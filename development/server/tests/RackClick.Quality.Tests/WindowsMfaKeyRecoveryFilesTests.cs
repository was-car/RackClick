using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Runtime.Versioning;
using System.Security.AccessControl;
using System.Security.Cryptography;
using System.Security.Principal;
using System.Text;
using Microsoft.Win32.SafeHandles;
using RackClick.Server;
using Xunit;

namespace RackClick.Quality.Tests;

// Archivo privado del sobre RCKEY (MFA-L2g) con raíces TEMP nuevas, datos sintéticos y una carpeta del operador separada del
// origen y del destino. Mismo token y máquina de laboratorio: no se afirma portabilidad DPAPI ni custodia bajo el SID real del
// servicio. El lector del origen y el custodio del sobre son el grupo Usuarios; el servicio simulado es Usuarios autenticados,
// que no tiene concesión sobre el archivo. Los fixtures declaran al usuario de laboratorio como principal de confianza.
[SupportedOSPlatform("windows")]
public sealed class WindowsMfaKeyRecoveryFilesTests
{
    private static readonly SecurityIdentifier UsersSid = new(WellKnownSidType.BuiltinUsersSid, null);
    private static readonly SecurityIdentifier AuthenticatedUsersSid = new(WellKnownSidType.AuthenticatedUserSid, null);
    private static readonly SecurityIdentifier EveryoneSid = new(WellKnownSidType.WorldSid, null);
    private static readonly SecurityIdentifier LocalSystemSid = new(WellKnownSidType.LocalSystemSid, null);
    private static readonly SecurityIdentifier AdministratorsSid = new(WellKnownSidType.BuiltinAdministratorsSid, null);
    private const string Password = "clave-de-laboratorio-sobre-archivo";
    private const string FileName = "sobre-laboratorio.rckey";

    [Fact]
    public void ExportWritesOnlyCiphertextAndRecoversThroughTheFileInAnotherRoot()
    {
        using var lab = new Lab();
        var originKeys = CreateOrigin(lab);
        var before = lab.Snapshot(lab.OriginRoot);

        var receipt = WindowsMfaKeyRecoveryFiles.ExportToFile(lab.OriginRoot, lab.Origin, UsersSid, UsersSid, lab.Trusted, Password,
            lab.SafeFolder, FileName);

        Assert.Equal(before, lab.Snapshot(lab.OriginRoot));
        Assert.Equal(MfaEnvelopeFileOutcome.Published, receipt.Outcome);
        Assert.Equal(Path.Combine(lab.SafeFolder, FileName), receipt.Path);
        Assert.Equal(new[] { FileName }, lab.FolderEntries(lab.SafeFolder));

        var bytes = File.ReadAllBytes(receipt.Path);
        Assert.Equal(bytes.Length, receipt.Length);
        Assert.Equal(Convert.ToHexString(SHA256.HashData(bytes)).ToLowerInvariant(), receipt.Sha256);
        foreach (var (_, key) in originKeys)
            Assert.True(bytes.AsSpan().IndexOf(key.AsSpan()) < 0, "el archivo del sobre contiene una clave en claro");

        var recovered = WindowsMfaKeyRecoveryFiles.RecoverFromFile(receipt.Path, Password, lab.Origin, lab.DestinationRoot,
            lab.Destination, UsersSid, UsersSid, lab.Trusted, adaptDestinationInstallation: true);
        Assert.Equal(MfaEnvelopeFileOutcome.Recovered, recovered.Outcome);
        Assert.Equal(receipt.Sha256, recovered.Sha256);
        Assert.Equal(receipt.Length, recovered.Length);

        var provider = new WindowsMfaKeyProvider(lab.DestinationRoot, lab.Destination, UsersSid, lab.Trusted);
        foreach (var (version, key) in originKeys)
        {
            var copy = provider.GetKey(version);
            Assert.True(CryptographicOperations.FixedTimeEquals(key, copy), "la clave recuperada del archivo no coincide");
            CryptographicOperations.ZeroMemory(copy);
        }

        // Factor sintético cifrado con la clave 2 original: sigue descifrando con la clave recuperada del archivo.
        var secret = RandomNumberGenerator.GetBytes(20);
        var systemhaus = Guid.NewGuid();
        var user = Guid.NewGuid();
        var factor = MfaSecretCipher.Seal(originKeys[1].Key, 2, secret, systemhaus, user);
        var recoveredKey2 = provider.GetKey(2);
        var opened = MfaSecretCipher.Open(recoveredKey2, 2, factor, systemhaus, user);
        Assert.True(CryptographicOperations.FixedTimeEquals(secret, opened), "el factor no descifra con la clave recuperada");
        CryptographicOperations.ZeroMemory(recoveredKey2);
        CryptographicOperations.ZeroMemory(opened);
    }

