using System.Globalization;
using System.Text.Json;
using System.Text.Json.Serialization;
using Npgsql;
using RackClick.Domain;

namespace RackClick.Server;

public sealed record UserPortColorsSnapshot(string Kind, Guid OwnerId, long Revision, SortedDictionary<string, string> Colors);
public sealed record UserPortColorChange(SortedDictionary<string, string> Colors, bool Changed);
public sealed record UserPortColorResult(string Kind, Guid OwnerId, long Revision, Guid RequestId, Guid OperationId, UserPortColorChange Result);
public sealed record UserPortColorStatus(string State, Guid OwnerId, long Revision, Guid RequestId, UserPortColorResult? Operation);

/// <summary>Session-owned port type overrides with an independent revision, journal and cancellation fences.</summary>
public sealed class UserPortColors(NpgsqlDataSource source)
{
    public const long MaximumRevision = 9007199254740991;
    private const string Kind = "userPortColors";
    private static readonly JsonSerializerOptions Json = new(JsonSerializerDefaults.Web)
        { UnmappedMemberHandling = JsonUnmappedMemberHandling.Disallow };
    private sealed record Intent(SortedDictionary<string, string> Colors);
    private sealed record Terminal(string Hash, string State, string Result, int Version, string Sha256, Guid OperationId, long Revision);
    private sealed record Fence(string Kind, string State, Guid OwnerId, Guid RequestId, Guid OperationId, long Revision, object? Operation);

    public static string ETag(long revision) => $"\"port-colors-{revision.ToString(CultureInfo.InvariantCulture)}\"";
    public static long ParseRevision(string? etag)
    {
        if (string.IsNullOrWhiteSpace(etag)) throw new DomainError(428, "revision_required");
        if (!etag.StartsWith("\"port-colors-", StringComparison.Ordinal) || !etag.EndsWith('"'))
            throw new DomainError(422, "revision_invalid");
        string digits = etag[13..^1];
        if (!long.TryParse(digits, NumberStyles.None, CultureInfo.InvariantCulture, out long revision)
            || revision < 0 || revision > MaximumRevision || ETag(revision) != etag)
            throw new DomainError(422, "revision_invalid");
        return revision;
    }

    public static void RequireEmptyRead(HttpRequest request)
    {
        // Reject a body even when it is chunked or the endpoint has no JSON binder.
        if (request.Query.Count != 0 || request.ContentLength is > 0 || request.Headers.TransferEncoding.Count != 0)
            throw new DomainError(422, "request_invalid");
    }

    public static Guid ParseRequestId(string? value) => Guid.TryParse(value, out Guid id) && id != Guid.Empty
        ? id : throw new DomainError(422, "request_id_invalid");

