using System.ComponentModel;
using System.Runtime.InteropServices;
using System.Runtime.Versioning;
using System.Security.AccessControl;
using System.Security.Cryptography;
using System.Security.Principal;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;
using Microsoft.Win32.SafeHandles;

namespace RackClick.Server;

internal sealed record WindowsMfaMaintenancePending(Guid OperationId, int Candidate, string CatalogHash,
    byte[] OriginalRing, byte[] FinalRing, string State);

// F-06.02. Sólo el coordinador local elevado usa este almacén. No altera claves DPAPI ni crea el almacén de claves.
// ACL privada desde creación; handles de directorios retenidos sin FILE_SHARE_DELETE; journal inmutable y fence durable
// preceden a File.Replace. La copia original privada/flush sustituye al backup nativo (que copiaría la DACL del servicio).
// No se afirma transacción DB/disco ni durabilidad universal ante pérdida de alimentación.
[SupportedOSPlatform("windows")]
internal sealed partial class WindowsMfaMaintenanceStore : IDisposable
{
    internal const string FenceFileName = "mfa-maintenance-fence.json";
    internal const string ManagementFolderName = "mfa-maintenance";
    private const string CatalogFileName = "catalog.json";
    private const string LockFileName = "maintenance.lock";
    private const int MaxCatalogBytes = 16 * 1024 * 1024;
    private const int MaxJournalBytes = 256 * 1024;
    private const uint Read = 0x80000000, Write = 0x40000000, Delete = 0x10000, ReadControl = 0x20000;
    private const uint Attributes = 0x80, BackupSemantics = 0x02000000, OpenReparse = 0x00200000;
    private readonly Guid _installation;
    private readonly string _root, _folder, _management, _ring, _fence;
    private readonly SecurityIdentifier _serviceReader;
    private readonly SecurityIdentifier[] _trusted;
    private readonly HashSet<string> _trustedValues;
    private readonly WindowsMfaKeyFileReader _reader;
    private readonly List<SafeFileHandle> _directories = [];
    private FileStream? _lock;
    private bool _disposed;
    internal Action<string>? Checkpoint { get; set; }

    internal WindowsMfaMaintenanceStore(string instancesRoot, Guid installationId, SecurityIdentifier serviceReader,
        IReadOnlyCollection<SecurityIdentifier> trusted)
    {
        if (!Path.IsPathFullyQualified(instancesRoot) || installationId == Guid.Empty || trusted.Count == 0 || trusted.Contains(serviceReader))
            throw Invalid("invalid constructor arguments");
        _root = Path.TrimEndingDirectorySeparator(Path.GetFullPath(instancesRoot));
        _installation = installationId;
        _serviceReader = serviceReader;
        _trusted = trusted.Distinct().ToArray();
        _trustedValues = _trusted.Select(s => s.Value).ToHashSet(StringComparer.Ordinal);
        _reader = new WindowsMfaKeyFileReader(serviceReader, _trustedValues);
        _folder = Path.Combine(_root, installationId.ToString("D"));
        _management = Path.Combine(_folder, ManagementFolderName);
        _ring = Path.Combine(_folder, WindowsMfaKeyProvider.KeysFolderName, MfaKeyRing.RingFileName);
        _fence = Path.Combine(_folder, FenceFileName);
        try
        {
            HoldAncestors(Path.GetDirectoryName(_ring)!);
            _reader.RequireSafeFolder(_root);
            _reader.RequireSafeFolder(_folder);
            _reader.RequireSafeFolder(Path.GetDirectoryName(_ring)!);
            if (!Exists(_management)) CreatePrivateDirectory(_management);
            var handle = Open(_management, Read, 3, directory: true);
            try
            {
                RequirePrivate(Security(handle), directory: true);
                _directories.Add(handle);
            }
            catch { handle.Dispose(); throw; }
        }
        catch { Dispose(); throw; }
    }

