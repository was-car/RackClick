using System.Globalization;
using System.Runtime.InteropServices;
using System.Runtime.Versioning;
using System.Security.AccessControl;
using System.Security.Cryptography;
using System.Security.Principal;
using System.Text.Json;

namespace RackClick.Server;

// Creación inicial explícita de un almacén MFA (MFA-L2c): ring con la versión 1 activa y una clave de 32 bytes protegida con
// DPAPI LocalMachine, con entropía de instalación y versión. No se llama desde el arranque, nunca reemplaza un destino
// existente y nunca genera una clave para cargar un almacén ausente o corrupto. Prepara en una carpeta de staging dentro de la
// instalación, valida con las mismas reglas del lector aprobado y publica con un renombrado que no reemplaza nada.
// Investigación previa: evidence/s1-20261026/mfa-l2c-claude/INVESTIGACION-PREVIA.md.
// Límites: el renombrado no tiene atomicidad documentada; el creador debe ser un principal de confianza; si el proceso se
// corta tras preparar el staging, éste queda y no se limpia aquí.
[SupportedOSPlatform("windows")]
internal static class WindowsMfaKeyStoreWriter
{
    private const string StagingPrefix = "mfa-keys.preparando-";
    private const string CreatedAtFormat = "yyyy-MM-dd'T'HH:mm:ss'Z'";
    private const int InitialVersion = 1;
    private const int CryptProtectUiForbidden = 0x1;
    private const int CryptProtectLocalMachine = 0x4;

    // Crea el almacén de una instalación. Lanza MfaKeyStoreCreationException sin dejar restos si no puede publicar.
    // beforePublish: punto de ensayo entre la validación y el renombrado; en producción no se usa.
    public static void CreateInitialStore(string instancesRoot, Guid installationId, SecurityIdentifier readerSid,
        IReadOnlyCollection<SecurityIdentifier> trustedPrincipals, Action? beforePublish = null)
    {
        if (!Path.IsPathFullyQualified(instancesRoot)) throw Invalid("la raíz debe ser absoluta");
        var root = Path.GetFullPath(instancesRoot);
        var parent = Path.GetDirectoryName(root);
        if (parent is null || !Directory.Exists(parent)) throw Invalid("la carpeta padre de la raíz debe existir");
        var trusted = trustedPrincipals.ToArray();
        if (trusted.Length == 0) throw Invalid("sin principales de confianza");
        if (trusted.Contains(readerSid)) throw Invalid("el lector no puede ser principal de confianza");

        var reader = new WindowsMfaKeyFileReader(readerSid, trusted.Select(sid => sid.Value).ToHashSet(StringComparer.Ordinal));
        var installation = Path.Combine(root, installationId.ToString("D"));
        var keys = Path.Combine(installation, WindowsMfaKeyProvider.KeysFolderName);

        // Antes de tocar nada: un destino existente, sea lo que sea, se conserva tal cual.
        if (Exists(keys))
            throw Creation(MfaKeyStoreCreationErrorKind.AlreadyExists, "mfa_key_store_exists: el destino ya existe; no se modifica");
        RequireExistingAncestor(root, reader);
        RequireExistingAncestor(installation, reader);

        var created = new List<string>();
        string? staging = null;
        try
        {
            CreateOwnFolder(root, trusted, readerSid, created);
            CreateOwnFolder(installation, trusted, readerSid, created);
            staging = Path.Combine(installation, StagingPrefix + Guid.NewGuid().ToString("N"));
            Directory.CreateDirectory(staging);
            ProtectFolder(staging, trusted, readerSid);
            StageStore(installationId, staging, trusted, readerSid, reader);
            Publish(staging, keys, beforePublish);
            staging = null;
        }
        catch (MfaKeyStoreCreationException)
        {
            Discard(staging, created);
            throw;
        }
        catch (MfaKeyRingException ex)
        {
            Discard(staging, created);
            throw Creation(MfaKeyStoreCreationErrorKind.ValidationFailed, ex.Message, ex);
        }
        catch (Exception ex) when (ex is IOException or UnauthorizedAccessException)
        {
            Discard(staging, created);
            throw Creation(MfaKeyStoreCreationErrorKind.CreationFailed, "mfa_key_store_write_failed: no se pudo preparar el almacén", ex);
        }
        catch (Exception)
        {
            Discard(staging, created);
            throw;
        }
    }

