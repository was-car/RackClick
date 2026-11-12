using System.Security.Cryptography;
using System.Text.Json;
using System.Text.Json.Nodes;
using RackClick.Domain;
using static RackClick.Server.InventoryJson;

namespace RackClick.Server;

/// <summary>Counts of inventory rows only; account and security tables are excluded.</summary>
public sealed record InventoryDataCounts(int Customers, int Sites, int Buildings, int Rooms, int Racks,
    int Devices, int PortGroups, int Ports, int Connections);
/// <summary>A portable global inventory archive, without security or configuration state.</summary>
public sealed record InventoryDataArchive(string Format, string Filename, string ContentType, string Encoding,
    int ByteLength, string Sha256, string ContentBase64);
/// <summary>Confirmed administrative inventory receipt, returned only after commit.</summary>
public sealed record InventoryDataResult(string Kind, string Action, Guid RequestId, Guid OperationId,
    long SystemhausRevision, InventoryDataCounts Counts, InventoryDataArchive? Archive);

public sealed partial class InventoryStore
{
    internal const int InventoryDataMaximumBytes = 32 * 1024 * 1024;
    private const int InventoryDataMaximumRows = 100000;
    private const long InventoryDataMaximumRevision = 9007199254740991L;
    private const string InventoryDataFormat = "RackClickInventoryBackup-v1";
    private static readonly string[] DataCollections = ["sites", "buildings", "rooms", "racks", "devices", "portGroups", "ports", "connections"];
    private sealed record ParsedInventoryData(byte[] Bytes, string Sha256, JsonArray Customers, InventoryDataCounts Counts);
    private static readonly Lazy<ParsedInventoryData> DemoInventoryData = new(LoadDemoInventoryData);

    private static void DataKeys(JsonObject value, params string[] keys)
    {
        if (value.Count != keys.Length || keys.Any(key => !value.ContainsKey(key))) throw new DomainError(422, "inventory_archive_invalid");
    }
    private static long DataRevision(JsonObject value)
    {
        // The existing customer/inventory adapters require Number.isSafeInteger, including on reload.
        if (value["revision"] is not JsonValue node || !node.TryGetValue<long>(out var revision) || revision < 1 || revision > InventoryDataMaximumRevision)
            throw new DomainError(422, "inventory_archive_invalid");
        return revision;
    }
    private static void DataRowNullability(string collection,JsonObject row)
    {
        // Live command readers can supply defaults for omitted/null fields. An archive is a complete
        // persisted row: SQL inserts its original values, so every NOT NULL field must be explicit.
        // These are the nullable columns in the closed insertion mapping, never arbitrary property keys.
        string[] nullable=collection switch
        {
            "racks"=>["roomId","hardwareProfileKey"],
            "devices"=>["rackId","roomId","sizeU","poeBudget","hardwareProfileKey","mountParentId","mountSlotKey"],
            "ports"=>["watts","color"],
            "connections"=>["color"],
            _=>[]
        };
        if(row.Any(field=>field.Value is null && !nullable.Contains(field.Key,StringComparer.Ordinal)))
            throw new DomainError(422,"inventory_archive_invalid");
    }
    private static ParsedInventoryData DecodeInventoryData(string base64)
    {
        // Bound the encoded input before allocating its decoded buffer. JSON body has its own, selective ceiling.
        if (base64.Length > ((InventoryDataMaximumBytes + 2) / 3) * 4) throw new DomainError(422, "inventory_archive_too_large");
        byte[] bytes;
        try { bytes = Convert.FromBase64String(base64); }
        catch (FormatException) { throw new DomainError(422, "inventory_archive_invalid"); }
        return ParseInventoryData(bytes);
    }
    private static ParsedInventoryData ParseInventoryData(byte[] bytes)
    {
        if (bytes.Length > InventoryDataMaximumBytes) throw new DomainError(422, "inventory_archive_too_large");
        try
        {
            using var document = JsonDocument.Parse(bytes);
            var root = Object(document.RootElement);
            DataKeys(root, "formatVersion", "kind", "schemaVersion", "createdAt", "customers");
            if (Integer(root, "formatVersion", 1, 1) != 1 || String(root, "kind") != "RackClickInventoryBackup" ||
                Integer(root, "schemaVersion", 48, 48) != 48 ||
                !DateTimeOffset.TryParse(String(root, "createdAt"), System.Globalization.CultureInfo.InvariantCulture,
                    System.Globalization.DateTimeStyles.None, out var created) || created.Offset != TimeSpan.Zero)
                throw new DomainError(422, "inventory_archive_invalid");
            var customers = Array(root, "customers", 500);
            var unique = new HashSet<Guid>(); var counts = new int[9]; counts[0] = customers.Count;
            foreach (var node in customers)
            {
                var customer = node as JsonObject ?? throw new DomainError(422, "inventory_archive_invalid");
                DataKeys(customer, "id", "name", "revision", "inventory");
                if (!unique.Add(Id(customer, "id"))) throw new DomainError(422, "inventory_archive_invalid");
                _ = Names.Validate(String(customer, "name")); _ = DataRevision(customer);
                var inventory = customer["inventory"] as JsonObject ?? throw new DomainError(422, "inventory_archive_invalid");
                DataKeys(inventory, DataCollections);
                var sets = new Dictionary<string, Dictionary<Guid, JsonObject>>(StringComparer.Ordinal);
                for (int i = 0; i < DataCollections.Length; i++)
                {
                    string collection = DataCollections[i]; var items = Array(inventory, collection, InventoryDataMaximumRows);
                    counts[i + 1] = checked(counts[i + 1] + items.Count);
                    if (counts.Sum() > InventoryDataMaximumRows) throw new DomainError(422, "inventory_archive_too_large");
                    var entries = new Dictionary<Guid, JsonObject>();
                    foreach (var item in items)
                    {
                        var row = item as JsonObject ?? throw new DomainError(422, "inventory_archive_invalid");
                        DataRowNullability(collection,row);
                        if(collection!="portGroups" && row["properties"] is not JsonObject) throw new DomainError(422,"properties_invalid");
                        Guid id = Id(row, "id");
                        if (!unique.Add(id) || !entries.TryAdd(id, row)) throw new DomainError(422, "inventory_archive_invalid");
                    }
                    sets.Add(collection, entries);
                }
                ValidateInventoryDataCustomer(sets);
            }
            return new(bytes, Convert.ToHexStringLower(SHA256.HashData(bytes)), customers,
                new(counts[0], counts[1], counts[2], counts[3], counts[4], counts[5], counts[6], counts[7], counts[8]));
        }
        catch (Exception error) when (error is JsonException or InvalidOperationException or ArgumentException or FormatException or OverflowException)
        { throw new DomainError(422, "inventory_archive_invalid"); }
        catch (DomainError error) when(error.Status!=422)
        { throw new DomainError(422,error.Code); }
    }

