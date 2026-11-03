using System.Diagnostics;
using System.Runtime.Versioning;
using System.Security.AccessControl;
using System.Security.Principal;
using System.Text;
using Microsoft.Extensions.Configuration;
using Npgsql;
using RackClick.Server;
using Xunit;

namespace RackClick.Quality.Tests;

// DPAPI/ACL are real Windows operations; the internal read seam uses a lab owner
// and the Users group as reader. This is not the effective token of the installed service.
[SupportedOSPlatform("windows")]
public sealed class SqlSecretConnectionTests
{
    private const string Database = "sql_fixture";
    private const string Runtime = "sql_runtime";
    private static readonly SecurityIdentifier Users = new(WellKnownSidType.BuiltinUsersSid, null);
    private static readonly SecurityIdentifier Everyone = new(WellKnownSidType.WorldSid, null);
    private static string Connection(string user = Runtime, string database = Database) => new NpgsqlConnectionStringBuilder
    {
        Host = "127.0.0.1", Port = 55441, Database = database, Username = user,
        Password = "synthetic-Only;quote=\"!日本語", PersistSecurityInfo = true, IncludeErrorDetail = true, LogParameters = true,
    }.ConnectionString;

    [Fact]
    public void AnUnpairedUnicodePasswordHasAConstantProvisioningError()
    {
        var connection = new NpgsqlConnectionStringBuilder(Connection()) { Password = "synthetic-\uD800" }.ConnectionString;
        var error = Assert.Throws<SqlSecretException>(() => WindowsSqlSecret.ProtectForProvisioning(connection, Guid.NewGuid(), Users, Database, Runtime));
        Assert.Equal("sql_secret_connection_invalid", error.Message);
        Assert.Null(error.InnerException);
    }

    [Fact]
    public void DpapiRoundTripPreservesTheRuntimeIdentityButDisablesSensitiveDetails()
    {
        var id = Guid.NewGuid();
        var sealedBytes = WindowsSqlSecret.ProtectForProvisioning(Connection(), id, Users, Database, Runtime);
        var opened = new NpgsqlConnectionStringBuilder(WindowsSqlSecret.Open(sealedBytes, id, Users, Database, Runtime));
        Assert.Equal(Runtime, opened.Username);
        Assert.Equal(Database, opened.Database);
        Assert.True(opened.Password == new NpgsqlConnectionStringBuilder(Connection()).Password);
        Assert.False(opened.PersistSecurityInfo);
        Assert.False(opened.IncludeErrorDetail);
        Assert.False(opened.LogParameters);
        Assert.False(Encoding.UTF8.GetString(sealedBytes).Contains("synthetic-Only", StringComparison.Ordinal));
        Assert.NotEqual(sealedBytes, WindowsSqlSecret.ProtectForProvisioning(Connection(), id, Users, Database, Runtime));
    }

    [Theory]
    [InlineData("installation")]
    [InlineData("reader")]
    [InlineData("database")]
    [InlineData("role")]
    [InlineData("ciphertext")]
    public void AnotherContextOrModifiedCiphertextCannotOpenTheBlob(string change)
    {
        var id = Guid.NewGuid();
        var bytes = WindowsSqlSecret.ProtectForProvisioning(Connection(), id, Users, Database, Runtime);
        if (change == "ciphertext") bytes[^1] ^= 0x40;
        var error = Assert.Throws<SqlSecretException>(() => WindowsSqlSecret.Open(bytes,
            change == "installation" ? Guid.NewGuid() : id, change == "reader" ? Everyone : Users,
            change == "database" ? "other_db" : Database, change == "role" ? "other_role" : Runtime));
        Assert.Equal("sql_secret_decryption_failed", error.Code);
        Assert.Equal(error.Code, error.Message);
        Assert.Null(error.InnerException);
    }

    [Theory]
    [InlineData("header")]
    [InlineData("truncated")]
    [InlineData("oversize")]
    public void InvalidFormatIsRejected(string shape)
    {
        byte[] bytes = shape switch
        {
            "header" => "not-the-sql-format"u8.ToArray(),
            "truncated" => "RCSQL001"u8.ToArray(),
            _ => new byte[WindowsSqlSecret.MaximumFileBytes + 1],
        };
        Assert.Equal("sql_secret_invalid", Assert.Throws<SqlSecretException>(() =>
            WindowsSqlSecret.Open(bytes, Guid.NewGuid(), Users, Database, Runtime)).Code);
    }

