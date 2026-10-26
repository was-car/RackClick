using Npgsql;
using RackClick.Domain;

namespace RackClick.Server;

// Primer paso del login. Misma transacción y mismas comprobaciones de contraseña, bloqueo y fallos que el login anterior.
// Si el usuario tiene MFA exigido y un factor activo, no se crea sesión: se crea un desafío de verificación de cinco minutos
// con su propio CSRF y con la revisión de la política vigente. Un reenrolamiento pendiente no admite desafío ni sesión.
public sealed partial class PostgresStore
{
    // Sesión completa, o desafío MFA sin sesión utilizable (su CSRF viaja solo al endpoint de verificación).
    // ChallengePurpose: 'verify' (segundo factor activo) o 'enroll' (enrolamiento restringido). Null si hay sesión.
    public sealed record LoginOutcome((string Token, string Csrf)? Session, (string Token, string Csrf)? Challenge, string? ChallengePurpose = null);

    // Sin proveedor de clave de producción (D2 pendiente) no se emiten desafíos: el login falla con 503 explícito.
    public bool MfaAvailable { get; init; }

    // Contrato histórico: con enrolamiento necesario lanza 409 mfa_enrollment_required y no emite desafío.
    public Task<LoginOutcome> Authenticate(string username, string password, CancellationToken ct) =>
        AuthenticateCore(username, password, allowEnrollmentChallenge: false, ct);

    // Login HTTP: con proveedor disponible, un enrolamiento necesario emite un desafío 'enroll' restringido, sin sesión API.
    public Task<LoginOutcome> AuthenticateForLogin(string username, string password, CancellationToken ct) =>
        AuthenticateCore(username, password, allowEnrollmentChallenge: true, ct);

    private async Task<LoginOutcome> AuthenticateCore(string username, string password, bool allowEnrollmentChallenge, CancellationToken ct)
    {
        try { username = UserNames.Normalize(username); }
        catch (DomainError) { throw new DomainError(401, "login_failed"); }
        if (password.Length > 1024) throw new DomainError(401, "login_failed");
        await using var db = await DataSource.OpenConnectionAsync(ct);
        await using var tx = await db.BeginTransactionAsync(ct);
        Guid? id = null;
        Guid? systemhaus = null;
        string? hash = null;
        bool available = false;
        await using (var cmd = Command(db, tx, """
            SELECT id,password_hash,active AND (locked_until IS NULL OR locked_until<now()),systemhaus_id
            FROM app_user WHERE username=@name FOR UPDATE
            """, ("name", username)))
        await using (var row = await cmd.ExecuteReaderAsync(ct))
            if (await row.ReadAsync(ct))
            {
                id = row.GetGuid(0); hash = row.GetString(1); available = row.GetBoolean(2); systemhaus = row.GetGuid(3);
            }
        bool valid = Secrets.PasswordValid(username, hash, password);
        if (!available || !valid)
        {
            if (id is not null && available)
            {
                await using var fail = Command(db, tx, """
                    UPDATE app_user SET failed_logins=failed_logins+1,
                      locked_until=CASE WHEN failed_logins+1>=5 THEN now()+interval '15 minutes' ELSE locked_until END
                    WHERE id=@id
                    """, ("id", id.Value));
                await fail.ExecuteNonQueryAsync(ct);
            }
            await tx.CommitAsync(ct);
            throw new DomainError(401, "login_failed");
        }

        await using (var reset = Command(db, tx,
            "UPDATE app_user SET failed_logins=0,locked_until=NULL WHERE id=@id", ("id", id!.Value)))
            await reset.ExecuteNonQueryAsync(ct);

        bool mfaRequired = false;
        bool enrollmentPending = false;
        bool factorActive = false;
        long policyRevision = 0;
        await using (var policy = Command(db, tx, """
            SELECT m.mfa_required,m.enrollment_pending,m.revision,
                   EXISTS(SELECT 1 FROM app_mfa_factor f
                          WHERE f.systemhaus_id=m.systemhaus_id AND f.user_id=m.user_id AND f.state='active')
            FROM app_mfa_user m WHERE m.systemhaus_id=@systemhaus AND m.user_id=@id
            """, ("systemhaus", systemhaus!.Value), ("id", id.Value)))
        await using (var row = await policy.ExecuteReaderAsync(ct))
            if (await row.ReadAsync(ct))
            {
                mfaRequired = row.GetBoolean(0); enrollmentPending = row.GetBoolean(1);
                policyRevision = row.GetInt64(2); factorActive = row.GetBoolean(3);
            }

        // Reenrolamiento necesario: el factor anterior no basta. Con proveedor y en el login HTTP, se emite un desafío 'enroll'
        // restringido (sin sesión). Sin proveedor, o en el contrato histórico, se rechaza con 409 explícito.
        if (enrollmentPending || (mfaRequired && !factorActive))
        {
            if (!allowEnrollmentChallenge || !MfaAvailable)
            {
                await tx.CommitAsync(ct);
                throw new DomainError(409, "mfa_enrollment_required");
            }
            string enrollChallenge = Secrets.Token();
            string enrollCsrf = Secrets.Csrf(enrollChallenge);
            await using (var add = Command(db, tx, """
                INSERT INTO app_mfa_challenge(token_hash,systemhaus_id,user_id,purpose,csrf_hash,policy_revision,expires_at)
                VALUES(@token,@systemhaus,@id,'enroll',@csrf,@revision,now()+interval '5 minutes')
                """, ("token", Secrets.Digest(enrollChallenge)), ("systemhaus", systemhaus!.Value), ("id", id.Value),
                ("csrf", Secrets.Digest(enrollCsrf)), ("revision", policyRevision)))
                await add.ExecuteNonQueryAsync(ct);
            await tx.CommitAsync(ct);
            return new LoginOutcome(null, (enrollChallenge, enrollCsrf), "enroll");
        }
        if (mfaRequired)
        {
            if (!MfaAvailable)
            {
                await tx.CommitAsync(ct);
                throw new DomainError(503, "mfa_unavailable");
            }
            string challenge = Secrets.Token();
            string challengeCsrf = Secrets.Csrf(challenge);
            await using (var add = Command(db, tx, """
                INSERT INTO app_mfa_challenge(token_hash,systemhaus_id,user_id,purpose,csrf_hash,policy_revision,expires_at)
                VALUES(@token,@systemhaus,@id,'verify',@csrf,@revision,now()+interval '5 minutes')
                """, ("token", Secrets.Digest(challenge)), ("systemhaus", systemhaus.Value), ("id", id.Value),
                ("csrf", Secrets.Digest(challengeCsrf)), ("revision", policyRevision)))
                await add.ExecuteNonQueryAsync(ct);
            await tx.CommitAsync(ct);
            return new LoginOutcome(null, (challenge, challengeCsrf));
        }

        string token = Secrets.Token();
        string csrf = Secrets.Csrf(token);
        await using (var add = Command(db, tx, """
            INSERT INTO app_session(token_hash,user_id,csrf_hash,expires_at)
            VALUES(@token,@id,@csrf,now()+interval '8 hours')
            """, ("token", Secrets.Digest(token)), ("id", id.Value), ("csrf", Secrets.Digest(csrf))))
            await add.ExecuteNonQueryAsync(ct);
        await tx.CommitAsync(ct);
        return new LoginOutcome((token, csrf), null);
    }
}
