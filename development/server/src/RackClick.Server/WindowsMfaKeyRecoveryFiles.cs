using System.ComponentModel;
using System.Globalization;
using System.Runtime.InteropServices;
using System.Runtime.Versioning;
using System.Security.AccessControl;
using System.Security.Cryptography;
using System.Security.Principal;
using System.Text;
using System.Text.RegularExpressions;
using Microsoft.Win32.SafeHandles;

namespace RackClick.Server;

// Archivo privado del sobre RCKEY (MFA-L2g). Exporta el sobre de L2f a un archivo nuevo en una carpeta explícita del operador
// y lo recupera explícitamente a un almacén nuevo. Sólo contiene ciphertext: ningún plaintext, clave ni contraseña llega a disco.
// Contrato e investigación previa: evidence/s1-20261026/mfa-l2g-claude/INVESTIGACION-PREVIA.md.
//
// Exportar: el sobre se produce en memoria (L2f). El staging se crea con CREATE_NEW y su DACL protegida desde la creación; se
// escribe, se vacía a disco, se relee con el lector aprobado y se valida con MfaKeyRecoveryEnvelope.Open. La publicación es un
// renombrado por identificador con ReplaceIfExists = FALSE: un destino existente nunca se reemplaza.
// Recuperar: el archivo se lee con el lector aprobado (tamaño antes de reservar, FileShare.Read, identidad y DACL del mismo
// identificador) y el contenido se entrega a WindowsMfaKeyRecovery.Recover, que autentica y valida antes de crear nada.
// Límites: ver el documento de contrato. La separación de rutas compara rutas normalizadas, no identidades.
[SupportedOSPlatform("windows")]
internal static class WindowsMfaKeyRecoveryFiles
{
    private const string EnvelopeExtension = ".rckey";
    private const string StagingPrefix = ".rckey-";
    private const string StagingSuffix = ".partial";
    private static readonly Regex EnvelopeFileName = new(@"^[A-Za-z0-9][A-Za-z0-9._-]{0,119}\.rckey\z", RegexOptions.CultureInvariant);

    private const uint GenericRead = 0x80000000;
    private const uint GenericWrite = 0x40000000;
    private const uint Delete = 0x00010000;
    private const uint FileReadAttributes = 0x0080;
    private const uint FileShareRead = 0x1;
    private const uint FileShareWrite = 0x2;
    private const uint FileShareDelete = 0x4;
    private const uint CreateNew = 1;
    private const uint OpenExisting = 3;
    private const uint FileAttributeNormal = 0x80;
    private const uint FileAttributeDirectory = 0x10;
    private const uint FileAttributeReparsePoint = 0x400;
    private const uint FileFlagOpenReparsePoint = 0x00200000;
    private const int ErrorFileExists = 80;
    private const int ErrorAlreadyExists = 183;
    private const int FileRenameInfoClass = 3;
    private const int FileDispositionInfoClass = 4;

