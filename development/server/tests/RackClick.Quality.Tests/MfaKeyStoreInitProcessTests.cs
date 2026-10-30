using System.Diagnostics;
using System.Runtime.Versioning;
using System.Security.Principal;
using System.Text.Json;
using RackClick.Server;
using Xunit;

namespace RackClick.Quality.Tests;

// Modo CLI `--mfa-keys-init` con el servidor compilado (MFA-L2j), sin PostgreSQL, sin origen HTTPS y sin composición MFA del host.
// Sólo negativos de proceso: esta sesión no está elevada, así que el positivo real queda para el ensayo coordinado.
[SupportedOSPlatform("windows")]
public sealed class MfaKeyStoreInitProcessTests
{
    private static readonly SecurityIdentifier UsersSid = new(WellKnownSidType.BuiltinUsersSid, null);

    // Un modo CLI combinado con --migrate se rechaza antes de cualquier trabajo, con la respuesta de conflicto existente.
    [Fact]
    public void ModeConflictIsRejectedBeforeAnyWork()
    {
        var run = RunServer(new Dictionary<string, string?>(), stdin: "{}", "--mfa-keys-init", "--migrate");

        Assert.Equal(1, run.ExitCode);
        Assert.Contains("cli_mode_conflict", run.Output, StringComparison.Ordinal);
        Assert.DoesNotContain("listening", run.Output, StringComparison.OrdinalIgnoreCase);
    }

    // Sin elevación, sin PostgreSQL, sin origen HTTPS y sin proveedor MFA: el modo rechaza con su código, no crea nada y no escucha.
    [Fact]
    public void NotElevatedRunRejectsWithoutPostgresOriginOrProviderAndCreatesNothing()
    {
        Assert.SkipWhen(MfaKeyStoreInitCommand.IsElevatedAdministrator(), "sesión elevada: el rechazo real no aplica en este proceso");
        var root = Path.Combine(Path.GetTempPath(), "rackclick-mfa-l2j-proceso-" + Guid.NewGuid().ToString("N"));
        var input = JsonSerializer.Serialize(new
        {
            instancesRoot = Path.Combine(root, "instancias"),
            installationId = Guid.NewGuid().ToString("D"),
            readerSid = UsersSid.Value,
        });
        try
        {
            var run = RunServer(new Dictionary<string, string?>
            {
                ["ConnectionStrings__RackClick"] = null,
                ["PublicOrigin"] = null,
                ["MfaKeyStore__Enabled"] = "true",
                ["MfaKeyStore__InstancesRoot"] = null,
                ["MfaKeyStore__InstallationId"] = null,
            }, stdin: input, "--mfa-keys-init");

            Assert.Equal(1, run.ExitCode);
            Assert.Equal("{\"status\":\"rejected\",\"code\":\"mfa_keystore_init_not_elevated\",\"residue\":\"none\"}", run.Output.Trim());
            Assert.DoesNotContain("listening", run.Output, StringComparison.OrdinalIgnoreCase);
            Assert.False(Directory.Exists(root), "sin elevación se creó el almacén");
        }
        finally
        {
            if (Directory.Exists(root)) Directory.Delete(root, true);
        }
    }

    // Ejecuta el servidor compilado con variables propias y una entrada estándar cerrada al final.
    private static ServerRun RunServer(IReadOnlyDictionary<string, string?> environment, string stdin, params string[] arguments)
    {
        var apphost = Path.Combine(AppContext.BaseDirectory, "RackClick.Server.exe");
        Assert.True(File.Exists(apphost), "falta RackClick.Server.exe en la carpeta de pruebas");
        var start = new ProcessStartInfo(apphost)
        {
            RedirectStandardInput = true,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false,
            WorkingDirectory = AppContext.BaseDirectory,
        };
        foreach (var argument in arguments) start.ArgumentList.Add(argument);
        start.Environment["ASPNETCORE_ENVIRONMENT"] = "Production";
        start.Environment["ConnectionStrings__RackClick"] = "Host=127.0.0.1;Port=1;Database=rackclick_inexistente;Username=u;Password=p;Timeout=2";
        start.Environment["PublicOrigin"] = "https://rackclick.test";
        foreach (var (name, value) in environment)
        {
            if (value is null) start.Environment.Remove(name);
            else start.Environment[name] = value;
        }
        using var process = Process.Start(start) ?? throw new InvalidOperationException("no se pudo iniciar el servidor");
        process.StandardInput.Write(stdin);
        process.StandardInput.Close();
        var output = process.StandardOutput.ReadToEndAsync();
        var error = process.StandardError.ReadToEndAsync();
        if (!process.WaitForExit(TimeSpan.FromSeconds(120)))
        {
            process.Kill(entireProcessTree: true);
            throw new InvalidOperationException("el servidor no terminó: posible listener abierto");
        }
        return new ServerRun(process.ExitCode, output.Result, error.Result);
    }

    private sealed record ServerRun(int ExitCode, string Output, string Error);
}
