using System.Threading.RateLimiting;
using System.Text.Json;
using Microsoft.AspNetCore.RateLimiting;
using Npgsql;
using RackClick.Domain;
using RackClick.Server;

bool bootstrap = args.Contains("--bootstrap", StringComparer.Ordinal);
bool migrate = args.Contains("--migrate", StringComparer.Ordinal);
bool recoverAdmin = args.Contains("--recover-admin", StringComparer.Ordinal);
bool mfaKeysInit = args.Contains("--mfa-keys-init", StringComparer.Ordinal);
bool mfaRequireAll = args.Contains("--mfa-require-all", StringComparer.Ordinal);
if ((bootstrap ? 1 : 0) + (migrate ? 1 : 0) + (recoverAdmin ? 1 : 0) + (mfaKeysInit ? 1 : 0) + (mfaRequireAll ? 1 : 0) > 1)
{
    Console.WriteLine(JsonSerializer.Serialize(new { status = "rejected", error = "cli_mode_conflict" }));
    Environment.ExitCode = 1;
    return;
}
var builder = WebApplication.CreateBuilder(args.Where(a => a is not ("--bootstrap" or "--migrate" or "--recover-admin" or "--mfa-keys-init" or "--mfa-require-all")).ToArray());
if (recoverAdmin)
{
    if (!Console.IsInputRedirected)
    {
        Console.WriteLine(JsonSerializer.Serialize(new { status = "rejected", error = "recovery_stdin_required" }));
        Environment.ExitCode = 1;
        return;
    }
    Environment.ExitCode = await RecoveryAdministrator.Run(builder.Configuration, Console.In, Console.Out, CancellationToken.None);
    return;
}
// Inicialización local del almacén MFA (MFA-L2j): sin base de datos, sin origen HTTPS y sin composición MFA del host.
if (mfaKeysInit)
{
    if (!Console.IsInputRedirected)
    {
        Console.WriteLine(JsonSerializer.Serialize(new { status = "rejected", code = "mfa_keystore_init_stdin_required", residue = "none" }));
        Environment.ExitCode = 1;
        return;
    }
    Environment.ExitCode = MfaKeyStoreInitCommand.Run(Console.In, Console.Out);
    return;
}
if (mfaRequireAll)
{
    if (!Console.IsInputRedirected)
    {
        Console.WriteLine(JsonSerializer.Serialize(new { status = "rejected", code = "mfa_policy_stdin_required" }));
        Environment.ExitCode = 1;
        return;
    }
    Environment.ExitCode = await MfaPolicyRequireAllCommand.Run(builder.Configuration, Console.In, Console.Out, CancellationToken.None);
    return;
}
builder.WebHost.ConfigureKestrel(o => o.Limits.MaxRequestBodySize = 16_384);
string frontendPath = Path.GetFullPath(builder.Configuration["RackClick:FrontendPath"]
    ?? Path.Combine(AppContext.BaseDirectory, "wwwroot"), builder.Environment.ContentRootPath);
bool guiIntegrated = Directory.Exists(frontendPath) && File.Exists(Path.Combine(frontendPath, "index.html"));
using var frontendFiles = guiIntegrated ? new Microsoft.Extensions.FileProviders.PhysicalFileProvider(frontendPath) : null;
string connection = builder.Configuration.GetConnectionString("RackClick")
    ?? throw new InvalidOperationException("ConnectionStrings:RackClick is required; no database is created automatically.");
await using var source = NpgsqlDataSource.Create(connection);
// Las ramas de línea de comandos usan un almacén propio sin MFA: no requieren proveedor ni origen HTTPS.
var cliStore = new PostgresStore(source);
var inventory = new InventoryStore(source);
var cancellations = new OperationCancellation(source);
var favorites = new UserCatalogFavorites(source);
var preferences = new UserPreferences(source);
var portColors = new UserPortColors(source);
var categoryColors = new UserCategoryColors(source);
var privateTemplates = new PrivateDeviceTemplates(source);
var sharedTemplates = new SharedDeviceTemplates(source);
if (migrate)
{
    try { await cliStore.Migrate(CancellationToken.None); Console.WriteLine($"Schema verified at version {SchemaMigrations.LatestVersion}."); }
    catch (DomainError e) { Console.Error.WriteLine(e.Code); Environment.ExitCode = 1; }
    catch (Exception) { Console.Error.WriteLine("Migration failed; transaction rolled back. No credentials are logged."); Environment.ExitCode = 1; }
    return;
}
if (bootstrap)
{
    string house = builder.Configuration["Bootstrap:House"] ?? "Systemhaus";
    string admin = builder.Configuration["Bootstrap:User"] ?? "admin";
    Console.Write("New administrator password (16+ characters): ");
    string password = ReadPassword();
    try { await cliStore.Bootstrap(house, admin, password, CancellationToken.None); Console.WriteLine("Initialized. Existing databases are never overwritten."); }
    catch (DomainError e) { Console.Error.WriteLine(e.Code); Environment.ExitCode = 1; }
    catch (Exception) { Console.Error.WriteLine("Initialization failed; inspect database configuration. No credentials are logged."); Environment.ExitCode = 1; }
    return;
}

builder.Services.AddNativeShutdown(builder.Configuration);
// Composición del proveedor Windows (MFA-L2i). Sin MfaKeyStore:Enabled, o con false, no se registra nada. Con true se compone una sola vez.
IMfaHostIdentity mfaHostIdentity = OperatingSystem.IsWindows() ? new ProcessMfaHostIdentity() : new UnavailableMfaHostIdentity();
builder.Services.AddSingleton(mfaHostIdentity);
var mfaMode = MfaWindowsHostComposition.ModeOf(builder.Configuration);
if (mfaMode != MfaHostMode.Disabled)
{
    builder.Services.AddSingleton(sp => MfaWindowsHostComposition.Compose(mfaMode, builder.Configuration, sp.GetRequiredService<IMfaHostIdentity>()));
    builder.Services.AddSingleton<IMfaKeyProvider>(sp => sp.GetRequiredService<MfaHostComposition>().Provider);
}

if (!Uri.TryCreate(builder.Configuration["PublicOrigin"], UriKind.Absolute, out var origin) ||
    origin.AbsolutePath != "/" || origin.Query.Length != 0 || origin.Fragment.Length != 0 || origin.UserInfo.Length != 0)
    throw new InvalidOperationException("PublicOrigin must be an explicit HTTPS origin.");
bool developmentHttp = builder.Environment.IsDevelopment() && origin.Scheme == "http" && origin.IsLoopback &&
    builder.Configuration.GetValue<bool>("DevelopmentLoopbackHttp");
if (origin.Scheme != "https" && !developmentHttp)
    throw new InvalidOperationException("HTTPS is required; development HTTP requires an explicit loopback opt-in.");
