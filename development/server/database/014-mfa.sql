-- MFA (aditiva). Contrato: docs/AUTENTICACION-MFA-S1.md; decisiones: docs/DECISION-D2-CUSTODIA-CLAVE-TOTP.md.
-- Ninguna migración anterior se modifica. El secreto TOTP se guarda cifrado; la clave no está en PostgreSQL.
-- El producto todavía no entrega proveedor de clave: sin proveedor no se emiten desafíos.

ALTER TABLE app_session ADD COLUMN mfa_verified_at timestamptz NULL;

-- Política por usuario, administrada desde el panel de usuarios. Por defecto desactivada (incluido el administrador).
-- enrollment_pending: el usuario debe configurar el factor antes de entrar; no se admite sesión con un factor anterior.
-- changed_by es referencia de auditoría; no se usa para autorizar.
CREATE TABLE app_mfa_user (
    systemhaus_id uuid NOT NULL,
    user_id uuid NOT NULL,
    mfa_required boolean NOT NULL DEFAULT false,
    enrollment_pending boolean NOT NULL DEFAULT false,
    revision bigint NOT NULL DEFAULT 0 CHECK (revision BETWEEN 0 AND 9007199254740991),
    changed_by uuid NULL,
    changed_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (systemhaus_id, user_id),
    FOREIGN KEY (systemhaus_id, user_id) REFERENCES app_user(systemhaus_id, id)
);

-- Un factor TOTP por usuario. Secreto cifrado con autenticación y versión de clave.
CREATE TABLE app_mfa_factor (
    systemhaus_id uuid NOT NULL,
    user_id uuid NOT NULL,
    state text NOT NULL CHECK (state IN ('pending', 'active', 'disabled')),
    secret_ciphertext bytea NOT NULL,
    key_version integer NOT NULL CHECK (key_version > 0),
    last_time_step bigint NOT NULL DEFAULT -1,
    failed_attempts integer NOT NULL DEFAULT 0 CHECK (failed_attempts >= 0),
    locked_until timestamptz NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    confirmed_at timestamptz NULL,
    PRIMARY KEY (systemhaus_id, user_id),
    FOREIGN KEY (systemhaus_id, user_id) REFERENCES app_user(systemhaus_id, id)
);

-- Desafío opaco: solo se guardan su hash y el hash de su CSRF. Vida máxima de cinco minutos y consumo único.
-- policy_revision fija la política con la que se emitió: si cambia antes de completarlo, el desafío se cancela.
CREATE TABLE app_mfa_challenge (
    token_hash text PRIMARY KEY,
    systemhaus_id uuid NOT NULL,
    user_id uuid NOT NULL,
    purpose text NOT NULL CHECK (purpose IN ('enroll', 'verify')),
    csrf_hash text NOT NULL,
    policy_revision bigint NOT NULL DEFAULT 0 CHECK (policy_revision >= 0),
    created_at timestamptz NOT NULL DEFAULT now(),
    expires_at timestamptz NOT NULL,
    attempts integer NOT NULL DEFAULT 0 CHECK (attempts >= 0),
    consumed_at timestamptz NULL,
    CHECK (expires_at <= created_at + interval '5 minutes'),
    FOREIGN KEY (systemhaus_id, user_id) REFERENCES app_user(systemhaus_id, id)
);

-- Códigos de recuperación de un solo uso, guardados solo como hash.
CREATE TABLE app_mfa_recovery_code (
    systemhaus_id uuid NOT NULL,
    user_id uuid NOT NULL,
    code_hash text NOT NULL,
    consumed_at timestamptz NULL,
    PRIMARY KEY (systemhaus_id, user_id, code_hash),
    FOREIGN KEY (systemhaus_id, user_id) REFERENCES app_user(systemhaus_id, id)
);
