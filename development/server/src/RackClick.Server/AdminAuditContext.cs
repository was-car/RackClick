using Npgsql;
using NpgsqlTypes;
using RackClick.Domain;

namespace RackClick.Server;

public sealed record AuditContextObject(string Kind, Guid Id, string Relation);
public sealed record AdminAuditContext(string Status, int? CaptureVersion, Guid? ActorId, string? ScopeKind,
    Guid? ScopeId, Guid? CustomerId, string? RevisionScope, long? RevisionBefore, long? RevisionAfter,
    long? CustomerRevisionBefore, long? CustomerRevisionAfter, string? Outcome, IReadOnlyList<AuditContextObject> Objects);
public sealed record AdminAuditContextSnapshot(long Revision, AdminAuditEvent Event, AdminAuditContext Context);

public sealed partial class PostgresStore
{
    private static Task CaptureUserCreationContext(NpgsqlConnection db, NpgsqlTransaction tx, Actor actor,
        Guid eventId, Guid requestId, Guid resourceId, long before, long after, bool cancel, CancellationToken ct) =>
        CaptureAuditContext(db, tx, actor, eventId, requestId, resourceId, cancel ? "user.create.cancel" : "user.create",
            before, after, [new(cancel ? "systemhaus" : "user", resourceId, cancel ? "intendedTarget" : "target")], ct);

    private static Task CaptureUserStateContext(NpgsqlConnection db, NpgsqlTransaction tx, Actor actor,
        Guid eventId, Guid requestId, Guid resourceId, long before, long after, bool cancel, CancellationToken ct) =>
        CaptureAuditContext(db, tx, actor, eventId, requestId, resourceId, cancel ? "user.state.set.cancel" : "user.state.set",
            before, after, [new("user", resourceId, cancel ? "intendedTarget" : "target")], ct);

    // Identities come from the writer in this transaction, never from live lookups or JSON.
    private static bool ContextCoherent(string action, Guid resource, Guid house, long before, long after,
        string outcome, string scope, Guid? scopeId, Guid? customerId, long? customerBefore, long? customerAfter,
        IReadOnlyList<AuditContextObject> objects)
    {
        bool cancel = action.EndsWith(".cancel", StringComparison.Ordinal);
        string command = cancel ? action[..^7] : action;
        bool customer = command is "customer.create" or "customer.rename";
        if (resource == Guid.Empty || house == Guid.Empty || before < 1 || after < 1
            || (cancel ? outcome != "cancelled" || after != before : outcome != "committed" || after - before != 1)
            || objects.Count is < 1 or > 3 || objects.Any(o => o.Id == Guid.Empty)) return false;
        if (customer)
        {
            if (cancel || scope != "customer" || scopeId != resource || customerId != resource || customerAfter is not > 0
                || (command == "customer.create" ? customerBefore is not null || customerAfter != 1
                    : customerBefore is not > 0 || customerAfter - customerBefore != 1)) return false;
        }
        else if (scope != "systemhaus" || scopeId is not null || customerId is not null
            || customerBefore is not null || customerAfter is not null) return false;
        string target = cancel ? "intendedTarget" : "target";
        bool Object(int position, string kind, string relation, Guid? id = null) => position < objects.Count
            && objects[position].Kind == kind && objects[position].Relation == relation
            && (!id.HasValue || objects[position].Id == id);
        switch (command)
        {
            case "user.create":
            case "userGroup.create":
            case "customerGroup.create":
                if (objects.Count != 1) return false;
                return cancel ? resource == house && Object(0, "systemhaus", target, house)
                    : Object(0, command == "user.create" ? "user" : command == "userGroup.create" ? "userGroup" : "customerGroup", target, resource);
            case "user.state.set":
            case "user.password.reset": return objects.Count == 1 && Object(0, "user", target, resource);
            case "user.session.revoke": return objects.Count == 2 && Object(0, "user", target) && Object(1, "session", target, resource);
            case "userGroup.member.set": return objects.Count == 2 && Object(0, "userGroup", target, resource)
                && Object(1, "user", cancel ? "intendedMember" : "member");
            case "customerGroup.member.set": return objects.Count == 2 && Object(0, "customerGroup", target, resource)
                && Object(1, "customer", cancel ? "intendedMember" : "member");
            case "userGroup.grant.set":
                return objects.Count == 3 && Object(0, "userGroup", target, resource) && Object(1, "grant", target)
                    && objects[2].Kind is "systemhaus" or "customer" or "customerGroup"
                    && objects[2].Relation == (cancel ? "intendedScope" : "scope")
                    && (objects[2].Kind != "systemhaus" || objects[2].Id == house);
            case "systemhaus.rename": return !cancel && objects.Count == 1 && resource == house && Object(0, "systemhaus", "target", house);
            case "customer.create":
            case "customer.rename": return objects.Count == 1 && Object(0, "customer", "target", resource);
            default: return false;
        }
    }

