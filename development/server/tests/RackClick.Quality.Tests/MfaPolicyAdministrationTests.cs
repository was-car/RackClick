using System.Security.Cryptography;
using Npgsql;
using RackClick.Domain;
using RackClick.Server;
using Xunit;

namespace RackClick.Quality.Tests;

public sealed class MfaPolicyAdministrationTests
{
    [Fact]
    public async Task ActivationRequiresAllPresentUsersAndPreservesActiveFactorsAndUnchangedUsers()
    {
        await using var lab = await Laboratory.Create();
        var active = await lab.AddUser("active.factor", activeFactor: true);
        var already = await lab.AddUser("already.required", activeFactor: true, required: true);
        await lab.SeedSessionAndChallenge(lab.Actor);
        await lab.SeedSessionAndChallenge(active);
        await lab.SeedSessionAndChallenge(already);
        string factors = await lab.Snapshot("app_mfa_factor");

        var result = await lab.Activate();

        Assert.False(result.Noop);
        Assert.Equal(2, result.ChangedUsers);
        Assert.Equal(2, result.RevokedSessions);
        Assert.Equal(2, result.RevokedChallenges);
        Assert.Equal(2, result.SystemhausRevision);
        Assert.Equal(3, await lab.Count("SELECT count(*) FROM app_mfa_user WHERE mfa_required"));
        Assert.Equal(1, await lab.Count("SELECT count(*) FROM app_mfa_user WHERE enrollment_pending"));
        Assert.Equal(factors, await lab.Snapshot("app_mfa_factor"));
        Assert.Equal(1, await lab.Count("SELECT count(*) FROM app_session"));
        Assert.Equal(1, await lab.Count("SELECT count(*) FROM app_mfa_challenge WHERE consumed_at IS NULL"));
        Assert.Equal(1, await lab.Count("SELECT count(*) FROM audit_event WHERE action='auth.mfa.policy.require_all'"));
        var noFactor = await new PostgresStore(lab.Source()) { MfaAvailable = true }
            .AuthenticateForLogin(Laboratory.AdminUser, Laboratory.Password, TestContext.Current.CancellationToken);
        var withFactor = await new PostgresStore(lab.Source()) { MfaAvailable = true }
            .AuthenticateForLogin("active.factor", Laboratory.Password, TestContext.Current.CancellationToken);
        Assert.Null(noFactor.Session); Assert.Equal("enroll", noFactor.ChallengePurpose);
        Assert.Null(withFactor.Session); Assert.NotNull(withFactor.Challenge);
        // The existing verify outcome leaves ChallengePurpose null; the HTTP route maps that legacy shape to verify.
        Assert.Equal(1, await lab.Count("SELECT count(*) FROM app_mfa_challenge WHERE purpose='verify' AND consumed_at IS NULL"));
    }

    [Fact]
    public async Task ExactRepetitionIsANoopAndDoesNotResetCountersOrExistingPendingState()
    {
        await using var lab = await Laboratory.Create();
        var user = await lab.AddUser("pending.factor", activeFactor: true, required: true, pending: true);
        await lab.Activate();
        await lab.SeedSessionAndChallenge(user);
        string before = await lab.FullSnapshot();

        var repeated = await lab.Activate();

        Assert.True(repeated.Noop);
        Assert.Equal(0, repeated.ChangedUsers);
        Assert.Equal(0, repeated.RevokedSessions);
        Assert.Equal(0, repeated.RevokedChallenges);
        Assert.Null(repeated.AuditId);
        Assert.Equal(before, await lab.FullSnapshot());
    }

    [Fact]
    public async Task RestrictedRuntimeCannotInvokeTheOwnerOperation()
    {
        await using var lab = await Laboratory.Create();
        string before = await lab.FullSnapshot();

        var error = await Assert.ThrowsAsync<DomainError>(() => MfaPolicyAdministration.RequireAll(
            lab.RuntimeConnection(), lab.Id, lab.Actor, lab.Keys, TestContext.Current.CancellationToken));

        Assert.Equal("mfa_policy_owner_required", error.Code);
        Assert.Equal(before, await lab.FullSnapshot());
    }

