using System.Globalization;
using System.Text.Json;
using System.Text.Json.Serialization;
using Npgsql;
using RackClick.Domain;

namespace RackClick.Server;

public sealed record UserPreferencesSnapshot(string Kind, Guid OwnerId, long Revision, string? Language, string? Theme);
public sealed record UserPreferenceChange(string Key, string Value, bool Changed);
public sealed record UserPreferenceResult(string Kind, Guid OwnerId, long Revision, Guid RequestId, Guid OperationId, UserPreferenceChange Result);
public sealed record UserPreferenceStatus(string State, Guid OwnerId, long Revision, Guid RequestId, UserPreferenceResult? Operation);

/// <summary>Session-owned settings with an independent revision, journal and cancellation fences.</summary>
public sealed class UserPreferences(NpgsqlDataSource source)
{
    public const long MaximumRevision = 9007199254740991;
    private const string Kind = "userPreferences";
    private static readonly JsonSerializerOptions Json = new(JsonSerializerDefaults.Web)
        { UnmappedMemberHandling = JsonUnmappedMemberHandling.Disallow };
    private sealed record Intent(string Key, string Value);
    private sealed record Terminal(string Hash, string State, string Result, int Version, string Sha256, Guid OperationId, long Revision);
    private sealed record Fence(string Kind, string State, Guid OwnerId, Guid RequestId, Guid OperationId, long Revision, object? Operation);

