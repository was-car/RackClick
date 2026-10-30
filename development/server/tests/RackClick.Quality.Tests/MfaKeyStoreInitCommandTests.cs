using System.Runtime.Versioning;
using System.Security.AccessControl;
using System.Security.Cryptography;
using System.Security.Principal;
using System.Text;
using System.Text.Json;
using RackClick.Server;
using Xunit;

namespace RackClick.Quality.Tests;

// Inicialización local del almacén MFA (MFA-L2j) con el seam interno de elevación y confianza. La rama productiva (elevación real y
// confianza fija SYSTEM/Administradores) sólo se ejecuta en su rechazo, porque esta sesión no está elevada; el positivo usa el seam
// con confianza de laboratorio y lo declara. No se presenta como identidad efectiva del servicio.
[SupportedOSPlatform("windows")]
public sealed class MfaKeyStoreInitCommandTests
{
    private static readonly SecurityIdentifier UsersSid = new(WellKnownSidType.BuiltinUsersSid, null);
    private static readonly SecurityIdentifier LocalSystemSid = new(WellKnownSidType.LocalSystemSid, null);
    private static readonly SecurityIdentifier AdministratorsSid = new(WellKnownSidType.BuiltinAdministratorsSid, null);
    private static readonly SecurityIdentifier EveryoneSid = new(WellKnownSidType.WorldSid, null);

    [Fact]
    public void NotElevatedRejectsWithoutReadingInputOrCreatingAnything()
    {
        using var fixture = Fixture.Create();
        var output = new StringWriter();

        var exit = MfaKeyStoreInitCommand.Run(new TrapReader(), output, elevated: false, TestTrust(), null, null);

        Assert.Equal(1, exit);
        Assert.Equal("{\"status\":\"rejected\",\"code\":\"mfa_keystore_init_not_elevated\",\"residue\":\"none\"}", output.ToString().Trim());
        Assert.False(Directory.Exists(fixture.Root), "sin elevación se creó el almacén");
    }

    // Rama productiva real: sólo se ejecuta si esta sesión no está elevada. Si lo está, el caso se omite declaradamente.
    [Fact]
    public void ProductionRunRejectsTheRealNonElevatedSessionBeforeAnyWork()
    {
        Assert.SkipWhen(MfaKeyStoreInitCommand.IsElevatedAdministrator(), "sesión elevada: el rechazo real no aplica");
        using var fixture = Fixture.Create();
        var output = new StringWriter();

        var exit = MfaKeyStoreInitCommand.Run(new TrapReader(), output);

        Assert.Equal(1, exit);
        Assert.Equal("mfa_keystore_init_not_elevated", Field(output.ToString(), "code"));
        Assert.False(Directory.Exists(fixture.Root));
    }

    [Theory]
    [InlineData("no-json")]
    [InlineData("arreglo")]
    [InlineData("campo-ausente")]
    [InlineData("campo-extra")]
    [InlineData("tipo-invalido")]
    [InlineData("duplicado")]
    [InlineData("comentario")]
    [InlineData("demasiado-grande")]
    public void InvalidInputIsRejectedBeforeAnyWrite(string shape)
    {
        using var fixture = Fixture.Create();
        var json = shape switch
        {
            "no-json" => "{no-es-json",
            "arreglo" => "[]",
            "campo-ausente" => "{\"instancesRoot\":\"" + Esc(fixture.Root) + "\",\"installationId\":\"" + fixture.Installation.ToString("D") + "\"}",
            "campo-extra" => Input(fixture) .Insert(1, "\"extra\":\"x\","),
            "tipo-invalido" => "{\"instancesRoot\":\"" + Esc(fixture.Root) + "\",\"installationId\":42,\"readerSid\":\"" + UsersSid.Value + "\"}",
            "duplicado" => "{\"instancesRoot\":\"" + Esc(fixture.Root) + "\",\"instancesRoot\":\"" + Esc(fixture.Root) + "\",\"installationId\":\"" +
                fixture.Installation.ToString("D") + "\",\"readerSid\":\"" + UsersSid.Value + "\"}",
            "comentario" => "{ /* x */ \"instancesRoot\":\"" + Esc(fixture.Root) + "\",\"installationId\":\"" + fixture.Installation.ToString("D") +
                "\",\"readerSid\":\"" + UsersSid.Value + "\"}",
            "demasiado-grande" => "{\"instancesRoot\":\"" + new string('a', 5000) + "\",\"installationId\":\"" + fixture.Installation.ToString("D") +
                "\",\"readerSid\":\"" + UsersSid.Value + "\"}",
            _ => throw new ArgumentOutOfRangeException(nameof(shape), shape, null),
        };
        var output = new StringWriter();

        var exit = Run(json, output);

        Assert.Equal(1, exit);
        Assert.Equal("rejected", Field(output.ToString(), "status"));
        var expected = shape == "demasiado-grande" ? "mfa_keystore_init_input_too_large" : "mfa_keystore_init_input_invalid";
        Assert.Equal(expected, Field(output.ToString(), "code"));
        Assert.False(Directory.Exists(fixture.Root), "una entrada inválida creó el almacén");
    }