    private static void ValidateInventoryDataCustomer(Dictionary<string, Dictionary<Guid, JsonObject>> sets)
    {
        JsonObject Reference(JsonObject row, string key, string collection) => sets[collection].GetValueOrDefault(Id(row, key))
            ?? throw new DomainError(422, "inventory_archive_reference_invalid");
        void OptionalReference(JsonObject row, string key, string collection) { if (row[key] is not null) _ = Reference(row, key, collection); }
        foreach (var site in sets["sites"].Values) { DataKeys(site,"id","name","properties"); _ = Names.Validate(String(site,"name")); _ = Properties(site); }
        foreach (var building in sets["buildings"].Values) { DataKeys(building,"id","siteId","name","properties"); _ = Reference(building,"siteId","sites"); _ = Names.Validate(String(building,"name")); _ = Properties(building); }
        foreach (var room in sets["rooms"].Values) { DataKeys(room,"id","buildingId","name","properties"); _ = Reference(room,"buildingId","buildings"); _ = Names.Validate(String(room,"name")); _ = Properties(room); }
        foreach (var rack in sets["racks"].Values)
        {
            DataKeys(rack, rack.ContainsKey("hardwareProfileKey") ? ["id","roomId","name","location","sizeU","properties","hardwareProfileKey"] : ["id","roomId","name","location","sizeU","properties"]);
            OptionalReference(rack,"roomId","rooms"); _ = Names.Validate(String(rack,"name")); _ = FreeText.Validate(String(rack,"location"),2000); _ = Properties(rack);
            int size = Integer(rack,"sizeU",1,1000); var profile = InventoryDataProfile(rack);
            if (profile is not null && (profile.Kind != "rackContainer" || profile.MountingJson is null ||
                JsonNode.Parse(profile.MountingJson)!["capacityU"]!.GetValue<int>() != size)) throw new DomainError(422,"hardware_profile_invalid");
        }
        var profiles = new Dictionary<Guid,InventoryHardwareProfiles.Profile?>();
        var positions = new HashSet<(Guid?,Guid?,int)>(); var slots = new HashSet<(Guid?,Guid?,string)>();
        foreach (var device in sets["devices"].Values)
        {
            DataKeys(device,"id","kind","rackId","roomId","name","sizeU","sortOrder","poeBudget","hardwareProfileKey","mountParentId","mountSlotKey","properties");
            _ = Names.Validate(String(device,"name")); _ = Properties(device); _ = Number(device,"poeBudget",999999);
            int order = Integer(device,"sortOrder",0,int.MaxValue); Guid? rack = OptionalId(device,"rackId"), room = OptionalId(device,"roomId");
            string kind = String(device,"kind"); var profile = InventoryDataProfile(device); profiles.Add(Id(device,"id"),profile);
            if (kind == "rackEquipment")
            {
                if (rack is null || room is not null) throw new DomainError(422,"placement_invalid");
                _ = Reference(device,"rackId","racks"); _ = Integer(device,"sizeU",profile is null?1:0,1000);
                if (!positions.Add((rack,null,order))) throw new DomainError(422,"device_order_invalid");
            }
            else if (kind is "dose" or "endDevice")
            {
                if (room is null || rack is not null || device["sizeU"] is not null || device["mountParentId"] is not null || device["mountSlotKey"] is not null)
                    throw new DomainError(422,"placement_invalid");
                _ = Reference(device,"roomId","rooms");
            }
            else throw new DomainError(422,"device_kind_invalid");
            if (profile is null && (device["mountParentId"] is not null || device["mountSlotKey"] is not null)) throw new DomainError(422,"mount_support_invalid");
            if (device["mountSlotKey"] is not null && !slots.Add((rack,OptionalId(device,"mountParentId"),String(device,"mountSlotKey")))) throw new DomainError(422,"mount_slot_occupied");
        }
        foreach (var rack in sets["racks"].Values)
        {
            Guid id = Id(rack,"id");
            int used = sets["devices"].Values.Where(d=>OptionalId(d,"rackId")==id).Sum(d=>Integer(d,"sizeU",0,1000));
            InventoryRules.RequireCapacity(Integer(rack,"sizeU",1,1000),used,0);
        }
        foreach (var device in sets["devices"].Values)
        {
            var profile = profiles[Id(device,"id")]; if (profile is null) continue;
            Guid? parent = OptionalId(device,"mountParentId"); string? slot = device["mountSlotKey"] is null ? null : String(device,"mountSlotKey");
            if (FamilyLRules.IsRoom(profile.Kind))
            { if (String(device,"kind")!="endDevice") throw new DomainError(422,"placement_invalid"); continue; }
            if (String(device,"kind")!="rackEquipment" || Integer(device,"sizeU",0,1000)!=profile.RackUnits || profile.Kind=="rackContainer") throw new DomainError(422,"placement_invalid");
            if (profile.Kind is "desktop" or "sharedU")
            {
                var support = Reference(device,"mountParentId","devices");
                if (support["mountParentId"] is not null || OptionalId(support,"rackId")!=OptionalId(device,"rackId") || Integer(support,"sizeU",0,1000)<=0) throw new DomainError(422,"mount_support_invalid");
                if (profile.Kind=="desktop")
                {
                    var bay = profiles[Id(support,"id")]?.Slots.SingleOrDefault(s=>s.Key==slot);
                    if (bay is null || profile.WidthMm is not {} width || profile.HeightMm is not {} height || profile.DepthMm is not {} depth || width>bay.WidthMm || height>bay.HeightMm || depth>bay.DepthMm) throw new DomainError(422,"mount_dimensions_invalid");
                }
                else if (slot!="shared" || (profile.MountingJson is {} mounting && JsonNode.Parse(mounting)?["parentProfileKeys"] is JsonArray keys && keys.Count>0 && !keys.Any(k=>k!.GetValue<string>()==support["hardwareProfileKey"]?.GetValue<string>()))) throw new DomainError(422,"mount_support_invalid");
            }
            else if (profile.Kind=="vertical0U")
            {
                var rack = Reference(device,"rackId","racks");
                if (parent is not null || slot is not ("vertical-left" or "vertical-right") || profile.HeightMm is null || profile.HeightMm>Integer(rack,"sizeU",1,1000)*44.45m) throw new DomainError(422,"mount_dimensions_invalid");
            }
            else if (parent is not null || slot is not null) throw new DomainError(422,"mount_support_invalid");
        }
        var groupsByDevice = sets["portGroups"].Values.ToLookup(g=>Id(g,"deviceId"));
        var portsByGroup = sets["ports"].Values.ToLookup(p=>Id(p,"groupId"));
        var portOrdinals = new HashSet<(Guid,int)>();
        foreach (var group in sets["portGroups"].Values)
        {
            DataKeys(group,"id","deviceId","type","name","prefix","sortOrder"); _ = Reference(group,"deviceId","devices");
            string type = InventoryRules.PortType(String(group,"type")); if (type=="rj45_poe") throw new DomainError(422,"port_type_invalid");
            _ = FreeText.Validate(String(group,"name"),100); _ = FreeText.Validate(String(group,"prefix"),100); _ = Integer(group,"sortOrder",0,int.MaxValue);
        }
        foreach (var port in sets["ports"].Values)
        {
            DataKeys(port,"id","deviceId","groupId","type","gn","sortOrder","label","status","poe","watts","color","face","powerRole","properties");
            var group = Reference(port,"groupId","portGroups"); var device=Reference(port,"deviceId","devices");
            string type=InventoryRules.PortType(String(port,"type")), role=InventoryRules.PowerRole(String(port,"powerRole"));
            if (Id(group,"deviceId")!=Id(device,"id") || InventoryRules.Family(type)!=String(group,"type")) throw new DomainError(422,"port_scope_invalid");
            int gn=Integer(port,"gn",1,int.MaxValue); _ = Integer(port,"sortOrder",0,int.MaxValue);
            if (!portOrdinals.Add((Id(group,"id"),gn))) throw new DomainError(422,"port_scope_invalid");
            _ = InventoryRules.Status(String(port,"status")); _ = InventoryRules.Face(String(port,"face")); _ = Color(port); _ = Properties(port);
            _ = FreeText.Validate(String(port,"label"),500); _ = InventoryRules.Watts(Number(port,"watts",90));
            if ((Boolean(port,"poe") && InventoryRules.Family(type)!="rj45") || (!FamilyLRules.IsPower(type) && role!="unspecified")) throw new DomainError(422,"port_type_invalid");
        }
        foreach (var device in sets["devices"].Values)
        {
            Guid id=Id(device,"id"); var profile=profiles[id];
            if (profile is null) continue;
            var actual=groupsByDevice[id].ToArray();
            if (actual.Length!=profile.Groups.Count) throw new DomainError(422,"hardware_metadata_invalid");
            for(int i=0;i<profile.Groups.Count;i++)
            {
                var definition=profile.Groups[i]; var group=actual.SingleOrDefault(g=>Integer(g,"sortOrder",0,int.MaxValue)==i);
                if (group is null || String(group,"type")!=definition.Type) throw new DomainError(422,"hardware_metadata_invalid");
                var ports=portsByGroup[Id(group,"id")].ToArray();
                if(ports.Length!=definition.Count) throw new DomainError(422,"hardware_metadata_invalid");
                foreach(var port in ports)
                {
                    int gn=Integer(port,"gn",1,definition.Count);
                    if(Integer(port,"sortOrder",0,int.MaxValue)!=gn-1 || String(port,"face")!=definition.Face || String(port,"powerRole")!=definition.PowerRole) throw new DomainError(422,"hardware_metadata_invalid");
                    var metadata=port["properties"]!.AsObject();
                    var expected=new Dictionary<string,string?> { ["hardwareGroupKey"]=definition.Key,["hardwarePortKey"]=definition.Key+":"+gn,["hardwarePhysicalConnector"]=definition.PhysicalConnector,["hardwarePhysicalFace"]=definition.PhysicalFace,["hardwareInterfaceRole"]=definition.InterfaceRole,["hardwareSignalRole"]=definition.SignalRole,["hardwarePowerSystem"]=definition.PowerSystem };
                    foreach(var item in expected) if(metadata[item.Key]?.GetValue<string>()!=item.Value) throw new DomainError(422,"hardware_metadata_invalid");
                }
            }
        }
        var occupied=new HashSet<Guid>();
        foreach(var connection in sets["connections"].Values)
        {
            DataKeys(connection,"id","fromPortId","toPortId","note","color","patch","createdAt","properties");
            var a=Reference(connection,"fromPortId","ports"); var b=Reference(connection,"toPortId","ports");
            if(!occupied.Add(Id(a,"id")) || !occupied.Add(Id(b,"id"))) throw new DomainError(422,"port_occupied");
            // The editor may mark an already connected endpoint faulty/disabled without removing its cable.
            // Archives preserve that documented state; the live creation command retains its port-blocked guard.
            InventoryRules.RequireConnectorPair(String(a,"type"),String(b,"type"),profiles[Id(a,"deviceId")] is not null || profiles[Id(b,"deviceId")] is not null);
            string? PowerClassification(JsonObject p) => String(p,"type")=="power_dc" ? p["properties"]?["hardwarePowerSystem"]?.GetValue<string>() ?? p["properties"]?["declaredPowerSystem"]?.GetValue<string>() ?? "dc" : null;
            FamilyLRules.PowerPair(String(a,"type"),String(a,"powerRole"),PowerClassification(a),String(b,"type"),String(b,"powerRole"),PowerClassification(b));
            _=FreeText.Validate(String(connection,"note"),2000);_=Color(connection);_=InventoryRules.Patch(String(connection,"patch"));_=Properties(connection);
            if(!DateTimeOffset.TryParse(String(connection,"createdAt"),System.Globalization.CultureInfo.InvariantCulture,System.Globalization.DateTimeStyles.None,out _)) throw new DomainError(422,"inventory_archive_invalid");
        }
    }

