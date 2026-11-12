"""Windows PowerShell 5.1 online19 guards; controlled fixtures, no installation."""
import base64
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / 'tools/windows/online-install/Install-RackClickOnline.ps1'
PS = shutil.which('powershell.exe')


@unittest.skipUnless(PS, 'requires Windows PowerShell 5.1')
class OnlineWindowsTests(unittest.TestCase):
    def setUp(self):
        self.work = Path(tempfile.mkdtemp(prefix='online19-test-'))
        self.addCleanup(shutil.rmtree, self.work, True)

    def ps(self, body, *, load=True):
        prefix = "$ErrorActionPreference='Stop';"
        if load:
            prefix += ". '" + str(SCRIPT).replace("'", "''") + "';"
        encoded = base64.b64encode((prefix + body + ';exit 0').encode('utf-16le')).decode()
        result = subprocess.run([PS, '-NoProfile', '-NonInteractive', '-EncodedCommand', encoded],
                                capture_output=True, text=True, timeout=45)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout.strip()

    def test_script_exists_and_parses_as_windows_powershell51(self):
        self.assertTrue(SCRIPT.is_file(), 'online19 Windows entry is missing')
        self.ps("$t=$null;$e=$null;[void][Management.Automation.Language.Parser]::ParseFile('" +
                str(SCRIPT) + "',[ref]$t,[ref]$e);if($e.Count){throw ($e|Out-String)};"
                "if($PSVersionTable.PSVersion.Major-ne5){throw 'not Windows PowerShell 5.1'}", load=False)

    def test_client_dc_wrong_version_and_unknown_role_rejected(self):
        output = self.ps("$cases=@(@(1,0,26200),@(2,4,26100),@(3,5,26100),@(3,2,20348),@(3,0,26100));"
                         "$r=@();foreach($c in $cases){try{Assert-OnlineHostFacts $c[0] $c[1] $c[2] '64-bit' $false;$r+='BAD'}catch{$r+=$_.Exception.Message}};"
                         "$r|ConvertTo-Json -Compress")
        self.assertEqual(json.loads(output), ['online19:host_not_supported'] * 5)
        self.ps("Assert-OnlineHostFacts 3 2 26100 '64-bit' $false;Assert-OnlineHostFacts 3 3 26100 '64-bit' $true")

    def test_check_and_host_rejection_do_not_write_or_confirm(self):
        output = self.ps("function Assert-OnlineHost {throw 'online19:host_not_supported'};"
                         "function New-OnlineStage {throw 'WRITE CALLED'};function Confirm-OnlineDownloads {throw 'PROMPT CALLED'};"
                         "$r=@();foreach($m in @('Check','Prepare','Install')){try{Invoke-OnlineInstall $m $false $false;$r+='BAD'}catch{$r+=$_.Exception.Message}};$r|ConvertTo-Json -Compress")
        self.assertEqual(json.loads(output), ['online19:host_not_supported'] * 3)
        self.ps("function Assert-OnlineHost {};function Assert-OnlineFreshHost {};function Assert-OnlinePins {};"
                "function Open-OnlineCore {return [pscustomobject]@{Dispose={}}};"
                "function New-OnlineStage {throw 'WRITE CALLED'};function Confirm-OnlineDownloads {throw 'PROMPT CALLED'};"
                "$r=Invoke-OnlineInstall 'Check' $false $false;if($r.code-ne'online_checked'){throw 'bad check'}")

    def test_non_admin_and_refused_confirmation_never_create_stage(self):
        self.ps("function Assert-OnlineHost {};function Assert-OnlineFreshHost {};function Assert-OnlinePins {};"
                "function New-OnlineStage {throw 'WRITE CALLED'};function Assert-OnlineAdmin {throw 'online19:admin_required'};"
                "try{Invoke-OnlineInstall 'Prepare' $false $false;throw 'BAD'}catch{if($_.Exception.Message-ne'online19:admin_required'){throw}}")
        self.ps("function Assert-OnlineHost {};function Assert-OnlineFreshHost {};function Assert-OnlinePins {};function Assert-OnlineAdmin {};"
                "function New-OnlineStage {throw 'WRITE CALLED'};function Confirm-OnlineDownloads {throw 'online19:downloads_not_accepted'};"
                "try{Invoke-OnlineInstall 'Install' $false $false;throw 'BAD'}catch{if($_.Exception.Message-ne'online19:downloads_not_accepted'){throw}}")

    def test_env_filters_all_runtime_injection_names(self):
        self.ps("$p=New-Object Diagnostics.ProcessStartInfo;foreach($n in @('PYTHONHOME','PYTHONPATH','COR_ENABLE_PROFILING','CORECLR_PROFILER','COMPLUS_Version','DOTNET_STARTUP_HOOKS')){$p.EnvironmentVariables[$n]='evil'};"
                "Set-OnlineChildEnvironment $p 'C:\\private';foreach($n in @('PYTHONHOME','PYTHONPATH','COR_ENABLE_PROFILING','CORECLR_PROFILER','COMPLUS_Version','DOTNET_STARTUP_HOOKS')){if($p.EnvironmentVariables.ContainsKey($n)){throw $n}};"
                "if($p.EnvironmentVariables['TEMP']-ne'C:\\private'){throw 'temp'}")

    def test_python_url_closed_https_and_exact_size_hash(self):
        output = self.ps("$r=@();foreach($u in @('http://www.python.org/a','https://evil.test/a','https://www.python.org.evil.test/a','https://user@www.python.org/a','https://www.python.org:444/a')){try{Assert-OnlinePythonUri ([uri]$u);$r+='BAD'}catch{$r+=$_.Exception.Message}};$r|ConvertTo-Json -Compress")
        self.assertEqual(json.loads(output), ['online19:download_origin_invalid'] * 5)
        fixture = self.work / 'three.bin'
        fixture.write_bytes(b'abc')
        q = str(fixture).replace("'", "''")
        digest = hashlib.sha256(b'abc').hexdigest()
        self.ps(f"Assert-OnlineArtifact '{q}' 3 '{digest}';try{{Assert-OnlineArtifact '{q}' 4 '{digest}';throw 'BAD'}}catch{{if($_.Exception.Message-ne'online19:download_size_mismatch'){{throw}}}};"
                f"try{{Assert-OnlineArtifact '{q}' 3 ('0'*64);throw 'BAD'}}catch{{if($_.Exception.Message-ne'online19:download_hash_mismatch'){{throw}}}}")

    def test_python_network_failure_is_sanitized_without_retry_or_output(self):
        target = self.work / 'python.zip'
        output = self.ps("Add-Type -TypeDefinition @'\n"
                         "using System;using System.Net;\n"
                         "public class Offline19Request:WebRequest {\n"
                         " public bool AllowAutoRedirect {get;set;} public int ReadWriteTimeout {get;set;} public string UserAgent {get;set;}\n"
                         " public override int Timeout {get;set;} public override string Method {get;set;} public static int Calls;\n"
                         " public override WebResponse GetResponse(){Calls++;throw new WebException(\"PRIVATE-NETWORK-DETAIL\",WebExceptionStatus.Timeout);}\n"
                         "}\n"
                         "public class Offline19Factory:IWebRequestCreate {public WebRequest Create(Uri u){return new Offline19Request();}}\n"
                         "'@;"
                         "if(-not[Net.WebRequest]::RegisterPrefix('https://www.python.org/',(New-Object Offline19Factory))){throw 'fixture registration failed'};"
                         "$old=[Net.ServicePointManager]::SecurityProtocol;"
                         f"$message='';try{{Receive-OnlinePython '{target}';throw 'BAD'}}catch{{$message=$_.Exception.Message}};"
                         "[ordered]@{message=$message;calls=[Offline19Request]::Calls;tlsRestored=($old-eq[Net.ServicePointManager]::SecurityProtocol)}|ConvertTo-Json -Compress")
        self.assertEqual(json.loads(output), {'message': 'online19:download_unavailable', 'calls': 1, 'tlsRestored': True})
        self.assertFalse(target.exists())

    def test_provider_recipe_pin_profiles_and_changed_metadata_reject_before_cache_creation(self):
        core = self.work / 'core'
        core.mkdir()
        recipe = json.loads((ROOT / 'development/online-installer19.sources.json').read_text('utf-8'))
        pinned = (json.dumps(recipe, sort_keys=True, indent=2) + '\n').encode()
        self.assertEqual(hashlib.sha256(pinned).hexdigest(), 'f382af8c4c242d243ab605e7ba6065e098e09d841ee1495739a74908005ae684')
        (core / 'recipe.json').write_bytes(pinned)
        result = json.loads(self.ps(f"@(Get-OnlineProviders '{core}')|Select-Object id,fileName,algorithm|ConvertTo-Json -Compress"))
        self.assertEqual({row['id']: row['algorithm'] for row in result}, {'sdk': 'sha512', 'postgresql': 'sha256', 'crt': 'sha256'})
        for change in ('unknown', 'metadata', 'missing'):
            changed = json.loads(pinned)
            if change == 'unknown':
                changed['providers'][0]['id'] = 'other'
            elif change == 'metadata':
                changed['providers'][0]['bytes'] = 1
            else:
                changed['providers'].pop()
            (core / 'recipe.json').write_text(json.dumps(changed), encoding='utf-8')
            stage = self.work / change
            stage.mkdir()
            self.ps(f"try{{Receive-OnlineProviders '{stage}' '{core}';throw 'BAD'}}catch{{if($_.Exception.Message-ne'online19:provider_recipe_pin_invalid'){{throw}}}}")
            self.assertFalse((stage / 'providers').exists())

    def provider_fixture_script(self, *, bad_digest=False, declared_bytes=3, redirect=False, short=False, oversize=False, io_failure=False):
        digest = hashlib.sha512(b'abc').hexdigest() if not bad_digest else '0' * 128
        stream = "return New-Object Online19BrokenStream" if io_failure else (
                      f"return New-Object IO.MemoryStream(,[Text.Encoding]::ASCII.GetBytes('{('abcd' if oversize else 'ab' if short else 'abc')}'))")
        initialization = ("Add-Type -TypeDefinition 'public class Online19BrokenStream:System.IO.MemoryStream {"
                          "public override int Read(byte[] buffer,int offset,int count){throw new System.IO.IOException(\"PRIVATE-IO-DETAIL\");}}';") if io_failure else ''
        return (
            initialization + "$script:requests=0;function New-OnlineRequest {param($Uri);$script:requests++;"
            f"$response=[pscustomobject]@{{StatusCode={302 if redirect else 200};ContentLength={declared_bytes};Headers=@{{Location='https://foreign.invalid/secret'}}}};"
            f"$response|Add-Member ScriptMethod GetResponseStream {{{stream}}};"
            "$response|Add-Member ScriptMethod Dispose {};"
            "$request=New-Object psobject;$request|Add-Member NoteProperty Response $response;"
            "$request|Add-Member ScriptMethod GetResponse {return $this.Response};return $request};"
            f"$item=[pscustomobject]@{{id='sdk';url='https://builds.dotnet.microsoft.com/dotnet/Sdk/10.0.401/dotnet-sdk-10.0.401-win-x64.zip';bytes=3;algorithm='sha512';digest='{digest}';fileName='fixture.zip'}};"
        )

    def test_provider_windows_transport_caps_hash_and_redirect_hosts(self):
        for number, (options, expected) in enumerate([
            ({}, None), ({'bad_digest': True}, 'download_hash_mismatch'),
            ({'declared_bytes': 4}, 'download_size_mismatch'), ({'redirect': True}, 'download_origin_invalid'),
            ({'short': True}, 'download_size_mismatch'), ({'declared_bytes': -1}, None),
            ({'declared_bytes': -1, 'oversize': True}, 'download_size_mismatch'), ({'io_failure': True}, 'download_unavailable'),
        ]):
            target = self.work / f'provider{number}.bin'
            command = self.provider_fixture_script(**options)
            if expected:
                command += f"try{{Receive-OnlineProvider $item '{target}';throw 'BAD'}}catch{{if($_.Exception.Message-ne'online19:{expected}'){{throw}}}};"
            else:
                command += f"Receive-OnlineProvider $item '{target}';"
            command += "if($script:requests-ne1){throw 'unexpected retry'}"
            self.ps(command)
            if expected is None:
                self.assertEqual(target.read_bytes(), b'abc')
        self.ps("foreach($u in @('http://builds.dotnet.microsoft.com/a','https://builds.dotnet.microsoft.com.evil/a','https://user@builds.dotnet.microsoft.com/a')){"
                "try{Assert-OnlineProviderUri ([uri]$u) 'sdk';throw 'BAD'}catch{if($_.Exception.Message-ne'online19:download_origin_invalid'){throw}}};"
                "try{Assert-OnlineProviderUri ([uri]'https://get.enterprisedb.com/a') 'unknown';throw 'BAD'}catch{if($_.Exception.Message-ne'online19:provider_profile_invalid'){throw}}")
        self.ps("$r=New-OnlineRequest ([uri]'https://builds.dotnet.microsoft.com/fixture');"
                "if($r.AllowAutoRedirect-or$r.Timeout-le0-or$r.Timeout-gt90000-or$r.ReadWriteTimeout-le0-or$r.ReadWriteTimeout-gt90000){throw 'transport bounds'}")

    def test_provider_cache_missing_partial_or_extra_rejects_before_python(self):
        cache = self.work / 'providers'
        cache.mkdir()
        digest = hashlib.sha256(b'abc').hexdigest()
        descriptors = [{"id": name, "fileName": name + '.bin', "bytes": 3, "algorithm": 'sha256', "digest": digest}
                       for name in ('sdk', 'postgresql', 'crt')]
        prefix = f"$script:items=ConvertFrom-Json '{json.dumps(descriptors)}';function Get-OnlineProviders {{return $script:items}};"
        self.ps(prefix + f"try{{Assert-OnlineProviderCache 'fixture-core' '{cache}';throw 'BAD'}}catch{{if($_.Exception.Message-ne'online19:provider_cache_incomplete'){{throw}}}}")
        for item in descriptors:
            (cache / item['fileName']).write_bytes(b'abc')
        self.ps(prefix + f"Assert-OnlineProviderCache 'fixture-core' '{cache}'")
        (cache / 'crt.bin').write_bytes(b'ab')
        self.ps(prefix + f"try{{Assert-OnlineProviderCache 'fixture-core' '{cache}';throw 'BAD'}}catch{{if($_.Exception.Message-ne'online19:download_size_mismatch'){{throw}}}}")
        (cache / 'crt.bin').write_bytes(b'abc')
        (cache / 'other.bin').write_bytes(b'abc')
        self.ps(prefix + f"try{{Assert-OnlineProviderCache 'fixture-core' '{cache}';throw 'BAD'}}catch{{if($_.Exception.Message-ne'online19:provider_cache_incomplete'){{throw}}}}")

    def test_provider_set_is_fresh_complete_and_never_reuses_existing_cache(self):
        stage = self.work / 'stage'
        stage.mkdir()
        descriptors = json.loads((ROOT / 'development/online-installer19.sources.json').read_text('utf-8'))['providers']
        for item in descriptors:
            item['bytes'] = 3
            item['digest'] = hashlib.new(item['algorithm'], b'abc').hexdigest()
        self.ps(self.provider_fixture_script() +
                f"$script:items=ConvertFrom-Json '{json.dumps(descriptors)}';function Get-OnlineProviders {{return $script:items}};"
                f"Receive-OnlineProviders '{stage}' 'fixture-core';if($script:requests-ne3){{throw 'three downloads required'}};"
                f"try{{Receive-OnlineProviders '{stage}' 'fixture-core';throw 'BAD'}}catch{{if($_.Exception.Message-ne'online19:provider_cache_exists'){{throw}}}};"
                "if($script:requests-ne3){throw 'old cache reused'}")
        self.assertEqual(sorted(p.name for p in (stage / 'providers').iterdir()), sorted(item['fileName'] for item in descriptors))
        for path in (stage / 'providers').iterdir():
            self.assertEqual(path.read_bytes(), b'abc')

    def test_private_old_transport_allows_new_attempt_but_installations_and_aliases_reject(self):
        program_data = self.work / 'ProgramData'
        program_files = self.work / 'ProgramFiles'
        program_data.mkdir()
        program_files.mkdir()
        name = 'RackClick-Online19-' + 'a' * 32
        prior = program_data / name
        prior.mkdir()
        marker = prior / 'online19-result.json'
        marker.write_text('{"success":false,"code":"unexpected_error","installed":false}')
        before = marker.read_bytes()
        # ACL objects are controlled fixtures so these tests never change host ACLs or ProgramData.
        output = self.ps(
            "function Get-CimInstance {param($ClassName,$ErrorAction)};function Get-LocalUser {};"
            # Redirect the existing OS inventory boundary too, so the regression is red on the old guard.
            "function Get-ChildItem {param($LiteralPath,[switch]$Force,$ErrorAction);"
            f"if($LiteralPath-eq[Environment]::GetFolderPath('CommonApplicationData')){{$LiteralPath='{program_data}'}};"
            "if($LiteralPath-in@([Environment]::GetFolderPath('ProgramFiles'),[Environment]::GetFolderPath('ProgramFilesX86'))){return};"
            "Microsoft.PowerShell.Management\\Get-ChildItem -LiteralPath $LiteralPath -Force};"
            f"function Get-OnlineInstallationRoots {{@([pscustomobject]@{{path='{program_data}';allowTransport=$true}},[pscustomobject]@{{path='{program_files}';allowTransport=$false}})}};"
            "$script:fixtureAcl=New-Object Security.AccessControl.DirectorySecurity;"
            "$script:fixtureAcl.SetSecurityDescriptorSddlForm('O:BAG:SYD:P(A;OICI;FA;;;SY)(A;OICI;FA;;;BA)');"
            "function Get-Acl {param($LiteralPath) return $script:fixtureAcl};"
            "Assert-OnlineFreshHost;'allowed'")
        self.assertEqual(output, 'allowed')
        self.assertEqual(marker.read_bytes(), before)
        self.assertEqual(sorted(p.name for p in program_data.iterdir()), [name])
        prior.rename(program_data / (name + '-similar'))
        self.ps("function Get-CimInstance {param($ClassName,$ErrorAction)};function Get-LocalUser {};"
                f"function Get-OnlineInstallationRoots {{[pscustomobject]@{{path='{program_data}';allowTransport=$true}}}};"
                "try{Assert-OnlineFreshHost;throw 'BAD'}catch{if($_.Exception.Message-ne'online19:existing_installation'){throw}}")
        (program_data / (name + '-similar')).rename(prior)
        for sddl in ('O:SYG:SYD:P(A;OICI;FA;;;SY)(A;OICI;FA;;;BA)',
                     'O:BUG:SYD:P(A;OICI;FA;;;SY)(A;OICI;FA;;;BA)',
                     'O:BAG:SYD:P(A;OICI;FA;;;SY)(A;OICI;FA;;;WD)',
                     'O:BAG:SYD:(A;OICI;FA;;;SY)(A;OICI;FA;;;BA)',
                     'O:BAG:SYD:P(A;OICI;FR;;;SY)(A;OICI;FA;;;BA)',
                     'O:BAG:SYD:P(A;;FA;;;SY)(A;OICI;FA;;;BA)',
                     'O:BAG:SYD:P(D;OICI;FA;;;SY)(A;OICI;FA;;;BA)'):
            expected = 'allowed' if sddl.startswith('O:SY') else 'rejected'
            output = self.ps("function Get-CimInstance {param($ClassName,$ErrorAction)};function Get-LocalUser {};"
                             f"function Get-OnlineInstallationRoots {{[pscustomobject]@{{path='{program_data}';allowTransport=$true}}}};"
                             f"$script:fixtureAcl=New-Object Security.AccessControl.DirectorySecurity;$script:fixtureAcl.SetSecurityDescriptorSddlForm('{sddl}');"
                             "function Get-Acl {param($LiteralPath) return $script:fixtureAcl};"
                             "try{Assert-OnlineFreshHost;'allowed'}catch{if($_.Exception.Message-ne'online19:existing_installation'){throw};'rejected'}")
            self.assertEqual(output, expected)
        genuine = program_files / 'RackClick'
        genuine.mkdir()
        self.ps("function Get-CimInstance {param($ClassName,$ErrorAction)};function Get-LocalUser {};"
                f"function Get-OnlineInstallationRoots {{[pscustomobject]@{{path='{program_files}';allowTransport=$false}}}};"
                "try{Assert-OnlineFreshHost;throw 'BAD'}catch{if($_.Exception.Message-ne'online19:existing_installation'){throw}}")
        self.assertTrue(genuine.is_dir())
        self.assertEqual(marker.read_bytes(), before)

    def test_private_transport_reparse_or_file_or_programfiles_name_is_rejected(self):
        base = self.work / 'root'
        base.mkdir()
        outside = self.work / 'outside'
        outside.mkdir()
        name = 'RackClick-Online19-' + 'b' * 32
        candidate = base / name
        self.ps(f"[void](New-Item -ItemType Junction -Path '{candidate}' -Target '{outside}')")
        self.ps(f"$item=Get-Item -LiteralPath '{candidate}' -Force;"
                f"if(Test-OnlinePreviousTransport $item '{base}'){{throw 'junction accepted'}}")
        # The target is intact; remove only the test junction, not its target.
        os.rmdir(candidate)
        candidate.write_text('this is a file')
        self.ps(f"$item=Get-Item -LiteralPath '{candidate}';"
                f"if(Test-OnlinePreviousTransport $item '{base}'){{throw 'file accepted'}}")
        candidate.unlink()
        candidate.mkdir()
        self.ps("function Get-CimInstance {param($ClassName,$ErrorAction)};function Get-LocalUser {};"
                f"function Get-OnlineInstallationRoots {{[pscustomobject]@{{path='{base}';allowTransport=$false}}}};"
                "try{Assert-OnlineFreshHost;throw 'BAD'}catch{if($_.Exception.Message-ne'online19:existing_installation'){throw}}")
        self.assertTrue(outside.is_dir())

    def test_zip_rejects_traversal_alias_duplicate_and_symlink_before_extract(self):
        cases = [('.. /x', False), ('../escape', False), ('a\\b', False), ('C:/x', False),
                 ('a/./b', False), ('a//b', False), ('a./b', False), ('CON', False), ('a', True)]
        for number, (name, link) in enumerate(cases):
            archive = self.work / f'bad{number}.zip'
            with zipfile.ZipFile(archive, 'w') as z:
                info = zipfile.ZipInfo(name)
                # On Windows ZipInfo.__init__ normalizes backslashes; preserve this hostile raw name.
                info.filename = name
                if link:
                    info.external_attr = 0o120777 << 16
                z.writestr(info, 'x')
            target = self.work / f'out{number}'
            self.ps(f"try{{Expand-OnlineZip '{archive}' '{target}';throw 'BAD'}}catch{{if($_.Exception.Message-notlike'online19:archive_*'){{throw}}}}")
            self.assertFalse(target.exists())
        archive = self.work / 'duplicate.zip'
        with zipfile.ZipFile(archive, 'w') as z:
            z.writestr('a', 'one')
            z.writestr('A', 'two')
        self.ps(f"try{{Expand-OnlineZip '{archive}' '{self.work / 'dups'}';throw 'BAD'}}catch{{if($_.Exception.Message-ne'online19:archive_path_invalid'){{throw}}}}")

    def test_zip_extracts_good_fixture_exclusively(self):
        archive = self.work / 'good.zip'
        target = self.work / 'output'
        with zipfile.ZipFile(archive, 'w') as z:
            z.writestr('folder/file.txt', 'safe')
        self.ps(f"Expand-OnlineZip '{archive}' '{target}'")
        self.assertEqual((target / 'folder/file.txt').read_text(), 'safe')
        self.ps(f"try{{Expand-OnlineZip '{archive}' '{target}';throw 'BAD'}}catch{{if($_.Exception.Message-ne'online19:archive_destination_exists'){{throw}}}}")

    def test_native_tree_tamper_or_extra_directory_is_rejected(self):
        for case in ('tamper', 'extra'):
            parent = self.work / case
            parent.mkdir()
            archive = parent / 'native.zip'
            with zipfile.ZipFile(archive, 'w') as z:
                z.writestr('RackClick-Servidor-19/INICIAR.ps1', 'approved')
            native = parent / 'native19'
            self.ps(f"Expand-OnlineZip '{archive}' '{native}'")
            if case == 'tamper':
                (native / 'RackClick-Servidor-19/INICIAR.ps1').write_text('other')
            else:
                (native / 'extra-directory').mkdir()
            self.ps(f"try{{Assert-OnlineExtractedTree '{archive}' '{native}';throw 'BAD'}}catch{{if($_.Exception.Message-ne'online19:native_tree_mismatch'){{throw}}}}")

    def test_existing_rackclick_service_or_account_is_preserved(self):
        self.ps("function Get-CimInstance {param($ClassName,$ErrorAction) [pscustomobject]@{Name='RackClick';DisplayName='app';PathName='app.exe'}};"
                "function Get-LocalUser {throw 'accounts should not be queried'};"
                "try{Assert-OnlineFreshHost;throw 'BAD'}catch{if($_.Exception.Message-ne'online19:existing_service'){throw}}")
        self.ps("function Get-CimInstance {param($ClassName,$ErrorAction)};"
                "function Get-LocalUser {[pscustomobject]@{Name='RackClickSvc'}};"
                "try{Assert-OnlineFreshHost;throw 'BAD'}catch{if($_.Exception.Message-ne'online19:existing_account'){throw}}")

    def test_child_process_has_bounded_stdout_and_stderr(self):
        self.ps("Initialize-OnlineNative;$p=New-Object Diagnostics.ProcessStartInfo;"
                "$p.FileName=(Join-Path $env:SystemRoot 'System32\\WindowsPowerShell\\v1.0\\powershell.exe');"
                "$p.UseShellExecute=$false;$p.CreateNoWindow=$true;$p.RedirectStandardOutput=$true;$p.RedirectStandardError=$true;"
                "$p.Arguments='-NoProfile -Command \"[Console]::Out.Write((''x''*10000))\"';"
                "$r=[RackClick.Online19.Child]::Run($p,10,100);if(-not$r.Limited-or$r.Output.Length-gt100){throw 'not bounded'};"
                "$p.Arguments='-NoProfile -Command \"[Console]::Error.Write((''x''*10000))\"';"
                "$r=[RackClick.Online19.Child]::Run($p,10,100);if(-not$r.Limited-or$r.Output.Length-ne0){throw 'stderr not bounded'}")

    def test_prepare_never_launches_and_install_reports_only_delegation(self):
        for mode, expected in [('Prepare', 'online_prepared'), ('Install', 'online_delegated')]:
            case = self.work / mode
            case.mkdir()
            core = case / 'input.zip'
            core.write_bytes(b'core fixture')
            stage = case / 'stage'
            stage.mkdir()
            digest = hashlib.sha256(core.read_bytes()).hexdigest()
            output = self.ps("function Assert-OnlineHost {};function Assert-OnlineFreshHost {};function Assert-OnlinePins {};"
                             "function Assert-OnlineAdmin {};function Confirm-OnlineDownloads {};"
                             f"$script:OnlineCoreSha='{digest}';function Open-OnlineCore {{return [IO.File]::OpenRead('{core}')}};"
                             f"function New-OnlineStage {{return '{stage}'}};function Expand-OnlineZip {{}};function Receive-OnlinePython {{}};"
                             f"$script:providersReceived=0;function Receive-OnlineProviders {{param($Stage,$Core);if($Stage-ne'{stage}'){{throw 'wrong providers root'}};$script:providersReceived++}};"
                             "function Invoke-OnlineAssembly {if($script:providersReceived-ne1){throw 'providers required before Python'};return 'fixed-native-launcher'};"
                             "function Invoke-OnlineNativeLauncher {param($Launcher,$Stage);if($Launcher-ne'fixed-native-launcher'){throw 'wrong launcher'};return 123};"
                             f"$r=Invoke-OnlineInstall '{mode}' $true $true;$r|ConvertTo-Json -Compress")
            receipt = json.loads(output)
            self.assertEqual(receipt['code'], expected)
            self.assertFalse(receipt['installed'])
            self.assertEqual('nativeProcessId' in receipt, mode == 'Install')
            self.assertEqual(json.loads((stage / 'online19-result.json').read_text())['code'], expected)

    def test_assembler_receives_new_work_path_and_creates_it_itself(self):
        core = self.work / 'core'
        core.mkdir()
        stage = self.work / 'stage'
        stage.mkdir()
        wrapper = b'controlled native wrapper fixture'
        digest = hashlib.sha256(wrapper).hexdigest()
        # The real assembler requires a fresh destination. This small subprocess preserves that boundary.
        (core / 'assemble.py').write_text(
            "import argparse, hashlib, json\n"
            "from pathlib import Path\n"
            "p=argparse.ArgumentParser();p.add_argument('--core-root');p.add_argument('--work-root');p.add_argument('--cache',required=True);a=p.parse_args()\n"
            "assert Path(a.cache)==Path(a.work_root).parent/'providers', 'fixed_cache_required'\n"
            "work=Path(a.work_root)\n"
            "assert not work.exists(), 'work_root_must_not_exist'\n"
            "work.mkdir()\n"
            "(work/'assembler-created-work.txt').write_text('fresh destination')\n"
            "(work/'.local').mkdir()\n"
            f"wrapper={wrapper!r}\n"
            "(work/'.local'/'RackClick-Servidor-19.zip').write_bytes(wrapper)\n"
            "native=work/'native19'/'RackClick-Servidor-19';native.mkdir(parents=True)\n"
            "(native/'INICIAR.ps1').write_text('# controlled fixture')\n"
            "print(json.dumps({'success':True,'code':'online_assembled','wrapperSha256':hashlib.sha256(wrapper).hexdigest()}))\n",
            encoding='ascii')
        output = self.ps(
            "Initialize-OnlineNative;"
            "function Get-AuthenticodeSignature {"
            "$cert=New-Object psobject;Add-Member -InputObject $cert -MemberType ScriptMethod -Name GetNameInfo -Value {return 'Python Software Foundation'};"
            "return [pscustomobject]@{Status='Valid';SignerCertificate=$cert}};"
            "function Assert-OnlineExtractedTree {};"
            "function Assert-OnlineProviderCache {};"
            f"$script:OnlineNativeSha='{digest}';"
            f"Invoke-OnlineAssembly '{stage}' '{core}' '{sys.executable}'")
        self.assertEqual(output, str(stage / 'work/native19/RackClick-Servidor-19/INICIAR.ps1'))
        self.assertEqual((stage / 'work/assembler-created-work.txt').read_text(), 'fresh destination')


if __name__ == '__main__':
    unittest.main()
