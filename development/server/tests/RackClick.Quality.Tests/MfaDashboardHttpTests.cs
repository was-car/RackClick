using System.Diagnostics;
using System.Net;
using System.Security.Cryptography;
using System.Text.Json;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.AspNetCore.TestHost;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;
using OtpNet;
using RackClick.Server;
using Xunit;
using AccountLab = RackClick.Quality.Tests.MfaAccountManagementTests.Laboratory;

namespace RackClick.Quality.Tests;

[Collection("MfaHttp")]
public sealed class MfaDashboardHttpTests
{
    [Fact]
    public async Task PersonalAndAdminHttpReadsArePrivateAndMutationsKeepOriginCsrfActorAndRevisionGuards()
    {
        await using var h = await Harness.Create();
        var user = await h.Lab.AddUser("http.grace.user"); await h.Lab.Legacy(user.Id);
        var auth = await h.Login(user.UserName);
        using var status = await h.Get("/api/v1/me/mfa", auth.Cookie);
        Assert.Equal(HttpStatusCode.OK, status.StatusCode);
        using var data = JsonDocument.Parse(await status.Content.ReadAsStringAsync(TestContext.Current.CancellationToken));
        Assert.Equal(35, data.RootElement.GetProperty("daysRemaining").GetInt32());
        Assert.False(data.RootElement.TryGetProperty("secret", out _));
        Assert.False(data.RootElement.TryGetProperty("secretCiphertext", out _));
        var revision = data.RootElement.GetProperty("revision").GetInt64();
        string before = await h.Lab.SnapshotAll();
        using var foreign = await h.Post("/api/v1/me/mfa/enable", new { password = AccountLab.Password }, auth,
            revision, origin: "https://foreign.invalid");
        Assert.Equal(HttpStatusCode.Forbidden, foreign.StatusCode);
        using var csrf = await h.Post("/api/v1/me/mfa/enable", new { password = AccountLab.Password }, auth with { Csrf = "wrong" }, revision);
        Assert.Equal(HttpStatusCode.Forbidden, csrf.StatusCode);
        using var actor = await h.Post("/api/v1/me/mfa/enable", new { password = AccountLab.Password }, auth, revision, actor: Guid.NewGuid());
        Assert.Equal(HttpStatusCode.Conflict, actor.StatusCode);
        using var conflict = await h.Post("/api/v1/me/mfa/enable", new { password = AccountLab.Password }, auth, revision + 1);
        Assert.Equal(HttpStatusCode.PreconditionFailed, conflict.StatusCode);
        using var forbidden = await h.Get("/api/v1/admin/users/" + h.Lab.Admin.Id + "/mfa", auth.Cookie);
        Assert.Equal(HttpStatusCode.Forbidden, forbidden.StatusCode);
        Assert.Equal(before, await h.Lab.SnapshotAll());
    }

    [Fact]
    public async Task SelfActivationOverHttpRevokesTheOldSessionAndRequiresEnrollmentBeforeApiAccess()
    {
        await using var h = await Harness.Create();
        var user = await h.Lab.AddUser("http.enrollment.user"); await h.Lab.Legacy(user.Id);
        var auth = await h.Login(user.UserName);
        long revision = await h.Revision(user.Id, auth);
        using var mutation = await h.Post("/api/v1/me/mfa/enable", new { password = AccountLab.Password }, auth, revision);
        Assert.Equal(HttpStatusCode.OK, mutation.StatusCode);
        using var receipt = JsonDocument.Parse(await mutation.Content.ReadAsStringAsync(TestContext.Current.CancellationToken));
        Assert.True(receipt.RootElement.GetProperty("signInRequired").GetBoolean());
        using var rejected = await h.Get("/api/v1/me", auth.Cookie);
        Assert.Equal(HttpStatusCode.Unauthorized, rejected.StatusCode);
        var verified = await h.Enroll(user.UserName);
        using var me = await h.Get("/api/v1/me", verified.Cookie);
        Assert.Equal(HttpStatusCode.OK, me.StatusCode);
        Assert.Equal(1, await h.Lab.Count("SELECT count(*) FROM app_mfa_factor WHERE user_id=@user AND state='active'", ("user", user.Id)));
    }

