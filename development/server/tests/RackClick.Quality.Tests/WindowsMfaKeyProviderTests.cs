using System.ComponentModel;
using System.Diagnostics;
using System.Globalization;
using System.Runtime.InteropServices;
using System.Runtime.Versioning;
using System.Security.AccessControl;
using System.Security.Cryptography;
using System.Security.Principal;
using RackClick.Server;
using Xunit;

namespace RackClick.Quality.Tests;

// Proveedor MFA-L2 con DPAPI LocalMachine y ACL reales, en carpetas nuevas bajo %TEMP%. No crea cuentas ni servicios.
// El lector de pruebas es el grupo Usuarios: el SID de la cuenta de servicio real NO se prueba aquí. La sesión no
// está elevada, así que el propietario de los fixtures es el usuario de la prueba; sólo en estas pruebas se declara
// principal de confianza. Los fixtures escriben primero y aplican el DACL de D2 después (SYSTEM, Administradores y
// el operador con control total; lector con sólo lectura), así cada negativo falla por una única causa.
[SupportedOSPlatform("windows")]
public sealed class WindowsMfaKeyProviderTests
{
    private static readonly SecurityIdentifier UsersSid = new(WellKnownSidType.BuiltinUsersSid, null);
    private static readonly SecurityIdentifier LocalSystemSid = new(WellKnownSidType.LocalSystemSid, null);
    private static readonly SecurityIdentifier AdministratorsSid = new(WellKnownSidType.BuiltinAdministratorsSid, null);
    private static readonly SecurityIdentifier WorldSid = new(WellKnownSidType.WorldSid, null);

    [Fact]
    public void ValidStoreReturnsTheKeyForActiveAndRetiredVersionsWithoutWritingAnything()
    {
        using var store = new Store();
        var key1 = RandomNumberGenerator.GetBytes(MfaKeyRing.KeyBytes);
        var key2 = RandomNumberGenerator.GetBytes(MfaKeyRing.KeyBytes);
        store.WriteRing(MfaKeyJson.Ring(store.Installation, MfaKeyJson.Entry(1, "retired") + "," + MfaKeyJson.Entry(2, "active")));
        store.WriteKey(1, MfaKeyJson.Key(store.Installation, 1, Protect(key1, 1, store.Installation)));
        store.WriteKey(2, MfaKeyJson.Key(store.Installation, 2, Protect(key2, 2, store.Installation)));
        store.Seal();
        var before = store.Listing();
        var provider = store.Provider();

        Assert.Equal(key1, provider.GetKey(1));
        Assert.Equal(key2, provider.GetKey(2));
        Assert.Equal(before, store.Listing());
    }

    [Fact]
    public void UnknownVersionIsRejectedAndNothingIsCreated()
    {
        using var store = new Store();
        store.WriteRing(MfaKeyJson.Ring(store.Installation, MfaKeyJson.Entry(1, "active")));
        store.WriteKey(1, MfaKeyJson.Key(store.Installation, 1, Protect(RandomNumberGenerator.GetBytes(MfaKeyRing.KeyBytes), 1, store.Installation)));
        store.Seal();
        var before = store.Listing();

        var error = Assert.Throws<MfaKeyRingException>(() => store.Provider().GetKey(3));

        Assert.Equal(MfaKeyRingErrorKind.UnknownVersion, error.Kind);
        Assert.Equal(before, store.Listing());
    }

    [Fact]
    public void MissingKeyFileIsReportedAndNeverRegenerated()
    {
        using var store = new Store();
        store.WriteRing(MfaKeyJson.Ring(store.Installation, MfaKeyJson.Entry(1, "retired") + "," + MfaKeyJson.Entry(2, "active")));
        store.WriteKey(1, MfaKeyJson.Key(store.Installation, 1, Protect(RandomNumberGenerator.GetBytes(MfaKeyRing.KeyBytes), 1, store.Installation)));
        store.Seal();
        var provider = store.Provider();

        var error = Assert.Throws<MfaKeyRingException>(() => provider.GetKey(2));

        Assert.Equal(MfaKeyRingErrorKind.MissingFile, error.Kind);
        Assert.False(File.Exists(store.KeyFile(2)));
    }

