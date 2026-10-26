using System.Text.Json.Nodes;
using Npgsql;
using RackClick.Domain;
using static RackClick.Server.InventoryJson;

namespace RackClick.Server;

public sealed partial class InventoryStore
{
    private static void CatalogKeys(JsonObject value, string[] keys)
    {
        if (value.Count != keys.Length || keys.Any(k => !value.ContainsKey(k))) throw new DomainError(422, "request_invalid");
    }

    private static async Task RequireCatalogCreateAuthorization(NpgsqlConnection db, NpgsqlTransaction tx, Actor actor, Guid customer, CancellationToken ct)
    {
        await PostgresStore.RequireCurrentSession(db, tx, actor, ct);
        await RequireRead(db, tx, actor, customer, ct);
        if (!await PostgresStore.Can(db, tx, actor, customer, Capabilities.InventoryEdit, ct)) throw new DomainError(403, "forbidden");
    }

    // Called only after the existing engine has checked current authority, replay and customer revision.
    private static async Task<Change> CreateFromCatalog(NpgsqlConnection db, NpgsqlTransaction tx, Actor actor,
        Guid customer, JsonObject payload, CancellationToken ct)
    {
        CatalogKeys(payload, ["presetKey", "catalogVersion", "catalogSha256", "language", "kind", "rackId", "roomId", "name", "color", "poeBudget", "notes"]);
        var preset = InventoryRc9Catalog.Preset(String(payload, "presetKey"), String(payload, "catalogVersion"),
            String(payload, "catalogSha256"), String(payload, "language"));
        string kind = String(payload, "kind"), name = Names.Validate(String(payload, "name"));
        if (kind is not ("rackEquipment" or "dose" or "endDevice")) throw new DomainError(422, "device_kind_invalid");
        Guid? rack = OptionalId(payload, "rackId"), room = OptionalId(payload, "roomId");
        if ((kind == "rackEquipment" && (rack is null || room is not null))
            || (kind != "rackEquipment" && (room is null || rack is not null))
            || (preset.Key == "ap" && kind != "endDevice")) throw new DomainError(422, "placement_invalid");
        string color = String(payload, "color");
        if (!InventoryRc9Catalog.ValidColor(color)) throw new DomainError(422, "color_invalid");
        decimal? budget = Number(payload, "poeBudget", 999999);
        if (payload["notes"] is not JsonObject notes) throw new DomainError(422, "request_invalid");
        CatalogKeys(notes, ["sn", "model", "ip", "firmware", "text"]);
        foreach (var key in notes.Select(p => p.Key)) _ = FreeText.Validate(String(notes, key), 2000);
        decimal knownWatts = preset.PortGroups.SelectMany(g => g.Ports).Where(p => p.Poe).Sum(p => p.Watts ?? 0);
        if (budget.HasValue && knownWatts > budget.Value) throw new DomainError(422, "poe_budget_exceeded");
        int? size = kind == "rackEquipment" ? preset.SizeU : null;
        if (rack.HasValue) await Capacity(db, tx, actor, customer, rack.Value, null, size!.Value, ct);
        if (room.HasValue) _ = await Row(db, tx, actor, customer, "inventory_room", room.Value, ct);
        int order = await NextOrder(db, tx, actor, customer, rack, room, ct);
        var propertiesInput = new JsonObject { ["properties"] = new JsonObject
        {
            ["preset"] = preset.Label, ["icon"] = preset.Icon, ["color"] = color, ["notes"] = notes.DeepClone(),
            ["catalog"] = new JsonObject { ["presetKey"] = preset.Key, ["version"] = InventoryRc9Catalog.Version,
                ["sha256"] = InventoryRc9Catalog.Sha256, ["language"] = String(payload, "language") }
        }};
        string properties = Properties(propertiesInput);
        Guid device = Guid.NewGuid(); var created = new List<Guid> { device };
        await Exec(db, tx, """
            INSERT INTO inventory_device(id,systemhaus_id,customer_id,kind,rack_id,room_id,name,size_u,sort_order,poe_budget,properties)
            VALUES(@id,@house,@customer,@kind,@rack,@room,@name,@size,@order,@budget,CAST(@properties AS jsonb))
            """, ct, ("id", device), ("house", actor.HouseId), ("customer", customer), ("kind", kind),
            ("rack", rack), ("room", room), ("name", name), ("size", size), ("order", order), ("budget", budget), ("properties", properties));
        foreach (var group in preset.PortGroups)
        {
            Guid groupId = Guid.NewGuid(); created.Add(groupId);
            await Exec(db, tx, """
                INSERT INTO inventory_port_group(id,systemhaus_id,customer_id,device_id,type,name,prefix,sort_order)
                VALUES(@id,@house,@customer,@device,@type,@name,@prefix,@order)
                """, ct, ("id", groupId), ("house", actor.HouseId), ("customer", customer), ("device", device),
                ("type", group.Type), ("name", group.Name), ("prefix", group.Prefix), ("order", group.SortOrder));
            foreach (var port in group.Ports)
            {
                Guid portId = Guid.NewGuid(); created.Add(portId);
                await Exec(db, tx, """
                    INSERT INTO inventory_port(id,systemhaus_id,customer_id,device_id,group_id,type,gn,sort_order,label,status,poe,watts,color,face,power_role,properties)
                    VALUES(@id,@house,@customer,@device,@group,@type,@gn,@order,@label,@status,@poe,@watts,@color,@face,@role,CAST(@properties AS jsonb))
                    """, ct, ("id", portId), ("house", actor.HouseId), ("customer", customer), ("device", device), ("group", groupId),
                    ("type", port.Type), ("gn", port.Gn), ("order", port.SortOrder), ("label", port.Label), ("status", port.Status),
                    ("poe", port.Poe), ("watts", port.Watts), ("color", port.Color), ("face", port.Face), ("role", port.PowerRole),
                    ("properties", port.Properties.GetRawText()));
            }
        }
        var after = await Row(db, tx, actor, customer, "inventory_device", device, ct);
        return new(device, null, new { device = after, createdIds = created,
            presetKey = preset.Key, catalogVersion = InventoryRc9Catalog.Version, catalogSha256 = InventoryRc9Catalog.Sha256 },
            new { resourceId = device, createdIds = created });
    }
}
