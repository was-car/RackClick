"""Contract checks for the isolated process-crash harness, without starting a DB or VM."""
from pathlib import Path
import ast,unittest

ROOT=Path(__file__).resolve().parents[2]
class RotationRunnerTests(unittest.TestCase):
 def setUp(self):self.source=(ROOT/'tools/tests/run_mfa_rotation.py').read_text('utf-8');self.tree=ast.parse(self.source)
 def test_binary_pins_are_checked_before_each_execution_and_after_trial(self):
  self.assertIn('rotation_binary_changed_before_execution',self.source);self.assertIn('rotation_binary_changed_during_trial',self.source)
 def test_only_owned_popen_pid_can_be_used_to_terminate_the_tree(self):
  calls=[n for n in ast.walk(self.tree) if isinstance(n,ast.List) and n.elts and isinstance(n.elts[0],ast.Constant) and n.elts[0].value=='taskkill.exe']
  self.assertEqual(2,len(calls))
  for n in calls:self.assertIn('process.pid',ast.unparse(n));self.assertNotIn('marker',ast.unparse(n))
 def test_restore_uses_custom_dump_single_transaction_and_new_cluster(self):
  for required in ['pg_dump.exe','pg_restore.exe','--single-transaction',"Lab('f0603-restore')",'sourceDatabaseUnchanged']:self.assertIn(required,self.source)
 def test_no_services_or_vm_operation_is_imported(self):
  for forbidden in ['vmrun.exe','Stop-Service','Start-Service','sc.exe','Remove-Service','Set-LocalUser']:self.assertNotIn(forbidden,self.source)
 def test_shared_admission_does_not_replace_table_locks(self):
  coordinator=(ROOT/'development/server/src/RackClick.Server/MfaRotationCoordinator.cs').read_text('utf-8')
  self.assertIn('MfaMaintenanceAdmission.ExclusiveAsync',coordinator);self.assertIn('MfaRotationDatabase.LockAsync',coordinator)
 def test_rotation_is_not_a_public_cli_or_http_mode(self):
  program=(ROOT/'development/server/src/RackClick.Server/Program.cs').read_text('utf-8-sig')
  self.assertNotIn('--mfa-key-rotate',program);self.assertIn('MfaRotationStartupGuard.ValidateAsync',program)

if __name__=='__main__':unittest.main()
