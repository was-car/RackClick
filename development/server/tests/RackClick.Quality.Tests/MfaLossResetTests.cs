using System.Data;
using System.Diagnostics;
using System.Runtime.Versioning;
using System.Security.Cryptography;
using System.Security.Principal;
using System.Text.Json;
using Npgsql;
using RackClick.Server;
using Xunit;

namespace RackClick.Quality.Tests;

// Explicit new native-name PG17 cluster, fixture Windows identity only; no installed service/VM is selected.
[SupportedOSPlatform("windows")]
public sealed class MfaLossResetTests
{
    private static CancellationToken Ct=>TestContext.Current.CancellationToken;
    [Fact]
    public async Task MixedStatesAndAuthoritiesAreArchivedAndOnlyLostFactorsRequireReenrollment()
    {
        using var f=await Fixture.Create();
        var global=await f.Factor(7,"active",true);var pending=await f.Factor(7,"pending");var disabled=await f.Factor(7,"disabled");
        await f.Exec("UPDATE app_user SET active=false WHERE id=@id",("id",disabled));
        var retained=await f.Factor(1,"active");
        var originalRows=await f.Text("SELECT jsonb_agg(to_jsonb(t) ORDER BY user_id)::text FROM public.app_mfa_factor t WHERE key_version=7");
        var accounts=await f.UnchangedAccounts();var retainedBefore=await f.Text("SELECT to_jsonb(t)::text FROM public.app_mfa_factor t WHERE user_id=@id",("id",retained));
        f.Lose(7);var opaque=f.KeyHash(7);await f.Initialize();
        Assert.Equal("awaiting_external_envelope_fenced",(await f.Run("prepare",[7])).Phase);
        Assert.Equal(4,await f.Count("SELECT count(*) FROM public.app_mfa_factor"));Assert.True(File.Exists(f.Fence));
        var envelope=await f.Export();
        try
        {
            Assert.Equal("db_committed_fenced",(await f.Run("apply",envelope:envelope)).Phase);
            Assert.Equal("material_published_verified_fenced",(await f.Run("publish")).Phase);
        }
        finally{CryptographicOperations.ZeroMemory(envelope);}
        Assert.Equal(8,f.Provider.GetActiveKey().Version);
        Assert.Equal(originalRows,await f.Text("SELECT jsonb_agg(factor_row ORDER BY user_id)::text FROM rackclick_private.mfa_loss_factor_archive"));
        Assert.Equal(3,await f.Count("SELECT count(*) FROM app_mfa_user WHERE mfa_required AND enrollment_pending AND revision=5"));
        Assert.Equal(1,await f.Count("SELECT count(*) FROM app_mfa_factor"));
        Assert.Equal(retainedBefore,await f.Text("SELECT to_jsonb(t)::text FROM public.app_mfa_factor t WHERE user_id=@id",("id",retained)));
        Assert.Equal(accounts,await f.UnchangedAccounts());Assert.Equal(opaque,f.KeyHash(7));
        Assert.Equal(1,await f.Count("SELECT count(*) FROM app_session"));
        Assert.Equal(3,await f.Count("SELECT count(*) FROM app_mfa_challenge WHERE consumed_at IS NOT NULL"));
        Assert.Equal(3,await f.Count("SELECT count(*) FROM app_mfa_recovery_code WHERE consumed_at IS NOT NULL"));
        Assert.Equal(1,await f.Count("SELECT count(*) FROM rackclick_private.mfa_loss_operation WHERE mode='loss-reset' AND authority='windows-local'"));
        Assert.True(File.Exists(f.Fence));Assert.Throws<MfaMaintenanceException>(()=>MfaMaintenanceAdmission.ThrowIfFenced(f.Instances,f.Id));
        await f.Authenticate(retained);await f.AssertEnrollmentOnly(global);await f.AssertEnrollmentOnly(pending);
        Assert.Equal("False",await f.Text("SELECT active FROM app_user WHERE id=@id",("id",disabled)));
        Assert.NotEqual(global,pending);Assert.NotEqual(disabled,retained);
        await using var runtime=new NpgsqlConnection(f.RuntimeConnection);await runtime.OpenAsync(Ct);
        foreach(var sql in new[]{"SELECT * FROM rackclick_private.mfa_loss_factor_archive","DELETE FROM rackclick_private.mfa_loss_operation"})
        {await using var denied=new NpgsqlCommand(sql,runtime);Assert.Equal("42501",(await Assert.ThrowsAsync<PostgresException>(()=>denied.ExecuteNonQueryAsync(Ct))).SqlState);}
    }
    [Fact]
    public async Task AllKeyMaterialCanBeLostButKnownRingAndOpaqueZeroByteBlobArePreserved()
    {
        using var f=await Fixture.Create();await f.Factor(1,"active");await f.Factor(7,"disabled");
        f.Lose(1);f.Lose(7,true);var one=f.KeyHash(1);var seven=f.KeyHash(7);await f.Initialize();
        await f.Run("prepare",[1,7]);var envelope=await f.Export();
        try{await f.Run("apply",envelope:envelope);await f.Run("publish");}finally{CryptographicOperations.ZeroMemory(envelope);}
        Assert.Equal(one,f.KeyHash(1));Assert.Equal(seven,f.KeyHash(7));
        Assert.Equal(0,await f.Count("SELECT count(*) FROM app_mfa_factor"));Assert.Equal(2,await f.Count("SELECT count(*) FROM rackclick_private.mfa_loss_factor_archive"));
        var ring=MfaKeyRing.Parse(File.ReadAllBytes(f.RingPath),f.Id);Assert.Single(ring.Entries);Assert.Equal(8,ring.Entries[0].Version);Assert.True(File.Exists(f.Fence));
    }
    [Fact]
    public async Task CommitFailureRollsBackEveryDatabaseEffectAndKeepsCandidateAndFence()
    {
        using var f=await Fixture.Create();await f.Factor(7,"active");f.Lose(7);await f.Initialize();await f.Run("prepare",[7]);
        var before=await f.SecuritySnapshot();
        await f.Exec("CREATE FUNCTION rackclick_private.reject_loss() RETURNS trigger LANGUAGE plpgsql AS $$BEGIN RAISE EXCEPTION 'synthetic'; END$$; CREATE TRIGGER reject_loss BEFORE UPDATE ON rackclick_private.mfa_loss_operation FOR EACH ROW EXECUTE FUNCTION rackclick_private.reject_loss()");
        var envelope=await f.Export();try{await Assert.ThrowsAsync<PostgresException>(()=>f.Run("apply",envelope:envelope));}finally{CryptographicOperations.ZeroMemory(envelope);}
        Assert.Equal(before,await f.SecuritySnapshot());Assert.Equal(0,await f.Count("SELECT count(*) FROM rackclick_private.mfa_loss_operation"));
        Assert.Equal(0,await f.Count("SELECT count(*) FROM rackclick_private.mfa_loss_factor_archive"));Assert.True(File.Exists(f.Fence));
    }
    [Theory][InlineData("after_loss_db_commit")][InlineData("after_loss_key_publish")]
    public async Task InterruptedCommitOrPublicationResumesForwardWithoutRepeatingPolicyRevision(string cut)
    {
        using var f=await Fixture.Create();await f.Factor(7,"active");f.Lose(7);await f.Initialize();await f.Run("prepare",[7]);var envelope=await f.Export();
        try
        {
            if(cut=="after_loss_db_commit")await Assert.ThrowsAsync<SyntheticCut>(()=>f.Run("apply",envelope:envelope,checkpoint:s=>{if(s==cut)throw new SyntheticCut();}));
            else{await f.Run("apply",envelope:envelope);await Assert.ThrowsAsync<SyntheticCut>(()=>f.Run("publish",checkpoint:s=>{if(s==cut)throw new SyntheticCut();}));}
            Assert.True(File.Exists(f.Fence));
            if(cut=="after_loss_db_commit")await f.Run("apply",envelope:envelope);
            await f.Run("publish");await f.Run("publish");
            Assert.Equal(5,await f.Count("SELECT revision FROM app_mfa_user"));Assert.Equal(1,await f.Count("SELECT count(*) FROM rackclick_private.mfa_loss_operation"));
        }
        finally{CryptographicOperations.ZeroMemory(envelope);}
    }
    [Theory][InlineData("policy")][InlineData("user")][InlineData("code")]
    public async Task AnySecurityChangeAfterPlanningStopsBeforeDatabaseCommit(string change)
    {
        using var f=await Fixture.Create();var user=await f.Factor(7,"active");f.Lose(7);await f.Initialize();await f.Run("prepare",[7]);
        await f.Exec(change switch{"policy"=>"UPDATE app_mfa_policy SET enabled=NOT enabled","user"=>"UPDATE app_user SET username=username||'changed' WHERE id=@id",_=>"UPDATE app_mfa_recovery_code SET consumed_at=clock_timestamp()"},("id",user));
        var before=await f.SecuritySnapshot();var envelope=await f.Export();
        try{Assert.Equal("mfa_loss_database_changed",(await Assert.ThrowsAsync<MfaMaintenanceException>(()=>f.Run("apply",envelope:envelope))).Code);}finally{CryptographicOperations.ZeroMemory(envelope);}
        Assert.Equal(before,await f.SecuritySnapshot());Assert.Equal(0,await f.Count("SELECT count(*) FROM rackclick_private.mfa_loss_factor_archive"));
    }
    [Theory][InlineData("readable_lost")][InlineData("retained_corrupt")][InlineData("ring_unknown")]
    public async Task UncertainOrStillRecoverableMaterialNeverExpandsTheDeclaredLoss(string variant)
    {
        using var f=await Fixture.Create();await f.Factor(1,"active");await f.Factor(7,"active");await f.Initialize();
        if(variant!="readable_lost")f.Lose(7);
        if(variant=="retained_corrupt")f.Lose(1);
        if(variant=="ring_unknown")File.WriteAllText(f.RingPath,"{}");
        var before=await f.SecuritySnapshot();await Assert.ThrowsAnyAsync<Exception>(()=>f.Run("prepare",[7]));
        Assert.Equal(before,await f.SecuritySnapshot());Assert.False(File.Exists(f.Fence));
    }
    [Fact]
    public async Task BackupOnlyVersionWithoutMaterialMustBeExplicitlyDeclaredLost()
    {
        using var f=await Fixture.Create();
        var entry=await f.BackupWithVersion(90);await f.Factor(7,"active");f.Lose(7);await f.Initialize([entry]);
        var before=await f.SecuritySnapshot();
        Assert.Equal("mfa_loss_versions_not_declared",(await Assert.ThrowsAsync<MfaMaintenanceException>(()=>f.Run("prepare",[7]))).Code);
        Assert.False(File.Exists(f.Fence));Assert.Equal(before,await f.SecuritySnapshot());
    }
    [Fact]
    public async Task ExplicitlyLostBackupVersionIsRecordedAndNeverReusedOrReportedAsRecoverable()
    {
        using var f=await Fixture.Create();var entry=await f.BackupWithVersion(90);await f.Factor(7,"active");f.Lose(7);await f.Initialize([entry]);
        var backupBefore=Directory.EnumerateFiles(f.Retained,"*",SearchOption.AllDirectories).Order().Select(p=>Convert.ToHexStringLower(SHA256.HashData(File.ReadAllBytes(p)))).ToArray();
        Assert.Equal(91,(await f.Run("prepare",[7,90])).NewVersion);
        using(var store=new WindowsMfaMaintenanceStore(f.Instances,f.Id,f.Reader,f.Trusted))
        using(store.AcquireLock()){var plan=store.ReadLossPlan(f.Operation);Assert.Single(plan.AffectedBackups);Assert.Equal(new[]{7,90},plan.LostVersions);}
        var envelope=await f.Export();try{await f.Run("apply",envelope:envelope);await f.Run("publish");}finally{CryptographicOperations.ZeroMemory(envelope);}
        var active=f.Provider.GetActiveKey();try{Assert.Equal(91,active.Version);}finally{CryptographicOperations.ZeroMemory(active.Key);}
        Assert.Equal(backupBefore,Directory.EnumerateFiles(f.Retained,"*",SearchOption.AllDirectories).Order().Select(p=>Convert.ToHexStringLower(SHA256.HashData(File.ReadAllBytes(p)))).ToArray());
        Assert.True(File.Exists(f.Fence));
    }
    [Fact]
    public async Task EveryNativeEntryRejectsTheObservedStandardTokenBeforeScmOrDatabase()
    {
        var denied=MfaEmergencyRecoveryCommand.AuthorizationFailure();Assert.SkipWhen(denied is null,"Requires an observed non-elevated Windows token; never invoke native mutation from an elevated fixture");
        var request=new MfaMaintenanceRequest("loss-reset","not a connection","invalid-root",Guid.NewGuid(),new(WellKnownSidType.BuiltinUsersSid,null),"",0,Guid.NewGuid(),null);
        foreach(var run in new Func<Task>[]
        {
            ()=>MfaLossResetCoordinator.PrepareAsync(request,"invalid service",[7],Ct),
            ()=>MfaLossResetCoordinator.ExportAsync(request,"invalid service","irrelevant",Ct),
            ()=>MfaLossResetCoordinator.ApplyAsync(request,"invalid service",[],"irrelevant","",Ct),
            ()=>MfaLossResetCoordinator.PublishAsync(request,"invalid service",Ct)
        })Assert.Equal(denied,(await Assert.ThrowsAsync<MfaMaintenanceException>(run)).Code);
    }
    [Fact]
    public async Task ExistingRetirementAndRotationAcceptKnownSchema47WithoutBecomingLossReset()
    {
        using var f=await Fixture.Create();
        // This compatibility case intentionally runs47, not whatever LatestVersion becomes.
        await f.Exec("DROP VIEW public.app_mfa_loss_startup_witness; DELETE FROM public.schema_migration WHERE version=48");
        await f.Factor(1,"active");await f.Initialize();var before=await f.SecuritySnapshot();
        var result=await f.RetireAndPrepareRotation();Assert.Equal("awaiting_external_envelope",result.Phase);Assert.Equal(8,result.NewVersion);
        Assert.Equal(before,await f.SecuritySnapshot());Assert.Equal(0,await f.Count("SELECT count(*) FROM rackclick_private.mfa_loss_operation"));
        Assert.Equal(47,await f.Count("SELECT max(version) FROM schema_migration"));Assert.True(File.Exists(f.Fence));
    }
    [Theory][InlineData("sid")][InlineData("new_version")][InlineData("lost_versions")][InlineData("envelope")]
    public async Task AlteredWitnessMetadataCannotAuthorizePublishing(string field)
    {
        using var f=await Fixture.Create();await f.Factor(7,"active");f.Lose(7);await f.Initialize();await f.Run("prepare",[7]);
        var envelope=await f.Export();try{await f.Run("apply",envelope:envelope);}finally{CryptographicOperations.ZeroMemory(envelope);}
        await f.Exec(field switch{"sid"=>"UPDATE rackclick_private.mfa_loss_operation SET operator_sid='S-1-5-18'","new_version"=>"UPDATE rackclick_private.mfa_loss_operation SET new_version=9","envelope"=>"UPDATE rackclick_private.mfa_loss_operation SET envelope_sha256=repeat('a',64)",_=>"UPDATE rackclick_private.mfa_loss_operation SET lost_versions=ARRAY[2]"});
        await Assert.ThrowsAsync<MfaMaintenanceException>(()=>f.Run("publish"));Assert.Equal(1,f.Provider.GetActiveKey().Version);Assert.True(File.Exists(f.Fence));
    }
    [Fact]
    public async Task WrongEnvelopeRejectsWithoutAffectingDatabase()
    {
        using var f=await Fixture.Create();await f.Factor(7,"active");f.Lose(7);await f.Initialize();await f.Run("prepare",[7]);var before=await f.SecuritySnapshot();
        var envelope=await f.Export();try{envelope[^1]^=1;await Assert.ThrowsAnyAsync<Exception>(()=>f.Run("apply",envelope:envelope));}finally{CryptographicOperations.ZeroMemory(envelope);}
        Assert.Equal(before,await f.SecuritySnapshot());Assert.True(File.Exists(f.Fence));
    }
    [Fact]
    public async Task PhysicallyMissingLostFileIsNotRecreatedAndNewCandidateCannotBeSubstituted()
    {
        using var f=await Fixture.Create();await f.Factor(7,"active");f.RemoveKey(7);await f.Initialize();await f.Run("prepare",[7]);
        var before=await f.SecuritySnapshot();var envelope=await f.Export();
        var candidate=Path.Combine(f.Instances,f.Id.ToString("D"),WindowsMfaMaintenanceStore.ManagementFolderName,f.Operation.ToString("N")+".lc",f.Id.ToString("D"),"mfa-keys",MfaKeyRing.KeyFileName(8));
        File.WriteAllText(candidate,"substituted fixture");
        try{await Assert.ThrowsAnyAsync<Exception>(()=>f.Run("apply",envelope:envelope));}finally{CryptographicOperations.ZeroMemory(envelope);}
        Assert.False(f.KeyExists(7));Assert.Equal(before,await f.SecuritySnapshot());Assert.True(File.Exists(f.Fence));
    }
    private sealed class SyntheticCut:Exception;

