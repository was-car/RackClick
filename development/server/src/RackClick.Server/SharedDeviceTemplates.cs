using System.Globalization;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using System.Text.Json.Serialization;
using Npgsql;
using RackClick.Domain;
using static RackClick.Server.InventoryJson;

namespace RackClick.Server;

public sealed record SharedTemplateMetadata(Guid Id, string Name, bool Active, int DefinitionVersion,
    string DefinitionSha256, string Kind, int? SizeU, int GroupCount, int PortCount, Guid PublishedById, string PublishedByName);
public sealed record SharedTemplateDetail(Guid Id, string Name, bool Active, int DefinitionVersion,
    string DefinitionSha256, string Kind, int? SizeU, int GroupCount, int PortCount, Guid PublishedById, string PublishedByName,
    int DefinitionByteLength, string DefinitionBase64);
public sealed record SharedTemplatesSnapshot(string Kind, Guid CustomerId, long Revision, IReadOnlyList<SharedTemplateMetadata> Templates);
public sealed record SharedTemplateSnapshot(string Kind, Guid CustomerId, long Revision, SharedTemplateDetail Template);
public sealed record SharedTemplateResult(string Kind, Guid CustomerId, Guid ActorId, long Revision,
    Guid RequestId, Guid OperationId, PrivateTemplateChange Result);
public sealed record SharedTemplateStatus(string State, Guid CustomerId, Guid ActorId, long Revision,
    Guid RequestId, SharedTemplateResult? Operation);

/// <summary>Immutable customer copies. Private source IDs exist only in the publisher's hash input.</summary>
public sealed class SharedDeviceTemplates(NpgsqlDataSource source)
{
    public const long MaximumRevision = 9007199254740991;
    public const int MaximumActive = 128;
    private const string Kind = "sharedTemplates";
    private static readonly JsonSerializerOptions Json = new(JsonSerializerDefaults.Web)
        { UnmappedMemberHandling = JsonUnmappedMemberHandling.Disallow };
    private sealed record Intent(string Type, Guid? PrivateTemplateId, int? DefinitionVersion, string? DefinitionSha256, string? Name, Guid? TemplateId);
    private sealed record Terminal(Guid CustomerId, string Hash, string State, string Result);
    private sealed record Stored(SharedTemplateMetadata Metadata, PrivateTemplateDefinition Definition, string DefinitionJson);

