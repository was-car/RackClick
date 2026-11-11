using System.Data;
using System.Security.Cryptography;
using System.Text.Json;
using Npgsql;
using RackClick.Server;
using Xunit;

namespace RackClick.Quality.Tests;

// Only the new loopback PostgreSQL laboratory supplied by the F0602 runner.
// No fallback to ConnectionStrings__RackClick or an installed database.
public sealed class MfaFactorKeyInventoryReaderTests
{
    private static readonly Guid Installation = Guid.Parse("4b29162b-0e97-46b0-9c7d-201600000020");

    [Fact]
    public async Task CountsEveryStateAcrossTheDatabaseWithoutFilteringAVisibleCustomer()
    {
        await using var db = await Open("POPULATED");
        await using var tx = await ReadOnly(db, IsolationLevel.RepeatableRead);
        var inventory = await MfaFactorKeyInventoryReader.ReadAsync(db, tx, Installation, CancellationToken.None);
        Assert.Equal(Installation, inventory.InstallationId);
        Assert.Equal(2, inventory.Entries.Count);
        Assert.Equal(new MfaKeyVersionCount(1, 1, 1, 1), inventory.Entries[0]);
        Assert.Equal(new MfaKeyVersionCount(7, 0, 2, 0), inventory.Entries[1]);
        await tx.CommitAsync(TestContext.Current.CancellationToken);
    }

    [Fact]
    public async Task EmptyDatabaseIsAnExplicitEmptyCensus()
    {
        await using var db = await Open("EMPTY");
        await using var tx = await ReadOnly(db, IsolationLevel.RepeatableRead);
        var inventory = await MfaFactorKeyInventoryReader.ReadAsync(db, tx, Installation, CancellationToken.None);
        Assert.Empty(inventory.Entries);
        Assert.Equal(Installation, inventory.InstallationId);
        await tx.CommitAsync(TestContext.Current.CancellationToken);
    }

    [Fact]
    public async Task WorksWithSelectOnlyRoleAndDoesNotChangePersistentRows()
    {
        await using var db = await Open("POPULATED");
        await using (var authority = new NpgsqlCommand("SELECT rolsuper,has_table_privilege(current_user,'app_mfa_factor','UPDATE'),has_schema_privilege(current_user,'public','CREATE') FROM pg_roles WHERE rolname=current_user", db))
        await using (var row = await authority.ExecuteReaderAsync(TestContext.Current.CancellationToken))
        {
            Assert.True(await row.ReadAsync(TestContext.Current.CancellationToken));
            Assert.False(row.GetBoolean(0));
            Assert.False(row.GetBoolean(1));
            Assert.False(row.GetBoolean(2));
        }
        await using var tx = await ReadOnly(db, IsolationLevel.RepeatableRead);
        var before = await Fingerprint(db, tx);
        _ = await MfaFactorKeyInventoryReader.ReadAsync(db, tx, Installation, CancellationToken.None);
        Assert.Equal(before, await Fingerprint(db, tx));
        await tx.CommitAsync(TestContext.Current.CancellationToken);
    }

    [Fact]
    public async Task SerializableReadOnlyIsAccepted()
    {
        await using var db = await Open("POPULATED");
        await using var tx = await ReadOnly(db, IsolationLevel.Serializable);
        Assert.Equal(2, (await MfaFactorKeyInventoryReader.ReadAsync(db, tx, Installation, CancellationToken.None)).Entries.Count);
    }

    [Fact]
    public async Task ReadWriteTransactionIsRejectedBeforeTheFactorQuery()
    {
        await using var db = await Open("POPULATED");
        await using var tx = await db.BeginTransactionAsync(IsolationLevel.RepeatableRead, TestContext.Current.CancellationToken);
        var error = await Assert.ThrowsAsync<InvalidOperationException>(() => MfaFactorKeyInventoryReader.ReadAsync(db, tx, Installation, CancellationToken.None));
        Assert.Equal("mfa_factor_inventory_read_only_required", error.Message);
    }

