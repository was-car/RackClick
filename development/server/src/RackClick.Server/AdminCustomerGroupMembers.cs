using System.Text.Json;
using RackClick.Domain;

namespace RackClick.Server;

public sealed record CustomerGroupMemberRequest(Guid CustomerId, bool? Assigned);

public sealed partial class PostgresStore
{
    public async Task<string> ReadAdminCustomers(Actor actor, CancellationToken ct)
    {
        await using var db = await source.OpenConnectionAsync(ct);
        await using var tx = await db.BeginTransactionAsync(System.Data.IsolationLevel.RepeatableRead, ct);
        await RequireSecurity(db, tx, actor, ct);
        await using var command = Command(db, tx, """
            SELECT jsonb_build_object('revision',h.revision,'customers',COALESCE((
              SELECT jsonb_agg(jsonb_build_object('id',c.id,'name',c.name) ORDER BY c.name,c.id)
              FROM customer c WHERE c.systemhaus_id=h.id),'[]'::jsonb))::text
            FROM systemhaus h WHERE h.id=@house
            """, ("house", actor.HouseId));
        string result = await command.ExecuteScalarAsync(ct) as string ?? throw new DomainError(404, "not_found");
        await tx.CommitAsync(ct);
        return result;
    }

    public async Task<string> CustomerGroupMemberStatus(Actor actor, Guid groupId, Guid requestId, CancellationToken ct)
    {
        if (groupId == Guid.Empty || requestId == Guid.Empty) throw new DomainError(422, "request_invalid");
        await using var db = await source.OpenConnectionAsync(ct);
        await using var tx = await db.BeginTransactionAsync(ct);
        await RequireSecurity(db, tx, actor, ct);
        await using var command = Command(db, tx, """
            SELECT o.result_json::text FROM operation o JOIN audit_event a
              ON a.systemhaus_id=o.systemhaus_id AND a.actor_id=o.actor_id AND a.request_id=o.request_id
            WHERE o.systemhaus_id=@house AND o.actor_id=@actor AND o.request_id=@request
              AND a.resource_id=@group AND a.action IN ('customerGroup.member.set','customerGroup.member.set.cancel')
            """, ("house", actor.HouseId), ("actor", actor.Id), ("request", requestId), ("group", groupId));
        return UserCreationOutcome(requestId, await command.ExecuteScalarAsync(ct) as string);
    }

    public async Task<string> SetOrCancelCustomerGroupMember(Actor actor, Guid groupId, CustomerGroupMemberRequest input,
        bool cancel, long expected, Guid requestId, CancellationToken ct)
    {
        if (requestId == Guid.Empty) throw new DomainError(422, "request_id_invalid");
        if (groupId == Guid.Empty || input.CustomerId == Guid.Empty || input.Assigned is null) throw new DomainError(422, "member_invalid");
        if (expected < 1) throw new DomainError(422, "revision_invalid");
        await using var db = await source.OpenConnectionAsync(ct);
        await using var tx = await db.BeginTransactionAsync(ct);
        await LockOperation(db, tx, actor, requestId, ct);
        await using var house = Command(db, tx, "SELECT revision FROM systemhaus WHERE id=@house FOR UPDATE", ("house", actor.HouseId));
        long revision = await house.ExecuteScalarAsync(ct) as long? ?? throw new DomainError(404, "not_found");
        await RequireSecurity(db, tx, actor, ct);
        const string action = "customerGroup.member.set";
        string digest = Secrets.Digest(JsonSerializer.Serialize(new { action, groupId, customerId = input.CustomerId, assigned = input.Assigned.Value, expected }, Json));
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
                SELECT EXISTS(SELECT 1 FROM customer_group WHERE systemhaus_id=@house AND id=@group)
                  AND EXISTS(SELECT 1 FROM customer WHERE systemhaus_id=@house AND id=@customer)
                """, ("house", actor.HouseId), ("group", groupId), ("customer", input.CustomerId)))
                if (!(bool)(await command.ExecuteScalarAsync(ct))!) throw new DomainError(404, "not_found");
            bool existed;
            await using (var command = Command(db, tx, "SELECT EXISTS(SELECT 1 FROM customer_group_member WHERE systemhaus_id=@house AND group_id=@group AND customer_id=@customer)",
                ("house", actor.HouseId), ("group", groupId), ("customer", input.CustomerId))) existed = (bool)(await command.ExecuteScalarAsync(ct))!;
            before = JsonSerializer.Serialize(new { groupId, customerId = input.CustomerId, assigned = existed }, Json);
            string sql = input.Assigned.Value
                ? "INSERT INTO customer_group_member(systemhaus_id,customer_id,group_id) VALUES(@house,@customer,@group) ON CONFLICT DO NOTHING"
                : "DELETE FROM customer_group_member WHERE systemhaus_id=@house AND customer_id=@customer AND group_id=@group";
            await using (var command = Command(db, tx, sql, ("house", actor.HouseId), ("customer", input.CustomerId), ("group", groupId)))
                await command.ExecuteNonQueryAsync(ct);
            long next = checked(revision + 1);
            contextAfter = next;
            await using (var command = Command(db, tx, "UPDATE systemhaus SET revision=@next WHERE id=@house", ("next", next), ("house", actor.HouseId)))
                await command.ExecuteNonQueryAsync(ct);
            var resource = new { groupId, customerId = input.CustomerId, assigned = input.Assigned.Value };
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
            revision, contextAfter, [new("customerGroup", groupId, cancel ? "intendedTarget" : "target"),
                new("customer", input.CustomerId, cancel ? "intendedMember" : "member")], ct);
        await tx.CommitAsync(ct);
        return result;
    }
}
