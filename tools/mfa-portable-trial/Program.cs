using System.Diagnostics;
using System.Globalization;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Security.AccessControl;
using System.Security.Cryptography;
using System.Security.Principal;
using System.Text;
using System.Text.Json;
using Microsoft.Win32.SafeHandles;
using RackClick.MfaServiceReadProbe;
using RackClick.Server;

namespace RackClick.MfaPortableTrial;

// Offline test coordinator, not a production maintenance operator. No DB/listener/configuration/service mutations.
// All source secrets are synthetic. Target trust is always SYSTEM/Administrators; the target service token only reads.
internal static class Program
{
    private const string ProtectedD = "bbd2b6c2-abaf-4964-8c12-cf8f0c4af2aa";
    private const string SourceHost = "LEAO";
    private static readonly SecurityIdentifier SystemSid = new(WellKnownSidType.LocalSystemSid, null);
    private static readonly SecurityIdentifier AdminSid = new(WellKnownSidType.BuiltinAdministratorsSid, null);
    private static readonly SecurityIdentifier UsersSid = new(WellKnownSidType.BuiltinUsersSid, null);
    private static readonly JsonSerializerOptions Json = new() { PropertyNamingPolicy = JsonNamingPolicy.CamelCase };
    private static readonly HashSet<string> Verbs = new(StringComparer.Ordinal) { "source", "recover", "verify" };
    private static string? inspectedTarget;

    private static int Main(string[] args)
    {
        var verb = args.Length == 1 && Verbs.Contains(args[0]) ? args[0] : "unknown";
        try
        {
            Need(verb != "unknown", "usage");
            Need(OperatingSystem.IsWindows(), "not_windows");
            PinServer();
            Need(Console.IsInputRedirected, "stdin_required");
            using var document = JsonDocument.Parse(ReadBounded(Console.In), new JsonDocumentOptions { MaxDepth = 6 });
            var request = document.RootElement;
            var result = verb switch
            {
                "source" => Source(request),
                "recover" => Recover(request),
                "verify" => Verify(request),
                _ => throw new ProbeException("usage"),
            };
            Emit(verb, "passed", "", result);
            return 0;
        }
        catch (Exception caught)
        {
            var error = caught is TargetInvocationException { InnerException: not null } reflection ? reflection.InnerException! : caught;
            string code = error is ProbeException p ? p.Code : error switch
            {
                JsonException or InvalidOperationException or FormatException or ArgumentException => "input_invalid",
                MfaKeyStoreCreationException => "store_creation_rejected",
                MfaRecoveryEnvelopeException => "envelope_rejected",
                MfaKeyRecoveryPayloadException => "payload_rejected",
                WindowsMfaKeyRecoveryFileException => "portable_file_rejected",
                WindowsMfaKeyRecoveryException => "portable_material_rejected",
                MfaKeyRingException => "store_rejected",
                UnauthorizedAccessException => "access_denied",
                IOException => "io_failed",
                _ => "unexpected_error",
            };
            var category = error switch
            {
                MfaKeyStoreCreationException e => e.Kind.ToString(),
                MfaRecoveryEnvelopeException e => e.Kind.ToString(),
                MfaKeyRecoveryPayloadException e => e.Kind.ToString(),
                WindowsMfaKeyRecoveryFileException e => e.Kind.ToString(),
                WindowsMfaKeyRecoveryException e => e.Kind.ToString(),
                MfaKeyRingException e => e.Kind.ToString(),
                _ => "none",
            };
            string destinationNamespace;
            try { destinationNamespace = inspectedTarget is null ? "not_observed" : Directory.Exists(Path.Combine(inspectedTarget, "instances")) ? "present_preserved_offline" : "absent"; }
            catch { destinationNamespace = "unknown"; }
            Emit(verb, "failed", code, new { errorType = error.GetType().Name, errorHResult = error.HResult, errorCategory = category, destinationNamespace });
            return 1;
        }
    }

