using System.Text.Json;
using System.Text.Json.Nodes;
using Npgsql;
using RackClick.Domain;
using static RackClick.Server.InventoryJson;

namespace RackClick.Server;

public sealed partial class InventoryStore
{
    private sealed record Impact(Guid[] RackIds, Guid[] DeviceIds, Guid[] GroupIds, Guid[] PortIds, Guid[] ConnectionIds);
    private sealed record ImpactState(Impact Impact, JsonObject Before);

    private static async Task<ImpactState> ImpactFor(NpgsqlConnection db, NpgsqlTransaction tx, Actor actor, Guid customer,
        string type, JsonObject payload, CancellationToken ct)
    {
        var snapshot = JsonNode.Parse(await Snapshot(db, tx, actor, customer, ct))!.AsObject();
        JsonObject[] All(string name) => snapshot[name]!.AsArray().Select(n => n!.AsObject()).ToArray();
        Guid[] racks = [], devices = [], groups = [], ports = [];
        if (type == "rack.delete")
        {
            Guid id = Id(payload, "id");
            await Row(db, tx, actor, customer, "inventory_rack", id, ct);
            racks = [id]; devices = All("devices").Where(d => OptionalId(d, "rackId") == id).Select(d => Id(d, "id")).ToArray();
        }
        else if (type == "device.delete")
        {
            Guid id = Id(payload, "id");
            await Row(db, tx, actor, customer, "inventory_device", id, ct); devices = [id];
        }
        else if (type == "devices.delete")
        {
            // Validate the entire explicit set before deleting anything. Never select by gn or placement.
            var values = Array(payload, "deviceIds", 64);
            if (values.Count == 0) throw new DomainError(422, "array_invalid");
            devices = Ids(payload, "deviceIds");
            foreach (Guid id in devices)
                await Row(db, tx, actor, customer, "inventory_device", id, ct);
        }
        else if (type == "device.editPortGroups")
        {
            Guid device = Id(payload, "deviceId");
            RequireLegacyMutableDevice(await Row(db, tx, actor, customer, "inventory_device", device, ct));
            ports = Ids(payload, "removedPortIds");
            foreach (Guid id in ports)
            {
                var port = await Row(db, tx, actor, customer, "inventory_port", id, ct);
                if (Id(port, "device_id") != device) throw new DomainError(422, "port_scope_invalid");
            }
            var desired = Array(payload, "groups", 32).Select(g => g as JsonObject ?? throw new DomainError(422, "port_group_invalid"))
                .Select(g => OptionalId(g, "id")).Where(id => id.HasValue).Select(id => id!.Value).ToHashSet();
            groups = All("portGroups").Where(g => Id(g, "deviceId") == device && !desired.Contains(Id(g, "id"))).Select(g => Id(g, "id")).ToArray();
        }
        else throw new DomainError(422, "preview_unsupported");
        if (type is "device.delete" or "devices.delete")
        {
            var omittedChildren = All("devices").Any(d => OptionalId(d, "mountParentId") is Guid parent && devices.Contains(parent) && !devices.Contains(Id(d, "id")));
            if (omittedChildren) throw new DomainError(409, "mount_children_present");
        }
        if (devices.Length > 0)
        {
            groups = All("portGroups").Where(g => devices.Contains(Id(g, "deviceId"))).Select(g => Id(g, "id")).ToArray();
            ports = All("ports").Where(p => devices.Contains(Id(p, "deviceId"))).Select(p => Id(p, "id")).ToArray();
        }
        var connections = All("connections").Where(c => ports.Contains(Id(c, "fromPortId")) || ports.Contains(Id(c, "toPortId"))).Select(c => Id(c, "id")).ToArray();
        var impact = new Impact(racks.Order().ToArray(), devices.Order().ToArray(), groups.Order().ToArray(), ports.Order().ToArray(), connections.Order().ToArray());
        var before = new JsonObject();
        foreach (var (collection, ids) in new[] { ("racks", racks), ("devices", devices), ("portGroups", groups), ("ports", ports), ("connections", connections) })
            before[collection] = new JsonArray(All(collection).Where(v => ids.Contains(Id(v, "id"))).Select(v => v.DeepClone()).ToArray());
        return new(impact, before);
    }
    private static string ImpactToken(Actor actor, Guid customer, long revision, string type, JsonObject payload, Impact impact)
    {
        var clean = (JsonObject)payload.DeepClone(); clean.Remove("confirmationToken");
        return Secrets.Digest(Canonical(new JsonObject { ["actor"] = actor.Id, ["customer"] = customer,
            ["revision"] = revision, ["type"] = type, ["payload"] = clean, ["impact"] = JsonSerializer.SerializeToNode(impact, Json) }));
    }
    private static void RequireImpact(Actor actor, Guid customer, long revision, string type, JsonObject payload, Impact impact)
    {
        if (String(payload, "confirmationToken", "") != ImpactToken(actor, customer, revision, type, payload, impact))
            throw new DomainError(409, "impact_confirmation_required");
    }
    public async Task<string> Preview(Actor actor, Guid customer, InventoryCommandRequest request, long expected, CancellationToken ct)
    {
        var payload = Object(request.Payload); string type = request.Type ?? "";
        return await PreviewImpact(actor, customer, type, payload, expected, ct);
    }
    private async Task<string> PreviewImpact(Actor actor, Guid customer, string type, JsonObject payload, long expected, CancellationToken ct)
    {
        await using var db = await source.OpenConnectionAsync(ct);
        await using var tx = await db.BeginTransactionAsync(System.Data.IsolationLevel.ReadCommitted, ct);
        string capability = type.EndsWith(".delete", StringComparison.Ordinal) ? Capabilities.InventoryDelete : Capabilities.InventoryEdit;
        async Task Authorize()
        {
            await RequireRead(db, tx, actor, customer, ct);
            if (!await PostgresStore.Can(db, tx, actor, customer, capability, ct))
                throw new DomainError(403, "forbidden");
        }
        // Preliminary checks hide the target without locks. Follow writers' customer -> actor/session order.
        await Authorize();
        long revision;
        await using (var command = Cmd(db, tx, "SELECT revision FROM customer WHERE systemhaus_id=@house AND id=@customer FOR SHARE",
            ("house", actor.HouseId), ("customer", customer)))
            revision = await command.ExecuteScalarAsync(ct) is long current ? current : throw new DomainError(404, "not_found");
        await PostgresStore.RequireCurrentSession(db, tx, actor, ct);
        await Authorize();
        Revisions.Require(expected, revision);
        // The customer lock keeps inventory stable while ReadCommitted observes current authorization after waits.
        var state = await ImpactFor(db, tx, actor, customer, type, payload, ct);
        string result = JsonSerializer.Serialize(new { customerId = customer, revision, impact = state.Impact,
            confirmationToken = ImpactToken(actor, customer, revision, type, payload, state.Impact) }, Json);
        await PostgresStore.RequireCurrentSession(db, tx, actor, ct);
        await Authorize();
        await tx.CommitAsync(ct);
        return result;
    }
    private static async Task RemoveConnections(NpgsqlConnection db, NpgsqlTransaction tx, Actor actor, Guid customer, Guid[] ids, CancellationToken ct)
        => await Exec(db, tx, "DELETE FROM inventory_connection WHERE systemhaus_id=@house AND customer_id=@customer AND id=ANY(@ids)", ct,
            ("house", actor.HouseId), ("customer", customer), ("ids", ids));
    private static async Task<Change> DeleteInventory(NpgsqlConnection db, NpgsqlTransaction tx, Actor actor, Guid customer,
        string type, JsonObject payload, long revision, Guid operationId, CancellationToken ct)
    {
        var state = await ImpactFor(db, tx, actor, customer, type, payload, ct);
        RequireImpact(actor, customer, revision, type, payload, state.Impact);
        await RemoveConnections(db, tx, actor, customer, state.Impact.ConnectionIds, ct);
        foreach (var (table, ids) in new[] { ("inventory_port", state.Impact.PortIds), ("inventory_port_group", state.Impact.GroupIds),
            ("inventory_device", state.Impact.DeviceIds), ("inventory_rack", state.Impact.RackIds) })
            await Exec(db, tx, $"DELETE FROM {table} WHERE systemhaus_id=@house AND customer_id=@customer AND id=ANY(@ids)", ct,
                ("house", actor.HouseId), ("customer", customer), ("ids", ids));
        if (type == "devices.delete")
            // The server-generated operation/audit identity is the batch resource, never a client-selected inventory entity.
            return new(operationId, state.Before, null, new { resourceId = operationId, batchId = operationId, removedIds = state.Impact });
        Guid id = Id(payload, "id");
        return new(id, state.Before, null, new { resourceId = id, removedIds = state.Impact });
    }

