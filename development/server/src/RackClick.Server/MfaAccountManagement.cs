using System.Text.Json;
using Npgsql;
using RackClick.Domain;

namespace RackClick.Server;

/// <summary>Public MFA state for one account. Contains no seed, ciphertext, recovery code or authentication URI.</summary>
public sealed record MfaAccountStatus(Guid UserId, string UserName, bool Available, bool Required,
    bool EnrollmentPending, string FactorState, bool GlobalPolicyEnabled, int? GraceDays,
    DateTimeOffset? DeadlineUtc, int? DaysRemaining, bool DeadlineReached, bool GlobalAdministratorExempt,
    bool SessionMfaVerified, bool CanEnable, bool CanDisable, bool CanReset, long Revision, DateTimeOffset ServerNowUtc);

/// <summary>Public intent for an MFA account change. Password is used only for own-account reauthentication.</summary>
public sealed record MfaAccountChangeRequest(string? Action, string? Password);

public sealed partial class PostgresStore
{
    public Task<MfaAccountStatus> ReadOwnMfaStatus(Actor actor, bool available, CancellationToken ct) =>
        ReadMfaAccount(actor, actor.Id, false, available, ct);

    public Task<MfaAccountStatus> ReadUserMfaStatus(Actor actor, Guid userId, bool available, CancellationToken ct) =>
        ReadMfaAccount(actor, userId, true, available, ct);

    private async Task<MfaAccountStatus> ReadMfaAccount(Actor actor, Guid userId, bool admin, bool available, CancellationToken ct)
    {
        if (userId == Guid.Empty) throw new DomainError(422, "request_invalid");
        await using var db = await source.OpenConnectionAsync(ct);
        await using var tx = await db.BeginTransactionAsync(System.Data.IsolationLevel.RepeatableRead, ct);
        await RequireMfaManagementActor(db, tx, actor, admin, false, ct);
        await using var house = Command(db, tx, "SELECT revision FROM systemhaus WHERE id=@house", ("house", actor.HouseId));
        var revision = await house.ExecuteScalarAsync(ct) as long? ?? throw new DomainError(404, "not_found");
        var status = await MfaAccountState(db, tx, actor, userId, admin, available, revision, ct);
        await tx.CommitAsync(ct);
        return status;
    }

    public Task<string> ChangeOwnMfa(Actor actor, string? action, string? password,
        long expected, Guid requestId, bool available, CancellationToken ct) =>
        ChangeMfaAccount(actor, actor.Id, action, password, expected, requestId, false, available, ct);

    public Task<string> ChangeUserMfa(Actor actor, Guid userId, string? action,
        long expected, Guid requestId, bool available, CancellationToken ct) =>
        ChangeMfaAccount(actor, userId, action, null, expected, requestId, true, available, ct);

    public async Task<string> ReadMfaChangeStatus(Actor actor, Guid userId, Guid requestId, bool admin, CancellationToken ct)
    {
        if (userId == Guid.Empty || requestId == Guid.Empty) throw new DomainError(422, "request_invalid");
        if (!admin && userId != actor.Id) throw new DomainError(403, "forbidden");
        await using var db = await source.OpenConnectionAsync(ct);
        await using var tx = await db.BeginTransactionAsync(ct);
        // Receipts need current authority, but not a factor that this very action deliberately removed.
        await RequireMfaManagementActor(db, tx, actor, admin, admin, ct);
        await RequireMfaManagementActor(db, tx, actor, admin, admin, ct);
        await using var receipt = Command(db, tx, """
            SELECT o.result_json::text FROM operation o JOIN audit_event a
              ON a.systemhaus_id=o.systemhaus_id AND a.actor_id=o.actor_id AND a.request_id=o.request_id
            WHERE o.systemhaus_id=@house AND o.actor_id=@actor AND o.request_id=@request
              AND a.resource_id=@user AND a.action IN
                ('auth.mfa.user.enable','auth.mfa.user.disable','auth.mfa.user.reset')
            """, ("house", actor.HouseId), ("actor", actor.Id), ("request", requestId), ("user", userId));
        return UserCreationOutcome(requestId, await receipt.ExecuteScalarAsync(ct) as string);
    }

