using System.Globalization;
using System.Text.Json;
using System.Text.Json.Nodes;
using Npgsql;
using RackClick.Domain;
using static RackClick.Server.InventoryJson;

namespace RackClick.Server;

public sealed partial class InventoryStore
{
    private static async Task<Change> CompensateGroupReduction(NpgsqlConnection db, NpgsqlTransaction tx, Actor actor,
        Guid customer, Guid device, Guid original, Guid requestId, JsonObject before, JsonObject after,
        JsonObject result, long revision, CancellationToken ct)
    {
        DomainError Unsupported() => new(422, "compensation_unsupported");
        DomainError Conflict() => new(409, "compensation_state_conflict");
        void Require(bool valid) { if (!valid) throw Unsupported(); }
        JsonObject old, next;
        Dictionary<Guid, JsonObject> oldGroups, oldPorts, oldConnections;
        Dictionary<Guid, JsonObject[]> oldEndpoints;
        Guid[] restoredPorts, restoredGroups, restoredConnections, existingEnds;
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
            Require(Id(body, "resourceId") == device && Ids(body, "createdIds").Length == 0);
            old = before["data"]!["groupEditEvidence"]!.AsObject();
            next = after["data"]!["groupEditEvidence"]!.AsObject();
            string[] fields = ["formatVersion", "complete", "systemhausId", "customerId", "deviceId",
                "groups", "ports", "connections", "connectionEndpoints"];
            foreach (var value in new[] { old, next })
                Require(value.Count == fields.Length && fields.All(value.ContainsKey)
                    && value["formatVersion"]!.GetValue<int>() == 1 && value["complete"]!.GetValue<bool>()
                    && Id(value, "systemhausId") == actor.HouseId && Id(value, "customerId") == customer
                    && Id(value, "deviceId") == device);
            void Scope(JsonObject row) => Require(Id(row, "systemhaus_id") == actor.HouseId && Id(row, "customer_id") == customer);
            Dictionary<Guid, JsonObject> Rows(JsonObject value, string key, int maximum, string[] columns, bool onDevice)
            {
                var rows = new Dictionary<Guid, JsonObject>();
                foreach (var entry in Array(value, key, maximum))
                {
                    var row = entry!.AsObject(); Scope(row);
                    Require(row.Count == columns.Length && columns.All(row.ContainsKey) && rows.TryAdd(Id(row, "id"), row)
                        && (!onDevice || Id(row, "device_id") == device));
                }
                return rows;
            }
            string[] groupFields = ["id", "systemhaus_id", "customer_id", "device_id", "type", "name", "prefix", "sort_order"];
            string[] portFields = ["id", "systemhaus_id", "customer_id", "device_id", "group_id", "type", "connector_family",
                "gn", "sort_order", "label", "status", "poe", "watts", "color", "face", "power_role", "properties"];
            oldGroups = Rows(old, "groups", 32, groupFields, true); var nextGroups = Rows(next, "groups", 32, groupFields, true);
            oldPorts = Rows(old, "ports", 3072, portFields, true); var nextPorts = Rows(next, "ports", 3072, portFields, true);
            foreach (var (id, row) in nextGroups) Require(oldGroups.TryGetValue(id, out var previousGroup) && JsonNode.DeepEquals(previousGroup, row));
            foreach (var (id, row) in nextPorts) Require(oldPorts.TryGetValue(id, out var previousPort) && JsonNode.DeepEquals(previousPort, row));
            foreach (var (ports, groups) in new[] { (oldPorts, oldGroups), (nextPorts, nextGroups) })
            {
                foreach (var group in groups.Values)
                {
                    Require(InventoryRules.Family(String(group, "type")) == String(group, "type"));
                    _ = String(group, "name"); _ = String(group, "prefix"); _ = Integer(group, "sort_order", 0, int.MaxValue);
                }
                foreach (var port in ports.Values)
                {
                    Require(groups.TryGetValue(Id(port, "group_id"), out var group)
                        && String(port, "connector_family") == String(group, "type")
                        && InventoryRules.Family(String(port, "type")) == String(group, "type"));
                    _ = Integer(port, "gn", 1, int.MaxValue); _ = Integer(port, "sort_order", 0, int.MaxValue);
                    _ = InventoryRules.Status(String(port, "status")); _ = InventoryRules.Face(String(port, "face"));
                    _ = InventoryRules.PowerRole(String(port, "power_role")); _ = Number(port, "watts", 90);
                    _ = Color(port); _ = String(port, "label");
                    Require(port["poe"] is JsonValue boolean && boolean.TryGetValue<bool>(out var poe)
                        && (!poe || InventoryRules.Family(String(port, "type")) == "rj45")
                        && (String(port, "type") == "power" || String(port, "power_role") == "unspecified")
                        && port["properties"] is JsonObject);
                }
            }
            restoredPorts = oldPorts.Keys.Except(nextPorts.Keys).Order().ToArray();
            restoredGroups = oldGroups.Keys.Except(nextGroups.Keys).Order().ToArray();
            Require(restoredPorts.Length is >= 1 and <= 256 && restoredPorts.Length + restoredGroups.Length <= 256
                && Ids(body, "removedIds").ToHashSet().SetEquals(restoredPorts));

            (Dictionary<Guid, JsonObject>, Dictionary<Guid, JsonObject[]>) Connections(JsonObject value, Dictionary<Guid, JsonObject> ports)
            {
                string[] columns = ["id", "systemhaus_id", "customer_id", "note", "color", "patch", "properties", "created_at"];
                var connections = Rows(value, "connections", 3072, columns, false);
                var endpoints = new Dictionary<Guid, List<JsonObject>>(); var used = new HashSet<Guid>();
                string[] endFields = ["systemhaus_id", "customer_id", "connection_id", "ordinal", "port_id"];
                foreach (var entry in Array(value, "connectionEndpoints", 6144))
                {
                    var end = entry!.AsObject(); Scope(end); Guid id = Id(end, "connection_id");
                    Require(end.Count == endFields.Length && endFields.All(end.ContainsKey) && connections.ContainsKey(id)
                        && used.Add(Id(end, "port_id")));
                    _ = Integer(end, "ordinal", 0, 1);
                    if (!endpoints.TryGetValue(id, out var pair)) endpoints[id] = pair = [];
                    pair.Add(end);
                }
                foreach (var (id, connection) in connections)
                {
                    Require(endpoints.TryGetValue(id, out var pair) && pair.Count == 2
                        && pair.Select(e => Integer(e, "ordinal", 0, 1)).ToHashSet().SetEquals([0, 1])
                        && pair.Any(e => ports.ContainsKey(Id(e, "port_id"))));
                    _ = String(connection, "note"); _ = Color(connection); _ = InventoryRules.Patch(String(connection, "patch"));
                    Require(connection["properties"] is JsonObject && DateTimeOffset.TryParse(String(connection, "created_at"),
                        CultureInfo.InvariantCulture, DateTimeStyles.None, out _));
                }
                return (connections, endpoints.ToDictionary(p => p.Key, p => p.Value.OrderBy(e => Integer(e, "ordinal", 0, 1)).ToArray()));
            }
            (oldConnections, oldEndpoints) = Connections(old, oldPorts);
            var (nextConnections, nextEndpoints) = Connections(next, nextPorts);
            foreach (var (id, row) in nextConnections)
                Require(oldConnections.TryGetValue(id, out var previous) && JsonNode.DeepEquals(previous, row)
                    && oldEndpoints[id].Zip(nextEndpoints[id]).All(p => JsonNode.DeepEquals(p.First, p.Second)));
            restoredConnections = oldConnections.Keys.Except(nextConnections.Keys).Order().ToArray();
            Require(restoredConnections.Length <= restoredPorts.Length
                && restoredConnections.All(id => oldEndpoints[id].Any(e => restoredPorts.Contains(Id(e, "port_id"))))
                && !nextEndpoints.Values.SelectMany(p => p).Any(e => restoredPorts.Contains(Id(e, "port_id"))));
            var restoredIds = restoredPorts.Concat(restoredGroups).Concat(restoredConnections).ToArray();
            Require(restoredIds.Distinct().Count() == restoredIds.Length && !restoredIds.Contains(device));
            existingEnds = restoredConnections.SelectMany(id => oldEndpoints[id]).Select(e => Id(e, "port_id"))
                .Except(restoredPorts).Distinct().Order().ToArray();
        }
        catch (Exception e) when (e is DomainError or JsonException or InvalidOperationException or FormatException
            or NullReferenceException or ArgumentException or OverflowException or KeyNotFoundException)
        { throw Unsupported(); }
        if (afterRevision != revision) throw new DomainError(409, "compensation_not_latest");