    private static async Task<Change> EditPortGroups(NpgsqlConnection db, NpgsqlTransaction tx, Actor actor, Guid customer,
        JsonObject payload, long revision, CancellationToken ct)
    {
        Guid device = Id(payload, "deviceId");
        RequireLegacyMutableDevice(await Row(db, tx, actor, customer, "inventory_device", device, ct));
        var groups = Array(payload, "groups", 32).Select(g => g as JsonObject ?? throw new DomainError(422, "port_group_invalid")).ToArray();
        var oldIds = await QueryIds(db, tx, "SELECT id FROM inventory_port WHERE systemhaus_id=@house AND customer_id=@customer AND device_id=@device", ct,
            ("house", actor.HouseId), ("customer", customer), ("device", device));
        Guid[] removed = Ids(payload, "removedPortIds"); var retained = new HashSet<Guid>(); var existingGroups = new HashSet<Guid>();
        var beforePorts = new List<JsonObject>();
        foreach (var g in groups)
        {
            string portType = InventoryRules.PortType(String(g, "type"));
            Guid? id = OptionalId(g, "id");
            if (id is not null)
            {
                if (!existingGroups.Add(id.Value)) throw new DomainError(422, "duplicate_ids");
                var current = await Row(db, tx, actor, customer, "inventory_port_group", id.Value, ct);
                if (Id(current, "device_id") != device) throw new DomainError(422, "port_scope_invalid");
            }
            var kept = Ids(g, "retainedPortIds"); int add = Integer(g, "addCount", 0, 96, 0);
            if (kept.Length + add < 1 || kept.Length + add > 96) throw new DomainError(422, "port_group_size_invalid");
            foreach (Guid pid in kept)
            {
                if (!retained.Add(pid) || id is null) throw new DomainError(422, "port_scope_invalid");
                var p = await Row(db, tx, actor, customer, "inventory_port", pid, ct);
                if (Id(p, "device_id") != device || Id(p, "group_id") != id.Value) throw new DomainError(422, "port_scope_invalid");
                if ((Boolean(p, "poe") && InventoryRules.Family(portType) != "rj45") ||
                    (String(p, "power_role") != "unspecified" && portType != "power")) throw new DomainError(422, "port_type_change_invalid");
                beforePorts.Add(p);
            }
        }
        if (!oldIds.Except(retained).ToHashSet().SetEquals(removed) || removed.Any(retained.Contains)) throw new DomainError(422, "removed_port_ids_invalid");
        var impact = await ImpactFor(db, tx, actor, customer, "device.editPortGroups", payload, ct);
        if (impact.Impact.PortIds.Length > 0 || impact.Impact.GroupIds.Length > 0)
            RequireImpact(actor, customer, revision, "device.editPortGroups", payload, impact.Impact);
        var evidenceBefore = await CaptureGroupEditEvidence(db, tx, actor, customer, device, ct);
        await RemoveConnections(db, tx, actor, customer, impact.Impact.ConnectionIds, ct);
        await Exec(db, tx, "DELETE FROM inventory_port WHERE systemhaus_id=@house AND customer_id=@customer AND id=ANY(@ids)", ct,
            ("house", actor.HouseId), ("customer", customer), ("ids", removed));
        await Exec(db, tx, "DELETE FROM inventory_port_group WHERE systemhaus_id=@house AND customer_id=@customer AND id=ANY(@ids)", ct,
            ("house", actor.HouseId), ("customer", customer), ("ids", impact.Impact.GroupIds));
        var created = new List<Guid>();
        for (int order = 0; order < groups.Length; order++)
        {
            var g = groups[order]; string type = InventoryRules.PortType(String(g, "type"));
            Guid group = OptionalId(g, "id") ?? Guid.NewGuid(); var kept = Ids(g, "retainedPortIds"); int add = Integer(g, "addCount", 0, 96, 0);
            bool isNew = !g.ContainsKey("id") || g["id"] is null;
            JsonObject? old = isNew ? null : await Row(db, tx, actor, customer, "inventory_port_group", group, ct);
            string name = g.ContainsKey("name") ? Text(g, "name", 100) : old is null ? "" : String(old, "name");
            string prefix = g.ContainsKey("prefix") ? Text(g, "prefix", 100) : old is null ? "" : String(old, "prefix");
            await Exec(db, tx, isNew ? """
                INSERT INTO inventory_port_group(id,systemhaus_id,customer_id,device_id,type,name,prefix,sort_order)
                VALUES(@id,@house,@customer,@device,@type,@name,@prefix,@order)
                """ : """
                UPDATE inventory_port_group SET type=@type,name=@name,prefix=@prefix,sort_order=@order
                WHERE systemhaus_id=@house AND customer_id=@customer AND id=@id
                """, ct, ("id", group), ("house", actor.HouseId), ("customer", customer), ("device", device),
                ("type", InventoryRules.Family(type)), ("name", name), ("prefix", prefix), ("order", order));
            if (isNew) created.Add(group);
            int gn = 0;
            for (int i = 0; i < kept.Length; i++)
            {
                var port = beforePorts.Single(p => Id(p, "id") == kept[i]); gn = Math.Max(gn, Integer(port, "gn", 1, int.MaxValue));
                string keptType = InventoryRules.Family(String(port, "type")) == InventoryRules.Family(type) ? String(port, "type") : type;
                await Exec(db, tx, "UPDATE inventory_port SET type=@type,sort_order=@order WHERE systemhaus_id=@house AND customer_id=@customer AND id=@id", ct,
                    ("type", keptType), ("order", i), ("house", actor.HouseId), ("customer", customer), ("id", kept[i]));
            }
            for (int i = 0; i < add; i++) created.Add(await AddPort(db, tx, actor, customer, device, group, type, checked(++gn), kept.Length + i, ct));
        }
        await ValidateExistingPower(db, tx, actor, customer, retained.ToArray(), ct);
        var evidenceAfter = await CaptureGroupEditEvidence(db, tx, actor, customer, device, ct);
        // Never expose a misleadingly complete half-pair; the edit can still commit without inverse evidence.
        if (evidenceBefore["complete"]!.GetValue<bool>() is false || evidenceAfter["complete"]!.GetValue<bool>() is false)
        {
            evidenceBefore = UnavailableGroupEditEvidence();
            evidenceAfter = UnavailableGroupEditEvidence();
        }
        return new(device, new { retainedPorts = beforePorts, removed = impact.Before, groupEditEvidence = evidenceBefore },
            new { groups = payload["groups"], createdIds = created, removed, groupEditEvidence = evidenceAfter },
            new { resourceId = device, createdIds = created, removedIds = removed });
    }
}