    internal IDisposable AcquireLock()
    {
        RequireAlive();
        if (_lock is not null) throw new InvalidOperationException("mfa_maintenance_lock_already_held");
        var path = Metadata(LockFileName);
        SafeFileHandle handle;
        if (!Exists(path))
        {
            // CREATE_NEW: a competing creation is never adopted by this acquisition.
            handle = Create(path, serviceRead: false, Read | Write, share: 0);
        }
        else handle = Open(path, Read | Write, share: 0);
        try
        {
            RequirePrivate(Security(handle), directory: false);
            var stream = new FileStream(handle, FileAccess.ReadWrite);
            if (stream.Length != 0) { stream.Dispose(); throw Corrupt("lock content"); }
            _lock = stream;
            return new Lease(this, stream);
        }
        catch { handle.Dispose(); throw; }
    }

    internal byte[] ReadCatalog() => ReadPrivate(Metadata(CatalogFileName), MaxCatalogBytes);

    internal string CreateCatalog(byte[] catalog)
    {
        RequireLocked();
        RequireNoPending();
        RequireCatalogSize(catalog);
        CreateContent(Metadata(CatalogFileName), catalog);
        return Hash(ReadCatalog());
    }

    internal void ReplaceCatalog(byte[] next, string expectedCurrentSha256)
    {
        RequireLocked();
        RequireNoPending();
        RequireCatalogSize(next);
        var current = ReadCatalog();
        RequireHash(current, expectedCurrentSha256);
        var stage = Metadata("catalog.stage-" + Guid.NewGuid().ToString("N") + ".json");
        var backup = Metadata("catalog.previous-" + Guid.NewGuid().ToString("N") + ".json");
        var identity = IdentityAt(Metadata(CatalogFileName));
        CreateContent(stage, next);
        RequireHash(ReadPrivate(stage, MaxCatalogBytes), Hash(next));
        RequireHash(ReadCatalog(), expectedCurrentSha256);
        RequireIdentity(IdentityAt(Metadata(CatalogFileName)), identity);
        File.Replace(stage, Metadata(CatalogFileName), backup, false);
        RequireHash(ReadPrivate(backup, MaxCatalogBytes), expectedCurrentSha256);
        RequireHash(ReadCatalog(), Hash(next));
    }

    internal byte[] ReadRing()
    {
        RequireAlive();
        var bytes = _reader.ReadValidated(_ring, MfaKeyRing.MaxRingFileBytes);
        MfaKeyRing.Parse(bytes, _installation);
        return bytes;
    }

    internal WindowsMfaMaintenancePending? Pending => ReadPending();

    internal WindowsMfaMaintenancePending? ReadPending()
    {
        RequireAlive();
        if (!Exists(_fence))
        {
            // A prepared journal without a verified completion is never treated as a fresh installation.
            foreach (var path in Directory.EnumerateFiles(_management, "*.prepared.json"))
            {
                var journal = ReadJournal(path);
                if (!Exists(OperationPath(journal.OperationId, "verified"))) throw Corrupt("prepared operation without fence");
                RequireCompletion(journal, "verified");
            }
            return null;
        }
        var (pending, _) = LoadPending();
        var state = Exists(OperationPath(pending.OperationId, "verified")) ? "verified" :
            Exists(OperationPath(pending.OperationId, "complete")) ? "complete" : "prepared";
        if (state != "prepared") RequireCompletion(pending, state);
        return new(pending.OperationId, pending.Candidate, pending.CatalogHash, pending.OriginalRing.ToArray(), pending.FinalRing.ToArray(), state);
    }

