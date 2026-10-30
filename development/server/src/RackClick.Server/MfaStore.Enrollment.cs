using System.Security.Cryptography;
using Npgsql;
using OtpNet;
using RackClick.Domain;

namespace RackClick.Server;

// Enrolamiento TOTP restringido (MFA-L1). Solo entra con un desafío 'enroll' emitido tras contraseña válida.
// Mismo orden de bloqueos y revalidaciones que CompleteVerify: cuenta → factor → desafío → política, con el reloj de PostgreSQL.
// La sesión nueva se emite en la misma transacción que consume el desafío. El secreto solo se entrega al titular del flujo,
// por respuesta; nunca en URL, logs, auditoría ni diagnóstico. Sin proveedor de clave no hay enrolamiento.
public sealed partial class MfaStore
{
    public sealed record EnrollmentStart(string SecretBase32, string OtpAuthUri);

    private sealed record LockedChallenge(
        Guid Systemhaus, Guid User, string Username, bool AccountUsable,
        byte[]? Cipher, int KeyVersion, long LastStep, string? FactorState,
        bool ChallengeAvailable, string CsrfHash, long IssuedRevision,
        bool PolicyPresent, bool MfaRequired, bool EnrollmentPending, long CurrentRevision,
        DateTimeOffset DatabaseNow, bool NotExpired, bool FactorLocked)
    {
        // Enrolamiento necesario: pendiente explícito, o exigencia sin factor activo.
        public bool NeedsEnrollment => EnrollmentPending || (MfaRequired && FactorState != "active");
    }

    // Paso 1: el titular recibe el secreto y su URI de configuración. Reemplaza cualquier factor anterior pendiente.
    public async Task<EnrollmentStart> StartEnrollment(string challengeToken, string csrfHeader, CancellationToken ct)
    {
        string tokenHash = Secrets.Digest(challengeToken);
        await using var db = await source.OpenConnectionAsync(ct);
        await using var tx = await db.BeginTransactionAsync(ct);
        var state = await LockChallenge(db, tx, tokenHash, "enroll", ct);
        if (state is null)
        {
            await tx.CommitAsync(ct);
            throw new DomainError(401, "mfa_challenge_invalid");
        }
        if (!ChallengeOpen(state))
        {
            await Burn(db, tx, tokenHash, ct);
            await tx.CommitAsync(ct);
            throw new DomainError(401, "mfa_challenge_invalid");
        }
        if (!Secrets.Matches(csrfHeader ?? "", state.CsrfHash))
        {
            await tx.CommitAsync(ct);
            throw new DomainError(403, "csrf_invalid");
        }

        byte[] secret = MfaTotp.NewSecret();
        // Versión activa del anillo: el nuevo factor se cifra y se guarda con esa misma versión. Si el proveedor falla, la
        // excepción sale antes de cualquier escritura y la transacción se revierte. La copia recibida es nuestra: se pone a cero.
        var (version, key) = keys.GetActiveKey();
        byte[] cipher;
        try
        {
            cipher = MfaSecretCipher.Seal(key, version, secret, state.Systemhaus, state.User);
        }
        finally
        {
            CryptographicOperations.ZeroMemory(key);
        }
        await using (var upsert = Command(db, tx, """
            INSERT INTO app_mfa_factor(systemhaus_id,user_id,state,secret_ciphertext,key_version,last_time_step,failed_attempts,locked_until,created_at,confirmed_at)
            VALUES(@systemhaus,@user,'pending',@cipher,@version,-1,0,NULL,now(),NULL)
            ON CONFLICT (systemhaus_id,user_id) DO UPDATE SET state='pending',secret_ciphertext=EXCLUDED.secret_ciphertext,
              key_version=EXCLUDED.key_version,last_time_step=-1,created_at=now(),confirmed_at=NULL
            """, ("systemhaus", state.Systemhaus), ("user", state.User), ("cipher", cipher), ("version", version)))
            await upsert.ExecuteNonQueryAsync(ct);
        await WriteAudit(db, tx, state.Systemhaus, state.User, "auth.mfa.enrollment_started", ct);
        await tx.CommitAsync(ct);

        string base32 = Base32Encoding.ToString(secret);
        string label = Uri.EscapeDataString("RackClick:" + state.Username);
        string uri = $"otpauth://totp/{label}?secret={base32}&issuer=RackClick&algorithm=SHA1&digits={MfaTotp.Digits}&period={MfaTotp.StepSeconds}";
        return new EnrollmentStart(base32, uri);
    }

