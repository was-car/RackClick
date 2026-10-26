using System.Text.Json.Nodes;
using Npgsql;
using RackClick.Domain;
using static RackClick.Server.InventoryJson;

namespace RackClick.Server;

public sealed partial class InventoryStore
{
    private static async Task<Change> DuplicateRack(NpgsqlConnection db, NpgsqlTransaction tx, Actor actor, Guid customer,
        JsonObject payload, CancellationToken ct)
    {
        Guid original = Id(payload, "id"), rack = Guid.NewGuid();
        var before = await Row(db, tx, actor, customer, "inventory_rack", original, ct);
        string name = payload.ContainsKey("name") ? Names.Validate(String(payload, "name")) : Names.Validate(String(before, "name") + " (Copy)");
        await Exec(db, tx, """
            INSERT INTO inventory_rack(id,systemhaus_id,customer_id,room_id,name,location,size_u,properties)
            SELECT @new,systemhaus_id,customer_id,room_id,@name,location,size_u,properties FROM inventory_rack
            WHERE systemhaus_id=@house AND customer_id=@customer AND id=@old
            """, ct, ("new", rack), ("name", name), ("house", actor.HouseId), ("customer", customer), ("old", original));
        var devices = await QueryIds(db, tx, "SELECT id FROM inventory_device WHERE systemhaus_id=@house AND customer_id=@customer AND rack_id=@rack ORDER BY sort_order,id", ct,
            ("house", actor.HouseId), ("customer", customer), ("rack", original));
        var created = new List<Guid> { rack }; var portMap = new Dictionary<Guid, Guid>();
        foreach (Guid oldDevice in devices)
        {
            Guid device = Guid.NewGuid(); created.Add(device);
            await Exec(db, tx, """
                INSERT INTO inventory_device(id,systemhaus_id,customer_id,kind,rack_id,room_id,name,size_u,sort_order,poe_budget,properties)
                SELECT @new,systemhaus_id,customer_id,kind,@rack,room_id,name,size_u,sort_order,poe_budget,properties FROM inventory_device
                WHERE systemhaus_id=@house AND customer_id=@customer AND id=@old
                """, ct, ("new", device), ("rack", rack), ("house", actor.HouseId), ("customer", customer), ("old", oldDevice));
            var groups = await QueryIds(db, tx, "SELECT id FROM inventory_port_group WHERE systemhaus_id=@house AND customer_id=@customer AND device_id=@device ORDER BY sort_order,id", ct,
                ("house", actor.HouseId), ("customer", customer), ("device", oldDevice));
            foreach (Guid oldGroup in groups)
            {
                Guid group = Guid.NewGuid(); created.Add(group);
                await Exec(db, tx, """
                    INSERT INTO inventory_port_group(id,systemhaus_id,customer_id,device_id,type,name,prefix,sort_order)
                    SELECT @new,systemhaus_id,customer_id,@device,type,name,prefix,sort_order FROM inventory_port_group
                    WHERE systemhaus_id=@house AND customer_id=@customer AND id=@old
                    """, ct, ("new", group), ("device", device), ("house", actor.HouseId), ("customer", customer), ("old", oldGroup));
                var ports = await QueryIds(db, tx, "SELECT id FROM inventory_port WHERE systemhaus_id=@house AND customer_id=@customer AND group_id=@group ORDER BY sort_order,id", ct,
                    ("house", actor.HouseId), ("customer", customer), ("group", oldGroup));
                foreach (Guid oldPort in ports)
                {
                    Guid port = Guid.NewGuid(); portMap.Add(oldPort, port); created.Add(port);
                    await Exec(db, tx, """
                        INSERT INTO inventory_port(id,systemhaus_id,customer_id,device_id,group_id,type,gn,sort_order,label,status,poe,watts,color,face,power_role,properties)
                        SELECT @new,systemhaus_id,customer_id,@device,@group,type,gn,sort_order,label,status,poe,watts,color,face,power_role,properties FROM inventory_port
                        WHERE systemhaus_id=@house AND customer_id=@customer AND id=@old
                        """, ct, ("new", port), ("device", device), ("group", group), ("house", actor.HouseId), ("customer", customer), ("old", oldPort));
                }
            }
        }
        if (Boolean(payload, "includeConnections"))
        {
            var connectionIds = await QueryIds(db, tx, """
                SELECT a.connection_id FROM inventory_connection_endpoint a JOIN inventory_connection_endpoint b ON b.connection_id=a.connection_id AND b.ordinal=1
                WHERE a.ordinal=0 AND a.systemhaus_id=@house AND a.customer_id=@customer AND a.port_id=ANY(@ports) AND b.port_id=ANY(@ports)
                """, ct, ("house", actor.HouseId), ("customer", customer), ("ports", portMap.Keys.ToArray()));
            var reserved = new List<JsonObject>();
            foreach (Guid oldConnection in connectionIds)
            {
                var old = await ConnectionRow(db, tx, actor, customer, oldConnection, ct);
                Guid a = Id(old, "fromPortId"), b = Id(old, "toPortId");
                reserved.Add(await Row(db, tx, actor, customer, "inventory_port", a, ct));
                reserved.Add(await Row(db, tx, actor, customer, "inventory_port", b, ct));
                await Pair(db, tx, actor, customer, portMap[a], portMap[b], null, ct);
                created.Add(await InsertConnection(db, tx, actor, customer, portMap[a], portMap[b], old, ct));
            }
            ConfirmReserved(reserved, payload);
        }
        return new(rack, new { sourceRackId = original }, new { rack = await Row(db, tx, actor, customer, "inventory_rack", rack, ct), createdIds = created },
            new { resourceId = rack, createdIds = created });
    }
}
