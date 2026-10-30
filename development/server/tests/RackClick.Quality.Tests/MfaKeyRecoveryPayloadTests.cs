using System.Security.Cryptography;
using System.Text;
using RackClick.Server;
using Xunit;

namespace RackClick.Quality.Tests;

// Contenido portable del sobre de recuperación (MFA-L2e): sólo memoria, datos y claves sintéticas nuevas en cada prueba.
// Las igualdades de claves usan igualdad constante; las aserciones no muestran bytes. El sellado con L2d se ejercita en
// round-trip completo, con la contraseña de laboratorio de estas pruebas.
public sealed class MfaKeyRecoveryPayloadTests
{
    private static readonly Guid Origin = Guid.Parse("8c2a7d10-4e3b-4f6a-9b21-5d0e7c3a9f42");
    private static readonly Guid Other = Guid.Parse("1e5f9a33-6b7c-4d2e-8f10-3a4b5c6d7e8f");
    private const string Password = "clave-de-prueba-larga";

    [Fact]
    public void RoundTripKeepsIdsDatesVersionsStatesAndKeyBytes()
    {
        var keys = NewKeys(1, 2);
        using var buffer = MfaKeyRecoveryPayload.Serialize(TwoVersionRing(), Origin, keys);
        using var content = MfaKeyRecoveryPayload.Deserialize(buffer.Bytes, Origin);

        Assert.Equal(Origin, content.Ring.InstallationId);
        Assert.Equal(new[] { 1, 2 }, content.Ring.Entries.Select(entry => entry.Version));
        Assert.Equal(MfaKeyState.Retired, content.Ring.Entries[0].State);
        Assert.Equal(MfaKeyState.Active, content.Ring.Entries[1].State);
        Assert.Equal(new DateTimeOffset(2026, 10, 1, 8, 30, 0, TimeSpan.Zero), content.Ring.Entries[0].CreatedAtUtc);
        Assert.Equal(new DateTimeOffset(2026, 10, 25, 10, 0, 0, TimeSpan.Zero), content.Ring.Entries[1].CreatedAtUtc);
        foreach (var (version, key) in keys)
            Assert.True(CryptographicOperations.FixedTimeEquals(key, content.KeyFor(version)), "la clave recuperada no coincide");
    }

    [Fact]
    public void SerializationIsDeterministicAcrossWhitespaceAndKeyOrder()
    {
        var compact = TwoVersionRing();
        var spaced = Encoding.UTF8.GetBytes(Encoding.UTF8.GetString(compact)
            .Replace("{\"", "{\n  \"", StringComparison.Ordinal)
            .Replace(",\"", ",\n  \"", StringComparison.Ordinal));
        var keys = NewKeys(1, 2);
        var reversed = keys.AsEnumerable().Reverse().ToList();

        using var first = MfaKeyRecoveryPayload.Serialize(compact, Origin, keys);
        using var second = MfaKeyRecoveryPayload.Serialize(spaced, Origin, reversed);

        Assert.Equal(first.Bytes.Length, second.Bytes.Length);
        Assert.True(CryptographicOperations.FixedTimeEquals(first.Bytes, second.Bytes), "el mismo contenido produjo bytes distintos");
    }

    [Fact]
    public void CallerKeysAreNotModifiedOrZeroedBySerialization()
    {
        var keys = NewKeys(1, 2);
        var copies = keys.Select(key => (Version: key.Version, Key: (byte[])key.Key.Clone())).ToArray();

        using (MfaKeyRecoveryPayload.Serialize(TwoVersionRing(), Origin, keys))
        {
        }

        for (var i = 0; i < keys.Count; i++)
            Assert.True(CryptographicOperations.FixedTimeEquals(keys[i].Key, copies[i].Key), "la entrada del llamador cambió");
    }

    [Fact]
    public void BufferAndContentZeroTheirOwnArraysOnDispose()
    {
        var buffer = MfaKeyRecoveryPayload.Serialize(TwoVersionRing(), Origin, NewKeys(1, 2));
        var payloadArray = buffer.Bytes;
        buffer.Dispose();
        Assert.True(AllZero(payloadArray), "el contenedor no puso a cero su arreglo");

        var content = MfaKeyRecoveryPayload.Deserialize(
            MfaKeyRecoveryPayloadWithKeys(), Origin);
        ReadOnlySpan<byte> view = content.KeyFor(1);
        content.Dispose();
        Assert.True(AllZero(view.ToArray()), "el contenido no puso a cero sus claves");
    }

