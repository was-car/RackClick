-- Additive shared copies. No UPDATE/GRANT on historical rows or permission grants.
CREATE TABLE customer_device_templates (
    systemhaus_id uuid NOT NULL,
    customer_id uuid NOT NULL,
    revision bigint NOT NULL DEFAULT 0 CHECK (revision BETWEEN 0 AND 9007199254740991),
    PRIMARY KEY (systemhaus_id, customer_id),
    FOREIGN KEY (systemhaus_id, customer_id) REFERENCES customer(systemhaus_id,id)
);
CREATE TABLE customer_device_template (
    id uuid PRIMARY KEY CHECK (id <> '00000000-0000-0000-0000-000000000000'),
    systemhaus_id uuid NOT NULL,
    customer_id uuid NOT NULL,
    published_by_id uuid NOT NULL,
    published_by_name text NOT NULL CHECK (length(published_by_name) BETWEEN 1 AND 100),
    name text NOT NULL CHECK (length(btrim(name)) BETWEEN 1 AND 100),
    active boolean NOT NULL DEFAULT true,
    definition_version integer NOT NULL CHECK (definition_version=1),
    definition_sha256 text NOT NULL CHECK (definition_sha256 ~ '^[0-9a-f]{64}$'),
    definition_json text NOT NULL CHECK (jsonb_typeof(definition_json::jsonb)='object' AND octet_length(definition_json)<=1048576),
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (systemhaus_id,customer_id,id),
    FOREIGN KEY (systemhaus_id,customer_id) REFERENCES customer_device_templates(systemhaus_id,customer_id),
    FOREIGN KEY (systemhaus_id,published_by_id) REFERENCES app_user(systemhaus_id,id)
);
CREATE INDEX customer_device_template_active ON customer_device_template(systemhaus_id,customer_id,active,id);
CREATE TABLE customer_device_template_operation (
    systemhaus_id uuid NOT NULL,
    actor_id uuid NOT NULL,
    customer_id uuid NOT NULL,
    request_id uuid NOT NULL CHECK (request_id <> '00000000-0000-0000-0000-000000000000'),
    request_hash text NOT NULL CHECK (request_hash ~ '^[0-9A-F]{64}$'),
    state text NOT NULL CHECK (state IN ('committed','cancelled')),
    operation_id uuid NOT NULL UNIQUE CHECK (operation_id <> '00000000-0000-0000-0000-000000000000'),
    revision bigint NOT NULL CHECK (revision BETWEEN 0 AND 9007199254740991),
    result_json jsonb NOT NULL CHECK (jsonb_typeof(result_json)='object' AND octet_length(result_json::text)<=8192),
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (systemhaus_id,actor_id,request_id),
    FOREIGN KEY (systemhaus_id,actor_id) REFERENCES app_user(systemhaus_id,id),
    FOREIGN KEY (systemhaus_id,customer_id) REFERENCES customer(systemhaus_id,id)
);
