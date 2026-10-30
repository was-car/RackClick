using System.Runtime.Versioning;
using System.Security.AccessControl;
using System.Security.Cryptography;
using System.Security.Principal;
using System.Text;
using RackClick.Server;
using Xunit;

namespace RackClick.Quality.Tests;

// Exportación y recuperación del anillo (MFA-L2f) con almacenes sintéticos en carpetas TEMP nuevas. Misma máquina y token de
// laboratorio: no se afirma portabilidad DPAPI ni acceso bajo el SID real del servicio. El lector de pruebas es el grupo Usuarios.
// Los fixtures declaran al propietario de laboratorio como principal de confianza; no es excepción de producción.
[SupportedOSPlatform("windows")]
public sealed class WindowsMfaKeyRecoveryTests
{
    private static readonly SecurityIdentifier UsersSid = new(WellKnownSidType.BuiltinUsersSid, null);
    private static readonly SecurityIdentifier LocalSystemSid = new(WellKnownSidType.LocalSystemSid, null);
    private static readonly SecurityIdentifier AdministratorsSid = new(WellKnownSidType.BuiltinAdministratorsSid, null);
    private const string Password = "clave-de-laboratorio-recuperacion";

    [Fact]
    public void ExportedEnvelopeRecoversEveryVersionAtANewDestinationWithTheSameKeys()
    {
        using var lab = new Lab();
        var originKeys = CreateOrigin(lab);
        var before = lab.Snapshot(lab.OriginRoot);

        var envelope = WindowsMfaKeyRecovery.Export(lab.OriginRoot, lab.Origin, UsersSid, lab.Trusted, Password);
        Assert.Equal(before, lab.Snapshot(lab.OriginRoot));

        WindowsMfaKeyRecovery.Recover(envelope, Password, lab.Origin, lab.DestinationRoot, lab.Destination, UsersSid, lab.Trusted,
            adaptDestinationInstallation: true);

        var provider = new WindowsMfaKeyProvider(lab.DestinationRoot, lab.Destination, UsersSid, lab.Trusted);
        foreach (var (version, key) in originKeys)
        {
            var recovered = provider.GetKey(version);
            Assert.True(CryptographicOperations.FixedTimeEquals(key, recovered), "la clave recuperada no coincide con la original");
            CryptographicOperations.ZeroMemory(recovered);
        }

        var destinationRing = MfaKeyRing.Parse(File.ReadAllBytes(lab.DestinationRing), lab.Destination);
        Assert.Equal(new[] { 1, 2 }, destinationRing.Entries.Select(entry => entry.Version));
        Assert.Equal(MfaKeyState.Retired, destinationRing.Entries[0].State);
        Assert.Equal(MfaKeyState.Active, destinationRing.Entries[1].State);
        Assert.Equal(new DateTimeOffset(2026, 10, 1, 8, 30, 0, TimeSpan.Zero), destinationRing.Entries[0].CreatedAtUtc);
        Assert.Equal(new DateTimeOffset(2026, 10, 25, 10, 0, 0, TimeSpan.Zero), destinationRing.Entries[1].CreatedAtUtc);

        // Un factor sintético cifrado con sus AAD originales sigue descifrando con la clave recuperada.
        var secret = RandomNumberGenerator.GetBytes(20);
        var systemhaus = Guid.NewGuid();
        var user = Guid.NewGuid();
        var factor = MfaSecretCipher.Seal(originKeys[1].Key, 2, secret, systemhaus, user);
        var recoveredKey2 = provider.GetKey(2);
        var opened = MfaSecretCipher.Open(recoveredKey2, 2, factor, systemhaus, user);
        Assert.True(CryptographicOperations.FixedTimeEquals(secret, opened), "el factor no descifra con la clave recuperada");
        CryptographicOperations.ZeroMemory(recoveredKey2);
        CryptographicOperations.ZeroMemory(opened);
    }