    [Theory]
    [InlineData("owner")]
    [InlineData("database")]
    [InlineData("no-password")]
    [InlineData("passfile")]
    [InlineData("malformed")]
    [InlineData("too-long")]
    public void ProvisioningDoesNotAcceptAnotherIdentityOrAnExternalPasswordSource(string shape)
    {
        var builder = new NpgsqlConnectionStringBuilder(Connection());
        switch (shape)
        {
            case "owner": builder.Username = "sql_owner"; break;
            case "database": builder.Database = "other_db"; break;
            case "no-password": builder.Remove("Password"); break;
            case "passfile": builder.Passfile = "C:\\private-test.pgpass"; break;
        }
        var connection = shape == "malformed" ? "password='" : shape == "too-long" ? new string('x', 9000) : builder.ConnectionString;
        Assert.Equal("sql_secret_connection_invalid", Assert.Throws<SqlSecretException>(() =>
            WindowsSqlSecret.ProtectForProvisioning(connection, Guid.NewGuid(), Users, Database, Runtime)).Code);
    }

    [Fact]
    public void LegacyConfigurationIsUnchangedWhenTheOptionIsAbsentOrFalse()
    {
        foreach (var flag in new string?[] { null, "false", "FALSE" })
        {
            var config = Config(new() { ["SqlSecret:Enabled"] = flag, ["ConnectionStrings:RackClick"] = Connection() });
            Assert.True(Connection() == SqlSecretConnection.Resolve(config));
            SqlSecretConnection.RequireSeparateMaintenanceIdentity(config);
        }
    }

    [Theory]
    [InlineData("")]
    [InlineData("yes")]
    [InlineData("1")]
    public void InvalidModeCannotSilentlyUsePlaintext(string flag)
    {
        Assert.Equal("sql_secret_config_invalid", Assert.Throws<SqlSecretException>(() =>
            SqlSecretConnection.Resolve(Config(new() { ["SqlSecret:Enabled"] = flag, ["ConnectionStrings:RackClick"] = Connection() }))).Code);
    }

    [Fact]
    public void ProtectedModeRejectsPlaintextEvenWhenTheStoreIsValid()
    {
        using var f = new Store();
        f.Values["ConnectionStrings:RackClick"] = Connection();
        Assert.Equal("sql_secret_plaintext_conflict", Assert.Throws<SqlSecretException>(() => f.Read()).Code);
    }

    [Fact]
    public void SafeStoreCanBeReadWithoutModifyingItsBytesOrDacl()
    {
        using var f = new Store();
        var bytes = File.ReadAllBytes(f.FilePath);
        var sddl = new FileInfo(f.FilePath).GetAccessControl().GetSecurityDescriptorSddlForm(AccessControlSections.Access | AccessControlSections.Owner);
        var opened = new NpgsqlConnectionStringBuilder(f.Read());
        Assert.Equal(Runtime, opened.Username);
        Assert.Equal(bytes, File.ReadAllBytes(f.FilePath));
        Assert.Equal(sddl, new FileInfo(f.FilePath).GetAccessControl().GetSecurityDescriptorSddlForm(AccessControlSections.Access | AccessControlSections.Owner));
    }

    [Theory]
    [InlineData("file-read")]
    [InlineData("folder-read")]
    [InlineData("reader-write")]
    public void UnsafeRealDaclIsRejectedBeforeUnprotecting(string defect)
    {
        using var f = new Store();
        if (defect == "folder-read")
        {
            var security = new DirectoryInfo(f.Keys).GetAccessControl();
            security.AddAccessRule(new FileSystemAccessRule(Everyone, FileSystemRights.ReadAndExecute, AccessControlType.Allow));
            new DirectoryInfo(f.Keys).SetAccessControl(security);
        }
        else
        {
            var security = new FileInfo(f.FilePath).GetAccessControl();
            security.AddAccessRule(new FileSystemAccessRule(defect == "file-read" ? Everyone : Users,
                defect == "file-read" ? FileSystemRights.Read : FileSystemRights.Write, AccessControlType.Allow));
            new FileInfo(f.FilePath).SetAccessControl(security);
        }
        Assert.Equal("sql_secret_access_unsafe", Assert.Throws<SqlSecretException>(() => f.Read()).Code);
    }

