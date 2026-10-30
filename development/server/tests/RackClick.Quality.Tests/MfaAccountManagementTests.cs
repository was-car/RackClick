using System.Text.Json;
using Npgsql;
using RackClick.Domain;
using RackClick.Server;
using Xunit;

namespace RackClick.Quality.Tests;

[Collection("MfaHttp")]
public sealed class MfaAccountManagementTests
{
    [Fact]
    public async Task ExistingUsersHaveFortyFiveDaysFromRolloutAndNoInventedCreationDate()
    {
        await using var lab = await Laboratory.Create();
        var user = await lab.AddUser("existing.user");
        await lab.Execute("UPDATE app_user SET created_at=NULL WHERE id=@user", ("user", user.Id));
        await lab.Policy(0);
        var status = await lab.Store.ReadOwnMfaStatus(user, true, TestContext.Current.CancellationToken);
        Assert.True(status.GlobalPolicyEnabled); Assert.Equal(45, status.GraceDays); Assert.Equal(45, status.DaysRemaining);
        Assert.False(status.DeadlineReached); Assert.False(status.Required); Assert.False(status.GlobalAdministratorExempt);
        Assert.True(status.CanEnable); Assert.False(status.CanDisable);
        Assert.Equal(TimeSpan.Zero, status.ServerNowUtc.Offset);
        Assert.True(status.DeadlineUtc > status.ServerNowUtc.AddDays(44));
    }

    [Fact]
    public async Task NewAccountsHaveTheirOwnCreationDeadlineAndCannotExtendItByDisabling()
    {
        await using var lab = await Laboratory.Create();
        var user = await lab.AddUser("new.user");
        await lab.Policy(10);
        await lab.Execute("UPDATE app_user SET created_at=clock_timestamp()-interval '5 days' WHERE id=@user", ("user", user.Id));
        var before = await lab.Store.ReadOwnMfaStatus(user, true, TestContext.Current.CancellationToken);
        Assert.Equal(40, before.DaysRemaining);
        await lab.Store.ChangeOwnMfa(user, "disable", Laboratory.Password, before.Revision, Guid.NewGuid(), true, TestContext.Current.CancellationToken);
        var renewed = await lab.Session(user.Id, verified: false);
        var after = await lab.Store.ReadOwnMfaStatus(renewed, true, TestContext.Current.CancellationToken);
        Assert.Equal(before.DeadlineUtc, after.DeadlineUtc); Assert.Equal(40, after.DaysRemaining);
    }

    [Fact]
    public async Task SelfEnableRevokesEverySessionAndChallengeAndRequiresEnrollmentWithoutAnApiSession()
    {
        await using var lab = await Laboratory.Create();
        var user = await lab.AddUser("enable.user");
        await lab.Session(user.Id, verified: false); await lab.Challenge(user.Id);
        var request = Guid.NewGuid();
        var receipt = await lab.Store.ChangeOwnMfa(user, "enable", Laboratory.Password, 1, request, true, TestContext.Current.CancellationToken);
        var json = JsonDocument.Parse(receipt).RootElement;
        Assert.Equal(user.Id, json.GetProperty("userId").GetGuid()); Assert.Equal("enable", json.GetProperty("action").GetString());
        Assert.True(json.GetProperty("signInRequired").GetBoolean()); Assert.Equal(request, json.GetProperty("requestId").GetGuid());
        Assert.Equal(0, await lab.Count("SELECT count(*) FROM app_session WHERE user_id=@user", ("user", user.Id)));
        Assert.Equal(0, await lab.Count("SELECT count(*) FROM app_mfa_challenge WHERE user_id=@user AND consumed_at IS NULL", ("user", user.Id)));
        Assert.Equal(1, await lab.Count("SELECT count(*) FROM app_mfa_user WHERE user_id=@user AND mfa_required AND enrollment_pending", ("user", user.Id)));
        var login = await new PostgresStore(lab.RuntimeSource) { MfaAvailable = true }.AuthenticateForLogin("enable.user", Laboratory.Password, TestContext.Current.CancellationToken);
        Assert.Null(login.Session); Assert.Equal("enroll", login.ChallengePurpose);
        Assert.DoesNotContain(Laboratory.Password, await lab.Snapshot("operation", "audit_event"), StringComparison.Ordinal);
    }

