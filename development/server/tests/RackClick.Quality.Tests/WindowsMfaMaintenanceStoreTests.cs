using System.Diagnostics;
using System.Runtime.Versioning;
using System.Security.AccessControl;
using System.Security.Cryptography;
using System.Security.Principal;
using RackClick.Server;
using Xunit;

namespace RackClick.Quality.Tests;

[SupportedOSPlatform("windows")]
public sealed class WindowsMfaMaintenanceStoreTests
{
    [Fact]
    public void PrivateMetadataAndServiceFenceHaveDifferentProtectedPermissions()
    {
        using var lab = new Lab();
        using var store = lab.Open();
        using var lease = store.AcquireLock();
        var digest = store.CreateCatalog([1, 2, 3]);
        store.Prepare(lab.Operation, 1, lab.Original, lab.Final, digest);
        foreach (var path in Directory.EnumerateFiles(lab.Management))
            AssertPrivate(path, lab);
        AssertPrivate(lab.Management, lab);
        var reader = new WindowsMfaKeyFileReader(lab.Reader, lab.Trusted.Select(s => s.Value).ToHashSet());
        Assert.Throws<MfaKeyRingException>(() => reader.ReadValidated(Path.Combine(lab.Management, "catalog.json"), 100));
        Assert.NotEmpty(reader.ReadValidated(lab.Fence, 64 * 1024));
        Assert.Equal(lab.Original, store.ReadRing());
    }

    [Fact]
    public void CatalogCreationIsExclusiveAndReplacementRetainsThePreviousGeneration()
    {
        using var lab = new Lab();
        using var store = lab.Open();
        Assert.Throws<InvalidOperationException>(() => store.CreateCatalog([1]));
        using var lease = store.AcquireLock();
        var hash = store.CreateCatalog([1]);
        Assert.ThrowsAny<Exception>(() => store.CreateCatalog([2]));
        Assert.Equal(new byte[] { 1 }, store.ReadCatalog());
        Assert.Throws<MfaKeyRingException>(() => store.ReplaceCatalog([2], new string('0', 64)));
        store.ReplaceCatalog([2], hash);
        Assert.Equal(new byte[] { 2 }, store.ReadCatalog());
        Assert.Contains(Directory.EnumerateFiles(lab.Management), path => Path.GetFileName(path).StartsWith("catalog.previous-", StringComparison.Ordinal) && File.ReadAllBytes(path).SequenceEqual(new byte[] { 1 }));
    }

    [Fact]
    public void LockIsExclusiveAcrossInstancesAndCannotBeReentered()
    {
        using var lab = new Lab();
        using var first = lab.Open();
        using var second = lab.Open();
        using (first.AcquireLock())
        {
            Assert.Throws<InvalidOperationException>(() => first.AcquireLock());
            Assert.ThrowsAny<IOException>(() => second.AcquireLock());
        }
        using var next = second.AcquireLock();
        Assert.Null(second.Pending);
    }

    [Fact]
    public void PublishRetiresOnlyTheRingEntryAndCompleteIsIdempotentAfterReopen()
    {
        using var lab = new Lab();
        var key = File.ReadAllBytes(lab.Key(1));
        var activeKey = File.ReadAllBytes(lab.Key(2));
        using (var store = lab.Open())
        using (store.AcquireLock())
        {
            var hash = store.CreateCatalog([1]);
            store.Prepare(lab.Operation, 1, lab.Original, lab.Final, hash);
            Assert.Throws<MfaKeyRingException>(() => store.Complete(lab.Operation));
            store.Publish(lab.Operation);
            store.Publish(lab.Operation);
            Assert.Equal(lab.Final, store.ReadRing());
            store.Complete(lab.Operation);
            Assert.Null(store.ReadPending());
            Assert.False(File.Exists(lab.Fence));
        }
        using (var reopened = lab.Open())
        using (reopened.AcquireLock())
            reopened.Complete(lab.Operation);
        Assert.Equal(key, File.ReadAllBytes(lab.Key(1)));
        Assert.Equal(activeKey, File.ReadAllBytes(lab.Key(2)));
        var provider = new WindowsMfaKeyProvider(lab.Instances, lab.Installation, lab.Reader, lab.Trusted);
        Assert.Throws<MfaKeyRingException>(() => provider.GetKey(1));
        Assert.Equal(MfaKeyRing.KeyBytes, provider.GetKey(2).Length);
        Assert.Contains(Directory.EnumerateFiles(lab.Management), path => Path.GetFileName(path).EndsWith(".verified.json", StringComparison.Ordinal));
    }

