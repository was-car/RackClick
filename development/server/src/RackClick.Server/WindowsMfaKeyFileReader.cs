using System.Globalization;
using System.Runtime.CompilerServices;
using System.Runtime.InteropServices;
using System.Runtime.Versioning;
using System.Security.AccessControl;
using System.Security.Principal;
using System.Text;
using Microsoft.Win32.SafeHandles;

// Primera asignación de visibilidad interna del repositorio: permite a las pruebas ensayar la ventana comprobar/abrir del
// lector sin exponerlo como API pública (docs/MENSAJE-PARA-CODEX-MFA-L2B-26-10-2026.md, decisión 1).
[assembly: InternalsVisibleTo("RackClick.Quality.Tests")]

namespace RackClick.Server;

// Lectura de los archivos del almacén MFA (MFA-L2b). Cada archivo se abre una sola vez y todas las comprobaciones y la
// lectura usan ese mismo identificador: propietario, DACL, tipo e identidad del objeto, y ruta final anclada a la ruta
// esperada. Con FileShare.Read (sin FILE_SHARE_DELETE ni FILE_SHARE_WRITE) nadie puede sustituir, renombrar o borrar el
// archivo mientras está abierto. Tras leer se repiten identidad y DACL sobre ese identificador; si han cambiado se rechaza,
// nunca se acreditan bytes distintos de los validados.
// Límites: no calcula el acceso efectivo de Windows; no aplica restricciones de lectura a los ancestros (sólo los ancla por
// ruta final); las carpetas de la cadena se validan por ruta, no por identificador.
[SupportedOSPlatform("windows")]
internal sealed class WindowsMfaKeyFileReader
{
    private const int GenericAll = 0x10000000;
    private const int GenericWrite = 0x40000000;
    private const int GenericRead = unchecked((int)0x80000000);

    // Derechos que permiten modificar un objeto. Incluye los bits genéricos por si el descriptor los conserva.
    private const int WriteRights =
        (int)(FileSystemRights.WriteData | FileSystemRights.AppendData | FileSystemRights.WriteExtendedAttributes |
              FileSystemRights.WriteAttributes | FileSystemRights.Delete | FileSystemRights.DeleteSubdirectoriesAndFiles |
              FileSystemRights.ChangePermissions | FileSystemRights.TakeOwnership) |
        GenericAll | GenericWrite;

    // Derechos que permiten leer datos.
    private const int ReadRights = (int)FileSystemRights.ReadData | GenericRead | GenericAll;

    private const uint FileAttributeDirectory = 0x10;
    private const uint FileAttributeReparsePoint = 0x400;
    private const uint VolumeDosName = 0;
    private const int InitialPathCapacity = 1024;

    private readonly SecurityIdentifier _readerSid;
    private readonly HashSet<string> _trusted;

    public WindowsMfaKeyFileReader(SecurityIdentifier readerSid, HashSet<string> trusted)
    {
        _readerSid = readerSid;
        _trusted = trusted;
    }

    // Carpeta de la cadena del almacén: existencia, sin reparse point y ACL de confianza.
    public void RequireSafeFolder(string path)
    {
        var folder = new DirectoryInfo(path);
        if (!folder.Exists) throw Missing(path);
        RequireNoReparsePoint(folder);
        RequireAcl(new DirectorySecurity(path, AccessControlSections.Owner | AccessControlSections.Access), Path.GetFileName(path));
    }

