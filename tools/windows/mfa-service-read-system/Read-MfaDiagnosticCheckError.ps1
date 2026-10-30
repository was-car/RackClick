#requires -Version 5.1
# Read-only companion: invokes ONLY Check of the exact delivered diagnostic01.
[CmdletBinding()]
param(
    [ValidateSet('Check','SelfTest')][string]$Mode='Check',
    [string]$SearchRoot='C:\MFA03'
)
$ErrorActionPreference='Stop'
$DiagnosticScriptPin='e2cb1ab8c3d1d92ec1ec2335476f2cf94fd3428ac86dc49508329f55fc99a0b4'
$DiagnosticSumsPin='a56b82900a40588a1a2e742bd730e23c30affd40a143a7d3fbf1443d08f8a3c6'
$FrameNames=@('Read-DiagnosticContext','Invoke-DiagnosticCheckOrRun','Add-DiagnosticLease','Import-DiagnosticPinnedFunctions',
    'Assert-DiagnosticPath','Assert-DiagnosticNoReparse','Assert-Elevated','Assert-PrivateRoot','Assert-ResumeRoot03',
    'Assert-ResumePlan03','Import-ReferenceFunctions','Get-Context','Get-StoreFingerprint','Test-PackageIntegrity',
    'Test-DiagnosticPackage','Get-Sha256Hex','Get-TextSha256','Hash-Text','Get-TaskXml','New-ResumeDefinition03',
    'Get-DiagnosticHash','ConvertFrom-SumsLine','Get-InstallationId','Resolve-TrialRoot','Get-RelPath')
$CommandNames=$FrameNames+@('Get-FileHash','Get-Item','Get-ChildItem','Get-Acl','Get-CimInstance','New-Object','Join-Path','ConvertFrom-Json')
$ExceptionNames=@('System.InvalidCastException','System.Management.Automation.MethodInvocationException',
    'System.Management.Automation.PSInvalidCastException','System.Management.Automation.MethodException',
    'System.Management.Automation.RuntimeException','System.Management.Automation.ParameterBindingException',
    'System.ArgumentException','System.InvalidOperationException','System.UnauthorizedAccessException',
    'System.IO.IOException','System.IO.FileNotFoundException','System.IO.DirectoryNotFoundException',
    'System.Runtime.InteropServices.COMException','System.Management.Automation.CmdletInvocationException')
