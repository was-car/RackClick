using System.Diagnostics;
using System.Net;
using System.Net.Sockets;
using System.Security.Cryptography;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.AspNetCore.TestHost;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;
using Npgsql;
using RackClick.Server;
using Xunit;

namespace RackClick.Quality.Tests;

// Browser/TCP integration, explicitly opt-in through a frontend build and PG administrator supplied by the laboratory.
// Synthetic key provider exists only in ConfigureTestServices; this does not test a Windows service token or enable MFA in QA.
[Collection("MfaHttp")]
public sealed class MfaBrowserGuiTests
{
    [Fact]
    public async Task BrowserEnrollsThenRequiresSecondFactorOnTheNextLogin()
    {
        var admin = Environment.GetEnvironmentVariable("RACKCLICK_TEST_PG_ADMIN");
        var frontend = Environment.GetEnvironmentVariable("RACKCLICK_MFA_GUI_FRONTEND");
        Assert.SkipWhen(string.IsNullOrWhiteSpace(admin) || string.IsNullOrWhiteSpace(frontend),
            "Explicit isolated PostgreSQL laboratory and frontend build are required.");
        var repository = RepositoryRoot();
        var node = Path.Combine(repository, ".local", "node-v24.21.0-win-x64", "node.exe");
        var browserScript = Path.Combine(repository, "development", "frontend", "tests", "browser-mfa-login.mjs");
        Assert.True(File.Exists(node) && File.Exists(browserScript), "Existing Node and browser fixture are required.");
        Assert.True(File.Exists(Path.Combine(frontend!, "index.html")), "The explicit frontend build is missing.");
        var output = Environment.GetEnvironmentVariable("RACKCLICK_MFA_GUI_OUTPUT")
            ?? Path.Combine(repository, ".local", "mfa-gui-browser", Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(output);

        await using var laboratory = await Laboratory.Create(admin!, Path.GetFullPath(frontend!), output);
        var start = new ProcessStartInfo(node)
        {
            WorkingDirectory = Path.Combine(repository, "development", "frontend"),
            UseShellExecute = false,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            CreateNoWindow = true,
        };
        start.ArgumentList.Add(browserScript);
        start.Environment["RACKCLICK_TEST_ORIGIN"] = laboratory.Origin;
        start.Environment["RACKCLICK_TEST_USERNAME"] = laboratory.UserName;
        start.Environment["RACKCLICK_TEST_PASSWORD"] = laboratory.Password;
        start.Environment["RACKCLICK_TEST_OUTPUT"] = output;
        // Browser testing never needs to inherit diagnostics/profiling configuration from the build process.
        foreach (var name in start.Environment.Keys.Where(name => name.StartsWith("CORECLR_", StringComparison.OrdinalIgnoreCase)
                     || name.StartsWith("DOTNET_", StringComparison.OrdinalIgnoreCase)).ToArray())
            start.Environment.Remove(name);
        using var process = Process.Start(start) ?? throw new InvalidOperationException("Browser test process did not start.");
        using var timeout = CancellationTokenSource.CreateLinkedTokenSource(TestContext.Current.CancellationToken);
        timeout.CancelAfter(TimeSpan.FromMinutes(4));
        var stdout = process.StandardOutput.ReadToEndAsync(timeout.Token);
        var stderr = process.StandardError.ReadToEndAsync(timeout.Token);
        try { await process.WaitForExitAsync(timeout.Token); }
        catch (OperationCanceledException)
        {
            if (!process.HasExited) process.Kill(entireProcessTree: true);
            throw new InvalidOperationException("Browser test exceeded its laboratory timeout.");
        }
        // The JS fixture emits only fixed check labels/statuses. It deliberately omits body text, screenshots and tokens.
        var safeOut = await stdout;
        var safeError = await stderr;
        await File.WriteAllTextAsync(Path.Combine(output, "browser-process.txt"), safeOut + "\n" + safeError,
            TestContext.Current.CancellationToken);
        Assert.True(process.ExitCode == 0, "Browser MFA scenario failed; inspect its sanitized laboratory result.");
        Assert.Equal(1, await laboratory.Count("SELECT count(*) FROM app_mfa_factor WHERE state='active'"));
        Assert.Equal(1, await laboratory.Count("SELECT count(*) FROM app_session WHERE mfa_verified_at IS NOT NULL"));
        Assert.True(await laboratory.Count("SELECT count(*) FROM app_mfa_challenge WHERE consumed_at IS NOT NULL") >= 2,
            "Successful enrollment and verification must both consume their challenges.");
    }

    private static string RepositoryRoot()
    {
        var folder = new DirectoryInfo(AppContext.BaseDirectory);
        while (folder is not null)
        {
            if (File.Exists(Path.Combine(folder.FullName, "development", "frontend", "build.mjs"))
                && File.Exists(Path.Combine(folder.FullName, ".local", "node-v24.21.0-win-x64", "node.exe"))
                && File.Exists(Path.Combine(folder.FullName, "development", "frontend", "tests", "browser-mfa-login.mjs")))
                return folder.FullName;
            folder = folder.Parent;
        }
        throw new InvalidOperationException("Repository root unavailable to the browser fixture.");
    }

    private sealed class Laboratory : IAsyncDisposable
    {
        private readonly string _admin;
        private readonly string _database = "rc_mfa_gui_" + Guid.NewGuid().ToString("N");
        private readonly string _runtimeRole = "rc_mfa_gui_runtime_" + Guid.NewGuid().ToString("N");
        private readonly string _runtimePassword = Convert.ToBase64String(RandomNumberGenerator.GetBytes(32));
        private readonly byte[] _key = RandomNumberGenerator.GetBytes(MfaSecretCipher.KeyBytes);
        private readonly Dictionary<string, string?> _previousEnvironment = [];
        private bool _databaseCreated;
        private bool _roleCreated;
        private WebApplicationFactory<Program>? _factory;
        private NpgsqlDataSource? _source;

        public string UserName { get; } = "mfa-gui-user";
        public string Password { get; } = "Laboratory-" + Convert.ToBase64String(RandomNumberGenerator.GetBytes(24));
        public string Origin { get; }

        private Laboratory(string admin)
        {
            _admin = admin;
            var listener = new TcpListener(IPAddress.Loopback, 0);
            listener.Start();
            var port = ((IPEndPoint)listener.LocalEndpoint).Port;
            listener.Stop();
            Origin = "http://127.0.0.1:" + port;
        }

        public static async Task<Laboratory> Create(string admin, string frontend, string output)
        {
            var laboratory = new Laboratory(admin);
            try
            {
                await laboratory.PrepareDatabase();
                laboratory.Start(frontend);
                await File.WriteAllTextAsync(Path.Combine(output, "laboratory-scope.json"),
                    "{\"provider\":\"synthetic-test-DI\",\"transport\":\"Kestrel-loopback-HTTP\",\"postgresRuntimeRoleHasDDL\":false,\"serviceTokenTested\":false,\"qaModified\":false}\n");
                return laboratory;
            }
            catch
            {
                await laboratory.DisposeAsync();
                throw;
            }
        }

        private string Connection(string? role = null)
        {
            var builder = new NpgsqlConnectionStringBuilder(_admin) { Database = _database };
            if (role is not null) { builder.Username = role; builder.Password = _runtimePassword; }
            return builder.ConnectionString;
        }

        private async Task PrepareDatabase()
        {
            await using (var connection = new NpgsqlConnection(_admin))
            {
                await connection.OpenAsync();
                // Identifiers are generated solely from closed literal prefixes and Guid.ToString("N").
                await using var create = new NpgsqlCommand($"CREATE DATABASE {_database} ENCODING 'UTF8' TEMPLATE template0", connection);
                await create.ExecuteNonQueryAsync();
                _databaseCreated = true;
            }
            _source = NpgsqlDataSource.Create(Connection());
            var store = new PostgresStore(_source);
            await store.Bootstrap("Laboratorio MFA GUI", UserName, Password, TestContext.Current.CancellationToken);
            await using (var connection = await _source.OpenConnectionAsync())
            {
                await using var require = new NpgsqlCommand(
                    "INSERT INTO app_mfa_user(systemhaus_id,user_id,mfa_required) SELECT systemhaus_id,id,true FROM app_user WHERE username=@name", connection);
                require.Parameters.AddWithValue("name", UserName);
                Assert.Equal(1, await require.ExecuteNonQueryAsync());
                await using var role = new NpgsqlCommand(
                    $"CREATE ROLE {_runtimeRole} LOGIN PASSWORD '{_runtimePassword}' NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT", connection);
                // The password is locally generated base64 (no quote/metacharacter). It never comes from external input.
                await role.ExecuteNonQueryAsync();
                _roleCreated = true;
                await using var grants = new NpgsqlCommand(
                    $"GRANT USAGE ON SCHEMA public TO {_runtimeRole}; GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public TO {_runtimeRole}", connection);
                await grants.ExecuteNonQueryAsync();
            }
            await using var runtime = new NpgsqlConnection(Connection(_runtimeRole));
            await runtime.OpenAsync();
            await using var denied = new NpgsqlCommand("CREATE TABLE mfa_gui_ddl_must_be_denied(id integer)", runtime);
            var failure = await Assert.ThrowsAsync<PostgresException>(() => denied.ExecuteNonQueryAsync());
            Assert.Equal(PostgresErrorCodes.InsufficientPrivilege, failure.SqlState);
        }

        private void SetEnvironment(string name, string value)
        {
            _previousEnvironment.TryAdd(name, Environment.GetEnvironmentVariable(name));
            Environment.SetEnvironmentVariable(name, value);
        }

        private void Start(string frontend)
        {
            SetEnvironment("ConnectionStrings__RackClick", Connection(_runtimeRole));
            SetEnvironment("PublicOrigin", Origin);
            SetEnvironment("DevelopmentLoopbackHttp", "true");
            SetEnvironment("RackClick__FrontendPath", frontend);
            SetEnvironment("MfaKeyStore__Enabled", "false");
            _factory = new WebApplicationFactory<Program>().WithWebHostBuilder(builder =>
            {
                builder.UseEnvironment("Development");
                builder.ConfigureLogging(logging => logging.ClearProviders());
                builder.ConfigureTestServices(services => services.AddSingleton<IMfaKeyProvider>(new SyntheticKeys(_key)));
            });
            _factory.UseKestrel(new Uri(Origin).Port);
            _factory.StartServer();
        }

        public async Task<long> Count(string sql)
        {
            await using var connection = await _source!.OpenConnectionAsync();
            await using var command = new NpgsqlCommand(sql, connection);
            return Convert.ToInt64(await command.ExecuteScalarAsync() ?? 0L);
        }

        public async ValueTask DisposeAsync()
        {
            try
            {
                try
                {
                    if (_factory is not null) await _factory.DisposeAsync();
                }
                finally
                {
                    try
                    {
                        if (_source is not null) await _source.DisposeAsync();
                    }
                    finally
                    {
                        NpgsqlConnection.ClearAllPools();
                        await using var connection = new NpgsqlConnection(_admin);
                        await connection.OpenAsync();
                        if (_databaseCreated)
                        {
                            await using var drop = new NpgsqlCommand($"DROP DATABASE IF EXISTS {_database} WITH (FORCE)", connection);
                            await drop.ExecuteNonQueryAsync();
                        }
                        if (_roleCreated)
                        {
                            await using var drop = new NpgsqlCommand($"DROP ROLE IF EXISTS {_runtimeRole}", connection);
                            await drop.ExecuteNonQueryAsync();
                        }
                    }
                }
            }
            finally
            {
                foreach (var (name, value) in _previousEnvironment) Environment.SetEnvironmentVariable(name, value);
                CryptographicOperations.ZeroMemory(_key);
            }
        }
    }

    private sealed class SyntheticKeys(byte[] key) : IMfaKeyProvider
    {
        public byte[] GetKey(int version) => version == 1 ? (byte[])key.Clone() : throw new InvalidOperationException("mfa_key_version_unknown");
        public (int Version, byte[] Key) GetActiveKey() => (1, (byte[])key.Clone());
    }
}