    [Theory]
    [InlineData("fence_created", false)]
    [InlineData("before_publish", false)]
    [InlineData("after_publish", true)]
    [InlineData("before_complete", true)]
    public void SyntheticInterruptionLeavesFenceAndResumesForward(string checkpoint, bool published)
    {
        using var lab = new Lab();
        using (var store = lab.Open())
        using (store.AcquireLock())
        {
            var hash = store.CreateCatalog([1]);
            store.Checkpoint = point => { if (point == checkpoint) throw new SyntheticCrash(); };
            Assert.Throws<SyntheticCrash>(() =>
            {
                store.Prepare(lab.Operation, 1, lab.Original, lab.Final, hash);
                store.Publish(lab.Operation);
                store.Complete(lab.Operation);
            });
        }
        Assert.True(File.Exists(lab.Fence));
        using var resume = lab.Open();
        using var lease = resume.AcquireLock();
        var pending = Assert.IsType<WindowsMfaMaintenancePending>(resume.Pending);
        Assert.Equal(lab.Operation, pending.OperationId);
        Assert.Equal(1, pending.Candidate);
        Assert.Equal(lab.Original, pending.OriginalRing);
        Assert.Equal(lab.Final, pending.FinalRing);
        Assert.Equal(published ? lab.Final : lab.Original, resume.ReadRing());
        Assert.Throws<MfaKeyRingException>(() => resume.Prepare(Guid.NewGuid(), 1, lab.Original, lab.Final, pending.CatalogHash));
        resume.Publish(lab.Operation);
        resume.Complete(lab.Operation);
        Assert.Null(resume.Pending);
    }

    [Theory]
    [InlineData("active")]
    [InlineData("foreign")]
    [InlineData("additional-change")]
    [InlineData("hash")]
    public void PrepareRejectsInvalidReductionOrForeignIdentityWithoutFence(string shape)
    {
        using var lab = new Lab();
        using var store = lab.Open();
        using var lease = store.AcquireLock();
        var hash = store.CreateCatalog([1]);
        var candidate = shape == "active" ? 2 : 1;
        var final = shape switch
        {
            "foreign" => MfaKeyJson.Bytes(MfaKeyJson.Ring(Guid.NewGuid(), MfaKeyJson.Entry(2, "active"))),
            "additional-change" => MfaKeyJson.Bytes(MfaKeyJson.Ring(lab.Installation, MfaKeyJson.Entry(2, "active", "2026-10-26T10:00:00Z"))),
            _ => lab.Final,
        };
        Assert.Throws<MfaKeyRingException>(() => store.Prepare(lab.Operation, candidate, lab.Original, final, shape == "hash" ? new string('0', 64) : hash));
        Assert.False(File.Exists(lab.Fence));
        Assert.Equal(lab.Original, store.ReadRing());
    }

    [Theory]
    [InlineData("catalog")]
    [InlineData("journal")]
    [InlineData("ring")]
    [InlineData("fence")]
    public void PoisonedStateNeverRemovesFenceOrPublishes(string shape)
    {
        using var lab = new Lab();
        using var store = lab.Open();
        using var lease = store.AcquireLock();
        var hash = store.CreateCatalog([1]);
        store.Prepare(lab.Operation, 1, lab.Original, lab.Final, hash);
        var path = shape switch
        {
            "catalog" => Path.Combine(lab.Management, "catalog.json"),
            "journal" => Path.Combine(lab.Management, lab.Operation.ToString("N") + ".prepared.json"),
            "ring" => lab.Ring,
            _ => lab.Fence,
        };
        File.WriteAllBytes(path, [3, 4, 5]);
        Assert.ThrowsAny<Exception>(() => store.Publish(lab.Operation));
        Assert.ThrowsAny<Exception>(() => store.Complete(lab.Operation));
        Assert.True(File.Exists(lab.Fence));
    }

    [Fact]
    public void IdenticalRingSubstitutionAtPublishIsRejectedByObjectIdentity()
    {
        using var lab = new Lab();
        using var store = lab.Open();
        using var lease = store.AcquireLock();
        store.Prepare(lab.Operation, 1, lab.Original, lab.Final, store.CreateCatalog([1]));
        store.Checkpoint = point =>
        {
            if (point != "before_publish") return;
            var security = new FileInfo(lab.Ring).GetAccessControl();
            File.Move(lab.Ring, lab.Ring + ".foreign-reserved");
            File.WriteAllBytes(lab.Ring, lab.Original);
            new FileInfo(lab.Ring).SetAccessControl(security);
        };
        Assert.Throws<MfaKeyRingException>(() => store.Publish(lab.Operation));
        Assert.True(File.Exists(lab.Fence));
        Assert.Equal(lab.Original, File.ReadAllBytes(lab.Ring));
    }

