using System.Data;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Npgsql;

namespace RackClick.Server;

// Local stdin/stdout protocol only. No host, files, environment identity, key store or writer.
// The exported snapshot binds census/dump, never future writes or key retirement.
internal static class MfaBackupInventoryCommand
{
    private const int InitialLimit = 2 * 1024 * 1024;
    private const int FinalLimit = 4096;
    private static readonly UTF8Encoding StrictUtf8 = new(false, true);
    private static readonly string[] SnapshotFields = ["operation", "installationId", "connectionString", "envelopeBase64", "envelopePassword"];
    private static readonly string[] VerifyFields = ["operation", "installationId", "inventoryBase64", "inventorySha256", "manifestSha256", "dumpSha256", "envelopeSha256"];
    private static readonly string[] FinalFields = ["backupId", "manifestSha256", "dumpSha256"];

    public static async Task<int> RunAsync(TextReader input, TextWriter output, CancellationToken cancellationToken)
    {
        using var timeout = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
        timeout.CancelAfter(TimeSpan.FromSeconds(180));
        var token = timeout.Token;
        try
        {
            token.ThrowIfCancellationRequested();
            using var request = Parse(await ReadLine(input, InitialLimit, token));
            var root = request.RootElement;
            var operation = String(root, "operation");
            if (operation == "verify")
            {
                Exact(root, VerifyFields);
                var inventory = MfaKeyRetention.ParseBackupInventory(
                    Base64(root, "inventoryBase64", MfaKeyRetention.MaxInventoryBytes), Id(root, "installationId"),
                    Hash(root, "inventorySha256"), Hash(root, "manifestSha256"),
                    Hash(root, "dumpSha256"), Hash(root, "envelopeSha256"));
                token.ThrowIfCancellationRequested();
                await Reply(output, new { status = "inventory_verified", backupId = inventory.BackupId.ToString("D"),
                    requiredVersions = inventory.RequiredVersions, envelopeVersions = inventory.EnvelopeVersions }, token);
                return 0;
            }
            if (operation != "snapshot") throw Invalid();
            Exact(root, SnapshotFields);
            var installation = Id(root, "installationId");
            var connectionString = ConnectionString(String(root, "connectionString"), installation);
            var envelope = MfaKeyRetention.InspectEnvelope(Base64(root, "envelopeBase64", MfaKeyRecoveryEnvelope.MaxEnvelopeBytes),
                String(root, "envelopePassword"), installation);
            token.ThrowIfCancellationRequested();
            await using var connection = new NpgsqlConnection(connectionString);
            await connection.OpenAsync(token);
            await using var maintenanceAdmission = await MfaMaintenanceAdmission.SharedAsync(connection, token);
            await using var transaction = await connection.BeginTransactionAsync(IsolationLevel.RepeatableRead, token);
            await using (var readOnly = new NpgsqlCommand("SET TRANSACTION READ ONLY", connection, transaction))
                await readOnly.ExecuteNonQueryAsync(token);
            await ValidateIdentity(connection, transaction, installation, token);
            await ValidateSchemaVersion(connection, transaction, token);
            var factors = await MfaFactorKeyInventoryReader.ReadAsync(connection, transaction, installation, token);
            // Reject a missing dependency before inviting pg_dump to consume the snapshot.
            if (factors.Entries.Any(entry => (entry.Pending != 0 || entry.Active != 0 || entry.Disabled != 0)
                && !envelope.Versions.Contains(entry.Version))) throw Invalid();
            string snapshot;
            await using (var export = new NpgsqlCommand("SELECT pg_catalog.pg_export_snapshot()", connection, transaction))
            {
                snapshot = (string)(await export.ExecuteScalarAsync(token))!;
                if (snapshot.Length is < 1 or > 128 || snapshot.Any(c => c is not (>= '0' and <= '9')
                    and not (>= 'A' and <= 'F') and not (>= 'a' and <= 'f') and not '-')) throw Invalid();
            }
            await Reply(output, new { status = "snapshot_ready", snapshot }, token);
            using var final = Parse(await ReadLine(input, FinalLimit, token));
            Exact(final.RootElement, FinalFields);
            var backup = MfaKeyRetention.CreateBackupInventory(Id(final.RootElement, "backupId"), factors, envelope,
                Hash(final.RootElement, "manifestSha256"), Hash(final.RootElement, "dumpSha256"));
            var bytes = MfaKeyRetention.SerializeBackupInventory(backup);
            // A positive final response is possible only after the read-only transaction commits.
            await transaction.CommitAsync(token);
            token.ThrowIfCancellationRequested();
            await Reply(output, new { status = "inventory_ready", inventoryBase64 = Convert.ToBase64String(bytes),
                inventorySha256 = Convert.ToHexStringLower(SHA256.HashData(bytes)) }, token);
            return 0;
        }
        catch (Rejected error) { return await Reject(output, error.Code); }
        catch (MfaKeyRetentionException error)
        {
            return await Reject(output, error.Message == "mfa_retention_envelope_rejected"
                ? "mfa_backup_envelope_rejected" : "mfa_backup_invalid");
        }
        catch (NpgsqlException) { return await Reject(output, "mfa_backup_database_rejected"); }
        catch (MfaMaintenanceException) { return await Reject(output, "mfa_backup_maintenance_busy"); }
        catch (OperationCanceledException) { return await Reject(output, "mfa_backup_cancelled"); }
        catch (IOException) { return await Reject(output, "mfa_backup_io_failed"); }
    }

