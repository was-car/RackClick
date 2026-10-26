#requires -Version 5.1
# Read-only diagnostic primitives. Import does not read files or enable privileges.
. (Join-Path $PSScriptRoot 'RackClick.Setup.Lifecycle.ps1')
function Get-SetupDiagnosticFailure($ErrorRecord) {
    $exception=$ErrorRecord.Exception
    for($i=0;$i-lt8-and$null-ne$exception.InnerException;$i++){$exception=$exception.InnerException}
    $safe=[ordered]@{errorType=$exception.GetType().FullName;errorHResult=$exception.HResult}
    if($exception-is[ComponentModel.Win32Exception]){$safe.nativeErrorCode=$exception.NativeErrorCode}
    if($exception.Message-cmatch'^report_[a-z0-9_]{1,100}$'){$safe.code=$exception.Message}
    return $safe
}
function Select-SetupDiagnosticFields($Value) {
    $safe=[ordered]@{}
    foreach($key in @('schemaVersion','success','valid','exitCode','code','stage','installationPercent','rebootVerified','productAdopted','errorType','errorHResult','failureLine','nativeExitCode','rebootRequired','percent','runId','childCode','childErrorType','childFailureLine','childNativeExitCode','processState','retryAllowed','productType','domainRole','partOfDomain','hostProductType','hostDomainRole','hostPartOfDomain','installationId','bootAtInstall','installedUtc','bootUtc','checkedUtc')){
        $property=$Value.PSObject.Properties[$key]
        if($null-ne$property){
            $item=$property.Value
            if($key-ceq'installationId'){
                $id=[guid]::Empty
                if($item-is[string]-and[guid]::TryParseExact($item,'D',[ref]$id)-and$item-ceq$id.ToString('D')){$safe[$key]=$item}
                continue
            }
            if($key-in@('bootAtInstall','installedUtc','bootUtc','checkedUtc')){if(Test-SetupUtcTimestamp $item){$safe[$key]=$item};continue}
            if($key-in@('productType','hostProductType')){if(($item-is[int]-or$item-is[long])-and$item-in@(1,2,3)){$safe[$key]=$item};continue}
            if($key-in@('domainRole','hostDomainRole')){if(($item-is[int]-or$item-is[long])-and$item-ge0-and$item-le5){$safe[$key]=$item};continue}
            if($key-in@('partOfDomain','hostPartOfDomain')){if($item-is[bool]){$safe[$key]=$item};continue}
            if($item-is[bool]-or$item-is[int]-or$item-is[long]-or($item-is[string]-and$item.Length-le160-and$item-cmatch'^[A-Za-z0-9_.-]+$')){$safe[$key]=$item}
        }
    }
    # CRT results already contain the post-install inspection. Export only its
    # typed, bounded facts; never serialize the source object or error messages.
    $codeProperty=$Value.PSObject.Properties['code'];$inspectionProperty=$Value.PSObject.Properties['inspection']
    if($null-ne$codeProperty-and$codeProperty.Value-is[string]-and$codeProperty.Value-cmatch'^crt_[a-z0-9_]{1,100}$'-and$null-ne$inspectionProperty-and$inspectionProperty.Value-is[pscustomobject]){
        $inspection=$inspectionProperty.Value
        $crt=[ordered]@{}
        foreach($key in @('valid','is64Bit')){
            $item=$inspection.PSObject.Properties[$key]
            if($null-ne$item-and$item.Value-is[bool]){$crt[$key]=$item.Value}
        }
        $item=$inspection.PSObject.Properties['registryInstalled']
        if($null-ne$item-and($item.Value-is[int]-or$item.Value-is[long])-and$item.Value-in@(0,1)){$crt.registryInstalled=$item.Value}
        foreach($key in @('registryVersion','vcruntimeVersion','msvcpVersion','minimumVersion')){
            $item=$inspection.PSObject.Properties[$key]
            if($null-ne$item-and$item.Value-is[string]-and($item.Value-ceq''-or$item.Value-cmatch'^v?[0-9]{1,5}(\.[0-9]{1,5}){3}$')){$crt[$key]=$item.Value}
        }
        if($crt.Count-gt0){$safe.crtInspection=$crt}
    }
    return $safe
}
function ConvertFrom-SetupDiagnosticBytes([byte[]]$Bytes) {
    # StreamReader detects BOMs. Also recognize BOM-less UTF16 emitted by some
    # redirection paths; report the choice instead of silently omitting a file.
    $encoding='bom_or_utf8';$text=''
    if($Bytes.Length-ge4-and$Bytes[0]-eq123-and$Bytes[1]-eq0-and$Bytes[3]-eq0){$text=(New-Object Text.UnicodeEncoding($false,$false,$true)).GetString($Bytes);$encoding='utf16le_without_bom'}
    elseif($Bytes.Length-ge4-and$Bytes[0]-eq0-and$Bytes[1]-eq123-and$Bytes[2]-eq0){$text=(New-Object Text.UnicodeEncoding($true,$false,$true)).GetString($Bytes);$encoding='utf16be_without_bom'}
    else{
        $stream=New-Object IO.MemoryStream(,$Bytes)
        $reader=New-Object IO.StreamReader($stream,(New-Object Text.UTF8Encoding($false,$true)),$true)
        try{$text=$reader.ReadToEnd()}finally{$reader.Dispose();$stream.Dispose()}
    }
    return @{text=$text;encoding=$encoding}
}
function ConvertTo-SetupJsonObservation([byte[]]$Bytes) {
    $observation=[ordered]@{status='invalid_json';bytes=$Bytes.Length;fields=[ordered]@{}}
    $decoded=$null
    $digest=[Security.Cryptography.SHA256]::Create()
    try{$observation.sha256=([BitConverter]::ToString($digest.ComputeHash($Bytes))).Replace('-','').ToLowerInvariant()}finally{$digest.Dispose()}
    try{
        $decoded=ConvertFrom-SetupDiagnosticBytes $Bytes;$observation.encoding=$decoded.encoding
        $value=$decoded.text|ConvertFrom-Json -ErrorAction Stop
        if($value-isnot[pscustomobject]){return $observation}
        $observation.fields=Select-SetupDiagnosticFields $value;$observation.status='parsed'
    }catch{
        $observation.failure=Get-SetupDiagnosticFailure $_
        # Extract only a bounded error token when the rest of a log is not JSON.
        # It remains diagnostic-only; never recover a success/valid/exit claim.
        if($null-ne$decoded){
            $observation.hasClixml=$decoded.text.StartsWith('#< CLIXML',[StringComparison]::Ordinal)
            $observation.clixmlProgressRecords=[regex]::Matches($decoded.text,'\bS="progress"').Count
            $match=[regex]::Match($decoded.text,'"code"\s*:\s*"((?:setup|preparation|server|preflight|deployment|installation|profile|runtime|finalize)_[a-z0-9_]{1,100})"')
            if($match.Success){$observation.recoveredErrorCode=$match.Groups[1].Value}
        }
    }
    return $observation
}
function Get-SetupJsonDiagnostic([string]$Path,[string[]]$AllowedSids) {
    $result=[ordered]@{status='unavailable'};$stream=$null
    try{
        Assert-SetupNoReparse $Path
        $stream=[IO.File]::Open($Path,'Open','Read','Read')
        $acl=Get-Acl -LiteralPath $Path -ErrorAction Stop
        if($acl.GetOwner([Security.Principal.SecurityIdentifier]).Value-notin$AllowedSids){throw 'report_acl_invalid'}
        $rules=@($acl.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier]))
        if($rules.Count-eq0){throw 'report_acl_invalid'}
        foreach($rule in $rules){if($rule.AccessControlType-ne'Allow'-or$rule.IdentityReference.Value-notin$AllowedSids){throw 'report_acl_invalid'}}
        if($stream.Length-gt1048576){$result.status='too_large';$result.bytes=$stream.Length;return $result}
        $bytes=New-Object byte[] ([int]$stream.Length);$offset=0
        while($offset-lt$bytes.Length){$read=$stream.Read($bytes,$offset,$bytes.Length-$offset);if($read-le0){throw 'report_short_read'};$offset+=$read}
        return ConvertTo-SetupJsonObservation $bytes
    }catch{
        $result.failure=Get-SetupDiagnosticFailure $_
        if($_.Exception.Message-ceq'report_acl_invalid'){$result.status='acl_rejected'}
        elseif($result.failure.errorType-cin@('System.IO.FileNotFoundException','System.IO.DirectoryNotFoundException')){$result.status='missing'}
        else{$result.status='read_failed'}
        return $result
    }finally{if($null-ne$stream){$stream.Dispose()}}
}
function Read-SetupDiagnosticBinding([string]$AttemptId) {
    $id=[guid]::Empty
    if(-not[guid]::TryParseExact($AttemptId,'D',[ref]$id)-or$AttemptId-cne$id.ToString('D')){throw 'report_attempt_invalid'}
    $path='C:\Program Files\RackClick\'+$AttemptId+'\preparation-plan.json'
    Assert-SetupNoReparse $path
    if((Get-Item -LiteralPath $path -Force -ErrorAction Stop).Length-gt32768){throw 'report_plan_invalid'}
    $acl=Get-Acl -LiteralPath $path -ErrorAction Stop
    if($acl.GetOwner([Security.Principal.SecurityIdentifier]).Value-notin@('S-1-5-18','S-1-5-32-544')){throw 'report_plan_owner_invalid'}
    $plan=[IO.File]::ReadAllText($path)|ConvertFrom-Json -ErrorAction Stop
    if($plan.id-cne$AttemptId-or$plan.codeRoot-cne('C:\Program Files\RackClick\'+$AttemptId)-or$plan.instancePath-cne('C:\ProgramData\RackClick\Instances\'+$AttemptId+'\instance')-or$plan.serviceSid-cnotmatch'^S-1-5-21-(\d+-){3}\d+$'-or$plan.serviceSid.EndsWith('-500')){throw 'report_plan_binding_invalid'}
    $write=[Security.AccessControl.FileSystemRights]::Write-bor[Security.AccessControl.FileSystemRights]::Delete-bor[Security.AccessControl.FileSystemRights]::ChangePermissions-bor[Security.AccessControl.FileSystemRights]::TakeOwnership
    $rules=@($acl.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier]));if($rules.Count-eq0){throw 'report_plan_acl_invalid'}
    foreach($rule in $rules){
        if($rule.AccessControlType-ne'Allow'-or$rule.IdentityReference.Value-notin@('S-1-5-18','S-1-5-32-544',$plan.serviceSid)-or($rule.IdentityReference.Value-ceq$plan.serviceSid-and($rule.FileSystemRights-band$write)-ne0)){throw 'report_plan_acl_invalid'}
    }
    $serviceName='';$serviceProperty=$plan.PSObject.Properties['serviceName']
    if($null-ne$serviceProperty-and$serviceProperty.Value-is[string]-and$serviceProperty.Value-cmatch'^RackClick(?:-Recovery-[a-f0-9]{8,32})?$'){$serviceName=$serviceProperty.Value}
    return @{id=$AttemptId;serviceSid=[string]$plan.serviceSid;serviceName=$serviceName}
}
function Assert-SetupPrivateDiagnosticName([string]$Name) {
    if($Name-cnotin@('preparation/exception-private.log','preparation/installation-stdout.log','preparation/installation-stderr.log','preparation/profile-stdout.log','preparation/profile-stderr.log','instance/installation-state.json')){throw 'report_private_path_not_allowed'}
}
function Read-SetupPrivateDiagnosticBytes([string]$AttemptId,[string]$Name,[string]$ServiceSid) {
    Assert-SetupAdministrator
    Assert-SetupPrivateDiagnosticName $Name
    $parent='C:\ProgramData\RackClick\Instances\'+$AttemptId
    Assert-SetupPath ($parent+'\instance') 'instance' -NativeHandleWalk
    $sid=New-Object Security.Principal.SecurityIdentifier($ServiceSid)
    if($sid.Value-notmatch'^S-1-5-21-(\d+-){3}\d+$'-or$sid.Value.EndsWith('-500')){throw 'report_service_sid_invalid'}
    $path=Join-Path $parent $Name.Replace('/','\')
    # Existing native reader holds non-reparse ancestor/file handles, verifies
    # SID/SYSTEM private ACL and bounds the read. Only backup READ is enabled;
    # no restore privilege, owner or ACL change is needed for collection.
    Initialize-SetupSecurityNative;$previous=$null
    try{
        $previous=[RackClickSetupSecurityNative]::Privilege('SeBackupPrivilege',2)
        return ,([byte[]][RackClickSetupSecurityNative]::ReadPrepared($path,$sid.Value))
    }finally{if($null-ne$previous){$null=[RackClickSetupSecurityNative]::Privilege('SeBackupPrivilege',$previous)}}
}
function Get-SetupExceptionDiagnostic([byte[]]$Bytes) {
    $decoded=ConvertFrom-SetupDiagnosticBytes $Bytes
    $result=[ordered]@{status='exception_summary';bytes=$Bytes.Length;frames=@()}
    $match=[regex]::Match($decoded.text,'\A(System\.[A-Za-z0-9_.]+Exception)(?=:)')
    if($match.Success){$result.errorType=$match.Groups[1].Value}
    $known=@('Prepare-RackClickServer.ps1','Install-RackClickOfflineBundle.ps1','New-RackClickServerProfile.ps1','RackClick.Backup.ps1','RackClick.Deployment.ps1','RackClick.OfflineBundle.ps1','RackClick.Instance.ps1','RackClick.Stage.ps1','RackClick.Https.ps1','RackClick.ServerRuntime.ps1')
    foreach($match in [regex]::Matches($decoded.text,'(?m)\\([A-Za-z0-9_.-]+\.ps1):\s*(?:line|Zeile|l[i\u00ed]nea)\s+(\d{1,6})(?:\D|$)')){
        if($match.Groups[1].Value-cin$known){$result.frames+=@{script=$match.Groups[1].Value;line=[int]$match.Groups[2].Value}}
        if($result.frames.Count-ge12){break}
    }
    return $result
}
function Get-SetupDiagnosticFolders([string]$Root,[string]$AttemptId='') {
    Assert-SetupNoReparse $Root
    $folders=@(Get-ChildItem -LiteralPath $Root -Directory -Force|Where-Object{
        $id=[guid]::Empty
        ($_.Attributes-band[IO.FileAttributes]::ReparsePoint)-eq0-and[guid]::TryParseExact($_.Name,'D',[ref]$id)-and$_.Name-ceq$id.ToString('D')
    }|Sort-Object LastWriteTime -Descending)
    if($AttemptId){
        $id=[guid]::Empty
        if(-not[guid]::TryParseExact($AttemptId,'D',[ref]$id)-or$AttemptId-cne$id.ToString('D')){throw 'report_attempt_invalid'}
        return @($folders|Where-Object{$_.Name-ceq$AttemptId})
    }
    return @($folders|Select-Object -First 10)
}
function Get-SetupAttemptDiagnostic([string]$Folder,[string[]]$AllowedSids) {
    $id=[IO.Path]::GetFileName($Folder);$parsed=[guid]::Empty
    if(-not[guid]::TryParseExact($id,'D',[ref]$parsed)-or$id-cne$parsed.ToString('D')){throw 'report_attempt_invalid'}
    Assert-SetupNoReparse $Folder
    $record=[ordered]@{attemptId=$id;reports=[ordered]@{};observations=[ordered]@{};privateDiagnostics=[ordered]@{};serviceDiagnostics=@{status='unavailable_binding'};installationState=@{status='unavailable';code='postboot_receipt_unavailable';rebootVerified=$false;currentHealthVerified=$false;productAdopted=$false}}
    foreach($name in @('result.json','progress.json','host-result.json','prerequisite-result.json','prepare.stdout.log','prepare.stderr.log','initial-backup.stdout.log','prepare.process.json')){
        $observation=Get-SetupJsonDiagnostic (Join-Path $Folder $name) $AllowedSids
        $record.observations[$name]=$observation
        if($observation.status-ceq'parsed'){$record.reports[$name]=$observation.fields}
    }
    try{
        $binding=Read-SetupDiagnosticBinding $id
        if($binding.serviceName-and(Get-Command Get-SetupServiceDiagnostic -ErrorAction SilentlyContinue)){
            try{$record.serviceDiagnostics=Get-SetupServiceDiagnostic $binding.id $binding.serviceSid $binding.serviceName}catch{$record.serviceDiagnostics=@{status='unavailable';failure=(Get-SetupDiagnosticFailure $_)}}
        }
        foreach($name in @('preparation/exception-private.log','preparation/installation-stdout.log','preparation/installation-stderr.log','preparation/profile-stdout.log','preparation/profile-stderr.log','instance/installation-state.json')){
            $privateBytes=$null
            try{
                $privateBytes=Read-SetupPrivateDiagnosticBytes $binding.id $name $binding.serviceSid
                $record.privateDiagnostics[$name]=if($name-ceq'preparation/exception-private.log'){Get-SetupExceptionDiagnostic $privateBytes}else{ConvertTo-SetupJsonObservation $privateBytes}
            }catch{$record.privateDiagnostics[$name]=@{status='unavailable';failure=(Get-SetupDiagnosticFailure $_)}}
            finally{if($null-ne$privateBytes){[Array]::Clear($privateBytes,0,$privateBytes.Length)}}
        }
    }catch{$record.privateDiagnostics.binding=@{status='unavailable';failure=(Get-SetupDiagnosticFailure $_)}}
    # Management paths also remain derived from this exact GUID, never from data.
    $management='C:\ProgramData\RackClick\Instances\'+$id+'\management'
    if([IO.Directory]::Exists($management)){
        try{
            Assert-SetupPath $management 'management';Assert-SetupManagementAcl $management
            $receiptObservation=Get-SetupJsonDiagnostic (Join-Path $management 'server-installation.json') @('S-1-5-18','S-1-5-32-544')
            $record.observations['server-installation.json']=$receiptObservation
            if($receiptObservation.status-ceq'parsed'){$record.reports['server-installation.json']=$receiptObservation.fields}
            $observation=Get-SetupJsonDiagnostic (Join-Path $management 'postboot-verification.json') @('S-1-5-18','S-1-5-32-544')
            $record.observations['postboot-verification.json']=$observation
            if($observation.status-ceq'parsed'){$record.reports['postboot-verification.json']=$observation.fields}
            if($receiptObservation.status-ceq'parsed'-and$receiptObservation.fields.installationId-is[string]-and$receiptObservation.fields.installationId-ceq$id-and$observation.status-cin@('parsed','missing')){
                $verification=$null;if($observation.status-ceq'parsed'){$verification=$observation.fields}
                $boot=(Get-CimInstance Win32_OperatingSystem -ErrorAction Stop).LastBootUpTime.ToUniversalTime().ToString('o')
                $record.installationState=Get-SetupRecordedInstallationState -Receipt $receiptObservation.fields -Verification $verification -CurrentBootUtc $boot -ObservedUtc ([DateTime]::UtcNow.ToString('o'))
                $record.installationState.receiptSha256=$receiptObservation.sha256
                if($observation.status-ceq'parsed'){$record.installationState.verificationSha256=$observation.sha256}
            }
        }catch{$record.observations['postboot-verification.json']=@{status='unavailable';failure=(Get-SetupDiagnosticFailure $_)}}
    }
    return $record
}
