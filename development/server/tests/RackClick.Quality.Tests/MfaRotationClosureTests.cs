using System.Data;
using System.Diagnostics;
using System.Runtime.Versioning;
using System.Security.Cryptography;
using System.Security.Principal;
using System.Text.Json;
using System.Text.Json.Nodes;
using Npgsql;
using RackClick.Server;
using Xunit;

namespace RackClick.Quality.Tests;

// Dedicated fresh native-name databases, never an installed instance. All state/dumps/envelopes stay private.
// Catches dropping a backup-only key, accepting incomplete material, or changing a TOTP across generations.
[SupportedOSPlatform("windows")]
public sealed class MfaRotationClosureTests
{
    public static bool Available => OperatingSystem.IsWindows() && File.Exists(Environment.GetEnvironmentVariable("RACKCLICK_F0604_CONTEXT"));
    private static CancellationToken Ct => TestContext.Current.CancellationToken;
    private static string Hash(byte[] bytes) => Convert.ToHexStringLower(SHA256.HashData(bytes));

    [Fact(Skip="Dedicated fresh F0604 laboratory required", SkipUnless=nameof(Available))]
    public async Task RetainedGenerationsWorker()
    {
        using var json=JsonDocument.Parse(File.ReadAllBytes(Environment.GetEnvironmentVariable("RACKCLICK_F0604_CONTEXT")!));
        var c=json.RootElement; var id=c.GetProperty("installationId").GetGuid();
        var root=c.GetProperty("instancesRoot").GetString()!; var privateRoot=c.GetProperty("privateRoot").GetString()!;
        var statePath=Path.Combine(privateRoot,"state.private.json"); var stage=c.GetProperty("stage").GetString();
        var reader=new SecurityIdentifier(WellKnownSidType.BuiltinUsersSid,null);
        SecurityIdentifier[] trusted=[WindowsIdentity.GetCurrent().User!,new(WellKnownSidType.LocalSystemSid,null),new(WellKnownSidType.BuiltinAdministratorsSid,null)];
        var provider=new WindowsMfaKeyProvider(root,id,reader,trusted);
        var keyFolder=Path.Combine(root,id.ToString("D"),"mfa-keys");
        var retained=Path.Combine(privateRoot,"retained");
        JsonObject state=stage=="seed"?new():JsonNode.Parse(File.ReadAllText(statePath))!.AsObject();
        void Save()=>File.WriteAllText(statePath,state.ToJsonString());
        async Task<NpgsqlConnection> Connect()
        {
            var db=new NpgsqlConnection(new NpgsqlConnectionStringBuilder(c.GetProperty("ownerConnection").GetString()!){Pooling=false}.ConnectionString);
            await db.OpenAsync(Ct);return db;
        }
        async Task<string> Scalar(string sql)
        {await using var db=await Connect();await using var cmd=new NpgsqlCommand(sql,db);return (string)(await cmd.ExecuteScalarAsync(Ct))!;}
        MfaMaintenanceRequest Request(string action,int version=0,Guid operation=default,byte[]? catalog=null)=>
            new(action,c.GetProperty("ownerConnection").GetString()!,root,id,reader,state["catalog"]?.GetValue<string>()??"",version,operation,catalog);
        async Task<MfaMaintenanceResult> Maintenance(string action,int version=0,byte[]? catalog=null)=>
            await MfaMaintenanceCoordinator.RunAsync(Request(action,version,Guid.NewGuid(),catalog),trusted,null,Ct);
        byte[] Catalog()=>JsonSerializer.SerializeToUtf8Bytes(new{format="RackClick.MfaBackupCatalog",formatVersion=1,installationId=id,catalogId=Guid.NewGuid(),
            operatorSid=WindowsIdentity.GetCurrent().User!.Value,confirmedUtc=DateTime.UtcNow.ToString("O"),coverage="all-retained-roots-declared",roots=new[]{retained},
            entries=state["backups"]!.AsArray().Select(b=>new{backupDirectory=b!["directory"]!.GetValue<string>(),receiptBase64=b["receipt"]!.GetValue<string>(),receiptSha256=b["receiptHash"]!.GetValue<string>()})});
        const string MetadataSql="""
            SELECT jsonb_build_object(
              'factors',(SELECT jsonb_agg(to_jsonb(f)-'secret_ciphertext'-'key_version' ORDER BY user_id) FROM app_mfa_factor f),
              'users',(SELECT jsonb_agg(to_jsonb(u) ORDER BY id) FROM app_user u),
              'policy',(SELECT jsonb_agg(to_jsonb(m) ORDER BY user_id) FROM app_mfa_user m),
              'codes',(SELECT jsonb_agg(to_jsonb(r) ORDER BY user_id,code_hash) FROM app_mfa_recovery_code r),
              'house',(SELECT jsonb_agg(to_jsonb(h) ORDER BY id) FROM systemhaus h))::text
            """;
        const string DataSql="""
            SELECT md5(jsonb_build_object(
              'factors',(SELECT jsonb_agg(to_jsonb(f) ORDER BY user_id) FROM app_mfa_factor f),
              'witness',(SELECT jsonb_agg(to_jsonb(w) ORDER BY new_version) FROM app_mfa_rotation_witness w),
              'sessions',(SELECT jsonb_agg(to_jsonb(s) ORDER BY token_hash) FROM app_session s),
              'challenges',(SELECT jsonb_agg(to_jsonb(c) ORDER BY token_hash) FROM app_mfa_challenge c))::text)
            """;
        string[] KeyHashes()=>Directory.GetFiles(keyFolder,"key-*.json").Order().Select(p=>Path.GetFileName(p)+":"+Hash(File.ReadAllBytes(p))).ToArray();
        async Task Authenticate(IMfaKeyProvider keys,int[] versions)
        {
            await using var db=await Connect();await using var cmd=new NpgsqlCommand("SELECT systemhaus_id,user_id,key_version,secret_ciphertext FROM app_mfa_factor ORDER BY user_id",db);
            await using var rows=await cmd.ExecuteReaderAsync(Ct);var actual=new List<int>();
            while(await rows.ReadAsync(Ct))
            {
                var version=rows.GetInt32(2);actual.Add(version);var key=keys.GetKey(version);byte[]? plain=null;
                try
                {
                    plain=MfaSecretCipher.Open(key,version,rows.GetFieldValue<byte[]>(3),rows.GetGuid(0),rows.GetGuid(1));
                    Assert.True(Hash(plain)==state["secrets"]![rows.GetGuid(1).ToString("D")]!.GetValue<string>(),"Synthetic TOTP identity changed");
                }
                finally{CryptographicOperations.ZeroMemory(key);if(plain is not null)CryptographicOperations.ZeroMemory(plain);}
            }
            Assert.Equal(versions.Order(),actual.Order());Assert.Equal(3,actual.Count);
        }
        async Task Backup()
        {
            var backupId=Guid.NewGuid();var folder=Path.Combine(retained,backupId.ToString("D"));var database=Path.Combine(folder,"database");Directory.CreateDirectory(database);
            var dumpPath=Path.Combine(database,"data.dump");var password=Convert.ToHexString(RandomNumberGenerator.GetBytes(24));
            byte[] envelope;
            // Same maintenance exclusion, ring handle, and exported DB snapshot for census and pg_dump.
            await using(var db=await Connect())
            await using(var admission=await MfaMaintenanceAdmission.SharedAsync(db,Ct))
            using(var ring=MfaMaintenanceAdmission.HoldHostRing(root,id))
            await using(var tx=await db.BeginTransactionAsync(IsolationLevel.RepeatableRead,Ct))
            {
                await using(var ro=new NpgsqlCommand("SET TRANSACTION READ ONLY",db,tx))await ro.ExecuteNonQueryAsync(Ct);
                var census=await MfaFactorKeyInventoryReader.ReadAsync(db,tx,id,Ct);
                await using var snapshotCommand=new NpgsqlCommand("SELECT pg_export_snapshot()",db,tx);
                var snapshot=(string)(await snapshotCommand.ExecuteScalarAsync(Ct))!;
                envelope=WindowsMfaKeyRecovery.Export(root,id,reader,trusted,password);
                var settings=new NpgsqlConnectionStringBuilder(c.GetProperty("ownerConnection").GetString()!);
                var start=new ProcessStartInfo(Path.Combine(c.GetProperty("postgresBin").GetString()!,"pg_dump.exe"))
                    {UseShellExecute=false,CreateNoWindow=true,RedirectStandardOutput=true,RedirectStandardError=true};
                foreach(var arg in new[]{"-w","-h","127.0.0.1","-p",settings.Port.ToString(System.Globalization.CultureInfo.InvariantCulture),"-U",settings.Username!,"-d",settings.Database!,"-Fc","--no-owner","--no-acl","--snapshot="+snapshot,"-f",dumpPath})start.ArgumentList.Add(arg);
                foreach(var name in start.Environment.Keys.Where(k=>k.StartsWith("PG",StringComparison.OrdinalIgnoreCase)).ToArray())start.Environment.Remove(name);
                start.Environment["PGPASSFILE"]=c.GetProperty("ownerPgpass").GetString()!;
                using var process=Process.Start(start)!;var stdout=process.StandardOutput.ReadToEndAsync();var stderr=process.StandardError.ReadToEndAsync();
                await process.WaitForExitAsync(Ct);await stdout;await stderr;Assert.Equal(0,process.ExitCode);
                var dumpHash=Hash(File.ReadAllBytes(dumpPath));
                var manifest=JsonSerializer.SerializeToUtf8Bytes(new{schemaVersion=1,kind="RackClickDatabaseBackup",postgresVersion="17.11",format="custom",dumpFile="data.dump",dumpBytes=new FileInfo(dumpPath).Length,dumpSha256=dumpHash,createdUtc=DateTime.UtcNow.ToString("O")});
                File.WriteAllBytes(Path.Combine(database,"manifest.json"),manifest);
                var info=MfaKeyRetention.InspectEnvelope(envelope,password,id);
                var inventory=MfaKeyRetention.CreateBackupInventory(backupId,census,info,Hash(manifest),dumpHash);
                var bytes=MfaKeyRetention.SerializeBackupInventory(inventory);File.WriteAllBytes(Path.Combine(folder,"mfa-inventory.json"),bytes);
                var receipt=JsonSerializer.SerializeToUtf8Bytes(new{format="RackClick.MfaBackupInventoryReceipt",formatVersion=1,installationId=id,backupId,
                    inventorySha256=Hash(bytes),manifestSha256=Hash(manifest),dumpSha256=dumpHash,envelopeSha256=Hash(envelope)});
                // Envelope outside retained root/instance, synthetic custody on this machine, never production custody.
                var envelopePath=Path.Combine(privateRoot,"custody-"+backupId.ToString("N")+".rckey");File.WriteAllBytes(envelopePath,envelope);
                state["backups"]!.AsArray().Add(new JsonObject{["directory"]=folder,["receipt"]=Convert.ToBase64String(receipt),["receiptHash"]=Hash(receipt),
                    ["envelope"]=envelopePath,["password"]=password,["dumpHash"]=dumpHash,["metadata"]=await Scalar(MetadataSql),
                    ["versions"]=new JsonArray(census.Entries.SelectMany(e=>Enumerable.Repeat(e.Version,checked((int)(e.Pending+e.Active+e.Disabled)))).Select(v=>(JsonNode?)JsonValue.Create(v)).ToArray())});
                await tx.CommitAsync(Ct);
            }
            CryptographicOperations.ZeroMemory(envelope);Save();
        }
        async Task Rotate(int version)
        {
            var operation=Guid.NewGuid();var request=Request("rotate",operation:operation);
            var oldKeys=KeyHashes();var metadata=await Scalar(MetadataSql);
            Assert.Equal(version,(await MfaRotationCoordinator.PrepareAsync(request,trusted,null,Ct)).NewVersion);
            var password=Convert.ToHexString(RandomNumberGenerator.GetBytes(24));
            var envelope=await MfaRotationCoordinator.ExportAsync(request,trusted,password,Ct);
            try
            {
                var outcome=await MfaRotationCoordinator.ResumeAsync(request,trusted,envelope,password,Hash(envelope),null,Ct);
                Assert.Equal("verified",outcome.Phase);Assert.Equal(3,outcome.Factors);Assert.Equal(version,outcome.NewVersion);
                await MfaRotationCoordinator.ResumeAsync(request,trusted,null,null,"",null,Ct);
            }
            finally{CryptographicOperations.ZeroMemory(envelope);}
            Assert.All(oldKeys,k=>Assert.Contains(k,KeyHashes()));Assert.Equal(metadata,await Scalar(MetadataSql));
            await Authenticate(provider,[version,version,version]);
            await using var guardDb=await Connect();await MfaRotationStartupGuard.ValidateAsync(guardDb,root,id,reader,trusted,provider,Ct);
        }
        if(stage=="seed")
        {
            Assert.False(File.Exists(statePath));Directory.CreateDirectory(retained);state["backups"]=new JsonArray();state["secrets"]=new JsonObject();
            var keys=new Dictionary<int,byte[]>{{1,RandomNumberGenerator.GetBytes(32)},{7,RandomNumberGenerator.GetBytes(32)}};
            var ring=JsonSerializer.SerializeToUtf8Bytes(new{format=MfaKeyRing.RingFormat,formatVersion=1,installationId=id,versions=keys.Keys.Select(v=>new{version=v,state=v==1?"active":"retired",createdAtUtc="2026-11-11T00:00:00Z"})});
            try
            {
                WindowsMfaKeyStoreWriter.CreateStoreFromMaterial(root,id,reader,trusted,ring,keys.Select(k=>(k.Key,k.Value)).ToArray());
                var house=Guid.Parse(await Scalar("SELECT id::text FROM systemhaus"));
                foreach(var (status,version) in new[]{("active",1),("pending",7),("disabled",7)})
                {
                    var user=Guid.NewGuid();var secret=RandomNumberGenerator.GetBytes(20);byte[] cipher;
                    try{state["secrets"]![user.ToString("D")]=Hash(secret);cipher=MfaSecretCipher.Seal(keys[version],version,secret,house,user);}
                    finally{CryptographicOperations.ZeroMemory(secret);}
                    try
                    {
                        await using var db=await Connect();await using var cmd=new NpgsqlCommand("""
                          INSERT INTO app_user(id,systemhaus_id,username,password_hash) VALUES(@u,@h,@name,@password);
                          INSERT INTO app_mfa_factor(systemhaus_id,user_id,state,key_version,secret_ciphertext,last_time_step,failed_attempts) VALUES(@h,@u,@state,@v,@cipher,1234567,3);
                          INSERT INTO app_mfa_user(systemhaus_id,user_id,mfa_required,revision) VALUES(@h,@u,true,19);
                          INSERT INTO app_mfa_recovery_code(systemhaus_id,user_id,code_hash) VALUES(@h,@u,@code);
                          """,db);
                        foreach(var (name,value) in new (string,object)[]{("u",user),("h",house),("name","synthetic-retained-"+user.ToString("N")),("password",Hash(RandomNumberGenerator.GetBytes(32))),
                            ("state",status),("v",version),("cipher",cipher),("code",Guid.NewGuid().ToString("N"))})cmd.Parameters.AddWithValue(name,value);
                        await cmd.ExecuteNonQueryAsync(Ct);
                    }
                    finally{CryptographicOperations.ZeroMemory(cipher);}
                }
            }
            finally{foreach(var key in keys.Values)CryptographicOperations.ZeroMemory(key);}
            await Backup();state["catalog"]=(await Maintenance("catalog-initialize",catalog:Catalog())).CatalogSha256;Save();
            Assert.Single(state["backups"]!.AsArray());await Authenticate(provider,[1,7,7]);
        }
        else if(stage=="rotate")
        {
            await Rotate(8);await Backup();
            state["catalog"]=(await Maintenance("catalog-refresh",catalog:Catalog())).CatalogSha256;Save();
            await Rotate(9);await Backup();
            state["catalog"]=(await Maintenance("catalog-refresh",catalog:Catalog())).CatalogSha256;Save();
            Assert.Equal(3,state["backups"]!.AsArray().Count);Assert.Equal("2",await Scalar("SELECT count(*)::text FROM app_mfa_rotation_witness"));
            var before=await Scalar(DataSql);var keyHashes=KeyHashes();var ringPath=Path.Combine(keyFolder,MfaKeyRing.RingFileName);var ringHash=Hash(File.ReadAllBytes(ringPath));
            foreach(var v in new[]{1,7,8})
                Assert.Equal("mfa_retirement_backup_referenced",(await Assert.ThrowsAsync<MfaMaintenanceException>(()=>Maintenance("retire",v))).Code);
            // Key 1 no longer encrypts any live row; its only dependency is retained backups.
            var missing=Path.Combine(keyFolder,MfaKeyRing.KeyFileName(1));var held=Path.Combine(privateRoot,"own-key-held.dpapi.json");File.Move(missing,held);
            try
            {
                await Assert.ThrowsAsync<MfaKeyRingException>(()=>MfaRotationCoordinator.PrepareAsync(Request("rotate",operation:Guid.NewGuid()),trusted,null,Ct));
                Assert.Equal(before,await Scalar(DataSql));Assert.Equal(ringHash,Hash(File.ReadAllBytes(ringPath)));
                Assert.False(File.Exists(Path.Combine(root,id.ToString("D"),WindowsMfaMaintenanceStore.FenceFileName)));
            }
            finally{File.Move(held,missing);}
            var dump=Path.Combine(state["backups"]![0]!["directory"]!.GetValue<string>(),"database","data.dump");
            var dumpBytes=File.ReadAllBytes(dump);File.WriteAllBytes(dump,[..dumpBytes,0]);
            try
            {
                await Assert.ThrowsAsync<MfaBackupCatalogException>(()=>MfaRotationCoordinator.PrepareAsync(Request("rotate",operation:Guid.NewGuid()),trusted,null,Ct));
                Assert.Equal(before,await Scalar(DataSql));Assert.Equal(ringHash,Hash(File.ReadAllBytes(ringPath)));
                Assert.False(File.Exists(Path.Combine(root,id.ToString("D"),WindowsMfaMaintenanceStore.FenceFileName)));
            }
            finally{File.WriteAllBytes(dump,dumpBytes);}
            Assert.Equal(keyHashes,KeyHashes());Assert.Equal(before,await Scalar(DataSql));await Authenticate(provider,[9,9,9]);
            state["finalDataHash"]=before;Save();
        }
        else if(stage=="restore")
        {
            var backup=state["backups"]![c.GetProperty("backupIndex").GetInt32()]!;
            var versions=backup["versions"]!.AsArray().Select(v=>v!.GetValue<int>()).ToArray();
            Assert.Equal(backup["metadata"]!.GetValue<string>(),await Scalar(MetadataSql));
            var before=await Scalar(DataSql);await Authenticate(provider,versions); // Still works with the final live ring9.
            var envelope=File.ReadAllBytes(backup["envelope"]!.GetValue<string>());var password=backup["password"]!.GetValue<string>();
            var recovered=Path.Combine(c.GetProperty("restoreRoot").GetString()!,"keys");
            WindowsMfaKeyRecovery.Recover(envelope,password,id,recovered,id,reader,trusted,false);
            var restoredProvider=new WindowsMfaKeyProvider(recovered,id,reader,trusted);
            await Authenticate(restoredProvider,versions);Assert.Equal(before,await Scalar(DataSql));
            Assert.Equal(backup["dumpHash"]!.GetValue<string>(),Hash(File.ReadAllBytes(Path.Combine(backup["directory"]!.GetValue<string>(),"database","data.dump"))));
            var missing=Path.Combine(recovered,id.ToString("D"),"mfa-keys",MfaKeyRing.KeyFileName(versions[0]));
            var held=Path.Combine(c.GetProperty("restoreRoot").GetString()!,"held-key.json");File.Move(missing,held);
            try{await Assert.ThrowsAsync<MfaKeyRingException>(()=>Authenticate(restoredProvider,versions));Assert.Equal(before,await Scalar(DataSql));}
            finally{File.Move(held,missing);}
            await Authenticate(restoredProvider,versions);CryptographicOperations.ZeroMemory(envelope);
        }
        else throw new InvalidOperationException("unknown_test_stage");
    }
}
