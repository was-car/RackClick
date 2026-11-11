using System.Security.Cryptography;
using System.Text.Json;

namespace RackClick.Server;

internal sealed record MfaKeyVersionCount(int Version, long Pending, long Active, long Disabled);

internal sealed class MfaFactorVersionInventory
{
    internal MfaFactorVersionInventory(Guid installationId, IEnumerable<MfaKeyVersionCount> entries)
    {
        InstallationId = installationId;
        Entries = Array.AsReadOnly(entries.ToArray());
    }
    public Guid InstallationId { get; }
    public IReadOnlyList<MfaKeyVersionCount> Entries { get; }
}

// Sólo metadatos de un sobre autenticado. Nunca retiene plaintext, claves ni contraseña.
internal sealed class MfaEnvelopeVersionInventory
{
    internal MfaEnvelopeVersionInventory(Guid installationId, IEnumerable<int> versions, int activeVersion, string envelopeSha256)
    {
        InstallationId = installationId;
        Versions = Array.AsReadOnly(versions.ToArray());
        ActiveVersion = activeVersion;
        EnvelopeSha256 = envelopeSha256;
    }
    public Guid InstallationId { get; }
    public IReadOnlyList<int> Versions { get; }
    public int ActiveVersion { get; }
    public string EnvelopeSha256 { get; }
}

internal sealed class MfaBackupKeyInventory
{
    internal MfaBackupKeyInventory(Guid installationId, Guid backupId, string manifestSha256, string dumpSha256,
        string envelopeSha256, IEnumerable<int> factorVersions, IEnumerable<int> envelopeVersions,
        int envelopeActiveVersion, IEnumerable<int> requiredVersions)
    {
        InstallationId = installationId;
        BackupId = backupId;
        ManifestSha256 = manifestSha256;
        DumpSha256 = dumpSha256;
        EnvelopeSha256 = envelopeSha256;
        FactorVersions = Array.AsReadOnly(factorVersions.ToArray());
        EnvelopeVersions = Array.AsReadOnly(envelopeVersions.ToArray());
        EnvelopeActiveVersion = envelopeActiveVersion;
        RequiredVersions = Array.AsReadOnly(requiredVersions.ToArray());
    }
    public Guid InstallationId { get; }
    public Guid BackupId { get; }
    public string ManifestSha256 { get; }
    public string DumpSha256 { get; }
    public string EnvelopeSha256 { get; }
    public IReadOnlyList<int> FactorVersions { get; }
    public IReadOnlyList<int> EnvelopeVersions { get; }
    public int EnvelopeActiveVersion { get; }
    public IReadOnlyList<int> RequiredVersions { get; }
}

internal enum MfaKeyRetentionDecision
{
    InvalidInput,
    ScopeMismatch,
    CatalogIncomplete,
    MissingDependency,
    ActiveVersion,
    UnknownVersion,
    FactorReferenced,
    BackupReferenced,
    CandidateUnreferenced,
}

// Códigos constantes; nunca se refleja texto de entrada ni excepciones criptográficas/JSON.
internal sealed class MfaKeyRetentionException : Exception
{
    internal MfaKeyRetentionException(string code) : base(code) { }
}

// F06.02: no IO, DB, publicación ni retirada. El llamador debe suministrar el censo completo y pines de un
// registro privado independiente. No prueban vigencia/autenticidad del dump ni equivalencia con el censo.
// CandidateUnreferenced requiere F06.03 (fence/recenso/validación material/publicación recuperable) antes de actuar.
internal static class MfaKeyRetention
{
    internal const int MaxInventoryBytes = 64 * 1024;
    private const string Format = "RackClick.MfaBackupKeyInventory";
    private static readonly string[] Fields = ["format", "formatVersion", "installationId", "backupId", "manifestSha256",
        "dumpSha256", "envelopeSha256", "factorVersions", "envelopeVersions", "envelopeActiveVersion", "requiredVersions"];

    internal static MfaFactorVersionInventory FactorInventory(Guid installationId, IEnumerable<MfaKeyVersionCount> entries)
    {
        RequireId(installationId);
        if (entries is null) throw Invalid();
        var copy = new List<MfaKeyVersionCount>();
        var seen = new HashSet<int>();
        foreach (var entry in entries)
        {
            if (entry is null || copy.Count >= MfaKeyRing.MaxVersions || !VersionValid(entry.Version) || !seen.Add(entry.Version)
                || entry.Pending < 0 || entry.Active < 0 || entry.Disabled < 0) throw Invalid();
            try { _ = checked(entry.Pending + entry.Active + entry.Disabled); }
            catch (OverflowException) { throw Invalid(); }
            copy.Add(entry);
        }
        return new MfaFactorVersionInventory(installationId, copy.OrderBy(entry => entry.Version));
    }

