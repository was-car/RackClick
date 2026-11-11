using System.ComponentModel;
using System.Globalization;
using System.Runtime.InteropServices;
using System.Runtime.Versioning;
using System.Security.AccessControl;
using System.Security.Cryptography;
using System.Security.Principal;
using System.Text;
using System.Text.Json;
using Microsoft.Win32.SafeHandles;

namespace RackClick.Server;

// Creación inicial explícita de un almacén MFA (MFA-L2c): ring con la versión 1 activa y una clave de 32 bytes protegida con
// DPAPI LocalMachine, con entropía de instalación y versión. No se llama desde el arranque, nunca reemplaza un destino
// existente y nunca genera una clave para cargar un almacén ausente o corrupto.
// Identidad (MFA-L2C-01): cada carpeta y archivo propio se crea de forma exclusiva y se registra su identidad (volumen + índice
// de archivo). Antes de publicar y antes de limpiar se abre cada objeto por ruta y se compara su identidad con la registrada:
// la publicación y el borrado actúan sobre el identificador verificado, nunca sobre el nombre. Un objeto que ya no coincide se
// conserva y se declara como residuo.
// Investigación previa: evidence/s1-20261026/mfa-l2c-claude/INVESTIGACION-PREVIA.md.
// F-04.01: cada objeto nace con DACL protegida explícita. No se cambia ninguna ACL por ruta después de crearlo.
// Límites: no se afirma durabilidad del directorio ni atomicidad disco/DB. Persiste la ventana entre crear una carpeta y
// capturar su identidad; el creador debe ser un principal de confianza; sólo NTFS (identidad de 64 bits).
[SupportedOSPlatform("windows")]
internal static class WindowsMfaKeyStoreWriter
{
    private const string StagingPrefix = "mfa-keys.preparando-";
    private const string CreatedAtFormat = "yyyy-MM-dd'T'HH:mm:ss'Z'";
    private const int InitialVersion = 1;
    private const int CryptProtectUiForbidden = 0x1;
    private const int CryptProtectLocalMachine = 0x4;

    private const uint GenericWrite = 0x40000000;
    private const uint Delete = 0x00010000;
    private const uint FileAddSubdirectory = 0x0004;
    private const uint FileReadAttributes = 0x0080;
    private const uint FileShareRead = 0x1;
    private const uint FileShareWrite = 0x2;
    private const uint FileShareDelete = 0x4;
    private const uint CreateNew = 1;
    private const uint OpenExisting = 3;
    private const uint FileAttributeNormal = 0x80;
    private const uint FileFlagBackupSemantics = 0x02000000;
    private const uint FileFlagOpenReparsePoint = 0x00200000;
    private const uint FileAttributeDirectory = 0x10;
    private const uint FileAttributeReparsePoint = 0x400;
    private const int ErrorAlreadyExists = 183;
    private const int ErrorFileExists = 80;
    private const int FileRenameInfoClass = 3;
    private const int FileDispositionInfoClass = 4;

    // Crea el almacén de una instalación. Lanza MfaKeyStoreCreationException; si queda algo propio sin retirar, lo declara en Residue.
    // beforeOwnFolderCreation y beforePublish son puntos de ensayo para las pruebas; en producción no se usan.
    private static void CreateCore(string instancesRoot, Guid installationId, SecurityIdentifier readerSid,
        IReadOnlyCollection<SecurityIdentifier> trustedPrincipals, Action? beforePublish, Action? beforeOwnFolderCreation, StagePreparation stage, Action<string, bool>? afterObjectCreated, Action? afterPublish)
    {
        if (!Path.IsPathFullyQualified(instancesRoot)) throw Invalid("la raíz debe ser absoluta");
        var root = Path.GetFullPath(instancesRoot);
        var parent = Path.GetDirectoryName(root);
        if (parent is null || !Directory.Exists(parent)) throw Invalid("la carpeta padre de la raíz debe existir");
        var trusted = trustedPrincipals.ToArray();
        if (trusted.Length == 0) throw Invalid("sin principales de confianza");
        if (trusted.Contains(readerSid)) throw Invalid("el lector no puede ser principal de confianza");

        var reader = new WindowsMfaKeyFileReader(readerSid, trusted.Select(sid => sid.Value).ToHashSet(StringComparer.Ordinal));
        var installation = Path.Combine(root, installationId.ToString("D"));
        var keys = Path.Combine(installation, WindowsMfaKeyProvider.KeysFolderName);

        // Antes de tocar nada: un destino existente, sea lo que sea, se conserva tal cual.
        if (Exists(keys))
            throw Creation(MfaKeyStoreCreationErrorKind.AlreadyExists, "mfa_key_store_exists: el destino ya existe; no se modifica");
        RequireExistingAncestor(root, reader);
        RequireExistingAncestor(installation, reader);

        var tracked = new List<Tracked>();
        try
        {
            EnsureFolder(root, trusted, readerSid, reader, tracked, afterObjectCreated);
            beforeOwnFolderCreation?.Invoke();
            var installationEntry = EnsureFolder(installation, trusted, readerSid, reader, tracked, afterObjectCreated);
            var staging = Path.Combine(installation, StagingPrefix + Guid.NewGuid().ToString("N"));
            var stagingEntry = TryCreateOwnedDirectory(staging, trusted, readerSid) ?? throw Creation(MfaKeyStoreCreationErrorKind.CreationFailed,
                "mfa_key_store_staging_exists: el nombre de staging ya existe; no se reutiliza");
            tracked.Add(stagingEntry);
            afterObjectCreated?.Invoke(stagingEntry.Path, true);
            ValidateCreatedFolder(stagingEntry, reader);
            stage(stagingEntry, trusted, readerSid, reader, tracked, afterObjectCreated);
            Publish(stagingEntry, installationEntry, keys, tracked, beforePublish, afterPublish);
        }
        catch (MfaKeyStoreCreationException ex)
        {
            throw Failed(ex, tracked);
        }
        catch (MfaKeyRingException ex)
        {
            throw Failed(Creation(MfaKeyStoreCreationErrorKind.ValidationFailed, ex.Message, ex), tracked);
        }
        catch (Exception ex) when (ex is IOException or UnauthorizedAccessException)
        {
            throw Failed(Creation(MfaKeyStoreCreationErrorKind.CreationFailed, "mfa_key_store_write_failed: no se pudo preparar el almacén", ex), tracked);
        }
        catch (Exception)
        {
            Discard(tracked);
            throw;
        }
    }