    [Fact]
    public async Task AdministrativeChangesRequireCompletedMfaAndTheAdminNeverReceivesAnotherUsersSeed()
    {
        await using var h = await Harness.Create();
        var user = await h.Lab.AddUser("http.admin.target");
        var auth = await h.Login(h.Lab.Admin.UserName);
        using var initial = await h.Get("/api/v1/admin/users/" + user.Id + "/mfa", auth.Cookie);
        using var initialData = JsonDocument.Parse(await initial.Content.ReadAsStringAsync(TestContext.Current.CancellationToken));
        long revision = initialData.RootElement.GetProperty("revision").GetInt64();
        using var denied = await h.Post("/api/v1/admin/users/" + user.Id + "/mfa/enable", new { }, auth, revision);
        Assert.Equal(HttpStatusCode.Forbidden, denied.StatusCode);
        Assert.Equal("mfa_verification_required", await Error(denied));
        using var ownEnable = await h.Post("/api/v1/me/mfa/enable", new { password = AccountLab.Password }, auth, revision);
        Assert.Equal(HttpStatusCode.OK, ownEnable.StatusCode);
        var verified = await h.Enroll(h.Lab.Admin.UserName);
        revision = await h.Revision(user.Id, verified, admin: true);
        using var changed = await h.Post("/api/v1/admin/users/" + user.Id + "/mfa/enable", new { }, verified, revision);
        Assert.Equal(HttpStatusCode.OK, changed.StatusCode);
        using var receipt = JsonDocument.Parse(await changed.Content.ReadAsStringAsync(TestContext.Current.CancellationToken));
        Assert.False(receipt.RootElement.TryGetProperty("secret", out _));
        Assert.Equal(user.Id, receipt.RootElement.GetProperty("userId").GetGuid());
        Assert.True(receipt.RootElement.GetProperty("resource").GetProperty("enrollmentPending").GetBoolean());
        using var spec = await h.Get("/api/v1/openapi.json", verified.Cookie);
        Assert.Equal(HttpStatusCode.OK, spec.StatusCode);
        using var document = JsonDocument.Parse(await spec.Content.ReadAsStringAsync(TestContext.Current.CancellationToken));
        Assert.True(document.RootElement.GetProperty("paths").TryGetProperty("/api/v1/me/mfa/enable", out _));
    }