    [Fact]
    public async Task AnotherDatabaseIdentityIsRejectedBeforeMutation()
    {
        await using var lab = await Laboratory.Create();
        string before = await lab.FullSnapshot();

        var error = await Assert.ThrowsAsync<DomainError>(() => MfaPolicyAdministration.RequireAll(
            lab.OwnerConnection(), Guid.NewGuid(), lab.Actor, lab.Keys, TestContext.Current.CancellationToken));

        Assert.Equal("mfa_policy_database_mismatch", error.Code);
        Assert.Equal(before, await lab.FullSnapshot());
    }

    [Fact]
    public async Task PendingRecoveryMarkerIsPreservedAndRejected()
    {
        await using var lab = await Laboratory.Create();
        await lab.Execute($"COMMENT ON DATABASE {lab.Database} IS 'RackClickRecoveryPending:test'");
        string before = await lab.FullSnapshot();

        var error = await Assert.ThrowsAsync<DomainError>(() => lab.Activate());

        Assert.Equal("mfa_policy_database_not_ready", error.Code);
        Assert.Equal(before, await lab.FullSnapshot());
        Assert.Equal("RackClickRecoveryPending:test", await lab.Text("SELECT shobj_description(oid,'pg_database') FROM pg_database WHERE datname=current_database()"));
    }

    [Fact]
    public async Task ActorWithoutSystemhausSecurityCapabilityIsRejected()
    {
        await using var lab = await Laboratory.Create();
        var reader = await lab.AddUser("reader", activeFactor: false);
        string before = await lab.FullSnapshot();

        var error = await Assert.ThrowsAsync<DomainError>(() => MfaPolicyAdministration.RequireAll(
            lab.OwnerConnection(), lab.Id, reader, lab.Keys, TestContext.Current.CancellationToken));

        Assert.Equal("mfa_policy_actor_required", error.Code);
        Assert.Equal(before, await lab.FullSnapshot());
    }

    [Fact]
    public async Task AuditFailureRollsBackPoliciesRevocationsAndHouseRevision()
    {
        await using var lab = await Laboratory.Create();
        await lab.SeedSessionAndChallenge(lab.Actor);
        await lab.Execute("CREATE FUNCTION fail_mfa_policy_audit() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'forced_test_failure'; END $$");
        await lab.Execute("CREATE TRIGGER fail_mfa_policy_audit BEFORE INSERT ON audit_event FOR EACH ROW EXECUTE FUNCTION fail_mfa_policy_audit()");
        string before = await lab.FullSnapshot();

        await Assert.ThrowsAsync<PostgresException>(() => lab.Activate());

        Assert.Equal(before, await lab.FullSnapshot());
    }

    [Fact]
    public async Task IncompleteSchemaIsRejectedWithoutApplyingAnyMigration()
    {
        await using var lab = await Laboratory.Create();
        await lab.Execute("DELETE FROM schema_migration WHERE version=14");
        string before = await lab.FullSnapshot();

        var error = await Assert.ThrowsAsync<DomainError>(() => lab.Activate());

        Assert.Equal("mfa_policy_schema_required", error.Code);
        Assert.Equal(before, await lab.FullSnapshot());
        Assert.Equal(SchemaMigrations.LatestVersion - 1, await lab.Count("SELECT count(*) FROM schema_migration"));
    }

    [Fact]
    public async Task TwoConcurrentCallsProduceOneCommitAndOneNoop()
    {
        await using var lab = await Laboratory.Create();
        var results = await Task.WhenAll(lab.Activate(), lab.Activate());

        Assert.Equal(1, results.Count(result => !result.Noop));
        Assert.Equal(1, results.Count(result => result.Noop));
        Assert.Equal(1, await lab.Count("SELECT count(*) FROM audit_event WHERE action='auth.mfa.policy.require_all'"));
        Assert.Equal(1, await lab.Count("SELECT revision FROM app_mfa_user"));
    }

