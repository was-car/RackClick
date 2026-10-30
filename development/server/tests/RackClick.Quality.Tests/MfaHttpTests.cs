using System.Net;
using System.Net.Http.Json;
using System.Security.Cryptography;
using System.Text.Json;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.AspNetCore.TestHost;
using Microsoft.Extensions.DependencyInjection;
using Npgsql;
using OtpNet;
using RackClick.Domain;
using RackClick.Server;
using Xunit;

namespace RackClick.Quality.Tests;

[CollectionDefinition("MfaHttp", DisableParallelization = true)]
public sealed class MfaHttpCollection
{
}

// Pruebas HTTP del enrolamiento MFA (MFA-L1) con el pipeline real: WebApplicationFactory ejecuta Program, el middleware
// y los endpoints. Es integración en memoria: no acredita TCP, TLS ni cookies de un navegador real.
// Usa PostgreSQL 17 de laboratorio (RACKCLICK_TEST_PG_ADMIN): base temporal propia, migraciones 001–015.
// La conexión del servidor usa el rol administrador del laboratorio (no el rol de ejecución restringido): limitación declarada.
[Collection("MfaHttp")]
public sealed class MfaHttpTests
{
    private const string AdminVariable = "RACKCLICK_TEST_PG_ADMIN";
    private const string Origin = "https://rackclick.test";
    private const string UserName = "usuario-http";
    private static readonly string Password = "RcTest-" + Convert.ToHexString(System.Security.Cryptography.RandomNumberGenerator.GetBytes(24));

    [Fact]
    public async Task EnrollmentOverHttpThenApiAndNextVerifyLogin()
    {
        await using var h = await Harness.CreateAsync(withProvider: true);
        await h.CreateUserAsync(mfaRequired: true, withActiveFactor: false);
        var ct = TestContext.Current.CancellationToken;

        var login = await h.Post("/api/v1/auth/login", new { username = UserName, password = Password });
        Assert.Equal(202, (int)login.StatusCode);
        var login1 = await login.Content.ReadFromJsonAsync<JsonElement>(ct);
        Assert.Equal("enroll", login1.GetProperty("purpose").GetString());
        var enrollCookie = Cookie(login, "RackClick.MfaChallenge");
        var enrollCsrf = login1.GetProperty("csrf").GetString()!;

        var start = await h.Post("/api/v1/auth/mfa/enroll/start", null, enrollCookie, enrollCsrf);
        Assert.Equal(HttpStatusCode.OK, start.StatusCode);
        var secret = (await start.Content.ReadFromJsonAsync<JsonElement>(ct)).GetProperty("secret").GetString()!;
        var code = MfaTotp.Compute(Base32Encoding.ToBytes(secret), DateTimeOffset.UtcNow);

        var confirm = await h.Post("/api/v1/auth/mfa/enroll/confirm", new { code }, enrollCookie, enrollCsrf);
        Assert.Equal(HttpStatusCode.OK, confirm.StatusCode);
        var sessionCookie = Cookie(confirm, "RackClick.Session");
        Assert.Equal(HttpStatusCode.OK, (await h.Get("/api/v1/me", sessionCookie)).StatusCode);

        var next = await h.Post("/api/v1/auth/login", new { username = UserName, password = Password });
        Assert.Equal(202, (int)next.StatusCode);
        var next1 = await next.Content.ReadFromJsonAsync<JsonElement>(ct);
        Assert.Equal("verify", next1.GetProperty("purpose").GetString());
        var verifyCookie = Cookie(next, "RackClick.MfaChallenge");
        var verifyCsrf = next1.GetProperty("csrf").GetString()!;
        var nextCode = MfaTotp.Compute(Base32Encoding.ToBytes(secret), DateTimeOffset.UtcNow.AddSeconds(MfaTotp.StepSeconds));
        var verify = await h.Post("/api/v1/auth/mfa/verify", new { code = nextCode }, verifyCookie, verifyCsrf);
        Assert.Equal(HttpStatusCode.OK, verify.StatusCode);
        Assert.Equal(HttpStatusCode.OK, (await h.Get("/api/v1/me", Cookie(verify, "RackClick.Session"))).StatusCode);

        Assert.Equal(2, await h.CountAsync("SELECT count(*) FROM app_session WHERE mfa_verified_at IS NOT NULL"));
    }

