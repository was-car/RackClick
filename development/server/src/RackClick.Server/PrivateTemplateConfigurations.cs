using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using Npgsql;
using RackClick.Domain;
using static RackClick.Server.InventoryJson;

namespace RackClick.Server;

public sealed partial class PrivateDeviceTemplates
{
    public const int MaximumConfigurationBodyBytes = MaximumDefinitionBytes + 16384;
    private sealed record ConfigurationIntent(string Type, string Name, int DefinitionVersion, string InputDefinitionSha256);
    private sealed record ConfigurationInput(ConfigurationIntent Intent, PrivateTemplateDefinition? Definition);

    // This opt-in is deliberately limited to the new create endpoint. All other bodies retain 16 KiB.
    internal static bool IsConfigurationCreate(HttpRequest request)
    {
        if (!HttpMethods.IsPost(request.Method)) return false;
        var parts = request.Path.Value?.Split('/');
        return parts is { Length: 8 } && parts[0] == "" && parts[1] == "api" && parts[2] == "v1"
            && parts[3] == "customers" && Guid.TryParse(parts[4], out var id) && id != Guid.Empty
            && parts[5] == "catalog" && parts[6] == "private-templates" && parts[7] == "configurations";
    }

    // Called before materializing the larger body; command authorization is repeated after every wait.
    public async Task AuthorizeConfiguration(Actor actor, Guid customer, IQueryCollection query, CancellationToken ct)
    {
        await using var db = await source.OpenConnectionAsync(ct); await using var tx = await db.BeginTransactionAsync(ct);
        await LockCustomer(db, tx, actor, customer, ct); await Authorize(db, tx, actor, customer, true, ct);
        if (query.Count != 0) throw new DomainError(422, "request_invalid");
        await tx.CommitAsync(ct);
    }

    private static ConfigurationInput ParseConfiguration(JsonElement input, bool cancel)
    {
        var value = Object(input);
        if (String(value, "type") != "create") throw new DomainError(422, "request_invalid");
        Keys(value, cancel ? ["type", "name", "definitionVersion", "inputDefinitionSha256"]
            : ["type", "name", "definitionVersion", "definition"]);
        string name = Names.Validate(String(value, "name"));
        _ = Integer(value, "definitionVersion", 1, 1);
        if (cancel)
        {
            string hash = String(value, "inputDefinitionSha256");
            if (hash.Length != 64 || hash.Any(c => c is not (>= '0' and <= '9') and not (>= 'a' and <= 'f')))
                throw new DomainError(422, "template_definition_invalid");
            return new(new("create", name, 1, hash), null);
        }
        JsonElement raw = input.GetProperty("definition");
        if (raw.ValueKind != JsonValueKind.Object) throw new DomainError(422, "template_definition_invalid");
        byte[] bytes = Encoding.UTF8.GetBytes(raw.GetRawText());
        if (bytes.Length > MaximumDefinitionBytes) throw new DomainError(422, "template_definition_too_large");
        string inputHash = Convert.ToHexStringLower(SHA256.HashData(bytes));
        JsonObject AsObject(JsonNode? node) => node as JsonObject ?? throw new DomainError(422, "template_definition_invalid");
        var definition = AsObject(value["definition"]);
        Keys(definition, "kind", "sizeU", "poeBudget", "icon", "color", "visualFamily", "portGroups");
        var groups = new List<PrivateTemplateGroup>();
        foreach (var groupNode in Array(definition, "portGroups", 32))
        {
            var group = AsObject(groupNode);
            Keys(group, "key", "type", "name", "prefix", "sortOrder", "ports");
            var ports = new List<PrivateTemplatePort>(); var numbers = new HashSet<int>();
            foreach (var portNode in Array(group, "ports", 96))
            {
                var port = AsObject(portNode);
                Keys(port, "gn", "sortOrder", "type", "label", "poe", "color", "face", "powerRole");
                int gn = Integer(port, "gn", 1, int.MaxValue);
                if (!numbers.Add(gn) || port["poe"] is not JsonValue poeValue || !poeValue.TryGetValue<bool>(out bool poe))
                    throw new DomainError(422, "template_definition_invalid");
                ports.Add(new(gn, Integer(port, "sortOrder", 0, 95), String(port, "type"), String(port, "label"), poe,
                    port["color"] is null ? null : String(port, "color"), String(port, "face"), String(port, "powerRole")));
            }
            groups.Add(new(String(group, "key"), String(group, "type"), String(group, "name"), String(group, "prefix"),
                Integer(group, "sortOrder", 0, 31), ports));
        }
        var result = new PrivateTemplateDefinition(String(definition, "kind"), definition["sizeU"] is null ? null
            : Integer(definition, "sizeU", 1, 1000), Number(definition, "poeBudget", 999999), String(definition, "icon"),
            String(definition, "color"), String(definition, "visualFamily"), groups);
        ValidateDefinition(result); // Historical Load remains unchanged; stricter GN rule applies only above.
        return new(new("create", name, 1, inputHash), result);
    }

    public async Task<PrivateTemplateResult> Configure(Actor actor, Guid customer, JsonElement input, long expected,
        Guid requestId, IQueryCollection query, CancellationToken ct)
        => (await ExecuteConfiguration(actor, customer, input, expected, requestId, query, false, ct)).Operation
            ?? throw new DomainError(409, "operation_cancelled");
    public Task<PrivateTemplateStatus> CancelConfiguration(Actor actor, Guid customer, JsonElement input, long expected,
        Guid requestId, IQueryCollection query, CancellationToken ct)
        => ExecuteConfiguration(actor, customer, input, expected, requestId, query, true, ct);

