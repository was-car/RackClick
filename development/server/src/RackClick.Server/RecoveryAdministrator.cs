using System.Text.Json;
using Npgsql;
using RackClick.Domain;

namespace RackClick.Server;

// Local, offline DB-owner command. This is deliberately not an HTTP authority.
public static class RecoveryAdministrator
{
    private const string Action = "deployment.recover";
    private static readonly int RequiredSchemaVersion = 14;
    private static readonly JsonSerializerOptions Json = new(JsonSerializerDefaults.Web);

    public static async Task<int> Run(IConfiguration configuration, TextReader passwordInput,
        TextWriter output, CancellationToken ct)
    {
        try
        {
            string username = UserNames.Normalize(configuration["Recovery:User"]);
            string database = configuration["Recovery:ExpectedDatabase"] ?? "";
            Guid instanceId = ParseDatabase(database);
            string backupSha256 = configuration["Recovery:BackupSha256"] ?? "";
            if (backupSha256.Length != 64 || backupSha256.Any(c => !char.IsAsciiHexDigit(c)))
                throw new DomainError(422, "recovery_backup_sha256_invalid");
            backupSha256 = backupSha256.ToLowerInvariant();
            string connection = configuration.GetConnectionString("RackClick")
                ?? throw new DomainError(422, "recovery_connection_required");
            string password = await ReadPassword(passwordInput, ct);
            var result = await Recover(connection, database, instanceId, backupSha256, username, password, ct);
            await output.WriteLineAsync(JsonSerializer.Serialize(result, Json));
            return 0;
        }
        catch (DomainError error)
        {
            await output.WriteLineAsync(JsonSerializer.Serialize(new { status = "rejected", error = error.Code }, Json));
        }
        catch (Exception)
        {
            // Connection strings, SQL, passwords, tokens and input are never logged.
            // An exception during COMMIT can be indeterminate: retain the new DB.
            await output.WriteLineAsync(JsonSerializer.Serialize(new { status = "failed", error = "recovery_failed" }, Json));
        }
        return 1;
    }

    private static Guid ParseDatabase(string database)
    {
        if (database.Length != 38 || !database.StartsWith("rc_db_", StringComparison.Ordinal)
            || database.AsSpan(6).ContainsAnyExcept("0123456789abcdef")
            || !Guid.TryParseExact(database.AsSpan(6), "N", out Guid instanceId) || instanceId == Guid.Empty)
            throw new DomainError(422, "recovery_database_invalid");
        return instanceId;
    }

    private static async Task<string> ReadPassword(TextReader input, CancellationToken ct)
    {
        // Bounded stdin, closed by the caller: one password and at most one final LF/CRLF.
        var buffer = new char[1027];
        try
        {
            int count = 0;
            while (count < buffer.Length)
            {
                int read = await input.ReadAsync(buffer.AsMemory(count), ct);
                if (read == 0) break;
                count += read;
            }
            if (count == buffer.Length) throw new DomainError(422, "password_length");
            int length = count;
            if (length > 0 && buffer[length - 1] == '\n')
            {
                length--;
                if (length > 0 && buffer[length - 1] == '\r') length--;
            }
            if (length is < 16 or > 1024) throw new DomainError(422, "password_length");
            if (buffer.AsSpan(0, length).ContainsAny('\r', '\n'))
                throw new DomainError(422, "recovery_password_input_invalid");
            return new string(buffer, 0, length);
        }
        finally { Array.Clear(buffer); }
    }