    [Fact]
    public async Task CookieAttributesKeepChallengeAndSessionRestricted()
    {
        await using var h = await Harness.CreateAsync(withProvider: true);
        await h.CreateUserAsync(mfaRequired: true, withActiveFactor: false);
        var ct = TestContext.Current.CancellationToken;

        var login = await h.Post("/api/v1/auth/login", new { username = UserName, password = Password });
        AssertCookieAttributes(SetCookieLine(login, "RackClick.MfaChallenge"), "/api/v1/auth/mfa");
        var login1 = await login.Content.ReadFromJsonAsync<JsonElement>(ct);
        var cookie = Cookie(login, "RackClick.MfaChallenge");
        var csrf = login1.GetProperty("csrf").GetString()!;

        var start = await h.Post("/api/v1/auth/mfa/enroll/start", null, cookie, csrf);
        var secret = Base32Encoding.ToBytes((await start.Content.ReadFromJsonAsync<JsonElement>(ct)).GetProperty("secret").GetString()!);
        var confirm = await h.Post("/api/v1/auth/mfa/enroll/confirm", new { code = MfaTotp.Compute(secret, DateTimeOffset.UtcNow) }, cookie, csrf);
        Assert.Equal(HttpStatusCode.OK, confirm.StatusCode);

        AssertCookieAttributes(SetCookieLine(confirm, "RackClick.Session"), "/");
        var cleared = SetCookieLine(confirm, "RackClick.MfaChallenge");
        Assert.StartsWith("RackClick.MfaChallenge=;", cleared, StringComparison.Ordinal);
        var clearedAttributes = Attributes(cleared);
        Assert.Contains("path=/api/v1/auth/mfa", clearedAttributes);
        Assert.Contains(clearedAttributes, a => a.StartsWith("expires=thu, 01 jan 1970", StringComparison.Ordinal));
    }

    [Fact]
    public async Task ChallengeCookieNeverOpensTheApi()
    {
        await using var h = await Harness.CreateAsync(withProvider: true);
        await h.CreateUserAsync(mfaRequired: true, withActiveFactor: false);
        var login = await h.Post("/api/v1/auth/login", new { username = UserName, password = Password });
        var cookie = Cookie(login, "RackClick.MfaChallenge");

        Assert.Equal(HttpStatusCode.Unauthorized, (await h.Get("/api/v1/me", cookie)).StatusCode);
        var logout = await h.Post("/api/v1/auth/logout", null, cookie, "no-es-csrf");
        Assert.Equal(HttpStatusCode.Unauthorized, logout.StatusCode);
        Assert.Equal(0, await h.CountAsync("SELECT count(*) FROM app_session"));
    }

    [Fact]
    public async Task ForeignOriginOrWrongCsrfNeverConsumesTheChallenge()
    {
        await using var h = await Harness.CreateAsync(withProvider: true);
        await h.CreateUserAsync(mfaRequired: true, withActiveFactor: false);
        var login = await h.Post("/api/v1/auth/login", new { username = UserName, password = Password });
        var login1 = await login.Content.ReadFromJsonAsync<JsonElement>(TestContext.Current.CancellationToken);
        var cookie = Cookie(login, "RackClick.MfaChallenge");
        var csrf = login1.GetProperty("csrf").GetString()!;
        var start = await h.Post("/api/v1/auth/mfa/enroll/start", null, cookie, csrf);
        var secret = (await start.Content.ReadFromJsonAsync<JsonElement>(TestContext.Current.CancellationToken)).GetProperty("secret").GetString()!;
        var code = MfaTotp.Compute(Base32Encoding.ToBytes(secret), DateTimeOffset.UtcNow);

        var foreign = await h.Post("/api/v1/auth/mfa/enroll/confirm", new { code }, cookie, csrf, origin: "https://evil.test");
        Assert.Equal(HttpStatusCode.Forbidden, foreign.StatusCode);
        var wrongCsrf = await h.Post("/api/v1/auth/mfa/enroll/confirm", new { code }, cookie, "no-es-csrf");
        Assert.Equal(HttpStatusCode.Forbidden, wrongCsrf.StatusCode);
        Assert.Equal(1, await h.CountAsync("SELECT count(*) FROM app_mfa_challenge WHERE purpose='enroll' AND consumed_at IS NULL"));
        Assert.Equal(0, await h.CountAsync("SELECT failed_attempts FROM app_mfa_factor"));

        var ok = await h.Post("/api/v1/auth/mfa/enroll/confirm", new { code }, cookie, csrf);
        Assert.Equal(HttpStatusCode.OK, ok.StatusCode);
    }

