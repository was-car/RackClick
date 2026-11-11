using System.Globalization;
using System.Runtime.InteropServices;
using System.Runtime.Versioning;
using System.Security.Cryptography;
using System.Security.Principal;
using System.Text;
using System.Text.Json.Nodes;
using RackClick.Server;
using Xunit;

namespace RackClick.Quality.Tests;

[SupportedOSPlatform("windows")]
public sealed class MfaBackupCatalogTests
{
    [Fact]
    public void DeclaredEmptyRootIsVerifiedButEmptyRootListIsNeverComplete()
    {
        using var fixture = new Fixture();
        using var snapshot = MfaBackupCatalog.Open(fixture.Parse());
        Assert.Empty(snapshot.Backups);
        Assert.Equal(fixture.Installation, snapshot.InstallationId);
        Assert.Equal(fixture.CatalogId, snapshot.CatalogId);
        Assert.Equal(Hash(fixture.Bytes()), snapshot.Digest);
        fixture.Catalog["roots"] = new JsonArray();
        Reject(() => fixture.Parse());
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void EmptyDeclaredRootAndItsAncestorCannotBeRenamedWhileSnapshotIsHeld(bool ancestor)
    {
        using var fixture = new Fixture();
        Assert.Empty(Directory.EnumerateFileSystemEntries(fixture.Root));
        using var snapshot = MfaBackupCatalog.Open(fixture.Parse());
        var folder = ancestor ? fixture.Home : fixture.Root;
        var moved = folder + "-moved";
        try { Assert.Throws<IOException>(() => Directory.Move(folder, moved)); }
        finally
        {
            // El caso RED puede moverlo: devolver sólo nuestra carpeta temporal a su ubicación.
            if (Directory.Exists(moved)) Directory.Move(moved, folder);
        }
        Assert.True(Directory.Exists(fixture.Root));
        snapshot.Dispose();
        Directory.Move(folder, moved);
        Directory.Move(moved, folder);
    }

    [Fact]
    public void ClosedBackupReturnsPinnedInventoryAndRetainsEveryFileUntilDispose()
    {
        using var fixture = new Fixture();
        var directory = fixture.Backup();
        var snapshot = MfaBackupCatalog.Open(fixture.Parse());
        var backup = Assert.Single(snapshot.Backups);
        Assert.Equal(new[] { 2, 7 }, backup.RequiredVersions);
        Assert.Equal(fixture.Installation, backup.InstallationId);
        Assert.Throws<NotSupportedException>(() => ((IList<MfaBackupKeyInventory>)snapshot.Backups).Clear());
        foreach (var file in Directory.GetFiles(directory, "*", SearchOption.AllDirectories))
        {
            Assert.Throws<IOException>(() => File.Open(file, FileMode.Open, FileAccess.Write, FileShare.ReadWrite).Dispose());
            Assert.Throws<IOException>(() => File.Delete(file));
        }
        Assert.Throws<IOException>(() => Directory.Move(directory, directory + "-moved"));
        snapshot.Dispose();
        snapshot.Dispose();
        File.WriteAllText(Path.Combine(directory, "mfa-inventory.json"), "released");
    }

    [Theory]
    [InlineData("extra")]
    [InlineData("incomplete")]
    [InlineData("legacy")]
    [InlineData("unknown")]
    [InlineData("root-file")]
    [InlineData("missing")]
    [InlineData("missing-dump")]
    [InlineData("missing-sidecar")]
    [InlineData("dump-tamper")]
    [InlineData("manifest-tamper")]
    [InlineData("inventory-tamper")]
    [InlineData("database-extra")]
    public void UncertainOrChangedObjectsBlockAndRemainOnDisk(string change)
    {
        using var fixture = new Fixture();
        var backup = fixture.Backup();
        switch (change)
        {
            case "extra": File.WriteAllText(Path.Combine(backup, "extra"), "x"); break;
            case "incomplete": File.WriteAllText(Path.Combine(backup, "INCOMPLETE.json"), "{}"); break;
            case "legacy": Directory.CreateDirectory(Path.Combine(fixture.Root, "legacy")); break;
            case "unknown": Directory.CreateDirectory(Path.Combine(fixture.Root, "pending")); break;
            case "root-file": File.WriteAllText(Path.Combine(fixture.Root, "unregistered"), "x"); break;
            case "missing": Directory.Move(backup, Path.Combine(fixture.Home, "moved")); break;
            case "missing-dump": File.Delete(Path.Combine(backup, "database", "data.dump")); break;
            case "missing-sidecar": File.Delete(Path.Combine(backup, "mfa-inventory.json")); break;
            case "dump-tamper": File.AppendAllText(Path.Combine(backup, "database", "data.dump"), "x"); break;
            case "manifest-tamper": File.AppendAllText(Path.Combine(backup, "database", "manifest.json"), " "); break;
            case "inventory-tamper": File.AppendAllText(Path.Combine(backup, "mfa-inventory.json"), " "); break;
            case "database-extra": Directory.CreateDirectory(Path.Combine(backup, "database", "extra")); break;
        }
        var before = Directory.GetFileSystemEntries(fixture.Home, "*", SearchOption.AllDirectories).Order().ToArray();
        Reject(() => MfaBackupCatalog.Open(fixture.Parse()));
        Assert.Equal(before, Directory.GetFileSystemEntries(fixture.Home, "*", SearchOption.AllDirectories).Order());
        // A failed validation releases already opened files as well.
        using var probe = File.Open(Path.Combine(backup == Path.Combine(fixture.Root, "one") && change == "missing" ? Path.Combine(fixture.Home, "moved") : backup,
            "database", "manifest.json"), FileMode.Open, FileAccess.ReadWrite, FileShare.None);
    }

    [Theory]
    [InlineData("coverage")]
    [InlineData("complete")]
    [InlineData("sid")]
    [InlineData("time")]
    [InlineData("scope")]
    [InlineData("id")]
    [InlineData("roots-overlap")]
    [InlineData("roots-duplicate")]
    [InlineData("roots-relative")]
    [InlineData("roots-alias")]
    [InlineData("entries-duplicate")]
    [InlineData("entries-outside")]
    [InlineData("entries-nested")]
    [InlineData("receipt-hash")]
    [InlineData("receipt-base64")]
    [InlineData("receipt-scope")]
    [InlineData("receipt-extra")]
    [InlineData("receipt-pin")]
    public void CatalogAndReceiptAreClosedScopedCanonicalAndBounded(string change)
    {
        using var fixture = new Fixture();
        fixture.Backup();
        switch (change)
        {
            case "coverage": fixture.Catalog["coverage"] = "some-roots"; break;
            case "complete": fixture.Catalog["complete"] = true; break;
            case "sid": fixture.Catalog["operatorSid"] = "S-1-1-0"; break;
            case "time": fixture.Catalog["confirmedUtc"] = "2026-11-09T12:00:00+01:00"; break;
            case "scope": fixture.Catalog["installationId"] = Guid.NewGuid().ToString("D"); break;
            case "id": fixture.Catalog["catalogId"] = Guid.Empty.ToString("D"); break;
            case "roots-overlap": fixture.Roots.Add(Path.Combine(fixture.Root, "sub")); break;
            case "roots-duplicate": fixture.Roots.Add(fixture.Root.ToUpperInvariant()); break;
            case "roots-relative": fixture.Roots[0] = "relative"; break;
            case "roots-alias": fixture.Roots[0] = fixture.Root + "\\."; break;
            case "entries-duplicate": fixture.Entries.Add(fixture.Entries[0]!.DeepClone()); break;
            case "entries-outside": fixture.Entries[0]!["backupDirectory"] = Path.Combine(fixture.Home, "outside"); break;
            case "entries-nested": fixture.Entries[0]!["backupDirectory"] = Path.Combine(fixture.Root, "one", "nested"); break;
            case "receipt-hash": fixture.Entries[0]!["receiptSha256"] = new string('0', 64); break;
            case "receipt-base64": fixture.Entries[0]!["receiptBase64"] = " " + fixture.Entries[0]!["receiptBase64"]!.GetValue<string>(); break;
            case "receipt-scope": fixture.EditReceipt(receipt => receipt["installationId"] = Guid.NewGuid().ToString("D")); break;
            case "receipt-extra": fixture.EditReceipt(receipt => receipt["extra"] = true); break;
            case "receipt-pin": fixture.EditReceipt(receipt => receipt["dumpSha256"] = "bad"); break;
        }
        Reject(() => fixture.Parse());
    }

    [Fact]
    public void ExternalDigestAndMalformedUnicodeDoNotLeakInput()
    {
        using var fixture = new Fixture();
        Reject(() => MfaBackupCatalog.Parse(fixture.Bytes(), fixture.Installation, new string('0', 64)));
        Reject(() => MfaBackupCatalog.Parse(new byte[1024 * 1024 + 1], fixture.Installation, new string('0', 64)));
        var original = Encoding.UTF8.GetString(fixture.Bytes());
        foreach (var text in new[] { original.Replace("all-retained-roots-declared", "\\uD800"),
            original.Replace("\"coverage\":", "\"\\uD800\":"), original.Replace("\"formatVersion\":1", "\"formatVersion\":1,\"formatVersion\":1") })
        {
            var bytes = Encoding.UTF8.GetBytes(text);
            Reject(() => MfaBackupCatalog.Parse(bytes, fixture.Installation, Hash(bytes)));
        }
    }

    [Fact]
    public void MultipleRootsAndBackupsAreVerifiedAndDuplicateBackupIdsAreRejected()
    {
        using var fixture = new Fixture();
        fixture.Backup();
        var second = Path.Combine(fixture.Home, "second");
        Directory.CreateDirectory(second);
        fixture.Roots.Add(second);
        fixture.Backup("two", second);
        using (var snapshot = MfaBackupCatalog.Open(fixture.Parse())) Assert.Equal(2, snapshot.Backups.Count);
        var first = JsonNode.Parse(Convert.FromBase64String(fixture.Entries[0]!["receiptBase64"]!.GetValue<string>()))!;
        fixture.EditReceipt(receipt => receipt["backupId"] = first["backupId"]!.DeepClone(), 1);
        Reject(() => fixture.Parse());
    }

    [Fact]
    public void RootAndEntryQuotasRejectExcessWithoutProbingPaths()
    {
        using var fixture = new Fixture();
        fixture.Catalog["roots"] = new JsonArray();
        for (var index = 0; index < 32; index++) fixture.Roots.Add(@"C:\catalog-test-" + index.ToString(CultureInfo.InvariantCulture));
        Assert.Equal(32, fixture.Parse().Roots.Count);
        fixture.Roots.Add(@"C:\catalog-test-overflow");
        Reject(() => fixture.Parse());
        fixture.Catalog["roots"] = new JsonArray(fixture.Root);
        fixture.Backup();
        var first = fixture.Entries[0]!.DeepClone();
        fixture.Entries.Clear();
        var shortRoot = Path.Combine(Path.GetPathRoot(fixture.Home)!, "catalog-test");
        fixture.Catalog["roots"] = new JsonArray(shortRoot);
        for (var index = 0; index < 1024; index++)
        {
            var entry = first.DeepClone();
            entry["backupDirectory"] = Path.Combine(shortRoot, "b" + index.ToString(CultureInfo.InvariantCulture));
            var receipt = JsonNode.Parse(Convert.FromBase64String(entry["receiptBase64"]!.GetValue<string>()))!;
            receipt["backupId"] = Guid.NewGuid().ToString("D");
            var bytes = Encoding.UTF8.GetBytes(receipt.ToJsonString());
            entry["receiptBase64"] = Convert.ToBase64String(bytes); entry["receiptSha256"] = Hash(bytes);
            fixture.Entries.Add(entry);
        }
        Assert.Equal(1024, fixture.Parse().Entries.Count);
        fixture.Entries.Add(first);
        Assert.True(fixture.Bytes().Length <= 1024 * 1024);
        Reject(() => fixture.Parse());
    }

    [Theory]
    [InlineData("installationId")]
    [InlineData("backupId")]
    [InlineData("dumpSha256")]
    [InlineData("manifestSha256")]
    [InlineData("envelopeSha256")]
    public void FreshlyPinnedSidecarStillMustMatchEveryReceiptIdentityAndPin(string field)
    {
        using var fixture = new Fixture();
        var backup = fixture.Backup();
        var path = Path.Combine(backup, "mfa-inventory.json");
        var inventory = JsonNode.Parse(File.ReadAllBytes(path))!;
        inventory[field] = field.EndsWith("Id", StringComparison.Ordinal) ? Guid.NewGuid().ToString("D") : new string('f', 64);
        var bytes = Encoding.UTF8.GetBytes(inventory.ToJsonString());
        File.WriteAllBytes(path, bytes);
        fixture.EditReceipt(receipt => receipt["inventorySha256"] = Hash(bytes));
        Reject(() => MfaBackupCatalog.Open(fixture.Parse()));
    }

    [Fact]
    public void NewDirectoryAfterAValidSnapshotBlocksTheNextRecensus()
    {
        using var fixture = new Fixture();
        using var first = MfaBackupCatalog.Open(fixture.Parse());
        Directory.CreateDirectory(Path.Combine(fixture.Root, "new-pending"));
        Reject(() => MfaBackupCatalog.Open(fixture.Parse()));
    }

    [Theory]
    [InlineData("schemaVersion", "2")]
    [InlineData("kind", "\"Wrong\"")]
    [InlineData("postgresVersion", "\"17.10\"")]
    [InlineData("format", "\"plain\"")]
    [InlineData("dumpFile", "\"other.dump\"")]
    [InlineData("dumpBytes", "4")]
    [InlineData("createdUtc", "\"not-date\"")]
    [InlineData("createdUtc", "\"2026-11-09T12:00:00.0000000+01:00\"")]
    public void PinnedButInvalidSqlManifestIsRejected(string field, string value)
    {
        using var fixture = new Fixture();
        var backup = fixture.Backup();
        var path = Path.Combine(backup, "database", "manifest.json");
        var manifest = JsonNode.Parse(File.ReadAllBytes(path))!;
        manifest[field] = JsonNode.Parse(value);
        File.WriteAllBytes(path, Encoding.UTF8.GetBytes(manifest.ToJsonString()));
        fixture.EditReceipt(receipt => receipt["manifestSha256"] = Hash(File.ReadAllBytes(path)));
        Reject(() => MfaBackupCatalog.Open(fixture.Parse()));
    }

    [Fact]
    public void HardLinkedFileAndEmptyJunctionRootAreRejectedWithoutTraversal()
    {
        using var fixture = new Fixture();
        var backup = fixture.Backup();
        var dump = Path.Combine(backup, "database", "data.dump");
        Assert.True(CreateHardLink(Path.Combine(fixture.Home, "alias.dump"), dump, IntPtr.Zero));
        Reject(() => MfaBackupCatalog.Open(fixture.Parse()));
        File.Delete(Path.Combine(fixture.Home, "alias.dump"));
        var target = Path.Combine(fixture.Home, "empty-target");
        Directory.CreateDirectory(target);
        var link = Path.Combine(fixture.Home, "junction");
        var start = new System.Diagnostics.ProcessStartInfo("cmd.exe") { UseShellExecute = false, CreateNoWindow = true };
        start.ArgumentList.Add("/c"); start.ArgumentList.Add("mklink"); start.ArgumentList.Add("/J"); start.ArgumentList.Add(link); start.ArgumentList.Add(target);
        using (var process = System.Diagnostics.Process.Start(start)!) { process.WaitForExit(); Assert.Equal(0, process.ExitCode); }
        fixture.Catalog["roots"] = new JsonArray(link);
        fixture.Catalog["entries"] = new JsonArray();
        Reject(() => MfaBackupCatalog.Open(fixture.Parse()));
        Directory.Delete(link);
    }

    private static string Hash(byte[] bytes) => Convert.ToHexStringLower(SHA256.HashData(bytes));
    private static void Reject(Action action)
    {
        var error = Assert.Throws<MfaBackupCatalogException>(action);
        Assert.Equal("mfa_backup_catalog_rejected", error.Message);
        Assert.Null(error.InnerException);
    }

    private sealed class Fixture : IDisposable
    {
        public string Home { get; } = Path.Combine(Path.GetTempPath(), "RackClick-catalog-" + Guid.NewGuid().ToString("N"));
        public string Root { get; }
        public Guid Installation { get; } = Guid.NewGuid();
        public Guid CatalogId { get; } = Guid.NewGuid();
        public JsonObject Catalog { get; }
        public JsonArray Roots => (JsonArray)Catalog["roots"]!;
        public JsonArray Entries => (JsonArray)Catalog["entries"]!;
        public Fixture()
        {
            Root = Path.Combine(Home, "retained");
            Directory.CreateDirectory(Root);
            Catalog = new JsonObject { ["format"] = "RackClick.MfaBackupCatalog", ["formatVersion"] = 1,
                ["installationId"] = Installation.ToString("D"), ["catalogId"] = CatalogId.ToString("D"),
                ["operatorSid"] = WindowsIdentity.GetCurrent().User!.Value,
                ["confirmedUtc"] = "2026-11-09T12:00:00.0000000Z", ["coverage"] = "all-retained-roots-declared",
                ["roots"] = new JsonArray(Root), ["entries"] = new JsonArray() };
        }
        public byte[] Bytes() => Encoding.UTF8.GetBytes(Catalog.ToJsonString());
        public MfaBackupCatalogDocument Parse() => MfaBackupCatalog.Parse(Bytes(), Installation, Hash(Bytes()));
        public string Backup(string name = "one", string? root = null)
        {
            var backup = Path.Combine(root ?? Root, name);
            Directory.CreateDirectory(Path.Combine(backup, "database"));
            var dump = "PGDMPsynthetic-only"u8.ToArray();
            File.WriteAllBytes(Path.Combine(backup, "database", "data.dump"), dump);
            var manifest = Encoding.UTF8.GetBytes(new JsonObject { ["schemaVersion"] = 1, ["kind"] = "RackClickDatabaseBackup",
                ["postgresVersion"] = "17.11", ["format"] = "custom", ["dumpFile"] = "data.dump", ["dumpBytes"] = dump.Length,
                ["dumpSha256"] = Hash(dump), ["createdUtc"] = "2026-11-09T12:00:00.0000000Z" }.ToJsonString());
            File.WriteAllBytes(Path.Combine(backup, "database", "manifest.json"), manifest);
            var id = Guid.NewGuid();
            var inventory = MfaKeyRetention.SerializeBackupInventory(new MfaBackupKeyInventory(Installation, id,
                Hash(manifest), Hash(dump), new string('e', 64), [2], [2, 7], 7, [2, 7]));
            File.WriteAllBytes(Path.Combine(backup, "mfa-inventory.json"), inventory);
            var receipt = Encoding.UTF8.GetBytes(new JsonObject { ["format"] = "RackClick.MfaBackupInventoryReceipt", ["formatVersion"] = 1,
                ["installationId"] = Installation.ToString("D"), ["backupId"] = id.ToString("D"), ["inventorySha256"] = Hash(inventory),
                ["manifestSha256"] = Hash(manifest), ["dumpSha256"] = Hash(dump), ["envelopeSha256"] = new string('e', 64) }.ToJsonString());
            Entries.Add(new JsonObject { ["backupDirectory"] = backup, ["receiptBase64"] = Convert.ToBase64String(receipt), ["receiptSha256"] = Hash(receipt) });
            return backup;
        }
        public void EditReceipt(Action<JsonNode> edit, int index = 0)
        {
            var entry = Entries[index]!;
            var receipt = JsonNode.Parse(Convert.FromBase64String(entry["receiptBase64"]!.GetValue<string>()))!;
            edit(receipt);
            var bytes = Encoding.UTF8.GetBytes(receipt.ToJsonString());
            entry["receiptBase64"] = Convert.ToBase64String(bytes); entry["receiptSha256"] = Hash(bytes);
        }
        public void Dispose()
        {
            var expected = Path.Combine(Path.GetTempPath(), "RackClick-catalog-");
            if (!Path.GetFullPath(Home).StartsWith(expected, StringComparison.OrdinalIgnoreCase)) throw new InvalidOperationException();
            Directory.Delete(Home, true);
        }
    }

    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool CreateHardLink(string path, string target, IntPtr security);
}
