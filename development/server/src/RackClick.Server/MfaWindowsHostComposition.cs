using System.Runtime.Versioning;
using System.Security.Cryptography;
using System.Security.Principal;
using Microsoft.Extensions.Configuration;

namespace RackClick.Server;

// Composición del proveedor Windows en el host (MFA-L2i). Configuración explícita: MfaKeyStore:Enabled, MfaKeyStore:InstancesRoot y
// MfaKeyStore:InstallationId. Ausente o false: no se compone nada. Verdadero: el preflight valida un almacén ya provisionado con los
// componentes aprobados (lector, parser y proveedor), sólo en lectura. Cualquier fallo es cerrado: MfaHostCompositionException con un
// código sanitizado, sin rutas, claves ni SID. Contrato: evidence/s1-20261026/mfa-l2i-claude/INVESTIGACION-PREVIA.md.

// Modo de la configuración MfaKeyStore:Enabled.
internal enum MfaHostMode
{
    Disabled,
    Enabled,
    Invalid,
}

// Fallo de composición o de validación. El mensaje es sólo el código: nunca rutas, claves ni identidades.
internal sealed class MfaHostCompositionException(string code) : Exception(code)
{
    public string Code => Message;
}

// Identidad que aporta el lector y los principales de confianza del almacén. La productiva es ProcessMfaHostIdentity; el host de
// pruebas puede sustituirla, y la salida diagnóstica declara qué rama se usó.
internal interface IMfaHostIdentity
{
    SecurityIdentifier? ReaderSid { get; }

    IReadOnlyCollection<SecurityIdentifier> TrustedPrincipals { get; }

    string Description { get; }
}

// Identidad sustituta fuera de Windows: no hay lector ni confianza. La composición rechaza el arranque con mfa_keystore_not_windows.
internal sealed class UnavailableMfaHostIdentity : IMfaHostIdentity
{
    public SecurityIdentifier? ReaderSid => null;

    public IReadOnlyCollection<SecurityIdentifier> TrustedPrincipals { get; } = [];

    public string Description => "no-disponible";
}

// Identidad de producción: el SID de la identidad del proceso como lector y SYSTEM/Administradores como confianza fija.
// No se acepta ningún SID por configuración, JSON ni variables de entorno.
[SupportedOSPlatform("windows")]
internal sealed class ProcessMfaHostIdentity : IMfaHostIdentity
{
    private static readonly SecurityIdentifier LocalSystemSid = new(WellKnownSidType.LocalSystemSid, null);
    private static readonly SecurityIdentifier AdministratorsSid = new(WellKnownSidType.BuiltinAdministratorsSid, null);

    public SecurityIdentifier? ReaderSid => OperatingSystem.IsWindows() ? ProcessSid() : null;

    public IReadOnlyCollection<SecurityIdentifier> TrustedPrincipals { get; } = [LocalSystemSid, AdministratorsSid];

    public string Description => "fija-SYSTEM-Administradores";

    [SupportedOSPlatform("windows")]
    private static SecurityIdentifier? ProcessSid()
    {
        using var identity = WindowsIdentity.GetCurrent();
        return identity.User;
    }
}

// Proveedor compuesto y su diagnóstico sanitizado. Se registra una sola vez en el contenedor de DI.
internal sealed record MfaHostComposition(IMfaKeyProvider Provider, string Diagnostic);

internal static class MfaWindowsHostComposition
{
    private const string Section = "MfaKeyStore";

    public static MfaHostMode ModeOf(IConfiguration configuration)
    {
        var raw = configuration[Section + ":Enabled"]?.Trim();
        if (string.IsNullOrEmpty(raw) || string.Equals(raw, "false", StringComparison.OrdinalIgnoreCase)) return MfaHostMode.Disabled;
        return string.Equals(raw, "true", StringComparison.OrdinalIgnoreCase) ? MfaHostMode.Enabled : MfaHostMode.Invalid;
    }

    public static MfaHostComposition Compose(MfaHostMode mode, IConfiguration configuration, IMfaHostIdentity identity) =>
        Compose(mode, configuration, identity, OperatingSystem.IsWindows());

    // isWindows se recibe como parámetro para que las pruebas ejerciten el rechazo "no Windows" sin cambiar de sistema.
    internal static MfaHostComposition Compose(MfaHostMode mode, IConfiguration configuration, IMfaHostIdentity identity, bool isWindows)
    {
        if (mode == MfaHostMode.Disabled) throw new InvalidOperationException("MfaKeyStore deshabilitado: no hay proveedor que componer");
        if (mode == MfaHostMode.Invalid) throw Fail("mfa_keystore_config_invalid");
        if (!isWindows || !OperatingSystem.IsWindows()) throw Fail("mfa_keystore_not_windows");

        var root = Setting(configuration, "InstancesRoot");
        if (root is null) throw Fail("mfa_keystore_root_missing");
        if (!Path.IsPathFullyQualified(root)) throw Fail("mfa_keystore_root_relative");

        var rawInstallation = Setting(configuration, "InstallationId");
        if (rawInstallation is null) throw Fail("mfa_keystore_installation_missing");
        if (!Guid.TryParseExact(rawInstallation, "D", out var installation) || installation == Guid.Empty)
            throw Fail("mfa_keystore_installation_invalid");

        var reader = identity.ReaderSid ?? throw Fail("mfa_keystore_identity_unavailable");
        var trusted = identity.TrustedPrincipals.ToArray();
        if (trusted.Length == 0) throw Fail("mfa_keystore_trust_empty");
        if (trusted.Contains(reader)) throw Fail("mfa_keystore_reader_trusted");

        return Validate(NormalizeRoot(root), installation, reader, trusted, identity.Description);
    }

