namespace RackClick.Server;

public static partial class OpenApiDocument
{
    private static void AddInventoryJsonExports(Dictionary<string, object?> paths, Dictionary<string, object?> schemas)
    {
        object text = Text(), uuid = Text("uuid"), revision = Obj(("type", "integer"), ("format", "int64"), ("minimum", 1));
        schemas["InventoryJsonExportRequest"] = Shape(["formatVersion", "scope"],
            ("formatVersion", Obj(("type", "integer"), ("enum", new[] { 1 }))),
            ("scope", Obj(("type", "string"), ("enum", new[] { "customer" }))));
        ((Dictionary<string, object?>)schemas["InventoryJsonExportRequest"]!)["additionalProperties"] = false;
        schemas["InventoryJsonArchive"] = Shape(["format", "scope", "filename", "contentType", "encoding", "rowCount", "byteLength", "sha256", "contentBase64"],
            ("format", Obj(("type", "string"), ("enum", new[] { "RackClickInventory-v1" }))),
            ("scope", Obj(("type", "string"), ("enum", new[] { "customer" }))), ("filename", text),
            ("contentType", Obj(("type", "string"), ("enum", new[] { "application/json; charset=utf-8" }))),
            ("encoding", Obj(("type", "string"), ("enum", new[] { "utf-8" }))),
            ("rowCount", Obj(("type", "integer"), ("minimum", 0), ("maximum", 100000))),
            ("byteLength", Obj(("type", "integer"), ("minimum", 1), ("maximum", 4194304))),
            ("sha256", Obj(("type", "string"), ("pattern", "^[0-9a-f]{64}$"))), ("contentBase64", Text("byte")));
        schemas["InventoryJsonExportResult"] = Shape(["kind", "customerId", "revision", "requestId", "operationId", "archive"],
            ("kind", Obj(("type", "string"), ("enum", new[] { "inventoryExport" }))),
            ("customerId", uuid), ("revision", revision), ("requestId", uuid), ("operationId", uuid), ("archive", Ref("InventoryJsonArchive")));
        schemas["InventoryJsonExportStatus"] = Shape(["state", "customerId", "requestId", "operation"],
            ("state", Obj(("type", "string"), ("enum", new[] { "committed", "notRecorded" }))), ("customerId", uuid), ("requestId", uuid),
            ("operation", Obj(("anyOf", new[] { Ref("InventoryJsonExportResult"), Obj(("type", "null")) }))));
        var generate = (Dictionary<string, object?>)Operation("generateInventoryJsonExport",
            "Export current complete customer inventory as RackClickInventory-v1. Requires current inventory.read AND reports.export; actor, CSRF, revision and idempotency guards. Includes notes/metadata entered in inventory, excludes security/account tables. Closed eight inventory collections; UUID, hardware revision, mounts and port metadata preserved. UTF8 without BOM, at most4MiB/100000records, no truncation. Audit contains metadata only. Receipt is a historical immutable artifact; this is not a PostgreSQL backup, original RC9 download, import or merge.",
            "200", Ref("InventoryJsonExportResult"), "InventoryJsonExportRequest", mutation: true, revision: true, customer: true, etag: true);
        foreach (var parameter in ((List<object>)generate["parameters"]!).OfType<Dictionary<string, object?>>())
            if (parameter["name"] is "X-RackClick-Actor") parameter["required"] = true;
        paths["/api/v1/customers/{id}/exports/inventory-json"] = Obj(("post", generate));
        var status = (Dictionary<string, object?>)Operation("inventoryJsonExportStatus",
            "Own actor/customer export receipt only, with current inventory.read AND reports.export even for unknown keys. notRecorded does not prove cancellation. Generic operation routes must not expose this artifact.",
            "200", Ref("InventoryJsonExportStatus"), customer: true);
        ((List<object>)status["parameters"]!).Add(Obj(("in", "path"), ("name", "requestId"), ("required", true), ("schema", uuid)));
        paths["/api/v1/customers/{id}/exports/inventory-json/operations/{requestId}"] = Obj(("get", status));
    }
}
