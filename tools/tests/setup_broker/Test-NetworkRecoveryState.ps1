#requires -Version 5.1
param([string]$OutputPath='')
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot '..\..\windows\server-install\Get-RackClickNetworkRecoveryState.ps1') -FunctionsOnly
$checks=New-Object 'Collections.Generic.List[string]'
function Assert-RecoveryTest([bool]$Condition,[string]$Name){if(-not$Condition){throw ('Test failed: '+$Name)};$checks.Add($Name)}
$id='606b8c29-41de-4dc0-b63d-ade836000d9e'
$record=[ordered]@{schemaVersion=1;utc='2026-10-20T14:00:00.0000000Z';installationId=$id;stage='infrastructure';committed=$false;rollbackStatus='not_needed'}
$last=[ordered]@{schemaVersion=1;utc='2026-10-20T14:00:02.0000000Z';installationId=$id;stage='rollback_partial';committed=$false;rollbackStatus='rollback_partial'}
$selected=@((Select-RcRecoveryJournal @((ConvertTo-Json $record -Compress),(ConvertTo-Json $last -Compress))).records)
Assert-RecoveryTest ($selected.Count-eq2) 'Keep two actual transaction stages'
Assert-RecoveryTest ($selected[0].stage-ceq'infrastructure'-and$selected[1].stage-ceq'rollback_partial') 'Preserve original failure context and rollback terminal row'
foreach($case in @(
 @{name='foreign installation';key='installationId';value='11111111-1111-4111-8111-111111111111'},
 @{name='free-form stage';key='stage';value='secret_marker_value'},
 @{name='string instead of boolean';key='committed';value='false'},
 @{name='free-form rollback status';key='rollbackStatus';value='secret_marker_value'},
 @{name='invalid timestamp';key='utc';value='secret_marker_value'}
)){
 $copy=[ordered]@{};foreach($key in $record.Keys){$copy[$key]=$record[$key]};$copy[$case.key]=$case.value
 $selected=@((Select-RcRecoveryJournal @((ConvertTo-Json $copy -Compress))).records)
 Assert-RecoveryTest ($selected.Count-eq0) ('Do not export '+$case.name)
}
$selected=@((Select-RcRecoveryJournal @('not json')).records)
Assert-RecoveryTest ($selected.Count-eq0) 'Malformed input is not echoed'
$extra=[ordered]@{};foreach($key in $record.Keys){$extra[$key]=$record[$key]};$extra.private='do_not_export_private_marker'
$selected=@((Select-RcRecoveryJournal @((ConvertTo-Json $extra -Compress))).records)
Assert-RecoveryTest (-not(($selected|ConvertTo-Json -Depth 6)-match'do_not_export_private_marker|"private"')) 'Extra private journal property never exported'
$large=Select-RcRecoveryJournal @(('x'*8193))
Assert-RecoveryTest (@($large.records).Count-eq0-and$large.invalidRows-eq1) 'Oversized journal input is omitted'
$many=Select-RcRecoveryJournal @((1..70|ForEach-Object{ConvertTo-Json $record -Compress}))
Assert-RecoveryTest (@($many.records).Count-eq64) 'Journal report is bounded to 64 rows'
$addresses=Select-RcRecoveryAddresses @('192.168.250.0/24','192.168.250.0/255.255.255.0')
Assert-RecoveryTest ($addresses.Count-eq2-and$addresses[0]-ceq'192.168.250.0/24'-and$addresses[1]-ceq'192.168.250.0/255.255.255.0') 'Preserve both provider subnet representations for diagnosis'
$unsafe=Select-RcRecoveryAddresses @('private_marker','C:\private_marker')
Assert-RecoveryTest (($unsafe-join',')-ceq'unlisted,unlisted') 'Unlisted address content is not echoed'
$bounded=Select-RcRecoveryAddresses @(1..12|ForEach-Object{'192.168.250.'+[string]$_})
Assert-RecoveryTest ($bounded.Count-eq8) 'Address output has a fixed bound'
$original='O:BAG:SYD:AI(A;ID;FA;;;BA)(A;ID;FA;;;SY)'
$protected='O:BAG:SYD:PAI(A;ID;FA;;;BA)(A;ID;FA;;;SY)'
$same=Get-RcRecoveryAclDifference $original $original
Assert-RecoveryTest ($same.ownerMatches-and$same.groupMatches-and$same.daclProtectedMatches-and$same.aceCountMatches) 'Equal security descriptors compare equal without exposing them'
$difference=Get-RcRecoveryAclDifference $protected $original
Assert-RecoveryTest ($difference.ownerMatches-and$difference.groupMatches-and$difference.aceCountMatches-and-not$difference.daclProtectedMatches) 'Detect a protected-DACL change despite matching owner, group and ACE count'
$ownerDifferent=Get-RcRecoveryAclDifference 'O:SYG:SYD:AI(A;ID;FA;;;BA)(A;ID;FA;;;SY)' $original
Assert-RecoveryTest (-not$ownerDifferent.ownerMatches-and$ownerDifferent.groupMatches) 'Detect owner changes separately'
Assert-RecoveryTest (-not(($difference|ConvertTo-Json -Depth 4)-match'O:|D:|S-1-|BA\)|SY\)')) 'ACL summary contains no raw descriptor or SID'
$sid='S-1-5-21-1-2-3-1001'
foreach($observed in @($sid,'.\rackclicksvc','fixture\RackClickSvc')){
 Assert-RecoveryTest ((Test-RcRecoveryPrincipalLocalMatch $observed $sid 'FIXTURE' 'RackClickSvc')-eq$true) 'Compare known SID or explicitly local account without external lookup'
}
Assert-RecoveryTest ((Test-RcRecoveryPrincipalLocalMatch 'S-1-5-21-1-2-3-1002' $sid 'FIXTURE' 'RackClickSvc')-eq$false) 'Different literal SID is a confirmed mismatch'
foreach($observed in @('DOMAIN\RackClickSvc','RackClickSvc@example.test','RackClickSvc')){
 Assert-RecoveryTest ($null-eq(Test-RcRecoveryPrincipalLocalMatch $observed $sid 'FIXTURE' 'RackClickSvc')) 'Unexpected domain, UPN or unqualified principal remains unverified'
}
Assert-RecoveryTest ($null-eq(Test-RcRecoveryPrincipalLocalMatch '.\RackClickSvc' $sid 'FIXTURE' '')) 'Missing local SAM result does not trigger alternate resolution'
$parseErrors=$null;$tokens=$null
$ast=[Management.Automation.Language.Parser]::ParseFile((Join-Path $PSScriptRoot '..\..\windows\server-install\Get-RackClickNetworkRecoveryState.ps1'),[ref]$tokens,[ref]$parseErrors)
$translations=@($ast.FindAll({param($node) $node-is[Management.Automation.Language.InvokeMemberExpressionAst]-and$node.Member.Extent.Text-ceq'Translate'},$true))
$resolutions=@($ast.FindAll({param($node) $node-is[Management.Automation.Language.CommandAst]-and$node.GetCommandName()-ceq'Resolve-RcNetworkSid'},$true))
Assert-RecoveryTest ($parseErrors.Count-eq0-and$translations.Count-eq0-and$resolutions.Count-eq0) 'Collector parses and has no NTAccount translation invocation'
$result=[ordered]@{schemaVersion=1;valid=$true;passed=$checks.Count;checks=@($checks);environment='Windows PowerShell 5.1; journal projections and in-memory ACL descriptors only';privilegedOperationsExecuted=0;serviceOperationsExecuted=0;databaseOperationsExecuted=0;credentialsRead=0}
if($OutputPath){[IO.File]::WriteAllText($OutputPath,($result|ConvertTo-Json -Depth 6),(New-Object Text.UTF8Encoding($false)))}
$result|ConvertTo-Json -Depth 6 -Compress
