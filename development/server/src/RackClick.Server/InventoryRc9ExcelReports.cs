using System.Globalization;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Npgsql;
using RackClick.Domain;

namespace RackClick.Server;

public sealed record InventoryRc9ExcelReport(string Format, string CellEncoding, Guid RackId, string GeneratedAt,
    string Filename, string ContentType, int DeviceCount, int ConnectionCount, int SummaryCount, int RowCount,
    int ByteLength, string Sha256, string ContentBase64);
public sealed record InventoryRc9ExcelResult(string Kind, Guid CustomerId, long Revision, Guid RequestId,
    Guid OperationId, InventoryRc9ExcelReport Report);
public sealed record InventoryRc9ExcelStatus(string State, Guid CustomerId, Guid RequestId, InventoryRc9ExcelResult? Operation);

public sealed partial class InventoryStore
{
    private const string Rc9ExcelFormat = "xls-html-rc9-v1", Rc9ExcelCells = "html-text-v1",
        Rc9ExcelMime = "application/vnd.ms-excel;charset=utf-8";

    private static Guid ParseRc9ExcelRack(JsonElement input)
    {
        try
        {
            var payload = InventoryJson.Object(input);
            if (payload.Count != 1 || !payload.ContainsKey("rackId") ||
                !Guid.TryParseExact(InventoryJson.String(payload, "rackId"), "D", out Guid rack) || rack == Guid.Empty)
                throw new DomainError(422, "request_invalid");
            return rack;
        }
        catch (Exception e) when (e is DomainError or ArgumentException or InvalidOperationException or JsonException)
        { throw new DomainError(422, "request_invalid"); }
    }

    private static InventoryRc9ExcelResult StoredRc9Excel(string json, Guid customer, Guid request)
    {
        try
        {
            var result = JsonSerializer.Deserialize<InventoryRc9ExcelResult>(json, Json);
            if (result is null || result.Kind != "rc9ExcelReport" || result.CustomerId != customer || result.RequestId != request ||
                result.Report is null || result.Report.RackId == Guid.Empty || result.Report.Format != Rc9ExcelFormat ||
                result.Report.CellEncoding != Rc9ExcelCells || result.Report.ContentType != Rc9ExcelMime)
                throw new DomainError(404, "not_found");
            return result;
        }
        catch (JsonException) { throw new DomainError(404, "not_found"); }
    }

