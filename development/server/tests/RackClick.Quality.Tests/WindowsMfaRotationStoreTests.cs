using System.Runtime.Versioning;
using System.Security.AccessControl;
using System.Security.Cryptography;
using System.Security.Principal;
using RackClick.Server;
using Xunit;

namespace RackClick.Quality.Tests;

[SupportedOSPlatform("windows")]
public sealed class WindowsMfaRotationStoreTests
{
    [Fact]
    public void PublishesNewKeyBeforeAdditiveAndFinalAndRetainsEveryOriginalKey()
    {
        using var lab = new Lab();
        var old = File.ReadAllBytes(lab.Key(1));
        using (var store = lab.Open())
        using (store.AcquireLock())
        {
            lab.Prepare(store);
            Assert.Equal("key_staged", store.ReadRotation(lab.Operation).State);
            Assert.Throws<MfaKeyRingException>(() => store.PublishRotationAdditive(lab.Operation));
            Assert.Throws<MfaKeyRingException>(() => store.CompleteRotation(lab.Operation));
            store.PublishRotationKey(lab.Operation);
            store.PublishRotationKey(lab.Operation);
            Assert.Equal(lab.NewKey, File.ReadAllBytes(lab.Key(2)));
            Assert.Equal(lab.Original, store.ReadRing());
            store.PublishRotationAdditive(lab.Operation);
            store.PublishRotationAdditive(lab.Operation);
            Assert.Equal(lab.Additive, store.ReadRing());
            Assert.Equal(1, MfaKeyRing.Parse(store.ReadRing(), lab.Installation).Entries.Single(e => e.State == MfaKeyState.Active).Version);
            store.PublishRotationFinal(lab.Operation);
            store.PublishRotationFinal(lab.Operation);
            Assert.Equal(lab.Final, store.ReadRing());
            store.CompleteRotation(lab.Operation);
            store.CompleteRotation(lab.Operation);
            Assert.Equal("verified", store.ReadRotation(lab.Operation).State);
            Assert.False(File.Exists(lab.Fence));
        }
        using var reopened = lab.Open();
        using var lease = reopened.AcquireLock();
        reopened.CompleteRotation(lab.Operation);
        Assert.Equal(2, reopened.HighestRotationVersion());
        Assert.Equal(old, File.ReadAllBytes(lab.Key(1)));
        Assert.Equal(lab.NewKey, File.ReadAllBytes(lab.Key(2)));
    }

    [Theory]
    [InlineData("rotation_prepared")]
    [InlineData("before_key_publish")]
    [InlineData("after_key_publish")]
    [InlineData("before_additive_publish")]
    [InlineData("after_additive_publish")]
    [InlineData("before_final_publish")]
    [InlineData("after_final_publish")]
    [InlineData("before_rotation_complete")]
    [InlineData("after_rotation_complete")]
    public void InterruptedPublicationResumesByBoundIdentityWithNoRepeatedKeyCreation(string checkpoint)
    {
        using var lab = new Lab();
        using (var store = lab.Open())
        using (store.AcquireLock())
        {
            store.Checkpoint = point => { if (point == checkpoint) throw new Interrupted(); };
            Assert.Throws<Interrupted>(() =>
            {
                lab.Prepare(store);
                store.PublishRotationKey(lab.Operation);
                store.PublishRotationAdditive(lab.Operation);
                store.PublishRotationFinal(lab.Operation);
                store.CompleteRotation(lab.Operation);
            });
        }
        using var resumed = lab.Open();
        using var lease = resumed.AcquireLock();
        var pending = resumed.ReadRotation(lab.Operation);
        Assert.Equal(lab.Operation, pending.OperationId);
        Assert.Equal(Convert.ToHexStringLower(SHA256.HashData(lab.NewKey)), pending.NewKeyHash);
        resumed.PublishRotationKey(lab.Operation);
        resumed.PublishRotationAdditive(lab.Operation);
        resumed.PublishRotationFinal(lab.Operation);
        resumed.CompleteRotation(lab.Operation);
        Assert.Equal(lab.Final, resumed.ReadRing());
        Assert.False(File.Exists(lab.Fence));
    }

    [Theory]
    [InlineData("before_key_publish", "key")]
    [InlineData("before_additive_publish", "ring")]
    [InlineData("before_final_publish", "ring")]
    [InlineData("before_rotation_complete", "fence")]
    public void SameBytesInAnotherObjectCannotBeAdoptedOrDeleted(string checkpoint, string shape)
    {
        using var lab = new Lab();
        using var store = lab.Open();
        using var lease = store.AcquireLock();
        lab.Prepare(store);
        store.Checkpoint = point =>
        {
            if (point != checkpoint) return;
            var path = shape switch { "key" => lab.StageKey, "fence" => lab.Fence, _ => lab.Ring };
            var bytes = File.ReadAllBytes(path);
            var security = new FileInfo(path).GetAccessControl();
            File.Move(path, path + ".foreign-reserved");
            File.WriteAllBytes(path, bytes);
            new FileInfo(path).SetAccessControl(security);
        };
        Assert.Throws<MfaKeyRingException>(() =>
        {
            store.PublishRotationKey(lab.Operation);
            store.PublishRotationAdditive(lab.Operation);
            store.PublishRotationFinal(lab.Operation);
            store.CompleteRotation(lab.Operation);
        });
        Assert.True(File.Exists(lab.Fence));
    }

