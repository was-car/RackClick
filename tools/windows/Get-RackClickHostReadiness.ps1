#requires -Version 5.1
<# Passive local inventory only. No compatibility, installation or network test.
   No elevation, SDK or Python required. Only a NEW JSON file is written.
   Output inherits directory permissions; this tool adds no private ACL/encryption.
   valid means critical inventory collected; it is never a compatibility verdict.
   Exit 0: critical inventory collected; 2: incomplete/invalid input; 3: output failed.
   Dot-source exposes functions without collecting or writing anything.
#>
[CmdletBinding()]
param([string]$Role='', [string]$OutputDirectory='')
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'

function New-RackClickHostInventory {
    param([string]$RequestedRole)
    return [ordered]@{
        schemaVersion=1;kind='RackClickHostInventory';readiness='inventory_only'
        id=[guid]::NewGuid().ToString('D');createdUtc=[DateTime]::UtcNow.ToString('o')
        role=$(if ($RequestedRole -cin @('Server','Client3')) {$RequestedRole} else {$null})
        valid=$false;inventoryComplete=$false;exitCode=2;hostname=$null;operatingSystem=$null
        powershell=[ordered]@{version=$PSVersionTable.PSVersion.ToString();edition=$PSVersionTable.PSEdition
            process64Bit=[Environment]::Is64BitProcess;os64Bit=[Environment]::Is64BitOperatingSystem}
        ramBytes=$null;localDisks=@();ipv4=@();networkProfiles=@();editionId=$null
        pendingReboot=[ordered]@{status='unknown';indicators=@();unreadableIndicators=@()}
        edge=[ordered]@{status='not_checked';version=$null;checkedScope='standard_local_install_locations'}
        errors=(New-Object 'Collections.Generic.List[object]')
        warnings=(New-Object 'Collections.Generic.List[object]')
    }
}

function Add-RackClickInventoryIssue {
    param($Report,[string]$Area,[string]$Code,[switch]$Critical)
    $issue=[ordered]@{area=$Area;code=$Code}
    if ($Critical) {$Report.errors.Add($issue)} else {$Report.warnings.Add($issue)}
}

function Get-RackClickInventoryHostname { return [Environment]::MachineName }

