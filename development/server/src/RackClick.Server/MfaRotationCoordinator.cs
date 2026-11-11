using System.Data;
using System.Globalization;
using System.Runtime.Versioning;
using System.Security.Cryptography;
using System.Security.Principal;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Text.RegularExpressions;
using Npgsql;

namespace RackClick.Server;

// Internal offline protocol. No HTTP/CLI activation: production custody/persistence/service-token gates remain separate.
// Plaintext keys/passwords/envelopes never enter journal or public receipts. Callers own/zero returned encrypted envelopes.
internal sealed record MfaRotationResult(Guid OperationId,int NewVersion,string Phase,long Factors=0);

[SupportedOSPlatform("windows")]
internal static class MfaRotationCoordinator
{
    private sealed record Plan(Guid InstallationId,Guid OperationId,Guid SystemhausId,string OperatorSid,int OldVersion,
        int NewVersion,string SnapshotHash,string CatalogHash);
    private sealed record Ready(MfaRotationBinding Binding,string SnapshotHash);

    internal static Task<MfaRotationResult> PrepareAsync(MfaMaintenanceRequest request,
        IReadOnlyCollection<SecurityIdentifier> trusted,Action<string>? checkpoint,CancellationToken ct) =>
        Exclusive<MfaRotationResult>(request,trusted,async (db,storage)=>
        {
            await using var tx=await db.BeginTransactionAsync(IsolationLevel.ReadCommitted,ct);
            await MfaRotationDatabase.LockAsync(db,tx,ct);
            if(request.OperationId==Guid.Empty)throw Fail("mfa_rotation_operation_invalid");
            // Existing pending retirement/rotation cannot be silently adopted as a new operation.
            if(storage.ReadPending() is not null)throw Fail("mfa_maintenance_pending");
            using var backups=Catalog(request,storage,trusted);
            var original=storage.ReadRing();var ring=MfaKeyRing.Parse(original,request.InstallationId);
            var provider=Provider(request,trusted);
            var inventory=await MfaFactorKeyInventoryReader.ReadForMaintenanceAsync(db,tx,request.InstallationId,ct);
            MfaMaintenanceCoordinator.ValidateMaterial(original,request.InstallationId,provider,inventory,backups.Backups);
            await MfaMaintenanceCoordinator.AuthenticateFactors(db,tx,provider,ct);
            var systemhaus=await Systemhaus(db,tx,ct);
            var snapshot=await MfaRotationDatabase.ReadSnapshotHashAsync(db,tx,ct);
            var maximum=ring.Entries.Max(e=>e.Version);
            maximum=Math.Max(maximum,storage.HighestRotationVersion());
            await using(var query=new NpgsqlCommand("SELECT COALESCE(max(new_version),0) FROM public.app_mfa_rotation_witness",db,tx))
                maximum=Math.Max(maximum,Convert.ToInt32(await query.ExecuteScalarAsync(ct),CultureInfo.InvariantCulture));
            var folder=Path.Combine(request.InstancesRoot,request.InstallationId.ToString("D"),"mfa-keys");
            foreach(var path in Directory.EnumerateFileSystemEntries(folder))
            {
                if(Path.GetFileName(path)==MfaKeyRing.RingFileName)continue;
                var match=Regex.Match(Path.GetFileName(path),"^key-v([1-9][0-9]{0,6})\\.dpapi\\.json$",RegexOptions.CultureInvariant);
                if(!match.Success || !int.TryParse(match.Groups[1].Value,out var found) || found>1_000_000)
                    throw Fail("mfa_rotation_unknown_material");
                maximum=Math.Max(maximum,found);
            }
            if(maximum>=1_000_000 || ring.Entries.Count>=MfaKeyRing.MaxVersions)throw Fail("mfa_rotation_version_capacity");
            var version=maximum+1;var old=ring.Entries.Single(e=>e.State==MfaKeyState.Active).Version;
            var created=DateTimeOffset.UtcNow;
            var additive=Ring(request.InstallationId,ring.Entries.Append(new(version,MfaKeyState.Retired,created)));
            var final=Ring(request.InstallationId,ring.Entries.Select(e=>e.Version==old?e with{State=MfaKeyState.Retired}:e)
                .Append(new(version,MfaKeyState.Active,created)));
            var plan=new Plan(request.InstallationId,request.OperationId,systemhaus,Operator(),old,version,snapshot,request.ExpectedCatalogHash);
            // Reuse the approved writer's DPAPI/format in memory; store owns all exclusive disk publication.
            var key=RandomNumberGenerator.GetBytes(32);
            try
            {
                var bytes=WindowsMfaKeyStoreWriter.ProtectVersionMaterial(request.InstallationId,version,key);
                storage.PrepareRotation(request.OperationId,version,bytes,original,additive,final,request.ExpectedCatalogHash);
            }
            finally{CryptographicOperations.ZeroMemory(key);}
            var priorReceipt=storage.RecordRotationStartupPrior(request.OperationId);
            if(priorReceipt is not null)
            {
                var priorWitness=await MfaRotationDatabase.ReadWitnessAsync(db,tx,priorReceipt.OperationId,ct);
                if(priorWitness is null || priorReceipt.NewVersion!=old || priorReceipt.BindingHash!=Hash(JsonSerializer.SerializeToUtf8Bytes(priorWitness.Binding)))
                    throw Fail("mfa_rotation_startup_prior_invalid");
            }
            storage.WriteRotationMetadata(request.OperationId,"coordinator-plan",JsonSerializer.SerializeToUtf8Bytes(plan));
            checkpoint?.Invoke("planned");
            storage.Checkpoint=phase=>
            {
                checkpoint?.Invoke(phase);
                if(phase=="before_rotation_complete")RequireAdmission(db,ct).GetAwaiter().GetResult();
            };
            storage.PublishRotationKey(request.OperationId);
            storage.PublishRotationAdditive(request.OperationId);
            await tx.CommitAsync(ct); // read-only DB transaction; no witness/factor mutation yet.
            return new(request.OperationId,version,"awaiting_external_envelope");
        },ct);

