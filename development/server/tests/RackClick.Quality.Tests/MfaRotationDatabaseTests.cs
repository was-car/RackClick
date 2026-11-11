using System.Data;
using System.Security.Cryptography;
using System.Text.Json;
using Npgsql;
using RackClick.Server;
using Xunit;

namespace RackClick.Quality.Tests;

// Only an explicitly supplied NEW loopback F0603 laboratory. No installed-DB fallback.
[Collection("MfaHttp")]
public sealed class MfaRotationDatabaseTests
{
    public static bool Available => File.Exists(Environment.GetEnvironmentVariable("RACKCLICK_F0603_CONTEXT"));
    private const string NeedLab = "Requires explicit new F0603 PostgreSQL laboratory context";
    private static CancellationToken Ct => TestContext.Current.CancellationToken;

    [Fact]
    public void BindingRejectsAmbiguousIdentityVersionsAndHashesBeforeSql()
    {
        var valid = Binding(Guid.NewGuid(), Guid.NewGuid());
        MfaRotationDatabase.ValidateBinding(valid);
        foreach (var invalid in new[]
        {
            valid with { OperationId = Guid.Empty }, valid with { InstallationId = Guid.Empty },
            valid with { SystemhausId = Guid.Empty }, valid with { OperatorSid = "administrator" },
            valid with { NewVersion = valid.OldVersion }, valid with { NewVersion = 1_000_001 },
            valid with { OriginalRingHash = "AA" }, valid with { FinalRingHash = valid.AdditiveRingHash }
        })
            Assert.Equal("mfa_rotation_binding_invalid", Assert.Throws<MfaMaintenanceException>(
                () => MfaRotationDatabase.ValidateBinding(invalid)).Code);
    }

    [Fact(Skip = NeedLab, SkipUnless = nameof(Available))]
    public async Task RewrapPreservesAllFactorStatesMetadataAndTotpAndRevokesOnlyAffectedSecurityRows()
    {
        await using var f = await Fixture.Create();
        var users = new List<Guid>();
        foreach (var state in new[] { "pending", "active", "disabled" })
            users.Add(await f.AddFactor(state, state == "disabled" ? 7 : 1));
        var unaffected = await f.AddUser();
        foreach (var user in users.Append(unaffected))
        {
            await f.AddSession(user);
            await f.AddChallenge(user, false);
            await f.AddChallenge(user, true);
        }
        var metadata = await f.Metadata();
        var witness = await MfaRotationDatabase.RewrapAsync(f.Db, f.Tx, f.Binding, f.Provider, f.Keys[8], Ct);
        Assert.Equal(3, witness.FactorCount);
        Assert.Equal(3, witness.RevokedSessions);
        Assert.Equal(3, witness.ConsumedChallenges);
        Assert.Equal(metadata, await f.Metadata());
        Assert.Equal(1L, await f.Scalar<long>("SELECT count(*) FROM public.app_session"));
        Assert.Equal(1L, await f.Scalar<long>("SELECT count(*) FROM public.app_mfa_challenge WHERE consumed_at IS NULL"));
        Assert.Equal(witness, await MfaRotationDatabase.ReadWitnessAsync(f.Db, f.Tx, f.Binding.OperationId, Ct));
        await MfaRotationDatabase.ValidateCommittedAsync(f.Db, f.Tx, witness, f.Provider, Ct);
        foreach (var user in users) await f.AuthenticateSameSecret(user);
    }

    [Fact(Skip = NeedLab, SkipUnless = nameof(Available))]
    public async Task EmptyCensusStillWritesWitnessWithoutRevokingAccountsWithoutFactor()
    {
        await using var f = await Fixture.Create();
        var user = await f.AddUser(); await f.AddSession(user); await f.AddChallenge(user, false);
        var witness = await MfaRotationDatabase.RewrapAsync(f.Db, f.Tx, f.Binding, f.Provider, f.Keys[8], Ct);
        Assert.Equal(new MfaRotationWitness(f.Binding, 0, 0, 0), witness);
        Assert.Equal(1L, await f.Scalar<long>("SELECT count(*) FROM public.app_session"));
        Assert.Equal(1L, await f.Scalar<long>("SELECT count(*) FROM public.app_mfa_challenge WHERE consumed_at IS NULL"));
        await MfaRotationDatabase.ValidateCommittedAsync(f.Db, f.Tx, witness, f.Provider, Ct);
    }

