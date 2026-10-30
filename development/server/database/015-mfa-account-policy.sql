-- Account creation time and delayed MFA enforcement. Additive; schema14 evidence stays unchanged.
-- Existing creation dates were not recorded: preserve NULL instead of inventing a historical date.
ALTER TABLE app_user ADD COLUMN created_at timestamptz NULL;
ALTER TABLE app_user ALTER COLUMN created_at SET DEFAULT clock_timestamp();

-- No policy is enabled by this migration. Rollout must explicitly set enabled and activated_at.
CREATE TABLE app_mfa_policy (
    systemhaus_id uuid PRIMARY KEY REFERENCES systemhaus(id),
    enabled boolean NOT NULL DEFAULT false,
    grace_days integer NOT NULL CHECK(grace_days=45),
    activated_at timestamptz NOT NULL,
    revision bigint NOT NULL DEFAULT 1 CHECK(revision BETWEEN 1 AND 9007199254740991)
);
