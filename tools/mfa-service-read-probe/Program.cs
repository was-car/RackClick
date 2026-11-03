using System.Security.AccessControl;
using System.Security.Cryptography;
using System.Security.Principal;
using System.Text;
using System.Text.Json;
using Microsoft.Win32.SafeHandles;
using RackClick.Server;

namespace RackClick.MfaServiceReadProbe;

// Verbos:
//   read            lectura con el token efectivo del servicio (único verbo que toca un servicio).
//   selftest-token  impersonación del token del operador: comprueba la identidad dentro del bloque y la restauración.
//   selftest-deny   fixture temporal propio con ACL conocida: comprueba que la comprobación de escritura detecta denegación y
//                   concesión. No recibe ni usa identidad de servicio.
//   selftest-privilege  ejercita DebugPrivilege con privilegios propios del proceso de prueba (SeChangeNotifyPrivilege ya
//                   habilitado; SeShutdownPrivilege deshabilitado por defecto). Nunca SeDebugPrivilege. Sólo de prueba; Run no lo usa.
// Un verbo desconocido se registra como "unknown" y no se refleja en la salida.
// Salida: una línea JSON con códigos constantes. Nunca claves, base64, hashes de clave, rutas, SIDs ni mensajes internos.
// Códigos de salida: 0 aprobado, 1 fallo, 2 uso incorrecto.
internal static class Program
{
    private const int Passed = 0;
    private const int Failed = 1;
    private const int Usage = 2;

    private static int Main(string[] args)
    {
        if (args.Length == 0) return Emit("usage", Usage, "usage");
        // Sólo se refleja un verbo conocido; cualquier otra entrada se registra como "unknown".
        var verb = (args[0] is "read" or "selftest-token" or "selftest-deny" or "selftest-privilege") ? args[0] : "unknown";
        try
        {
            if (!OperatingSystem.IsWindows()) return Emit(verb, Failed, "not_windows");
            return args[0] switch
            {
                "read" => RunRead(args),
                "selftest-token" => RunSelfTestToken(args),
                "selftest-deny" => RunSelfTestDeny(args),
                "selftest-privilege" => RunSelfTestPrivilege(args),
                _ => Emit("unknown", Usage, "usage"),
            };
        }
        catch (ProbeException ex)
        {
            return Emit(verb, Failed, ex.Code);
        }
        catch (Exception)
        {
            return Emit(verb, Failed, "unexpected_error");
        }
    }

    private static int RunRead(string[] args)
    {
        var options = ParseOptions(args, "instances-root", "installation-id", "service");
        if (options is null) return Emit("read", Usage, "usage");
        var root = options["instances-root"];
        if (!Path.IsPathFullyQualified(root)) return Emit("read", Usage, "usage");
        if (!Guid.TryParseExact(options["installation-id"], "D", out var installationId)) return Emit("read", Usage, "usage");
        var service = options["service"];
        if (!ValidServiceName(service)) return Emit("read", Usage, "usage");
        var fullRoot = Path.GetFullPath(root);
        if (!Directory.Exists(fullRoot)) return Emit("read", Failed, "store_root_missing");

        var evidence = ReadService(service, fullRoot, installationId);
        var code = Judge(evidence);
        return Emit("read", code.Length == 0 ? Passed : Failed, code, ReadFields(evidence));
    }

    private static int RunSelfTestToken(string[] args)
    {
        if (args.Length != 1) return Emit("selftest-token", Usage, "usage");
        var own = WindowsIdentity.GetCurrent().User ?? throw new ProbeException("operator_identity_unavailable");
        var verified = false;
        var token = IntPtr.Zero;
        SafeAccessTokenHandle? impersonation = null;
        try
        {
            if (!Native.OpenProcessToken(Native.GetCurrentProcess(), Native.TOKEN_DUPLICATE | Native.TOKEN_QUERY, out token))
                throw new ProbeException("token_access_denied");
            impersonation = TokenLink.DuplicateForImpersonation(token);
            verified = WindowsIdentity.RunImpersonated(impersonation,
                () => WindowsIdentity.GetCurrent(true)?.User?.Equals(own) == true);
        }
        finally
        {
            impersonation?.Dispose();
            if (token != IntPtr.Zero) Native.CloseHandle(token);
        }
        var restored = WindowsIdentity.GetCurrent().User?.Equals(own) == true;
        var ok = verified && restored;
        return Emit("selftest-token", ok ? Passed : Failed, ok ? "" : "impersonation_failed", new Dictionary<string, object?>
        {
            ["impersonationVerified"] = verified,
            ["identityRestored"] = restored,
        });
    }