    private static async Task<RecoveryAdministratorResult> Recover(string connection, string database,
        Guid instanceId, string backupSha256, string username, string password, CancellationToken ct)
    {
        var settings = new NpgsqlConnectionStringBuilder(connection) { IncludeErrorDetail = false };
        await using var source = NpgsqlDataSource.Create(settings.ConnectionString);
        await using var db = await source.OpenConnectionAsync(ct);
        await using var tx = await db.BeginTransactionAsync(ct);
        await using (var path = Command(db, tx, "SET LOCAL search_path = pg_catalog, public"))
            await path.ExecuteNonQueryAsync(ct);
        // The same advisory key serializes bootstrap/migrate/recovery commands.
        await using (var guard = Command(db, tx, "SELECT pg_catalog.pg_advisory_xact_lock(81726201)"))
            await guard.ExecuteNonQueryAsync(ct);

        string? marker;
        string expectedOwner = $"rc_owner_{instanceId:N}";
        await using (var identity = Command(db, tx, """
            SELECT current_database(),current_user,pg_catalog.pg_get_userbyid(d.datdba),
                pg_catalog.shobj_description(d.oid,'pg_database')
            FROM pg_catalog.pg_database d WHERE d.datname=current_database()
            """))
        await using (var row = await identity.ExecuteReaderAsync(ct))
        {
            if (!await row.ReadAsync(ct) || row.GetString(0) != database)
                throw new DomainError(409, "recovery_database_mismatch");
            if (row.GetString(1) != expectedOwner || row.GetString(2) != expectedOwner)
                throw new DomainError(403, "recovery_owner_required");
            marker = row.IsDBNull(3) ? null : row.GetString(3);
        }

        // Fail closed before Apply: complete 1..10 means it can only verify digests.
        // Never bootstrap or upgrade a restored archive as a side effect of recovery.
        if (SchemaMigrations.LatestVersion != RequiredSchemaVersion)
            throw new DomainError(409, "recovery_schema_required");
        await using (var exists = Command(db, tx, "SELECT pg_catalog.to_regclass('public.schema_migration') IS NOT NULL"))
            if (await exists.ExecuteScalarAsync(ct) is not true)
                throw new DomainError(409, "recovery_schema_required");
        await using (var historyLock = Command(db, tx, "LOCK TABLE public.schema_migration IN SHARE MODE"))
            await historyLock.ExecuteNonQueryAsync(ct);
        await using (var history = Command(db, tx, "SELECT version FROM public.schema_migration ORDER BY version"))
        await using (var rows = await history.ExecuteReaderAsync(ct))
        {
            int version = 0;
            while (await rows.ReadAsync(ct))
            {
                version++;
                if (rows.GetInt32(0) != version || version > RequiredSchemaVersion)
                    throw new DomainError(409, "recovery_schema_required");
            }
            if (version != RequiredSchemaVersion) throw new DomainError(409, "recovery_schema_required");
        }
        await SchemaMigrations.Apply(db, tx, ct);

        Guid houseId;
        long beforeRevision;
        await using (var house = Command(db, tx, "SELECT id,revision FROM public.systemhaus ORDER BY id FOR UPDATE"))
        await using (var rows = await house.ExecuteReaderAsync(ct))
        {
            if (!await rows.ReadAsync(ct)) throw new DomainError(409, "recovery_systemhaus_required");
            houseId = rows.GetGuid(0);
            beforeRevision = rows.GetInt64(1);
            if (houseId == Guid.Empty || beforeRevision < 1 || await rows.ReadAsync(ct))
                throw new DomainError(409, "recovery_systemhaus_required");
        }
        await using (var prior = Command(db, tx, """
            SELECT EXISTS(SELECT 1 FROM public.audit_event WHERE systemhaus_id=@house
                AND action='deployment.recover' AND after_json->>'instanceId'=@instance)
            """, ("house", houseId), ("instance", instanceId.ToString("D"))))
            if (await prior.ExecuteScalarAsync(ct) is true)
                throw new DomainError(409, "recovery_already_initialized");
        if (marker != $"RackClickRecoveryPending:{instanceId:D}:{backupSha256}")
            throw new DomainError(409, "recovery_pending_marker_required");
        await using (var exists = Command(db, tx, "SELECT EXISTS(SELECT 1 FROM public.app_user WHERE systemhaus_id=@house AND username=@name)",
            ("house", houseId), ("name", username)))
            if (await exists.ExecuteScalarAsync(ct) is true)
                throw new DomainError(409, "recovery_username_exists");
        long afterRevision = checked(beforeRevision + 1);

        Guid userId = Guid.NewGuid(), groupId = Guid.NewGuid(), eventId = Guid.NewGuid(), requestId = Guid.NewGuid();
        await using (var user = Command(db, tx, """
            INSERT INTO public.app_user(id,systemhaus_id,username,password_hash,active)
            VALUES(@id,@house,@name,@hash,true)
            """, ("id", userId), ("house", houseId), ("name", username), ("hash", Secrets.PasswordHash(username, password))))
            await user.ExecuteNonQueryAsync(ct);
        await using (var group = Command(db, tx, "INSERT INTO public.user_group(id,systemhaus_id,name) VALUES(@id,@house,'Recovered Systemhaus Administrators')",
            ("id", groupId), ("house", houseId)))
            await group.ExecuteNonQueryAsync(ct);
        await using (var membership = Command(db, tx, "INSERT INTO public.user_group_member(systemhaus_id,user_id,group_id) VALUES(@house,@user,@group)",
            ("house", houseId), ("user", userId), ("group", groupId)))
            await membership.ExecuteNonQueryAsync(ct);
        foreach (string capability in Capabilities.FoundationAdmin)
        {
            await using var grant = Command(db, tx, """
                INSERT INTO public.permission_grant(id,systemhaus_id,user_group_id,capability)
                VALUES(@id,@house,@group,@capability)
                """, ("id", Guid.NewGuid()), ("house", houseId), ("group", groupId), ("capability", capability));
            await grant.ExecuteNonQueryAsync(ct);
        }
        int revokedSessions;
        await using (var sessions = Command(db, tx, "DELETE FROM public.app_session"))
            revokedSessions = await sessions.ExecuteNonQueryAsync(ct);
        // Un desafío MFA pendiente (enroll o verify) no sobrevive a la recuperación: se consume en la misma transacción
        // que revoca las sesiones. Si la transacción falla, el commit no ocurre y ningún cambio queda aplicado.
        int revokedChallenges;
        await using (var challenges = Command(db, tx, "UPDATE public.app_mfa_challenge SET consumed_at=now() WHERE consumed_at IS NULL"))
            revokedChallenges = await challenges.ExecuteNonQueryAsync(ct);
        await using (var revision = Command(db, tx, "UPDATE public.systemhaus SET revision=@revision WHERE id=@house",
            ("revision", afterRevision), ("house", houseId)))
            if (await revision.ExecuteNonQueryAsync(ct) != 1) throw new InvalidOperationException("Recovery Systemhaus missing.");
        string after = JsonSerializer.Serialize(new
        {
            origin = "localRecovery", instanceId, sourceBackupManifestSha256 = backupSha256,
            revokedSessions, revokedChallenges, createdUserId = userId, createdGroupId = groupId
        }, Json);
        await using (var audit = Command(db, tx, """
            INSERT INTO public.audit_event(id,systemhaus_id,actor_id,request_id,action,resource_id,before_json,after_json)
            VALUES(@id,@house,@actor,@request,@action,@house,NULL,CAST(@after AS jsonb))
            """, ("id", eventId), ("house", houseId), ("actor", userId), ("request", requestId),
            ("action", Action), ("after", after)))
            await audit.ExecuteNonQueryAsync(ct);
        // database is the exact validated ASCII identifier; no untrusted identifier interpolation.
        await using (var consume = Command(db, tx, $"COMMENT ON DATABASE {database} IS NULL"))
            await consume.ExecuteNonQueryAsync(ct);
        await tx.CommitAsync(ct);
        return new("committed", Action, instanceId, houseId, userId, groupId, eventId, requestId, revokedSessions, afterRevision);
    }

    private static NpgsqlCommand Command(NpgsqlConnection db, NpgsqlTransaction tx, string sql,
        params (string Name, object Value)[] parameters)
    {
        var command = new NpgsqlCommand(sql, db, tx);
        foreach (var (name, value) in parameters) command.Parameters.AddWithValue(name, value);
        return command;
    }
}

public sealed record RecoveryAdministratorResult(string Status, string Action, Guid InstanceId, Guid SystemhausId,
    Guid CreatedUserId, Guid CreatedGroupId, Guid AuditEventId, Guid RequestId, int RevokedSessions, long SystemhausRevision);
