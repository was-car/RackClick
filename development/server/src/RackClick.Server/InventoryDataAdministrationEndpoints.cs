using System.Text.Json;
using RackClick.Domain;

namespace RackClick.Server;

public static class InventoryDataAdministrationEndpoints
{
    internal const long MaximumBodyBytes=45L*1024*1024;
    internal static bool IsLargeInventoryDataRequest(HttpRequest request) => request.Method=="POST" &&
        (request.Path.Equals("/api/v1/admin/inventory-data/preview",StringComparison.OrdinalIgnoreCase) || request.Path.Equals("/api/v1/admin/inventory-data/restore",StringComparison.OrdinalIgnoreCase));
    public static void MapInventoryDataAdministration(this WebApplication app,InventoryStore inventory)
    {
        const string path="/api/v1/admin/inventory-data";
        app.MapGet(path,async Task<IResult> (HttpContext c)=>Results.Ok(await inventory.ReadInventoryDataAdministration(Actor(c,false),c.RequestAborted)));
        app.MapPost(path+"/preview",async Task<IResult> (JsonElement input,HttpContext c)=>Results.Ok(await inventory.PreviewInventoryData(Actor(c,true),input,c.RequestAborted))).RequireRateLimiting("inventoryData");
        app.MapGet(path+"/operations/{requestId:guid}",async Task<IResult> (Guid requestId,HttpContext c)=>Results.Ok(await inventory.InventoryDataOperation(Actor(c,false),requestId,c.RequestAborted)));
        app.MapPost(path+"/operations/{requestId:guid}/cancel",async Task<IResult> (Guid requestId,JsonElement input,HttpContext c)=>
        {
            if(!Guid.TryParse(c.Request.Headers["Idempotency-Key"],out var header) || header!=requestId) throw new DomainError(422,"request_id_mismatch");
            return Results.Ok(await inventory.CancelInventoryData(Actor(c,true),requestId,input,Revisions.Parse(c.Request.Headers.IfMatch.ToString()),c.RequestAborted));
        });
        foreach(string action in new[]{"backup","demo50","restore"})
            app.MapPost(path+"/"+action,async Task<IResult> (JsonElement input,HttpContext c)=>
            {
                if(!Guid.TryParse(c.Request.Headers["Idempotency-Key"],out var request) || request==Guid.Empty) throw new DomainError(422,"request_id_invalid");
                var result=await inventory.ExecuteInventoryData(Actor(c,true),action,input,Revisions.Parse(c.Request.Headers.IfMatch.ToString()),request,c.RequestAborted);
                c.Response.Headers.ETag=Revisions.ETag(result.SystemhausRevision);return Results.Ok(result);
            }).RequireRateLimiting("inventoryData");
    }
    private static Actor Actor(HttpContext c,bool mutation)
    {
        var actor=((SessionIdentity)c.Items["session"]!).Actor;if(!mutation) return actor;
        if(!c.Request.Headers.TryGetValue("X-RackClick-Actor",out var header)) throw new DomainError(422,"actor_required");
        if(!Guid.TryParse(header.ToString(),out var expected) || expected==Guid.Empty) throw new DomainError(422,"actor_invalid");
        return actor.Id==expected?actor:throw new DomainError(409,"actor_changed");
    }
}