    // Exporta el sobre de un almacén de origen a un archivo nuevo en la carpeta del operador. Devuelve un recibo sin secretos.
    // readerSid: lector del origen (servicio). envelopeReaderSid: custodio que puede leer el archivo; el servicio sólo lo lee si
    // se le concede. afterStagingWrite y beforePublish son puntos de ensayo internos.
    public static MfaEnvelopeFileReceipt ExportToFile(string instancesRoot, Guid installationId, SecurityIdentifier readerSid,
        SecurityIdentifier envelopeReaderSid, IReadOnlyCollection<SecurityIdentifier> trustedPrincipals, string password,
        string folder, string fileName, Action<string>? afterStagingWrite = null, Action? beforePublish = null,
        Action<string>? afterPublish = null, Action<string>? whileHeld = null)
    {
        var root = RequireAbsolute(instancesRoot, "la raíz de instancias");
        var envelopeFolder = RequireAbsolute(folder, "la carpeta del sobre");
        var name = RequireEnvelopeName(fileName);
        RequireSeparated(envelopeFolder, root, "la carpeta del sobre no puede estar dentro de la raíz de instancias ni contenerla");
        var trusted = RequireTrusted(trustedPrincipals, envelopeReaderSid);
        var fileReader = new WindowsMfaKeyFileReader(envelopeReaderSid, TrustedValues(trusted));
        RequireFolder(fileReader, envelopeFolder);

        var finalPath = Path.Combine(envelopeFolder, name);
        if (new FileInfo(finalPath).Exists || new DirectoryInfo(finalPath).Exists)
            throw Failure(WindowsMfaKeyRecoveryFileErrorKind.AlreadyExists, "el archivo de destino ya existe; no se modifica");

        var tracked = new List<Tracked>();
        byte[]? envelope = null;
        try
        {
            try
            {
                envelope = WindowsMfaKeyRecovery.Export(root, installationId, readerSid, trusted, password);
            }
            catch (WindowsMfaKeyRecoveryException ex)
            {
                throw Failure(WindowsMfaKeyRecoveryFileErrorKind.ExportRejected, "el origen no se pudo exportar: " + ex.Kind, ex);
            }

            var stagingPath = Path.Combine(envelopeFolder, StagingPrefix + Guid.NewGuid().ToString("N") + StagingSuffix);
            var staging = CreateStaging(stagingPath, envelope, trusted, envelopeReaderSid, tracked);
            afterStagingWrite?.Invoke(stagingPath);
            RequireStagingContent(fileReader, stagingPath, envelope, password);
            Publish(staging, finalPath, beforePublish);
            afterPublish?.Invoke(finalPath);
            var published = VerifyPublished(fileReader, finalPath, staging.Identity, envelope, whileHeld);
            return new MfaEnvelopeFileReceipt(finalPath, published.Length, Sha256Hex(published), MfaEnvelopeFileOutcome.Published);
        }
        catch (WindowsMfaKeyRecoveryFileException ex)
        {
            throw WithResidue(ex, tracked);
        }
        catch (Exception ex) when (ex is IOException or UnauthorizedAccessException)
        {
            throw WithResidue(Failure(WindowsMfaKeyRecoveryFileErrorKind.WriteFailed, "fallo de E/S durante la exportación", ex), tracked);
        }
    }

    // Recupera un archivo de sobre a un almacén nuevo. Lee el archivo con el lector del custodio y valida antes de crear nada.
    public static MfaEnvelopeFileReceipt RecoverFromFile(string envelopePath, string password, Guid expectedSourceInstallationId,
        string destinationRoot, Guid destinationInstallationId, SecurityIdentifier readerSid, SecurityIdentifier envelopeReaderSid,
        IReadOnlyCollection<SecurityIdentifier> trustedPrincipals, bool adaptDestinationInstallation,
        Action? beforeEnvelopeRead = null, Action? beforePublish = null, Action? beforeOwnFolderCreation = null)
    {
        var fullPath = RequireAbsolute(envelopePath, "la ruta del sobre");
        var name = RequireEnvelopeName(Path.GetFileName(fullPath));
        var envelopeFolder = Path.GetDirectoryName(fullPath) ?? throw Failure(WindowsMfaKeyRecoveryFileErrorKind.InvalidRequest, "ruta del sobre sin carpeta");
        var destination = RequireAbsolute(destinationRoot, "la raíz de destino");
        RequireSeparated(envelopeFolder, destination, "la carpeta del sobre no puede estar dentro del destino ni contenerlo");
        var trusted = RequireTrusted(trustedPrincipals, envelopeReaderSid);
        var fileReader = new WindowsMfaKeyFileReader(envelopeReaderSid, TrustedValues(trusted));
        RequireFolder(fileReader, envelopeFolder);

        byte[] envelope;
        try
        {
            envelope = fileReader.ReadValidated(Path.Combine(envelopeFolder, name), MfaKeyRecoveryEnvelope.MaxEnvelopeBytes, beforeEnvelopeRead);
        }
        catch (MfaKeyRingException ex)
        {
            throw Failure(WindowsMfaKeyRecoveryFileErrorKind.FileRejected, "el archivo del sobre fue rechazado: " + ex.Kind, ex);
        }

        try
        {
            WindowsMfaKeyRecovery.Recover(envelope, password, expectedSourceInstallationId, destination, destinationInstallationId,
                readerSid, trusted, adaptDestinationInstallation, beforePublish, beforeOwnFolderCreation);
        }
        catch (WindowsMfaKeyRecoveryException ex)
        {
            throw Failure(WindowsMfaKeyRecoveryFileErrorKind.RecoveryRejected, "la recuperación no se completó: " + ex.Kind, ex, ex.Residue);
        }
        return new MfaEnvelopeFileReceipt(fullPath, envelope.Length, Sha256Hex(envelope), MfaEnvelopeFileOutcome.Recovered);
    }

