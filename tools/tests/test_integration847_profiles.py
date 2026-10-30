"""New closed RC9 Excel832/schema11 profile checks. Read-only application inputs; no DB/install."""
import argparse,hashlib,importlib.util,json,os,platform,subprocess,sys,tempfile,time,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('offline847_builder',ROOT/'tools/package_offline_bundle.py')
builder=importlib.util.module_from_spec(spec);sys.modules[spec.name]=builder;spec.loader.exec_module(builder)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
PS=Path(os.environ['SystemRoot'])/'System32/WindowsPowerShell/v1.0/powershell.exe'
E=ROOT/'evidence/s1-20261018'
MANIFESTS=[ROOT/'evidence/s1-20261017/treinta-tandas-308-337/CANDIDATA337.json',ROOT/'evidence/s1-20261017/treinta-tandas-368-397/CANDIDATA397.json',
 E/'sesenta-tandas-473-532/CANDIDATA532-FINAL03.json',E/'sesenta-tandas-533-592/CANDIDATA592-FINAL02.json',
 E/'sesenta-tandas-653-712/CANDIDATA712-FINAL02.json',E/'sesenta-tandas-773-832/CANDIDATA832-02.json']
CALLS=[]
q=lambda x:"'"+str(x).replace("'","''")+"'"
def run(text):
    env={k:v for k,v in os.environ.items() if k.upper()!='PSMODULEPATH'}
    p=subprocess.run([str(PS),'-NoLogo','-NoProfile','-NonInteractive','-Command',text],capture_output=True,
        text=True,encoding='utf-8-sig',env=env,timeout=45,creationflags=0x08000000)
    CALLS.append(dict(exitCode=p.returncode,stdout=p.stdout,stderr=p.stderr))
    return p