    // Normaliza la raíz configurada. Una cadena válida para JSON puede contener caracteres que la ruta de Windows rechaza, como NUL;
    // esa excepción se traduce a un código constante. Ni el mensaje ni la ruta salen del proceso.
    private static string NormalizeRoot(string root)
    {
        try
        {
            return Path.GetFullPath(root);
        }
        catch (Exception ex) when (ex is ArgumentException or NotSupportedException or PathTooLongException)
        {
            throw Fail("mfa_keystore_root_invalid");
        }
    }

    // E/S o permisos que el lector aprobado no clasifica, por ejemplo un archivo retenido en exclusiva por otro proceso.
    // Sólo estos tipos: los errores de programación no se absorben aquí.
    private static bool IsUnreadable(Exception ex) => ex is IOException or UnauthorizedAccessException;

    // Preflight de sólo lectura: carpetas, anillo, material de cada versión y activa. Las copias de clave se ponen a cero al terminar.
    [SupportedOSPlatform("windows")]
    private static MfaHostComposition Validate(string root, Guid installation, SecurityIdentifier reader, SecurityIdentifier[] trusted,
        string description)
    {
        var files = new WindowsMfaKeyFileReader(reader, trusted.Select(sid => sid.Value).ToHashSet(StringComparer.Ordinal));
        var installationFolder = Path.Combine(root, installation.ToString("D"));
        var keysFolder = Path.Combine(installationFolder, WindowsMfaKeyProvider.KeysFolderName);
        MfaKeyRing ring;
        try
        {
            files.RequireSafeFolder(root);
            files.RequireSafeFolder(installationFolder);
            files.RequireSafeFolder(keysFolder);
            MfaMaintenanceAdmission.ThrowIfFenced(root, installation);
            ring = MfaKeyRing.Parse(files.ReadValidated(Path.Combine(keysFolder, MfaKeyRing.RingFileName), MfaKeyRing.MaxRingFileBytes),
                installation);
        }
        catch (MfaKeyRingException ex)
        {
            throw Fail(StoreCode(ex.Kind, storeStage: true));
        }
        catch (Exception ex) when (IsUnreadable(ex))
        {
            throw Fail("mfa_keystore_unreadable");
        }

        var provider = new WindowsMfaKeyProvider(root, installation, reader, trusted);
        foreach (var entry in ring.Entries)
            CheckKey(() => provider.GetKey(entry.Version));
        var active = ring.Entries.Single(entry => entry.State == MfaKeyState.Active);
        CheckActive(provider, active.Version);
        return new MfaHostComposition(provider,
            $"mfa_keystore: habilitado; versiones={ring.Entries.Count}; activa={active.Version}; confianza={description}");
    }

    [SupportedOSPlatform("windows")]
    private static void CheckKey(Func<byte[]> load)
    {
        byte[] key;
        try
        {
            key = load();
        }
        catch (MfaKeyRingException ex)
        {
            throw Fail(StoreCode(ex.Kind, storeStage: false));
        }
        catch (Exception ex) when (IsUnreadable(ex))
        {
            throw Fail("mfa_keystore_unreadable");
        }
        try
        {
            if (key.Length != MfaKeyRing.KeyBytes) throw Fail("mfa_keystore_corrupt");
        }
        finally
        {
            CryptographicOperations.ZeroMemory(key);
        }
    }

    [SupportedOSPlatform("windows")]
    private static void CheckActive(WindowsMfaKeyProvider provider, int expectedVersion)
    {
        (int Version, byte[] Key) active;
        try
        {
            active = provider.GetActiveKey();
        }
        catch (MfaKeyRingException ex)
        {
            throw Fail(StoreCode(ex.Kind, storeStage: false));
        }
        catch (Exception ex) when (IsUnreadable(ex))
        {
            throw Fail("mfa_keystore_unreadable");
        }
        try
        {
            if (active.Version != expectedVersion || active.Key.Length != MfaKeyRing.KeyBytes) throw Fail("mfa_keystore_corrupt");
        }
        finally
        {
            CryptographicOperations.ZeroMemory(active.Key);
        }
    }

    // Traduce el tipo de fallo del lector o del parser a un código sanitizado. "Ausente" depende de la etapa: almacén o versión.
    private static string StoreCode(MfaKeyRingErrorKind kind, bool storeStage) => kind switch
    {
        MfaKeyRingErrorKind.MissingFile => storeStage ? "mfa_keystore_store_missing" : "mfa_keystore_version_missing",
        MfaKeyRingErrorKind.UnsafeAccess or MfaKeyRingErrorKind.UnsafePath => "mfa_keystore_access_unsafe",
        _ => "mfa_keystore_corrupt",
    };

    private static string? Setting(IConfiguration configuration, string name)
    {
        var value = configuration[Section + ":" + name]?.Trim();
        return string.IsNullOrEmpty(value) ? null : value;
    }

    private static MfaHostCompositionException Fail(string code) => new(code);
}
