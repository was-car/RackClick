using System.Globalization;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using System.Text.Json.Serialization;
using System.Text.RegularExpressions;
using Npgsql;
using RackClick.Domain;
using static RackClick.Server.InventoryJson;

namespace RackClick.Server;

public sealed record PrivateTemplatePort(int Gn, int SortOrder, string Type, string Label, bool Poe,
    string? Color, string Face, string PowerRole);
public sealed record PrivateTemplateGroup(string Key, string Type, string Name, string Prefix, int SortOrder,
    IReadOnlyList<PrivateTemplatePort> Ports);
public sealed record PrivateTemplateDefinition(string Kind, int? SizeU, decimal? PoeBudget, string Icon, string Color, string VisualFamily,
    IReadOnlyList<PrivateTemplateGroup> PortGroups);
public sealed record PrivateTemplateMetadata(Guid Id, string Name, bool Active, int DefinitionVersion,
    string DefinitionSha256, string Kind, int? SizeU, int GroupCount, int PortCount);
public sealed record PrivateTemplateDetail(Guid Id, string Name, bool Active, int DefinitionVersion,
    string DefinitionSha256, string Kind, int? SizeU, int GroupCount, int PortCount, int DefinitionByteLength, string DefinitionBase64);
public sealed record PrivateTemplatesSnapshot(string Kind, Guid CustomerId, Guid OwnerId, long Revision,
    IReadOnlyList<PrivateTemplateMetadata> Templates);
public sealed record PrivateTemplateSnapshot(string Kind, Guid CustomerId, Guid OwnerId, long Revision, PrivateTemplateDetail Template);
public sealed record PrivateTemplateChange(string Type, Guid TemplateId, string Name, bool Active, bool Changed,
    int DefinitionVersion, string DefinitionSha256);
public sealed record PrivateTemplateResult(string Kind, Guid CustomerId, Guid OwnerId, long Revision,
    Guid RequestId, Guid OperationId, PrivateTemplateChange Result);
public sealed record PrivateTemplateStatus(string State, Guid CustomerId, Guid OwnerId, long Revision,
    Guid RequestId, PrivateTemplateResult? Operation);

/// <summary>Private immutable configurations with a personal revision and separate terminal operation journal.</summary>
public sealed partial class PrivateDeviceTemplates(NpgsqlDataSource source)
{
    public const long MaximumRevision = 9007199254740991;
    public const int MaximumActive = 128;
    public const int MaximumDefinitionBytes = 1048576;
    private const string Kind = "privateTemplates";
    private static readonly JsonSerializerOptions Json = new(JsonSerializerDefaults.Web)
        { UnmappedMemberHandling = JsonUnmappedMemberHandling.Disallow };
    private sealed record Intent(string Type, Guid? DeviceId, string? Name, long? SourceRevision, Guid? TemplateId);
    private sealed record Terminal(Guid CustomerId, string Hash, string State, string Result);
    private sealed record Stored(PrivateTemplateMetadata Metadata, PrivateTemplateDefinition Definition, string DefinitionJson);

