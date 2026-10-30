using Npgsql;
using RackClick.Domain;

namespace RackClick.Server;

// Entrega la clave de cifrado del secreto TOTP por versión. La implementación con DPAPI depende de
// la decisión D2 (docs/DECISION-D2-CUSTODIA-CLAVE-TOTP.md); no hay proveedor por defecto en el producto.
public interface IMfaKeyProvider
{
    // Clave de una versión concreta del anillo (factores existentes, incluidas versiones retiradas). Devuelve una copia nueva.
    byte[] GetKey(int version);

    // Versión activa del anillo y copia nueva de su clave, obtenidas en una sola operación. Lo usan los nuevos enrolamientos.
    // No hay valor por defecto ni respaldo con la versión 1: si la activa no está disponible, lanza una excepción explícita.
    (int Version, byte[] Key) GetActiveKey();
}

// Segundo paso de MFA: verificación de desafíos de corta vida.
// Orden de bloqueos fijo: cuenta → factor → desafío. El reset administrativo sigue el mismo orden para no bloquearse entre sí.
// Después de cada espera se revalidan cuenta, factor, desafío, CSRF y política. La vigencia usa el reloj de PostgreSQL
// (clock_timestamp) leído después del último bloqueo. El desafío se consume en la misma transacción que emite la sesión.
public sealed partial class MfaStore(NpgsqlDataSource source, IMfaKeyProvider keys)
{
    private const int MaxChallengeAttempts = 5;
    private const int MaxFactorFailures = 5;

    // Invalida los desafíos pendientes del usuario dentro de la transacción del llamador (p. ej. reset de contraseña).
    public static async Task RevokePendingChallenges(NpgsqlConnection db, NpgsqlTransaction tx, Guid systemhausId, Guid userId, CancellationToken ct)
    {
        await using var command = Command(db, tx, """
            UPDATE app_mfa_challenge SET consumed_at=now()
            WHERE systemhaus_id=@systemhaus AND user_id=@user AND consumed_at IS NULL
            """, ("systemhaus", systemhausId), ("user", userId));
        await command.ExecuteNonQueryAsync(ct);
    }