    private static async Task ValidateSchemaVersion(NpgsqlConnection connection, NpgsqlTransaction transaction, CancellationToken token)
    {
        // Closed version sequence only. Migration SQL digests remain the deployment preflight's responsibility.
        await using var command = new NpgsqlCommand("SELECT version FROM public.schema_migration ORDER BY version", connection, transaction);
        await using var rows = await command.ExecuteReaderAsync(token);
        for (var version = 1; version <= 45; version++)
            if (!await rows.ReadAsync(token) || rows.GetInt32(0) != version) throw new Rejected("mfa_backup_identity_rejected");
        if (await rows.ReadAsync(token) && (rows.GetInt32(0) != 46 || await rows.ReadAsync(token)))
            throw new Rejected("mfa_backup_identity_rejected");
    }

    private static string ConnectionString(string value, Guid installation)
    {
        NpgsqlConnectionStringBuilder builder;
        try { builder = new NpgsqlConnectionStringBuilder(value); }
        catch (ArgumentException) { throw Invalid(); }
        var id = installation.ToString("N");
        if (builder.Host != "127.0.0.1" || builder.Database != "rc_db_" + id || builder.Username != "rc_backup_" + id
            || string.IsNullOrEmpty(builder.Password) || !string.IsNullOrEmpty(builder.Options)
            || !string.IsNullOrEmpty(builder.SearchPath) || !string.IsNullOrEmpty(builder.Passfile)) throw Invalid();
        // Explicit identity/password plus fixed session settings: no debug/configuration/environment fallback.
        builder.Pooling = false;
        builder.Multiplexing = false;
        builder.PersistSecurityInfo = false;
        builder.IncludeErrorDetail = false;
        builder.LogParameters = false;
        builder.ApplicationName = "RackClick.MfaBackupInventory";
        builder.Options = "-c default_transaction_read_only=on";
        builder.SearchPath = "pg_catalog,public";
        builder.SslMode = SslMode.Disable;
        builder.GssEncryptionMode = GssEncryptionMode.Disable;
        builder.Enlist = false;
        builder.Timeout = 10;
        builder.CommandTimeout = 30;
        return builder.ConnectionString;
    }

    private static async Task ValidateIdentity(NpgsqlConnection connection, NpgsqlTransaction transaction,
        Guid installation, CancellationToken token)
    {
        await using var command = new NpgsqlCommand("""
            SELECT current_database(),current_user,session_user,
                pg_catalog.pg_get_userbyid(d.datdba),pg_catalog.shobj_description(d.oid,'pg_database'),
                pg_catalog.current_setting('server_version_num'),
                r.rolsuper,r.rolcreatedb,r.rolcreaterole,r.rolbypassrls,r.rolreplication,
                pg_catalog.has_table_privilege(current_user,'public.app_mfa_factor','INSERT,UPDATE,DELETE,TRUNCATE'),
                pg_catalog.has_schema_privilege(current_user,'public','CREATE'),
                pg_catalog.has_any_column_privilege(current_user,'public.app_mfa_factor','INSERT,UPDATE'),
                EXISTS (
                    SELECT 1 FROM pg_catalog.pg_class c
                    JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace
                    WHERE n.nspname !~ '^pg_' AND n.nspname<>'information_schema'
                        AND c.relkind IN ('r','p','v','m','f')
                        AND (pg_catalog.has_table_privilege(current_user,c.oid,'INSERT,UPDATE,DELETE,TRUNCATE')
                            OR pg_catalog.has_any_column_privilege(current_user,c.oid,'INSERT,UPDATE'))
                ),
                EXISTS (
                    SELECT 1 FROM pg_catalog.pg_namespace n
                    WHERE n.nspname !~ '^pg_' AND n.nspname<>'information_schema'
                        AND pg_catalog.has_schema_privilege(current_user,n.oid,'CREATE')
                ),
                EXISTS (SELECT 1 FROM pg_catalog.pg_auth_members m WHERE m.member=r.oid),
                pg_catalog.has_database_privilege(current_user,d.oid,'CREATE')
            FROM pg_catalog.pg_database d CROSS JOIN pg_catalog.pg_roles r
            WHERE d.datname=current_database() AND r.rolname=current_user
            """, connection, transaction);
        await using var row = await command.ExecuteReaderAsync(token);
        var id = installation.ToString("N");
        if (!await row.ReadAsync(token) || row.GetString(0) != "rc_db_" + id || row.GetString(1) != "rc_backup_" + id
            || row.GetString(2) != "rc_backup_" + id || row.GetString(3) != "rc_owner_" + id || !row.IsDBNull(4)
            || row.GetString(5) != "170011" || Enumerable.Range(6, 12).Any(row.GetBoolean))
            throw new Rejected("mfa_backup_identity_rejected");
    }

