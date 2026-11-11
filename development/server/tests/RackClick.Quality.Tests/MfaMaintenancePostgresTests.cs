using System.Diagnostics;
using System.Runtime.Versioning;
using System.Security.AccessControl;
using System.Security.Cryptography;
using System.Security.Principal;
using System.Text.Json;
using Npgsql;
using RackClick.Server;
using Xunit;

namespace RackClick.Quality.Tests;

[SupportedOSPlatform("windows")]
public sealed class MfaMaintenancePostgresTests
{
    public static bool Available=>!string.IsNullOrEmpty(Environment.GetEnvironmentVariable("RACKCLICK_F0602_MAINT_CONTEXT"));
    private const string NeedLab="Requires a caller-created isolated PG17 native-name maintenance fixture";

    [Fact(Skip=NeedLab,SkipUnless=nameof(Available))]
    public async Task UnreferencedVersionIsRetiredAndSecurityRowsAndEveryKeyFileArePreserved()
    {
        using var f=new Fixture();var user=await f.AddFactor(1,"active");var catalog=await f.Initialize();
        var before=await f.Fingerprint();var keys=f.KeyHashes();var operation=Guid.NewGuid();
        var result=await f.Run("retire",catalog,2,operation);
        Assert.Equal("mfa_version_retired",result.Code);Assert.True(result.EncryptedMaterialPreserved);
        var error=Assert.Throws<MfaKeyRingException>(()=>f.Provider.GetKey(2));Assert.Equal(MfaKeyRingErrorKind.UnknownVersion,error.Kind);
        var active=f.Provider.GetActiveKey();try{Assert.Equal(1,active.Version);Assert.True(CryptographicOperations.FixedTimeEquals(active.Key,f.Keys[1]));}finally{CryptographicOperations.ZeroMemory(active.Key);}
        Assert.Equal(before,await f.Fingerprint());Assert.Equal(keys,f.KeyHashes());await f.Authenticate(user);
        Assert.False(File.Exists(f.Fence));
        Assert.Equal("mfa_retirement_already_verified",(await f.Run("resume",catalog,0,operation)).Code);
    }

    [Theory(Skip=NeedLab,SkipUnless=nameof(Available))]
    [InlineData("pending")][InlineData("active")][InlineData("disabled")]
    public async Task AnyPersistedFactorStateKeepsItsVersion(string state)
    {
        using var f=new Fixture();await f.AddFactor(2,state);var catalog=await f.Initialize();var before=await f.Fingerprint();
        var error=await Assert.ThrowsAsync<MfaMaintenanceException>(()=>f.Run("retire",catalog,2,Guid.NewGuid()));
        Assert.Equal("mfa_retirement_factor_referenced",error.Code);Assert.Equal(before,await f.Fingerprint());Assert.False(File.Exists(f.Fence));
    }

    [Fact(Skip=NeedLab,SkipUnless=nameof(Available))]
    public async Task ActiveVersionCanNeverBeRetired()
    {
        using var f=new Fixture();var catalog=await f.Initialize();
        Assert.Equal("mfa_retirement_active_version",(await Assert.ThrowsAsync<MfaMaintenanceException>(()=>f.Run("retire",catalog,1,Guid.NewGuid()))).Code);
        Assert.False(File.Exists(f.Fence));
    }

    [Fact(Skip=NeedLab,SkipUnless=nameof(Available))]
    public async Task UncoordinatedThirdPartyAccessToRetainedRootBlocksRetirement()
    {
        using var f=new Fixture();var catalog=await f.Initialize();
        var directory=new DirectoryInfo(f.Retained);var original=directory.GetAccessControl();var changed=directory.GetAccessControl();
        changed.AddAccessRule(new FileSystemAccessRule(new SecurityIdentifier(WellKnownSidType.WorldSid,null),FileSystemRights.WriteData,AccessControlType.Allow));
        directory.SetAccessControl(changed);
        try{Assert.Equal("mfa_catalog_root_authority_invalid",(await Assert.ThrowsAsync<MfaMaintenanceException>(()=>f.Run("retire",catalog,2,Guid.NewGuid()))).Code);Assert.False(File.Exists(f.Fence));}
        finally{directory.SetAccessControl(original);}
    }

