using System.Net;
using System.Security.Cryptography;
using System.Text.Json;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.AspNetCore.TestHost;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;
using Npgsql;
using OtpNet;
using RackClick.Server;
using Xunit;
using Lab = RackClick.Quality.Tests.MfaAccountManagementTests.Laboratory;

namespace RackClick.Quality.Tests;

public sealed class MfaRecoveryOpenApiTests
{
    [Fact]
    public void RecoveryAndInventoryRoutesBuildACompleteOpenApiDocument()
    {
        using var document = JsonDocument.Parse(JsonSerializer.Serialize(OpenApiDocument.Create()));
        var paths = document.RootElement.GetProperty("paths");
        var receipt = paths.GetProperty("/api/v1/me/mfa/recovery-codes/operations/{requestId}").GetProperty("get");
        Assert.Contains(receipt.GetProperty("parameters").EnumerateArray(), item =>
            item.GetProperty("name").GetString() == "requestId" && item.GetProperty("in").GetString() == "path" && item.GetProperty("required").GetBoolean());
        Assert.True(paths.GetProperty("/api/v1/me/mfa/recovery-codes").TryGetProperty("post", out _));
        Assert.True(paths.GetProperty("/api/v1/auth/mfa/recover").GetProperty("post").GetProperty("responses").TryGetProperty("202", out _));
        Assert.True(paths.GetProperty("/api/v1/customers/{id}/exports/inventory-json").TryGetProperty("post", out _));
        Assert.True(paths.GetProperty("/api/v1/customers/{id}/exports/inventory-json/operations/{requestId}").TryGetProperty("get", out _));
    }
}

[Collection("MfaHttp")]
public sealed class MfaRecoveryHttpTests
{
    [Fact]
    public async Task OwnGenerationKeepsOriginCsrfActorPasswordAndCodeFreeReplayGuards()
    {
        await using var h=await Host.Create(); var auth=await h.Enroll();
        var revision=await h.Revision(auth); var request=Guid.NewGuid();
        using(var denied=await h.Post("/api/v1/me/mfa/recovery-codes",new{password=Lab.Password},auth,revision,request,origin:"https://foreign.invalid"))Assert.Equal(HttpStatusCode.Forbidden,denied.StatusCode);
        using(var denied=await h.Post("/api/v1/me/mfa/recovery-codes",new{password=Lab.Password},auth with{Csrf="wrong"},revision,request))Assert.Equal(HttpStatusCode.Forbidden,denied.StatusCode);
        using(var denied=await h.Post("/api/v1/me/mfa/recovery-codes",new{password=Lab.Password},auth,revision,request,actor:Guid.NewGuid()))Assert.Equal(HttpStatusCode.Conflict,denied.StatusCode);
        using(var denied=await h.Post("/api/v1/me/mfa/recovery-codes",new{password="wrong-password-synthetic"},auth,revision,request))Assert.Equal(HttpStatusCode.Unauthorized,denied.StatusCode);
        Assert.Equal(0,await h.Laboratory.Count("SELECT count(*) FROM app_mfa_recovery_code"));
        var codes=await h.Generate(auth,revision,request);
        Assert.Equal(10,codes.Length);
        using var replay=await h.Post("/api/v1/me/mfa/recovery-codes",new{password=Lab.Password},auth,revision,request);
        Assert.Equal(HttpStatusCode.OK,replay.StatusCode);
        using var replayJson=JsonDocument.Parse(await replay.Content.ReadAsStringAsync(TestContext.Current.CancellationToken));
        Assert.False(replayJson.RootElement.GetProperty("codesAvailable").GetBoolean());
        Assert.Equal(JsonValueKind.Null,replayJson.RootElement.GetProperty("codes").ValueKind);
        using var receipt=await h.Get("/api/v1/me/mfa/recovery-codes/operations/"+request,auth);
        using var receiptJson=JsonDocument.Parse(await receipt.Content.ReadAsStringAsync(TestContext.Current.CancellationToken));
        Assert.True(receiptJson.RootElement.GetProperty("recorded").GetBoolean());
        Assert.Equal(JsonValueKind.Null,receiptJson.RootElement.GetProperty("result").GetProperty("codes").ValueKind);
        foreach(var code in codes)Assert.Equal(0,await h.Laboratory.Count("SELECT count(*) FROM operation WHERE position(@code in result_json::text)>0",("code",code)));
    }