    internal void Prepare(Guid operationId, int candidate, byte[] originalRing, byte[] finalRing, string catalogHash)
    {
        RequireLocked();
        RequireNoPending();
        if (operationId == Guid.Empty) throw Invalid("empty operation");
        ValidateReduction(candidate, originalRing, finalRing);
        RequireHash(ReadCatalog(), catalogHash);
        RequireHash(ReadRing(), Hash(originalRing));
        var originalIdentity = IdentityAt(_ring);
        var originalCopy = OperationPath(operationId, "original-ring");
        var finalCopy = OperationPath(operationId, "final-ring");
        var stage = OperationPath(operationId, "stage-ring");
        CreateContent(originalCopy, originalRing);
        CreateContent(finalCopy, finalRing);
        var stageIdentity = CreateContent(stage, finalRing);
        RequireHash(ReadPrivate(originalCopy, MfaKeyRing.MaxRingFileBytes), Hash(originalRing));
        RequireHash(ReadPrivate(finalCopy, MfaKeyRing.MaxRingFileBytes), Hash(finalRing));
        // An empty/partial fence already blocks admission. No cleanup on any failure after its exclusive creation.
        using var fence = Create(_fence, serviceRead: true, Read | Write, share: 1);
        var fenceIdentity = Information(fence);
        var journal = new Journal(1, _installation, "rc_db_" + _installation.ToString("N"), _serviceReader.Value,
            WindowsIdentity.GetCurrent().User?.Value ?? throw Invalid("operator SID missing"), "retire", operationId,
            candidate, catalogHash, Hash(originalRing), Hash(finalRing), originalRing.ToArray(), finalRing.ToArray(),
            originalIdentity, stageIdentity, fenceIdentity);
        var journalBytes = JsonSerializer.SerializeToUtf8Bytes(journal);
        CreateContent(OperationPath(operationId, "prepared"), journalBytes);
        var fenceBytes = JsonSerializer.SerializeToUtf8Bytes(new Fence(1, _installation, operationId, Hash(journalBytes)));
        WriteFlush(fence, fenceBytes);
        // Close the writer before approved reader validation (no FILE_SHARE_WRITE).
        fence.Dispose();
        LoadPending();
        Checkpoint?.Invoke("fence_created");
    }

    internal void Publish(Guid operationId)
    {
        RequireLocked();
        var (journal, _) = LoadPending();
        RequireOperation(journal, operationId);
        var current = ReadRing();
        if (Hash(current) == journal.FinalHash)
        {
            RequireIdentity(IdentityAt(_ring), journal.StageIdentity);
            return;
        }
        RequireHash(current, journal.OriginalHash);
        RequireIdentity(IdentityAt(_ring), journal.OriginalIdentity);
        var stage = OperationPath(operationId, "stage-ring");
        RequireHash(ReadPrivate(stage, MfaKeyRing.MaxRingFileBytes), journal.FinalHash);
        RequireIdentity(IdentityAt(stage), journal.StageIdentity);
        Checkpoint?.Invoke("before_publish");
        // Repeat after the injection point; same bytes in a replacement object are insufficient.
        LoadPending();
        RequireHash(ReadRing(), journal.OriginalHash);
        RequireIdentity(IdentityAt(_ring), journal.OriginalIdentity);
        RequireHash(ReadPrivate(stage, MfaKeyRing.MaxRingFileBytes), journal.FinalHash);
        RequireIdentity(IdentityAt(stage), journal.StageIdentity);
        // Preserve private original-ring.json instead of native backup, which would inherit the service-readable ring DACL.
        File.Replace(stage, _ring, null, false);
        Checkpoint?.Invoke("after_publish");
        RequireHash(ReadRing(), journal.FinalHash);
        RequireIdentity(IdentityAt(_ring), journal.StageIdentity);
    }

    internal void Complete(Guid operationId)
    {
        RequireLocked();
        if (!Exists(_fence))
        {
            var previous = ReadJournal(OperationPath(operationId, "prepared"));
            RequireCompletion(previous, "complete");
            RequireCompletion(previous, "verified");
            RequireHash(ReadRing(), previous.FinalHash);
            RequireIdentity(IdentityAt(_ring), previous.StageIdentity);
            return;
        }
        var (journal, fenceBytes) = LoadPending();
        RequireOperation(journal, operationId);
        RequireHash(ReadRing(), journal.FinalHash);
        RequireIdentity(IdentityAt(_ring), journal.StageIdentity);
        Checkpoint?.Invoke("before_complete");
        LoadPending();
        RequireHash(ReadRing(), journal.FinalHash);
        RequireIdentity(IdentityAt(_ring), journal.StageIdentity);
        WriteCompletion(journal, "complete");
        WriteCompletion(journal, "verified");
        // Delete only the exact fence object recorded before its content was written. Hash and ACL use this same handle.
        using var handle = Open(_fence, Read | Delete, share: 1);
        RequireIdentity(Information(handle), journal.FenceIdentity);
        var security = Security(handle);
        RequireServiceFile(security);
        RequireHash(ReadHandle(handle, 4096), Hash(fenceBytes));
        var disposition = new FileDisposition { DeleteFile = true };
        if (!SetFileInformationByHandle(handle, 4, ref disposition, (uint)Marshal.SizeOf<FileDisposition>())) throw NativeFailure("delete fence");
    }

