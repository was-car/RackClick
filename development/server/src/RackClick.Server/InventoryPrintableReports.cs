using System.Globalization;
using System.Security.Cryptography;
using System.Text;
using System.Text.Encodings.Web;
using System.Text.Json;
using Npgsql;
using RackClick.Domain;

namespace RackClick.Server;

public sealed record InventoryPrintableReport(string ReportKind, string Language, Guid[] RackIds,
    string Filename, string ContentType, string Encoding, string TemplateVersion,
    int RowCount, int ByteLength, string Sha256, string ContentBase64);
public sealed record InventoryPrintableResult(string Kind, Guid CustomerId, long Revision, Guid RequestId,
    Guid OperationId, InventoryPrintableReport Report);
public sealed record InventoryPrintableStatus(string State, Guid CustomerId, Guid RequestId, InventoryPrintableResult? Operation);

public sealed partial class InventoryStore
{
    private sealed record PrintableFilter(string ReportKind, string Language, Guid[] RackIds);
    private const string PrintableContentType = "text/html; charset=utf-8", PrintableEncoding = "utf-8",
        PrintableTemplateVersion = "rackclick-print-v1";
    private const string PrintableCsp = "default-src 'none'; script-src 'none'; style-src 'unsafe-inline'; img-src 'none'; " +
        "font-src 'none'; connect-src 'none'; object-src 'none'; frame-src 'none'; base-uri 'none'; form-action 'none'";

    private static PrintableFilter ParsePrintableFilter(JsonElement input)
    {
        try
        {
            var payload = InventoryJson.Object(input);
            string[] keys = ["reportKind", "language", "rackIds"];
            if (payload.Count != keys.Length || keys.Any(k => !payload.ContainsKey(k))) throw new DomainError(422, "request_invalid");
            string kind = InventoryJson.String(payload, "reportKind"), language = InventoryJson.String(payload, "language");
            if (kind is not ("rack" or "client" or "rackLabels") || language is not ("en" or "de" or "es"))
                throw new DomainError(422, "request_invalid");
            var ids = InventoryJson.Array(payload, "rackIds", 64).Select(node =>
                node is not null && node.GetValueKind() == JsonValueKind.String &&
                Guid.TryParseExact(node.GetValue<string>(), "D", out Guid id) && id != Guid.Empty
                    ? id : throw new DomainError(422, "request_invalid")).ToArray();
            if (ids.Distinct().Count() != ids.Length || (kind == "rack" && ids.Length != 1) ||
                (kind == "client" && ids.Length != 0) || (kind == "rackLabels" && ids.Length == 0))
                throw new DomainError(422, "request_invalid");
            return new(kind, language, ids.OrderBy(id => id.ToString("D"), StringComparer.Ordinal).ToArray());
        }
        catch (Exception e) when (e is DomainError or ArgumentException or InvalidOperationException or JsonException)
        { throw new DomainError(422, "request_invalid"); }
    }

    private static InventoryPrintableResult StoredPrintableReport(string json, Guid customer, Guid request)
    {
        try
        {
            var result = JsonSerializer.Deserialize<InventoryPrintableResult>(json, Json);
            if (result is null || result.Kind != "report" || result.CustomerId != customer || result.RequestId != request ||
                result.Report is null || result.Report.ReportKind is not ("rack" or "client" or "rackLabels") ||
                result.Report.Language is not ("en" or "de" or "es") || result.Report.RackIds is null ||
                result.Report.ContentType != PrintableContentType || result.Report.Encoding != PrintableEncoding ||
                result.Report.TemplateVersion != PrintableTemplateVersion)
                throw new DomainError(404, "not_found");
            return result;
        }
        catch (JsonException) { throw new DomainError(404, "not_found"); }
    }

