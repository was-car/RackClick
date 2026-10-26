-- Personal BASE-catalog membership. Existing customer/Systemhaus revisions are untouched.
CREATE TABLE user_catalog_favorites (
    systemhaus_id uuid NOT NULL,
    owner_id uuid NOT NULL,
    revision bigint NOT NULL DEFAULT 0 CHECK (revision BETWEEN 0 AND 9007199254740991),
    PRIMARY KEY (systemhaus_id, owner_id),
    FOREIGN KEY (systemhaus_id, owner_id) REFERENCES app_user(systemhaus_id, id)
);

CREATE TABLE user_catalog_favorite (
    systemhaus_id uuid NOT NULL,
    owner_id uuid NOT NULL,
    preset_key text NOT NULL CHECK (preset_key ~ '^[a-z0-9][a-z0-9_-]{0,63}$'),
    PRIMARY KEY (systemhaus_id, owner_id, preset_key),
    FOREIGN KEY (systemhaus_id, owner_id) REFERENCES user_catalog_favorites(systemhaus_id, owner_id)
);

-- A single durable terminal row is either commit or cancellation, never both.
-- This journal is not the master favorite set; do not replay it to reconstruct membership.
-- Retain cancellation fences until an explicit replay-expiry protocol exists.
CREATE TABLE user_catalog_favorite_operation (
    systemhaus_id uuid NOT NULL,
    owner_id uuid NOT NULL,
    request_id uuid NOT NULL CHECK (request_id <> '00000000-0000-0000-0000-000000000000'),
    request_hash text NOT NULL CHECK (request_hash ~ '^[0-9A-F]{64}$'),
    state text NOT NULL CHECK (state IN ('committed', 'cancelled')),
    operation_id uuid NOT NULL UNIQUE CHECK (operation_id <> '00000000-0000-0000-0000-000000000000'),
    revision bigint NOT NULL CHECK (revision BETWEEN 0 AND 9007199254740991),
    result_json jsonb NOT NULL CHECK (jsonb_typeof(result_json) = 'object' AND octet_length(result_json::text) <= 8192),
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (systemhaus_id, owner_id, request_id),
    FOREIGN KEY (systemhaus_id, owner_id) REFERENCES app_user(systemhaus_id, id)
);
