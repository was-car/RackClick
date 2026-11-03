using System.Text.Json.Nodes;
using Npgsql;
using RackClick.Domain;
using static RackClick.Server.InventoryJson;

namespace RackClick.Server;

public sealed partial class InventoryStore
{
    private static async Task<Change> CreateHardware(NpgsqlConnection db, NpgsqlTransaction tx, Actor actor, Guid customer,
        JsonObject payload, CancellationToken ct)
    {
        if (payload.Any(field => field.Key is not ("profileKey" or "profileVersion" or "rackId" or "roomId" or "name" or "mountParentId" or "mountSlotKey")))
            throw new DomainError(422, "field_unknown");
        string key = String(payload, "profileKey");
        if (!InventoryHardwareProfiles.All.Any(profile => profile.Key == key)) throw new DomainError(422, "hardware_profile_unknown");
        // Old v1 requests are permanently pinned to v1, never to a future default.
        string revision = payload.ContainsKey("profileVersion") ? String(payload, "profileVersion") : InventoryHardwareProfiles.Version;
        var compiled = InventoryHardwareProfiles.Find(key, revision) ?? throw new DomainError(422, "hardware_revision_unknown");
        var profile = await ReadHardwareDefinition(db, tx, compiled, ct);
        if (profile.Kind == "rackContainer") throw new DomainError(422, "hardware_rack_command_required");
        if (FamilyLRules.IsRoom(profile.Kind) || profile.Kind is "vertical0U" or "sharedU") return await CreateFamilyHardware(db, tx, actor, customer, payload, profile, ct);
        if (payload["roomId"] is not null) throw new DomainError(422, "mount_profile_incompatible");
        Guid rack = Id(payload, "rackId"), id = Guid.NewGuid();
        Guid? parent = OptionalId(payload, "mountParentId");
        string? slot = payload["mountSlotKey"] is null ? null : String(payload, "mountSlotKey");
        await Row(db, tx, actor, customer, "inventory_rack", rack, ct);
        if (profile.Kind == "desktop")
        {
            if (parent is null || slot is null) throw new DomainError(422, "mount_parent_required");
            var support = await Row(db, tx, actor, customer, "inventory_device", parent.Value, ct);
            if (OptionalId(support, "rack_id") != rack || support["mount_parent_id"] is not null)
                throw new DomainError(422, "mount_support_invalid");
            string? supportRevision = support["properties"]?["hardwareProfileVersion"] is JsonValue recorded && recorded.TryGetValue<string>(out var value) ? value : null;
            var parentCompiled = InventoryHardwareProfiles.Find(support["hardware_profile_key"]?.GetValue<string>(), supportRevision);
            if (parentCompiled is null)
                throw new DomainError(409, "mount_support_revision_unavailable");
            if (parentCompiled.Kind != "shelf") throw new DomainError(422, "mount_support_invalid");
            var parentDefinition = await ReadHardwareDefinition(db, tx, parentCompiled, ct);
            var bay = parentDefinition.Slots.SingleOrDefault(s => s.Key == slot) ?? throw new DomainError(422, "mount_support_invalid");
            if (profile.WidthMm is not { } w || profile.HeightMm is not { } h || profile.DepthMm is not { } depth || w > bay.WidthMm || h > bay.HeightMm || depth > bay.DepthMm)
                throw new DomainError(422, "mount_dimensions_invalid");
            await using var occupied = Cmd(db, tx, "SELECT EXISTS(SELECT 1 FROM inventory_device WHERE systemhaus_id=@house AND customer_id=@customer AND mount_parent_id=@parent AND mount_slot_key=@slot)",
                ("house", actor.HouseId), ("customer", customer), ("parent", parent), ("slot", slot));
            if (await occupied.ExecuteScalarAsync(ct) is true) throw new DomainError(409, "mount_slot_occupied");
        }
        else if (parent is not null || slot is not null) throw new DomainError(422, "mount_profile_incompatible");
        await Capacity(db, tx, actor, customer, rack, null, profile.RackUnits, ct);
        int order = await NextOrder(db, tx, actor, customer, rack, null, ct);
        string name = Names.Validate(String(payload, "name"));
        var properties = HardwareProperties(profile);
        await Exec(db, tx, """
            INSERT INTO inventory_device(id,systemhaus_id,customer_id,kind,rack_id,name,size_u,sort_order,properties,hardware_profile_key,mount_parent_id,mount_slot_key)
            VALUES(@id,@house,@customer,'rackEquipment',@rack,@name,@size,@order,CAST(@properties AS jsonb),@profile,@parent,@slot)
            """, ct, ("id", id), ("house", actor.HouseId), ("customer", customer), ("rack", rack), ("name", name),
            ("size", profile.RackUnits), ("order", order), ("properties", properties.ToJsonString()), ("profile", profile.Key), ("parent", parent), ("slot", slot));
        var created = new List<Guid> { id };
        created.AddRange(await CreateProfileGroups(db, tx, actor, customer, id, profile, ct));
        var after = await Row(db, tx, actor, customer, "inventory_device", id, ct);
        return new(id, null, new { device = after, createdIds = created }, new { resourceId = id, createdIds = created });
    }

    private static async Task<Change> UpdateHardware(NpgsqlConnection db, NpgsqlTransaction tx, Actor actor, Guid customer,
        JsonObject payload, JsonObject before, CancellationToken ct)
    {
        if (payload.Any(field => field.Key is not ("id" or "name" or "properties"))) throw new DomainError(422, "hardware_operation_unsupported");
        if (payload["properties"] is not null && payload["properties"] is not JsonObject) throw new DomainError(422, "properties_invalid");
        if (payload["properties"] is JsonObject patch && patch.Any(field => field.Key is not ("notes" or "color")))
            throw new DomainError(422, "hardware_metadata_immutable");
        if (payload["properties"] is JsonObject colorPatch && colorPatch.ContainsKey("color")) _ = Color(colorPatch);
        Guid id = Id(before, "id");
        string name = payload.ContainsKey("name") ? Names.Validate(String(payload, "name")) : String(before, "name");
        await Exec(db, tx, "UPDATE inventory_device SET name=@name,properties=CAST(@properties AS jsonb) WHERE systemhaus_id=@house AND customer_id=@customer AND id=@id", ct,
            ("name", name), ("properties", Properties(payload, before["properties"]!.AsObject())), ("house", actor.HouseId), ("customer", customer), ("id", id));
        return new(id, before, await Row(db, tx, actor, customer, "inventory_device", id, ct), new { resourceId = id });
    }

    private static void RequireLegacyMutableDevice(JsonObject row)
    {
        if (row["hardware_profile_key"] is not null || row["mount_parent_id"] is not null)
            throw new DomainError(422, "hardware_operation_unsupported");
    }
}