    public async Task<InventoryPrintableResult> GeneratePrintableReport(Actor actor, Guid customer, JsonElement input,
        long expected, Guid requestId, CancellationToken ct)
    {
        var filter = ParsePrintableFilter(input);
        if (requestId == Guid.Empty) throw new DomainError(422, "request_id_invalid");
        string digest = Secrets.Digest(JsonSerializer.Serialize(new { action = "reports.printable.generate", customerId = customer, filter, expected }, Json));
        await using var db = await source.OpenConnectionAsync(ct);
        await using var tx = await db.BeginTransactionAsync(System.Data.IsolationLevel.ReadCommitted, ct);
        try
        {
            await PostgresStore.LockOperation(db, tx, actor, requestId, ct, allowReport: true);
            await RequireRead(db, tx, actor, customer, ct);
            long revision;
            string customerName;
            await using (var command = Cmd(db, tx, "SELECT revision,name FROM customer WHERE systemhaus_id=@house AND id=@customer FOR SHARE",
                ("house", actor.HouseId), ("customer", customer)))
            await using (var row = await command.ExecuteReaderAsync(ct))
            {
                if (!await row.ReadAsync(ct)) throw new DomainError(404, "not_found");
                revision = row.GetInt64(0); customerName = row.GetString(1);
            }
            await RequireReportAuthorization(db, tx, actor, customer, ct);
            await OperationCancellation.EnsureNotCanceled(db, tx, actor, requestId, digest, ct);
            InventoryPrintableResult? committed = null;
            await using (var command = Cmd(db, tx, "SELECT request_hash,result_json::text FROM operation WHERE systemhaus_id=@house AND actor_id=@actor AND request_id=@request",
                ("house", actor.HouseId), ("actor", actor.Id), ("request", requestId)))
            await using (var row = await command.ExecuteReaderAsync(ct))
                if (await row.ReadAsync(ct))
                {
                    if (row.GetString(0) != digest) throw new DomainError(409, "request_id_reused");
                    committed = StoredPrintableReport(row.GetString(1), customer, requestId);
                }
            if (committed is not null)
            {
                await RequireReportAuthorization(db, tx, actor, customer, ct);
                await tx.CommitAsync(ct);
                return committed;
            }
            Revisions.Require(expected, revision);
            string snapshot = await Snapshot(db, tx, actor, customer, ct);
            var (html, rows) = BuildPrintableReport(customer, customerName, revision, filter, snapshot);
            Guid operationId = Guid.NewGuid();
            var report = new InventoryPrintableReport(filter.ReportKind, filter.Language, filter.RackIds,
                $"rackclick-{filter.ReportKind}-{customer:D}-r{revision.ToString(CultureInfo.InvariantCulture)}-{filter.Language}.html",
                PrintableContentType, PrintableEncoding, PrintableTemplateVersion, rows, html.Length,
                Convert.ToHexStringLower(SHA256.HashData(html)), Convert.ToBase64String(html));
            var result = new InventoryPrintableResult("report", customer, revision, requestId, operationId, report);
            string metadata = JsonSerializer.Serialize(new { customerId = customer, sourceRevision = revision,
                filter.ReportKind, filter.Language, filter.RackIds, report.RowCount, report.ByteLength, report.Sha256,
                templateVersion = PrintableTemplateVersion }, Json);
            await Exec(db, tx, "INSERT INTO audit_event(id,systemhaus_id,actor_id,request_id,action,resource_id,before_json,after_json) VALUES(@id,@house,@actor,@request,'reports.printable.generate',@customer,NULL,CAST(@metadata AS jsonb))", ct,
                ("id", operationId), ("house", actor.HouseId), ("actor", actor.Id), ("request", requestId), ("customer", customer), ("metadata", metadata));
            await Exec(db, tx, "INSERT INTO operation(systemhaus_id,actor_id,request_id,request_hash,result_json) VALUES(@house,@actor,@request,@hash,CAST(@result AS jsonb))", ct,
                ("house", actor.HouseId), ("actor", actor.Id), ("request", requestId), ("hash", digest), ("result", JsonSerializer.Serialize(result, Json)));
            await RequireReportAuthorization(db, tx, actor, customer, ct);
            await tx.CommitAsync(ct);
            return result;
        }
        catch (PostgresException e) when (e.SqlState is "23503" or "23505" or "23514") { throw new DomainError(409, "report_conflict"); }
    }

