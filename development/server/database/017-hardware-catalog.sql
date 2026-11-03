-- Normalized immutable definitions. The four seeds were emitted once from the
-- reviewed catalog-source-v1.json; never regenerate an applied migration.
CREATE TABLE hardware_definition (
 profile_key text COLLATE "C" NOT NULL CHECK(profile_key ~ '^[a-z0-9][a-z0-9-]{0,127}$'),
 revision text COLLATE "C" NOT NULL CHECK(revision ~ '^[a-z0-9][a-z0-9-]{0,127}$'),
 mount_kind text NOT NULL CHECK(mount_kind IN ('shelf','rack','desktop')),
 rack_units integer NOT NULL CHECK(rack_units BETWEEN 0 AND 60),
 width_mm numeric NOT NULL CHECK(width_mm>0 AND width_mm<=10000),
 height_mm integer NOT NULL CHECK(height_mm BETWEEN 1 AND 10000),
 depth_mm integer NOT NULL CHECK(depth_mm BETWEEN 1 AND 10000),
 color text NOT NULL CHECK(color ~ '^#[0-9a-f]{6}$'),
 definition_sha256 text NOT NULL CHECK(definition_sha256 ~ '^[0-9a-f]{64}$'),
 manufacturer text, family text, model text, sku text,
 provenance_kind text NOT NULL, source_reference text NOT NULL, sealed boolean NOT NULL DEFAULT false,
 PRIMARY KEY(profile_key,revision),
 CHECK((mount_kind='desktop' AND rack_units=0) OR (mount_kind<>'desktop' AND rack_units>0))
);
CREATE TABLE hardware_mount_slot (
 profile_key text COLLATE "C" NOT NULL, revision text COLLATE "C" NOT NULL,
 slot_key text COLLATE "C" NOT NULL CHECK(slot_key ~ '^[a-z0-9][a-z0-9-]{0,127}$'),
 width_mm numeric NOT NULL CHECK(width_mm>0 AND width_mm<=10000),
 height_mm integer NOT NULL CHECK(height_mm BETWEEN 1 AND 10000),
 depth_mm integer NOT NULL CHECK(depth_mm BETWEEN 1 AND 10000),
 PRIMARY KEY(profile_key,revision,slot_key),
 FOREIGN KEY(profile_key,revision) REFERENCES hardware_definition(profile_key,revision)
);
CREATE TABLE hardware_group_template (
 profile_key text COLLATE "C" NOT NULL, revision text COLLATE "C" NOT NULL,
 group_key text COLLATE "C" NOT NULL CHECK(group_key ~ '^[a-z0-9][a-z0-9-]{0,127}$'),
 sort_order integer NOT NULL CHECK(sort_order BETWEEN 0 AND 31),
 type text NOT NULL CHECK(type IN ('rj45','sfp')), port_count integer NOT NULL CHECK(port_count BETWEEN 1 AND 256),
 face text NOT NULL CHECK(face IN ('front','rear')), name text NOT NULL, prefix text NOT NULL,
 PRIMARY KEY(profile_key,revision,group_key), UNIQUE(profile_key,revision,sort_order),
 FOREIGN KEY(profile_key,revision) REFERENCES hardware_definition(profile_key,revision)
);
CREATE TABLE hardware_passthrough (
 profile_key text COLLATE "C" NOT NULL, revision text COLLATE "C" NOT NULL,
 front_group_key text COLLATE "C" NOT NULL, rear_group_key text COLLATE "C" NOT NULL,
 port_count integer NOT NULL CHECK(port_count BETWEEN 1 AND 256),
 PRIMARY KEY(profile_key,revision), CHECK(front_group_key<>rear_group_key),
 FOREIGN KEY(profile_key,revision,front_group_key) REFERENCES hardware_group_template(profile_key,revision,group_key),
 FOREIGN KEY(profile_key,revision,rear_group_key) REFERENCES hardware_group_template(profile_key,revision,group_key)
);
-- SEED-BEGIN: checked against the normalized authoring source by PG tests.
INSERT INTO hardware_definition VALUES('shelf-2u','hw-reference-v1','shelf',2,482.6,44,300,'#46505c','8e2f625187eee860ed35a17c7107c9b7b2f3d208d11a5f9890efafc4ec59629f',NULL,NULL,NULL,NULL,'own-synthetic','docs/CONTRATO-HARDWARE-MONTAJE-v1.md');
INSERT INTO hardware_mount_slot VALUES('shelf-2u','hw-reference-v1','main',440,60,300);
INSERT INTO hardware_definition VALUES('desktop-firewall-6','hw-reference-v1','desktop',0,220,38,200,'#cbd5e1','3fcdbe32d119fc4b86d8cdb1afc0c14ebe34bf8e9c33913477d2e86873091610',NULL,NULL,NULL,NULL,'own-synthetic','docs/CONTRATO-HARDWARE-MONTAJE-v1.md');
INSERT INTO hardware_group_template VALUES('desktop-firewall-6','hw-reference-v1','front-lan',0,'rj45',6,'front','LAN','LAN ');
INSERT INTO hardware_group_template VALUES('desktop-firewall-6','hw-reference-v1','rear-management',1,'rj45',1,'rear','Management','MGMT ');
INSERT INTO hardware_definition VALUES('switch-24','hw-reference-v1','rack',1,482.6,44,200,'#607d8b','b8f92a735d3630a10630d5aab0a69fe224f6200a0d4e490531ad88af4a861c1a',NULL,NULL,NULL,NULL,'own-synthetic','docs/CONTRATO-HARDWARE-MONTAJE-v1.md');
INSERT INTO hardware_group_template VALUES('switch-24','hw-reference-v1','front-lan',0,'rj45',24,'front','LAN','');
INSERT INTO hardware_group_template VALUES('switch-24','hw-reference-v1','rear-uplink',1,'sfp',2,'rear','Uplink','SFP ');
INSERT INTO hardware_definition VALUES('patchpanel-24','hw-reference-v1','rack',1,482.6,44,100,'#303640','550bc18d29d309b3aba551923bd34c3d184560646e541fb2baf150672fcc4de6',NULL,NULL,NULL,NULL,'own-synthetic','docs/CONTRATO-HARDWARE-MONTAJE-v1.md');
INSERT INTO hardware_group_template VALUES('patchpanel-24','hw-reference-v1','front-patch',0,'rj45',24,'front','Front','F ');
INSERT INTO hardware_group_template VALUES('patchpanel-24','hw-reference-v1','rear-patch',1,'rj45',24,'rear','Rear','R ');
INSERT INTO hardware_passthrough VALUES('patchpanel-24','hw-reference-v1','front-patch','rear-patch',24);
UPDATE hardware_definition SET sealed=true;
-- SEED-END