function Get-RackClickInventoryEdition {
    return [string](Get-ItemProperty -LiteralPath 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion' -Name EditionID -ErrorAction Stop).EditionID
}

function Get-RackClickInventoryIPv4 {
    return @(Get-NetIPAddress -AddressFamily IPv4 -ErrorAction Stop | ForEach-Object {
        [ordered]@{address=[string]$_.IPAddress;prefixLength=[int]$_.PrefixLength
            interfaceIndex=[int]$_.InterfaceIndex;interfaceAlias=[string]$_.InterfaceAlias;addressState=[string]$_.AddressState}
    })
}

function Get-RackClickInventoryProfiles {
    return @(Get-NetConnectionProfile -ErrorAction Stop | ForEach-Object {
        [ordered]@{name=[string]$_.Name;interfaceIndex=[int]$_.InterfaceIndex
            interfaceAlias=[string]$_.InterfaceAlias;category=[string]$_.NetworkCategory;ipv4Connectivity=[string]$_.IPv4Connectivity}
    })
}

function Get-RackClickInventoryReboot {
    $pending=New-Object 'Collections.Generic.List[string]';$unknown=New-Object 'Collections.Generic.List[string]'
    $keys=@(
        @{name='component_based_servicing';path='HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Component Based Servicing\RebootPending'},
        @{name='windows_update';path='HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\WindowsUpdate\Auto Update\RebootRequired'})
    foreach ($key in $keys) {
        try {$null=Get-Item -LiteralPath $key.path -ErrorAction Stop;$pending.Add($key.name)}
        catch {if ($_.CategoryInfo.Category -ne [Management.Automation.ErrorCategory]::ObjectNotFound) {$unknown.Add($key.name)}}
    }
    try {
        $value=Get-ItemProperty -LiteralPath 'HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager' -ErrorAction Stop
        $property=$value.PSObject.Properties['PendingFileRenameOperations']
        if ($null -ne $property -and @($property.Value).Count -gt 0) {$pending.Add('pending_file_rename')}
    } catch {$unknown.Add('pending_file_rename')}
    $status=if ($pending.Count) {'pending'} elseif ($unknown.Count) {'unknown'} else {'not_detected'}
    return [ordered]@{status=$status;indicators=@($pending.ToArray());unreadableIndicators=@($unknown.ToArray())}
}

function Get-RackClickInventoryEdge {
    $roots=@([Environment]::GetFolderPath('ProgramFiles'),[Environment]::GetFolderPath('ProgramFilesX86'),[Environment]::GetFolderPath('LocalApplicationData'))
    $unreadable=$false
    foreach ($root in $roots) {
        if ([string]::IsNullOrWhiteSpace($root)) {continue}
        $path=[IO.Path]::Combine($root,'Microsoft\Edge\Application\msedge.exe')
        if (-not [IO.File]::Exists($path)) {continue}
        try {
            $version=[string](Get-Item -LiteralPath $path -ErrorAction Stop).VersionInfo.ProductVersion
            return [ordered]@{status='found';version=$(if ($version) {$version} else {$null});checkedScope='standard_local_install_locations'}
        } catch {$unreadable=$true}
    }
    return [ordered]@{status=$(if ($unreadable) {'unknown'} else {'not_found_in_checked_locations'});version=$null;checkedScope='standard_local_install_locations'}
}

function Get-RackClickHostInventory {
    param([string]$RequestedRole)
    $report=New-RackClickHostInventory $RequestedRole
    if ($null -eq $report.role) {Add-RackClickInventoryIssue $report 'input' 'role_invalid' -Critical;return $report}
    if (-not $report.powershell.process64Bit -or -not $report.powershell.os64Bit) {Add-RackClickInventoryIssue $report 'powershell' 'x64_inventory_process_required' -Critical}
    try {$report.hostname=Get-RackClickInventoryHostname}
    catch {Add-RackClickInventoryIssue $report 'host' 'hostname_unavailable' -Critical}
    if ([string]::IsNullOrWhiteSpace($report.hostname) -and -not @($report.errors|Where-Object {$_.area -ceq 'host'}).Count) {Add-RackClickInventoryIssue $report 'host' 'hostname_unavailable' -Critical}
    try {
        $values=@(Get-CimInstance -ClassName Win32_OperatingSystem -Property Caption,Version,BuildNumber,OSArchitecture,ProductType -ErrorAction Stop)
        if ($values.Count -ne 1) {throw 'os_count_invalid'}
        $os=$values[0]
        if ([string]::IsNullOrWhiteSpace($os.Caption) -or [string]::IsNullOrWhiteSpace($os.Version) -or
            [string]::IsNullOrWhiteSpace($os.BuildNumber) -or [string]::IsNullOrWhiteSpace($os.OSArchitecture) -or [int]$os.ProductType -notin @(1,2,3)) {throw 'os_fields_invalid'}
        $productType=[int]$os.ProductType
        $typeName=switch ($productType) {1 {'workstation'} 2 {'domain_controller'} 3 {'server'}}
        $report.operatingSystem=[ordered]@{caption=[string]$os.Caption;version=[string]$os.Version;build=[string]$os.BuildNumber
            architecture=[string]$os.OSArchitecture;productType=$productType;productTypeName=$typeName}
        if ($productType -eq 2) {Add-RackClickInventoryIssue $report 'operatingSystem' 'domain_controller_detected_inventory_only'}
        if ($RequestedRole -ceq 'Client3' -and $productType -ne 1) {Add-RackClickInventoryIssue $report 'operatingSystem' 'requested_role_differs_from_product_type'}
    } catch {Add-RackClickInventoryIssue $report 'operatingSystem' 'os_cim_inventory_failed' -Critical}
    try {
        $systems=@(Get-CimInstance -ClassName Win32_ComputerSystem -Property TotalPhysicalMemory -ErrorAction Stop)
        if ($systems.Count -ne 1 -or $null -eq $systems[0].TotalPhysicalMemory -or [uint64]$systems[0].TotalPhysicalMemory -eq 0) {throw 'ram_invalid'}
        $report.ramBytes=[uint64]$systems[0].TotalPhysicalMemory
    } catch {Add-RackClickInventoryIssue $report 'ram' 'ram_cim_inventory_failed' -Critical}
    try {
        $disks=@(Get-CimInstance -ClassName Win32_LogicalDisk -Filter 'DriveType=3' -Property DeviceID,Size,FreeSpace -ErrorAction Stop)
        if (-not $disks.Count) {throw 'disks_empty'}
        $report.localDisks=@(foreach ($disk in $disks) {
            if ($disk.DeviceID -notmatch '^[A-Za-z]:$' -or $null -eq $disk.Size -or $null -eq $disk.FreeSpace -or [uint64]$disk.Size -eq 0 -or [uint64]$disk.FreeSpace -gt [uint64]$disk.Size) {throw 'disk_fields_invalid'}
            [ordered]@{drive=[string]$disk.DeviceID;sizeBytes=[uint64]$disk.Size;freeBytes=[uint64]$disk.FreeSpace}
        })
    } catch {$report.localDisks=@();Add-RackClickInventoryIssue $report 'disk' 'disk_cim_inventory_failed' -Critical}
    try {$report.editionId=Get-RackClickInventoryEdition} catch {Add-RackClickInventoryIssue $report 'editionId' 'edition_id_unavailable'}
    if ([string]::IsNullOrWhiteSpace($report.editionId)) {Add-RackClickInventoryIssue $report 'editionId' 'edition_id_not_detected'}
    try {$report.ipv4=@(Get-RackClickInventoryIPv4)} catch {Add-RackClickInventoryIssue $report 'network' 'ipv4_inventory_unavailable'}
    try {$report.networkProfiles=@(Get-RackClickInventoryProfiles)} catch {Add-RackClickInventoryIssue $report 'network' 'network_profiles_unavailable'}
    try {$report.pendingReboot=Get-RackClickInventoryReboot} catch {Add-RackClickInventoryIssue $report 'reboot' 'reboot_inventory_unavailable'}
    if ($report.pendingReboot.status -ceq 'unknown' -or @($report.pendingReboot.unreadableIndicators).Count) {Add-RackClickInventoryIssue $report 'reboot' 'reboot_indicators_incomplete'}
    try {$report.edge=Get-RackClickInventoryEdge} catch {Add-RackClickInventoryIssue $report 'edge' 'edge_inventory_unavailable'}
    if ($report.edge.status -cne 'found' -or [string]::IsNullOrWhiteSpace($report.edge.version)) {Add-RackClickInventoryIssue $report 'edge' 'edge_not_confirmed_in_checked_locations'}
    $report.inventoryComplete=($report.errors.Count -eq 0)
    $report.valid=$report.inventoryComplete
    $report.exitCode=$(if ($report.inventoryComplete) {0} else {2})
    return $report
}

function Write-RackClickHostInventory {
    param($Report,[string]$Directory)
    if ([string]::IsNullOrWhiteSpace($Directory) -or $Directory.StartsWith('\\')) {throw 'output_directory_invalid'}
    $full=$ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($Directory)
    if ($full -notmatch '^[A-Za-z]:[\\/]' -or -not [IO.Directory]::Exists($full)) {throw 'output_directory_invalid'}
    $item=New-Object IO.DirectoryInfo($full)
    while ($null -ne $item) {
        if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {throw 'output_reparse_rejected'}
        $item=$item.Parent
    }
    $id=[guid]::Parse($Report.id).ToString('D')
    $stamp=[DateTime]::Parse($Report.createdUtc,[Globalization.CultureInfo]::InvariantCulture,[Globalization.DateTimeStyles]::RoundtripKind).ToUniversalTime().ToString('yyyyMMddTHHmmssfffZ')
    $roleName=if ($Report.role -cin @('Server','Client3')) {$Report.role} else {'InvalidRole'}
    $name='RackClick-Host-'+$roleName+'-'+$stamp+'-'+$id+'.json'
    $json=$Report|ConvertTo-Json -Depth 10
    $utf8=New-Object Text.UTF8Encoding($false);$bytes=$utf8.GetBytes($json+"`n");$stream=$null
    try {
        $stream=[IO.File]::Open([IO.Path]::Combine($full,$name),[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
        $stream.Write($bytes,0,$bytes.Length);$stream.Flush($true)
    } finally {if ($null -ne $stream) {$stream.Dispose()}}
    return $name
}

function Invoke-RackClickHostInventoryCommand {
    param([string]$RequestedRole,[string]$Directory)
    try {$result=Get-RackClickHostInventory $RequestedRole}
    catch {$result=New-RackClickHostInventory $RequestedRole;Add-RackClickInventoryIssue $result 'inventory' 'inventory_failed' -Critical}
    $name=$null
    try {$name=Write-RackClickHostInventory $result $Directory}
    catch {$result.valid=$false;$result.inventoryComplete=$false;$result.exitCode=3;Add-RackClickInventoryIssue $result 'output' 'new_report_write_failed' -Critical}
    [ordered]@{readiness='inventory_only';valid=$result.valid;inventoryComplete=$result.inventoryComplete;exitCode=$result.exitCode;reportFileName=$name;errors=@($result.errors.ToArray());warnings=@($result.warnings.ToArray())}|ConvertTo-Json -Depth 5 -Compress
    exit $result.exitCode
}

if ($MyInvocation.InvocationName -eq '.') {return}
Invoke-RackClickHostInventoryCommand $Role $OutputDirectory