    [Fact]
    public async Task SelfDisableWithinGraceRequiresPasswordAndCompletedMfaAndRevokesRecoveryMaterial()
    {
        await using var lab = await Laboratory.Create();
        var user = await lab.AddUser("disable.user", factor: true, verified: true);
        await lab.Policy(0); await lab.Challenge(user.Id); await lab.RecoveryCode(user.Id);
        await lab.Store.ChangeOwnMfa(user, "disable", Laboratory.Password, 1, Guid.NewGuid(), true, TestContext.Current.CancellationToken);
        Assert.Equal(1, await lab.Count("SELECT count(*) FROM app_mfa_factor WHERE user_id=@user AND state='disabled'", ("user", user.Id)));
        Assert.Equal(1, await lab.Count("SELECT count(*) FROM app_mfa_user WHERE user_id=@user AND NOT mfa_required AND NOT enrollment_pending", ("user", user.Id)));
        Assert.Equal(0, await lab.Count("SELECT count(*) FROM app_mfa_recovery_code WHERE user_id=@user", ("user", user.Id)));
        Assert.Equal(0, await lab.Count("SELECT count(*) FROM app_session WHERE user_id=@user", ("user", user.Id)));
        Assert.Equal(0, await lab.Count("SELECT count(*) FROM app_mfa_challenge WHERE user_id=@user AND consumed_at IS NULL", ("user", user.Id)));
    }

    [Fact]
    public async Task OrdinaryUsersCannotDisableAfterDeadlineEvenWithACompletedMfaSession()
    {
        await using var lab = await Laboratory.Create();
        var user = await lab.AddUser("overdue.user", factor: true, verified: true);
        await lab.Policy(50); await lab.Legacy(user.Id);
        var before = await lab.SnapshotAll();
        var error = await Assert.ThrowsAsync<DomainError>(() => lab.Store.ChangeOwnMfa(user, "disable", Laboratory.Password, 1, Guid.NewGuid(), true, TestContext.Current.CancellationToken));
        Assert.Equal("mfa_required_by_policy", error.Code); Assert.Equal(before, await lab.SnapshotAll());
        var status = await lab.Store.ReadOwnMfaStatus(user, true, TestContext.Current.CancellationToken);
        Assert.True(status.Required); Assert.True(status.DeadlineReached); Assert.Equal(0, status.DaysRemaining); Assert.False(status.CanDisable);
    }

    [Fact]
    public async Task OnlyTheGlobalAdministratorMayDisableTheirOwnFactorAfterDeadline()
    {
        await using var lab = await Laboratory.Create();
        await lab.Factor(lab.Admin.Id); await lab.Policy(50); await lab.Legacy(lab.Admin.Id);
        var status = await lab.Store.ReadOwnMfaStatus(lab.Admin, true, TestContext.Current.CancellationToken);
        Assert.True(status.GlobalAdministratorExempt); Assert.True(status.DeadlineReached); Assert.True(status.CanDisable);
        await lab.Store.ChangeOwnMfa(lab.Admin, "disable", Laboratory.Password, status.Revision, Guid.NewGuid(), true, TestContext.Current.CancellationToken);
        var admin = await lab.Session(lab.Admin.Id, false);
        status = await lab.Store.ReadOwnMfaStatus(admin, true, TestContext.Current.CancellationToken);
        Assert.False(status.Required); Assert.True(status.GlobalAdministratorExempt);
    }

