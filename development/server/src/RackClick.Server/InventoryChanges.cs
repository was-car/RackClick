using System.Globalization;
using System.Text.Json;
using RackClick.Domain;

namespace RackClick.Server;

public sealed record InventoryChangeActor(Guid Id, string? UserNameCurrent);
public sealed record InventoryChangedPort(Guid Id, Guid DeviceId, Guid GroupId, string Type, int Gn);
public sealed record InventoryChangedConnection(Guid Id, Guid FromPortId, Guid ToPortId);
public sealed record InventoryChangeContext(string Status, IReadOnlyList<InventoryChangedPort> BeforePorts,
    IReadOnlyList<InventoryChangedPort> AfterPorts, IReadOnlyList<InventoryChangedConnection> BeforeConnections,
    IReadOnlyList<InventoryChangedConnection> AfterConnections);
public sealed record InventoryChangeEvent(Guid Id, InventoryChangeActor Actor, string Action, Guid? ResourceId,
    long RevisionBefore, long RevisionAfter, DateTime OccurredAt, InventoryChangeContext Context);
public sealed record InventoryChanges(Guid CustomerId, long CurrentRevision, long NextRevision, bool HasMore,
    bool RefreshRequired, IReadOnlyList<InventoryChangeEvent> Events);

public sealed partial class InventoryStore
{
    private static readonly HashSet<string> ChangeActions = new(StringComparer.Ordinal)
    {
        "inventory.site.create", "inventory.site.update", "inventory.site.delete",
        "inventory.building.create", "inventory.building.update", "inventory.building.delete",
        "inventory.room.create", "inventory.room.update", "inventory.room.delete",
        "inventory.rack.create", "inventory.rack.createHardware", "inventory.rack.update", "inventory.rack.assignRoom", "inventory.rack.delete", "inventory.rack.duplicate",
        "inventory.device.create", "inventory.device.createHardware", "inventory.device.createFromCatalog", "inventory.device.createFromPrivateTemplate", "inventory.device.createFromSharedTemplate", "inventory.device.update", "inventory.device.move", "inventory.device.reorder",
        "inventory.device.delete", "inventory.devices.delete", "inventory.device.editPortGroups", "inventory.ports.update",
        "inventory.operations.compensate", "inventory.connections.create", "inventory.connections.createBatch", "inventory.connections.update",
        "inventory.connections.disconnect", "inventory.connections.reconnect"
    };
    internal static string[] AllowedChangeActions() => ChangeActions.Order(StringComparer.Ordinal).ToArray();
    private static InventoryChangeContext NoChangeContext() => new("notAvailable", [], [], [], []);

    // These expressions use only literal field names. Large/private extensions never leave PostgreSQL.
    private static string ChangeText(string value, string field, int max = 36) =>
        $"CASE WHEN jsonb_typeof({value}->'{field}')='string' AND octet_length({value}->>'{field}')<={max} THEN {value}->'{field}' ELSE NULL END";
    private static string ChangeData(string wrapper, bool ports)
    {
        string data = wrapper + "->'data'";
        string Item(string value) => "jsonb_build_object(" +
            $"'id',{ChangeText(value, "id")},'houseId',{ChangeText(value, "systemhaus_id")},'customerId',{ChangeText(value, "customer_id")}," +
            (ports ? $"'deviceId',{ChangeText(value, "device_id")},'groupId',{ChangeText(value, "group_id")},'type',{ChangeText(value, "type", 16)}," +
                $"'gn',CASE WHEN jsonb_typeof({value}->'gn')='number' AND octet_length({value}->>'gn')<=10 THEN {value}->'gn' ELSE NULL END"
                : $"'fromPortId',{ChangeText(value, "fromPortId")},'toPortId',{ChangeText(value, "toPortId")}") + ")";
        int maximum = ports ? 256 : 128;
        return $"jsonb_build_object('kind',jsonb_typeof({data}),'count',CASE WHEN jsonb_typeof({data})='array' THEN jsonb_array_length({data}) ELSE NULL END," +
            $"'items',CASE WHEN jsonb_typeof({data})='array' THEN CASE WHEN jsonb_array_length({data})<={maximum} THEN " +
            $"(SELECT COALESCE(jsonb_agg({Item("v")} ORDER BY n),'[]'::jsonb) FROM jsonb_array_elements({data}) WITH ORDINALITY AS e(v,n)) ELSE '[]'::jsonb END " +
            $"WHEN jsonb_typeof({data})='object' THEN jsonb_build_array({Item(data)}) ELSE '[]'::jsonb END)::text";
    }

