using System.Runtime.InteropServices;
using System.Runtime.Versioning;
using System.Security.AccessControl;
using System.Security.Cryptography;
using System.Security.Principal;
using System.Text.Json;
using Microsoft.Win32.SafeHandles;
using RackClick.Server;
using Xunit;

namespace RackClick.Quality.Tests;

// Filesystem-only synthetic authority. No DB witness is inserted and no service token is impersonated.
[SupportedOSPlatform("windows")]
public sealed class WindowsMfaRotationStartupReceiptTests
{
    [Fact]
    public void ForeignMarkerCreatedAfterPriorCaptureIsPreservedAndLeavesFence()
    {
        using var lab = new Lab();
        using var store = lab.Open();
        using var lease = store.AcquireLock();
        var witness = lab.PrepareFinal(store);
        var foreign = JsonSerializer.SerializeToUtf8Bytes(new MfaRotationStartupReceipt(lab.Installation,
            Guid.NewGuid(), 17, new string('a', 64)));
        store.Checkpoint = point =>
        {
            if (point == "before_startup_receipt") lab.WriteServiceMarker(foreign);
        };

        Assert.Throws<MfaKeyRingException>(() => store.PublishRotationStartupReceipt(witness));

        Assert.Equal(foreign, File.ReadAllBytes(lab.Marker));
        var identity = ObjectIdentity(lab.Marker);
        store.Checkpoint = null;
        Assert.Throws<MfaKeyRingException>(() => store.PublishRotationStartupReceipt(witness));
        Assert.Equal(identity, ObjectIdentity(lab.Marker));
        Assert.Equal(foreign, File.ReadAllBytes(lab.Marker));
        Assert.True(File.Exists(lab.Fence));
        Assert.True(File.Exists(lab.Stage));
    }

    [Fact]
    public void IdenticalPublishedMarkerInAnotherObjectIsRejectedWithoutReplacingIt()
    {
        using var lab = new Lab();
        using var store = lab.Open();
        using var lease = store.AcquireLock();
        var witness = lab.PrepareFinal(store);
        store.PublishRotationStartupReceipt(witness);
        var bytes = File.ReadAllBytes(lab.Marker);
        var publishedIdentity = ObjectIdentity(lab.Marker);
        var security = new FileInfo(lab.Marker).GetAccessControl();
        File.Move(lab.Marker, lab.Marker + ".foreign-reserved");
        File.WriteAllBytes(lab.Marker, bytes);
        new FileInfo(lab.Marker).SetAccessControl(security);
        var foreignIdentity = ObjectIdentity(lab.Marker);
        Assert.NotEqual(publishedIdentity, foreignIdentity);

        Assert.Throws<MfaKeyRingException>(() => store.PublishRotationStartupReceipt(witness));

        Assert.Equal(foreignIdentity, ObjectIdentity(lab.Marker));
        Assert.Equal(bytes, File.ReadAllBytes(lab.Marker));
        Assert.Equal(bytes, File.ReadAllBytes(lab.Marker + ".foreign-reserved"));
        Assert.True(File.Exists(lab.Fence));
    }

    [Theory]
    [InlineData("before_startup_receipt", false)]
    [InlineData("after_startup_receipt", true)]
    public void InterruptedReceiptPublicationReopensAndResumesWithTheSameStagedObject(string checkpoint, bool published)
    {
        using var lab = new Lab();
        MfaRotationWitness witness;
        (uint Volume, ulong Index) expectedIdentity;
        using (var store = lab.Open())
        using (store.AcquireLock())
        {
            witness = lab.PrepareFinal(store);
            store.Checkpoint = point => { if (point == checkpoint) throw new Interrupted(); };
            Assert.Throws<Interrupted>(() => store.PublishRotationStartupReceipt(witness));
            Assert.Equal(published, File.Exists(lab.Marker));
            expectedIdentity = ObjectIdentity(published ? lab.Marker : lab.Stage);
        }

        using var resumed = lab.Open();
        using var lease = resumed.AcquireLock();
        resumed.PublishRotationStartupReceipt(witness);
        var publishedIdentity = ObjectIdentity(lab.Marker);
        resumed.PublishRotationStartupReceipt(witness);

        Assert.Equal(expectedIdentity, publishedIdentity);
        Assert.Equal(publishedIdentity, ObjectIdentity(lab.Marker));
        Assert.False(File.Exists(lab.Stage));
        var receipt = JsonSerializer.Deserialize<MfaRotationStartupReceipt>(File.ReadAllBytes(lab.Marker));
        Assert.NotNull(receipt);
        Assert.Equal(lab.Installation, receipt.InstallationId);
        Assert.Equal(lab.Operation, receipt.OperationId);
        Assert.Equal(2, receipt.NewVersion);
        Assert.Equal(Hash(JsonSerializer.SerializeToUtf8Bytes(witness.Binding)), receipt.BindingHash);
        Assert.True(File.Exists(lab.Fence));
    }

    private static string Hash(byte[] bytes) => Convert.ToHexStringLower(SHA256.HashData(bytes));