if (developmentHttp) builder.WebHost.UseUrls(origin.GetLeftPart(UriPartial.Authority));
string publicOrigin = origin.GetLeftPart(UriPartial.Authority);
const string cookie = "RackClick.Session";
const string mfaCookie = "RackClick.MfaChallenge";
builder.Services.AddRateLimiter(options =>
{
    options.RejectionStatusCode = StatusCodes.Status429TooManyRequests;
    options.AddPolicy("login", context => RateLimitPartition.GetFixedWindowLimiter(
        context.Connection.RemoteIpAddress?.ToString() ?? "unknown", _ => new FixedWindowRateLimiterOptions
        { PermitLimit = 10, Window = TimeSpan.FromMinutes(1), QueueLimit = 0 }));
});
var app = builder.Build();
// Proveedor de la clave TOTP desde la composición de DI del host (MFA-L2i). Sin MfaKeyStore:Enabled no hay proveedor: sin desafíos
// MFA y el servidor los rechaza explícitamente. Con true, la composición valida el almacén; si falla, el arranque termina sin listener.
IMfaKeyProvider? mfaKeys;
MfaHostComposition? mfaComposition;
try
{
    mfaComposition = app.Services.GetService<MfaHostComposition>();
    mfaKeys = app.Services.GetService<IMfaKeyProvider>();
}
catch (MfaHostCompositionException e)
{
    Console.Error.WriteLine(e.Code);
    Environment.ExitCode = 1;
    return;
}
if (mfaComposition is not null) app.Logger.LogInformation("{Diagnostic}", mfaComposition.Diagnostic);
var store = new PostgresStore(source) { MfaAvailable = mfaKeys is not null };
if (mfaComposition is not null)
{
    try { await store.EnsureMfaGracePolicy(CancellationToken.None); }
    catch (NpgsqlException)
    {
        Console.Error.WriteLine("mfa_grace_policy_unavailable");
        Environment.ExitCode = 1;
        return;
    }
}
var mfa = mfaKeys is null ? null : new MfaStore(source, mfaKeys);
app.Use(async (context, next) =>
{
    HttpSecurityHeaders.Apply(context, origin, developmentHttp);
    context.Response.Headers.CacheControl = "no-store";
    context.Response.Headers["X-Content-Type-Options"] = "nosniff";
    context.Response.Headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; " +
        "img-src 'self' data: blob:; font-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'";
    try
    {
        if (!string.Equals(context.Request.Host.Value, origin.Authority, StringComparison.OrdinalIgnoreCase))
            throw new DomainError(400, "host_invalid");
        if (!developmentHttp && !context.Request.IsHttps) throw new DomainError(400, "https_required");
        if (context.Request.Method is not ("GET" or "HEAD" or "OPTIONS") &&
            !string.Equals(context.Request.Headers.Origin.ToString(), publicOrigin, StringComparison.Ordinal))
            throw new DomainError(403, "origin_invalid");
        long bodyLimit = PrivateDeviceTemplates.IsConfigurationCreate(context.Request)
            ? PrivateDeviceTemplates.MaximumConfigurationBodyBytes : 16_384;
        var bodyFeature = context.Features.Get<Microsoft.AspNetCore.Http.Features.IHttpMaxRequestBodySizeFeature>();
        if (bodyFeature is { IsReadOnly: false }) bodyFeature.MaxRequestBodySize = bodyLimit;
        if (context.Request.ContentLength > bodyLimit) throw new DomainError(413, "request_too_large");
        if (context.Request.Path.StartsWithSegments("/api") && context.Request.Path != "/api/v1/auth/login" &&
            context.Request.Path != "/api/v1/auth/mfa/verify" && context.Request.Path != "/api/v1/auth/mfa/enroll/start" &&
            context.Request.Path != "/api/v1/auth/mfa/enroll/confirm")
        {
            string token = context.Request.Cookies[cookie] ?? "";
            var session = await store.Session(token, context.RequestAborted)
                ?? throw new DomainError(401, "authentication_required");
            context.Items["session"] = session;
            if (context.Request.Method is not ("GET" or "HEAD") &&
                !Secrets.Matches(context.Request.Headers["X-RackClick-CSRF"].ToString(), session.CsrfHash))
                throw new DomainError(403, "csrf_invalid");
        }
        await next(context);
    }
    catch (DomainError e)
    {
        context.Response.StatusCode = e.Status;
        await context.Response.WriteAsJsonAsync(new { error = e.Code });
    }
    catch (BadHttpRequestException e)
    {
        context.Response.StatusCode = e.StatusCode;
        await context.Response.WriteAsJsonAsync(new { error = HttpError(e.StatusCode) });
    }
    catch (OperationCanceledException) when (context.RequestAborted.IsCancellationRequested) { }
    catch (Exception e)
    {
        // Do not log request bodies, tokens, passwords, SQL, or connection strings.
        app.Logger.LogError("Request failed: {ErrorType}; trace {TraceId}", e.GetType().Name, context.TraceIdentifier);
        context.Response.StatusCode = 503;
        await context.Response.WriteAsJsonAsync(new { error = "service_unavailable", traceId = context.TraceIdentifier });
    }
});
app.UseStatusCodePages(async status =>
{
    // Framework binding and rate limiting may reject without a body. Keep the
    // same machine-readable error envelope as application/domain rejections.
    await status.HttpContext.Response.WriteAsJsonAsync(new { error = HttpError(status.HttpContext.Response.StatusCode) });
});
app.UseRateLimiter();
if (frontendFiles is not null) app.UseStaticFiles(new StaticFileOptions { FileProvider = frontendFiles });
app.MapGet("/", () => guiIntegrated
    ? (IResult)Results.File(Path.Combine(frontendPath, "index.html"), "text/html")
    : Results.Json(new { product = "RackClick Server", stage = "development-foundation", guiIntegrated }));
