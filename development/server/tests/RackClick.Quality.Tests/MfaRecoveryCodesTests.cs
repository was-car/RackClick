using System.Security.Cryptography;
using Npgsql;
using OtpNet;
using RackClick.Domain;
using RackClick.Server;
using Xunit;
using AccountLab = RackClick.Quality.Tests.MfaAccountManagementTests.Laboratory;

namespace RackClick.Quality.Tests;

public sealed class MfaRecoveryCodeCodecTests
{
    [Fact]
    public void CodesHave128RandomBitsAndOnlyVersionedSaltedAccountBoundHashesAreComparable()
    {
        Guid house = Guid.NewGuid(), user = Guid.NewGuid();
        string code = MfaRecoveryCodeCodec.NewCode();
        Assert.True(code.Length == 39 && code.Replace("-", "", StringComparison.Ordinal).Length == 32);
        string first = MfaRecoveryCodeCodec.Hash(code, house, user), second = MfaRecoveryCodeCodec.Hash(code, house, user);
        Assert.True(first.Length == 102 && first.StartsWith("rck1$", StringComparison.Ordinal));
        Assert.False(first == second);
        Assert.False(first.Contains(code, StringComparison.Ordinal));
        Assert.True(MfaRecoveryCodeCodec.Matches(code, first, house, user));
        Assert.True(MfaRecoveryCodeCodec.Matches(" " + code.ToLowerInvariant() + " ", first, house, user));
        Assert.False(MfaRecoveryCodeCodec.Matches(code, first, Guid.NewGuid(), user));
        Assert.False(MfaRecoveryCodeCodec.Matches(code, first, house, Guid.NewGuid()));
    }

    [Theory]
    [InlineData(null)]
    [InlineData("")]
    [InlineData("123456")]
    [InlineData("GGGG-GGGG-GGGG-GGGG-GGGG-GGGG-GGGG-GGGG")]
    public void InvalidPresentedCodesFailWithoutThrowingOrRevealingInput(string? value)
    {
        Guid house = Guid.NewGuid(), user = Guid.NewGuid();
        string hash = MfaRecoveryCodeCodec.Hash(MfaRecoveryCodeCodec.NewCode(), house, user);
        Assert.False(MfaRecoveryCodeCodec.Matches(value, hash, house, user));
    }

    [Fact]
    public void UnpairedUnicodeIsInvalidWithoutBeingReflectedByTestDiscovery()
    {
        Guid house=Guid.NewGuid(),user=Guid.NewGuid();
        string hash=MfaRecoveryCodeCodec.Hash(MfaRecoveryCodeCodec.NewCode(),house,user);
        Assert.False(MfaRecoveryCodeCodec.Matches(new string((char)0xD800,32),hash,house,user));
    }

    [Theory]
    [InlineData("")]
    [InlineData("rck2$00000000000000000000000000000000$0000000000000000000000000000000000000000000000000000000000000000")]
    [InlineData("rck1$0000000000000000000000000000000G$0000000000000000000000000000000000000000000000000000000000000000")]
    public void UnknownOrMalformedStoredHashesAreNotAccepted(string value) =>
        Assert.False(MfaRecoveryCodeCodec.Matches(MfaRecoveryCodeCodec.NewCode(), value, Guid.NewGuid(), Guid.NewGuid()));
}

[Collection("MfaHttp")]
public sealed class MfaRecoveryCodesTests
{
    private static CancellationToken Ct => TestContext.Current.CancellationToken;