    [Fact]
    public void ReplacementFailureLeavesFenceAndInitialRingForResume()
    {
        using var lab = new Lab();
        using var store = lab.Open();
        using var lease = store.AcquireLock();
        store.Prepare(lab.Operation, 1, lab.Original, lab.Final, store.CreateCatalog([1]));
        using (var held = new FileStream(lab.Ring, FileMode.Open, FileAccess.Read, FileShare.Read))
            Assert.ThrowsAny<IOException>(() => store.Publish(lab.Operation));
        Assert.True(File.Exists(lab.Fence));
        Assert.Equal(lab.Original, store.ReadRing());
        store.Publish(lab.Operation);
        store.Complete(lab.Operation);
    }

    [Fact]
    public void AnotherOperationCannotCompleteOrDeleteOwnedFence()
    {
        using var lab = new Lab();
        using var store = lab.Open();
        using var lease = store.AcquireLock();
        store.Prepare(lab.Operation, 1, lab.Original, lab.Final, store.CreateCatalog([1]));
        store.Publish(lab.Operation);
        var before = File.ReadAllBytes(lab.Fence);
        Assert.Throws<MfaKeyRingException>(() => store.Complete(Guid.NewGuid()));
        Assert.Equal(before, File.ReadAllBytes(lab.Fence));
    }

    [Theory]
    [InlineData("management")]
    [InlineData("catalog")]
    [InlineData("lock")]
    public void UntrustedAclIncludingAnEmptyDirectoryIsRejectedWithoutRepair(string shape)
    {
        using var lab = new Lab();
        using (var init = lab.Open())
        using (init.AcquireLock())
            init.CreateCatalog([1]);
        var path = shape switch { "catalog" => Path.Combine(lab.Management, "catalog.json"), "lock" => Path.Combine(lab.Management, "maintenance.lock"), _ => lab.Management };
        var everyone = new SecurityIdentifier(WellKnownSidType.WorldSid, null);
        FileSystemSecurity security = shape == "management" ? new DirectoryInfo(path).GetAccessControl() : new FileInfo(path).GetAccessControl();
        security.AddAccessRule(new FileSystemAccessRule(everyone, FileSystemRights.FullControl, AccessControlType.Allow));
        if (shape == "management") new DirectoryInfo(path).SetAccessControl((DirectorySecurity)security);
        else new FileInfo(path).SetAccessControl((FileSecurity)security);
        Assert.Throws<MfaKeyRingException>(() =>
        {
            using var rejected = lab.Open();
            using var acquire = rejected.AcquireLock();
            rejected.ReadCatalog();
        });
    }

    [Fact]
    public void JunctionManagementIsRejectedAndTargetRemainsUntouched()
    {
        using var lab = new Lab();
        var target = Path.Combine(lab.Root, "target");
        Directory.CreateDirectory(target);
        using var process = Process.Start(new ProcessStartInfo("cmd.exe", $"/c mklink /J \"{lab.Management}\" \"{target}\"") { UseShellExecute = false, RedirectStandardOutput = true, RedirectStandardError = true })!;
        process.WaitForExit();
        Assert.Equal(0, process.ExitCode);
        try
        {
            Assert.Throws<MfaKeyRingException>(() => lab.Open());
            Assert.Empty(Directory.EnumerateFileSystemEntries(target));
        }
        finally { Directory.Delete(lab.Management); }
    }

    [Fact]
    public void StoreKeepsDirectoryAncestorsFromBeingRenamedWhileOpen()
    {
        using var lab = new Lab();
        using var store = lab.Open();
        Assert.ThrowsAny<IOException>(() => Directory.Move(lab.Instances, lab.Instances + ".moved"));
        Assert.ThrowsAny<IOException>(() => Directory.Move(lab.Management, lab.Management + ".moved"));
    }

