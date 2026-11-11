using System.Data;
using System.Globalization;
using System.Runtime.Versioning;
using System.Security.Cryptography;
using System.Security.Principal;
using System.Security.AccessControl;
using System.Text.Json;
using Npgsql;

namespace RackClick.Server;

internal sealed record MfaMaintenanceRequest(string Action,string OwnerConnection,string InstancesRoot,Guid InstallationId,
    SecurityIdentifier ReaderSid,string ExpectedCatalogHash,int Candidate,Guid OperationId,byte[]? Catalog)
{
    public override string ToString()=>"MfaMaintenanceRequest(redacted)";
}
internal sealed record MfaMaintenanceResult(string Code,Guid OperationId,string CatalogSha256,int? RetiredVersion,
    bool EncryptedMaterialPreserved=true);

// Local, offline logical retirement. No factor/session/user/DDL mutation and no cryptographic erasure.
[SupportedOSPlatform("windows")]
internal static class MfaMaintenanceCoordinator
{
    internal static async Task<MfaMaintenanceResult> RunAsync(MfaMaintenanceRequest request,
        IReadOnlyCollection<SecurityIdentifier> trusted,Action<string>? checkpoint,CancellationToken ct)
    {
        var connectionString=OwnerConnection(request.OwnerConnection,request.InstallationId);
        await using var connection=new NpgsqlConnection(connectionString);
        await connection.OpenAsync(ct);
        await ValidateDatabase(connection,request.InstallationId,ct);
        using var storage=new WindowsMfaMaintenanceStore(request.InstancesRoot,request.InstallationId,request.ReaderSid,trusted){Checkpoint=checkpoint};
        using var local=storage.AcquireLock();
        await using var admission=await MfaMaintenanceAdmission.ExclusiveAsync(connection,ct);
        MfaMaintenanceAdmission.RequireNoHostRingLease(request.InstancesRoot,request.InstallationId);
        await using(var otherClients=new NpgsqlCommand("SELECT EXISTS(SELECT 1 FROM pg_catalog.pg_stat_activity WHERE datname=current_database() AND backend_type='client backend' AND pid<>pg_catalog.pg_backend_pid())",connection))
            if(await otherClients.ExecuteScalarAsync(ct) is true)throw Fail("mfa_maintenance_other_clients");
        await using var transaction=await connection.BeginTransactionAsync(IsolationLevel.ReadCommitted,ct);
        await using(var limits=new NpgsqlCommand("SET LOCAL lock_timeout='5s'; SET LOCAL statement_timeout='30s'",connection,transaction))
            await limits.ExecuteNonQueryAsync(ct);
        // Blocks inserts/updates/deletes and new pg_dump readers; counts are taken only after this lock is granted.
        await using(var tableLock=new NpgsqlCommand("LOCK TABLE public.app_mfa_factor IN ACCESS EXCLUSIVE MODE",connection,transaction))
            await tableLock.ExecuteNonQueryAsync(ct);
        var pending=storage.ReadPending();
        if(pending is not null && request.Action!="resume")throw Fail("mfa_maintenance_pending");
        if(request.Action is "catalog-initialize" or "catalog-refresh")
        {
            if(request.Catalog is null)throw Fail("mfa_maintenance_input_invalid");
            var digest=Hash(request.Catalog);
            var document=MfaBackupCatalog.Parse(request.Catalog,request.InstallationId,digest);
            RequireRootAuthority(document,request.ReaderSid,trusted);
            using var identity=WindowsIdentity.GetCurrent();
            if(document.OperatorSid!=identity.User?.Value || document.ConfirmedUtc>DateTimeOffset.UtcNow.AddMinutes(1))
                throw Fail("mfa_catalog_authority_mismatch");
            using var verified=MfaBackupCatalog.Open(document);
            if(request.Action=="catalog-initialize")storage.CreateCatalog(request.Catalog);
            else
            {
                var previous=MfaBackupCatalog.Parse(storage.ReadCatalog(),request.InstallationId,request.ExpectedCatalogHash);
                RequireMonotonic(previous,document);
                storage.ReplaceCatalog(request.Catalog,request.ExpectedCatalogHash);
            }
            await transaction.CommitAsync(ct);
            return new(request.Action=="catalog-initialize"?"mfa_catalog_initialized":"mfa_catalog_refreshed",Guid.Empty,digest,null);
        }
        var catalog=MfaBackupCatalog.Parse(storage.ReadCatalog(),request.InstallationId,request.ExpectedCatalogHash);
        RequireRootAuthority(catalog,request.ReaderSid,trusted);
        using var backups=MfaBackupCatalog.Open(catalog);
        var factors=await MfaFactorKeyInventoryReader.ReadForMaintenanceAsync(connection,transaction,request.InstallationId,ct);
        var provider=new WindowsMfaKeyProvider(request.InstancesRoot,request.InstallationId,request.ReaderSid,trusted);
        var current=storage.ReadRing();
        if(request.Action=="resume" && pending is null)
        {
            ValidateMaterial(current,request.InstallationId,provider,factors,backups.Backups);
            await AuthenticateFactors(connection,transaction,provider,ct);
            storage.Complete(request.OperationId);
            await transaction.CommitAsync(ct);
            return new("mfa_retirement_already_verified",request.OperationId,catalog.Digest,null);
        }
        if(request.Action=="check")
        {
            ValidateMaterial(current,request.InstallationId,provider,factors,backups.Backups);
            await AuthenticateFactors(connection,transaction,provider,ct);
            await transaction.CommitAsync(ct);
            return new("mfa_catalog_and_material_verified",pending?.OperationId??Guid.Empty,catalog.Digest,null);
        }
        byte[] original,final;
        int candidate;
        Guid operation;
        if(request.Action=="retire")
        {
            if(request.OperationId==Guid.Empty)throw Fail("mfa_maintenance_input_invalid");
            original=current;candidate=request.Candidate;operation=request.OperationId;
            RequireUnreferenced(original,request.InstallationId,factors,backups.Backups,candidate);
            ValidateMaterial(original,request.InstallationId,provider,factors,backups.Backups);
            await AuthenticateFactors(connection,transaction,provider,ct);
            final=WithoutVersion(original,request.InstallationId,candidate);
            storage.Prepare(operation,candidate,original,final,catalog.Digest);
        }
        else if(request.Action=="resume")
        {
            if(pending is null || pending.OperationId!=request.OperationId || pending.CatalogHash!=catalog.Digest)
                throw Fail("mfa_maintenance_operation_mismatch");
            original=pending.OriginalRing;final=pending.FinalRing;candidate=pending.Candidate;operation=pending.OperationId;
            RequireUnreferenced(original,request.InstallationId,factors,backups.Backups,candidate);
            if(Hash(current)!=Hash(original) && Hash(current)!=Hash(final))throw Fail("mfa_maintenance_ring_changed");
        }
        else throw Fail("mfa_maintenance_input_invalid");
        // Recensus and filesystem rescan under the same SQL/local exclusions immediately before publication.
        var fresh=await MfaFactorKeyInventoryReader.ReadForMaintenanceAsync(connection,transaction,request.InstallationId,ct);
        using(var rescan=MfaBackupCatalog.Open(catalog))
            RequireUnreferenced(original,request.InstallationId,fresh,rescan.Backups,candidate);
        ct.ThrowIfCancellationRequested();
        if(Hash(storage.ReadRing())==Hash(original))storage.Publish(operation);
        if(Hash(storage.ReadRing())!=Hash(final))throw Fail("mfa_maintenance_publication_invalid");
        using(var rescan=MfaBackupCatalog.Open(catalog))
            ValidateMaterial(final,request.InstallationId,provider,fresh,rescan.Backups);
        await AuthenticateFactors(connection,transaction,provider,ct);
        // Hold table/local/advisory exclusion through fence release. No DB rows were mutated by this operation.
        storage.Complete(operation);
        await transaction.CommitAsync(ct);
        return new("mfa_version_retired",operation,catalog.Digest,candidate);
    }

