using System.Globalization;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using Npgsql;
using RackClick.Domain;

namespace RackClick.Server;

public sealed record InventoryCsvReport(string ReportKind, string Query, string Status, string Family, Guid? RackId,
    string Filename, string ContentType, string Encoding, string CsvValueEncoding, int RowCount, int ByteLength, string Sha256, string ContentBase64);
public sealed record InventoryReportResult(string Kind, Guid CustomerId, long Revision, Guid RequestId, Guid OperationId, InventoryCsvReport Report);
public sealed record InventoryReportStatus(string State, Guid CustomerId, Guid RequestId, InventoryReportResult? Operation);

public sealed partial class InventoryStore
{
    private sealed record ReportFilter(string ReportKind, string Query, string Status, string Family, Guid? RackId);
    private const int ReportMaximumRows = 10000, ReportMaximumBytes = 4 * 1024 * 1024;
    private const string ReportContentType = "text/csv; charset=utf-8", ReportEncoding = "utf-8-bom",
        ReportValueEncoding = "spreadsheet-safe-apostrophe-v1";

    private static ReportFilter ParseReportFilter(JsonElement input)
    {
        JsonObject payload;
        try { payload = InventoryJson.Object(input); }
        catch (DomainError) { throw new DomainError(422, "request_invalid"); }
        string[] keys = ["reportKind", "query", "status", "family", "rackId"];
        // Five keys, all required, including explicit null for whole-customer scope.
        if (payload.Count != keys.Length || keys.Any(k => !payload.ContainsKey(k))) throw new DomainError(422, "request_invalid");
        try
        {
            string kind = InventoryJson.String(payload, "reportKind"), query = InventoryJson.String(payload, "query"),
                status = InventoryJson.String(payload, "status"), family = InventoryJson.String(payload, "family");
            FreeText.Validate(query, 200); _ = query.Normalize(NormalizationForm.FormC);
            if (kind is not ("ports" or "connections") ||
                status is not ("all" or "free" or "reserved" or "disabled" or "faulty") ||
                !(family == "all" || InventoryRules.PortTypes.Select(InventoryRules.Family).Contains(family, StringComparer.Ordinal)) ||
                (kind == "connections" && (status != "all" || family != "all"))) throw new DomainError(422, "request_invalid");
            Guid? rack = null;
            if (payload["rackId"] is not null)
            {
                if (!Guid.TryParseExact(InventoryJson.String(payload, "rackId"), "D", out Guid id) || id == Guid.Empty)
                    throw new DomainError(422, "request_invalid");
                rack = id;
            }
            return new(kind, query, status, family, rack);
        }
        catch (Exception e) when (e is DomainError or ArgumentException) { throw new DomainError(422, "request_invalid"); }
    }

    private static async Task RequireReportAuthorization(NpgsqlConnection db, NpgsqlTransaction tx, Actor actor, Guid customer, CancellationToken ct)
    {
        await PostgresStore.RequireCurrentSession(db, tx, actor, ct);
        await RequireRead(db, tx, actor, customer, ct);
        if (!await PostgresStore.Can(db, tx, actor, customer, Capabilities.ReportsExport, ct)) throw new DomainError(403, "forbidden");
    }

    private static InventoryReportResult StoredReport(string json, Guid customer, Guid request)
    {
        try
        {
            var result = JsonSerializer.Deserialize<InventoryReportResult>(json, Json);
            if (result is null || result.Kind != "report" || result.CustomerId != customer || result.RequestId != request ||
                result.Report is null || result.Report.ReportKind is not ("ports" or "connections") ||
                result.Report.ContentType != ReportContentType || result.Report.Encoding != ReportEncoding ||
                result.Report.CsvValueEncoding != ReportValueEncoding)
                throw new DomainError(404, "not_found");
            return result;
        }
        catch (JsonException) { throw new DomainError(404, "not_found"); }
    }

