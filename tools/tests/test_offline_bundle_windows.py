"""Focused Windows PowerShell5.1 bundle IO/decisions; no PostgreSQL/app/global installs."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[2]
PS = Path(os.environ.get('SystemRoot', r'C:\Windows')) / 'System32/WindowsPowerShell/v1.0/powershell.exe'
HELPER = ROOT / 'tools/windows/RackClick.OfflineBundle.ps1'
TEST = ROOT / 'tools/windows/Test-RackClickOfflineBundle.ps1'
INSTALL = ROOT / 'tools/windows/Install-RackClickOfflineBundle.ps1'
EVENTS: list[dict] = []

def quote(value):
    return "'" + str(value).replace("'", "''") + "'"

def run(script):
    start = time.monotonic()
    result = subprocess.run([str(PS), '-NoLogo', '-NoProfile', '-NonInteractive', '-Command', script],
                            cwd=ROOT, capture_output=True, text=True, encoding='utf-8', timeout=50)
    EVENTS.append({'exitCode': result.returncode, 'seconds': round(time.monotonic()-start, 3),
                   'stdout': result.stdout.strip(), 'stderr': result.stderr.strip()})
    return result

def read_report(path):
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    result = run(f'& {quote(TEST)} -ArchivePath {quote(path)} -ExpectedArchiveSha256 {quote(digest)}')
    return result, json.loads(result.stdout)

class OfflineBundleWindows(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='rackclick-bundle-')
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)

    def archive(self, entries):
        path = self.directory / ('bundle-' + str(len(list(self.directory.glob('*.zip')))) + '.zip')
        with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
            for name, data, attrs in entries:
                info = zipfile.ZipInfo(name)
                if attrs is not None:
                    info.external_attr = attrs
                archive.writestr(info, data)
        # Python's ZipInfo normalizes os.sep on Windows. Patch the equal-length
        # local/central filename bytes so the attack fixture really contains '\\'.
        payload=path.read_bytes()
        for name, _, _ in entries:
            if '\\' in name:
                payload=payload.replace(name.replace('\\','/').encode('ascii'),name.encode('ascii'))
        path.write_bytes(payload)
        return path

    def test_01_pure_import_and_syntax(self):
        script = f"""$before=[Environment]::GetEnvironmentVariable('PSModulePath','Process')
$output=@(. {quote(HELPER)})
$errors=@();foreach($path in @({quote(HELPER)},{quote(TEST)},{quote(INSTALL)})){{
 $tokens=$null;$parse=$null;$null=[Management.Automation.Language.Parser]::ParseFile($path,[ref]$tokens,[ref]$parse);$errors+=@($parse)
}}
@{{outputCount=$output.Count;unchanged=($before -ceq [Environment]::GetEnvironmentVariable('PSModulePath','Process'));errors=$errors.Count;operators=@(Get-OfflineBundleOperatorNames).Count}}|ConvertTo-Json -Compress"""
        result=run(script)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {'outputCount':0,'unchanged':True,'errors':0,'operators':25})

    def test_02_names_and_crt_decisions(self):
        bad=['../x','/x','x\\y','C:x','a//b','a/./b','NUL.txt','a/COM1','a/lpt0.log','a.','a ','a/','a\u00e9','a~1/b','a?b']
        script=f'. {quote(HELPER)}; $bad=@('+','.join(quote(x) for x in bad)+');$rejected=0;foreach($name in $bad){try{Assert-OfflineBundleName $name}catch{$rejected++}};'+"""