    // Etapa de preparación del staging: recibe el objeto de staging ya creado y validado, y escribe los archivos del almacén.
    private delegate void StagePreparation(Tracked stagingEntry, SecurityIdentifier[] trusted, SecurityIdentifier readerSid,
        WindowsMfaKeyFileReader reader, List<Tracked> tracked, Action<string, bool>? afterObjectCreated);

    // Crea el almacén de una instalación con una clave generada (versión inicial). Lanza MfaKeyStoreCreationException; si queda
    // algo propio sin retirar, lo declara en Residue. beforeOwnFolderCreation y beforePublish son puntos de ensayo de las pruebas.
    public static void CreateInitialStore(string instancesRoot, Guid installationId, SecurityIdentifier readerSid,
        IReadOnlyCollection<SecurityIdentifier> trustedPrincipals, Action? beforePublish = null, Action? beforeOwnFolderCreation = null, Action<string, bool>? afterObjectCreated = null, Action? afterPublish = null) =>
        CreateCore(instancesRoot, installationId, readerSid, trustedPrincipals, beforePublish, beforeOwnFolderCreation,
            (stagingEntry, trusted, sid, reader, tracked, observed) => StageStore(installationId, stagingEntry, trusted, sid, reader, tracked, observed), afterObjectCreated, afterPublish);

    // Crea un almacén nuevo con material importado (MFA-L2f): ring canónico validado por MfaKeyRing.Parse y una clave de 32 bytes
    // por versión del anillo. Las claves de entrada no se modifican ni se ponen a cero. Todo se valida antes de tocar el disco.
    internal static void CreateStoreFromMaterial(string instancesRoot, Guid installationId, SecurityIdentifier readerSid,
        IReadOnlyCollection<SecurityIdentifier> trustedPrincipals, byte[] ringJson, IReadOnlyList<(int Version, byte[] Key)> keys,
        Action? beforePublish = null, Action? beforeOwnFolderCreation = null, Action<string, bool>? afterObjectCreated = null, Action? afterPublish = null)
    {
        if (ringJson is null || keys is null) throw Invalid("material ausente");
        MfaKeyRing ring;
        try
        {
            ring = MfaKeyRing.Parse(ringJson, installationId);
        }
        catch (MfaKeyRingException ex)
        {
            throw Creation(MfaKeyStoreCreationErrorKind.InvalidRequest,
                "mfa_key_store_material_invalid: el anillo fue rechazado por su parser: " + ex.Kind, ex);
        }
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

        CreateCore(instancesRoot, installationId, readerSid, trustedPrincipals, beforePublish, beforeOwnFolderCreation,
            (stagingEntry, trusted, sid, reader, tracked, observed) => StageMaterial(installationId, ringJson, ordered, stagingEntry, trusted, sid, reader, tracked, observed), afterObjectCreated, afterPublish);
    }