CREATE FUNCTION hardware_validate_component() RETURNS trigger LANGUAGE plpgsql AS $$
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
   IF front.face IS DISTINCT FROM 'front' OR rear.face IS DISTINCT FROM 'rear' OR front.type IS DISTINCT FROM rear.type
      OR front.port_count IS DISTINCT FROM NEW.port_count OR rear.port_count IS DISTINCT FROM NEW.port_count THEN
     RAISE EXCEPTION 'Invalid catalog continuity' USING ERRCODE='23514', CONSTRAINT='hardware_passthrough_groups';
   END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER hardware_slot_validate BEFORE INSERT ON hardware_mount_slot FOR EACH ROW EXECUTE FUNCTION hardware_validate_component();
CREATE TRIGGER hardware_passthrough_validate BEFORE INSERT ON hardware_passthrough FOR EACH ROW EXECUTE FUNCTION hardware_validate_component();

CREATE FUNCTION hardware_catalog_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE closed boolean; slot_count integer; group_count integer; port_total integer;
BEGIN
 -- Catalog authoring is migration-only. Prevent a stale repeatable-read
 -- publisher from validating components committed after its transaction snapshot.
 IF current_setting('transaction_isolation')<>'read committed' THEN
   RAISE EXCEPTION 'Catalog writes require READ COMMITTED' USING ERRCODE='25001';
 END IF;
 IF current_user<>(SELECT pg_get_userbyid(relowner) FROM pg_class WHERE oid=TG_RELID) THEN
   RAISE EXCEPTION 'Catalog insertion requires the migration owner' USING ERRCODE='42501';
 END IF;
 IF TG_TABLE_NAME='hardware_definition' THEN
   IF TG_OP='UPDATE' AND NOT OLD.sealed AND NEW.sealed AND to_jsonb(OLD)-'sealed'=to_jsonb(NEW)-'sealed' THEN
     SELECT count(*) INTO slot_count FROM hardware_mount_slot WHERE profile_key=NEW.profile_key AND revision=NEW.revision;
     SELECT count(*),COALESCE(sum(port_count),0) INTO group_count,port_total FROM hardware_group_template WHERE profile_key=NEW.profile_key AND revision=NEW.revision;
     IF (NEW.mount_kind='shelf' AND (slot_count=0 OR group_count<>0)) OR
        (NEW.mount_kind<>'shelf' AND slot_count<>0) OR group_count>32 OR port_total>1024 THEN
       RAISE EXCEPTION 'Catalog publication is incomplete' USING ERRCODE='23514', CONSTRAINT='hardware_catalog_publication';
     END IF;
     RETURN NEW;
   END IF;
 END IF;
 IF TG_OP<>'INSERT' THEN
   RAISE EXCEPTION 'Catalog revisions are immutable' USING ERRCODE='23514', CONSTRAINT='hardware_catalog_immutable';
 END IF;
 IF TG_TABLE_NAME='hardware_definition' THEN
   IF NEW.sealed THEN
     RAISE EXCEPTION 'Catalog definition must start as a draft' USING ERRCODE='23514';
   END IF;
 ELSE
   -- Both component insertion and publication lock/update the same parent. A
   -- stale repeatable-read writer cannot add children after another tx seals it.
   SELECT sealed INTO closed FROM hardware_definition WHERE profile_key=NEW.profile_key AND revision=NEW.revision FOR UPDATE;
   IF closed IS DISTINCT FROM false THEN
     RAISE EXCEPTION 'Catalog revisions are immutable' USING ERRCODE='23514', CONSTRAINT='hardware_catalog_immutable';
   END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER hardware_definition_immutable BEFORE INSERT OR UPDATE OR DELETE ON hardware_definition FOR EACH ROW EXECUTE FUNCTION hardware_catalog_immutable();