    [Fact]
    public void MissingStoreIsReportedAndNotCreated()
    {
        using var store = new Store();
        var absent = Path.Combine(store.Root, "ausente");

        var error = Assert.Throws<MfaKeyRingException>(() => new WindowsMfaKeyProvider(absent, store.Installation, UsersSid).GetKey(1));

        Assert.Equal(MfaKeyRingErrorKind.MissingFile, error.Kind);
        Assert.False(Directory.Exists(absent));
    }

    [Fact]
    public void CorruptedBlobIsRejected()
    {
        using var store = new Store();
        var blob = TestDpapi.ProtectLocalMachine(RandomNumberGenerator.GetBytes(MfaKeyRing.KeyBytes), MfaKeyRing.EntropyFor(store.Installation, 1));
        blob[blob.Length / 2] ^= 0xFF;
        store.WriteRing(MfaKeyJson.Ring(store.Installation, MfaKeyJson.Entry(1, "active")));
        store.WriteKey(1, MfaKeyJson.Key(store.Installation, 1, Convert.ToBase64String(blob)));
        store.Seal();

        var error = Assert.Throws<MfaKeyRingException>(() => store.Provider().GetKey(1));

        Assert.Equal(MfaKeyRingErrorKind.Corrupt, error.Kind);
    }

    [Fact]
    public void KeyFileProtectedForAnotherVersionIsRejectedByEntropy()
    {
        using var store = new Store();
        store.WriteRing(MfaKeyJson.Ring(store.Installation, MfaKeyJson.Entry(1, "retired") + "," + MfaKeyJson.Entry(2, "active")));
        store.WriteKey(1, MfaKeyJson.Key(store.Installation, 1, Protect(RandomNumberGenerator.GetBytes(MfaKeyRing.KeyBytes), 1, store.Installation)));
        // Declara la versión 2, pero el blob se protegió con la entropía de la versión 1.
        store.WriteKey(2, MfaKeyJson.Key(store.Installation, 2, Protect(RandomNumberGenerator.GetBytes(MfaKeyRing.KeyBytes), 1, store.Installation)));
        store.Seal();

        var error = Assert.Throws<MfaKeyRingException>(() => store.Provider().GetKey(2));

        Assert.Equal(MfaKeyRingErrorKind.Corrupt, error.Kind);
    }

    [Fact]
    public void KeyFileDeclaringAnotherVersionIsCorruptBeforeDpapi()
    {
        using var store = new Store();
        store.WriteRing(MfaKeyJson.Ring(store.Installation, MfaKeyJson.Entry(1, "retired") + "," + MfaKeyJson.Entry(2, "active")));
        store.WriteKey(1, MfaKeyJson.Key(store.Installation, 1, Protect(RandomNumberGenerator.GetBytes(MfaKeyRing.KeyBytes), 1, store.Installation)));
        store.WriteKey(2, MfaKeyJson.Key(store.Installation, 1, Protect(RandomNumberGenerator.GetBytes(MfaKeyRing.KeyBytes), 1, store.Installation)));
        store.Seal();

        var error = Assert.Throws<MfaKeyRingException>(() => store.Provider().GetKey(2));

        Assert.Equal(MfaKeyRingErrorKind.Corrupt, error.Kind);
    }

    [Fact]
    public void RingOfAnotherInstallationIsIdentityMismatch()
    {
        using var store = new Store();
        store.WriteRing(MfaKeyJson.Ring(Guid.NewGuid(), MfaKeyJson.Entry(1, "active")));
        store.Seal();

        var error = Assert.Throws<MfaKeyRingException>(() => store.Provider().GetKey(1));

        Assert.Equal(MfaKeyRingErrorKind.IdentityMismatch, error.Kind);
    }

    [Fact]
    public void OversizedRingIsRejectedBeforeParsing()
    {
        using var store = new Store();
        store.WriteRing(new string(' ', MfaKeyRing.MaxRingFileBytes + 1));
        store.Seal();

        var error = Assert.Throws<MfaKeyRingException>(() => store.Provider().GetKey(1));

        Assert.Equal(MfaKeyRingErrorKind.FileTooLarge, error.Kind);
    }