    // Escribe el material importado: el anillo tal como se validó y una clave protegida con su entropía de versión por cada versión.
    private static void StageMaterial(Guid installationId, byte[] ringJson, (int Version, byte[] Key)[] keys, Tracked stagingEntry,
        SecurityIdentifier[] trusted, SecurityIdentifier readerSid, WindowsMfaKeyFileReader reader, List<Tracked> tracked, Action<string, bool>? afterObjectCreated)
    {
        var ringEntry = CreateExclusiveFile(Path.Combine(stagingEntry.Path, MfaKeyRing.RingFileName), ringJson, tracked, trusted, readerSid, afterObjectCreated);
        var keyEntries = new List<Tracked>(keys.Length);
        foreach (var (version, key) in keys)
        {
            var entropy = MfaKeyRing.EntropyFor(installationId, version);
            var blob = Protect(key, entropy);
            var recovered = Unprotect(blob, entropy);
            try
            {
                if (!CryptographicOperations.FixedTimeEquals(recovered, key))
                    throw Creation(MfaKeyStoreCreationErrorKind.ValidationFailed, "mfa_key_store_dpapi_roundtrip: la comprobación DPAPI no devuelve la clave");
            }
            finally
            {
                CryptographicOperations.ZeroMemory(recovered);
            }
            var keyFile = KeyFileBytes(installationId, version, blob);
            MfaKeyRing.ParseKeyFile(keyFile, installationId, version);
            keyEntries.Add(CreateExclusiveFile(Path.Combine(stagingEntry.Path, MfaKeyRing.KeyFileName(version)), keyFile, tracked, trusted, readerSid, afterObjectCreated));
        }

        // Mismas reglas que el lector aprobado: carpeta, propietario, DACL e identidad de cada archivo.
        reader.RequireSafeFolder(stagingEntry.Path);
        reader.ReadValidated(ringEntry.Path, MfaKeyRing.MaxRingFileBytes);
        foreach (var keyEntry in keyEntries) reader.ReadValidated(keyEntry.Path, MfaKeyRing.MaxKeyFileBytes);
    }

    // Prepara los archivos en el staging: clave generada, protegida y verificada antes de escribir nada.
    private static void StageStore(Guid installationId, Tracked stagingEntry, SecurityIdentifier[] trusted, SecurityIdentifier readerSid,
        WindowsMfaKeyFileReader reader, List<Tracked> tracked, Action<string, bool>? afterObjectCreated)
    {
        var key = RandomNumberGenerator.GetBytes(MfaKeyRing.KeyBytes);
        try
        {
            var entropy = MfaKeyRing.EntropyFor(installationId, InitialVersion);
            var blob = Protect(key, entropy);
            var recovered = Unprotect(blob, entropy);
            try
            {
                if (!CryptographicOperations.FixedTimeEquals(recovered, key))
                    throw Creation(MfaKeyStoreCreationErrorKind.ValidationFailed, "mfa_key_store_dpapi_roundtrip: la comprobación DPAPI no devuelve la clave");
            }
            finally
            {
                CryptographicOperations.ZeroMemory(recovered);
            }

            var ring = RingBytes(installationId, DateTimeOffset.UtcNow);
            var keyFile = KeyFileBytes(installationId, InitialVersion, blob);
            MfaKeyRing.Parse(ring, installationId);
            MfaKeyRing.ParseKeyFile(keyFile, installationId, InitialVersion);

            var ringEntry = CreateExclusiveFile(Path.Combine(stagingEntry.Path, MfaKeyRing.RingFileName), ring, tracked, trusted, readerSid, afterObjectCreated);
            var keyEntry = CreateExclusiveFile(Path.Combine(stagingEntry.Path, MfaKeyRing.KeyFileName(InitialVersion)), keyFile, tracked, trusted, readerSid, afterObjectCreated);
            // Mismas reglas que el lector aprobado: carpeta, propietario, DACL e identidad de cada archivo.
            reader.RequireSafeFolder(stagingEntry.Path);
            reader.ReadValidated(ringEntry.Path, MfaKeyRing.MaxRingFileBytes);
            reader.ReadValidated(keyEntry.Path, MfaKeyRing.MaxKeyFileBytes);
        }
        finally
        {
            CryptographicOperations.ZeroMemory(key);
        }
    }

