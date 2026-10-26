namespace RackClick.Server;

public static partial class OpenApiDocument
{
    private static void AddInventoryCatalog(Dictionary<string, object?> paths, Dictionary<string, object?> schemas)
    {
        object text = Text(), uuid = Text("uuid"), integer = Obj(("type", "integer"));
        object languages = Obj(("type", "string"), ("enum", new[] { "en", "de", "es" }));
        object version = Obj(("type", "string"), ("enum", new[] { InventoryRc9Catalog.Version }));
        object sha = Obj(("type", "string"), ("pattern", "^[0-9a-f]{64}$"));
        object nullableId = Obj(("type", "string"), ("format", "uuid"), ("nullable", true));
        object nullableNumber = Obj(("type", "number"), ("nullable", true), ("minimum", 0), ("maximum", 999999));
        object nullableColor = Obj(("type", "string"), ("nullable", true), ("pattern", "^#[0-9A-Fa-f]{6}$"));
        schemas["InventoryCatalogCategory"] = Shape(["key", "label", "presetKeys"], ("key", text), ("label", text), ("presetKeys", ArrayOf(text)));
        schemas["InventoryCatalogPort"] = Shape(["gn", "sortOrder", "type", "label", "status", "poe", "watts", "color", "face", "powerRole", "properties"],
            ("gn", integer), ("sortOrder", integer), ("type", text), ("label", text), ("status", text), ("poe", Obj(("type", "boolean"))),
            ("watts", Obj(("type", "number"), ("nullable", true), ("minimum", 0), ("maximum", 90))), ("color", nullableColor),
            ("face", text), ("powerRole", text), ("properties", Obj(("type", "object"), ("additionalProperties", false), ("maxProperties", 0))));
        schemas["InventoryCatalogGroup"] = Shape(["key", "type", "name", "prefix", "sortOrder", "ports"], ("key", text), ("type", text),
            ("name", text), ("prefix", text), ("sortOrder", integer), ("ports", ArrayOf(Ref("InventoryCatalogPort"))));
        schemas["InventoryCatalogPreset"] = Shape(["key", "categoryKey", "label", "icon", "color", "sizeU", "poeBudget", "portGroups"],
            ("key", text), ("categoryKey", text), ("label", text), ("icon", text), ("color", text), ("sizeU", integer),
            ("poeBudget", nullableNumber), ("portGroups", ArrayOf(Ref("InventoryCatalogGroup"))));
        schemas["InventoryCatalogSnapshot"] = Shape(["customerId", "revision", "language", "catalogVersion", "catalogSha256", "categories", "presets"],
            ("customerId", uuid), ("revision", Obj(("type", "integer"), ("format", "int64"))), ("language", languages),
            ("catalogVersion", version), ("catalogSha256", sha), ("categories", ArrayOf(Ref("InventoryCatalogCategory"))), ("presets", ArrayOf(Ref("InventoryCatalogPreset"))));
        object note = Obj(("type", "string"), ("maxLength", 2000));
        var notes = (Dictionary<string, object?>)Shape(["sn", "model", "ip", "firmware", "text"],
            ("sn", note), ("model", note), ("ip", note), ("firmware", note), ("text", note));
        notes["additionalProperties"] = false;
        schemas["CreateDeviceFromCatalog"] = Shape(["presetKey", "catalogVersion", "catalogSha256", "language", "kind", "rackId", "roomId", "name", "color", "poeBudget", "notes"],
            ("presetKey", text), ("catalogVersion", version), ("catalogSha256", sha), ("language", languages),
            ("kind", Obj(("type", "string"), ("enum", new[] { "rackEquipment", "dose", "endDevice" }))),
            ("rackId", nullableId), ("roomId", nullableId), ("name", Obj(("type", "string"), ("minLength", 1), ("maxLength", 100))),
            ("color", Obj(("type", "string"), ("pattern", "^#[0-9A-Fa-f]{6}$"))), ("poeBudget", nullableNumber),
            ("notes", notes));
        foreach (string name in new[] { "InventoryCatalogCategory", "InventoryCatalogPort", "InventoryCatalogGroup", "InventoryCatalogPreset", "InventoryCatalogSnapshot", "CreateDeviceFromCatalog" })
            ((Dictionary<string, object?>)schemas[name]!)["additionalProperties"] = false;
        var operation = (Dictionary<string, object?>)Operation("readInventoryCatalog",
            "Immutable adopted RC9 base reference, 33 presets/7 categories/3 languages. Requires current inventory.read and exact customer If-Match; only one language query is permitted and required. Customer SHARE lock, current session/grants rechecked after waits and before return. No inventory/revision/audit changes, user templates, favorites or shared editable catalog. AP sizeU=1 is documentation reference; creation accepts AP only as endDevice in a room with physical sizeU null. device.createFromCatalog takes the closed eleven-key payload, trusts server layouts only, requires current read+edit, creates all UUIDs/attributes atomically under the existing inventory idempotency/commit/audit engine; exact replay precedes checking current catalog version/hash. Other preset kinds/placement are explicit; rackEquipment uses canonical sizeU and validates capacity. Colors override device color only, notes five text fields <=2000 scalars each and total properties <=8192 UTF-8 bytes. No generated connections or circuits.",
            "200", Ref("InventoryCatalogSnapshot"), revision: true, customer: true, etag: true);
        var parameters = (List<object>)operation["parameters"]!;
        parameters.RemoveAll(p => p is Dictionary<string, object?> d && d.TryGetValue("name", out var n) && n is "Idempotency-Key" or "X-RackClick-Actor");
        parameters.Add(Obj(("in", "query"), ("name", "language"), ("required", true), ("schema", languages)));
        paths["/api/v1/customers/{id}/catalog"] = Obj(("get", operation));
    }
}
