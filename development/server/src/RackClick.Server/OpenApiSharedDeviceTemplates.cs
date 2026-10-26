namespace RackClick.Server;

public static partial class OpenApiDocument
{
    private static void AddSharedDeviceTemplates(Dictionary<string, object?> paths, Dictionary<string, object?> schemas)
    {
        object uuid = Text("uuid"), text = Text(), boolean = Obj(("type", "boolean"));
        object revision = Obj(("type", "integer"), ("format", "int64"), ("minimum", 0), ("maximum", SharedDeviceTemplates.MaximumRevision));
        object sha = Obj(("type", "string"), ("pattern", "^[0-9a-f]{64}$"));
        object version = Obj(("type", "integer"), ("enum", new[] { 1 }));
        object name = Obj(("type", "string"), ("minLength", 1), ("maxLength", 100));
        object kind = Obj(("type", "string"), ("enum", new[] { "sharedTemplates" }));
        object Closed(params (string Key, object? Value)[] fields)
        {
            var result = (Dictionary<string, object?>)Shape(fields.Select(f => f.Key).ToArray(), fields);
            result["additionalProperties"] = false; return result;
        }
        schemas["SharedTemplatePublish"] = Closed(("type", Obj(("type", "string"), ("enum", new[] { "publish" }))),
            ("privateTemplateId", uuid), ("definitionVersion", version), ("definitionSha256", sha), ("name", name));
        schemas["SharedTemplateDeactivate"] = Closed(("type", Obj(("type", "string"), ("enum", new[] { "deactivate" }))), ("templateId", uuid));
        schemas["SharedTemplateIntent"] = Obj(("oneOf", new[] { Ref("SharedTemplatePublish"), Ref("SharedTemplateDeactivate") }));
        var metadata = new (string Key, object? Value)[] { ("id", uuid), ("name", name), ("active", boolean), ("definitionVersion", version),
            ("definitionSha256", sha), ("kind", Obj(("type", "string"), ("enum", new[] { "rackEquipment", "dose", "endDevice" }))),
            ("sizeU", Obj(("type", "integer"), ("nullable", true), ("minimum", 1), ("maximum", 1000))),
            ("groupCount", Obj(("type", "integer"), ("minimum", 0), ("maximum", 32))),
            ("portCount", Obj(("type", "integer"), ("minimum", 0), ("maximum", 3072))), ("publishedById", uuid), ("publishedByName", name) };
        schemas["SharedTemplateMetadata"] = Closed(metadata);
        schemas["SharedTemplateDetail"] = Closed(metadata.Concat(new (string Key, object? Value)[] {
            ("definitionByteLength", Obj(("type", "integer"), ("minimum", 1), ("maximum", PrivateDeviceTemplates.MaximumDefinitionBytes))),
            ("definitionBase64", Obj(("type", "string"), ("format", "byte"), ("description", "Exact immutable UTF-8 bytes copied from the publisher's own private template, without reserialization. Verify byte length and SHA256 before parsing closed v1."))) }).ToArray());
        schemas["SharedTemplatesSnapshot"] = Closed(("kind", kind), ("customerId", uuid), ("revision", revision),
            ("templates", Obj(("type", "array"), ("maxItems", SharedDeviceTemplates.MaximumActive), ("items", Ref("SharedTemplateMetadata")))));
        schemas["SharedTemplateSnapshot"] = Closed(("kind", kind), ("customerId", uuid), ("revision", revision), ("template", Ref("SharedTemplateDetail")));
        schemas["SharedTemplateChange"] = Closed(("type", Obj(("type", "string"), ("enum", new[] { "publish", "deactivate" }))),
            ("templateId", uuid), ("name", name), ("active", boolean), ("changed", boolean), ("definitionVersion", version), ("definitionSha256", sha));
        schemas["SharedTemplateResult"] = Closed(("kind", kind), ("customerId", uuid), ("actorId", uuid), ("revision", revision),
            ("requestId", uuid), ("operationId", uuid), ("result", Ref("SharedTemplateChange")));
        schemas["SharedTemplateStatus"] = Closed(("state", Obj(("type", "string"), ("enum", new[] { "notRecorded", "committed", "cancelled" }))),
            ("customerId", uuid), ("actorId", uuid), ("revision", revision), ("requestId", uuid),
            ("operation", Obj(("allOf", new[] { Ref("SharedTemplateResult") }), ("nullable", true))));
        schemas["CreateDeviceFromSharedTemplate"] = schemas["CreateDeviceFromPrivateTemplate"];

        const string authority = "Immutable copies shared only in one customer. Current inventory.read required on every call. Publish/deactivate/status/cancel additionally require templates.publish, without inventory.edit. Instantiation requires read+edit without publish. All authorization/session checks repeat after waits and before commit or replay. Private source remains actor-owned and inaccessible to others. No source UUID or blueprint in public receipts/audit. GET never inserts. Empty queries only. ";
        Dictionary<string, object?> Endpoint(string id, string response, bool mutation = false, bool requestPath = false, bool templatePath = false, string description = "")
        {
            var operation = (Dictionary<string, object?>)Operation(id, authority + description, "200", Ref(response),
                request: mutation ? "SharedTemplateIntent" : null, mutation: mutation, customer: true, etag: true);
            var parameters = (List<object>)operation["parameters"]!;
            if (mutation)
            {
                parameters.Add(Header("If-Match", "Exact quoted shared-templates-N, 0..9007199254740991; independent of private/inventory revisions. Cancellation takes original revision even when stale."));
                parameters.Add(Header("Idempotency-Key", "Nonempty UUID; cancellation path requestId must match.", uuid));
                parameters.Add(Header("X-RackClick-Actor", "Original actor UUID; actor mismatch409 actor_changed.", uuid));
            }
            if (requestPath) parameters.Add(Obj(("in", "path"), ("name", "requestId"), ("required", true), ("schema", uuid)));
            if (templatePath) parameters.Add(Obj(("in", "path"), ("name", "templateId"), ("required", true), ("schema", uuid)));
            var responses = (Dictionary<string, object?>)operation["responses"]!;
            responses["404"] = Response("Customer outside read scope, shared template outside customer, own source absent/not owned or operation in another context.", Ref("Error"));
            responses["409"] = Response("request_id_reused, operation_cancelled, template_inactive, template_changed, templates_limit, templates_revision_exhausted or templates_conflict.", Ref("Error"));
            responses["422"] = Response("Closed request/query/UUID/hash/name/shared ETag validation error.", Ref("Error"));
            if (mutation) { responses["412"] = Response("revision_conflict; keep draft.", Ref("Error")); responses["428"] = Response("Original shared If-Match required.", Ref("Error")); }
            ((Dictionary<string, object?>)((Dictionary<string, object?>)responses["200"]!)["headers"]!)["ETag"] = Obj(("schema", text),
                ("description", "Exact shared-templates-N. POST/replay result revision is historical; status/cancel outer revision is current."));
            return operation;
        }
        const string root = "/api/v1/customers/{id}/catalog/shared-templates";
        paths[root] = Obj(("get", Endpoint("readSharedDeviceTemplates", "SharedTemplatesSnapshot", description: "Active metadata max128, stable UUID order, absent aggregate revision0.")),
            ("post", Endpoint("changeSharedDeviceTemplate", "SharedTemplateResult", mutation: true, description: "Publish always creates a new UUID by exact byte copy from own active source. Deactivate any shared template with current publish authority; inactive noop keeps revision. Atomic receipt/audit.")));
        paths[root + "/{templateId}"] = Obj(("get", Endpoint("readSharedDeviceTemplate", "SharedTemplateSnapshot", templatePath: true, description: "Active or retired detail remains readable in scope, including author captured at publication.")));
        paths[root + "/operations/{requestId}"] = Obj(("get", Endpoint("readSharedDeviceTemplateOperation", "SharedTemplateStatus", requestPath: true, description: "Actor-owned terminal receipt, with no source dependency.")));
        paths[root + "/operations/{requestId}/cancel"] = Obj(("post", Endpoint("cancelSharedDeviceTemplateOperation", "SharedTemplateStatus", mutation: true, requestPath: true, description: "Exact original intent/revision; returns committed receipt or atomic cancellation fence. Never loads source or requires current revision.")));
    }
}
