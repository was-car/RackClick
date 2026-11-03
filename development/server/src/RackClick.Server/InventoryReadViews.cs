using System.Globalization;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;
using Microsoft.AspNetCore.Http;
using RackClick.Domain;

namespace RackClick.Server;

public sealed record InventoryViewPath(string Kind, Guid Id, string Name);
public sealed record InventorySearchItem(Guid CustomerId, Guid Id, string Kind, string Name,
    InventoryViewPath[] Path, Guid? RackId, Guid? RoomId, Guid? DeviceId, Guid? GroupId, string? Type, int? Gn, string? Status);
public sealed record InventoryPortView(Guid CustomerId, Guid Id, Guid DeviceId, string DeviceName, string DeviceKind,
    Guid? RackId, Guid? RoomId, InventoryViewPath[] Path, Guid GroupId, string GroupName, string Type, string Family,
    int Gn, string Label, string Status, string Face, bool Poe, decimal? Watts, string? Color, string PowerRole,
    bool Connected, Guid[] ConnectionIds, Guid[] PeerPortIds)
{
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public string? PhysicalConnector { get; init; }
}
public sealed record InventoryConnectionView(Guid CustomerId, Guid Id, InventoryPortView From, InventoryPortView To,
    string Note, string? Color, string Patch, bool? CrossRack);
public sealed record InventoryReadView(Guid CustomerId, long Revision, string Query, string? Kind, string? Status,
    string? Family, int Offset, int Limit, int Total, int? NextOffset, object[] Items);

public sealed partial class InventoryStore
{
    private static string? ReadPhysicalConnector(JsonElement device, JsonElement port)
    {
        static string? TextOrNull(JsonElement value, string key) => value.ValueKind == JsonValueKind.Object &&
            value.TryGetProperty(key, out var text) && text.ValueKind == JsonValueKind.String ? text.GetString() : null;
        if (!device.TryGetProperty("properties", out var deviceProperties) ||
            !port.TryGetProperty("properties", out var portProperties)) return null;
        return InventoryHardwareProfiles.TrustedPhysicalConnector(TextOrNull(device, "hardwareProfileKey"),
            TextOrNull(deviceProperties, "hardwareProfileVersion"), TextOrNull(portProperties, "hardwareGroupKey"),
            TextOrNull(port, "type"), TextOrNull(port, "face"), TextOrNull(portProperties, "hardwarePhysicalConnector"));
    }
    private sealed record ViewFilter(string Query, string? Kind, string? Status, string? Family, int Offset, int Limit);
    public Task<InventoryReadView> ReadView(Actor actor, Guid customer, string view, long expected, IQueryCollection query, CancellationToken ct)
    {
        var filter = ParseViewFilter(view, query);
        return ReadAuthorizedSnapshot(actor, customer, expected, (json, revision) => ProjectView(customer, revision, view, filter, json), ct);
    }

    private static ViewFilter ParseViewFilter(string view, IQueryCollection query)
    {
        string[] permitted = view switch {
            "search" => ["query", "kind", "offset", "limit"],
            "ports" => ["query", "status", "family", "offset", "limit"],
            "connections" => ["query", "offset", "limit"],
            _ => throw new DomainError(422, "request_invalid") };
        if (query.Any(p => !permitted.Contains(p.Key, StringComparer.Ordinal) || p.Value.Count != 1))
            throw new DomainError(422, "request_invalid");
        string Value(string name, string fallback) => query.TryGetValue(name, out var value) ? value.ToString() : fallback;
        int Number(string name, int fallback, int min, int max) => !query.ContainsKey(name) ? fallback :
            int.TryParse(Value(name, ""), NumberStyles.None, CultureInfo.InvariantCulture, out int value) && value >= min && value <= max
                ? value : throw new DomainError(422, "request_invalid");
        string Choice(string name, string[] values) => values.Contains(Value(name, "all"), StringComparer.Ordinal)
            ? Value(name, "all") : throw new DomainError(422, "request_invalid");
        string text = Value("query", "");
        try { FreeText.Validate(text, 200); _ = text.Normalize(NormalizationForm.FormC); }
        catch (Exception e) when (e is DomainError or ArgumentException) { throw new DomainError(422, "request_invalid"); }
        return new(text, view == "search" ? Choice("kind", ["all", "site", "building", "room", "rack", "device", "port", "connection"]) : null,
            view == "ports" ? Choice("status", ["all", "free", "reserved", "disabled", "faulty"]) : null,
            view == "ports" ? Choice("family", ["all", "rj45", "sfp", "sfp28", "sfp56", "qsfp", "qsfpdd", "mgmt", "console", "idc", "power", "usb_a", "usb_c", "ipc", "fiber", "sfpdd", "cfp2", "sas", "dsl", "telephony", "isdn", "expansion", "power_dc"]) : null,
            Number("offset", 0, 0, 1000000), Number("limit", 50, 1, 100));
    }