    // Staging nuevo: CREATE_NEW con DACL protegida desde la creación, escritura, vaciado a disco y registro de identidad.
    private static Tracked CreateStaging(string path, byte[] content, SecurityIdentifier[] trusted, SecurityIdentifier reader,
        List<Tracked> tracked)
    {
        var descriptor = ProtectedFileSecurity(trusted, reader).GetSecurityDescriptorBinaryForm();
        var pinned = GCHandle.Alloc(descriptor, GCHandleType.Pinned);
        try
        {
            var attributes = new SecurityAttributes
            {
                nLength = (uint)Marshal.SizeOf<SecurityAttributes>(),
                lpSecurityDescriptor = pinned.AddrOfPinnedObject(),
                bInheritHandle = 0,
            };
            using var handle = CreateFileW(path, GenericWrite | FileReadAttributes, FileShareRead, ref attributes, CreateNew,
                FileAttributeNormal | FileFlagOpenReparsePoint, IntPtr.Zero);
            if (handle.IsInvalid)
                throw Failure(WindowsMfaKeyRecoveryFileErrorKind.WriteFailed, "no se pudo crear el staging del sobre",
                    new Win32Exception(Marshal.GetLastWin32Error()));
            var info = Information(handle);
            if (!IsKind(info, isDirectory: false))
                throw Failure(WindowsMfaKeyRecoveryFileErrorKind.WriteFailed, "el staging creado no es un archivo regular; se conserva");
            var entry = new Tracked(path, IdentityOf(info));
            tracked.Add(entry);
            RandomAccess.Write(handle, content, 0);
            if (!FlushFileBuffers(handle))
                throw new IOException("el vaciado a disco del staging falló", new Win32Exception(Marshal.GetLastWin32Error()));
            return entry;
        }
        finally
        {
            pinned.Free();
        }
    }

    // El staging releído con el lector aprobado debe ser idéntico al sobre generado y abrir con la contraseña del operador.
    private static void RequireStagingContent(WindowsMfaKeyFileReader reader, string path, byte[] envelope, string password)
    {
        byte[] readback;
        try
        {
            readback = reader.ReadValidated(path, MfaKeyRecoveryEnvelope.MaxEnvelopeBytes);
        }
        catch (MfaKeyRingException ex)
        {
            throw Failure(WindowsMfaKeyRecoveryFileErrorKind.ValidationFailed, "el staging no se pudo releer: " + ex.Kind, ex);
        }
        if (!CryptographicOperations.FixedTimeEquals(readback, envelope))
            throw Failure(WindowsMfaKeyRecoveryFileErrorKind.ValidationFailed, "el contenido releído no coincide con el sobre generado");
        try
        {
            var plaintext = MfaKeyRecoveryEnvelope.Open(password, readback);
            CryptographicOperations.ZeroMemory(plaintext);
        }
        catch (MfaRecoveryEnvelopeException ex)
        {
            throw Failure(WindowsMfaKeyRecoveryFileErrorKind.ValidationFailed, "el contenido del staging no abre: " + ex.Kind, ex);
        }
    }