Assert-OfflineBundleName 'application/server/database/001-foundation.sql'
$values=@();foreach($c in @($false,$true)){foreach($i in @($false,$true)){foreach($a in @($false,$true)){$values+=Get-RackClickCrtDecision $c $i $a}}}
@{rejected=$rejected;decisions=$values;exits=@((Get-RackClickCrtExitDecision 0),(Get-RackClickCrtExitDecision 3010),(Get-RackClickCrtExitDecision 1603))}|ConvertTo-Json -Compress
"""
        result=run(script);self.assertEqual(result.returncode,0,result.stderr);value=json.loads(result.stdout)
        self.assertEqual(value['rejected'],len(bad))
        self.assertEqual(value['decisions'],['missing','missing','elevation_required','install','reuse','reuse','reuse','reuse'])
        self.assertEqual(value['exits'],['verify','reboot_required','failed'])

    def test_03_zip_entry_attacks_before_manifest(self):
        variants=[([('../x',b'x',None)],'entry_name_invalid'),
                  ([('a\\x',b'x',None)],'entry_name_invalid'),
                  ([('A',b'x',None),('a',b'x',None)],'entry_collision'),
                  ([('a',b'x',None),('a/b',b'x',None)],'entry_collision'),
                  ([('A/x',b'x',None),('a/y',b'x',None)],'entry_collision'),
                  ([('a/b',b'x',None),('a',b'x',None)],'entry_collision'),
                  ([('link',b'x',0o120777<<16)],'entry_type_invalid'),
                  ([('dir/',b'',16)],'entry_name_invalid'),
                  ([('reparse',b'x',1024)],'entry_type_invalid')]
        for entries, code in variants:
            with self.subTest(code=code,entries=entries):
                path=self.archive([('bundle.json',b'{}',None)]+entries)
                result,report=read_report(path)
                self.assertEqual(result.stderr,'');self.assertFalse(report['valid']);self.assertEqual(report['code'],code)
                self.assertEqual(report['bundleArchiveSha256'],'')

    def test_04_hash_and_schema_fail_closed(self):
        path=self.archive([('bundle.json',b'{}',None),('x',b'x',None)])
        result=run(f'& {quote(TEST)} -ArchivePath {quote(path)} -ExpectedArchiveSha256 {quote("0"*64)}')
        self.assertEqual(json.loads(result.stdout)['code'],'archive_hash_mismatch');self.assertEqual(result.stderr,'')
        result,report=read_report(path)
        self.assertEqual(report['code'],'manifest_schema_invalid');self.assertEqual(result.stderr,'')
        result=run(f'& {quote(INSTALL)} -ArchivePath {quote(path)} -ExpectedArchiveSha256 {quote(hashlib.sha256(path.read_bytes()).hexdigest())} -DestinationPath {quote(self.directory / "must-not-exist")}')
        self.assertEqual(json.loads(result.stdout)['code'],'preflight_manifest_schema_invalid')
        self.assertEqual(result.stderr,'');self.assertFalse((self.directory/'must-not-exist').exists())

    def test_05_extraction_create_new_digest_and_lock(self):
        data=b'controlled fixture only';manifest=b'fixture manifest'
        path=self.archive([('bundle.json',manifest,None),('nested/file.txt',data,None)])
        target=self.directory/'content';target.mkdir()
        script=f""". {quote(HELPER)}