    private (Journal Journal, byte[] FenceBytes) LoadPending()
    {
        using var handle = Open(_fence, Read, share: 1);
        RequireServiceFile(Security(handle));
        var fenceBytes = ReadHandle(handle, 4096);
        var fence = Decode<Fence>(fenceBytes);
        if (fence.FormatVersion != 1 || fence.InstallationId != _installation || fence.OperationId == Guid.Empty) throw Corrupt("fence identity");
        var path = OperationPath(fence.OperationId, "prepared");
        var bytes = ReadPrivate(path, MaxJournalBytes);
        RequireHash(bytes, fence.JournalHash);
        var journal = ReadJournal(path);
        RequireIdentity(Information(handle), journal.FenceIdentity);
        RequireOperation(journal, fence.OperationId);
        RequireHash(ReadCatalog(), journal.CatalogHash);
        RequireHash(ReadPrivate(OperationPath(journal.OperationId, "original-ring"), MfaKeyRing.MaxRingFileBytes), journal.OriginalHash);
        RequireHash(ReadPrivate(OperationPath(journal.OperationId, "final-ring"), MfaKeyRing.MaxRingFileBytes), journal.FinalHash);
        return (journal, fenceBytes);
    }

    private Journal ReadJournal(string path)
    {
        var journal = Decode<Journal>(ReadPrivate(path, MaxJournalBytes));
        if (journal.FormatVersion != 1 || journal.InstallationId != _installation || journal.Database != "rc_db_" + _installation.ToString("N") ||
            journal.ReaderSid != _serviceReader.Value || journal.OperationId == Guid.Empty || journal.Mode != "retire" ||
            string.IsNullOrEmpty(journal.OperatorSid) || path != OperationPath(journal.OperationId, "prepared")) throw Corrupt("journal identity");
        ValidateReduction(journal.Candidate, journal.OriginalRing, journal.FinalRing);
        RequireHash(journal.OriginalRing, journal.OriginalHash);
        RequireHash(journal.FinalRing, journal.FinalHash);
        RequireDigest(journal.CatalogHash);
        return journal;
    }

    private void WriteCompletion(Journal journal, string state)
    {
        var path = OperationPath(journal.OperationId, state);
        if (Exists(path)) { RequireCompletion(journal, state); return; }
        CreateContent(path, JsonSerializer.SerializeToUtf8Bytes(CompletionFor(journal, state)));
        RequireCompletion(journal, state);
    }

    private Completion CompletionFor(Journal journal, string state) => new(1, _installation, journal.OperationId,
        Hash(ReadPrivate(OperationPath(journal.OperationId, "prepared"), MaxJournalBytes)), journal.FinalHash, state);

    private void RequireCompletion(Journal journal, string state)
    {
        var actual = Decode<Completion>(ReadPrivate(OperationPath(journal.OperationId, state), 4096));
        if (actual != CompletionFor(journal, state)) throw Corrupt("completion mismatch");
    }

    private void ValidateReduction(int candidate, byte[] original, byte[] final)
    {
        var before = MfaKeyRing.Parse(original, _installation);
        var after = MfaKeyRing.Parse(final, _installation);
        if (candidate <= 0 || before.RequireEntry(candidate).State == MfaKeyState.Active ||
            !before.Entries.Where(e => e.Version != candidate).SequenceEqual(after.Entries)) throw Corrupt("invalid reduction");
    }

    private void RequireNoPending()
    {
        RequireNoRotationPending();
        if (ReadPending() is not null) throw Corrupt("pending operation");
    }