    // Prepara los archivos en el staging: clave generada, protegida y verificada antes de escribir nada.
    private static void StageStore(Guid installationId, string staging, SecurityIdentifier[] trusted, SecurityIdentifier readerSid,
        WindowsMfaKeyFileReader reader)
    {
        var key = RandomNumberGenerator.GetBytes(MfaKeyRing.KeyBytes);
        try
        {
            var entropy = MfaKeyRing.EntropyFor(installationId, InitialVersion);
            var blob = Protect(key, entropy);
            var recovered = Unprotect(blob, entropy);
            try
            {
                if (!CryptographicOperations.FixedTimeEquals(recovered, key))
                    throw Creation(MfaKeyStoreCreationErrorKind.ValidationFailed, "mfa_key_store_dpapi_roundtrip: la comprobación DPAPI no devuelve la clave");
            }
            finally
            {
                CryptographicOperations.ZeroMemory(recovered);
            }

            var ring = RingBytes(installationId, DateTimeOffset.UtcNow);
            var keyFile = KeyFileBytes(installationId, blob);
            MfaKeyRing.Parse(ring, installationId);
            MfaKeyRing.ParseKeyFile(keyFile, installationId, InitialVersion);

            var ringPath = Path.Combine(staging, MfaKeyRing.RingFileName);
            var keyPath = Path.Combine(staging, MfaKeyRing.KeyFileName(InitialVersion));
            File.WriteAllBytes(ringPath, ring);
            File.WriteAllBytes(keyPath, keyFile);
            ProtectFile(ringPath, trusted, readerSid);
            ProtectFile(keyPath, trusted, readerSid);

            // Mismas reglas que el lector aprobado: carpeta, propietario, DACL e identidad de cada archivo.
            reader.RequireSafeFolder(staging);
            reader.ReadValidated(ringPath, MfaKeyRing.MaxRingFileBytes);
            reader.ReadValidated(keyPath, MfaKeyRing.MaxKeyFileBytes);
        }
        finally
        {
            CryptographicOperations.ZeroMemory(key);
        }
    }

    // Publicación: Directory.Move falla si el destino existe; no reemplaza nada.
    private static void Publish(string staging, string keys, Action? beforePublish)
    {
        try
        {
            beforePublish?.Invoke();
            Directory.Move(staging, keys);
        }
        catch (IOException ex) when (Exists(keys))
        {
            throw Creation(MfaKeyStoreCreationErrorKind.AlreadyExists,
                "mfa_key_store_exists: el destino apareció durante la publicación; no se reemplaza", ex);
        }
        catch (Exception ex) when (ex is IOException or UnauthorizedAccessException)
        {
            throw Creation(MfaKeyStoreCreationErrorKind.PublishFailed, "mfa_key_store_publish_failed: no se pudo publicar el almacén", ex);
        }
    }

    // Un ancestro existente debe cumplir el mismo DACL que el lector exige. No se corrige lo ajeno.
    private static void RequireExistingAncestor(string path, WindowsMfaKeyFileReader reader)
    {
        if (File.Exists(path)) throw Invalid("un ancestro existe como archivo: " + Path.GetFileName(path));
        if (!Directory.Exists(path)) return;
        try
        {
            reader.RequireSafeFolder(path);
        }
        catch (MfaKeyRingException ex)
        {
            throw Creation(MfaKeyStoreCreationErrorKind.ValidationFailed, "mfa_key_store_ancestor_unsafe: " + ex.Message, ex);
        }
    }

    // Sólo crea carpetas que no existían, y las marca para retirarlas si la llamada falla.
    private static void CreateOwnFolder(string path, SecurityIdentifier[] trusted, SecurityIdentifier readerSid, List<string> created)
    {
        if (Directory.Exists(path)) return;
        Directory.CreateDirectory(path);
        created.Add(path);
        ProtectFolder(path, trusted, readerSid);
    }

