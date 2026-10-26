using System.Text.Json;
using RackClick.Domain;

namespace RackClick.Server;

public sealed record AuditAdministrativeField(string Field, string Type, string? Before, string? After);
public sealed record AdminAuditAdministrativeDetail(string Status, IReadOnlyList<AuditAdministrativeField> Fields);
public sealed record AdminAuditAdministrativeDetailSnapshot(long Revision, AdminAuditEvent Event,
    AdminAuditAdministrativeDetail Detail);

public sealed partial class PostgresStore
{
    private static AdminAuditAdministrativeDetail AdministrativeDetail(AdminAuditEvent item, Guid houseId,
        string? before, string? after)
    {
        var unavailable = new AdminAuditAdministrativeDetail("unavailable", []);
        if (after is null) return unavailable;
        try
        {
            using var prior = JsonDocument.Parse(before ?? "null", new JsonDocumentOptions { MaxDepth = 8 });
            using var next = JsonDocument.Parse(after, new JsonDocumentOptions { MaxDepth = 8 });
            var a = prior.RootElement;
            var b = next.RootElement;
            var fields = new List<AuditAdministrativeField>();
            void Require(bool valid) { if (!valid) throw new JsonException(); }
            JsonElement Property(JsonElement value, string key) =>
                value.ValueKind == JsonValueKind.Object && value.TryGetProperty(key, out var result)
                    ? result : throw new JsonException();
            string Text(JsonElement value, string key)
            {
                var result = Property(value, key);
                return result.ValueKind == JsonValueKind.String ? result.GetString()! : throw new JsonException();
            }
            string Id(JsonElement value, string key)
            {
                string raw = Text(value, key);
                Require(raw.Length == 36 && Guid.TryParseExact(raw, "D", out var parsed) && parsed != Guid.Empty);
                return Guid.ParseExact(raw, "D").ToString("D");
            }
            string Boolean(JsonElement value, string key) => Property(value, key).ValueKind switch
            {
                JsonValueKind.True => "true", JsonValueKind.False => "false", _ => throw new JsonException()
            };
            string Name(JsonElement value, string key, int maximum = 100)
            {
                string raw = Text(value, key);
                Require(Names.Validate(raw, maximum) == raw);
                return raw;
            }
            void Field(string key, string type, string? oldValue, string? newValue) =>
                fields.Add(new(key, type, oldValue, newValue));
            void SameId(string property, string field)
            {
                string oldValue = Id(a, property), newValue = Id(b, property);
                Require(oldValue == newValue);
                Field(field, "uuid", oldValue, newValue);
            }
            void Resource(string value) => Require(value == item.ResourceId.ToString("D") && item.ResourceId != Guid.Empty);
            void User(bool create, bool reset)
            {
                string id = Id(b, "id"), name = Name(b, "userName", UserNames.MaximumRunes), active = Boolean(b, "active");
                Resource(id);
                if (create)
                {
                    Require(a.ValueKind == JsonValueKind.Null && active == "true");
                    Field("userId", "uuid", null, id);
                    Field("userName", "userName", null, name);
                    Field("active", "boolean", null, active);
                }
                else
                {
                    Require(Id(a, "id") == id && Name(a, "userName", UserNames.MaximumRunes) == name);
                    string oldActive = Boolean(a, "active");
                    if (reset) Require(oldActive == active);
                    Field("userId", "uuid", id, id);
                    Field("userName", "userName", name, name);
                    Field("active", "boolean", oldActive, active);
                }
                if (reset)
                {
                    Require(Boolean(b, "passwordReset") == "true");
                    Field("passwordReset", "boolean", null, "true");
                }
            }
            Require(item.ResourceId != Guid.Empty);
            if (item.Action.EndsWith(".cancel", StringComparison.Ordinal))
            {
                string action = item.Action[..^7];
                Require(action is "user.create" or "userGroup.create" or "customerGroup.create"
                    or "userGroup.member.set" or "customerGroup.member.set" or "userGroup.grant.set"
                    or "user.state.set" or "user.password.reset" or "user.session.revoke");
                if (action == "user.session.revoke")
                {
                    Field("userId", "uuid", Id(a, "userId"), null);
                    string session = Id(a, "sessionId");
                    Resource(session);
                    Field("sessionId", "uuid", session, null);
                }
                else Require(a.ValueKind == JsonValueKind.Null);
                if (action is "user.create" or "userGroup.create" or "customerGroup.create")
                    Require(item.ResourceId == houseId);
                string request = Id(b, "requestId");
                Require(item.RequestId != Guid.Empty && request == item.RequestId.ToString("D")
                    && Text(b, "state") == "cancelled" && Property(b, "operation").ValueKind == JsonValueKind.Null);
                Field("requestId", "uuid", null, request);
                Field("state", "state", null, "cancelled");
            }
            else switch (item.Action)
            {
                case "user.create": User(true, false); break;
                case "user.state.set": User(false, false); break;
                case "user.password.reset": User(false, true); break;
                case "userGroup.create":
                case "customerGroup.create":
                    Require(a.ValueKind == JsonValueKind.Null);
                    string group = Id(b, "id"), kind = Text(b, "kind");
                    Resource(group);
                    Require(kind == (item.Action == "userGroup.create" ? "userGroup" : "customerGroup"));
                    Field("groupId", "uuid", null, group);
                    Field("name", "name", null, Name(b, "name"));
                    Field("groupKind", "groupKind", null, kind);
                    break;
                case "userGroup.member.set":
                case "customerGroup.member.set":
                    SameId("groupId", "groupId");
                    Resource(Id(b, "groupId"));
                    string member = item.Action == "userGroup.member.set" ? "userId" : "customerId";
                    SameId(member, member);
                    Field("assigned", "boolean", Boolean(a, "assigned"), Boolean(b, "assigned"));
                    break;
                case "userGroup.grant.set":
                    SameId("groupId", "groupId");
                    Resource(Id(b, "groupId"));
                    SameId("grantId", "grantId");
                    string capability = Text(b, "capability"), scope = Text(b, "scope");
                    Require(Capabilities.FoundationAdmin.Contains(capability) && Text(a, "capability") == capability
                        && scope is "systemhaus" or "customer" or "customerGroup" && Text(a, "scope") == scope);
                    Field("capability", "capability", capability, capability);
                    Field("scope", "scope", scope, scope);
                    if (scope == "systemhaus")
                    {
                        Require(Property(a, "targetId").ValueKind == JsonValueKind.Null
                            && Property(b, "targetId").ValueKind == JsonValueKind.Null);
                        Field("targetId", "uuid", null, null);
                    }
                    else SameId("targetId", "targetId");
                    Field("assigned", "boolean", Boolean(a, "assigned"), Boolean(b, "assigned"));
                    break;
                case "user.session.revoke":
                    SameId("userId", "userId");
                    SameId("sessionId", "sessionId");
                    Resource(Id(b, "sessionId"));
                    string wasCurrent = Boolean(b, "wasCurrent");
                    Require(Boolean(b, "revoked") == "true"
                        && (wasCurrent != "true" || Id(b, "userId") == item.Actor.Id.ToString("D")));
                    Field("revoked", "boolean", null, "true");
                    Field("wasCurrent", "boolean", null, wasCurrent);
                    break;
                default: return unavailable;
            }
            return new("available", fields);
        }
        catch (JsonException) { return unavailable; }
        catch (DomainError) { return unavailable; }
    }

