using System.Text.Json;
using RackClick.Domain;

namespace RackClick.Server;

public sealed record UserPasswordRequest(string? Password);

public sealed partial class PostgresStore
{
    public async Task<string> UserPasswordStatus(Actor actor, Guid userId, Guid requestId, CancellationToken ct)
    {
        if (userId == Guid.Empty || requestId == Guid.Empty) throw new DomainError(422, "request_invalid");
        await using var db = await source.OpenConnectionAsync(ct);
        await using var tx = await db.BeginTransactionAsync(ct);
        await RequireSecurity(db, tx, actor, ct);
        // The initial FOR SHARE may itself wait on actor Login; evaluate expiry after that wait.
        await RequireSecurity(db, tx, actor, ct);
        await using var command = Command(db, tx, """
            SELECT o.result_json::text FROM operation o JOIN audit_event a
              ON a.systemhaus_id=o.systemhaus_id AND a.actor_id=o.actor_id AND a.request_id=o.request_id
            WHERE o.systemhaus_id=@house AND o.actor_id=@actor AND o.request_id=@request
              AND a.resource_id=@user AND a.action IN ('user.password.reset','user.password.reset.cancel')
            """, ("house", actor.HouseId), ("actor", actor.Id), ("request", requestId), ("user", userId));
        return UserCreationOutcome(requestId, await command.ExecuteScalarAsync(ct) as string);
    }

    public async Task<string> ResetOrCancelUserPassword(Actor actor, Guid userId, string? password,
        bool cancel, long expected, Guid requestId, CancellationToken ct)
    {
        if (requestId == Guid.Empty) throw new DomainError(422, "request_id_invalid");
        if (userId == Guid.Empty) throw new DomainError(422, "request_invalid");
        if (!cancel && (password is null || password.Length < 16 || password.Length > 1024)) throw new DomainError(422, "password_length");
        if (expected < 1) throw new DomainError(422, "revision_invalid");
        await using var db = await source.OpenConnectionAsync(ct);
        await using var tx = await db.BeginTransactionAsync(ct);
        await LockOperation(db, tx, actor, requestId, ct);
        await using var house = Command(db, tx, "SELECT revision FROM systemhaus WHERE id=@house FOR UPDATE", ("house", actor.HouseId));
        long revision = await house.ExecuteScalarAsync(ct) as long? ?? throw new DomainError(404, "not_found");
        await RequireSecurity(db, tx, actor, ct);
        // Cancellation has no later target lock/check: validate again after initial actor lock wait.
        if (cancel) await RequireSecurity(db, tx, actor, ct);
        const string action = "user.password.reset";
        // Only public intent is durable. Password verification uses the current salted account hash.
        string digest = Secrets.Digest(JsonSerializer.Serialize(new { action, userId, expected }, Json));
        await OperationCancellation.EnsureNotCanceled(db, tx, actor, requestId, digest, ct);
        string? replay = null;
        await using (var command = Command(db, tx,
            "SELECT request_hash,result_json::text FROM operation WHERE systemhaus_id=@house AND actor_id=@actor AND request_id=@request",
            ("house", actor.HouseId), ("actor", actor.Id), ("request", requestId)))
        await using (var rows = await command.ExecuteReaderAsync(ct))
            if (await rows.ReadAsync(ct))
            {
                if (rows.GetString(0) != digest) throw new DomainError(409, "request_id_reused");
                replay = rows.GetString(1);
                if (cancel) return UserCreationOutcome(requestId, replay);
                if (IsUserCreationCancelled(replay)) throw new DomainError(409, "operation_cancelled");
            }
        string result, after, before = "null";
        long contextAfter = revision;
        if (cancel)
        {
            // A durable public fence needs neither a password, target nor current revision.
            result = JsonSerializer.Serialize(new { requestId, state = "cancelled", operation = (object?)null }, Json);
            after = result;
        }
        else
        {
            if (replay is null) Revisions.Require(expected, revision);
            AdminUser prior;
            string currentHash;
            // Login and account state share this row lock. No session survives a committed reset.
            await using (var command = Command(db, tx, "SELECT id,username,active,password_hash FROM app_user WHERE systemhaus_id=@house AND id=@user FOR UPDATE",
                ("house", actor.HouseId), ("user", userId)))
            await using (var rows = await command.ExecuteReaderAsync(ct))
            {
                if (!await rows.ReadAsync(ct)) throw new DomainError(404, "not_found");
                prior = new(rows.GetGuid(0), rows.GetString(1), rows.GetBoolean(2));
                currentHash = rows.GetString(3);
            }
            // Revalidate after the last blocking wait, for fresh execution AND committed replay.
            await RequireSecurity(db, tx, actor, ct);
            if (replay is not null)
            {
                if (!Secrets.PasswordValid(prior.UserName, currentHash, password!)) throw new DomainError(409, "request_id_reused");
                return replay;
            }
            before = JsonSerializer.Serialize(prior, Json);
            await using (var command = Command(db, tx,
                "UPDATE app_user SET password_hash=@hash,failed_logins=0,locked_until=NULL WHERE systemhaus_id=@house AND id=@user",
                ("hash", Secrets.PasswordHash(prior.UserName, password!)), ("house", actor.HouseId), ("user", userId)))
                await command.ExecuteNonQueryAsync(ct);
            await using (var command = Command(db, tx, "DELETE FROM app_session WHERE user_id=@user", ("user", userId)))
                await command.ExecuteNonQueryAsync(ct);
            // Un desafío MFA emitido con la contraseña anterior no puede completarse después del reset.
            await MfaStore.RevokePendingChallenges(db, tx, actor.HouseId, userId, ct);
            long next = checked(revision + 1);
            contextAfter = next;
            await using (var command = Command(db, tx, "UPDATE systemhaus SET revision=@next WHERE id=@house", ("next", next), ("house", actor.HouseId)))
                await command.ExecuteNonQueryAsync(ct);
            var resource = new { id = prior.Id, userName = prior.UserName, active = prior.Active, passwordReset = true };
            after = JsonSerializer.Serialize(resource, Json);
            result = JsonSerializer.Serialize(new { resource, systemhausRevision = next, requestId }, Json);
        }
        Guid eventId = Guid.NewGuid();
        await using (var command = Command(db, tx, """
            INSERT INTO audit_event(id,systemhaus_id,actor_id,request_id,action,resource_id,before_json,after_json)
            VALUES(@id,@house,@actor,@request,@action,@user,CAST(@before AS jsonb),CAST(@after AS jsonb))
            """, ("id", eventId), ("house", actor.HouseId), ("actor", actor.Id), ("request", requestId),
            ("action", cancel ? action + ".cancel" : action), ("user", userId), ("before", before), ("after", after)))
            await command.ExecuteNonQueryAsync(ct);
        await using (var command = Command(db, tx,
            "INSERT INTO operation(systemhaus_id,actor_id,request_id,request_hash,result_json) VALUES(@house,@actor,@request,@hash,CAST(@result AS jsonb))",
            ("house", actor.HouseId), ("actor", actor.Id), ("request", requestId), ("hash", digest), ("result", result)))
            await command.ExecuteNonQueryAsync(ct);
        await CaptureAuditContext(db, tx, actor, eventId, requestId, userId, cancel ? action + ".cancel" : action,
            revision, contextAfter, [new("user", userId, cancel ? "intendedTarget" : "target")], ct);
        await tx.CommitAsync(ct);
        return result;
    }
}
