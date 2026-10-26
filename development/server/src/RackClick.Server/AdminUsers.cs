using System.Text.Json;
using Npgsql;
using RackClick.Domain;

namespace RackClick.Server;

public sealed record AdminUser(Guid Id, string UserName, bool Active);
public sealed record AdminUsersSnapshot(long Revision, IReadOnlyList<AdminUser> Users);

public sealed partial class PostgresStore
{
    private static string UserCreationDigest(string username, long expected) =>
        Secrets.Digest(JsonSerializer.Serialize(new { action = "user.create", username, expected }, Json));

    private static bool IsUserCreationCancelled(string result) =>
        JsonSerializer.Deserialize<JsonElement>(result).TryGetProperty("state", out var state) && state.GetString() == "cancelled";

    private static string UserCreationOutcome(Guid requestId, string? result) =>
        result is not null && IsUserCreationCancelled(result) ? result :
        JsonSerializer.Serialize(new { requestId, state = result is null ? "notRecorded" : "committed",
            operation = result is null ? (JsonElement?)null : JsonSerializer.Deserialize<JsonElement>(result) }, Json);

    private static async Task RequireSecurity(NpgsqlConnection db, NpgsqlTransaction tx, Actor actor, CancellationToken ct)
    {
        await RequireCurrentSession(db, tx, actor, ct);
        if (!await Can(db, tx, actor, null, Capabilities.SecurityManage, ct)) throw new DomainError(403, "forbidden");
    }

    public async Task<AdminUsersSnapshot> ReadUsers(Actor actor, CancellationToken ct)
    {
        await using var db = await source.OpenConnectionAsync(ct);
        await using var tx = await db.BeginTransactionAsync(System.Data.IsolationLevel.RepeatableRead, ct);
        await RequireSecurity(db, tx, actor, ct);
        await using var revision = Command(db, tx, "SELECT revision FROM systemhaus WHERE id=@house", ("house", actor.HouseId));
        long current = (long)(await revision.ExecuteScalarAsync(ct))!;
        var users = new List<AdminUser>();
        await using (var cmd = Command(db, tx, "SELECT id,username,active FROM app_user WHERE systemhaus_id=@house ORDER BY username,id", ("house", actor.HouseId)))
        await using (var rows = await cmd.ExecuteReaderAsync(ct))
            while (await rows.ReadAsync(ct)) users.Add(new(rows.GetGuid(0), rows.GetString(1), rows.GetBoolean(2)));
        await tx.CommitAsync(ct);
        return new(current, users);
    }

    public async Task<string> UserCreationStatus(Actor actor, Guid requestId, CancellationToken ct)
    {
        await using var db = await source.OpenConnectionAsync(ct);
        await using var tx = await db.BeginTransactionAsync(ct);
        await RequireSecurity(db, tx, actor, ct);
        await using var cmd = Command(db, tx, """
            SELECT o.result_json::text FROM operation o JOIN audit_event a
              ON a.systemhaus_id=o.systemhaus_id AND a.actor_id=o.actor_id AND a.request_id=o.request_id
            WHERE o.systemhaus_id=@house AND o.actor_id=@actor AND o.request_id=@request AND a.action IN ('user.create','user.create.cancel')
            """, ("house", actor.HouseId), ("actor", actor.Id), ("request", requestId));
        var result = await cmd.ExecuteScalarAsync(ct) as string;
        return UserCreationOutcome(requestId, result);
    }

    public async Task<string> CancelUserCreation(Actor actor, string? input, long expected, Guid requestId, CancellationToken ct)
    {
        if (requestId == Guid.Empty) throw new DomainError(422, "request_id_invalid");
        if (expected < 1) throw new DomainError(422, "revision_invalid");
        await using var db = await source.OpenConnectionAsync(ct);
        await using var tx = await db.BeginTransactionAsync(ct);
        await LockOperation(db, tx, actor, requestId, ct);
        await using var house = Command(db, tx, "SELECT revision FROM systemhaus WHERE id=@house FOR UPDATE", ("house", actor.HouseId));
        var revision = await house.ExecuteScalarAsync(ct) as long? ?? throw new DomainError(404, "not_found");
        await RequireSecurity(db, tx, actor, ct);
        string digest;
        try { digest = UserCreationDigest(UserNames.Normalize(input), expected); }
        catch (DomainError error) when (error.Code == "username_invalid")
        {
            // An invalid name can never be created, but a lost validation response
            // still leaves a local intent. Fence its exact metadata under a separate digest.
            digest = Secrets.Digest(JsonSerializer.Serialize(new { action = "user.create.invalidName", input, expected }, Json));
        }
        await OperationCancellation.EnsureNotCanceled(db, tx, actor, requestId, digest, ct);
        await using (var command = Command(db, tx,
            "SELECT request_hash,result_json::text FROM operation WHERE systemhaus_id=@house AND actor_id=@actor AND request_id=@request",
            ("house", actor.HouseId), ("actor", actor.Id), ("request", requestId)))
        await using (var rows = await command.ExecuteReaderAsync(ct))
            if (await rows.ReadAsync(ct))
            {
                if (rows.GetString(0) != digest) throw new DomainError(409, "request_id_reused");
                return UserCreationOutcome(requestId, rows.GetString(1));
            }
        // Stale revisions are intentional: reserve the original key, without rebasing
        // the old intent or undoing a committed account. Creation holds these same locks.
        string result = JsonSerializer.Serialize(new { requestId, state = "cancelled", operation = (object?)null }, Json);
        Guid eventId = Guid.NewGuid();
        await using (var command = Command(db, tx,
            "INSERT INTO operation(systemhaus_id,actor_id,request_id,request_hash,result_json) VALUES(@house,@actor,@request,@hash,CAST(@result AS jsonb))",
            ("house", actor.HouseId), ("actor", actor.Id), ("request", requestId), ("hash", digest), ("result", result)))
            await command.ExecuteNonQueryAsync(ct);
        await using (var command = Command(db, tx, """
            INSERT INTO audit_event(id,systemhaus_id,actor_id,request_id,action,resource_id,before_json,after_json)
            VALUES(@id,@house,@actor,@request,'user.create.cancel',@house,'null'::jsonb,CAST(@after AS jsonb))
            """, ("id", eventId), ("house", actor.HouseId), ("actor", actor.Id), ("request", requestId), ("after", result)))
            await command.ExecuteNonQueryAsync(ct);
        await CaptureUserCreationContext(db, tx, actor, eventId, requestId, actor.HouseId, revision, revision, true, ct);
        await tx.CommitAsync(ct);
        return result;
    }