    [Fact]
    public void ToStringDoesNotExposeKeyMaterial()
    {
        var keys = NewKeys(1, 2);
        using var buffer = MfaKeyRecoveryPayload.Serialize(TwoVersionRing(), Origin, keys);
        using var content = MfaKeyRecoveryPayload.Deserialize(buffer.Bytes, Origin);
        var texts = new[] { buffer.ToString(), content.ToString() };

        foreach (var (_, key) in keys)
        {
            var base64 = Convert.ToBase64String(key);
            var hex = Convert.ToHexString(key);
            foreach (var text in texts)
            {
                Assert.False(text.Contains(base64, StringComparison.Ordinal), "ToString expone una clave");
                Assert.False(text.Contains(hex, StringComparison.OrdinalIgnoreCase), "ToString expone una clave");
            }
        }
    }

    [Theory]
    [InlineData("faltan-versiones")]
    [InlineData("versiones-extra")]
    [InlineData("versiones-duplicadas")]
    [InlineData("versiones-desordenadas")]
    [InlineData("clave-de-31-bytes")]
    [InlineData("clave-de-33-bytes")]
    [InlineData("truncado")]
    [InlineData("sobrante")]
    [InlineData("longitud-de-anillo-cero")]
    [InlineData("longitud-de-anillo-desbordada")]
    [InlineData("anillo-mas-largo-que-el-payload")]
    [InlineData("magia-incorrecta")]
    [InlineData("version-desconocida")]
    [InlineData("anillo-con-dos-activas")]
    [InlineData("identidad-de-otra-instalacion")]
    public void StrictAnalysisRejectsMalformedPayloadsWithoutKeyMaterial(string shape)
    {
        var (payload, expected, secret) = MalformedPayload(shape);
        var leaked = Convert.ToBase64String(secret);

        var error = Assert.Throws<MfaKeyRecoveryPayloadException>(() => MfaKeyRecoveryPayload.Deserialize(payload, Origin));

        Assert.Equal(expected, error.Kind);
        Assert.False(error.Message.Contains(leaked, StringComparison.Ordinal), "el error expone una clave");
    }

    [Theory]
    [InlineData("clave-faltante")]
    [InlineData("clave-de-version-ajena")]
    [InlineData("version-duplicada")]
    [InlineData("clave-de-31-bytes")]
    [InlineData("identidad-distinta")]
    public void SerializationRejectsInconsistentInputBeforeProducingAnyPayload(string shape)
    {
        var keys = NewKeys(1, 2).ToList();
        var ring = TwoVersionRing();
        var expectedInstallation = Origin;
        switch (shape)
        {
            case "clave-faltante": keys.RemoveAt(1); break;
            case "clave-de-version-ajena": keys[1] = (3, Key(3)); break;
            case "version-duplicada": keys[1] = (1, Key(9)); break;
            case "clave-de-31-bytes": keys[1] = (2, new byte[31]); break;
            case "identidad-distinta": expectedInstallation = Other; break;
            default: throw new ArgumentOutOfRangeException(nameof(shape), shape, null);
        }

        var error = Assert.Throws<MfaKeyRecoveryPayloadException>(() =>
            MfaKeyRecoveryPayload.Serialize(ring, expectedInstallation, keys));

        var expected = shape == "identidad-distinta"
            ? MfaKeyRecoveryPayloadErrorKind.RingRejected
            : MfaKeyRecoveryPayloadErrorKind.InvalidRequest;
        Assert.Equal(expected, error.Kind);
    }

    [Fact]
    public void SixtyFourVersionsRoundTripAndSixtyFiveAreRejectedByTheParser()
    {
        var entries = Enumerable.Range(1, 64)
            .Select(version => MfaKeyJson.Entry(version, version == 64 ? "active" : "retired", "2026-10-01T08:30:00Z"));
        var ring64 = Encoding.UTF8.GetBytes(MfaKeyJson.Ring(Origin, string.Join(",", entries)));
        var keys = Enumerable.Range(1, 64).Select(version => (version, Key(version))).ToArray();

        using var buffer = MfaKeyRecoveryPayload.Serialize(ring64, Origin, keys);
        using var content = MfaKeyRecoveryPayload.Deserialize(buffer.Bytes, Origin);

        Assert.Equal(Enumerable.Range(1, 64), content.Ring.Entries.Select(entry => entry.Version));
        Assert.True(buffer.Bytes.Length <= MfaKeyRecoveryPayload.MaxPayloadBytes, "el payload supera el límite del sobre");

        var entries65 = Enumerable.Range(1, 65)
            .Select(version => MfaKeyJson.Entry(version, version == 65 ? "active" : "retired", "2026-10-01T08:30:00Z"));
        var ring65 = Encoding.UTF8.GetBytes(MfaKeyJson.Ring(Origin, string.Join(",", entries65)));
        var keys65 = Enumerable.Range(1, 65).Select(version => (version, Key(version))).ToArray();
        var error = Assert.Throws<MfaKeyRecoveryPayloadException>(() => MfaKeyRecoveryPayload.Serialize(ring65, Origin, keys65));
        Assert.Equal(MfaKeyRecoveryPayloadErrorKind.RingRejected, error.Kind);
    }