    [Fact]
    public async Task BrowserDashboardShowsGraceAndManagesPersonalAndSelectedUserMfa()
    {
        var frontend = Environment.GetEnvironmentVariable("RACKCLICK_MFA_DASHBOARD_FRONTEND");
        var repository = Environment.GetEnvironmentVariable("RACKCLICK_MFA_DASHBOARD_REPOSITORY");
        Assert.SkipWhen(string.IsNullOrEmpty(frontend) || string.IsNullOrEmpty(repository), "Explicit frontend build and repository browser runner required.");
        var output = Environment.GetEnvironmentVariable("RACKCLICK_MFA_DASHBOARD_OUTPUT")
            ?? Path.Combine(Path.GetTempPath(), "rc-mfa-dashboard-browser-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(output);
        await using var h = await Harness.Create(frontend);
        var ordinary = await h.Lab.AddUser("grace.browser.user"); await h.Lab.Legacy(ordinary.Id);
        var start = new ProcessStartInfo(Path.Combine(repository!, ".local", "node-v24.21.0-win-x64", "node.exe"))
        {
            UseShellExecute = false, CreateNoWindow = true, RedirectStandardOutput = true, RedirectStandardError = true,
            WorkingDirectory = Path.Combine(repository!, "development", "frontend"),
        };
        start.ArgumentList.Add(Path.Combine(repository!, "development", "frontend", "tests", "browser-mfa-dashboard.mjs"));
        foreach (var name in start.Environment.Keys.Where(key => key.StartsWith("CORECLR_", StringComparison.OrdinalIgnoreCase)
                     || key.StartsWith("DOTNET_", StringComparison.OrdinalIgnoreCase)).ToArray()) start.Environment.Remove(name);
        start.Environment["RACKCLICK_TEST_ORIGIN"] = h.Origin;
        start.Environment["RACKCLICK_TEST_USERNAME"] = h.Lab.Admin.UserName;
        start.Environment["RACKCLICK_TEST_PASSWORD"] = AccountLab.Password;
        start.Environment["RACKCLICK_TEST_GRACE_USER"] = ordinary.UserName;
        start.Environment["RACKCLICK_TEST_GRACE_USER_ID"] = ordinary.Id.ToString("D");
        start.Environment["RACKCLICK_TEST_OUTPUT"] = output;
        using var process = Process.Start(start) ?? throw new InvalidOperationException("Browser process unavailable.");
        using var timeout = CancellationTokenSource.CreateLinkedTokenSource(TestContext.Current.CancellationToken);
        timeout.CancelAfter(TimeSpan.FromMinutes(5));
        var stdout = process.StandardOutput.ReadToEndAsync(timeout.Token);
        var stderr = process.StandardError.ReadToEndAsync(timeout.Token);
        try { await process.WaitForExitAsync(timeout.Token); }
        catch (OperationCanceledException) { if (!process.HasExited) process.Kill(entireProcessTree: true); throw; }
        await File.WriteAllTextAsync(Path.Combine(output, "browser-process.txt"), await stdout + "\n" + await stderr, TestContext.Current.CancellationToken);
        Assert.Equal(0, process.ExitCode);
    }

    private static async Task<string> Error(HttpResponseMessage response)
    {
        using var json = JsonDocument.Parse(await response.Content.ReadAsStringAsync(TestContext.Current.CancellationToken));
        return json.RootElement.GetProperty("error").GetString()!;
    }

    private sealed record Authentication(string Cookie, string Csrf, Guid UserId);
    private sealed class Harness : IAsyncDisposable
    {
        private readonly Dictionary<string, string?> _previous = [];
        private readonly byte[] _key = RandomNumberGenerator.GetBytes(32);
        private WebApplicationFactory<Program> _factory = null!;
        private HttpClient _client = null!;
        public AccountLab Lab { get; private set; } = null!;
        public string Origin { get; private set; } = "https://rackclick.test";

        public static async Task<Harness> Create(string? frontend = null)
        {
            var h = new Harness { Lab = await AccountLab.Create() };
            try
            {
                await h.Lab.Policy(10);
                h.Set("ConnectionStrings__RackClick", h.Lab.RuntimeConnection);
                h.Set("MfaKeyStore__Enabled", "false");
                h.Set("RackClick__FrontendPath", frontend);
                if (frontend is not null)
                {
                    var listener = new System.Net.Sockets.TcpListener(IPAddress.Loopback, 0);
                    listener.Start(); int port = ((IPEndPoint)listener.LocalEndpoint).Port; listener.Stop();
                    h.Origin = "http://127.0.0.1:" + port;
                    h.Set("DevelopmentLoopbackHttp", "true");
                }
                h.Set("PublicOrigin", h.Origin);
                h._factory = new WebApplicationFactory<Program>().WithWebHostBuilder(builder =>
                {
                    builder.UseEnvironment(frontend is null ? "Production" : "Development");
                    builder.ConfigureLogging(logging => logging.ClearProviders());
                    builder.ConfigureTestServices(services => services.AddSingleton<IMfaKeyProvider>(new SyntheticKeys(h._key)));
                });
                if (frontend is not null)
                {
                    h._factory.UseKestrel(new Uri(h.Origin).Port); h._factory.StartServer();
                }
                h._client = h._factory.CreateClient(new WebApplicationFactoryClientOptions { BaseAddress = new Uri(h.Origin), HandleCookies = false });
                return h;
            }
            catch { await h.DisposeAsync(); throw; }
        }

        private void Set(string name, string? value) { _previous.TryAdd(name, Environment.GetEnvironmentVariable(name)); Environment.SetEnvironmentVariable(name, value); }
        public Task<HttpResponseMessage> Get(string path, string cookie)
        {
            var request = new HttpRequestMessage(HttpMethod.Get, path); request.Headers.Add("Cookie", cookie);
            return _client.SendAsync(request, TestContext.Current.CancellationToken);
        }
        public Task<HttpResponseMessage> Post(string path, object body, Authentication? auth = null, long? revision = null,
            string? origin = null, Guid? actor = null)
        {
            var request = new HttpRequestMessage(HttpMethod.Post, path) { Content = new StringContent(JsonSerializer.Serialize(body), System.Text.Encoding.UTF8, "application/json") };
            request.Headers.Add("Origin", origin ?? Origin);
            if (auth is not null)
            {
                request.Headers.Add("Cookie", auth.Cookie); request.Headers.Add("X-RackClick-CSRF", auth.Csrf);
                request.Headers.Add("X-RackClick-Actor", (actor ?? auth.UserId).ToString("D"));
            }
            if (revision.HasValue) { request.Headers.Add("If-Match", "\"" + revision + "\""); request.Headers.Add("Idempotency-Key", Guid.NewGuid().ToString("D")); }
            return _client.SendAsync(request, TestContext.Current.CancellationToken);
        }
        public async Task<Authentication> Login(string username)
        {
            using var response = await Post("/api/v1/auth/login", new { username, password = AccountLab.Password });
            Assert.Equal(HttpStatusCode.OK, response.StatusCode);
            using var data = JsonDocument.Parse(await response.Content.ReadAsStringAsync(TestContext.Current.CancellationToken));
            string cookie = Cookie(response, "RackClick.Session");
            using var me = await Get("/api/v1/me", cookie);
            using var identity = JsonDocument.Parse(await me.Content.ReadAsStringAsync(TestContext.Current.CancellationToken));
            return new(cookie, data.RootElement.GetProperty("csrf").GetString()!, identity.RootElement.GetProperty("user").GetProperty("id").GetGuid());
        }
        public async Task<Authentication> Enroll(string username)
        {
            using var login = await Post("/api/v1/auth/login", new { username, password = AccountLab.Password });
            Assert.Equal(HttpStatusCode.Accepted, login.StatusCode);
            using var challenge = JsonDocument.Parse(await login.Content.ReadAsStringAsync(TestContext.Current.CancellationToken));
            Assert.Equal("enroll", challenge.RootElement.GetProperty("purpose").GetString());
            var auth = new Authentication(Cookie(login, "RackClick.MfaChallenge"), challenge.RootElement.GetProperty("csrf").GetString()!, Guid.Empty);
            using var start = await Post("/api/v1/auth/mfa/enroll/start", new { }, auth);
            Assert.Equal(HttpStatusCode.OK, start.StatusCode);
            using var setup = JsonDocument.Parse(await start.Content.ReadAsStringAsync(TestContext.Current.CancellationToken));
            var secret = Base32Encoding.ToBytes(setup.RootElement.GetProperty("secret").GetString()!);
            string code;
            try { code = new Totp(secret).ComputeTotp(DateTime.UtcNow); }
            finally { CryptographicOperations.ZeroMemory(secret); }
            using var confirm = await Post("/api/v1/auth/mfa/enroll/confirm", new { code }, auth);
            Assert.Equal(HttpStatusCode.OK, confirm.StatusCode);
            using var data = JsonDocument.Parse(await confirm.Content.ReadAsStringAsync(TestContext.Current.CancellationToken));
            string cookie = Cookie(confirm, "RackClick.Session");
            using var me = await Get("/api/v1/me", cookie);
            using var identity = JsonDocument.Parse(await me.Content.ReadAsStringAsync(TestContext.Current.CancellationToken));
            return new(cookie, data.RootElement.GetProperty("csrf").GetString()!, identity.RootElement.GetProperty("user").GetProperty("id").GetGuid());
        }
        public async Task<long> Revision(Guid id, Authentication auth, bool admin = false)
        {
            using var response = await Get(admin ? "/api/v1/admin/users/" + id + "/mfa" : "/api/v1/me/mfa", auth.Cookie);
            Assert.Equal(HttpStatusCode.OK, response.StatusCode);
            using var data = JsonDocument.Parse(await response.Content.ReadAsStringAsync(TestContext.Current.CancellationToken));
            return data.RootElement.GetProperty("revision").GetInt64();
        }
        private static string Cookie(HttpResponseMessage response, string name) => response.Headers.GetValues("Set-Cookie")
            .Single(value => value.StartsWith(name + "=", StringComparison.Ordinal) && !value.StartsWith(name + "=;", StringComparison.Ordinal)).Split(';')[0];
        public async ValueTask DisposeAsync()
        {
            try { _client?.Dispose(); if (_factory is not null) await _factory.DisposeAsync(); }
            finally
            {
                try { if (Lab is not null) await Lab.DisposeAsync(); }
                finally { foreach (var (name, value) in _previous) Environment.SetEnvironmentVariable(name, value); CryptographicOperations.ZeroMemory(_key); }
            }
        }
    }
    private sealed class SyntheticKeys(byte[] key) : IMfaKeyProvider
    {
        public byte[] GetKey(int version) => version == 1 ? (byte[])key.Clone() : throw new InvalidOperationException("test_key_unavailable");
        public (int Version, byte[] Key) GetActiveKey() => (1, (byte[])key.Clone());
    }
}