    [Fact]
    public void StoreCreatedByCreateInitialStoreExportsAndRecoversItsOnlyKey()
    {
        using var lab = new Lab();
        WindowsMfaKeyStoreWriter.CreateInitialStore(lab.OriginRoot, lab.Origin, UsersSid, lab.Trusted);
        // La versión inicial del escritor es 1 (constante privada del escritor).
        var originKey = new WindowsMfaKeyProvider(lab.OriginRoot, lab.Origin, UsersSid, lab.Trusted).GetKey(1);
        var before = lab.Snapshot(lab.OriginRoot);

        var envelope = WindowsMfaKeyRecovery.Export(lab.OriginRoot, lab.Origin, UsersSid, lab.Trusted, Password);
        Assert.Equal(before, lab.Snapshot(lab.OriginRoot));

        WindowsMfaKeyRecovery.Recover(envelope, Password, lab.Origin, lab.DestinationRoot, lab.Destination, UsersSid, lab.Trusted,
            adaptDestinationInstallation: true);

        var recovered = new WindowsMfaKeyProvider(lab.DestinationRoot, lab.Destination, UsersSid, lab.Trusted).GetKey(1);
        Assert.True(CryptographicOperations.FixedTimeEquals(originKey, recovered), "la clave recuperada no coincide con la original");
        var ring = MfaKeyRing.Parse(File.ReadAllBytes(lab.DestinationRing), lab.Destination);
        Assert.Single(ring.Entries);
        Assert.Equal(MfaKeyState.Active, ring.Entries[0].State);
        CryptographicOperations.ZeroMemory(originKey);
        CryptographicOperations.ZeroMemory(recovered);
    }

    [Fact]
    public void SameInstallationRecoversWithoutAdaptation()
    {
        using var lab = new Lab();
        var originKeys = CreateOrigin(lab);
        var envelope = WindowsMfaKeyRecovery.Export(lab.OriginRoot, lab.Origin, UsersSid, lab.Trusted, Password);

        WindowsMfaKeyRecovery.Recover(envelope, Password, lab.Origin, lab.DestinationRoot, lab.Origin, UsersSid, lab.Trusted,
            adaptDestinationInstallation: false);

        var provider = new WindowsMfaKeyProvider(lab.DestinationRoot, lab.Origin, UsersSid, lab.Trusted);
        var recovered = provider.GetKey(1);
        Assert.True(CryptographicOperations.FixedTimeEquals(originKeys[0].Key, recovered), "la clave recuperada no coincide");
        CryptographicOperations.ZeroMemory(recovered);
    }

    [Fact]
    public void ExportFailsWithoutAPartialEnvelopeWhenAVersionIsMissing()
    {
        using var lab = new Lab();
        CreateOrigin(lab);
        File.Delete(lab.OriginKeyFile(2));

        var error = Assert.Throws<WindowsMfaKeyRecoveryException>(() =>
            WindowsMfaKeyRecovery.Export(lab.OriginRoot, lab.Origin, UsersSid, lab.Trusted, Password));

        Assert.Equal(WindowsMfaKeyRecoveryErrorKind.SourceRejected, error.Kind);
    }

    [Fact]
    public void ExportFailsWithoutAPartialEnvelopeWhenAVersionIsCorrupt()
    {
        using var lab = new Lab();
        CreateOrigin(lab);
        File.WriteAllText(lab.OriginKeyFile(2), "{no-es-json", Encoding.UTF8);

        var error = Assert.Throws<WindowsMfaKeyRecoveryException>(() =>
            WindowsMfaKeyRecovery.Export(lab.OriginRoot, lab.Origin, UsersSid, lab.Trusted, Password));

        Assert.Equal(WindowsMfaKeyRecoveryErrorKind.SourceRejected, error.Kind);
    }

