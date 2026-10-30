using Npgsql;
using RackClick.Domain;
using RackClick.Server;
using Xunit;
using Lab = RackClick.Quality.Tests.MfaAccountManagementTests.Laboratory;

namespace RackClick.Quality.Tests;

public sealed class MfaGraceEnforcementTests
{
    [Fact]
    public async Task RealProviderRolloutInitializationIsPersistedAndNeverRestarted()
    {
        await using var lab = await Lab.Create();
        Assert.Equal(0, await lab.Count("SELECT count(*) FROM app_mfa_policy"));
        await lab.Store.EnsureMfaGracePolicy(TestContext.Current.CancellationToken);
        string before = await lab.Snapshot("app_mfa_policy");
        await lab.Store.EnsureMfaGracePolicy(TestContext.Current.CancellationToken);
        Assert.Equal(before, await lab.Snapshot("app_mfa_policy"));
        Assert.Equal(1, await lab.Count("SELECT count(*) FROM app_mfa_policy WHERE enabled AND grace_days=45"));
        await lab.Execute("UPDATE app_mfa_policy SET enabled=false");
        await lab.Store.EnsureMfaGracePolicy(TestContext.Current.CancellationToken);
        Assert.Equal(0, await lab.Count("SELECT count(*) FROM app_mfa_policy WHERE enabled"));
    }

    [Fact]
    public async Task GraceAllowsPasswordSessionAndNewAccountsDoNotInheritAnOldDeadline()
    {
        await using var lab = await Lab.Create();
        await lab.Policy(80);
        var user = await lab.AddUser("new.account");
        var outcome = await lab.Store.AuthenticateForLogin(user.UserName, Lab.Password, TestContext.Current.CancellationToken);
        Assert.NotNull(outcome.Session); Assert.Null(outcome.Challenge);
        var status = await lab.Store.ReadOwnMfaStatus(user, true, TestContext.Current.CancellationToken);
        Assert.Equal(45, status.DaysRemaining); Assert.False(status.DeadlineReached);
    }

    [Fact]
    public async Task ExistingAccountsUseRolloutAndPasswordOnlySessionsLoseAccessAtExpiry()
    {
        await using var lab = await Lab.Create();
        var user = await lab.AddUser("old.account");
        await lab.Legacy(user.Id); await lab.Policy(46);
        var (token, actor) = await PlainSession(lab, user, verified: false);
        Assert.Null(await lab.Store.Session(token, TestContext.Current.CancellationToken));
        await using var db = await lab.RuntimeSource.OpenConnectionAsync(TestContext.Current.CancellationToken);
        await using var tx = await db.BeginTransactionAsync(TestContext.Current.CancellationToken);
        var error = await Assert.ThrowsAsync<DomainError>(() => PostgresStore.RequireCurrentSession(db, tx, actor, TestContext.Current.CancellationToken));
        Assert.Equal(401, error.Status);
    }

    [Fact]
    public async Task ExpiredLoginCreatesEnrollmentChallengeWithoutAnApiSessionAndAuditsOnlyOnce()
    {
        await using var lab = await Lab.Create();
        var user = await lab.AddUser("expired.account");
        await lab.Legacy(user.Id); await lab.Policy(46);
        var outcome = await lab.Store.AuthenticateForLogin(user.UserName, Lab.Password, TestContext.Current.CancellationToken);
        Assert.Null(outcome.Session); Assert.NotNull(outcome.Challenge); Assert.Equal("enroll", outcome.ChallengePurpose);
        Assert.Equal(0, await lab.Count("SELECT count(*) FROM app_session WHERE user_id=@user", ("user", user.Id)));
        Assert.Equal(1, await lab.Count("SELECT count(*) FROM audit_event WHERE action='auth.mfa.grace_expired'"));
        await lab.Store.AuthenticateForLogin(user.UserName, Lab.Password, TestContext.Current.CancellationToken);
        Assert.Equal(1, await lab.Count("SELECT count(*) FROM audit_event WHERE action='auth.mfa.grace_expired'"));
    }

