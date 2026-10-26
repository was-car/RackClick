#requires -Version 5.1
[CmdletBinding()]
param([string]$AttemptId='',[switch]$FunctionsOnly,[switch]$Quiet,[string]$RecoverySessionDirectory='')
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot 'RackClick.Setup.ps1')
. (Join-Path $PSScriptRoot 'RackClick.Setup.Security.ps1')
. (Join-Path $PSScriptRoot 'RackClick.Setup.Diagnostics.ps1')
. (Join-Path $PSScriptRoot 'RackClick.Setup.ServiceDiagnostics.ps1')
. (Join-Path $PSScriptRoot 'RackClick.Setup.ServiceStatus.ps1')
function Get-SetupRecoveryDiagnostic([string]$Directory,[string[]]$AllowedSids) {
    $root=Join-Path $env:LOCALAPPDATA 'RackClick\RecoverySessions'
    $id=[guid]::Empty;$full=[IO.Path]::GetFullPath($Directory)
    $name=[IO.Path]::GetFileName($full)
    if($Directory-cne$full-or[IO.Path]::GetDirectoryName($full)-cne$root-or-not[guid]::TryParseExact($name,'D',[ref]$id)-or$name-cne$id.ToString('D')){throw 'report_recovery_session_invalid'}
    Assert-SetupNoReparse $full
    if(-not[IO.Directory]::Exists($full)){throw 'report_recovery_session_missing'}
    $acl=Get-Acl -LiteralPath $full
    if($acl.GetOwner([Security.Principal.SecurityIdentifier]).Value-notin$AllowedSids){throw 'report_recovery_acl_invalid'}
    $rules=@($acl.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier]));if($rules.Count-eq0){throw 'report_recovery_acl_invalid'}
    foreach($rule in $rules){if($rule.AccessControlType-ne'Allow'-or$rule.IdentityReference.Value-notin$AllowedSids){throw 'report_recovery_acl_invalid'}}
    $resetPath=Join-Path $full 'reset-result.json';$reset=Get-SetupJsonDiagnostic $resetPath $AllowedSids
    if($reset.status-ceq'parsed'){
        # Counts are derived from the same bounded, private receipt; never copy
        # quarantine paths, account names, actions, blockers or raw messages.
        $stream=$null
        try{
            Assert-SetupNoReparse $resetPath
            $stream=[IO.File]::Open($resetPath,'Open','Read','Read')
            $fileAcl=Get-Acl -LiteralPath $resetPath
            if($fileAcl.GetOwner([Security.Principal.SecurityIdentifier]).Value-notin$AllowedSids){throw 'report_recovery_acl_invalid'}
            foreach($rule in $fileAcl.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier])){if($rule.AccessControlType-ne'Allow'-or$rule.IdentityReference.Value-notin$AllowedSids){throw 'report_recovery_acl_invalid'}}
            if($stream.Length-gt1048576){throw 'report_recovery_receipt_too_large'}
            $reader=New-Object IO.StreamReader($stream,(New-Object Text.UTF8Encoding($false,$true)),$true)
            try{$value=$reader.ReadToEnd()|ConvertFrom-Json -ErrorAction Stop}finally{$reader.Dispose()}
            if($value.cleanupComplete-is[bool]){$reset.fields.cleanupComplete=$value.cleanupComplete}
            foreach($pair in @(@('archivedInstances','archivedInstanceCount'),@('retiredAccounts','retiredAccountCount'),@('preserved','preservedCount'),@('remainingBlockers','blockerCount'))){
                $property=$value.PSObject.Properties[$pair[0]]
                $reset.fields[$pair[1]]=if($null-eq$property-or$null-eq$property.Value){0}else{@($property.Value).Count}
            }
        }catch{$reset.countObservation='unavailable'}finally{if($null-ne$stream){$stream.Dispose()}}
    }
    return [ordered]@{sessionId=$name;reset=$reset;launcher=(Get-SetupJsonDiagnostic (Join-Path $full 'launcher-result.json') $AllowedSids);host=(Get-SetupJsonDiagnostic (Join-Path $full 'host-result.json') $AllowedSids)}
}
function New-SetupSanitizedReport([string]$RequestedAttemptId='',[string]$RecoveryDirectory='') {
    if($RequestedAttemptId){$id=[guid]::Empty;if(-not[guid]::TryParseExact($RequestedAttemptId,'D',[ref]$id)-or$RequestedAttemptId-cne$id.ToString('D')){throw 'report_attempt_invalid'}}
    $root=Join-Path $env:LOCALAPPDATA 'RackClick\Setup';Assert-SetupNoReparse $root
    $folders=@();if([IO.Directory]::Exists($root)){$folders=@(Get-SetupDiagnosticFolders $root $RequestedAttemptId)}
    $allowed=@([Security.Principal.WindowsIdentity]::GetCurrent().User.Value,'S-1-5-18','S-1-5-32-544')
    $recovery=$null;if($RecoveryDirectory){$recovery=Get-SetupRecoveryDiagnostic $RecoveryDirectory $allowed}
    if(($folders.Count-eq0-and$null-eq$recovery)-or($RequestedAttemptId-and$folders.Count-eq0)){throw 'report_not_found'}
    $attempts=@(foreach($folder in $folders){Get-SetupAttemptDiagnostic $folder.FullName $allowed})
    $record=[ordered]@{schemaVersion=5;kind='RackClickSanitizedInstallationReport';generatedUtc=[DateTime]::UtcNow.ToString('o');computer=$env:COMPUTERNAME;attemptId='';reports=[ordered]@{};observations=[ordered]@{};privateDiagnostics=[ordered]@{};serviceDiagnostics=@{status='unavailable_binding'};installationState=@{status='unavailable';rebootVerified=$false;currentHealthVerified=$false;productAdopted=$false};attemptCount=$attempts.Count;attemptLimit=10;additionalAttempts=@();recoverySession=$recovery}
    if($attempts.Count-gt0){$latest=$attempts[0];$record.attemptId=$latest.attemptId;$record.reports=$latest.reports;$record.observations=$latest.observations;$record.privateDiagnostics=$latest.privateDiagnostics;$record.serviceDiagnostics=$latest.serviceDiagnostics;$record.installationState=$latest.installationState}
    if($attempts.Count-gt1){$record.additionalAttempts=@($attempts|Select-Object -Skip 1)}
    return $record
}
function Export-SetupSanitizedReport($Record,[string]$Directory) {
    Assert-SetupNoReparse $Directory
    if(-not[IO.Directory]::Exists($Directory)){throw 'report_output_directory_missing'}
    $stamp=[DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ')+'-'+[guid]::NewGuid().ToString('N').Substring(0,8)
    $zipPath=Join-Path $Directory ('RackClick-Informe-Instalacion-'+$stamp+'.zip')
    Add-Type -AssemblyName System.IO.Compression
    $file=[IO.File]::Open($zipPath,'CreateNew','Write','None')
    try{
        $zip=New-Object IO.Compression.ZipArchive($file,[IO.Compression.ZipArchiveMode]::Create,$true)
        try{$entry=$zip.CreateEntry('INFORME.json');$stream=$entry.Open();try{$bytes=(New-Object Text.UTF8Encoding($false)).GetBytes(($Record|ConvertTo-Json -Depth 14));$stream.Write($bytes,0,$bytes.Length)}finally{$stream.Dispose()}}finally{$zip.Dispose()}
    }finally{$file.Dispose()}
    return $zipPath
}
if($FunctionsOnly){return}
if(-not(Test-SetupAdministrator)){
    if($Quiet){@{valid=$false;exitCode=1;code='report_administrator_required'}|ConvertTo-Json -Compress;exit 1}
    try{
        $arguments=@('-NoProfile','-STA','-ExecutionPolicy','Bypass','-File',(ConvertTo-SetupArgument $PSCommandPath))
        if($AttemptId){if($AttemptId-cnotmatch'^[a-f0-9-]{36}$'){throw 'report_attempt_invalid'};$arguments+=@('-AttemptId',$AttemptId)}
        if($RecoverySessionDirectory){$arguments+=@('-RecoverySessionDirectory',(ConvertTo-SetupArgument $RecoverySessionDirectory))}
        $p=Start-Process -FilePath "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" -ArgumentList $arguments -Verb RunAs -Wait -PassThru;exit $p.ExitCode
    }catch{exit 1}
}
try {
    $record=New-SetupSanitizedReport $AttemptId $RecoverySessionDirectory
    $zipPath=Export-SetupSanitizedReport $record ([Environment]::GetFolderPath('Desktop'))
    if(-not$Quiet){Add-Type -AssemblyName System.Windows.Forms;[Windows.Forms.MessageBox]::Show(('Informe de diagnostico creado en el Escritorio:'+[Environment]::NewLine+$zipPath+[Environment]::NewLine+'Incluye hasta diez intentos recientes, separados por identificador; no incluye contrasenas ni logs completos.'),'RackClick','OK','Information')|Out-Null}
    @{valid=$true;exitCode=0;code='report_exported';zipPath=$zipPath;attemptId=$record.attemptId}|ConvertTo-Json -Compress
    exit 0
}catch{$code='report_export_failed';if($_.Exception.Message-cmatch'^report_[a-z0-9_]{1,100}$'){$code=$_.Exception.Message};@{valid=$false;exitCode=1;code=$code}|ConvertTo-Json -Compress;exit 1}
