"""Three bounded native checks for the closed palette969/schema12 Windows profile."""
import argparse,hashlib,importlib.util,json,os,platform,shutil,subprocess,sys,tempfile,time,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('offline1029_builder',ROOT/'tools/package_offline_bundle.py')
builder=importlib.util.module_from_spec(spec);sys.modules[spec.name]=builder;spec.loader.exec_module(builder)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
PS=Path(os.environ['SystemRoot'])/'System32/WindowsPowerShell/v1.0/powershell.exe'
E=ROOT/'evidence/s1-20261018'
MANIFESTS=[ROOT/'evidence/s1-20261017/treinta-tandas-308-337/CANDIDATA337.json',ROOT/'evidence/s1-20261017/treinta-tandas-368-397/CANDIDATA397.json',
 E/'sesenta-tandas-473-532/CANDIDATA532-FINAL03.json',E/'sesenta-tandas-533-592/CANDIDATA592-FINAL02.json',
 E/'sesenta-tandas-653-712/CANDIDATA712-FINAL02.json',E/'sesenta-tandas-773-832/CANDIDATA832-02.json',E/'tanda-849/CANDIDATA849.json',
 E/'sesenta-tandas-970-1029/CANDIDATA969-FIX02.json']
PIN='b589609154fed1567106ef0865972155258f0f5474128c73076f4697d43b8bda'
ORIGINAL=E/'sesenta-tandas-910-969/CANDIDATA969-01.json'
FAILED=E/'sesenta-tandas-970-1029/CANDIDATA969-WINDOWS.json'
CALLS=[]
q=lambda x:"'"+str(x).replace("'","''")+"'"
def run(text):
    env={k:v for k,v in os.environ.items() if k.upper()!='PSMODULEPATH'}
    p=subprocess.run([str(PS),'-NoLogo','-NoProfile','-NonInteractive','-Command',text],capture_output=True,
        text=True,encoding='utf-8-sig',env=env,timeout=45,creationflags=0x08000000)
    CALLS.append(dict(exitCode=p.returncode,stdout=p.stdout,stderr=p.stderr));return p
