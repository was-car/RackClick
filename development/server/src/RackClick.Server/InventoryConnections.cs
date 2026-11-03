using System.Text.Json.Nodes;
using Npgsql;
using RackClick.Domain;
using static RackClick.Server.InventoryJson;

namespace RackClick.Server;

public sealed partial class InventoryStore
{
    private static string? PowerSystem(JsonObject port)
    {
        if (String(port,"type")!="power_dc") return null;
        if (port["properties"] is not JsonObject properties) throw new DomainError(422,"properties_invalid");
        string? Read(string key)
        {
            if (!properties.ContainsKey(key) || properties[key] is null) return null;
            if (properties[key] is not JsonValue scalar || !scalar.TryGetValue<string>(out var value)) throw new DomainError(422,"hardware_metadata_invalid");
            return FamilyLRules.Feature("powerSystem",value);
        }
        return Read("hardwarePowerSystem") ?? Read("declaredPowerSystem") ?? "dc";
    }
    private static async Task ValidateExistingPower(NpgsqlConnection db, NpgsqlTransaction tx, Actor actor, Guid customer, Guid[] ports, CancellationToken ct)
    {
        await using var cmd = Cmd(db, tx, """
            SELECT p.type,p.power_role,q.type,q.power_role,p.properties::text,q.properties::text
            FROM inventory_connection_endpoint a JOIN inventory_connection_endpoint b ON a.connection_id=b.connection_id AND b.ordinal=1
            JOIN inventory_port p ON p.id=a.port_id JOIN inventory_port q ON q.id=b.port_id
            WHERE a.ordinal=0 AND a.systemhaus_id=@house AND a.customer_id=@customer AND (a.port_id=ANY(@ports) OR b.port_id=ANY(@ports))
            """, ("house", actor.HouseId), ("customer", customer), ("ports", ports));
        await using var rows = await cmd.ExecuteReaderAsync(ct);
        while (await rows.ReadAsync(ct))
        {
            var a=new JsonObject{["type"]=rows.GetString(0),["properties"]=JsonNode.Parse(rows.GetString(4))};
            var b=new JsonObject{["type"]=rows.GetString(2),["properties"]=JsonNode.Parse(rows.GetString(5))};
            FamilyLRules.PowerPair(rows.GetString(0),rows.GetString(1),PowerSystem(a),rows.GetString(2),rows.GetString(3),PowerSystem(b));
        }
    }
    private static async Task<JsonObject[]> Pair(NpgsqlConnection db, NpgsqlTransaction tx, Actor actor, Guid customer,
        Guid first, Guid second, Guid? excluding, CancellationToken ct)
    {
        if (first == second) throw new DomainError(422, "same_port");
        var a = await Row(db, tx, actor, customer, "inventory_port", first, ct);
        var b = await Row(db, tx, actor, customer, "inventory_port", second, ct);
        if (new[] { a, b }.Any(p => String(p, "status") is "disabled" or "faulty")) throw new DomainError(409, "port_blocked");
        FamilyLRules.PowerPair(String(a,"type"),String(a,"power_role"),PowerSystem(a),String(b,"type"),String(b,"power_role"),PowerSystem(b));
        // The reference profiles name actual connector families. Legacy broad-family behavior remains unchanged.
        var firstOwner = await Row(db, tx, actor, customer, "inventory_device", Id(a, "device_id"), ct);
        var secondOwner = await Row(db, tx, actor, customer, "inventory_device", Id(b, "device_id"), ct);
        InventoryRules.RequireConnectorPair(String(a, "type"), String(b, "type"),
            firstOwner["hardware_profile_key"] is not null || secondOwner["hardware_profile_key"] is not null);
        await using var occupied = Cmd(db, tx, "SELECT EXISTS(SELECT 1 FROM inventory_connection_endpoint WHERE systemhaus_id=@house AND customer_id=@customer AND port_id=ANY(@ports) AND connection_id IS DISTINCT FROM @excluding::uuid)",
            ("house", actor.HouseId), ("customer", customer), ("ports", new[] { first, second }), ("excluding", excluding));
        if (await occupied.ExecuteScalarAsync(ct) is true) throw new DomainError(409, "port_occupied");
        return [a, b];
    }
    private static void ConfirmReserved(IEnumerable<JsonObject> ports, JsonObject payload)
    {
        var required = ports.Where(p => String(p, "status") == "reserved").Select(p => Id(p, "id")).ToHashSet();
        var confirmed = Ids(payload, "confirmedReservedPortIds", optional: true).ToHashSet();
        if (!required.SetEquals(confirmed)) throw new DomainError(409, "reserved_confirmation_required");
    }
    private static async Task<JsonObject> ConnectionRow(NpgsqlConnection db, NpgsqlTransaction tx, Actor actor, Guid customer, Guid id, CancellationToken ct)
    {
        var row = await Row(db, tx, actor, customer, "inventory_connection", id, ct);
        var ports = await QueryIds(db, tx, "SELECT port_id FROM inventory_connection_endpoint WHERE systemhaus_id=@house AND customer_id=@customer AND connection_id=@id ORDER BY ordinal", ct,
            ("house", actor.HouseId), ("customer", customer), ("id", id));
        if (ports.Length != 2) throw new DomainError(409, "connection_invalid");
        // Keep the same JSON string representation used by request/snapshot IDs.
        // JsonValue<Guid> serializes as a string but cannot be read by GetValue<string>().
        row["fromPortId"] = ports[0].ToString("D"); row["toPortId"] = ports[1].ToString("D");
        return row;
    }
    // Duplication keeps the already materialized color, including null, without consulting a preference.
    private static Task<Guid> InsertConnection(NpgsqlConnection db, NpgsqlTransaction tx, Actor actor, Guid customer,
        Guid first, Guid second, JsonObject data, CancellationToken ct)
        => InsertConnection(db, tx, actor, customer, first, second, data, Color(data), ct);

