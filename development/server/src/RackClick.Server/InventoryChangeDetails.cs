using System.Globalization;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using Npgsql;
using RackClick.Domain;
using static RackClick.Server.InventoryJson;

namespace RackClick.Server;

public sealed record InventoryChangedEntity(string Relation, string Kind, Guid Id, string? Name, string? ParentKind,
    Guid? ParentId, string? DeviceKind, Guid? RackId, Guid? RoomId, int? SizeU, int? PositionU, int? SortOrder,
    string? GroupType, string? Prefix, int? PortCount);
public sealed record InventoryChangeDetails(string Status, IReadOnlyList<InventoryChangedEntity> BeforeEntities,
    IReadOnlyList<InventoryChangedEntity> AfterEntities);
public sealed record InventoryDetailedChangeEvent(Guid Id, InventoryChangeActor Actor, string Action, Guid? ResourceId,
    long RevisionBefore, long RevisionAfter, DateTime OccurredAt, InventoryChangeContext Context, InventoryChangeDetails Details);
public sealed record InventoryDetailedChanges(Guid CustomerId, long CurrentRevision, long NextRevision, bool HasMore,
    bool RefreshRequired, IReadOnlyList<InventoryDetailedChangeEvent> Events);

public sealed partial class InventoryStore
{
    private const int DetailLimit = 512;
    private sealed record DetailCapture(bool Complete, InventoryChangedEntity[] Entities);
    private static InventoryChangeDetails NoChangeDetails() => new("notAvailable", [], []);
    private static bool HasChangeDetails(string action) => ChangeActions.Contains("inventory." + action)
        && action is not ("ports.update" or "operations.compensate") && !action.StartsWith("connections.", StringComparison.Ordinal);

