using System.Diagnostics;
using System.Net;
using System.Net.Http.Json;
using System.Runtime.Versioning;
using System.Security.Cryptography;
using System.Security.Principal;
using System.Text;
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

// Composición del proveedor Windows en el host (MFA-L2i) con el pipeline real. Dos clases de prueba:
//  - HTTP en memoria con PostgreSQL 17 de laboratorio (RACKCLICK_TEST_PG_ADMIN): el proveedor se compone desde MfaKeyStore:* con un
//    almacén TEMP sintético y el lector/parser/DPAPI aprobados. Sólo el seam de identidad es de prueba (lector Usuarios, confianza
//    Usuario de laboratorio, SYSTEM y Administradores); el diagnóstico lo declara. No es identidad efectiva del servicio.
//  - Procesos reales del servidor compilado, sin PostgreSQL: arranque cerrado con configuración inválida y contrato de la CLI.
// Comparte la colección MfaHttp porque usa variables de entorno del proceso, como MfaHttpTests.
[Collection("MfaHttp")]
[SupportedOSPlatform("windows")]
public sealed class MfaWindowsHostHttpTests
{
    private const string AdminVariable = "RACKCLICK_TEST_PG_ADMIN";
    private const string Origin = "https://rackclick.test";
    private const string UserName = "usuario-host-mfa";
    private static readonly string Password = "RcTest-" + Convert.ToHexString(System.Security.Cryptography.RandomNumberGenerator.GetBytes(24));
    private const int ActiveVersion = 7;
    private const int RetiredVersion = 1;

    private static readonly SecurityIdentifier UsersSid = new(WellKnownSidType.BuiltinUsersSid, null);
    private static readonly SecurityIdentifier LocalSystemSid = new(WellKnownSidType.LocalSystemSid, null);
    private static readonly SecurityIdentifier AdministratorsSid = new(WellKnownSidType.BuiltinAdministratorsSid, null);

    [Fact]
    public async Task RunningHostRetainsTheRingUntilItsOwnLifetimeEnds()
    {
        using var store=HostStore.Create();
        var ring=Path.Combine(store.Root,store.Installation.ToString("D"),WindowsMfaKeyProvider.KeysFolderName,MfaKeyRing.RingFileName);
        await using(var host=await Harness.CreateAsync(store))
        {
            using var response=await host.Get("/health/live","");
            Assert.Equal(HttpStatusCode.OK,response.StatusCode);
            Assert.Throws<IOException>(()=>{using var write=new FileStream(ring,FileMode.Open,FileAccess.ReadWrite,FileShare.Read);});
        }
        for(var attempt=0;attempt<100;attempt++)
        {
            try {using var afterStop=new FileStream(ring,FileMode.Open,FileAccess.ReadWrite,FileShare.Read);Assert.True(afterStop.CanRead);return;}
            catch(IOException)when(attempt<99){await Task.Delay(20,TestContext.Current.CancellationToken);}
        }
    }

    [Fact]
    public async Task EnrollmentThroughTheHostWithTheWindowsProviderOpensSessionWithTheActiveVersion()
    {
        using var store = HostStore.Create();
        await using var h = await Harness.CreateAsync(store);
        await h.CreateUserAsync();
        var ct = TestContext.Current.CancellationToken;

        var login = await h.Post("/api/v1/auth/login", new { username = UserName, password = Password });
        Assert.Equal(HttpStatusCode.Accepted, login.StatusCode);
        var challenge = Cookie(login, "RackClick.MfaChallenge");
        var csrf = (await login.Content.ReadFromJsonAsync<JsonElement>(ct)).GetProperty("csrf").GetString()!;

        var start = await h.Post("/api/v1/auth/mfa/enroll/start", null, challenge, csrf);
        Assert.Equal(HttpStatusCode.OK, start.StatusCode);
        var secret = Base32Encoding.ToBytes((await start.Content.ReadFromJsonAsync<JsonElement>(ct)).GetProperty("secret").GetString()!);
        var code = MfaTotp.Compute(secret, DateTimeOffset.UtcNow);

        var confirm = await h.Post("/api/v1/auth/mfa/enroll/confirm", new { code }, challenge, csrf);
        Assert.Equal(HttpStatusCode.OK, confirm.StatusCode);
        var session = Cookie(confirm, "RackClick.Session");
        Assert.Equal(HttpStatusCode.OK, (await h.Get("/api/v1/me", session)).StatusCode);

        Assert.Equal(ActiveVersion, await h.ScalarIntAsync("SELECT key_version FROM app_mfa_factor"));
        Assert.Equal("active", await h.ScalarTextAsync("SELECT state FROM app_mfa_factor"));
        Assert.Equal(1, await h.CountAsync("SELECT count(*) FROM app_session WHERE mfa_verified_at IS NOT NULL"));
    }