    // Publicación sin reemplazo: el staging se renombra por identificador verificado. Un destino existente produce AlreadyExists.
    private static void Publish(Tracked staging, string target, Action? beforePublish)
    {
        try
        {
            beforePublish?.Invoke();
            using var handle = OpenVerified(staging.Path, staging.Identity, Delete | FileReadAttributes)
                ?? throw Failure(WindowsMfaKeyRecoveryFileErrorKind.PublishFailed,
                    "el staging ya no es el objeto validado; no se publica");
            RenameByHandle(handle, target);
            staging.Path = target;
        }
        catch (WindowsMfaKeyRecoveryFileException)
        {
            throw;
        }
        catch (IOException ex) when (IsAlreadyExists(ex))
        {
            throw Failure(WindowsMfaKeyRecoveryFileErrorKind.AlreadyExists, "el destino apareció durante la publicación; no se reemplaza", ex);
        }
        catch (Exception ex) when (ex is IOException or UnauthorizedAccessException)
        {
            throw Failure(WindowsMfaKeyRecoveryFileErrorKind.PublishFailed, "no se pudo publicar el archivo del sobre", ex);
        }
    }

    // Verificación del archivo final ligada a la identidad del staging publicado (MFA-L2G-01). El objeto de la ruta se retiene con
    // compartición de sólo lectura mientras el lector aprobado lo comprueba: nadie puede moverlo, reemplazarlo, escribirlo ni
    // borrarlo en esa ventana. Un objeto distinto en la ruta se rechaza sin tocarlo.
    private static byte[] VerifyPublished(WindowsMfaKeyFileReader reader, string path, FileIdentity expected, byte[] envelope,
        Action<string>? whileHeld)
    {
        using var held = OpenHeldForRead(path, expected);
        whileHeld?.Invoke(path);
        byte[] published;
        try
        {
            published = reader.ReadValidated(path, MfaKeyRecoveryEnvelope.MaxEnvelopeBytes);
        }
        catch (MfaKeyRingException ex)
        {
            throw Failure(WindowsMfaKeyRecoveryFileErrorKind.ValidationFailed, "el archivo publicado no se pudo verificar: " + ex.Kind, ex);
        }
        if (IdentityOf(Information(held)) != expected)
            throw Failure(WindowsMfaKeyRecoveryFileErrorKind.ValidationFailed,
                "la identidad del archivo final cambió durante la verificación; no se retira ni se toca");
        if (!CryptographicOperations.FixedTimeEquals(published, envelope))
            throw Failure(WindowsMfaKeyRecoveryFileErrorKind.ValidationFailed, "el archivo publicado no coincide con el sobre generado");
        return published;
    }

    // Abre el objeto de la ruta final sólo para lectura y con compartición de lectura: mientras esté abierto no se puede escribir,
    // borrar ni renombrar. Si no es el archivo regular publicado, se cierra y se rechaza sin tocarlo.
    private static SafeFileHandle OpenHeldForRead(string path, FileIdentity expected)
    {
        var handle = CreateFileW(path, GenericRead, FileShareRead, IntPtr.Zero, OpenExisting, FileFlagOpenReparsePoint, IntPtr.Zero);
        if (handle.IsInvalid)
            throw Failure(WindowsMfaKeyRecoveryFileErrorKind.ValidationFailed, "el archivo final no se puede abrir para verificarlo",
                new Win32Exception(Marshal.GetLastWin32Error()));
        try
        {
            var info = Information(handle);
            if (!IsKind(info, isDirectory: false) || IdentityOf(info) != expected)
                throw Failure(WindowsMfaKeyRecoveryFileErrorKind.ValidationFailed,
                    "el archivo final no es el objeto publicado; se conserva el objeto ajeno y no se retira");
            return handle;
        }
        catch
        {
            handle.Dispose();
            throw;
        }
    }