    [Fact]
    public void UsersWriteRightOnKeyFileIsRejected()
    {
        using var store = new Store();
        StoreWithOneKey(store);
        store.Seal();
        store.Grant(store.KeyFile(1), FileSystemRights.WriteData);

        var error = Assert.Throws<MfaKeyRingException>(() => store.Provider().GetKey(1));

        Assert.Equal(MfaKeyRingErrorKind.UnsafeAccess, error.Kind);
    }

    [Fact]
    public void UsersModifyRightOnKeysFolderIsRejected()
    {
        using var store = new Store();
        StoreWithOneKey(store);
        store.Seal();
        store.Grant(store.KeysFolder, FileSystemRights.Modify);

        var error = Assert.Throws<MfaKeyRingException>(() => store.Provider().GetKey(1));

        Assert.Equal(MfaKeyRingErrorKind.UnsafeAccess, error.Kind);
    }

    [Fact]
    public void UsersCreateRightOnInstancesRootIsRejected()
    {
        using var store = new Store();
        StoreWithOneKey(store);
        store.Seal();
        store.Grant(store.InstancesRoot, FileSystemRights.CreateDirectories);

        var error = Assert.Throws<MfaKeyRingException>(() => store.Provider().GetKey(1));

        Assert.Equal(MfaKeyRingErrorKind.UnsafeAccess, error.Kind);
    }

    [Fact]
    public void OwnerOutsideTheTrustedPrincipalsIsRejected()
    {
        using var store = new Store();
        StoreWithOneKey(store);
        store.Seal();

        var error = Assert.Throws<MfaKeyRingException>(() =>
            store.Provider(trusted: [LocalSystemSid, AdministratorsSid]).GetKey(1));

        Assert.Equal(MfaKeyRingErrorKind.UnsafeAccess, error.Kind);
    }

    [Fact]
    public void ReaderThatOwnsTheStoreIsRejected()
    {
        using var store = new Store();
        StoreWithOneKey(store);
        store.Seal();

        var error = Assert.Throws<MfaKeyRingException>(() => store.Provider(reader: store.Me).GetKey(1));

        Assert.Equal(MfaKeyRingErrorKind.UnsafeAccess, error.Kind);
    }

    [Fact]
    public void ReaderWithoutExplicitReadIsRejected()
    {
        using var store = new Store();
        StoreWithOneKey(store);
        store.Seal(grantReader: false);

        var error = Assert.Throws<MfaKeyRingException>(() => store.Provider().GetKey(1));

        Assert.Equal(MfaKeyRingErrorKind.UnsafeAccess, error.Kind);
    }

    // Lectura para un tercero (Everyone) sobre la clave o sobre el anillo: el proveedor debe rechazarla.
    [Theory]
    [InlineData("key")]
    [InlineData("ring")]
    public void ThirdPartyReadMustBeRejected(string target)
    {
        using var store = new Store();
        StoreWithOneKey(store);
        store.Seal();
        // Control: con el fixture válido el proveedor devuelve la clave antes de añadir la concesión indebida.
        Assert.Equal(MfaKeyRing.KeyBytes, store.Provider().GetKey(1).Length);
        var path = target == "key" ? store.KeyFile(1) : store.RingFile;
        store.Grant(path, FileSystemRights.ReadData, WorldSid);
        Assert.True(Persisted(store.Dacl(path), AceType.AccessAllowed, WorldSid, (int)FileSystemRights.ReadData));

        var error = Assert.Throws<MfaKeyRingException>(() => store.Provider().GetKey(1));

        Assert.Equal(MfaKeyRingErrorKind.UnsafeAccess, error.Kind);
    }

    // Concesión condicional (XA) de escritura: el proveedor no puede ignorarla en silencio.
    [Fact]
    public void ConditionalWriteAceMustNotBeSilentlyIgnored()
    {
        using var store = new Store();
        StoreWithOneKey(store);
        store.Seal();
        Assert.Equal(MfaKeyRing.KeyBytes, store.Provider().GetKey(1).Length);
        store.AddConditionalWrite(store.KeyFile(1));
        Assert.True(Persisted(store.Dacl(store.KeyFile(1)), AceType.AccessAllowedCallback, WorldSid, (int)FileSystemRights.WriteData));

        var error = Assert.Throws<MfaKeyRingException>(() => store.Provider().GetKey(1));

        Assert.Equal(MfaKeyRingErrorKind.UnsafeAccess, error.Kind);
    }

