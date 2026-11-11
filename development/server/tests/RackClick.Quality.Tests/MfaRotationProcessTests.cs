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

// Worker intentionally killed only by the dedicated parent runner; no fallback database/service.
[SupportedOSPlatform("windows")]
public sealed class MfaRotationProcessTests
{
    public static bool Available=>OperatingSystem.IsWindows() && File.Exists(Environment.GetEnvironmentVariable("RACKCLICK_F0603_CONTEXT"));
    private static CancellationToken Ct=>TestContext.Current.CancellationToken;
    private static string Hash(byte[] b)=>Convert.ToHexStringLower(SHA256.HashData(b));

    [Fact(Skip="Dedicated fresh process laboratory required",SkipUnless=nameof(Available))]
    public async Task Worker()
    {
        using var context=JsonDocument.Parse(File.ReadAllBytes(Environment.GetEnvironmentVariable("RACKCLICK_F0603_CONTEXT")!));
        var c=context.RootElement;
        Assert.True(c.TryGetProperty("stage",out var stage));
        var id=c.GetProperty("installationId").GetGuid();
        var root=Path.Combine(c.GetProperty("fixtureRoot").GetString()!,"instances");
        var reader=new SecurityIdentifier(WellKnownSidType.BuiltinUsersSid,null);
        SecurityIdentifier[] trusted=[WindowsIdentity.GetCurrent().User!,new(WellKnownSidType.LocalSystemSid,null),new(WellKnownSidType.BuiltinAdministratorsSid,null)];
        var connection=c.GetProperty("ownerConnection").GetString()!;
        var statePath=c.GetProperty("caseState").GetString()!;
        JsonObject state;
        async Task<NpgsqlConnection> Connect(bool runtime=false)
        {
            var db=new NpgsqlConnection(new NpgsqlConnectionStringBuilder(runtime?c.GetProperty("runtimeConnection").GetString()!:connection){Pooling=false}.ConnectionString);
            await db.OpenAsync(Ct);return db;
        }
        async Task<string> Scalar(string sql)
        {
            await using var db=await Connect();await using var cmd=new NpgsqlCommand(sql,db);
            return Convert.ToString(await cmd.ExecuteScalarAsync(Ct),System.Globalization.CultureInfo.InvariantCulture)!;
        }
        void Save()=>File.WriteAllText(statePath,state.ToJsonString());
        var keysFolder=Path.Combine(root,id.ToString("D"),"mfa-keys");
        var provider=new WindowsMfaKeyProvider(root,id,reader,trusted);
        var metaSql="""
            SELECT jsonb_build_object('factors',(SELECT jsonb_agg(to_jsonb(t)-'key_version'-'secret_ciphertext' ORDER BY user_id) FROM app_mfa_factor t),
            'users',(SELECT jsonb_agg(to_jsonb(t) ORDER BY id) FROM app_user t),
            'policy',(SELECT jsonb_agg(to_jsonb(t) ORDER BY user_id) FROM app_mfa_user t),
            'recovery',(SELECT jsonb_agg(to_jsonb(t) ORDER BY user_id,code_hash) FROM app_mfa_recovery_code t),
            'house',(SELECT jsonb_agg(to_jsonb(t) ORDER BY id) FROM systemhaus t))::text
            """;
        if(stage.GetString()=="cut")
        {
            Assert.False(File.Exists(statePath));
            var originals=new Dictionary<int,byte[]>{{1,RandomNumberGenerator.GetBytes(32)},{7,RandomNumberGenerator.GetBytes(32)}};
            var ring=JsonSerializer.SerializeToUtf8Bytes(new{format=MfaKeyRing.RingFormat,formatVersion=1,installationId=id,
                versions=originals.Keys.Select(v=>new{version=v,state=v==1?"active":"retired",createdAtUtc="2026-11-10T00:00:00Z"})});
            WindowsMfaKeyStoreWriter.CreateStoreFromMaterial(root,id,reader,trusted,ring,originals.Select(k=>(k.Key,k.Value)).ToArray());
            var expected=new JsonObject();
            foreach(var (status,v) in new[]{("active",1),("pending",7),("disabled",7)})
            {
                await using var db=await Connect();
                var house=Guid.Parse(await Scalar("SELECT id::text FROM systemhaus"));var user=Guid.NewGuid();var secret=RandomNumberGenerator.GetBytes(20);
                var cipher=MfaSecretCipher.Seal(originals[v],v,secret,house,user);expected[user.ToString("D")]=Hash(secret);
                CryptographicOperations.ZeroMemory(secret);
                await using var insert=new NpgsqlCommand("""
                    INSERT INTO app_user(id,systemhaus_id,username,password_hash) VALUES(@u,@h,@name,@password);
                    INSERT INTO app_mfa_factor(systemhaus_id,user_id,state,key_version,secret_ciphertext,last_time_step,failed_attempts)
                        VALUES(@h,@u,@state,@v,@cipher,1234567,3);
                    INSERT INTO app_mfa_user(systemhaus_id,user_id,mfa_required,revision) VALUES(@h,@u,true,19);
                    INSERT INTO app_mfa_recovery_code(systemhaus_id,user_id,code_hash) VALUES(@h,@u,@code);
                    INSERT INTO app_session(token_hash,user_id,csrf_hash,expires_at) VALUES(@token,@u,@csrf,clock_timestamp()+interval '1 hour');
                    INSERT INTO app_mfa_challenge(token_hash,systemhaus_id,user_id,purpose,csrf_hash,expires_at)
                        VALUES(@challenge,@h,@u,'verify',@csrf,now()+interval '4 minutes');
                    """,db);
                foreach(var p in new (string,object)[]{("u",user),("h",house),("name","synthetic-rotation-"+user.ToString("N")),("password",Hash(RandomNumberGenerator.GetBytes(32))),
                    ("state",status),("v",v),("cipher",cipher),("code",Guid.NewGuid().ToString("N")),("token",Guid.NewGuid().ToString("N")),
                    ("csrf",Guid.NewGuid().ToString("N")),("challenge",Guid.NewGuid().ToString("N"))})insert.Parameters.AddWithValue(p.Item1,p.Item2);
                await insert.ExecuteNonQueryAsync(Ct);CryptographicOperations.ZeroMemory(cipher);
            }
            foreach(var k in originals.Values)CryptographicOperations.ZeroMemory(k);
            var retained=Path.Combine(c.GetProperty("fixtureRoot").GetString()!,"retained");Directory.CreateDirectory(retained);
            var catalog=JsonSerializer.SerializeToUtf8Bytes(new{format="RackClick.MfaBackupCatalog",formatVersion=1,installationId=id,catalogId=Guid.NewGuid(),
                operatorSid=WindowsIdentity.GetCurrent().User!.Value,confirmedUtc=DateTime.UtcNow.ToString("O"),coverage="all-retained-roots-declared",roots=new[]{retained},entries=Array.Empty<object>()});
            var init=new MfaMaintenanceRequest("catalog-initialize",connection,root,id,reader,"",0,Guid.Empty,catalog);
            var receipt=await MfaMaintenanceCoordinator.RunAsync(init,trusted,null,Ct);
            state=new JsonObject{["operation"]=Guid.NewGuid().ToString("D"),["catalog"]=receipt.CatalogSha256,["expectedSecrets"]=expected,["metadata"]=await Scalar(metaSql),
                ["oldFactor"]=await Scalar("SELECT json_build_object('user',user_id,'version',key_version,'cipher',encode(secret_ciphertext,'hex'))::text FROM app_mfa_factor WHERE state='active'"),
                ["envelopePassword"]=Convert.ToHexString(RandomNumberGenerator.GetBytes(24)),
                ["oldKeys"]=new JsonObject{["1"]=Hash(File.ReadAllBytes(Path.Combine(keysFolder,MfaKeyRing.KeyFileName(1)))),["7"]=Hash(File.ReadAllBytes(Path.Combine(keysFolder,MfaKeyRing.KeyFileName(7))))}};
            Save();
        }
        else state=JsonNode.Parse(File.ReadAllText(statePath))!.AsObject();
        if(stage.GetString()=="source-guard-reject")
        {
            await using var sourceDb=await Connect(true);
            Assert.Equal("mfa_rotation_startup_witness_missing",(await Assert.ThrowsAsync<MfaMaintenanceException>(()=>MfaRotationStartupGuard.ValidateAsync(sourceDb,root,id,reader,trusted,provider,Ct))).Code);
            await sourceDb.CloseAsync();
            var restoredOld=new MfaMaintenanceRequest("rotate",connection,root,id,reader,state["catalog"]!.GetValue<string>(),0,Guid.Parse(state["operation"]!.GetValue<string>()),null);
            var retainedEnvelope=File.ReadAllBytes(Path.Combine(Path.GetDirectoryName(statePath)!,"external-custody-fixture.rckey"));
            Assert.Equal("mfa_rotation_completed_witness_missing",(await Assert.ThrowsAsync<MfaMaintenanceException>(()=>MfaRotationCoordinator.ResumeAsync(restoredOld,trusted,retainedEnvelope,state["envelopePassword"]!.GetValue<string>(),Hash(retainedEnvelope),null,Ct))).Code);
            return;
        }
        var operation=Guid.Parse(state["operation"]!.GetValue<string>());
        var request=new MfaMaintenanceRequest("rotate",connection,root,id,reader,state["catalog"]!.GetValue<string>(),0,operation,null);
        var envelopePath=Path.Combine(Path.GetDirectoryName(statePath)!,"external-custody-fixture.rckey");
        var negative=c.GetProperty("cut").GetString()!;
        var injected=false;
        void Cut(string phase)
        {
            if(stage.GetString()=="cut" && negative=="lease_"+phase)
            {
                using var killer=new NpgsqlConnection(new NpgsqlConnectionStringBuilder(connection){Pooling=false}.ConnectionString);killer.Open();
                using var kill=new NpgsqlCommand("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname=current_database() AND application_name='RackClick.MfaMaintenance' AND pid<>pg_backend_pid()",killer);
                Assert.True((bool)kill.ExecuteScalar()!);injected=true;return;
            }
            if(stage.GetString()=="cut" && negative=="receipt_collision" && phase=="before_startup_receipt")
            {
                File.WriteAllText(Path.Combine(root,id.ToString("D"),WindowsMfaMaintenanceStore.RotationStartupFileName),"foreign-fixture");
                injected=true;return;
            }
            if(stage.GetString()!="cut" || phase!=c.GetProperty("cut").GetString())return;
            var bytes=JsonSerializer.SerializeToUtf8Bytes(new{phase,pid=Environment.ProcessId});
            using(var marker=new FileStream(c.GetProperty("marker").GetString()!,FileMode.CreateNew,FileAccess.Write,FileShare.Read))
            {marker.Write(bytes);marker.Flush(true);}
            // Parent observes the flushed marker, then terminates ONLY its owned test process tree.
            Thread.Sleep(Timeout.Infinite);
            throw new InvalidOperationException("test_process_was_not_terminated");
        }
        if(stage.GetString()=="cut")await MfaRotationCoordinator.PrepareAsync(request,trusted,Cut,Ct);
        if(!File.Exists(envelopePath))
        {
            var bytes=await MfaRotationCoordinator.ExportAsync(request,trusted,state["envelopePassword"]!.GetValue<string>(),Ct);
            using var stream=new FileStream(envelopePath,FileMode.CreateNew,FileAccess.Write,FileShare.Read);stream.Write(bytes);stream.Flush(true);
        }
        var envelope=File.ReadAllBytes(envelopePath);
        if(stage.GetString()=="cut" && (negative.StartsWith("lease_",StringComparison.Ordinal) || negative=="receipt_collision"))
        {
            if(negative.StartsWith("lease_",StringComparison.Ordinal))
                await Assert.ThrowsAnyAsync<NpgsqlException>(()=>MfaRotationCoordinator.ResumeAsync(request,trusted,envelope,state["envelopePassword"]!.GetValue<string>(),Hash(envelope),Cut,Ct));
            else
            {
                await Assert.ThrowsAsync<MfaKeyRingException>(()=>MfaRotationCoordinator.ResumeAsync(request,trusted,envelope,state["envelopePassword"]!.GetValue<string>(),Hash(envelope),Cut,Ct));
                var collision=Path.Combine(root,id.ToString("D"),WindowsMfaMaintenanceStore.RotationStartupFileName);
                Assert.Equal("foreign-fixture",File.ReadAllText(collision));
                File.Move(collision,Path.Combine(Path.GetDirectoryName(statePath)!,"foreign-preserved.txt"));
            }
            Assert.True(injected);Assert.True(File.Exists(Path.Combine(root,id.ToString("D"),WindowsMfaMaintenanceStore.FenceFileName)));
        }
        var result=await MfaRotationCoordinator.ResumeAsync(request,trusted,envelope,state["envelopePassword"]!.GetValue<string>(),Hash(envelope),injected?null:Cut,Ct);
        Assert.Equal("verified",result.Phase);Assert.Equal(8,result.NewVersion);Assert.Equal(3,result.Factors);
        var cipherAfter=await Scalar("SELECT md5(string_agg(encode(secret_ciphertext,'hex'),',' ORDER BY user_id)) FROM app_mfa_factor");
        await MfaRotationCoordinator.ResumeAsync(request,trusted,null,null,"",null,Ct);
        Assert.Equal(cipherAfter,await Scalar("SELECT md5(string_agg(encode(secret_ciphertext,'hex'),',' ORDER BY user_id)) FROM app_mfa_factor"));
        Assert.Equal(state["metadata"]!.GetValue<string>(),await Scalar(metaSql));
        Assert.Equal("0",await Scalar("SELECT count(*)::text FROM app_session"));
        Assert.Equal("0",await Scalar("SELECT count(*)::text FROM app_mfa_challenge WHERE consumed_at IS NULL"));
        Assert.Equal("1",await Scalar("SELECT count(*)::text FROM app_mfa_rotation_witness"));
        Assert.False(File.Exists(Path.Combine(root,id.ToString("D"),WindowsMfaMaintenanceStore.FenceFileName)));
        foreach(var k in state["oldKeys"]!.AsObject())Assert.Equal(k.Value!.GetValue<string>(),Hash(File.ReadAllBytes(Path.Combine(keysFolder,MfaKeyRing.KeyFileName(int.Parse(k.Key))))));
        await using(var db=await Connect())
        await using(var query=new NpgsqlCommand("SELECT systemhaus_id,user_id,key_version,secret_ciphertext FROM app_mfa_factor",db))
        await using(var rows=await query.ExecuteReaderAsync(Ct))
        {
            while(await rows.ReadAsync(Ct))
            {
                Assert.Equal(8,rows.GetInt32(2));var key=provider.GetKey(8);byte[]? plain=null;
                try{plain=MfaSecretCipher.Open(key,8,rows.GetFieldValue<byte[]>(3),rows.GetGuid(0),rows.GetGuid(1));Assert.Equal(state["expectedSecrets"]![rows.GetGuid(1).ToString("D")]!.GetValue<string>(),Hash(plain));}
                finally{CryptographicOperations.ZeroMemory(key);if(plain is not null)CryptographicOperations.ZeroMemory(plain);}
            }
        }
        await using(var db=await Connect(true))await MfaRotationStartupGuard.ValidateAsync(db,root,id,reader,trusted,provider,Ct);
        // Startup must distinguish an old-but-authentic row, a lost witness, and a mismatching ring.
        async Task Change(string sql,params (string,object)[] values)
        {
            await using var db=await Connect();await using var cmd=new NpgsqlCommand(sql,db);
            foreach(var (name,value) in values)cmd.Parameters.AddWithValue(name,value);
            await cmd.ExecuteNonQueryAsync(Ct);
        }
        async Task GuardRejects(string code)
        {
            await using var db=await Connect(true);
            var failure=await Assert.ThrowsAsync<MfaMaintenanceException>(()=>MfaRotationStartupGuard.ValidateAsync(db,root,id,reader,trusted,provider,Ct));
            Assert.Equal(code,failure.Code);
        }
        using(var old=JsonDocument.Parse(state["oldFactor"]!.GetValue<string>()))
        {
            var user=old.RootElement.GetProperty("user").GetGuid();
            var saved=await Scalar("SELECT encode(secret_ciphertext,'hex') FROM app_mfa_factor WHERE state='active'");
            await Change("UPDATE app_mfa_factor SET key_version=@v,secret_ciphertext=@c WHERE user_id=@u",("v",old.RootElement.GetProperty("version").GetInt32()),("c",Convert.FromHexString(old.RootElement.GetProperty("cipher").GetString()!)),("u",user));
            try{await GuardRejects("mfa_rotation_startup_factor_version_invalid");}
            finally{await Change("UPDATE app_mfa_factor SET key_version=8,secret_ciphertext=@c WHERE user_id=@u",("c",Convert.FromHexString(saved)),("u",user));}
        }
        var savedWitness=await Scalar("SELECT row_to_json(w)::text FROM app_mfa_rotation_witness w");
        await Change("DELETE FROM app_mfa_rotation_witness");
        try{await GuardRejects("mfa_rotation_startup_witness_missing");}
        finally{await Change("INSERT INTO app_mfa_rotation_witness SELECT * FROM jsonb_populate_record(NULL::app_mfa_rotation_witness,@row::jsonb)",("row",savedWitness));}
        var liveRing=Path.Combine(keysFolder,MfaKeyRing.RingFileName);var finalBytes=File.ReadAllBytes(liveRing);
        using(var store=new WindowsMfaMaintenanceStore(root,id,reader,trusted))
        {
            var oldRing=store.ReadRotation(operation).AdditiveRing;
            File.WriteAllBytes(liveRing,oldRing);
            try{await GuardRejects("mfa_rotation_startup_material_invalid");}
            finally{File.WriteAllBytes(liveRing,finalBytes);}
        }
        await using(var db=await Connect(true))
        {
            await using var rights=new NpgsqlCommand("SELECT has_table_privilege(current_user,'public.app_mfa_rotation_witness','SELECT'),has_table_privilege(current_user,'public.app_mfa_rotation_witness','INSERT'),has_table_privilege(current_user,'public.app_mfa_rotation_witness','UPDATE'),has_table_privilege(current_user,'public.app_mfa_rotation_witness','DELETE'),has_table_privilege(current_user,'public.app_mfa_rotation_witness','TRUNCATE')",db);
            await using var rows=await rights.ExecuteReaderAsync(Ct);Assert.True(await rows.ReadAsync(Ct));Assert.True(rows.GetBoolean(0));
            for(var i=1;i<5;i++)Assert.False(rows.GetBoolean(i));
        }
        state["verified"]=true;Save();
    }
}