    [Theory(Skip=NeedLab,SkipUnless=nameof(Available))]
    [InlineData(false)][InlineData(true)]
    public async Task AuthenticationOrAadFailureStopsBeforeFenceAndPreservesTheObservedRows(bool wrongUser)
    {
        using var f=new Fixture();var first=await f.AddFactor(1,"active");var second=await f.AddFactor(1,"disabled");var catalog=await f.Initialize();
        await using(var connection=await f.Connect())
        await using(var corrupt=new NpgsqlCommand(wrongUser
            ?"UPDATE public.app_mfa_factor SET secret_ciphertext=(SELECT secret_ciphertext FROM public.app_mfa_factor WHERE user_id=@other) WHERE user_id=@id"
            :"UPDATE public.app_mfa_factor SET secret_ciphertext=set_byte(secret_ciphertext,12,get_byte(secret_ciphertext,12)#1) WHERE user_id=@id",connection))
        {corrupt.Parameters.AddWithValue("id",first);corrupt.Parameters.AddWithValue("other",second);await corrupt.ExecuteNonQueryAsync(TestContext.Current.CancellationToken);}
        var before=await f.Fingerprint();var keys=f.KeyHashes();
        await Assert.ThrowsAnyAsync<CryptographicException>(()=>f.Run("retire",catalog,2,Guid.NewGuid()));
        Assert.Equal(before,await f.Fingerprint());Assert.Equal(keys,f.KeyHashes());Assert.False(File.Exists(f.Fence));
    }

    [Fact(Skip=NeedLab,SkipUnless=nameof(Available))]
    public async Task NewOrLegacyBackupBlocksUntilAppendOnlyCatalogueRefreshAndThenPinsItsRequiredKey()
    {
        using var f=new Fixture();var original=await f.Initialize();
        var user=await f.AddFactor(2,"active");var entry=await f.CreateBackup(2);await f.RemoveUser(user);
        await Assert.ThrowsAsync<MfaBackupCatalogException>(()=>f.Run("retire",original,2,Guid.NewGuid()));
        var next=f.Catalog([entry]);var refreshed=await f.Run("catalog-refresh",original,catalog:next);
        Assert.Equal("mfa_catalog_refreshed",refreshed.Code);
        Assert.NotEqual(original,refreshed.CatalogSha256);
        Assert.Equal("mfa_retirement_backup_referenced",(await Assert.ThrowsAsync<MfaMaintenanceException>(()=>f.Run("retire",refreshed.CatalogSha256,2,Guid.NewGuid()))).Code);
        Assert.False(File.Exists(f.Fence));
        var other=Path.Combine(f.CaseRoot,"other-retained");Directory.CreateDirectory(other);
        var dropped=f.Catalog([],other);
        Assert.Equal("mfa_catalog_history_cannot_be_removed",(await Assert.ThrowsAsync<MfaMaintenanceException>(()=>f.Run("catalog-refresh",refreshed.CatalogSha256,catalog:dropped))).Code);
        Assert.Equal("mfa_catalog_and_material_verified",(await f.Run("check",refreshed.CatalogSha256)).Code);
    }

    [Theory(Skip=NeedLab,SkipUnless=nameof(Available))]
    [InlineData("fence_created")][InlineData("before_publish")][InlineData("after_publish")][InlineData("before_complete")]
    public async Task InterruptedPublicationRemainsFencedAndResumesFromObservedMaterial(string cut)
    {
        using var f=new Fixture();await f.AddFactor(1,"active");var catalog=await f.Initialize();var before=await f.Fingerprint();var operation=Guid.NewGuid();
        await Assert.ThrowsAsync<SyntheticCut>(()=>f.Run("retire",catalog,2,operation,checkpoint:phase=>{if(phase==cut)throw new SyntheticCut();}));
        Assert.Throws<MfaMaintenanceException>(()=>MfaMaintenanceAdmission.ThrowIfFenced(f.Instances,f.Installation));
        Assert.Equal(before,await f.Fingerprint());
        Assert.Equal("mfa_version_retired",(await f.Run("resume",catalog,0,operation)).Code);
        Assert.False(File.Exists(f.Fence));Assert.Equal(before,await f.Fingerprint());
        Assert.Equal(MfaKeyRingErrorKind.UnknownVersion,Assert.Throws<MfaKeyRingException>(()=>f.Provider.GetKey(2)).Kind);
        Assert.Equal("mfa_retirement_already_verified",(await f.Run("resume",catalog,0,operation)).Code);
    }