    // Retira el staging y las carpetas creadas por esta llamada. Nunca toca contenido ajeno: las carpetas creadas se quitan
    // sólo si están vacías.
    private static void Discard(string? staging, List<string> created)
    {
        if (staging is not null) RemoveQuietly(staging, recursive: true);
        for (var i = created.Count - 1; i >= 0; i--) RemoveQuietly(created[i], recursive: false);
    }

    private static void RemoveQuietly(string path, bool recursive)
    {
        try
        {
            if (Directory.Exists(path)) Directory.Delete(path, recursive);
        }
        catch (IOException)
        {
            // Lo que no se puede retirar se deja; la llamada ya devuelve su fallo original.
        }
        catch (UnauthorizedAccessException)
        {
            // Igual que arriba: no se oculta el fallo principal por un borrado fallido.
        }
    }

    private static void ProtectFolder(string path, SecurityIdentifier[] trusted, SecurityIdentifier readerSid)
    {
        const InheritanceFlags inherit = InheritanceFlags.ContainerInherit | InheritanceFlags.ObjectInherit;
        var security = new DirectorySecurity();
        security.SetAccessRuleProtection(true, false);
        foreach (var sid in trusted)
            security.AddAccessRule(new FileSystemAccessRule(sid, FileSystemRights.FullControl, inherit, PropagationFlags.None, AccessControlType.Allow));
        security.AddAccessRule(new FileSystemAccessRule(readerSid, FileSystemRights.ReadAndExecute, inherit, PropagationFlags.None, AccessControlType.Allow));
        new DirectoryInfo(path).SetAccessControl(security);
    }

    private static void ProtectFile(string path, SecurityIdentifier[] trusted, SecurityIdentifier readerSid)
    {
        var security = new FileSecurity();
        security.SetAccessRuleProtection(true, false);
        foreach (var sid in trusted)
            security.AddAccessRule(new FileSystemAccessRule(sid, FileSystemRights.FullControl, InheritanceFlags.None, PropagationFlags.None, AccessControlType.Allow));
        security.AddAccessRule(new FileSystemAccessRule(readerSid, FileSystemRights.ReadAndExecute, InheritanceFlags.None, PropagationFlags.None, AccessControlType.Allow));
        new FileInfo(path).SetAccessControl(security);
    }

    private static byte[] RingBytes(Guid installationId, DateTimeOffset createdAt)
    {
        using var stream = new MemoryStream();
        using (var writer = new Utf8JsonWriter(stream))
        {
            writer.WriteStartObject();
            writer.WriteString("format", MfaKeyRing.RingFormat);
            writer.WriteNumber("formatVersion", MfaKeyRing.FormatVersion);
            writer.WriteString("installationId", installationId.ToString("D"));
            writer.WriteStartArray("versions");
            writer.WriteStartObject();
            writer.WriteNumber("version", InitialVersion);
            writer.WriteString("state", "active");
            writer.WriteString("createdAtUtc", createdAt.ToUniversalTime().ToString(CreatedAtFormat, CultureInfo.InvariantCulture));
            writer.WriteEndObject();
            writer.WriteEndArray();
            writer.WriteEndObject();
        }
        return stream.ToArray();
    }

    private static byte[] KeyFileBytes(Guid installationId, byte[] protectedKey)
    {
        using var stream = new MemoryStream();
        using (var writer = new Utf8JsonWriter(stream))
        {
            writer.WriteStartObject();
            writer.WriteString("format", MfaKeyRing.KeyFileFormat);
            writer.WriteNumber("formatVersion", MfaKeyRing.FormatVersion);
            writer.WriteString("installationId", installationId.ToString("D"));
            writer.WriteNumber("keyVersion", InitialVersion);
            writer.WriteString("protection", MfaKeyRing.ProtectionName);
            writer.WriteString("protectedKey", Convert.ToBase64String(protectedKey));
            writer.WriteEndObject();
        }
        return stream.ToArray();
    }

