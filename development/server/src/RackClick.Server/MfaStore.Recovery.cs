using System.Text.Json;
using Npgsql;
using RackClick.Domain;

namespace RackClick.Server;

public sealed partial class MfaStore
{
    /// <summary>Recovery grants only a fresh enrollment challenge; it never contains or creates an API session.</summary>
    public sealed record RecoveryEnrollmentChallenge(string ChallengeToken, string Csrf)
    {
        public string Purpose => "enroll";
        public override string ToString() => nameof(RecoveryEnrollmentChallenge);
    }

    public async Task<RecoveryEnrollmentChallenge> RedeemRecoveryCode(string challengeToken, string? code, string csrfHeader, CancellationToken ct)
    {
        string tokenHash = Secrets.Digest(challengeToken);
        await using var db = await source.OpenConnectionAsync(ct);
        await using var tx = await db.BeginTransactionAsync(ct);
        // This reuses the verified account -> factor -> challenge -> policy lock order,
        // and measures expiry only after every lock. It never decrypts a TOTP secret.
        var state = await LockChallenge(db, tx, tokenHash, "verify", ct);
        if (state is null) throw new DomainError(401, "mfa_challenge_invalid");
        if (!Secrets.Matches(csrfHeader ?? "", state.CsrfHash)) throw new DomainError(403, "csrf_invalid");
        if (!state.AccountUsable || !state.ChallengeAvailable || !state.NotExpired || state.FactorLocked
            || state.FactorState != "active" || !state.PolicyPresent || !state.MfaRequired
            || state.EnrollmentPending || state.CurrentRevision != state.IssuedRevision)
        {
            await Burn(db, tx, tokenHash, ct);
            await tx.CommitAsync(ct);
            throw new DomainError(401, "mfa_challenge_invalid");
        }

        string? match = null;
        var stored = new List<string>();
        await using (var query = Command(db, tx, """
            SELECT code_hash FROM app_mfa_recovery_code
            WHERE systemhaus_id=@house AND user_id=@user AND consumed_at IS NULL
            ORDER BY code_hash LIMIT 11 FOR UPDATE
            """, ("house", state.Systemhaus), ("user", state.User)))
        await using (var rows = await query.ExecuteReaderAsync(ct))
            while (await rows.ReadAsync(ct)) stored.Add(rows.GetString(0));
        // Code-row locks are additional waits after LockChallenge. Recheck the
        // challenge with PostgreSQL's clock after these waits as well.
        await using (var current = Command(db, tx, """
            SELECT consumed_at IS NULL AND attempts<@max AND expires_at>clock_timestamp()
            FROM app_mfa_challenge WHERE token_hash=@token AND purpose='verify'
            """, ("token", tokenHash), ("max", MaxChallengeAttempts)))
            if (await current.ExecuteScalarAsync(ct) is not true)
            {
                await Burn(db, tx, tokenHash, ct);
                await tx.CommitAsync(ct);
                throw new DomainError(401, "mfa_challenge_invalid");
            }
        // Bound work to the fixed ten-code profile. Examine every hash, not an early successful prefix.
        if (stored.Count <= MfaRecoveryCodeCodec.CodeCount)
            foreach (string hash in stored)
                if (MfaRecoveryCodeCodec.Matches(code, hash, state.Systemhaus, state.User)) match = hash;
        if (match is null)
        {
            await using (var challenge = Command(db, tx, """
                UPDATE app_mfa_challenge SET attempts=attempts+1,
                  consumed_at=CASE WHEN attempts+1>=@max THEN clock_timestamp() ELSE consumed_at END
                WHERE token_hash=@token
                """, ("token", tokenHash), ("max", MaxChallengeAttempts)))
                await challenge.ExecuteNonQueryAsync(ct);
            await using (var factor = Command(db, tx, """
                UPDATE app_mfa_factor SET failed_attempts=failed_attempts+1,
                  locked_until=CASE WHEN failed_attempts+1>=@max THEN clock_timestamp()+interval '15 minutes' ELSE locked_until END
                WHERE systemhaus_id=@house AND user_id=@user
                """, ("house", state.Systemhaus), ("user", state.User), ("max", MaxFactorFailures)))
                await factor.ExecuteNonQueryAsync(ct);
            await tx.CommitAsync(ct);
            throw new DomainError(401, "mfa_code_invalid");
        }

        // A successful recovery retires the whole old set. No old code can authenticate again.
        int retiredCodes, revokedSessions, revokedChallenges;
        await using (var consume = Command(db, tx, """
            UPDATE app_mfa_recovery_code SET consumed_at=clock_timestamp()
            WHERE systemhaus_id=@house AND user_id=@user AND consumed_at IS NULL
            """, ("house", state.Systemhaus), ("user", state.User)))
            retiredCodes = await consume.ExecuteNonQueryAsync(ct);
        await using (var factor = Command(db, tx, """
            UPDATE app_mfa_factor SET state='disabled',failed_attempts=0,locked_until=NULL,last_time_step=-1
            WHERE systemhaus_id=@house AND user_id=@user
            """, ("house", state.Systemhaus), ("user", state.User)))
            await factor.ExecuteNonQueryAsync(ct);
        long revision;
        await using (var policy = Command(db, tx, """
            UPDATE app_mfa_user SET mfa_required=true,enrollment_pending=true,revision=revision+1,
              changed_by=@user,changed_at=clock_timestamp()
            WHERE systemhaus_id=@house AND user_id=@user RETURNING revision
            """, ("house", state.Systemhaus), ("user", state.User)))
            revision = (long)(await policy.ExecuteScalarAsync(ct) ?? throw new InvalidOperationException("Recovery policy missing."));
        await using (var sessions = Command(db, tx, "DELETE FROM app_session WHERE user_id=@user", ("user", state.User)))
            revokedSessions = await sessions.ExecuteNonQueryAsync(ct);
        await using (var challenges = Command(db, tx, """
            UPDATE app_mfa_challenge SET consumed_at=clock_timestamp()
            WHERE systemhaus_id=@house AND user_id=@user AND consumed_at IS NULL
            """, ("house", state.Systemhaus), ("user", state.User)))
            revokedChallenges = await challenges.ExecuteNonQueryAsync(ct);

        string nextToken = Secrets.Token(), nextCsrf = Secrets.Token();
        // One measured timestamp supplies both columns, including after a long lock wait.
        await using (var next = Command(db, tx, """
            WITH stamp AS (SELECT clock_timestamp() AS value)
            INSERT INTO app_mfa_challenge(token_hash,systemhaus_id,user_id,purpose,csrf_hash,policy_revision,created_at,expires_at)
            SELECT @token,@house,@user,'enroll',@csrf,@revision,value,value+interval '5 minutes' FROM stamp
            """, ("token", Secrets.Digest(nextToken)), ("house", state.Systemhaus), ("user", state.User),
            ("csrf", Secrets.Digest(nextCsrf)), ("revision", revision)))
            await next.ExecuteNonQueryAsync(ct);
        await using (var audit = Command(db, tx, """
            INSERT INTO audit_event(id,systemhaus_id,actor_id,request_id,action,resource_id,before_json,after_json)
            VALUES(@id,@house,@user,@request,'auth.mfa.recovery_code_redeemed',@user,NULL,CAST(@after AS jsonb))
            """, ("id", Guid.NewGuid()), ("house", state.Systemhaus), ("user", state.User), ("request", Guid.NewGuid()),
            ("after", JsonSerializer.Serialize(new { enrollmentPending = true, retiredCodes, revokedSessions, revokedChallenges }))))
            await audit.ExecuteNonQueryAsync(ct);
        await tx.CommitAsync(ct);
        return new(nextToken, nextCsrf);
    }
}