    internal sealed class Fixture:IDisposable
    {
        internal Guid Id{get;}=Guid.NewGuid();internal Guid Operation{get;}=Guid.NewGuid();internal Guid House{get;private set;}
        internal string Instances{get;}internal string Retained{get;}internal string CaseRoot{get;}
        internal string RingPath=>Path.Combine(Instances,Id.ToString("D"),"mfa-keys","ring.json");
        internal string Fence=>Path.Combine(Instances,Id.ToString("D"),WindowsMfaMaintenanceStore.FenceFileName);
        internal string OwnerConnection{get;private set;}="";internal string RuntimeConnection{get;private set;}="";
        internal SecurityIdentifier Reader{get;}=new(WellKnownSidType.BuiltinUsersSid,null);
        internal SecurityIdentifier[] Trusted{get;}=[WindowsIdentity.GetCurrent().User!,new(WellKnownSidType.LocalSystemSid,null),new(WellKnownSidType.BuiltinAdministratorsSid,null)];
        internal Dictionary<int,byte[]> Keys{get;}=new(){[1]=RandomNumberGenerator.GetBytes(32),[7]=RandomNumberGenerator.GetBytes(32)};
        private string CatalogHash="";private readonly string EnvelopePassword=Convert.ToHexString(RandomNumberGenerator.GetBytes(24));
        internal WindowsMfaKeyProvider Provider=>new(Instances,Id,Reader,Trusted);
        private Fixture()
        {
            var root=Environment.GetEnvironmentVariable("RACKCLICK_F0902_ROOT");Assert.SkipWhen(string.IsNullOrEmpty(root),"New isolated native-name PG17 fixture required");
            CaseRoot=Path.Combine(root!,Id.ToString("N")[..8]);Directory.CreateDirectory(CaseRoot);Instances=Path.Combine(CaseRoot,"i");Retained=Path.Combine(CaseRoot,"retained");Directory.CreateDirectory(Retained);
            WindowsMfaKeyStoreWriter.CreateStoreFromMaterial(Instances,Id,Reader,Trusted,Ring(Keys.Keys),Keys.Select(k=>(k.Key,k.Value)).ToArray());
        }
        internal static async Task<Fixture> Create()
        {
            var f=new Fixture();var admin=Environment.GetEnvironmentVariable("RACKCLICK_TEST_PG_ADMIN")!;
            string owner="rc_owner_"+f.Id.ToString("N"),runtime="rc_runtime_"+f.Id.ToString("N"),database="rc_db_"+f.Id.ToString("N");
            var password=Convert.ToHexString(RandomNumberGenerator.GetBytes(32));
            await using(var db=new NpgsqlConnection(admin))
            {
                await db.OpenAsync(Ct);
                // Identifiers and hex-only fixture password are generated locally, never external inputs.
                foreach(var sql in new[]{$"CREATE ROLE {owner} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD '{password}'",$"CREATE ROLE {runtime} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD '{password}'",$"CREATE DATABASE {database} OWNER {owner} ENCODING 'UTF8' TEMPLATE template0"})
                {await using var c=new NpgsqlCommand(sql,db);await c.ExecuteNonQueryAsync(Ct);}
            }
            f.OwnerConnection=new NpgsqlConnectionStringBuilder(admin){Database=database,Username=owner,Password=password,Pooling=false,IncludeErrorDetail=false}.ConnectionString;
            f.RuntimeConnection=new NpgsqlConnectionStringBuilder(f.OwnerConnection){Username=runtime}.ConnectionString;
            await using(var source=NpgsqlDataSource.Create(f.OwnerConnection))await new PostgresStore(source).Bootstrap("Synthetic loss-reset laboratory","loss.admin",Convert.ToHexString(RandomNumberGenerator.GetBytes(32)),Ct);
            await f.Exec($"GRANT USAGE ON SCHEMA public TO {runtime}; GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public TO {runtime}; REVOKE CREATE ON SCHEMA public FROM PUBLIC");
            await using(var db=await f.Connect())f.House=(Guid)(await new NpgsqlCommand("SELECT id FROM public.systemhaus",db).ExecuteScalarAsync(Ct))!;
            await f.Exec("INSERT INTO public.app_mfa_policy(systemhaus_id,enabled,grace_days,activated_at) VALUES(@house,true,45,clock_timestamp()-interval '70 days')",("house",f.House));
            await f.Exec("""
                INSERT INTO public.customer(id,systemhaus_id,name) VALUES(@customer,@house,'Synthetic loss sentinel');
                INSERT INTO public.inventory_rack(id,systemhaus_id,customer_id,name,size_u) VALUES(@rack,@house,@customer,'Synthetic retained rack',42);
                INSERT INTO public.inventory_device(id,systemhaus_id,customer_id,kind,rack_id,name,size_u,sort_order) VALUES(@device,@house,@customer,'rackEquipment',@rack,'Synthetic switch',1,0);
                """,("customer",Guid.NewGuid()),("house",f.House),("rack",Guid.NewGuid()),("device",Guid.NewGuid()));
            return f;
        }
        internal async Task<NpgsqlConnection> Connect(){var db=new NpgsqlConnection(OwnerConnection);await db.OpenAsync(Ct);await using var utc=new NpgsqlCommand("SET TimeZone='UTC'",db);await utc.ExecuteNonQueryAsync(Ct);return db;}
        internal async Task<int> Exec(string sql,params (string Name,object Value)[] args){await using var db=await Connect();await using var c=new NpgsqlCommand(sql,db);foreach(var a in args)c.Parameters.AddWithValue(a.Name,a.Value);return await c.ExecuteNonQueryAsync(Ct);}
        internal async Task<string> Text(string sql,params (string Name,object Value)[] args){await using var db=await Connect();await using var c=new NpgsqlCommand(sql,db);foreach(var a in args)c.Parameters.AddWithValue(a.Name,a.Value);return Convert.ToString(await c.ExecuteScalarAsync(Ct))!;}
        internal async Task<long> Count(string sql)=>long.Parse(await Text(sql),System.Globalization.CultureInfo.InvariantCulture);
        internal async Task<Guid> Factor(int version,string state,bool global=false)
        {
            var id=Guid.NewGuid();var secret=RandomNumberGenerator.GetBytes(20);byte[] cipher;
            try{cipher=MfaSecretCipher.Seal(Keys[version],version,secret,House,id);}finally{CryptographicOperations.ZeroMemory(secret);}
            var name="synthetic-"+id.ToString("N");await Exec("""
                INSERT INTO public.app_user(id,systemhaus_id,username,password_hash,created_at) VALUES(@id,@house,@name,@password,clock_timestamp()-interval '70 days');
                INSERT INTO public.app_mfa_factor(systemhaus_id,user_id,state,secret_ciphertext,key_version,last_time_step,failed_attempts) VALUES(@house,@id,@state,@cipher,@version,1234,2);
                INSERT INTO public.app_mfa_user(systemhaus_id,user_id,mfa_required,enrollment_pending,revision,changed_by) VALUES(@house,@id,false,false,4,NULL);
                INSERT INTO public.app_session(token_hash,user_id,csrf_hash,expires_at) VALUES(@token,@id,@csrf,clock_timestamp()+interval '1 hour');
                INSERT INTO public.app_mfa_challenge(token_hash,systemhaus_id,user_id,purpose,csrf_hash,expires_at,policy_revision) VALUES(@token,@house,@id,'verify',@csrf,clock_timestamp()+interval '4 minutes',4);
                INSERT INTO public.app_mfa_recovery_code(systemhaus_id,user_id,code_hash) VALUES(@house,@id,@token);
                """,("id",id),("house",House),("name",name),("password",Secrets.PasswordHash(name,EnvelopePassword)),("state",state),("cipher",cipher),("version",version),("token",Secrets.Digest(Secrets.Token())),("csrf",Secrets.Digest(Secrets.Token())));
            if(global)await Exec("INSERT INTO user_group_member(systemhaus_id,group_id,user_id) SELECT @house,group_id,@id FROM user_group_member WHERE user_id=(SELECT id FROM app_user WHERE username='loss.admin')",("house",House),("id",id));
            return id;
        }
        internal void Lose(int v,bool empty=false)=>File.WriteAllBytes(KeyPath(v),empty?[]:"opaque-corrupt-fixture"u8.ToArray());
        internal void RemoveKey(int v)=>File.Move(KeyPath(v),Path.Combine(CaseRoot,"original-"+v+".private.json"),false);
        internal bool KeyExists(int v)=>File.Exists(KeyPath(v));
        private string KeyPath(int v)=>Path.Combine(Path.GetDirectoryName(RingPath)!,MfaKeyRing.KeyFileName(v));
        internal string KeyHash(int v)=>Hash(File.ReadAllBytes(KeyPath(v)));
        internal byte[] Ring(IEnumerable<int> versions)=>JsonSerializer.SerializeToUtf8Bytes(new{format=MfaKeyRing.RingFormat,formatVersion=1,installationId=Id,versions=versions.Order().Select(v=>new{version=v,state=v==versions.Min()?"active":"retired",createdAtUtc="2026-11-11T00:00:00Z"})});
        internal async Task Initialize(object[]? entries=null)
        {
            var bytes=JsonSerializer.SerializeToUtf8Bytes(new{format="RackClick.MfaBackupCatalog",formatVersion=1,installationId=Id,catalogId=Guid.NewGuid(),operatorSid=WindowsIdentity.GetCurrent().User!.Value,confirmedUtc=DateTime.UtcNow.ToString("O"),coverage="all-retained-roots-declared",roots=new[]{Retained},entries=entries??[]});
            var r=new MfaMaintenanceRequest("catalog-initialize",OwnerConnection,Instances,Id,Reader,"",0,Guid.Empty,bytes);
            CatalogHash=(await MfaMaintenanceCoordinator.RunAsync(r,Trusted,null,Ct)).CatalogSha256;
        }
        private MfaMaintenanceRequest Request=>new("loss-reset",OwnerConnection,Instances,Id,Reader,CatalogHash,0,Operation,null);
        internal Task<MfaLossResetResult> Run(string stage,int[]? lost=null,byte[]? envelope=null,Action<string>? checkpoint=null)=>MfaLossResetCoordinator.RunFixtureAsync(stage,Request,lost??[],Trusted,WindowsIdentity.GetCurrent().User!.Value,envelope,EnvelopePassword,envelope is null?null:Hash(envelope),checkpoint,Ct);
        internal Task<byte[]> Export()=>MfaLossResetCoordinator.ExportFixtureAsync(Request,Trusted,WindowsIdentity.GetCurrent().User!.Value,EnvelopePassword,Ct);
        internal async Task<MfaRotationResult> RetireAndPrepareRotation()
        {
            var r=Request with{Action="retire",Candidate=7,OperationId=Guid.NewGuid()};
            Assert.Equal("mfa_version_retired",(await MfaMaintenanceCoordinator.RunAsync(r,Trusted,null,Ct)).Code);
            return await MfaRotationCoordinator.PrepareAsync(r with{Action="rotate",Candidate=0,OperationId=Guid.NewGuid()},Trusted,null,Ct);
        }
        internal Task<string> SecuritySnapshot()=>Text("SELECT md5(jsonb_build_array((SELECT jsonb_agg(to_jsonb(t) ORDER BY user_id) FROM app_mfa_factor t),(SELECT jsonb_agg(to_jsonb(t) ORDER BY user_id) FROM app_mfa_user t),(SELECT jsonb_agg(to_jsonb(t) ORDER BY id) FROM app_user t),(SELECT jsonb_agg(to_jsonb(t) ORDER BY token_hash) FROM app_session t),(SELECT jsonb_agg(to_jsonb(t) ORDER BY token_hash) FROM app_mfa_challenge t),(SELECT jsonb_agg(to_jsonb(t) ORDER BY user_id) FROM app_mfa_recovery_code t),(SELECT jsonb_agg(to_jsonb(t) ORDER BY systemhaus_id) FROM app_mfa_policy t))::text)");
        internal Task<string> UnchangedAccounts()=>Text("SELECT md5(jsonb_build_array((SELECT jsonb_agg(to_jsonb(t) ORDER BY id) FROM app_user t),(SELECT jsonb_agg(to_jsonb(t) ORDER BY user_id,group_id) FROM user_group_member t),(SELECT jsonb_agg(to_jsonb(t) ORDER BY systemhaus_id) FROM app_mfa_policy t),(SELECT jsonb_agg(to_jsonb(t) ORDER BY id) FROM systemhaus t),(SELECT jsonb_agg(to_jsonb(t) ORDER BY id) FROM customer t),(SELECT jsonb_agg(to_jsonb(t) ORDER BY id) FROM inventory_rack t),(SELECT jsonb_agg(to_jsonb(t) ORDER BY id) FROM inventory_device t))::text)");
        internal async Task AssertEnrollmentOnly(Guid user)
        {
            var name=await Text("SELECT username FROM app_user WHERE id=@id",("id",user));
            await using var source=NpgsqlDataSource.Create(RuntimeConnection);
            var result=await new PostgresStore(source){MfaAvailable=true}.AuthenticateForLogin(name,EnvelopePassword,Ct);
            Assert.Null(result.Session);Assert.NotNull(result.Challenge);Assert.Equal("enroll",result.ChallengePurpose);
        }
        internal async Task Authenticate(Guid user)
        {
            await using var db=await Connect();await using var c=new NpgsqlCommand("SELECT key_version,secret_ciphertext FROM app_mfa_factor WHERE user_id=@id",db);c.Parameters.AddWithValue("id",user);
            await using var row=await c.ExecuteReaderAsync(Ct);Assert.True(await row.ReadAsync(Ct));var version=row.GetInt32(0);var key=Provider.GetKey(version);byte[]? plain=null;
            try{plain=MfaSecretCipher.Open(key,version,row.GetFieldValue<byte[]>(1),House,user);Assert.Equal(20,plain.Length);}finally{CryptographicOperations.ZeroMemory(key);if(plain is not null)CryptographicOperations.ZeroMemory(plain);}
        }
        internal async Task<object> BackupWithVersion(int version)
        {
            Keys.Add(version,RandomNumberGenerator.GetBytes(32));var user=await Factor(version,"active");var backup=Guid.NewGuid();
            var dir=Path.Combine(Retained,backup.ToString("D"));var database=Path.Combine(dir,"database");Directory.CreateDirectory(database);
            var settings=new NpgsqlConnectionStringBuilder(OwnerConnection);var pgpass=Path.Combine(CaseRoot,"backup.pgpass");
            File.WriteAllText(pgpass,$"127.0.0.1:{settings.Port}:{settings.Database}:{settings.Username}:{settings.Password}\n");
            var start=new ProcessStartInfo(Path.Combine(Environment.GetEnvironmentVariable("RACKCLICK_TEST_PG_BIN")!,"pg_dump.exe")){UseShellExecute=false,CreateNoWindow=true,RedirectStandardOutput=true,RedirectStandardError=true};
            foreach(var arg in new[]{"-w","-h","127.0.0.1","-p",settings.Port.ToString(),"-U",settings.Username!,"-d",settings.Database!,"-F","c","--no-owner","--no-acl","-f",Path.Combine(database,"data.dump")})start.ArgumentList.Add(arg);
            foreach(var name in start.Environment.Keys.Where(k=>k.StartsWith("PG",StringComparison.OrdinalIgnoreCase)).ToArray())start.Environment.Remove(name);start.Environment["PGPASSFILE"]=pgpass;
            using(var process=Process.Start(start)!){var output=process.StandardOutput.ReadToEndAsync();var error=process.StandardError.ReadToEndAsync();await process.WaitForExitAsync(Ct);await output;await error;Assert.Equal(0,process.ExitCode);}
            var dump=File.ReadAllBytes(Path.Combine(database,"data.dump"));var manifest=JsonSerializer.SerializeToUtf8Bytes(new{schemaVersion=1,kind="RackClickDatabaseBackup",postgresVersion="17.11",format="custom",dumpFile="data.dump",dumpBytes=dump.Length,dumpSha256=Hash(dump),createdUtc=DateTime.UtcNow.ToString("O")});File.WriteAllBytes(Path.Combine(database,"manifest.json"),manifest);
            using var payload=MfaKeyRecoveryPayload.Serialize(Ring([version]),Id,[(version,Keys[version])]);var envelope=MfaKeyRecoveryEnvelope.Seal(EnvelopePassword,payload.Bytes);
            var inventory=MfaKeyRetention.CreateBackupInventory(backup,MfaKeyRetention.FactorInventory(Id,[new(version,0,1,0)]),MfaKeyRetention.InspectEnvelope(envelope,EnvelopePassword,Id),Hash(manifest),Hash(dump));
            var inventoryBytes=MfaKeyRetention.SerializeBackupInventory(inventory);File.WriteAllBytes(Path.Combine(dir,"mfa-inventory.json"),inventoryBytes);
            var receipt=JsonSerializer.SerializeToUtf8Bytes(new{format="RackClick.MfaBackupInventoryReceipt",formatVersion=1,installationId=Id,backupId=backup,inventorySha256=Hash(inventoryBytes),manifestSha256=Hash(manifest),dumpSha256=Hash(dump),envelopeSha256=Hash(envelope)});CryptographicOperations.ZeroMemory(envelope);
            await Exec("DELETE FROM app_mfa_factor WHERE user_id=@id; DELETE FROM app_mfa_user WHERE user_id=@id; DELETE FROM app_session WHERE user_id=@id; DELETE FROM app_mfa_challenge WHERE user_id=@id; DELETE FROM app_mfa_recovery_code WHERE user_id=@id; DELETE FROM app_user WHERE id=@id",("id",user));
            return new{backupDirectory=dir,receiptBase64=Convert.ToBase64String(receipt),receiptSha256=Hash(receipt)};
        }
        public void Dispose(){foreach(var key in Keys.Values)CryptographicOperations.ZeroMemory(key);/* Private new-lab artifacts retained for independent review; no deletion by supplied paths. */}
        private static string Hash(byte[] bytes)=>Convert.ToHexStringLower(SHA256.HashData(bytes));
    }
}
