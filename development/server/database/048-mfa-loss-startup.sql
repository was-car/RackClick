-- Metadata-only projection for the runtime startup guard. No ciphertext/key/archive access.
-- GROUP BY makes this view intrinsically non-updatable even if a legacy operator grants public DML broadly.
CREATE VIEW public.app_mfa_loss_startup_witness WITH (security_barrier=true) AS
SELECT operation_id,mode,authority,installation_id,database_name,systemhaus_id,operator_sid,lost_versions,new_version,
       plan_sha256,envelope_sha256,material_sha256,post_security_sha256,archive_sha256,
       affected_factors,revoked_sessions,consumed_challenges,consumed_codes,committed_at
FROM rackclick_private.mfa_loss_operation
GROUP BY operation_id;
REVOKE ALL ON public.app_mfa_loss_startup_witness FROM PUBLIC;