    private static NpgsqlCommand Cmd(NpgsqlConnection db, NpgsqlTransaction tx, string sql, params (string, object)[] values)
    {
        var command = new NpgsqlCommand(sql, db, tx);
        foreach (var (name, value) in values) command.Parameters.AddWithValue(name, value);
        return command;
    }
    private static async Task<int> Exec(NpgsqlConnection db, NpgsqlTransaction tx, string sql, CancellationToken ct, params (string, object)[] values)
    {
        await using var command = Cmd(db, tx, sql, values);
        return await command.ExecuteNonQueryAsync(ct);
    }
    private static bool Shape(JsonElement input, params string[] keys)
    {
        if (input.ValueKind != JsonValueKind.Object) return false;
        var properties = input.EnumerateObject().ToArray();
        return properties.Length == keys.Length && properties.Select(p => p.Name).Distinct(StringComparer.Ordinal).Count() == keys.Length
            && properties.All(p => keys.Contains(p.Name, StringComparer.Ordinal));
    }
    private static readonly HashSet<string> AllowedTypes = new(StringComparer.Ordinal)
        { "rj45", "rj45_poe", "sfp", "sfp28", "qsfp", "mgmt", "console", "power", "usb_a", "usb_c" };
    private static SortedDictionary<string, string> ParseColors(JsonElement input)
    {
        if (input.ValueKind != JsonValueKind.Object) throw new DomainError(422, "request_invalid");
        var colors = new SortedDictionary<string, string>(StringComparer.Ordinal);
        foreach (var property in input.EnumerateObject())
        {
            if (!AllowedTypes.Contains(property.Name) || property.Value.ValueKind != JsonValueKind.String)
                throw new DomainError(422, "request_invalid");
            string value = property.Value.GetString()!;
            if (value.Length != 7 || value[0] != '#' || value.Skip(1).Any(c => c is not (>= '0' and <= '9' or >= 'a' and <= 'f'))
                || !colors.TryAdd(property.Name, value)) throw new DomainError(422, "request_invalid");
        }
        return colors;
    }
    private static Intent ParseIntent(JsonElement input)
    {
        if (!Shape(input, "colors")) throw new DomainError(422, "request_invalid");
        return new(ParseColors(input.GetProperty("colors")));
    }
    private static bool SameColors(SortedDictionary<string, string> left, SortedDictionary<string, string> right)
        => left.Count == right.Count && left.All(pair => right.TryGetValue(pair.Key, out var value) && value == pair.Value);
    private static Task<int> LockAggregate(NpgsqlConnection db, NpgsqlTransaction tx, Actor actor, bool shared, CancellationToken ct)
        => Exec(db, tx, shared ? "SELECT pg_advisory_xact_lock_shared(hashtextextended(@key,0))" : "SELECT pg_advisory_xact_lock(hashtextextended(@key,0))", ct,
            ("key", $"RackClick/user-port-colors/{actor.HouseId:D}/{actor.Id:D}"));
    private static Task<int> LockRequest(NpgsqlConnection db, NpgsqlTransaction tx, Actor actor, Guid requestId, CancellationToken ct)
        => Exec(db, tx, "SELECT pg_advisory_xact_lock(hashtextextended(@key,0))", ct,
            ("key", $"RackClick/user-port-color-operation/{actor.HouseId:D}/{actor.Id:D}/{requestId:D}"));
    private static async Task<UserPortColorsSnapshot> Snapshot(NpgsqlConnection db, NpgsqlTransaction tx, Actor actor, CancellationToken ct)
    {
        await using var command = Cmd(db, tx, "SELECT revision,colors::text FROM user_port_colors WHERE systemhaus_id=@house AND owner_id=@owner",
            ("house", actor.HouseId), ("owner", actor.Id));
        await using var row = await command.ExecuteReaderAsync(ct);
        if (!await row.ReadAsync(ct)) return new(Kind, actor.Id, 0, new(StringComparer.Ordinal));
        try
        {
            using var document = JsonDocument.Parse(row.GetString(1));
            return new(Kind, actor.Id, row.GetInt64(0), ParseColors(document.RootElement));
        }
        catch (Exception e) when (e is JsonException or DomainError) { throw new DomainError(409, "port_colors_conflict"); }
    }
    private static async Task<Terminal?> Find(NpgsqlConnection db, NpgsqlTransaction tx, Actor actor, Guid requestId, CancellationToken ct)
    {
        await using var command = Cmd(db, tx, "SELECT request_hash,state,result_json,result_version,result_sha256,operation_id,revision FROM user_port_color_operation WHERE systemhaus_id=@house AND owner_id=@owner AND request_id=@request",
            ("house", actor.HouseId), ("owner", actor.Id), ("request", requestId));
        await using var row = await command.ExecuteReaderAsync(ct);
        return await row.ReadAsync(ct) ? new(row.GetString(0), row.GetString(1), row.GetString(2), row.GetInt32(3), row.GetString(4), row.GetGuid(5), row.GetInt64(6)) : null;
    }
    private static UserPortColorResult? ValidateTerminal(Terminal terminal, Actor actor, Guid requestId)
    {
        try
        {
            if (terminal.Version != 1 || terminal.Revision < 0 || terminal.Revision > MaximumRevision || terminal.OperationId == Guid.Empty
                || terminal.Hash.Length != 64 || terminal.Hash.Any(c => c is not (>= '0' and <= '9' or >= 'A' and <= 'F'))
                || !string.Equals(terminal.Sha256, Secrets.Digest(terminal.Result), StringComparison.Ordinal))
                throw new DomainError(409, "port_colors_conflict");
            using var document = JsonDocument.Parse(terminal.Result);
            var root = document.RootElement;
            if (terminal.State == "committed")
            {
                if (!Shape(root, "kind", "ownerId", "revision", "requestId", "operationId", "result")
                    || !Shape(root.GetProperty("result"), "colors", "changed")
                    || root.GetProperty("result").GetProperty("changed").ValueKind is not (JsonValueKind.True or JsonValueKind.False))
                    throw new DomainError(409, "port_colors_conflict");
                var result = JsonSerializer.Deserialize<UserPortColorResult>(terminal.Result, Json);
                if (result is null || result.Kind != Kind || result.OwnerId != actor.Id || result.RequestId != requestId
                    || result.OperationId != terminal.OperationId || result.Revision != terminal.Revision || result.Result is null
                    || result.Result.Colors is null) throw new DomainError(409, "port_colors_conflict");
                try { ParseColors(root.GetProperty("result").GetProperty("colors")); }
                catch (DomainError) { throw new DomainError(409, "port_colors_conflict"); }
                return result;
            }
            if (terminal.State != "cancelled" || !Shape(root, "kind", "state", "ownerId", "requestId", "operationId", "revision", "operation")
                || root.GetProperty("operation").ValueKind != JsonValueKind.Null) throw new DomainError(409, "port_colors_conflict");
            var fence = JsonSerializer.Deserialize<Fence>(terminal.Result, Json);
            if (fence is null || fence.Kind != Kind || fence.State != "cancelled" || fence.OwnerId != actor.Id
                || fence.RequestId != requestId || fence.OperationId != terminal.OperationId || fence.Revision != terminal.Revision)
                throw new DomainError(409, "port_colors_conflict");
            return null;
        }
        catch (JsonException) { throw new DomainError(409, "port_colors_conflict"); }
    }
    private static UserPortColorStatus Outcome(Terminal? terminal, Actor actor, Guid requestId, long revision)
        => new(terminal?.State ?? "notRecorded", actor.Id, revision, requestId,
            terminal is null ? null : ValidateTerminal(terminal, actor, requestId));

