"""Seven physical media for future authoring; v2 and all published definitions stay immutable.

validate_model(row, expected_revision) returns the exact ORIGINAL object unchanged.
Only a private structural copy maps sfp56->sfp28 and qsfpdd->qsfp for v2 validation.
No speed negotiation, adapters, breakouts, module population or lane endpoints inferred.
"""
from __future__ import annotations
import copy
import importlib.util
from pathlib import Path

ROOT = Path(__file__).absolute().parents[1]
_spec = importlib.util.spec_from_file_location('physical_v3_private_v2', ROOT/'tools/hardware_physical_v2.py')
engine = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(engine)
base, c, g = engine.base, engine.c, engine.g
CatalogError, expand = engine.CatalogError, engine.expand
ALLOWED_TYPES = ('rj45', 'sfp', 'sfp28', 'sfp56', 'qsfp', 'qsfpdd', 'power')


def validate_model(row, expected_revision):
    c.require(isinstance(row, dict) and isinstance(row.get('definition'), dict) and
              isinstance(row['definition'].get('groups'), list), 'physical_v3_groups_invalid')
    groups = row['definition']['groups']
    c.require(all(isinstance(group, dict) and isinstance(group.get('type'), str) and
                  group['type'] in ALLOWED_TYPES for group in groups), 'physical_v3_connector_unsupported')
    shadow = copy.deepcopy(row)
    for group in shadow['definition']['groups']:
        group['type'] = {'sfp56': 'sfp28', 'qsfpdd': 'qsfp'}.get(group['type'], group['type'])
    engine.validate_model(shadow, expected_revision)
    # AddGroup materializes name and prefix through Text(...,100). Count raw
    # scalars and keep stricter authoring checks; do not normalize/trim input.
    for group in groups:
        for field in ('name', 'prefix'):
            value = group[field]
            c.require(len(value) <= 100 and (field != 'name' or bool(value.strip())) and
                      not any(ord(char) < 32 or 0x7f <= ord(char) <= 0x9f or
                              0xd800 <= ord(char) <= 0xdfff for char in value),
                      'physical_v3_group_'+field+'_invalid')
    return row
