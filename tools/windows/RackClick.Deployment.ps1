#requires -Version 5.1
# Private deployment integrity only. Importing never creates files or starts a runtime.
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
# Runtime prerequisite helpers have a param block in the caller's scope.
$deploymentImportValues=@{}
foreach ($deploymentImportName in @('DotNetPath','PostgresBinPath','RuntimeConfigPath','PostgresVersion','DeploymentPath','ExpectedDeploymentSha256')) {
    $deploymentImportVariable=Get-Variable -Name $deploymentImportName -ErrorAction SilentlyContinue
    if ($null -ne $deploymentImportVariable) { $deploymentImportValues[$deploymentImportName]=$deploymentImportVariable.Value }
}
. (Join-Path $PSScriptRoot 'RackClick.Https.ps1')
foreach ($deploymentImportName in $deploymentImportValues.Keys) { Set-Variable -Name $deploymentImportName -Value $deploymentImportValues[$deploymentImportName] }

function Stop-PrivateDeploymentCheck {
    param([string]$Code,[int]$ExitCode=2)
    $failure=New-Object InvalidOperationException($Code)
    $failure.Data['deploymentCode']=$Code;$failure.Data['deploymentExit']=$ExitCode
    throw $failure
}

function Assert-DeploymentInputAcl {
    param([string]$Path,[string]$Root)
    # Inspect only retained fixed inputs and their ancestors. Never enumerate
    # mutable PGdata/log contents: live PostgreSQL can remove/rotate those files.
    $item=Get-Item -LiteralPath $Path -Force
    while ($null -ne $item) {
        Assert-BackupPrivateAcl $item.FullName
        if ($item.FullName.Equals($Root,[StringComparison]::OrdinalIgnoreCase)) { return }
        if ($item -is [IO.FileInfo]) { $item=$item.Directory } else { $item=$item.Parent }
    }
    Stop-PrivateDeploymentCheck 'deployment_input_binding_invalid'
}

function Read-DeploymentJson {
    param([IO.FileStream]$Stream,[string]$Code)
    if ($Stream.Length -le 0 -or $Stream.Length -gt 32768) { Stop-PrivateDeploymentCheck $Code }
    $bytes=New-Object byte[] ([int]$Stream.Length);$Stream.Position=0;$offset=0
    while ($offset -lt $bytes.Length) {
        $count=$Stream.Read($bytes,$offset,$bytes.Length-$offset)
        if ($count -le 0) { Stop-PrivateDeploymentCheck $Code };$offset+=$count
    }
    try { $utf8=New-Object Text.UTF8Encoding($false,$true);$value=$utf8.GetString($bytes)|ConvertFrom-Json }
    catch { Stop-PrivateDeploymentCheck $Code }
    if ($null -eq $value -or $value -isnot [pscustomobject]) { Stop-PrivateDeploymentCheck $Code }
    return $value
}

function Close-RackClickPrivateDeployment {
    param([hashtable]$Deployment)
    if ($null -eq $Deployment) { return }
    if ($Deployment.ContainsKey('https')) { Close-RackClickHttpsProfile $Deployment.https }
    if ($Deployment.ContainsKey('instance')) { Close-RackClickInstance $Deployment.instance }
    if ($Deployment.ContainsKey('inputLocks')) { foreach ($stream in $Deployment.inputLocks) { $stream.Dispose() } }
}

