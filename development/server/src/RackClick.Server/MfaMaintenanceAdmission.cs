using Npgsql;

namespace RackClick.Server;

internal sealed class MfaMaintenanceException(string code) : Exception(code)
{
    internal string Code => Message;
}

// Same key in host/backup/maintenance. A lease is coordination, never a replacement for table locks or a durable fence.
internal static class MfaMaintenanceAdmission
{
    internal const string SharedSql = "SELECT pg_catalog.pg_try_advisory_lock_shared(81726202,pg_catalog.hashtext(current_database()))";
    internal const string ExclusiveSql = "SELECT pg_catalog.pg_try_advisory_lock(81726202,pg_catalog.hashtext(current_database()))";

    internal static FileStream HoldHostRing(string root,Guid installation)
    {
        ThrowIfFenced(root,installation);
        return new FileStream(Path.Combine(root,installation.ToString("D"),"mfa-keys",MfaKeyRing.RingFileName),
            FileMode.Open,FileAccess.Read,FileShare.Read);
    }

    internal static void RequireNoHostRingLease(string root,Guid installation)
    {
        try
        {
            using var probe=new FileStream(Path.Combine(root,installation.ToString("D"),"mfa-keys",MfaKeyRing.RingFileName),
                FileMode.Open,FileAccess.ReadWrite,FileShare.Read);
        }
        catch(IOException){throw new MfaMaintenanceException("mfa_maintenance_host_still_running");}
    }

    internal static void ThrowIfFenced(string instancesRoot, Guid installationId)
    {
        var path=Path.Combine(Path.GetFullPath(instancesRoot),installationId.ToString("D"),"mfa-maintenance-fence.json");
        try
        {
            _=File.GetAttributes(path);
            throw new MfaMaintenanceException("mfa_maintenance_pending");
        }
        catch(FileNotFoundException) { }
        // Missing parents are not proof of an absent fence: composition validates the store separately.
    }

    internal static async Task<MfaMaintenanceLease> SharedAsync(NpgsqlConnection connection,CancellationToken ct)
    {
        await using var command=new NpgsqlCommand(SharedSql,connection);
        if(await command.ExecuteScalarAsync(ct) is not true)throw new MfaMaintenanceException("mfa_maintenance_busy");
        return new MfaMaintenanceLease(connection,false);
    }

    internal static async Task<MfaMaintenanceLease> ExclusiveAsync(NpgsqlConnection connection,CancellationToken ct)
    {
        await using var command=new NpgsqlCommand(ExclusiveSql,connection);
        if(await command.ExecuteScalarAsync(ct) is not true)throw new MfaMaintenanceException("mfa_maintenance_busy");
        return new MfaMaintenanceLease(connection,true);
    }
}

internal sealed class MfaMaintenanceLease(NpgsqlConnection connection,bool exclusive):IAsyncDisposable
{
    private bool disposed;
    private int healthy=1;
    internal NpgsqlConnection Connection=>connection;
    internal bool IsHealthy=>Volatile.Read(ref healthy)==1 && !disposed && connection.State==System.Data.ConnectionState.Open;

    internal async Task MonitorAsync(Action stop,CancellationToken ct)
    {
        using var timer=new PeriodicTimer(TimeSpan.FromMilliseconds(500));
        try
        {
            while(await timer.WaitForNextTickAsync(ct))
            {
                await using var command=new NpgsqlCommand("SELECT EXISTS(SELECT 1 FROM pg_catalog.pg_locks WHERE pid=pg_catalog.pg_backend_pid() AND locktype='advisory' AND classid=81726202 AND granted)",connection){CommandTimeout=1};
                if(await command.ExecuteScalarAsync(ct) is not true)throw new InvalidOperationException("admission_lost");
            }
        }
        catch(OperationCanceledException)when(ct.IsCancellationRequested){ }
        catch(Exception error)when(error is NpgsqlException or InvalidOperationException or IOException)
        {Interlocked.Exchange(ref healthy,0);stop();}
    }
    public async ValueTask DisposeAsync()
    {
        if(disposed)return;disposed=true;
        try
        {
            if(connection.State==System.Data.ConnectionState.Open)
            {
                var sql=exclusive?"SELECT pg_catalog.pg_advisory_unlock(81726202,pg_catalog.hashtext(current_database()))":"SELECT pg_catalog.pg_advisory_unlock_shared(81726202,pg_catalog.hashtext(current_database()))";
                await using var command=new NpgsqlCommand(sql,connection){CommandTimeout=5};
                await command.ExecuteScalarAsync();
            }
        }
        catch(NpgsqlException) { await connection.CloseAsync(); }
        catch(InvalidOperationException) { await connection.CloseAsync(); }
    }
}