    [Theory]
    [InlineData("original-change")]
    [InlineData("additive-active-new")]
    [InlineData("final-old-still-active")]
    [InlineData("removed-old")]
    [InlineData("version-reuse")]
    [InlineData("foreign-key")]
    public void InvalidModelsFailBeforeCreatingFenceOrPublishingKey(string shape)
    {
        using var lab = new Lab();
        using var store = lab.Open();
        using var lease = store.AcquireLock();
        var catalog = store.CreateCatalog([1]);
        var original = shape == "original-change" ? lab.RingBytes(MfaKeyJson.Entry(1, "active", "2026-10-26T10:00:00Z")) : lab.Original;
        var additive = shape == "additive-active-new" ? lab.Final : lab.Additive;
        var final = shape == "final-old-still-active" ? lab.Additive : shape == "removed-old" ? lab.RingBytes(MfaKeyJson.Entry(2, "active")) : lab.Final;
        var key = shape == "foreign-key" ? MfaKeyJson.Bytes(MfaKeyJson.Key(Guid.NewGuid(), 2, Convert.ToBase64String([1, 2]))) : lab.NewKey;
        Assert.ThrowsAny<Exception>(() => store.PrepareRotation(lab.Operation, shape == "version-reuse" ? 1 : 2, key, original, additive, final, catalog));
        Assert.False(File.Exists(lab.Fence));
        Assert.False(File.Exists(lab.Key(2)));
        Assert.Equal(lab.Original, store.ReadRing());
    }

    [Fact]
    public void RetireAndRotationCannotShareFenceAndMissingFenceDoesNotAdmitNewWork()
    {
        using var lab = new Lab();
        using var store = lab.Open();
        using var lease = store.AcquireLock();
        lab.Prepare(store);
        Assert.ThrowsAny<Exception>(() => store.Prepare(Guid.NewGuid(), 1, lab.Original, lab.Final, lab.CatalogHash!));
        Assert.ThrowsAny<Exception>(() => store.PrepareRotation(Guid.NewGuid(), 2, lab.NewKey, lab.Original, lab.Additive, lab.Final, lab.CatalogHash!));
        File.Delete(lab.Fence);
        Assert.ThrowsAny<Exception>(() => store.ReadRotation(lab.Operation));
        Assert.ThrowsAny<Exception>(() => store.ReplaceCatalog([2], lab.CatalogHash!));
        Assert.ThrowsAny<Exception>(() => store.Prepare(Guid.NewGuid(), 1, lab.Original, lab.Final, lab.CatalogHash!));
    }

    [Fact]
    public void UnknownLiveKeyIsNeverOverwrittenAndUnknownMetadataIsNeverAccepted()
    {
        using var lab = new Lab();
        using var store = lab.Open();
        using var lease = store.AcquireLock();
        lab.Prepare(store);
        File.WriteAllBytes(lab.Key(2), [19]);
        Assert.ThrowsAny<Exception>(() => store.PublishRotationKey(lab.Operation));
        Assert.Equal(new byte[] { 19 }, File.ReadAllBytes(lab.Key(2)));
        Assert.ThrowsAny<Exception>(() => store.WriteRotationMetadata(lab.Operation, "arbitrary/path", [1]));
    }

    [Fact]
    public void PrivateMetadataIsBoundedImmutableAndCannotBeReadByApprovedServiceReader()
    {
        using var lab = new Lab();
        using var store = lab.Open();
        using var lease = store.AcquireLock();
        lab.Prepare(store);
        store.WriteRotationMetadata(lab.Operation, "coordinator-plan", [1, 2]);
        store.WriteRotationMetadata(lab.Operation, "coordinator-plan", [1, 2]);
        Assert.Equal(new byte[] { 1, 2 }, store.ReadRotationMetadata(lab.Operation, "coordinator-plan"));
        Assert.Throws<MfaKeyRingException>(() => store.WriteRotationMetadata(lab.Operation, "coordinator-plan", [3]));
        Assert.ThrowsAny<Exception>(() => store.WriteRotationMetadata(lab.Operation, "material-ready", new byte[65537]));
        var reader = new WindowsMfaKeyFileReader(lab.Reader, lab.Trusted.Select(s => s.Value).ToHashSet());
        foreach (var path in Directory.EnumerateFiles(lab.Management).Where(p => !p.EndsWith(".rotation-stage-key.json", StringComparison.Ordinal) && !p.EndsWith("maintenance.lock", StringComparison.Ordinal)))
            Assert.Throws<MfaKeyRingException>(() => reader.ReadValidated(path, 1024 * 1024));
        Assert.NotEmpty(reader.ReadValidated(lab.Fence, 4096));
    }

