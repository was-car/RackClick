using System.Text.Json.Nodes;
using Npgsql;
using RackClick.Domain;
using static RackClick.Server.InventoryJson;

namespace RackClick.Server;

public sealed partial class InventoryStore
{
    private static async Task<Guid[]> QueryIds(NpgsqlConnection db, NpgsqlTransaction tx, string sql, CancellationToken ct, params (string, object?)[] args)
    {
        await using var cmd = Cmd(db, tx, sql, args);
        await using var rows = await cmd.ExecuteReaderAsync(ct);
        var ids = new List<Guid>();
        while (await rows.ReadAsync(ct)) ids.Add(rows.GetGuid(0));
        return ids.ToArray();
    }
    private static async Task<int> NextOrder(NpgsqlConnection db, NpgsqlTransaction tx, Actor actor, Guid customer, Guid? rack, Guid? room, CancellationToken ct)
    {
        await using var cmd = Cmd(db, tx, "SELECT COALESCE(max(sort_order),-1)+1 FROM inventory_device WHERE systemhaus_id=@house AND customer_id=@customer AND rack_id IS NOT DISTINCT FROM @rack::uuid AND room_id IS NOT DISTINCT FROM @room::uuid",
            ("house", actor.HouseId), ("customer", customer), ("rack", rack), ("room", room));
        return (int)(await cmd.ExecuteScalarAsync(ct))!;
    }
    private static async Task Capacity(NpgsqlConnection db, NpgsqlTransaction tx, Actor actor, Guid customer, Guid rack, Guid? exclude, int added, CancellationToken ct)
    {
        var target = await Row(db, tx, actor, customer, "inventory_rack", rack, ct);
        await using var cmd = Cmd(db, tx, "SELECT COALESCE(sum(size_u),0)::integer FROM inventory_device WHERE systemhaus_id=@house AND customer_id=@customer AND rack_id=@rack AND id IS DISTINCT FROM @exclude::uuid",
            ("house", actor.HouseId), ("customer", customer), ("rack", rack), ("exclude", exclude));
        InventoryRules.RequireCapacity(Integer(target, "size_u", 1, 1000), (int)(await cmd.ExecuteScalarAsync(ct))!, added);
    }

    private static async Task<Change> Device(NpgsqlConnection db, NpgsqlTransaction tx, Actor actor, Guid customer,
        string type, JsonObject payload, CancellationToken ct)
    {
        if (type == "device.reorder")
        {
            Guid rackId = Id(payload, "rackId");
            await Row(db, tx, actor, customer, "inventory_rack", rackId, ct);
            Guid[] ids = Ids(payload, "deviceIds"), actual = await QueryIds(db, tx,
                "SELECT id FROM inventory_device WHERE systemhaus_id=@house AND customer_id=@customer AND rack_id=@rack ORDER BY sort_order,id", ct,
                ("house", actor.HouseId), ("customer", customer), ("rack", rackId));
            if (!ids.ToHashSet().SetEquals(actual)) throw new DomainError(422, "device_order_invalid");
            for (int i = 0; i < ids.Length; i++)
                await Exec(db, tx, "UPDATE inventory_device SET sort_order=@order WHERE systemhaus_id=@house AND customer_id=@customer AND id=@id", ct,
                    ("order", i), ("house", actor.HouseId), ("customer", customer), ("id", ids[i]));
            return new(rackId, new { deviceIds = actual }, new { deviceIds = ids }, new { resourceId = rackId });
        }
        bool create = type == "device.create", move = type == "device.move";
        Guid id = create ? Guid.NewGuid() : Id(payload, "id");
        JsonObject? before = create ? null : await Row(db, tx, actor, customer, "inventory_device", id, ct);
        if (before?["hardware_profile_key"] is not null)
        {
            if (type == "device.update") return await UpdateHardware(db, tx, actor, customer, payload, before, ct);
            RequireLegacyMutableDevice(before);
        }
        if (payload.Any(field => field.Key is "hardwareProfileKey" or "profileKey" or "mountParentId" or "mountSlotKey"))
            throw new DomainError(422, "hardware_command_required");
        string kind = create ? String(payload, "kind") : String(before!, "kind");
        if (kind is not ("rackEquipment" or "dose" or "endDevice")) throw new DomainError(422, "device_kind_invalid");
        Guid? rack = create || move ? OptionalId(payload, "rackId") : OptionalId(before!, "rack_id");
        Guid? room = create || move ? OptionalId(payload, "roomId") : OptionalId(before!, "room_id");
        if ((kind == "rackEquipment" && (rack is null || room is not null)) ||
            (kind != "rackEquipment" && (room is null || rack is not null))) throw new DomainError(422, "placement_invalid");
        int? size = kind == "rackEquipment" ? Integer(payload, "sizeU", 1, 1000, before is null ? null : Integer(before, "size_u", 1, 1000)) : null;
        if (kind != "rackEquipment" && payload["sizeU"] is not null) throw new DomainError(422, "placement_invalid");
        if (rack.HasValue) await Capacity(db, tx, actor, customer, rack.Value, create ? null : id, size!.Value, ct);
        if (room.HasValue) await Row(db, tx, actor, customer, "inventory_room", room.Value, ct);
        string name = create || payload.ContainsKey("name") ? Names.Validate(String(payload, "name")) : String(before!, "name");
        decimal? budget = create || payload.ContainsKey("poeBudget") ? Number(payload, "poeBudget", 999999) : Number(before!, "poe_budget", 999999);
        string properties = Properties(payload, before?["properties"] as JsonObject);
        int order = create || move ? await NextOrder(db, tx, actor, customer, rack, room, ct) : Integer(before!, "sort_order", 0, int.MaxValue);
        string sql = create ? """
            INSERT INTO inventory_device(id,systemhaus_id,customer_id,kind,rack_id,room_id,name,size_u,sort_order,poe_budget,properties)
            VALUES(@id,@house,@customer,@kind,@rack,@room,@name,@size,@order,@budget,CAST(@properties AS jsonb))
            """ : """
            UPDATE inventory_device SET rack_id=@rack,room_id=@room,name=@name,size_u=@size,sort_order=@order,
            poe_budget=@budget,properties=CAST(@properties AS jsonb) WHERE systemhaus_id=@house AND customer_id=@customer AND id=@id
            """;
        await Exec(db, tx, sql, ct, ("id", id), ("house", actor.HouseId), ("customer", customer), ("kind", kind),
            ("rack", rack), ("room", room), ("name", name), ("size", size), ("order", order), ("budget", budget), ("properties", properties));
        var createdIds = new List<Guid> { id };
        if (create)
        {
            var groups = Array(payload, "portGroups", 32, optional: true);
            for (int i = 0; i < groups.Count; i++)
            {
                if (groups[i] is not JsonObject group) throw new DomainError(422, "port_group_invalid");
                createdIds.AddRange(await AddGroup(db, tx, actor, customer, id, group, i, ct));
            }
        }
        var after = await Row(db, tx, actor, customer, "inventory_device", id, ct);
        return new(id, before, new { device = after, createdIds }, new { resourceId = id, createdIds });
    }

