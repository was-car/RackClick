using System.Runtime.Versioning;
using System.Security.Cryptography;
using System.Security.Principal;
using System.Text;
using Npgsql;
using OtpNet;
using RackClick.Domain;
using RackClick.Server;
using Xunit;

namespace RackClick.Quality.Tests;

// Versión activa del anillo para nuevos enrolamientos (MFA-L2h). Almacén TEMP sintético con dos versiones (1 retirada y 7 activa),
// proveedor Windows real (lector y DPAPI aprobados) y PostgreSQL 17 de laboratorio (RACKCLICK_TEST_PG_ADMIN). Se ejecutan sólo con
// ese servidor. Mismo token y máquina de laboratorio: no es la identidad efectiva del servicio ni prueba de portabilidad DPAPI.
// Los fixtures declaran al usuario de laboratorio como principal de confianza; no es una excepción de producción.
[SupportedOSPlatform("windows")]
public sealed class MfaActiveKeyTests
{
    private const string AdminVariable = "RACKCLICK_TEST_PG_ADMIN";
    private const string EnrollUser = "usuario-enrolamiento-activa";
    private const string VerifyUser = "usuario-factor-retirado";
    private static readonly string Password = "RcTest-" + Convert.ToHexString(System.Security.Cryptography.RandomNumberGenerator.GetBytes(24));
    private const int RetiredVersion = 1;
    private const int ActiveVersion = 7;

    private static readonly SecurityIdentifier UsersSid = new(WellKnownSidType.BuiltinUsersSid, null);
    private static readonly SecurityIdentifier LocalSystemSid = new(WellKnownSidType.LocalSystemSid, null);
    private static readonly SecurityIdentifier AdministratorsSid = new(WellKnownSidType.BuiltinAdministratorsSid, null);

    [Fact]
    public void ActiveKeyIsTheSingleActiveVersionAndReturnsAnIndependentCopy()
    {
        using var store = KeyStore.Create();
        var provider = store.Provider();
        var before = store.MaterialBytes();

        var first = provider.GetActiveKey();
        var second = provider.GetActiveKey();

        Assert.Equal(ActiveVersion, first.Version);
        Assert.Equal(ActiveVersion, second.Version);
        Assert.True(CryptographicOperations.FixedTimeEquals(store.KeyOf(ActiveVersion), first.Key), "la clave activa no coincide");
        Assert.True(CryptographicOperations.FixedTimeEquals(first.Key, second.Key), "dos lecturas dan claves distintas");
        Assert.False(ReferenceEquals(first.Key, second.Key), "el proveedor devolvió el mismo arreglo dos veces");
        CryptographicOperations.ZeroMemory(first.Key);
        Assert.True(CryptographicOperations.FixedTimeEquals(store.KeyOf(ActiveVersion), second.Key),
            "poner a cero una copia alteró la otra");
        CryptographicOperations.ZeroMemory(second.Key);
        Assert.True(CryptographicOperations.FixedTimeEquals(before, store.MaterialBytes()), "el almacén cambió al leer la clave activa");
    }

    [Fact]
    public void RetiredVersionStaysReadableForItsExistingFactors()
    {
        using var store = KeyStore.Create();

        var retired = store.Provider().GetKey(RetiredVersion);

        Assert.True(CryptographicOperations.FixedTimeEquals(store.KeyOf(RetiredVersion), retired), "la versión retirada no coincide");
        CryptographicOperations.ZeroMemory(retired);
    }

    [Theory]
    [InlineData("anillo-invalido", MfaKeyRingErrorKind.InvalidFormat)]
    [InlineData("activa-ausente", MfaKeyRingErrorKind.MissingFile)]
    [InlineData("activa-corrupta", MfaKeyRingErrorKind.InvalidFormat)]
    public void ActiveKeyFailuresAreExplicitAndNeverFallBackToVersionOne(string shape, MfaKeyRingErrorKind expected)
    {
        using var store = KeyStore.Create();
        store.Damage(shape);
        var provider = store.Provider();

        var error = Assert.Throws<MfaKeyRingException>(() => { provider.GetActiveKey(); });

        Assert.Equal(expected, error.Kind);
        if (shape == "activa-ausente")
        {
            // La versión 1 sigue existiendo en el almacén: el fallo no debe sustituirse por ella.
            var fallback = provider.GetKey(RetiredVersion);
            Assert.True(CryptographicOperations.FixedTimeEquals(store.KeyOf(RetiredVersion), fallback));
            CryptographicOperations.ZeroMemory(fallback);
        }
    }