    // DPAPI LocalMachine con entropía de instalación y versión. Copia nativa propia: el proveedor y el lector no se tocan.
    private static byte[] Protect(byte[] plain, byte[] entropy)
    {
        var input = Allocate(plain);
        var extra = Allocate(entropy);
        try
        {
            var inputBlob = new DataBlob { cbData = plain.Length, pbData = input };
            var entropyBlob = new DataBlob { cbData = entropy.Length, pbData = extra };
            if (!CryptProtectData(ref inputBlob, null, ref entropyBlob, IntPtr.Zero, IntPtr.Zero,
                    CryptProtectUiForbidden | CryptProtectLocalMachine, out var output))
                throw Creation(MfaKeyStoreCreationErrorKind.CreationFailed,
                    "mfa_key_protect_failed: DPAPI no protegió la clave (Win32 " + Marshal.GetLastWin32Error().ToString(CultureInfo.InvariantCulture) + ")");
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
            // La copia nativa de la clave en claro se pone a cero antes de liberarla.
            ZeroAndFree(input, plain.Length);
            Marshal.FreeHGlobal(extra);
        }
    }

    private static byte[] Unprotect(byte[] blob, byte[] entropy)
    {
        var input = Allocate(blob);
        var extra = Allocate(entropy);
        try
        {
            var inputBlob = new DataBlob { cbData = blob.Length, pbData = input };
            var entropyBlob = new DataBlob { cbData = entropy.Length, pbData = extra };
            if (!CryptUnprotectData(ref inputBlob, IntPtr.Zero, ref entropyBlob, IntPtr.Zero, IntPtr.Zero, CryptProtectUiForbidden, out var output))
                throw Creation(MfaKeyStoreCreationErrorKind.ValidationFailed,
                    "mfa_key_unprotect_failed: DPAPI no abrió el blob recién creado (Win32 " + Marshal.GetLastWin32Error().ToString(CultureInfo.InvariantCulture) + ")");
            try
            {
                if (output.cbData != MfaKeyRing.KeyBytes)
                    throw Creation(MfaKeyStoreCreationErrorKind.ValidationFailed, "mfa_key_length_invalid: la clave descifrada no mide 32 bytes");
                var result = new byte[output.cbData];
                Marshal.Copy(output.pbData, result, 0, result.Length);
                return result;
            }
            finally
            {
                ZeroAndFreeBlob(output);
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

    private static void ZeroAndFree(IntPtr handle, int length)
    {
        Marshal.Copy(new byte[length], 0, handle, length);
        Marshal.FreeHGlobal(handle);
    }

    private static void ZeroAndFreeBlob(DataBlob blob)
    {
        if (blob.pbData == IntPtr.Zero) return;
        Marshal.Copy(new byte[blob.cbData], 0, blob.pbData, blob.cbData);
        LocalFree(blob.pbData);
    }

    private static bool Exists(string path) => Directory.Exists(path) || File.Exists(path);

    private static MfaKeyStoreCreationException Invalid(string detail) =>
        new(MfaKeyStoreCreationErrorKind.InvalidRequest, "mfa_key_store_request_invalid: " + detail, null);

    private static MfaKeyStoreCreationException Creation(MfaKeyStoreCreationErrorKind kind, string message, Exception? inner = null) =>
        new(kind, message, inner);

    [StructLayout(LayoutKind.Sequential)]
    private struct DataBlob
    {
        public int cbData;
        public IntPtr pbData;
    }

    [DllImport("crypt32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool CryptProtectData(ref DataBlob dataIn, [MarshalAs(UnmanagedType.LPWStr)] string? description,
        ref DataBlob optionalEntropy, IntPtr reserved, IntPtr promptStruct, int flags, out DataBlob dataOut);

    [DllImport("crypt32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool CryptUnprotectData(ref DataBlob dataIn, IntPtr description, ref DataBlob optionalEntropy,
        IntPtr reserved, IntPtr promptStruct, int flags, out DataBlob dataOut);

    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern IntPtr LocalFree(IntPtr memory);
}

internal enum MfaKeyStoreCreationErrorKind
{
    InvalidRequest,
    AlreadyExists,
    ValidationFailed,
    CreationFailed,
    PublishFailed,
}

// El mensaje contiene sólo códigos y detalles genéricos: nunca bytes de clave ni contenido de los archivos.
internal sealed class MfaKeyStoreCreationException(MfaKeyStoreCreationErrorKind kind, string message, Exception? inner)
    : Exception(message, inner)
{
    public MfaKeyStoreCreationErrorKind Kind { get; } = kind;
}
