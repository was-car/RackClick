using System.Runtime.Versioning;
using System.Security.Principal;

namespace RackClick.Server;

// Explicit opt-in only; never falls back to plaintext after opting in. No writes,
// file creation, repair or database access. CLI ownership stays separate from runtime.
internal static class SqlSecretConnection
{
    internal static bool Enabled(IConfiguration configuration)
    {
        var raw = configuration["SqlSecret:Enabled"];
        if (raw is null || string.Equals(raw, "false", StringComparison.OrdinalIgnoreCase)) return false;
        if (string.Equals(raw, "true", StringComparison.OrdinalIgnoreCase)) return true;
        throw Fail("sql_secret_config_invalid");
    }

    internal static void RequireSeparateMaintenanceIdentity(IConfiguration configuration)
    {
        if (Enabled(configuration)) throw Fail("sql_secret_runtime_only");
    }

    internal static string Resolve(IConfiguration configuration)
    {
        if (!Enabled(configuration)) return configuration.GetConnectionString("RackClick")
            ?? throw new InvalidOperationException("ConnectionStrings:RackClick is required; no database is created automatically.");
        if (!OperatingSystem.IsWindows()) throw Fail("sql_secret_not_windows");
        using var impersonated = WindowsIdentity.GetCurrent(ifImpersonating: true);
        if (impersonated is not null) throw Fail("sql_secret_identity_invalid");
        using var identity = WindowsIdentity.GetCurrent();
        var reader = identity.User ?? throw Fail("sql_secret_identity_invalid");
        SecurityIdentifier[] trusted = [new(WellKnownSidType.LocalSystemSid, null), new(WellKnownSidType.BuiltinAdministratorsSid, null)];
        return Read(configuration, reader, trusted);
    }

    // Internal seam only; production always derives the SID and fixed trust above.
    [SupportedOSPlatform("windows")]
    internal static string Read(IConfiguration configuration, SecurityIdentifier reader, IReadOnlyCollection<SecurityIdentifier> trusted)
    {
        if (!string.IsNullOrEmpty(configuration.GetConnectionString("RackClick"))) throw Fail("sql_secret_plaintext_conflict");
        if (trusted.Count == 0 || trusted.Contains(reader)) throw Fail("sql_secret_identity_invalid");
        var root = configuration["SqlSecret:InstancesRoot"];
        var database = configuration["SqlSecret:Database"] ?? "";
        var runtime = configuration["SqlSecret:RuntimeUser"] ?? "";
        if (string.IsNullOrEmpty(root) || !Path.IsPathFullyQualified(root) ||
            !Guid.TryParseExact(configuration["SqlSecret:InstallationId"], "D", out var id) || id == Guid.Empty ||
            !WindowsSqlSecret.Identifier(database) || !WindowsSqlSecret.Identifier(runtime))
            throw Fail("sql_secret_config_invalid");
        try
        {
            root = Path.GetFullPath(root);
            var installation = Path.Combine(root, id.ToString("D"));
            var folder = Path.Combine(installation, "sql-secrets");
            var fileReader = new WindowsMfaKeyFileReader(reader, trusted.Select(sid => sid.Value).ToHashSet(StringComparer.Ordinal));
            fileReader.RequireSafeFolder(root);
            fileReader.RequireSafeFolder(installation);
            fileReader.RequireSafeFolder(folder);
            var bytes = fileReader.ReadValidated(Path.Combine(folder, "runtime.bin"), WindowsSqlSecret.MaximumFileBytes);
            return WindowsSqlSecret.Open(bytes, id, reader, database, runtime);
        }
        catch (MfaKeyRingException ex)
        {
            throw Fail(ex.Kind switch
            {
                MfaKeyRingErrorKind.MissingFile => "sql_secret_missing",
                MfaKeyRingErrorKind.UnsafeAccess or MfaKeyRingErrorKind.UnsafePath => "sql_secret_access_unsafe",
                _ => "sql_secret_invalid",
            });
        }
        catch (Exception ex) when (ex is ArgumentException or NotSupportedException) { throw Fail("sql_secret_config_invalid"); }
        catch (Exception ex) when (ex is IOException or UnauthorizedAccessException) { throw Fail("sql_secret_unreadable"); }
    }

    private static SqlSecretException Fail(string code) => new(code);
}