    [Fact(Skip=NeedLab,SkipUnless=nameof(Available))]
    public async Task DatabaseLeaseAndPhysicalHostLeasePreventMaintenanceEvenWhenPgSessionDies()
    {
        using var f=new Fixture();var catalog=await f.Initialize();
        await using var host=await f.Connect();await using var shared=await MfaMaintenanceAdmission.SharedAsync(host,TestContext.Current.CancellationToken);
        Assert.Equal("mfa_maintenance_busy",(await Assert.ThrowsAsync<MfaMaintenanceException>(()=>f.Run("retire",catalog,2,Guid.NewGuid()))).Code);
        using(var ring=MfaMaintenanceAdmission.HoldHostRing(f.Instances,f.Installation))
        {
            var pid=Convert.ToInt32(await new NpgsqlCommand("SELECT pg_backend_pid()",host).ExecuteScalarAsync(TestContext.Current.CancellationToken));
            await using(var killer=await f.Connect())
            await using(var kill=new NpgsqlCommand("SELECT pg_terminate_backend(@pid)",killer))
            {kill.Parameters.AddWithValue("pid",pid);Assert.True((bool)(await kill.ExecuteScalarAsync(TestContext.Current.CancellationToken))!);}
            var stopped=false;using var timeout=new CancellationTokenSource(TimeSpan.FromSeconds(5));
            await shared.MonitorAsync(()=>stopped=true,timeout.Token);Assert.True(stopped);Assert.False(shared.IsHealthy);
            Assert.Equal("mfa_maintenance_host_still_running",(await Assert.ThrowsAsync<MfaMaintenanceException>(()=>f.Run("retire",catalog,2,Guid.NewGuid()))).Code);
        }
        Assert.Equal("mfa_version_retired",(await f.Run("retire",catalog,2,Guid.NewGuid())).Code);
    }

    [Fact(Skip=NeedLab,SkipUnless=nameof(Available))]
    public async Task AccessExclusiveLockBlocksAConcurrentWriterAndSharedBackupAdmissionIsRejected()
    {
        using var f=new Fixture();var catalog=await f.Initialize();Task? writer=null;
        await f.Run("retire",catalog,2,Guid.NewGuid(),checkpoint:phase=>
        {
            if(phase!="before_publish")return;
            using(var connection=f.Connect().GetAwaiter().GetResult())
            {
                var rejected=Assert.ThrowsAsync<MfaMaintenanceException>(async()=>{await using var lease=await MfaMaintenanceAdmission.SharedAsync(connection,TestContext.Current.CancellationToken);}).GetAwaiter().GetResult();
                Assert.Equal("mfa_maintenance_busy",rejected.Code);
            }
            var started=new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
            writer=Task.Run(async()=>
            {
                await using var connection=await f.Connect();await using var tx=await connection.BeginTransactionAsync(TestContext.Current.CancellationToken);
                await using var insert=new NpgsqlCommand("LOCK TABLE public.app_mfa_factor IN ROW EXCLUSIVE MODE",connection,tx);
                started.SetResult();await insert.ExecuteNonQueryAsync(TestContext.Current.CancellationToken);await tx.RollbackAsync(TestContext.Current.CancellationToken);
            },TestContext.Current.CancellationToken);
            started.Task.Wait(TimeSpan.FromSeconds(5),TestContext.Current.CancellationToken);Assert.False(writer.Wait(TimeSpan.FromMilliseconds(150),TestContext.Current.CancellationToken));
        });
        Assert.NotNull(writer);await writer.WaitAsync(TimeSpan.FromSeconds(5),TestContext.Current.CancellationToken);
    }

