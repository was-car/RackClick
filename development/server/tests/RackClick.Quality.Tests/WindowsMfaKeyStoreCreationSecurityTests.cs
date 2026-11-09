using System.Runtime.Versioning;
using System.Security.AccessControl;
using System.Security.Cryptography;
using System.Security.Principal;
using RackClick.Server;
using Xunit;

namespace RackClick.Quality.Tests;

// F-04.01: DACL nativa observada después de crear y registrar el objeto, antes de cualquier
// SetAcl posterior o escritura de contenido. Sólo fixtures TEMP, sin cuentas, servicios o VM.
[SupportedOSPlatform("windows")]
public sealed class WindowsMfaKeyStoreCreationSecurityTests
{
    [Fact]
    public void DirectoriesAlreadyHaveProtectedAclBeforeAnyPostCreationOperation()
    {
        using var fixture = new Root();
        var directories = 0;
        fixture.Create((path, directory) =>
        {
            if (!directory) return;
            AssertExactAcl(path, true, fixture);
            directories++;
        });
        Assert.Equal(3, directories);
    }

    [Fact]
    public void FilesAlreadyHaveProtectedAclBeforeTheFirstContentWrite()
    {
        using var fixture = new Root();
        var files = 0;
        fixture.Create((path, directory) =>
        {
            if (directory) return;
            Assert.Equal(0, new FileInfo(path).Length);
            AssertExactAcl(path, false, fixture);
            files++;
        });
        Assert.Equal(2, files);
    }

    [Fact]
    public void ImportedMaterialUsesTheSameProtectedCreationPath()
    {
        using var origin = new Root();
        origin.Create();
        var ring = File.ReadAllBytes(Path.Combine(origin.Keys, MfaKeyRing.RingFileName));
        var key = origin.Provider().GetKey(1);
        try
        {
            using var target = new Root(origin.Installation);
            var observed = 0;
            WindowsMfaKeyStoreWriter.CreateStoreFromMaterial(target.Instances, target.Installation, target.Reader,
                target.Trusted, ring, [(1, key)], afterObjectCreated: (path, directory) =>
                {
                    AssertExactAcl(path, directory, target);
                    if (!directory) Assert.Equal(0, new FileInfo(path).Length);
                    observed++;
                });
            Assert.Equal(5, observed);
            var imported = target.Provider().GetKey(1);
            try { Assert.True(CryptographicOperations.FixedTimeEquals(key, imported)); }
            finally { CryptographicOperations.ZeroMemory(imported); }
        }
        finally { CryptographicOperations.ZeroMemory(key); }
    }

    [Fact]
    public void FinalPathIsAbsentUntilTheEntireValidatedStageIsReady()
    {
        using var fixture = new Root();
        var observations = 0;
        fixture.Create((_, _) =>
        {
            Assert.False(Directory.Exists(fixture.Keys));
            observations++;
        }, beforePublish: () =>
        {
            Assert.False(Directory.Exists(fixture.Keys));
            var stage = Assert.Single(Directory.GetDirectories(fixture.InstallationFolder, "mfa-keys.preparando-*"));
            var files = Directory.GetFiles(stage);
            Assert.Equal(2, files.Length);
            AssertExactAcl(stage, true, fixture);
            foreach (var file in files)
            {
                Assert.True(new FileInfo(file).Length > 0);
                AssertExactAcl(file, false, fixture);
            }
        });
        Assert.Equal(5, observations);
        Assert.Equal(2, Directory.GetFiles(fixture.Keys).Length);
        Assert.Empty(Directory.GetDirectories(fixture.InstallationFolder, "mfa-keys.preparando-*"));
        var key = fixture.Provider().GetKey(1);
        try { Assert.Equal(32, key.Length); }
        finally { CryptographicOperations.ZeroMemory(key); }
    }

    [Fact]
    public void FailureBeforePublicationLeavesNoPartialFinalStore()
    {
        using var fixture = new Root();
        Assert.Throws<MfaKeyStoreCreationException>(() => fixture.Create(beforePublish: () =>
        {
            Assert.False(Directory.Exists(fixture.Keys));
            Assert.Equal(2, Directory.GetFiles(Assert.Single(Directory.GetDirectories(
                fixture.InstallationFolder, "mfa-keys.preparando-*"))).Length);
            throw new IOException("synthetic prepublication failure");
        }));
        Assert.False(Directory.Exists(fixture.Keys));
        Assert.False(Directory.Exists(fixture.Instances));
    }

