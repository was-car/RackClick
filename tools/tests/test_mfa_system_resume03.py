"""Default Settings regression. No real task is created or run.

RC_RESUME03_TARGET can point to preserved02 for the omission red tests.
The five semantic tests from02 are inherited unchanged against the new target.
"""
import importlib.util
import json
import os
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('resume02_regression',ROOT/'tools/tests/test_mfa_system_resume02.py')
previous=importlib.util.module_from_spec(spec)
spec.loader.exec_module(previous)
previous.SCRIPT=Path(os.environ.get('RC_RESUME03_TARGET',str(ROOT/'tools/windows/mfa-service-read-system/Resume-MfaServiceReadSystemTrial03.ps1')))

class EnabledDefaultsTests(previous.SemanticTests):
    def test_enabled_absent_uses_documented_true_default(self):
        data=self.focus(previous.FIXTURE+r'''
[xml]$doc=$canonical
[void]$doc.Task.Settings.RemoveChild($doc.GetElementsByTagName('Enabled')[0])
$code=Code {Assert-ResumeTask $doc.OuterXml $legacy $false}
@{accepted=($code -ceq '');code=$code}|ConvertTo-Json -Compress
''')
        self.assertTrue(data['accepted'],data)

    def test_policy_absent_uses_documented_ignore_new_default(self):
        data=self.focus(previous.FIXTURE+r'''
[xml]$doc=$canonical
[void]$doc.Task.Settings.RemoveChild($doc.GetElementsByTagName('MultipleInstancesPolicy')[0])
$code=Code {Assert-ResumeTask $doc.OuterXml $legacy $false}
@{accepted=($code -ceq '');code=$code}|ConvertTo-Json -Compress
''')
        self.assertTrue(data['accepted'],data)

    def test_absence_does_not_allow_disabled_invalid_duplicate_or_other_policy(self):
        data=self.focus(previous.FIXTURE+r'''
$rows=@()
foreach($case in @('false','zero','bad_enabled','empty_enabled','duplicate_enabled','queue','parallel','stop_existing','duplicate_policy','missing_settings','missing_timeout')) {
 [xml]$doc=$canonical;$ns=$doc.DocumentElement.NamespaceURI
 $expected='task_enabled_invalid'
 switch($case) {
  'false' {$doc.Task.Settings.Enabled='false'}
  'zero' {$doc.Task.Settings.Enabled='0'}
  'bad_enabled' {$doc.Task.Settings.Enabled='yes'}
  'empty_enabled' {$doc.Task.Settings.Enabled=''}
  'duplicate_enabled' {[void]$doc.Task.Settings.AppendChild($doc.GetElementsByTagName('Enabled')[0].CloneNode($true))}
  'queue' {$doc.Task.Settings.MultipleInstancesPolicy='Queue';$expected='task_multiple_instances_invalid'}
  'parallel' {$doc.Task.Settings.MultipleInstancesPolicy='Parallel';$expected='task_multiple_instances_invalid'}
  'stop_existing' {$doc.Task.Settings.MultipleInstancesPolicy='StopExisting';$expected='task_multiple_instances_invalid'}
  'duplicate_policy' {[void]$doc.Task.Settings.AppendChild($doc.GetElementsByTagName('MultipleInstancesPolicy')[0].CloneNode($true));$expected='task_multiple_instances_invalid'}
  'missing_settings' {[void]$doc.Task.RemoveChild($doc.GetElementsByTagName('Settings')[0]);$expected='task_settings_invalid'}
  'missing_timeout' {[void]$doc.Task.Settings.RemoveChild($doc.GetElementsByTagName('ExecutionTimeLimit')[0]);$expected='task_execution_time_invalid'}
 }
 $code=Code {Assert-ResumeTask $doc.OuterXml $legacy $false}
 $rows+=@{case=$case;actual=$code;expected=$expected;passed=($code -ceq $expected)}
}
$rows|ConvertTo-Json -Depth 5 -Compress
''')
        self.assertTrue(all(row['passed'] for row in data),data)

    def test_native_disabled_and_unknown_values_are_never_enabled_or_accepted(self):
        data=self.focus(r'''
function Code([scriptblock]$Body){try{&$Body|Out-Null;return ''}catch{return Resume-Code $_}}
$rows=@()
foreach($case in @('ready','registered_false','settings_false','registered_string','settings_string','registered_missing','queue','enum_string')) {
 $task=[pscustomobject]@{Enabled=$true;Definition=[pscustomobject]@{Settings=[pscustomobject]@{Enabled=$true;MultipleInstances=2}}}
 $expected=''
 switch($case) {
  'registered_false' {$task.Enabled=$false;$expected='task_enabled_invalid'}
  'settings_false' {$task.Definition.Settings.Enabled=$false;$expected='task_enabled_invalid'}
  'registered_string' {$task.Enabled='true';$expected='task_enabled_invalid'}
  'settings_string' {$task.Definition.Settings.Enabled='true';$expected='task_enabled_invalid'}
  'registered_missing' {$task=[pscustomobject]@{Definition=$task.Definition};$expected='task_enabled_invalid'}
  'queue' {$task.Definition.Settings.MultipleInstances=1;$expected='task_multiple_instances_invalid'}
  'enum_string' {$task.Definition.Settings.MultipleInstances='2';$expected='task_multiple_instances_invalid'}
 }
 $code=Code {Assert-RegisteredTaskSettings $task}
 $rows+=@{case=$case;actual=$code;passed=($code -ceq $expected);enabledAfter=$task.Enabled}
}
$rows|ConvertTo-Json -Depth 4 -Compress
''')
        self.assertTrue(all(row['passed'] for row in data),data)
        self.assertFalse(next(row for row in data if row['case']=='registered_false')['enabledAfter'])

    def test_native_definition_resolves_both_omissions_to_safe_defaults(self):
        data=self.focus(previous.FIXTURE+r'''
[xml]$doc=$canonical
[void]$doc.Task.Settings.RemoveChild($doc.GetElementsByTagName('Enabled')[0])
[void]$doc.Task.Settings.RemoveChild($doc.GetElementsByTagName('MultipleInstancesPolicy')[0])
$definition=$scheduler.NewTask(0);$definition.XmlText=$doc.OuterXml
Assert-ResumeTask $doc.OuterXml $legacy $false
Assert-RegisteredTaskSettings ([pscustomobject]@{Enabled=$definition.Settings.Enabled;Definition=$definition})
@{enabled=$definition.Settings.Enabled;multipleInstances=[int]$definition.Settings.MultipleInstances;created=$false;ran=$false}|ConvertTo-Json -Compress
''')
        self.assertTrue(data['enabled'])
        self.assertEqual(data['multipleInstances'],2)
        self.assertFalse(data['created'])

    def test_registered_settings_are_checked_before_run_without_setters(self):
        text=previous.SCRIPT.read_text(encoding='ascii')
        body=text[text.index("$stage='task_create'"):]
        self.assertLess(body.index("'-registered-task.json'"),body.index('Assert-RegisteredTaskSettings $task'))
        self.assertLess(body.index('Assert-RegisteredTaskSettings $task'),body.index('$task.Run($null)'))
        self.assertNotIn('.Enabled=',text)
        self.assertNotIn('.Enabled =',text)

if __name__=='__main__':unittest.main(verbosity=2)