    // DACL nulo real: se aplica con SetNamedSecurityInfo (pDacl = NULL) y se relee del disco antes de llamar al proveedor.
    [Theory]
    [InlineData("key")]
    [InlineData("ring")]
    public void RealNullDaclIsRejectedAfterReadingItBack(string target)
    {
        using var store = new Store();
        StoreWithOneKey(store);
        store.Seal();
        Assert.Equal(MfaKeyRing.KeyBytes, store.Provider().GetKey(1).Length);
        var path = target == "key" ? store.KeyFile(1) : store.RingFile;
        TestAcl.SetNullDacl(path);
        // Relectura binaria: DACL nulo real (no un Allow para Everyone equivalente).
        Assert.Null(store.Descriptor(path).DiscretionaryAcl);

        var error = Assert.Throws<MfaKeyRingException>(() => store.Provider().GetKey(1));

        Assert.Equal(MfaKeyRingErrorKind.UnsafeAccess, error.Kind);
        Assert.Contains("DACL nulo", error.Message, StringComparison.Ordinal);
    }

    // Redirección de un ancestro por encima de la raíz del almacén mediante un enlace de directorio. Las comprobaciones de
    // la cadena pasan sobre el destino, pero la ruta final del archivo abierto no coincide con la ruta anclada: se rechaza.
    [Fact]
    public void AncestorRedirectionOutsideTheChainIsRejected()
    {
        using var store = new Store();
        StoreWithOneKey(store);
        store.Seal();
        Assert.Equal(MfaKeyRing.KeyBytes, store.Provider().GetKey(1).Length);
        var destination = Path.Combine(store.Root, "destino");
        Directory.CreateDirectory(destination);
        Directory.Move(store.InstancesRoot, Path.Combine(destination, "Instances"));
        var link = Path.Combine(store.Root, "enlace");
        CreateJunction(link, destination);
        try
        {
            var provider = new WindowsMfaKeyProvider(Path.Combine(link, "Instances"), store.Installation, UsersSid, store.TestTrusted);

            var error = Assert.Throws<MfaKeyRingException>(() => provider.GetKey(1));

            Assert.Equal(MfaKeyRingErrorKind.UnsafePath, error.Kind);
            Assert.StartsWith("mfa_key_store_path_redirected", error.Message, StringComparison.Ordinal);
        }
        finally
        {
            // Quitar sólo el enlace, nunca su destino.
            Directory.Delete(link);
        }
    }

    // Ensayo determinista de la ventana comprobar/leer: tras validar y antes de leer, sustituir, borrar, renombrar o redirigir
    // el archivo debe bloquearse. Los bytes devueltos son los del objeto validado, nunca otros.
    [Fact]
    public void SubstitutionAndRedirectionInsideTheWindowAreBlocked()
    {
        using var store = new Store();
        StoreWithOneKey(store);
        store.Seal();
        var keyPath = store.KeyFile(1);
        var validated = File.ReadAllBytes(keyPath);
        var reader = new WindowsMfaKeyFileReader(UsersSid, store.TestTrusted.Select(sid => sid.Value).ToHashSet(StringComparer.Ordinal));
        var outcomes = new Dictionary<string, string>(StringComparer.Ordinal);

        var bytes = reader.ReadValidated(keyPath, MfaKeyRing.MaxKeyFileBytes, beforeRead: () =>
        {
            outcomes["borrar"] = Attempt(() => File.Delete(keyPath));
            outcomes["renombrar"] = Attempt(() => File.Move(keyPath, keyPath + ".otro"));
            outcomes["sustituir"] = Attempt(() => File.WriteAllBytes(keyPath, new byte[] { 1, 2, 3 }));
            outcomes["redirigir"] = Attempt(() => Directory.Move(store.KeysFolder, store.KeysFolder + "-movida"));
        });

        Assert.Equal(validated, bytes);
        Assert.Equal("bloqueado", outcomes["borrar"]);
        Assert.Equal("bloqueado", outcomes["renombrar"]);
        Assert.Equal("bloqueado", outcomes["sustituir"]);
        // Mover la carpeta puede bloquearse o completarse; en ambos casos el archivo validado no cambia.
        Assert.True(outcomes["redirigir"] is "bloqueado" or "permitido");
    }

