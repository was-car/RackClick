using Npgsql;
using RackClick.Domain;

namespace RackClick.Server;

public sealed partial class PostgresStore
{
    // Fixed SQL fragment, scoped to app_user alias u. External values remain parameters.
    internal const string MfaGraceDueSql = """
        EXISTS(SELECT 1 FROM app_mfa_policy gp
            WHERE gp.systemhaus_id=u.systemhaus_id AND gp.enabled
              AND clock_timestamp() >= GREATEST(COALESCE(u.created_at,gp.activated_at),gp.activated_at)
                  +make_interval(days=>gp.grace_days))
        AND NOT (SELECT count(DISTINCT g.capability)=2
            FROM user_group_member gm JOIN permission_grant g
              ON g.systemhaus_id=gm.systemhaus_id AND g.user_group_id=gm.group_id
            WHERE gm.systemhaus_id=u.systemhaus_id AND gm.user_id=u.id
              AND g.customer_id IS NULL AND g.customer_group_id IS NULL
              AND g.capability IN ('security.manage','systemhaus.manage'))
        """;

    internal const string MfaSessionAllowedSql = "(s.mfa_verified_at IS NOT NULL OR NOT (" + MfaGraceDueSql + "))";

    // Called only after explicit real Windows-provider composition succeeds, before the listener.
    // Persist once: restart, migration and a later user's first login never move the rollout date.
    public async Task EnsureMfaGracePolicy(CancellationToken ct)
    {
        await using var db = await source.OpenConnectionAsync(ct);
        await using var command = Command(db, null, """
            INSERT INTO app_mfa_policy(systemhaus_id,enabled,grace_days,activated_at,revision)
            SELECT id,true,45,clock_timestamp(),1 FROM systemhaus
            ON CONFLICT(systemhaus_id) DO NOTHING
            """);
        await command.ExecuteNonQueryAsync(ct);
    }

    private static async Task EnforceMfaGrace(NpgsqlConnection db, NpgsqlTransaction tx,
        Guid houseId, Guid userId, CancellationToken ct)
    {
        await using var due = Command(db, tx, $"""
            SELECT ({MfaGraceDueSql}) FROM app_user u WHERE u.systemhaus_id=@house AND u.id=@user
            """, ("house", houseId), ("user", userId));
        if (await due.ExecuteScalarAsync(ct) is not true) return;

        // Login already holds the account row. The enrollment/verify flows use that same lock first.
        // No Systemhaus FOR UPDATE is introduced after this lock.
        await using var enforce = Command(db, tx, """
            INSERT INTO app_mfa_user(systemhaus_id,user_id,mfa_required,enrollment_pending,revision,changed_by)
            VALUES(@house,@user,true,
                NOT EXISTS(SELECT 1 FROM app_mfa_factor f WHERE f.systemhaus_id=@house AND f.user_id=@user AND f.state='active'),1,@user)
            ON CONFLICT(systemhaus_id,user_id) DO UPDATE SET
                mfa_required=true,
                enrollment_pending=app_mfa_user.enrollment_pending OR EXCLUDED.enrollment_pending,
                revision=app_mfa_user.revision+1,changed_by=@user,changed_at=clock_timestamp()
            WHERE NOT app_mfa_user.mfa_required OR (NOT app_mfa_user.enrollment_pending AND EXCLUDED.enrollment_pending)
            """, ("house", houseId), ("user", userId));
        if (await enforce.ExecuteNonQueryAsync(ct) == 0) return;
        await using var revoke = Command(db, tx, """
            DELETE FROM app_session WHERE user_id=@user;
            UPDATE app_mfa_challenge SET consumed_at=clock_timestamp()
            WHERE systemhaus_id=@house AND user_id=@user AND consumed_at IS NULL;
            INSERT INTO audit_event(id,systemhaus_id,actor_id,request_id,action,resource_id,before_json,after_json)
            VALUES(@audit,@house,@user,@request,'auth.mfa.grace_expired',@user,NULL,'{"required":true,"graceDays":45}'::jsonb)
            """, ("house", houseId), ("user", userId), ("audit", Guid.NewGuid()), ("request", Guid.NewGuid()));
        await revoke.ExecuteNonQueryAsync(ct);
    }
}
