"""Compile the curated hardware authoring data; never import vendor data implicitly.

Schema 16 is a closed publication target. The frozen reference and reviewed lock
must match before ANY output is written. New models need a new database contract,
not an override flag here. Python is needed by authors, not the running server.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import sys
import tempfile
from decimal import Decimal

ROOT = Path(__file__).resolve().parents[1]
SOURCE = 'development/hardware/catalog-source-v1.json'
LOCK = 'development/hardware/catalog-schema16.lock.json'
REFERENCE = 'development/frontend/src/hardware-reference.json'
SERVER = 'development/server/src/RackClick.Server/InventoryHardwareProfiles.Generated.cs'
FRONTEND = 'development/frontend/src/hardware-catalog.generated.json'
MANIFEST = 'development/hardware/catalog-generated.manifest.json'
TARGETS = 'development/server/src/RackClick.Server/HardwareCatalog.Generated.targets'
KEY = re.compile(r'[a-z0-9][a-z0-9-]{0,127}\Z')


class CatalogError(ValueError):
    pass


def require(ok, code):
    if not ok:
        raise CatalogError(code)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return (json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode('ascii')


def fields(value, names, code):
    require(isinstance(value, dict) and set(value) == set(names.split()), code)


def key(value):
    require(isinstance(value, str) and KEY.fullmatch(value) is not None, 'catalog_key_invalid')


def text(value, limit=128):
    require(isinstance(value, str) and len(value) <= limit and
            all(ord(c) >= 32 and not 0xD800 <= ord(c) <= 0xDFFF for c in value), 'catalog_text_invalid')


def integer(value, low, high):
    require(type(value) is int and low <= value <= high, 'catalog_integer_invalid')


def dimensions(value, commercial=False):
    fields(value, 'width height depth', 'catalog_dimensions_invalid')
    for size in value.values():
        require(type(size) in (int, float) and 0 < size <= 10000 and math.isfinite(size),
                'catalog_dimensions_invalid')
    # Current backend profile contract has decimal width and integral height/depth.
    if commercial:
        require(value['height'] >= 1 and value['depth'] >= 1 and all(Decimal(str(size)).as_tuple().exponent >= -3 for size in value.values()), 'catalog_dimensions_precision_unsupported')
    else:
        require(type(value['height']) is int and type(value['depth']) is int, 'catalog_dimensions_precision_unsupported')


def validate(data, commercial=False):
    fields(data, 'formatVersion catalogKey definitions', 'catalog_format_invalid')
    require(type(data['formatVersion']) is int and data['formatVersion'] == 1, 'catalog_format_invalid')
    key(data['catalogKey'])
    definitions = data['definitions']
    require(isinstance(definitions, list) and 0 < len(definitions) <= 10000, 'catalog_definitions_invalid')
    seen = set()
    for model in definitions:
        fields(model, 'key revision identity provenance kind rackUnits dimensionsMm color slots groups passthrough', 'catalog_definition_invalid')
        key(model['key']); key(model['revision'])
        pair = model['key'], model['revision']
        require(pair not in seen, 'catalog_duplicate_revision'); seen.add(pair)
        fields(model['identity'], 'manufacturer family model sku', 'catalog_identity_invalid')
        # Only own synthetic definitions are publishable in this authoring profile.
        if commercial:
            for value in model['identity'].values():
                text(value); require(bool(value.strip()), 'catalog_identity_invalid')
        else:
            require(all(v is None for v in model['identity'].values()), 'catalog_commercial_identity_not_reviewed')
        fields(model['provenance'], 'kind source assets', 'catalog_provenance_invalid')
        if commercial:
            require(model['provenance']['kind'] == 'manufacturer-specification' and model['provenance']['assets'] == [] and
                    model['provenance']['source'] == 'https://media.startech.com/cms/pdfs/c6panelutp241uft_datasheet.pdf', 'catalog_provenance_not_reviewed')
        else:
            require(model['provenance'] == {'kind': 'own-synthetic', 'source': 'docs/CONTRATO-HARDWARE-MONTAJE-v1.md', 'assets': []}, 'catalog_provenance_not_reviewed')
        require(model['kind'] in ('shelf', 'rack', 'desktop'), 'catalog_mount_kind_invalid')
        integer(model['rackUnits'], 0 if model['kind'] == 'desktop' else 1, 0 if model['kind'] == 'desktop' else 60)
        dimensions(model['dimensionsMm'], commercial)
        require(isinstance(model['color'], str) and re.fullmatch(r'#[0-9a-f]{6}', model['color']) is not None, 'catalog_color_invalid')
        require(isinstance(model['slots'], list) and len(model['slots']) <= 1, 'catalog_slots_unsupported')
        require(bool(model['slots']) == (model['kind'] == 'shelf'), 'catalog_slots_invalid')
        for slot in model['slots']:
            fields(slot, 'key dimensionsMm', 'catalog_slot_invalid'); key(slot['key']); dimensions(slot['dimensionsMm'], commercial)
        require(isinstance(model['groups'], list) and len(model['groups']) <= 32, 'catalog_groups_invalid')
        group_keys = set(); total = 0
        for group in model['groups']:
            fields(group, 'key type count face name prefix', 'catalog_group_invalid'); key(group['key'])
            require(group['key'] not in group_keys, 'catalog_group_duplicate'); group_keys.add(group['key'])
            require(group['type'] in ('rj45', 'sfp'), 'catalog_connector_unsupported')
            require(group['face'] in ('front', 'rear'), 'catalog_face_invalid')
            integer(group['count'], 1, 256); total += group['count']
            text(group['name']); text(group['prefix'])
        require(total <= 1024, 'catalog_ports_limit')
        if model['kind'] == 'shelf':
            require(not model['groups'], 'catalog_shelf_ports_unsupported')
        continuity = model['passthrough']
        if continuity is not None:
            fields(continuity, 'frontGroup rearGroup count mapping tracingAvailable', 'catalog_passthrough_invalid')
            require(continuity['mapping'] == 'one-to-one' and continuity['tracingAvailable'] is False, 'catalog_tracing_unsupported')
            integer(continuity['count'], 1, 256)
            groups = {group['key']: group for group in model['groups']}
            key(continuity['frontGroup']); key(continuity['rearGroup'])
            front = groups.get(continuity['frontGroup']); rear = groups.get(continuity['rearGroup'])
            require(front is not None and rear is not None and front['face'] == 'front' and rear['face'] == 'rear'
                    and front['count'] == rear['count'] == continuity['count'] and front['type'] == rear['type'], 'catalog_passthrough_invalid')
    return data


def unique_object(pairs):
    result = {}
    for name, value in pairs:
        require(name not in result, 'catalog_json_duplicate_field'); result[name] = value
    return result


def load(raw):
    require(len(raw) <= 16 * 1024 * 1024, 'catalog_input_too_large')
    try:
        return json.loads(raw.decode('utf-8'), object_pairs_hook=unique_object,
                          parse_constant=lambda _: (_ for _ in ()).throw(CatalogError('catalog_number_invalid')))
    except CatalogError:
        raise
    except (UnicodeError, ValueError, RecursionError) as error:
        raise CatalogError('catalog_json_invalid') from error


def projection(data):
    revisions = {model['revision'] for model in data['definitions']}
    require(len(revisions) == 1, 'catalog_frontend_multirevision_not_propagated')
    profiles = []
    for model in data['definitions']:
        dims = model['dimensionsMm']
        row = dict(key=model['key'], kind=model['kind'], sizeU=model['rackUnits'],
                   widthMm=dims['width'], heightMm=dims['height'], depthMm=dims['depth'])
        if model['slots']:
            slot = model['slots'][0]; sd = slot['dimensionsMm']
            row['slot'] = dict(key=slot['key'], widthMm=sd['width'], heightMm=sd['height'], depthMm=sd['depth'])
        if model['passthrough'] is not None:
            row['passthrough'] = model['passthrough']
        row['groups'] = [{field: group[field] for field in ('key', 'face', 'type', 'count')} for group in model['groups']]
        profiles.append(row)
    return dict(version=next(iter(revisions)), synthetic=True, profiles=profiles)


def server_source(data, commercial=False):
    # JSON string literals are a safe C# subset for this format's escaped text.
    quote = lambda value: json.dumps(value, ensure_ascii=True)
    lines = ['// <auto-generated> tools/build_hardware_catalog.py; do not edit. </auto-generated>', 'namespace RackClick.Server;', '']
    lines += (['using static RackClick.Server.InventoryHardwareProfiles;', 'internal static class CommercialHardwareProfiles', '{', '    internal static readonly Registry Catalog = new(['] if commercial else
              ['public static partial class InventoryHardwareProfiles', '{', '    private static readonly Registry ReferenceCatalog = new(['])
    for model in data['definitions']:
        dims = model['dimensionsMm']
        groups = ', '.join('new(' + ', '.join((quote(g['key']), quote(g['type']), str(g['count']), quote(g['face']), quote(g['name']), quote(g['prefix']))) + ')' for g in model['groups'])
        slots = ', '.join('new(' + ', '.join((quote(s['key']), str(s['dimensionsMm']['width']) + 'm',
                        str(s['dimensionsMm']['height'])+'m', str(s['dimensionsMm']['depth'])+'m')) + ')' for s in model['slots'])
        continuity = model['passthrough']
        passthrough = ('new(' + ', '.join((quote(continuity['frontGroup']), quote(continuity['rearGroup']), str(continuity['count']))) + ')') if continuity else 'null'
        lines.append('        new(' + ', '.join((quote(model['key']), str(model['rackUnits']), str(dims['width']) + 'm',
                     str(dims['height'])+'m', str(dims['depth'])+'m', quote(model['color']), '[' + groups + ']', quote(model['revision']))) + ') {' +
                     ' Kind = ' + quote(model['kind']) + ', DefinitionSha256 = ' + quote(sha(canonical(model))) +
                     ', Slots = [' + slots + '], Passthrough = ' + passthrough +
                     ''.join(', '+field.title()+' = '+quote(value) for field,value in model['identity'].items() if value is not None) + ' },')
    return ('\n'.join(lines + ['    ]);', '}', ''])).encode('ascii')


def path(root, relative):
    candidate = Path(os.path.abspath(root / relative))
    for ancestor in (*reversed(candidate.parents), candidate):
        if os.path.lexists(ancestor):
            info = os.lstat(ancestor)
            require(not (stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400), 'catalog_reparse_path')
    return candidate


def compile_catalog(root):
    source_raw = path(root, SOURCE).read_bytes(); source = validate(load(source_raw))
    lock_raw = path(root, LOCK).read_bytes(); lock = load(lock_raw)
    fields(lock, 'formatVersion targetSchema referenceSha256 definitions', 'catalog_lock_invalid')
    require(type(lock['formatVersion']) is int and lock['formatVersion'] == 1 and
            type(lock['targetSchema']) is int and lock['targetSchema'] == 16, 'catalog_target_unsupported')
    reference_raw = path(root, REFERENCE).read_bytes()
    require(sha(reference_raw) == lock['referenceSha256'], 'catalog_reference_changed')
    pins = [{'key': model['key'], 'revision': model['revision'], 'sha256': sha(canonical(model))} for model in source['definitions']]
    require(pins == lock['definitions'], 'catalog_schema16_definition_not_reviewed')
    view = projection(source)
    require(view == load(reference_raw), 'catalog_frozen_projection_changed')
    outputs = {SERVER: server_source(source), FRONTEND: (json.dumps(view, indent=2, ensure_ascii=True) + '\n').encode('ascii')}
    manifest = dict(formatVersion=1, targetSchema=16, catalogKey=source['catalogKey'],
                    sourceSha256=sha(source_raw), lockSha256=sha(lock_raw),
                    referenceSha256=sha(reference_raw), files={name: sha(raw) for name, raw in outputs.items()},
                    definitions=pins, state='synthetic_development_not_a_release')
    outputs[MANIFEST] = (json.dumps(manifest, indent=2) + '\n').encode('ascii')
    # Built-in MSBuild task, no Python process/dependency during .NET compilation.
    inputs = {SOURCE: sha(source_raw), LOCK: sha(lock_raw), REFERENCE: sha(reference_raw),
              **{name: sha(raw) for name, raw in outputs.items()}}
    target_lines = ['<!-- Auto-generated by tools/build_hardware_catalog.py. -->', '<Project>',
                    '  <Target Name="VerifyHardwareCatalog" BeforeTargets="CoreCompile">', '    <ItemGroup>']
    for name, digest in inputs.items():
        target_lines.append('      <_HardwareCatalogInput Include="$(MSBuildThisFileDirectory)../../../../' + name + '"><ExpectedHash>' + digest + '</ExpectedHash></_HardwareCatalogInput>')
    target_lines += ['    </ItemGroup>', '    <GetFileHash Files="@(_HardwareCatalogInput)" Algorithm="SHA256">',
                     '      <Output TaskParameter="Items" ItemName="_HardwareCatalogHashed" />', '    </GetFileHash>',
                     '    <Error Condition="\'%(_HardwareCatalogHashed.FileHash)\' != \'%(_HardwareCatalogHashed.ExpectedHash)\'" Text="hardware_catalog_stale: run tools/build_hardware_catalog.py --check" />',
                     '  </Target>', '</Project>', '']
    outputs[TARGETS] = '\n'.join(target_lines).encode('ascii')
    return outputs


def run(root, write=False):
    outputs = compile_catalog(root)
    # Preflight ALL paths before publishing any derivative. Multi-file publication
    # is not a transaction; --check must pass before building or packaging.
    targets = {name: path(root, name) for name in outputs}
    if write:
        for name, target in targets.items():
            target.parent.mkdir(parents=True, exist_ok=True)
            fd, temporary = tempfile.mkstemp(prefix='.catalog-', dir=target.parent)
            try:
                with os.fdopen(fd, 'wb') as stream:
                    stream.write(outputs[name]); stream.flush(); os.fsync(stream.fileno())
                os.replace(temporary, target)
            finally:
                if os.path.lexists(temporary): os.unlink(temporary)
    else:
        for name, target in targets.items():
            require(target.is_file() and target.read_bytes() == outputs[name], 'catalog_generated_stale')
    return {'status': 'written' if write else 'verified', 'targetSchema': 16, 'definitions': 4,
            'files': {name: sha(raw) for name, raw in outputs.items()}, 'databaseChanged': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check', action='store_true'); mode.add_argument('--write', action='store_true')
    args = parser.parse_args()
    try:
        print(json.dumps(run(ROOT, write=args.write))); return 0
    except (CatalogError, OSError) as error:
        print(json.dumps({'status': 'failed', 'code': str(error) if isinstance(error, CatalogError) else 'catalog_io_failed'})); return 1


if __name__ == '__main__':
    sys.exit(main())
