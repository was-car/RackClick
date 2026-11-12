#requires -Version 5.1
# Import has no side effects. CRT installation is broker-only and explicit.
function Get-SetupCrtPolicy {
    param([bool]$Is64Bit,[object]$Installed,[string]$RegistryVersion,[string]$VcruntimeVersion,[string]$MsvcpVersion)
    $minimum=[version]'14.44.35211.0';$vcr=$null;$msv=$null
    $validVersions=[version]::TryParse($VcruntimeVersion,[ref]$vcr) -and [version]::TryParse($MsvcpVersion,[ref]$msv)
    $ready=$Is64Bit -and $Installed -eq 1 -and $validVersions -and $vcr -ge $minimum -and $msv -ge $minimum
    return [pscustomobject]@{valid=[bool]$ready;exitCode=$(if($ready){0}else{2});code=$(if($ready){'crt_ready'}else{'crt_missing_or_incompatible'});rebootRequired=$false;is64Bit=$Is64Bit;registryInstalled=$Installed;registryVersion=$RegistryVersion;vcruntimeVersion=$VcruntimeVersion;msvcpVersion=$MsvcpVersion;minimumVersion=$minimum.ToString()}
}
function Test-SetupCrt {
    $installed=$null;$registryVersion='';$vcr='';$msv=''
    if([Environment]::Is64BitProcess){
        try{$reg=Get-ItemProperty -LiteralPath 'HKLM:\SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64' -ErrorAction Stop;$installed=$reg.Installed;$registryVersion=[string]$reg.Version}catch{}
        foreach($entry in @(@('vcruntime140.dll','vcr'),@('msvcp140.dll','msv'))){
            try{
                $info=[Diagnostics.FileVersionInfo]::GetVersionInfo((Join-Path $env:SystemRoot ('System32\'+$entry[0])))
                $value=('{0}.{1}.{2}.{3}' -f $info.FileMajorPart,$info.FileMinorPart,$info.FileBuildPart,$info.FilePrivatePart)
                if($entry[1]-eq 'vcr'){$vcr=$value}else{$msv=$value}
            }catch{}
        }
    }
    return Get-SetupCrtPolicy ([Environment]::Is64BitProcess) $installed $registryVersion $vcr $msv
}
function Assert-SetupCrtInstallerMetadata {
    param([string]$Sha256,[string]$Version,[string]$SignatureStatus,[string]$SignerSubject)
    if($Sha256 -cne '843068991daaa1f73ad9f6239bce4d0f6a07a51f18c37ea2a867e9beca71295c'){throw 'crt_installer_hash_mismatch'}
    if($Version -cne '14.51.36247.0'){throw 'crt_installer_version_mismatch'}
    if($SignatureStatus -cne 'Valid' -or $SignerSubject -notmatch '(?:^|,\s*)O=Microsoft Corporation(?:,|$)'){throw 'crt_installer_signature_invalid'}
}
function Assert-SetupCrtNoReparse {
    param([string]$Path)
    if(-not [IO.Path]::IsPathRooted($Path) -or $Path.StartsWith('\\') -or $Path.Substring(2).Contains(':')){throw 'crt_path_invalid'}
    if([IO.Path]::GetFullPath($Path) -cne $Path){throw 'crt_path_not_canonical'}
    $cursor=$Path
    while($cursor){
        if(Test-Path -LiteralPath $cursor){if(((Get-Item -LiteralPath $cursor -Force -ErrorAction Stop).Attributes-band[IO.FileAttributes]::ReparsePoint)-ne 0){throw 'crt_reparse_not_allowed'}}
        $cursor=[IO.Path]::GetDirectoryName($cursor)
    }
}
function Install-SetupCrt {
    param([string]$PayloadRoot,[string]$ReportDirectory)
    $result=[ordered]@{valid=$false;exitCode=1;code='crt_install_failed';rebootRequired=$false;installed=$false;nativeExitCode=$null;inspection=$null}
    $archiveStream=$null;$zip=$null;$exeLock=$null;$process=$null
    try{
        $principal=New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
        if(-not [Environment]::Is64BitProcess -or -not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)){throw 'crt_elevated_x64_required'}
        $current=Test-SetupCrt;$result.inspection=$current
        if($current.valid){$result.valid=$true;$result.exitCode=0;$result.code='crt_already_ready';return [pscustomobject]$result}
        Assert-SetupCrtNoReparse $PayloadRoot;Assert-SetupCrtNoReparse $ReportDirectory
        if(-not [IO.Directory]::Exists($ReportDirectory)){throw 'crt_report_directory_missing'}
        $adminSid=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value
        $acl=Get-Acl -LiteralPath $ReportDirectory -ErrorAction Stop
        if(-not $acl.AreAccessRulesProtected){throw 'crt_report_acl_invalid'}
        foreach($rule in $acl.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier])){
            if($rule.IdentityReference.Value -notin @($adminSid,'S-1-5-18','S-1-5-32-544') -or $rule.AccessControlType-ne 'Allow'){throw 'crt_report_acl_invalid'}
        }
        $archive=Join-Path $PayloadRoot 'RackClick.zip';Assert-SetupCrtNoReparse $archive
        $archiveStream=[IO.File]::Open($archive,'Open','Read','Read')
        $hash=[Security.Cryptography.SHA256]::Create()
        try{$actual=([BitConverter]::ToString($hash.ComputeHash($archiveStream))).Replace('-','').ToLowerInvariant()}finally{$hash.Dispose()}
        if($actual -cne 'c69a82210a4f221058c088d01e5b70a13c4ec1855386692c44774cc6ee28efea'){throw 'crt_archive_hash_mismatch'}
        $archiveStream.Position=0
        Add-Type -AssemblyName System.IO.Compression
        $zip=New-Object IO.Compression.ZipArchive($archiveStream,[IO.Compression.ZipArchiveMode]::Read,$true)
        $entries=@($zip.Entries|Where-Object {$_.FullName -ceq 'prerequisites/vc_redist.x64.exe'})
        if($entries.Count-ne 1 -or $entries[0].Length-le 0 -or $entries[0].Length-gt 104857600){throw 'crt_archive_entry_invalid'}
        $folder=Join-Path $ReportDirectory ('crt-'+[guid]::NewGuid().ToString('N'))
        if(Test-Path -LiteralPath $folder){throw 'crt_destination_exists'}
        $privateAcl=New-Object Security.AccessControl.DirectorySecurity
        $privateAcl.SetSecurityDescriptorSddlForm(('O:'+$adminSid+'G:SYD:P(A;OICI;FA;;;'+$adminSid+')(A;OICI;FA;;;SY)'))
        $null=[IO.Directory]::CreateDirectory($folder,$privateAcl)
        $exe=Join-Path $folder 'vc_redist.x64.exe'
        $source=$entries[0].Open();$target=$null
        try{$target=[IO.File]::Open($exe,'CreateNew','Write','None');$source.CopyTo($target);$target.Flush($true)}finally{if($target){$target.Dispose()};$source.Dispose()}
        $exeLock=[IO.File]::Open($exe,'Open','Read','Read')
        $exeHash=(Get-FileHash -LiteralPath $exe -Algorithm SHA256 -ErrorAction Stop).Hash.ToLowerInvariant()
        $signature=Get-AuthenticodeSignature -LiteralPath $exe -ErrorAction Stop
        $version=[Diagnostics.FileVersionInfo]::GetVersionInfo($exe)
        $versionText=('{0}.{1}.{2}.{3}' -f $version.FileMajorPart,$version.FileMinorPart,$version.FileBuildPart,$version.FilePrivatePart)
        $subject='';if($signature.SignerCertificate){$subject=$signature.SignerCertificate.Subject}
        Assert-SetupCrtInstallerMetadata $exeHash $versionText ([string]$signature.Status) $subject
        $process=Start-Process -FilePath $exe -ArgumentList '/install','/quiet','/norestart' -WindowStyle Hidden -Wait -PassThru
        $result.nativeExitCode=$process.ExitCode
        if($process.ExitCode-eq 3010){$result.exitCode=3010;$result.code='crt_reboot_required';$result.rebootRequired=$true;return [pscustomobject]$result}
        if($process.ExitCode-ne 0){throw 'crt_installer_process_failed'}
        $post=Test-SetupCrt;$result.inspection=$post
        if(-not $post.valid){throw 'crt_postcheck_failed'}
        $result.valid=$true;$result.exitCode=0;$result.code='crt_installed_verified';$result.installed=$true
    }catch{
        $known=@('crt_elevated_x64_required','crt_path_invalid','crt_path_not_canonical','crt_reparse_not_allowed','crt_report_directory_missing','crt_report_acl_invalid','crt_archive_hash_mismatch','crt_archive_entry_invalid','crt_destination_exists','crt_installer_hash_mismatch','crt_installer_version_mismatch','crt_installer_signature_invalid','crt_installer_process_failed','crt_postcheck_failed')
        if($_.Exception.Message -cin $known){$result.code=$_.Exception.Message}
    }finally{
        if($process){$process.Dispose()};if($exeLock){$exeLock.Dispose()};if($zip){$zip.Dispose()};if($archiveStream){$archiveStream.Dispose()}
    }
    return [pscustomobject]$result
}