    [Fact]
    public async Task RecoveryReturnsOnlyAnEnrollmentChallengeAndRevokesTheOldSession()
    {
        await using var h=await Host.Create(); var old=await h.Enroll(); var codes=await h.Generate(old,await h.Revision(old),Guid.NewGuid());
        var verify=await h.LoginChallenge();
        using var result=await h.Post("/api/v1/auth/mfa/recover",new{code=codes[0]},verify);
        Assert.Equal(HttpStatusCode.Accepted,result.StatusCode);
        Assert.DoesNotContain(result.Headers.GetValues("Set-Cookie"),v=>v.StartsWith("RackClick.Session=",StringComparison.Ordinal)&&!v.StartsWith("RackClick.Session=;",StringComparison.Ordinal));
        using var data=JsonDocument.Parse(await result.Content.ReadAsStringAsync(TestContext.Current.CancellationToken));
        Assert.Equal("enroll",data.RootElement.GetProperty("purpose").GetString());
        var enroll=new Auth(Cookie(result,"RackClick.MfaChallenge"),data.RootElement.GetProperty("csrf").GetString()!,Guid.Empty);
        using(var denied=await h.Get("/api/v1/me",old))Assert.Equal(HttpStatusCode.Unauthorized,denied.StatusCode);
        using(var denied=await h.Get("/api/v1/me",enroll))Assert.Equal(HttpStatusCode.Unauthorized,denied.StatusCode);
        Assert.Equal(0,await h.Laboratory.Count("SELECT count(*) FROM app_session"));
        Assert.Equal(0,await h.Laboratory.Count("SELECT count(*) FROM app_mfa_recovery_code WHERE consumed_at IS NULL"));
        var fresh=await h.FinishEnrollment(enroll);
        using var me=await h.Get("/api/v1/me",fresh);Assert.Equal(HttpStatusCode.OK,me.StatusCode);
        Assert.Equal(1,await h.Laboratory.Count("SELECT count(*) FROM app_session WHERE mfa_verified_at IS NOT NULL"));
    }

    [Fact]
    public async Task RecoveryOriginAndChallengeCsrfFailuresDoNotConsumeTheValidCode()
    {
        await using var h=await Host.Create();var auth=await h.Enroll();var codes=await h.Generate(auth,await h.Revision(auth),Guid.NewGuid());var challenge=await h.LoginChallenge();
        using(var bad=await h.Post("/api/v1/auth/mfa/recover",new{code=codes[0]},challenge,origin:"https://foreign.invalid"))Assert.Equal(HttpStatusCode.Forbidden,bad.StatusCode);
        using(var bad=await h.Post("/api/v1/auth/mfa/recover",new{code=codes[0]},challenge with{Csrf="wrong"}))Assert.Equal(HttpStatusCode.Forbidden,bad.StatusCode);
        Assert.Equal(10,await h.Laboratory.Count("SELECT count(*) FROM app_mfa_recovery_code WHERE consumed_at IS NULL"));
        using var good=await h.Post("/api/v1/auth/mfa/recover",new{code=codes[0]},challenge);Assert.Equal(HttpStatusCode.Accepted,good.StatusCode);
    }

