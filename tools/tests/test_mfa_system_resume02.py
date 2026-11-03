"""Semantic contract foci for resume02. Native checks never register or run a task.

Set RC_RESUME02_TARGET to the frozen 558 script to reproduce the prior lexical rejection.
"""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
SCRIPT=Path(os.environ.get('RC_RESUME02_TARGET',str(ROOT/'tools/windows/mfa-service-read-system/Resume-MfaServiceReadSystemTrial02.ps1')))
BASE=ROOT/'tools/windows/mfa-service-read-system/Invoke-MfaServiceReadSystemTrial.ps1'
PS=shutil.which('powershell.exe')

def environment():
    value=os.environ.copy()
    value['PSModulePath']=str(Path(os.environ['SystemRoot'])/'System32/WindowsPowerShell/v1.0/Modules')+';'+str(Path(os.environ['ProgramFiles'])/'WindowsPowerShell/Modules')
    value.update(RC_RESUME02_SCRIPT=str(SCRIPT),RC_RESUME02_BASE=str(BASE))
    return value

LOAD=r'''
$ErrorActionPreference='Stop'
$text=[IO.File]::ReadAllText($env:RC_RESUME02_SCRIPT).Replace("`r`n","`n")
$cut=$text.LastIndexOf("`ntry {`n    if (`$Mode")
if($cut -lt 0){throw 'dispatcher_not_found'}
. ([scriptblock]::Create($text.Substring(0,$cut)))
. Import-ResumeBase $env:RC_RESUME02_BASE
'''