    [Theory]
    [InlineData("raiz-relativa", "mfa_keystore_init_root_relative")]
    [InlineData("raiz-con-nul", "mfa_keystore_init_root_invalid")]
    [InlineData("uuid-invalido", "mfa_keystore_init_installation_invalid")]
    [InlineData("uuid-vacio", "mfa_keystore_init_installation_invalid")]
    [InlineData("sid-invalido", "mfa_keystore_init_reader_invalid")]
    [InlineData("sid-confiable", "mfa_keystore_init_reader_trusted")]
    public void InvalidFieldsAreRejectedBeforeAnyWrite(string shape, string expectedCode)
    {
        using var fixture = Fixture.Create();
        var root = shape switch
        {
            "raiz-relativa" => "instancias-relativas",
            "raiz-con-nul" => fixture.Root + "\0cola",
            _ => fixture.Root,
        };
        var installation = shape is "uuid-invalido" ? "no-es-un-uuid" : shape == "uuid-vacio" ? Guid.Empty.ToString("D") : fixture.Installation.ToString("D");
        var reader = shape switch
        {
            "sid-invalido" => "no-es-un-sid",
            "sid-confiable" => LocalSystemSid.Value,
            _ => UsersSid.Value,
        };
        var output = new StringWriter();

        var exit = Run(Json(root, installation, reader), output);

        Assert.Equal(1, exit);
        Assert.Equal(expectedCode, Field(output.ToString(), "code"));
        Assert.False(Directory.Exists(fixture.Root), "un campo inválido creó el almacén");
    }

    [Theory]
    [InlineData("vacio")]
    [InlineData("parcial")]
    [InlineData("corrupto")]
    [InlineData("archivo")]
    public void ExistingDestinationIsPreservedAndNeverAdopted(string shape)
    {
        using var fixture = Fixture.Create();
        var installationFolder = Path.Combine(fixture.Root, fixture.Installation.ToString("D"));
        Directory.CreateDirectory(installationFolder);
        var keys = Path.Combine(installationFolder, "mfa-keys");
        switch (shape)
        {
            case "vacio":
                Directory.CreateDirectory(keys);
                break;
            case "parcial":
                Directory.CreateDirectory(keys);
                File.WriteAllText(Path.Combine(keys, "ring.json"), "{\"format\"", Encoding.UTF8);
                break;
            case "corrupto":
                Directory.CreateDirectory(keys);
                File.WriteAllBytes(Path.Combine(keys, "ring.json"), [0xFF, 0x00, 0x7B]);
                File.WriteAllBytes(Path.Combine(keys, "key-v1.dpapi.json"), [1, 2, 3, 4]);
                break;
            case "archivo":
                File.WriteAllBytes(keys, [9, 8, 7]);
                break;
            default:
                throw new ArgumentOutOfRangeException(nameof(shape), shape, null);
        }
        var before = fixture.Listing();
        var output = new StringWriter();

        var exit = Run(Json(fixture), output);

        Assert.Equal(1, exit);
        Assert.Equal("rejected", Field(output.ToString(), "status"));
        Assert.Equal("mfa_keystore_init_exists", Field(output.ToString(), "code"));
        Assert.Equal(before, fixture.Listing());
    }

    // Un ancestro que no cumple el contrato se rechaza y se conserva: el comando no añade permisos para arreglarlo.
    [Fact]
    public void UnsafeAncestorIsRefusedAndKeptWithoutRepair()
    {
        using var fixture = Fixture.Create();
        Directory.CreateDirectory(fixture.Root);
        var security = new DirectorySecurity(fixture.Root, AccessControlSections.Access);
        security.AddAccessRule(new FileSystemAccessRule(EveryoneSid, FileSystemRights.Modify,
            InheritanceFlags.ContainerInherit | InheritanceFlags.ObjectInherit, PropagationFlags.None, AccessControlType.Allow));
        new DirectoryInfo(fixture.Root).SetAccessControl(security);
        var before = fixture.Listing();
        var output = new StringWriter();

        var exit = Run(Json(fixture), output);

        Assert.Equal(1, exit);
        Assert.Equal("failed", Field(output.ToString(), "status"));
        Assert.Equal("mfa_keystore_init_failed", Field(output.ToString(), "code"));
        Assert.Equal("none", Field(output.ToString(), "residue"));
        Assert.False(Directory.Exists(Path.Combine(fixture.Root, fixture.Installation.ToString("D"))), "se creó bajo un ancestro inseguro");
        Assert.Equal(before, fixture.Listing());
    }

