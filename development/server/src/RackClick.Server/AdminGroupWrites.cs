using System.Text.Json;
using Npgsql;
using RackClick.Domain;

namespace RackClick.Server;

public sealed partial class PostgresStore
{
    private static string GroupAction(bool customerGroup) => customerGroup ? "customerGroup.create" : "userGroup.create";

    public async Task<string> GroupCreationStatus(Actor actor, bool customerGroup, Guid requestId, CancellationToken ct)
    {
        await using var db = await source.OpenConnectionAsync(ct);
        await using var tx = await db.BeginTransactionAsync(ct);
        await RequireSecurity(db, tx, actor, ct);
        string action = GroupAction(customerGroup);
        await using var command = Command(db, tx, """
            SELECT o.result_json::text FROM operation o JOIN audit_event a
              ON a.systemhaus_id=o.systemhaus_id AND a.actor_id=o.actor_id AND a.request_id=o.request_id
            WHERE o.systemhaus_id=@house AND o.actor_id=@actor AND o.request_id=@request
              AND (a.action=@action OR a.action=@cancel)
            """, ("house", actor.HouseId), ("actor", actor.Id), ("request", requestId), ("action", action), ("cancel", action + ".cancel"));
        return UserCreationOutcome(requestId, await command.ExecuteScalarAsync(ct) as string);
    }

    public async Task<string> CreateOrCancelGroup(Actor actor, bool customerGroup, bool cancel, string? input,
        long expected, Guid requestId, CancellationToken ct)
    {
        if (requestId == Guid.Empty) throw new DomainError(422, "request_id_invalid");
        if (expected < 1) throw new DomainError(422, "revision_invalid");
        await using var db = await source.OpenConnectionAsync(ct);
        await using var tx = await db.BeginTransactionAsync(ct);
        await LockOperation(db, tx, actor, requestId, ct);
        await using var house = Command(db, tx, "SELECT revision FROM systemhaus WHERE id=@house FOR UPDATE", ("house", actor.HouseId));
        long revision = await house.ExecuteScalarAsync(ct) as long? ?? throw new DomainError(404, "not_found");
        await RequireSecurity(db, tx, actor, ct);
        string action = GroupAction(customerGroup), name = "", digest;
        try
        {
            name = Names.Validate(input);
            digest = Secrets.Digest(JsonSerializer.Serialize(new { action, name, expected }, Json));
        }
        catch (DomainError error) when (cancel && (error.Code is "name_required" or "name_invalid"))
        {
            digest = Secrets.Digest(JsonSerializer.Serialize(new { action = action + ".invalidName", input, expected }, Json));
        }
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
        string result, after;
        long contextAfter = revision;
        Guid resourceId;
        if (cancel)
        {
            // Reserve the original key without rebasing stale revision or undoing a commit.
            result = JsonSerializer.Serialize(new { requestId, state = "cancelled", operation = (object?)null }, Json);
            after = result; resourceId = actor.HouseId;
        }
        else
        {
            Revisions.Require(expected, revision);
            resourceId = Guid.NewGuid();
            // The table is selected solely from the hardcoded route kind, never user text.
            string table = customerGroup ? "customer_group" : "user_group";
            await using (var command = Command(db, tx, $"INSERT INTO {table}(id,systemhaus_id,name) VALUES(@id,@house,@name)",
                ("id", resourceId), ("house", actor.HouseId), ("name", name))) await command.ExecuteNonQueryAsync(ct);
            long next = checked(revision + 1);
            contextAfter = next;
            await using (var command = Command(db, tx, "UPDATE systemhaus SET revision=@next WHERE id=@house", ("next", next), ("house", actor.HouseId)))
                await command.ExecuteNonQueryAsync(ct);
            var resource = new { id = resourceId, name, kind = customerGroup ? "customerGroup" : "userGroup" };
            after = JsonSerializer.Serialize(resource, Json);
            result = JsonSerializer.Serialize(new { resource, systemhausRevision = next, requestId }, Json);
        }
        Guid eventId = Guid.NewGuid();
        await using (var command = Command(db, tx, """
            INSERT INTO audit_event(id,systemhaus_id,actor_id,request_id,action,resource_id,before_json,after_json)
            VALUES(@id,@house,@actor,@request,@action,@resource,'null'::jsonb,CAST(@after AS jsonb))
            """, ("id", eventId), ("house", actor.HouseId), ("actor", actor.Id), ("request", requestId),
            ("action", cancel ? action + ".cancel" : action), ("resource", resourceId), ("after", after)))
            await command.ExecuteNonQueryAsync(ct);
        await using (var command = Command(db, tx,
            "INSERT INTO operation(systemhaus_id,actor_id,request_id,request_hash,result_json) VALUES(@house,@actor,@request,@hash,CAST(@result AS jsonb))",
            ("house", actor.HouseId), ("actor", actor.Id), ("request", requestId), ("hash", digest), ("result", result)))
            await command.ExecuteNonQueryAsync(ct);
        await CaptureAuditContext(db, tx, actor, eventId, requestId, resourceId, cancel ? action + ".cancel" : action,
            revision, contextAfter, [new(cancel ? "systemhaus" : customerGroup ? "customerGroup" : "userGroup", resourceId,
                cancel ? "intendedTarget" : "target")], ct);
        await tx.CommitAsync(ct);
        return result;
    }
}
