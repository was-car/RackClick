using System.Text.Json;
using Npgsql;
using RackClick.Domain;
using static RackClick.Server.InventoryJson;

namespace RackClick.Server;

public sealed partial class InventoryStore
{
    // operation_cancellation is customer-FK-bound. A global inventory operation uses the existing
    // operation journal for its terminal fence instead of creating a fictitious customer or changing SQL.
    private sealed record InventoryDataFence(string Kind,string State,string Action,Guid RequestId,
        Guid OperationId,long SystemhausRevision,object? Operation);
    private static string DataDigest(Actor actor,string action,long expected,string? archiveSha256) =>
        Secrets.Digest(JsonSerializer.Serialize(new { kind="inventoryData",systemhausId=actor.HouseId,action,expected,archiveSha256 },Json));
    private static InventoryDataFence? StoredDataFence(string json,Guid requestId)
    {
        try
        {
            using var document=JsonDocument.Parse(json);var root=Object(document.RootElement);
            if(!root.ContainsKey("state")) return null;
            DataKeys(root,"kind","state","action","requestId","operationId","systemhausRevision","operation");
            var fence=JsonSerializer.Deserialize<InventoryDataFence>(json,Json);
            if(fence is null || fence.Kind!="inventoryData" || fence.State!="cancelled" || fence.Action is not ("backup" or "restore" or "demo50") ||
                fence.RequestId!=requestId || fence.OperationId==Guid.Empty || fence.SystemhausRevision<1 || fence.Operation is not null)
                throw new DomainError(404,"not_found");
            return fence;
        }
        catch(Exception error) when(error is JsonException or InvalidOperationException or ArgumentException or DomainError)
        { throw new DomainError(404,"not_found"); }
    }

    public async Task<object> CancelInventoryData(Actor actor,Guid requestId,JsonElement input,long expected,CancellationToken ct)
    {
        if(requestId==Guid.Empty) throw new DomainError(422,"request_id_invalid");
        var body=Object(input);DataKeys(body,"action","archiveSha256");string action=String(body,"action");
        if(action is not ("backup" or "restore" or "demo50")) throw new DomainError(422,"request_invalid");
        string? sha=null;
        if(action=="restore")
        {
            sha=String(body,"archiveSha256");
            if(sha.Length!=64 || sha.Any(c=>c is not (>= '0' and <= '9') and not (>= 'a' and <= 'f'))) throw new DomainError(422,"inventory_archive_hash_mismatch");
        }
        else if(body["archiveSha256"] is not null) throw new DomainError(422,"request_invalid");
        if(action=="demo50") sha=DemoInventoryData.Value.Sha256;
        string digest=DataDigest(actor,action,expected,sha);
        await using var db=await source.OpenConnectionAsync(ct);await using var tx=await db.BeginTransactionAsync(ct);
        await PostgresStore.LockOperation(db,tx,actor,requestId,ct,allowReport:true);
        long revision=await DataHouseRevision(db,tx,actor,true,ct);await DataAuthority(db,tx,actor,action,ct);
        string? stored=null;
        await using(var command=Cmd(db,tx,"SELECT request_hash,result_json::text FROM operation WHERE systemhaus_id=@house AND actor_id=@actor AND request_id=@request",("house",actor.HouseId),("actor",actor.Id),("request",requestId)))
        await using(var row=await command.ExecuteReaderAsync(ct))
            if(await row.ReadAsync(ct)) { if(row.GetString(0)!=digest) throw new DomainError(409,"request_id_reused");stored=row.GetString(1); }
        InventoryDataResult? operation=null;string state;
        if(stored is not null)
        {
            if(StoredDataFence(stored,requestId) is {} fence) { state=fence.State;action=fence.Action; }
            else { operation=StoredDataResult(stored,requestId);state="committed";action=operation.Action; }
        }
        else
        {
            await OperationCancellation.EnsureNotCanceled(db,tx,actor,requestId,digest,ct);
            Guid id=Guid.NewGuid();state="cancelled";
            var fence=new InventoryDataFence("inventoryData",state,action,requestId,id,revision,null);
            string metadata=JsonSerializer.Serialize(new { action,state,systemhausRevision=revision,expectedRevision=expected,archiveSha256=sha },Json);
            await Exec(db,tx,"INSERT INTO audit_event(id,systemhaus_id,actor_id,request_id,action,resource_id,before_json,after_json) VALUES(@id,@house,@actor,@request,'inventory.data.cancel',@house,NULL,CAST(@metadata AS jsonb))",ct,
                ("id",id),("house",actor.HouseId),("actor",actor.Id),("request",requestId),("metadata",metadata));
            await Exec(db,tx,"INSERT INTO operation(systemhaus_id,actor_id,request_id,request_hash,result_json) VALUES(@house,@actor,@request,@hash,CAST(@result AS jsonb))",ct,
                ("house",actor.HouseId),("actor",actor.Id),("request",requestId),("hash",digest),("result",JsonSerializer.Serialize(fence,Json)));
        }
        await DataAuthority(db,tx,actor,action,ct);await tx.CommitAsync(ct);
        return new { state,requestId,operation };
    }
}