    public async Task<InventoryReportResult> GenerateReport(Actor actor, Guid customer, JsonElement input, long expected, Guid requestId, CancellationToken ct)
    {
        var filter = ParseReportFilter(input);
        if (requestId == Guid.Empty) throw new DomainError(422, "request_id_invalid");
        string digest = Secrets.Digest(JsonSerializer.Serialize(new { action = "reports.csv.generate", customerId = customer, filter, expected }, Json));
        await using var db = await source.OpenConnectionAsync(ct);
        await using var tx = await db.BeginTransactionAsync(System.Data.IsolationLevel.ReadCommitted, ct);
        try
        {
            await PostgresStore.LockOperation(db, tx, actor, requestId, ct, allowReport: true);
            await RequireRead(db, tx, actor, customer, ct);
            long revision;
            await using (var command = Cmd(db, tx, "SELECT revision FROM customer WHERE systemhaus_id=@house AND id=@customer FOR SHARE",
                ("house", actor.HouseId), ("customer", customer)))
                revision = await command.ExecuteScalarAsync(ct) is long value ? value : throw new DomainError(404, "not_found");
            await RequireReportAuthorization(db, tx, actor, customer, ct);
            await OperationCancellation.EnsureNotCanceled(db, tx, actor, requestId, digest, ct);
            InventoryReportResult? committed = null;
            await using (var command = Cmd(db, tx, "SELECT request_hash,result_json::text FROM operation WHERE systemhaus_id=@house AND actor_id=@actor AND request_id=@request",
                ("house", actor.HouseId), ("actor", actor.Id), ("request", requestId)))
            await using (var row = await command.ExecuteReaderAsync(ct))
                if (await row.ReadAsync(ct))
                {
                    if (row.GetString(0) != digest) throw new DomainError(409, "request_id_reused");
                    committed = StoredReport(row.GetString(1), customer, requestId);
                }
            if (committed is not null)
            {
                await RequireReportAuthorization(db, tx, actor, customer, ct);
                await tx.CommitAsync(ct);
                return committed;
            }
            Revisions.Require(expected, revision);
            string snapshot = await Snapshot(db, tx, actor, customer, ct);
            if (filter.RackId is Guid rack)
            {
                using var document = JsonDocument.Parse(snapshot);
                if (!document.RootElement.GetProperty("racks").EnumerateArray().Any(r => r.GetProperty("id").GetGuid() == rack))
                    throw new DomainError(404, "not_found");
            }
            var page = ProjectView(customer, revision, filter.ReportKind,
                new(filter.Query, null, filter.ReportKind == "ports" ? filter.Status : null, filter.ReportKind == "ports" ? filter.Family : null, 0, ReportMaximumRows + 1),
                snapshot, paginate: false, rackId: filter.RackId);
            if (page.Total > ReportMaximumRows) throw new DomainError(422, "report_too_large");
            byte[] csv = BuildReportCsv(customer, revision, filter.ReportKind, page.Items);
            Guid operationId = Guid.NewGuid();
            var report = new InventoryCsvReport(filter.ReportKind, filter.Query, filter.Status, filter.Family, filter.RackId,
                $"rackclick-{filter.ReportKind}-{customer:D}-r{revision.ToString(CultureInfo.InvariantCulture)}.csv", ReportContentType, ReportEncoding,
                ReportValueEncoding, page.Total, csv.Length, Convert.ToHexStringLower(SHA256.HashData(csv)), Convert.ToBase64String(csv));
            var result = new InventoryReportResult("report", customer, revision, requestId, operationId, report);
            string metadata = JsonSerializer.Serialize(new { customerId = customer, sourceRevision = revision, reportKind = filter.ReportKind,
                filter.Query, filter.Status, filter.Family, filter.RackId, report.RowCount, report.ByteLength, report.Sha256,
                csvValueEncoding = ReportValueEncoding }, Json);
            await Exec(db, tx, "INSERT INTO audit_event(id,systemhaus_id,actor_id,request_id,action,resource_id,before_json,after_json) VALUES(@id,@house,@actor,@request,'reports.csv.generate',@customer,NULL,CAST(@metadata AS jsonb))", ct,
                ("id", operationId), ("house", actor.HouseId), ("actor", actor.Id), ("request", requestId), ("customer", customer), ("metadata", metadata));
            await Exec(db, tx, "INSERT INTO operation(systemhaus_id,actor_id,request_id,request_hash,result_json) VALUES(@house,@actor,@request,@hash,CAST(@result AS jsonb))", ct,
                ("house", actor.HouseId), ("actor", actor.Id), ("request", requestId), ("hash", digest), ("result", JsonSerializer.Serialize(result, Json)));
            await RequireReportAuthorization(db, tx, actor, customer, ct);
            await tx.CommitAsync(ct);
            return result;
        }
        catch (PostgresException e) when (e.SqlState is "23503" or "23505" or "23514") { throw new DomainError(409, "report_conflict"); }
    }

    public async Task<InventoryReportStatus> ReportStatus(Actor actor, Guid customer, Guid requestId, CancellationToken ct)
    {
        if (requestId == Guid.Empty) throw new DomainError(422, "request_id_invalid");
        await using var db = await source.OpenConnectionAsync(ct);
        await using var tx = await db.BeginTransactionAsync(System.Data.IsolationLevel.ReadCommitted, ct);
        await PostgresStore.LockOperation(db, tx, actor, requestId, ct, allowReport: true);
        await RequireRead(db, tx, actor, customer, ct);
        await using (var command = Cmd(db, tx, "SELECT id FROM customer WHERE systemhaus_id=@house AND id=@customer FOR SHARE", ("house", actor.HouseId), ("customer", customer)))
            if (await command.ExecuteScalarAsync(ct) is not Guid) throw new DomainError(404, "not_found");
        await RequireReportAuthorization(db, tx, actor, customer, ct);
        InventoryReportResult? result = null;
        await using (var command = Cmd(db, tx, "SELECT result_json::text FROM operation WHERE systemhaus_id=@house AND actor_id=@actor AND request_id=@request",
            ("house", actor.HouseId), ("actor", actor.Id), ("request", requestId)))
            if (await command.ExecuteScalarAsync(ct) is string json) result = StoredReport(json, customer, requestId);
        await RequireReportAuthorization(db, tx, actor, customer, ct);
        await tx.CommitAsync(ct);
        return new(result is null ? "notRecorded" : "committed", customer, requestId, result);
    }

