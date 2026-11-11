using System.Runtime.Versioning;
using System.Security.AccessControl;
using System.Security.Cryptography;
using System.Security.Principal;
using System.Text;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using RackClick.Server;
using Xunit;

namespace RackClick.Quality.Tests;

// Composición del proveedor Windows en el host (MFA-L2i) sin PostgreSQL: almacenes TEMP sintéticos, configuración en memoria y
// seam de identidad interno. La rama productiva (SID efectivo del proceso y confianza fija SYSTEM/Administradores) sólo ejecuta su
// rechazo aquí: el propietario de los almacenes de laboratorio es el usuario actual, no SYSTEM ni Administradores. El positivo usa el
// seam, y así se declara en su diagnóstico. No se presenta como identidad efectiva del servicio.
[SupportedOSPlatform("windows")]
public sealed class MfaWindowsHostCompositionTests
{
    private static readonly SecurityIdentifier UsersSid = new(WellKnownSidType.BuiltinUsersSid, null);
    private static readonly SecurityIdentifier LocalSystemSid = new(WellKnownSidType.LocalSystemSid, null);
    private static readonly SecurityIdentifier AdministratorsSid = new(WellKnownSidType.BuiltinAdministratorsSid, null);
    private static readonly SecurityIdentifier EveryoneSid = new(WellKnownSidType.WorldSid, null);
    private const int RetiredVersion = 1;
    private const int ActiveVersion = 7;

    [Fact]
    public void ValidWindowsStoreWithPersistentMaintenanceFenceCannotComposeAHost()
    {
        using var store=StoreFixture.Create();
        var fence=Path.Combine(store.Root,store.Installation.ToString("D"),"mfa-maintenance-fence.json");
        File.WriteAllText(fence,"{\"pending\":true}");
        var before=store.Listing();var configuration=Config("true",store.Root,store.Installation.ToString("D"));
        Assert.Equal("mfa_maintenance_pending",Assert.Throws<MfaMaintenanceException>(()=>MfaWindowsHostComposition.Compose(MfaHostMode.Enabled,configuration,Identity())).Code);
        Assert.Equal(before,store.Listing());
    }

    [Theory]
    [InlineData(null, "Disabled")]
    [InlineData("", "Disabled")]
    [InlineData("false", "Disabled")]
    [InlineData("FALSE", "Disabled")]
    [InlineData("true", "Enabled")]
    [InlineData("True", "Enabled")]
    [InlineData("yes", "Invalid")]
    [InlineData("1", "Invalid")]
    public void EnabledSettingIsParsedStrictly(string? raw, string expected)
    {
        var configuration = Config(raw, root: null, installation: null);

        Assert.Equal(expected, MfaWindowsHostComposition.ModeOf(configuration).ToString());
    }

    [Fact]
    public void InvalidSwitchValueFailsClosedBeforeAnyStoreIsRead()
    {
        using var store = StoreFixture.Create();
        var configuration = Config("yes", store.Root, store.Installation.ToString("D"));
        var before = store.Listing();

        var error = Assert.Throws<MfaHostCompositionException>(() =>
            MfaWindowsHostComposition.Compose(MfaWindowsHostComposition.ModeOf(configuration), configuration, Identity()));

        Assert.Equal("mfa_keystore_config_invalid", error.Code);
        Assert.Equal(before, store.Listing());
    }

    [Fact]
    public void NonWindowsHostRefusesTheStoreWithoutTouchingDisk()
    {
        using var store = StoreFixture.Create();
        var configuration = Config("true", store.Root, store.Installation.ToString("D"));
        var before = store.Listing();

        var error = Assert.Throws<MfaHostCompositionException>(() =>
            MfaWindowsHostComposition.Compose(MfaHostMode.Enabled, configuration, Identity(), isWindows: false));

        Assert.Equal("mfa_keystore_not_windows", error.Code);
        Assert.Equal(before, store.Listing());
    }

