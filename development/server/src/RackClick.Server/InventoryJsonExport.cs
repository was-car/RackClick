using System.Globalization;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using Npgsql;
using RackClick.Domain;

namespace RackClick.Server;

/// <summary>One server-confirmed current-inventory archive. Notes and user metadata are included, never account tables.</summary>
public sealed record InventoryJsonArchive(string Format, string Scope, string Filename, string ContentType,
    string Encoding, int RowCount, int ByteLength, string Sha256, string ContentBase64);
/// <summary>Idempotent receipt for an authorized inventory-only JSON export.</summary>
public sealed record InventoryJsonExportResult(string Kind, Guid CustomerId, long Revision, Guid RequestId,
    Guid OperationId, InventoryJsonArchive Archive);
/// <summary>Current authorization is required to retrieve even a historical export receipt.</summary>
public sealed record InventoryJsonExportStatus(string State, Guid CustomerId, Guid RequestId, InventoryJsonExportResult? Operation);

public sealed partial class InventoryStore
{
    private const string InventoryJsonFormat = "RackClickInventory-v1", InventoryJsonContentType = "application/json; charset=utf-8";
    private const int InventoryJsonMaximumBytes = 4 * 1024 * 1024, InventoryJsonMaximumRows = 100000;
    private static readonly string[] InventoryJsonCollections = ["sites", "buildings", "rooms", "racks", "devices", "portGroups", "ports", "connections"];

    private static void ValidateInventoryJsonRequest(JsonElement input)
    {
        try
        {
            var body = InventoryJson.Object(input);
            if (body.Count != 2 || InventoryJson.Integer(body, "formatVersion", 1, 1) != 1 || InventoryJson.String(body, "scope") != "customer")
                throw new DomainError(422, "request_invalid");
        }
        catch (Exception error) when (error is DomainError or InvalidOperationException or FormatException or OverflowException)
        { throw new DomainError(422, "request_invalid"); }
    }

    private static byte[] BuildInventoryJson(Guid customer, long revision, string snapshot, out int rowCount)
    {
        if (Encoding.UTF8.GetByteCount(snapshot) > InventoryJsonMaximumBytes) throw new DomainError(422, "report_too_large");
        var source = JsonNode.Parse(snapshot)!.AsObject();
        if (source["customerId"]!.GetValue<string>() != customer.ToString("D") || source["revision"]!.GetValue<long>() != revision)
            throw new InvalidOperationException("Inventory snapshot identity mismatch.");
        var inventory = new JsonObject();
        rowCount = 0;
        // Only the explicit inventory collections cross the archive boundary. No raw SQL rows, house/security state or receipts.
        foreach (string name in InventoryJsonCollections)
        {
            var items = source[name]!.AsArray();
            rowCount = checked(rowCount + items.Count);
            if (rowCount > InventoryJsonMaximumRows) throw new DomainError(422, "report_too_large");
            inventory[name] = items.DeepClone();
        }
        var archive = new JsonObject { ["formatVersion"] = 1, ["kind"] = "RackClickInventory", ["scope"] = "customer",
            ["customerId"] = customer.ToString("D"), ["revision"] = revision, ["inventory"] = inventory };
        byte[] bytes = JsonSerializer.SerializeToUtf8Bytes(archive, Json);
        if (bytes.Length > InventoryJsonMaximumBytes) throw new DomainError(422, "report_too_large");
        return bytes;
    }

    private static InventoryJsonExportResult StoredInventoryJsonExport(string json, Guid customer, Guid request)
    {
        try
        {
            var result = JsonSerializer.Deserialize<InventoryJsonExportResult>(json, Json);
            if (result is null || result.Kind != "inventoryExport" || result.CustomerId != customer || result.RequestId != request ||
                result.OperationId == Guid.Empty || result.Revision < 1 || result.Archive is not { } archive ||
                archive.Format != InventoryJsonFormat || archive.Scope != "customer" || archive.ContentType != InventoryJsonContentType ||
                archive.Encoding != "utf-8" || archive.RowCount is < 0 or > InventoryJsonMaximumRows ||
                archive.ByteLength is < 1 or > InventoryJsonMaximumBytes ||
                archive.Filename != InventoryJsonFilename(customer, result.Revision)) throw new DomainError(404, "not_found");
            return result;
        }
        catch (JsonException) { throw new DomainError(404, "not_found"); }
    }

    private static string InventoryJsonFilename(Guid customer, long revision) =>
        $"rackclick-inventory-{customer:D}-r{revision.ToString(CultureInfo.InvariantCulture)}.json";