        // Customer is already locked. Lock parents, then every surviving endpoint in UUID order.
        await using (var command = Cmd(db, tx,
            "SELECT id FROM inventory_device WHERE systemhaus_id=@house AND customer_id=@customer AND id=@device FOR UPDATE",
            ("house", actor.HouseId), ("customer", customer), ("device", device)))
            if (await command.ExecuteScalarAsync(ct) is not Guid) throw Conflict();
        await using (var command = Cmd(db, tx,
            "SELECT id FROM inventory_port_group WHERE systemhaus_id=@house AND customer_id=@customer AND device_id=@device ORDER BY id FOR UPDATE",
            ("house", actor.HouseId), ("customer", customer), ("device", device)))
        await using (var rows = await command.ExecuteReaderAsync(ct)) while (await rows.ReadAsync(ct)) { }
        var lockedPorts = new HashSet<Guid>();
        await using (var command = Cmd(db, tx,
            "SELECT id FROM inventory_port WHERE systemhaus_id=@house AND customer_id=@customer AND (device_id=@device OR id=ANY(@ends)) ORDER BY id FOR UPDATE",
            ("house", actor.HouseId), ("customer", customer), ("device", device), ("ends", existingEnds)))
        await using (var rows = await command.ExecuteReaderAsync(ct)) while (await rows.ReadAsync(ct)) lockedPorts.Add(rows.GetGuid(0));
        if (existingEnds.Any(id => !lockedPorts.Contains(id))) throw Conflict();
        foreach (var sql in new[] {
            "SELECT c.id FROM inventory_connection c WHERE c.systemhaus_id=@house AND c.customer_id=@customer AND EXISTS(SELECT 1 FROM inventory_connection_endpoint e JOIN inventory_port p ON p.id=e.port_id WHERE e.connection_id=c.id AND p.device_id=@device) ORDER BY c.id FOR UPDATE",
            "SELECT e.connection_id FROM inventory_connection_endpoint e WHERE e.systemhaus_id=@house AND e.customer_id=@customer AND EXISTS(SELECT 1 FROM inventory_connection_endpoint x JOIN inventory_port p ON p.id=x.port_id WHERE x.connection_id=e.connection_id AND p.device_id=@device) ORDER BY e.connection_id,e.ordinal FOR UPDATE"
        })
        {
            await using var command = Cmd(db, tx, sql, ("house", actor.HouseId), ("customer", customer), ("device", device));
            await using var rows = await command.ExecuteReaderAsync(ct); while (await rows.ReadAsync(ct)) { }
        }
        var current = await CaptureGroupEditEvidence(db, tx, actor, customer, device, ct);
        if (!JsonNode.DeepEquals(current, next)) throw Conflict();
        await using (var command = Cmd(db, tx, """
            SELECT EXISTS(SELECT 1 FROM inventory_port_group WHERE id=ANY(@groups))
                OR EXISTS(SELECT 1 FROM inventory_port WHERE id=ANY(@ports))
                OR EXISTS(SELECT 1 FROM inventory_connection WHERE id=ANY(@connections))
            """, ("groups", restoredGroups), ("ports", restoredPorts), ("connections", restoredConnections)))
            if (await command.ExecuteScalarAsync(ct) is true) throw Conflict();
        await RequireCompensationAuthorization(db, tx, actor, customer, ct);