$null=[Reflection.Assembly]::LoadWithPartialName('System.IO.Compression')
$source=[IO.File]::Open({quote(path)},[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
$zip=New-Object IO.Compression.ZipArchive($source,[IO.Compression.ZipArchiveMode]::Read,$true)
$entries=@{{}};foreach($entry in $zip.Entries){{$entries[$entry.FullName]=$entry}}
$bundle=@{{zip=$zip;inputLocks=@($source);entries=$entries;manifestSha256='{hashlib.sha256(manifest).hexdigest()}';manifest=[pscustomobject]@{{files=[pscustomobject]@{{'nested/file.txt'=[pscustomobject]@{{sha256='{hashlib.sha256(data).hexdigest()}'}}}}}}}}
$locked=$false;try{{$write=[IO.File]::Open({quote(path)},'Open','Write','Read');$write.Dispose()}}catch{{$locked=$true}}
Copy-RackClickOfflineBundleContent $bundle {quote(target)}
Assert-RackClickOfflineInstalledContent $bundle {quote(target)}
$exclusive=$false;try{{Copy-RackClickOfflineBundleContent $bundle {quote(target)}}}catch{{$exclusive=$true}}
Close-RackClickOfflineBundle $bundle
$write=[IO.File]::Open({quote(path)},'Open','Write','Read');$write.Dispose()
@{{locked=$locked;exclusive=$exclusive;bytes=[IO.File]::ReadAllText({quote(target/'nested/file.txt')})}}|ConvertTo-Json -Compress
"""
        result=run(script);self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout),{'locked':True,'exclusive':True,'bytes':data.decode()})

    def test_06_environment_function_restore_and_inputs(self):
        script=f""". {quote(HELPER)}
$tokens=$null;$errors=$null;$ast=[Management.Automation.Language.Parser]::ParseFile({quote(INSTALL)},[ref]$tokens,[ref]$errors)
$function=$ast.Find({{param($n)$n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -ceq 'Clear-OfflineInheritedEnvironment'}},$true)
Invoke-Expression $function.Extent.Text
$saved=@{{}};foreach($key in @('PSModulePath','PGHOST','DOTNET_ROOT','RackClick__Probe','PublicOrigin')){{$saved[$key]=[Environment]::GetEnvironmentVariable($key,'Process')}}
try{{
 [Environment]::SetEnvironmentVariable('PGHOST','fixture','Process');[Environment]::SetEnvironmentVariable('DOTNET_ROOT','fixture','Process')
 [Environment]::SetEnvironmentVariable('RackClick__Probe','fixture','Process');[Environment]::SetEnvironmentVariable('PublicOrigin','fixture','Process')
 $captured=@{{}};Clear-OfflineInheritedEnvironment $captured
 $cleared=([Environment]::GetEnvironmentVariable('PGHOST','Process') -eq $null -and [Environment]::GetEnvironmentVariable('DOTNET_ROOT','Process') -eq $null -and [Environment]::GetEnvironmentVariable('RackClick__Probe','Process') -eq $null -and [Environment]::GetEnvironmentVariable('PublicOrigin','Process') -eq $null)
 foreach($key in $captured.Keys){{[Environment]::SetEnvironmentVariable($key,$captured[$key],'Process')}}
 $restored=([Environment]::GetEnvironmentVariable('PGHOST','Process') -ceq 'fixture' -and [Environment]::GetEnvironmentVariable('PSModulePath','Process') -ceq $saved.PSModulePath)
 $DotNetPath='sentinel-dotnet';$PostgresBinPath='sentinel-pg';$DeploymentPath='sentinel-deployment';$ExpectedDeploymentSha256='sentinel-hash'
 . {quote(ROOT/'tools/windows/RackClick.Deployment.ps1')}
 $inputs=($DotNetPath -ceq 'sentinel-dotnet' -and $PostgresBinPath -ceq 'sentinel-pg' -and $DeploymentPath -ceq 'sentinel-deployment' -and $ExpectedDeploymentSha256 -ceq 'sentinel-hash')
 @{{cleared=$cleared;restored=$restored;inputs=$inputs}}|ConvertTo-Json -Compress
}}finally{{foreach($key in $saved.Keys){{[Environment]::SetEnvironmentVariable($key,$saved[$key],'Process')}}}}
"""
        result=run(script);self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout),{'cleared':True,'restored':True,'inputs':True})

    def test_07_crt_readonly_current_machine(self):
        result=run(f'. {quote(HELPER)}; Get-RackClickCrtInventory|ConvertTo-Json -Depth 5 -Compress')
        self.assertEqual(result.returncode,0,result.stderr);value=json.loads(result.stdout)
        self.assertIsInstance(value['compatible'],bool);self.assertEqual(len(value['dlls']),2)
        # Compatibility is observed, not assumed for every machine or used to run redist.
        if value['compatible']:
            self.assertTrue(value['installed']);self.assertTrue(all(x['valid'] for x in value['dlls']))

    def test_08_manual_bootstrap_exact_recipe(self):
        manual=(ROOT/'docs/MANUAL-PAQUETE-WINDOWS-S1.md').read_text(encoding='utf-8')
        code=next(block.split('```',1)[0] for block in manual.split('```powershell\n')[1:] if block.startswith("$archivePath="))
        # Obtain the exact allowlist from the actual helper; only fixture payloads are copied.
        result=run(f'. {quote(HELPER)}; @(Get-OfflineBundleOperatorNames)|ConvertTo-Json -Compress')
        names=json.loads(result.stdout)
        path=self.archive([('operators/'+name,b'controlled fixture; never executed',None) for name in names])
        target=self.directory/'bootstrap'
        code=code.replace("$archivePath='C:\\Entregas\\RackClick.zip'",f'$archivePath={quote(path)}')
        code=code.replace("$expected='HASH_ZIP_CONFIABLE'",f"$expected='{hashlib.sha256(path.read_bytes()).hexdigest()}'")
        code=code.replace("$bootstrap='C:\\Entregas\\operators'",f'$bootstrap={quote(target)}')
        result=run(code);self.assertEqual(result.returncode,0,result.stderr);self.assertEqual(result.stderr,'')
        self.assertEqual(sorted(p.name for p in target.iterdir()),sorted(names))
        other=self.directory/'no-bootstrap-on-badhash'
        result=run(code.replace(quote(target),quote(other)).replace(hashlib.sha256(path.read_bytes()).hexdigest(),'0'*64))
        self.assertNotEqual(result.returncode,0);self.assertFalse(other.exists())

    def test_10_closed_profile_schema_pair_rejected_before_inventory(self):
        profiles=[('b7b26834ac5186792a01014b7221f4ba94940da19efafb84546ca635f868fa00',9),
                  ('cf51b03c80ddec460944295daf09705f3dbdec0cd83e054f5bfc6592fb081685',9),
                  ('c818294e27a40c94fe2ebf603709c94263820af1facca9a7d5c288cb70e8158e',9),
                  ('66426b3c4fdf8c75b8c1faae4572066754934000eb2567881d93407f4ae5e9f9',10)]
        script=f'. {quote(HELPER)}; $rows=@();\n'
        for digest,schema in profiles:
            script+=f"""
$value=[pscustomobject]@{{schemaVersion=1;kind='RackClickOfflineBundle';id='11111111-1111-4111-8111-111111111111';platform='win-x64';applicationManifestSha256='{digest}';files=[pscustomobject]@{{}};versions=[pscustomobject]@{{schema={19-schema};dotnetRuntime='10.0.12';postgresql='17.11';vcRedist='14.51.36247.0';vcRuntimeMinimum='14.44.35211.0'}}}}
try{{$null=Assert-OfflineBundleLayout $value @{{}};$rows+='unexpected'}}catch{{$rows+=[string]$_.Exception.Data['bundleCode']}}
"""
        script+='$rows|ConvertTo-Json -Compress'
        result=run(script);self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout),['application_schema_mismatch']*4)

    def test_09_unicode_archive_path_ascii_root_boundary(self):
        folder=self.directory/'paquete trasladado \u03a9';folder.mkdir()
        archive=folder/'RackClick offline \u03a9.zip'
        with zipfile.ZipFile(archive,'w') as stream:
            stream.writestr('bundle.json','{}');stream.writestr('safe.txt','fixture')
        # Parsing the file must now reach its invalid manifest, not reject its local Unicode path.
        result,report=read_report(archive)
        self.assertEqual(result.stderr,'');self.assertEqual(report['code'],'manifest_schema_invalid')
        invalid=['../escape','a//b','a/../b','a/./b','a~1/b','a./b','a /b','a:b','NUL.txt','COM1','LPT\u00b9.txt','a?b','a\n/b']
        script=f""". {quote(HELPER)}
$path={quote(archive)};$accepted=(Get-OfflineBundleLocalPath $path) -ceq $path
$asciiRejected=$false;try{{$null=Get-OfflineBundleLocalPath $path -Ascii}}catch{{$asciiRejected=$true}}
$bad=@({','.join(quote(x) for x in invalid)});$rejected=0
foreach($tail in $bad){{try{{$null=Get-OfflineBundleLocalPath ('C:\\'+$tail)}}catch{{$rejected++}}}}
$zipNamesStillAscii=$false;try{{Assert-OfflineBundleName ('safe'+[char]937)}}catch{{$zipNamesStillAscii=$true}}
@{{accepted=$accepted;asciiRejected=$asciiRejected;rejected=$rejected;zipNamesStillAscii=$zipNamesStillAscii}}|ConvertTo-Json -Compress
"""
        result=run(script);self.assertEqual(result.returncode,0,result.stderr)
        value=json.loads(result.stdout);self.assertTrue(value['accepted']);self.assertTrue(value['asciiRejected']);self.assertTrue(value['zipNamesStillAscii']);self.assertEqual(value['rejected'],len(invalid))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--evidence',required=True);parser.add_argument('--test',action='append')
    args,rest=parser.parse_known_args();destination=Path(args.evidence)
    destination.mkdir(parents=True,exist_ok=False)
    started=time.monotonic()
    import io
    suite=(unittest.TestSuite(OfflineBundleWindows(name) for name in args.test) if args.test else unittest.defaultTestLoader.loadTestsFromTestCase(OfflineBundleWindows))
    log=io.StringIO();result=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
    (destination/'unittest.log').write_text(log.getvalue(),encoding='utf-8')
    (destination/'commands.json').write_text(json.dumps(EVENTS,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    summary={'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'seconds':round(time.monotonic()-started,3),
             'powershell':str(PS),'scope':'IO, schema and pure CRT/environment decisions; no PostgreSQL/app/redistributable/global changes',
             'sources':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (HELPER,TEST,INSTALL,Path(__file__))}}
    (destination/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    print(log.getvalue());print(json.dumps(summary));raise SystemExit(not result.wasSuccessful())