    // Publicación ligada al objeto validado: el renombrado se hace sobre el identificador del staging comprobado. Antes se
    // comprueban la identidad de los ancestros y de cada archivo propio. Si algo no coincide, se rechaza sin publicar.
    private static void Publish(Tracked stagingEntry, Tracked installationEntry, string keys, List<Tracked> tracked, Action? beforePublish, Action? afterPublish)
    {
        var renamed = false;
        try
        {
            beforePublish?.Invoke();
            using var stagingHandle = OpenVerified(stagingEntry.Path, stagingEntry.IsDirectory, stagingEntry.Identity, Delete | FileReadAttributes)
                ?? throw Creation(MfaKeyStoreCreationErrorKind.PublishFailed,
                    "mfa_key_store_staging_changed: el staging ya no es el objeto validado; no se publica");
            using var parentHandle = OpenVerified(installationEntry.Path, true, installationEntry.Identity, FileAddSubdirectory | FileReadAttributes)
                ?? throw Creation(MfaKeyStoreCreationErrorKind.PublishFailed,
                    "mfa_key_store_parent_changed: la carpeta de la instalación ya no es la validada; no se publica");
            foreach (var entry in tracked.Where(entry => !ReferenceEquals(entry, stagingEntry)))
            {
                using var verified = OpenVerified(entry.Path, entry.IsDirectory, entry.Identity, FileReadAttributes)
                    ?? throw Creation(MfaKeyStoreCreationErrorKind.PublishFailed,
                        "mfa_key_store_entry_changed: un objeto de la cadena ya no es el validado; no se publica");
            }
            // Renombrado sobre el identificador verificado, con destino absoluto. El nombre relativo a un identificador de padre
            // falla con ERROR_INVALID_PARAMETER en las mediciones (sonda temporal), así que no se usa.
            RenameByHandle(stagingHandle, keys);
            renamed = true;
            // Después del rename nunca se desmonta parcialmente un almacén publicado. Conservar las
            // identidades y sus rutas reales permite declarar el residuo sin borrar por nombre.
            var stagePath = stagingEntry.Path;
            foreach (var entry in tracked.Where(entry => ReferenceEquals(entry, stagingEntry) ||
                         entry.Path.StartsWith(stagePath + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase)))
                entry.PreservePublished(keys + entry.Path[stagePath.Length..]);
            afterPublish?.Invoke();
            // Antes de devolver éxito, el destino debe contener el objeto validado: misma identidad que el staging.
            using var published = OpenVerified(keys, true, stagingEntry.Identity, FileReadAttributes)
                ?? throw new MfaKeyStoreCreationException(MfaKeyStoreCreationErrorKind.PublishFailed,
                    "mfa_key_store_publish_unverified: el destino no contiene el objeto validado", null, [keys]);
        }
        catch (MfaKeyStoreCreationException)
        {
            throw;
        }
        catch (IOException ex) when (!renamed && Exists(keys))
        {
            throw Creation(MfaKeyStoreCreationErrorKind.AlreadyExists,
                "mfa_key_store_exists: el destino apareció durante la publicación; no se reemplaza", ex);
        }
        catch (Exception ex) when (ex is IOException or UnauthorizedAccessException)
        {
            if (renamed)
                throw new MfaKeyStoreCreationException(MfaKeyStoreCreationErrorKind.PublishFailed,
                    "mfa_key_store_publish_unverified: almacén publicado conservado; comprobar antes de continuar", ex, [keys]);
            throw Creation(MfaKeyStoreCreationErrorKind.PublishFailed, "mfa_key_store_publish_failed: no se pudo publicar el almacén", ex);
        }
    }

    // Carpeta de la cadena: si la crea esta llamada, es propia (se registra su identidad); si ya existía, se valida y no se
    // adopta para limpieza ni se cambia su ACL.
    private static Tracked EnsureFolder(string path, SecurityIdentifier[] trusted, SecurityIdentifier readerSid,
        WindowsMfaKeyFileReader reader, List<Tracked> tracked, Action<string, bool>? afterObjectCreated)
    {
        var created = TryCreateOwnedDirectory(path, trusted, readerSid);
        if (created is not null)
        {
            tracked.Add(created);
            afterObjectCreated?.Invoke(created.Path, true);
            ValidateCreatedFolder(created, reader);
            return created;
        }
        if (File.Exists(path)) throw Invalid("un ancestro existe como archivo: " + Path.GetFileName(path));
        var existing = IdentityOfExisting(path);
        try
        {
            reader.RequireSafeFolder(path);
        }
        catch (MfaKeyRingException ex)
        {
            throw Creation(MfaKeyStoreCreationErrorKind.ValidationFailed, "mfa_key_store_ancestor_unsafe: " + ex.Message, ex);
        }
        using var verified = OpenVerified(path, true, existing, FileReadAttributes)
            ?? throw Creation(MfaKeyStoreCreationErrorKind.ValidationFailed, "mfa_key_store_ancestor_changed: el ancestro cambió durante su validación");
        var entry = new Tracked(path, isDirectory: true, owned: false, existing);
        tracked.Add(entry);
        return entry;
    }

    // Un ancestro existente debe cumplir el mismo DACL que el lector exige, antes de escribir nada. No se corrige lo ajeno.
    private static void RequireExistingAncestor(string path, WindowsMfaKeyFileReader reader)
    {
        if (File.Exists(path)) throw Invalid("un ancestro existe como archivo: " + Path.GetFileName(path));
        if (!Directory.Exists(path)) return;
        try
        {
            reader.RequireSafeFolder(path);
        }
        catch (MfaKeyRingException ex)
        {
            throw Creation(MfaKeyStoreCreationErrorKind.ValidationFailed, "mfa_key_store_ancestor_unsafe: " + ex.Message, ex);
        }
    }

    // Creación exclusiva de carpeta: CreateDirectoryW falla con ERROR_ALREADY_EXISTS si ya existe, y entonces no es propia.
    private static Tracked? TryCreateOwnedDirectory(string path, SecurityIdentifier[] trusted, SecurityIdentifier readerSid)
    {
        using var security = new CreationSecurity(isDirectory: true, trusted, readerSid);
        if (!CreateDirectoryW(ExtendedLocalPath(path), security.Pointer))
        {
            var code = Marshal.GetLastWin32Error();
            if (code is ErrorAlreadyExists or ErrorFileExists) return null;
            throw Creation(MfaKeyStoreCreationErrorKind.CreationFailed,
                "mfa_key_store_create_failed: no se pudo crear la carpeta (Win32 " + code.ToString(CultureInfo.InvariantCulture) + ")",
                new Win32Exception(code));
        }
        using var handle = OpenByPath(path, isDirectory: true, FileReadAttributes)
            ?? throw new MfaKeyStoreCreationException(MfaKeyStoreCreationErrorKind.CreationFailed,
                "mfa_key_store_identity_unavailable: la carpeta creada no se pudo identificar; se conserva", null, [path]);
        var info = Information(handle);
        RequireKind(info, isDirectory: true, path);
        return new Tracked(path, isDirectory: true, owned: true, IdentityOf(info));
    }