app.MapGet("/health/foundation", () => Results.Json(new { product = "RackClick Server", stage = "development-foundation", guiIntegrated }));
app.MapGet("/health/live", () => Results.Json(new { status = "alive" }));
app.MapGet("/health/ready", async (CancellationToken ct) =>
{
    await using var db = await source.OpenConnectionAsync(ct);
    await using var cmd = new NpgsqlCommand("SELECT version FROM schema_migration ORDER BY version DESC LIMIT 1", db);
    return await cmd.ExecuteScalarAsync(ct) is int version && version == SchemaMigrations.LatestVersion
        ? Results.Ok(new { status = "ready", schemaVersion = version }) : Results.StatusCode(503);
});
app.MapPost("/api/v1/auth/login", async (LoginRequest input, HttpContext context) =>
{
    var outcome = await store.AuthenticateForLogin(input.Username ?? "", input.Password ?? "", context.RequestAborted);
    if (outcome.Challenge is { } challenge)
    {
        // El desafío no concede acceso a la API: solo sirve para completar el segundo factor.
        context.Response.Cookies.Append(mfaCookie, challenge.Token, new CookieOptions
        {
            HttpOnly = true, Secure = !developmentHttp, SameSite = SameSiteMode.Strict, Path = "/api/v1/auth/mfa",
            MaxAge = TimeSpan.FromMinutes(5), IsEssential = true
        });
        return Results.Json(new { mfaRequired = true, purpose = outcome.ChallengePurpose ?? "verify", csrf = challenge.Csrf }, statusCode: 202);
    }
    var (token, csrf) = outcome.Session!.Value;
    context.Response.Cookies.Append(cookie, token, new CookieOptions
    {
        HttpOnly = true, Secure = !developmentHttp, SameSite = SameSiteMode.Strict, Path = "/",
        MaxAge = TimeSpan.FromHours(8), IsEssential = true
    });
    return Results.Ok(new { csrf });
}).RequireRateLimiting("login");
app.MapPost("/api/v1/auth/mfa/verify", async (MfaVerifyRequest input, HttpContext context) =>
{
    if (mfa is null) throw new DomainError(503, "mfa_unavailable");
    string challenge = context.Request.Cookies[mfaCookie] ?? throw new DomainError(401, "mfa_challenge_invalid");
    var (token, csrf) = await mfa.CompleteVerify(challenge, input.Code ?? "", context.Request.Headers["X-RackClick-CSRF"].ToString(), context.RequestAborted);
    context.Response.Cookies.Delete(mfaCookie, new CookieOptions { Path = "/api/v1/auth/mfa" });
    context.Response.Cookies.Append(cookie, token, new CookieOptions
    {
        HttpOnly = true, Secure = !developmentHttp, SameSite = SameSiteMode.Strict, Path = "/",
        MaxAge = TimeSpan.FromHours(8), IsEssential = true
    });
    return Results.Ok(new { csrf });
}).RequireRateLimiting("login");
app.MapPost("/api/v1/auth/mfa/enroll/start", async (HttpContext context) =>
{
    if (mfa is null) throw new DomainError(503, "mfa_unavailable");
    string challenge = context.Request.Cookies[mfaCookie] ?? throw new DomainError(401, "mfa_challenge_invalid");
    var start = await mfa.StartEnrollment(challenge, context.Request.Headers["X-RackClick-CSRF"].ToString(), context.RequestAborted);
    return Results.Ok(new { secret = start.SecretBase32, otpauth = start.OtpAuthUri });
}).RequireRateLimiting("login");
app.MapPost("/api/v1/auth/mfa/enroll/confirm", async (MfaVerifyRequest input, HttpContext context) =>
{
    if (mfa is null) throw new DomainError(503, "mfa_unavailable");
    string challenge = context.Request.Cookies[mfaCookie] ?? throw new DomainError(401, "mfa_challenge_invalid");
    var (token, csrf) = await mfa.ConfirmEnrollment(challenge, input.Code ?? "", context.Request.Headers["X-RackClick-CSRF"].ToString(), context.RequestAborted);
    context.Response.Cookies.Delete(mfaCookie, new CookieOptions { Path = "/api/v1/auth/mfa" });
    context.Response.Cookies.Append(cookie, token, new CookieOptions
    {
        HttpOnly = true, Secure = !developmentHttp, SameSite = SameSiteMode.Strict, Path = "/",
        MaxAge = TimeSpan.FromHours(8), IsEssential = true
    });
    return Results.Ok(new { csrf });
}).RequireRateLimiting("login");
app.MapGet("/api/v1/me", async Task<IResult> (HttpContext c) => Results.Ok(new
{
    user = Identity(c).Actor, csrf = Secrets.Csrf(c.Request.Cookies[cookie]!),
    permissions = await store.ReadPermissions(Identity(c).Actor, c.RequestAborted)
}));
app.MapGet("/api/v1/openapi.json", () => Results.Json(OpenApiDocument.Create()));
app.MapMfaAccounts(store, mfa is not null);
app.MapGet("/api/v1/me/preferences", async Task<IResult> (HttpContext c) =>
{
    UserPreferences.RequireEmptyRead(c.Request);
    var result = await preferences.Read(Identity(c).Actor, c.RequestAborted);
    c.Response.Headers.ETag = UserPreferences.ETag(result.Revision);
    return Results.Ok(result);
});
app.MapPost("/api/v1/me/preferences", async Task<IResult> (JsonElement input, HttpContext c) =>
{
    var result = await preferences.Set(InventoryActor(c), input, UserPreferences.ParseRevision(c.Request.Headers.IfMatch.ToString()), RequestId(c), c.Request.Query, c.RequestAborted);
    c.Response.Headers.ETag = UserPreferences.ETag(result.Revision);
    return Results.Ok(result);
});
app.MapGet("/api/v1/me/preferences/operations/{requestId}", async Task<IResult> (string requestId, HttpContext c) =>
{
    UserPreferences.RequireEmptyRead(c.Request);
    var result = await preferences.Status(Identity(c).Actor, UserPreferences.ParseRequestId(requestId), c.RequestAborted);
    c.Response.Headers.ETag = UserPreferences.ETag(result.Revision);
    return Results.Ok(result);
});
app.MapPost("/api/v1/me/preferences/operations/{requestId}/cancel", async Task<IResult> (string requestId, JsonElement input, HttpContext c) =>
{
    Guid id = UserPreferences.ParseRequestId(requestId);
    if (RequestId(c) != id) throw new DomainError(422, "request_id_mismatch");
    var result = await preferences.Cancel(InventoryActor(c), input, UserPreferences.ParseRevision(c.Request.Headers.IfMatch.ToString()), id, c.Request.Query, c.RequestAborted);
    c.Response.Headers.ETag = UserPreferences.ETag(result.Revision);
    return Results.Ok(result);
});
app.MapGet("/api/v1/me/port-colors", async Task<IResult> (HttpContext c) =>
{
    UserPortColors.RequireEmptyRead(c.Request);
    var result = await portColors.Read(Identity(c).Actor, c.RequestAborted);
    c.Response.Headers.ETag = UserPortColors.ETag(result.Revision);
    return Results.Ok(result);
});
app.MapPost("/api/v1/me/port-colors", async Task<IResult> (JsonElement input, HttpContext c) =>
{
    var result = await portColors.Set(InventoryActor(c), input, UserPortColors.ParseRevision(c.Request.Headers.IfMatch.ToString()), RequestId(c), c.Request.Query, c.RequestAborted);
    c.Response.Headers.ETag = UserPortColors.ETag(result.Revision);
    return Results.Ok(result);
});
app.MapGet("/api/v1/me/port-colors/operations/{requestId}", async Task<IResult> (string requestId, HttpContext c) =>
{
    UserPortColors.RequireEmptyRead(c.Request);
    var result = await portColors.Status(Identity(c).Actor, UserPortColors.ParseRequestId(requestId), c.RequestAborted);
    c.Response.Headers.ETag = UserPortColors.ETag(result.Revision);
    return Results.Ok(result);
});
app.MapPost("/api/v1/me/port-colors/operations/{requestId}/cancel", async Task<IResult> (string requestId, JsonElement input, HttpContext c) =>
{
    Guid id = UserPortColors.ParseRequestId(requestId);
    if (RequestId(c) != id) throw new DomainError(422, "request_id_mismatch");
    var result = await portColors.Cancel(InventoryActor(c), input, UserPortColors.ParseRevision(c.Request.Headers.IfMatch.ToString()), id, c.Request.Query, c.RequestAborted);
    c.Response.Headers.ETag = UserPortColors.ETag(result.Revision);
    return Results.Ok(result);
});
app.MapGet("/api/v1/me/category-colors", async Task<IResult> (HttpContext c) =>
{
    UserCategoryColors.RequireEmptyRead(c.Request);
    var result = await categoryColors.Read(Identity(c).Actor, c.RequestAborted);
    c.Response.Headers.ETag = UserCategoryColors.ETag(result.Revision);
    return Results.Ok(result);
});
app.MapPost("/api/v1/me/category-colors", async Task<IResult> (JsonElement input, HttpContext c) =>
{
    var result = await categoryColors.Set(InventoryActor(c), input, UserCategoryColors.ParseRevision(c.Request.Headers.IfMatch.ToString()), RequestId(c), c.Request.Query, c.RequestAborted);
    c.Response.Headers.ETag = UserCategoryColors.ETag(result.Revision);
    return Results.Ok(result);
});
app.MapGet("/api/v1/me/category-colors/operations/{requestId}", async Task<IResult> (string requestId, HttpContext c) =>
{
    UserCategoryColors.RequireEmptyRead(c.Request);
    var result = await categoryColors.Status(Identity(c).Actor, UserCategoryColors.ParseRequestId(requestId), c.RequestAborted);
    c.Response.Headers.ETag = UserCategoryColors.ETag(result.Revision);
    return Results.Ok(result);
});
app.MapPost("/api/v1/me/category-colors/operations/{requestId}/cancel", async Task<IResult> (string requestId, JsonElement input, HttpContext c) =>
{
    Guid id = UserCategoryColors.ParseRequestId(requestId);
    if (RequestId(c) != id) throw new DomainError(422, "request_id_mismatch");
    var result = await categoryColors.Cancel(InventoryActor(c), input, UserCategoryColors.ParseRevision(c.Request.Headers.IfMatch.ToString()), id, c.Request.Query, c.RequestAborted);
    c.Response.Headers.ETag = UserCategoryColors.ETag(result.Revision);
    return Results.Ok(result);
});
app.MapPost("/api/v1/auth/logout", async (HttpContext c) =>
{
    await store.Logout(c.Request.Cookies[cookie]!, c.RequestAborted);
    c.Response.Cookies.Delete(cookie, new CookieOptions { Path = "/", Secure = !developmentHttp, HttpOnly = true, SameSite = SameSiteMode.Strict });
    return Results.NoContent();
});
app.MapGet("/api/v1/systemhaus", async (HttpContext c) =>
{
    var value = await store.ReadHouse(Identity(c).Actor, c.RequestAborted);
    c.Response.Headers.ETag = Revisions.ETag(value.Revision);
    return Results.Ok(value);
});
app.MapPut("/api/v1/systemhaus", async (NameRequest input, HttpContext c) =>
    Results.Content(await store.RenameHouse(MutationActor(c), input.Name, Revision(c), RequestId(c), c.RequestAborted), "application/json"));