    private static InventoryHardwareProfiles.Profile? InventoryDataProfile(JsonObject row)
    {
        if(row["hardwareProfileKey"] is null) return null;
        var properties=row["properties"] as JsonObject ?? throw new DomainError(422,"properties_invalid");
        var profile=InventoryHardwareProfiles.Find(String(row,"hardwareProfileKey"),String(properties,"hardwareProfileVersion")) ?? throw new DomainError(422,"hardware_revision_unknown");
        var expected=HardwareProperties(profile);
        foreach(string key in new[]{"hardwareProfileVersion","physicalDimensionsMm","hardwareIdentity","declaredPassthrough","hardwareMounting","hardwareConfiguration","hardwareContinuities"})
            if(!JsonNode.DeepEquals(properties[key],expected[key])) throw new DomainError(422,"hardware_metadata_invalid");
        return profile;
    }

    private static ParsedInventoryData LoadDemoInventoryData()
    {
        var assembly=typeof(InventoryStore).Assembly;
        byte[] Resource(string name) { using var stream=assembly.GetManifestResourceStream("RackClick.Demo50."+name) ?? throw new InvalidOperationException("demo50_unavailable");using var output=new MemoryStream();stream.CopyTo(output);return output.ToArray(); }
        var manifestBytes=Resource("manifest.json");
        if(Convert.ToHexStringLower(SHA256.HashData(manifestBytes))!="45700b0eea13282d779d4a362e1b24bbe7ec0afad591bf4cd5b42ddcab1f70fb") throw new InvalidOperationException("demo50_pin_invalid");
        var manifest=JsonNode.Parse(manifestBytes)!.AsObject();var customers=new JsonArray();
        foreach(var item in manifest["customers"]!.AsArray())
        {
            var pin=item!.AsObject(); var bytes=Resource(String(pin,"file"));
            if(bytes.Length!=Integer(pin,"bytes",1,InventoryDataMaximumBytes) || Convert.ToHexStringLower(SHA256.HashData(bytes))!=String(pin,"sha256")) throw new InvalidOperationException("demo50_pin_invalid");
            using var document=JsonDocument.Parse(bytes);var data=Object(document.RootElement);
            if(String(data,"customerId")!=String(pin,"customerId") || DataRevision(data)!=DataRevision(pin) || String(data,"kind")!="RackClickInventory" || String(data,"scope")!="customer" || Integer(data,"formatVersion",1,1)!=1) throw new InvalidOperationException("demo50_pin_invalid");
            customers.Add(new JsonObject { ["id"]=String(pin,"customerId"),["name"]=String(pin,"name"),["revision"]=DataRevision(pin),["inventory"]=data["inventory"]!.DeepClone() });
        }
        var root=new JsonObject { ["formatVersion"]=1,["kind"]="RackClickInventoryBackup",["schemaVersion"]=48,["createdAt"]="2026-11-12T00:00:00Z",["customers"]=customers };
        var result=ParseInventoryData(JsonSerializer.SerializeToUtf8Bytes(root,Json));
        if(result.Counts!=new InventoryDataCounts(50,66,88,226,180,1563,2869,20665,2207)) throw new InvalidOperationException("demo50_count_invalid");
        return result;
    }
}
