using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using RackClick.Server;
using Xunit;

namespace RackClick.Quality.Tests;

public sealed class MfaBackupInventoryCommandTests
{
    internal static readonly Guid Installation = Guid.Parse("c76d6f6b-1caa-46dd-932c-1a04c442ab22");
    internal static readonly Guid Backup = Guid.Parse("f7878e3a-0b62-4791-b282-2fe14ac7d1d9");
    internal static readonly string ManifestHash = new('a', 64);
    internal static readonly string DumpHash = new('b', 64);
    internal static readonly string EnvelopeHash = new('c', 64);

    [Fact]
    public async Task VerifyNeedsOnlyInventoryAndExternalPinsWithoutDatabaseOrKeys()
    {
        var (exit, output) = await Run(VerifyRequest().ToJsonString(), TestContext.Current.CancellationToken);
        Assert.Equal(0, exit);
        using var result = JsonDocument.Parse(output);
        Assert.Equal("inventory_verified", result.RootElement.GetProperty("status").GetString());
        Assert.Equal(Backup.ToString("D"), result.RootElement.GetProperty("backupId").GetString());
        Assert.Equal(new[] { 2, 7 }, result.RootElement.GetProperty("requiredVersions").EnumerateArray().Select(x => x.GetInt32()));
        Assert.Equal(new[] { 1, 2, 7 }, result.RootElement.GetProperty("envelopeVersions").EnumerateArray().Select(x => x.GetInt32()));
    }

    [Theory]
    [InlineData("")]
    [InlineData("{}")]
    [InlineData("[]")]
    [InlineData("{\"operation\":\"snapshot\",\"operation\":\"verify\"}")]
    [InlineData("{\"operation\":\"\\ud800\"}")]
    [InlineData("{\"\\ud800\":\"snapshot\"}")]
    [InlineData("{\"operation\":true}")]
    public async Task MalformedInitialInputIsRejectedWithoutReflectingIt(string input)
    {
        await Rejected(input, "mfa_backup_invalid");
    }

    [Theory]
    [InlineData("extra", "private-marker")]
    [InlineData("installationId", "00000000-0000-0000-0000-000000000000")]
    [InlineData("installationId", "c76d6f6b1caa46dd932c1a04c442ab22")]
    [InlineData("inventoryBase64", "not-base64-private-marker")]
    [InlineData("inventorySha256", "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")]
    [InlineData("dumpSha256", "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff")]
    public async Task VerifyRejectsExtraFieldsNoncanonicalIdsAndMismatchedPins(string field, string value)
    {
        var request = VerifyRequest();
        request[field] = value;
        await Rejected(request.ToJsonString(), "mfa_backup_invalid");
    }

    [Fact]
    public async Task DuplicateEvenEscapedPropertyNameIsRejected()
    {
        var request = VerifyRequest().ToJsonString();
        await Rejected(request.Insert(1, "\"operati\\u006fn\":\"verify\","), "mfa_backup_invalid");
    }

    [Fact]
    public async Task InitialLimitIsEnforcedBeforeAnUnboundedLineIsRead()
    {
        await Rejected(new string(' ', 2 * 1024 * 1024 + 1), "mfa_backup_invalid");
    }

    [Fact]
    public async Task UnicodeEscapedAndLiteralUnpairedSurrogatesAreRejected()
    {
        var input = VerifyRequest().ToJsonString().Replace("\"verify\"", "\"\\udfff\"", StringComparison.Ordinal);
        await Rejected(input, "mfa_backup_invalid");
        await Rejected("{\"operation\":\"" + '\ud800' + "\"}", "mfa_backup_invalid");
    }

    [Fact]
    public async Task ValidJsonWithoutTerminatingNewlineIsATruncatedProtocol()
    {
        using var input = new StringReader(VerifyRequest().ToJsonString());
        using var output = new StringWriter();
        Assert.Equal(1, await Invoke(input, output, TestContext.Current.CancellationToken));
        Assert.Contains("mfa_backup_invalid", output.ToString());
        Assert.DoesNotContain("inventory_verified", output.ToString());
    }

    [Fact]
    public async Task InputIOExceptionIsSanitized()
    {
        using var input = new FailingReader();
        using var output = new StringWriter();
        Assert.Equal(1, await Invoke(input, output, TestContext.Current.CancellationToken));
        Assert.Equal("{\"status\":\"rejected\",\"code\":\"mfa_backup_io_failed\"}" + Environment.NewLine, output.ToString());
    }

    [Fact]
    public async Task AlreadyCancelledCommandHasNoPositiveResponse()
    {
        using var cancelled = new CancellationTokenSource();
        cancelled.Cancel();
        var (exit, output) = await Run(VerifyRequest().ToJsonString(), cancelled.Token);
        Assert.Equal(1, exit);
        Assert.Equal("{\"status\":\"rejected\",\"code\":\"mfa_backup_cancelled\"}" + Environment.NewLine, output);
    }

