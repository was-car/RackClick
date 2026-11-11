-- F-09.02. Owner-only archive and local-authority witness, never an application actor or public audit payload.
-- PUBLIC-table runtime grants do not grant USAGE/SELECT/DML here. No default role or existing data is changed.
CREATE SCHEMA rackclick_private;
REVOKE ALL ON SCHEMA rackclick_private FROM PUBLIC;
CREATE TABLE rackclick_private.mfa_loss_operation (
    operation_id uuid PRIMARY KEY CHECK(operation_id<>'00000000-0000-0000-0000-000000000000'::uuid),
    mode text NOT NULL CHECK(mode='loss-reset'),
    authority text NOT NULL CHECK(authority='windows-local'),
    installation_id uuid NOT NULL CHECK(installation_id<>'00000000-0000-0000-0000-000000000000'::uuid),
    database_name text NOT NULL CHECK(database_name='rc_db_'||replace(installation_id::text,'-','')),
    systemhaus_id uuid NOT NULL REFERENCES public.systemhaus(id),
    operator_sid text NOT NULL CHECK(length(operator_sid) BETWEEN 7 AND 184 AND operator_sid ~ '^S-1-[0-9]+(-[0-9]+){1,15}$'),
    lost_versions integer[] NOT NULL CHECK(cardinality(lost_versions) BETWEEN 1 AND 64
        AND array_position(lost_versions,NULL) IS NULL AND 0<ALL(lost_versions) AND 1000000>=ALL(lost_versions)),
    new_version integer NOT NULL CHECK(new_version BETWEEN 1 AND 1000000 AND new_version>ALL(lost_versions)),
    plan_sha256 text NOT NULL CHECK(plan_sha256 ~ '^[0-9a-f]{64}$'),
    envelope_sha256 text NOT NULL CHECK(envelope_sha256 ~ '^[0-9a-f]{64}$'),
    material_sha256 text NOT NULL CHECK(material_sha256 ~ '^[0-9a-f]{64}$'),
    post_security_sha256 text NOT NULL CHECK(post_security_sha256 ~ '^[0-9a-f]{64}$'),
    archive_sha256 text NOT NULL CHECK(archive_sha256 ~ '^[0-9a-f]{64}$'),
    affected_factors bigint NOT NULL CHECK(affected_factors>=0),
    revoked_sessions bigint NOT NULL CHECK(revoked_sessions>=0),
    consumed_challenges bigint NOT NULL CHECK(consumed_challenges>=0),
    consumed_codes bigint NOT NULL CHECK(consumed_codes>=0),
    committed_at timestamptz NOT NULL DEFAULT clock_timestamp() CHECK(isfinite(committed_at)),
    UNIQUE(installation_id,new_version)
);
CREATE TABLE rackclick_private.mfa_loss_factor_archive (
    operation_id uuid NOT NULL REFERENCES rackclick_private.mfa_loss_operation(operation_id),
    systemhaus_id uuid NOT NULL,
    user_id uuid NOT NULL,
    key_version integer NOT NULL CHECK(key_version BETWEEN 1 AND 1000000),
    factor_row jsonb NOT NULL CHECK(jsonb_typeof(factor_row)='object' AND octet_length(factor_row::text)<=65536
        AND (factor_row->>'systemhaus_id')::uuid=systemhaus_id AND (factor_row->>'user_id')::uuid=user_id
        AND (factor_row->>'key_version')::integer=key_version),
    PRIMARY KEY(operation_id,systemhaus_id,user_id)
);
-- No FK to a live user/factor: future account cleanup must not erase the preserved encrypted row.
REVOKE ALL ON ALL TABLES IN SCHEMA rackclick_private FROM PUBLIC;
