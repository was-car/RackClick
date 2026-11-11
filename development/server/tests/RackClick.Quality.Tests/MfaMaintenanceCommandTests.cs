using System.Reflection;
using System.Runtime.Versioning;
using System.Security.Principal;
using RackClick.Server;
using Xunit;

namespace RackClick.Quality.Tests;

[SupportedOSPlatform("windows")]
public sealed class MfaMaintenanceCommandTests
{
    [Fact]
    public void MaintenanceRequestDoesNotExposeSqlMaterialInItsStringRepresentation()
    {
        var material=Convert.ToHexString(System.Security.Cryptography.RandomNumberGenerator.GetBytes(32));
        var request=new MfaMaintenanceRequest("check","Password="+material,Path.GetTempPath(),Guid.NewGuid(),WindowsIdentity.GetCurrent().User!,new string('a',64),0,Guid.Empty,null);
        Assert.Equal("MfaMaintenanceRequest(redacted)",request.ToString());Assert.DoesNotContain(material,request.ToString());
    }
    [Fact]
    public async Task UnelevatedInvocationIsRejectedBeforeReadingInput()
    {
        using var output=new StringWriter();
        var code=await Invoke(new MustNotRead(),output,false);
        Assert.Equal(1,code);Assert.Contains("mfa_maintenance_not_elevated",output.ToString());
    }

    [Theory]
    [InlineData("")]
    [InlineData("{}")]
    [InlineData("[]")]
    [InlineData("{\"action\":\"retire\",\"action\":\"check\"}")]
    [InlineData("{\"action\":\"\\ud800\"}")]
    [InlineData("{\"\\udfff\":\"retire\"}")]
    [InlineData("{\"action\":\"invented-untrusted-text\"}")]
    public async Task InvalidLocalProtocolDoesNotEchoInputOrTouchTheHost(string input)
    {
        using var output=new StringWriter();
        Assert.Equal(1,await Invoke(new StringReader(input),output,true));
        Assert.Equal("{\"status\":\"rejected\",\"code\":\"mfa_maintenance_input_invalid\",\"maintenanceState\":\"inspect_before_retry\"}"+Environment.NewLine,output.ToString());
    }

    private static Task<int> Invoke(TextReader input,TextWriter output,bool elevated)
    {
        var type=typeof(MfaKeyRing).Assembly.GetType("RackClick.Server.MfaMaintenanceCommand");Assert.NotNull(type);
        var method=type.GetMethods(BindingFlags.Static|BindingFlags.NonPublic).Single(m=>m.Name=="RunAsync");
        var trusted=new[]{WindowsIdentity.GetCurrent().User!};
        return (Task<int>)method.Invoke(null,[input,output,elevated,trusted,CancellationToken.None])!;
    }

    [Theory]
    [InlineData("\"1\"")]
    [InlineData("null")]
    [InlineData("{}")]
    [InlineData("[]")]
    [InlineData("true")]
    public async Task NonNumericCandidateIsASanitizedRejection(string candidate)
    {
        const string id="fb118060-8a8f-49f2-a3d0-a1f467fb6e2b";
        var input="{\"action\":\"retire\",\"serviceName\":\"synthetic-not-queried\",\"ownerConnection\":\"invalid-untrusted-connection\",\"instancesRoot\":\"C:\\\\untrusted-fixture\",\"installationId\":\""+id+"\",\"readerSid\":\"S-1-5-21-11-22-33-1001\",\"expectedCatalogSha256\":\""+new string('a',64)+"\",\"operationId\":\"ccfaf4fd-f20e-4b60-ad5e-2ea0d8fa9ce8\",\"confirmation\":\"CONFIRMO RETIRADA "+id+" v1\",\"candidate\":"+candidate+"}";
        using var output=new StringWriter();Assert.Equal(1,await Invoke(new StringReader(input),output,true));
        Assert.Contains("mfa_maintenance_input_invalid",output.ToString());Assert.DoesNotContain("untrusted",output.ToString());
    }

    private sealed class MustNotRead:TextReader
    {
        public override int Read()=>throw new InvalidOperationException("input_was_read");
        public override ValueTask<int> ReadAsync(Memory<char> buffer,CancellationToken cancellationToken=default)=>throw new InvalidOperationException("input_was_read");
    }
}
