using System.Text.Json;
using System.Text.Json.Nodes;
using Npgsql;
using RackClick.Domain;
using static RackClick.Server.InventoryJson;

namespace RackClick.Server;

public sealed partial class InventoryStore
{
    private static async Task DataAuthority(NpgsqlConnection db, NpgsqlTransaction tx, Actor actor, string? action, CancellationToken ct)
    {
        await PostgresStore.RequireCurrentSession(db,tx,actor,ct);
        string[] required=action=="backup" ? [Capabilities.HouseManage,Capabilities.SecurityManage,Capabilities.InventoryRead,Capabilities.ReportsExport]
            : action is "restore" or "demo50" or "preview" ? [Capabilities.HouseManage,Capabilities.SecurityManage,Capabilities.CustomerCreate,Capabilities.InventoryEdit]
            : [Capabilities.HouseManage,Capabilities.SecurityManage];
        foreach(string capability in required)
            if(!await PostgresStore.Can(db,tx,actor,null,capability,ct)) throw new DomainError(403,"forbidden");
    }
    private static async Task<long> DataHouseRevision(NpgsqlConnection db,NpgsqlTransaction tx,Actor actor,bool writing,CancellationToken ct)
    {
        await using var command=Cmd(db,tx,"SELECT revision FROM systemhaus WHERE id=@house"+(writing?" FOR UPDATE":" FOR SHARE"),("house",actor.HouseId));
        return await command.ExecuteScalarAsync(ct) is long revision ? revision : throw new DomainError(404,"not_found");
    }
    private static async Task<List<(Guid Id,string Name,long Revision)>> DataCustomers(NpgsqlConnection db,NpgsqlTransaction tx,Actor actor,CancellationToken ct,int maximum=500)
    {
        await using var command=Cmd(db,tx,"SELECT id,name,revision FROM customer WHERE systemhaus_id=@house ORDER BY id FOR SHARE",("house",actor.HouseId));
        await using var reader=await command.ExecuteReaderAsync(ct);var result=new List<(Guid,string,long)>();
        while(await reader.ReadAsync(ct)) { if(result.Count>=maximum) throw new DomainError(422,"inventory_archive_too_large");result.Add((reader.GetGuid(0),reader.GetString(1),reader.GetInt64(2))); }
        return result;
    }
    private static async Task<InventoryDataCounts> DataCounts(NpgsqlConnection db,NpgsqlTransaction tx,Actor actor,CancellationToken ct)
    {
        var tables=new[]{"customer","inventory_site","inventory_building","inventory_room","inventory_rack","inventory_device","inventory_port_group","inventory_port","inventory_connection"};
        var counts=new int[9];
        for(int i=0;i<tables.Length;i++)
        {
            await using var command=Cmd(db,tx,$"SELECT count(*) FROM {tables[i]} WHERE systemhaus_id=@house",("house",actor.HouseId));
            counts[i]=checked((int)(long)(await command.ExecuteScalarAsync(ct))!);
        }
        return new(counts[0],counts[1],counts[2],counts[3],counts[4],counts[5],counts[6],counts[7],counts[8]);
    }
    public async Task<object> ReadInventoryDataAdministration(Actor actor,CancellationToken ct)
    {
        await using var db=await source.OpenConnectionAsync(ct);await using var tx=await db.BeginTransactionAsync(ct);
        long revision=await DataHouseRevision(db,tx,actor,false,ct);await DataAuthority(db,tx,actor,null,ct);
        _=await DataCustomers(db,tx,actor,ct,int.MaxValue);var counts=await DataCounts(db,tx,actor,ct);
        var result=new { systemhausRevision=revision,empty=counts.Customers==0,counts,demo=new { available=true,counts=DemoInventoryData.Value.Counts },maxArchiveBytes=InventoryDataMaximumBytes };
        await DataAuthority(db,tx,actor,null,ct);await tx.CommitAsync(ct);return result;
    }
    public async Task<object> PreviewInventoryData(Actor actor,JsonElement input,CancellationToken ct)
    {
        await using var db=await source.OpenConnectionAsync(ct);await using var tx=await db.BeginTransactionAsync(ct);
        _=await DataHouseRevision(db,tx,actor,false,ct);await DataAuthority(db,tx,actor,"preview",ct);
        var body=Object(input);DataKeys(body,"contentBase64");var archive=DecodeInventoryData(String(body,"contentBase64"));
        await ValidateDataCatalog(db,tx,archive,ct);
        await DataAuthority(db,tx,actor,"preview",ct);await tx.CommitAsync(ct);
        return new { archiveSha256=archive.Sha256,byteLength=archive.Bytes.Length,counts=archive.Counts,format=InventoryDataFormat,schemaVersion=48 };
    }
    private static async Task ValidateDataCatalog(NpgsqlConnection db,NpgsqlTransaction tx,ParsedInventoryData archive,CancellationToken ct)
    {
        // JSON syntax alone permits strings/numbers which PostgreSQL jsonb cannot represent (e.g. U+0000).
        // Parse with the real target engine during preview, without writing an archive or inventory row.
        try
        {
            await using var compatible=Cmd(db,tx,"SELECT CAST(@archive AS jsonb) IS NOT NULL",("archive",System.Text.Encoding.UTF8.GetString(archive.Bytes)));
            _=await compatible.ExecuteScalarAsync(ct);
        }
        catch(PostgresException error) when(error.SqlState.StartsWith("22",StringComparison.Ordinal))
        { throw new DomainError(422,"inventory_archive_invalid"); }
        var profiles=new Dictionary<(string,string),InventoryHardwareProfiles.Profile>();
        foreach(var customer in archive.Customers)
            foreach(string collection in new[]{"racks","devices"})
                foreach(var item in customer!["inventory"]![collection]!.AsArray())
                    if(InventoryDataProfile(item!.AsObject()) is {} profile) profiles.TryAdd((profile.Key,profile.Revision),profile);
        foreach(var profile in profiles.Values) _=await ReadHardwareDefinition(db,tx,profile,ct);
    }
    private static InventoryDataResult StoredDataResult(string json,Guid request)
    {
        try
        {
            var result=JsonSerializer.Deserialize<InventoryDataResult>(json,Json);
            if(result is null || result.Kind!="inventoryData" || result.RequestId!=request || result.OperationId==Guid.Empty || result.SystemhausRevision<1 ||
                result.Action is not ("backup" or "restore" or "demo50") || (result.Action=="backup")!=(result.Archive is not null)) throw new DomainError(404,"not_found");
            if(result.Archive is {} archive)
            {
                if(archive.Format!=InventoryDataFormat || archive.Filename!=$"rackclick-inventory-backup-{result.OperationId:D}.json" || archive.ContentType!="application/json; charset=utf-8" || archive.Encoding!="utf-8" || archive.ByteLength is <1 or >InventoryDataMaximumBytes) throw new DomainError(404,"not_found");
                var parsed=DecodeInventoryData(archive.ContentBase64);
                if(parsed.Sha256!=archive.Sha256 || parsed.Bytes.Length!=archive.ByteLength || parsed.Counts!=result.Counts) throw new DomainError(404,"not_found");
            }
            return result;
        }
        catch(Exception error) when(error is JsonException or InvalidOperationException or ArgumentException or DomainError)
        { throw new DomainError(404,"not_found"); }
    }
    public async Task<object> InventoryDataOperation(Actor actor,Guid requestId,CancellationToken ct)
    {
        if(requestId==Guid.Empty) throw new DomainError(422,"request_id_invalid");
        await using var db=await source.OpenConnectionAsync(ct);await using var tx=await db.BeginTransactionAsync(ct);
        await PostgresStore.LockOperation(db,tx,actor,requestId,ct,allowReport:true);
        _=await DataHouseRevision(db,tx,actor,false,ct);await DataAuthority(db,tx,actor,null,ct);
        InventoryDataResult? result=null;InventoryDataFence? fence=null;
        await using(var command=Cmd(db,tx,"SELECT result_json::text FROM operation WHERE systemhaus_id=@house AND actor_id=@actor AND request_id=@request",("house",actor.HouseId),("actor",actor.Id),("request",requestId)))
            if(await command.ExecuteScalarAsync(ct) is string json) { fence=StoredDataFence(json,requestId);if(fence is null) result=StoredDataResult(json,requestId); }
        await DataAuthority(db,tx,actor,result?.Action ?? fence?.Action,ct);await tx.CommitAsync(ct);
        return new { state=fence is not null?"cancelled":result is null?"notRecorded":"committed",requestId,operation=result };
    }