    public static string ETag(long revision) => $"\"shared-templates-{revision.ToString(CultureInfo.InvariantCulture)}\"";
    public static long ParseRevision(string? etag)
    {
        if (string.IsNullOrWhiteSpace(etag)) throw new DomainError(428, "revision_required");
        const string prefix = "\"shared-templates-";
        if (!etag.StartsWith(prefix, StringComparison.Ordinal) || !etag.EndsWith('"')
            || !long.TryParse(etag[prefix.Length..^1], NumberStyles.None, CultureInfo.InvariantCulture, out long value)
            || value < 0 || value > MaximumRevision || ETag(value) != etag) throw new DomainError(422, "revision_invalid");
        return value;
    }
    private static NpgsqlCommand Cmd(NpgsqlConnection db, NpgsqlTransaction tx, string sql, params (string, object)[] values)
    {
        var command = new NpgsqlCommand(sql, db, tx);
        foreach (var (key, value) in values) command.Parameters.AddWithValue(key, value);
        return command;
    }
    private static async Task<int> Exec(NpgsqlConnection db, NpgsqlTransaction tx, string sql, CancellationToken ct, params (string, object)[] values)
    {
        await using var command = Cmd(db, tx, sql, values); return await command.ExecuteNonQueryAsync(ct);
    }
    private static void Keys(JsonObject value, params string[] keys)
    {
        if (value.Count != keys.Length || keys.Any(k => !value.ContainsKey(k))) throw new DomainError(422, "request_invalid");
    }
    private static Intent ParseIntent(JsonElement input)
    {
        var value = Object(input); string type = String(value, "type");
        if (type == "publish")
        {
            Keys(value, "type", "privateTemplateId", "definitionVersion", "definitionSha256", "name");
            string hash = String(value, "definitionSha256");
            if (hash.Length != 64 || hash.Any(c => c is not (>= '0' and <= '9' or >= 'a' and <= 'f')))
                throw new DomainError(422, "request_invalid");
            return new(type, Id(value, "privateTemplateId"), Integer(value, "definitionVersion", 1, 1), hash,
                Names.Validate(String(value, "name")), null);
        }
        if (type == "deactivate")
        {
            Keys(value, "type", "templateId"); return new(type, null, null, null, null, Id(value, "templateId"));
        }
        throw new DomainError(422, "request_invalid");
    }
    private static async Task Authorize(NpgsqlConnection db, NpgsqlTransaction tx, Actor actor, Guid customer, bool publish, CancellationToken ct)
    {
        await PrivateDeviceTemplates.Authorize(db, tx, actor, customer, false, ct);
        if (publish && !await PostgresStore.Can(db, tx, actor, customer, Capabilities.TemplatesPublish, ct))
            throw new DomainError(403, "forbidden");
    }
    internal static async Task AuthorizeCreation(NpgsqlConnection db, NpgsqlTransaction tx, Actor actor, Guid customer, CancellationToken ct)
        => await PrivateDeviceTemplates.Authorize(db, tx, actor, customer, true, ct);
    private static async Task LockCustomer(NpgsqlConnection db, NpgsqlTransaction tx, Actor actor, Guid customer, CancellationToken ct)
    {
        await using var command = Cmd(db, tx, "SELECT id FROM customer WHERE systemhaus_id=@house AND id=@customer FOR SHARE",
            ("house", actor.HouseId), ("customer", customer));
        if (await command.ExecuteScalarAsync(ct) is not Guid) throw new DomainError(404, "not_found");
    }
    private static Task<int> LockAggregate(NpgsqlConnection db, NpgsqlTransaction tx, Actor actor, Guid customer, bool shared, CancellationToken ct)
        => Exec(db, tx, shared ? "SELECT pg_advisory_xact_lock_shared(hashtextextended(@key,0))" : "SELECT pg_advisory_xact_lock(hashtextextended(@key,0))", ct,
            ("key", $"RackClick/customer-device-templates/{actor.HouseId:D}/{customer:D}"));
    private static Task<int> LockRequest(NpgsqlConnection db, NpgsqlTransaction tx, Actor actor, Guid requestId, CancellationToken ct)
        => Exec(db, tx, "SELECT pg_advisory_xact_lock(hashtextextended(@key,0))", ct,
            ("key", $"RackClick/customer-device-template-operation/{actor.HouseId:D}/{actor.Id:D}/{requestId:D}"));
    private static async Task<long> Revision(NpgsqlConnection db, NpgsqlTransaction tx, Actor actor, Guid customer, CancellationToken ct)
    {
        await using var command = Cmd(db, tx, "SELECT revision FROM customer_device_templates WHERE systemhaus_id=@house AND customer_id=@customer",
            ("house", actor.HouseId), ("customer", customer));
        return await command.ExecuteScalarAsync(ct) is long value ? value : 0;
    }
    private static async Task<Terminal?> Find(NpgsqlConnection db, NpgsqlTransaction tx, Actor actor, Guid requestId, CancellationToken ct)
    {
        await using var command = Cmd(db, tx, "SELECT customer_id,request_hash,state,result_json::text FROM customer_device_template_operation WHERE systemhaus_id=@house AND actor_id=@actor AND request_id=@request",
            ("house", actor.HouseId), ("actor", actor.Id), ("request", requestId));
        await using var rows = await command.ExecuteReaderAsync(ct);
        return await rows.ReadAsync(ct) ? new(rows.GetGuid(0), rows.GetString(1), rows.GetString(2), rows.GetString(3)) : null;
    }
    private static SharedTemplateResult Committed(Terminal terminal, Actor actor, Guid customer, Guid requestId)
    {
        try
        {
            var result = JsonSerializer.Deserialize<SharedTemplateResult>(terminal.Result, Json);
            if (result is null || result.Kind != Kind || result.CustomerId != customer || result.ActorId != actor.Id
                || result.RequestId != requestId || result.OperationId == Guid.Empty || result.Revision < 0
                || result.Revision > MaximumRevision || result.Result is null) throw new DomainError(409, "templates_conflict");
            return result;
        }
        catch (JsonException) { throw new DomainError(409, "templates_conflict"); }
    }
    private static SharedTemplateStatus Outcome(Terminal? terminal, Actor actor, Guid customer, Guid requestId, long revision)
    {
        if (terminal is not null && terminal.CustomerId != customer) throw new DomainError(404, "not_found");
        return new(terminal?.State ?? "notRecorded", customer, actor.Id, revision, requestId,
            terminal?.State == "committed" ? Committed(terminal, actor, customer, requestId) : null);
    }
    private static async Task<Stored> Load(NpgsqlConnection db, NpgsqlTransaction tx, Actor actor, Guid customer, Guid id, CancellationToken ct)
    {
        await using var command = Cmd(db, tx, "SELECT name,active,definition_version,definition_sha256,definition_json,published_by_id,published_by_name FROM customer_device_template WHERE systemhaus_id=@house AND customer_id=@customer AND id=@id",
            ("house", actor.HouseId), ("customer", customer), ("id", id));
        await using var rows = await command.ExecuteReaderAsync(ct);
        if (!await rows.ReadAsync(ct)) throw new DomainError(404, "not_found");
        string raw = rows.GetString(4), hash = rows.GetString(3);
        var definition = PrivateDeviceTemplates.ValidateSharedDefinition(raw, rows.GetInt32(2), hash);
        return new(new(id, rows.GetString(0), rows.GetBoolean(1), 1, hash, definition.Kind, definition.SizeU,
            definition.PortGroups.Count, definition.PortGroups.Sum(g => g.Ports.Count), rows.GetGuid(5), rows.GetString(6)), definition, raw);
    }
    private static SharedTemplateDetail Detail(Stored value)
    {
        var m = value.Metadata; byte[] bytes = Encoding.UTF8.GetBytes(value.DefinitionJson);
        return new(m.Id, m.Name, m.Active, m.DefinitionVersion, m.DefinitionSha256, m.Kind, m.SizeU, m.GroupCount, m.PortCount,
            m.PublishedById, m.PublishedByName, bytes.Length, Convert.ToBase64String(bytes));
    }
    internal static async Task<PrivateTemplateDefinition> ForCreation(NpgsqlConnection db, NpgsqlTransaction tx, Actor actor,
        Guid customer, Guid templateId, int version, string hash, CancellationToken ct)
    {
        // Inventory owns customer UPDATE. Never acquire the private aggregate from this path.
        await LockAggregate(db, tx, actor, customer, true, ct); await AuthorizeCreation(db, tx, actor, customer, ct);
        var stored = await Load(db, tx, actor, customer, templateId, ct);
        if (!stored.Metadata.Active) throw new DomainError(409, "template_inactive");
        if (version != stored.Metadata.DefinitionVersion || hash != stored.Metadata.DefinitionSha256)
            throw new DomainError(409, "template_changed");
        return stored.Definition;
    }
    public async Task<SharedTemplatesSnapshot> Read(Actor actor, Guid customer, IQueryCollection query, CancellationToken ct)
    {
        await using var db = await source.OpenConnectionAsync(ct); await using var tx = await db.BeginTransactionAsync(ct);
        await LockCustomer(db, tx, actor, customer, ct); await Authorize(db, tx, actor, customer, false, ct);
        if (query.Count != 0) throw new DomainError(422, "request_invalid");
        await LockAggregate(db, tx, actor, customer, true, ct); await Authorize(db, tx, actor, customer, false, ct);
        long revision = await Revision(db, tx, actor, customer, ct); var ids = new List<Guid>();
        await using (var command = Cmd(db, tx, "SELECT id FROM customer_device_template WHERE systemhaus_id=@house AND customer_id=@customer AND active ORDER BY id", ("house", actor.HouseId), ("customer", customer)))
        await using (var rows = await command.ExecuteReaderAsync(ct)) while (await rows.ReadAsync(ct)) ids.Add(rows.GetGuid(0));
        if (ids.Count > MaximumActive) throw new DomainError(409, "templates_conflict");
        var items = new List<SharedTemplateMetadata>();
        foreach (Guid id in ids) items.Add((await Load(db, tx, actor, customer, id, ct)).Metadata);
        await Authorize(db, tx, actor, customer, false, ct); await tx.CommitAsync(ct); return new(Kind, customer, revision, items);
    }
    public async Task<SharedTemplateSnapshot> ReadOne(Actor actor, Guid customer, Guid templateId, IQueryCollection query, CancellationToken ct)
    {
        if (templateId == Guid.Empty) throw new DomainError(422, "object_id_invalid");
        await using var db = await source.OpenConnectionAsync(ct); await using var tx = await db.BeginTransactionAsync(ct);
        await LockCustomer(db, tx, actor, customer, ct); await Authorize(db, tx, actor, customer, false, ct);
        if (query.Count != 0) throw new DomainError(422, "request_invalid");
        await LockAggregate(db, tx, actor, customer, true, ct); await Authorize(db, tx, actor, customer, false, ct);
        var result = new SharedTemplateSnapshot(Kind, customer, await Revision(db, tx, actor, customer, ct), Detail(await Load(db, tx, actor, customer, templateId, ct)));
        await Authorize(db, tx, actor, customer, false, ct); await tx.CommitAsync(ct); return result;
    }
    public async Task<SharedTemplateStatus> Status(Actor actor, Guid customer, Guid requestId, IQueryCollection query, CancellationToken ct)
    {
        if (requestId == Guid.Empty) throw new DomainError(422, "request_id_invalid");
        await using var db = await source.OpenConnectionAsync(ct); await using var tx = await db.BeginTransactionAsync(ct);
        await LockRequest(db, tx, actor, requestId, ct); await LockCustomer(db, tx, actor, customer, ct);
        await Authorize(db, tx, actor, customer, true, ct);
        if (query.Count != 0) throw new DomainError(422, "request_invalid");
        await LockAggregate(db, tx, actor, customer, true, ct); await Authorize(db, tx, actor, customer, true, ct);
        var result = Outcome(await Find(db, tx, actor, requestId, ct), actor, customer, requestId, await Revision(db, tx, actor, customer, ct));
        await Authorize(db, tx, actor, customer, true, ct); await tx.CommitAsync(ct); return result;
    }
    public async Task<SharedTemplateResult> Set(Actor actor, Guid customer, JsonElement input, long expected, Guid requestId, IQueryCollection query, CancellationToken ct)
        => (await Execute(actor, customer, input, expected, requestId, query, false, ct)).Operation ?? throw new DomainError(409, "operation_cancelled");
    public Task<SharedTemplateStatus> Cancel(Actor actor, Guid customer, JsonElement input, long expected, Guid requestId, IQueryCollection query, CancellationToken ct)
        => Execute(actor, customer, input, expected, requestId, query, true, ct);

