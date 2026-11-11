using System.Runtime.InteropServices;
using System.Security.Principal;
using System.Text;
using System.Text.Json;
using Microsoft.Win32.SafeHandles;

namespace RackClick.Server;

// Private coordinator contract. Ring JSON contains version metadata only; NewKeyHash hashes the DPAPI file.
// This record is not an HTTP receipt and never contains plaintext keys, TOTP or factor ciphertext.
internal sealed record WindowsMfaRotationPending(Guid OperationId, int NewVersion, string CatalogHash,
    byte[] OriginalRing, byte[] AdditiveRing, byte[] FinalRing, string NewKeyHash, string State);

internal sealed partial class WindowsMfaMaintenanceStore
{
    private const int MaxRotationJournalBytes = 512 * 1024;
    private const int MaxRotationMetadataBytes = 64 * 1024;

    internal void PrepareRotation(Guid operationId, int newVersion, byte[] protectedKeyFile, byte[] originalRing,
        byte[] additiveRing, byte[] finalRing, string catalogHash)
    {
        RequireLocked();
        RequireNoPending();
        if (operationId == Guid.Empty) throw Invalid("empty rotation operation");
        ValidateRotation(newVersion, originalRing, additiveRing, finalRing);
        MfaKeyRing.ParseKeyFile(protectedKeyFile, _installation, newVersion);
        RequireHash(ReadCatalog(), catalogHash);
        var originalIdentity = ReadServiceArtifact(_ring, MfaKeyRing.MaxRingFileBytes, Hash(originalRing));
        var retained = MfaKeyRing.Parse(originalRing, _installation).Entries.Select(entry =>
        {
            var bytes = _reader.ReadValidated(RotationKeyPath(entry.Version), MfaKeyRing.MaxKeyFileBytes);
            MfaKeyRing.ParseKeyFile(bytes, _installation, entry.Version);
            return new RotationRetainedKey(entry.Version, Hash(bytes),
                ReadServiceArtifact(RotationKeyPath(entry.Version), MfaKeyRing.MaxKeyFileBytes, Hash(bytes)));
        }).ToArray();
        if (newVersion <= HighestRotationVersion() || Exists(RotationKeyPath(newVersion)))
            throw Corrupt("rotation version already used");

        // Immutable private copies survive the rename/replace of each publication stage.
        CreateContent(RotationPath(operationId, "original-ring"), originalRing);
        CreateContent(RotationPath(operationId, "additive-ring"), additiveRing);
        CreateContent(RotationPath(operationId, "final-ring"), finalRing);
        CreateContent(RotationPath(operationId, "new-key"), protectedKeyFile);
        var additiveIdentity = CreateContent(RotationPath(operationId, "stage-additive"), additiveRing);
        var finalIdentity = CreateContent(RotationPath(operationId, "stage-final"), finalRing);
        Identity keyIdentity;
        using (var key = Create(RotationPath(operationId, "stage-key"), serviceRead: true, Read | Write, share: 1))
        {
            keyIdentity = Information(key);
            RequireServiceFile(Security(key));
            WriteFlush(key, protectedKeyFile);
            RequireHash(ReadHandle(key, MfaKeyRing.MaxKeyFileBytes), Hash(protectedKeyFile));
        }
        // An empty/partial fence is still an admission blocker. Failures leave all material for diagnosis.
        using var fence = Create(_fence, serviceRead: true, Read | Write, share: 1);
        var journal = new RotationJournal(1, _installation, "rc_db_" + _installation.ToString("N"), _serviceReader.Value,
            WindowsIdentity.GetCurrent().User?.Value ?? throw Invalid("operator SID missing"), "rotate", operationId,
            newVersion, catalogHash, Hash(originalRing), Hash(additiveRing), Hash(finalRing), Hash(protectedKeyFile),
            originalRing.ToArray(), additiveRing.ToArray(), finalRing.ToArray(), originalIdentity, additiveIdentity,
            finalIdentity, keyIdentity, Information(fence), retained);
        var journalBytes = JsonSerializer.SerializeToUtf8Bytes(journal);
        if (journalBytes.Length > MaxRotationJournalBytes) throw Invalid("rotation journal size");
        CreateContent(RotationPath(operationId, "plan"), journalBytes);
        WriteFlush(fence, JsonSerializer.SerializeToUtf8Bytes(new Fence(1, _installation, operationId, Hash(journalBytes))));
        fence.Dispose();
        ReadRotation(operationId);
        Checkpoint?.Invoke("rotation_prepared");
    }

