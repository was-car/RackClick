using System.Text.Json;
using RackClick.Domain;

namespace RackClick.Server;

public sealed record GroupMemberRequest(Guid UserId, bool? Assigned);

public sealed partial class PostgresStore
{
    public async Task<string> GroupMemberStatus(Actor actor, Guid groupId, Guid requestId, CancellationToken ct)
    {
        if (groupId == Guid.Empty || requestId == Guid.Empty) throw new DomainError(422, "request_invalid");
        await using var db = await source.OpenConnectionAsync(ct);
        await using var tx = await db.BeginTransactionAsync(ct);
        await RequireSecurity(db, tx, actor, ct);
        await using var command = Command(db, tx, """
            SELECT o.result_json::text FROM operation o JOIN audit_event a
              ON a.systemhaus_id=o.systemhaus_id AND a.actor_id=o.actor_id AND a.request_id=o.request_id
            WHERE o.systemhaus_id=@house AND o.actor_id=@actor AND o.request_id=@request
              AND a.resource_id=@group AND a.action IN ('userGroup.member.set','userGroup.member.set.cancel')
            """, ("house", actor.HouseId), ("actor", actor.Id), ("request", requestId), ("group", groupId));
        return UserCreationOutcome(requestId, await command.ExecuteScalarAsync(ct) as string);
    }

    public async Task<string> SetOrCancelGroupMember(Actor actor, Guid groupId, GroupMemberRequest input,
        bool cancel, long expected, Guid requestId, CancellationToken ct)
    {
        if (requestId == Guid.Empty) throw new DomainError(422, "request_id_invalid");
        if (groupId == Guid.Empty || input.UserId == Guid.Empty || input.Assigned is null) throw new DomainError(422, "member_invalid");
        if (expected < 1) throw new DomainError(422, "revision_invalid");
        await using var db = await source.OpenConnectionAsync(ct);
        await using var tx = await db.BeginTransactionAsync(ct);
        await LockOperation(db, tx, actor, requestId, ct);
        await using var house = Command(db, tx, "SELECT revision FROM systemhaus WHERE id=@house FOR UPDATE", ("house", actor.HouseId));
        long revision = await house.ExecuteScalarAsync(ct) as long? ?? throw new DomainError(404, "not_found");
        await RequireSecurity(db, tx, actor, ct);
        const string action = "userGroup.member.set";
        string digest = Secrets.Digest(JsonSerializer.Serialize(new { action, groupId, userId = input.UserId, assigned = input.Assigned.Value, expected }, Json));
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
            await using (var command = Command(db, tx, """
                SELECT EXISTS(SELECT 1 FROM user_group WHERE systemhaus_id=@house AND id=@group)
                  AND EXISTS(SELECT 1 FROM app_user WHERE systemhaus_id=@house AND id=@user)
                """, ("house", actor.HouseId), ("group", groupId), ("user", input.UserId)))
                if (!(bool)(await command.ExecuteScalarAsync(ct))!) throw new DomainError(404, "not_found");
            bool existed;
            await using (var command = Command(db, tx, "SELECT EXISTS(SELECT 1 FROM user_group_member WHERE systemhaus_id=@house AND group_id=@group AND user_id=@user)",
                ("house", actor.HouseId), ("group", groupId), ("user", input.UserId))) existed = (bool)(await command.ExecuteScalarAsync(ct))!;
            before = JsonSerializer.Serialize(new { groupId, userId = input.UserId, assigned = existed }, Json);
            string sql = input.Assigned.Value
                ? "INSERT INTO user_group_member(systemhaus_id,user_id,group_id) VALUES(@house,@user,@group) ON CONFLICT DO NOTHING"
                : "DELETE FROM user_group_member WHERE systemhaus_id=@house AND user_id=@user AND group_id=@group";
            await using (var command = Command(db, tx, sql, ("house", actor.HouseId), ("user", input.UserId), ("group", groupId)))
                await command.ExecuteNonQueryAsync(ct);
            if (!input.Assigned.Value)
            {
                await using var command = Command(db, tx, """
                    SELECT EXISTS(SELECT 1 FROM app_user u
                      JOIN user_group_member m ON m.systemhaus_id=u.systemhaus_id AND m.user_id=u.id
                      JOIN permission_grant g ON g.systemhaus_id=m.systemhaus_id AND g.user_group_id=m.group_id
                      WHERE u.systemhaus_id=@house AND u.active AND g.capability='security.manage'
                        AND g.customer_id IS NULL AND g.customer_group_id IS NULL)
                    """, ("house", actor.HouseId));
                if (!(bool)(await command.ExecuteScalarAsync(ct))!) throw new DomainError(409, "last_admin_required");
            }
            long next = checked(revision + 1);
            contextAfter = next;
            await using (var command = Command(db, tx, "UPDATE systemhaus SET revision=@next WHERE id=@house", ("next", next), ("house", actor.HouseId)))
                await command.ExecuteNonQueryAsync(ct);
            var resource = new { groupId, userId = input.UserId, assigned = input.Assigned.Value };
            after = JsonSerializer.Serialize(resource, Json);
            result = JsonSerializer.Serialize(new { resource, systemhausRevision = next, requestId }, Json);
        }
        Guid eventId = Guid.NewGuid();
        await using (var command = Command(db, tx, """
            INSERT INTO audit_event(id,systemhaus_id,actor_id,request_id,action,resource_id,before_json,after_json)
            VALUES(@id,@house,@actor,@request,@action,@group,CAST(@before AS jsonb),CAST(@after AS jsonb))
            """, ("id", eventId), ("house", actor.HouseId), ("actor", actor.Id), ("request", requestId),
            ("action", cancel ? action + ".cancel" : action), ("group", groupId), ("before", before), ("after", after)))
            await command.ExecuteNonQueryAsync(ct);
        await using (var command = Command(db, tx,
            "INSERT INTO operation(systemhaus_id,actor_id,request_id,request_hash,result_json) VALUES(@house,@actor,@request,@hash,CAST(@result AS jsonb))",
            ("house", actor.HouseId), ("actor", actor.Id), ("request", requestId), ("hash", digest), ("result", result)))
            await command.ExecuteNonQueryAsync(ct);
        await CaptureAuditContext(db, tx, actor, eventId, requestId, groupId, cancel ? action + ".cancel" : action,
            revision, contextAfter, [new("userGroup", groupId, cancel ? "intendedTarget" : "target"),
                new("user", input.UserId, cancel ? "intendedMember" : "member")], ct);
        await tx.CommitAsync(ct);
        return result;
    }
}
