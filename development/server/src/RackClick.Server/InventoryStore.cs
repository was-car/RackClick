using System.Text.Json;
using System.Text.Json.Nodes;
using Npgsql;
using NpgsqlTypes;
using RackClick.Domain;
using static RackClick.Server.InventoryJson;

namespace RackClick.Server;

public sealed partial class InventoryStore(NpgsqlDataSource source)
{
    private static readonly JsonSerializerOptions Json = new(JsonSerializerDefaults.Web);
    private sealed record Change(Guid ResourceId, object? Before, object? After, object Result);
    private static NpgsqlCommand Cmd(NpgsqlConnection db, NpgsqlTransaction tx, string sql, params (string, object?)[] values)
    {
        var cmd = new NpgsqlCommand(sql, db, tx);
        foreach (var (key, value) in values)
            if (value is null) cmd.Parameters.AddWithValue(key, NpgsqlDbType.Unknown, DBNull.Value);
            else cmd.Parameters.AddWithValue(key, value);
        return cmd;
    }
    private static async Task Exec(NpgsqlConnection db, NpgsqlTransaction tx, string sql, CancellationToken ct, params (string, object?)[] values)
    {
        await using var cmd = Cmd(db, tx, sql, values);
        await cmd.ExecuteNonQueryAsync(ct);
    }
    private static async Task<JsonObject> Row(NpgsqlConnection db, NpgsqlTransaction tx, Actor actor, Guid customer,
        string table, Guid id, CancellationToken ct)
    {
        // Table names come exclusively from command dispatch, never request strings.
        await using var cmd = Cmd(db, tx, $"SELECT to_jsonb(t)::text FROM {table} t WHERE systemhaus_id=@house AND customer_id=@customer AND id=@id",
            ("house", actor.HouseId), ("customer", customer), ("id", id));
        return await cmd.ExecuteScalarAsync(ct) is string json ? JsonNode.Parse(json)!.AsObject() : throw new DomainError(404, "not_found");
    }
    private static async Task RequireRead(NpgsqlConnection db, NpgsqlTransaction tx, Actor actor, Guid customer, CancellationToken ct)
    {
        if (!await PostgresStore.Can(db, tx, actor, customer, Capabilities.InventoryRead, ct)) throw new DomainError(404, "not_found");
    }
    private static async Task<long> Revision(NpgsqlConnection db, NpgsqlTransaction tx, Actor actor, Guid customer, bool locking, CancellationToken ct)
    {
        await using var cmd = Cmd(db, tx, "SELECT revision FROM customer WHERE systemhaus_id=@house AND id=@customer" + (locking ? " FOR UPDATE" : ""),
            ("house", actor.HouseId), ("customer", customer));
        return await cmd.ExecuteScalarAsync(ct) is long revision ? revision : throw new DomainError(404, "not_found");
    }

    public async Task<(string Json, long Revision)> Read(Actor actor, Guid customer, CancellationToken ct)
        => await ReadAuthorizedSnapshot(actor, customer, null, (json, revision) => (json, revision), ct);

    private async Task<T> ReadAuthorizedSnapshot<T>(Actor actor, Guid customer, long? expected,
        Func<string, long, T> project, CancellationToken ct)
    {
        await using var db = await source.OpenConnectionAsync(ct);
        await using var tx = await db.BeginTransactionAsync(System.Data.IsolationLevel.ReadCommitted, ct);
        await RequireRead(db, tx, actor, customer, ct);
        long revision;
        // Writers lock customer before actor/session. Readers use that same order.
        await using (var cmd = Cmd(db, tx, "SELECT revision FROM customer WHERE systemhaus_id=@house AND id=@customer FOR SHARE",
            ("house", actor.HouseId), ("customer", customer)))
            revision = await cmd.ExecuteScalarAsync(ct) is long value ? value : throw new DomainError(404, "not_found");
        await PostgresStore.RequireCurrentSession(db, tx, actor, ct);
        await RequireRead(db, tx, actor, customer, ct);
        if (expected.HasValue) Revisions.Require(expected.Value, revision);
        string json = await Snapshot(db, tx, actor, customer, ct);
        T result = project(json, revision);
        await PostgresStore.RequireCurrentSession(db, tx, actor, ct);
        await RequireRead(db, tx, actor, customer, ct);
        await tx.CommitAsync(ct);
        return result;
    }