    internal WindowsMfaRotationPending ReadRotation(Guid operationId)
    {
        var (journal, _, state) = LoadRotation(operationId);
        return new(journal.OperationId, journal.NewVersion, journal.CatalogHash, journal.OriginalRing.ToArray(),
            journal.AdditiveRing.ToArray(), journal.FinalRing.ToArray(), journal.NewKeyHash, state);
    }

    internal void PublishRotationKey(Guid operationId)
    {
        RequireLocked();
        var (journal, _, state) = LoadRotation(operationId);
        if (state != "key_staged") return;
        Checkpoint?.Invoke("before_key_publish");
        (journal, _, state) = LoadRotation(operationId);
        if (state != "key_staged") return;
        var stage = RotationPath(operationId, "stage-key");
        using (var handle = Open(stage, Read | Delete, share: 1))
        {
            RequireIdentity(Information(handle), journal.NewKeyIdentity);
            RequireServiceFile(Security(handle));
            RequireHash(ReadHandle(handle, MfaKeyRing.MaxKeyFileBytes), journal.NewKeyHash);
            // Operate on the verified handle. ReplaceIfExists=false never overwrites an unknown live key.
            RenameRotationKey(handle, RotationKeyPath(journal.NewVersion));
            RequireIdentity(Information(handle), journal.NewKeyIdentity);
            RequireServiceFile(Security(handle));
            RequireHash(ReadHandle(handle, MfaKeyRing.MaxKeyFileBytes), journal.NewKeyHash);
        }
        Checkpoint?.Invoke("after_key_publish");
        LoadRotation(operationId);
    }

    internal void PublishRotationAdditive(Guid operationId) => PublishRotationRing(operationId, final: false);
    internal void PublishRotationFinal(Guid operationId) => PublishRotationRing(operationId, final: true);

    private void PublishRotationRing(Guid operationId, bool final)
    {
        RequireLocked();
        var (journal, _, state) = LoadRotation(operationId);
        if (state is "ring_published" or "verified" || (!final && state == "additive_published")) return;
        if (state != (final ? "additive_published" : "key_published")) throw Corrupt("rotation publication order");
        Checkpoint?.Invoke(final ? "before_final_publish" : "before_additive_publish");
        (journal, _, state) = LoadRotation(operationId);
        if (state != (final ? "additive_published" : "key_published")) throw Corrupt("rotation publication changed");
        var stage = RotationPath(operationId, final ? "stage-final" : "stage-additive");
        var hash = final ? journal.FinalHash : journal.AdditiveHash;
        var identity = final ? journal.FinalIdentity : journal.AdditiveIdentity;
        RequireHash(ReadPrivate(stage, MfaKeyRing.MaxRingFileBytes), hash);
        RequireIdentity(IdentityAt(stage), identity);
        // Existing F-06.02 primitive: bound live ring + bound private stage, pinned parents, preserved private copies.
        // No native backup: it would inherit the service-readable ring DACL. No universal power-loss claim.
        File.Replace(stage, _ring, null, false);
        Checkpoint?.Invoke(final ? "after_final_publish" : "after_additive_publish");
        ReadServiceArtifact(_ring, MfaKeyRing.MaxRingFileBytes, hash, identity);
        LoadRotation(operationId);
    }

    // The coordinator must prove DB commit/data_verified and authorize startup before invoking this filesystem gate.
    // This method alone neither proves those facts nor starts any service.
    internal void CompleteRotation(Guid operationId)
    {
        RequireLocked();
        var (journal, fenceBytes, state) = LoadRotation(operationId);
        if (state == "verified" && fenceBytes is null) return;
        if (state is not ("ring_published" or "verified")) throw Corrupt("rotation final ring required");
        Checkpoint?.Invoke("before_rotation_complete");
        (journal, fenceBytes, state) = LoadRotation(operationId);
        if (state is not ("ring_published" or "verified") || fenceBytes is null) throw Corrupt("rotation completion changed");
        WriteRotationCompletion(journal, "complete");
        WriteRotationCompletion(journal, "verified");
        using (var handle = Open(_fence, Read | Delete, share: 1))
        {
            RequireIdentity(Information(handle), journal.FenceIdentity);
            RequireServiceFile(Security(handle));
            RequireHash(ReadHandle(handle, 4096), Hash(fenceBytes));
            var disposition = new FileDisposition { DeleteFile = true };
            if (!SetFileInformationByHandle(handle, 4, ref disposition, (uint)Marshal.SizeOf<FileDisposition>()))
                throw NativeFailure("delete rotation fence");
        }
        Checkpoint?.Invoke("after_rotation_complete");
    }