    [Fact]
    public async Task StartEnrollmentStoresTheActiveVersionAndTheFactorOpensOnlyWithItsKey()
    {
        using var store = KeyStore.Create();
        await using var env = await ActiveKeyDatabase.CreateAsync();
        await env.CreateUserAsync(EnrollUser, withFactor: false);
        var ct = TestContext.Current.CancellationToken;
        var provider = store.Provider();
        var (token, csrf) = await env.EnrollChallengeAsync(env.Store());

        var start = await env.Enrollment(provider).StartEnrollment(token, csrf, ct);

        Assert.Equal("pending", await env.ScalarTextAsync("SELECT state FROM app_mfa_factor"));
        Assert.Equal(ActiveVersion, await env.ScalarIntAsync("SELECT key_version FROM app_mfa_factor"));
        var sealedSecret = await env.ScalarBytesAsync("SELECT secret_ciphertext FROM app_mfa_factor");
        var systemhaus = await env.SystemhausIdAsync();
        var user = await env.UserIdAsync(EnrollUser);
        var secret = Base32Encoding.ToBytes(start.SecretBase32);

        Assert.True(CryptographicOperations.FixedTimeEquals(secret,
            MfaSecretCipher.Open(store.KeyOf(ActiveVersion), ActiveVersion, sealedSecret, systemhaus, user)),
            "el factor no abre con la clave de la versión activa");
        Assert.ThrowsAny<CryptographicException>(() =>
        {
            _ = MfaSecretCipher.Open(store.KeyOf(RetiredVersion), ActiveVersion, sealedSecret, systemhaus, user);
        });
        Assert.ThrowsAny<CryptographicException>(() =>
        {
            _ = MfaSecretCipher.Open(store.KeyOf(ActiveVersion), RetiredVersion, sealedSecret, systemhaus, user);
        });

        var code = MfaTotp.Compute(secret, DateTimeOffset.UtcNow);
        var (sessionToken, sessionCsrf) = await env.Enrollment(provider).ConfirmEnrollment(token, code, csrf, ct);

        Assert.False(string.IsNullOrEmpty(sessionToken));
        Assert.False(string.IsNullOrEmpty(sessionCsrf));
        Assert.Equal("active", await env.ScalarTextAsync("SELECT state FROM app_mfa_factor"));
        Assert.Equal(ActiveVersion, await env.ScalarIntAsync("SELECT key_version FROM app_mfa_factor"));
        Assert.Equal(1, await env.CountAsync("SELECT count(*) FROM app_session"));
    }

    [Fact]
    public async Task FactorOfTheRetiredVersionVerifiesByItsStoredVersionWithoutResealing()
    {
        using var store = KeyStore.Create();
        await using var env = await ActiveKeyDatabase.CreateAsync();
        await env.CreateUserAsync(VerifyUser, withFactor: true, factorVersion: RetiredVersion, factorKey: store.KeyOf(RetiredVersion));
        var ct = TestContext.Current.CancellationToken;
        var provider = store.Provider();
        var before = await env.ScalarBytesAsync("SELECT secret_ciphertext FROM app_mfa_factor");

        var verify = (await env.Store().AuthenticateForLogin(VerifyUser, Password, ct)).Challenge!.Value;
        var code = MfaTotp.Compute(env.SecretOf(VerifyUser), DateTimeOffset.UtcNow);
        var (sessionToken, _) = await env.Verifier(provider).CompleteVerify(verify.Token, code, verify.Csrf, ct);

        Assert.False(string.IsNullOrEmpty(sessionToken));
        Assert.Equal(RetiredVersion, await env.ScalarIntAsync("SELECT key_version FROM app_mfa_factor"));
        var after = await env.ScalarBytesAsync("SELECT secret_ciphertext FROM app_mfa_factor");
        Assert.True(CryptographicOperations.FixedTimeEquals(before, after),
            "el inicio de sesión volvió a cifrar el factor de una versión retirada");
    }

