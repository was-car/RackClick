#requires -Version 5.1
# Read-only snapshots. Import never queries CIM, events, services or private files.
function Get-SetupServiceDiagnosticAccountFormat([string]$Account) {
    if([string]::IsNullOrWhiteSpace($Account)){return 'empty'}
    if($Account-match'^S-1-'){return 'sid'}
    if($Account.StartsWith('.\',[StringComparison]::Ordinal)){return 'local_dot'}
    if($Account.Contains('\')){return 'qualified'}
    if($Account.Contains('@')){return 'upn'}
    return 'plain'
}
function Resolve-SetupServiceDiagnosticAccountSid([string]$Account) {
    # Keep diagnostic collection independent of lifecycle/registration helpers.
    # Never propagate an identity-translation message containing the account name.
    $accountNameForm=Get-SetupServiceDiagnosticAccountFormat $Account
    try {
        if($accountNameForm-ceq'empty'){throw (New-Object ArgumentException('report_service_account_unresolved'))}
        if($Account-match'^S-1-'){return (New-Object Security.Principal.SecurityIdentifier($Account)).Value}
        # SCM can describe a local service identity with .\ instead of MACHINE\.
        # Normalize only this literal local prefix; preserve explicit domains/UPNs.
        if($accountNameForm-ceq'local_dot'){$Account=[Environment]::MachineName+'\'+$Account.Substring(2)}
        return (New-Object Security.Principal.NTAccount($Account)).Translate([Security.Principal.SecurityIdentifier]).Value
    }catch{
        $cause=$_.Exception
        for($i=0;$i-lt8-and$null-ne$cause.InnerException;$i++){$cause=$cause.InnerException}
        $accountErrorType='unresolved'
        if($cause-is[Security.Principal.IdentityNotMappedException]){$accountErrorType='System.Security.Principal.IdentityNotMappedException'}
        elseif($cause-is[ArgumentException]){$accountErrorType='System.ArgumentException'}
        elseif($cause-is[Security.SecurityException]-or$cause-is[UnauthorizedAccessException]){$accountErrorType='System.Security.SecurityException'}
        $failure=New-Object InvalidOperationException('report_service_account_unresolved')
        $failure.Data['accountNameForm']=$accountNameForm
        $failure.Data['accountErrorType']=$accountErrorType
        $failure.Data['accountErrorHResult']=[int]$cause.HResult
        throw $failure
    }
}
function ConvertTo-SetupServiceEventSummary([string]$Xml,[string]$ServiceName,[string]$InstanceId) {
    if($Xml.Length-gt65536){return $null}
    $reader=$null
    try {
        $settings=New-Object Xml.XmlReaderSettings
        $settings.DtdProcessing=[Xml.DtdProcessing]::Prohibit;$settings.XmlResolver=$null;$settings.MaxCharactersInDocument=65536
        $reader=[Xml.XmlReader]::Create((New-Object IO.StringReader($Xml)),$settings)
        $doc=New-Object Xml.XmlDocument;$doc.XmlResolver=$null;$doc.Load($reader)
        $sys=$doc.SelectSingleNode("/*[local-name()='Event']/*[local-name()='System']")
        if($null-eq$sys){return $null}
        $provider=$sys.SelectSingleNode("*[local-name()='Provider']/@Name").Value
        if($provider-cnotin@('Service Control Manager','.NET Runtime','Application Error')){return $null}
        $nodes=@($doc.SelectNodes("/*[local-name()='Event']/*[local-name()='EventData']/*[local-name()='Data']"))
        $data=@($nodes|ForEach-Object {$_.InnerText})
        $correlated=$false;$correlation='service_name'
        if($provider-ceq'Service Control Manager'){
            $correlated=@($data|Where-Object {$_-ceq$ServiceName-or$_-ceq('RackClick '+$InstanceId)}).Count-gt0
        }else{
            $correlated=@($data|Where-Object {$_-cmatch'\bRackClick\.WindowsService(?:\.dll|\.exe)?\b'}).Count-gt0
            $correlation='host_executable_not_instance_specific'
        }
        if(-not$correlated){return $null}
        $eventId=0;$recordId=[long]0;$stamp=[DateTime]::MinValue
        if(-not[int]::TryParse($sys.SelectSingleNode("*[local-name()='EventID']").InnerText,[ref]$eventId)-or$eventId-lt1-or$eventId-gt99999){return $null}
        $safe=[ordered]@{provider=$provider;eventId=$eventId;correlation=$correlation;errorCodes=@();exceptionTypes=@()}
        $record=$sys.SelectSingleNode("*[local-name()='EventRecordID']")
        if($null-ne$record-and[long]::TryParse($record.InnerText,[ref]$recordId)-and$recordId-ge0){$safe.recordId=$recordId}
        $time=$sys.SelectSingleNode("*[local-name()='TimeCreated']/@SystemTime")
        if($null-ne$time-and[DateTime]::TryParse($time.Value,[Globalization.CultureInfo]::InvariantCulture,[Globalization.DateTimeStyles]::RoundtripKind,[ref]$stamp)){$safe.timeUtc=$stamp.ToUniversalTime().ToString('o')}
        foreach($value in $data){
            if($value-cmatch'^%%([0-9]{1,10})$'){
                $number=[long]0
                if([long]::TryParse($Matches[1],[ref]$number)-and$number-le4294967295-and$safe.errorCodes.Count-lt8-and$number-notin$safe.errorCodes){$safe.errorCodes+=@($number)}
            }
            foreach($match in [regex]::Matches($value,'\bSystem\.[A-Za-z0-9_.]{1,120}Exception\b')){
                if($safe.exceptionTypes.Count-lt5-and$match.Value-cnotin$safe.exceptionTypes){$safe.exceptionTypes+=@($match.Value)}
            }
        }
        return [pscustomobject]$safe
    }catch{return $null}finally{if($null-ne$reader){$reader.Dispose()}}
}
function Get-SetupServiceEventDiagnostic([string]$ServiceName,[string]$InstanceId) {
    $result=[ordered]@{status='collected';windowHours=48;events=@();sources=[ordered]@{}}
    foreach($source in @(
        @{name='system';filter=@{LogName='System';ProviderName='Service Control Manager';Id=@(7000,7001,7009,7011,7023,7024,7031,7034,7036,7038,7040);StartTime=(Get-Date).AddHours(-48)};max=128},
        @{name='application';filter=@{LogName='Application';ProviderName=@('.NET Runtime','Application Error');Id=@(1000,1026);StartTime=(Get-Date).AddHours(-48)};max=64}
    )){
        try{
            $events=@(Get-WinEvent -FilterHashtable $source.filter -MaxEvents $source.max -ErrorAction Stop)
            $result.sources[$source.name]=@{status='read';scanned=$events.Count;limit=$source.max}
            foreach($event in $events){
                try{$summary=ConvertTo-SetupServiceEventSummary $event.ToXml() $ServiceName $InstanceId;if($null-ne$summary){$result.events+=@($summary)}}finally{$event.Dispose()}
            }
        }catch{
            if($_.FullyQualifiedErrorId-like'NoMatchingEventsFound*'){$result.sources[$source.name]=@{status='empty';scanned=0;limit=$source.max}}
            else{$result.sources[$source.name]=@{status='unavailable';errorType=$_.Exception.GetType().FullName}}
        }
    }
    return $result
}
function Get-SetupServiceDiagnostic([string]$InstanceId,[string]$ServiceSid,[string]$ServiceName) {
    $id=[guid]::Empty
    if(-not[guid]::TryParseExact($InstanceId,'D',[ref]$id)-or$id.ToString('D')-cne$InstanceId-or$ServiceSid-cnotmatch'^S-1-5-21-(\d+-){3}\d+$'-or$ServiceSid.EndsWith('-500')-or$ServiceName-cnotmatch'^RackClick(?:-Recovery-[a-f0-9]{8,32})?$'){throw 'report_service_binding_invalid'}
    $report=[ordered]@{status='collected';measuredUtc=[DateTime]::UtcNow.ToString('o');instanceId=$InstanceId;service=[ordered]@{status='unavailable'};boot=[ordered]@{status='unavailable'};events=[ordered]@{};private=[ordered]@{};servicesChanged=0;databasesChanged=0}
    try{
        $items=@(Get-CimInstance Win32_Service -Filter ("Name='"+$ServiceName+"'") -ErrorAction Stop)
        if($items.Count-eq0){$report.service=@{status='not_found'}}
        elseif($items.Count-eq1){
            $item=$items[0];$safe=[ordered]@{status='found'}
            foreach($pair in @(@('State','state'),@('StartMode','startMode'))){
                $value=[string]$item.($pair[0])
                if($value-cin@('Stopped','Start Pending','Stop Pending','Running','Continue Pending','Pause Pending','Paused','Unknown','Auto','Manual','Disabled','Boot','System')){$safe[$pair[1]]=$value}
            }
            foreach($pair in @(@('ExitCode','win32ExitCode'),@('ServiceSpecificExitCode','serviceSpecificExitCode'),@('ProcessId','processId'))){
                $property=$item.PSObject.Properties[$pair[0]]
                if($null-ne$property-and($property.Value-is[uint32]-or$property.Value-is[int]-or$property.Value-is[long])-and$property.Value-ge0-and$property.Value-le4294967295){$safe[$pair[1]]=[long]$property.Value}
            }
            $start=$item.PSObject.Properties['StartName']
            if($null-ne$start){try{$safe.accountSidMatches=(Resolve-SetupServiceDiagnosticAccountSid ([string]$start.Value))-ceq$ServiceSid}catch{$safe.accountSidStatus='unverified'}}
            $path=$item.PSObject.Properties['PathName']
            if($null-ne$path){
                $instance='C:\ProgramData\RackClick\Instances\'+$InstanceId+'\instance';$codeRoot='C:\Program Files\RackClick\'+$InstanceId
                $expected=(ConvertTo-SetupArgument ($instance+'\content\dependencies\dotnet\dotnet.exe'))+' '+(ConvertTo-SetupArgument ($codeRoot+'\service\RackClick.WindowsService.dll'))+' --config '+(ConvertTo-SetupArgument ($instance+'\service-config.json'))
                $safe.executableBindingMatches=([string]$path.Value)-ceq$expected
            }
            $report.service=$safe
        }else{$report.service=@{status='ambiguous'}}
    }catch{$report.service=@{status='unavailable';errorType=$_.Exception.GetType().FullName}}
    try{
        $boot=(Get-CimInstance Win32_OperatingSystem -ErrorAction Stop).LastBootUpTime
        if($boot-is[DateTime]){$report.boot=@{status='read';lastBootUtc=$boot.ToUniversalTime().ToString('o')}}
    }catch{$report.boot=@{status='unavailable';errorType=$_.Exception.GetType().FullName}}
    $report.events=Get-SetupServiceEventDiagnostic $ServiceName $InstanceId
    try{$report.private=Get-SetupServicePrivateDiagnostic $InstanceId $ServiceSid}catch{$report.private=@{status='unavailable';errorType=$_.Exception.GetType().FullName}}
    return $report
}
