namespace RackClick.Server;

public static partial class OpenApiDocument
{
    private static void AddInventory(Dictionary<string, object?> paths, Dictionary<string, object?> schemas)
    {
        AddInventoryReadViews(paths, schemas);
        AddInventoryReports(paths, schemas);
        AddInventoryPrintableReports(paths, schemas);
        AddInventoryCatalog(paths, schemas);
        object uuid = Text("uuid"), text = Text(), properties = Obj(("type", "object"), ("additionalProperties", true));
        object integer = Obj(("type", "integer")), number = Obj(("type", "number"), ("nullable", true)), boolean = Obj(("type", "boolean"));
        object nullableId = Obj(("type", "string"), ("format", "uuid"), ("nullable", true));
        object nullableText = Obj(("type", "string"), ("nullable", true));
        object ids = ArrayOf(uuid);
        object props = properties;
        schemas["InventorySite"] = Shape(["id", "name", "properties"], ("id", uuid), ("name", text), ("properties", props));
        schemas["InventoryBuilding"] = Shape(["id", "siteId", "name", "properties"], ("id", uuid), ("siteId", uuid), ("name", text), ("properties", props));
        schemas["InventoryRoom"] = Shape(["id", "buildingId", "name", "properties"], ("id", uuid), ("buildingId", uuid), ("name", text), ("properties", props));
        schemas["InventoryRack"] = Shape(["id", "roomId", "name", "location", "sizeU", "properties"], ("id", uuid), ("roomId", nullableId), ("name", text), ("location", text), ("sizeU", integer), ("properties", props));
        schemas["InventoryDevice"] = Shape(["id", "kind", "rackId", "roomId", "name", "sizeU", "sortOrder", "poeBudget", "properties"],
            ("id", uuid), ("kind", Obj(("type", "string"), ("enum", new[] { "rackEquipment", "dose", "endDevice" }))),
            ("rackId", nullableId), ("roomId", nullableId), ("name", text), ("sizeU", Obj(("type", "integer"), ("nullable", true))),
            ("sortOrder", integer), ("poeBudget", number), ("properties", props));
        schemas["InventoryPortGroup"] = Shape(["id", "deviceId", "type", "name", "prefix", "sortOrder"],
            ("id", uuid), ("deviceId", uuid), ("type", text), ("name", text), ("prefix", text), ("sortOrder", integer));
        schemas["InventoryPort"] = Shape(["id", "deviceId", "groupId", "type", "gn", "sortOrder", "label", "status", "poe", "watts", "color", "face", "powerRole", "properties"],
            ("id", uuid), ("deviceId", uuid), ("groupId", uuid), ("type", text), ("gn", integer), ("sortOrder", integer), ("label", text), ("status", text),
            ("poe", boolean), ("watts", number), ("color", nullableText), ("face", text), ("powerRole", text), ("properties", props));
        schemas["InventoryConnection"] = Shape(["id", "fromPortId", "toPortId", "note", "color", "patch", "createdAt", "properties"],
            ("id", uuid), ("fromPortId", uuid), ("toPortId", uuid), ("note", text), ("color", nullableText),
            ("patch", Obj(("type", "string"), ("enum", new[] { "none", "planned", "progress", "done", "tested" }))), ("createdAt", Text("date-time")), ("properties", props));
        schemas["InventoryProject"] = Shape(["customerId", "revision", "sites", "buildings", "rooms", "racks", "devices", "portGroups", "ports", "connections"],
            ("customerId", uuid), ("revision", Obj(("type", "integer"), ("format", "int64"))),
            ("sites", ArrayOf(Ref("InventorySite"))), ("buildings", ArrayOf(Ref("InventoryBuilding"))), ("rooms", ArrayOf(Ref("InventoryRoom"))),
            ("racks", ArrayOf(Ref("InventoryRack"))), ("devices", ArrayOf(Ref("InventoryDevice"))), ("portGroups", ArrayOf(Ref("InventoryPortGroup"))),
            ("ports", ArrayOf(Ref("InventoryPort"))), ("connections", ArrayOf(Ref("InventoryConnection"))));
        schemas["InventoryImpact"] = Shape(["rackIds", "deviceIds", "groupIds", "portIds", "connectionIds"],
            ("rackIds", ids), ("deviceIds", ids), ("groupIds", ids), ("portIds", ids), ("connectionIds", ids));
        schemas["InventoryPreview"] = Shape(["customerId", "revision", "impact", "confirmationToken"],
            ("customerId", uuid), ("revision", integer), ("impact", Ref("InventoryImpact")), ("confirmationToken", text));
        schemas["InventoryCommandResult"] = Shape(["customerId", "revision", "requestId", "operationId", "result"],
            ("customerId", uuid), ("revision", integer), ("requestId", uuid), ("operationId", uuid),
            ("result", Shape(["resourceId"], ("resourceId", uuid), ("batchId", uuid), ("compensatedOperationId", uuid), ("createdIds", ids), ("changedIds", ids),
                ("removedIds", Obj(("oneOf", new[] { ids, Ref("InventoryImpact") }))))));
        object Named(bool update, string? parent = null)
        {
            var fields = new List<(string, object?)> { ("id", uuid), ("name", text), ("properties", props) };
            if (parent is not null) fields.Add((parent, uuid));
            return Shape(update ? ["id"] : parent is null ? ["name"] : ["name", parent], fields.ToArray());
        }
        object IdOnly = Shape(["id"], ("id", uuid));
        object Delete = Shape(["id", "confirmationToken"], ("id", uuid), ("confirmationToken", text));
        object DeviceDeleteIds = Obj(("type", "array"), ("items", uuid), ("minItems", 1), ("maxItems", 64), ("uniqueItems", true));
        object DevicesDelete = Shape(["deviceIds", "confirmationToken"], ("deviceIds", DeviceDeleteIds), ("confirmationToken", text));
        object Rack(bool create) => Shape(create ? ["name", "sizeU"] : ["id"], ("id", uuid), ("name", text), ("roomId", nullableId), ("sizeU", integer), ("location", text), ("properties", props));
        object Group = Shape(["type", "count"], ("type", text), ("count", Obj(("type", "integer"), ("minimum", 1), ("maximum", 96))), ("name", text), ("prefix", text));
        object Pair = Shape(["fromPortId", "toPortId"], ("fromPortId", uuid), ("toPortId", uuid), ("note", text), ("color", nullableText), ("patch", text), ("properties", props), ("confirmedReservedPortIds", ids));
        var commands = new Dictionary<string, object?>
        {
            ["site.create"] = Named(false), ["site.update"] = Named(true), ["site.delete"] = IdOnly,
            ["building.create"] = Named(false, "siteId"), ["building.update"] = Named(true, "siteId"), ["building.delete"] = IdOnly,
            ["room.create"] = Named(false, "buildingId"), ["room.update"] = Named(true, "buildingId"), ["room.delete"] = IdOnly,
            ["rack.create"] = Rack(true), ["rack.update"] = Rack(false), ["rack.assignRoom"] = Shape(["id", "roomId"], ("id", uuid), ("roomId", nullableId)),
            ["rack.delete"] = Delete, ["rack.duplicate"] = Shape(["id", "includeConnections"], ("id", uuid), ("includeConnections", boolean), ("name", text), ("confirmedReservedPortIds", ids)),
            ["device.create"] = Shape(["kind", "name"], ("kind", text), ("name", text), ("rackId", nullableId), ("roomId", nullableId), ("sizeU", integer), ("poeBudget", number), ("properties", props), ("portGroups", ArrayOf(Group))),
            ["device.createFromCatalog"] = Ref("CreateDeviceFromCatalog"),
            ["device.createFromPrivateTemplate"] = Ref("CreateDeviceFromPrivateTemplate"),
            ["device.createFromSharedTemplate"] = Ref("CreateDeviceFromSharedTemplate"),
            ["device.update"] = Shape(["id"], ("id", uuid), ("name", text), ("sizeU", integer), ("poeBudget", number), ("properties", props)),
            ["device.move"] = Shape(["id"], ("id", uuid), ("rackId", uuid), ("roomId", uuid)),
            ["devices.delete"] = DevicesDelete,
            ["device.reorder"] = Shape(["rackId", "deviceIds"], ("rackId", uuid), ("deviceIds", ids)), ["device.delete"] = Delete,
            ["device.editPortGroups"] = Shape(["deviceId", "groups", "removedPortIds"], ("deviceId", uuid), ("confirmationToken", text), ("removedPortIds", ids),
                ("groups", ArrayOf(Shape(["type", "retainedPortIds", "addCount"], ("id", uuid), ("type", text), ("name", text), ("prefix", text), ("retainedPortIds", ids), ("addCount", integer))))),
            ["ports.update"] = Shape(["deviceId", "groupId", "groupType", "portIds", "changes"], ("deviceId", uuid), ("groupId", uuid), ("groupType", text), ("portIds", ids),
                ("changes", Shape([], ("status", text), ("poe", boolean), ("watts", number), ("color", nullableText), ("label", text), ("face", text), ("powerRole", text), ("properties", props)))),
            ["operations.compensate"] = Obj(("type", "object"), ("required", new[] { "operationId" }), ("additionalProperties", false), ("properties", Obj(("operationId", uuid)))),
            ["connections.create"] = Pair,
            ["connections.createBatch"] = Shape(["pairs"], ("pairs", ArrayOf(Pair)), ("confirmedReservedPortIds", ids)),
            ["connections.update"] = Shape(["connectionId"], ("connectionId", uuid), ("note", text), ("color", nullableText), ("patch", text), ("properties", props)),
            ["connections.disconnect"] = Shape(["connectionId"], ("connectionId", uuid)),
            ["connections.reconnect"] = Shape(["connectionId", "keepPortId", "newPortId"], ("connectionId", uuid), ("keepPortId", uuid), ("newPortId", uuid), ("confirmedReservedPortIds", ids))
        };
        schemas["InventoryCommandRequest"] = Obj(("oneOf", commands.Select(c => Shape(["type", "payload"],
            ("type", Obj(("type", "string"), ("enum", new[] { c.Key }))), ("payload", c.Value))).ToArray()));
        schemas["InventoryPreviewRequest"] = Shape(["type", "payload"],
            ("type", Obj(("type", "string"), ("enum", new[] { "rack.delete", "device.delete", "devices.delete", "device.editPortGroups" }))), ("payload", properties));
        schemas["InventoryOperationState"] = Shape(["state", "customerId", "requestId"],
            ("state", Obj(("type", "string"), ("enum", new[] { "committed", "notRecorded", "cancelled" }))), ("customerId", uuid), ("requestId", uuid),
            ("revision", integer), ("operation", Obj(("allOf", new[] { Ref("InventoryCommandResult") }), ("nullable", true))));
        Dictionary<string, object?> Endpoint(string name, string description, string schema, string? request = null, bool command = false, bool preview = false, bool operationId = false)
        {
            var op = (Dictionary<string, object?>)Operation(name, description, "200", Ref(schema), request,
                mutation: request is not null, revision: command || preview, customer: true, etag: name == "readCustomerProject");
            var parameters = (List<object>)op["parameters"]!;
            foreach (var parameter in parameters.Cast<Dictionary<string, object?>>())
            {
                if (Equals(parameter["name"], "If-Match")) parameter["description"] = "Quoted customer revision; commands mutate one customer atomically.";
                if (Equals(parameter["name"], "X-RackClick-Actor")) parameter["required"] = true;
            }
            if (preview && name != "cancelInventoryOperation") parameters.RemoveAll(p => Equals(((Dictionary<string, object?>)p)["name"], "Idempotency-Key"));
            if (operationId) parameters.Add(Obj(("in", "path"), ("name", "requestId"), ("required", true), ("schema", uuid)));
            return op;
        }
        paths["/api/v1/customers/{id}/project"] = Obj(("get", Endpoint("readCustomerProject", "One authorized RepeatableRead snapshot and customer ETag. Every identity is a UUID; local/cross-rack is derived.", "InventoryProject")));
        paths["/api/v1/customers/{id}/commands"] = Obj(("post", Endpoint("executeInventoryCommand", "Requires inventory.read plus inventory.edit or inventory.delete for .delete commands. Server validates every object and both endpoints. Replays remain bound to actor/customer/key/digest; reply follows commit. devices.delete accepts 1..64 distinct nonempty UUID deviceIds of any device kind in this customer; one atomic revision/audit, resourceId and batchId equal the server-generated operationId/audit.id (batch operation identity, not requestId), removedIds exact union including incident connections. No internal Dose passage is inferred.", "InventoryCommandResult", "InventoryCommandRequest", command: true)));
        paths["/api/v1/customers/{id}/commands/preview"] = Obj(("post", Endpoint("previewInventoryImpact", "Authorized coherent impact. Token binds actor/customer/revision/payload and impact; commit revalidates. devices.delete takes deviceIds without confirmationToken, holds customer SHARE lock, revalidates current session/read/delete after waits and before return; other preview types keep existing RepeatableRead behavior. Preview changes no revision or inventory.", "InventoryPreview", "InventoryPreviewRequest", preview: true)));
        paths["/api/v1/customers/{id}/operations/{requestId}"] = Obj(("get", Endpoint("readInventoryOperation", "Current actor only. notRecorded does not prove a delayed request cannot arrive; keep an uncertain operation until replay or confirmed cancellation.", "InventoryOperationState", operationId: true)));
        paths["/api/v1/customers/{id}/operations/{requestId}/cancel"] = Obj(("post", Endpoint("cancelInventoryOperation", "Body and If-Match must be the original command and original revision (not the current revision). Idempotency-Key must equal requestId in the route; mismatch returns 422 request_id_mismatch. Serializes against commit; returns committed result or durable cancelled tombstone. Does not modify inventory revision. Retain the journal until either result is confirmed.", "InventoryOperationState", "InventoryCommandRequest", preview: true, operationId: true)));
    }
}