    [Theory]
    [InlineData("root-ausente", "mfa_keystore_root_missing")]
    [InlineData("raiz-relativa", "mfa_keystore_root_relative")]
    [InlineData("instalacion-ausente", "mfa_keystore_installation_missing")]
    [InlineData("instalacion-vacia", "mfa_keystore_installation_missing")]
    [InlineData("instalacion-sin-guiones", "mfa_keystore_installation_invalid")]
    [InlineData("instalacion-con-llaves", "mfa_keystore_installation_invalid")]
    [InlineData("instalacion-no-uuid", "mfa_keystore_installation_invalid")]
    [InlineData("instalacion-vacio-uuid", "mfa_keystore_installation_invalid")]
    public void IncompleteOrInvalidConfigurationFailsClosedWithoutCreatingAnything(string shape, string expectedCode)
    {
        using var store = StoreFixture.Pending();
        var installation = store.Installation.ToString("D");
        var configuration = shape switch
        {
            "root-ausente" => Config("true", root: null, installation),
            "raiz-relativa" => Config("true", "instancias-relativas", installation),
            "instalacion-ausente" => Config("true", store.Root, installation: null),
            "instalacion-vacia" => Config("true", store.Root, "   "),
            "instalacion-sin-guiones" => Config("true", store.Root, store.Installation.ToString("N")),
            "instalacion-con-llaves" => Config("true", store.Root, "{" + installation + "}"),
            "instalacion-no-uuid" => Config("true", store.Root, "no-es-un-uuid"),
            "instalacion-vacio-uuid" => Config("true", store.Root, Guid.Empty.ToString("D")),
            _ => throw new ArgumentOutOfRangeException(nameof(shape), shape, null),
        };

        var error = Assert.Throws<MfaHostCompositionException>(() =>
            MfaWindowsHostComposition.Compose(MfaWindowsHostComposition.ModeOf(configuration), configuration, Identity()));

        Assert.Equal(expectedCode, error.Code);
        Assert.False(Directory.Exists(store.Root), "una configuración inválida creó el almacén");
    }

    // MFA-L2I-01: una raíz que la normalización de Windows rechaza (NUL) se traduce a un código constante. Un carácter que
    // la normalización acepta (<) llega a la comprobación del almacén, y allí es un almacén ausente. Ninguna excepción sale.
    [Theory]
    [InlineData("\0cola", "mfa_keystore_root_invalid")]
    [InlineData("<mala>", "mfa_keystore_store_missing")]
    public void RootCharactersAreClassifiedWithoutLeakingAnException(string suffix, string expectedCode)
    {
        using var store = StoreFixture.Pending();
        var parent = Path.Combine(Path.GetTempPath(), "rackclick-mfa-l2i-raiz");
        var existedBefore = Directory.Exists(parent);
        var root = Path.Combine(parent, "instancias") + suffix;
        var configuration = Config("true", root, store.Installation.ToString("D"));

        var error = Assert.Throws<MfaHostCompositionException>(() =>
            MfaWindowsHostComposition.Compose(MfaHostMode.Enabled, configuration, Identity(), isWindows: true));

        Assert.Equal(expectedCode, error.Code);
        Assert.Equal(existedBefore, Directory.Exists(parent));
    }

    // MFA-L2I-01: el anillo retenido en exclusiva por otro proceso es E/S no clasificable. Se rechaza sin tocar el almacén.
    [Fact]
    public void RingHeldExclusivelyIsRefusedAsUnreadableWithoutChangingTheStore()
    {
        using var store = StoreFixture.Create();
        var configuration = Config("true", store.Root, store.Installation.ToString("D"));
        var materialBefore = store.MaterialBytes();
        var listingBefore = store.Listing();

        using (new FileStream(store.RingPath, FileMode.Open, FileAccess.Read, FileShare.None))
        {
            var error = Assert.Throws<MfaHostCompositionException>(() =>
                MfaWindowsHostComposition.Compose(MfaHostMode.Enabled, configuration, Identity(), isWindows: true));
            Assert.Equal("mfa_keystore_unreadable", error.Code);
        }

        Assert.True(CryptographicOperations.FixedTimeEquals(materialBefore, store.MaterialBytes()), "cambió el material del almacén");
        Assert.Equal(listingBefore, store.Listing());
    }

    // MFA-L2I-01: un archivo de clave retenido en exclusiva durante la comprobación también es E/S no clasificable.
    [Fact]
    public void KeyFileHeldExclusivelyIsRefusedAsUnreadableWithoutChangingTheStore()
    {
        using var store = StoreFixture.Create();
        var configuration = Config("true", store.Root, store.Installation.ToString("D"));
        var materialBefore = store.MaterialBytes();
        var listingBefore = store.Listing();

        using (new FileStream(store.KeyFile(ActiveVersion), FileMode.Open, FileAccess.Read, FileShare.None))
        {
            var error = Assert.Throws<MfaHostCompositionException>(() =>
                MfaWindowsHostComposition.Compose(MfaHostMode.Enabled, configuration, Identity(), isWindows: true));
            Assert.Equal("mfa_keystore_unreadable", error.Code);
        }

        Assert.True(CryptographicOperations.FixedTimeEquals(materialBefore, store.MaterialBytes()), "cambió el material del almacén");
        Assert.Equal(listingBefore, store.Listing());
    }