    public async Task<UserPortColorsSnapshot> Read(Actor actor, CancellationToken ct)
    {
        await using var db = await source.OpenConnectionAsync(ct);
        await using var tx = await db.BeginTransactionAsync(System.Data.IsolationLevel.ReadCommitted, ct);
        await LockAggregate(db, tx, actor, true, ct);
        await PostgresStore.RequireCurrentSession(db, tx, actor, ct);
        var result = await Snapshot(db, tx, actor, ct);
        await PostgresStore.RequireCurrentSession(db, tx, actor, ct);
        await tx.CommitAsync(ct);
        return result;
    }
    public async Task<UserPortColorStatus> Status(Actor actor, Guid requestId, CancellationToken ct)
    {
        if (requestId == Guid.Empty) throw new DomainError(422, "request_id_invalid");
        await using var db = await source.OpenConnectionAsync(ct);
        await using var tx = await db.BeginTransactionAsync(System.Data.IsolationLevel.ReadCommitted, ct);
        await LockRequest(db, tx, actor, requestId, ct);
        await LockAggregate(db, tx, actor, true, ct);
        await PostgresStore.RequireCurrentSession(db, tx, actor, ct);
        var result = Outcome(await Find(db, tx, actor, requestId, ct), actor, requestId, (await Snapshot(db, tx, actor, ct)).Revision);
        await PostgresStore.RequireCurrentSession(db, tx, actor, ct);
        await tx.CommitAsync(ct);
        return result;
    }
    public async Task<UserPortColorResult> Set(Actor actor, JsonElement input, long expected, Guid requestId, IQueryCollection query, CancellationToken ct)
        => (await Execute(actor, input, expected, requestId, query, false, ct)).Operation
            ?? throw new DomainError(409, "operation_cancelled");
    public Task<UserPortColorStatus> Cancel(Actor actor, JsonElement input, long expected, Guid requestId, IQueryCollection query, CancellationToken ct)
        => Execute(actor, input, expected, requestId, query, true, ct);

