-- Additive personal settings. No historical row, grant or inventory revision changes.
CREATE TABLE user_preferences (
    systemhaus_id uuid NOT NULL,
    owner_id uuid NOT NULL,
    revision bigint NOT NULL DEFAULT 0 CHECK (revision BETWEEN 0 AND 9007199254740991),
    language text CHECK (language IN ('en','de','es')),
    theme text CHECK (theme IN ('dark','light')),
    PRIMARY KEY (systemhaus_id,owner_id),
    FOREIGN KEY (systemhaus_id,owner_id) REFERENCES app_user(systemhaus_id,id)
);

-- The exact UTF-8 result JSON is retained with its format version and SHA256.
-- This terminal journal is not a source from which settings are reconstructed.
-- Cancellation fences are durable until an explicit replay-expiry protocol exists.
CREATE TABLE user_preference_operation (
    systemhaus_id uuid NOT NULL,
    owner_id uuid NOT NULL,
    request_id uuid NOT NULL CHECK (request_id <> '00000000-0000-0000-0000-000000000000'),
    request_hash text NOT NULL CHECK (request_hash ~ '^[0-9A-F]{64}$'),
    state text NOT NULL CHECK (state IN ('committed','cancelled')),
    operation_id uuid NOT NULL UNIQUE CHECK (operation_id <> '00000000-0000-0000-0000-000000000000'),
    revision bigint NOT NULL CHECK (revision BETWEEN 0 AND 9007199254740991),
    result_version integer NOT NULL CHECK (result_version=1),
    result_sha256 text NOT NULL CHECK (result_sha256 ~ '^[0-9A-F]{64}$'),
    result_json text NOT NULL CHECK (jsonb_typeof(result_json::jsonb)='object' AND octet_length(result_json)<=8192),
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (systemhaus_id,owner_id,request_id),
    FOREIGN KEY (systemhaus_id,owner_id) REFERENCES app_user(systemhaus_id,id),
    CHECK (result_sha256=upper(encode(sha256(convert_to(result_json,'UTF8')),'hex'))),
    CHECK (COALESCE(result_json::jsonb->>'kind'='userPreferences'
        AND result_json::jsonb->>'ownerId'=owner_id::text
        AND result_json::jsonb->>'requestId'=request_id::text
        AND result_json::jsonb->>'operationId'=operation_id::text
        AND jsonb_typeof(result_json::jsonb->'revision')='number'
        AND result_json::jsonb->>'revision'=revision::text,false)),
    CHECK (COALESCE(CASE WHEN state='committed' THEN
        result_json::jsonb ?& ARRAY['kind','ownerId','requestId','operationId','revision','result']
        AND (result_json::jsonb - ARRAY['kind','ownerId','requestId','operationId','revision','result'])='{}'::jsonb
        AND jsonb_typeof(result_json::jsonb->'result')='object'
        AND (result_json::jsonb->'result') ?& ARRAY['key','value','changed']
        AND ((result_json::jsonb->'result') - ARRAY['key','value','changed'])='{}'::jsonb
        AND jsonb_typeof(result_json::jsonb->'result'->'changed')='boolean'
        AND ((result_json::jsonb->'result'->>'key'='language' AND result_json::jsonb->'result'->>'value' IN ('en','de','es'))
          OR (result_json::jsonb->'result'->>'key'='theme' AND result_json::jsonb->'result'->>'value' IN ('dark','light')))
    ELSE
        result_json::jsonb ?& ARRAY['kind','state','ownerId','requestId','operationId','revision','operation']
        AND (result_json::jsonb - ARRAY['kind','state','ownerId','requestId','operationId','revision','operation'])='{}'::jsonb
        AND result_json::jsonb->>'state'='cancelled'
        AND result_json::jsonb->'operation'='null'::jsonb
    END,false))
);
