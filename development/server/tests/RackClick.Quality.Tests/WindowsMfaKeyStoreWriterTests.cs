using System.Runtime.Versioning;
using System.Security.Principal;
using System.Text;
using RackClick.Server;
using Xunit;

namespace RackClick.Quality.Tests;

// Creación inicial del almacén MFA (MFA-L2c) con ACL y DPAPI reales, en carpetas nuevas bajo %TEMP%. No crea cuentas ni
// servicios. El lector de pruebas es el grupo Usuarios. Los fixtures declaran al propietario de laboratorio como confiable;
// esa confianza no es una excepción de producción ni acredita el SID real del servicio.
[SupportedOSPlatform("windows")]
public sealed class WindowsMfaKeyStoreWriterTests
{
    private static readonly SecurityIdentifier UsersSid = new(WellKnownSidType.BuiltinUsersSid, null);
    private static readonly SecurityIdentifier LocalSystemSid = new(WellKnownSidType.LocalSystemSid, null);
    private static readonly SecurityIdentifier AdministratorsSid = new(WellKnownSidType.BuiltinAdministratorsSid, null);

    [Fact]
    public void CreatedStoreIsReadByTheExistingProviderAndHoldsNoClearKey()
    {
        using var fixture = new CreationRoot();
        Create(fixture);
        var provider = new WindowsMfaKeyProvider(fixture.Instances, fixture.Installation, UsersSid, fixture.Trusted);

        var key = provider.GetKey(1);

        Assert.Equal(MfaKeyRing.KeyBytes, key.Length);
        Assert.Equal(key, provider.GetKey(1));
        // La clave no aparece en claro ni en base64 en ningún archivo del almacén.
        var keyFile = File.ReadAllBytes(fixture.KeyFile(1));
        var ringFile = File.ReadAllBytes(fixture.RingFile);
        Assert.False(ContainsSequence(keyFile, key));
        Assert.False(ContainsSequence(ringFile, key));
        Assert.DoesNotContain(Convert.ToBase64String(key), Encoding.UTF8.GetString(keyFile), StringComparison.Ordinal);
        // Publicación completa: sin staging y con el contenido esperado.
        Assert.Empty(fixture.StagingEntries());
        var names = Directory.GetFiles(fixture.KeysFolder).Select(path => Path.GetFileName(path)).Order(StringComparer.Ordinal).ToArray();
        Assert.Equal(new[] { MfaKeyRing.KeyFileName(1), MfaKeyRing.RingFileName }.Order(StringComparer.Ordinal).ToArray(), names);
    }

    [Theory]
    [InlineData("vacio")]
    [InlineData("parcial")]
    [InlineData("corrupto")]
    [InlineData("archivo")]
    public void ExistingDestinationIsRefusedAndItsBytesAreKept(string kind)
    {
        using var fixture = new CreationRoot();
        Directory.CreateDirectory(fixture.InstallationFolder);
        switch (kind)
        {
            case "vacio":
                Directory.CreateDirectory(fixture.KeysFolder);
                break;
            case "parcial":
                Directory.CreateDirectory(fixture.KeysFolder);
                File.WriteAllText(fixture.RingFile, "{\"format\"", Encoding.UTF8);
                break;
            case "corrupto":
                Directory.CreateDirectory(fixture.KeysFolder);
                File.WriteAllBytes(fixture.RingFile, [0xFF, 0x00, 0x7B]);
                File.WriteAllBytes(fixture.KeyFile(1), [1, 2, 3, 4]);
                break;
            case "archivo":
                File.WriteAllBytes(fixture.KeysFolder, [1, 2, 3]);
                break;
        }
        var before = fixture.Listing();

        var error = Assert.Throws<MfaKeyStoreCreationException>(() => Create(fixture));

        Assert.Equal(MfaKeyStoreCreationErrorKind.AlreadyExists, error.Kind);
        Assert.Equal(before, fixture.Listing());
    }

    [Fact]
    public void PublishRaceKeepsTheExistingDestinationAndLeavesNoStaging()
    {
        using var fixture = new CreationRoot();

        var error = Assert.Throws<MfaKeyStoreCreationException>(() => Create(fixture, beforePublish: () =>
        {
            Directory.CreateDirectory(fixture.KeysFolder);
            File.WriteAllBytes(Path.Combine(fixture.KeysFolder, "centinela.bin"), [9, 8, 7]);
        }));

        Assert.Equal(MfaKeyStoreCreationErrorKind.AlreadyExists, error.Kind);
        Assert.Equal(new byte[] { 9, 8, 7 }, File.ReadAllBytes(Path.Combine(fixture.KeysFolder, "centinela.bin")));
        Assert.Single(Directory.GetFileSystemEntries(fixture.KeysFolder));
        Assert.Empty(fixture.StagingEntries());
        // Sin almacén válido, el proveedor no genera ni presenta una clave.
        var provider = new WindowsMfaKeyProvider(fixture.Instances, fixture.Installation, UsersSid, fixture.Trusted);
        var missing = Assert.Throws<MfaKeyRingException>(() => provider.GetKey(1));
        Assert.Equal(MfaKeyRingErrorKind.MissingFile, missing.Kind);
        Assert.Single(Directory.GetFileSystemEntries(fixture.KeysFolder));
    }

    [Fact]
    public void PublishFailureReportsFailureAndRemovesEverythingThisCallCreated()
    {
        using var fixture = new CreationRoot();

        var error = Assert.Throws<MfaKeyStoreCreationException>(() => Create(fixture,
            beforePublish: () => throw new IOException("fallo simulado de publicación")));

        Assert.Equal(MfaKeyStoreCreationErrorKind.PublishFailed, error.Kind);
        Assert.False(Directory.Exists(fixture.KeysFolder));
        Assert.Empty(fixture.StagingEntries());
        Assert.False(Directory.Exists(fixture.Instances));
    }