    internal void WriteRotationMetadata(Guid operationId, string kind, byte[] bytes)
    {
        RequireLocked();
        var path = RotationMetadataPath(operationId, kind);
        if (bytes.Length is < 1 or > MaxRotationMetadataBytes) throw Invalid("rotation metadata size");
        LoadRotation(operationId);
        if (Exists(path)) { RequireHash(ReadPrivate(path, MaxRotationMetadataBytes), Hash(bytes)); return; }
        CreateContent(path, bytes);
        RequireHash(ReadPrivate(path, MaxRotationMetadataBytes), Hash(bytes));
    }

    internal byte[] ReadRotationMetadata(Guid operationId, string kind)
    {
        var path = RotationMetadataPath(operationId, kind);
        LoadRotation(operationId);
        return ReadPrivate(path, MaxRotationMetadataBytes);
    }

    internal int HighestRotationVersion()
    {
        RequireAlive();
        RequirePrivate(Security(_directories[^1]), directory: true);
        var highest = 0;
        foreach (var path in RotationPlans())
            highest = Math.Max(highest, ReadRotationJournal(path).NewVersion);
        return highest;
    }

    private void RequireNoRotationPending()
    {
        foreach (var path in RotationPlans())
        {
            var journal = ReadRotationJournal(path);
            if (!Exists(RotationPath(journal.OperationId, "verified"))) throw Corrupt("pending rotation operation");
            RequireRotationCompletion(journal, "complete");
            RequireRotationCompletion(journal, "verified");
        }
    }

    private IReadOnlyList<string> RotationPlans()
    {
        var operations = new HashSet<Guid>();
        foreach (var path in Directory.EnumerateFileSystemEntries(_management, "*.rotation-*.json"))
        {
            var name = Path.GetFileName(path);
            var split = name.IndexOf(".rotation-", StringComparison.Ordinal);
            if (split != 32 || !Guid.TryParseExact(name[..split], "N", out var operation) || operation == Guid.Empty)
                throw Corrupt("unknown rotation artifact");
            var kind = name[(split + ".rotation-".Length)..];
            if (kind is not ("plan.json" or "original-ring.json" or "additive-ring.json" or "final-ring.json" or
                "new-key.json" or "stage-additive.json" or "stage-final.json" or "stage-key.json" or "complete.json" or
                "verified.json" or "coordinator-plan.json" or "material-ready.json")) throw Corrupt("unknown rotation artifact");
            if (!File.Exists(RotationPath(operation, "plan"))) throw Corrupt("rotation residue without plan");
            operations.Add(operation);
        }
        return operations.Select(operation => RotationPath(operation, "plan")).ToArray();
    }

    private (RotationJournal Journal, byte[]? FenceBytes, string State) LoadRotation(Guid operationId)
    {
        RequireAlive();
        if (operationId == Guid.Empty) throw Invalid("empty rotation operation");
        RequirePrivate(Security(_directories[^1]), directory: true);
        _reader.RequireSafeFolder(_root);
        _reader.RequireSafeFolder(_folder);
        _reader.RequireSafeFolder(Path.GetDirectoryName(_ring)!);
        var journal = ReadRotationJournal(RotationPath(operationId, "plan"));
        RequireHash(ReadCatalog(), journal.CatalogHash);
        foreach (var key in journal.RetainedKeys)
            ReadServiceArtifact(RotationKeyPath(key.Version), MfaKeyRing.MaxKeyFileBytes, key.Hash, key.Identity);
        var state = RotationRingState(journal);
        var keyLive = Exists(RotationKeyPath(journal.NewVersion));
        if (keyLive)
        {
            ReadServiceArtifact(RotationKeyPath(journal.NewVersion), MfaKeyRing.MaxKeyFileBytes, journal.NewKeyHash, journal.NewKeyIdentity);
            if (Exists(RotationPath(operationId, "stage-key"))) throw Corrupt("duplicate rotation key stage");
            if (state == "key_staged") state = "key_published";
        }
        else
        {
            if (state != "key_staged") throw Corrupt("rotation published ring without key");
            ReadServiceArtifact(RotationPath(operationId, "stage-key"), MfaKeyRing.MaxKeyFileBytes, journal.NewKeyHash, journal.NewKeyIdentity);
        }
        if (state is "key_staged" or "key_published") RequireRotationStage(journal, final: false);
        else if (Exists(RotationPath(operationId, "stage-additive"))) throw Corrupt("duplicate additive stage");
        if (state != "ring_published") RequireRotationStage(journal, final: true);
        else if (Exists(RotationPath(operationId, "stage-final"))) throw Corrupt("duplicate final stage");
        if (Exists(RotationPath(operationId, "complete"))) RequireRotationCompletion(journal, "complete");
        if (Exists(RotationPath(operationId, "verified")))
        {
            RequireRotationCompletion(journal, "complete");
            RequireRotationCompletion(journal, "verified");
            if (state != "ring_published") throw Corrupt("rotation completion ring mismatch");
            state = "verified";
        }
        if (!Exists(_fence))
        {
            if (state != "verified") throw Corrupt("rotation journal without fence");
            return (journal, null, state);
        }
        using var handle = Open(_fence, Read, share: 1);
        RequireServiceFile(Security(handle));
        RequireIdentity(Information(handle), journal.FenceIdentity);
        var fenceBytes = ReadHandle(handle, 4096);
        var fence = Decode<Fence>(fenceBytes);
        if (fence.FormatVersion != 1 || fence.InstallationId != _installation || fence.OperationId != operationId)
            throw Corrupt("rotation fence binding");
        RequireHash(ReadPrivate(RotationPath(operationId, "plan"), MaxRotationJournalBytes), fence.JournalHash);
        return (journal, fenceBytes, state);
    }