    [Fact]
    public void PublishedFileHasItsDaclProtectedFromCreation()
    {
        using var lab = new Lab();
        CreateOrigin(lab);

        var receipt = WindowsMfaKeyRecoveryFiles.ExportToFile(lab.OriginRoot, lab.Origin, UsersSid, UsersSid, lab.Trusted, Password,
            lab.SafeFolder, FileName);

        var security = new FileInfo(receipt.Path).GetAccessControl();
        Assert.True(security.AreAccessRulesProtected, "la DACL del archivo hereda del padre");
        var rules = security.GetAccessRules(true, true, typeof(SecurityIdentifier)).Cast<FileSystemAccessRule>().ToArray();
        Assert.All(rules, rule => Assert.False(rule.IsInherited, "el archivo tiene una ACE heredada"));
        var identities = rules.Select(rule => rule.IdentityReference.Value).Distinct().OrderBy(value => value, StringComparer.Ordinal);
        var expected = lab.Trusted.Append(UsersSid).Select(sid => sid.Value).Distinct().OrderBy(value => value, StringComparer.Ordinal);
        Assert.Equal(expected, identities);
    }

    [Fact]
    public void PublishedFileThatNoLongerMatchesIsRetiredWithoutSuccess()
    {
        using var lab = new Lab();
        CreateOrigin(lab);

        var error = Assert.Throws<WindowsMfaKeyRecoveryFileException>(() =>
            WindowsMfaKeyRecoveryFiles.ExportToFile(lab.OriginRoot, lab.Origin, UsersSid, UsersSid, lab.Trusted, Password,
                lab.SafeFolder, FileName, afterPublish: path => File.WriteAllBytes(path, [1, 2, 3])));

        Assert.Equal(WindowsMfaKeyRecoveryFileErrorKind.ValidationFailed, error.Kind);
        Assert.Empty(lab.FolderEntries(lab.SafeFolder));
        Assert.Empty(error.Residue);
    }

    // MFA-L2G-01: un sustituto idéntico en bytes no es el archivo publicado. Se rechaza, se conserva y se declara como residuo.
    [Fact]
    public void IdenticalReplacementAfterPublishIsRejectedAndTheSubstituteIsPreserved()
    {
        using var lab = new Lab();
        CreateOrigin(lab);
        var target = Path.Combine(lab.SafeFolder, FileName);
        var reserved = Path.Combine(lab.Root, "original-publicado.rckey");

        var error = Assert.Throws<WindowsMfaKeyRecoveryFileException>(() =>
            WindowsMfaKeyRecoveryFiles.ExportToFile(lab.OriginRoot, lab.Origin, UsersSid, UsersSid, lab.Trusted, Password,
                lab.SafeFolder, FileName, afterPublish: path => ReplaceWithIdenticalCopy(path, reserved)));

        Assert.Equal(WindowsMfaKeyRecoveryFileErrorKind.ValidationFailed, error.Kind);
        Assert.Contains(target, error.Residue);
        Assert.True(File.Exists(reserved), "el original publicado no debía tocarse");
        Assert.True(File.Exists(target), "el sustituto ajeno debe conservarse");
        Assert.NotEqual(ObjectIdOf(reserved), ObjectIdOf(target));
    }