    [Fact]
    public async Task StartAndConfirmWithoutChallengeCookieAreRejected()
    {
        await using var h = await Harness.CreateAsync(withProvider: true);
        await h.CreateUserAsync(mfaRequired: true, withActiveFactor: false);

        var start = await h.Post("/api/v1/auth/mfa/enroll/start", null, null, "x");
        var confirm = await h.Post("/api/v1/auth/mfa/enroll/confirm", new { code = "000000" }, null, "x");

        Assert.Equal(HttpStatusCode.Unauthorized, start.StatusCode);
        Assert.Equal("mfa_challenge_invalid", (await start.Content.ReadFromJsonAsync<JsonElement>(TestContext.Current.CancellationToken)).GetProperty("error").GetString());
        Assert.Equal(HttpStatusCode.Unauthorized, confirm.StatusCode);
    }

    [Fact]
    public async Task VerifyChallengeCannotEnrollAndStillCompletesLogin()
    {
        await using var h = await Harness.CreateAsync(withProvider: true);
        var secret = await h.CreateUserAsync(mfaRequired: true, withActiveFactor: true);
        var ct = TestContext.Current.CancellationToken;
        var login = await h.Post("/api/v1/auth/login", new { username = UserName, password = Password });
        var login1 = await login.Content.ReadFromJsonAsync<JsonElement>(ct);
        Assert.Equal("verify", login1.GetProperty("purpose").GetString());
        var cookie = Cookie(login, "RackClick.MfaChallenge");
        var csrf = login1.GetProperty("csrf").GetString()!;

        var misuse = await h.Post("/api/v1/auth/mfa/enroll/start", null, cookie, csrf);
        Assert.Equal(HttpStatusCode.Unauthorized, misuse.StatusCode);
        Assert.Equal(1, await h.CountAsync("SELECT count(*) FROM app_mfa_challenge WHERE purpose='verify' AND consumed_at IS NULL"));

        var code = MfaTotp.Compute(secret, DateTimeOffset.UtcNow);
        var verify = await h.Post("/api/v1/auth/mfa/verify", new { code }, cookie, csrf);
        Assert.Equal(HttpStatusCode.OK, verify.StatusCode);
    }

    [Fact]
    public async Task WrongCodeCountsOverHttpAndReplayIsRejected()
    {
        await using var h = await Harness.CreateAsync(withProvider: true);
        await h.CreateUserAsync(mfaRequired: true, withActiveFactor: false);
        var login = await h.Post("/api/v1/auth/login", new { username = UserName, password = Password });
        var login1 = await login.Content.ReadFromJsonAsync<JsonElement>(TestContext.Current.CancellationToken);
        var cookie = Cookie(login, "RackClick.MfaChallenge");
        var csrf = login1.GetProperty("csrf").GetString()!;
        var start = await h.Post("/api/v1/auth/mfa/enroll/start", null, cookie, csrf);
        var secret = Base32Encoding.ToBytes((await start.Content.ReadFromJsonAsync<JsonElement>(TestContext.Current.CancellationToken)).GetProperty("secret").GetString()!);
        var good = MfaTotp.Compute(secret, DateTimeOffset.UtcNow);
        var wrong = good == "000000" ? "111111" : "000000";

        var bad = await h.Post("/api/v1/auth/mfa/enroll/confirm", new { code = wrong }, cookie, csrf);
        Assert.Equal(HttpStatusCode.Unauthorized, bad.StatusCode);
        Assert.Equal("mfa_code_invalid", (await bad.Content.ReadFromJsonAsync<JsonElement>(TestContext.Current.CancellationToken)).GetProperty("error").GetString());
        Assert.Equal(1, await h.CountAsync("SELECT failed_attempts FROM app_mfa_factor"));

        var ok = await h.Post("/api/v1/auth/mfa/enroll/confirm", new { code = good }, cookie, csrf);
        Assert.Equal(HttpStatusCode.OK, ok.StatusCode);
        var replay = await h.Post("/api/v1/auth/mfa/enroll/confirm", new { code = good }, cookie, csrf);
        Assert.Equal(HttpStatusCode.Unauthorized, replay.StatusCode);
        Assert.Equal(1, await h.CountAsync("SELECT count(*) FROM app_session"));
    }

