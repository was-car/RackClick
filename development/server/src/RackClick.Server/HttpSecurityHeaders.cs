namespace RackClick.Server;

/// <summary>Browser protections shared by successful and rejected responses.</summary>
public static class HttpSecurityHeaders
{
    public static void Apply(HttpContext context, Uri configuredOrigin, bool developmentHttp)
    {
        context.Response.Headers["Referrer-Policy"] = "no-referrer";
        context.Response.Headers["X-Frame-Options"] = "DENY";
        context.Response.Headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()";

        // Start with one day and no subdomain/preload commitment. LAN installations
        // commonly use IP certificates; HSTS is a domain policy, not an IP policy.
        // Never let a request Host header decide which origin receives this policy.
        if (!developmentHttp && context.Request.IsHttps &&
            configuredOrigin.Scheme == Uri.UriSchemeHttps && !configuredOrigin.IsLoopback &&
            configuredOrigin.HostNameType == UriHostNameType.Dns)
            context.Response.Headers.StrictTransportSecurity = "max-age=86400";
    }
}