    public async Task<InventoryDataResult> ExecuteInventoryData(Actor actor,string action,JsonElement input,long expected,Guid requestId,CancellationToken ct)
    {
        if(requestId==Guid.Empty) throw new DomainError(422,"request_id_invalid");
        if(action is not ("backup" or "restore" or "demo50")) throw new DomainError(422,"request_invalid");
        await using var db=await source.OpenConnectionAsync(ct);await using var tx=await db.BeginTransactionAsync(ct);
        try
        {
            await PostgresStore.LockOperation(db,tx,actor,requestId,ct,allowReport:true);
            long revision=await DataHouseRevision(db,tx,actor,true,ct);await DataAuthority(db,tx,actor,action,ct);
            var body=Object(input);ParsedInventoryData? imported=null;
            if(action=="backup") DataKeys(body);
            else if(action=="demo50")
            {
                DataKeys(body,"confirmation");if(String(body,"confirmation")!="LOAD DEMO50") throw new DomainError(422,"confirmation_required");
                imported=DemoInventoryData.Value;
            }
            else
            {
                DataKeys(body,"contentBase64","archiveSha256","confirmation");
                if(String(body,"confirmation")!="RESTORE INVENTORY") throw new DomainError(422,"confirmation_required");
                imported=DecodeInventoryData(String(body,"contentBase64"));
                if(String(body,"archiveSha256")!=imported.Sha256) throw new DomainError(422,"inventory_archive_hash_mismatch");
            }
            string digest=DataDigest(actor,action,expected,imported?.Sha256);
            await OperationCancellation.EnsureNotCanceled(db,tx,actor,requestId,digest,ct);
            InventoryDataResult? prior=null;
            await using(var command=Cmd(db,tx,"SELECT request_hash,result_json::text FROM operation WHERE systemhaus_id=@house AND actor_id=@actor AND request_id=@request",("house",actor.HouseId),("actor",actor.Id),("request",requestId)))
            await using(var row=await command.ExecuteReaderAsync(ct))
                if(await row.ReadAsync(ct)) { if(row.GetString(0)!=digest) throw new DomainError(409,"request_id_reused");if(StoredDataFence(row.GetString(1),requestId) is not null) throw new DomainError(409,"operation_cancelled");prior=StoredDataResult(row.GetString(1),requestId); }
            if(prior is not null) { await DataAuthority(db,tx,actor,action,ct);await tx.CommitAsync(ct);return prior; }
            Revisions.Require(expected,revision);
            var customers=await DataCustomers(db,tx,actor,ct);Guid operation=Guid.NewGuid();InventoryDataArchive? artifact=null;InventoryDataCounts counts;
            long next=revision;
            if(action=="backup")
            {
                // All existing customer revisions remain shared-locked through snapshot, audit and commit.
                var rowCounts=await DataCounts(db,tx,actor,ct);
                long rows=(long)rowCounts.Customers+rowCounts.Sites+rowCounts.Buildings+rowCounts.Rooms+rowCounts.Racks+rowCounts.Devices+rowCounts.PortGroups+rowCounts.Ports+rowCounts.Connections;
                if(rows>InventoryDataMaximumRows) throw new DomainError(422,"inventory_archive_too_large");
                var exported=new JsonArray();int snapshotBytes=0;
                foreach(var customer in customers)
                {
                    string text=await Snapshot(db,tx,actor,customer.Id,ct);
                    snapshotBytes=checked(snapshotBytes+System.Text.Encoding.UTF8.GetByteCount(text));
                    if(snapshotBytes>InventoryDataMaximumBytes) throw new DomainError(422,"inventory_archive_too_large");
                    var snapshot=JsonNode.Parse(text)!.AsObject();var inventory=new JsonObject();
                    foreach(string collection in DataCollections) inventory[collection]=snapshot[collection]!.DeepClone();
                    exported.Add(new JsonObject { ["id"]=customer.Id.ToString("D"),["name"]=customer.Name,["revision"]=customer.Revision,["inventory"]=inventory });
                }
                var archive=new JsonObject { ["formatVersion"]=1,["kind"]="RackClickInventoryBackup",["schemaVersion"]=48,["createdAt"]=DateTimeOffset.UtcNow.ToString("O"),["customers"]=exported };
                var parsed=ParseInventoryData(JsonSerializer.SerializeToUtf8Bytes(archive,Json));counts=parsed.Counts;
                artifact=new(InventoryDataFormat,$"rackclick-inventory-backup-{operation:D}.json","application/json; charset=utf-8","utf-8",parsed.Bytes.Length,parsed.Sha256,Convert.ToBase64String(parsed.Bytes));
            }
            else
            {
                if(customers.Count!=0) throw new DomainError(409,"inventory_not_empty");
                if(revision>=InventoryDataMaximumRevision) throw new DomainError(409,"inventory_revision_exhausted");
                await ValidateDataCatalog(db,tx,imported!,ct);
                await InsertInventoryData(db,tx,actor,imported!,ct);counts=imported!.Counts;next=checked(revision+1);
                await Exec(db,tx,"UPDATE systemhaus SET revision=@next WHERE id=@house",ct,("next",next),("house",actor.HouseId));
            }
            var result=new InventoryDataResult("inventoryData",action,requestId,operation,next,counts,artifact);
            var metadata=JsonSerializer.Serialize(new { action,sourceRevision=revision,systemhausRevision=next,counts,format=InventoryDataFormat,byteLength=artifact?.ByteLength ?? imported?.Bytes.Length,sha256=artifact?.Sha256 ?? imported?.Sha256 },Json);
            await Exec(db,tx,"INSERT INTO audit_event(id,systemhaus_id,actor_id,request_id,action,resource_id,before_json,after_json) VALUES(@operation,@house,@actor,@request,@action,@house,NULL,CAST(@metadata AS jsonb))",ct,
                ("operation",operation),("house",actor.HouseId),("actor",actor.Id),("request",requestId),("action","inventory.data."+action),("metadata",metadata));
            await Exec(db,tx,"INSERT INTO operation(systemhaus_id,actor_id,request_id,request_hash,result_json) VALUES(@house,@actor,@request,@hash,CAST(@result AS jsonb))",ct,
                ("house",actor.HouseId),("actor",actor.Id),("request",requestId),("hash",digest),("result",JsonSerializer.Serialize(result,Json)));
            await DataAuthority(db,tx,actor,action,ct);await tx.CommitAsync(ct);return result;
        }
        catch(PostgresException error) when(error.SqlState is "23503" or "23505" or "23514" or "22001" or "22003" or "22007" or "22P02")
        { throw new DomainError(409,"inventory_data_conflict"); }
    }