    [Fact]
    public void ReaderThatIsAlsoTrustedIsRefused()
    {
        using var store = StoreFixture.Create();
        var configuration = Config("true", store.Root, store.Installation.ToString("D"));
        var identity = new TestIdentity(LocalSystemSid, [LocalSystemSid, AdministratorsSid]);

        var error = Assert.Throws<MfaHostCompositionException>(() =>
            MfaWindowsHostComposition.Compose(MfaHostMode.Enabled, configuration, identity, isWindows: true));

        Assert.Equal("mfa_keystore_reader_trusted", error.Code);
    }

    [Fact]
    public void EmptyTrustIsRefused()
    {
        using var store = StoreFixture.Create();
        var configuration = Config("true", store.Root, store.Installation.ToString("D"));
        var identity = new TestIdentity(UsersSid, []);

        var error = Assert.Throws<MfaHostCompositionException>(() =>
            MfaWindowsHostComposition.Compose(MfaHostMode.Enabled, configuration, identity, isWindows: true));

        Assert.Equal("mfa_keystore_trust_empty", error.Code);
    }

    [Fact]
    public void AbsentStoreIsRefusedWithoutCreatingAnything()
    {
        using var store = StoreFixture.Pending();
        var configuration = Config("true", store.Root, store.Installation.ToString("D"));

        var error = Assert.Throws<MfaHostCompositionException>(() =>
            MfaWindowsHostComposition.Compose(MfaHostMode.Enabled, configuration, Identity(), isWindows: true));

        Assert.Equal("mfa_keystore_store_missing", error.Code);
        Assert.False(Directory.Exists(store.Root), "un almacén ausente se regeneró");
    }

    [Fact]
    public void CorruptRingIsRefusedWithoutRegeneration()
    {
        using var store = StoreFixture.Create();
        File.WriteAllBytes(store.RingPath, Encoding.UTF8.GetBytes("{\"format\":"));
        var before = store.Listing();
        var configuration = Config("true", store.Root, store.Installation.ToString("D"));

        var error = Assert.Throws<MfaHostCompositionException>(() =>
            MfaWindowsHostComposition.Compose(MfaHostMode.Enabled, configuration, Identity(), isWindows: true));

        Assert.Equal("mfa_keystore_corrupt", error.Code);
        Assert.Equal(before, store.Listing());
    }

    [Fact]
    public void UnsafeKeysFolderAclIsRefusedWithoutRepair()
    {
        using var store = StoreFixture.Create();
        var security = new DirectorySecurity(store.KeysFolder, AccessControlSections.Access);
        security.AddAccessRule(new FileSystemAccessRule(EveryoneSid, FileSystemRights.Modify,
            InheritanceFlags.ContainerInherit | InheritanceFlags.ObjectInherit, PropagationFlags.None, AccessControlType.Allow));
        new DirectoryInfo(store.KeysFolder).SetAccessControl(security);
        var before = store.Listing();
        var configuration = Config("true", store.Root, store.Installation.ToString("D"));

        var error = Assert.Throws<MfaHostCompositionException>(() =>
            MfaWindowsHostComposition.Compose(MfaHostMode.Enabled, configuration, Identity(), isWindows: true));

        Assert.Equal("mfa_keystore_access_unsafe", error.Code);
        Assert.Equal(before, store.Listing());
    }

    [Theory]
    [InlineData(RetiredVersion)]
    [InlineData(ActiveVersion)]
    public void MissingVersionMaterialIsRefusedWithoutRegeneration(int version)
    {
        using var store = StoreFixture.Create();
        File.Delete(store.KeyFile(version));
        var before = store.Listing();
        var configuration = Config("true", store.Root, store.Installation.ToString("D"));

        var error = Assert.Throws<MfaHostCompositionException>(() =>
            MfaWindowsHostComposition.Compose(MfaHostMode.Enabled, configuration, Identity(), isWindows: true));

        Assert.Equal("mfa_keystore_version_missing", error.Code);
        Assert.Equal(before, store.Listing());
    }

    // Rama productiva: SID efectivo del proceso y confianza fija. El almacén de laboratorio es propiedad del usuario actual,
    // que no es de confianza fija: el rechazo es el esperado y prueba que la confianza no se amplía con el usuario actual.
    [Fact]
    public void ProductionBranchRefusesTheLabOwnedStoreBecauseTheOwnerIsNotFixedTrust()
    {
        using var store = StoreFixture.Create();
        var configuration = Config("true", store.Root, store.Installation.ToString("D"));
        var before = store.Listing();

        var error = Assert.Throws<MfaHostCompositionException>(() =>
            MfaWindowsHostComposition.Compose(MfaHostMode.Enabled, configuration, new ProcessMfaHostIdentity(), isWindows: true));

        Assert.Equal("mfa_keystore_access_unsafe", error.Code);
        Assert.Equal(before, store.Listing());
    }

