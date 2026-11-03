namespace RackClick.Server;

public static partial class OpenApiDocument
{
    private static void AddInventoryReports(Dictionary<string, object?> paths, Dictionary<string, object?> schemas)
    {
        object text = Text(), uuid = Text("uuid"), integer = Obj(("type", "integer")), nullableId = Obj(("type", "string"), ("format", "uuid"), ("nullable", true));
        object kinds = Obj(("type", "string"), ("enum", new[] { "ports", "connections" }));
        object statuses = Obj(("type", "string"), ("enum", new[] { "all", "free", "reserved", "disabled", "faulty" }));
        object families = Obj(("type", "string"), ("enum", new[] { "all", "rj45", "sfp", "sfp28", "sfp56", "qsfp", "qsfpdd", "mgmt", "console", "idc", "power", "usb_a", "usb_c", "ipc", "fiber", "sfpdd", "cfp2", "sas", "dsl", "telephony", "isdn", "expansion", "power_dc" }));
        schemas["InventoryCsvRequest"] = Shape(["reportKind", "query", "status", "family", "rackId"], ("reportKind", kinds),
            ("query", Obj(("type", "string"), ("maxLength", 200))), ("status", statuses), ("family", families), ("rackId", nullableId));
        ((Dictionary<string, object?>)schemas["InventoryCsvRequest"]!)["additionalProperties"] = false;
        schemas["InventoryCsvReport"] = Shape(["reportKind", "query", "status", "family", "rackId", "filename", "contentType", "encoding", "csvValueEncoding", "rowCount", "byteLength", "sha256", "contentBase64"],
            ("reportKind", kinds), ("query", text), ("status", statuses), ("family", families), ("rackId", nullableId), ("filename", text),
            ("contentType", Obj(("type", "string"), ("enum", new[] { "text/csv; charset=utf-8" }))),
            ("encoding", Obj(("type", "string"), ("enum", new[] { "utf-8-bom" }))),
            ("csvValueEncoding", Obj(("type", "string"), ("enum", new[] { "spreadsheet-safe-apostrophe-v1" }))),
            ("rowCount", Obj(("type", "integer"), ("minimum", 0), ("maximum", 10000))),
            ("byteLength", Obj(("type", "integer"), ("maximum", 4194304))), ("sha256", text), ("contentBase64", Text("byte")));
        schemas["InventoryReportResult"] = Shape(["kind", "customerId", "revision", "requestId", "operationId", "report"],
            ("kind", Obj(("type", "string"), ("enum", new[] { "report" }))), ("customerId", uuid),
            ("revision", Obj(("type", "integer"), ("format", "int64"), ("minimum", 1))), ("requestId", uuid), ("operationId", uuid), ("report", Ref("InventoryCsvReport")));
        schemas["InventoryReportStatus"] = Shape(["state", "customerId", "requestId", "operation"],
            ("state", Obj(("type", "string"), ("enum", new[] { "committed", "notRecorded" }))), ("customerId", uuid), ("requestId", uuid),
            ("operation", Obj(("allOf", new[] { Ref("InventoryReportResult") }), ("nullable", true))));
        var generate = (Dictionary<string, object?>)Operation("generateInventoryCsv", "Current inventory.read AND reports.export in customer scope. Closed five-key request. connections requires status/family all. Rack filter uses customer UUID; cables include either endpoint and keep both contexts. Customer snapshot If-Match; actor/key/revision/body digest; current authorization checked after waits and before commit. Durable exact replay, even after later inventory revisions. No inventory/customer/Systemhaus revision increment; audit reports.csv.generate metadata only. Maximum 10000 rows and 4MiB BOM UTF-8/CRLF, no truncation (422 report_too_large). Every field quoted RFC4180. Selective reversible apostrophe protection: original leading apostrophe, TAB/CR/LF or first non-whitespace =+-@ gets one added apostrophe; other cells preserved. No import/roundtrip or universal spreadsheet behavior promised.",
            "200", Ref("InventoryReportResult"), "InventoryCsvRequest", mutation: true, revision: true, customer: true, etag: true);
        var parameters = (List<object>)generate["parameters"]!;
        foreach (var item in parameters.OfType<Dictionary<string, object?>>())
        {
            if (item["name"] is "If-Match") item["description"] = "Source customer inventory revision; original revision required for replay.";
            if (item["name"] is "X-RackClick-Actor") item["required"] = true;
        }
        paths["/api/v1/customers/{id}/reports/csv"] = Obj(("post", generate));
        var status = (Dictionary<string, object?>)Operation("inventoryReportStatus", "Own actor, customer and report operation only, CURRENT inventory.read AND reports.export required even for unknown keys. Returns historical immutable artifact without inferred current revision. notRecorded is not cancellation. No GET download using inventory.read alone.",
            "200", Ref("InventoryReportStatus"), customer: true);
        ((List<object>)status["parameters"]!).Add(Obj(("in", "path"), ("name", "requestId"), ("required", true), ("schema", uuid)));
        ((Dictionary<string, object?>)status["responses"]!)["404"] = Response("Unknown customer, wrong actor/customer/kind, or unreadable scope.", Ref("Error"));
        paths["/api/v1/customers/{id}/reports/operations/{requestId}"] = Obj(("get", status));
    }
}