    [Fact]
    public async Task AnAccountOperationCanFinishBeforeTheActivationTakesItsTableLock()
    {
        await using var lab = await Laboratory.Create();
        await using var holder = await lab.Source().OpenConnectionAsync(TestContext.Current.CancellationToken);
        await using var tx = await holder.BeginTransactionAsync(TestContext.Current.CancellationToken);
        await using (var row = new NpgsqlCommand("SELECT id FROM app_user FOR UPDATE", holder, tx))
            await row.ExecuteScalarAsync(TestContext.Current.CancellationToken);
        var activation = lab.Activate();
        await Task.Delay(150, TestContext.Current.CancellationToken);
        Assert.False(activation.IsCompleted);
        await using (var update = new NpgsqlCommand("UPDATE app_user SET failed_logins=failed_logins+1", holder, tx))
            await update.ExecuteNonQueryAsync(TestContext.Current.CancellationToken);
        await tx.CommitAsync(TestContext.Current.CancellationToken);

        var result = await activation.WaitAsync(TimeSpan.FromSeconds(10), TestContext.Current.CancellationToken);

        Assert.False(result.Noop);
        Assert.Equal(1, await lab.Count("SELECT failed_logins FROM app_user"));
    }

    [Fact]
    public async Task AValidButDifferentKeyStoreCannotActivatePoliciesForExistingFactors()
    {
        await using var lab = await Laboratory.Create();
        var active = await lab.AddUser("active.factor", activeFactor: true);
        await lab.SeedSessionAndChallenge(active);
        string before = await lab.FullSnapshot();
        var wrongKey = RandomNumberGenerator.GetBytes(MfaSecretCipher.KeyBytes);
        try
        {
            var error = await Assert.ThrowsAsync<DomainError>(() => MfaPolicyAdministration.RequireAll(
                lab.OwnerConnection(), lab.Id, lab.Actor, new FixedKeys(wrongKey), TestContext.Current.CancellationToken));

            Assert.Equal("mfa_policy_factor_key_mismatch", error.Code);
            Assert.Equal(before, await lab.FullSnapshot());
        }
        finally { CryptographicOperations.ZeroMemory(wrongKey); }
    }

    [Fact]
    public async Task MissingHistoricalKeyVersionIsRejectedWithoutMutation()
    {
        await using var lab = await Laboratory.Create();
        await lab.AddUser("active.factor", activeFactor: true);
        string before = await lab.FullSnapshot();

        var error = await Assert.ThrowsAsync<DomainError>(() => MfaPolicyAdministration.RequireAll(
            lab.OwnerConnection(), lab.Id, lab.Actor, new MissingHistoricalVersionKeys(), TestContext.Current.CancellationToken));

        Assert.Equal("mfa_policy_factor_key_mismatch", error.Code);
        Assert.Equal(before, await lab.FullSnapshot());
    }

    [Fact]
    public async Task AnExistingPendingFactorMustAlsoBelongToTheSelectedKeyStore()
    {
        await using var lab = await Laboratory.Create();
        var pending = await lab.AddUser("pending.factor", activeFactor: true, required: true, pending: true, factorState: "pending");
        await lab.SeedSessionAndChallenge(pending);
        Assert.Equal(0, await lab.Count("SELECT count(*) FROM app_mfa_factor WHERE state='active'"));
        string before = await lab.FullSnapshot();
        var wrongKey = RandomNumberGenerator.GetBytes(MfaSecretCipher.KeyBytes);
        try
        {
            var error = await Assert.ThrowsAsync<DomainError>(() => MfaPolicyAdministration.RequireAll(
                lab.OwnerConnection(), lab.Id, lab.Actor, new FixedKeys(wrongKey), TestContext.Current.CancellationToken));

            Assert.Equal("mfa_policy_factor_key_mismatch", error.Code);
            Assert.Equal(before, await lab.FullSnapshot());
        }
        finally { CryptographicOperations.ZeroMemory(wrongKey); }
    }

    private sealed class FixedKeys(byte[] material) : IMfaKeyProvider
    {
        public byte[] GetKey(int version) => version == 7 ? (byte[])material.Clone()
            : throw new MfaKeyRingException(MfaKeyRingErrorKind.UnknownVersion, "test_unknown_version");
        public (int Version, byte[] Key) GetActiveKey() => (7, (byte[])material.Clone());
    }

