-- Foundation only. Future inventory migrations are separate, versioned files.
CREATE TABLE IF NOT EXISTS schema_migration (
    version integer PRIMARY KEY, digest text NOT NULL, applied_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE systemhaus (
    id uuid PRIMARY KEY, name text NOT NULL CHECK(length(btrim(name)) BETWEEN 1 AND 100),
    revision bigint NOT NULL DEFAULT 1 CHECK(revision > 0)
);
-- One Systemhaus per installation; customers are the isolated tenant scopes.
CREATE UNIQUE INDEX one_systemhaus_per_installation ON systemhaus ((true));
CREATE TABLE customer (
    id uuid PRIMARY KEY, systemhaus_id uuid NOT NULL REFERENCES systemhaus(id),
    name text NOT NULL CHECK(length(btrim(name)) BETWEEN 1 AND 100),
    revision bigint NOT NULL DEFAULT 1 CHECK(revision > 0),
    UNIQUE(systemhaus_id,id)
);
CREATE TABLE app_user (
    id uuid PRIMARY KEY, systemhaus_id uuid NOT NULL REFERENCES systemhaus(id),
    username text NOT NULL, password_hash text NOT NULL,
    active boolean NOT NULL DEFAULT true, failed_logins integer NOT NULL DEFAULT 0,
    locked_until timestamptz, UNIQUE(systemhaus_id,id), UNIQUE(systemhaus_id,username)
);
CREATE TABLE user_group (
    id uuid PRIMARY KEY, systemhaus_id uuid NOT NULL REFERENCES systemhaus(id), name text NOT NULL,
    UNIQUE(systemhaus_id,id)
);
CREATE TABLE user_group_member (
    systemhaus_id uuid NOT NULL, user_id uuid NOT NULL, group_id uuid NOT NULL,
    PRIMARY KEY(systemhaus_id,user_id,group_id),
    FOREIGN KEY(systemhaus_id,user_id) REFERENCES app_user(systemhaus_id,id),
    FOREIGN KEY(systemhaus_id,group_id) REFERENCES user_group(systemhaus_id,id)
);
CREATE TABLE customer_group (
    id uuid PRIMARY KEY, systemhaus_id uuid NOT NULL REFERENCES systemhaus(id), name text NOT NULL,
    UNIQUE(systemhaus_id,id)
);
CREATE TABLE customer_group_member (
    systemhaus_id uuid NOT NULL, group_id uuid NOT NULL, customer_id uuid NOT NULL,
    PRIMARY KEY(systemhaus_id,group_id,customer_id),
    FOREIGN KEY(systemhaus_id,group_id) REFERENCES customer_group(systemhaus_id,id),
    FOREIGN KEY(systemhaus_id,customer_id) REFERENCES customer(systemhaus_id,id)
);
CREATE TABLE permission_grant (
    id uuid PRIMARY KEY, systemhaus_id uuid NOT NULL, user_group_id uuid NOT NULL,
    capability text NOT NULL, customer_id uuid, customer_group_id uuid,
    CHECK(customer_id IS NULL OR customer_group_id IS NULL),
    FOREIGN KEY(systemhaus_id,user_group_id) REFERENCES user_group(systemhaus_id,id),
    FOREIGN KEY(systemhaus_id,customer_id) REFERENCES customer(systemhaus_id,id),
    FOREIGN KEY(systemhaus_id,customer_group_id) REFERENCES customer_group(systemhaus_id,id)
);
CREATE TABLE app_session (
    token_hash text PRIMARY KEY, user_id uuid NOT NULL REFERENCES app_user(id),
    csrf_hash text NOT NULL, expires_at timestamptz NOT NULL
);
CREATE TABLE operation (
    systemhaus_id uuid NOT NULL, actor_id uuid NOT NULL, request_id uuid NOT NULL,
    request_hash text NOT NULL, result_json jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY(systemhaus_id,actor_id,request_id),
    FOREIGN KEY(systemhaus_id,actor_id) REFERENCES app_user(systemhaus_id,id)
);
CREATE TABLE audit_event (
    id uuid PRIMARY KEY, systemhaus_id uuid NOT NULL, actor_id uuid NOT NULL,
    request_id uuid NOT NULL, action text NOT NULL, resource_id uuid NOT NULL,
    before_json jsonb, after_json jsonb NOT NULL, occurred_at timestamptz NOT NULL DEFAULT now(),
    FOREIGN KEY(systemhaus_id,actor_id) REFERENCES app_user(systemhaus_id,id)
);
CREATE INDEX permission_subject ON permission_grant(systemhaus_id,user_group_id,capability);
CREATE INDEX session_expiry ON app_session(expires_at);
