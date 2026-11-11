-- F-06.03. Dedicated local-authority commit witness; never an invented app actor.
-- Inserted in the SAME transaction as factor rewrap and security invalidation.
-- Runtime is granted SELECT separately; only the maintenance identity writes.
CREATE TABLE public.app_mfa_rotation_witness (
    operation_id uuid PRIMARY KEY CHECK(operation_id <> '00000000-0000-0000-0000-000000000000'::uuid),
    mode text NOT NULL CHECK(mode = 'rotate'),
    authority text NOT NULL CHECK(authority = 'windows-local'),
    installation_id uuid NOT NULL CHECK(installation_id <> '00000000-0000-0000-0000-000000000000'::uuid),
    database_name text NOT NULL CHECK(database_name = 'rc_db_' || replace(installation_id::text, '-', '')),
    systemhaus_id uuid NOT NULL REFERENCES public.systemhaus(id),
    operator_sid text NOT NULL CHECK(length(operator_sid) BETWEEN 7 AND 184 AND operator_sid ~ '^S-1-[0-9]+(-[0-9]+){1,15}$'),
    old_version integer NOT NULL CHECK(old_version BETWEEN 1 AND 1000000),
    new_version integer NOT NULL CHECK(new_version BETWEEN 1 AND 1000000 AND new_version > old_version),
    original_ring_sha256 text NOT NULL CHECK(original_ring_sha256 ~ '^[0-9a-f]{64}$'),
    additive_ring_sha256 text NOT NULL CHECK(additive_ring_sha256 ~ '^[0-9a-f]{64}$'),
    final_ring_sha256 text NOT NULL CHECK(final_ring_sha256 ~ '^[0-9a-f]{64}$'),
    new_key_sha256 text NOT NULL CHECK(new_key_sha256 ~ '^[0-9a-f]{64}$'),
    catalog_sha256 text NOT NULL CHECK(catalog_sha256 ~ '^[0-9a-f]{64}$'),
    envelope_sha256 text NOT NULL CHECK(envelope_sha256 ~ '^[0-9a-f]{64}$'),
    factor_count bigint NOT NULL CHECK(factor_count >= 0),
    revoked_sessions bigint NOT NULL CHECK(revoked_sessions >= 0),
    consumed_challenges bigint NOT NULL CHECK(consumed_challenges >= 0),
    committed_at timestamptz NOT NULL DEFAULT clock_timestamp() CHECK(isfinite(committed_at)),
    CHECK(systemhaus_id <> '00000000-0000-0000-0000-000000000000'::uuid),
    CHECK(original_ring_sha256 <> additive_ring_sha256 AND original_ring_sha256 <> final_ring_sha256
        AND additive_ring_sha256 <> final_ring_sha256),
    UNIQUE(installation_id,new_version)
);
REVOKE ALL ON TABLE public.app_mfa_rotation_witness FROM PUBLIC;
