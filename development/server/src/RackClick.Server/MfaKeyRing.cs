using System.Globalization;
using System.Text;
using System.Text.Json;

namespace RackClick.Server;

// Anillo de versiones de la clave TOTP (D2 v2 §2 y §5). Valida formato, identidad de instalación y coherencia de
// ring.json y de cada archivo de clave. No descifra ni genera nada. Cualquier anomalía lanza un error explícito:
// nunca se repara ni se regenera una clave.
public enum MfaKeyRingErrorKind
{
    InvalidPath,
    UnsafePath,
    MissingFile,
    FileTooLarge,
    InvalidFormat,
    IdentityMismatch,
    UnknownVersion,
    Corrupt,
    UnsafeAccess,
}

// El mensaje sólo contiene un código y un detalle genérico: nunca bytes de clave ni contenido de los archivos.
public sealed class MfaKeyRingException(MfaKeyRingErrorKind kind, string message) : Exception(message)
{
    public MfaKeyRingErrorKind Kind { get; } = kind;
}

public enum MfaKeyState
{
    Active,
    Retired,
}

public sealed record MfaKeyRingEntry(int Version, MfaKeyState State, DateTimeOffset CreatedAtUtc);

// Contenido de key-v<N>.dpapi.json. La clave sigue protegida por DPAPI hasta que la abre el proveedor.
public sealed record MfaKeyFile(Guid InstallationId, int KeyVersion, byte[] ProtectedKey);

public sealed class MfaKeyRing
{
    public const string RingFileName = "ring.json";
    public const string RingFormat = "RackClick.MfaKeyRing";
    public const string KeyFileFormat = "RackClick.MfaKeyFile";
    public const string ProtectionName = "DPAPI-LocalMachine";
    public const int FormatVersion = 1;
    public const int KeyBytes = MfaSecretCipher.KeyBytes;
    public const int MaxRingFileBytes = 64 * 1024;
    public const int MaxKeyFileBytes = 16 * 1024;
    public const int MaxProtectedKeyBytes = 4096;
    public const int MaxVersions = 64;
    private const int MaxKeyVersion = 1_000_000;
    private const int MaxJsonDepth = 8;
    private const string CreatedAtFormat = "yyyy-MM-dd'T'HH:mm:ss'Z'";
    private static readonly UTF8Encoding StrictUtf8 = new(false, true);

    private readonly List<MfaKeyRingEntry> _entries;

    private MfaKeyRing(Guid installationId, List<MfaKeyRingEntry> entries)
    {
        InstallationId = installationId;
        _entries = entries;
    }

    public Guid InstallationId { get; }

    public IReadOnlyList<MfaKeyRingEntry> Entries => _entries;

    public static string KeyFileName(int version) => "key-v" + version.ToString(CultureInfo.InvariantCulture) + ".dpapi.json";

    // Entropía DPAPI: liga cada blob a su instalación y a su versión. Copiar un archivo a otra versión o instalación no descifra.
    public static byte[] EntropyFor(Guid installationId, int version) =>
        Encoding.UTF8.GetBytes(
            "RackClick.MfaKey|v" + FormatVersion.ToString(CultureInfo.InvariantCulture) + "|" + installationId.ToString("D") +
            "|" + version.ToString(CultureInfo.InvariantCulture));

    public MfaKeyRingEntry RequireEntry(int version)
    {
        foreach (var entry in _entries)
            if (entry.Version == version) return entry;
        throw new MfaKeyRingException(MfaKeyRingErrorKind.UnknownVersion, "mfa_key_version_unknown: la versión no figura en ring.json");
    }

    public static MfaKeyRing Parse(byte[] bytes, Guid expectedInstallationId)
    {
        using var document = ParseDocument(bytes, MaxRingFileBytes);
        var root = document.RootElement;
        ExactProperties(root, "format", "formatVersion", "installationId", "versions");
        RequireHeader(root, RingFormat);
        var installationId = RequireInstallation(root, expectedInstallationId);

        var versions = Property(root, "versions");
        if (versions.ValueKind != JsonValueKind.Array || versions.GetArrayLength() is < 1 or > MaxVersions)
            throw Invalid("versions: número de versiones fuera de rango");

        var entries = new List<MfaKeyRingEntry>();
        var seen = new HashSet<int>();
        foreach (var item in versions.EnumerateArray())
        {
            ExactProperties(item, "version", "state", "createdAtUtc");
            var version = RequireInt(item, "version", 1, MaxKeyVersion);
            if (!seen.Add(version)) throw Invalid("versions: versión repetida");
            entries.Add(new MfaKeyRingEntry(version, RequireState(item), RequireUtcTimestamp(item, "createdAtUtc")));
        }
        if (entries.Count(e => e.State == MfaKeyState.Active) != 1)
            throw Invalid("versions: debe haber exactamente una versión activa");
        entries.Sort((a, b) => a.Version.CompareTo(b.Version));
        return new MfaKeyRing(installationId, entries);
    }

