using System.Text.Json;
using System.Text.Json.Nodes;
using Npgsql;
using NpgsqlTypes;
using RackClick.Domain;
using static RackClick.Server.InventoryJson;

namespace RackClick.Server;

public sealed partial class InventoryStore
{
    private static async Task RequireCompensationAuthorization(NpgsqlConnection db, NpgsqlTransaction tx, Actor actor, Guid customer, CancellationToken ct)
    {
        await PostgresStore.RequireCurrentSession(db, tx, actor, ct);
        await RequireRead(db, tx, actor, customer, ct);
        if (!await PostgresStore.Can(db, tx, actor, customer, Capabilities.InventoryEdit, ct)) throw new DomainError(403, "forbidden");
    }

    private static async Task<Change> CompensatePorts(NpgsqlConnection db, NpgsqlTransaction tx, Actor actor, Guid customer,
        JsonObject payload, long revision, CancellationToken ct)
    {
        if (payload.Count != 1 || !payload.ContainsKey("operationId")) throw new DomainError(422, "payload_invalid");
        Guid original = Id(payload, "operationId");
        DomainError Unsupported() => new(422, "compensation_unsupported");
        void Require(bool value) { if (!value) throw Unsupported(); }
        JsonObject before, after, result;
        Guid device, requestId;
        string action;
        // Identity is filtered before bounded materialization. Invalid evidence remains distinguishable from absence.
        await using (var command = Cmd(db, tx, """
            SELECT a.action,a.resource_id,a.request_id,
              CASE WHEN octet_length(a.before_json::text)<=8388608 THEN a.before_json::text ELSE NULL END,
              CASE WHEN octet_length(a.after_json::text)<=8388608 THEN a.after_json::text ELSE NULL END,
              CASE WHEN octet_length(o.result_json::text)<=8388608 THEN o.result_json::text ELSE NULL END
            FROM audit_event a JOIN operation o ON o.systemhaus_id=a.systemhaus_id AND o.actor_id=a.actor_id AND o.request_id=a.request_id
            WHERE a.id=@original AND a.systemhaus_id=@house AND a.actor_id=@actor
              AND o.result_json->>'operationId'=@originalText AND o.result_json->>'customerId'=@customerText
              AND a.before_json->>'customerId'=@customerText AND a.after_json->>'customerId'=@customerText
            """, ("original", original), ("originalText", original.ToString("D")), ("customerText", customer.ToString("D")),
            ("house", actor.HouseId), ("actor", actor.Id)))
        await using (var row = await command.ExecuteReaderAsync(ct))
        {
            if (!await row.ReadAsync(ct)) throw new DomainError(404, "not_found");
            Require(!row.IsDBNull(1) && !row.IsDBNull(3) && !row.IsDBNull(4) && !row.IsDBNull(5));
            action = row.GetString(0); device = row.GetGuid(1); requestId = row.GetGuid(2);
            try
            {
                before = JsonNode.Parse(row.GetString(3))!.AsObject();
                after = JsonNode.Parse(row.GetString(4))!.AsObject();
                result = JsonNode.Parse(row.GetString(5))!.AsObject();
            }
            catch (Exception e) when (e is JsonException or InvalidOperationException) { throw Unsupported(); }
        }
        if (action == "inventory.device.editPortGroups")
        {
            if (result["result"] is JsonObject groupResult && groupResult["createdIds"] is JsonArray { Count: 0 })
                return await CompensateGroupReduction(db, tx, actor, customer, device, original, requestId,
                    before, after, result, revision, ct);
            return await CompensateGroupGrowth(db, tx, actor, customer, device, original, requestId,
                before, after, result, revision, ct);
        }
        JsonObject[] old, next;
        Guid group;
        string family;
        long afterRevision;
        try
        {
            Require(action == "inventory.ports.update" && device != Guid.Empty && requestId != Guid.Empty);
            long prior = before["revision"]!.GetValue<long>(); afterRevision = after["revision"]!.GetValue<long>();
            Require(prior >= 1 && prior < long.MaxValue && afterRevision == prior + 1
                && Id(before, "customerId") == customer && Id(after, "customerId") == customer
                && Id(result, "customerId") == customer && Id(result, "operationId") == original
                && Id(result, "requestId") == requestId && result["revision"]!.GetValue<long>() == afterRevision
                && Id(result["result"]!.AsObject(), "resourceId") == device);
            old = Array(before, "data").Select(p => p!.AsObject()).ToArray();
            next = Array(after, "data").Select(p => p!.AsObject()).ToArray();
            Require(old.Length is >= 1 and <= 256 && old.Length == next.Length);
            group = Id(old[0], "group_id"); family = InventoryRules.Family(String(old[0], "type"));
            var ids = new HashSet<Guid>(); bool changed = false;
            string[] columns = ["id", "systemhaus_id", "customer_id", "device_id", "group_id", "type", "connector_family", "gn", "sort_order", "label", "status", "poe", "watts", "color", "face", "power_role", "properties"];
            void ValidateRow(JsonObject port)
            {
                Require(port.Count == columns.Length && columns.All(port.ContainsKey));
                _ = Id(port, "id"); Require(Id(port, "systemhaus_id") == actor.HouseId && Id(port, "customer_id") == customer
                    && Id(port, "device_id") == device && Id(port, "group_id") == group
                    && InventoryRules.Family(String(port, "type")) == family && String(port, "connector_family") == family);
                _ = Integer(port, "gn", 1, int.MaxValue); _ = Integer(port, "sort_order", 0, int.MaxValue);
                _ = InventoryRules.Status(String(port, "status")); _ = InventoryRules.Face(String(port, "face"));
                _ = InventoryRules.PowerRole(String(port, "power_role")); _ = Color(port); _ = Number(port, "watts", 90);
                Require(port["poe"] is JsonValue boolean && boolean.TryGetValue<bool>(out var poe)
                    && (!poe || family == "rj45") && (family == "power" || String(port, "power_role") == "unspecified"));
                string label = String(port, "label"); if (label.Length != 0) _ = Names.Validate(label, 500);
                Require(port["properties"] is JsonObject); _ = Properties(port);
            }
            for (int i = 0; i < old.Length; i++)
            {
                ValidateRow(old[i]); ValidateRow(next[i]); Require(ids.Add(Id(old[i], "id")) && Id(old[i], "id") == Id(next[i], "id"));
                // UpdatePorts canonicalizes the RJ45 alias only when its request contains poe,
                // including normalization-only writes whose bool is unchanged. Otherwise legacy
                // rj45+true / rj45_poe+false remain valid and must survive an unrelated edit.
                if (!JsonNode.DeepEquals(old[i]["poe"], next[i]["poe"]) || !JsonNode.DeepEquals(old[i]["type"], next[i]["type"]))
                    Require(family == "rj45" && String(next[i], "type") == (Boolean(next[i], "poe") ? "rj45_poe" : "rj45"));
                foreach (string column in columns)
                    if (!JsonNode.DeepEquals(old[i][column], next[i][column]))
                    {
                        Require(column is "status" or "label" or "color" or "face" or "poe" or "watts" or "type"); changed = true;
                    }
            }
            Require(changed);
            Require(Ids(result["result"]!.AsObject(), "changedIds").SequenceEqual(old.Select(p => Id(p, "id"))));
        }
        catch (Exception e) when (e is DomainError or JsonException or InvalidOperationException or FormatException or NullReferenceException or ArgumentException or OverflowException)
        { throw Unsupported(); }
        if (afterRevision != revision) throw new DomainError(409, "compensation_not_latest");
        DomainError Conflict() => new(409, "compensation_state_conflict");
        try
        {
            _ = await Row(db, tx, actor, customer, "inventory_device", device, ct);
            var currentGroup = await Row(db, tx, actor, customer, "inventory_port_group", group, ct);
            if (Id(currentGroup, "device_id") != device || String(currentGroup, "type") != family) throw Conflict();
        }
        catch (DomainError e) when (e.Status == 404) { throw Conflict(); }
        var actual = new Dictionary<Guid, JsonObject>();
        // Customer precedes rows; stable UUID ordering avoids introducing an inverse lock order.
        foreach (var port in next.OrderBy(p => Id(p, "id")))
        {
            Guid id = Id(port, "id");
            await using var command = Cmd(db, tx, """
                SELECT to_jsonb(p)::text,to_jsonb(p)=CAST(@after AS jsonb) FROM inventory_port p
                WHERE systemhaus_id=@house AND customer_id=@customer AND id=@id FOR UPDATE
                """, ("house", actor.HouseId), ("customer", customer), ("id", id), ("after", port.ToJsonString()));
            await using var row = await command.ExecuteReaderAsync(ct);
            if (!await row.ReadAsync(ct) || !row.GetBoolean(1)) throw Conflict();
            actual.Add(id, JsonNode.Parse(row.GetString(0))!.AsObject());
        }
        var restored = new List<JsonObject>();
        foreach (var port in old)
        {
            Guid id = Id(port, "id");
            await using var command = Cmd(db, tx, """
                UPDATE inventory_port SET status=@status,label=@label,color=@color,face=@face,type=@type,poe=@poe,watts=@watts
                WHERE systemhaus_id=@house AND customer_id=@customer AND id=@id
                """, ("status", String(port, "status")), ("label", String(port, "label")), ("color", Color(port)), ("face", String(port, "face")),
                ("type", String(port, "type")), ("poe", Boolean(port, "poe")),
                ("house", actor.HouseId), ("customer", customer), ("id", id));
            // Preserve decimal values and NULL versus zero without text conversion or bool-derived aliases.
            command.Parameters.Add(new NpgsqlParameter("watts", NpgsqlDbType.Numeric) { Value = (object?)Number(port, "watts", 90) ?? DBNull.Value });
            if (await command.ExecuteNonQueryAsync(ct) != 1) throw Conflict();
            restored.Add(await Row(db, tx, actor, customer, "inventory_port", id, ct));
        }
        Guid[] changedIds = old.Select(p => Id(p, "id")).ToArray();
        await ValidateExistingPower(db, tx, actor, customer, changedIds, ct);
        await RequireCompensationAuthorization(db, tx, actor, customer, ct);
        return new(device, changedIds.Select(id => actual[id]).ToArray(), restored,
            new { resourceId = device, changedIds, compensatedOperationId = original });
    }
}
