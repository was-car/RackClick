using System.Security.Cryptography;
using Npgsql;
using OtpNet;
using RackClick.Domain;
using RackClick.Server;
using Xunit;

namespace RackClick.Quality.Tests;

// Enrolamiento TOTP restringido (MFA-L1) contra PostgreSQL 17 real.
// Se ejecutan solo si RACKCLICK_TEST_PG_ADMIN apunta a un servidor de laboratorio con rol que pueda crear bases.
// Crean una base temporal propia, aplican 001–015 desde la copia de database/ del proyecto y la eliminan al terminar.
// No modifican ni reutilizan las pruebas históricas de MfaStoreTests.
public sealed class MfaEnrollmentTests
{
    private const string AdminVariable = "RACKCLICK_TEST_PG_ADMIN";
    private const string EnrollUser = "usuario-enrolamiento";
    private const string VerifyUser = "usuario-con-factor";
    private static readonly string Password = "RcTest-" + Convert.ToHexString(System.Security.Cryptography.RandomNumberGenerator.GetBytes(24));

    [Fact]
    public async Task LoginWithoutFactorIssuesRestrictedEnrollChallengeAndNoSession()
    {
        await using var env = await EnrollmentDatabase.CreateAsync();
        await env.CreateUserAsync(EnrollUser, mfaRequired: true, withActiveFactor: false);

        var outcome = await env.Store(mfaAvailable: true).AuthenticateForLogin(EnrollUser, Password, TestContext.Current.CancellationToken);

        Assert.Null(outcome.Session);
        Assert.NotNull(outcome.Challenge);
        Assert.Equal("enroll", outcome.ChallengePurpose);
        Assert.Equal(0, await env.CountAsync("SELECT count(*) FROM app_session"));
        Assert.Equal(1, await env.CountAsync("SELECT count(*) FROM app_mfa_challenge WHERE purpose='enroll' AND consumed_at IS NULL"));
    }

    [Fact]
    public async Task HistoricAuthenticateKeepsItsEnrollmentRejectionWithoutChallenge()
    {
        await using var env = await EnrollmentDatabase.CreateAsync();
        await env.CreateUserAsync(EnrollUser, mfaRequired: true, withActiveFactor: false);

        var error = await Assert.ThrowsAsync<DomainError>(() => env.Store(mfaAvailable: true).Authenticate(EnrollUser, Password, TestContext.Current.CancellationToken));

        Assert.Equal("mfa_enrollment_required", error.Message);
        Assert.Equal(0, await env.CountAsync("SELECT count(*) FROM app_mfa_challenge"));
        Assert.Equal(0, await env.CountAsync("SELECT count(*) FROM app_session"));
    }

    [Fact]
    public async Task WithoutProviderLoginRejectsEnrollmentExplicitlyAndIssuesNothing()
    {
        await using var env = await EnrollmentDatabase.CreateAsync();
        await env.CreateUserAsync(EnrollUser, mfaRequired: true, withActiveFactor: false);

        var error = await Assert.ThrowsAsync<DomainError>(() => env.Store(mfaAvailable: false).AuthenticateForLogin(EnrollUser, Password, TestContext.Current.CancellationToken));

        Assert.Equal("mfa_enrollment_required", error.Message);
        Assert.Equal(0, await env.CountAsync("SELECT count(*) FROM app_mfa_challenge"));
        Assert.Equal(0, await env.CountAsync("SELECT count(*) FROM app_session"));
    }