    private RotationJournal ReadRotationJournal(string path)
    {
        var journal = Decode<RotationJournal>(ReadPrivate(path, MaxRotationJournalBytes));
        if (journal.FormatVersion != 1 || journal.InstallationId != _installation || journal.Database != "rc_db_" + _installation.ToString("N") ||
            journal.ReaderSid != _serviceReader.Value || journal.OperationId == Guid.Empty || journal.Mode != "rotate" ||
            string.IsNullOrEmpty(journal.OperatorSid) || path != RotationPath(journal.OperationId, "plan")) throw Corrupt("rotation journal identity");
        ValidateRotation(journal.NewVersion, journal.OriginalRing, journal.AdditiveRing, journal.FinalRing);
        RequireDigest(journal.CatalogHash);
        RequireHash(journal.OriginalRing, journal.OriginalHash);
        RequireHash(journal.AdditiveRing, journal.AdditiveHash);
        RequireHash(journal.FinalRing, journal.FinalHash);
        RequireHash(ReadPrivate(RotationPath(journal.OperationId, "original-ring"), MfaKeyRing.MaxRingFileBytes), journal.OriginalHash);
        RequireHash(ReadPrivate(RotationPath(journal.OperationId, "additive-ring"), MfaKeyRing.MaxRingFileBytes), journal.AdditiveHash);
        RequireHash(ReadPrivate(RotationPath(journal.OperationId, "final-ring"), MfaKeyRing.MaxRingFileBytes), journal.FinalHash);
        var keyBytes = ReadPrivate(RotationPath(journal.OperationId, "new-key"), MfaKeyRing.MaxKeyFileBytes);
        RequireHash(keyBytes, journal.NewKeyHash);
        MfaKeyRing.ParseKeyFile(keyBytes, _installation, journal.NewVersion);
        var versions = MfaKeyRing.Parse(journal.OriginalRing, _installation).Entries.Select(e => e.Version);
        if (journal.RetainedKeys is null || !versions.SequenceEqual(journal.RetainedKeys.Select(k => k.Version)))
            throw Corrupt("rotation retained key set");
        foreach (var key in journal.RetainedKeys) RequireDigest(key.Hash);
        return journal;
    }

    private string RotationRingState(RotationJournal journal)
    {
        using var handle = Open(_ring, Read, share: 1);
        RequireServiceFile(Security(handle));
        var identity = Information(handle);
        var bytes = ReadHandle(handle, MfaKeyRing.MaxRingFileBytes);
        MfaKeyRing.Parse(bytes, _installation);
        var hash = Hash(bytes);
        if (hash == journal.OriginalHash) { RequireIdentity(identity, journal.OriginalIdentity); return "key_staged"; }
        if (hash == journal.AdditiveHash) { RequireIdentity(identity, journal.AdditiveIdentity); return "additive_published"; }
        if (hash == journal.FinalHash) { RequireIdentity(identity, journal.FinalIdentity); return "ring_published"; }
        throw Corrupt("rotation live ring mismatch");
    }

    private void RequireRotationStage(RotationJournal journal, bool final)
    {
        var stage = RotationPath(journal.OperationId, final ? "stage-final" : "stage-additive");
        RequireHash(ReadPrivate(stage, MfaKeyRing.MaxRingFileBytes), final ? journal.FinalHash : journal.AdditiveHash);
        RequireIdentity(IdentityAt(stage), final ? journal.FinalIdentity : journal.AdditiveIdentity);
    }