@unittest.skipUnless(PS,'Windows PowerShell5.1 required')
class SemanticTests(unittest.TestCase):
    def focus(self,tail,extra=None):
        with tempfile.TemporaryDirectory(prefix='rc-resume02-focus-') as directory:
            file=Path(directory)/'focus.ps1';file.write_text(LOAD+tail,encoding='ascii')
            env=environment()
            if extra:env.update(extra)
            out=subprocess.run([PS,'-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(file)],env=env,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=60)
        self.assertEqual(out.returncode,0,out.stdout+out.stderr)
        return json.loads(out.stdout)

    def test_equivalent_system_representations_are_accepted(self):
        data=self.focus(FIXTURE+r'''
$values=@()
foreach($case in @('canonical','system_alias','localized_alias','duration','runlevel','runlevel_omitted','service_account_logon','enabled','command','normalized_path','empty_cwd','combined')) {
 [xml]$doc=$canonical
 switch($case) {
  'system_alias' {$doc.Task.Principals.Principal.UserId='SYSTEM'}
  'localized_alias' {$doc.Task.Principals.Principal.UserId=(New-Object Security.Principal.SecurityIdentifier('S-1-5-18')).Translate([Security.Principal.NTAccount]).Value}
  'duration' {$doc.Task.Settings.ExecutionTimeLimit='PT240S'}
  'runlevel' {$doc.Task.Principals.Principal.RunLevel='LeastPrivilege'}
  'runlevel_omitted' {[void]$doc.Task.Principals.Principal.RemoveChild($doc.GetElementsByTagName('RunLevel')[0])}
  'service_account_logon' {$node=$doc.CreateElement('LogonType',$doc.DocumentElement.NamespaceURI);$node.InnerText='ServiceAccount';[void]$doc.Task.Principals.Principal.AppendChild($node)}
  'enabled' {$doc.Task.Settings.Enabled='1'}
  'command' {$doc.Task.Actions.Exec.Command=([string]$doc.Task.Actions.Exec.Command).ToUpperInvariant()}
  'normalized_path' {$doc.Task.Actions.Exec.Command=([string]$doc.Task.Actions.Exec.Command).Replace('\v1.0\','\v1.0\.\')}
  'empty_cwd' {$node=$doc.CreateElement('WorkingDirectory',$doc.DocumentElement.NamespaceURI);[void]$doc.Task.Actions.Exec.AppendChild($node)}
  'combined' {$doc.Task.Principals.Principal.UserId='SYSTEM';$doc.Task.Settings.ExecutionTimeLimit='PT240S';$doc.Task.Principals.Principal.RunLevel='LeastPrivilege';$doc.Task.Settings.Enabled='1'}
 }
 $code=Code {Assert-ResumeTask $doc.OuterXml $legacy $false}
 $values+=@{case=$case;code=$code;accepted=($code -ceq '')}
}
$values|ConvertTo-Json -Depth 5 -Compress
''')
        self.assertTrue(all(item['accepted'] for item in data),data)

    def test_material_differences_rejected_with_specific_codes(self):
        data=self.focus(FIXTURE+r'''
$cases=@(
 @{name='domain_system';field='user';value='OTHERDOMAIN\SYSTEM';code='task_userid_invalid'},
 @{name='other_builtin';field='user';value='S-1-5-19';code='task_userid_invalid'},
 @{name='long_timeout';field='duration';value='PT241S';code='task_execution_time_invalid'},
 @{name='bad_timeout';field='duration';value='not-duration';code='task_execution_time_invalid'},
 @{name='disabled';field='enabled';value='false';code='task_enabled_invalid'},
 @{name='other_exe';field='command';value='C:\Windows\System32\cmd.exe';code='task_command_invalid'},
 @{name='unc_exe';field='command';value='\\host\share\powershell.exe';code='task_command_invalid'},
 @{name='ads_exe';field='command';value='C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe:stream';code='task_command_invalid'},
 @{name='relative_exe';field='command';value='powershell.exe';code='task_command_invalid'},
 @{name='other_args';field='arguments';value='-NoProfile -Command whoami';code='task_arguments_invalid'},
 @{name='other_description';field='description';value='other';code='task_description_invalid'},
 @{name='nonempty_cwd';field='cwd';value='C:\Temp';code='task_working_directory_invalid'},
 @{name='password_logon';field='logon';value='Password';code='task_logon_type_invalid'},
 @{name='group_logon';field='group';value='S-1-5-32-544';code='task_group_invalid'},
 @{name='invalid_runlevel';field='runlevel';value='InvalidLevel';code='task_runlevel_invalid'},
 @{name='privileges';field='privileges';value='SeImpersonatePrivilege';code='system_privileges_must_be_omitted'},
 @{name='trigger';field='trigger';value='';code='task_triggers_invalid'},
 @{name='second_action';field='action';value='';code='task_action_invalid'},
 @{name='second_principal';field='principal';value='';code='task_principal_invalid'}
)
$rows=@()
foreach($case in $cases) {
 [xml]$doc=$canonical;$namespace=$doc.DocumentElement.NamespaceURI
 switch($case.field) {
  'user' {$doc.Task.Principals.Principal.UserId=$case.value}
  'duration' {$doc.Task.Settings.ExecutionTimeLimit=$case.value}
  'enabled' {$doc.Task.Settings.Enabled=$case.value}
  'command' {$doc.Task.Actions.Exec.Command=$case.value}
  'arguments' {$doc.Task.Actions.Exec.Arguments=$case.value}
  'description' {$doc.Task.RegistrationInfo.Description=$case.value}
  'cwd' {$n=$doc.CreateElement('WorkingDirectory',$namespace);$n.InnerText=$case.value;[void]$doc.Task.Actions.Exec.AppendChild($n)}
  'logon' {$n=$doc.CreateElement('LogonType',$namespace);$n.InnerText=$case.value;[void]$doc.Task.Principals.Principal.AppendChild($n)}
  'group' {$n=$doc.CreateElement('GroupId',$namespace);$n.InnerText=$case.value;[void]$doc.Task.Principals.Principal.AppendChild($n)}
  'runlevel' {$doc.Task.Principals.Principal.RunLevel=$case.value}
  'privileges' {$n=$doc.CreateElement('RequiredPrivileges',$namespace);$p=$doc.CreateElement('Privilege',$namespace);$p.InnerText=$case.value;[void]$n.AppendChild($p);[void]$doc.Task.Principals.Principal.AppendChild($n)}
  'trigger' {$n=$doc.CreateElement('BootTrigger',$namespace);[void]$doc.GetElementsByTagName('Triggers')[0].AppendChild($n)}
  'action' {[void]$doc.Task.Actions.AppendChild($doc.Task.Actions.Exec.CloneNode($true))}
  'principal' {[void]$doc.Task.Principals.AppendChild($doc.Task.Principals.Principal.CloneNode($true))}
 }
 $code=Code {Assert-ResumeTask $doc.OuterXml $legacy $false}
 $rows+=@{case=$case.name;expected=$case.code;actual=$code;passed=($code -ceq $case.code)}
}
$rows|ConvertTo-Json -Depth 5 -Compress
''')
        self.assertTrue(all(item['passed'] for item in data),data)

    def test_legacy_identification_requires_exact_privileges(self):
        data=self.focus(FIXTURE+r'''
[xml]$wrong=$legacy;$wrong.GetElementsByTagName('Privilege')[0].InnerText='SeShutdownPrivilege'
@{oldIdentified=((Code {Assert-ResumeTask $legacy $legacy $true}) -ceq '');wrongRejected=((Code {Assert-ResumeTask $wrong.OuterXml $legacy $true}) -ceq 'task_privileges_invalid')}|ConvertTo-Json -Compress
''')
        self.assertTrue(data['oldIdentified'])
        self.assertTrue(data['wrongRejected'])

    def test_registered_xml_is_saved_before_validation(self):
        text=SCRIPT.read_text(encoding='ascii')
        start=text.index("$stage='task_create'")
        body=text[start:]
        self.assertLess(body.index("'-registered-task.json'"),body.index('Assert-ResumeTask $xml'))
        self.assertIn('task.Definition.Principal.LogonType',body)

    def test_native_definition_keeps_system_and_omits_privileges(self):
        data=self.focus(FIXTURE+r'''
$definition=New-ResumeDefinition $scheduler $legacy
$definition.Principal.UserId='SYSTEM';$definition.Principal.LogonType=5
Assert-ResumeTask $definition.XmlText $legacy $false
@{nativeDefinitionValidated=$true;created=$false;ran=$false}|ConvertTo-Json -Compress
''')
        self.assertTrue(data['nativeDefinitionValidated'])
        self.assertFalse(data['created'])

FIXTURE=r'''
function Code([scriptblock]$Body){try{&$Body|Out-Null;return ''}catch{return Resume-Code $_}}
$legacy=Get-TaskXml 'C:\private\worker.ps1' 'C:\private\plan.json' ('a'*64) 'RackClick-MFA-SystemRead-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
$scheduler=New-Object -ComObject Schedule.Service
$canonical=(New-ResumeDefinition $scheduler $legacy).XmlText
'''

if __name__=='__main__':unittest.main(verbosity=2)
