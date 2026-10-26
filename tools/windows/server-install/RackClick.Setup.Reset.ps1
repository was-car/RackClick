#requires -Version 5.1
# Import is pure. Reset retires attributed installations; it never deletes databases.
function Get-SetupResetPaths([string]$Id) {
    $parsed=[guid]::Empty
    if(-not[guid]::TryParseExact($Id,'D',[ref]$parsed)-or$parsed.ToString('D')-cne$Id){throw 'setup_reset_id_invalid'}
    return [pscustomobject]@{id=$Id;parent=('C:\ProgramData\RackClick\Instances\'+$Id);instance=('C:\ProgramData\RackClick\Instances\'+$Id+'\instance');codeRoot=('C:\Program Files\RackClick\'+$Id)}
}
function Assert-SetupResetPrivilegedFile([string]$Path,[string]$ReadSid='') {
    Assert-SetupNoReparse $Path
    $acl=Get-Acl -LiteralPath $Path -ErrorAction Stop
    if($acl.GetOwner([Security.Principal.SecurityIdentifier]).Value-notin@('S-1-5-18','S-1-5-32-544',[Security.Principal.WindowsIdentity]::GetCurrent().User.Value)){throw 'setup_reset_marker_owner_invalid'}
    foreach($rule in $acl.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier])){
        if($rule.AccessControlType-ne'Allow'){throw 'setup_reset_marker_acl_invalid'}
        if($rule.IdentityReference.Value-notin@('S-1-5-18','S-1-5-32-544',[Security.Principal.WindowsIdentity]::GetCurrent().User.Value)){
            if($rule.IdentityReference.Value-cne$ReadSid-or([int]$rule.FileSystemRights-band0xD0156)-ne0){throw 'setup_reset_marker_acl_invalid'}
        }
    }
}
function Test-SetupResetAccountSnapshot($Account,[string]$Id,[string]$CurrentSid) {
    if($null-eq$Account){return $false}
    return ($Account.Name-cmatch'^RackClickSvc(?:[a-fA-F0-9]{8})?$'-and$Account.Description-ceq('RackClick '+$Id)-and$Account.Sid-cmatch'^S-1-5-21-(\d+-){3}\d+$'-and$Account.Sid-cne$CurrentSid-and$Account.Sid-cnotmatch'-(500|501)$')
}
function Test-SetupResetServiceSnapshot($Service,$Paths,[string]$Sid) {
    $expected='"'+$Paths.instance+'\content\dependencies\dotnet\dotnet.exe" "'+$Paths.codeRoot+'\service\RackClick.WindowsService.dll" --config "'+$Paths.instance+'\service-config.json"'
    return ($Service.Name-cmatch'^RackClick(?:-Recovery-[a-f0-9]{8,32})?$'-and$Service.DisplayName-ceq('RackClick '+$Paths.id)-and$Service.PathName-ceq$expected-and$Service.Sid-ceq$Sid)
}
function Test-SetupResetServiceCandidateReference($Service,[string]$Id,[string]$ServiceName,[string]$Sid,$Paths,$VerifiedAssignments) {
    $binaryPath=[string]$Service.PathName
    $direct=(($Sid-and$Service.Sid-ceq$Sid)-or$binaryPath.IndexOf($Paths.parent,[StringComparison]::OrdinalIgnoreCase)-ge0-or$binaryPath.IndexOf($Paths.codeRoot,[StringComparison]::OrdinalIgnoreCase)-ge0)
    if($direct){return $true}
    if($Service.Name-cne$ServiceName){return $false}
    # A fixed default service name is shared by several historical attempts.
    # Ignore it only after all identity/path/display/binary checks bound it to
    # another attributed plan. Unknown same-name services remain blockers.
    return (-not$VerifiedAssignments.ContainsKey($Service.Name)-or$VerifiedAssignments[$Service.Name]-ceq$Id)
}
function Wait-SetupResetServiceAbsent([string]$Name,[int]$TimeoutSeconds=10) {
    if($Name-cnotmatch'^RackClick(?:-Recovery-[a-f0-9]{8,32})?$'-or$TimeoutSeconds-lt0-or$TimeoutSeconds-gt30){throw 'setup_reset_service_wait_binding_invalid'}
    $watch=[Diagnostics.Stopwatch]::StartNew()
    do {
        if(-not@(Get-CimInstance -ClassName Win32_Service -Filter ("Name='"+$Name+"'") -ErrorAction Stop).Count){return}
        if($watch.Elapsed.TotalSeconds-ge$TimeoutSeconds){throw 'setup_reset_service_removal_pending'}
        Start-Sleep -Milliseconds 200
    }while($true)
}
function Test-SetupResetTaskSnapshot($Task,$Paths,[string]$Sid) {
    $exe=$env:SystemRoot+'\System32\WindowsPowerShell\v1.0\powershell.exe'
    if($Task.TaskPath-cne'\'-or$Task.Execute-cne$exe-or$Task.ActionCount-ne1){return $false}
    if($Task.TaskName-ceq('RackClick-Backup-'+$Paths.id)){
        return ($Task.Sid-ceq$Sid-and$Task.Arguments-cmatch('^-NoProfile -NonInteractive -ExecutionPolicy Bypass -File '+[regex]::Escape('"'+$Paths.codeRoot+'\operators\server-install\Invoke-RackClickScheduledBackup.ps1" -ManifestPath "'+$Paths.instance+'\runtime\server-profile.json" -ExpectedManifestSha256 ')+'[a-f0-9]{64}$'))
    }
    if($Task.TaskName-ceq('RackClick-Verify-'+$Paths.id)){
        return ($Task.Sid-ceq'S-1-5-18'-and$Task.Arguments-ceq('-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "'+$Paths.codeRoot+'\operators\server-install\Test-RackClickServerAfterReboot.ps1" -ManagementPath "'+$Paths.parent+'\management"'))
    }
    return $false
}
function Get-SetupResetDigest($Value) {
    $sha=[Security.Cryptography.SHA256]::Create()
    try{return ([BitConverter]::ToString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes(($Value|ConvertTo-Json -Depth 16 -Compress))))).Replace('-','').ToLowerInvariant()}finally{$sha.Dispose()}
}
function Test-SetupResetCommonAclSnapshot($Snapshot,[string[]]$KnownServiceSids) {
    if($Snapshot.owner-notin@('S-1-5-18','S-1-5-32-544')){return $false}
    foreach($rule in $Snapshot.rules){
        if($rule.type-cne'Allow'){return $false}
        if($rule.sid-in@('S-1-5-18','S-1-5-32-544')){continue}
        if($rule.sid-in$KnownServiceSids){continue}
        if($rule.sid-in@('S-1-5-32-545','S-1-5-11','S-1-1-0')-and([int]$rule.rights-band0xD0156)-eq0){continue}
        return $false
    }
    return $true
}
function Test-SetupResetRetiredAclSnapshot($Snapshot) {
    if($Snapshot.owner-notin@('S-1-5-18','S-1-5-32-544')-or$Snapshot.protected-ne$true){return $false}
    $seen=@{}
    foreach($rule in $Snapshot.rules){
        if($rule.type-cne'Allow'-or$rule.sid-notin@('S-1-5-18','S-1-5-32-544')-or$rule.rights-ne2032127){return $false}
        $seen[$rule.sid]=$true
    }
    return ($seen.ContainsKey('S-1-5-18')-and$seen.ContainsKey('S-1-5-32-544'))
}
function Test-SetupResetCommonChildrenSnapshot([string]$HubKind,$Children,[string[]]$AllowedArchiveTargets) {
    foreach($child in $Children){
        if(-not$child.isDirectory-or$child.reparse){return $false}
        if($HubKind-ceq'DataRoot'){
            if($child.name-ceq'Instances'){continue}
            if($child.name-ceq'Retired'-and(Test-SetupResetRetiredAclSnapshot $child.acl)){continue}
            return $false
        }
        if($HubKind-cnotin@('Instances','CodeRoot')-or$child.path-cnotin$AllowedArchiveTargets){return $false}
    }
    return ($HubKind-cin@('DataRoot','Instances','CodeRoot'))
}
function Get-SetupResetCommonPaths([string[]]$KnownServiceSids,[string[]]$AllowedArchiveTargets) {
    foreach($path in @('C:\ProgramData\RackClick','C:\ProgramData\RackClick\Instances','C:\Program Files\RackClick')){
        if(-not[IO.Directory]::Exists($path)){continue}
        Assert-SetupNoReparse $path;$acl=Get-Acl -LiteralPath $path -ErrorAction Stop
        $snapshot=[pscustomobject]@{owner=$acl.GetOwner([Security.Principal.SecurityIdentifier]).Value;rules=@($acl.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier])|ForEach-Object{[pscustomobject]@{sid=$_.IdentityReference.Value;type=[string]$_.AccessControlType;rights=[int]$_.FileSystemRights}})}
        if(-not(Test-SetupResetCommonAclSnapshot $snapshot $KnownServiceSids)){throw 'setup_reset_common_acl_unattributed'}
        $hub=if($path-ceq'C:\ProgramData\RackClick'){'DataRoot'}elseif($path-ceq'C:\ProgramData\RackClick\Instances'){'Instances'}else{'CodeRoot'}
        $children=@(Get-ChildItem -LiteralPath $path -Force -ErrorAction Stop|Sort-Object Name|ForEach-Object{
            $childAcl=$null
            if($hub-ceq'DataRoot'-and$_.Name-ceq'Retired'-and$_.PSIsContainer-and($_.Attributes-band[IO.FileAttributes]::ReparsePoint)-eq0){
                $a=Get-Acl -LiteralPath $_.FullName -ErrorAction Stop
                $childAcl=[pscustomobject]@{owner=$a.GetOwner([Security.Principal.SecurityIdentifier]).Value;protected=$a.AreAccessRulesProtected;sddl=$a.Sddl;rules=@($a.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier])|ForEach-Object{[pscustomobject]@{sid=$_.IdentityReference.Value;type=[string]$_.AccessControlType;rights=[int]$_.FileSystemRights}})}
            }
            [pscustomobject]@{name=$_.Name;path=$_.FullName;isDirectory=[bool]$_.PSIsContainer;reparse=(($_.Attributes-band[IO.FileAttributes]::ReparsePoint)-ne0);acl=$childAcl}
        })
        # SetSecurityInfo with OI/CI can propagate to unprotected children.
        # Every child must therefore either leave before the ACL repair, be the
        # known Instances hub, or be an already protected private Retired vault.
        if(-not(Test-SetupResetCommonChildrenSnapshot $hub $children $AllowedArchiveTargets)){throw 'setup_reset_common_children_unattributed_preserved'}
        [pscustomobject]@{path=$path;sddl=$acl.Sddl;children=$children}
    }
}
function Get-SetupResetPlan {
    [CmdletBinding()]param()
    $items=New-Object Collections.Generic.List[object];$preserved=New-Object Collections.Generic.List[object];$blockers=New-Object Collections.Generic.List[string]
    $sources=@{};$setupRoot=Join-Path $env:LOCALAPPDATA 'RackClick\Setup'
    if(Test-Path -LiteralPath $setupRoot){
        Assert-SetupNoReparse $setupRoot
        foreach($dir in @(Get-ChildItem -LiteralPath $setupRoot -Directory -Force|Sort-Object Name)){
            try{$paths=Get-SetupResetPaths $dir.Name;$file=Join-Path $dir.FullName 'plan.json';Assert-SetupResetPrivilegedFile $file;$plan=Read-SetupPlan $file;if($plan.id-cne$dir.Name){throw 'setup_reset_plan_binding_invalid'};$sources[$plan.id]=[pscustomobject]@{marker=$file;markerSha256=(Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant();serviceName=$plan.serviceName}}catch{$preserved.Add([pscustomobject]@{path=$dir.FullName;reason='unattributed_setup_report'})}
        }
    }
    $codeBase='C:\Program Files\RackClick'
    if(Test-Path -LiteralPath $codeBase){
        Assert-SetupNoReparse $codeBase
        foreach($dir in @(Get-ChildItem -LiteralPath $codeBase -Directory -Force|Sort-Object Name)){
            if($sources.ContainsKey($dir.Name)){continue}
            try{$paths=Get-SetupResetPaths $dir.Name;$file=Join-Path $dir.FullName 'preparation-plan.json';Assert-SetupNoReparse $file;$prep=[IO.File]::ReadAllText($file)|ConvertFrom-Json -ErrorAction Stop;Assert-SetupResetPrivilegedFile $file $prep.serviceSid;if($prep.schemaVersion-ne1-or$prep.id-cne$paths.id-or$prep.instancePath-cne$paths.instance-or$prep.codeRoot-cne$paths.codeRoot-or$prep.serviceSid-cnotmatch'^S-1-5-21-(\d+-){3}\d+$'-or$prep.serviceName-cnotmatch'^RackClick(?:-Recovery-[a-f0-9]{8,32})?$'){throw 'setup_reset_preparation_binding_invalid'};$sources[$prep.id]=[pscustomobject]@{marker=$file;markerSha256=(Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant();serviceName=$prep.serviceName}}catch{$preserved.Add([pscustomobject]@{path=$dir.FullName;reason='unattributed_code_root'})}
        }
    }
    $users=@(Get-LocalUser -ErrorAction Stop);$services=@(Get-CimInstance Win32_Service -ErrorAction Stop);$tasks=@(Get-ScheduledTask -ErrorAction Stop);$processes=@(Get-CimInstance Win32_Process -ErrorAction Stop);$firewalls=@(Get-NetFirewallRule -PolicyStore PersistentStore -ErrorAction Stop|Where-Object{$_.Name-clike'RackClick-*'})
    $serviceAssignments=@{}
    foreach($service in $services){
        $serviceSid='';try{$serviceSid=Resolve-SetupAccountSid $service.StartName}catch{}
        $snapshot=[pscustomobject]@{Name=$service.Name;DisplayName=$service.DisplayName;PathName=$service.PathName;Sid=$serviceSid}
        foreach($otherId in @($sources.Keys)){
            $otherPaths=Get-SetupResetPaths $otherId
            $otherAccounts=@($users|Where-Object{Test-SetupResetAccountSnapshot ([pscustomobject]@{Name=$_.Name;Description=$_.Description;Sid=$_.SID.Value}) $otherId ([Security.Principal.WindowsIdentity]::GetCurrent().User.Value)})
            if($otherAccounts.Count-ne1-or-not(Test-SetupResetServiceSnapshot $snapshot $otherPaths $otherAccounts[0].SID.Value)){continue}
            try{$dll=Join-Path $otherPaths.codeRoot 'service\RackClick.WindowsService.dll';Assert-SetupNoReparse $dll;if((Get-FileHash -LiteralPath $dll -Algorithm SHA256).Hash.ToLowerInvariant()-ceq'130e9cc3959d414a0e00759a2e3323a0fc004d76113df56c250f319d38065c61'){$serviceAssignments[$service.Name]=$otherId}}catch{}
        }
    }
    foreach($id in @($sources.Keys|Sort-Object)){
        $paths=Get-SetupResetPaths $id;$reasons=New-Object Collections.Generic.List[string]
        $accounts=@($users|Where-Object{Test-SetupResetAccountSnapshot ([pscustomobject]@{Name=$_.Name;Description=$_.Description;Sid=$_.SID.Value}) $id ([Security.Principal.WindowsIdentity]::GetCurrent().User.Value)})
        $account=$null;$sid='';if($accounts.Count-eq1){$account=$accounts[0];$sid=$account.SID.Value}elseif($accounts.Count-gt1){$reasons.Add('multiple_accounts_for_id')}
        if($sid-and@(Get-LocalGroupMember -SID 'S-1-5-32-544' -ErrorAction Stop|Where-Object{$_.SID.Value-ceq$sid}).Count){$reasons.Add('account_is_administrator')}
        foreach($path in @($paths.parent,$paths.codeRoot)){try{Assert-SetupNoReparse $path}catch{$reasons.Add('reparse_root')}}
        $ownedServices=New-Object Collections.Generic.List[object]
        foreach($service in $services){
            $serviceSid='';try{$serviceSid=Resolve-SetupAccountSid $service.StartName}catch{}
            $snapshot=[pscustomobject]@{Name=$service.Name;DisplayName=$service.DisplayName;PathName=$service.PathName;Sid=$serviceSid}
            if(Test-SetupResetServiceCandidateReference $snapshot $id $sources[$id].serviceName $sid $paths $serviceAssignments){
                if($sid-and(Test-SetupResetServiceSnapshot $snapshot $paths $sid)){$dll=Join-Path $paths.codeRoot 'service\RackClick.WindowsService.dll';try{Assert-SetupNoReparse $dll;if((Get-FileHash -LiteralPath $dll -Algorithm SHA256).Hash.ToLowerInvariant()-cne'130e9cc3959d414a0e00759a2e3323a0fc004d76113df56c250f319d38065c61'){throw 'hash'}}catch{$reasons.Add('service_binary_not_pinned')};$ownedServices.Add($snapshot)}else{$reasons.Add('foreign_service_reference')}
            }
        }
        $ownedTasks=New-Object Collections.Generic.List[object]
        foreach($task in $tasks){$taskSid='';try{$taskSid=Resolve-SetupAccountSid $task.Principal.UserId}catch{};$actions=@($task.Actions);$arguments=($actions|ForEach-Object{$_.Arguments})-join' '
            if(($sid-and$taskSid-ceq$sid)-or$task.TaskName-in@(('RackClick-Backup-'+$id),('RackClick-Verify-'+$id))-or$arguments.IndexOf($paths.codeRoot,[StringComparison]::OrdinalIgnoreCase)-ge0-or$arguments.IndexOf($paths.parent,[StringComparison]::OrdinalIgnoreCase)-ge0){
                $snapshot=[pscustomobject]@{TaskName=$task.TaskName;TaskPath=$task.TaskPath;Execute=if($actions.Count){$actions[0].Execute}else{''};Arguments=$arguments;ActionCount=$actions.Count;Sid=$taskSid}
                if($sid-and(Test-SetupResetTaskSnapshot $snapshot $paths $sid)){$ownedTasks.Add($snapshot);if([string]$task.State-cin@('Running','Queued')){$reasons.Add('running_task_preserved')}}else{$reasons.Add('foreign_task_reference')}
            }
        }
        # A running account or executable blocks archival; no guessed PID termination.
        foreach($process in $processes){$related=($process.ExecutablePath-and($process.ExecutablePath.StartsWith($paths.parent+'\',[StringComparison]::OrdinalIgnoreCase)-or$process.ExecutablePath.StartsWith($paths.codeRoot+'\',[StringComparison]::OrdinalIgnoreCase)))
            if($sid){try{$owner=Invoke-CimMethod -InputObject $process -MethodName GetOwnerSid -ErrorAction Stop;if($owner.ReturnValue-eq0-and$owner.Sid-ceq$sid){$related=$true}}catch{if(-not$process.ExecutablePath){$reasons.Add('process_owner_unavailable')}}}
            if($related){$reasons.Add('running_process_preserved')}
        }
        $accountName=if($account){$account.Name}else{''};$retiredName=if($account){'RC-Old-'+$id.Replace('-','').Substring(0,8)}else{''}
        if($account-and@($users|Where-Object{$_.Name-ieq$retiredName}).Count){$reasons.Add('retired_account_name_exists')}
        $ownedFirewall=@();foreach($fw in @($firewalls|Where-Object{$_.Name-ceq('RackClick-'+$id)})){$apps=@($fw|Get-NetFirewallApplicationFilter -ErrorAction Stop);if($apps.Count-ne1-or$apps[0].Program-cne($paths.instance+'\content\dependencies\dotnet\dotnet.exe')-or$fw.DisplayName-cne$fw.Name){$reasons.Add('foreign_firewall_reference')}else{$ownedFirewall+=@{name=$fw.Name;program=$apps[0].Program}}}
        $targets=@(@($paths.parent,$paths.codeRoot)|Where-Object{[IO.Directory]::Exists($_)})
        if($targets.Count-or$account-or$ownedServices.Count-or$ownedTasks.Count){$items.Add([pscustomobject]@{id=$id;marker=$sources[$id].marker;markerSha256=$sources[$id].markerSha256;paths=$paths;targets=$targets;accountName=$accountName;serviceSid=$sid;retiredAccountName=$retiredName;services=@($ownedServices.ToArray());tasks=@($ownedTasks.ToArray());firewall=$ownedFirewall;blocked=@($reasons.ToArray()|Sort-Object -Unique)})}
    }
    foreach($root in @('C:\RackClick-Servidor-01','C:\RackClick-Instancia-01','C:\RackClick-Instancia-02','C:\Users\RackClickOperador\Documents\RackClick-Instancia-01')){
        if(-not[IO.Directory]::Exists($root)){continue}
        try{Assert-SetupNoReparse $root;$attributed=$false;$marker='';$bundle=Join-Path $root 'bundle.json'
            if([IO.File]::Exists($bundle)-and(Get-FileHash -LiteralPath $bundle -Algorithm SHA256).Hash.ToLowerInvariant()-ceq'03e1b4a268250f4a98cec28a402d449cd1bfbcd589aa9f6eeb6c90bc123ca7cd'){$attributed=$true;$marker=$bundle}
            $receipt=Join-Path $root 'installation.json';if(-not$attributed-and[IO.File]::Exists($receipt)){$m=[IO.File]::ReadAllText($receipt)|ConvertFrom-Json -ErrorAction Stop;$gid=[guid]::Empty;if($m.schemaVersion-eq1-and$m.kind-ceq'RackClickPrivateInstallation'-and$m.rootPath-ceq$root-and[guid]::TryParseExact([string]$m.id,'D',[ref]$gid)){$attributed=$true;$marker=$receipt}}
            # A failed state has no root binding, so a state file alone is insufficient.
            if(-not$attributed){throw 'setup_reset_legacy_marker_unbound'}
            $active=@($processes|Where-Object{$_.ExecutablePath-and$_.ExecutablePath.StartsWith($root+'\',[StringComparison]::OrdinalIgnoreCase)})
            $refs=@($services|Where-Object{$_.PathName.IndexOf($root,[StringComparison]::OrdinalIgnoreCase)-ge0})
            $taskRefs=@($tasks|Where-Object{(@($_.Actions|ForEach-Object{$_.Arguments})-join' ').IndexOf($root,[StringComparison]::OrdinalIgnoreCase)-ge0})
            if($active.Count-or$refs.Count-or$taskRefs.Count){throw 'setup_reset_legacy_in_use'}
            $items.Add([pscustomobject]@{id=('legacy-'+[IO.Path]::GetFileName($root)+'-'+(Get-SetupResetDigest $root).Substring(0,8));marker=$marker;markerSha256=(Get-FileHash -LiteralPath $marker -Algorithm SHA256).Hash.ToLowerInvariant();paths=$null;targets=@($root);accountName='';serviceSid='';retiredAccountName='';services=@();tasks=@();firewall=@();blocked=@()})
        }catch{$preserved.Add([pscustomobject]@{path=$root;reason='legacy_not_safely_attributed_or_in_use'})}
    }
    $instancesRoot='C:\ProgramData\RackClick\Instances';if([IO.Directory]::Exists($instancesRoot)){Assert-SetupNoReparse $instancesRoot;foreach($dir in @(Get-ChildItem -LiteralPath $instancesRoot -Directory -Force)){if(-not$sources.ContainsKey($dir.Name)){$preserved.Add([pscustomobject]@{path=$dir.FullName;reason='unattributed_instance_root'})}}}
    foreach($user in @($users|Where-Object{$_.Name-cmatch'^RackClickSvc'})){if(-not@($items|Where-Object{$_.serviceSid-ceq$user.SID.Value}).Count){$preserved.Add([pscustomobject]@{path=('account:'+ $user.Name);reason='account_without_valid_installation_marker'})}}
    foreach($item in $items){foreach($reason in $item.blocked){$blockers.Add($item.id+':'+$reason)}}
    $common=@();try{$common=@(Get-SetupResetCommonPaths @($items|Where-Object{$_.serviceSid}|ForEach-Object{$_.serviceSid}) @($items|ForEach-Object{$_.targets}))}catch{if($_.Exception.Message-cmatch'^setup_reset_common_[a-z_]+$'){$blockers.Add($_.Exception.Message)}else{$blockers.Add('setup_reset_common_acl_unattributed')}}
    $body=[ordered]@{instances=@($items.ToArray());preserved=@($preserved.ToArray());blockers=@($blockers.ToArray());commonPaths=$common}
    return [pscustomobject]@{schemaVersion=1;id=[guid]::NewGuid().ToString('D');createdUtc=[DateTime]::UtcNow.ToString('o');fingerprint=(Get-SetupResetDigest $body);instances=$body.instances;preserved=$body.preserved;blockers=$body.blockers;commonPaths=$common}
}
function Move-SetupResetDirectory([string]$Source,[string]$Destination,[string]$AllowedSource,[string]$AllowedDestinationParent) {
    # Exact normalized arguments and direct-child destination, never recursive delete.
    foreach($p in @($Source,$Destination,$AllowedSource,$AllowedDestinationParent)){Assert-SetupNoReparse $p;if([IO.Path]::GetFullPath($p)-cne$p){throw 'setup_reset_path_not_canonical'}}
    if($Source-cne$AllowedSource-or[IO.Path]::GetDirectoryName($Destination)-cne$AllowedDestinationParent-or[IO.Path]::GetPathRoot($Source)-cne[IO.Path]::GetPathRoot($Destination)-or-not[IO.Directory]::Exists($Source)-or-not[IO.Directory]::Exists($AllowedDestinationParent)-or(Test-Path -LiteralPath $Destination)){throw 'setup_reset_move_binding_invalid'}
    [IO.Directory]::Move($Source,$Destination)
}
function Invoke-SetupResetPlan {
    [CmdletBinding(SupportsShouldProcess=$true,ConfirmImpact='High')]
    param([Parameter(Mandatory=$true)]$Plan,[Parameter(Mandatory=$true)][string]$JournalDirectory)
    Assert-SetupAdministrator
    $fresh=Get-SetupResetPlan
    $resetId=[guid]::Empty
    if($Plan.schemaVersion-ne1-or-not[guid]::TryParseExact([string]$Plan.id,'D',[ref]$resetId)-or$Plan.id-cne$resetId.ToString('D')-or$Plan.fingerprint-cne$fresh.fingerprint-or(Get-SetupResetDigest ([ordered]@{instances=$Plan.instances;preserved=$Plan.preserved;blockers=$Plan.blockers;commonPaths=$Plan.commonPaths}))-cne$fresh.fingerprint){throw 'setup_reset_plan_changed'}
    if(@($fresh.blockers).Count){throw 'setup_reset_blocked_preserved'}
    Assert-SetupNoReparse $JournalDirectory;Assert-SetupResetPrivilegedFile $JournalDirectory
    $retiredBase='C:\ProgramData\RackClick\Retired';$retired=Join-Path $retiredBase $Plan.id
    Assert-SetupNoReparse $retired
    if([IO.Directory]::Exists($retiredBase)){Assert-SetupResetPrivilegedFile $retiredBase}
    if(Test-Path -LiteralPath $retired){throw 'setup_reset_destination_exists'}
    $journal=[ordered]@{schemaVersion=1;resetId=$Plan.id;valid=$false;cleanupComplete=$false;exitCode=1;complete=$false;code='reset_not_applied';quarantinePath=$retired;actions=@();archivedInstances=@();retiredAccounts=@();preserved=$fresh.preserved;remainingBlockers=$fresh.blockers}
    if(-not$PSCmdlet.ShouldProcess('Instalaciones RackClick atribuidas','Retirar reversiblemente cuentas, tareas, servicios y carpetas')){return [pscustomobject]$journal}
    $journalPath=Join-Path $JournalDirectory 'reset-result.json';if(Test-Path -LiteralPath $journalPath){throw 'setup_reset_journal_already_used'};Write-SetupJson $journalPath $journal
    try{
        foreach($path in @($retiredBase,$retired)){
            if(-not[IO.Directory]::Exists($path)){$acl=New-Object Security.AccessControl.DirectorySecurity;$acl.SetOwner((New-Object Security.Principal.SecurityIdentifier('S-1-5-32-544')));$acl.SetAccessRuleProtection($true,$false);foreach($sid in @('S-1-5-18','S-1-5-32-544')){$acl.AddAccessRule((New-Object Security.AccessControl.FileSystemAccessRule((New-Object Security.Principal.SecurityIdentifier($sid)),'FullControl','ContainerInherit,ObjectInherit','None','Allow')))};[IO.Directory]::CreateDirectory($path,$acl)|Out-Null}
            Assert-SetupResetPrivilegedFile $path
        }
        foreach($item in $fresh.instances){
            foreach($task in $item.tasks){Disable-ScheduledTask -TaskName $task.TaskName -TaskPath $task.TaskPath -ErrorAction Stop|Out-Null;Unregister-ScheduledTask -TaskName $task.TaskName -TaskPath $task.TaskPath -Confirm:$false -ErrorAction Stop;$journal.actions+=@{action='task_removed';name=$task.TaskName};Write-SetupJson $journalPath $journal}
            foreach($service in $item.services){
                $svc=Get-Service -Name $service.Name -ErrorAction Stop
                try{if($svc.Status-ne'Stopped'){Stop-Service -Name $service.Name -ErrorAction Stop;$svc.WaitForStatus('Stopped',[TimeSpan]::FromSeconds(60))}}finally{$svc.Dispose()}
                & "$env:SystemRoot\System32\sc.exe" delete $service.Name|Out-Null
                if($LASTEXITCODE-ne0){throw 'setup_reset_service_remove_failed'}
                $journal.actions+=@{action='service_delete_requested';name=$service.Name};Write-SetupJson $journalPath $journal
                Wait-SetupResetServiceAbsent $service.Name
                $journal.actions+=@{action='service_removed';name=$service.Name};Write-SetupJson $journalPath $journal
            }
            foreach($fw in $item.firewall){Remove-NetFirewallRule -PolicyStore PersistentStore -Name $fw.name -ErrorAction Stop;$journal.actions+=@{action='firewall_removed';name=$fw.name};Write-SetupJson $journalPath $journal}
            # A task could have started between preview and disable. Check again
            # after stopping producers, before touching names or live data.
            foreach($process in @(Get-CimInstance Win32_Process -ErrorAction Stop)){
                if($process.ExecutablePath-and@($item.targets|Where-Object{$process.ExecutablePath.StartsWith($_+'\',[StringComparison]::OrdinalIgnoreCase)}).Count){throw 'setup_reset_process_started_during_apply'}
                if($item.serviceSid){$owner=Invoke-CimMethod -InputObject $process -MethodName GetOwnerSid -ErrorAction Stop;if($owner.ReturnValue-eq0-and$owner.Sid-ceq$item.serviceSid){throw 'setup_reset_process_started_during_apply'}}
            }
            if($item.accountName){$u=Get-LocalUser -SID (New-Object Security.Principal.SecurityIdentifier($item.serviceSid)) -ErrorAction Stop;if($u.Name-cne$item.accountName-or$u.Description-cne('RackClick '+$item.id)){throw 'setup_reset_account_changed'};Rename-LocalUser -SID $u.SID -NewName $item.retiredAccountName -ErrorAction Stop;Disable-LocalUser -SID $u.SID -ErrorAction Stop;$journal.actions+=@{action='account_renamed_disabled';oldName=$item.accountName;newName=$item.retiredAccountName;sid=$item.serviceSid};Write-SetupJson $journalPath $journal}
            if($item.accountName){$journal.retiredAccounts+=@{sid=$item.serviceSid;oldName=$item.accountName;newName=$item.retiredAccountName}}
            $index=0;foreach($source in $item.targets){$index++;$destination=Join-Path $retired ($item.id+'-'+$index);Move-SetupResetDirectory $source $destination $source $retired;$journal.actions+=@{action='directory_archived';source=$source;destination=$destination};Write-SetupJson $journalPath $journal};$journal.archivedInstances+=@($item.id)
        }
        # Recheck after archival. No unprotected preserved child may remain
        # below a hub whose inheritable administrative ACEs are being repaired.
        $safeHubs=@(Get-SetupResetCommonPaths @($fresh.instances|Where-Object{$_.serviceSid}|ForEach-Object{$_.serviceSid}) @())
        Initialize-SetupSecurityNative
        foreach($common in $safeHubs){Assert-SetupNoReparse $common.path;[RackClickSetupSecurityNative]::SetAcl($common.path,'O:BAG:SYD:P(A;OICI;FA;;;BA)(A;OICI;FA;;;SY)(A;;FRFX;;;BU)');$journal.actions+=@{action='common_directory_access_restored';path=$common.path};Write-SetupJson $journalPath $journal}
        $journal.complete=$true;$journal.valid=$true;$journal.cleanupComplete=$true;$journal.exitCode=0;$journal.code='setup_reset_completed_preserved';$journal.success=$true
    }catch{$journal.complete=$false;$journal.code='setup_reset_partial_preserved';$journal.success=$false;$journal.errorType=$_.Exception.GetType().FullName;Write-SetupJson $journalPath $journal;throw}
    Write-SetupJson $journalPath $journal
    return [pscustomobject]$journal
}