    [Fact]
    public async Task ReadCommittedIsNotPresentedAsAStableInventory()
    {
        await using var db = await Open("POPULATED");
        await using var tx = await ReadOnly(db, IsolationLevel.ReadCommitted);
        var error = await Assert.ThrowsAsync<InvalidOperationException>(() => MfaFactorKeyInventoryReader.ReadAsync(db, tx, Installation, CancellationToken.None));
        Assert.Equal("mfa_factor_inventory_snapshot_required", error.Message);
    }

    [Fact]
    public async Task AnotherConnectionsTransactionIsRejected()
    {
        await using var db = await Open("POPULATED");
        await using var other = await Open("POPULATED");
        await using var tx = await ReadOnly(db, IsolationLevel.RepeatableRead);
        var error = await Assert.ThrowsAsync<InvalidOperationException>(() => MfaFactorKeyInventoryReader.ReadAsync(other, tx, Installation, CancellationToken.None));
        Assert.Equal("mfa_factor_inventory_transaction_required", error.Message);
    }

    [Fact]
    public async Task CancellationIsNotAnEmptySuccessfulCensus()
    {
        await using var db = await Open("POPULATED");
        await using var tx = await ReadOnly(db, IsolationLevel.RepeatableRead);
        using var cancel = new CancellationTokenSource();
        cancel.Cancel();
        await Assert.ThrowsAnyAsync<OperationCanceledException>(() => MfaFactorKeyInventoryReader.ReadAsync(db, tx, Installation, cancel.Token));
    }

    [Fact]
    public async Task SqlPositiveVersionBeyondTheRingProfileIsRejected()
    {
        await using var db = await Open("INVALID_VERSION");
        await using var tx = await ReadOnly(db, IsolationLevel.RepeatableRead);
        var error = await Assert.ThrowsAsync<MfaKeyRetentionException>(() => MfaFactorKeyInventoryReader.ReadAsync(db, tx, Installation, CancellationToken.None));
        Assert.Equal("mfa_retention_invalid", error.Message);
    }