function Read-RackClickPrivateDeployment {
    param([string]$DeploymentPath,[string]$ExpectedDeploymentSha256,[switch]$Maintenance)
    $streams=@();$instance=$null;$https=$null
    try {
        if ($ExpectedDeploymentSha256 -notmatch '^[a-fA-F0-9]{64}$') { Stop-PrivateDeploymentCheck 'deployment_reference_required' }
        $root=Get-StageLocalPath $DeploymentPath;Assert-InstanceTechnicalRoot $root
        if (-not [IO.Directory]::Exists($root)) { Stop-PrivateDeploymentCheck 'deployment_directory_missing' 1 }
        Assert-BackupPrivateAcl $root
        $directories=@('distribution','https','instance','logs');$files=@('deployment-state.json','deployment.json')
        $entries=@((New-Object IO.DirectoryInfo($root)).GetFileSystemInfos())
        if ($entries.Count -ne 6) { Stop-PrivateDeploymentCheck 'deployment_contents_invalid' }
        foreach ($entry in $entries) {
            if (($entry -is [IO.DirectoryInfo] -and $entry.Name -cnotin $directories) -or
                ($entry -is [IO.FileInfo] -and $entry.Name -cnotin $files)) { Stop-PrivateDeploymentCheck 'deployment_contents_invalid' }
            Assert-BackupPrivateAcl $entry.FullName
        }
        foreach ($name in @('deployment.json','deployment-state.json')) {
            $streams += [IO.File]::Open((Join-Path $root $name),[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
        }
        $digest=Get-RuntimeConfigDigest (Join-Path $root 'deployment.json')
        if ($digest -cne $ExpectedDeploymentSha256.ToLowerInvariant()) { Stop-PrivateDeploymentCheck 'deployment_hash_mismatch' }
        $manifest=Read-DeploymentJson $streams[0] 'deployment_manifest_invalid'
        $keys='httpsProfileSha256,id,instanceId,instanceManifestSha256,kind,publicOrigin,rootPath,schemaVersion,stageManifestSha256,stageReceiptSha256,state'
        if ((($manifest.PSObject.Properties.Name|Sort-Object)-join ',') -cne $keys) { Stop-PrivateDeploymentCheck 'deployment_manifest_invalid' }
        if ($manifest.schemaVersion -isnot [int] -or $manifest.schemaVersion -ne 1) { Stop-PrivateDeploymentCheck 'deployment_manifest_invalid' }
        foreach ($name in @('kind','state','id','rootPath','instanceId','instanceManifestSha256','stageManifestSha256','stageReceiptSha256','httpsProfileSha256','publicOrigin')) {
            if ($manifest.$name -isnot [string]) { Stop-PrivateDeploymentCheck 'deployment_manifest_invalid' }
        }
        if ($manifest.kind -cne 'RackClickPrivateDeployment' -or $manifest.state -cne 'prepared' -or $manifest.rootPath -cne $root) { Stop-PrivateDeploymentCheck 'deployment_manifest_invalid' }
        foreach ($name in @('id','instanceId')) {
            if ($manifest.$name -cnotmatch '^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$') { Stop-PrivateDeploymentCheck 'deployment_manifest_invalid' }
        }
        foreach ($name in @('instanceManifestSha256','stageManifestSha256','stageReceiptSha256','httpsProfileSha256')) {
            if ($manifest.$name -cnotmatch '^[a-f0-9]{64}$') { Stop-PrivateDeploymentCheck 'deployment_manifest_invalid' }
        }
        $state=Read-DeploymentJson $streams[1] 'deployment_state_invalid'
        if ((($state.PSObject.Properties.Name|Sort-Object)-join ',') -cne 'code,deploymentId,schemaVersion,status' -or
            $state.schemaVersion -isnot [int] -or $state.schemaVersion -ne 1 -or $state.deploymentId -isnot [string] -or
            $state.status -isnot [string] -or $state.code -isnot [string] -or $state.deploymentId -cne $manifest.id -or
            $state.status -cne 'prepared' -or $state.code -cne 'deployment_prepared') { Stop-PrivateDeploymentCheck 'deployment_state_invalid' }
        # Inspect retained instance bytes BEFORE calling its reader: never follow stagePath,
        # dotnetPath or postgresBinPath from an unbound manifest into another deployment.
        $instanceRoot=Join-Path $root 'instance';$instancePath=Join-Path $instanceRoot 'instance.json'
        $streams += [IO.File]::Open($instancePath,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
        if ((Get-RuntimeConfigDigest $instancePath) -cne $manifest.instanceManifestSha256) { Stop-PrivateDeploymentCheck 'instance_hash_mismatch' }
        $instanceManifest=Read-DeploymentJson $streams[2] 'deployment_instance_binding_invalid'
        if ($instanceManifest.rootPath -isnot [string] -or $instanceManifest.rootPath -cne $instanceRoot -or
            $instanceManifest.stagePath -isnot [string] -or $instanceManifest.stagePath -cne (Join-Path $root 'distribution') -or
            $instanceManifest.id -cne $manifest.instanceId -or $instanceManifest.stageManifestSha256 -cne $manifest.stageManifestSha256 -or
            $instanceManifest.stageReceiptSha256 -cne $manifest.stageReceiptSha256) { Stop-PrivateDeploymentCheck 'deployment_instance_binding_invalid' }
        foreach ($name in @('postgresBinPath','dotnetPath')) {
            if ($instanceManifest.$name -isnot [string]) { Stop-PrivateDeploymentCheck 'deployment_instance_binding_invalid' }
            $toolPath=Get-StageLocalPath $instanceManifest.$name
            if ($name -eq 'dotnetPath') { $toolPath=[IO.Path]::GetDirectoryName($toolPath) }
            if (Test-StageOverlap $root $toolPath) { Stop-PrivateDeploymentCheck 'deployment_paths_overlap' }
        }
        $instance=Read-RackClickInstance $instanceRoot $manifest.instanceManifestSha256
        foreach ($stream in $instance.inputLocks) { Assert-DeploymentInputAcl $stream.Name $root }
        if ($instance.id -cne $manifest.instanceId -or $instance.root -cne $instanceRoot -or $instance.stageRoot -cne (Join-Path $root 'distribution')) { Stop-PrivateDeploymentCheck 'deployment_instance_binding_invalid' }
        if ($manifest.publicOrigin -cne ('https://127.0.0.1:'+[string]$instance.httpPort)) { Stop-PrivateDeploymentCheck 'deployment_origin_invalid' }
        if (-not $Maintenance) {
            $https=Read-RackClickHttpsProfile -Instance $instance -ProfilePath (Join-Path $root 'https') -ExpectedProfileSha256 $manifest.httpsProfileSha256
            if ($https.origin -cne $manifest.publicOrigin) { Stop-PrivateDeploymentCheck 'deployment_origin_invalid' }
        }
        # The instance reader now owns a retained handle for instance.json.
        $streams[2].Dispose();$streams=@($streams[0],$streams[1])
        return @{id=$manifest.id;root=$root;manifestSha256=$digest;instance=$instance;https=$https;httpsValidated=(-not $Maintenance);inputLocks=$streams}
    } catch {
        Close-RackClickHttpsProfile $https;Close-RackClickInstance $instance
        foreach ($stream in $streams) { $stream.Dispose() }
        throw
    }
}

