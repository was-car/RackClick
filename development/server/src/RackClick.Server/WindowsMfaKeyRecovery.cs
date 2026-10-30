using System.Globalization;
using System.Runtime.Versioning;
using System.Security.Cryptography;
using System.Security.Principal;
using System.Text.Json;

namespace RackClick.Server;

// Exportación y recuperación del anillo MFA en laboratorio (MFA-L2f). Sólo memoria: la exportación devuelve un sobre cifrado y la
// recuperación crea un almacén nuevo con material importado. No escribe sobres en disco ni añade operador alguno.
// Investigación previa y contrato: evidence/s1-20261026/mfa-l2f-claude/INVESTIGACION-PREVIA.md.
//
// Exportación: lee el anillo y las claves de todas sus versiones con los componentes aprobados, comprueba que el anillo no cambió
// durante la lectura, serializa (L2e) y sella (L2d). Sólo devuelve el sobre; nunca un resultado parcial.
// Recuperación: abre el sobre, valida el contenido con la identidad de origen esperada antes de crear nada y crea el almacén de
// destino con el escritor aprobado. Si la instalación de destino difiere del origen, exige una adaptación explícita: sólo cambian
// los metadatos del anillo y la entropía DPAPI de las claves. Los identificadores y el ciphertext de los factores no cambian.
[SupportedOSPlatform("windows")]
internal static class WindowsMfaKeyRecovery
{
    // Exporta el anillo de un almacén de origen como sobre cifrado. Lanza WindowsMfaKeyRecoveryException sin devolver nada si algo falla.
    // beforeCoherenceCheck es un punto de ensayo interno: se ejecuta entre la lectura de las claves y la comprobación de coherencia.
    public static byte[] Export(string instancesRoot, Guid installationId, SecurityIdentifier readerSid,
        IReadOnlyCollection<SecurityIdentifier> trustedPrincipals, string password, Action? beforeCoherenceCheck = null)
    {
        var trusted = RequireTrusted(trustedPrincipals, readerSid);
        var root = RequireRoot(instancesRoot);
        var reader = new WindowsMfaKeyFileReader(readerSid, TrustedValues(trusted));
        var provider = new WindowsMfaKeyProvider(root, installationId, readerSid, trusted);
        var installation = Path.Combine(root, installationId.ToString("D"));
        var keysFolder = Path.Combine(installation, WindowsMfaKeyProvider.KeysFolderName);
        var ringPath = Path.Combine(keysFolder, MfaKeyRing.RingFileName);

        // Copias de claves propias: se ponen a cero en finally, también si la exportación falla a mitad.
        var copies = new List<(int Version, byte[] Key)>();
        try
        {
            byte[] ringFirst;
            try
            {
                reader.RequireSafeFolder(root);
                reader.RequireSafeFolder(installation);
                reader.RequireSafeFolder(keysFolder);
                ringFirst = reader.ReadValidated(ringPath, MfaKeyRing.MaxRingFileBytes);
                var ring = MfaKeyRing.Parse(ringFirst, installationId);
                foreach (var entry in ring.Entries)
                    copies.Add((entry.Version, provider.GetKey(entry.Version)));
            }
            catch (MfaKeyRingException ex)
            {
                throw Failure(WindowsMfaKeyRecoveryErrorKind.SourceRejected, "el origen no es exportable: " + ex.Kind, ex);
            }

            beforeCoherenceCheck?.Invoke();

            // Coherencia: el anillo debe ser idéntico al de la primera lectura. Límite: no es un instantáneo atómico (ver evidencia).
            byte[] ringSecond;
            try
            {
                ringSecond = reader.ReadValidated(ringPath, MfaKeyRing.MaxRingFileBytes);
            }
            catch (MfaKeyRingException ex)
            {
                throw Failure(WindowsMfaKeyRecoveryErrorKind.Incoherent, "el anillo no se pudo releer tras obtener las claves: " + ex.Kind, ex);
            }
            if (!CryptographicOperations.FixedTimeEquals(ringFirst, ringSecond))
                throw Failure(WindowsMfaKeyRecoveryErrorKind.Incoherent, "el anillo cambió durante la exportación; no se devuelve ningún sobre");

            try
            {
                using var payload = MfaKeyRecoveryPayload.Serialize(ringFirst, installationId, copies);
                return MfaKeyRecoveryEnvelope.Seal(password, payload.Bytes);
            }
            catch (MfaKeyRecoveryPayloadException ex)
            {
                throw Failure(WindowsMfaKeyRecoveryErrorKind.PayloadRejected, "el contenido no se pudo serializar: " + ex.Kind, ex);
            }
            catch (MfaRecoveryEnvelopeException ex)
            {
                throw MapEnvelope(ex);
            }
        }
        finally
        {
            foreach (var (_, key) in copies) CryptographicOperations.ZeroMemory(key);
        }
    }