    [Fact]
    public async Task StartRequiresValidCsrfAndStoresOnlyAPendingFactor()
    {
        await using var env = await EnrollmentDatabase.CreateAsync();
        await env.CreateUserAsync(EnrollUser, mfaRequired: true, withActiveFactor: false);
        var store = env.Store(mfaAvailable: true);
        var (token, csrf) = await env.EnrollChallengeAsync(store);
        var ct = TestContext.Current.CancellationToken;

        var wrong = await Assert.ThrowsAsync<DomainError>(() => env.Enrollment().StartEnrollment(token, "no-es-el-csrf", ct));
        Assert.Equal("csrf_invalid", wrong.Message);
        Assert.Equal(0, await env.CountAsync("SELECT count(*) FROM app_mfa_factor"));
        Assert.Equal(1, await env.CountAsync("SELECT count(*) FROM app_mfa_challenge WHERE purpose='enroll' AND consumed_at IS NULL"));

        var start = await env.Enrollment().StartEnrollment(token, csrf, ct);
        Assert.Matches("^[A-Z2-7]+$", start.SecretBase32);
        Assert.StartsWith("otpauth://totp/", start.OtpAuthUri);
        Assert.Contains("algorithm=SHA1&digits=6&period=30", start.OtpAuthUri);
        Assert.Equal("pending", await env.ScalarTextAsync("SELECT state FROM app_mfa_factor"));
        Assert.Equal(0, await env.CountAsync("SELECT count(*) FROM app_session"));
    }

    [Fact]
    public async Task ConfirmActivatesFactorIssuesOneSessionAndCannotBeReplayed()
    {
        await using var env = await EnrollmentDatabase.CreateAsync();
        await env.CreateUserAsync(EnrollUser, mfaRequired: true, withActiveFactor: false);
        var store = env.Store(mfaAvailable: true);
        var (token, csrf) = await env.EnrollChallengeAsync(store);
        var ct = TestContext.Current.CancellationToken;
        var start = await env.Enrollment().StartEnrollment(token, csrf, ct);
        var code = MfaTotp.Compute(Base32Encoding.ToBytes(start.SecretBase32), DateTimeOffset.UtcNow);

        var (sessionToken, sessionCsrf) = await env.Enrollment().ConfirmEnrollment(token, code, csrf, ct);

        Assert.False(string.IsNullOrEmpty(sessionToken));
        Assert.False(string.IsNullOrEmpty(sessionCsrf));
        Assert.Equal("active", await env.ScalarTextAsync("SELECT state FROM app_mfa_factor"));
        Assert.False(await env.ScalarBoolAsync("SELECT enrollment_pending FROM app_mfa_user"));
        Assert.Equal(1, await env.CountAsync("SELECT count(*) FROM app_session WHERE mfa_verified_at IS NOT NULL"));
        Assert.Equal(0, await env.CountAsync("SELECT count(*) FROM app_mfa_challenge WHERE consumed_at IS NULL"));

        var replay = await Assert.ThrowsAsync<DomainError>(() => env.Enrollment().ConfirmEnrollment(token, code, csrf, ct));
        Assert.Equal("mfa_challenge_invalid", replay.Message);
        Assert.Equal(1, await env.CountAsync("SELECT count(*) FROM app_session"));
    }

    [Fact]
    public async Task WrongCodeCountsAndOpensNoSession()
    {
        await using var env = await EnrollmentDatabase.CreateAsync();
        await env.CreateUserAsync(EnrollUser, mfaRequired: true, withActiveFactor: false);
        var store = env.Store(mfaAvailable: true);
        var (token, csrf) = await env.EnrollChallengeAsync(store);
        var ct = TestContext.Current.CancellationToken;
        var start = await env.Enrollment().StartEnrollment(token, csrf, ct);
        var secret = Base32Encoding.ToBytes(start.SecretBase32);
        var wrong = MfaTotp.Compute(secret, DateTimeOffset.UtcNow) == "000000" ? "111111" : "000000";

        var error = await Assert.ThrowsAsync<DomainError>(() => env.Enrollment().ConfirmEnrollment(token, wrong, csrf, ct));

        Assert.Equal("mfa_code_invalid", error.Message);
        Assert.Equal(0, await env.CountAsync("SELECT count(*) FROM app_session"));
        Assert.Equal("pending", await env.ScalarTextAsync("SELECT state FROM app_mfa_factor"));
        Assert.Equal(1, await env.CountAsync("SELECT failed_attempts FROM app_mfa_factor"));
        Assert.Equal(1, await env.CountAsync("SELECT attempts FROM app_mfa_challenge"));
        Assert.Equal(1, await env.CountAsync("SELECT count(*) FROM app_mfa_challenge WHERE consumed_at IS NULL"));
    }