    public async Task<AdminAuditAdministrativeDetailSnapshot> ReadAuditAdministrativeDetail(Actor actor,
        string rawEventId, CancellationToken ct)
    {
        await using var db = await source.OpenConnectionAsync(ct);
        await using var tx = await db.BeginTransactionAsync(System.Data.IsolationLevel.RepeatableRead, ct);
        await RequireSecurity(db, tx, actor, ct);
        if (rawEventId.Length != 36 || !Guid.TryParseExact(rawEventId, "D", out var id) || id == Guid.Empty)
            throw new DomainError(422, "request_invalid");
        // Only these writer contracts can cross the JSON boundary, with independent byte limits.
        const string eligible = "a.action IN ('user.create','userGroup.create','customerGroup.create',"
            + "'userGroup.member.set','customerGroup.member.set','userGroup.grant.set','user.state.set',"
            + "'user.password.reset','user.session.revoke','user.create.cancel','userGroup.create.cancel',"
            + "'customerGroup.create.cancel','userGroup.member.set.cancel','customerGroup.member.set.cancel',"
            + "'userGroup.grant.set.cancel','user.state.set.cancel','user.password.reset.cancel','user.session.revoke.cancel') "
            + "AND (a.before_json IS NULL OR octet_length(a.before_json::text)<=4096) "
            + "AND octet_length(a.after_json::text)<=4096";
        AdminAuditEvent item;
        AdminAuditAdministrativeDetail detail;
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
            detail = AdministrativeDetail(item, actor.HouseId, row.IsDBNull(7) ? null : row.GetString(7),
                row.IsDBNull(8) ? null : row.GetString(8));
        }
        await using var revision = Command(db, tx, "SELECT revision FROM systemhaus WHERE id=@house", ("house", actor.HouseId));
        long current = (long)(await revision.ExecuteScalarAsync(ct))!;
        await tx.CommitAsync(ct);
        return new(current, item, detail);
    }
}