app.MapGet("/api/v1/customers", async Task<IResult> (HttpContext c) =>
    Results.Ok(await store.ReadCustomers(Identity(c).Actor, c.RequestAborted)));
app.MapPost("/api/v1/customers", async (NameRequest input, HttpContext c) =>
    Results.Content(await store.CreateCustomer(MutationActor(c), input.Name, Revision(c), RequestId(c), c.RequestAborted), "application/json", statusCode: 201));
app.MapPut("/api/v1/customers/{id:guid}", async (Guid id, NameRequest input, HttpContext c) =>
    Results.Content(await store.RenameCustomer(MutationActor(c), id, input.Name, Revision(c), RequestId(c), c.RequestAborted), "application/json"));
app.MapGet("/api/v1/customers/{id:guid}/project", async Task<IResult> (Guid id, HttpContext c) =>
{
    var result = await inventory.Read(Identity(c).Actor, id, c.RequestAborted);
    c.Response.Headers.ETag = Revisions.ETag(result.Revision);
    return Results.Content(result.Json, "application/json");
});
app.MapGet("/api/v1/customers/{id:guid}/catalog", async Task<IResult> (Guid id, HttpContext c) =>
{
    var result = await inventory.ReadCatalog(Identity(c).Actor, id, Revision(c), c.Request.Query, c.RequestAborted);
    c.Response.Headers.ETag = Revisions.ETag(result.Revision);
    return Results.Ok(result);
});
app.MapGet("/api/v1/customers/{id:guid}/catalog/favorites", async Task<IResult> (Guid id, HttpContext c) =>
{
    var result = await favorites.Read(Identity(c).Actor, id, c.Request.Query, c.RequestAborted);
    c.Response.Headers.ETag = UserCatalogFavorites.ETag(result.Revision);
    return Results.Ok(result);
});
app.MapPost("/api/v1/customers/{id:guid}/catalog/favorites", async Task<IResult> (Guid id, JsonElement input, HttpContext c) =>
{
    var result = await favorites.Set(InventoryActor(c), id, input, UserCatalogFavorites.ParseRevision(c.Request.Headers.IfMatch.ToString()), RequestId(c), c.Request.Query, c.RequestAborted);
    c.Response.Headers.ETag = UserCatalogFavorites.ETag(result.Revision);
    return Results.Ok(result);
});
app.MapGet("/api/v1/customers/{id:guid}/catalog/favorites/operations/{requestId:guid}", async Task<IResult> (Guid id, Guid requestId, HttpContext c) =>
{
    var result = await favorites.Status(Identity(c).Actor, id, requestId, c.Request.Query, c.RequestAborted);
    c.Response.Headers.ETag = UserCatalogFavorites.ETag(result.Revision);
    return Results.Ok(result);
});
app.MapPost("/api/v1/customers/{id:guid}/catalog/favorites/operations/{requestId:guid}/cancel", async Task<IResult> (Guid id, Guid requestId, JsonElement input, HttpContext c) =>
{
    if (RequestId(c) != requestId) throw new DomainError(422, "request_id_mismatch");
    var result = await favorites.Cancel(InventoryActor(c), id, input, UserCatalogFavorites.ParseRevision(c.Request.Headers.IfMatch.ToString()), requestId, c.Request.Query, c.RequestAborted);
    c.Response.Headers.ETag = UserCatalogFavorites.ETag(result.Revision);
    return Results.Ok(result);
});
app.MapGet("/api/v1/customers/{id:guid}/catalog/shared-templates", async Task<IResult> (Guid id, HttpContext c) =>
{
    var result = await sharedTemplates.Read(Identity(c).Actor, id, c.Request.Query, c.RequestAborted);
    c.Response.Headers.ETag = SharedDeviceTemplates.ETag(result.Revision); return Results.Ok(result);
});
app.MapGet("/api/v1/customers/{id:guid}/catalog/shared-templates/{templateId:guid}", async Task<IResult> (Guid id, Guid templateId, HttpContext c) =>
{
    var result = await sharedTemplates.ReadOne(Identity(c).Actor, id, templateId, c.Request.Query, c.RequestAborted);
    c.Response.Headers.ETag = SharedDeviceTemplates.ETag(result.Revision); return Results.Ok(result);
});
app.MapPost("/api/v1/customers/{id:guid}/catalog/shared-templates", async Task<IResult> (Guid id, JsonElement input, HttpContext c) =>
{
    var result = await sharedTemplates.Set(InventoryActor(c), id, input, SharedDeviceTemplates.ParseRevision(c.Request.Headers.IfMatch.ToString()), RequestId(c), c.Request.Query, c.RequestAborted);
    c.Response.Headers.ETag = SharedDeviceTemplates.ETag(result.Revision); return Results.Ok(result);
});
app.MapGet("/api/v1/customers/{id:guid}/catalog/shared-templates/operations/{requestId:guid}", async Task<IResult> (Guid id, Guid requestId, HttpContext c) =>
{
    var result = await sharedTemplates.Status(Identity(c).Actor, id, requestId, c.Request.Query, c.RequestAborted);
    c.Response.Headers.ETag = SharedDeviceTemplates.ETag(result.Revision); return Results.Ok(result);
});
app.MapPost("/api/v1/customers/{id:guid}/catalog/shared-templates/operations/{requestId:guid}/cancel", async Task<IResult> (Guid id, Guid requestId, JsonElement input, HttpContext c) =>
{
    if (RequestId(c) != requestId) throw new DomainError(422, "request_id_mismatch");
    var result = await sharedTemplates.Cancel(InventoryActor(c), id, input, SharedDeviceTemplates.ParseRevision(c.Request.Headers.IfMatch.ToString()), requestId, c.Request.Query, c.RequestAborted);
    c.Response.Headers.ETag = SharedDeviceTemplates.ETag(result.Revision); return Results.Ok(result);
});
app.MapGet("/api/v1/customers/{id:guid}/catalog/private-templates", async Task<IResult> (Guid id, HttpContext c) =>
{
    var result = await privateTemplates.Read(Identity(c).Actor, id, c.Request.Query, c.RequestAborted);
    c.Response.Headers.ETag = PrivateDeviceTemplates.ETag(result.Revision);
    return Results.Ok(result);
});
app.MapGet("/api/v1/customers/{id:guid}/catalog/private-templates/{templateId:guid}", async Task<IResult> (Guid id, Guid templateId, HttpContext c) =>
{
    var result = await privateTemplates.ReadOne(Identity(c).Actor, id, templateId, c.Request.Query, c.RequestAborted);
    c.Response.Headers.ETag = PrivateDeviceTemplates.ETag(result.Revision);
    return Results.Ok(result);
});
app.MapPost("/api/v1/customers/{id:guid}/catalog/private-templates", async Task<IResult> (Guid id, JsonElement input, HttpContext c) =>
{
    var result = await privateTemplates.Set(InventoryActor(c), id, input, PrivateDeviceTemplates.ParseRevision(c.Request.Headers.IfMatch.ToString()), RequestId(c), c.Request.Query, c.RequestAborted);
    c.Response.Headers.ETag = PrivateDeviceTemplates.ETag(result.Revision);
    return Results.Ok(result);
});
app.MapGet("/api/v1/customers/{id:guid}/catalog/private-templates/operations/{requestId:guid}", async Task<IResult> (Guid id, Guid requestId, HttpContext c) =>
{
    var result = await privateTemplates.Status(Identity(c).Actor, id, requestId, c.Request.Query, c.RequestAborted);
    c.Response.Headers.ETag = PrivateDeviceTemplates.ETag(result.Revision);
    return Results.Ok(result);
});
app.MapPost("/api/v1/customers/{id:guid}/catalog/private-templates/configurations", async Task<IResult> (Guid id, HttpContext c) =>
{
    var actor = InventoryActor(c);
    long revision = PrivateDeviceTemplates.ParseRevision(c.Request.Headers.IfMatch.ToString());
    Guid requestId = RequestId(c);
    await privateTemplates.AuthorizeConfiguration(actor, id, c.Request.Query, c.RequestAborted);
    if (!c.Request.HasJsonContentType()) throw new DomainError(415, "request_invalid");
    JsonDocument document;
    try { document = await JsonDocument.ParseAsync(c.Request.Body, cancellationToken: c.RequestAborted); }
    catch (JsonException) { throw new DomainError(400, "request_invalid"); }
    using (document)
    {
        var result = await privateTemplates.Configure(actor, id, document.RootElement, revision, requestId, c.Request.Query, c.RequestAborted);
        c.Response.Headers.ETag = PrivateDeviceTemplates.ETag(result.Revision);
        return Results.Ok(result);
    }
});
app.MapPost("/api/v1/customers/{id:guid}/catalog/private-templates/configurations/operations/{requestId:guid}/cancel", async Task<IResult> (Guid id, Guid requestId, JsonElement input, HttpContext c) =>
{
    if (RequestId(c) != requestId) throw new DomainError(422, "request_id_mismatch");
    var result = await privateTemplates.CancelConfiguration(InventoryActor(c), id, input,
        PrivateDeviceTemplates.ParseRevision(c.Request.Headers.IfMatch.ToString()), requestId, c.Request.Query, c.RequestAborted);
    c.Response.Headers.ETag = PrivateDeviceTemplates.ETag(result.Revision);
    return Results.Ok(result);
});
app.MapPost("/api/v1/customers/{id:guid}/catalog/private-templates/operations/{requestId:guid}/cancel", async Task<IResult> (Guid id, Guid requestId, JsonElement input, HttpContext c) =>
{
    if (RequestId(c) != requestId) throw new DomainError(422, "request_id_mismatch");
    var result = await privateTemplates.Cancel(InventoryActor(c), id, input, PrivateDeviceTemplates.ParseRevision(c.Request.Headers.IfMatch.ToString()), requestId, c.Request.Query, c.RequestAborted);
    c.Response.Headers.ETag = PrivateDeviceTemplates.ETag(result.Revision);
    return Results.Ok(result);
});
app.MapGet("/api/v1/customers/{id:guid}/changes", async Task<IResult> (Guid id, HttpContext c) =>
{
    var query = c.Request.Query;
    var value = await inventory.ReadChanges(Identity(c).Actor, id,
        query.TryGetValue("afterRevision", out var after) ? after.ToString() : null,
        query.TryGetValue("limit", out var limit) ? limit.ToString() : null, c.RequestAborted);
    c.Response.Headers.ETag = Revisions.ETag(value.CurrentRevision);
    return Results.Ok(value);
});
app.MapGet("/api/v1/customers/{id:guid}/changes/details", async Task<IResult> (Guid id, HttpContext c) =>
{
    var query = c.Request.Query;
    var value = await inventory.ReadDetailedChanges(Identity(c).Actor, id,
        query.TryGetValue("afterRevision", out var after) ? after.ToString() : null,
        query.TryGetValue("limit", out var limit) ? limit.ToString() : null, c.RequestAborted);
    c.Response.Headers.ETag = Revisions.ETag(value.CurrentRevision);
    return Results.Ok(value);
});
app.MapGet("/api/v1/customers/{id:guid}/inventory/search", async Task<IResult> (Guid id, HttpContext c) =>
{
    var value = await inventory.ReadView(Identity(c).Actor, id, "search", Revision(c), c.Request.Query, c.RequestAborted);
    c.Response.Headers.ETag = Revisions.ETag(value.Revision);
    return Results.Ok(value);
});
app.MapGet("/api/v1/customers/{id:guid}/inventory/ports", async Task<IResult> (Guid id, HttpContext c) =>
{
    var value = await inventory.ReadView(Identity(c).Actor, id, "ports", Revision(c), c.Request.Query, c.RequestAborted);
    c.Response.Headers.ETag = Revisions.ETag(value.Revision);
    return Results.Ok(value);
});
app.MapGet("/api/v1/customers/{id:guid}/inventory/connections", async Task<IResult> (Guid id, HttpContext c) =>
{
    var value = await inventory.ReadView(Identity(c).Actor, id, "connections", Revision(c), c.Request.Query, c.RequestAborted);
    c.Response.Headers.ETag = Revisions.ETag(value.Revision);
    return Results.Ok(value);
});
app.MapPost("/api/v1/customers/{id:guid}/reports/csv", async Task<IResult> (Guid id, JsonElement input, HttpContext c) =>
{
    var result = await inventory.GenerateReport(InventoryActor(c), id, input, Revision(c), RequestId(c), c.RequestAborted);
    c.Response.Headers.ETag = Revisions.ETag(result.Revision);
    return Results.Ok(result);
});
app.MapGet("/api/v1/customers/{id:guid}/reports/operations/{requestId:guid}", async Task<IResult> (Guid id, Guid requestId, HttpContext c) =>
    Results.Ok(await inventory.ReportStatus(Identity(c).Actor, id, requestId, c.RequestAborted)));
