using System.Runtime.InteropServices;
using System.Runtime.Versioning;
using System.Security.Cryptography;
using System.Security.Principal;
using System.Text;
using Npgsql;

namespace RackClick.Server;

// F-02.01: purpose-separated DPAPI envelope. Not a portable backup format. The ACL is
// essential: LocalMachine alone permits other local users to unprotect a readable blob.
internal sealed class SqlSecretException(string code) : Exception(code)
{
    public string Code { get; } = code;
}

[SupportedOSPlatform("windows")]
internal static class WindowsSqlSecret
{
    internal const int MaximumFileBytes = 65_536;
    internal const int MaximumConnectionBytes = 8_192;
    private static readonly byte[] Magic = "RCSQL001"u8.ToArray();
    private static readonly UTF8Encoding Utf8 = new(false, true);

    // Returns ciphertext only. Publication/ACL creation is the provisioner's responsibility (F-02.02).
    internal static byte[] ProtectForProvisioning(string connection, Guid installation, SecurityIdentifier reader, string database, string runtimeUser)
    {
        var normalized = ValidateConnection(connection, database, runtimeUser);
        byte[] plain;
        try { plain = Utf8.GetBytes(normalized); }
        catch (EncoderFallbackException) { throw Fail("sql_secret_connection_invalid"); }
        try
        {
            if (plain.Length > MaximumConnectionBytes) throw Fail("sql_secret_connection_invalid");
            var encrypted = Transform(plain, Entropy(installation, reader, database, runtimeUser), protect: true);
            if (encrypted.Length > MaximumFileBytes - Magic.Length) throw Fail("sql_secret_invalid");
            return [.. Magic, .. encrypted];
        }
        finally { CryptographicOperations.ZeroMemory(plain); }
    }

    internal static string Open(ReadOnlySpan<byte> file, Guid installation, SecurityIdentifier reader, string database, string runtimeUser)
    {
        if (file.Length <= Magic.Length || file.Length > MaximumFileBytes || !file.StartsWith(Magic))
            throw Fail("sql_secret_invalid");
        var plain = Transform(file[Magic.Length..].ToArray(), Entropy(installation, reader, database, runtimeUser), protect: false);
        try
        {
            if (plain.Length > MaximumConnectionBytes) throw Fail("sql_secret_invalid");
            string connection;
            try { connection = Utf8.GetString(plain); }
            catch (DecoderFallbackException) { throw Fail("sql_secret_invalid"); }
            return ValidateConnection(connection, database, runtimeUser);
        }
        finally { CryptographicOperations.ZeroMemory(plain); }
    }

    private static byte[] Entropy(Guid installation, SecurityIdentifier reader, string database, string runtimeUser)
    {
        if (installation == Guid.Empty || !Identifier(database) || !Identifier(runtimeUser))
            throw Fail("sql_secret_config_invalid");
        return Utf8.GetBytes($"RackClick/SQL/runtime/v1\n{installation:D}\n{reader.Value}\n{database}\n{runtimeUser}");
    }

    internal static bool Identifier(string value) => value.Length is > 0 and <= 63 &&
        value.All(c => c is >= 'a' and <= 'z' or >= '0' and <= '9' or '_') && value[0] is >= 'a' and <= 'z';

    private static string ValidateConnection(string connection, string database, string runtimeUser)
    {
        try
        {
            if (string.IsNullOrEmpty(connection) || connection.Length > MaximumConnectionBytes)
                throw Fail("sql_secret_connection_invalid");
            var parsed = new NpgsqlConnectionStringBuilder(connection);
            if (parsed.Database != database || parsed.Username != runtimeUser || string.IsNullOrEmpty(parsed.Password) ||
                string.IsNullOrWhiteSpace(parsed.Host) || !string.IsNullOrEmpty(parsed.Passfile))
                throw Fail("sql_secret_connection_invalid");
            parsed.PersistSecurityInfo = false;
            parsed.IncludeErrorDetail = false;
            parsed.LogParameters = false;
            return parsed.ConnectionString;
        }
        catch (ArgumentException) { throw Fail("sql_secret_connection_invalid"); }
    }

    // As in the approved MFA provider, no extra package is required. All unmanaged
    // buffers (including plaintext inputs/outputs) are zeroed before freeing them.
    private static byte[] Transform(byte[] input, byte[] entropy, bool protect)
    {
        IntPtr inputPointer = IntPtr.Zero, entropyPointer = IntPtr.Zero;
        Blob output = default;
        try
        {
            inputPointer = Marshal.AllocHGlobal(input.Length);
            Marshal.Copy(input, 0, inputPointer, input.Length);
            entropyPointer = Marshal.AllocHGlobal(entropy.Length);
            Marshal.Copy(entropy, 0, entropyPointer, entropy.Length);
            var source = new Blob { Length = input.Length, Data = inputPointer };
            var extra = new Blob { Length = entropy.Length, Data = entropyPointer };
            bool ok = protect
                ? CryptProtectData(ref source, IntPtr.Zero, ref extra, IntPtr.Zero, IntPtr.Zero, 0x1 | 0x4, out output)
                : CryptUnprotectData(ref source, IntPtr.Zero, ref extra, IntPtr.Zero, IntPtr.Zero, 0x1, out output);
            if (!ok) throw Fail(protect ? "sql_secret_protection_failed" : "sql_secret_decryption_failed");
            int limit = protect ? MaximumFileBytes - Magic.Length : MaximumConnectionBytes;
            if (output.Length <= 0 || output.Length > limit || output.Data == IntPtr.Zero) throw Fail("sql_secret_invalid");
            var bytes = new byte[output.Length];
            Marshal.Copy(output.Data, bytes, 0, bytes.Length);
            return bytes;
        }
        finally
        {
            if (inputPointer != IntPtr.Zero) { Marshal.Copy(new byte[input.Length], 0, inputPointer, input.Length); Marshal.FreeHGlobal(inputPointer); }
            if (entropyPointer != IntPtr.Zero) { Marshal.Copy(new byte[entropy.Length], 0, entropyPointer, entropy.Length); Marshal.FreeHGlobal(entropyPointer); }
            if (output.Data != IntPtr.Zero)
            {
                Marshal.Copy(new byte[output.Length], 0, output.Data, output.Length);
                LocalFree(output.Data);
            }
        }
    }

    private static SqlSecretException Fail(string code) => new(code);
    [StructLayout(LayoutKind.Sequential)]
    private struct Blob { public int Length; public IntPtr Data; }
    [DllImport("crypt32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool CryptProtectData(ref Blob input, IntPtr description, ref Blob entropy, IntPtr reserved, IntPtr prompt, int flags, out Blob output);
    [DllImport("crypt32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool CryptUnprotectData(ref Blob input, IntPtr description, ref Blob entropy, IntPtr reserved, IntPtr prompt, int flags, out Blob output);
    [DllImport("kernel32.dll")]
    private static extern IntPtr LocalFree(IntPtr memory);
}
