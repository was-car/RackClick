-- Typed references for the remaining administrative/name writers; no backfill.
ALTER TABLE audit_context ADD COLUMN scope_id uuid;
ALTER TABLE audit_context ADD COLUMN customer_id uuid;
ALTER TABLE audit_context ADD COLUMN customer_revision_before bigint;
ALTER TABLE audit_context ADD COLUMN customer_revision_after bigint;
ALTER TABLE audit_context DROP CONSTRAINT audit_context_scope_kind_check;
ALTER TABLE audit_context ADD CONSTRAINT audit_context_scope_kind_check CHECK (scope_kind IN ('systemhaus','customer'));
ALTER TABLE audit_context ADD CONSTRAINT audit_context_scope_customer_check CHECK (
    (scope_kind='systemhaus' AND scope_id IS NULL AND customer_id IS NULL
        AND customer_revision_before IS NULL AND customer_revision_after IS NULL)
    OR (scope_kind='customer' AND scope_id IS NOT NULL AND customer_id IS NOT NULL AND customer_id=scope_id
        AND scope_id<>'00000000-0000-0000-0000-000000000000'::uuid AND outcome='committed'
        AND customer_revision_after IS NOT NULL AND customer_revision_after>0
        AND ((customer_revision_before IS NULL AND customer_revision_after=1)
            OR (customer_revision_before IS NOT NULL AND customer_revision_before>0
                AND customer_revision_after-customer_revision_before=1)))
);
ALTER TABLE audit_context_object DROP CONSTRAINT audit_context_object_kind_check;
ALTER TABLE audit_context_object ADD CONSTRAINT audit_context_object_kind_check CHECK (kind IN ('systemhaus','user','userGroup','customerGroup','customer','grant','session'));
ALTER TABLE audit_context_object DROP CONSTRAINT audit_context_object_relation_check;
ALTER TABLE audit_context_object ADD CONSTRAINT audit_context_object_relation_check CHECK (relation IN ('target','intendedTarget','member','intendedMember','scope','intendedScope'));
ALTER TABLE audit_context_object DROP CONSTRAINT audit_context_object_kind_relation_check;
ALTER TABLE audit_context_object ADD CONSTRAINT audit_context_object_kind_relation_check CHECK (
    relation IN ('target','intendedTarget')
    OR (kind IN ('user','customer') AND relation IN ('member','intendedMember'))
    OR (kind IN ('systemhaus','customer','customerGroup') AND relation IN ('scope','intendedScope'))
);
