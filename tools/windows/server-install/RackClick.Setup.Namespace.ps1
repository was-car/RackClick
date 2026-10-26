#requires -Version 5.1
# Isolate the two explicitly named RackClick hubs without inspecting descendants
# or changing any old ACL/account. Import never changes the host.
. (Join-Path $PSScriptRoot 'RackClick.Setup.Host.ps1')
function Test-SetupNamespaceReference([string]$Text,[string]$Root) {
    if(-not$Text){return $false}
    $expanded=[Environment]::ExpandEnvironmentVariables($Text).Replace('/','\')
    $pattern=[regex]::Escape($Root)+'(?=\\|[\s"'']|$)'
    if([regex]::IsMatch($expanded,$pattern,[Text.RegularExpressions.RegexOptions]::IgnoreCase)){return $true}
    # Normalize absolute local path candidates without executing command text.
    # An existing ancestor also resolves NTFS short names (PROGRA~1) even when
    # the referenced descendant has already been deleted.
    $starts=[regex]::Matches($expanded,'(?i)[a-z]:\\')
    for($i=0;$i-lt[Math]::Min(16,$starts.Count);$i++){
        $end=if($i+1-lt$starts.Count){$starts[$i+1].Index}else{$expanded.Length}
        $candidate=$expanded.Substring($starts[$i].Index,$end-$starts[$i].Index).Split('"')[0].Trim()
        if(-not$candidate.StartsWith([IO.Path]::GetPathRoot($Root),[StringComparison]::OrdinalIgnoreCase)){continue}
        try{$full=[IO.Path]::GetFullPath($candidate)}catch{continue}
        if([regex]::IsMatch($full,$pattern,[Text.RegularExpressions.RegexOptions]::IgnoreCase)){return $true}
        $cursor=$full;$item=$null
        while($cursor){
            try{$item=Get-Item -LiteralPath $cursor -Force -ErrorAction Stop;break}catch{$cursor=[IO.Path]::GetDirectoryName($cursor)}
        }
        if($cursor-and$null-ne$item){$resolved=$item.FullName.TrimEnd('\')+$full.Substring($cursor.Length);if([regex]::IsMatch($resolved,$pattern,[Text.RegularExpressions.RegexOptions]::IgnoreCase)){return $true}}
    }
    return $false
}
function Get-SetupNamespaceItem([string]$Path) {
    try {return Get-Item -LiteralPath $Path -Force -ErrorAction Stop}
    catch [Management.Automation.ItemNotFoundException] {return $null}
    # Access denied and all other IO errors remain errors, never "absent".
}
function Get-SetupNamespacePlan {
    [CmdletBinding()]param([string]$Id='')
    $null=Assert-SetupSupportedHost
    if(-not$Id){$Id=[guid]::NewGuid().ToString('D')}
    $parsed=[guid]::Empty
    if(-not[guid]::TryParseExact($Id,'D',[ref]$parsed)-or$parsed.ToString('D')-cne$Id){throw 'namespace_id_invalid'}
    $roots=@('C:\ProgramData\RackClick','C:\Program Files\RackClick')
    $hubs=@();$blockers=New-Object Collections.Generic.List[string]
    foreach($root in $roots){
        Assert-SetupNoReparse $root
        $item=Get-SetupNamespaceItem $root
        $target=$root+'-Previous-'+$Id
        Assert-SetupNoReparse $target
        if($null-ne(Get-SetupNamespaceItem $target)){$blockers.Add('namespace_archive_destination_exists')}
        if($null-ne$item-and-not$item.PSIsContainer){$blockers.Add('namespace_root_is_not_directory')}
        $sddl='';if($null-ne$item){$sddl=(Get-Acl -LiteralPath $root -ErrorAction Stop).Sddl}
        $hubs+=@([pscustomobject]@{source=$root;destination=$target;exists=($null-ne$item);sddl=$sddl})
    }
    $accounts=@(Get-LocalUser -ErrorAction Stop|Where-Object{$_.Name-cmatch'^RackClickSvc(?:[a-zA-Z0-9]{1,8})?$'-or$_.Name-ceq'RackClickOperador'}|Sort-Object Name|ForEach-Object{[pscustomobject]@{name=$_.Name;sid=$_.SID.Value}})
    $serviceSids=@($accounts|Where-Object{$_.name-cne'RackClickOperador'}|ForEach-Object{$_.sid})
    $references=New-Object Collections.Generic.List[object]
    foreach($service in @(Get-CimInstance Win32_Service -ErrorAction Stop)){
        $sid='';try{$sid=Resolve-SetupAccountSid $service.StartName}catch{}
        $related=($sid-and$sid-in$serviceSids)
        foreach($root in $roots){if(Test-SetupNamespaceReference ([string]$service.PathName) $root){$related=$true}}
        if($related){$references.Add([pscustomobject]@{kind='service';name=[string]$service.Name});$blockers.Add('namespace_registered_service_preserved')}
        elseif($service.Name-ceq'RackClick'){$references.Add([pscustomobject]@{kind='service';name=[string]$service.Name});$blockers.Add('namespace_default_service_name_occupied')}
    }
    foreach($task in @(Get-ScheduledTask -ErrorAction Stop)){
        $sid='';try{$sid=Resolve-SetupAccountSid $task.Principal.UserId}catch{}
        $related=($sid-and$sid-in$serviceSids)
        foreach($action in @($task.Actions)){foreach($text in @($action.Execute,$action.Arguments,$action.WorkingDirectory)){foreach($root in $roots){if(Test-SetupNamespaceReference ([string]$text) $root){$related=$true}}}}
        if($related){$references.Add([pscustomobject]@{kind='task';name=([string]$task.TaskPath+[string]$task.TaskName)});$blockers.Add('namespace_registered_task_preserved')}
    }
    foreach($process in @(Get-CimInstance Win32_Process -ErrorAction Stop)){
        $related=$false
        foreach($text in @($process.ExecutablePath,$process.CommandLine)){foreach($root in $roots){if(Test-SetupNamespaceReference ([string]$text) $root){$related=$true}}}
        if($serviceSids.Count){try{$owner=Invoke-CimMethod -InputObject $process -MethodName GetOwnerSid -ErrorAction Stop;if($owner.ReturnValue-eq0-and$owner.Sid-in$serviceSids){$related=$true}}catch{if($related){$blockers.Add('namespace_candidate_process_owner_unavailable')}}}
        if($related){$references.Add([pscustomobject]@{kind='process';name=[string]$process.ProcessId});$blockers.Add('namespace_running_process_preserved')}
    }
    $listeners=@(Get-NetTCPConnection -State Listen -ErrorAction Stop)
    foreach($port in @(5443,55441)){if(@($listeners|Where-Object{$_.LocalPort-eq$port}).Count){$blockers.Add('namespace_install_port_in_use_'+$port)}}
    $body=[ordered]@{hubs=$hubs;preservedAccounts=$accounts;references=@($references.ToArray()|Sort-Object kind,name);blockers=@($blockers.ToArray()|Sort-Object -Unique)}
    return [pscustomobject]@{schemaVersion=1;kind='RackClickNamespaceIsolation';id=$Id;fingerprint=(Get-SetupResetDigest $body);hubs=$hubs;preservedAccounts=$accounts;references=$body.references;blockers=$body.blockers}
}
function Move-SetupNamespaceDirectory([string]$Source,[string]$Destination,[string]$AllowedSource,[string]$Id) {
    $parsed=[guid]::Empty
    if(-not[guid]::TryParseExact($Id,'D',[ref]$parsed)-or$parsed.ToString('D')-cne$Id-or$Source-cne$AllowedSource-or$Destination-cne($Source+'-Previous-'+$Id)-or[IO.Path]::GetDirectoryName($Destination)-cne[IO.Path]::GetDirectoryName($Source)){throw 'namespace_move_binding_invalid'}
    foreach($path in @($Source,$Destination)){if([IO.Path]::GetFullPath($path)-cne$path){throw 'namespace_move_binding_invalid'};Assert-SetupNoReparse $path}
    if($null-eq(Get-SetupNamespaceItem $Source)-or$null-ne(Get-SetupNamespaceItem $Destination)){throw 'namespace_move_state_changed'}
    [IO.Directory]::Move($Source,$Destination)
}
function Move-SetupNamespaceHub([string]$Source,[string]$Destination,[string]$Id) {
    $parsed=[guid]::Empty
    if(-not[guid]::TryParseExact($Id,'D',[ref]$parsed)-or$parsed.ToString('D')-cne$Id-or$Source-cnotin@('C:\ProgramData\RackClick','C:\Program Files\RackClick')-or$Destination-cne($Source+'-Previous-'+$Id)){throw 'namespace_move_binding_invalid'}
    # Same parent and same volume; no recursion or ACL write.
    Move-SetupNamespaceDirectory $Source $Destination $Source $Id
}
function Invoke-SetupNamespacePlan {
    [CmdletBinding(SupportsShouldProcess=$true,ConfirmImpact='High')]
    param([Parameter(Mandatory=$true)]$Plan,[Parameter(Mandatory=$true)][string]$JournalDirectory)
    Assert-SetupAdministrator
    $null=Assert-SetupSupportedHost
    if([IO.Path]::GetFullPath($JournalDirectory)-cne$JournalDirectory){throw 'namespace_journal_path_invalid'}
    foreach($root in @('C:\ProgramData\RackClick','C:\Program Files\RackClick')){if($JournalDirectory.Equals($root,[StringComparison]::OrdinalIgnoreCase)-or$JournalDirectory.StartsWith($root+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'namespace_journal_inside_archive'}}
    Assert-SetupNoReparse $JournalDirectory;Assert-SetupResetPrivilegedFile $JournalDirectory
    $fresh=Get-SetupNamespacePlan -Id $Plan.id
    $body=[ordered]@{hubs=$Plan.hubs;preservedAccounts=$Plan.preservedAccounts;references=$Plan.references;blockers=$Plan.blockers}
    if($Plan.schemaVersion-ne1-or$Plan.kind-cne'RackClickNamespaceIsolation'-or$Plan.fingerprint-cne$fresh.fingerprint-or(Get-SetupResetDigest $body)-cne$fresh.fingerprint){throw 'namespace_plan_changed'}
    if(@($fresh.blockers).Count){throw 'namespace_references_preserved'}
    $journal=[ordered]@{schemaVersion=1;resetId=$Plan.id;valid=$false;cleanupComplete=$false;exitCode=1;code='namespace_isolation_not_applied';actions=@();archivedInstances=@();retiredAccounts=@();preserved=$fresh.preservedAccounts;remainingBlockers=$fresh.blockers}
    if(-not$PSCmdlet.ShouldProcess('C:\ProgramData\RackClick y C:\Program Files\RackClick','Archivar directorios completos sin cambiar cuentas ni permisos')){return [pscustomobject]$journal}
    $journalPath=Join-Path $JournalDirectory 'reset-result.json'
    if(Test-Path -LiteralPath $journalPath){throw 'namespace_journal_already_used'}
    Write-SetupJson $journalPath $journal
    try{
        foreach($hub in $fresh.hubs){
            if(-not$hub.exists){continue}
            # Requery all references and root identities immediately before each
            # move. Earlier moves are expected; all other changes stop the run.
            $again=Get-SetupNamespacePlan -Id $Plan.id
            if(@($again.references).Count-or@($again.blockers|Where-Object{$_-ne'namespace_archive_destination_exists'}).Count){throw 'namespace_references_changed'}
            foreach($expected in $fresh.hubs){
                $now=@($again.hubs|Where-Object{$_.source-ceq$expected.source})[0]
                $done=@($journal.actions|Where-Object{$_.source-ceq$expected.source-and$_.action-ceq'hub_archived'}).Count-gt0
                if($done){if($now.exists-or(Get-Acl -LiteralPath $expected.destination -ErrorAction Stop).Sddl-cne$expected.sddl){throw 'namespace_root_changed'}}
                elseif($now.exists-ne$expected.exists-or$now.sddl-cne$expected.sddl-or$null-ne(Get-SetupNamespaceItem $expected.destination)){throw 'namespace_root_changed'}
            }
            Move-SetupNamespaceHub $hub.source $hub.destination $Plan.id
            $journal.actions+=@{action='hub_archived';source=$hub.source;destination=$hub.destination};$journal.archivedInstances+=@($hub.source)
            Write-SetupJson $journalPath $journal
            if($null-ne(Get-SetupNamespaceItem $hub.source)-or(Get-Acl -LiteralPath $hub.destination -ErrorAction Stop).Sddl-cne$hub.sddl){throw 'namespace_archive_verification_failed'}
        }
        $last=Get-SetupNamespacePlan -Id $Plan.id
        if(@($last.references).Count-or@($last.blockers|Where-Object{$_-ne'namespace_archive_destination_exists'}).Count-or@($last.hubs|Where-Object{$_.exists}).Count){throw 'namespace_final_state_changed'}
        $journal.valid=$true;$journal.cleanupComplete=$true;$journal.exitCode=0;$journal.code='namespace_isolated_preserved'
    }catch{$journal.code='namespace_partial_preserved';$journal.errorType=$_.Exception.GetType().FullName;Write-SetupJson $journalPath $journal;throw}
    Write-SetupJson $journalPath $journal
    return [pscustomobject]$journal
}
