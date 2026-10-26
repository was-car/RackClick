namespace RackClick.Server;

public static partial class OpenApiDocument
{
    private static void AddUserPortColors(Dictionary<string, object?> paths, Dictionary<string, object?> schemas)
    {
        object uuid = Text("uuid"), boolean = Obj(("type", "boolean"));
        object revision = Obj(("type", "integer"), ("format", "int64"), ("minimum", 0), ("maximum", UserPortColors.MaximumRevision));
        object kind = Obj(("type", "string"), ("enum", new[] { "userPortColors" }));
        object hex = Obj(("type", "string"), ("pattern", "^#[0-9a-f]{6}$"));
        string[] types = ["rj45", "rj45_poe", "sfp", "sfp28", "qsfp", "mgmt", "console", "power", "usb_a", "usb_c"];
        schemas["UserPortColorsMap"] = Obj(("type", "object"), ("minProperties", 0), ("maxProperties", 10),
            ("properties", types.ToDictionary(type => type, _ => hex)), ("additionalProperties", false));
        schemas["UserPortColorsSet"] = Shape(["colors"], ("colors", Ref("UserPortColorsMap")));
        schemas["UserPortColorChange"] = Shape(["colors", "changed"], ("colors", Ref("UserPortColorsMap")), ("changed", boolean));
        schemas["UserPortColorsSnapshot"] = Shape(["kind", "ownerId", "revision", "colors"],
            ("kind", kind), ("ownerId", uuid), ("revision", revision), ("colors", Ref("UserPortColorsMap")));
        schemas["UserPortColorResult"] = Shape(["kind", "ownerId", "revision", "requestId", "operationId", "result"],
            ("kind", kind), ("ownerId", uuid), ("revision", revision), ("requestId", uuid), ("operationId", uuid), ("result", Ref("UserPortColorChange")));
        schemas["UserPortColorStatus"] = Shape(["state", "ownerId", "revision", "requestId", "operation"],
            ("state", Obj(("type", "string"), ("enum", new[] { "notRecorded", "committed", "cancelled" }))),
            ("ownerId", uuid), ("revision", revision), ("requestId", uuid),
            ("operation", Obj(("allOf", new[] { Ref("UserPortColorResult") }), ("nullable", true))));
        foreach (string name in new[] { "UserPortColorsSet", "UserPortColorChange", "UserPortColorsSnapshot", "UserPortColorResult", "UserPortColorStatus" })
            ((Dictionary<string, object?>)schemas[name]!)["additionalProperties"] = false;

        const string authority = "Personal port-type color overrides only. Systemhaus and owner derive exclusively from the active session. All current active users, including readers and users without customer grants, manage themselves. No inventory.edit or new capability. Session revalidated after waits and before commit/return. Independent revision, journal and fences; no inventory/Systemhaus revision or inventory change-feed event. GET/status reject all query/body input. ";
        Dictionary<string, object?> Endpoint(string id, bool mutation, bool requestPath, string response, string description)
        {
            var operation = (Dictionary<string, object?>)Operation(id, authority + description, "200", Ref(response),
                request: mutation ? "UserPortColorsSet" : null, mutation: mutation, etag: true);
            if (!operation.TryGetValue("parameters", out var list)) operation["parameters"] = list = new List<object>();
            var parameters = (List<object>)list!;
            if (mutation)
            {
                parameters.Add(Header("If-Match", "Original personal revision: exact quoted port-colors-N, N=0..9007199254740991 without leading zeroes. Missing 428, malformed 422. Cancel accepts stale original revision.", Obj(("type", "string"), ("pattern", "^\"port-colors-(0|[1-9][0-9]*)\"$"))));
                parameters.Add(Header("Idempotency-Key", "Nonempty UUID scoped to palette/owner; must equal cancellation path requestId.", uuid));
                parameters.Add(Header("X-RackClick-Actor", "Required original actor UUID; mismatch 409 actor_changed.", uuid));
            }
            if (requestPath) parameters.Add(Obj(("in", "path"), ("name", "requestId"), ("required", true), ("schema", uuid)));
            var responses = (Dictionary<string, object?>)operation["responses"]!;
            responses["422"] = Response("Invalid query/body, duplicate/extra/missing keys, null, unknown port type, non-string or non-lowercase #rrggbb color, ETag or UUID.", Ref("Error"));
            responses["409"] = Response("Invalid stored receipt, actor_changed/request_id_reused/operation_cancelled/port_colors_revision_exhausted/port_colors_conflict.", Ref("Error"));
            if (mutation)
            {
                responses["412"] = Response("Personal revision conflict, including stale no-op; do not rebase automatically.", Ref("Error"));
                responses["428"] = Response("Original personal If-Match required.", Ref("Error"));
            }
            ((Dictionary<string, object?>)((Dictionary<string, object?>)responses["200"]!)["headers"]!)["ETag"] =
                Obj(("schema", Text()), ("description", "Exact quoted port-colors-N. POST replay returns historical receipt revision; GET/status/cancel return current revision. Refresh GET after confirmation."));
            return operation;
        }
        paths["/api/v1/me/port-colors"] = Obj(
            ("get", Endpoint("readUserPortColors", false, false, "UserPortColorsSnapshot", "Never inserts. Absent row is revision0/colors{}. Returns overrides only, never defaults.")),
            ("post", Endpoint("setUserPortColors", true, false, "UserPortColorResult", "Exact body {colors:{...}} replaces the entire map, 0..10 allowed type keys. Empty resets all; omitted type resets that type; rj45_poe is distinct. Exact lower-case RGB values are preserved. Key order is canonicalized for digest/comparison. Current revision required for each new intent; no-op journals/audits once without increment, including empty revision0 and maximum revision. Settings/receipt/audit commit atomically. Exact replay returns immutable original receipt.")));
        paths["/api/v1/me/port-colors/operations/{requestId}"] = Obj(
            ("get", Endpoint("readUserPortColorOperation", false, true, "UserPortColorStatus", "Owner-bound notRecorded/committed/cancelled. notRecorded is neither success nor a fence. Outer revision is current; committed operation is the historical receipt, otherwise null.")));
        paths["/api/v1/me/port-colors/operations/{requestId}/cancel"] = Obj(
            ("post", Endpoint("cancelUserPortColorOperation", true, true, "UserPortColorStatus", "Requires original body, requestId, actor and original revision even if stale. Durable fence never erases or undoes a prior commit. Repetition does not duplicate audit. Same-actor reauthentication supports recovery. No expiry/purge in this scope.")));
    }
}