    private static object Source(JsonElement request)
    {
        Keys(request, "schemaVersion", "operationId", "expectedHost", "baseDirectory", "installationId", "password");
        Common(request);
        Need(Environment.MachineName.Equals(SourceHost, StringComparison.OrdinalIgnoreCase), "source_host_excluded");
        var origin = Id(request, "installationId");
        var root = Absolute(Text(request, "baseDirectory"));
        var parent = Path.GetDirectoryName(root)!;
        Need(parent.Equals(@"C:\RackClick_SVR\.local", StringComparison.OrdinalIgnoreCase) && Path.GetFileName(root).StartsWith("f0504-", StringComparison.Ordinal), "source_root_invalid");
        Need(!Exists(root), "source_exists");
        NoReparse(parent);
        var password = Password(request);
        var me = WindowsIdentity.GetCurrent().User ?? throw new ProbeException("identity_missing");
        SecurityIdentifier[] trusted = [me, SystemSid, AdminSid];
        NewPrivateDirectory(root, me, trusted);
        var envelopes = Path.Combine(root, "envelopes");
        var data = Path.Combine(root, "datos");
        NewPrivateDirectory(envelopes, me, trusted, UsersSid);
        NewPrivateDirectory(data, me, trusted);
        var store = Path.Combine(root, "source-store");
        var systemhaus = Guid.NewGuid();
        var keyMaterials = new List<(int Version, byte[] Key)>();
        var factors = new List<Factor>();
        try
        {
            foreach (var version in new[] { 1, 7 })
            {
                var key = RandomNumberGenerator.GetBytes(32);
                keyMaterials.Add((version, key));
                var secret = RandomNumberGenerator.GetBytes(20);
                try
                {
                    var user = Guid.NewGuid();
                    factors.Add(new Factor(version, version == 7 ? "active" : "retired", user,
                        Convert.ToBase64String(MfaSecretCipher.Seal(key, version, secret, systemhaus, user)),
                        Convert.ToHexString(SHA256.HashData(secret)).ToLowerInvariant()));
                }
                finally { CryptographicOperations.ZeroMemory(secret); }
            }
            var ring = JsonSerializer.SerializeToUtf8Bytes(new { format = MfaKeyRing.RingFormat, formatVersion = 1, installationId = origin,
                versions = new[] { new { version = 1, state = "retired", createdAtUtc = "2026-10-01T00:00:00Z" }, new { version = 7, state = "active", createdAtUtc = "2026-11-01T00:00:00Z" } } });
            // The isolated executable has the explicitly authorized friend-test assembly identity.
            WindowsMfaKeyStoreWriter.CreateStoreFromMaterial(store, origin, UsersSid, trusted, ring, keyMaterials);
            var fixture = new Fixture(1, Id(request, "operationId"), origin, SourceHost, systemhaus, factors.ToArray());
            NewPrivateFile(Path.Combine(data, "factors.json"), JsonSerializer.SerializeToUtf8Bytes(fixture, Json), me, trusted);
            var receipt = WindowsMfaKeyRecoveryFiles.ExportToFile(store, origin, UsersSid, UsersSid, trusted, password, envelopes, "export.rckey");
            Need(receipt.Length > 59, "export_empty");
            var incompleteRing = JsonSerializer.SerializeToUtf8Bytes(new { format = MfaKeyRing.RingFormat, formatVersion = 1, installationId = origin,
                versions = new[] { new { version = 7, state = "active", createdAtUtc = "2026-11-01T00:00:00Z" } } });
            var incompleteStore = Path.Combine(root, "source-incomplete-store");
            WindowsMfaKeyStoreWriter.CreateStoreFromMaterial(incompleteStore, origin, UsersSid, trusted, incompleteRing, keyMaterials.Where(k => k.Version == 7).ToArray());
            WindowsMfaKeyRecoveryFiles.ExportToFile(incompleteStore, origin, UsersSid, UsersSid, trusted, password, envelopes, "missing-retired.rckey");
            return new { sourceCreated = true, sourceTrust = "laboratory_owner_explicit", versions = new[] { 1, 7 }, factorCount = factors.Count,
                envelopeExported = true, incompleteEnvelopeExported = true, plaintextKeysWritten = false, passwordWrittenByTool = false };
        }
        finally { foreach (var material in keyMaterials) CryptographicOperations.ZeroMemory(material.Key); }
    }