    // Only persisted finite columns of the affected objects are selected. No inventory snapshot, notes or properties.
    // A 513th row marks the entire description unavailable; never present a truncated deletion/duplication as complete.
    private static async Task<DetailCapture?> CaptureChangeDetails(NpgsqlConnection db, NpgsqlTransaction tx, Actor actor,
        Guid customer, string action, JsonObject payload, Guid? resource, bool before, CancellationToken ct)
    {
        if (!HasChangeDetails(action)) return null;
        bool create = action.EndsWith(".create", StringComparison.Ordinal) || action is "device.createFromCatalog" or "device.createFromPrivateTemplate" or "device.createFromSharedTemplate";
        bool delete = action.EndsWith(".delete", StringComparison.Ordinal);
        if ((before && create) || (!before && delete)) return new(true, []);
        string kind = action.Split('.')[0];
        Guid id = resource ?? (action == "device.reorder" ? Id(payload, "rackId") : action == "device.editPortGroups" ? Id(payload, "deviceId")
            : action == "devices.delete" ? Guid.Empty : Id(payload, "id"));
        Guid[] ids = action == "devices.delete" ? Ids(payload, "deviceIds") : [id];
        bool rackTree = action is "rack.delete" or "rack.duplicate";
        bool reorder = action == "device.reorder";
        bool groupsEdit = action == "device.editPortGroups";
        if (reorder) kind = "rack";
        if (groupsEdit || kind == "devices") kind = "device";
        string relation = action == "rack.duplicate" && before ? "source" : "target";
        string rootRelation = reorder || groupsEdit ? "scope" : relation;
        string rootFilter = "systemhaus_id=@house AND customer_id=@customer AND id=ANY(@ids)";
        string deviceFilter = rackTree || reorder ? "d.rack_id=ANY(@ids)" : "d.id=ANY(@ids)";
        string deviceScope = "d.systemhaus_id=@house AND d.customer_id=@customer AND " + deviceFilter;
        var selects = new List<string>();
        string Entity(string entityKind, string rel, string table, string filter, string parentKind, string parentId,
            string deviceKind = "NULL::text", string rack = "NULL::uuid", string room = "NULL::uuid", string size = "NULL::int",
            string order = "NULL::int", string groupType = "NULL::text", string prefix = "NULL::text", string count = "NULL::int") =>
            $"SELECT '{rel}'::text relation,'{entityKind}'::text kind,id,name,{parentKind} parent_kind,{parentId} parent_id," +
            $"{deviceKind} device_kind,{rack} rack_id,{room} room_id,{size} size_u,NULL::int position_u,{order} sort_order," +
            $"{groupType} group_type,{prefix} prefix,{count} port_count FROM {table} WHERE {filter}";
        if (kind is "site" or "building" or "room" or "rack")
        {
            string parentKind = kind switch { "site" => "'customer'::text", "building" => "'site'::text", "room" => "'building'::text", _ => "CASE WHEN room_id IS NULL THEN NULL::text ELSE 'room'::text END" };
            string parent = kind switch { "site" => "customer_id", "building" => "site_id", "room" => "building_id", _ => "room_id" };
            selects.Add(Entity(kind, rootRelation, "inventory_" + kind, rootFilter, parentKind, parent,
                room: kind == "rack" ? "room_id" : "NULL::uuid", size: kind == "rack" ? "size_u" : "NULL::int"));
        }
        if (kind == "device" || rackTree || reorder)
            selects.Add(Entity("device", groupsEdit ? "scope" : relation, "inventory_device d", deviceScope,
                "CASE WHEN rack_id IS NOT NULL THEN 'rack'::text ELSE 'room'::text END", "COALESCE(rack_id,room_id)",
                "d.kind", "rack_id", "room_id", "size_u", "sort_order"));
        if ((kind == "device" || rackTree) && !reorder)
            selects.Add(Entity("portGroup", relation, "inventory_port_group g",
                "g.systemhaus_id=@house AND g.customer_id=@customer AND EXISTS(SELECT 1 FROM inventory_device d WHERE " + deviceScope + " AND d.id=g.device_id)",
                "'device'::text", "device_id", order: "sort_order", groupType: "type", prefix: "prefix",
                count: "(SELECT count(*)::int FROM inventory_port p WHERE p.systemhaus_id=@house AND p.customer_id=@customer AND p.group_id=g.id)"));
        await using var command = Cmd(db, tx, string.Join(" UNION ALL ", selects) + " ORDER BY kind,id LIMIT 513",
            ("house", actor.HouseId), ("customer", customer), ("ids", ids));
        await using var rows = await command.ExecuteReaderAsync(ct);
        var values = new List<InventoryChangedEntity>();
        while (await rows.ReadAsync(ct))
        {
            string? Text(int n) => rows.IsDBNull(n) ? null : rows.GetString(n);
            Guid? Uuid(int n) => rows.IsDBNull(n) ? null : rows.GetGuid(n);
            int? Number(int n) => rows.IsDBNull(n) ? null : rows.GetInt32(n);
            values.Add(new(rows.GetString(0), rows.GetString(1), rows.GetGuid(2), Text(3), Text(4), Uuid(5), Text(6),
                Uuid(7), Uuid(8), Number(9), Number(10), Number(11), Text(12), Text(13), Number(14)));
        }
        return values.Count > DetailLimit ? new(false, []) : new(true, values.ToArray());
    }

    private static object? DetailAudit(DetailCapture? capture, Actor actor, Guid customer, string action, Guid resource)
        => capture is null ? null : new { version = 1, houseId = actor.HouseId, customerId = customer, action = "inventory." + action,
            resourceId = resource, complete = capture.Complete, entities = capture.Entities };