    private async Task<SharedTemplateStatus> Execute(Actor actor, Guid customer, JsonElement input, long expected, Guid requestId,
        IQueryCollection query, bool cancel, CancellationToken ct)
    {
        var intent = ParseIntent(input);
        if (requestId == Guid.Empty) throw new DomainError(422, "request_id_invalid");
        if (expected < 0 || expected > MaximumRevision) throw new DomainError(422, "revision_invalid");
        string digest = Secrets.Digest(Canonical(new JsonObject { ["family"] = Kind, ["houseId"] = actor.HouseId,
            ["actorId"] = actor.Id, ["customerId"] = customer, ["intent"] = JsonSerializer.SerializeToNode(intent, Json), ["expected"] = expected }));
        await using var db = await source.OpenConnectionAsync(ct); await using var tx = await db.BeginTransactionAsync(ct);
        try
        {
            await LockRequest(db, tx, actor, requestId, ct); await LockCustomer(db, tx, actor, customer, ct);
            await Authorize(db, tx, actor, customer, true, ct);
            if (query.Count != 0) throw new DomainError(422, "request_invalid");
            await LockAggregate(db, tx, actor, customer, false, ct); await Authorize(db, tx, actor, customer, true, ct);
            long revision = await Revision(db, tx, actor, customer, ct); var prior = await Find(db, tx, actor, requestId, ct);
            if (prior is not null)
            {
                if (prior.CustomerId != customer || prior.Hash != digest) throw new DomainError(409, "request_id_reused");
                if (!cancel && prior.State == "cancelled") throw new DomainError(409, "operation_cancelled");
                var replay = Outcome(prior, actor, customer, requestId, revision);
                await Authorize(db, tx, actor, customer, true, ct); await tx.CommitAsync(ct); return replay;
            }
            Guid operationId = Guid.NewGuid(), resource = customer; SharedTemplateResult? committed = null;
            string before, after, stored;
            if (cancel)
            {
                before = JsonSerializer.Serialize(new { customerId = customer, revision }, Json);
                after = JsonSerializer.Serialize(new { customerId = customer, revision, state = "cancelled", type = intent.Type, expectedSharedRevision = expected }, Json);
                stored = JsonSerializer.Serialize(new { kind = Kind, state = "cancelled", customerId = customer, actorId = actor.Id, requestId, operationId, revision }, Json);
            }
            else
            {
                Revisions.Require(expected, revision); bool changed; Stored value;
                if (intent.Type == "publish")
                {
                    if (revision == MaximumRevision) throw new DomainError(409, "templates_revision_exhausted");
                    await using var count = Cmd(db, tx, "SELECT count(*) FROM customer_device_template WHERE systemhaus_id=@house AND customer_id=@customer AND active", ("house", actor.HouseId), ("customer", customer));
                    if ((long)(await count.ExecuteScalarAsync(ct))! >= MaximumActive) throw new DomainError(409, "templates_limit");
                    var original = await PrivateDeviceTemplates.ForPublication(db, tx, actor, customer, intent.PrivateTemplateId!.Value,
                        intent.DefinitionVersion!.Value, intent.DefinitionSha256!, ct);
                    // Validate without serializing: persist precisely the previously verified UTF-8 text.
                    _ = PrivateDeviceTemplates.ValidateSharedDefinition(original.DefinitionJson, 1, original.Metadata.DefinitionSha256);
                    await Exec(db, tx, "INSERT INTO customer_device_templates(systemhaus_id,customer_id) VALUES(@house,@customer) ON CONFLICT DO NOTHING", ct,
                        ("house", actor.HouseId), ("customer", customer));
                    Guid id = Guid.NewGuid();
                    await Exec(db, tx, "INSERT INTO customer_device_template(id,systemhaus_id,customer_id,published_by_id,published_by_name,name,definition_version,definition_sha256,definition_json) VALUES(@id,@house,@customer,@actor,@author,@name,1,@hash,@definition)", ct,
                        ("id", id), ("house", actor.HouseId), ("customer", customer), ("actor", actor.Id), ("author", actor.UserName),
                        ("name", intent.Name!), ("hash", original.Metadata.DefinitionSha256), ("definition", original.DefinitionJson));
                    value = await Load(db, tx, actor, customer, id, ct); changed = true;
                    before = JsonSerializer.Serialize(new { customerId = customer, revision, template = (object?)null }, Json);
                }
                else
                {
                    value = await Load(db, tx, actor, customer, intent.TemplateId!.Value, ct); changed = value.Metadata.Active;
                    before = JsonSerializer.Serialize(new { customerId = customer, revision, template = value.Metadata }, Json);
                    if (changed)
                    {
                        if (revision == MaximumRevision) throw new DomainError(409, "templates_revision_exhausted");
                        await Exec(db, tx, "UPDATE customer_device_template SET active=false WHERE systemhaus_id=@house AND customer_id=@customer AND id=@id", ct,
                            ("house", actor.HouseId), ("customer", customer), ("id", value.Metadata.Id));
                        value = value with { Metadata = value.Metadata with { Active = false } };
                    }
                }
                if (changed)
                {
                    if (await Exec(db, tx, "UPDATE customer_device_templates SET revision=@next WHERE systemhaus_id=@house AND customer_id=@customer AND revision=@before", ct,
                        ("next", revision + 1), ("house", actor.HouseId), ("customer", customer), ("before", revision)) != 1)
                        throw new DomainError(409, "templates_conflict");
                    revision++;
                }
                var m = value.Metadata; resource = m.Id;
                committed = new(Kind, customer, actor.Id, revision, requestId, operationId,
                    new(intent.Type, m.Id, m.Name, m.Active, changed, m.DefinitionVersion, m.DefinitionSha256));
                stored = JsonSerializer.Serialize(committed, Json);
                after = JsonSerializer.Serialize(new { customerId = customer, revision, template = m, changed }, Json);
            }
            string state = cancel ? "cancelled" : "committed";
            await Exec(db, tx, "INSERT INTO audit_event(id,systemhaus_id,actor_id,request_id,action,resource_id,before_json,after_json) VALUES(@id,@house,@actor,@request,@action,@resource,CAST(@before AS jsonb),CAST(@after AS jsonb))", ct,
                ("id", operationId), ("house", actor.HouseId), ("actor", actor.Id), ("request", requestId), ("resource", resource),
                ("action", "customer.deviceTemplate." + intent.Type + (cancel ? ".cancel" : "")), ("before", before), ("after", after));
            await Exec(db, tx, "INSERT INTO customer_device_template_operation(systemhaus_id,actor_id,customer_id,request_id,request_hash,state,operation_id,revision,result_json) VALUES(@house,@actor,@customer,@request,@hash,@state,@operation,@revision,CAST(@result AS jsonb))", ct,
                ("house", actor.HouseId), ("actor", actor.Id), ("customer", customer), ("request", requestId), ("hash", digest), ("state", state), ("operation", operationId), ("revision", revision), ("result", stored));
            await Authorize(db, tx, actor, customer, true, ct); await tx.CommitAsync(ct);
            return new(state, customer, actor.Id, revision, requestId, committed);
        }
        catch (PostgresException e) when (e.SqlState is "23503" or "23505" or "23514") { throw new DomainError(409, "templates_conflict"); }
    }
}
