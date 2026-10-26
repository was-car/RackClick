using Npgsql;
using RackClick.Domain;

namespace RackClick.Server;

public static class SchemaMigrations
{
    public const int LatestVersion = 14;
    private static readonly string[] Files = ["001-foundation.sql", "002-inventory.sql", "003-operation-cancellation.sql", "004-session-identity.sql", "005-audit-context.sql", "006-audit-state-intent.sql", "007-audit-context-families.sql", "008-user-catalog-favorites.sql", "009-private-device-templates.sql", "010-customer-shared-device-templates.sql", "011-user-preferences.sql", "012-user-port-colors.sql", "013-user-category-colors.sql", "014-mfa.sql"];

    public static async Task Apply(NpgsqlConnection db, NpgsqlTransaction tx, CancellationToken ct)
    {
        await using var exists = new NpgsqlCommand("SELECT to_regclass('public.schema_migration') IS NOT NULL", db, tx);
        bool initialized = (bool)(await exists.ExecuteScalarAsync(ct))!;
        var applied = new Dictionary<int, string>();
        if (initialized)
        {
            await using var history = new NpgsqlCommand("SELECT version,digest FROM schema_migration ORDER BY version", db, tx);
            await using var rows = await history.ExecuteReaderAsync(ct);
            while (await rows.ReadAsync(ct)) applied.Add(rows.GetInt32(0), rows.GetString(1));
            if (applied.Keys.Any(v => v < 1 || v > LatestVersion)) throw new DomainError(409, "schema_version_unsupported");
        }
        for (int index = 0; index < Files.Length; index++)
        {
            string sql = await File.ReadAllTextAsync(Path.Combine(AppContext.BaseDirectory, "database", Files[index]), ct);
            string digest = Secrets.Digest(sql);
            if (applied.TryGetValue(index + 1, out string? existing))
            {
                if (!string.Equals(existing, digest, StringComparison.OrdinalIgnoreCase)) throw new DomainError(409, "migration_digest_mismatch");
                continue;
            }
            if (applied.Keys.Any(v => v > index + 1)) throw new DomainError(409, "migration_history_invalid");
            await using (var migrate = new NpgsqlCommand(sql, db, tx)) await migrate.ExecuteNonQueryAsync(ct);
            await using var record = new NpgsqlCommand("INSERT INTO schema_migration(version,digest) VALUES(@version,@digest)", db, tx);
            record.Parameters.AddWithValue("version", index + 1);
            record.Parameters.AddWithValue("digest", digest);
            await record.ExecuteNonQueryAsync(ct);
        }
    }
}
