using System.Text.Json;
using RackClick.Domain;

namespace RackClick.Server;

public sealed partial class PostgresStore
{
    public async Task<string> UserSessionRevocationStatus(Actor actor, Guid userId, Guid sessionId, Guid requestId, CancellationToken ct)
    {
        if (userId == Guid.Empty || sessionId == Guid.Empty || requestId == Guid.Empty) throw new DomainError(422, "request_invalid");
        await using var db = await source.OpenConnectionAsync(ct);
        await using var tx = await db.BeginTransactionAsync(ct);
        await RequireSecurity(db, tx, actor, ct);
        await using var command = Command(db, tx, """
            SELECT o.result_json::text FROM operation o JOIN audit_event a
              ON a.systemhaus_id=o.systemhaus_id AND a.actor_id=o.actor_id AND a.request_id=o.request_id
            WHERE o.systemhaus_id=@house AND o.actor_id=@actor AND o.request_id=@request
              AND a.resource_id=@session AND a.before_json->>'userId'=@user
              AND a.action IN ('user.session.revoke','user.session.revoke.cancel')
            """, ("house", actor.HouseId), ("actor", actor.Id), ("request", requestId), ("session", sessionId), ("user", userId.ToString("D")));
        return UserCreationOutcome(requestId, await command.ExecuteScalarAsync(ct) as string);
    }

    public async Task<string> RevokeOrCancelUserSession(Actor actor, Guid userId, Guid sessionId,
        bool cancel, long expected, Guid requestId, CancellationToken ct)
    {
        if (requestId == Guid.Empty) throw new DomainError(422, "request_id_invalid");
        if (userId == Guid.Empty || sessionId == Guid.Empty) throw new DomainError(422, "request_invalid");
        if (expected < 1) throw new DomainError(422, "revision_invalid");
        await using var db = await source.OpenConnectionAsync(ct);
        await using var tx = await db.BeginTransactionAsync(ct);
        await LockOperation(db, tx, actor, requestId, ct);
        await using var house = Command(db, tx, "SELECT revision FROM systemhaus WHERE id=@house FOR UPDATE", ("house", actor.HouseId));
        long revision = await house.ExecuteScalarAsync(ct) as long? ?? throw new DomainError(404, "not_found");
        await RequireSecurity(db, tx, actor, ct);
        const string action = "user.session.revoke";
        string digest = Secrets.Digest(JsonSerializer.Serialize(new { action, userId, sessionId, expected }, Json));
        await OperationCancellation.EnsureNotCanceled(db, tx, actor, requestId, digest, ct);
        await using (var command = Command(db, tx,
            "SELECT request_hash,result_json::text FROM operation WHERE systemhaus_id=@house AND actor_id=@actor AND request_id=@request",
            ("house", actor.HouseId), ("actor", actor.Id), ("request", requestId)))
        await using (var rows = await command.ExecuteReaderAsync(ct))
            if (await rows.ReadAsync(ct))
            {
                if (rows.GetString(0) != digest) throw new DomainError(409, "request_id_reused");
                string replay = rows.GetString(1);
                if (cancel) return UserCreationOutcome(requestId, replay);
                if (IsUserCreationCancelled(replay)) throw new DomainError(409, "operation_cancelled");
                // The selected row no longer exists. Authorize the original actor and return its original result.
                return replay;
            }
        string before = JsonSerializer.Serialize(new { userId, sessionId }, Json);
        string result, after;
        long contextAfter = revision;
        if (cancel)
        {
            // Public durable fence: no target lookup, deletion, or revision increment.
            result = JsonSerializer.Serialize(new { requestId, state = "cancelled", operation = (object?)null }, Json);
            after = result;
        }
        else
        {
            Revisions.Require(expected, revision);
            await using (var command = Command(db, tx,
                "SELECT id FROM app_user WHERE systemhaus_id=@house AND id=@user FOR UPDATE",
                ("house", actor.HouseId), ("user", userId)))
                if (await command.ExecuteScalarAsync(ct) is not Guid) throw new DomainError(404, "not_found");
            bool wasCurrent;
            await using (var command = Command(db, tx,
                "SELECT token_hash=@token FROM app_session WHERE user_id=@user AND id=@session FOR UPDATE",
                ("token", actor.SessionTokenHash!), ("user", userId), ("session", sessionId)))
                wasCurrent = await command.ExecuteScalarAsync(ct) as bool? ?? throw new DomainError(404, "not_found");
            // The final target lock may wait: session expiry and GLOBAL permission are checked again now.
            await RequireSecurity(db, tx, actor, ct);
            await using (var command = Command(db, tx, "DELETE FROM app_session WHERE user_id=@user AND id=@session",
                ("user", userId), ("session", sessionId)))
                await command.ExecuteNonQueryAsync(ct);
            long next = checked(revision + 1);
            contextAfter = next;
            await using (var command = Command(db, tx, "UPDATE systemhaus SET revision=@next WHERE id=@house", ("next", next), ("house", actor.HouseId)))
                await command.ExecuteNonQueryAsync(ct);
            var resource = new { userId, sessionId, revoked = true, wasCurrent };
            after = JsonSerializer.Serialize(resource, Json);
            result = JsonSerializer.Serialize(new { resource, systemhausRevision = next, requestId }, Json);
        }
        Guid eventId = Guid.NewGuid();
        await using (var command = Command(db, tx, """
            INSERT INTO audit_event(id,systemhaus_id,actor_id,request_id,action,resource_id,before_json,after_json)
            VALUES(@id,@house,@actor,@request,@action,@session,CAST(@before AS jsonb),CAST(@after AS jsonb))
            """, ("id", eventId), ("house", actor.HouseId), ("actor", actor.Id), ("request", requestId),
            ("action", cancel ? action + ".cancel" : action), ("session", sessionId), ("before", before), ("after", after)))
            await command.ExecuteNonQueryAsync(ct);
        await using (var command = Command(db, tx,
            "INSERT INTO operation(systemhaus_id,actor_id,request_id,request_hash,result_json) VALUES(@house,@actor,@request,@hash,CAST(@result AS jsonb))",
            ("house", actor.HouseId), ("actor", actor.Id), ("request", requestId), ("hash", digest), ("result", result)))
            await command.ExecuteNonQueryAsync(ct);
        string relation = cancel ? "intendedTarget" : "target";
        await CaptureAuditContext(db, tx, actor, eventId, requestId, sessionId, cancel ? action + ".cancel" : action,
            revision, contextAfter, [new("user", userId, relation), new("session", sessionId, relation)], ct);
        await tx.CommitAsync(ct);
        return result;
    }
}
