using System.Runtime.InteropServices;
using System.Runtime.Versioning;
using System.Security.Principal;
using System.Text.Json;

namespace RackClick.Server;

// Inicialización local explícita del almacén MFA (MFA-L2j): `--mfa-keys-init`. Sólo Windows, operador local elevado, JSON acotado por
// stdin, confianza productiva fija (SYSTEM y Administradores) y delegación en WindowsMfaKeyStoreWriter.CreateInitialStore sin tocar el
// writer. No usa base de datos, no requiere origen HTTPS, no compone el proveedor del host, no habilita MfaKeyStore:Enabled, no inicia
// listener y no regenera, repara ni retira nada ajeno. Contrato: evidence/s1-20261026/mfa-l2j-claude/INVESTIGACION-PREVIA.md.
// Salida: una línea JSON con status, code (sólo si aplica) y residue (none, declared o unknown). Nunca rutas, claves ni mensajes internos.
internal static class MfaKeyStoreInitCommand
{
    private const int MaxInputChars = 4096;
    private const uint TokenQuery = 0x0008;
    private const int TokenElevationClass = 20;
    private static readonly JsonSerializerOptions Json = new(JsonSerializerDefaults.Web);

    // CLI productiva: la elevación se comprueba antes de leer nada, y la confianza es la fija.
    public static int Run(TextReader input, TextWriter output)
    {
        if (!OperatingSystem.IsWindows()) return Reject(output, "mfa_keystore_init_not_windows");
        return Run(input, output, IsElevatedAdministrator(), ProductionTrusted(), beforePublish: null, beforeOwnFolderCreation: null);
    }

    // Seam interno de pruebas: elevación, confianza y puntos de ensayo del writer. La CLI y la configuración nunca llegan aquí.
    internal static int Run(TextReader input, TextWriter output, bool elevated, IReadOnlyCollection<SecurityIdentifier> trusted,
        Action? beforePublish, Action? beforeOwnFolderCreation)
    {
        if (!OperatingSystem.IsWindows()) return Reject(output, "mfa_keystore_init_not_windows");
        if (!elevated) return Reject(output, "mfa_keystore_init_not_elevated");
        try
        {
            var parsed = ParseInput(ReadBounded(input));
            var (root, installation, reader) = Validate(parsed, trusted);
            return Create(output, root, installation, reader, trusted, beforePublish, beforeOwnFolderCreation);
        }
        catch (MfaKeyStoreInitRejected rejected)
        {
            return Reject(output, rejected.Code);
        }
    }

    [SupportedOSPlatform("windows")]
    private static (string Root, Guid Installation, SecurityIdentifier Reader) Validate(InitInput input,
        IReadOnlyCollection<SecurityIdentifier> trusted)
    {
        if (string.IsNullOrEmpty(input.InstancesRoot) || !Path.IsPathFullyQualified(input.InstancesRoot))
            throw new MfaKeyStoreInitRejected("mfa_keystore_init_root_relative");
        string root;
        try
        {
            root = Path.GetFullPath(input.InstancesRoot);
        }
        catch (Exception ex) when (ex is ArgumentException or NotSupportedException or PathTooLongException)
        {
            throw new MfaKeyStoreInitRejected("mfa_keystore_init_root_invalid");
        }
        if (!Guid.TryParseExact(input.InstallationId, "D", out var installation) || installation == Guid.Empty)
            throw new MfaKeyStoreInitRejected("mfa_keystore_init_installation_invalid");
        SecurityIdentifier reader;
        try
        {
            reader = new SecurityIdentifier(input.ReaderSid);
        }
        catch (ArgumentException)
        {
            throw new MfaKeyStoreInitRejected("mfa_keystore_init_reader_invalid");
        }
        if (trusted.Contains(reader)) throw new MfaKeyStoreInitRejected("mfa_keystore_init_reader_trusted");
        return (root, installation, reader);
    }

    // Delegación en el writer aprobado. Sus excepciones se traducen a códigos constantes con el estado del residuo.
    [SupportedOSPlatform("windows")]
    private static int Create(TextWriter output, string root, Guid installation, SecurityIdentifier reader,
        IReadOnlyCollection<SecurityIdentifier> trusted, Action? beforePublish, Action? beforeOwnFolderCreation)
    {
        try
        {
            WindowsMfaKeyStoreWriter.CreateInitialStore(root, installation, reader, trusted, beforePublish, beforeOwnFolderCreation);
            return Write(output, "created", code: null, residue: "none", exitCode: 0);
        }
        catch (MfaKeyStoreCreationException ex)
        {
            string residue = ex.Residue.Count > 0 ? "declared" : "none";
            return ex.Kind switch
            {
                MfaKeyStoreCreationErrorKind.AlreadyExists => Write(output, "rejected", "mfa_keystore_init_exists", residue, 1),
                MfaKeyStoreCreationErrorKind.InvalidRequest => Write(output, "rejected", "mfa_keystore_init_rejected", residue, 1),
                _ => Write(output, "failed", "mfa_keystore_init_failed", residue, 1),
            };
        }
        catch (Exception ex) when (ex is IOException or UnauthorizedAccessException)
        {
            // E/S que escapa sin lista de residuos: el estado queda como desconocido, nunca como limpieza completa.
            return Write(output, "failed", "mfa_keystore_init_failed", "unknown", 1);
        }
    }