    internal static MfaEnvelopeVersionInventory InspectEnvelope(byte[] envelope, string password, Guid expectedInstallationId)
    {
        RequireId(expectedInstallationId);
        byte[]? plaintext = null;
        try
        {
            // Copia acotada del ciphertext: evita que el hash describa bytes distintos de los autenticados.
            if (envelope is null || envelope.Length > MfaKeyRecoveryEnvelope.MaxEnvelopeBytes) throw Invalid();
            var copy = (byte[])envelope.Clone();
            plaintext = MfaKeyRecoveryEnvelope.Open(password, copy);
            using var content = MfaKeyRecoveryPayload.Deserialize(plaintext, expectedInstallationId);
            // Deserialize valida el anillo a través de MfaKeyRing.Parse.
            return new MfaEnvelopeVersionInventory(content.Ring.InstallationId,
                content.Ring.Entries.Select(entry => entry.Version),
                content.Ring.Entries.Single(entry => entry.State == MfaKeyState.Active).Version, Hash(copy));
        }
        catch (Exception error) when (error is MfaRecoveryEnvelopeException or MfaKeyRecoveryPayloadException or MfaKeyRetentionException)
        { throw new MfaKeyRetentionException("mfa_retention_envelope_rejected"); }
        finally { if (plaintext is not null) CryptographicOperations.ZeroMemory(plaintext); }
    }

    internal static MfaBackupKeyInventory CreateBackupInventory(Guid backupId, MfaFactorVersionInventory factors,
        MfaEnvelopeVersionInventory envelope, string manifestSha256, string dumpSha256)
    {
        if (factors is null || envelope is null) throw Invalid();
        var validated = FactorInventory(factors.InstallationId, factors.Entries);
        if (validated.InstallationId != envelope.InstallationId) throw Scope();
        var factorVersions = validated.Entries.Where(HasFactors).Select(entry => entry.Version).ToArray();
        var result = new MfaBackupKeyInventory(validated.InstallationId, backupId, manifestSha256, dumpSha256,
            envelope.EnvelopeSha256, factorVersions, envelope.Versions, envelope.ActiveVersion,
            Required(factorVersions, envelope.ActiveVersion));
        ValidateBackup(result);
        return result;
    }

    internal static byte[] SerializeBackupInventory(MfaBackupKeyInventory inventory)
    {
        ValidateBackup(inventory);
        using var buffer = new MemoryStream();
        using (var writer = new Utf8JsonWriter(buffer))
        {
            writer.WriteStartObject();
            writer.WriteString("format", Format);
            writer.WriteNumber("formatVersion", 1);
            writer.WriteString("installationId", inventory.InstallationId.ToString("D"));
            writer.WriteString("backupId", inventory.BackupId.ToString("D"));
            writer.WriteString("manifestSha256", inventory.ManifestSha256);
            writer.WriteString("dumpSha256", inventory.DumpSha256);
            writer.WriteString("envelopeSha256", inventory.EnvelopeSha256);
            WriteVersions(writer, "factorVersions", inventory.FactorVersions);
            WriteVersions(writer, "envelopeVersions", inventory.EnvelopeVersions);
            writer.WriteNumber("envelopeActiveVersion", inventory.EnvelopeActiveVersion);
            WriteVersions(writer, "requiredVersions", inventory.RequiredVersions);
            writer.WriteEndObject();
        }
        return buffer.ToArray();
    }