    [Fact]
    public async Task VerifyAndEnrollChallengesAreNotInterchangeable()
    {
        await using var env = await EnrollmentDatabase.CreateAsync();
        await env.CreateUserAsync(VerifyUser, mfaRequired: true, withActiveFactor: true);
        await env.CreateUserAsync(EnrollUser, mfaRequired: true, withActiveFactor: false);
        var store = env.Store(mfaAvailable: true);
        var ct = TestContext.Current.CancellationToken;
        var verify = (await store.AuthenticateForLogin(VerifyUser, Password, ct)).Challenge!.Value;
        var enroll = (await store.AuthenticateForLogin(EnrollUser, Password, ct)).Challenge!.Value;

        var verifyAsEnroll = await Assert.ThrowsAsync<DomainError>(() => env.Enrollment().StartEnrollment(verify.Token, verify.Csrf, ct));
        Assert.Equal("mfa_challenge_invalid", verifyAsEnroll.Message);

        var enrollAsVerify = await Assert.ThrowsAsync<DomainError>(() => env.Verifier().CompleteVerify(enroll.Token, "000000", enroll.Csrf, ct));
        Assert.Equal("mfa_challenge_invalid", enrollAsVerify.Message);
        Assert.Equal(0, await env.CountAsync("SELECT count(*) FROM app_session"));
    }

    [Fact]
    public async Task PolicyChangeAfterStartCancelsConfirmation()
    {
        await using var env = await EnrollmentDatabase.CreateAsync();
        await env.CreateUserAsync(EnrollUser, mfaRequired: true, withActiveFactor: false);
        var store = env.Store(mfaAvailable: true);
        var (token, csrf) = await env.EnrollChallengeAsync(store);
        var ct = TestContext.Current.CancellationToken;
        var start = await env.Enrollment().StartEnrollment(token, csrf, ct);
        var code = MfaTotp.Compute(Base32Encoding.ToBytes(start.SecretBase32), DateTimeOffset.UtcNow);
        await env.ExecuteAsync("UPDATE app_mfa_user SET revision = revision + 1");

        var error = await Assert.ThrowsAsync<DomainError>(() => env.Enrollment().ConfirmEnrollment(token, code, csrf, ct));

        Assert.Equal("mfa_challenge_invalid", error.Message);
        Assert.Equal(0, await env.CountAsync("SELECT count(*) FROM app_session"));
        Assert.Equal("pending", await env.ScalarTextAsync("SELECT state FROM app_mfa_factor"));
        Assert.Equal(0, await env.CountAsync("SELECT count(*) FROM app_mfa_challenge WHERE consumed_at IS NULL"));
    }

    [Fact]
    public async Task ExpiredEnrollChallengeIsRejectedAndBurned()
    {
        await using var env = await EnrollmentDatabase.CreateAsync();
        await env.CreateUserAsync(EnrollUser, mfaRequired: true, withActiveFactor: false);
        var store = env.Store(mfaAvailable: true);
        var (token, csrf) = await env.EnrollChallengeAsync(store);
        var ct = TestContext.Current.CancellationToken;
        await env.ExecuteAsync("UPDATE app_mfa_challenge SET expires_at = now() - interval '1 second'");

        var error = await Assert.ThrowsAsync<DomainError>(() => env.Enrollment().StartEnrollment(token, csrf, ct));

        Assert.Equal("mfa_challenge_invalid", error.Message);
        Assert.Equal(0, await env.CountAsync("SELECT count(*) FROM app_mfa_factor"));
        Assert.Equal(0, await env.CountAsync("SELECT count(*) FROM app_mfa_challenge WHERE consumed_at IS NULL"));
    }