    [Fact]
    public async Task BrowserCanGenerateCodesAndRecoverOnlyThroughNewAuthenticatorEnrollment()
    {
        var frontend=Environment.GetEnvironmentVariable("RACKCLICK_P3_FRONTEND");var repository=Environment.GetEnvironmentVariable("RACKCLICK_P3_REPOSITORY");
        Assert.SkipWhen(string.IsNullOrEmpty(frontend)||string.IsNullOrEmpty(repository),"Explicit PostgreSQL/frontend browser laboratory required.");
        var output=Environment.GetEnvironmentVariable("RACKCLICK_P3_MFA_OUTPUT")!;Directory.CreateDirectory(output);
        await using var h=await Host.Create(frontend);
        var start=new System.Diagnostics.ProcessStartInfo(Path.Combine(repository!,".local","node-v24.21.0-win-x64","node.exe")){UseShellExecute=false,CreateNoWindow=true,RedirectStandardOutput=true,RedirectStandardError=true,WorkingDirectory=Path.Combine(repository!,"development","frontend")};
        start.ArgumentList.Add(Path.Combine(repository!,"development","frontend","tests","browser-mfa-recovery.mjs"));
        start.Environment["RACKCLICK_TEST_ORIGIN"]=h.Origin;start.Environment["RACKCLICK_TEST_USERNAME"]="dashboard.admin";start.Environment["RACKCLICK_TEST_PASSWORD"]=Lab.Password;start.Environment["RACKCLICK_TEST_OUTPUT"]=output;
        using var process=System.Diagnostics.Process.Start(start)!;var stdout=process.StandardOutput.ReadToEndAsync(TestContext.Current.CancellationToken);var stderr=process.StandardError.ReadToEndAsync(TestContext.Current.CancellationToken);
        using var timeout=new CancellationTokenSource(TimeSpan.FromMinutes(4));
        try{await process.WaitForExitAsync(timeout.Token);}catch(OperationCanceledException){if(!process.HasExited)process.Kill(entireProcessTree:true);throw;}
        await File.WriteAllTextAsync(Path.Combine(output,"browser-process-private.log"),await stdout+"\n"+await stderr,TestContext.Current.CancellationToken);
        Assert.Equal(0,process.ExitCode);
        Assert.Equal(1,await h.Laboratory.Count("SELECT count(*) FROM app_mfa_factor WHERE state='active'"));
        Assert.Equal(0,await h.Laboratory.Count("SELECT count(*) FROM app_mfa_recovery_code WHERE consumed_at IS NULL"));
    }

