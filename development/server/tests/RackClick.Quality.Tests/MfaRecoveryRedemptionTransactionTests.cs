using Npgsql;
using RackClick.Domain;
using RackClick.Server;
using Xunit;
using Lab = RackClick.Quality.Tests.MfaAccountManagementTests.Laboratory;

namespace RackClick.Quality.Tests;

// F-08.03: native PostgreSQL only in a fresh isolated fixture; no installed host/store is used.
[Collection("MfaHttp")]
public sealed class MfaRecoveryRedemptionTransactionTests
{
    private static CancellationToken Ct => TestContext.Current.CancellationToken;
    private sealed class NoKeys : IMfaKeyProvider
    {
        public byte[] GetKey(int version) => throw new InvalidOperationException("Recovery must not read TOTP material.");
        public (int Version, byte[] Key) GetActiveKey() => throw new InvalidOperationException("Recovery must not read TOTP material.");
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task OverlappingRedemptionsCommitOneAccountRecoveryAndLeaveAnotherAccountUntouched(bool differentCodes)
    {
        await using var lab = await Lab.Create();
        await lab.Policy(10);
        await lab.Factor(lab.Admin.Id);
        await lab.Session(lab.Admin.Id, true); // Two old sessions must both be revoked.
        var other = await lab.AddUser("unrelated.recovery.user", factor: true, verified: true);
        await lab.Execute("UPDATE app_mfa_factor SET confirmed_at=clock_timestamp()");
        async Task<MfaRecoveryCodesGeneration> Generate(Actor actor) =>
            await lab.Store.GenerateOwnRecoveryCodes(actor, Lab.Password,
                await lab.Count("SELECT revision FROM systemhaus WHERE id=@house", ("house", lab.House)), Guid.NewGuid(), true, Ct);
        var unrelatedCodes = await Generate(other);
        var generated = await Generate(lab.Admin);
        var a = await Challenge(lab, lab.Admin.Id, "verify");
        var b = await Challenge(lab, lab.Admin.Id, "verify");
        await Challenge(lab, lab.Admin.Id, "enroll"); // A stale challenge of another purpose also retires.
        await Challenge(lab, other.Id, "verify");
        var unrelatedBefore = await OtherAccount(lab, other.Id);
        var policyBefore = await lab.Snapshot("app_mfa_policy");
        var role = new NpgsqlConnectionStringBuilder(lab.RuntimeConnection).Username!;
        Assert.Matches("^rc_mfa_dashboard_runtime_[a-f0-9]{32}$", role);
        // Test-only owner DDL: record transaction/role/relationship, never values of affected rows.
        await lab.Execute($"""
            CREATE TABLE f0803_writes(id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
              rel text NOT NULL,verb text NOT NULL,actor text NOT NULL,tx bigint NOT NULL);
            GRANT SELECT,INSERT ON f0803_writes TO {role};
            GRANT USAGE ON SEQUENCE f0803_writes_id_seq TO {role};
            CREATE FUNCTION f0803_capture() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
              INSERT INTO f0803_writes(rel,verb,actor,tx) VALUES(TG_TABLE_NAME,TG_OP,current_user,txid_current());
              IF TG_OP='DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF;
            END $$;
            """);
        foreach (var (table, verbs) in new[]
        {
            ("app_mfa_recovery_code", "UPDATE"), ("app_mfa_factor", "UPDATE"), ("app_mfa_user", "UPDATE"),
            ("app_session", "DELETE"), ("app_mfa_challenge", "INSERT OR UPDATE"), ("audit_event", "INSERT")
        })
            await lab.Execute($"CREATE TRIGGER f0803_{table} AFTER {verbs} ON {table} FOR EACH ROW EXECUTE FUNCTION f0803_capture()");

        var store = new MfaStore(lab.RuntimeSource, new NoKeys());
        async Task<MfaStore.RecoveryEnrollmentChallenge?> Try((string Token, string Csrf) challenge, string code)
        {
            try { return await store.RedeemRecoveryCode(challenge.Token, code, challenge.Csrf, Ct); }
            catch (DomainError error)
            {
                Assert.Equal(401, error.Status); Assert.Equal("mfa_challenge_invalid", error.Code); return null;
            }
        }
        await using var blocker = await lab.RuntimeSource.OpenConnectionAsync(Ct);
        await using var transaction = await blocker.BeginTransactionAsync(Ct);
        await using (var hold = new NpgsqlCommand("SELECT id FROM app_user WHERE id=@user FOR UPDATE", blocker, transaction))
        { hold.Parameters.AddWithValue("user", lab.Admin.Id); await hold.ExecuteScalarAsync(Ct); }
        var first = Try(a, generated.Codes![0]);
        var second = Try(b, generated.Codes![differentCodes ? 1 : 0]);
        var waiting = 0L;
        try
        {
            // Observe with the worker role: pg_stat_activity hides other roles' query text.
            await using var observer = await lab.RuntimeSource.OpenConnectionAsync(Ct);
            for (var attempt = 0; attempt < 250; attempt++)
            {
                await using var observe = new NpgsqlCommand("""
                    SELECT count(DISTINCT l.pid) FROM pg_catalog.pg_locks l
                    JOIN pg_catalog.pg_stat_activity a ON a.pid=l.pid
                    WHERE NOT l.granted AND a.datname=current_database() AND a.wait_event_type='Lock'
                      AND a.query LIKE '%FROM app_user WHERE systemhaus_id=%FOR UPDATE%'
                    """, observer);
                waiting = Convert.ToInt64(await observe.ExecuteScalarAsync(Ct));
                if (waiting >= 2 || first.IsCompleted || second.IsCompleted) break;
                await Task.Delay(20, Ct);
            }
        }
        finally { await transaction.CommitAsync(Ct); }
        var results = await Task.WhenAll(first, second);
        Assert.True(waiting >= 2, "Two recovery requests were not observed waiting concurrently.");
        var recovered = Assert.Single(results, value => value is not null)!;
        Assert.Equal(1, results.Count(value => value is null));
        Assert.Equal("enroll", recovered.Purpose);
        Assert.Equal(10, await lab.Count("SELECT count(*) FROM app_mfa_recovery_code WHERE user_id=@user AND consumed_at IS NOT NULL", ("user", lab.Admin.Id)));
        Assert.Equal(0, await lab.Count("SELECT count(*) FROM app_session WHERE user_id=@user", ("user", lab.Admin.Id)));
        Assert.Equal(3, await lab.Count("SELECT count(*) FROM app_mfa_challenge WHERE user_id=@user AND consumed_at IS NOT NULL", ("user", lab.Admin.Id)));
        Assert.Equal(1, await lab.Count("SELECT count(*) FROM app_mfa_challenge WHERE user_id=@user AND purpose='enroll' AND consumed_at IS NULL AND token_hash=@token",
            ("user", lab.Admin.Id), ("token", Secrets.Digest(recovered.ChallengeToken))));
        Assert.Equal(1, await lab.Count("SELECT count(*) FROM app_mfa_user WHERE user_id=@user AND enrollment_pending AND revision=2", ("user", lab.Admin.Id)));
        Assert.Equal(1, await lab.Count("SELECT count(*) FROM app_mfa_factor WHERE user_id=@user AND state='disabled'", ("user", lab.Admin.Id)));
        Assert.Equal(1, await lab.Count("SELECT count(*) FROM audit_event WHERE action='auth.mfa.recovery_code_redeemed' AND actor_id=@user AND resource_id=@user",
            ("user", lab.Admin.Id)));
        Assert.Equal(1, await lab.Count("""
            SELECT count(*) FROM audit_event WHERE action='auth.mfa.recovery_code_redeemed'
              AND (after_json->>'retiredCodes')::int=10 AND (after_json->>'revokedSessions')::int=2
              AND (after_json->>'revokedChallenges')::int=3 AND (after_json->>'enrollmentPending')::boolean
            """));
        Assert.Equal(6, await lab.Count("""
            SELECT count(DISTINCT rel) FROM f0803_writes
            WHERE tx=(SELECT tx FROM f0803_writes WHERE rel='audit_event')
            """));
        Assert.Equal(0, await lab.Count("SELECT count(*) FROM f0803_writes WHERE actor<>@role", ("role", role)));
        Assert.True(unrelatedBefore == await OtherAccount(lab, other.Id), "Recovery modified another account.");
        Assert.True(policyBefore == await lab.Snapshot("app_mfa_policy"), "Recovery changed the grace policy.");
        var state = await lab.SnapshotAll();
        foreach (var value in generated.Codes!.Concat(unrelatedCodes.Codes!))
        {
            Assert.False(state.Contains(value, StringComparison.Ordinal), "Persisted state contains a recovery value.");
            Assert.False(state.Contains(value.Replace("-", "", StringComparison.Ordinal), StringComparison.Ordinal), "Persisted state contains a normalized recovery value.");
        }
        foreach (var value in new[] { a.Token, a.Csrf, b.Token, b.Csrf, recovered.ChallengeToken, recovered.Csrf })
            Assert.False(state.Contains(value, StringComparison.Ordinal), "Persisted state contains an unhashed challenge credential.");
    }

