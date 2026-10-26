using System.Text;
using RackClick.Server;
using Xunit;

namespace RackClick.Quality.Tests;

// Formato y coherencia del anillo de claves TOTP (MFA-L2): sin DPAPI ni sistema de archivos, en cualquier plataforma.
public sealed class MfaKeyRingTests
{
    private static readonly Guid Installation = Guid.Parse("6f1c3c2e-9d4b-4e0a-8a55-2d7b9f0c1e11");
    private static readonly Guid OtherInstallation = Guid.Parse("0b9e5a7c-3f21-4d6e-9c08-7a4f2e1d3b22");

    [Fact]
    public void ValidRingParsesWithOneActiveVersionSortedByVersion()
    {
        var ring = MfaKeyRing.Parse(
            Encoding.UTF8.GetBytes(MfaKeyJson.Ring(Installation, MfaKeyJson.Entry(2, "active", "2026-10-25T10:00:00Z") + "," +
                                                  MfaKeyJson.Entry(1, "retired", "2026-10-01T08:30:00Z"))),
            Installation);

        Assert.Equal(Installation, ring.InstallationId);
        Assert.Equal(new[] { 1, 2 }, ring.Entries.Select(e => e.Version));
        Assert.Equal(MfaKeyState.Retired, ring.RequireEntry(1).State);
        Assert.Equal(MfaKeyState.Active, ring.RequireEntry(2).State);
        Assert.Equal(new DateTimeOffset(2026, 10, 25, 10, 0, 0, TimeSpan.Zero), ring.RequireEntry(2).CreatedAtUtc);
    }

    [Fact]
    public void RingFromAnotherInstallationIsIdentityMismatch()
    {
        var error = Assert.Throws<MfaKeyRingException>(() =>
            MfaKeyRing.Parse(MfaKeyJson.Bytes(MfaKeyJson.Ring(OtherInstallation, MfaKeyJson.Entry(1, "active"))), Installation));

        Assert.Equal(MfaKeyRingErrorKind.IdentityMismatch, error.Kind);
    }

    [Fact]
    public void RingWithForeignStructureIsInvalidFormat()
    {
        var active = MfaKeyJson.Entry(1, "active");
        var cases = new[]
        {
            MfaKeyJson.Ring(Installation, active).Replace("\"versions\"", "\"versiones\""),
            MfaKeyJson.Ring(Installation, active).Insert(1, "\"extra\":1,"),
            MfaKeyJson.Ring(Installation, active, format: "RackClick.Otro"),
            MfaKeyJson.Ring(Installation, active, formatVersion: "2"),
            "{\"format\":\"RackClick.MfaKeyRing\",\"format\":\"RackClick.MfaKeyRing\",\"formatVersion\":1,\"installationId\":\"" +
                Installation.ToString("D") + "\",\"versions\":[" + active + "]}",
            "[" + active + "]",
            MfaKeyJson.Ring(Installation, ""),
            MfaKeyJson.Ring(Installation, active + "," + MfaKeyJson.Entry(1, "retired")),
            MfaKeyJson.Ring(Installation, active + "," + MfaKeyJson.Entry(2, "active")),
            MfaKeyJson.Ring(Installation, MfaKeyJson.Entry(1, "retired")),
            MfaKeyJson.Ring(Installation, MfaKeyJson.Entry(1, "activa")),
            MfaKeyJson.Ring(Installation, MfaKeyJson.Entry(0, "active")),
            MfaKeyJson.Ring(Installation, MfaKeyJson.Entry(1, "active", "2026-10-25 10:00:00")),
        };

        foreach (var json in cases)
        {
            var error = Assert.Throws<MfaKeyRingException>(() => MfaKeyRing.Parse(MfaKeyJson.Bytes(json), Installation));
            Assert.Equal(MfaKeyRingErrorKind.InvalidFormat, error.Kind);
        }
    }

    [Fact]
    public void DeepNestingIsRejectedBeforeAnyFieldIsRead()
    {
        var deep = "{\"x\":" + new string('[', 40) + new string(']', 40) + "}";

        var error = Assert.Throws<MfaKeyRingException>(() => MfaKeyRing.Parse(MfaKeyJson.Bytes(deep), Installation));

        Assert.Equal(MfaKeyRingErrorKind.InvalidFormat, error.Kind);
    }

    [Fact]
    public void OversizedRingIsRejectedBeforeParsing()
    {
        var padded = new string(' ', MfaKeyRing.MaxRingFileBytes) + MfaKeyJson.Ring(Installation, MfaKeyJson.Entry(1, "active"));

        var error = Assert.Throws<MfaKeyRingException>(() => MfaKeyRing.Parse(MfaKeyJson.Bytes(padded), Installation));

        Assert.Equal(MfaKeyRingErrorKind.FileTooLarge, error.Kind);
    }

