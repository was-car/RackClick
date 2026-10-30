"""Read-only final contrast. No HTTP, SQL, build or QA application access."""
import hashlib
import importlib.util
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
E = ROOT / 'evidence/s1-20261018/sesenta-tandas-653-712'


def sha(p):
    with p.open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def read(p):
    return json.loads(p.read_bytes())


def tree(p):
    return {f.relative_to(p).as_posix(): sha(f) for f in sorted(p.rglob('*')) if f.is_file()}


def main():
    output = E / 'VERIFICACION-FINAL.json'
    if output.exists():
        raise SystemExit('Preserve previous verification; choose a new evidence filename before repeating')
    report = dict(utc=datetime.now(timezone.utc).isoformat(), successful=False,
                  scope='Static final contrast only; no HTTP/SQL/QA runtime/manual results access', checks=[])
    try:
        start = read(E / 'INICIO.json')
        allowed = set(start['authorizedMutableGuards'])
        for p in ['ALCANCE-ADICIONAL.json', 'ALCANCE-GUIA-712.json']:
            allowed.update(read(E / p)['authorizedMutableGuardsAdditional'])
        changed = [p for p, h in start['guards'].items() if not (ROOT / p).is_file() or sha(ROOT / p) != h]
        assert set(changed) <= allowed, changed
        extra = read(E / 'GUARDAS-QA-ADICIONALES.json')['guards']
        assert len(extra) == 43 and all(sha(ROOT / p) == h for p, h in extra.items())
        report.update(initialGuardCount=len(start['guards']), authorizedChangedGuards=changed,
                      extraActualQaGuardsUnchanged=len(extra))
        report['checks'].append('Original guards differ only in authorized files; 43 additional QA artifact/credential hashes unchanged')
        previous = ROOT / 'evidence/s1-20261018/sesenta-tandas-593-652'
        assert sha(previous / 'SHA256SUMS') == '30378a7e3583cfb946810b068974c331eb3828f8656f1b625321f3c430077843'
        operators = read(previous / 'SOURCE-FREEZE-OPERATORS-03.json')['sources']
        assert len(operators) == 33 and all(sha(ROOT / p) == h for p, h in operators.items())
        zips = read(previous / 'PACKAGES-03.json')['outputs']
        assert len(zips) == 2 and all(sha(ROOT / z['path']) == 'b27aafb92e3523e7d10e9813a0f30d0bc34387b939dc2cf74d53dc02483e8ec1' for z in zips)
        report['checks'].append('Previous evidence seal, 33 frozen operator/manual sources and two ZIP652 unchanged')
        pointer = read(ROOT / '.local/qa-rc9/current.json')
        assert Path(pointer['directory']).resolve() == (ROOT / start['sourceQaDirectory']).resolve()
        cfg = read(Path(pointer['directory']) / 'manual-qa.json')
        old = read(ROOT / 'evidence/s1-20261018/sesenta-tandas-533-592/CANDIDATA592-FINAL02.json')
        assert cfg['dllSha256'] == old['distributions']['server']['RackClick.Server.dll']
        assert cfg['bundleSha256'] == old['distributions']['frontend']['app.js']
        report['checks'].append('Selected QA pointer/config still592/schema10; no selection or runtime access')
        final = read(E / 'CANDIDATA712-FINAL02.json')
        assert sha(E / 'CANDIDATA712-FINAL02.json') == 'f256c0fc5c99c4ff24c05e36a7eddc0ed2da9d66979db3502e0c4d606ac881cd'
        assert (final['schema'], final['fileCount'], final['totalBytes']) == (11, 38, 7028507)
        candidate = ROOT / final['candidateDirectory']
        for part, hashes in final['distributions'].items():
            assert tree(candidate / part) == hashes, part
        assert sum(p.stat().st_size for p in candidate.rglob('*') if p.is_file()) == final['totalBytes']
        sources = read(E / 'SOURCE-FREEZE-APP-02.json')['sources']
        assert len(sources) == 170 and all(sha(ROOT / p) == h for p, h in sources.items())
        initial = read(E / 'CANDIDATA712.json')
        assert initial['distributions']['server'] == final['distributions']['server']
        assert [p for p, h in final['distributions']['frontend'].items() if initial['distributions']['frontend'][p] != h] == ['app.js']
        assert all(h == old['distributions']['frontend'][p] for p, h in final['distributions']['frontend'].items() if p != 'app.js')
        assert all(h == final['distributions']['server'][p] for p, h in old['distributions']['server'].items() if p.startswith('database/'))
        report['checks'].append('FINAL02: schema11, 38 files/7028507 bytes,170 sources exact; all20 server files unchanged from01,17 frontend assets and SQL001–010 exact')
        for path, count in [('backend/postgres01/result.json', 8), ('native-backup01/result.json', 1)]:
            result = read(E / path)
            assert result['successful'] and result['testsRun'] == count and result['labStopped'] and result['serversStopped']
            assert result['sourcesUnchanged']
        assert read(E / 'native-backup01/result.json')['observations']['tableCount'] == 35
        for path in ['frontend/edge-02/fixture.json', 'frontend/edge-03-visual-final02/fixture.json', 'legacy-smoke-final02/fixture.json']:
            result = read(E / path)
            assert result['result'] == 'PASS' and result['labStopped'] and result['inputsUnchanged']
        assert read(E / 'BUILD-01.json')['successful'] and read(E / 'BUILD-02.json')['successful']
        seal_path = E / 'revision/SEAL-REVISION.json'
        assert sha(seal_path) == '385bf3b486d32ebd14fac91fc3df48e5aedbb4b04ae6f8549e52789f21e4ea3d'
        seal = read(seal_path)
        assert len(seal['files']) == 14 and seal['ownPostgresFocusPassed'] and seal['ownNodeFocusPassed']
        assert all(sha(E / 'revision' / p) == h for p, h in seal['files'].items())
        report['checks'].append('Author suites PASS/stopped; independent14-file seal unchanged; own PG1/Node1 kept separate')
        catalog = read(ROOT / 'docs/QA-CASOS-WASCAR.json')
        base = json.loads(subprocess.check_output([str(ROOT / '.local/git-2.55.0.5/cmd/git.exe'), 'show', start['baseCommit'] + ':docs/QA-CASOS-WASCAR.json'], cwd=ROOT))
        assert len(catalog['cases']) == 74 and catalog['cases'][:71] == base['cases']
        pair = dict(dll=final['distributions']['server']['RackClick.Server.dll'], bundle=final['distributions']['frontend']['app.js'])
        assert catalog['userPreferencesBuilds'] == [pair]
        spec = importlib.util.spec_from_file_location('qa_guide_closure712', ROOT / 'tools/windows/qa_guide.py')
        guide = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(guide)
        def cases(ctx):
            return json.loads(guide.render(catalog, ctx).split('const guide=', 1)[1].split(';', 1)[0])['cases']
        for profile, count in [('manual', 8), ('rc9', 71)]:
            current = cases(guide.context(profile=profile))
            assert sum(c['available'] for c in current.values()) == count
            assert all(not current[f'QA-{i}']['available'] for i in range(72, 75))
            assert guide.generate(check=True, profile=profile)
        future = dict(configured=True, roles=True, restored=True, origin='', **pair)
        assert all(cases(future)[f'QA-{i}']['available'] for i in range(72, 75))
        for wrong in [dict(dll='wrong'), dict(bundle='wrong'), dict(roles=False), dict(configured=False)]:
            assert all(not cases({**future, **wrong})[f'QA-{i}']['available'] for i in range(72, 75))
        qa = read(E / 'QA-TESTS-01.json')
        assert qa['successful'] and qa['testsRun'] == 38
        assert catalog['globalProgressEstimate'] == 78
        report['checks'].append('74cases, old71exact; guides exact; actual71/8 available,72–74disabled; future exact-pair/config/roles gates closed')
        plan = read(ROOT / 'docs/PLAN-SESENTA-TANDAS-653-712.json')
        assert plan['completed'] == 60 and plan['finalProgress'] == 78
        assert len(plan['batches']) == 60 and all(x['status'] == 'verified' and (ROOT / x['evidence']).is_file() for x in plan['batches'])
        m = read(ROOT / 'docs/MAPA-ENTREGA.json')
        assert m['progress'] == 78 and m['currentBatch']['completed'] == 60
        assert [s['points'] for s in m['streams']] == [18, 22, 14, 14, 9, 1]
        assert [s['weight'] for s in m['streams']] == [20, 25, 15, 15, 15, 10]
        assert b'Grupo653' in (ROOT / 'docs/CONTINUIDAD-CODEX.md').read_bytes()[:2500]
        report['checks'].append('60 attributed milestones closed; global78/components unchanged; development11/QA10/CLI11-pending limits documented')
        report.update(successful=True, actualQaRuntimeAccessed=False, manualWascarResultsWritten=False,
                      newCasesAvailableInCurrentQa=False, progress=78, completed=60)
    except Exception as error:
        report['error'] = repr(error)
        raise
    finally:
        with output.open('x', encoding='utf-8') as stream:
            json.dump(report, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
        print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
