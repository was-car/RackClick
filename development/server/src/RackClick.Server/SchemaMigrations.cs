using Npgsql;
using RackClick.Domain;

namespace RackClick.Server;

public static class SchemaMigrations
{
    public const int LatestVersion = 48;
    private static readonly string[] Files = ["001-foundation.sql", "002-inventory.sql", "003-operation-cancellation.sql", "004-session-identity.sql", "005-audit-context.sql", "006-audit-state-intent.sql", "007-audit-context-families.sql", "008-user-catalog-favorites.sql", "009-private-device-templates.sql", "010-customer-shared-device-templates.sql", "011-user-preferences.sql", "012-user-port-colors.sql", "013-user-category-colors.sql", "014-mfa.sql", "015-mfa-account-policy.sql", "016-hardware-mounting.sql", "017-hardware-catalog.sql", "018-commercial-hardware.sql", "019-aruba-hardware.sql", "020-fortinet-hardware.sql", "021-synology-hardware.sql", "022-diskstation-hardware.sql", "023-qnap-hardware.sql", "024-batch50-hardware.sql", "025-batch50b-hardware.sql", "026-batch100-hardware.sql", "027-batch100b-hardware.sql", "028-batch100c-hardware.sql", "029-selected506a-hardware.sql", "030-selected506b-hardware.sql", "031-selected506c-hardware.sql", "032-selected506d-hardware.sql", "033-selected506e-hardware.sql", "034-selected506f-hardware.sql", "035-selected506g-hardware.sql", "036-physical-media.sql", "037-selected506h-hardware.sql", "038-selected506i-hardware.sql", "039-selected506j-hardware.sql", "040-hardware-families.sql", "041-selected506k-hardware.sql", "042-hardware-family-l.sql", "043-selected506l-hardware.sql", "044-german-cpe-hardware.sql", "045-german-repeaters-hardware.sql", "046-mfa-key-rotation.sql", "047-mfa-loss-reset.sql", "048-mfa-loss-startup.sql"];

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
