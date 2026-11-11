using System.Security.Cryptography;
using System.Text;
using System.Text.Json.Nodes;
using RackClick.Server;
using Xunit;

namespace RackClick.Quality.Tests;

// F06.02: sólo datos sintéticos y memoria. No DPAPI, DB, archivos del usuario o writer.
public sealed class MfaKeyRetentionTests
{
    private static readonly Guid Installation = Guid.Parse("680bd39a-ed4c-4e5d-8e7d-d3a8a349d971");
    private static readonly Guid Other = Guid.Parse("7bc3d242-b631-4bb1-a64e-db261c2b2dc8");
    private static readonly Guid BackupId = Guid.Parse("e1724f30-87fe-4ea1-91b0-593ca888c4cd");
    private const string Password = "clave-sintetica-pruebas-larga";
    private static readonly string ManifestHash = new('a', 64);
    private static readonly string DumpHash = new('b', 64);

    [Fact]
    public void FactorSnapshotIsCopiedSortedAndImmutable()
    {
        var source = new[] { new MfaKeyVersionCount(7, 1, 2, 3), new MfaKeyVersionCount(1, 4, 5, 6) };
        var inventory = MfaKeyRetention.FactorInventory(Installation, source);
        source[0] = new MfaKeyVersionCount(8, 0, 0, 0);
        Assert.Equal(Installation, inventory.InstallationId);
        Assert.Equal(new[] { 1, 7 }, inventory.Entries.Select(entry => entry.Version));
        Assert.Equal(new MfaKeyVersionCount(7, 1, 2, 3), inventory.Entries[1]);
        Assert.Throws<NotSupportedException>(() => ((IList<MfaKeyVersionCount>)inventory.Entries)[0] = source[0]);
    }

    [Theory]
    [InlineData(0, 0, 0, 0)]
    [InlineData(1000001, 0, 0, 0)]
    [InlineData(1, -1, 0, 0)]
    [InlineData(1, 0, -1, 0)]
    [InlineData(1, 0, 0, -1)]
    [InlineData(1, long.MaxValue, 1, 0)]
    public void InvalidCountsAndOverflowAreRejected(int version, long pending, long active, long disabled) =>
        Assert.Throws<MfaKeyRetentionException>(() => MfaKeyRetention.FactorInventory(Installation,
            new[] { new MfaKeyVersionCount(version, pending, active, disabled) }));

    [Fact]
    public void InvalidFactorScopeDuplicatesNullAndQuotaAreRejected()
    {
        Assert.Empty(Factors().Entries);
        Assert.Throws<MfaKeyRetentionException>(() => MfaKeyRetention.FactorInventory(Guid.Empty, []));
        Assert.Throws<MfaKeyRetentionException>(() => MfaKeyRetention.FactorInventory(Installation, null!));
        Assert.Throws<MfaKeyRetentionException>(() => MfaKeyRetention.FactorInventory(Installation, [null!]));
        Assert.Throws<MfaKeyRetentionException>(() => MfaKeyRetention.FactorInventory(Installation,
            [new(1, 0, 0, 0), new(1, 1, 0, 0)]));
        Assert.Equal(64, MfaKeyRetention.FactorInventory(Installation,
            Enumerable.Range(1, 64).Select(v => new MfaKeyVersionCount(v, 0, 1, 0))).Entries.Count);
        Assert.Throws<MfaKeyRetentionException>(() => MfaKeyRetention.FactorInventory(Installation,
            Enumerable.Range(1, 65).Select(v => new MfaKeyVersionCount(v, 0, 1, 0))));
    }

    [Fact]
    public void AuthenticatedSyntheticEnvelopeReturnsOnlyVersionMetadataAndHash()
    {
        var envelope = Envelope();
        var inspected = MfaKeyRetention.InspectEnvelope(envelope, Password, Installation);
        Assert.Equal(Installation, inspected.InstallationId);
        Assert.Equal(new[] { 1, 2, 7 }, inspected.Versions);
        Assert.Equal(7, inspected.ActiveVersion);
        Assert.Equal(Hash(envelope), inspected.EnvelopeSha256);
        Assert.Throws<NotSupportedException>(() => ((IList<int>)inspected.Versions)[0] = 9);
        envelope[100] ^= 1;
        Assert.Equal(new[] { 1, 2, 7 }, inspected.Versions);
    }

