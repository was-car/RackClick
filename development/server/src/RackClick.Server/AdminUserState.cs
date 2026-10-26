using System.Text.Json;
using RackClick.Domain;

namespace RackClick.Server;

public sealed record UserStateRequest(bool? Active);

public sealed partial class PostgresStore
{
    public async Task<string> UserStateStatus(Actor actor, Guid userId, Guid requestId, CancellationToken ct)
    {
        if (userId == Guid.Empty || requestId == Guid.Empty) throw new DomainError(422, "request_invalid");
        await using var db = await source.OpenConnectionAsync(ct);
        await using var tx = await db.BeginTransactionAsync(ct);
        await RequireSecurity(db, tx, actor, ct);
        await using var command = Command(db, tx, """
            SELECT o.result_json::text FROM operation o JOIN audit_event a
              ON a.systemhaus_id=o.systemhaus_id AND a.actor_id=o.actor_id AND a.request_id=o.request_id
            WHERE o.systemhaus_id=@house AND o.actor_id=@actor AND o.request_id=@request
              AND a.resource_id=@user AND a.action IN ('user.state.set','user.state.set.cancel')
            """, ("house", actor.HouseId), ("actor", actor.Id), ("request", requestId), ("user", userId));
        return UserCreationOutcome(requestId, await command.ExecuteScalarAsync(ct) as string);
    }

    public async Task<string> SetOrCancelUserState(Actor actor, Guid userId, UserStateRequest input,
        bool cancel, long expected, Guid requestId, CancellationToken ct)
    {
        if (requestId == Guid.Empty) throw new DomainError(422, "request_id_invalid");
        if (userId == Guid.Empty || input.Active is null) throw new DomainError(422, "user_state_invalid");
        if (expected < 1) throw new DomainError(422, "revision_invalid");
        await using var db = await source.OpenConnectionAsync(ct);
        await using var tx = await db.BeginTransactionAsync(ct);
        await LockOperation(db, tx, actor, requestId, ct);
        await using var house = Command(db, tx, "SELECT revision FROM systemhaus WHERE id=@house FOR UPDATE", ("house", actor.HouseId));
        long revision = await house.ExecuteScalarAsync(ct) as long? ?? throw new DomainError(404, "not_found");
        await RequireSecurity(db, tx, actor, ct);
        const string action = "user.state.set";
        string digest = Secrets.Digest(JsonSerializer.Serialize(new { action, userId, active = input.Active.Value, expected }, Json));
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
                return replay;
            }
        string result, after, before = "null";
        long contextAfter = revision;
        if (cancel)
        {
            // A fence does not require still-existing targets or a current revision.
            result = JsonSerializer.Serialize(new { requestId, state = "cancelled", operation = (object?)null }, Json);
            after = result;
        }
        else
        {
            Revisions.Require(expected, revision);
            AdminUser prior;
            // Login also locks this row; it cannot issue a usable session after deactivation commits.
            await using (var command = Command(db, tx, "SELECT id,username,active FROM app_user WHERE systemhaus_id=@house AND id=@user FOR UPDATE",
                ("house", actor.HouseId), ("user", userId)))
            await using (var rows = await command.ExecuteReaderAsync(ct))
            {
                if (!await rows.ReadAsync(ct)) throw new DomainError(404, "not_found");
                prior = new(rows.GetGuid(0), rows.GetString(1), rows.GetBoolean(2));
            }
            // Target may have waited behind Login. Check expiry/permissions after the final wait.
            await RequireSecurity(db, tx, actor, ct);
            before = JsonSerializer.Serialize(prior, Json);
            await using (var command = Command(db, tx, "UPDATE app_user SET active=@active WHERE systemhaus_id=@house AND id=@user",
                ("active", input.Active.Value), ("house", actor.HouseId), ("user", userId)))
                await command.ExecuteNonQueryAsync(ct);
            if (!input.Active.Value)
            {
                await using (var command = Command(db, tx, "DELETE FROM app_session WHERE user_id=@user", ("user", userId)))
                    await command.ExecuteNonQueryAsync(ct);
                await using var guard = Command(db, tx, """
                    SELECT EXISTS(SELECT 1 FROM app_user u
                      JOIN user_group_member m ON m.systemhaus_id=u.systemhaus_id AND m.user_id=u.id
                      JOIN permission_grant g ON g.systemhaus_id=m.systemhaus_id AND g.user_group_id=m.group_id
                      WHERE u.systemhaus_id=@house AND u.active AND g.capability='security.manage'
                        AND g.customer_id IS NULL AND g.customer_group_id IS NULL)
                    """, ("house", actor.HouseId));
                if (!(bool)(await guard.ExecuteScalarAsync(ct))!) throw new DomainError(409, "last_admin_required");
            }
            long next = checked(revision + 1);
            contextAfter = next;
            await using (var command = Command(db, tx, "UPDATE systemhaus SET revision=@next WHERE id=@house", ("next", next), ("house", actor.HouseId)))
                await command.ExecuteNonQueryAsync(ct);
            var resource = new AdminUser(userId, prior.UserName, input.Active.Value);
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
        await CaptureUserStateContext(db, tx, actor, eventId, requestId, userId, revision, contextAfter, cancel, ct);
        await tx.CommitAsync(ct);
        return result;
    }
}