    [Theory]
    [InlineData("anillo-invalido")]
    [InlineData("activa-ausente")]
    [InlineData("activa-corrupta")]
    [InlineData("proveedor-error")]
    public async Task ActiveKeyFailureLeavesNoFactorNoSessionAndNoPartialCommit(string shape)
    {
        using var store = KeyStore.Create();
        await using var env = await ActiveKeyDatabase.CreateAsync();
        await env.CreateUserAsync(EnrollUser, withFactor: false);
        var ct = TestContext.Current.CancellationToken;
        var (token, csrf) = await env.EnrollChallengeAsync(env.Store());
        IMfaKeyProvider provider;
        if (shape == "proveedor-error")
        {
            provider = new FailingProvider(store.Provider());
            await Assert.ThrowsAsync<InvalidOperationException>(() => env.Enrollment(provider).StartEnrollment(token, csrf, ct));
        }
        else
        {
            store.Damage(shape);
            provider = store.Provider();
            await Assert.ThrowsAsync<MfaKeyRingException>(() => env.Enrollment(provider).StartEnrollment(token, csrf, ct));
        }

        Assert.Equal(0, await env.CountAsync("SELECT count(*) FROM app_mfa_factor"));
        Assert.Equal(0, await env.CountAsync("SELECT count(*) FROM app_session"));
        Assert.Equal(0, await env.CountAsync("SELECT count(*) FROM app_mfa_factor WHERE key_version=1"));
        Assert.Equal(1, await env.CountAsync("SELECT count(*) FROM app_mfa_challenge WHERE purpose='enroll' AND consumed_at IS NULL"));
    }

    [Fact]
    public async Task EnrollmentZeroesItsOwnCopyAndLeavesTheProviderMaterialIntact()
    {
        using var store = KeyStore.Create();
        await using var env = await ActiveKeyDatabase.CreateAsync();
        await env.CreateUserAsync(EnrollUser, withFactor: false);
        var ct = TestContext.Current.CancellationToken;
        var (token, csrf) = await env.EnrollChallengeAsync(env.Store());
        var recording = new RecordingProvider(store.Provider());

        await env.Enrollment(recording).StartEnrollment(token, csrf, ct);

        Assert.NotNull(recording.Returned);
        Assert.True(recording.Returned!.All(b => b == 0), "la copia recibida por el enrolamiento no se puso a cero");
        var again = store.Provider().GetActiveKey();
        Assert.True(CryptographicOperations.FixedTimeEquals(store.KeyOf(ActiveVersion), again.Key),
            "el material del proveedor cambió tras el enrolamiento");
        CryptographicOperations.ZeroMemory(again.Key);
    }

    // Proveedor que falla al pedir la activa: el enrolamiento debe fallar sin escribir nada.
    private sealed class FailingProvider(IMfaKeyProvider inner) : IMfaKeyProvider
    {
        public byte[] GetKey(int version) => inner.GetKey(version);

        public (int Version, byte[] Key) GetActiveKey() => throw new InvalidOperationException("fallo simulado del proveedor");
    }

    // Guarda la copia devuelta al enrolamiento para comprobar que se pone a cero después de usarla.
    private sealed class RecordingProvider(IMfaKeyProvider inner) : IMfaKeyProvider
    {
        public byte[]? Returned { get; private set; }

        public byte[] GetKey(int version) => inner.GetKey(version);

        public (int Version, byte[] Key) GetActiveKey()
        {
            var active = inner.GetActiveKey();
            Returned = active.Key;
            return active;
        }
    }

