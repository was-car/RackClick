#requires -Version 5.1
# Copy a trusted DB backup to a new, protected staging directory. Never restores in place.
function Get-SetupRecoveryStreamHash([IO.Stream]$Stream) {
    $start=$Stream.Position;$sha=[Security.Cryptography.SHA256]::Create()
    try{return ([BitConverter]::ToString($sha.ComputeHash($Stream))).Replace('-','').ToLowerInvariant()}finally{$Stream.Position=$start;$sha.Dispose()}
}
function Test-SetupRecoveryManifest($Manifest,[long]$DumpBytes,[string]$DumpSha256) {
    if($Manifest.schemaVersion-ne1-or$Manifest.kind-cne'RackClickDatabaseBackup'-or$Manifest.postgresVersion-cne'17.11'-or$Manifest.format-cne'custom'-or$Manifest.dumpFile-cne'data.dump'-or$Manifest.dumpBytes-ne$DumpBytes-or$DumpBytes-lt5-or$Manifest.dumpSha256-cne$DumpSha256-or$DumpSha256-cnotmatch'^[a-f0-9]{64}$'){throw 'setup_recovery_backup_invalid'}
}
function Copy-SetupRecoveryInput {
    param([string]$BackupPath,[string]$ExpectedManifestSha256,[string]$DestinationPath)
    Assert-SetupNoReparse $BackupPath;Assert-SetupNoReparse $DestinationPath
    if($ExpectedManifestSha256-cnotmatch'^[a-f0-9]{64}$'-or-not[IO.Directory]::Exists($BackupPath)-or(Test-Path -LiteralPath $DestinationPath)){throw 'setup_recovery_input_invalid'}
    $files=@(Get-ChildItem -LiteralPath $BackupPath -Force -ErrorAction Stop)
    if($files.Count-ne2-or@($files|Where-Object{$_.PSIsContainer-or$_.Name-cnotin@('manifest.json','data.dump')}).Count){throw 'setup_recovery_inventory_invalid'}
    $manifestPath=Join-Path $BackupPath 'manifest.json';$dumpPath=Join-Path $BackupPath 'data.dump'
    Assert-SetupNoReparse $manifestPath;Assert-SetupNoReparse $dumpPath
    $manifestStream=$null;$dumpStream=$null
    try {
        $manifestStream=[IO.File]::Open($manifestPath,'Open','Read','Read');$dumpStream=[IO.File]::Open($dumpPath,'Open','Read','Read')
        if($manifestStream.Length-gt65536-or(Get-SetupRecoveryStreamHash $manifestStream)-cne$ExpectedManifestSha256){throw 'setup_recovery_manifest_hash_mismatch'}
        $reader=New-Object IO.StreamReader($manifestStream,(New-Object Text.UTF8Encoding($false,$true)),$true,4096,$true)
        try{$manifest=$reader.ReadToEnd()|ConvertFrom-Json -ErrorAction Stop}finally{$reader.Dispose();$manifestStream.Position=0}
        Test-SetupRecoveryManifest $manifest $dumpStream.Length (Get-SetupRecoveryStreamHash $dumpStream)
        $null=[IO.Directory]::CreateDirectory($DestinationPath)
        foreach($entry in @(@('manifest.json',$manifestStream),@('data.dump',$dumpStream))){
            $target=[IO.File]::Open((Join-Path $DestinationPath $entry[0]),'CreateNew','Write','None')
            try{$entry[1].Position=0;$entry[1].CopyTo($target);$target.Flush($true)}finally{$target.Dispose()}
        }
        if((Get-FileHash -LiteralPath (Join-Path $DestinationPath 'manifest.json') -Algorithm SHA256).Hash.ToLowerInvariant()-cne$ExpectedManifestSha256-or(Get-FileHash -LiteralPath (Join-Path $DestinationPath 'data.dump') -Algorithm SHA256).Hash.ToLowerInvariant()-cne$manifest.dumpSha256){throw 'setup_recovery_copy_hash_mismatch'}
        return $DestinationPath
    }finally{if($manifestStream){$manifestStream.Dispose()};if($dumpStream){$dumpStream.Dispose()}}
}