    [Fact(Skip=NeedLab,SkipUnless=nameof(Available))]
    public async Task MaintenanceCensusWithoutTheActualTableLockIsRejected()
    {
        using var f=new Fixture();await using var connection=await f.Connect();await using var tx=await connection.BeginTransactionAsync(System.Data.IsolationLevel.ReadCommitted,TestContext.Current.CancellationToken);
        Assert.Equal("mfa_maintenance_census_lock_required",(await Assert.ThrowsAsync<MfaMaintenanceException>(()=>MfaFactorKeyInventoryReader.ReadForMaintenanceAsync(connection,tx,f.Installation,TestContext.Current.CancellationToken))).Code);
    }

    private sealed class SyntheticCut:Exception;

    private sealed class Fixture:IDisposable
    {
        private readonly JsonElement context;
        private readonly List<Guid> users=[];
        internal Guid Installation{get;}
        internal string CaseRoot{get;}
        internal string Instances{get;}
        internal string Retained{get;}
        internal string Fence=>Path.Combine(Instances,Installation.ToString("D"),WindowsMfaMaintenanceStore.FenceFileName);
        internal SecurityIdentifier Reader{get;}=new(WellKnownSidType.BuiltinUsersSid,null);
        internal SecurityIdentifier[] Trusted{get;}
        internal Dictionary<int,byte[]> Keys{get;}=new(){[1]=RandomNumberGenerator.GetBytes(32),[2]=RandomNumberGenerator.GetBytes(32),[7]=RandomNumberGenerator.GetBytes(32)};
        internal WindowsMfaKeyProvider Provider=>new(Instances,Installation,Reader,Trusted);
        private byte[] Ring{get;}
        internal Fixture()
        {
            context=JsonDocument.Parse(File.ReadAllBytes(Environment.GetEnvironmentVariable("RACKCLICK_F0602_MAINT_CONTEXT")!)).RootElement.Clone();
            Installation=context.GetProperty("installationId").GetGuid();
            CaseRoot=Path.Combine(context.GetProperty("fixtureRoot").GetString()!,"case-"+Guid.NewGuid().ToString("N"));Directory.CreateDirectory(CaseRoot);
            Instances=Path.Combine(CaseRoot,"instances");Retained=Path.Combine(CaseRoot,"retained");Directory.CreateDirectory(Retained);
            Trusted=[WindowsIdentity.GetCurrent().User!,new(WellKnownSidType.LocalSystemSid,null),new(WellKnownSidType.BuiltinAdministratorsSid,null)];
            Ring=JsonSerializer.SerializeToUtf8Bytes(new{format=MfaKeyRing.RingFormat,formatVersion=1,installationId=Installation,
                versions=Keys.Keys.Select(v=>new{version=v,state=v==1?"active":"retired",createdAtUtc="2026-11-09T00:00:00Z"})});
            WindowsMfaKeyStoreWriter.CreateStoreFromMaterial(Instances,Installation,Reader,Trusted,Ring,Keys.Select(p=>(p.Key,p.Value)).ToArray());
        }
        internal async Task<NpgsqlConnection> Connect()
        {var db=new NpgsqlConnection(new NpgsqlConnectionStringBuilder(context.GetProperty("ownerConnection").GetString()!){Pooling=false}.ConnectionString);await db.OpenAsync(TestContext.Current.CancellationToken);return db;}
        internal async Task<MfaMaintenanceResult> Run(string action,string hash="",int candidate=0,Guid operation=default,byte[]? catalog=null,Action<string>? checkpoint=null)
        {
            var request=new MfaMaintenanceRequest(action,context.GetProperty("ownerConnection").GetString()!,Instances,Installation,Reader,hash,candidate,operation,catalog);
            return await MfaMaintenanceCoordinator.RunAsync(request,Trusted,checkpoint,TestContext.Current.CancellationToken);
        }
        internal byte[] Catalog(object[] entries,string? root=null)=>JsonSerializer.SerializeToUtf8Bytes(new{format="RackClick.MfaBackupCatalog",formatVersion=1,
            installationId=Installation,catalogId=Guid.NewGuid(),operatorSid=WindowsIdentity.GetCurrent().User!.Value,confirmedUtc=DateTime.UtcNow.ToString("O"),
            coverage="all-retained-roots-declared",roots=new[]{root??Retained},entries});
        internal async Task<string> Initialize()=> (await Run("catalog-initialize",catalog:Catalog([]))).CatalogSha256;
        internal async Task<Guid> AddFactor(int version,string state)
        {
            var user=Guid.NewGuid();users.Add(user);await using var connection=await Connect();
            var house=(Guid)(await new NpgsqlCommand("SELECT id FROM public.systemhaus",connection).ExecuteScalarAsync(TestContext.Current.CancellationToken))!;
            var secret=RandomNumberGenerator.GetBytes(20);byte[] cipher;
            try{cipher=MfaSecretCipher.Seal(Keys[version],version,secret,house,user);}finally{CryptographicOperations.ZeroMemory(secret);}
            await using var command=new NpgsqlCommand("INSERT INTO public.app_user(id,systemhaus_id,username,password_hash) VALUES(@user,@house,@name,@password); INSERT INTO public.app_mfa_factor(systemhaus_id,user_id,state,secret_ciphertext,key_version) VALUES(@house,@user,@state,@cipher,@version)",connection);
            command.Parameters.AddWithValue("user",user);command.Parameters.AddWithValue("house",house);command.Parameters.AddWithValue("name","synthetic-retire-"+user.ToString("N"));
            command.Parameters.AddWithValue("password",Convert.ToHexString(RandomNumberGenerator.GetBytes(32)));command.Parameters.AddWithValue("state",state);command.Parameters.AddWithValue("cipher",cipher);command.Parameters.AddWithValue("version",version);
            await command.ExecuteNonQueryAsync(TestContext.Current.CancellationToken);return user;
        }
        internal async Task RemoveUser(Guid user)
        {await using var connection=await Connect();await using var tx=await connection.BeginTransactionAsync(TestContext.Current.CancellationToken);await using var command=new NpgsqlCommand("DELETE FROM public.app_mfa_factor WHERE user_id=@id; DELETE FROM public.app_user WHERE id=@id",connection,tx);command.Parameters.AddWithValue("id",user);await command.ExecuteNonQueryAsync(TestContext.Current.CancellationToken);await tx.CommitAsync(TestContext.Current.CancellationToken);}
        internal async Task Authenticate(Guid user)
        {
            await using var connection=await Connect();await using var command=new NpgsqlCommand("SELECT systemhaus_id,key_version,secret_ciphertext FROM public.app_mfa_factor WHERE user_id=@id",connection);command.Parameters.AddWithValue("id",user);
            await using var row=await command.ExecuteReaderAsync(TestContext.Current.CancellationToken);Assert.True(await row.ReadAsync(TestContext.Current.CancellationToken));var key=Provider.GetKey(row.GetInt32(1));byte[]? plain=null;
            try{plain=MfaSecretCipher.Open(key,row.GetInt32(1),row.GetFieldValue<byte[]>(2),row.GetGuid(0),user);Assert.Equal(20,plain.Length);}finally{CryptographicOperations.ZeroMemory(key);if(plain is not null)CryptographicOperations.ZeroMemory(plain);}
        }
        internal async Task<string> Fingerprint()
        {
            await using var connection=await Connect();await using var command=new NpgsqlCommand("""
                SELECT md5(jsonb_build_object(
                    'users',(SELECT jsonb_agg(to_jsonb(t) ORDER BY id) FROM public.app_user t),
                    'factors',(SELECT jsonb_agg(to_jsonb(t) ORDER BY systemhaus_id,user_id) FROM public.app_mfa_factor t),
                    'policies',(SELECT jsonb_agg(to_jsonb(t) ORDER BY systemhaus_id,user_id) FROM public.app_mfa_user t),
                    'sessions',(SELECT jsonb_agg(to_jsonb(t) ORDER BY token_hash) FROM public.app_session t),
                    'challenges',(SELECT jsonb_agg(to_jsonb(t) ORDER BY token_hash) FROM public.app_mfa_challenge t),
                    'house',(SELECT jsonb_agg(to_jsonb(t) ORDER BY id) FROM public.systemhaus t))::text)
                """,connection);return (string)(await command.ExecuteScalarAsync(TestContext.Current.CancellationToken))!;
        }
        internal string[] KeyHashes()=>Keys.Keys.Order().Select(v=>Hash(File.ReadAllBytes(Path.Combine(Instances,Installation.ToString("D"),WindowsMfaKeyProvider.KeysFolderName,MfaKeyRing.KeyFileName(v))))).ToArray();
        internal async Task<object> CreateBackup(int factorVersion)
        {
            var backup=Guid.NewGuid();var dir=Path.Combine(Retained,backup.ToString("D"));var database=Path.Combine(dir,"database");Directory.CreateDirectory(database);
            var settings=new NpgsqlConnectionStringBuilder(context.GetProperty("ownerConnection").GetString()!);
            var start=new ProcessStartInfo(Path.Combine(context.GetProperty("postgresBin").GetString()!,"pg_dump.exe")){UseShellExecute=false,CreateNoWindow=true,RedirectStandardOutput=true,RedirectStandardError=true};
            foreach(var arg in new[]{"-w","-h","127.0.0.1","-p",settings.Port.ToString(),"-U",settings.Username!,"-d",settings.Database!,"-F","c","--no-owner","--no-acl","-f",Path.Combine(database,"data.dump")})start.ArgumentList.Add(arg);
            foreach(var name in start.Environment.Keys.Where(k=>k.StartsWith("PG",StringComparison.OrdinalIgnoreCase)).ToArray())start.Environment.Remove(name);
            start.Environment["PGPASSFILE"]=context.GetProperty("ownerPgpass").GetString()!;
            using var process=Process.Start(start)!;var stdout=process.StandardOutput.ReadToEndAsync();var stderr=process.StandardError.ReadToEndAsync();
            await process.WaitForExitAsync(TestContext.Current.CancellationToken);await stdout;await stderr;Assert.Equal(0,process.ExitCode);
            var dump=File.ReadAllBytes(Path.Combine(database,"data.dump"));
            var manifest=JsonSerializer.SerializeToUtf8Bytes(new{schemaVersion=1,kind="RackClickDatabaseBackup",postgresVersion="17.11",format="custom",dumpFile="data.dump",dumpBytes=dump.Length,dumpSha256=Hash(dump),createdUtc=DateTime.UtcNow.ToString("O")});
            File.WriteAllBytes(Path.Combine(database,"manifest.json"),manifest);
            using var payload=MfaKeyRecoveryPayload.Serialize(Ring,Installation,Keys.Select(p=>(p.Key,p.Value)).ToArray());
            var password=Convert.ToHexString(RandomNumberGenerator.GetBytes(20));
            var envelope=MfaKeyRecoveryEnvelope.Seal(password,payload.Bytes);
            var envelopeInfo=MfaKeyRetention.InspectEnvelope(envelope,password,Installation);
            var inventory=MfaKeyRetention.CreateBackupInventory(backup,MfaKeyRetention.FactorInventory(Installation,[new(factorVersion,0,1,0)]),envelopeInfo,Hash(manifest),Hash(dump));
            File.WriteAllBytes(Path.Combine(dir,"mfa-inventory.json"),MfaKeyRetention.SerializeBackupInventory(inventory));
            var receipt=JsonSerializer.SerializeToUtf8Bytes(new{format="RackClick.MfaBackupInventoryReceipt",formatVersion=1,installationId=Installation,backupId=backup,
                inventorySha256=Hash(File.ReadAllBytes(Path.Combine(dir,"mfa-inventory.json"))),manifestSha256=Hash(manifest),dumpSha256=Hash(dump),envelopeSha256=Hash(envelope)});
            return new{backupDirectory=dir,receiptBase64=Convert.ToBase64String(receipt),receiptSha256=Hash(receipt)};
        }
        public void Dispose()
        {
            foreach(var user in users)RemoveUser(user).GetAwaiter().GetResult();
            foreach(var key in Keys.Values)CryptographicOperations.ZeroMemory(key);
            // Isolated artifacts/DPAPI files remain private in the new lab, never delete by a supplied path.
        }
        private static string Hash(byte[] bytes)=>Convert.ToHexStringLower(SHA256.HashData(bytes));
    }
}