    [Fact]
    public async Task SeparateInventoryBindsARealQuiescentBackupAndAnAuthenticatedEnvelope()
    {
        await using var db = await Open("POPULATED");
        await using var tx = await ReadOnly(db, IsolationLevel.RepeatableRead);
        var census = await MfaFactorKeyInventoryReader.ReadAsync(db, tx, Installation, CancellationToken.None);
        var contextPath = Environment.GetEnvironmentVariable("RACKCLICK_F0602_BACKUP_CONTEXT");
        Assert.False(string.IsNullOrEmpty(contextPath));
        using var context = JsonDocument.Parse(await File.ReadAllBytesAsync(contextPath!, TestContext.Current.CancellationToken));
        var root = context.RootElement;
        var backupPath = root.GetProperty("backupDirectory").GetString()!;
        var sidecarPath = root.GetProperty("inventoryPath").GetString()!;
        var manifestHash = root.GetProperty("manifestSha256").GetString()!;
        var dumpHash = root.GetProperty("dumpSha256").GetString()!;
        Assert.Equal(manifestHash, Digest(await File.ReadAllBytesAsync(Path.Combine(backupPath, "manifest.json"), TestContext.Current.CancellationToken)));
        Assert.Equal(dumpHash, Digest(await File.ReadAllBytesAsync(Path.Combine(backupPath, "data.dump"), TestContext.Current.CancellationToken)));
        Assert.Equal(2, Directory.GetFiles(backupPath).Length);
        Assert.NotEqual(Path.GetFullPath(backupPath), Path.GetDirectoryName(Path.GetFullPath(sidecarPath)));

        var ringJson = JsonSerializer.SerializeToUtf8Bytes(new
        {
            format = MfaKeyRing.RingFormat, formatVersion = 1, installationId = Installation.ToString("D"),
            versions = new[] { 1, 5, 7 }.Select(v => new { version = v, state = v == 7 ? "active" : "retired", createdAtUtc = "2026-11-09T00:00:00Z" })
        });
        var keys = new[] { 1, 5, 7 }.Select(v => (Version: v, Key: RandomNumberGenerator.GetBytes(32))).ToArray();
        try
        {
            using var payload = MfaKeyRecoveryPayload.Serialize(ringJson, Installation, keys);
            var password = Convert.ToBase64String(RandomNumberGenerator.GetBytes(24));
            var envelope = MfaKeyRecoveryEnvelope.Seal(password, payload.Bytes);
            var envelopeInventory = MfaKeyRetention.InspectEnvelope(envelope, password, Installation);
            var inventory = MfaKeyRetention.CreateBackupInventory(Guid.NewGuid(), census, envelopeInventory, manifestHash, dumpHash);
            Assert.Equal(new[] { 1, 7 }, inventory.RequiredVersions);
            Assert.Equal(new[] { 1, 5, 7 }, inventory.EnvelopeVersions);
            var bytes = MfaKeyRetention.SerializeBackupInventory(inventory);
            var expectedInventoryHash = Digest(bytes);
            await using (var output = new FileStream(sidecarPath, FileMode.CreateNew, FileAccess.Write, FileShare.None))
                await output.WriteAsync(bytes, TestContext.Current.CancellationToken);
            var parsed = MfaKeyRetention.ParseBackupInventory(await File.ReadAllBytesAsync(sidecarPath, TestContext.Current.CancellationToken), Installation,
                expectedInventoryHash, manifestHash, dumpHash, Digest(envelope));
            Assert.Equal(MfaKeyRetentionDecision.CandidateUnreferenced,
                MfaKeyRetention.EvaluateCandidate(ringJson, Installation, census, [parsed], true, 5));
            Assert.Equal(MfaKeyRetentionDecision.FactorReferenced,
                MfaKeyRetention.EvaluateCandidate(ringJson, Installation, census, [parsed], true, 1));
            Assert.Equal(2, Directory.GetFiles(backupPath).Length);
        }
        finally
        {
            foreach (var key in keys) CryptographicOperations.ZeroMemory(key.Key);
        }
        await tx.CommitAsync(TestContext.Current.CancellationToken);
    }

    private static string Digest(byte[] value) => Convert.ToHexStringLower(SHA256.HashData(value));

    private static async Task<NpgsqlConnection> Open(string suffix)
    {
        var raw = Environment.GetEnvironmentVariable("RACKCLICK_F0602_PG_" + suffix);
        Assert.SkipWhen(string.IsNullOrWhiteSpace(raw), "isolated F0602 PostgreSQL inventory laboratory required");
        var builder = new NpgsqlConnectionStringBuilder(raw);
        Assert.Equal("127.0.0.1", builder.Host);
        Assert.StartsWith("rc_", builder.Database ?? "");
        Assert.InRange(builder.Port, 1024, 65535);
        var connection = new NpgsqlConnection(builder.ConnectionString);
        await connection.OpenAsync(TestContext.Current.CancellationToken);
        return connection;
    }

    private static async Task<NpgsqlTransaction> ReadOnly(NpgsqlConnection db, IsolationLevel isolation)
    {
        var tx = await db.BeginTransactionAsync(isolation, TestContext.Current.CancellationToken);
        await using var command = new NpgsqlCommand("SET TRANSACTION READ ONLY", db, tx);
        await command.ExecuteNonQueryAsync(TestContext.Current.CancellationToken);
        return tx;
    }

    private static async Task<string> Fingerprint(NpgsqlConnection db, NpgsqlTransaction tx)
    {
        // The reader itself never reads ciphertext; this synthetic fixture witness
        // compares complete factor rows inside this read-only snapshot. The runner
        // separately compares fresh before/after snapshots of the quiescent lab.
        await using var command = new NpgsqlCommand("SELECT md5(COALESCE(jsonb_agg(to_jsonb(f) ORDER BY systemhaus_id,user_id)::text,'')) FROM app_mfa_factor f", db, tx);
        return (string)(await command.ExecuteScalarAsync(TestContext.Current.CancellationToken))!;
    }
}