    [Fact(Skip = NeedLab, SkipUnless = nameof(Available))]
    public async Task ExistingWitnessCommandsReconciliationInsteadOfRepeatingCiphertextRewrite()
    {
        await using var f = await Fixture.Create(); await f.AddFactor("active", 1);
        var witness = await MfaRotationDatabase.RewrapAsync(f.Db, f.Tx, f.Binding, f.Provider, f.Keys[8], Ct);
        var committedHash = await MfaRotationDatabase.ReadSnapshotHashAsync(f.Db, f.Tx, Ct);
        await f.Tx.CommitAsync(Ct);
        await f.NewTransaction();
        Assert.Equal(witness, await MfaRotationDatabase.ReadWitnessAsync(f.Db, f.Tx, f.Binding.OperationId, Ct));
        var error = await Assert.ThrowsAsync<MfaMaintenanceException>(() =>
            MfaRotationDatabase.RewrapAsync(f.Db, f.Tx, f.Binding, f.Provider, f.Keys[8], Ct));
        Assert.Equal("mfa_rotation_witness_exists", error.Code);
        await f.NewTransaction();
        Assert.Equal(committedHash, await MfaRotationDatabase.ReadSnapshotHashAsync(f.Db, f.Tx, Ct));
        // This test committed only synthetic data in the explicit lab; restore it through fixture-owned rows.
        await f.RemoveCommittedRows();
    }

    [Fact(Skip = NeedLab, SkipUnless = nameof(Available))]
    public async Task CorruptCiphertextRollsBackEveryChangeAndCreatesNoWitness()
    {
        await using var f = await Fixture.Create(); await f.AddFactor("active", 1); var corrupt = await f.AddFactor("disabled", 7);
        await f.Execute("UPDATE public.app_mfa_factor SET secret_ciphertext=decode(repeat('00',48),'hex') WHERE user_id=@id", ("id", corrupt));
        var before = await MfaRotationDatabase.ReadSnapshotHashAsync(f.Db, f.Tx, Ct);
        await f.Tx.CommitAsync(Ct); await f.NewTransaction();
        await Assert.ThrowsAnyAsync<CryptographicException>(() => MfaRotationDatabase.RewrapAsync(f.Db, f.Tx, f.Binding, f.Provider, f.Keys[8], Ct));
        await f.NewTransaction();
        Assert.Equal(before, await MfaRotationDatabase.ReadSnapshotHashAsync(f.Db, f.Tx, Ct));
        Assert.Null(await MfaRotationDatabase.ReadWitnessAsync(f.Db, f.Tx, f.Binding.OperationId, Ct));
        await f.RemoveCommittedRows();
    }

    [Fact(Skip = NeedLab, SkipUnless = nameof(Available))]
    public async Task WitnessInsertionFailureRollsBackRewrapAndSecurityChanges()
    {
        await using var f = await Fixture.Create(); var user = await f.AddFactor("pending", 1);
        await f.AddSession(user); await f.AddChallenge(user, false);
        var before = await MfaRotationDatabase.ReadSnapshotHashAsync(f.Db, f.Tx, Ct);
        await f.Tx.CommitAsync(Ct); await f.NewTransaction();
        // Isolated transaction-only constraint forces the final INSERT to fail, without product hooks.
        await f.Execute("ALTER TABLE public.app_mfa_rotation_witness ADD CONSTRAINT f0603_force_witness_failure CHECK(factor_count < 0) NOT VALID");
        await Assert.ThrowsAsync<PostgresException>(() => MfaRotationDatabase.RewrapAsync(f.Db, f.Tx, f.Binding, f.Provider, f.Keys[8], Ct));
        await f.NewTransaction();
        Assert.Equal(before, await MfaRotationDatabase.ReadSnapshotHashAsync(f.Db, f.Tx, Ct));
        Assert.Null(await MfaRotationDatabase.ReadWitnessAsync(f.Db, f.Tx, f.Binding.OperationId, Ct));
        await f.RemoveCommittedRows();
    }

