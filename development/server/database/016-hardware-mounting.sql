-- Own reference profiles, not a vendor specification. Existing rows remain unbound roots.
ALTER TABLE inventory_device ADD COLUMN hardware_profile_key text;
ALTER TABLE inventory_device ADD COLUMN mount_parent_id uuid;
ALTER TABLE inventory_device ADD COLUMN mount_slot_key text;
-- Replace only the placement CHECK installed by 002 (its generated name is stable).
ALTER TABLE inventory_device DROP CONSTRAINT inventory_device_check;
ALTER TABLE inventory_device ADD CONSTRAINT inventory_device_placement CHECK ((
 (kind='rackEquipment' AND rack_id IS NOT NULL AND room_id IS NULL AND size_u IS NOT NULL AND
   ((mount_parent_id IS NULL AND mount_slot_key IS NULL AND size_u BETWEEN 1 AND 1000) OR
    (mount_parent_id IS NOT NULL AND mount_slot_key='main' AND size_u=0 AND hardware_profile_key='desktop-firewall-6')))
 OR (kind IN ('dose','endDevice') AND rack_id IS NULL AND room_id IS NOT NULL AND size_u IS NULL
     AND mount_parent_id IS NULL AND mount_slot_key IS NULL AND hardware_profile_key IS NULL)) IS TRUE);
ALTER TABLE inventory_device ADD CONSTRAINT inventory_hardware_profile CHECK (
 hardware_profile_key IS NULL OR
 (hardware_profile_key='shelf-2u' AND size_u=2 AND mount_parent_id IS NULL) OR
 (hardware_profile_key IN ('switch-24','patchpanel-24') AND size_u=1 AND mount_parent_id IS NULL) OR
 (hardware_profile_key='desktop-firewall-6' AND size_u=0 AND mount_parent_id IS NOT NULL));
ALTER TABLE inventory_device ADD CONSTRAINT inventory_mount_not_self CHECK (mount_parent_id IS DISTINCT FROM id);
ALTER TABLE inventory_device ADD CONSTRAINT inventory_device_scoped_rack_id UNIQUE(systemhaus_id,customer_id,rack_id,id);
ALTER TABLE inventory_device ADD CONSTRAINT inventory_mount_parent FOREIGN KEY(systemhaus_id,customer_id,rack_id,mount_parent_id)
 REFERENCES inventory_device(systemhaus_id,customer_id,rack_id,id) DEFERRABLE INITIALLY DEFERRED;
CREATE UNIQUE INDEX inventory_mount_slot ON inventory_device(systemhaus_id,customer_id,mount_parent_id,mount_slot_key)
 WHERE mount_parent_id IS NOT NULL;
CREATE FUNCTION inventory_validate_mount() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE support inventory_device%ROWTYPE;
BEGIN
 IF NEW.mount_parent_id IS NOT NULL THEN
   SELECT * INTO support FROM inventory_device WHERE id=NEW.mount_parent_id FOR UPDATE;
   IF NOT FOUND OR support.hardware_profile_key IS DISTINCT FROM 'shelf-2u' OR support.mount_parent_id IS NOT NULL
      OR support.systemhaus_id<>NEW.systemhaus_id OR support.customer_id<>NEW.customer_id OR support.rack_id<>NEW.rack_id THEN
     RAISE EXCEPTION 'Invalid mounting support' USING ERRCODE='23514', CONSTRAINT='inventory_mount_support';
   END IF;
 END IF;
 IF EXISTS(SELECT 1 FROM inventory_device d WHERE d.mount_parent_id=NEW.id AND
      (NEW.hardware_profile_key IS DISTINCT FROM 'shelf-2u' OR NEW.mount_parent_id IS NOT NULL OR
       NEW.systemhaus_id<>d.systemhaus_id OR NEW.customer_id<>d.customer_id OR NEW.rack_id<>d.rack_id)) THEN
   RAISE EXCEPTION 'Occupied mounting support cannot be changed' USING ERRCODE='23514', CONSTRAINT='inventory_mount_support';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER inventory_mount_support BEFORE INSERT OR UPDATE ON inventory_device
 FOR EACH ROW EXECUTE FUNCTION inventory_validate_mount();