CREATE TRIGGER hardware_slot_immutable BEFORE INSERT OR UPDATE OR DELETE ON hardware_mount_slot FOR EACH ROW EXECUTE FUNCTION hardware_catalog_immutable();
CREATE TRIGGER hardware_group_immutable BEFORE INSERT OR UPDATE OR DELETE ON hardware_group_template FOR EACH ROW EXECUTE FUNCTION hardware_catalog_immutable();
CREATE TRIGGER hardware_passthrough_immutable BEFORE INSERT OR UPDATE OR DELETE ON hardware_passthrough FOR EACH ROW EXECUTE FUNCTION hardware_catalog_immutable();
CREATE TRIGGER hardware_definition_no_truncate BEFORE TRUNCATE ON hardware_definition FOR EACH STATEMENT EXECUTE FUNCTION hardware_catalog_immutable();
CREATE TRIGGER hardware_slot_no_truncate BEFORE TRUNCATE ON hardware_mount_slot FOR EACH STATEMENT EXECUTE FUNCTION hardware_catalog_immutable();
CREATE TRIGGER hardware_group_no_truncate BEFORE TRUNCATE ON hardware_group_template FOR EACH STATEMENT EXECUTE FUNCTION hardware_catalog_immutable();
CREATE TRIGGER hardware_passthrough_no_truncate BEFORE TRUNCATE ON hardware_passthrough FOR EACH STATEMENT EXECUTE FUNCTION hardware_catalog_immutable();
REVOKE ALL ON hardware_definition,hardware_mount_slot,hardware_group_template,hardware_passthrough FROM PUBLIC;

-- Keep one instance version value: derive the relational FK from protected JSON.
-- Missing/malformed/unknown historical versions fail the transaction, never become v1.
ALTER TABLE inventory_device ADD COLUMN hardware_profile_revision text COLLATE "C"
 GENERATED ALWAYS AS (CASE WHEN hardware_profile_key IS NOT NULL THEN properties->>'hardwareProfileVersion' END) STORED;
ALTER TABLE inventory_device ADD CONSTRAINT inventory_hardware_revision_required
 CHECK ((hardware_profile_key IS NULL) = (hardware_profile_revision IS NULL));
ALTER TABLE inventory_device ADD CONSTRAINT inventory_hardware_definition
 FOREIGN KEY(hardware_profile_key,hardware_profile_revision) REFERENCES hardware_definition(profile_key,revision);
ALTER TABLE inventory_device DROP CONSTRAINT inventory_hardware_profile;
ALTER TABLE inventory_device DROP CONSTRAINT inventory_device_placement;
ALTER TABLE inventory_device ADD CONSTRAINT inventory_device_placement CHECK ((
 (kind='rackEquipment' AND rack_id IS NOT NULL AND room_id IS NULL AND size_u IS NOT NULL AND
  ((mount_parent_id IS NULL AND mount_slot_key IS NULL AND size_u BETWEEN 1 AND 1000) OR
   (mount_parent_id IS NOT NULL AND mount_slot_key IS NOT NULL AND size_u=0 AND hardware_profile_key IS NOT NULL)))
 OR (kind IN ('dose','endDevice') AND rack_id IS NULL AND room_id IS NOT NULL AND size_u IS NULL
     AND mount_parent_id IS NULL AND mount_slot_key IS NULL AND hardware_profile_key IS NULL)) IS TRUE);