    [Fact]
    public void ByteOrderMarkEmptyFileAndInvalidUtf8AreInvalidFormat()
    {
        var json = MfaKeyJson.Bytes(MfaKeyJson.Ring(Installation, MfaKeyJson.Entry(1, "active")));
        var withBom = new byte[] { 0xEF, 0xBB, 0xBF }.Concat(json).ToArray();
        var cases = new[] { withBom, Array.Empty<byte>(), new byte[] { 0x7B, 0xFF, 0x7D } };

        foreach (var bytes in cases)
        {
            var error = Assert.Throws<MfaKeyRingException>(() => MfaKeyRing.Parse(bytes, Installation));
            Assert.Equal(MfaKeyRingErrorKind.InvalidFormat, error.Kind);
        }
    }

    [Fact]
    public void UnknownVersionIsExplicit()
    {
        var ring = MfaKeyRing.Parse(MfaKeyJson.Bytes(MfaKeyJson.Ring(Installation, MfaKeyJson.Entry(1, "active"))), Installation);

        var error = Assert.Throws<MfaKeyRingException>(() => ring.RequireEntry(2));

        Assert.Equal(MfaKeyRingErrorKind.UnknownVersion, error.Kind);
    }

    [Fact]
    public void ValidKeyFileKeepsItsProtectedBlobUntilTheProviderOpensIt()
    {
        var blob = new byte[] { 1, 2, 3, 4 };

        var file = MfaKeyRing.ParseKeyFile(MfaKeyJson.Bytes(MfaKeyJson.Key(Installation, 2, Convert.ToBase64String(blob))), Installation, 2);

        Assert.Equal(Installation, file.InstallationId);
        Assert.Equal(2, file.KeyVersion);
        Assert.Equal(blob, file.ProtectedKey);
        Assert.Equal("key-v2.dpapi.json", MfaKeyRing.KeyFileName(2));
    }

    [Fact]
    public void KeyFileWithWrongVersionUnknownProtectionOrBadBlobIsRejected()
    {
        var blob = Convert.ToBase64String(new byte[] { 1, 2, 3 });

        var declaresOtherVersion = Assert.Throws<MfaKeyRingException>(() =>
            MfaKeyRing.ParseKeyFile(MfaKeyJson.Bytes(MfaKeyJson.Key(Installation, 1, blob)), Installation, 2));
        Assert.Equal(MfaKeyRingErrorKind.Corrupt, declaresOtherVersion.Kind);

        var otherInstallation = Assert.Throws<MfaKeyRingException>(() =>
            MfaKeyRing.ParseKeyFile(MfaKeyJson.Bytes(MfaKeyJson.Key(OtherInstallation, 2, blob)), Installation, 2));
        Assert.Equal(MfaKeyRingErrorKind.IdentityMismatch, otherInstallation.Kind);

        var badProtection = MfaKeyJson.Key(Installation, 2, blob).Replace("DPAPI-LocalMachine", "DPAPI-CurrentUser");
        Assert.Equal(MfaKeyRingErrorKind.InvalidFormat,
            Assert.Throws<MfaKeyRingException>(() => MfaKeyRing.ParseKeyFile(MfaKeyJson.Bytes(badProtection), Installation, 2)).Kind);

        var tooLong = Convert.ToBase64String(new byte[MfaKeyRing.MaxProtectedKeyBytes + 1]);
        foreach (var protectedKey in new[] { "", "%%%", tooLong })
        {
            var error = Assert.Throws<MfaKeyRingException>(() =>
                MfaKeyRing.ParseKeyFile(MfaKeyJson.Bytes(MfaKeyJson.Key(Installation, 2, protectedKey)), Installation, 2));
            Assert.Equal(MfaKeyRingErrorKind.InvalidFormat, error.Kind);
        }
    }

    [Fact]
    public void EntropyDiffersByInstallationAndVersion()
    {
        var baseline = MfaKeyRing.EntropyFor(Installation, 1);

        Assert.Equal(baseline, MfaKeyRing.EntropyFor(Installation, 1));
        Assert.NotEqual(baseline, MfaKeyRing.EntropyFor(Installation, 2));
        Assert.NotEqual(baseline, MfaKeyRing.EntropyFor(OtherInstallation, 1));
    }
}

// Constructores JSON compartidos por las pruebas del anillo y del proveedor. Sólo producen texto de prueba.
internal static class MfaKeyJson
{
    public static byte[] Bytes(string text) => Encoding.UTF8.GetBytes(text);

    public static string Entry(int version, string state, string createdAt = "2026-10-25T10:00:00Z") =>
        "{\"version\":" + version + ",\"state\":\"" + state + "\",\"createdAtUtc\":\"" + createdAt + "\"}";

    public static string Ring(Guid installation, string versions, string format = "RackClick.MfaKeyRing", string formatVersion = "1") =>
        "{\"format\":\"" + format + "\",\"formatVersion\":" + formatVersion + ",\"installationId\":\"" + installation.ToString("D") +
        "\",\"versions\":[" + versions + "]}";

    public static string Key(Guid installation, int keyVersion, string protectedKey, string protection = "DPAPI-LocalMachine") =>
        "{\"format\":\"RackClick.MfaKeyFile\",\"formatVersion\":1,\"installationId\":\"" + installation.ToString("D") +
        "\",\"keyVersion\":" + keyVersion + ",\"protection\":\"" + protection + "\",\"protectedKey\":\"" + protectedKey + "\"}";
}