    [Fact]
    public async Task OwnGenerationStoresOnlySaltedHashesAndSafeReceiptAndOnlyShowsCodesOnce()
    {
        await using var lab = await AccountLab.Create();
        await Active(lab, lab.Admin);
        long revision = await Revision(lab);
        Guid request = Guid.NewGuid();
        var generated = await lab.Store.GenerateOwnRecoveryCodes(lab.Admin, AccountLab.Password, revision, request, true, Ct);
        Assert.True(generated.CodesAvailable && generated.Codes?.Length == 10);
        Assert.True(generated.Codes!.Distinct(StringComparer.Ordinal).Count() == 10);
        Assert.Equal(revision + 1, generated.SystemhausRevision);
        string state = await lab.SnapshotAll();
        foreach (string code in generated.Codes!) Assert.False(state.Contains(code, StringComparison.Ordinal));
        Assert.Equal(10, await lab.Count("SELECT count(*) FROM app_mfa_recovery_code WHERE code_hash LIKE 'rck1$%' AND consumed_at IS NULL"));
        string before = await lab.SnapshotAll();
        var repeated = await lab.Store.GenerateOwnRecoveryCodes(lab.Admin, AccountLab.Password, revision, request, true, Ct);
        Assert.False(repeated.CodesAvailable); Assert.Null(repeated.Codes);
        var receipt = await lab.Store.ReadOwnRecoveryCodesReceipt(lab.Admin, request, Ct);
        Assert.NotNull(receipt); Assert.False(receipt.CodesAvailable); Assert.Null(receipt.Codes);
        Assert.True(before == await lab.SnapshotAll());
        var status = await lab.Store.ReadOwnRecoveryCodeStatus(lab.Admin, Ct);
        Assert.Equal(10, status.Remaining); Assert.True(status.CanGenerate && status.SessionMfaVerified);
    }

    [Fact]
    public async Task RotationRetiresOldCodesAndKeepsAnUnknownReceiptAbsent()
    {
        await using var lab = await AccountLab.Create();
        var original = await Generate(lab);
        var replacement = await lab.Store.GenerateOwnRecoveryCodes(lab.Admin, AccountLab.Password, await Revision(lab), Guid.NewGuid(), true, Ct);
        Assert.True(replacement.CodesAvailable && replacement.Codes?.Length == 10);
        var challenge = await Challenge(lab, lab.Admin.Id);
        var error = await Assert.ThrowsAsync<DomainError>(() => Recovery(lab).RedeemRecoveryCode(challenge.Token, original.Codes![0], challenge.Csrf, Ct));
        Assert.Equal("mfa_code_invalid", error.Message);
        Assert.Null(await lab.Store.ReadOwnRecoveryCodesReceipt(lab.Admin, Guid.NewGuid(), Ct));
        Assert.Equal(10, await lab.Count("SELECT count(*) FROM app_mfa_recovery_code WHERE consumed_at IS NULL"));
    }

    [Fact]
    public async Task GenerationNeedsMfaCurrentPasswordActiveFactorAndMatchingRevision()
    {
        await using var lab = await AccountLab.Create();
        await Active(lab, lab.Admin);
        var unverified = await lab.Session(lab.Admin.Id, false);
        string before = await lab.SnapshotAll(); long revision = await Revision(lab);
        Assert.Equal("mfa_verification_required", (await Assert.ThrowsAsync<DomainError>(() => lab.Store.GenerateOwnRecoveryCodes(unverified, AccountLab.Password, revision, Guid.NewGuid(), true, Ct))).Message);
        Assert.Equal("mfa_reauthentication_required", (await Assert.ThrowsAsync<DomainError>(() => lab.Store.GenerateOwnRecoveryCodes(lab.Admin, "Not-the-current-password!", revision, Guid.NewGuid(), true, Ct))).Message);
        Assert.Equal("revision_conflict", (await Assert.ThrowsAsync<DomainError>(() => lab.Store.GenerateOwnRecoveryCodes(lab.Admin, AccountLab.Password, revision+1, Guid.NewGuid(), true, Ct))).Message);
        Assert.Equal("mfa_unavailable", (await Assert.ThrowsAsync<DomainError>(() => lab.Store.GenerateOwnRecoveryCodes(lab.Admin, AccountLab.Password, revision, Guid.NewGuid(), false, Ct))).Message);
        Assert.True(before == await lab.SnapshotAll());
        await lab.Execute("UPDATE app_mfa_factor SET state='disabled'");
        Assert.Equal("mfa_active_factor_required", (await Assert.ThrowsAsync<DomainError>(() => lab.Store.GenerateOwnRecoveryCodes(lab.Admin, AccountLab.Password, revision, Guid.NewGuid(), true, Ct))).Message);
    }