    public async Task<(string Token, string Csrf)> CompleteVerify(string challengeToken, string code, string csrfHeader, CancellationToken ct)
    {
        string tokenHash = Secrets.Digest(challengeToken);
        await using var db = await source.OpenConnectionAsync(ct);
        await using var tx = await db.BeginTransactionAsync(ct);

        // Lectura sin bloqueo solo para saber qué cuenta bloquear. Todo lo decisivo se relee después de bloquear.
        Guid? systemhaus = null;
        Guid? user = null;
        await using (var cmd = Command(db, tx,
            "SELECT systemhaus_id,user_id FROM app_mfa_challenge WHERE token_hash=@token AND purpose='verify'", ("token", tokenHash)))
        await using (var row = await cmd.ExecuteReaderAsync(ct))
            if (await row.ReadAsync(ct)) { systemhaus = row.GetGuid(0); user = row.GetGuid(1); }
        if (systemhaus is null || user is null)
        {
            await tx.CommitAsync(ct);
            throw new DomainError(401, "mfa_challenge_invalid");
        }

        // 1. Cuenta: activa y no bloqueada después de esperar el bloqueo.
        bool accountUsable = false;
        await using (var cmd = Command(db, tx, """
            SELECT active AND (locked_until IS NULL OR locked_until<now())
            FROM app_user WHERE systemhaus_id=@systemhaus AND id=@user FOR UPDATE
            """, ("systemhaus", systemhaus.Value), ("user", user.Value)))
        await using (var row = await cmd.ExecuteReaderAsync(ct))
            if (await row.ReadAsync(ct)) accountUsable = row.GetBoolean(0);

        // 2. Factor activo, no bloqueado.
        byte[]? cipher = null;
        int keyVersion = 0;
        long lastStep = -1;
        bool factorUsable = false;
        await using (var cmd = Command(db, tx, """
            SELECT secret_ciphertext,key_version,last_time_step,state='active' AND (locked_until IS NULL OR locked_until<now())
            FROM app_mfa_factor WHERE systemhaus_id=@systemhaus AND user_id=@user FOR UPDATE
            """, ("systemhaus", systemhaus.Value), ("user", user.Value)))
        await using (var row = await cmd.ExecuteReaderAsync(ct))
            if (await row.ReadAsync(ct))
            {
                cipher = (byte[])row[0]; keyVersion = row.GetInt32(1); lastStep = row.GetInt64(2); factorUsable = row.GetBoolean(3);
            }

        // 3. Desafío bloqueado: estado, intentos, CSRF y revisión de política emitida. La vigencia NO se decide aquí:
        // puede caducar durante las esperas siguientes, así que se mide al final con el reloj de PostgreSQL.
        bool challengeAvailable = false;
        string csrfHash = "";
        long issuedRevision = -1;
        await using (var cmd = Command(db, tx, """
            SELECT consumed_at IS NULL AND attempts<@max,csrf_hash,policy_revision
            FROM app_mfa_challenge WHERE token_hash=@token AND purpose='verify' FOR UPDATE
            """, ("token", tokenHash), ("max", MaxChallengeAttempts)))
        await using (var row = await cmd.ExecuteReaderAsync(ct))
            if (await row.ReadAsync(ct))
            {
                challengeAvailable = row.GetBoolean(0); csrfHash = row.GetString(1); issuedRevision = row.GetInt64(2);
            }

        // 4. Política vigente con la cuenta bloqueada: exigencia, reenrolamiento y revisión.
        bool policyPresent = false;
        bool mfaRequired = false;
        bool enrollmentPending = false;
        long currentRevision = -1;
        await using (var cmd = Command(db, tx, """
            SELECT mfa_required,enrollment_pending,revision FROM app_mfa_user
            WHERE systemhaus_id=@systemhaus AND user_id=@user FOR SHARE
            """, ("systemhaus", systemhaus.Value), ("user", user.Value)))
        await using (var row = await cmd.ExecuteReaderAsync(ct))
            if (await row.ReadAsync(ct))
            {
                policyPresent = true; mfaRequired = row.GetBoolean(0); enrollmentPending = row.GetBoolean(1); currentRevision = row.GetInt64(2);
            }

        // 5. Vigencia y hora con el reloj de PostgreSQL leído después de TODOS los bloqueos.
        DateTimeOffset databaseNow = default;
        bool notExpired = false;
        await using (var cmd = Command(db, tx, """
            SELECT clock_timestamp(),expires_at>clock_timestamp()
            FROM app_mfa_challenge WHERE token_hash=@token AND purpose='verify'
            """, ("token", tokenHash)))
        await using (var row = await cmd.ExecuteReaderAsync(ct))
            if (await row.ReadAsync(ct))
            {
                databaseNow = row.GetFieldValue<DateTimeOffset>(0);
                notExpired = row.GetBoolean(1);
            }
        bool challengeOpen = challengeAvailable && notExpired;

        if (!challengeOpen || !accountUsable || !factorUsable || cipher is null)
        {
            await Burn(db, tx, tokenHash, ct);
            await tx.CommitAsync(ct);
            throw new DomainError(401, "mfa_challenge_invalid");
        }

        // El CSRF del desafío se comprueba antes de cambiar ningún contador: una petición ajena no gasta intentos.
        if (!Secrets.Matches(csrfHeader ?? "", csrfHash))
        {
            await tx.CommitAsync(ct);
            throw new DomainError(403, "csrf_invalid");
        }

        if (!policyPresent || !mfaRequired || enrollmentPending || currentRevision != issuedRevision)
        {
            await Burn(db, tx, tokenHash, ct);
            await tx.CommitAsync(ct);
            throw new DomainError(enrollmentPending ? 409 : 401, enrollmentPending ? "mfa_enrollment_required" : "mfa_challenge_invalid");
        }

        byte[] secret = MfaSecretCipher.Open(keys.GetKey(keyVersion), keyVersion, cipher, systemhaus.Value, user.Value);
        if (!MfaTotp.TryVerify(secret, code, databaseNow, lastStep, out long matchedStep))
        {
            await using (var challenge = Command(db, tx, """
                UPDATE app_mfa_challenge SET attempts=attempts+1,
                  consumed_at=CASE WHEN attempts+1>=@max THEN now() ELSE consumed_at END
                WHERE token_hash=@token
                """, ("token", tokenHash), ("max", MaxChallengeAttempts)))
                await challenge.ExecuteNonQueryAsync(ct);
            await using (var factor = Command(db, tx, """
                UPDATE app_mfa_factor SET failed_attempts=failed_attempts+1,
                  locked_until=CASE WHEN failed_attempts+1>=@max THEN now()+interval '15 minutes' ELSE locked_until END
                WHERE systemhaus_id=@systemhaus AND user_id=@user
                """, ("systemhaus", systemhaus.Value), ("user", user.Value), ("max", MaxFactorFailures)))
                await factor.ExecuteNonQueryAsync(ct);
            await tx.CommitAsync(ct);
            throw new DomainError(401, "mfa_code_invalid");
        }

        await Burn(db, tx, tokenHash, ct);
        await using (var reset = Command(db, tx, """
            UPDATE app_mfa_factor SET last_time_step=@step, failed_attempts=0, locked_until=NULL
            WHERE systemhaus_id=@systemhaus AND user_id=@user
            """, ("step", matchedStep), ("systemhaus", systemhaus.Value), ("user", user.Value)))
            await reset.ExecuteNonQueryAsync(ct);

        string token = Secrets.Token();
        string csrf = Secrets.Csrf(token);
        await using (var session = Command(db, tx, """
            INSERT INTO app_session(token_hash,user_id,csrf_hash,expires_at,mfa_verified_at)
            VALUES(@token,@user,@csrf,now()+interval '8 hours',now())
            """, ("token", Secrets.Digest(token)), ("user", user.Value), ("csrf", Secrets.Digest(csrf))))
            await session.ExecuteNonQueryAsync(ct);
        await tx.CommitAsync(ct);
        return (token, csrf);
    }

    private static async Task Burn(NpgsqlConnection db, NpgsqlTransaction tx, string tokenHash, CancellationToken ct)
    {
        await using var command = Command(db, tx, "UPDATE app_mfa_challenge SET consumed_at=now() WHERE token_hash=@token", ("token", tokenHash));
        await command.ExecuteNonQueryAsync(ct);
    }

    private static NpgsqlCommand Command(NpgsqlConnection db, NpgsqlTransaction? tx, string sql,
        params (string Name, object? Value)[] values)
    {
        var command = new NpgsqlCommand(sql, db, tx);
        foreach (var (name, value) in values)
        {
            command.Parameters.AddWithValue(name, value ?? DBNull.Value);
        }
        return command;
    }
}