    [Fact]
    public void SerializedPayloadSurvivesTheL2dSealAndOpenAndAnalyzes()
    {
        var keys = NewKeys(1, 2);
        using var buffer = MfaKeyRecoveryPayload.Serialize(TwoVersionRing(), Origin, keys);
        var envelope = MfaKeyRecoveryEnvelope.Seal(Password, buffer.Bytes);
        var opened = MfaKeyRecoveryEnvelope.Open(Password, envelope);
        try
        {
            using var content = MfaKeyRecoveryPayload.Deserialize(opened, Origin);
            foreach (var (version, key) in keys)
                Assert.True(CryptographicOperations.FixedTimeEquals(key, content.KeyFor(version)), "la clave recuperada no coincide");
        }
        finally
        {
            CryptographicOperations.ZeroMemory(opened);
        }
    }

    [Fact]
    public void WrongPasswordOrAlteredEnvelopeReturnsNoContent()
    {
        using var buffer = MfaKeyRecoveryPayload.Serialize(TwoVersionRing(), Origin, NewKeys(1, 2));
        var envelope = MfaKeyRecoveryEnvelope.Seal(Password, buffer.Bytes);
        var altered = (byte[])envelope.Clone();
        altered[100] ^= 0x01;

        var wrong = Assert.Throws<MfaRecoveryEnvelopeException>(() => MfaKeyRecoveryEnvelope.Open("clave-de-prueba-erronea", envelope));
        var tampered = Assert.Throws<MfaRecoveryEnvelopeException>(() => MfaKeyRecoveryEnvelope.Open(Password, altered));

        Assert.Equal(MfaRecoveryEnvelopeErrorKind.AuthenticationFailed, wrong.Kind);
        Assert.Equal(MfaRecoveryEnvelopeErrorKind.AuthenticationFailed, tampered.Kind);
    }

    // Claves sintéticas nuevas por llamada.
    private static List<(int Version, byte[] Key)> NewKeys(params int[] versions) =>
        versions.Select(version => (Version: version, Key: Key(version))).ToList();

    private static byte[] Key(int version) => RandomNumberGenerator.GetBytes(MfaKeyRing.KeyBytes);

    private static byte[] TwoVersionRing() => Encoding.UTF8.GetBytes(MfaKeyJson.Ring(Origin,
        MfaKeyJson.Entry(1, "retired", "2026-10-01T08:30:00Z") + "," + MfaKeyJson.Entry(2, "active", "2026-10-25T10:00:00Z")));

    // Payload válido de dos versiones con las claves fijas de este método (para pruebas que necesitan un contenido ya construido).
    private static byte[] MfaKeyRecoveryPayloadWithKeys()
    {
        using var buffer = MfaKeyRecoveryPayload.Serialize(TwoVersionRing(), Origin, NewKeys(1, 2));
        return (byte[])buffer.Bytes.Clone();
    }

    private static bool AllZero(byte[] bytes)
    {
        foreach (var value in bytes)
        {
            if (value != 0) return false;
        }
        return true;
    }