    // Recupera el anillo exportado en un almacén nuevo. Valida todo el sobre y el contenido antes de crear nada.
    // adaptDestinationInstallation: permiso explícito para una instalación de destino distinta del origen. Sin él, se rechaza.
    // beforePublish y beforeOwnFolderCreation son puntos de ensayo internos del escritor.
    public static void Recover(byte[] envelope, string password, Guid expectedSourceInstallationId, string destinationRoot,
        Guid destinationInstallationId, SecurityIdentifier readerSid, IReadOnlyCollection<SecurityIdentifier> trustedPrincipals,
        bool adaptDestinationInstallation, Action? beforePublish = null, Action? beforeOwnFolderCreation = null)
    {
        if (envelope is null) throw Failure(WindowsMfaKeyRecoveryErrorKind.InvalidRequest, "sobre ausente");
        var trusted = RequireTrusted(trustedPrincipals, readerSid);
        var root = RequireRoot(destinationRoot);
        if (destinationInstallationId != expectedSourceInstallationId && !adaptDestinationInstallation)
            throw Failure(WindowsMfaKeyRecoveryErrorKind.InvalidRequest,
                "la instalación de destino difiere del origen y no se autorizó la adaptación explícita; no se crea nada");

        byte[]? plaintext = null;
        MfaKeyRecoveryContent? content = null;
        var copies = new List<(int Version, byte[] Key)>();
        try
        {
            try
            {
                plaintext = MfaKeyRecoveryEnvelope.Open(password, envelope);
            }
            catch (MfaRecoveryEnvelopeException ex)
            {
                throw MapEnvelope(ex);
            }

            // Identidad de origen esperada: se valida antes de cualquier escritura en destino.
            try
            {
                content = MfaKeyRecoveryPayload.Deserialize(plaintext, expectedSourceInstallationId);
            }
            catch (MfaKeyRecoveryPayloadException ex)
            {
                throw Failure(WindowsMfaKeyRecoveryErrorKind.PayloadRejected, "el contenido del sobre fue rechazado: " + ex.Kind, ex);
            }

            // Adaptación explícita: sólo los metadatos del anillo cambian; las claves son las mismas.
            var ringJson = RingJsonFor(content.Ring, destinationInstallationId);
            foreach (var entry in content.Ring.Entries)
                copies.Add((entry.Version, content.KeyFor(entry.Version).ToArray()));

            try
            {
                WindowsMfaKeyStoreWriter.CreateStoreFromMaterial(root, destinationInstallationId, readerSid, trusted, ringJson, copies,
                    beforePublish, beforeOwnFolderCreation);
            }
            catch (MfaKeyStoreCreationException ex)
            {
                throw Failure(WindowsMfaKeyRecoveryErrorKind.DestinationRejected, "el destino no se creó: " + ex.Kind, ex, ex.Residue);
            }
        }
        finally
        {
            if (plaintext is not null) CryptographicOperations.ZeroMemory(plaintext);
            content?.Dispose();
            foreach (var (_, key) in copies) CryptographicOperations.ZeroMemory(key);
        }
    }

