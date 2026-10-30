using System.Text.Json;
using System.Security.Cryptography;
using Npgsql;
using RackClick.Domain;

namespace RackClick.Server;

// Local DB-owner operation, deliberately not an HTTP authority or a runtime-account operation.
// It applies to the accounts present in this transaction; future account provisioning is a separate policy concern.
public static class MfaPolicyAdministration
{
    private const string Action = "auth.mfa.policy.require_all";
    private static readonly JsonSerializerOptions Json = new(JsonSerializerDefaults.Web);

    public static async Task<MfaPolicyActivationResult> RequireAll(string ownerConnection, Guid databaseInstanceId,
        Guid actorId, IMfaKeyProvider keys, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(keys);
        if (databaseInstanceId == Guid.Empty || actorId == Guid.Empty)
            throw new DomainError(422, "mfa_policy_identity_invalid");
        string database = $"rc_db_{databaseInstanceId:N}", owner = $"rc_owner_{databaseInstanceId:N}";
        var settings = new NpgsqlConnectionStringBuilder(ownerConnection) { IncludeErrorDetail = false };
        await using var source = NpgsqlDataSource.Create(settings.ConnectionString);
        await using var db = await source.OpenConnectionAsync(ct);
        await using var tx = await db.BeginTransactionAsync(ct);
        await Execute(db, tx, "SET LOCAL search_path = pg_catalog, public", ct);
        await Execute(db, tx, "SELECT pg_catalog.pg_advisory_xact_lock(81726201)", ct);

        await using (var identity = Command(db, tx, """
            SELECT current_database(),current_user,session_user,pg_catalog.pg_get_userbyid(d.datdba),
                pg_catalog.shobj_description(d.oid,'pg_database')
            FROM pg_catalog.pg_database d WHERE d.datname=current_database()
            """))
        await using (var row = await identity.ExecuteReaderAsync(ct))
        {
            if (!await row.ReadAsync(ct) || row.GetString(0) != database)
                throw new DomainError(409, "mfa_policy_database_mismatch");
            if (row.GetString(1) != owner || row.GetString(2) != owner || row.GetString(3) != owner)
                throw new DomainError(403, "mfa_policy_owner_required");
            // Normal instances have no database comment. Recovery consumes its pending marker on commit.
            // There is no invented positive installation marker; the binding is database + owner + UUID.
            if (!row.IsDBNull(4)) throw new DomainError(409, "mfa_policy_database_not_ready");
        }

        await VerifySchema(db, tx, ct);
        Guid houseId;
        long houseRevision;
        await using (var house = Command(db, tx, "SELECT id,revision FROM public.systemhaus ORDER BY id FOR UPDATE"))
        await using (var rows = await house.ExecuteReaderAsync(ct))
        {
            if (!await rows.ReadAsync(ct)) throw new DomainError(409, "mfa_policy_systemhaus_required");
            houseId = rows.GetGuid(0); houseRevision = rows.GetInt64(1);
            if (houseId == Guid.Empty || houseRevision < 1 || await rows.ReadAsync(ct))
                throw new DomainError(409, "mfa_policy_systemhaus_required");
        }

        // Administration takes the Systemhaus before accounts. An EXCLUSIVE table lock also conflicts with
        // SELECT FOR UPDATE, so an existing login/MFA operation finishes before this lock is granted; it
        // cannot retain an account row and then wait on our table lock. New accounts cannot slip past the batch.
        // Normal reads remain possible. All table locks are transaction scoped and no prompt occurs here.
        await Execute(db, tx, "LOCK TABLE public.app_user IN EXCLUSIVE MODE", ct);
        await using (var actor = Command(db, tx, """
            SELECT EXISTS(SELECT 1 FROM public.app_user u
                JOIN public.user_group_member m ON m.systemhaus_id=u.systemhaus_id AND m.user_id=u.id
                JOIN public.permission_grant g ON g.systemhaus_id=m.systemhaus_id AND g.user_group_id=m.group_id
                WHERE u.id=@actor AND u.systemhaus_id=@house AND u.active
                  AND g.capability='security.manage' AND g.customer_id IS NULL AND g.customer_group_id IS NULL)
            """, ("actor", actorId), ("house", houseId)))
            if (await actor.ExecuteScalarAsync(ct) is not true)
                throw new DomainError(403, "mfa_policy_actor_required");

        await ValidateFactorKeys(db, tx, houseId, keys, ct);

        var changes = new List<(Guid Id, bool Pending)>();
        await using (var accounts = Command(db, tx, """
            SELECT u.id,m.mfa_required,m.enrollment_pending,
                EXISTS(SELECT 1 FROM public.app_mfa_factor f
                       WHERE f.systemhaus_id=u.systemhaus_id AND f.user_id=u.id AND f.state='active')
            FROM public.app_user u LEFT JOIN public.app_mfa_user m
                ON m.systemhaus_id=u.systemhaus_id AND m.user_id=u.id
            WHERE u.systemhaus_id=@house ORDER BY u.id
            """, ("house", houseId)))
        await using (var rows = await accounts.ExecuteReaderAsync(ct))
            while (await rows.ReadAsync(ct))
            {
                bool absent = rows.IsDBNull(1);
                bool required = !absent && rows.GetBoolean(1);
                bool pending = !absent && rows.GetBoolean(2);
                bool desiredPending = pending || !rows.GetBoolean(3);
                if (absent || !required || pending != desiredPending)
                    changes.Add((rows.GetGuid(0), desiredPending));
            }

        if (changes.Count == 0)
        {
            await tx.CommitAsync(ct);
            return new(databaseInstanceId, houseId, 0, 0, 0, null, true, houseRevision);
        }
        foreach (var change in changes)
        {
            await using var policy = Command(db, tx, """
                INSERT INTO public.app_mfa_user(systemhaus_id,user_id,mfa_required,enrollment_pending,revision,changed_by)
                VALUES(@house,@user,true,@pending,1,@actor)
                ON CONFLICT(systemhaus_id,user_id) DO UPDATE SET
                    mfa_required=true,enrollment_pending=@pending,revision=app_mfa_user.revision+1,
                    changed_by=@actor,changed_at=now()
                """, ("house", houseId), ("user", change.Id), ("pending", change.Pending), ("actor", actorId));
            await policy.ExecuteNonQueryAsync(ct);
        }
        var changedIds = changes.Select(change => change.Id).ToArray();
        int sessions, challenges;
        await using (var revoke = Command(db, tx, "DELETE FROM public.app_session WHERE user_id=ANY(@users)", ("users", changedIds)))
            sessions = await revoke.ExecuteNonQueryAsync(ct);
        await using (var revoke = Command(db, tx, """
            UPDATE public.app_mfa_challenge SET consumed_at=now()
            WHERE systemhaus_id=@house AND user_id=ANY(@users) AND consumed_at IS NULL
            """, ("house", houseId), ("users", changedIds)))
            challenges = await revoke.ExecuteNonQueryAsync(ct);

        long nextRevision = checked(houseRevision + 1);
        await using (var revision = Command(db, tx, "UPDATE public.systemhaus SET revision=@next WHERE id=@house",
            ("next", nextRevision), ("house", houseId)))
            await revision.ExecuteNonQueryAsync(ct);
        var auditId = Guid.NewGuid();
        string after = JsonSerializer.Serialize(new
        {
            origin = "localMfaPolicy", databaseInstanceId, changedUserIds = changedIds,
            changedUsers = changes.Count, revokedSessions = sessions, revokedChallenges = challenges
        }, Json);
        await using (var audit = Command(db, tx, """
            INSERT INTO public.audit_event(id,systemhaus_id,actor_id,request_id,action,resource_id,before_json,after_json)
            VALUES(@id,@house,@actor,@request,@action,@house,NULL,CAST(@after AS jsonb))
            """, ("id", auditId), ("house", houseId), ("actor", actorId), ("request", Guid.NewGuid()),
            ("action", Action), ("after", after)))
            await audit.ExecuteNonQueryAsync(ct);
        await tx.CommitAsync(ct);
        return new(databaseInstanceId, houseId, changes.Count, sessions, challenges, auditId, false, nextRevision);
    }