    [Fact]
    public async Task AnotherActorCannotReadAReceiptAndConsumedRequestCannotChangeItsIntent()
    {
        await using var lab = await AccountLab.Create();
        var generated = await Generate(lab);
        var other = await lab.AddUser("recovery.other");
        Assert.Null(await lab.Store.ReadOwnRecoveryCodesReceipt(other, generated.RequestId, Ct));
        var error = await Assert.ThrowsAsync<DomainError>(() => lab.Store.GenerateOwnRecoveryCodes(lab.Admin, AccountLab.Password, generated.SystemhausRevision, generated.RequestId, true, Ct));
        Assert.Equal("request_id_reused", error.Message);
        await lab.Execute("DELETE FROM app_session WHERE user_id=@user", ("user", lab.Admin.Id));
        await Assert.ThrowsAsync<DomainError>(() => lab.Store.ReadOwnRecoveryCodesReceipt(lab.Admin, generated.RequestId, Ct));
    }

    [Fact]
    public async Task GenerationAuditFailureRollsBackCodesRevisionAndReceipt()
    {
        await using var lab = await AccountLab.Create();
        await Generate(lab); string before = await lab.SnapshotAll();
        await AuditFailure(lab);
        long revision=await Revision(lab);
        await Assert.ThrowsAsync<PostgresException>(() => lab.Store.GenerateOwnRecoveryCodes(lab.Admin, AccountLab.Password, revision, Guid.NewGuid(), true, Ct));
        Assert.True(before == await lab.SnapshotAll());
    }

    [Fact]
    public async Task RecoveryReturnsOnlyFreshEnrollmentAndCannotReadTheTotpKey()
    {
        await using var lab = await AccountLab.Create();
        var generated = await Generate(lab); var challenge = await Challenge(lab, lab.Admin.Id);
        await Challenge(lab, lab.Admin.Id);
        var result = await Recovery(lab).RedeemRecoveryCode(challenge.Token, generated.Codes![0], challenge.Csrf, Ct);
        Assert.Equal("enroll", result.Purpose);
        Assert.Equal(0, await lab.Count("SELECT count(*) FROM app_session"));
        Assert.Equal(0, await lab.Count("SELECT count(*) FROM app_mfa_recovery_code WHERE consumed_at IS NULL"));
        Assert.Equal(1, await lab.Count("SELECT count(*) FROM app_mfa_challenge WHERE purpose='enroll' AND consumed_at IS NULL"));
        Assert.Equal(0, await lab.Count("SELECT count(*) FROM app_mfa_challenge WHERE purpose='verify' AND consumed_at IS NULL"));
        Assert.Equal(1, await lab.Count("SELECT count(*) FROM app_mfa_user WHERE mfa_required AND enrollment_pending"));
        Assert.Equal(1, await lab.Count("SELECT count(*) FROM app_mfa_factor WHERE state='disabled'"));
        Assert.False(result.ToString().Contains(result.ChallengeToken, StringComparison.Ordinal));
        string state = await lab.SnapshotAll();
        foreach (string code in generated.Codes!) Assert.False(state.Contains(code, StringComparison.Ordinal));
    }

    [Fact]
    public async Task OnlyOneConcurrentUseCanSucceedEvenFromDifferentVerifyChallenges()
    {
        await using var lab = await AccountLab.Create();
        var generated = await Generate(lab); var a = await Challenge(lab, lab.Admin.Id); var b = await Challenge(lab, lab.Admin.Id);
        async Task<bool> Try((string Token,string Csrf) challenge)
        {
            try { await Recovery(lab).RedeemRecoveryCode(challenge.Token, generated.Codes![0], challenge.Csrf, Ct); return true; }
            catch (DomainError e) { Assert.Equal("mfa_challenge_invalid", e.Message); return false; }
        }
        bool[] results = await Task.WhenAll(Try(a), Try(b));
        Assert.Single(results, result => result);
        Assert.Equal(1, await lab.Count("SELECT count(*) FROM app_mfa_challenge WHERE purpose='enroll' AND consumed_at IS NULL"));
        Assert.Equal(0, await lab.Count("SELECT count(*) FROM app_session"));
    }

