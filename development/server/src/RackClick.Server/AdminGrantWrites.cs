using System.Text.Json;
using RackClick.Domain;

namespace RackClick.Server;

public sealed record GrantRequest(Guid GrantId, string? Capability, string? Scope, Guid? TargetId, bool? Assigned);

public sealed partial class PostgresStore
{
    public async Task<string> ReadAdminCapabilities(Actor actor, CancellationToken ct)
    {
        await using var db = await source.OpenConnectionAsync(ct);
        await using var tx = await db.BeginTransactionAsync(System.Data.IsolationLevel.RepeatableRead, ct);
        await RequireSecurity(db, tx, actor, ct);
        await using var command = Command(db, tx, """
            SELECT jsonb_build_object('revision',h.revision,'capabilities',CAST(@capabilities AS jsonb))::text
            FROM systemhaus h WHERE h.id=@house
            """, ("house", actor.HouseId), ("capabilities", JsonSerializer.Serialize(Capabilities.FoundationAdmin, Json)));
        string result = await command.ExecuteScalarAsync(ct) as string ?? throw new DomainError(404, "not_found");
        await tx.CommitAsync(ct);
        return result;
    }

    public async Task<string> GrantStatus(Actor actor, Guid groupId, Guid requestId, CancellationToken ct)
    {
        if (groupId == Guid.Empty || requestId == Guid.Empty) throw new DomainError(422, "request_invalid");
        await using var db = await source.OpenConnectionAsync(ct);
        await using var tx = await db.BeginTransactionAsync(ct);
        await RequireSecurity(db, tx, actor, ct);
        await using var command = Command(db, tx, """
            SELECT o.result_json::text FROM operation o JOIN audit_event a
              ON a.systemhaus_id=o.systemhaus_id AND a.actor_id=o.actor_id AND a.request_id=o.request_id
            WHERE o.systemhaus_id=@house AND o.actor_id=@actor AND o.request_id=@request
              AND a.resource_id=@group AND a.action IN ('userGroup.grant.set','userGroup.grant.set.cancel')
            """, ("house", actor.HouseId), ("actor", actor.Id), ("request", requestId), ("group", groupId));
        return UserCreationOutcome(requestId, await command.ExecuteScalarAsync(ct) as string);
    }

