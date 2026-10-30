using System.Security.Cryptography;
using Npgsql;
using RackClick.Domain;
using RackClick.Server;
using Xunit;

namespace RackClick.Quality.Tests;

// Pruebas de integración del segundo paso MFA contra PostgreSQL 17 real.
// Se ejecutan solo si RACKCLICK_TEST_PG_ADMIN apunta a un servidor de laboratorio con rol que pueda crear bases.
// Crean una base temporal, aplican 001–015 desde el árbol de fuentes y la eliminan al terminar. No usan el servidor QA.
public sealed class MfaStoreTests
{
    private const string AdminVariable = "RACKCLICK_TEST_PG_ADMIN";
    private const string LoginUserName = "usuario-login";
    private static readonly string LoginPassword = "RcTest-" + Convert.ToHexString(System.Security.Cryptography.RandomNumberGenerator.GetBytes(24));

    [Fact]
    public async Task ValidCodeIssuesSessionMarkedAsMfaVerified()
    {
        await using var env = await MfaTestDatabase.CreateAsync();
        var user = await env.CreateLoginUserAsync(mfaRequired: true, withActiveFactor: true);
        var (challenge, csrf) = await env.IssueChallengeAsync();

        var (token, sessionCsrf) = await env.Verifier().CompleteVerify(challenge, env.CodeNow(user), csrf, TestContext.Current.CancellationToken);

        Assert.NotEmpty(sessionCsrf);
        Assert.True(await env.SessionHasMfaVerifiedAsync(token));
    }

    [Fact]
    public async Task SameCodeCannotBeReusedWithANewChallenge()
    {
        await using var env = await MfaTestDatabase.CreateAsync();
        var user = await env.CreateLoginUserAsync(mfaRequired: true, withActiveFactor: true);
        var code = env.CodeNow(user);
        var (first, firstCsrf) = await env.IssueChallengeAsync();
        await env.Verifier().CompleteVerify(first, code, firstCsrf, TestContext.Current.CancellationToken);
        var (second, secondCsrf) = await env.IssueChallengeAsync();

        var error = await Assert.ThrowsAsync<DomainError>(() => env.Verifier().CompleteVerify(second, code, secondCsrf, TestContext.Current.CancellationToken));

        Assert.Equal("mfa_code_invalid", error.Message);
    }

    [Fact]
    public async Task ChallengeCannotBeUsedTwice()
    {
        await using var env = await MfaTestDatabase.CreateAsync();
        var user = await env.CreateLoginUserAsync(mfaRequired: true, withActiveFactor: true);
        var (challenge, csrf) = await env.IssueChallengeAsync();
        await env.Verifier().CompleteVerify(challenge, env.CodeNow(user), csrf, TestContext.Current.CancellationToken);

        var error = await Assert.ThrowsAsync<DomainError>(() => env.Verifier().CompleteVerify(challenge, env.CodeNow(user), csrf, TestContext.Current.CancellationToken));

        Assert.Equal("mfa_challenge_invalid", error.Message);
    }

    [Fact]
    public async Task ExpiredChallengeIsRejected()
    {
        await using var env = await MfaTestDatabase.CreateAsync();
        var user = await env.CreateLoginUserAsync(mfaRequired: true, withActiveFactor: true);
        var (challenge, csrf) = await env.IssueChallengeAsync();
        await env.ExecuteAsync("UPDATE app_mfa_challenge SET expires_at = now() - interval '1 second'");

        var error = await Assert.ThrowsAsync<DomainError>(() => env.Verifier().CompleteVerify(challenge, env.CodeNow(user), csrf, TestContext.Current.CancellationToken));

        Assert.Equal("mfa_challenge_invalid", error.Message);
    }