    // Creación exclusiva de archivo (CREATE_NEW). La identidad se toma del identificador de creación, antes de escribir.
    private static Tracked CreateExclusiveFile(string path, byte[] content, List<Tracked> tracked, SecurityIdentifier[] trusted, SecurityIdentifier readerSid, Action<string, bool>? afterObjectCreated)
    {
        using var security = new CreationSecurity(isDirectory: false, trusted, readerSid);
        using var handle = CreateFileW(ExtendedLocalPath(path), GenericWrite | FileReadAttributes, FileShareRead, security.Pointer, CreateNew,
            FileAttributeNormal | FileFlagOpenReparsePoint, IntPtr.Zero);
        if (handle.IsInvalid)
            throw Creation(MfaKeyStoreCreationErrorKind.CreationFailed,
                "mfa_key_store_file_failed: no se pudo crear el archivo propio " + Path.GetFileName(path),
                new Win32Exception(Marshal.GetLastWin32Error()));
        var info = Information(handle);
        RequireKind(info, isDirectory: false, path);
        var entry = new Tracked(path, isDirectory: false, owned: true, IdentityOf(info));
        tracked.Add(entry);
        afterObjectCreated?.Invoke(path, false);
        RandomAccess.Write(handle, content, 0);
        RandomAccess.FlushToDisk(handle);
        return entry;
    }

    // Sólo valida: el descriptor se aplicó en la llamada nativa de creación, nunca con SetAcl posterior.
    private static void ValidateCreatedFolder(Tracked entry, WindowsMfaKeyFileReader reader)
    {
        using var verified = OpenVerified(entry.Path, true, entry.Identity, FileReadAttributes)
            ?? throw Creation(MfaKeyStoreCreationErrorKind.ValidationFailed,
                "mfa_key_store_identity_changed: el objeto ya no es el creado");
        reader.RequireSafeFolder(entry.Path);
    }

    // Retira lo propio: cada objeto se borra sólo si, al abrirlo por ruta, su identidad coincide con la registrada.
    // Lo que no coincide, no se abre o no se puede vaciar se conserva y se devuelve como residuo.
    private static List<string> Discard(List<Tracked> tracked)
    {
        var residue = new List<string>();
        for (var i = tracked.Count - 1; i >= 0; i--)
        {
            var entry = tracked[i];
            if (entry.Owned && !RetireOwned(entry)) residue.Add(entry.Path);
        }
        return residue;
    }

    private static bool RetireOwned(Tracked entry)
    {
        using var handle = OpenVerified(entry.Path, entry.IsDirectory, entry.Identity, Delete | FileReadAttributes);
        if (handle is null) return false;
        try
        {
            MarkForDeletion(handle);
            return true;
        }
        catch (IOException)
        {
            return false;
        }
        catch (UnauthorizedAccessException)
        {
            return false;
        }
    }

    // Une el fallo original con lo que no se pudo retirar. Si queda residuo, el mensaje lo dice.
    private static MfaKeyStoreCreationException Failed(MfaKeyStoreCreationException failure, List<Tracked> tracked)
    {
        var residue = failure.Residue.Concat(Discard(tracked)).ToArray();
        if (residue.Length == 0) return failure;
        return new MfaKeyStoreCreationException(failure.Kind,
            failure.Message + " Residuo conservado (no se pudo retirar): " + string.Join("; ", residue) + ".", failure, residue);
    }

    private static SafeFileHandle? OpenVerified(string path, bool isDirectory, FileIdentity expected, uint access)
    {
        var handle = OpenByPath(path, isDirectory, access);
        if (handle is null) return null;
        try
        {
            var info = Information(handle);
            if (!IsKind(info, isDirectory) || IdentityOf(info) != expected)
            {
                handle.Dispose();
                return null;
            }
            return handle;
        }
        catch
        {
            handle.Dispose();
            throw;
        }
    }

    private static SafeFileHandle? OpenByPath(string path, bool isDirectory, uint access)
    {
        var flags = FileFlagOpenReparsePoint | (isDirectory ? FileFlagBackupSemantics : 0);
        var handle = CreateFileW(ExtendedLocalPath(path), access, FileShareRead | FileShareWrite | FileShareDelete, IntPtr.Zero, OpenExisting, flags, IntPtr.Zero);
        return handle.IsInvalid ? null : handle;
    }

    private static FileIdentity IdentityOfExisting(string path)
    {
        using var handle = OpenByPath(path, isDirectory: true, FileReadAttributes)
            ?? throw Creation(MfaKeyStoreCreationErrorKind.ValidationFailed, "mfa_key_store_ancestor_missing: el ancestro desapareció");
        return IdentityOf(Information(handle));
    }