    // The encrypted bytes are returned to an explicit custodian; this method never stores them inside the instance/backups.
    internal static Task<byte[]> ExportAsync(MfaMaintenanceRequest request,IReadOnlyCollection<SecurityIdentifier> trusted,
        string password,CancellationToken ct) => Exclusive(request,trusted,async(db,storage)=>
        {
            await using var tx=await db.BeginTransactionAsync(IsolationLevel.ReadCommitted,ct);
            await MfaRotationDatabase.LockAsync(db,tx,ct);
            var pending=storage.ReadRotation(request.OperationId);ReadPlan(request,storage,pending);
            using var backups=Catalog(request,storage,trusted);
            storage.PublishRotationKey(request.OperationId);storage.PublishRotationAdditive(request.OperationId);
            var result=WindowsMfaKeyRecovery.Export(request.InstancesRoot,request.InstallationId,request.ReaderSid,trusted,password);
            await tx.CommitAsync(ct);
            return result;
        },ct);

    // Re-entry is always by the same operation and explicit catalog pin. A DB witness, never process exit, decides commit.
    internal static Task<MfaRotationResult> ResumeAsync(MfaMaintenanceRequest request,IReadOnlyCollection<SecurityIdentifier> trusted,
        byte[]? externalEnvelope,string? password,string expectedEnvelopeHash,Action<string>? checkpoint,CancellationToken ct) =>
        Exclusive<MfaRotationResult>(request,trusted,async(db,storage)=>
        {
            var pending=storage.ReadRotation(request.OperationId);
            var plan=ReadPlan(request,storage,pending);
            using var backups=Catalog(request,storage,trusted);
            storage.Checkpoint=phase=>
            {
                checkpoint?.Invoke(phase);
                if(phase=="before_rotation_complete")RequireAdmission(db,ct).GetAwaiter().GetResult();
            };
            await using(var tx=await db.BeginTransactionAsync(IsolationLevel.ReadCommitted,ct))
            {
                await MfaRotationDatabase.LockAsync(db,tx,ct);
                var witness=await MfaRotationDatabase.ReadWitnessAsync(db,tx,request.OperationId,ct);
                if(witness is null)
                {
                    // Completed local evidence plus an older/lost DB witness is a Restore/coherence incident,
                    // not an uncommitted transaction that this rotation may silently replay.
                    if(pending.State=="verified")throw Fail("mfa_rotation_completed_witness_missing");
                    if(await MfaRotationDatabase.ReadSnapshotHashAsync(db,tx,ct)!=plan.SnapshotHash)
                        throw Fail("mfa_rotation_database_changed");
                    storage.PublishRotationKey(request.OperationId);storage.PublishRotationAdditive(request.OperationId);
                    // Even a saved material-ready record does not replace proof of the external envelope on retry.
                    if(externalEnvelope is null || password is null || Hash(externalEnvelope)!=expectedEnvelopeHash)
                        throw Fail("mfa_rotation_external_envelope_required");
                    VerifyEnvelope(request,pending,trusted,externalEnvelope,password);
                    var binding=new MfaRotationBinding(request.OperationId,request.InstallationId,plan.SystemhausId,plan.OperatorSid,
                        plan.OldVersion,plan.NewVersion,Hash(pending.OriginalRing),Hash(pending.AdditiveRing),Hash(pending.FinalRing),
                        pending.NewKeyHash,plan.CatalogHash,expectedEnvelopeHash);
                    var ready=new Ready(binding,plan.SnapshotHash);
                    storage.WriteRotationMetadata(request.OperationId,"material-ready",JsonSerializer.SerializeToUtf8Bytes(ready));
                    checkpoint?.Invoke("material_ready");
                    var provider=Provider(request,trusted);byte[]? key=null;
                    try
                    {
                        key=provider.GetKey(plan.NewVersion);
                        witness=await MfaRotationDatabase.RewrapAsync(db,tx,binding,provider,key,ct);
                    }
                    finally{if(key is not null)CryptographicOperations.ZeroMemory(key);}
                    checkpoint?.Invoke("before_db_commit");
                    await tx.CommitAsync(ct);
                    // A kill or lost reply here leaves a committed witness and the fence. Resume must NOT recipher twice.
                    checkpoint?.Invoke("after_db_commit");
                }
                else
                {
                    RequireWitness(request,storage,pending,plan,witness);
                    await tx.CommitAsync(ct);
                }
            }
            // Reacquire table locks after commit while retaining session/local exclusion and persistent fence.
            await using var verify=await db.BeginTransactionAsync(IsolationLevel.ReadCommitted,ct);
            await MfaRotationDatabase.LockAsync(db,verify,ct);
            var committed=await MfaRotationDatabase.ReadWitnessAsync(db,verify,request.OperationId,ct)
                ?? throw Fail("mfa_rotation_witness_missing");
            RequireWitness(request,storage,pending,plan,committed);
            storage.PublishRotationFinal(request.OperationId);
            using(var rescan=Catalog(request,storage,trusted))
            {
                var provider=Provider(request,trusted);
                var inventory=await MfaFactorKeyInventoryReader.ReadForMaintenanceAsync(db,verify,request.InstallationId,ct);
                MfaMaintenanceCoordinator.ValidateMaterial(pending.FinalRing,request.InstallationId,provider,inventory,rescan.Backups);
                await MfaRotationDatabase.ValidateCommittedAsync(db,verify,committed,provider,ct);
            }
            checkpoint?.Invoke("data_verified");
            await RequireAdmission(db,ct);
            storage.PublishRotationStartupReceipt(committed);
            storage.CompleteRotation(request.OperationId);
            await verify.CommitAsync(ct); // no data writes; the earlier committed witness is authoritative.
            return new(request.OperationId,pending.NewVersion,"verified",committed.FactorCount);
        },ct);