    [Fact]
    public void FailureImmediatelyAfterRenameIsReportedAsPublicationFailure()
    {
        using var fixture = new Root();
        var error = Assert.Throws<MfaKeyStoreCreationException>(() => fixture.Create(afterPublish: () =>
        {
            Assert.Equal(2, Directory.GetFiles(fixture.Keys).Length);
            throw new IOException("synthetic failure after rename");
        }));
        Assert.Equal(MfaKeyStoreCreationErrorKind.PublishFailed, error.Kind);
        if (Directory.Exists(fixture.Keys))
        {
            Assert.Contains(fixture.Keys, error.Residue);
            var key = fixture.Provider().GetKey(1);
            try { Assert.Equal(32, key.Length); }
            finally { CryptographicOperations.ZeroMemory(key); }
        }
        else Assert.False(Directory.Exists(fixture.Instances));
    }

    [Fact]
    public void RetainedPublishedStoreIsCompleteAndDeclaredByItsRealPath()
    {
        using var fixture = new Root();
        FileStream? retained = null;
        try
        {
            var error = Assert.Throws<MfaKeyStoreCreationException>(() => fixture.Create(afterPublish: () =>
            {
                retained = new FileStream(System.IO.Path.Combine(fixture.Keys, MfaKeyRing.RingFileName),
                    FileMode.Open, FileAccess.Read, FileShare.Read);
                throw new IOException("synthetic retained publication");
            }));
            Assert.Equal(MfaKeyStoreCreationErrorKind.PublishFailed, error.Kind);
            Assert.Contains(fixture.Keys, error.Residue);
            Assert.Equal(2, Directory.GetFiles(fixture.Keys).Length);
            var before = Directory.GetFiles(fixture.Keys).ToDictionary(p => p, File.ReadAllBytes);
            Assert.Throws<MfaKeyStoreCreationException>(() => fixture.Create());
            foreach (var (path, bytes) in before) Assert.Equal(bytes, File.ReadAllBytes(path));
        }
        finally { retained?.Dispose(); }
    }

    [Fact]
    public void PermissiveParentAndSeparateManagementAreNotChanged()
    {
        using var fixture = new Root();
        var management = Path.Combine(fixture.Path, "management");
        Directory.CreateDirectory(management);
        File.WriteAllText(System.IO.Path.Combine(management, "sentinel.txt"), "synthetic");
        var parentAcl = new DirectoryInfo(fixture.Path).GetAccessControl().GetSecurityDescriptorSddlForm(AccessControlSections.Access);
        var managementAcl = new DirectoryInfo(management).GetAccessControl().GetSecurityDescriptorSddlForm(AccessControlSections.Access);
        fixture.Create();
        Assert.Equal(parentAcl, new DirectoryInfo(fixture.Path).GetAccessControl().GetSecurityDescriptorSddlForm(AccessControlSections.Access));
        Assert.Equal(managementAcl, new DirectoryInfo(management).GetAccessControl().GetSecurityDescriptorSddlForm(AccessControlSections.Access));
        Assert.Equal("synthetic", File.ReadAllText(System.IO.Path.Combine(management, "sentinel.txt")));
        var before = Directory.GetFiles(fixture.Keys).ToDictionary(p => p, File.ReadAllBytes);
        var acl = new DirectoryInfo(fixture.Keys).GetAccessControl().GetSecurityDescriptorSddlForm(AccessControlSections.Access);
        Assert.Throws<MfaKeyStoreCreationException>(() => fixture.Create());
        Assert.Equal(acl, new DirectoryInfo(fixture.Keys).GetAccessControl().GetSecurityDescriptorSddlForm(AccessControlSections.Access));
        foreach (var (path, bytes) in before) Assert.Equal(bytes, File.ReadAllBytes(path));
    }

