#requires -Version 5.1
param([string]$OutputPath='')
$ErrorActionPreference='Stop'
$ops=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\windows\server-install'))
$checks=New-Object Collections.Generic.List[string]
function Check($Value,[string]$Name){if(-not$Value){throw $Name};$checks.Add($Name)}
$script:queryCount=0
function Get-CimInstance {param($ClassName,$ErrorAction) $script:queryCount++;throw 'Import must never query Windows'}
. (Join-Path $ops 'RackClick.Setup.Host.ps1')
Check ($script:queryCount-eq0) 'Import makes no CIM query or host mutation'
Remove-Item Function:\Get-CimInstance
$nativeOs=@(Get-CimInstance -ClassName Win32_OperatingSystem -ErrorAction Stop)
$nativeComputer=@(Get-CimInstance -ClassName Win32_ComputerSystem -ErrorAction Stop)
$native=Get-SetupHostCompatibility
Check ($native.schemaVersion-eq1-and$native.productType-eq$nativeOs[0].ProductType-and$native.domainRole-eq$nativeComputer[0].DomainRole-and$native.partOfDomain-eq$nativeComputer[0].PartOfDomain) 'Actual local CIM queries produce a matching read-only snapshot'
Check (@($native.PSObject.Properties.Name).Count-eq7-and-not($native|ConvertTo-Json -Compress).Contains([Environment]::UserName)) 'Snapshot contains only seven status fields and no user or domain name'
$script:osRows=@();$script:computerRows=@();$script:failedClass='';$script:queryCount=0
function Get-CimInstance {
    param($ClassName,$ErrorAction)
    $script:queryCount++
    if($ClassName-ceq$script:failedClass){throw [UnauthorizedAccessException]::new('Fixture CIM unavailable')}
    switch -CaseSensitive ($ClassName) {
        Win32_OperatingSystem {return $script:osRows}
        Win32_ComputerSystem {return $script:computerRows}
        default {throw 'Unexpected host query'}
    }
}
function Set-HostFixture($Product,$Role,$Domain) {
    $script:osRows=@([pscustomobject]@{ProductType=$Product})
    $script:computerRows=@([pscustomobject]@{DomainRole=$Role;PartOfDomain=$Domain})
    $script:failedClass=''
}
function Expect-Code([string]$Code,[bool]$Valid,[string]$Name) {
    $status=Get-SetupHostCompatibility
    Check ($status.code-ceq$Code-and$status.valid-eq$Valid-and$status.exitCode-eq$(if($Valid){0}else{2})) $Name
}
Set-HostFixture ([uint32]1) ([uint16]0) $false
Expect-Code 'setup_host_supported' $true 'Standalone Windows workstation accepted'
Set-HostFixture ([uint32]1) ([uint16]1) $true
Expect-Code 'setup_host_supported' $true 'Domain-member workstation accepted without changing Active Directory'
Set-HostFixture ([uint32]3) ([uint16]2) $false
Expect-Code 'setup_host_supported' $true 'Standalone Windows Server accepted'
Set-HostFixture ([uint32]3) ([uint16]3) $true
Expect-Code 'setup_host_supported' $true 'Domain-member Windows Server accepted'
$guard=Assert-SetupSupportedHost
Check ($guard.valid-and$guard.code-ceq'setup_host_supported') 'Supported-host guard returns the validated snapshot'
Set-HostFixture ([uint32]2) ([uint16]4) $true
Expect-Code 'setup_domain_controller_not_supported' $false 'Backup domain controller rejected'
Set-HostFixture ([uint32]2) ([uint16]5) $true
Expect-Code 'setup_domain_controller_not_supported' $false 'Primary domain controller rejected'
$thrown='';try{Assert-SetupSupportedHost|Out-Null}catch{$thrown=$_.Exception.Message}
Check ($thrown-ceq'setup_domain_controller_not_supported') 'Unsupported-host guard throws the exact actionable code'
Set-HostFixture ([uint32]2) ([uint16]2) $false
Expect-Code 'setup_domain_controller_not_supported' $false 'ProductType DC indication overrides contradictory normal server role'
Set-HostFixture ([uint32]3) ([uint16]5) $false
Expect-Code 'setup_domain_controller_not_supported' $false 'ComputerSystem DC indication overrides contradictory product type and membership'
Set-HostFixture ([uint32]3) ([uint16]1) $true
Expect-Code 'setup_host_role_unverified' $false 'Inconsistent server and workstation roles rejected'
Set-HostFixture ([uint32]1) ([uint16]0) $true
Expect-Code 'setup_host_role_unverified' $false 'Inconsistent domain membership rejected'
Set-HostFixture ([uint32]3) ([uint16]3) 'True'
Expect-Code 'setup_host_role_unverified' $false 'String domain-membership value rejected'
Set-HostFixture '3' ([uint16]2) $false
Expect-Code 'setup_host_role_unverified' $false 'String product type rejected'
Set-HostFixture ([uint32]3) '2' $false
Expect-Code 'setup_host_role_unverified' $false 'String role rejected'
Set-HostFixture ([uint32]3) ([uint16]6) $false
Expect-Code 'setup_host_role_unverified' $false 'Unknown role rejected'
Set-HostFixture ([uint32]0) ([uint16]2) $false
Expect-Code 'setup_host_role_unverified' $false 'Unknown product type rejected'
Set-HostFixture ([uint32]3) ([uint16]2) $false
$script:osRows=@()
Expect-Code 'setup_host_role_unverified' $false 'Missing OperatingSystem row fails closed'
Set-HostFixture ([uint32]3) ([uint16]2) $false
$script:computerRows+= $script:computerRows[0]
Expect-Code 'setup_host_role_unverified' $false 'Ambiguous ComputerSystem rows fail closed'
Set-HostFixture ([uint32]3) ([uint16]2) $false
$script:failedClass='Win32_OperatingSystem'
Expect-Code 'setup_host_role_unverified' $false 'OperatingSystem query failure fails closed'
Set-HostFixture ([uint32]3) ([uint16]2) $false
$script:failedClass='Win32_ComputerSystem'
Expect-Code 'setup_host_role_unverified' $false 'ComputerSystem query failure fails closed'
Set-HostFixture ([uint32]2) ([uint16]5) $true
$script:failedClass='Win32_ComputerSystem'
Expect-Code 'setup_domain_controller_not_supported' $false 'Known DC product type still rejects when second CIM query fails'
Set-HostFixture ([uint32]3) ([uint16]5) $true
$script:failedClass='Win32_OperatingSystem'
Expect-Code 'setup_domain_controller_not_supported' $false 'Known DC role still rejects when first CIM query fails'
$result=[ordered]@{valid=$true;passed=$checks.Count;checks=@($checks.ToArray());environment='Windows PowerShell 5.1 x64; actual local read-only CIM plus mocked role matrix';localHost=$native;osAccountsChanged=0;servicesChanged=0;tasksChanged=0;activeDirectoryChanged=$false;limits=@('No domain-controller VM queried or modified','No account, group, registry, LSA, service, namespace or cleanup operation performed')}
if($OutputPath){[IO.File]::WriteAllText([IO.Path]::GetFullPath($OutputPath),($result|ConvertTo-Json -Depth 6),(New-Object Text.UTF8Encoding($false)))}
$result|ConvertTo-Json -Depth 6 -Compress
