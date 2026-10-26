-- Additive inventory migration. Never rewrite the received foundation migration.
CREATE TABLE inventory_site (
 id uuid PRIMARY KEY, systemhaus_id uuid NOT NULL, customer_id uuid NOT NULL,
 name text NOT NULL CHECK(length(btrim(name)) BETWEEN 1 AND 100), properties jsonb NOT NULL DEFAULT '{}' CHECK(jsonb_typeof(properties)='object'),
 UNIQUE(systemhaus_id,customer_id,id), FOREIGN KEY(systemhaus_id,customer_id) REFERENCES customer(systemhaus_id,id)
);
CREATE TABLE inventory_building (
 id uuid PRIMARY KEY, systemhaus_id uuid NOT NULL, customer_id uuid NOT NULL, site_id uuid NOT NULL,
 name text NOT NULL CHECK(length(btrim(name)) BETWEEN 1 AND 100), properties jsonb NOT NULL DEFAULT '{}' CHECK(jsonb_typeof(properties)='object'),
 UNIQUE(systemhaus_id,customer_id,id), FOREIGN KEY(systemhaus_id,customer_id,site_id) REFERENCES inventory_site(systemhaus_id,customer_id,id)
);
CREATE TABLE inventory_room (
 id uuid PRIMARY KEY, systemhaus_id uuid NOT NULL, customer_id uuid NOT NULL, building_id uuid NOT NULL,
 name text NOT NULL CHECK(length(btrim(name)) BETWEEN 1 AND 100), properties jsonb NOT NULL DEFAULT '{}' CHECK(jsonb_typeof(properties)='object'),
 UNIQUE(systemhaus_id,customer_id,id), FOREIGN KEY(systemhaus_id,customer_id,building_id) REFERENCES inventory_building(systemhaus_id,customer_id,id)
);
CREATE TABLE inventory_rack (
 id uuid PRIMARY KEY, systemhaus_id uuid NOT NULL, customer_id uuid NOT NULL, room_id uuid,
 name text NOT NULL CHECK(length(btrim(name)) BETWEEN 1 AND 100), location text NOT NULL DEFAULT '', size_u integer NOT NULL CHECK(size_u BETWEEN 1 AND 1000),
 properties jsonb NOT NULL DEFAULT '{}' CHECK(jsonb_typeof(properties)='object'),
 UNIQUE(systemhaus_id,customer_id,id), FOREIGN KEY(systemhaus_id,customer_id) REFERENCES customer(systemhaus_id,id),
 FOREIGN KEY(systemhaus_id,customer_id,room_id) REFERENCES inventory_room(systemhaus_id,customer_id,id)
);
CREATE TABLE inventory_device (
 id uuid PRIMARY KEY, systemhaus_id uuid NOT NULL, customer_id uuid NOT NULL,
 kind text NOT NULL CHECK(kind IN ('rackEquipment','dose','endDevice')), rack_id uuid, room_id uuid,
 name text NOT NULL CHECK(length(btrim(name)) BETWEEN 1 AND 100), size_u integer, sort_order integer NOT NULL CHECK(sort_order>=0),
 poe_budget numeric CHECK(poe_budget>=0 AND poe_budget<1000000), properties jsonb NOT NULL DEFAULT '{}' CHECK(jsonb_typeof(properties)='object'),
 CHECK((kind='rackEquipment' AND rack_id IS NOT NULL AND room_id IS NULL AND size_u IS NOT NULL AND size_u BETWEEN 1 AND 1000)
    OR (kind IN ('dose','endDevice') AND rack_id IS NULL AND room_id IS NOT NULL AND size_u IS NULL)),
 UNIQUE(systemhaus_id,customer_id,id), UNIQUE(systemhaus_id,customer_id,rack_id,sort_order) DEFERRABLE INITIALLY DEFERRED,
 FOREIGN KEY(systemhaus_id,customer_id,rack_id) REFERENCES inventory_rack(systemhaus_id,customer_id,id),
 FOREIGN KEY(systemhaus_id,customer_id,room_id) REFERENCES inventory_room(systemhaus_id,customer_id,id)
);
CREATE TABLE inventory_port_group (
 id uuid PRIMARY KEY, systemhaus_id uuid NOT NULL, customer_id uuid NOT NULL, device_id uuid NOT NULL,
 type text NOT NULL CHECK(type IN ('rj45','sfp','sfp28','qsfp','mgmt','console','power','usb_a','usb_c')),
 name text NOT NULL DEFAULT '', prefix text NOT NULL DEFAULT '', sort_order integer NOT NULL CHECK(sort_order>=0),
 UNIQUE(systemhaus_id,customer_id,device_id,id), UNIQUE(systemhaus_id,customer_id,device_id,id,type), UNIQUE(systemhaus_id,customer_id,id),
 FOREIGN KEY(systemhaus_id,customer_id,device_id) REFERENCES inventory_device(systemhaus_id,customer_id,id)
);
CREATE TABLE inventory_port (
 id uuid PRIMARY KEY, systemhaus_id uuid NOT NULL, customer_id uuid NOT NULL, device_id uuid NOT NULL, group_id uuid NOT NULL,
 type text NOT NULL CHECK(type IN ('rj45','rj45_poe','sfp','sfp28','qsfp','mgmt','console','power','usb_a','usb_c')),
 connector_family text GENERATED ALWAYS AS (CASE WHEN type='rj45_poe' THEN 'rj45' ELSE type END) STORED,
 gn integer NOT NULL CHECK(gn>0), sort_order integer NOT NULL CHECK(sort_order>=0), label text NOT NULL DEFAULT '',
 status text NOT NULL DEFAULT 'free' CHECK(status IN ('free','reserved','disabled','faulty')),
 poe boolean NOT NULL DEFAULT false, watts numeric CHECK(watts BETWEEN 0 AND 90), color text,
 face text NOT NULL DEFAULT 'auto' CHECK(face IN ('auto','front','rear')),
 power_role text NOT NULL DEFAULT 'unspecified' CHECK(power_role IN ('unspecified','inlet','outlet')),
 properties jsonb NOT NULL DEFAULT '{}' CHECK(jsonb_typeof(properties)='object'),
 CHECK(NOT poe OR type IN ('rj45','rj45_poe')),
 CHECK(type='power' OR power_role='unspecified'),
 UNIQUE(systemhaus_id,customer_id,id),
 FOREIGN KEY(systemhaus_id,customer_id,device_id,group_id,connector_family)
 REFERENCES inventory_port_group(systemhaus_id,customer_id,device_id,id,type) DEFERRABLE INITIALLY DEFERRED
);
CREATE TABLE inventory_connection (
 id uuid PRIMARY KEY, systemhaus_id uuid NOT NULL, customer_id uuid NOT NULL,
 note text NOT NULL DEFAULT '', color text, patch text NOT NULL DEFAULT 'none' CHECK(patch IN ('none','planned','progress','done','tested')),
 properties jsonb NOT NULL DEFAULT '{}' CHECK(jsonb_typeof(properties)='object'), created_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE(systemhaus_id,customer_id,id), FOREIGN KEY(systemhaus_id,customer_id) REFERENCES customer(systemhaus_id,id)
);
CREATE TABLE inventory_connection_endpoint (
 systemhaus_id uuid NOT NULL, customer_id uuid NOT NULL, connection_id uuid NOT NULL, ordinal smallint NOT NULL CHECK(ordinal IN (0,1)), port_id uuid NOT NULL,
 PRIMARY KEY(systemhaus_id,customer_id,connection_id,ordinal), UNIQUE(systemhaus_id,customer_id,port_id),
 FOREIGN KEY(systemhaus_id,customer_id,connection_id) REFERENCES inventory_connection(systemhaus_id,customer_id,id) ON DELETE CASCADE,
 FOREIGN KEY(systemhaus_id,customer_id,port_id) REFERENCES inventory_port(systemhaus_id,customer_id,id)
);
CREATE FUNCTION inventory_check_two_endpoints() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE target uuid;
BEGIN
 target := CASE WHEN TG_OP='DELETE' THEN OLD.connection_id ELSE NEW.connection_id END;
 IF EXISTS(SELECT 1 FROM inventory_connection WHERE id=target) AND
    (SELECT count(*) FROM inventory_connection_endpoint WHERE connection_id=target)<>2 THEN
   RAISE EXCEPTION 'Connection requires exactly two endpoints' USING ERRCODE='23514';
 END IF;
 IF TG_OP='UPDATE' AND OLD.connection_id<>NEW.connection_id AND
    EXISTS(SELECT 1 FROM inventory_connection WHERE id=OLD.connection_id) AND
    (SELECT count(*) FROM inventory_connection_endpoint WHERE connection_id=OLD.connection_id)<>2 THEN
   RAISE EXCEPTION 'Connection requires exactly two endpoints' USING ERRCODE='23514';
 END IF;
 RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER inventory_endpoint_pair AFTER INSERT OR UPDATE OR DELETE ON inventory_connection_endpoint
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION inventory_check_two_endpoints();
CREATE FUNCTION inventory_check_new_connection() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF EXISTS(SELECT 1 FROM inventory_connection WHERE id=NEW.id) AND
    (SELECT count(*) FROM inventory_connection_endpoint WHERE connection_id=NEW.id)<>2 THEN
   RAISE EXCEPTION 'Connection requires exactly two endpoints' USING ERRCODE='23514';
 END IF;
 RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER inventory_new_connection_pair AFTER INSERT ON inventory_connection
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION inventory_check_new_connection();
CREATE INDEX inventory_device_rack ON inventory_device(systemhaus_id,customer_id,rack_id,sort_order);
CREATE INDEX inventory_port_owner ON inventory_port(systemhaus_id,customer_id,device_id,group_id,sort_order);
CREATE INDEX inventory_endpoint_connection ON inventory_connection_endpoint(connection_id);
-- Upgrade the full foundation administrator grant bundle, never all users or a role label.
INSERT INTO permission_grant(id,systemhaus_id,user_group_id,capability)
 SELECT gen_random_uuid(),systemhaus_id,user_group_id,'inventory.delete'
 FROM permission_grant WHERE customer_id IS NULL AND customer_group_id IS NULL
   AND capability IN ('systemhaus.read','systemhaus.manage','customer.create','customer.manage','inventory.read','inventory.edit','security.manage')
 GROUP BY systemhaus_id,user_group_id HAVING count(DISTINCT capability)=7
 AND NOT EXISTS(SELECT 1 FROM permission_grant existing WHERE existing.systemhaus_id=permission_grant.systemhaus_id
   AND existing.user_group_id=permission_grant.user_group_id AND existing.capability='inventory.delete'
   AND existing.customer_id IS NULL AND existing.customer_group_id IS NULL);
