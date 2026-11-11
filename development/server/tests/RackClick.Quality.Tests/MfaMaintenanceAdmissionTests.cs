using RackClick.Server;
using Npgsql;
using Xunit;

namespace RackClick.Quality.Tests;

public sealed class MfaMaintenanceAdmissionTests
{
    [Fact]
    public async Task LostAdmissionStopsHostAndBecomesUnhealthy()
    {
        await using var connection=new NpgsqlConnection();await using var lease=new MfaMaintenanceLease(connection,false);
        var stopped=0;using var timeout=new CancellationTokenSource(TimeSpan.FromSeconds(5));
        await lease.MonitorAsync(()=>stopped++,timeout.Token);
        Assert.Equal(1,stopped);Assert.False(lease.IsHealthy);
    }
    [Fact]
    public void ExistingFenceFileBlocksStartupWithoutParsingOrExposingIt()
    {
        var root=Path.Combine(Path.GetTempPath(),"rc-fence-"+Guid.NewGuid().ToString("N"));var id=Guid.NewGuid();
        var dir=Path.Combine(root,id.ToString("D"));Directory.CreateDirectory(dir);
        try
        {
            File.WriteAllText(Path.Combine(dir,"mfa-maintenance-fence.json"),"not a trusted receipt and not interpreted as one");
            var error=Assert.Throws<MfaMaintenanceException>(()=>MfaMaintenanceAdmission.ThrowIfFenced(root,id));
            Assert.Equal("mfa_maintenance_pending",error.Code);
        }
        finally { Directory.Delete(root,true); }
    }

    [Fact]
    public void DirectoryAtFencePathAlsoBlocksStartup()
    {
        var root=Path.Combine(Path.GetTempPath(),"rc-fence-"+Guid.NewGuid().ToString("N"));var id=Guid.NewGuid();
        var dir=Path.Combine(root,id.ToString("D"));Directory.CreateDirectory(Path.Combine(dir,"mfa-maintenance-fence.json"));
        try { Assert.Throws<MfaMaintenanceException>(()=>MfaMaintenanceAdmission.ThrowIfFenced(root,id)); }
        finally {Directory.Delete(root,true);}
    }

    [Fact]
    public void MissingFenceInExistingScopeDoesNotCreateFiles()
    {
        var root=Path.Combine(Path.GetTempPath(),"rc-fence-"+Guid.NewGuid().ToString("N"));var id=Guid.NewGuid();
        var dir=Path.Combine(root,id.ToString("D"));Directory.CreateDirectory(dir);
        try { MfaMaintenanceAdmission.ThrowIfFenced(root,id);Assert.Empty(Directory.GetFileSystemEntries(dir)); }
        finally {Directory.Delete(root,true);}
    }
}