    // MFA-L2G-01: mientras el archivo final está retenido para su verificación, no se puede mover, reemplazar, escribir ni borrar.
    [Fact]
    public void PublishedFileCannotBeMovedReplacedOrDeletedWhileItIsHeld()
    {
        using var lab = new Lab();
        CreateOrigin(lab);
        var target = Path.Combine(lab.SafeFolder, FileName);
        var reserved = Path.Combine(lab.Root, "intento-de-movimiento.rckey");
        var attempts = new List<Exception?>();
        var identityWhileHeld = default((uint Volume, uint High, uint Low));

        var receipt = WindowsMfaKeyRecoveryFiles.ExportToFile(lab.OriginRoot, lab.Origin, UsersSid, UsersSid, lab.Trusted, Password,
            lab.SafeFolder, FileName, whileHeld: path =>
            {
                identityWhileHeld = ObjectIdOf(path);
                attempts.Add(Attempt(() => File.Move(path, reserved)));
                attempts.Add(Attempt(() => File.Delete(path)));
                attempts.Add(Attempt(() =>
                {
                    using var writer = new FileStream(path, FileMode.Open, FileAccess.Write, FileShare.ReadWrite);
                }));
            });

        Assert.Equal(MfaEnvelopeFileOutcome.Published, receipt.Outcome);
        Assert.Equal(3, attempts.Count);
        Assert.All(attempts, attempt => Assert.True(attempt is IOException or UnauthorizedAccessException,
            "un intento concurrente sobre el archivo retenido tuvo éxito"));
        Assert.False(File.Exists(reserved), "el archivo retenido se movió");
        Assert.Equal(identityWhileHeld, ObjectIdOf(target));
        Assert.Equal(receipt.Sha256, Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(target))).ToLowerInvariant());
    }

    [Fact]
    public void ExistingExportDestinationIsRefusedAndItsBytesAreKept()
    {
        using var lab = new Lab();
        CreateOrigin(lab);
        var sentinel = new byte[] { 4, 4, 4 };
        File.WriteAllBytes(Path.Combine(lab.SafeFolder, FileName), sentinel);

        var error = Assert.Throws<WindowsMfaKeyRecoveryFileException>(() =>
            WindowsMfaKeyRecoveryFiles.ExportToFile(lab.OriginRoot, lab.Origin, UsersSid, UsersSid, lab.Trusted, Password,
                lab.SafeFolder, FileName));

        Assert.Equal(WindowsMfaKeyRecoveryFileErrorKind.AlreadyExists, error.Kind);
        Assert.Equal(sentinel, File.ReadAllBytes(Path.Combine(lab.SafeFolder, FileName)));
        Assert.Equal(new[] { FileName }, lab.FolderEntries(lab.SafeFolder));
    }

    [Fact]
    public void PublishRaceKeepsTheForeignFileAndRetiresTheStaging()
    {
        using var lab = new Lab();
        CreateOrigin(lab);
        var target = Path.Combine(lab.SafeFolder, FileName);
        var sentinel = new byte[] { 9, 8, 7 };

        var error = Assert.Throws<WindowsMfaKeyRecoveryFileException>(() =>
            WindowsMfaKeyRecoveryFiles.ExportToFile(lab.OriginRoot, lab.Origin, UsersSid, UsersSid, lab.Trusted, Password,
                lab.SafeFolder, FileName, beforePublish: () => File.WriteAllBytes(target, sentinel)));

        Assert.Equal(WindowsMfaKeyRecoveryFileErrorKind.AlreadyExists, error.Kind);
        Assert.Equal(sentinel, File.ReadAllBytes(target));
        Assert.Equal(new[] { FileName }, lab.FolderEntries(lab.SafeFolder));
        Assert.Empty(error.Residue);
    }

    [Fact]
    public void PublishFailureLeavesNoFileAndNoStagingAndNoSuccess()
    {
        using var lab = new Lab();
        CreateOrigin(lab);

        var error = Assert.Throws<WindowsMfaKeyRecoveryFileException>(() =>
            WindowsMfaKeyRecoveryFiles.ExportToFile(lab.OriginRoot, lab.Origin, UsersSid, UsersSid, lab.Trusted, Password,
                lab.SafeFolder, FileName, beforePublish: () => throw new IOException("fallo simulado de publicación")));

        Assert.Equal(WindowsMfaKeyRecoveryFileErrorKind.PublishFailed, error.Kind);
        Assert.IsType<IOException>(error.InnerException);
        Assert.Empty(lab.FolderEntries(lab.SafeFolder));
        Assert.Empty(error.Residue);
    }

    [Fact]
    public void StagingThatDoesNotRereadAsTheExportedEnvelopeIsRemoved()
    {
        using var lab = new Lab();
        CreateOrigin(lab);

        var error = Assert.Throws<WindowsMfaKeyRecoveryFileException>(() =>
            WindowsMfaKeyRecoveryFiles.ExportToFile(lab.OriginRoot, lab.Origin, UsersSid, UsersSid, lab.Trusted, Password,
                lab.SafeFolder, FileName, afterStagingWrite: path => File.WriteAllBytes(path, [1, 2, 3])));

        Assert.Equal(WindowsMfaKeyRecoveryFileErrorKind.ValidationFailed, error.Kind);
        Assert.Empty(lab.FolderEntries(lab.SafeFolder));
        Assert.Empty(error.Residue);
    }

    [Theory]
    [InlineData("dentro")]
    [InlineData("contenedora")]
    public void ExportFolderOverlappingTheInstancesRootIsRefusedBeforeAnyWrite(string shape)
    {
        using var lab = new Lab();
        CreateOrigin(lab);
        var folder = shape switch
        {
            "dentro" => Path.Combine(lab.OriginRoot, "sobres"),
            "contenedora" => lab.Root,
            _ => throw new ArgumentOutOfRangeException(nameof(shape), shape, null),
        };
        Directory.CreateDirectory(folder);
        var before = lab.Snapshot(lab.OriginRoot);

        var error = Assert.Throws<WindowsMfaKeyRecoveryFileException>(() =>
            WindowsMfaKeyRecoveryFiles.ExportToFile(lab.OriginRoot, lab.Origin, UsersSid, UsersSid, lab.Trusted, Password,
                folder, FileName));

        Assert.Equal(WindowsMfaKeyRecoveryFileErrorKind.InvalidRequest, error.Kind);
        Assert.Empty(Directory.EnumerateFiles(lab.Root, "*.rckey", SearchOption.AllDirectories));
        Assert.Equal(before, lab.Snapshot(lab.OriginRoot));
    }

    [Fact]
    public void ExportFolderWithAnEveryoneWriteAceIsRefusedAndNothingIsRepaired()
    {
        using var lab = new Lab();
        CreateOrigin(lab);
        var security = new DirectorySecurity(lab.SafeFolder, AccessControlSections.Access);
        security.AddAccessRule(new FileSystemAccessRule(EveryoneSid, FileSystemRights.Modify, InheritanceFlags.ContainerInherit |
            InheritanceFlags.ObjectInherit, PropagationFlags.None, AccessControlType.Allow));
        new DirectoryInfo(lab.SafeFolder).SetAccessControl(security);
        var before = lab.Snapshot(lab.SafeFolder);

        var error = Assert.Throws<WindowsMfaKeyRecoveryFileException>(() =>
            WindowsMfaKeyRecoveryFiles.ExportToFile(lab.OriginRoot, lab.Origin, UsersSid, UsersSid, lab.Trusted, Password,
                lab.SafeFolder, FileName));

        Assert.Equal(WindowsMfaKeyRecoveryFileErrorKind.FolderRejected, error.Kind);
        Assert.Empty(lab.FolderEntries(lab.SafeFolder));
        Assert.Equal(before, lab.Snapshot(lab.SafeFolder));
    }

    [Fact]
    public void ExportFolderThatIsAJunctionIsRefused()
    {
        using var lab = new Lab();
        CreateOrigin(lab);
        var junction = Path.Combine(lab.Root, "enlace-sobres");
        CreateLink("/J", junction, lab.SafeFolder);
        lab.Links.Add(junction);

        var error = Assert.Throws<WindowsMfaKeyRecoveryFileException>(() =>
            WindowsMfaKeyRecoveryFiles.ExportToFile(lab.OriginRoot, lab.Origin, UsersSid, UsersSid, lab.Trusted, Password,
                junction, FileName));

        Assert.Equal(WindowsMfaKeyRecoveryFileErrorKind.FolderRejected, error.Kind);
        Assert.Empty(lab.FolderEntries(lab.SafeFolder));
    }

    [Fact]
    public void ExportWithAMissingOriginVersionWritesNoFile()
    {
        using var lab = new Lab();
        CreateOrigin(lab);
        File.Delete(lab.OriginKeyFile(2));

        var error = Assert.Throws<WindowsMfaKeyRecoveryFileException>(() =>
            WindowsMfaKeyRecoveryFiles.ExportToFile(lab.OriginRoot, lab.Origin, UsersSid, UsersSid, lab.Trusted, Password,
                lab.SafeFolder, FileName));

        Assert.Equal(WindowsMfaKeyRecoveryFileErrorKind.ExportRejected, error.Kind);
        Assert.Equal(WindowsMfaKeyRecoveryErrorKind.SourceRejected, Assert.IsType<WindowsMfaKeyRecoveryException>(error.InnerException).Kind);
        Assert.Empty(lab.FolderEntries(lab.SafeFolder));
    }

    [Theory]
    [InlineData("")]
    [InlineData("sobre.bin")]
    [InlineData("..\\fuera.rckey")]
    [InlineData("../fuera.rckey")]
    [InlineData(".oculto.rckey")]
    [InlineData("con espacio.rckey")]
    public void EnvelopeFileNamesAreValidatedBeforeAnyWrite(string name)
    {
        using var lab = new Lab();
        CreateOrigin(lab);

        var error = Assert.Throws<WindowsMfaKeyRecoveryFileException>(() =>
            WindowsMfaKeyRecoveryFiles.ExportToFile(lab.OriginRoot, lab.Origin, UsersSid, UsersSid, lab.Trusted, Password,
                lab.SafeFolder, name));

        Assert.Equal(WindowsMfaKeyRecoveryFileErrorKind.InvalidRequest, error.Kind);
        Assert.Empty(lab.FolderEntries(lab.SafeFolder));
    }

    [Fact]
    public void TruncatedFileIsRefusedWithoutCreatingTheDestination()
    {
        using var lab = new Lab();
        var receipt = ExportToSafeFolder(lab);
        using (var stream = new FileStream(receipt.Path, FileMode.Open, FileAccess.Write, FileShare.None))
            stream.SetLength(stream.Length - 10);
        var before = File.ReadAllBytes(receipt.Path);

        var error = Assert.Throws<WindowsMfaKeyRecoveryFileException>(() => Recover(lab, receipt.Path));

        Assert.Equal(WindowsMfaKeyRecoveryFileErrorKind.RecoveryRejected, error.Kind);
        var inner = Assert.IsType<WindowsMfaKeyRecoveryException>(error.InnerException).Kind;
        Assert.True(inner is WindowsMfaKeyRecoveryErrorKind.EnvelopeRejected or WindowsMfaKeyRecoveryErrorKind.AuthenticationFailed,
            "un archivo truncado debe rechazarse antes de crear nada");
        Assert.False(Directory.Exists(lab.DestinationRoot), "un archivo truncado creó el destino");
        Assert.Equal(before, File.ReadAllBytes(receipt.Path));
    }

    [Fact]
    public void AlteredTagIsRefusedWithoutCreatingTheDestination()
    {
        using var lab = new Lab();
        var receipt = ExportToSafeFolder(lab);
        var bytes = File.ReadAllBytes(receipt.Path);
        bytes[^1] ^= 0x01;
        File.WriteAllBytes(receipt.Path, bytes);

        var error = Assert.Throws<WindowsMfaKeyRecoveryFileException>(() => Recover(lab, receipt.Path));

        Assert.Equal(WindowsMfaKeyRecoveryFileErrorKind.RecoveryRejected, error.Kind);
        Assert.Equal(WindowsMfaKeyRecoveryErrorKind.AuthenticationFailed, Assert.IsType<WindowsMfaKeyRecoveryException>(error.InnerException).Kind);
        Assert.False(Directory.Exists(lab.DestinationRoot), "un archivo alterado creó el destino");
    }

    [Fact]
    public void OversizedFileIsRefusedBeforeItIsReadOrAllocated()
    {
        using var lab = new Lab();
        var path = Path.Combine(lab.SafeFolder, FileName);
        File.WriteAllBytes(path, new byte[MfaKeyRecoveryEnvelope.MaxEnvelopeBytes + 1]);
        var readStarted = false;

        var error = Assert.Throws<WindowsMfaKeyRecoveryFileException>(() =>
            WindowsMfaKeyRecoveryFiles.RecoverFromFile(path, Password, lab.Origin, lab.DestinationRoot, lab.Destination, UsersSid,
                UsersSid, lab.Trusted, adaptDestinationInstallation: true, beforeEnvelopeRead: () => readStarted = true));

        Assert.Equal(WindowsMfaKeyRecoveryFileErrorKind.FileRejected, error.Kind);
        Assert.Equal(MfaKeyRingErrorKind.FileTooLarge, Assert.IsType<MfaKeyRingException>(error.InnerException).Kind);
        Assert.False(readStarted, "el archivo sobredimensionado llegó a la ventana de lectura");
        Assert.False(Directory.Exists(lab.DestinationRoot));
    }

    [Fact]
    public void HardLinkedEnvelopeIsRefused()
    {
        using var lab = new Lab();
        var receipt = ExportToSafeFolder(lab);
        var link = Path.Combine(lab.SafeFolder, "enlace-laboratorio.rckey");
        CreateLink("/H", link, receipt.Path);

        var error = Assert.Throws<WindowsMfaKeyRecoveryFileException>(() => Recover(lab, link));

        Assert.Equal(WindowsMfaKeyRecoveryFileErrorKind.FileRejected, error.Kind);
        Assert.Equal(MfaKeyRingErrorKind.UnsafePath, Assert.IsType<MfaKeyRingException>(error.InnerException).Kind);
        Assert.False(Directory.Exists(lab.DestinationRoot));
    }

    [Fact]
    public void EnvelopeWithAnEveryoneWriteAceIsRefused()
    {
        using var lab = new Lab();
        var receipt = ExportToSafeFolder(lab);
        var info = new FileInfo(receipt.Path);
        var security = info.GetAccessControl();
        security.AddAccessRule(new FileSystemAccessRule(EveryoneSid, FileSystemRights.Modify, AccessControlType.Allow));
        info.SetAccessControl(security);

        var error = Assert.Throws<WindowsMfaKeyRecoveryFileException>(() => Recover(lab, receipt.Path));

        Assert.Equal(WindowsMfaKeyRecoveryFileErrorKind.FileRejected, error.Kind);
        Assert.Equal(MfaKeyRingErrorKind.UnsafeAccess, Assert.IsType<MfaKeyRingException>(error.InnerException).Kind);
        Assert.False(Directory.Exists(lab.DestinationRoot));
    }

    [Fact]
    public void ServiceWithoutAnExplicitGrantCannotReadTheEnvelope()
    {
        using var lab = new Lab();
        var receipt = ExportToSafeFolder(lab);
        var before = File.ReadAllBytes(receipt.Path);
        // Carpeta que sólo concede lectura a Usuarios autenticados (el "servicio" simulado). El archivo conserva su DACL de
        // custodio, sin concesión para ese SID: el lector del servicio debe rechazarlo en el archivo, no en la carpeta.
        var serviceFolder = Path.Combine(lab.Root, "sobres-servicio");
        lab.CreateFolderGrantingReadTo(serviceFolder, AuthenticatedUsersSid);
        var moved = Path.Combine(serviceFolder, FileName);
        File.Move(receipt.Path, moved);

        var error = Assert.Throws<WindowsMfaKeyRecoveryFileException>(() =>
            WindowsMfaKeyRecoveryFiles.RecoverFromFile(moved, Password, lab.Origin, lab.DestinationRoot, lab.Destination,
                UsersSid, AuthenticatedUsersSid, lab.Trusted, adaptDestinationInstallation: true));

        Assert.Equal(WindowsMfaKeyRecoveryFileErrorKind.FileRejected, error.Kind);
        Assert.Equal(MfaKeyRingErrorKind.UnsafeAccess, Assert.IsType<MfaKeyRingException>(error.InnerException).Kind);
        Assert.False(Directory.Exists(lab.DestinationRoot));
        Assert.Equal(before, File.ReadAllBytes(moved));
    }

    [Fact]
    public void ConcurrentWritersAndDeletersCannotTouchTheEnvelopeWhileItIsRead()
    {
        using var lab = new Lab();
        var receipt = ExportToSafeFolder(lab);
        var before = File.ReadAllBytes(receipt.Path);
        Exception? writeAttempt = null;
        Exception? deleteAttempt = null;

        var recovered = WindowsMfaKeyRecoveryFiles.RecoverFromFile(receipt.Path, Password, lab.Origin, lab.DestinationRoot,
            lab.Destination, UsersSid, UsersSid, lab.Trusted, adaptDestinationInstallation: true, beforeEnvelopeRead: () =>
            {
                try
                {
                    using var writer = new FileStream(receipt.Path, FileMode.Open, FileAccess.Write, FileShare.ReadWrite);
                }
                catch (Exception ex)
                {
                    writeAttempt = ex;
                }
                try
                {
                    File.Delete(receipt.Path);
                }
                catch (Exception ex)
                {
                    deleteAttempt = ex;
                }
            });

        Assert.True(writeAttempt is IOException or UnauthorizedAccessException, "un escritor concurrente abrió el sobre durante la lectura");
        Assert.True(deleteAttempt is IOException or UnauthorizedAccessException, "un borrado concurrente tuvo éxito durante la lectura");
        Assert.Equal(MfaEnvelopeFileOutcome.Recovered, recovered.Outcome);
        Assert.Equal(before, File.ReadAllBytes(receipt.Path));
    }

    [Theory]
    [InlineData("dentro")]
    [InlineData("contenedora")]
    public void RecoveryDestinationOverlappingTheEnvelopeFolderIsRefused(string shape)
    {
        using var lab = new Lab();
        var receipt = ExportToSafeFolder(lab);
        var destination = shape switch
        {
            "dentro" => Path.Combine(lab.SafeFolder, "destino"),
            "contenedora" => lab.Root,
            _ => throw new ArgumentOutOfRangeException(nameof(shape), shape, null),
        };

        var error = Assert.Throws<WindowsMfaKeyRecoveryFileException>(() =>
            WindowsMfaKeyRecoveryFiles.RecoverFromFile(receipt.Path, Password, lab.Origin, destination, lab.Destination, UsersSid,
                UsersSid, lab.Trusted, adaptDestinationInstallation: true));

        Assert.Equal(WindowsMfaKeyRecoveryFileErrorKind.InvalidRequest, error.Kind);
        Assert.False(Directory.Exists(Path.Combine(destination, lab.Destination.ToString("D"))), "el destino se creó dentro del sobre");
    }

    [Theory]
    [InlineData("contraseña")]
    [InlineData("origen")]
    public void WrongPasswordOrSourceCreatesNothing(string shape)
    {
        using var lab = new Lab();
        var receipt = ExportToSafeFolder(lab);
        var password = shape == "contraseña" ? "clave-de-prueba-erronea" : Password;
        var source = shape == "origen" ? Guid.NewGuid() : lab.Origin;

        var error = Assert.Throws<WindowsMfaKeyRecoveryFileException>(() =>
            WindowsMfaKeyRecoveryFiles.RecoverFromFile(receipt.Path, password, source, lab.DestinationRoot, lab.Destination, UsersSid,
                UsersSid, lab.Trusted, adaptDestinationInstallation: true));

        Assert.Equal(WindowsMfaKeyRecoveryFileErrorKind.RecoveryRejected, error.Kind);
        var inner = Assert.IsType<WindowsMfaKeyRecoveryException>(error.InnerException).Kind;
        Assert.Equal(shape == "contraseña" ? WindowsMfaKeyRecoveryErrorKind.AuthenticationFailed : WindowsMfaKeyRecoveryErrorKind.PayloadRejected, inner);
        Assert.False(Directory.Exists(lab.DestinationRoot), "un fallo de autenticación o de origen creó el destino");
    }

    [Fact]
    public void ExistingDestinationIsPreservedWhenRecoveryFromFileIsRefused()
    {
        using var lab = new Lab();
        var receipt = ExportToSafeFolder(lab);
        Directory.CreateDirectory(lab.DestinationKeys);
        var sentinel = Path.Combine(lab.DestinationKeys, "centinela.bin");
        File.WriteAllBytes(sentinel, [5, 6, 7]);
        var before = lab.Snapshot(lab.DestinationRoot);

        var error = Assert.Throws<WindowsMfaKeyRecoveryFileException>(() => Recover(lab, receipt.Path));

        Assert.Equal(WindowsMfaKeyRecoveryFileErrorKind.RecoveryRejected, error.Kind);
        Assert.Equal(WindowsMfaKeyRecoveryErrorKind.DestinationRejected, Assert.IsType<WindowsMfaKeyRecoveryException>(error.InnerException).Kind);
        Assert.Equal(new byte[] { 5, 6, 7 }, File.ReadAllBytes(sentinel));
        Assert.Equal(before, lab.Snapshot(lab.DestinationRoot));
    }

    [Fact]
    public void MissingEnvelopeFileIsRefused()
    {
        using var lab = new Lab();

        var error = Assert.Throws<WindowsMfaKeyRecoveryFileException>(() =>
            WindowsMfaKeyRecoveryFiles.RecoverFromFile(Path.Combine(lab.SafeFolder, FileName), Password, lab.Origin, lab.DestinationRoot,
                lab.Destination, UsersSid, UsersSid, lab.Trusted, adaptDestinationInstallation: true));

        Assert.Equal(WindowsMfaKeyRecoveryFileErrorKind.FileRejected, error.Kind);
        Assert.Equal(MfaKeyRingErrorKind.MissingFile, Assert.IsType<MfaKeyRingException>(error.InnerException).Kind);
    }

    [Fact]
    public void ReceiptCarriesOnlyPathLengthHashAndOutcome()
    {
        using var lab = new Lab();
        var receipt = ExportToSafeFolder(lab);

        var names = typeof(MfaEnvelopeFileReceipt).GetProperties().Select(property => property.Name).OrderBy(name => name, StringComparer.Ordinal);
        Assert.Equal(new[] { "Length", "Outcome", "Path", "Sha256" }, names);
        Assert.DoesNotContain(Password, receipt.ToString(), StringComparison.Ordinal);
    }

    // Sustituto con el mismo contenido y la misma ACL: otro objeto del sistema de archivos. El original queda en "reserved".
    private static void ReplaceWithIdenticalCopy(string path, string reserved)
    {
        var security = new FileInfo(path).GetAccessControl(AccessControlSections.Access);
        File.Move(path, reserved);
        File.Copy(reserved, path);
        new FileInfo(path).SetAccessControl(security);
    }

    // Identidad nativa del objeto (volumen e índice): distingue dos archivos con los mismos bytes.
    private static (uint Volume, uint High, uint Low) ObjectIdOf(string path)
    {
        using var stream = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.Read);
        Assert.True(GetFileInformationByHandle(stream.SafeFileHandle, out var info));
        return (info.VolumeSerialNumber, info.FileIndexHigh, info.FileIndexLow);
    }

    private static Exception? Attempt(Action action)
    {
        try
        {
            action();
            return null;
        }
        catch (Exception ex)
        {
            return ex;
        }
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct NativeFileTime
    {
        public uint Low;
        public uint High;
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct NativeInfo
    {
        public uint Attributes;
        public NativeFileTime Created;
        public NativeFileTime Accessed;
        public NativeFileTime Written;
        public uint VolumeSerialNumber;
        public uint SizeHigh;
        public uint SizeLow;
        public uint NumberOfLinks;
        public uint FileIndexHigh;
        public uint FileIndexLow;
    }

    [DllImport("kernel32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool GetFileInformationByHandle(SafeFileHandle handle, out NativeInfo info);

    // Origen creado con el escritor: versión 1 retirada y versión 2 activa. Claves sintéticas y nuevas.
    private static List<(int Version, byte[] Key)> CreateOrigin(Lab lab)
    {
        var keys = new List<(int Version, byte[] Key)>
        {
            (1, RandomNumberGenerator.GetBytes(MfaKeyRing.KeyBytes)),
            (2, RandomNumberGenerator.GetBytes(MfaKeyRing.KeyBytes)),
        };
        var ring = Encoding.UTF8.GetBytes(MfaKeyJson.Ring(lab.Origin,
            MfaKeyJson.Entry(1, "retired", "2026-10-01T08:30:00Z") + "," + MfaKeyJson.Entry(2, "active", "2026-10-25T10:00:00Z")));
        WindowsMfaKeyStoreWriter.CreateStoreFromMaterial(lab.OriginRoot, lab.Origin, UsersSid, lab.Trusted, ring, keys);
        return keys;
    }

    private static MfaEnvelopeFileReceipt ExportToSafeFolder(Lab lab)
    {
        CreateOrigin(lab);
        return WindowsMfaKeyRecoveryFiles.ExportToFile(lab.OriginRoot, lab.Origin, UsersSid, UsersSid, lab.Trusted, Password,
            lab.SafeFolder, FileName);
    }

    private static MfaEnvelopeFileReceipt Recover(Lab lab, string path) =>
        WindowsMfaKeyRecoveryFiles.RecoverFromFile(path, Password, lab.Origin, lab.DestinationRoot, lab.Destination, UsersSid,
            UsersSid, lab.Trusted, adaptDestinationInstallation: true);

    // Enlace duro o de unión creado con cmd: no requiere privilegios elevados en NTFS. Un fallo de la herramienta falla la prueba.
    private static void CreateLink(string switchName, string link, string target)
    {
        using var process = Process.Start(new ProcessStartInfo("cmd.exe", $"/c mklink {switchName} \"{link}\" \"{target}\"")
        {
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false,
        }) ?? throw new InvalidOperationException("no se pudo iniciar cmd");
        var output = process.StandardOutput.ReadToEnd() + process.StandardError.ReadToEnd();
        process.WaitForExit();
        Assert.True(process.ExitCode == 0, "mklink falló: " + output.Trim());
    }

    // Raíz TEMP nueva por prueba: origen, carpeta del operador y destino son carpetas separadas bajo la misma raíz.
    private sealed class Lab : IDisposable
    {
        public Lab()
        {
            Root = Path.Combine(Path.GetTempPath(), "rackclick-mfa-l2g", Guid.NewGuid().ToString("N"));
            Directory.CreateDirectory(Root);
            Origin = Guid.NewGuid();
            Destination = Guid.NewGuid();
            Me = WindowsIdentity.GetCurrent().User ?? throw new InvalidOperationException("sin SID de usuario");
            Trusted = [Me, LocalSystemSid, AdministratorsSid];
            CreateSafeFolder(SafeFolder);
        }

        public string Root { get; }
        public Guid Origin { get; }
        public Guid Destination { get; }
        public SecurityIdentifier Me { get; }
        public SecurityIdentifier[] Trusted { get; }

        public string OriginRoot => Path.Combine(Root, "origen");
        public string SafeFolder => Path.Combine(Root, "sobres");
        public string DestinationRoot => Path.Combine(Root, "destino");
        public string DestinationInstallation => Path.Combine(DestinationRoot, Destination.ToString("D"));
        public string DestinationKeys => Path.Combine(DestinationInstallation, WindowsMfaKeyProvider.KeysFolderName);
        public string DestinationRing => Path.Combine(DestinationKeys, MfaKeyRing.RingFileName);

        public string OriginKeyFile(int version) =>
            Path.Combine(OriginRoot, Origin.ToString("D"), WindowsMfaKeyProvider.KeysFolderName, MfaKeyRing.KeyFileName(version));

        // Carpeta del operador: protegida, con control total de confianza y lectura explícita del custodio (Usuarios). El lector
        // aprobado rechaza cualquier otra lectura concedida, así que el servicio simulado no aparece aquí.
        public void CreateSafeFolder(string path) => CreateFolderGrantingReadTo(path, UsersSid);

        // Carpeta protegida cuyo único lector explícito es el SID indicado.
        public void CreateFolderGrantingReadTo(string path, SecurityIdentifier reader)
        {
            Directory.CreateDirectory(path);
            const InheritanceFlags inherit = InheritanceFlags.ContainerInherit | InheritanceFlags.ObjectInherit;
            var security = new DirectorySecurity();
            security.SetAccessRuleProtection(true, false);
            foreach (var sid in Trusted)
                security.AddAccessRule(new FileSystemAccessRule(sid, FileSystemRights.FullControl, inherit, PropagationFlags.None,
                    AccessControlType.Allow));
            security.AddAccessRule(new FileSystemAccessRule(reader, FileSystemRights.ReadAndExecute, inherit, PropagationFlags.None,
                AccessControlType.Allow));
            new DirectoryInfo(path).SetAccessControl(security);
        }

        public string[] FolderEntries(string folder) =>
            Directory.Exists(folder)
                ? Directory.EnumerateFileSystemEntries(folder).Select(Path.GetFileName).Select(name => name!)
                    .OrderBy(name => name, StringComparer.Ordinal).ToArray()
                : [];

        // Listado del subárbol con longitud, fecha de escritura y ACL. Cualquier cambio visible cambia la lista.
        public string[] Snapshot(string top)
        {
            var entries = new List<string>();
            foreach (var path in Directory.EnumerateFileSystemEntries(top, "*", SearchOption.AllDirectories))
            {
                if (Directory.Exists(path))
                {
                    var directory = new DirectoryInfo(path);
                    var descriptor = directory.GetAccessControl(AccessControlSections.Access).GetSecurityDescriptorBinaryForm();
                    entries.Add(directory.FullName + "|" + directory.LastWriteTimeUtc.Ticks + "|" + Convert.ToBase64String(descriptor));
                }
                else
                {
                    var file = new FileInfo(path);
                    var descriptor = file.GetAccessControl(AccessControlSections.Access).GetSecurityDescriptorBinaryForm();
                    entries.Add(file.FullName + "|" + file.LastWriteTimeUtc.Ticks + "|" + file.Length + "|" + Convert.ToBase64String(descriptor));
                }
            }
            entries.Sort(StringComparer.Ordinal);
            return entries.ToArray();
        }

        // Uniones creadas por la prueba: se retiran sin recursión (el enlace, no su destino) antes de borrar la raíz.
        public List<string> Links { get; } = [];

        public void Dispose()
        {
            foreach (var link in Links)
            {
                if (Directory.Exists(link)) Directory.Delete(link);
            }
            Directory.Delete(Root, true);
            var parent = Path.GetDirectoryName(Root)!;
            // La carpeta padre compartida sólo se retira si ya no contiene nada de otras pruebas.
            if (Directory.Exists(parent) && !Directory.EnumerateFileSystemEntries(parent).Any())
                Directory.Delete(parent);
        }
    }
}
