using System.Net;
using System.Net.Http.Json;
using System.Runtime.Versioning;
using System.Security.Cryptography;
using System.Security.Principal;
using System.Text.Json;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.AspNetCore.TestHost;
using Microsoft.Extensions.DependencyInjection;
using Npgsql;
using OtpNet;
using RackClick.Server;
using Xunit;

namespace RackClick.Quality.Tests;

// F0705: real Windows key composition + restricted SQL identity, with HTTP in-memory only.
// The runner creates a fresh native-name DB for each scenario. No installed host or user is touched.
[Collection("MfaHttp")]
[SupportedOSPlatform("windows")]
public sealed class MfaEnrollmentClosureTests
{
    public static bool Available=>OperatingSystem.IsWindows() && File.Exists(Environment.GetEnvironmentVariable("RACKCLICK_F0705_CONTEXT"));
    private static CancellationToken Ct=>TestContext.Current.CancellationToken;
    private const string Origin="https://rackclick.test";

    private sealed class LabIdentity(SecurityIdentifier reader,SecurityIdentifier[] trusted):IMfaHostIdentity
    {
        public SecurityIdentifier? ReaderSid=>reader;
        public IReadOnlyCollection<SecurityIdentifier> TrustedPrincipals=>trusted;
        public string Description=>"F0705-laboratory-identity";
    }