    // Validate raw shape and reduce private JSON in PostgreSQL, before .NET materialization. Unknown/private fields never escape.
    private static string ChangeDetailsData(string wrapper)
    {
        string value = wrapper + "->'changeDetails'";
        string Text(string field, int max) => ChangeText("v", field, max);
        string Number(string field) => $"CASE WHEN v->'{field}'='null'::jsonb THEN 'null'::jsonb WHEN jsonb_typeof(v->'{field}')='number' AND octet_length(v->>'{field}')<=10 THEN v->'{field}' ELSE NULL END";
        string NullableText(string field, int max) => $"CASE WHEN v->'{field}'='null'::jsonb THEN 'null'::jsonb ELSE {Text(field, max)} END";
        string ShapeText(string key, int max, bool nullable = false) => $"(jsonb_typeof(v->'{key}')='string' AND octet_length(v->>'{key}')<={max}" + (nullable ? $" OR v->'{key}'='null'::jsonb)" : ")");
        string ShapeNumber(string key) => $"(jsonb_typeof(v->'{key}')='number' AND octet_length(v->>'{key}')<=10 OR v->'{key}'='null'::jsonb)";
        string shape = string.Join(" AND ", new[] { ShapeText("relation", 8), ShapeText("kind", 12), ShapeText("id", 36), ShapeText("name", 400, true),
            ShapeText("parentKind", 12, true), ShapeText("parentId", 36, true), ShapeText("deviceKind", 16, true), ShapeText("rackId", 36, true), ShapeText("roomId", 36, true),
            ShapeNumber("sizeU"), ShapeNumber("positionU"), ShapeNumber("sortOrder"), ShapeText("groupType", 16, true), ShapeText("prefix", 400, true), ShapeNumber("portCount") });
        string entity = $"jsonb_build_object('shape',CASE WHEN jsonb_typeof(v)='object' THEN (SELECT count(*)=15 FROM jsonb_object_keys(v)) AND ({shape}) ELSE false END," +
            $"'relation',{Text("relation", 8)},'kind',{Text("kind", 12)},'id',{Text("id", 36)},'name',{NullableText("name", 400)}," +
            $"'parentKind',{NullableText("parentKind", 12)},'parentId',{NullableText("parentId", 36)},'deviceKind',{NullableText("deviceKind", 16)}," +
            $"'rackId',{NullableText("rackId", 36)},'roomId',{NullableText("roomId", 36)},'sizeU',{Number("sizeU")},'positionU',{Number("positionU")}," +
            $"'sortOrder',{Number("sortOrder")},'groupType',{NullableText("groupType", 16)},'prefix',{NullableText("prefix", 400)},'portCount',{Number("portCount")})";
        return $"CASE WHEN jsonb_typeof({value})='object' THEN CASE WHEN (SELECT count(*) FROM jsonb_object_keys({value}))=7 " +
            $"AND {value}->'version'='1'::jsonb AND {value}->'complete'='true'::jsonb AND jsonb_typeof({value}->'entities')='array' THEN " +
            $"CASE WHEN jsonb_array_length({value}->'entities')<={DetailLimit} THEN jsonb_build_object(" +
            $"'houseId',{ChangeText(value, "houseId")},'customerId',{ChangeText(value, "customerId")},'action',{ChangeText(value, "action", 64)},'resourceId',{ChangeText(value, "resourceId")}," +
            $"'entities',(SELECT COALESCE(jsonb_agg({entity} ORDER BY n),'[]'::jsonb) FROM jsonb_array_elements({value}->'entities') WITH ORDINALITY x(v,n))) ELSE NULL END ELSE NULL END ELSE NULL END";
    }