    public async Task<InventoryRc9ExcelResult> GenerateRc9ExcelReport(Actor actor, Guid customer, JsonElement input,
        long expected, Guid requestId, CancellationToken ct)
    {
        Guid rack = ParseRc9ExcelRack(input);
        if (requestId == Guid.Empty) throw new DomainError(422, "request_id_invalid");
        string digest = Secrets.Digest(JsonSerializer.Serialize(new { action = "reports.xlsHtml.generate", customerId = customer, rackId = rack, expected }, Json));
        await using var db = await source.OpenConnectionAsync(ct);
        await using var tx = await db.BeginTransactionAsync(System.Data.IsolationLevel.ReadCommitted, ct);
        try
        {
            await PostgresStore.LockOperation(db, tx, actor, requestId, ct, allowReport: true);
            await RequireRead(db, tx, actor, customer, ct);
            long revision; string customerName;
            await using (var command = Cmd(db, tx, "SELECT revision,name FROM customer WHERE systemhaus_id=@house AND id=@customer FOR SHARE",
                ("house", actor.HouseId), ("customer", customer)))
            await using (var row = await command.ExecuteReaderAsync(ct))
            {
                if (!await row.ReadAsync(ct)) throw new DomainError(404, "not_found");
                revision = row.GetInt64(0); customerName = row.GetString(1);
            }
            await RequireReportAuthorization(db, tx, actor, customer, ct);
            await OperationCancellation.EnsureNotCanceled(db, tx, actor, requestId, digest, ct);
            InventoryRc9ExcelResult? committed = null;
            await using (var command = Cmd(db, tx, "SELECT request_hash,result_json::text FROM operation WHERE systemhaus_id=@house AND actor_id=@actor AND request_id=@request",
                ("house", actor.HouseId), ("actor", actor.Id), ("request", requestId)))
            await using (var row = await command.ExecuteReaderAsync(ct))
                if (await row.ReadAsync(ct))
                {
                    if (row.GetString(0) != digest) throw new DomainError(409, "request_id_reused");
                    committed = StoredRc9Excel(row.GetString(1), customer, requestId);
                }
            if (committed is not null)
            {
                await RequireReportAuthorization(db, tx, actor, customer, ct);
                await tx.CommitAsync(ct);
                return committed;
            }
            Revisions.Require(expected, revision);
            // Snapshot joins must never silently omit a corrupt/incomplete persisted cable.
            await using (var check = Cmd(db, tx, """
                SELECT EXISTS(SELECT 1 FROM inventory_connection c WHERE c.systemhaus_id=@house AND c.customer_id=@customer
                  AND (SELECT count(*) FROM inventory_connection_endpoint e WHERE e.systemhaus_id=c.systemhaus_id
                    AND e.customer_id=c.customer_id AND e.connection_id=c.id)<>2)
                """, ("house", actor.HouseId), ("customer", customer)))
                if (await check.ExecuteScalarAsync(ct) is true) throw new DomainError(422, "report_source_invalid");
            string snapshot = await Snapshot(db, tx, actor, customer, ct);
            string generatedAt = DateTimeOffset.UtcNow.ToString("yyyy-MM-dd'T'HH:mm:ss.fff'Z'", CultureInfo.InvariantCulture);
            var (html, deviceCount, connectionCount) = BuildRc9ExcelReport(customer, customerName, revision, rack, generatedAt, snapshot);
            Guid operationId = Guid.NewGuid();
            var report = new InventoryRc9ExcelReport(Rc9ExcelFormat, Rc9ExcelCells, rack, generatedAt,
                $"rackclick-rack-{rack:D}-r{revision.ToString(CultureInfo.InvariantCulture)}.xls", Rc9ExcelMime,
                deviceCount, connectionCount, 10, deviceCount + connectionCount + 10, html.Length,
                Convert.ToHexStringLower(SHA256.HashData(html)), Convert.ToBase64String(html));
            var result = new InventoryRc9ExcelResult("rc9ExcelReport", customer, revision, requestId, operationId, report);
            string metadata = JsonSerializer.Serialize(new { customerId = customer, sourceRevision = revision, rackId = rack,
                report.GeneratedAt, report.DeviceCount, report.ConnectionCount, report.SummaryCount, report.RowCount,
                report.ByteLength, report.Sha256, format = Rc9ExcelFormat, cellEncoding = Rc9ExcelCells }, Json);
            await Exec(db, tx, "INSERT INTO audit_event(id,systemhaus_id,actor_id,request_id,action,resource_id,before_json,after_json) VALUES(@id,@house,@actor,@request,'reports.xlsHtml.generate',@customer,NULL,CAST(@metadata AS jsonb))", ct,
                ("id", operationId), ("house", actor.HouseId), ("actor", actor.Id), ("request", requestId), ("customer", customer), ("metadata", metadata));
            await Exec(db, tx, "INSERT INTO operation(systemhaus_id,actor_id,request_id,request_hash,result_json) VALUES(@house,@actor,@request,@hash,CAST(@result AS jsonb))", ct,
                ("house", actor.HouseId), ("actor", actor.Id), ("request", requestId), ("hash", digest), ("result", JsonSerializer.Serialize(result, Json)));
            await RequireReportAuthorization(db, tx, actor, customer, ct);
            await tx.CommitAsync(ct);
            return result;
        }
        catch (PostgresException e) when (e.SqlState is "23503" or "23505" or "23514") { throw new DomainError(409, "report_conflict"); }
    }

    public async Task<InventoryRc9ExcelStatus> Rc9ExcelReportStatus(Actor actor, Guid customer, Guid requestId, CancellationToken ct)
    {
        if (requestId == Guid.Empty) throw new DomainError(422, "request_id_invalid");
        await using var db = await source.OpenConnectionAsync(ct);
        await using var tx = await db.BeginTransactionAsync(System.Data.IsolationLevel.ReadCommitted, ct);
        await PostgresStore.LockOperation(db, tx, actor, requestId, ct, allowReport: true);
        await RequireRead(db, tx, actor, customer, ct);
        await using (var command = Cmd(db, tx, "SELECT id FROM customer WHERE systemhaus_id=@house AND id=@customer FOR SHARE",
            ("house", actor.HouseId), ("customer", customer)))
            if (await command.ExecuteScalarAsync(ct) is not Guid) throw new DomainError(404, "not_found");
        await RequireReportAuthorization(db, tx, actor, customer, ct);
        InventoryRc9ExcelResult? result = null;
        await using (var command = Cmd(db, tx, "SELECT result_json::text FROM operation WHERE systemhaus_id=@house AND actor_id=@actor AND request_id=@request",
            ("house", actor.HouseId), ("actor", actor.Id), ("request", requestId)))
            if (await command.ExecuteScalarAsync(ct) is string json) result = StoredRc9Excel(json, customer, requestId);
        await RequireReportAuthorization(db, tx, actor, customer, ct);
        await tx.CommitAsync(ct);
        return new(result is null ? "notRecorded" : "committed", customer, requestId, result);
    }