    [Fact]
    public async Task AdministratorCannotDisableAnotherUsersFactorAfterTheirDeadline()
    {
        await using var lab = await Laboratory.Create();
        var user = await lab.AddUser("other.overdue", factor: true);
        await lab.Policy(50); await lab.Legacy(user.Id);
        var before = await lab.SnapshotAll();
        var error = await Assert.ThrowsAsync<DomainError>(() => lab.Store.ChangeUserMfa(lab.Admin, user.Id, "disable", 1, Guid.NewGuid(), true, TestContext.Current.CancellationToken));
        Assert.Equal("mfa_required_by_policy", error.Code); Assert.Equal(before, await lab.SnapshotAll());
    }

    [Fact]
    public async Task AdministratorMutationRequiresCurrentCompletedMfaAndCannotBypassOwnPasswordRoute()
    {
        await using var lab = await Laboratory.Create();
        var user = await lab.AddUser("managed.user");
        var admin = await lab.Session(lab.Admin.Id, false);
        var before = await lab.SnapshotAll();
        var denied = await Assert.ThrowsAsync<DomainError>(() => lab.Store.ChangeUserMfa(admin, user.Id, "enable", 1, Guid.NewGuid(), true, TestContext.Current.CancellationToken));
        Assert.Equal("mfa_verification_required", denied.Code); Assert.Equal(before, await lab.SnapshotAll());
        var self = await Assert.ThrowsAsync<DomainError>(() => lab.Store.ChangeUserMfa(lab.Admin, lab.Admin.Id, "disable", 1, Guid.NewGuid(), true, TestContext.Current.CancellationToken));
        Assert.Equal("mfa_use_self_service", self.Code);
    }

    [Fact]
    public async Task EnableReplayReturnsTheExactReceiptWithoutDuplicatingAuditOrRevision()
    {
        await using var lab = await Laboratory.Create();
        var user = await lab.AddUser("replay.user"); var request = Guid.NewGuid();
        var first = await lab.Store.ChangeUserMfa(lab.Admin, user.Id, "enable", 1, request, true, TestContext.Current.CancellationToken);
        var snapshot = await lab.SnapshotAll();
        var repeated = await lab.Store.ChangeUserMfa(lab.Admin, user.Id, "enable", 1, request, true, TestContext.Current.CancellationToken);
        Assert.Equal(first, repeated); Assert.Equal(snapshot, await lab.SnapshotAll());
        var outcome = JsonDocument.Parse(await lab.Store.ReadMfaChangeStatus(lab.Admin, user.Id, request, true, TestContext.Current.CancellationToken)).RootElement;
        Assert.Equal("committed", outcome.GetProperty("state").GetString());
        Assert.Equal(user.Id, outcome.GetProperty("operation").GetProperty("userId").GetGuid());
        var reused = await Assert.ThrowsAsync<DomainError>(() => lab.Store.ChangeUserMfa(lab.Admin, user.Id, "reset", 1, request, true, TestContext.Current.CancellationToken));
        Assert.Equal("request_id_reused", reused.Code); Assert.Equal(snapshot, await lab.SnapshotAll());
    }

    [Fact]
    public async Task ResetRevokesFactorSessionsChallengesAndRecoveryCodesAndPreservesMandatoryEnrollment()
    {
        await using var lab = await Laboratory.Create();
        var user = await lab.AddUser("reset.user", factor: true, verified: true);
        await lab.Challenge(user.Id); await lab.RecoveryCode(user.Id);
        await lab.Store.ChangeUserMfa(lab.Admin, user.Id, "reset", 1, Guid.NewGuid(), true, TestContext.Current.CancellationToken);
        Assert.Equal(1, await lab.Count("SELECT count(*) FROM app_mfa_user WHERE user_id=@user AND mfa_required AND enrollment_pending", ("user", user.Id)));
        Assert.Equal(0, await lab.Count("SELECT count(*) FROM app_session WHERE user_id=@user", ("user", user.Id)));
        Assert.Equal(0, await lab.Count("SELECT count(*) FROM app_mfa_recovery_code WHERE user_id=@user", ("user", user.Id)));
        Assert.Equal(0, await lab.Count("SELECT count(*) FROM app_mfa_challenge WHERE user_id=@user AND consumed_at IS NULL", ("user", user.Id)));
    }