    [Fact]
    public async Task StartIsRateLimitedAfterTheLoginWindowIsSpent()
    {
        await using var h = await Harness.CreateAsync(withProvider: true);
        await h.CreateUserAsync(mfaRequired: true, withActiveFactor: false);
        var login = await h.Post("/api/v1/auth/login", new { username = UserName, password = Password });
        var login1 = await login.Content.ReadFromJsonAsync<JsonElement>(TestContext.Current.CancellationToken);
        var cookie = Cookie(login, "RackClick.MfaChallenge");
        var csrf = login1.GetProperty("csrf").GetString()!;

        var statuses = new List<HttpStatusCode>();
        for (var i = 0; i < 10; i++)
            statuses.Add((await h.Post("/api/v1/auth/mfa/enroll/start", null, cookie, csrf)).StatusCode);

        Assert.All(statuses.Take(9), s => Assert.Equal(HttpStatusCode.OK, s));
        Assert.Equal(HttpStatusCode.TooManyRequests, statuses[9]);
    }

    [Fact]
    public async Task WithoutProviderLoginAndEnrollmentAreExplicitlyRejected()
    {
        await using var h = await Harness.CreateAsync(withProvider: false);
        await h.CreateUserAsync(mfaRequired: true, withActiveFactor: false);

        var login = await h.Post("/api/v1/auth/login", new { username = UserName, password = Password });
        var start = await h.Post("/api/v1/auth/mfa/enroll/start", null, null, "x");
        var confirm = await h.Post("/api/v1/auth/mfa/enroll/confirm", new { code = "000000" }, null, "x");

        Assert.Equal(HttpStatusCode.Conflict, login.StatusCode);
        Assert.Equal("mfa_enrollment_required", (await login.Content.ReadFromJsonAsync<JsonElement>(TestContext.Current.CancellationToken)).GetProperty("error").GetString());
        Assert.Equal(HttpStatusCode.ServiceUnavailable, start.StatusCode);
        Assert.Equal(HttpStatusCode.ServiceUnavailable, confirm.StatusCode);
        Assert.Equal(0, await h.CountAsync("SELECT count(*) FROM app_mfa_challenge"));
        Assert.Equal(0, await h.CountAsync("SELECT count(*) FROM app_session"));
    }

    [Fact]
    public async Task ConcurrentHttpConfirmOpensExactlyOneSession()
    {
        await using var h = await Harness.CreateAsync(withProvider: true);
        await h.CreateUserAsync(mfaRequired: true, withActiveFactor: false);
        var login = await h.Post("/api/v1/auth/login", new { username = UserName, password = Password });
        var login1 = await login.Content.ReadFromJsonAsync<JsonElement>(TestContext.Current.CancellationToken);
        var cookie = Cookie(login, "RackClick.MfaChallenge");
        var csrf = login1.GetProperty("csrf").GetString()!;
        var start = await h.Post("/api/v1/auth/mfa/enroll/start", null, cookie, csrf);
        var secret = Base32Encoding.ToBytes((await start.Content.ReadFromJsonAsync<JsonElement>(TestContext.Current.CancellationToken)).GetProperty("secret").GetString()!);
        var code = MfaTotp.Compute(secret, DateTimeOffset.UtcNow);

        var results = await Task.WhenAll(
            h.Post("/api/v1/auth/mfa/enroll/confirm", new { code }, cookie, csrf),
            h.Post("/api/v1/auth/mfa/enroll/confirm", new { code }, cookie, csrf));

        Assert.Equal(1, results.Count(r => r.StatusCode == HttpStatusCode.OK));
        Assert.Equal(1, results.Count(r => r.StatusCode == HttpStatusCode.Unauthorized));
        Assert.Equal(1, await h.CountAsync("SELECT count(*) FROM app_session"));
    }

