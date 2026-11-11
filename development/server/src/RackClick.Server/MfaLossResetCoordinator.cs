using System.Data;
using System.Globalization;
using System.Runtime.Versioning;
using System.Security;
using System.Security.Cryptography;
using System.Security.Principal;
using System.Text.Json;
using Npgsql;

namespace RackClick.Server;

internal sealed record MfaLossResetResult(Guid OperationId,int NewVersion,string Phase,long Factors=0);

// Local maintenance protocol (no HTTP endpoint). Every production entry recaptures native authority.
[SupportedOSPlatform("windows")]
internal static class MfaLossResetCoordinator
{
    internal static Task<MfaLossResetResult> PrepareAsync(MfaMaintenanceRequest request,string serviceName,int[] lost,CancellationToken ct)=>
        RunNative("prepare",request,serviceName,lost,null,null,null,null,ct);
    internal static Task<MfaLossResetResult> ApplyAsync(MfaMaintenanceRequest request,string serviceName,byte[] envelope,string password,string expectedEnvelopeHash,CancellationToken ct)=>
        RunNative("apply",request,serviceName,[],envelope,password,expectedEnvelopeHash,null,ct);
    internal static async Task<MfaLossResetResult> ApplyFromFileAsync(MfaMaintenanceRequest r,string serviceName,SecurityIdentifier custodian,
        string path,string password,string hash,CancellationToken ct)
    {
        var authority=Native();var scmRoot=NativeServiceRoot(r.InstancesRoot,r.InstallationId);
        WindowsMfaMaintenanceService.RequireStopped(serviceName,r.ReaderSid,r.InstallationId,scmRoot);
        byte[] bytes;
        using(var storage=new WindowsMfaMaintenanceStore(r.InstancesRoot,r.InstallationId,r.ReaderSid,authority.Trusted))
        using(storage.AcquireLock())
        {
            var catalog=MfaBackupCatalog.Parse(storage.ReadCatalog(),r.InstallationId,r.ExpectedCatalogHash);
            MfaMaintenanceCoordinator.RequireRootAuthority(catalog,r.ReaderSid,authority.Trusted);
            RequireExternalEnvelopeFolder(Path.GetDirectoryName(path)!,new[]{scmRoot}.Concat(catalog.Roots));
            var reader=new WindowsMfaKeyFileReader(custodian,authority.Trusted.Select(s=>s.Value).ToHashSet(StringComparer.Ordinal));
            reader.RequireSafeFolder(Path.GetDirectoryName(path)!);bytes=reader.ReadValidated(path,1024*1024);
        }
        try{return await ApplyAsync(r,serviceName,bytes,password,hash,ct);}
        finally{CryptographicOperations.ZeroMemory(bytes);}
    }
    internal static Task<MfaLossResetResult> PublishAsync(MfaMaintenanceRequest request,string serviceName,CancellationToken ct)=>
        RunNative("publish",request,serviceName,[],null,null,null,null,ct);
    internal static Task<MfaLossResetResult> CompleteAsync(MfaMaintenanceRequest request,string serviceName,CancellationToken ct)=>
        RunNative("complete",request,serviceName,[],null,null,null,null,ct);
    internal static Task<byte[]> ExportAsync(MfaMaintenanceRequest request,string serviceName,string password,CancellationToken ct)
    {
        var authority=Native();WindowsMfaMaintenanceService.RequireStopped(serviceName,request.ReaderSid,request.InstallationId,NativeServiceRoot(request.InstancesRoot,request.InstallationId));
        return ExportCore(request,authority.Trusted,authority.Sid,password,ct);
    }
    internal static Task<MfaEnvelopeFileReceipt> ExportToFileAsync(MfaMaintenanceRequest r,string serviceName,SecurityIdentifier custodian,
        string password,string folder,string name,CancellationToken ct)
    {
        var authority=Native();var scmRoot=NativeServiceRoot(r.InstancesRoot,r.InstallationId);
        WindowsMfaMaintenanceService.RequireStopped(serviceName,r.ReaderSid,r.InstallationId,scmRoot);
        return Exclusive<MfaEnvelopeFileReceipt>(r,authority.Trusted,async(db,storage)=>
        {
            await using var tx=await db.BeginTransactionAsync(IsolationLevel.ReadCommitted,ct);await MfaLossResetDatabase.LockAsync(db,tx,ct);
            using var backups=Catalog(r,storage,authority.Trusted);RequirePlan(r,storage,authority.Sid);storage.RequireLossMaterial(r.OperationId);
            var catalog=MfaBackupCatalog.Parse(storage.ReadCatalog(),r.InstallationId,r.ExpectedCatalogHash);
            RequireExternalEnvelopeFolder(folder,new[]{scmRoot}.Concat(catalog.Roots));
            var result=WindowsMfaKeyRecoveryFiles.ExportToFile(storage.LossCandidateRoot(r.OperationId),r.InstallationId,r.ReaderSid,
                custodian,authority.Trusted,password,folder,name);
            storage.RequireLossMaterial(r.OperationId);await tx.CommitAsync(ct);return result;
        },ct);
    }
    internal static void RequireExternalEnvelopeFolder(string folder,IEnumerable<string> roots)
    {
        var destination=Path.TrimEndingDirectorySeparator(Path.GetFullPath(folder));
        foreach(var root in roots)
        {
            var excluded=Path.TrimEndingDirectorySeparator(Path.GetFullPath(root));
            var destinationPrefix=Path.EndsInDirectorySeparator(destination)?destination:destination+Path.DirectorySeparatorChar;
            var excludedPrefix=Path.EndsInDirectorySeparator(excluded)?excluded:excluded+Path.DirectorySeparatorChar;
            if(destination.Equals(excluded,StringComparison.OrdinalIgnoreCase)
                ||destination.StartsWith(excludedPrefix,StringComparison.OrdinalIgnoreCase)
                ||excluded.StartsWith(destinationPrefix,StringComparison.OrdinalIgnoreCase))throw Fail("mfa_loss_external_custody_required");
        }
    }
    private static Task<MfaLossResetResult> RunNative(string stage,MfaMaintenanceRequest r,string serviceName,int[] lost,byte[]? envelope,
        string? password,string? hash,Action<string>? checkpoint,CancellationToken ct)
    {var a=Native();WindowsMfaMaintenanceService.RequireStopped(serviceName,r.ReaderSid,r.InstallationId,NativeServiceRoot(r.InstancesRoot,r.InstallationId));return RunCore(stage,r,lost,a.Trusted,a.Sid,envelope,password,hash,checkpoint,ct);}
    internal static string NativeServiceRoot(string securityRoot,Guid installation)
    {
        try
        {
            if(installation==Guid.Empty||!Path.IsPathFullyQualified(securityRoot))throw Fail("mfa_loss_native_layout_invalid");
            var path=Path.TrimEndingDirectorySeparator(Path.GetFullPath(securityRoot));var folder=Directory.GetParent(path);
            if(!string.Equals(Path.GetFileName(path),"security",StringComparison.OrdinalIgnoreCase)||folder?.Name!=installation.ToString("D")||folder.Parent is null)
                throw Fail("mfa_loss_native_layout_invalid");
            return folder.Parent.FullName;
        }
        catch(Exception e)when(e is ArgumentException or NotSupportedException or PathTooLongException){throw Fail("mfa_loss_native_layout_invalid");}
    }
    private static (SecurityIdentifier[] Trusted,string Sid) Native()
    {
        var denied=MfaEmergencyRecoveryCommand.AuthorizationFailure();if(denied is not null)throw new MfaMaintenanceException(denied);
        using var identity=WindowsIdentity.GetCurrent();
        return ([new(WellKnownSidType.LocalSystemSid,null),new(WellKnownSidType.BuiltinAdministratorsSid,null)],identity.User?.Value??throw new SecurityException());
    }
    // Explicit component fixture seam; never registered in DI or selected by configuration/CLI.
    internal static Task<MfaLossResetResult> RunFixtureAsync(string stage,MfaMaintenanceRequest request,int[] lost,
        IReadOnlyCollection<SecurityIdentifier> trusted,string operatorSid,byte[]? envelope,string? password,string? hash,
        Action<string>? checkpoint,CancellationToken ct)=>RunCore(stage,request,lost,trusted,operatorSid,envelope,password,hash,checkpoint,ct);
    internal static Task<byte[]> ExportFixtureAsync(MfaMaintenanceRequest request,IReadOnlyCollection<SecurityIdentifier> trusted,
        string sid,string password,CancellationToken ct)=>ExportCore(request,trusted,sid,password,ct);

