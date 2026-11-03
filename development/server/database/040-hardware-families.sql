-- K foundation only. SQL001-039 and all752 historical definitions remain immutable.
-- Connector forms classify appearance only; power links do not declare cord ends or certify electrical suitability.
ALTER TABLE hardware_group_template DROP CONSTRAINT hardware_group_template_type_check;
ALTER TABLE hardware_group_template ADD CONSTRAINT hardware_group_template_type_check CHECK(type IN ('rj45','sfp','sfp28','sfp56','qsfp','qsfpdd','power','console','idc'));
ALTER TABLE inventory_port_group DROP CONSTRAINT inventory_port_group_type_check;
ALTER TABLE inventory_port_group ADD CONSTRAINT inventory_port_group_type_check CHECK(type IN ('rj45','sfp','sfp28','sfp56','qsfp','qsfpdd','mgmt','console','idc','power','usb_a','usb_c'));
ALTER TABLE inventory_port DROP CONSTRAINT inventory_port_type_check;
ALTER TABLE inventory_port ADD CONSTRAINT inventory_port_type_check CHECK(type IN ('rj45','rj45_poe','sfp','sfp28','sfp56','qsfp','qsfpdd','mgmt','console','idc','power','usb_a','usb_c'));

-- Widen the existing palette predicate without changing any stored palette/receipt.
CREATE OR REPLACE FUNCTION rackclick_user_port_colors_valid(value jsonb) RETURNS boolean
LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$
    SELECT CASE WHEN jsonb_typeof(value)='object' THEN NOT EXISTS (
        SELECT 1 FROM jsonb_each(value) AS item(key,color)
        WHERE key NOT IN ('rj45','rj45_poe','sfp','sfp28','sfp56','qsfp','qsfpdd','mgmt','console','idc','power','usb_a','usb_c')
           OR jsonb_typeof(color)<>'string' OR (color #>> '{}') !~ '^#[0-9a-f]{6}$'
    ) ELSE false END
$$;

CREATE TABLE hardware_connector_template (
 profile_key text COLLATE "C" NOT NULL, revision text COLLATE "C" NOT NULL, group_key text COLLATE "C" NOT NULL,
 physical_connector text COLLATE "C" NOT NULL,
 PRIMARY KEY(profile_key,revision,group_key),
 FOREIGN KEY(profile_key,revision,group_key) REFERENCES hardware_group_template(profile_key,revision,group_key)
);
COMMENT ON COLUMN hardware_connector_template.physical_connector IS 'Physical form classification only. Cord ends, voltage, current and pinout are unspecified.';
CREATE FUNCTION hardware_validate_connector() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE raw_type text; valid boolean;
BEGIN
 SELECT type INTO raw_type FROM hardware_group_template WHERE profile_key=NEW.profile_key AND revision=NEW.revision AND group_key=NEW.group_key;
 valid := CASE raw_type
   WHEN 'power' THEN NEW.physical_connector IN ('iec-c13','iec-c14','iec-c19','iec-c20','nema-5-15p','nema-5-15r','nema-5-20p','nema-5-20r','nema-l5-30p','nema-l5-30r','nema-l6-20p','nema-l6-20r','nema-l6-30p','nema-l6-30r','iec60309-16a-2p-e-plug','iec60309-16a-2p-e-connector','iec60309-32a-2p-e-plug')
   WHEN 'console' THEN NEW.physical_connector IN ('serial-8p8c','serial-10p10c','serial-de9','serial-rj12')
   WHEN 'idc' THEN NEW.physical_connector IN ('idc-110','idc-dual-110-krone')
   ELSE false END;
 IF valid IS DISTINCT FROM true THEN
   RAISE EXCEPTION 'Invalid physical form classification' USING ERRCODE='23514', CONSTRAINT='hardware_connector_type';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER hardware_connector_validate BEFORE INSERT OR UPDATE ON hardware_connector_template FOR EACH ROW EXECUTE FUNCTION hardware_validate_connector();
CREATE TRIGGER hardware_connector_immutable BEFORE INSERT OR UPDATE OR DELETE ON hardware_connector_template FOR EACH ROW EXECUTE FUNCTION hardware_catalog_immutable();
CREATE TRIGGER hardware_connector_no_truncate BEFORE TRUNCATE ON hardware_connector_template FOR EACH STATEMENT EXECUTE FUNCTION hardware_catalog_immutable();
REVOKE ALL ON hardware_connector_template FROM PUBLIC;

CREATE OR REPLACE FUNCTION hardware_validate_component() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE parent_kind text; front hardware_group_template%ROWTYPE; rear hardware_group_template%ROWTYPE;
BEGIN
 IF TG_TABLE_NAME='hardware_mount_slot' THEN
   SELECT mount_kind INTO parent_kind FROM hardware_definition WHERE profile_key=NEW.profile_key AND revision=NEW.revision;
   IF parent_kind IS DISTINCT FROM 'shelf' THEN
     RAISE EXCEPTION 'Invalid catalog slot' USING ERRCODE='23514', CONSTRAINT='hardware_slot_kind';
   END IF;
 ELSE
   SELECT * INTO front FROM hardware_group_template WHERE profile_key=NEW.profile_key AND revision=NEW.revision AND group_key=NEW.front_group_key;
   SELECT * INTO rear FROM hardware_group_template WHERE profile_key=NEW.profile_key AND revision=NEW.revision AND group_key=NEW.rear_group_key;
   IF front.face IS DISTINCT FROM 'front' OR rear.face IS DISTINCT FROM 'rear' OR (front.type IS DISTINCT FROM rear.type AND NOT (front.type='rj45' AND rear.type='idc'))
      OR front.port_count IS DISTINCT FROM NEW.port_count OR rear.port_count IS DISTINCT FROM NEW.port_count THEN
     RAISE EXCEPTION 'Invalid catalog continuity' USING ERRCODE='23514', CONSTRAINT='hardware_passthrough_groups';
   END IF;
 END IF;
 RETURN NEW;
END $$;
