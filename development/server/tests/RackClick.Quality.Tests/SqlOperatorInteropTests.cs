using System.Diagnostics;
using System.Collections;
using System.Reflection;
using System.Runtime.Versioning;
using System.Security.AccessControl;
using System.Security.Principal;
using System.Text;
using System.Text.Json;
using Microsoft.Extensions.Configuration.EnvironmentVariables;
using Npgsql;
using RackClick.Server;
using Xunit;

namespace RackClick.Quality.Tests;

[SupportedOSPlatform("windows")]
public sealed class SqlOperatorInteropTests
{
    [Theory]
    [InlineData("CUSTOMCONNSTR_RackClick")]
    [InlineData("POSTGRESQLCONNSTR_RackClick")]
    public void TheRealDotnetProviderCannotRecoverAnAmbientAliasAfterTheOperatorClearsIt(string alias)
    {
        var raw = Invoke("environment", Guid.NewGuid(), "S-1-5-32-545", alias);
        var values = JsonSerializer.Deserialize<Dictionary<string, string?>>(raw)!;
        var table = new Hashtable();
        foreach (var (key, value) in values) table.Add(key, value);
        var provider = new EnvironmentVariablesConfigurationProvider();
        var load = typeof(EnvironmentVariablesConfigurationProvider).GetMethod("Load", BindingFlags.NonPublic | BindingFlags.Instance,
            null, [typeof(IDictionary)], null)!;
        Assert.NotNull(load);
        load.Invoke(provider, [table]);
        provider.TryGet("ConnectionStrings:RackClick", out var connection);
        Assert.Null(connection);
        Assert.True(provider.TryGet("SqlSecret:Enabled", out var enabled));
        Assert.Equal("true", enabled);
    }
    [Fact]
    public void PowershellFrameworkProducesTheSameEnvelopeContractThatDotnetConsumes()
    {
        var id = Guid.NewGuid();
        var sid = new SecurityIdentifier(WellKnownSidType.BuiltinUsersSid, null);
        var connection = new NpgsqlConnectionStringBuilder { Host = "127.0.0.1", Database = "interop_db", Username = "interop_runtime", Password = "synthetic-漢字;quote=\"!" }.ConnectionString;
        var raw = Invoke("protect", id, sid.Value, connection);
        var bytes = Convert.FromBase64String(raw);
        var value = new NpgsqlConnectionStringBuilder(WindowsSqlSecret.Open(bytes, id, sid, "interop_db", "interop_runtime"));
        Assert.True(value.Password == new NpgsqlConnectionStringBuilder(connection).Password);
        Assert.Equal("interop_runtime", value.Username);
        Assert.False(value.PersistSecurityInfo);
    }

    [Fact]
    public void DotnetProducesTheSameEnvelopeContractThatThePrivatePowershellCodecConsumes()
    {
        var id = Guid.NewGuid();
        var sid = new SecurityIdentifier(WellKnownSidType.BuiltinUsersSid, null);
        var connection = new NpgsqlConnectionStringBuilder { Host = "127.0.0.1", Database = "interop_db", Username = "interop_runtime", Password = "synthetic-Only;quoted=\"!" }.ConnectionString;
        var bytes = WindowsSqlSecret.ProtectForProvisioning(connection, id, sid, "interop_db", "interop_runtime");
        // The probe returns only booleans/metadata; plaintext never goes to stdout.
        var raw = Invoke("open", id, sid.Value, Convert.ToBase64String(bytes));
        var result = JsonSerializer.Deserialize<JsonElement>(raw);
        Assert.True(result.GetProperty("valid").GetBoolean());
        Assert.Equal("interop_runtime", result.GetProperty("user").GetString());
        Assert.False(result.GetProperty("details").GetBoolean());
    }

    [Fact]
    public void TheCompleteProtectedViewerAcceptsTheDotnetNormalizedConnection()
    {
        var id = Guid.NewGuid();
        var sid = new SecurityIdentifier(WellKnownSidType.BuiltinUsersSid, null);
        var connection = new NpgsqlConnectionStringBuilder
        {
            Host = "127.0.0.1", Port = 55441, Database = "interop_db", Username = "interop_runtime",
            Password = new string('a', 64), SslMode = SslMode.Disable, Timeout = 5, CommandTimeout = 15,
        }.ConnectionString;
        var bytes = WindowsSqlSecret.ProtectForProvisioning(connection, id, sid, "interop_db", "interop_runtime");
        var raw = Invoke("viewer", id, sid.Value, Convert.ToBase64String(bytes));
        var result = JsonSerializer.Deserialize<JsonElement>(raw);
        Assert.True(result.GetProperty("valid").GetBoolean());
        Assert.Equal("interop_runtime", result.GetProperty("user").GetString());
    }