    // Ejerce el código real de DebugPrivilege sin SeDebugPrivilege y sólo sobre privilegios del proceso de prueba:
    //   SeChangeNotifyPrivilege ya habilitado: no debe haber cambio ni alteración de atributos.
    //   SeShutdownPrivilege deshabilitado por defecto: se habilita durante el bloque y vuelve exactamente a deshabilitado.
    private static int RunSelfTestPrivilege(string[] args)
    {
        if (args.Length != 1) return Emit("selftest-privilege", Usage, "usage");
        var unchanged = ExercisePrivilege("SeChangeNotifyPrivilege");
        var changed = ExercisePrivilege("SeShutdownPrivilege");
        var unchangedWhenEnabled = (unchanged.Before & Native.SE_PRIVILEGE_ENABLED) != 0 && unchanged.Held && !unchanged.Changed
                                   && unchanged.During == unchanged.Before && unchanged.After == unchanged.Before;
        var changedAndRestored = (changed.Before & Native.SE_PRIVILEGE_ENABLED) == 0 && changed.Held && changed.Changed
                                 && (changed.During & Native.SE_PRIVILEGE_ENABLED) != 0 && changed.After == changed.Before;
        var ok = unchangedWhenEnabled && changedAndRestored;
        return Emit("selftest-privilege", ok ? Passed : Failed, ok ? "" : "privilege_selftest_failed", new Dictionary<string, object?>
        {
            ["unchangedWhenEnabled"] = unchangedWhenEnabled,
            ["changedAndRestoredExactly"] = changedAndRestored,
            ["SeDebugUsed"] = false,
        });
    }

    private sealed record PrivilegeExercise(uint Before, uint During, uint After, bool Held, bool Changed);

    private static PrivilegeExercise ExercisePrivilege(string name)
    {
        var token = IntPtr.Zero;
        try
        {
            if (!Native.OpenProcessToken(Native.GetCurrentProcess(), Native.TOKEN_QUERY, out token))
                throw new ProbeException("token_access_denied");
            var before = TokenPrivilegeQuery.Attributes(token, name);
            bool held;
            bool changed;
            uint during;
            using (var privilege = new DebugPrivilege(name))
            {
                held = privilege.EnsureEnabled();
                changed = privilege.Changed;
                during = TokenPrivilegeQuery.Attributes(token, name);
            }
            var after = TokenPrivilegeQuery.Attributes(token, name);
            return new PrivilegeExercise(before, during, after, held, changed);
        }
        finally
        {
            if (token != IntPtr.Zero) Native.CloseHandle(token);
        }
    }