    private static async Task InsertInventoryData(NpgsqlConnection db,NpgsqlTransaction tx,Actor actor,ParsedInventoryData archive,CancellationToken ct)
    {
        // The mapping is closed source code. External identifiers, values and JSON are exclusively parameters.
        (string Collection,string Table,string[] Fields)[] mapping=[
            ("sites","inventory_site",["name","properties"]),
            ("buildings","inventory_building",["site_id:siteId","name","properties"]),
            ("rooms","inventory_room",["building_id:buildingId","name","properties"]),
            ("racks","inventory_rack",["room_id:roomId","name","location","size_u:sizeU","properties","hardware_profile_key:hardwareProfileKey"]),
            ("devices","inventory_device",["kind","rack_id:rackId","room_id:roomId","name","size_u:sizeU","sort_order:sortOrder","poe_budget:poeBudget","properties","hardware_profile_key:hardwareProfileKey","mount_parent_id:mountParentId","mount_slot_key:mountSlotKey"]),
            ("portGroups","inventory_port_group",["device_id:deviceId","type","name","prefix","sort_order:sortOrder"]),
            ("ports","inventory_port",["device_id:deviceId","group_id:groupId","type","gn","sort_order:sortOrder","label","status","poe","watts","color","face","power_role:powerRole","properties"]),
            ("connections","inventory_connection",["note","color","patch","created_at:createdAt","properties"])
        ];
        foreach(var node in archive.Customers)
        {
            var customer=node!.AsObject();Guid id=Id(customer,"id");
            await Exec(db,tx,"INSERT INTO customer(id,systemhaus_id,name,revision) VALUES(@id,@house,@name,@revision)",ct,("id",id),("house",actor.HouseId),("name",String(customer,"name")),("revision",DataRevision(customer)));
            var inventory=customer["inventory"]!.AsObject();
            foreach(var item in mapping)
            {
                var fields=item.Fields.Select(field=>field.Split(':')).ToArray();
                var columns=new[]{"id","systemhaus_id","customer_id"}.Concat(fields.Select(f=>f[0])).ToArray();
                async Task Insert(IEnumerable<JsonNode?> values)
                {
                    var rows=new JsonArray();
                    foreach(var value in values)
                    {
                        var row=new JsonObject { ["id"]=value!["id"]!.DeepClone(),["systemhaus_id"]=actor.HouseId.ToString("D"),["customer_id"]=id.ToString("D") };
                        foreach(var field in fields) row[field[0]]=value[field[^1]]?.DeepClone();rows.Add(row);
                    }
                    if(rows.Count==0) return;
                    string sql=$"INSERT INTO {item.Table}({string.Join(',',columns)}) SELECT {string.Join(',',columns.Select(c=>"x."+c))} FROM jsonb_populate_recordset(NULL::{item.Table},CAST(@rows AS jsonb)) x";
                    await Exec(db,tx,sql,ct,("rows",rows.ToJsonString()));
                }
                var collection=inventory[item.Collection]!.AsArray();
                if(item.Collection=="devices") { await Insert(collection.Where(d=>d!["mountParentId"] is null));await Insert(collection.Where(d=>d!["mountParentId"] is not null)); }
                else await Insert(collection);
            }
            var endpoints=new JsonArray();
            foreach(var connection in inventory["connections"]!.AsArray())
                for(int ordinal=0;ordinal<2;ordinal++) endpoints.Add(new JsonObject { ["connection_id"]=connection!["id"]!.DeepClone(),["ordinal"]=ordinal,["port_id"]=connection[ordinal==0?"fromPortId":"toPortId"]!.DeepClone() });
            if(endpoints.Count>0) await Exec(db,tx,"INSERT INTO inventory_connection_endpoint(systemhaus_id,customer_id,connection_id,ordinal,port_id) SELECT @house,@customer,x.connection_id,x.ordinal,x.port_id FROM jsonb_to_recordset(CAST(@rows AS jsonb)) AS x(connection_id uuid,ordinal smallint,port_id uuid)",ct,("house",actor.HouseId),("customer",id),("rows",endpoints.ToJsonString()));
        }
    }
}
