namespace RackClick.Server;

public static partial class OpenApiDocument
{
    private static void AddInventoryRackSvgReports(Dictionary<string, object?> paths, Dictionary<string, object?> schemas)
    {
        object uuid = Text("uuid"), text = Text();
        object faces = Obj(("type", "string"), ("enum", new[] { "front", "rear" }));
        object languages = Obj(("type", "string"), ("enum", new[] { "en", "de", "es" }));
        schemas["InventoryRackSvgRequest"] = Shape(["rackId", "face", "language"], ("rackId", uuid), ("face", faces), ("language", languages));
        schemas["InventoryRackSvgReport"] = Shape(["reportKind", "rackId", "face", "language", "filename", "contentType", "encoding", "templateVersion", "rowCount", "byteLength", "sha256", "contentBase64"],
            ("reportKind", Obj(("type", "string"), ("enum", new[] { "rackSvg" }))), ("rackId", uuid), ("face", faces), ("language", languages), ("filename", text),
            ("contentType", Obj(("type", "string"), ("enum", new[] { "image/svg+xml; charset=utf-8" }))),
            ("encoding", Obj(("type", "string"), ("enum", new[] { "utf-8" }))),
            ("templateVersion", Obj(("type", "string"), ("enum", new[] { "rackclick-rack-svg-v1" }))),
            ("rowCount", Obj(("type", "integer"), ("minimum", 1), ("maximum", 10000))),
            ("byteLength", Obj(("type", "integer"), ("minimum", 1), ("maximum", 4194304))),
            ("sha256", Obj(("type", "string"), ("pattern", "^[0-9a-f]{64}$"))), ("contentBase64", Text("byte")));
        schemas["InventoryRackSvgResult"] = Shape(["kind", "customerId", "revision", "requestId", "operationId", "report"],
            ("kind", Obj(("type", "string"), ("enum", new[] { "report" }))), ("customerId", uuid),
            ("revision", Obj(("type", "integer"), ("format", "int64"), ("minimum", 1))),
            ("requestId", uuid), ("operationId", uuid), ("report", Ref("InventoryRackSvgReport")));
        schemas["InventoryRackSvgStatus"] = Shape(["state", "customerId", "requestId", "operation"],
            ("state", Obj(("type", "string"), ("enum", new[] { "committed", "notRecorded" }))), ("customerId", uuid), ("requestId", uuid),
            ("operation", Obj(("allOf", new[] { Ref("InventoryRackSvgResult") }), ("nullable", true))));
        foreach (string name in new[] { "InventoryRackSvgRequest", "InventoryRackSvgReport", "InventoryRackSvgResult", "InventoryRackSvgStatus" })
            ((Dictionary<string, object?>)schemas[name]!)["additionalProperties"] = false;
        var generate = (Dictionary<string, object?>)Operation("generateInventoryRackSvg", "One rack UUID, explicit front/rear and en/de/es; closed three-key request. Current inventory.read AND reports.export in customer scope, Origin/CSRF/actor/key and source revision required. Customer shared lock with current session/read/export after waits and before commit. Immutable replay by normalized body/original revision/actor/key, including after edits/restart. Wrong rack/customer404, key reuse409, new stale revision412. UTF8 passive SVG, only svg/title/desc/g/rect/circle/path/text and fixed attributes; XmlWriter escaping, no active/network content or arbitrary properties. Invalid XML1.0 text422 report_text_invalid without silent replacement. RC9-derived 960-wide documentary geometry and native connector shapes; order is not certified physical U placement. Every rack/device/group/port/incident connection retains UUID row metadata, including hidden ports and external endpoints. Paths only when both endpoints are visible; no invented Dose circuit. At most10000 marked rows/4194304 raw bytes, overflow422 report_too_large without partial persistence. Atomic audit/operation, no inventory/revision/change-feed mutation. Not PDF/XLS/branding or installation/adoption.",
            "200", Ref("InventoryRackSvgResult"), "InventoryRackSvgRequest", mutation: true, revision: true, customer: true, etag: true);
        foreach (var parameter in ((List<object>)generate["parameters"]!).OfType<Dictionary<string, object?>>())
        {
            if (parameter["name"] is "If-Match") parameter["description"] = "Source customer inventory revision; retain original revision for retries.";
            if (parameter["name"] is "X-RackClick-Actor") parameter["required"] = true;
        }
        paths["/api/v1/customers/{id}/reports/rack-svg"] = Obj(("post", generate));
        var status = (Dictionary<string, object?>)Operation("inventoryRackSvgReportStatus", "Own actor/Systemhaus/customer/SVG family only, with CURRENT inventory.read AND reports.export even for unknown keys. Historical committed bytes or notRecorded; wrong family/customer404 without artifact. No cancellation endpoint. Generic operation routes cannot expose report artifacts.",
            "200", Ref("InventoryRackSvgStatus"), customer: true);
        ((List<object>)status["parameters"]!).Add(Obj(("in", "path"), ("name", "requestId"), ("required", true), ("schema", uuid)));
        ((Dictionary<string, object?>)status["responses"]!)["404"] = Response("Wrong customer/format/operation family, or unreadable scope.", Ref("Error"));
        paths["/api/v1/customers/{id}/reports/rack-svg/operations/{requestId}"] = Obj(("get", status));
    }
}