    [Fact]
    public async Task ChallengeExpiringWhileWaitingForAnAccountLockIsRejected()
    {
        await using var env = await MfaTestDatabase.CreateAsync();
        var user = await env.CreateLoginUserAsync(mfaRequired: true, withActiveFactor: true);
        var (challenge, csrf) = await env.IssueChallengeAsync();
        await env.ExecuteAsync("UPDATE app_mfa_challenge SET expires_at = now() + interval '2 seconds'");
        var code = env.CodeNow(user);

        await using var holder = await env.Source().OpenConnectionAsync(TestContext.Current.CancellationToken);
        await using var hold = holder.BeginTransaction();
        await using (var lockAccount = new NpgsqlCommand("SELECT 1 FROM app_user WHERE id=@user FOR UPDATE", holder, hold))
        {
            lockAccount.Parameters.AddWithValue("user", user.UserId);
            await lockAccount.ExecuteScalarAsync(TestContext.Current.CancellationToken);
        }
        var pending = env.Verifier().CompleteVerify(challenge, code, csrf, TestContext.Current.CancellationToken);
        await Task.Delay(TimeSpan.FromSeconds(3), TestContext.Current.CancellationToken);
        await hold.CommitAsync(TestContext.Current.CancellationToken);

        var error = await Assert.ThrowsAsync<DomainError>(() => pending);
        Assert.Equal("mfa_challenge_invalid", error.Message);
        Assert.Equal(0, await env.CountAsync("SELECT count(*) FROM app_session"));
    }

    [Fact]
    public async Task FiveWrongCodesConsumeTheChallengeAndLockTheFactor()
    {
        await using var env = await MfaTestDatabase.CreateAsync();
        var user = await env.CreateLoginUserAsync(mfaRequired: true, withActiveFactor: true);
        var wrong = env.WrongCode(user);
        for (var attempt = 1; attempt <= 5; attempt++)
        {
            var (challenge, csrf) = await env.IssueChallengeAsync();
            var error = await Assert.ThrowsAsync<DomainError>(() => env.Verifier().CompleteVerify(challenge, wrong, csrf, TestContext.Current.CancellationToken));
            Assert.Equal("mfa_code_invalid", error.Message);
        }

        Assert.True(await env.FactorIsLockedAsync(user));
        var (locked, lockedCsrf) = await env.IssueChallengeAsync();
        var lockedError = await Assert.ThrowsAsync<DomainError>(() => env.Verifier().CompleteVerify(locked, env.CodeNow(user), lockedCsrf, TestContext.Current.CancellationToken));
        Assert.Equal("mfa_challenge_invalid", lockedError.Message);
    }

    [Fact]
    public async Task ChallengeExpiringWhileWaitingForThePolicyLockIsRejected()
    {
        await using var env = await MfaTestDatabase.CreateAsync();
        var user = await env.CreateLoginUserAsync(mfaRequired: true, withActiveFactor: true);
        var (challenge, csrf) = await env.IssueChallengeAsync();
        await env.ExecuteAsync("UPDATE app_mfa_challenge SET expires_at = now() + interval '2 seconds'");
        var code = env.CodeNow(user);

        await using var holder = await env.Source().OpenConnectionAsync(TestContext.Current.CancellationToken);
        await using var hold = holder.BeginTransaction();
        await using (var lockPolicy = new NpgsqlCommand("SELECT 1 FROM app_mfa_user WHERE user_id=@user FOR UPDATE", holder, hold))
        {
            lockPolicy.Parameters.AddWithValue("user", user.UserId);
            await lockPolicy.ExecuteScalarAsync(TestContext.Current.CancellationToken);
        }
        var pending = env.Verifier().CompleteVerify(challenge, code, csrf, TestContext.Current.CancellationToken);
        await Task.Delay(TimeSpan.FromSeconds(3), TestContext.Current.CancellationToken);
        await hold.CommitAsync(TestContext.Current.CancellationToken);

        var error = await Assert.ThrowsAsync<DomainError>(() => pending);
        Assert.Equal("mfa_challenge_invalid", error.Message);
        Assert.Equal(0, await env.CountAsync("SELECT count(*) FROM app_session"));
    }

