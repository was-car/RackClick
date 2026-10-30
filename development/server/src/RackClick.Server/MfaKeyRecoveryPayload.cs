using System.Buffers.Binary;
using System.Globalization;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

namespace RackClick.Server;

// Contenido portable del sobre de recuperación (MFA-L2e): metadatos canónicos del anillo y exactamente una clave de 32 bytes
// por versión. Sólo memoria: el sellado lo hace MfaKeyRecoveryEnvelope (L2d) y la exportación/importación se integra en otro
// lote. Las reglas del anillo las aplica MfaKeyRing.Parse; aquí sólo se valida la forma del contenedor y su coherencia con el anillo.
// Investigación previa: evidence/s1-20261026/mfa-l2e-claude/INVESTIGACION-PREVIA.md.
//
// Formato (enteros big-endian, sin campos opcionales ni desconocidos): magia "RCKPAY" (0-5); versión 1 (6); longitud N del
// anillo canónico, uint32, 1 ≤ N ≤ 65536 (7-10); anillo canónico JSON (11...11+N-1); número de claves K = versiones del anillo,
// un byte (11+N); K registros en orden estrictamente ascendente de versión: versión uint32, longitud 32 (1 byte) y clave (32 bytes).
// Fin exacto: no se admiten bytes sobrantes.
internal static class MfaKeyRecoveryPayload
{
    // Límite fijado por L2d: sobre de 1 MiB menos la cabecera RCKEY v1 de 59 bytes.
    public const int MaxPayloadBytes = 1024 * 1024 - 59;

    private const int MagicLength = 6;
    private const byte FormatVersion = 1;
    private const int RingLengthOffset = MagicLength + 1;
    private const int HeaderBytes = RingLengthOffset + 4;
    private const int KeyRecordBytes = 4 + 1 + MfaKeyRing.KeyBytes;
    private const string CreatedAtFormat = "yyyy-MM-dd'T'HH:mm:ss'Z'";

    private static ReadOnlySpan<byte> Magic => "RCKPAY"u8;

    // Serializa el anillo (validado por MfaKeyRing.Parse y reescrito en forma canónica) y sus claves. Las entradas del llamador no se
    // modifican ni se ponen a cero. El contenedor devuelto contiene claves en claro: el llamador lo desecha al terminar.
    public static MfaKeyRecoveryPayloadBuffer Serialize(byte[] ringJson, Guid expectedInstallationId,
        IReadOnlyList<(int Version, byte[] Key)> keys)
    {
        if (ringJson is null || keys is null) throw Invalid("entrada ausente");
        var ring = ParseRing(ringJson, expectedInstallationId);
        var canonicalRing = CanonicalRingJson(ring);
        if (keys.Count != ring.Entries.Count)
            throw Invalid("el número de claves no coincide con las versiones del anillo");

        var ordered = keys.OrderBy(key => key.Version).ToArray();
        for (var i = 0; i < ordered.Length; i++)
        {
            var (version, key) = ordered[i];
            if (!ring.Entries.Any(entry => entry.Version == version))
                throw Invalid("hay una clave para una versión que no figura en el anillo");
            if (i > 0 && ordered[i - 1].Version == version)
                throw Invalid("hay una versión con más de una clave");
            if (key is null || key.Length != MfaKeyRing.KeyBytes)
                throw Invalid("una clave no mide 32 bytes");
        }

        var total = HeaderBytes + canonicalRing.Length + 1 + ordered.Length * KeyRecordBytes;
        if (total > MaxPayloadBytes)
            throw new MfaKeyRecoveryPayloadException(MfaKeyRecoveryPayloadErrorKind.TooLarge, "el contenido supera el límite del sobre", null);

        var payload = new byte[total];
        try
        {
            Magic.CopyTo(payload);
            payload[MagicLength] = FormatVersion;
            BinaryPrimitives.WriteUInt32BigEndian(payload.AsSpan(RingLengthOffset, 4), (uint)canonicalRing.Length);
            canonicalRing.CopyTo(payload, HeaderBytes);
            var offset = HeaderBytes + canonicalRing.Length;
            payload[offset++] = (byte)ordered.Length;
            foreach (var (version, key) in ordered)
            {
                BinaryPrimitives.WriteUInt32BigEndian(payload.AsSpan(offset, 4), (uint)version);
                payload[offset + 4] = MfaKeyRing.KeyBytes;
                key.CopyTo(payload, offset + 5);
                offset += KeyRecordBytes;
            }
            return new MfaKeyRecoveryPayloadBuffer(payload);
        }
        catch
        {
            // Un fallo a mitad de escritura no deja claves en claro en el arreglo parcial.
            CryptographicOperations.ZeroMemory(payload);
            throw;
        }
    }

