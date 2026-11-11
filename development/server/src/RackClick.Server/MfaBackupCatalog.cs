using System.Globalization;
using System.Runtime.InteropServices;
using System.Runtime.Versioning;
using System.Security.Cryptography;
using System.Security.Principal;
using System.Text;
using System.Text.Json;
using Microsoft.Win32.SafeHandles;

namespace RackClick.Server;

internal sealed class MfaBackupCatalogException : Exception
{
    internal MfaBackupCatalogException() : base("mfa_backup_catalog_rejected") { }
    public string Code => Message;
}

internal sealed class MfaBackupCatalogDocument
{
    internal MfaBackupCatalogDocument(Guid installationId, Guid catalogId, string operatorSid, DateTime confirmedUtc,
        string coverage, IEnumerable<string> roots, IEnumerable<MfaBackupCatalogEntry> entries, string digest)
    {
        InstallationId = installationId; CatalogId = catalogId; OperatorSid = operatorSid; ConfirmedUtc = confirmedUtc;
        Coverage = coverage; Roots = Array.AsReadOnly(roots.ToArray()); Entries = Array.AsReadOnly(entries.ToArray()); Digest = digest;
    }
    public Guid InstallationId { get; }
    public Guid CatalogId { get; }
    public string OperatorSid { get; }
    public DateTime ConfirmedUtc { get; }
    public string Coverage { get; }
    public IReadOnlyList<string> Roots { get; }
    public IReadOnlyList<MfaBackupCatalogEntry> Entries { get; }
    public string Digest { get; }
}

internal sealed class MfaBackupCatalogEntry
{
    internal MfaBackupCatalogEntry(string backupDirectory, string receiptBase64, string receiptSha256, MfaBackupCatalogReceipt receipt)
    { BackupDirectory = backupDirectory; ReceiptBase64 = receiptBase64; ReceiptSha256 = receiptSha256; Receipt = receipt; }
    public string BackupDirectory { get; }
    public string ReceiptBase64 { get; }
    public string ReceiptSha256 { get; }
    internal MfaBackupCatalogReceipt Receipt { get; }
}

internal sealed record MfaBackupCatalogReceipt(Guid InstallationId, Guid BackupId, string InventorySha256,
    string ManifestSha256, string DumpSha256, string EnvelopeSha256);

internal sealed class MfaBackupCatalogSnapshot : IDisposable
{
    private List<IDisposable>? _handles;
    internal MfaBackupCatalogSnapshot(MfaBackupCatalogDocument catalog, IEnumerable<MfaBackupKeyInventory> backups, List<IDisposable> handles)
    {
        InstallationId = catalog.InstallationId; CatalogId = catalog.CatalogId; Digest = catalog.Digest;
        Backups = Array.AsReadOnly(backups.ToArray()); _handles = handles;
    }
    public IReadOnlyList<MfaBackupKeyInventory> Backups { get; }
    public string Digest { get; }
    public Guid CatalogId { get; }
    public Guid InstallationId { get; }
    public void Dispose()
    {
        var handles = Interlocked.Exchange(ref _handles, null);
        if (handles is null) return;
        for (var index = handles.Count - 1; index >= 0; index--) handles[index].Dispose();
    }
}

// La autoridad, DACL y pin del catálogo se verifican por el almacén/CLI antes de Parse.
// No descubre medios desconectados ni demuestra que un administrador declaró todas las raíces.
// No abre DB, sobres o claves. Los pines protegidos autentican los bytes; las ACL del backup no son autoridad.
[SupportedOSPlatform("windows")]
internal static class MfaBackupCatalog
{
    internal const int MaxCatalogBytes = 1024 * 1024;
    internal const int MaxRoots = 32;
    internal const int MaxEntries = 1024;
    internal const string CoverageDeclaration = "all-retained-roots-declared";
    private static readonly string[] Fields = ["format", "formatVersion", "installationId", "catalogId", "operatorSid", "confirmedUtc", "coverage", "roots", "entries"];
    private static readonly string[] EntryFields = ["backupDirectory", "receiptBase64", "receiptSha256"];
    private static readonly string[] ReceiptFields = ["format", "formatVersion", "installationId", "backupId", "inventorySha256", "manifestSha256", "dumpSha256", "envelopeSha256"];
    private static readonly string[] ManifestFields = ["schemaVersion", "kind", "postgresVersion", "format", "dumpFile", "dumpBytes", "dumpSha256", "createdUtc"];
    private static readonly JsonDocumentOptions JsonOptions = new() { MaxDepth = 6, AllowTrailingCommas = false, CommentHandling = JsonCommentHandling.Disallow };