    // DACL protegida: trusted con control total y lectura explícita del custodio. Sin herencia del padre.
    private static FileSecurity ProtectedFileSecurity(SecurityIdentifier[] trusted, SecurityIdentifier reader)
    {
        var security = new FileSecurity();
        security.SetAccessRuleProtection(true, false);
        foreach (var sid in trusted)
            security.AddAccessRule(new FileSystemAccessRule(sid, FileSystemRights.FullControl, AccessControlType.Allow));
        security.AddAccessRule(new FileSystemAccessRule(reader, FileSystemRights.ReadAndExecute, AccessControlType.Allow));
        return security;
    }

    // Retira lo propio por identificador. Lo que no se pueda retirar se conserva y se devuelve como residuo.
    private static List<string> Discard(List<Tracked> tracked)
    {
        var residue = new List<string>();
        for (var i = tracked.Count - 1; i >= 0; i--)
        {
            if (!RetireOwned(tracked[i])) residue.Add(tracked[i].Path);
        }
        return residue;
    }

    private static bool RetireOwned(Tracked entry)
    {
        using var handle = OpenVerified(entry.Path, entry.Identity, Delete | FileReadAttributes);
        if (handle is null) return false;
        try
        {
            MarkForDeletion(handle);
            return true;
        }
        catch (IOException)
        {
            return false;
        }
        catch (UnauthorizedAccessException)
        {
            return false;
        }
    }

    private static WindowsMfaKeyRecoveryFileException WithResidue(WindowsMfaKeyRecoveryFileException failure, List<Tracked> tracked)
    {
        var residue = failure.Residue.Concat(Discard(tracked)).ToArray();
        if (residue.Length == 0) return failure;
        return new WindowsMfaKeyRecoveryFileException(failure.Kind,
            failure.Message + " Residuo conservado (no se pudo retirar): " + string.Join("; ", residue) + ".", failure, residue);
    }

    private static SafeFileHandle? OpenVerified(string path, FileIdentity expected, uint access)
    {
        var handle = OpenByPath(path, access);
        if (handle is null) return null;
        try
        {
            var info = Information(handle);
            if (!IsKind(info, isDirectory: false) || IdentityOf(info) != expected)
            {
                handle.Dispose();
                return null;
            }
            return handle;
        }
        catch
        {
            handle.Dispose();
            throw;
        }
    }

    private static SafeFileHandle? OpenByPath(string path, uint access)
    {
        var handle = CreateFileW(path, access, FileShareRead | FileShareWrite | FileShareDelete, IntPtr.Zero, OpenExisting,
            FileFlagOpenReparsePoint, IntPtr.Zero);
        return handle.IsInvalid ? null : handle;
    }

    // Carpeta del operador: validada con el lector del custodio, sin reparar nada ajeno.
    private static void RequireFolder(WindowsMfaKeyFileReader reader, string folder)
    {
        try
        {
            reader.RequireSafeFolder(folder);
        }
        catch (MfaKeyRingException ex)
        {
            throw Failure(WindowsMfaKeyRecoveryFileErrorKind.FolderRejected, "la carpeta del sobre no es segura: " + ex.Kind, ex);
        }
    }

    private static string RequireAbsolute(string? path, string what)
    {
        if (string.IsNullOrEmpty(path) || !Path.IsPathFullyQualified(path))
            throw Failure(WindowsMfaKeyRecoveryFileErrorKind.InvalidRequest, what + " debe ser una ruta absoluta");
        return Path.GetFullPath(path);
    }

    private static string RequireEnvelopeName(string? name)
    {
        if (string.IsNullOrEmpty(name) || !EnvelopeFileName.IsMatch(name))
            throw Failure(WindowsMfaKeyRecoveryFileErrorKind.InvalidRequest, "nombre de sobre no válido: debe terminar en " + EnvelopeExtension + " y no contener separadores");
        return name;
    }