    [Theory]
    [InlineData("password")]
    [InlineData("scope")]
    [InlineData("tamper")]
    [InlineData("invalid-payload")]
    public void EnvelopeNegativesReturnClosedErrorWithoutSensitiveInput(string kind)
    {
        var envelope = kind == "invalid-payload" ? MfaKeyRecoveryEnvelope.Seal(Password, "invalid-payload"u8.ToArray()) : Envelope();
        if (kind == "tamper") envelope[100] ^= 1;
        var error = Assert.Throws<MfaKeyRetentionException>(() => MfaKeyRetention.InspectEnvelope(envelope,
            kind == "password" ? "contraseña-sintetica-incorrecta" : Password, kind == "scope" ? Other : Installation));
        Assert.Equal("mfa_retention_envelope_rejected", error.Message);
        Assert.Null(error.InnerException);
    }

    [Fact]
    public void CanonicalBackupRequiresFactorVersionsAndEnvelopeActiveEvenWithNoFactors()
    {
        var inspected = Inspect();
        var backup = MfaKeyRetention.CreateBackupInventory(BackupId, Factors(new MfaKeyVersionCount(2, 0, 0, 1)), inspected, ManifestHash, DumpHash);
        Assert.Equal(new[] { 2 }, backup.FactorVersions);
        Assert.Equal(new[] { 2, 7 }, backup.RequiredVersions);
        Assert.Equal(new[] { 1, 2, 7 }, backup.EnvelopeVersions);
        var bytes = MfaKeyRetention.SerializeBackupInventory(backup);
        Assert.Equal(bytes, MfaKeyRetention.SerializeBackupInventory(Parse(bytes, inspected)));
        Assert.Equal(new[] { 7 }, MfaKeyRetention.CreateBackupInventory(BackupId, Factors(), inspected, ManifestHash, DumpHash).RequiredVersions);
        Assert.Throws<NotSupportedException>(() => ((IList<int>)backup.RequiredVersions)[0] = 9);
        Assert.Throws<MfaKeyRetentionException>(() => MfaKeyRetention.CreateBackupInventory(BackupId, Factors(new MfaKeyVersionCount(3, 1, 0, 0)), inspected, ManifestHash, DumpHash));
        Assert.Throws<MfaKeyRetentionException>(() => MfaKeyRetention.CreateBackupInventory(Guid.Empty, Factors(), inspected, ManifestHash, DumpHash));
        Assert.Throws<MfaKeyRetentionException>(() => MfaKeyRetention.CreateBackupInventory(BackupId, MfaKeyRetention.FactorInventory(Other, []), inspected, ManifestHash, DumpHash));
    }

    [Theory]
    [InlineData("extra")]
    [InlineData("duplicate")]
    [InlineData("null")]
    [InlineData("wrong-type")]
    [InlineData("empty-uuid")]
    [InlineData("bad-uuid")]
    [InlineData("format-version")]
    [InlineData("bad-format")]
    [InlineData("uppercase-hash")]
    [InlineData("short-hash")]
    [InlineData("unsorted")]
    [InlineData("duplicate-version")]
    [InlineData("range-zero")]
    [InlineData("range-max")]
    [InlineData("quota")]
    [InlineData("missing-active")]
    [InlineData("missing-required")]
    [InlineData("extra-required")]
    [InlineData("uncovered-factor")]
    [InlineData("omit-field")]
    [InlineData("too-large")]
    [InlineData("invalid-json")]
    public void StrictParserRejectsMalformedMetadataEvenWithMatchingExternalHash(string shape)
    {
        var inspected = Inspect();
        var root = JsonNode.Parse(MfaKeyRetention.SerializeBackupInventory(Backup(inspected)))!.AsObject();
        switch (shape)
        {
            case "extra": root["injected-secret"] = "injected-secret"; break;
            case "null": root["factorVersions"] = null; break;
            case "wrong-type": root["envelopeActiveVersion"] = "7"; break;
            case "empty-uuid": root["backupId"] = Guid.Empty.ToString(); break;
            case "bad-uuid": root["backupId"] = "not-an-id"; break;
            case "format-version": root["formatVersion"] = 2; break;
            case "bad-format": root["format"] = "injected-secret"; break;
            case "uppercase-hash": root["manifestSha256"] = ManifestHash.ToUpperInvariant(); break;
            case "short-hash": root["dumpSha256"] = "abc"; break;
            case "unsorted": root["envelopeVersions"] = new JsonArray(2, 1, 7); break;
            case "duplicate-version": root["envelopeVersions"] = new JsonArray(1, 1, 7); break;
            case "range-zero": root["factorVersions"] = new JsonArray(0); break;
            case "range-max": root["factorVersions"] = new JsonArray(1000001); break;
            case "quota": root["envelopeVersions"] = new JsonArray(Enumerable.Range(1, 65).Select(v => JsonValue.Create(v) as JsonNode).ToArray()); break;
            case "missing-active": root["envelopeActiveVersion"] = 3; break;
            case "missing-required": root["requiredVersions"] = new JsonArray(2); break;
            case "extra-required": root["requiredVersions"] = new JsonArray(1, 2, 7); break;
            case "uncovered-factor": root["factorVersions"] = new JsonArray(3); root["requiredVersions"] = new JsonArray(3, 7); break;
            case "omit-field": root.Remove("factorVersions"); break;
        }
        var text = root.ToJsonString();
        if (shape == "duplicate") text = text.Insert(1, "\"backupId\":\"" + BackupId + "\",");
        if (shape == "too-large") text += new string(' ', 65536);
        if (shape == "invalid-json") text = "{invalid";
        var bytes = Encoding.UTF8.GetBytes(text);
        var error = Assert.Throws<MfaKeyRetentionException>(() => Parse(bytes, inspected));
        Assert.StartsWith("mfa_retention_", error.Message);
        Assert.DoesNotContain("injected-secret", error.Message);
        Assert.Null(error.InnerException);
    }