function Get-CheckErrorMetadata($Record) {
    $types=@();$hresults=@();$errorException=$Record.Exception
    while ($null -ne $errorException -and $hresults.Count -lt 8) {
        $type=$errorException.GetType().FullName
        $types+= $(if($type -cin $ExceptionNames){$type}else{'other'})
        $hresults+=([int]$errorException.HResult)
        $errorException=$errorException.InnerException
    }
    $frames=@()
    foreach ($line in @(([string]$Record.ScriptStackTrace) -split "`r?`n")) {
        # Ignore the localized prefix and discard the complete filename/path.
        $match=[regex]::Match($line,'^\s*\S+\s+([A-Za-z][A-Za-z0-9_-]*),.*?(\d+)\s*$')
        if ($match.Success -and $match.Groups[1].Value -cin $FrameNames) {
            $number=0
            if ([int]::TryParse($match.Groups[2].Value,[ref]$number)) {
                $frames+=@{function=$match.Groups[1].Value;line=$number}
            }
        }
        if($frames.Count -ge 12){break}
    }
    $command=[string]$Record.InvocationInfo.MyCommand.Name
    if ($command -cnotin $CommandNames) { $command='unavailable' }
    return [ordered]@{exceptionTypes=@($types);hresults=@($hresults);command=$command;frames=@($frames)}
}
function Assert-CheckReaderPath([string]$Path) {
    $item=Get-Item -LiteralPath $Path -Force
    while($null -ne $item){
        if(($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0){throw 'check_reader:reparse_point'}
        if($item -is [IO.FileInfo]){$item=$item.Directory}else{$item=$item.Parent}
    }
}
function Invoke-CheckReaderSelfTest {
    $inner=New-Object InvalidCastException('PRIVATE_SENTINEL SID=synthetic C:\private\fixture')
    $outer=New-Object Exception('PRIVATE_SENTINEL',$inner)
    $record=[pscustomobject]@{Exception=$outer;ScriptStackTrace="bei Read-DiagnosticContext, C:\PRIVATE_SENTINEL.ps1: Zeile 117`r`nat UnknownPrivateName, C:\PRIVATE_SENTINEL.ps1: line 99";InvocationInfo=[pscustomobject]@{MyCommand=[pscustomobject]@{Name='PRIVATE_SENTINEL'}}}
    $safe=Get-CheckErrorMetadata $record;$json=$safe|ConvertTo-Json -Depth 6 -Compress
    if($safe.exceptionTypes -cnotcontains 'System.InvalidCastException' -or $safe.hresults -notcontains -2147467262 -or
        @($safe.frames).Count -ne 1 -or $safe.frames[0].line -ne 117 -or $safe.command -cne 'unavailable' -or
        $json -match 'PRIVATE_SENTINEL|private|SID='){throw 'check_reader:selftest_failed'}
    @{schemaVersion=1;status='selftest_passed';checks=4;tasksCreated=$false;probeExecuted=$false}|ConvertTo-Json -Compress
}
function Invoke-ReadCheckError {
    if($env:COMPUTERNAME -ieq 'LEAO' -or [Environment]::MachineName -ieq 'LEAO'){throw 'check_reader:host_excluded'}
    Assert-CheckReaderPath $SearchRoot
    $files=@(Get-ChildItem -LiteralPath $SearchRoot -Filter 'Invoke-MfaProbeExceptionDiagnostic.ps1' -Recurse -File -ErrorAction Stop | Sort-Object LastWriteTimeUtc -Descending)
    $file=$null
    foreach($candidate in $files){
        Assert-CheckReaderPath $candidate.FullName
        if((Get-FileHash -LiteralPath $candidate.FullName -Algorithm SHA256).Hash -ieq $DiagnosticScriptPin){$file=$candidate;break}
    }
    if($null -eq $file){throw 'check_reader:approved_script_missing'}
    $package=$file.DirectoryName;$sums=Join-Path $package 'SHA256SUMS';Assert-CheckReaderPath $sums
    $scriptLease=[IO.File]::Open($file.FullName,'Open','Read','Read');$sumsLease=$null
    try {
        $sumsLease=[IO.File]::Open($sums,'Open','Read','Read')
        if((Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash -ine $DiagnosticScriptPin -or
            (Get-FileHash -LiteralPath $sums -Algorithm SHA256).Hash -ine $DiagnosticSumsPin){throw 'check_reader:hash_mismatch'}
        # This reader runs in its own PowerShell process. Do not clear the operator console history.
        $Error.Clear()
        & $file.FullName -Mode Check -PackageRoot $package -ExpectedScriptSha256 $DiagnosticScriptPin -ExpectedSumsSha256 $DiagnosticSumsPin
        $checkExit=$LASTEXITCODE
        $records=@($Error)
        $metadata=@()
        foreach($record in $records){$metadata+=(Get-CheckErrorMetadata $record);if($metadata.Count -ge 8){break}}
        [ordered]@{schemaVersion=1;status='check_error_collected';checkExitCode=$checkExit;errors=@($metadata);
            checkOnly=$true;tasksCreated=$false;probeExecuted=$false;keysRead=$false;priorAttemptPreserved=$true}|ConvertTo-Json -Depth 9 -Compress
    }
    finally {if($null -ne $sumsLease){$sumsLease.Dispose()};$scriptLease.Dispose()}
}
try {
    if($Mode -ceq 'SelfTest'){Invoke-CheckReaderSelfTest}else{Invoke-ReadCheckError}
    exit 0
} catch {
    $code='reader_failed'
    if($_.Exception.Message -cmatch '^check_reader:([a-z_]+)$'){$code=$Matches[1]}
    @{schemaVersion=1;status='rejected';code=$code;tasksCreated=$false;probeExecuted=$false}|ConvertTo-Json -Compress
    exit 1
}