    [Fact]
    public void RingChangedDuringExportIsNeverReturned()
    {
        using var lab = new Lab();
        CreateOrigin(lab);
        var changed = Encoding.UTF8.GetBytes(MfaKeyJson.Ring(lab.Origin,
            MfaKeyJson.Entry(1, "retired", "2026-10-01T08:30:00Z") + "," + MfaKeyJson.Entry(2, "active", "2026-10-26T09:00:00Z")));

        var error = Assert.Throws<WindowsMfaKeyRecoveryException>(() =>
            WindowsMfaKeyRecovery.Export(lab.OriginRoot, lab.Origin, UsersSid, lab.Trusted, Password,
                beforeCoherenceCheck: () => File.WriteAllBytes(lab.OriginRing, changed)));

        Assert.Equal(WindowsMfaKeyRecoveryErrorKind.Incoherent, error.Kind);
    }

    [Fact]
    public void WrongPasswordOrAlteredEnvelopeFailsWithoutCreatingAnything()
    {
        using var lab = new Lab();
        CreateOrigin(lab);
        var envelope = WindowsMfaKeyRecovery.Export(lab.OriginRoot, lab.Origin, UsersSid, lab.Trusted, Password);
        var altered = (byte[])envelope.Clone();
        altered[^1] ^= 0x01; // último byte: etiqueta GCM del sobre, no cabecera ni longitud

        var wrong = Assert.Throws<WindowsMfaKeyRecoveryException>(() =>
            WindowsMfaKeyRecovery.Recover(envelope, "clave-de-prueba-erronea", lab.Origin, lab.DestinationRoot, lab.Destination,
                UsersSid, lab.Trusted, adaptDestinationInstallation: true));
        var tampered = Assert.Throws<WindowsMfaKeyRecoveryException>(() =>
            WindowsMfaKeyRecovery.Recover(altered, Password, lab.Origin, lab.DestinationRoot, lab.Destination,
                UsersSid, lab.Trusted, adaptDestinationInstallation: true));

        Assert.Equal(WindowsMfaKeyRecoveryErrorKind.AuthenticationFailed, wrong.Kind);
        Assert.Equal(WindowsMfaKeyRecoveryErrorKind.AuthenticationFailed, tampered.Kind);
        Assert.False(Directory.Exists(lab.DestinationRoot), "un fallo de autenticación creó el destino");
    }

    [Fact]
    public void WrongExpectedSourceIdentityFailsBeforeCreatingAnything()
    {
        using var lab = new Lab();
        CreateOrigin(lab);
        var envelope = WindowsMfaKeyRecovery.Export(lab.OriginRoot, lab.Origin, UsersSid, lab.Trusted, Password);

        var error = Assert.Throws<WindowsMfaKeyRecoveryException>(() =>
            WindowsMfaKeyRecovery.Recover(envelope, Password, Guid.NewGuid(), lab.DestinationRoot, lab.Destination,
                UsersSid, lab.Trusted, adaptDestinationInstallation: true));

        Assert.Equal(WindowsMfaKeyRecoveryErrorKind.PayloadRejected, error.Kind);
        Assert.False(Directory.Exists(lab.DestinationRoot), "una identidad de origen equivocada creó el destino");
    }

    [Fact]
    public void DifferentDestinationWithoutExplicitAdaptationIsRefusedBeforeAnyWork()
    {
        using var lab = new Lab();
        CreateOrigin(lab);
        var envelope = WindowsMfaKeyRecovery.Export(lab.OriginRoot, lab.Origin, UsersSid, lab.Trusted, Password);

        var error = Assert.Throws<WindowsMfaKeyRecoveryException>(() =>
            WindowsMfaKeyRecovery.Recover(envelope, Password, lab.Origin, lab.DestinationRoot, lab.Destination,
                UsersSid, lab.Trusted, adaptDestinationInstallation: false));

        Assert.Equal(WindowsMfaKeyRecoveryErrorKind.InvalidRequest, error.Kind);
        Assert.False(Directory.Exists(lab.DestinationRoot), "se creó el destino sin adaptación explícita");
    }