    private static InventoryChangeDetails ReadChangeDetails(string action, Guid? resource, Guid house, Guid customer, string? before, string? after)
    {
        if (resource is null || !HasChangeDetails(action["inventory.".Length..]) || before is null || after is null
            || before.Length > 1048576 || after.Length > 1048576) return NoChangeDetails();
        try
        {
            void Require(bool valid) { if (!valid) throw new JsonException(); }
            InventoryChangedEntity[] Read(string json)
            {
                using var document = JsonDocument.Parse(json, new JsonDocumentOptions { MaxDepth = 8 });
                var root = document.RootElement;
                Guid? Uuid(JsonElement e, string key)
                {
                    var value = e.GetProperty(key); if (value.ValueKind == JsonValueKind.Null) return null;
                    string? text = value.GetString(); Require(text?.Length == 36 && Guid.TryParseExact(text, "D", out var parsed) && parsed != Guid.Empty);
                    return Guid.ParseExact(text!, "D");
                }
                string? Text(JsonElement e, string key) => e.GetProperty(key).GetString();
                int? Number(JsonElement e, string key) => e.GetProperty(key).ValueKind == JsonValueKind.Null ? null : e.GetProperty(key).GetInt32();
                Require(Uuid(root, "houseId") == house && Uuid(root, "customerId") == customer && Uuid(root, "resourceId") == resource && Text(root, "action") == action);
                var values = root.GetProperty("entities").EnumerateArray().Select(e =>
                {
                    Require(e.GetProperty("shape").GetBoolean());
                    var entity = new InventoryChangedEntity(Text(e, "relation")!, Text(e, "kind")!, Uuid(e, "id") ?? Guid.Empty, Text(e, "name"), Text(e, "parentKind"),
                        Uuid(e, "parentId"), Text(e, "deviceKind"), Uuid(e, "rackId"), Uuid(e, "roomId"), Number(e, "sizeU"), Number(e, "positionU"), Number(e, "sortOrder"),
                        Text(e, "groupType"), Text(e, "prefix"), Number(e, "portCount"));
                    Require(ValidDetailEntity(entity) && (entity.Kind != "site" || entity.ParentId == customer)); return entity;
                }).ToArray();
                Require(values.Length <= DetailLimit && values.Select(e => (e.Kind, e.Id, e.Relation)).Distinct().Count() == values.Length);
                foreach (var group in values.Where(e => e.Kind == "portGroup"))
                    Require(values.Any(e => e.Kind == "device" && e.Id == group.ParentId && e.Relation == (group.Relation == "source" ? "source" : action == "inventory.device.editPortGroups" ? "scope" : "target")));
                return values;
            }
            var prior = Read(before); var next = Read(after);
            Require(ValidDetailSelection(action, resource.Value, prior, next));
            return new("captured", prior, next);
        }
        catch (Exception e) when (e is JsonException or InvalidOperationException or FormatException or KeyNotFoundException or OverflowException or ArgumentException)
        { return NoChangeDetails(); }
    }

    private static bool ValidDetailEntity(InventoryChangedEntity e)
    {
        bool Name(bool empty = false) => e.Name is { Length: <= 200 } name && name.EnumerateRunes().Count() <= 100
            && (empty && name.Length == 0 || name.Length > 0 && name == name.Trim() && !name.Any(char.IsControl));
        bool NoGroup() => e.GroupType is null && e.Prefix is null && e.PortCount is null;
        if (e.Id == Guid.Empty || e.ParentId == e.Id || e.Relation is not ("target" or "source" or "scope") || e.PositionU is not null || !Name(e.Kind == "portGroup")
            || e.SortOrder is < 0 || (e.ParentKind is null) != (e.ParentId is null)) return false;
        if (e.Kind is "site" or "building" or "room") return NoGroup() && e.DeviceKind is null && e.RackId is null && e.RoomId is null
            && e.SizeU is null && e.SortOrder is null && e.ParentId is not null && e.ParentKind == (e.Kind == "site" ? "customer" : e.Kind == "building" ? "site" : "building");
        if (e.Kind == "rack") return NoGroup() && e.DeviceKind is null && e.RackId is null && e.SizeU is >= 1 and <= 1000
            && e.SortOrder is null && (e.ParentKind is null || e.ParentKind == "room") && e.RoomId == e.ParentId;
        if (e.Kind == "device") return NoGroup() && e.SortOrder is >= 0 && (e.DeviceKind == "rackEquipment"
            ? e.ParentKind == "rack" && e.ParentId is not null && e.RackId == e.ParentId && e.RoomId is null && e.SizeU is >= 1 and <= 1000
            : e.DeviceKind is "dose" or "endDevice" && e.ParentKind == "room" && e.ParentId is not null && e.RoomId == e.ParentId && e.RackId is null && e.SizeU is null);
        return e.Kind == "portGroup" && e.ParentKind == "device" && e.ParentId is not null && e.DeviceKind is null && e.RackId is null && e.RoomId is null
            && e.SizeU is null && e.SortOrder is >= 0 && e.GroupType is not null && e.GroupType != "rj45_poe" && InventoryRules.PortTypes.Contains(e.GroupType, StringComparer.Ordinal)
            && e.Prefix is { Length: <= 200 } prefix && prefix.EnumerateRunes().Count() <= 100
            && (prefix.Length == 0 || prefix == prefix.Trim() && !prefix.Any(char.IsControl)) && e.PortCount is >= 1 and <= 96;
    }