    public static string ETag(long revision) => $"\"templates-{revision.ToString(CultureInfo.InvariantCulture)}\"";
    public static long ParseRevision(string? etag)
    {
        if (string.IsNullOrWhiteSpace(etag)) throw new DomainError(428, "revision_required");
        if (!etag.StartsWith("\"templates-", StringComparison.Ordinal) || !etag.EndsWith('"')) throw new DomainError(422, "revision_invalid");
        if (!long.TryParse(etag[11..^1], NumberStyles.None, CultureInfo.InvariantCulture, out long value)
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
        await using var command = Cmd(db, tx, sql, values);
        return await command.ExecuteNonQueryAsync(ct);
    }
    private static void Keys(JsonObject value, params string[] keys)
    {
        if (value.Count != keys.Length || keys.Any(k => !value.ContainsKey(k))) throw new DomainError(422, "request_invalid");
    }
    private static Intent ParseIntent(JsonElement input)
    {
        JsonObject value = Object(input);
        string type = String(value, "type");
        if (type == "capture")
        {
            Keys(value, "type", "deviceId", "name", "sourceRevision");
            if (value["sourceRevision"] is not JsonValue number || !number.TryGetValue<long>(out long revision)
                || revision < 1 || revision > MaximumRevision) throw new DomainError(422, "revision_invalid");
            return new(type, Id(value, "deviceId"), Names.Validate(String(value, "name")), revision, null);
        }
        if (type == "deactivate")
        {
            Keys(value, "type", "templateId");
            return new(type, null, null, null, Id(value, "templateId"));
        }
        if (type == "rename")
        {
            Keys(value, "type", "templateId", "name");
            return new(type, null, Names.Validate(String(value, "name")), null, Id(value, "templateId"));
        }
        throw new DomainError(422, "request_invalid");
    }
    internal static async Task Authorize(NpgsqlConnection db, NpgsqlTransaction tx, Actor actor, Guid customer, bool edit, CancellationToken ct)
    {
        await PostgresStore.RequireCurrentSession(db, tx, actor, ct);
        await using var command = Cmd(db, tx, "SELECT EXISTS(SELECT 1 FROM customer WHERE systemhaus_id=@house AND id=@customer)",
            ("house", actor.HouseId), ("customer", customer));
        if (await command.ExecuteScalarAsync(ct) is not true
            || !await PostgresStore.Can(db, tx, actor, customer, Capabilities.InventoryRead, ct)) throw new DomainError(404, "not_found");
        if (edit && !await PostgresStore.Can(db, tx, actor, customer, Capabilities.InventoryEdit, ct)) throw new DomainError(403, "forbidden");
    }
    private static async Task<long> LockCustomer(NpgsqlConnection db, NpgsqlTransaction tx, Actor actor, Guid customer, CancellationToken ct)
    {
        await using var command = Cmd(db, tx, "SELECT revision FROM customer WHERE systemhaus_id=@house AND id=@customer FOR SHARE",
            ("house", actor.HouseId), ("customer", customer));
        return await command.ExecuteScalarAsync(ct) is long revision ? revision : throw new DomainError(404, "not_found");
    }
    internal static Task<int> LockAggregate(NpgsqlConnection db, NpgsqlTransaction tx, Actor actor, bool shared, CancellationToken ct)
        => Exec(db, tx, shared ? "SELECT pg_advisory_xact_lock_shared(hashtextextended(@key,0))" : "SELECT pg_advisory_xact_lock(hashtextextended(@key,0))", ct,
            ("key", $"RackClick/private-device-templates/{actor.HouseId:D}/{actor.Id:D}"));
    private static Task<int> LockRequest(NpgsqlConnection db, NpgsqlTransaction tx, Actor actor, Guid requestId, CancellationToken ct)
        => Exec(db, tx, "SELECT pg_advisory_xact_lock(hashtextextended(@key,0))", ct,
            ("key", $"RackClick/private-device-template-operation/{actor.HouseId:D}/{actor.Id:D}/{requestId:D}"));
    private static async Task<long> Revision(NpgsqlConnection db, NpgsqlTransaction tx, Actor actor, CancellationToken ct)
    {
        await using var command = Cmd(db, tx, "SELECT revision FROM user_device_templates WHERE systemhaus_id=@house AND owner_id=@owner",
            ("house", actor.HouseId), ("owner", actor.Id));
        return await command.ExecuteScalarAsync(ct) is long revision ? revision : 0;
    }
    private static async Task<Terminal?> Find(NpgsqlConnection db, NpgsqlTransaction tx, Actor actor, Guid requestId, CancellationToken ct)
    {
        await using var command = Cmd(db, tx, "SELECT customer_id,request_hash,state,result_json::text FROM user_device_template_operation WHERE systemhaus_id=@house AND owner_id=@owner AND request_id=@request",
            ("house", actor.HouseId), ("owner", actor.Id), ("request", requestId));
        await using var rows = await command.ExecuteReaderAsync(ct);
        return await rows.ReadAsync(ct) ? new(rows.GetGuid(0), rows.GetString(1), rows.GetString(2), rows.GetString(3)) : null;
    }
    private static PrivateTemplateResult Committed(Terminal terminal, Actor actor, Guid customer, Guid requestId)
    {
        try
        {
            var result = JsonSerializer.Deserialize<PrivateTemplateResult>(terminal.Result, Json);
            if (result is null || result.Kind != Kind || result.CustomerId != customer || result.OwnerId != actor.Id
                || result.RequestId != requestId || result.OperationId == Guid.Empty || result.Revision < 0
                || result.Revision > MaximumRevision || result.Result is null) throw new DomainError(409, "templates_conflict");
            return result;
        }
        catch (JsonException) { throw new DomainError(409, "templates_conflict"); }
    }
    private static PrivateTemplateStatus Outcome(Terminal? terminal, Actor actor, Guid customer, Guid requestId, long revision)
    {
        if (terminal is not null && terminal.CustomerId != customer) throw new DomainError(404, "not_found");
        return new(terminal?.State ?? "notRecorded", customer, actor.Id, revision, requestId,
            terminal?.State == "committed" ? Committed(terminal, actor, customer, requestId) : null);
    }
    private static string DefinitionJson(PrivateTemplateDefinition definition)
        => Canonical(JsonSerializer.SerializeToNode(definition, Json));
    internal static string DefinitionHash(PrivateTemplateDefinition definition)
        => Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes(DefinitionJson(definition))));
    // Same ordered classification as adopted irLayout; persist a closed technical family, never a literal source preset/name.
    private static string VisualFamily(string preset)
    {
        preset = preset.ToLowerInvariant();
        if (Regex.IsMatch(preset, "server|srv|nas|storage|san", RegexOptions.CultureInvariant)) return "storage";
        if (preset.Contains("ups", StringComparison.Ordinal)) return "ups";
        if (Regex.IsMatch(preset, "blank|spacer|cable|shelf|bl[12]u|sp[12]u|cbl", RegexOptions.CultureInvariant)) return "blank";
        if (preset.Contains("switch", StringComparison.Ordinal) || preset.StartsWith("sw", StringComparison.Ordinal)) return "switch";
        return "panel";
    }
    private static void ValidateDefinition(PrivateTemplateDefinition definition)
    {
        if (definition.Kind is not ("rackEquipment" or "dose" or "endDevice")
            || (definition.Kind == "rackEquipment" ? definition.SizeU is null or < 1 or > 1000 : definition.SizeU is not null)
            || definition.PoeBudget is < 0 or > 999999 || definition.PortGroups is null || definition.PortGroups.Count > 32
            || definition.VisualFamily is not ("storage" or "ups" or "blank" or "switch" or "panel")
            || definition.Icon is null || definition.Color is null || !InventoryRc9Catalog.ValidColor(definition.Color)) throw new DomainError(422, "template_definition_invalid");
        _ = FreeText.Validate(definition.Icon, 100);
        for (int i = 0; i < definition.PortGroups.Count; i++)
        {
            var group = definition.PortGroups[i];
            if (group is null || group.Key != "g" + (i + 1) || group.SortOrder != i
                || InventoryRules.Family(group.Type) != group.Type || group.Ports is null || group.Ports.Count is < 1 or > 96)
                throw new DomainError(422, "template_definition_invalid");
            _ = FreeText.Validate(group.Name, 100); _ = FreeText.Validate(group.Prefix, 100);
            for (int j = 0; j < group.Ports.Count; j++)
            {
                var port = group.Ports[j];
                if (port is null || port.Gn < 1 || port.SortOrder != j || InventoryRules.Family(port.Type) != group.Type
                    || (port.Poe && group.Type != "rj45")
                    || (port.Type != "power" && port.PowerRole != "unspecified")
                    || (port.Color is not null && !InventoryRc9Catalog.ValidColor(port.Color))) throw new DomainError(422, "template_definition_invalid");
                _ = FreeText.Validate(port.Label, 500); _ = InventoryRules.Face(port.Face); _ = InventoryRules.PowerRole(port.PowerRole);
            }
        }
        if (Encoding.UTF8.GetByteCount(DefinitionJson(definition)) > MaximumDefinitionBytes) throw new DomainError(422, "template_definition_too_large");
    }
    private static async Task<Stored> Load(NpgsqlConnection db, NpgsqlTransaction tx, Actor actor, Guid templateId, CancellationToken ct)
    {
        await using var command = Cmd(db, tx, "SELECT name,active,definition_version,definition_sha256,definition_json FROM user_device_template WHERE systemhaus_id=@house AND owner_id=@owner AND id=@id",
            ("house", actor.HouseId), ("owner", actor.Id), ("id", templateId));
        await using var rows = await command.ExecuteReaderAsync(ct);
        if (!await rows.ReadAsync(ct)) throw new DomainError(404, "not_found");
        try
        {
            var definition = JsonSerializer.Deserialize<PrivateTemplateDefinition>(rows.GetString(4), Json) ?? throw new DomainError(409, "templates_conflict");
            ValidateDefinition(definition);
            string definitionJson = rows.GetString(4);
            string hash = Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes(definitionJson)));
            if (rows.GetInt32(2) != 1 || hash != rows.GetString(3)) throw new DomainError(409, "templates_conflict");
            return new(new(templateId, rows.GetString(0), rows.GetBoolean(1), 1, rows.GetString(3), definition.Kind,
                definition.SizeU, definition.PortGroups.Count, definition.PortGroups.Sum(g => g.Ports.Count)), definition, definitionJson);
        }
        catch (JsonException) { throw new DomainError(409, "templates_conflict"); }
    }
    internal static async Task<PrivateTemplateDefinition> ForCreation(NpgsqlConnection db, NpgsqlTransaction tx, Actor actor,
        Guid customer, Guid templateId, int version, string hash, CancellationToken ct)
    {
        // Inventory engine already owns the customer UPDATE lock. All private commands take customer before owner.
        await LockAggregate(db, tx, actor, true, ct);
        await Authorize(db, tx, actor, customer, true, ct);
        var stored = await Load(db, tx, actor, templateId, ct);
        if (!stored.Metadata.Active) throw new DomainError(409, "template_inactive");
        if (version != stored.Metadata.DefinitionVersion || hash != stored.Metadata.DefinitionSha256) throw new DomainError(409, "template_changed");
        return stored.Definition;
    }
    // Caller owns customer SHARE and shared collection lock. The source stays actor-owned;
    // publication requires read+publish, deliberately not inventory.edit.
    internal static async Task<(PrivateTemplateMetadata Metadata, string DefinitionJson)> ForPublication(
        NpgsqlConnection db, NpgsqlTransaction tx, Actor actor, Guid customer, Guid templateId, int version,
        string hash, CancellationToken ct)
    {
        await LockAggregate(db, tx, actor, true, ct);
        await Authorize(db, tx, actor, customer, false, ct);
        var stored = await Load(db, tx, actor, templateId, ct);
        if (!stored.Metadata.Active) throw new DomainError(409, "template_inactive");
        if (version != stored.Metadata.DefinitionVersion || hash != stored.Metadata.DefinitionSha256)
            throw new DomainError(409, "template_changed");
        return (stored.Metadata, stored.DefinitionJson);
    }
    internal static PrivateTemplateDefinition ValidateSharedDefinition(string definitionJson, int version, string hash)
    {
        try
        {
            if (version != 1 || Encoding.UTF8.GetByteCount(definitionJson) > MaximumDefinitionBytes
                || Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes(definitionJson))) != hash)
                throw new DomainError(409, "templates_conflict");
            var definition = JsonSerializer.Deserialize<PrivateTemplateDefinition>(definitionJson, Json)
                ?? throw new DomainError(409, "templates_conflict");
            ValidateDefinition(definition);
            if (definition.PortGroups.Any(g => g.Ports.Select(p => p.Gn).Distinct().Count() != g.Ports.Count))
                throw new DomainError(409, "templates_conflict");
            return definition;
        }
        catch (Exception e) when (e is JsonException or DomainError)
        { throw new DomainError(409, "templates_conflict"); }
    }
    private static PrivateTemplateDetail Detail(Stored value)
    {
        var m = value.Metadata;
        byte[] bytes = Encoding.UTF8.GetBytes(value.DefinitionJson);
        return new(m.Id, m.Name, m.Active, m.DefinitionVersion, m.DefinitionSha256, m.Kind, m.SizeU, m.GroupCount, m.PortCount,
            bytes.Length, Convert.ToBase64String(bytes));
    }
    public async Task<PrivateTemplatesSnapshot> Read(Actor actor, Guid customer, IQueryCollection query, CancellationToken ct)
    {
        await using var db = await source.OpenConnectionAsync(ct); await using var tx = await db.BeginTransactionAsync(ct);
        await LockCustomer(db, tx, actor, customer, ct); await Authorize(db, tx, actor, customer, false, ct);
        if (query.Count != 0) throw new DomainError(422, "request_invalid");
        await LockAggregate(db, tx, actor, true, ct); await Authorize(db, tx, actor, customer, false, ct);
        long revision = await Revision(db, tx, actor, ct);
        var ids = new List<Guid>();
        await using (var command = Cmd(db, tx, "SELECT id FROM user_device_template WHERE systemhaus_id=@house AND owner_id=@owner AND active ORDER BY id", ("house", actor.HouseId), ("owner", actor.Id)))
        await using (var rows = await command.ExecuteReaderAsync(ct)) while (await rows.ReadAsync(ct)) ids.Add(rows.GetGuid(0));
        if (ids.Count > MaximumActive) throw new DomainError(409, "templates_conflict");
        var items = new List<PrivateTemplateMetadata>();
        foreach (Guid id in ids) items.Add((await Load(db, tx, actor, id, ct)).Metadata);
        await Authorize(db, tx, actor, customer, false, ct); await tx.CommitAsync(ct);
        return new(Kind, customer, actor.Id, revision, items);
    }
    public async Task<PrivateTemplateSnapshot> ReadOne(Actor actor, Guid customer, Guid templateId, IQueryCollection query, CancellationToken ct)
    {
        if (templateId == Guid.Empty) throw new DomainError(422, "object_id_invalid");
        await using var db = await source.OpenConnectionAsync(ct); await using var tx = await db.BeginTransactionAsync(ct);
        await LockCustomer(db, tx, actor, customer, ct); await Authorize(db, tx, actor, customer, false, ct);
        if (query.Count != 0) throw new DomainError(422, "request_invalid");
        await LockAggregate(db, tx, actor, true, ct); await Authorize(db, tx, actor, customer, false, ct);
        var result = new PrivateTemplateSnapshot(Kind, customer, actor.Id, await Revision(db, tx, actor, ct), Detail(await Load(db, tx, actor, templateId, ct)));
        await Authorize(db, tx, actor, customer, false, ct); await tx.CommitAsync(ct); return result;
    }
    public async Task<PrivateTemplateStatus> Status(Actor actor, Guid customer, Guid requestId, IQueryCollection query, CancellationToken ct)
    {
        if (requestId == Guid.Empty) throw new DomainError(422, "request_id_invalid");
        await using var db = await source.OpenConnectionAsync(ct); await using var tx = await db.BeginTransactionAsync(ct);
        await LockRequest(db, tx, actor, requestId, ct); await LockCustomer(db, tx, actor, customer, ct);
        await Authorize(db, tx, actor, customer, true, ct);
        if (query.Count != 0) throw new DomainError(422, "request_invalid");
        await LockAggregate(db, tx, actor, true, ct); await Authorize(db, tx, actor, customer, true, ct);
        var result = Outcome(await Find(db, tx, actor, requestId, ct), actor, customer, requestId, await Revision(db, tx, actor, ct));
        await Authorize(db, tx, actor, customer, true, ct); await tx.CommitAsync(ct); return result;
    }
    public async Task<PrivateTemplateResult> Set(Actor actor, Guid customer, JsonElement input, long expected, Guid requestId, IQueryCollection query, CancellationToken ct)
        => (await Execute(actor, customer, input, expected, requestId, query, false, ct)).Operation ?? throw new DomainError(409, "operation_cancelled");
    public Task<PrivateTemplateStatus> Cancel(Actor actor, Guid customer, JsonElement input, long expected, Guid requestId, IQueryCollection query, CancellationToken ct)
        => Execute(actor, customer, input, expected, requestId, query, true, ct);

    private static async Task<PrivateTemplateDefinition> Capture(NpgsqlConnection db, NpgsqlTransaction tx, Actor actor, Guid customer, Guid device, CancellationToken ct)
    {
        async Task<JsonObject> Row(string table, Guid id)
        {
            await using var command = Cmd(db, tx, $"SELECT to_jsonb(t)::text FROM {table} t WHERE systemhaus_id=@house AND customer_id=@customer AND id=@id",
                ("house", actor.HouseId), ("customer", customer), ("id", id));
            return await command.ExecuteScalarAsync(ct) is string value ? JsonNode.Parse(value)!.AsObject() : throw new DomainError(404, "not_found");
        }
        var row = await Row("inventory_device", device);
        var properties = row["properties"]!.AsObject();
        string icon = properties["icon"] is null ? "▦" : String(properties, "icon");
        string color = properties["color"] is null ? "#64748b" : String(properties, "color");
        string family = VisualFamily(properties["preset"] is null ? "" : String(properties, "preset"));
        var groups = new List<PrivateTemplateGroup>(); var groupIds = new List<Guid>();
        await using (var command = Cmd(db, tx, "SELECT id FROM inventory_port_group WHERE systemhaus_id=@house AND customer_id=@customer AND device_id=@device ORDER BY sort_order,id",
            ("house", actor.HouseId), ("customer", customer), ("device", device)))
        await using (var rows = await command.ExecuteReaderAsync(ct)) while (await rows.ReadAsync(ct)) groupIds.Add(rows.GetGuid(0));
        if (groupIds.Count > 32) throw new DomainError(422, "template_definition_invalid");
        foreach (Guid groupId in groupIds)
        {
            var group = await Row("inventory_port_group", groupId); var ports = new List<PrivateTemplatePort>();
            await using (var command = Cmd(db, tx, "SELECT gn,type,label,poe,color,face,power_role FROM inventory_port WHERE systemhaus_id=@house AND customer_id=@customer AND device_id=@device AND group_id=@group ORDER BY sort_order,id",
                ("house", actor.HouseId), ("customer", customer), ("device", device), ("group", groupId)))
            await using (var rows = await command.ExecuteReaderAsync(ct))
                while (await rows.ReadAsync(ct)) ports.Add(new(rows.GetInt32(0), ports.Count, rows.GetString(1), rows.GetString(2), rows.GetBoolean(3),
                    rows.IsDBNull(4) ? null : rows.GetString(4), rows.GetString(5), rows.GetString(6)));
            groups.Add(new("g" + (groups.Count + 1), String(group, "type"), String(group, "name"), String(group, "prefix"), groups.Count, ports));
        }
        string kind = String(row, "kind");
        var definition = new PrivateTemplateDefinition(kind, kind == "rackEquipment" ? Integer(row, "size_u", 1, 1000) : null,
            Number(row, "poe_budget", 999999), icon, color, family, groups);
        ValidateDefinition(definition); return definition;
    }
    private async Task<PrivateTemplateStatus> Execute(Actor actor, Guid customer, JsonElement input, long expected, Guid requestId,
        IQueryCollection query, bool cancel, CancellationToken ct)
    {
        var intent = ParseIntent(input);
        if (requestId == Guid.Empty) throw new DomainError(422, "request_id_invalid");
        if (expected < 0 || expected > MaximumRevision) throw new DomainError(422, "revision_invalid");
        string digest = Secrets.Digest(Canonical(new JsonObject { ["family"] = Kind, ["houseId"] = actor.HouseId,
            ["ownerId"] = actor.Id, ["customerId"] = customer, ["intent"] = JsonSerializer.SerializeToNode(intent, Json), ["expected"] = expected }));
        await using var db = await source.OpenConnectionAsync(ct); await using var tx = await db.BeginTransactionAsync(ct);
        try
        {
            await LockRequest(db, tx, actor, requestId, ct);
            long sourceRevision = await LockCustomer(db, tx, actor, customer, ct);
            await Authorize(db, tx, actor, customer, true, ct);
            if (query.Count != 0) throw new DomainError(422, "request_invalid");
            await LockAggregate(db, tx, actor, false, ct); await Authorize(db, tx, actor, customer, true, ct);
            long revision = await Revision(db, tx, actor, ct);
            var prior = await Find(db, tx, actor, requestId, ct);
            if (prior is not null)
            {
                if (prior.CustomerId != customer || prior.Hash != digest) throw new DomainError(409, "request_id_reused");
                if (!cancel && prior.State == "cancelled") throw new DomainError(409, "operation_cancelled");
                var replay = Outcome(prior, actor, customer, requestId, revision);
                await Authorize(db, tx, actor, customer, true, ct); await tx.CommitAsync(ct); return replay;
            }
            Guid operationId = Guid.NewGuid(); PrivateTemplateResult? committed = null;
            string before, after, stored; Guid resource = actor.Id;
            if (cancel)
            {
                before = JsonSerializer.Serialize(new { ownerId = actor.Id, customerId = customer, revision }, Json);
                after = JsonSerializer.Serialize(new { ownerId = actor.Id, customerId = customer, revision, state = "cancelled", type = intent.Type, expectedPersonalRevision = expected }, Json);
                stored = JsonSerializer.Serialize(new { kind = Kind, state = "cancelled", customerId = customer, ownerId = actor.Id, requestId, operationId, revision }, Json);
            }
            else
            {
                Revisions.Require(expected, revision);
                bool changed; Stored value;
                if (intent.Type == "capture")
                {
                    if (intent.SourceRevision!.Value != sourceRevision) throw new DomainError(412, "source_revision_conflict");
                    await using var count = Cmd(db, tx, "SELECT count(*) FROM user_device_template WHERE systemhaus_id=@house AND owner_id=@owner AND active", ("house", actor.HouseId), ("owner", actor.Id));
                    if ((long)(await count.ExecuteScalarAsync(ct))! >= MaximumActive) throw new DomainError(409, "templates_limit");
                    var definition = await Capture(db, tx, actor, customer, intent.DeviceId!.Value, ct);
                    string definitionJson = DefinitionJson(definition), hash = DefinitionHash(definition);
                    if (revision == MaximumRevision) throw new DomainError(409, "templates_revision_exhausted");
                    await Exec(db, tx, "INSERT INTO user_device_templates(systemhaus_id,owner_id) VALUES(@house,@owner) ON CONFLICT DO NOTHING", ct, ("house", actor.HouseId), ("owner", actor.Id));
                    Guid id = Guid.NewGuid();
                    await Exec(db, tx, "INSERT INTO user_device_template(id,systemhaus_id,owner_id,name,definition_version,definition_sha256,definition_json) VALUES(@id,@house,@owner,@name,1,@hash,@definition)", ct,
                        ("id", id), ("house", actor.HouseId), ("owner", actor.Id), ("name", intent.Name!), ("hash", hash), ("definition", definitionJson));
                    value = await Load(db, tx, actor, id, ct); changed = true;
                    before = JsonSerializer.Serialize(new { ownerId = actor.Id, customerId = customer, revision, template = (object?)null }, Json);
                }
                else
                {
                    value = await Load(db, tx, actor, intent.TemplateId!.Value, ct);
                    if (intent.Type == "rename" && !value.Metadata.Active) throw new DomainError(409, "template_inactive");
                    changed = intent.Type == "rename"
                        ? !string.Equals(value.Metadata.Name, intent.Name, StringComparison.Ordinal) : value.Metadata.Active;
                    before = JsonSerializer.Serialize(new { ownerId = actor.Id, customerId = customer, revision, template = value.Metadata }, Json);
                    if (changed)
                    {
                        if (revision == MaximumRevision) throw new DomainError(409, "templates_revision_exhausted");
                        if (intent.Type == "rename")
                        {
                            await Exec(db, tx, "UPDATE user_device_template SET name=@name WHERE systemhaus_id=@house AND owner_id=@owner AND id=@id", ct,
                                ("name", intent.Name!), ("house", actor.HouseId), ("owner", actor.Id), ("id", value.Metadata.Id));
                            value = value with { Metadata = value.Metadata with { Name = intent.Name! } };
                        }
                        else
                        {
                            await Exec(db, tx, "UPDATE user_device_template SET active=false WHERE systemhaus_id=@house AND owner_id=@owner AND id=@id", ct,
                                ("house", actor.HouseId), ("owner", actor.Id), ("id", value.Metadata.Id));
                            value = value with { Metadata = value.Metadata with { Active = false } };
                        }
                    }
                }
                if (changed)
                {
                    if (await Exec(db, tx, "UPDATE user_device_templates SET revision=@next WHERE systemhaus_id=@house AND owner_id=@owner AND revision=@before", ct,
                        ("next", revision + 1), ("house", actor.HouseId), ("owner", actor.Id), ("before", revision)) != 1) throw new DomainError(409, "templates_conflict");
                    revision++;
                }
                var m = value.Metadata; resource = m.Id;
                committed = new(Kind, customer, actor.Id, revision, requestId, operationId,
                    new(intent.Type, m.Id, m.Name, m.Active, changed, m.DefinitionVersion, m.DefinitionSha256));
                stored = JsonSerializer.Serialize(committed, Json);
                after = JsonSerializer.Serialize(new { ownerId = actor.Id, customerId = customer, revision, template = m, changed }, Json);
            }
            string state = cancel ? "cancelled" : "committed";
            await Exec(db, tx, "INSERT INTO audit_event(id,systemhaus_id,actor_id,request_id,action,resource_id,before_json,after_json) VALUES(@id,@house,@owner,@request,@action,@resource,CAST(@before AS jsonb),CAST(@after AS jsonb))", ct,
                ("id", operationId), ("house", actor.HouseId), ("owner", actor.Id), ("request", requestId), ("resource", resource),
                ("action", "user.deviceTemplate." + intent.Type + (cancel ? ".cancel" : "")), ("before", before), ("after", after));
            await Exec(db, tx, "INSERT INTO user_device_template_operation(systemhaus_id,owner_id,customer_id,request_id,request_hash,state,operation_id,revision,result_json) VALUES(@house,@owner,@customer,@request,@hash,@state,@operation,@revision,CAST(@result AS jsonb))", ct,
                ("house", actor.HouseId), ("owner", actor.Id), ("customer", customer), ("request", requestId), ("hash", digest), ("state", state), ("operation", operationId), ("revision", revision), ("result", stored));
            await Authorize(db, tx, actor, customer, true, ct); await tx.CommitAsync(ct);
            return new(state, customer, actor.Id, revision, requestId, committed);
        }
        catch (PostgresException e) when (e.SqlState is "23503" or "23505" or "23514") { throw new DomainError(409, "templates_conflict"); }
    }
}
