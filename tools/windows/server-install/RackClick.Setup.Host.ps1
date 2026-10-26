#requires -Version 5.1
# Read-only host checks. Import defines functions; it does not inspect or change Windows.
function Get-SetupHostCompatibility {
    $productType=$null;$domainRole=$null;$partOfDomain=$null
    $osRead=$false;$computerRead=$false
    $integerTypes=@([byte],[sbyte],[int16],[uint16],[int32],[uint32],[int64],[uint64])
    try {
        $operatingSystems=@(Get-CimInstance -ClassName Win32_OperatingSystem -ErrorAction Stop)
        if($operatingSystems.Count-eq1-and$null-ne$operatingSystems[0].ProductType-and
            $operatingSystems[0].ProductType.GetType()-in$integerTypes-and
            $operatingSystems[0].ProductType-in@(1,2,3)) {
            $productType=[int]$operatingSystems[0].ProductType;$osRead=$true
        }
    } catch { $osRead=$false }
    try {
        $computers=@(Get-CimInstance -ClassName Win32_ComputerSystem -ErrorAction Stop)
        if($computers.Count-eq1-and$null-ne$computers[0].DomainRole-and
            $computers[0].DomainRole.GetType()-in$integerTypes-and
            $computers[0].DomainRole-in@(0,1,2,3,4,5)) {
            $domainRole=[int]$computers[0].DomainRole
            if($computers[0].PartOfDomain-is[bool]) {
                $partOfDomain=$computers[0].PartOfDomain;$computerRead=$true
            }
        }
    } catch { $computerRead=$false }
    $valid=$false;$code='setup_host_role_unverified'
    # Either authoritative indication of a DC is sufficient to reject this local-account installer.
    if($productType-eq2-or$domainRole-in@(4,5)) {
        $code='setup_domain_controller_not_supported'
    } elseif($osRead-and$computerRead) {
        $pairMatches=($productType-eq1-and$domainRole-in@(0,1))-or
            ($productType-eq3-and$domainRole-in@(2,3))
        $domainMatches=$partOfDomain-eq($domainRole-in@(1,3))
        if($pairMatches-and$domainMatches) {$valid=$true;$code='setup_host_supported'}
    }
    [pscustomobject][ordered]@{
        schemaVersion=1;valid=$valid;exitCode=$(if($valid){0}else{2});code=$code
        productType=$productType;domainRole=$domainRole;partOfDomain=$partOfDomain
    }
}
function Assert-SetupSupportedHost {
    $compatibility=Get-SetupHostCompatibility
    if(-not$compatibility.valid) {throw ([string]$compatibility.code)}
    return $compatibility
}
