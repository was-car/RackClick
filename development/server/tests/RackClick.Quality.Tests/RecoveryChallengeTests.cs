using Microsoft.Extensions.Configuration;
using Npgsql;
using RackClick.Server;
using Xunit;

namespace RackClick.Quality.Tests;

// Recuperación local (`--recover-admin`) con desafíos MFA pendientes. Se ejecuta solo si RACKCLICK_TEST_PG_ADMIN apunta
// a un servidor de laboratorio con rol que pueda crear bases y roles. Cada prueba crea su propia base y su rol propietario.
public sealed class RecoveryChallengeTests
{
    private const string AdminVariable = "RACKCLICK_TEST_PG_ADMIN";
    private const string BackupSha256 = "4f2c9b1d7e0a3c58f6b2d9e41a7c05839d6f2b1e8a4c7d0f35b9e2a6c18d4f7b";
    private const string RecoveryUser = "Recuperacion Prueba";
    private static readonly string AppPassword = "RcTest-" + Convert.ToHexString(System.Security.Cryptography.RandomNumberGenerator.GetBytes(24));

    [Fact]
    public async Task Recovery_consumes_pending_enroll_and_verify_challenges_together_with_sessions()
    {
        await using var fixture = await RecoveryFixture.CreateAsync();
        await fixture.SeedPendingStateAsync();
        var output = new StringWriter();

        int code = await RecoveryAdministrator.Run(fixture.Configuration(), new StringReader(AppPassword + "\n"), output, TestContext.Current.CancellationToken);

        Assert.Equal(0, code);
        Assert.Contains("createdUserId", output.ToString());
        Assert.DoesNotContain("failed", output.ToString());
        Assert.Equal(0, await fixture.CountAsync("SELECT count(*) FROM app_session"));
        Assert.Equal(0, await fixture.CountAsync("SELECT count(*) FROM app_mfa_challenge WHERE consumed_at IS NULL"));
        Assert.Equal(2, await fixture.CountAsync("SELECT count(*) FROM app_mfa_challenge WHERE consumed_at IS NOT NULL"));
        Assert.Equal(1, await fixture.CountAsync("SELECT count(*) FROM audit_event WHERE action='deployment.recover'"));
        Assert.Equal("2", await fixture.ScalarTextAsync("SELECT after_json->>'revokedChallenges' FROM audit_event WHERE action='deployment.recover'"));
        Assert.Equal(2, await fixture.CountAsync("SELECT count(*) FROM app_user"));
    }

    [Fact]
    public async Task Failed_recovery_rolls_back_challenges_sessions_marker_and_user_together()
    {
        await using var fixture = await RecoveryFixture.CreateAsync();
        await fixture.SeedPendingStateAsync();
        // Fallo forzado después de consumir desafíos y revocar sesiones, justo al insertar la auditoría.
        await fixture.ExecuteAsync("""
            CREATE FUNCTION fail_recovery_audit() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN RAISE EXCEPTION 'forced_recovery_failure'; END $$
            """);
        await fixture.ExecuteAsync("CREATE TRIGGER fail_recovery_audit BEFORE INSERT ON audit_event FOR EACH ROW EXECUTE FUNCTION fail_recovery_audit()");
        var output = new StringWriter();

        int code = await RecoveryAdministrator.Run(fixture.Configuration(), new StringReader(AppPassword + "\n"), output, TestContext.Current.CancellationToken);

        Assert.Equal(1, code);
        Assert.Contains("failed", output.ToString());
        Assert.Equal(1, await fixture.CountAsync("SELECT count(*) FROM app_session"));
        Assert.Equal(2, await fixture.CountAsync("SELECT count(*) FROM app_mfa_challenge WHERE consumed_at IS NULL"));
        Assert.Equal(1, await fixture.CountAsync("SELECT count(*) FROM app_user"));
        Assert.Equal(fixture.Marker, await fixture.ScalarTextAsync("SELECT shobj_description(oid,'pg_database') FROM pg_database WHERE datname=current_database()"));
    }

    // Base, rol propietario y migraciones reales (001–014) aplicadas con el migrador del servidor, para que el historial
    // y los digests de schema_migration sean los que exige la recuperación.
    private sealed class RecoveryFixture : IAsyncDisposable
    {
        private readonly string _admin;
        private readonly Guid _instanceId;
        private readonly string _owner;
        private readonly string _password;
        private NpgsqlDataSource? _source;

        private RecoveryFixture(string admin, Guid instanceId, string password)
        {
            _admin = admin;
            _instanceId = instanceId;
            _owner = "rc_owner_" + instanceId.ToString("N");
            _password = password;
            Database = "rc_db_" + instanceId.ToString("N");
        }

        public string Database { get; }
        public string Marker => $"RackClickRecoveryPending:{_instanceId:D}:{BackupSha256}";