    private static string Invoke(string mode, Guid id, string sid, string material)
    {
        var module = Environment.GetEnvironmentVariable("RACKCLICK_SQL_OPERATOR_MODULE");
        Assert.SkipWhen(string.IsNullOrEmpty(module), "source operator path supplied by the isolated runner");
        Assert.True(File.Exists(module));
        var parent = Path.GetFullPath(Path.Combine(Path.GetTempPath(), "rackclick-sql-interop"));
        var folder = Path.Combine(parent, Guid.NewGuid().ToString("N"));
        var security = new DirectorySecurity();
        security.SetAccessRuleProtection(true, false);
        security.AddAccessRule(new FileSystemAccessRule(WindowsIdentity.GetCurrent().User!, FileSystemRights.FullControl,
            InheritanceFlags.ContainerInherit | InheritanceFlags.ObjectInherit, PropagationFlags.None, AccessControlType.Allow));
        FileSystemAclExtensions.CreateDirectory(security, folder);
        try
        {
            var script = Path.Combine(folder, "probe.ps1");
            File.WriteAllText(script, """
                $ErrorActionPreference='Stop'
                [Console]::InputEncoding=New-Object Text.UTF8Encoding($false)
                [Console]::OutputEncoding=New-Object Text.UTF8Encoding($false)
                $v=[Console]::In.ReadToEnd()|ConvertFrom-Json
                . $v.module
                if($v.mode -ceq 'protect'){
                    $bytes=Protect-SqlRuntimeConnection $v.material $v.id $v.sid 'interop_db' 'interop_runtime'
                    [Console]::Write([Convert]::ToBase64String($bytes))
                }elseif($v.mode -ceq 'environment'){
                    $descriptor=@{schemaVersion=2;ciphertextSha256=('a'*64);sqlSecret=@{enabled=$true;instancesRoot='C:\synthetic\sql-security';installationId=$v.id;database='interop_db';runtimeUser='interop_runtime'}}
                    $d=Get-SqlRuntimeDefinition $descriptor 'C:\synthetic' $v.id 'interop_db' 'interop_runtime'
                    $e=@{};$e[$v.material]='synthetic-poison';Set-SqlRuntimeEnvironment $e $d
                    [Console]::Write(($e|ConvertTo-Json -Compress))
                }elseif($v.mode -ceq 'viewer'){
                    . (Join-Path (Split-Path $v.module -Parent) 'server-install\Show-RackClickDatabaseAccess.ps1') -FunctionsOnly
                    $cipher=[Convert]::FromBase64String($v.material)
                    $sha=[Security.Cryptography.SHA256]::Create();try{$digest=([BitConverter]::ToString($sha.ComputeHash($cipher))).Replace('-','').ToLowerInvariant()}finally{$sha.Dispose()}
                    $descriptor=@{schemaVersion=2;ciphertextSha256=$digest;sqlSecret=@{enabled=$true;instancesRoot='C:\synthetic\sql-security';installationId=$v.id;database='interop_db';runtimeUser='interop_runtime'}}
                    $bytes=[Text.Encoding]::UTF8.GetBytes(($descriptor|ConvertTo-Json -Depth 5 -Compress))
                    $m=[pscustomobject]@{id=$v.id;rootPath='C:\synthetic';database='interop_db';runtime='interop_runtime';postgresPort=55441;secretFiles=[pscustomobject]@{'runtime.json'=(Get-RcDatabaseAccessHash $bytes)}}
                    $value=Read-RcDatabaseAccessRuntime $bytes $m $cipher $v.sid
                    [Console]::Write((@{valid=($value.password-ceq('a'*64));user=$value.username}|ConvertTo-Json -Compress))
                }else{
                    $text=Unprotect-SqlRuntimeConnection ([Convert]::FromBase64String($v.material)) $v.id $v.sid 'interop_db' 'interop_runtime'
                    $b=New-Object Data.Common.DbConnectionStringBuilder;$b.set_ConnectionString($text)
                    [Console]::Write((@{valid=([string]$b['Database']-ceq'interop_db'-and-not[string]::IsNullOrEmpty([string]$b['Password']));user=[string]$b['Username'];details=([bool]::Parse([string]$b['Include Error Detail']))}|ConvertTo-Json -Compress))
                }
                """, new UTF8Encoding(false));
            var executable = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Windows), "System32/WindowsPowerShell/v1.0/powershell.exe");
            var start = new ProcessStartInfo(executable) { WorkingDirectory = folder, UseShellExecute = false, CreateNoWindow = true,
                RedirectStandardInput = true, RedirectStandardOutput = true, RedirectStandardError = true,
                StandardInputEncoding = new UTF8Encoding(false), StandardOutputEncoding = Encoding.UTF8, StandardErrorEncoding = Encoding.UTF8 };
            foreach (var arg in new[] { "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", script }) start.ArgumentList.Add(arg);
            foreach (var key in start.Environment.Keys.ToArray())
                if (key.StartsWith("COR_", StringComparison.OrdinalIgnoreCase) || key.StartsWith("CORECLR_", StringComparison.OrdinalIgnoreCase) || key.StartsWith("COMPlus_", StringComparison.OrdinalIgnoreCase) || key.StartsWith("DOTNET_", StringComparison.OrdinalIgnoreCase)) start.Environment.Remove(key);
            using var process = Process.Start(start) ?? throw new InvalidOperationException("probe startup failed");
            var output = process.StandardOutput.ReadToEndAsync(); var errors = process.StandardError.ReadToEndAsync();
            process.StandardInput.Write(JsonSerializer.Serialize(new { mode, id = id.ToString("D"), sid, module, material })); process.StandardInput.Close();
            if (!process.WaitForExit(TimeSpan.FromSeconds(20))) { process.Kill(entireProcessTree: true); throw new InvalidOperationException("probe timeout"); }
            Assert.True(process.ExitCode == 0, "private PowerShell interop process rejected the request");
            Assert.True(string.IsNullOrWhiteSpace(errors.Result), "unexpected stderr; no raw contents disclosed");
            return output.Result.Trim();
        }
        finally
        {
            if (!Path.GetFullPath(folder).StartsWith(parent + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase)) throw new InvalidOperationException("unsafe fixture cleanup");
            Directory.Delete(folder, recursive: true);
        }
    }
}
