#requires -Version 5.1
# Pure validation helpers. Import never changes the host.
# Use the built-in PS5 modules even when launched from a PowerShell 7 parent.
$env:PSModulePath=Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\Modules'
function Assert-SetupNoReparse([string]$Path) {
    if (-not [IO.Path]::IsPathRooted($Path) -or $Path.StartsWith('\\')) {throw 'setup_local_path_required'}
    $cursor=[IO.Path]::GetFullPath($Path)
    while($cursor){if(Test-Path -LiteralPath $cursor){if(((Get-Item -LiteralPath $cursor -Force -ErrorAction Stop).Attributes-band[IO.FileAttributes]::ReparsePoint)-ne 0){throw 'setup_reparse_not_allowed'}};$cursor=[IO.Path]::GetDirectoryName($cursor)}
}
function ConvertTo-SetupArgument([string]$Value) {
    if ($Value.Contains('"') -or $Value.Contains("`r") -or $Value.Contains("`n") -or $Value.EndsWith('\')) {throw 'setup_argument_invalid'}
    return '"'+$Value+'"'
}
function Write-SetupJson([string]$Path,$Value) {
    Assert-SetupNoReparse $Path
    $bytes=(New-Object Text.UTF8Encoding($false)).GetBytes(($Value|ConvertTo-Json -Depth 12 -Compress))
    $temporary=$Path+'.'+[guid]::NewGuid().ToString('N')+'.tmp'
    $stream=[IO.File]::Open($temporary,'CreateNew','Write','None')
    try {$stream.Write($bytes,0,$bytes.Length);$stream.Flush($true)}finally{$stream.Dispose()}
    if([IO.File]::Exists($Path)){
        # PS5 marshals $null to an empty string for the backup-name argument.
        $previous=$temporary+'.previous'
        for($attempt=0;;$attempt++){
            try{[IO.File]::Replace($temporary,$Path,$previous);break}catch [IO.IOException]{
                if(($_.Exception.HResult-band65535)-notin@(32,33)-or$attempt-ge9){throw}
                Start-Sleep -Milliseconds 25
            }
        }
        [IO.File]::Delete($previous)
    }else{[IO.File]::Move($temporary,$Path)}
}
function Read-SetupPlan([string]$Path) {
    Assert-SetupNoReparse $Path
    $plan=[IO.File]::ReadAllText($Path)|ConvertFrom-Json -ErrorAction Stop
    $expected=@('schemaVersion','id','bindAddress','publicHost','httpsPort','postgresPort','allowedSubnet','systemhaus','bootstrapUser','serviceName','accountName','mode','backupPath','backupManifestSha256','trustOnServer')
    $actual=@($plan.PSObject.Properties.Name)
    if($actual.Count-ne$expected.Count-or@(Compare-Object $expected $actual -CaseSensitive).Count-ne 0-or$plan.schemaVersion-ne 1){throw 'setup_plan_invalid'}
    $guid=[guid]::Empty
    if(-not [guid]::TryParseExact([string]$plan.id,'D',[ref]$guid)-or$plan.id-cne$guid.ToString('D')){throw 'setup_plan_id_invalid'}
    $ip=$null
    if(-not [Net.IPAddress]::TryParse([string]$plan.bindAddress,[ref]$ip)-or$ip.AddressFamily-ne'InterNetwork'-or[Net.IPAddress]::IsLoopback($ip)-or$ip.ToString()-ne$plan.bindAddress-or$ip.ToString().StartsWith('169.254.')-or$ip.ToString().StartsWith('0.')){throw 'setup_bind_invalid'}
    $hostName=[string]$plan.publicHost
    if($hostName.Length-gt253-or$hostName-cnotmatch '^[a-zA-Z0-9](?:[a-zA-Z0-9.-]*[a-zA-Z0-9])?$'-or[Uri]::CheckHostName($hostName)-notin @('Dns','IPv4')){throw 'setup_public_host_invalid'}
    foreach($port in @($plan.httpsPort,$plan.postgresPort)){if($port-isnot[int]-and$port-isnot[long]){throw 'setup_port_invalid'};if($port-lt1024-or$port-gt65535){throw 'setup_port_invalid'}}
    if($plan.httpsPort-eq$plan.postgresPort){throw 'setup_ports_overlap'}
    $net=([string]$plan.allowedSubnet).Split('/');$network=$null;$prefix=0
    if($net.Count-ne2-or-not[Net.IPAddress]::TryParse($net[0],[ref]$network)-or$network.AddressFamily-ne'InterNetwork'-or-not[int]::TryParse($net[1],[ref]$prefix)-or$prefix-lt8-or$prefix-gt32){throw 'setup_subnet_invalid'}
    $a=$ip.GetAddressBytes();$b=$network.GetAddressBytes()
    for($i=0;$i-lt4;$i++){$bits=[Math]::Min(8,[Math]::Max(0,$prefix-$i*8));$mask=if($bits-eq0){0}else{256-[int][Math]::Pow(2,8-$bits)};if(($a[$i]-band$mask)-ne$b[$i]){throw 'setup_subnet_not_canonical_or_not_local'}}
    foreach($name in @('systemhaus','bootstrapUser')){if($plan.$name-isnot[string]-or[string]::IsNullOrWhiteSpace($plan.$name)-or$plan.$name.Length-gt100-or$plan.$name-match'[\x00-\x1f"\r\n]'){throw 'setup_name_invalid'}}
    if($plan.serviceName-cnotmatch '^RackClick(?:-Recovery-[a-f0-9]{8,32})?$'-or$plan.accountName-cnotmatch '^RackClickSvc(?:[a-zA-Z0-9]{1,8})?$'){throw 'setup_account_or_service_invalid'}
    if($plan.mode-cnotin@('New','Restore')-or$plan.trustOnServer-isnot[bool]-or-not$plan.trustOnServer){throw 'setup_mode_or_trust_invalid'}
    if($plan.mode-ceq'New'){if($plan.backupPath-ne''-or$plan.backupManifestSha256-ne''){throw 'setup_new_backup_not_allowed'}}else{
        Assert-SetupNoReparse ([string]$plan.backupPath)
        if($plan.backupManifestSha256-cnotmatch'^[a-f0-9]{64}$'){throw 'setup_backup_reference_required'}
    }
    return $plan
}
function Assert-SetupPayload([string]$Root) {
    Assert-SetupNoReparse $Root
    $manifest=[IO.File]::ReadAllText((Join-Path $Root 'payload.json'))|ConvertFrom-Json -ErrorAction Stop
    if($manifest.schemaVersion-ne1-or$manifest.kind-cne'RackClickServerSetup'-or$manifest.bundleArchiveSha256-cne'c69a82210a4f221058c088d01e5b70a13c4ec1855386692c44774cc6ee28efea'){throw 'setup_payload_invalid'}
    $seen=New-Object 'Collections.Generic.HashSet[string]' ([StringComparer]::OrdinalIgnoreCase)
    foreach($file in $manifest.files){
        if($file.path-cnotmatch'^[a-zA-Z0-9_. /-]+$'-or$file.path-match'(^|/)\.\.?(/|$)'-or$file.path.StartsWith('/')-or-not$seen.Add($file.path)){throw 'setup_payload_path_invalid'}
        $path=Join-Path $Root ($file.path.Replace('/','\'));Assert-SetupNoReparse $path
        if(-not[IO.File]::Exists($path)-or(Get-Item -LiteralPath $path).Length-ne$file.size-or(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()-cne$file.sha256){throw 'setup_payload_hash_mismatch'}
    }
    $manifestPath=Join-Path $Root 'payload.json'
    $allFiles=@(Get-ChildItem -LiteralPath $Root -Recurse -File -Force)
    if(@($allFiles|Where-Object{[StringComparer]::OrdinalIgnoreCase.Equals($_.FullName,$manifestPath)}).Count-ne1){throw 'setup_payload_unlisted_file'}
    $actual=@($allFiles|Where-Object{-not[StringComparer]::OrdinalIgnoreCase.Equals($_.FullName,$manifestPath)})
    if($actual.Count-ne$seen.Count){throw 'setup_payload_unlisted_file'}
    foreach($file in $actual){if(-not$seen.Contains($file.FullName.Substring($Root.Length+1).Replace('\','/'))){throw 'setup_payload_unlisted_file'}}
    foreach($required in @('RackClick.zip','service/RackClick.WindowsService.dll','operators/Install-RackClickOfflineBundle.ps1','operators/server-install/Prepare-RackClickServer.ps1')){if(-not$seen.Contains($required)){throw 'setup_payload_component_missing'}}
    return $manifest
}