    [Fact]
    public async Task ReplayWrongPurposeAndWrongCsrfCannotConsumeAValidEnrollmentOrCode()
    {
        await using var lab = await AccountLab.Create();
        var generated = await Generate(lab); var challenge = await Challenge(lab, lab.Admin.Id);
        string before = await lab.SnapshotAll();
        Assert.Equal("csrf_invalid", (await Assert.ThrowsAsync<DomainError>(() => Recovery(lab).RedeemRecoveryCode(challenge.Token, generated.Codes![0], "wrong", Ct))).Message);
        Assert.True(before == await lab.SnapshotAll());
        var enrolled = await Challenge(lab, lab.Admin.Id, "enroll");before = await lab.SnapshotAll();
        Assert.Equal("mfa_challenge_invalid", (await Assert.ThrowsAsync<DomainError>(() => Recovery(lab).RedeemRecoveryCode(enrolled.Token, generated.Codes![0], enrolled.Csrf, Ct))).Message);
        Assert.True(before == await lab.SnapshotAll());
        await Recovery(lab).RedeemRecoveryCode(challenge.Token, generated.Codes![0], challenge.Csrf, Ct);
        Assert.Equal("mfa_challenge_invalid", (await Assert.ThrowsAsync<DomainError>(() => Recovery(lab).RedeemRecoveryCode(challenge.Token, generated.Codes![0], challenge.Csrf, Ct))).Message);
    }

    [Fact]
    public async Task ExpiredOrChangedPolicyChallengeDoesNotConsumeRecoveryCodes()
    {
        await using var lab = await AccountLab.Create();
        var generated = await Generate(lab); var expired = await Challenge(lab, lab.Admin.Id);
        await lab.Execute("UPDATE app_mfa_challenge SET expires_at=created_at WHERE token_hash=@token", ("token", Secrets.Digest(expired.Token)));
        Assert.Equal("mfa_challenge_invalid", (await Assert.ThrowsAsync<DomainError>(() => Recovery(lab).RedeemRecoveryCode(expired.Token, generated.Codes![0], expired.Csrf, Ct))).Message);
        var changed = await Challenge(lab, lab.Admin.Id); await lab.Execute("UPDATE app_mfa_user SET revision=revision+1");
        Assert.Equal("mfa_challenge_invalid", (await Assert.ThrowsAsync<DomainError>(() => Recovery(lab).RedeemRecoveryCode(changed.Token, generated.Codes![0], changed.Csrf, Ct))).Message);
        Assert.Equal(10, await lab.Count("SELECT count(*) FROM app_mfa_recovery_code WHERE consumed_at IS NULL"));
    }

    [Fact]
    public async Task ExpiryWhileWaitingForTheCodeRowIsMeasuredAfterThatLastLock()
    {
        await using var lab=await AccountLab.Create();
        var generated=await Generate(lab);var challenge=await Challenge(lab,lab.Admin.Id);
        await lab.Execute("UPDATE app_mfa_challenge SET expires_at=clock_timestamp()+interval '3 seconds' WHERE token_hash=@token",("token",Secrets.Digest(challenge.Token)));
        await using var blocker=new NpgsqlConnection(lab.RuntimeConnection);await blocker.OpenAsync(Ct);
        await using var blocking=await blocker.BeginTransactionAsync(Ct);
        await using (var command=new NpgsqlCommand("SELECT code_hash FROM app_mfa_recovery_code WHERE user_id=@user FOR UPDATE",blocker,blocking))
        {
            command.Parameters.AddWithValue("user",lab.Admin.Id);
            await command.ExecuteNonQueryAsync(Ct);
        }
        Task<MfaStore.RecoveryEnrollmentChallenge> recovery=Recovery(lab).RedeemRecoveryCode(challenge.Token,generated.Codes![0],challenge.Csrf,Ct);
        try
        {
            await using var observer=new NpgsqlConnection(lab.RuntimeConnection);await observer.OpenAsync(Ct);
            bool waiting=false;
            for(int attempt=0;attempt<100&&!waiting;attempt++)
            {
                await using var command=new NpgsqlCommand("""
                    SELECT EXISTS(SELECT 1 FROM pg_stat_activity WHERE datname=current_database()
                     AND pid<>pg_backend_pid() AND wait_event_type='Lock'
                     AND query LIKE '%SELECT code_hash FROM app_mfa_recovery_code%')
                    """,observer);
                waiting=await command.ExecuteScalarAsync(Ct) is true;
                if(!waiting)await Task.Delay(20,Ct);
            }
            Assert.True(waiting,"The recovery must demonstrably wait on the locked code row.");
            await Task.Delay(3200,Ct);
        }
        finally{await blocking.RollbackAsync(Ct);}
        Assert.Equal("mfa_challenge_invalid",(await Assert.ThrowsAsync<DomainError>(()=>recovery)).Message);
        Assert.Equal(10,await lab.Count("SELECT count(*) FROM app_mfa_recovery_code WHERE consumed_at IS NULL"));
        Assert.Equal(0,await lab.Count("SELECT count(*) FROM app_mfa_user WHERE enrollment_pending"));
    }

