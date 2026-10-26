using System.Globalization;
using Npgsql;
using RackClick.Domain;

namespace RackClick.Server;

public sealed record AuditActor(Guid Id, string UserName);
public sealed record AdminAuditEvent(Guid Id, DateTime OccurredAt, AuditActor Actor, Guid RequestId, string Action, Guid ResourceId);
public sealed record AdminAuditSnapshot(long Revision, IReadOnlyList<AdminAuditEvent> Events, Guid? NextBeforeId);

public sealed partial class PostgresStore
{
    public async Task<AdminAuditSnapshot> ReadAudit(Actor actor, string? rawLimit, string? rawBeforeId, string? rawActorId, string? rawResourceId, CancellationToken ct)
    {
        await using var db = await source.OpenConnectionAsync(ct);
        await using var tx = await db.BeginTransactionAsync(System.Data.IsolationLevel.RepeatableRead, ct);
        // Global authority and current session precede query validation/cursor lookup.
        await RequireSecurity(db, tx, actor, ct);
        int limit = 50;
        if (rawLimit is not null && (!int.TryParse(rawLimit, NumberStyles.None, CultureInfo.InvariantCulture, out limit) || limit is < 1 or > 100))
            throw new DomainError(422, "request_invalid");
        static Guid? FilterId(string? raw)
        {
            if (raw is null) return null;
            if (raw.Length != 36 || !Guid.TryParseExact(raw, "D", out Guid id) || id == Guid.Empty)
                throw new DomainError(422, "request_invalid");
            return id;
        }
        Guid? filterActor = FilterId(rawActorId), filterResource = FilterId(rawResourceId);
        // One parameterized AND predicate for both cursor membership and page rows.
        string filters = (filterActor.HasValue ? " AND a.actor_id=@filterActor" : "")
                       + (filterResource.HasValue ? " AND a.resource_id=@filterResource" : "");
        void BindFilters(NpgsqlCommand cmd)
        {
            if (filterActor.HasValue) cmd.Parameters.AddWithValue("filterActor", filterActor.Value);
            if (filterResource.HasValue) cmd.Parameters.AddWithValue("filterResource", filterResource.Value);
        }
        Guid? before = null;
        DateTime boundary = default;
        if (rawBeforeId is not null)
        {
            if (!Guid.TryParseExact(rawBeforeId, "D", out Guid parsed) || parsed == Guid.Empty)
                throw new DomainError(422, "request_invalid");
            before = parsed;
            await using var cursor = Command(db, tx, $"SELECT a.occurred_at FROM audit_event a WHERE a.systemhaus_id=@house AND a.id=@id{filters}", ("house", actor.HouseId), ("id", parsed));
            BindFilters(cursor);
            boundary = await cursor.ExecuteScalarAsync(ct) is DateTime timestamp ? timestamp : throw new DomainError(404, "not_found");
        }
        await using var revision = Command(db, tx, "SELECT revision FROM systemhaus WHERE id=@house", ("house", actor.HouseId));
        long current = (long)(await revision.ExecuteScalarAsync(ct))!;
        var events = new List<AdminAuditEvent>();
        string seek = before.HasValue ? "AND (a.occurred_at,a.id)<(@time,@before)" : "";
        // Explicit public metadata only: no before/after JSON, operation payload or identity secrets.
        await using (var cmd = Command(db, tx, $"""
            SELECT a.id,a.occurred_at,a.actor_id,u.username,a.request_id,a.action,a.resource_id
            FROM audit_event a JOIN app_user u ON u.systemhaus_id=a.systemhaus_id AND u.id=a.actor_id
            WHERE a.systemhaus_id=@house {filters} {seek}
            ORDER BY a.occurred_at DESC,a.id DESC LIMIT @take
            """, ("house", actor.HouseId), ("take", limit + 1)))
        {
            BindFilters(cmd);
            if (before.HasValue)
            {
                cmd.Parameters.AddWithValue("time", boundary);
                cmd.Parameters.AddWithValue("before", before.Value);
            }
            await using var rows = await cmd.ExecuteReaderAsync(ct);
            while (await rows.ReadAsync(ct)) events.Add(new(rows.GetGuid(0), rows.GetDateTime(1),
                new(rows.GetGuid(2), rows.GetString(3)), rows.GetGuid(4), rows.GetString(5), rows.GetGuid(6)));
        }
        bool more = events.Count > limit;
        if (more) events.RemoveAt(limit);
        await tx.CommitAsync(ct);
        return new(current, events, more ? events[^1].Id : null);
    }
}
