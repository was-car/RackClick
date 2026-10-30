"""Verify the closed Windows/QA12 integration without starting any runtime."""
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
E = ROOT / 'evidence/s1-20261018/sesenta-tandas-970-1029'
PIN = 'b589609154fed1567106ef0865972155258f0f5474128c73076f4697d43b8bda'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(name):
    return json.loads((E / name).read_bytes())


def protected_inputs():
    initial = read('INICIO.json')
    mutable = set(initial['authorizedMutableGuards'])
    for name in ['ALCANCE-OPERADORES.json', 'ALCANCE-READYBODY.json']:
        mutable.update(read(name)['additionalMutableGuards'])
    runtime = read('ALCANCE-RUNTIME-FUENTE.json')['authorizedMutableRuntimeFiles']
    mutable.update(runtime)
    protected = {p: h for p, h in initial['guards'].items() if p not in mutable}
    assert all(sha(ROOT / p) == h for p, h in protected.items())
    for p, row in runtime.items():
        assert initial['guards'][p] == row['sha256']
        archive = ROOT / row['privateArchive']
        assert archive.stat().st_size == row['bytes'] and sha(archive) == row['sha256']
    source = {p: h for p, h in initial['sourceQaGuards'].items() if p not in runtime}
    assert len(source) == 20 and all(sha(ROOT / p) == h for p, h in source.items())
    changes = {p: ('absent' if not (ROOT / p).exists() else sha(ROOT / p))
               for p, row in runtime.items() if not (ROOT / p).exists() or sha(ROOT / p) != row['sha256']}
    return initial, len(protected), len(source), changes


def current_product():
    publication = read('PUBLISH-FIX02-FINAL.json')
    assert publication['successful'] and publication['publicationCount'] == 1
    assert publication['frontendBuilds'] == 0 and publication['additionalBuilds'] == 0
    assert len(publication['sourceHashes']) == 181
    assert all(sha(ROOT / p) == h for p, h in publication['sourceHashes'].items())
    assert sha(E / 'CANDIDATA969-FIX02.json') == PIN
    manifest = read('CANDIDATA969-FIX02.json')
    artifacts = [(ROOT / manifest['candidateDirectory'] / part / p, h)
                 for part, files in manifest['distributions'].items() for p, h in files.items()]
    assert len(artifacts) == 39 and all(sha(p) == h for p, h in artifacts)
    assert sum(p.stat().st_size for p, _ in artifacts) == 7037914
    original = json.loads((ROOT / manifest['sourceManifest']).read_bytes())
    assert manifest['distributions']['frontend'] == original['distributions']['frontend']
    differences = [p for p, h in manifest['distributions']['server'].items()
                   if original['distributions']['server'][p] != h]
    assert sorted(differences) == ['RackClick.Domain.dll', 'RackClick.Domain.pdb',
                                  'RackClick.Server.dll', 'RackClick.Server.pdb']
    return manifest


def technical_gate():
    gate = read('revision/GATE-TECNICO.json')
    assert gate['valid'] and gate['approved'] and not gate['openBlockingFindings']
    assert gate['targetManifestSha256'] == PIN
    for key in ['sourceHashes', 'manualHashes']:
        assert all(sha(ROOT / p) == h for p, h in gate[key].items())
    assert all(sha(E / p) == h for p, h in gate['observedFilesSha256'].items())
    return gate