    [Fact]
    public async Task ChallengeExpiringWhileWaitingForTheChallengeLockIsRejected()
    {
        await using var env = await MfaTestDatabase.CreateAsync();
        var user = await env.CreateLoginUserAsync(mfaRequired: true, withActiveFactor: true);
        var (challenge, csrf) = await env.IssueChallengeAsync();
        await env.ExecuteAsync("UPDATE app_mfa_challenge SET expires_at = now() + interval '2 seconds'");
        var code = env.CodeNow(user);

        await using var holder = await env.Source().OpenConnectionAsync(TestContext.Current.CancellationToken);
        await using var hold = holder.BeginTransaction();
        await using (var lockChallenge = new NpgsqlCommand("SELECT 1 FROM app_mfa_challenge WHERE token_hash=@token FOR UPDATE", holder, hold))
        {
            lockChallenge.Parameters.AddWithValue("token", Secrets.Digest(challenge));
            await lockChallenge.ExecuteScalarAsync(TestContext.Current.CancellationToken);
        }
        var pending = env.Verifier().CompleteVerify(challenge, code, csrf, TestContext.Current.CancellationToken);
        await Task.Delay(TimeSpan.FromSeconds(3), TestContext.Current.CancellationToken);
        await hold.CommitAsync(TestContext.Current.CancellationToken);

        var error = await Assert.ThrowsAsync<DomainError>(() => pending);
        Assert.Equal("mfa_challenge_invalid", error.Message);
        Assert.Equal(0, await env.CountAsync("SELECT count(*) FROM app_session"));
    }

    [Fact]
    public async Task WrongCsrfIsRejectedWithoutConsumingTheChallenge()
    {
        await using var env = await MfaTestDatabase.CreateAsync();
        var user = await env.CreateLoginUserAsync(mfaRequired: true, withActiveFactor: true);
        var (challenge, csrf) = await env.IssueChallengeAsync();

        var error = await Assert.ThrowsAsync<DomainError>(() => env.Verifier().CompleteVerify(challenge, env.CodeNow(user), "csrf-ajeno", TestContext.Current.CancellationToken));
        Assert.Equal("csrf_invalid", error.Message);
        Assert.Equal(0, await env.CountAsync("SELECT attempts::bigint FROM app_mfa_challenge"));

        var (token, _) = await env.Verifier().CompleteVerify(challenge, env.CodeNow(user), csrf, TestContext.Current.CancellationToken);
        Assert.True(await env.SessionHasMfaVerifiedAsync(token));
    }

    [Fact]
    public async Task MissingCsrfIsRejected()
    {
        await using var env = await MfaTestDatabase.CreateAsync();
        var user = await env.CreateLoginUserAsync(mfaRequired: true, withActiveFactor: true);
        var (challenge, _) = await env.IssueChallengeAsync();

        var error = await Assert.ThrowsAsync<DomainError>(() => env.Verifier().CompleteVerify(challenge, env.CodeNow(user), "", TestContext.Current.CancellationToken));

        Assert.Equal("csrf_invalid", error.Message);
    }

    [Fact]
    public async Task DeactivatedUserCannotCompleteAPendingChallenge()
    {
        await using var env = await MfaTestDatabase.CreateAsync();
        var user = await env.CreateLoginUserAsync(mfaRequired: true, withActiveFactor: true);
        var (challenge, csrf) = await env.IssueChallengeAsync();
        await env.ExecuteAsync("UPDATE app_user SET active = false");

        var error = await Assert.ThrowsAsync<DomainError>(() => env.Verifier().CompleteVerify(challenge, env.CodeNow(user), csrf, TestContext.Current.CancellationToken));

        Assert.Equal("mfa_challenge_invalid", error.Message);
    }

    [Fact]
    public async Task EnrollmentPendingRejectsLoginEvenWithAnOldActiveFactor()
    {
        await using var env = await MfaTestDatabase.CreateAsync();
        await env.CreateLoginUserAsync(mfaRequired: true, withActiveFactor: true);
        await env.ExecuteAsync("UPDATE app_mfa_user SET enrollment_pending = true");
        var store = env.Store(mfaAvailable: true);

        var error = await Assert.ThrowsAsync<DomainError>(() => store.Authenticate(LoginUserName, LoginPassword, TestContext.Current.CancellationToken));

        Assert.Equal("mfa_enrollment_required", error.Message);
        Assert.Equal(0, await env.CountAsync("SELECT count(*) FROM app_session"));
    }