    private static async Task<Guid[]> AddGroup(NpgsqlConnection db, NpgsqlTransaction tx, Actor actor, Guid customer, Guid device,
        JsonObject input, int order, CancellationToken ct, int maximum = 96)
    {
        if (input.ContainsKey("physicalConnector") || input.ContainsKey("physicalFace") || input.ContainsKey("interfaceRole") || input.ContainsKey("signalRole") || input.ContainsKey("hardwarePhysicalConnector") ||
            input["properties"] is JsonObject metadata && metadata.Any(f => f.Key is "hardwarePhysicalConnector" or "hardwarePhysicalFace" or "hardwareInterfaceRole" or "hardwareSignalRole" or "hardwarePowerSystem" or "declaredPowerSystem"))
            throw new DomainError(422, "hardware_metadata_immutable");
        string type = InventoryRules.PortType(String(input, "type"));
        if(type!="power_dc" && input["powerSystem"] is not null) throw new DomainError(422,"hardware_metadata_invalid");
        int count = Integer(input, "count", 1, maximum);
        Guid group = Guid.NewGuid();
        await Exec(db, tx, """
            INSERT INTO inventory_port_group(id,systemhaus_id,customer_id,device_id,type,name,prefix,sort_order)
            VALUES(@id,@house,@customer,@device,@type,@name,@prefix,@order)
            """, ct, ("id", group), ("house", actor.HouseId), ("customer", customer), ("device", device),
            ("type", InventoryRules.Family(type)), ("name", Text(input, "name", 100)), ("prefix", Text(input, "prefix", 100)), ("order", order));
        var ids = new List<Guid> { group };
        for (int i = 0; i < count; i++) ids.Add(await AddPort(db, tx, actor, customer, device, group, type, i + 1, i, ct));
        if (type == "power_dc")
        {
            string system = input["powerSystem"] is null ? "dc" : String(input, "powerSystem");
            _ = FamilyLRules.Feature("powerSystem", system);
            await Exec(db, tx, "UPDATE inventory_port SET properties=jsonb_set(properties,'{declaredPowerSystem}',to_jsonb(@system::text),true) WHERE systemhaus_id=@house AND customer_id=@customer AND group_id=@group", ct,
                ("system", system), ("house", actor.HouseId), ("customer", customer), ("group", group));
        }
        return ids.ToArray();
    }
    private static async Task<Guid> AddPort(NpgsqlConnection db, NpgsqlTransaction tx, Actor actor, Guid customer, Guid device, Guid group,
        string type, int gn, int order, CancellationToken ct)
    {
        Guid id = Guid.NewGuid();
        await Exec(db, tx, """
            INSERT INTO inventory_port(id,systemhaus_id,customer_id,device_id,group_id,type,gn,sort_order,poe)
            VALUES(@id,@house,@customer,@device,@group,@type,@gn,@order,@poe)
            """, ct, ("id", id), ("house", actor.HouseId), ("customer", customer), ("device", device), ("group", group),
            ("type", type), ("gn", gn), ("order", order), ("poe", type == "rj45_poe"));
        return id;
    }