    [Fact]
    public async Task GlobalAdministratorIsExemptButClientScopedGrantsDoNotExemptAUser()
    {
        await using var lab = await Lab.Create();
        await lab.Policy(46); await lab.Legacy(lab.Admin.Id);
        var outcome = await lab.Store.AuthenticateForLogin(lab.Admin.UserName, Lab.Password, TestContext.Current.CancellationToken);
        Assert.NotNull(outcome.Session); Assert.Null(outcome.Challenge);
        var user = await lab.AddUser("client.administrator"); await lab.Legacy(user.Id);
        await lab.Execute("""
            INSERT INTO customer(id,systemhaus_id,name) VALUES(@customer,@house,'Client scope');
            INSERT INTO user_group(id,systemhaus_id,name) VALUES(@group,@house,'Scoped administrators');
            INSERT INTO user_group_member(systemhaus_id,user_id,group_id) VALUES(@house,@user,@group);
            INSERT INTO permission_grant(id,systemhaus_id,user_group_id,capability,customer_id)
            VALUES(@grant1,@house,@group,'security.manage',@customer),(@grant2,@house,@group,'systemhaus.manage',@customer);
            """, ("customer", Guid.NewGuid()), ("house", lab.House), ("group", Guid.NewGuid()), ("user", user.Id),
            ("grant1", Guid.NewGuid()), ("grant2", Guid.NewGuid()));
        var ordinary = await lab.Store.AuthenticateForLogin(user.UserName, Lab.Password, TestContext.Current.CancellationToken);
        Assert.Null(ordinary.Session); Assert.NotNull(ordinary.Challenge);
    }

    [Fact]
    public async Task CompletedMfaSessionsContinueAfterGraceButUnavailableProviderCannotIssuePasswordSession()
    {
        await using var lab = await Lab.Create();
        var user = await lab.AddUser("verified.account");
        await lab.Policy(46); await lab.Legacy(user.Id);
        var (token, _) = await PlainSession(lab, user, verified: true);
        Assert.NotNull(await lab.Store.Session(token, TestContext.Current.CancellationToken));
        var unavailable = new PostgresStore(lab.RuntimeSource) { MfaAvailable = false };
        var error = await Assert.ThrowsAsync<DomainError>(() => unavailable.AuthenticateForLogin(user.UserName, Lab.Password, TestContext.Current.CancellationToken));
        Assert.Equal("mfa_enrollment_required", error.Code);
        Assert.Equal(0, await lab.Count("SELECT count(*) FROM app_session WHERE user_id=@user AND mfa_verified_at IS NULL", ("user", user.Id)));
    }

    [Fact]
    public async Task SessionRevalidationUsesDatabaseTimeAfterAnAccountLockWait()
    {
        await using var lab = await Lab.Create();
        var user = await lab.AddUser("lock.wait.account"); await lab.Legacy(user.Id);
        await lab.Policy(44);
        var (_, actor) = await PlainSession(lab, user, verified: false);
        await using var holder = await lab.RuntimeSource.OpenConnectionAsync(TestContext.Current.CancellationToken);
        await using var held = await holder.BeginTransactionAsync(TestContext.Current.CancellationToken);
        await using (var row = new NpgsqlCommand("SELECT id FROM app_user WHERE id=@user FOR UPDATE", holder, held))
        {
            row.Parameters.AddWithValue("user", user.Id); await row.ExecuteScalarAsync(TestContext.Current.CancellationToken);
        }
        await lab.Execute("UPDATE app_mfa_policy SET activated_at=clock_timestamp()-interval '45 days'+interval '400 milliseconds'");
        await using var db = await lab.RuntimeSource.OpenConnectionAsync(TestContext.Current.CancellationToken);
        await using var tx = await db.BeginTransactionAsync(TestContext.Current.CancellationToken);
        var pending = PostgresStore.RequireCurrentSession(db, tx, actor, TestContext.Current.CancellationToken);
        await using (var wait = new NpgsqlCommand("SELECT pg_sleep(0.65)", holder, held)) await wait.ExecuteNonQueryAsync(TestContext.Current.CancellationToken);
        Assert.False(pending.IsCompleted);
        await held.RollbackAsync(TestContext.Current.CancellationToken);
        var error = await Assert.ThrowsAsync<DomainError>(() => pending);
        Assert.Equal(401, error.Status);
    }

    private static async Task<(string Token, Actor Actor)> PlainSession(Lab lab, Actor user, bool verified)
    {
        string token = Secrets.Token(), csrf = Secrets.Token();
        await lab.Execute("""
            INSERT INTO app_session(token_hash,user_id,csrf_hash,expires_at,mfa_verified_at)
            VALUES(@token,@user,@csrf,clock_timestamp()+interval '1 hour',CASE WHEN @verified THEN clock_timestamp() ELSE NULL END)
            """, ("token", Secrets.Digest(token)), ("user", user.Id), ("csrf", Secrets.Digest(csrf)), ("verified", verified));
        return (token, user with { SessionTokenHash = Secrets.Digest(token) });
    }
}
