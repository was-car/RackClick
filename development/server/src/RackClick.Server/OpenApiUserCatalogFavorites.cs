namespace RackClick.Server;

public static partial class OpenApiDocument
{
    private static void AddUserCatalogFavorites(Dictionary<string, object?> paths, Dictionary<string, object?> schemas)
    {
        object uuid = Text("uuid"), boolean = Obj(("type", "boolean"));
        object revision = Obj(("type", "integer"), ("format", "int64"), ("minimum", 0), ("maximum", UserCatalogFavorites.MaximumRevision));
        object key = Obj(("type", "string"), ("pattern", "^[a-z0-9][a-z0-9_-]{0,63}$"));
        object version = Obj(("type", "string"), ("minLength", 1), ("maxLength", 64));
        object sha = Obj(("type", "string"), ("pattern", "^[0-9a-f]{64}$"));
        object kind = Obj(("type", "string"), ("enum", new[] { "catalogFavorites" }));
        schemas["UserCatalogFavoriteSet"] = Shape(["presetKey", "catalogVersion", "catalogSha256", "favorite"],
            ("presetKey", key), ("catalogVersion", version), ("catalogSha256", sha), ("favorite", boolean));
        schemas["UserCatalogFavoriteChange"] = Shape(["presetKey", "catalogVersion", "catalogSha256", "favorite", "changed"],
            ("presetKey", key), ("catalogVersion", version), ("catalogSha256", sha), ("favorite", boolean), ("changed", boolean));
        schemas["UserCatalogFavoritesSnapshot"] = Shape(["kind", "customerId", "ownerId", "revision", "catalogVersion", "catalogSha256", "presetKeys"],
            ("kind", kind), ("customerId", uuid), ("ownerId", uuid), ("revision", revision), ("catalogVersion", version), ("catalogSha256", sha), ("presetKeys", ArrayOf(key)));
        schemas["UserCatalogFavoriteResult"] = Shape(["kind", "ownerId", "revision", "requestId", "operationId", "result"],
            ("kind", kind), ("ownerId", uuid), ("revision", revision), ("requestId", uuid), ("operationId", uuid), ("result", Ref("UserCatalogFavoriteChange")));
        schemas["UserCatalogFavoriteStatus"] = Shape(["state", "ownerId", "revision", "requestId", "operation"],
            ("state", Obj(("type", "string"), ("enum", new[] { "notRecorded", "committed", "cancelled" }))),
            ("ownerId", uuid), ("revision", revision), ("requestId", uuid),
            ("operation", Obj(("allOf", new[] { Ref("UserCatalogFavoriteResult") }), ("nullable", true))));
        foreach (string name in new[] { "UserCatalogFavoriteSet", "UserCatalogFavoriteChange", "UserCatalogFavoritesSnapshot", "UserCatalogFavoriteResult", "UserCatalogFavoriteStatus" })
            ((Dictionary<string, object?>)schemas[name]!)["additionalProperties"] = false;

        const string authority = "Personal BASE RC9 catalog favorites. Owner is derived only from the current session; current inventory.read on the customer context is required for all calls, including replay/status/cancel, before/after waits and before commit. Readers may manage their own favorites; no inventory.edit or new capability. Membership/revision are personal across accessible customer contexts; no inventory/customer/Systemhaus revision or inventory change-feed event. GET never inserts. Queries are closed/empty. ";
        Dictionary<string, object?> Endpoint(string id, bool mutation, bool requestPath, string response, string description)
        {
            var operation = (Dictionary<string, object?>)Operation(id, authority + description, "200", Ref(response),
                request: mutation ? "UserCatalogFavoriteSet" : null, mutation: mutation, customer: true, etag: true);
            if (!operation.TryGetValue("parameters", out var value)) operation["parameters"] = value = new List<object>();
            var parameters = (List<object>)value!;
            if (mutation)
            {
                parameters.Add(Header("If-Match", "Original personal revision only: exact quoted favorites-N, N=0..9007199254740991; no leading zeroes. Missing 428, malformed 422. Cancellation accepts stale original revision.", Obj(("type", "string"), ("pattern", "^\"favorites-(0|[1-9][0-9]*)\"$"))));
                parameters.Add(Header("Idempotency-Key", "Nonempty UUID; scoped to this personal family/owner. Must equal requestId in cancellation path.", uuid));
                parameters.Add(Header("X-RackClick-Actor", "Required original session actor UUID; mismatch 409 actor_changed.", uuid));
            }
            if (requestPath) parameters.Add(Obj(("in", "path"), ("name", "requestId"), ("required", true), ("schema", uuid)));
            var responses = (Dictionary<string, object?>)operation["responses"]!;
            responses["404"] = Response("Customer context absent or outside current inventory.read scope.", Ref("Error"));
            responses["422"] = Response("Invalid query, duplicate/extra/missing JSON keys, nonboolean favorite, preset, UUID or personal ETag.", Ref("Error"));
            if (mutation)
            {
                responses["409"] = Response("Actor changed, request_id_reused, operation_cancelled, catalog_changed, favorites_revision_exhausted or favorites_conflict.", Ref("Error"));
                responses["412"] = Response("Personal revision conflict; retain draft.", Ref("Error"));
                responses["428"] = Response("Original personal If-Match required.", Ref("Error"));
            }
            ((Dictionary<string, object?>)((Dictionary<string, object?>)responses["200"]!)["headers"]!)["ETag"] =
                Obj(("schema", Text()), ("description", "Exact quoted favorites-N personal revision. POST replay uses historical result revision; GET/status/cancel use current revision. Refresh GET after confirmation."));
            return operation;
        }
        paths["/api/v1/customers/{id}/catalog/favorites"] = Obj(
            ("get", Endpoint("readUserCatalogFavorites", false, false, "UserCatalogFavoritesSnapshot", "Returns ordinal presetKeys and current reference version/hash; absent aggregate revision is zero. No If-Match required.")),
            ("post", Endpoint("setUserCatalogFavorite", true, false, "UserCatalogFavoriteResult", "Closed four-key explicit SET, never toggle. New intent validates current catalog version/hash and one of 33 keys. Changed membership increments personal revision once; no-op commits one operation/audit with unchanged revision. Exact replay precedes current catalog validation, returns original result without customerId, and works through another currently accessible customer context. Commit/favorite/revision/audit/result atomic.")));
        paths["/api/v1/customers/{id}/catalog/favorites/operations/{requestId}"] = Obj(
            ("get", Endpoint("readUserCatalogFavoriteOperation", false, true, "UserCatalogFavoriteStatus", "Actor-bound committed/cancelled/notRecorded; operation null except committed. Outer revision is current, inner immutable result revision historical. notRecorded is not a fence.")));
        paths["/api/v1/customers/{id}/catalog/favorites/operations/{requestId}/cancel"] = Obj(
            ("post", Endpoint("cancelUserCatalogFavoriteOperation", true, true, "UserCatalogFavoriteStatus", "Requires exact original four-key body/key/revision. Durable own terminal row prevents delayed entry; stale original revision/catalog allowed. Does not undo committed operation or change membership/revision. No duplicate audit on replay. Fences retained indefinitely in this scope.")));
    }
}