    private static async Task<Change> UpdatePorts(NpgsqlConnection db, NpgsqlTransaction tx, Actor actor, Guid customer, JsonObject payload, CancellationToken ct)
    {
        Guid device = Id(payload, "deviceId"), group = Id(payload, "groupId");
        var owner = await Row(db, tx, actor, customer, "inventory_device", device, ct);
        var groupRow = await Row(db, tx, actor, customer, "inventory_port_group", group, ct);
        string groupType = String(payload, "groupType");
        if (Id(groupRow, "device_id") != device || String(groupRow, "type") != groupType) throw new DomainError(422, "port_scope_invalid");
        Guid[] ids = Ids(payload, "portIds");
        if (ids.Length == 0) throw new DomainError(422, "port_ids_required");
        if (payload["changes"] is not JsonObject changes || changes.Count == 0) throw new DomainError(422, "changes_required");
        if (changes["properties"] is JsonObject physicalPatch && physicalPatch.Any(field => field.Key is "hardwarePhysicalConnector" or "hardwarePhysicalFace" or "hardwareInterfaceRole" or "hardwareSignalRole" or "hardwarePowerSystem" or "declaredPowerSystem"))
            throw new DomainError(422, "hardware_metadata_immutable");
        if (owner["hardware_profile_key"] is not null && changes["properties"] is JsonObject hardwarePatch
            && hardwarePatch.Any(field => field.Key is "hardwareGroupKey" or "hardwarePortKey"))
            throw new DomainError(422, "hardware_metadata_immutable");
        if (changes.Any(p => p.Key is not ("status" or "poe" or "watts" or "color" or "label" or "face" or "powerRole" or "properties")))
            throw new DomainError(422, "field_unknown");
        var before = new List<JsonObject>();
        var after = new List<JsonObject>();
        foreach (Guid id in ids)
        {
            var port = await Row(db, tx, actor, customer, "inventory_port", id, ct);
            if (Id(port, "device_id") != device || Id(port, "group_id") != group || InventoryRules.Family(String(port, "type")) != groupType)
                throw new DomainError(422, "port_scope_invalid");
            before.Add(port);
            string type = String(port, "type");
            bool poe = changes.ContainsKey("poe") ? Boolean(changes, "poe") : Boolean(port, "poe");
            if (changes.ContainsKey("poe"))
            {
                if (InventoryRules.Family(type) != "rj45") throw new DomainError(422, "poe_not_supported");
                type = poe ? "rj45_poe" : "rj45";
            }
            string role = changes.ContainsKey("powerRole") ? InventoryRules.PowerRole(String(changes, "powerRole")) : String(port, "power_role");
            if (!FamilyLRules.IsPower(type) && role != "unspecified") throw new DomainError(422, "power_role_invalid");
            // A fixed hardware inlet is not an editable generic power socket.
            // Retain its sealed role; labels/status and same-role requests stay valid.
            if (owner["hardware_profile_key"] is not null && role != String(port, "power_role"))
                throw new DomainError(422, "hardware_metadata_immutable");
            string status = changes.ContainsKey("status") ? InventoryRules.Status(String(changes, "status")) : String(port, "status");
            string face = changes.ContainsKey("face") ? InventoryRules.Face(String(changes, "face")) : String(port, "face");
            if (owner["hardware_profile_key"] is not null && face != String(port, "face"))
                throw new DomainError(422, "hardware_metadata_immutable");
            decimal? watts = changes.ContainsKey("watts") ? InventoryRules.Watts(Number(changes, "watts", 90)) : Number(port, "watts", 90);
            string label = changes.ContainsKey("label") ? Text(changes, "label", 500) : String(port, "label");
            string? color = changes.ContainsKey("color") ? Color(changes) : Color(port);
            await Exec(db, tx, """
                UPDATE inventory_port SET type=@type,poe=@poe,power_role=@role,status=@status,face=@face,watts=@watts,label=@label,
                color=@color,properties=CAST(@properties AS jsonb) WHERE systemhaus_id=@house AND customer_id=@customer AND id=@id
                """, ct, ("type", type), ("poe", poe), ("role", role), ("status", status), ("face", face), ("watts", watts),
                ("label", label), ("color", color), ("properties", Properties(changes, port["properties"] as JsonObject)),
                ("house", actor.HouseId), ("customer", customer), ("id", id));
            after.Add(await Row(db, tx, actor, customer, "inventory_port", id, ct));
        }
        await ValidateExistingPower(db, tx, actor, customer, ids, ct);
        return new(device, before, after, new { resourceId = device, changedIds = ids });
    }
}
