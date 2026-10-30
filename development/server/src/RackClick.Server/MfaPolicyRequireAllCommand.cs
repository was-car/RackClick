using System.Runtime.Versioning;
using System.Security.Principal;
using System.Text.Json;
using Npgsql;
using RackClick.Domain;

namespace RackClick.Server;

// Explicit local provisioning command; never an HTTP authority or a password-only escape route.
internal static class MfaPolicyRequireAllCommand
{
    public static Task<int> Run(IConfiguration configuration, TextReader input, TextWriter output, CancellationToken ct)
    {
        if (!OperatingSystem.IsWindows()) return Task.FromResult(Reject(output, "mfa_policy_not_windows"));
        return Run(configuration, input, output, MfaKeyStoreInitCommand.IsElevatedAdministrator(),
            ValidateStore, MfaPolicyAdministration.RequireAll, ct);
    }

    // Test-only seam: the production entry always uses native elevation, fixed trust and the real DB-owner operation.
    internal static async Task<int> Run(IConfiguration configuration, TextReader input, TextWriter output, bool elevated,
        Func<IConfiguration, string, IMfaKeyProvider> validateStore,
        Func<string, Guid, Guid, IMfaKeyProvider, CancellationToken, Task<MfaPolicyActivationResult>> activate, CancellationToken ct)
    {
        if (!elevated) return Reject(output, "mfa_policy_not_elevated");
        try
        {
            if (!Guid.TryParseExact(configuration["MfaPolicy:DatabaseInstanceId"], "D", out var databaseId)
                || databaseId == Guid.Empty
                || !Guid.TryParseExact(configuration["MfaPolicy:ActorId"], "D", out var actorId) || actorId == Guid.Empty
                || !Guid.TryParseExact(configuration["MfaKeyStore:InstallationId"], "D", out var installationId)
                || installationId == Guid.Empty
                || MfaWindowsHostComposition.ModeOf(configuration) != MfaHostMode.Enabled)
                return Reject(output, "mfa_policy_config_invalid");
            var readerSid = configuration["MfaPolicy:ReaderSid"];
            var connection = configuration.GetConnectionString("RackClick");
            if (string.IsNullOrEmpty(readerSid) || readerSid.Length > 184 || string.IsNullOrWhiteSpace(connection))
                return Reject(output, "mfa_policy_config_invalid");

            // Bounded exact confirmation; no unbounded ReadToEnd, no writes/connection before it matches.
            var confirmation = "REQUIRE MFA " + databaseId.ToString("D");
            for (int i = 0; i < confirmation.Length; i++)
                if (input.Read() != confirmation[i]) return Reject(output, "mfa_policy_confirmation_invalid");
            if (input.Read() != -1) return Reject(output, "mfa_policy_confirmation_invalid");

            var provider = validateStore(configuration, readerSid);
            var result = await activate(connection, databaseId, actorId, provider, ct);
            output.WriteLine(JsonSerializer.Serialize(new
            {
                status = "committed", code = result.Noop ? "mfa_policy_unchanged" : "mfa_policy_required",
                changedUsers = result.ChangedUsers, revokedSessions = result.RevokedSessions,
                revokedChallenges = result.RevokedChallenges, noop = result.Noop,
                scope = "existing_users", futureUserProvisioningCovered = false,
            }));
            return 0;
        }
        catch (MfaHostCompositionException error) { return Reject(output, error.Code); }
        catch (DomainError error) { return Reject(output, error.Code); }
        catch (NpgsqlException) { return Reject(output, "mfa_policy_database_failed"); }
        catch (ArgumentException) { return Reject(output, "mfa_policy_config_invalid"); }
        catch (IOException) { return Reject(output, "mfa_policy_input_unreadable"); }
    }

    [SupportedOSPlatform("windows")]
    private static IMfaKeyProvider ValidateStore(IConfiguration configuration, string readerSid)
    {
        var identity = new ProvisionedReader(new SecurityIdentifier(readerSid));
        return MfaWindowsHostComposition.Compose(MfaHostMode.Enabled, configuration, identity).Provider;
    }

    [SupportedOSPlatform("windows")]
    private sealed class ProvisionedReader(SecurityIdentifier reader) : IMfaHostIdentity
    {
        public SecurityIdentifier? ReaderSid => reader;
        public IReadOnlyCollection<SecurityIdentifier> TrustedPrincipals { get; } =
            [new(WellKnownSidType.LocalSystemSid, null), new(WellKnownSidType.BuiltinAdministratorsSid, null)];
        public string Description => "fixed-production-trust-provisioning-preflight";
    }

    private static int Reject(TextWriter output, string code)
    {
        output.WriteLine(JsonSerializer.Serialize(new { status = "rejected", code }));
        return 1;
    }
}