    // Negativo de limpieza: si Dispose falla, ambas variables de entorno y la base temporal deben quedar restauradas.
    [Fact]
    public async Task CleanupRestoresBothVariablesAndDropsTheDatabaseWhenDisposeFails()
    {
        var connectionBefore = Environment.GetEnvironmentVariable("ConnectionStrings__RackClick");
        var originBefore = Environment.GetEnvironmentVariable("PublicOrigin");
        var h = await Harness.CreateAsync(withProvider: true);
        try
        {
            await h.Get("/api/v1/me", "RackClick.Session=sin-sesion");
            Assert.Equal(Origin, Environment.GetEnvironmentVariable("PublicOrigin"));
            Assert.NotEqual(connectionBefore, Environment.GetEnvironmentVariable("ConnectionStrings__RackClick"));

            h.FailCleanupForTest();
            var error = await Assert.ThrowsAsync<InvalidOperationException>(() => h.DisposeAsync().AsTask());
            Assert.Equal("limpieza simulada", error.Message);
            Assert.Equal(connectionBefore, Environment.GetEnvironmentVariable("ConnectionStrings__RackClick"));
            Assert.Equal(originBefore, Environment.GetEnvironmentVariable("PublicOrigin"));
            Assert.False(await h.DatabaseExistsAsync());
        }
        finally
        {
            await h.DisposeAsync();
        }
    }

    private static string SetCookieLine(HttpResponseMessage response, string name)
    {
        foreach (var value in response.Headers.GetValues("Set-Cookie"))
            if (value.StartsWith(name + "=", StringComparison.Ordinal)) return value;
        throw new InvalidOperationException("sin Set-Cookie " + name);
    }

    private static string Cookie(HttpResponseMessage response, string name) => SetCookieLine(response, name).Split(';')[0];

    private static string[] Attributes(string setCookie) =>
        setCookie.Split(';').Skip(1).Select(a => a.Trim().ToLowerInvariant()).ToArray();

    // Cookies de desafío y de sesión: HttpOnly, Secure (origen https), SameSite=Strict y la ruta de cada una.
    private static void AssertCookieAttributes(string setCookie, string path)
    {
        var attributes = Attributes(setCookie);
        Assert.Contains("httponly", attributes);
        Assert.Contains("secure", attributes);
        Assert.Contains("samesite=strict", attributes);
        Assert.Contains("path=" + path, attributes);
    }

    // Host de pruebas: base temporal, migraciones reales, proveedor sintético solo en ConfigureTestServices.
    private sealed class Harness : IAsyncDisposable
    {
        private readonly string _database;
        private readonly string _admin;
        private readonly byte[] _key = RandomNumberGenerator.GetBytes(MfaSecretCipher.KeyBytes);
        private readonly string? _previousConnection;
        private readonly string? _previousOrigin;
        private readonly bool _withProvider;
        private WebApplicationFactory<Program>? _factory;
        private HttpClient? _client;
        private NpgsqlDataSource? _source;
        private byte[]? _secret;
        private bool _disposed;
        private bool _failCleanup;

        private Harness(string database, string admin, bool withProvider)
        {
            _database = database;
            _admin = admin;
            _withProvider = withProvider;
            _previousConnection = Environment.GetEnvironmentVariable("ConnectionStrings__RackClick");
            _previousOrigin = Environment.GetEnvironmentVariable("PublicOrigin");
        }

        public static async Task<Harness> CreateAsync(bool withProvider)
        {
            var admin = Environment.GetEnvironmentVariable(AdminVariable);
            Assert.SkipWhen(string.IsNullOrWhiteSpace(admin), AdminVariable + " no está definido: prueba PostgreSQL omitida.");
            var database = "rc_mfa_http_" + Guid.NewGuid().ToString("N");
            await using (var connection = new NpgsqlConnection(admin))
            {
                await connection.OpenAsync();
                await using var create = new NpgsqlCommand($"CREATE DATABASE {database} ENCODING 'UTF8' TEMPLATE template0", connection);
                await create.ExecuteNonQueryAsync();
            }
            var harness = new Harness(database, admin!, withProvider);
            await harness.ApplyMigrationsAsync();
            return harness;
        }

