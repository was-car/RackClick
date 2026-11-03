-- L foundation only. Historical SQL001-041 and805 definitions are preserved.
ALTER TABLE hardware_group_template DROP CONSTRAINT hardware_group_template_type_check;
ALTER TABLE hardware_group_template ADD CONSTRAINT hardware_group_template_type_check CHECK(type IN ('rj45','sfp','sfp28','sfp56','qsfp','qsfpdd','power','console','idc','ipc','fiber','sfpdd','cfp2','sas','dsl','telephony','isdn','expansion','power_dc'));
ALTER TABLE inventory_port_group DROP CONSTRAINT inventory_port_group_type_check;
ALTER TABLE inventory_port_group ADD CONSTRAINT inventory_port_group_type_check CHECK(type IN ('rj45','sfp','sfp28','sfp56','qsfp','qsfpdd','mgmt','console','idc','power','usb_a','usb_c','ipc','fiber','sfpdd','cfp2','sas','dsl','telephony','isdn','expansion','power_dc'));
ALTER TABLE inventory_port DROP CONSTRAINT inventory_port_type_check;
ALTER TABLE inventory_port ADD CONSTRAINT inventory_port_type_check CHECK(type IN ('rj45','rj45_poe','sfp','sfp28','sfp56','qsfp','qsfpdd','mgmt','console','idc','power','usb_a','usb_c','ipc','fiber','sfpdd','cfp2','sas','dsl','telephony','isdn','expansion','power_dc'));
ALTER TABLE hardware_definition DROP CONSTRAINT hardware_definition_mount_kind_check;
ALTER TABLE hardware_definition ADD CONSTRAINT hardware_definition_mount_kind_check CHECK(mount_kind IN ('rack','desktop','shelf','rackContainer','vertical0U','sharedU','wall','pole','din','floor'));
ALTER TABLE hardware_definition DROP CONSTRAINT hardware_definition_check;
ALTER TABLE hardware_definition ADD CONSTRAINT hardware_definition_check CHECK ((mount_kind IN ('rack','shelf') AND rack_units>0) OR (mount_kind NOT IN ('rack','shelf') AND rack_units=0));
ALTER TABLE hardware_definition ALTER COLUMN width_mm DROP NOT NULL, ALTER COLUMN height_mm DROP NOT NULL, ALTER COLUMN depth_mm DROP NOT NULL;
ALTER TABLE hardware_group_template DROP CONSTRAINT hardware_group_template_port_count_check;
ALTER TABLE hardware_group_template ADD CONSTRAINT hardware_group_template_port_count_check CHECK(port_count BETWEEN 1 AND 512);
ALTER TABLE hardware_group_template DROP CONSTRAINT hardware_group_power_role;
ALTER TABLE hardware_group_template ADD CONSTRAINT hardware_group_power_role CHECK(type IN ('power','power_dc') OR power_role='unspecified');
-- inventory_port_check is the original PoE guard and must remain unchanged.
-- Only inventory_port_check1 restricts power_role to the old AC type.
ALTER TABLE inventory_port DROP CONSTRAINT inventory_port_check1;
ALTER TABLE inventory_port ADD CONSTRAINT inventory_port_check1 CHECK(type IN ('power','power_dc') OR power_role='unspecified');
CREATE TABLE hardware_profile_extension (profile_key text COLLATE "C" NOT NULL, revision text COLLATE "C" NOT NULL, metadata jsonb NOT NULL CHECK(jsonb_typeof(metadata)='object'), PRIMARY KEY(profile_key,revision), FOREIGN KEY(profile_key,revision) REFERENCES hardware_definition(profile_key,revision));
CREATE TRIGGER hardware_profile_extension_immutable BEFORE INSERT OR UPDATE OR DELETE ON hardware_profile_extension FOR EACH ROW EXECUTE FUNCTION hardware_catalog_immutable();
CREATE TRIGGER hardware_profile_extension_no_truncate BEFORE TRUNCATE ON hardware_profile_extension FOR EACH STATEMENT EXECUTE FUNCTION hardware_catalog_immutable();
REVOKE ALL ON hardware_profile_extension FROM PUBLIC;
CREATE TABLE hardware_group_extension (profile_key text COLLATE "C" NOT NULL, revision text COLLATE "C" NOT NULL, group_key text COLLATE "C" NOT NULL, metadata jsonb NOT NULL CHECK(jsonb_typeof(metadata)='object'), PRIMARY KEY(profile_key,revision,group_key), FOREIGN KEY(profile_key,revision,group_key) REFERENCES hardware_group_template(profile_key,revision,group_key));
CREATE TRIGGER hardware_group_extension_immutable BEFORE INSERT OR UPDATE OR DELETE ON hardware_group_extension FOR EACH ROW EXECUTE FUNCTION hardware_catalog_immutable();
CREATE TRIGGER hardware_group_extension_no_truncate BEFORE TRUNCATE ON hardware_group_extension FOR EACH STATEMENT EXECUTE FUNCTION hardware_catalog_immutable();
REVOKE ALL ON hardware_group_extension FROM PUBLIC;
CREATE OR REPLACE FUNCTION hardware_validate_connector() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE raw_type text; valid boolean; BEGIN
SELECT type INTO raw_type FROM hardware_group_template WHERE profile_key=NEW.profile_key AND revision=NEW.revision AND group_key=NEW.group_key;
valid := CASE raw_type
WHEN 'power' THEN NEW.physical_connector IN ('iec-c13','iec-c14','iec-c19','iec-c20','nema-5-15p','nema-5-15r','nema-5-20p','nema-5-20r','nema-l5-30p','nema-l5-30r','nema-l6-20p','nema-l6-20r','nema-l6-30p','nema-l6-30r','iec60309-16a-2p-e-plug','iec60309-16a-2p-e-connector','iec60309-32a-2p-e-plug','schuko-f')
WHEN 'console' THEN NEW.physical_connector IN ('serial-8p8c','serial-10p10c','serial-de9','serial-rj12','serial-mini-din8','serial-usb-c','serial-mini-usb','serial-micro-usb')
WHEN 'idc' THEN NEW.physical_connector IN ('idc-110','idc-dual-110-krone')
WHEN 'ipc' THEN NEW.physical_connector IN ('belden-revconnect-core')
WHEN 'fiber' THEN NEW.physical_connector IN ('lc-duplex-upc','lc-simplex-upc','sc-duplex-upc','sc-simplex-upc','sc-simplex-apc')
WHEN 'sfpdd' THEN NEW.physical_connector IN ('sfp-dd')
WHEN 'cfp2' THEN NEW.physical_connector IN ('cfp2')
WHEN 'sas' THEN NEW.physical_connector IN ('sff-8644','sff-8088')
WHEN 'dsl' THEN NEW.physical_connector IN ('dsl-8p8c','dsl-rj11')
WHEN 'telephony' THEN NEW.physical_connector IN ('voice-8p8c','voice-rj11')
WHEN 'isdn' THEN NEW.physical_connector IN ('isdn-8p8c')
WHEN 'expansion' THEN NEW.physical_connector IN ('avaya-ipoffice-expansion-8p8c')
WHEN 'power_dc' THEN NEW.physical_connector IN ('dc-barrel','unifi-smartpower','usb-c-pd','dc-terminal-2p','dc-terminal-3p','dc-terminal-6p')
ELSE false END; IF valid IS DISTINCT FROM true THEN RAISE EXCEPTION 'Invalid physical classification' USING ERRCODE='23514', CONSTRAINT='hardware_connector_type'; END IF; RETURN NEW; END $$;
CREATE OR REPLACE FUNCTION rackclick_user_port_colors_valid(value jsonb) RETURNS boolean
LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$
    SELECT CASE WHEN jsonb_typeof(value)='object' THEN NOT EXISTS (
        SELECT 1 FROM jsonb_each(value) AS item(key,color)
        WHERE key NOT IN ('rj45','rj45_poe','sfp','sfp28','sfp56','qsfp','qsfpdd','mgmt','console','idc','power','usb_a','usb_c','ipc','fiber','sfpdd','cfp2','sas','dsl','telephony','isdn','expansion','power_dc')
           OR jsonb_typeof(color)<>'string' OR (color #>> '{}') !~ '^#[0-9a-f]{6}$'
    ) ELSE false END
$$;



CREATE FUNCTION hardware_validate_l_extension() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE k text; v jsonb; d hardware_definition%ROWTYPE; g hardware_group_template%ROWTYPE; a hardware_group_template%ROWTYPE; b hardware_group_template%ROWTYPE; item jsonb; m jsonb;
BEGIN
 IF TG_TABLE_NAME='hardware_group_extension' THEN
  SELECT * INTO g FROM hardware_group_template WHERE profile_key=NEW.profile_key AND revision=NEW.revision AND group_key=NEW.group_key;
  IF NEW.metadata='{}'::jsonb THEN RAISE EXCEPTION 'Empty extension' USING ERRCODE='23514'; END IF;
  FOR k,v IN SELECT * FROM jsonb_each(NEW.metadata) LOOP
   IF jsonb_typeof(v)<>'string' OR NOT (CASE k
WHEN 'physicalFace' THEN (v#>>'{}') IN ('front','rear','top','bottom')
WHEN 'interfaceRole' THEN (v#>>'{}') IN ('ethernet','storage','cluster','ha','management','optical-line','optical-client','serial','proprietary','voice','dsl')
WHEN 'signalRole' THEN (v#>>'{}') IN ('tx','rx','bidi','passive')
WHEN 'powerSystem' THEN (v#>>'{}') IN ('dc','usb-pd','unifi-smartpower')
ELSE false END) THEN RAISE EXCEPTION 'Invalid group extension' USING ERRCODE='23514', CONSTRAINT='hardware_group_extension_invalid'; END IF;
  END LOOP;
  IF NEW.metadata ? 'powerSystem' AND g.type<>'power_dc' THEN RAISE EXCEPTION 'Power system on data port' USING ERRCODE='23514'; END IF;
 ELSE
  SELECT * INTO d FROM hardware_definition WHERE profile_key=NEW.profile_key AND revision=NEW.revision;
  IF NOT (NEW.metadata ?& ARRAY['mounting','configuration','continuities']) OR EXISTS(SELECT 1 FROM jsonb_object_keys(NEW.metadata) AS keys(key) WHERE keys.key NOT IN ('mounting','configuration','continuities'))
   OR jsonb_typeof(NEW.metadata->'mounting')<>'object' OR jsonb_typeof(NEW.metadata->'configuration')<>'array' OR jsonb_typeof(NEW.metadata->'continuities')<>'array' THEN
   RAISE EXCEPTION 'Invalid profile extension' USING ERRCODE='23514'; END IF;
  m=NEW.metadata->'mounting';
  IF m->>'kind' IS DISTINCT FROM d.mount_kind OR m->>'target' IS DISTINCT FROM (CASE WHEN d.mount_kind IN ('desktop','sharedU') THEN 'parent' WHEN d.mount_kind IN ('rack','shelf','vertical0U') THEN 'rack' ELSE 'room' END) THEN
   RAISE EXCEPTION 'Invalid mounting contract' USING ERRCODE='23514'; END IF;
  IF EXISTS(SELECT 1 FROM jsonb_object_keys(m) AS keys(key) WHERE keys.key NOT IN ('kind','target','capacityU','parentProfileKeys')) THEN RAISE EXCEPTION 'Unknown mounting field' USING ERRCODE='23514'; END IF;
  IF d.mount_kind='rackContainer' AND (COALESCE(m->>'capacityU','') !~ '^[1-9][0-9]{0,3}$' OR (m->>'capacityU')::integer>1000) THEN RAISE EXCEPTION 'Invalid rack capacity' USING ERRCODE='23514'; END IF;
  IF m ? 'parentProfileKeys' AND (jsonb_typeof(m->'parentProfileKeys')<>'array' OR EXISTS(SELECT 1 FROM jsonb_array_elements(m->'parentProfileKeys')x WHERE jsonb_typeof(x)<>'string')) THEN RAISE EXCEPTION 'Invalid parent keys' USING ERRCODE='23514'; END IF;
  FOR item IN SELECT * FROM jsonb_array_elements(NEW.metadata->'configuration') LOOP
   IF jsonb_typeof(item)<>'object' OR NOT item ?& ARRAY['slot','partNumber','quantity','description'] OR EXISTS(SELECT 1 FROM jsonb_object_keys(item) AS keys(key) WHERE keys.key NOT IN ('slot','partNumber','quantity','description')) OR
    jsonb_typeof(item->'slot')<>'string' OR jsonb_typeof(item->'partNumber')<>'string' OR jsonb_typeof(item->'description')<>'string' OR jsonb_typeof(item->'quantity')<>'number' OR (item->>'quantity') !~ '^[1-9][0-9]{0,3}$' THEN RAISE EXCEPTION 'Invalid fixed BOM' USING ERRCODE='23514'; END IF;
  END LOOP;
  FOR item IN SELECT * FROM jsonb_array_elements(NEW.metadata->'continuities') LOOP
   SELECT * INTO a FROM hardware_group_template WHERE profile_key=NEW.profile_key AND revision=NEW.revision AND group_key=item->>'fromGroup';
   SELECT * INTO b FROM hardware_group_template WHERE profile_key=NEW.profile_key AND revision=NEW.revision AND group_key=item->>'toGroup';
   IF jsonb_typeof(item)<>'object' OR NOT item ?& ARRAY['fromGroup','toGroup','count','mapping','tracingAvailable'] OR EXISTS(SELECT 1 FROM jsonb_object_keys(item) AS keys(key) WHERE keys.key NOT IN ('fromGroup','toGroup','count','mapping','tracingAvailable')) OR
    item->>'mapping' IS DISTINCT FROM 'one-to-one' OR item->'tracingAvailable' IS DISTINCT FROM 'false'::jsonb OR a.group_key IS NULL OR b.group_key IS NULL OR a.group_key=b.group_key OR
    jsonb_typeof(item->'count')<>'number' OR (item->>'count') !~ '^[1-9][0-9]{0,2}$' OR a.port_count IS DISTINCT FROM (item->>'count')::integer OR b.port_count IS DISTINCT FROM (item->>'count')::integer OR
    NOT (a.type=b.type OR (a.type='rj45' AND b.type IN ('idc','ipc'))) THEN RAISE EXCEPTION 'Invalid declared continuity' USING ERRCODE='23514', CONSTRAINT='hardware_continuity_invalid'; END IF;
  END LOOP;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER hardware_profile_extension_validate BEFORE INSERT OR UPDATE ON hardware_profile_extension FOR EACH ROW EXECUTE FUNCTION hardware_validate_l_extension();
CREATE TRIGGER hardware_group_extension_validate BEFORE INSERT OR UPDATE ON hardware_group_extension FOR EACH ROW EXECUTE FUNCTION hardware_validate_l_extension();
CREATE FUNCTION hardware_validate_l_seal() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NOT OLD.sealed AND NEW.sealed THEN
  IF NEW.mount_kind NOT IN ('rack','desktop','shelf') AND NOT EXISTS(SELECT 1 FROM hardware_profile_extension WHERE profile_key=NEW.profile_key AND revision=NEW.revision) THEN RAISE EXCEPTION 'Missing mounting extension' USING ERRCODE='23514'; END IF;
  IF NEW.mount_kind IN ('desktop','shelf') AND (NEW.width_mm IS NULL OR NEW.height_mm IS NULL OR NEW.depth_mm IS NULL) THEN RAISE EXCEPTION 'Unknown fit dimensions' USING ERRCODE='23514'; END IF;
  IF EXISTS(SELECT 1 FROM hardware_group_template g LEFT JOIN hardware_group_extension e USING(profile_key,revision,group_key) WHERE g.profile_key=NEW.profile_key AND g.revision=NEW.revision AND g.type='power_dc' AND (g.power_role NOT IN ('inlet','outlet') OR e.metadata->>'powerSystem' IS NULL)) THEN RAISE EXCEPTION 'Missing DC system/role' USING ERRCODE='23514'; END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER hardware_l_seal BEFORE UPDATE ON hardware_definition FOR EACH ROW EXECUTE FUNCTION hardware_validate_l_seal();
ALTER TABLE inventory_rack ADD COLUMN hardware_profile_key text COLLATE "C";
ALTER TABLE inventory_rack ADD COLUMN hardware_profile_revision text COLLATE "C" GENERATED ALWAYS AS (CASE WHEN hardware_profile_key IS NOT NULL THEN properties->>'hardwareProfileVersion' END) STORED;
ALTER TABLE inventory_rack ADD CONSTRAINT inventory_rack_hardware_revision CHECK ((hardware_profile_key IS NULL)=(hardware_profile_revision IS NULL));
ALTER TABLE inventory_rack ADD CONSTRAINT inventory_rack_hardware_definition FOREIGN KEY(hardware_profile_key,hardware_profile_revision) REFERENCES hardware_definition(profile_key,revision);
CREATE FUNCTION inventory_validate_l_rack() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE d hardware_definition%ROWTYPE; m jsonb; BEGIN
 IF TG_OP='UPDATE' AND (OLD.hardware_profile_key IS NOT NULL OR NEW.hardware_profile_key IS NOT NULL) AND (OLD.hardware_profile_key IS DISTINCT FROM NEW.hardware_profile_key OR OLD.properties->>'hardwareProfileVersion' IS DISTINCT FROM NEW.properties->>'hardwareProfileVersion') THEN RAISE EXCEPTION 'Rack identity immutable' USING ERRCODE='23514'; END IF;
 IF NEW.hardware_profile_key IS NOT NULL THEN
  SELECT * INTO d FROM hardware_definition WHERE profile_key=NEW.hardware_profile_key AND revision=NEW.properties->>'hardwareProfileVersion' AND sealed;
  SELECT metadata->'mounting' INTO m FROM hardware_profile_extension WHERE profile_key=d.profile_key AND revision=d.revision;
  IF d.mount_kind IS DISTINCT FROM 'rackContainer' OR NEW.size_u IS DISTINCT FROM (m->>'capacityU')::integer THEN RAISE EXCEPTION 'Invalid rack container' USING ERRCODE='23514'; END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER inventory_l_rack_validate BEFORE INSERT OR UPDATE ON inventory_rack FOR EACH ROW EXECUTE FUNCTION inventory_validate_l_rack();
ALTER TABLE inventory_device DROP CONSTRAINT inventory_device_placement;
ALTER TABLE inventory_device ADD CONSTRAINT inventory_device_placement CHECK ((
 (kind='rackEquipment' AND rack_id IS NOT NULL AND room_id IS NULL AND size_u IS NOT NULL AND (size_u BETWEEN 1 AND 1000 OR (size_u=0 AND hardware_profile_key IS NOT NULL))) OR
 (kind IN ('dose','endDevice') AND rack_id IS NULL AND room_id IS NOT NULL AND size_u IS NULL AND mount_parent_id IS NULL AND mount_slot_key IS NULL)) IS TRUE);
CREATE UNIQUE INDEX inventory_vertical_side ON inventory_device(systemhaus_id,customer_id,rack_id,mount_slot_key) WHERE mount_parent_id IS NULL AND mount_slot_key IN ('vertical-left','vertical-right');
CREATE OR REPLACE FUNCTION inventory_validate_mount() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE d hardware_definition%ROWTYPE; support inventory_device%ROWTYPE; bay hardware_mount_slot%ROWTYPE; m jsonb; parent_keys jsonb; capacity integer;
BEGIN
 IF TG_OP='UPDATE' AND (OLD.hardware_profile_key IS NOT NULL OR NEW.hardware_profile_key IS NOT NULL) AND (OLD.hardware_profile_key IS DISTINCT FROM NEW.hardware_profile_key OR OLD.properties->>'hardwareProfileVersion' IS DISTINCT FROM NEW.properties->>'hardwareProfileVersion') THEN RAISE EXCEPTION 'Hardware identity immutable' USING ERRCODE='23514'; END IF;
 IF NEW.hardware_profile_key IS NULL THEN
  IF NEW.mount_parent_id IS NOT NULL OR NEW.mount_slot_key IS NOT NULL THEN RAISE EXCEPTION 'Unbound mount' USING ERRCODE='23514'; END IF;
 ELSE
  SELECT * INTO d FROM hardware_definition WHERE profile_key=NEW.hardware_profile_key AND revision=NEW.properties->>'hardwareProfileVersion' AND sealed;
  IF NOT FOUND OR d.mount_kind='rackContainer' THEN RAISE EXCEPTION 'Invalid device definition' USING ERRCODE='23514'; END IF;
  IF d.mount_kind IN ('wall','pole','din','floor') THEN
   IF NEW.kind<>'endDevice' OR NEW.room_id IS NULL OR NEW.rack_id IS NOT NULL OR NEW.size_u IS NOT NULL OR NEW.mount_parent_id IS NOT NULL OR NEW.mount_slot_key IS NOT NULL THEN RAISE EXCEPTION 'Invalid room hardware' USING ERRCODE='23514'; END IF;
  ELSE
   IF NEW.kind<>'rackEquipment' OR NEW.rack_id IS NULL OR NEW.room_id IS NOT NULL OR NEW.size_u IS DISTINCT FROM d.rack_units THEN RAISE EXCEPTION 'Invalid rack hardware' USING ERRCODE='23514'; END IF;
   IF d.mount_kind IN ('desktop','sharedU') THEN
    SELECT * INTO support FROM inventory_device WHERE id=NEW.mount_parent_id FOR UPDATE;
    IF NOT FOUND OR support.mount_parent_id IS NOT NULL OR support.size_u<=0 OR support.systemhaus_id<>NEW.systemhaus_id OR support.customer_id<>NEW.customer_id OR support.rack_id<>NEW.rack_id THEN RAISE EXCEPTION 'Invalid parent' USING ERRCODE='23514'; END IF;
    IF d.mount_kind='desktop' THEN
     SELECT * INTO bay FROM hardware_mount_slot WHERE profile_key=support.hardware_profile_key AND revision=support.properties->>'hardwareProfileVersion' AND slot_key=NEW.mount_slot_key;
     IF NOT FOUND OR d.width_mm IS NULL OR d.height_mm IS NULL OR d.depth_mm IS NULL OR d.width_mm>bay.width_mm OR d.height_mm>bay.height_mm OR d.depth_mm>bay.depth_mm THEN RAISE EXCEPTION 'Invalid fit' USING ERRCODE='23514'; END IF;
    ELSE
     IF NEW.mount_slot_key IS DISTINCT FROM 'shared' THEN RAISE EXCEPTION 'Invalid shared slot' USING ERRCODE='23514'; END IF;
     SELECT metadata->'mounting'->'parentProfileKeys' INTO parent_keys FROM hardware_profile_extension WHERE profile_key=d.profile_key AND revision=d.revision;
     IF parent_keys IS NOT NULL AND jsonb_array_length(parent_keys)>0 AND NOT parent_keys ? COALESCE(support.hardware_profile_key,'') THEN RAISE EXCEPTION 'Parent profile incompatible' USING ERRCODE='23514'; END IF;
    END IF;
   ELSIF d.mount_kind='vertical0U' THEN
    SELECT size_u INTO capacity FROM inventory_rack WHERE id=NEW.rack_id;
    IF NEW.mount_parent_id IS NOT NULL OR NEW.mount_slot_key NOT IN ('vertical-left','vertical-right') OR NEW.mount_slot_key IS NULL OR d.height_mm IS NULL OR d.height_mm>capacity*44.45 THEN RAISE EXCEPTION 'Invalid vertical position' USING ERRCODE='23514'; END IF;
   ELSIF NEW.mount_parent_id IS NOT NULL OR NEW.mount_slot_key IS NOT NULL THEN RAISE EXCEPTION 'Unsupported mount' USING ERRCODE='23514'; END IF;
  END IF;
 END IF;
 IF EXISTS(SELECT 1 FROM inventory_device child JOIN hardware_definition cd ON cd.profile_key=child.hardware_profile_key AND cd.revision=child.hardware_profile_revision LEFT JOIN hardware_mount_slot cb ON cb.profile_key=NEW.hardware_profile_key AND cb.revision=NEW.properties->>'hardwareProfileVersion' AND cb.slot_key=child.mount_slot_key WHERE child.mount_parent_id=NEW.id AND
  (NEW.mount_parent_id IS NOT NULL OR NEW.rack_id IS DISTINCT FROM child.rack_id OR NEW.systemhaus_id<>child.systemhaus_id OR NEW.customer_id<>child.customer_id OR NEW.size_u<=0 OR
   (cd.mount_kind='desktop' AND (cb.slot_key IS NULL OR cd.width_mm IS NULL OR cd.height_mm IS NULL OR cd.depth_mm IS NULL OR cd.width_mm>cb.width_mm OR cd.height_mm>cb.height_mm OR cd.depth_mm>cb.depth_mm)))) THEN RAISE EXCEPTION 'Occupied support cannot change' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $$;
