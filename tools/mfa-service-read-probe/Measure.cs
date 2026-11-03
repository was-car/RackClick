using System.Runtime.InteropServices;
using System.Security.AccessControl;
using System.Security.Cryptography;
using System.Security.Principal;
using System.Text;
using Microsoft.Win32.SafeHandles;
using RackClick.Server;

namespace RackClick.MfaServiceReadProbe;

// Error con código constante. El texto nunca lleva rutas, SIDs ni mensajes internos.
internal sealed class ProbeException(string code) : Exception(code)
{
    public string Code { get; } = code;
}

internal sealed record ServiceFacts(string Name, uint ProcessId, string BinaryPath, SecurityIdentifier AccountSid);

internal sealed record WriteCounts
{
    public int Targets;
    public int WriteDenied;
    public int WriteGranted;
    public int DacDenied;
    public int DacGranted;
    public int OwnerIsReader;
    public int Inconclusive;
}

internal sealed record StoreOutcome(int ActiveVersion, int KeyBytes, bool Impersonated, WriteCounts Writes);

internal static class Sids
{
    // Cuentas de confianza fija del proveedor: nunca pueden ser el lector que se mide.
    internal static bool IsFixedTrust(SecurityIdentifier sid) =>
        sid.IsWellKnown(WellKnownSidType.LocalSystemSid) || sid.IsWellKnown(WellKnownSidType.BuiltinAdministratorsSid);

    internal static bool IsTrustedAccountName(string name) =>
        name.Equals("LocalSystem", StringComparison.OrdinalIgnoreCase)
        || name.Equals(@"NT AUTHORITY\SYSTEM", StringComparison.OrdinalIgnoreCase)
        || name.Equals(@".\LocalSystem", StringComparison.OrdinalIgnoreCase);
}

// Servicio por nombre exacto, sólo consultas: estado, PID, binario y cuenta de inicio.
internal static class ServiceMeasure
{
    internal static ServiceFacts Measure(string name)
    {
        var scm = Native.OpenSCManagerW(null, null, Native.SC_MANAGER_CONNECT);
        if (scm == IntPtr.Zero) throw new ProbeException("scm_unavailable");
        try
        {
            var service = Native.OpenServiceW(scm, name, Native.SERVICE_QUERY_CONFIG | Native.SERVICE_QUERY_STATUS);
            if (service == IntPtr.Zero)
            {
                var error = Marshal.GetLastWin32Error();
                throw new ProbeException(error == Native.ERROR_SERVICE_DOES_NOT_EXIST ? "service_not_found" : "service_open_failed");
            }
            try
            {
                if (!Native.QueryServiceStatusEx(service, Native.SC_STATUS_PROCESS_INFO, out var status,
                        (uint)Marshal.SizeOf<Native.SERVICE_STATUS_PROCESS>(), out _))
                    throw new ProbeException("service_status_failed");
                if (status.dwCurrentState != Native.SERVICE_RUNNING) throw new ProbeException("service_not_running");
                if (status.dwProcessId == 0) throw new ProbeException("service_pid_invalid");
                var (binary, account) = QueryConfig(service);
                return new ServiceFacts(name, status.dwProcessId, binary, ResolveAccount(account));
            }
            finally
            {
                Native.CloseServiceHandle(service);
            }
        }
        finally
        {
            Native.CloseServiceHandle(scm);
        }
    }

    private static (string Binary, string Account) QueryConfig(IntPtr service)
    {
        Native.QueryServiceConfigW(service, IntPtr.Zero, 0, out var needed);
        if (needed == 0 || Marshal.GetLastWin32Error() != Native.ERROR_INSUFFICIENT_BUFFER)
            throw new ProbeException("service_config_failed");
        var buffer = Marshal.AllocHGlobal((int)needed);
        try
        {
            if (!Native.QueryServiceConfigW(service, buffer, needed, out _)) throw new ProbeException("service_config_failed");
            var config = Marshal.PtrToStructure<Native.QUERY_SERVICE_CONFIGW>(buffer);
            return (Marshal.PtrToStringUni(config.lpBinaryPathName) ?? string.Empty,
                    Marshal.PtrToStringUni(config.lpServiceStartName) ?? string.Empty);
        }
        finally
        {
            Marshal.FreeHGlobal(buffer);
        }
    }