    private static void RequireKind(ByHandleFileInformation info, bool isDirectory, string path)
    {
        if (!IsKind(info, isDirectory) || (info.FileAttributes & FileAttributeReparsePoint) != 0)
            throw new MfaKeyStoreCreationException(MfaKeyStoreCreationErrorKind.CreationFailed,
                "mfa_key_store_kind_unexpected: el objeto creado no tiene el tipo esperado; se conserva", null, [path]);
    }

    private static bool IsKind(ByHandleFileInformation info, bool isDirectory) =>
        ((info.FileAttributes & FileAttributeDirectory) != 0) == isDirectory && (info.FileAttributes & FileAttributeReparsePoint) == 0;

    private static ByHandleFileInformation Information(SafeFileHandle handle)
    {
        if (!GetFileInformationByHandle(handle, out var info))
            throw new IOException("mfa_key_store_identity_unavailable: no se pudo leer la identidad del objeto",
                new Win32Exception(Marshal.GetLastWin32Error()));
        return info;
    }

    private static FileIdentity IdentityOf(ByHandleFileInformation info) =>
        new(info.VolumeSerialNumber, ((ulong)info.FileIndexHigh << 32) | info.FileIndexLow);

    // Renombrado sobre el identificador: ReplaceIfExists = FALSE, así que falla si el destino existe.
    private static void RenameByHandle(SafeFileHandle handle, string target)
    {
        var nameBytes = Encoding.Unicode.GetBytes(target);
        // FILE_RENAME_INFO: el nombre debe ir terminado en NUL (medido en la sonda: sin terminador el kernel lee memoria ajena
        // y crea nombres corruptos o falla con ERROR_INVALID_NAME). Todo el búfer empieza a cero.
        var size = 2 * IntPtr.Size + 4 + nameBytes.Length + sizeof(char);
        var buffer = Marshal.AllocHGlobal(size);
        try
        {
            Marshal.Copy(new byte[size], 0, buffer, size);
            Marshal.WriteByte(buffer, 0, 0);
            Marshal.WriteIntPtr(buffer, IntPtr.Size, IntPtr.Zero);
            Marshal.WriteInt32(buffer, 2 * IntPtr.Size, nameBytes.Length);
            Marshal.Copy(nameBytes, 0, IntPtr.Add(buffer, 2 * IntPtr.Size + 4), nameBytes.Length);
            if (!SetFileInformationByHandle(handle, FileRenameInfoClass, buffer, (uint)size))
                throw new IOException("mfa_key_store_rename_failed: el renombrado sobre el identificador falló",
                    new Win32Exception(Marshal.GetLastWin32Error()));
        }
        finally
        {
            Marshal.FreeHGlobal(buffer);
        }
    }

    // Only the native call receives the extended prefix. Canonical paths/ACL/identity anchoring remain unchanged.
    private static string ExtendedLocalPath(string path)=>path.Length>=248&&path.Length>=3&&path[1]==':'&&path[2]=='\\'?@"\\?\"+path:path;

    // Marca el objeto para borrarse al cerrar el identificador. Un directorio sólo se borra si está vacío.
    private static void MarkForDeletion(SafeFileHandle handle)
    {
        var buffer = Marshal.AllocHGlobal(1);
        try
        {
            Marshal.WriteByte(buffer, 1);
            if (!SetFileInformationByHandle(handle, FileDispositionInfoClass, buffer, 1))
                throw new IOException("mfa_key_store_delete_failed: el borrado sobre el identificador falló",
                    new Win32Exception(Marshal.GetLastWin32Error()));
        }
        finally
        {
            Marshal.FreeHGlobal(buffer);
        }
    }

    // SECURITY_ATTRIBUTES contiene un descriptor autorrelativo protegido. El kernel lo aplica al crear
    // y asigna el propietario desde el token; no se fuerza el SID del operador ni se heredan handles.
    private sealed class CreationSecurity : IDisposable
    {
        private readonly IntPtr _descriptor;
        public IntPtr Pointer { get; }

        public CreationSecurity(bool isDirectory, SecurityIdentifier[] trusted, SecurityIdentifier readerSid)
        {
            FileSystemSecurity security = isDirectory ? new DirectorySecurity() : new FileSecurity();
            security.SetAccessRuleProtection(true, false);
            var inherit = isDirectory ? InheritanceFlags.ContainerInherit | InheritanceFlags.ObjectInherit : InheritanceFlags.None;
            foreach (var sid in trusted)
                security.AddAccessRule(new FileSystemAccessRule(sid, FileSystemRights.FullControl, inherit,
                    PropagationFlags.None, AccessControlType.Allow));
            security.AddAccessRule(new FileSystemAccessRule(readerSid, FileSystemRights.ReadAndExecute, inherit,
                PropagationFlags.None, AccessControlType.Allow));
            _descriptor = Allocate(security.GetSecurityDescriptorBinaryForm());
            try
            {
                Pointer = Marshal.AllocHGlobal(Marshal.SizeOf<SecurityAttributes>());
                Marshal.StructureToPtr(new SecurityAttributes
                {
                    Length = Marshal.SizeOf<SecurityAttributes>(), Descriptor = _descriptor, InheritHandle = 0,
                }, Pointer, false);
            }
            catch
            {
                if (Pointer != IntPtr.Zero) Marshal.FreeHGlobal(Pointer);
                Marshal.FreeHGlobal(_descriptor);
                throw;
            }
        }

