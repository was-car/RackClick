namespace RackClick.Server;

public static partial class OpenApiDocument
{
    private static void AddAudit(Dictionary<string, object?> paths, Dictionary<string, object?> schemas)
    {
        schemas["AuditActor"] = Shape(["id", "userName"], ("id", Text("uuid")), ("userName", Text()));
        schemas["AdminAuditEvent"] = Shape(["id", "occurredAt", "actor", "requestId", "action", "resourceId"],
            ("id", Text("uuid")), ("occurredAt", Text("date-time")), ("actor", Ref("AuditActor")),
            ("requestId", Text("uuid")), ("action", Text()), ("resourceId", Text("uuid")));
        schemas["AdminAuditSnapshot"] = Shape(["revision", "events", "nextBeforeId"],
            ("revision", Obj(("type", "integer"), ("format", "int64"), ("minimum", 1))),
            ("events", ArrayOf(Ref("AdminAuditEvent"))),
            ("nextBeforeId", Obj(("type", "string"), ("format", "uuid"), ("nullable", true))));
        var get = (Dictionary<string, object?>)Operation("readAdminAudit",
            "Current GLOBAL security.manage required before query validation/cursor lookup. Own Systemhaus committed event metadata only, no raw before/after JSON. Actor name is current, not historical. Ordered occurredAt DESC then UUID DESC; beforeId is exclusive and must match any actorId/resourceId filters. Filters combine with AND, exact UUID identity without object lookups; valid unknown/foreign filter IDs return no rows, not existence errors. One consistent read per page, not a cross-page snapshot or notifications feed. Revision/ETag is Systemhaus revision, not an audit watermark (inventory may change it independently).",
            "200", Ref("AdminAuditSnapshot"), etag: true);
        get["parameters"] = new object[] {
            Obj(("in", "query"), ("name", "limit"), ("required", false), ("description", "ASCII decimal digits only, 1..100; default 50. Empty/repeated values are invalid."),
                ("schema", Obj(("type", "integer"), ("minimum", 1), ("maximum", 100), ("default", 50)))),
            Obj(("in", "query"), ("name", "beforeId"), ("required", false), ("description", "Existing own event UUID in D form, nonempty. Foreign and absent cursors have the same response."), ("schema", Text("uuid"))),
            Obj(("in", "query"), ("name", "actorId"), ("required", false), ("description", "Optional exact actor UUID D, 36 characters, nonzero. Empty, repeated, whitespace or other UUID formats are invalid. Current actor names are not filter identities."), ("schema", Text("uuid"))),
            Obj(("in", "query"), ("name", "resourceId"), ("required", false), ("description", "Optional exact audited resource UUID D, 36 characters, nonzero. Combined with actorId using AND. No live resource lookup; deleted objects remain searchable."), ("schema", Text("uuid"))) };
        var responses = (Dictionary<string, object?>)get["responses"]!;
        responses["404"] = Response("Cursor absent, outside the administrator's Systemhaus, or outside the selected filters.", Ref("Error"));
        responses["422"] = Response("Invalid limit, cursor UUID or filter UUID.", Ref("Error"));
        paths["/api/v1/admin/audit"] = Obj(("get", get));
        var state = (Dictionary<string, object?>)Shape(["name", "revision"],
            ("name", Text()), ("revision", Obj(("type", "integer"), ("format", "int64"), ("minimum", 1))));
        state["nullable"] = true;
        schemas["AuditNameState"] = state;
        schemas["AdminAuditDetail"] = Shape(["status", "revisionScope", "customerId", "before", "after"],
            ("status", Obj(("type", "string"), ("enum", new[] { "available", "unavailable" }))),
            ("revisionScope", Obj(("type", "string"), ("nullable", true), ("enum", new object?[] { "systemhaus", "customer", null }))),
            ("customerId", Obj(("type", "string"), ("format", "uuid"), ("nullable", true))),
            ("before", Ref("AuditNameState")), ("after", Ref("AuditNameState")));
        schemas["AdminAuditDetailSnapshot"] = Shape(["revision", "event", "detail"],
            ("revision", Obj(("type", "integer"), ("format", "int64"), ("minimum", 1))),
            ("event", Ref("AdminAuditEvent")), ("detail", Ref("AdminAuditDetail")));
        var detail = (Dictionary<string, object?>)Operation("readAdminAuditDetail",
            "Current GLOBAL security.manage and own Systemhaus before event ID validation/lookup. Exact nonzero UUID D (36 characters). Metadata is unchanged; actor name is current. Only systemhaus.rename, customer.create and customer.rename have typed historical name/revision detail, with verified identities and revision succession. Customer ID comes from the historical event, without current object/operation lookup. Rename to the same name is valid. Other actions, unsupported shapes, invalid identities/revisions/names, JSON deeper than 8 or either payload over 4096 UTF8 bytes return detail.status=unavailable and all other detail fields null. Available detail has revisionScope and after; before is null only on customer.create. No raw JSON, identity secrets or arbitrary nested properties. Revision/ETag is the current Systemhaus revision, not the historical resource revision, inventory watermark or audit version. GET never mutates data.",
            "200", Ref("AdminAuditDetailSnapshot"), etag: true);
        detail["parameters"] = new object[] { Obj(("in", "path"), ("name", "eventId"), ("required", true),
            ("description", "Exact UUID D, nonzero, 36 characters; uppercase accepted. Invalid formats are checked after global authorization."), ("schema", Text("uuid"))) };
        var detailResponses = (Dictionary<string, object?>)detail["responses"]!;
        detailResponses["404"] = Response("Event absent or outside own Systemhaus; indistinguishable response.", Ref("Error"));
        detailResponses["422"] = Response("Invalid event UUID.", Ref("Error"));
        paths["/api/v1/admin/audit/{eventId}"] = Obj(("get", detail));
        schemas["AuditAdministrativeField"] = Shape(["field", "type", "before", "after"],
            ("field", Obj(("type", "string"), ("enum", new[] { "userId", "userName", "active", "passwordReset",
                "groupId", "name", "groupKind", "customerId", "assigned", "grantId", "capability", "scope", "targetId",
                "sessionId", "revoked", "wasCurrent", "requestId", "state" }))),
            ("type", Obj(("type", "string"), ("enum", new[] { "uuid", "userName", "boolean", "name", "groupKind", "capability", "scope", "state" }))),
            ("before", Obj(("type", "string"), ("nullable", true))),
            ("after", Obj(("type", "string"), ("nullable", true))));
        schemas["AdminAuditAdministrativeDetail"] = Shape(["status", "fields"],
            ("status", Obj(("type", "string"), ("enum", new[] { "available", "unavailable" }))),
            ("fields", ArrayOf(Ref("AuditAdministrativeField"))));
        schemas["AdminAuditAdministrativeDetailSnapshot"] = Shape(["revision", "event", "detail"],
            ("revision", Obj(("type", "integer"), ("format", "int64"), ("minimum", 1))),
            ("event", Ref("AdminAuditEvent")), ("detail", Ref("AdminAuditAdministrativeDetail")));
        var administrative = (Dictionary<string, object?>)Operation("readAdminAuditAdministrativeDetail",
            "Current GLOBAL security.manage and own Systemhaus before strict nonzero UUID D validation/lookup. Metadata matches the audit list; actor name is current. Typed fixed fields for nine administrative writer actions and their cancellations only. Both historical payloads must match their writer's types, identities and coherence; either payload over 4096 UTF8 bytes, JSON depth over 8, unknown action or invalid shape returns unavailable with fields empty. Extras are ignored and never exposed. Field order/type is fixed per action; values are strings or null, UUID D canonical, booleans true/false and finite codes. Names preserve original validated Unicode/case. No secret/raw JSON/current resource/operation lookup or inferred historical revision; null means no value published on that side, not reconstructed context. Cancel publishes requestId/state only, except session cancellation also publishes before userId/sessionId. Current Systemhaus revision/ETag, RepeatableRead, no mutation; existing name-detail route unchanged. See API-ADMIN-AUDITORIA-CAMBIOS-S1.md for action-specific field order.",
            "200", Ref("AdminAuditAdministrativeDetailSnapshot"), etag: true);
        administrative["parameters"] = new object[] { Obj(("in", "path"), ("name", "eventId"), ("required", true),
            ("description", "Exact nonzero UUID D, 36 characters; uppercase accepted after current global authorization."), ("schema", Text("uuid"))) };
        var administrativeResponses = (Dictionary<string, object?>)administrative["responses"]!;
        administrativeResponses["404"] = Response("Event absent or outside own Systemhaus; indistinguishable response.", Ref("Error"));
        administrativeResponses["422"] = Response("Invalid event UUID.", Ref("Error"));
        paths["/api/v1/admin/audit/{eventId}/administrative-detail"] = Obj(("get", administrative));
        schemas["AuditContextObject"] = Shape(["kind", "id", "relation"],
            ("kind", Obj(("type", "string"), ("enum", new[] { "systemhaus", "user", "userGroup", "customerGroup", "customer", "grant", "session" }))),
            ("id", Text("uuid")),
            ("relation", Obj(("type", "string"), ("enum", new[] { "target", "intendedTarget", "member", "intendedMember", "scope", "intendedScope" }))));
        schemas["AdminAuditContext"] = Shape(["status", "captureVersion", "actorId", "scopeKind", "scopeId", "customerId",
            "revisionScope", "revisionBefore", "revisionAfter", "customerRevisionBefore", "customerRevisionAfter", "outcome", "objects"],
            ("status", Obj(("type", "string"), ("enum", new[] { "available", "notRecorded" }))),
            ("captureVersion", Obj(("type", "integer"), ("nullable", true), ("enum", new object?[] { 1, null }))),
            ("actorId", Obj(("type", "string"), ("format", "uuid"), ("nullable", true))),
            ("scopeKind", Obj(("type", "string"), ("nullable", true), ("enum", new object?[] { "systemhaus", "customer", null }))),
            ("scopeId", Obj(("type", "string"), ("format", "uuid"), ("nullable", true))),
            ("customerId", Obj(("type", "string"), ("format", "uuid"), ("nullable", true))),
            ("revisionScope", Obj(("type", "string"), ("nullable", true), ("enum", new object?[] { "systemhaus", null }))),
            ("revisionBefore", Obj(("type", "integer"), ("format", "int64"), ("minimum", 1), ("nullable", true))),
            ("revisionAfter", Obj(("type", "integer"), ("format", "int64"), ("minimum", 1), ("nullable", true))),
            ("customerRevisionBefore", Obj(("type", "integer"), ("format", "int64"), ("minimum", 1), ("nullable", true))),
            ("customerRevisionAfter", Obj(("type", "integer"), ("format", "int64"), ("minimum", 1), ("nullable", true))),
            ("outcome", Obj(("type", "string"), ("nullable", true), ("enum", new object?[] { "committed", "cancelled", null }))),
            ("objects", Obj(("type", "array"), ("items", Ref("AuditContextObject")), ("maxItems", 3))));
        schemas["AdminAuditContextSnapshot"] = Shape(["revision", "event", "context"],
            ("revision", Obj(("type", "integer"), ("format", "int64"), ("minimum", 1))),
            ("event", Ref("AdminAuditEvent")), ("context", Ref("AdminAuditContext")));
        var context = (Dictionary<string, object?>)Operation("readAdminAuditContext",
            "Current GLOBAL security.manage and own Systemhaus before strict nonzero UUID D validation/lookup. RepeatableRead and current Systemhaus revision/ETag. Capture version1 finite shapes for21 administrative/name actions, integrated by writer family without backfill. Existing revisionScope/before/after always describe historical Systemhaus revisions; customer.create/rename additionally have customer scope/id and nullable customerRevisionBefore/After (create null->1). Other actions keep customer fields null. Ordered1..3 typed direct references; session uses exact public UUID, cancellation uses explicit intended references and unknown creation targets use House. No historical actor name, indirect session enumeration, raw JSON, secrets, live resource or operation lookup. Missing/unsupported/incoherent capture is notRecorded with all nullable fields null and objects empty. GET never mutates;46/50 unchanged. See API-ADMIN-AUDITORIA-CONTEXTO-21-S1.md for exact action/object order and capture stage.",
            "200", Ref("AdminAuditContextSnapshot"), etag: true);
        context["parameters"] = new object[] { Obj(("in", "path"), ("name", "eventId"), ("required", true),
            ("description", "Exact nonzero UUID D, 36 characters; uppercase accepted after current global authorization."), ("schema", Text("uuid"))) };
        var contextResponses = (Dictionary<string, object?>)context["responses"]!;
        contextResponses["404"] = Response("Event absent or outside own Systemhaus; indistinguishable response.", Ref("Error"));
        contextResponses["422"] = Response("Invalid event UUID.", Ref("Error"));
        paths["/api/v1/admin/audit/{eventId}/context"] = Obj(("get", context));
    }
}
