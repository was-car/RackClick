"""Author explicit RJ45 female/female continuity without changing published engines.

validate_model(row, expected_revision) returns the exact ORIGINAL object unchanged.
Only a private structural copy removes passthrough for v3 geometry validation.
The declared one-to-one rule is descriptive; no internal cable or tracing is inferred.
Rows without continuity use the unchanged seven-media v3 contract.
"""
from __future__ import annotations
import copy
import importlib.util
from pathlib import Path

ROOT = Path(__file__).absolute().parents[1]
_spec = importlib.util.spec_from_file_location('passive_family_private_v3', ROOT/'tools/hardware_physical_v3.py')
engine = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(engine)
base, c, g = engine.base, engine.c, engine.g
CatalogError, expand, ALLOWED_TYPES = engine.CatalogError, engine.expand, engine.ALLOWED_TYPES


def validate_model(row, expected_revision):
    c.require(isinstance(row, dict) and isinstance(row.get('definition'), dict),
              'passive_family_definition_invalid')
    definition = row['definition']
    continuity = definition.get('passthrough')
    if continuity is None:
        return engine.validate_model(row, expected_revision)
    c.require(isinstance(continuity, dict) and set(continuity) ==
              {'frontGroup', 'rearGroup', 'count', 'mapping', 'tracingAvailable'},
              'passive_family_continuity_invalid')
    c.require(continuity['mapping'] == 'one-to-one' and continuity['tracingAvailable'] is False,
              'passive_family_tracing_unsupported')
    c.require(type(continuity['count']) is int and 1 <= continuity['count'] <= 96,
              'passive_family_count_invalid')
    c.require(isinstance(continuity['frontGroup'], str) and isinstance(continuity['rearGroup'], str),
              'passive_family_mapping_invalid')
    shadow = copy.deepcopy(row)
    shadow['definition']['passthrough'] = None
    engine.validate_model(shadow, expected_revision)
    groups = definition['groups']
    c.require(len(groups) == 2 and all(group['type'] == 'rj45' for group in groups),
              'passive_family_connector_unsupported')
    by_key = {group['key']: group for group in groups}
    front = by_key.get(continuity['frontGroup'])
    rear = by_key.get(continuity['rearGroup'])
    c.require(front is not None and rear is not None and front is not rear and
              front['face'] == 'front' and rear['face'] == 'rear' and
              front['count'] == rear['count'] == continuity['count'],
              'passive_family_mapping_invalid')
    return row