    // Rama de prueba (seam interno): lector Usuarios y confianza Usuario de laboratorio, SYSTEM y Administradores.
    [Fact]
    public void ValidStoreComposesWithTheTestBranchAndReportsItsVersionsWithoutKeyMaterial()
    {
        using var store = StoreFixture.Create();
        var configuration = Config("true", store.Root, store.Installation.ToString("D"));
        var identity = Identity();
        var before = store.Listing();

        var composition = MfaWindowsHostComposition.Compose(MfaHostMode.Enabled, configuration, identity, isWindows: true);

        Assert.Equal($"mfa_keystore: habilitado; versiones=2; activa={ActiveVersion}; confianza=prueba-inyectada", composition.Diagnostic);
        Assert.DoesNotContain(Convert.ToHexString(store.KeyOf(ActiveVersion)), composition.Diagnostic, StringComparison.Ordinal);
        var active = composition.Provider.GetActiveKey();
        Assert.Equal(ActiveVersion, active.Version);
        Assert.True(CryptographicOperations.FixedTimeEquals(store.KeyOf(ActiveVersion), active.Key), "la clave activa no coincide");
        CryptographicOperations.ZeroMemory(active.Key);
        Assert.Equal(before, store.Listing());
        Assert.True(identity.ReaderReads >= 1);
    }

    // Resolución única: el preflight corre una vez, y el contenedor entrega el mismo proveedor a todas las resoluciones.
    [Fact]
    public void CompositionIsResolvedOnceThroughDependencyInjection()
    {
        using var store = StoreFixture.Create();
        var configuration = Config("true", store.Root, store.Installation.ToString("D"));
        var identity = Identity();
        var services = new ServiceCollection();
        services.AddSingleton<IMfaHostIdentity>(identity);
        services.AddSingleton(sp => MfaWindowsHostComposition.Compose(MfaHostMode.Enabled, configuration,
            sp.GetRequiredService<IMfaHostIdentity>(), isWindows: true));
        services.AddSingleton<IMfaKeyProvider>(sp => sp.GetRequiredService<MfaHostComposition>().Provider);
        using var container = services.BuildServiceProvider();

        var first = container.GetRequiredService<IMfaKeyProvider>();
        var second = container.GetRequiredService<IMfaKeyProvider>();
        var composition = container.GetRequiredService<MfaHostComposition>();

        Assert.Same(first, second);
        Assert.Same(first, composition.Provider);
        Assert.Equal(1, identity.ReaderReads);
    }

    // Un fallo de composición llega al contenedor como su excepción propia: Program lo convierte en arranque cerrado.
    [Fact]
    public void CompositionFailureReachesTheContainerAsItsOwnException()
    {
        using var store = StoreFixture.Pending();
        var configuration = Config("true", store.Root, store.Installation.ToString("D"));
        var identity = Identity();
        var services = new ServiceCollection();
        services.AddSingleton<IMfaHostIdentity>(identity);
        services.AddSingleton(sp => MfaWindowsHostComposition.Compose(MfaHostMode.Enabled, configuration,
            sp.GetRequiredService<IMfaHostIdentity>(), isWindows: true));
        services.AddSingleton<IMfaKeyProvider>(sp => sp.GetRequiredService<MfaHostComposition>().Provider);
        using var container = services.BuildServiceProvider();

        var error = Assert.Throws<MfaHostCompositionException>(() => container.GetRequiredService<IMfaKeyProvider>());

        Assert.Equal("mfa_keystore_store_missing", error.Code);
    }

    private static IConfiguration Config(string? enabled, string? root, string? installation)
    {
        var values = new Dictionary<string, string?>();
        if (enabled is not null) values["MfaKeyStore:Enabled"] = enabled;
        if (root is not null) values["MfaKeyStore:InstancesRoot"] = root;
        if (installation is not null) values["MfaKeyStore:InstallationId"] = installation;
        return new ConfigurationBuilder().AddInMemoryCollection(values).Build();
    }

    private static TestIdentity Identity() =>
        new(UsersSid, [WindowsIdentity.GetCurrent().User ?? throw new InvalidOperationException("sin SID"), LocalSystemSid, AdministratorsSid]);

    // Identidad de prueba: el lector y la confianza son los que declara la prueba. Su descripción lo deja en el diagnóstico.
    private sealed class TestIdentity(SecurityIdentifier reader, SecurityIdentifier[] trusted) : IMfaHostIdentity
    {
        public int ReaderReads { get; private set; }