    private static object Recover(JsonElement request)
    {
        Keys(request, "schemaVersion", "operationId", "expectedHost", "baseDirectory", "originInstallationId", "installationId",
            "serviceName", "expectedServiceSid", "custodianSid", "password", "envelopeSha256", "factorsSha256", "adaptDestinationInstallation");
        var target = Target(request);
        Need(request.GetProperty("adaptDestinationInstallation").ValueKind is JsonValueKind.True or JsonValueKind.False, "adaptation_invalid");
        var adapt = request.GetProperty("adaptDestinationInstallation").GetBoolean();
        var origin = Id(request, "originInstallationId");
        var destination = Id(request, "installationId");
        Need(!Exists(Path.Combine(target, "instances")), "destination_exists");
        var fixture = LoadFixture(request, target);
        Need(fixture.OriginInstallationId == origin, "fixture_origin_mismatch");
        Need(origin != destination || !adapt, "adaptation_not_needed");
        Need(origin == destination || adapt, "adaptation_required");
        var custodian = new SecurityIdentifier(Text(request, "custodianSid"));
        Need(!Sids.IsFixedTrust(custodian), "custodian_invalid");
        var envelope = Path.Combine(target, "envelope-in", "export.rckey");
        Need(FileHash(envelope) == Hash(request, "envelopeSha256"), "envelope_hash_mismatch");
        using var linked = Link(request, withExpectedProcess: false);
        Need(!custodian.Equals(linked.Facts.AccountSid), "custodian_is_service");
        // Authenticate and prove complete factor-version coverage before the approved writer can be reached.
        var reader = new WindowsMfaKeyFileReader(custodian, new HashSet<string>([SystemSid.Value, AdminSid.Value], StringComparer.Ordinal));
        var sealedBytes = reader.ReadValidated(envelope, MfaKeyRecoveryEnvelope.MaxEnvelopeBytes);
        var plain = MfaKeyRecoveryEnvelope.Open(Password(request), sealedBytes);
        try
        {
            using var content = MfaKeyRecoveryPayload.Deserialize(plain, origin);
            Need(content.Ring.Entries.Any(e => e.Version == 1 && e.State == MfaKeyState.Retired) &&
                content.Ring.Entries.Any(e => e.Version == 7 && e.State == MfaKeyState.Active), "material_required_version_missing");
            ValidateFactors(v => content.KeyFor(v).ToArray(), fixture);
        }
        finally { CryptographicOperations.ZeroMemory(plain); }
        WindowsMfaKeyRecoveryFiles.RecoverFromFile(envelope, Password(request), origin, Path.Combine(target, "instances"), destination,
            linked.Facts.AccountSid, custodian, [SystemSid, AdminSid], adapt);
        var recovered = new WindowsMfaKeyProvider(Path.Combine(target, "instances"), destination, linked.Facts.AccountSid, [SystemSid, AdminSid]);
        ValidateFactors(recovered.GetKey, fixture);
        linked.Revalidate();
        return new { storeRecovered = true, explicitAdaptation = adapt, targetTrust = "fixed_system_administrators", factorCount = fixture.Factors.Length,
            processLinked = true, tokenMatched = true, standardAccount = true, existingServiceStoreChanged = false };
    }