    // Closed grammar FINAL02: evidence/.../backend/GRAMATICA-v1-FINAL02.json. Only fixed markup is emitted.
    private const string Rc9ExcelPrefix = """
        <!DOCTYPE html><html xmlns="http://www.w3.org/TR/REC-html40" xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:x="urn:schemas-microsoft-com:office:excel"><head><meta charset="utf-8"><style>td,th{mso-number-format:"\@";white-space:pre-wrap}</style><!--[if gte mso 9]><xml><x:ExcelWorkbook><x:ExcelWorksheets><x:ExcelWorksheet><x:Name>Devices</x:Name><x:WorksheetOptions><x:DisplayGridlines/></x:WorksheetOptions></x:ExcelWorksheet><x:ExcelWorksheet><x:Name>Connections</x:Name><x:WorksheetOptions><x:DisplayGridlines/></x:WorksheetOptions></x:ExcelWorksheet><x:ExcelWorksheet><x:Name>Summary</x:Name><x:WorksheetOptions><x:DisplayGridlines/></x:WorksheetOptions></x:ExcelWorksheet></x:ExcelWorksheets></x:ExcelWorkbook></xml><![endif]--></head>
        """;
    private static readonly string[] Rc9DeviceHeaders = ["Name", "Preset", "Size (U)", "Ports", "Connected", "Icon", "Color"],
        Rc9ConnectionHeaders = ["From Device", "From Port#", "From Type", "From Label", "To Device", "To Port#", "To Type", "To Label", "Cable/Note", "Cross-Rack", "Color", "Created"],
        Rc9SummaryKeys = ["Rack Name", "Location", "Size", "Used", "Free", "Devices", "Connections", "Project", "Technician", "Exported"];

    private sealed class Rc9ExcelWriter : IDisposable
    {
        private readonly MemoryStream output = new();
        private static readonly UTF8Encoding Utf8 = new(false, true);
        public void Raw(string text)
        {
            int count = Utf8.GetByteCount(text);
            if (output.Length + count > ReportMaximumBytes) throw new DomainError(422, "report_too_large");
            output.Write(Utf8.GetBytes(text));
        }
        public void Text(string text, bool attribute = false)
        {
            if (text.Length > 32767) throw new DomainError(422, "report_too_large");
            for (int i = 0; i < text.Length; i++)
            {
                char c = text[i];
                if (char.IsSurrogate(c))
                {
                    if (!char.IsHighSurrogate(c) || i + 1 == text.Length || !char.IsLowSurrogate(text[i + 1]))
                        throw new DomainError(422, "report_cell_invalid");
                    int scalar = char.ConvertToUtf32(c, text[i + 1]);
                    if ((scalar & 0xffff) is 0xfffe or 0xffff) throw new DomainError(422, "report_cell_invalid");
                    i++; continue;
                }
                if ((c < 32 && c is not ('\t' or '\r' or '\n')) || c is >= '\u007f' and <= '\u009f' or '\ufffe' or '\uffff')
                    throw new DomainError(422, "report_cell_invalid");
            }
            string escaped = text.Replace("&", "&amp;", StringComparison.Ordinal).Replace("<", "&lt;", StringComparison.Ordinal)
                .Replace(">", "&gt;", StringComparison.Ordinal).Replace("\"", "&quot;", StringComparison.Ordinal).Replace("'", "&#39;", StringComparison.Ordinal);
            // Excel takes the literal value from x:str. Numeric whitespace entities
            // preserve TAB/CR/LF there; HTML attribute whitespace would otherwise fold.
            if (attribute) escaped = escaped.Replace("\t", "&#9;", StringComparison.Ordinal)
                .Replace("\r", "&#13;", StringComparison.Ordinal).Replace("\n", "&#10;", StringComparison.Ordinal);
            Raw(escaped);
        }
        public void Attr(string name, string value) { Raw(" " + name + "=\""); Text(value, attribute: true); Raw("\""); }
        public void Cell(string value)
        {
            Raw("<td x:str=\""); Text(value, attribute: true); Raw("\">"); Text(value); Raw("</td>");
        }
        public void Table(string name, string[] headers)
        {
            Raw("<table x:str=\"\" border=\"1\" data-table=\"" + name + "\"><thead><tr>");
            foreach (string header in headers) { Raw("<th x:str>"); Text(header); Raw("</th>"); }
            Raw("</tr></thead><tbody>");
        }
        public void EndTable() => Raw("</tbody></table>");
        public byte[] Bytes() => output.ToArray();
        public void Dispose() => output.Dispose();
    }