    [Fact]
    public async Task PolicyChangeAfterChallengeCancelsIt()
    {
        await using var env = await MfaTestDatabase.CreateAsync();
        var user = await env.CreateLoginUserAsync(mfaRequired: true, withActiveFactor: true);
        var (challenge, csrf) = await env.IssueChallengeAsync();
        await env.ExecuteAsync("UPDATE app_mfa_user SET enrollment_pending = true, revision = revision + 1");

        var error = await Assert.ThrowsAsync<DomainError>(() => env.Verifier().CompleteVerify(challenge, env.CodeNow(user), csrf, TestContext.Current.CancellationToken));

        Assert.Equal("mfa_enrollment_required", error.Message);
        Assert.Equal(0, await env.CountAsync("SELECT count(*) FROM app_session"));
        Assert.Equal(0, await env.CountAsync("SELECT count(*) FROM app_mfa_challenge WHERE consumed_at IS NULL"));
    }

    [Fact]
    public async Task PolicyRevisionChangeWithoutEnrollmentCancelsTheChallenge()
    {
        await using var env = await MfaTestDatabase.CreateAsync();
        var user = await env.CreateLoginUserAsync(mfaRequired: true, withActiveFactor: true);
        var (challenge, csrf) = await env.IssueChallengeAsync();
        await env.ExecuteAsync("UPDATE app_mfa_user SET revision = revision + 1");

        var error = await Assert.ThrowsAsync<DomainError>(() => env.Verifier().CompleteVerify(challenge, env.CodeNow(user), csrf, TestContext.Current.CancellationToken));

        Assert.Equal("mfa_challenge_invalid", error.Message);
    }

    [Fact]
    public async Task PasswordResetRevokesPendingChallengeWhenCommitted()
    {
        await using var env = await MfaTestDatabase.CreateAsync();
        var user = await env.CreateLoginUserAsync(mfaRequired: true, withActiveFactor: true);
        var (challenge, csrf) = await env.IssueChallengeAsync();
        await env.ResetLikeTransactionAsync(user, commit: true);

        var error = await Assert.ThrowsAsync<DomainError>(() => env.Verifier().CompleteVerify(challenge, env.CodeNow(user), csrf, TestContext.Current.CancellationToken));

        Assert.Equal("mfa_challenge_invalid", error.Message);
    }

    [Fact]
    public async Task PasswordResetRolledBackKeepsTheChallengeUsable()
    {
        await using var env = await MfaTestDatabase.CreateAsync();
        var user = await env.CreateLoginUserAsync(mfaRequired: true, withActiveFactor: true);
        var (challenge, csrf) = await env.IssueChallengeAsync();
        await env.ResetLikeTransactionAsync(user, commit: false);

        var (token, _) = await env.Verifier().CompleteVerify(challenge, env.CodeNow(user), csrf, TestContext.Current.CancellationToken);

        Assert.True(await env.SessionHasMfaVerifiedAsync(token));
    }

    [Fact]
    public async Task VerificationWaitingForAPasswordResetDoesNotEmitASession()
    {
        await using var env = await MfaTestDatabase.CreateAsync();
        var user = await env.CreateLoginUserAsync(mfaRequired: true, withActiveFactor: true);
        var (challenge, csrf) = await env.IssueChallengeAsync();
        var code = env.CodeNow(user);

        await using var reset = await env.Source().OpenConnectionAsync(TestContext.Current.CancellationToken);
        await using var resetTx = reset.BeginTransaction();
        await using (var lockAccount = new NpgsqlCommand("UPDATE app_user SET password_hash = password_hash WHERE id=@user", reset, resetTx))
        {
            lockAccount.Parameters.AddWithValue("user", user.UserId);
            await lockAccount.ExecuteNonQueryAsync(TestContext.Current.CancellationToken);
        }
        var pending = env.Verifier().CompleteVerify(challenge, code, csrf, TestContext.Current.CancellationToken);
        await Task.Delay(TimeSpan.FromSeconds(1), TestContext.Current.CancellationToken);
        await MfaStore.RevokePendingChallenges(reset, resetTx, user.SystemhausId, user.UserId, TestContext.Current.CancellationToken);
        await resetTx.CommitAsync(TestContext.Current.CancellationToken);

        var error = await Assert.ThrowsAsync<DomainError>(() => pending);
        Assert.Equal("mfa_challenge_invalid", error.Message);
        Assert.Equal(0, await env.CountAsync("SELECT count(*) FROM app_session"));
    }