    private static void RequireMonotonic(MfaBackupCatalogDocument previous,MfaBackupCatalogDocument next)
    {
        if(next.CatalogId==previous.CatalogId || next.ConfirmedUtc<previous.ConfirmedUtc
            || previous.Roots.Any(root=>!next.Roots.Contains(root,StringComparer.OrdinalIgnoreCase))
            || previous.Entries.Any(entry=>!next.Entries.Any(item=>string.Equals(item.BackupDirectory,entry.BackupDirectory,StringComparison.OrdinalIgnoreCase)
                && item.ReceiptSha256==entry.ReceiptSha256 && item.ReceiptBase64==entry.ReceiptBase64)))
            throw Fail("mfa_catalog_history_cannot_be_removed");
    }

    internal static void RequireRootAuthority(MfaBackupCatalogDocument catalog,SecurityIdentifier reader,IReadOnlyCollection<SecurityIdentifier> trusted)
    {
        using var identity=WindowsIdentity.GetCurrent();
        var allowed=trusted.Select(s=>s.Value).Append(reader.Value).Append(identity.User!.Value).ToHashSet(StringComparer.Ordinal);
        foreach(var root in catalog.Roots)
        {
            if((File.GetAttributes(root)&FileAttributes.ReparsePoint)!=0)throw Fail("mfa_catalog_root_authority_invalid");
            var acl=new DirectorySecurity(root,AccessControlSections.Owner|AccessControlSections.Access);
            var owner=acl.GetOwner(typeof(SecurityIdentifier));
            if(owner is null || !allowed.Contains(owner.Value))throw Fail("mfa_catalog_root_authority_invalid");
            var descriptor=new RawSecurityDescriptor(acl.GetSecurityDescriptorBinaryForm(),0);
            if(descriptor.DiscretionaryAcl is null)throw Fail("mfa_catalog_root_authority_invalid");
            foreach(var ace in descriptor.DiscretionaryAcl)
            {
                if(ace.AceType==AceType.AccessDenied)continue;
                if(ace.AceType!=AceType.AccessAllowed || ace is not CommonAce grant || !allowed.Contains(grant.SecurityIdentifier.Value))
                    throw Fail("mfa_catalog_root_authority_invalid");
            }
        }
    }

