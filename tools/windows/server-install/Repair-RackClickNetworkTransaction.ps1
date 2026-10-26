#requires -Version 5.1
[CmdletBinding()]
param([string]$NetworkScriptPath='',[string]$NetworkScriptSha256='',[switch]$FunctionsOnly)
# Repairs only the recorded 606b / 16b82 rollback. No service start, credentials or database operations.
function Stop-RcRepair([string]$Code){throw (New-Object InvalidOperationException($Code))}
function Get-RcRepairCodes {return @('network_repair_failed','network_repair_index_invalid','network_repair_task_xml_invalid','network_repair_files_changed','network_repair_task_changed','network_repair_service_binding_invalid','network_repair_postgres_pid_present','network_repair_port_in_use','network_repair_firewall_changed','network_repair_task_binding_invalid','network_repair_journal_invalid','network_repair_verification_failed','network_repair_preflight_required','network_repair_elevated_winps51_x64_required','network_repair_source_hash_required','network_repair_source_invalid','network_repair_source_hash_mismatch','network_repair_source_api_missing','network_repair_receipt_invalid','network_repair_local_account_unverified','network_repair_infrastructure_invalid','network_repair_configuration_invalid','network_repair_closed_state_changed')}
function Get-RcRepairHash([byte[]]$Bytes){$sha=[Security.Cryptography.SHA256]::Create();try{return ([BitConverter]::ToString($sha.ComputeHash($Bytes))).Replace('-','').ToLowerInvariant()}finally{$sha.Dispose()}}
function Read-RcRepairJournalState([byte[]]$Bytes){
    $lines=@([Text.Encoding]::UTF8.GetString($Bytes)-split'\r?\n'|Where-Object{$_.Length-gt0});if($lines.Count-lt3-or$lines.Count-gt512){Stop-RcRepair 'network_repair_journal_invalid'};$first='';$infrastructure=$false;$last=$null
    $allowed=@('snapshot_started','snapshot_complete','stopping','files','write_profile','write_config','write_receipt','write_root','write_public','write_pfx','write_managementCa','infrastructure','verification','rollback_partial','repair_started','repair_acl','repair_task','repair_verification','repair_failed','rollback_restored_service_stopped')
    foreach($line in $lines){try{if($line.Length-gt8192){throw 'invalid'};$r=$line|ConvertFrom-Json;$utc=[DateTimeOffset]::MinValue;if($r.schemaVersion-ne1-or$r.installationId-cne'606b8c29-41de-4dc0-b63d-ade836000d9e'-or$r.committed-isnot[bool]-or$r.committed-or$r.stage-cnotin$allowed-or$r.rollbackStatus-cnotin@('not_needed','rollback_partial','rollback_restored_service_stopped')-or$r.utc-isnot[string]-or-not[DateTimeOffset]::TryParseExact($r.utc,'o',[Globalization.CultureInfo]::InvariantCulture,[Globalization.DateTimeStyles]::None,[ref]$utc)){throw 'invalid'};if($first-ceq''){$first=$r.stage};if($r.stage-ceq'infrastructure'){$infrastructure=$true};$last=$r}catch{Stop-RcRepair 'network_repair_journal_invalid'}}
    if($first-cne'snapshot_started'-or-not$infrastructure-or$last.stage-cnotin@('rollback_partial','repair_started','repair_acl','repair_task','repair_verification','repair_failed','rollback_restored_service_stopped')-or($last.stage-ceq'rollback_restored_service_stopped'-and$last.rollbackStatus-cne'rollback_restored_service_stopped')){Stop-RcRepair 'network_repair_journal_invalid'}
    return @{alreadyClosed=($last.stage-ceq'rollback_restored_service_stopped');rowCount=$lines.Count}
}
function Get-RcRepairExpectedPaths([string]$Base){return @{profile=($Base+'\instance\runtime\server-profile.json');config=($Base+'\instance\service-config.json');root=($Base+'\instance\runtime\RootCA.cer');public=($Base+'\instance\runtime\server.cer');pfx=($Base+'\instance\runtime\server.pfx');'tls-password'=($Base+'\instance\runtime\tls-password.txt');managementCa=($Base+'\management\RootCA.cer');receipt=($Base+'\management\server-installation.json')}}
function Read-RcRepairIndex([byte[]]$Bytes,[hashtable]$Expected){
    $entries=ConvertFrom-Json -InputObject ([Text.Encoding]::UTF8.GetString($Bytes)) -ErrorAction Stop
    if($entries-isnot[Array]-or$entries.Count-ne8-or$Expected.Count-ne8){Stop-RcRepair 'network_repair_index_invalid'};$keys=@{};$names=@{}
    foreach($e in $entries){if($null-eq$e-or$e.key-isnot[string]-or$e.path-isnot[string]-or$e.backup-isnot[string]-or$e.sha256-isnot[string]-or$e.sddl-isnot[string]-or$e.key-cnotin$Expected.Keys-or$keys.ContainsKey($e.key)-or$e.path-cne$Expected[$e.key]-or$e.backup-cnotmatch'^file-[0-7]\.bin$'-or$names.ContainsKey($e.backup)-or$e.sha256-cnotmatch'^[a-f0-9]{64}$'-or$e.sddl.Length-gt65536){Stop-RcRepair 'network_repair_index_invalid'};$keys[$e.key]=$true;$names[$e.backup]=$true;try{$null=New-Object Security.AccessControl.RawSecurityDescriptor($e.sddl)}catch{Stop-RcRepair 'network_repair_index_invalid'}}
    return ,$entries
}
function Get-RcRepairAclState([string]$Key,[string]$CurrentSddl,[string]$BackupSddl){
    try{$a=New-Object Security.AccessControl.RawSecurityDescriptor($CurrentSddl);$b=New-Object Security.AccessControl.RawSecurityDescriptor($BackupSddl);$sections=[Security.AccessControl.AccessControlSections]::All
        if($a.GetSddlForm($sections)-ceq$b.GetSddlForm($sections)){return 'exact'}
        $flag=[Security.AccessControl.ControlFlags]::DiscretionaryAclProtected
        if($Key-cnotin@('managementCa','receipt')-or($b.ControlFlags-band$flag)-ne0-or$null-eq$b.DiscretionaryAcl){return 'rejected'}
        # Exact variant reproduced by PS101 SetAcl: protection/AI added, inherited ACE markers removed.
        $b.SetFlags([Security.AccessControl.ControlFlags]([int]$b.ControlFlags-bor[int]$flag-bor[int][Security.AccessControl.ControlFlags]::DiscretionaryAclAutoInherited))
        foreach($ace in $b.DiscretionaryAcl){$ace.AceFlags=[Security.AccessControl.AceFlags]([int]$ace.AceFlags-band(-bnot[int][Security.AccessControl.AceFlags]::Inherited))}
        if($a.GetSddlForm($sections)-ceq$b.GetSddlForm($sections)){return 'known_inheritance_change'}
    }catch{};return 'rejected'
}
function ConvertTo-RcRepairTaskDocument([string]$Text){
    if([string]::IsNullOrEmpty($Text)-or$Text.Length-gt1048576){Stop-RcRepair 'network_repair_task_xml_invalid'}
    $settings=New-Object Xml.XmlReaderSettings;$settings.DtdProcessing=[Xml.DtdProcessing]::Prohibit;$settings.XmlResolver=$null;$settings.MaxCharactersInDocument=1048576
    $textReader=New-Object IO.StringReader($Text);$reader=[Xml.XmlReader]::Create($textReader,$settings)
    try{$document=New-Object Xml.XmlDocument;$document.XmlResolver=$null;$document.PreserveWhitespace=$false;$document.Load($reader);if($document.DocumentElement.LocalName-cne'Task'-or$document.DocumentElement.NamespaceURI-cne'http://schemas.microsoft.com/windows/2004/02/mit/task'){Stop-RcRepair 'network_repair_task_xml_invalid'};return ,$document}finally{$reader.Dispose();$textReader.Dispose()}
}
function Get-RcRepairTaskNodes($Document,[string]$Path){$ns=New-Object Xml.XmlNamespaceManager($Document.NameTable);$ns.AddNamespace('t','http://schemas.microsoft.com/windows/2004/02/mit/task');return ,$Document.SelectNodes($Path,$ns)}
function Compare-RcRecoveryTaskXml([string]$CurrentXml,[string]$BackupXml){
    $a=ConvertTo-RcRepairTaskDocument $CurrentXml;$b=ConvertTo-RcRepairTaskDocument $BackupXml;$an=Get-RcRepairTaskNodes $a '/t:Task/t:Settings/t:Enabled';$bn=Get-RcRepairTaskNodes $b '/t:Task/t:Settings/t:Enabled'
    if((Get-RcRepairTaskNodes $a '/t:Task/t:Settings').Count-ne1-or(Get-RcRepairTaskNodes $b '/t:Task/t:Settings').Count-ne1-or$an.Count-gt1-or$bn.Count-gt1-or($an.Count-eq1-and$an[0].InnerText-cnotin@('true','false'))-or($bn.Count-eq1-and$bn[0].InnerText-cnotin@('true','false'))){Stop-RcRepair 'network_repair_task_xml_invalid'}
    # Task Settings.Enabled defaults to true; only its explicit value can be
    # toggled by Disable/Enable-ScheduledTask. Remove the node for comparison
    # instead of inserting it at a different position in the settings sequence.
    $ae=$an.Count-eq0-or$an[0].InnerText-ceq'true';$be=$bn.Count-eq0-or$bn[0].InnerText-ceq'true'
    foreach($node in $an){$null=$node.ParentNode.RemoveChild($node)};foreach($node in $bn){$null=$node.ParentNode.RemoveChild($node)}
    foreach($doc in @($a,$b)){
        $level=Get-RcRepairTaskNodes $doc '/t:Task/t:Principals/t:Principal/t:RunLevel'
        if($level.Count-gt1){Stop-RcRepair 'network_repair_task_xml_invalid'}
        if($level.Count-eq1-and$level[0].InnerText-ceq'LeastPrivilege'){$null=$level[0].ParentNode.RemoveChild($level[0])}
    }
    $equal=$a.OuterXml-ceq$b.OuterXml
    return @{exact=($equal-and$ae-eq$be);matchesExceptEnabled=$equal;currentEnabled=$ae;backupEnabled=$be}
}
function Test-RcRepairLocalPrincipal([string]$Observed,[string]$ExpectedSid,[string]$LocalMachine,[string]$LocalName){
    try{$sid=(New-Object Security.Principal.SecurityIdentifier($ExpectedSid)).Value;if($Observed-cmatch'^S-1-'){return (New-Object Security.Principal.SecurityIdentifier($Observed)).Value-ceq$sid}}catch{return $false}
    if([string]::IsNullOrEmpty($LocalMachine)-or[string]::IsNullOrEmpty($LocalName)-or$LocalMachine.Contains('\')-or$LocalMachine.Contains('@')-or$LocalName.Contains('\')-or$LocalName.Contains('@')){return $false}
    $name=if($Observed.StartsWith('.\',[StringComparison]::Ordinal)){$Observed.Substring(2)}elseif($Observed.StartsWith(($LocalMachine+'\'),[StringComparison]::OrdinalIgnoreCase)){$Observed.Substring($LocalMachine.Length+1)}elseif(-not$Observed.Contains('\')-and-not$Observed.Contains('@')){$Observed}else{return $false}
    return [string]::Equals($name,$LocalName,[StringComparison]::OrdinalIgnoreCase)
}
function Get-RcRepairOriginalTaskBinding($Context,$Document){
    $principal=Get-RcRepairTaskNodes $Document '/t:Task/t:Principals/t:Principal';$actions=Get-RcRepairTaskNodes $Document '/t:Task/t:Actions/*'
    $command=Get-RcRepairTaskNodes $Document '/t:Task/t:Actions/t:Exec/t:Command';$arguments=Get-RcRepairTaskNodes $Document '/t:Task/t:Actions/t:Exec/t:Arguments'
    $user=Get-RcRepairTaskNodes $Document '/t:Task/t:Principals/t:Principal/t:UserId';$group=Get-RcRepairTaskNodes $Document '/t:Task/t:Principals/t:Principal/t:GroupId'
    $logon=Get-RcRepairTaskNodes $Document '/t:Task/t:Principals/t:Principal/t:LogonType';$level=Get-RcRepairTaskNodes $Document '/t:Task/t:Principals/t:Principal/t:RunLevel'
    # MS-TSCH 3.2.5.4.2 mandates LeastPrivilege when RunLevel is absent.
    # Never apply that default to empty, duplicate or explicit elevated values.
    $representation=if($level.Count-eq0){'omitted_default'}elseif($level.Count-ne1){'duplicate'}elseif($level[0].InnerText-ceq'LeastPrivilege'){'least_privilege'}elseif($level[0].InnerText-ceq'HighestAvailable'){'highest_available'}else{'invalid'}
    $answer=[ordered]@{valid=$false;principalSingle=($principal.Count-eq1);actionSingle=($actions.Count-eq1);commandSingle=($command.Count-eq1);commandMatches=($command.Count-eq1-and$command[0].InnerText-ceq$Context.receipt.backupExecutable);argumentsSingle=($arguments.Count-eq1);argumentsMatch=($arguments.Count-eq1-and$arguments[0].InnerText-ceq$Context.receipt.backupArguments);userSingle=($user.Count-eq1);userSidMatches=($user.Count-eq1-and(Test-RcRepairLocalPrincipal $user[0].InnerText $Context.receipt.serviceSid $Context.localMachine $Context.localName));noGroupPrincipal=($group.Count-eq0);logonTypeSingle=($logon.Count-eq1);logonTypePassword=($logon.Count-eq1-and$logon[0].InnerText-ceq'Password');runLevelRepresentation=$representation;leastPrivilege=($representation-cin@('omitted_default','least_privilege'))}
    $answer.valid=$answer.principalSingle-and$answer.actionSingle-and$answer.commandSingle-and$answer.commandMatches-and$answer.argumentsSingle-and$answer.argumentsMatch-and$answer.userSingle-and$answer.userSidMatches-and$answer.noGroupPrincipal-and$answer.logonTypeSingle-and$answer.logonTypePassword-and$answer.leastPrivilege
    return $answer
}
function Get-RcRepairCurrentTaskBinding($Context,$Task){
    $answer=[ordered]@{valid=$false;readable=$false;notRunning=$false;logonTypePassword=$false;limitedRunLevel=$false;userSidMatches=$false;actionSingle=$false;executableMatches=$false;argumentsMatch=$false}
    try{$answer.notRunning=([string]$Task.State-cin@('Disabled','Ready'));$answer.logonTypePassword=([string]$Task.Principal.LogonType-ceq'Password');$answer.limitedRunLevel=([string]$Task.Principal.RunLevel-ceq'Limited');$answer.userSidMatches=Test-RcRepairLocalPrincipal $Task.Principal.UserId $Context.receipt.serviceSid $Context.localMachine $Context.localName;$answer.actionSingle=(@($Task.Actions).Count-eq1);$answer.executableMatches=$answer.actionSingle-and$Task.Actions[0].Execute-ceq$Context.receipt.backupExecutable;$answer.argumentsMatch=$answer.actionSingle-and$Task.Actions[0].Arguments-ceq$Context.receipt.backupArguments;$answer.readable=$true}catch{}
    $answer.valid=$answer.readable-and$answer.notRunning-and$answer.logonTypePassword-and$answer.limitedRunLevel-and$answer.userSidMatches-and$answer.actionSingle-and$answer.executableMatches-and$answer.argumentsMatch
    return $answer
}
function Get-RcRecoveryRepairPlan([object[]]$FileStates,$TaskComparison){
    $keys=@('profile','config','root','public','pfx','tls-password','managementCa','receipt');$seen=@{};$repairs=@()
    if($FileStates.Count-ne8){Stop-RcRepair 'network_repair_files_changed'}
    foreach($s in $FileStates){if($s.key-cnotin$keys-or$seen.ContainsKey([string]$s.key)-or$s.backupShaValid-isnot[bool]-or-not$s.backupShaValid-or$s.currentMatchesBackup-isnot[bool]-or-not$s.currentMatchesBackup-or$s.aclState-cnotin@('exact','known_inheritance_change')){Stop-RcRepair 'network_repair_files_changed'};$seen[$s.key]=$true;if($s.aclState-ceq'known_inheritance_change'){if($s.key-cnotin@('managementCa','receipt')){Stop-RcRepair 'network_repair_files_changed'};$repairs+=@([string]$s.key)}}
    if($TaskComparison.exact-isnot[bool]-or$TaskComparison.matchesExceptEnabled-isnot[bool]-or-not$TaskComparison.matchesExceptEnabled-or$TaskComparison.backupEnabled-isnot[bool]-or-not$TaskComparison.backupEnabled-or$TaskComparison.currentEnabled-isnot[bool]){Stop-RcRepair 'network_repair_task_changed'}
    return @{aclKeys=$repairs;taskEnableRequired=(-not$TaskComparison.currentEnabled);alreadyRestored=($repairs.Count-eq0-and$TaskComparison.exact)}
}
function Read-RcRepairPrivate([string]$Path){Assert-RcNetworkManagementAcl $Path;return ,([RackClickNetworkMaintenanceNative]::Snapshot($Path).Bytes)}
function Read-RcRepairSnapshot([string]$Path){$old=$null;try{$old=[RackClickSetupSecurityNative]::Privilege('SeBackupPrivilege',2);return [RackClickNetworkMaintenanceNative]::Snapshot($Path)}finally{if($null-ne$old){$null=[RackClickSetupSecurityNative]::Privilege('SeBackupPrivilege',$old)}}}
function Read-RcRepairFileStates($Context){
    $states=@();$Context.documents=@{}
    foreach($e in $Context.entries){$backup=$null;$current=$null;try{$backup=Read-RcRepairPrivate (Join-Path $Context.transactionDirectory $e.backup);$valid=(Get-RcRepairHash $backup)-ceq$e.sha256;$current=Read-RcRepairSnapshot $e.path;Assert-RcNetworkSnapshotAcl @{Sddl=$e.sddl} $(if($e.key-cin@('managementCa','receipt')){@('S-1-5-18','S-1-5-32-544')}else{@('S-1-5-18',$Context.receipt.serviceSid)});$states+=@(@{key=$e.key;backupShaValid=$valid;currentMatchesBackup=((Get-RcRepairHash $current.Bytes)-ceq$e.sha256);aclState=(Get-RcRepairAclState $e.key $current.Sddl $e.sddl)});if($e.key-cin@('profile','config','receipt')){$Context.documents[$e.key]=[Text.Encoding]::UTF8.GetString($current.Bytes)|ConvertFrom-Json}}finally{if($e.key-cin@('pfx','tls-password')){if($backup){[Array]::Clear($backup,0,$backup.Length)};if($current){[Array]::Clear($current.Bytes,0,$current.Bytes.Length)}}}}
    return ,$states
}
function Assert-RcRepairServiceAndFirewall($Context){
    $r=$Context.receipt;$service=@(Get-CimInstance Win32_Service -Filter "Name='RackClick'");$binary='"'+$r.instancePath+'\content\dependencies\dotnet\dotnet.exe" "'+$r.codeRoot+'\service\RackClick.WindowsService.dll" --config "'+$r.instancePath+'\service-config.json"'
    if($service.Count-ne1-or$service[0].State-cne'Stopped'-or$service[0].ProcessId-ne0-or$service[0].PathName-cne$binary-or-not(Test-RcRepairLocalPrincipal $service[0].StartName $r.serviceSid $Context.localMachine $Context.localName)){Stop-RcRepair 'network_repair_service_binding_invalid'}
    $old=$null;try{$old=[RackClickSetupSecurityNative]::Privilege('SeBackupPrivilege',2);if([RackClickNetworkMaintenanceNative]::Exists(($Context.instanceRoot+'\pgdata\postmaster.pid'))){Stop-RcRepair 'network_repair_postgres_pid_present'}}finally{if($null-ne$old){$null=[RackClickSetupSecurityNative]::Privilege('SeBackupPrivilege',$old)}}
    $ports=@([Net.NetworkInformation.IPGlobalProperties]::GetIPGlobalProperties().GetActiveTcpListeners()|ForEach-Object{$_.Port});if(5443-in$ports-or55441-in$ports){Stop-RcRepair 'network_repair_port_in_use'}
    $rules=@(Get-NetFirewallRule -Name $r.firewallRule);if($rules.Count-ne1-or$rules[0].Enabled-ne'True'-or$rules[0].Profile-ne'Any'-or$rules[0].Direction-ne'Inbound'-or$rules[0].Action-ne'Allow'){Stop-RcRepair 'network_repair_firewall_changed'}
    $port=$rules[0]|Get-NetFirewallPortFilter;$app=$rules[0]|Get-NetFirewallApplicationFilter;$addresses=$rules[0]|Get-NetFirewallAddressFilter
    if($port.Protocol-ne'TCP'-or$port.LocalPort-ne'5443'-or$app.Program-cne($r.instancePath+'\content\dependencies\dotnet\dotnet.exe')-or-not(Test-RcNetworkFirewallAddresses @($addresses.LocalAddress) @($Context.infrastructure.firewall.local))-or-not(Test-RcNetworkFirewallAddresses @($addresses.RemoteAddress) @($Context.infrastructure.firewall.remote))){Stop-RcRepair 'network_repair_firewall_changed'}
}
function Read-RcRepairTaskState($Context){
    if(-not$Context.ContainsKey('taskValidation')){$Context.taskValidation=@{}}
    $r=$Context.receipt;$task=Get-ScheduledTask -TaskName $r.backupTaskName -TaskPath '\';$Context.taskValidation.current=Get-RcRepairCurrentTaskBinding $Context $task;if(-not$Context.taskValidation.current.valid){Stop-RcRepair 'network_repair_task_binding_invalid'}
    $xml=Export-ScheduledTask -TaskName $r.backupTaskName -TaskPath '\';$comparison=Compare-RcRecoveryTaskXml $xml $Context.originalTaskXml;$Context.taskValidation.xmlMatchesExceptEnabled=$comparison.matchesExceptEnabled;$Context.taskValidation.enabledMatchesXml=([bool]$task.Settings.Enabled-eq$comparison.currentEnabled);if(-not$Context.taskValidation.enabledMatchesXml){Stop-RcRepair 'network_repair_task_binding_invalid'};return $comparison
}
function Write-RcRepairJournal($Context,[string]$Stage){
    if($Stage-cnotin@('repair_started','repair_acl','repair_task','repair_verification','repair_failed','rollback_restored_service_stopped')){Stop-RcRepair 'network_repair_journal_invalid'};$Context.stage=$Stage
    $status=if($Stage-ceq'rollback_restored_service_stopped'){$Stage}else{'rollback_partial'};$record=@{schemaVersion=1;utc=[DateTime]::UtcNow.ToString('o');installationId=$Context.installationId;stage=$Stage;committed=$false;rollbackStatus=$status;repairVersion=2}
    $bytes=[Text.Encoding]::UTF8.GetBytes(($record|ConvertTo-Json -Compress));$h=[IO.File]::Open($Context.journalPath,'Append','Write','Read');try{$h.Write($bytes,0,$bytes.Length);$h.WriteByte(10);$h.Flush($true)}finally{$h.Dispose()}
}
function Set-RcRepairAcl($Context){foreach($key in $Context.plan.aclKeys){$e=@($Context.entries|Where-Object{$_.key-ceq$key})[0];Invoke-SetupSecurityPrivileges {Set-RcNetworkExactAcl $e.path $e.sddl}}}
function Enable-RcRepairTask($Context){if($Context.plan.taskEnableRequired){$null=Enable-ScheduledTask -TaskName $Context.receipt.backupTaskName -TaskPath '\'}}
function Test-RcRepairRestored($Context){
    Assert-RcRepairServiceAndFirewall $Context;$states=Read-RcRepairFileStates $Context;$task=Read-RcRepairTaskState $Context;$plan=Get-RcRecoveryRepairPlan $states $task
    if(-not$plan.alreadyRestored){Stop-RcRepair 'network_repair_verification_failed'};return $true
}
function Invoke-RcRecoveryRepairTransaction($Context){
    if(-not$Context.preflightComplete){Stop-RcRepair 'network_repair_preflight_required'}
    if($Context.plan.alreadyRestored-and$Context.journalAlreadyClosed){if(-not(Test-RcRepairRestored $Context)){Stop-RcRepair 'network_repair_verification_failed'};$Context.completed=$true;$Context.alreadyRestored=$true;$Context.rollbackStatus='rollback_restored_service_stopped';return $true}
    try{Write-RcRepairJournal $Context 'repair_started';if($Context.plan.aclKeys.Count){Write-RcRepairJournal $Context 'repair_acl';$Context.mutationsStarted=$true;Set-RcRepairAcl $Context};if($Context.plan.taskEnableRequired){Write-RcRepairJournal $Context 'repair_task';$Context.mutationsStarted=$true;Enable-RcRepairTask $Context};Write-RcRepairJournal $Context 'repair_verification';if(-not(Test-RcRepairRestored $Context)){Stop-RcRepair 'network_repair_verification_failed'};Write-RcRepairJournal $Context 'rollback_restored_service_stopped';$Context.completed=$true;$Context.rollbackStatus='rollback_restored_service_stopped';return $true}
    catch{$Context.failureStage=$Context.stage;$Context.completed=$false;$Context.rollbackStatus='rollback_partial';try{Write-RcRepairJournal $Context 'repair_failed'}catch{$Context.journalWriteFailed=$true};throw}
}
if($FunctionsOnly){return}
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$id='606b8c29-41de-4dc0-b63d-ade836000d9e';$token='16b82e5914dc46c288ce1119b965bbfc';$base='C:\ProgramData\RackClick\Instances\'+$id;$management=$base+'\management';$transaction=$management+'\network-change-'+$token
$result=[ordered]@{schemaVersion=1;repairVersion=2;valid=$false;success=$false;exitCode=2;code='network_repair_failed';installationId=$id;transactionId=$token;journalDirectory=$transaction;stage='preflight';rollbackStatus='rollback_partial';networkChangeApplied=$false;repairPerformed=$false;mutationsAttempted=$false;serviceStarted=$false;credentialsRead=0;authenticationAttempts=0;databasesChanged=0;rootStoreChanged=0}
$context=$null;$maintenance=$null;$sourceLock=$null;$exit=2;$oldModulePath=$env:PSModulePath
try{
    if($PSVersionTable.PSEdition-cne'Desktop'-or$PSVersionTable.PSVersion.Major-ne5-or-not[Environment]::Is64BitProcess-or-not(New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)){Stop-RcRepair 'network_repair_elevated_winps51_x64_required'}
    $env:PSModulePath=Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\Modules';if($NetworkScriptSha256-cnotmatch'^[a-f0-9]{64}$'){Stop-RcRepair 'network_repair_source_hash_required'};if($NetworkScriptPath-ceq''){$NetworkScriptPath=Join-Path $PSScriptRoot 'Set-RackClickServerNetwork.ps1'}
    $NetworkScriptPath=[IO.Path]::GetFullPath($NetworkScriptPath);$cursor=$NetworkScriptPath;if($cursor.StartsWith('\\')){Stop-RcRepair 'network_repair_source_invalid'};while($cursor){if(((Get-Item -LiteralPath $cursor -Force).Attributes-band[IO.FileAttributes]::ReparsePoint)-ne0){Stop-RcRepair 'network_repair_source_invalid'};$cursor=[IO.Path]::GetDirectoryName($cursor)}
    $sourceLock=[IO.File]::Open($NetworkScriptPath,'Open','Read','Read');if((Get-FileHash -LiteralPath $NetworkScriptPath -Algorithm SHA256).Hash.ToLowerInvariant()-cne$NetworkScriptSha256){Stop-RcRepair 'network_repair_source_hash_mismatch'};. $NetworkScriptPath -FunctionsOnly
    foreach($fn in @('Set-RcNetworkExactAcl','Test-RcNetworkFirewallAddresses')){if(-not(Get-Command $fn -CommandType Function -ErrorAction SilentlyContinue)){Stop-RcRepair 'network_repair_source_api_missing'}}
    Assert-RcNetworkManagementAcl $management;Assert-RcNetworkManagementAcl $transaction;Assert-RcNetworkManagementAcl ($management+'\network-maintenance.lock');$maintenance=[IO.File]::Open(($management+'\network-maintenance.lock'),'Open','Read','None')
    $context=@{installationId=$id;transactionDirectory=$transaction;journalPath=($transaction+'\journal.jsonl');receipt=@{codeRoot=('C:\Program Files\RackClick\'+$id)};codeLocks=(New-Object Collections.ArrayList);runtime=($base+'\instance\runtime');instanceRoot=($base+'\instance\deployment\instance');instanceLock=$null;backupLock=$null;preflightComplete=$false;completed=$false;alreadyRestored=$false;mutationsStarted=$false;stage='preflight';rollbackStatus='rollback_partial'}
    Import-RcNetworkHelpers $context;Initialize-SetupSecurityNative;Initialize-RcNetworkNative
    $context.entries=Read-RcRepairIndex (Read-RcRepairPrivate ($transaction+'\files.json')) (Get-RcRepairExpectedPaths $base)
    $e=@($context.entries|Where-Object{$_.key-ceq'receipt'})[0];$bytes=Read-RcRepairPrivate (Join-Path $transaction $e.backup);if((Get-RcRepairHash $bytes)-cne$e.sha256){Stop-RcRepair 'network_repair_receipt_invalid'};$r=[Text.Encoding]::UTF8.GetString($bytes)|ConvertFrom-Json
    if($r.schemaVersion-ne1-or$r.installationId-cne$id-or$r.managementPath-cne$management-or$r.instancePath-cne($base+'\instance')-or$r.codeRoot-cne$context.receipt.codeRoot-or$r.serviceName-cne'RackClick'-or$r.firewallRule-cne('RackClick-'+$id)-or$r.serviceSid-cnotmatch'^S-1-5-21-(\d+-){3}\d+$'-or$r.backupTaskName-cne('RackClick-Backup-'+$id)-or$r.manifestSha256-cnotmatch'^[a-f0-9]{64}$'){Stop-RcRepair 'network_repair_receipt_invalid'};$context.receipt=$r
    $expectedArgs='-NoProfile -NonInteractive -ExecutionPolicy Bypass -File '+(ConvertTo-SetupArgument ($r.codeRoot+'\operators\server-install\Invoke-RackClickScheduledBackup.ps1'))+' -ManifestPath '+(ConvertTo-SetupArgument ($context.runtime+'\server-profile.json'))+' -ExpectedManifestSha256 '+$r.manifestSha256
    if($r.backupExecutable-cne($env:SystemRoot+'\System32\WindowsPowerShell\v1.0\powershell.exe')-or$r.backupArguments-cne$expectedArgs){Stop-RcRepair 'network_repair_receipt_invalid'}
    $sam=@(Get-LocalUser -SID (New-Object Security.Principal.SecurityIdentifier($r.serviceSid)));if($sam.Count-ne1-or$sam[0].SID.Value-cne$r.serviceSid){Stop-RcRepair 'network_repair_local_account_unverified'};$context.localName=[string]$sam[0].Name;$context.localMachine=[Environment]::MachineName
    $context.infrastructure=[Text.Encoding]::UTF8.GetString((Read-RcRepairPrivate ($transaction+'\infrastructure.json')))|ConvertFrom-Json;if($context.infrastructure.taskWasEnabled-isnot[bool]-or-not$context.infrastructure.taskWasEnabled-or$context.infrastructure.serviceWasRunning-isnot[bool]-or$context.infrastructure.taskArguments-cne$r.backupArguments){Stop-RcRepair 'network_repair_infrastructure_invalid'}
    $context.originalTaskXml=[Text.Encoding]::UTF8.GetString((Read-RcRepairPrivate ($transaction+'\backup-task.xml')));$originalTask=ConvertTo-RcRepairTaskDocument $context.originalTaskXml
    $context.taskValidation=@{original=(Get-RcRepairOriginalTaskBinding $context $originalTask)};if(-not$context.taskValidation.original.valid){Stop-RcRepair 'network_repair_task_binding_invalid'}
    $journalState=Read-RcRepairJournalState (Read-RcRepairPrivate $context.journalPath);$context.journalAlreadyClosed=$journalState.alreadyClosed
    Assert-RcRepairServiceAndFirewall $context;Test-RcNetworkStopped $context;$states=Read-RcRepairFileStates $context;$task=Read-RcRepairTaskState $context;$context.plan=Get-RcRecoveryRepairPlan $states $task;if($context.journalAlreadyClosed-and-not$context.plan.alreadyRestored){Stop-RcRepair 'network_repair_closed_state_changed'}
    $p=$context.documents.profile;$c=$context.documents.config;$currentReceipt=$context.documents.receipt;$profileEntry=@($context.entries|Where-Object{$_.key-ceq'profile'})[0]
    if($profileEntry.sha256-cne$r.manifestSha256-or$p.expectedWindowsSid-cne$r.serviceSid-or$p.publicOrigin-cne$r.publicOrigin-or$c.serverManifestSha256-cne$r.manifestSha256-or$c.serverManifestPath-cne($context.runtime+'\server-profile.json')-or$currentReceipt.manifestSha256-cne$r.manifestSha256){Stop-RcRepair 'network_repair_configuration_invalid'}
    $context.preflightComplete=$true;$null=Invoke-RcRecoveryRepairTransaction $context;$result.valid=$true;$result.success=$true;$result.exitCode=0;$result.code=if($context.alreadyRestored){'network_repair_already_restored'}else{'network_repair_verified'};$result.stage='rollback_restored_service_stopped';$result.rollbackStatus='rollback_restored_service_stopped';$result.repairPerformed=[bool]$context.mutationsStarted;$result.aclRepairsPlanned=$context.plan.aclKeys.Count;$result.taskEnableRequired=$context.plan.taskEnableRequired;$exit=0
}catch{$code=$_.Exception.Message;if($code-cin(Get-RcRepairCodes)){$result.code=$code};$result.errorHResult=$_.Exception.HResult;$result.failureLine=$_.InvocationInfo.ScriptLineNumber;if($context){$result.stage=$context.stage;$result.rollbackStatus=$context.rollbackStatus;if($context.ContainsKey('failureStage')){$result.failureStage=$context.failureStage}}}
finally{if($context){$result.mutationsAttempted=[bool]$context.mutationsStarted;Release-RcNetworkLocks $context;foreach($h in $context.codeLocks){$h.Dispose()}};if($maintenance){$maintenance.Dispose()};if($sourceLock){$sourceLock.Dispose()};[Environment]::SetEnvironmentVariable('PSModulePath',$oldModulePath,'Process')}
$result.exitCode=$exit
if($context-and$context.ContainsKey('taskValidation')){$result.taskValidation=$context.taskValidation}
$result|ConvertTo-Json -Depth 6 -Compress
exit $exit