    // Almacén TEMP sintético: versión 1 retirada y versión 7 activa. Las claves son nuevas y sólo viven en memoria de la prueba.
    private sealed class KeyStore : IDisposable
    {
        private readonly Dictionary<int, byte[]> _keys = new();
        private readonly string _folder;
        private readonly string _root;
        private readonly Guid _installation;

        private KeyStore(string folder, string root, Guid installation, SecurityIdentifier[] trusted)
        {
            _folder = folder;
            _root = root;
            _installation = installation;
            Trusted = trusted;
        }

        public SecurityIdentifier[] Trusted { get; }

        public static KeyStore Create()
        {
            var me = WindowsIdentity.GetCurrent().User ?? throw new InvalidOperationException("sin SID de usuario");
            var folder = Path.Combine(Path.GetTempPath(), "rackclick-mfa-l2h", Guid.NewGuid().ToString("N"));
            var root = Path.Combine(folder, "instancias");
            Directory.CreateDirectory(folder);
            var installation = Guid.NewGuid();
            var store = new KeyStore(folder, root, installation, [me, LocalSystemSid, AdministratorsSid]);
            store._keys[RetiredVersion] = RandomNumberGenerator.GetBytes(MfaKeyRing.KeyBytes);
            store._keys[ActiveVersion] = RandomNumberGenerator.GetBytes(MfaKeyRing.KeyBytes);
            var ring = Encoding.UTF8.GetBytes(MfaKeyJson.Ring(installation,
                MfaKeyJson.Entry(RetiredVersion, "retired", "2026-10-01T08:30:00Z") + "," +
                MfaKeyJson.Entry(ActiveVersion, "active", "2026-10-25T10:00:00Z")));
            var keys = new List<(int Version, byte[] Key)>
            {
                (RetiredVersion, store._keys[RetiredVersion]),
                (ActiveVersion, store._keys[ActiveVersion]),
            };
            WindowsMfaKeyStoreWriter.CreateStoreFromMaterial(root, installation, UsersSid, store.Trusted, ring, keys);
            return store;
        }

        public WindowsMfaKeyProvider Provider() => new(_root, _installation, UsersSid, Trusted);

        // Clave original de la prueba. No debe ponerse a cero: la usan las comprobaciones.
        public byte[] KeyOf(int version) => _keys[version];

        public string RingPath => Path.Combine(KeysFolder, MfaKeyRing.RingFileName);

        public string KeyFile(int version) => Path.Combine(KeysFolder, MfaKeyRing.KeyFileName(version));

        private string KeysFolder => Path.Combine(_root, _installation.ToString("D"), WindowsMfaKeyProvider.KeysFolderName);

        // Bytes del anillo y de sus archivos de clave (blobs protegidos, nunca claves en claro).
        public byte[] MaterialBytes()
        {
            var bytes = new List<byte>();
            foreach (var path in new[] { RingPath, KeyFile(RetiredVersion), KeyFile(ActiveVersion) })
                bytes.AddRange(File.ReadAllBytes(path));
            return bytes.ToArray();
        }

        // Daños controlados del almacén recién creado, sólo dentro de la carpeta TEMP de la prueba.
        public void Damage(string shape)
        {
            switch (shape)
            {
                case "anillo-invalido":
                    File.WriteAllBytes(RingPath, Encoding.UTF8.GetBytes("{\"format\":"));
                    break;
                case "activa-ausente":
                    File.Delete(KeyFile(ActiveVersion));
                    break;
                case "activa-corrupta":
                    File.WriteAllBytes(KeyFile(ActiveVersion), Encoding.UTF8.GetBytes("{no-es-json"));
                    break;
                default:
                    throw new ArgumentOutOfRangeException(nameof(shape), shape, null);
            }
        }

        public void Dispose()
        {
            if (Directory.Exists(_folder)) Directory.Delete(_folder, true);
            // La carpeta padre compartida sólo se retira si ya no contiene nada de otras pruebas.
            var parent = Path.GetDirectoryName(_folder)!;
            if (Directory.Exists(parent) && !Directory.EnumerateFileSystemEntries(parent).Any())
                Directory.Delete(parent);
        }
    }