    private static bool ValidDetailSelection(string action, Guid resource, InventoryChangedEntity[] before, InventoryChangedEntity[] after)
    {
        string type = action["inventory.".Length..];
        bool create = type.EndsWith(".create", StringComparison.Ordinal) || type is "device.createFromCatalog" or "device.createFromPrivateTemplate" or "device.createFromSharedTemplate";
        bool delete = type.EndsWith(".delete", StringComparison.Ordinal);
        string kind = type.Split('.')[0];
        bool Side(InventoryChangedEntity[] rows, bool prior)
        {
            if (create && prior || delete && !prior) return rows.Length == 0;
            if (type == "devices.delete") return rows.Length > 0 && rows.All(e => e.Relation == "target" && e.Kind is "device" or "portGroup");
            string rootKind = type == "device.reorder" ? "rack" : kind;
            string relation = type == "rack.duplicate" && prior ? "source" : type is "device.reorder" or "device.editPortGroups" ? "scope" : "target";
            var roots = rows.Where(e => e.Kind == rootKind && e.Relation == relation).ToArray();
            if (roots.Length != 1 || (type != "rack.duplicate" || !prior) && roots[0].Id != resource) return false;
            if (type == "rack.duplicate" && prior && roots[0].Id == resource) return false;
            if (kind is "site" or "building" or "room" || type is "rack.create" or "rack.update" or "rack.assignRoom") return rows.Length == 1;
            if (type == "device.reorder") return rows.All(e => e == roots[0] || e.Kind == "device" && e.Relation == "target" && e.RackId == resource);
            string descendantRelation = type == "rack.duplicate" && prior ? "source" : "target";
            return rows.All(e => e == roots[0] || e.Relation == descendantRelation && (e.Kind == "portGroup" || rootKind == "rack" && e.Kind == "device" && e.RackId == roots[0].Id));
        }
        if (!Side(before, true) || !Side(after, false)) return false;
        if (!create && !delete && type != "rack.duplicate")
        {
            // Editing groups changes their set; other updates preserve the identities of the selected objects.
            if (type != "device.editPortGroups" && !before.Select(e => (e.Kind, e.Id, e.Relation)).ToHashSet().SetEquals(after.Select(e => (e.Kind, e.Id, e.Relation)))) return false;
            foreach (var old in before)
            {
                var next = after.SingleOrDefault(e => e.Kind == old.Kind && e.Id == old.Id && e.Relation == old.Relation);
                if (old.Kind == "device" && next is not null && old.DeviceKind != next.DeviceKind) return false;
                if (type == "device.update" && old.Kind == "device" && next is not null
                    && (old.ParentKind != next.ParentKind || old.ParentId != next.ParentId || old.RackId != next.RackId || old.RoomId != next.RoomId || old.SortOrder != next.SortOrder)) return false;
                if (type is "device.update" or "device.move" && old.Kind == "portGroup" && old != next) return false;
                if (type == "device.reorder" && (next is null || old != (next with { SortOrder = old.SortOrder }))) return false;
                if (type == "device.editPortGroups" && old.Kind == "device" && old != next) return false;
            }
        }
        if (type == "rack.duplicate" && before.Select(e => e.Id).Intersect(after.Select(e => e.Id)).Any()) return false;
        return true;
    }
}
