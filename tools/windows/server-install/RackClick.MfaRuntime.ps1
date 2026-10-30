#requires -Version 5.1
# Pure profile/environment contract. No file access, key access or process mutation.

function Stop-ServerMfaProfile {
    $failure = New-Object InvalidOperationException('server_mfa_profile_invalid')
    $failure.Data['serverCode'] = 'server_mfa_profile_invalid'
    $failure.Data['serverExit'] = 2
    throw $failure
}

function ConvertTo-ServerMfaMap {
    param($Value)
    $map = @{}
    if ($Value -is [Collections.IDictionary]) {
        foreach ($name in $Value.Keys) {
            if ($name -isnot [string] -or $map.ContainsKey($name)) { Stop-ServerMfaProfile }
            $map[$name] = $Value[$name]
        }
    } elseif ($Value -is [pscustomobject]) {
        foreach ($property in $Value.PSObject.Properties) {
            if ($map.ContainsKey($property.Name)) { Stop-ServerMfaProfile }
            $map[$property.Name] = $property.Value
        }
    } else {
        Stop-ServerMfaProfile
    }
    return $map
}

function Get-ServerMfaProfile {
    param($Manifest, [string]$InstallationId = '')
    $manifestMap = ConvertTo-ServerMfaMap $Manifest
    if ($manifestMap.Keys -cnotcontains 'schemaVersion' -or $manifestMap['schemaVersion'] -isnot [int]) { Stop-ServerMfaProfile }
    if ($manifestMap['schemaVersion'] -eq 1) {
        if ($manifestMap.ContainsKey('mfa')) { Stop-ServerMfaProfile }
        return @{ enabled = $false; instancesRoot = $null; installationId = $null }
    }
    if ($manifestMap['schemaVersion'] -ne 2 -or $manifestMap.Keys -cnotcontains 'mfa') { Stop-ServerMfaProfile }
    $mfa = ConvertTo-ServerMfaMap $manifestMap['mfa']
    if ((($mfa.Keys | Sort-Object) -join ',') -cne 'enabled,installationId,instancesRoot' -or
        $mfa['enabled'] -isnot [bool] -or -not $mfa['enabled'] -or
        $mfa['instancesRoot'] -isnot [string] -or $mfa['installationId'] -isnot [string]) { Stop-ServerMfaProfile }

    $id = [guid]::Empty
    if (-not [guid]::TryParseExact($InstallationId, 'D', [ref]$id) -or $id -eq [guid]::Empty -or
        $InstallationId -cne $id.ToString('D') -or $mfa['installationId'] -cne $InstallationId) { Stop-ServerMfaProfile }
    $parent = 'C:\ProgramData\RackClick\Instances\' + $InstallationId
    $root = $parent + '\security'
    # Dedicated root: the shared Instances directory has readers from outside
    # this service and cannot satisfy the approved provider's private ACL rules.
    if (-not [string]::Equals($mfa['instancesRoot'], $root, [StringComparison]::OrdinalIgnoreCase)) { Stop-ServerMfaProfile }
    $expectedPath = $parent + '\instance'
    if ($manifestMap.Keys -cnotcontains 'installationPath' -or $manifestMap['installationPath'] -isnot [string] -or
        -not [string]::Equals($manifestMap['installationPath'], $expectedPath, [StringComparison]::OrdinalIgnoreCase)) { Stop-ServerMfaProfile }
    return @{ enabled = $true; instancesRoot = $root; installationId = $InstallationId }
}

function Set-ServerMfaEnvironment {
    param([hashtable]$Environment, $MfaProfile)
    if ($null -eq $Environment) { Stop-ServerMfaProfile }
    $profile = ConvertTo-ServerMfaMap $MfaProfile
    if ((($profile.Keys | Sort-Object) -join ',') -cne 'enabled,installationId,instancesRoot' -or $profile['enabled'] -isnot [bool]) { Stop-ServerMfaProfile }
    # Validate everything before changing the supplied table.
    if ($profile['enabled']) {
        $synthetic = @{
            schemaVersion = 2
            installationPath = 'C:\ProgramData\RackClick\Instances\' + $profile['installationId'] + '\instance'
            mfa = $profile
        }
        $profile = Get-ServerMfaProfile $synthetic $profile['installationId']
    } elseif ($null -ne $profile['instancesRoot'] -or $null -ne $profile['installationId']) {
        Stop-ServerMfaProfile
    }
    foreach ($name in @($Environment.Keys)) {
        if ($name -isnot [string]) { Stop-ServerMfaProfile }
    }
    foreach ($name in @($Environment.Keys)) {
        if ($name -match '^(?i:MfaKeyStore):') {
            # Colon aliases must also be removed from the launching process by
            # Clear-LauncherInheritedConfiguration, then restored in finally.
            $Environment.Remove($name)
        } elseif ($name -match '^(?i:MfaKeyStore)(?:__|$)') {
            $Environment[$name] = $null
        }
    }
    $Environment['MfaKeyStore__Enabled'] = if ($profile['enabled']) { 'true' } else { 'false' }
    $Environment['MfaKeyStore__InstancesRoot'] = if ($profile['enabled']) { $profile['instancesRoot'] } else { $null }
    $Environment['MfaKeyStore__InstallationId'] = if ($profile['enabled']) { $profile['installationId'] } else { $null }
}