    [Theory]
    [InlineData("inventory")]
    [InlineData("manifest")]
    [InlineData("dump")]
    [InlineData("envelope")]
    [InlineData("installation")]
    public void ExternalPinsAndScopeMustMatch(string pin)
    {
        var inspected = Inspect();
        var bytes = MfaKeyRetention.SerializeBackupInventory(Backup(inspected));
        Assert.Throws<MfaKeyRetentionException>(() => MfaKeyRetention.ParseBackupInventory(bytes,
            pin == "installation" ? Other : Installation, pin == "inventory" ? new string('c', 64) : Hash(bytes),
            pin == "manifest" ? new string('c', 64) : ManifestHash,
            pin == "dump" ? new string('c', 64) : DumpHash,
            pin == "envelope" ? new string('c', 64) : inspected.EnvelopeSha256));
    }

    [Theory]
    [InlineData("unpaired-name")]
    [InlineData("unpaired-installation")]
    [InlineData("unpaired-hash")]
    [InlineData("supplementary-name")]
    [InlineData("supplementary-hash")]
    public void UnicodeEscapesRejectWithClosedErrorIncludingUnpairedSurrogates(string shape)
    {
        var inspected = Inspect();
        var text = Encoding.UTF8.GetString(MfaKeyRetention.SerializeBackupInventory(Backup(inspected)));
        text = shape switch
        {
            "unpaired-name" => text.Insert(1, "\"\\uD800\":1,"),
            "unpaired-installation" => text.Replace(Installation.ToString("D"), "\\uDC00", StringComparison.Ordinal),
            "unpaired-hash" => text.Replace(DumpHash, "\\uDC00", StringComparison.Ordinal),
            "supplementary-name" => text.Insert(1, "\"\\uD83D\\uDE00\":1,"),
            "supplementary-hash" => text.Replace(DumpHash, "\\uD83D\\uDE00", StringComparison.Ordinal),
            _ => throw new ArgumentOutOfRangeException(nameof(shape)),
        };
        var bytes = Encoding.UTF8.GetBytes(text);
        // Se enlazan deliberadamente los bytes de este negativo, para alcanzar al lector JSON y no sólo al pin.
        var error = Assert.Throws<MfaKeyRetentionException>(() => Parse(bytes, inspected));
        Assert.Equal("mfa_retention_invalid", error.Message);
        Assert.Null(error.InnerException);
    }

    [Fact]
    public void RemovingFactorAndRequiredVersionsCannotReplaceOriginalTrustedPin()
    {
        var inspected = Inspect();
        var original = MfaKeyRetention.SerializeBackupInventory(Backup(inspected));
        var modified = JsonNode.Parse(original)!.AsObject();
        modified["factorVersions"] = new JsonArray();
        modified["requiredVersions"] = new JsonArray(7);
        var bytes = Encoding.UTF8.GetBytes(modified.ToJsonString());
        Assert.NotEqual(Hash(original), Hash(bytes));
        Assert.Throws<MfaKeyRetentionException>(() => MfaKeyRetention.ParseBackupInventory(bytes, Installation,
            Hash(original), ManifestHash, DumpHash, inspected.EnvelopeSha256));
        // Un pin nuevo suministrado por el llamador haría válido el contenido: el almacén de confianza externo es esencial.
        Assert.Empty(Parse(bytes, inspected).FactorVersions);
    }

    [Theory]
    [InlineData(1, 0, 0)]
    [InlineData(0, 1, 0)]
    [InlineData(0, 0, 1)]
    public void EveryFactorStateKeepsItsVersion(long pending, long active, long disabled) =>
        Assert.Equal(MfaKeyRetentionDecision.FactorReferenced, Decide(2, Factors(new MfaKeyVersionCount(2, pending, active, disabled))));