    private static async Task<string> Snapshot(NpgsqlConnection db, NpgsqlTransaction tx, Actor actor, Guid customer, CancellationToken ct)
    {
        static string Collection(string table, string fields, string order = "id", string? extra = null) =>
            $"(SELECT COALESCE(jsonb_agg(jsonb_build_object({fields}){(extra is null ? "" : " || " + extra)} ORDER BY {order}), '[]'::jsonb) FROM {table} WHERE systemhaus_id=@house AND customer_id=@customer)";
        string sql = "SELECT jsonb_build_object('customerId',id,'revision',revision," +
            "'sites'," + Collection("inventory_site", "'id',id,'name',name,'properties',properties") + "," +
            "'buildings'," + Collection("inventory_building", "'id',id,'siteId',site_id,'name',name,'properties',properties") + "," +
            "'rooms'," + Collection("inventory_room", "'id',id,'buildingId',building_id,'name',name,'properties',properties") + "," +
            "'racks'," + Collection("inventory_rack", "'id',id,'roomId',room_id,'name',name,'location',location,'sizeU',size_u,'properties',properties", "id", "CASE WHEN hardware_profile_key IS NULL THEN '{}'::jsonb ELSE jsonb_build_object('hardwareProfileKey',hardware_profile_key) END") + "," +
            "'devices'," + Collection("inventory_device", "'id',id,'kind',kind,'rackId',rack_id,'roomId',room_id,'name',name,'sizeU',size_u,'sortOrder',sort_order,'poeBudget',poe_budget,'hardwareProfileKey',hardware_profile_key,'mountParentId',mount_parent_id,'mountSlotKey',mount_slot_key,'properties',properties", "sort_order,id") + "," +
            "'portGroups'," + Collection("inventory_port_group", "'id',id,'deviceId',device_id,'type',type,'name',name,'prefix',prefix,'sortOrder',sort_order", "sort_order,id") + "," +
            "'ports'," + Collection("inventory_port", "'id',id,'deviceId',device_id,'groupId',group_id,'type',type,'gn',gn,'sortOrder',sort_order,'label',label,'status',status,'poe',poe,'watts',watts,'color',color,'face',face,'powerRole',power_role,'properties',properties", "sort_order,id") + "," +
            "'connections',(SELECT COALESCE(jsonb_agg(jsonb_build_object('id',c.id,'fromPortId',a.port_id,'toPortId',b.port_id," +
            "'note',c.note,'color',c.color,'patch',c.patch,'createdAt',c.created_at,'properties',c.properties) ORDER BY c.id),'[]'::jsonb) " +
            "FROM inventory_connection c JOIN inventory_connection_endpoint a ON a.connection_id=c.id AND a.ordinal=0 " +
            "JOIN inventory_connection_endpoint b ON b.connection_id=c.id AND b.ordinal=1 WHERE c.systemhaus_id=@house AND c.customer_id=@customer))::text " +
            "FROM customer WHERE systemhaus_id=@house AND id=@customer";
        await using var cmd = Cmd(db, tx, sql, ("house", actor.HouseId), ("customer", customer));
        return (string)(await cmd.ExecuteScalarAsync(ct))!;
    }