    internal static SecurityIdentifier ResolveAccount(string startName)
    {
        if (string.IsNullOrWhiteSpace(startName)) throw new ProbeException("service_account_unknown");
        if (Sids.IsTrustedAccountName(startName)) throw new ProbeException("service_account_trusted");
        var account = startName.StartsWith(@".\", StringComparison.Ordinal)
            ? Environment.MachineName + @"\" + startName[2..]
            : startName;
        SecurityIdentifier sid;
        try
        {
            sid = (SecurityIdentifier)new NTAccount(account).Translate(typeof(SecurityIdentifier));
        }
        catch (Exception)
        {
            throw new ProbeException("service_account_unresolved");
        }
        if (Sids.IsFixedTrust(sid)) throw new ProbeException("service_account_trusted");
        return sid;
    }
}

// Habilita un privilegio (por defecto SeDebugPrivilege) sólo si hace falta y sólo en el token del proceso que lo pide.
// Restaura el estado previo siempre. El nombre sólo lo cambia selftest-privilege, con privilegios propios no sensibles.
internal sealed class DebugPrivilege : IDisposable
{
    private const int RequestBytes = 16;
    private readonly string _privilegeName;
    private IntPtr _token;
    private IntPtr _previous;
    private IntPtr _returnLength;
    private bool _attempted;
    private bool _held;
    private bool _changed;
    private bool _restored = true;

    internal DebugPrivilege(string privilegeName = "SeDebugPrivilege") => _privilegeName = privilegeName;

    internal string State =>
        !_attempted ? "not_used" : !_held ? "unavailable" : _restored ? "enabled_restored" : "restore_failed";

    // true si esta instancia cambió el privilegio y aún no lo ha restaurado.
    internal bool Changed => _changed;

    // true sólo si el privilegio queda habilitado ahora (por esta llamada o antes).
    // Un fallo de AdjustTokenPrivileges es ProbeException; sólo ERROR_NOT_ALL_ASSIGNED significa "no asignado".
    internal bool EnsureEnabled()
    {
        if (_attempted) return _held;
        _attempted = true;
        if (!Native.OpenProcessToken(Native.GetCurrentProcess(), Native.TOKEN_ADJUST_PRIVILEGES | Native.TOKEN_QUERY, out _token))
            return false;
        if (!Native.LookupPrivilegeValueW(null, _privilegeName, out var luid)) return false;
        _previous = Marshal.AllocHGlobal(RequestBytes);
        _returnLength = Marshal.AllocHGlobal(sizeof(int));
        var request = Marshal.AllocHGlobal(RequestBytes);
        try
        {
            Marshal.WriteInt32(request, 0, 1);
            Marshal.WriteInt32(request, 4, unchecked((int)luid.LowPart));
            Marshal.WriteInt32(request, 8, luid.HighPart);
            Marshal.WriteInt32(request, 12, (int)Native.SE_PRIVILEGE_ENABLED);
            Marshal.WriteInt32(_returnLength, 0, 0);
            var adjusted = Native.AdjustTokenPrivileges(_token, false, request, RequestBytes, _previous, _returnLength);
            var error = Marshal.GetLastWin32Error();
            if (!adjusted) throw new ProbeException("privilege_adjust_failed");
            if (error == Native.ERROR_NOT_ALL_ASSIGNED) return false;
            // PrivilegeCount del estado previo: 0 si ya estaba habilitado (no hubo cambio), 1 si la entrada es nuestra.
            // Sólo con 1 se lee su Attributes; con 0 no hay entrada válida que leer.
            _changed = Marshal.ReadInt32(_previous, 0) == 1
                       && (Marshal.ReadInt32(_previous, 12) & (int)Native.SE_PRIVILEGE_ENABLED) == 0;
            _held = true;
            return true;
        }
        finally
        {
            Marshal.FreeHGlobal(request);
        }
    }

    // Pasa el estado previo como NewState, según la documentación de AdjustTokenPrivileges.
    // Restaurar sin PreviousState ni ReturnLength es válido.
    internal bool Restore()
    {
        if (_changed && _token != IntPtr.Zero && _previous != IntPtr.Zero)
        {
            _restored = Native.AdjustTokenPrivileges(_token, false, _previous, RequestBytes, IntPtr.Zero, IntPtr.Zero)
                        && Marshal.GetLastWin32Error() == 0;
            _changed = false;
        }
        return _restored;
    }