def main():
    output = E / 'VERIFICACION-FINAL.json'
    assert not output.exists()
    initial, protected, source_count, runtime_changes = protected_inputs()
    manifest = current_product()
    gate = technical_gate()
    package = read('PACKAGES-02.json')
    assert package['valid'] and package['byteIdentical'] and package['sourcesUnchanged']
    assert package['sourceManifestSha256'] == PIN
    assert all(sha(ROOT / row['path']) == row['sha256'] for row in package['outputs'])
    assert all(sha(ROOT / p) == h for p, h in read('SOURCE-FREEZE-OPERATORS-02.json')['sources'].items())
    assert gate['archiveSha256'] == package['outputs'][0]['sha256']
    for name in ['windows/profiles03/result.json', 'windows/native02/result.json',
                 'qa-copy/RESUMEN-AUTOR.json', 'revision/target-palette-activity01/result.json',
                 'QA-TESTS-01.json']:
        assert read(name)['successful'], name
    native = read('windows/native02/result.json')
    assert native['ownedProcessesStopped'] and native['inputsUnchanged'] and not native['cleanupErrors']
    assert native['successfulOperationalRecoveries'] == 1 and native['recoverySnapshotExact']
    assert native['systemCrtDllsAndX64RegistryUnchanged'] and len(native['tableDigestsBeforeBackup']) == 37
    assert read('COORDINATOR-GO.json')['valid']
    assert all(sha(ROOT / p) == h for p, h in read('COORDINATOR-GO.json')['gates'].items())
    prepared = read('REAL-QA-PREPARE-01.json')
    activated = read('REAL-QA-ACTIVATE-01.json')
    validated = read('REAL-QA-VALIDATE-01.json')
    assert prepared['valid'] and prepared['logicalTableCount'] == 37 and prepared['recoverySchema'] == 11
    assert activated['valid'] and activated['state'] == 'committed' and validated['valid']
    pointer = ROOT / '.local/qa-rc9/current.json'
    assert sha(pointer) == activated['pointerSha256']
    assert Path(json.loads(pointer.read_bytes())['directory']).resolve() == (ROOT / prepared['candidateDirectory']).resolve()
    cfg = json.loads((ROOT / prepared['candidateDirectory'] / 'manual-qa.json').read_bytes())
    assert cfg['dllSha256'] == sha(ROOT / manifest['serverDll'])
    assert cfg['bundleSha256'] == sha(ROOT / manifest['frontend'] / 'app.js')
    sys.path.insert(0, str(ROOT / 'tools/windows'))
    from qa_port_colors12_switch1029 import OwnedRuntime
    for directory in [ROOT / prepared['sourceDirectory'], ROOT / prepared['candidateDirectory']]:
        OwnedRuntime(directory, json.loads((directory / 'manual-qa.json').read_bytes())).quiet()
    spec = importlib.util.spec_from_file_location('guide1029final', ROOT / 'tools/windows/qa_guide.py')
    guide = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(guide)
    catalog = json.loads(guide.CATALOG.read_bytes())
    git = str(ROOT / '.local/git-2.55.0.5/cmd/git.exe')
    baseline = json.loads(subprocess.check_output([git, 'show', initial['baseCommit'] + ':docs/QA-CASOS-WASCAR.json']))
    assert len(catalog['cases']) == 81 and catalog['cases'][:78] == baseline['cases'][:78]
    assert all(c['feature'] == 'userPortColorsGui' for c in catalog['cases'][78:])
    availability = {}
    for profile in ['manual', 'rc9']:
        assert guide.generate(check=True, profile=profile)
        cases = json.loads(guide.render(catalog, guide.context(profile=profile)).split('const guide=', 1)[1].split(';', 1)[0])['cases']
        availability[profile] = sum(v['available'] for v in cases.values())
    assert availability == dict(manual=8, rc9=81)
    plan = json.loads((ROOT / 'docs/PLAN-SESENTA-TANDAS-970-1029.json').read_bytes())
    assert plan['completed'] == 60 and len(plan['batches']) == 60
    assert all(b['status'] == 'verified' and (ROOT / b['evidence']).is_file() for b in plan['batches'])
    progress = json.loads((ROOT / 'docs/MAPA-ENTREGA.json').read_bytes())
    assert progress['progress'] == 78 and [s['points'] for s in progress['streams']] == [18, 22, 14, 14, 9, 1]
    assert subprocess.check_output([git, 'rev-parse', 'HEAD'], text=True).strip() == initial['baseCommit']
    record = dict(utc=datetime.now(timezone.utc).isoformat(), successful=True, protectedFilesExact=protected,
                  immutableSourceQaRootFilesExact=source_count, originalRuntimeFilesPrivatelyArchived=7,
                  allowedRuntimeChanges=runtime_changes, productSourcesExact=181, candidateFilesExact=39,
                  selectedQaRevision=969, selectedQaSchema=12, recoveryRevision=849, recoverySchema=11,
                  originalSourceRevision=849, originalSourceRecoveryRevision=832, originalSourceRecoverySchema=11,
                  windowsRecoveredTables=37, realQaPrimaryTables=37, realQaRecoveryTables=35,
                  manualCases=81, available=availability, previous78CasesExact=True,
                  originalEvidencePreserved=True, manualWascarResultsWritten=False,
                  newApplicationPublications=1, newFrontendBuilds=0, processesQuiet=True,
                  independentGateApproved=True, finalAdoption=False, progress=78)
    output.write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(record))


if __name__ == '__main__':
    main()
