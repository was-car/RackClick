"""Kit integrity tests; no inventory, connection, installation or elevation is run."""
import hashlib
import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('two_host_kit',ROOT/'tools/prepare_two_host_kit.py')
kit=importlib.util.module_from_spec(spec);spec.loader.exec_module(kit)

class TwoHostKit(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='rackclick-hostkit-')
        self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name)

    def build(self,name='kit'):
        out=self.base/name;result=kit.build(out)
        return out,out/'Preparar-Cliente3-Servidor',result

    def invoke(self,folder):
        ps=Path(os.environ['SystemRoot'])/'System32/WindowsPowerShell/v1.0/powershell.exe'
        return subprocess.run([str(ps),'-NoLogo','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(folder/'Invoke-RackClickHostPreparation.ps1'),'-Role','Client3'],capture_output=True,timeout=25)

    def test_deterministic_closed_inventory_and_pending_network(self):
        out,folder,first=self.build('a');other,_,second=self.build('b')
        self.assertEqual(first['sha256'],second['sha256'])
        self.assertEqual(first['files'],7)
        manifest=json.loads((folder/'MANIFIESTO.json').read_text(encoding='utf-8'))
        self.assertEqual(set(manifest['files']),set(kit.NAMES))
        self.assertEqual(manifest['readiness'],'inventory_only')
        with zipfile.ZipFile(first['archive']) as archive:
            self.assertEqual(set(archive.namelist()),{'Preparar-Cliente3-Servidor/'+n for n in (*kit.NAMES,'MANIFIESTO.json')})
            for name,expected in manifest['files'].items():
                self.assertEqual(hashlib.sha256(archive.read('Preparar-Cliente3-Servidor/'+name)).hexdigest(),expected)
        plan=json.loads((folder/'PLAN-PENDIENTE.json').read_text(encoding='utf-8'))
        self.assertIsNone(plan['network']['httpsOrigin'])
        self.assertFalse(plan['installationOrCompatibilityApproved'])
        self.assertFalse(plan['currentApplicationBundle']['includedInPreparationKit'])
        self.assertEqual(plan['currentApplicationBundle']['mode'],'loopback_only')
        self.assertFalse(plan['usageModel']['rackClickClientInstallationRequired'])
        self.assertFalse(plan['usageModel']['browserHostInventoryRequired'])
        self.assertEqual(plan['usageModel']['serverHostOptions'],['Windows Server 2025','Windows 11 Pro'])
        self.assertIn(b'-Role Server',(folder/'02-DATOS-WINDOWS11-SERVIDOR.cmd').read_bytes())
        self.assertFalse((folder/'02-DATOS-CLIENTE3.cmd').exists())

    def test_existing_destination_is_untouched(self):
        out,folder,result=self.build()
        before={str(p.relative_to(out)):p.read_bytes() for p in out.rglob('*') if p.is_file()}
        with self.assertRaises(ValueError):kit.build(out)
        self.assertEqual(before,{str(p.relative_to(out)):p.read_bytes() for p in out.rglob('*') if p.is_file()})

    @unittest.skipUnless(os.name=='nt','Windows PowerShell required')
    def test_tampered_inventory_script_never_executed(self):
        _,folder,_=self.build()
        (folder/'Get-RackClickHostReadiness.ps1').write_text("[IO.File]::WriteAllText((Join-Path $PSScriptRoot 'SHOULD-NOT-EXIST'),'executed')",encoding='ascii')
        result=self.invoke(folder)
        self.assertEqual(result.returncode,2,result.stdout+result.stderr)
        self.assertIn(b'Preparation file changed',result.stdout)
        self.assertFalse((folder/'SHOULD-NOT-EXIST').exists())
        self.assertFalse((folder/'resultados').exists())

    @unittest.skipUnless(os.name=='nt','Windows PowerShell required')
    def test_missing_manifest_member_rejected_before_inventory(self):
        _,folder,_=self.build()
        (folder/'LEEME-PRIMERO.html').unlink()
        result=self.invoke(folder)
        self.assertEqual(result.returncode,2,result.stdout+result.stderr)
        self.assertIn(b'LEEME-PRIMERO.html',result.stdout)
        self.assertFalse((folder/'resultados').exists())

if __name__=='__main__':unittest.main(verbosity=2)