    [Fact]
    public void ExistingAncestorWithoutTheStoreAclIsRefusedBeforeAnyWrite()
    {
        using var fixture = new CreationRoot();
        Directory.CreateDirectory(fixture.Instances);
        var before = fixture.Listing();

        var error = Assert.Throws<MfaKeyStoreCreationException>(() => Create(fixture));

        Assert.Equal(MfaKeyStoreCreationErrorKind.ValidationFailed, error.Kind);
        var inner = Assert.IsType<MfaKeyRingException>(error.InnerException);
        Assert.Equal(MfaKeyRingErrorKind.UnsafeAccess, inner.Kind);
        Assert.Equal(before, fixture.Listing());
    }

    // El creador no está entre los principales de confianza: en esta sesión no elevada no conserva acceso al staging.
    // La prueba fija lo que importa (nada publicado, nada residual) sin fijar la clase de fallo al entorno.
    [Fact]
    public void CreatorWithoutRightsPublishesNothing()
    {
        using var fixture = new CreationRoot();

        Assert.Throws<MfaKeyStoreCreationException>(() =>
            WindowsMfaKeyStoreWriter.CreateInitialStore(fixture.Instances, fixture.Installation, UsersSid,
                new[] { LocalSystemSid, AdministratorsSid }));

        Assert.False(Directory.Exists(fixture.KeysFolder));
        Assert.False(Directory.Exists(fixture.Instances));
        Assert.Empty(fixture.StagingEntries());
    }

    [Fact]
    public void InvalidRequestsAreRefusedBeforeAnyWrite()
    {
        using var fixture = new CreationRoot();
        var before = fixture.Listing();

        var readerIsTrusted = Assert.Throws<MfaKeyStoreCreationException>(() =>
            WindowsMfaKeyStoreWriter.CreateInitialStore(fixture.Instances, fixture.Installation, UsersSid,
                new[] { UsersSid, fixture.Me }));
        var noTrusted = Assert.Throws<MfaKeyStoreCreationException>(() =>
            WindowsMfaKeyStoreWriter.CreateInitialStore(fixture.Instances, fixture.Installation, UsersSid, Array.Empty<SecurityIdentifier>()));
        var relative = Assert.Throws<MfaKeyStoreCreationException>(() =>
            WindowsMfaKeyStoreWriter.CreateInitialStore("relativa\\Instances", fixture.Installation, UsersSid, fixture.Trusted));

        Assert.Equal(MfaKeyStoreCreationErrorKind.InvalidRequest, readerIsTrusted.Kind);
        Assert.Equal(MfaKeyStoreCreationErrorKind.InvalidRequest, noTrusted.Kind);
        Assert.Equal(MfaKeyStoreCreationErrorKind.InvalidRequest, relative.Kind);
        Assert.Equal(before, fixture.Listing());
    }

    private static void Create(CreationRoot fixture, Action? beforePublish = null) =>
        WindowsMfaKeyStoreWriter.CreateInitialStore(fixture.Instances, fixture.Installation, UsersSid, fixture.Trusted, beforePublish);

    private static bool ContainsSequence(byte[] haystack, byte[] needle)
    {
        for (var i = 0; i + needle.Length <= haystack.Length; i++)
            if (haystack.AsSpan(i, needle.Length).SequenceEqual(needle)) return true;
        return false;
    }

    // Raíz nueva con el padre existente: la creación crea la raíz "Instances" y la carpeta de la instalación.
    private sealed class CreationRoot : IDisposable
    {
        public CreationRoot()
        {
            Root = Path.Combine(Path.GetTempPath(), "rackclick-mfa-l2c", Guid.NewGuid().ToString("N"));
            Directory.CreateDirectory(Root);
            Instances = Path.Combine(Root, "Instances");
            Installation = Guid.NewGuid();
            Me = WindowsIdentity.GetCurrent().User ?? throw new InvalidOperationException("sin SID de usuario");
            Trusted = [Me, LocalSystemSid, AdministratorsSid];
        }

        public string Root { get; }
        public string Instances { get; }
        public Guid Installation { get; }
        public SecurityIdentifier Me { get; }
        public SecurityIdentifier[] Trusted { get; }

        public string InstallationFolder => Path.Combine(Instances, Installation.ToString("D"));
        public string KeysFolder => Path.Combine(InstallationFolder, WindowsMfaKeyProvider.KeysFolderName);
        public string RingFile => Path.Combine(KeysFolder, MfaKeyRing.RingFileName);
        public string KeyFile(int version) => Path.Combine(KeysFolder, MfaKeyRing.KeyFileName(version));

        public string[] StagingEntries() =>
            Directory.Exists(InstallationFolder)
                ? Directory.EnumerateFileSystemEntries(InstallationFolder)
                    .Where(p => Path.GetFileName(p).StartsWith("mfa-keys.preparando-", StringComparison.Ordinal))
                    .ToArray()
                : [];

        // Listado con tamaño y fecha de modificación: cualquier escritura, creación o borrado lo cambia.
        public string[] Listing()
        {
            var entries = new List<string>();
            foreach (var path in Directory.EnumerateFileSystemEntries(Root, "*", SearchOption.AllDirectories))
            {
                FileSystemInfo item = Directory.Exists(path) ? new DirectoryInfo(path) : new FileInfo(path);
                var size = item is FileInfo file ? file.Length : -1;
                entries.Add(item.FullName + "|" + item.LastWriteTimeUtc.Ticks + "|" + size);
            }
            entries.Sort(StringComparer.Ordinal);
            return entries.ToArray();
        }

        public void Dispose() => Directory.Delete(Root, true);
    }
}
