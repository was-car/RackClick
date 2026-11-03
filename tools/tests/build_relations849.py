"""Build the complete frontend once and freeze it with the unchanged832 server."""
import hashlib
import json
import shutil
import subprocess
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
E = ROOT / 'evidence/s1-20261018/tanda-849'
BASE = ROOT / 'evidence/s1-20261018/sesenta-tandas-773-832/CANDIDATA832-02.json'
PIN = '511c097bafd5baf7590da15287a0dbd53bb5eb8e2fde33931c940b2885e7dfc5'
STATUS_SOURCE = 'development/frontend/src/AdminGroupRelations.jsx'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree(directory):
    return {p.relative_to(directory).as_posix(): sha(p)
            for p in sorted(directory.rglob('*')) if p.is_file()}


def save(name, value):
    path = E / name
    with path.open('x', encoding='utf-8') as output:
        json.dump(value, output, indent=2)
        output.write('\n')


def main():
    assert not E.exists(), 'Keep previous evidence; inspect before any new attempt'
    assert sha(BASE) == PIN
    old = json.loads(BASE.read_bytes())
    old_sources = json.loads((BASE.parent / 'SOURCE-FREEZE-APP-02.json').read_bytes())['sources']
    sources = {p: sha(ROOT / p) for p in old_sources}
    assert len(sources) == 175
    assert {p for p in sources if sources[p] != old_sources[p]} == {STATUS_SOURCE}
    assert sources[STATUS_SOURCE] == '7f0da587c8284dc8aa3b0a2ae76fdd5ed39ba4b02a884741f377e00e913e8b9f'
    assert tree(ROOT / old['candidateDirectory'] / 'server') == old['distributions']['server']
    assert tree(ROOT / old['candidateDirectory'] / 'frontend') == old['distributions']['frontend']
    git = str(ROOT / '.local/git-2.55.0.5/cmd/git.exe')
    base_commit = subprocess.check_output([git, 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    assert base_commit == '834cc776c98f4a8c08d6db40b75480a709373dc2'
    node = ROOT / '.local/node-v24.21.0-win-x64/node.exe'
    assert subprocess.check_output([str(node), '--version'], text=True).strip() == 'v24.21.0'
    # Only public hashes of private QA inputs are recorded; no application/database access.
    prior = json.loads((ROOT / 'evidence/s1-20261018/tanda-848/INICIO.json').read_bytes())
    guards = {p: sha(ROOT / p) for p in prior['guards'] if p != STATUS_SOURCE}
    E.mkdir(parents=True)
    save('INICIO.json', dict(utc=datetime.now(timezone.utc).isoformat(), baseCommit=base_commit,
         sourceManifest=BASE.relative_to(ROOT).as_posix(), sourceManifestSha256=PIN,
         guards=guards, actualQaAccessed=False, progress=78))
    save('SOURCE-FREEZE-APP.json', dict(sources=sources, sourceCount=len(sources),
         changesFrom832=[STATUS_SOURCE], serverSourcesUnchanged=True))
    started = time.monotonic()
    with (E / 'frontend-build.log').open('xb') as log:
        done = subprocess.run([str(node), 'build.mjs'], cwd=ROOT / 'development/frontend',
                              stdout=log, stderr=subprocess.STDOUT, timeout=180)
    unchanged = all(sha(ROOT / p) == h for p, h in sources.items())
    record = dict(exitCode=done.returncode, seconds=round(time.monotonic() - started, 3),
                  successful=done.returncode == 0 and unchanged, sourcesUnchanged=unchanged,
                  fullFrontendBuilds=1, serverBuilds=0, node='v24.21.0', actualQaAccessed=False)
    save('BUILD.json', record)
    assert record['successful']
    target = ROOT / '.local/candidates' / ('relations849-final-' + uuid.uuid4().hex)
    shutil.copytree(ROOT / old['candidateDirectory'] / 'server', target / 'server')
    shutil.copytree(ROOT / 'development/frontend/dist', target / 'frontend')
    distributions = {part: tree(target / part) for part in ['server', 'frontend']}
    assert distributions['server'] == old['distributions']['server']
    assert len(distributions['server']) == 20 and len(distributions['frontend']) == 18
    assert set(distributions['frontend']) == set(old['distributions']['frontend'])
    assert {p for p, h in distributions['frontend'].items()
            if h != old['distributions']['frontend'][p]} == {'app.js'}
    manifest = dict(utc=datetime.now(timezone.utc).isoformat(), baseCommit=base_commit, schema=11,
                    candidateDirectory=target.relative_to(ROOT).as_posix(),
                    serverDll=(target / 'server/RackClick.Server.dll').relative_to(ROOT).as_posix(),
                    frontend=(target / 'frontend').relative_to(ROOT).as_posix(),
                    selectedInRealQaAtFreeze=False, sourceManifest=BASE.relative_to(ROOT).as_posix(),
                    sourceManifestSha256=PIN, distributions=distributions, fileCount=38,
                    totalBytes=sum(p.stat().st_size for p in target.rglob('*') if p.is_file()),
                    scope='Full frontend containing848 status correction; frozen832 server copied unchanged. Not selected in real QA or admitted by Windows bundle profiles.')
    save('CANDIDATA849.json', manifest)
    print(json.dumps(dict(successful=True, candidate=manifest['candidateDirectory'],
                         manifestSha256=sha(E / 'CANDIDATA849.json'), files=38,
                         bytes=manifest['totalBytes'], fullFrontendBuilds=1, serverBuilds=0)))


if __name__ == '__main__':
    main()