    private static readonly string[] ReportPortColumns = ["port_id", "device_id", "device_name", "device_kind", "rack_id", "rack_name", "room_id", "room_name",
        "site_id", "site_name", "building_id", "building_name", "group_id", "group_name", "type", "family", "gn", "label", "status", "face", "poe", "watts", "color", "power_role", "connected", "connection_ids", "peer_port_ids"];
    private static string[] PortCells(InventoryPortView port, bool includePhysicalConnector)
    {
        string Id(Guid? id) => id?.ToString("D") ?? "";
        InventoryViewPath? Node(string kind) => port.Path.FirstOrDefault(n => n.Kind == kind);
        string[] cells = [Id(port.Id), Id(port.DeviceId), port.DeviceName, port.DeviceKind, Id(port.RackId), Node("rack")?.Name ?? "", Id(port.RoomId), Node("room")?.Name ?? "",
            Id(Node("site")?.Id), Node("site")?.Name ?? "", Id(Node("building")?.Id), Node("building")?.Name ?? "", Id(port.GroupId), port.GroupName,
            port.Type, port.Family, port.Gn.ToString(CultureInfo.InvariantCulture), port.Label, port.Status, port.Face, port.Poe ? "true" : "false",
            port.Watts?.ToString(CultureInfo.InvariantCulture) ?? "", port.Color ?? "", port.PowerRole, port.Connected ? "true" : "false",
            string.Join(";", port.ConnectionIds.Select(id => id.ToString("D"))), string.Join(";", port.PeerPortIds.Select(id => id.ToString("D")))];
        return includePhysicalConnector ? [..cells, port.PhysicalConnector ?? ""] : cells;
    }

    private static bool ReportIncludesPhysicalConnector(object[] items) => items.Any(item => item is InventoryPortView port ? port.PhysicalConnector is not null :
            item is InventoryConnectionView cable && (cable.From.PhysicalConnector is not null || cable.To.PhysicalConnector is not null));

    private static byte[] BuildReportCsv(Guid customer, long revision, string kind, object[] items)
    {
        using var output = new MemoryStream();
        output.Write([0xef, 0xbb, 0xbf]);
        void Row(IEnumerable<string> cells, bool protect)
        {
            static string Safe(string value)
            {
                string trimmed = value.TrimStart();
                bool prefix = value.Length != 0 && (value[0] is '\'' or '\t' or '\r' or '\n' ||
                    (trimmed.Length != 0 && trimmed[0] is '=' or '+' or '-' or '@'));
                return prefix ? "'" + value : value;
            }
            string row = string.Join(",", cells.Select(c => "\"" + (protect ? Safe(c) : c).Replace("\"", "\"\"", StringComparison.Ordinal) + "\"")) + "\r\n";
            byte[] bytes = Encoding.UTF8.GetBytes(row);
            if (output.Length + bytes.Length > ReportMaximumBytes) throw new DomainError(422, "report_too_large");
            output.Write(bytes);
        }
        bool includePhysicalConnector = ReportIncludesPhysicalConnector(items);
        string[] columns = includePhysicalConnector ? [..ReportPortColumns, "physical_connector"] : ReportPortColumns;
        string[] prefix = ["customer_id", "source_revision"];
        if (kind == "ports") Row(prefix.Concat(columns), false);
        else Row(prefix.Concat(["connection_id", "note", "color", "patch", "cross_rack"])
            .Concat(columns.Select(c => "from_" + c)).Concat(columns.Select(c => "to_" + c)), false);
        string[] context = [customer.ToString("D"), revision.ToString(CultureInfo.InvariantCulture)];
        foreach (object item in items)
            if (item is InventoryPortView port) Row(context.Concat(PortCells(port, includePhysicalConnector)), true);
            else if (item is InventoryConnectionView cable) Row(context.Concat([cable.Id.ToString("D"), cable.Note, cable.Color ?? "", cable.Patch,
                    cable.CrossRack.HasValue ? cable.CrossRack.Value ? "true" : "false" : ""])
                .Concat(PortCells(cable.From, includePhysicalConnector)).Concat(PortCells(cable.To, includePhysicalConnector)), true);
        return output.ToArray();
    }
}