    [Fact]
    public async Task ConflictsInvalidPasswordsUnavailableProviderAndForeignTargetsDoNotMutate()
    {
        await using var lab = await Laboratory.Create();
        var user = await lab.AddUser("negative.user"); var before = await lab.SnapshotAll();
        var conflict = await Assert.ThrowsAsync<DomainError>(() => lab.Store.ChangeUserMfa(lab.Admin, user.Id, "enable", 99, Guid.NewGuid(), true, TestContext.Current.CancellationToken));
        Assert.Equal(412, conflict.Status);
        var password = await Assert.ThrowsAsync<DomainError>(() => lab.Store.ChangeOwnMfa(user, "enable", "Incorrect-password-only-for-lab", 1, Guid.NewGuid(), true, TestContext.Current.CancellationToken));
        Assert.Equal("mfa_reauthentication_required", password.Code);
        var unavailable = await Assert.ThrowsAsync<DomainError>(() => lab.Store.ChangeOwnMfa(user, "enable", Laboratory.Password, 1, Guid.NewGuid(), false, TestContext.Current.CancellationToken));
        Assert.Equal("mfa_unavailable", unavailable.Code);
        var missing = await Assert.ThrowsAsync<DomainError>(() => lab.Store.ChangeUserMfa(lab.Admin, Guid.NewGuid(), "enable", 1, Guid.NewGuid(), true, TestContext.Current.CancellationToken));
        Assert.Equal(404, missing.Status); Assert.Equal(before, await lab.SnapshotAll());
    }

    [Fact]
    public async Task SelfChangingAnActiveFactorRequiresCompletedMfaAndCurrentGlobalPrivilegesAreRechecked()
    {
        await using var lab = await Laboratory.Create();
        var user = await lab.AddUser("active.unverified", factor: true, verified: false);
        var before = await lab.SnapshotAll();
        var denied = await Assert.ThrowsAsync<DomainError>(() => lab.Store.ChangeOwnMfa(user, "disable", Laboratory.Password, 1, Guid.NewGuid(), true, TestContext.Current.CancellationToken));
        Assert.Equal("mfa_verification_required", denied.Code); Assert.Equal(before, await lab.SnapshotAll());
        await lab.Execute("DELETE FROM permission_grant WHERE capability='systemhaus.manage'");
        await lab.Policy(50); await lab.Legacy(lab.Admin.Id); await lab.Factor(lab.Admin.Id);
        var status = await lab.Store.ReadOwnMfaStatus(lab.Admin, true, TestContext.Current.CancellationToken);
        Assert.False(status.GlobalAdministratorExempt); Assert.False(status.CanDisable);
    }

    [Fact]
    public async Task AuditFailureRollsBackPolicyFactorSessionChallengeRecoveryAndRevision()
    {
        await using var lab = await Laboratory.Create();
        var user = await lab.AddUser("rollback.user", factor: true, verified: true);
        await lab.Challenge(user.Id); await lab.RecoveryCode(user.Id);
        await lab.Execute("""
            CREATE FUNCTION reject_mfa_audit_fixture() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN IF NEW.action LIKE 'auth.mfa.user.%' THEN RAISE EXCEPTION 'fixture_audit_failure'; END IF; RETURN NEW; END $$;
            CREATE TRIGGER reject_mfa_audit_fixture BEFORE INSERT ON audit_event FOR EACH ROW EXECUTE FUNCTION reject_mfa_audit_fixture();
            """);
        var before = await lab.SnapshotAll();
        await Assert.ThrowsAsync<PostgresException>(() => lab.Store.ChangeUserMfa(lab.Admin, user.Id, "reset", 1, Guid.NewGuid(), true, TestContext.Current.CancellationToken));
        Assert.Equal(before, await lab.SnapshotAll());
    }