    internal static MfaBackupCatalogDocument Parse(byte[] bytes, Guid expectedInstallation, string expectedDigest)
    {
        if (expectedInstallation == Guid.Empty || bytes is null || bytes.Length is 0 or > MaxCatalogBytes) throw Rejected();
        RequireHash(expectedDigest);
        var copy = (byte[])bytes.Clone();
        if (Hash(copy) != expectedDigest) throw Rejected();
        try
        {
            using var json = JsonDocument.Parse(copy, JsonOptions);
            var root = json.RootElement;
            Closed(root, Fields);
            if (Text(root, "format") != "RackClick.MfaBackupCatalog" || Integer(root, "formatVersion") != 1) throw Rejected();
            var installation = Id(root, "installationId");
            if (installation != expectedInstallation) throw Rejected();
            var catalogId = Id(root, "catalogId");
            var operatorSid = Text(root, "operatorSid");
            RequireOperatorSid(operatorSid);
            var date = Utc(Text(root, "confirmedUtc"));
            var coverage = Text(root, "coverage");
            if (coverage != CoverageDeclaration) throw Rejected();
            var rootsJson = root.GetProperty("roots");
            if (rootsJson.ValueKind != JsonValueKind.Array || rootsJson.GetArrayLength() is < 1 or > MaxRoots) throw Rejected();
            var roots = rootsJson.EnumerateArray().Select(value => CanonicalPath(Text(value))).ToArray();
            for (var index = 0; index < roots.Length; index++)
                for (var other = 0; other < index; other++)
                    if (Same(roots[index], roots[other]) || Below(roots[index], roots[other]) || Below(roots[other], roots[index])) throw Rejected();
            var entriesJson = root.GetProperty("entries");
            if (entriesJson.ValueKind != JsonValueKind.Array || entriesJson.GetArrayLength() > MaxEntries) throw Rejected();
            var entries = new List<MfaBackupCatalogEntry>();
            var directories = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            var backupIds = new HashSet<Guid>();
            foreach (var value in entriesJson.EnumerateArray())
            {
                Closed(value, EntryFields);
                var path = CanonicalPath(Text(value, "backupDirectory"));
                if (roots.Count(folder => Same(Path.GetDirectoryName(path)!, folder)) != 1 || !directories.Add(path)) throw Rejected();
                var base64 = Text(value, "receiptBase64");
                var receiptHash = Text(value, "receiptSha256");
                RequireHash(receiptHash);
                var receipt = Receipt(base64, receiptHash, installation);
                if (!backupIds.Add(receipt.BackupId)) throw Rejected();
                entries.Add(new MfaBackupCatalogEntry(path, base64, receiptHash, receipt));
            }
            return new MfaBackupCatalogDocument(installation, catalogId, operatorSid, date, coverage, roots, entries, expectedDigest);
        }
        catch (JsonException) { throw Rejected(); }
    }

    internal static MfaBackupCatalogSnapshot Validate(MfaBackupCatalogDocument model) => Open(model);

