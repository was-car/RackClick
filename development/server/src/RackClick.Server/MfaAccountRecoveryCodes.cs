using System.Text.Json;
using Npgsql;
using RackClick.Domain;

namespace RackClick.Server;

/// <summary>Own-account recovery-code count and generation authority; never contains a code.</summary>
public sealed record MfaRecoveryCodesStatus(Guid UserId, int Remaining, long Revision, bool CanGenerate, bool SessionMfaVerified);

/// <summary>Codes are returned only by the first successful generation response, never by a receipt or replay.</summary>
public sealed record MfaRecoveryCodesGeneration(Guid UserId, Guid RequestId, int Remaining, long SystemhausRevision,
    bool CodesAvailable, string[]? Codes)
{
    public override string ToString() => nameof(MfaRecoveryCodesGeneration);
}

public sealed partial class PostgresStore
{
    public async Task<MfaRecoveryCodesStatus> ReadOwnRecoveryCodeStatus(Actor actor, CancellationToken ct)
    {
        await using var db = await source.OpenConnectionAsync(ct);
        await using var tx = await db.BeginTransactionAsync(System.Data.IsolationLevel.RepeatableRead, ct);
        await RequireCurrentSession(db, tx, actor, ct);
        await using var house = Command(db, tx, "SELECT revision FROM systemhaus WHERE id=@house", ("house", actor.HouseId));
        long revision = await house.ExecuteScalarAsync(ct) as long? ?? throw new DomainError(404, "not_found");
        bool verified = await MfaSessionVerified(db, tx, actor, ct);
        bool active = await RecoveryFactorActive(db, tx, actor, false, ct);
        int remaining = await RecoveryCodeCount(db, tx, actor, ct);
        await RequireCurrentSession(db, tx, actor, ct);
        await tx.CommitAsync(ct);
        return new(actor.Id, remaining, revision, MfaAvailable && verified && active, verified);
    }

    public async Task<MfaRecoveryCodesGeneration?> ReadOwnRecoveryCodesReceipt(Actor actor, Guid requestId, CancellationToken ct)
    {
        if (requestId == Guid.Empty) throw new DomainError(422, "request_id_invalid");
        await using var db = await source.OpenConnectionAsync(ct);
        await using var tx = await db.BeginTransactionAsync(ct);
        await RequireCurrentSession(db, tx, actor, ct);
        await using var receipt = Command(db, tx, """
            SELECT o.result_json::text FROM operation o JOIN audit_event a
              ON a.systemhaus_id=o.systemhaus_id AND a.actor_id=o.actor_id AND a.request_id=o.request_id
            WHERE o.systemhaus_id=@house AND o.actor_id=@actor AND o.request_id=@request
              AND a.resource_id=@actor AND a.action='auth.mfa.recovery_codes.generated'
            """, ("house", actor.HouseId), ("actor", actor.Id), ("request", requestId));
        string? value = await receipt.ExecuteScalarAsync(ct) as string;
        await RequireCurrentSession(db, tx, actor, ct);
        await tx.CommitAsync(ct);
        return value is null ? null : RecoveryReceipt(value);
    }