        private string DatabaseConnection()
        {
            var builder = new NpgsqlConnectionStringBuilder(_admin) { Database = _database };
            return builder.ConnectionString;
        }

        internal NpgsqlDataSource Source() => _source ??= NpgsqlDataSource.Create(DatabaseConnection());

        // Crea el servidor y el cliente la primera vez. Las variables de entorno se restauran al cerrar el host.
        private HttpClient Client()
        {
            if (_client is not null) return _client;
            Environment.SetEnvironmentVariable("ConnectionStrings__RackClick", DatabaseConnection());
            Environment.SetEnvironmentVariable("PublicOrigin", Origin);
            var withProvider = _withProvider;
            var key = _key;
            _factory = new WebApplicationFactory<Program>().WithWebHostBuilder(builder =>
            {
                if (withProvider) builder.ConfigureTestServices(services => services.AddSingleton<IMfaKeyProvider>(new SyntheticKeys(key)));
            });
            _client = _factory.CreateClient(new WebApplicationFactoryClientOptions { BaseAddress = new Uri(Origin + "/"), HandleCookies = false });
            return _client;
        }

        public async Task<byte[]> CreateUserAsync(bool mfaRequired, bool withActiveFactor)
        {
            var systemhaus = await SystemhausAsync();
            var user = Guid.NewGuid();
            var secret = MfaTotp.NewSecret();
            _secret = secret;
            await ExecuteAsync(
                "INSERT INTO app_user(id,systemhaus_id,username,password_hash) VALUES(@user,@sh,@name,@hash)",
                ("user", user), ("sh", systemhaus), ("name", UserName), ("hash", Secrets.PasswordHash(UserName, Password)));
            await ExecuteAsync(
                "INSERT INTO app_mfa_user(systemhaus_id,user_id,mfa_required) VALUES(@sh,@user,@required)",
                ("sh", systemhaus), ("user", user), ("required", mfaRequired));
            if (withActiveFactor)
            {
                var sealedSecret = MfaSecretCipher.Seal(_key, 1, secret, systemhaus, user);
                await ExecuteAsync(
                    "INSERT INTO app_mfa_factor(systemhaus_id,user_id,state,secret_ciphertext,key_version,confirmed_at) VALUES(@sh,@user,'active',@cipher,1,now())",
                    ("sh", systemhaus), ("user", user), ("cipher", sealedSecret));
            }
            return secret;
        }

        private async Task<Guid> SystemhausAsync()
        {
            await using var connection = await Source().OpenConnectionAsync(TestContext.Current.CancellationToken);
            await using (var read = new NpgsqlCommand("SELECT id FROM systemhaus LIMIT 1", connection))
                if (await read.ExecuteScalarAsync(TestContext.Current.CancellationToken) is Guid existing) return existing;
            var id = Guid.NewGuid();
            await using var insert = new NpgsqlCommand("INSERT INTO systemhaus(id,name) VALUES(@sh,'Lab MFA HTTP')", connection);
            insert.Parameters.AddWithValue("sh", id);
            await insert.ExecuteNonQueryAsync(TestContext.Current.CancellationToken);
            return id;
        }

        public async Task<HttpResponseMessage> Post(string path, object? body, string? cookie = null, string? csrf = null, string origin = Origin)
        {
            var request = new HttpRequestMessage(HttpMethod.Post, path)
            {
                Content = body is null ? new StringContent("{}", System.Text.Encoding.UTF8, "application/json") : JsonContent.Create(body),
            };
            request.Headers.TryAddWithoutValidation("Origin", origin);
            if (cookie is not null) request.Headers.TryAddWithoutValidation("Cookie", cookie);
            if (csrf is not null) request.Headers.TryAddWithoutValidation("X-RackClick-CSRF", csrf);
            return await Client().SendAsync(request, TestContext.Current.CancellationToken);
        }

        public async Task<HttpResponseMessage> Get(string path, string cookie)
        {
            var request = new HttpRequestMessage(HttpMethod.Get, path);
            request.Headers.TryAddWithoutValidation("Cookie", cookie);
            return await Client().SendAsync(request, TestContext.Current.CancellationToken);
        }