    [Fact]
    public async Task ClientScopedAdministrativeGrantsDoNotCreateTheGlobalAdministratorException()
    {
        await using var lab = await Laboratory.Create();
        var scoped = await lab.AddUser("client.administrator", factor: true, verified: true);
        var other = await lab.AddUser("other.user");
        var customer = Guid.NewGuid(); var group = Guid.NewGuid();
        await lab.Execute("""
            INSERT INTO customer(id,systemhaus_id,name) VALUES(@customer,@house,'Scoped fixture');
            INSERT INTO user_group(id,systemhaus_id,name) VALUES(@group,@house,'Scoped administrators');
            INSERT INTO user_group_member(systemhaus_id,user_id,group_id) VALUES(@house,@user,@group);
            INSERT INTO permission_grant(id,systemhaus_id,user_group_id,capability,customer_id)
              VALUES(@grant1,@house,@group,'security.manage',@customer),(@grant2,@house,@group,'systemhaus.manage',@customer);
            """, ("customer", customer), ("house", lab.House), ("group", group), ("user", scoped.Id),
            ("grant1", Guid.NewGuid()), ("grant2", Guid.NewGuid()));
        await lab.Policy(50); await lab.Legacy(scoped.Id);
        var status = await lab.Store.ReadOwnMfaStatus(scoped, true, TestContext.Current.CancellationToken);
        Assert.False(status.GlobalAdministratorExempt); Assert.False(status.CanDisable); Assert.True(status.Required);
        var before = await lab.SnapshotAll();
        var denied = await Assert.ThrowsAsync<DomainError>(() => lab.Store.ChangeUserMfa(scoped, other.Id, "enable", 1, Guid.NewGuid(), true, TestContext.Current.CancellationToken));
        Assert.Equal(403, denied.Status); Assert.Equal("forbidden", denied.Code); Assert.Equal(before, await lab.SnapshotAll());
    }

    internal sealed class Laboratory(string adminConnection) : IAsyncDisposable
    {
        public const string Password = "Dashboard-only-laboratory-password-2026!";
        private readonly string _database = "rc_mfa_dashboard_" + Guid.NewGuid().ToString("N");
        private readonly string _owner = "rc_mfa_dashboard_owner_" + Guid.NewGuid().ToString("N");
        private readonly string _runtime = "rc_mfa_dashboard_runtime_" + Guid.NewGuid().ToString("N");
        private readonly string _rolePassword = Convert.ToBase64String(System.Security.Cryptography.RandomNumberGenerator.GetBytes(32));
        private NpgsqlDataSource? _ownerSource;
        private NpgsqlDataSource? _runtimeSource;
        public Guid House { get; private set; }
        public Actor Admin { get; private set; } = null!;
        public NpgsqlDataSource RuntimeSource => _runtimeSource ??= NpgsqlDataSource.Create(Connection(_runtime));
        public string RuntimeConnection => Connection(_runtime);
        public PostgresStore Store => new(RuntimeSource) { MfaAvailable = true };
        private NpgsqlDataSource OwnerSource => _ownerSource ??= NpgsqlDataSource.Create(Connection(_owner));
        private string Connection(string role) => new NpgsqlConnectionStringBuilder(adminConnection)
            { Database = _database, Username = role, Password = _rolePassword, IncludeErrorDetail = false }.ConnectionString;