    // Pérdida de la clave activa después del arranque: 503 genérico, sin sesión, sin factor y con el desafío sin consumir.
    [Fact]
    public async Task LosingTheActiveKeyDuringExecutionAnswers503WithoutAuthorityOrPartialWrites()
    {
        using var store = HostStore.Create();
        await using var h = await Harness.CreateAsync(store);
        await h.CreateUserAsync();
        var ct = TestContext.Current.CancellationToken;
        var login = await h.Post("/api/v1/auth/login", new { username = UserName, password = Password });
        Assert.Equal(HttpStatusCode.Accepted, login.StatusCode);
        var challenge = Cookie(login, "RackClick.MfaChallenge");
        var csrf = (await login.Content.ReadFromJsonAsync<JsonElement>(ct)).GetProperty("csrf").GetString()!;

        File.Delete(store.KeyFile(ActiveVersion));
        var start = await h.Post("/api/v1/auth/mfa/enroll/start", null, challenge, csrf);

        Assert.Equal(HttpStatusCode.ServiceUnavailable, start.StatusCode);
        var text = await start.Content.ReadAsStringAsync(ct);
        var body = JsonSerializer.Deserialize<JsonElement>(text);
        Assert.Equal("service_unavailable", body.GetProperty("error").GetString());
        Assert.DoesNotContain("mfa_key", text, StringComparison.Ordinal);
        Assert.False(start.Headers.TryGetValues("Set-Cookie", out var setCookies) &&
            setCookies.Any(value => value.StartsWith("RackClick.Session=", StringComparison.Ordinal)), "se emitió sesión sin clave");
        Assert.Equal(0, await h.CountAsync("SELECT count(*) FROM app_mfa_factor"));
        Assert.Equal(0, await h.CountAsync("SELECT count(*) FROM app_session"));
        Assert.Equal(1, await h.CountAsync("SELECT count(*) FROM app_mfa_challenge WHERE purpose='enroll' AND consumed_at IS NULL"));
    }

    // Arranque cerrado con un proceso real: raíz relativa. Debe terminar con código 1, sólo el código sanitizado y sin listener.
    [Fact]
    public void StartupWithARelativeStoreRootTerminatesBeforeTheListenerWithItsCodeOnly()
    {
        var run = RunServer(new Dictionary<string, string?>
        {
            ["MfaKeyStore__Enabled"] = "true",
            ["MfaKeyStore__InstancesRoot"] = "instancias-relativas",
            ["MfaKeyStore__InstallationId"] = Guid.NewGuid().ToString("D"),
        });

        Assert.Equal(1, run.ExitCode);
        Assert.Equal("mfa_keystore_root_relative", run.Error.Trim());
        Assert.DoesNotContain("listening", run.Output, StringComparison.OrdinalIgnoreCase);
    }

