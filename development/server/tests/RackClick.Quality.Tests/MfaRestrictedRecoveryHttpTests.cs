using System.Net;
using System.Net.Http.Json;
using System.Security.Cryptography;
using System.Text.Json;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.AspNetCore.TestHost;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;
using Npgsql;
using OtpNet;
using RackClick.Server;
using Xunit;
using Lab = RackClick.Quality.Tests.MfaAccountManagementTests.Laboratory;

namespace RackClick.Quality.Tests;

// F-08.02: test-only host/keys, actual middleware and separate restricted PostgreSQL role.
// No installed service, account, MFA store or browser is used.
[Collection("MfaHttp")]
public sealed class MfaRestrictedRecoveryHttpTests
{
    private static CancellationToken Ct => TestContext.Current.CancellationToken;
    private const string Origin = "https://rackclick.test";
    private sealed record Auth(string Cookie, string Csrf)
    {
        public override string ToString() => nameof(Auth);
    }
    private sealed class Keys(byte[] key) : IMfaKeyProvider
    {
        public byte[] GetKey(int version) => (byte[])key.Clone();
        public (int Version, byte[] Key) GetActiveKey() => (1, (byte[])key.Clone());
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task RecoveryNeverAuthorizesTheApiUntilTheNewFactorIsConfirmed(bool globalAdministrator)
    {
        await using var lab = await Lab.Create();
        var actor = globalAdministrator ? lab.Admin : await lab.AddUser("restricted.ordinary");
        await lab.Policy(50);
        await lab.Execute("""
            DELETE FROM app_session;
            UPDATE app_user SET created_at=clock_timestamp()-interval '46 days' WHERE id=@user;
            INSERT INTO app_mfa_user(systemhaus_id,user_id,mfa_required,enrollment_pending,revision)
            VALUES(@house,@user,true,true,1);
            """, ("house", lab.House), ("user", actor.Id));
        var policyBefore = await lab.Snapshot("app_mfa_policy");
        var role = new NpgsqlConnectionStringBuilder(lab.RuntimeConnection).Username!;
        Assert.Matches("^rc_mfa_dashboard_runtime_[a-f0-9]{32}$", role);
        foreach (var table in new[] { "hardware_definition", "hardware_mount_slot", "hardware_group_template",
            "hardware_passthrough", "hardware_connector_template", "hardware_profile_extension", "hardware_group_extension" })
            await lab.Execute($"REVOKE ALL ON {table} FROM {role}; GRANT SELECT ON {table} TO {role}");
        await using (var db = new NpgsqlConnection(lab.RuntimeConnection))
        {
            await db.OpenAsync(Ct);
            await using var command = new NpgsqlCommand("CREATE TABLE public.f0802_forbidden(id int)", db);
            Assert.Equal("42501", (await Assert.ThrowsAsync<PostgresException>(() => command.ExecuteNonQueryAsync(Ct))).SqlState);
        }

        byte[] key = RandomNumberGenerator.GetBytes(32);
        byte[]? initialSecret = null, replacementSecret = null;
        var previous = new Dictionary<string, string?>();
        WebApplicationFactory<Program>? factory = null;
        void Set(string name, string? value)
        {
            previous.Add(name, Environment.GetEnvironmentVariable(name));
            Environment.SetEnvironmentVariable(name, value);
        }
        try
        {
            Set("ConnectionStrings__RackClick", lab.RuntimeConnection);
            Set("PublicOrigin", Origin);
            Set("MfaKeyStore__Enabled", "false");
            Set("RackClick__FrontendPath", null);
            factory = new WebApplicationFactory<Program>().WithWebHostBuilder(b =>
            {
                b.ConfigureLogging(l => l.ClearProviders());
                b.ConfigureTestServices(s => s.AddSingleton<IMfaKeyProvider>(new Keys(key)));
            });
            using var client = factory.CreateClient(new WebApplicationFactoryClientOptions
                { BaseAddress = new Uri(Origin), HandleCookies = false });
            async Task<HttpResponseMessage> Send(string method, string path, object? body = null,
                Auth? auth = null, long? revision = null, Guid? requestId = null)
            {
                using var request = new HttpRequestMessage(new HttpMethod(method), path);
                if (body is not null) request.Content = JsonContent.Create(body);
                if (method != "GET") request.Headers.Add("Origin", Origin);
                if (auth is not null)
                {
                    request.Headers.Add("Cookie", auth.Cookie);
                    request.Headers.Add("X-RackClick-CSRF", auth.Csrf);
                    request.Headers.Add("X-RackClick-Actor", actor.Id.ToString());
                }
                if (revision.HasValue) request.Headers.Add("If-Match", "\"" + revision + "\"");
                if (requestId.HasValue) request.Headers.Add("Idempotency-Key", requestId.Value.ToString());
                return await client.SendAsync(request, Ct);
            }
            static string CookieLine(HttpResponseMessage response, string name) =>
                response.Headers.GetValues("Set-Cookie").Single(s =>
                    s.StartsWith(name + "=", StringComparison.Ordinal) && !s.StartsWith(name + "=;", StringComparison.Ordinal));
            static void NoSession(HttpResponseMessage response) => Assert.False(
                response.Headers.TryGetValues("Set-Cookie", out var cookies) && cookies.Any(s =>
                    s.StartsWith("RackClick.Session=", StringComparison.Ordinal) && !s.StartsWith("RackClick.Session=;", StringComparison.Ordinal)),
                "A restricted response emitted an API session cookie.");
            static void CookieAttributes(string line, string path)
            {
                line = line.ToLowerInvariant();
                foreach (var part in new[] { "httponly", "secure", "samesite=strict", "path=" + path })
                    Assert.Contains(part, line);
            }
            async Task<Auth> Login(string purpose)
            {
                using var response = await Send("POST", "/api/v1/auth/login", new { username = actor.UserName, password = Lab.Password });
                Assert.Equal(HttpStatusCode.Accepted, response.StatusCode);
                NoSession(response);
                var json = await response.Content.ReadFromJsonAsync<JsonElement>(Ct);
                Assert.Equal(purpose, json.GetProperty("purpose").GetString());
                return new(CookieLine(response, "RackClick.MfaChallenge").Split(';')[0], json.GetProperty("csrf").GetString()!);
            }
            async Task<byte[]> Start(Auth auth)
            {
                using var response = await Send("POST", "/api/v1/auth/mfa/enroll/start", new { }, auth);
                Assert.Equal(HttpStatusCode.OK, response.StatusCode); NoSession(response);
                return Base32Encoding.ToBytes((await response.Content.ReadFromJsonAsync<JsonElement>(Ct)).GetProperty("secret").GetString()!);
            }
            async Task<Auth> Confirm(Auth auth, byte[] secret)
            {
                using var response = await Send("POST", "/api/v1/auth/mfa/enroll/confirm",
                    new { code = MfaTotp.Compute(secret, DateTimeOffset.UtcNow) }, auth);
                Assert.Equal(HttpStatusCode.OK, response.StatusCode);
                var line = CookieLine(response, "RackClick.Session"); CookieAttributes(line, "/");
                return new(line.Split(';')[0], (await response.Content.ReadFromJsonAsync<JsonElement>(Ct)).GetProperty("csrf").GetString()!);
            }
            async Task Restricted(Auth challenge, Auth oldSession)
            {
                var before = await lab.SnapshotAll();
                var renamed = challenge with { Cookie = "RackClick.Session=" + challenge.Cookie[(challenge.Cookie.IndexOf('=') + 1)..] };
                foreach (var candidate in new Auth?[] { null, challenge, renamed, oldSession })
                foreach (var (method, path, body) in new (string, string, object?)[]
                {
                    ("GET", "/api/v1/me", null), ("GET", "/api/v1/customers", null),
                    ("POST", "/api/v1/customers", new { name = "Blocked synthetic recovery mutation" }),
                    ("POST", "/api/v1/me/preferences", new { language = "en", theme = "dark" })
                })
                {
                    using var denied = await Send(method, path, body, candidate);
                    Assert.Equal(HttpStatusCode.Unauthorized, denied.StatusCode); NoSession(denied);
                }
                Assert.True(before == await lab.SnapshotAll(), "Protected requests changed persisted recovery state.");
                Assert.Equal(0, await lab.Count("SELECT count(*) FROM app_session"));
            }

            using (var wrong = await Send("POST", "/api/v1/auth/login", new { username = actor.UserName, password = "intentionally-invalid-synthetic-value" }))
            {
                Assert.Equal(HttpStatusCode.Unauthorized, wrong.StatusCode); NoSession(wrong);
                Assert.Equal(0, await lab.Count("SELECT count(*) FROM app_mfa_challenge"));
                Assert.Equal(0, await lab.Count("SELECT count(*) FROM app_session"));
            }
            // Arrange the pre-existing factor/session through the same store, without spending
            // the ten-per-minute HTTP budget on a flow already covered by F-07.05.
            var initial = (await lab.Store.AuthenticateForLogin(actor.UserName, Lab.Password, Ct)).Challenge!.Value;
            var initialStore = new MfaStore(lab.RuntimeSource, new Keys(key));
            var initialStart = await initialStore.StartEnrollment(initial.Token, initial.Csrf, Ct);
            initialSecret = Base32Encoding.ToBytes(initialStart.SecretBase32);
            var initialSession = await initialStore.ConfirmEnrollment(initial.Token,
                MfaTotp.Compute(initialSecret, DateTimeOffset.UtcNow), initial.Csrf, Ct);
            var oldSession = new Auth("RackClick.Session=" + initialSession.Token, initialSession.Csrf);
            using var status = await Send("GET", "/api/v1/me/mfa/recovery-codes", auth: oldSession);
            Assert.Equal(HttpStatusCode.OK, status.StatusCode);
            long revision = (await status.Content.ReadFromJsonAsync<JsonElement>(Ct)).GetProperty("revision").GetInt64();
            using var generate = await Send("POST", "/api/v1/me/mfa/recovery-codes", new { password = Lab.Password }, oldSession, revision, Guid.NewGuid());
            Assert.Equal(HttpStatusCode.OK, generate.StatusCode);
            var codes = (await generate.Content.ReadFromJsonAsync<JsonElement>(Ct)).GetProperty("codes").EnumerateArray().Select(v => v.GetString()!).ToArray();
            Assert.Equal(10, codes.Length);
            using (var noPasswordProof = await Send("POST", "/api/v1/auth/mfa/recover", new { code = codes[0] }))
                Assert.Equal(HttpStatusCode.Unauthorized, noPasswordProof.StatusCode);
            Assert.Equal(10, await lab.Count("SELECT count(*) FROM app_mfa_recovery_code WHERE consumed_at IS NULL"));

            var verify = await Login("verify");
            using var recovered = await Send("POST", "/api/v1/auth/mfa/recover", new { code = codes[0] }, verify);
            Assert.Equal(HttpStatusCode.Accepted, recovered.StatusCode); NoSession(recovered);
            Assert.Contains("no-store", recovered.Headers.CacheControl!.ToString());
            var result = await recovered.Content.ReadFromJsonAsync<JsonElement>(Ct);
            Assert.Equal(new[] { "csrf", "mfaRequired", "purpose" }, result.EnumerateObject().Select(v => v.Name).Order().ToArray());
            Assert.True(result.GetProperty("mfaRequired").GetBoolean()); Assert.Equal("enroll", result.GetProperty("purpose").GetString());
            var challengeLine = CookieLine(recovered, "RackClick.MfaChallenge"); CookieAttributes(challengeLine, "/api/v1/auth/mfa");
            var enroll = new Auth(challengeLine.Split(';')[0], result.GetProperty("csrf").GetString()!);
            Assert.True(enroll.Cookie != verify.Cookie && enroll.Csrf != verify.Csrf, "Recovery reused its verify credentials.");
            Assert.Equal(1, await lab.Count("SELECT count(*) FROM app_mfa_user WHERE user_id=@user AND enrollment_pending", ("user", actor.Id)));
            await Restricted(enroll, oldSession);
            replacementSecret = await Start(enroll);
            await Restricted(enroll, oldSession);
            var accepted = new HashSet<string>(Enumerable.Range(-1, 3).Select(i =>
                MfaTotp.Compute(replacementSecret, DateTimeOffset.UtcNow.AddSeconds(i * MfaTotp.StepSeconds))));
            var wrongCode = Enumerable.Range(0, 10).Select(i => i.ToString("D6")).First(v => !accepted.Contains(v));
            using (var wrong = await Send("POST", "/api/v1/auth/mfa/enroll/confirm", new { code = wrongCode }, enroll))
            { Assert.Equal(HttpStatusCode.Unauthorized, wrong.StatusCode); NoSession(wrong); }
            await Restricted(enroll, oldSession);
            // A global exemption must not bypass a recovery that explicitly requires reenrollment.
            var secondLogin = await Login("enroll"); await Restricted(secondLogin, oldSession);
            var fresh = await Confirm(enroll, replacementSecret);
            Assert.True(fresh.Cookie != oldSession.Cookie && fresh.Cookie != enroll.Cookie && fresh.Csrf != enroll.Csrf,
                "Confirmation must issue fresh session credentials.");
            using (var me = await Send("GET", "/api/v1/me", auth: fresh)) Assert.Equal(HttpStatusCode.OK, me.StatusCode);
            using (var old = await Send("GET", "/api/v1/me", auth: oldSession)) Assert.Equal(HttpStatusCode.Unauthorized, old.StatusCode);
            Assert.Equal(1, await lab.Count("SELECT count(*) FROM app_session WHERE user_id=@user AND mfa_verified_at IS NOT NULL", ("user", actor.Id)));
            Assert.Equal(1, await lab.Count("SELECT count(*) FROM app_mfa_factor WHERE user_id=@user AND state='active'", ("user", actor.Id)));
            Assert.Equal(0, await lab.Count("SELECT count(*) FROM app_mfa_user WHERE user_id=@user AND enrollment_pending", ("user", actor.Id)));
            Assert.True(policyBefore == await lab.Snapshot("app_mfa_policy"), "Recovery changed the grace policy.");
        }
        finally
        {
            if (initialSecret is not null) CryptographicOperations.ZeroMemory(initialSecret);
            if (replacementSecret is not null) CryptographicOperations.ZeroMemory(replacementSecret);
            try { if (factory is not null) await factory.DisposeAsync(); }
            finally
            {
                foreach (var (name, value) in previous) Environment.SetEnvironmentVariable(name, value);
                CryptographicOperations.ZeroMemory(key);
            }
        }
    }
}