    // Analiza un payload en claro con la identidad de origen esperada. Rechaza las formas ilegales antes de reservar memoria.
    // El contenido devuelto contiene copias de las claves: el llamador lo desecha al terminar.
    public static MfaKeyRecoveryContent Deserialize(byte[] payload, Guid expectedInstallationId)
    {
        if (payload is null) throw Invalid("payload ausente");
        if (payload.Length > MaxPayloadBytes)
            throw new MfaKeyRecoveryPayloadException(MfaKeyRecoveryPayloadErrorKind.TooLarge, "el payload supera el límite del sobre", null);
        RequireAvailable(payload, 0, HeaderBytes + 1);
        if (!payload.AsSpan(0, MagicLength).SequenceEqual(Magic))
            throw Format("magia no válida");
        if (payload[MagicLength] != FormatVersion)
            throw new MfaKeyRecoveryPayloadException(MfaKeyRecoveryPayloadErrorKind.UnsupportedVersion, "versión de payload no soportada", null);

        var ringLength = BinaryPrimitives.ReadUInt32BigEndian(payload.AsSpan(RingLengthOffset, 4));
        if (ringLength is 0 or > MfaKeyRing.MaxRingFileBytes)
            throw Format("longitud del anillo fuera de límites");
        // Comprobación en 64 bits antes de cualquier asignación o slice: el anillo y el número de claves deben caber.
        if ((ulong)HeaderBytes + ringLength + 1 > (ulong)payload.Length)
            throw Format("payload truncado");

        var offset = HeaderBytes;
        var ringJson = payload.AsSpan(offset, (int)ringLength).ToArray();
        offset += (int)ringLength;
        var ring = ParseRing(ringJson, expectedInstallationId);

        var keyCount = payload[offset++];
        if (keyCount != ring.Entries.Count)
            throw Format("número de claves distinto de las versiones del anillo");

        var keys = new List<MfaKeyVersionMaterial>(keyCount);
        try
        {
            var previous = 0;
            for (var i = 0; i < keyCount; i++)
            {
                RequireAvailable(payload, offset, KeyRecordBytes);
                var version = BinaryPrimitives.ReadUInt32BigEndian(payload.AsSpan(offset, 4));
                if (payload[offset + 4] != MfaKeyRing.KeyBytes)
                    throw Format("una clave no mide 32 bytes");
                if (version > int.MaxValue || version <= previous)
                    throw Format("versiones desordenadas o repetidas");
                if (!ring.Entries.Any(entry => entry.Version == (int)version))
                    throw Format("clave para una versión que no figura en el anillo");

                keys.Add(new MfaKeyVersionMaterial((int)version, payload.AsSpan(offset + 5, MfaKeyRing.KeyBytes).ToArray()));
                previous = (int)version;
                offset += KeyRecordBytes;
            }
            if (offset != payload.Length)
                throw Format("contenido sobrante tras las claves");
            return new MfaKeyRecoveryContent(ring, keys);
        }
        catch
        {
            // Un fallo a mitad de análisis pone a cero las copias ya hechas.
            foreach (var key in keys) key.Dispose();
            throw;
        }
    }

    private static MfaKeyRing ParseRing(byte[] ringJson, Guid expectedInstallationId)
    {
        try
        {
            return MfaKeyRing.Parse(ringJson, expectedInstallationId);
        }
        catch (MfaKeyRingException ex)
        {
            // Sólo se nombra el tipo de fallo del parser: nunca su contenido ni claves.
            throw new MfaKeyRecoveryPayloadException(MfaKeyRecoveryPayloadErrorKind.RingRejected,
                "el anillo fue rechazado por su parser: " + ex.Kind, ex);
        }
    }

    // Forma canónica: orden fijo de campos, versiones ascendentes, estados en minúsculas y fechas UTC exactas. Dos anillos con el
    // mismo contenido producen los mismos bytes, aunque el JSON de origen tenga distinto espaciado.
    private static byte[] CanonicalRingJson(MfaKeyRing ring)
    {
        using var stream = new MemoryStream();
        using (var writer = new Utf8JsonWriter(stream))
        {
            writer.WriteStartObject();
            writer.WriteString("format", MfaKeyRing.RingFormat);
            writer.WriteNumber("formatVersion", MfaKeyRing.FormatVersion);
            writer.WriteString("installationId", ring.InstallationId.ToString("D"));
            writer.WriteStartArray("versions");
            foreach (var entry in ring.Entries.OrderBy(entry => entry.Version))
            {
                writer.WriteStartObject();
                writer.WriteNumber("version", entry.Version);
                writer.WriteString("state", entry.State == MfaKeyState.Active ? "active" : "retired");
                writer.WriteString("createdAtUtc", entry.CreatedAtUtc.ToUniversalTime().ToString(CreatedAtFormat, CultureInfo.InvariantCulture));
                writer.WriteEndObject();
            }
            writer.WriteEndArray();
            writer.WriteEndObject();
        }
        return stream.ToArray();
    }