    [Theory]
    [InlineData("vacio")]
    [InlineData("parcial")]
    [InlineData("corrupto")]
    [InlineData("archivo")]
    public void ExistingDestinationIsRefusedAndItsBytesAreKept(string kind)
    {
        using var lab = new Lab();
        CreateOrigin(lab);
        var envelope = WindowsMfaKeyRecovery.Export(lab.OriginRoot, lab.Origin, UsersSid, lab.Trusted, Password);
        Directory.CreateDirectory(lab.DestinationInstallation);
        switch (kind)
        {
            case "vacio":
                Directory.CreateDirectory(lab.DestinationKeys);
                break;
            case "parcial":
                Directory.CreateDirectory(lab.DestinationKeys);
                File.WriteAllText(lab.DestinationRing, "{\"format\"", Encoding.UTF8);
                break;
            case "corrupto":
                Directory.CreateDirectory(lab.DestinationKeys);
                File.WriteAllBytes(lab.DestinationRing, [0xFF, 0x00, 0x7B]);
                File.WriteAllBytes(Path.Combine(lab.DestinationKeys, MfaKeyRing.KeyFileName(1)), [1, 2, 3, 4]);
                break;
            case "archivo":
                File.WriteAllBytes(lab.DestinationKeys, [1, 2, 3]);
                break;
            default:
                throw new ArgumentOutOfRangeException(nameof(kind), kind, null);
        }
        var before = lab.Snapshot(lab.DestinationRoot);

        var error = Assert.Throws<WindowsMfaKeyRecoveryException>(() =>
            WindowsMfaKeyRecovery.Recover(envelope, Password, lab.Origin, lab.DestinationRoot, lab.Destination,
                UsersSid, lab.Trusted, adaptDestinationInstallation: true));

        Assert.Equal(WindowsMfaKeyRecoveryErrorKind.DestinationRejected, error.Kind);
        Assert.Equal(MfaKeyStoreCreationErrorKind.AlreadyExists, Assert.IsType<MfaKeyStoreCreationException>(error.InnerException).Kind);
        Assert.Equal(before, lab.Snapshot(lab.DestinationRoot));
    }

    [Fact]
    public void PublishRaceAtDestinationKeepsTheForeignContentWithoutSuccess()
    {
        using var lab = new Lab();
        CreateOrigin(lab);
        var envelope = WindowsMfaKeyRecovery.Export(lab.OriginRoot, lab.Origin, UsersSid, lab.Trusted, Password);

        var error = Assert.Throws<WindowsMfaKeyRecoveryException>(() =>
            WindowsMfaKeyRecovery.Recover(envelope, Password, lab.Origin, lab.DestinationRoot, lab.Destination,
                UsersSid, lab.Trusted, adaptDestinationInstallation: true,
                beforePublish: () =>
                {
                    Directory.CreateDirectory(lab.DestinationKeys);
                    File.WriteAllBytes(Path.Combine(lab.DestinationKeys, "centinela.bin"), [9, 8, 7]);
                }));

        Assert.Equal(WindowsMfaKeyRecoveryErrorKind.DestinationRejected, error.Kind);
        Assert.Equal(MfaKeyStoreCreationErrorKind.AlreadyExists, Assert.IsType<MfaKeyStoreCreationException>(error.InnerException).Kind);
        Assert.Equal(new byte[] { 9, 8, 7 }, File.ReadAllBytes(Path.Combine(lab.DestinationKeys, "centinela.bin")));
        Assert.Empty(lab.StagingEntries());
        // La instalación la creó esta llamada, pero contiene contenido ajeno: no se retira y queda declarada como residuo.
        Assert.NotEmpty(error.Residue);
        Assert.True(Directory.Exists(lab.DestinationInstallation), "la instalación con contenido ajeno no debía retirarse");
        var provider = new WindowsMfaKeyProvider(lab.DestinationRoot, lab.Destination, UsersSid, lab.Trusted);
        var missing = Assert.Throws<MfaKeyRingException>(() => provider.GetKey(1));
        Assert.Equal(MfaKeyRingErrorKind.MissingFile, missing.Kind);
    }

