using System.Globalization;
using System.IO.Compression;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Xml;
using Npgsql;
using RackClick.Domain;

namespace RackClick.Server;

public sealed record InventorySpreadsheetReport(string ReportKind, string Query, string Status, string Family, Guid? RackId,
    string Filename, string ContentType, string Format, string CellEncoding, int RowCount, int ByteLength, string Sha256, string ContentBase64);
public sealed record InventorySpreadsheetResult(string Kind, Guid CustomerId, long Revision, Guid RequestId, Guid OperationId, InventorySpreadsheetReport Report);
public sealed record InventorySpreadsheetStatus(string State, Guid CustomerId, Guid RequestId, InventorySpreadsheetResult? Operation);

public sealed partial class InventoryStore
{
    private const string SpreadsheetContentType = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        SpreadsheetFormat = "xlsx", SpreadsheetCellEncoding = "inline-string-v1",
        SpreadsheetNamespace = "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
        SpreadsheetRelationshipNamespace = "http://schemas.openxmlformats.org/officeDocument/2006/relationships";

    private static InventorySpreadsheetResult StoredSpreadsheetReport(string json, Guid customer, Guid request)
    {
        try
        {
            var result = JsonSerializer.Deserialize<InventorySpreadsheetResult>(json, Json);
            if (result is null || result.Kind != "spreadsheetReport" || result.CustomerId != customer || result.RequestId != request ||
                result.Report is null || result.Report.ReportKind is not ("ports" or "connections") ||
                result.Report.ContentType != SpreadsheetContentType || result.Report.Format != SpreadsheetFormat ||
                result.Report.CellEncoding != SpreadsheetCellEncoding) throw new DomainError(404, "not_found");
            return result;
        }
        catch (JsonException) { throw new DomainError(404, "not_found"); }
    }

    public async Task<InventorySpreadsheetResult> GenerateSpreadsheetReport(Actor actor, Guid customer, JsonElement input, long expected, Guid requestId, CancellationToken ct)
    {
        var filter = ParseReportFilter(input);
        if (requestId == Guid.Empty) throw new DomainError(422, "request_id_invalid");
        string digest = Secrets.Digest(JsonSerializer.Serialize(new { action = "reports.xlsx.generate", customerId = customer, filter, expected }, Json));
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
            InventorySpreadsheetResult? committed = null;
            await using (var command = Cmd(db, tx, "SELECT request_hash,result_json::text FROM operation WHERE systemhaus_id=@house AND actor_id=@actor AND request_id=@request",
                ("house", actor.HouseId), ("actor", actor.Id), ("request", requestId)))
            await using (var row = await command.ExecuteReaderAsync(ct))
                if (await row.ReadAsync(ct))
                {
                    if (row.GetString(0) != digest) throw new DomainError(409, "request_id_reused");
                    committed = StoredSpreadsheetReport(row.GetString(1), customer, requestId);
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
            byte[] bytes = BuildSpreadsheet(customer, revision, filter.ReportKind, page.Items);
            Guid operationId = Guid.NewGuid();
            var report = new InventorySpreadsheetReport(filter.ReportKind, filter.Query, filter.Status, filter.Family, filter.RackId,
                $"rackclick-{filter.ReportKind}-{customer:D}-r{revision.ToString(CultureInfo.InvariantCulture)}.xlsx", SpreadsheetContentType,
                SpreadsheetFormat, SpreadsheetCellEncoding, page.Total, bytes.Length, Convert.ToHexStringLower(SHA256.HashData(bytes)), Convert.ToBase64String(bytes));
            var result = new InventorySpreadsheetResult("spreadsheetReport", customer, revision, requestId, operationId, report);
            string metadata = JsonSerializer.Serialize(new { customerId = customer, sourceRevision = revision, reportKind = filter.ReportKind,
                filter.Query, filter.Status, filter.Family, filter.RackId, report.RowCount, report.ByteLength, report.Sha256,
                format = SpreadsheetFormat, cellEncoding = SpreadsheetCellEncoding }, Json);
            await Exec(db, tx, "INSERT INTO audit_event(id,systemhaus_id,actor_id,request_id,action,resource_id,before_json,after_json) VALUES(@id,@house,@actor,@request,'reports.xlsx.generate',@customer,NULL,CAST(@metadata AS jsonb))", ct,
                ("id", operationId), ("house", actor.HouseId), ("actor", actor.Id), ("request", requestId), ("customer", customer), ("metadata", metadata));
            await Exec(db, tx, "INSERT INTO operation(systemhaus_id,actor_id,request_id,request_hash,result_json) VALUES(@house,@actor,@request,@hash,CAST(@result AS jsonb))", ct,
                ("house", actor.HouseId), ("actor", actor.Id), ("request", requestId), ("hash", digest), ("result", JsonSerializer.Serialize(result, Json)));
            await RequireReportAuthorization(db, tx, actor, customer, ct);
            await tx.CommitAsync(ct);
            return result;
        }
        catch (PostgresException e) when (e.SqlState is "23503" or "23505" or "23514") { throw new DomainError(409, "report_conflict"); }
    }