    internal static MfaBackupCatalogSnapshot Open(MfaBackupCatalogDocument model)
    {
        if (model is null || model.Roots.Count is < 1 or > MaxRoots || model.Entries.Count > MaxEntries ||
            model.Coverage != CoverageDeclaration || model.InstallationId == Guid.Empty || model.CatalogId == Guid.Empty) throw Rejected();
        var handles = new List<IDisposable>();
        var success = false;
        try
        {
            var folders = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            foreach (var root in model.Roots) PinFolderChain(root, handles, folders);
            RequireRootSets(model);
            var inventories = new List<MfaBackupKeyInventory>();
            foreach (var entry in model.Entries)
            {
                PinFolderChain(entry.BackupDirectory, handles, folders);
                var database = Path.Combine(entry.BackupDirectory, "database");
                PinFolderChain(database, handles, folders);
                ExactNames(entry.BackupDirectory, ["database", "mfa-inventory.json"]);
                ExactNames(database, ["manifest.json", "data.dump"]);
                var manifest = PinFile(Path.Combine(database, "manifest.json"), handles);
                var dump = PinFile(Path.Combine(database, "data.dump"), handles);
                var sidecar = PinFile(Path.Combine(entry.BackupDirectory, "mfa-inventory.json"), handles);
                var manifestBytes = Read(manifest, 16 * 1024);
                if (Hash(manifestBytes) != entry.Receipt.ManifestSha256 || HashStream(dump) != entry.Receipt.DumpSha256) throw Rejected();
                ValidateManifest(manifestBytes, dump.Length, entry.Receipt.DumpSha256);
                var inventory = MfaKeyRetention.ParseBackupInventory(Read(sidecar, MfaKeyRetention.MaxInventoryBytes), model.InstallationId,
                    entry.Receipt.InventorySha256, entry.Receipt.ManifestSha256, entry.Receipt.DumpSha256, entry.Receipt.EnvelopeSha256);
                if (inventory.BackupId != entry.Receipt.BackupId) throw Rejected();
                inventories.Add(inventory);
                // Detecta entradas añadidas mientras se abrían los ficheros de esta carpeta.
                ExactNames(entry.BackupDirectory, ["database", "mfa-inventory.json"]);
                ExactNames(database, ["manifest.json", "data.dump"]);
            }
            RequireRootSets(model);
            var result = new MfaBackupCatalogSnapshot(model, inventories, handles);
            success = true;
            return result;
        }
        catch (JsonException) { throw Rejected(); }
        catch (MfaKeyRetentionException) { throw Rejected(); }
        catch (IOException) { throw Rejected(); }
        catch (UnauthorizedAccessException) { throw Rejected(); }
        finally
        {
            if (!success) for (var index = handles.Count - 1; index >= 0; index--) handles[index].Dispose();
        }
    }

    private static MfaBackupCatalogReceipt Receipt(string base64, string expectedHash, Guid installation)
    {
        if (base64.Length is 0 or > 8192) throw Rejected();
        byte[] bytes;
        try { bytes = Convert.FromBase64String(base64); }
        catch (FormatException) { throw Rejected(); }
        if (Convert.ToBase64String(bytes) != base64 || bytes.Length > 4096 || Hash(bytes) != expectedHash) throw Rejected();
        using var json = JsonDocument.Parse(bytes, JsonOptions);
        var root = json.RootElement;
        Closed(root, ReceiptFields);
        if (Text(root, "format") != "RackClick.MfaBackupInventoryReceipt" || Integer(root, "formatVersion") != 1 || Id(root, "installationId") != installation) throw Rejected();
        var result = new MfaBackupCatalogReceipt(installation, Id(root, "backupId"), Text(root, "inventorySha256"),
            Text(root, "manifestSha256"), Text(root, "dumpSha256"), Text(root, "envelopeSha256"));
        RequireHash(result.InventorySha256); RequireHash(result.ManifestSha256); RequireHash(result.DumpSha256); RequireHash(result.EnvelopeSha256);
        return result;
    }

    private static void ValidateManifest(byte[] bytes, long length, string digest)
    {
        using var json = JsonDocument.Parse(bytes, JsonOptions);
        var root = json.RootElement;
        Closed(root, ManifestFields);
        if (Integer(root, "schemaVersion") != 1 || Text(root, "kind") != "RackClickDatabaseBackup" || Text(root, "postgresVersion") != "17.11" ||
            Text(root, "format") != "custom" || Text(root, "dumpFile") != "data.dump" || Text(root, "dumpSha256") != digest) throw Rejected();
        var size = root.GetProperty("dumpBytes");
        if (size.ValueKind != JsonValueKind.Number || !size.TryGetInt64(out var number) || number < 5 || number != length) throw Rejected();
        _ = Utc(Text(root, "createdUtc"));
    }

    private static void RequireRootSets(MfaBackupCatalogDocument model)
    {
        foreach (var root in model.Roots)
        {
            var expected = model.Entries.Where(entry => Same(Path.GetDirectoryName(entry.BackupDirectory)!, root)).Select(entry => entry.BackupDirectory).ToHashSet(StringComparer.OrdinalIgnoreCase);
            var actual = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            foreach (var path in Directory.EnumerateFileSystemEntries(root))
            {
                var attributes = File.GetAttributes(path);
                if ((attributes & FileAttributes.ReparsePoint) != 0 || (attributes & FileAttributes.Directory) == 0 || !actual.Add(path)) throw Rejected();
                // Do not traverse unknown directories, including pending/legacy backups.
                if (!expected.Contains(path)) throw Rejected();
            }
            if (!actual.SetEquals(expected)) throw Rejected();
        }
    }