    private async Task<PrivateTemplateStatus> ExecuteConfiguration(Actor actor, Guid customer, JsonElement input, long expected,
        Guid requestId, IQueryCollection query, bool cancel, CancellationToken ct)
    {
        var parsed = ParseConfiguration(input, cancel); var intent = parsed.Intent;
        if (requestId == Guid.Empty) throw new DomainError(422, "request_id_invalid");
        if (expected < 0 || expected > MaximumRevision) throw new DomainError(422, "revision_invalid");
        string digest = Secrets.Digest(Canonical(new JsonObject { ["family"] = "privateTemplateConfigurationsV1", ["houseId"] = actor.HouseId,
            ["ownerId"] = actor.Id, ["customerId"] = customer, ["intent"] = JsonSerializer.SerializeToNode(intent, Json), ["expected"] = expected }));
        await using var db = await source.OpenConnectionAsync(ct); await using var tx = await db.BeginTransactionAsync(ct);
        try
        {
            await LockRequest(db, tx, actor, requestId, ct); await LockCustomer(db, tx, actor, customer, ct);
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
            Guid operationId = Guid.NewGuid(), resource = actor.Id; PrivateTemplateResult? committed = null;
            string before = JsonSerializer.Serialize(new { ownerId = actor.Id, customerId = customer, revision, template = (object?)null }, Json);
            string after, stored;
            if (cancel)
            {
                after = JsonSerializer.Serialize(new { ownerId = actor.Id, customerId = customer, revision, state = "cancelled", type = intent.Type, expectedPersonalRevision = expected }, Json);
                stored = JsonSerializer.Serialize(new { kind = Kind, state = "cancelled", customerId = customer, ownerId = actor.Id, requestId, operationId, revision }, Json);
            }
            else
            {
                Revisions.Require(expected, revision);
                if (revision == MaximumRevision) throw new DomainError(409, "templates_revision_exhausted");
                await using var count = Cmd(db, tx, "SELECT count(*) FROM user_device_template WHERE systemhaus_id=@house AND owner_id=@owner AND active", ("house", actor.HouseId), ("owner", actor.Id));
                if ((long)(await count.ExecuteScalarAsync(ct))! >= MaximumActive) throw new DomainError(409, "templates_limit");
                var definition = parsed.Definition!;
                string definitionJson = DefinitionJson(definition), hash = DefinitionHash(definition);
                await Exec(db, tx, "INSERT INTO user_device_templates(systemhaus_id,owner_id) VALUES(@house,@owner) ON CONFLICT DO NOTHING", ct, ("house", actor.HouseId), ("owner", actor.Id));
                resource = Guid.NewGuid();
                await Exec(db, tx, "INSERT INTO user_device_template(id,systemhaus_id,owner_id,name,definition_version,definition_sha256,definition_json) VALUES(@id,@house,@owner,@name,1,@hash,@definition)", ct,
                    ("id", resource), ("house", actor.HouseId), ("owner", actor.Id), ("name", intent.Name), ("hash", hash), ("definition", definitionJson));
                if (await Exec(db, tx, "UPDATE user_device_templates SET revision=@next WHERE systemhaus_id=@house AND owner_id=@owner AND revision=@before", ct,
                    ("next", revision + 1), ("house", actor.HouseId), ("owner", actor.Id), ("before", revision)) != 1) throw new DomainError(409, "templates_conflict");
                revision++;
                var m = (await Load(db, tx, actor, resource, ct)).Metadata;
                committed = new(Kind, customer, actor.Id, revision, requestId, operationId,
                    new("create", m.Id, m.Name, true, true, 1, m.DefinitionSha256));
                stored = JsonSerializer.Serialize(committed, Json);
                after = JsonSerializer.Serialize(new { ownerId = actor.Id, customerId = customer, revision, template = m, changed = true }, Json);
            }
            string state = cancel ? "cancelled" : "committed";
            await Exec(db, tx, "INSERT INTO audit_event(id,systemhaus_id,actor_id,request_id,action,resource_id,before_json,after_json) VALUES(@id,@house,@owner,@request,@action,@resource,CAST(@before AS jsonb),CAST(@after AS jsonb))", ct,
                ("id", operationId), ("house", actor.HouseId), ("owner", actor.Id), ("request", requestId), ("resource", resource),
                ("action", "user.deviceTemplate.create" + (cancel ? ".cancel" : "")), ("before", before), ("after", after));
            await Exec(db, tx, "INSERT INTO user_device_template_operation(systemhaus_id,owner_id,customer_id,request_id,request_hash,state,operation_id,revision,result_json) VALUES(@house,@owner,@customer,@request,@hash,@state,@operation,@revision,CAST(@result AS jsonb))", ct,
                ("house", actor.HouseId), ("owner", actor.Id), ("customer", customer), ("request", requestId), ("hash", digest), ("state", state), ("operation", operationId), ("revision", revision), ("result", stored));
            await Authorize(db, tx, actor, customer, true, ct); await tx.CommitAsync(ct);
            return new(state, customer, actor.Id, revision, requestId, committed);
        }
        catch (PostgresException e) when (e.SqlState is "23503" or "23505" or "23514") { throw new DomainError(409, "templates_conflict"); }
    }
}