    [Fact]
    public async Task InvalidGuessesAreBoundedAcrossRecoveryAndNormalFactorUse()
    {
        await using var lab = await AccountLab.Create();
        var generated = await Generate(lab); var challenge = await Challenge(lab, lab.Admin.Id);
        for (int attempt=0; attempt<5; attempt++)
            Assert.Equal("mfa_code_invalid", (await Assert.ThrowsAsync<DomainError>(() => Recovery(lab).RedeemRecoveryCode(challenge.Token, "invalid", challenge.Csrf, Ct))).Message);
        Assert.Equal("mfa_challenge_invalid", (await Assert.ThrowsAsync<DomainError>(() => Recovery(lab).RedeemRecoveryCode(challenge.Token, generated.Codes![0], challenge.Csrf, Ct))).Message);
        Assert.Equal(1, await lab.Count("SELECT count(*) FROM app_mfa_factor WHERE failed_attempts=5 AND locked_until>clock_timestamp()"));
        Assert.Equal(1, await lab.Count("SELECT count(*) FROM app_mfa_challenge WHERE attempts=5 AND consumed_at IS NOT NULL"));
        Assert.Equal(10, await lab.Count("SELECT count(*) FROM app_mfa_recovery_code WHERE consumed_at IS NULL"));
    }

    [Fact]
    public async Task RecoveryAuditFailureRollsBackEverythingIncludingTheUsedCode()
    {
        await using var lab = await AccountLab.Create();
        var generated = await Generate(lab); var challenge = await Challenge(lab, lab.Admin.Id);string before = await lab.SnapshotAll();
        await AuditFailure(lab);
        await Assert.ThrowsAsync<PostgresException>(() => Recovery(lab).RedeemRecoveryCode(challenge.Token, generated.Codes![0], challenge.Csrf, Ct));
        Assert.True(before == await lab.SnapshotAll());
    }

    [Fact]
    public async Task NewFactorMustBeConfirmedBeforeRecoveryCreatesAnyNewSession()
    {
        await using var lab = await AccountLab.Create();
        var generated = await Generate(lab); var challenge = await Challenge(lab, lab.Admin.Id);
        var recovered = await Recovery(lab).RedeemRecoveryCode(challenge.Token, generated.Codes![0], challenge.Csrf, Ct);
        var keys = new SyntheticKeys();var store = new MfaStore(lab.RuntimeSource, keys);
        var started = await store.StartEnrollment(recovered.ChallengeToken, recovered.Csrf, Ct);
        Assert.Equal(0, await lab.Count("SELECT count(*) FROM app_session"));
        byte[] secret = Base32Encoding.ToBytes(started.SecretBase32);
        string code;
        try { code = new Totp(secret).ComputeTotp(DateTime.UtcNow); }
        finally { CryptographicOperations.ZeroMemory(secret); }
        var session = await store.ConfirmEnrollment(recovered.ChallengeToken, code, recovered.Csrf, Ct);
        Assert.Equal(1, await lab.Count("SELECT count(*) FROM app_session WHERE mfa_verified_at IS NOT NULL AND token_hash=@token", ("token", Secrets.Digest(session.Token))));
        Assert.Equal(0, await lab.Count("SELECT count(*) FROM app_mfa_user WHERE enrollment_pending"));
        Assert.Equal(0, await lab.Count("SELECT count(*) FROM app_mfa_recovery_code WHERE consumed_at IS NULL"));
    }