    [Fact(Skip = NeedLab, SkipUnless = nameof(Available))]
    public async Task RejectsMissingLocksBeforeReadingOrMutatingFactors()
    {
        await using var f = await Fixture.Create(); await f.Tx.RollbackAsync(Ct);
        f.Tx = await f.Db.BeginTransactionAsync(IsolationLevel.ReadCommitted, Ct);
        Assert.Equal("mfa_rotation_locks_required", (await Assert.ThrowsAsync<MfaMaintenanceException>(() =>
            MfaRotationDatabase.RewrapAsync(f.Db, f.Tx, f.Binding, f.Provider, f.Keys[8], Ct))).Code);
    }

    [Fact(Skip = NeedLab, SkipUnless = nameof(Available))]
    public async Task FactorLockBlocksAConcurrentInsertionAndSnapshotDetectsMetadataChanges()
    {
        await using var f = await Fixture.Create(); var user = await f.AddFactor("active", 1);
        var before = await MfaRotationDatabase.ReadSnapshotHashAsync(f.Db, f.Tx, Ct);
        await f.Execute("UPDATE public.app_mfa_factor SET failed_attempts=failed_attempts+1 WHERE user_id=@id", ("id", user));
        Assert.NotEqual(before, await MfaRotationDatabase.ReadSnapshotHashAsync(f.Db, f.Tx, Ct));
        await using var other = await f.Open();
        await using var tx = await other.BeginTransactionAsync(Ct);
        await using var command = new NpgsqlCommand("SET LOCAL lock_timeout='150ms'; LOCK TABLE public.app_mfa_factor IN ROW EXCLUSIVE MODE", other, tx);
        var error = await Assert.ThrowsAsync<PostgresException>(() => command.ExecuteNonQueryAsync(Ct));
        Assert.Equal(PostgresErrorCodes.LockNotAvailable, error.SqlState);
    }

    [Fact(Skip = NeedLab, SkipUnless = nameof(Available))]
    public async Task WrongSystemhausAndUnknownVersionAndWrongDatabaseBindingFailClosed()
    {
        await using var f = await Fixture.Create(); await f.AddFactor("disabled", 7);
        Assert.Equal("mfa_rotation_database_mismatch", (await Assert.ThrowsAsync<MfaMaintenanceException>(() =>
            MfaRotationDatabase.RewrapAsync(f.Db, f.Tx, f.Binding with { InstallationId = Guid.NewGuid() }, f.Provider, f.Keys[8], Ct))).Code);
        await f.NewTransaction();
        Assert.Equal("mfa_rotation_systemhaus_mismatch", (await Assert.ThrowsAsync<MfaMaintenanceException>(() =>
            MfaRotationDatabase.RewrapAsync(f.Db, f.Tx, f.Binding with { SystemhausId = Guid.NewGuid() }, f.Provider, f.Keys[8], Ct))).Code);
        await f.NewTransaction(); await f.AddFactor("pending", 7);
        var missing = new TestProvider(new Dictionary<int, byte[]> { [1] = f.Keys[1], [8] = f.Keys[8] });
        await Assert.ThrowsAsync<KeyNotFoundException>(() => MfaRotationDatabase.RewrapAsync(f.Db, f.Tx, f.Binding, missing, f.Keys[8], Ct));
    }