    [Fact]
    public async Task WrongCodesAccumulateAcrossChallengesAndLockAfterFive()
    {
        await using var env = await EnrollmentDatabase.CreateAsync();
        await env.CreateUserAsync(EnrollUser, mfaRequired: true, withActiveFactor: false);
        var store = env.Store(mfaAvailable: true);
        var ct = TestContext.Current.CancellationToken;
        for (var attempt = 1; attempt <= 5; attempt++)
        {
            var (token, csrf) = await env.EnrollChallengeAsync(store);
            await env.Enrollment().StartEnrollment(token, csrf, ct);
            var error = await Assert.ThrowsAsync<DomainError>(() => env.Enrollment().ConfirmEnrollment(token, "000000", csrf, ct));
            Assert.Equal("mfa_code_invalid", error.Message);
        }

        Assert.Equal(5, await env.CountAsync("SELECT failed_attempts FROM app_mfa_factor"));
        Assert.Equal(1, await env.CountAsync("SELECT count(*) FROM app_mfa_factor WHERE locked_until > clock_timestamp()"));
        Assert.Equal(0, await env.CountAsync("SELECT count(*) FROM app_session"));
    }

    [Fact]
    public async Task NewChallengeAndStartCannotReopenALockedFactor()
    {
        await using var env = await EnrollmentDatabase.CreateAsync();
        await env.CreateUserAsync(EnrollUser, mfaRequired: true, withActiveFactor: false);
        var store = env.Store(mfaAvailable: true);
        var ct = TestContext.Current.CancellationToken;
        var (token, csrf) = await env.EnrollChallengeAsync(store);
        var start = await env.Enrollment().StartEnrollment(token, csrf, ct);
        await env.ExecuteAsync("UPDATE app_mfa_factor SET failed_attempts = 5, locked_until = now() + interval '15 minutes'");
        var code = MfaTotp.Compute(Base32Encoding.ToBytes(start.SecretBase32), DateTimeOffset.UtcNow);

        var (newToken, newCsrf) = await env.EnrollChallengeAsync(store);
        var restart = await Assert.ThrowsAsync<DomainError>(() => env.Enrollment().StartEnrollment(newToken, newCsrf, ct));
        Assert.Equal("mfa_challenge_invalid", restart.Message);
        var confirm = await Assert.ThrowsAsync<DomainError>(() => env.Enrollment().ConfirmEnrollment(newToken, code, newCsrf, ct));
        Assert.Equal("mfa_challenge_invalid", confirm.Message);

        Assert.Equal(5, await env.CountAsync("SELECT failed_attempts FROM app_mfa_factor"));
        Assert.Equal(1, await env.CountAsync("SELECT count(*) FROM app_mfa_factor WHERE locked_until > clock_timestamp()"));
        Assert.Equal(0, await env.CountAsync("SELECT count(*) FROM app_session"));
    }

    [Fact]
    public async Task ExpiredLockAllowsRecoveryWithAValidCode()
    {
        await using var env = await EnrollmentDatabase.CreateAsync();
        await env.CreateUserAsync(EnrollUser, mfaRequired: true, withActiveFactor: false);
        var store = env.Store(mfaAvailable: true);
        var ct = TestContext.Current.CancellationToken;
        var (token, csrf) = await env.EnrollChallengeAsync(store);
        await env.Enrollment().StartEnrollment(token, csrf, ct);
        await env.ExecuteAsync("UPDATE app_mfa_factor SET failed_attempts = 5, locked_until = now() - interval '1 second'");
        var (newToken, newCsrf) = await env.EnrollChallengeAsync(store);
        var restarted = await env.Enrollment().StartEnrollment(newToken, newCsrf, ct);
        var recoveredCode = MfaTotp.Compute(Base32Encoding.ToBytes(restarted.SecretBase32), DateTimeOffset.UtcNow);

        var (sessionToken, _) = await env.Enrollment().ConfirmEnrollment(newToken, recoveredCode, newCsrf, ct);

        Assert.False(string.IsNullOrEmpty(sessionToken));
        Assert.Equal("active", await env.ScalarTextAsync("SELECT state FROM app_mfa_factor"));
        Assert.Equal(0, await env.CountAsync("SELECT failed_attempts FROM app_mfa_factor"));
    }

