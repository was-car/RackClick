using RackClick.Domain;

namespace RackClick.Server;

public static class MfaAccountEndpoints
{
    public static void MapMfaAccounts(this WebApplication app, PostgresStore store, bool available)
    {
        app.MapGet("/api/v1/me/mfa", async Task<IResult> (HttpContext context) =>
        {
            var value = await store.ReadOwnMfaStatus(Actor(context), available, context.RequestAborted);
            context.Response.Headers.ETag = Revisions.ETag(value.Revision);
            return TypedResults.Ok(value);
        }).WithName("ReadOwnMfaStatus").WithSummary("Read own MFA state and the 45-day grace deadline.");
        app.MapGet("/api/v1/admin/users/{userId:guid}/mfa", async Task<IResult> (Guid userId, HttpContext context) =>
        {
            var value = await store.ReadUserMfaStatus(Actor(context), userId, available, context.RequestAborted);
            context.Response.Headers.ETag = Revisions.ETag(value.Revision);
            return TypedResults.Ok(value);
        }).WithName("ReadUserMfaStatus").WithSummary("Read a user's MFA state with server-side security.manage authorization.");

        foreach (var action in new[] { "enable", "disable", "reset" })
        {
            app.MapPost("/api/v1/me/mfa/" + action, async Task<IResult> (MfaAccountChangeRequest input, HttpContext context) =>
            {
                CheckAction(input, action);
                var result = await store.ChangeOwnMfa(MutationActor(context), action, input.Password,
                    Revisions.Parse(context.Request.Headers.IfMatch.ToString()), RequestId(context), available, context.RequestAborted);
                return Results.Content(result, "application/json");
            }).RequireRateLimiting("login").WithName("OwnMfa" + action).WithSummary("Change own MFA after password reauthentication; grace never restarts.");
            app.MapPost("/api/v1/admin/users/{userId:guid}/mfa/" + action, async Task<IResult> (Guid userId, MfaAccountChangeRequest input, HttpContext context) =>
            {
                CheckAction(input, action);
                var result = await store.ChangeUserMfa(MutationActor(context), userId, action,
                    Revisions.Parse(context.Request.Headers.IfMatch.ToString()), RequestId(context), available, context.RequestAborted);
                return Results.Content(result, "application/json");
            }).RequireRateLimiting("login").WithName("UserMfa" + action).WithSummary("Administer another user's MFA with security.manage and a completed MFA session.");
        }
        app.MapGet("/api/v1/me/mfa/operations/{requestId:guid}", async Task<IResult> (Guid requestId, HttpContext context) =>
            Results.Content(await store.ReadMfaChangeStatus(Actor(context), Actor(context).Id, requestId, false, context.RequestAborted), "application/json"));
        app.MapGet("/api/v1/admin/users/{userId:guid}/mfa/operations/{requestId:guid}", async Task<IResult> (Guid userId, Guid requestId, HttpContext context) =>
            Results.Content(await store.ReadMfaChangeStatus(Actor(context), userId, requestId, true, context.RequestAborted), "application/json"));
    }

    private static Actor Actor(HttpContext context) => ((SessionIdentity)context.Items["session"]!).Actor;
    private static Actor MutationActor(HttpContext context)
    {
        if (!context.Request.Headers.TryGetValue("X-RackClick-Actor", out var header)) throw new DomainError(422, "actor_required");
        if (!Guid.TryParse(header.ToString(), out var expected) || expected == Guid.Empty) throw new DomainError(422, "actor_invalid");
        var actor = Actor(context);
        return actor.Id == expected ? actor : throw new DomainError(409, "actor_changed");
    }
    private static Guid RequestId(HttpContext context) => Guid.TryParse(context.Request.Headers["Idempotency-Key"], out var id) && id != Guid.Empty
        ? id : throw new DomainError(422, "request_id_invalid");
    private static void CheckAction(MfaAccountChangeRequest input, string action)
    {
        if (input.Action is not null && input.Action != action) throw new DomainError(422, "mfa_action_invalid");
    }
}