    [Fact(Skip = NeedLab, SkipUnless = nameof(Available))]
    public async Task CommittedValidationRejectsWrongKeyVersionCountAndSubstitutedBinding()
    {
        await using var f = await Fixture.Create(); var user = await f.AddFactor("disabled", 1);
        var witness = await MfaRotationDatabase.RewrapAsync(f.Db, f.Tx, f.Binding, f.Provider, f.Keys[8], Ct);
        Assert.Equal("mfa_rotation_witness_invalid", (await Assert.ThrowsAsync<MfaMaintenanceException>(() =>
            MfaRotationDatabase.ValidateCommittedAsync(f.Db, f.Tx, witness with { FactorCount = 2 }, f.Provider, Ct))).Code);
        Assert.Equal("mfa_rotation_witness_invalid", (await Assert.ThrowsAsync<MfaMaintenanceException>(() =>
            MfaRotationDatabase.ValidateCommittedAsync(f.Db, f.Tx, witness with { Binding = f.Binding with { EnvelopeHash = new string('7', 64) } }, f.Provider, Ct))).Code);
        await f.Execute("UPDATE public.app_mfa_factor SET key_version=1 WHERE user_id=@id", ("id", user));
        Assert.Equal("mfa_rotation_factor_invalid", (await Assert.ThrowsAsync<MfaMaintenanceException>(() =>
            MfaRotationDatabase.ValidateCommittedAsync(f.Db, f.Tx, witness, f.Provider, Ct))).Code);
    }

    [Fact(Skip = NeedLab, SkipUnless = nameof(Available))]
    public async Task ReusingAVersionFromAnyRetainedWitnessIsRejectedEvenWithZeroFactors()
    {
        await using var f = await Fixture.Create();
        await MfaRotationDatabase.RewrapAsync(f.Db, f.Tx, f.Binding, f.Provider, f.Keys[8], Ct);
        var next = f.Binding with { OperationId = Guid.NewGuid() };
        Assert.Equal("mfa_rotation_version_reused", (await Assert.ThrowsAsync<MfaMaintenanceException>(() =>
            MfaRotationDatabase.RewrapAsync(f.Db, f.Tx, next, f.Provider, f.Keys[8], Ct))).Code);
    }

    [Fact(Skip = NeedLab, SkipUnless = nameof(Available))]
    public async Task OversizedCiphertextIsRejectedWithoutDownloadingItOrCreatingWitness()
    {
        await using var f = await Fixture.Create(); var user = await f.AddFactor("pending", 1);
        await f.Execute("UPDATE public.app_mfa_factor SET secret_ciphertext=decode(repeat('01',16385),'hex') WHERE user_id=@id", ("id", user));
        Assert.Equal("mfa_rotation_factor_invalid", (await Assert.ThrowsAsync<MfaMaintenanceException>(() =>
            MfaRotationDatabase.RewrapAsync(f.Db, f.Tx, f.Binding, f.Provider, f.Keys[8], Ct))).Code);
    }

    private static MfaRotationBinding Binding(Guid installation, Guid house) => new(Guid.NewGuid(), installation, house,
        "S-1-5-21-101-102-103-1001", 1, 8, new string('1', 64), new string('2', 64), new string('3', 64),
        new string('4', 64), new string('5', 64), new string('6', 64));

    private sealed class TestProvider(Dictionary<int, byte[]> keys) : IMfaKeyProvider
    {
        public byte[] GetKey(int version) => keys[version].ToArray();
        public (int Version, byte[] Key) GetActiveKey() => (1, GetKey(1));
    }

    private sealed class Fixture : IAsyncDisposable
    {
        internal NpgsqlConnection Db = null!;
        internal NpgsqlTransaction Tx = null!;
        internal MfaRotationBinding Binding = null!;
        internal Dictionary<int, byte[]> Keys = new() { [1] = RandomNumberGenerator.GetBytes(32), [7] = RandomNumberGenerator.GetBytes(32), [8] = RandomNumberGenerator.GetBytes(32) };
        internal IMfaKeyProvider Provider => new TestProvider(Keys);
        private readonly Dictionary<Guid, byte[]> secrets = [];
        private readonly List<Guid> users = [];
        private string connection = "";