    [Fact]
    public void ReparsePointInTheKeysPathIsRejected()
    {
        using var store = new Store();
        var alternative = Path.Combine(store.Root, "alterno");
        Directory.CreateDirectory(alternative);
        Directory.Delete(store.KeysFolder);
        CreateJunction(store.KeysFolder, alternative);
        try
        {
            store.Seal();

            var error = Assert.Throws<MfaKeyRingException>(() => store.Provider().GetKey(1));

            Assert.Equal(MfaKeyRingErrorKind.UnsafePath, error.Kind);
        }
        finally
        {
            // Quitar sólo el enlace: borrar de forma recursiva podría recorrer el destino.
            Directory.Delete(store.KeysFolder);
        }
    }

    [Fact]
    public void RelativeRootIsRejectedBeforeAnyAccess()
    {
        var error = Assert.Throws<MfaKeyRingException>(() =>
            new WindowsMfaKeyProvider("relativa\\Instances", Guid.NewGuid(), UsersSid));

        Assert.Equal(MfaKeyRingErrorKind.InvalidPath, error.Kind);
    }

    // Resultado de un intento de manipulación dentro de la ventana: "bloqueado" cuando el sistema lo impide.
    private static string Attempt(Action action)
    {
        try
        {
            action();
            return "permitido";
        }
        catch (IOException)
        {
            return "bloqueado";
        }
        catch (UnauthorizedAccessException)
        {
            return "bloqueado";
        }
    }

    // Comprueba el ACE en el descriptor real releído del disco, no sólo en lo que se intentó aplicar.
    private static bool Persisted(RawAcl dacl, AceType type, SecurityIdentifier sid, int mask) =>
        dacl.OfType<QualifiedAce>().Any(ace => ace.AceType == type && ace.SecurityIdentifier == sid && (ace.AccessMask & mask) != 0);

    // Lo mínimo para un GetKey válido: ring con la versión 1 activa y su clave protegida.
    private static void StoreWithOneKey(Store store)
    {
        store.WriteRing(MfaKeyJson.Ring(store.Installation, MfaKeyJson.Entry(1, "active")));
        store.WriteKey(1, MfaKeyJson.Key(store.Installation, 1, Protect(RandomNumberGenerator.GetBytes(MfaKeyRing.KeyBytes), 1, store.Installation)));
    }

    private static string Protect(byte[] key, int version, Guid installation) =>
        Convert.ToBase64String(TestDpapi.ProtectLocalMachine(key, MfaKeyRing.EntropyFor(installation, version)));

    private static void CreateJunction(string link, string target)
    {
        using var process = Process.Start(new ProcessStartInfo("cmd.exe", "/d /c mklink /J \"" + link + "\" \"" + target + "\"")
        {
            UseShellExecute = false,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            CreateNoWindow = true,
        })!;
        var output = process.StandardOutput.ReadToEnd() + process.StandardError.ReadToEnd();
        process.WaitForExit();
        Assert.True(process.ExitCode == 0, "mklink /J falló: " + output);
    }

    // Almacén de prueba: raíz nueva, cadena de carpetas y archivos con DACL de D2 aplicado en Seal().
    private sealed class Store : IDisposable
    {
        public Store()
        {
            Root = Path.Combine(Path.GetTempPath(), "rackclick-mfa-l2", Guid.NewGuid().ToString("N"));
            InstancesRoot = Path.Combine(Root, "Instances");
            Installation = Guid.NewGuid();
            InstallationFolder = Path.Combine(InstancesRoot, Installation.ToString("D"));
            KeysFolder = Path.Combine(InstallationFolder, WindowsMfaKeyProvider.KeysFolderName);
            Directory.CreateDirectory(KeysFolder);
            Me = WindowsIdentity.GetCurrent().User ?? throw new InvalidOperationException("sin SID de usuario");
        }

        public string Root { get; }
        public string InstancesRoot { get; }
        public string InstallationFolder { get; }
        public string KeysFolder { get; }
        public Guid Installation { get; }
        public SecurityIdentifier Me { get; }

