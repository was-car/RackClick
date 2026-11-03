-- German CPE additive extension. Historical migrations001..043 stay unchanged.
-- USB physical type already exists for manual inventory; TAE is voice, never Ethernet.
ALTER TABLE hardware_group_template DROP CONSTRAINT hardware_group_template_type_check;
ALTER TABLE hardware_group_template ADD CONSTRAINT hardware_group_template_type_check CHECK(type IN ('rj45','sfp','sfp28','sfp56','qsfp','qsfpdd','power','console','idc','ipc','fiber','sfpdd','cfp2','sas','dsl','telephony','isdn','expansion','power_dc','usb_a','usb_c'));
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
WHEN 'telephony' THEN NEW.physical_connector IN ('voice-8p8c','voice-rj11','voice-tae')
WHEN 'isdn' THEN NEW.physical_connector IN ('isdn-8p8c')
WHEN 'expansion' THEN NEW.physical_connector IN ('avaya-ipoffice-expansion-8p8c')
WHEN 'power_dc' THEN NEW.physical_connector IN ('dc-barrel','unifi-smartpower','usb-c-pd','dc-terminal-2p','dc-terminal-3p','dc-terminal-6p')
ELSE false END; IF valid IS DISTINCT FROM true THEN RAISE EXCEPTION 'Invalid physical classification' USING ERRCODE='23514', CONSTRAINT='hardware_connector_type'; END IF; RETURN NEW; END $$;
-- Auto-generated L. SQL001..041 and historical sealed revisions are unchanged.
-- Fixed population and connector classification are not protocol, circuit or fit simulation.
INSERT INTO hardware_definition (profile_key, revision, mount_kind, rack_units, width_mm, height_mm, depth_mm, color, definition_sha256, manufacturer, family, model, sku, provenance_kind, source_reference, sealed) VALUES (E'draytek-vigor167', E'german-cpe-20261103-v1', E'desktop', 0, 181, 40, 125, E'#f2f1ef', E'06ce9c1709e1ec6f8848a1422393f364ae928562680840a167e7f017fda26e45', E'DrayTek', E'Vigor167 modem', E'Vigor167', E'Vigor167', E'manufacturer-specification', E'https://www.draytek.de/de/produkte/modem-router/vigor167/', false);
INSERT INTO hardware_group_template (profile_key, revision, group_key, sort_order, type, port_count, face, name, prefix, power_role) VALUES (E'draytek-vigor167', E'german-cpe-20261103-v1', E'dc', 0, E'power_dc', 1, E'rear', E'POWER', E'POWER ', E'inlet');
INSERT INTO hardware_group_template (profile_key, revision, group_key, sort_order, type, port_count, face, name, prefix, power_role) VALUES (E'draytek-vigor167', E'german-cpe-20261103-v1', E'lan', 1, E'rj45', 2, E'rear', E'P', E'P ', E'unspecified');
INSERT INTO hardware_group_template (profile_key, revision, group_key, sort_order, type, port_count, face, name, prefix, power_role) VALUES (E'draytek-vigor167', E'german-cpe-20261103-v1', E'dsl', 2, E'dsl', 1, E'rear', E'DSL', E'DSL ', E'unspecified');
INSERT INTO hardware_profile_extension (profile_key, revision, metadata) VALUES (E'draytek-vigor167', E'german-cpe-20261103-v1', E'{"configuration":[{"description":"Modelo/SKU expl\\u00edcito; fuente externaDC. No accesorios derack impl\\u00edcitos.","partNumber":"Vigor167","quantity":1,"slot":"base"}],"continuities":[],"mounting":{"kind":"desktop","target":"parent"}}
');
INSERT INTO hardware_connector_template (profile_key, revision, group_key, physical_connector) VALUES (E'draytek-vigor167', E'german-cpe-20261103-v1', E'dc', E'dc-barrel');
INSERT INTO hardware_group_extension (profile_key, revision, group_key, metadata) VALUES (E'draytek-vigor167', E'german-cpe-20261103-v1', E'dc', E'{"physicalFace":"rear","powerSystem":"dc"}
');
INSERT INTO hardware_group_extension (profile_key, revision, group_key, metadata) VALUES (E'draytek-vigor167', E'german-cpe-20261103-v1', E'lan', E'{"interfaceRole":"ethernet","physicalFace":"rear"}
');
INSERT INTO hardware_connector_template (profile_key, revision, group_key, physical_connector) VALUES (E'draytek-vigor167', E'german-cpe-20261103-v1', E'dsl', E'dsl-rj11');
INSERT INTO hardware_group_extension (profile_key, revision, group_key, metadata) VALUES (E'draytek-vigor167', E'german-cpe-20261103-v1', E'dsl', E'{"interfaceRole":"dsl","physicalFace":"rear"}
');
UPDATE hardware_definition SET sealed=true WHERE profile_key=E'draytek-vigor167' AND revision=E'german-cpe-20261103-v1';
INSERT INTO hardware_definition (profile_key, revision, mount_kind, rack_units, width_mm, height_mm, depth_mm, color, definition_sha256, manufacturer, family, model, sku, provenance_kind, source_reference, sealed) VALUES (E'draytek-vigor2766', E'german-cpe-20261103-v1', E'desktop', 0, 207, 42, 131, E'#f2f1ef', E'a18edec815c64c14d79ebc618368e6f14eaece463440d9ddae826dc458b51ac8', E'DrayTek', E'Vigor2766 sinWLAN', E'Vigor2766', E'Vigor2766', E'manufacturer-specification', E'https://www.draytek.de/de/produkte/modem-router/vigor2766-serie/', false);
INSERT INTO hardware_group_template (profile_key, revision, group_key, sort_order, type, port_count, face, name, prefix, power_role) VALUES (E'draytek-vigor2766', E'german-cpe-20261103-v1', E'usb', 0, E'usb_a', 2, E'rear', E'USB', E'USB ', E'unspecified');
INSERT INTO hardware_group_template (profile_key, revision, group_key, sort_order, type, port_count, face, name, prefix, power_role) VALUES (E'draytek-vigor2766', E'german-cpe-20261103-v1', E'lan', 1, E'rj45', 4, E'rear', E'P', E'P ', E'unspecified');
INSERT INTO hardware_group_template (profile_key, revision, group_key, sort_order, type, port_count, face, name, prefix, power_role) VALUES (E'draytek-vigor2766', E'german-cpe-20261103-v1', E'dsl', 2, E'dsl', 1, E'rear', E'DSL', E'DSL ', E'unspecified');
INSERT INTO hardware_group_template (profile_key, revision, group_key, sort_order, type, port_count, face, name, prefix, power_role) VALUES (E'draytek-vigor2766', E'german-cpe-20261103-v1', E'dc', 3, E'power_dc', 1, E'rear', E'POWER', E'POWER ', E'inlet');
INSERT INTO hardware_profile_extension (profile_key, revision, metadata) VALUES (E'draytek-vigor2766', E'german-cpe-20261103-v1', E'{"configuration":[{"description":"Modelo/SKU expl\\u00edcito; fuente externaDC. No accesorios derack impl\\u00edcitos.","partNumber":"Vigor2766","quantity":1,"slot":"base"}],"continuities":[],"mounting":{"kind":"desktop","target":"parent"}}
');
INSERT INTO hardware_group_extension (profile_key, revision, group_key, metadata) VALUES (E'draytek-vigor2766', E'german-cpe-20261103-v1', E'usb', E'{"physicalFace":"rear"}
');
INSERT INTO hardware_group_extension (profile_key, revision, group_key, metadata) VALUES (E'draytek-vigor2766', E'german-cpe-20261103-v1', E'lan', E'{"interfaceRole":"ethernet","physicalFace":"rear"}
');
INSERT INTO hardware_connector_template (profile_key, revision, group_key, physical_connector) VALUES (E'draytek-vigor2766', E'german-cpe-20261103-v1', E'dsl', E'dsl-rj11');
INSERT INTO hardware_group_extension (profile_key, revision, group_key, metadata) VALUES (E'draytek-vigor2766', E'german-cpe-20261103-v1', E'dsl', E'{"interfaceRole":"dsl","physicalFace":"rear"}
');
INSERT INTO hardware_connector_template (profile_key, revision, group_key, physical_connector) VALUES (E'draytek-vigor2766', E'german-cpe-20261103-v1', E'dc', E'dc-barrel');
INSERT INTO hardware_group_extension (profile_key, revision, group_key, metadata) VALUES (E'draytek-vigor2766', E'german-cpe-20261103-v1', E'dc', E'{"physicalFace":"rear","powerSystem":"dc"}
');
UPDATE hardware_definition SET sealed=true WHERE profile_key=E'draytek-vigor2766' AND revision=E'german-cpe-20261103-v1';
INSERT INTO hardware_definition (profile_key, revision, mount_kind, rack_units, width_mm, height_mm, depth_mm, color, definition_sha256, manufacturer, family, model, sku, provenance_kind, source_reference, sealed) VALUES (E'draytek-vigor2766ac', E'german-cpe-20261103-v1', E'desktop', 0, 207, 42, 131, E'#f2f1ef', E'f1f64745f1ccee59c29397a5f592f536ee4fac7e7d40a7c2995b693a1dfe0107', E'DrayTek', E'Vigor2766ac WLAN', E'Vigor2766ac', E'Vigor2766ac', E'manufacturer-specification', E'https://www.draytek.de/de/produkte/modem-router/vigor2766-serie/', false);
INSERT INTO hardware_group_template (profile_key, revision, group_key, sort_order, type, port_count, face, name, prefix, power_role) VALUES (E'draytek-vigor2766ac', E'german-cpe-20261103-v1', E'usb', 0, E'usb_a', 2, E'rear', E'USB', E'USB ', E'unspecified');
INSERT INTO hardware_group_template (profile_key, revision, group_key, sort_order, type, port_count, face, name, prefix, power_role) VALUES (E'draytek-vigor2766ac', E'german-cpe-20261103-v1', E'lan', 1, E'rj45', 4, E'rear', E'P', E'P ', E'unspecified');
INSERT INTO hardware_group_template (profile_key, revision, group_key, sort_order, type, port_count, face, name, prefix, power_role) VALUES (E'draytek-vigor2766ac', E'german-cpe-20261103-v1', E'dsl', 2, E'dsl', 1, E'rear', E'DSL', E'DSL ', E'unspecified');
INSERT INTO hardware_group_template (profile_key, revision, group_key, sort_order, type, port_count, face, name, prefix, power_role) VALUES (E'draytek-vigor2766ac', E'german-cpe-20261103-v1', E'dc', 3, E'power_dc', 1, E'rear', E'POWER', E'POWER ', E'inlet');
INSERT INTO hardware_profile_extension (profile_key, revision, metadata) VALUES (E'draytek-vigor2766ac', E'german-cpe-20261103-v1', E'{"configuration":[{"description":"Modelo/SKU expl\\u00edcito; fuente externaDC. No accesorios derack impl\\u00edcitos.","partNumber":"Vigor2766ac","quantity":1,"slot":"base"}],"continuities":[],"mounting":{"kind":"desktop","target":"parent"}}
');
INSERT INTO hardware_group_extension (profile_key, revision, group_key, metadata) VALUES (E'draytek-vigor2766ac', E'german-cpe-20261103-v1', E'usb', E'{"physicalFace":"rear"}
');
INSERT INTO hardware_group_extension (profile_key, revision, group_key, metadata) VALUES (E'draytek-vigor2766ac', E'german-cpe-20261103-v1', E'lan', E'{"interfaceRole":"ethernet","physicalFace":"rear"}
');
INSERT INTO hardware_connector_template (profile_key, revision, group_key, physical_connector) VALUES (E'draytek-vigor2766ac', E'german-cpe-20261103-v1', E'dsl', E'dsl-rj11');
INSERT INTO hardware_group_extension (profile_key, revision, group_key, metadata) VALUES (E'draytek-vigor2766ac', E'german-cpe-20261103-v1', E'dsl', E'{"interfaceRole":"dsl","physicalFace":"rear"}
');
INSERT INTO hardware_connector_template (profile_key, revision, group_key, physical_connector) VALUES (E'draytek-vigor2766ac', E'german-cpe-20261103-v1', E'dc', E'dc-barrel');
INSERT INTO hardware_group_extension (profile_key, revision, group_key, metadata) VALUES (E'draytek-vigor2766ac', E'german-cpe-20261103-v1', E'dc', E'{"physicalFace":"rear","powerSystem":"dc"}
');
UPDATE hardware_definition SET sealed=true WHERE profile_key=E'draytek-vigor2766ac' AND revision=E'german-cpe-20261103-v1';
INSERT INTO hardware_definition (profile_key, revision, mount_kind, rack_units, width_mm, height_mm, depth_mm, color, definition_sha256, manufacturer, family, model, sku, provenance_kind, source_reference, sealed) VALUES (E'fritz-7530ax-de', E'german-cpe-20261103-v1', E'desktop', 0, 200, 45, 152, E'#f2f1ef', E'9ec77a0b14d668ed809b85d8bd1c37dc629c6d4acd60bc12d90d69e7cd05cfab', E'FRITZ!', E'FRITZ!Box DSL compacto', E'FRITZ!Box 7530 AX', E'20002930', E'manufacturer-specification', E'https://fritz.com/products/fritz-box-7530-ax-20002930', false);
INSERT INTO hardware_group_template (profile_key, revision, group_key, sort_order, type, port_count, face, name, prefix, power_role) VALUES (E'fritz-7530ax-de', E'german-cpe-20261103-v1', E'dsl', 0, E'dsl', 1, E'rear', E'DSL', E'DSL ', E'unspecified');
INSERT INTO hardware_group_template (profile_key, revision, group_key, sort_order, type, port_count, face, name, prefix, power_role) VALUES (E'fritz-7530ax-de', E'german-cpe-20261103-v1', E'lan', 1, E'rj45', 4, E'rear', E'LAN', E'LAN ', E'unspecified');
INSERT INTO hardware_group_template (profile_key, revision, group_key, sort_order, type, port_count, face, name, prefix, power_role) VALUES (E'fritz-7530ax-de', E'german-cpe-20261103-v1', E'fon-rj', 2, E'telephony', 1, E'rear', E'FON', E'FON ', E'unspecified');
INSERT INTO hardware_group_template (profile_key, revision, group_key, sort_order, type, port_count, face, name, prefix, power_role) VALUES (E'fritz-7530ax-de', E'german-cpe-20261103-v1', E'dc', 3, E'power_dc', 1, E'rear', E'POWER', E'POWER ', E'inlet');
INSERT INTO hardware_group_template (profile_key, revision, group_key, sort_order, type, port_count, face, name, prefix, power_role) VALUES (E'fritz-7530ax-de', E'german-cpe-20261103-v1', E'usb', 4, E'usb_a', 1, E'rear', E'USB2', E'USB2 ', E'unspecified');
INSERT INTO hardware_group_template (profile_key, revision, group_key, sort_order, type, port_count, face, name, prefix, power_role) VALUES (E'fritz-7530ax-de', E'german-cpe-20261103-v1', E'fon-tae', 5, E'telephony', 1, E'rear', E'FON TAE', E'FON TAE ', E'unspecified');
INSERT INTO hardware_profile_extension (profile_key, revision, metadata) VALUES (E'fritz-7530ax-de', E'german-cpe-20261103-v1', E'{"configuration":[{"description":"Modelo/SKU expl\\u00edcito; fuente externaDC. No accesorios derack impl\\u00edcitos.","partNumber":"20002930","quantity":1,"slot":"base"}],"continuities":[],"mounting":{"kind":"desktop","target":"parent"}}
');
INSERT INTO hardware_connector_template (profile_key, revision, group_key, physical_connector) VALUES (E'fritz-7530ax-de', E'german-cpe-20261103-v1', E'dsl', E'dsl-8p8c');
INSERT INTO hardware_group_extension (profile_key, revision, group_key, metadata) VALUES (E'fritz-7530ax-de', E'german-cpe-20261103-v1', E'dsl', E'{"interfaceRole":"dsl","physicalFace":"rear"}
');
INSERT INTO hardware_group_extension (profile_key, revision, group_key, metadata) VALUES (E'fritz-7530ax-de', E'german-cpe-20261103-v1', E'lan', E'{"interfaceRole":"ethernet","physicalFace":"rear"}
');
INSERT INTO hardware_connector_template (profile_key, revision, group_key, physical_connector) VALUES (E'fritz-7530ax-de', E'german-cpe-20261103-v1', E'fon-rj', E'voice-rj11');
INSERT INTO hardware_group_extension (profile_key, revision, group_key, metadata) VALUES (E'fritz-7530ax-de', E'german-cpe-20261103-v1', E'fon-rj', E'{"interfaceRole":"voice","physicalFace":"rear"}
');
INSERT INTO hardware_connector_template (profile_key, revision, group_key, physical_connector) VALUES (E'fritz-7530ax-de', E'german-cpe-20261103-v1', E'dc', E'dc-barrel');
INSERT INTO hardware_group_extension (profile_key, revision, group_key, metadata) VALUES (E'fritz-7530ax-de', E'german-cpe-20261103-v1', E'dc', E'{"physicalFace":"rear","powerSystem":"dc"}
');
INSERT INTO hardware_connector_template (profile_key, revision, group_key, physical_connector) VALUES (E'fritz-7530ax-de', E'german-cpe-20261103-v1', E'fon-tae', E'voice-tae');
INSERT INTO hardware_group_extension (profile_key, revision, group_key, metadata) VALUES (E'fritz-7530ax-de', E'german-cpe-20261103-v1', E'fon-tae', E'{"interfaceRole":"voice"}
');
UPDATE hardware_definition SET sealed=true WHERE profile_key=E'fritz-7530ax-de' AND revision=E'german-cpe-20261103-v1';
INSERT INTO hardware_definition (profile_key, revision, mount_kind, rack_units, width_mm, height_mm, depth_mm, color, definition_sha256, manufacturer, family, model, sku, provenance_kind, source_reference, sealed) VALUES (E'fritz-7590ax-v2-de', E'german-cpe-20261103-v1', E'desktop', 0, 254, 63, 191, E'#f2f1ef', E'8fbc14fdf21b45a762353cd33f1b41452da8bca6ec562e822414cd49d6799c2b', E'FRITZ!', E'FRITZ!Box DSL ancho', E'FRITZ!Box 7590 AX v2', E'20002998', E'manufacturer-specification', E'https://fritz.com/en/products/fritz-box-7590-ax-20002998', false);
INSERT INTO hardware_group_template (profile_key, revision, group_key, sort_order, type, port_count, face, name, prefix, power_role) VALUES (E'fritz-7590ax-v2-de', E'german-cpe-20261103-v1', E'dsl', 0, E'dsl', 1, E'rear', E'DSL', E'DSL ', E'unspecified');
INSERT INTO hardware_group_template (profile_key, revision, group_key, sort_order, type, port_count, face, name, prefix, power_role) VALUES (E'fritz-7590ax-v2-de', E'german-cpe-20261103-v1', E'fon-rj', 1, E'telephony', 2, E'rear', E'FON', E'FON ', E'unspecified');
INSERT INTO hardware_group_template (profile_key, revision, group_key, sort_order, type, port_count, face, name, prefix, power_role) VALUES (E'fritz-7590ax-v2-de', E'german-cpe-20261103-v1', E'wan', 2, E'rj45', 1, E'rear', E'WAN', E'WAN ', E'unspecified');
INSERT INTO hardware_group_template (profile_key, revision, group_key, sort_order, type, port_count, face, name, prefix, power_role) VALUES (E'fritz-7590ax-v2-de', E'german-cpe-20261103-v1', E'lan', 3, E'rj45', 4, E'rear', E'LAN', E'LAN ', E'unspecified');
INSERT INTO hardware_group_template (profile_key, revision, group_key, sort_order, type, port_count, face, name, prefix, power_role) VALUES (E'fritz-7590ax-v2-de', E'german-cpe-20261103-v1', E'dc', 4, E'power_dc', 1, E'rear', E'POWER', E'POWER ', E'inlet');
INSERT INTO hardware_group_template (profile_key, revision, group_key, sort_order, type, port_count, face, name, prefix, power_role) VALUES (E'fritz-7590ax-v2-de', E'german-cpe-20261103-v1', E'usb-rear', 5, E'usb_a', 1, E'rear', E'USB3 rear', E'USB3 rear ', E'unspecified');
INSERT INTO hardware_group_template (profile_key, revision, group_key, sort_order, type, port_count, face, name, prefix, power_role) VALUES (E'fritz-7590ax-v2-de', E'german-cpe-20261103-v1', E'usb-side', 6, E'usb_a', 1, E'rear', E'USB3 side', E'USB3 side ', E'unspecified');
INSERT INTO hardware_group_template (profile_key, revision, group_key, sort_order, type, port_count, face, name, prefix, power_role) VALUES (E'fritz-7590ax-v2-de', E'german-cpe-20261103-v1', E'fon-tae', 7, E'telephony', 1, E'rear', E'FON1 TAE', E'FON1 TAE ', E'unspecified');
INSERT INTO hardware_profile_extension (profile_key, revision, metadata) VALUES (E'fritz-7590ax-v2-de', E'german-cpe-20261103-v1', E'{"configuration":[{"description":"Modelo/SKU expl\\u00edcito; fuente externaDC. No accesorios derack impl\\u00edcitos.","partNumber":"20002998","quantity":1,"slot":"base"}],"continuities":[],"mounting":{"kind":"desktop","target":"parent"}}
');
INSERT INTO hardware_connector_template (profile_key, revision, group_key, physical_connector) VALUES (E'fritz-7590ax-v2-de', E'german-cpe-20261103-v1', E'dsl', E'dsl-8p8c');
INSERT INTO hardware_group_extension (profile_key, revision, group_key, metadata) VALUES (E'fritz-7590ax-v2-de', E'german-cpe-20261103-v1', E'dsl', E'{"interfaceRole":"dsl","physicalFace":"rear"}
');
INSERT INTO hardware_connector_template (profile_key, revision, group_key, physical_connector) VALUES (E'fritz-7590ax-v2-de', E'german-cpe-20261103-v1', E'fon-rj', E'voice-rj11');
INSERT INTO hardware_group_extension (profile_key, revision, group_key, metadata) VALUES (E'fritz-7590ax-v2-de', E'german-cpe-20261103-v1', E'fon-rj', E'{"interfaceRole":"voice","physicalFace":"rear"}
');
INSERT INTO hardware_group_extension (profile_key, revision, group_key, metadata) VALUES (E'fritz-7590ax-v2-de', E'german-cpe-20261103-v1', E'wan', E'{"interfaceRole":"ethernet","physicalFace":"rear"}
');
INSERT INTO hardware_group_extension (profile_key, revision, group_key, metadata) VALUES (E'fritz-7590ax-v2-de', E'german-cpe-20261103-v1', E'lan', E'{"interfaceRole":"ethernet","physicalFace":"rear"}
');
INSERT INTO hardware_connector_template (profile_key, revision, group_key, physical_connector) VALUES (E'fritz-7590ax-v2-de', E'german-cpe-20261103-v1', E'dc', E'dc-barrel');
INSERT INTO hardware_group_extension (profile_key, revision, group_key, metadata) VALUES (E'fritz-7590ax-v2-de', E'german-cpe-20261103-v1', E'dc', E'{"physicalFace":"rear","powerSystem":"dc"}
');
INSERT INTO hardware_group_extension (profile_key, revision, group_key, metadata) VALUES (E'fritz-7590ax-v2-de', E'german-cpe-20261103-v1', E'usb-rear', E'{"physicalFace":"rear"}
');
INSERT INTO hardware_connector_template (profile_key, revision, group_key, physical_connector) VALUES (E'fritz-7590ax-v2-de', E'german-cpe-20261103-v1', E'fon-tae', E'voice-tae');
INSERT INTO hardware_group_extension (profile_key, revision, group_key, metadata) VALUES (E'fritz-7590ax-v2-de', E'german-cpe-20261103-v1', E'fon-tae', E'{"interfaceRole":"voice"}
');
UPDATE hardware_definition SET sealed=true WHERE profile_key=E'fritz-7590ax-v2-de' AND revision=E'german-cpe-20261103-v1';
INSERT INTO hardware_definition (profile_key, revision, mount_kind, rack_units, width_mm, height_mm, depth_mm, color, definition_sha256, manufacturer, family, model, sku, provenance_kind, source_reference, sealed) VALUES (E'fritz-7690-de', E'german-cpe-20261103-v1', E'desktop', 0, 254, 63, 191, E'#f2f1ef', E'd403fbbd30f7f2191cf347b202130b0609150a28c0eea297265d8d511ff54f1e', E'FRITZ!', E'FRITZ!Box DSL Wi-Fi7', E'FRITZ!Box 7690', E'20003057', E'manufacturer-specification', E'https://fritz.com/products/fritz-box-7690-20003057', false);
INSERT INTO hardware_group_template (profile_key, revision, group_key, sort_order, type, port_count, face, name, prefix, power_role) VALUES (E'fritz-7690-de', E'german-cpe-20261103-v1', E'dsl', 0, E'dsl', 1, E'rear', E'DSL', E'DSL ', E'unspecified');
INSERT INTO hardware_group_template (profile_key, revision, group_key, sort_order, type, port_count, face, name, prefix, power_role) VALUES (E'fritz-7690-de', E'german-cpe-20261103-v1', E'fon-rj', 1, E'telephony', 2, E'rear', E'FON', E'FON ', E'unspecified');
INSERT INTO hardware_group_template (profile_key, revision, group_key, sort_order, type, port_count, face, name, prefix, power_role) VALUES (E'fritz-7690-de', E'german-cpe-20261103-v1', E'wan', 2, E'rj45', 1, E'rear', E'WAN2.5G', E'WAN2.5G ', E'unspecified');
INSERT INTO hardware_group_template (profile_key, revision, group_key, sort_order, type, port_count, face, name, prefix, power_role) VALUES (E'fritz-7690-de', E'german-cpe-20261103-v1', E'lan-fast', 3, E'rj45', 1, E'rear', E'LAN2.5G', E'LAN2.5G ', E'unspecified');
INSERT INTO hardware_group_template (profile_key, revision, group_key, sort_order, type, port_count, face, name, prefix, power_role) VALUES (E'fritz-7690-de', E'german-cpe-20261103-v1', E'lan', 4, E'rj45', 2, E'rear', E'LAN1G', E'LAN1G ', E'unspecified');
INSERT INTO hardware_group_template (profile_key, revision, group_key, sort_order, type, port_count, face, name, prefix, power_role) VALUES (E'fritz-7690-de', E'german-cpe-20261103-v1', E'dc', 5, E'power_dc', 1, E'rear', E'POWER', E'POWER ', E'inlet');
INSERT INTO hardware_group_template (profile_key, revision, group_key, sort_order, type, port_count, face, name, prefix, power_role) VALUES (E'fritz-7690-de', E'german-cpe-20261103-v1', E'usb', 6, E'usb_a', 1, E'rear', E'USB2', E'USB2 ', E'unspecified');
INSERT INTO hardware_group_template (profile_key, revision, group_key, sort_order, type, port_count, face, name, prefix, power_role) VALUES (E'fritz-7690-de', E'german-cpe-20261103-v1', E'fon-tae', 7, E'telephony', 1, E'rear', E'FON1 TAE', E'FON1 TAE ', E'unspecified');
INSERT INTO hardware_profile_extension (profile_key, revision, metadata) VALUES (E'fritz-7690-de', E'german-cpe-20261103-v1', E'{"configuration":[{"description":"Modelo/SKU expl\\u00edcito; fuente externaDC. No accesorios derack impl\\u00edcitos.","partNumber":"20003057","quantity":1,"slot":"base"}],"continuities":[],"mounting":{"kind":"desktop","target":"parent"}}
');
INSERT INTO hardware_connector_template (profile_key, revision, group_key, physical_connector) VALUES (E'fritz-7690-de', E'german-cpe-20261103-v1', E'dsl', E'dsl-8p8c');
INSERT INTO hardware_group_extension (profile_key, revision, group_key, metadata) VALUES (E'fritz-7690-de', E'german-cpe-20261103-v1', E'dsl', E'{"interfaceRole":"dsl","physicalFace":"rear"}
');
INSERT INTO hardware_connector_template (profile_key, revision, group_key, physical_connector) VALUES (E'fritz-7690-de', E'german-cpe-20261103-v1', E'fon-rj', E'voice-rj11');
INSERT INTO hardware_group_extension (profile_key, revision, group_key, metadata) VALUES (E'fritz-7690-de', E'german-cpe-20261103-v1', E'fon-rj', E'{"interfaceRole":"voice","physicalFace":"rear"}
');
INSERT INTO hardware_group_extension (profile_key, revision, group_key, metadata) VALUES (E'fritz-7690-de', E'german-cpe-20261103-v1', E'wan', E'{"interfaceRole":"ethernet","physicalFace":"rear"}
');
INSERT INTO hardware_group_extension (profile_key, revision, group_key, metadata) VALUES (E'fritz-7690-de', E'german-cpe-20261103-v1', E'lan-fast', E'{"interfaceRole":"ethernet","physicalFace":"rear"}
');
INSERT INTO hardware_group_extension (profile_key, revision, group_key, metadata) VALUES (E'fritz-7690-de', E'german-cpe-20261103-v1', E'lan', E'{"interfaceRole":"ethernet","physicalFace":"rear"}
');
INSERT INTO hardware_connector_template (profile_key, revision, group_key, physical_connector) VALUES (E'fritz-7690-de', E'german-cpe-20261103-v1', E'dc', E'dc-barrel');
INSERT INTO hardware_group_extension (profile_key, revision, group_key, metadata) VALUES (E'fritz-7690-de', E'german-cpe-20261103-v1', E'dc', E'{"physicalFace":"rear","powerSystem":"dc"}
');
INSERT INTO hardware_connector_template (profile_key, revision, group_key, physical_connector) VALUES (E'fritz-7690-de', E'german-cpe-20261103-v1', E'fon-tae', E'voice-tae');
INSERT INTO hardware_group_extension (profile_key, revision, group_key, metadata) VALUES (E'fritz-7690-de', E'german-cpe-20261103-v1', E'fon-tae', E'{"interfaceRole":"voice"}
');
UPDATE hardware_definition SET sealed=true WHERE profile_key=E'fritz-7690-de' AND revision=E'german-cpe-20261103-v1';