    private async Task<string> ChangeMfaAccount(Actor actor, Guid userId, string? action, string? password,
        long expected, Guid requestId, bool admin, bool available, CancellationToken ct)
    {
        if (userId == Guid.Empty || requestId == Guid.Empty) throw new DomainError(422, "request_invalid");
        if (action is not ("enable" or "disable" or "reset")) throw new DomainError(422, "mfa_action_invalid");
        if (expected < 1) throw new DomainError(422, "revision_invalid");
        if (!available) throw new DomainError(503, "mfa_unavailable");
        if (admin && userId == actor.Id) throw new DomainError(422, "mfa_use_self_service");
        if (!admin && (password is null || password.Length is < 16 or > 1024))
            throw new DomainError(401, "mfa_reauthentication_required");

        await using var db = await source.OpenConnectionAsync(ct);
        await using var tx = await db.BeginTransactionAsync(ct);
        await LockOperation(db, tx, actor, requestId, ct);
        await using var house = Command(db, tx, "SELECT revision FROM systemhaus WHERE id=@house FOR UPDATE", ("house", actor.HouseId));
        long revision = await house.ExecuteScalarAsync(ct) as long? ?? throw new DomainError(404, "not_found");
        await RequireMfaManagementActor(db, tx, actor, admin, admin, ct);

        string username, passwordHash;
        bool active;
        await using (var target = Command(db, tx,
            "SELECT username,password_hash,active FROM app_user WHERE systemhaus_id=@house AND id=@user FOR UPDATE",
            ("house", actor.HouseId), ("user", userId)))
        await using (var row = await target.ExecuteReaderAsync(ct))
        {
            if (!await row.ReadAsync(ct)) throw new DomainError(404, "not_found");
            username = row.GetString(0); passwordHash = row.GetString(1); active = row.GetBoolean(2);
        }
        await RequireMfaManagementActor(db, tx, actor, admin, admin, ct);
        if (!active) throw new DomainError(409, "mfa_user_inactive");
        if (!admin && !Secrets.PasswordValid(username, passwordHash, password!))
            throw new DomainError(401, "mfa_reauthentication_required");

        string auditAction = "auth.mfa.user." + action;
        string digest = Secrets.Digest(JsonSerializer.Serialize(new { action = auditAction, userId, expected, admin }, Json));
        await using (var prior = Command(db, tx,
            "SELECT request_hash,result_json::text FROM operation WHERE systemhaus_id=@house AND actor_id=@actor AND request_id=@request",
            ("house", actor.HouseId), ("actor", actor.Id), ("request", requestId)))
        await using (var row = await prior.ExecuteReaderAsync(ct))
            if (await row.ReadAsync(ct))
            {
                if (row.GetString(0) != digest) throw new DomainError(409, "request_id_reused");
                return row.GetString(1);
            }
        Revisions.Require(expected, revision);
        var before = await MfaAccountState(db, tx, actor, userId, admin, available, revision, ct);
        if (!admin && before.FactorState == "active" && !before.SessionMfaVerified)
            throw new DomainError(403, "mfa_verification_required");
        if (action == "disable" && before.EnrollmentPending)
            throw new DomainError(409, "mfa_enrollment_required");
        // The global administrator exception is own-account only. Nobody may extend a user's grace deadline.
        if (action == "disable" && before.DeadlineReached && !(userId == actor.Id && before.GlobalAdministratorExempt))
            throw new DomainError(409, "mfa_required_by_policy");

        bool required = action != "disable";
        bool pending = action == "reset" || (action == "enable" && (before.EnrollmentPending || before.FactorState != "active"));
        await using (var policy = Command(db, tx, """
            INSERT INTO app_mfa_user(systemhaus_id,user_id,mfa_required,enrollment_pending,revision,changed_by)
            VALUES(@house,@user,@required,@pending,1,@actor)
            ON CONFLICT(systemhaus_id,user_id) DO UPDATE SET mfa_required=@required,enrollment_pending=@pending,
                revision=app_mfa_user.revision+1,changed_by=@actor,changed_at=clock_timestamp()
            """, ("house", actor.HouseId), ("user", userId), ("required", required), ("pending", pending), ("actor", actor.Id)))
            await policy.ExecuteNonQueryAsync(ct);
        if (action is "disable" or "reset")
        {
            await using (var factor = Command(db, tx, """
                UPDATE app_mfa_factor SET state='disabled',last_time_step=-1,failed_attempts=0,locked_until=NULL
                WHERE systemhaus_id=@house AND user_id=@user
                """, ("house", actor.HouseId), ("user", userId)))
                await factor.ExecuteNonQueryAsync(ct);
            await using (var codes = Command(db, tx, "DELETE FROM app_mfa_recovery_code WHERE systemhaus_id=@house AND user_id=@user",
                ("house", actor.HouseId), ("user", userId)))
                await codes.ExecuteNonQueryAsync(ct);
        }
        int revokedSessions, revokedChallenges;
        await using (var sessions = Command(db, tx, "DELETE FROM app_session WHERE user_id=@user", ("user", userId)))
            revokedSessions = await sessions.ExecuteNonQueryAsync(ct);
        await using (var challenges = Command(db, tx, """
            UPDATE app_mfa_challenge SET consumed_at=clock_timestamp()
            WHERE systemhaus_id=@house AND user_id=@user AND consumed_at IS NULL
            """, ("house", actor.HouseId), ("user", userId)))
            revokedChallenges = await challenges.ExecuteNonQueryAsync(ct);
        long next = checked(revision + 1);
        await using (var update = Command(db, tx, "UPDATE systemhaus SET revision=@next WHERE id=@house",
            ("next", next), ("house", actor.HouseId)))
            await update.ExecuteNonQueryAsync(ct);

        var after = await MfaAccountState(db, tx, actor, userId, admin, available, next, ct);
        string result = JsonSerializer.Serialize(new { userId, action, requestId, systemhausRevision = next,
            signInRequired = userId == actor.Id, resource = after }, Json);
        // Passwords, seeds, ciphertext and URI are absent from public intent, receipt and audit.
        var auditBefore = new { before.Required, before.EnrollmentPending, before.FactorState };
        var auditAfter = new { after.Required, after.EnrollmentPending, after.FactorState, revokedSessions, revokedChallenges };
        await using (var audit = Command(db, tx, """
            INSERT INTO audit_event(id,systemhaus_id,actor_id,request_id,action,resource_id,before_json,after_json)
            VALUES(@id,@house,@actor,@request,@action,@user,CAST(@before AS jsonb),CAST(@after AS jsonb))
            """, ("id", Guid.NewGuid()), ("house", actor.HouseId), ("actor", actor.Id), ("request", requestId),
            ("action", auditAction), ("user", userId), ("before", JsonSerializer.Serialize(auditBefore, Json)),
            ("after", JsonSerializer.Serialize(auditAfter, Json))))
            await audit.ExecuteNonQueryAsync(ct);
        await using (var receipt = Command(db, tx, """
            INSERT INTO operation(systemhaus_id,actor_id,request_id,request_hash,result_json)
            VALUES(@house,@actor,@request,@hash,CAST(@result AS jsonb))
            RETURNING result_json::text
            """, ("house", actor.HouseId), ("actor", actor.Id), ("request", requestId), ("hash", digest), ("result", result)))
            result = await receipt.ExecuteScalarAsync(ct) as string ?? throw new InvalidOperationException("MFA receipt missing.");
        await tx.CommitAsync(ct);
        return result;
    }

