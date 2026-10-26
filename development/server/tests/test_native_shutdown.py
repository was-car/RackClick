"""Focal Windows tests of the production NativeShutdown source; no PostgreSQL.

One private fixture build, no NuGet packages, no product routes or existing QA.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import http.client
import json
import os
from pathlib import Path
import platform
import secrets
import subprocess
import time
import unittest
import uuid

from pg_support import WORKSPACE, free_port, protect_directory, toolchain

ROOT = WORKSPACE
SOURCE = ROOT/'development/server/src/RackClick.Server/NativeShutdown.cs'
PROGRAM = ROOT/'development/server/src/RackClick.Server/Program.cs'
GLOBAL = ROOT/'development/server/global.json'
NO_WINDOW = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
write = lambda path, data: path.write_bytes((json.dumps(data, ensure_ascii=False, indent=2)+'\n').encode('utf-8'))

PROJECT = '''<Project Sdk="Microsoft.NET.Sdk.Web"><PropertyGroup><TargetFramework>net10.0</TargetFramework><Nullable>enable</Nullable><ImplicitUsings>enable</ImplicitUsings><TreatWarningsAsErrors>true</TreatWarningsAsErrors><Deterministic>true</Deterministic></PropertyGroup></Project>'''

FIXTURE = r'''
using System.IO.Pipes;
using System.Text.Json;
using RackClick.Server;

if (args[0] == "client")
{
    using var deadline = new CancellationTokenSource(TimeSpan.FromSeconds(10));
    await using var pipe = new NamedPipeClientStream(".", args[1], PipeDirection.InOut,
        PipeOptions.Asynchronous | PipeOptions.CurrentUserOnly);
    await pipe.ConnectAsync(deadline.Token);
    if (args[2] == "eof") { Console.WriteLine("{\"closed\":true}"); return; }
    try
    {
        if (args[2] != "idle")
        {
            using var request = new MemoryStream();
            await Console.OpenStandardInput().CopyToAsync(request, deadline.Token);
            await pipe.WriteAsync(request.ToArray(), deadline.Token);
            await pipe.FlushAsync(deadline.Token);
            if (args[2] == "delayed") await Task.Delay(500, deadline.Token);
        }
        using var response = new MemoryStream();
        byte[] next = new byte[1];
        while (response.Length < 128 && await pipe.ReadAsync(next, deadline.Token) != 0)
        {
            if (next[0] == 10) break;
            response.WriteByte(next[0]);
        }
        Console.WriteLine(response.Length == 0 ? "{\"closed\":true}" : System.Text.Encoding.ASCII.GetString(response.ToArray()));
        if (args[2] == "no-close") await Task.Delay(4000, deadline.Token);
        if (args[2] == "extra") await pipe.WriteAsync(new byte[] { 1 }, deadline.Token);
    }
    catch (IOException) { Console.WriteLine("{\"closed\":true}"); }
    return;
}

if (args[0] == "config")
{
    var values = JsonSerializer.Deserialize<Dictionary<string, string?>>(await Console.In.ReadToEndAsync())!;
    var configuration = new ConfigurationBuilder().AddInMemoryCollection(values).Build();
    var services = new ServiceCollection();
    try
    {
        services.AddNativeShutdown(configuration);
        Console.WriteLine(JsonSerializer.Serialize(new { accepted = true, registered = services.Any(x => x.ServiceType == typeof(IHostedService)) }));
    }
    catch (InvalidOperationException)
    {
        Console.WriteLine("{\"accepted\":false,\"error\":\"configuration_invalid\"}");
        Environment.ExitCode = 2;
    }
    return;
}

var builder = WebApplication.CreateBuilder(Array.Empty<string>());
builder.Logging.ClearProviders();
builder.WebHost.UseUrls(args[1]);
builder.Services.AddNativeShutdown(builder.Configuration);
var app = builder.Build();
app.MapGet("/live", () => Results.Text("alive"));
app.MapGet("/hold", async () =>
{
    File.WriteAllText(args[2], "entered");
    await Task.Delay(2000);
    return Results.Text("completed-request");
});
await app.RunAsync();
'''


class NativeShutdownTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        assert os.name == 'nt', 'These are Windows-native named-pipe tests'
        cls.guards = {p.relative_to(ROOT).as_posix(): sha(p) for p in (SOURCE, PROGRAM, GLOBAL, Path(__file__))}
        cls.home = ROOT/'.local/native-shutdown-fixtures'/('backend248-'+uuid.uuid4().hex)
        cls.home.mkdir(parents=True, exist_ok=False)
        protect_directory(cls.home)
        cls.dotnet = toolchain()['dotnet']; cls.hosts = []; cls.checks = []
        cls.clean = False; cls.unchanged = False
        (cls.home/'NativeShutdown.cs').write_bytes(SOURCE.read_bytes())
        (cls.home/'Program.cs').write_bytes(FIXTURE.encode('utf-8'))
        (cls.home/'Fixture.csproj').write_bytes(PROJECT.encode('utf-8'))
        (cls.home/'global.json').write_bytes(GLOBAL.read_bytes())
        config = cls.home/'NuGet.Config'
        config.write_bytes(b'<configuration><packageSources><clear/></packageSources></configuration>')
        command = [str(cls.dotnet), 'build', str(cls.home/'Fixture.csproj'), '--configuration', 'Release', '--nologo',
                   '-p:RestoreConfigFile='+str(config)]
        started = time.monotonic()
        build = subprocess.run(command, cwd=cls.home, capture_output=True, timeout=120,
                               creationflags=NO_WINDOW)
        (cls.home/'build-private.log').write_bytes(build.stdout+build.stderr)
        cls.build = dict(exitCode=build.returncode, seconds=round(time.monotonic()-started, 3),
                         builds=1, packageReferences=0, productApplicationBuilds=0,
                         sourceCopySha256=sha(cls.home/'NativeShutdown.cs'), sourceExact=sha(SOURCE)==sha(cls.home/'NativeShutdown.cs'))
        assert build.returncode == 0, 'Fixture compilation failed; raw log remains private'
        assert cls.build['sourceExact']
        cls.dll = cls.home/'bin/Release/net10.0/Fixture.dll'

    @classmethod
    def tearDownClass(cls):
        unexpected = []
        for item in cls.hosts:
            if item['process'].poll() is None:
                unexpected.append(item['name'])
                item['process'].terminate(); item['process'].wait(timeout=10)
            item['log'].close()
        cls.clean = not unexpected
        cls.unchanged = all(sha(ROOT/name)==value for name, value in cls.guards.items())
        assert cls.clean and cls.unchanged, 'Unexpected surviving fixture or changed source'

    def invoke(self, mode, *, values=None, pipe=None, request=b'', client_mode='payload'):
        args = ['config'] if mode == 'config' else ['client', pipe, client_mode]
        body = json.dumps(values).encode('utf-8') if mode == 'config' else request
        result = subprocess.run([str(self.dotnet), str(self.dll), *args], input=body, capture_output=True,
                                cwd=self.home, timeout=20, creationflags=NO_WINDOW)
        self.assertFalse(result.stderr, 'Fixture wrote stderr; raw content is not exported')
        response = json.loads(result.stdout)
        self.assertIn(result.returncode, (0, 2))
        return result.returncode, response

    def config(self, pipe=None, token=None, *, absent=()):
        return {key: value for key, value in {'RackClick:ShutdownPipe': pipe,
                'RackClick:ShutdownToken': token}.items() if key not in absent}

    def environment(self, pipe, token):
        result = {key: value for key, value in os.environ.items() if not key.upper().startswith(
            ('RACKCLICK', 'ASPNETCORE_', 'DOTNET_', 'KESTREL', 'URLS', 'HTTP_PORTS', 'HTTPS_PORTS'))}
        result.update(RackClick__ShutdownPipe=pipe, RackClick__ShutdownToken=token,
                      DOTNET_CLI_TELEMETRY_OPTOUT='1')
        return result

    def start(self):
        name = uuid.uuid4().hex; pipe = 'rc-shutdown-'+name; token = secrets.token_hex(32)
        origin = 'http://127.0.0.1:'+str(free_port()); marker = self.home/(name+'.entered')
        log = (self.home/(name+'.private.log')).open('xb')
        process = subprocess.Popen([str(self.dotnet), str(self.dll), 'host', origin, str(marker)],
            env=self.environment(pipe, token), stdout=log, stderr=log, cwd=self.home, creationflags=NO_WINDOW)
        item = dict(process=process, pipe=pipe, token=token, origin=origin, marker=marker, log=log, name=name)
        self.hosts.append(item)
        deadline = time.monotonic()+15
        while time.monotonic()<deadline:
            self.assertIsNone(process.poll(), 'Fixture stopped before readiness; private raw log retained')
            try:
                if self.http(item, '/live') == (200, b'alive'): return item
            except OSError: pass
            time.sleep(.05)
        self.fail('Fixture readiness timed out')

    @staticmethod
    def http(item, path):
        connection = http.client.HTTPConnection('127.0.0.1', int(item['origin'].rsplit(':', 1)[1]), timeout=10)
        try:
            connection.request('GET', path); result = connection.getresponse()
            return result.status, result.read()
        finally: connection.close()

    def send(self, item, payload=None, mode='payload'):
        if payload is None:
            payload = (json.dumps(dict(schemaVersion=1, action='stop', token=item['token']), separators=(',', ':'))+'\n').encode('ascii')
        return self.invoke('client', pipe=item['pipe'], request=payload, client_mode=mode)[1]

    def stop(self, item):
        self.assertEqual(self.send(item), dict(schemaVersion=1, accepted=True))
        self.assertEqual(item['process'].wait(timeout=18), 0)

    def test_01_configuration_is_explicit_and_closed(self):
        pipe = 'rc-shutdown-'+uuid.uuid4().hex; token = secrets.token_hex(32)
        self.assertEqual(self.invoke('config', values={}), (0, dict(accepted=True, registered=False)))
        self.assertEqual(self.invoke('config', values=self.config(pipe, token)), (0, dict(accepted=True, registered=True)))
        invalid = [self.config(pipe, token, absent=('RackClick:ShutdownToken',)),
                   self.config(pipe, token, absent=('RackClick:ShutdownPipe',)),
                   self.config('', token), self.config(pipe, ''), self.config(pipe.upper(), token),
                   self.config('rc-shutdown-'+'0'*32, token), self.config(pipe, 'g'*64),
                   self.config(pipe, 'a'*63), self.config(pipe+'/', token)]
        for values in invalid:
            self.assertEqual(self.invoke('config', values=values), (2, dict(accepted=False, error='configuration_invalid')))
        self.checks.append(dict(case=self._testMethodName, passed=True, invalidConfigurations=len(invalid), absentIsOptOut=True))

    def test_02_rejected_clients_do_not_stop_or_poison_host(self):
        item = self.start()
        self.assertEqual(self.send(item, mode='eof'), dict(closed=True))
        base = dict(schemaVersion=1, action='stop', token=item['token'])
        values = [b'not-json\n', b'{}\n', b'[]\n', b'\xff\n', b'{}\r\n',
                  (json.dumps(dict(base, token='0'*64))+'\n').encode('ascii'),
                  (json.dumps(dict(base, unknown=True))+'\n').encode('ascii'),
                  (json.dumps(base)[:-1]+',"schemaVersion":1}\n').encode('ascii')]
        for value in values:
            response = self.send(item, value)
            self.assertIn(response, (dict(schemaVersion=1, accepted=False), dict(closed=True)))
            self.assertEqual(self.http(item, '/live'), (200, b'alive'))
        self.stop(item)
        self.checks.append(dict(case=self._testMethodName, passed=True, rejectedPayloads=len(values), disconnectIgnored=True, validStopAfterRejections=True))

    def test_03_size_boundary_and_idle_timeout_release_channel(self):
        item = self.start()
        valid = json.dumps(dict(schemaVersion=1, action='stop', token=item['token']), separators=(',', ':')).encode('ascii')
        self.assertLess(len(valid), 255)
        oversized = valid+b' '*(256-len(valid))+b'\n'
        self.assertEqual(len(oversized), 257)
        self.assertIn(self.send(item, oversized), (dict(schemaVersion=1, accepted=False), dict(closed=True)))
        self.assertEqual(self.http(item, '/live'), (200, b'alive'))
        started = time.monotonic()
        self.assertEqual(self.send(item, mode='idle'), dict(closed=True))
        elapsed = time.monotonic()-started
        self.assertGreaterEqual(elapsed, 2.5); self.assertLess(elapsed, 7)
        self.assertEqual(self.http(item, '/live'), (200, b'alive'))
        self.assertEqual(self.send(item, mode='extra'), dict(schemaVersion=1, accepted=True))
        self.assertEqual(self.http(item, '/live'), (200, b'alive'))
        self.assertEqual(self.send(item, mode='no-close'), dict(schemaVersion=1, accepted=True))
        self.assertEqual(self.http(item, '/live'), (200, b'alive'))
        self.assertEqual(self.send(item, valid+b' '*(255-len(valid))+b'\n'), dict(schemaVersion=1, accepted=True))
        self.assertEqual(item['process'].wait(timeout=18), 0)
        self.checks.append(dict(case=self._testMethodName, passed=True, acceptedMaximumBytes=256, rejectedBytes=257,
                                idleSeconds=round(elapsed, 3), validStopAfterTimeout=True,
                                noStopWithoutClientClose=True, extraBytesDoNotStop=True))

    def test_04_ack_precedes_exit_and_inflight_http_drains(self):
        item = self.start()
        with ThreadPoolExecutor(max_workers=1) as executor:
            pending = executor.submit(self.http, item, '/hold')
            deadline = time.monotonic()+5
            while not item['marker'].exists() and time.monotonic()<deadline: time.sleep(.01)
            self.assertTrue(item['marker'].exists(), 'HTTP request never entered handler')
            self.assertEqual(self.send(item, mode='delayed'), dict(schemaVersion=1, accepted=True))
            self.assertIsNone(item['process'].poll(), 'Host exited before its in-flight request completed')
            self.assertEqual(pending.result(timeout=10), (200, b'completed-request'))
        self.assertEqual(item['process'].wait(timeout=18), 0)
        self.checks.append(dict(case=self._testMethodName, passed=True, acknowledgementBeforeExit=True,
                               inFlightHttpStatus=200, inFlightBodyComplete=True, normalExitCode=0,
                               delayedAcknowledgementReaderMilliseconds=500))

    def test_05_duplicate_pipe_cannot_start_an_uncontrolled_host(self):
        item = self.start(); duplicate_port = free_port()
        with (self.home/'duplicate-private.log').open('xb') as log:
            process = subprocess.Popen([str(self.dotnet), str(self.dll), 'host',
                'http://127.0.0.1:'+str(duplicate_port), str(self.home/'duplicate.entered')],
                env=self.environment(item['pipe'], item['token']), stdout=log, stderr=log,
                cwd=self.home, creationflags=NO_WINDOW)
            try:
                self.assertNotEqual(process.wait(timeout=15), 0)
            finally:
                if process.poll() is None: process.terminate(); process.wait(timeout=10)
        self.assertEqual(self.http(item, '/live'), (200, b'alive'))
        self.stop(item)
        self.checks.append(dict(case=self._testMethodName, passed=True, duplicatePipeFailsStartup=True, originalHostUnaffected=True))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--tests', nargs='*', help='Optional focal methods; still one fixture compilation per invocation')
    args = parser.parse_args(); args.evidence.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    suite = (unittest.defaultTestLoader.loadTestsFromNames(args.tests, NativeShutdownTests) if args.tests else
             unittest.defaultTestLoader.loadTestsFromTestCase(NativeShutdownTests))
    with (args.evidence/'tests.log').open('w', encoding='utf-8') as log:
        result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
    cls = NativeShutdownTests
    report = dict(utc=datetime.now(timezone.utc).isoformat(), platform=platform.platform(),
        testsRun=result.testsRun, successful=result.wasSuccessful(), failures=len(result.failures), errors=len(result.errors),
        seconds=round(time.monotonic()-started, 3), sources=getattr(cls, 'guards', {}),
        sourcesUnchanged=getattr(cls, 'unchanged', False), ownedFixturesStopped=getattr(cls, 'clean', False),
        build=getattr(cls, 'build', None), checks=getattr(cls, 'checks', []),
        fixture=str(getattr(cls, 'home', 'not initialized')), actualQaAccessed=False, postgresqlTests=0,
        limits='Fixture HTTP drain of the same NativeShutdown.cs source; no PostgreSQL, service, TLS, installer or final adoption.')
    write(args.evidence/'result.json', report)
    print(json.dumps({key: report[key] for key in ('testsRun', 'successful', 'failures', 'errors', 'seconds', 'sourcesUnchanged', 'ownedFixturesStopped')}))
    return 0 if result.wasSuccessful() and report['sourcesUnchanged'] and report['ownedFixturesStopped'] else 1


if __name__ == '__main__': raise SystemExit(main())
