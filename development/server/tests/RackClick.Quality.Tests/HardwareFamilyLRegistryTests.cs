using System.Text.Json.Nodes;
using RackClick.Server;
using Xunit;
namespace RackClick.Quality.Tests;
public sealed class HardwareFamilyLRegistryTests
{
    [Fact]
    public void AllSelectedRevisionsArePresentAndContainersDoNotConsumeTheirCapacity()
    {
        var profiles=InventoryHardwareProfiles.All.Where(p=>p.Revision=="selected506l-20261101-v1").ToArray();
        Assert.Equal(62,profiles.Length);
        Assert.Equal(1673,profiles.Sum(p=>p.Groups.Sum(g=>g.Count)));
        Assert.Equal(4,profiles.Count(p=>p.Kind=="rackContainer"));
        foreach(var p in profiles.Where(p=>p.Kind=="rackContainer"))
        {
            Assert.Equal(0,p.RackUnits);Assert.Empty(p.Groups);
            var mounting=JsonNode.Parse(p.MountingJson!)!;
            Assert.Equal("room",mounting["target"]!.GetValue<string>());
            Assert.InRange(mounting["capacityU"]!.GetValue<int>(),1,60);
        }
    }
    [Fact]
    public void OpticalMatrixKeeps640SeparateEndpointsWithoutInventingAnInternalRoute()
    {
        var profile=InventoryHardwareProfiles.All.Single(p=>p.Revision=="selected506l-20261101-v1"&&p.Groups.Count(g=>g.Count==320)==2);
        var optical=profile.Groups.Where(g=>g.Count==320).ToArray();
        Assert.All(optical,g=>Assert.Equal("fiber",g.Type));
        Assert.Contains(optical,g=>g.SignalRole=="tx");Assert.Contains(optical,g=>g.SignalRole=="rx");
        Assert.Null(profile.Passthrough);Assert.Empty(JsonNode.Parse(profile.ContinuitiesJson!)!.AsArray());
    }
    [Fact]
    public void UspReceiverIsAnExplicitSuccessorAndDoesNotRewriteTheExistingSwitch()
    {
        const string key="selected-nb-e5030fe747d79fe6";
        var old=InventoryHardwareProfiles.Find(key,"selected506a-20261101-v1")!;
        var current=InventoryHardwareProfiles.Find(key,"selected506l-support-20261101-v1")!;
        Assert.DoesNotContain(old.Groups,g=>g.PowerSystem=="unifi-smartpower");
        var inlet=Assert.Single(current.Groups,g=>g.PowerSystem=="unifi-smartpower");
        Assert.Equal("power_dc",inlet.Type);Assert.Equal("inlet",inlet.PowerRole);
        Assert.Equal(old.Groups,current.Groups.Take(old.Groups.Count));
        Assert.Null(InventoryHardwareProfiles.Find(key,"latest"));
        var historical=InventoryHardwareProfiles.All.Where(p=>p.Revision is not
            ("german-cpe-20261103-v1" or "german-repeaters-20261103-v1")).ToArray();
        Assert.Equal(861,historical.Where(p=>p.Manufacturer is not null).Select(p=>p.Key).Distinct().Count());
        Assert.Equal(877,InventoryHardwareProfiles.All.Where(p=>p.Manufacturer is not null).Select(p=>p.Key).Distinct().Count());
    }
}