    private static (byte[] Bytes, int Devices, int Connections) BuildRc9ExcelReport(Guid customer, string customerName,
        long revision, Guid rackId, string generatedAt, string snapshot)
    {
        try
        {
            using var document = JsonDocument.Parse(snapshot);
            var root = document.RootElement;
            static Guid Id(JsonElement e, string key = "id") => e.GetProperty(key).GetGuid();
            static Guid? Parent(JsonElement e, string key) => e.GetProperty(key).ValueKind == JsonValueKind.Null ? null : Id(e, key);
            static string S(JsonElement e, string key) => e.GetProperty(key).GetString() ?? "";
            static string Num(long n) => n.ToString(CultureInfo.InvariantCulture);
            Dictionary<Guid, JsonElement> Map(string key) => root.GetProperty(key).EnumerateArray().ToDictionary(e => Id(e));
            var racks = Map("racks"); var rooms = Map("rooms"); var devices = Map("devices"); var ports = Map("ports"); var groups = Map("portGroups");
            if (!racks.TryGetValue(rackId, out var rack)) throw new DomainError(404, "not_found");
            var selected = devices.Values.Where(d => Parent(d, "rackId") == rackId).ToArray(); // snapshot sort_order,id preserved
            var selectedIds = selected.Select(d => Id(d)).ToHashSet();
            var cables = root.GetProperty("connections").EnumerateArray().Where(c =>
            {
                Guid a = Id(c, "fromPortId"), b = Id(c, "toPortId");
                if (!ports.TryGetValue(a, out var from) || !ports.TryGetValue(b, out var to)) throw new DomainError(422, "report_source_invalid");
                return selectedIds.Contains(Id(from, "deviceId")) || selectedIds.Contains(Id(to, "deviceId"));
            }).ToArray();
            if (selected.Length + cables.Length + 10 > ReportMaximumRows) throw new DomainError(422, "report_too_large");
            var cableIds = new HashSet<Guid>(); var occupied = new HashSet<Guid>();
            string Prop(JsonElement e, string key, string fallback)
            {
                var props = e.GetProperty("properties");
                if (!props.TryGetProperty(key, out var value) || value.ValueKind == JsonValueKind.Null) return fallback;
                if (value.ValueKind != JsonValueKind.String) throw new DomainError(422, "report_source_invalid");
                string text = value.GetString()!; return text.Length == 0 ? fallback : text;
            }
            (JsonElement Port, JsonElement Device, JsonElement Group) Endpoint(Guid portId)
            {
                var p = ports[portId]; var d = devices[Id(p, "deviceId")]; var g = groups[Id(p, "groupId")];
                string type = S(p, "type"), groupType = S(g, "type");
                if (!InventoryRules.PortTypes.Contains(type, StringComparer.Ordinal) || Id(g, "deviceId") != Id(d) ||
                    (type == "rj45_poe" ? "rj45" : type) != groupType)
                    throw new DomainError(422, "report_source_invalid");
                Guid? r = Parent(d, "rackId"), room = Parent(d, "roomId");
                if (r.HasValue ? !racks.ContainsKey(r.Value) || room.HasValue || S(d, "kind") != "rackEquipment" :
                    !room.HasValue || !rooms.ContainsKey(room.Value) || S(d, "kind") is not ("dose" or "endDevice"))
                    throw new DomainError(422, "report_source_invalid");
                return (p, d, g);
            }
            string Location(JsonElement d) => Parent(d, "rackId") is Guid r ? S(racks[r], "name") :
                $"Room: {S(rooms[Id(d, "roomId")], "name")} [{Id(d, "roomId"):D}] / {S(d, "name")}";
            using var html = new Rc9ExcelWriter();
            html.Raw(Rc9ExcelPrefix + "<body"); html.Attr("data-format", Rc9ExcelFormat); html.Attr("data-customer-id", customer.ToString("D"));
            html.Attr("data-rack-id", rackId.ToString("D")); html.Attr("data-revision", Num(revision)); html.Raw(">");
            html.Table("Devices", Rc9DeviceHeaders);
            long used = 0;
            foreach (var d in selected)
            {
                Guid id = Id(d); long size = d.GetProperty("sizeU").GetInt64(); used = checked(used + size);
                if (size <= 0 || S(d, "kind") != "rackEquipment" || Parent(d, "roomId").HasValue) throw new DomainError(422, "report_source_invalid");
                int incident = cables.Count(c => Id(ports[Id(c, "fromPortId")], "deviceId") == id || Id(ports[Id(c, "toPortId")], "deviceId") == id);
                html.Raw("<tr"); html.Attr("data-device-id", id.ToString("D")); html.Raw(">");
                foreach (string value in new[] { S(d, "name"), Prop(d, "preset", ""), Num(size), Num(ports.Values.Count(p => Id(p, "deviceId") == id)), Num(incident),
                    Prop(d, "icon", "▥"), Prop(d, "color", "#457b9d") }) html.Cell(value);
                html.Raw("</tr>");
            }
            html.EndTable(); html.Table("Connections", Rc9ConnectionHeaders);
            foreach (var c in cables)
            {
                Guid id = Id(c), aId = Id(c, "fromPortId"), bId = Id(c, "toPortId");
                if (!cableIds.Add(id) || aId == bId || !occupied.Add(aId) || !occupied.Add(bId)) throw new DomainError(422, "report_source_invalid");
                var a = Endpoint(aId); var b = Endpoint(bId);
                string created;
                var props = c.GetProperty("properties");
                if (props.TryGetProperty("createdAt", out var legacy) && legacy.ValueKind != JsonValueKind.Null)
                    created = legacy.ValueKind == JsonValueKind.String ? legacy.GetString()! : throw new DomainError(422, "report_source_invalid");
                else created = DateTimeOffset.Parse(S(c, "createdAt"), CultureInfo.InvariantCulture, DateTimeStyles.RoundtripKind)
                    .ToUniversalTime().ToString("yyyy-MM-dd'T'HH:mm:ss.fff'Z'", CultureInfo.InvariantCulture);
                html.Raw("<tr"); html.Attr("data-connection-id", id.ToString("D"));
                void EndpointAttrs(string side, (JsonElement Port, JsonElement Device, JsonElement Group) e)
                {
                    html.Attr("data-" + side + "-device-id", Id(e.Device).ToString("D")); html.Attr("data-" + side + "-port-id", Id(e.Port).ToString("D"));
                    html.Attr("data-" + side + "-group-id", Id(e.Group).ToString("D")); html.Attr("data-" + side + "-group-type", S(e.Group, "type"));
                }
                EndpointAttrs("from", a); EndpointAttrs("to", b); html.Raw(">");
                bool local = Parent(a.Device, "rackId") is Guid ar && Parent(b.Device, "rackId") == ar;
                string cross = local ? "" : Location(a.Device) + " → " + Location(b.Device);
                foreach (string value in new[] { S(a.Device, "name"), Num(a.Port.GetProperty("gn").GetInt64()), S(a.Port, "type"), S(a.Port, "label"),
                    S(b.Device, "name"), Num(b.Port.GetProperty("gn").GetInt64()), S(b.Port, "type"), S(b.Port, "label"), S(c, "note"), cross, S(c, "color"), created }) html.Cell(value);
                html.Raw("</tr>");
            }
            html.EndTable(); html.Table("Summary", ["Property", "Value"]);
            long capacity = rack.GetProperty("sizeU").GetInt64();
            string[] values = [S(rack, "name"), S(rack, "location"), Num(capacity) + "U", Num(used) + "U", Num(checked(capacity - used)) + "U",
                Num(selected.Length), Num(cables.Length), customerName, "", generatedAt];
            for (int i = 0; i < Rc9SummaryKeys.Length; i++) { html.Raw("<tr>"); html.Cell(Rc9SummaryKeys[i]); html.Cell(values[i]); html.Raw("</tr>"); }
            html.EndTable(); html.Raw("</body></html>");
            return (html.Bytes(), selected.Length, cables.Length);
        }
        catch (Exception e) when (e is KeyNotFoundException or InvalidOperationException or FormatException or ArgumentException or OverflowException or JsonException)
        { throw new DomainError(422, "report_source_invalid"); }
    }
}
