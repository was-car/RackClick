using System.Text.Json.Nodes;
using Npgsql;
using RackClick.Domain;
using static RackClick.Server.InventoryJson;

namespace RackClick.Server;

public sealed partial class InventoryStore
{
    private static async Task<Change> CreateFromPrivateTemplate(NpgsqlConnection db, NpgsqlTransaction tx, Actor actor,
        Guid customer, JsonObject payload, CancellationToken ct)
    {
        CatalogKeys(payload, ["templateId", "definitionVersion", "definitionSha256", "kind", "rackId", "roomId", "name", "color", "poeBudget", "notes"]);
        Guid templateId = Id(payload, "templateId");
        int version = Integer(payload, "definitionVersion", 1, 1);
        string hash = String(payload, "definitionSha256");
        if (hash.Length != 64 || hash.Any(c => c is not (>= '0' and <= '9' or >= 'a' and <= 'f'))) throw new DomainError(422, "request_invalid");
        var definition = await PrivateDeviceTemplates.ForCreation(db, tx, actor, customer, templateId, version, hash, ct);
        return await CreateFromTemplateDefinition(db, tx, actor, customer, payload, templateId, version, hash, definition, ct);
    }
    private static async Task<Change> CreateFromTemplateDefinition(NpgsqlConnection db, NpgsqlTransaction tx, Actor actor,
        Guid customer, JsonObject payload, Guid templateId, int version, string hash, PrivateTemplateDefinition definition, CancellationToken ct)
    {
        string kind = String(payload, "kind"), name = Names.Validate(String(payload, "name"));
        if (kind != definition.Kind) throw new DomainError(422, "device_kind_invalid");
        Guid? rack = OptionalId(payload, "rackId"), room = OptionalId(payload, "roomId");
        if ((kind == "rackEquipment" && (rack is null || room is not null)) || (kind != "rackEquipment" && (room is null || rack is not null)))
            throw new DomainError(422, "placement_invalid");
        string color = String(payload, "color");
        if (!InventoryRc9Catalog.ValidColor(color)) throw new DomainError(422, "color_invalid");
        decimal? budget = Number(payload, "poeBudget", 999999);
        if (payload["notes"] is not JsonObject notes) throw new DomainError(422, "request_invalid");
        CatalogKeys(notes, ["sn", "model", "ip", "firmware", "text"]);
        foreach (var key in notes.Select(p => p.Key)) _ = FreeText.Validate(String(notes, key), 2000);
        if (rack.HasValue) await Capacity(db, tx, actor, customer, rack.Value, null, definition.SizeU!.Value, ct);
        if (room.HasValue) _ = await Row(db, tx, actor, customer, "inventory_room", room.Value, ct);
        int order = await NextOrder(db, tx, actor, customer, rack, room, ct);
        string properties = Properties(new JsonObject { ["properties"] = new JsonObject
        {
            ["icon"] = definition.Icon, ["color"] = color, ["preset"] = definition.VisualFamily, ["notes"] = notes.DeepClone()
        }});
        Guid device = Guid.NewGuid(); var created = new List<Guid> { device };
        await Exec(db, tx, "INSERT INTO inventory_device(id,systemhaus_id,customer_id,kind,rack_id,room_id,name,size_u,sort_order,poe_budget,properties) VALUES(@id,@house,@customer,@kind,@rack,@room,@name,@size,@order,@budget,CAST(@properties AS jsonb))", ct,
            ("id", device), ("house", actor.HouseId), ("customer", customer), ("kind", kind), ("rack", rack), ("room", room),
            ("name", name), ("size", definition.SizeU), ("order", order), ("budget", budget), ("properties", properties));
        foreach (var group in definition.PortGroups)
        {
            Guid groupId = Guid.NewGuid(); created.Add(groupId);
            await Exec(db, tx, "INSERT INTO inventory_port_group(id,systemhaus_id,customer_id,device_id,type,name,prefix,sort_order) VALUES(@id,@house,@customer,@device,@type,@name,@prefix,@order)", ct,
                ("id", groupId), ("house", actor.HouseId), ("customer", customer), ("device", device), ("type", group.Type), ("name", group.Name), ("prefix", group.Prefix), ("order", group.SortOrder));
            foreach (var port in group.Ports)
            {
                Guid portId = Guid.NewGuid(); created.Add(portId);
                // Runtime state and all extension properties are deliberately reset; never create connections.
                await Exec(db, tx, "INSERT INTO inventory_port(id,systemhaus_id,customer_id,device_id,group_id,type,gn,sort_order,label,status,poe,watts,color,face,power_role,properties) VALUES(@id,@house,@customer,@device,@group,@type,@gn,@order,@label,'free',@poe,NULL,@color,@face,@role,'{}'::jsonb)", ct,
                    ("id", portId), ("house", actor.HouseId), ("customer", customer), ("device", device), ("group", groupId), ("type", port.Type),
                    ("gn", port.Gn), ("order", port.SortOrder), ("label", port.Label), ("poe", port.Poe), ("color", port.Color), ("face", port.Face), ("role", port.PowerRole));
            }
        }
        var after = await Row(db, tx, actor, customer, "inventory_device", device, ct);
        return new(device, null, new { device = after, createdIds = created, templateId, definitionVersion = version, definitionSha256 = hash },
            new { resourceId = device, createdIds = created });
    }
}
