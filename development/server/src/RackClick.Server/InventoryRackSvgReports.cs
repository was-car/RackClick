using System.Globalization;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Xml;
using Npgsql;
using RackClick.Domain;

namespace RackClick.Server;

public sealed record InventoryRackSvgReport(string ReportKind, Guid RackId, string Face, string Language,
    string Filename, string ContentType, string Encoding, string TemplateVersion,
    int RowCount, int ByteLength, string Sha256, string ContentBase64);
public sealed record InventoryRackSvgResult(string Kind, Guid CustomerId, long Revision, Guid RequestId,
    Guid OperationId, InventoryRackSvgReport Report);
public sealed record InventoryRackSvgStatus(string State, Guid CustomerId, Guid RequestId, InventoryRackSvgResult? Operation);

public sealed partial class InventoryStore
{
    private sealed record RackSvgFilter(Guid RackId, string Face, string Language);
    private const string RackSvgContentType = "image/svg+xml; charset=utf-8", RackSvgEncoding = "utf-8",
        RackSvgTemplateVersion = "rackclick-rack-svg-v1", RackSvgNamespace = "http://www.w3.org/2000/svg";

    private static RackSvgFilter ParseRackSvgFilter(JsonElement input)
    {
        try
        {
            var payload = InventoryJson.Object(input);
            string[] keys = ["rackId", "face", "language"];
            if (payload.Count != keys.Length || keys.Any(k => !payload.ContainsKey(k))) throw new DomainError(422, "request_invalid");
            if (!Guid.TryParseExact(InventoryJson.String(payload, "rackId"), "D", out Guid rack) || rack == Guid.Empty)
                throw new DomainError(422, "request_invalid");
            string face = InventoryJson.String(payload, "face"), language = InventoryJson.String(payload, "language");
            if (face is not ("front" or "rear") || language is not ("en" or "de" or "es")) throw new DomainError(422, "request_invalid");
            return new(rack, face, language);
        }
        catch (Exception e) when (e is DomainError or ArgumentException or InvalidOperationException or JsonException)
        { throw new DomainError(422, "request_invalid"); }
    }

    private static InventoryRackSvgResult StoredRackSvg(string json, Guid customer, Guid request)
    {
        try
        {
            var result = JsonSerializer.Deserialize<InventoryRackSvgResult>(json, Json);
            if (result is null || result.Kind != "report" || result.CustomerId != customer || result.RequestId != request ||
                result.Report is null || result.Report.ReportKind != "rackSvg" || result.Report.RackId == Guid.Empty ||
                result.Report.Face is not ("front" or "rear") || result.Report.Language is not ("en" or "de" or "es") ||
                result.Report.ContentType != RackSvgContentType || result.Report.Encoding != RackSvgEncoding ||
                result.Report.TemplateVersion != RackSvgTemplateVersion) throw new DomainError(404, "not_found");
            return result;
        }
        catch (JsonException) { throw new DomainError(404, "not_found"); }
    }

