using Npgsql;
using RackClick.Domain;
using System.Text.Json.Nodes;

namespace RackClick.Server;

public sealed partial class InventoryStore
{
    private static async Task<InventoryHardwareProfiles.Profile> ReadHardwareDefinition(NpgsqlConnection db,
        NpgsqlTransaction tx, InventoryHardwareProfiles.Profile expected, CancellationToken ct)
    {
        // A deployment that grants the runtime generic ALL TABLES DML must not
        // silently make the global catalog writable. Also checks inherited rights.
        await using (var rights = Cmd(db, tx, """
            SELECT bool_and(has_table_privilege(current_user,name,'SELECT') AND
              NOT has_table_privilege(current_user,name,'INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER'))
            FROM (VALUES('public.hardware_definition'),('public.hardware_mount_slot'),
              ('public.hardware_group_template'),('public.hardware_passthrough'),('public.hardware_connector_template'),
              ('public.hardware_profile_extension'),('public.hardware_group_extension')) AS tables(name)
            """))
            if (await rights.ExecuteScalarAsync(ct) is not true)
                throw new DomainError(503, "hardware_catalog_permissions_invalid");

        await using (var definition = Cmd(db, tx, """
            SELECT mount_kind,rack_units,width_mm,height_mm,depth_mm,color,definition_sha256,manufacturer,family,model,sku
            FROM hardware_definition WHERE profile_key=@key AND revision=@revision AND sealed
            """, ("key", expected.Key), ("revision", expected.Revision)))
        {
            await using var row = await definition.ExecuteReaderAsync(ct);
            if (!await row.ReadAsync(ct)) throw new DomainError(409, "hardware_catalog_revision_unavailable");
            if (row.GetString(0) != expected.Kind || row.GetInt32(1) != expected.RackUnits || (row.IsDBNull(2) ? (decimal?)null : row.GetDecimal(2)) != expected.WidthMm ||
                (row.IsDBNull(3) ? (decimal?)null : row.GetDecimal(3)) != expected.HeightMm || (row.IsDBNull(4) ? (decimal?)null : row.GetDecimal(4)) != expected.DepthMm || row.GetString(5) != expected.Color ||
                row.GetString(6) != expected.DefinitionSha256 ||
                (row.IsDBNull(7) ? null : row.GetString(7)) != expected.Manufacturer || (row.IsDBNull(8) ? null : row.GetString(8)) != expected.Family ||
                (row.IsDBNull(9) ? null : row.GetString(9)) != expected.Model || (row.IsDBNull(10) ? null : row.GetString(10)) != expected.Sku)
                throw new DomainError(409, "hardware_catalog_definition_mismatch");
        }
        await using (var query = Cmd(db, tx, """
            SELECT metadata::text FROM hardware_profile_extension WHERE profile_key=@key AND revision=@revision
            """, ("key", expected.Key), ("revision", expected.Revision)))
        {
            var stored = await query.ExecuteScalarAsync(ct) as string;
            if (expected.MountingJson is null)
            {
                if (stored is not null || expected.ConfigurationJson is not null || expected.ContinuitiesJson is not null)
                    throw new DomainError(409, "hardware_catalog_definition_mismatch");
            }
            else
            {
                var metadata = new JsonObject { ["mounting"] = JsonNode.Parse(expected.MountingJson),
                    ["configuration"] = JsonNode.Parse(expected.ConfigurationJson ?? "[]"),
                    ["continuities"] = JsonNode.Parse(expected.ContinuitiesJson ?? "[]") };
                if (stored is null || !JsonNode.DeepEquals(JsonNode.Parse(stored), metadata))
                    throw new DomainError(409, "hardware_catalog_definition_mismatch");
            }
        }
        var groups = new List<InventoryHardwareProfiles.Group>();
        await using (var query = Cmd(db, tx, """
            SELECT g.group_key,g.type,g.port_count,g.face,g.name,g.prefix,g.power_role,c.physical_connector,e.metadata::text FROM hardware_group_template g
            LEFT JOIN hardware_connector_template c USING(profile_key,revision,group_key)
            LEFT JOIN hardware_group_extension e USING(profile_key,revision,group_key)
            WHERE g.profile_key=@key AND g.revision=@revision ORDER BY g.sort_order
            """, ("key", expected.Key), ("revision", expected.Revision)))
        {
            await using var rows = await query.ExecuteReaderAsync(ct);
            while (await rows.ReadAsync(ct))
            {
                var metadata = rows.IsDBNull(8) ? null : JsonNode.Parse(rows.GetString(8)) as JsonObject;
                if (!rows.IsDBNull(8) && (metadata is null || metadata.Count == 0 || metadata.Any(p =>
                    p.Key is not ("physicalFace" or "interfaceRole" or "signalRole" or "powerSystem") || p.Value is not JsonValue value || !value.TryGetValue<string>(out _))))
                    throw new DomainError(409, "hardware_catalog_definition_mismatch");
                string? Feature(string key) => metadata?[key] is JsonValue value && value.TryGetValue<string>(out var text)
                    ? FamilyLRules.Feature(key, text) : null;
                groups.Add(new(rows.GetString(0), rows.GetString(1), rows.GetInt32(2), rows.GetString(3), rows.GetString(4), rows.GetString(5)) {
                    PowerRole = rows.GetString(6), PhysicalConnector = FamilyLRules.Descriptor(rows.GetString(1), rows.IsDBNull(7) ? null : rows.GetString(7)),
                    PhysicalFace = Feature("physicalFace"), InterfaceRole = Feature("interfaceRole"), SignalRole = Feature("signalRole"), PowerSystem = Feature("powerSystem") });
            }
        }
        var slots = new List<InventoryHardwareProfiles.Slot>();
        await using (var query = Cmd(db, tx, """
            SELECT slot_key,width_mm,height_mm,depth_mm FROM hardware_mount_slot
            WHERE profile_key=@key AND revision=@revision ORDER BY slot_key
            """, ("key", expected.Key), ("revision", expected.Revision)))
        {
            await using var rows = await query.ExecuteReaderAsync(ct);
            while (await rows.ReadAsync(ct)) slots.Add(new(rows.GetString(0), rows.GetDecimal(1), rows.GetDecimal(2), rows.GetDecimal(3)));
        }
        InventoryHardwareProfiles.Continuity? passthrough = null;
        await using (var query = Cmd(db, tx, """
            SELECT front_group_key,rear_group_key,port_count FROM hardware_passthrough
            WHERE profile_key=@key AND revision=@revision
            """, ("key", expected.Key), ("revision", expected.Revision)))
        {
            await using var rows = await query.ExecuteReaderAsync(ct);
            if (await rows.ReadAsync(ct)) passthrough = new(rows.GetString(0), rows.GetString(1), rows.GetInt32(2));
        }
        if (!groups.SequenceEqual(expected.Groups) || !slots.SequenceEqual(expected.Slots.OrderBy(s => s.Key, StringComparer.Ordinal)) ||
            passthrough != expected.Passthrough)
            throw new DomainError(409, "hardware_catalog_definition_mismatch");
        return expected with { Groups = groups.AsReadOnly(), Slots = slots.AsReadOnly(), Passthrough = passthrough };
    }
}