    public async Task<InventoryChanges> ReadChanges(Actor actor, Guid customer, string? rawAfter, string? rawLimit, CancellationToken ct)
    {
        var page = await ReadChangesCore(actor, customer, rawAfter, rawLimit, false, ct);
        return new(page.CustomerId, page.CurrentRevision, page.NextRevision, page.HasMore, page.RefreshRequired,
            page.Events.Select(e => new InventoryChangeEvent(e.Id, e.Actor, e.Action, e.ResourceId, e.RevisionBefore,
                e.RevisionAfter, e.OccurredAt, e.Context)).ToArray());
    }

    public Task<InventoryDetailedChanges> ReadDetailedChanges(Actor actor, Guid customer, string? rawAfter, string? rawLimit, CancellationToken ct)
        => ReadChangesCore(actor, customer, rawAfter, rawLimit, true, ct);

    private async Task<InventoryDetailedChanges> ReadChangesCore(Actor actor, Guid customer, string? rawAfter, string? rawLimit, bool includeDetails, CancellationToken ct)
    {
        await using var db = await source.OpenConnectionAsync(ct);
        await using var tx = await db.BeginTransactionAsync(System.Data.IsolationLevel.ReadCommitted, ct);
        // Middleware authenticates the cookie; preliminary Can hides the target. Do not lock actor before customer:
        // inventory writers acquire customer then actor/session, so use the same order here.
        await RequireRead(db, tx, actor, customer, ct);
        long current;
        // Inventory commands and customer rename require UPDATE on this row. Keep it stable through the event read.
        await using (var command = Cmd(db, tx, "SELECT revision FROM customer WHERE systemhaus_id=@house AND id=@customer FOR SHARE",
            ("house", actor.HouseId), ("customer", customer)))
            current = await command.ExecuteScalarAsync(ct) is long value ? value : throw new DomainError(404, "not_found");
        // ReadCommitted observes grants revoked while waiting, and the session helper rechecks wall-clock expiry.
        await PostgresStore.RequireCurrentSession(db, tx, actor, ct);
        await RequireRead(db, tx, actor, customer, ct);
        int limit = 50;
        if (rawLimit is not null && (!int.TryParse(rawLimit, NumberStyles.None, CultureInfo.InvariantCulture, out limit) || limit is < 1 or > 100))
            throw new DomainError(422, "request_invalid");
        long after = current;
        if (rawAfter is not null && (!long.TryParse(rawAfter, NumberStyles.None, CultureInfo.InvariantCulture, out after) || after < 1))
            throw new DomainError(422, "request_invalid");
        InventoryDetailedChanges Result(bool refresh = false) => new(customer, current, current, false, refresh, []);
        if (after >= current)
        {
            await PostgresStore.RequireCurrentSession(db, tx, actor, ct);
            await RequireRead(db, tx, actor, customer, ct);
            await tx.CommitAsync(ct);
            return Result(after > current);
        }
        int count = (int)Math.Min(current - after, limit + 1L);
        var revisions = Enumerable.Range(1, count).Select(i => after + i).ToArray();
        string[] nexts = revisions.Select(r => r.ToString(CultureInfo.InvariantCulture)).ToArray();
        string[] priors = revisions.Select(r => (r - 1).ToString(CultureInfo.InvariantCulture)).ToArray();
        var events = new Dictionary<long, InventoryDetailedChangeEvent>();
        bool invalid = false;
        string beforePort = ChangeData("a.before_json", true), afterPort = ChangeData("a.after_json", true);
        string beforeConnection = ChangeData("a.before_json", false), afterConnection = ChangeData("a.after_json", false);
        string beforeDetails = includeDetails ? ChangeDetailsData("a.before_json") : "NULL::jsonb";
        string afterDetails = includeDetails ? ChangeDetailsData("a.after_json") : "NULL::jsonb";
        // One bounded page and lookahead. Both wrapper revisions participate so a corrupt side cannot hide its counterpart.
        await using (var command = Cmd(db, tx, $"""
            SELECT a.id,a.actor_id,u.username,a.action,a.resource_id,a.occurred_at,
                jsonb_typeof(a.before_json),jsonb_typeof(a.after_json),
                {ChangeText("a.before_json", "customerId") }::text,{ChangeText("a.after_json", "customerId")}::text,
                jsonb_typeof(a.before_json->'revision'),a.before_json->>'revision',
                jsonb_typeof(a.after_json->'revision'),a.after_json->>'revision',
                CASE WHEN a.action IN ('inventory.ports.update','inventory.operations.compensate') THEN {beforePort}
                    WHEN a.action IN ('inventory.connections.create','inventory.connections.createBatch','inventory.connections.update','inventory.connections.disconnect','inventory.connections.reconnect') THEN {beforeConnection} ELSE NULL END,
                CASE WHEN a.action IN ('inventory.ports.update','inventory.operations.compensate') THEN {afterPort}
                    WHEN a.action IN ('inventory.connections.create','inventory.connections.createBatch','inventory.connections.update','inventory.connections.disconnect','inventory.connections.reconnect') THEN {afterConnection} ELSE NULL END,
                {beforeDetails},{afterDetails}
            FROM audit_event a LEFT JOIN app_user u ON u.systemhaus_id=a.systemhaus_id AND u.id=a.actor_id
            WHERE a.systemhaus_id=@house AND a.action<>'operation.cancel'
                AND (a.before_json->>'customerId'=@customerText OR a.after_json->>'customerId'=@customerText)
                AND (a.after_json->>'revision'=ANY(@nexts) OR a.before_json->>'revision'=ANY(@priors))
            ORDER BY a.id LIMIT @take
            """, ("house", actor.HouseId), ("customerText", customer.ToString("D")),
            ("nexts", nexts), ("priors", priors), ("take", count * 2 + 1)))
        await using (var rows = await command.ExecuteReaderAsync(ct))
        {
            while (await rows.ReadAsync(ct))
            {
                string? Cell(int i) => rows.IsDBNull(i) ? null : rows.GetString(i);
                bool WrapperId(int i) => Cell(i) is { } text && text.Length == 38
                    && Guid.TryParseExact(text[1..^1], "D", out Guid id) && id == customer;
                string action = rows.GetString(3);
                if (rows.GetGuid(0) == Guid.Empty || rows.GetGuid(1) == Guid.Empty || !ChangeActions.Contains(action)
                    || Cell(6) != "object" || Cell(7) != "object" || !WrapperId(8) || !WrapperId(9)
                    || Cell(10) != "number" || Cell(12) != "number"
                    || !long.TryParse(Cell(11), NumberStyles.None, CultureInfo.InvariantCulture, out long previous) || previous < 1
                    || !long.TryParse(Cell(13), NumberStyles.None, CultureInfo.InvariantCulture, out long next)
                    || next <= after || next > current || next - previous != 1 || !revisions.Contains(next))
                { invalid = true; continue; }
                Guid? resource = rows.GetGuid(4) is var resourceId && resourceId != Guid.Empty ? resourceId : null;
                var context = ReadChangeContext(action, resource, actor.HouseId, customer, Cell(14), Cell(15));
                var details = includeDetails ? ReadChangeDetails(action, resource, actor.HouseId, customer, Cell(16), Cell(17)) : NoChangeDetails();
                var item = new InventoryDetailedChangeEvent(rows.GetGuid(0), new(rows.GetGuid(1), Cell(2)), action, resource,
                    previous, next, rows.GetDateTime(5), context, details);
                if (!events.TryAdd(next, item)) invalid = true;
            }
        }
        invalid |= revisions.Any(r => !events.ContainsKey(r));
        await PostgresStore.RequireCurrentSession(db, tx, actor, ct);
        await RequireRead(db, tx, actor, customer, ct);
        await tx.CommitAsync(ct);
        if (invalid) return Result(true);
        var page = revisions.Take(limit).Select(r => events[r]).ToArray();
        return new(customer, current, page[^1].RevisionAfter, count > limit, false, page);
    }