    [Theory]
    [InlineData("missing", "sql_secret_missing")]
    [InlineData("corrupt", "sql_secret_invalid")]
    [InlineData("locked", "sql_secret_unreadable")]
    [InlineData("relative", "sql_secret_config_invalid")]
    [InlineData("nul", "sql_secret_config_invalid")]
    public void StoreFailuresHaveConstantErrorsAndDoNotRegenerate(string defect, string expected)
    {
        using var f = new Store();
        if (defect == "missing") File.Delete(f.FilePath);
        if (defect == "corrupt") File.WriteAllBytes(f.FilePath, "invalid"u8.ToArray());
        if (defect == "relative") f.Values["SqlSecret:InstancesRoot"] = "relative";
        if (defect == "nul") f.Values["SqlSecret:InstancesRoot"] = f.Root + "\0";
        using var held = defect == "locked" ? File.Open(f.FilePath, FileMode.Open, FileAccess.Read, FileShare.None) : null;
        var error = Assert.Throws<SqlSecretException>(() => f.Read());
        Assert.Equal(expected, error.Message);
        Assert.Null(error.InnerException);
        if (defect == "missing") Assert.False(File.Exists(f.FilePath));
    }

    [Fact]
    public void ProductionTrustCannotAdoptTheLaboratoryOwner()
    {
        using var f = new Store();
        Assert.Equal("sql_secret_access_unsafe", Assert.Throws<SqlSecretException>(() => SqlSecretConnection.Resolve(Config(f.Values))).Code);
    }

    [Theory]
    [InlineData("--bootstrap")]
    [InlineData("--migrate")]
    [InlineData("--recover-admin")]
    [InlineData("--mfa-require-all")]
    public void MaintenanceProcessCannotUseTheProtectedRuntimeIdentity(string argument)
    {
        var result = RunServer(new() { ["SqlSecret__Enabled"] = "true" }, argument);
        Assert.Equal(1, result.Exit);
        Assert.Equal("sql_secret_runtime_only", result.Error.Trim());
        Assert.Equal("", result.Output);
    }

    [Theory]
    [InlineData("yes", "sql_secret_config_invalid")]
    [InlineData("true", "sql_secret_config_invalid")]
    public void InvalidProtectedStartupExitsWithoutDatabaseOrListener(string enabled, string expected)
    {
        var result = RunServer(new() { ["SqlSecret__Enabled"] = enabled });
        Assert.Equal(1, result.Exit);
        Assert.Equal(expected, result.Error.Trim());
        Assert.Equal("", result.Output);
    }

    [Fact]
    public void StartupCannotFallBackToAnAvailablePlaintextConnection()
    {
        var result = RunServer(new() { ["SqlSecret__Enabled"] = "true", ["ConnectionStrings__RackClick"] = Connection() });
        Assert.Equal(1, result.Exit);
        Assert.Equal("sql_secret_plaintext_conflict", result.Error.Trim());
        Assert.Equal("", result.Output);
    }

    [Fact]
    public async Task DecryptedConnectionUsesOnlyTheRestrictedPostgresRole()
    {
        var runtime = Environment.GetEnvironmentVariable("RACKCLICK_SQL_TEST_RUNTIME");
        Assert.SkipWhen(string.IsNullOrEmpty(runtime), "requires an isolated PostgreSQL runtime supplied by the test runner");
        var parsed = new NpgsqlConnectionStringBuilder(runtime);
        using var f = new Store(runtime!, parsed.Database!, parsed.Username!);
        await using var connection = new NpgsqlConnection(f.Read());
        await connection.OpenAsync(TestContext.Current.CancellationToken);
        await using var query = new NpgsqlCommand("SELECT current_user = @role AND NOT rolsuper AND NOT rolcreatedb AND NOT rolcreaterole AND NOT rolbypassrls FROM pg_roles WHERE rolname=current_user", connection);
        query.Parameters.AddWithValue("role", parsed.Username!);
        Assert.True((bool)(await query.ExecuteScalarAsync(TestContext.Current.CancellationToken))!);
        await using var read = new NpgsqlCommand("SELECT value FROM sql_secret_probe", connection);
        Assert.Equal(7, Convert.ToInt32(await read.ExecuteScalarAsync(TestContext.Current.CancellationToken)));
        await using var ddl = new NpgsqlCommand("CREATE TABLE must_not_be_created(id integer)", connection);
        var denied = await Assert.ThrowsAsync<PostgresException>(() => ddl.ExecuteNonQueryAsync(TestContext.Current.CancellationToken));
        Assert.Equal("42501", denied.SqlState);
    }

    private static IConfiguration Config(Dictionary<string, string?> values) => new ConfigurationBuilder().AddInMemoryCollection(values).Build();