    public async Task<InventoryPrintableStatus> PrintableReportStatus(Actor actor, Guid customer, Guid requestId, CancellationToken ct)
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
        InventoryPrintableResult? result = null;
        await using (var command = Cmd(db, tx, "SELECT result_json::text FROM operation WHERE systemhaus_id=@house AND actor_id=@actor AND request_id=@request",
            ("house", actor.HouseId), ("actor", actor.Id), ("request", requestId)))
            if (await command.ExecuteScalarAsync(ct) is string json) result = StoredPrintableReport(json, customer, requestId);
        await RequireReportAuthorization(db, tx, actor, customer, ct);
        await tx.CommitAsync(ct);
        return new(result is null ? "notRecorded" : "committed", customer, requestId, result);
    }

    // CSS uses the adopted RC9 report palette, table rules and 336px/16px rack-label geometry.
    // Fonts are local fallbacks. This tabular template does not claim the approved graphical rack SVG.
    private const string PrintableCss = """
        *{box-sizing:border-box}body{background:#fff;color:#152b3c;margin:0;font-family:Arial,sans-serif}
        main{padding:32px;max-width:1200px;margin:auto}header{border-bottom:3px solid #08794e;padding-bottom:15px}
        header>b{font-size:26px;font-weight:600;color:#08794e}h1{font-size:26px}h2{font-size:18px;margin-top:24px}
        p{overflow-wrap:anywhere}table{width:100%;border-collapse:collapse;font-size:12px;margin-bottom:24px;table-layout:fixed}
        th,td{border:1px solid #a4b1bc;padding:7px;text-align:left;vertical-align:top;overflow-wrap:anywhere;white-space:pre-wrap}
        th{background:#edf2f5}tr{break-inside:avoid}small{display:block;font-size:9px;overflow-wrap:anywhere}
        .ir-port-table th:nth-child(1){width:35%}.ir-port-table th:nth-child(2){width:30%}
        .ir-port-table th:nth-child(3){width:20%}.ir-port-table th:nth-child(4){width:15%}
        .ir-label-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(336px,100%),336px));gap:16px;justify-content:start}
        .ir-batch-label{width:336px;max-width:100%;border:2px solid #111;border-radius:8px;padding:16px;font-family:monospace;background:#fff;color:#111;break-inside:avoid;page-break-inside:avoid;overflow-wrap:anywhere}
        .ir-label-title{font-size:18px;font-weight:900;letter-spacing:1px;margin-bottom:4px}.ir-label-location{font-size:11px;color:#666;margin-bottom:8px}
        .ir-label-info{font-size:10px;color:#333;margin-bottom:6px;display:flex;gap:12px;flex-wrap:wrap}
        .ir-label-id{border:1.5px solid #000;border-radius:4px;padding:6px 10px;margin:8px 0;font-size:13px;font-weight:900;letter-spacing:2px;text-align:center;background:#fff;color:#000}
        .ir-label-footer{font-size:9px;color:#555;border-top:1px solid #ddd;padding-top:6px;margin-top:8px}
        @media(max-width:700px){main{padding:12px}.ir-label-grid{grid-template-columns:1fr}}
        @page{size:A4 portrait;margin:12mm}
        @media print{main{padding:12px;max-width:none}body{background:#fff}thead{display:table-header-group}table{font-size:9px}
        .ir-label-grid{grid-template-columns:repeat(2,minmax(0,336px));gap:16px}.ir-batch-label{border:2px solid #000;break-inside:avoid;page-break-inside:avoid}}
        """;

    private sealed class PrintableWriter : IDisposable
    {
        private readonly MemoryStream output = new();
        public int Rows { get; private set; }
        public void Raw(string value) => Raw(value.AsSpan());
        private void Raw(ReadOnlySpan<char> value)
        {
            int length = Encoding.UTF8.GetByteCount(value);
            if (output.Length + length > ReportMaximumBytes) throw new DomainError(422, "report_too_large");
            byte[] bytes = new byte[length];
            Encoding.UTF8.GetBytes(value, bytes);
            output.Write(bytes);
        }
        private sealed class EncodedWriter(PrintableWriter owner) : TextWriter
        {
            public override Encoding Encoding => System.Text.Encoding.UTF8;
            public override void Write(char value) => owner.Raw(value.ToString());
            public override void Write(string? value) { if (value is not null) owner.Raw(value); }
            public override void Write(char[] buffer, int index, int count) => owner.Raw(buffer.AsSpan(index, count));
            public override void Write(ReadOnlySpan<char> buffer) => owner.Raw(buffer);
        }
        public void Text(string? value)
        {
            // Encode directly into the bounded sink, never construct an unbounded escaped document/string.
            using var writer = new EncodedWriter(this);
            HtmlEncoder.Default.Encode(writer, value ?? "");
        }
        public void Row(string kind, Guid id, bool label = false)
        {
            if (++Rows > ReportMaximumRows) throw new DomainError(422, "report_too_large");
            Raw(label ? "<section class=\"ir-batch-label\"" : "<tr");
            Raw(" data-report-row=\""); Text(kind); Raw("\" data-id=\""); Text(id.ToString("D")); Raw("\">");
        }
        public void Cell(string? value) { Raw("<td>"); Text(value); Raw("</td>"); }
        public byte[] Bytes() => output.ToArray();
        public void Dispose() => output.Dispose();
    }

    private static (byte[] Bytes, int Rows) BuildPrintableReport(Guid customer, string customerName, long revision, PrintableFilter filter, string snapshot)
    {
        using var document = JsonDocument.Parse(snapshot);
        var root = document.RootElement;
        JsonElement[] All(string key) => root.GetProperty(key).EnumerateArray().ToArray();
        static Guid Id(JsonElement e, string key = "id") => e.GetProperty(key).GetGuid();
        static string S(JsonElement e, string key) => e.GetProperty(key).GetString() ?? "";
        static string Number(JsonElement e, string key) => e.GetProperty(key).ValueKind == JsonValueKind.Null ? "—" : e.GetProperty(key).GetRawText();
        static Guid? Parent(JsonElement e, string key) => e.GetProperty(key).ValueKind == JsonValueKind.Null ? null : Id(e, key);
        string L(string en, string de, string es) => filter.Language == "de" ? de : filter.Language == "es" ? es : en;
        var sites = All("sites").ToDictionary(e => Id(e)); var buildings = All("buildings").ToDictionary(e => Id(e));
        var rooms = All("rooms").ToDictionary(e => Id(e)); var racks = All("racks").ToDictionary(e => Id(e));
        var devices = All("devices").ToDictionary(e => Id(e)); var groups = All("portGroups").ToDictionary(e => Id(e));
        var rawPorts = All("ports").ToDictionary(e => Id(e)); var rawConnections = All("connections");
        if (filter.RackIds.Any(id => !racks.ContainsKey(id))) throw new DomainError(404, "not_found");
        if (filter.ReportKind == "client" && racks.Count > 20) throw new DomainError(422, "report_too_large");
        string Path(string kind, Guid id)
        {
            var entity = kind switch { "site" => sites[id], "building" => buildings[id], "room" => rooms[id], "rack" => racks[id], "device" => devices[id], _ => throw new InvalidOperationException() };
            (string Kind, Guid? Id) parent = kind switch {
                "building" => ("site", Id(entity, "siteId")), "room" => ("building", Id(entity, "buildingId")),
                "rack" => ("room", Parent(entity, "roomId")), "device" => Parent(entity, "rackId") is Guid rack ? ("rack", rack) : ("room", Parent(entity, "roomId")),
                _ => ("site", null) };
            return (parent.Id.HasValue ? Path(parent.Kind, parent.Id.Value) + " / " : "") + S(entity, "name");
        }
        string PortText(InventoryPortView p) => string.Join(" / ", p.Path.Select(n => n.Name)) + "\n" +
            L("Label", "Beschriftung", "Etiqueta") + ": " + p.Label + "\n" + L("Group", "Gruppe", "Grupo") + ": " + p.GroupName + "\n" +
            $"{p.Type} #{p.Gn.ToString(CultureInfo.InvariantCulture)} · {p.Face}\nport: {p.Id:D}\ndevice: {p.DeviceId:D}\ngroup: {p.GroupId:D}\n" +
            $"rack: {p.RackId?.ToString("D") ?? "—"}\nroom: {p.RoomId?.ToString("D") ?? "—"}";
        string title = filter.ReportKind switch {
            "rack" => L("Rack report · tables", "Rackbericht · Tabellen", "Informe de rack · tablas"),
            "client" => L("Customer report · tables", "Kundenbericht · Tabellen", "Informe de cliente · tablas"),
            _ => L("Rack labels", "Rack-Etiketten", "Etiquetas de racks") };
        using var html = new PrintableWriter();
        html.Raw("<!doctype html><html lang=\""); html.Text(filter.Language); html.Raw("\"><head><meta charset=\"utf-8\"><meta http-equiv=\"Content-Security-Policy\" content=\"");
        html.Text(PrintableCsp); html.Raw("\"><meta name=\"rackclick-template\" content=\""); html.Text(PrintableTemplateVersion);
        html.Raw("\"><meta name=\"referrer\" content=\"no-referrer\"><meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"><title>");
        html.Text(title + " · " + customerName); html.Raw("</title><style>"); html.Raw(PrintableCss); html.Raw("</style></head><body data-report-kind=\"");
        html.Text(filter.ReportKind); html.Raw("\"><main class=\"ir-client-report\"><header><b>RackClick</b><h1>");
        html.Text(title); html.Raw("</h1><p>"); html.Text(customerName); html.Raw("</p><p>");
        html.Text(L("Customer", "Kunde", "Cliente") + ": " + customer.ToString("D") + " · " +
            L("Source revision", "Quellrevision", "Revisión fuente") + ": " + revision.ToString(CultureInfo.InvariantCulture));
        html.Raw("</p></header>");
        void Table(string section, string heading, params string[] headers)
        {
            html.Raw("<section data-report-section=\""); html.Text(section); html.Raw("\"><h2>"); html.Text(heading); html.Raw("</h2><table");
            if (section == "ports") html.Raw(" class=\"ir-port-table\"");
            html.Raw("><thead><tr>");
            foreach (string header in headers) { html.Raw("<th scope=\"col\">"); html.Text(header); html.Raw("</th>"); }
            html.Raw("</tr></thead><tbody>");
        }
        void EndTable() => html.Raw("</tbody></table></section>");
        void Identity(JsonElement e) => html.Cell(S(e, "name") + "\n" + Id(e).ToString("D"));
        if (filter.ReportKind == "rackLabels")
        {
            html.Raw("<div class=\"ir-label-grid\">");
            foreach (Guid rackId in filter.RackIds)
            {
                var rack = racks[rackId];
                var deviceIds = devices.Values.Where(d => Parent(d, "rackId") == rackId).Select(d => Id(d)).ToHashSet();
                var portIds = rawPorts.Values.Where(p => deviceIds.Contains(Id(p, "deviceId"))).Select(p => Id(p)).ToHashSet();
                int cables = rawConnections.Count(c => portIds.Contains(Id(c, "fromPortId")) || portIds.Contains(Id(c, "toPortId")));
                html.Row("rack-label", rackId, label: true); html.Raw("<div class=\"ir-label-title\">"); html.Text("RACK: " + S(rack, "name"));
                html.Raw("</div><div class=\"ir-label-location\">"); html.Text(Path("rack", rackId));
                if (S(rack, "location").Length != 0) { html.Raw("<br>"); html.Text(S(rack, "location")); }
                html.Raw("</div><div class=\"ir-label-info\"><span>"); html.Text(deviceIds.Count.ToString(CultureInfo.InvariantCulture) + " " + L("Devices", "Geräte", "Equipos"));
                html.Raw("</span><span>"); html.Text(Number(rack, "sizeU") + " U"); html.Raw("</span><span>");
                html.Text(cables.ToString(CultureInfo.InvariantCulture) + " " + L("Connections", "Verbindungen", "Conexiones"));
                html.Raw("</span></div><div class=\"ir-label-id\">"); html.Text(rackId.ToString("D"));
                html.Raw("</div><div class=\"ir-label-footer\">"); html.Text("RackClick | " + customerName + " | " + customer.ToString("D") + " | " +
                    L("Source revision", "Quellrevision", "Revisión fuente") + " " + revision.ToString(CultureInfo.InvariantCulture));
                html.Raw("</div></section>");
            }
            html.Raw("</div>");
        }
        else
        {
            Guid? onlyRack = filter.ReportKind == "rack" ? filter.RackIds[0] : null;
            var ports = ProjectView(customer, revision, "ports", new("", null, "all", "all", 0, ReportMaximumRows + 1), snapshot, paginate: false, rackId: onlyRack);
            var cables = ProjectView(customer, revision, "connections", new("", null, null, null, 0, ReportMaximumRows + 1), snapshot, paginate: false, rackId: onlyRack);
            if (ports.Total > ReportMaximumRows || cables.Total > ReportMaximumRows) throw new DomainError(422, "report_too_large");
            string nameId = L("Name / UUID", "Name / UUID", "Nombre / UUID"), context = L("Location / path", "Standort / Pfad", "Ubicación / ruta");
            if (!onlyRack.HasValue)
            {
                Table("hierarchy", L("Sites, buildings and rooms", "Standorte, Gebäude und Räume", "Sitios, edificios y salas"), L("Kind", "Art", "Clase"), nameId, context);
                foreach (var (kind, map) in new[] { ("site", sites), ("building", buildings), ("room", rooms) })
                    foreach (var e in map.Values.OrderBy(e => Id(e).ToString("D"), StringComparer.Ordinal))
                    { html.Row(kind, Id(e)); html.Cell(kind); Identity(e); html.Cell(Path(kind, Id(e))); html.Raw("</tr>"); }
                EndTable();
            }
            var selectedRacks = racks.Values.Where(r => !onlyRack.HasValue || Id(r) == onlyRack).OrderBy(r => Id(r).ToString("D"), StringComparer.Ordinal).ToArray();
            Table("racks", L("Racks", "Racks", "Racks"), nameId, context, L("Description", "Beschreibung", "Descripción"), "U");
            foreach (var rack in selectedRacks)
            { html.Row("rack", Id(rack)); Identity(rack); html.Cell(Path("rack", Id(rack))); html.Cell(S(rack, "location")); html.Cell(Number(rack, "sizeU")); html.Raw("</tr>"); }
            EndTable();
            var selectedDevices = devices.Values.Where(d => !onlyRack.HasValue || Parent(d, "rackId") == onlyRack).ToArray();
            var selectedDeviceIds = selectedDevices.Select(d => Id(d)).ToHashSet();
            Table("devices", L("Devices", "Geräte", "Equipos"), nameId, L("Kind", "Art", "Clase"), context, "U", L("Order", "Reihenfolge", "Orden"), L("PoE budget (W)", "PoE-Budget (W)", "Presupuesto PoE (W)"));
            foreach (var device in selectedDevices)
            { html.Row("device", Id(device)); Identity(device); html.Cell(S(device, "kind")); html.Cell(Path("device", Id(device))); html.Cell(device.TryGetProperty("mountParentId", out var mountedOn) && mountedOn.ValueKind != JsonValueKind.Null
                    ? "0 " + L("additional U; mounted on", "zusätzliche HE; montiert auf", "U adicionales; montado sobre") + " " + S(devices[mountedOn.GetGuid()], "name") + " [" + mountedOn.GetString() + "] / " + S(device, "mountSlotKey")
                    : Number(device, "sizeU")); html.Cell(Number(device, "sortOrder")); html.Cell(Number(device, "poeBudget")); html.Raw("</tr>"); }
            EndTable();
            Table("groups", L("Port groups", "Portgruppen", "Grupos de puertos"), nameId, L("Device UUID", "Geräte-UUID", "UUID de equipo"), L("Type", "Typ", "Tipo"), L("Prefix", "Präfix", "Prefijo"), L("Order", "Reihenfolge", "Orden"));
            foreach (var group in groups.Values.Where(g => selectedDeviceIds.Contains(Id(g, "deviceId"))))
            { html.Row("group", Id(group)); Identity(group); html.Cell(Id(group, "deviceId").ToString("D")); html.Cell(S(group, "type")); html.Cell(S(group, "prefix")); html.Cell(Number(group, "sortOrder")); html.Raw("</tr>"); }
            EndTable();
            Table("ports", L("Ports", "Ports", "Puertos"), L("Port / group", "Port / Gruppe", "Puerto / grupo"),
                L("Device / location", "Gerät / Standort", "Equipo / ubicación"), L("Technical data", "Technische Daten", "Datos técnicos"),
                L("Connection / peer UUIDs", "Verbindungs- / Gegenstellen-UUIDs", "UUID de conexión / puerto remoto"));
            foreach (var port in ports.Items.Cast<InventoryPortView>())
            {
                // This listing has its own compact identity/location cells. Cable endpoints below retain PortText in full.
                string identity = L("Label", "Beschriftung", "Etiqueta") + ": " + port.Label + $"\nport: {port.Id:D}\n{port.Type} #{port.Gn.ToString(CultureInfo.InvariantCulture)}\n" +
                    L("Group", "Gruppe", "Grupo") + ": " + port.GroupName + $"\ngroup: {port.GroupId:D}";
                string location = port.DeviceName + $"\ndevice: {port.DeviceId:D}\nrack: {port.RackId?.ToString("D") ?? "—"}\nroom: {port.RoomId?.ToString("D") ?? "—"}";
                string technical = L("Status", "Status", "Estado") + ": " + port.Status + "\n" + L("Face", "Seite", "Cara") + ": " + port.Face + " · PoE: " + (port.Poe ? "true" : "false") + "\n" +
                    L("Configured W", "Konfigurierte W", "W configurados") + ": " + (port.Watts?.ToString(CultureInfo.InvariantCulture) ?? "—") + "\n" +
                    L("Color", "Farbe", "Color") + ": " + (port.Color ?? "—") + "\n" + L("Power role", "Versorgungsrolle", "Rol de alimentación") + ": " + port.PowerRole;
                string links = L("Connections", "Verbindungen", "Conexiones") + ":\n" + (port.ConnectionIds.Length == 0 ? "—" : string.Join("\n", port.ConnectionIds.Select(id => id.ToString("D")))) + "\n" +
                    L("Peers", "Gegenstellen", "Puertos remotos") + ":\n" + (port.PeerPortIds.Length == 0 ? "—" : string.Join("\n", port.PeerPortIds.Select(id => id.ToString("D"))));
                html.Row("port", port.Id); html.Cell(identity); html.Cell(location); html.Cell(technical); html.Cell(links); html.Raw("</tr>");
            }
            EndTable();
            Table("connections", L("Connections", "Verbindungen", "Conexiones"), "UUID", L("From", "Von", "Desde"), L("To", "Nach", "Hasta"), L("Note", "Notiz", "Nota"), L("Color / patch / cross-rack", "Farbe / Patch / rackübergreifend", "Color / patch / entre racks"));
            foreach (var cable in cables.Items.Cast<InventoryConnectionView>())
            {
                html.Row("connection", cable.Id); html.Cell(cable.Id.ToString("D")); html.Cell(PortText(cable.From)); html.Cell(PortText(cable.To)); html.Cell(cable.Note);
                html.Cell((cable.Color ?? "") + "\n" + cable.Patch + "\n" + (cable.CrossRack.HasValue ? cable.CrossRack.Value ? "true" : "false" : "—")); html.Raw("</tr>");
            }
            EndTable();
        }
        html.Raw("<footer><small>"); html.Text(PrintableTemplateVersion); html.Raw("</small></footer></main></body></html>");
        return (html.Bytes(), html.Rows);
    }
}
