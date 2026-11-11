using System.Security.Cryptography;
using Npgsql;
using OtpNet;
using RackClick.Domain;
using RackClick.Server;
using Xunit;
using Lab = RackClick.Quality.Tests.MfaAccountManagementTests.Laboratory;

namespace RackClick.Quality.Tests;

// F-08.04: actual PostgreSQL/store path, synthetic accounts/material, no installed host.
[Collection("MfaHttp")]
public sealed class MfaLastAdministratorRecoveryTests
{
    private static CancellationToken Ct => TestContext.Current.CancellationToken;
    private sealed class NoKeys : IMfaKeyProvider
    {
        public byte[] GetKey(int version) => throw new InvalidOperationException("Recovery requested a TOTP encryption key.");
        public (int Version, byte[] Key) GetActiveKey() => throw new InvalidOperationException("Recovery requested a TOTP encryption key.");
    }
    private sealed class Keys(byte[] key) : IMfaKeyProvider
    {
        public byte[] GetKey(int version) => version == 1 ? (byte[])key.Clone() : throw new InvalidOperationException("Unexpected fixture key version.");
        public (int Version, byte[] Key) GetActiveKey() => (1, (byte[])key.Clone());
    }

    [Fact]
    public async Task TheOnlyGlobalAdministratorRecoversWithoutAnotherAdministratorAndKeepsAuthority()
    {
        await using var lab = await Lab.Create();
        await Prepare(lab);
        var scoped = await lab.AddUser("client.administrator");
        var customer = Guid.NewGuid(); var group = Guid.NewGuid();
        await lab.Execute("""
            INSERT INTO customer(id,systemhaus_id,name) VALUES(@customer,@house,'Scoped recovery fixture');
            INSERT INTO user_group(id,systemhaus_id,name) VALUES(@group,@house,'Customer administrators');
            INSERT INTO user_group_member(systemhaus_id,user_id,group_id) VALUES(@house,@user,@group);
            INSERT INTO permission_grant(id,systemhaus_id,user_group_id,capability,customer_id)
              VALUES(@grant1,@house,@group,'security.manage',@customer),(@grant2,@house,@group,'systemhaus.manage',@customer);
            """, ("customer", customer), ("house", lab.House), ("group", group), ("user", scoped.Id),
            ("grant1", Guid.NewGuid()), ("grant2", Guid.NewGuid()));
        Assert.Equal(2, await lab.Count("SELECT count(*) FROM app_user WHERE active"));
        Assert.Equal(1, await ActiveGlobals(lab));
        var authorityBefore = await Authority(lab);
        var policyBefore = await lab.Snapshot("app_mfa_policy");
        var permissionsBefore = await lab.Store.ReadPermissions(lab.Admin, Ct);
        Assert.Contains("security.manage", permissionsBefore.SystemhausCapabilities);
        Assert.Contains("systemhaus.manage", permissionsBefore.SystemhausCapabilities);
        var oldCodes = await Generate(lab, lab.Admin);
        var login = await lab.Store.AuthenticateForLogin(lab.Admin.UserName, Lab.Password, Ct);
        Assert.Null(login.Session); Assert.Equal("verify", login.ChallengePurpose ?? "verify");
        Assert.True(login.Challenge.HasValue, "The valid password did not produce a verification challenge.");
        var verify = login.Challenge!.Value;
        var recovery = await new MfaStore(lab.RuntimeSource, new NoKeys())
            .RedeemRecoveryCode(verify.Token, oldCodes.Codes![0], verify.Csrf, Ct);
        Assert.Equal("enroll", recovery.Purpose);
        Assert.Equal(1, await ActiveGlobals(lab));
        Assert.True(authorityBefore == await Authority(lab), "Recovery changed identity, password or grants.");
        Assert.Equal(0, await lab.Count("SELECT count(*) FROM app_session WHERE user_id=@user", ("user", lab.Admin.Id)));
        Assert.Equal(401, (await Assert.ThrowsAsync<DomainError>(() => lab.Store.ReadUsers(lab.Admin, Ct))).Status);
        var pendingLogin = await lab.Store.AuthenticateForLogin(lab.Admin.UserName, Lab.Password, Ct);
        Assert.Null(pendingLogin.Session); Assert.Equal("enroll", pendingLogin.ChallengePurpose);
        Assert.Equal(10, await lab.Count("SELECT count(*) FROM app_mfa_recovery_code WHERE user_id=@user AND consumed_at IS NOT NULL", ("user", lab.Admin.Id)));

        byte[] key = RandomNumberGenerator.GetBytes(32); byte[]? secret = null;
        try
        {
            var mfa = new MfaStore(lab.RuntimeSource, new Keys(key));
            var start = await mfa.StartEnrollment(recovery.ChallengeToken, recovery.Csrf, Ct);
            secret = Base32Encoding.ToBytes(start.SecretBase32);
            Assert.Equal(0, await lab.Count("SELECT count(*) FROM app_session WHERE user_id=@user", ("user", lab.Admin.Id)));
            var confirmed = await mfa.ConfirmEnrollment(recovery.ChallengeToken,
                MfaTotp.Compute(secret, DateTimeOffset.UtcNow), recovery.Csrf, Ct);
            Assert.True(Secrets.Digest(confirmed.Token) != lab.Admin.SessionTokenHash, "Recovery reused an old session.");
            Assert.True(confirmed.Token != recovery.ChallengeToken && confirmed.Csrf != recovery.Csrf, "Recovery reused challenge credentials.");
            var identity = await lab.Store.Session(confirmed.Token, Ct); Assert.NotNull(identity);
            Assert.Equal(lab.Admin.Id, identity.Actor.Id); Assert.Equal(lab.Admin.HouseId, identity.Actor.HouseId);
            Assert.Equal(lab.Admin.UserName, identity.Actor.UserName);
            Assert.True(authorityBefore == await Authority(lab), "Reenrollment changed identity or authority.");
            var permissions = await lab.Store.ReadPermissions(identity.Actor, Ct);
            Assert.Equal(permissionsBefore.SystemhausCapabilities.Order(), permissions.SystemhausCapabilities.Order());
            var users = await lab.Store.ReadUsers(identity.Actor, Ct);
            Assert.Contains(users.Users, user => user.Id == lab.Admin.Id && user.Active);
            var status = await lab.Store.ReadOwnMfaStatus(identity.Actor, true, Ct);
            Assert.True(status.GlobalAdministratorExempt && status.SessionMfaVerified);
            Assert.False(status.EnrollmentPending); Assert.Equal("active", status.FactorState);
            Assert.True(status.CanDisable, "Recovery changed the confirmed global own-account exemption.");

            // Explicitly replenish codes only after the new MFA session; never expose another person's codes.
            var replenished = await Generate(lab, identity.Actor);
            Assert.NotNull(replenished.Codes); Assert.Equal(10, replenished.Codes.Length);
            Assert.False(oldCodes.Codes!.Intersect(replenished.Codes, StringComparer.Ordinal).Any(), "Old recovery values were reissued.");
            Assert.Equal(10, await lab.Count("SELECT count(*) FROM app_mfa_recovery_code WHERE user_id=@user AND consumed_at IS NULL", ("user", lab.Admin.Id)));
            await lab.Store.ChangeUserMfa(identity.Actor, scoped.Id, "enable", await Revision(lab), Guid.NewGuid(), true, Ct);
            Assert.Equal(1, await lab.Count("SELECT count(*) FROM app_mfa_user WHERE user_id=@user AND mfa_required AND enrollment_pending", ("user", scoped.Id)));
            Assert.True(authorityBefore == await Authority(lab), "An MFA operation changed groups or capabilities.");

            // The separate existing guard must still prevent removing the sole administrator.
            var beforeGuard = await lab.SnapshotAll();
            var expected = await Revision(lab);
            var denied = await Assert.ThrowsAsync<DomainError>(() => lab.Store.SetOrCancelUserState(identity.Actor,
                lab.Admin.Id, new UserStateRequest(false), false, expected, Guid.NewGuid(), Ct));
            Assert.Equal(409, denied.Status); Assert.Equal("last_admin_required", denied.Code);
            Assert.True(beforeGuard == await lab.SnapshotAll(), "Last-administrator rejection failed to roll back.");
            Assert.Equal(1, await ActiveGlobals(lab));
            Assert.True(policyBefore == await lab.Snapshot("app_mfa_policy"), "Recovery changed the grace policy.");
            var stored = await lab.SnapshotAll();
            foreach (var code in oldCodes.Codes!.Concat(replenished.Codes))
                Assert.False(stored.Contains(code, StringComparison.Ordinal), "A stored recovery value is plaintext.");
        }
        finally
        {
            if (secret is not null) CryptographicOperations.ZeroMemory(secret);
            CryptographicOperations.ZeroMemory(key);
        }
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task ValidCodesDoNotReactivateAnInactiveAccountOrBypassAFactorLock(bool factorLocked)
    {
        await using var lab = await Lab.Create(); await Prepare(lab);
        Assert.Equal(1, await ActiveGlobals(lab));
        var generated = await Generate(lab, lab.Admin);
        var login = await lab.Store.AuthenticateForLogin(lab.Admin.UserName, Lab.Password, Ct);
        Assert.Null(login.Session); Assert.True(login.Challenge.HasValue);
        var challenge = login.Challenge!.Value;
        // Only owner SQL in this fresh fixture can simulate an externally revoked last account.
        if (factorLocked) await lab.Execute("UPDATE app_mfa_factor SET locked_until=clock_timestamp()+interval '15 minutes' WHERE user_id=@user", ("user", lab.Admin.Id));
        else await lab.Execute("UPDATE app_user SET active=false WHERE id=@user", ("user", lab.Admin.Id));
        string[] unchanged = ["app_user", "app_mfa_user", "app_mfa_factor", "app_mfa_recovery_code", "app_session", "systemhaus", "operation", "audit_event", "app_mfa_policy"];
        var before = await lab.Snapshot(unchanged); var authority = await Authority(lab);
        var denied = await Assert.ThrowsAsync<DomainError>(() => new MfaStore(lab.RuntimeSource, new NoKeys())
            .RedeemRecoveryCode(challenge.Token, generated.Codes![0], challenge.Csrf, Ct));
        Assert.Equal(401, denied.Status); Assert.Equal("mfa_challenge_invalid", denied.Code);
        Assert.True(before == await lab.Snapshot(unchanged), "A blocked recovery changed protected state.");
        Assert.True(authority == await Authority(lab), "A recovery code changed account activation or authority.");
        Assert.Equal(10, await lab.Count("SELECT count(*) FROM app_mfa_recovery_code WHERE consumed_at IS NULL"));
        Assert.Equal(0, await lab.Count("SELECT count(*) FROM app_mfa_challenge WHERE purpose='enroll' AND consumed_at IS NULL"));
        Assert.Equal(0, await lab.Count("SELECT count(*) FROM audit_event WHERE action='auth.mfa.recovery_code_redeemed'"));
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task DisableCannotCancelRecoveryPendingEvenWithAnAuthorizedMfaSession(bool selfGlobal)
    {
        await using var lab = await Lab.Create(); await Prepare(lab);
        var target = selfGlobal ? lab.Admin : await lab.AddUser("recovering.in.grace", factor: true, verified: true);
        await lab.Execute("UPDATE app_mfa_factor SET confirmed_at=clock_timestamp() WHERE user_id=@user", ("user", target.Id));
        var generated = await Generate(lab, target);
        var login = await lab.Store.AuthenticateForLogin(target.UserName, Lab.Password, Ct);
        Assert.Null(login.Session); Assert.True(login.Challenge.HasValue);
        var challenge = login.Challenge!.Value;
        await new MfaStore(lab.RuntimeSource, new NoKeys())
            .RedeemRecoveryCode(challenge.Token, generated.Codes![0], challenge.Csrf, Ct);
        // The administrator/other-user case is reachable through normal flows. For the own-account
        // guard, inject a verified fixture session: normal login must never produce it while pending.
        var actor = selfGlobal ? await lab.Session(target.Id, true) : lab.Admin;
        var status = selfGlobal ? await lab.Store.ReadOwnMfaStatus(actor, true, Ct)
            : await lab.Store.ReadUserMfaStatus(actor, target.Id, true, Ct);
        Assert.True(status.EnrollmentPending);
        var before = await lab.SnapshotAll();
        var revision = await Revision(lab); var request = Guid.NewGuid();
        var denied = await Assert.ThrowsAsync<DomainError>(() => selfGlobal
            ? lab.Store.ChangeOwnMfa(actor, "disable", Lab.Password, revision, request, true, Ct)
            : lab.Store.ChangeUserMfa(actor, target.Id, "disable", revision, request, true, Ct));
        Assert.Equal(409, denied.Status); Assert.Equal("mfa_enrollment_required", denied.Code);
        Assert.False(status.CanDisable, "The public state still offers disabling a pending recovery.");
        Assert.True(before == await lab.SnapshotAll(), "Rejected disable changed recovery state.");
        var retry = await lab.Store.AuthenticateForLogin(target.UserName, Lab.Password, Ct);
        Assert.Null(retry.Session); Assert.Equal("enroll", retry.ChallengePurpose);
    }

    private static async Task Prepare(Lab lab)
    {
        await lab.Policy(50); await lab.Legacy(lab.Admin.Id); await lab.Factor(lab.Admin.Id);
        await lab.Execute("UPDATE app_mfa_factor SET confirmed_at=clock_timestamp() WHERE user_id=@user", ("user", lab.Admin.Id));
    }
    private static Task<long> Revision(Lab lab) => lab.Count("SELECT revision FROM systemhaus WHERE id=@house", ("house", lab.House));
    private static async Task<MfaRecoveryCodesGeneration> Generate(Lab lab, Actor actor) =>
        await lab.Store.GenerateOwnRecoveryCodes(actor, Lab.Password, await Revision(lab), Guid.NewGuid(), true, Ct);
    private static Task<long> ActiveGlobals(Lab lab) => lab.Count("""
        SELECT count(*) FROM app_user u WHERE u.systemhaus_id=@house AND u.active AND
          (SELECT count(DISTINCT g.capability)=2 FROM user_group_member m JOIN permission_grant g
             ON g.systemhaus_id=m.systemhaus_id AND g.user_group_id=m.group_id
           WHERE m.systemhaus_id=u.systemhaus_id AND m.user_id=u.id
             AND g.customer_id IS NULL AND g.customer_group_id IS NULL
             AND g.capability IN ('security.manage','systemhaus.manage'))
        """, ("house", lab.House));
    private static async Task<string> Authority(Lab lab)
    {
        await using var db = await lab.RuntimeSource.OpenConnectionAsync(Ct);
        await using var command = new NpgsqlCommand("""
            SELECT jsonb_build_object(
              'user',(SELECT to_jsonb(t) FROM app_user t WHERE id=@user),
              'groups',(SELECT jsonb_agg(to_jsonb(t) ORDER BY id) FROM user_group t WHERE systemhaus_id=@house),
              'members',(SELECT jsonb_agg(to_jsonb(t) ORDER BY user_id,group_id) FROM user_group_member t WHERE systemhaus_id=@house),
              'grants',(SELECT jsonb_agg(to_jsonb(t) ORDER BY id) FROM permission_grant t WHERE systemhaus_id=@house))::text
            """, db);
        command.Parameters.AddWithValue("user", lab.Admin.Id); command.Parameters.AddWithValue("house", lab.House);
        return (string)(await command.ExecuteScalarAsync(Ct))!;
    }
}