    public async Task<InventoryJsonExportResult> GenerateInventoryJsonExport(Actor actor, Guid customer, JsonElement input,
        long expected, Guid requestId, CancellationToken ct)
    {
        ValidateInventoryJsonRequest(input);
        if (requestId == Guid.Empty) throw new DomainError(422, "request_id_invalid");
        string digest = Secrets.Digest(JsonSerializer.Serialize(new { action = "inventory.json.export", customerId = customer, expected, format = InventoryJsonFormat }, Json));
        await using var db = await source.OpenConnectionAsync(ct);
        await using var tx = await db.BeginTransactionAsync(System.Data.IsolationLevel.ReadCommitted, ct);
        try
        {
            await PostgresStore.LockOperation(db, tx, actor, requestId, ct, allowReport: true);
            await RequireRead(db, tx, actor, customer, ct);
            long revision = await RevisionForInventoryJsonExport(db, tx, actor, customer, ct);
            await RequireReportAuthorization(db, tx, actor, customer, ct);
            await OperationCancellation.EnsureNotCanceled(db, tx, actor, requestId, digest, ct);
            InventoryJsonExportResult? prior = null;
            await using (var command = Cmd(db, tx, "SELECT request_hash,result_json::text FROM operation WHERE systemhaus_id=@house AND actor_id=@actor AND request_id=@request",
                ("house", actor.HouseId), ("actor", actor.Id), ("request", requestId)))
            await using (var row = await command.ExecuteReaderAsync(ct))
                if (await row.ReadAsync(ct))
                {
                    if (row.GetString(0) != digest) throw new DomainError(409, "request_id_reused");
                    prior = StoredInventoryJsonExport(row.GetString(1), customer, requestId);
                }
            if (prior is not null)
            {
                await RequireReportAuthorization(db, tx, actor, customer, ct);
                await tx.CommitAsync(ct);
                return prior;
            }
            Revisions.Require(expected, revision);
            byte[] bytes = BuildInventoryJson(customer, revision, await Snapshot(db, tx, actor, customer, ct), out int rows);
            Guid operation = Guid.NewGuid();
            var artifact = new InventoryJsonArchive(InventoryJsonFormat, "customer", InventoryJsonFilename(customer, revision),
                InventoryJsonContentType, "utf-8", rows, bytes.Length, Convert.ToHexStringLower(SHA256.HashData(bytes)), Convert.ToBase64String(bytes));
            var result = new InventoryJsonExportResult("inventoryExport", customer, revision, requestId, operation, artifact);
            string metadata = JsonSerializer.Serialize(new { customerId = customer, sourceRevision = revision, format = InventoryJsonFormat,
                scope = "customer", rowCount = rows, artifact.ByteLength, artifact.Sha256 }, Json);
            await Exec(db, tx, "INSERT INTO audit_event(id,systemhaus_id,actor_id,request_id,action,resource_id,before_json,after_json) VALUES(@id,@house,@actor,@request,'inventory.json.export',@customer,NULL,CAST(@metadata AS jsonb))", ct,
                ("id", operation), ("house", actor.HouseId), ("actor", actor.Id), ("request", requestId), ("customer", customer), ("metadata", metadata));
            await Exec(db, tx, "INSERT INTO operation(systemhaus_id,actor_id,request_id,request_hash,result_json) VALUES(@house,@actor,@request,@hash,CAST(@result AS jsonb))", ct,
                ("house", actor.HouseId), ("actor", actor.Id), ("request", requestId), ("hash", digest), ("result", JsonSerializer.Serialize(result, Json)));
            await RequireReportAuthorization(db, tx, actor, customer, ct);
            await tx.CommitAsync(ct);
            return result;
        }
        catch (PostgresException error) when (error.SqlState is "23503" or "23505" or "23514")
        { throw new DomainError(409, "report_conflict"); }
    }

    public async Task<InventoryJsonExportStatus> InventoryJsonExportStatus(Actor actor, Guid customer, Guid requestId, CancellationToken ct)
    {
        if (requestId == Guid.Empty) throw new DomainError(422, "request_id_invalid");
        await using var db = await source.OpenConnectionAsync(ct);
        await using var tx = await db.BeginTransactionAsync(System.Data.IsolationLevel.ReadCommitted, ct);
        await PostgresStore.LockOperation(db, tx, actor, requestId, ct, allowReport: true);
        await RequireRead(db, tx, actor, customer, ct);
        _ = await RevisionForInventoryJsonExport(db, tx, actor, customer, ct);
        await RequireReportAuthorization(db, tx, actor, customer, ct);
        InventoryJsonExportResult? result = null;
        await using (var command = Cmd(db, tx, "SELECT result_json::text FROM operation WHERE systemhaus_id=@house AND actor_id=@actor AND request_id=@request",
            ("house", actor.HouseId), ("actor", actor.Id), ("request", requestId)))
            if (await command.ExecuteScalarAsync(ct) is string json) result = StoredInventoryJsonExport(json, customer, requestId);
        await RequireReportAuthorization(db, tx, actor, customer, ct);
        await tx.CommitAsync(ct);
        return new(result is null ? "notRecorded" : "committed", customer, requestId, result);
    }

    private static async Task<long> RevisionForInventoryJsonExport(NpgsqlConnection db, NpgsqlTransaction tx, Actor actor, Guid customer, CancellationToken ct)
    {
        await using var command = Cmd(db, tx, "SELECT revision FROM customer WHERE systemhaus_id=@house AND id=@customer FOR SHARE",
            ("house", actor.HouseId), ("customer", customer));
        return await command.ExecuteScalarAsync(ct) is long revision ? revision : throw new DomainError(404, "not_found");
    }
}