app.MapPost("/api/v1/customers/{id:guid}/reports/xlsx", async Task<IResult> (Guid id, JsonElement input, HttpContext c) =>
{
    var result = await inventory.GenerateSpreadsheetReport(InventoryActor(c), id, input, Revision(c), RequestId(c), c.RequestAborted);
    c.Response.Headers.ETag = Revisions.ETag(result.Revision);
    return Results.Ok(result);
});
app.MapGet("/api/v1/customers/{id:guid}/reports/xlsx/operations/{requestId:guid}", async Task<IResult> (Guid id, Guid requestId, HttpContext c) =>
    Results.Ok(await inventory.SpreadsheetReportStatus(Identity(c).Actor, id, requestId, c.RequestAborted)));
app.MapPost("/api/v1/customers/{id:guid}/reports/xls-html", async Task<IResult> (Guid id, JsonElement input, HttpContext c) =>
{
    if (c.Request.Query.Count != 0) throw new DomainError(422, "request_invalid");
    var result = await inventory.GenerateRc9ExcelReport(InventoryActor(c), id, input, Revision(c), RequestId(c), c.RequestAborted);
    c.Response.Headers.ETag = Revisions.ETag(result.Revision);
    return Results.Ok(result);
});
app.MapGet("/api/v1/customers/{id:guid}/reports/xls-html/operations/{requestId:guid}", async Task<IResult> (Guid id, Guid requestId, HttpContext c) =>
{
    if (c.Request.Query.Count != 0) throw new DomainError(422, "request_invalid");
    return Results.Ok(await inventory.Rc9ExcelReportStatus(Identity(c).Actor, id, requestId, c.RequestAborted));
});
app.MapPost("/api/v1/customers/{id:guid}/reports/printable", async Task<IResult> (Guid id, JsonElement input, HttpContext c) =>
{
    var result = await inventory.GeneratePrintableReport(InventoryActor(c), id, input, Revision(c), RequestId(c), c.RequestAborted);
    c.Response.Headers.ETag = Revisions.ETag(result.Revision);
    return Results.Ok(result);
});
app.MapGet("/api/v1/customers/{id:guid}/reports/printable/operations/{requestId:guid}", async Task<IResult> (Guid id, Guid requestId, HttpContext c) =>
    Results.Ok(await inventory.PrintableReportStatus(Identity(c).Actor, id, requestId, c.RequestAborted)));