    // Lectura acotada: más de MaxInputChars caracteres se rechazan sin procesar el resto.
    private static string ReadBounded(TextReader input)
    {
        var buffer = new char[MaxInputChars + 1];
        int count = 0;
        while (count < buffer.Length)
        {
            int read = input.Read(buffer, count, buffer.Length - count);
            if (read == 0) break;
            count += read;
        }
        if (count > MaxInputChars) throw new MfaKeyStoreInitRejected("mfa_keystore_init_input_too_large");
        return new string(buffer, 0, count);
    }

    // JSON estricto: un objeto con exactamente instancesRoot, installationId y readerSid, todos cadenas, sin duplicados ni campos extra.
    private static InitInput ParseInput(string text)
    {
        JsonDocument document;
        try
        {
            document = JsonDocument.Parse(text, new JsonDocumentOptions
            {
                MaxDepth = 2,
                CommentHandling = JsonCommentHandling.Disallow,
                AllowTrailingCommas = false,
            });
        }
        catch (JsonException)
        {
            throw new MfaKeyStoreInitRejected("mfa_keystore_init_input_invalid");
        }
        using (document)
        {
            var root = document.RootElement;
            if (root.ValueKind != JsonValueKind.Object) throw new MfaKeyStoreInitRejected("mfa_keystore_init_input_invalid");
            var values = new Dictionary<string, string>(StringComparer.Ordinal);
            foreach (var property in root.EnumerateObject())
            {
                if (!TryName(property, out var name) || property.Value.ValueKind != JsonValueKind.String ||
                    name is not ("instancesRoot" or "installationId" or "readerSid") ||
                    !TryText(property.Value, out var value) || !values.TryAdd(name, value))
                    throw new MfaKeyStoreInitRejected("mfa_keystore_init_input_invalid");
            }
            if (values.Count != 3) throw new MfaKeyStoreInitRejected("mfa_keystore_init_input_invalid");
            return new InitInput(values["instancesRoot"], values["installationId"], values["readerSid"]);
        }
    }

    [SupportedOSPlatform("windows")]
    private static SecurityIdentifier[] ProductionTrusted() =>
        [new SecurityIdentifier(WellKnownSidType.LocalSystemSid, null), new SecurityIdentifier(WellKnownSidType.BuiltinAdministratorsSid, null)];

    // Elevado = el usuario es Administrador Y el token del proceso está elevado. Sin elevar, aunque el usuario sea administrador, es no.
    [SupportedOSPlatform("windows")]
    internal static bool IsElevatedAdministrator()
    {
        using var identity = WindowsIdentity.GetCurrent();
        return new WindowsPrincipal(identity).IsInRole(WindowsBuiltInRole.Administrator) && TokenIsElevated();
    }

    [SupportedOSPlatform("windows")]
    private static bool TokenIsElevated()
    {
        if (!OpenProcessToken(GetCurrentProcess(), TokenQuery, out var token)) return false;
        try
        {
            var size = Marshal.SizeOf<TokenElevationInfo>();
            if (!GetTokenInformation(token, TokenElevationClass, out var elevation, size, out _)) return false;
            return elevation.TokenIsElevated != 0;
        }
        finally
        {
            CloseHandle(token);
        }
    }

    // Frontera de decodificación. Un escape Unicode sin pareja (\uD800 o \uDC00) es JSON estructuralmente válido, pero no se puede
    // convertir a texto: esa lectura lanza InvalidOperationException. Sólo esa lectura se traduce a rechazo de entrada. Un par
    // suplementario válido se decodifica normalmente y no se rechaza aquí.
    private static bool TryName(JsonProperty property, out string name)
    {
        try
        {
            name = property.Name;
            return true;
        }
        catch (InvalidOperationException)
        {
            name = "";
            return false;
        }
    }

    private static bool TryText(JsonElement element, out string text)
    {
        try
        {
            text = element.GetString() ?? "";
            return true;
        }
        catch (InvalidOperationException)
        {
            text = "";
            return false;
        }
    }

    private static int Reject(TextWriter output, string code) => Write(output, "rejected", code, "none", 1);

    private static int Write(TextWriter output, string status, string? code, string residue, int exitCode)
    {
        object payload = code is null ? new { status, residue } : new { status, code, residue };
        output.WriteLine(JsonSerializer.Serialize(payload, Json));
        return exitCode;
    }

    private sealed record InitInput(string InstancesRoot, string InstallationId, string ReaderSid);

    private sealed class MfaKeyStoreInitRejected(string code) : Exception(code)
    {
        public string Code => Message;
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct TokenElevationInfo
    {
        public uint TokenIsElevated;
    }

    [DllImport("advapi32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool OpenProcessToken(IntPtr processHandle, uint desiredAccess, out IntPtr tokenHandle);

    [DllImport("advapi32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool GetTokenInformation(IntPtr tokenHandle, int tokenInformationClass, out TokenElevationInfo tokenInformation,
        int tokenInformationLength, out int returnLength);

    [DllImport("kernel32.dll")]
    private static extern IntPtr GetCurrentProcess();

    [DllImport("kernel32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool CloseHandle(IntPtr handle);
}
