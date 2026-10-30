using System.Text.Json;
using Npgsql;
using RackClick.Domain;

namespace RackClick.Server;

public sealed record AuditNameState(string Name, long Revision);
public sealed record AdminAuditDetail(string Status, string? RevisionScope, Guid? CustomerId,
    AuditNameState? Before, AuditNameState? After);
public sealed record AdminAuditDetailSnapshot(long Revision, AdminAuditEvent Event, AdminAuditDetail Detail);

public sealed partial class PostgresStore
{
    private static AdminAuditDetail NameDetail(AdminAuditEvent item, Guid houseId, string? before, string? after)
    {
        var unavailable = new AdminAuditDetail("unavailable", null, null, null, null);
        bool house = item.Action == "systemhaus.rename", create = item.Action == "customer.create";
        if ((!house && !create && item.Action != "customer.rename") || after is null) return unavailable;
        try
        {
            using var prior = JsonDocument.Parse(before ?? "null", new JsonDocumentOptions { MaxDepth = 8 });
            using var next = JsonDocument.Parse(after, new JsonDocumentOptions { MaxDepth = 8 });
            AuditNameState? State(JsonElement value)
            {
                if (value.ValueKind != JsonValueKind.Object) return null;
                bool Id(string property, Guid expected) => value.TryGetProperty(property, out var id)
                    && id.ValueKind == JsonValueKind.String && id.GetString() is { Length: 36 } raw
                    && Guid.TryParseExact(raw, "D", out var parsed) && parsed != Guid.Empty && parsed == expected;
                if (!Id("id", item.ResourceId) || (house ? item.ResourceId != houseId : !Id("houseId", houseId))
                    || !value.TryGetProperty("name", out var name) || name.ValueKind != JsonValueKind.String
                    || !value.TryGetProperty("revision", out var rev) || rev.ValueKind != JsonValueKind.Number
                    || !rev.TryGetInt64(out long revision) || revision < 1) return null;
                string text = name.GetString()!;
                // Historical display must not trim, translate or replace invalid names.
                if (Names.Validate(text) != text) return null;
                return new(text, revision);
            }
            var afterState = State(next.RootElement);
            if (afterState is null) return unavailable;
            AuditNameState? beforeState = null;
            if (create)
            {
                if (prior.RootElement.ValueKind != JsonValueKind.Null || afterState.Revision != 1) return unavailable;
            }
            else
            {
                beforeState = State(prior.RootElement);
                if (beforeState is null || beforeState.Revision == long.MaxValue
                    || afterState.Revision != beforeState.Revision + 1) return unavailable;
            }
            return new("available", house ? "systemhaus" : "customer", house ? null : item.ResourceId,
                beforeState, afterState);
        }
        catch (JsonException) { return unavailable; }
        catch (DomainError) { return unavailable; }
    }

    public async Task<AdminAuditDetailSnapshot> ReadAuditDetail(Actor actor, string rawEventId, CancellationToken ct)
    {
        await using var db = await source.OpenConnectionAsync(ct);
        await using var tx = await db.BeginTransactionAsync(System.Data.IsolationLevel.RepeatableRead, ct);
        await RequireSecurity(db, tx, actor, ct);
        if (rawEventId.Length != 36 || !Guid.TryParseExact(rawEventId, "D", out var id) || id == Guid.Empty)
            throw new DomainError(422, "request_invalid");
        // Transfer bounded historical payloads only for the three supported writer shapes.
        // Unknown actions, large JSON and invalid historical shapes retain metadata, never raw JSON.
        const string eligible = "a.action IN ('systemhaus.rename','customer.create','customer.rename') "
            + "AND (a.before_json IS NULL OR octet_length(a.before_json::text)<=4096) "
            + "AND octet_length(a.after_json::text)<=4096";
        AdminAuditEvent item;
        AdminAuditDetail detail;
        await using (var cmd = Command(db, tx, $"""
            SELECT a.id,a.occurred_at,a.actor_id,u.username,a.request_id,a.action,a.resource_id,
                CASE WHEN {eligible} THEN a.before_json::text END,
                CASE WHEN {eligible} THEN a.after_json::text END
            FROM audit_event a JOIN app_user u ON u.systemhaus_id=a.systemhaus_id AND u.id=a.actor_id
            WHERE a.systemhaus_id=@house AND a.id=@id
            """, ("house", actor.HouseId), ("id", id)))
        await using (var row = await cmd.ExecuteReaderAsync(ct))
        {
            if (!await row.ReadAsync(ct)) throw new DomainError(404, "not_found");
            item = new(row.GetGuid(0), row.GetDateTime(1), new(row.GetGuid(2), row.GetString(3)),
                row.GetGuid(4), row.GetString(5), row.GetGuid(6));
            detail = NameDetail(item, actor.HouseId, row.IsDBNull(7) ? null : row.GetString(7),
                row.IsDBNull(8) ? null : row.GetString(8));
        }
        await using var revision = Command(db, tx, "SELECT revision FROM systemhaus WHERE id=@house", ("house", actor.HouseId));
        long current = (long)(await revision.ExecuteScalarAsync(ct))!;
        await tx.CommitAsync(ct);
        return new(current, item, detail);
    }
}