    private static void ExactNames(string folder, string[] expected)
    {
        var names = new HashSet<string>(StringComparer.Ordinal);
        foreach (var path in Directory.EnumerateFileSystemEntries(folder))
        {
            if ((File.GetAttributes(path) & FileAttributes.ReparsePoint) != 0 || !names.Add(Path.GetFileName(path)) || !expected.Contains(Path.GetFileName(path), StringComparer.Ordinal)) throw Rejected();
        }
        if (!names.SetEquals(expected)) throw Rejected();
    }

    private static void PinFolderChain(string path, List<IDisposable> handles, HashSet<string> pinned)
    {
        // Iterativo: la profundidad controlada por el JSON no puede agotar la pila del proceso.
        var root = Path.GetPathRoot(path)!;
        var end = root.Length;
        while (true)
        {
            var folder = path[..end];
            if (!pinned.Contains(folder))
            {
                // Ancestros fijados contra sustitución, sin exigir una ACL de propietario de backup.
                // FILE_READ_ATTRIBUTES por sí solo no activa la protección de compartición frente a
                // rename de una carpeta vacía. GENERIC_READ fija también ese objeto sin hijos abiertos.
                var handle = CreateFile(folder, 0x80000000, 1, IntPtr.Zero, 3, 0x02000000 | 0x00200000, IntPtr.Zero);
                handles.Add(handle);
                if (handle.IsInvalid) throw Rejected();
                RequireObject(handle, folder, true);
                pinned.Add(folder);
            }
            if (end == path.Length) break;
            var next = path.IndexOf('\\', end == root.Length ? end : end + 1);
            end = next < 0 ? path.Length : next;
        }
    }

    private static FileStream PinFile(string path, List<IDisposable> handles)
    {
        // OPEN_REPARSE_POINT avoids following a last-component link even during a race.
        var handle = CreateFile(path, 0x80000000, 1, IntPtr.Zero, 3, 0x00200000, IntPtr.Zero);
        if (handle.IsInvalid) { handle.Dispose(); throw Rejected(); }
        FileStream? stream = null;
        try
        {
            RequireObject(handle, path, false);
            stream = new FileStream(handle, FileAccess.Read);
            handles.Add(stream);
            return stream;
        }
        finally { if (stream is null) handle.Dispose(); }
    }