    // Forma canónica del anillo para una instalación dada: mismos campos y reglas que la forma canónica de L2e, con el identificador
    // de la instalación de destino. Se valida después con MfaKeyRing.Parse dentro del escritor.
    private static byte[] RingJsonFor(MfaKeyRing ring, Guid installationId)
    {
        using var stream = new MemoryStream();
        using (var writer = new Utf8JsonWriter(stream))
        {
            writer.WriteStartObject();
            writer.WriteString("format", MfaKeyRing.RingFormat);
            writer.WriteNumber("formatVersion", MfaKeyRing.FormatVersion);
            writer.WriteString("installationId", installationId.ToString("D"));
            writer.WriteStartArray("versions");
            foreach (var entry in ring.Entries)
            {
                writer.WriteStartObject();
                writer.WriteNumber("version", entry.Version);
                writer.WriteString("state", entry.State == MfaKeyState.Active ? "active" : "retired");
                writer.WriteString("createdAtUtc", entry.CreatedAtUtc.ToUniversalTime().ToString("yyyy-MM-dd'T'HH:mm:ss'Z'", CultureInfo.InvariantCulture));
                writer.WriteEndObject();
            }
            writer.WriteEndArray();
            writer.WriteEndObject();
        }
        return stream.ToArray();
    }

    private static SecurityIdentifier[] RequireTrusted(IReadOnlyCollection<SecurityIdentifier> trustedPrincipals, SecurityIdentifier readerSid)
    {
        var trusted = trustedPrincipals.ToArray();
        if (trusted.Length == 0) throw Failure(WindowsMfaKeyRecoveryErrorKind.InvalidRequest, "sin principales de confianza");
        if (trusted.Contains(readerSid)) throw Failure(WindowsMfaKeyRecoveryErrorKind.InvalidRequest, "el lector no puede ser principal de confianza");
        return trusted;
    }

    private static string RequireRoot(string root)
    {
        if (!Path.IsPathFullyQualified(root))
            throw Failure(WindowsMfaKeyRecoveryErrorKind.InvalidRequest, "la raíz del almacén debe ser absoluta");
        return Path.GetFullPath(root);
    }

    private static HashSet<string> TrustedValues(SecurityIdentifier[] trusted) =>
        trusted.Select(sid => sid.Value).ToHashSet(StringComparer.Ordinal);

    private static WindowsMfaKeyRecoveryException MapEnvelope(MfaRecoveryEnvelopeException ex) => ex.Kind switch
    {
        MfaRecoveryEnvelopeErrorKind.AuthenticationFailed => Failure(WindowsMfaKeyRecoveryErrorKind.AuthenticationFailed,
            "contraseña incorrecta o sobre alterado; no se devuelve contenido", ex),
        MfaRecoveryEnvelopeErrorKind.InvalidRequest => Failure(WindowsMfaKeyRecoveryErrorKind.InvalidRequest,
            "la contraseña o el sobre no cumplen los requisitos", ex),
        _ => Failure(WindowsMfaKeyRecoveryErrorKind.EnvelopeRejected, "el sobre fue rechazado antes de descifrar: " + ex.Kind, ex),
    };

    private static WindowsMfaKeyRecoveryException Failure(WindowsMfaKeyRecoveryErrorKind kind, string message, Exception? inner = null,
        IReadOnlyList<string>? residue = null) =>
        new(kind, message, inner, residue ?? []);
}

internal enum WindowsMfaKeyRecoveryErrorKind
{
    InvalidRequest,
    SourceRejected,
    Incoherent,
    AuthenticationFailed,
    EnvelopeRejected,
    PayloadRejected,
    DestinationRejected,
}

// Sólo códigos y detalles genéricos. Nunca bytes de clave ni contenido del sobre.
internal sealed class WindowsMfaKeyRecoveryException(WindowsMfaKeyRecoveryErrorKind kind, string message, Exception? inner,
    IReadOnlyList<string> residue) : Exception(message, inner)
{
    public WindowsMfaKeyRecoveryErrorKind Kind { get; } = kind;

    // Rutas propias que el escritor no pudo retirar en el destino. Si hay residuo, el destino no quedó limpio.
    public IReadOnlyList<string> Residue { get; } = residue;
}