    [Theory]
    [InlineData("catalog")]
    [InlineData("lock")]
    [InlineData("stage")]
    public void HardLinkedMetadataIsRejectedWithoutModifyingEitherName(string shape)
    {
        using var lab = new Lab();
        using (var store = lab.Open())
        using (store.AcquireLock())
        {
            var hash = store.CreateCatalog([1]);
            if (shape == "stage") store.Prepare(lab.Operation, 1, lab.Original, lab.Final, hash);
        }
        var path = shape switch
        {
            "catalog" => Path.Combine(lab.Management, "catalog.json"),
            "lock" => Path.Combine(lab.Management, "maintenance.lock"),
            _ => Path.Combine(lab.Management, lab.Operation.ToString("N") + ".stage-ring.json"),
        };
        var before = File.ReadAllBytes(path);
        var alias = Path.Combine(lab.Root, "alias.bin");
        using var process = Process.Start(new ProcessStartInfo("cmd.exe", $"/c mklink /H \"{alias}\" \"{path}\"") { UseShellExecute = false, RedirectStandardOutput = true, RedirectStandardError = true })!;
        process.WaitForExit();
        Assert.Equal(0, process.ExitCode);
        using var reopened = lab.Open();
        Assert.Throws<MfaKeyRingException>(() =>
        {
            using var lease = reopened.AcquireLock();
            if (shape == "catalog") reopened.ReadCatalog();
            else if (shape == "stage") reopened.Publish(lab.Operation);
        });
        Assert.Equal(before, File.ReadAllBytes(alias));
        Assert.Equal(before, File.ReadAllBytes(path));
        Assert.Equal(shape == "stage", File.Exists(lab.Fence));
    }

    [Fact]
    public void MissingFenceWithAnUnfinishedJournalBlocksNewOperations()
    {
        using var lab = new Lab();
        using var store = lab.Open();
        using var lease = store.AcquireLock();
        store.Prepare(lab.Operation, 1, lab.Original, lab.Final, store.CreateCatalog([1]));
        File.Delete(lab.Fence);
        Assert.Throws<MfaKeyRingException>(() => store.ReadPending());
        Assert.Throws<MfaKeyRingException>(() => store.ReplaceCatalog([2], Convert.ToHexStringLower(SHA256.HashData([1]))));
        Assert.Throws<MfaKeyRingException>(() => store.Prepare(Guid.NewGuid(), 1, lab.Original, lab.Final, Convert.ToHexStringLower(SHA256.HashData([1]))));
        Assert.Equal(lab.Original, store.ReadRing());
    }

    [Fact]
    public void IdenticalFenceSubstitutionAtCompletionIsPreserved()
    {
        using var lab = new Lab();
        using var store = lab.Open();
        using var lease = store.AcquireLock();
        store.Prepare(lab.Operation, 1, lab.Original, lab.Final, store.CreateCatalog([1]));
        store.Publish(lab.Operation);
        var before = File.ReadAllBytes(lab.Fence);
        store.Checkpoint = point =>
        {
            if (point != "before_complete") return;
            var security = new FileInfo(lab.Fence).GetAccessControl();
            File.Move(lab.Fence, lab.Fence + ".reserved");
            File.WriteAllBytes(lab.Fence, before);
            new FileInfo(lab.Fence).SetAccessControl(security);
        };
        Assert.Throws<MfaKeyRingException>(() => store.Complete(lab.Operation));
        Assert.Equal(before, File.ReadAllBytes(lab.Fence));
        Assert.True(File.Exists(lab.Fence + ".reserved"));
    }

    [Theory]
    [InlineData("empty-catalog")]
    [InlineData("empty-ring")]
    [InlineData("nonempty-lock")]
    [InlineData("empty-fence")]
    public void EmptyOrUnexpectedMetadataFailsClosed(string shape)
    {
        using var lab = new Lab();
        using (var store = lab.Open())
        using (store.AcquireLock())
        {
            var hash = store.CreateCatalog([1]);
            if (shape == "empty-fence") store.Prepare(lab.Operation, 1, lab.Original, lab.Final, hash);
        }
        var path = shape switch
        {
            "empty-catalog" => Path.Combine(lab.Management, "catalog.json"),
            "empty-ring" => lab.Ring,
            "nonempty-lock" => Path.Combine(lab.Management, "maintenance.lock"),
            _ => lab.Fence,
        };
        File.WriteAllBytes(path, shape == "nonempty-lock" ? new byte[] { 1 } : []);
        using var reopened = lab.Open();
        Assert.Throws<MfaKeyRingException>(() =>
        {
            using var lease = reopened.AcquireLock();
            if (shape == "empty-catalog") reopened.ReadCatalog();
            else if (shape == "empty-ring") reopened.ReadRing();
            else if (shape == "empty-fence") reopened.ReadPending();
        });
        Assert.Equal(shape == "empty-fence", File.Exists(lab.Fence));
    }

