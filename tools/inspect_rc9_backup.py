"""Read-only RC9 backup inventory. Does not restore, execute or publish its contents."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path


def analyze(path):
    raw = path.read_bytes()
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate JSON keys')
            result[key] = value
        return result
    data = json.loads(raw.decode('utf-8-sig'), object_pairs_hook=unique)
    if not isinstance(data, dict) or data.get('version') != '0.8' or not isinstance(data.get('racks'), list):
        raise ValueError('Not a supported RC9 inspection structure')
    racks = data['racks']
    devices = [d for r in racks for d in r['devs']]
    ports = [p for d in devices for p in d['ports']]
    cables = [c for r in racks for c in r['conns']] + data.get('crossConns', [])
    counts = {label: Counter(x['id'] for x in items) for label, items in [('racks', racks), ('devices', devices), ('ports', ports), ('connections', cables)]}
    port_owner = {p['id']: d['id'] for d in devices for p in d['ports']}
    references = sum(port_owner.get(c.get(p)) != c.get(d) for c in cables for p, d in [('fp','fd'), ('tp','td')])
    occupied = Counter(c[p] for c in cables for p in ('fp', 'tp'))
    clients = {r.get('rackclickLocation', {}).get('client') for r in racks}
    return {'status': 'ANALYZED_NOT_RESTORED', 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
        'format': 'RC9 project JSON v0.8; not PostgreSQL dump',
        'counts': {'clientsByRackLocation': len(clients - {None, ''}), 'racks': len(racks), 'devices': len(devices),
            'ports': len(ports), 'internalConnections': sum(len(r['conns']) for r in racks),
            'crossConnections': len(data.get('crossConns', [])), 'locations': len(data.get('rackclickLocations', []))},
        'duplicateIds': {key: sum(n - 1 for n in value.values() if n > 1) for key, value in counts.items()},
        'unresolvedEndpointReferences': references,
        'repeatedEndpointOccupations': sum(n - 1 for n in occupied.values() if n > 1),
        'limitations': ['Read-only structural inventory, not full compatibility validation.',
            'Requires preserving customer hierarchy, explicit group/type identity and all source extensions.',
            'No database or manual QA data changed; restore/importer remains pending.']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = analyze(args.source)
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2)
        stream.write('\n')