    private async Task<UserPortColorStatus> Execute(Actor actor, JsonElement input, long expected, Guid requestId, IQueryCollection query, bool cancel, CancellationToken ct)
    {
        var intent = ParseIntent(input);
        if (query.Count != 0) throw new DomainError(422, "request_invalid");
        if (requestId == Guid.Empty) throw new DomainError(422, "request_id_invalid");
        if (expected < 0 || expected > MaximumRevision) throw new DomainError(422, "revision_invalid");
        string digest = Secrets.Digest(JsonSerializer.Serialize(new { family = Kind, houseId = actor.HouseId, ownerId = actor.Id,
            intent.Colors, expectedPersonalRevision = expected }, Json));
        await using var db = await source.OpenConnectionAsync(ct);
        await using var tx = await db.BeginTransactionAsync(System.Data.IsolationLevel.ReadCommitted, ct);
        try
        {
            // Never hold session row locks while waiting for this personal aggregate.
            // HTTP already authenticated; revalidate and lock the live session after both waits.
            await LockRequest(db, tx, actor, requestId, ct);
            await LockAggregate(db, tx, actor, false, ct);
            await PostgresStore.RequireCurrentSession(db, tx, actor, ct);
            var snapshot = await Snapshot(db, tx, actor, ct);
            long revision = snapshot.Revision;
            var prior = await Find(db, tx, actor, requestId, ct);
            if (prior is not null)
            {
                if (prior.Hash != digest) throw new DomainError(409, "request_id_reused");
                var replay = Outcome(prior, actor, requestId, revision);
                if (!cancel && prior.State == "cancelled") throw new DomainError(409, "operation_cancelled");
                await PostgresStore.RequireCurrentSession(db, tx, actor, ct);
                await tx.CommitAsync(ct);
                return replay;
            }
            Guid operationId = Guid.NewGuid();
            string stored, before, after;
            UserPortColorResult? committed = null;
            if (cancel)
            {
                stored = JsonSerializer.Serialize(new Fence(Kind, "cancelled", actor.Id, requestId, operationId, revision, null), Json);
                before = JsonSerializer.Serialize(new { ownerId = actor.Id, revision }, Json);
                after = JsonSerializer.Serialize(new { ownerId = actor.Id, state = "cancelled", revision, intent.Colors, expectedPersonalRevision = expected }, Json);
            }
            else
            {
                Revisions.Require(expected, revision);
                bool changed = !SameColors(snapshot.Colors, intent.Colors);
                before = JsonSerializer.Serialize(new { ownerId = actor.Id, revision, colors = snapshot.Colors }, Json);
                if (changed)
                {
                    if (revision == MaximumRevision) throw new DomainError(409, "port_colors_revision_exhausted");
                    await Exec(db, tx, "INSERT INTO user_port_colors(systemhaus_id,owner_id) VALUES(@house,@owner) ON CONFLICT DO NOTHING", ct,
                        ("house", actor.HouseId), ("owner", actor.Id));
                    if (await Exec(db, tx, "UPDATE user_port_colors SET colors=CAST(@colors AS jsonb),revision=@next WHERE systemhaus_id=@house AND owner_id=@owner AND revision=@before", ct,
                        ("colors", JsonSerializer.Serialize(intent.Colors, Json)), ("next", revision + 1), ("house", actor.HouseId), ("owner", actor.Id), ("before", revision)) != 1)
                        throw new DomainError(409, "port_colors_conflict");
                    revision++;
                }
                committed = new(Kind, actor.Id, revision, requestId, operationId, new(intent.Colors, changed));
                stored = JsonSerializer.Serialize(committed, Json);
                after = JsonSerializer.Serialize(new { ownerId = actor.Id, revision, colors = intent.Colors, changed }, Json);
            }
            string state = cancel ? "cancelled" : "committed";
            await Exec(db, tx, "INSERT INTO audit_event(id,systemhaus_id,actor_id,request_id,action,resource_id,before_json,after_json) VALUES(@id,@house,@owner,@request,@action,@owner,CAST(@before AS jsonb),CAST(@after AS jsonb))", ct,
                ("id", operationId), ("house", actor.HouseId), ("owner", actor.Id), ("request", requestId),
                ("action", cancel ? "user.portColors.set.cancel" : "user.portColors.set"), ("before", before), ("after", after));
            await Exec(db, tx, "INSERT INTO user_port_color_operation(systemhaus_id,owner_id,request_id,request_hash,state,operation_id,revision,result_version,result_sha256,result_json) VALUES(@house,@owner,@request,@hash,@state,@id,@revision,1,@sha,@result)", ct,
                ("house", actor.HouseId), ("owner", actor.Id), ("request", requestId), ("hash", digest), ("state", state), ("id", operationId), ("revision", revision),
                ("sha", Secrets.Digest(stored)), ("result", stored));
            await PostgresStore.RequireCurrentSession(db, tx, actor, ct);
            await tx.CommitAsync(ct);
            return new(state, actor.Id, revision, requestId, committed);
        }
        catch (PostgresException e) when (e.SqlState is "23503" or "23505" or "23514")
        { throw new DomainError(409, "port_colors_conflict"); }
    }
}
