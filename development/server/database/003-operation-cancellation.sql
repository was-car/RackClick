-- Durable cancellation fences for commands whose response was lost. Never undo a committed operation.
CREATE TABLE operation_cancellation (
    systemhaus_id uuid NOT NULL,
    actor_id uuid NOT NULL,
    request_id uuid NOT NULL CHECK (request_id <> '00000000-0000-0000-0000-000000000000'),
    customer_id uuid NOT NULL,
    request_hash text NOT NULL CHECK (request_hash ~ '^[0-9A-F]{64}$'),
    operation_id uuid NOT NULL UNIQUE,
    result_json jsonb NOT NULL CHECK (jsonb_typeof(result_json) = 'object'),
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (systemhaus_id, actor_id, request_id),
    FOREIGN KEY (systemhaus_id, actor_id) REFERENCES app_user(systemhaus_id, id),
    FOREIGN KEY (systemhaus_id, customer_id) REFERENCES customer(systemhaus_id, id)
);

-- Same transaction-scoped key as PostgresStore.LockOperation. It also protects direct SQL inserts
-- from creating both terminal states. This is not an authorization grant or a SECURITY DEFINER function.
CREATE FUNCTION operation_terminal_state_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    PERFORM pg_advisory_xact_lock(hashtextextended(
        'RackClick/operation/' || NEW.systemhaus_id::text || '/' || NEW.actor_id::text || '/' || NEW.request_id::text, 0));
    IF TG_TABLE_NAME = 'operation' THEN
        IF EXISTS (SELECT 1 FROM operation_cancellation
                   WHERE systemhaus_id = NEW.systemhaus_id AND actor_id = NEW.actor_id AND request_id = NEW.request_id) THEN
            RAISE EXCEPTION 'Operation already cancelled' USING ERRCODE = '23505', CONSTRAINT = 'operation_terminal_state_conflict';
        END IF;
    ELSE
        IF EXISTS (SELECT 1 FROM operation
                   WHERE systemhaus_id = NEW.systemhaus_id AND actor_id = NEW.actor_id AND request_id = NEW.request_id) THEN
            RAISE EXCEPTION 'Operation already committed' USING ERRCODE = '23505', CONSTRAINT = 'operation_terminal_state_conflict';
        END IF;
    END IF;
    RETURN NEW;
END $$;

CREATE TRIGGER operation_terminal_state BEFORE INSERT OR UPDATE ON operation
    FOR EACH ROW EXECUTE FUNCTION operation_terminal_state_guard();
CREATE TRIGGER cancellation_terminal_state BEFORE INSERT OR UPDATE ON operation_cancellation
    FOR EACH ROW EXECUTE FUNCTION operation_terminal_state_guard();

-- Fences are retained indefinitely in this revision. Deleting one could permit a delayed request;
-- retention/archival requires an explicit replay-expiry protocol, not a blind scheduled DELETE.