class Profiles1029(unittest.TestCase):
    def test_01_producer_eight_closed_profiles_and_original_exact(self):
        self.assertEqual(len(builder.APPLICATION_PROFILES),8)
        for path in MANIFESTS:
            payload,_=builder.collect_application(path,sha(path));m=json.loads(path.read_bytes())
            self.assertEqual(builder.application_schema(sha(path)),m['schema'])
            self.assertEqual(len(payload)-1,sum(len(v) for v in m['distributions'].values()))
        for pin in ['0'*64,sha(ORIGINAL),sha(FAILED)]:
            with self.assertRaisesRegex(builder.BundleError,'application_pin_mismatch'):builder.application_schema(pin)
        self.assertEqual(sha(ORIGINAL),'a74c88607a5471a19f317f685a6defbfa68f01f86bfd19789a01d1000c873030')
        original=json.loads(ORIGINAL.read_bytes());m=json.loads(MANIFESTS[-1].read_bytes())
        self.assertEqual(sha(FAILED),'1f651be9a69c5bb225928ebd948f02ad00b19f790bcce967715d4fcc0c1e99d2')
        self.assertEqual(m['distributions']['frontend'],original['distributions']['frontend']);self.assertEqual(sha(MANIFESTS[-1]),PIN)
        self.assertEqual(set(m['distributions']['server']),set(original['distributions']['server']))
        changed={n for n,h in m['distributions']['server'].items() if original['distributions']['server'][n]!=h}
        self.assertEqual(changed,{'RackClick.Server.dll','RackClick.Server.pdb','RackClick.Domain.dll','RackClick.Domain.pdb'})
        self.assertNotEqual(m['candidateDirectory'],original['candidateDirectory'])
        self.assertEqual((m['schema'],m['fileCount'],m['totalBytes']),(12,39,7037914))
        self.assertEqual(builder.VERSIONS,dict(schema=9,dotnetRuntime='10.0.12',postgresql='17.11',vcRedist='14.51.36247.0',vcRuntimeMinimum='14.44.35211.0'))

    def test_02_native_profiles_ps51_syntax_and_readiness(self):
        names=['RackClick.OfflineBundle.ps1','Test-ServerDistribution.ps1','RackClick.Stage.ps1','RackClick.Instance.ps1',
               'Start-RackClickLabInstance.ps1','New-RackClickRecoveredInstance.ps1']
        paths=[ROOT/'tools/windows'/n for n in names]
        script=f". {q(paths[0])};$errors=@();foreach($p in @({','.join(q(p) for p in paths)})){{"+"$tokens=$null;$parse=$null;$null=[Management.Automation.Language.Parser]::ParseFile($p,[ref]$tokens,[ref]$parse);$errors+=@($parse)};"
        script+="$values=@();foreach($pin in @("+','.join(q(sha(p)) for p in MANIFESTS)+")){$values+=Get-OfflineBundleApplicationProfile $pin};$closed=$false;try{Get-OfflineBundleApplicationProfile ('0'*64)}catch{$closed=$true};"
        script+=f"$ast=[Management.Automation.Language.Parser]::ParseFile({q(paths[4])},[ref]$null,[ref]$null);"
        script+="$f=$ast.Find({param($n)$n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -ceq 'Test-LauncherReadyBody'},$true);Invoke-Expression $f.Extent.Text;"
        script+="@{psVersion=$PSVersionTable.PSVersion.ToString();errors=$errors.Count;profiles=$values;closed=$closed;readiness=@((Test-LauncherReadyBody ([pscustomobject]@{status='ready';schemaVersion=12}) 12),(Test-LauncherReadyBody ([pscustomobject]@{status='ready';schemaVersion=11}) 12),(Test-LauncherReadyBody ([pscustomobject]@{schemaVersion=12}) 12))}|ConvertTo-Json -Depth 6 -Compress"
        p=run(script);self.assertEqual(p.returncode,0,p.stderr);self.assertFalse(p.stderr)
        value=json.loads(p.stdout);self.assertEqual(value['errors'],0);self.assertTrue(value['closed']);self.assertTrue(value['psVersion'].startswith('5.1.'))
        self.assertEqual([x['name'] for x in value['profiles']],['337','397','532','592','712','832','849','969'])
        self.assertEqual(value['profiles'][-1],dict(name='969',server=21,frontend=18,bytes=7037914));self.assertEqual(value['readiness'],[True,False,False])

    def test_03_native_distribution_stage_schema_sql012_hash_pin_negatives(self):
        path=MANIFESTS[-1];m=json.loads(path.read_bytes());candidate=ROOT/m['candidateDirectory'];tool=ROOT/'tools/windows/Test-ServerDistribution.ps1'
        def check(p,digest,root=candidate):
            result=run(f'& {q(tool)} -ManifestPath {q(p)} -ExpectedManifestSha256 {q(digest)} -ServerPath {q(root/"server")} -FrontendPath {q(root/"frontend")};exit $LASTEXITCODE')
            self.assertFalse(result.stderr);return result,json.loads(result.stdout)
        p,value=check(path,PIN);self.assertEqual(p.returncode,0);self.assertTrue(value['valid']);self.assertEqual((value['verifiedFiles'],value['serverFiles'],value['frontendFiles']),(39,21,18))
        p,value=check(FAILED,sha(FAILED));self.assertEqual(p.returncode,2);self.assertEqual(value['code'],'manifest_distribution_unsupported')
        stage=ROOT/'tools/windows/RackClick.Stage.ps1'
        with tempfile.TemporaryDirectory(prefix='rackclick1029-profile-') as tmp:
            tmp=Path(tmp);shutil.copy2(path,tmp/'manifest.json')
            p=run(f'. {q(stage)};$v=Invoke-StageIntegrity {q(path)} {q(PIN)} {q(candidate/"server")} {q(candidate/"frontend")};@{{files=$v.verifiedFiles;schema=(Get-StageSchema {q(tmp)})}}|ConvertTo-Json -Compress')
            self.assertEqual(p.returncode,0,p.stderr);self.assertFalse(p.stderr);self.assertEqual(json.loads(p.stdout),dict(files=39,schema=12))
            p,value=check(path,'0'*64);self.assertEqual(p.returncode,2);self.assertEqual(value['code'],'manifest_untrusted')
            forged=tmp/'forged.json';m['unreviewed']=True;forged.write_text(json.dumps(m),encoding='utf-8')
            p,value=check(forged,sha(forged));self.assertEqual(p.returncode,2);self.assertEqual(value['code'],'manifest_distribution_unsupported')
            del m['unreviewed'];del m['distributions']['server']['database/012-user-port-colors.sql'];forged.write_text(json.dumps(m),encoding='utf-8')
            p,value=check(forged,sha(forged));self.assertEqual(p.returncode,2);self.assertEqual(value['code'],'manifest_distribution_unsupported')
            copy=tmp/'candidate';shutil.copytree(candidate,copy);sql=copy/'server/database/012-user-port-colors.sql';sql.rename(sql.with_suffix('.missing'))
            p,value=check(path,PIN,copy);self.assertEqual(p.returncode,1);self.assertEqual(value['code'],'distribution_files_missing')
            sql.with_suffix('.missing').rename(sql);sql.write_bytes(sql.read_bytes()+b'\n-- tamper isolated fixture\n')
            p,value=check(path,PIN,copy);self.assertEqual(p.returncode,1);self.assertEqual(value['code'],'artifact_hash_mismatch')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    sources=[Path(__file__),ROOT/'tools/package_offline_bundle.py',ORIGINAL,FAILED]+[ROOT/'tools/windows'/n for n in builder.OPERATORS]+MANIFESTS
    guards={p.relative_to(ROOT).as_posix():sha(p) for p in sources};started=time.monotonic()
    with (a.output/'tests.log').open('x',encoding='utf-8') as log:r=unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Profiles1029))
    report=dict(platform=platform.platform(),testsRun=r.testsRun,successful=r.wasSuccessful(),failures=len(r.failures),errors=len(r.errors),seconds=round(time.monotonic()-started,3),sources=guards,sourcesUnchanged=all(sha(ROOT/p)==h for p,h in guards.items()),calls=CALLS,actualQaAccessed=False,postgresExecuted=False,applicationBuilds=0,frontendBuilds=0)
    (a.output/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:report[k] for k in ['testsRun','successful','seconds','sourcesUnchanged']}));return 0 if r.wasSuccessful() and report['sourcesUnchanged'] else 1
if __name__=='__main__':raise SystemExit(main())
