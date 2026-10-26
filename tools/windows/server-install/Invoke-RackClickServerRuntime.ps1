#requires -Version 5.1
[CmdletBinding()]
param([string]$Operation='',[string]$ManifestPath='',[string]$ExpectedManifestSha256='',[string]$RunId='',[string]$BackupPath='')
$serverOperationInputs=@{operation=$Operation;manifest=$ManifestPath;sha=$ExpectedManifestSha256;runId=$RunId;backup=$BackupPath}
. (Join-Path $PSScriptRoot 'RackClick.ServerRuntime.ps1')
$launcherInputs=@{stopAfter=0;graceful=$true}
$serverOriginalTemp=$env:TEMP;$serverOriginalTmp=$env:TMP
$launcherInheritedConfiguration=@{}
function Write-ServerOperationResult {
    param([string]$Code,[int]$ExitCode=0)
    [ordered]@{schemaVersion=1;valid=($ExitCode -eq 0);exitCode=$ExitCode;code=$Code;operation=$serverOperationInputs.operation;runId=$serverOperationInputs.runId}|ConvertTo-Json -Compress
}
if ($serverOperationInputs.operation -cnotin @('Start','Stop','Verify','Backup') -or
    ($serverOperationInputs.operation -cin @('Start','Stop') -and $serverOperationInputs.runId -cnotmatch '^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$') -or
    ($serverOperationInputs.operation -cne 'Backup' -and $serverOperationInputs.backup -ne '')) {
    Write-ServerOperationResult 'server_operation_input_invalid' 2
    exit 2
}
if ($serverOperationInputs.operation -cne 'Start') {
    $profile=$null;$operationExit=2
    try {
        $profile=Read-ServerProfile $serverOperationInputs.manifest $serverOperationInputs.sha -Maintenance:($serverOperationInputs.operation -ceq 'Stop')
        $instance=$profile.instance
        $env:TEMP=Join-Path $profile.root 'temp';$env:TMP=$env:TEMP
        . (Join-Path $script:ServerOperatorsRoot 'RackClick.LaunchControl.ps1')
        $launcherInheritedConfiguration=Clear-LauncherInheritedConfiguration
        if ($serverOperationInputs.operation -ceq 'Verify') {
            Write-ServerOperationResult 'server_profile_verified';$operationExit=0
        } elseif ($serverOperationInputs.operation -ceq 'Stop') {
            $activePath=Join-Path $instance.logRoot 'active-run.json'
            Assert-BackupPrivateAcl $activePath
            $active=[IO.File]::ReadAllText($activePath)|ConvertFrom-Json
            if ($active.runId -cne $serverOperationInputs.runId -or $active.instanceId -cne $instance.id -or $active.publicOrigin -cne $profile.origin.origin) {Stop-ServerCheck 'server_active_run_changed'}
            $runRoot=Join-Path $instance.logRoot ('launcher-'+$serverOperationInputs.runId);Assert-BackupPrivateAcl $runRoot
            if ($active.status -cnotin @('starting','ready','stopped')) {Stop-ServerCheck 'server_run_not_stoppable'}
            if ($active.status -cne 'stopped') {
                $request=Join-Path $runRoot 'stop-request.json'
                $value=@{schemaVersion=1;runId=$serverOperationInputs.runId;instanceId=$instance.id}|ConvertTo-Json -Compress
                if ([IO.File]::Exists($request)) {
                    Assert-BackupPrivateAcl $request;$previous=[IO.File]::ReadAllText($request)|ConvertFrom-Json
                    if ($previous.runId -cne $serverOperationInputs.runId -or $previous.instanceId -cne $instance.id -or $previous.schemaVersion -ne 1) {Stop-ServerCheck 'server_stop_request_invalid'}
                } else {
                    # Publish only a complete, closed file; never expose the exclusive writer.
                    $temporaryRequest=Join-Path $runRoot ('stop-request-'+[guid]::NewGuid().ToString('N')+'.tmp')
                    try {
                        Write-BackupNewText $temporaryRequest $value
                        Assert-BackupPrivateAcl $temporaryRequest
                        try {[IO.File]::Move($temporaryRequest,$request)}
                        catch [IO.IOException] {
                            if (-not [IO.File]::Exists($request)) {throw}
                            Assert-BackupPrivateAcl $request
                            $previous=[IO.File]::ReadAllText($request)|ConvertFrom-Json
                            if ($previous.runId -cne $serverOperationInputs.runId -or $previous.instanceId -cne $instance.id -or $previous.schemaVersion -ne 1) {Stop-ServerCheck 'server_stop_request_invalid'}
                        }
                    } finally {if ([IO.File]::Exists($temporaryRequest)) {[IO.File]::Delete($temporaryRequest)}}
                }
            }
            $watch=[Diagnostics.Stopwatch]::StartNew();$confirmed=$false
            while ($watch.Elapsed.TotalSeconds -lt 90) {
                Assert-BackupPrivateAcl $activePath
                try {$active=[IO.File]::ReadAllText($activePath)|ConvertFrom-Json} catch {Start-Sleep -Milliseconds 100;continue}
                if ($active.runId -cne $serverOperationInputs.runId -or $active.instanceId -cne $instance.id) {Stop-ServerCheck 'server_active_run_changed'}
                if ($active.status -ceq 'failed') {Stop-ServerCheck 'server_stop_failed'}
                if ($active.status -ceq 'stopped' -and $active.code -ceq 'instance_stopped' -and -not [IO.File]::Exists((Join-Path $instance.pgData 'postmaster.pid'))) {
                    $probe=$null
                    try {$probe=[IO.File]::Open($instance.lockPath,'Open','ReadWrite','None');$confirmed=$true} catch [IO.IOException] {} finally {if ($null -ne $probe) {$probe.Dispose()}}
                    if ($confirmed) {
                        $ports=@([Net.NetworkInformation.IPGlobalProperties]::GetIPGlobalProperties().GetActiveTcpListeners()|ForEach-Object {$_.Port})
                        $confirmed=($instance.pgPort -notin $ports -and $instance.httpPort -notin $ports)
                        if ($confirmed) {break}
                    }
                }
                Start-Sleep -Milliseconds 100
            }
            if (-not $confirmed) {Stop-ServerCheck 'server_stop_timeout' 1}
            Write-ServerOperationResult 'server_stopped';$operationExit=0
        } else {
            $destination=Get-StageLocalPath $serverOperationInputs.backup
            foreach ($other in @($profile.manifest.installationPath,$instance.pgBin,[IO.Path]::GetDirectoryName($instance.dotnet))) {if ((Test-StageOverlap $destination $other) -and -not $destination.StartsWith((Join-Path $profile.root 'backups')+'\',[StringComparison]::OrdinalIgnoreCase)) {Stop-ServerCheck 'server_backup_paths_overlap'}}
            $answer=@(& (Join-Path $script:ServerOperatorsRoot 'New-RackClickDatabaseBackup.ps1') -PostgresBinPath $instance.pgBin -ProfilePath (Join-Path $instance.privateRoot 'backup-profile.json') -DestinationPath $destination)
            $operationExit=[int]$LASTEXITCODE
            $result=($answer -join [Environment]::NewLine)|ConvertFrom-Json
            if (-not $result.valid -or $result.exitCode -ne $operationExit -or $operationExit -ne 0) {Stop-ServerCheck 'server_backup_failed' 1}
            $result|ConvertTo-Json -Compress
        }
    } catch {
        $code='server_operation_failed';$operationExit=2
        foreach ($pair in @(@('serverCode','serverExit'),@('deploymentCode','deploymentExit'),@('instanceCode','instanceExit'),@('code','exitCode'))) {if ($_.Exception.Data.Contains($pair[0])) {$code=$_.Exception.Data[$pair[0]];$operationExit=[int]$_.Exception.Data[$pair[1]];break}}
        Write-ServerOperationResult $code $operationExit
    } finally {Close-ServerProfile $profile;if (Get-Command Restore-LauncherInheritedConfiguration -ErrorAction SilentlyContinue) {Restore-LauncherInheritedConfiguration $launcherInheritedConfiguration};[Environment]::SetEnvironmentVariable('TEMP',$serverOriginalTemp,'Process');[Environment]::SetEnvironmentVariable('TMP',$serverOriginalTmp,'Process')}
    exit $operationExit
}
function Write-LauncherJson {
    param([string]$Path,$Value)
    Assert-RackClickProcessPrivateAcl ([IO.Path]::GetDirectoryName($Path))
    $temporary=Join-Path ([IO.Path]::GetDirectoryName($Path)) ('record-'+[guid]::NewGuid().ToString('N')+'.json')
    $stream=$null
    try {
        $stream=[IO.File]::Open($temporary,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
        $bytes=(New-Object Text.UTF8Encoding($false)).GetBytes(($Value | ConvertTo-Json -Depth 6 -Compress)+[Environment]::NewLine)
        $stream.Write($bytes,0,$bytes.Length); $stream.Flush($true); $stream.Dispose(); $stream=$null
        if ([IO.File]::Exists($Path)) {
            $expectedBytes=[Convert]::ToBase64String($bytes)
            $retry= [Diagnostics.Stopwatch]::StartNew()
            while ($true) {
                # Only retry errors whose Win32 contract preserves BOTH original names.
                # Validate the same private, non-reparse files and exact source bytes each time.
                if (-not [IO.File]::Exists($temporary) -or -not [IO.File]::Exists($Path)) { Stop-RackClickProcessError 'run_state_files_changed' }
                Assert-RackClickProcessPrivateAcl $temporary; Assert-RackClickProcessPrivateAcl $Path
                if ([Convert]::ToBase64String([IO.File]::ReadAllBytes($temporary)) -cne $expectedBytes) { Stop-RackClickProcessError 'run_state_source_changed' }
                try {
                    # PS5.1 plain $null becomes an empty string; File.Replace needs true CLR null.
                    [IO.File]::Replace($temporary,$Path,[System.Management.Automation.Language.NullString]::Value)
                    break
                } catch [IO.IOException] {
                    $cause=$_.Exception
                    while ($null -ne $cause.InnerException) { $cause=$cause.InnerException }
                    $nativeCode=$cause.HResult -band 0xffff
                    if ($nativeCode -notin @(32,33,1175)) { throw }
                    if ($retry.ElapsedMilliseconds -ge 2000) { Stop-RackClickProcessError 'run_state_replace_timeout' }
                    Start-Sleep -Milliseconds 50
                }
            }
        } else { [IO.File]::Move($temporary,$Path) }
    } finally { if ($null -ne $stream) { $stream.Dispose() } }
}

function Get-LauncherPgEnvironment {
    $values=@{}
    foreach ($key in [Environment]::GetEnvironmentVariables().Keys) { if ([string]$key -like 'PG*') { $values[[string]$key]=$null } }
    $values.PGCLIENTENCODING='UTF8'; $values.LC_ALL='C'; $values.LANG='C'
    return $values
}

function Test-LauncherPortAvailable {
    param([int]$Port)
    $listener=$null
    try { $listener=New-Object Net.Sockets.TcpListener([Net.IPAddress]::Loopback,$Port); $listener.Start() }
    catch { Stop-InstanceCheck 'launcher_port_in_use' 1 }
    finally { if ($null -ne $listener) { $listener.Stop() } }
}

function Test-LauncherReadyBody {
    param($Body,[int]$ExpectedSchema)
    # The expected version comes from the externally authenticated, locked Stage.
    # A version supported by some other Stage is not readiness for this instance.
    return $ExpectedSchema -in @(9,10,11,12,13,14) -and $Body -is [pscustomobject] -and
        $null -ne $Body.PSObject.Properties['status'] -and $Body.status -ceq 'ready' -and
        $null -ne $Body.PSObject.Properties['schemaVersion'] -and $Body.schemaVersion -is [int] -and $Body.schemaVersion -eq $ExpectedSchema
}

function Test-LauncherHttpReady {
    param([string]$Origin,[string]$CertificateSha256='',[int]$ExpectedSchema=0)
    $response=$null; $reader=$null
    try {
        $request=[Net.HttpWebRequest]::Create($Origin+'/health/ready')
        $request.Proxy=$null; $request.AllowAutoRedirect=$false; $request.Timeout=1000; $request.ReadWriteTimeout=1000
        if ($CertificateSha256.Length -gt 0) { $request.ServerCertificateValidationCallback=[RackClickLaunchNative]::PinnedValidator($CertificateSha256) }
        $response=$request.GetResponse()
        if ([int]$response.StatusCode -ne 200) { return $false }
        $reader=New-Object IO.StreamReader($response.GetResponseStream(),[Text.Encoding]::UTF8)
        $body=$reader.ReadToEnd() | ConvertFrom-Json
        return Test-LauncherReadyBody $body $ExpectedSchema
    } catch { return $false }
    finally { if ($null -ne $reader) { $reader.Dispose() }; if ($null -ne $response) { $response.Dispose() } }
}

function Test-LauncherRuntime {
    param([hashtable]$Instance,[string]$Logs)
    $ps=Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
    $arguments=@('-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',(Join-Path $script:ServerOperatorsRoot 'Test-RuntimePrerequisites.ps1'),'-DotNetPath',$Instance.dotnet,'-PostgresBinPath',$Instance.pgBin,'-RuntimeConfigPath',(Join-Path $Instance.stageRoot 'server\RackClick.Server.runtimeconfig.json'),'-PostgresVersion','17.11')
    $handle=Start-RackClickOwnedProcess -Executable $ps -Arguments $arguments -WorkingDirectory $Instance.root -Environment @{} -LogDirectory $Logs -Label 'runtime-preflight'
    $result=Wait-RackClickOwnedProcess -Handle $handle -TimeoutSeconds 90
    if ($result.exitCode -ne 0 -or $result.stderr.Length -ne 0) { Stop-InstanceCheck 'launcher_runtime_unavailable' 1 }
    try { $report=$result.stdout | ConvertFrom-Json } catch { Stop-InstanceCheck 'launcher_runtime_invalid' }
    if (-not $report.ready -or $report.exitCode -ne 0 -or $report.postgresRequiredVersion -ne '17.11') { Stop-InstanceCheck 'launcher_runtime_unavailable' 1 }
    foreach ($name in @('pg_ctl','pg_isready')) {
        $executable=Join-Path $Instance.pgBin ($name+'.exe')
        if (-not [IO.File]::Exists($executable)) { Stop-InstanceCheck 'launcher_postgres_tool_missing' 1 }
        Assert-RackClickProcessNoReparse $executable
        if (-not (Test-RuntimeX64Pe $executable)) { Stop-InstanceCheck 'launcher_postgres_tool_architecture' 1 }
        $handle=Start-RackClickOwnedProcess -Executable $executable -Arguments @('--version') -WorkingDirectory $Instance.root -Environment (Get-LauncherPgEnvironment) -LogDirectory $Logs -Label ('version-'+$name)
        $result=Wait-RackClickOwnedProcess -Handle $handle -TimeoutSeconds 20
        if ($result.exitCode -ne 0 -or $result.stderr.Length -ne 0 -or $result.stdout.Trim() -cne ($name+' (PostgreSQL) 17.11')) { Stop-InstanceCheck 'launcher_postgres_tool_version' 1 }
    }
}

$profile=$null; $instance=$null; $lock=$null; $pg=$null; $app=$null; $runRoot=$null; $record=$null; $tls=$null; $control=$null
$pgReady=$false; $pgClean=$false; $ready=$false; $runId=''; $ownedPgPid=0
$final=[ordered]@{event='stopped';schemaVersion=1;valid=$false;exitCode=2;code='launcher_failed';runId='';instanceId='';postgresCleanStop=$false;applicationHttpDrain=$false;applicationGracefulExit=$false}
try {
    if ($launcherInputs.stopAfter -lt 0 -or $launcherInputs.stopAfter -gt 3600) { Stop-InstanceCheck 'stop_after_invalid' }
    $profile=Read-ServerProfile $serverOperationInputs.manifest $serverOperationInputs.sha
    $env:TEMP=Join-Path $profile.root 'temp';$env:TMP=$env:TEMP
    . (Join-Path $script:ServerOperatorsRoot 'RackClick.LaunchControl.ps1')
    $launcherInheritedConfiguration=Clear-LauncherInheritedConfiguration
    $instance=$profile.instance
    $expectedSchema=Get-StageSchema $instance.stageRoot
    $effectiveOrigin=$profile.origin.origin;$certificatePin=$profile.certificateSha256
    $tls=@{pfxPath=$profile.pfx;password=$profile.password}
    $final.instanceId=$instance.id
    Assert-RackClickProcessPrivateAcl $instance.root
    if ([IO.File]::Exists($instance.lockPath)) { Assert-RackClickProcessPrivateAcl $instance.lockPath }
    try { $lock=[IO.File]::Open($instance.lockPath,[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None) }
    catch [IO.IOException] {
        if (($_.Exception.HResult -band 0xffff) -in @(32,33)) { Stop-InstanceCheck 'instance_in_use' 1 }
        Stop-InstanceCheck 'instance_lock_unavailable'
    }
    # The instance reader holds the exact manifest and all five secret files read-locked.
    Test-LauncherPortAvailable $instance.pgPort
    $bindProbe=New-Object Net.Sockets.TcpListener([Net.IPAddress]::Parse($profile.origin.bind),$profile.origin.port)
    try {$bindProbe.Start()} finally {$bindProbe.Stop()}
    $pidPath=Join-Path $instance.pgData 'postmaster.pid'
    # Existing pid files, even apparently stale ones, require a separate recovery audit.
    # Never start against or stop an out-of-band backend for the same data directory.
    if ([IO.File]::Exists($pidPath) -or [IO.Directory]::Exists($pidPath)) { Stop-InstanceCheck 'postgres_pid_file_exists' 1 }
    $runId=$serverOperationInputs.runId; $final.runId=$runId
    if ($launcherInputs.graceful) { $control=@{pipe=('rc-shutdown-'+$runId.Replace('-',''));token=(New-InstancePassword)} }
    $runRoot=New-RackClickProcessPrivateDirectory (Join-Path $instance.logRoot ('launcher-'+$runId))
    Test-LauncherRuntime -Instance $instance -Logs $runRoot
    $record=[ordered]@{schemaVersion=1;instanceId=$instance.id;runId=$runId;status='starting';publicOrigin=$effectiveOrigin;requestRelativePath=('launcher-'+$runId+'/stop-request.json');code='starting';utc=[DateTime]::UtcNow.ToString('o')}
    Write-LauncherJson (Join-Path $runRoot 'run-state.json') $record
    Write-LauncherJson (Join-Path $instance.logRoot 'active-run.json') $record
    $pgEnvironment=Get-LauncherPgEnvironment
    $pg=Start-RackClickOwnedProcess -Executable (Join-Path $instance.pgBin 'postgres.exe') -Arguments @('-D','pgdata','-h','127.0.0.1','-p',[string]$instance.pgPort) -WorkingDirectory $instance.root -Environment $pgEnvironment -LogDirectory $runRoot -Label 'postgres'
    $deadline=[DateTime]::UtcNow.AddSeconds(40)
    while ([DateTime]::UtcNow -lt $deadline) {
        if ($pg.Process.HasExited) { Stop-InstanceCheck 'postgres_start_failed' 1 }
        $pidReady=$false
        if ([IO.File]::Exists($pidPath)) {
            try {
                $lines=[IO.File]::ReadAllLines($pidPath)
                $pidReady=$lines.Count -ge 8 -and $lines[0] -match '^[1-9][0-9]*$' -and $lines[3] -eq [string]$instance.pgPort -and $lines[7].Trim() -ceq 'ready'
            } catch { $pidReady=$false }
        }
        if ($pidReady) {
            $probe=Start-RackClickOwnedProcess -Executable (Join-Path $instance.pgBin 'pg_isready.exe') -Arguments @('-h','127.0.0.1','-p',[string]$instance.pgPort,'-d',$instance.database,'-U',$instance.runtime,'-t','1') -WorkingDirectory $instance.root -Environment $pgEnvironment -LogDirectory $runRoot -Label 'readiness'
            $result=Wait-RackClickOwnedProcess -Handle $probe -TimeoutSeconds 10
            if ($result.exitCode -eq 0 -and -not $pg.Process.HasExited -and (Test-RackClickOwnedProcessMembership -Handle $pg -ProcessId ([int]$lines[0]))) { $ownedPgPid=[int]$lines[0]; $pgReady=$true; break }
        }
        Start-Sleep -Milliseconds 100
    }
    if (-not $pgReady) { Stop-InstanceCheck 'postgres_readiness_timeout' 1 }
    $appEnvironment=@{}
    foreach ($key in [Environment]::GetEnvironmentVariables().Keys) {
        if ([string]$key -like 'PG*' -or [string]$key -like 'ASPNETCORE_*' -or [string]$key -like 'DOTNET_*' -or [string]$key -like 'Kestrel__*' -or [string]$key -like 'Kestrel:*' -or [string]$key -like 'ConnectionStrings__*' -or [string]$key -like 'ConnectionStrings:*' -or [string]$key -like 'Bootstrap__*' -or [string]$key -like 'Bootstrap:*' -or [string]$key -like 'RackClick__*' -or [string]$key -like 'RackClick:*' -or [string]$key -in @('URLS','HTTP_PORTS','HTTPS_PORTS','PublicOrigin','DevelopmentLoopbackHttp')) { $appEnvironment[[string]$key]=$null }
    }
    $appEnvironment.ASPNETCORE_ENVIRONMENT=if ($null -eq $tls) { 'Development' } else { 'Production' }; $appEnvironment.ASPNETCORE_URLS=('https://'+$profile.origin.bind+':'+[string]$profile.origin.port)
    $appEnvironment.ConnectionStrings__RackClick=$instance.runtimeConnectionString
    $appEnvironment.PublicOrigin=$effectiveOrigin; $appEnvironment.DevelopmentLoopbackHttp=if ($null -eq $tls) { 'true' } else { 'false' }
    if ($null -ne $tls) { $appEnvironment.Kestrel__Certificates__Default__Path=$tls.pfxPath; $appEnvironment.Kestrel__Certificates__Default__Password=$tls.password }
    if ($null -ne $control) { $appEnvironment.RackClick__ShutdownPipe=$control.pipe; $appEnvironment.RackClick__ShutdownToken=$control.token }
    $appEnvironment.RackClick__FrontendPath=Join-Path $instance.stageRoot 'frontend'
    $appEnvironment.TEMP=Join-Path $profile.root 'temp';$appEnvironment.TMP=$appEnvironment.TEMP
    $appEnvironment.DOTNET_CLI_TELEMETRY_OPTOUT='1'; $appEnvironment.DOTNET_NOLOGO='1'
    $app=Start-RackClickOwnedProcess -Executable $instance.dotnet -Arguments @((Join-Path $instance.stageRoot 'server\RackClick.Server.dll')) -WorkingDirectory $instance.root -Environment $appEnvironment -LogDirectory $runRoot -Label 'application'
    $deadline=[DateTime]::UtcNow.AddSeconds(40)
    while ([DateTime]::UtcNow -lt $deadline) {
        if ($pg.Process.HasExited -or $app.Process.HasExited) { Stop-InstanceCheck 'application_start_failed' 1 }
        if (Test-LauncherHttpReady $effectiveOrigin $certificatePin $expectedSchema) {
            if ($null -ne $control) { $probeAck=Invoke-LauncherControl -ApplicationHandle $app -Control $control -Action probe }
            $ready=$true; break
        }
        Start-Sleep -Milliseconds 100
    }
    if (-not $ready -or $pg.Process.HasExited -or $app.Process.HasExited) { Stop-InstanceCheck 'application_readiness_timeout' 1 }
    $record.status='ready'; $record.code='ready'; Write-LauncherJson (Join-Path $runRoot 'run-state.json') $record; Write-LauncherJson (Join-Path $instance.logRoot 'active-run.json') $record
    [ordered]@{event='ready';schemaVersion=1;valid=$true;exitCode=0;code='ready';runId=$runId;instanceId=$instance.id;url=$effectiveOrigin;gracefulShutdown=$launcherInputs.graceful;https=($null -ne $tls);scope='Production TLS LAN runtime; certificate trust provisioning is explicit'} | ConvertTo-Json -Compress
    $readyUtc=[DateTime]::UtcNow
    while ($true) {
        if ($pg.Process.HasExited -or $app.Process.HasExited) { Stop-InstanceCheck 'owned_process_ended' 1 }
        $stopPath=Join-Path $runRoot 'stop-request.json'
        if ([IO.File]::Exists($stopPath)) {
            Assert-RackClickProcessPrivateAcl $stopPath
            try { $stop=[IO.File]::ReadAllText($stopPath) | ConvertFrom-Json } catch { Stop-InstanceCheck 'stop_request_invalid' }
            if ($stop.schemaVersion -ne 1 -or $stop.runId -cne $runId -or $stop.instanceId -cne $instance.id) { Stop-InstanceCheck 'stop_request_invalid' }
            break
        }
        if ($launcherInputs.stopAfter -gt 0 -and ([DateTime]::UtcNow-$readyUtc).TotalSeconds -ge $launcherInputs.stopAfter) { break }
        Start-Sleep -Milliseconds 100
    }
    $final.valid=$true; $final.exitCode=0; $final.code='instance_stopped'
} catch {
    if ($_.Exception.Data.Contains('serverCode')) { $final.code=$_.Exception.Data['serverCode']; $final.exitCode=$_.Exception.Data['serverExit'] }
    elseif ($_.Exception.Data.Contains('instanceCode')) { $final.code=$_.Exception.Data['instanceCode']; $final.exitCode=$_.Exception.Data['instanceExit'] }
    elseif ($_.Exception.Data.Contains('httpsCode')) { $final.code=$_.Exception.Data['httpsCode']; $final.exitCode=$_.Exception.Data['httpsExit'] }
    elseif ($_.Exception.Data.Contains('code')) { $final.code=$_.Exception.Data['code']; $final.exitCode=$_.Exception.Data['exitCode'] }
    if ($null -ne $runRoot) { try { [IO.File]::WriteAllText((Join-Path $runRoot 'launcher-error.log'),$_.Exception.ToString(),(New-Object Text.UTF8Encoding($false))) } catch {} }
} finally {
  try {
    try {
        if ($null -ne $app) {
            try { $final.applicationGracefulExit=Stop-LauncherApplication -ApplicationHandle $app -Control $control }
            catch { $final.valid=$false; $final.exitCode=2; $final.code='application_graceful_stop_failed'; Stop-RackClickOwnedProcess $app }
        }
        if ($null -ne $pg -and $pgReady -and -not $pg.Process.HasExited) {
            $currentPid=[IO.File]::ReadAllLines((Join-Path $instance.pgData 'postmaster.pid'))
            if ($currentPid.Count -lt 1 -or $currentPid[0] -cne [string]$ownedPgPid -or -not (Test-RackClickOwnedProcessMembership -Handle $pg -ProcessId $ownedPgPid)) { Stop-InstanceCheck 'postgres_ownership_unverified' }
            $stopper=Start-RackClickOwnedProcess -Executable (Join-Path $instance.pgBin 'pg_ctl.exe') -Arguments @('-D','pgdata','-m','fast','-w','-t','15','stop') -WorkingDirectory $instance.root -Environment (Get-LauncherPgEnvironment) -LogDirectory $runRoot -Label 'postgres-stop'
            $stopResult=Wait-RackClickOwnedProcess -Handle $stopper -TimeoutSeconds 20
            if ($stopResult.exitCode -eq 0 -and $pg.Process.WaitForExit(10000) -and -not [IO.File]::Exists((Join-Path $instance.pgData 'postmaster.pid'))) { $pgClean=$true }
            else { $final.valid=$false; $final.exitCode=2; $final.code='postgres_clean_stop_failed' }
        }
    } catch { $final.valid=$false; $final.exitCode=2; $final.code='owned_shutdown_failed' }
    finally {
        try { if ($null -ne $pg) { Stop-RackClickOwnedProcess $pg }; if ($null -ne $app) { Stop-RackClickOwnedProcess $app } }
        catch { $final.valid=$false; $final.exitCode=2; $final.code='owned_stop_indeterminate' }
    }
    $final.postgresCleanStop=$pgClean
    if ($final.valid -and -not $pgClean) { $final.valid=$false; $final.exitCode=2; $final.code='postgres_clean_stop_failed' }
    if ($null -ne $record) {
        try {
            $record.status=if ($final.valid) { 'stopped' } else { 'failed' }; $record.code=$final.code
            Write-LauncherJson (Join-Path $runRoot 'run-state.json') $record
            Write-LauncherJson (Join-Path $instance.logRoot 'active-run.json') $record
        } catch { $final.valid=$false; $final.exitCode=2; $final.code='run_state_write_failed' }
    }
    if ($null -ne $lock) { $lock.Dispose() }
    if ($null -ne $profile) { Close-ServerProfile $profile }

  } finally {
    try {
        if (Get-Command Restore-LauncherInheritedConfiguration -ErrorAction SilentlyContinue) {Restore-LauncherInheritedConfiguration -Original $launcherInheritedConfiguration}
        [Environment]::SetEnvironmentVariable('TEMP',$serverOriginalTemp,'Process');[Environment]::SetEnvironmentVariable('TMP',$serverOriginalTmp,'Process')
    }
    catch { $final.valid=$false; $final.exitCode=2; $final.code='launcher_environment_restore_failed' }
  }
}
$final | ConvertTo-Json -Compress
exit $final.exitCode