    private static async Task CaptureAuditContext(NpgsqlConnection db, NpgsqlTransaction tx, Actor actor,
        Guid eventId, Guid requestId, Guid resourceId, string action, long before, long after,
        IReadOnlyList<AuditContextObject> objects, CancellationToken ct, Guid? customerId = null,
        long? customerRevisionBefore = null, long? customerRevisionAfter = null)
    {
        string scope = customerId.HasValue ? "customer" : "systemhaus";
        string outcome = action.EndsWith(".cancel", StringComparison.Ordinal) ? "cancelled" : "committed";
        if (actor.Id == Guid.Empty || requestId == Guid.Empty || eventId == Guid.Empty
            || !ContextCoherent(action, resourceId, actor.HouseId, before, after, outcome, scope, customerId,
                customerId, customerRevisionBefore, customerRevisionAfter, objects))
            throw new InvalidOperationException("Invalid audit context.");
        await using (var command = Command(db, tx, """
            INSERT INTO audit_context(event_id,capture_version,scope_kind,revision_scope,revision_before,revision_after,outcome,
                scope_id,customer_id,customer_revision_before,customer_revision_after)
            SELECT id,1,@scope,'systemhaus',@before,@after,@outcome,@customer,@customer,@customerBefore,@customerAfter
            FROM audit_event WHERE id=@event AND systemhaus_id=@house AND actor_id=@actor AND request_id=@request
                AND action=@action AND resource_id=@resource
            """, ("scope", scope), ("before", before), ("after", after), ("outcome", outcome), ("customer", customerId),
            ("event", eventId), ("house", actor.HouseId), ("actor", actor.Id), ("request", requestId),
            ("action", action), ("resource", resourceId)))
        {
            command.Parameters.AddWithValue("customerBefore", NpgsqlDbType.Bigint, (object?)customerRevisionBefore ?? DBNull.Value);
            command.Parameters.AddWithValue("customerAfter", NpgsqlDbType.Bigint, (object?)customerRevisionAfter ?? DBNull.Value);
            if (await command.ExecuteNonQueryAsync(ct) != 1) throw new InvalidOperationException("Audit event missing for context.");
        }
        for (int index = 0; index < objects.Count; index++)
        {
            var item = objects[index];
            await using var command = Command(db, tx, """
                INSERT INTO audit_context_object(event_id,position,kind,object_id,relation)
                VALUES(@event,@position,@kind,@resource,@relation)
                """, ("event", eventId), ("position", index + 1), ("kind", item.Kind), ("resource", item.Id), ("relation", item.Relation));
            await command.ExecuteNonQueryAsync(ct);
        }
    }

    public async Task<AdminAuditContextSnapshot> ReadAuditContext(Actor actor, string rawEventId, CancellationToken ct)
    {
        await using var db = await source.OpenConnectionAsync(ct);
        await using var tx = await db.BeginTransactionAsync(System.Data.IsolationLevel.RepeatableRead, ct);
        await RequireSecurity(db, tx, actor, ct);
        if (rawEventId.Length != 36 || !Guid.TryParseExact(rawEventId, "D", out var id) || id == Guid.Empty)
            throw new DomainError(422, "request_invalid");
        var context = new AdminAuditContext("notRecorded", null, null, null, null, null, null, null, null, null, null, null, []);
        AdminAuditEvent item;
        int version = 0;
        string scope = "", revisionScope = "", outcome = "";
        long before = 0, after = 0;
        Guid? scopeId = null, customerId = null;
        long? customerBefore = null, customerAfter = null;
        await using (var command = Command(db, tx, """
            SELECT a.id,a.occurred_at,a.actor_id,u.username,a.request_id,a.action,a.resource_id,
                c.capture_version,c.scope_kind,c.revision_scope,c.revision_before,c.revision_after,c.outcome,
                c.scope_id,c.customer_id,c.customer_revision_before,c.customer_revision_after
            FROM audit_event a JOIN app_user u ON u.systemhaus_id=a.systemhaus_id AND u.id=a.actor_id
            LEFT JOIN audit_context c ON c.event_id=a.id WHERE a.systemhaus_id=@house AND a.id=@event
            """, ("house", actor.HouseId), ("event", id)))
        await using (var row = await command.ExecuteReaderAsync(ct))
        {
            if (!await row.ReadAsync(ct)) throw new DomainError(404, "not_found");
            item = new(row.GetGuid(0), row.GetDateTime(1), new(row.GetGuid(2), row.GetString(3)), row.GetGuid(4), row.GetString(5), row.GetGuid(6));
            if (!row.IsDBNull(7))
            {
                version = row.GetInt32(7); scope = row.GetString(8); revisionScope = row.GetString(9);
                before = row.GetInt64(10); after = row.GetInt64(11); outcome = row.GetString(12);
                scopeId = row.IsDBNull(13) ? null : row.GetGuid(13); customerId = row.IsDBNull(14) ? null : row.GetGuid(14);
                customerBefore = row.IsDBNull(15) ? null : row.GetInt64(15); customerAfter = row.IsDBNull(16) ? null : row.GetInt64(16);
            }
        }
        var objects = new List<AuditContextObject>();
        bool positions = true;
        if (version == 1 && revisionScope == "systemhaus" && item.Actor.Id != Guid.Empty && item.RequestId != Guid.Empty)
        {
            await using (var command = Command(db, tx, "SELECT position,kind,object_id,relation FROM audit_context_object WHERE event_id=@event ORDER BY position LIMIT 4", ("event", id)))
            await using (var rows = await command.ExecuteReaderAsync(ct))
                while (await rows.ReadAsync(ct))
                {
                    positions &= rows.GetInt16(0) == objects.Count + 1;
                    objects.Add(new(rows.GetString(1), rows.GetGuid(2), rows.GetString(3)));
                }
            if (positions && ContextCoherent(item.Action, item.ResourceId, actor.HouseId, before, after, outcome,
                scope, scopeId, customerId, customerBefore, customerAfter, objects))
                context = new("available", version, item.Actor.Id, scope, scope == "systemhaus" ? actor.HouseId : scopeId,
                    customerId, revisionScope, before, after, customerBefore, customerAfter, outcome, objects);
        }
        await using var revision = Command(db, tx, "SELECT revision FROM systemhaus WHERE id=@house", ("house", actor.HouseId));
        long current = (long)(await revision.ExecuteScalarAsync(ct))!;
        await tx.CommitAsync(ct);
        return new(current, item, context);
    }
}
