namespace RackClick.Server;

public static partial class OpenApiDocument
{
    private static void AddUserCategoryColors(Dictionary<string, object?> paths, Dictionary<string, object?> schemas)
    {
        object uuid = Text("uuid"), boolean = Obj(("type", "boolean"));
        object revision = Obj(("type", "integer"), ("format", "int64"), ("minimum", 0), ("maximum", UserCategoryColors.MaximumRevision));
        object kind = Obj(("type", "string"), ("enum", new[] { "userCategoryColors" }));
        object hex = Obj(("type", "string"), ("enum", UserCategoryColors.Swatches));
        string[] types = UserCategoryColors.CanonicalKeys;
        schemas["UserCategoryColorsMap"] = Obj(("type", "object"), ("minProperties", 0), ("maxProperties", 28),
            ("properties", types.ToDictionary(type => type, _ => hex)), ("additionalProperties", false));
        schemas["UserCategoryColorsSet"] = Shape(["colors"], ("colors", Ref("UserCategoryColorsMap")));
        schemas["UserCategoryColorChange"] = Shape(["colors", "changed"], ("colors", Ref("UserCategoryColorsMap")), ("changed", boolean));
        schemas["UserCategoryColorsSnapshot"] = Shape(["kind", "ownerId", "revision", "colors"],
            ("kind", kind), ("ownerId", uuid), ("revision", revision), ("colors", Ref("UserCategoryColorsMap")));
        schemas["UserCategoryColorResult"] = Shape(["kind", "ownerId", "revision", "requestId", "operationId", "result"],
            ("kind", kind), ("ownerId", uuid), ("revision", revision), ("requestId", uuid), ("operationId", uuid), ("result", Ref("UserCategoryColorChange")));
        schemas["UserCategoryColorStatus"] = Shape(["state", "ownerId", "revision", "requestId", "operation"],
            ("state", Obj(("type", "string"), ("enum", new[] { "notRecorded", "committed", "cancelled" }))),
            ("ownerId", uuid), ("revision", revision), ("requestId", uuid),
            ("operation", Obj(("allOf", new[] { Ref("UserCategoryColorResult") }), ("nullable", true))));
        foreach (string name in new[] { "UserCategoryColorsSet", "UserCategoryColorChange", "UserCategoryColorsSnapshot", "UserCategoryColorResult", "UserCategoryColorStatus" })
            ((Dictionary<string, object?>)schemas[name]!)["additionalProperties"] = false;

        const string authority = "Personal category-pair color overrides only. Systemhaus and owner derive exclusively from the active session. All current active users, including readers and users without customer grants, manage themselves. No inventory.edit or new capability. Session revalidated after waits and before commit/return. Independent revision, journal and fences; no inventory/Systemhaus revision or inventory change-feed event. GET/status reject all query/body input. ";
        Dictionary<string, object?> Endpoint(string id, bool mutation, bool requestPath, string response, string description)
        {
            var operation = (Dictionary<string, object?>)Operation(id, authority + description, "200", Ref(response),
                request: mutation ? "UserCategoryColorsSet" : null, mutation: mutation, etag: true);
            if (!operation.TryGetValue("parameters", out var list)) operation["parameters"] = list = new List<object>();
            var parameters = (List<object>)list!;
            if (mutation)
            {
                parameters.Add(Header("If-Match", "Original personal revision: exact quoted category-colors-N, N=0..9007199254740991 without leading zeroes. Missing 428, malformed 422. Cancel accepts stale original revision.", Obj(("type", "string"), ("pattern", "^\"category-colors-(0|[1-9][0-9]*)\"$"))));
                parameters.Add(Header("Idempotency-Key", "Nonempty UUID scoped to palette/owner; must equal cancellation path requestId.", uuid));
                parameters.Add(Header("X-RackClick-Actor", "Required original actor UUID; mismatch 409 actor_changed.", uuid));
            }
            if (requestPath) parameters.Add(Obj(("in", "path"), ("name", "requestId"), ("required", true), ("schema", uuid)));
            var responses = (Dictionary<string, object?>)operation["responses"]!;
            responses["422"] = Response("Invalid query/body, duplicate/extra/missing keys, null, unknown category pair, non-string or a color outside the ten exact lower-case swatches, ETag or UUID.", Ref("Error"));
            responses["409"] = Response("Invalid stored receipt, actor_changed/request_id_reused/operation_cancelled/category_colors_revision_exhausted/category_colors_conflict.", Ref("Error"));
            if (mutation)
            {
                responses["412"] = Response("Personal revision conflict, including stale no-op; do not rebase automatically.", Ref("Error"));
                responses["428"] = Response("Original personal If-Match required.", Ref("Error"));
            }
            ((Dictionary<string, object?>)((Dictionary<string, object?>)responses["200"]!)["headers"]!)["ETag"] =
                Obj(("schema", Text()), ("description", "Exact quoted category-colors-N. POST replay returns historical receipt revision; GET/status/cancel return current revision. Refresh GET after confirmation."));
            return operation;
        }
        paths["/api/v1/me/category-colors"] = Obj(
            ("get", Endpoint("readUserCategoryColors", false, false, "UserCategoryColorsSnapshot", "Never inserts. Absent row is revision0/colors{}. Returns overrides only, never defaults.")),
            ("post", Endpoint("setUserCategoryColors", true, false, "UserCategoryColorResult", "Exact body {colors:{...}} replaces the entire map, 0..28 canonical category-pair keys. Empty resets all; omitted pair resets that pair. Only the ten exact RC9 swatches are accepted. Pair keys use ordinal category sorting and the arrow ↔ without spaces. Editing the preference never recolors inventory. On new single/batch connections only, the server reads one committed map and uses explicit valid non-null connection color, then UUID-derived pair color, then null. Existing/update/reconnect/replay retain original colors. Key order is canonicalized for digest/comparison. Current revision required for each new intent; no-op journals/audits once without increment, including empty revision0 and maximum revision. Settings/receipt/audit commit atomically. Exact replay returns immutable original receipt.")));
        paths["/api/v1/me/category-colors/operations/{requestId}"] = Obj(
            ("get", Endpoint("readUserCategoryColorOperation", false, true, "UserCategoryColorStatus", "Owner-bound notRecorded/committed/cancelled. notRecorded is neither success nor a fence. Outer revision is current; committed operation is the historical receipt, otherwise null.")));
        paths["/api/v1/me/category-colors/operations/{requestId}/cancel"] = Obj(
            ("post", Endpoint("cancelUserCategoryColorOperation", true, true, "UserCategoryColorStatus", "Requires original body, requestId, actor and original revision even if stale. Durable fence never erases or undoes a prior commit. Repetition does not duplicate audit. Same-actor reauthentication supports recovery. No expiry/purge in this scope.")));
    }
}
