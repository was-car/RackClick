using System.Text.Json;
using System.Text.Json.Nodes;
using Npgsql;
using RackClick.Domain;

namespace RackClick.Server;

/// <summary>Fences a never-confirmed request under the same key lock used by all writes.</summary>
public sealed class OperationCancellation(NpgsqlDataSource source)
{
    private static readonly JsonSerializerOptions Json = new(JsonSerializerDefaults.Web);
    private sealed record Canceled(Guid Customer, string Hash, string Result);

    private static NpgsqlCommand Command(NpgsqlConnection db, NpgsqlTransaction tx, string sql,
        params (string Name, object Value)[] values)
    {
        var command = new NpgsqlCommand(sql, db, tx);
        foreach (var (name, value) in values) command.Parameters.AddWithValue(name, value);
        return command;
    }

    private static async Task<Canceled?> Find(NpgsqlConnection db, NpgsqlTransaction tx,
        Actor actor, Guid requestId, CancellationToken ct)
    {
        await using var command = Command(db, tx, """
            SELECT customer_id,request_hash,result_json::text FROM operation_cancellation
            WHERE systemhaus_id=@house AND actor_id=@actor AND request_id=@request
            """, ("house", actor.HouseId), ("actor", actor.Id), ("request", requestId));
        await using var row = await command.ExecuteReaderAsync(ct);
        return await row.ReadAsync(ct) ? new(row.GetGuid(0), row.GetString(1), row.GetString(2)) : null;
    }

    // Caller holds LockOperation and has checked current authorization before inspecting prior state.
    public static async Task EnsureNotCanceled(NpgsqlConnection db, NpgsqlTransaction tx,
        Actor actor, Guid requestId, string requestHash, CancellationToken ct)
    {
        if (await Find(db, tx, actor, requestId, ct) is { } canceled)
            throw new DomainError(409, canceled.Hash == requestHash ? "operation_cancelled" : "request_id_reused");
    }

    // Caller holds LockOperation and has checked inventory.read for this customer.
    public static async Task<string?> Read(NpgsqlConnection db, NpgsqlTransaction tx,
        Actor actor, Guid customer, Guid requestId, CancellationToken ct)
    {
        var canceled = await Find(db, tx, actor, requestId, ct);
        if (canceled is not null && canceled.Customer != customer) throw new DomainError(404, "not_found");
        return canceled?.Result;
    }

    public async Task<string> Cancel(Actor actor, Guid customer, InventoryCommandRequest original,
        long expected, Guid requestId, CancellationToken ct)
    {
        if (requestId == Guid.Empty) throw new DomainError(422, "request_id_invalid");
        if (expected < 1) throw new DomainError(422, "revision_invalid");
        if (string.IsNullOrEmpty(original.Type)) throw new DomainError(422, "command_required");
        string requestHash = InventoryStore.RequestDigest(customer, original, expected);
        await using var db = await source.OpenConnectionAsync(ct);
        await using var tx = await db.BeginTransactionAsync(ct);
        await PostgresStore.LockOperation(db, tx, actor, requestId, ct);
        if (!await PostgresStore.Can(db, tx, actor, customer, Capabilities.InventoryRead, ct))
            throw new DomainError(404, "not_found");

        long revision;
        await using (var command = Command(db, tx,
            "SELECT revision FROM customer WHERE systemhaus_id=@house AND id=@customer FOR UPDATE",
            ("house", actor.HouseId), ("customer", customer)))
            revision = await command.ExecuteScalarAsync(ct) is long value ? value : throw new DomainError(404, "not_found");
        await PostgresStore.RequireCurrentSession(db, tx, actor, ct);
        if (!await PostgresStore.Can(db, tx, actor, customer, Capabilities.InventoryRead, ct))
            throw new DomainError(404, "not_found");
        string capability = original.Type.EndsWith(".delete", StringComparison.Ordinal)
            ? Capabilities.InventoryDelete : Capabilities.InventoryEdit;
        if (!await PostgresStore.Can(db, tx, actor, customer, capability, ct)) throw new DomainError(403, "forbidden");

        string? committed = null;
        await using (var command = Command(db, tx, """
            SELECT request_hash,result_json::text FROM operation
            WHERE systemhaus_id=@house AND actor_id=@actor AND request_id=@request
            """, ("house", actor.HouseId), ("actor", actor.Id), ("request", requestId)))
        await using (var row = await command.ExecuteReaderAsync(ct))
            if (await row.ReadAsync(ct))
            {
                if (row.GetString(0) != requestHash) throw new DomainError(409, "request_id_reused");
                committed = row.GetString(1);
            }
        if (committed is not null)
        {
            // Cancellation cannot undo an earlier commit. Return its original authoritative result.
            await tx.CommitAsync(ct);
            return new JsonObject { ["state"] = "committed", ["customerId"] = customer,
                ["requestId"] = requestId, ["revision"] = revision,
                ["operation"] = JsonNode.Parse(committed) }.ToJsonString();
        }
        if (await Find(db, tx, actor, requestId, ct) is { } canceled)
        {
            if (canceled.Customer != customer || canceled.Hash != requestHash)
                throw new DomainError(409, "request_id_reused");
            await tx.CommitAsync(ct);
            return canceled.Result;
        }

        Guid operationId = Guid.NewGuid();
        string result = JsonSerializer.Serialize(new { state = "cancelled", customerId = customer,
            requestId, revision, operationId, operation = (object?)null }, Json);
        await using (var command = Command(db, tx, """
            INSERT INTO operation_cancellation(systemhaus_id,actor_id,request_id,customer_id,request_hash,operation_id,result_json)
            VALUES(@house,@actor,@request,@customer,@hash,@operation,CAST(@result AS jsonb))
            """, ("house", actor.HouseId), ("actor", actor.Id), ("request", requestId), ("customer", customer),
            ("hash", requestHash), ("operation", operationId), ("result", result)))
            await command.ExecuteNonQueryAsync(ct);
        // No command body, password, token or CSRF in audit. The digest binds the immutable original.
        await using (var command = Command(db, tx, """
            INSERT INTO audit_event(id,systemhaus_id,actor_id,request_id,action,resource_id,before_json,after_json)
            VALUES(@id,@house,@actor,@request,'operation.cancel',@customer,CAST(@before AS jsonb),CAST(@after AS jsonb))
            """, ("id", operationId), ("house", actor.HouseId), ("actor", actor.Id), ("request", requestId),
            ("customer", customer), ("before", JsonSerializer.Serialize(new { state = "notRecorded", customerId = customer }, Json)),
            ("after", JsonSerializer.Serialize(new { state = "cancelled", customerId = customer, requestHash,
                originalType = original.Type, revision }, Json))))
            await command.ExecuteNonQueryAsync(ct);
        await tx.CommitAsync(ct);
        return result;
    }
}