    public async Task<string> Execute(Actor actor, Guid customer, InventoryCommandRequest request, long expected, Guid requestId, CancellationToken ct)
    {
        var payload = Object(request.Payload);
        string type = request.Type ?? throw new DomainError(422, "command_required");
        if (requestId == Guid.Empty) throw new DomainError(422, "request_id_invalid");
        string requestHash = RequestDigest(customer, request, expected);
        await using var db = await source.OpenConnectionAsync(ct);
        await using var tx = await db.BeginTransactionAsync(ct);
        try
        {
            // Same lock protocol as foundation writes; different actors/keys/customers need no global row lock.
            await PostgresStore.LockOperation(db, tx, actor, requestId, ct);
            long revision = await Revision(db, tx, actor, customer, true, ct);
            await PostgresStore.RequireCurrentSession(db, tx, actor, ct);
            await RequireRead(db, tx, actor, customer, ct);
            string capability = type.EndsWith(".delete", StringComparison.Ordinal) ? Capabilities.InventoryDelete : Capabilities.InventoryEdit;
            if (!await PostgresStore.Can(db, tx, actor, customer, capability, ct)) throw new DomainError(403, "forbidden");
            await OperationCancellation.EnsureNotCanceled(db, tx, actor, requestId, requestHash, ct);
            await using (var replay = Cmd(db, tx, "SELECT request_hash,result_json::text FROM operation WHERE systemhaus_id=@house AND actor_id=@actor AND request_id=@request",
                ("house", actor.HouseId), ("actor", actor.Id), ("request", requestId)))
            await using (var row = await replay.ExecuteReaderAsync(ct))
                if (await row.ReadAsync(ct))
                {
                    if (row.GetString(0) != requestHash) throw new DomainError(409, "request_id_reused");
                    return row.GetString(1);
                }
            Revisions.Require(expected, revision);
            Guid operationId = Guid.NewGuid();
            var detailsBefore = await CaptureChangeDetails(db, tx, actor, customer, type, payload, null, true, ct);
            Change change = await Apply(db, tx, actor, customer, type, payload, revision, operationId, ct);
            var detailsAfter = await CaptureChangeDetails(db, tx, actor, customer, type, payload, change.ResourceId, false, ct);
            // Oversized descriptions must be unavailable as a pair, not misleadingly partial.
            if (detailsBefore is { Complete: false } || detailsAfter is { Complete: false })
                detailsBefore = detailsAfter = new DetailCapture(false, []);
            long next = checked(revision + 1);
            string result = JsonSerializer.Serialize(new { customerId = customer, revision = next, requestId, operationId, result = change.Result }, Json);
            await Exec(db, tx, "UPDATE customer SET revision=@next WHERE systemhaus_id=@house AND id=@customer", ct,
                ("next", next), ("house", actor.HouseId), ("customer", customer));
            await Exec(db, tx, """
                INSERT INTO audit_event(id,systemhaus_id,actor_id,request_id,action,resource_id,before_json,after_json)
                VALUES(@id,@house,@actor,@request,@action,@resource,CAST(@before AS jsonb),CAST(@after AS jsonb))
                """, ct, ("id", operationId), ("house", actor.HouseId), ("actor", actor.Id), ("request", requestId),
                ("action", "inventory." + type), ("resource", change.ResourceId),
                ("before", JsonSerializer.Serialize(new { customerId = customer, revision, data = change.Before,
                    changeDetails = DetailAudit(detailsBefore, actor, customer, type, change.ResourceId) }, Json)),
                ("after", JsonSerializer.Serialize(new { customerId = customer, revision = next, data = change.After,
                    changeDetails = DetailAudit(detailsAfter, actor, customer, type, change.ResourceId) }, Json)));
            await Exec(db, tx, "INSERT INTO operation(systemhaus_id,actor_id,request_id,request_hash,result_json) VALUES(@house,@actor,@request,@hash,CAST(@result AS jsonb))", ct,
                ("house", actor.HouseId), ("actor", actor.Id), ("request", requestId), ("hash", requestHash), ("result", result));
            if (type == "operations.compensate") await RequireCompensationAuthorization(db, tx, actor, customer, ct);
            if (type == "device.createFromCatalog") await RequireCatalogCreateAuthorization(db, tx, actor, customer, ct);
            if (type == "device.createFromPrivateTemplate") await PrivateDeviceTemplates.Authorize(db, tx, actor, customer, true, ct);
            if (type == "device.createFromSharedTemplate") await SharedDeviceTemplates.AuthorizeCreation(db, tx, actor, customer, ct);
            await PostgresStore.RequireCurrentSession(db, tx, actor, ct);
            await tx.CommitAsync(ct);
            return result;
        }
        catch (PostgresException e) when (e.SqlState is "23503" or "23505" or "23514")
        {
            throw new DomainError(409, e.ConstraintName == "operation_pkey" ? "request_id_reused" : "inventory_conflict");
        }
    }

