"""Reproduce RC9/R3 integration gaps on synthetic data only. No production DB."""
from pathlib import Path
import hashlib
import json
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'reference/r3'))
from reference_import import new_db, add_destination, preflight, import_copy, ImportRejected
from pilot_server import project_view, HOUSE


def run():
    archive = ROOT / 'reference/RackClick-v0.9.0-rc9-Adoptada-2026-09-28.zip'
    with zipfile.ZipFile(archive) as z:
        base = 'RackClick-v0.9.0-rc9-Adoptada-2026-09-28/'
        html = z.read(base + 'RackClick-v0.9.0-rc9-Offline.html')
        raw = z.read(base + 'fixtures/demo-10-clients-es.json')
        double = z.read(base + 'fixtures/golden-double-occupancy.json')
    sha = hashlib.sha256(html).hexdigest()
    assert sha == '63a60c4b52360211e1ae90b2e38541dc76bf372007219868e7c203af9223ea96'
    source = json.loads(raw)
    source_clients = {r['rackclickLocation']['client'] for r in source['racks']}
    db = new_db()
    try:
        scope = (HOUSE, 'destination', 'site', 'building', 'room')
        add_destination(db, *scope)
        result = import_copy(db, raw, scope=scope, request_id='bridge-audit')
        scopes = db.execute('SELECT count(DISTINCT customer_id), count(DISTINCT room_id), count(*) FROM rack').fetchone()
        view = project_view(db, 'destination')
        api_port_keys = sorted(view['racks'][0]['devices'][0]['ports'][0])
        original = db.execute('SELECT original_bytes FROM import_batch').fetchone()[0]
        assert len(source_clients) == 10 and scopes == (1, 1, 68)
        assert original == raw
        assert 'type' not in api_port_keys and 'rackclickFace' not in api_port_keys
    finally:
        db.close()
    try:
        preflight(double)
    except ImportRejected as exc:
        double_result = str(exc)
    else:
        raise AssertionError('Expected the existing R3 importer to reject double occupancy')
    assert double_result == 'port used by multiple connections'
    return {
        'status': 'DIAGNOSTIC_REPRODUCED_NOT_FIXED',
        'rc9_html_sha256': sha,
        'synthetic_only': True,
        'findings': [
            {'id': 'S0-01', 'source_clients': len(source_clients), 'r3_destination_customers': scopes[0],
             'r3_destination_rooms': scopes[1], 'racks': scopes[2], 'original_bytes_retained': original == raw,
             'meaning': 'R3 single-destination import is unsuitable for automatic RC9 multi-client import'},
            {'id': 'S0-02', 'api_port_fields': api_port_keys,
             'meaning': 'API projection omits port type and front/rear metadata; originals remain stored'},
            {'id': 'S0-03', 'r3_rejection': double_result,
             'meaning': 'Known RC9 double-occupancy fixture cannot be imported with the current R3 policy'}
        ],
        'demo_counts': result['counts']
    }


if __name__ == '__main__':
    print(json.dumps(run(), indent=2, ensure_ascii=False))
