using System.Runtime.Versioning;
using System.Security.AccessControl;
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

    // Negativo de propiedad (MFA-L2C-01, reproducido por Codex y adaptado): tras validar, el staging se sustituye por otro
    // directorio y la publicación falla. La limpieza no debe borrar el directorio sustituto.
    [Fact]
    public void FailedPublishDoesNotDeleteAReplacementDirectory()
    {
        using var fixture = new CreationRoot();
        string? sentinel = null;

        var error = Assert.Throws<MfaKeyStoreCreationException>(() => Create(fixture, beforePublish: () =>
        {
            var original = Assert.Single(fixture.StagingEntries());
            Directory.Move(original, Path.Combine(fixture.Root, "original-stage-reserved"));
            Directory.CreateDirectory(original);
            sentinel = Path.Combine(original, "external-sentinel.txt");
            File.WriteAllText(sentinel, "preserve replacement directory", Encoding.UTF8);
            throw new IOException("simulated publish failure after directory replacement");
        }));

        Assert.Equal(MfaKeyStoreCreationErrorKind.PublishFailed, error.Kind);
        Assert.NotNull(sentinel);
        Assert.True(File.Exists(sentinel), "la limpieza borró contenido de un directorio distinto en la ruta del staging");
        Assert.Equal("preserve replacement directory", File.ReadAllText(sentinel, Encoding.UTF8));
    }

    // Negativo de publicación (MFA-L2C-01): un directorio distinto del staging validado no se publica ni se devuelve éxito.
    [Fact]
    public void PublishDoesNotAcceptADirectoryDifferentFromTheValidatedStage()
    {
        using var fixture = new CreationRoot();

        var error = Assert.Throws<MfaKeyStoreCreationException>(() => Create(fixture, beforePublish: () =>
        {
            var original = Assert.Single(fixture.StagingEntries());
            Directory.Move(original, Path.Combine(fixture.Root, "original-stage-reserved"));
            Directory.CreateDirectory(original);
            File.WriteAllText(Path.Combine(original, "external-sentinel.txt"), "not the validated store", Encoding.UTF8);
        }));

        Assert.Equal(MfaKeyStoreCreationErrorKind.PublishFailed, error.Kind);
        Assert.False(Directory.Exists(fixture.KeysFolder));
        Assert.False(File.Exists(fixture.RingFile));
        Assert.False(File.Exists(fixture.KeyFile(1)));
    }

    // Carrera de creación (MFA-L2C-01, misma regla de propiedad): la carpeta de la instalación aparece entre la comprobación
    // y su creación. No se adopta, no se cambia su ACL, no se publica dentro de ella y no se borra. Se hace insegura a
    // propósito (escritura para Usuarios) para que, si se adoptara, el lector la rechazaría.
    [Fact]
    public void ForeignFolderCreatedInTheWindowIsNeitherAdoptedNorChanged()
    {
        using var fixture = new CreationRoot();
        string? sentinel = null;
        byte[]? descriptor = null;

        var error = Assert.Throws<MfaKeyStoreCreationException>(() => Create(fixture, beforeOwnFolderCreation: () =>
        {
            Directory.CreateDirectory(fixture.InstallationFolder);
            var foreign = new DirectoryInfo(fixture.InstallationFolder);
            var security = foreign.GetAccessControl(AccessControlSections.Access);
            security.AddAccessRule(new FileSystemAccessRule(UsersSid, FileSystemRights.Modify,
                InheritanceFlags.ContainerInherit | InheritanceFlags.ObjectInherit, PropagationFlags.None, AccessControlType.Allow));
            foreign.SetAccessControl(security);
            sentinel = Path.Combine(fixture.InstallationFolder, "ajeno.txt");
            File.WriteAllText(sentinel, "carpeta ajena", Encoding.UTF8);
            descriptor = fixture.DescriptorBytes(fixture.InstallationFolder);
        }));

        Assert.Equal(MfaKeyStoreCreationErrorKind.ValidationFailed, error.Kind);
        Assert.NotNull(sentinel);
        Assert.Equal("carpeta ajena", File.ReadAllText(sentinel, Encoding.UTF8));
        Assert.Equal(descriptor, fixture.DescriptorBytes(fixture.InstallationFolder));
        Assert.False(Directory.Exists(fixture.KeysFolder));
        Assert.Empty(fixture.StagingEntries());
    }

    // Reemplazo que contiene los mismos archivos propios: la comprobación de hijos pasa, así que sólo la identidad del staging
    // puede rechazarlo. Sin esa comprobación, el directorio sustituto se publicaría.
    [Fact]
    public void ReplacementHoldingTheValidatedFilesIsStillRefused()
    {
        using var fixture = new CreationRoot();

        var error = Assert.Throws<MfaKeyStoreCreationException>(() => Create(fixture, beforePublish: () =>
        {
            var original = Assert.Single(fixture.StagingEntries());
            var reserved = Path.Combine(fixture.Root, "original-stage-reserved");
            Directory.Move(original, reserved);
            Directory.CreateDirectory(original);
            File.Move(Path.Combine(reserved, MfaKeyRing.RingFileName), Path.Combine(original, MfaKeyRing.RingFileName));
            File.Move(Path.Combine(reserved, MfaKeyRing.KeyFileName(1)), Path.Combine(original, MfaKeyRing.KeyFileName(1)));
        }));

        Assert.Equal(MfaKeyStoreCreationErrorKind.PublishFailed, error.Kind);
        Assert.False(Directory.Exists(fixture.KeysFolder));
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

    private static void Create(CreationRoot fixture, Action? beforePublish = null, Action? beforeOwnFolderCreation = null) =>
        WindowsMfaKeyStoreWriter.CreateInitialStore(fixture.Instances, fixture.Installation, UsersSid, fixture.Trusted,
            beforePublish, beforeOwnFolderCreation);

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

        // Descriptor DACL en binario: comprueba que una carpeta ajena no ha cambiado de ACL.
        public byte[] DescriptorBytes(string path) =>
            new DirectoryInfo(path).GetAccessControl(AccessControlSections.Access).GetSecurityDescriptorBinaryForm();

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

        public void Dispose()
        {
            Directory.Delete(Root, true);
            // El padre común de las raíces de prueba se retira sólo si quedó vacío.
            var parent = Path.GetDirectoryName(Root)!;
            if (Directory.Exists(parent) && Directory.GetFileSystemEntries(parent).Length == 0) Directory.Delete(parent);
        }
    }
}
