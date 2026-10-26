using System.ComponentModel;
using System.Runtime.InteropServices;
using System.Runtime.Versioning;
using System.Text;
using Microsoft.Win32.SafeHandles;
using Xunit;

namespace RackClick.Quality.Tests;

// SONDA TEMPORAL (diagnóstico de la forma del nombre de FileRenameInfo). Se borra después de medir.
[SupportedOSPlatform("windows")]
public sealed class WindowsRenameProbeTests
{
    [Fact]
    public void ProbeRenameNameForms()
    {
        var root = Path.Combine(Path.GetTempPath(), "rackclick-sonda", Guid.NewGuid().ToString("N"));
        var parent = Path.Combine(root, "padre");
        Directory.CreateDirectory(parent);
        var lines = new List<string>();
        var nested = Path.Combine(root, "Instances", Guid.NewGuid().ToString("D"));
        Directory.CreateDirectory(nested);
        foreach (var variant in new[] { "simple-absoluta", "anidado-absoluta", "anidado-prefijo-largo", "anidado-relativa" })
        {
            var baseDir = variant.StartsWith("anidado", StringComparison.Ordinal) ? nested : parent;
            var source = Path.Combine(baseDir, "origen-" + variant);
            Directory.CreateDirectory(source);
            using var handle = CreateFileW(source, 0x00010000 | 0x0080, 0x1 | 0x2 | 0x4, IntPtr.Zero, 3, 0x02000000 | 0x00200000, IntPtr.Zero);
            using var parentHandle = CreateFileW(baseDir, 0x0004 | 0x0080, 0x1 | 0x2 | 0x4, IntPtr.Zero, 3, 0x02000000 | 0x00200000, IntPtr.Zero);
            var target = Path.Combine(baseDir, "destino-" + variant);
            var rootHandle = IntPtr.Zero;
            string name = target;
            if (variant == "anidado-prefijo-largo") name = @"\\?\" + target;
            if (variant == "anidado-relativa")
            {
                name = "destino-" + variant;
                rootHandle = parentHandle.DangerousGetHandle();
            }
            var nameBytes = Encoding.Unicode.GetBytes(name);
            var size = 2 * IntPtr.Size + 4 + nameBytes.Length;
            var buffer = Marshal.AllocHGlobal(size);
            try
            {
                Marshal.Copy(new byte[size], 0, buffer, size);
                Marshal.WriteByte(buffer, 0, 0);
                Marshal.WriteIntPtr(buffer, IntPtr.Size, rootHandle);
                Marshal.WriteInt32(buffer, 2 * IntPtr.Size, nameBytes.Length);
                Marshal.Copy(nameBytes, 0, IntPtr.Add(buffer, 2 * IntPtr.Size + 4), nameBytes.Length);
                var ok = SetFileInformationByHandle(handle, 3, buffer, (uint)size);
                var code = ok ? 0 : Marshal.GetLastWin32Error();
                lines.Add(variant + " ok=" + ok + " win32=" + code + " existeDestino=" + Directory.Exists(target) + " nombreBytes=" + nameBytes.Length);
            }
            finally
            {
                Marshal.FreeHGlobal(buffer);
            }
        }
        lines.Add("IntPtr.Size=" + IntPtr.Size);
        File.WriteAllLines(Path.Combine(Path.GetTempPath(), "sonda-renombrado-resultado.txt"), lines);
    }

    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern SafeFileHandle CreateFileW(string fileName, uint desiredAccess, uint shareMode, IntPtr securityAttributes,
        uint creationDisposition, uint flagsAndAttributes, IntPtr templateFile);

    [DllImport("kernel32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool SetFileInformationByHandle(SafeFileHandle file, int informationClass, IntPtr information, uint bufferSize);
}