    internal static string RequestDigest(Guid customer, InventoryCommandRequest request, long expected)
        => Secrets.Digest(InventoryJson.Canonical(new JsonObject
            { ["type"] = request.Type, ["customerId"] = customer, ["payload"] = Object(request.Payload), ["expected"] = expected }));

    public async Task<string> Operation(Actor actor, Guid customer, Guid requestId, CancellationToken ct)
    {
        await using var db = await source.OpenConnectionAsync(ct);
        await using var tx = await db.BeginTransactionAsync(ct);
        await PostgresStore.LockOperation(db, tx, actor, requestId, ct);
        await PostgresStore.RequireCurrentSession(db, tx, actor, ct);
        await RequireRead(db, tx, actor, customer, ct);
        long revision = await Revision(db, tx, actor, customer, false, ct);
        string? cancelled = await OperationCancellation.Read(db, tx, actor, customer, requestId, ct);
        if (cancelled is not null) return cancelled;
        await using var cmd = Cmd(db, tx, "SELECT result_json::text FROM operation WHERE systemhaus_id=@house AND actor_id=@actor AND request_id=@request",
            ("house", actor.HouseId), ("actor", actor.Id), ("request", requestId));
        var operation = await cmd.ExecuteScalarAsync(ct) is string json ? JsonNode.Parse(json) : null;
        if (operation is not null && operation["customerId"]?.GetValue<Guid>() != customer) throw new DomainError(404, "not_found");
        return new JsonObject { ["state"] = operation is null ? "notRecorded" : "committed", ["customerId"] = customer,
            ["requestId"] = requestId, ["revision"] = revision, ["operation"] = operation }.ToJsonString();
    }

    private static Task<Change> Apply(NpgsqlConnection db, NpgsqlTransaction tx, Actor actor, Guid customer, string type,
        JsonObject payload, long revision, Guid operationId, CancellationToken ct) => type switch
    {
        "site.create" or "site.update" or "site.delete" or "building.create" or "building.update" or "building.delete" or
        "room.create" or "room.update" or "room.delete" or "rack.create" or "rack.update" or "rack.assignRoom"
            => Hierarchy(db, tx, actor, customer, type, payload, ct),
        "device.create" or "device.update" or "device.move" or "device.reorder" => Device(db, tx, actor, customer, type, payload, ct),
        "rack.createHardware" => CreateRackHardware(db, tx, actor, customer, payload, ct),
        "device.createHardware" => CreateHardware(db, tx, actor, customer, payload, ct),
        "device.createFromCatalog" => CreateFromCatalog(db, tx, actor, customer, payload, ct),
        "device.createFromPrivateTemplate" => CreateFromPrivateTemplate(db, tx, actor, customer, payload, ct),
        "device.createFromSharedTemplate" => CreateFromSharedTemplate(db, tx, actor, customer, payload, ct),
        "ports.update" => UpdatePorts(db, tx, actor, customer, payload, ct),
        "operations.compensate" => CompensatePorts(db, tx, actor, customer, payload, revision, ct),
        "connections.create" or "connections.createBatch" or "connections.update" or "connections.disconnect" or "connections.reconnect"
            => Connections(db, tx, actor, customer, type, payload, ct),
        "rack.delete" or "device.delete" or "devices.delete" => DeleteInventory(db, tx, actor, customer, type, payload, revision, operationId, ct),
        "device.editPortGroups" => EditPortGroups(db, tx, actor, customer, payload, revision, ct),
        "rack.duplicate" => DuplicateRack(db, tx, actor, customer, payload, ct),
        _ => throw new DomainError(422, "command_unknown")
    };