    private static void RequireWitness(MfaMaintenanceRequest r,WindowsMfaMaintenanceStore storage,WindowsMfaRotationPending pending,
        Plan plan,MfaRotationWitness witness)
    {
        var ready=Decode<Ready>(storage.ReadRotationMetadata(r.OperationId,"material-ready"));
        if(ready.SnapshotHash!=plan.SnapshotHash || witness.Binding!=ready.Binding || witness.Binding.OperationId!=r.OperationId
            || witness.Binding.InstallationId!=r.InstallationId || witness.Binding.SystemhausId!=plan.SystemhausId
            || witness.Binding.OperatorSid!=plan.OperatorSid || witness.Binding.OldVersion!=plan.OldVersion
            || witness.Binding.NewVersion!=plan.NewVersion || witness.Binding.OriginalRingHash!=Hash(pending.OriginalRing)
            || witness.Binding.AdditiveRingHash!=Hash(pending.AdditiveRing) || witness.Binding.FinalRingHash!=Hash(pending.FinalRing)
            || witness.Binding.NewKeyHash!=pending.NewKeyHash || witness.Binding.CatalogHash!=r.ExpectedCatalogHash)
            throw Fail("mfa_rotation_witness_mismatch");
    }

    private static void VerifyEnvelope(MfaMaintenanceRequest r,WindowsMfaRotationPending pending,
        IReadOnlyCollection<SecurityIdentifier> trusted,byte[] envelope,string password)
    {
        var plain=MfaKeyRecoveryEnvelope.Open(password,envelope);
        try
        {
            using var content=MfaKeyRecoveryPayload.Deserialize(plain,r.InstallationId);
            var ring=MfaKeyRing.Parse(pending.AdditiveRing,r.InstallationId);
            if(!content.Ring.Entries.SequenceEqual(ring.Entries))throw Fail("mfa_rotation_envelope_mismatch");
            var provider=Provider(r,trusted);
            foreach(var entry in ring.Entries)
            {
                var key=provider.GetKey(entry.Version);
                try{if(!CryptographicOperations.FixedTimeEquals(key,content.KeyFor(entry.Version)))throw Fail("mfa_rotation_envelope_mismatch");}
                finally{CryptographicOperations.ZeroMemory(key);}
            }
        }
        finally{CryptographicOperations.ZeroMemory(plain);}
    }