    // Residuo declarado: el writer no puede retirar un archivo retenido en exclusiva. La salida dice "declared" y no imprime rutas.
    [Fact]
    public void ResidueIsDeclaredWithoutPrintingPaths()
    {
        using var fixture = Fixture.Create();
        FileStream? hold = null;
        var output = new StringWriter();
        try
        {
            var exit = MfaKeyStoreInitCommand.Run(new StringReader(Json(fixture)), output, elevated: true, TestTrust(),
                beforePublish: () =>
                {
                    var staging = Directory.EnumerateDirectories(Path.Combine(fixture.Root, fixture.Installation.ToString("D")),
                        "mfa-keys.preparando-*").Single();
                    hold = new FileStream(Path.Combine(staging, "ring.json"), FileMode.Open, FileAccess.Read, FileShare.None);
                    throw new IOException("fallo simulado de publicación");
                },
                beforeOwnFolderCreation: null);

            Assert.Equal(1, exit);
            Assert.Equal("failed", Field(output.ToString(), "status"));
            Assert.Equal("mfa_keystore_init_failed", Field(output.ToString(), "code"));
            Assert.Equal("declared", Field(output.ToString(), "residue"));
            Assert.DoesNotContain(fixture.Root, output.ToString(), StringComparison.OrdinalIgnoreCase);
            Assert.DoesNotContain("preparando", output.ToString(), StringComparison.OrdinalIgnoreCase);
        }
        finally
        {
            hold?.Dispose();
        }
    }

    // Positivo con el seam: el escritor aprobado crea el almacén, la versión inicial es activa y una segunda ejecución no lo toca.
    [Fact]
    public void InitializationDelegatesToTheApprovedWriterAndNeverOverwrites()
    {
        using var fixture = Fixture.Create();
        var output = new StringWriter();

        var exit = Run(Json(fixture), output);

        Assert.Equal(0, exit);
        Assert.Equal("{\"status\":\"created\",\"residue\":\"none\"}", output.ToString().Trim());
        var active = new WindowsMfaKeyProvider(fixture.Root, fixture.Installation, UsersSid, TestTrust()).GetActiveKey();
        Assert.Equal(1, active.Version);
        Assert.Equal(MfaKeyRing.KeyBytes, active.Key.Length);
        CryptographicOperations.ZeroMemory(active.Key);
        var before = fixture.Listing();

        var second = new StringWriter();
        var exitAgain = Run(Json(fixture), second);

        Assert.Equal(1, exitAgain);
        Assert.Equal("mfa_keystore_init_exists", Field(second.ToString(), "code"));
        Assert.Equal(before, fixture.Listing());
    }

    // MFA-L2J-01: escapes Unicode sin pareja en nombres o valores son entrada inválida, sin excepción ni escritura.
    [Theory]
    [InlineData("valor-alto-solo")]
    [InlineData("valor-bajo-solo")]
    [InlineData("valor-alto-sin-bajo")]
    [InlineData("nombre-bajo")]
    [InlineData("nombre-alto-en-medio")]
    public void NonScalarNamesAndValuesAreRejectedAsInvalidInputWithoutWriting(string shape)
    {
        using var fixture = Fixture.Create();
        var root = Esc(fixture.Root);
        var installation = fixture.Installation.ToString("D");
        var json = shape switch
        {
            "valor-alto-solo" => "{\"instancesRoot\":\"" + root + "\\uD83D\",\"installationId\":\"" + installation + "\",\"readerSid\":\"" + UsersSid.Value + "\"}",
            "valor-bajo-solo" => "{\"instancesRoot\":\"" + root + "\",\"installationId\":\"" + installation + "\",\"readerSid\":\"\\uDE00\"}",
            "valor-alto-sin-bajo" => "{\"instancesRoot\":\"" + root + "\",\"installationId\":\"" + installation + "\",\"readerSid\":\"\\uD83D\\u0041\"}",
            "nombre-bajo" => "{\"instancesRoot\":\"" + root + "\",\"installationId\":\"" + installation + "\",\"readerSid\":\"" + UsersSid.Value + "\",\"\\uDE00\":\"x\"}",
            "nombre-alto-en-medio" => "{\"instancesRoot\":\"" + root + "\",\"installationId\":\"" + installation + "\",\"readerSid\":\"" + UsersSid.Value + "\",\"a\\uD800b\":\"x\"}",
            _ => throw new ArgumentOutOfRangeException(nameof(shape), shape, null),
        };
        var output = new StringWriter();

        var exit = Run(json, output);

        Assert.Equal(1, exit);
        Assert.Equal("mfa_keystore_init_input_invalid", Field(output.ToString(), "code"));
        Assert.Equal("none", Field(output.ToString(), "residue"));
        Assert.False(Directory.Exists(fixture.Root), "una entrada con escapes sin pareja creó el almacén");
    }

