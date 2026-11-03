"""Validate five physical connector families without widening historical engines.

API: validate_model(row, expected_revision) returns the ORIGINAL row unchanged.
Groups/banks keep their existing shape; a QSFP bank has type='qsfp', not 'sfp'.
Only a private structural copy substitutes sfp28/qsfp for legacy geometry validation.
QSFP means a documented QSFP+/QSFP28 cage: no DD, breakout or optional module inference.
No files, database or catalogue locks are written by this module.
"""
from __future__ import annotations

import copy
import importlib.util
from pathlib import Path

ROOT = Path(__file__).absolute().parents[1]
ALLOWED_TYPES = ('rj45', 'sfp', 'sfp28', 'qsfp', 'power')


def _private_legacy():
    spec = importlib.util.spec_from_file_location('physical_v2_private_legacy', ROOT/'tools/build_hardware_batch50.py')
    engine = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(engine)
    return engine


base = _private_legacy()
c, g = base.c, base.g
CatalogError = c.CatalogError
expand = base.expand


def validate_model(row, expected_revision):
    """Validate without mutation; reject unsupported types before normalizing a copy.

    Structural errors retain their legacy diagnostic codes. The extra diagnostics
    use physical_v2_*. A fresh validator per call avoids revision/global-state leaks.
    The returned row is the input object, with every real connector type preserved.
    """
    c.require(isinstance(expected_revision, str) and 0 < len(expected_revision) <= 128,
              'physical_v2_revision_invalid')
    c.require(isinstance(row, dict) and isinstance(row.get('definition'), dict) and
              isinstance(row['definition'].get('groups'), list), 'physical_v2_groups_invalid')
    groups = row['definition']['groups']
    c.require(all(isinstance(group, dict) and isinstance(group.get('type'), str) and
                  group['type'] in ALLOWED_TYPES for group in groups), 'physical_v2_connector_unsupported')
    shadow = copy.deepcopy(row)
    for group in shadow['definition']['groups']:
        if group['type'] in ('sfp28', 'qsfp'):
            group['type'] = 'sfp'
    engine = _private_legacy()
    engine.REVISION = expected_revision
    try:
        engine.validate_model(shadow)
    except engine.c.CatalogError as error:
        raise CatalogError(str(error)) from None
    c.require(all(group['count'] <= 96 for group in groups), 'physical_v2_runtime_group_limit')
    return row