    private static InventoryReadView ProjectView(Guid customer, long revision, string view, ViewFilter filter, string json,
        bool paginate = true, Guid? rackId = null)
    {
        using var document = JsonDocument.Parse(json);
        var root = document.RootElement;
        static string S(JsonElement e, string key) => e.GetProperty(key).GetString()!;
        static Guid G(JsonElement e, string key = "id") => e.GetProperty(key).GetGuid();
        static Guid? N(JsonElement e, string key) => e.GetProperty(key).ValueKind == JsonValueKind.Null ? null : G(e, key);
        Dictionary<Guid, JsonElement> Map(string key) => root.GetProperty(key).EnumerateArray().ToDictionary(e => G(e));
        var sites = Map("sites"); var buildings = Map("buildings"); var rooms = Map("rooms");
        var racks = Map("racks"); var devices = Map("devices"); var groups = Map("portGroups"); var ports = Map("ports"); var connections = Map("connections");
        InventoryViewPath[] Path(string kind, Guid id)
        {
            JsonElement entity = kind switch { "site" => sites[id], "building" => buildings[id], "room" => rooms[id],
                "rack" => racks[id], "device" => devices[id], "port" => ports[id], _ => throw new InvalidOperationException() };
            (string Kind, Guid? Id) parent = kind switch {
                "building" => ("site", G(entity, "siteId")), "room" => ("building", G(entity, "buildingId")),
                "rack" => ("room", N(entity, "roomId")), "device" => N(entity, "rackId") is Guid rack ? ("rack", rack) : ("room", N(entity, "roomId")),
                "port" => ("device", G(entity, "deviceId")), _ => ("site", null) };
            var path = parent.Id.HasValue ? Path(parent.Kind, parent.Id.Value).ToList() : [];
            string name = kind == "port" ? S(entity, "label") : S(entity, "name");
            if (kind == "port" && name.Length == 0) name = entity.GetProperty("gn").GetInt32().ToString(CultureInfo.InvariantCulture);
            path.Add(new(kind, id, name)); return path.ToArray();
        }
        (Guid? Rack, Guid? Room) Location(InventoryViewPath[] path) =>
            (path.FirstOrDefault(p => p.Kind == "rack")?.Id, path.FirstOrDefault(p => p.Kind == "room")?.Id);
        var portViews = new Dictionary<Guid, InventoryPortView>();
        var incidence = connections.Values.SelectMany(c => new[] { (Port: G(c, "fromPortId"), Cable: c), (Port: G(c, "toPortId"), Cable: c) })
            .ToLookup(p => p.Port, p => p.Cable);
        foreach (var (id, port) in ports)
        {
            var deviceId = G(port, "deviceId"); var device = devices[deviceId]; var groupId = G(port, "groupId");
            var path = Path("port", id); var location = Location(path);
            var incident = incidence[id].OrderBy(c => G(c).ToString("D"), StringComparer.Ordinal).ToArray();
            string type = S(port, "type");
            portViews[id] = new(customer, id, deviceId, S(device, "name"), S(device, "kind"), location.Rack, location.Room,
                path, groupId, S(groups[groupId], "name"), type, InventoryRules.Family(type), port.GetProperty("gn").GetInt32(),
                S(port, "label"), S(port, "status"), S(port, "face"), port.GetProperty("poe").GetBoolean(),
                port.GetProperty("watts").ValueKind == JsonValueKind.Null ? null : port.GetProperty("watts").GetDecimal(),
                port.GetProperty("color").GetString(), S(port, "powerRole"), incident.Length != 0,
                incident.Select(c => G(c)).ToArray(), incident.Select(c => G(c, "fromPortId") == id ? G(c, "toPortId") : G(c, "fromPortId")).ToArray())
            {
                PhysicalConnector = ReadPhysicalConnector(device, port)
            };
        }
        var cables = connections.Values.Select(c => {
            var from = portViews[G(c, "fromPortId")]; var to = portViews[G(c, "toPortId")];
            return new InventoryConnectionView(customer, G(c), from, to, S(c, "note"), c.GetProperty("color").GetString(), S(c, "patch"),
                from.RackId.HasValue && to.RackId.HasValue ? from.RackId != to.RackId : null);
        }).ToArray();
        string needle = filter.Query.Normalize(NormalizationForm.FormC);
        bool Matches(params string[] texts) => texts.Any(t => t.Normalize(NormalizationForm.FormC).Contains(needle, StringComparison.OrdinalIgnoreCase));
        bool PortMatches(InventoryPortView p) => Matches(p.Label, p.DeviceName, p.GroupName, p.Type, p.Status,
            p.Gn.ToString(CultureInfo.InvariantCulture), string.Join(" / ", p.Path.Select(n => n.Name)));
        bool CableMatches(InventoryConnectionView c) => Matches(c.Note, c.Patch) || PortMatches(c.From) || PortMatches(c.To);
        var results = new List<(Guid Id, object Value)>();
        if (view == "ports")
            results.AddRange(portViews.Values.Where(p => (filter.Status == "all" || p.Status == filter.Status) &&
                (filter.Family == "all" || p.Family == filter.Family) && PortMatches(p)).Select(p => (p.Id, (object)p)));
        else if (view == "connections") results.AddRange(cables.Where(CableMatches).Select(c => (c.Id, (object)c)));
        else
        {
            foreach (var (kind, map) in new[] { ("site", sites), ("building", buildings), ("room", rooms), ("rack", racks), ("device", devices), ("port", ports) })
                foreach (var (id, entity) in map)
                {
                    if (filter.Kind != "all" && filter.Kind != kind) continue;
                    var path = Path(kind, id); var location = Location(path); var port = kind == "port" ? portViews[id] : null;
                    string name = path[^1].Name;
                    if (!(port is not null ? PortMatches(port) : Matches(name, kind == "rack" ? S(entity, "location") : ""))) continue;
                    results.Add((id, new InventorySearchItem(customer, id, kind, name, path, location.Rack, location.Room,
                        port?.DeviceId ?? (kind == "device" ? id : null), port?.GroupId, port?.Type, port?.Gn, port?.Status)));
                }
            if (filter.Kind is "all" or "connection")
                results.AddRange(cables.Where(CableMatches).Select(c => (c.Id, (object)new InventorySearchItem(customer, c.Id, "connection", c.Note,
                    [], null, null, null, null, null, null, null))));
        }
        if (rackId.HasValue) results = results.Where(p => p.Value switch {
            InventoryPortView port => port.RackId == rackId,
            InventoryConnectionView cable => cable.From.RackId == rackId || cable.To.RackId == rackId,
            _ => false }).ToList();
        var ordered = results.OrderBy(p => p.Id.ToString("D"), StringComparer.Ordinal).ToArray();
        var items = (paginate ? ordered.Skip(filter.Offset).Take(filter.Limit) : ordered.Take(10001)).Select(p => p.Value).ToArray();
        return new(customer, revision, filter.Query, filter.Kind, filter.Status, filter.Family, filter.Offset, filter.Limit,
            ordered.Length, filter.Offset + items.Length < ordered.Length ? filter.Offset + items.Length : null, items);
    }
}