CREATE OR REPLACE FUNCTION inventory_validate_mount() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE definition hardware_definition%ROWTYPE; support inventory_device%ROWTYPE; slot hardware_mount_slot%ROWTYPE;
BEGIN
 IF TG_OP='UPDATE' AND (OLD.hardware_profile_key IS NOT NULL OR NEW.hardware_profile_key IS NOT NULL) AND
    (OLD.hardware_profile_key IS DISTINCT FROM NEW.hardware_profile_key OR
     OLD.properties->>'hardwareProfileVersion' IS DISTINCT FROM NEW.properties->>'hardwareProfileVersion') THEN
   RAISE EXCEPTION 'Hardware identity is immutable' USING ERRCODE='23514', CONSTRAINT='inventory_hardware_identity_immutable';
 END IF;
 IF NEW.hardware_profile_key IS NOT NULL THEN
   SELECT * INTO definition FROM hardware_definition WHERE profile_key=NEW.hardware_profile_key AND revision=NEW.properties->>'hardwareProfileVersion' AND sealed;
   IF NOT FOUND OR NEW.kind<>'rackEquipment' OR NEW.size_u IS DISTINCT FROM definition.rack_units
      OR ((definition.mount_kind='desktop') IS DISTINCT FROM (NEW.mount_parent_id IS NOT NULL)) THEN
     RAISE EXCEPTION 'Invalid hardware revision or placement' USING ERRCODE='23514', CONSTRAINT='inventory_hardware_definition';
   END IF;
 END IF;
 IF NEW.mount_parent_id IS NOT NULL THEN
   SELECT * INTO support FROM inventory_device WHERE id=NEW.mount_parent_id FOR UPDATE;
   IF NOT FOUND OR support.mount_parent_id IS NOT NULL OR support.systemhaus_id<>NEW.systemhaus_id
      OR support.customer_id<>NEW.customer_id OR support.rack_id<>NEW.rack_id THEN
     RAISE EXCEPTION 'Invalid mounting support' USING ERRCODE='23514', CONSTRAINT='inventory_mount_support';
   END IF;
   SELECT * INTO slot FROM hardware_mount_slot WHERE profile_key=support.hardware_profile_key
      AND revision=support.properties->>'hardwareProfileVersion' AND slot_key=NEW.mount_slot_key;
   IF NOT FOUND OR definition.width_mm>slot.width_mm OR definition.height_mm>slot.height_mm OR definition.depth_mm>slot.depth_mm THEN
     RAISE EXCEPTION 'Invalid mounting slot or dimensions' USING ERRCODE='23514', CONSTRAINT='inventory_mount_dimensions';
   END IF;
 END IF;
 IF EXISTS(SELECT 1 FROM inventory_device child
   LEFT JOIN hardware_definition cd ON cd.profile_key=child.hardware_profile_key AND cd.revision=child.properties->>'hardwareProfileVersion'
   LEFT JOIN hardware_mount_slot bay ON bay.profile_key=NEW.hardware_profile_key AND bay.revision=NEW.properties->>'hardwareProfileVersion' AND bay.slot_key=child.mount_slot_key
   WHERE child.mount_parent_id=NEW.id AND (NEW.mount_parent_id IS NOT NULL OR child.systemhaus_id<>NEW.systemhaus_id
     OR child.customer_id<>NEW.customer_id OR child.rack_id<>NEW.rack_id OR bay.slot_key IS NULL OR cd.profile_key IS NULL
     OR cd.width_mm>bay.width_mm OR cd.height_mm>bay.height_mm OR cd.depth_mm>bay.depth_mm)) THEN
   RAISE EXCEPTION 'Occupied mounting support cannot be changed' USING ERRCODE='23514', CONSTRAINT='inventory_mount_support';
 END IF;
 RETURN NEW;
END $$;
-- Validate existing physical placement as well as the FK, without rewriting rows
-- or producing audit/operation entries. A failure rolls back all DDL/seeds.
DO $$
BEGIN
 IF EXISTS(SELECT 1 FROM inventory_device d JOIN hardware_definition model
    ON model.profile_key=d.hardware_profile_key AND model.revision=d.hardware_profile_revision
    LEFT JOIN inventory_device parent ON parent.id=d.mount_parent_id
    LEFT JOIN hardware_mount_slot bay ON bay.profile_key=parent.hardware_profile_key
      AND bay.revision=parent.hardware_profile_revision AND bay.slot_key=d.mount_slot_key
    WHERE d.size_u<>model.rack_units OR ((model.mount_kind='desktop') IS DISTINCT FROM (d.mount_parent_id IS NOT NULL))
      OR (d.mount_parent_id IS NOT NULL AND (bay.slot_key IS NULL OR model.width_mm>bay.width_mm OR model.height_mm>bay.height_mm OR model.depth_mm>bay.depth_mm))) THEN
   RAISE EXCEPTION 'Historical hardware placement is incompatible' USING ERRCODE='23514';
 END IF;
END $$;