    // Base PostgreSQL 17 propia de la prueba: migraciones 001–015 y limpieza al final, igual que MfaEnrollmentTests.
    private sealed class ActiveKeyDatabase : IAsyncDisposable
    {
        private readonly string _database;
        private readonly string _adminConnection;
        private NpgsqlDataSource? _source;
        private readonly Dictionary<string, byte[]> _secrets = new();

        private ActiveKeyDatabase(string database, string adminConnection)
        {
            _database = database;
            _adminConnection = adminConnection;
        }

        public static async Task<ActiveKeyDatabase> CreateAsync()
        {
            var admin = Environment.GetEnvironmentVariable(AdminVariable);
            Assert.SkipWhen(string.IsNullOrWhiteSpace(admin), AdminVariable + " no está definido: prueba PostgreSQL omitida.");
            var database = "rc_mfa_activa_" + Guid.NewGuid().ToString("N");
            await using (var connection = new NpgsqlConnection(admin))
            {
                await connection.OpenAsync();
                await using var create = new NpgsqlCommand($"CREATE DATABASE {database} ENCODING 'UTF8' TEMPLATE template0", connection);
                await create.ExecuteNonQueryAsync();
            }
            var environment = new ActiveKeyDatabase(database, admin!);
            await environment.ApplyMigrationsAsync();
            return environment;
        }

        public NpgsqlDataSource Source()
        {
            if (_source is not null) return _source;
            var builder = new NpgsqlConnectionStringBuilder(_adminConnection) { Database = _database };
            _source = NpgsqlDataSource.Create(builder.ConnectionString);
            return _source;
        }

        public PostgresStore Store() => new(Source()) { MfaAvailable = true };

        public MfaStore Enrollment(IMfaKeyProvider provider) => new(Source(), provider);

        public MfaStore Verifier(IMfaKeyProvider provider) => new(Source(), provider);

        public byte[] SecretOf(string username) => _secrets[username];

        // Login real con contraseña válida: emite el desafío de enrolamiento restringido.
        public async Task<(string Token, string Csrf)> EnrollChallengeAsync(PostgresStore store)
        {
            var outcome = await store.AuthenticateForLogin(EnrollUser, Password, TestContext.Current.CancellationToken);
            var challenge = outcome.Challenge ?? throw new InvalidOperationException("el login no emitió desafío de enrolamiento");
            return (challenge.Token, challenge.Csrf);
        }

        // Usuario con contraseña y MFA obligatorio. Con factor, se cifra con la versión y la clave indicadas.
        public async Task CreateUserAsync(string username, bool withFactor, int factorVersion = 0, byte[]? factorKey = null)
        {
            var systemhaus = await SystemhausAsync();
            var user = Guid.NewGuid();
            var secret = MfaTotp.NewSecret();
            _secrets[username] = secret;
            await ExecuteAsync(
                "INSERT INTO app_user(id,systemhaus_id,username,password_hash) VALUES(@user,@sh,@name,@hash)",
                ("user", user), ("sh", systemhaus), ("name", username), ("hash", Secrets.PasswordHash(username, Password)));
            await ExecuteAsync(
                "INSERT INTO app_mfa_user(systemhaus_id,user_id,mfa_required) VALUES(@sh,@user,true)",
                ("sh", systemhaus), ("user", user));
            if (withFactor)
            {
                ArgumentNullException.ThrowIfNull(factorKey);
                var sealedSecret = MfaSecretCipher.Seal(factorKey, factorVersion, secret, systemhaus, user);
                await ExecuteAsync(
                    "INSERT INTO app_mfa_factor(systemhaus_id,user_id,state,secret_ciphertext,key_version,confirmed_at) VALUES(@sh,@user,'active',@cipher,@version,now())",
                    ("sh", systemhaus), ("user", user), ("cipher", sealedSecret), ("version", factorVersion));
            }
        }

