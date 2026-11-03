using RackClick.Domain;
namespace RackClick.Server;

/// <summary>Own recovery-code generation requires the current password and an MFA-verified session.</summary>
public sealed record MfaRecoveryCodesRequest(string? Password);

public static class MfaRecoveryCodesEndpoints
{
    public static void MapMfaRecoveryCodes(this WebApplication app, PostgresStore store, bool available)
    {
        app.MapGet("/api/v1/me/mfa/recovery-codes", async (HttpContext c) =>
        {
            var value = await store.ReadOwnRecoveryCodeStatus(Actor(c), c.RequestAborted);
            c.Response.Headers.ETag = Revisions.ETag(value.Revision);
            return TypedResults.Ok(value);
        })
            .WithName("ReadOwnRecoveryCodeStatus").WithSummary("Read only the remaining own recovery-code count, never code values.");
        app.MapPost("/api/v1/me/mfa/recovery-codes", async (MfaRecoveryCodesRequest input, HttpContext c) =>
        {
            var actor = Actor(c);
            if (!Guid.TryParse(c.Request.Headers["X-RackClick-Actor"], out var expected) || expected != actor.Id)
                throw new DomainError(409, "actor_changed");
            if (!Guid.TryParse(c.Request.Headers["Idempotency-Key"], out var request) || request == Guid.Empty)
                throw new DomainError(422, "request_id_invalid");
            c.Response.Headers.CacheControl = "no-store";
            return TypedResults.Ok(await store.GenerateOwnRecoveryCodes(actor, input.Password,
                Revisions.Parse(c.Request.Headers.IfMatch.ToString()), request, available, c.RequestAborted));
        }).RequireRateLimiting("login").WithName("GenerateOwnRecoveryCodes")
            .WithSummary("Replace own recovery codes; disclose values once, receipts contain no codes.");
        app.MapGet("/api/v1/me/mfa/recovery-codes/operations/{requestId:guid}", async (Guid requestId, HttpContext c) =>
        {
            var value = await store.ReadOwnRecoveryCodesReceipt(Actor(c), requestId, c.RequestAborted);
            return value is null ? Results.Json(new { recorded = false, requestId }) : Results.Json(new { recorded = true, requestId, result = value });
        }).WithName("ReadOwnRecoveryCodesReceipt").WithSummary("Recover the operation outcome without redisclosing recovery codes.");
    }
    private static Actor Actor(HttpContext c) => ((SessionIdentity)c.Items["session"]!).Actor;
}