    [Fact]
    public void CorruptHistoricalJournalBlocksVersionSelection()
    {
        using var lab = new Lab();
        using var store = lab.Open();
        using var lease = store.AcquireLock();
        lab.Prepare(store);
        File.WriteAllBytes(lab.Plan, [7]);
        Assert.ThrowsAny<Exception>(() => store.HighestRotationVersion());
        Assert.ThrowsAny<Exception>(() => store.PublishRotationKey(lab.Operation));
        Assert.True(File.Exists(lab.Fence));
    }

    [Fact]
    public void ExistingRetirementFenceRejectsRotationWithoutWritingAnyRotationPlan()
    {
        using var lab = new Lab();
        // Supply a retired version so retirement itself is a valid competing maintenance operation.
        var original = lab.RingBytes(MfaKeyJson.Entry(1, "retired") + "," + MfaKeyJson.Entry(2, "active"));
        var otherRoot = Path.Combine(lab.Root, "retirement");
        WindowsMfaKeyStoreWriter.CreateStoreFromMaterial(otherRoot, lab.Installation, lab.Reader, lab.Trusted,
            original, [(1, RandomNumberGenerator.GetBytes(32)), (2, RandomNumberGenerator.GetBytes(32))]);
        using var store = new WindowsMfaMaintenanceStore(otherRoot, lab.Installation, lab.Reader, lab.Trusted);
        using var lease = store.AcquireLock();
        var hash = store.CreateCatalog([1]);
        store.Prepare(Guid.NewGuid(), 1, original, lab.RingBytes(MfaKeyJson.Entry(2, "active")), hash);
        Assert.ThrowsAny<Exception>(() => store.PrepareRotation(lab.Operation, 3, lab.NewKey, lab.Original, lab.Additive, lab.Final, hash));
        var management = Path.Combine(otherRoot, lab.Installation.ToString("D"), WindowsMfaMaintenanceStore.ManagementFolderName);
        Assert.Empty(Directory.EnumerateFiles(management, "*.rotation-plan.json"));
    }

    [Fact]
    public void OriginalKeyReplacementAndForeignCompletionCannotRemoveFence()
    {
        using var lab = new Lab();
        using var store = lab.Open();
        using var lease = store.AcquireLock();
        lab.Prepare(store);
        var bytes = File.ReadAllBytes(lab.Key(1));
        var security = new FileInfo(lab.Key(1)).GetAccessControl();
        File.Move(lab.Key(1), lab.Key(1) + ".foreign-reserved");
        File.WriteAllBytes(lab.Key(1), bytes);
        new FileInfo(lab.Key(1)).SetAccessControl(security);
        Assert.Throws<MfaKeyRingException>(() => store.PublishRotationKey(lab.Operation));
        Assert.ThrowsAny<Exception>(() => store.CompleteRotation(Guid.NewGuid()));
        Assert.True(File.Exists(lab.Fence));
        Assert.False(File.Exists(lab.Key(2)));
        Assert.Equal(bytes, File.ReadAllBytes(lab.Key(1)));
    }

    [Fact]
    public void MissingVerifiedMarkerWithNoFenceNeverCountsAsCompleted()
    {
        using var lab = new Lab();
        using var store = lab.Open();
        using var lease = store.AcquireLock();
        lab.Prepare(store);
        store.PublishRotationKey(lab.Operation);
        store.PublishRotationAdditive(lab.Operation);
        store.PublishRotationFinal(lab.Operation);
        store.CompleteRotation(lab.Operation);
        File.Delete(Path.Combine(lab.Management, lab.Operation.ToString("N") + ".rotation-verified.json"));
        Assert.Throws<MfaKeyRingException>(() => store.ReadRotation(lab.Operation));
        Assert.Throws<MfaKeyRingException>(() => store.CompleteRotation(lab.Operation));
        Assert.Throws<MfaKeyRingException>(() => store.ReplaceCatalog([2], lab.CatalogHash!));
    }