    private static object Verify(JsonElement request)
    {
        Keys(request, "schemaVersion", "operationId", "expectedHost", "baseDirectory", "originInstallationId", "installationId",
            "serviceName", "expectedServiceSid", "expectedProcessId", "expectedProcessStartUtc", "factorsSha256");
        var target = Target(request);
        var destination = Id(request, "installationId");
        var fixture = LoadFixture(request, target);
        Need(fixture.OriginInstallationId == Id(request, "originInstallationId"), "fixture_origin_mismatch");
        var root = Path.Combine(target, "instances");
        var folder = Path.Combine(root, destination.ToString("D"));
        var keys = Path.Combine(folder, WindowsMfaKeyProvider.KeysFolderName);
        var before = Snapshot(root);
        var beforeIdentity = WindowsIdentity.GetCurrent().User ?? throw new ProbeException("identity_missing");
        using var linked = Link(request, withExpectedProcess: true);
        var checkedFactors = 0;
        var aadDenied = 0;
        WriteCounts? counts = null;
        var impersonated = false;
        var missingVersionDenied = false;
        WindowsIdentity.RunImpersonated(linked.Impersonation, () =>
        {
            impersonated = WindowsIdentity.GetCurrent(true)?.User?.Equals(linked.Facts.AccountSid) == true;
            Need(impersonated, "impersonation_not_effective");
            var provider = new WindowsMfaKeyProvider(root, destination, linked.Facts.AccountSid, [SystemSid, AdminSid]);
            var active = provider.GetActiveKey();
            try { Need(active.Version == 7 && active.Key.Length == 32, "active_version_mismatch"); }
            finally { CryptographicOperations.ZeroMemory(active.Key); }
            foreach (var factor in fixture.Factors)
            {
                var key = provider.GetKey(factor.Version);
                var ciphertext = Convert.FromBase64String(factor.Ciphertext);
                byte[]? plain = null;
                try
                {
                    plain = MfaSecretCipher.Open(key, factor.Version, ciphertext, fixture.SystemhausId, factor.UserId);
                    Need(CryptographicOperations.FixedTimeEquals(SHA256.HashData(plain), Convert.FromHexString(factor.SecretSha256)), "factor_plaintext_mismatch");
                    checkedFactors++;
                    aadDenied += RejectAad(key, factor.Version, ciphertext, Guid.NewGuid(), factor.UserId);
                    aadDenied += RejectAad(key, factor.Version, ciphertext, fixture.SystemhausId, Guid.NewGuid());
                    aadDenied += RejectAad(key, factor.Version == 1 ? 7 : 1, ciphertext, fixture.SystemhausId, factor.UserId);
                }
                finally { CryptographicOperations.ZeroMemory(key); if (plain is not null) CryptographicOperations.ZeroMemory(plain); }
            }
            try
            {
                var unexpected = provider.GetKey(8);
                CryptographicOperations.ZeroMemory(unexpected);
                throw new ProbeException("missing_version_accepted");
            }
            catch (MfaKeyRingException ex) when (ex.Kind == MfaKeyRingErrorKind.UnknownVersion) { missingVersionDenied = true; }
            counts = WriteProbe.CheckStore(root, folder, keys, linked.Facts.AccountSid);
        });
        Need(WindowsIdentity.GetCurrent().User?.Equals(beforeIdentity) == true, "identity_not_restored");
        linked.Revalidate();
        Need(before.SequenceEqual(Snapshot(root)), "store_changed");
        Need(checkedFactors == 2 && aadDenied == 6 && missingVersionDenied && counts is not null, "verification_incomplete");
        Need(counts!.WriteGranted == 0 && counts.DacGranted == 0 && counts.Inconclusive == 0 && counts.OwnerIsReader == 0 &&
            counts.WriteDenied == counts.Targets && counts.DacDenied == counts.Targets, "unexpected_write_access");
        return new { processLinked = true, tokenMatched = true, standardAccount = true, impersonationVerified = impersonated,
            identityRestored = true, activeVersion = 7, retiredVersionRead = true, factorsVerified = checkedFactors,
            aadMismatchesRejected = aadDenied, missingVersionDenied, targets = counts.Targets, writeDenied = counts.WriteDenied,
            dacDenied = counts.DacDenied, writeGranted = counts.WriteGranted, dacGranted = counts.DacGranted, inconclusive = counts.Inconclusive,
            storeFingerprintUnchanged = true, noDatabaseOrListener = true };
    }