    public async Task<string> SetOrCancelGrant(Actor actor, Guid groupId, GrantRequest input,
        bool cancel, long expected, Guid requestId, CancellationToken ct)
    {
        if (requestId == Guid.Empty) throw new DomainError(422, "request_id_invalid");
        if (groupId == Guid.Empty || input.GrantId == Guid.Empty || input.Assigned is null ||
            input.Capability is null || !Capabilities.FoundationAdmin.Contains(input.Capability, StringComparer.Ordinal) ||
            input.Scope is not ("systemhaus" or "customer" or "customerGroup") ||
            (input.Scope == "systemhaus" ? input.TargetId is not null : input.TargetId is null || input.TargetId == Guid.Empty))
            throw new DomainError(422, "grant_invalid");
        Guid? customerId = input.Scope == "customer" ? input.TargetId : null;
        Guid? customerGroupId = input.Scope == "customerGroup" ? input.TargetId : null;
        if (expected < 1) throw new DomainError(422, "revision_invalid");
        await using var db = await source.OpenConnectionAsync(ct);
        await using var tx = await db.BeginTransactionAsync(ct);
        await LockOperation(db, tx, actor, requestId, ct);
        await using var house = Command(db, tx, "SELECT revision FROM systemhaus WHERE id=@house FOR UPDATE", ("house", actor.HouseId));
        long revision = await house.ExecuteScalarAsync(ct) as long? ?? throw new DomainError(404, "not_found");
        await RequireSecurity(db, tx, actor, ct);
        const string action = "userGroup.grant.set";
        string digest = Secrets.Digest(JsonSerializer.Serialize(new { action, groupId, grantId = input.GrantId, capability = input.Capability, scope = input.Scope, targetId = input.TargetId, assigned = input.Assigned.Value, expected }, Json));
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
                  AND (@customer IS NULL OR EXISTS(SELECT 1 FROM customer WHERE systemhaus_id=@house AND id=@customer))
                  AND (@customers IS NULL OR EXISTS(SELECT 1 FROM customer_group WHERE systemhaus_id=@house AND id=@customers))
                """, ("house", actor.HouseId), ("group", groupId), ("customer", customerId), ("customers", customerGroupId)))
                if (!(bool)(await command.ExecuteScalarAsync(ct))!) throw new DomainError(404, "not_found");
            bool existed = false;
            await using (var command = Command(db, tx,
                "SELECT systemhaus_id,user_group_id,capability,customer_id,customer_group_id FROM permission_grant WHERE id=@id", ("id", input.GrantId)))
            await using (var rows = await command.ExecuteReaderAsync(ct))
                if (await rows.ReadAsync(ct))
                {
                    if (rows.GetGuid(0) != actor.HouseId || rows.GetGuid(1) != groupId) throw new DomainError(404, "not_found");
                    Guid? savedCustomer = rows.IsDBNull(3) ? null : rows.GetGuid(3);
                    Guid? savedGroup = rows.IsDBNull(4) ? null : rows.GetGuid(4);
                    if (rows.GetString(2) != input.Capability || savedCustomer != customerId || savedGroup != customerGroupId)
                        throw new DomainError(409, "grant_intent_mismatch");
                    existed = true;
                }
            before = JsonSerializer.Serialize(new { groupId, grantId = input.GrantId, capability = input.Capability, scope = input.Scope, targetId = input.TargetId, assigned = existed }, Json);
            if (input.Assigned.Value && !existed)
            {
                await using (var duplicate = Command(db, tx, """
                    SELECT EXISTS(SELECT 1 FROM permission_grant WHERE systemhaus_id=@house AND user_group_id=@group
                      AND capability=@cap AND customer_id IS NOT DISTINCT FROM @customer AND customer_group_id IS NOT DISTINCT FROM @customers)
                    """, ("house", actor.HouseId), ("group", groupId), ("cap", input.Capability), ("customer", customerId), ("customers", customerGroupId)))
                    if ((bool)(await duplicate.ExecuteScalarAsync(ct))!) throw new DomainError(409, "grant_exists");
                await using var command = Command(db, tx, """
                    INSERT INTO permission_grant(id,systemhaus_id,user_group_id,capability,customer_id,customer_group_id)
                    VALUES(@id,@house,@group,@cap,@customer,@customers)
                    """, ("id", input.GrantId), ("house", actor.HouseId), ("group", groupId), ("cap", input.Capability), ("customer", customerId), ("customers", customerGroupId));
                await command.ExecuteNonQueryAsync(ct);
            }
            if (!input.Assigned.Value)
            {
                await using (var command = Command(db, tx, "DELETE FROM permission_grant WHERE id=@id AND systemhaus_id=@house AND user_group_id=@group",
                    ("id", input.GrantId), ("house", actor.HouseId), ("group", groupId))) await command.ExecuteNonQueryAsync(ct);
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
            var resource = new { groupId, grantId = input.GrantId, capability = input.Capability, scope = input.Scope, targetId = input.TargetId, assigned = input.Assigned.Value };
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
        string relation = cancel ? "intendedTarget" : "target";
        await CaptureAuditContext(db, tx, actor, eventId, requestId, groupId, cancel ? action + ".cancel" : action,
            revision, contextAfter, [new("userGroup", groupId, relation), new("grant", input.GrantId, relation),
                new(input.Scope!, input.Scope == "systemhaus" ? actor.HouseId : input.TargetId!.Value,
                    cancel ? "intendedScope" : "scope")], ct);
        await tx.CommitAsync(ct);
        return result;
    }
}
