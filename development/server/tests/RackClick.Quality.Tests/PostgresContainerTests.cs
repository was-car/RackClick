using System.ComponentModel;
using System.Diagnostics;
using System.Security.Cryptography;
using Microsoft.Extensions.Logging.Abstractions;
using Npgsql;
using RackClick.Domain;
using RackClick.Server;
using Testcontainers.PostgreSql;
using Xunit;

namespace RackClick.Quality.Tests;

public sealed class PostgresContainerTests
{
    [Fact]
    [Trait("RequiresDocker", "true")]
    public async Task BootstrapUnicodeLoginAndSessionPersistAndRejectWrongPassword()
    {
        var docker = await DockerAvailability.Probe();
        if (Environment.GetEnvironmentVariable("RACKCLICK_REQUIRE_DOCKER") == "1")
            Assert.True(docker.Available, "RACKCLICK_REQUIRE_DOCKER=1: " + docker.Reason);
        Assert.SkipWhen(!docker.Available, docker.Reason);

        // Every invocation owns one new PG 17.11 container/database; no existing server,
        // persisted host path, reusable container, fixed port, or QA credential is accepted.
        await using var postgres = new PostgreSqlBuilder("postgres:17.11")
            .WithDatabase("rackclick_rev4_" + Guid.NewGuid().ToString("N"))
            .WithUsername("rackclick_fixture")
            .WithPassword(Convert.ToHexString(RandomNumberGenerator.GetBytes(32)))
            .WithReuse(false)
            .WithLogger(NullLogger.Instance)
            .WithCreateParameterModifier(parameters =>
            {
                var bindings = parameters.HostConfig?.PortBindings
                    ?? throw new InvalidOperationException("PostgreSQL fixture port bindings missing.");
                foreach (var binding in bindings.Values.SelectMany(value => value))
                    binding.HostIP = "127.0.0.1";
            })
            .Build();
        using var timeout = new CancellationTokenSource(TimeSpan.FromMinutes(3));
        var ct = timeout.Token;
        await postgres.StartAsync(ct);

        string password = Convert.ToHexString(RandomNumberGenerator.GetBytes(24));
        string username = "ADMIN" + string.Concat(Enumerable.Repeat(char.ConvertFromUtf32(0x1F680), 95));
        const string houseName = "Casa de pruebas ÄÖÜ";
        (string Token, string Csrf) login;

        await using (var source = NpgsqlDataSource.Create(postgres.GetConnectionString()))
        {
            var store = new PostgresStore(source);
            await store.Bootstrap(houseName, "  " + username + "  ", password, ct);
            login = await store.Login(username.ToLowerInvariant(), password, ct);
        }

        // A fresh pool/store must read the committed account/session, rather than process memory.
        await using var reconnected = NpgsqlDataSource.Create(postgres.GetConnectionString());
        var freshStore = new PostgresStore(reconnected);
        var session = await freshStore.Session(login.Token, ct);
        Assert.NotNull(session);
        Assert.Equal(UserNames.Normalize(username), session.Actor.UserName);
        Assert.NotEqual(Guid.Empty, session.Actor.Id);
        Assert.NotEqual(Guid.Empty, session.Actor.HouseId);
        Assert.Equal(Secrets.Digest(login.Csrf), session.CsrfHash);
        Assert.Equal(Secrets.Digest(login.Token), session.Actor.SessionTokenHash);

        var error = await Assert.ThrowsAsync<DomainError>(() => freshStore.Login(username, password + "x", ct));
        Assert.Equal(401, error.Status);
        Assert.Equal("login_failed", error.Code);

        await using var db = await reconnected.OpenConnectionAsync(ct);
        await using (var version = new NpgsqlCommand("SHOW server_version_num", db))
            Assert.Equal("170011", Convert.ToString(await version.ExecuteScalarAsync(ct)));
        await using (var migration = new NpgsqlCommand("SELECT max(version) FROM schema_migration", db))
            Assert.Equal(SchemaMigrations.LatestVersion, (int)(await migration.ExecuteScalarAsync(ct))!);
        await using (var sessions = new NpgsqlCommand("SELECT count(*) FROM app_session", db))
            Assert.Equal(1L, (long)(await sessions.ExecuteScalarAsync(ct))!);
        await using (var failed = new NpgsqlCommand("SELECT failed_logins FROM app_user", db))
            Assert.Equal(1, (int)(await failed.ExecuteScalarAsync(ct))!);
        await using (var house = new NpgsqlCommand("SELECT name FROM systemhaus", db))
            Assert.Equal(houseName, (string)(await house.ExecuteScalarAsync(ct))!);
    }
}

internal static class DockerAvailability
{
    // A sanitized reason is intentionally used instead of dumping daemon output/connection settings.
    public static async Task<(bool Available, string Reason)> Probe()
    {
        try
        {
            using var docker = new Process
            {
                StartInfo = new ProcessStartInfo("docker")
                {
                    UseShellExecute = false,
                    CreateNoWindow = true,
                    RedirectStandardOutput = true,
                    RedirectStandardError = true
                }
            };
            docker.StartInfo.ArgumentList.Add("info");
            docker.StartInfo.ArgumentList.Add("--format");
            docker.StartInfo.ArgumentList.Add("{{.OSType}}");
            if (!docker.Start()) return (false, "Docker CLI did not start; Linux container test not executed.");
            var stdout = docker.StandardOutput.ReadToEndAsync();
            var stderr = docker.StandardError.ReadToEndAsync();
            using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(10));
            try { await docker.WaitForExitAsync(timeout.Token); }
            catch (OperationCanceledException)
            {
                docker.Kill(entireProcessTree: true);
                await docker.WaitForExitAsync();
                await Task.WhenAll(stdout, stderr);
                return (false, "Docker engine probe timed out; Linux container test not executed.");
            }
            await stderr;
            return docker.ExitCode == 0 && (await stdout).Trim() == "linux"
                ? (true, "Linux Docker engine available.")
                : (false, "Reachable Linux Docker engine required; container test not executed.");
        }
        catch (Win32Exception)
        {
            return (false, "Docker CLI unavailable; PostgreSQL container test not executed.");
        }
    }
}
