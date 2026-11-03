"""Focused physical/role and no-reuse guards, no database or real credential."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools'))
from prepare_demo50 import compatible,counterpart_spec,COUNTERPART

def port(role='bidi',device='a',typ='fiber',physical='lc-simplex-upc',power='unspecified',system=None):
 return {'id':device+'-p','deviceId':device,'type':typ,'powerRole':power,
  'properties':{'hardwarePhysicalConnector':physical,'hardwareSignalRole':role,**({'hardwarePowerSystem':system} if system else {})}}

class Demo50LoaderTests(unittest.TestCase):
 def test_directional_optical_pair_is_symmetric_and_not_a_bidi_shortcut(self):
  for a,b,valid in [('tx','rx',True),('rx','tx',True),('tx','tx',False),('rx','rx',False),('bidi','rx',False),('rx','bidi',False),('bidi','tx',False),('tx','bidi',False)]:
   with self.subTest(first=a,second=b):self.assertEqual(compatible(port(a),port(b,'b')),valid)
 def test_physical_and_power_systems_do_not_collapse(self):
  self.assertFalse(compatible(port(),port('bidi','b',physical='sc-simplex-apc')))
  for typ in ('console','idc','ipc','dsl','telephony','sas'):
   self.assertFalse(compatible(port(typ=typ),port('bidi','b',typ='rj45',physical='rj45')))
  for system in ('dc','usb-pd','unifi-smartpower'):
   a=port(None,typ='power_dc',physical='dc-barrel',power='outlet',system=system)
   self.assertTrue(compatible(a,port(None,'b',typ='power_dc',physical='dc-barrel',power='inlet',system=system)))
   self.assertFalse(compatible(a,port(None,'b',typ='power_dc',physical='dc-barrel',power='outlet',system=system)))
   self.assertFalse(compatible(a,port(None,'b',typ='power_dc',physical='dc-barrel',power='inlet',system='usb-pd' if system!='usb-pd' else 'dc')))
 def test_no_self_loop_and_declared_iec_counterparts(self):
  self.assertFalse(compatible(port(),port('rx')))
  self.assertEqual(counterpart_spec(port(None,typ='power',physical='iec-c14',power='inlet'))['physicalConnector'],'iec-c13')
  self.assertEqual(COUNTERPART['iec-c13'],'iec-c14')
 def test_existing_output_rejected_before_reading_application_or_creating_a_lab(self):
  with tempfile.TemporaryDirectory(prefix='demo50-reuse-',dir=ROOT/'.local') as directory:
   target=Path(directory);sentinel=target/'preserved.txt';sentinel.write_text('must survive')
   result=subprocess.run([sys.executable,'-B',str(ROOT/'tools/prepare_demo50.py'),'--application',str(target/'does-not-exist.json'),'--output',str(target)],capture_output=True,text=True,creationflags=0x08000000)
   self.assertNotEqual(result.returncode,0);self.assertIn('new_private_output_required',result.stderr)
   self.assertEqual([p.name for p in target.iterdir()],['preserved.txt']);self.assertEqual(sentinel.read_text(),'must survive')

if __name__=='__main__':unittest.main()