    [Fact]
    public async Task ChallengeExpiringWhileConfirmWaitsForPolicyLockIsRejected()
    {
        await using var env = await EnrollmentDatabase.CreateAsync();
        await env.CreateUserAsync(EnrollUser, mfaRequired: true, withActiveFactor: false);
        var store = env.Store(mfaAvailable: true);
        var ct = TestContext.Current.CancellationToken;
        var (token, csrf) = await env.EnrollChallengeAsync(store);
        var start = await env.Enrollment().StartEnrollment(token, csrf, ct);
        var code = MfaTotp.Compute(Base32Encoding.ToBytes(start.SecretBase32), DateTimeOffset.UtcNow);
        await env.ExecuteAsync("UPDATE app_mfa_challenge SET expires_at = clock_timestamp() + interval '1500 milliseconds'");

        await using var holder = await env.Source().OpenConnectionAsync(ct);
        await using var tx = await holder.BeginTransactionAsync(ct);
        await using (var lockPolicy = new NpgsqlCommand("SELECT 1 FROM app_mfa_user FOR SHARE", holder, tx))
            await lockPolicy.ExecuteScalarAsync(ct);
        var confirm = env.Enrollment().ConfirmEnrollment(token, code, csrf, ct);
        await Task.Delay(TimeSpan.FromSeconds(3), ct);
        await tx.CommitAsync(ct);

        var error = await Assert.ThrowsAsync<DomainError>(() => confirm);
        Assert.Equal("mfa_challenge_invalid", error.Message);
        Assert.Equal(0, await env.CountAsync("SELECT count(*) FROM app_session"));
        Assert.Equal("pending", await env.ScalarTextAsync("SELECT state FROM app_mfa_factor"));
    }

    [Fact]
    public async Task CrossPurposeUseDoesNotConsumeTheValidChallenge()
    {
        await using var env = await EnrollmentDatabase.CreateAsync();
        await env.CreateUserAsync(VerifyUser, mfaRequired: true, withActiveFactor: true);
        var store = env.Store(mfaAvailable: true);
        var ct = TestContext.Current.CancellationToken;
        var verify = (await store.AuthenticateForLogin(VerifyUser, Password, ct)).Challenge!.Value;

        var misuse = await Assert.ThrowsAsync<DomainError>(() => env.Enrollment().StartEnrollment(verify.Token, verify.Csrf, ct));
        Assert.Equal("mfa_challenge_invalid", misuse.Message);
        Assert.Equal(1, await env.CountAsync("SELECT count(*) FROM app_mfa_challenge WHERE purpose='verify' AND consumed_at IS NULL"));

        var code = MfaTotp.Compute(env.SecretOf(VerifyUser), DateTimeOffset.UtcNow);
        var (sessionToken, _) = await env.Verifier().CompleteVerify(verify.Token, code, verify.Csrf, ct);
        Assert.False(string.IsNullOrEmpty(sessionToken));
        Assert.Equal(1, await env.CountAsync("SELECT count(*) FROM app_session"));
    }

    [Fact]
    public async Task EnrollmentWritesMinimalAuditWithoutSecrets()
    {
        await using var env = await EnrollmentDatabase.CreateAsync();
        await env.CreateUserAsync(EnrollUser, mfaRequired: true, withActiveFactor: false);
        var store = env.Store(mfaAvailable: true);
        var ct = TestContext.Current.CancellationToken;
        var (token, csrf) = await env.EnrollChallengeAsync(store);
        var start = await env.Enrollment().StartEnrollment(token, csrf, ct);
        var code = MfaTotp.Compute(Base32Encoding.ToBytes(start.SecretBase32), DateTimeOffset.UtcNow);
        await env.Enrollment().ConfirmEnrollment(token, code, csrf, ct);

        Assert.Equal(1, await env.CountAsync("SELECT count(*) FROM audit_event WHERE action='auth.mfa.enrollment_started'"));
        Assert.Equal(1, await env.CountAsync("SELECT count(*) FROM audit_event WHERE action='auth.mfa.enrollment_confirmed'"));
        Assert.Equal(0, await env.CountAsync("SELECT count(*) FROM audit_event WHERE after_json::text ILIKE '%otpauth%' OR after_json::text ILIKE '%secret%' OR after_json::text ILIKE '%csrf%' OR after_json::text ILIKE '%" + "\"" + "code%'"));
    }