    // Carpetas separadas por ruta normalizada. Sólo se comprueba por ruta: los puntos de unión de los ancestros no se resuelven.
    private static void RequireSeparated(string a, string b, string message)
    {
        if (Inside(a, b) || Inside(b, a)) throw Failure(WindowsMfaKeyRecoveryFileErrorKind.InvalidRequest, message);
    }

    private static bool Inside(string path, string root)
    {
        var p = Path.TrimEndingDirectorySeparator(path);
        var r = Path.TrimEndingDirectorySeparator(root);
        return string.Equals(p, r, StringComparison.OrdinalIgnoreCase) ||
            p.StartsWith(r + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase);
    }

    private static SecurityIdentifier[] RequireTrusted(IReadOnlyCollection<SecurityIdentifier> trustedPrincipals, SecurityIdentifier readerSid)
    {
        var trusted = trustedPrincipals.ToArray();
        if (trusted.Length == 0) throw Failure(WindowsMfaKeyRecoveryFileErrorKind.InvalidRequest, "sin principales de confianza");
        if (trusted.Contains(readerSid)) throw Failure(WindowsMfaKeyRecoveryFileErrorKind.InvalidRequest, "el lector no puede ser principal de confianza");
        return trusted;
    }

    private static HashSet<string> TrustedValues(SecurityIdentifier[] trusted) =>
        trusted.Select(sid => sid.Value).ToHashSet(StringComparer.Ordinal);

    private static string Sha256Hex(byte[] bytes) => Convert.ToHexString(SHA256.HashData(bytes)).ToLowerInvariant();

    private static bool IsAlreadyExists(IOException ex) =>
        ex.InnerException is Win32Exception win32 && win32.NativeErrorCode is ErrorFileExists or ErrorAlreadyExists;

    private static ByHandleFileInformation Information(SafeFileHandle handle)
    {
        if (!GetFileInformationByHandle(handle, out var info))
            throw new IOException("no se pudo leer la identidad del archivo", new Win32Exception(Marshal.GetLastWin32Error()));
        return info;
    }

    private static bool IsKind(ByHandleFileInformation info, bool isDirectory) =>
        ((info.FileAttributes & FileAttributeDirectory) != 0) == isDirectory && (info.FileAttributes & FileAttributeReparsePoint) == 0;

    private static FileIdentity IdentityOf(ByHandleFileInformation info) =>
        new(info.VolumeSerialNumber, ((ulong)info.FileIndexHigh << 32) | info.FileIndexLow);

    // Renombrado sobre el identificador: ReplaceIfExists = FALSE. Nombre absoluto terminado en NUL, búfer a cero (medido en L2c).
    private static void RenameByHandle(SafeFileHandle handle, string target)
    {
        var nameBytes = Encoding.Unicode.GetBytes(target);
        var size = 2 * IntPtr.Size + 4 + nameBytes.Length + sizeof(char);
        var buffer = Marshal.AllocHGlobal(size);
        try
        {
            Marshal.Copy(new byte[size], 0, buffer, size);
            Marshal.WriteByte(buffer, 0, 0);
            Marshal.WriteIntPtr(buffer, IntPtr.Size, IntPtr.Zero);
            Marshal.WriteInt32(buffer, 2 * IntPtr.Size, nameBytes.Length);
            Marshal.Copy(nameBytes, 0, IntPtr.Add(buffer, 2 * IntPtr.Size + 4), nameBytes.Length);
            if (!SetFileInformationByHandle(handle, FileRenameInfoClass, buffer, (uint)size))
                throw new IOException("el renombrado sobre el identificador falló", new Win32Exception(Marshal.GetLastWin32Error()));
        }
        finally
        {
            Marshal.FreeHGlobal(buffer);
        }
    }