    private byte[] ReadPrivate(string path, int maximum)
    {
        RequireAlive();
        using var handle = Open(path, Read, share: 1);
        var identity = Information(handle);
        RequirePrivate(Security(handle), directory: false);
        var content = ReadHandle(handle, maximum);
        RequireIdentity(Information(handle), identity);
        RequirePrivate(Security(handle), directory: false);
        return content;
    }

    private Identity CreateContent(string path, byte[] bytes)
    {
        using var handle = Create(path, serviceRead: false, Read | Write, share: 1);
        RequirePrivate(Security(handle), directory: false);
        var identity = Information(handle);
        WriteFlush(handle, bytes);
        RequireHash(ReadHandle(handle, Math.Max(bytes.Length, 1)), Hash(bytes));
        return identity;
    }

    private static byte[] ReadHandle(SafeFileHandle handle, int maximum)
    {
        var length = RandomAccess.GetLength(handle);
        if (length < 1 || length > maximum) throw Corrupt("metadata length");
        var bytes = new byte[(int)length];
        var offset = 0;
        while (offset < bytes.Length)
        {
            var count = RandomAccess.Read(handle, bytes.AsSpan(offset), offset);
            if (count == 0) throw Corrupt("short metadata read");
            offset += count;
        }
        return bytes;
    }

    private static void WriteFlush(SafeFileHandle handle, byte[] bytes)
    {
        RandomAccess.Write(handle, bytes, 0);
        if (!FlushFileBuffers(handle)) throw NativeFailure("flush");
    }

    private void HoldAncestors(string folder)
    {
        var ancestors = new Stack<string>();
        for (string? path = folder; path is not null; path = Path.GetDirectoryName(Path.TrimEndingDirectorySeparator(path)))
        {
            ancestors.Push(path);
            if (Path.GetPathRoot(path) == path) break;
        }
        // Attribute-only handles do not participate in all Windows sharing checks. Request data read to pin renames.
        while (ancestors.Count > 0) _directories.Add(Open(ancestors.Pop(), Read, share: 3, directory: true));
    }

    private void CreatePrivateDirectory(string path)
    {
        WithSecurity(directory: true, serviceRead: false, attributes =>
        {
            if (!CreateDirectoryW(ExtendedLocalPath(path), ref attributes)) throw NativeFailure("exclusive directory creation");
            return true;
        });
    }

    private SafeFileHandle Create(string path, bool serviceRead, uint access, uint share) => WithSecurity(false, serviceRead, attributes =>
    {
        var handle = CreateFileW(ExtendedLocalPath(path), access, share, ref attributes, 1, Attributes | OpenReparse, IntPtr.Zero);
        if (handle.IsInvalid) { handle.Dispose(); throw NativeFailure("exclusive file creation"); }
        try { RequireObject(handle, path, directory: false); return handle; }
        catch { handle.Dispose(); throw; }
    });

    private T WithSecurity<T>(bool directory, bool serviceRead, Func<SecurityAttributes, T> action)
    {
        FileSystemSecurity security = directory ? new DirectorySecurity() : new FileSecurity();
        security.SetAccessRuleProtection(true, false);
        var inheritance = directory ? InheritanceFlags.ContainerInherit | InheritanceFlags.ObjectInherit : InheritanceFlags.None;
        foreach (var sid in _trusted)
            security.AddAccessRule(new FileSystemAccessRule(sid, FileSystemRights.FullControl, inheritance, PropagationFlags.None, AccessControlType.Allow));
        if (serviceRead) security.AddAccessRule(new FileSystemAccessRule(_serviceReader, FileSystemRights.ReadAndExecute, AccessControlType.Allow));
        var descriptor = security.GetSecurityDescriptorBinaryForm();
        var pinned = GCHandle.Alloc(descriptor, GCHandleType.Pinned);
        try
        {
            return action(new SecurityAttributes { Length = (uint)Marshal.SizeOf<SecurityAttributes>(), Descriptor = pinned.AddrOfPinnedObject() });
        }
        finally { pinned.Free(); }
    }

