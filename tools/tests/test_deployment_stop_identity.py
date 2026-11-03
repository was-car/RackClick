"""Native PS5.1 file-only regression of captured-run stop publication; no PG/app."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
import uuid

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'development/server/tests'))
from pg_support import protect_directory

DRIVER=r'''param([string]$OperatorPath,[string]$ReaderPath,[string]$RootPath)
$inputs=@{operator=$OperatorPath;reader=$ReaderPath;root=$RootPath}
. $inputs.reader
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile($inputs.operator,[ref]$tokens,[ref]$errors)
if ($errors.Count -ne 0) {throw 'operator_parse_failed'}
foreach($name in @('Read-DeploymentOperationRecord','Test-DeploymentInstanceLockFree','Publish-DeploymentRunStop','Request-DeploymentCapturedRunStop')) {
    $definition=@($ast.FindAll({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -ceq $name},$true))
    if ($definition.Count -ne 1) {throw 'missing_actual_function'}
    Invoke-Expression $definition[0].Extent.Text
}
$probeRoot=$inputs.root;$logs=Join-Path $probeRoot 'logs';[IO.Directory]::CreateDirectory($logs)|Out-Null
$instanceId=[guid]::NewGuid().ToString('D');$oldId=[guid]::NewGuid().ToString('D');$newId=[guid]::NewGuid().ToString('D')
$oldDirectory=Join-Path $logs ('launcher-'+$oldId);$newDirectory=Join-Path $logs ('launcher-'+$newId)
[IO.Directory]::CreateDirectory($oldDirectory)|Out-Null;[IO.Directory]::CreateDirectory($newDirectory)|Out-Null
$activePath=Join-Path $logs 'active-run.json';$instanceLock=Join-Path $probeRoot 'instance.lock'
$deployment=@{instance=@{id=$instanceId;httpPort=34567;logRoot=$logs;lockPath=$instanceLock}}
function New-ProbeRecord([string]$runId) {
    return @{schemaVersion=1;instanceId=$instanceId;runId=$runId;publicOrigin='https://127.0.0.1:34567';requestRelativePath=('launcher-'+$runId+'/stop-request.json');status='ready';code='ready';utc=[DateTime]::UtcNow.ToString('o')}
}
$old=New-ProbeRecord $oldId;$next=New-ProbeRecord $newId
function Write-ProbeActive($value) { [IO.File]::WriteAllText($activePath,($value|ConvertTo-Json -Compress),(New-Object Text.UTF8Encoding($false))) }
$held=[IO.File]::Open($instanceLock,[IO.FileMode]::CreateNew,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
try {
    Write-ProbeActive $next;$code=''
    try { $null=Request-DeploymentCapturedRunStop -Deployment $deployment -CapturedRecord $old }
    catch { $code=$_.Exception.Data['deploymentCode'] }
    $beforeChangedRejected=$code -ceq 'deployment_active_run_changed'
    $beforeNoRequests=(-not [IO.File]::Exists((Join-Path $oldDirectory 'stop-request.json')) -and -not [IO.File]::Exists((Join-Path $newDirectory 'stop-request.json')))

    # Deterministic test interleaving, after the REAL reader validates OLD and closes
    # its snapshot but before the REAL requesting function chooses its publication.
    Write-ProbeActive $old
    $actualRead=(Get-Command Read-DeploymentOperationRecord).ScriptBlock
    function Read-DeploymentOperationRecord {
        param([string]$Path,[hashtable]$Deployment,[string]$ExpectedRunId='')
        $result=& $actualRead -Path $Path -Deployment $Deployment -ExpectedRunId $ExpectedRunId
        Write-ProbeActive $next
        return $result
    }
    try { $requested=Request-DeploymentCapturedRunStop -Deployment $deployment -CapturedRecord $old }
    finally { Set-Item -LiteralPath Function:Read-DeploymentOperationRecord -Value $actualRead }
    $oldRequest=Join-Path $oldDirectory 'stop-request.json';$newRequest=Join-Path $newDirectory 'stop-request.json'
    $body=[IO.File]::ReadAllText($oldRequest)|ConvertFrom-Json
    $capturedOnly=$requested -and $body.runId -ceq $oldId -and $body.instanceId -ceq $instanceId -and -not [IO.File]::Exists($newRequest)
    $newStillActive=([IO.File]::ReadAllText($activePath)|ConvertFrom-Json).runId -ceq $newId
    $bytesBefore=[Convert]::ToBase64String([IO.File]::ReadAllBytes($oldRequest))
    Publish-DeploymentRunStop -Directory $oldDirectory -RunId $oldId -InstanceId $instanceId
    $idempotent=$bytesBefore -ceq [Convert]::ToBase64String([IO.File]::ReadAllBytes($oldRequest))
    $conflict=''
    try { Publish-DeploymentRunStop -Directory $oldDirectory -RunId $newId -InstanceId $instanceId }
    catch { $conflict=$_.Exception.Data['deploymentCode'] }
    $conflictPreserved=$conflict -ceq 'deployment_stop_request_invalid' -and $bytesBefore -ceq [Convert]::ToBase64String([IO.File]::ReadAllBytes($oldRequest)) -and -not [IO.File]::Exists($newRequest)
    if (-not $beforeChangedRejected -or -not $beforeNoRequests -or -not $capturedOnly -or -not $newStillActive -or -not $idempotent -or -not $conflictPreserved) {throw 'identity_regression_failed'}
    @{valid=$true;changedBeforeReadRejected=$beforeChangedRejected;noRequestBeforeValidIdentity=$beforeNoRequests;controlledSwitchAfterRealRead=$true;publishedCapturedOldRunOnly=$capturedOnly;newRunStillActive=$newStillActive;identicalRequestIdempotent=$idempotent;conflictingRequestPreserved=$conflictPreserved;databaseQueries=0;applicationExecutions=0;serviceOperations=0}|ConvertTo-Json -Compress
} finally {$held.Dispose()}
'''

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--evidence',required=True,type=Path);args=parser.parse_args()
    args.evidence.mkdir(parents=True,exist_ok=False);home=ROOT/'.local/deployment-stop-probes'/('identity-'+uuid.uuid4().hex)
    home.mkdir(parents=True,exist_ok=False);protect_directory(home);driver=home/'probe.ps1';driver.write_bytes(DRIVER.encode('utf-8'))
    sources=[Path(__file__),ROOT/'tools/windows/Invoke-RackClickPrivateDeployment.ps1',ROOT/'tools/windows/RackClick.Deployment.ps1']
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();guards={p.relative_to(ROOT).as_posix():sha(p) for p in sources}
    for p in sources:(args.evidence/(p.name+'.SOURCE.txt')).write_bytes(p.read_bytes())
    (args.evidence/'executed-probe.ps1').write_bytes(driver.read_bytes())
    command=[str(Path(os.environ['SystemRoot'])/'System32/WindowsPowerShell/v1.0/powershell.exe'),'-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(driver),'-OperatorPath',str(sources[1]),'-ReaderPath',str(sources[2]),'-RootPath',str(home)]
    started=time.monotonic();p=subprocess.run(command,capture_output=True,timeout=30,creationflags=subprocess.CREATE_NO_WINDOW)
    report=dict(utc=datetime.now(timezone.utc).isoformat(),platform=platform.platform(),exitCode=p.returncode,stderrEmpty=not p.stderr,
                seconds=round(time.monotonic()-started,3),sources=guards,inputsUnchanged=all(sha(ROOT/n)==v for n,v in guards.items()),fixture=str(home))
    if p.returncode==0:
        try:report['report']=json.loads(p.stdout.decode('utf-8-sig'))
        except (ValueError,UnicodeError):report['outputParseFailed']=True
    if p.returncode or p.stderr:(home/'private-error.log').write_bytes(p.stdout+p.stderr)
    (args.evidence/'result.json').write_bytes((json.dumps(report,indent=2)+'\n').encode('utf-8'))
    good=p.returncode==0 and not p.stderr and report['inputsUnchanged'] and report.get('report',{}).get('valid')
    print(json.dumps(dict(passed=bool(good),seconds=report['seconds'],exitCode=p.returncode,inputsUnchanged=report['inputsUnchanged'])))
    return 0 if good else 1

if __name__=='__main__':raise SystemExit(main())