    [Fact(Skip="Dedicated fresh F0705 Windows/PG laboratory required",SkipUnless=nameof(Available))]
    public async Task RestrictedEnrollmentWorker()
    {
        using var document=JsonDocument.Parse(File.ReadAllBytes(Environment.GetEnvironmentVariable("RACKCLICK_F0705_CONTEXT")!));
        var c=document.RootElement;var id=c.GetProperty("installationId").GetGuid();var legacy=c.GetProperty("legacy").GetBoolean();
        var instances=c.GetProperty("instancesRoot").GetString()!;var runtime=c.GetProperty("runtimeConnection").GetString()!;
        var role="rc_runtime_"+id.ToString("N");var username="synthetic-enrollment-"+id.ToString("N");
        var password=Convert.ToHexString(RandomNumberGenerator.GetBytes(24));var user=Guid.NewGuid();
        var reader=new SecurityIdentifier(WellKnownSidType.BuiltinUsersSid,null);
        SecurityIdentifier[] trusted=[WindowsIdentity.GetCurrent().User!,new(WellKnownSidType.LocalSystemSid,null),new(WellKnownSidType.BuiltinAdministratorsSid,null)];
        var ring=JsonSerializer.SerializeToUtf8Bytes(new{format=MfaKeyRing.RingFormat,formatVersion=1,installationId=id,
            versions=new[]{new{version=1,state="retired",createdAtUtc="2026-11-11T00:00:00Z"},new{version=7,state="active",createdAtUtc="2026-11-11T00:00:00Z"}}});
        var keys=new[]{(1,RandomNumberGenerator.GetBytes(32)),(7,RandomNumberGenerator.GetBytes(32))};
        try{WindowsMfaKeyStoreWriter.CreateStoreFromMaterial(instances,id,reader,trusted,ring,keys);}
        finally{foreach(var entry in keys)CryptographicOperations.ZeroMemory(entry.Item2);}

        async Task<NpgsqlConnection> Connect(string? connection=null)
        {
            var db=new NpgsqlConnection(new NpgsqlConnectionStringBuilder(connection??c.GetProperty("ownerConnection").GetString()!){Pooling=false}.ConnectionString);
            await db.OpenAsync(Ct);return db;
        }
        async Task<string> Scalar(string sql,params (string,object)[] args)
        {
            await using var db=await Connect();await using var cmd=new NpgsqlCommand(sql,db);
            foreach(var (name,value) in args)cmd.Parameters.AddWithValue(name,value);
            return Convert.ToString(await cmd.ExecuteScalarAsync(Ct),System.Globalization.CultureInfo.InvariantCulture)!;
        }
        async Task Execute(string sql,params (string,object)[] args)
        {
            await using var db=await Connect();await using var cmd=new NpgsqlCommand(sql,db);
            foreach(var (name,value) in args)cmd.Parameters.AddWithValue(name,value);await cmd.ExecuteNonQueryAsync(Ct);
        }
        var house=Guid.Parse(await Scalar("SELECT id::text FROM systemhaus"));
        await Execute("""
            INSERT INTO app_user(id,systemhaus_id,username,password_hash,created_at)
            VALUES(@u,@h,@name,@hash,CASE WHEN @legacy THEN NULL ELSE clock_timestamp()-interval '46 days' END);
            INSERT INTO app_mfa_policy(systemhaus_id,enabled,grace_days,activated_at)
            VALUES(@h,true,45,clock_timestamp()-make_interval(days=>@days));
            """,("u",user),("h",house),("name",username),("hash",Secrets.PasswordHash(username,password)),("legacy",legacy),("days",legacy?46:50));
        // Test-only witness of the role/transaction actually performing HTTP writes, no tokens or factors recorded.
        await Execute($"""
            CREATE TABLE public.f0705_writes(id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,rel text NOT NULL,actor text NOT NULL,tx bigint NOT NULL);
            GRANT SELECT,INSERT ON public.f0705_writes TO {role};
            GRANT USAGE ON SEQUENCE public.f0705_writes_id_seq TO {role};
            CREATE FUNCTION public.f0705_capture() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
              INSERT INTO public.f0705_writes(rel,actor,tx) VALUES(TG_TABLE_NAME,current_user,txid_current());RETURN NEW;
            END $$;
            CREATE TRIGGER f0705_challenge AFTER INSERT OR UPDATE ON public.app_mfa_challenge FOR EACH ROW EXECUTE FUNCTION public.f0705_capture();
            CREATE TRIGGER f0705_factor AFTER INSERT OR UPDATE ON public.app_mfa_factor FOR EACH ROW EXECUTE FUNCTION public.f0705_capture();
            CREATE TRIGGER f0705_session AFTER INSERT ON public.app_session FOR EACH ROW EXECUTE FUNCTION public.f0705_capture();
            """);
        await using(var limited=await Connect(runtime))
        {
            await using var identity=new NpgsqlCommand("SELECT current_user",limited);Assert.True((string)(await identity.ExecuteScalarAsync(Ct))! == role,"Wrong runtime role");
            await using var ddl=new NpgsqlCommand("CREATE TABLE public.f0705_forbidden(id int)",limited);
            Assert.Equal("42501",(await Assert.ThrowsAsync<PostgresException>(()=>ddl.ExecuteNonQueryAsync(Ct))).SqlState);
        }
        var previousConnection=Environment.GetEnvironmentVariable("ConnectionStrings__RackClick");
        var previousOrigin=Environment.GetEnvironmentVariable("PublicOrigin");
        WebApplicationFactory<Program>? factory=null;byte[]? secret=null;
        try
        {
            Environment.SetEnvironmentVariable("ConnectionStrings__RackClick",runtime);Environment.SetEnvironmentVariable("PublicOrigin",Origin);
            factory=new WebApplicationFactory<Program>().WithWebHostBuilder(builder=>
            {
                builder.UseSetting("MfaKeyStore:Enabled","true");builder.UseSetting("MfaKeyStore:InstancesRoot",instances);
                builder.UseSetting("MfaKeyStore:InstallationId",id.ToString("D"));
                builder.ConfigureTestServices(services=>services.AddSingleton<IMfaHostIdentity>(new LabIdentity(reader,trusted)));
            });
            using var client=factory.CreateClient(new WebApplicationFactoryClientOptions{BaseAddress=new Uri(Origin),HandleCookies=false});
            async Task<HttpResponseMessage> Send(string method,string path,object? body=null,string? cookie=null,string? csrf=null)
            {
                using var request=new HttpRequestMessage(new HttpMethod(method),path);
                if(body is not null)request.Content=JsonContent.Create(body);
                if(method!="GET")request.Headers.TryAddWithoutValidation("Origin",Origin);
                if(cookie is not null)request.Headers.TryAddWithoutValidation("Cookie",cookie);
                if(csrf is not null)request.Headers.TryAddWithoutValidation("X-RackClick-CSRF",csrf);
                return await client.SendAsync(request,Ct);
            }
            string Line(HttpResponseMessage response,string name)=>response.Headers.GetValues("Set-Cookie").Single(s=>s.StartsWith(name+"=",StringComparison.Ordinal));
            string Cookie(HttpResponseMessage response,string name)=>Line(response,name).Split(';')[0];
            void NoSessionCookie(HttpResponseMessage response)=>Assert.False(response.Headers.TryGetValues("Set-Cookie",out var lines)&&lines.Any(s=>s.StartsWith("RackClick.Session=",StringComparison.Ordinal)),"Unexpected API session cookie");
            Task<string> Snapshot()=>Scalar("""
                SELECT md5(jsonb_build_object(
                  'users',(SELECT jsonb_agg(to_jsonb(u) ORDER BY id) FROM app_user u),
                  'factors',(SELECT jsonb_agg(to_jsonb(f) ORDER BY user_id) FROM app_mfa_factor f),
                  'challenges',(SELECT jsonb_agg(to_jsonb(c) ORDER BY token_hash) FROM app_mfa_challenge c),
                  'sessions',(SELECT jsonb_agg(to_jsonb(s) ORDER BY token_hash) FROM app_session s),
                  'customers',(SELECT jsonb_agg(to_jsonb(c) ORDER BY id) FROM customer c),
                  'preferences',(SELECT jsonb_agg(to_jsonb(p) ORDER BY owner_id) FROM user_preferences p),
                  'audit',(SELECT jsonb_agg(to_jsonb(a) ORDER BY id) FROM audit_event a))::text)
                """);
            async Task Restricted(string challenge,string csrf)
            {
                var before=await Snapshot();var value=challenge[(challenge.IndexOf('=')+1)..];
                foreach(var candidate in new[]{challenge,"RackClick.Session="+value})
                foreach(var (method,path,body) in new (string,string,object?)[]{("GET","/api/v1/me",null),("GET","/api/v1/customers",null),
                    ("POST","/api/v1/customers",new{name="Synthetic blocked mutation"}),("POST","/api/v1/me/preferences",new{language="en",theme="dark"})})
                {
                    using var response=await Send(method,path,body,candidate,csrf);
                    Assert.Equal(HttpStatusCode.Unauthorized,response.StatusCode);NoSessionCookie(response);
                }
                Assert.Equal(before,await Snapshot());Assert.Equal("0",await Scalar("SELECT count(*)::text FROM app_session"));
            }
            using(var wrong=await Send("POST","/api/v1/auth/login",new{username,password="intentionally-invalid-synthetic-value"}))
            {
                Assert.Equal(HttpStatusCode.Unauthorized,wrong.StatusCode);
                Assert.False(wrong.Headers.Contains("Set-Cookie"));Assert.Equal("0",await Scalar("SELECT count(*)::text FROM app_mfa_challenge"));
                Assert.Equal("0",await Scalar("SELECT count(*)::text FROM app_session"));
            }
            using var login=await Send("POST","/api/v1/auth/login",new{username,password});
            Assert.Equal(HttpStatusCode.Accepted,login.StatusCode);NoSessionCookie(login);
            var loginJson=await login.Content.ReadFromJsonAsync<JsonElement>(Ct);Assert.Equal("enroll",loginJson.GetProperty("purpose").GetString());
            var challenge=Cookie(login,"RackClick.MfaChallenge");var csrf=loginJson.GetProperty("csrf").GetString()!;
            var challengeLine=Line(login,"RackClick.MfaChallenge").ToLowerInvariant();
            foreach(var attribute in new[]{"secure","httponly","samesite=strict","path=/api/v1/auth/mfa"})Assert.Contains(attribute,challengeLine);
            Assert.Equal("true",await Scalar("SELECT mfa_required::text FROM app_mfa_user WHERE user_id=@u",("u",user)));
            await Restricted(challenge,csrf); // challenge, before any factor exists
            using var start=await Send("POST","/api/v1/auth/mfa/enroll/start",new{},challenge,csrf);
            Assert.Equal(HttpStatusCode.OK,start.StatusCode);NoSessionCookie(start);
            secret=Base32Encoding.ToBytes((await start.Content.ReadFromJsonAsync<JsonElement>(Ct)).GetProperty("secret").GetString()!);
            Assert.Equal("pending",await Scalar("SELECT state FROM app_mfa_factor WHERE user_id=@u",("u",user)));
            Assert.Equal("7",await Scalar("SELECT key_version::text FROM app_mfa_factor WHERE user_id=@u",("u",user)));
            await Restricted(challenge,csrf); // pending is still not authentication
            var accepted=new HashSet<string>(Enumerable.Range(-1,3).Select(i=>MfaTotp.Compute(secret,DateTimeOffset.UtcNow.AddSeconds(i*MfaTotp.StepSeconds))));
            var wrongCode=Enumerable.Range(0,10).Select(i=>i.ToString("D6")).First(s=>!accepted.Contains(s));
            using(var wrong=await Send("POST","/api/v1/auth/mfa/enroll/confirm",new{code=wrongCode},challenge,csrf))
            {Assert.Equal(HttpStatusCode.Unauthorized,wrong.StatusCode);NoSessionCookie(wrong);}
            await Restricted(challenge,csrf); // a rejected confirmation must not change authority
            var watermark=long.Parse(await Scalar("SELECT COALESCE(max(id),0)::text FROM f0705_writes"));
            var valid=MfaTotp.Compute(secret,DateTimeOffset.UtcNow);
            var confirms=await Task.WhenAll(Send("POST","/api/v1/auth/mfa/enroll/confirm",new{code=valid},challenge,csrf),
                Send("POST","/api/v1/auth/mfa/enroll/confirm",new{code=valid},challenge,csrf));
            try
            {
                Assert.Equal(1,confirms.Count(r=>r.StatusCode==HttpStatusCode.OK));Assert.Equal(1,confirms.Count(r=>r.StatusCode==HttpStatusCode.Unauthorized));
                var winner=confirms.Single(r=>r.StatusCode==HttpStatusCode.OK);NoSessionCookie(confirms.Single(r=>r.StatusCode==HttpStatusCode.Unauthorized));
                var session=Cookie(winner,"RackClick.Session");var sessionToken=session[(session.IndexOf('=')+1)..];
                var sessionCsrf=(await winner.Content.ReadFromJsonAsync<JsonElement>(Ct)).GetProperty("csrf").GetString()!;
                Assert.True(sessionToken!=challenge[(challenge.IndexOf('=')+1)..],"Challenge reused as session");Assert.True(sessionCsrf!=csrf,"Challenge CSRF reused");
                var sessionLine=Line(winner,"RackClick.Session").ToLowerInvariant();
                foreach(var attribute in new[]{"secure","httponly","samesite=strict","path=/"})Assert.Contains(attribute,sessionLine);
                using var me=await Send("GET","/api/v1/me",cookie:session);Assert.Equal(HttpStatusCode.OK,me.StatusCode);
                using var customers=await Send("GET","/api/v1/customers",cookie:session);Assert.Equal(HttpStatusCode.OK,customers.StatusCode);
                Assert.Equal("1",await Scalar("SELECT count(*)::text FROM app_session WHERE mfa_verified_at IS NOT NULL"));
                Assert.True(await Scalar("SELECT token_hash FROM app_session")==Secrets.Digest(sessionToken),"Session was not persisted by its digest");
                Assert.True(await Scalar("SELECT csrf_hash FROM app_session")==Secrets.Digest(sessionCsrf),"Session CSRF digest mismatch");
                Assert.Equal("active",await Scalar("SELECT state FROM app_mfa_factor WHERE user_id=@u",("u",user)));
                Assert.Equal("1",await Scalar("SELECT count(*)::text FROM app_mfa_challenge WHERE consumed_at IS NOT NULL"));
                // Same committed transaction contains factor activation, challenge consumption and session insertion.
                Assert.Equal("3",await Scalar("SELECT count(DISTINCT rel)::text FROM f0705_writes WHERE tx=(SELECT tx FROM f0705_writes WHERE rel='app_session' AND id>@mark)",("mark",watermark)));
                using var retry=await Send("POST","/api/v1/auth/mfa/enroll/confirm",new{code=valid},challenge,csrf);
                Assert.Equal(HttpStatusCode.Unauthorized,retry.StatusCode);NoSessionCookie(retry);
                Assert.Equal("1",await Scalar("SELECT count(*)::text FROM app_session"));
            }
            finally{foreach(var response in confirms)response.Dispose();}
            Assert.Equal("0",await Scalar("SELECT count(*)::text FROM f0705_writes WHERE actor<>@role",("role",role)));
            Assert.Equal("3",await Scalar("SELECT count(DISTINCT rel)::text FROM f0705_writes"));
            Assert.Equal("0",await Scalar("SELECT count(*)::text FROM customer"));
            Assert.Equal("45",await Scalar("SELECT grace_days::text FROM app_mfa_policy"));
        }
        finally
        {
            if(secret is not null)CryptographicOperations.ZeroMemory(secret);
            try{if(factory is not null)await factory.DisposeAsync();}
            finally
            {
                Environment.SetEnvironmentVariable("ConnectionStrings__RackClick",previousConnection);
                Environment.SetEnvironmentVariable("PublicOrigin",previousOrigin);
            }
        }
    }
}