    private static SafeFileHandle Open(string path, uint access, uint share, bool directory = false)
    {
        var handle = CreateFileW(ExtendedLocalPath(path), access, share, IntPtr.Zero, 3, OpenReparse | (directory ? BackupSemantics : 0), IntPtr.Zero);
        if (handle.IsInvalid) { handle.Dispose(); throw NativeFailure("open object"); }
        try { RequireObject(handle, path, directory); return handle; }
        catch { handle.Dispose(); throw; }
    }

    private static string ExtendedLocalPath(string path)=>path.Length>=248&&path.Length>=3&&path[1]==':'&&path[2]=='\\'?@"\\?\"+path:path;

    private static void RequireObject(SafeFileHandle handle, string path, bool directory)
    {
        var info = NativeInformation(handle);
        if ((info.Attributes & 0x400) != 0 || ((info.Attributes & 0x10) != 0) != directory || (!directory && info.NumberOfLinks != 1))
            throw UnsafePath("reparse, kind or hard links");
        var buffer = new StringBuilder(1024);
        var length = GetFinalPathNameByHandleW(handle, buffer, (uint)buffer.Capacity, 0);
        if (length >= buffer.Capacity)
        {
            buffer.EnsureCapacity((int)length + 1);
            length = GetFinalPathNameByHandleW(handle, buffer, (uint)buffer.Capacity, 0);
        }
        if (length == 0 || length >= buffer.Capacity) throw UnsafePath("unavailable final path");
        var finalPath = buffer.ToString();
        if (finalPath.StartsWith(@"\\?\UNC\", StringComparison.Ordinal)) finalPath = @"\\" + finalPath[8..];
        else if (finalPath.StartsWith(@"\\?\", StringComparison.Ordinal)) finalPath = finalPath[4..];
        var expected = Path.GetFullPath(path);
        var longBuffer = new StringBuilder(32768);
        var longLength = GetLongPathNameW(expected, longBuffer, (uint)longBuffer.Capacity);
        if (longLength > 0 && longLength < longBuffer.Capacity) expected = longBuffer.ToString();
        if (!StringComparer.OrdinalIgnoreCase.Equals(Path.TrimEndingDirectorySeparator(expected), Path.TrimEndingDirectorySeparator(finalPath)))
            throw UnsafePath("redirected path");
    }

    private FileSystemSecurity Security(SafeFileHandle handle)
    {
        // GetSecurityInfo is handle based and supports directories as well as files.
        var result = GetSecurityInfo(handle, 1, 5, out _, out _, out _, out _, out var descriptor);
        if (result != 0) throw new IOException("mfa_maintenance_security_unavailable", new Win32Exception((int)result));
        try
        {
            var length = GetSecurityDescriptorLength(descriptor);
            var bytes = new byte[length];
            Marshal.Copy(descriptor, bytes, 0, bytes.Length);
            var security = new FileSecurity();
            security.SetSecurityDescriptorBinaryForm(bytes);
            return security;
        }
        finally { LocalFree(descriptor); }
    }

    private void RequirePrivate(FileSystemSecurity security, bool directory)
    {
        var raw = new RawSecurityDescriptor(security.GetSecurityDescriptorBinaryForm(), 0);
        if (!security.AreAccessRulesProtected || raw.Owner is null || !_trustedValues.Contains(raw.Owner.Value) || raw.DiscretionaryAcl is null)
            throw UnsafeAccess("private owner or DACL");
        var found = new HashSet<string>(StringComparer.Ordinal);
        foreach (var entry in raw.DiscretionaryAcl)
        {
            if (entry is not CommonAce ace || ace.AceType != AceType.AccessAllowed || ace.IsCallback ||
                !_trustedValues.Contains(ace.SecurityIdentifier.Value) || ace.AccessMask != (int)FileSystemRights.FullControl ||
                (ace.AceFlags & (AceFlags.InheritOnly | AceFlags.Inherited | AceFlags.NoPropagateInherit)) != 0 ||
                (!directory && ace.AceFlags != AceFlags.None)) throw UnsafeAccess("private ACE");
            found.Add(ace.SecurityIdentifier.Value);
        }
        if (!found.SetEquals(_trustedValues)) throw UnsafeAccess("missing trusted principal");
    }

    private void RequireServiceFile(FileSystemSecurity security)
    {
        var raw = new RawSecurityDescriptor(security.GetSecurityDescriptorBinaryForm(), 0);
        if (!security.AreAccessRulesProtected || raw.Owner is null || !_trustedValues.Contains(raw.Owner.Value) || raw.DiscretionaryAcl is null)
            throw UnsafeAccess("fence owner or DACL");
        var found = new HashSet<string>(StringComparer.Ordinal);
        foreach (var entry in raw.DiscretionaryAcl)
        {
            if (entry is not CommonAce ace || ace.AceType != AceType.AccessAllowed || ace.IsCallback || ace.AceFlags != AceFlags.None)
                throw UnsafeAccess("fence ACE type");
            var trusted = _trustedValues.Contains(ace.SecurityIdentifier.Value);
            if ((trusted && ace.AccessMask != (int)FileSystemRights.FullControl) ||
                (!trusted && (ace.SecurityIdentifier != _serviceReader || ace.AccessMask != (int)(FileSystemRights.ReadAndExecute | FileSystemRights.Synchronize))))
                throw UnsafeAccess("fence permissions");
            found.Add(ace.SecurityIdentifier.Value);
        }
        if (!found.SetEquals(_trustedValues.Append(_serviceReader.Value))) throw UnsafeAccess("fence principal missing");
    }

    private static T Decode<T>(byte[] bytes)
    {
        try
        {
            var value = JsonSerializer.Deserialize<T>(bytes, new JsonSerializerOptions { UnmappedMemberHandling = JsonUnmappedMemberHandling.Disallow, MaxDepth = 8 })
                ?? throw Corrupt("null metadata");
            // The immutable format is the canonical encoding emitted here. This also rejects duplicate/missing properties.
            if (!JsonSerializer.SerializeToUtf8Bytes(value).SequenceEqual(bytes)) throw Corrupt("noncanonical metadata");
            return value;
        }
        catch (JsonException) { throw Corrupt("invalid metadata JSON"); }
    }

    private Identity IdentityAt(string path)
    {
        using var handle = Open(path, Attributes, 1);
        return Information(handle);
    }
    private static Identity Information(SafeFileHandle handle)
    {
        var info = NativeInformation(handle);
        return new(info.Volume, ((ulong)info.IndexHigh << 32) | info.IndexLow);
    }
    private static NativeInfo NativeInformation(SafeFileHandle handle)
    {
        if (!GetFileInformationByHandle(handle, out var info)) throw NativeFailure("object identity");
        return info;
    }
    private static void RequireIdentity(Identity actual, Identity expected)
    {
        if (actual != expected) throw UnsafePath("object substituted");
    }
    private static string Hash(byte[] content) => Convert.ToHexStringLower(SHA256.HashData(content));
    private static void RequireDigest(string hash)
    {
        if (hash.Length != 64 || hash.Any(c => !char.IsAsciiHexDigit(c))) throw Corrupt("digest format");
    }
    private static void RequireHash(byte[] content, string expected)
    {
        RequireDigest(expected);
        if (!StringComparer.OrdinalIgnoreCase.Equals(Hash(content), expected)) throw Corrupt("hash mismatch");
    }
    private static void RequireCatalogSize(byte[] content)
    {
        if (content.Length is < 1 or > MaxCatalogBytes) throw Invalid("catalog size");
    }
    private static void RequireOperation(Journal journal, Guid operation)
    {
        if (journal.OperationId != operation) throw Corrupt("operation mismatch");
    }
    private string Metadata(string name) => Path.Combine(_management, name);
    private string OperationPath(Guid operation, string kind) => Metadata(operation.ToString("N") + "." + kind + ".json");
    private static bool Exists(string path) => File.Exists(path) || Directory.Exists(path);
    private void RequireAlive() => ObjectDisposedException.ThrowIf(_disposed, this);
    private void RequireLocked()
    {
        RequireAlive();
        if (_lock is null) throw new InvalidOperationException("mfa_maintenance_local_lock_required");
        RequirePrivate(Security(_directories[^1]), directory: true);
    }
    public void Dispose()
    {
        _lock?.Dispose();
        _lock = null;
        foreach (var directory in _directories) directory.Dispose();
        _directories.Clear();
        _disposed = true;
    }
    private static IOException NativeFailure(string detail) => new("mfa_maintenance_io: " + detail, new Win32Exception(Marshal.GetLastWin32Error()));
    private static MfaKeyRingException Invalid(string detail) => new(MfaKeyRingErrorKind.InvalidFormat, "mfa_maintenance_invalid: " + detail);
    private static MfaKeyRingException Corrupt(string detail) => new(MfaKeyRingErrorKind.Corrupt, "mfa_maintenance_corrupt: " + detail);
    private static MfaKeyRingException UnsafePath(string detail) => new(MfaKeyRingErrorKind.UnsafePath, "mfa_maintenance_path: " + detail);
    private static MfaKeyRingException UnsafeAccess(string detail) => new(MfaKeyRingErrorKind.UnsafeAccess, "mfa_maintenance_acl: " + detail);

    private sealed class Lease(WindowsMfaMaintenanceStore store, FileStream stream) : IDisposable
    {
        public void Dispose()
        {
            if (ReferenceEquals(store._lock, stream)) { store._lock = null; stream.Dispose(); }
        }
    }
    private sealed record Identity(uint Volume, ulong Index);
    private sealed record Journal(int FormatVersion, Guid InstallationId, string Database, string ReaderSid, string OperatorSid,
        string Mode, Guid OperationId, int Candidate, string CatalogHash, string OriginalHash, string FinalHash,
        byte[] OriginalRing, byte[] FinalRing, Identity OriginalIdentity, Identity StageIdentity, Identity FenceIdentity);
    private sealed record Fence(int FormatVersion, Guid InstallationId, Guid OperationId, string JournalHash);
    private sealed record Completion(int FormatVersion, Guid InstallationId, Guid OperationId, string JournalHash, string FinalHash, string State);
    [StructLayout(LayoutKind.Sequential)] private struct SecurityAttributes { public uint Length; public IntPtr Descriptor; public int Inherit; }
    [StructLayout(LayoutKind.Sequential)] private struct FileTime { public uint Low, High; }
    [StructLayout(LayoutKind.Sequential)] private struct NativeInfo
    {
        public uint Attributes; public FileTime Created, Accessed, Written; public uint Volume, SizeHigh, SizeLow, NumberOfLinks, IndexHigh, IndexLow;
    }
    [StructLayout(LayoutKind.Sequential)] private struct FileDisposition { [MarshalAs(UnmanagedType.Bool)] public bool DeleteFile; }
    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern SafeFileHandle CreateFileW(string path, uint access, uint share, IntPtr security, uint creation, uint flags, IntPtr template);
    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern SafeFileHandle CreateFileW(string path, uint access, uint share, ref SecurityAttributes security, uint creation, uint flags, IntPtr template);
    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)] [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool CreateDirectoryW(string path, ref SecurityAttributes security);
    [DllImport("kernel32.dll", SetLastError = true)] [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool FlushFileBuffers(SafeFileHandle handle);
    [DllImport("kernel32.dll", SetLastError = true)] [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool GetFileInformationByHandle(SafeFileHandle handle, out NativeInfo info);
    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern uint GetFinalPathNameByHandleW(SafeFileHandle handle, StringBuilder path, uint length, uint flags);
    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern uint GetLongPathNameW(string shortPath, StringBuilder longPath, uint length);
    [DllImport("advapi32.dll", SetLastError = true)]
    private static extern uint GetSecurityInfo(SafeFileHandle handle, uint type, uint information, out IntPtr owner, out IntPtr group, out IntPtr dacl, out IntPtr sacl, out IntPtr descriptor);
    [DllImport("advapi32.dll", SetLastError = true)]
    private static extern uint GetSecurityDescriptorLength(IntPtr descriptor);
    [DllImport("kernel32.dll")] private static extern IntPtr LocalFree(IntPtr memory);
    [DllImport("kernel32.dll", SetLastError = true)] [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool SetFileInformationByHandle(SafeFileHandle handle, int informationClass, ref FileDisposition information, uint size);
}