    private sealed class MissingHistoricalVersionKeys : IMfaKeyProvider
    {
        public byte[] GetKey(int version) => throw new MfaKeyRingException(MfaKeyRingErrorKind.UnknownVersion, "test_missing_historical_version");
        public (int Version, byte[] Key) GetActiveKey() => (8, RandomNumberGenerator.GetBytes(MfaSecretCipher.KeyBytes));
    }

    private sealed class Laboratory : IAsyncDisposable
    {
        public const string AdminUser = "policy.admin";
        public const string Password = "Local-Mfa-Test-Password16";
        private readonly string _admin;
        private readonly string _rolePassword = Convert.ToHexString(RandomNumberGenerator.GetBytes(24));
        private readonly byte[] _key = RandomNumberGenerator.GetBytes(MfaSecretCipher.KeyBytes);
        private NpgsqlDataSource? _source;
        private Laboratory(string admin) { _admin = admin; }
        public Guid Id { get; } = Guid.NewGuid();
        public string Database => "rc_db_" + Id.ToString("N");
        private string Owner => "rc_owner_" + Id.ToString("N");
        private string Runtime => "rc_runtime_" + Id.ToString("N");
        public Guid Actor { get; private set; }
        private Guid House { get; set; }
        public IMfaKeyProvider Keys => new FixedKeys(_key);

        public static async Task<Laboratory> Create()
        {
            string? admin = Environment.GetEnvironmentVariable("RACKCLICK_TEST_PG_ADMIN");
            Assert.SkipWhen(string.IsNullOrWhiteSpace(admin), "Explicit isolated PostgreSQL laboratory required.");
            var lab = new Laboratory(admin!);
            await using (var db = new NpgsqlConnection(admin))
            {
                await db.OpenAsync(TestContext.Current.CancellationToken);
                foreach (string sql in new[]
                {
                    $"CREATE ROLE {lab.Owner} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD '{lab._rolePassword}'",
                    $"CREATE ROLE {lab.Runtime} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD '{lab._rolePassword}'",
                    $"CREATE DATABASE {lab.Database} OWNER {lab.Owner} ENCODING 'UTF8' TEMPLATE template0",
                })
                {
                    await using var create = new NpgsqlCommand(sql, db);
                    await create.ExecuteNonQueryAsync(TestContext.Current.CancellationToken);
                }
            }
            await new PostgresStore(lab.Source()).Bootstrap("Policy laboratory", AdminUser, Password, TestContext.Current.CancellationToken);
            await using (var db = await lab.Source().OpenConnectionAsync(TestContext.Current.CancellationToken))
            {
                await using var actor = new NpgsqlCommand("SELECT id,systemhaus_id FROM app_user", db);
                await using var row = await actor.ExecuteReaderAsync(TestContext.Current.CancellationToken);
                Assert.True(await row.ReadAsync(TestContext.Current.CancellationToken));
                lab.Actor = row.GetGuid(0); lab.House = row.GetGuid(1);
            }
            await lab.Execute($"GRANT USAGE ON SCHEMA public TO {lab.Runtime}; GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public TO {lab.Runtime}; REVOKE CREATE ON SCHEMA public FROM PUBLIC;");
            return lab;
        }

        public NpgsqlDataSource Source() => _source ??= NpgsqlDataSource.Create(OwnerConnection());
        public string OwnerConnection() => new NpgsqlConnectionStringBuilder(_admin)
            { Database = Database, Username = Owner, Password = _rolePassword, IncludeErrorDetail = false }.ConnectionString;
        public string RuntimeConnection() => new NpgsqlConnectionStringBuilder(_admin)
            { Database = Database, Username = Runtime, Password = _rolePassword, IncludeErrorDetail = false }.ConnectionString;
        public Task<MfaPolicyActivationResult> Activate() => MfaPolicyAdministration.RequireAll(
            OwnerConnection(), Id, Actor, Keys, TestContext.Current.CancellationToken);