    [Fact]
    public async Task ForcedAuditFailureRollsBackTheWholeConfirmation()
    {
        await using var env = await EnrollmentDatabase.CreateAsync();
        await env.CreateUserAsync(EnrollUser, mfaRequired: true, withActiveFactor: false);
        var store = env.Store(mfaAvailable: true);
        var ct = TestContext.Current.CancellationToken;
        var (token, csrf) = await env.EnrollChallengeAsync(store);
        var start = await env.Enrollment().StartEnrollment(token, csrf, ct);
        var code = MfaTotp.Compute(Base32Encoding.ToBytes(start.SecretBase32), DateTimeOffset.UtcNow);
        var revisionBefore = await env.CountAsync("SELECT revision FROM app_mfa_user");
        await env.ExecuteAsync("CREATE FUNCTION rc_fail_mfa_audit() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF NEW.action = 'auth.mfa.enrollment_confirmed' THEN RAISE EXCEPTION 'auditoria forzada a fallar'; END IF; RETURN NEW; END $$;"
            + " CREATE TRIGGER rc_fail_mfa_audit BEFORE INSERT ON audit_event FOR EACH ROW EXECUTE FUNCTION rc_fail_mfa_audit();");

        await Assert.ThrowsAnyAsync<Exception>(() => env.Enrollment().ConfirmEnrollment(token, code, csrf, ct));

        Assert.Equal("pending", await env.ScalarTextAsync("SELECT state FROM app_mfa_factor"));
        Assert.Equal(revisionBefore, await env.CountAsync("SELECT revision FROM app_mfa_user"));
        Assert.Equal(0, await env.CountAsync("SELECT count(*) FROM app_session"));
        Assert.Equal(1, await env.CountAsync("SELECT count(*) FROM app_mfa_challenge WHERE consumed_at IS NULL"));
        Assert.Equal(0, await env.CountAsync("SELECT count(*) FROM audit_event WHERE action='auth.mfa.enrollment_confirmed'"));
        Assert.Equal(1, await env.CountAsync("SELECT count(*) FROM audit_event WHERE action='auth.mfa.enrollment_started'"));
    }

    [Fact]
    public async Task ConcurrentConfirmWithTheSameCodeOpensExactlyOneSession()
    {
        await using var env = await EnrollmentDatabase.CreateAsync();
        await env.CreateUserAsync(EnrollUser, mfaRequired: true, withActiveFactor: false);
        var store = env.Store(mfaAvailable: true);
        var ct = TestContext.Current.CancellationToken;
        var (token, csrf) = await env.EnrollChallengeAsync(store);
        var start = await env.Enrollment().StartEnrollment(token, csrf, ct);
        var code = MfaTotp.Compute(Base32Encoding.ToBytes(start.SecretBase32), DateTimeOffset.UtcNow);

        var outcomes = await Task.WhenAll(
            Attempt(() => env.Enrollment().ConfirmEnrollment(token, code, csrf, ct)),
            Attempt(() => env.Enrollment().ConfirmEnrollment(token, code, csrf, ct)));

        Assert.Equal(1, outcomes.Count(o => o == "ok"));
        Assert.Equal(1, outcomes.Count(o => o == "mfa_challenge_invalid"));
        Assert.Equal(1, await env.CountAsync("SELECT count(*) FROM app_session"));
    }