    public async Task<string> CreateUser(Actor actor, string? input, string? password, long expected, Guid requestId, CancellationToken ct)
    {
        await using var db = await source.OpenConnectionAsync(ct);
        await using var tx = await db.BeginTransactionAsync(ct);
        await LockOperation(db, tx, actor, requestId, ct);
        await using var house = Command(db, tx, "SELECT revision FROM systemhaus WHERE id=@house FOR UPDATE", ("house", actor.HouseId));
        var revision = await house.ExecuteScalarAsync(ct) as long? ?? throw new DomainError(404, "not_found");
        await RequireSecurity(db, tx, actor, ct);
        string username = UserNames.Normalize(input);
        if (password is null || password.Length < 16 || password.Length > 1024) throw new DomainError(422, "password_length");
        if (requestId == Guid.Empty) throw new DomainError(422, "request_id_invalid");
        // No password or fast password digest in operation/audit. Replays verify the salted account hash.
        string digest = UserCreationDigest(username, expected);
        await OperationCancellation.EnsureNotCanceled(db, tx, actor, requestId, digest, ct);
        string? replay = null;
        await using (var cmd = Command(db, tx, "SELECT request_hash,result_json::text FROM operation WHERE systemhaus_id=@house AND actor_id=@actor AND request_id=@request",
            ("house", actor.HouseId), ("actor", actor.Id), ("request", requestId)))
        await using (var rows = await cmd.ExecuteReaderAsync(ct))
            if (await rows.ReadAsync(ct))
            {
                if (rows.GetString(0) != digest) throw new DomainError(409, "request_id_reused");
                replay = rows.GetString(1);
            }
        if (replay is not null)
        {
            if (IsUserCreationCancelled(replay)) throw new DomainError(409, "operation_cancelled");
            Guid id = JsonSerializer.Deserialize<JsonElement>(replay).GetProperty("resource").GetProperty("id").GetGuid();
            await using var hash = Command(db, tx, "SELECT password_hash FROM app_user WHERE id=@id AND systemhaus_id=@house", ("id", id), ("house", actor.HouseId));
            if (!Secrets.PasswordValid(username, await hash.ExecuteScalarAsync(ct) as string, password)) throw new DomainError(409, "request_id_reused");
            return replay;
        }
        Revisions.Require(expected, revision);
        Guid userId = Guid.NewGuid();
        await using (var cmd = Command(db, tx, """
            INSERT INTO app_user(id,systemhaus_id,username,password_hash) VALUES(@id,@house,@name,@hash)
            ON CONFLICT(systemhaus_id,username) DO NOTHING RETURNING id
            """, ("id", userId), ("house", actor.HouseId), ("name", username), ("hash", Secrets.PasswordHash(username, password))))
            if (await cmd.ExecuteScalarAsync(ct) is null) throw new DomainError(409, "username_exists");
        var resource = new AdminUser(userId, username, true);
        long next = checked(revision + 1);
        await using (var cmd = Command(db, tx, "UPDATE systemhaus SET revision=@revision WHERE id=@house", ("revision", next), ("house", actor.HouseId))) await cmd.ExecuteNonQueryAsync(ct);
        string result = JsonSerializer.Serialize(new { resource, systemhausRevision = next, requestId }, Json);
        Guid eventId = Guid.NewGuid();
        await using (var cmd = Command(db, tx, """
            INSERT INTO audit_event(id,systemhaus_id,actor_id,request_id,action,resource_id,before_json,after_json)
            VALUES(@id,@house,@actor,@request,'user.create',@resource,'null'::jsonb,CAST(@after AS jsonb))
            """, ("id", eventId), ("house", actor.HouseId), ("actor", actor.Id), ("request", requestId), ("resource", userId), ("after", JsonSerializer.Serialize(resource, Json)))) await cmd.ExecuteNonQueryAsync(ct);
        await using (var cmd = Command(db, tx, "INSERT INTO operation(systemhaus_id,actor_id,request_id,request_hash,result_json) VALUES(@house,@actor,@request,@hash,CAST(@result AS jsonb))",
            ("house", actor.HouseId), ("actor", actor.Id), ("request", requestId), ("hash", digest), ("result", result))) await cmd.ExecuteNonQueryAsync(ct);
        await CaptureUserCreationContext(db, tx, actor, eventId, requestId, userId, revision, next, false, ct);
        await tx.CommitAsync(ct);
        return result;
    }
}