    private static (uint Volume, ulong Index) ObjectIdentity(string path)
    {
        using var handle = File.OpenHandle(path, FileMode.Open, FileAccess.Read, FileShare.ReadWrite | FileShare.Delete);
        Assert.True(GetFileInformationByHandle(handle, out var info));
        return (info.Volume, ((ulong)info.IndexHigh << 32) | info.IndexLow);
    }

    private sealed class Interrupted : Exception;

    private sealed class Lab : IDisposable
    {
        internal string Root { get; } = Path.Combine(Path.GetTempPath(), "rackclick-rotation-receipt-" + Guid.NewGuid().ToString("N"));
        internal Guid Installation { get; } = Guid.NewGuid();
        internal Guid Operation { get; } = Guid.NewGuid();
        internal Guid Systemhaus { get; } = Guid.NewGuid();
        internal SecurityIdentifier Reader { get; } = new(WellKnownSidType.BuiltinUsersSid, null);
        internal SecurityIdentifier[] Trusted { get; } = [WindowsIdentity.GetCurrent().User!, new(WellKnownSidType.LocalSystemSid, null), new(WellKnownSidType.BuiltinAdministratorsSid, null)];
        internal string Instances => Path.Combine(Root, "instances");
        internal string Folder => Path.Combine(Instances, Installation.ToString("D"));
        internal string Management => Path.Combine(Folder, WindowsMfaMaintenanceStore.ManagementFolderName);
        internal string Ring => Path.Combine(Folder, WindowsMfaKeyProvider.KeysFolderName, MfaKeyRing.RingFileName);
        internal string Fence => Path.Combine(Folder, WindowsMfaMaintenanceStore.FenceFileName);
        internal string Marker => Path.Combine(Folder, WindowsMfaMaintenanceStore.RotationStartupFileName);
        internal string Stage => Path.Combine(Management, Operation.ToString("N") + ".startup-receipt.json");
        internal byte[] Original => RingBytes(MfaKeyJson.Entry(1, "active"));
        internal byte[] Additive => RingBytes(MfaKeyJson.Entry(1, "active") + "," + MfaKeyJson.Entry(2, "retired"));
        internal byte[] Final => RingBytes(MfaKeyJson.Entry(1, "retired") + "," + MfaKeyJson.Entry(2, "active"));
        internal byte[] NewKey { get; }

        internal Lab()
        {
            Directory.CreateDirectory(Root);
            WindowsMfaKeyStoreWriter.CreateStoreFromMaterial(Instances, Installation, Reader, Trusted, Original,
                [(1, RandomNumberGenerator.GetBytes(MfaKeyRing.KeyBytes))]);
            var source = Path.Combine(Root, "source");
            WindowsMfaKeyStoreWriter.CreateStoreFromMaterial(source, Installation, Reader, Trusted,
                RingBytes(MfaKeyJson.Entry(2, "active")), [(2, RandomNumberGenerator.GetBytes(MfaKeyRing.KeyBytes))]);
            NewKey = File.ReadAllBytes(Path.Combine(source, Installation.ToString("D"), WindowsMfaKeyProvider.KeysFolderName,
                MfaKeyRing.KeyFileName(2)));
        }

        internal WindowsMfaMaintenanceStore Open() => new(Instances, Installation, Reader, Trusted);

        internal MfaRotationWitness PrepareFinal(WindowsMfaMaintenanceStore store)
        {
            var catalogHash = store.CreateCatalog([1]);
            store.PrepareRotation(Operation, 2, NewKey, Original, Additive, Final, catalogHash);
            Assert.Null(store.RecordRotationStartupPrior(Operation));
            store.PublishRotationKey(Operation);
            store.PublishRotationAdditive(Operation);
            store.PublishRotationFinal(Operation);
            var binding = new MfaRotationBinding(Operation, Installation, Systemhaus, WindowsIdentity.GetCurrent().User!.Value,
                1, 2, Hash(Original), Hash(Additive), Hash(Final), Hash(NewKey), catalogHash, Hash([29]));
            return new MfaRotationWitness(binding, 0, 0, 0);
        }

        internal void WriteServiceMarker(byte[] bytes)
        {
            // Fixture creation only: retain the exact service-readable DACL of its synthetic ring.
            var security = new FileInfo(Ring).GetAccessControl();
            using (var stream = new FileStream(Marker, FileMode.CreateNew, FileAccess.Write, FileShare.None)) stream.Write(bytes);
            new FileInfo(Marker).SetAccessControl(security);
        }

        private byte[] RingBytes(string entries) => MfaKeyJson.Bytes(MfaKeyJson.Ring(Installation, entries));
        public void Dispose() => Directory.Delete(Root, true);
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct FileTime { public uint Low, High; }

    [StructLayout(LayoutKind.Sequential)]
    private struct NativeInfo
    {
        public uint Attributes;
        public FileTime Created, Accessed, Written;
        public uint Volume, SizeHigh, SizeLow, NumberOfLinks, IndexHigh, IndexLow;
    }

    [DllImport("kernel32.dll", SetLastError = true)] [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool GetFileInformationByHandle(SafeFileHandle handle, out NativeInfo information);
}