    // Arranque cerrado: con MfaKeyStore habilitado y un almacén inexistente no se regenera nada y no hay listener.
    [Fact]
    public void StartupWithAnAbsentStoreTerminatesWithoutRegeneratingOrListening()
    {
        var root = Path.Combine(Path.GetTempPath(), "rackclick-mfa-l2i-proceso", Guid.NewGuid().ToString("N"), "instancias");
        try
        {
            var run = RunServer(new Dictionary<string, string?>
            {
                ["MfaKeyStore__Enabled"] = "true",
                ["MfaKeyStore__InstancesRoot"] = root,
                ["MfaKeyStore__InstallationId"] = Guid.NewGuid().ToString("D"),
            });

            Assert.Equal(1, run.ExitCode);
            Assert.Equal("mfa_keystore_store_missing", run.Error.Trim());
            Assert.False(Directory.Exists(root), "el arranque regeneró el almacén");
            Assert.DoesNotContain("listening", run.Output, StringComparison.OrdinalIgnoreCase);
        }
        finally
        {
            var parent = Path.GetDirectoryName(Path.GetDirectoryName(root)!)!;
            if (Directory.Exists(parent)) Directory.Delete(parent, true);
        }
    }

    // MFA-L2I-01: una raíz con NUL llega desde appsettings.json. El proceso debe salir con 1 y una sola línea de código, sin pila,
    // sin eco de la ruta y sin listener. La carpeta de configuración es propia de la prueba y se retira siempre.
    [Fact]
    public void StartupWithANulRootFromJsonTerminatesWithOneCodeLineAndNoStackOrPath()
    {
        var folder = Path.Combine(Path.GetTempPath(), "rackclick-mfa-l2i-json-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(folder);
        try
        {
            File.WriteAllText(Path.Combine(folder, "appsettings.json"), JsonSerializer.Serialize(new
            {
                MfaKeyStore = new
                {
                    Enabled = "true",
                    InstancesRoot = Path.Combine(Path.GetTempPath(), "rackclick-nul") + "\0cola",
                    InstallationId = Guid.NewGuid().ToString("D"),
                },
                PublicOrigin = Origin,
                ConnectionStrings = new { RackClick = "Host=127.0.0.1;Port=1;Database=rackclick_inexistente;Username=u;Password=p;Timeout=2" },
            }));

            var run = RunServer(new Dictionary<string, string?>(), "--contentRoot", folder);

            Assert.Equal(1, run.ExitCode);
            Assert.Equal("mfa_keystore_root_invalid", run.Error.Trim());
            Assert.DoesNotContain("   at ", run.Error + run.Output, StringComparison.Ordinal);
            Assert.DoesNotContain("rackclick-nul", run.Error + run.Output, StringComparison.Ordinal);
            Assert.DoesNotContain("listening", run.Output, StringComparison.OrdinalIgnoreCase);
        }
        finally
        {
            if (Directory.Exists(folder)) Directory.Delete(folder, true);
        }
    }

    // CLI con configuración MFA rota y origen no HTTPS: la migración conserva su contrato y no evalúa el proveedor.
    [Fact]
    public void MigrateKeepsItsContractWithBrokenMfaConfigurationAndNoHttpsOrigin()
    {
        var run = RunServer(new Dictionary<string, string?>
        {
            ["ConnectionStrings__RackClick"] = "Host=127.0.0.1;Port=1;Database=rackclick_inexistente;Username=u;Password=p;Timeout=2",
            ["PublicOrigin"] = "http://no-https.invalid",
            ["MfaKeyStore__Enabled"] = "true",
            ["MfaKeyStore__InstancesRoot"] = "instancias-relativas",
            ["MfaKeyStore__InstallationId"] = "no-es-un-uuid",
        }, "--migrate");

        Assert.Equal(1, run.ExitCode);
        Assert.Contains("Migration failed", run.Error, StringComparison.Ordinal);
        Assert.DoesNotContain("mfa_keystore", run.Error + run.Output, StringComparison.Ordinal);
        Assert.DoesNotContain("PublicOrigin", run.Error + run.Output, StringComparison.Ordinal);
    }

    // Ejecuta el servidor compilado (apphost del directorio de pruebas) con variables propias y sin entrada interactiva.
    private static ServerRun RunServer(IReadOnlyDictionary<string, string?> environment, params string[] arguments)
    {
        var apphost = Path.Combine(AppContext.BaseDirectory, "RackClick.Server.exe");
        Assert.True(File.Exists(apphost), "falta RackClick.Server.exe en la carpeta de pruebas");
        var start = new ProcessStartInfo(apphost)
        {
            RedirectStandardInput = true,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false,
            WorkingDirectory = AppContext.BaseDirectory,
        };
        foreach (var argument in arguments) start.ArgumentList.Add(argument);
        start.Environment["ASPNETCORE_ENVIRONMENT"] = "Production";
        start.Environment["PublicOrigin"] = Origin;
        start.Environment["ConnectionStrings__RackClick"] = "Host=127.0.0.1;Port=1;Database=rackclick_inexistente;Username=u;Password=p;Timeout=2";
        foreach (var (name, value) in environment)
        {
            if (value is null) start.Environment.Remove(name);
            else start.Environment[name] = value;
        }
        using var process = Process.Start(start) ?? throw new InvalidOperationException("no se pudo iniciar el servidor");
        process.StandardInput.Close();
        var output = process.StandardOutput.ReadToEndAsync();
        var error = process.StandardError.ReadToEndAsync();
        if (!process.WaitForExit(TimeSpan.FromSeconds(120)))
        {
            process.Kill(entireProcessTree: true);
            throw new InvalidOperationException("el servidor no terminó: posible listener abierto");
        }
        return new ServerRun(process.ExitCode, output.Result, error.Result);
    }

    private static string Cookie(HttpResponseMessage response, string name)
    {
        foreach (var value in response.Headers.GetValues("Set-Cookie"))
            if (value.StartsWith(name + "=", StringComparison.Ordinal)) return value.Split(';')[0];
        throw new InvalidOperationException("sin Set-Cookie " + name);
    }

    private sealed record ServerRun(int ExitCode, string Output, string Error);

    // Identidad de prueba del host: lector Usuarios y confianza Usuario de laboratorio, SYSTEM y Administradores.
    private sealed class TestIdentity(SecurityIdentifier reader, SecurityIdentifier[] trusted) : IMfaHostIdentity
    {
        public SecurityIdentifier? ReaderSid => reader;

        public IReadOnlyCollection<SecurityIdentifier> TrustedPrincipals => trusted;

        public string Description => "prueba-inyectada";
    }

    // Almacén TEMP sintético con versión 1 retirada y versión 7 activa, creado con el escritor aprobado.
    private sealed class HostStore : IDisposable
    {
        private readonly Dictionary<int, byte[]> _keys = new();

        private HostStore(string folder, Guid installation)
        {
            Folder = folder;
            Installation = installation;
        }

        public string Folder { get; }

        public string Root => Path.Combine(Folder, "instancias");

        public Guid Installation { get; }

        public SecurityIdentifier[] Trusted { get; private set; } = [];

        public string KeyFile(int version) =>
            Path.Combine(Root, Installation.ToString("D"), WindowsMfaKeyProvider.KeysFolderName, MfaKeyRing.KeyFileName(version));

        public static HostStore Create()
        {
            var me = WindowsIdentity.GetCurrent().User ?? throw new InvalidOperationException("sin SID de usuario");
            var folder = Path.Combine(Path.GetTempPath(), "rackclick-mfa-l2i-http", Guid.NewGuid().ToString("N"));
            Directory.CreateDirectory(folder);
            var store = new HostStore(folder, Guid.NewGuid()) { Trusted = [me, LocalSystemSid, AdministratorsSid] };
            store._keys[RetiredVersion] = RandomNumberGenerator.GetBytes(MfaKeyRing.KeyBytes);
            store._keys[ActiveVersion] = RandomNumberGenerator.GetBytes(MfaKeyRing.KeyBytes);
            var ring = Encoding.UTF8.GetBytes(MfaKeyJson.Ring(store.Installation,
                MfaKeyJson.Entry(RetiredVersion, "retired", "2026-10-01T08:30:00Z") + "," +
                MfaKeyJson.Entry(ActiveVersion, "active", "2026-10-25T10:00:00Z")));
            var keys = new List<(int Version, byte[] Key)>
            {
                (RetiredVersion, store._keys[RetiredVersion]),
                (ActiveVersion, store._keys[ActiveVersion]),
            };
            WindowsMfaKeyStoreWriter.CreateStoreFromMaterial(store.Root, store.Installation, UsersSid, store.Trusted, ring, keys);
            return store;
        }

        public void Dispose()
        {
            if (Directory.Exists(Folder)) Directory.Delete(Folder, true);
            var parent = Path.GetDirectoryName(Folder)!;
            if (Directory.Exists(parent) && !Directory.EnumerateFileSystemEntries(parent).Any())
                Directory.Delete(parent);
        }
    }

    // Host de pruebas: base temporal, migraciones reales y composición del proveedor desde MfaKeyStore:*. Sólo la identidad es de prueba.
    private sealed class Harness : IAsyncDisposable
    {
        private readonly string _database;
        private readonly string _admin;
        private readonly HostStore _store;
        private readonly string? _previousConnection;
        private readonly string? _previousOrigin;
        private WebApplicationFactory<Program>? _factory;
        private HttpClient? _client;
        private NpgsqlDataSource? _source;
        private bool _disposed;

        private Harness(string database, string admin, HostStore store)
        {
            _database = database;
            _admin = admin;
            _store = store;
            _previousConnection = Environment.GetEnvironmentVariable("ConnectionStrings__RackClick");
            _previousOrigin = Environment.GetEnvironmentVariable("PublicOrigin");
        }

        public static async Task<Harness> CreateAsync(HostStore store)
        {
            var admin = Environment.GetEnvironmentVariable(AdminVariable);
            Assert.SkipWhen(string.IsNullOrWhiteSpace(admin), AdminVariable + " no está definido: prueba PostgreSQL omitida.");
            var database = "rc_mfa_host_" + Guid.NewGuid().ToString("N");
            await using (var connection = new NpgsqlConnection(admin))
            {
                await connection.OpenAsync();
                await using var create = new NpgsqlCommand($"CREATE DATABASE {database} ENCODING 'UTF8' TEMPLATE template0", connection);
                await create.ExecuteNonQueryAsync();
            }
            var harness = new Harness(database, admin!, store);
            await harness.ApplyMigrationsAsync();
            return harness;
        }

        private string DatabaseConnection()
        {
            var builder = new NpgsqlConnectionStringBuilder(_admin) { Database = _database };
            return builder.ConnectionString;
        }

        private NpgsqlDataSource Source() => _source ??= NpgsqlDataSource.Create(DatabaseConnection());

        private HttpClient Client()
        {
            if (_client is not null) return _client;
            Environment.SetEnvironmentVariable("ConnectionStrings__RackClick", DatabaseConnection());
            Environment.SetEnvironmentVariable("PublicOrigin", Origin);
            var store = _store;
            _factory = new WebApplicationFactory<Program>().WithWebHostBuilder(builder =>
            {
                builder.UseSetting("MfaKeyStore:Enabled", "true");
                builder.UseSetting("MfaKeyStore:InstancesRoot", store.Root);
                builder.UseSetting("MfaKeyStore:InstallationId", store.Installation.ToString("D"));
                builder.ConfigureTestServices(services => services.AddSingleton<IMfaHostIdentity>(
                    new TestIdentity(UsersSid, store.Trusted)));
            });
            _client = _factory.CreateClient(new WebApplicationFactoryClientOptions { BaseAddress = new Uri(Origin + "/"), HandleCookies = false });
            return _client;
        }

        public async Task CreateUserAsync()
        {
            var systemhaus = await SystemhausAsync();
            var user = Guid.NewGuid();
            await ExecuteAsync(
                "INSERT INTO app_user(id,systemhaus_id,username,password_hash) VALUES(@user,@sh,@name,@hash)",
                ("user", user), ("sh", systemhaus), ("name", UserName), ("hash", Secrets.PasswordHash(UserName, Password)));
            await ExecuteAsync(
                "INSERT INTO app_mfa_user(systemhaus_id,user_id,mfa_required) VALUES(@sh,@user,true)",
                ("sh", systemhaus), ("user", user));
        }

        private async Task<Guid> SystemhausAsync()
        {
            await using var connection = await Source().OpenConnectionAsync(TestContext.Current.CancellationToken);
            await using (var read = new NpgsqlCommand("SELECT id FROM systemhaus LIMIT 1", connection))
                if (await read.ExecuteScalarAsync(TestContext.Current.CancellationToken) is Guid existing) return existing;
            var id = Guid.NewGuid();
            await using var insert = new NpgsqlCommand("INSERT INTO systemhaus(id,name) VALUES(@sh,'Lab MFA host')", connection);
            insert.Parameters.AddWithValue("sh", id);
            await insert.ExecuteNonQueryAsync(TestContext.Current.CancellationToken);
            return id;
        }

        public async Task<HttpResponseMessage> Post(string path, object? body, string? cookie = null, string? csrf = null)
        {
            var request = new HttpRequestMessage(HttpMethod.Post, path)
            {
                Content = body is null ? new StringContent("{}", Encoding.UTF8, "application/json") : JsonContent.Create(body),
            };
            request.Headers.TryAddWithoutValidation("Origin", Origin);
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

        public async Task<int> ScalarIntAsync(string sql)
        {
            await using var connection = await Source().OpenConnectionAsync(TestContext.Current.CancellationToken);
            await using var command = new NpgsqlCommand(sql, connection);
            return Convert.ToInt32(await command.ExecuteScalarAsync(TestContext.Current.CancellationToken) ?? 0);
        }

        public async Task<string> ScalarTextAsync(string sql)
        {
            await using var connection = await Source().OpenConnectionAsync(TestContext.Current.CancellationToken);
            await using var command = new NpgsqlCommand(sql, connection);
            return (string)(await command.ExecuteScalarAsync(TestContext.Current.CancellationToken) ?? "");
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
            // Exercise the real current migration/history contract. The old hand-written
            // 001..015 subset left schema_migration empty and cannot describe a current host.
            await using var connection = await Source().OpenConnectionAsync(TestContext.Current.CancellationToken);
            await using var transaction = await connection.BeginTransactionAsync(TestContext.Current.CancellationToken);
            await SchemaMigrations.Apply(connection, transaction, TestContext.Current.CancellationToken);
            await transaction.CommitAsync(TestContext.Current.CancellationToken);
        }

        // Idempotente. Cierra el host, retira la base temporal y restaura las variables de entorno.
        public async ValueTask DisposeAsync()
        {
            if (_disposed) return;
            _disposed = true;
            try
            {
                _client?.Dispose();
                if (_factory is not null) await _factory.DisposeAsync();
                _source?.Dispose();
                NpgsqlConnection.ClearAllPools();
                await using var connection = new NpgsqlConnection(_admin);
                await connection.OpenAsync();
                await using var drop = new NpgsqlCommand($"DROP DATABASE IF EXISTS {_database} WITH (FORCE)", connection);
                await drop.ExecuteNonQueryAsync();
            }
            finally
            {
                try { Environment.SetEnvironmentVariable("ConnectionStrings__RackClick", _previousConnection); }
                finally { Environment.SetEnvironmentVariable("PublicOrigin", _previousOrigin); }
            }
        }
    }
}
