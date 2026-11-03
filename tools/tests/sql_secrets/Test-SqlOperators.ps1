#requires -Version 5.1
[CmdletBinding()]
param([string]$FixtureRoot)
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$project=Split-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) -Parent
$PostgresBinPath=''
. (Join-Path $project 'tools/windows/RackClick.Backup.ps1')
. (Join-Path $project 'tools/windows/server-install/Show-RackClickDatabaseAccess.ps1') -FunctionsOnly
. (Join-Path $project 'tools/windows/server-install/RackClick.Setup.ServiceDiagnostics.ps1')
$script:passed=0
function Check-Sql([bool]$Condition,[string]$Name){if(-not$Condition){throw ('test_failed: '+$Name)};$script:passed++}
function Reject-Sql([scriptblock]$Action,[string]$Expected){try{&$Action|Out-Null}catch{if($_.Exception.Message-cne$Expected){throw ('unexpected_error_type: '+$Expected)};$script:passed++;return};throw ('not_rejected: '+$Expected)}
$root=New-BackupPrivateDirectory $FixtureRoot
$id=[guid]::NewGuid().ToString('D');$suffix=$id.Replace('-','')
$db='rc_db_'+$suffix;$user='rc_runtime_'+$suffix;$password='synthetic-only-sql-:'+('\tail')
$profile=@{schemaVersion=2;installationId=$id;host='127.0.0.1';port=55441;database=$db;user=$user;passwordFile='C:\unused\secret.json'}
$record=Protect-SqlBackupPassword $password $profile
Check-Sql ((Unprotect-SqlBackupPassword $record $profile)-ceq$password) 'backup current-user DPAPI round trip'
$copy=@{};foreach($key in $profile.Keys){$copy[$key]=$profile[$key]};$copy.database='other_db'
Reject-Sql {Unprotect-SqlBackupPassword $record $copy} 'sql_operator_unprotect_failed'
$copy.installationId=[guid]::NewGuid().ToString('D');$copy.database=$db
Reject-Sql {Unprotect-SqlBackupPassword $record $copy} 'sql_operator_unprotect_failed'
$bad=@{};foreach($key in $record.Keys){$bad[$key]=$record[$key]};$bad.ciphertext='not-base64'
Reject-Sql {Unprotect-SqlBackupPassword $bad $profile} 'sql_operator_unprotect_failed'
$bad=@{};foreach($key in $record.Keys){$bad[$key]=$record[$key]};$bad.protection='DPAPI-LocalMachine'
Reject-Sql {Unprotect-SqlBackupPassword $bad $profile} 'sql_operator_secret_invalid'
$backupRoot=Join-Path $root 'backup-new';$path=New-SqlProtectedBackupProfile $backupRoot $id 55441 $db $user $password
$read=Read-BackupProfile $path
Check-Sql ($read.password-ceq$password-and$read.user-ceq$user) 'backup reader v2 consumes protected password'
Check-Sql (-not([IO.File]::ReadAllText((Join-Path $backupRoot 'password.dpapi.json')).Contains($password))) 'ciphertext persisted without password'
$filesBefore=@(Get-ChildItem -LiteralPath $backupRoot -File|ForEach-Object{(Get-FileHash -LiteralPath $_.FullName).Hash})-join','
Reject-Sql {New-SqlProtectedBackupProfile $backupRoot $id 55441 $db $user $password} 'destination_exists'
Check-Sql ($filesBefore-ceq(@(Get-ChildItem -LiteralPath $backupRoot -File|ForEach-Object{(Get-FileHash -LiteralPath $_.FullName).Hash})-join',')) 'existing destination preserved'
$builder=New-Object Data.Common.DbConnectionStringBuilder
$builder.set_ConnectionString(('Host=127.0.0.1;Port=55441;Database='+$db+';Username='+$user+';Password='+('a'*64)+';SSL Mode=Disable;Timeout=5;Command Timeout=15'))
$sid=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value
$descriptor=New-SqlProtectedRuntimeStore $root $id $sid $db $user $builder.ConnectionString
$definition=Get-SqlRuntimeDefinition $descriptor $root $id $db $user
$cipher=[IO.File]::ReadAllBytes($definition.file)
Check-Sql ((Unprotect-SqlRuntimeConnection $cipher $id $sid $db $user)-ceq$builder.ConnectionString) 'runtime codec RCSQL001 round trip'
$runtimeBytes=[Text.Encoding]::UTF8.GetBytes(($descriptor|ConvertTo-Json -Depth 5 -Compress))
$manifest=[pscustomobject]@{id=$id;rootPath=$root;database=$db;runtime=$user;postgresPort=55441;secretFiles=[pscustomobject]@{'runtime.json'=(Get-RcDatabaseAccessHash $runtimeBytes)}}
$runtimeView=Read-RcDatabaseAccessRuntime $runtimeBytes $manifest $cipher $sid
Check-Sql ($runtimeView.username-ceq$user-and$runtimeView.password-ceq('a'*64)) 'protected private viewer consumes real PS DPAPI'
foreach($flag in @('Persist Security Info','Include Error Detail','Log Parameters')){
    $badBuilder=New-Object Data.Common.DbConnectionStringBuilder;$badBuilder.set_ConnectionString($builder.ConnectionString)
    foreach($key in @('Persist Security Info','Include Error Detail','Log Parameters')){$badBuilder[$key]='false'}
    $badBuilder[$flag]='true'
    $badCipher=Protect-SqlRuntimeConnection $badBuilder.ConnectionString $id $sid $db $user
    $badDescriptor=@{schemaVersion=2;ciphertextSha256=(Get-RcDatabaseAccessHash $badCipher);sqlSecret=$descriptor.sqlSecret}
    $badBytes=[Text.Encoding]::UTF8.GetBytes(($badDescriptor|ConvertTo-Json -Depth 5 -Compress))
    $badManifest=[pscustomobject]@{id=$id;rootPath=$root;database=$db;runtime=$user;postgresPort=55441;secretFiles=[pscustomobject]@{'runtime.json'=(Get-RcDatabaseAccessHash $badBytes)}}
    Reject-Sql {Read-RcDatabaseAccessRuntime $badBytes $badManifest $badCipher $sid} 'database_access_runtime_invalid'
}
Reject-Sql {Unprotect-SqlRuntimeConnection $cipher ([guid]::NewGuid().ToString('D')) $sid $db $user} 'sql_operator_unprotect_failed'
Reject-Sql {Unprotect-SqlRuntimeConnection $cipher $id 'S-1-5-32-545' $db $user} 'sql_operator_unprotect_failed'
Reject-Sql {New-SqlProtectedRuntimeStore $root $id $sid $db $user $builder.ConnectionString} 'destination_exists'
$changed=@{schemaVersion=2;ciphertextSha256=$descriptor.ciphertextSha256;sqlSecret=@{enabled=$true;instancesRoot='C:\other';installationId=$id;database=$db;runtimeUser=$user}}
Reject-Sql {Get-SqlRuntimeDefinition $changed $root $id $db $user} 'sql_operator_runtime_invalid'
$envMap=@{'SqlSecret__Enabled'='false';'SqlSecret:InstancesRoot'='C:\poison';'ConnectionStrings__RackClick'='poison';'ConnectionStrings:RackClick'='poison'}
Set-SqlRuntimeEnvironment $envMap $definition
Check-Sql ($envMap.SqlSecret__Enabled-ceq'true'-and$null-eq$envMap.ConnectionStrings__RackClick-and$null-eq$envMap['ConnectionStrings:RackClick']-and$null-eq$envMap['SqlSecret:InstancesRoot']) 'protected environment only metadata, aliases removed'
$aliases=@('MYSQL','SQLAZURE','SQL','CUSTOM','POSTGRESQL','APIHUB','DOCDB','EVENTHUB','NOTIFICATIONHUB','REDISCACHE','SERVICEBUS')
foreach($alias in $aliases){$envMap[$alias+'CONNSTR_RackClick']='synthetic-poison'}
Set-SqlRuntimeEnvironment $envMap $definition
Check-Sql (@($envMap.Keys|Where-Object{$_-like'*CONNSTR*'-and$null-ne$envMap[$_]}).Count-eq0) 'all eleven dotnet connection aliases removed'
$savedAlias=[Environment]::GetEnvironmentVariable('CUSTOMCONNSTR_RackClick','Process')
try{[Environment]::SetEnvironmentVariable('CUSTOMCONNSTR_RackClick','synthetic-ambient-poison','Process');$ambient=@{};Set-SqlRuntimeEnvironment $ambient $definition;Check-Sql ($ambient.ContainsKey('CUSTOMCONNSTR_RackClick')-and$null-eq$ambient.CUSTOMCONNSTR_RackClick) 'ambient alias cleared even when absent in supplied map'}finally{[Environment]::SetEnvironmentVariable('CUSTOMCONNSTR_RackClick',$savedAlias,'Process')}
Reject-Sql {Set-SqlRuntimeEnvironment @{} $definition 'plaintext-conflict'} 'sql_operator_plaintext_conflict'
Set-SqlRuntimeEnvironment $envMap $null 'legacy-value'
Check-Sql ($envMap.SqlSecret__Enabled-ceq'false'-and$envMap.ConnectionStrings__RackClick-ceq'legacy-value') 'legacy explicit mode only'
$diagnostic=Get-SqlOperatorDiagnostic 'protected' 'secret-value-should-not-appear'
Check-Sql (($diagnostic|ConvertTo-Json -Compress)-notlike'*secret-value*'-and$diagnostic.code-ceq'sql_operator_unknown') 'diagnostic unknown value does not reflect input'
Check-Sql ((Get-SetupServiceKnownRuntimeCodes)-ccontains'sql_secret_decryption_failed') 'finite diagnostic vocabulary includes SQL codes'
$access=@{installationId=$id;serviceName='RackClick';publicOrigin='https://192.0.2.10:5443';host='127.0.0.1';port=55441;database=$db;username=$user;password='NEVER_EXPORT_SQL_92';webUsername='fixture-web';webPassword='NEVER_EXPORT_WEB_19'}
$card=Format-RcDatabaseAccessMetadata $access
Check-Sql (-not$card.Contains($access.password)-and-not$card.Contains($access.webPassword)-and$card.Contains($db)) 'connection card excludes both passwords'
# Compile the real private reader, without invoking privileged reads.
Initialize-RcDatabaseAccessReader
Check-Sql ($null-ne('RackClickDatabasePrivateReader'-as[type])) 'native access reader compiles with ciphertext whitelist'
@{result='PASS';checks=$script:passed;windowsPowerShell=$PSVersionTable.PSVersion.ToString();syntheticOnly=$true;vmOperations=0}|ConvertTo-Json -Compress