        public static async Task<RecoveryFixture> CreateAsync()
        {
            var admin = Environment.GetEnvironmentVariable(AdminVariable);
            Assert.SkipWhen(string.IsNullOrWhiteSpace(admin), AdminVariable + " no está definido: prueba PostgreSQL omitida.");
            var fixture = new RecoveryFixture(admin!, Guid.NewGuid(), Guid.NewGuid().ToString("N") + "Aa1");
            await using (var connection = new NpgsqlConnection(admin))
            {
                await connection.OpenAsync(TestContext.Current.CancellationToken);
                await using (var role = new NpgsqlCommand($"CREATE ROLE {fixture._owner} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD '{fixture._password}'", connection))
                    await role.ExecuteNonQueryAsync(TestContext.Current.CancellationToken);
                await using (var database = new NpgsqlCommand($"CREATE DATABASE {fixture.Database} OWNER {fixture._owner} ENCODING 'UTF8' TEMPLATE template0", connection))
                    await database.ExecuteNonQueryAsync(TestContext.Current.CancellationToken);
            }
            // Base vacía: PostgresStore.Migrate exige una instancia ya inicializada, así que se aplica el mismo migrador.
            await using var db = await fixture.Source().OpenConnectionAsync(TestContext.Current.CancellationToken);
            await using var tx = await db.BeginTransactionAsync(TestContext.Current.CancellationToken);
            await SchemaMigrations.Apply(db, tx, TestContext.Current.CancellationToken);
            await tx.CommitAsync(TestContext.Current.CancellationToken);
            return fixture;
        }

        public IConfiguration Configuration() => new ConfigurationBuilder().AddInMemoryCollection(new Dictionary<string, string?>
        {
            ["Recovery:User"] = RecoveryUser,
            ["Recovery:ExpectedDatabase"] = Database,
            ["Recovery:BackupSha256"] = BackupSha256,
            ["ConnectionStrings:RackClick"] = OwnerConnection(),
        }).Build();

        // Un enroll y un verify pendientes, vigentes, y una sesión: lo que debe quedar invalidado al recuperar.
        public async Task SeedPendingStateAsync()
        {
            var user = Guid.NewGuid();
            var systemhaus = Guid.NewGuid();
            await ExecuteAsync("INSERT INTO systemhaus(id,name) VALUES(@id,'Laboratorio recuperacion')", ("id", systemhaus));
            await ExecuteAsync("INSERT INTO app_user(id,systemhaus_id,username,password_hash) VALUES(@user,@sh,'usuario.mfa',@hash)",
                ("user", user), ("sh", systemhaus), ("hash", Secrets.PasswordHash("usuario.mfa", "Usuario-Mfa-Prueba-16")));
            await ExecuteAsync("""
                INSERT INTO app_mfa_challenge(token_hash,systemhaus_id,user_id,purpose,csrf_hash,policy_revision,expires_at)
                VALUES('enroll-pendiente-0001',@sh,@user,'enroll','csrf-enroll-0001',0,now()+interval '4 minutes'),
                      ('verify-pendiente-0001',@sh,@user,'verify','csrf-verify-0001',0,now()+interval '4 minutes')
                """, ("sh", systemhaus), ("user", user));
            await ExecuteAsync("INSERT INTO app_session(token_hash,user_id,csrf_hash,expires_at) VALUES('sesion-previa-0001',@user,'csrf-sesion-0001',now()+interval '8 hours')",
                ("user", user));
            await ExecuteAsync($"COMMENT ON DATABASE {Database} IS '{Marker}'");
        }

        public async Task<long> CountAsync(string sql) => Convert.ToInt64(await ScalarAsync(sql));

        public async Task<string?> ScalarTextAsync(string sql) => Convert.ToString(await ScalarAsync(sql));

        public async Task ExecuteAsync(string sql, params (string Name, object Value)[] values)
        {
            await using var connection = await Source().OpenConnectionAsync(TestContext.Current.CancellationToken);
            await using var command = new NpgsqlCommand(sql, connection);
            foreach (var (name, value) in values) command.Parameters.AddWithValue(name, value);
            await command.ExecuteNonQueryAsync(TestContext.Current.CancellationToken);
        }

        private async Task<object?> ScalarAsync(string sql)
        {
            await using var connection = await Source().OpenConnectionAsync(TestContext.Current.CancellationToken);
            await using var command = new NpgsqlCommand(sql, connection);
            return await command.ExecuteScalarAsync(TestContext.Current.CancellationToken);
        }

        private NpgsqlDataSource Source()
        {
            _source ??= NpgsqlDataSource.Create(OwnerConnection());
            return _source;
        }

        private string OwnerConnection()
        {
            var builder = new NpgsqlConnectionStringBuilder(_admin) { Database = Database, Username = _owner, Password = _password };
            return builder.ConnectionString;
        }

        public async ValueTask DisposeAsync()
        {
            _source?.Dispose();
            NpgsqlConnection.ClearAllPools();
            await using var connection = new NpgsqlConnection(_admin);
            await connection.OpenAsync();
            await using (var drop = new NpgsqlCommand($"DROP DATABASE IF EXISTS {Database} WITH (FORCE)", connection))
                await drop.ExecuteNonQueryAsync();
            await using (var role = new NpgsqlCommand($"DROP ROLE IF EXISTS {_owner}", connection))
                await role.ExecuteNonQueryAsync();
        }
    }
}