    private static void RequireUnreferenced(byte[] ring,Guid id,MfaFactorVersionInventory factors,
        IEnumerable<MfaBackupKeyInventory> backups,int candidate)
    {
        var decision=MfaKeyRetention.EvaluateCandidate(ring,id,factors,backups,true,candidate);
        if(decision!=MfaKeyRetentionDecision.CandidateUnreferenced)
            throw Fail(decision switch
            {
                MfaKeyRetentionDecision.ActiveVersion=>"mfa_retirement_active_version",
                MfaKeyRetentionDecision.FactorReferenced=>"mfa_retirement_factor_referenced",
                MfaKeyRetentionDecision.BackupReferenced=>"mfa_retirement_backup_referenced",
                MfaKeyRetentionDecision.UnknownVersion=>"mfa_retirement_unknown_version",
                _=>"mfa_retirement_dependencies_invalid"
            });
    }

    internal static void ValidateMaterial(byte[] bytes,Guid id,IMfaKeyProvider provider,MfaFactorVersionInventory factors,
        IEnumerable<MfaBackupKeyInventory> backups)
    {
        var ring=MfaKeyRing.Parse(bytes,id);var versions=ring.Entries.Select(e=>e.Version).ToHashSet();
        if(factors.Entries.Any(e=>(e.Pending+e.Active+e.Disabled)>0 && !versions.Contains(e.Version))
            || backups.Any(b=>b.RequiredVersions.Any(v=>!versions.Contains(v))))throw Fail("mfa_retirement_dependencies_invalid");
        foreach(var version in versions)
        {
            byte[]? key=null;
            try{key=provider.GetKey(version);if(key.Length!=32)throw Fail("mfa_retirement_material_invalid");}
            finally{if(key is not null)CryptographicOperations.ZeroMemory(key);}
        }
    }

    private static byte[] WithoutVersion(byte[] bytes,Guid id,int candidate)
    {
        var ring=MfaKeyRing.Parse(bytes,id);
        return JsonSerializer.SerializeToUtf8Bytes(new{format=MfaKeyRing.RingFormat,formatVersion=1,installationId=id,
            versions=ring.Entries.Where(e=>e.Version!=candidate).OrderBy(e=>e.Version).Select(e=>new{version=e.Version,
                state=e.State==MfaKeyState.Active?"active":"retired",createdAtUtc=e.CreatedAtUtc.ToUniversalTime().ToString("yyyy-MM-dd'T'HH:mm:ss'Z'",CultureInfo.InvariantCulture)})});
    }