    public async Task<InventorySpreadsheetStatus> SpreadsheetReportStatus(Actor actor, Guid customer, Guid requestId, CancellationToken ct)
    {
        if (requestId == Guid.Empty) throw new DomainError(422, "request_id_invalid");
        await using var db = await source.OpenConnectionAsync(ct);
        await using var tx = await db.BeginTransactionAsync(System.Data.IsolationLevel.ReadCommitted, ct);
        await PostgresStore.LockOperation(db, tx, actor, requestId, ct, allowReport: true);
        await RequireRead(db, tx, actor, customer, ct);
        await using (var command = Cmd(db, tx, "SELECT id FROM customer WHERE systemhaus_id=@house AND id=@customer FOR SHARE", ("house", actor.HouseId), ("customer", customer)))
            if (await command.ExecuteScalarAsync(ct) is not Guid) throw new DomainError(404, "not_found");
        await RequireReportAuthorization(db, tx, actor, customer, ct);
        InventorySpreadsheetResult? result = null;
        await using (var command = Cmd(db, tx, "SELECT result_json::text FROM operation WHERE systemhaus_id=@house AND actor_id=@actor AND request_id=@request",
            ("house", actor.HouseId), ("actor", actor.Id), ("request", requestId)))
            if (await command.ExecuteScalarAsync(ct) is string json) result = StoredSpreadsheetReport(json, customer, requestId);
        await RequireReportAuthorization(db, tx, actor, customer, ct);
        await tx.CommitAsync(ct);
        return new(result is null ? "notRecorded" : "committed", customer, requestId, result);
    }

    // Reject before growing either an XML part or the final archive beyond the contract.
    private sealed class SpreadsheetStream(int maximum) : MemoryStream
    {
        private void RequireLength(int count)
        {
            if (Math.Max(Length, Position + count) > maximum) throw new DomainError(422, "report_too_large");
        }
        public override void Write(byte[] buffer, int offset, int count) { RequireLength(count); base.Write(buffer, offset, count); }
        public override void Write(ReadOnlySpan<byte> buffer) { RequireLength(buffer.Length); base.Write(buffer); }
        public override void WriteByte(byte value) { RequireLength(1); base.WriteByte(value); }
    }

    private static string SpreadsheetCell(string value)
    {
        if (value.Length > 32767) throw new DomainError(422, "report_too_large");
        var result = new StringBuilder(value.Length);
        for (int i = 0; i < value.Length; i++)
        {
            char c = value[i];
            if (char.IsHighSurrogate(c))
            {
                if (i + 1 == value.Length || !char.IsLowSurrogate(value[i + 1])) throw new DomainError(422, "report_cell_invalid");
                result.Append(c).Append(value[++i]);
            }
            else if (char.IsLowSurrogate(c)) throw new DomainError(422, "report_cell_invalid");
            else if (c == '_' && i + 6 < value.Length && value[i + 1] == 'x' && value[i + 6] == '_' &&
                value.AsSpan(i + 2, 4).IndexOfAnyExcept("0123456789abcdefABCDEF".AsSpan()) < 0)
                result.Append("_x005F_");
            else if ((c < 0x20 && c is not ('\t' or '\n')) || c is '\ufffe' or '\uffff')
                result.Append("_x").Append(((int)c).ToString("X4", CultureInfo.InvariantCulture)).Append('_');
            else result.Append(c);
        }
        return result.ToString();
    }

    private static byte[] SpreadsheetXml(Action<XmlWriter> write, int maximum)
    {
        using var output = new SpreadsheetStream(maximum);
        using (var xml = XmlWriter.Create(output, new XmlWriterSettings { Encoding = new UTF8Encoding(false, true),
            Indent = false, NewLineHandling = NewLineHandling.None, CloseOutput = false }))
        { xml.WriteStartDocument(); write(xml); xml.WriteEndDocument(); }
        return output.ToArray();
    }