    private Identity ReadServiceArtifact(string path, int maximum, string hash, Identity? expected = null)
    {
        using var handle = Open(path, Read, share: 1);
        var identity = Information(handle);
        if (expected is not null) RequireIdentity(identity, expected);
        RequireServiceFile(Security(handle));
        RequireHash(ReadHandle(handle, maximum), hash);
        RequireIdentity(Information(handle), identity);
        RequireServiceFile(Security(handle));
        return identity;
    }

    private void ValidateRotation(int version, byte[] original, byte[] additive, byte[] final)
    {
        var before = MfaKeyRing.Parse(original, _installation);
        var plus = MfaKeyRing.Parse(additive, _installation);
        var after = MfaKeyRing.Parse(final, _installation);
        if (version <= before.Entries.Max(e => e.Version) || plus.Entries.Count != before.Entries.Count + 1 ||
            !before.Entries.SequenceEqual(plus.Entries.Where(e => e.Version != version))) throw Corrupt("invalid additive rotation");
        var added = plus.RequireEntry(version);
        if (added.State != MfaKeyState.Retired) throw Corrupt("new additive key active");
        var active = before.Entries.Single(e => e.State == MfaKeyState.Active).Version;
        var expected = plus.Entries.Select(e => e.Version == version ? e with { State = MfaKeyState.Active } :
            e.Version == active ? e with { State = MfaKeyState.Retired } : e);
        if (!expected.SequenceEqual(after.Entries)) throw Corrupt("invalid final rotation");
    }

    private void WriteRotationCompletion(RotationJournal journal, string state)
    {
        var path = RotationPath(journal.OperationId, state);
        if (!Exists(path)) CreateContent(path, JsonSerializer.SerializeToUtf8Bytes(RotationCompletionFor(journal, state)));
        RequireRotationCompletion(journal, state);
    }

    private Completion RotationCompletionFor(RotationJournal journal, string state) => new(1, _installation, journal.OperationId,
        Hash(ReadPrivate(RotationPath(journal.OperationId, "plan"), MaxRotationJournalBytes)), journal.FinalHash, state);

    private void RequireRotationCompletion(RotationJournal journal, string state)
    {
        var actual = Decode<Completion>(ReadPrivate(RotationPath(journal.OperationId, state), 4096));
        if (actual != RotationCompletionFor(journal, state)) throw Corrupt("rotation completion mismatch");
    }

    private string RotationMetadataPath(Guid operationId, string kind)
    {
        if (operationId == Guid.Empty || kind is not ("coordinator-plan" or "material-ready")) throw Invalid("rotation metadata kind");
        return RotationPath(operationId, kind);
    }

    private string RotationPath(Guid operationId, string kind) => OperationPath(operationId, "rotation-" + kind);
    private string RotationKeyPath(int version) => Path.Combine(Path.GetDirectoryName(_ring)!, MfaKeyRing.KeyFileName(version));

    // Same native layout as the existing key-store writer; all bytes begin zeroed and target is absolute.
    private static void RenameRotationKey(SafeFileHandle handle, string target)
    {
        var name = Encoding.Unicode.GetBytes(target);
        var size = 2 * IntPtr.Size + 4 + name.Length + sizeof(char);
        var buffer = Marshal.AllocHGlobal(size);
        try
        {
            Marshal.Copy(new byte[size], 0, buffer, size);
            Marshal.WriteIntPtr(buffer, IntPtr.Size, IntPtr.Zero);
            Marshal.WriteInt32(buffer, 2 * IntPtr.Size, name.Length);
            Marshal.Copy(name, 0, IntPtr.Add(buffer, 2 * IntPtr.Size + 4), name.Length);
            if (!SetFileInformationByHandle(handle, 3, buffer, (uint)size)) throw NativeFailure("publish rotation key");
        }
        finally { Marshal.FreeHGlobal(buffer); }
    }

    private sealed record RotationRetainedKey(int Version, string Hash, Identity Identity);
    private sealed record RotationJournal(int FormatVersion, Guid InstallationId, string Database, string ReaderSid, string OperatorSid,
        string Mode, Guid OperationId, int NewVersion, string CatalogHash, string OriginalHash, string AdditiveHash, string FinalHash,
        string NewKeyHash, byte[] OriginalRing, byte[] AdditiveRing, byte[] FinalRing, Identity OriginalIdentity, Identity AdditiveIdentity,
        Identity FinalIdentity, Identity NewKeyIdentity, Identity FenceIdentity, RotationRetainedKey[] RetainedKeys);

    [DllImport("kernel32.dll", SetLastError = true)] [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool SetFileInformationByHandle(SafeFileHandle file, int informationClass, IntPtr information, uint bufferSize);
}