    private static int RunSelfTestDeny(string[] args)
    {
        var options = ParseOptions(args, "variant");
        if (options is null || options["variant"] is not ("deny" or "allow")) return Emit("selftest-deny", Usage, "usage");
        var deny = options["variant"] == "deny";
        var own = WindowsIdentity.GetCurrent().User ?? throw new ProbeException("operator_identity_unavailable");
        var dir = Path.Combine(Path.GetTempPath(), "rackclick-mfa-l2l-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(dir);
        var file = Path.Combine(dir, "fixture.bin");
        var counts = new WriteCounts();
        var contentUnchanged = false;
        var cleaned = false;
        try
        {
            File.WriteAllBytes(file, Encoding.ASCII.GetBytes("synthetic-fixture"));
            var security = new FileSecurity();
            security.SetOwner(own);
            security.SetAccessRuleProtection(true, false);
            // Lectura completa (FILE_GENERIC_READ incluye FILE_READ_EA): sin ReadExtendedAttributes ni el titular puede leer.
            security.AddAccessRule(new FileSystemAccessRule(own, FileSystemRights.Read | FileSystemRights.Synchronize,
                AccessControlType.Allow));
            security.AddAccessRule(deny
                ? new FileSystemAccessRule(own, FileSystemRights.WriteData | FileSystemRights.ChangePermissions, AccessControlType.Deny)
                : new FileSystemAccessRule(own, FileSystemRights.FullControl, AccessControlType.Allow));
            new FileInfo(file).SetAccessControl(security);
            var before = Sha256Hex(file);

            var token = IntPtr.Zero;
            SafeAccessTokenHandle? impersonation = null;
            try
            {
                if (!Native.OpenProcessToken(Native.GetCurrentProcess(), Native.TOKEN_DUPLICATE | Native.TOKEN_QUERY, out token))
                    throw new ProbeException("token_access_denied");
                impersonation = TokenLink.DuplicateForImpersonation(token);
                counts = WindowsIdentity.RunImpersonated(impersonation, () => WriteProbe.CheckFile(file, own));
            }
            finally
            {
                impersonation?.Dispose();
                if (token != IntPtr.Zero) Native.CloseHandle(token);
            }
            contentUnchanged = Sha256Hex(file) == before;
        }
        finally
        {
            try
            {
                Directory.Delete(dir, true);
                cleaned = true;
            }
            catch (Exception)
            {
                cleaned = false;
            }
        }

        // WRITE_DAC concedido sólo se admite si lo explica la propiedad del fixture (el propio operador).
        var code = !contentUnchanged ? "content_changed"
            : counts.WriteGranted > 0 ? "unexpected_write_access"
            : counts.Inconclusive > 0 || counts.WriteDenied != counts.Targets ? "write_probe_inconclusive"
            : counts.DacGranted > counts.OwnerIsReader ? "unexpected_dac_access"
            : "";
        return Emit("selftest-deny", code.Length == 0 ? Passed : Failed, code, new Dictionary<string, object?>
        {
            ["variant"] = options["variant"],
            ["writeProbe"] = WriteFields(counts),
            ["contentUnchanged"] = contentUnchanged,
            ["fixtureRemoved"] = cleaned,
        });
    }

    private static ReadEvidence ReadService(string name, string root, Guid installationId)
    {
        var evidence = new ReadEvidence();
        var operatorSid = WindowsIdentity.GetCurrent().User ?? throw new ProbeException("operator_identity_unavailable");
        using var debug = new DebugPrivilege();
        var process = IntPtr.Zero;
        var token = IntPtr.Zero;
        SafeAccessTokenHandle? impersonation = null;
        try
        {
            var service = ServiceMeasure.Measure(name);
            process = Access.OpenProcess(service.ProcessId,
                Native.PROCESS_QUERY_INFORMATION | Native.PROCESS_QUERY_LIMITED_INFORMATION, debug);
            evidence.ProcessLinked = ImageMatch.Matches(ImageMatch.ProcessImage(process), service.BinaryPath);
            if (!evidence.ProcessLinked) throw new ProbeException("process_image_mismatch");

            token = Access.OpenToken(process, debug);
            impersonation = TokenLink.DuplicateForImpersonation(token);
            evidence.TokenMatched = TokenLink.SidOf(impersonation).Equals(service.AccountSid);
            if (!evidence.TokenMatched) throw new ProbeException("token_sid_mismatch");

            var outcome = WindowsIdentity.RunImpersonated(impersonation,
                () => ImpersonatedRead(service.AccountSid, root, installationId));
            evidence.Impersonated = outcome.Impersonated;
            evidence.Version = outcome.ActiveVersion;
            evidence.KeyBytes = outcome.KeyBytes;
            evidence.Writes = outcome.Writes;
        }
        catch (ProbeException ex)
        {
            evidence.Code = ex.Code;
        }
        finally
        {
            impersonation?.Dispose();
            if (token != IntPtr.Zero) Native.CloseHandle(token);
            if (process != IntPtr.Zero) Native.CloseHandle(process);
            debug.Restore();
            evidence.Debug = debug.State;
            evidence.IdentityRestored = WindowsIdentity.GetCurrent().User?.Equals(operatorSid) == true;
        }
        return evidence;
    }

    // Dentro de la impersonación: se verifica la identidad, se lee la clave activa con el proveedor aprobado y se comprueban
    // las escrituras. Ninguna de estas operaciones escribe en el almacén.
    private static StoreOutcome ImpersonatedRead(SecurityIdentifier accountSid, string root, Guid installationId)
    {
        var current = WindowsIdentity.GetCurrent(true)?.User;
        if (current is null || !current.Equals(accountSid)) throw new ProbeException("impersonation_not_effective");
        var installationFolder = Path.Combine(root, installationId.ToString("D"));
        var keysFolder = Path.Combine(installationFolder, WindowsMfaKeyProvider.KeysFolderName);
        var (version, length) = StoreRead.ReadActiveKey(root, installationId, accountSid);
        var writes = WriteProbe.CheckStore(root, installationFolder, keysFolder, accountSid);
        return new StoreOutcome(version, length, true, writes);
    }

    private static string Judge(ReadEvidence evidence)
    {
        if (evidence.Code.Length > 0) return evidence.Code;
        if (evidence.Debug == "restore_failed") return "debug_restore_failed";
        if (!evidence.IdentityRestored) return "identity_not_restored";
        if (!evidence.Impersonated) return "impersonation_not_effective";
        // El lector no puede ser propietario de ningún objetivo del almacén: la confianza del proveedor ya lo exige.
        if (evidence.Writes.OwnerIsReader > 0) return "store_owner_is_reader";
        if (evidence.Writes.WriteGranted > 0) return "unexpected_write_access";
        if (evidence.Writes.DacGranted > 0) return "unexpected_dac_access";
        if (evidence.Writes.Inconclusive > 0 || evidence.Writes.WriteDenied != evidence.Writes.Targets
            || evidence.Writes.DacDenied != evidence.Writes.Targets) return "write_probe_inconclusive";
        return "";
    }

    private static IReadOnlyDictionary<string, object?> ReadFields(ReadEvidence evidence) => new Dictionary<string, object?>
    {
        ["processLinked"] = evidence.ProcessLinked,
        ["tokenMatched"] = evidence.TokenMatched,
        ["impersonationVerified"] = evidence.Impersonated,
        ["identityRestored"] = evidence.IdentityRestored,
        ["debugPrivilege"] = evidence.Debug,
        ["store"] = new Dictionary<string, object?> { ["activeVersion"] = evidence.Version, ["keyBytes"] = evidence.KeyBytes },
        ["writeProbe"] = WriteFields(evidence.Writes),
    };

    private static Dictionary<string, object?> WriteFields(WriteCounts counts) => new()
    {
        ["targets"] = counts.Targets,
        ["writeDenied"] = counts.WriteDenied,
        ["writeGranted"] = counts.WriteGranted,
        ["dacDenied"] = counts.DacDenied,
        ["dacGranted"] = counts.DacGranted,
        ["ownerIsReader"] = counts.OwnerIsReader,
        ["inconclusive"] = counts.Inconclusive,
    };

    private static string Sha256Hex(string path) => Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path)));

    private static Dictionary<string, string>? ParseOptions(string[] args, params string[] allowed)
    {
        var values = new Dictionary<string, string>(StringComparer.Ordinal);
        for (var i = 1; i < args.Length; i += 2)
        {
            if (i + 1 >= args.Length) return null;
            var key = args[i];
            if (!key.StartsWith("--", StringComparison.Ordinal)) return null;
            var name = key[2..];
            if (Array.IndexOf(allowed, name) < 0 || values.ContainsKey(name)) return null;
            values[name] = args[i + 1];
        }
        return allowed.All(values.ContainsKey) ? values : null;
    }

    private static bool ValidServiceName(string name) =>
        name.Length is >= 1 and <= 256 && name.All(c => !char.IsControl(c) && c is not ('\\' or '/' or '"'));

    private static int Emit(string verb, int exit, string code, IReadOnlyDictionary<string, object?>? fields = null)
    {
        var payload = new Dictionary<string, object?>(StringComparer.Ordinal)
        {
            ["schemaVersion"] = 1,
            ["verb"] = verb,
            ["status"] = exit == Passed ? "passed" : exit == Usage ? "usage" : "failed",
            ["code"] = exit == Passed ? string.Empty : code,
        };
        if (fields is not null)
            foreach (var (key, value) in fields) payload[key] = value;
        Console.Out.WriteLine(JsonSerializer.Serialize(payload));
        return exit;
    }

    private sealed class ReadEvidence
    {
        public string Code { get; set; } = string.Empty;
        public bool ProcessLinked { get; set; }
        public bool TokenMatched { get; set; }
        public bool Impersonated { get; set; }
        public bool IdentityRestored { get; set; }
        public string Debug { get; set; } = "not_used";
        public int Version { get; set; }
        public int KeyBytes { get; set; }
        public WriteCounts Writes { get; set; } = new();
    }
}