    // Todos los expected provienen de un registro externo de confianza, nunca del archivo a analizar.
    internal static MfaBackupKeyInventory ParseBackupInventory(byte[] bytes, Guid expectedInstallationId,
        string expectedInventorySha256, string expectedManifestSha256, string expectedDumpSha256, string expectedEnvelopeSha256)
    {
        RequireId(expectedInstallationId);
        RequireHash(expectedInventorySha256); RequireHash(expectedManifestSha256);
        RequireHash(expectedDumpSha256); RequireHash(expectedEnvelopeSha256);
        if (bytes is null || bytes.Length is 0 or > MaxInventoryBytes) throw Invalid();
        var copy = (byte[])bytes.Clone();
        if (Hash(copy) != expectedInventorySha256) throw Integrity();
        try
        {
            using var document = JsonDocument.Parse(copy, new JsonDocumentOptions
            { MaxDepth = 4, AllowTrailingCommas = false, CommentHandling = JsonCommentHandling.Disallow });
            var root = document.RootElement;
            if (root.ValueKind != JsonValueKind.Object) throw Invalid();
            var names = new HashSet<string>(StringComparer.Ordinal);
            foreach (var field in root.EnumerateObject())
            {
                var name = PropertyName(field);
                if (!Fields.Contains(name, StringComparer.Ordinal) || !names.Add(name)) throw Invalid();
            }
            if (names.Count != Fields.Length || String(root, "format") != Format || Int(root, "formatVersion") != 1) throw Invalid();
            var inventory = new MfaBackupKeyInventory(Id(root, "installationId"), Id(root, "backupId"),
                String(root, "manifestSha256"), String(root, "dumpSha256"), String(root, "envelopeSha256"),
                Versions(root, "factorVersions", true), Versions(root, "envelopeVersions", false),
                Int(root, "envelopeActiveVersion"), Versions(root, "requiredVersions", false));
            ValidateBackup(inventory);
            if (inventory.InstallationId != expectedInstallationId) throw Scope();
            if (inventory.ManifestSha256 != expectedManifestSha256 || inventory.DumpSha256 != expectedDumpSha256
                || inventory.EnvelopeSha256 != expectedEnvelopeSha256) throw Integrity();
            return inventory;
        }
        catch (JsonException) { throw Invalid(); }
    }

    // Completeness is explicit: an empty list does not imply a complete retained-backup catalog.
    internal static MfaKeyRetentionDecision EvaluateCandidate(byte[] ringJson, Guid expectedInstallationId,
        MfaFactorVersionInventory factors, IEnumerable<MfaBackupKeyInventory> backups, bool backupCatalogComplete, int candidateVersion)
    {
        if (!VersionValid(candidateVersion) || expectedInstallationId == Guid.Empty || factors is null || backups is null)
            return MfaKeyRetentionDecision.InvalidInput;
        if (!backupCatalogComplete) return MfaKeyRetentionDecision.CatalogIncomplete;
        try
        {
            if (ringJson is null) return MfaKeyRetentionDecision.InvalidInput;
            var ring = MfaKeyRing.Parse(ringJson, expectedInstallationId);
            var snapshot = FactorInventory(factors.InstallationId, factors.Entries);
            if (snapshot.InstallationId != expectedInstallationId) return MfaKeyRetentionDecision.ScopeMismatch;
            var ringVersions = ring.Entries.Select(entry => entry.Version).ToHashSet();
            if (snapshot.Entries.Where(HasFactors).Any(entry => !ringVersions.Contains(entry.Version)))
                return MfaKeyRetentionDecision.MissingDependency;
            var referencedByBackup = false;
            var backupIds = new HashSet<Guid>();
            foreach (var backup in backups)
            {
                ValidateBackup(backup);
                if (backup.InstallationId != expectedInstallationId) return MfaKeyRetentionDecision.ScopeMismatch;
                if (!backupIds.Add(backup.BackupId)) return MfaKeyRetentionDecision.InvalidInput;
                if (backup.RequiredVersions.Any(version => !ringVersions.Contains(version)))
                    return MfaKeyRetentionDecision.MissingDependency;
                referencedByBackup |= backup.RequiredVersions.Contains(candidateVersion);
            }
            if (!ringVersions.Contains(candidateVersion)) return MfaKeyRetentionDecision.UnknownVersion;
            if (ring.RequireEntry(candidateVersion).State == MfaKeyState.Active) return MfaKeyRetentionDecision.ActiveVersion;
            if (snapshot.Entries.Any(entry => entry.Version == candidateVersion && HasFactors(entry))) return MfaKeyRetentionDecision.FactorReferenced;
            return referencedByBackup ? MfaKeyRetentionDecision.BackupReferenced : MfaKeyRetentionDecision.CandidateUnreferenced;
        }
        catch (MfaKeyRingException error)
        {
            return error.Kind == MfaKeyRingErrorKind.IdentityMismatch ? MfaKeyRetentionDecision.ScopeMismatch : MfaKeyRetentionDecision.InvalidInput;
        }
        catch (MfaKeyRetentionException) { return MfaKeyRetentionDecision.InvalidInput; }
    }

