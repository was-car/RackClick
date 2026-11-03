-- Additive German repeaters45; historical SQL001..044 remains unchanged.
-- tabletop is room equipment, never a rack shelf or floor container.
ALTER TABLE hardware_definition DROP CONSTRAINT hardware_definition_mount_kind_check;
ALTER TABLE hardware_definition ADD CONSTRAINT hardware_definition_mount_kind_check CHECK(mount_kind IN ('rack','desktop','shelf','rackContainer','vertical0U','sharedU','wall','pole','din','floor','tabletop'));
CREATE OR REPLACE FUNCTION hardware_validate_connector() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE raw_type text; valid boolean; BEGIN
SELECT type INTO raw_type FROM hardware_group_template WHERE profile_key=NEW.profile_key AND revision=NEW.revision AND group_key=NEW.group_key;
valid := CASE raw_type
WHEN 'power' THEN NEW.physical_connector IN ('iec-c13','iec-c14','iec-c19','iec-c20','nema-5-15p','nema-5-15r','nema-5-20p','nema-5-20r','nema-l5-30p','nema-l5-30r','nema-l6-20p','nema-l6-20r','nema-l6-30p','nema-l6-30r','iec60309-16a-2p-e-plug','iec60309-16a-2p-e-connector','iec60309-32a-2p-e-plug','schuko-f','eu-2pin-plug')
WHEN 'console' THEN NEW.physical_connector IN ('serial-8p8c','serial-10p10c','serial-de9','serial-rj12','serial-mini-din8','serial-usb-c','serial-mini-usb','serial-micro-usb')
WHEN 'idc' THEN NEW.physical_connector IN ('idc-110','idc-dual-110-krone')
WHEN 'ipc' THEN NEW.physical_connector IN ('belden-revconnect-core')
WHEN 'fiber' THEN NEW.physical_connector IN ('lc-duplex-upc','lc-simplex-upc','sc-duplex-upc','sc-simplex-upc','sc-simplex-apc')
WHEN 'sfpdd' THEN NEW.physical_connector IN ('sfp-dd')
WHEN 'cfp2' THEN NEW.physical_connector IN ('cfp2')
WHEN 'sas' THEN NEW.physical_connector IN ('sff-8644','sff-8088')
WHEN 'dsl' THEN NEW.physical_connector IN ('dsl-8p8c','dsl-rj11')
WHEN 'telephony' THEN NEW.physical_connector IN ('voice-8p8c','voice-rj11','voice-tae')
WHEN 'isdn' THEN NEW.physical_connector IN ('isdn-8p8c')
WHEN 'expansion' THEN NEW.physical_connector IN ('avaya-ipoffice-expansion-8p8c')
WHEN 'power_dc' THEN NEW.physical_connector IN ('dc-barrel','unifi-smartpower','usb-c-pd','dc-terminal-2p','dc-terminal-3p','dc-terminal-6p')
ELSE false END; IF valid IS DISTINCT FROM true THEN RAISE EXCEPTION 'Invalid physical classification' USING ERRCODE='23514', CONSTRAINT='hardware_connector_type'; END IF; RETURN NEW; END $$;
CREATE OR REPLACE FUNCTION inventory_validate_mount() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE d hardware_definition%ROWTYPE; support inventory_device%ROWTYPE; bay hardware_mount_slot%ROWTYPE; m jsonb; parent_keys jsonb; capacity integer;
BEGIN
 IF TG_OP='UPDATE' AND (OLD.hardware_profile_key IS NOT NULL OR NEW.hardware_profile_key IS NOT NULL) AND (OLD.hardware_profile_key IS DISTINCT FROM NEW.hardware_profile_key OR OLD.properties->>'hardwareProfileVersion' IS DISTINCT FROM NEW.properties->>'hardwareProfileVersion') THEN RAISE EXCEPTION 'Hardware identity immutable' USING ERRCODE='23514'; END IF;
 IF NEW.hardware_profile_key IS NULL THEN
  IF NEW.mount_parent_id IS NOT NULL OR NEW.mount_slot_key IS NOT NULL THEN RAISE EXCEPTION 'Unbound mount' USING ERRCODE='23514'; END IF;
 ELSE
  SELECT * INTO d FROM hardware_definition WHERE profile_key=NEW.hardware_profile_key AND revision=NEW.properties->>'hardwareProfileVersion' AND sealed;
  IF NOT FOUND OR d.mount_kind='rackContainer' THEN RAISE EXCEPTION 'Invalid device definition' USING ERRCODE='23514'; END IF;
  IF d.mount_kind IN ('wall','pole','din','floor','tabletop') THEN
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