        public async Task<Guid> SystemhausIdAsync()
        {
            await using var connection = await Source().OpenConnectionAsync(TestContext.Current.CancellationToken);
            await using var command = new NpgsqlCommand("SELECT id FROM systemhaus LIMIT 1", connection);
            return (Guid)(await command.ExecuteScalarAsync(TestContext.Current.CancellationToken) ?? Guid.Empty);
        }

        public async Task<Guid> UserIdAsync(string username)
        {
            await using var connection = await Source().OpenConnectionAsync(TestContext.Current.CancellationToken);
            await using var command = new NpgsqlCommand("SELECT id FROM app_user WHERE username=@name", connection);
            command.Parameters.AddWithValue("name", username);
            return (Guid)(await command.ExecuteScalarAsync(TestContext.Current.CancellationToken) ?? Guid.Empty);
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

        public async Task<byte[]> ScalarBytesAsync(string sql)
        {
            await using var connection = await Source().OpenConnectionAsync(TestContext.Current.CancellationToken);
            await using var command = new NpgsqlCommand(sql, connection);
            return (byte[])(await command.ExecuteScalarAsync(TestContext.Current.CancellationToken) ?? Array.Empty<byte>());
        }

        public async Task ExecuteAsync(string sql, params (string Name, object Value)[] values)
        {
            await using var connection = await Source().OpenConnectionAsync(TestContext.Current.CancellationToken);
            await using var command = new NpgsqlCommand(sql, connection);
            foreach (var (name, value) in values) command.Parameters.AddWithValue(name, value);
            await command.ExecuteNonQueryAsync(TestContext.Current.CancellationToken);
        }

        // Una instalación tiene un solo systemhaus (restricción one_systemhaus_per_installation): se reutiliza el existente.
        private async Task<Guid> SystemhausAsync()
        {
            await using var connection = await Source().OpenConnectionAsync(TestContext.Current.CancellationToken);
            await using (var read = new NpgsqlCommand("SELECT id FROM systemhaus LIMIT 1", connection))
            {
                if (await read.ExecuteScalarAsync(TestContext.Current.CancellationToken) is Guid existing) return existing;
            }
            var id = Guid.NewGuid();
            await using var insert = new NpgsqlCommand("INSERT INTO systemhaus(id,name) VALUES(@sh,'Lab MFA activa')", connection);
            insert.Parameters.AddWithValue("sh", id);
            await insert.ExecuteNonQueryAsync(TestContext.Current.CancellationToken);
            return id;
        }

        public async ValueTask DisposeAsync()
        {
            _source?.Dispose();
            NpgsqlConnection.ClearAllPools();
            await using var connection = new NpgsqlConnection(_adminConnection);
            await connection.OpenAsync();
            await using var drop = new NpgsqlCommand($"DROP DATABASE IF EXISTS {_database} WITH (FORCE)", connection);
            await drop.ExecuteNonQueryAsync();
        }

        private async Task ApplyMigrationsAsync()
        {
            var folder = Path.Combine(AppContext.BaseDirectory, "database");
            var files = new List<string>();
            foreach (var name in new[]
            {
                "001-foundation.sql", "002-inventory.sql", "003-operation-cancellation.sql", "004-session-identity.sql",
                "005-audit-context.sql", "006-audit-state-intent.sql", "007-audit-context-families.sql",
                "008-user-catalog-favorites.sql", "009-private-device-templates.sql", "010-customer-shared-device-templates.sql",
                "011-user-preferences.sql", "012-user-port-colors.sql", "013-user-category-colors.sql", "014-mfa.sql", "015-mfa-account-policy.sql",
            })
                files.Add(Path.Combine(folder, name));
            await using var connection = await Source().OpenConnectionAsync(TestContext.Current.CancellationToken);
            foreach (var file in files)
            {
                await using var command = new NpgsqlCommand(await File.ReadAllTextAsync(file, TestContext.Current.CancellationToken), connection);
                await command.ExecuteNonQueryAsync(TestContext.Current.CancellationToken);
            }
        }
    }
}