        internal static async Task<Fixture> Create()
        {
            using var json = JsonDocument.Parse(await File.ReadAllBytesAsync(Environment.GetEnvironmentVariable("RACKCLICK_F0603_CONTEXT")!, Ct));
            var context = json.RootElement;
            var installation = context.GetProperty("installationId").GetGuid();
            var settings = new NpgsqlConnectionStringBuilder(context.GetProperty("ownerConnection").GetString()!) { Pooling = false };
            if (installation == Guid.Empty || settings.Host != "127.0.0.1" || settings.Database != "rc_db_" + installation.ToString("N")
                || settings.Username != "rc_owner_" + installation.ToString("N") || string.IsNullOrEmpty(settings.Password))
                throw new InvalidOperationException("Explicit NEW F0603 loopback laboratory required");
            var f = new Fixture { connection = settings.ConnectionString };
            f.Db = await f.Open(); await f.NewTransaction();
            var house = await f.Scalar<Guid>("SELECT id FROM public.systemhaus");
            f.Binding = MfaRotationDatabaseTests.Binding(installation, house);
            // Test changes stay rollback-only except explicit transaction durability/rollback tests.
            await f.Execute("DELETE FROM public.app_mfa_rotation_witness; DELETE FROM public.app_session; DELETE FROM public.app_mfa_challenge; DELETE FROM public.app_mfa_factor");
            return f;
        }