    private static async Task ValidateFactorKeys(NpgsqlConnection db, NpgsqlTransaction tx, Guid houseId,
        IMfaKeyProvider keys, CancellationToken ct)
    {
        try
        {
            byte[]? activeKey = null;
            try
            {
                var active = keys.GetActiveKey();
                activeKey = active.Key;
                if (active.Version < 1 || activeKey.Length != MfaSecretCipher.KeyBytes)
                    throw new CryptographicException();
            }
            finally { if (activeKey is not null) CryptographicOperations.ZeroMemory(activeKey); }

            await using var factors = Command(db, tx, """
                SELECT user_id,key_version,secret_ciphertext FROM public.app_mfa_factor
                WHERE systemhaus_id=@house AND state IN ('active','pending') ORDER BY user_id
                """, ("house", houseId));
            await using var rows = await factors.ExecuteReaderAsync(ct);
            while (await rows.ReadAsync(ct))
            {
                byte[]? key = null, secret = null;
                try
                {
                    int version = rows.GetInt32(1);
                    key = keys.GetKey(version);
                    secret = MfaSecretCipher.Open(key, version, (byte[])rows[2], houseId, rows.GetGuid(0));
                    if (secret.Length != MfaTotp.SecretBytes) throw new CryptographicException();
                }
                finally
                {
                    if (secret is not null) CryptographicOperations.ZeroMemory(secret);
                    if (key is not null) CryptographicOperations.ZeroMemory(key);
                }
            }
        }
        catch (Exception error) when (error is CryptographicException or MfaKeyRingException or IOException
                                     or UnauthorizedAccessException or ArgumentException or KeyNotFoundException)
        {
            // Never expose a file path, provider message, key, TOTP seed, ciphertext or user identity on failure.
            throw new DomainError(409, "mfa_policy_factor_key_mismatch");
        }
    }