        public void Dispose()
        {
            Marshal.FreeHGlobal(Pointer);
            Marshal.FreeHGlobal(_descriptor);
        }
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct SecurityAttributes
    {
        public int Length;
        public IntPtr Descriptor;
        public int InheritHandle;
    }

    private static byte[] RingBytes(Guid installationId, DateTimeOffset createdAt)
    {
        using var stream = new MemoryStream();
        using (var writer = new Utf8JsonWriter(stream))
        {
            writer.WriteStartObject();
            writer.WriteString("format", MfaKeyRing.RingFormat);
            writer.WriteNumber("formatVersion", MfaKeyRing.FormatVersion);
            writer.WriteString("installationId", installationId.ToString("D"));
            writer.WriteStartArray("versions");
            writer.WriteStartObject();
            writer.WriteNumber("version", InitialVersion);
            writer.WriteString("state", "active");
            writer.WriteString("createdAtUtc", createdAt.ToUniversalTime().ToString(CreatedAtFormat, CultureInfo.InvariantCulture));
            writer.WriteEndObject();
            writer.WriteEndArray();
            writer.WriteEndObject();
        }
        return stream.ToArray();
    }

    // Rotation preparation reuses the same DPAPI/format without constructing another nested store on disk.
    internal static byte[] ProtectVersionMaterial(Guid installationId,int version,byte[] key)
    {
        if(installationId==Guid.Empty || version is < 1 or > 1_000_000 || key.Length!=MfaKeyRing.KeyBytes)
            throw Invalid("invalid version material");
        var entropy=MfaKeyRing.EntropyFor(installationId,version);
        var blob=Protect(key,entropy);var check=Unprotect(blob,entropy);
        try
        {
            if(!CryptographicOperations.FixedTimeEquals(key,check))throw Invalid("DPAPI roundtrip mismatch");
            return KeyFileBytes(installationId,version,blob);
        }
        finally{CryptographicOperations.ZeroMemory(check);CryptographicOperations.ZeroMemory(blob);}
    }

    private static byte[] KeyFileBytes(Guid installationId, int version, byte[] protectedKey)
    {
        using var stream = new MemoryStream();
        using (var writer = new Utf8JsonWriter(stream))
        {
            writer.WriteStartObject();
            writer.WriteString("format", MfaKeyRing.KeyFileFormat);
            writer.WriteNumber("formatVersion", MfaKeyRing.FormatVersion);
            writer.WriteString("installationId", installationId.ToString("D"));
            writer.WriteNumber("keyVersion", version);
            writer.WriteString("protection", MfaKeyRing.ProtectionName);
            writer.WriteString("protectedKey", Convert.ToBase64String(protectedKey));
            writer.WriteEndObject();
        }
        return stream.ToArray();
    }

    // DPAPI LocalMachine con entropía de instalación y versión. Copia nativa propia: el proveedor y el lector no se tocan.
    private static byte[] Protect(byte[] plain, byte[] entropy)
    {
        var input = Allocate(plain);
        var extra = Allocate(entropy);
        try
        {
            var inputBlob = new DataBlob { cbData = plain.Length, pbData = input };
            var entropyBlob = new DataBlob { cbData = entropy.Length, pbData = extra };
            if (!CryptProtectData(ref inputBlob, null, ref entropyBlob, IntPtr.Zero, IntPtr.Zero,
                    CryptProtectUiForbidden | CryptProtectLocalMachine, out var output))
                throw Creation(MfaKeyStoreCreationErrorKind.CreationFailed,
                    "mfa_key_protect_failed: DPAPI no protegió la clave (Win32 " + Marshal.GetLastWin32Error().ToString(CultureInfo.InvariantCulture) + ")");
            try
            {
                var result = new byte[output.cbData];
                Marshal.Copy(output.pbData, result, 0, result.Length);
                return result;
            }
            finally
            {
                LocalFree(output.pbData);
            }
        }
        finally
        {
            // La copia nativa de la clave en claro se pone a cero antes de liberarla.
            ZeroAndFree(input, plain.Length);
            Marshal.FreeHGlobal(extra);
        }
    }