    // Paso 2: confirmar un código del factor pendiente activa el factor, retira el enrolamiento pendiente,
    // consume el desafío y emite sesión y CSRF nuevos en la misma transacción.
    public async Task<(string Token, string Csrf)> ConfirmEnrollment(string challengeToken, string code, string csrfHeader, CancellationToken ct)
    {
        string tokenHash = Secrets.Digest(challengeToken);
        await using var db = await source.OpenConnectionAsync(ct);
        await using var tx = await db.BeginTransactionAsync(ct);
        var state = await LockChallenge(db, tx, tokenHash, "enroll", ct);
        if (state is null)
        {
            await tx.CommitAsync(ct);
            throw new DomainError(401, "mfa_challenge_invalid");
        }
        if (!ChallengeOpen(state) || state.Cipher is null)
        {
            await Burn(db, tx, tokenHash, ct);
            await tx.CommitAsync(ct);
            throw new DomainError(401, "mfa_challenge_invalid");
        }
        if (!Secrets.Matches(csrfHeader ?? "", state.CsrfHash))
        {
            await tx.CommitAsync(ct);
            throw new DomainError(403, "csrf_invalid");
        }
        if (state.FactorState != "pending")
        {
            await tx.CommitAsync(ct);
            throw new DomainError(409, "mfa_enrollment_not_started");
        }

        byte[] secret = MfaSecretCipher.Open(keys.GetKey(state.KeyVersion), state.KeyVersion, state.Cipher, state.Systemhaus, state.User);
        if (!MfaTotp.TryVerify(secret, code, state.DatabaseNow, state.LastStep, out long matchedStep))
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
                """, ("systemhaus", state.Systemhaus), ("user", state.User), ("max", MaxFactorFailures)))
                await factor.ExecuteNonQueryAsync(ct);
            await tx.CommitAsync(ct);
            throw new DomainError(401, "mfa_code_invalid");
        }

        await using (var activate = Command(db, tx, """
            UPDATE app_mfa_factor SET state='active',last_time_step=@step,failed_attempts=0,locked_until=NULL,confirmed_at=now()
            WHERE systemhaus_id=@systemhaus AND user_id=@user AND state='pending'
            """, ("step", matchedStep), ("systemhaus", state.Systemhaus), ("user", state.User)))
            await activate.ExecuteNonQueryAsync(ct);
        // Cambia la revisión de la política: los desafíos emitidos antes quedan invalidados.
        await using (var policy = Command(db, tx, """
            UPDATE app_mfa_user SET enrollment_pending=false,revision=revision+1,changed_at=now()
            WHERE systemhaus_id=@systemhaus AND user_id=@user
            """, ("systemhaus", state.Systemhaus), ("user", state.User)))
            await policy.ExecuteNonQueryAsync(ct);
        await Burn(db, tx, tokenHash, ct);

        string token = Secrets.Token();
        string csrf = Secrets.Csrf(token);
        await using (var session = Command(db, tx, """
            INSERT INTO app_session(token_hash,user_id,csrf_hash,expires_at,mfa_verified_at)
            VALUES(@token,@user,@csrf,now()+interval '8 hours',now())
            """, ("token", Secrets.Digest(token)), ("user", state.User), ("csrf", Secrets.Digest(csrf))))
            await session.ExecuteNonQueryAsync(ct);
        await WriteAudit(db, tx, state.Systemhaus, state.User, "auth.mfa.enrollment_confirmed", ct);
        await tx.CommitAsync(ct);
        return (token, csrf);
    }

    private static async Task WriteAudit(NpgsqlConnection db, NpgsqlTransaction tx, Guid systemhaus, Guid user, string action, CancellationToken ct)
    {
        await using var audit = Command(db, tx, """
            INSERT INTO audit_event(id,systemhaus_id,actor_id,request_id,action,resource_id,before_json,after_json)
            VALUES(@id,@systemhaus,@user,@request,@action,@user,NULL,'{"result":"ok"}'::jsonb)
            """, ("id", Guid.NewGuid()), ("systemhaus", systemhaus), ("user", user), ("request", Guid.NewGuid()), ("action", action));
        await audit.ExecuteNonQueryAsync(ct);
    }

    private static bool ChallengeOpen(LockedChallenge state) =>
        state.PolicyPresent && state.AccountUsable && state.ChallengeAvailable && state.NotExpired
        && !state.FactorLocked && state.NeedsEnrollment && state.CurrentRevision == state.IssuedRevision;

    // Lectura con bloqueos en el orden fijo cuenta → factor → desafío → política. El reloj se lee al final.
    private static async Task<LockedChallenge?> LockChallenge(NpgsqlConnection db, NpgsqlTransaction tx, string tokenHash, string purpose, CancellationToken ct)
    {
        Guid? systemhaus = null, user = null;
        await using (var cmd = Command(db, tx,
            "SELECT systemhaus_id,user_id FROM app_mfa_challenge WHERE token_hash=@token AND purpose=@purpose",
            ("token", tokenHash), ("purpose", purpose)))
        await using (var row = await cmd.ExecuteReaderAsync(ct))
            if (await row.ReadAsync(ct)) { systemhaus = row.GetGuid(0); user = row.GetGuid(1); }
        if (systemhaus is null || user is null) return null;

        string username = "";
        bool accountUsable = false;
        await using (var cmd = Command(db, tx, """
            SELECT username, active AND (locked_until IS NULL OR locked_until<now())
            FROM app_user WHERE systemhaus_id=@systemhaus AND id=@user FOR UPDATE
            """, ("systemhaus", systemhaus.Value), ("user", user.Value)))
        await using (var row = await cmd.ExecuteReaderAsync(ct))
            if (await row.ReadAsync(ct)) { username = row.GetString(0); accountUsable = row.GetBoolean(1); }

        byte[]? cipher = null;
        int keyVersion = 0;
        long lastStep = -1;
        string? factorState = null;
        await using (var cmd = Command(db, tx, """
            SELECT secret_ciphertext,key_version,last_time_step,state
            FROM app_mfa_factor WHERE systemhaus_id=@systemhaus AND user_id=@user FOR UPDATE
            """, ("systemhaus", systemhaus.Value), ("user", user.Value)))
        await using (var row = await cmd.ExecuteReaderAsync(ct))
            if (await row.ReadAsync(ct))
            {
                cipher = (byte[])row[0]; keyVersion = row.GetInt32(1); lastStep = row.GetInt64(2); factorState = row.GetString(3);
            }

        bool challengeAvailable = false;
        string csrfHash = "";
        long issuedRevision = -1;
        await using (var cmd = Command(db, tx, """
            SELECT consumed_at IS NULL AND attempts<@max,csrf_hash,policy_revision
            FROM app_mfa_challenge WHERE token_hash=@token AND purpose=@purpose FOR UPDATE
            """, ("token", tokenHash), ("purpose", purpose), ("max", MaxChallengeAttempts)))
        await using (var row = await cmd.ExecuteReaderAsync(ct))
            if (await row.ReadAsync(ct))
            {
                challengeAvailable = row.GetBoolean(0); csrfHash = row.GetString(1); issuedRevision = row.GetInt64(2);
            }

        bool policyPresent = false, mfaRequired = false, enrollmentPending = false;
        long currentRevision = -1;
        await using (var cmd = Command(db, tx, """
            SELECT mfa_required,enrollment_pending,revision FROM app_mfa_user
            WHERE systemhaus_id=@systemhaus AND user_id=@user FOR UPDATE
            """, ("systemhaus", systemhaus.Value), ("user", user.Value)))
        await using (var row = await cmd.ExecuteReaderAsync(ct))
            if (await row.ReadAsync(ct))
            {
                policyPresent = true; mfaRequired = row.GetBoolean(0); enrollmentPending = row.GetBoolean(1); currentRevision = row.GetInt64(2);
            }

        DateTimeOffset databaseNow = default;
        bool notExpired = false;
        bool factorLocked = false;
        await using (var cmd = Command(db, tx, """
            SELECT clock_timestamp(),expires_at>clock_timestamp(),
                   COALESCE((SELECT locked_until>clock_timestamp() FROM app_mfa_factor
                             WHERE systemhaus_id=@systemhaus AND user_id=@user),false)
            FROM app_mfa_challenge WHERE token_hash=@token AND purpose=@purpose
            """, ("token", tokenHash), ("purpose", purpose), ("systemhaus", systemhaus.Value), ("user", user.Value)))
        await using (var row = await cmd.ExecuteReaderAsync(ct))
            if (await row.ReadAsync(ct))
            {
                databaseNow = row.GetFieldValue<DateTimeOffset>(0);
                notExpired = row.GetBoolean(1);
                factorLocked = row.GetBoolean(2);
            }

        return new LockedChallenge(systemhaus.Value, user.Value, username, accountUsable, cipher, keyVersion, lastStep, factorState,
            challengeAvailable, csrfHash, issuedRevision, policyPresent, mfaRequired, enrollmentPending, currentRevision,
            databaseNow, notExpired, factorLocked);
    }
}