        public SecurityIdentifier[] TestTrusted => [LocalSystemSid, AdministratorsSid, Me];

        public string KeyFile(int version) => Path.Combine(KeysFolder, MfaKeyRing.KeyFileName(version));

        public string RingFile => Path.Combine(KeysFolder, MfaKeyRing.RingFileName);

        public void WriteRing(string json) => File.WriteAllBytes(RingFile, MfaKeyJson.Bytes(json));

        public void WriteKey(int version, string json) => File.WriteAllBytes(KeyFile(version), MfaKeyJson.Bytes(json));

        public void Seal(bool grantReader = true)
        {
            ProtectFolder(InstancesRoot, grantReader);
            ProtectFolder(InstallationFolder, grantReader);
            ProtectFolder(KeysFolder, grantReader);
            foreach (var file in Directory.GetFiles(KeysFolder)) ProtectFile(file, grantReader);
        }

        // Añade un ACE permitido para un principal (por defecto, el grupo Usuarios) sobre un archivo o carpeta.
        public void Grant(string path, FileSystemRights rights, SecurityIdentifier? sid = null)
        {
            var principal = sid ?? UsersSid;
            if (Directory.Exists(path))
            {
                var folder = new DirectoryInfo(path);
                var security = folder.GetAccessControl(AccessControlSections.Access);
                security.AddAccessRule(new FileSystemAccessRule(principal, rights,
                    InheritanceFlags.ContainerInherit | InheritanceFlags.ObjectInherit, PropagationFlags.None, AccessControlType.Allow));
                folder.SetAccessControl(security);
            }
            else
            {
                var file = new FileInfo(path);
                var security = file.GetAccessControl(AccessControlSections.Access);
                security.AddAccessRule(new FileSystemAccessRule(principal, rights, InheritanceFlags.None, PropagationFlags.None, AccessControlType.Allow));
                file.SetAccessControl(security);
            }
        }

        // Concesión condicional (XA) de escritura para Everyone, aplicada al descriptor real del archivo.
        public void AddConditionalWrite(string path)
        {
            var file = new FileInfo(path);
            var security = file.GetAccessControl(AccessControlSections.Access);
            var sddl = security.GetSecurityDescriptorSddlForm(AccessControlSections.Access) + "(XA;;FW;;;WD;(Member_of {SID(S-1-1-0)}))";
            security.SetSecurityDescriptorSddlForm(sddl, AccessControlSections.Access);
            file.SetAccessControl(security);
        }

        // Descriptor releído del disco en forma binaria. La forma SDDL de un DACL nulo llega vacía, así que no se usa para leer.
        public RawSecurityDescriptor Descriptor(string path)
        {
            FileSystemSecurity security = Directory.Exists(path)
                ? new DirectoryInfo(path).GetAccessControl(AccessControlSections.Access)
                : new FileInfo(path).GetAccessControl(AccessControlSections.Access);
            return new RawSecurityDescriptor(security.GetSecurityDescriptorBinaryForm(), 0);
        }

        public RawAcl Dacl(string path) => Descriptor(path).DiscretionaryAcl!;

        public WindowsMfaKeyProvider Provider(SecurityIdentifier? reader = null, SecurityIdentifier[]? trusted = null) =>
            new(InstancesRoot, Installation, reader ?? UsersSid, trusted ?? TestTrusted);

        // Listado con tamaño y fecha de modificación: cualquier escritura o creación del proveedor cambia la lista.
        public string[] Listing()
        {
            var entries = new List<string>();
            foreach (var path in Directory.EnumerateFileSystemEntries(Root, "*", SearchOption.AllDirectories))
            {
                FileSystemInfo item = Directory.Exists(path) ? new DirectoryInfo(path) : new FileInfo(path);
                var size = item is FileInfo file ? file.Length : -1;
                entries.Add(item.FullName + "|" + item.LastWriteTimeUtc.Ticks.ToString(CultureInfo.InvariantCulture) + "|" +
                            size.ToString(CultureInfo.InvariantCulture));
            }
            entries.Sort(StringComparer.Ordinal);
            return entries.ToArray();
        }

        public void Dispose() => Directory.Delete(Root, true);