    private static async Task<(string Token, string Csrf)> Challenge(Lab lab, Guid user, string purpose)
    {
        var token = Secrets.Token(); var csrf = Secrets.Token();
        await lab.Execute("""
            WITH stamp AS (SELECT clock_timestamp() AS value)
            INSERT INTO app_mfa_challenge(token_hash,systemhaus_id,user_id,purpose,csrf_hash,policy_revision,created_at,expires_at)
            SELECT @token,@house,@user,@purpose,@csrf,m.revision,value,value+interval '5 minutes'
            FROM stamp,app_mfa_user m WHERE m.systemhaus_id=@house AND m.user_id=@user
            """, ("token", Secrets.Digest(token)), ("csrf", Secrets.Digest(csrf)), ("house", lab.House), ("user", user), ("purpose", purpose));
        return (token, csrf);
    }
    private static async Task<string> OtherAccount(Lab lab, Guid user)
    {
        await using var db = await lab.RuntimeSource.OpenConnectionAsync(Ct);
        await using var query = new NpgsqlCommand("""
            SELECT jsonb_build_object(
              'user',(SELECT jsonb_agg(to_jsonb(t)) FROM app_user t WHERE id=@user),
              'policy',(SELECT jsonb_agg(to_jsonb(t)) FROM app_mfa_user t WHERE user_id=@user),
              'factor',(SELECT jsonb_agg(to_jsonb(t)) FROM app_mfa_factor t WHERE user_id=@user),
              'codes',(SELECT jsonb_agg(to_jsonb(t) ORDER BY code_hash) FROM app_mfa_recovery_code t WHERE user_id=@user),
              'sessions',(SELECT jsonb_agg(to_jsonb(t) ORDER BY token_hash) FROM app_session t WHERE user_id=@user),
              'challenges',(SELECT jsonb_agg(to_jsonb(t) ORDER BY token_hash) FROM app_mfa_challenge t WHERE user_id=@user))::text
            """, db);
        query.Parameters.AddWithValue("user", user);
        return (string)(await query.ExecuteScalarAsync(Ct))!;
    }
}