    [Fact]
    public async Task CancellationEndsAReaderThatIgnoresTheReadCancellationToken()
    {
        using var reader = new NeverFinishingReader();
        using var writer = new StringWriter();
        using var cancellation = CancellationTokenSource.CreateLinkedTokenSource(TestContext.Current.CancellationToken);
        cancellation.CancelAfter(50);
        var task = Invoke(reader, writer, cancellation.Token);
        Assert.Equal(1, await task.WaitAsync(TimeSpan.FromSeconds(2), TestContext.Current.CancellationToken));
        Assert.Contains("mfa_backup_cancelled", writer.ToString());
    }

    [Theory]
    [InlineData("Host=localhost")]
    [InlineData("Host=127.0.0.2")]
    [InlineData("Host=127.0.0.1;Options=-c role=postgres")]
    public async Task SnapshotRejectsNonNativeConnectionsBeforeInspectingEnvelope(string connection)
    {
        var id = Installation.ToString("N");
        var request = new JsonObject
        {
            ["operation"] = "snapshot", ["installationId"] = Installation.ToString("D"),
            ["connectionString"] = connection + ";Database=rc_db_" + id + ";Username=rc_backup_" + id + ";Password=private-marker",
            ["envelopeBase64"] = "not-envelope", ["envelopePassword"] = "private-marker"
        };
        await Rejected(request.ToJsonString(), "mfa_backup_invalid");
    }

    internal static JsonObject VerifyRequest()
    {
        var inventory = new MfaBackupKeyInventory(Installation, Backup, ManifestHash, DumpHash, EnvelopeHash,
            [2], [1, 2, 7], 7, [2, 7]);
        var bytes = MfaKeyRetention.SerializeBackupInventory(inventory);
        return new JsonObject
        {
            ["operation"] = "verify", ["installationId"] = Installation.ToString("D"),
            ["inventoryBase64"] = Convert.ToBase64String(bytes),
            ["inventorySha256"] = Convert.ToHexStringLower(SHA256.HashData(bytes)),
            ["manifestSha256"] = ManifestHash, ["dumpSha256"] = DumpHash, ["envelopeSha256"] = EnvelopeHash
        };
    }

    internal static async Task<(int Exit, string Output)> Run(string input, CancellationToken token)
    {
        using var reader = new StringReader(input + "\n");
        using var writer = new StringWriter();
        return (await Invoke(reader, writer, token), writer.ToString());
    }

    private static Task<int> Invoke(TextReader reader, TextWriter writer, CancellationToken token) =>
        MfaBackupInventoryCommand.RunAsync(reader, writer, token);

    private sealed class NeverFinishingReader : TextReader
    {
        private readonly TaskCompletionSource<int> pending = new(TaskCreationOptions.RunContinuationsAsynchronously);
        public override ValueTask<int> ReadAsync(Memory<char> buffer, CancellationToken cancellationToken = default) => new(pending.Task);
    }

    private sealed class FailingReader : TextReader
    {
        public override ValueTask<int> ReadAsync(Memory<char> buffer, CancellationToken cancellationToken = default) =>
            ValueTask.FromException<int>(new IOException("private-marker"));
    }

    private static async Task Rejected(string input, string code)
    {
        var (exit, output) = await Run(input, TestContext.Current.CancellationToken);
        Assert.Equal(1, exit);
        Assert.Equal(JsonSerializer.Serialize(new { status = "rejected", code }) + Environment.NewLine, output);
    }
}

// Explicit opt-in laboratory. No installed/default connection string or identity fallback.
public sealed class MfaBackupInventoryPostgresTests
{
    public const string Password = "F0602-synthetic-envelope-only-password";

    [Fact]
    public async Task NativeSnapshotAndInventoryAreBoundToExternalPins()
    {
        var (installation, connection) = Context();
        var initial = Snapshot(installation, connection);
        var final = JsonSerializer.Serialize(new { backupId = MfaBackupInventoryCommandTests.Backup,
            manifestSha256 = MfaBackupInventoryCommandTests.ManifestHash, dumpSha256 = MfaBackupInventoryCommandTests.DumpHash });
        var (exit, output) = await MfaBackupInventoryCommandTests.Run(initial + "\n" + final, TestContext.Current.CancellationToken);
        Assert.Equal(0, exit);
        var lines = output.Split(Environment.NewLine, StringSplitOptions.RemoveEmptyEntries);
        Assert.Equal(2, lines.Length);
        using var ready = JsonDocument.Parse(lines[0]);
        Assert.Equal("snapshot_ready", ready.RootElement.GetProperty("status").GetString());
        using var completed = JsonDocument.Parse(lines[1]);
        Assert.Equal("inventory_ready", completed.RootElement.GetProperty("status").GetString());
        var bytes = Convert.FromBase64String(completed.RootElement.GetProperty("inventoryBase64").GetString()!);
        using var inventory = JsonDocument.Parse(bytes);
        Assert.Equal(installation.ToString("D"), inventory.RootElement.GetProperty("installationId").GetString());
        Assert.Equal(new[] { 2, 7 }, inventory.RootElement.GetProperty("requiredVersions").EnumerateArray().Select(v => v.GetInt32()));
        Assert.Equal(Convert.ToHexStringLower(SHA256.HashData(bytes)), completed.RootElement.GetProperty("inventorySha256").GetString());
    }