        private void ProtectFolder(string path, bool grantReader)
        {
            const InheritanceFlags inherit = InheritanceFlags.ContainerInherit | InheritanceFlags.ObjectInherit;
            var security = new DirectorySecurity();
            security.SetAccessRuleProtection(true, false);
            foreach (var sid in TestTrusted)
                security.AddAccessRule(new FileSystemAccessRule(sid, FileSystemRights.FullControl, inherit, PropagationFlags.None, AccessControlType.Allow));
            if (grantReader)
                security.AddAccessRule(new FileSystemAccessRule(UsersSid, FileSystemRights.ReadAndExecute, inherit, PropagationFlags.None, AccessControlType.Allow));
            new DirectoryInfo(path).SetAccessControl(security);
        }

        private void ProtectFile(string path, bool grantReader)
        {
            var security = new FileSecurity();
            security.SetAccessRuleProtection(true, false);
            foreach (var sid in TestTrusted)
                security.AddAccessRule(new FileSystemAccessRule(sid, FileSystemRights.FullControl, InheritanceFlags.None, PropagationFlags.None, AccessControlType.Allow));
            if (grantReader)
                security.AddAccessRule(new FileSystemAccessRule(UsersSid, FileSystemRights.ReadAndExecute, InheritanceFlags.None, PropagationFlags.None, AccessControlType.Allow));
            new FileInfo(path).SetAccessControl(security);
        }
    }

    // Operación de ACL nativa sólo para fabricar el fixture de DACL nulo.
    private static class TestAcl
    {
        private const int SeFileObject = 1;
        private const uint DaclSecurityInformation = 0x4;

        public static void SetNullDacl(string path)
        {
            var error = SetNamedSecurityInfo(path, SeFileObject, DaclSecurityInformation, IntPtr.Zero, IntPtr.Zero, IntPtr.Zero, IntPtr.Zero);
            if (error != 0) throw new Win32Exception((int)error);
        }

        [DllImport("advapi32.dll", CharSet = CharSet.Unicode, SetLastError = false)]
        private static extern uint SetNamedSecurityInfo(string objectName, int objectType, uint securityInfo,
            IntPtr owner, IntPtr group, IntPtr dacl, IntPtr sacl);
    }

    // Protección DPAPI LocalMachine sólo para fabricar fixtures. Es una copia independiente del P/Invoke del producto:
    // así la prueba no comparte código con lo que verifica.
    private static class TestDpapi
    {
        private const int UiForbidden = 0x1;
        private const int LocalMachine = 0x4;

        public static byte[] ProtectLocalMachine(byte[] plain, byte[] entropy)
        {
            var input = Allocate(plain);
            var extra = Allocate(entropy);
            try
            {
                var inputBlob = new Blob { cbData = plain.Length, pbData = input };
                var entropyBlob = new Blob { cbData = entropy.Length, pbData = extra };
                if (!CryptProtectData(ref inputBlob, null, ref entropyBlob, IntPtr.Zero, IntPtr.Zero, UiForbidden | LocalMachine, out var output))
                    throw new Win32Exception(Marshal.GetLastWin32Error());
                try
                {
                    var result = new byte[output.cbData];
                    Marshal.Copy(output.pbData, result, 0, result.Length);
                    return result;
                }
                finally
                {
                    LocalFree(output.pbData);
                }
            }
            finally
            {
                Marshal.FreeHGlobal(input);
                Marshal.FreeHGlobal(extra);
            }
        }

        private static IntPtr Allocate(byte[] data)
        {
            var handle = Marshal.AllocHGlobal(data.Length);
            Marshal.Copy(data, 0, handle, data.Length);
            return handle;
        }

        [StructLayout(LayoutKind.Sequential)]
        private struct Blob
        {
            public int cbData;
            public IntPtr pbData;
        }

        [DllImport("crypt32.dll", SetLastError = true, CharSet = CharSet.Unicode)]
        [return: MarshalAs(UnmanagedType.Bool)]
        private static extern bool CryptProtectData(ref Blob dataIn, [MarshalAs(UnmanagedType.LPWStr)] string? description,
            ref Blob optionalEntropy, IntPtr reserved, IntPtr promptStruct, int flags, out Blob dataOut);

        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern IntPtr LocalFree(IntPtr memory);
    }
}