    [Fact]
    public void GuardBlocksActiveUnknownCatalogScopeMissingDependenciesAndOldBackups()
    {
        Assert.Equal(MfaKeyRetentionDecision.CandidateUnreferenced, Decide(1));
        Assert.Equal(MfaKeyRetentionDecision.ActiveVersion, Decide(7));
        Assert.Equal(MfaKeyRetentionDecision.UnknownVersion, Decide(3));
        Assert.Equal(MfaKeyRetentionDecision.InvalidInput, Decide(0));
        Assert.Equal(MfaKeyRetentionDecision.CatalogIncomplete, Decide(1, complete: false));
        Assert.Equal(MfaKeyRetentionDecision.ScopeMismatch, Decide(1, MfaKeyRetention.FactorInventory(Other, [])));
        Assert.Equal(MfaKeyRetentionDecision.MissingDependency, Decide(1, Factors(new MfaKeyVersionCount(3, 1, 0, 0))));
        var inspected = Inspect();
        Assert.Equal(MfaKeyRetentionDecision.BackupReferenced, Decide(2, backups: [Backup(inspected)]));
        // La activa de un sobre histórico queda protegida aunque el anillo vivo tenga otra activa y el backup no tenga factores.
        var historical = MfaKeyRetention.InspectEnvelope(Envelope(active: 2), Password, Installation);
        var oldBackup = MfaKeyRetention.CreateBackupInventory(BackupId, Factors(), historical, ManifestHash, DumpHash);
        Assert.Equal(MfaKeyRetentionDecision.BackupReferenced, Decide(2, backups: [oldBackup]));
        var foreign = MfaKeyRetention.InspectEnvelope(Envelope(installation: Other), Password, Other);
        var foreignBackup = MfaKeyRetention.CreateBackupInventory(BackupId, MfaKeyRetention.FactorInventory(Other, []), foreign, ManifestHash, DumpHash);
        Assert.Equal(MfaKeyRetentionDecision.ScopeMismatch, Decide(1, backups: [foreignBackup]));
        var missing = MfaKeyRetention.InspectEnvelope(Envelope(active: 3, versions: [1, 3]), Password, Installation);
        Assert.Equal(MfaKeyRetentionDecision.MissingDependency, Decide(1, backups:
            [MfaKeyRetention.CreateBackupInventory(BackupId, Factors(), missing, ManifestHash, DumpHash)]));
        Assert.Equal(MfaKeyRetentionDecision.InvalidInput, Decide(1, backups: [null!]));
        Assert.Equal(MfaKeyRetentionDecision.InvalidInput, MfaKeyRetention.EvaluateCandidate("{}"u8.ToArray(), Installation, Factors(), [], true, 1));
    }

    private static MfaFactorVersionInventory Factors(params MfaKeyVersionCount[] entries) => MfaKeyRetention.FactorInventory(Installation, entries);
    private static MfaEnvelopeVersionInventory Inspect() => MfaKeyRetention.InspectEnvelope(Envelope(), Password, Installation);
    private static MfaBackupKeyInventory Backup(MfaEnvelopeVersionInventory inspected) =>
        MfaKeyRetention.CreateBackupInventory(BackupId, Factors(new MfaKeyVersionCount(2, 0, 1, 0)), inspected, ManifestHash, DumpHash);
    private static MfaBackupKeyInventory Parse(byte[] bytes, MfaEnvelopeVersionInventory inspected) =>
        MfaKeyRetention.ParseBackupInventory(bytes, Installation, Hash(bytes), ManifestHash, DumpHash, inspected.EnvelopeSha256);
    private static MfaKeyRetentionDecision Decide(int candidate, MfaFactorVersionInventory? factors = null,
        IEnumerable<MfaBackupKeyInventory>? backups = null, bool complete = true) =>
        MfaKeyRetention.EvaluateCandidate(Ring(), Installation, factors ?? Factors(), backups ?? [], complete, candidate);
    private static string Hash(byte[] bytes) => Convert.ToHexStringLower(SHA256.HashData(bytes));
    private static byte[] Ring(Guid? installation = null, int active = 7, int[]? versions = null) =>
        Encoding.UTF8.GetBytes(MfaKeyJson.Ring(installation ?? Installation, string.Join(",", (versions ?? [1, 2, 7])
            .Select(v => MfaKeyJson.Entry(v, v == active ? "active" : "retired")))));
    private static byte[] Envelope(Guid? installation = null, int active = 7, int[]? versions = null)
    {
        var keys = (versions ?? [1, 2, 7]).Select(v => (Version: v, Key: RandomNumberGenerator.GetBytes(32))).ToArray();
        try
        {
            using var buffer = MfaKeyRecoveryPayload.Serialize(Ring(installation, active, versions), installation ?? Installation, keys);
            return MfaKeyRecoveryEnvelope.Seal(Password, buffer.Bytes);
        }
        finally { foreach (var key in keys) CryptographicOperations.ZeroMemory(key.Key); }
    }
}
