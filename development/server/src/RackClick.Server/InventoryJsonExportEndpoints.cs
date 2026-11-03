using System.Text.Json;
using RackClick.Domain;

namespace RackClick.Server;

public static class InventoryJsonExportEndpoints
{
    public static void MapInventoryJsonExports(this WebApplication app, InventoryStore inventory)
    {
        app.MapPost("/api/v1/customers/{id:guid}/exports/inventory-json", async Task<IResult> (Guid id, JsonElement input, HttpContext context) =>
        {
            var actor = ExportActor(context, mutation: true);
            if (!Guid.TryParse(context.Request.Headers["Idempotency-Key"], out Guid request) || request == Guid.Empty)
                throw new DomainError(422, "request_id_invalid");
            var result = await inventory.GenerateInventoryJsonExport(actor, id, input, Revisions.Parse(context.Request.Headers.IfMatch.ToString()), request, context.RequestAborted);
            context.Response.Headers.ETag = Revisions.ETag(result.Revision);
            context.Response.Headers.CacheControl = "no-store";
            return TypedResults.Ok(result);
        }).WithName("GenerateCurrentInventoryJson").WithSummary("Export an authorized current customer inventory snapshot; excludes account/security tables.");
        app.MapGet("/api/v1/customers/{id:guid}/exports/inventory-json/operations/{requestId:guid}", async Task<IResult> (Guid id, Guid requestId, HttpContext context) =>
        {
            var result = await inventory.InventoryJsonExportStatus(ExportActor(context, mutation: false), id, requestId, context.RequestAborted);
            context.Response.Headers.CacheControl = "no-store";
            return TypedResults.Ok(result);
        }).WithName("ReadCurrentInventoryJsonReceipt").WithSummary("Read this actor's confirmed export with current inventory.read and reports.export authority.");
    }

    private static Actor ExportActor(HttpContext context, bool mutation)
    {
        var actor = ((SessionIdentity)context.Items["session"]!).Actor;
        if (!mutation) return actor;
        if (!context.Request.Headers.TryGetValue("X-RackClick-Actor", out var header)) throw new DomainError(422, "actor_required");
        if (!Guid.TryParse(header.ToString(), out Guid expected) || expected == Guid.Empty) throw new DomainError(422, "actor_invalid");
        return expected == actor.Id ? actor : throw new DomainError(409, "actor_changed");
    }
}