    [Fact]
    public async Task ConcurrentCompletionsOfTheSameChallengeYieldOneSession()
    {
        await using var env = await MfaTestDatabase.CreateAsync();
        var user = await env.CreateLoginUserAsync(mfaRequired: true, withActiveFactor: true);
        var (challenge, csrf) = await env.IssueChallengeAsync();
        var code = env.CodeNow(user);

        var results = await Task.WhenAll(
            Attempt(() => env.Verifier().CompleteVerify(challenge, code, csrf, TestContext.Current.CancellationToken)),
            Attempt(() => env.Verifier().CompleteVerify(challenge, code, csrf, TestContext.Current.CancellationToken)));

        Assert.Equal(1, results.Count(r => r));
    }

    [Fact]
    public async Task LoginWithoutMfaIssuesSession()
    {
        await using var env = await MfaTestDatabase.CreateAsync();
        await env.CreateLoginUserAsync(mfaRequired: false, withActiveFactor: false);

        var outcome = await env.Store(mfaAvailable: false).Authenticate(LoginUserName, LoginPassword, TestContext.Current.CancellationToken);

        Assert.NotNull(outcome.Session);
        Assert.Null(outcome.Challenge);
    }

    [Fact]
    public async Task LoginWithMfaReturnsChallengeAndNoSession()
    {
        await using var env = await MfaTestDatabase.CreateAsync();
        await env.CreateLoginUserAsync(mfaRequired: true, withActiveFactor: true);

        var outcome = await env.Store(mfaAvailable: true).Authenticate(LoginUserName, LoginPassword, TestContext.Current.CancellationToken);

        Assert.Null(outcome.Session);
        Assert.NotNull(outcome.Challenge);
        Assert.Equal(0, await env.CountAsync("SELECT count(*) FROM app_session"));
        Assert.Equal(1, await env.CountAsync("SELECT count(*) FROM app_mfa_challenge WHERE consumed_at IS NULL"));
    }

    [Fact]
    public async Task MfaRequiredWithoutFactorNeedsEnrollment()
    {
        await using var env = await MfaTestDatabase.CreateAsync();
        await env.CreateLoginUserAsync(mfaRequired: true, withActiveFactor: false);

        var error = await Assert.ThrowsAsync<DomainError>(() => env.Store(mfaAvailable: true).Authenticate(LoginUserName, LoginPassword, TestContext.Current.CancellationToken));

        Assert.Equal("mfa_enrollment_required", error.Message);
        Assert.Equal(0, await env.CountAsync("SELECT count(*) FROM app_session"));
    }

    [Fact]
    public async Task MfaRequiredWithoutKeyProviderIsUnavailable()
    {
        await using var env = await MfaTestDatabase.CreateAsync();
        await env.CreateLoginUserAsync(mfaRequired: true, withActiveFactor: true);

        var error = await Assert.ThrowsAsync<DomainError>(() => env.Store(mfaAvailable: false).Authenticate(LoginUserName, LoginPassword, TestContext.Current.CancellationToken));

        Assert.Equal("mfa_unavailable", error.Message);
        Assert.Equal(0, await env.CountAsync("SELECT count(*) FROM app_mfa_challenge"));
    }

    [Fact]
    public async Task LegacyLoginRefusesUserWithMfa()
    {
        await using var env = await MfaTestDatabase.CreateAsync();
        await env.CreateLoginUserAsync(mfaRequired: true, withActiveFactor: true);

        var error = await Assert.ThrowsAsync<DomainError>(() => env.Store(mfaAvailable: true).Login(LoginUserName, LoginPassword, TestContext.Current.CancellationToken));

        Assert.Equal("mfa_required", error.Message);
    }

    private static async Task<bool> Attempt(Func<Task<(string Token, string Csrf)>> action)
    {
        try
        {
            await action();
            return true;
        }
        catch (DomainError)
        {
            return false;
        }
    }

    private sealed record TestUser(Guid SystemhausId, Guid UserId, byte[] Secret);

