using System.Globalization;
using System.Runtime.InteropServices;
using System.Runtime.Versioning;
using System.Security.Principal;

namespace RackClick.Server;

// Proveedor de solo lectura de la clave TOTP sobre el almacén de D2 v2: <raíz>\<instalación>\mfa-keys, protegido con DPAPI
// LocalMachine. La lectura y las comprobaciones de ACL, propietario, tipo y ruta están en WindowsMfaKeyFileReader: cada
// archivo se valida y se lee sobre un único identificador abierto. Nunca crea, repara, rota ni regenera archivos; cada
// fallo lanza MfaKeyRingException.
// Límite: la cuenta de servicio real no se prueba aquí; el SID lector lo fija quien construye el proveedor.
[SupportedOSPlatform("windows")]
public sealed class WindowsMfaKeyProvider : IMfaKeyProvider
{
    public const string KeysFolderName = "mfa-keys";
    private const int CryptProtectUiForbidden = 0x1;

    private static readonly SecurityIdentifier LocalSystemSid = new(WellKnownSidType.LocalSystemSid, null);
    private static readonly SecurityIdentifier AdministratorsSid = new(WellKnownSidType.BuiltinAdministratorsSid, null);

    private readonly Guid _installationId;
    private readonly string _instancesRoot;
    private readonly string _installationFolder;
    private readonly string _keysFolder;
    private readonly WindowsMfaKeyFileReader _reader;

    // trustedPrincipals: propietarios y principales con escritura legítima. Por defecto SYSTEM y Administradores.
    public WindowsMfaKeyProvider(string instancesRoot, Guid installationId, SecurityIdentifier readerSid,
        IEnumerable<SecurityIdentifier>? trustedPrincipals = null)
    {
        if (!Path.IsPathFullyQualified(instancesRoot))
            throw new MfaKeyRingException(MfaKeyRingErrorKind.InvalidPath, "mfa_key_store_path_invalid: la raíz del almacén debe ser absoluta");
        _instancesRoot = Path.GetFullPath(instancesRoot);
        _installationId = installationId;
        _installationFolder = Path.Combine(_instancesRoot, installationId.ToString("D"));
        _keysFolder = Path.Combine(_installationFolder, KeysFolderName);
        var trusted = trustedPrincipals ?? new[] { LocalSystemSid, AdministratorsSid };
        _reader = new WindowsMfaKeyFileReader(readerSid, trusted.Select(sid => sid.Value).ToHashSet(StringComparer.Ordinal));
    }

    public byte[] GetKey(int version)
    {
        var ring = LoadRing();
        ring.RequireEntry(version);
        return ReadKey(version);
    }

    // Versión activa y copia nueva de su clave, desde una sola lectura validada del anillo. El parser garantiza una única activa;
    // aquí se comprueba de nuevo para que el contrato no dependa sólo de esa garantía.
    public (int Version, byte[] Key) GetActiveKey()
    {
        var ring = LoadRing();
        var active = ring.Entries.Where(entry => entry.State == MfaKeyState.Active).ToArray();
        if (active.Length != 1)
            throw new MfaKeyRingException(MfaKeyRingErrorKind.InvalidFormat, "mfa_key_active_invalid: el anillo no tiene exactamente una versión activa");
        return (active[0].Version, ReadKey(active[0].Version));
    }

    private byte[] ReadKey(int version)
    {
        var keyPath = Path.Combine(_keysFolder, MfaKeyRing.KeyFileName(version));
        var keyFile = MfaKeyRing.ParseKeyFile(_reader.ReadValidated(keyPath, MfaKeyRing.MaxKeyFileBytes), _installationId, version);
        return Unprotect(keyFile.ProtectedKey, MfaKeyRing.EntropyFor(_installationId, version));
    }

    private MfaKeyRing LoadRing()
    {
        _reader.RequireSafeFolder(_instancesRoot);
        _reader.RequireSafeFolder(_installationFolder);
        _reader.RequireSafeFolder(_keysFolder);
        var ringPath = Path.Combine(_keysFolder, MfaKeyRing.RingFileName);
        return MfaKeyRing.Parse(_reader.ReadValidated(ringPath, MfaKeyRing.MaxRingFileBytes), _installationId);
    }

    private static byte[] Unprotect(byte[] protectedKey, byte[] entropy)
    {
        var input = Allocate(protectedKey);
        var extra = Allocate(entropy);
        try
        {
            var inputBlob = new DataBlob { cbData = protectedKey.Length, pbData = input };
            var entropyBlob = new DataBlob { cbData = entropy.Length, pbData = extra };
            if (!CryptUnprotectData(ref inputBlob, IntPtr.Zero, ref entropyBlob, IntPtr.Zero, IntPtr.Zero, CryptProtectUiForbidden, out var output))
                throw new MfaKeyRingException(MfaKeyRingErrorKind.Corrupt,
                    "mfa_key_unprotect_failed: DPAPI no abrió el blob (Win32 " + Marshal.GetLastWin32Error().ToString(CultureInfo.InvariantCulture) + ")");
            try
            {
                if (output.cbData != MfaKeyRing.KeyBytes)
                    throw new MfaKeyRingException(MfaKeyRingErrorKind.Corrupt, "mfa_key_length_invalid: la clave descifrada no mide 32 bytes");
                var key = new byte[output.cbData];
                Marshal.Copy(output.pbData, key, 0, key.Length);
                return key;
            }
            finally
            {
                ZeroAndFree(output);
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

    private static void ZeroAndFree(DataBlob blob)
    {
        if (blob.pbData == IntPtr.Zero) return;
        Marshal.Copy(new byte[blob.cbData], 0, blob.pbData, blob.cbData);
        LocalFree(blob.pbData);
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct DataBlob
    {
        public int cbData;
        public IntPtr pbData;
    }

    [DllImport("crypt32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool CryptUnprotectData(ref DataBlob dataIn, IntPtr description, ref DataBlob optionalEntropy,
        IntPtr reserved, IntPtr promptStruct, int flags, out DataBlob dataOut);

    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern IntPtr LocalFree(IntPtr memory);
}
