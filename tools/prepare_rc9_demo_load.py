"""Prepare the ORIGINAL synthetic RC9 inventory, never a DB or credentials.

The output is private, exclusive, under .local and contains the exact source and
the canonical data plan. It is not a full database backup or an upload endpoint.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools/windows'))
from rc9_restore import analyze

SOURCE_SHA256 = 'cb52d27990a82d3f2dc12bf731bcbe6c1586575643f301e4b040b250f31374d0'


def prepare(source, output):
    source, output = Path(source), Path(output).absolute()
    if any(p.is_symlink() or p.is_junction() for p in (source, *source.parents, output, *output.parents)):
        raise ValueError('reparse_rejected')
    raw = source.read_bytes()
    if hashlib.sha256(raw).hexdigest() != SOURCE_SHA256:
        raise ValueError('original_source_hash_mismatch')
    plan = analyze(source)
    # analyze() rereads the source: bind its result to the original snapshot.
    if plan['raw'] != raw or plan['sourceSha256'] != SOURCE_SHA256:
        raise ValueError('source_changed')
    if output.parent != ROOT / '.local' or output.exists() or not output.name.startswith('rc9-demo-'):
        raise ValueError('new_private_output_required')
    output.mkdir()
    sys.path.insert(0, str(ROOT / 'development/server/tests'))
    from pg_support import protect_directory
    protect_directory(output)
    content = {'format': 'RackClickOriginalRc9Demo-v1', 'sourceSha256': SOURCE_SHA256,
               'counts': plan['counts'], 'rows': plan['rows']}
    canonical = json.dumps(content, ensure_ascii=True, allow_nan=False, sort_keys=True,
                           separators=(',', ':')).encode('ascii')
    (output / 'original.json').write_bytes(raw)
    (output / 'demo-plan.json').write_bytes(canonical)
    result = {'sourceSha256': SOURCE_SHA256, 'planSha256': hashlib.sha256(canonical).hexdigest(),
              'counts': plan['counts'], 'databaseChanged': False}
    (output / 'PREPARACION.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.source, args.output)))