    private sealed class StaticKeys(byte[] key) : IMfaKeyProvider
    {
        public byte[] GetKey(int version) => version == 1 ? (byte[])key.Clone() : throw new InvalidOperationException("mfa_key_version_unknown");

        // Versión activa explícita del stub (1) y copia nueva del material.
        public (int Version, byte[] Key) GetActiveKey() => (1, (byte[])key.Clone());
    }

    private sealed class MfaTestDatabase : IAsyncDisposable
    {
        private readonly string _database;
        private readonly string _adminConnection;
        private readonly byte[] _key = RandomNumberGenerator.GetBytes(MfaSecretCipher.KeyBytes);
        private NpgsqlDataSource? _source;
        private TestUser? _loginUser;

        private MfaTestDatabase(string database, string adminConnection)
        {
            _database = database;
            _adminConnection = adminConnection;
        }

        public static async Task<MfaTestDatabase> CreateAsync()
        {
            var admin = Environment.GetEnvironmentVariable(AdminVariable);
            Assert.SkipWhen(string.IsNullOrWhiteSpace(admin), AdminVariable + " no está definido: prueba PostgreSQL omitida.");
            var database = "rc_mfa_test_" + Guid.NewGuid().ToString("N");
            await using (var connection = new NpgsqlConnection(admin))
            {
                await connection.OpenAsync();
                await using var create = new NpgsqlCommand($"CREATE DATABASE {database} ENCODING 'UTF8' TEMPLATE template0", connection);
                await create.ExecuteNonQueryAsync();
            }
            var environment = new MfaTestDatabase(database, admin!);
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

        internal MfaStore Verifier() => new(Source(), new StaticKeys(_key));

        internal PostgresStore Store(bool mfaAvailable) => new(Source()) { MfaAvailable = mfaAvailable };

        // Emite un desafío real con la contraseña válida, igual que el login.
        internal async Task<(string Challenge, string Csrf)> IssueChallengeAsync()
        {
            var outcome = await Store(mfaAvailable: true).Authenticate(LoginUserName, LoginPassword, TestContext.Current.CancellationToken);
            var challenge = outcome.Challenge ?? throw new InvalidOperationException("el login no emitió desafío");
            return (challenge.Token, challenge.Csrf);
        }

        // Usuario con contraseña real, política y factor activo. Mantiene el valor del secreto para generar códigos.
        internal async Task<TestUser> CreateLoginUserAsync(bool mfaRequired, bool withActiveFactor)
        {
            var systemhaus = Guid.NewGuid();
            var user = Guid.NewGuid();
            var secret = MfaTotp.NewSecret();
            await ExecuteAsync("INSERT INTO systemhaus(id,name) VALUES(@sh,'Lab MFA')", ("sh", systemhaus));
            await ExecuteAsync(
                "INSERT INTO app_user(id,systemhaus_id,username,password_hash) VALUES(@user,@sh,@name,@hash)",
                ("user", user), ("sh", systemhaus), ("name", LoginUserName), ("hash", Secrets.PasswordHash(LoginUserName, LoginPassword)));
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
            _loginUser = new TestUser(systemhaus, user, secret);
            return _loginUser;
        }

        // Réplica de la transacción de reset administrativo: bloquea la cuenta, invalida desafíos y confirma o revierte.
        internal async Task ResetLikeTransactionAsync(TestUser user, bool commit)
        {
            await using var connection = await Source().OpenConnectionAsync(TestContext.Current.CancellationToken);
            await using var tx = await connection.BeginTransactionAsync(TestContext.Current.CancellationToken);
            await using (var lockAccount = new NpgsqlCommand("UPDATE app_user SET password_hash = password_hash WHERE id=@user", connection, tx))
            {
                lockAccount.Parameters.AddWithValue("user", user.UserId);
                await lockAccount.ExecuteNonQueryAsync(TestContext.Current.CancellationToken);
            }
            await MfaStore.RevokePendingChallenges(connection, tx, user.SystemhausId, user.UserId, TestContext.Current.CancellationToken);
            if (commit) await tx.CommitAsync(TestContext.Current.CancellationToken);
            else await tx.RollbackAsync(TestContext.Current.CancellationToken);
        }

        public string CodeNow(TestUser user) => MfaTotp.Compute(user.Secret, DateTimeOffset.UtcNow);

        public string WrongCode(TestUser user)
        {
            var valid = new HashSet<string>
            {
                MfaTotp.Compute(user.Secret, DateTimeOffset.UtcNow.AddSeconds(-MfaTotp.StepSeconds)),
                MfaTotp.Compute(user.Secret, DateTimeOffset.UtcNow),
                MfaTotp.Compute(user.Secret, DateTimeOffset.UtcNow.AddSeconds(MfaTotp.StepSeconds)),
            };
            for (var candidate = 0; candidate < 1_000_000; candidate++)
            {
                var text = candidate.ToString("D6");
                if (!valid.Contains(text)) return text;
            }
            throw new InvalidOperationException("sin código incorrecto disponible");
        }

        public async Task<bool> SessionHasMfaVerifiedAsync(string token)
        {
            await using var connection = await Source().OpenConnectionAsync(TestContext.Current.CancellationToken);
            await using var command = new NpgsqlCommand("SELECT mfa_verified_at IS NOT NULL FROM app_session WHERE token_hash=@token", connection);
            command.Parameters.AddWithValue("token", Secrets.Digest(token));
            return (bool)(await command.ExecuteScalarAsync(TestContext.Current.CancellationToken) ?? false);
        }

        public async Task<bool> FactorIsLockedAsync(TestUser user)
        {
            await using var connection = await Source().OpenConnectionAsync(TestContext.Current.CancellationToken);
            await using var command = new NpgsqlCommand("SELECT locked_until IS NOT NULL FROM app_mfa_factor WHERE user_id=@user", connection);
            command.Parameters.AddWithValue("user", user.UserId);
            return (bool)(await command.ExecuteScalarAsync(TestContext.Current.CancellationToken) ?? false);
        }

        public async Task<long> CountAsync(string sql)
        {
            await using var connection = await Source().OpenConnectionAsync(TestContext.Current.CancellationToken);
            await using var command = new NpgsqlCommand(sql, connection);
            return (long)(await command.ExecuteScalarAsync(TestContext.Current.CancellationToken) ?? 0L);
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
            var database = FindDatabaseFolder();
            var files = Enumerable.Range(1, 13).Select(n => Path.Combine(database, n.ToString("D3") + "-" + MigrationName(n))).ToList();
            files.Add(Path.Combine(database, "014-mfa.sql"));
            files.Add(Path.Combine(database, "015-mfa-account-policy.sql"));
            await using var connection = await Source().OpenConnectionAsync(TestContext.Current.CancellationToken);
            foreach (var file in files)
            {
                await using var command = new NpgsqlCommand(await File.ReadAllTextAsync(file, TestContext.Current.CancellationToken), connection);
                await command.ExecuteNonQueryAsync(TestContext.Current.CancellationToken);
            }
        }

        private static string MigrationName(int number) => number switch
        {
            1 => "foundation.sql",
            2 => "inventory.sql",
            3 => "operation-cancellation.sql",
            4 => "session-identity.sql",
            5 => "audit-context.sql",
            6 => "audit-state-intent.sql",
            7 => "audit-context-families.sql",
            8 => "user-catalog-favorites.sql",
            9 => "private-device-templates.sql",
            10 => "customer-shared-device-templates.sql",
            11 => "user-preferences.sql",
            12 => "user-port-colors.sql",
            13 => "user-category-colors.sql",
            _ => throw new ArgumentOutOfRangeException(nameof(number)),
        };

        // Se busca el árbol de fuentes, no la copia de la salida de compilación.
        private static string FindDatabaseFolder()
        {
            for (var directory = new DirectoryInfo(AppContext.BaseDirectory); directory is not null; directory = directory.Parent)
            {
                var candidate = Path.Combine(directory.FullName, "database");
                if (Directory.Exists(candidate) && File.Exists(Path.Combine(candidate, "014-mfa.sql")))
                {
                    return candidate;
                }
            }
            throw new DirectoryNotFoundException("carpeta database de migraciones no encontrada");
        }
    }
}