    private static Task<MfaLossResetResult> RunCore(string stage,MfaMaintenanceRequest r,int[] lost,IReadOnlyCollection<SecurityIdentifier> trusted,
        string sid,byte[]? envelope,string? password,string? envelopeHash,Action<string>? checkpoint,CancellationToken ct)
    {
        if(stage!="apply")return RunExclusiveCore(stage,r,lost,trusted,sid,null,password,envelopeHash,checkpoint,ct);
        if(envelope is null||envelope.Length is <59 or >1024*1024)throw Fail("mfa_loss_external_envelope_required");
        var owned=envelope.ToArray(); // Hash and authentication use this same bounded, caller-independent snapshot.
        return ApplyOwned();
        async Task<MfaLossResetResult> ApplyOwned()
        {try{return await RunExclusiveCore(stage,r,lost,trusted,sid,owned,password,envelopeHash,checkpoint,ct);}finally{CryptographicOperations.ZeroMemory(owned);}}
    }
    private static Task<MfaLossResetResult> RunExclusiveCore(string stage,MfaMaintenanceRequest r,int[] lost,IReadOnlyCollection<SecurityIdentifier> trusted,
        string sid,byte[]? envelope,string? password,string? envelopeHash,Action<string>? checkpoint,CancellationToken ct)=>
        Exclusive<MfaLossResetResult>(r,trusted,async(db,storage)=>
        {
            storage.Checkpoint=checkpoint;
            await using var tx=await db.BeginTransactionAsync(IsolationLevel.ReadCommitted,ct);await MfaLossResetDatabase.LockAsync(db,tx,ct);
            using var backups=Catalog(r,storage,trusted);
            if(stage=="prepare")
            {
                if(storage.ReadPending() is not null)throw Fail("mfa_maintenance_pending");
                var source=storage.InspectLossSource();
                var plan=await MfaLossResetDatabase.PlanAsync(db,tx,r.InstallationId,r.OperationId,sid,source.Ring,source.FileVersions,
                    storage.HighestRotationVersion(),lost,backups,source.FilesHash,ct);
                var provider=Provider(r.InstancesRoot,r,trusted);var ring=MfaKeyRing.Parse(source.Ring,r.InstallationId);
                RequireLostAndRetained(provider,plan,ring);await AuthenticateRetained(db,tx,provider,plan.LostVersions,ct);
                storage.PrepareLoss(plan);
                var material=new List<(int Version,byte[] Key)>();
                try
                {
                    foreach(var entry in ring.Entries.Where(e=>!plan.LostVersions.Contains(e.Version)))material.Add((entry.Version,provider.GetKey(entry.Version)));
                    material.Add((plan.NewVersion,RandomNumberGenerator.GetBytes(32)));
                    var entries=ring.Entries.Where(e=>!plan.LostVersions.Contains(e.Version)).Select(e=>e with{State=MfaKeyState.Retired})
                        .Append(new MfaKeyRingEntry(plan.NewVersion,MfaKeyState.Active,DateTimeOffset.UtcNow));
                    WindowsMfaKeyStoreWriter.CreateStoreFromMaterial(storage.LossCandidateRoot(r.OperationId),r.InstallationId,r.ReaderSid,trusted,
                        Ring(r.InstallationId,entries),material);
                    var candidate=Provider(storage.LossCandidateRoot(r.OperationId),r,trusted);
                    foreach(var item in material)
                    {var key=candidate.GetKey(item.Version);try{if(!CryptographicOperations.FixedTimeEquals(item.Key,key))throw Fail("mfa_loss_material_mismatch");}finally{CryptographicOperations.ZeroMemory(key);}}
                    storage.RecordLossMaterial(r.OperationId);storage.VerifyLossOriginal(r.OperationId);
                }
                finally{foreach(var item in material)CryptographicOperations.ZeroMemory(item.Key);}
                await tx.CommitAsync(ct);return new(r.OperationId,plan.NewVersion,"awaiting_external_envelope_fenced");
            }
            var saved=RequirePlan(r,storage,sid);
            if(stage=="complete"&&storage.LossReleased(r.OperationId))
            {
                await tx.CommitAsync(ct);
                await MfaRotationStartupGuard.ValidateAsync(db,r.InstancesRoot,r.InstallationId,r.ReaderSid,trusted,Provider(r.InstancesRoot,r,trusted),ct);
                return new(r.OperationId,saved.NewVersion,"data_verified_released",saved.Factors);
            }
            var ready=storage.RequireLossMaterial(r.OperationId);
            if(stage=="apply")
            {
                if(envelope is null||password is null||envelopeHash is null||MfaLossResetDatabase.Hash(envelope)!=envelopeHash)
                    throw Fail("mfa_loss_external_envelope_required");
                VerifyEnvelope(r,storage,trusted,envelope,password);
                storage.PinLossEnvelope(r.OperationId,envelopeHash);
                var previous=await MfaLossResetDatabase.ReadWitnessAsync(db,tx,r.OperationId,ct);
                if(previous is null)storage.VerifyLossOriginal(r.OperationId);
                else
                {
                    RequireWitness(saved,ready,previous,storage.RequireLossEnvelope(r.OperationId));
                    if(await MfaLossResetDatabase.SnapshotAsync(db,tx,ct)!=previous.PostSecurityHash
                        ||await MfaLossResetDatabase.ArchiveHashAsync(db,tx,r.OperationId,ct)!=previous.ArchiveHash)throw Fail("mfa_loss_committed_state_changed");
                }
                var witness=await MfaLossResetDatabase.ApplyAsync(db,tx,saved,envelopeHash,ready.FilesHash,ct);
                checkpoint?.Invoke("before_loss_db_commit");storage.RequireLossMaterial(r.OperationId);
                if(previous is null)storage.VerifyLossOriginal(r.OperationId);
                await tx.CommitAsync(ct);checkpoint?.Invoke("after_loss_db_commit");
                return new(r.OperationId,saved.NewVersion,"db_committed_fenced",witness.Factors);
            }
            if(stage is not ("publish" or "complete"))throw Fail("mfa_loss_stage_invalid");
            var committed=await MfaLossResetDatabase.ReadWitnessAsync(db,tx,r.OperationId,ct)??throw Fail("mfa_loss_witness_missing");
            RequireWitness(saved,ready,committed,storage.RequireLossEnvelope(r.OperationId));
            if(await MfaLossResetDatabase.SnapshotAsync(db,tx,ct)!=committed.PostSecurityHash
                ||await MfaLossResetDatabase.ArchiveHashAsync(db,tx,r.OperationId,ct)!=committed.ArchiveHash)throw Fail("mfa_loss_committed_state_changed");
            storage.PublishLoss(r.OperationId);
            var live=Provider(r.InstancesRoot,r,trusted);var active=live.GetActiveKey();
            try{if(active.Version!=saved.NewVersion||active.Key.Length!=32)throw Fail("mfa_loss_publication_invalid");}finally{CryptographicOperations.ZeroMemory(active.Key);}
            await AuthenticateRetained(db,tx,live,[],ct);
            if(stage=="complete")
            {
                await RequireStartupProjection(db,tx,committed,ct);
                storage.PublishLossStartupReceipt(committed);
            }
            await tx.CommitAsync(ct);
            if(stage=="complete")
            {
                await using var admission=new NpgsqlCommand("SELECT EXISTS(SELECT 1 FROM pg_catalog.pg_locks WHERE pid=pg_backend_pid() AND locktype='advisory' AND classid=81726202 AND mode='ExclusiveLock' AND granted)",db);
                if(await admission.ExecuteScalarAsync(ct) is not true)throw Fail("mfa_maintenance_admission_lost");
                storage.CompleteLoss(r.OperationId);
                return new(r.OperationId,saved.NewVersion,"data_verified_released",committed.Factors);
            }
            return new(r.OperationId,saved.NewVersion,"material_published_verified_fenced",committed.Factors);
        },ct);
    private static Task<byte[]> ExportCore(MfaMaintenanceRequest r,IReadOnlyCollection<SecurityIdentifier> trusted,string sid,string password,CancellationToken ct)=>
        Exclusive<byte[]>(r,trusted,async(db,storage)=>
        {
            await using var tx=await db.BeginTransactionAsync(IsolationLevel.ReadCommitted,ct);await MfaLossResetDatabase.LockAsync(db,tx,ct);
            using var backups=Catalog(r,storage,trusted);RequirePlan(r,storage,sid);storage.RequireLossMaterial(r.OperationId);
            var result=WindowsMfaKeyRecovery.Export(storage.LossCandidateRoot(r.OperationId),r.InstallationId,r.ReaderSid,trusted,password);
            storage.RequireLossMaterial(r.OperationId);await tx.CommitAsync(ct);return result;
        },ct);
    private static async Task RequireStartupProjection(NpgsqlConnection db,NpgsqlTransaction tx,MfaLossResetWitness witness,CancellationToken ct)
    {
        await using(var check=new NpgsqlCommand("SELECT to_regclass('public.app_mfa_loss_startup_witness') IS NOT NULL,(SELECT max(version) FROM public.schema_migration)",db,tx))
        await using(var row=await check.ExecuteReaderAsync(ct))
            if(!await row.ReadAsync(ct)||!row.GetBoolean(0)||row.GetInt32(1)!=48)throw Fail("mfa_loss_startup_projection_missing");
        // Runtime authority is part of readiness: owner access alone is insufficient.
        await using(var access=new NpgsqlCommand("SELECT COALESCE(has_schema_privilege(to_regrole(@role),'public','USAGE') AND has_table_privilege(to_regrole(@role),'public.app_mfa_loss_startup_witness','SELECT'),false)",db,tx))
        {
            access.Parameters.AddWithValue("role","rc_runtime_"+witness.InstallationId.ToString("N"));
            if(await access.ExecuteScalarAsync(ct) is not true)throw Fail("mfa_loss_startup_projection_unreadable");
        }
        var projected=await MfaLossResetDatabase.ReadStartupWitnessAsync(db,tx,witness.OperationId,ct);
        if(projected is null||!JsonSerializer.SerializeToUtf8Bytes(projected).AsSpan().SequenceEqual(JsonSerializer.SerializeToUtf8Bytes(witness)))
            throw Fail("mfa_loss_startup_binding_invalid");
    }
    private static async Task<T> Exclusive<T>(MfaMaintenanceRequest r,IReadOnlyCollection<SecurityIdentifier> trusted,
        Func<NpgsqlConnection,WindowsMfaMaintenanceStore,Task<T>> body,CancellationToken ct)
    {
        if(r.Action!="loss-reset"||r.OperationId==Guid.Empty)throw Fail("mfa_loss_request_invalid");
        await using var db=new NpgsqlConnection(MfaMaintenanceCoordinator.OwnerConnection(r.OwnerConnection,r.InstallationId));await db.OpenAsync(ct);
        await MfaMaintenanceCoordinator.ValidateDatabase(db,r.InstallationId,ct);
        using var storage=new WindowsMfaMaintenanceStore(r.InstancesRoot,r.InstallationId,r.ReaderSid,trusted);using var local=storage.AcquireLock();
        await using var admission=await MfaMaintenanceAdmission.ExclusiveAsync(db,ct);MfaMaintenanceAdmission.RequireNoHostRingLease(r.InstancesRoot,r.InstallationId);
        await using(var others=new NpgsqlCommand("SELECT EXISTS(SELECT 1 FROM pg_stat_activity WHERE datname=current_database() AND backend_type='client backend' AND pid<>pg_backend_pid())",db))
            if(await others.ExecuteScalarAsync(ct) is true)throw Fail("mfa_maintenance_other_clients");
        return await body(db,storage);
    }
    private static MfaBackupCatalogSnapshot Catalog(MfaMaintenanceRequest r,WindowsMfaMaintenanceStore s,IReadOnlyCollection<SecurityIdentifier> trusted)
    {var document=MfaBackupCatalog.Parse(s.ReadCatalog(),r.InstallationId,r.ExpectedCatalogHash);MfaMaintenanceCoordinator.RequireRootAuthority(document,r.ReaderSid,trusted);return MfaBackupCatalog.Open(document);}
    private static MfaLossResetPlan RequirePlan(MfaMaintenanceRequest r,WindowsMfaMaintenanceStore s,string sid)
    {var p=s.ReadLossPlan(r.OperationId);if(p.InstallationId!=r.InstallationId||p.CatalogHash!=r.ExpectedCatalogHash||p.OperatorSid!=sid)throw Fail("mfa_loss_plan_mismatch");return p;}
    private static void RequireWitness(MfaLossResetPlan p,MfaLossMaterial material,MfaLossResetWitness witness,string envelopeHash)
    {MfaLossResetDatabase.RequireWitness(p,material.FilesHash,witness,envelopeHash);}
    private static WindowsMfaKeyProvider Provider(string root,MfaMaintenanceRequest r,IReadOnlyCollection<SecurityIdentifier> trusted)=>new(root,r.InstallationId,r.ReaderSid,trusted);
    private static void RequireLostAndRetained(IMfaKeyProvider provider,MfaLossResetPlan plan,MfaKeyRing ring)
    {
        foreach(var version in plan.LostVersions)
        {
            byte[]? key=null;bool unavailable=false;
            try{key=provider.GetKey(version);}
            catch(MfaKeyRingException e)when(e.Kind is MfaKeyRingErrorKind.MissingFile or MfaKeyRingErrorKind.Corrupt or MfaKeyRingErrorKind.InvalidFormat or MfaKeyRingErrorKind.UnknownVersion){unavailable=true;}
            catch(FileNotFoundException){unavailable=true;}
            finally{if(key is not null)CryptographicOperations.ZeroMemory(key);}
            if(!unavailable)throw Fail("mfa_loss_material_still_available");
        }
        foreach(var entry in ring.Entries.Where(e=>!plan.LostVersions.Contains(e.Version)))
        {var key=provider.GetKey(entry.Version);try{if(key.Length!=32)throw Fail("mfa_loss_material_invalid");}finally{CryptographicOperations.ZeroMemory(key);}}
    }
    private static async Task AuthenticateRetained(NpgsqlConnection db,NpgsqlTransaction tx,IMfaKeyProvider provider,int[] lost,CancellationToken ct)
    {
        await using var query=new NpgsqlCommand("SELECT systemhaus_id,user_id,key_version,CASE WHEN octet_length(secret_ciphertext) BETWEEN 29 AND 16384 THEN secret_ciphertext ELSE NULL END FROM public.app_mfa_factor WHERE NOT(key_version=ANY(@lost)) ORDER BY systemhaus_id,user_id",db,tx);
        query.Parameters.AddWithValue("lost",lost);await using var rows=await query.ExecuteReaderAsync(ct);
        while(await rows.ReadAsync(ct))
        {
            if(rows.IsDBNull(3))throw Fail("mfa_loss_retained_factor_invalid");byte[]? key=null,plain=null;
            try{key=provider.GetKey(rows.GetInt32(2));plain=MfaSecretCipher.Open(key,rows.GetInt32(2),rows.GetFieldValue<byte[]>(3),rows.GetGuid(0),rows.GetGuid(1));if(plain.Length==0)throw Fail("mfa_loss_retained_factor_invalid");}
            finally{if(key is not null)CryptographicOperations.ZeroMemory(key);if(plain is not null)CryptographicOperations.ZeroMemory(plain);}
        }
    }
    private static void VerifyEnvelope(MfaMaintenanceRequest r,WindowsMfaMaintenanceStore storage,IReadOnlyCollection<SecurityIdentifier> trusted,byte[] envelope,string password)
    {
        var plain=MfaKeyRecoveryEnvelope.Open(password,envelope);
        try
        {
            using var content=MfaKeyRecoveryPayload.Deserialize(plain,r.InstallationId);var provider=Provider(storage.LossCandidateRoot(r.OperationId),r,trusted);
            var active=provider.GetActiveKey();try{if(content.Ring.Entries.Single(e=>e.State==MfaKeyState.Active).Version!=active.Version)throw Fail("mfa_loss_envelope_mismatch");}finally{CryptographicOperations.ZeroMemory(active.Key);}
            if(!content.Ring.Entries.SequenceEqual(MfaKeyRing.Parse(storage.ReadLossCandidateRing(r.OperationId),r.InstallationId).Entries))throw Fail("mfa_loss_envelope_mismatch");
            foreach(var entry in content.Ring.Entries)
            {var key=provider.GetKey(entry.Version);try{if(!CryptographicOperations.FixedTimeEquals(key,content.KeyFor(entry.Version)))throw Fail("mfa_loss_envelope_mismatch");}finally{CryptographicOperations.ZeroMemory(key);}}
        }
        finally{CryptographicOperations.ZeroMemory(plain);}
    }
    private static byte[] Ring(Guid id,IEnumerable<MfaKeyRingEntry> entries)=>JsonSerializer.SerializeToUtf8Bytes(new{format=MfaKeyRing.RingFormat,formatVersion=1,installationId=id,
        versions=entries.OrderBy(e=>e.Version).Select(e=>new{version=e.Version,state=e.State==MfaKeyState.Active?"active":"retired",createdAtUtc=e.CreatedAtUtc.ToUniversalTime().ToString("yyyy-MM-dd'T'HH:mm:ss'Z'",CultureInfo.InvariantCulture)})});
    private static MfaMaintenanceException Fail(string code)=>new(code);
}
