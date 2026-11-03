-- Seven declared physical media. No seeds or writes to definitions/inventory.
-- SQL001-035 remain unchanged; old values stay valid under the wider constraints.
ALTER TABLE hardware_group_template DROP CONSTRAINT hardware_group_template_type_check;
ALTER TABLE hardware_group_template ADD CONSTRAINT hardware_group_template_type_check CHECK(type IN ('rj45','sfp','sfp28','sfp56','qsfp','qsfpdd','power'));
ALTER TABLE inventory_port_group DROP CONSTRAINT inventory_port_group_type_check;
ALTER TABLE inventory_port_group ADD CONSTRAINT inventory_port_group_type_check CHECK(type IN ('rj45','sfp','sfp28','sfp56','qsfp','qsfpdd','mgmt','console','power','usb_a','usb_c'));
ALTER TABLE inventory_port DROP CONSTRAINT inventory_port_type_check;
ALTER TABLE inventory_port ADD CONSTRAINT inventory_port_type_check CHECK(type IN ('rj45','rj45_poe','sfp','sfp28','sfp56','qsfp','qsfpdd','mgmt','console','power','usb_a','usb_c'));

-- Widen the existing palette predicate without changing any stored palette/receipt.
CREATE OR REPLACE FUNCTION rackclick_user_port_colors_valid(value jsonb) RETURNS boolean
LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$
    SELECT CASE WHEN jsonb_typeof(value)='object' THEN NOT EXISTS (
        SELECT 1 FROM jsonb_each(value) AS item(key,color)
        WHERE key NOT IN ('rj45','rj45_poe','sfp','sfp28','sfp56','qsfp','qsfpdd','mgmt','console','power','usb_a','usb_c')
           OR jsonb_typeof(color)<>'string' OR (color #>> '{}') !~ '^#[0-9a-f]{6}$'
    ) ELSE false END
$$;