    private static void AssertExactAcl(string path, bool directory, Root fixture)
    {
        FileSystemSecurity acl = directory ? new DirectoryInfo(path).GetAccessControl() : new FileInfo(path).GetAccessControl();
        Assert.True(acl.AreAccessRulesProtected, "Object must be protected at native creation, before any later ACL operation.");
        var rules = acl.GetAccessRules(true, true, typeof(SecurityIdentifier)).Cast<FileSystemAccessRule>().ToArray();
        Assert.Equal(fixture.Trusted.Length + 1, rules.Length);
        foreach (var rule in rules)
        {
            Assert.False(rule.IsInherited);
            Assert.Equal(AccessControlType.Allow, rule.AccessControlType);
            var sid = (SecurityIdentifier)rule.IdentityReference;
            Assert.True(sid == fixture.Reader || fixture.Trusted.Contains(sid));
            var expected = sid == fixture.Reader ? FileSystemRights.ReadAndExecute : FileSystemRights.FullControl;
            // Windows may add SYNCHRONIZE to an allow ACE; no additional modification rights are allowed.
            Assert.Equal(expected & ~FileSystemRights.Synchronize, rule.FileSystemRights & ~FileSystemRights.Synchronize);
            Assert.Equal(directory ? InheritanceFlags.ContainerInherit | InheritanceFlags.ObjectInherit : InheritanceFlags.None,
                rule.InheritanceFlags);
        }
    }

    private sealed class Root : IDisposable
    {
        public Root(Guid? installation = null)
        {
            Path = System.IO.Path.Combine(System.IO.Path.GetTempPath(), "rackclick-f0401-" + Guid.NewGuid().ToString("N"));
            Directory.CreateDirectory(Path);
            var security = new DirectorySecurity();
            security.SetAccessRuleProtection(true, false);
            const InheritanceFlags inherit = InheritanceFlags.ContainerInherit | InheritanceFlags.ObjectInherit;
            foreach (var sid in Trusted) security.AddAccessRule(new FileSystemAccessRule(sid, FileSystemRights.FullControl, inherit,
                PropagationFlags.None, AccessControlType.Allow));
            security.AddAccessRule(new FileSystemAccessRule(new SecurityIdentifier(WellKnownSidType.WorldSid, null),
                FileSystemRights.ReadAndExecute, inherit, PropagationFlags.None, AccessControlType.Allow));
            new DirectoryInfo(Path).SetAccessControl(security);
            Installation = installation ?? Guid.NewGuid();
        }

        public string Path { get; }
        public Guid Installation { get; }
        public SecurityIdentifier Reader { get; } = new(WellKnownSidType.BuiltinUsersSid, null);
        public SecurityIdentifier[] Trusted { get; } = [WindowsIdentity.GetCurrent().User!,
            new(WellKnownSidType.LocalSystemSid, null), new(WellKnownSidType.BuiltinAdministratorsSid, null)];
        public string Instances => System.IO.Path.Combine(Path, "Instances");
        public string InstallationFolder => System.IO.Path.Combine(Instances, Installation.ToString("D"));
        public string Keys => System.IO.Path.Combine(InstallationFolder, WindowsMfaKeyProvider.KeysFolderName);
        public WindowsMfaKeyProvider Provider() => new(Instances, Installation, Reader, Trusted);
        public void Create(Action<string, bool>? observed = null, Action? beforePublish = null, Action? afterPublish = null) =>
            WindowsMfaKeyStoreWriter.CreateInitialStore(Instances, Installation, Reader, Trusted,
                beforePublish: beforePublish, afterObjectCreated: observed, afterPublish: afterPublish);
        public void Dispose()
        {
            var resolved = System.IO.Path.GetFullPath(Path);
            var temp = System.IO.Path.GetFullPath(System.IO.Path.GetTempPath()).TrimEnd(System.IO.Path.DirectorySeparatorChar)
                + System.IO.Path.DirectorySeparatorChar;
            if (!resolved.StartsWith(temp, StringComparison.OrdinalIgnoreCase) ||
                !System.IO.Path.GetFileName(resolved).StartsWith("rackclick-f0401-", StringComparison.Ordinal))
                throw new InvalidOperationException("unsafe fixture cleanup target");
            if (Directory.Exists(resolved)) Directory.Delete(resolved, true);
        }
    }
}