    [Fact]
    public void IntermediateFailureAtDestinationLeavesNoStoreAndNoResidue()
    {
        using var lab = new Lab();
        CreateOrigin(lab);
        var envelope = WindowsMfaKeyRecovery.Export(lab.OriginRoot, lab.Origin, UsersSid, lab.Trusted, Password);

        var error = Assert.Throws<WindowsMfaKeyRecoveryException>(() =>
            WindowsMfaKeyRecovery.Recover(envelope, Password, lab.Origin, lab.DestinationRoot, lab.Destination,
                UsersSid, lab.Trusted, adaptDestinationInstallation: true,
                beforePublish: () => throw new IOException("fallo simulado de publicación")));

        Assert.Equal(WindowsMfaKeyRecoveryErrorKind.DestinationRejected, error.Kind);
        Assert.Equal(MfaKeyStoreCreationErrorKind.PublishFailed, Assert.IsType<MfaKeyStoreCreationException>(error.InnerException).Kind);
        Assert.Empty(error.Residue);
        Assert.False(Directory.Exists(lab.DestinationKeys), "un fallo intermedio dejó un almacén publicado");
        Assert.False(Directory.Exists(lab.DestinationRoot), "un fallo intermedio dejó carpetas propias sin retirar");
    }

    [Theory]
    [InlineData("faltante")]
    [InlineData("extra")]
    [InlineData("duplicada")]
    [InlineData("clave-corta")]
    public void MaterialInconsistentWithItsRingIsRefusedBeforeAnyWrite(string shape)
    {
        using var lab = new Lab();
        var ring = Encoding.UTF8.GetBytes(MfaKeyJson.Ring(lab.Destination,
            MfaKeyJson.Entry(1, "retired", "2026-10-01T08:30:00Z") + "," + MfaKeyJson.Entry(2, "active", "2026-10-25T10:00:00Z")));
        var key = RandomNumberGenerator.GetBytes(32);
        var keys = shape switch
        {
            "faltante" => new List<(int Version, byte[] Key)> { (1, key) },
            "extra" => new List<(int Version, byte[] Key)> { (1, key), (3, RandomNumberGenerator.GetBytes(32)) },
            "duplicada" => new List<(int Version, byte[] Key)> { (1, key), (1, RandomNumberGenerator.GetBytes(32)) },
            "clave-corta" => new List<(int Version, byte[] Key)> { (1, key), (2, new byte[31]) },
            _ => throw new ArgumentOutOfRangeException(nameof(shape), shape, null),
        };

        var error = Assert.Throws<MfaKeyStoreCreationException>(() =>
            WindowsMfaKeyStoreWriter.CreateStoreFromMaterial(lab.DestinationRoot, lab.Destination, UsersSid, lab.Trusted, ring, keys));

        Assert.Equal(MfaKeyStoreCreationErrorKind.InvalidRequest, error.Kind);
        Assert.False(Directory.Exists(lab.DestinationRoot), "un material incoherente creó el destino");
    }

    // Origen creado por el escritor con dos versiones: la 1 retirada y la 2 activa. Las claves son sintéticas y nuevas.
    private static List<(int Version, byte[] Key)> CreateOrigin(Lab lab)
    {
        var keys = new List<(int Version, byte[] Key)>
        {
            (1, RandomNumberGenerator.GetBytes(MfaKeyRing.KeyBytes)),
            (2, RandomNumberGenerator.GetBytes(MfaKeyRing.KeyBytes)),
        };
        var ring = Encoding.UTF8.GetBytes(MfaKeyJson.Ring(lab.Origin,
            MfaKeyJson.Entry(1, "retired", "2026-10-01T08:30:00Z") + "," + MfaKeyJson.Entry(2, "active", "2026-10-25T10:00:00Z")));
        WindowsMfaKeyStoreWriter.CreateStoreFromMaterial(lab.OriginRoot, lab.Origin, UsersSid, lab.Trusted, ring, keys);
        return keys;
    }