    private static Plan ReadPlan(MfaMaintenanceRequest r,WindowsMfaMaintenanceStore storage,WindowsMfaRotationPending pending)
    {
        var plan=Decode<Plan>(storage.ReadRotationMetadata(r.OperationId,"coordinator-plan"));
        if(plan.InstallationId!=r.InstallationId || plan.OperationId!=r.OperationId || plan.CatalogHash!=r.ExpectedCatalogHash
            || pending.CatalogHash!=r.ExpectedCatalogHash || plan.NewVersion!=pending.NewVersion || plan.OperatorSid!=Operator())
            throw Fail("mfa_rotation_plan_mismatch");
        return plan;
    }

    private static MfaBackupCatalogSnapshot Catalog(MfaMaintenanceRequest r,WindowsMfaMaintenanceStore storage,
        IReadOnlyCollection<SecurityIdentifier> trusted)
    {
        var catalog=MfaBackupCatalog.Parse(storage.ReadCatalog(),r.InstallationId,r.ExpectedCatalogHash);
        MfaMaintenanceCoordinator.RequireRootAuthority(catalog,r.ReaderSid,trusted);
        return MfaBackupCatalog.Open(catalog);
    }

    private static async Task<T> Exclusive<T>(MfaMaintenanceRequest r,IReadOnlyCollection<SecurityIdentifier> trusted,
        Func<NpgsqlConnection,WindowsMfaMaintenanceStore,Task<T>> body,CancellationToken ct)
    {
        await using var db=new NpgsqlConnection(MfaMaintenanceCoordinator.OwnerConnection(r.OwnerConnection,r.InstallationId));
        await db.OpenAsync(ct);await MfaMaintenanceCoordinator.ValidateDatabase(db,r.InstallationId,ct);
        await using(var schema=new NpgsqlCommand("SELECT COALESCE(max(version),0) FROM public.schema_migration",db))
            if(Convert.ToInt32(await schema.ExecuteScalarAsync(ct),CultureInfo.InvariantCulture) is not (46 or 47 or 48))throw Fail("mfa_rotation_schema46_required");
        using var storage=new WindowsMfaMaintenanceStore(r.InstancesRoot,r.InstallationId,r.ReaderSid,trusted);
        using var local=storage.AcquireLock();
        await using var admission=await MfaMaintenanceAdmission.ExclusiveAsync(db,ct);
        MfaMaintenanceAdmission.RequireNoHostRingLease(r.InstancesRoot,r.InstallationId);
        await using(var others=new NpgsqlCommand("SELECT EXISTS(SELECT 1 FROM pg_catalog.pg_stat_activity WHERE datname=current_database() AND backend_type='client backend' AND pid<>pg_catalog.pg_backend_pid())",db))
            if(await others.ExecuteScalarAsync(ct) is true)throw Fail("mfa_maintenance_other_clients");
        return await body(db,storage);
    }