app.MapPost("/api/v1/customers/{id:guid}/reports/rack-svg", async Task<IResult> (Guid id, JsonElement input, HttpContext c) =>
{
    var result = await inventory.GenerateRackSvgReport(InventoryActor(c), id, input, Revision(c), RequestId(c), c.RequestAborted);
    c.Response.Headers.ETag = Revisions.ETag(result.Revision);
    return Results.Ok(result);
});
app.MapGet("/api/v1/customers/{id:guid}/reports/rack-svg/operations/{requestId:guid}", async Task<IResult> (Guid id, Guid requestId, HttpContext c) =>
    Results.Ok(await inventory.RackSvgReportStatus(Identity(c).Actor, id, requestId, c.RequestAborted)));
app.MapPost("/api/v1/customers/{id:guid}/commands", async Task<IResult> (Guid id, InventoryCommandRequest input, HttpContext c) =>
    Results.Content(await inventory.Execute(InventoryActor(c), id, input, Revision(c), RequestId(c), c.RequestAborted), "application/json"));
app.MapPost("/api/v1/customers/{id:guid}/commands/preview", async Task<IResult> (Guid id, InventoryCommandRequest input, HttpContext c) =>
    Results.Content(await inventory.Preview(InventoryActor(c), id, input, Revision(c), c.RequestAborted), "application/json"));
app.MapGet("/api/v1/customers/{id:guid}/operations/{requestId:guid}", async Task<IResult> (Guid id, Guid requestId, HttpContext c) =>
    Results.Content(await inventory.Operation(Identity(c).Actor, id, requestId, c.RequestAborted), "application/json"));
app.MapPost("/api/v1/customers/{id:guid}/operations/{requestId:guid}/cancel", async Task<IResult> (Guid id, Guid requestId, InventoryCommandRequest original, HttpContext c) =>
{
    if (RequestId(c) != requestId) throw new DomainError(422, "request_id_mismatch");
    return Results.Content(await cancellations.Cancel(InventoryActor(c), id, original, Revision(c), requestId, c.RequestAborted), "application/json");
});
app.MapGet("/api/v1/admin/users", async Task<IResult> (HttpContext c) =>
{
    var result = await store.ReadUsers(Identity(c).Actor, c.RequestAborted);
    c.Response.Headers.ETag = Revisions.ETag(result.Revision);
    return Results.Ok(result);
});
app.MapGet("/api/v1/admin/audit", async Task<IResult> (HttpContext c) =>
{
    var query = c.Request.Query;
    var result = await store.ReadAudit(Identity(c).Actor,
        query.TryGetValue("limit", out var limit) ? limit.ToString() : null,
        query.TryGetValue("beforeId", out var before) ? before.ToString() : null,
        query.TryGetValue("actorId", out var auditActor) ? auditActor.ToString() : null,
        query.TryGetValue("resourceId", out var auditResource) ? auditResource.ToString() : null, c.RequestAborted);
    c.Response.Headers.ETag = Revisions.ETag(result.Revision);
    return Results.Ok(result);
});
app.MapGet("/api/v1/admin/audit/{eventId}", async Task<IResult> (string eventId, HttpContext c) =>
{
    var result = await store.ReadAuditDetail(Identity(c).Actor, eventId, c.RequestAborted);
    c.Response.Headers.ETag = Revisions.ETag(result.Revision);
    return Results.Ok(result);
});
app.MapGet("/api/v1/admin/audit/{eventId}/administrative-detail", async Task<IResult> (string eventId, HttpContext c) =>
{
    var result = await store.ReadAuditAdministrativeDetail(Identity(c).Actor, eventId, c.RequestAborted);
    c.Response.Headers.ETag = Revisions.ETag(result.Revision);
    return Results.Ok(result);
});
app.MapGet("/api/v1/admin/audit/{eventId}/context", async Task<IResult> (string eventId, HttpContext c) =>
{
    var result = await store.ReadAuditContext(Identity(c).Actor, eventId, c.RequestAborted);
    c.Response.Headers.ETag = Revisions.ETag(result.Revision);
    return Results.Ok(result);
});
app.MapGet("/api/v1/admin/users/{userId:guid}/effective-permissions", async Task<IResult> (Guid userId, HttpContext c) =>
{
    var result = await store.ReadUserEffectivePermissions(Identity(c).Actor, userId, c.RequestAborted);
    c.Response.Headers.ETag = Revisions.ETag(result.Revision);
    return Results.Ok(result);
});
app.MapGet("/api/v1/admin/users/{userId:guid}/sessions", async Task<IResult> (Guid userId, HttpContext c) =>
{
    var result = await store.ReadUserSessions(Identity(c).Actor, userId, c.RequestAborted);
    c.Response.Headers.ETag = Revisions.ETag(result.Revision);
    return Results.Ok(result);
});
app.MapGet("/api/v1/admin/user-groups", async Task<IResult> (HttpContext c) =>
    Results.Content(await store.ReadUserGroups(Identity(c).Actor, c.RequestAborted), "application/json"));
