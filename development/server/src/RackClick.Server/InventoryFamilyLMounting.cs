using System.Text.Json.Nodes;
using Npgsql;
using RackClick.Domain;
using static RackClick.Server.InventoryJson;
namespace RackClick.Server;
public sealed partial class InventoryStore
{
    private static JsonObject HardwareProperties(InventoryHardwareProfiles.Profile profile)
    {
        var result = new JsonObject { ["hardwareProfileVersion"] = profile.Revision, ["color"] = profile.Color,
            ["icon"] = profile.Kind == "shelf" ? "▤" : "▥",
            ["physicalDimensionsMm"] = new JsonObject { ["width"] = JsonValue.Create(profile.WidthMm), ["height"] = JsonValue.Create(profile.HeightMm), ["depth"] = JsonValue.Create(profile.DepthMm) } };
        if (profile.Manufacturer is not null) result["hardwareIdentity"] = new JsonObject { ["manufacturer"] = profile.Manufacturer, ["family"] = profile.Family, ["model"] = profile.Model, ["sku"] = profile.Sku };
        if (profile.Passthrough is { } continuity) result["declaredPassthrough"] = new JsonObject { ["fromGroupKey"] = continuity.FrontGroupKey, ["toGroupKey"] = continuity.RearGroupKey, ["rule"] = "sameOrdinal", ["tracingImplemented"] = false };
        if (profile.MountingJson is not null) result["hardwareMounting"] = JsonNode.Parse(profile.MountingJson);
        if (profile.ConfigurationJson is not null) result["hardwareConfiguration"] = JsonNode.Parse(profile.ConfigurationJson);
        if (profile.ContinuitiesJson is not null) result["hardwareContinuities"] = JsonNode.Parse(profile.ContinuitiesJson);
        return result;
    }
    private static async Task<List<Guid>> CreateProfileGroups(NpgsqlConnection db, NpgsqlTransaction tx, Actor actor, Guid customer, Guid id, InventoryHardwareProfiles.Profile profile, CancellationToken ct)
    {
        var created = new List<Guid>();
        for (int order = 0; order < profile.Groups.Count; order++)
        {
            var group = profile.Groups[order];
            Guid[] ids = await AddGroup(db, tx, actor, customer, id, new JsonObject { ["type"] = group.Type, ["count"] = group.Count, ["name"] = group.Name, ["prefix"] = group.Prefix }, order, ct, 512);
            created.AddRange(ids);
            await Exec(db, tx, "UPDATE inventory_port SET face=@face,power_role=@role,properties=jsonb_strip_nulls(jsonb_build_object('hardwareGroupKey',@key::text,'hardwarePortKey',@key::text||':'||gn::text,'hardwarePhysicalConnector',@pc::text,'hardwarePhysicalFace',@physicalFace::text,'hardwareInterfaceRole',@interfaceRole::text,'hardwareSignalRole',@signalRole::text,'hardwarePowerSystem',@powerSystem::text)) WHERE systemhaus_id=@house AND customer_id=@customer AND group_id=@group", ct,
                ("face",group.Face),("role",group.PowerRole),("key",group.Key),("pc",group.PhysicalConnector),("physicalFace",group.PhysicalFace),("interfaceRole",group.InterfaceRole),("signalRole",group.SignalRole),("powerSystem",group.PowerSystem),("house",actor.HouseId),("customer",customer),("group",ids[0]));
        }
        return created;
    }
    private static async Task<Change> CreateRackHardware(NpgsqlConnection db,NpgsqlTransaction tx,Actor actor,Guid customer,JsonObject payload,CancellationToken ct)
    {
        if (payload.Any(f => f.Key is not ("profileKey" or "profileVersion" or "roomId" or "name" or "location"))) throw new DomainError(422,"field_unknown");
        var compiled=InventoryHardwareProfiles.Find(String(payload,"profileKey"),String(payload,"profileVersion")) ?? throw new DomainError(422,"hardware_revision_unknown");
        var profile=await ReadHardwareDefinition(db,tx,compiled,ct);
        if (profile.Kind!="rackContainer" || profile.MountingJson is null) throw new DomainError(422,"hardware_profile_invalid");
        var mounting=JsonNode.Parse(profile.MountingJson)!.AsObject(); int capacity=mounting["capacityU"]!.GetValue<int>();
        if (capacity<1 || capacity>1000) throw new DomainError(422,"hardware_profile_invalid");
        Guid room=Id(payload,"roomId"); await Row(db,tx,actor,customer,"inventory_room",room,ct);
        Guid id=Guid.NewGuid();var properties=HardwareProperties(profile); string name=Names.Validate(String(payload,"name"));
        await Exec(db,tx,"INSERT INTO inventory_rack(id,systemhaus_id,customer_id,room_id,name,location,size_u,properties,hardware_profile_key) VALUES(@id,@house,@customer,@room,@name,@location,@capacity,CAST(@properties AS jsonb),@profile)",ct,
            ("id",id),("house",actor.HouseId),("customer",customer),("room",room),("name",name),("location",payload.ContainsKey("location")?Text(payload,"location"):""),("capacity",capacity),("properties",properties.ToJsonString()),("profile",profile.Key));
        var after=await Row(db,tx,actor,customer,"inventory_rack",id,ct);return new(id,null,after,new {resourceId=id,createdIds=new[]{id}});
    }
    private static async Task<Change> CreateFamilyHardware(NpgsqlConnection db,NpgsqlTransaction tx,Actor actor,Guid customer,JsonObject payload,InventoryHardwareProfiles.Profile profile,CancellationToken ct)
    {
        Guid? rack=null,room=null,parent=OptionalId(payload,"mountParentId"); string? slot=payload["mountSlotKey"] is null?null:String(payload,"mountSlotKey");
        bool roomTarget=FamilyLRules.IsRoom(profile.Kind);
        if(roomTarget)
        {
            if(payload["rackId"] is not null || parent is not null || slot is not null)throw new DomainError(422,"mount_profile_incompatible");
            room=Id(payload,"roomId");await Row(db,tx,actor,customer,"inventory_room",room.Value,ct);
        }
        else
        {
            if(payload["roomId"] is not null)throw new DomainError(422,"mount_profile_incompatible");
            rack=Id(payload,"rackId");var container=await Row(db,tx,actor,customer,"inventory_rack",rack.Value,ct);
            if(profile.Kind=="vertical0U")
            {
                if(parent is not null || slot is not ("vertical-left" or "vertical-right"))throw new DomainError(422,"mount_support_invalid");
                if(profile.HeightMm is null || profile.HeightMm>Integer(container,"size_u",1,1000)*44.45m)throw new DomainError(422,"mount_dimensions_invalid");
            }
            else if(profile.Kind=="sharedU")
            {
                if(parent is null || slot!="shared")throw new DomainError(422,"mount_parent_required");
                var support=await Row(db,tx,actor,customer,"inventory_device",parent.Value,ct);
                if(OptionalId(support,"rack_id")!=rack || support["mount_parent_id"] is not null || support["size_u"] is null || Integer(support,"size_u",0,1000)<=0)throw new DomainError(422,"mount_support_invalid");
                var mounting=profile.MountingJson is null?null:JsonNode.Parse(profile.MountingJson);
                if(mounting?["parentProfileKeys"] is JsonArray keys && keys.Count>0 && !keys.Any(key=>key?.GetValue<string>()==support["hardware_profile_key"]?.GetValue<string>()))throw new DomainError(422,"mount_support_invalid");
            }
            else throw new DomainError(422,"mount_profile_incompatible");
            await using var occupied=Cmd(db,tx,"SELECT EXISTS(SELECT 1 FROM inventory_device WHERE systemhaus_id=@house AND customer_id=@customer AND rack_id=@rack AND mount_slot_key=@slot AND mount_parent_id IS NOT DISTINCT FROM @parent::uuid)",("house",actor.HouseId),("customer",customer),("rack",rack),("slot",slot),("parent",parent));
            if(await occupied.ExecuteScalarAsync(ct) is true)throw new DomainError(409,"mount_slot_occupied");
            await Capacity(db,tx,actor,customer,rack.Value,null,0,ct);
        }
        Guid id=Guid.NewGuid();int order=await NextOrder(db,tx,actor,customer,rack,room,ct);string name=Names.Validate(String(payload,"name"));var properties=HardwareProperties(profile);
        await Exec(db,tx,"INSERT INTO inventory_device(id,systemhaus_id,customer_id,kind,rack_id,room_id,name,size_u,sort_order,properties,hardware_profile_key,mount_parent_id,mount_slot_key) VALUES(@id,@house,@customer,@kind,@rack,@room,@name,@size,@order,CAST(@properties AS jsonb),@profile,@parent,@slot)",ct,
            ("id",id),("house",actor.HouseId),("customer",customer),("kind",roomTarget?"endDevice":"rackEquipment"),("rack",rack),("room",room),("name",name),("size",roomTarget?(int?)null:0),("order",order),("properties",properties.ToJsonString()),("profile",profile.Key),("parent",parent),("slot",slot));
        var created=new List<Guid>{id};created.AddRange(await CreateProfileGroups(db,tx,actor,customer,id,profile,ct));var after=await Row(db,tx,actor,customer,"inventory_device",id,ct);
        return new(id,null,new {device=after,createdIds=created},new {resourceId=id,createdIds=created});
    }
}
