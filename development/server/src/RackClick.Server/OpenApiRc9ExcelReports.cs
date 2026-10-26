namespace RackClick.Server;

public static partial class OpenApiDocument
{
    private static void AddRc9ExcelReports(Dictionary<string, object?> paths, Dictionary<string, object?> schemas)
    {
        object uuid = Text("uuid"), text = Text();
        object Choice(string value) => Obj(("type", "string"), ("enum", new[] { value }));
        object Count(int minimum = 0) => Obj(("type", "integer"), ("minimum", minimum), ("maximum", 10000));
        schemas["Rc9ExcelRequest"] = Shape(["rackId"], ("rackId", uuid));
        schemas["Rc9ExcelReport"] = Shape(["format", "cellEncoding", "rackId", "generatedAt", "filename", "contentType", "deviceCount", "connectionCount", "summaryCount", "rowCount", "byteLength", "sha256", "contentBase64"],
            ("format", Choice("xls-html-rc9-v1")), ("cellEncoding", Choice("html-text-v1")), ("rackId", uuid),
            ("generatedAt", Obj(("type", "string"), ("format", "date-time"), ("pattern", "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\\.[0-9]{3}Z$"))),
            ("filename", text), ("contentType", Choice("application/vnd.ms-excel;charset=utf-8")), ("deviceCount", Count()), ("connectionCount", Count()),
            ("summaryCount", Obj(("type", "integer"), ("enum", new[] { 10 }))), ("rowCount", Count(10)),
            ("byteLength", Obj(("type", "integer"), ("minimum", 1), ("maximum", 4194304))),
            ("sha256", Obj(("type", "string"), ("pattern", "^[0-9a-f]{64}$"))), ("contentBase64", Text("byte")));
        schemas["Rc9ExcelResult"] = Shape(["kind", "customerId", "revision", "requestId", "operationId", "report"],
            ("kind", Choice("rc9ExcelReport")), ("customerId", uuid), ("revision", Obj(("type", "integer"), ("format", "int64"), ("minimum", 1))),
            ("requestId", uuid), ("operationId", uuid), ("report", Ref("Rc9ExcelReport")));
        schemas["Rc9ExcelStatus"] = Shape(["state", "customerId", "requestId", "operation"],
            ("state", Obj(("type", "string"), ("enum", new[] { "committed", "notRecorded" }))), ("customerId", uuid), ("requestId", uuid),
            ("operation", Obj(("allOf", new[] { Ref("Rc9ExcelResult") }), ("nullable", true))));
        foreach (string name in new[] { "Rc9ExcelRequest", "Rc9ExcelReport", "Rc9ExcelResult", "Rc9ExcelStatus" })
            ((Dictionary<string, object?>)schemas[name]!)["additionalProperties"] = false;
        var generate = (Dictionary<string, object?>)Operation("generateRc9ExcelReport",
            "RC9 rack report: fixed Devices/Connections/Summary tables in passive UTF8 HTML with .xls extension, not BIFF or OOXML. Rack UUID mandatory, no query/filter/language. Current inventory.read AND reports.export in customer scope after waits and before replay/commit. Own format-specific reports.xlsHtml.generate digest, original body/revision/actor/key for retry. Artifact+metadata-only audit+receipt atomic; no inventory/customer/Systemhaus revision or collaboration event. 10000 total data rows including 10 Summary, 32767 UTF16 units per cell, final 4MiB. All cells x:str/text MSO, no formula/active content. Created uses literal properties.createdAt string or persisted PostgreSQL createdAt fallback; Technician empty because absent from model. Structural validation does not assert Office opening or effective formula safety; Excel can warn about HTML/.xls format mismatch.",
            "200", Ref("Rc9ExcelResult"), "Rc9ExcelRequest", mutation: true, revision: true, customer: true, etag: true);
        foreach (var item in ((List<object>)generate["parameters"]!).OfType<Dictionary<string, object?>>())
        {
            if (item["name"] is "If-Match") item["description"] = "Original source customer revision required for replay; new stale key returns 412.";
            if (item["name"] is "X-RackClick-Actor") item["required"] = true;
        }
        paths["/api/v1/customers/{id}/reports/xls-html"] = Obj(("post", generate));
        var status = (Dictionary<string, object?>)Operation("rc9ExcelReportStatus",
            "Own actor/customer/format receipt only. Current inventory.read AND reports.export after waits and before return, including unknown keys. Another actor key is notRecorded without inspecting that actor; own wrong customer/format 404. notRecorded does not cancel. No specialized cancel; generic inventory/status/cancel/replay must never return rc9ExcelReport. Revalidate via this status immediately before browser Blob/download; server commit does not confirm a disk save.",
            "200", Ref("Rc9ExcelStatus"), customer: true);
        ((List<object>)status["parameters"]!).Add(Obj(("in", "path"), ("name", "requestId"), ("required", true), ("schema", uuid)));
        ((Dictionary<string, object?>)status["responses"]!)["404"] = Response("Unknown customer, own wrong customer/format, or unreadable scope.", Ref("Error"));
        paths["/api/v1/customers/{id}/reports/xls-html/operations/{requestId}"] = Obj(("get", status));
    }
}