app.MapGet("/api/v1/admin/customer-groups", async Task<IResult> (HttpContext c) =>
    Results.Content(await store.ReadCustomerGroups(Identity(c).Actor, c.RequestAborted), "application/json"));
foreach (bool customerGroup in new[] { false, true })
{
    string groupPath = customerGroup ? "/api/v1/admin/customer-groups" : "/api/v1/admin/user-groups";
    app.MapPost(groupPath, async Task<IResult> (NameRequest input, HttpContext c) =>
        Results.Content(await store.CreateOrCancelGroup(InventoryActor(c), customerGroup, false, input.Name, Revision(c), RequestId(c), c.RequestAborted), "application/json", statusCode: 201));
    app.MapGet(groupPath + "/operations/{requestId:guid}", async Task<IResult> (Guid requestId, HttpContext c) =>
        Results.Content(await store.GroupCreationStatus(Identity(c).Actor, customerGroup, requestId, c.RequestAborted), "application/json"));
    app.MapPost(groupPath + "/operations/{requestId:guid}/cancel", async Task<IResult> (Guid requestId, NameRequest input, HttpContext c) =>
    {
        if (RequestId(c) != requestId) throw new DomainError(422, "request_id_mismatch");
        return Results.Content(await store.CreateOrCancelGroup(InventoryActor(c), customerGroup, true, input.Name, Revision(c), requestId, c.RequestAborted), "application/json");
    });
}
app.MapPost("/api/v1/admin/user-groups/{groupId:guid}/members", async Task<IResult> (Guid groupId, GroupMemberRequest input, HttpContext c) =>
    Results.Content(await store.SetOrCancelGroupMember(InventoryActor(c), groupId, input, false, Revision(c), RequestId(c), c.RequestAborted), "application/json"));
app.MapGet("/api/v1/admin/user-groups/{groupId:guid}/members/operations/{requestId:guid}", async Task<IResult> (Guid groupId, Guid requestId, HttpContext c) =>
    Results.Content(await store.GroupMemberStatus(Identity(c).Actor, groupId, requestId, c.RequestAborted), "application/json"));
app.MapPost("/api/v1/admin/user-groups/{groupId:guid}/members/operations/{requestId:guid}/cancel", async Task<IResult> (Guid groupId, Guid requestId, GroupMemberRequest input, HttpContext c) =>
{
    if (RequestId(c) != requestId) throw new DomainError(422, "request_id_mismatch");
    return Results.Content(await store.SetOrCancelGroupMember(InventoryActor(c), groupId, input, true, Revision(c), requestId, c.RequestAborted), "application/json");
});

app.MapGet("/api/v1/admin/capabilities", async Task<IResult> (HttpContext c) =>
    Results.Content(await store.ReadAdminCapabilities(Identity(c).Actor, c.RequestAborted), "application/json"));
app.MapPost("/api/v1/admin/user-groups/{groupId:guid}/grants", async Task<IResult> (Guid groupId, GrantRequest input, HttpContext c) =>
    Results.Content(await store.SetOrCancelGrant(InventoryActor(c), groupId, input, false, Revision(c), RequestId(c), c.RequestAborted), "application/json"));
app.MapGet("/api/v1/admin/user-groups/{groupId:guid}/grants/operations/{requestId:guid}", async Task<IResult> (Guid groupId, Guid requestId, HttpContext c) =>
    Results.Content(await store.GrantStatus(Identity(c).Actor, groupId, requestId, c.RequestAborted), "application/json"));
app.MapPost("/api/v1/admin/user-groups/{groupId:guid}/grants/operations/{requestId:guid}/cancel", async Task<IResult> (Guid groupId, Guid requestId, GrantRequest input, HttpContext c) =>
{
    if (RequestId(c) != requestId) throw new DomainError(422, "request_id_mismatch");
    return Results.Content(await store.SetOrCancelGrant(InventoryActor(c), groupId, input, true, Revision(c), requestId, c.RequestAborted), "application/json");
});
app.MapGet("/api/v1/admin/customers", async Task<IResult> (HttpContext c) =>
    Results.Content(await store.ReadAdminCustomers(Identity(c).Actor, c.RequestAborted), "application/json"));
app.MapPost("/api/v1/admin/customer-groups/{groupId:guid}/members", async Task<IResult> (Guid groupId, CustomerGroupMemberRequest input, HttpContext c) =>
    Results.Content(await store.SetOrCancelCustomerGroupMember(InventoryActor(c), groupId, input, false, Revision(c), RequestId(c), c.RequestAborted), "application/json"));
app.MapGet("/api/v1/admin/customer-groups/{groupId:guid}/members/operations/{requestId:guid}", async Task<IResult> (Guid groupId, Guid requestId, HttpContext c) =>
    Results.Content(await store.CustomerGroupMemberStatus(Identity(c).Actor, groupId, requestId, c.RequestAborted), "application/json"));
app.MapPost("/api/v1/admin/customer-groups/{groupId:guid}/members/operations/{requestId:guid}/cancel", async Task<IResult> (Guid groupId, Guid requestId, CustomerGroupMemberRequest input, HttpContext c) =>
{
    if (RequestId(c) != requestId) throw new DomainError(422, "request_id_mismatch");
    return Results.Content(await store.SetOrCancelCustomerGroupMember(InventoryActor(c), groupId, input, true, Revision(c), requestId, c.RequestAborted), "application/json");
});
app.MapPost("/api/v1/admin/users/{userId:guid}/state", async Task<IResult> (Guid userId, UserStateRequest input, HttpContext c) =>
    Results.Content(await store.SetOrCancelUserState(InventoryActor(c), userId, input, false, Revision(c), RequestId(c), c.RequestAborted), "application/json"));