    // Raíz TEMP nueva por prueba: origen y destino son carpetas distintas bajo la misma raíz.
    private sealed class Lab : IDisposable
    {
        public Lab()
        {
            Root = Path.Combine(Path.GetTempPath(), "rackclick-mfa-l2f", Guid.NewGuid().ToString("N"));
            Directory.CreateDirectory(Root);
            Origin = Guid.NewGuid();
            Destination = Guid.NewGuid();
            Me = WindowsIdentity.GetCurrent().User ?? throw new InvalidOperationException("sin SID de usuario");
            Trusted = [Me, LocalSystemSid, AdministratorsSid];
        }

        public string Root { get; }
        public Guid Origin { get; }
        public Guid Destination { get; }
        public SecurityIdentifier Me { get; }
        public SecurityIdentifier[] Trusted { get; }

        public string OriginRoot => Path.Combine(Root, "origen");
        public string DestinationRoot => Path.Combine(Root, "destino");
        public string DestinationInstallation => Path.Combine(DestinationRoot, Destination.ToString("D"));
        public string DestinationKeys => Path.Combine(DestinationInstallation, WindowsMfaKeyProvider.KeysFolderName);
        public string DestinationRing => Path.Combine(DestinationKeys, MfaKeyRing.RingFileName);
        public string OriginRing => Path.Combine(OriginRoot, Origin.ToString("D"), WindowsMfaKeyProvider.KeysFolderName, MfaKeyRing.RingFileName);

        public string OriginKeyFile(int version) =>
            Path.Combine(OriginRoot, Origin.ToString("D"), WindowsMfaKeyProvider.KeysFolderName, MfaKeyRing.KeyFileName(version));

        // Listado del subárbol con tamaño, fecha de escritura y ACL: cualquier cambio en el subárbol cambia la lista.
        public string[] Snapshot(string top)
        {
            var entries = new List<string>();
            foreach (var path in Directory.EnumerateFileSystemEntries(top, "*", SearchOption.AllDirectories))
            {
                if (Directory.Exists(path))
                {
                    var directory = new DirectoryInfo(path);
                    var descriptor = directory.GetAccessControl(AccessControlSections.Access).GetSecurityDescriptorBinaryForm();
                    entries.Add(directory.FullName + "|" + directory.LastWriteTimeUtc.Ticks + "|" + Convert.ToBase64String(descriptor));
                }
                else
                {
                    var file = new FileInfo(path);
                    var descriptor = file.GetAccessControl(AccessControlSections.Access).GetSecurityDescriptorBinaryForm();
                    entries.Add(file.FullName + "|" + file.LastWriteTimeUtc.Ticks + "|" + file.Length + "|" + Convert.ToBase64String(descriptor));
                }
            }
            entries.Sort(StringComparer.Ordinal);
            return entries.ToArray();
        }

        // Staging residual en la instalación de destino: no debe quedar ninguno.
        public string[] StagingEntries() =>
            Directory.Exists(DestinationInstallation)
                ? Directory.EnumerateFileSystemEntries(DestinationInstallation)
                    .Where(path => Path.GetFileName(path).StartsWith("mfa-keys.preparando-", StringComparison.Ordinal))
                    .ToArray()
                : [];

        public void Dispose()
        {
            Directory.Delete(Root, true);
            var parent = Path.GetDirectoryName(Root)!;
            // La carpeta padre compartida sólo se retira si ya no contiene nada de otras pruebas.
            if (Directory.Exists(parent) && !Directory.EnumerateFileSystemEntries(parent).Any())
                Directory.Delete(parent);
        }
    }
}