    public void Dispose()
    {
        Restore();
        if (_previous != IntPtr.Zero) { Marshal.FreeHGlobal(_previous); _previous = IntPtr.Zero; }
        if (_returnLength != IntPtr.Zero) { Marshal.FreeHGlobal(_returnLength); _returnLength = IntPtr.Zero; }
        if (_token != IntPtr.Zero) { Native.CloseHandle(_token); _token = IntPtr.Zero; }
    }
}

// Lectura de Attributes de un privilegio en un token ya abierto (sólo consulta).
internal static class TokenPrivilegeQuery
{
    internal static uint Attributes(IntPtr token, string name)
    {
        if (!Native.LookupPrivilegeValueW(null, name, out var luid)) throw new ProbeException("privilege_lookup_failed");
        Native.GetTokenInformation(token, Native.TokenPrivileges, IntPtr.Zero, 0, out var needed);
        if (Marshal.GetLastWin32Error() != Native.ERROR_INSUFFICIENT_BUFFER || needed == 0)
            throw new ProbeException("token_query_failed");
        var buffer = Marshal.AllocHGlobal((int)needed);
        try
        {
            if (!Native.GetTokenInformation(token, Native.TokenPrivileges, buffer, needed, out _))
                throw new ProbeException("token_query_failed");
            var count = Marshal.ReadInt32(buffer, 0);
            for (var i = 0; i < count; i++)
            {
                var offset = 4 + 12 * i;
                if (unchecked((uint)Marshal.ReadInt32(buffer, offset)) == luid.LowPart
                    && Marshal.ReadInt32(buffer, offset + 4) == luid.HighPart)
                    return unchecked((uint)Marshal.ReadInt32(buffer, offset + 8));
            }
            throw new ProbeException("privilege_not_in_token");
        }
        finally
        {
            Marshal.FreeHGlobal(buffer);
        }
    }
}

// Apertura de procesos y tokens. Sólo si la primera apertura se deniega se usa el privilegio de respaldo.
internal static class Access
{
    internal static IntPtr OpenProcess(uint pid, uint access, DebugPrivilege debug)
    {
        var handle = Native.OpenProcess(access, false, pid);
        if (handle != IntPtr.Zero) return handle;
        var error = Marshal.GetLastWin32Error();
        if (error == Native.ERROR_INVALID_PARAMETER) throw new ProbeException("process_not_found");
        if (error != Native.ERROR_ACCESS_DENIED) throw new ProbeException("process_open_failed");
        if (!debug.EnsureEnabled()) throw new ProbeException("process_access_denied");
        handle = Native.OpenProcess(access, false, pid);
        return handle != IntPtr.Zero ? handle : throw new ProbeException("process_access_denied");
    }

    internal static IntPtr OpenToken(IntPtr process, DebugPrivilege debug)
    {
        if (Native.OpenProcessToken(process, Native.TOKEN_DUPLICATE | Native.TOKEN_QUERY, out var token)) return token;
        if (!debug.EnsureEnabled()) throw new ProbeException("token_access_denied");
        return Native.OpenProcessToken(process, Native.TOKEN_DUPLICATE | Native.TOKEN_QUERY, out token)
            ? token
            : throw new ProbeException("token_access_denied");
    }
}

internal static class ImageMatch
{
    internal static string ProcessImage(IntPtr process)
    {
        var builder = new StringBuilder(1024);
        uint size = (uint)builder.Capacity;
        if (!Native.QueryFullProcessImageNameW(process, 0, builder, ref size)) throw new ProbeException("process_image_unavailable");
        return builder.ToString(0, (int)size);
    }

    internal static bool Matches(string processImage, string serviceCommandLine)
    {
        var candidate = ServiceBinary(serviceCommandLine);
        if (candidate.Length == 0) return false;
        return string.Equals(Path.GetFullPath(Environment.ExpandEnvironmentVariables(candidate)), Path.GetFullPath(processImage),
            StringComparison.OrdinalIgnoreCase);
    }

    // Binario del servicio sin argumentos: entre comillas o hasta el primer ".exe".
    internal static string ServiceBinary(string commandLine)
    {
        var text = commandLine.Trim();
        if (text.StartsWith('"'))
        {
            var end = text.IndexOf('"', 1);
            return end > 1 ? text[1..end] : string.Empty;
        }
        var exe = text.IndexOf(".exe", StringComparison.OrdinalIgnoreCase);
        return exe > 0 ? text[..(exe + 4)] : text;
    }
}

internal static class TokenLink
{
    // Duplicado de suplantación: el token de origen no se modifica y el duplicado se cierra al terminar el bloque.
    internal static SafeAccessTokenHandle DuplicateForImpersonation(IntPtr token)
    {
        if (!Native.DuplicateTokenEx(token, Native.TOKEN_QUERY | Native.TOKEN_DUPLICATE | Native.TOKEN_IMPERSONATE, IntPtr.Zero,
                Native.SecurityImpersonation, Native.TokenImpersonation, out var duplicate))
            throw new ProbeException("token_duplicate_failed");
        return new SafeAccessTokenHandle(duplicate);
    }