    internal static async Task AuthenticateFactors(NpgsqlConnection connection,NpgsqlTransaction transaction,IMfaKeyProvider provider,CancellationToken ct)
    {
        await using var command=new NpgsqlCommand("SELECT systemhaus_id,user_id,key_version,secret_ciphertext FROM public.app_mfa_factor ORDER BY systemhaus_id,user_id",connection,transaction);
        await using var rows=await command.ExecuteReaderAsync(ct);
        while(await rows.ReadAsync(ct))
        {
            byte[]? key=null;byte[]? plaintext=null;
            try
            {
                key=provider.GetKey(rows.GetInt32(2));
                plaintext=MfaSecretCipher.Open(key,rows.GetInt32(2),rows.GetFieldValue<byte[]>(3),rows.GetGuid(0),rows.GetGuid(1));
                if(plaintext.Length==0)throw Fail("mfa_retirement_material_invalid");
            }
            finally
            {
                if(plaintext is not null)CryptographicOperations.ZeroMemory(plaintext);
                if(key is not null)CryptographicOperations.ZeroMemory(key);
            }
        }
    }

    internal static string OwnerConnection(string input,Guid id)
    {
        NpgsqlConnectionStringBuilder value;
        try{value=new(input);}catch(ArgumentException){throw Fail("mfa_maintenance_connection_invalid");}
        if(id==Guid.Empty || value.Host!="127.0.0.1" || value.Database!="rc_db_"+id.ToString("N") || value.Username!="rc_owner_"+id.ToString("N")
            || string.IsNullOrEmpty(value.Password) || !string.IsNullOrEmpty(value.Options) || !string.IsNullOrEmpty(value.SearchPath)
            || !string.IsNullOrEmpty(value.Passfile))throw Fail("mfa_maintenance_connection_invalid");
        value.Pooling=false;value.Multiplexing=false;value.Enlist=false;value.IncludeErrorDetail=false;value.LogParameters=false;
        value.SslMode=SslMode.Disable;value.GssEncryptionMode=GssEncryptionMode.Disable;
        value.Options="-c default_transaction_read_only=off";value.SearchPath="pg_catalog,public";
        value.Timeout=10;value.CommandTimeout=30;value.ApplicationName="RackClick.MfaMaintenance";
        return value.ConnectionString;
    }

    internal static async Task ValidateDatabase(NpgsqlConnection db,Guid id,CancellationToken ct)
    {
        await using(var command=new NpgsqlCommand("""
            SELECT current_database(),current_user,session_user,pg_catalog.pg_get_userbyid(d.datdba),
                pg_catalog.shobj_description(d.oid,'pg_database'),current_setting('server_version_num'),
                r.rolsuper,r.rolcreatedb,r.rolcreaterole,r.rolreplication,r.rolbypassrls
            FROM pg_catalog.pg_database d JOIN pg_catalog.pg_roles r ON r.rolname=current_user WHERE d.datname=current_database()
            """,db))
        await using(var row=await command.ExecuteReaderAsync(ct))
            if(!await row.ReadAsync(ct) || row.GetString(0)!="rc_db_"+id.ToString("N")
                || Enumerable.Range(1,3).Any(i=>row.GetString(i)!="rc_owner_"+id.ToString("N")) || !row.IsDBNull(4)
                || row.GetString(5)!="170011" || Enumerable.Range(6,5).Any(row.GetBoolean))throw Fail("mfa_maintenance_database_rejected");
        await using var history=new NpgsqlCommand("SELECT version FROM public.schema_migration ORDER BY version",db);
        await using var rows=await history.ExecuteReaderAsync(ct);
        for(var version=1;version<=45;version++)if(!await rows.ReadAsync(ct) || rows.GetInt32(0)!=version)throw Fail("mfa_maintenance_schema_rejected");
        // Schema45 remains valid for retirement; only the explicitly known contiguous additions are admitted.
        int next=46;
        while(await rows.ReadAsync(ct))
            if(rows.GetInt32(0)!=next++ || next>49)throw Fail("mfa_maintenance_schema_rejected");
    }
    private static string Hash(byte[] bytes)=>Convert.ToHexStringLower(SHA256.HashData(bytes));
    private static MfaMaintenanceException Fail(string code)=>new(code);
}