    private static InventoryChangeContext ReadChangeContext(string action, Guid? resource, Guid house, Guid customer, string? before, string? after)
    {
        if (before is null || after is null || resource is null || before.Length > 262144 || after.Length > 262144) return NoChangeContext();
        try
        {
            using var a = JsonDocument.Parse(before, new JsonDocumentOptions { MaxDepth = 8 });
            using var b = JsonDocument.Parse(after, new JsonDocumentOptions { MaxDepth = 8 });
            void Require(bool valid) { if (!valid) throw new JsonException(); }
            Guid Id(JsonElement value, string field)
            {
                var text = value.GetProperty(field).GetString();
                Require(text?.Length == 36 && Guid.TryParseExact(text, "D", out var parsed) && parsed != Guid.Empty);
                return Guid.ParseExact(text!, "D");
            }
            JsonElement[] Items(JsonElement value, string kind, int minimum, int maximum)
            {
                Require(value.GetProperty("kind").GetString() == kind);
                var items = value.GetProperty("items").EnumerateArray().ToArray();
                Require(items.Length >= minimum && items.Length <= maximum);
                if (kind == "array") Require(value.GetProperty("count").GetInt32() == items.Length);
                foreach (var item in items) Require(Id(item, "houseId") == house && Id(item, "customerId") == customer);
                return items;
            }
            if (action is "inventory.ports.update" or "inventory.operations.compensate")
            {
                InventoryChangedPort[] Ports(JsonElement value) => Items(value, "array", 1, 256).Select(p =>
                {
                    int gn = p.GetProperty("gn").GetInt32(); string type = p.GetProperty("type").GetString()!;
                    Require(gn > 0 && InventoryRules.PortTypes.Contains(type, StringComparer.Ordinal));
                    return new InventoryChangedPort(Id(p, "id"), Id(p, "deviceId"), Id(p, "groupId"), type, gn);
                }).ToArray();
                var old = Ports(a.RootElement); var next = Ports(b.RootElement);
                Require(old.Length == next.Length && old.Select(p => p.Id).Distinct().Count() == old.Length
                    && old.All(p => p.DeviceId == resource && p.GroupId == old[0].GroupId && InventoryRules.Family(p.Type) == InventoryRules.Family(old[0].Type)));
                for (int i = 0; i < old.Length; i++) Require(old[i].Id == next[i].Id && old[i].DeviceId == next[i].DeviceId
                    && old[i].GroupId == next[i].GroupId && old[i].Gn == next[i].Gn && InventoryRules.Family(old[i].Type) == InventoryRules.Family(next[i].Type));
                return new("captured", old, next, [], []);
            }
            InventoryChangedConnection[] Connections(JsonElement value, string kind, int minimum, int maximum)
            {
                var items = Items(value, kind, minimum, maximum).Select(p => new InventoryChangedConnection(Id(p, "id"), Id(p, "fromPortId"), Id(p, "toPortId"))).ToArray();
                Require(items.Select(p => p.Id).Distinct().Count() == items.Length
                    && items.SelectMany(p => new[] { p.FromPortId, p.ToPortId }).Distinct().Count() == items.Length * 2);
                return items;
            }
            InventoryChangedConnection[] prior, current;
            if (action is "inventory.connections.create" or "inventory.connections.createBatch")
            {
                Items(a.RootElement, "null", 0, 0);
                prior = []; current = Connections(b.RootElement, "array", 1, action == "inventory.connections.create" ? 1 : 128);
            }
            else if (action == "inventory.connections.disconnect")
            {
                prior = Connections(a.RootElement, "object", 1, 1); current = []; Items(b.RootElement, "null", 0, 0);
            }
            else
            {
                prior = Connections(a.RootElement, "object", 1, 1); current = Connections(b.RootElement, "object", 1, 1);
                Require(prior[0].Id == current[0].Id);
                bool first = prior[0].FromPortId == current[0].FromPortId, second = prior[0].ToPortId == current[0].ToPortId;
                Require(action == "inventory.connections.update" ? first && second : action == "inventory.connections.reconnect" && (first || second));
            }
            Require((prior.Length == 0 ? current[0].Id : prior[0].Id) == resource);
            return new("captured", [], [], prior, current);
        }
        catch (Exception e) when (e is JsonException or InvalidOperationException or FormatException or KeyNotFoundException or OverflowException or ArgumentException)
        { return NoChangeContext(); }
    }
}
