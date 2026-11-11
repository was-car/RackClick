using System.Data;
using System.Globalization;
using System.Runtime.Versioning;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;
using Npgsql;

namespace RackClick.Server;

internal sealed record MfaLossResetPlan(Guid InstallationId,Guid OperationId,Guid SystemhausId,string OperatorSid,
    int[] LostVersions,int NewVersion,string SourceRingHash,string SourceFilesHash,string CatalogHash,
    string SnapshotHash,Guid[] AffectedBackups,long Factors,long Sessions,long Challenges,long Codes,DateTime PlannedAtUtc)
{
    public override string ToString()=>"MfaLossResetPlan(metadata-redacted)";
}
internal sealed record MfaLossResetWitness(Guid OperationId,string PlanHash,string EnvelopeHash,string MaterialHash,
    string PostSecurityHash,string ArchiveHash,long Factors,long Sessions,long Challenges,long Codes,
    string Mode,string Authority,Guid InstallationId,string DatabaseName,Guid SystemhausId,string OperatorSid,int[] LostVersions,int NewVersion,DateTime CommittedAtUtc);

// SQL adapter under explicit maintenance/table exclusion. No COMMIT here; caller retains the durable fence.
[SupportedOSPlatform("windows")]
internal static class MfaLossResetDatabase
{
    private static readonly string[] ExtraTables=["public.app_mfa_policy","rackclick_private.mfa_loss_operation","rackclick_private.mfa_loss_factor_archive"];
    internal static int NextVersion(int[] versions,bool complete,int retained)
    {
        if(!complete || versions.Length==0 || versions.Any(v=>v is <1 or >1000000) || retained is <0 or >=64)
            throw Fail("mfa_loss_history_unknown_or_capacity");
        int maximum=versions.Max();if(maximum>=1000000)throw Fail("mfa_loss_version_capacity");return maximum+1;
    }
    internal static async Task LockAsync(NpgsqlConnection db,NpgsqlTransaction tx,CancellationToken ct)
    {
        await MfaRotationDatabase.LockAsync(db,tx,ct);
        foreach(var table in ExtraTables)
        {await using var command=new NpgsqlCommand("LOCK TABLE "+table+" IN ACCESS EXCLUSIVE MODE",db,tx);await command.ExecuteNonQueryAsync(ct);}
    }
    private static async Task RequireAsync(NpgsqlConnection db,NpgsqlTransaction tx,Guid installation,CancellationToken ct)
    {
        if(tx.Connection!=db || tx.IsolationLevel!=IsolationLevel.ReadCommitted)throw Fail("mfa_loss_transaction_required");
        await MfaMaintenanceCoordinator.ValidateDatabase(db,installation,ct);
        await using var check=new NpgsqlCommand("""
            SELECT (SELECT max(version) IN (47,48) FROM public.schema_migration) AND current_setting('synchronous_commit')='on'
            AND NOT EXISTS(SELECT 1 FROM unnest(@tables::text[]) t(name) WHERE NOT EXISTS(
                SELECT 1 FROM pg_catalog.pg_locks WHERE pid=pg_backend_pid() AND granted AND mode='AccessExclusiveLock'
                AND relation=pg_catalog.to_regclass(t.name)))
            """,db,tx);
        check.Parameters.AddWithValue("tables",ExtraTables.Concat(new[]{"public.app_mfa_factor","public.app_session","public.app_mfa_user","public.app_user","public.app_mfa_challenge","public.app_mfa_recovery_code","public.systemhaus","public.app_mfa_rotation_witness"}).ToArray());
        if(await check.ExecuteScalarAsync(ct) is not true)throw Fail("mfa_loss_locks_required");
    }
    internal static async Task<MfaLossResetPlan> PlanAsync(NpgsqlConnection db,NpgsqlTransaction tx,Guid installation,Guid operation,
        string sid,byte[] ringBytes,int[] fileVersions,int journalMaximum,int[] lost,MfaBackupCatalogSnapshot backups,string filesHash,CancellationToken ct)
    {
        await RequireAsync(db,tx,installation,ct);
        var ring=MfaKeyRing.Parse(ringBytes,installation);
        if(operation==Guid.Empty || sid.Length>184 || !Regex.IsMatch(sid,@"\AS-1-[0-9]+(-[0-9]+){1,15}\z",RegexOptions.CultureInvariant|RegexOptions.NonBacktracking)
            || lost.Length is <1 or >64 || lost.Distinct().Count()!=lost.Length || lost.Any(v=>v is <1 or >1000000)
            || backups.InstallationId!=installation)throw Fail("mfa_loss_plan_invalid");
        if(await ReadWitnessAsync(db,tx,operation,ct) is not null)throw Fail("mfa_loss_operation_exists");
        await using var houses=new NpgsqlCommand("SELECT id FROM public.systemhaus ORDER BY id",db,tx);
        Guid house;
        await using(var rows=await houses.ExecuteReaderAsync(ct))
        {if(!await rows.ReadAsync(ct))throw Fail("mfa_loss_systemhaus_invalid");house=rows.GetGuid(0);if(house==Guid.Empty||await rows.ReadAsync(ct))throw Fail("mfa_loss_systemhaus_invalid");}
        var inventory=await MfaFactorKeyInventoryReader.ReadForMaintenanceAsync(db,tx,installation,ct);
        var known=ring.Entries.Select(e=>e.Version).Concat(fileVersions).Concat(inventory.Entries.Select(e=>e.Version))
            .Concat(backups.Backups.SelectMany(b=>b.RequiredVersions.Concat(b.EnvelopeVersions))).ToList();
        if(journalMaximum>0)known.Add(journalMaximum);
        await using(var history=new NpgsqlCommand("SELECT GREATEST(COALESCE((SELECT max(new_version) FROM public.app_mfa_rotation_witness),0),COALESCE((SELECT max(new_version) FROM rackclick_private.mfa_loss_operation),0),COALESCE((SELECT max(key_version) FROM rackclick_private.mfa_loss_factor_archive),0))",db,tx))
        {var maximum=Convert.ToInt32(await history.ExecuteScalarAsync(ct),CultureInfo.InvariantCulture);if(maximum>0)known.Add(maximum);}
        if(lost.Any(v=>!known.Contains(v)) || inventory.Entries.Any(e=>!lost.Contains(e.Version)&&!ring.Entries.Any(r=>r.Version==e.Version))
            || backups.Backups.SelectMany(b=>b.RequiredVersions).Any(v=>!lost.Contains(v)&&!ring.Entries.Any(r=>r.Version==v)))throw Fail("mfa_loss_versions_not_declared");
        var next=NextVersion(known.ToArray(),true,ring.Entries.Count(e=>!lost.Contains(e.Version)));
        await using(var bad=new NpgsqlCommand("""
            SELECT EXISTS(SELECT 1 FROM public.app_mfa_factor f LEFT JOIN public.app_user u ON u.systemhaus_id=f.systemhaus_id AND u.id=f.user_id
                WHERE f.systemhaus_id<>@house OR u.id IS NULL OR octet_length(to_jsonb(f)::text)>65536)
            OR EXISTS(SELECT 1 FROM public.app_mfa_user m JOIN public.app_mfa_factor f USING(systemhaus_id,user_id)
                WHERE f.key_version=ANY(@lost) AND m.revision>=9007199254740991)
            """,db,tx))
        {bad.Parameters.AddWithValue("house",house);bad.Parameters.AddWithValue("lost",lost);if(await bad.ExecuteScalarAsync(ct) is true)throw Fail("mfa_loss_factor_or_policy_invalid");}
        var counts=new long[4];
        string affected="EXISTS(SELECT 1 FROM public.app_mfa_factor f WHERE f.key_version=ANY(@lost) AND f.user_id=t.user_id)";
        string[] countQueries=["SELECT count(*) FROM public.app_mfa_factor t WHERE key_version=ANY(@lost)",
            "SELECT count(*) FROM public.app_session t WHERE "+affected,"SELECT count(*) FROM public.app_mfa_challenge t WHERE consumed_at IS NULL AND "+affected,
            "SELECT count(*) FROM public.app_mfa_recovery_code t WHERE consumed_at IS NULL AND "+affected];
        for(int i=0;i<countQueries.Length;i++){await using var count=new NpgsqlCommand(countQueries[i],db,tx);count.Parameters.AddWithValue("lost",lost);counts[i]=(long)(await count.ExecuteScalarAsync(ct))!;}
        return new(installation,operation,house,sid,lost.Order().ToArray(),next,Hash(ringBytes),filesHash,backups.Digest,
            await SnapshotAsync(db,tx,ct),backups.Backups.Where(b=>b.RequiredVersions.Any(lost.Contains)).Select(b=>b.BackupId).Order().ToArray(),counts[0],counts[1],counts[2],counts[3],DateTime.UtcNow);
    }
    internal static Task<string> SnapshotAsync(NpgsqlConnection db,NpgsqlTransaction tx,CancellationToken ct)=>HashRows(db,tx,
        ["SELECT to_jsonb(t)::text FROM public.app_mfa_factor t ORDER BY systemhaus_id,user_id",
         "SELECT to_jsonb(t)::text FROM public.app_mfa_user t ORDER BY systemhaus_id,user_id",
         "SELECT to_jsonb(t)::text FROM public.app_user t ORDER BY id",
         "SELECT to_jsonb(t)::text FROM public.app_session t ORDER BY token_hash",
         "SELECT to_jsonb(t)::text FROM public.app_mfa_challenge t ORDER BY token_hash",
         "SELECT to_jsonb(t)::text FROM public.app_mfa_recovery_code t ORDER BY systemhaus_id,user_id,code_hash",
         "SELECT to_jsonb(t)::text FROM public.app_mfa_policy t ORDER BY systemhaus_id",
         "SELECT to_jsonb(t)::text FROM public.systemhaus t ORDER BY id"],ct);
    private static async Task<string> HashRows(NpgsqlConnection db,NpgsqlTransaction tx,string[] queries,CancellationToken ct,Guid? operation=null)
    {
        using var hash=IncrementalHash.CreateHash(HashAlgorithmName.SHA256);
        await using(var format=new NpgsqlCommand("SET LOCAL TimeZone='UTC'; SET LOCAL DateStyle='ISO, YMD'; SET LOCAL bytea_output='hex'",db,tx))await format.ExecuteNonQueryAsync(ct);
        foreach(var sql in queries)
        {
            hash.AppendData([0]);await using var command=new NpgsqlCommand(sql.Replace("SELECT to_jsonb(t)::text", "SELECT CASE WHEN octet_length(to_jsonb(t)::text)<=65536 THEN to_jsonb(t)::text ELSE NULL END",StringComparison.Ordinal),db,tx);
            if(operation.HasValue)command.Parameters.AddWithValue("operation",operation.Value);
            await using var rows=await command.ExecuteReaderAsync(ct);
            while(await rows.ReadAsync(ct))
            {
                if(rows.IsDBNull(0))throw Fail("mfa_loss_snapshot_row_too_large");var text=rows.GetString(0);
                var bytes=Encoding.UTF8.GetBytes(text);
                try{hash.AppendData(BitConverter.GetBytes(bytes.Length));hash.AppendData(bytes);}finally{CryptographicOperations.ZeroMemory(bytes);}
            }
        }
        return Convert.ToHexStringLower(hash.GetHashAndReset());
    }
    internal static async Task<MfaLossResetWitness?> ReadWitnessAsync(NpgsqlConnection db,NpgsqlTransaction tx,Guid operation,CancellationToken ct)
        =>await ReadWitnessCore(db,tx,operation,false,ct);
    internal static async Task<MfaLossResetWitness?> ReadStartupWitnessAsync(NpgsqlConnection db,NpgsqlTransaction tx,Guid operation,CancellationToken ct)
        =>await ReadWitnessCore(db,tx,operation,true,ct);
    private static async Task<MfaLossResetWitness?> ReadWitnessCore(NpgsqlConnection db,NpgsqlTransaction tx,Guid operation,bool startup,CancellationToken ct)
    {
        var table=startup?"public.app_mfa_loss_startup_witness":"rackclick_private.mfa_loss_operation";
        await using var command=new NpgsqlCommand("SELECT plan_sha256,envelope_sha256,material_sha256,post_security_sha256,archive_sha256,affected_factors,revoked_sessions,consumed_challenges,consumed_codes,mode,authority,installation_id,database_name,systemhaus_id,operator_sid,lost_versions,new_version,committed_at FROM "+table+" WHERE operation_id=@operation",db,tx);
        command.Parameters.AddWithValue("operation",operation);await using var row=await command.ExecuteReaderAsync(ct);
        return await row.ReadAsync(ct)?new(operation,row.GetString(0),row.GetString(1),row.GetString(2),row.GetString(3),row.GetString(4),row.GetInt64(5),row.GetInt64(6),row.GetInt64(7),row.GetInt64(8),
            row.GetString(9),row.GetString(10),row.GetGuid(11),row.GetString(12),row.GetGuid(13),row.GetString(14),row.GetFieldValue<int[]>(15),row.GetInt32(16),row.GetDateTime(17)):null;
    }
    internal static void RequireWitness(MfaLossResetPlan p,string materialHash,MfaLossResetWitness w,string? envelopeHash=null)
    {
        if(w.OperationId!=p.OperationId||w.Mode!="loss-reset"||w.Authority!="windows-local"||w.InstallationId!=p.InstallationId
            ||w.DatabaseName!="rc_db_"+p.InstallationId.ToString("N")||w.SystemhausId!=p.SystemhausId||w.OperatorSid!=p.OperatorSid
            ||!w.LostVersions.SequenceEqual(p.LostVersions)||w.NewVersion!=p.NewVersion||w.PlanHash!=Hash(JsonSerializer.SerializeToUtf8Bytes(p))
            ||w.MaterialHash!=materialHash||envelopeHash is not null&&w.EnvelopeHash!=envelopeHash
            ||w.Factors!=p.Factors||w.Sessions!=p.Sessions||w.Challenges!=p.Challenges||w.Codes!=p.Codes
            ||w.CommittedAtUtc.Kind!=DateTimeKind.Utc||w.CommittedAtUtc<p.PlannedAtUtc||w.CommittedAtUtc>DateTime.UtcNow.AddMinutes(1))
            throw Fail("mfa_loss_witness_mismatch");
    }
    internal static async Task<MfaLossResetWitness> ApplyAsync(NpgsqlConnection db,NpgsqlTransaction tx,MfaLossResetPlan plan,
        string envelopeHash,string materialHash,CancellationToken ct)
    {
        await RequireAsync(db,tx,plan.InstallationId,ct);
        string planHash=Hash(JsonSerializer.SerializeToUtf8Bytes(plan));
        var previous=await ReadWitnessAsync(db,tx,plan.OperationId,ct);
        if(previous is not null)
        {RequireWitness(plan,materialHash,previous,envelopeHash);return previous;}
        if(await SnapshotAsync(db,tx,ct)!=plan.SnapshotHash)throw Fail("mfa_loss_database_changed");
        try
        {
            await using(var insert=new NpgsqlCommand("""
                INSERT INTO rackclick_private.mfa_loss_operation(operation_id,mode,authority,installation_id,database_name,systemhaus_id,operator_sid,lost_versions,new_version,
                    plan_sha256,envelope_sha256,material_sha256,post_security_sha256,archive_sha256,affected_factors,revoked_sessions,consumed_challenges,consumed_codes)
                VALUES(@operation,'loss-reset','windows-local',@installation,current_database(),@house,@sid,@lost,@version,@plan,@envelope,@material,@zero,@zero,0,0,0,0)
                """,db,tx))
            {
                insert.Parameters.AddWithValue("operation",plan.OperationId);insert.Parameters.AddWithValue("installation",plan.InstallationId);insert.Parameters.AddWithValue("house",plan.SystemhausId);
                insert.Parameters.AddWithValue("sid",plan.OperatorSid);insert.Parameters.AddWithValue("lost",plan.LostVersions);insert.Parameters.AddWithValue("version",plan.NewVersion);
                insert.Parameters.AddWithValue("plan",planHash);insert.Parameters.AddWithValue("envelope",envelopeHash);insert.Parameters.AddWithValue("material",materialHash);insert.Parameters.AddWithValue("zero",new string('0',64));await insert.ExecuteNonQueryAsync(ct);
            }
            await using(var archive=new NpgsqlCommand("INSERT INTO rackclick_private.mfa_loss_factor_archive SELECT @operation,f.systemhaus_id,f.user_id,f.key_version,to_jsonb(f) FROM public.app_mfa_factor f WHERE f.key_version=ANY(@lost)",db,tx))
            {archive.Parameters.AddWithValue("operation",plan.OperationId);archive.Parameters.AddWithValue("lost",plan.LostVersions);if(await archive.ExecuteNonQueryAsync(ct)!=plan.Factors)throw Fail("mfa_loss_archive_write_invalid");}
            await using(var pending=new NpgsqlCommand("""
                INSERT INTO public.app_mfa_user(systemhaus_id,user_id,mfa_required,enrollment_pending,revision,changed_by,changed_at)
                SELECT systemhaus_id,user_id,true,true,1,NULL,clock_timestamp() FROM rackclick_private.mfa_loss_factor_archive WHERE operation_id=@operation
                ON CONFLICT(systemhaus_id,user_id) DO UPDATE SET mfa_required=true,enrollment_pending=true,revision=app_mfa_user.revision+1,changed_at=clock_timestamp()
                """,db,tx))
            {pending.Parameters.AddWithValue("operation",plan.OperationId);if(await pending.ExecuteNonQueryAsync(ct)!=plan.Factors)throw Fail("mfa_loss_pending_write_invalid");}
            var counts=new long[4];
            string affected="EXISTS(SELECT 1 FROM rackclick_private.mfa_loss_factor_archive a WHERE a.operation_id=@operation AND a.user_id=t.user_id)";
            string[] changes=["DELETE FROM public.app_mfa_factor t WHERE "+affected,
                "DELETE FROM public.app_session t WHERE "+affected,
                "UPDATE public.app_mfa_challenge t SET consumed_at=clock_timestamp() WHERE consumed_at IS NULL AND "+affected,
                "UPDATE public.app_mfa_recovery_code t SET consumed_at=clock_timestamp() WHERE consumed_at IS NULL AND "+affected];
            for(int i=0;i<changes.Length;i++)
            {await using var change=new NpgsqlCommand(changes[i],db,tx);change.Parameters.AddWithValue("operation",plan.OperationId);counts[i]=await change.ExecuteNonQueryAsync(ct);}
            string post=await SnapshotAsync(db,tx,ct), archived=await ArchiveHashAsync(db,tx,plan.OperationId,ct);
            await using(var finish=new NpgsqlCommand("UPDATE rackclick_private.mfa_loss_operation SET post_security_sha256=@post,archive_sha256=@archive,affected_factors=@f,revoked_sessions=@s,consumed_challenges=@c,consumed_codes=@r WHERE operation_id=@operation",db,tx))
            {finish.Parameters.AddWithValue("post",post);finish.Parameters.AddWithValue("archive",archived);finish.Parameters.AddWithValue("f",counts[0]);finish.Parameters.AddWithValue("s",counts[1]);finish.Parameters.AddWithValue("c",counts[2]);finish.Parameters.AddWithValue("r",counts[3]);finish.Parameters.AddWithValue("operation",plan.OperationId);if(await finish.ExecuteNonQueryAsync(ct)!=1)throw Fail("mfa_loss_witness_write_invalid");}
            // A successful SQL command may still have skipped/changed rows. Validate the fresh witness before COMMIT,
            // including the zero-factor case; Publish must not be the first place an incomplete transition is detected.
            var witness=await ReadWitnessAsync(db,tx,plan.OperationId,ct)??throw Fail("mfa_loss_witness_missing");
            RequireWitness(plan,materialHash,witness,envelopeHash);
            if(witness.PostSecurityHash!=post||witness.ArchiveHash!=archived)throw Fail("mfa_loss_witness_mismatch");
            return witness;
        }
        catch{if(tx.Connection is not null)try{await tx.RollbackAsync(CancellationToken.None);}catch(NpgsqlException){}throw;}
    }
    internal static Task<string> ArchiveHashAsync(NpgsqlConnection db,NpgsqlTransaction tx,Guid operation,CancellationToken ct)
    {
        return HashRows(db,tx,["SELECT to_jsonb(t)::text FROM rackclick_private.mfa_loss_factor_archive t WHERE operation_id=@operation ORDER BY systemhaus_id,user_id"],ct,operation);
    }
    internal static string Hash(byte[] bytes)=>Convert.ToHexStringLower(SHA256.HashData(bytes));
    private static MfaMaintenanceException Fail(string code)=>new(code);
}