        public async Task<long> CountAsync(string sql)
        {
            await using var connection = await Source().OpenConnectionAsync(TestContext.Current.CancellationToken);
            await using var command = new NpgsqlCommand(sql, connection);
            return Convert.ToInt64(await command.ExecuteScalarAsync(TestContext.Current.CancellationToken) ?? 0L);
        }

        public async Task ExecuteAsync(string sql, params (string Name, object Value)[] values)
        {
            await using var connection = await Source().OpenConnectionAsync(TestContext.Current.CancellationToken);
            await using var command = new NpgsqlCommand(sql, connection);
            foreach (var (name, value) in values) command.Parameters.AddWithValue(name, value);
            await command.ExecuteNonQueryAsync(TestContext.Current.CancellationToken);
        }

        private async Task ApplyMigrationsAsync()
        {
            var folder = Path.Combine(AppContext.BaseDirectory, "database");
            var files = new[]
            {
                "001-foundation.sql", "002-inventory.sql", "003-operation-cancellation.sql", "004-session-identity.sql",
                "005-audit-context.sql", "006-audit-state-intent.sql", "007-audit-context-families.sql",
                "008-user-catalog-favorites.sql", "009-private-device-templates.sql", "010-customer-shared-device-templates.sql",
                "011-user-preferences.sql", "012-user-port-colors.sql", "013-user-category-colors.sql", "014-mfa.sql", "015-mfa-account-policy.sql",
            };
            await using var connection = await Source().OpenConnectionAsync(TestContext.Current.CancellationToken);
            foreach (var name in files)
            {
                await using var command = new NpgsqlCommand(await File.ReadAllTextAsync(Path.Combine(folder, name), TestContext.Current.CancellationToken), connection);
                await command.ExecuteNonQueryAsync(TestContext.Current.CancellationToken);
            }
        }

        // Solo para el negativo de limpieza: simula un fallo de Dispose después de cerrar el host.
        internal void FailCleanupForTest() => _failCleanup = true;

        public async Task<bool> DatabaseExistsAsync()
        {
            await using var connection = new NpgsqlConnection(_admin);
            await connection.OpenAsync(TestContext.Current.CancellationToken);
            await using var command = new NpgsqlCommand("SELECT 1 FROM pg_database WHERE datname = @name", connection);
            command.Parameters.AddWithValue("name", _database);
            return await command.ExecuteScalarAsync(TestContext.Current.CancellationToken) is not null;
        }

        // Idempotente: la prueba de limpieza puede cerrar el host antes del bloque finally de la prueba.
        public async ValueTask DisposeAsync()
        {
            if (_disposed) return;
            _disposed = true;
            try
            {
                try
                {
                    _client?.Dispose();
                    if (_factory is not null) await _factory.DisposeAsync();
                    _source?.Dispose();
                    NpgsqlConnection.ClearAllPools();
                    if (_failCleanup) throw new InvalidOperationException("limpieza simulada");
                }
                finally
                {
                    await DropDatabaseAsync();
                }
            }
            finally
            {
                // Cada variable se restaura aunque falle la anterior o la eliminación de la base temporal.
                try { Environment.SetEnvironmentVariable("ConnectionStrings__RackClick", _previousConnection); }
                finally { Environment.SetEnvironmentVariable("PublicOrigin", _previousOrigin); }
            }
        }

        private async Task DropDatabaseAsync()
        {
            await using var connection = new NpgsqlConnection(_admin);
            await connection.OpenAsync();
            await using var drop = new NpgsqlCommand($"DROP DATABASE IF EXISTS {_database} WITH (FORCE)", connection);
            await drop.ExecuteNonQueryAsync();
        }
    }

    private sealed class SyntheticKeys(byte[] key) : IMfaKeyProvider
    {
        public byte[] GetKey(int version) => version == 1 ? (byte[])key.Clone() : throw new InvalidOperationException("mfa_key_version_unknown");

        // Versión activa explícita del stub (1) y copia nueva del material.
        public (int Version, byte[] Key) GetActiveKey() => (1, (byte[])key.Clone());
    }
}
