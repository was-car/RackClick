namespace RackClick.Server;

public static partial class OpenApiDocument
{
    private static void AddUserPreferences(Dictionary<string, object?> paths, Dictionary<string, object?> schemas)
    {
        object uuid = Text("uuid"), boolean = Obj(("type", "boolean"));
        object revision = Obj(("type", "integer"), ("format", "int64"), ("minimum", 0), ("maximum", UserPreferences.MaximumRevision));
        object key = Obj(("type", "string"), ("enum", new[] { "language", "theme" }));
        object value = Obj(("type", "string"), ("enum", new[] { "en", "de", "es", "dark", "light" }));
        object kind = Obj(("type", "string"), ("enum", new[] { "userPreferences" }));
        schemas["UserPreferenceSet"] = Shape(["key", "value"], ("key", key), ("value", value));
        // Pair constraints are explicit: language cannot be set to a theme or vice versa.
        ((Dictionary<string, object?>)schemas["UserPreferenceSet"]!)["oneOf"] = new object[] {
            Obj(("properties", Obj(("key", Obj(("enum", new[] { "language" }))), ("value", Obj(("enum", new[] { "en", "de", "es" })))))),
            Obj(("properties", Obj(("key", Obj(("enum", new[] { "theme" }))), ("value", Obj(("enum", new[] { "dark", "light" })))))) };
        schemas["UserPreferenceChange"] = Shape(["key", "value", "changed"], ("key", key), ("value", value), ("changed", boolean));
        ((Dictionary<string, object?>)schemas["UserPreferenceChange"]!)["oneOf"] = ((Dictionary<string, object?>)schemas["UserPreferenceSet"]!)["oneOf"];
        schemas["UserPreferencesSnapshot"] = Shape(["kind", "ownerId", "revision", "language", "theme"],
            ("kind", kind), ("ownerId", uuid), ("revision", revision),
            ("language", Obj(("type", "string"), ("nullable", true), ("enum", new object?[] { "en", "de", "es", null }))),
            ("theme", Obj(("type", "string"), ("nullable", true), ("enum", new object?[] { "dark", "light", null }))));
        schemas["UserPreferenceResult"] = Shape(["kind", "ownerId", "revision", "requestId", "operationId", "result"],
            ("kind", kind), ("ownerId", uuid), ("revision", revision), ("requestId", uuid), ("operationId", uuid), ("result", Ref("UserPreferenceChange")));
        schemas["UserPreferenceStatus"] = Shape(["state", "ownerId", "revision", "requestId", "operation"],
            ("state", Obj(("type", "string"), ("enum", new[] { "notRecorded", "committed", "cancelled" }))),
            ("ownerId", uuid), ("revision", revision), ("requestId", uuid),
            ("operation", Obj(("allOf", new[] { Ref("UserPreferenceResult") }), ("nullable", true))));
        foreach (string name in new[] { "UserPreferenceSet", "UserPreferenceChange", "UserPreferencesSnapshot", "UserPreferenceResult", "UserPreferenceStatus" })
            ((Dictionary<string, object?>)schemas[name]!)["additionalProperties"] = false;

        const string authority = "Personal language/theme only. Systemhaus and owner derive exclusively from the active current session. All authenticated active users, including readers and users with no customer grants, manage only themselves. No customer selector, customer permission, inventory.edit or new capability. Session revalidated after waits and before commit/return. No inventory/Systemhaus/customer revision or inventory change-feed event. Read/query bodies closed: GET and status reject any query or body. ";
        Dictionary<string, object?> Endpoint(string id, bool mutation, bool requestPath, string response, string description)
        {
            var operation = (Dictionary<string, object?>)Operation(id, authority + description, "200", Ref(response),
                request: mutation ? "UserPreferenceSet" : null, mutation: mutation, etag: true);
            if (!operation.TryGetValue("parameters", out var list)) operation["parameters"] = list = new List<object>();
            var parameters = (List<object>)list!;
            if (mutation)
            {
                parameters.Add(Header("If-Match", "Original personal revision: exact quoted preferences-N, N=0..9007199254740991, no leading zeroes. Missing 428, malformed 422. Cancel accepts stale original revision.", Obj(("type", "string"), ("pattern", "^\"preferences-(0|[1-9][0-9]*)\"$"))));
                parameters.Add(Header("Idempotency-Key", "Nonempty UUID scoped to this personal family/owner; equals requestId in the cancellation path.", uuid));
                parameters.Add(Header("X-RackClick-Actor", "Required original actor UUID, mismatch 409 actor_changed.", uuid));
            }
            if (requestPath) parameters.Add(Obj(("in", "path"), ("name", "requestId"), ("required", true), ("schema", uuid)));
            var responses = (Dictionary<string, object?>)operation["responses"]!;
            responses["422"] = Response("Invalid query/body, duplicate/extra/missing JSON keys, null/invalid enum pair, personal ETag or UUID.", Ref("Error"));
            responses["409"] = Response("Invalid stored receipt, or mutation actor_changed/request_id_reused/operation_cancelled/preferences_revision_exhausted/preferences_conflict.", Ref("Error"));
            if (mutation)
            {
                responses["412"] = Response("Personal revision conflict, including stale no-op; do not rebase automatically.", Ref("Error"));
                responses["428"] = Response("Original personal If-Match required.", Ref("Error"));
            }
            ((Dictionary<string, object?>)((Dictionary<string, object?>)responses["200"]!)["headers"]!)["ETag"] =
                Obj(("schema", Text()), ("description", "Exact quoted preferences-N personal revision. POST replay returns historical result revision; GET/status/cancel current revision. Always GET after confirmation before applying settings."));
            return operation;
        }
        paths["/api/v1/me/preferences"] = Obj(
            ("get", Endpoint("readUserPreferences", false, false, "UserPreferencesSnapshot", "GET never inserts. Absent row yields revision0 and language/theme null; null means preserve this browser's anonymous fallback.")),
            ("post", Endpoint("setUserPreference", true, false, "UserPreferenceResult", "Closed explicit two-key SET changes only that key. Current revision required for every new intent; no-op commits one journal/audit with unchanged revision, including at the maximum. Exhausted revision rejects a changed value without writing. Exact replay returns immutable original result; receipt, audit and settings commit atomically. Refresh GET after confirmation.")));
        paths["/api/v1/me/preferences/operations/{requestId}"] = Obj(
            ("get", Endpoint("readUserPreferenceOperation", false, true, "UserPreferenceStatus", "Actor-bound notRecorded/committed/cancelled. notRecorded is neither success nor a fence. Outer revision is current; operation is null except committed, whose receipt remains historical.")));
        paths["/api/v1/me/preferences/operations/{requestId}/cancel"] = Obj(
            ("post", Endpoint("cancelUserPreferenceOperation", true, true, "UserPreferenceStatus", "Requires original body, request UUID, actor and revision even if revision changed. Durable cancellation fence does not undo committed settings. Replay/cancel repetition never duplicates audit. Reauthentication as the same actor permits recovery; another actor cannot recover this intent. No expiry/purge in this scope.")));
    }
}
