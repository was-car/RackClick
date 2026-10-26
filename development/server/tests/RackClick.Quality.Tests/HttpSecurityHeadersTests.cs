using Microsoft.AspNetCore.Http;
using RackClick.Server;
using Xunit;

namespace RackClick.Quality.Tests;

public sealed class HttpSecurityHeadersTests
{
    [Fact]
    public void SuccessAndErrorResponsesPreserveCspAndDoNotEnableCors()
    {
        const string csp = "default-src 'self'; script-src 'self'; object-src 'none'";
        const string reportOnly = "default-src 'none'; report-uri /report";

        foreach (int status in new[] { 200, 401, 404, 500 })
        {
            var context = Context("https", "untrusted.example");
            context.Response.StatusCode = status;
            context.Response.Headers.ContentSecurityPolicy = csp;
            context.Response.Headers["Content-Security-Policy-Report-Only"] = reportOnly;

            HttpSecurityHeaders.Apply(context, new Uri("https://rackclick.example:5443"), false);

            Assert.Equal("no-referrer", context.Response.Headers["Referrer-Policy"].ToString());
            Assert.Equal("DENY", context.Response.Headers.XFrameOptions.ToString());
            Assert.Equal("camera=(), microphone=(), geolocation=()",
                context.Response.Headers["Permissions-Policy"].ToString());
            Assert.Equal(csp, context.Response.Headers.ContentSecurityPolicy.ToString());
            Assert.Equal(reportOnly, context.Response.Headers["Content-Security-Policy-Report-Only"].ToString());
            Assert.DoesNotContain(context.Response.Headers.Keys,
                key => key.StartsWith("Access-Control-", StringComparison.OrdinalIgnoreCase));
            Assert.Equal(status, context.Response.StatusCode);
        }
    }

    [Fact]
    public void PublicDnsOriginWithRealTlsUsesOnlyOneDayHsts()
    {
        var context = Context("https", "rackclick.example:5443");

        HttpSecurityHeaders.Apply(context, new Uri("https://rackclick.example:5443"), false);

        // Equality also rejects includeSubDomains, preload, or duplicate values.
        Assert.Equal("max-age=86400", context.Response.Headers.StrictTransportSecurity.ToString());
    }

    [Theory]
    [InlineData("https://rackclick.example:5443", "http", false)]
    [InlineData("https://192.0.2.8:5443", "https", false)]
    [InlineData("https://[2001:db8::8]:5443", "https", false)]
    [InlineData("https://localhost:5443", "https", false)]
    [InlineData("https://127.0.0.1:5443", "https", false)]
    [InlineData("https://[::1]:5443", "https", false)]
    [InlineData("https://rackclick.example:5443", "https", true)]
    [InlineData("http://rackclick.example:5443", "https", false)]
    public void UnsafeOrDevelopmentProfilesNeverEmitHsts(string origin, string actualScheme, bool developmentHttp)
    {
        // Neither the client Host nor a forwarded hint can opt an IP/local profile into HSTS.
        var context = Context(actualScheme, "public-client-host.example");
        context.Request.Headers["X-Forwarded-Proto"] = "https";
        context.Request.Headers["X-Forwarded-Host"] = "another-public-host.example";

        HttpSecurityHeaders.Apply(context, new Uri(origin), developmentHttp);

        Assert.False(context.Response.Headers.ContainsKey("Strict-Transport-Security"));
        Assert.Equal("no-referrer", context.Response.Headers["Referrer-Policy"].ToString());
        Assert.Equal("DENY", context.Response.Headers.XFrameOptions.ToString());
    }

    private static DefaultHttpContext Context(string scheme, string host)
    {
        var context = new DefaultHttpContext();
        context.Request.Scheme = scheme;
        context.Request.Host = new HostString(host);
        return context;
    }
}
