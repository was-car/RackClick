#requires -Version 5.1
<# Demo50 edition03: fixed EN/DE/ES names, source43 to target48 only.
   Optional inventory-only loader. No SQL, account changes or MFA bypass.
   Import functions by dot-sourcing; no action is performed on import.
#>
[CmdletBinding()]
param([string]$Origin='', [string]$PlanPath='', [string]$ExpectedPlanSha256='',
      [string]$Username='', [switch]$DevelopmentLoopbackHttp)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'

function Stop-Demo50([string]$Code) {throw (New-Object InvalidOperationException($Code))}
function Get-Demo50DiagnosticRoute([string]$Route) {
    if($Route-cin@('/health/ready','/api/v1/auth/login','/api/v1/auth/mfa/verify','/api/v1/auth/logout','/api/v1/me','/api/v1/customers','/api/v1/systemhaus')){return $Route}
    if($Route-cmatch'^/api/v1/customers/[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}/(project|commands)$'){return '/api/v1/customers/{customerId}/'+$Matches[1]}
    return 'unknown'
}
function Get-Demo50HttpFailure([string]$Method,[string]$Route,$ErrorRecord) {
    $failure=[ordered]@{method='unknown';route=(Get-Demo50DiagnosticRoute $Route);httpStatus=0;code='unavailable'}
    if($Method-cin@('GET','POST')){$failure.method=$Method}
    $response=$null;$text=$null;$stream=$null
    try{
        if($null-ne$ErrorRecord.Exception.PSObject.Properties['Response']){$response=$ErrorRecord.Exception.Response}
        if($null-ne$response){
            $status=[int]$response.StatusCode
            if($status-ge100-and$status-le599){$failure.httpStatus=$status}
            if($response.ContentLength-le4096){
                $stream=$response.GetResponseStream();$buffer=New-Object byte[] 4097;$length=0
                while($null-ne$stream-and$length-lt$buffer.Length){$read=$stream.Read($buffer,$length,$buffer.Length-$length);if($read-eq0){break};$length+=$read}
                if($length-gt0-and$length-le4096){$utf8=New-Object Text.UTF8Encoding($false,$true);$text=$utf8.GetString($buffer,0,$length)}
            }
        }
    }catch{}finally{try{if($null-ne$stream){$stream.Dispose()}}catch{};try{if($null-ne$response){$response.Close()}}catch{}}
    # PowerShell may have consumed the exception response stream already. Its
    # ErrorDetails is considered only as bounded JSON input, never printed.
    if([string]::IsNullOrEmpty($text)-and$null-ne$ErrorRecord.ErrorDetails){$detail=[string]$ErrorRecord.ErrorDetails.Message;if($detail.Length-le4096){$text=$detail}}
    if(-not[string]::IsNullOrEmpty($text)){
        try{
            $body=$text|ConvertFrom-Json -ErrorAction Stop
            $allowed=@('mfa_code_invalid','mfa_challenge_invalid','mfa_unavailable','mfa_enrollment_required','csrf_invalid','origin_invalid','host_invalid','authentication_required','login_failed','rate_limited','forbidden','not_found','service_unavailable','revision_conflict','request_too_large','content_type_invalid')
            if($body-is[Management.Automation.PSCustomObject]-and$null-ne$body.PSObject.Properties['error']-and$body.error-is[string]-and$body.error-cin$allowed){$failure.code=$body.error}
        }catch{}
    }
    return $failure
}
function Get-Demo50FailureReport([Exception]$Exception) {
    $code='demo_failed_no_retry';if($Exception.Message-cmatch'^demo_[a-z0-9_]+$'){$code=$Exception.Message}
    $report=[ordered]@{schemaVersion=1;success=$false;code=$code;partialDataPreserved=$true;automaticRetry=$false}
    if($Exception.Data.Contains('demoHttpFailure')){$report.httpFailure=$Exception.Data['demoHttpFailure']}
    return $report
}
function Write-Demo50HttpGuidance($Failure) {
    if($Failure.httpStatus-eq401-and$Failure.code-ceq'mfa_code_invalid'){
        Write-Host 'El servidor rechazo el codigo MFA. No distingue aqui entre codigo incorrecto, fuera de ventana o ya usado. No repita la carga: conserve este resultado para revisar; no cambie MFA.'
    }elseif($Failure.code-ceq'csrf_invalid'){
        Write-Host 'El servidor rechazo CSRF. Conserve este resultado y detengase; no cambie cookies, permisos ni controles de seguridad.'
    }elseif($Failure.httpStatus-eq429){
        Write-Host 'El servidor limito los intentos (HTTP429). Conserve este resultado y detengase; no se reintentara automaticamente.'
    }
}
function Assert-Demo50Path([string]$Path) {
    $item=Get-Item -LiteralPath $Path -Force -ErrorAction Stop
    while($null-ne$item){
        if(($item.Attributes-band[IO.FileAttributes]::ReparsePoint)-ne0){Stop-Demo50 'demo_reparse_rejected'}
        $item=if($item-is[IO.FileInfo]){$item.Directory}else{$item.Parent}
    }
}
function Get-Demo50Origin([string]$Value,[bool]$Development) {
    $uri=$null
    if(-not[uri]::TryCreate($Value,[UriKind]::Absolute,[ref]$uri)-or$uri.UserInfo-or$uri.Query-or$uri.Fragment-or$uri.AbsolutePath-ne'/') {Stop-Demo50 'demo_origin_invalid'}
    $local=$uri.Scheme-eq'http'-and$uri.Host-in@('127.0.0.1','localhost','[::1]')
    if($uri.Scheme-ne'https'-and-not($Development-and$local)){Stop-Demo50 'demo_https_required'}
    return $uri.GetLeftPart([UriPartial]::Authority)
}
function Convert-Demo50Value($Value,[hashtable]$Map,[bool]$RequireKnownIds=$false) {
    if($null-eq$Value){return $null}
    if($Value-is[string]){if($Map.ContainsKey($Value)){return $Map[$Value]};if($RequireKnownIds-and$Value-cmatch'^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$'){Stop-Demo50 'demo_unmapped_source_id'};return $Value}
    if($Value-is[Collections.IDictionary]){$copy=[ordered]@{};foreach($key in $Value.Keys){$copy[$key]=Convert-Demo50Value $Value[$key] $Map $RequireKnownIds};return $copy}
    if($Value-is[Management.Automation.PSCustomObject]){$copy=[ordered]@{};foreach($p in $Value.PSObject.Properties){$copy[$p.Name]=Convert-Demo50Value $p.Value $Map $RequireKnownIds};return $copy}
    if($Value-is[Collections.IEnumerable]){$copy=@(foreach($item in $Value){Convert-Demo50Value $item $Map $RequireKnownIds});return ,$copy}
    return $Value
}
function Convert-Demo50Canonical($Value) {
    if($null-eq$Value){return $null}
    if($Value-is[Collections.IDictionary]){$copy=[ordered]@{};foreach($key in @($Value.Keys|Sort-Object)){$copy[$key]=Convert-Demo50Canonical $Value[$key]};return $copy}
    if($Value-is[Management.Automation.PSCustomObject]){$copy=[ordered]@{};foreach($p in @($Value.PSObject.Properties|Sort-Object Name)){$copy[$p.Name]=Convert-Demo50Canonical $p.Value};return $copy}
    if($Value-is[Collections.IEnumerable]-and$Value-isnot[string]){return ,@(foreach($item in $Value){Convert-Demo50Canonical $item})}
    return $Value
}
function Set-Demo50MfaChallengeCookie($Context,$Answer) {
    try{
        $source=[uri]($Context.origin+'/api/v1/auth/login');$actual=$Answer.BaseResponse.ResponseUri
        if($null-eq$actual-or[uri]::Compare($source,$actual,[UriComponents]::AbsoluteUri,[UriFormat]::UriEscaped,[StringComparison]::Ordinal)-ne0){throw 'invalid'}
        if($source.Scheme-ne'https'-and-not($source.Scheme-eq'http'-and$source.IsLoopback)){throw 'invalid'}
        $headers=@($Answer.BaseResponse.Headers.GetValues('Set-Cookie'))
        if($headers.Count-ne1-or$null-eq$headers[0]){throw 'invalid'}
        $raw=[string]$headers[0]
        if($raw.Length-gt1024-or$raw-cmatch'[\x00-\x1f\x7f,]'){throw 'invalid'}
        $parts=$raw.Split(';')
        if($parts[0].Trim()-cnotmatch'^RackClick[.]MfaChallenge=[A-Za-z0-9_-]{40,256}$'){throw 'invalid'}
        $attributes=@{}
        for($i=1;$i-lt$parts.Length;$i++){
            $part=$parts[$i].Trim();$equal=$part.IndexOf('=');$key=$part.ToLowerInvariant();$value=''
            if($equal-ge0){$key=$part.Substring(0,$equal).Trim().ToLowerInvariant();$value=$part.Substring($equal+1).Trim()}
            if($key-cnotin@('path','max-age','secure','httponly','samesite')-or$attributes.ContainsKey($key)){throw 'invalid'}
            if(($key-cin@('secure','httponly'))-and$equal-ge0){throw 'invalid'}
            $attributes[$key]=$value
        }
        if(-not$attributes.ContainsKey('path')-or$attributes.path-cne'/api/v1/auth/mfa'-or-not$attributes.ContainsKey('httponly')-or-not$attributes.ContainsKey('samesite')-or$attributes.samesite-ine'Strict'){throw 'invalid'}
        if($source.Scheme-eq'https'-and-not$attributes.ContainsKey('secure')){throw 'invalid'}
        if($attributes.ContainsKey('max-age')-and($attributes['max-age']-cnotmatch'^[1-9][0-9]{0,2}$'-or[int]$attributes['max-age']-gt300)){throw 'invalid'}
        # Framework rejects this sibling Path at /auth/login. Parse only the
        # validated host-only challenge against its actual target URI, preserving
        # its Path and flags. Do not copy a session or any other response cookie.
        $target=[uri]($Context.origin+'/api/v1/auth/mfa/verify');$cookies=New-Object Net.CookieContainer
        $cookies.SetCookies($target,$raw);$selected=$cookies.GetCookies($target)
        if($selected.Count-ne1-or$selected[0].Name-cne'RackClick.MfaChallenge'-or$selected[0].Path-cne'/api/v1/auth/mfa'-or-not$selected[0].HttpOnly-or($source.Scheme-eq'https'-and-not$selected[0].Secure)){throw 'invalid'}
        $Context.web.Cookies=$cookies
    }catch{
        # Do not retain even an automatically accepted broad/extra cookie after
        # rejecting the response contract. The import stops before verification.
        $Context.web.Cookies=New-Object Net.CookieContainer
        Stop-Demo50 'demo_mfa_challenge_cookie_invalid'
    }
}
function Invoke-Demo50Http($Context,[string]$Method,[string]$Route,$Body=$null,[hashtable]$Headers=@{},[int[]]$Expected=@(200)) {
    $options=@{Uri=($Context.origin+$Route);Method=$Method;WebSession=$Context.web;UseBasicParsing=$true;
               MaximumRedirection=0;TimeoutSec=90;ErrorAction='Stop';Headers=@{Origin=$Context.origin}}
    foreach($key in $Headers.Keys){$options.Headers[$key]=$Headers[$key]}
    if($Method-ne'GET'){$options.Headers['X-RackClick-CSRF']=$Context.csrf}
    if($null-ne$Body){$options.ContentType='application/json; charset=utf-8';$options.Body=[Text.Encoding]::UTF8.GetBytes(($Body|ConvertTo-Json -Depth 60 -Compress))}
    try{$answer=Invoke-WebRequest @options}catch{
        $failure=New-Object InvalidOperationException('demo_http_rejected_or_uncertain_no_retry')
        $failure.Data['demoHttpFailure']=Get-Demo50HttpFailure $Method $Route $_
        throw $failure
    }
    if([int]$answer.StatusCode-notin$Expected){Stop-Demo50 'demo_http_contract_invalid'}
    if([int]$answer.StatusCode-eq204){return [pscustomobject]@{status=204;data=$null}}
    # Some existing JSON endpoints omit charset. Windows PowerShell5.1 then
    # decodes Content as ISO-8859-1; JSON wire bytes are UTF-8. Decode those bytes
    # explicitly so customer names/notes are neither mistranslated nor corrupted.
    try{$utf8=New-Object Text.UTF8Encoding($false,$true);$text=$utf8.GetString($answer.RawContentStream.ToArray());$data=$text|ConvertFrom-Json -ErrorAction Stop}catch{Stop-Demo50 'demo_http_json_invalid'}
    if($Method-ceq'POST'-and$Route-ceq'/api/v1/auth/login'-and[int]$answer.StatusCode-eq202){Set-Demo50MfaChallengeCookie $Context $answer}
    return [pscustomobject]@{status=[int]$answer.StatusCode;data=$data}
}
function Add-Demo50Map([hashtable]$Map,[string]$Old,[string]$New) {
    $id=[guid]::Empty
    if(-not[guid]::TryParseExact($Old,'D',[ref]$id)-or-not[guid]::TryParseExact($New,'D',[ref]$id)){Stop-Demo50 'demo_resource_id_invalid'}
    if($Map.ContainsKey($Old)-and$Map[$Old]-cne$New){Stop-Demo50 'demo_resource_map_conflict'}
    $Map[$Old]=$New
}
function Assert-Demo50Project($Project,$Expected,[hashtable]$Map) {
    foreach($collection in @('sites','buildings','rooms','racks','devices','portGroups','ports','connections')){
        $actual=@($Project.$collection);$expectedRows=@($Expected.$collection)
        if($actual.Count-ne$expectedRows.Count){Stop-Demo50 ('demo_count_mismatch_'+$collection)}
        $byId=@{};foreach($row in $actual){if($byId.ContainsKey($row.id)){Stop-Demo50 'demo_duplicate_resource'};$byId[$row.id]=$row}
        foreach($row in $expectedRows){
            if(-not$Map.ContainsKey($row.id)-or-not$byId.ContainsKey($Map[$row.id])){Stop-Demo50 'demo_resource_mapping_missing'}
            $left=Convert-Demo50Value $row $Map;$right=Convert-Demo50Value $byId[$Map[$row.id]] @{}
            if($collection-eq'connections'){$right.Remove('createdAt')}
            $leftText=Convert-Demo50Canonical $left|ConvertTo-Json -Depth 60 -Compress
            $rightText=Convert-Demo50Canonical $right|ConvertTo-Json -Depth 60 -Compress
            # Group and port identity includes deviceId/groupId/type/gn and sealed
            # hardware metadata. A positional createdIds assumption cannot pass
            # this final complete comparison if the server changes its ordering.
            if($leftText-cne$rightText){Stop-Demo50 ('demo_content_mismatch_'+$collection)}
        }
    }
}
function Read-Demo50Plan([string]$Path,[string]$Expected) {
    # This is one reviewed synthetic dataset, not a generic importer. A locally
    # rehashed different plan is not enough to authorize another dataset.
    if($Expected-cne'44f7fca5dd78b10de1a5efbb51f34cff488974ed264bfcf9ea72059b1194216d'){Stop-Demo50 'demo_plan_reference_required'}
    Assert-Demo50Path $Path
    $lock=[IO.File]::Open($Path,'Open','Read','Read')
    try{
        if($lock.Length-gt16777216-or$lock.Length-lt1000){Stop-Demo50 'demo_plan_size_invalid'}
        $hash=[Security.Cryptography.SHA256]::Create()
        try{$digest=([BitConverter]::ToString($hash.ComputeHash($lock))).Replace('-','').ToLowerInvariant()}finally{$hash.Dispose()}
        if($digest-cne$Expected){Stop-Demo50 'demo_plan_hash_mismatch'}
        $lock.Position=0;$reader=New-Object IO.StreamReader($lock,[Text.Encoding]::UTF8,$true,4096,$true)
        try{$plan=$reader.ReadToEnd()|ConvertFrom-Json -ErrorAction Stop}finally{$reader.Dispose()}
        if((($plan.PSObject.Properties.Name|Sort-Object)-join',')-cne'counts,customers,format,productionDefault,schemaVersion,securityIncluded'-or
            $plan.format-cne'RackClickDemo50Replay-v1'-or$plan.schemaVersion-ne43-or$plan.securityIncluded-isnot[bool]-or$plan.securityIncluded-or$plan.productionDefault-isnot[bool]-or$plan.productionDefault-or@($plan.customers).Count-ne50){Stop-Demo50 'demo_plan_contract_invalid'}
        $allowed=@('site.create','building.create','room.create','rack.create','rack.createHardware','device.create','device.createHardware','connections.createBatch','ports.update','device.update')
        $number=0
        foreach($customer in $plan.customers){
            $number++;if($customer.key-cne('c{0:00}'-f$number)-or(($customer.PSObject.Properties.Name|Sort-Object)-join',')-cne'commands,expected,key,name,sourceCustomerId'){Stop-Demo50 'demo_customer_contract_invalid'}
            foreach($command in $customer.commands){if($command.type-cnotin$allowed-or(($command.PSObject.Properties.Name|Sort-Object)-join',')-cne'payload,sourceCreatedIds,sourceResourceId,type'){Stop-Demo50 'demo_command_contract_invalid'}}
        }
        return $plan
    }finally{$lock.Dispose()}
}
function Invoke-Demo50Import {
    param([string]$Origin,[string]$PlanPath,[string]$ExpectedPlanSha256,[pscredential]$Credential,
          [bool]$DevelopmentLoopbackHttp=$false,[string]$Confirmation='')
    $originValue=Get-Demo50Origin $Origin $DevelopmentLoopbackHttp
    $plan=Read-Demo50Plan $PlanPath $ExpectedPlanSha256
    $context=@{origin=$originValue;web=(New-Object Microsoft.PowerShell.Commands.WebRequestSession);csrf='';actor=''}
    $health=(Invoke-Demo50Http $context GET '/health/ready').data
    if($health.status-cne'ready'-or$health.schemaVersion-isnot[int]-or$health.schemaVersion-ne48){Stop-Demo50 'demo_schema48_required'}
    $created=0;$commandsApplied=0;$counts=@{sites=0;buildings=0;rooms=0;racks=0;devices=0;portGroups=0;ports=0;connections=0}
    try{
    $native=[IntPtr]::Zero;$password=$null
    try{
        $native=[Runtime.InteropServices.Marshal]::SecureStringToBSTR($Credential.Password)
        $password=[Runtime.InteropServices.Marshal]::PtrToStringBSTR($native)
        $auth=Invoke-Demo50Http $context POST '/api/v1/auth/login' @{username=$Credential.UserName;password=$password} @{} @(200,202)
    }finally{$password=$null;if($native-ne[IntPtr]::Zero){[Runtime.InteropServices.Marshal]::ZeroFreeBSTR($native)}}
    if($auth.status-eq202){
        if($auth.data.purpose-cne'verify'){Stop-Demo50 'demo_finish_enrollment_in_browser_first'}
        $context.csrf=$auth.data.csrf;$codeSecret=Read-Host 'Codigo TOTP de seis cifras (no se muestra)' -AsSecureString
        $codePointer=[IntPtr]::Zero;$code=$null
        try{
            $codePointer=[Runtime.InteropServices.Marshal]::SecureStringToBSTR($codeSecret)
            $code=[Runtime.InteropServices.Marshal]::PtrToStringBSTR($codePointer)
            if($code-cnotmatch'^[0-9]{6}$'){Stop-Demo50 'demo_totp_invalid'}
            $auth=Invoke-Demo50Http $context POST '/api/v1/auth/mfa/verify' @{code=$code}
        }finally{$code=$null;if($codePointer-ne[IntPtr]::Zero){[Runtime.InteropServices.Marshal]::ZeroFreeBSTR($codePointer)};$codeSecret.Dispose()}
    }
    $context.csrf=$auth.data.csrf;$me=(Invoke-Demo50Http $context GET '/api/v1/me').data
    $context.actor=$me.user.id;$context.csrf=$me.csrf
    foreach($capability in @('systemhaus.manage','security.manage','customer.manage','inventory.read','inventory.edit')){
        if($capability-cnotin$me.permissions.systemhausCapabilities){Stop-Demo50 'demo_global_administrator_required'}
    }
    $customers=@((Invoke-Demo50Http $context GET '/api/v1/customers').data)
    if($customers.Count-ne0){Stop-Demo50 'demo_empty_installation_required'}
    if($Confirmation-ceq''){$Confirmation=Read-Host 'Escriba exactamente CARGAR 50 CLIENTES SINTETICOS'}
    if($Confirmation-cne'CARGAR 50 CLIENTES SINTETICOS'){Stop-Demo50 'demo_confirmation_rejected'}
        foreach($customer in $plan.customers){
            $house=(Invoke-Demo50Http $context GET '/api/v1/systemhaus').data
            $headers=@{'X-RackClick-Actor'=$context.actor;'If-Match'=('"'+$house.revision+'"');'Idempotency-Key'=[guid]::NewGuid().ToString('D')}
            $new=(Invoke-Demo50Http $context POST '/api/v1/customers' @{name=$customer.name} $headers @(201)).data
            $cid=$new.resource.id;$created++;$map=@{};Add-Demo50Map $map $customer.sourceCustomerId $cid
            $route='/api/v1/customers/'+$cid;$revision=(Invoke-Demo50Http $context GET ($route+'/project')).data.revision
            foreach($command in $customer.commands){
                $payload=Convert-Demo50Value $command.payload $map $true
                $headers=@{'X-RackClick-Actor'=$context.actor;'If-Match'=('"'+$revision+'"');'Idempotency-Key'=[guid]::NewGuid().ToString('D')}
                $answer=(Invoke-Demo50Http $context POST ($route+'/commands') @{type=$command.type;payload=$payload} $headers).data
                $revision=$answer.revision;$commandsApplied++;Add-Demo50Map $map $command.sourceResourceId $answer.result.resourceId
                $source=@($command.sourceCreatedIds)
                if($source.Count-ne0){
                    $target=@($answer.result.createdIds)
                    if($source.Count-ne$target.Count){Stop-Demo50 'demo_created_resource_count_invalid'}
                    for($i=0;$i-lt$source.Count;$i++){Add-Demo50Map $map $source[$i] $target[$i]}
                }
            }
            $project=(Invoke-Demo50Http $context GET ($route+'/project')).data
            Assert-Demo50Project $project $customer.expected $map
            foreach($key in @($counts.Keys)){$counts[$key]+=@($project.$key).Count}
            Write-Host ('Cliente '+$customer.key+' verificado ('+$created+'/50).')
        }
        foreach($key in @($counts.Keys)){if($counts[$key]-ne$plan.counts.$key){Stop-Demo50 'demo_final_counts_invalid'}}
        return [ordered]@{schemaVersion=1;success=$true;code='demo50_loaded_verified';customers=$created;commands=$commandsApplied;counts=$counts;securityImported=$false;globalTransaction=$false}
    }catch{
        Write-Host ('Detenido. Clientes creados: '+$created+'. Comandos confirmados: '+$commandsApplied+'. Se conservan los datos parciales. No repetir ni borrar; conserve este resultado.')
        throw
    }finally{
        try{$null=Invoke-Demo50Http $context POST '/api/v1/auth/logout' $null @{} @(204)}catch{}
        $context.csrf='';$context.actor='';$context.web=$null
    }
}
if($MyInvocation.InvocationName-eq'.'){return}
try{
    if(-not$Origin){$Origin=Read-Host 'URL HTTPS de esta instalacion nueva y vacia'}
    if(-not$Username){$Username=Read-Host 'Usuario administrador global de RackClick'}
    $secret=Read-Host 'Contrasena de RackClick (no se muestra)' -AsSecureString
    try{$credential=New-Object Management.Automation.PSCredential($Username,$secret);$result=Invoke-Demo50Import -Origin $Origin -PlanPath $PlanPath -ExpectedPlanSha256 $ExpectedPlanSha256 -Credential $credential -DevelopmentLoopbackHttp ([bool]$DevelopmentLoopbackHttp)}finally{$secret.Dispose()}
    $result|ConvertTo-Json -Depth 10 -Compress;exit 0
}catch{
    $report=Get-Demo50FailureReport $_.Exception
    if($report.Contains('httpFailure')){Write-Demo50HttpGuidance $report.httpFailure}
    $report|ConvertTo-Json -Depth 5 -Compress;exit 1
}