        async Task InsertRows(string sql, IEnumerable<JsonObject> values, int expected)
        {
            if (expected == 0) return;
            await using var command = Cmd(db, tx, sql, ("rows", JsonSerializer.Serialize(values, Json)));
            if (await command.ExecuteNonQueryAsync(ct) != expected) throw Conflict();
        }
        // Literal column lists: connector_family is generated; no UPSERT or regenerated identities/dates.
        await InsertRows("""
            INSERT INTO inventory_port_group(id,systemhaus_id,customer_id,device_id,type,name,prefix,sort_order)
            SELECT id,systemhaus_id,customer_id,device_id,type,name,prefix,sort_order
            FROM jsonb_populate_recordset(NULL::inventory_port_group,CAST(@rows AS jsonb))
            """, restoredGroups.Select(id => oldGroups[id]), restoredGroups.Length);
        await InsertRows("""
            INSERT INTO inventory_port(id,systemhaus_id,customer_id,device_id,group_id,type,gn,sort_order,label,status,poe,watts,color,face,power_role,properties)
            SELECT id,systemhaus_id,customer_id,device_id,group_id,type,gn,sort_order,label,status,poe,watts,color,face,power_role,properties
            FROM jsonb_populate_recordset(NULL::inventory_port,CAST(@rows AS jsonb))
            """, restoredPorts.Select(id => oldPorts[id]), restoredPorts.Length);
        foreach (Guid id in restoredConnections)
        {
            var endpoints = oldEndpoints[id];
            try
            {
                var pair = await Pair(db, tx, actor, customer, Id(endpoints[0], "port_id"), Id(endpoints[1], "port_id"), null, ct);
                ConfirmReserved(pair, new JsonObject());
            }
            catch (DomainError e) when (e.Status is 404 or 409 or 422) { throw Conflict(); }
            await InsertRows("""
                INSERT INTO inventory_connection(id,systemhaus_id,customer_id,note,color,patch,properties,created_at)
                SELECT id,systemhaus_id,customer_id,note,color,patch,properties,created_at
                FROM jsonb_populate_recordset(NULL::inventory_connection,CAST(@rows AS jsonb))
                """, [oldConnections[id]], 1);
            await InsertRows("""
                INSERT INTO inventory_connection_endpoint(systemhaus_id,customer_id,connection_id,ordinal,port_id)
                SELECT systemhaus_id,customer_id,connection_id,ordinal,port_id
                FROM jsonb_populate_recordset(NULL::inventory_connection_endpoint,CAST(@rows AS jsonb))
                """, endpoints, 2);
        }
        await ValidateExistingPower(db, tx, actor, customer, restoredPorts, ct);
        var restored = await CaptureGroupEditEvidence(db, tx, actor, customer, device, ct);
        if (!JsonNode.DeepEquals(restored, old)) throw Conflict();
        await RequireCompensationAuthorization(db, tx, actor, customer, ct);
        return new(device, new { kind = "groupReduction", groupEditEvidence = current },
            new { kind = "groupReduction", groupEditEvidence = restored },
            new { resourceId = device, compensationKind = "groupReduction", restoredPortIds = restoredPorts,
                restoredGroupIds = restoredGroups, restoredConnectionIds = restoredConnections, compensatedOperationId = original });
    }
}