    private static async Task RequireMfaManagementActor(NpgsqlConnection db, NpgsqlTransaction tx,
        Actor actor, bool admin, bool mfa, CancellationToken ct)
    {
        if (admin) await RequireSecurity(db, tx, actor, ct);
        else await RequireCurrentSession(db, tx, actor, ct);
        if (mfa && !await MfaSessionVerified(db, tx, actor, ct))
            throw new DomainError(403, "mfa_verification_required");
    }

    private static async Task<bool> MfaSessionVerified(NpgsqlConnection db, NpgsqlTransaction tx, Actor actor, CancellationToken ct)
    {
        await using var current = Command(db, tx, """
            SELECT EXISTS(SELECT 1 FROM app_session s JOIN app_user u ON u.id=s.user_id
                WHERE s.token_hash=@token AND s.user_id=@actor AND u.systemhaus_id=@house AND u.active
                  AND s.expires_at>clock_timestamp() AND s.mfa_verified_at IS NOT NULL)
            """, ("token", actor.SessionTokenHash ?? ""), ("actor", actor.Id), ("house", actor.HouseId));
        return await current.ExecuteScalarAsync(ct) is true;
    }

    private static async Task<MfaAccountStatus> MfaAccountState(NpgsqlConnection db, NpgsqlTransaction tx,
        Actor actor, Guid userId, bool admin, bool available, long revision, CancellationToken ct)
    {
        Guid target;
        string name, factor;
        bool active, required, pending, global, exempt;
        int? grace;
        DateTimeOffset? deadline;
        DateTimeOffset now;
        await using (var query = Command(db, tx, """
            SELECT u.id,u.username,u.active,COALESCE(m.mfa_required,false),COALESCE(m.enrollment_pending,false),
                COALESCE(f.state,'none'),COALESCE(p.enabled,false),p.grace_days,
                CASE WHEN p.enabled THEN GREATEST(COALESCE(u.created_at,p.activated_at),p.activated_at)
                    +make_interval(days=>p.grace_days) ELSE NULL END,
                clock_timestamp(),
                (SELECT count(DISTINCT g.capability)=2 FROM user_group_member ug JOIN permission_grant g
                    ON g.systemhaus_id=ug.systemhaus_id AND g.user_group_id=ug.group_id
                    WHERE ug.systemhaus_id=u.systemhaus_id AND ug.user_id=u.id
                      AND g.customer_id IS NULL AND g.customer_group_id IS NULL
                      AND g.capability IN ('security.manage','systemhaus.manage'))
            FROM app_user u LEFT JOIN app_mfa_user m ON m.systemhaus_id=u.systemhaus_id AND m.user_id=u.id
            LEFT JOIN app_mfa_factor f ON f.systemhaus_id=u.systemhaus_id AND f.user_id=u.id
            LEFT JOIN app_mfa_policy p ON p.systemhaus_id=u.systemhaus_id
            WHERE u.systemhaus_id=@house AND u.id=@user
            """, ("house", actor.HouseId), ("user", userId)))
        await using (var row = await query.ExecuteReaderAsync(ct))
        {
            if (!await row.ReadAsync(ct)) throw new DomainError(404, "not_found");
            target = row.GetGuid(0); name = row.GetString(1); active = row.GetBoolean(2);
            required = row.GetBoolean(3); pending = row.GetBoolean(4); factor = row.GetString(5); global = row.GetBoolean(6);
            grace = row.IsDBNull(7) ? null : row.GetInt32(7);
            deadline = row.IsDBNull(8) ? null : row.GetFieldValue<DateTimeOffset>(8);
            now = row.GetFieldValue<DateTimeOffset>(9); exempt = row.GetBoolean(10);
        }
        bool verified = await MfaSessionVerified(db, tx, actor, ct);
        bool reached = deadline.HasValue && deadline.Value <= now;
        bool effectiveRequired = required || (reached && !exempt);
        bool authorized = admin ? verified && target != actor.Id : factor != "active" || verified;
        bool usable = available && active && authorized;
        int? days = deadline.HasValue ? (int)Math.Max(0, Math.Ceiling((deadline.Value - now).TotalDays)) : null;
        bool configured = required || pending || factor is "active" or "pending";
        return new(target, name, available, effectiveRequired, pending, factor, global, grace, deadline,
            days, reached, exempt, verified, usable && !required, usable && configured && !pending && (!reached || (!admin && exempt)),
            usable && (factor is "active" or "pending"), revision, now);
    }
}