    [Theory]
    [InlineData("stage-key")]
    [InlineData("unknown")]
    public void UnknownOrOrphanRotationArtifactsBlockVersionSelectionAndNewMaintenance(string kind)
    {
        using var lab = new Lab();
        using var store = lab.Open();
        using var lease = store.AcquireLock();
        var hash = store.CreateCatalog([1]);
        var path = Path.Combine(lab.Management, lab.Operation.ToString("N") + ".rotation-" + kind + ".json");
        File.WriteAllBytes(path, [17]);
        Assert.Throws<MfaKeyRingException>(() => store.HighestRotationVersion());
        Assert.Throws<MfaKeyRingException>(() => store.ReplaceCatalog([2], hash));
        Assert.Equal(new byte[] { 17 }, File.ReadAllBytes(path));
        Assert.False(File.Exists(lab.Fence));
    }

    [Fact]
    public void ReappearingConsumedStageIsPreservedAndBlocksCompletion()
    {
        using var lab = new Lab();
        using var store = lab.Open();
        using var lease = store.AcquireLock();
        lab.Prepare(store);
        store.PublishRotationKey(lab.Operation);
        store.PublishRotationAdditive(lab.Operation);
        store.PublishRotationFinal(lab.Operation);
        var path = Path.Combine(lab.Management, lab.Operation.ToString("N") + ".rotation-stage-final.json");
        File.WriteAllBytes(path, [31]);
        Assert.Throws<MfaKeyRingException>(() => store.CompleteRotation(lab.Operation));
        Assert.Equal(new byte[] { 31 }, File.ReadAllBytes(path));
        Assert.True(File.Exists(lab.Fence));
        Assert.Equal(lab.Final, store.ReadRing());
    }

    private sealed class Interrupted : Exception;

    private sealed class Lab : IDisposable
    {
        internal string Root { get; } = Path.Combine(Path.GetTempPath(), "rackclick-rotation-" + Guid.NewGuid().ToString("N"));
        internal Guid Installation { get; } = Guid.NewGuid();
        internal Guid Operation { get; } = Guid.NewGuid();
        internal SecurityIdentifier Reader { get; } = new(WellKnownSidType.BuiltinUsersSid, null);
        internal SecurityIdentifier[] Trusted { get; } = [WindowsIdentity.GetCurrent().User!, new(WellKnownSidType.LocalSystemSid, null), new(WellKnownSidType.BuiltinAdministratorsSid, null)];
        internal string Instances => Path.Combine(Root, "instances");
        internal string Folder => Path.Combine(Instances, Installation.ToString("D"));
        internal string Management => Path.Combine(Folder, WindowsMfaMaintenanceStore.ManagementFolderName);
        internal string Ring => Path.Combine(Folder, WindowsMfaKeyProvider.KeysFolderName, MfaKeyRing.RingFileName);
        internal string Fence => Path.Combine(Folder, WindowsMfaMaintenanceStore.FenceFileName);
        internal string StageKey => Path.Combine(Management, Operation.ToString("N") + ".rotation-stage-key.json");
        internal string Plan => Path.Combine(Management, Operation.ToString("N") + ".rotation-plan.json");
        internal byte[] Original => RingBytes(MfaKeyJson.Entry(1, "active"));
        internal byte[] Additive => RingBytes(MfaKeyJson.Entry(1, "active") + "," + MfaKeyJson.Entry(2, "retired"));
        internal byte[] Final => RingBytes(MfaKeyJson.Entry(1, "retired") + "," + MfaKeyJson.Entry(2, "active"));
        internal byte[] NewKey { get; }
        internal string? CatalogHash { get; private set; }
        internal byte[] RingBytes(string entries) => MfaKeyJson.Bytes(MfaKeyJson.Ring(Installation, entries));
        internal string Key(int version) => Path.Combine(Path.GetDirectoryName(Ring)!, MfaKeyRing.KeyFileName(version));
        internal Lab()
        {
            Directory.CreateDirectory(Root);
            WindowsMfaKeyStoreWriter.CreateStoreFromMaterial(Instances, Installation, Reader, Trusted, Original, [(1, RandomNumberGenerator.GetBytes(32))]);
            var staging = Path.Combine(Root, "source");
            WindowsMfaKeyStoreWriter.CreateStoreFromMaterial(staging, Installation, Reader, Trusted, RingBytes(MfaKeyJson.Entry(2, "active")), [(2, RandomNumberGenerator.GetBytes(32))]);
            NewKey = File.ReadAllBytes(Path.Combine(staging, Installation.ToString("D"), WindowsMfaKeyProvider.KeysFolderName, MfaKeyRing.KeyFileName(2)));
        }
        internal WindowsMfaMaintenanceStore Open() => new(Instances, Installation, Reader, Trusted);
        internal void Prepare(WindowsMfaMaintenanceStore store)
        {
            CatalogHash = store.CreateCatalog([1]);
            store.PrepareRotation(Operation, 2, NewKey, Original, Additive, Final, CatalogHash);
        }
        public void Dispose() => Directory.Delete(Root, true);
    }
}