    public static string ETag(long revision) => $"\"preferences-{revision.ToString(CultureInfo.InvariantCulture)}\"";
    public static long ParseRevision(string? etag)
    {
        if (string.IsNullOrWhiteSpace(etag)) throw new DomainError(428, "revision_required");
        if (!etag.StartsWith("\"preferences-", StringComparison.Ordinal) || !etag.EndsWith('"'))
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
    private static bool Choice(string? key, string? value) => key switch
    {
        "language" => value is "en" or "de" or "es",
        "theme" => value is "dark" or "light",
        _ => false
    };
    private static Intent ParseIntent(JsonElement input)
    {
        if (!Shape(input, "key", "value") || input.GetProperty("key").ValueKind != JsonValueKind.String
            || input.GetProperty("value").ValueKind != JsonValueKind.String)
            throw new DomainError(422, "request_invalid");
        string key = input.GetProperty("key").GetString()!, value = input.GetProperty("value").GetString()!;
        if (!Choice(key, value)) throw new DomainError(422, "request_invalid");
        return new(key, value);
    }
    private static Task<int> LockAggregate(NpgsqlConnection db, NpgsqlTransaction tx, Actor actor, bool shared, CancellationToken ct)
        => Exec(db, tx, shared ? "SELECT pg_advisory_xact_lock_shared(hashtextextended(@key,0))" : "SELECT pg_advisory_xact_lock(hashtextextended(@key,0))", ct,
            ("key", $"RackClick/user-preferences/{actor.HouseId:D}/{actor.Id:D}"));
    private static Task<int> LockRequest(NpgsqlConnection db, NpgsqlTransaction tx, Actor actor, Guid requestId, CancellationToken ct)
        => Exec(db, tx, "SELECT pg_advisory_xact_lock(hashtextextended(@key,0))", ct,
            ("key", $"RackClick/user-preference-operation/{actor.HouseId:D}/{actor.Id:D}/{requestId:D}"));
    private static async Task<UserPreferencesSnapshot> Snapshot(NpgsqlConnection db, NpgsqlTransaction tx, Actor actor, CancellationToken ct)
    {
        await using var command = Cmd(db, tx, "SELECT revision,language,theme FROM user_preferences WHERE systemhaus_id=@house AND owner_id=@owner",
            ("house", actor.HouseId), ("owner", actor.Id));
        await using var row = await command.ExecuteReaderAsync(ct);
        return await row.ReadAsync(ct)
            ? new(Kind, actor.Id, row.GetInt64(0), row.IsDBNull(1) ? null : row.GetString(1), row.IsDBNull(2) ? null : row.GetString(2))
            : new(Kind, actor.Id, 0, null, null);
    }
    private static async Task<Terminal?> Find(NpgsqlConnection db, NpgsqlTransaction tx, Actor actor, Guid requestId, CancellationToken ct)
    {
        await using var command = Cmd(db, tx, "SELECT request_hash,state,result_json,result_version,result_sha256,operation_id,revision FROM user_preference_operation WHERE systemhaus_id=@house AND owner_id=@owner AND request_id=@request",
            ("house", actor.HouseId), ("owner", actor.Id), ("request", requestId));
        await using var row = await command.ExecuteReaderAsync(ct);
        return await row.ReadAsync(ct) ? new(row.GetString(0), row.GetString(1), row.GetString(2), row.GetInt32(3), row.GetString(4), row.GetGuid(5), row.GetInt64(6)) : null;
    }
    private static UserPreferenceResult? ValidateTerminal(Terminal terminal, Actor actor, Guid requestId)
    {
        try
        {
            if (terminal.Version != 1 || terminal.Revision < 0 || terminal.Revision > MaximumRevision || terminal.OperationId == Guid.Empty
                || terminal.Hash.Length != 64 || terminal.Hash.Any(c => c is not (>= '0' and <= '9' or >= 'A' and <= 'F'))
                || !string.Equals(terminal.Sha256, Secrets.Digest(terminal.Result), StringComparison.Ordinal))
                throw new DomainError(409, "preferences_conflict");
            using var document = JsonDocument.Parse(terminal.Result);
            var root = document.RootElement;
            if (terminal.State == "committed")
            {
                if (!Shape(root, "kind", "ownerId", "revision", "requestId", "operationId", "result")
                    || !Shape(root.GetProperty("result"), "key", "value", "changed")
                    || root.GetProperty("result").GetProperty("changed").ValueKind is not (JsonValueKind.True or JsonValueKind.False))
                    throw new DomainError(409, "preferences_conflict");
                var result = JsonSerializer.Deserialize<UserPreferenceResult>(terminal.Result, Json);
                if (result is null || result.Kind != Kind || result.OwnerId != actor.Id || result.RequestId != requestId
                    || result.OperationId != terminal.OperationId || result.Revision != terminal.Revision || result.Result is null
                    || !Choice(result.Result.Key, result.Result.Value)) throw new DomainError(409, "preferences_conflict");
                return result;
            }
            if (terminal.State != "cancelled" || !Shape(root, "kind", "state", "ownerId", "requestId", "operationId", "revision", "operation")
                || root.GetProperty("operation").ValueKind != JsonValueKind.Null) throw new DomainError(409, "preferences_conflict");
            var fence = JsonSerializer.Deserialize<Fence>(terminal.Result, Json);
            if (fence is null || fence.Kind != Kind || fence.State != "cancelled" || fence.OwnerId != actor.Id
                || fence.RequestId != requestId || fence.OperationId != terminal.OperationId || fence.Revision != terminal.Revision)
                throw new DomainError(409, "preferences_conflict");
            return null;
        }
        catch (JsonException) { throw new DomainError(409, "preferences_conflict"); }
    }
    private static UserPreferenceStatus Outcome(Terminal? terminal, Actor actor, Guid requestId, long revision)
        => new(terminal?.State ?? "notRecorded", actor.Id, revision, requestId,
            terminal is null ? null : ValidateTerminal(terminal, actor, requestId));

    public async Task<UserPreferencesSnapshot> Read(Actor actor, CancellationToken ct)
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
    public async Task<UserPreferenceStatus> Status(Actor actor, Guid requestId, CancellationToken ct)
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
    public async Task<UserPreferenceResult> Set(Actor actor, JsonElement input, long expected, Guid requestId, IQueryCollection query, CancellationToken ct)
        => (await Execute(actor, input, expected, requestId, query, false, ct)).Operation
            ?? throw new DomainError(409, "operation_cancelled");
    public Task<UserPreferenceStatus> Cancel(Actor actor, JsonElement input, long expected, Guid requestId, IQueryCollection query, CancellationToken ct)
        => Execute(actor, input, expected, requestId, query, true, ct);

    private async Task<UserPreferenceStatus> Execute(Actor actor, JsonElement input, long expected, Guid requestId, IQueryCollection query, bool cancel, CancellationToken ct)
    {
        var intent = ParseIntent(input);
        if (query.Count != 0) throw new DomainError(422, "request_invalid");
        if (requestId == Guid.Empty) throw new DomainError(422, "request_id_invalid");
        if (expected < 0 || expected > MaximumRevision) throw new DomainError(422, "revision_invalid");
        string digest = Secrets.Digest(JsonSerializer.Serialize(new { family = Kind, houseId = actor.HouseId, ownerId = actor.Id,
            intent.Key, intent.Value, expectedPersonalRevision = expected }, Json));
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
            UserPreferenceResult? committed = null;
            if (cancel)
            {
                stored = JsonSerializer.Serialize(new Fence(Kind, "cancelled", actor.Id, requestId, operationId, revision, null), Json);
                before = JsonSerializer.Serialize(new { ownerId = actor.Id, revision }, Json);
                after = JsonSerializer.Serialize(new { ownerId = actor.Id, state = "cancelled", revision, intent.Key, intent.Value, expectedPersonalRevision = expected }, Json);
            }
            else
            {
                Revisions.Require(expected, revision);
                string? previous = intent.Key == "language" ? snapshot.Language : snapshot.Theme;
                bool changed = previous != intent.Value;
                before = JsonSerializer.Serialize(new { ownerId = actor.Id, revision, intent.Key, value = previous }, Json);
                if (changed)
                {
                    if (revision == MaximumRevision) throw new DomainError(409, "preferences_revision_exhausted");
                    await Exec(db, tx, "INSERT INTO user_preferences(systemhaus_id,owner_id) VALUES(@house,@owner) ON CONFLICT DO NOTHING", ct,
                        ("house", actor.HouseId), ("owner", actor.Id));
                    string column = intent.Key == "language" ? "language" : "theme"; // Closed enum, never user SQL.
                    if (await Exec(db, tx, $"UPDATE user_preferences SET {column}=@value,revision=@next WHERE systemhaus_id=@house AND owner_id=@owner AND revision=@before", ct,
                        ("value", intent.Value), ("next", revision + 1), ("house", actor.HouseId), ("owner", actor.Id), ("before", revision)) != 1)
                        throw new DomainError(409, "preferences_conflict");
                    revision++;
                }
                committed = new(Kind, actor.Id, revision, requestId, operationId, new(intent.Key, intent.Value, changed));
                stored = JsonSerializer.Serialize(committed, Json);
                after = JsonSerializer.Serialize(new { ownerId = actor.Id, revision, intent.Key, intent.Value, changed }, Json);
            }
            string state = cancel ? "cancelled" : "committed";
            await Exec(db, tx, "INSERT INTO audit_event(id,systemhaus_id,actor_id,request_id,action,resource_id,before_json,after_json) VALUES(@id,@house,@owner,@request,@action,@owner,CAST(@before AS jsonb),CAST(@after AS jsonb))", ct,
                ("id", operationId), ("house", actor.HouseId), ("owner", actor.Id), ("request", requestId),
                ("action", cancel ? "user.preference.set.cancel" : "user.preference.set"), ("before", before), ("after", after));
            await Exec(db, tx, "INSERT INTO user_preference_operation(systemhaus_id,owner_id,request_id,request_hash,state,operation_id,revision,result_version,result_sha256,result_json) VALUES(@house,@owner,@request,@hash,@state,@id,@revision,1,@sha,@result)", ct,
                ("house", actor.HouseId), ("owner", actor.Id), ("request", requestId), ("hash", digest), ("state", state), ("id", operationId), ("revision", revision),
                ("sha", Secrets.Digest(stored)), ("result", stored));
            await PostgresStore.RequireCurrentSession(db, tx, actor, ct);
            await tx.CommitAsync(ct);
            return new(state, actor.Id, revision, requestId, committed);
        }
        catch (PostgresException e) when (e.SqlState is "23503" or "23505" or "23514")
        { throw new DomainError(409, "preferences_conflict"); }
    }
}