    private static async Task<Change> Hierarchy(NpgsqlConnection db, NpgsqlTransaction tx, Actor actor, Guid customer,
        string type, JsonObject payload, CancellationToken ct)
    {
        string entity = type.Split('.')[0], action = type.Split('.')[1], table = "inventory_" + entity;
        Guid id = action == "create" ? Guid.NewGuid() : Id(payload, "id");
        JsonObject? before = action == "create" ? null : await Row(db, tx, actor, customer, table, id, ct);
        if (action == "delete")
        {
            await Exec(db, tx, $"DELETE FROM {table} WHERE systemhaus_id=@house AND customer_id=@customer AND id=@id", ct,
                ("house", actor.HouseId), ("customer", customer), ("id", id));
            return new(id, before, null, new { resourceId = id, removedIds = new[] { id } });
        }
        if (entity=="rack" && payload.Any(f=>f.Key is "hardwareProfileKey" or "profileKey" or "profileVersion")) throw new DomainError(422,"hardware_command_required");
        if (entity=="rack" && before?["hardware_profile_key"] is not null &&
            ((payload.ContainsKey("sizeU") && Integer(payload,"sizeU",1,1000)!=Integer(before,"size_u",1,1000)) ||
             payload["properties"] is JsonObject rackPatch && rackPatch.Any(f=>f.Key is not ("notes" or "color"))))
            throw new DomainError(422,"hardware_metadata_immutable");
        string name = payload.ContainsKey("name") || before is null ? Names.Validate(String(payload, "name")) : String(before, "name");
        string properties = Properties(payload, before?["properties"] as JsonObject);
        string? parentKey = entity switch { "building" => "siteId", "room" => "buildingId", "rack" => "roomId", _ => null };
        string? parentColumn = entity switch { "building" => "site_id", "room" => "building_id", "rack" => "room_id", _ => null };
        Guid? parent = parentKey is null ? null : payload.ContainsKey(parentKey) ? OptionalId(payload, parentKey) : before is null ? null : OptionalId(before, parentColumn!);
        if (entity is "building" or "room" && parent is null) throw new DomainError(422, "parent_required");
        if (parent is not null)
            await Row(db, tx, actor, customer, entity switch { "building" => "inventory_site", "room" => "inventory_building", _ => "inventory_room" }, parent.Value, ct);
        int size = entity == "rack" ? Integer(payload, "sizeU", 1, 1000, before is null ? null : Integer(before, "size_u", 1, 1000)) : 0;
        string location = entity == "rack" ? (payload.ContainsKey("location") ? Text(payload, "location") : before is null ? "" : String(before, "location")) : "";
        if (entity == "rack" && before is not null)
        {
            await using var used = Cmd(db, tx, "SELECT COALESCE(sum(size_u),0)::integer FROM inventory_device WHERE systemhaus_id=@house AND customer_id=@customer AND rack_id=@id",
                ("house", actor.HouseId), ("customer", customer), ("id", id));
            InventoryRules.RequireCapacity(size, (int)(await used.ExecuteScalarAsync(ct))!, 0);
        }
        var args = new (string, object?)[] { ("id", id), ("house", actor.HouseId), ("customer", customer), ("name", name),
            ("properties", properties), ("parent", parent), ("size", size), ("location", location) };
        string parentInsert = parentColumn is null ? "" : $",{parentColumn}";
        string extraInsert = entity == "rack" ? ",size_u,location" : "";
        string sql = action == "create"
            ? $"INSERT INTO {table}(id,systemhaus_id,customer_id,name,properties{parentInsert}{extraInsert}) VALUES(@id,@house,@customer,@name,CAST(@properties AS jsonb){(parentColumn is null ? "" : ",@parent")}{(entity == "rack" ? ",@size,@location" : "")})"
            : $"UPDATE {table} SET name=@name,properties=CAST(@properties AS jsonb){(parentColumn is null ? "" : $",{parentColumn}=@parent")}{(entity == "rack" ? ",size_u=@size,location=@location" : "")} WHERE systemhaus_id=@house AND customer_id=@customer AND id=@id";
        await Exec(db, tx, sql, ct, args);
        var after = await Row(db, tx, actor, customer, table, id, ct);
        return new(id, before, after, new { resourceId = id });
    }
}
