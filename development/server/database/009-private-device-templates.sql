-- Detached, actor-owned configurations. SQL001--008 and inventory revisions remain unchanged.
CREATE TABLE user_device_templates (
    systemhaus_id uuid NOT NULL,
    owner_id uuid NOT NULL,
    revision bigint NOT NULL DEFAULT 0 CHECK (revision BETWEEN 0 AND 9007199254740991),
    PRIMARY KEY (systemhaus_id, owner_id),
    FOREIGN KEY (systemhaus_id, owner_id) REFERENCES app_user(systemhaus_id, id)
);

CREATE TABLE user_device_template (
    id uuid PRIMARY KEY CHECK (id <> '00000000-0000-0000-0000-000000000000'),
    systemhaus_id uuid NOT NULL,
    owner_id uuid NOT NULL,
    name text NOT NULL CHECK (length(btrim(name)) BETWEEN 1 AND 100),
    active boolean NOT NULL DEFAULT true,
    definition_version integer NOT NULL CHECK (definition_version = 1),
    definition_sha256 text NOT NULL CHECK (definition_sha256 ~ '^[0-9a-f]{64}$'),
    -- TEXT retains the exact UTF-8 hash input (including decimal lexical representation).
    definition_json text NOT NULL CHECK (jsonb_typeof(definition_json::jsonb) = 'object' AND octet_length(definition_json) <= 1048576),
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (systemhaus_id, owner_id, id),
    FOREIGN KEY (systemhaus_id, owner_id) REFERENCES user_device_templates(systemhaus_id, owner_id)
);
CREATE INDEX user_device_template_active ON user_device_template(systemhaus_id, owner_id, active, id);

-- A terminal receipt/fence is not a master template; it never contains the definition.
CREATE TABLE user_device_template_operation (
    systemhaus_id uuid NOT NULL,
    owner_id uuid NOT NULL,
    customer_id uuid NOT NULL,
    request_id uuid NOT NULL CHECK (request_id <> '00000000-0000-0000-0000-000000000000'),
    request_hash text NOT NULL CHECK (request_hash ~ '^[0-9A-F]{64}$'),
    state text NOT NULL CHECK (state IN ('committed', 'cancelled')),
    operation_id uuid NOT NULL UNIQUE CHECK (operation_id <> '00000000-0000-0000-0000-000000000000'),
    revision bigint NOT NULL CHECK (revision BETWEEN 0 AND 9007199254740991),
    result_json jsonb NOT NULL CHECK (jsonb_typeof(result_json) = 'object' AND octet_length(result_json::text) <= 8192),
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (systemhaus_id, owner_id, request_id),
    FOREIGN KEY (systemhaus_id, owner_id) REFERENCES app_user(systemhaus_id, id),
    FOREIGN KEY (systemhaus_id, customer_id) REFERENCES customer(systemhaus_id, id)
);