        internal async Task<NpgsqlConnection> Open()
        { var result = new NpgsqlConnection(connection); await result.OpenAsync(Ct); return result; }
        internal async Task NewTransaction()
        {
            if (Tx is not null) await Tx.DisposeAsync();
            Tx = await Db.BeginTransactionAsync(IsolationLevel.ReadCommitted, Ct);
            await MfaRotationDatabase.LockAsync(Db, Tx, Ct);
        }
        internal async Task Execute(string sql, params (string Name, object Value)[] parameters)
        { await using var command = new NpgsqlCommand(sql, Db, Tx); foreach (var p in parameters) command.Parameters.AddWithValue(p.Name, p.Value); await command.ExecuteNonQueryAsync(Ct); }
        internal async Task<T> Scalar<T>(string sql)
        { await using var command = new NpgsqlCommand(sql, Db, Tx); return (T)(await command.ExecuteScalarAsync(Ct))!; }
        internal async Task<Guid> AddUser()
        {
            var id = Guid.NewGuid(); users.Add(id);
            await Execute("INSERT INTO public.app_user(id,systemhaus_id,username,password_hash) VALUES(@id,@house,@name,'synthetic-not-a-password')", ("id", id), ("house", Binding.SystemhausId), ("name", "f0603-" + id.ToString("N")));
            return id;
        }
        internal async Task<Guid> AddFactor(string state, int version)
        {
            var user = await AddUser(); var secret = MfaTotp.NewSecret(); secrets.Add(user, secret);
            var cipher = MfaSecretCipher.Seal(Keys[version], version, secret, Binding.SystemhausId, user);
            try
            {
                await Execute("""
                    INSERT INTO public.app_mfa_factor(systemhaus_id,user_id,state,secret_ciphertext,key_version,last_time_step,
                        failed_attempts,locked_until,created_at,confirmed_at)
                    VALUES(@house,@user,@state,@cipher,@version,1234567,3,'2026-11-11T00:00:00Z','2026-10-01T00:00:00Z','2026-10-02T00:00:00Z');
                    INSERT INTO public.app_mfa_user(systemhaus_id,user_id,mfa_required,enrollment_pending,revision)
                    VALUES(@house,@user,true,false,17);
                    INSERT INTO public.app_mfa_recovery_code(systemhaus_id,user_id,code_hash) VALUES(@house,@user,@hash)
                    """, ("house", Binding.SystemhausId), ("user", user), ("state", state), ("cipher", cipher), ("version", version), ("hash", Guid.NewGuid().ToString("N")));
            }
            finally { CryptographicOperations.ZeroMemory(cipher); }
            return user;
        }
        internal Task AddSession(Guid user) => Execute("INSERT INTO public.app_session(token_hash,user_id,csrf_hash,expires_at) VALUES(@token,@user,@csrf,clock_timestamp()+interval '1 hour')",
            ("token", Guid.NewGuid().ToString("N")), ("user", user), ("csrf", Guid.NewGuid().ToString("N")));
        internal Task AddChallenge(Guid user, bool consumed) => Execute("""
            INSERT INTO public.app_mfa_challenge(token_hash,systemhaus_id,user_id,purpose,csrf_hash,created_at,expires_at,consumed_at,attempts)
            VALUES(@token,@house,@user,'verify',@csrf,now(),now()+interval '3 minutes',CASE WHEN @consumed THEN now() ELSE NULL END,CASE WHEN @consumed THEN 5 ELSE 2 END)
            """, ("token", Guid.NewGuid().ToString("N")), ("house", Binding.SystemhausId), ("user", user), ("csrf", Guid.NewGuid().ToString("N")), ("consumed", consumed));
        internal Task<string> Metadata() => Scalar<string>("""
            SELECT jsonb_build_object(
              'factors',(SELECT jsonb_agg(to_jsonb(f)-'secret_ciphertext'-'key_version' ORDER BY user_id) FROM public.app_mfa_factor f),
              'users',(SELECT jsonb_agg(to_jsonb(u) ORDER BY id) FROM public.app_user u),
              'policy',(SELECT jsonb_agg(to_jsonb(p) ORDER BY user_id) FROM public.app_mfa_user p),
              'recovery',(SELECT jsonb_agg(to_jsonb(r) ORDER BY user_id,code_hash) FROM public.app_mfa_recovery_code r),
              'alreadyConsumedChallenges',(SELECT jsonb_agg(to_jsonb(c) ORDER BY token_hash) FROM public.app_mfa_challenge c WHERE attempts=5),
              'house',(SELECT jsonb_agg(to_jsonb(h) ORDER BY id) FROM public.systemhaus h))::text
            """);
        internal async Task AuthenticateSameSecret(Guid user)
        {
            await using var command = new NpgsqlCommand("SELECT key_version,secret_ciphertext FROM public.app_mfa_factor WHERE user_id=@user", Db, Tx);
            command.Parameters.AddWithValue("user", user);
            await using var rows = await command.ExecuteReaderAsync(Ct); Assert.True(await rows.ReadAsync(Ct)); Assert.Equal(8, rows.GetInt32(0));
            var plain = MfaSecretCipher.Open(Keys[8], 8, rows.GetFieldValue<byte[]>(1), Binding.SystemhausId, user);
            try { Assert.Equal(secrets[user], plain); } finally { CryptographicOperations.ZeroMemory(plain); }
        }
        internal async Task RemoveCommittedRows()
        {
            foreach (var id in users)
                await Execute("DELETE FROM public.app_mfa_challenge WHERE user_id=@id; DELETE FROM public.app_session WHERE user_id=@id; DELETE FROM public.app_mfa_recovery_code WHERE user_id=@id; DELETE FROM public.app_mfa_user WHERE user_id=@id; DELETE FROM public.app_mfa_factor WHERE user_id=@id; DELETE FROM public.app_user WHERE id=@id", ("id", id));
            await Execute("DELETE FROM public.app_mfa_rotation_witness WHERE operation_id=@id", ("id", Binding.OperationId));
            await Tx.CommitAsync(Ct);
        }
        public async ValueTask DisposeAsync()
        {
            if (Tx is not null) await Tx.DisposeAsync();
            if (Db is not null) await Db.DisposeAsync();
            foreach (var bytes in Keys.Values.Concat(secrets.Values)) CryptographicOperations.ZeroMemory(bytes);
        }
    }
}