    // Devuelve los bytes del archivo validado. beforeRead se ejecuta después de validar y antes de leer: es el punto de
    // ensayo de la ventana comprobar/leer.
    public byte[] ReadValidated(string path, int maxBytes, Action? beforeRead = null)
    {
        var name = Path.GetFileName(path);
        var pathInfo = new FileInfo(path);
        if (!pathInfo.Exists) throw Missing(path);
        RequireNoReparsePoint(pathInfo);
        try
        {
            using var stream = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.Read);
            var handle = stream.SafeFileHandle;
            var identity = RequireRegularFile(handle, name);
            RequireAnchored(handle, path, name);
            RequireAcl(stream.GetAccessControl(), name);
            if (stream.Length > maxBytes)
                throw new MfaKeyRingException(MfaKeyRingErrorKind.FileTooLarge, "mfa_key_file_too_large: " + name);

            beforeRead?.Invoke();

            var bytes = new byte[stream.Length];
            stream.ReadExactly(bytes);
            if (Identity(handle, name) != identity)
                throw new MfaKeyRingException(MfaKeyRingErrorKind.UnsafePath, "mfa_key_store_object_changed: " + name);
            RequireAcl(stream.GetAccessControl(), name);
            return bytes;
        }
        catch (FileNotFoundException)
        {
            throw Missing(path);
        }
        catch (DirectoryNotFoundException)
        {
            throw Missing(path);
        }
        catch (UnauthorizedAccessException)
        {
            throw Unsafe(name, "sin acceso de lectura");
        }
    }

    private void RequireAcl(FileSystemSecurity security, string name)
    {
        var owner = (SecurityIdentifier?)security.GetOwner(typeof(SecurityIdentifier));
        if (owner is null || !_trusted.Contains(owner.Value) || owner == _readerSid)
            throw Unsafe(name, "propietario no de confianza o igual al lector");

        // Forma binaria: un DACL nulo aparece como DiscretionaryAcl == null. La forma SDDL de la sola sección DACL llega vacía.
        var descriptor = new RawSecurityDescriptor(security.GetSecurityDescriptorBinaryForm(), 0);
        if (descriptor.DiscretionaryAcl is null) throw Unsafe(name, "DACL nulo: acceso sin restricciones");

        var readerCanRead = false;
        foreach (var ace in descriptor.DiscretionaryAcl)
        {
            // Una denegación no concede acceso. Cualquier otro tipo que no sea Allow simple se rechaza, no se ignora.
            if (ace.AceType == AceType.AccessDenied) continue;
            if (ace.AceType != AceType.AccessAllowed || ace is not QualifiedAce allowed)
                throw Unsafe(name, "tipo de ACE no admitido: " + ace.AceType);
            var mask = allowed.AccessMask;
            var sid = allowed.SecurityIdentifier;
            var isReader = sid == _readerSid;
            var isTrusted = _trusted.Contains(sid.Value);
            if ((mask & ReadRights) != 0)
            {
                if (isReader) readerCanRead = true;
                else if (!isTrusted) throw Unsafe(name, "lectura concedida a " + sid.Value);
            }
            if ((mask & WriteRights) != 0 && (isReader || !isTrusted))
                throw Unsafe(name, "escritura concedida a " + sid.Value);
        }
        if (!readerCanRead) throw Unsafe(name, "el lector no tiene lectura explícita");
    }

    private static void RequireNoReparsePoint(FileSystemInfo item)
    {
        if ((item.Attributes & FileAttributes.ReparsePoint) != 0)
            throw new MfaKeyRingException(MfaKeyRingErrorKind.UnsafePath, "mfa_key_store_reparse_point: " + item.Name);
    }

    // Tipo e identidad del objeto abierto: archivo regular, sin enlaces adicionales.
    private static FileIdentity RequireRegularFile(SafeFileHandle handle, string name)
    {
        var info = Information(handle, name);
        if ((info.FileAttributes & (FileAttributeDirectory | FileAttributeReparsePoint)) != 0)
            throw new MfaKeyRingException(MfaKeyRingErrorKind.UnsafePath, "mfa_key_store_not_regular_file: " + name);
        if (info.NumberOfLinks != 1)
            throw new MfaKeyRingException(MfaKeyRingErrorKind.UnsafePath, "mfa_key_store_hard_links: " + name);
        return IdentityOf(info);
    }

    private static FileIdentity Identity(SafeFileHandle handle, string name) => IdentityOf(Information(handle, name));

    private static FileIdentity IdentityOf(ByHandleFileInformation info) =>
        new(info.VolumeSerialNumber, ((ulong)info.FileIndexHigh << 32) | info.FileIndexLow);

    private static ByHandleFileInformation Information(SafeFileHandle handle, string name)
    {
        if (!GetFileInformationByHandle(handle, out var info))
            throw new MfaKeyRingException(MfaKeyRingErrorKind.UnsafePath,
                "mfa_key_store_identity_unavailable: " + name + " (Win32 " + Marshal.GetLastWin32Error().ToString(CultureInfo.InvariantCulture) + ")");
        return info;
    }

    // La ruta final del identificador abierto debe coincidir con la ruta esperada ya normalizada. Así se detecta una
    // redirección por enlace en cualquier ancestro, también por encima de la raíz del almacén.
    private static void RequireAnchored(SafeFileHandle handle, string path, string name)
    {
        var expected = LongPath(Path.GetFullPath(path));
        if (!string.Equals(expected, FinalPath(handle, name), StringComparison.OrdinalIgnoreCase))
            throw new MfaKeyRingException(MfaKeyRingErrorKind.UnsafePath, "mfa_key_store_path_redirected: " + name);
    }

    private static string FinalPath(SafeFileHandle handle, string name)
    {
        var buffer = new StringBuilder(InitialPathCapacity);
        var length = GetFinalPathNameByHandle(handle, buffer, (uint)buffer.Capacity, VolumeDosName);
        if (length >= buffer.Capacity)
        {
            buffer.EnsureCapacity((int)length + 1);
            length = GetFinalPathNameByHandle(handle, buffer, (uint)buffer.Capacity, VolumeDosName);
        }
        if (length == 0 || length >= buffer.Capacity)
            throw new MfaKeyRingException(MfaKeyRingErrorKind.UnsafePath, "mfa_key_store_final_path_unavailable: " + name);
        var result = buffer.ToString(0, (int)length);
        return result.StartsWith(@"\\?\", StringComparison.Ordinal) ? result[4..] : result;
    }

    // Convierte nombres cortos (8.3) en largos sin resolver enlaces: la ruta anclada es la que se escribió, no la que se redirige.
    private static string LongPath(string path)
    {
        var buffer = new StringBuilder(InitialPathCapacity);
        var length = GetLongPathName(path, buffer, (uint)buffer.Capacity);
        if (length >= buffer.Capacity)
        {
            buffer.EnsureCapacity((int)length + 1);
            length = GetLongPathName(path, buffer, (uint)buffer.Capacity);
        }
        return length == 0 ? path : buffer.ToString(0, (int)length);
    }

    private static MfaKeyRingException Missing(string path) =>
        new(MfaKeyRingErrorKind.MissingFile, "mfa_key_store_missing: " + Path.GetFileName(path));

    private static MfaKeyRingException Unsafe(string name, string detail) =>
        new(MfaKeyRingErrorKind.UnsafeAccess, "mfa_key_store_access_unsafe: " + name + ": " + detail);

    private readonly record struct FileIdentity(uint Volume, ulong Index);

    // FILETIME alineado a 4 bytes, como en Windows. Con un long el relleno desplazaría los campos siguientes.
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

    [DllImport("kernel32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool GetFileInformationByHandle(SafeFileHandle file, out ByHandleFileInformation information);

    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern uint GetFinalPathNameByHandle(SafeFileHandle file, StringBuilder filePath, uint filePathLength, uint flags);

    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern uint GetLongPathName(string shortPath, StringBuilder longPath, uint longPathLength);
}
