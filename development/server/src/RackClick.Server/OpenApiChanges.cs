namespace RackClick.Server;

public static partial class OpenApiDocument
{
    private static void AddChanges(Dictionary<string, object?> paths, Dictionary<string, object?> schemas)
    {
        object uuid = Text("uuid"), revision = Obj(("type", "integer"), ("format", "int64"), ("minimum", 1));
        object nullableId = Obj(("type", "string"), ("format", "uuid"), ("nullable", true));
        object nullableText = Obj(("type", "string"), ("nullable", true));
        object Closed(string[] required, params (string Key, object? Value)[] properties)
        {
            var value = (Dictionary<string, object?>)Shape(required, properties);
            value["additionalProperties"] = false; return value;
        }
        object Bounded(string name, int maximum) => Obj(("type", "array"), ("items", Ref(name)), ("maxItems", maximum));
        schemas["InventoryChangeActor"] = Closed(["id", "userNameCurrent"], ("id", uuid), ("userNameCurrent", nullableText));
        schemas["InventoryChangedPort"] = Closed(["id", "deviceId", "groupId", "type", "gn"],
            ("id", uuid), ("deviceId", uuid), ("groupId", uuid),
            ("type", Obj(("type", "string"), ("enum", RackClick.Domain.InventoryRules.PortTypes))),
            ("gn", Obj(("type", "integer"), ("minimum", 1), ("maximum", int.MaxValue))));
        schemas["InventoryChangedConnection"] = Closed(["id", "fromPortId", "toPortId"],
            ("id", uuid), ("fromPortId", uuid), ("toPortId", uuid));
        schemas["InventoryChangeContext"] = Closed(["status", "beforePorts", "afterPorts", "beforeConnections", "afterConnections"],
            ("status", Obj(("type", "string"), ("enum", new[] { "captured", "notAvailable" }))),
            ("beforePorts", Bounded("InventoryChangedPort", 256)), ("afterPorts", Bounded("InventoryChangedPort", 256)),
            ("beforeConnections", Bounded("InventoryChangedConnection", 128)), ("afterConnections", Bounded("InventoryChangedConnection", 128)));
        schemas["InventoryChangeEvent"] = Closed(["id", "actor", "action", "resourceId", "revisionBefore", "revisionAfter", "occurredAt", "context"],
            ("id", uuid), ("actor", Ref("InventoryChangeActor")),
            ("action", Obj(("type", "string"), ("enum", InventoryStore.AllowedChangeActions()))), ("resourceId", nullableId),
            ("revisionBefore", revision), ("revisionAfter", revision), ("occurredAt", Text("date-time")), ("context", Ref("InventoryChangeContext")));
        schemas["InventoryChanges"] = Closed(["customerId", "currentRevision", "nextRevision", "hasMore", "refreshRequired", "events"],
            ("customerId", uuid), ("currentRevision", revision), ("nextRevision", revision), ("hasMore", Obj(("type", "boolean"))),
            ("refreshRequired", Obj(("type", "boolean"))), ("events", Bounded("InventoryChangeEvent", 100)));
        var operation = (Dictionary<string, object?>)Operation("readCustomerChanges",
            "Current inventory.read and session are revalidated before cursor parsing, after customer SHARE lock and before return. " +
            "Cursor is a customer revision, never a timestamp/UUID. Omitted afterRevision starts at current without history; use project.revision to cover snapshot-to-poll races. " +
            "Events are contiguous ascending revisions with limit+1 lookahead. Gaps, duplicates, unknown actions, incompatible wrappers or cursor ahead return refreshRequired=true, no events, hasMore=false and nextRevision=currentRevision. " +
            "Customer rename may create a gap. operation.cancel is excluded; replay/rollback do not add committed revisions. " +
            "id is historical operationId/audit_event.id; resourceId remains the direct historical resource (server-generated operationId/audit.id batch identity for devices.delete), and userNameCurrent is current, not a name snapshot. " +
            "Only ports.update, operations.compensate and five connections actions can publish captured bounded references; other/malformed context is notAvailable with four empty arrays. No raw JSON, names of inventory resources, notes, properties, secrets or operations are exposed. Read-only, no-store; current customer ETag.",
            "200", Ref("InventoryChanges"), customer: true, etag: true);
        var parameters = (List<object>)operation["parameters"]!;
        parameters.Add(Obj(("in", "query"), ("name", "afterRevision"), ("required", false), ("schema", revision)));
        parameters.Add(Obj(("in", "query"), ("name", "limit"), ("required", false),
            ("schema", Obj(("type", "integer"), ("minimum", 1), ("maximum", 100), ("default", 50)))));
        var responses = (Dictionary<string, object?>)operation["responses"]!;
        responses.Remove("403");
        responses["404"] = Response("Customer absent, foreign House or current inventory.read absent; indistinguishable.", Ref("Error"));
        responses["422"] = Response("Invalid positive Int64 cursor or limit 1..100, including duplicate query values; validated only after authorization.", Ref("Error"));
        paths["/api/v1/customers/{id}/changes"] = Obj(("get", operation));
        object NullableNumber(int minimum, int maximum) => Obj(("type", "integer"), ("nullable", true), ("minimum", minimum), ("maximum", maximum));
        object Enum(string[] values, bool nullable = false) => Obj(("type", "string"), ("enum", values), ("nullable", nullable));
        object historicalText = Obj(("type", "string"), ("nullable", true), ("maxLength", 100));
        schemas["InventoryChangedEntity"] = Closed(["relation", "kind", "id", "name", "parentKind", "parentId", "deviceKind", "rackId", "roomId", "sizeU", "positionU", "sortOrder", "groupType", "prefix", "portCount"],
            ("relation", Enum(["target", "source", "scope"])), ("kind", Enum(["site", "building", "room", "rack", "device", "portGroup"])),
            ("id", uuid), ("name", historicalText), ("parentKind", Enum(["customer", "site", "building", "room", "rack", "device"], true)), ("parentId", nullableId),
            ("deviceKind", Enum(["rackEquipment", "dose", "endDevice"], true)), ("rackId", nullableId), ("roomId", nullableId),
            ("sizeU", NullableNumber(1, 1000)), ("positionU", Obj(("type", "integer"), ("nullable", true), ("description", "Always null: schema9 has no persisted physical U position."))),
            ("sortOrder", NullableNumber(0, int.MaxValue)), ("groupType", Enum(RackClick.Domain.InventoryRules.PortTypes.Where(t => t != "rj45_poe").ToArray(), true)),
            ("prefix", historicalText), ("portCount", NullableNumber(1, 96)));
        schemas["InventoryChangeDetails"] = Closed(["status", "beforeEntities", "afterEntities"],
            ("status", Enum(["captured", "notAvailable"])), ("beforeEntities", Bounded("InventoryChangedEntity", 512)), ("afterEntities", Bounded("InventoryChangedEntity", 512)));
        schemas["InventoryDetailedChangeEvent"] = Closed(["id", "actor", "action", "resourceId", "revisionBefore", "revisionAfter", "occurredAt", "context", "details"],
            ("id", uuid), ("actor", Ref("InventoryChangeActor")), ("action", Obj(("type", "string"), ("enum", InventoryStore.AllowedChangeActions()))),
            ("resourceId", nullableId), ("revisionBefore", revision), ("revisionAfter", revision), ("occurredAt", Text("date-time")),
            ("context", Ref("InventoryChangeContext")), ("details", Ref("InventoryChangeDetails")));
        schemas["InventoryDetailedChanges"] = Closed(["customerId", "currentRevision", "nextRevision", "hasMore", "refreshRequired", "events"],
            ("customerId", uuid), ("currentRevision", revision), ("nextRevision", revision), ("hasMore", Obj(("type", "boolean"))),
            ("refreshRequired", Obj(("type", "boolean"))), ("events", Bounded("InventoryDetailedChangeEvent", 100)));
        var detailed = (Dictionary<string, object?>)Operation("readCustomerChangeDetails",
            "Opt-in extension of readCustomerChanges with identical authority, locking, cursor and gap semantics; the original route/DTO remain unchanged. " +
            "details contains versioned, transactionally captured historical names and immediate parent/location UUIDs for the 23 hierarchy/device/group actions. " +
            "No historical backfill from current tables. Old, malformed, foreign or oversized captures return notAvailable with empty arrays. At most 512 entities per side, never truncated. " +
            "Names/prefixes are literal and at most 100 Unicode scalar values; sizeU 1..1000, sortOrder 0..Int32.MaxValue, group portCount 1..96. " +
            "Fields not applicable to the entity are null; positionU is always null. Relations are target, source (duplicate before) and scope (reorder rack/edit-groups device). " +
            "Entity/action combinations are validated as a complete description. Existing seven port/connection/compensation contexts remain separate; their details is notAvailable. " +
            "No notes/properties/raw audit JSON, credentials or request hashes are projected. Current actor name is not a historical resource name. Read-only, no-store; customer ETag.",
            "200", Ref("InventoryDetailedChanges"), customer: true, etag: true);
        var detailedParameters = (List<object>)detailed["parameters"]!;
        detailedParameters.Add(Obj(("in", "query"), ("name", "afterRevision"), ("required", false), ("schema", revision)));
        detailedParameters.Add(Obj(("in", "query"), ("name", "limit"), ("required", false), ("schema", Obj(("type", "integer"), ("minimum", 1), ("maximum", 100), ("default", 50)))));
        var detailedResponses = (Dictionary<string, object?>)detailed["responses"]!;
        detailedResponses.Remove("403");
        detailedResponses["404"] = responses["404"];
        detailedResponses["422"] = responses["422"];
        paths["/api/v1/customers/{id}/changes/details"] = Obj(("get", detailed));
    }
}
