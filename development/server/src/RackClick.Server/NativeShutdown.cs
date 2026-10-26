using System.IO.Pipes;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

namespace RackClick.Server;

/// <summary>Opt-in, private Windows control channel. It does not expose an HTTP command.</summary>
public static class NativeShutdown
{
    public static IServiceCollection AddNativeShutdown(this IServiceCollection services, IConfiguration configuration)
    {
        string? pipe = configuration["RackClick:ShutdownPipe"];
        string? token = configuration["RackClick:ShutdownToken"];
        if (pipe is null && token is null) return services;
        const string prefix = "rc-shutdown-";
        if (!OperatingSystem.IsWindows() || pipe is null || token is null ||
            !pipe.StartsWith(prefix, StringComparison.Ordinal) ||
            !Guid.TryParseExact(pipe[prefix.Length..], "N", out var id) || id == Guid.Empty ||
            pipe != prefix + id.ToString("N") || !IsToken(token))
            throw new InvalidOperationException("Native shutdown configuration is invalid.");

        services.Configure<HostOptions>(options => options.ShutdownTimeout = TimeSpan.FromSeconds(15));
        services.AddSingleton<IHostedService>(provider => new NativeShutdownService(
            pipe, token, provider.GetRequiredService<IHostApplicationLifetime>()));
        return services;
    }

    internal static bool IsToken(string value) => value.Length == 64 &&
        value.All(character => character is >= '0' and <= '9' or >= 'a' and <= 'f');
}

internal sealed class NativeShutdownService(string pipeName, string token, IHostApplicationLifetime lifetime) : BackgroundService
{
    private const int MaximumLineBytes = 256;
    private static readonly byte[] Accepted = Encoding.ASCII.GetBytes("{\"schemaVersion\":1,\"accepted\":true}\n");
    private static readonly byte[] Rejected = Encoding.ASCII.GetBytes("{\"schemaVersion\":1,\"accepted\":false}\n");
    private readonly byte[] expectedToken = Encoding.ASCII.GetBytes(token);
    private NamedPipeServerStream? pipe;

    public override Task StartAsync(CancellationToken cancellationToken)
    {
        // Fail startup if the private channel cannot be bound. Keep this same
        // first instance across rejected clients, so its name is never released.
        pipe = new NamedPipeServerStream(pipeName, PipeDirection.InOut, 1,
            PipeTransmissionMode.Byte, PipeOptions.Asynchronous | PipeOptions.CurrentUserOnly | PipeOptions.FirstPipeInstance);
        return base.StartAsync(cancellationToken);
    }

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        var channel = pipe ?? throw new InvalidOperationException("Native shutdown channel is unavailable.");
        try
        {
            while (!stoppingToken.IsCancellationRequested)
            {
                // Infrastructure errors here stop the host through the default
                // BackgroundService policy; never leave a live uncontrolled host.
                await channel.WaitForConnectionAsync(stoppingToken);
                using var clientDeadline = CancellationTokenSource.CreateLinkedTokenSource(stoppingToken);
                clientDeadline.CancelAfter(TimeSpan.FromSeconds(3));
                bool accepted = false;
                try
                {
                    byte[]? request = await ReadLine(channel, clientDeadline.Token);
                    accepted = request is not null && IsStop(request);
                    await channel.WriteAsync(accepted ? Accepted : Rejected, clientDeadline.Token);
                    await channel.FlushAsync(clientDeadline.Token);
                    // PipeStream.FlushAsync does not wait for client consumption.
                    // Retain the connection until the client closes after its ACK.
                    // No extra data or unbounded WaitForPipeDrain is permitted.
                    byte[] completion = new byte[1];
                    bool closed = await channel.ReadAsync(completion, clientDeadline.Token) == 0;
                    if (accepted && closed)
                    {
                        // The acknowledgement is on the channel before Kestrel
                        // begins draining requests through normal host shutdown.
                        lifetime.StopApplication();
                        return;
                    }
                }
                catch (OperationCanceledException) when (clientDeadline.IsCancellationRequested) { }
                catch (IOException) { /* Disconnected client; no request content is logged. */ }
                finally
                {
                    // EOF can mark PipeState.Broken, making IsConnected false.
                    // Disconnect also resets that state for the next client.
                    channel.Disconnect();
                }
            }
        }
        catch (OperationCanceledException) when (stoppingToken.IsCancellationRequested) { }
        finally
        {
            channel.Dispose();
            CryptographicOperations.ZeroMemory(expectedToken);
        }
    }

    private static async Task<byte[]?> ReadLine(Stream channel, CancellationToken cancellationToken)
    {
        byte[] line = new byte[MaximumLineBytes];
        byte[] next = new byte[1];
        for (int count = 0; count < line.Length; count++)
        {
            if (await channel.ReadAsync(next, cancellationToken) == 0) return null;
            if (next[0] == (byte)'\n') return line[..count];
            if (next[0] > 127 || next[0] == (byte)'\r') return null;
            line[count] = next[0];
        }
        return null;
    }

    private bool IsStop(byte[] request)
    {
        try
        {
            using var document = JsonDocument.Parse(request, new JsonDocumentOptions { MaxDepth = 2 });
            if (document.RootElement.ValueKind != JsonValueKind.Object) return false;
            int fields = 0;
            bool version = false, stop = false, authenticated = false;
            foreach (var property in document.RootElement.EnumerateObject())
            {
                fields++;
                switch (property.Name)
                {
                    case "schemaVersion" when !version:
                        if (property.Value.ValueKind != JsonValueKind.Number ||
                            !property.Value.TryGetInt32(out var number) || number != 1) return false;
                        version = true;
                        break;
                    case "action" when !stop:
                        if (property.Value.ValueKind != JsonValueKind.String || property.Value.GetString() != "stop") return false;
                        stop = true;
                        break;
                    case "token" when !authenticated:
                        if (property.Value.ValueKind != JsonValueKind.String ||
                            property.Value.GetString() is not string supplied || !NativeShutdown.IsToken(supplied)) return false;
                        authenticated = CryptographicOperations.FixedTimeEquals(Encoding.ASCII.GetBytes(supplied), expectedToken);
                        if (!authenticated) return false;
                        break;
                    default: return false;
                }
            }
            return fields == 3 && version && stop && authenticated;
        }
        catch (JsonException) { return false; }
    }
}