    public async Task<InventoryRackSvgResult> GenerateRackSvgReport(Actor actor, Guid customer, JsonElement input,
        long expected, Guid requestId, CancellationToken ct)
    {
        var filter = ParseRackSvgFilter(input);
        if (requestId == Guid.Empty) throw new DomainError(422, "request_id_invalid");
        string digest = Secrets.Digest(JsonSerializer.Serialize(new { action = "reports.rackSvg.generate", customerId = customer, filter, expected }, Json));
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
            InventoryRackSvgResult? committed = null;
            await using (var command = Cmd(db, tx, "SELECT request_hash,result_json::text FROM operation WHERE systemhaus_id=@house AND actor_id=@actor AND request_id=@request",
                ("house", actor.HouseId), ("actor", actor.Id), ("request", requestId)))
            await using (var row = await command.ExecuteReaderAsync(ct))
                if (await row.ReadAsync(ct))
                {
                    if (row.GetString(0) != digest) throw new DomainError(409, "request_id_reused");
                    committed = StoredRackSvg(row.GetString(1), customer, requestId);
                }
            if (committed is not null)
            {
                await RequireReportAuthorization(db, tx, actor, customer, ct);
                await tx.CommitAsync(ct);
                return committed;
            }
            Revisions.Require(expected, revision);
            string snapshot = await Snapshot(db, tx, actor, customer, ct);
            var (svg, rows) = BuildRackSvg(customer, customerName, revision, filter, snapshot);
            Guid operationId = Guid.NewGuid();
            var report = new InventoryRackSvgReport("rackSvg", filter.RackId, filter.Face, filter.Language,
                $"rackclick-rackSvg-{customer:D}-{filter.RackId:D}-r{revision.ToString(CultureInfo.InvariantCulture)}-{filter.Face}-{filter.Language}.svg",
                RackSvgContentType, RackSvgEncoding, RackSvgTemplateVersion, rows, svg.Length,
                Convert.ToHexStringLower(SHA256.HashData(svg)), Convert.ToBase64String(svg));
            var result = new InventoryRackSvgResult("report", customer, revision, requestId, operationId, report);
            string metadata = JsonSerializer.Serialize(new { customerId = customer, sourceRevision = revision,
                filter.RackId, filter.Face, filter.Language, report.RowCount, report.ByteLength, report.Sha256,
                templateVersion = RackSvgTemplateVersion }, Json);
            await Exec(db, tx, "INSERT INTO audit_event(id,systemhaus_id,actor_id,request_id,action,resource_id,before_json,after_json) VALUES(@id,@house,@actor,@request,'reports.rackSvg.generate',@customer,NULL,CAST(@metadata AS jsonb))", ct,
                ("id", operationId), ("house", actor.HouseId), ("actor", actor.Id), ("request", requestId), ("customer", customer), ("metadata", metadata));
            await Exec(db, tx, "INSERT INTO operation(systemhaus_id,actor_id,request_id,request_hash,result_json) VALUES(@house,@actor,@request,@hash,CAST(@result AS jsonb))", ct,
                ("house", actor.HouseId), ("actor", actor.Id), ("request", requestId), ("hash", digest), ("result", JsonSerializer.Serialize(result, Json)));
            await RequireReportAuthorization(db, tx, actor, customer, ct);
            await tx.CommitAsync(ct);
            return result;
        }
        catch (PostgresException e) when (e.SqlState is "23503" or "23505" or "23514") { throw new DomainError(409, "report_conflict"); }
    }

    public async Task<InventoryRackSvgStatus> RackSvgReportStatus(Actor actor, Guid customer, Guid requestId, CancellationToken ct)
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
        InventoryRackSvgResult? result = null;
        await using (var command = Cmd(db, tx, "SELECT result_json::text FROM operation WHERE systemhaus_id=@house AND actor_id=@actor AND request_id=@request",
            ("house", actor.HouseId), ("actor", actor.Id), ("request", requestId)))
            if (await command.ExecuteScalarAsync(ct) is string json) result = StoredRackSvg(json, customer, requestId);
        await RequireReportAuthorization(db, tx, actor, customer, ct);
        await tx.CommitAsync(ct);
        return new(result is null ? "notRecorded" : "committed", customer, requestId, result);
    }

    private sealed class RackSvgStream : MemoryStream
    {
        private void Check(int count) { if (Length + count > ReportMaximumBytes) throw new DomainError(422, "report_too_large"); }
        public override void Write(byte[] buffer, int offset, int count) { Check(count); base.Write(buffer, offset, count); }
        public override void Write(ReadOnlySpan<byte> buffer) { Check(buffer.Length); base.Write(buffer); }
        public override void WriteByte(byte value) { Check(1); base.WriteByte(value); }
    }
    private sealed record SvgPort(JsonElement Value, double X, double Y, double Width);
    private sealed record SvgBlock(JsonElement Device, double Top, double Height, string Family, SvgPort[] Ports);
    private static Guid SvgId(JsonElement e, string key = "id") => e.GetProperty(key).GetGuid();
    private static string SvgString(JsonElement e, string key) => e.GetProperty(key).GetString() ?? "";
    private static string SvgPreset(JsonElement d) => d.GetProperty("properties").TryGetProperty("preset", out var p) && p.ValueKind == JsonValueKind.String ? p.GetString() ?? "" : "";
    private static bool SvgContains(string value, params string[] options) => options.Any(value.Contains);
    private static string SvgFace(JsonElement d, JsonElement p)
    {
        string face = SvgString(p, "face");
        if (face is "front" or "rear") return face;
        return SvgContains(SvgPreset(d).ToLowerInvariant(), "server", "srv", "nas", "storage", "san", "ups") || SvgString(p, "type") == "power" ? "rear" : "front";
    }
    private static string SvgColor(JsonElement e, string key, string fallback)
        => e.TryGetProperty(key, out var value) && value.ValueKind == JsonValueKind.String && InventoryRc9Catalog.ValidColor(value.GetString()!) ? value.GetString()! : fallback;
    private static string SvgFamily(string type) => type == "rj45_poe" ? "rj45" : type;
    private static string AbbreviateSvgLabel(string text, double width, double size)
    {
        // Conservative glyph budgets, not a claim about installed font metrics. Keep entire
        // extended grapheme clusters (including emoji/combining sequences), and retain the
        // complete literal original in a child title whenever the visible label is shortened.
        double budget = width / size;
        var elements = new List<(string Text, double Units)>();
        var iterator = StringInfo.GetTextElementEnumerator(text);
        double used = 0;
        while (iterator.MoveNext())
        {
            string element = iterator.GetTextElement();
            double units = element.Length == 1 && element[0] is >= ' ' and <= '~' ? 1 : 2;
            elements.Add((element, units)); used += units;
        }
        if (used <= budget) return text;
        var visible = new StringBuilder(); used = 1; // reserve one em for the ellipsis
        foreach (var element in elements)
        {
            if (used + element.Units > budget) break;
            visible.Append(element.Text); used += element.Units;
        }
        return visible.Append('…').ToString();
    }
    private static SvgBlock LayoutRackSvg(JsonElement device, JsonElement[] ownPorts, string face, double top)
    {
        var groups = ownPorts.Where(p => SvgFace(device, p) == face).GroupBy(p => SvgFamily(SvgString(p, "type"))).Select(g => g.ToArray()).ToArray();
        string preset = SvgPreset(device).ToLowerInvariant();
        string family = SvgContains(preset, "server", "srv", "nas", "storage", "san") ? "storage" : preset.Contains("ups") ? "ups" : "panel";
        double deco = family == "storage" ? face == "front" ? 60 : 72 : family == "ups" ? 38 : 0;
        var dense = groups.FirstOrDefault(g => g.Length >= 20); var ports = new List<SvgPort>();
        double bottom = 26 + deco;
        if (dense is not null)
        {
            var auxiliary = groups.Where(g => !ReferenceEquals(g, dense)).SelectMany(g => g).ToArray();
            double pitch = auxiliary.Length != 0 ? 29 : 37, width = auxiliary.Length != 0 ? 24 : 30;
            for (int i = 0; i < dense.Length; i++) ports.Add(new(dense[i], 40 + i % 24 * pitch, 26 + deco + i / 24 * 44, width));
            for (int i = 0; i < auxiliary.Length; i++) ports.Add(new(auxiliary[i], 760 + i % 4 * 43, 26 + deco + i / 4 * 44, 28));
            bottom += Math.Max(Math.Ceiling(dense.Length / 24.0), Math.Ceiling(auxiliary.Length / 4.0)) * 44;
        }
        else
        {
            double x = 40, y = 26 + deco;
            foreach (var group in groups)
            {
                foreach (var port in group) { if (x + 42 > 920) { x = 40; y += 50; } ports.Add(new(port, x, y, 34)); x += 56; }
                x += 24;
            }
            bottom = y + 45;
        }
        return new(device, top, Math.Max(device.GetProperty("sizeU").GetInt32() * 70, bottom + 12), family, ports.ToArray());
    }

    private static (byte[] Bytes, int Rows) BuildRackSvg(Guid customer, string customerName, long revision, RackSvgFilter filter, string snapshot)
    {
        using var document = JsonDocument.Parse(snapshot);
        var root = document.RootElement;
        JsonElement[] All(string key) => root.GetProperty(key).EnumerateArray().ToArray();
        var rack = All("racks").FirstOrDefault(r => SvgId(r) == filter.RackId);
        if (rack.ValueKind == JsonValueKind.Undefined) throw new DomainError(404, "not_found");
        var allDevices = All("devices").ToDictionary(d => SvgId(d));
        var devices = All("devices").Where(d => d.GetProperty("rackId").ValueKind != JsonValueKind.Null && SvgId(d, "rackId") == filter.RackId)
            .OrderBy(d => d.GetProperty("sortOrder").GetInt32()).ThenBy(d => SvgId(d).ToString("D"), StringComparer.Ordinal).ToArray();
        // This passive SVG format predates nested mounting. Never silently flatten it.
        if (devices.Any(d => d.TryGetProperty("mountParentId", out var parent) && parent.ValueKind != JsonValueKind.Null))
            throw new DomainError(422, "report_mounting_unsupported");
        var deviceIds = devices.Select(d => SvgId(d)).ToHashSet();
        var groups = All("portGroups").Where(g => deviceIds.Contains(SvgId(g, "deviceId"))).ToArray();
        var allGroups = All("portGroups").ToDictionary(g => SvgId(g));
        var allPorts = All("ports").ToDictionary(p => SvgId(p));
        var ports = All("ports").Where(p => deviceIds.Contains(SvgId(p, "deviceId")))
            .OrderBy(p => p.GetProperty("sortOrder").GetInt32()).ThenBy(p => SvgId(p).ToString("D"), StringComparer.Ordinal).ToArray();
        var portIds = ports.Select(p => SvgId(p)).ToHashSet();
        var connections = All("connections").Where(c => portIds.Contains(SvgId(c, "fromPortId")) || portIds.Contains(SvgId(c, "toPortId"))).ToArray();
        int rows = 1 + devices.Length + groups.Length + ports.Length + connections.Length;
        if (rows > ReportMaximumRows) throw new DomainError(422, "report_too_large");
        string L(string en, string de, string es) => filter.Language == "de" ? de : filter.Language == "es" ? es : en;
        var rooms = All("rooms").ToDictionary(r => SvgId(r)); var buildings = All("buildings").ToDictionary(b => SvgId(b));
        var sites = All("sites").ToDictionary(s => SvgId(s)); var racks = All("racks").ToDictionary(r => SvgId(r));
        string RoomPath(JsonElement e)
        {
            if (e.GetProperty("roomId").ValueKind == JsonValueKind.Null) return L("Unassigned", "Nicht zugeordnet", "Sin asignar");
            var room = rooms[SvgId(e, "roomId")]; var building = buildings[SvgId(room, "buildingId")]; var site = sites[SvgId(building, "siteId")];
            return string.Join(" / ", SvgString(site, "name"), SvgString(building, "name"), SvgString(room, "name"));
        }
        string Endpoint(Guid id)
        {
            var p = allPorts[id]; var d = allDevices[SvgId(p, "deviceId")]; var g = allGroups[SvgId(p, "groupId")];
            string location = d.GetProperty("rackId").ValueKind == JsonValueKind.Null ? RoomPath(d) : SvgString(racks[SvgId(d, "rackId")], "name");
            string rackId = d.GetProperty("rackId").ValueKind == JsonValueKind.Null ? "null" : SvgId(d, "rackId").ToString("D");
            string roomId = d.GetProperty("roomId").ValueKind == JsonValueKind.Null ? "null" : SvgId(d, "roomId").ToString("D");
            return $"{location} / {SvgString(d, "name")} / {SvgString(g, "name")} / {SvgString(g, "prefix")}{p.GetProperty("gn").GetInt32()} · port:{id:D} device:{SvgId(d):D} group:{SvgId(g):D} rack:{rackId} room:{roomId}\n" +
                $"type:{SvgString(p, "type")} gn:{p.GetProperty("gn").GetInt32()} label:{SvgString(p, "label")} face:{SvgString(p, "face")} effectiveFace:{SvgFace(d, p)} status:{SvgString(p, "status")} powerRole:{SvgString(p, "powerRole")} PoE:{p.GetProperty("poe").GetBoolean()} watts:{p.GetProperty("watts").GetRawText()}";
        }
        var blocks = new List<SvgBlock>(); double bottom = 144;
        foreach (var device in devices)
        {
            var block = LayoutRackSvg(device, ports.Where(p => SvgId(p, "deviceId") == SvgId(device)).ToArray(), filter.Face, bottom);
            blocks.Add(block); bottom += block.Height + 27;
            if (bottom > 999900) throw new DomainError(422, "report_too_large");
        }
        double height = Math.Max(250, bottom + 64);
        var visible = blocks.SelectMany(b => b.Ports.Select(p => (Id: SvgId(p.Value), Port: p, Block: b))).ToDictionary(p => p.Id);
        try
        {
            using var output = new RackSvgStream();
            using var xml = XmlWriter.Create(output, new XmlWriterSettings { Encoding = new UTF8Encoding(false), OmitXmlDeclaration = true,
                CheckCharacters = true, NewLineHandling = NewLineHandling.Entitize, CloseOutput = false });
            void Start(string name) => xml.WriteStartElement(null, name, RackSvgNamespace);
            void A(string name, string value) => xml.WriteAttributeString(name, value);
            string N(double value) => value.ToString("0.###", CultureInfo.InvariantCulture);
            void Text(string tag, string text) { Start(tag); xml.WriteString(text); xml.WriteEndElement(); }
            void Row(string kind, Guid id) { Start("g"); A("data-report-row", kind); A("data-id", id.ToString("D")); }
            void Label(double x, double y, string text, double size = 12, string fill = "#152b3c", double? width = null)
            {
                string displayed = AbbreviateSvgLabel(text, width ?? 948 - x, size);
                Start("text"); A("x", N(x)); A("y", N(y)); A("font-family", "Arial,sans-serif"); A("font-size", N(size)); A("fill", fill);
                if (displayed != text) Text("title", text);
                xml.WriteString(displayed); xml.WriteEndElement();
            }
            void Rect(double x, double y, double width, double h, string fill, string stroke, double radius = 0)
            { Start("rect"); A("x", N(x)); A("y", N(y)); A("width", N(width)); A("height", N(h)); A("rx", N(radius)); A("fill", fill); A("stroke", stroke); xml.WriteEndElement(); }
            void Path(string d, string fill, string stroke, double width = 1)
            { Start("path"); A("d", d); A("fill", fill); A("stroke", stroke); A("stroke-width", N(width)); xml.WriteEndElement(); }
            void Circle(double x, double y, double r, string fill, string stroke)
            { Start("circle"); A("cx", N(x)); A("cy", N(y)); A("r", N(r)); A("fill", fill); A("stroke", stroke); xml.WriteEndElement(); }
            Start("svg"); A("xmlns", RackSvgNamespace); A("lang", filter.Language); A("data-template", RackSvgTemplateVersion);
            A("data-customer-id", customer.ToString("D")); A("data-rack-id", filter.RackId.ToString("D"));
            A("data-source-revision", revision.ToString(CultureInfo.InvariantCulture)); A("data-face", filter.Face);
            A("viewBox", "0 0 960 " + N(height)); A("role", "img"); A("aria-label", SvgString(rack, "name"));
            Text("title", SvgString(rack, "name") + " · " + L(filter.Face == "front" ? "Front" : "Rear", filter.Face == "front" ? "Vorderseite" : "Rückseite", filter.Face == "front" ? "Frontal" : "Trasera"));
            Text("desc", L("Documentary rack view; ordered equipment, not measured U placement. No invented circuit through room objects.",
                "Dokumentarische Rackansicht; geordnete Geräte, keine gemessene HE-Position. Keine erfundenen Schaltungen durch Raumobjekte.",
                "Vista documental del rack; equipos ordenados, sin posición U medida. No inventa circuitos a través de objetos de sala.") +
                $"\n{customerName}\ncustomer:{customer:D} rack:{filter.RackId:D} revision:{revision}\n" +
                L("Visible/hidden ports", "Sichtbare/verdeckte Ports", "Puertos visibles/ocultos") + $": {visible.Count}/{ports.Length - visible.Count}\n" +
                L("Long visual labels use an ellipsis; title/description retain the complete literal original.",
                    "Lange sichtbare Beschriftungen werden mit Auslassungspunkten gekürzt; Titel/Beschreibung bewahren das vollständige Original.",
                    "Las etiquetas visuales largas usan elipsis; título/descripción conservan el original literal completo."));
            Rect(0, 0, 960, height, "#ffffff", "#a4b1bc");
            Label(12, 28, "RackClick", 24, "#08794e"); Label(12, 53, customerName, 16);
            Label(12, 76, SvgString(rack, "name"), 16, width: 590);
            Label(620, 76, L(filter.Face == "front" ? "Front" : "Rear", filter.Face == "front" ? "Vorderseite" : "Rückseite", filter.Face == "front" ? "Frontal" : "Trasera") + " · " + rack.GetProperty("sizeU").GetInt32() + " U", 14, width: 328);
            Label(12, 98, RoomPath(rack)); Label(12, 119, $"{customer:D} · r{revision} · {filter.RackId:D}", 10);
            Row("rack", filter.RackId); Text("desc", SvgString(rack, "name") + "\n" + RoomPath(rack) + "\n" + SvgString(rack, "location") + $"\nsizeU:{rack.GetProperty("sizeU").GetInt32()}"); xml.WriteEndElement();
            foreach (var block in blocks)
            {
                var d = block.Device; Row("device", SvgId(d));
                Text("desc", SvgString(d, "name") + $"\nkind:{SvgString(d, "kind")} sizeU:{d.GetProperty("sizeU").GetInt32()} sortOrder:{d.GetProperty("sortOrder").GetInt32()}\nrack:{filter.RackId:D}");
                Label(12, block.Top + 18, SvgString(d, "name"), 13, width: 790);
                Label(820, block.Top + 18, d.GetProperty("sizeU").GetInt32() + " U", 13, width: 128);
                Rect(1, block.Top + 24, 958, block.Height, "#eef2f5", "#56687a", 4);
                if (block.Family == "storage" && filter.Face == "front")
                    for (int i = 0; i < 8; i++) Rect(38 + i * 108, block.Top + 36, 97, 39, "#d2dae2", "#56687a", 3);
                if (block.Family == "storage" && filter.Face == "rear")
                    foreach (int x in new[] { 55, 135, 215 }) { Rect(x, block.Top + 38, 70, 57, "#d2dae2", "#56687a", 4); Circle(x + 35, block.Top + 66, 23, "none", "#56687a"); }
                if (block.Family == "ups" && filter.Face == "front")
                { Rect(30, block.Top + 38, 148, 32, "#d2dae2", "#56687a", 3); Label(38, block.Top + 58, L("No telemetry", "Keine Telemetrie", "Sin telemetría"), 10); }
                if (block.Ports.Length == 0) Label(30, block.Top + block.Height / 2 + 28, L("No ports on this face", "Keine Ports auf dieser Seite", "Sin puertos en esta cara"));
                xml.WriteEndElement();
            }
            foreach (var g in groups)
            { Row("group", SvgId(g)); A("data-device-id", SvgId(g, "deviceId").ToString("D")); Text("desc", $"{SvgString(g, "name")}\ntype:{SvgString(g, "type")} prefix:{SvgString(g, "prefix")} sortOrder:{g.GetProperty("sortOrder").GetInt32()}"); xml.WriteEndElement(); }
            foreach (var p in ports)
            {
                Guid id = SvgId(p); bool shown = visible.TryGetValue(id, out var point);
                Row("port", id); A("data-device-id", SvgId(p, "deviceId").ToString("D")); A("data-group-id", SvgId(p, "groupId").ToString("D")); A("data-visible", shown ? "true" : "false");
                string? physicalConnector = ReadPhysicalConnector(allDevices[SvgId(p, "deviceId")], p);
                Text("desc", Endpoint(id) + $"\nlabel:{SvgString(p, "label")} type:{SvgString(p, "type")} gn:{p.GetProperty("gn").GetInt32()} status:{SvgString(p, "status")} face:{SvgString(p, "face")} effectiveFace:{SvgFace(allDevices[SvgId(p, "deviceId")], p)} powerRole:{SvgString(p, "powerRole")} PoE:{p.GetProperty("poe").GetBoolean()} watts:{p.GetProperty("watts").GetRawText()} color:{p.GetProperty("color").GetRawText()}\n" +
                    (physicalConnector is null ? "" : "physicalConnector:" + physicalConnector + "\nPhysical form classification only; cord ends, voltage and pinout unspecified.\n") +
                    (shown ? L("Visible port", "Sichtbarer Port", "Puerto visible") : L("Hidden on this face; same port UUID", "Auf dieser Seite verdeckt; gleiche Port-UUID", "Oculto en esta cara; mismo UUID de puerto")));
                if (shown)
                {
                    var port = point.Port; double x = port.X, y = point.Block.Top + 26 + port.Y, width = port.Width;
                    string type = SvgString(p, "type"), role = SvgString(p, "powerRole"), status = SvgString(p, "status");
                    var cable = connections.FirstOrDefault(c => SvgId(c, "fromPortId") == id || SvgId(c, "toPortId") == id);
                    string color = SvgColor(p, "color", cable.ValueKind != JsonValueKind.Undefined ? SvgColor(cable, "color", "#08794e") : "#457b9d");
                    Label(x, y - 3, allGroups[SvgId(p, "groupId")].GetProperty("prefix").GetString() + p.GetProperty("gn").GetInt32(), 10, width: width);
                    Start("g"); A("transform", $"translate({N(x)} {N(y)}) scale({N(width / 40)})");
                    string shape = type is "rj45" or "rj45_poe" or "mgmt" ? "M5 6H35V27H27V32H13V27H5Z" : type is "sfp" or "sfp28" or "sfp56" or "qsfp" or "qsfpdd" ? "M3 10H37V27H3Z M7 24H33 M10 27V31H30V27" :
                        type == "idc" ? "M3 6H37V34H3Z M5 12H35 M5 20H35 M5 28H35" : type == "usb_a" ? "M3 10H37V30H3Z M8 16H32" : type == "power" ? "M8 6H32L37 12V34H3V12Z" : type == "usb_c" ? "M11 12H29C40 12 40 28 29 28H11C0 28 0 12 11 12Z M10 20H30" : "M5 10H35L31 30H9Z";
                    Path(shape, "#d2dae2", color);
                    if (type == "idc") Label(20, 26, "IDC", 8, "#152b3c", 36);
                    if (type is "sfp56" or "qsfpdd") Label(20, 23, type == "sfp56" ? "56" : "DD", 8, "#152b3c", 36);
                    if (type is "rj45" or "rj45_poe" or "mgmt") for (int i = 0; i < 8; i++) Path($"M{N(8 + i * 3.2)} 7V15", "none", "#56687a");
                    if (type == "power") Path(role == "inlet" ? "M12 18V25 M28 18V25 M20 12V19" : role == "outlet" ? "M10 18H14V26H10Z M26 18H30V26H26Z M18 10H22V18H18Z" : "M12 20H28 M20 12V28", "none", "#56687a");
                    xml.WriteEndElement();
                    Rect(x, y, width, width, "none", status is "disabled" or "faulty" ? "#fb7185" : status == "reserved" ? "#fbbf24" : color, 2);
                    if (status == "reserved") { Start("path"); A("d", $"M{N(x)} {N(y)}H{N(x + width)}V{N(y + width)}H{N(x)}Z"); A("fill", "none"); A("stroke", "#fbbf24"); A("stroke-dasharray", "3 2"); xml.WriteEndElement(); }
                    if (type is "rj45" or "rj45_poe") Path($"M{N(x + width - 6)} {N(y + 4)}l-4 7h4l-3 7 7-10h-4l3-4Z", p.GetProperty("poe").GetBoolean() ? "#08794e" : "none", "#08794e");
                    if (cable.ValueKind != JsonValueKind.Undefined) Circle(x + width - 2, y + 2, 1.7, "#08794e", "#08794e");
                }
                xml.WriteEndElement();
            }
            foreach (var c in connections)
            {
                Guid from = SvgId(c, "fromPortId"), to = SvgId(c, "toPortId"); bool shown = visible.ContainsKey(from) && visible.ContainsKey(to);
                Row("connection", SvgId(c)); A("data-from-port-id", from.ToString("D")); A("data-to-port-id", to.ToString("D")); A("data-visible", shown ? "true" : "false");
                Text("desc", Endpoint(from) + "\n→ " + Endpoint(to) + $"\nnote:{SvgString(c, "note")} patch:{SvgString(c, "patch")} color:{c.GetProperty("color").GetRawText()}\n" +
                    (shown ? L("Both endpoints visible", "Beide Endpunkte sichtbar", "Ambos extremos visibles") : L("Endpoint hidden or outside this rack; no invented path", "Endpunkt verdeckt oder außerhalb dieses Racks; kein erfundener Pfad", "Extremo oculto o fuera de este rack; sin ruta inventada")));
                if (shown)
                {
                    var a = visible[from]; var b = visible[to]; double ax = a.Port.X + a.Port.Width / 2, ay = a.Block.Top + 26 + a.Port.Y + a.Port.Width / 2;
                    double bx = b.Port.X + b.Port.Width / 2, by = b.Block.Top + 26 + b.Port.Y + b.Port.Width / 2;
                    Path($"M{N(ax)} {N(ay)} C{N(ax + 30)} {N(ay + 40)} {N(bx + 30)} {N(by - 40)} {N(bx)} {N(by)}", "none", SvgColor(c, "color", "#08794e"), 2);
                }
                xml.WriteEndElement();
            }
            Label(12, height - 35, L("Visible / hidden ports", "Sichtbare / verdeckte Ports", "Puertos visibles / ocultos") + $": {visible.Count} / {ports.Length - visible.Count} · " + L("Incident connections", "Anliegende Verbindungen", "Conexiones incidentes") + ": " + connections.Length);
            Label(12, height - 14, L("Documented, not physically verified", "Dokumentiert, nicht physisch geprüft", "Documentado, sin verificación física"), 10);
            xml.WriteEndElement(); xml.Flush();
            return (output.ToArray(), rows);
        }
        catch (Exception e) when (e is XmlException or ArgumentException) { throw new DomainError(422, "report_text_invalid"); }
    }
}