        public static async Task<Laboratory> Create()
        {
            var admin = Environment.GetEnvironmentVariable("RACKCLICK_TEST_PG_ADMIN");
            Assert.SkipWhen(string.IsNullOrWhiteSpace(admin), "Explicit isolated PostgreSQL laboratory required.");
            var lab = new Laboratory(admin!);
            await using (var db = new NpgsqlConnection(admin))
            {
                await db.OpenAsync(TestContext.Current.CancellationToken);
                foreach (var sql in new[]
                {
                    $"CREATE ROLE {lab._owner} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD '{lab._rolePassword}'",
                    $"CREATE ROLE {lab._runtime} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD '{lab._rolePassword}'",
                    $"CREATE DATABASE {lab._database} OWNER {lab._owner} ENCODING 'UTF8' TEMPLATE template0",
                })
                {
                    await using var create = new NpgsqlCommand(sql, db);
                    await create.ExecuteNonQueryAsync(TestContext.Current.CancellationToken);
                }
            }
            await new PostgresStore(lab.OwnerSource).Bootstrap("MFA dashboard laboratory", "dashboard.admin", Password, TestContext.Current.CancellationToken);
            await lab.Execute($"GRANT USAGE ON SCHEMA public TO {lab._runtime}; GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public TO {lab._runtime}; REVOKE CREATE ON SCHEMA public FROM PUBLIC;");
            await using (var db = await lab.OwnerSource.OpenConnectionAsync(TestContext.Current.CancellationToken))
            {
                await using var query = new NpgsqlCommand("SELECT id,systemhaus_id FROM app_user WHERE username='dashboard.admin'", db);
                await using var row = await query.ExecuteReaderAsync(TestContext.Current.CancellationToken);
                Assert.True(await row.ReadAsync(TestContext.Current.CancellationToken));
                lab.House = row.GetGuid(1);
                lab.Admin = new Actor(row.GetGuid(0), lab.House, "dashboard.admin");
            }
            lab.Admin = await lab.Session(lab.Admin.Id, true);
            return lab;
        }