        public async Task<Guid> AddUser(string name, bool activeFactor, bool required = false, bool pending = false,
            string factorState = "active")
        {
            var user = Guid.NewGuid();
            await Execute("INSERT INTO app_user(id,systemhaus_id,username,password_hash) VALUES(@user,@house,@name,@hash)",
                ("user", user), ("house", House), ("name", name), ("hash", Secrets.PasswordHash(name, Password)));
            if (required)
                await Execute("INSERT INTO app_mfa_user(systemhaus_id,user_id,mfa_required,enrollment_pending,revision) VALUES(@house,@user,true,@pending,5)",
                    ("house", House), ("user", user), ("pending", pending));
            if (activeFactor)
            {
                var secret = MfaTotp.NewSecret();
                try
                {
                    var cipher = MfaSecretCipher.Seal(_key, 7, secret, House, user);
                    await Execute("""
                    INSERT INTO app_mfa_factor(systemhaus_id,user_id,state,secret_ciphertext,key_version,
                        last_time_step,failed_attempts,locked_until,confirmed_at)
                    VALUES(@house,@user,@state,@cipher,7,42,3,now()+interval '1 minute',
                           CASE WHEN @state='active' THEN now() ELSE NULL END)
                    """, ("house", House), ("user", user), ("state", factorState), ("cipher", cipher));
                }
                finally { CryptographicOperations.ZeroMemory(secret); }
            }
            return user;
        }

        public async Task SeedSessionAndChallenge(Guid user)
        {
            await Execute("INSERT INTO app_session(token_hash,user_id,csrf_hash,expires_at) VALUES(@token,@user,@csrf,now()+interval '1 hour')",
                ("token", Guid.NewGuid().ToString("N")), ("user", user), ("csrf", Guid.NewGuid().ToString("N")));
            await Execute("""
                INSERT INTO app_mfa_challenge(token_hash,systemhaus_id,user_id,purpose,csrf_hash,expires_at)
                VALUES(@token,@house,@user,'enroll',@csrf,now()+interval '4 minutes')
                """, ("token", Guid.NewGuid().ToString("N")), ("house", House), ("user", user), ("csrf", Guid.NewGuid().ToString("N")));
        }

        public async Task Execute(string sql, params (string Name, object Value)[] values)
        {
            await using var db = await Source().OpenConnectionAsync(TestContext.Current.CancellationToken);
            await using var command = new NpgsqlCommand(sql, db);
            foreach (var (name, value) in values) command.Parameters.AddWithValue(name, value);
            await command.ExecuteNonQueryAsync(TestContext.Current.CancellationToken);
        }
        public async Task<string> Text(string sql)
        {
            await using var db = await Source().OpenConnectionAsync(TestContext.Current.CancellationToken);
            await using var command = new NpgsqlCommand(sql, db);
            return Convert.ToString(await command.ExecuteScalarAsync(TestContext.Current.CancellationToken)) ?? "";
        }
        public async Task<long> Count(string sql) => long.Parse(await Text(sql), System.Globalization.CultureInfo.InvariantCulture);
        // Table identifiers are fixture-internal fixed names, never external data.
        public Task<string> Snapshot(string table) => Text($"SELECT COALESCE(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text),'[]'::jsonb)::text FROM public.{table} t");
        public async Task<string> FullSnapshot()
        {
            var snapshots = new List<string>();
            foreach (string table in new[] { "systemhaus", "app_user", "app_mfa_user", "app_mfa_factor", "app_session", "app_mfa_challenge", "audit_event", "schema_migration" })
                snapshots.Add(await Snapshot(table));
            return string.Join("\n", snapshots);
        }
        public async ValueTask DisposeAsync()
        {
            CryptographicOperations.ZeroMemory(_key);
            if (_source is not null) await _source.DisposeAsync();
            NpgsqlConnection.ClearAllPools();
            await using var db = new NpgsqlConnection(_admin);
            await db.OpenAsync();
            foreach (string sql in new[] { $"DROP DATABASE IF EXISTS {Database} WITH (FORCE)", $"DROP ROLE IF EXISTS {Runtime}", $"DROP ROLE IF EXISTS {Owner}" })
            {
                await using var drop = new NpgsqlCommand(sql, db);
                await drop.ExecuteNonQueryAsync();
            }
        }
    }
}