    private static async Task<Guid> InsertConnection(NpgsqlConnection db, NpgsqlTransaction tx, Actor actor, Guid customer,
        Guid first, Guid second, JsonObject data, string? color, CancellationToken ct)
    {
        Guid id = Guid.NewGuid();
        await Exec(db, tx, """
            INSERT INTO inventory_connection(id,systemhaus_id,customer_id,note,color,patch,properties)
            VALUES(@id,@house,@customer,@note,@color,@patch,CAST(@properties AS jsonb))
            """, ct, ("id", id), ("house", actor.HouseId), ("customer", customer), ("note", FreeText.Validate(String(data, "note", ""), 2000)),
            ("color", color), ("patch", InventoryRules.Patch(String(data, "patch", "none"))), ("properties", Properties(data)));
        await Exec(db, tx, """
            INSERT INTO inventory_connection_endpoint(systemhaus_id,customer_id,connection_id,ordinal,port_id)
            VALUES(@house,@customer,@id,0,@first),(@house,@customer,@id,1,@second)
            """, ct, ("house", actor.HouseId), ("customer", customer), ("id", id), ("first", first), ("second", second));
        return id;
    }
    private static async Task<Change> Connections(NpgsqlConnection db, NpgsqlTransaction tx, Actor actor, Guid customer,
        string type, JsonObject payload, CancellationToken ct)
    {
        if (type is "connections.create" or "connections.createBatch")
        {
            JsonObject[] pairs = type == "connections.create" ? [payload] : Array(payload, "pairs", 128)
                .Select(p => p as JsonObject ?? throw new DomainError(422, "pair_invalid")).ToArray();
            if (pairs.Length == 0) throw new DomainError(422, "pairs_required");
            var ids = new HashSet<Guid>(); var ports = new List<JsonObject>();
            foreach (var pair in pairs)
            {
                Guid a = Id(pair, "fromPortId"), b = Id(pair, "toPortId");
                if (!ids.Add(a) || !ids.Add(b)) throw new DomainError(422, "duplicate_ids");
                ports.AddRange(await Pair(db, tx, actor, customer, a, b, null, ct));
            }
            ConfirmReserved(ports, payload);
            // One committed preference snapshot per command; every pair in a batch uses it.
            // No palette advisory wait here: inventory already holds the actor/session locks.
            var palette = await UserCategoryColors.ReadForConnectionCreation(db, tx, actor, ct);
            var categories = await ConnectionCategories(db, tx, actor, customer, ids.ToArray(), ct);
            var colors = pairs.Select(pair => Color(pair) ?? palette.GetValueOrDefault(UserCategoryColors.PairKey(
                categories[Id(pair, "fromPortId")], categories[Id(pair, "toPortId")]))).ToArray();
            // Validate attributes for every pair before the first insert, preserving all-or-nothing batches.
            foreach (var pair in pairs)
            {
                _ = FreeText.Validate(String(pair, "note", ""), 2000);
                _ = InventoryRules.Patch(String(pair, "patch", "none"));
                _ = Properties(pair);
            }
            var created = new List<Guid>(); var after = new List<JsonObject>();
            for (int index = 0; index < pairs.Length; index++)
            {
                var pair = pairs[index];
                Guid id = await InsertConnection(db, tx, actor, customer, Id(pair, "fromPortId"), Id(pair, "toPortId"), pair, colors[index], ct);
                created.Add(id); after.Add(await ConnectionRow(db, tx, actor, customer, id, ct));
            }
            return new(created[0], null, after, new { resourceId = created[0], createdIds = created });
        }
        Guid connectionId = Id(payload, "connectionId");
        var before = await ConnectionRow(db, tx, actor, customer, connectionId, ct);
        if (type == "connections.disconnect")
        {
            await Exec(db, tx, "DELETE FROM inventory_connection WHERE systemhaus_id=@house AND customer_id=@customer AND id=@id", ct,
                ("house", actor.HouseId), ("customer", customer), ("id", connectionId));
            return new(connectionId, before, null, new { resourceId = connectionId, removedIds = new[] { connectionId } });
        }
        if (type == "connections.reconnect")
        {
            Guid keep = Id(payload, "keepPortId"), destination = Id(payload, "newPortId");
            Guid first = Id(before, "fromPortId"), second = Id(before, "toPortId");
            if (keep != first && keep != second) throw new DomainError(409, "connection_endpoint_changed");
            var ports = await Pair(db, tx, actor, customer, keep, destination, connectionId, ct);
            ConfirmReserved(ports, payload);
            await Exec(db, tx, "UPDATE inventory_connection_endpoint SET port_id=@destination WHERE systemhaus_id=@house AND customer_id=@customer AND connection_id=@id AND ordinal=@ordinal", ct,
                ("destination", destination), ("house", actor.HouseId), ("customer", customer), ("id", connectionId), ("ordinal", (short)(keep == first ? 1 : 0)));
        }
        else
        {
            string note = payload.ContainsKey("note") ? FreeText.Validate(String(payload, "note", ""), 2000) : String(before, "note");
            string? color = payload.ContainsKey("color") ? Color(payload) : Color(before);
            string patch = payload.ContainsKey("patch") ? InventoryRules.Patch(String(payload, "patch")) : String(before, "patch");
            await Exec(db, tx, "UPDATE inventory_connection SET note=@note,color=@color,patch=@patch,properties=CAST(@properties AS jsonb) WHERE systemhaus_id=@house AND customer_id=@customer AND id=@id", ct,
                ("note", note), ("color", color), ("patch", patch), ("properties", Properties(payload, before["properties"] as JsonObject)),
                ("house", actor.HouseId), ("customer", customer), ("id", connectionId));
        }
        var changed = await ConnectionRow(db, tx, actor, customer, connectionId, ct);
        return new(connectionId, before, changed, new { resourceId = connectionId });
    }
}