    private static int RejectAad(byte[] key, int version, byte[] cipher, Guid systemhaus, Guid user)
    {
        try
        {
            var opened = MfaSecretCipher.Open(key, version, cipher, systemhaus, user);
            CryptographicOperations.ZeroMemory(opened);
            throw new ProbeException("wrong_aad_accepted");
        }
        catch (CryptographicException) { return 1; }
    }

    private static void ValidateFactors(Func<int, byte[]> getKey, Fixture fixture)
    {
        foreach (var factor in fixture.Factors)
        {
            var key = getKey(factor.Version);
            byte[]? plain = null;
            try
            {
                plain = MfaSecretCipher.Open(key, factor.Version, Convert.FromBase64String(factor.Ciphertext), fixture.SystemhausId, factor.UserId);
                Need(CryptographicOperations.FixedTimeEquals(SHA256.HashData(plain), Convert.FromHexString(factor.SecretSha256)), "factor_plaintext_mismatch");
            }
            finally { CryptographicOperations.ZeroMemory(key); if (plain is not null) CryptographicOperations.ZeroMemory(plain); }
        }
    }

    private static LinkedToken Link(JsonElement request, bool withExpectedProcess)
    {
        var name = Text(request, "serviceName");
        Need(name.Length is > 0 and < 100 && name.All(c => char.IsAsciiLetterOrDigit(c) || c is '-' or '_'), "service_name_invalid");
        var expected = new SecurityIdentifier(Text(request, "expectedServiceSid"));
        Need(expected.Value.StartsWith("S-1-5-21-", StringComparison.Ordinal) && !expected.Value.EndsWith("-500", StringComparison.Ordinal), "service_sid_invalid");
        var result = new LinkedToken(name, expected);
        try
        {
            if (withExpectedProcess)
            {
                Need(request.GetProperty("expectedProcessId").GetUInt32() == result.Facts.ProcessId, "process_id_mismatch");
                var expectedTime = DateTimeOffset.Parse(Text(request, "expectedProcessStartUtc"), CultureInfo.InvariantCulture, DateTimeStyles.None);
                Need(expectedTime.Offset == TimeSpan.Zero && expectedTime.UtcDateTime.Ticks == result.StartTicks, "process_start_mismatch");
            }
            return result;
        }
        catch { result.Dispose(); throw; }
    }

    private sealed class LinkedToken : IDisposable
    {
        private readonly DebugPrivilege debug = new();
        private IntPtr process, token;
        public ServiceFacts Facts { get; }
        public long StartTicks { get; }
        public SafeAccessTokenHandle Impersonation { get; }
        public LinkedToken(string service, SecurityIdentifier expected)
        {
            try
            {
                Facts = ServiceMeasure.Measure(service);
                Need(Facts.AccountSid.Equals(expected), "service_account_mismatch");
                process = Access.OpenProcess(Facts.ProcessId, Native.PROCESS_QUERY_INFORMATION | Native.PROCESS_QUERY_LIMITED_INFORMATION, debug);
                Need(ImageMatch.Matches(ImageMatch.ProcessImage(process), Facts.BinaryPath), "process_image_mismatch");
                StartTicks = HeldProcessStart(process);
                token = Access.OpenToken(process, debug);
                Impersonation = TokenLink.DuplicateForImpersonation(token);
                Need(TokenLink.SidOf(Impersonation).Equals(expected), "token_sid_mismatch");
                var operatorSid = WindowsIdentity.GetCurrent().User ?? throw new ProbeException("identity_missing");
                var standard = WindowsIdentity.RunImpersonated(Impersonation, () =>
                    WindowsIdentity.GetCurrent(true)?.User?.Equals(expected) == true &&
                    !new WindowsPrincipal(WindowsIdentity.GetCurrent()).IsInRole(WindowsBuiltInRole.Administrator));
                Need(WindowsIdentity.GetCurrent().User?.Equals(operatorSid) == true, "identity_not_restored");
                Need(standard, "service_not_standard");
                Revalidate();
            }
            catch { Dispose(); throw; }
        }
        public void Revalidate()
        {
            var now = ServiceMeasure.Measure(Facts.Name);
            Need(now.ProcessId == Facts.ProcessId && now.AccountSid.Equals(Facts.AccountSid) && now.BinaryPath == Facts.BinaryPath &&
                HeldProcessStart(process) == StartTicks && ObservedProcessStart(Facts.ProcessId) == StartTicks, "service_binding_changed");
        }
        public void Dispose()
        {
            Impersonation?.Dispose();
            if (token != IntPtr.Zero) { Native.CloseHandle(token); token = IntPtr.Zero; }
            if (process != IntPtr.Zero) { Native.CloseHandle(process); process = IntPtr.Zero; }
            var restored = debug.Restore();
            debug.Dispose();
            Need(restored, "debug_privilege_restore_failed");
        }
    }