    private static byte[] Unprotect(byte[] blob, byte[] entropy)
    {
        var input = Allocate(blob);
        var extra = Allocate(entropy);
        try
        {
            var inputBlob = new DataBlob { cbData = blob.Length, pbData = input };
            var entropyBlob = new DataBlob { cbData = entropy.Length, pbData = extra };
            if (!CryptUnprotectData(ref inputBlob, IntPtr.Zero, ref entropyBlob, IntPtr.Zero, IntPtr.Zero, CryptProtectUiForbidden, out var output))
                throw Creation(MfaKeyStoreCreationErrorKind.ValidationFailed,
                    "mfa_key_unprotect_failed: DPAPI no abrió el blob recién creado (Win32 " + Marshal.GetLastWin32Error().ToString(CultureInfo.InvariantCulture) + ")");
            try
            {
                if (output.cbData != MfaKeyRing.KeyBytes)
                    throw Creation(MfaKeyStoreCreationErrorKind.ValidationFailed, "mfa_key_length_invalid: la clave descifrada no mide 32 bytes");
                var result = new byte[output.cbData];
                Marshal.Copy(output.pbData, result, 0, result.Length);
                return result;
            }
            finally
            {
                ZeroAndFreeBlob(output);
            }
        }
        finally
        {
            Marshal.FreeHGlobal(input);
            Marshal.FreeHGlobal(extra);
        }
    }

    private static IntPtr Allocate(byte[] data)
    {
        var handle = Marshal.AllocHGlobal(data.Length);
        Marshal.Copy(data, 0, handle, data.Length);
        return handle;
    }

    private static void ZeroAndFree(IntPtr handle, int length)
    {
        Marshal.Copy(new byte[length], 0, handle, length);
        Marshal.FreeHGlobal(handle);
    }

    private static void ZeroAndFreeBlob(DataBlob blob)
    {
        if (blob.pbData == IntPtr.Zero) return;
        Marshal.Copy(new byte[blob.cbData], 0, blob.pbData, blob.cbData);
        LocalFree(blob.pbData);
    }

    private static bool Exists(string path) => Directory.Exists(path) || File.Exists(path);

    private static MfaKeyStoreCreationException Invalid(string detail) =>
        new(MfaKeyStoreCreationErrorKind.InvalidRequest, "mfa_key_store_request_invalid: " + detail, null, []);

    private static MfaKeyStoreCreationException Creation(MfaKeyStoreCreationErrorKind kind, string message, Exception? inner = null) =>
        new(kind, message, inner, []);

    // Objeto de la cadena. Owned: lo creó esta llamada (se puede retirar). Identity: identidad registrada.
    private sealed class Tracked(string path, bool isDirectory, bool owned, FileIdentity identity)
    {
        public string Path { get; private set; } = path;
        public bool IsDirectory { get; } = isDirectory;
        public bool Owned { get; private set; } = owned;
        public void PreservePublished(string publishedPath)
        {
            Path = publishedPath;
            Owned = false;
        }
        public FileIdentity Identity { get; } = identity;
    }

    private readonly record struct FileIdentity(uint Volume, ulong Index);

    // FILETIME alineado a 4 bytes, como en Windows. Con un long el relleno desplazaría los campos siguientes.
    [StructLayout(LayoutKind.Sequential)]
    private struct FileTime
    {
        public uint Low;
        public uint High;
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct ByHandleFileInformation
    {
        public uint FileAttributes;
        public FileTime CreationTime;
        public FileTime LastAccessTime;
        public FileTime LastWriteTime;
        public uint VolumeSerialNumber;
        public uint FileSizeHigh;
        public uint FileSizeLow;
        public uint NumberOfLinks;
        public uint FileIndexHigh;
        public uint FileIndexLow;
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct DataBlob
    {
        public int cbData;
        public IntPtr pbData;
    }

    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool CreateDirectoryW(string pathName, IntPtr securityAttributes);

    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern SafeFileHandle CreateFileW(string fileName, uint desiredAccess, uint shareMode, IntPtr securityAttributes,
        uint creationDisposition, uint flagsAndAttributes, IntPtr templateFile);

    [DllImport("kernel32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool GetFileInformationByHandle(SafeFileHandle file, out ByHandleFileInformation information);

    [DllImport("kernel32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool SetFileInformationByHandle(SafeFileHandle file, int informationClass, IntPtr information, uint bufferSize);

    [DllImport("crypt32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool CryptProtectData(ref DataBlob dataIn, [MarshalAs(UnmanagedType.LPWStr)] string? description,
        ref DataBlob optionalEntropy, IntPtr reserved, IntPtr promptStruct, int flags, out DataBlob dataOut);

    [DllImport("crypt32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool CryptUnprotectData(ref DataBlob dataIn, IntPtr description, ref DataBlob optionalEntropy,
        IntPtr reserved, IntPtr promptStruct, int flags, out DataBlob dataOut);

    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern IntPtr LocalFree(IntPtr memory);

}

internal enum MfaKeyStoreCreationErrorKind
{
    InvalidRequest,
    AlreadyExists,
    ValidationFailed,
    CreationFailed,
    PublishFailed,
}

// El mensaje contiene sólo códigos y detalles genéricos: nunca bytes de clave ni contenido de los archivos.
// Residue: rutas propias que no se pudieron retirar. Su presencia significa que el almacén no quedó limpio.
internal sealed class MfaKeyStoreCreationException(MfaKeyStoreCreationErrorKind kind, string message, Exception? inner,
    IReadOnlyList<string> residue) : Exception(message, inner)
{
    public MfaKeyStoreCreationErrorKind Kind { get; } = kind;

    public IReadOnlyList<string> Residue { get; } = residue;
}