    [Theory]
    [InlineData("")]
    [InlineData("{}")]
    [InlineData("{\"backupId\":\"00000000-0000-0000-0000-000000000000\",\"manifestSha256\":\"private-marker\",\"dumpSha256\":\"private-marker\"}")]
    public async Task ExportedSnapshotWithMissingOrInvalidFinalMessageHasNoInventorySuccess(string final)
    {
        var (installation, connection) = Context();
        var (exit, output) = await MfaBackupInventoryCommandTests.Run(Snapshot(installation, connection) + "\n" + final,
            TestContext.Current.CancellationToken);
        Assert.Equal(1, exit);
        Assert.Contains("snapshot_ready", output);
        Assert.DoesNotContain("inventory_ready", output);
        Assert.DoesNotContain("private-marker", output);
    }

    [Fact]
    public async Task OversizedFinalMessageIsRejectedWhileSnapshotTransactionIsOpen()
    {
        var (installation, connection) = Context();
        var (exit, output) = await MfaBackupInventoryCommandTests.Run(Snapshot(installation, connection) + "\n" + new string(' ', 4097),
            TestContext.Current.CancellationToken);
        Assert.Equal(1, exit);
        Assert.Contains("snapshot_ready", output);
        Assert.DoesNotContain("inventory_ready", output);
    }

    [Fact]
    public async Task WrongEnvelopePasswordIsRejectedBeforeDatabaseSnapshot()
    {
        var (installation, connection) = Context();
        var request = JsonNode.Parse(Snapshot(installation, connection))!.AsObject();
        request["envelopePassword"] = "private-marker-wrong-password";
        var (exit, output) = await MfaBackupInventoryCommandTests.Run(request.ToJsonString(), TestContext.Current.CancellationToken);
        Assert.Equal(1, exit);
        Assert.Equal("{\"status\":\"rejected\",\"code\":\"mfa_backup_envelope_rejected\"}" + Environment.NewLine, output);
    }

    // Exposed only in the test assembly for the coordinator's synthetic operator harness.
    public static byte[] Envelope(Guid installation)
    {
        var ring = Encoding.UTF8.GetBytes(MfaKeyJson.Ring(installation,
            MfaKeyJson.Entry(1, "retired") + "," + MfaKeyJson.Entry(2, "retired") + "," + MfaKeyJson.Entry(7, "active")));
        var keys = new[] { 1, 2, 7 }.Select(version => (Version: version, Key: RandomNumberGenerator.GetBytes(32))).ToArray();
        try
        {
            using var payload = MfaKeyRecoveryPayload.Serialize(ring, installation, keys);
            return MfaKeyRecoveryEnvelope.Seal(Password, payload.Bytes);
        }
        finally { foreach (var key in keys) CryptographicOperations.ZeroMemory(key.Key); }
    }

    internal static string Snapshot(Guid installation, string connection) => JsonSerializer.Serialize(new
    {
        operation = "snapshot", installationId = installation.ToString("D"), connectionString = connection,
        envelopeBase64 = Convert.ToBase64String(Envelope(installation)), envelopePassword = Password
    });

    internal static (Guid Installation, string Connection) Context()
    {
        var connection = Environment.GetEnvironmentVariable("RACKCLICK_TEST_MFA_BACKUP_CONNECTION");
        var installation = Environment.GetEnvironmentVariable("RACKCLICK_TEST_MFA_BACKUP_INSTALLATION");
        Assert.SkipUnless(!string.IsNullOrEmpty(connection) && !string.IsNullOrEmpty(installation), "Requires an explicit F0602 native backup laboratory.");
        return (Guid.ParseExact(installation!, "D"), connection!);
    }
}

// Run separately while the coordinator has placed a recovery marker on the same isolated DB.
public sealed class MfaBackupInventoryMarkedPostgresTests
{
    [Fact]
    public async Task SharedDatabaseCommentMarkerRejectsSnapshotBeforeAnyPositiveResponse()
    {
        var (installation, connection) = MfaBackupInventoryPostgresTests.Context();
        var (exit, output) = await MfaBackupInventoryCommandTests.Run(
            MfaBackupInventoryPostgresTests.Snapshot(installation, connection), TestContext.Current.CancellationToken);
        Assert.Equal(1, exit);
        Assert.Equal("{\"status\":\"rejected\",\"code\":\"mfa_backup_identity_rejected\"}" + Environment.NewLine, output);
    }
}
