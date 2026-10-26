using System.Text.Json;
using Npgsql;
using RackClick.Domain;

namespace RackClick.Server;

public sealed partial class InventoryStore
{
    private static string Category(JsonElement properties)
    {
        string? preset = null;
        // An explicit textual catalog key takes precedence even when unknown or empty.
        // The legacy fallback accepts exact keys only, never a translated preset label.
        if (properties.ValueKind == JsonValueKind.Object)
        {
            if (properties.TryGetProperty("catalog", out var catalog) && catalog.ValueKind == JsonValueKind.Object
                && catalog.TryGetProperty("presetKey", out var key) && key.ValueKind == JsonValueKind.String)
                preset = key.GetString();
            else if (properties.TryGetProperty("preset", out var legacy) && legacy.ValueKind == JsonValueKind.String)
                preset = legacy.GetString();
        }
        return preset switch
        {
            "pp24" or "pp48" or "ppf24" => "Patch Panel",
            "sw24" or "sw48" or "swsfp" => "Switch",
            "rtr" => "Router",
            "fw" => "Firewall",
            "srv1u" or "srv2u" or "srv4u" => "Server",
            "nas2u" or "nas4u" or "san" => "NAS/SAN",
            _ => "Other"
        };
    }

    private static async Task<Dictionary<Guid, string>> ConnectionCategories(NpgsqlConnection db, NpgsqlTransaction tx,
        Actor actor, Guid customer, Guid[] ports, CancellationToken ct)
    {
        // Resolve persisted identities and their group/device ownership in the authorized customer.
        // gn, user labels and category strings in the request never participate.
        await using var command = Cmd(db, tx, """
            SELECT p.id,d.properties::text
            FROM inventory_port p
            JOIN inventory_port_group g ON g.systemhaus_id=p.systemhaus_id AND g.customer_id=p.customer_id
                AND g.id=p.group_id AND g.device_id=p.device_id
            JOIN inventory_device d ON d.systemhaus_id=g.systemhaus_id AND d.customer_id=g.customer_id AND d.id=g.device_id
            WHERE p.systemhaus_id=@house AND p.customer_id=@customer AND p.id=ANY(@ports)
            """, ("house", actor.HouseId), ("customer", customer), ("ports", ports));
        var categories = new Dictionary<Guid, string>();
        await using var rows = await command.ExecuteReaderAsync(ct);
        while (await rows.ReadAsync(ct))
        {
            using var properties = JsonDocument.Parse(rows.GetString(1));
            categories.Add(rows.GetGuid(0), Category(properties.RootElement));
        }
        if (categories.Count != ports.Length) throw new DomainError(404, "not_found");
        return categories;
    }
}