    private static async Task<Guid> Systemhaus(NpgsqlConnection db,NpgsqlTransaction tx,CancellationToken ct)
    {
        await using var command=new NpgsqlCommand("SELECT id FROM public.systemhaus ORDER BY id",db,tx);
        await using var rows=await command.ExecuteReaderAsync(ct);
        if(!await rows.ReadAsync(ct))throw Fail("mfa_rotation_systemhaus_invalid");var id=rows.GetGuid(0);
        if(await rows.ReadAsync(ct))throw Fail("mfa_rotation_systemhaus_invalid");return id;
    }
    private static async Task RequireAdmission(NpgsqlConnection db,CancellationToken ct)
    {
        await using var check=new NpgsqlCommand("SELECT EXISTS(SELECT 1 FROM pg_catalog.pg_locks WHERE pid=pg_catalog.pg_backend_pid() AND locktype='advisory' AND classid=81726202 AND mode='ExclusiveLock' AND granted)",db){CommandTimeout=1};
        if(await check.ExecuteScalarAsync(ct) is not true)throw Fail("mfa_rotation_admission_lost");
    }
    private static T Decode<T>(byte[] bytes)
    {
        var value=JsonSerializer.Deserialize<T>(bytes,new JsonSerializerOptions{UnmappedMemberHandling=JsonUnmappedMemberHandling.Disallow,MaxDepth=8})
            ?? throw Fail("mfa_rotation_metadata_invalid");
        if(!JsonSerializer.SerializeToUtf8Bytes(value).AsSpan().SequenceEqual(bytes))throw Fail("mfa_rotation_metadata_invalid");return value;
    }
    private static WindowsMfaKeyProvider Provider(MfaMaintenanceRequest r,IReadOnlyCollection<SecurityIdentifier> trusted)=>new(r.InstancesRoot,r.InstallationId,r.ReaderSid,trusted);
    private static string Operator()=>WindowsIdentity.GetCurrent().User?.Value??throw Fail("mfa_rotation_operator_invalid");
    private static byte[] Ring(Guid id,IEnumerable<MfaKeyRingEntry> entries)=>JsonSerializer.SerializeToUtf8Bytes(new{format=MfaKeyRing.RingFormat,formatVersion=1,installationId=id,
        versions=entries.OrderBy(e=>e.Version).Select(e=>new{version=e.Version,state=e.State==MfaKeyState.Active?"active":"retired",
            createdAtUtc=e.CreatedAtUtc.ToUniversalTime().ToString("yyyy-MM-dd'T'HH:mm:ss'Z'",CultureInfo.InvariantCulture)})});
    private static string Hash(byte[] bytes)=>Convert.ToHexStringLower(SHA256.HashData(bytes));
    private static MfaMaintenanceException Fail(string code)=>new(code);
}