    private static void RequireAvailable(byte[] payload, int offset, int count)
    {
        if ((long)offset + count > payload.Length)
            throw Format("payload truncado");
    }

    private static MfaKeyRecoveryPayloadException Invalid(string detail) =>
        new(MfaKeyRecoveryPayloadErrorKind.InvalidRequest, "mfa_key_recovery_payload_request_invalid: " + detail, null);

    private static MfaKeyRecoveryPayloadException Format(string detail) =>
        new(MfaKeyRecoveryPayloadErrorKind.InvalidFormat, "mfa_key_recovery_payload_format_invalid: " + detail, null);
}

// Contenedor desechable del payload serializado. Contiene claves en claro. Dispose pone a cero su arreglo.
internal sealed class MfaKeyRecoveryPayloadBuffer : IDisposable
{
    private byte[]? _bytes;

    internal MfaKeyRecoveryPayloadBuffer(byte[] bytes)
    {
        _bytes = bytes;
    }

    // Acceso al arreglo propio, sin copia. No debe conservarse tras Dispose.
    internal byte[] Bytes => _bytes ?? throw new ObjectDisposedException(nameof(MfaKeyRecoveryPayloadBuffer));

    public void Dispose()
    {
        if (_bytes is null) return;
        CryptographicOperations.ZeroMemory(_bytes);
        _bytes = null;
    }

    // Sólo la longitud: nunca bytes.
    public override string ToString() =>
        _bytes is null
            ? "MfaKeyRecoveryPayloadBuffer(dispuesto)"
            : "MfaKeyRecoveryPayloadBuffer(longitud=" + _bytes.Length.ToString(CultureInfo.InvariantCulture) + ")";
}

// Clave de una versión. Posee su arreglo y lo pone a cero al desecharse. Nunca se imprime.
internal sealed class MfaKeyVersionMaterial : IDisposable
{
    private byte[]? _key;

    internal MfaKeyVersionMaterial(int version, byte[] key)
    {
        Version = version;
        _key = key;
    }

    public int Version { get; }

    // Vista del arreglo propio, sin copia. No debe conservarse tras Dispose.
    internal ReadOnlySpan<byte> Key => _key ?? throw new ObjectDisposedException(nameof(MfaKeyVersionMaterial));

    public void Dispose()
    {
        if (_key is null) return;
        CryptographicOperations.ZeroMemory(_key);
        _key = null;
    }

    public override string ToString() => "MfaKeyVersionMaterial(versión=" + Version.ToString(CultureInfo.InvariantCulture) + ")";
}

// Contenido analizado: metadatos del anillo y una clave por versión. Dispose pone a cero todas las claves.
internal sealed class MfaKeyRecoveryContent : IDisposable
{
    private readonly List<MfaKeyVersionMaterial> _keys;
    private bool _disposed;

    internal MfaKeyRecoveryContent(MfaKeyRing ring, List<MfaKeyVersionMaterial> keys)
    {
        Ring = ring;
        _keys = keys;
    }

    // Metadatos del anillo de origen (sin claves).
    public MfaKeyRing Ring { get; }

    // Vista de la clave de una versión, sin copia. No debe conservarse tras Dispose.
    internal ReadOnlySpan<byte> KeyFor(int version)
    {
        if (_disposed) throw new ObjectDisposedException(nameof(MfaKeyRecoveryContent));
        foreach (var material in _keys)
        {
            if (material.Version == version) return material.Key;
        }
        throw new ArgumentOutOfRangeException(nameof(version), "la versión no figura en el contenido");
    }

    public void Dispose()
    {
        if (_disposed) return;
        foreach (var key in _keys) key.Dispose();
        _keys.Clear();
        _disposed = true;
    }

    // Sólo el número de versiones: nunca claves.
    public override string ToString() =>
        "MfaKeyRecoveryContent(versiones=" + (_disposed ? "dispuesto" : _keys.Count.ToString(CultureInfo.InvariantCulture)) + ")";
}

internal enum MfaKeyRecoveryPayloadErrorKind
{
    InvalidRequest,
    TooLarge,
    InvalidFormat,
    UnsupportedVersion,
    RingRejected,
}

// Sólo códigos y detalles genéricos. Nunca bytes de clave ni contenido del payload.
internal sealed class MfaKeyRecoveryPayloadException(MfaKeyRecoveryPayloadErrorKind kind, string message, Exception? inner)
    : Exception(message, inner)
{
    public MfaKeyRecoveryPayloadErrorKind Kind { get; } = kind;
}
