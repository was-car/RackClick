using System.Data;
using System.Reflection;
using System.Runtime.Versioning;
using System.Security.Cryptography;
using System.Security.Principal;
using System.Text.Json;
using Npgsql;
using RackClick.Server;
using Xunit;
using Fixture = RackClick.Quality.Tests.MfaLossResetTests.Fixture;

namespace RackClick.Quality.Tests;

[SupportedOSPlatform("windows")]
public sealed class MfaLossStartupTests
{
    private static CancellationToken Ct=>TestContext.Current.CancellationToken;
    [Fact]
    public async Task PublishedTotalLossRemainsFencedUntilExplicitCompletionThenRuntimeGuardAccepts()
    {
        using var f=await Fixture.Create();await f.Factor(7,"active",true);await f.Factor(1,"pending");
        File.Move(Key(f,1),Path.Combine(f.CaseRoot,"lost1.private"));File.Move(Key(f,7),Path.Combine(f.CaseRoot,"lost7.private"));
        await f.Initialize();await f.Run("prepare",[1,7]);var envelope=await f.Export();
        try{await f.Run("apply",envelope:envelope);await f.Run("publish");}finally{CryptographicOperations.ZeroMemory(envelope);}
        Assert.True(File.Exists(f.Fence));await Assert.ThrowsAsync<MfaMaintenanceException>(()=>Guard(f));
        var result=await f.Run("complete");Assert.Equal("data_verified_released",result.Phase);Assert.False(File.Exists(f.Fence));
        await Guard(f);await f.Run("complete");await Guard(f);
        Assert.Equal(0,await f.Count("SELECT count(*) FROM app_mfa_factor"));Assert.Equal(2,await f.Count("SELECT count(*) FROM app_mfa_user WHERE enrollment_pending"));
        Assert.False(File.Exists(Key(f,1)));Assert.False(File.Exists(Key(f,7)));
    }
    [Theory][InlineData("receipt")][InlineData("witness")][InlineData("key")]
    public async Task MissingOrAlteredPublicationCannotBecomeAUsableStartup(string target)
    {
        using var f=await Fixture.Create();await f.Factor(7,"active");await Reset(f);await f.Run("complete");
        if(target=="receipt")File.WriteAllText(Path.Combine(f.Instances,f.Id.ToString("D"),"mfa-loss-state.json"),"{}");
        if(target=="witness")await f.Exec("UPDATE rackclick_private.mfa_loss_operation SET envelope_sha256=repeat('f',64)");
        if(target=="key")File.WriteAllText(Key(f,8),"corrupt fixture");
        await Assert.ThrowsAnyAsync<Exception>(()=>Guard(f));
    }
    [Fact]
    public async Task RuntimeProjectionContainsOnlyMetadataAndCannotBeWrittenEvenWithPublicDmlGrant()
    {
        using var f=await Fixture.Create();await f.Factor(7,"active");await Reset(f);await f.Run("complete");
        await using var db=new NpgsqlConnection(f.RuntimeConnection);await db.OpenAsync(Ct);
        await using(var read=new NpgsqlCommand("SELECT count(*) FROM public.app_mfa_loss_startup_witness",db))Assert.Equal(1L,await read.ExecuteScalarAsync(Ct));
        foreach(var sql in new[]{"UPDATE public.app_mfa_loss_startup_witness SET new_version=999","DELETE FROM public.app_mfa_loss_startup_witness"})
        {await using var change=new NpgsqlCommand(sql,db);Assert.Equal("55000",(await Assert.ThrowsAsync<PostgresException>(()=>change.ExecuteNonQueryAsync(Ct))).SqlState);}
        await using var archive=new NpgsqlCommand("SELECT factor_row FROM rackclick_private.mfa_loss_factor_archive",db);
        Assert.Equal("42501",(await Assert.ThrowsAsync<PostgresException>(()=>archive.ExecuteNonQueryAsync(Ct))).SqlState);
    }
    [Fact]
    public async Task NativeServiceRootIsDerivedFromBoundSecurityLayoutNotUsedAsKeyRoot()
    {
        var id=Guid.NewGuid();var root=Path.Combine(Path.GetTempPath(),"native-loss-layout");var security=Path.Combine(root,id.ToString("D"),"security");
        var method=typeof(MfaLossResetCoordinator).GetMethod("NativeServiceRoot",BindingFlags.Static|BindingFlags.NonPublic);Assert.NotNull(method);
        Assert.Equal(root,method.Invoke(null,[security,id]));
        foreach(var invalid in new[]{Path.Combine(root,id.ToString("D"),"other"),Path.Combine(root,Guid.NewGuid().ToString("D"),"security")})
            Assert.IsType<MfaMaintenanceException>(Assert.Throws<TargetInvocationException>(()=>method.Invoke(null,[invalid,id])).InnerException);
    }
    [Fact]
    public async Task ApprovedWriterAndMaintenanceCanUseDeepLocalPathsWithoutDroppingAclOrIdentityChecks()
    {
        using var f=await Fixture.Create();var parent=Path.Combine(f.CaseRoot,new string('n',110));Directory.CreateDirectory(parent);var root=Path.Combine(parent,"security");
        var ring=File.ReadAllBytes(f.RingPath);WindowsMfaKeyStoreWriter.CreateStoreFromMaterial(root,f.Id,f.Reader,f.Trusted,ring,f.Keys.Select(p=>(p.Key,p.Value)).ToArray());
        var provider=new WindowsMfaKeyProvider(root,f.Id,f.Reader,f.Trusted);var active=provider.GetActiveKey();try{Assert.Equal(1,active.Version);}finally{CryptographicOperations.ZeroMemory(active.Key);}
        using var store=new WindowsMfaMaintenanceStore(root,f.Id,f.Reader,f.Trusted);using var held=store.AcquireLock();Assert.Equal(ring,store.ReadRing());
    }
    [Theory][InlineData("before_loss_startup_receipt")][InlineData("after_loss_startup_receipt")][InlineData("before_loss_release")][InlineData("after_loss_release")]
    public async Task CompletionInterruptionReentersUsingItsOwnReceiptAndFenceIdentity(string cut)
    {
        using var f=await Fixture.Create();await f.Factor(7,"active");await Reset(f);
        await Assert.ThrowsAsync<LogicalCut>(()=>f.Run("complete",checkpoint:s=>{if(s==cut)throw new LogicalCut();}));
        Assert.Equal(cut!="after_loss_release",File.Exists(f.Fence));await f.Run("complete");await Guard(f);Assert.False(File.Exists(f.Fence));
    }
    [Theory][InlineData(false)][InlineData(true)]
    public async Task MostRecentModeDeterminesMaterialWithoutDiscardingTheOtherHistory(bool rotationFirst)
    {
        using var f=await Fixture.Create();await f.Factor(7,"active");await f.Initialize();
        if(rotationFirst)await Rotate(f);
        var lost=rotationFirst?new[]{1,7,8}:new[]{7};foreach(var version in lost)f.Lose(version);
        await f.Run("prepare",lost);var envelope=await f.Export();try{await f.Run("apply",envelope:envelope);await f.Run("publish");}finally{CryptographicOperations.ZeroMemory(envelope);}
        await f.Run("complete");await Guard(f);
        if(!rotationFirst){await Rotate(f);await Guard(f);}
        Assert.Equal(1,await f.Count("SELECT count(*) FROM rackclick_private.mfa_loss_operation"));Assert.Equal(1,await f.Count("SELECT count(*) FROM app_mfa_rotation_witness"));
        if(!rotationFirst)
        {
            File.WriteAllText(Path.Combine(f.Instances,f.Id.ToString("D"),"mfa-loss-state.json"),"{}");
            await Assert.ThrowsAsync<MfaMaintenanceException>(()=>Guard(f));
        }
    }
    [Fact]
    public async Task MissingProjectionInSchema48FailsClosedAndLegitimateNewSecurityDoesNotInvalidateACompletedLoss()
    {
        using var f=await Fixture.Create();var user=await f.Factor(7,"active");await Reset(f);await f.Run("complete");
        var active=f.Provider.GetActiveKey();var secret=RandomNumberGenerator.GetBytes(20);
        try{await f.Exec("INSERT INTO app_mfa_factor(systemhaus_id,user_id,state,secret_ciphertext,key_version) VALUES(@house,@user,'pending',@cipher,@version)",("house",f.House),("user",user),("cipher",MfaSecretCipher.Seal(active.Key,active.Version,secret,f.House,user)),("version",active.Version));}
        finally{CryptographicOperations.ZeroMemory(active.Key);CryptographicOperations.ZeroMemory(secret);}
        await Guard(f);await f.Run("complete");await f.Exec("DROP VIEW public.app_mfa_loss_startup_witness");
        Assert.Equal("mfa_loss_startup_projection_missing",(await Assert.ThrowsAsync<MfaMaintenanceException>(()=>Guard(f))).Code);
    }
    private sealed class LogicalCut:Exception;
    [Fact]
    public async Task MissingProjectionWithEmptyHistoryIsAnExplicitFailureNotAnUnhandledCast()
    {
        using var f=await Fixture.Create();await f.Exec("DROP VIEW public.app_mfa_loss_startup_witness;TRUNCATE public.schema_migration");
        Assert.Equal("mfa_loss_startup_projection_missing",(await Assert.ThrowsAsync<MfaMaintenanceException>(()=>Guard(f))).Code);
    }
    [Fact]
    public async Task CompletionMustNotReleaseFenceWithoutItsRuntimeMetadataProjection()
    {
        using var f=await Fixture.Create();await f.Factor(7,"active");await Reset(f);
        await f.Exec("DROP VIEW public.app_mfa_loss_startup_witness");
        Assert.Equal("mfa_loss_startup_projection_missing",(await Assert.ThrowsAsync<MfaMaintenanceException>(()=>f.Run("complete"))).Code);
        Assert.True(File.Exists(f.Fence));Assert.False(File.Exists(Path.Combine(f.Instances,f.Id.ToString("D"),"mfa-loss-state.json")));
    }
    [Fact]
    public async Task CompletionMustNotReleaseFenceWhenRuntimeCannotReadItsProjection()
    {
        using var f=await Fixture.Create();await f.Factor(7,"active");await Reset(f);
        await f.Exec("REVOKE ALL ON public.app_mfa_loss_startup_witness FROM \"rc_runtime_"+f.Id.ToString("N")+"\"");
        Assert.Equal("mfa_loss_startup_projection_unreadable",(await Assert.ThrowsAsync<MfaMaintenanceException>(()=>f.Run("complete"))).Code);
        Assert.True(File.Exists(f.Fence));
    }
    private static async Task Rotate(Fixture f)
    {
        string hash;using(var storage=new WindowsMfaMaintenanceStore(f.Instances,f.Id,f.Reader,f.Trusted))using(storage.AcquireLock())hash=Convert.ToHexStringLower(SHA256.HashData(storage.ReadCatalog()));
        var request=new MfaMaintenanceRequest("rotate",f.OwnerConnection,f.Instances,f.Id,f.Reader,hash,0,Guid.NewGuid(),null);
        await MfaRotationCoordinator.PrepareAsync(request,f.Trusted,null,Ct);var password=Convert.ToHexString(RandomNumberGenerator.GetBytes(32));
        var envelope=await MfaRotationCoordinator.ExportAsync(request,f.Trusted,password,Ct);
        try{await MfaRotationCoordinator.ResumeAsync(request,f.Trusted,envelope,password,Convert.ToHexStringLower(SHA256.HashData(envelope)),null,Ct);}finally{CryptographicOperations.ZeroMemory(envelope);}
    }
    private static string Key(Fixture f,int version)=>Path.Combine(Path.GetDirectoryName(f.RingPath)!,MfaKeyRing.KeyFileName(version));
    internal static async Task Reset(Fixture f)
    {f.Lose(7);await f.Initialize();await f.Run("prepare",[7]);var envelope=await f.Export();try{await f.Run("apply",envelope:envelope);await f.Run("publish");}finally{CryptographicOperations.ZeroMemory(envelope);}}
    internal static async Task Guard(Fixture f)
    {
        await using var db=new NpgsqlConnection(f.RuntimeConnection);await db.OpenAsync(Ct);
        await MfaRotationStartupGuard.ValidateAsync(db,f.Instances,f.Id,f.Reader,f.Trusted,f.Provider,Ct);
    }
}