    private sealed record Auth(string Cookie,string Csrf,Guid Actor);
    private static string Cookie(HttpResponseMessage response,string name)=>response.Headers.GetValues("Set-Cookie").Single(v=>v.StartsWith(name+"=",StringComparison.Ordinal)&&!v.StartsWith(name+"=;",StringComparison.Ordinal)).Split(';')[0];
    private sealed class Keys(byte[] key):IMfaKeyProvider{public byte[] GetKey(int v)=>(byte[])key.Clone();public (int Version,byte[] Key)GetActiveKey()=>(1,(byte[])key.Clone());}
    private sealed class Host:IAsyncDisposable
    {
        public Lab Laboratory=null!;private WebApplicationFactory<Program>? factory;private HttpClient? client;private readonly byte[] key=RandomNumberGenerator.GetBytes(32);private readonly Dictionary<string,string?> previous=[];
        public string Origin="https://rackclick.test";
        public static async Task<Host>Create(string? frontend=null)
        {
            var h=new Host{Laboratory=await Lab.Create()};
            try{
                await h.Laboratory.Policy(10);
                await h.Laboratory.Execute("INSERT INTO app_mfa_user(systemhaus_id,user_id,mfa_required,enrollment_pending,revision) VALUES(@house,@user,true,true,1)",("house",h.Laboratory.House),("user",h.Laboratory.Admin.Id));
                var runtime=new NpgsqlConnectionStringBuilder(h.Laboratory.RuntimeConnection).Username;
                if(!System.Text.RegularExpressions.Regex.IsMatch(runtime!,"^rc_mfa_dashboard_runtime_[a-f0-9]{32}$"))throw new InvalidOperationException("unexpected synthetic role");
                foreach(var table in new[]{"hardware_definition","hardware_mount_slot","hardware_group_template","hardware_passthrough","hardware_connector_template","hardware_profile_extension","hardware_group_extension"})await h.Laboratory.Execute($"REVOKE ALL ON {table} FROM {runtime}; GRANT SELECT ON {table} TO {runtime};");
                if(frontend is not null){var listener=new System.Net.Sockets.TcpListener(IPAddress.Loopback,0);listener.Start();h.Origin="http://127.0.0.1:"+((System.Net.IPEndPoint)listener.LocalEndpoint).Port;listener.Stop();h.Set("DevelopmentLoopbackHttp","true");}
                h.Set("ConnectionStrings__RackClick",h.Laboratory.RuntimeConnection);h.Set("MfaKeyStore__Enabled","false");h.Set("PublicOrigin",h.Origin);h.Set("RackClick__FrontendPath",frontend);
                h.factory=new WebApplicationFactory<Program>().WithWebHostBuilder(b=>{b.UseEnvironment(frontend is null?"Production":"Development");b.ConfigureLogging(l=>l.ClearProviders());b.ConfigureTestServices(s=>s.AddSingleton<IMfaKeyProvider>(new Keys(h.key)));});
                if(frontend is not null){h.factory.UseKestrel(new Uri(h.Origin).Port);h.factory.StartServer();}
                h.client=h.factory.CreateClient(new WebApplicationFactoryClientOptions{BaseAddress=new Uri(h.Origin),HandleCookies=false});return h;
            }catch{await h.DisposeAsync();throw;}
        }
        private void Set(string n,string? v){previous.TryAdd(n,Environment.GetEnvironmentVariable(n));Environment.SetEnvironmentVariable(n,v);}
        public Task<HttpResponseMessage>Get(string path,Auth auth){var request=new HttpRequestMessage(HttpMethod.Get,path);request.Headers.Add("Cookie",auth.Cookie);return client!.SendAsync(request);}
        public Task<HttpResponseMessage>Post(string path,object body,Auth? auth=null,long? revision=null,Guid? requestId=null,string? origin=null,Guid? actor=null)
        {
            var request=new HttpRequestMessage(HttpMethod.Post,path){Content=new StringContent(JsonSerializer.Serialize(body),System.Text.Encoding.UTF8,"application/json")};request.Headers.Add("Origin",origin??Origin);
            if(auth is not null){request.Headers.Add("Cookie",auth.Cookie);request.Headers.Add("X-RackClick-CSRF",auth.Csrf);request.Headers.Add("X-RackClick-Actor",(actor??auth.Actor).ToString());}
            if(revision.HasValue){request.Headers.Add("If-Match","\""+revision+"\"");request.Headers.Add("Idempotency-Key",requestId.ToString());}return client!.SendAsync(request);
        }
        public async Task<Auth>LoginChallenge(){using var login=await Post("/api/v1/auth/login",new{username="dashboard.admin",password=Lab.Password});Assert.Equal(HttpStatusCode.Accepted,login.StatusCode);using var data=JsonDocument.Parse(await login.Content.ReadAsStringAsync());return new(Cookie(login,"RackClick.MfaChallenge"),data.RootElement.GetProperty("csrf").GetString()!,Guid.Empty);}
        public async Task<Auth>Enroll()=>await FinishEnrollment(await LoginChallenge());
        public async Task<Auth>FinishEnrollment(Auth challenge)
        {
            using var start=await Post("/api/v1/auth/mfa/enroll/start",new{},challenge);Assert.Equal(HttpStatusCode.OK,start.StatusCode);using var data=JsonDocument.Parse(await start.Content.ReadAsStringAsync());byte[] secret=Base32Encoding.ToBytes(data.RootElement.GetProperty("secret").GetString()!);string code;
            try{code=new Totp(secret).ComputeTotp();}finally{CryptographicOperations.ZeroMemory(secret);}
            using var confirm=await Post("/api/v1/auth/mfa/enroll/confirm",new{code},challenge);Assert.Equal(HttpStatusCode.OK,confirm.StatusCode);using var reply=JsonDocument.Parse(await confirm.Content.ReadAsStringAsync());return new(Cookie(confirm,"RackClick.Session"),reply.RootElement.GetProperty("csrf").GetString()!,Laboratory.Admin.Id);
        }
        public async Task<long>Revision(Auth auth){using var response=await Get("/api/v1/me/mfa/recovery-codes",auth);Assert.Equal(HttpStatusCode.OK,response.StatusCode);using var json=JsonDocument.Parse(await response.Content.ReadAsStringAsync());return json.RootElement.GetProperty("revision").GetInt64();}
        public async Task<string[]>Generate(Auth auth,long revision,Guid id){using var response=await Post("/api/v1/me/mfa/recovery-codes",new{password=Lab.Password},auth,revision,id);Assert.Equal(HttpStatusCode.OK,response.StatusCode);Assert.Contains("no-store",response.Headers.CacheControl!.ToString());using var json=JsonDocument.Parse(await response.Content.ReadAsStringAsync());return json.RootElement.GetProperty("codes").EnumerateArray().Select(c=>c.GetString()!).ToArray();}
        public async ValueTask DisposeAsync(){try{client?.Dispose();if(factory is not null)await factory.DisposeAsync();}finally{try{if(Laboratory is not null)await Laboratory.DisposeAsync();}finally{foreach(var(n,v)in previous)Environment.SetEnvironmentVariable(n,v);CryptographicOperations.ZeroMemory(key);}}}
    }
}
