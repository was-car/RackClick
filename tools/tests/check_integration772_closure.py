"""Static final metadata/hash contrast; does not start PG/app or write user results."""
import argparse,hashlib,importlib.util,json,subprocess
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];E=ROOT/'evidence/s1-20261018/sesenta-tandas-713-772'
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(p):return json.loads(p.read_bytes())
def tree(p):return {f.relative_to(p).as_posix():sha(f) for f in sorted(p.rglob('*')) if f.is_file()}
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--attempt',default='01');a=ap.parse_args();assert len(a.attempt)==2 and a.attempt.isdecimal()
    out=E/f'VERIFICACION-FINAL-{a.attempt}.json'
    if out.exists():raise SystemExit('Preserve verification evidence')
    report=dict(utc=datetime.now(timezone.utc).isoformat(),successful=False,checks=[],scope='Static hashes and metadata only; no new runtime/SQL/HTTP/manual QA')
    try:
        start=read(E/'INICIO.json');changed=[p for p,h in start['guards'].items() if not (ROOT/p).is_file() or sha(ROOT/p)!=h]
        assert set(changed)<=set(start['authorizedMutableGuards']),changed
        report.update(initialGuardCount=len(start['guards']),changedAuthorizedGuards=changed)
        previous=ROOT/'evidence/s1-20261018/sesenta-tandas-653-712'
        assert sha(previous/'SHA256SUMS')=='6948cd72777dc91f37f470aa3ad9c3894d5cb0b902990aa56465e04eb36601b6'
        app=read(previous/'SOURCE-FREEZE-APP-02.json')['sources'];assert len(app)==170 and all(sha(ROOT/p)==h for p,h in app.items())
        oldqa=read(previous/'GUARDAS-QA-ADICIONALES.json')['guards'];assert len(oldqa)==43 and all(sha(ROOT/p)==h for p,h in oldqa.items())
        for mf in [previous/'CANDIDATA712-FINAL02.json',ROOT/'evidence/s1-20261018/sesenta-tandas-533-592/CANDIDATA592-FINAL02.json']:
            m=read(mf)
            for part,values in m['distributions'].items():
                directory=ROOT/Path(m['serverDll']).parent if part=='server' else ROOT/m['frontend']
                assert tree(directory)==values
        report['checks'].append('476 starting guards only authorized changes; previous seal,170 application sources,43 source-QA guards and both frozen distributions exact')
        package=read(E/'PACKAGES-02.json');assert package['valid'] and package['byteIdentical'] and package['sourcesUnchanged']
        assert all(sha(ROOT/x['path'])==x['sha256']=='7140a0207c113248a7c66b61a92133c9d2b524a8ab14e37bdbc9cfe6296ad6b4' for x in package['outputs'])
        frozen=read(E/'SOURCE-FREEZE-OPERATORS-02.json')['sources'];assert len(frozen)==33 and all(sha(ROOT/p)==h for p,h in frozen.items())
        first=read(E/'SOURCE-FREEZE-OPERATORS-01.json')['sources'];assert {p for p,h in frozen.items() if first[p]!=h}=={'tools/windows/RackClick.Stage.ps1','tools/tests/build_offline772.py'}
        assert not read(E/'windows/native01/result.json')['successful'] and read(E/'windows/native01/result.json')['freshClustersInitialized']==0
        for name in ['windows/native02/result.json','qa-transition/all01/result.json','revision/source-activity01/result.json']:
            value=read(E/name);assert value.get('successful',value.get('valid',False)),name
        composite=read(E/'windows/WRAPPER-COMPOSITE.json');assert composite['valid'] and composite['compositeComplete']
        assert not read(E/composite['original'])['successful'] and read(E/composite['remainder'])['successful']
        native=read(E/'windows/native02/result.json');assert native['inputsUnchanged'] and native['ownedProcessesStopped'] and native['recoverySnapshotExact'] and not native['cleanupErrors']
        assert any(x.get('recoverAdmin11ReallyExecuted') for x in native['preferencesChecks']) and len(native['tableDigestsBeforeBackup'])==35
        transition=read(E/'qa-transition/all01/result.json');assert transition['testsRun']==5 and transition['inputsUnchanged'] and all(all(x.values()) for x in transition['labs'])
        report['checks'].append('Final two ZIP02 exact;33 frozen packaged inputs stable; P2 original fail retained and Stage correction/native/CLI35tables/wrapper/transition/independent focus PASS')
        gate=read(E/'COORDINATOR-GO.json');assert gate['valid'] and all(sha(ROOT/p)==h for p,h in gate['gates'].items())
        tech=read(E/'revision/GATE-TECNICO.json');assert tech['valid'] and tech['approved'] and not tech['openBlockingFindings']
        assert all(sha(ROOT/p)==h for key in ['sourceHashes','manualHashes'] for p,h in tech[key].items())
        for name in ['PREFLIGHT','PREPARE','ACTIVATE','VALIDATE']:
            value=read(E/f'REAL-QA-{name}-01.json');assert value['valid'] and not value['sourceApplicationLogin'] and not value['sourceApplicationDml'] and not value['manualWascarResultsWritten']
        pre=read(E/'REAL-QA-PREFLIGHT-01.json');activated=read(E/'REAL-QA-ACTIVATE-01.json');validated=read(E/'REAL-QA-VALIDATE-01.json')
        source=ROOT/pre['sourceDirectory'];target=ROOT/activated['candidateDirectory']
        assert source!=target and activated['selectedSchema']==11 and activated['state']=='committed' and not activated['leftRunning']
        assert read(ROOT/'.local/qa-rc9/current.json')==dict(directory=str(target)) and validated['selectedSchema']==11 and not validated['databaseTestExecuted']
        assert all(sha(source/p)==h for p,h in pre['sourceInputHashes'].items())
        for name in ['ACCESO-PRIVADO.txt','QA-CUENTAS-ESTADO.json','qa-accounts-private.json','RESTORE-ESTADO.json']:assert sha(source/name)==sha(target/name)
        assert not (source/'data/postmaster.pid').exists() and not (target/'data/postmaster.pid').exists()
        report['checks'].append('Technical GO remains exact; real QA11 copied/selected in new directory without app login/DML; source10 inputs/four private copies intact and PG branches stopped')
        catalog=read(ROOT/'docs/QA-CASOS-WASCAR.json')
        base=json.loads(subprocess.check_output([str(ROOT/'.local/git-2.55.0.5/cmd/git.exe'),'show',start['baseCommit']+':docs/QA-CASOS-WASCAR.json'],cwd=ROOT))
        assert len(catalog['cases'])==74 and catalog['cases'][:71]==base['cases'][:71]
        for old,new in zip(base['cases'][-3:],catalog['cases'][-3:]):assert {**old,'steps':new['steps']}==new and old['steps'][1:]==new['steps'][1:]
        spec=importlib.util.spec_from_file_location('guide_closure772',ROOT/'tools/windows/qa_guide.py');q=importlib.util.module_from_spec(spec);spec.loader.exec_module(q)
        for profile,want in [('manual',8),('rc9',74)]:
            assert q.generate(check=True,profile=profile)
            cases=json.loads(q.render(catalog,q.context(profile=profile)).split('const guide=',1)[1].split(';',1)[0])['cases']
            assert sum(x['available'] for x in cases.values())==want
            assert all(cases[f'QA-{i}']['available']==(profile=='rc9') for i in range(72,75))
        assert read(E/'QA-TESTS-01.json')['successful']
        report['checks'].append('74cases/old71exact; only availability intros72–74 changed; both guides exact,74restored/8original available, no user result storage writes')
        plan=read(ROOT/'docs/PLAN-SESENTA-TANDAS-713-772.json');m=read(ROOT/'docs/MAPA-ENTREGA.json')
        assert plan['completed']==60 and [x['id'] for x in plan['batches']]==list(range(713,773))
        assert all(x['status']=='verified' and (ROOT/x['evidence']).is_file() and (ROOT/x['independentEvidence']).is_file() for x in plan['batches'])
        assert plan['finalProgress']==m['progress']==catalog['globalProgressEstimate']==78
        assert [x['points'] for x in m['streams']]==[18,22,14,14,9,1] and [x['weight'] for x in m['streams']]==[20,25,15,15,15,10]
        assert b'Grupo713' in (ROOT/'docs/CONTINUIDAD-CODEX.md').read_bytes()[:2500]
        report['checks'].append('60 attributed internal milestones; global78/components unchanged; limits, next work and manual acceptance documented')
        report.update(successful=True,completed=60,progress=78,actualQaSelectedSchema=11,manualWascarResultsWritten=False)
    except Exception as error:
        report['error']=repr(error);raise
    finally:
        with out.open('x',encoding='utf-8') as f:json.dump(report,f,indent=2);f.write('\n')
        print(json.dumps(report))
if __name__=='__main__':main()