    private static Fixture LoadFixture(JsonElement request, string root)
    {
        var path = Path.Combine(root, "datos", "factors.json");
        Need(FileHash(path) == Hash(request, "factorsSha256"), "fixture_hash_mismatch");
        var bytes = File.ReadAllBytes(path); Need(bytes.Length is > 0 and < 32768, "fixture_size_invalid");
        using var doc = JsonDocument.Parse(bytes, new JsonDocumentOptions { MaxDepth = 5 });
        var data = doc.RootElement;
        Keys(data, "schemaVersion", "operationId", "originInstallationId", "sourceHost", "systemhausId", "factors");
        Need(data.GetProperty("schemaVersion").GetInt32() == 1 && Id(data, "operationId") == Id(request, "operationId") && Text(data, "sourceHost") == SourceHost, "fixture_invalid");
        var factors = data.GetProperty("factors").EnumerateArray().Select(f =>
        {
            Keys(f, "version", "state", "userId", "ciphertext", "secretSha256");
            var factor = new Factor(f.GetProperty("version").GetInt32(), Text(f, "state"), Id(f, "userId"), Text(f, "ciphertext"), Hash(f, "secretSha256"));
            Need(Convert.FromBase64String(factor.Ciphertext).Length == 48, "factor_size_invalid");
            return factor;
        }).ToArray();
        Need(factors.Length == 2 && factors[0].Version == 1 && factors[0].State == "retired" && factors[1].Version == 7 && factors[1].State == "active" && factors[0].UserId != factors[1].UserId, "fixture_versions_invalid");
        return new Fixture(1, Id(data, "operationId"), Id(data, "originInstallationId"), SourceHost, Id(data, "systemhausId"), factors);
    }

