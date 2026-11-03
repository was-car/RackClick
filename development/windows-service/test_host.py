"""Native Windows fixtures, private isolated directory; no SCM, elevation or PostgreSQL."""
import hashlib, json, os, pathlib, subprocess, tempfile, time, sys
focus = '--focus-immediate' in sys.argv

ROOT = pathlib.Path(__file__).resolve().parents[2]
HOST = ROOT / 'development/windows-service/bin/Debug/net10.0-windows/RackClick.WindowsService.dll'
DOTNET = ROOT / '.local/dotnet-10.0.401/dotnet.exe'
work = pathlib.Path(tempfile.mkdtemp(prefix='rackclick-service-', dir=ROOT / '.local'))
sid = subprocess.check_output(['whoami', '/user', '/fo', 'csv', '/nh'], text=True).strip().split(',')[1].strip('"')

def private(path):
    subprocess.run(['icacls', str(path), '/inheritance:r', '/grant:r', f'*{sid}:(F)', '*S-1-5-18:(F)'], check=True, capture_output=True)
    command = r"$env:PSModulePath=$PSHOME+'\Modules;'+$env:PSModulePath; (Get-Acl -LiteralPath $env:RACKCLICK_FIXTURE_PATH).Access | ForEach-Object {$_.IdentityReference.Translate([Security.Principal.SecurityIdentifier]).Value}"
    identities = subprocess.check_output(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', command], env=dict(os.environ, RACKCLICK_FIXTURE_PATH=str(path)), text=True).splitlines()
    for other in set(identities) - {sid, 'S-1-5-18'}:
        subprocess.run(['icacls', str(path), '/remove:g', '*'+other], check=True, capture_output=True)

script = work / 'runtime.ps1'
manifest = work / 'manifest.json'
config = work / 'host.json'
logs = work / 'logs'
logs.mkdir()
manifest.write_text('{}', encoding='utf-8')
script.write_text('param($Operation,$ManifestPath,$ExpectedManifestSha256,$RunId)\nSet-Content -LiteralPath (Join-Path $PSScriptRoot "started") -Value $RunId\nexit 0\n', encoding='utf-8')
data = dict(schemaVersion=1, serviceName='RackClick', runtimeScriptPath=str(script), serverManifestPath=str(manifest), serverManifestSha256=hashlib.sha256(manifest.read_bytes()).hexdigest(), logDirectory=str(logs))

def write_config(value):
    config.write_text(json.dumps(value), encoding='utf-8')
    private(config)

for path in [work, script, manifest, logs]: private(path)
results = []

def case(name, value, console=True):
    if focus: return
    write_config(value)
    command = [str(DOTNET), str(HOST), '--config', str(config)] + (['--console'] if console else [])
    result = subprocess.run(command, capture_output=True, text=True, timeout=20)
    assert result.returncode != 0, (name, result.stdout, result.stderr)
    results.append(dict(case=name, exitCode=result.returncode, expected='failure', passed=True))

case('early_runtime_exit_is_failure', data)
if not focus: assert (work / 'started').exists(), 'runtime did not execute; early-exit test invalid'
case('SCM_required_without_console', data, False)
case('unknown_config_field', dict(data, unknown=True))
case('unsupported_schema', dict(data, schemaVersion=2))
case('manifest_hash_mismatch', dict(data, serverManifestSha256='0'*64))
subprocess.run(['icacls', str(script), '/grant', '*S-1-5-32-545:(R)'], capture_output=True, check=True)
case('public_runtime_acl_rejected', data)
private(script)
for fail_stop in ([] if focus else [False, True]):
    marker = work / ('failed-started' if fail_stop else 'normal-started')
    stopped = work / ('failed-stopped' if fail_stop else 'normal-stopped')
    script.write_text('param($Operation,$ManifestPath,$ExpectedManifestSha256,$RunId)\n' +
        f'$marker = "{marker}"\n$stopped = "{stopped}"\n' +
        ('if ($Operation -eq "Stop") { exit 7 }\n' if fail_stop else 'if ($Operation -eq "Stop") { Set-Content -LiteralPath $stopped -Value $RunId; exit 0 }\n') +
        'Set-Content -LiteralPath $marker -Value $RunId\nwhile (-not (Test-Path -LiteralPath $stopped)) { Start-Sleep -Milliseconds 100 }\nif ((Get-Content -LiteralPath $stopped) -ne $RunId) { exit 8 }\nexit 0\n', encoding='utf-8')
    write_config(data)
    proc = subprocess.Popen([str(DOTNET), str(HOST), '--config', str(config), '--console'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    deadline = time.monotonic() + 15
    while not marker.exists() and time.monotonic() < deadline and proc.poll() is None: time.sleep(.05)
    assert marker.exists(), 'runtime Start not reached'
    try:
        out, err = proc.communicate('stop\n', timeout=15)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.communicate(timeout=5)
        raise
    assert proc.returncode == (1 if fail_stop else 0), (proc.returncode, out, err)
    results.append(dict(case='failed_stop_is_failure' if fail_stop else 'graceful_stop_same_runId', exitCode=proc.returncode, passed=True))
    if fail_stop:
        output = subprocess.check_output(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', "@(Get-CimInstance Win32_Process | Where-Object {$_.Name -eq 'powershell.exe' -and $_.CommandLine -like ('*'+$env:RACKCLICK_FIXTURE_PATH+'*')}).Count"], env=dict(os.environ, RACKCLICK_FIXTURE_PATH=str(work)), text=True)
        assert output.strip() == '0', 'owned runtime remained after failed Stop'
link = work / 'junction'
subprocess.run(['cmd.exe', '/c', 'mklink', '/J', str(link), str(logs)], check=True, capture_output=True)
case('junction_log_path_rejected', dict(data, logDirectory=str(link)))
script.write_text('param($Operation,$ManifestPath,$ExpectedManifestSha256,$RunId)\nif ($Operation -eq "Stop") { Set-Content -LiteralPath (Join-Path $PSScriptRoot "immediate-stopped") -Value $RunId; exit 0 }; while (-not(Test-Path -LiteralPath (Join-Path $PSScriptRoot "immediate-stopped"))) { Start-Sleep -Milliseconds 50 }; exit 0\n', encoding='utf-8')
for iteration in range(5):
    marker = work / 'immediate-stopped'
    if marker.exists(): marker.unlink()
    write_config(data)
    proc = subprocess.Popen([str(DOTNET), str(HOST), '--config', str(config), '--console'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        out, err = proc.communicate('stop\n', timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill(); proc.communicate(timeout=5); raise
    assert proc.returncode == 0, (proc.returncode, out, err)
results.append(dict(case='immediate_stop_no_hang_five_iterations', passed=True))
for log in logs.glob('host-*.jsonl'):
    rows = [json.loads(line) for line in log.read_text().splitlines()]
    assert len({row['runId'] for row in rows}) == 1
    assert all(set(row) == {'timestamp','code','runId','exitCode'} for row in rows)
if not focus: assert len(list(logs.glob('host-*.jsonl'))) >= 3
report = dict(platform='Windows', scmInstalled=False, postgresExecuted=False, fixturePath=str(work), cases=results, limits=['SCM start/stop under real standard service account not executed'])
(work / 'result.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report, indent=2))
