namespace RackClick.Server;

public static partial class OpenApiDocument
{
    private static void AddPrivateDeviceTemplates(Dictionary<string, object?> paths, Dictionary<string, object?> schemas)
    {
        object uuid = Text("uuid"), text = Text(), boolean = Obj(("type", "boolean"));
        object revision = Obj(("type", "integer"), ("format", "int64"), ("minimum", 0), ("maximum", PrivateDeviceTemplates.MaximumRevision));
        object sha = Obj(("type", "string"), ("pattern", "^[0-9a-f]{64}$"));
        object version = Obj(("type", "integer"), ("enum", new[] { 1 }));
        object kind = Obj(("type", "string"), ("enum", new[] { "privateTemplates" }));
        object deviceKind = Obj(("type", "string"), ("enum", new[] { "rackEquipment", "dose", "endDevice" }));
        object nullableSize = Obj(("type", "integer"), ("nullable", true), ("minimum", 1), ("maximum", 1000));
        object nullableId = Obj(("type", "string"), ("format", "uuid"), ("nullable", true));
        object color = Obj(("type", "string"), ("pattern", "^#[0-9A-Fa-f]{6}$"));
        object number = Obj(("type", "number"), ("nullable", true), ("minimum", 0), ("maximum", 999999));
        object name = Obj(("type", "string"), ("minLength", 1), ("maxLength", 100));
        object Closed(string[] required, params (string Key, object? Value)[] fields)
        {
            var result = (Dictionary<string, object?>)Shape(required, fields); result["additionalProperties"] = false; return result;
        }
        schemas["PrivateTemplateCapture"] = Closed(["type", "deviceId", "name", "sourceRevision"],
            ("type", Obj(("type", "string"), ("enum", new[] { "capture" }))), ("deviceId", uuid), ("name", name),
            ("sourceRevision", Obj(("type", "integer"), ("format", "int64"), ("minimum", 1), ("maximum", PrivateDeviceTemplates.MaximumRevision))));
        schemas["PrivateTemplateDeactivate"] = Closed(["type", "templateId"],
            ("type", Obj(("type", "string"), ("enum", new[] { "deactivate" }))), ("templateId", uuid));
        schemas["PrivateTemplateRename"] = Closed(["type", "templateId", "name"],
            ("type", Obj(("type", "string"), ("enum", new[] { "rename" }))), ("templateId", uuid), ("name", name));
        schemas["PrivateTemplateIntent"] = Obj(("oneOf", new[] { Ref("PrivateTemplateCapture"), Ref("PrivateTemplateDeactivate"), Ref("PrivateTemplateRename") }));
        var metadata = new (string Key, object? Value)[] { ("id", uuid), ("name", name), ("active", boolean),
            ("definitionVersion", version), ("definitionSha256", sha), ("kind", deviceKind), ("sizeU", nullableSize),
            ("groupCount", Obj(("type", "integer"), ("minimum", 0), ("maximum", 32))),
            ("portCount", Obj(("type", "integer"), ("minimum", 0), ("maximum", 3072))) };
        schemas["PrivateTemplateMetadata"] = Closed(metadata.Select(p => p.Key).ToArray(), metadata);
        var detail = metadata.Concat(new (string Key, object? Value)[] {
            ("definitionByteLength", Obj(("type", "integer"), ("minimum", 1), ("maximum", PrivateDeviceTemplates.MaximumDefinitionBytes))),
            ("definitionBase64", Obj(("type", "string"), ("format", "byte"), ("description", "Exact immutable UTF-8 JSON bytes whose lowercase SHA256 is definitionSha256; decode, verify byte length/hash, then parse closed v1 definition. Never reserialize JavaScript decimals for hashing."))) }).ToArray();
        schemas["PrivateTemplateDetail"] = Closed(detail.Select(p => p.Key).ToArray(), detail);
        schemas["PrivateTemplatesSnapshot"] = Closed(["kind", "customerId", "ownerId", "revision", "templates"],
            ("kind", kind), ("customerId", uuid), ("ownerId", uuid), ("revision", revision),
            ("templates", Obj(("type", "array"), ("maxItems", PrivateDeviceTemplates.MaximumActive), ("items", Ref("PrivateTemplateMetadata")))));
        schemas["PrivateTemplateSnapshot"] = Closed(["kind", "customerId", "ownerId", "revision", "template"],
            ("kind", kind), ("customerId", uuid), ("ownerId", uuid), ("revision", revision), ("template", Ref("PrivateTemplateDetail")));
        schemas["PrivateTemplateChange"] = Closed(["type", "templateId", "name", "active", "changed", "definitionVersion", "definitionSha256"],
            ("type", Obj(("type", "string"), ("enum", new[] { "capture", "deactivate", "rename", "create" }))), ("templateId", uuid), ("name", name),
            ("active", boolean), ("changed", boolean), ("definitionVersion", version), ("definitionSha256", sha));
        schemas["PrivateTemplateResult"] = Closed(["kind", "customerId", "ownerId", "revision", "requestId", "operationId", "result"],
            ("kind", kind), ("customerId", uuid), ("ownerId", uuid), ("revision", revision), ("requestId", uuid), ("operationId", uuid), ("result", Ref("PrivateTemplateChange")));
        schemas["PrivateTemplateStatus"] = Closed(["state", "customerId", "ownerId", "revision", "requestId", "operation"],
            ("state", Obj(("type", "string"), ("enum", new[] { "notRecorded", "committed", "cancelled" }))),
            ("customerId", uuid), ("ownerId", uuid), ("revision", revision), ("requestId", uuid),
            ("operation", Obj(("allOf", new[] { Ref("PrivateTemplateResult") }), ("nullable", true))));
        schemas["CreateDeviceFromPrivateTemplate"] = Closed(["templateId", "definitionVersion", "definitionSha256", "kind", "rackId", "roomId", "name", "color", "poeBudget", "notes"],
            ("templateId", uuid), ("definitionVersion", version), ("definitionSha256", sha), ("kind", deviceKind), ("rackId", nullableId), ("roomId", nullableId),
            ("name", name), ("color", color), ("poeBudget", number), ("notes", Closed(["sn", "model", "ip", "firmware", "text"],
                new[] { "sn", "model", "ip", "firmware", "text" }.Select(k => (k, (object?)Obj(("type", "string"), ("maxLength", 2000)))).ToArray())));
        // JSON schema for the decoded bytes; these properties never carry inventory IDs or extension bags.
        schemas["PrivateTemplatePort"] = Closed(["gn", "sortOrder", "type", "label", "poe", "color", "face", "powerRole"],
            ("gn", Obj(("type", "integer"), ("minimum", 1))), ("sortOrder", Obj(("type", "integer"), ("minimum", 0), ("maximum", 95))),
            ("type", Obj(("type", "string"), ("enum", RackClick.Domain.InventoryRules.PortTypes))),
            ("label", Obj(("type", "string"), ("maxLength", 500))), ("poe", boolean),
            ("color", Obj(("type", "string"), ("nullable", true), ("pattern", "^#[0-9A-Fa-f]{6}$"))),
            ("face", Obj(("type", "string"), ("enum", new[] { "auto", "front", "rear" }))),
            ("powerRole", Obj(("type", "string"), ("enum", new[] { "unspecified", "inlet", "outlet" }))));
        schemas["PrivateTemplateGroup"] = Closed(["key", "type", "name", "prefix", "sortOrder", "ports"],
            ("key", Obj(("type", "string"), ("pattern", "^g([1-9]|[12][0-9]|3[0-2])$"))), ("type", text),
            ("name", Obj(("type", "string"), ("maxLength", 100))), ("prefix", Obj(("type", "string"), ("maxLength", 100))),
            ("sortOrder", Obj(("type", "integer"), ("minimum", 0), ("maximum", 31))),
            ("ports", Obj(("type", "array"), ("minItems", 1), ("maxItems", 96), ("items", Ref("PrivateTemplatePort")))));
        schemas["PrivateTemplateDefinition"] = Closed(["kind", "sizeU", "poeBudget", "icon", "color", "visualFamily", "portGroups"],
            ("kind", deviceKind), ("sizeU", nullableSize), ("poeBudget", number),
            ("icon", Obj(("type", "string"), ("maxLength", 100))), ("color", color),
            ("visualFamily", Obj(("type", "string"), ("enum", new[] { "storage", "ups", "blank", "switch", "panel" }))),
            ("portGroups", Obj(("type", "array"), ("maxItems", 32), ("items", Ref("PrivateTemplateGroup")))));
        schemas["PrivateTemplateConfigurationCreate"] = Closed(["type", "name", "definitionVersion", "definition"],
            ("type", Obj(("type", "string"), ("enum", new[] { "create" }))), ("name", name), ("definitionVersion", version),
            ("definition", Ref("PrivateTemplateDefinition")));
        schemas["PrivateTemplateConfigurationCancel"] = Closed(["type", "name", "definitionVersion", "inputDefinitionSha256"],
            ("type", Obj(("type", "string"), ("enum", new[] { "create" }))), ("name", name), ("definitionVersion", version),
            ("inputDefinitionSha256", sha));

        const string authority = "Detached, actor-owned private configurations. Owner derived only from current session. All calls require current inventory.read on the customer context; capture, deactivate, rename, create, status and cancellation additionally require inventory.edit. Session/grants rechecked after waits and before commit. Queries closed/empty. Customer lock precedes personal aggregate lock. Personal changes never advance customer/Systemhaus revision or inventory change feed. Stored v1 is immutable; no sharing/publication/in-place definition edit. ";
        Dictionary<string, object?> Endpoint(string id, string response, bool mutation = false, bool requestPath = false, bool templatePath = false, string description = "", string? requestSchema = null)
        {
            var operation = (Dictionary<string, object?>)Operation(id, authority + description, "200", Ref(response),
                request: mutation ? requestSchema ?? "PrivateTemplateIntent" : null, mutation: mutation, customer: true, etag: true);
            var parameters = (List<object>)operation["parameters"]!;
            if (mutation)
            {
                parameters.Add(Header("If-Match", "Original exact personal templates-N, 0..9007199254740991, no leading zeroes. Not a customer ETag; cancellation accepts stale original revision."));
                parameters.Add(Header("Idempotency-Key", "Nonempty UUID, equals cancellation route requestId.", uuid));
                parameters.Add(Header("X-RackClick-Actor", "Required original actor UUID; mismatch409 actor_changed.", uuid));
            }
            if (requestPath) parameters.Add(Obj(("in", "path"), ("name", "requestId"), ("required", true), ("schema", uuid)));
            if (templatePath) parameters.Add(Obj(("in", "path"), ("name", "templateId"), ("required", true), ("schema", uuid)));
            var responses = (Dictionary<string, object?>)operation["responses"]!;
            responses["404"] = Response("Context absent/outside current read scope, template not owned, or operation in another customer context.", Ref("Error"));
            responses["409"] = Response("request_id_reused, operation_cancelled, template_inactive, template_changed, templates_limit, templates_revision_exhausted or templates_conflict.", Ref("Error"));
            responses["422"] = Response("Closed DTO/query/UUID/personal ETag/definition validation error; no silent truncation.", Ref("Error"));
            if (mutation)
            {
                responses["412"] = Response("revision_conflict for personal ETag; source_revision_conflict for capture sourceRevision. Keep draft and refresh only the relevant aggregate.", Ref("Error"));
                responses["428"] = Response("Original personal If-Match required.", Ref("Error"));
            }
            ((Dictionary<string, object?>)((Dictionary<string, object?>)responses["200"]!)["headers"]!)["ETag"] = Obj(("schema", text),
                ("description", "Exact quoted templates-N. POST/replay receipt revision is historical; list/detail/status/cancel outer revision is current. Refresh list after confirmation."));
            return operation;
        }
        const string root = "/api/v1/customers/{id}/catalog/private-templates";
        paths[root] = Obj(("get", Endpoint("readPrivateDeviceTemplates", "PrivateTemplatesSnapshot", description: "Active metadata only, max128, stable UUID order, missing aggregate revision0; GET never inserts.")),
            ("post", Endpoint("changePrivateDeviceTemplate", "PrivateTemplateResult", mutation: true, description: "Capture requires exact source customer revision; persists configuration only with group/port labels, family/face/PoE/roles. Excludes source IDs, names/notes/private extension properties, status/watts and all connections. 32groups,96ports/group,1MiB exact definition bytes,128active; errors instead of truncation. Deactivate immutable tombstone. Rename changes only an active own template metadata name, trim and 1..100 Unicode scalars without controls or normalization; duplicate names allowed, definition bytes/hash/version/UUID/creation unchanged. Exact normalized no-op retains revision (including maximum) but commits operation/audit. Replay precedes source/template reads. Digest binds owner, house, original context, normalized closed intent and original personal revision. Receipt/audit/definition/revision commit atomically.")));
        paths[root + "/{templateId}"] = Obj(("get", Endpoint("readPrivateDeviceTemplate", "PrivateTemplateSnapshot", templatePath: true, description: "Own metadata plus base64 exact immutable definition bytes and byte length, including an inactive own template. SHA256 verifies the decoded bytes, not JSON.stringify. Generic properties and inventory identifiers are forbidden in the decoded v1 shape.")));
        paths[root + "/operations/{requestId}"] = Obj(("get", Endpoint("readPrivateDeviceTemplateOperation", "PrivateTemplateStatus", requestPath: true, description: "Requires read+edit; own original customer context. Outer revision current, committed inner receipt immutable/historical. notRecorded is not a fence.")));
        paths[root + "/operations/{requestId}/cancel"] = Obj(("post", Endpoint("cancelPrivateDeviceTemplateOperation", "PrivateTemplateStatus", mutation: true, requestPath: true, description: "Original closed body/key/personal revision; durable terminal cancellation serializes with commit and prevents delayed entry. No source/template lookup or current source revision required; no undo of a committed change. Fences retained until explicit expiry protocol.")));
        paths[root + "/configurations"] = Obj(("post", Endpoint("createPrivateDeviceTemplateConfiguration", "PrivateTemplateResult", mutation: true,
            requestSchema: "PrivateTemplateConfigurationCreate", description: "Creates a NEW immutable own v1 template; never changes historical definitions/equipment. Explicit recursively closed required fields, no duplicates/extensions/IDs/status/cables. Ordered keys g1..g32 and zero-based group/port sortOrder; GN positive Int32 and unique WITHIN each group only. Existing field/domain limits, 32 groups, 1..96 ports/group, 128 active templates, 1MiB raw and canonical definition. Only this exact POST route admits body up to 1MiB+16KiB; global and compact cancellation remain 16KiB, enforced also without Content-Length. Read/edit authority checked before reading the body and repeated within the command transaction. Name trimmed 1..100 Unicode scalars without normalization; free text limits icon/group name/prefix100 and port label500 Unicode scalars. Digest family privateTemplateConfigurationsV1 binds owner/house/customer/expected and create/name/version/SHA256 of exact UTF8 definition GetRawText, so lexically different inputs differ even if semantically equal. Stored hash is canonical NEW definition hash. Receipt type=create, active=true, changed=true. Replay returns immutable receipt; original Intent capture/rename/deactivate digest unchanged.")));
        paths[root + "/configurations/operations/{requestId}/cancel"] = Obj(("post", Endpoint("cancelPrivateDeviceTemplateConfiguration", "PrivateTemplateStatus", mutation: true, requestPath: true,
            requestSchema: "PrivateTemplateConfigurationCancel", description: "Compact create intent uses exact original inputDefinitionSha256, normalized name, version1 and original expected personal revision; no definition/templateId. Same new-family digest and request lock as create. Stale original revision allowed for a durable cancellation fence; committed receipts remain committed. GET operations/{requestId} recovers type=create with existing closed status shape. No blueprint is retained in operation or audit JSON.")));
    }
}
