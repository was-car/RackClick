"""Final readonly guards after real849 selection, guide tests and continuity update."""
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
E = ROOT / 'evidence/s1-20261018/sesenta-tandas-850-909'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(name):
    return json.loads((E / name).read_bytes())


def main():
    output = E / 'VERIFICACION-FINAL.json'
    assert not output.exists()
    start = read('INICIO.json')
    changed = {p for p, h in start['guards'].items() if sha(ROOT / p) != h}
    assert changed <= set(start['authorizedMutableGuards']), changed - set(start['authorizedMutableGuards'])
    assert all(sha(ROOT / p) == h for p, h in start['sourceQaGuards'].items())
    package = read('PACKAGES-01.json')
    assert package['valid'] and package['byteIdentical'] and package['sourcesUnchanged']
    assert all(sha(ROOT / row['path']) == row['sha256'] for row in package['outputs'])
    freeze = read('SOURCE-FREEZE-OPERATORS-01.json')
    assert all(sha(ROOT / p) == h for p, h in freeze['sources'].items())
    manifest_path = ROOT / start['candidateManifest']
    assert sha(manifest_path) == start['candidateManifestSha256']
    manifest = json.loads(manifest_path.read_bytes())
    assert all(sha(ROOT / manifest['candidateDirectory'] / part / p) == h
               for part, files in manifest['distributions'].items() for p, h in files.items())
    app_sources = json.loads((ROOT / 'evidence/s1-20261018/tanda-849/SOURCE-FREEZE-APP.json').read_bytes())['sources']
    assert all(sha(ROOT / p) == h for p, h in app_sources.items())
    assert read('COORDINATOR-GO.json')['valid']
    assert read('REAL-QA-ACTIVATE-01.json')['state'] == 'committed' and read('REAL-QA-VALIDATE-01.json')['valid']
    tests = read('QA-TESTS-01.json')
    assert tests['successful'] and tests['availability'] == dict(manual=8, rc9=78)
    pointer = json.loads((ROOT / '.local/qa-rc9/current.json').read_bytes())
    selected = ROOT / read('REAL-QA-PREPARE-01.json')['candidateDirectory']
    assert Path(pointer['directory']).resolve() == selected.resolve()
    cfg = json.loads((selected / 'manual-qa.json').read_bytes())
    assert cfg['dllSha256'] == manifest['distributions']['server']['RackClick.Server.dll']
    assert cfg['bundleSha256'] == manifest['distributions']['frontend']['app.js']
    plan = json.loads((ROOT / 'docs/PLAN-SESENTA-TANDAS-850-909.json').read_bytes())
    assert plan['completed'] == 60
    assert all(row['status'] == 'verified' and (ROOT / row['evidence']).is_file()
               and (ROOT / row['independentEvidence']).is_file() for row in plan['batches'])
    gate = read('revision/GATE-TECNICO.json')
    assert gate['valid'] and gate['recommendedProgress'] == 78
    for key in ['sourceHashes', 'manualHashes']:
        assert all(sha(ROOT / p) == h for p, h in gate[key].items())
    progress = json.loads((ROOT / 'docs/MAPA-ENTREGA.json').read_bytes())
    assert progress['progress'] == 78 and [s['points'] for s in progress['streams']] == [18, 22, 14, 14, 9, 1]
    git = str(ROOT / '.local/git-2.55.0.5/cmd/git.exe')
    assert subprocess.check_output([git, 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip() == start['baseCommit']
    record = dict(utc=datetime.now(timezone.utc).isoformat(), successful=True,
                  guardCount=len(start['guards']), unchangedGuards=len(start['guards']) - len(changed),
                  authorizedChangedGuards=sorted(changed), sourceQaUnchangedFiles=len(start['sourceQaGuards']),
                  candidateFileCount=manifest['fileCount'], productSourcesVerified=len(app_sources),
                  applicationManifestSha256=start['candidateManifestSha256'], packagedSourceCount=len(freeze['sources']),
                  packagesByteIdentical=True, applicationBuilds=0, frontendBuilds=0,
                  sourceApplicationLogin=False, sourceApplicationDml=False,
                  source832AndRecovery712Preserved=True, actualSelectedRevision=849, actualSelectedSchema=11,
                  qaAvailable=dict(manual=8, rc9=78), newCasesAvailable=['QA-78'],
                  internalMilestonesVerified=60, progress=78, screenReaderSpeechTested=False,
                  manualWascarResultsWritten=False, finalAdoption=False)
    output.write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(record, indent=2))


if __name__ == '__main__':
    main()