    // Payloads malformados construidos byte a byte, sin pasar por Serialize, para que el analizador se pruebe en aislamiento.
    // Devuelve el payload malformado, el fallo esperado y la clave que contiene (para comprobar que el error no la expone).
    private static (byte[] Payload, MfaKeyRecoveryPayloadErrorKind Kind, byte[] Secret) MalformedPayload(string shape)
    {
        var ring = TwoVersionRing();
        var key1 = Key(1);
        var key2 = Key(2);
        var invalid = MfaKeyRecoveryPayloadErrorKind.InvalidFormat;
        var valid = Raw(ring, 2, (1, key1), (2, key2));
        switch (shape)
        {
            case "faltan-versiones":
                return (Raw(ring, 2, (1, key1)), invalid, key1);
            case "versiones-extra":
                return (Raw(ring, 2, (1, key1), (3, key2)), invalid, key1);
            case "versiones-duplicadas":
                return (Raw(ring, 2, (1, key1), (1, key2)), invalid, key1);
            case "versiones-desordenadas":
                return (Raw(ring, 2, (2, key2), (1, key1)), invalid, key1);
            case "clave-de-31-bytes":
                return (RawWithLength(ring, 2, 31, (1, key1), (2, key2)), invalid, key1);
            case "clave-de-33-bytes":
                return (RawWithLength(ring, 2, 33, (1, key1), (2, key2)), invalid, key1);
            case "truncado":
                return (valid.AsSpan(0, valid.Length - 1).ToArray(), invalid, key1);
            case "sobrante":
                return (Concat(valid, new byte[] { 0 }), invalid, key1);
            case "longitud-de-anillo-cero":
                return (WithRingLength(valid, 0), invalid, key1);
            case "longitud-de-anillo-desbordada":
                return (WithRingLength(valid, 0xFFFFFFFF), invalid, key1);
            case "anillo-mas-largo-que-el-payload":
                return (WithRingLength(valid, 60000), invalid, key1);
            case "magia-incorrecta":
            {
                var payload = (byte[])valid.Clone();
                payload[0] = (byte)'X';
                return (payload, invalid, key1);
            }
            case "version-desconocida":
            {
                var payload = (byte[])valid.Clone();
                payload[6] = 2;
                return (payload, MfaKeyRecoveryPayloadErrorKind.UnsupportedVersion, key1);
            }
            case "anillo-con-dos-activas":
            {
                var twoActive = Encoding.UTF8.GetBytes(MfaKeyJson.Ring(Origin,
                    MfaKeyJson.Entry(1, "active", "2026-10-01T08:30:00Z") + "," + MfaKeyJson.Entry(2, "active", "2026-10-25T10:00:00Z")));
                return (Raw(twoActive, 2, (1, key1), (2, key2)), MfaKeyRecoveryPayloadErrorKind.RingRejected, key1);
            }
            case "identidad-de-otra-instalacion":
            {
                var foreign = Encoding.UTF8.GetBytes(MfaKeyJson.Ring(Other,
                    MfaKeyJson.Entry(1, "retired", "2026-10-01T08:30:00Z") + "," + MfaKeyJson.Entry(2, "active", "2026-10-25T10:00:00Z")));
                return (Raw(foreign, 2, (1, key1), (2, key2)), MfaKeyRecoveryPayloadErrorKind.RingRejected, key1);
            }
            default:
                throw new ArgumentOutOfRangeException(nameof(shape), shape, null);
        }
    }

    private static byte[] Raw(byte[] ring, int declaredKeyCount, params (int Version, byte[] Key)[] records) =>
        RawWithLength(ring, declaredKeyCount, MfaKeyRing.KeyBytes, records);

    private static byte[] RawWithLength(byte[] ring, int declaredKeyCount, int keyLength, params (int Version, byte[] Key)[] records)
    {
        using var stream = new MemoryStream();
        stream.Write("RCKPAY"u8);
        stream.WriteByte(1);
        var ringLength = new byte[4];
        System.Buffers.Binary.BinaryPrimitives.WriteUInt32BigEndian(ringLength, (uint)ring.Length);
        stream.Write(ringLength);
        stream.Write(ring);
        stream.WriteByte((byte)declaredKeyCount);
        foreach (var (version, key) in records)
        {
            var versionBytes = new byte[4];
            System.Buffers.Binary.BinaryPrimitives.WriteUInt32BigEndian(versionBytes, (uint)version);
            stream.Write(versionBytes);
            stream.WriteByte((byte)keyLength);
            stream.Write(key);
        }
        return stream.ToArray();
    }

    private static byte[] WithRingLength(byte[] payload, uint ringLength)
    {
        var copy = (byte[])payload.Clone();
        System.Buffers.Binary.BinaryPrimitives.WriteUInt32BigEndian(copy.AsSpan(7, 4), ringLength);
        return copy;
    }

    private static byte[] Concat(byte[] first, byte[] second)
    {
        var result = new byte[first.Length + second.Length];
        first.CopyTo(result, 0);
        second.CopyTo(result, first.Length);
        return result;
    }
}