    private static void RequireObject(SafeFileHandle handle, string path, bool directory)
    {
        if (!GetFileInformationByHandle(handle, out var info) || (info.Attributes & 0x400) != 0 ||
            ((info.Attributes & 0x10) != 0) != directory || (!directory && info.Links != 1)) throw Rejected();
        var buffer = new StringBuilder(32768);
        var length = GetFinalPathNameByHandle(handle, buffer, (uint)buffer.Capacity, 0);
        if (length == 0 || length >= buffer.Capacity) throw Rejected();
        var actual = buffer.ToString();
        if (actual.StartsWith(@"\\?\UNC\", StringComparison.OrdinalIgnoreCase)) actual = @"\\" + actual[8..];
        else if (actual.StartsWith(@"\\?\", StringComparison.Ordinal)) actual = actual[4..];
        if (!Same(actual, path)) throw Rejected();
    }

    private static byte[] Read(FileStream stream, int max)
    {
        if (stream.Length is <= 0 || stream.Length > max) throw Rejected();
        var bytes = new byte[(int)stream.Length];
        stream.Position = 0; stream.ReadExactly(bytes); return bytes;
    }
    private static string HashStream(FileStream stream) { stream.Position = 0; return Convert.ToHexStringLower(SHA256.HashData(stream)); }
    private static string Hash(byte[] bytes) => Convert.ToHexStringLower(SHA256.HashData(bytes));
    private static void Closed(JsonElement value, string[] expected)
    {
        if (value.ValueKind != JsonValueKind.Object) throw Rejected();
        var names = new HashSet<string>(StringComparer.Ordinal);
        foreach (var property in value.EnumerateObject())
        {
            string name;
            try { name = property.Name; }
            catch (InvalidOperationException) { throw Rejected(); }
            if (!expected.Contains(name, StringComparer.Ordinal) || !names.Add(name)) throw Rejected();
        }
        if (names.Count != expected.Length) throw Rejected();
    }
    private static string Text(JsonElement root, string field) => Text(root.GetProperty(field));
    private static string Text(JsonElement value)
    {
        if (value.ValueKind != JsonValueKind.String) throw Rejected();
        try { return value.GetString()!; }
        catch (InvalidOperationException) { throw Rejected(); }
    }
    private static int Integer(JsonElement root, string field)
    {
        var value = root.GetProperty(field);
        if (value.ValueKind != JsonValueKind.Number || !value.TryGetInt32(out var number)) throw Rejected();
        return number;
    }
    private static Guid Id(JsonElement root, string field)
    {
        var text = Text(root, field);
        if (!Guid.TryParseExact(text, "D", out var id) || id == Guid.Empty || id.ToString("D") != text) throw Rejected();
        return id;
    }
    private static DateTime Utc(string text)
    {
        if (!DateTime.TryParseExact(text, "O", CultureInfo.InvariantCulture, DateTimeStyles.RoundtripKind, out var value) || value.Kind != DateTimeKind.Utc) throw Rejected();
        return value;
    }
    private static void RequireHash(string hash)
    {
        if (hash is null || hash.Length != 64 || hash.Any(c => c is not (>= '0' and <= '9') and not (>= 'a' and <= 'f'))) throw Rejected();
    }
    private static void RequireOperatorSid(string text)
    {
        SecurityIdentifier sid;
        try { sid = new SecurityIdentifier(text); }
        catch (ArgumentException) { throw Rejected(); }
        if (sid.Value != text || (!sid.IsAccountSid() && !sid.IsWellKnown(WellKnownSidType.LocalSystemSid)) || sid.AccountDomainSid?.Value == sid.Value) throw Rejected();
    }
    private static string CanonicalPath(string path)
    {
        if (path.Length is 0 or > 32700 || path.Contains('/') || path.StartsWith(@"\\?\", StringComparison.Ordinal) || path.StartsWith(@"\\.\", StringComparison.Ordinal) || !Path.IsPathFullyQualified(path)) throw Rejected();
        string full;
        try { full = Path.GetFullPath(path); }
        catch (ArgumentException) { throw Rejected(); }
        catch (NotSupportedException) { throw Rejected(); }
        catch (PathTooLongException) { throw Rejected(); }
        if (full != path || (path.EndsWith('\\') && path != Path.GetPathRoot(path))) throw Rejected();
        var remainder = path[Path.GetPathRoot(path)!.Length..];
        foreach (var segment in remainder.Split('\\', StringSplitOptions.RemoveEmptyEntries))
        {
            if (segment.EndsWith('.') || segment.EndsWith(' ') || segment.IndexOfAny(Path.GetInvalidFileNameChars()) >= 0) throw Rejected();
            var stem = segment.Split('.')[0].ToUpperInvariant();
            if (stem is "CON" or "PRN" or "AUX" or "NUL" || (stem.Length == 4 && (stem.StartsWith("COM", StringComparison.Ordinal) || stem.StartsWith("LPT", StringComparison.Ordinal)) && stem[3] is >= '1' and <= '9')) throw Rejected();
        }
        return full;
    }
    private static bool Same(string left, string right) => string.Equals(left, right, StringComparison.OrdinalIgnoreCase);
    private static bool Below(string child, string parent) => child.StartsWith(parent.TrimEnd('\\') + "\\", StringComparison.OrdinalIgnoreCase);
    private static MfaBackupCatalogException Rejected() => new();

    [StructLayout(LayoutKind.Sequential)]
    private struct FileTime { public uint Low; public uint High; }
    [StructLayout(LayoutKind.Sequential)]
    private struct FileInformation
    {
        public uint Attributes; public FileTime Created; public FileTime Accessed; public FileTime Written;
        public uint Volume; public uint SizeHigh; public uint SizeLow; public uint Links; public uint IndexHigh; public uint IndexLow;
    }
    [DllImport("kernel32.dll", EntryPoint = "CreateFileW", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern SafeFileHandle CreateFile(string path, uint access, uint share, IntPtr security, uint disposition, uint flags, IntPtr template);
    [DllImport("kernel32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool GetFileInformationByHandle(SafeFileHandle handle, out FileInformation info);
    [DllImport("kernel32.dll", EntryPoint = "GetFinalPathNameByHandleW", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern uint GetFinalPathNameByHandle(SafeFileHandle handle, StringBuilder path, uint capacity, uint flags);
}
