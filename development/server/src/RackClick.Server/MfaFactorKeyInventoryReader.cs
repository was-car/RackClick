using System.Data;
using Npgsql;

namespace RackClick.Server;

// Metadata only. The caller must bind this connection to the installation and
// coordinate it with the dump/ring/retained-backup catalogue under F06.03.
// A read-only SQL snapshot is not a lease against future factor creation.
internal static class MfaFactorKeyInventoryReader
{
    internal static async Task<MfaFactorVersionInventory> ReadAsync(NpgsqlConnection connection,
        NpgsqlTransaction transaction, Guid installationId, CancellationToken cancellationToken)
    {
        cancellationToken.ThrowIfCancellationRequested();
        if (installationId == Guid.Empty)
            throw new MfaKeyRetentionException("mfa_retention_invalid");
        if (connection is null || transaction is null || connection.State != ConnectionState.Open
            || !ReferenceEquals(transaction.Connection, connection))
            throw new InvalidOperationException("mfa_factor_inventory_transaction_required");
        if (transaction.IsolationLevel is not (IsolationLevel.RepeatableRead or IsolationLevel.Serializable))
            throw new InvalidOperationException("mfa_factor_inventory_snapshot_required");

        await using (var mode = new NpgsqlCommand("SHOW transaction_read_only", connection, transaction))
        {
            if (!string.Equals(await mode.ExecuteScalarAsync(cancellationToken) as string, "on", StringComparison.Ordinal))
                throw new InvalidOperationException("mfa_factor_inventory_read_only_required");
        }

        return await ReadCountsAsync(connection,transaction,installationId,cancellationToken);
    }

    // Retirement must count after a blocking lock has been granted, never from a snapshot established before waiting.
    internal static async Task<MfaFactorVersionInventory> ReadForMaintenanceAsync(NpgsqlConnection connection,
        NpgsqlTransaction transaction,Guid installationId,CancellationToken cancellationToken)
    {
        if(installationId==Guid.Empty || connection is null || transaction is null || connection.State!=ConnectionState.Open
            || !ReferenceEquals(transaction.Connection,connection) || transaction.IsolationLevel!=IsolationLevel.ReadCommitted)
            throw new MfaMaintenanceException("mfa_maintenance_census_lock_required");
        await using(var guard=new NpgsqlCommand("""
            SELECT EXISTS(SELECT 1 FROM pg_catalog.pg_locks
                WHERE pid=pg_catalog.pg_backend_pid() AND granted AND mode='AccessExclusiveLock'
                AND relation=pg_catalog.to_regclass('public.app_mfa_factor'))
            """,connection,transaction))
            if(await guard.ExecuteScalarAsync(cancellationToken) is not true)
                throw new MfaMaintenanceException("mfa_maintenance_census_lock_required");
        return await ReadCountsAsync(connection,transaction,installationId,cancellationToken);
    }

    private static async Task<MfaFactorVersionInventory> ReadCountsAsync(NpgsqlConnection connection,
        NpgsqlTransaction transaction,Guid installationId,CancellationToken cancellationToken)
    {
        var counts = new SortedDictionary<int, MfaKeyVersionCount>();
        // All Systemhaus/users and all factor states. No ciphertext or identity is
        // selected, and public qualification prevents a temporary search_path alias.
        await using (var command = new NpgsqlCommand("""
            SELECT key_version,state,count(*)
            FROM public.app_mfa_factor
            GROUP BY key_version,state
            ORDER BY key_version,state
            """, connection, transaction))
        await using (var rows = await command.ExecuteReaderAsync(cancellationToken))
        {
            while (await rows.ReadAsync(cancellationToken))
            {
                var version = rows.GetInt32(0);
                var state = rows.GetString(1);
                var count = rows.GetInt64(2);
                if (count <= 0 || (!counts.ContainsKey(version) && counts.Count >= MfaKeyRing.MaxVersions))
                    throw new MfaKeyRetentionException("mfa_retention_invalid");
                var current = counts.GetValueOrDefault(version) ?? new MfaKeyVersionCount(version, 0, 0, 0);
                try
                {
                    counts[version] = state switch
                    {
                        "pending" => current with { Pending = checked(current.Pending + count) },
                        "active" => current with { Active = checked(current.Active + count) },
                        "disabled" => current with { Disabled = checked(current.Disabled + count) },
                        _ => throw new MfaKeyRetentionException("mfa_retention_invalid")
                    };
                }
                catch (OverflowException)
                {
                    throw new MfaKeyRetentionException("mfa_retention_invalid");
                }
            }
        }
        return MfaKeyRetention.FactorInventory(installationId, counts.Values);
    }
}