    [Fact]
    public async Task RevocationDuringConfirmationLeavesNoSession()
    {
        await using var env = await EnrollmentDatabase.CreateAsync();
        await env.CreateUserAsync(EnrollUser, mfaRequired: true, withActiveFactor: false);
        var store = env.Store(mfaAvailable: true);
        var ct = TestContext.Current.CancellationToken;
        var (token, csrf) = await env.EnrollChallengeAsync(store);
        var start = await env.Enrollment().StartEnrollment(token, csrf, ct);
        var code = MfaTotp.Compute(Base32Encoding.ToBytes(start.SecretBase32), DateTimeOffset.UtcNow);
        var userId = await env.CountAsync("SELECT count(*) FROM app_user");

        await using var holder = await env.Source().OpenConnectionAsync(ct);
        await using var tx = await holder.BeginTransactionAsync(ct);
        await using (var lockAccount = new NpgsqlCommand("UPDATE app_user SET password_hash = password_hash", holder, tx))
            await lockAccount.ExecuteNonQueryAsync(ct);
        await MfaStore.RevokePendingChallenges(holder, tx, await env.SystemhausIdAsync(), await env.UserIdAsync(EnrollUser), ct);
        var confirm = env.Enrollment().ConfirmEnrollment(token, code, csrf, ct);
        await Task.Delay(TimeSpan.FromSeconds(2), ct);
        await tx.CommitAsync(ct);

        var error = await Assert.ThrowsAsync<DomainError>(() => confirm);
        Assert.Equal("mfa_challenge_invalid", error.Message);
        Assert.Equal(0, await env.CountAsync("SELECT count(*) FROM app_session"));
        Assert.Equal("pending", await env.ScalarTextAsync("SELECT state FROM app_mfa_factor"));
        Assert.Equal(1, userId);
    }

    private static async Task<string> Attempt(Func<Task<(string Token, string Csrf)>> call)
    {
        try
        {
            await call();
            return "ok";
        }
        catch (DomainError error)
        {
            return error.Message;
        }
    }

    private sealed class EnrollmentDatabase : IAsyncDisposable
    {
        private readonly string _database;
        private readonly string _adminConnection;
        private readonly byte[] _key = RandomNumberGenerator.GetBytes(MfaSecretCipher.KeyBytes);
        private NpgsqlDataSource? _source;
        private readonly Dictionary<string, byte[]> _secrets = new();

        private EnrollmentDatabase(string database, string adminConnection)
        {
            _database = database;
            _adminConnection = adminConnection;
        }

        public static async Task<EnrollmentDatabase> CreateAsync()
        {
            var admin = Environment.GetEnvironmentVariable(AdminVariable);
            Assert.SkipWhen(string.IsNullOrWhiteSpace(admin), AdminVariable + " no está definido: prueba PostgreSQL omitida.");
            var database = "rc_mfa_enroll_" + Guid.NewGuid().ToString("N");
            await using (var connection = new NpgsqlConnection(admin))
            {
                await connection.OpenAsync();
                await using var create = new NpgsqlCommand($"CREATE DATABASE {database} ENCODING 'UTF8' TEMPLATE template0", connection);
                await create.ExecuteNonQueryAsync();
            }
            var environment = new EnrollmentDatabase(database, admin!);
            await environment.ApplyMigrationsAsync();
            return environment;
        }

        internal NpgsqlDataSource Source()
        {
            if (_source is not null) return _source;
            var builder = new NpgsqlConnectionStringBuilder(_adminConnection) { Database = _database };
            _source = NpgsqlDataSource.Create(builder.ConnectionString);
            return _source;
        }

        internal async Task<Guid> SystemhausIdAsync()
        {
            await using var connection = await Source().OpenConnectionAsync(TestContext.Current.CancellationToken);
            await using var command = new NpgsqlCommand("SELECT id FROM systemhaus LIMIT 1", connection);
            return (Guid)(await command.ExecuteScalarAsync(TestContext.Current.CancellationToken) ?? Guid.Empty);
        }

