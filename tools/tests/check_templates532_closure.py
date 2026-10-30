"""Read-only final metadata/identity checks; no HTTP, login, SQL or native suite."""
import argparse
import hashlib
import importlib.util
import json
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
E = ROOT / 'evidence/s1-20261018/sesenta-tandas-473-532'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def read(name):
    return json.loads((E / name).read_bytes())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit('Preserve prior verification evidence; choose a new output')
    checks = {}

    def check(name, value):
        checks[name] = bool(value)

    start = read('INICIO.json')
    mutable = {'GUIA-QA-RESTAURADO.html', 'GUIA-QA-WASCAR.html',
               'development/server/src/RackClick.Server/Program.cs', 'docs/QA-CASOS-WASCAR.json'}
    mutations = [p for p, h in start['guards'].items() if sha(ROOT / p) != h]
    check('169 guards: only four authorized public files changed; 165 historical/pin guards exact',
          len(start['guards']) == 169 and set(mutations) == mutable)
    frozen = read('SOURCE-FREEZE-APP-03.json')['sources']
    check('153 frozen product and focal test sources exact',
          len(frozen) == 153 and all(sha(ROOT / p) == h for p, h in frozen.items()))
    operators = read('SOURCE-FREEZE-OPERATORS-03.json')['sources']
    harness = 'development/server/tests/test_offline_configuration532.py'
    changed = [p for p, h in operators.items() if sha(ROOT / p) != h]
    check('38 package sources: only unbundled native test changed and its original preserved',
          len(operators) == 38 and changed == [harness]
          and sha(E / 'packaging/HARNESS-NATIVE03.py') == operators[harness])
    m = read('CANDIDATA532-FINAL03.json')
    directory = ROOT / m['candidateDirectory']
    trees = {part: {p.relative_to(directory / part).as_posix(): sha(p)
                    for p in (directory / part).rglob('*') if p.is_file()}
             for part in ['server', 'frontend']}
    check('FINAL03 exact manifest and 36 files',
          sha(E / 'CANDIDATA532-FINAL03.json') == 'c818294e27a40c94fe2ebf603709c94263820af1facca9a7d5c288cb70e8158e'
          and trees == m['distributions'] and sum(map(len, trees.values())) == m['fileCount'] == 36)
    check('FINAL03 exact 6794984 bytes', m['totalBytes'] == 6794984
          and sum(p.stat().st_size for part in trees for p in (directory / part).rglob('*') if p.is_file()) == 6794984)
    old = json.loads((ROOT / 'evidence/s1-20261018/cuarenta-y-cinco-tandas-428-472/CANDIDATA472.json').read_bytes())
    check('SQL001-009 and 17 non-app frontend files unchanged',
          sum(p.startswith('database/') for p in trees['server']) == 9
          and all(old['distributions']['server'][p] == h for p, h in trees['server'].items() if p.startswith('database/'))
          and all(old['distributions']['frontend'][p] == h for p, h in trees['frontend'].items() if p != 'app.js'))
    second = read('CANDIDATA532-FINAL02.json')
    check('FINAL02 and FINAL03 server identical; only frontend app differs',
          second['distributions']['server'] == trees['server']
          and [p for p, h in trees['frontend'].items() if second['distributions']['frontend'][p] != h] == ['app.js'])
    git = str(ROOT / '.local/git-2.55.0.5/cmd/git.exe')
    domain_source = subprocess.check_output([git, 'diff', start['baseCommit'], '--name-only', '--', 'development/server/src/RackClick.Domain'], cwd=ROOT)
    check('Domain source unchanged; assembly embeds current build base revision',
          not domain_source.strip() and start['baseCommit'].encode() in (directory / 'server/RackClick.Domain.dll').read_bytes())

    for folder, count in [('backend/postgres-focus02', 1), ('legacy/rename01', 1),
                          ('legacy/capture-instantiate01', 2), ('revision/pg-own-02-remaining', 1)]:
        d = read(folder + '/result.json')
        check(folder + ' pass, stopped, isolated; focal attribution retained',
              d['successful'] and d['testsRun'] == count and d['labStopped'] and d['serversStopped']
              and d['actualQaOpened'] is False and d['historicalResultsReused'] is False)
    check('initial backend failure log retained without fabricated result',
          (E / 'backend/postgres01/tests.log').is_file() and not (E / 'backend/postgres01/result.json').exists())
    gui = read('frontend/gui02/fixture.json')
    check('functional Edge/PG FINAL02 preserved and stopped', gui['result'] == 'PASS'
          and all(gui[k] for k in ['inputsUnchanged', 'labStopped', 'serversStopped', 'originalTemplateExact', 'serverRestartPersistence'])
          and gui['realQaAccessed'] is False)
    layout = read('frontend/gui-layout04/browser.json')
    check('FINAL03 visual focus honest: mock HTTP, no PG/application writes', layout['result'] == 'PASS'
          and layout['postgresqlExecuted'] is False and layout['applicationWrites'] == 0
          and layout['frontendSha256'] == trees['frontend']['app.js'] and layout['frontendUnchanged'])
    update = read('integration/native01/result.json')
    check('native updater fixture success and exact FINAL02 attribution',
          update['successful'] and update['testsRun'] == 1 and update['targetManifestSha256'] == sha(E/'CANDIDATA532-FINAL02.json')
          and update['inputsUnchanged'] and update['actualQaAccessed'] is False)
    package = read('PACKAGES-03.json')
    check('two ZIPs byte-identical, exact final03 hash and bytes', package['valid'] and package['byteIdentical']
          and package['sourceManifestSha256'] == sha(E/'CANDIDATA532-FINAL03.json')
          and len(package['outputs']) == 2 and all(sha(ROOT / x['path']) == x['sha256']
          and (ROOT / x['path']).stat().st_size == x['bytes'] == 117055538 for x in package['outputs']))
    native = read('packaging/native04/result.json')
    check('new native install/backup/recovery: two clusters, configuration receipts and no residual processes',
          native['successful'] and native['testsRun'] == 1 and native['freshClustersInitialized'] == 2
          and native['inputsUnchanged'] and native['ownedProcessesStopped'] and native['systemCrtDllsAndX64RegistryUnchanged']
          and not native['cleanupErrors'] and native['archiveSha256'] == package['outputs'][0]['sha256']
          and {x['stage'] for x in native['configurationChecks']} == {'before_backup', 'after_recovery'})
    check('native03 FAIL retained as failure', not read('packaging/native03/result.json')['successful'])

    selected = read('QA-SELECTED-03.json')
    pointer = ROOT / '.local/qa-rc9/current.json'
    profile = Path(json.loads(pointer.read_bytes())['directory'])
    check('real selection committed, quiet, three fields, previous retained and no application login/DML',
          selected['state'] == 'committed' and selected['activationConfirmed'] and selected['leftRunning'] is False
          and selected['pointerUnchanged'] and selected['privateInputsUnchanged'] and selected['old185ArtifactsRetained']
          and selected['allRowsHistoryOidAndActivityVerifiedByOperator']
          and set(selected['changedFields']) == {'artifactDirectory', 'dllSha256', 'bundleSha256'}
          and selected['applicationLoginPlanned'] is False and selected['applicationDmlPlanned'] is False
          and selected['wascarResultsWritten'] is False and sha(pointer) == selected['pointerSha256']
          and sha(profile / 'manual-qa.json') == selected['finalConfigurationSha256']
          and all(sha(profile / p) == h for p, h in selected['privateInputs'].items()))
    catalog = json.loads((ROOT / 'docs/QA-CASOS-WASCAR.json').read_bytes())
    previous = json.loads(subprocess.check_output([git, 'show', start['baseCommit'] + ':docs/QA-CASOS-WASCAR.json'], cwd=ROOT))
    check('65 prior QA cases exact; 68 total and displayed scope estimate77',
          catalog['cases'][:65] == previous['cases'] and len(catalog['cases']) == 68 and catalog['globalProgressEstimate'] == 77)
    spec = importlib.util.spec_from_file_location('guide', ROOT/'tools/windows/qa_guide.py')
    guide = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(guide)
    availability = {}
    for name, count in [('manual', 8), ('rc9', 68)]:
        html = guide.render(catalog, guide.context(profile=name))
        data = json.loads(html.split('const guide=', 1)[1].split(';', 1)[0])
        availability[name] = sum(x['available'] for x in data['cases'].values())
        check(name + ' generated guide exact and real availability ' + str(count),
              guide.guide_path(name).read_text(encoding='utf-8') == html and availability[name] == count)
    plan = json.loads((ROOT / 'docs/PLAN-SESENTA-TANDAS-473-532.json').read_bytes())
    check('60 milestones with real evidence and separate review', plan['completed'] == 60
          and [x['id'] for x in plan['batches']] == list(range(473, 533))
          and all(x['status'] == 'verified' and (ROOT/x['evidence']).is_file()
          and (ROOT/x['independentEvidence']).is_file() for x in plan['batches']))
    mp = json.loads((ROOT / 'docs/MAPA-ENTREGA.json').read_bytes())
    check('77 weighted scope points; inventory21 only and fixed total100',
          plan['finalProgress'] == mp['progress'] == 77 and [s['points'] for s in mp['streams']] == [18, 21, 14, 14, 9, 1]
          and sum(s['weight'] for s in mp['streams']) == 100)
    progress = (ROOT / 'docs/PROGRESO-GLOBAL.md').read_text(encoding='utf-8')
    check('current prose table agrees with77 and leaves sharing/publication pending',
          '| Jerarquía e inventario compartido | 25 | 21 |' in progress
          and '| Instalación Windows y recuperación operativa | 15 | 9 |' in progress
          and '| **Total** | **100** | **77** |' in progress
          and 'Faltan compartición/publicación' in progress)
    report = dict(utc=datetime.now(timezone.utc).isoformat(), platform=platform.platform(),
                  checks=checks, passed=sum(checks.values()), total=len(checks),
                  authorizedMutableGuards=mutations, immutableGuardCount=165,
                  guidesAvailable=availability, result='PASS' if all(checks.values()) else 'FAIL',
                  scope='Read-only file, SHA and metadata checks; no new PG, browser, installation or manual Wascar QA.')
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if all(checks.values()) else 1


if __name__ == '__main__':
    raise SystemExit(main())