    // Read at most the allowed UTF-16 units before allocating further; then enforce UTF-8 byte quota.
    // A newline terminates one message. EOF before the newline is a truncated protocol, even for valid JSON.
    private static async Task<string> ReadLine(TextReader input, int limit, CancellationToken token)
    {
        var buffer = new char[1];
        var line = new StringBuilder(Math.Min(limit, 4096));
        while (true)
        {
            token.ThrowIfCancellationRequested();
            var read = await input.ReadAsync(buffer.AsMemory(), token).AsTask().WaitAsync(token);
            if (read == 0) throw Invalid();
            if (buffer[0] == '\n') break;
            if (line.Length >= limit) throw Invalid();
            line.Append(buffer[0]);
        }
        if (line.Length > 0 && line[^1] == '\r') line.Length--;
        var text = line.ToString();
        try { if (StrictUtf8.GetByteCount(text) > limit) throw Invalid(); }
        catch (EncoderFallbackException) { throw Invalid(); }
        return text;
    }

    private static JsonDocument Parse(string text)
    {
        try
        {
            var document = JsonDocument.Parse(text, new JsonDocumentOptions
            { MaxDepth = 4, CommentHandling = JsonCommentHandling.Disallow, AllowTrailingCommas = false });
            if (document.RootElement.ValueKind == JsonValueKind.Object) return document;
            document.Dispose();
            throw Invalid();
        }
        catch (JsonException) { throw Invalid(); }
    }

    private static void Exact(JsonElement root, string[] fields)
    {
        var seen = new HashSet<string>(StringComparer.Ordinal);
        foreach (var property in root.EnumerateObject())
        {
            string name;
            try { name = property.Name; }
            catch (InvalidOperationException) { throw Invalid(); }
            if (!fields.Contains(name, StringComparer.Ordinal) || !seen.Add(name)) throw Invalid();
        }
        if (seen.Count != fields.Length) throw Invalid();
    }

    private static string String(JsonElement root, string name)
    {
        if (!root.TryGetProperty(name, out var value) || value.ValueKind != JsonValueKind.String) throw Invalid();
        try { return value.GetString()!; }
        catch (InvalidOperationException) { throw Invalid(); }
    }

    private static Guid Id(JsonElement root, string name) =>
        Guid.TryParseExact(String(root, name), "D", out var id) && id != Guid.Empty ? id : throw Invalid();

    private static string Hash(JsonElement root, string name)
    {
        var value = String(root, name);
        if (value.Length != 64 || value.Any(c => c is not (>= 'a' and <= 'f') and not (>= '0' and <= '9'))) throw Invalid();
        return value;
    }

    private static byte[] Base64(JsonElement root, string name, int limit)
    {
        var value = String(root, name);
        if (value.Length == 0 || value.Length > ((limit + 2) / 3) * 4) throw Invalid();
        try
        {
            var bytes = Convert.FromBase64String(value);
            if (bytes.Length == 0 || bytes.Length > limit) throw Invalid();
            return bytes;
        }
        catch (FormatException) { throw Invalid(); }
    }

    private static async Task Reply(TextWriter output, object message, CancellationToken token)
    {
        await output.WriteLineAsync(JsonSerializer.Serialize(message).AsMemory(), token).WaitAsync(token);
        await output.FlushAsync(token).WaitAsync(token);
    }

    private static async Task<int> Reject(TextWriter output, string code)
    {
        using var diagnosticTimeout = new CancellationTokenSource(TimeSpan.FromSeconds(1));
        try { await Reply(output, new { status = "rejected", code }, diagnosticTimeout.Token); }
        catch (IOException) { /* Broken stdout cannot turn a failed command into success. */ }
        catch (OperationCanceledException) { /* No indefinite wait for an abandoned stdout pipe. */ }
        return 1;
    }

    private static Rejected Invalid() => new("mfa_backup_invalid");
    private sealed class Rejected(string code) : Exception
    {
        internal string Code { get; } = code;
    }
}