    internal static SecurityIdentifier SidOf(SafeAccessTokenHandle token)
    {
        using var identity = new WindowsIdentity(token.DangerousGetHandle());
        return identity.User ?? throw new ProbeException("token_sid_unavailable");
    }
}

// Comprobación de escritura sin escribir: se abre con FILE_WRITE_DATA (o FILE_ADD_FILE en carpetas) y con WRITE_DAC, y el
// identificador se cierra en el acto. Con OPEN_EXISTING no se crea, no se trunca y no se cambia la ACL.
// El propietario tiene WRITE_DAC de forma implícita y una entrada DENY no se lo quita: si el lector es el propietario se cuenta
// aparte (OwnerIsReader) y el veredicto de lectura lo rechaza. Un WRITE_DAC concedido a quien no es propietario sí es fallo.
internal static class WriteProbe
{
    private enum Outcome { Denied, Granted, Inconclusive }

    internal static WriteCounts CheckStore(string root, string installationFolder, string keysFolder, SecurityIdentifier reader)
    {
        var counts = new WriteCounts();
        foreach (var directory in new[] { root, installationFolder, keysFolder }) ProbeTarget(directory, true, reader, counts);
        foreach (var file in Directory.EnumerateFiles(keysFolder)) ProbeTarget(file, false, reader, counts);
        return counts;
    }

    internal static WriteCounts CheckFile(string file, SecurityIdentifier reader)
    {
        var counts = new WriteCounts();
        ProbeTarget(file, false, reader, counts);
        return counts;
    }

    private static void ProbeTarget(string path, bool directory, SecurityIdentifier reader, WriteCounts counts)
    {
        counts.Targets++;
        var owner = OwnerOf(path, directory);
        if (owner is null) counts.Inconclusive++;
        else if (owner.Equals(reader)) counts.OwnerIsReader++;
        var flags = directory ? Native.FILE_FLAG_BACKUP_SEMANTICS : 0u;
        Tally(Open(path, directory ? Native.FILE_ADD_FILE : Native.FILE_WRITE_DATA, flags), counts, dac: false);
        Tally(Open(path, Native.WRITE_DAC, flags), counts, dac: true);
    }

    private static SecurityIdentifier? OwnerOf(string path, bool directory)
    {
        try
        {
            FileSystemSecurity security = directory
                ? (FileSystemSecurity)new DirectoryInfo(path).GetAccessControl()
                : new FileInfo(path).GetAccessControl();
            return security.GetOwner(typeof(SecurityIdentifier)) as SecurityIdentifier;
        }
        catch (Exception)
        {
            return null;
        }
    }

    private static void Tally(Outcome outcome, WriteCounts counts, bool dac)
    {
        switch (outcome)
        {
            case Outcome.Denied:
                if (dac) counts.DacDenied++; else counts.WriteDenied++;
                break;
            case Outcome.Granted:
                if (dac) counts.DacGranted++; else counts.WriteGranted++;
                break;
            default:
                counts.Inconclusive++;
                break;
        }
    }

    private static Outcome Open(string path, uint access, uint flags)
    {
        var handle = Native.CreateFileW(path, access, Native.FILE_SHARE_ALL, IntPtr.Zero, Native.OPEN_EXISTING, flags, IntPtr.Zero);
        if (handle == Native.InvalidHandle)
            return Marshal.GetLastWin32Error() == Native.ERROR_ACCESS_DENIED ? Outcome.Denied : Outcome.Inconclusive;
        Native.CloseHandle(handle);
        return Outcome.Granted;
    }
}

internal static class StoreRead
{
    // Lectura con el proveedor aprobado: la confianza es la fija de producción (SYSTEM y Administradores) y el lector es la
    // cuenta medida. La clave se pone a cero en finally; nunca se devuelve al llamador, sólo versión y longitud.
    internal static (int Version, int Length) ReadActiveKey(string root, Guid installationId, SecurityIdentifier readerSid)
    {
        byte[]? key = null;
        try
        {
            var provider = new WindowsMfaKeyProvider(root, installationId, readerSid);
            var (version, material) = provider.GetActiveKey();
            key = material;
            return (version, key.Length);
        }
        catch (ProbeException)
        {
            throw;
        }
        catch (Exception ex)
        {
            throw new ProbeException(ErrorCode(ex.Message));
        }
        finally
        {
            if (key is not null) CryptographicOperations.ZeroMemory(key);
        }
    }

    // Sólo códigos del proveedor (mfa_…); cualquier otro texto se descarta.
    internal static string ErrorCode(string message)
    {
        var head = message.Split(':', 2)[0];
        var valid = head.StartsWith("mfa_", StringComparison.Ordinal)
                    && head.All(c => c is >= 'a' and <= 'z' or '_');
        return valid ? head : "store_read_failed";
    }
}