    private static bool HasFactors(MfaKeyVersionCount entry) => entry.Pending != 0 || entry.Active != 0 || entry.Disabled != 0;
    private static int[] Required(IEnumerable<int> factors, int active) => factors.Append(active).Distinct().Order().ToArray();
    private static bool VersionValid(int version) => version is >= 1 and <= 1_000_000;
    private static void RequireId(Guid id) { if (id == Guid.Empty) throw Invalid(); }
    private static void RequireHash(string hash)
    {
        if (hash is null || hash.Length != 64 || hash.Any(c => c is not (>= '0' and <= '9') and not (>= 'a' and <= 'f'))) throw Invalid();
    }
    private static string Hash(byte[] bytes) => Convert.ToHexStringLower(SHA256.HashData(bytes));
    private static MfaKeyRetentionException Invalid() => new("mfa_retention_invalid");
    private static MfaKeyRetentionException Scope() => new("mfa_retention_scope_mismatch");
    private static MfaKeyRetentionException Integrity() => new("mfa_retention_integrity_mismatch");

    private static void ValidateBackup(MfaBackupKeyInventory inventory)
    {
        if (inventory is null) throw Invalid();
        RequireId(inventory.InstallationId); RequireId(inventory.BackupId);
        RequireHash(inventory.ManifestSha256); RequireHash(inventory.DumpSha256); RequireHash(inventory.EnvelopeSha256);
        ValidateVersions(inventory.FactorVersions, true);
        ValidateVersions(inventory.EnvelopeVersions, false);
        ValidateVersions(inventory.RequiredVersions, false);
        if (!VersionValid(inventory.EnvelopeActiveVersion) || !inventory.EnvelopeVersions.Contains(inventory.EnvelopeActiveVersion)
            || !inventory.RequiredVersions.SequenceEqual(Required(inventory.FactorVersions, inventory.EnvelopeActiveVersion))
            || inventory.RequiredVersions.Any(version => !inventory.EnvelopeVersions.Contains(version))) throw Invalid();
    }
    private static void ValidateVersions(IReadOnlyList<int> versions, bool allowEmpty)
    {
        if (versions is null || versions.Count > MfaKeyRing.MaxVersions || (!allowEmpty && versions.Count == 0)) throw Invalid();
        var previous = 0;
        foreach (var version in versions)
        {
            if (!VersionValid(version) || version <= previous) throw Invalid();
            previous = version;
        }
    }
    private static string String(JsonElement root, string name)
    {
        var value = root.GetProperty(name);
        if (value.ValueKind != JsonValueKind.String) throw Invalid();
        // JsonDocument puede conservar escapes sin pareja que sólo fallan al materializar el string.
        try { return value.GetString()!; }
        catch (InvalidOperationException) { throw Invalid(); }
    }
    private static string PropertyName(JsonProperty property)
    {
        // Acotar la traducción al acceso que decodifica Unicode; no ocultar fallos ajenos del parser.
        try { return property.Name; }
        catch (InvalidOperationException) { throw Invalid(); }
    }
    private static int Int(JsonElement root, string name)
    {
        var value = root.GetProperty(name);
        if (value.ValueKind != JsonValueKind.Number || !value.TryGetInt32(out var number)) throw Invalid();
        return number;
    }
    private static Guid Id(JsonElement root, string name)
    {
        if (!Guid.TryParseExact(String(root, name), "D", out var id) || id == Guid.Empty) throw Invalid();
        return id;
    }
    private static int[] Versions(JsonElement root, string name, bool allowEmpty)
    {
        var array = root.GetProperty(name);
        if (array.ValueKind != JsonValueKind.Array || array.GetArrayLength() > MfaKeyRing.MaxVersions) throw Invalid();
        var versions = new List<int>();
        foreach (var value in array.EnumerateArray())
        {
            if (value.ValueKind != JsonValueKind.Number || !value.TryGetInt32(out var version)) throw Invalid();
            versions.Add(version);
        }
        var copy = versions.ToArray();
        ValidateVersions(copy, allowEmpty);
        return copy;
    }
    private static void WriteVersions(Utf8JsonWriter writer, string name, IEnumerable<int> versions)
    {
        writer.WriteStartArray(name);
        foreach (var version in versions) writer.WriteNumberValue(version);
        writer.WriteEndArray();
    }
}