-- Auto-generated L. SQL001..041 and historical sealed revisions are unchanged.
-- Fixed population and connector classification are not protocol, circuit or fit simulation.
INSERT INTO hardware_definition (profile_key, revision, mount_kind, rack_units, width_mm, height_mm, depth_mm, color, definition_sha256, manufacturer, family, model, sku, provenance_kind, source_reference, sealed) VALUES (E'devolo-wifi6-repeater3000-eu', E'german-repeaters-20261103-v1', E'wall', 0, NULL, NULL, NULL, E'#f5f4f1', E'f1ffaab496fd743471b5f1ff2862beb0bb148f9bf9a2a272f4cc28394950f553', E'devolo', E'WiFi repeater EU', E'WiFi 6 Repeater 3000', E'WiFi 6 Repeater 3000 (EU)', E'manufacturer-specification', E'https://www.devolo.de/media/c7/b7/f0/1753865610/Datasheet_devolo_WiFi_6_Repeater_3000_EN_DE_FR_NL.pdf?ts=1753865610', false);
INSERT INTO hardware_group_template (profile_key, revision, group_key, sort_order, type, port_count, face, name, prefix, power_role) VALUES (E'devolo-wifi6-repeater3000-eu', E'german-repeaters-20261103-v1', E'lan', 0, E'rj45', 1, E'rear', E'LAN · 1 GbE', E'LAN ', E'unspecified');
INSERT INTO hardware_group_template (profile_key, revision, group_key, sort_order, type, port_count, face, name, prefix, power_role) VALUES (E'devolo-wifi6-repeater3000-eu', E'german-repeaters-20261103-v1', E'ac-plug', 1, E'power', 1, E'rear', E'EU plug · 2 pins', E'POWER ', E'inlet');
INSERT INTO hardware_profile_extension (profile_key, revision, metadata) VALUES (E'devolo-wifi6-repeater3000-eu', E'german-repeaters-20261103-v1', E'{"configuration":[{"description":"Unidad y alimentaci\\u00f3n nominal del modelo; sin montaje de rack ni adaptadores impl\\u00edcitos.","partNumber":"WiFi 6 Repeater 3000 (EU)","quantity":1,"slot":"base"}],"continuities":[],"mounting":{"kind":"wall","target":"room"}}
');
INSERT INTO hardware_group_extension (profile_key, revision, group_key, metadata) VALUES (E'devolo-wifi6-repeater3000-eu', E'german-repeaters-20261103-v1', E'lan', E'{"interfaceRole":"ethernet"}
');
INSERT INTO hardware_connector_template (profile_key, revision, group_key, physical_connector) VALUES (E'devolo-wifi6-repeater3000-eu', E'german-repeaters-20261103-v1', E'ac-plug', E'eu-2pin-plug');
UPDATE hardware_definition SET sealed=true WHERE profile_key=E'devolo-wifi6-repeater3000-eu' AND revision=E'german-repeaters-20261103-v1';
INSERT INTO hardware_definition (profile_key, revision, mount_kind, rack_units, width_mm, height_mm, depth_mm, color, definition_sha256, manufacturer, family, model, sku, provenance_kind, source_reference, sealed) VALUES (E'devolo-wifi6-repeater5400-eu', E'german-repeaters-20261103-v1', E'tabletop', 0, NULL, NULL, NULL, E'#f5f4f1', E'cbc4d4989a6597b247139a9936c9a54940be3fc665aa72efcd365673de9381b4', E'devolo', E'WiFi repeater EU', E'WiFi 6 Repeater 5400', E'WiFi 6 Repeater 5400 (EU)', E'manufacturer-specification', E'https://www.devolo.de/media/c7/e2/16/1753865618/Datasheet_devolo_WiFi_6_Repeater_5400_EN_DE_FR_NL.pdf?ts=1753865618', false);
INSERT INTO hardware_group_template (profile_key, revision, group_key, sort_order, type, port_count, face, name, prefix, power_role) VALUES (E'devolo-wifi6-repeater5400-eu', E'german-repeaters-20261103-v1', E'lan', 0, E'rj45', 2, E'rear', E'LAN · 1 GbE', E'LAN ', E'unspecified');
INSERT INTO hardware_group_template (profile_key, revision, group_key, sort_order, type, port_count, face, name, prefix, power_role) VALUES (E'devolo-wifi6-repeater5400-eu', E'german-repeaters-20261103-v1', E'dc', 1, E'power_dc', 1, E'rear', E'DC input · external PSU', E'DC ', E'inlet');
INSERT INTO hardware_profile_extension (profile_key, revision, metadata) VALUES (E'devolo-wifi6-repeater5400-eu', E'german-repeaters-20261103-v1', E'{"configuration":[{"description":"Unidad y alimentaci\\u00f3n nominal del modelo; sin montaje de rack ni adaptadores impl\\u00edcitos.","partNumber":"WiFi 6 Repeater 5400 (EU)","quantity":1,"slot":"base"}],"continuities":[],"mounting":{"kind":"tabletop","target":"room"}}
');
INSERT INTO hardware_group_extension (profile_key, revision, group_key, metadata) VALUES (E'devolo-wifi6-repeater5400-eu', E'german-repeaters-20261103-v1', E'lan', E'{"interfaceRole":"ethernet"}
');
INSERT INTO hardware_connector_template (profile_key, revision, group_key, physical_connector) VALUES (E'devolo-wifi6-repeater5400-eu', E'german-repeaters-20261103-v1', E'dc', E'dc-barrel');
INSERT INTO hardware_group_extension (profile_key, revision, group_key, metadata) VALUES (E'devolo-wifi6-repeater5400-eu', E'german-repeaters-20261103-v1', E'dc', E'{"powerSystem":"dc"}
');
UPDATE hardware_definition SET sealed=true WHERE profile_key=E'devolo-wifi6-repeater5400-eu' AND revision=E'german-repeaters-20261103-v1';
INSERT INTO hardware_definition (profile_key, revision, mount_kind, rack_units, width_mm, height_mm, depth_mm, color, definition_sha256, manufacturer, family, model, sku, provenance_kind, source_reference, sealed) VALUES (E'fritz-repeater1200ax-de', E'german-repeaters-20261103-v1', E'wall', 0, 80, 80, 37, E'#f5f4f1', E'621d82b81dd999e99c1974dfbd4646c7636e8a15f192ade6f429842c0d5b05a0', E'FRITZ!', E'FRITZ!Repeater', E'FRITZ!Repeater 1200 AX', E'20002974', E'manufacturer-specification', E'https://fritz.com/products/fritz-repeater-1200-ax-20002974/', false);
INSERT INTO hardware_group_template (profile_key, revision, group_key, sort_order, type, port_count, face, name, prefix, power_role) VALUES (E'fritz-repeater1200ax-de', E'german-repeaters-20261103-v1', E'lan', 0, E'rj45', 1, E'rear', E'LAN · 1 GbE', E'LAN ', E'unspecified');
INSERT INTO hardware_group_template (profile_key, revision, group_key, sort_order, type, port_count, face, name, prefix, power_role) VALUES (E'fritz-repeater1200ax-de', E'german-repeaters-20261103-v1', E'ac-plug', 1, E'power', 1, E'rear', E'EU plug · 2 pins', E'POWER ', E'inlet');
INSERT INTO hardware_profile_extension (profile_key, revision, metadata) VALUES (E'fritz-repeater1200ax-de', E'german-repeaters-20261103-v1', E'{"configuration":[{"description":"Unidad y alimentaci\\u00f3n nominal del modelo; sin montaje de rack ni adaptadores impl\\u00edcitos.","partNumber":"20002974","quantity":1,"slot":"base"}],"continuities":[],"mounting":{"kind":"wall","target":"room"}}
');
INSERT INTO hardware_group_extension (profile_key, revision, group_key, metadata) VALUES (E'fritz-repeater1200ax-de', E'german-repeaters-20261103-v1', E'lan', E'{"interfaceRole":"ethernet"}
');
INSERT INTO hardware_connector_template (profile_key, revision, group_key, physical_connector) VALUES (E'fritz-repeater1200ax-de', E'german-repeaters-20261103-v1', E'ac-plug', E'eu-2pin-plug');
UPDATE hardware_definition SET sealed=true WHERE profile_key=E'fritz-repeater1200ax-de' AND revision=E'german-repeaters-20261103-v1';
INSERT INTO hardware_definition (profile_key, revision, mount_kind, rack_units, width_mm, height_mm, depth_mm, color, definition_sha256, manufacturer, family, model, sku, provenance_kind, source_reference, sealed) VALUES (E'fritz-repeater2400-de', E'german-repeaters-20261103-v1', E'wall', 0, 76.5, 155, 62.6, E'#f5f4f1', E'0bb4132d04d1bd224bb1b1d045f6122f211627fe870c9b3ce2fdbd781f71cbd9', E'FRITZ!', E'FRITZ!Repeater', E'FRITZ!Repeater 2400', E'20002855', E'manufacturer-specification', E'https://fritz.com/products/fritz-repeater-2400-20002855/', false);
INSERT INTO hardware_group_template (profile_key, revision, group_key, sort_order, type, port_count, face, name, prefix, power_role) VALUES (E'fritz-repeater2400-de', E'german-repeaters-20261103-v1', E'lan', 0, E'rj45', 1, E'rear', E'LAN · 1 GbE', E'LAN ', E'unspecified');
INSERT INTO hardware_group_template (profile_key, revision, group_key, sort_order, type, port_count, face, name, prefix, power_role) VALUES (E'fritz-repeater2400-de', E'german-repeaters-20261103-v1', E'ac-plug', 1, E'power', 1, E'rear', E'EU plug · 2 pins', E'POWER ', E'inlet');
INSERT INTO hardware_profile_extension (profile_key, revision, metadata) VALUES (E'fritz-repeater2400-de', E'german-repeaters-20261103-v1', E'{"configuration":[{"description":"Unidad y alimentaci\\u00f3n nominal del modelo; sin montaje de rack ni adaptadores impl\\u00edcitos.","partNumber":"20002855","quantity":1,"slot":"base"}],"continuities":[],"mounting":{"kind":"wall","target":"room"}}
');
INSERT INTO hardware_group_extension (profile_key, revision, group_key, metadata) VALUES (E'fritz-repeater2400-de', E'german-repeaters-20261103-v1', E'lan', E'{"interfaceRole":"ethernet"}
');
INSERT INTO hardware_connector_template (profile_key, revision, group_key, physical_connector) VALUES (E'fritz-repeater2400-de', E'german-repeaters-20261103-v1', E'ac-plug', E'eu-2pin-plug');
UPDATE hardware_definition SET sealed=true WHERE profile_key=E'fritz-repeater2400-de' AND revision=E'german-repeaters-20261103-v1';
INSERT INTO hardware_definition (profile_key, revision, mount_kind, rack_units, width_mm, height_mm, depth_mm, color, definition_sha256, manufacturer, family, model, sku, provenance_kind, source_reference, sealed) VALUES (E'fritz-repeater3000ax-de', E'german-repeaters-20261103-v1', E'tabletop', 0, 90, 190, 145, E'#f5f4f1', E'8773d9b1fab35d7e59e5bc30b5123c69e7fa596bd158aba5274f88126bf5ed3c', E'FRITZ!', E'FRITZ!Repeater', E'FRITZ!Repeater 3000 AX', E'20002988', E'manufacturer-specification', E'https://fritz.com/products/fritz-repeater-3000-ax-20002988/', false);
INSERT INTO hardware_group_template (profile_key, revision, group_key, sort_order, type, port_count, face, name, prefix, power_role) VALUES (E'fritz-repeater3000ax-de', E'german-repeaters-20261103-v1', E'lan', 0, E'rj45', 2, E'rear', E'LAN · 1 GbE', E'LAN ', E'unspecified');
INSERT INTO hardware_group_template (profile_key, revision, group_key, sort_order, type, port_count, face, name, prefix, power_role) VALUES (E'fritz-repeater3000ax-de', E'german-repeaters-20261103-v1', E'dc', 1, E'power_dc', 1, E'rear', E'DC input · external PSU', E'DC ', E'inlet');
INSERT INTO hardware_profile_extension (profile_key, revision, metadata) VALUES (E'fritz-repeater3000ax-de', E'german-repeaters-20261103-v1', E'{"configuration":[{"description":"Unidad y alimentaci\\u00f3n nominal del modelo; sin montaje de rack ni adaptadores impl\\u00edcitos.","partNumber":"20002988","quantity":1,"slot":"base"}],"continuities":[],"mounting":{"kind":"tabletop","target":"room"}}
');
INSERT INTO hardware_group_extension (profile_key, revision, group_key, metadata) VALUES (E'fritz-repeater3000ax-de', E'german-repeaters-20261103-v1', E'lan', E'{"interfaceRole":"ethernet"}
');
INSERT INTO hardware_connector_template (profile_key, revision, group_key, physical_connector) VALUES (E'fritz-repeater3000ax-de', E'german-repeaters-20261103-v1', E'dc', E'dc-barrel');
INSERT INTO hardware_group_extension (profile_key, revision, group_key, metadata) VALUES (E'fritz-repeater3000ax-de', E'german-repeaters-20261103-v1', E'dc', E'{"powerSystem":"dc"}
');
UPDATE hardware_definition SET sealed=true WHERE profile_key=E'fritz-repeater3000ax-de' AND revision=E'german-repeaters-20261103-v1';
INSERT INTO hardware_definition (profile_key, revision, mount_kind, rack_units, width_mm, height_mm, depth_mm, color, definition_sha256, manufacturer, family, model, sku, provenance_kind, source_reference, sealed) VALUES (E'fritz-repeater600-de', E'german-repeaters-20261103-v1', E'wall', 0, 63, 63, 30, E'#f5f4f1', E'fb410380fc41883b2cfc13ad3a606580481ad86daa4fd10ced58d391a9ad9555', E'FRITZ!', E'FRITZ!Repeater', E'FRITZ!Repeater 600', E'20002853', E'manufacturer-specification', E'https://fritz.com/products/fritz-repeater-600-20002853/', false);
INSERT INTO hardware_group_template (profile_key, revision, group_key, sort_order, type, port_count, face, name, prefix, power_role) VALUES (E'fritz-repeater600-de', E'german-repeaters-20261103-v1', E'ac-plug', 0, E'power', 1, E'rear', E'EU plug · 2 pins', E'POWER ', E'inlet');
INSERT INTO hardware_profile_extension (profile_key, revision, metadata) VALUES (E'fritz-repeater600-de', E'german-repeaters-20261103-v1', E'{"configuration":[{"description":"Unidad y alimentaci\\u00f3n nominal del modelo; sin montaje de rack ni adaptadores impl\\u00edcitos.","partNumber":"20002853","quantity":1,"slot":"base"}],"continuities":[],"mounting":{"kind":"wall","target":"room"}}
');
INSERT INTO hardware_connector_template (profile_key, revision, group_key, physical_connector) VALUES (E'fritz-repeater600-de', E'german-repeaters-20261103-v1', E'ac-plug', E'eu-2pin-plug');
UPDATE hardware_definition SET sealed=true WHERE profile_key=E'fritz-repeater600-de' AND revision=E'german-repeaters-20261103-v1';
INSERT INTO hardware_definition (profile_key, revision, mount_kind, rack_units, width_mm, height_mm, depth_mm, color, definition_sha256, manufacturer, family, model, sku, provenance_kind, source_reference, sealed) VALUES (E'fritz-repeater6000-de', E'german-repeaters-20261103-v1', E'tabletop', 0, 87, 185, 135, E'#f5f4f1', E'3e114eca7ab0d5c2cc5e16dc93141779c4a155962449ee8f5f47f7c92fd5db09', E'FRITZ!', E'FRITZ!Repeater', E'FRITZ!Repeater 6000', E'20002908', E'manufacturer-specification', E'https://fritz.com/products/fritz-repeater-6000-20002908/', false);
INSERT INTO hardware_group_template (profile_key, revision, group_key, sort_order, type, port_count, face, name, prefix, power_role) VALUES (E'fritz-repeater6000-de', E'german-repeaters-20261103-v1', E'lan25', 0, E'rj45', 1, E'rear', E'LAN 1 · 2.5 GbE', E'LAN 1 · 2.5 GbE ', E'unspecified');
INSERT INTO hardware_group_template (profile_key, revision, group_key, sort_order, type, port_count, face, name, prefix, power_role) VALUES (E'fritz-repeater6000-de', E'german-repeaters-20261103-v1', E'lan1', 1, E'rj45', 1, E'rear', E'LAN 2 · 1 GbE', E'LAN 2 · 1 GbE ', E'unspecified');
INSERT INTO hardware_group_template (profile_key, revision, group_key, sort_order, type, port_count, face, name, prefix, power_role) VALUES (E'fritz-repeater6000-de', E'german-repeaters-20261103-v1', E'dc', 2, E'power_dc', 1, E'rear', E'DC input · external PSU', E'DC ', E'inlet');
INSERT INTO hardware_profile_extension (profile_key, revision, metadata) VALUES (E'fritz-repeater6000-de', E'german-repeaters-20261103-v1', E'{"configuration":[{"description":"Unidad y alimentaci\\u00f3n nominal del modelo; sin montaje de rack ni adaptadores impl\\u00edcitos.","partNumber":"20002908","quantity":1,"slot":"base"}],"continuities":[],"mounting":{"kind":"tabletop","target":"room"}}
');
INSERT INTO hardware_group_extension (profile_key, revision, group_key, metadata) VALUES (E'fritz-repeater6000-de', E'german-repeaters-20261103-v1', E'lan25', E'{"interfaceRole":"ethernet"}
');
INSERT INTO hardware_group_extension (profile_key, revision, group_key, metadata) VALUES (E'fritz-repeater6000-de', E'german-repeaters-20261103-v1', E'lan1', E'{"interfaceRole":"ethernet"}
');
INSERT INTO hardware_connector_template (profile_key, revision, group_key, physical_connector) VALUES (E'fritz-repeater6000-de', E'german-repeaters-20261103-v1', E'dc', E'dc-barrel');
INSERT INTO hardware_group_extension (profile_key, revision, group_key, metadata) VALUES (E'fritz-repeater6000-de', E'german-repeaters-20261103-v1', E'dc', E'{"powerSystem":"dc"}
');
UPDATE hardware_definition SET sealed=true WHERE profile_key=E'fritz-repeater6000-de' AND revision=E'german-repeaters-20261103-v1';
INSERT INTO hardware_definition (profile_key, revision, mount_kind, rack_units, width_mm, height_mm, depth_mm, color, definition_sha256, manufacturer, family, model, sku, provenance_kind, source_reference, sealed) VALUES (E'telekom-speedhome-wlan-2021', E'german-repeaters-20261103-v1', E'tabletop', 0, 157, 157, 69, E'#25282b', E'3b6da79afda92e318c3fe4798964d14960712cff2621f1dd86aed5790f6f2491', E'Telekom', E'Speed Home WLAN original', E'Speed Home WLAN (2021)', E'40823475', E'manufacturer-specification', E'https://www.telekom.com/resource/blob/627822/c83408f468252af4369eea285310d15a/dl-produktsteckbrief-speed-home-data.pdf', false);
INSERT INTO hardware_group_template (profile_key, revision, group_key, sort_order, type, port_count, face, name, prefix, power_role) VALUES (E'telekom-speedhome-wlan-2021', E'german-repeaters-20261103-v1', E'lan', 0, E'rj45', 2, E'rear', E'LAN · 1 GbE', E'LAN ', E'unspecified');
INSERT INTO hardware_group_template (profile_key, revision, group_key, sort_order, type, port_count, face, name, prefix, power_role) VALUES (E'telekom-speedhome-wlan-2021', E'german-repeaters-20261103-v1', E'dc', 1, E'power_dc', 1, E'rear', E'DC input · external PSU', E'DC ', E'inlet');
INSERT INTO hardware_profile_extension (profile_key, revision, metadata) VALUES (E'telekom-speedhome-wlan-2021', E'german-repeaters-20261103-v1', E'{"configuration":[{"description":"Unidad y alimentaci\\u00f3n nominal del modelo; sin montaje de rack ni adaptadores impl\\u00edcitos.","partNumber":"40823475","quantity":1,"slot":"base"}],"continuities":[],"mounting":{"kind":"tabletop","target":"room"}}
');
INSERT INTO hardware_group_extension (profile_key, revision, group_key, metadata) VALUES (E'telekom-speedhome-wlan-2021', E'german-repeaters-20261103-v1', E'lan', E'{"interfaceRole":"ethernet"}
');
INSERT INTO hardware_connector_template (profile_key, revision, group_key, physical_connector) VALUES (E'telekom-speedhome-wlan-2021', E'german-repeaters-20261103-v1', E'dc', E'dc-barrel');
INSERT INTO hardware_group_extension (profile_key, revision, group_key, metadata) VALUES (E'telekom-speedhome-wlan-2021', E'german-repeaters-20261103-v1', E'dc', E'{"powerSystem":"dc"}
');
UPDATE hardware_definition SET sealed=true WHERE profile_key=E'telekom-speedhome-wlan-2021' AND revision=E'german-repeaters-20261103-v1';
INSERT INTO hardware_definition (profile_key, revision, mount_kind, rack_units, width_mm, height_mm, depth_mm, color, definition_sha256, manufacturer, family, model, sku, provenance_kind, source_reference, sealed) VALUES (E'tplink-re605x-eu', E'german-repeaters-20261103-v1', E'wall', 0, 74, 124.8, 46, E'#f5f4f1', E'820c053ec6a906dd9eba8133a602432da739c49147183b7ecd3d69aaeab426a5', E'TP-Link', E'WiFi repeater EU', E'RE605X EU', E'RE605X(EU)', E'manufacturer-specification', E'https://www.tp-link.com/de/home-networking/range-extender/re605x/#specifications', false);
INSERT INTO hardware_group_template (profile_key, revision, group_key, sort_order, type, port_count, face, name, prefix, power_role) VALUES (E'tplink-re605x-eu', E'german-repeaters-20261103-v1', E'lan', 0, E'rj45', 1, E'rear', E'LAN · 1 GbE', E'LAN ', E'unspecified');
INSERT INTO hardware_group_template (profile_key, revision, group_key, sort_order, type, port_count, face, name, prefix, power_role) VALUES (E'tplink-re605x-eu', E'german-repeaters-20261103-v1', E'ac-plug', 1, E'power', 1, E'rear', E'EU plug · 2 pins', E'POWER ', E'inlet');
INSERT INTO hardware_profile_extension (profile_key, revision, metadata) VALUES (E'tplink-re605x-eu', E'german-repeaters-20261103-v1', E'{"configuration":[{"description":"Unidad y alimentaci\\u00f3n nominal del modelo; sin montaje de rack ni adaptadores impl\\u00edcitos.","partNumber":"RE605X(EU)","quantity":1,"slot":"base"}],"continuities":[],"mounting":{"kind":"wall","target":"room"}}
');
INSERT INTO hardware_group_extension (profile_key, revision, group_key, metadata) VALUES (E'tplink-re605x-eu', E'german-repeaters-20261103-v1', E'lan', E'{"interfaceRole":"ethernet"}
');
INSERT INTO hardware_connector_template (profile_key, revision, group_key, physical_connector) VALUES (E'tplink-re605x-eu', E'german-repeaters-20261103-v1', E'ac-plug', E'eu-2pin-plug');
UPDATE hardware_definition SET sealed=true WHERE profile_key=E'tplink-re605x-eu' AND revision=E'german-repeaters-20261103-v1';
INSERT INTO hardware_definition (profile_key, revision, mount_kind, rack_units, width_mm, height_mm, depth_mm, color, definition_sha256, manufacturer, family, model, sku, provenance_kind, source_reference, sealed) VALUES (E'tplink-re700x-eu', E'german-repeaters-20261103-v1', E'wall', 0, 78, 149, 36, E'#f5f4f1', E'f2c4d6fc2d345deabad24a6507bdaf38d150232830f42d261501e840b19c4fa2', E'TP-Link', E'WiFi repeater EU', E'RE700X EU', E'RE700X(EU)', E'manufacturer-specification', E'https://www.tp-link.com/de/home-networking/range-extender/re700x/#specifications', false);
INSERT INTO hardware_group_template (profile_key, revision, group_key, sort_order, type, port_count, face, name, prefix, power_role) VALUES (E'tplink-re700x-eu', E'german-repeaters-20261103-v1', E'lan', 0, E'rj45', 1, E'rear', E'LAN · 1 GbE', E'LAN ', E'unspecified');
INSERT INTO hardware_group_template (profile_key, revision, group_key, sort_order, type, port_count, face, name, prefix, power_role) VALUES (E'tplink-re700x-eu', E'german-repeaters-20261103-v1', E'ac-plug', 1, E'power', 1, E'rear', E'EU plug · 2 pins', E'POWER ', E'inlet');
INSERT INTO hardware_profile_extension (profile_key, revision, metadata) VALUES (E'tplink-re700x-eu', E'german-repeaters-20261103-v1', E'{"configuration":[{"description":"Unidad y alimentaci\\u00f3n nominal del modelo; sin montaje de rack ni adaptadores impl\\u00edcitos.","partNumber":"RE700X(EU)","quantity":1,"slot":"base"}],"continuities":[],"mounting":{"kind":"wall","target":"room"}}
');
INSERT INTO hardware_group_extension (profile_key, revision, group_key, metadata) VALUES (E'tplink-re700x-eu', E'german-repeaters-20261103-v1', E'lan', E'{"interfaceRole":"ethernet"}
');
INSERT INTO hardware_connector_template (profile_key, revision, group_key, physical_connector) VALUES (E'tplink-re700x-eu', E'german-repeaters-20261103-v1', E'ac-plug', E'eu-2pin-plug');
UPDATE hardware_definition SET sealed=true WHERE profile_key=E'tplink-re700x-eu' AND revision=E'german-repeaters-20261103-v1';