    private static async Task VerifySchema(NpgsqlConnection db, NpgsqlTransaction tx, CancellationToken ct)
    {
        await using (var exists = Command(db, tx, "SELECT pg_catalog.to_regclass('public.schema_migration') IS NOT NULL"))
            if (await exists.ExecuteScalarAsync(ct) is not true) throw new DomainError(409, "mfa_policy_schema_required");
        await Execute(db, tx, "LOCK TABLE public.schema_migration IN SHARE MODE", ct);
        await using (var history = Command(db, tx, "SELECT version FROM public.schema_migration ORDER BY version"))
        await using (var rows = await history.ExecuteReaderAsync(ct))
        {
            int version = 0;
            while (await rows.ReadAsync(ct))
                if (rows.GetInt32(0) != ++version || version > SchemaMigrations.LatestVersion)
                    throw new DomainError(409, "mfa_policy_schema_required");
            if (version != SchemaMigrations.LatestVersion)
                throw new DomainError(409, "mfa_policy_schema_required");
        }
        // The complete current history was required above: Apply verifies pinned digests, never fills a gap here.
        await SchemaMigrations.Apply(db, tx, ct);
    }

    private static async Task Execute(NpgsqlConnection db, NpgsqlTransaction tx, string sql, CancellationToken ct)
    {
        await using var command = Command(db, tx, sql);
        await command.ExecuteNonQueryAsync(ct);
    }

    private static NpgsqlCommand Command(NpgsqlConnection db, NpgsqlTransaction tx, string sql,
        params (string Name, object Value)[] parameters)
    {
        var command = new NpgsqlCommand(sql, db, tx);
        foreach (var (name, value) in parameters) command.Parameters.AddWithValue(name, value);
        return command;
    }
}

public sealed record MfaPolicyActivationResult(Guid DatabaseInstanceId, Guid SystemhausId,
    int ChangedUsers, int RevokedSessions, int RevokedChallenges, Guid? AuditId, bool Noop, long SystemhausRevision);
