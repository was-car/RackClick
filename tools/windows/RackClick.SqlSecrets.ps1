#requires -Version 5.1
# SQL operator formats. Import does not touch files, credentials, services or environment.
function Stop-SqlOperator([string]$Code) {
    $errorSql=New-Object InvalidOperationException($Code)
    $errorSql.Data['code']=$Code;$errorSql.Data['exitCode']=2
    throw $errorSql
}
function ConvertTo-SqlOperatorMap($Value) {
    $map=@{}
    if($Value -is [Collections.IDictionary]) {
        foreach($key in $Value.Keys){if($key-isnot[string]-or$map.ContainsKey($key)){Stop-SqlOperator 'sql_operator_profile_invalid'};$map[$key]=$Value[$key]}
    }elseif($Value-is[pscustomobject]){
        foreach($property in $Value.PSObject.Properties){if($map.ContainsKey($property.Name)){Stop-SqlOperator 'sql_operator_profile_invalid'};$map[$property.Name]=$property.Value}
    }else{Stop-SqlOperator 'sql_operator_profile_invalid'}
    return $map
}
function Assert-SqlOperatorKeys($Map,[string]$Keys) {
    if((($Map.Keys|Sort-Object)-join',')-cne$Keys){Stop-SqlOperator 'sql_operator_profile_invalid'}
}
function Assert-SqlOperatorIdentity($InstallationId,$Database,$User) {
    $id=[guid]::Empty
    if($InstallationId-isnot[string]-or-not[guid]::TryParseExact($InstallationId,'D',[ref]$id)-or$id-eq[guid]::Empty-or$InstallationId-cne$id.ToString('D')-or
       $Database-isnot[string]-or$Database-cnotmatch'^[a-z][a-z0-9_]{0,62}$'-or$User-isnot[string]-or$User-cnotmatch'^[a-z][a-z0-9_]{0,62}$'){Stop-SqlOperator 'sql_operator_identity_invalid'}
}
function Get-SqlBackupContext($Profile) {
    $p=ConvertTo-SqlOperatorMap $Profile
    Assert-SqlOperatorKeys $p 'database,host,installationId,passwordFile,port,schemaVersion,user'
    Assert-SqlOperatorIdentity $p.installationId $p.database $p.user
    if($p.schemaVersion-isnot[int]-or$p.schemaVersion-ne2-or$p.host-cne'127.0.0.1'-or$p.port-isnot[int]-or$p.port-lt1024-or$p.port-gt65535-or$p.passwordFile-isnot[string]){Stop-SqlOperator 'sql_operator_profile_invalid'}
    $sid=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value
    # Purpose and all connection metadata are authenticated via DPAPI entropy.
    return 'RackClick/SQL/backup/v1'+"`n"+$p.installationId+"`n"+$sid+"`n"+$p.host+"`n"+$p.port+"`n"+$p.database+"`n"+$p.user
}
function Protect-SqlBackupPassword([string]$Password,$Profile) {
    $context=Get-SqlBackupContext $Profile
    if($Password.Length-lt1-or$Password.Length-gt1024-or$Password.IndexOfAny([char[]]"`r`n`0")-ge0){Stop-SqlOperator 'sql_operator_password_invalid'}
    Add-Type -AssemblyName System.Security
    $utf8=New-Object Text.UTF8Encoding($false,$true);$plain=$null
    try{
        $plain=$utf8.GetBytes($Password)
        $cipher=[Security.Cryptography.ProtectedData]::Protect($plain,$utf8.GetBytes($context),[Security.Cryptography.DataProtectionScope]::CurrentUser)
        return @{schemaVersion=1;kind='RackClickSqlBackupSecret';protection='DPAPI-CurrentUser';ciphertext=[Convert]::ToBase64String($cipher)}
    }catch{Stop-SqlOperator 'sql_operator_protection_failed'}finally{if($null-ne$plain){[Array]::Clear($plain,0,$plain.Length)}}
}
function Unprotect-SqlBackupPassword($Record,$Profile) {
    $context=Get-SqlBackupContext $Profile;$r=ConvertTo-SqlOperatorMap $Record
    Assert-SqlOperatorKeys $r 'ciphertext,kind,protection,schemaVersion'
    if($r.schemaVersion-isnot[int]-or$r.schemaVersion-ne1-or$r.kind-cne'RackClickSqlBackupSecret'-or$r.protection-cne'DPAPI-CurrentUser'-or
       $r.ciphertext-isnot[string]-or$r.ciphertext.Length-lt1-or$r.ciphertext.Length-gt16384){Stop-SqlOperator 'sql_operator_secret_invalid'}
    Add-Type -AssemblyName System.Security
    $plain=$null;$utf8=New-Object Text.UTF8Encoding($false,$true)
    try{
        $plain=[Security.Cryptography.ProtectedData]::Unprotect([Convert]::FromBase64String($r.ciphertext),$utf8.GetBytes($context),[Security.Cryptography.DataProtectionScope]::CurrentUser)
        if($plain.Length-lt1-or$plain.Length-gt4096){Stop-SqlOperator 'sql_operator_secret_invalid'}
        $password=$utf8.GetString($plain)
        if($password.Length-lt1-or$password.Length-gt1024-or$password.IndexOfAny([char[]]"`r`n`0")-ge0){Stop-SqlOperator 'sql_operator_secret_invalid'}
        return $password
    }catch{Stop-SqlOperator 'sql_operator_unprotect_failed'}finally{if($null-ne$plain){[Array]::Clear($plain,0,$plain.Length)}}
}
function New-SqlProtectedBackupProfile {
    param([string]$DestinationPath,[string]$InstallationId,[int]$Port,[string]$Database,[string]$User,[string]$Password)
    # Existing exclusive private-folder helper; never adopt an existing destination.
    Assert-SqlOperatorIdentity $InstallationId $Database $User
    $path=Assert-BackupPath $DestinationPath
    $profile=[ordered]@{schemaVersion=2;installationId=$InstallationId;host='127.0.0.1';port=$Port;database=$Database;user=$User;passwordFile=(Join-Path $path 'password.dpapi.json')}
    $record=Protect-SqlBackupPassword $Password $profile
    $null=New-BackupPrivateDirectory $path
    # Only ciphertext and non-secret metadata are persisted. Failures preserve this new folder.
    Write-BackupNewText $profile.passwordFile ($record|ConvertTo-Json -Compress)
    $profilePath=Join-Path $path 'backup-profile.json'
    Write-BackupNewText $profilePath ($profile|ConvertTo-Json -Compress)
    return $profilePath
}
function Get-SqlRuntimeDefinition($Value,[string]$InstanceRoot,[string]$InstallationId,[string]$Database,[string]$RuntimeUser) {
    $v=ConvertTo-SqlOperatorMap $Value
    Assert-SqlOperatorKeys $v 'ciphertextSha256,schemaVersion,sqlSecret'
    $s=ConvertTo-SqlOperatorMap $v.sqlSecret
    Assert-SqlOperatorKeys $s 'database,enabled,installationId,instancesRoot,runtimeUser'
    Assert-SqlOperatorIdentity $InstallationId $Database $RuntimeUser
    $root=Join-Path $InstanceRoot 'sql-security'
    if($v.schemaVersion-isnot[int]-or$v.schemaVersion-ne2-or$v.ciphertextSha256-isnot[string]-or$v.ciphertextSha256-cnotmatch'^[a-f0-9]{64}$'-or
       $s.enabled-isnot[bool]-or-not$s.enabled-or$s.installationId-cne$InstallationId-or$s.database-cne$Database-or$s.runtimeUser-cne$RuntimeUser-or
       $s.instancesRoot-isnot[string]-or-not[StringComparer]::OrdinalIgnoreCase.Equals($s.instancesRoot,$root)){Stop-SqlOperator 'sql_operator_runtime_invalid'}
    return @{enabled=$true;instancesRoot=$root;installationId=$InstallationId;database=$Database;runtimeUser=$RuntimeUser;ciphertextSha256=$v.ciphertextSha256;file=(Join-Path $root ($InstallationId+'\sql-secrets\runtime.bin'))}
}
function Protect-SqlRuntimeConnection([string]$Connection,[string]$InstallationId,[string]$ReaderSid,[string]$Database,[string]$RuntimeUser) {
    Assert-SqlOperatorIdentity $InstallationId $Database $RuntimeUser
    $plain=$null;$builder=$null
    try{
        $sid=New-Object Security.Principal.SecurityIdentifier($ReaderSid)
        if($sid.Value-cne$ReaderSid-or$Connection.Length-lt1-or$Connection.Length-gt8192){throw 'invalid'}
        $builder=New-Object Data.Common.DbConnectionStringBuilder;$builder.set_ConnectionString($Connection)
        if([string]$builder['Database']-cne$Database-or[string]$builder['Username']-cne$RuntimeUser-or
           -not$builder.ContainsKey('Password')-or[string]::IsNullOrEmpty([string]$builder['Password'])-or$builder.ContainsKey('Passfile')){throw 'invalid'}
        $utf8=New-Object Text.UTF8Encoding($false,$true);$plain=$utf8.GetBytes($Connection)
        if($plain.Length-gt8192){throw 'invalid'}
        Add-Type -AssemblyName System.Security
        $entropy=$utf8.GetBytes('RackClick/SQL/runtime/v1'+"`n"+$InstallationId+"`n"+$ReaderSid+"`n"+$Database+"`n"+$RuntimeUser)
        $cipher=[Security.Cryptography.ProtectedData]::Protect($plain,$entropy,[Security.Cryptography.DataProtectionScope]::LocalMachine)
        return ,([byte[]]([Text.Encoding]::ASCII.GetBytes('RCSQL001')+$cipher))
    }catch{Stop-SqlOperator 'sql_operator_protection_failed'}finally{if($null-ne$plain){[Array]::Clear($plain,0,$plain.Length)};if($null-ne$builder){$builder.Clear()}}
}
function New-SqlProtectedRuntimeStore {
    param([string]$InstanceRoot,[string]$InstallationId,[string]$ReaderSid,[string]$Database,[string]$RuntimeUser,[string]$Connection)
    $root=Assert-BackupPath $InstanceRoot;Assert-BackupPrivateAcl $root
    $bytes=Protect-SqlRuntimeConnection $Connection $InstallationId $ReaderSid $Database $RuntimeUser
    # A new tree only, with private ACLs from creation. Elevated setup must later
    # assign SYSTEM ownership and read-only rights to the service, before activation.
    $security=Join-Path $root 'sql-security';$null=New-BackupPrivateDirectory $security
    $installation=Join-Path $security $InstallationId;$null=New-BackupPrivateDirectory $installation
    $folder=Join-Path $installation 'sql-secrets';$null=New-BackupPrivateDirectory $folder
    $file=Join-Path $folder 'runtime.bin'
    $stream=New-Object IO.FileStream($file,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
    try{$stream.Write($bytes,0,$bytes.Length);$stream.Flush($true)}finally{$stream.Dispose()}
    $sha=[Security.Cryptography.SHA256]::Create()
    try{$digest=([BitConverter]::ToString($sha.ComputeHash($bytes))).Replace('-','').ToLowerInvariant()}finally{$sha.Dispose()}
    return @{schemaVersion=2;ciphertextSha256=$digest;sqlSecret=@{enabled=$true;instancesRoot=$security;installationId=$InstallationId;database=$Database;runtimeUser=$RuntimeUser}}
}
function Unprotect-SqlRuntimeConnection([byte[]]$Bytes,[string]$InstallationId,[string]$ReaderSid,[string]$Database,[string]$RuntimeUser) {
    Assert-SqlOperatorIdentity $InstallationId $Database $RuntimeUser
    $plain=$null
    try{
        $sid=New-Object Security.Principal.SecurityIdentifier($ReaderSid)
        if($sid.Value-cne$ReaderSid-or$Bytes.Length-le8-or$Bytes.Length-gt65536-or[Text.Encoding]::ASCII.GetString($Bytes,0,8)-cne'RCSQL001'){throw 'invalid'}
        $utf8=New-Object Text.UTF8Encoding($false,$true)
        $entropy=$utf8.GetBytes('RackClick/SQL/runtime/v1'+"`n"+$InstallationId+"`n"+$ReaderSid+"`n"+$Database+"`n"+$RuntimeUser)
        $cipher=New-Object byte[] ($Bytes.Length-8);[Array]::Copy($Bytes,8,$cipher,0,$cipher.Length)
        Add-Type -AssemblyName System.Security
        $plain=[Security.Cryptography.ProtectedData]::Unprotect($cipher,$entropy,[Security.Cryptography.DataProtectionScope]::LocalMachine)
        if($plain.Length-gt8192){throw 'invalid'}
        return $utf8.GetString($plain)
    }catch{Stop-SqlOperator 'sql_operator_unprotect_failed'}finally{if($null-ne$plain){[Array]::Clear($plain,0,$plain.Length)}}
}
function Test-SqlRuntimeVariableName([string]$Name) {
    # .NET 10 EnvironmentVariablesConfigurationProvider maps these prefixes to
    # ConnectionStrings too; clear them even if the launcher did not capture them.
    return $Name-match'^(?i:(?:SqlSecret|ConnectionStrings)(?::|__|$)|(?:MYSQL|SQLAZURE|SQL|CUSTOM|POSTGRESQL|APIHUB|DOCDB|EVENTHUB|NOTIFICATIONHUB|REDISCACHE|SERVICEBUS)CONNSTR_)'
}
function Set-SqlRuntimeEnvironment([hashtable]$Environment,$Definition,[string]$LegacyConnection='') {
    foreach($name in @([Environment]::GetEnvironmentVariables().Keys)){
        if(Test-SqlRuntimeVariableName ([string]$name)){$Environment[[string]$name]=$null}
    }
    foreach($name in @($Environment.Keys)){
        if(Test-SqlRuntimeVariableName ([string]$name)){$Environment[[string]$name]=$null}
    }
    $Environment.ConnectionStrings__RackClick=$null
    if($null-eq$Definition){$Environment.SqlSecret__Enabled='false';$Environment.ConnectionStrings__RackClick=$LegacyConnection;return}
    if($LegacyConnection-ne''){Stop-SqlOperator 'sql_operator_plaintext_conflict'}
    $d=ConvertTo-SqlOperatorMap $Definition
    Assert-SqlOperatorKeys $d 'ciphertextSha256,database,enabled,file,installationId,instancesRoot,runtimeUser'
    Assert-SqlOperatorIdentity $d.installationId $d.database $d.runtimeUser
    if($d.enabled-isnot[bool]-or-not$d.enabled-or$d.instancesRoot-isnot[string]-or-not[IO.Path]::IsPathRooted($d.instancesRoot)){Stop-SqlOperator 'sql_operator_runtime_invalid'}
    $Environment.SqlSecret__Enabled='true'
    $Environment.SqlSecret__InstancesRoot=$d.instancesRoot;$Environment.SqlSecret__InstallationId=$d.installationId
    $Environment.SqlSecret__Database=$d.database;$Environment.SqlSecret__RuntimeUser=$d.runtimeUser
}
function Get-SqlOperatorDiagnostic([string]$Mode,[string]$Code) {
    $allowed=@('sql_secret_missing','sql_secret_invalid','sql_secret_access_unsafe','sql_secret_unreadable','sql_secret_decryption_failed','sql_secret_config_invalid','sql_secret_plaintext_conflict','sql_secret_runtime_only','sql_operator_unprotect_failed','sql_operator_runtime_invalid')
    return @{schemaVersion=1;protection=$(if($Mode-cin@('legacy','protected')){$Mode}else{'unknown'});code=$(if($Code-cin$allowed){$Code}else{'sql_operator_unknown'});credentialsIncluded=$false}
}
