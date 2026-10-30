ALTER TABLE app_session ADD COLUMN id uuid NOT NULL DEFAULT gen_random_uuid();
ALTER TABLE app_session ADD CONSTRAINT app_session_public_id_unique UNIQUE (id);
ALTER TABLE app_session ADD CONSTRAINT app_session_public_id_nonempty CHECK (id <> '00000000-0000-0000-0000-000000000000'::uuid);
