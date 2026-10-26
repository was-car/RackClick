namespace RackClick.Server;

public static partial class OpenApiDocument
{
    private static void AddInventorySpreadsheetReports(Dictionary<string, object?> paths, Dictionary<string, object?> schemas)
    {
        object text = Text(), uuid = Text("uuid"), nullableId = Obj(("type", "string"), ("format", "uuid"), ("nullable", true));
        object kinds = Obj(("type", "string"), ("enum", new[] { "ports", "connections" }));
        object statuses = Obj(("type", "string"), ("enum", new[] { "all", "free", "reserved", "disabled", "faulty" }));
        object families = Obj(("type", "string"), ("enum", new[] { "all", "rj45", "sfp", "sfp28", "qsfp", "mgmt", "console", "power", "usb_a", "usb_c" }));
        schemas["InventorySpreadsheetRequest"] = Shape(["reportKind", "query", "status", "family", "rackId"], ("reportKind", kinds),
            ("query", Obj(("type", "string"), ("maxLength", 200))), ("status", statuses), ("family", families), ("rackId", nullableId));
        schemas["InventorySpreadsheetReport"] = Shape(["reportKind", "query", "status", "family", "rackId", "filename", "contentType", "format", "cellEncoding", "rowCount", "byteLength", "sha256", "contentBase64"],
            ("reportKind", kinds), ("query", text), ("status", statuses), ("family", families), ("rackId", nullableId), ("filename", text),
            ("contentType", Obj(("type", "string"), ("enum", new[] { "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" }))),
            ("format", Obj(("type", "string"), ("enum", new[] { "xlsx" }))),
            ("cellEncoding", Obj(("type", "string"), ("enum", new[] { "inline-string-v1" }))),
            ("rowCount", Obj(("type", "integer"), ("minimum", 0), ("maximum", 10000))),
            ("byteLength", Obj(("type", "integer"), ("minimum", 1), ("maximum", 4194304))),
            ("sha256", Obj(("type", "string"), ("pattern", "^[0-9a-f]{64}$"))), ("contentBase64", Text("byte")));
        schemas["InventorySpreadsheetResult"] = Shape(["kind", "customerId", "revision", "requestId", "operationId", "report"],
            ("kind", Obj(("type", "string"), ("enum", new[] { "spreadsheetReport" }))), ("customerId", uuid),
            ("revision", Obj(("type", "integer"), ("format", "int64"), ("minimum", 1))), ("requestId", uuid), ("operationId", uuid), ("report", Ref("InventorySpreadsheetReport")));
        schemas["InventorySpreadsheetStatus"] = Shape(["state", "customerId", "requestId", "operation"],
            ("state", Obj(("type", "string"), ("enum", new[] { "committed", "notRecorded" }))), ("customerId", uuid), ("requestId", uuid),
            ("operation", Obj(("allOf", new[] { Ref("InventorySpreadsheetResult") }), ("nullable", true))));
        foreach (string name in new[] { "InventorySpreadsheetRequest", "InventorySpreadsheetReport", "InventorySpreadsheetResult", "InventorySpreadsheetStatus" })
            ((Dictionary<string, object?>)schemas[name]!)["additionalProperties"] = false;
        var generate = (Dictionary<string, object?>)Operation("generateInventorySpreadsheet", "Current inventory.read AND reports.export in customer scope, checked after waits and before commit/replay. Same closed five-field filter/projection as CSV. Source If-Match and original actor/key/body/revision for replay; format-specific reports.xlsx.generate digest. Transactional immutable artifact and metadata-only audit; inventory/revisions unchanged. 10000 data rows, 32767 UTF-16 units per cell, 4MiB XML and final ZIP, without truncation (422 report_too_large); invalid surrogate pairs 422 report_cell_invalid. Minimal five-part uncompressed OOXML, one Ports/Connections sheet, inline-string-v1 text only, no formula or external relationship, deterministic ZIP timestamps. Literal SpreadsheetML escape sequences and CR are preserved. This tabular XLSX is distinct from legacy RC9 HTML .xls Devices/Connections/Summary export; no import/roundtrip or spreadsheet-app opening promised.",
            "200", Ref("InventorySpreadsheetResult"), "InventorySpreadsheetRequest", mutation: true, revision: true, customer: true, etag: true);
        foreach (var item in ((List<object>)generate["parameters"]!).OfType<Dictionary<string, object?>>())
        {
            if (item["name"] is "If-Match") item["description"] = "Source customer revision; original revision required for replay.";
            if (item["name"] is "X-RackClick-Actor") item["required"] = true;
        }
        paths["/api/v1/customers/{id}/reports/xlsx"] = Obj(("post", generate));
        var status = (Dictionary<string, object?>)Operation("inventorySpreadsheetStatus", "Own actor and customer only. Current inventory.read AND reports.export required, including unknown keys. Unknown own key or another actor key is notRecorded without revealing existence; own wrong customer/format 404. notRecorded does not cancel. Historical bytes remain immutable after later revisions. Generic operations never expose spreadsheet artifacts.",
            "200", Ref("InventorySpreadsheetStatus"), customer: true);
        ((List<object>)status["parameters"]!).Add(Obj(("in", "path"), ("name", "requestId"), ("required", true), ("schema", uuid)));
        ((Dictionary<string, object?>)status["responses"]!)["404"] = Response("Unknown customer, own wrong customer/format, or unreadable scope.", Ref("Error"));
        paths["/api/v1/customers/{id}/reports/xlsx/operations/{requestId}"] = Obj(("get", status));
    }
}