    // Control: un par suplementario válido se decodifica y llega a su validación. Aquí el SID inválido prueba que el parser lo aceptó.
    [Fact]
    public void ValidSurrogatePairInAValueReachesItsOwnValidation()
    {
        using var fixture = Fixture.Create();
        var json = "{\"instancesRoot\":\"" + Esc(fixture.Root) + "\",\"installationId\":\"" + fixture.Installation.ToString("D") +
            "\",\"readerSid\":\"S-1-5-32-545\\uD83D\\uDE00\"}";
        var output = new StringWriter();

        var exit = Run(json, output);

        Assert.Equal(1, exit);
        Assert.Equal("mfa_keystore_init_reader_invalid", Field(output.ToString(), "code"));
        Assert.False(Directory.Exists(fixture.Root));
    }

    // Control: un nombre con par suplementario válido se decodifica sin excepción y se rechaza sólo por ser un campo no permitido.
    [Fact]
    public void ValidSurrogatePairInANameIsDecodedAndRejectedAsAnUnknownField()
    {
        using var fixture = Fixture.Create();
        var json = Json(fixture).Insert(1, "\"\\uD83D\\uDE00\":\"x\",");
        var output = new StringWriter();

        var exit = Run(json, output);

        Assert.Equal(1, exit);
        Assert.Equal("mfa_keystore_init_input_invalid", Field(output.ToString(), "code"));
        Assert.False(Directory.Exists(fixture.Root));
    }

    private static int Run(string json, TextWriter output) =>
        MfaKeyStoreInitCommand.Run(new StringReader(json), output, elevated: true, TestTrust(), beforePublish: null, beforeOwnFolderCreation: null);

    // Confianza de laboratorio para el seam: el usuario actual, SYSTEM y Administradores. Sólo la usan las pruebas.
    private static SecurityIdentifier[] TestTrust() =>
        [System.Security.Principal.WindowsIdentity.GetCurrent().User!, LocalSystemSid, AdministratorsSid];

    private static string Json(Fixture fixture) => Json(fixture.Root, fixture.Installation.ToString("D"), UsersSid.Value);

    private static string Json(string root, string installation, string reader) =>
        JsonSerializer.Serialize(new { instancesRoot = root, installationId = installation, readerSid = reader });

    private static string Input(Fixture fixture) => Json(fixture);

    private static string Esc(string value) => value.Replace("\\", "\\\\", StringComparison.Ordinal);

    private static string? Field(string output, string name)
    {
        using var document = JsonDocument.Parse(output.Trim());
        return document.RootElement.TryGetProperty(name, out var value) ? value.GetString() : null;
    }

    // Lector que falla si se intenta leer: demuestra que el rechazo de elevación ocurre antes de tocar stdin.
    private sealed class TrapReader : TextReader
    {
        public override int Read(char[] buffer, int index, int count) => throw new InvalidOperationException("no debía leerse la entrada");
    }

    // Raíz nueva por prueba, dentro de una carpeta propia que se retira siempre.
    private sealed class Fixture : IDisposable
    {
        private Fixture(string folder, Guid installation)
        {
            Folder = folder;
            Installation = installation;
        }

        public string Folder { get; }

        public string Root => Path.Combine(Folder, "instancias");

        public Guid Installation { get; }

        public static Fixture Create()
        {
            var folder = Path.Combine(Path.GetTempPath(), "rackclick-mfa-l2j-" + Guid.NewGuid().ToString("N"));
            Directory.CreateDirectory(folder);
            return new Fixture(folder, Guid.NewGuid());
        }

        // Listado con tamaño, fecha y ACL de todo lo que hay bajo la carpeta propia.
        public string[] Listing()
        {
            if (!Directory.Exists(Folder)) return [];
            var entries = new List<string>();
            foreach (var path in Directory.EnumerateFileSystemEntries(Folder, "*", SearchOption.AllDirectories))
            {
                if (Directory.Exists(path))
                {
                    var directory = new DirectoryInfo(path);
                    entries.Add(directory.FullName + "|" + directory.LastWriteTimeUtc.Ticks + "|-|" +
                        Convert.ToBase64String(directory.GetAccessControl(AccessControlSections.Access).GetSecurityDescriptorBinaryForm()));
                }
                else
                {
                    var file = new FileInfo(path);
                    entries.Add(file.FullName + "|" + file.LastWriteTimeUtc.Ticks + "|" + file.Length + "|" +
                        Convert.ToBase64String(file.GetAccessControl(AccessControlSections.Access).GetSecurityDescriptorBinaryForm()));
                }
            }
            entries.Sort(StringComparer.Ordinal);
            return entries.ToArray();
        }

        public void Dispose()
        {
            if (Directory.Exists(Folder)) Directory.Delete(Folder, true);
        }
    }
}