    private static void MarkForDeletion(SafeFileHandle handle)
    {
        var buffer = Marshal.AllocHGlobal(1);
        try
        {
            Marshal.WriteByte(buffer, 1);
            if (!SetFileInformationByHandle(handle, FileDispositionInfoClass, buffer, 1))
                throw new IOException("el borrado sobre el identificador falló", new Win32Exception(Marshal.GetLastWin32Error()));
        }
        finally
        {
            Marshal.FreeHGlobal(buffer);
        }
    }

    private static WindowsMfaKeyRecoveryFileException Failure(WindowsMfaKeyRecoveryFileErrorKind kind, string message, Exception? inner = null,
        IReadOnlyList<string>? residue = null) =>
        new(kind, message, inner, residue ?? []);

    private readonly record struct FileIdentity(uint Volume, ulong Index);

    // Objeto propio creado por esta llamada. Path cambia a la ruta final tras publicar: la identidad no cambia.
    private sealed class Tracked(string path, FileIdentity identity)
    {
        public string Path { get; set; } = path;

        public FileIdentity Identity { get; } = identity;
    }

    // FILETIME alineado a 4 bytes, como en Windows (ver el escritor aprobado).
    [StructLayout(LayoutKind.Sequential)]
    private struct FileTime
    {
        public uint Low;
        public uint High;
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct ByHandleFileInformation
    {
        public uint FileAttributes;
        public FileTime CreationTime;
        public FileTime LastAccessTime;
        public FileTime LastWriteTime;
        public uint VolumeSerialNumber;
        public uint FileSizeHigh;
        public uint FileSizeLow;
        public uint NumberOfLinks;
        public uint FileIndexHigh;
        public uint FileIndexLow;
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct SecurityAttributes
    {
        public uint nLength;
        public IntPtr lpSecurityDescriptor;
        public int bInheritHandle;
    }

    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern SafeFileHandle CreateFileW(string fileName, uint desiredAccess, uint shareMode,
        ref SecurityAttributes securityAttributes, uint creationDisposition, uint flagsAndAttributes, IntPtr templateFile);

    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern SafeFileHandle CreateFileW(string fileName, uint desiredAccess, uint shareMode, IntPtr securityAttributes,
        uint creationDisposition, uint flagsAndAttributes, IntPtr templateFile);

    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern bool GetFileInformationByHandle(SafeFileHandle file, out ByHandleFileInformation information);

    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern bool SetFileInformationByHandle(SafeFileHandle file, int informationClass, IntPtr information, uint bufferSize);

    [DllImport("kernel32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool FlushFileBuffers(SafeFileHandle file);
}

internal enum WindowsMfaKeyRecoveryFileErrorKind
{
    InvalidRequest,
    FolderRejected,
    ExportRejected,
    AlreadyExists,
    WriteFailed,
    ValidationFailed,
    PublishFailed,
    FileRejected,
    RecoveryRejected,
}

// Sólo códigos y detalles genéricos. Nunca contraseñas, claves ni contenido del sobre.
internal sealed class WindowsMfaKeyRecoveryFileException(WindowsMfaKeyRecoveryFileErrorKind kind, string message, Exception? inner,
    IReadOnlyList<string> residue) : Exception(message, inner)
{
    public WindowsMfaKeyRecoveryFileErrorKind Kind { get; } = kind;

    // Rutas propias que no se pudieron retirar. Si hay residuo, el archivo o el destino no quedaron limpios.
    public IReadOnlyList<string> Residue { get; } = residue;
}

internal enum MfaEnvelopeFileOutcome
{
    Published,
    Recovered,
}

// Recibo sin secretos: ruta, longitud, SHA256 de los bytes del archivo y resultado. Ningún otro campo.
internal sealed record MfaEnvelopeFileReceipt(string Path, long Length, string Sha256, MfaEnvelopeFileOutcome Outcome);
