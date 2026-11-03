namespace RackClick.Server;

public static partial class OpenApiDocument
{
    private static void AddInventoryReadViews(Dictionary<string, object?> paths, Dictionary<string, object?> schemas)
    {
        static object Parameter(string name, string location, bool required, object schema) =>
            Obj(("name", name), ("in", location), ("required", required), ("schema", schema));
        object uuid = Text("uuid"), text = Text(), integer = Obj(("type", "integer")), boolean = Obj(("type", "boolean"));
        object nullableId = Obj(("type", "string"), ("format", "uuid"), ("nullable", true));
        object nullableText = Obj(("type", "string"), ("nullable", true));
        object nullableInt = Obj(("type", "integer"), ("nullable", true));
        schemas["InventoryViewPath"] = Shape(["kind", "id", "name"], ("kind", text), ("id", uuid), ("name", text));
        object path = ArrayOf(Ref("InventoryViewPath"));
        schemas["InventorySearchItem"] = Shape(["customerId", "id", "kind", "name", "path", "rackId", "roomId", "deviceId", "groupId", "type", "gn", "status"],
            ("customerId", uuid), ("id", uuid), ("kind", text), ("name", text), ("path", path), ("rackId", nullableId), ("roomId", nullableId),
            ("deviceId", nullableId), ("groupId", nullableId), ("type", nullableText), ("gn", nullableInt), ("status", nullableText));
        schemas["InventoryPortView"] = Shape(["customerId", "id", "deviceId", "deviceName", "deviceKind", "rackId", "roomId", "path", "groupId", "groupName", "type", "family", "gn", "label", "status", "face", "poe", "watts", "color", "powerRole", "connected", "connectionIds", "peerPortIds"],
            ("customerId", uuid), ("id", uuid), ("deviceId", uuid), ("deviceName", text), ("deviceKind", text), ("rackId", nullableId), ("roomId", nullableId),
            ("path", path), ("groupId", uuid), ("groupName", text), ("type", text), ("family", text), ("gn", integer), ("label", text), ("status", text),
            ("face", text), ("poe", boolean), ("watts", Obj(("type", "number"), ("nullable", true))), ("color", nullableText), ("powerRole", text),
            ("connected", boolean), ("connectionIds", ArrayOf(uuid)), ("peerPortIds", ArrayOf(uuid)),
            ("physicalConnector", Obj(("type", "string"), ("nullable", true), ("description", "Optional authenticated physical form classification; power cord ends, voltage, current and pinout are unspecified. Omitted when unknown."))));
        schemas["InventoryConnectionView"] = Shape(["customerId", "id", "from", "to", "note", "color", "patch", "crossRack"],
            ("customerId", uuid), ("id", uuid), ("from", Ref("InventoryPortView")), ("to", Ref("InventoryPortView")), ("note", text),
            ("color", nullableText), ("patch", text), ("crossRack", Obj(("type", "boolean"), ("nullable", true))));
        foreach (string view in new[] { "search", "ports", "connections" })
        {
            string item = view == "search" ? "InventorySearchItem" : view == "ports" ? "InventoryPortView" : "InventoryConnectionView";
            string schema = "InventoryReadView_" + view;
            schemas[schema] = Shape(["customerId", "revision", "query", "kind", "status", "family", "offset", "limit", "total", "nextOffset", "items"],
                ("customerId", uuid), ("revision", Obj(("type", "integer"), ("format", "int64"))), ("query", text), ("kind", nullableText),
                ("status", nullableText), ("family", nullableText), ("offset", integer), ("limit", integer), ("total", integer), ("nextOffset", nullableInt), ("items", ArrayOf(Ref(item))));
            var operation = (Dictionary<string, object?>)Operation("readInventory_" + view,
                "Screen query requiring inventory.read in this customer and If-Match of its snapshot revision. ReadCommitted/customer SHARE; current session and grants rechecked after waits and after projection. UUID order, literal NFC OrdinalIgnoreCase matching. No export/download contract. Unknown or repeated filters return 422 request_invalid; stale revision 412. No properties/audit data.",
                "200", Ref(schema), revision: true, customer: true, etag: true);
            var parameters = (List<object>)operation["parameters"]!;
            parameters.RemoveAll(p => p is Dictionary<string, object?> d && d.TryGetValue("name", out var n) && n is "Idempotency-Key" or "X-RackClick-Actor");
            ((Dictionary<string, object?>)parameters[0])["description"] = "Current inventory snapshot customer revision, quoted; required on every page.";
            parameters.Add(Parameter("query", "query", false, Obj(("type", "string"), ("maxLength", 200), ("default", ""))));
            parameters.Add(Parameter("offset", "query", false, Obj(("type", "integer"), ("minimum", 0), ("maximum", 1000000), ("default", 0))));
            parameters.Add(Parameter("limit", "query", false, Obj(("type", "integer"), ("minimum", 1), ("maximum", 100), ("default", 50))));
            if (view == "search") parameters.Add(Parameter("kind", "query", false, Obj(("type", "string"), ("enum", new[] { "all", "site", "building", "room", "rack", "device", "port", "connection" }), ("default", "all"))));
            if (view == "ports")
            {
                parameters.Add(Parameter("status", "query", false, Obj(("type", "string"), ("enum", new[] { "all", "free", "reserved", "disabled", "faulty" }), ("default", "all"))));
                parameters.Add(Parameter("family", "query", false, Obj(("type", "string"), ("enum", new[] { "all", "rj45", "sfp", "sfp28", "sfp56", "qsfp", "qsfpdd", "mgmt", "console", "idc", "power", "usb_a", "usb_c", "ipc", "fiber", "sfpdd", "cfp2", "sas", "dsl", "telephony", "isdn", "expansion", "power_dc" }), ("default", "all"))));
            }
            ((Dictionary<string, object?>)operation["responses"]!)["422"] = Response("Invalid closed query, bounds or revision.", Ref("Error"));
            paths["/api/v1/customers/{id}/inventory/" + view] = Obj(("get", operation));
        }
    }
}