    private static (int Exit, string Output, string Error) RunServer(Dictionary<string, string?> values, params string[] args)
    {
        var start = new ProcessStartInfo(Path.Combine(AppContext.BaseDirectory, "RackClick.Server.exe"))
        {
            WorkingDirectory = AppContext.BaseDirectory, UseShellExecute = false,
            RedirectStandardInput = true, RedirectStandardOutput = true, RedirectStandardError = true, CreateNoWindow = true,
        };
        foreach (var key in start.Environment.Keys.ToArray())
            if (key.StartsWith("SqlSecret", StringComparison.OrdinalIgnoreCase) || key.StartsWith("ConnectionStrings", StringComparison.OrdinalIgnoreCase) ||
                key.StartsWith("MfaKeyStore", StringComparison.OrdinalIgnoreCase) || key.StartsWith("CORECLR_", StringComparison.OrdinalIgnoreCase) ||
                key.StartsWith("COR_", StringComparison.OrdinalIgnoreCase) || key.StartsWith("DOTNET_", StringComparison.OrdinalIgnoreCase) ||
                key.StartsWith("ASPNETCORE_", StringComparison.OrdinalIgnoreCase)) start.Environment.Remove(key);
        start.Environment["DOTNET_EnableDiagnostics"] = "0";
        if (Environment.GetEnvironmentVariable("DOTNET_ROOT") is { Length: > 0 } dotnetRoot) start.Environment["DOTNET_ROOT"] = dotnetRoot;
        foreach (var (key, value) in values) start.Environment[key] = value;
        foreach (var arg in args) start.ArgumentList.Add(arg);
        using var process = Process.Start(start) ?? throw new InvalidOperationException("test process missing");
        process.StandardInput.Close();
        var output = process.StandardOutput.ReadToEndAsync();
        var error = process.StandardError.ReadToEndAsync();
        if (!process.WaitForExit(TimeSpan.FromSeconds(20))) { process.Kill(entireProcessTree: true); throw new InvalidOperationException("unexpected listener or wait"); }
        return (process.ExitCode, output.Result, error.Result);
    }

    private sealed class Store : IDisposable
    {
        private static readonly string Parent = Path.GetFullPath(Path.Combine(Path.GetTempPath(), "rackclick-sql-f0201"));
        public string Root { get; } = Path.Combine(Parent, Guid.NewGuid().ToString("N"));
        private Guid Id { get; } = Guid.NewGuid();
        public SecurityIdentifier[] Trusted { get; } = [WindowsIdentity.GetCurrent().User!, new(WellKnownSidType.LocalSystemSid, null)];
        public string Keys => Path.Combine(Root, Id.ToString("D"), "sql-secrets");
        public string FilePath => Path.Combine(Keys, "runtime.bin");
        public Dictionary<string, string?> Values { get; }
        public Store(string? connection = null, string database = Database, string role = Runtime)
        {
            Values = new() { ["SqlSecret:Enabled"] = "true", ["SqlSecret:InstancesRoot"] = Root,
                ["SqlSecret:InstallationId"] = Id.ToString("D"), ["SqlSecret:Database"] = database, ["SqlSecret:RuntimeUser"] = role };
            foreach (var path in new[] { Root, Path.GetDirectoryName(Keys)!, Keys })
            {
                var security = new DirectorySecurity();
                security.SetAccessRuleProtection(true, false);
                foreach (var sid in Trusted) security.AddAccessRule(new FileSystemAccessRule(sid, FileSystemRights.FullControl, InheritanceFlags.ContainerInherit | InheritanceFlags.ObjectInherit, PropagationFlags.None, AccessControlType.Allow));
                security.AddAccessRule(new FileSystemAccessRule(Users, FileSystemRights.ReadAndExecute, InheritanceFlags.ContainerInherit | InheritanceFlags.ObjectInherit, PropagationFlags.None, AccessControlType.Allow));
                FileSystemAclExtensions.CreateDirectory(security, path);
            }
            var cipher = WindowsSqlSecret.ProtectForProvisioning(connection ?? Connection(), Id, Users, database, role);
            File.WriteAllBytes(FilePath, cipher); // synthetic ciphertext, inherits the fixture's private DACL
        }
        public string Read() => SqlSecretConnection.Read(Config(Values), Users, Trusted);
        public void Dispose()
        {
            var absolute = Path.GetFullPath(Root);
            if (!absolute.StartsWith(Parent + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase)) throw new InvalidOperationException("unsafe fixture cleanup");
            if (Directory.Exists(absolute)) Directory.Delete(absolute, recursive: true);
        }
    }
}