    private static string Target(JsonElement request)
    {
        Common(request);
        Need(!Environment.MachineName.Equals(SourceHost, StringComparison.OrdinalIgnoreCase), "target_host_excluded");
        using var identity = WindowsIdentity.GetCurrent();
        Need(IsElevated(identity), "target_not_elevated");
        var path = Absolute(Text(request, "baseDirectory"));
        var required = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.CommonApplicationData), "RackClick-F0504-" + Id(request, "operationId").ToString("D"));
        Need(path.Equals(required, StringComparison.OrdinalIgnoreCase) && Directory.Exists(path), "target_root_invalid");
        NoReparse(path);
        inspectedTarget = path;
        return path;
    }

    private static void Common(JsonElement request)
    {
        Need(request.GetProperty("schemaVersion").GetInt32() == 1, "input_version_invalid");
        _ = Id(request, "operationId");
        Need(Text(request, "expectedHost").Equals(Environment.MachineName, StringComparison.OrdinalIgnoreCase), "host_mismatch");
    }
    private static void Keys(JsonElement value, params string[] names)
    {
        Need(value.ValueKind == JsonValueKind.Object, "input_invalid");
        var found = value.EnumerateObject().Select(p => p.Name).ToArray();
        Need(found.Length == names.Length && found.Distinct(StringComparer.Ordinal).Count() == names.Length && !found.Except(names, StringComparer.Ordinal).Any(), "input_invalid");
    }
    private static string Text(JsonElement value, string name)
    {
        var text = value.GetProperty(name).GetString();
        Need(!string.IsNullOrEmpty(text) && !text.Any(char.IsControl), "input_invalid"); return text!;
    }
    private static Guid Id(JsonElement value, string name)
    {
        var text = Text(value, name); Need(Guid.TryParseExact(text, "D", out var id) && id != Guid.Empty && text == id.ToString("D") && text != ProtectedD, "identity_invalid"); return id;
    }
    private static string Hash(JsonElement value, string name)
    {
        var text = Text(value, name); Need(text.Length == 64 && text.All(c => c is >= '0' and <= '9' or >= 'a' and <= 'f'), "hash_invalid"); return text;
    }
    private static string Password(JsonElement value)
    {
        var password = Text(value, "password");
        Need(password.Length is >= 12 and <= 512 && password.EnumerateRunes().Count() is >= 12 and <= 256, "password_size_invalid");
        _ = new UTF8Encoding(false, true).GetByteCount(password);
        return password;
    }
    private static string Absolute(string value)
    {
        Need(Path.IsPathFullyQualified(value) && !value.Contains('/') && !value[2..].Contains(':') && !value.Split('\\').Any(p => p is "." or ".."), "path_invalid"); return Path.GetFullPath(value).TrimEnd('\\');
    }
    private static void NoReparse(string path)
    {
        for (var d = new DirectoryInfo(path); d is not null; d = d.Parent)
            Need(!d.Exists || (d.Attributes & FileAttributes.ReparsePoint) == 0, "reparse_rejected");
    }
    private static bool Exists(string path) => File.Exists(path) || Directory.Exists(path);
    private static string FileHash(string path) { using var stream = File.OpenRead(path); return Convert.ToHexString(SHA256.HashData(stream)).ToLowerInvariant(); }
    private static string[] Snapshot(string root) => Directory.EnumerateFileSystemEntries(root, "*", SearchOption.AllDirectories).Prepend(root).Order(StringComparer.Ordinal).Select(path =>
    {
        FileSystemSecurity security = Directory.Exists(path) ? new DirectoryInfo(path).GetAccessControl() : new FileInfo(path).GetAccessControl();
        return path + "|" + security.GetSecurityDescriptorSddlForm(AccessControlSections.Owner | AccessControlSections.Access) + "|" + (File.Exists(path) ? FileHash(path) : "directory");
    }).ToArray();
    private static string ReadBounded(TextReader input)
    {
        var chars = new char[16385]; var length = 0;
        while (length < chars.Length) { var count = input.Read(chars, length, chars.Length - length); if (count == 0) break; length += count; }
        Need(length is > 0 and <= 16384, "input_too_large"); return new string(chars, 0, length);
    }
    private static void PinServer()
    {
        var expected = Assembly.GetExecutingAssembly().GetCustomAttributes<AssemblyMetadataAttribute>().Single(a => a.Key == "RackClickServerSha256").Value;
        Need(expected is not null && FileHash(typeof(WindowsMfaKeyProvider).Assembly.Location) == expected, "server_pin_mismatch");
    }
    private static void Need(bool value, string code) { if (!value) throw new ProbeException(code); }
    private static void Emit(string verb, string status, string code, object result) => Console.WriteLine(JsonSerializer.Serialize(new { schemaVersion = 1, verb, status, code, offlineOnly = true, notMfaActivation = true, productAdopted = false, result }, Json));
    private sealed record Factor(int Version, string State, Guid UserId, string Ciphertext, string SecretSha256);
    private sealed record Fixture(int SchemaVersion, Guid OperationId, Guid OriginInstallationId, string SourceHost, Guid SystemhausId, Factor[] Factors);

    private static long HeldProcessStart(IntPtr process)
    {
        Need(GetProcessTimes(process, out var created, out _, out _, out _), "process_start_unavailable");
        return DateTime.FromFileTimeUtc(((long)created.High << 32) | created.Low).Ticks;
    }
    private static long ObservedProcessStart(uint processId)
    {
        using var process = Process.GetProcessById((int)processId);
        return process.StartTime.ToUniversalTime().Ticks;
    }
    private static bool IsElevated(WindowsIdentity identity)
    {
        if (identity.User?.Equals(SystemSid) == true) return true;
        if (!new WindowsPrincipal(identity).IsInRole(WindowsBuiltInRole.Administrator)) return false;
        var buffer = Marshal.AllocHGlobal(4);
        try { return Native.GetTokenInformation(identity.AccessToken.DangerousGetHandle(), 20, buffer, 4, out _) && Marshal.ReadInt32(buffer) != 0; }
        finally { Marshal.FreeHGlobal(buffer); }
    }

    // Laboratory fixture directory/file creation: explicit descriptor at exclusive native creation, no adoption/overwrite.
    private static void NewPrivateDirectory(string path, SecurityIdentifier owner, SecurityIdentifier[] trusted, SecurityIdentifier? reader = null)
    {
        var security = new DirectorySecurity(); security.SetOwner(owner); security.SetAccessRuleProtection(true, false);
        foreach (var sid in trusted.Distinct()) security.AddAccessRule(new FileSystemAccessRule(sid, FileSystemRights.FullControl, InheritanceFlags.ContainerInherit | InheritanceFlags.ObjectInherit, PropagationFlags.None, AccessControlType.Allow));
        if (reader is not null) security.AddAccessRule(new FileSystemAccessRule(reader, FileSystemRights.ReadAndExecute, InheritanceFlags.ContainerInherit | InheritanceFlags.ObjectInherit, PropagationFlags.None, AccessControlType.Allow));
        var bytes = security.GetSecurityDescriptorBinaryForm(); var pin = GCHandle.Alloc(bytes, GCHandleType.Pinned);
        try
        {
            var attrs = new SecurityAttributes { Length = (uint)Marshal.SizeOf<SecurityAttributes>(), Descriptor = pin.AddrOfPinnedObject(), Inherit = false };
            Need(CreateDirectoryW(path, ref attrs), Marshal.GetLastWin32Error() == 183 ? "fixture_exists" : "fixture_directory_failed");
        }
        finally { pin.Free(); }
    }
    private static void NewPrivateFile(string path, byte[] data, SecurityIdentifier owner, SecurityIdentifier[] trusted)
    {
        var security = new FileSecurity(); security.SetOwner(owner); security.SetAccessRuleProtection(true, false);
        foreach (var sid in trusted.Distinct()) security.AddAccessRule(new FileSystemAccessRule(sid, FileSystemRights.FullControl, AccessControlType.Allow));
        using var stream = new FileInfo(path).Create(FileMode.CreateNew, FileSystemRights.Write, FileShare.Read, 4096, FileOptions.None, security);
        stream.Write(data); stream.Flush(true);
    }
    [StructLayout(LayoutKind.Sequential)] private struct SecurityAttributes { public uint Length; public IntPtr Descriptor; [MarshalAs(UnmanagedType.Bool)] public bool Inherit; }
    [StructLayout(LayoutKind.Sequential)] private struct FileTime { public uint Low; public uint High; }
    [DllImport("kernel32.dll", SetLastError = true)] [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool GetProcessTimes(IntPtr process, out FileTime creation, out FileTime exit, out FileTime kernel, out FileTime user);
    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)] [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool CreateDirectoryW(string path, ref SecurityAttributes securityAttributes);
}
