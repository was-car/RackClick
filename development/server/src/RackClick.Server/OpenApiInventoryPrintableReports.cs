namespace RackClick.Server;

public static partial class OpenApiDocument
{
    private static void AddInventoryPrintableReports(Dictionary<string, object?> paths, Dictionary<string, object?> schemas)
    {
        object uuid = Text("uuid"), text = Text();
        object kinds = Obj(("type", "string"), ("enum", new[] { "rack", "client", "rackLabels" }));
        object languages = Obj(("type", "string"), ("enum", new[] { "en", "de", "es" }));
        object racks = Obj(("type", "array"), ("items", uuid), ("maxItems", 64), ("uniqueItems", true),
            ("description", "Nonempty canonical D UUIDs, no duplicates. rack: exactly one; client: empty; rackLabels: 1..64. Canonically sorted for digest and result; original request order does not affect replay."));
        schemas["InventoryPrintableRequest"] = Shape(["reportKind", "language", "rackIds"],
            ("reportKind", kinds), ("language", languages), ("rackIds", racks));
        ((Dictionary<string, object?>)schemas["InventoryPrintableRequest"]!)["additionalProperties"] = false;
        ((Dictionary<string, object?>)schemas["InventoryPrintableRequest"]!)["oneOf"] = new[] {
            Obj(("properties", Obj(("reportKind", Obj(("enum", new[] { "rack" }))), ("rackIds", Obj(("minItems", 1), ("maxItems", 1)))))),
            Obj(("properties", Obj(("reportKind", Obj(("enum", new[] { "client" }))), ("rackIds", Obj(("maxItems", 0)))))),
            Obj(("properties", Obj(("reportKind", Obj(("enum", new[] { "rackLabels" }))), ("rackIds", Obj(("minItems", 1), ("maxItems", 64)))))) };
        schemas["InventoryPrintableReport"] = Shape(["reportKind", "language", "rackIds", "filename", "contentType", "encoding", "templateVersion", "rowCount", "byteLength", "sha256", "contentBase64"],
            ("reportKind", kinds), ("language", languages), ("rackIds", racks), ("filename", text),
            ("contentType", Obj(("type", "string"), ("enum", new[] { "text/html; charset=utf-8" }))),
            ("encoding", Obj(("type", "string"), ("enum", new[] { "utf-8" }))),
            ("templateVersion", Obj(("type", "string"), ("enum", new[] { "rackclick-print-v1" }))),
            ("rowCount", Obj(("type", "integer"), ("minimum", 0), ("maximum", 10000))),
            ("byteLength", Obj(("type", "integer"), ("minimum", 1), ("maximum", 4194304))),
            ("sha256", Obj(("type", "string"), ("pattern", "^[0-9a-f]{64}$"))), ("contentBase64", Text("byte")));
        schemas["InventoryPrintableResult"] = Shape(["kind", "customerId", "revision", "requestId", "operationId", "report"],
            ("kind", Obj(("type", "string"), ("enum", new[] { "report" }))), ("customerId", uuid),
            ("revision", Obj(("type", "integer"), ("format", "int64"), ("minimum", 1))),
            ("requestId", uuid), ("operationId", uuid), ("report", Ref("InventoryPrintableReport")));
        schemas["InventoryPrintableStatus"] = Shape(["state", "customerId", "requestId", "operation"],
            ("state", Obj(("type", "string"), ("enum", new[] { "committed", "notRecorded" }))), ("customerId", uuid), ("requestId", uuid),
            ("operation", Obj(("allOf", new[] { Ref("InventoryPrintableResult") }), ("nullable", true))));
        foreach (string name in new[] { "InventoryPrintableReport", "InventoryPrintableResult", "InventoryPrintableStatus" })
            ((Dictionary<string, object?>)schemas[name]!)["additionalProperties"] = false;
        var generate = (Dictionary<string, object?>)Operation("generateInventoryPrintable", "Current inventory.read AND reports.export in customer scope; no extra capability. Closed THREE-key request. rack is one rack tabular report; client is the entire customer (including room objects) with at most 20 racks, no filters or truncation; rackLabels is 1..64 distinct rack UUIDs in this customer. Missing/foreign racks 404. Source revision If-Match; same actor/key/normalized body/revision replays immutable bytes after later edits. Customer shared lock and current authorization after waits and before commit; report audit metadata and result stored atomically. No inventory or revision mutations. Passive HTML UTF-8 without BOM, fixed CSP and CSS, escaped user data, no scripts or network resources. 4MiB raw bytes and 10000 marked data rows maximum; excess 422 report_too_large without partial artifact. Tabular/labels scope does not implement the full graphical RC9 rack SVG, branding/logo/technician, native PDF, XLS or port/cable labels. CSV unchanged and separate; cross-format key reuse 409.",
            "200", Ref("InventoryPrintableResult"), "InventoryPrintableRequest", mutation: true, revision: true, customer: true, etag: true);
        foreach (var parameter in ((List<object>)generate["parameters"]!).OfType<Dictionary<string, object?>>())
        {
            if (parameter["name"] is "If-Match") parameter["description"] = "Source customer inventory revision; retain original revision for retries.";
            if (parameter["name"] is "X-RackClick-Actor") parameter["required"] = true;
        }
        paths["/api/v1/customers/{id}/reports/printable"] = Obj(("post", generate));
        var status = (Dictionary<string, object?>)Operation("inventoryPrintableReportStatus", "Own actor, Systemhaus/customer and HTML printable family only; CURRENT inventory.read AND reports.export required even for unknown keys. Historical immutable bytes, not a current inventory revision. Unknown own key: notRecorded; CSV or other operation family: 404 without artifact. No cancellation endpoint or implicit cancellation.",
            "200", Ref("InventoryPrintableStatus"), customer: true);
        ((List<object>)status["parameters"]!).Add(Obj(("in", "path"), ("name", "requestId"), ("required", true), ("schema", uuid)));
        ((Dictionary<string, object?>)status["responses"]!)["404"] = Response("Wrong customer/format/operation family, or unreadable scope.", Ref("Error"));
        paths["/api/v1/customers/{id}/reports/printable/operations/{requestId}"] = Obj(("get", status));
    }
}