        internal async Task<Guid> UserIdAsync(string username)
        {
            await using var connection = await Source().OpenConnectionAsync(TestContext.Current.CancellationToken);
            await using var command = new NpgsqlCommand("SELECT id FROM app_user WHERE username=@name", connection);
            command.Parameters.AddWithValue("name", username);
            return (Guid)(await command.ExecuteScalarAsync(TestContext.Current.CancellationToken) ?? Guid.Empty);
        }

        internal byte[] SecretOf(string username) => _secrets[username];

        internal PostgresStore Store(bool mfaAvailable) => new(Source()) { MfaAvailable = mfaAvailable };
        internal MfaStore Enrollment() => new(Source(), new StaticKeys(_key));
        internal MfaStore Verifier() => new(Source(), new StaticKeys(_key));

        // Login real con contraseña válida: emite el desafío de enrolamiento restringido.
        internal async Task<(string Token, string Csrf)> EnrollChallengeAsync(PostgresStore store)
        {
            var outcome = await store.AuthenticateForLogin(EnrollUser, Password, TestContext.Current.CancellationToken);
            var challenge = outcome.Challenge ?? throw new InvalidOperationException("el login no emitió desafío de enrolamiento");
            return (challenge.Token, challenge.Csrf);
        }

        internal async Task CreateUserAsync(string username, bool mfaRequired, bool withActiveFactor)
        {
            var systemhaus = await SystemhausAsync();
            var user = Guid.NewGuid();
            var secret = MfaTotp.NewSecret();
            _secrets[username] = secret;
            await ExecuteAsync(
                "INSERT INTO app_user(id,systemhaus_id,username,password_hash) VALUES(@user,@sh,@name,@hash)",
                ("user", user), ("sh", systemhaus), ("name", username), ("hash", Secrets.PasswordHash(username, Password)));
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
            await using var insert = new NpgsqlCommand("INSERT INTO systemhaus(id,name) VALUES(@sh,'Lab MFA enrolamiento')", connection);
            insert.Parameters.AddWithValue("sh", id);
            await insert.ExecuteNonQueryAsync(TestContext.Current.CancellationToken);
            return id;
        }

        public async Task<long> CountAsync(string sql)
        {
            await using var connection = await Source().OpenConnectionAsync(TestContext.Current.CancellationToken);
            await using var command = new NpgsqlCommand(sql, connection);
            return Convert.ToInt64(await command.ExecuteScalarAsync(TestContext.Current.CancellationToken) ?? 0L);
        }

        public async Task<string> ScalarTextAsync(string sql)
        {
            await using var connection = await Source().OpenConnectionAsync(TestContext.Current.CancellationToken);
            await using var command = new NpgsqlCommand(sql, connection);
            return (string)(await command.ExecuteScalarAsync(TestContext.Current.CancellationToken) ?? "");
        }

        public async Task<bool> ScalarBoolAsync(string sql)
        {
            await using var connection = await Source().OpenConnectionAsync(TestContext.Current.CancellationToken);
            await using var command = new NpgsqlCommand(sql, connection);
            return (bool)(await command.ExecuteScalarAsync(TestContext.Current.CancellationToken) ?? false);
        }

        public async Task ExecuteAsync(string sql, params (string Name, object Value)[] values)
        {
            await using var connection = await Source().OpenConnectionAsync(TestContext.Current.CancellationToken);
            await using var command = new NpgsqlCommand(sql, connection);
            foreach (var (name, value) in values) command.Parameters.AddWithValue(name, value);
            await command.ExecuteNonQueryAsync(TestContext.Current.CancellationToken);
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

    private sealed class StaticKeys(byte[] key) : IMfaKeyProvider
    {
        public byte[] GetKey(int version) => version == 1 ? (byte[])key.Clone() : throw new InvalidOperationException("mfa_key_version_unknown");

        // Versión activa explícita del stub (1) y copia nueva del material.
        public (int Version, byte[] Key) GetActiveKey() => (1, (byte[])key.Clone());
    }
}