    public static MfaKeyFile ParseKeyFile(byte[] bytes, Guid expectedInstallationId, int expectedVersion)
    {
        using var document = ParseDocument(bytes, MaxKeyFileBytes);
        var root = document.RootElement;
        ExactProperties(root, "format", "formatVersion", "installationId", "keyVersion", "protection", "protectedKey");
        RequireHeader(root, KeyFileFormat);
        var installationId = RequireInstallation(root, expectedInstallationId);
        var keyVersion = RequireInt(root, "keyVersion", 1, MaxKeyVersion);
        if (keyVersion != expectedVersion)
            throw new MfaKeyRingException(MfaKeyRingErrorKind.Corrupt, "mfa_key_file_version_mismatch: la versión declarada no coincide con el nombre del archivo");
        if (RequireString(root, "protection") != ProtectionName) throw Invalid("protection: valor desconocido");
        return new MfaKeyFile(installationId, keyVersion, DecodeProtectedKey(RequireString(root, "protectedKey")));
    }

    private static JsonDocument ParseDocument(byte[] bytes, int maxBytes)
    {
        if (bytes.Length == 0) throw Invalid("archivo vacío");
        if (bytes.Length > maxBytes)
            throw new MfaKeyRingException(MfaKeyRingErrorKind.FileTooLarge, "mfa_key_file_too_large: el archivo supera el límite");
        string text;
        try
        {
            text = StrictUtf8.GetString(bytes);
        }
        catch (DecoderFallbackException)
        {
            throw Invalid("codificación no UTF-8 o con BOM");
        }
        try
        {
            return JsonDocument.Parse(text, new JsonDocumentOptions
            {
                MaxDepth = MaxJsonDepth,
                CommentHandling = JsonCommentHandling.Disallow,
                AllowTrailingCommas = false,
            });
        }
        catch (JsonException)
        {
            throw Invalid("JSON no válido");
        }
    }

    // Exige exactamente las propiedades previstas: ni faltan, ni sobran, ni se repiten.
    private static void ExactProperties(JsonElement element, params string[] names)
    {
        if (element.ValueKind != JsonValueKind.Object) throw Invalid("se esperaba un objeto");
        var seen = new HashSet<string>(StringComparer.Ordinal);
        foreach (var property in element.EnumerateObject())
            if (Array.IndexOf(names, property.Name) < 0 || !seen.Add(property.Name))
                throw Invalid("propiedad inesperada o repetida");
        if (seen.Count != names.Length) throw Invalid("faltan propiedades");
    }

    private static void RequireHeader(JsonElement root, string format)
    {
        if (RequireString(root, "format") != format) throw Invalid("format: tipo de archivo inesperado");
        RequireInt(root, "formatVersion", FormatVersion, FormatVersion);
    }

    private static Guid RequireInstallation(JsonElement root, Guid expected)
    {
        if (!Guid.TryParseExact(RequireString(root, "installationId"), "D", out var value))
            throw Invalid("installationId: identificador no válido");
        if (value != expected)
            throw new MfaKeyRingException(MfaKeyRingErrorKind.IdentityMismatch, "mfa_key_identity_mismatch: el archivo pertenece a otra instalación");
        return value;
    }

    private static MfaKeyState RequireState(JsonElement item) => RequireString(item, "state") switch
    {
        "active" => MfaKeyState.Active,
        "retired" => MfaKeyState.Retired,
        _ => throw Invalid("state: valor desconocido"),
    };

    private static DateTimeOffset RequireUtcTimestamp(JsonElement element, string name)
    {
        if (!DateTimeOffset.TryParseExact(RequireString(element, name), CreatedAtFormat, CultureInfo.InvariantCulture,
                DateTimeStyles.AssumeUniversal, out var value))
            throw Invalid(name + ": fecha UTC no válida");
        return value;
    }

    private static byte[] DecodeProtectedKey(string text)
    {
        byte[] bytes;
        try
        {
            bytes = Convert.FromBase64String(text);
        }
        catch (FormatException)
        {
            throw Invalid("protectedKey: base64 no válido");
        }
        if (bytes.Length is < 1 or > MaxProtectedKeyBytes) throw Invalid("protectedKey: tamaño fuera de rango");
        return bytes;
    }

    private static JsonElement Property(JsonElement element, string name)
    {
        if (!element.TryGetProperty(name, out var value)) throw Invalid(name + ": falta");
        return value;
    }

    private static string RequireString(JsonElement element, string name)
    {
        var value = Property(element, name);
        if (value.ValueKind != JsonValueKind.String) throw Invalid(name + ": debe ser texto");
        return value.GetString()!;
    }

    private static int RequireInt(JsonElement element, string name, int min, int max)
    {
        var value = Property(element, name);
        if (value.ValueKind != JsonValueKind.Number || !value.TryGetInt32(out var number) || number < min || number > max)
            throw Invalid(name + ": entero fuera de rango");
        return number;
    }

    private static MfaKeyRingException Invalid(string detail) =>
        new(MfaKeyRingErrorKind.InvalidFormat, "mfa_key_format_invalid: " + detail);
}
