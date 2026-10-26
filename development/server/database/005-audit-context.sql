-- Additive capture only; historical audit_event rows are never backfilled.
-- Identity, actor, House, request and time remain authoritative in audit_event.
CREATE TABLE audit_context (
    event_id uuid PRIMARY KEY REFERENCES audit_event(id),
    capture_version integer NOT NULL CHECK (capture_version = 1),
    scope_kind text NOT NULL CHECK (scope_kind = 'systemhaus'),
    revision_scope text NOT NULL CHECK (revision_scope = 'systemhaus'),
    revision_before bigint NOT NULL CHECK (revision_before > 0),
    revision_after bigint NOT NULL CHECK (revision_after > 0),
    outcome text NOT NULL CHECK (outcome IN ('committed','cancelled')),
    CHECK (event_id <> '00000000-0000-0000-0000-000000000000'::uuid),
    CHECK ((outcome = 'committed' AND revision_after - revision_before = 1)
        OR (outcome = 'cancelled' AND revision_after = revision_before))
);
CREATE TABLE audit_context_object (
    event_id uuid NOT NULL REFERENCES audit_context(event_id),
    position smallint NOT NULL CHECK (position BETWEEN 1 AND 16),
    kind text NOT NULL CHECK (kind IN ('user','systemhaus')),
    object_id uuid NOT NULL CHECK (object_id <> '00000000-0000-0000-0000-000000000000'::uuid),
    relation text NOT NULL CHECK (relation IN ('target','intendedTarget')),
    PRIMARY KEY (event_id,position),
    CHECK ((kind = 'user' AND relation = 'target')
        OR (kind = 'systemhaus' AND relation = 'intendedTarget'))
);
-- No FK to a live user/House target: cancelled intent is not resource existence.
