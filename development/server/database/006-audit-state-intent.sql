-- Preserve005 and every existing context. State cancellation refers to an intended user.
ALTER TABLE audit_context_object DROP CONSTRAINT audit_context_object_check;
ALTER TABLE audit_context_object ADD CONSTRAINT audit_context_object_kind_relation_check
    CHECK ((kind = 'user' AND relation IN ('target','intendedTarget'))
        OR (kind = 'systemhaus' AND relation = 'intendedTarget'));