        public SecurityIdentifier? ReaderSid
        {
            get
            {
                ReaderReads++;
                return reader;
            }
        }

        public IReadOnlyCollection<SecurityIdentifier> TrustedPrincipals => trusted;

        public string Description => "prueba-inyectada";
    }

    // Almacén TEMP sintético: versión 1 retirada y versión 7 activa, creado con el escritor aprobado. Pending no crea nada.
    private sealed class StoreFixture : IDisposable
    {
        private readonly Dictionary<int, byte[]> _keys = new();

        private StoreFixture(string folder, Guid installation)
        {
            Folder = folder;
            Installation = installation;
        }

        public string Folder { get; }

        public string Root => Path.Combine(Folder, "instancias");

        public Guid Installation { get; }

        public string KeysFolder => Path.Combine(Root, Installation.ToString("D"), WindowsMfaKeyProvider.KeysFolderName);

        public string RingPath => Path.Combine(KeysFolder, MfaKeyRing.RingFileName);

        public string KeyFile(int version) => Path.Combine(KeysFolder, MfaKeyRing.KeyFileName(version));

        public static StoreFixture Create()
        {
            var store = Pending();
            store._keys[RetiredVersion] = RandomNumberGenerator.GetBytes(MfaKeyRing.KeyBytes);
            store._keys[ActiveVersion] = RandomNumberGenerator.GetBytes(MfaKeyRing.KeyBytes);
            var ring = Encoding.UTF8.GetBytes(MfaKeyJson.Ring(store.Installation,
                MfaKeyJson.Entry(RetiredVersion, "retired", "2026-10-01T08:30:00Z") + "," +
                MfaKeyJson.Entry(ActiveVersion, "active", "2026-10-25T10:00:00Z")));
            var keys = new List<(int Version, byte[] Key)>
            {
                (RetiredVersion, store._keys[RetiredVersion]),
                (ActiveVersion, store._keys[ActiveVersion]),
            };
            WindowsMfaKeyStoreWriter.CreateStoreFromMaterial(store.Root, store.Installation, UsersSid,
                [WindowsIdentity.GetCurrent().User ?? throw new InvalidOperationException("sin SID"), LocalSystemSid, AdministratorsSid],
                ring, keys);
            return store;
        }

        // Carpeta propia de la prueba y raíz sin crear: el almacén no existe todavía.
        public static StoreFixture Pending()
        {
            var folder = Path.Combine(Path.GetTempPath(), "rackclick-mfa-l2i", Guid.NewGuid().ToString("N"));
            Directory.CreateDirectory(folder);
            return new StoreFixture(folder, Guid.NewGuid());
        }

        public byte[] KeyOf(int version) => _keys[version];

        // Anillo y archivos de clave tal como están en disco (blobs protegidos, nunca claves en claro).
        public byte[] MaterialBytes()
        {
            var bytes = new List<byte>();
            foreach (var path in new[] { RingPath, KeyFile(RetiredVersion), KeyFile(ActiveVersion) })
                bytes.AddRange(File.ReadAllBytes(path));
            return bytes.ToArray();
        }

        // Listado de todo lo que hay bajo la carpeta de la prueba, con tamaño, fecha y ACL: cualquier cambio lo modifica.
        public string[] Listing()
        {
            if (!Directory.Exists(Folder)) return [];
            var entries = new List<string>();
            foreach (var path in Directory.EnumerateFileSystemEntries(Folder, "*", SearchOption.AllDirectories))
            {
                if (Directory.Exists(path))
                {
                    var directory = new DirectoryInfo(path);
                    entries.Add(directory.FullName + "|" + directory.LastWriteTimeUtc.Ticks + "|" +
                        Convert.ToBase64String(directory.GetAccessControl(AccessControlSections.Access).GetSecurityDescriptorBinaryForm()));
                }
                else
                {
                    var file = new FileInfo(path);
                    entries.Add(file.FullName + "|" + file.LastWriteTimeUtc.Ticks + "|" + file.Length + "|" +
                        Convert.ToBase64String(file.GetAccessControl(AccessControlSections.Access).GetSecurityDescriptorBinaryForm()));
                }
            }
            entries.Sort(StringComparer.Ordinal);
            return entries.ToArray();
        }

        public void Dispose()
        {
            if (Directory.Exists(Folder)) Directory.Delete(Folder, true);
            var parent = Path.GetDirectoryName(Folder)!;
            if (Directory.Exists(parent) && !Directory.EnumerateFileSystemEntries(parent).Any())
                Directory.Delete(parent);
        }
    }
}