class Profiles847(unittest.TestCase):
    def test_01_producer_profiles_and_exact_artifacts(self):
        self.assertEqual(len(builder.APPLICATION_PROFILES),6)
        for path in MANIFESTS:
            payload,candidate=builder.collect_application(path,sha(path));m=json.loads(path.read_bytes())
            self.assertEqual(builder.application_schema(sha(path)),m['schema'])
            self.assertEqual(len(payload)-1,sum(len(v) for v in m['distributions'].values()))
        with self.assertRaisesRegex(builder.BundleError,'application_pin_mismatch'):
            builder.application_schema('0'*64)
        m=json.loads(MANIFESTS[-1].read_bytes());self.assertEqual(m['schema'],11)
        self.assertEqual(m['fileCount'],38);self.assertEqual(m['totalBytes'],7108267)
        self.assertEqual(builder.VERSIONS,dict(schema=9,dotnetRuntime='10.0.12',postgresql='17.11',vcRedist='14.51.36247.0',vcRuntimeMinimum='14.44.35211.0'))

    def test_02_native_closed_profiles_readiness_and_syntax(self):
        names=['RackClick.OfflineBundle.ps1','Test-ServerDistribution.ps1','RackClick.Stage.ps1',
               'Start-RackClickLabInstance.ps1','New-RackClickRecoveredInstance.ps1']
        paths=[ROOT/'tools/windows'/n for n in names]
        script=f". {q(paths[0])};$errors=@();foreach($p in @({','.join(q(p) for p in paths)})){{"+"$tokens=$null;$parse=$null;$null=[Management.Automation.Language.Parser]::ParseFile($p,[ref]$tokens,[ref]$parse);$errors+=@($parse)};"
        script+="$values=@();foreach($pin in @("+','.join(q(sha(p)) for p in MANIFESTS)+")){$values+=Get-OfflineBundleApplicationProfile $pin};$closed=$false;try{Get-OfflineBundleApplicationProfile ('0'*64)}catch{$closed=$true};"
        script+=f"$ast=[Management.Automation.Language.Parser]::ParseFile({q(paths[3])},[ref]$null,[ref]$null);"
        script+="$f=$ast.Find({param($n)$n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -ceq 'Test-LauncherReadyBody'},$true);Invoke-Expression $f.Extent.Text;"
        script+="@{errors=$errors.Count;profiles=$values;closed=$closed;readiness=@((Test-LauncherReadyBody ([pscustomobject]@{status='ready';schemaVersion=11}) 11),(Test-LauncherReadyBody ([pscustomobject]@{status='ready';schemaVersion=10}) 11),(Test-LauncherReadyBody ([pscustomobject]@{schemaVersion=11}) 11))}|ConvertTo-Json -Depth 6 -Compress"
        p=run(script);self.assertEqual(p.returncode,0,p.stderr);self.assertFalse(p.stderr)
        value=json.loads(p.stdout);self.assertEqual(value['errors'],0);self.assertTrue(value['closed'])
        self.assertEqual([x['name'] for x in value['profiles']],['337','397','532','592','712','832'])
        self.assertEqual(value['profiles'][-1],dict(name='832',server=20,frontend=18,bytes=7108267))
        self.assertEqual(value['readiness'],[True,False,False])

    def test_03_native_integrity_exact_pin_and_forged_schema_rejection(self):
        path=MANIFESTS[-1];m=json.loads(path.read_bytes());candidate=ROOT/m['candidateDirectory']
        tool=ROOT/'tools/windows/Test-ServerDistribution.ps1'
        def check(p,digest):
            result=run(f'& {q(tool)} -ManifestPath {q(p)} -ExpectedManifestSha256 {q(digest)} -ServerPath {q(candidate/"server")} -FrontendPath {q(candidate/"frontend")};exit $LASTEXITCODE')
            self.assertFalse(result.stderr);return result,json.loads(result.stdout)
        p,value=check(path,sha(path));self.assertEqual(p.returncode,0);self.assertTrue(value['valid'])
        self.assertEqual((value['verifiedFiles'],value['serverFiles'],value['frontendFiles']),(38,20,18))
        stage=ROOT/'tools/windows/RackClick.Stage.ps1'
        p=run(f'. {q(stage)};Invoke-StageIntegrity {q(path)} {q(sha(path))} {q(candidate/"server")} {q(candidate/"frontend")}|ConvertTo-Json -Compress')
        self.assertEqual(p.returncode,0,p.stderr);self.assertFalse(p.stderr);self.assertEqual(json.loads(p.stdout)['verifiedFiles'],38)
        with tempfile.TemporaryDirectory(prefix='rackclick847-profile-') as tmp:
            forged=Path(tmp)/'manifest.json';m['schema']=12;forged.write_text(json.dumps(m),encoding='utf-8')
            p,value=check(forged,sha(forged));self.assertEqual(p.returncode,2);self.assertEqual(value['code'],'manifest_distribution_unsupported')
            m['schema']=11;m['unreviewed']=True;forged.write_text(json.dumps(m),encoding='utf-8')
            p,value=check(forged,sha(forged));self.assertEqual(p.returncode,2);self.assertEqual(value['code'],'manifest_distribution_unsupported')
            del m['unreviewed'];del m['distributions']['server']['database/011-user-preferences.sql'];forged.write_text(json.dumps(m),encoding='utf-8')
            p,value=check(forged,sha(forged));self.assertEqual(p.returncode,2);self.assertEqual(value['code'],'manifest_distribution_unsupported')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    sources=[Path(__file__),ROOT/'tools/package_offline_bundle.py']+[ROOT/'tools/windows'/n for n in ['RackClick.OfflineBundle.ps1','Test-ServerDistribution.ps1','RackClick.Stage.ps1','Start-RackClickLabInstance.ps1','New-RackClickRecoveredInstance.ps1']]+MANIFESTS
    guards={p.relative_to(ROOT).as_posix():sha(p) for p in sources};started=time.monotonic()
    with (a.output/'tests.log').open('x',encoding='utf-8') as log:r=unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Profiles847))
    report=dict(platform=platform.platform(),testsRun=r.testsRun,successful=r.wasSuccessful(),failures=len(r.failures),errors=len(r.errors),seconds=round(time.monotonic()-started,3),sources=guards,sourcesUnchanged=all(sha(ROOT/p)==h for p,h in guards.items()),calls=CALLS,actualQaAccessed=False,postgresExecuted=False)
    (a.output/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:report[k] for k in ['testsRun','successful','seconds','sourcesUnchanged']}));return 0 if r.wasSuccessful() and report['sourcesUnchanged'] else 1
if __name__=='__main__':raise SystemExit(main())