    [Fact]
    public async Task AdministrativeResetInvalidatesGeneratedCodesWithoutChangingGraceActivation()
    {
        await using var lab = await AccountLab.Create();
        var target = await lab.AddUser("recovery.target", verified:true);await Active(lab,target);await lab.Policy(10);
        var generated=await lab.Store.GenerateOwnRecoveryCodes(target,AccountLab.Password,await Revision(lab),Guid.NewGuid(),true,Ct);
        string policy=await lab.Snapshot("app_mfa_policy");
        await lab.Store.ChangeUserMfa(lab.Admin,target.Id,"reset",generated.SystemhausRevision,Guid.NewGuid(),true,Ct);
        Assert.Equal(0,await lab.Count("SELECT count(*) FROM app_mfa_recovery_code WHERE user_id=@user",("user",target.Id)));
        Assert.True(policy==await lab.Snapshot("app_mfa_policy"));
    }

    private static async Task Active(AccountLab lab, Actor actor)
    {
        await lab.Factor(actor.Id);
        await lab.Execute("UPDATE app_mfa_factor SET confirmed_at=clock_timestamp() WHERE user_id=@user", ("user",actor.Id));
    }
    private static async Task<MfaRecoveryCodesGeneration> Generate(AccountLab lab)
    {
        await Active(lab,lab.Admin);
        return await lab.Store.GenerateOwnRecoveryCodes(lab.Admin,AccountLab.Password,await Revision(lab),Guid.NewGuid(),true,Ct);
    }
    private static Task<long> Revision(AccountLab lab) => lab.Count("SELECT revision FROM systemhaus WHERE id=@house",("house",lab.House));
    private static async Task<(string Token,string Csrf)> Challenge(AccountLab lab, Guid user, string purpose="verify")
    {
        string token=Secrets.Token(),csrf=Secrets.Token();
        await lab.Execute("""
            WITH stamp AS (SELECT clock_timestamp() AS value)
            INSERT INTO app_mfa_challenge(token_hash,systemhaus_id,user_id,purpose,csrf_hash,policy_revision,created_at,expires_at)
            SELECT @token,@house,@user,@purpose,@csrf,m.revision,value,value+interval '5 minutes'
            FROM stamp,app_mfa_user m WHERE m.systemhaus_id=@house AND m.user_id=@user
            """,("token",Secrets.Digest(token)),("house",lab.House),("user",user),("purpose",purpose),("csrf",Secrets.Digest(csrf)));
        return(token,csrf);
    }
    private static MfaStore Recovery(AccountLab lab) => new(lab.RuntimeSource,new ThrowingKeys());
    private static Task<int> AuditFailure(AccountLab lab) => lab.Execute("""
        CREATE FUNCTION recovery_test_fail_audit() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'synthetic audit failure'; END $$;
        CREATE TRIGGER recovery_test_fail_audit BEFORE INSERT ON audit_event FOR EACH ROW EXECUTE FUNCTION recovery_test_fail_audit();
        """);
    private sealed class ThrowingKeys : IMfaKeyProvider
    {
        public byte[] GetKey(int version) => throw new InvalidOperationException("Recovery must not read a TOTP key.");
        public (int Version,byte[] Key) GetActiveKey() => throw new InvalidOperationException("Recovery must not read a TOTP key.");
    }
    private sealed class SyntheticKeys : IMfaKeyProvider
    {
        public byte[] GetKey(int version) => version==1 ? new byte[32] : throw new InvalidOperationException("test_key_unavailable");
        public (int Version,byte[] Key) GetActiveKey() => (1,new byte[32]);
    }
}
