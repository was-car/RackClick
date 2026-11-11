using System.Net;
using System.Text.Json;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.Extensions.Logging;
using Xunit;
using Lab = RackClick.Quality.Tests.MfaAccountManagementTests.Laboratory;

namespace RackClick.Quality.Tests;

[Collection("MfaHttp")]
public sealed class MfaEmergencyHttpTests
{
    [Fact]
    public async Task NeitherAnonymousRequestsNorAGlobalApplicationAdministratorCanInvokeLocalEmergencyOverHttp()
    {
        await using var lab = await Lab.Create();
        var previous = new Dictionary<string, string?>();
        void Set(string name, string value) { previous[name] = Environment.GetEnvironmentVariable(name); Environment.SetEnvironmentVariable(name, value); }
        try
        {
            Set("ConnectionStrings__RackClick", lab.RuntimeConnection);
            Set("MfaKeyStore__Enabled", "false");
            Set("PublicOrigin", "https://rackclick.test");
            await using var factory = new WebApplicationFactory<Program>().WithWebHostBuilder(b =>
            { b.UseEnvironment("Production"); b.ConfigureLogging(l => l.ClearProviders()); });
            using var client = factory.CreateClient(new WebApplicationFactoryClientOptions
            { BaseAddress = new Uri("https://rackclick.test"), HandleCookies = false, AllowAutoRedirect = false });
            using var loginRequest = Post("/api/v1/auth/login", JsonSerializer.Serialize(new { username = lab.Admin.UserName, password = Lab.Password }));
            using var login = await client.SendAsync(loginRequest, TestContext.Current.CancellationToken);
            Assert.Equal(HttpStatusCode.OK, login.StatusCode);
            using var loginBody = JsonDocument.Parse(await login.Content.ReadAsStringAsync(TestContext.Current.CancellationToken));
            string cookie = login.Headers.GetValues("Set-Cookie").Single(c => c.StartsWith("RackClick.Session=", StringComparison.Ordinal)).Split(';')[0];
            string csrf = loginBody.RootElement.GetProperty("csrf").GetString()!;
            var before = await lab.SnapshotAll();
            foreach (string route in new[] { "/api/v1/auth/mfa/emergency", "/api/v1/auth/mfa/loss-reset", "/api/v1/admin/mfa/emergency", "/api/v1/mfa/emergency-recovery" })
            {
                using var anonymousRequest = Post(route, "{\"action\":\"loss-reset\",\"authorized\":true,\"system\":true}");
                using var anonymous = await client.SendAsync(anonymousRequest, TestContext.Current.CancellationToken);
                Assert.Equal(HttpStatusCode.Unauthorized, anonymous.StatusCode);
                using var adminRequest = Post(route, "{\"action\":\"loss-reset\",\"authorized\":true,\"system\":true}");
                adminRequest.Headers.Add("Cookie", cookie); adminRequest.Headers.Add("X-RackClick-CSRF", csrf);
                adminRequest.Headers.Add("X-RackClick-Actor", lab.Admin.Id.ToString("D"));
                using var admin = await client.SendAsync(adminRequest, TestContext.Current.CancellationToken);
                Assert.Equal(HttpStatusCode.NotFound, admin.StatusCode);
            }
            Assert.Equal(before, await lab.SnapshotAll());
        }
        finally { foreach (var item in previous) Environment.SetEnvironmentVariable(item.Key, item.Value); }
    }

    private static HttpRequestMessage Post(string route, string body)
    {
        var request = new HttpRequestMessage(HttpMethod.Post, route)
        { Content = new StringContent(body, System.Text.Encoding.UTF8, "application/json") };
        request.Headers.Add("Origin", "https://rackclick.test");
        return request;
    }
}
