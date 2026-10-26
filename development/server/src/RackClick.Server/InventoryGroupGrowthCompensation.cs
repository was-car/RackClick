using System.Text.Json;
using System.Text.Json.Nodes;
using Npgsql;
using RackClick.Domain;
using static RackClick.Server.InventoryJson;

namespace RackClick.Server;

public sealed partial class InventoryStore
{
    private static async Task<Change> CompensateGroupGrowth(NpgsqlConnection db, NpgsqlTransaction tx, Actor actor,
        Guid customer, Guid device, Guid original, Guid requestId, JsonObject before, JsonObject after,
        JsonObject result, long revision, CancellationToken ct)
    {
        DomainError Unsupported() => new(422, "compensation_unsupported");
        void Require(bool valid) { if (!valid) throw Unsupported(); }
        JsonObject old, next;
        Guid[] addedPorts, addedGroups;
        long afterRevision;
        try
        {
            Require(device != Guid.Empty && requestId != Guid.Empty);
            long prior = before["revision"]!.GetValue<long>(); afterRevision = after["revision"]!.GetValue<long>();
            Require(prior >= 1 && prior < long.MaxValue && afterRevision == prior + 1
                && Id(before, "customerId") == customer && Id(after, "customerId") == customer
                && Id(result, "customerId") == customer && Id(result, "operationId") == original
                && Id(result, "requestId") == requestId && result["revision"]!.GetValue<long>() == afterRevision);
            var body = result["result"]!.AsObject();
            Require(Id(body, "resourceId") == device && Ids(body, "removedIds").Length == 0);
            old = before["data"]!["groupEditEvidence"]!.AsObject();
            next = after["data"]!["groupEditEvidence"]!.AsObject();
            string[] evidenceFields = ["formatVersion", "complete", "systemhausId", "customerId", "deviceId",
                "groups", "ports", "connections", "connectionEndpoints"];
            foreach (var value in new[] { old, next })
                Require(value.Count == evidenceFields.Length && evidenceFields.All(value.ContainsKey)
                    && value["formatVersion"]!.GetValue<int>() == 1 && value["complete"]!.GetValue<bool>()
                    && Id(value, "systemhausId") == actor.HouseId && Id(value, "customerId") == customer
                    && Id(value, "deviceId") == device);

            Dictionary<Guid, JsonObject> Rows(JsonObject value, string key, int maximum, string[] fields)
            {
                var rows = new Dictionary<Guid, JsonObject>();
                foreach (var entry in Array(value, key, maximum))
                {
                    var row = entry!.AsObject(); Guid id = Id(row, "id");
                    Require(row.Count == fields.Length && fields.All(row.ContainsKey) && rows.TryAdd(id, row)
                        && Id(row, "systemhaus_id") == actor.HouseId && Id(row, "customer_id") == customer
                        && Id(row, "device_id") == device);
                }
                return rows;
            }
            string[] groupFields = ["id", "systemhaus_id", "customer_id", "device_id", "type", "name", "prefix", "sort_order"];
            string[] portFields = ["id", "systemhaus_id", "customer_id", "device_id", "group_id", "type", "connector_family",
                "gn", "sort_order", "label", "status", "poe", "watts", "color", "face", "power_role", "properties"];
            var oldGroups = Rows(old, "groups", 32, groupFields); var nextGroups = Rows(next, "groups", 32, groupFields);
            var oldPorts = Rows(old, "ports", 3072, portFields); var nextPorts = Rows(next, "ports", 3072, portFields);
            foreach (var (id, row) in oldGroups) Require(nextGroups.TryGetValue(id, out var currentGroup) && JsonNode.DeepEquals(row, currentGroup));
            foreach (var (id, row) in oldPorts) Require(nextPorts.TryGetValue(id, out var currentPort) && JsonNode.DeepEquals(row, currentPort));
            foreach (var (ports, groups) in new[] { (oldPorts, oldGroups), (nextPorts, nextGroups) })
                foreach (var port in ports.Values)
                    Require(groups.TryGetValue(Id(port, "group_id"), out var group)
                        && String(port, "connector_family") == String(group, "type")
                        && InventoryRules.Family(String(port, "type")) == String(group, "type"));
            addedPorts = nextPorts.Keys.Except(oldPorts.Keys).Order().ToArray();
            addedGroups = nextGroups.Keys.Except(oldGroups.Keys).Order().ToArray();
            var created = Ids(body, "createdIds");
            Require(addedPorts.Length is >= 1 and <= 256 && created.Length >= 1
                && created.ToHashSet().SetEquals(addedPorts.Concat(addedGroups))
                && addedPorts.Concat(addedGroups).Distinct().Count() == addedPorts.Length + addedGroups.Length);
            Require(Array(old, "connections", 3072).Count == Array(next, "connections", 3072).Count
                && JsonNode.DeepEquals(old["connections"], next["connections"])
                && Array(old, "connectionEndpoints", 6144).Count == Array(next, "connectionEndpoints", 6144).Count
                && JsonNode.DeepEquals(old["connectionEndpoints"], next["connectionEndpoints"]));
            Require(!Array(next, "connectionEndpoints", 6144).Any(e => addedPorts.Contains(Id(e!.AsObject(), "port_id"))));
        }
        catch (Exception e) when (e is DomainError or JsonException or InvalidOperationException or FormatException
            or NullReferenceException or ArgumentException or OverflowException)
        { throw Unsupported(); }
        if (afterRevision != revision) throw new DomainError(409, "compensation_not_latest");
        DomainError Conflict() => new(409, "compensation_state_conflict");

        // Customer is already locked by Execute. Parent then UUID-ordered rows protect FK references too.
        await using (var command = Cmd(db, tx,
            "SELECT id FROM inventory_device WHERE systemhaus_id=@house AND customer_id=@customer AND id=@device FOR UPDATE",
            ("house", actor.HouseId), ("customer", customer), ("device", device)))
            if (await command.ExecuteScalarAsync(ct) is not Guid) throw Conflict();
        foreach (var sql in new[] {
            "SELECT id FROM inventory_port_group WHERE systemhaus_id=@house AND customer_id=@customer AND device_id=@device ORDER BY id FOR UPDATE",
            "SELECT id FROM inventory_port WHERE systemhaus_id=@house AND customer_id=@customer AND device_id=@device ORDER BY id FOR UPDATE",
            "SELECT c.id FROM inventory_connection c WHERE c.systemhaus_id=@house AND c.customer_id=@customer AND EXISTS(SELECT 1 FROM inventory_connection_endpoint e JOIN inventory_port p ON p.id=e.port_id WHERE e.connection_id=c.id AND p.device_id=@device) ORDER BY c.id FOR UPDATE",
            "SELECT e.connection_id FROM inventory_connection_endpoint e WHERE e.systemhaus_id=@house AND e.customer_id=@customer AND EXISTS(SELECT 1 FROM inventory_connection_endpoint x JOIN inventory_port p ON p.id=x.port_id WHERE x.connection_id=e.connection_id AND p.device_id=@device) ORDER BY e.connection_id,e.ordinal FOR UPDATE"
        })
        {
            await using var command = Cmd(db, tx, sql, ("house", actor.HouseId), ("customer", customer), ("device", device));
            await using var rows = await command.ExecuteReaderAsync(ct);
            while (await rows.ReadAsync(ct)) { }
        }
        var currentEvidence = await CaptureGroupEditEvidence(db, tx, actor, customer, device, ct);
        if (!JsonNode.DeepEquals(currentEvidence, next)) throw Conflict();
        await RequireCompensationAuthorization(db, tx, actor, customer, ct);
        await using (var command = Cmd(db, tx,
            "DELETE FROM inventory_port WHERE systemhaus_id=@house AND customer_id=@customer AND device_id=@device AND id=ANY(@ids)",
            ("house", actor.HouseId), ("customer", customer), ("device", device), ("ids", addedPorts)))
            if (await command.ExecuteNonQueryAsync(ct) != addedPorts.Length) throw Conflict();
        if (addedGroups.Length != 0)
        {
            await using var command = Cmd(db, tx,
                "DELETE FROM inventory_port_group WHERE systemhaus_id=@house AND customer_id=@customer AND device_id=@device AND id=ANY(@ids)",
                ("house", actor.HouseId), ("customer", customer), ("device", device), ("ids", addedGroups));
            if (await command.ExecuteNonQueryAsync(ct) != addedGroups.Length) throw Conflict();
        }
        var restoredEvidence = await CaptureGroupEditEvidence(db, tx, actor, customer, device, ct);
        if (!JsonNode.DeepEquals(restoredEvidence, old)) throw Conflict();
        await RequireCompensationAuthorization(db, tx, actor, customer, ct);
        return new(device, new { kind = "groupGrowth", groupEditEvidence = currentEvidence },
            new { kind = "groupGrowth", groupEditEvidence = restoredEvidence },
            new { resourceId = device, compensationKind = "groupGrowth", removedPortIds = addedPorts,
                removedGroupIds = addedGroups, compensatedOperationId = original });
    }
}