        public async Task<Actor> AddUser(string username, bool factor = false, bool verified = false)
        {
            var id = Guid.NewGuid();
            await Execute("INSERT INTO app_user(id,systemhaus_id,username,password_hash) VALUES(@id,@house,@name,@hash)",
                ("id", id), ("house", House), ("name", username), ("hash", Secrets.PasswordHash(username, Password)));
            if (factor) await Factor(id);
            return await Session(id, verified);
        }
        public async Task<Actor> Session(Guid user, bool verified)
        {
            var token = Secrets.Token(); var csrf = Secrets.Token();
            await Execute("INSERT INTO app_session(token_hash,user_id,csrf_hash,expires_at,mfa_verified_at) VALUES(@token,@user,@csrf,clock_timestamp()+interval '1 hour',CASE WHEN @verified THEN clock_timestamp() ELSE NULL END)",
                ("token", Secrets.Digest(token)), ("user", user), ("csrf", Secrets.Digest(csrf)), ("verified", verified));
            await using var db = await OwnerSource.OpenConnectionAsync(TestContext.Current.CancellationToken);
            await using var query = new NpgsqlCommand("SELECT username FROM app_user WHERE id=@user", db); query.Parameters.AddWithValue("user", user);
            var name = (string)(await query.ExecuteScalarAsync(TestContext.Current.CancellationToken))!;
            return new(user, House, name) { SessionTokenHash = Secrets.Digest(token) };
        }
        public Task Factor(Guid user) => Execute("""
            INSERT INTO app_mfa_factor(systemhaus_id,user_id,state,secret_ciphertext,key_version) VALUES(@house,@user,'active',decode('012345','hex'),1)
            ON CONFLICT(systemhaus_id,user_id) DO UPDATE SET state='active';
            INSERT INTO app_mfa_user(systemhaus_id,user_id,mfa_required,enrollment_pending,revision) VALUES(@house,@user,true,false,1)
            ON CONFLICT(systemhaus_id,user_id) DO UPDATE SET mfa_required=true,enrollment_pending=false;
            """, ("house", House), ("user", user));
        public Task Challenge(Guid user) => Execute("""
            INSERT INTO app_mfa_challenge(token_hash,systemhaus_id,user_id,purpose,csrf_hash,expires_at,policy_revision)
            VALUES(@token,@house,@user,'verify',@csrf,clock_timestamp()+interval '4 minutes',1)
            """, ("token", Secrets.Digest(Secrets.Token())), ("csrf", Secrets.Digest(Secrets.Token())), ("house", House), ("user", user));
        public Task RecoveryCode(Guid user) => Execute("INSERT INTO app_mfa_recovery_code(code_hash,systemhaus_id,user_id) VALUES(@code,@house,@user)",
            ("code", Secrets.Digest(Secrets.Token())), ("house", House), ("user", user));
        public Task Legacy(Guid user) => Execute("UPDATE app_user SET created_at=NULL WHERE id=@user", ("user", user));
        public Task Policy(int elapsedDays) => Execute("INSERT INTO app_mfa_policy(systemhaus_id,enabled,grace_days,activated_at) VALUES(@house,true,45,clock_timestamp()-make_interval(days=>@days))",
            ("house", House), ("days", elapsedDays));
        public async Task<int> Execute(string sql, params (string Name, object Value)[] values)
        {
            await using var db = await OwnerSource.OpenConnectionAsync(TestContext.Current.CancellationToken);
            await using var command = new NpgsqlCommand(sql, db);
            foreach (var (name, value) in values) command.Parameters.AddWithValue(name, value);
            return await command.ExecuteNonQueryAsync(TestContext.Current.CancellationToken);
        }
        public async Task<long> Count(string sql, params (string Name, object Value)[] values)
        {
            await using var db = await OwnerSource.OpenConnectionAsync(TestContext.Current.CancellationToken);
            await using var command = new NpgsqlCommand(sql, db);
            foreach (var (name, value) in values) command.Parameters.AddWithValue(name, value);
            return Convert.ToInt64(await command.ExecuteScalarAsync(TestContext.Current.CancellationToken));
        }
        public Task<long> Scalar(string sql, params (string Name, object Value)[] values) => Count(sql, values);
        public async Task<string> Snapshot(params string[] tables)
        {
            var rows = new List<string>();
            foreach (var table in tables)
            {
                Assert.Contains(table, new[] { "app_user", "app_mfa_user", "app_mfa_factor", "app_mfa_recovery_code", "app_mfa_challenge", "app_session", "systemhaus", "operation", "audit_event", "app_mfa_policy" });
                await using var db = await OwnerSource.OpenConnectionAsync(TestContext.Current.CancellationToken);
                await using var command = new NpgsqlCommand($"SELECT COALESCE(jsonb_agg(row_to_json(t) ORDER BY row_to_json(t)::text),'[]'::jsonb)::text FROM {table} t", db);
                rows.Add(table + ":" + await command.ExecuteScalarAsync(TestContext.Current.CancellationToken));
            }
            return string.Join("\n", rows);
        }
        public Task<string> SnapshotAll() => Snapshot("app_user", "app_mfa_user", "app_mfa_factor", "app_mfa_recovery_code", "app_mfa_challenge", "app_session", "systemhaus", "operation", "audit_event", "app_mfa_policy");
        public async ValueTask DisposeAsync()
        {
            if (_runtimeSource is not null) await _runtimeSource.DisposeAsync();
            if (_ownerSource is not null) await _ownerSource.DisposeAsync();
            await using var db = new NpgsqlConnection(adminConnection); await db.OpenAsync(TestContext.Current.CancellationToken);
            foreach (var sql in new[] { $"DROP DATABASE IF EXISTS {_database} WITH (FORCE)", $"DROP ROLE IF EXISTS {_runtime}", $"DROP ROLE IF EXISTS {_owner}" })
            {
                await using var command = new NpgsqlCommand(sql, db); await command.ExecuteNonQueryAsync(TestContext.Current.CancellationToken);
            }
        }
    }
}