app.MapGet("/api/v1/admin/users/{userId:guid}/state/operations/{requestId:guid}", async Task<IResult> (Guid userId, Guid requestId, HttpContext c) =>
    Results.Content(await store.UserStateStatus(Identity(c).Actor, userId, requestId, c.RequestAborted), "application/json"));
app.MapPost("/api/v1/admin/users/{userId:guid}/state/operations/{requestId:guid}/cancel", async Task<IResult> (Guid userId, Guid requestId, UserStateRequest input, HttpContext c) =>
{
    if (RequestId(c) != requestId) throw new DomainError(422, "request_id_mismatch");
    return Results.Content(await store.SetOrCancelUserState(InventoryActor(c), userId, input, true, Revision(c), requestId, c.RequestAborted), "application/json");
});
app.MapPost("/api/v1/admin/users/{userId:guid}/sessions/{sessionId:guid}/revoke", async Task<IResult> (Guid userId, Guid sessionId, System.Text.Json.JsonElement input, HttpContext c) =>
{
    if (input.ValueKind != System.Text.Json.JsonValueKind.Object || input.EnumerateObject().Any()) throw new DomainError(422, "request_invalid");
    return Results.Content(await store.RevokeOrCancelUserSession(InventoryActor(c), userId, sessionId, false, Revision(c), RequestId(c), c.RequestAborted), "application/json");
});
app.MapGet("/api/v1/admin/users/{userId:guid}/sessions/{sessionId:guid}/revoke/operations/{requestId:guid}", async Task<IResult> (Guid userId, Guid sessionId, Guid requestId, HttpContext c) =>
    Results.Content(await store.UserSessionRevocationStatus(Identity(c).Actor, userId, sessionId, requestId, c.RequestAborted), "application/json"));
app.MapPost("/api/v1/admin/users/{userId:guid}/sessions/{sessionId:guid}/revoke/operations/{requestId:guid}/cancel", async Task<IResult> (Guid userId, Guid sessionId, Guid requestId, System.Text.Json.JsonElement input, HttpContext c) =>
{
    if (input.ValueKind != System.Text.Json.JsonValueKind.Object || input.EnumerateObject().Any()) throw new DomainError(422, "request_invalid");
    if (RequestId(c) != requestId) throw new DomainError(422, "request_id_mismatch");
    return Results.Content(await store.RevokeOrCancelUserSession(InventoryActor(c), userId, sessionId, true, Revision(c), requestId, c.RequestAborted), "application/json");
});
app.MapPost("/api/v1/admin/users/{userId:guid}/password", async Task<IResult> (Guid userId, UserPasswordRequest input, HttpContext c) =>
    Results.Content(await store.ResetOrCancelUserPassword(InventoryActor(c), userId, input.Password, false, Revision(c), RequestId(c), c.RequestAborted), "application/json"));
app.MapGet("/api/v1/admin/users/{userId:guid}/password/operations/{requestId:guid}", async Task<IResult> (Guid userId, Guid requestId, HttpContext c) =>
    Results.Content(await store.UserPasswordStatus(Identity(c).Actor, userId, requestId, c.RequestAborted), "application/json"));
app.MapPost("/api/v1/admin/users/{userId:guid}/password/operations/{requestId:guid}/cancel", async Task<IResult> (Guid userId, Guid requestId, System.Text.Json.JsonElement input, HttpContext c) =>
{
    if (input.ValueKind != System.Text.Json.JsonValueKind.Object) throw new DomainError(422, "request_invalid");
    if (RequestId(c) != requestId) throw new DomainError(422, "request_id_mismatch");
    return Results.Content(await store.ResetOrCancelUserPassword(InventoryActor(c), userId, null, true, Revision(c), requestId, c.RequestAborted), "application/json");
});
app.MapPost("/api/v1/admin/users", async Task<IResult> (CreateUserRequest input, HttpContext c) =>
    Results.Content(await store.CreateUser(InventoryActor(c), input.Username, input.Password, Revision(c), RequestId(c), c.RequestAborted), "application/json", statusCode: 201));
app.MapGet("/api/v1/admin/users/operations/{requestId:guid}", async Task<IResult> (Guid requestId, HttpContext c) =>
    Results.Content(await store.UserCreationStatus(Identity(c).Actor, requestId, c.RequestAborted), "application/json"));
app.MapPost("/api/v1/admin/users/operations/{requestId:guid}/cancel", async Task<IResult> (Guid requestId, CancelUserCreationRequest input, HttpContext c) =>
{
    if (RequestId(c) != requestId) throw new DomainError(422, "request_id_mismatch");
    return Results.Content(await store.CancelUserCreation(InventoryActor(c), input.Username, Revision(c), requestId, c.RequestAborted), "application/json");
});
await app.RunAsync();

static SessionIdentity Identity(HttpContext c) => (SessionIdentity)c.Items["session"]!;
static Actor InventoryActor(HttpContext c)
{
    if (!c.Request.Headers.ContainsKey("X-RackClick-Actor")) throw new DomainError(422, "actor_required");
    return MutationActor(c);
}
static Actor MutationActor(HttpContext c)
{
    var actor = Identity(c).Actor;
    if (c.Request.Headers.TryGetValue("X-RackClick-Actor", out var expected))
    {
        if (!Guid.TryParse(expected.ToString(), out var id) || id == Guid.Empty)
            throw new DomainError(422, "actor_invalid");
        if (id != actor.Id) throw new DomainError(409, "actor_changed");
    }
    return actor;
}
static string HttpError(int status) => status switch
{
    413 => "request_too_large", 415 => "content_type_invalid", 429 => "rate_limited",
    404 => "not_found", 405 => "method_not_allowed", _ => "request_invalid"
};
static long Revision(HttpContext c) => Revisions.Parse(c.Request.Headers.IfMatch.ToString());
static Guid RequestId(HttpContext c) => Guid.TryParse(c.Request.Headers["Idempotency-Key"], out var id) && id != Guid.Empty
    ? id : throw new DomainError(422, "request_id_invalid");
static string ReadPassword()
{
    if (Console.IsInputRedirected) return Console.ReadLine() ?? "";
    var value = new System.Text.StringBuilder();
    for (;;)
    {
        var key = Console.ReadKey(true);
        if (key.Key == ConsoleKey.Enter) { Console.WriteLine(); return value.ToString(); }
        if (key.Key == ConsoleKey.Backspace) { if (value.Length > 0) value.Length--; }
        else if (!char.IsControl(key.KeyChar)) value.Append(key.KeyChar);
    }
}
record LoginRequest(string? Username, string? Password);
record MfaVerifyRequest(string? Code);
record NameRequest(string? Name);

record CreateUserRequest(string? Username, string? Password);
record CancelUserCreationRequest(string? Username);

// Visibilidad del punto de entrada para WebApplicationFactory en las pruebas HTTP. No cambia el comportamiento del producto.
public partial class Program { }
