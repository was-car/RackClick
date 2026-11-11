#requires -Version 5.1
[CmdletBinding()]
param(
    [ValidateSet('catalog-initialize','catalog-refresh','check','retire','resume')][string]$Action='check',
    [string]$DotnetPath='', [string]$ToolDirectory='', [string]$ExpectedToolSumsSha256='',
    [string]$InstancesRoot='', [string]$InstallationId='', [string]$ServiceName='',
    [ValidateRange(1024,65535)][int]$PostgresPort=55441,
    [string]$CatalogPath='', [string]$ExpectedCatalogSha256='',
    [ValidateRange(0,1000000)][int]$Candidate=0,[string]$OperationId='',
    [Security.SecureString]$OwnerPassword
)
[Console]::OutputEncoding=New-Object Text.UTF8Encoding($false)
$ErrorActionPreference='Stop';$ProgressPreference='SilentlyContinue'
$mfaHostPath=$DotnetPath;$PostgresBinPath=''
$tool=$null;$protocol=$null;$pointer=[IntPtr]::Zero;$success=$false
try{
    $identity=[Security.Principal.WindowsIdentity]::GetCurrent()
    if(-not ([Security.Principal.WindowsPrincipal]::new($identity)).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)){throw 'mfa_maintenance_not_elevated'}
    . (Join-Path $PSScriptRoot 'RackClick.MfaBackupInventory.ps1')
    $id=[guid]::Empty
    if(-not [guid]::TryParseExact($InstallationId,'D',[ref]$id) -or $id -eq [guid]::Empty -or $InstallationId -cne $id.ToString('D') -or $ServiceName -cnotmatch '^[A-Za-z0-9_.-]{1,128}$'){throw 'mfa_maintenance_input_invalid'}
    $root=Assert-BackupPath $InstancesRoot;Assert-BackupNoReparse $root
    $service=Get-CimInstance -ClassName Win32_Service -Filter ("Name='"+$ServiceName+"'")
    if($null -eq $service -or $service.State -cne 'Stopped'){throw 'mfa_maintenance_service_not_stopped'}
    $account=[string]$service.StartName
    if($account.StartsWith('.\')){$account=$env:COMPUTERNAME+$account.Substring(1)}
    $reader=([Security.Principal.NTAccount]::new($account)).Translate([Security.Principal.SecurityIdentifier]).Value
    $tool=Open-MfaBackupTool $ToolDirectory $ExpectedToolSumsSha256
    $request=[ordered]@{action=$Action;ownerConnection='';instancesRoot=$root;installationId=$InstallationId;readerSid=$reader;serviceName=$ServiceName}
    $confirmation=''
    if($Action -in @('catalog-initialize','catalog-refresh')){
        $catalog=Read-MfaBackupBytes $CatalogPath 1048576
        $request.catalogBase64=[Convert]::ToBase64String($catalog)
        $confirmation='CONFIRMO CATALOGO '+$InstallationId
    }
    if($Action -ne 'catalog-initialize'){
        if($ExpectedCatalogSha256 -cnotmatch '^[a-f0-9]{64}$'){throw 'mfa_maintenance_catalog_pin_required'}
        $request.expectedCatalogSha256=$ExpectedCatalogSha256
    }
    if($Action -in @('retire','resume')){
        $operation=[guid]::Empty
        if(-not [guid]::TryParseExact($OperationId,'D',[ref]$operation) -or $operation -eq [guid]::Empty -or $operation.ToString('D') -cne $OperationId){throw 'mfa_maintenance_operation_id_required'}
        $request.operationId=$OperationId
        if($Action -eq 'retire'){
            if($Candidate -lt 1){throw 'mfa_maintenance_candidate_required'}
            $request.candidate=$Candidate;$confirmation='CONFIRMO RETIRADA '+$InstallationId+' v'+$Candidate
        }else{$confirmation='CONFIRMO REANUDAR '+$InstallationId+' '+$OperationId}
    }
    if($confirmation.Length -gt 0){
        $answer=Read-Host ('Escriba exactamente: '+$confirmation)
        if($answer -cne $confirmation){throw 'mfa_maintenance_confirmation_rejected'}
        $request.confirmation=$confirmation
    }
    if($null -eq $OwnerPassword){$OwnerPassword=Read-Host 'Contrasena SQL de mantenimiento (no la cuenta de ejecucion)' -AsSecureString}
    $pointer=[Runtime.InteropServices.Marshal]::SecureStringToBSTR($OwnerPassword)
    $password=[Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
    $request.ownerConnection='Host=127.0.0.1;Port='+$PostgresPort+';Database=rc_db_'+$id.ToString('N')+';Username=rc_owner_'+$id.ToString('N')+';Password="'+$password.Replace('"','""')+'";Pooling=false;Include Error Detail=false'
    $protocol=Start-MfaBackupProtocol $mfaHostPath $tool '--mfa-key-maintenance'
    $protocol.InputWriter.Write(($request | ConvertTo-Json -Compress -Depth 4));$protocol.InputWriter.Close()
    $request=$null;$password=$null
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer);$pointer=[IntPtr]::Zero
    $pending=$protocol.Process.StandardOutput.ReadLineAsync()
    if(-not $pending.Wait(190000)){throw 'mfa_maintenance_timeout'}
    if($null -eq $pending.Result -or $pending.Result.Length -gt 4096){throw 'mfa_maintenance_protocol_invalid'}
    $result=$pending.Result|ConvertFrom-Json -ErrorAction Stop
    if($result.status -cnotin @('verified','rejected') -or $result.code -cnotmatch '^mfa_[a-z_]+$'){throw 'mfa_maintenance_protocol_invalid'}
    if(-not $protocol.Process.WaitForExit(10000) -or $protocol.Process.StandardOutput.ReadToEnd().Length -ne 0){throw 'mfa_maintenance_protocol_invalid'}
    $success=$result.status -ceq 'verified' -and $protocol.Process.ExitCode -eq 0
    if(-not $success -and ($result.status -cne 'rejected' -or $protocol.Process.ExitCode -ne 1)){throw 'mfa_maintenance_protocol_invalid'}
    # Re-serialize only the pinned command's bounded result; no private input or stderr is shown.
    $result | ConvertTo-Json -Compress -Depth 4
}catch{
    $code='mfa_maintenance_operator_failed'
    if($_.Exception.Message -cmatch '^mfa_[a-z_]+$'){$code=$_.Exception.Message}
    [ordered]@{status='rejected';code=$code;maintenanceState='inspect_before_retry'}|ConvertTo-Json -Compress
}finally{
    if($pointer -ne [IntPtr]::Zero){[Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)}
    if(Get-Command Close-MfaBackupProtocol -ErrorAction SilentlyContinue){Close-MfaBackupProtocol $protocol;Close-MfaBackupTool $tool}
}
if($success){exit 0}else{exit 1}