    [Theory]
    [InlineData("root")]
    [InlineData("installation")]
    [InlineData("keys")]
    public void AServiceWritableExistingStoreIsRejectedBeforeCreatingManagement(string shape)
    {
        using var lab = new Lab();
        var path = shape switch { "root" => lab.Instances, "installation" => lab.InstallationFolder, _ => Path.GetDirectoryName(lab.Ring)! };
        var info = new DirectoryInfo(path);
        var security = info.GetAccessControl();
        security.AddAccessRule(new FileSystemAccessRule(lab.Reader, FileSystemRights.Modify, AccessControlType.Allow));
        info.SetAccessControl(security);
        Assert.Throws<MfaKeyRingException>(() => lab.Open());
        Assert.False(Directory.Exists(lab.Management));
    }

    [Fact]
    public void StoreDoesNotCreateMissingInstancesOrInstallationFolders()
    {
        using var lab = new Lab();
        var missing = Path.Combine(lab.Root, "missing");
        Assert.ThrowsAny<IOException>(() => new WindowsMfaMaintenanceStore(missing, lab.Installation, lab.Reader, lab.Trusted));
        Assert.False(Directory.Exists(missing));
        var unknown = Guid.NewGuid();
        Assert.ThrowsAny<IOException>(() => new WindowsMfaMaintenanceStore(lab.Instances, unknown, lab.Reader, lab.Trusted));
        Assert.False(Directory.Exists(Path.Combine(lab.Instances, unknown.ToString("D"))));
    }

    private static void AssertPrivate(string path, Lab lab)
    {
        FileSystemSecurity security = Directory.Exists(path) ? new DirectoryInfo(path).GetAccessControl() : new FileInfo(path).GetAccessControl();
        Assert.True(security.AreAccessRulesProtected);
        var descriptor = new RawSecurityDescriptor(security.GetSecurityDescriptorBinaryForm(), 0);
        Assert.Contains(descriptor.Owner!.Value, lab.Trusted.Select(s => s.Value));
        foreach (CommonAce ace in descriptor.DiscretionaryAcl!)
        {
            Assert.Equal(AceType.AccessAllowed, ace.AceType);
            Assert.Contains(ace.SecurityIdentifier.Value, lab.Trusted.Select(s => s.Value));
            Assert.Equal((int)FileSystemRights.FullControl, ace.AccessMask);
        }
    }

    private sealed class SyntheticCrash : Exception;

    private sealed class Lab : IDisposable
    {
        public string Root { get; } = Path.Combine(Path.GetTempPath(), "rackclick-maintenance-" + Guid.NewGuid().ToString("N"));
        public Guid Installation { get; } = Guid.NewGuid();
        public Guid Operation { get; } = Guid.NewGuid();
        public SecurityIdentifier Reader { get; } = new(WellKnownSidType.BuiltinUsersSid, null);
        public SecurityIdentifier[] Trusted { get; } = [WindowsIdentity.GetCurrent().User!, new(WellKnownSidType.LocalSystemSid, null), new(WellKnownSidType.BuiltinAdministratorsSid, null)];
        public string Instances => Path.Combine(Root, "instances");
        public string InstallationFolder => Path.Combine(Instances, Installation.ToString("D"));
        public string Management => Path.Combine(InstallationFolder, "mfa-maintenance");
        public string Fence => Path.Combine(InstallationFolder, "mfa-maintenance-fence.json");
        public string Ring => Path.Combine(InstallationFolder, WindowsMfaKeyProvider.KeysFolderName, MfaKeyRing.RingFileName);
        public string Key(int version) => Path.Combine(Path.GetDirectoryName(Ring)!, MfaKeyRing.KeyFileName(version));
        public byte[] Original => MfaKeyJson.Bytes(MfaKeyJson.Ring(Installation, MfaKeyJson.Entry(1, "retired") + "," + MfaKeyJson.Entry(2, "active")));
        public byte[] Final => MfaKeyJson.Bytes(MfaKeyJson.Ring(Installation, MfaKeyJson.Entry(2, "active")));
        public Lab()
        {
            Directory.CreateDirectory(Root);
            WindowsMfaKeyStoreWriter.CreateStoreFromMaterial(Instances, Installation, Reader, Trusted, Original,
                [(1, RandomNumberGenerator.GetBytes(MfaKeyRing.KeyBytes)), (2, RandomNumberGenerator.GetBytes(MfaKeyRing.KeyBytes))]);
        }
        public WindowsMfaMaintenanceStore Open() => new(Instances, Installation, Reader, Trusted);
        public void Dispose() => Directory.Delete(Root, true);
    }
}
