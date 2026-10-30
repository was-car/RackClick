"""PS5.1 listener snapshots distinguish closed and bound ports without PG/app."""
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

DRIVER=r'''param([string]$OperatorPath,[string]$ReaderPath)
$inputs=@{operator=$OperatorPath;reader=$ReaderPath}
. $inputs.reader
$tokens=$null;$errors=$null;$ast=[Management.Automation.Language.Parser]::ParseFile($inputs.operator,[ref]$tokens,[ref]$errors)
if($errors.Count -ne 0){throw 'operator_parse_failed'}
$definition=@($ast.FindAll({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -ceq 'Test-DeploymentPortClosed'},$true))
if($definition.Count -ne 1){throw 'actual_function_missing'}
Invoke-Expression $definition[0].Extent.Text
$listener=New-Object Net.Sockets.TcpListener([Net.IPAddress]::Loopback,0)
$listener6=$null
try {
    $listener.Start();$port=$listener.LocalEndpoint.Port
    $openRejected=-not (Test-DeploymentPortClosed $port)
    $listener.Stop()
    $closedAccepted=Test-DeploymentPortClosed $port
    $v6Checked=$false;$v6Open=$false;$v6Closed=$false
    if([Net.Sockets.Socket]::OSSupportsIPv6){
        $listener6=New-Object Net.Sockets.TcpListener([Net.IPAddress]::IPv6Any,0)
        $listener6.Start();$port6=$listener6.LocalEndpoint.Port
        $v6Open=-not(Test-DeploymentPortClosed $port6);$listener6.Stop();$v6Closed=Test-DeploymentPortClosed $port6;$v6Checked=$true
    }
    # Diagnose, without asserting a timing assumption, the old 500ms connect probe.
    $client=New-Object Net.Sockets.TcpClient;$oldCompleted=$false;$refused=$false;$watch=[Diagnostics.Stopwatch]::StartNew()
    try {
        $pending=$client.ConnectAsync('127.0.0.1',$port)
        try{$oldCompleted=$pending.Wait(500)}catch{$oldCompleted=$true}
        try{$null=$pending.Wait(3500)}catch{
            $cause=$_.Exception;while($null -ne $cause.InnerException){$cause=$cause.InnerException}
            $refused=$cause -is [Net.Sockets.SocketException] -and $cause.SocketErrorCode -eq [Net.Sockets.SocketError]::ConnectionRefused
        }
    }finally{$client.Dispose()}
    if(-not $openRejected -or -not $closedAccepted -or ($v6Checked -and (-not $v6Open -or -not $v6Closed))){throw 'listener_snapshot_failed'}
    @{valid=$true;openIpv4Rejected=$openRejected;closedIpv4Accepted=$closedAccepted;ipv6Checked=$v6Checked;openIpv6WildcardRejected=$v6Open;closedIpv6Accepted=$v6Closed;oldConnectCompletedWithin500ms=$oldCompleted;oldConnectEventuallyRefused=$refused;oldConnectMilliseconds=$watch.ElapsedMilliseconds;databaseQueries=0;applicationExecutions=0;serviceOperations=0}|ConvertTo-Json -Compress
}finally{$listener.Stop();if($null -ne $listener6){$listener6.Stop()}}
'''

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--evidence',type=Path,required=True);args=parser.parse_args();args.evidence.mkdir(parents=True,exist_ok=False)
    home=ROOT/'.local/deployment-stop-probes'/('ports-'+uuid.uuid4().hex);home.mkdir(parents=True,exist_ok=False);protect_directory(home)
    driver=home/'probe.ps1';driver.write_bytes(DRIVER.encode('utf-8'))
    files=[Path(__file__),ROOT/'tools/windows/Invoke-RackClickPrivateDeployment.ps1',ROOT/'tools/windows/RackClick.Deployment.ps1']
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();guards={p.relative_to(ROOT).as_posix():sha(p) for p in files}
    for p in files:(args.evidence/(p.name+'.SOURCE.txt')).write_bytes(p.read_bytes())
    (args.evidence/'executed-probe.ps1').write_bytes(driver.read_bytes())
    command=[str(Path(os.environ['SystemRoot'])/'System32/WindowsPowerShell/v1.0/powershell.exe'),'-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(driver),'-OperatorPath',str(files[1]),'-ReaderPath',str(files[2])]
    start=time.monotonic();p=subprocess.run(command,capture_output=True,timeout=30,creationflags=subprocess.CREATE_NO_WINDOW)
    d=dict(utc=datetime.now(timezone.utc).isoformat(),platform=platform.platform(),exitCode=p.returncode,stderrEmpty=not p.stderr,
           seconds=round(time.monotonic()-start,3),sources=guards,inputsUnchanged=all(sha(ROOT/n)==v for n,v in guards.items()),fixture=str(home))
    if p.returncode==0:
        try:d['report']=json.loads(p.stdout.decode('utf-8-sig'))
        except(ValueError,UnicodeError):d['outputParseFailed']=True
    if p.returncode or p.stderr:(home/'private-error.log').write_bytes(p.stdout+p.stderr)
    (args.evidence/'result.json').write_bytes((json.dumps(d,indent=2)+'\n').encode('utf-8'))
    good=p.returncode==0 and not p.stderr and d['inputsUnchanged'] and d.get('report',{}).get('valid')
    print(json.dumps(dict(passed=bool(good),seconds=d['seconds'],exitCode=p.returncode,inputsUnchanged=d['inputsUnchanged'])))
    return 0 if good else 1

if __name__=='__main__':raise SystemExit(main())
