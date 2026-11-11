using System.Reflection;
using System.Runtime.Versioning;
using System.Security.Principal;
using System.Text.Json;
using RackClick.Server;
using Xunit;

namespace RackClick.Quality.Tests;

[SupportedOSPlatform("windows")]
public sealed class MfaLossRecoveryCommandTests
{
    private static readonly Guid Id=Guid.Parse("1f690b0d-cabf-40af-983c-d2d9852a92c7"),Op=Guid.Parse("51898610-a769-429d-90ed-cc982bb2ab36");
    private static Dictionary<string,object> Request(string action="prepare")
    {
        var value=new Dictionary<string,object>{["action"]=action,["ownerConnection"]="Host=127.0.0.1;Database=synthetic;Username=owner;Password=synthetic-not-used",
            ["instancesRoot"]=@"C:\synthetic\"+Id+@"\security",["installationId"]=Id.ToString("D"),["readerSid"]="S-1-5-21-11-22-33-1001",
            ["serviceName"]="RackClick-Synthetic",["expectedCatalogSha256"]=new string('a',64),["operationId"]=Op.ToString("D"),
            ["confirmation"]=$"CONFIRMO PERDIDA {Id:D} {Op:D} {action}"};
        if(action=="prepare")value["lostVersions"]=new[]{1,7};
        if(action is "export" or "apply") {value["envelopeReaderSid"]="S-1-5-21-11-22-33-1002";value["password"]="synthetic-recovery-password-only";}
        if(action=="export"){value["envelopeFolder"]=@"C:\custody";value["envelopeName"]="new-material.rckey";}
        if(action=="apply"){value["envelopePath"]=@"C:\custody\new-material.rckey";value["expectedEnvelopeSha256"]=new string('b',64);}
        return value;
    }
    private static object Parse(string text)
    {
        var type=typeof(MfaKeyRing).Assembly.GetType("RackClick.Server.MfaLossRecoveryCommand");Assert.NotNull(type);
        var method=type.GetMethod("Parse",BindingFlags.NonPublic|BindingFlags.Static);Assert.NotNull(method);
        try{return method.Invoke(null,[text])!;}catch(TargetInvocationException e)when(e.InnerException is not null){System.Runtime.ExceptionServices.ExceptionDispatchInfo.Capture(e.InnerException).Throw();throw;}
    }
    [Theory][InlineData("prepare")][InlineData("export")][InlineData("apply")][InlineData("publish")][InlineData("complete")]
    public void ExplicitClosedStageParsesWithoutOpeningFilesSqlOrService(string action)=>Assert.NotNull(Parse(JsonSerializer.Serialize(Request(action))));
    [Theory][InlineData("unknown")][InlineData("duplicate")][InlineData("case")][InlineData("confirmation")][InlineData("path")]
    [InlineData("unicode-name")][InlineData("unicode-value")][InlineData("surrogate")][InlineData("over-limit")][InlineData("reader")]
    [InlineData("zero")][InlineData("lost-duplicate")][InlineData("lost-empty")][InlineData("lost-fraction")][InlineData("hash")]
    public void InvalidShapeOrAuthorityCannotReachMaintenance(string mutation)
    {
        var r=Request();string? text=null;
        switch(mutation)
        {
            case "unknown":r["trustedSid"]="S-1-5-18";break;
            case "duplicate":text=JsonSerializer.Serialize(r).Replace("\"action\":\"prepare\"","\"action\":\"prepare\",\"action\":\"prepare\"",StringComparison.Ordinal);break;
            case "case":r["Action"]=r["action"];r.Remove("action");break;
            case "confirmation":r["confirmation"]="CONFIRMO";break;
            case "path":r["instancesRoot"]=@"C:\synthetic\wrong\security";break;
            case "unicode-name":text=JsonSerializer.Serialize(r).Replace("\"action\"","\"\\uD800\"",StringComparison.Ordinal);break;
            case "unicode-value":text=JsonSerializer.Serialize(r).Replace("\"prepare\"","\"\\uDC00\"",StringComparison.Ordinal);break;
            case "surrogate":text="\ud800";break;
            case "over-limit":text=new string(' ',65537);break;
            case "reader":r["readerSid"]="S-1-5-18";break;
            case "zero":r["operationId"]=Guid.Empty.ToString("D");break;
            case "lost-duplicate":r["lostVersions"]=new[]{7,7};break;
            case "lost-empty":r["lostVersions"]=Array.Empty<int>();break;
            case "lost-fraction":r["lostVersions"]=new[]{1.5};break;
            case "hash":r["expectedCatalogSha256"]=new string('A',64);break;
        }
        var e=Assert.Throws<MfaMaintenanceException>(()=>Parse(text??JsonSerializer.Serialize(r)));
        Assert.Equal("mfa_emergency_input_invalid",e.Code);Assert.DoesNotContain("synthetic",e.Message,StringComparison.OrdinalIgnoreCase);
    }
    [Fact]
    public void CustodianMustDifferFromServiceAndFixedTrust()
    {
        foreach(var sid in new[]{"S-1-5-21-11-22-33-1001","S-1-5-18","S-1-5-32-544"})
        {var r=Request("export");r["envelopeReaderSid"]=sid;Assert.Throws<MfaMaintenanceException>(()=>Parse(JsonSerializer.Serialize(r)));}
    }
    [Fact]
    public void ExternalEnvelopeMustNotOverlapAnyDeclaredBackupRootOrNativeInstances()
    {
        var method=typeof(MfaKeyRing).Assembly.GetType("RackClick.Server.MfaLossResetCoordinator",true)!.GetMethod("RequireExternalEnvelopeFolder",BindingFlags.Static|BindingFlags.NonPublic);Assert.NotNull(method);
        string[] excluded=[@"C:\instances",@"D:\retained"];
        foreach(var path in new[]{@"C:\instances",@"C:\instances\private",@"C:\",@"D:\retained\new",@"D:\retained"})
        {var e=Assert.Throws<TargetInvocationException>(()=>method.Invoke(null,[path,excluded]));Assert.IsType<MfaMaintenanceException>(e.InnerException);}
        method.Invoke(null,[@"C:\instances-other",excluded]);method.Invoke(null,[@"D:\custody",excluded]);
    }
    [Fact]
    public async Task UnauthorizedNativeCallerNeverReadsStdinOrUsesAConfigurationSeam()
    {
        var authority=typeof(MfaKeyRing).Assembly.GetType("RackClick.Server.MfaEmergencyRecoveryCommand",true)!;
        var denied=(string?)authority.GetMethod("AuthorizationFailure",BindingFlags.NonPublic|BindingFlags.Static)!.Invoke(null,null);
        Assert.SkipWhen(denied is null,"Native elevated token belongs in the isolated VM trial, not this fixture");
        var type=typeof(MfaKeyRing).Assembly.GetType("RackClick.Server.MfaLossRecoveryCommand",true)!;
        using var writer=new StringWriter();var task=(Task<int>)type.GetMethod("RunAsync",BindingFlags.NonPublic|BindingFlags.Static)!.Invoke(null,[new NoRead(),writer,TestContext.Current.CancellationToken])!;
        Assert.Equal(1,await task);using var json=JsonDocument.Parse(writer.ToString());Assert.Equal(denied,json.RootElement.GetProperty("code").GetString());
        Assert.Equal(0,json.RootElement.GetProperty("operationsApplied").GetInt32());Assert.False(json.RootElement.GetProperty("sessionGranted").GetBoolean());
    }
    private sealed class NoRead:TextReader
    {public override ValueTask<int> ReadAsync(Memory<char> buffer,CancellationToken cancellationToken=default)=>throw new InvalidOperationException("stdin must not be read");}
}