    private static byte[] BuildSpreadsheet(Guid customer, long revision, string kind, object[] items)
    {
        string[] names = ["[Content_Types].xml", "_rels/.rels", "xl/workbook.xml", "xl/_rels/workbook.xml.rels", "xl/worksheets/sheet1.xml"];
        const string packageRels = "http://schemas.openxmlformats.org/package/2006/relationships";
        var parts = new List<byte[]>();
        int total = 0;
        void Part(Action<XmlWriter> write)
        {
            var bytes = SpreadsheetXml(write, ReportMaximumBytes - total);
            parts.Add(bytes); total += bytes.Length;
        }
        Part(xml =>
        {
            const string ns = "http://schemas.openxmlformats.org/package/2006/content-types";
            xml.WriteStartElement("Types", ns);
            void Type(string element, string key, string value, string contentType)
            { xml.WriteStartElement(element, ns); xml.WriteAttributeString(key, value); xml.WriteAttributeString("ContentType", contentType); xml.WriteEndElement(); }
            Type("Default", "Extension", "rels", "application/vnd.openxmlformats-package.relationships+xml");
            Type("Default", "Extension", "xml", "application/xml");
            Type("Override", "PartName", "/xl/workbook.xml", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml");
            Type("Override", "PartName", "/xl/worksheets/sheet1.xml", "application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml");
            xml.WriteEndElement();
        });
        void Relationship(XmlWriter xml, string type, string target)
        {
            xml.WriteStartElement("Relationships", packageRels); xml.WriteStartElement("Relationship", packageRels);
            xml.WriteAttributeString("Id", "rId1"); xml.WriteAttributeString("Type", SpreadsheetRelationshipNamespace + "/" + type);
            xml.WriteAttributeString("Target", target); xml.WriteEndElement(); xml.WriteEndElement();
        }
        Part(xml => Relationship(xml, "officeDocument", "xl/workbook.xml"));
        Part(xml =>
        {
            xml.WriteStartElement("workbook", SpreadsheetNamespace); xml.WriteAttributeString("xmlns", "r", null, SpreadsheetRelationshipNamespace);
            xml.WriteStartElement("sheets", SpreadsheetNamespace); xml.WriteStartElement("sheet", SpreadsheetNamespace);
            xml.WriteAttributeString("name", kind == "ports" ? "Ports" : "Connections"); xml.WriteAttributeString("sheetId", "1");
            xml.WriteAttributeString("r", "id", SpreadsheetRelationshipNamespace, "rId1");
            xml.WriteEndElement(); xml.WriteEndElement(); xml.WriteEndElement();
        });
        Part(xml => Relationship(xml, "worksheet", "worksheets/sheet1.xml"));
        Part(xml =>
        {
            xml.WriteStartElement("worksheet", SpreadsheetNamespace); xml.WriteStartElement("sheetData", SpreadsheetNamespace);
            int row = 0;
            void Row(IEnumerable<string> cells)
            {
                row++;
                xml.WriteStartElement("row", SpreadsheetNamespace); xml.WriteAttributeString("r", row.ToString(CultureInfo.InvariantCulture));
                int column = 0;
                foreach (string cell in cells)
                {
                    string reference = "";
                    for (int n = ++column; n > 0; n = (n - 1) / 26) reference = (char)('A' + (n - 1) % 26) + reference;
                    xml.WriteStartElement("c", SpreadsheetNamespace); xml.WriteAttributeString("r", reference + row.ToString(CultureInfo.InvariantCulture));
                    xml.WriteAttributeString("t", "inlineStr"); xml.WriteStartElement("is", SpreadsheetNamespace); xml.WriteStartElement("t", SpreadsheetNamespace);
                    xml.WriteAttributeString("xml", "space", "http://www.w3.org/XML/1998/namespace", "preserve");
                    xml.WriteString(SpreadsheetCell(cell)); xml.WriteEndElement(); xml.WriteEndElement(); xml.WriteEndElement();
                }
                xml.WriteEndElement();
            }
            bool includePhysicalConnector = ReportIncludesPhysicalConnector(items);
            string[] columns = includePhysicalConnector ? [..ReportPortColumns, "physical_connector"] : ReportPortColumns;
            string[] prefix = ["customer_id", "source_revision"];
            Row(kind == "ports" ? prefix.Concat(columns) : prefix.Concat(["connection_id", "note", "color", "patch", "cross_rack"])
                .Concat(columns.Select(c => "from_" + c)).Concat(columns.Select(c => "to_" + c)));
            string[] context = [customer.ToString("D"), revision.ToString(CultureInfo.InvariantCulture)];
            foreach (object item in items)
                if (item is InventoryPortView port) Row(context.Concat(PortCells(port, includePhysicalConnector)));
                else if (item is InventoryConnectionView cable) Row(context.Concat([cable.Id.ToString("D"), cable.Note, cable.Color ?? "", cable.Patch,
                    cable.CrossRack.HasValue ? cable.CrossRack.Value ? "true" : "false" : ""]).Concat(PortCells(cable.From, includePhysicalConnector)).Concat(PortCells(cable.To, includePhysicalConnector)));
            xml.WriteEndElement(); xml.WriteEndElement();
        });
        using var output = new SpreadsheetStream(ReportMaximumBytes);
        using (var archive = new ZipArchive(output, ZipArchiveMode.Create, leaveOpen: true, entryNameEncoding: Encoding.UTF8))
            for (int i = 0; i < names.Length; i++)
            {
                var entry = archive.CreateEntry(names[i], CompressionLevel.NoCompression);
                entry.LastWriteTime = new DateTimeOffset(1980, 1, 1, 0, 0, 0, TimeSpan.Zero); entry.ExternalAttributes = 0;
                using var destination = entry.Open(); destination.Write(parts[i]);
            }
        return output.ToArray();
    }
}