    public async Task<MfaRecoveryCodesGeneration> GenerateOwnRecoveryCodes(Actor actor, string? password,
        long expected, Guid requestId, bool available, CancellationToken ct)
    {
        if (requestId == Guid.Empty) throw new DomainError(422, "request_id_invalid");
        if (expected < 1) throw new DomainError(422, "revision_invalid");
        if (!available) throw new DomainError(503, "mfa_unavailable");
        if (password is null || password.Length is < 16 or > 1024) throw new DomainError(401, "mfa_reauthentication_required");
        await using var db = await source.OpenConnectionAsync(ct);
        await using var tx = await db.BeginTransactionAsync(ct);
        await LockOperation(db, tx, actor, requestId, ct);
        await using var house = Command(db, tx, "SELECT revision FROM systemhaus WHERE id=@house FOR UPDATE", ("house", actor.HouseId));
        long revision = await house.ExecuteScalarAsync(ct) as long? ?? throw new DomainError(404, "not_found");
        await RequireMfaManagementActor(db, tx, actor, false, true, ct);
        string username, hash;
        bool active;
        await using (var account = Command(db, tx, """
            SELECT username,password_hash,active AND (locked_until IS NULL OR locked_until<clock_timestamp())
            FROM app_user WHERE systemhaus_id=@house AND id=@actor FOR UPDATE
            """, ("house", actor.HouseId), ("actor", actor.Id)))
        await using (var row = await account.ExecuteReaderAsync(ct))
        {
            if (!await row.ReadAsync(ct)) throw new DomainError(401, "session_revoked");
            username = row.GetString(0); hash = row.GetString(1); active = row.GetBoolean(2);
        }
        await RequireMfaManagementActor(db, tx, actor, false, true, ct);
        if (!active) throw new DomainError(409, "mfa_user_inactive");
        if (!Secrets.PasswordValid(username, hash, password)) throw new DomainError(401, "mfa_reauthentication_required");
        string digest = Secrets.Digest(JsonSerializer.Serialize(new { action = "auth.mfa.recovery_codes.generated", userId = actor.Id, expected }, Json));
        await using (var prior = Command(db, tx, """
            SELECT request_hash,result_json::text FROM operation
            WHERE systemhaus_id=@house AND actor_id=@actor AND request_id=@request
            """, ("house", actor.HouseId), ("actor", actor.Id), ("request", requestId)))
        await using (var row = await prior.ExecuteReaderAsync(ct))
            if (await row.ReadAsync(ct))
            {
                if (row.GetString(0) != digest) throw new DomainError(409, "request_id_reused");
                return RecoveryReceipt(row.GetString(1));
            }
        Revisions.Require(expected, revision);
        if (!await RecoveryFactorActive(db, tx, actor, true, ct)) throw new DomainError(409, "mfa_active_factor_required");
        int invalidated = await RecoveryCodeCount(db, tx, actor, ct);
        await using (var delete = Command(db, tx, "DELETE FROM app_mfa_recovery_code WHERE systemhaus_id=@house AND user_id=@actor",
            ("house", actor.HouseId), ("actor", actor.Id)))
            await delete.ExecuteNonQueryAsync(ct);
        string[] codes = Enumerable.Range(0, MfaRecoveryCodeCodec.CodeCount).Select(_ => MfaRecoveryCodeCodec.NewCode()).ToArray();
        foreach (string code in codes)
        {
            await using var insert = Command(db, tx, """
                INSERT INTO app_mfa_recovery_code(systemhaus_id,user_id,code_hash)
                VALUES(@house,@actor,@hash)
                """, ("house", actor.HouseId), ("actor", actor.Id), ("hash", MfaRecoveryCodeCodec.Hash(code, actor.HouseId, actor.Id)));
            await insert.ExecuteNonQueryAsync(ct);
        }
        // Any pre-existing challenge must not straddle a recovery-code rotation.
        await MfaStore.RevokePendingChallenges(db, tx, actor.HouseId, actor.Id, ct);
        long next = checked(revision + 1);
        await using (var update = Command(db, tx, "UPDATE systemhaus SET revision=@next WHERE id=@house", ("next", next), ("house", actor.HouseId)))
            await update.ExecuteNonQueryAsync(ct);
        var safe = new MfaRecoveryCodesGeneration(actor.Id, requestId, codes.Length, next, false, null);
        string receiptJson = JsonSerializer.Serialize(safe, Json);
        await using (var audit = Command(db, tx, """
            INSERT INTO audit_event(id,systemhaus_id,actor_id,request_id,action,resource_id,before_json,after_json)
            VALUES(@id,@house,@actor,@request,'auth.mfa.recovery_codes.generated',@actor,NULL,CAST(@after AS jsonb))
            """, ("id", Guid.NewGuid()), ("house", actor.HouseId), ("actor", actor.Id), ("request", requestId),
            ("after", JsonSerializer.Serialize(new { remaining = codes.Length, invalidated }, Json))))
            await audit.ExecuteNonQueryAsync(ct);
        await using (var receipt = Command(db, tx, """
            INSERT INTO operation(systemhaus_id,actor_id,request_id,request_hash,result_json)
            VALUES(@house,@actor,@request,@hash,CAST(@result AS jsonb))
            """, ("house", actor.HouseId), ("actor", actor.Id), ("request", requestId), ("hash", digest), ("result", receiptJson)))
            await receipt.ExecuteNonQueryAsync(ct);
        await RequireMfaManagementActor(db, tx, actor, false, true, ct);
        await tx.CommitAsync(ct);
        return safe with { CodesAvailable = true, Codes = codes };
    }

    private static MfaRecoveryCodesGeneration RecoveryReceipt(string json)
    {
        var value = JsonSerializer.Deserialize<MfaRecoveryCodesGeneration>(json, Json) ?? throw new InvalidOperationException("Recovery receipt unavailable.");
        return value with { CodesAvailable = false, Codes = null };
    }

    private static async Task<int> RecoveryCodeCount(NpgsqlConnection db, NpgsqlTransaction tx, Actor actor, CancellationToken ct)
    {
        await using var count = Command(db, tx, "SELECT count(*) FROM app_mfa_recovery_code WHERE systemhaus_id=@house AND user_id=@actor AND consumed_at IS NULL",
            ("house", actor.HouseId), ("actor", actor.Id));
        return checked((int)(long)(await count.ExecuteScalarAsync(ct) ?? 0L));
    }

    private static async Task<bool> RecoveryFactorActive(NpgsqlConnection db, NpgsqlTransaction tx, Actor actor, bool locking, CancellationToken ct)
    {
        await using var factor = Command(db, tx, """
            SELECT f.state='active' AND f.confirmed_at IS NOT NULL
              AND (f.locked_until IS NULL OR f.locked_until<clock_timestamp())
              AND EXISTS(SELECT 1 FROM app_mfa_user m WHERE m.systemhaus_id=f.systemhaus_id AND m.user_id=f.user_id
                         AND m.mfa_required AND NOT m.enrollment_pending)
            FROM app_mfa_factor f WHERE f.systemhaus_id=@house AND f.user_id=@actor
            """ + (locking ? " FOR UPDATE OF f" : ""), ("house", actor.HouseId), ("actor", actor.Id));
        return await factor.ExecuteScalarAsync(ct) is true;
    }
}
