using RackClick.Server;
using Xunit;

namespace RackClick.Quality.Tests;

public sealed class HardwareRevisionTests
{
    // Historical batch assertions must use the closed pre-German snapshot,
    // rather than accidentally counting the two later additive revisions.
    private static IReadOnlyList<InventoryHardwareProfiles.Profile> PreGermanCatalogue =>
        InventoryHardwareProfiles.All.Where(p => p.Revision is not
            ("german-cpe-20261103-v1" or "german-repeaters-20261103-v1")).ToArray();
    private static InventoryHardwareProfiles.Profile Profile(string revision, int ports) => new(
        "same-key", 1, 220, 38, 200, "#123456", [new("front", "rj45", ports, "front", "LAN", "")], revision);

    [Fact]
    public void SameKeyResolvesOnlyTheExactRevision()
    {
        var registry = new InventoryHardwareProfiles.Registry([Profile("r1", 6), Profile("r2", 24)]);
        Assert.Equal(6, registry.Find("same-key", "r1")!.Groups[0].Count);
        Assert.Equal(24, registry.Find("same-key", "r2")!.Groups[0].Count);
        foreach (string? revision in new string?[] { null, "latest", "unknown", "R1", "r1 " }) Assert.Null(registry.Find("same-key", revision));
        Assert.Null(registry.Find("SAME-KEY", "r1"));
    }

    [Fact]
    public void DuplicateRevisionCannotReplaceAnExistingDefinition()
        => Assert.Throws<ArgumentException>(() => new InventoryHardwareProfiles.Registry([Profile("r1", 6), Profile("r1", 24)]));

    [Fact]
    public void CallerAndExposedCollectionsCannotMutateTheRegistry()
    {
        var groups = new List<InventoryHardwareProfiles.Group> { new("front", "rj45", 6, "front", "LAN", "") };
        var original = Profile("r1", 6) with { Groups = groups };
        var input = new List<InventoryHardwareProfiles.Profile> { original };
        var registry = new InventoryHardwareProfiles.Registry(input);
        groups[0] = groups[0] with { Count = 99 }; input.Clear();
        Assert.Equal(6, registry.Find("same-key", "r1")!.Groups[0].Count);
        Assert.Throws<NotSupportedException>(() => ((IList<InventoryHardwareProfiles.Profile>)registry.All).Clear());
        Assert.Throws<NotSupportedException>(() => ((IList<InventoryHardwareProfiles.Group>)registry.All[0].Groups).Clear());
    }

    [Fact]
    public void ProductPreservesReferenceAndReviewedCommercialModelRevisions()
    {
        Assert.Equal(884, InventoryHardwareProfiles.All.Count);
        Assert.Equal(868, PreGermanCatalogue.Count);
        Assert.Equal(6, InventoryHardwareProfiles.All.Count(p => p.Revision == "german-cpe-20261103-v1"));
        Assert.Equal(10, InventoryHardwareProfiles.All.Count(p => p.Revision == "german-repeaters-20261103-v1"));
        Assert.Equal(4, InventoryHardwareProfiles.All.Count(p => p.Revision == "hw-reference-v1"));
        Assert.Null(InventoryHardwareProfiles.Find("switch-24", "hw-reference-v2"));
        Assert.Equal(38, InventoryHardwareProfiles.Find("desktop-firewall-6", "hw-reference-v1")!.HeightMm);
        var commercial = InventoryHardwareProfiles.Find("startech-c6panelutp241uft", "startech-20261030-v1")!;
        Assert.Equal(44.3m, commercial.HeightMm);
        Assert.Equal("StarTech.com", commercial.Manufacturer);
        Assert.Equal(48, commercial.Groups.Sum(g => g.Count));
        Assert.Null(InventoryHardwareProfiles.Find(commercial.Key, "hw-reference-v1"));
        Assert.All(PreGermanCatalogue.Where(p => p.Revision != "batch50-20261030-v1" && p.Revision != "batch50b-20261031-v1" && p.Revision != "batch100-20261031-v1" && p.Revision != "batch100b-20261031-v1" && p.Revision != "batch100c-20261031-v1" && p.Revision != "selected506a-20261101-v1" && p.Revision != "selected506b-20261101-v1" && p.Revision != "selected506c-20261101-v1" && p.Revision != "selected506d-20261101-v1" && p.Revision != "selected506e-20261101-v1" && p.Revision != "selected506f-20261101-v1" && p.Revision != "selected506g-20261101-v1" && p.Revision != "selected506h-20261101-v1" && p.Revision != "selected506i-20261101-v1" && p.Revision != "selected506j-20261101-v1" && p.Revision != "selected506k-20261101-v1" && p.Revision != "selected506l-20261101-v1" && p.Revision != "selected506l-support-20261101-v1" && p.Revision != "mount-support7u-20261101-v1" && p.Key is not ("aruba-jl682a" or "synology-rs1221plus")).SelectMany(p => p.Groups), g => Assert.Equal("unspecified", g.PowerRole));
        var aruba = InventoryHardwareProfiles.Find("aruba-jl682a", "aruba-20261030-v1")!;
        Assert.Equal("JL682A", aruba.Sku);
        Assert.Equal(442.5m, aruba.WidthMm);
        Assert.Equal(43.9m, aruba.HeightMm);
        Assert.Equal(221.5m, aruba.DepthMm);
        Assert.Equal(29, aruba.Groups.Sum(g => g.Count));
        Assert.Equal(24, aruba.Groups.Single(g => g.Key == "front-copper").Count);
        Assert.Equal(4, aruba.Groups.Single(g => g.Key == "front-uplink").Count);
        var inlet = aruba.Groups.Single(g => g.Key == "rear-power");
        Assert.Equal("power", inlet.Type);
        Assert.Equal("rear", inlet.Face);
        Assert.Equal("inlet", inlet.PowerRole);
        Assert.Equal(1, inlet.Count);
        Assert.Null(aruba.Passthrough);
        Assert.Null(InventoryHardwareProfiles.Find(aruba.Key, "hw-reference-v1"));
        Assert.Null(InventoryHardwareProfiles.Find(aruba.Key, "latest"));
        var fortinet = InventoryHardwareProfiles.Find("fortinet-fg60f", "fortinet-20261030-v1")!;
        Assert.Equal("FortiGate 60F", fortinet.Model);
        Assert.Equal("FG-60F", fortinet.Sku);
        Assert.Equal("desktop", fortinet.Kind);
        Assert.Equal(0, fortinet.RackUnits);
        Assert.Equal(216m, fortinet.WidthMm);
        Assert.Equal(38.5m, fortinet.HeightMm);
        Assert.Equal(160m, fortinet.DepthMm);
        Assert.Equal(10, fortinet.Groups.Sum(g => g.Count));
        Assert.Equal(4, fortinet.Groups.Count);
        Assert.All(fortinet.Groups, g => { Assert.Equal("rj45", g.Type); Assert.Equal("rear", g.Face); Assert.Equal("unspecified", g.PowerRole); });
        Assert.Empty(fortinet.Slots);
        Assert.Null(fortinet.Passthrough);
        Assert.Null(InventoryHardwareProfiles.Find(fortinet.Key, "hw-reference-v1"));
        Assert.Null(InventoryHardwareProfiles.Find(fortinet.Key, "latest"));
        var synology = InventoryHardwareProfiles.Find("synology-rs1221plus", "synology-20261030-v1")!;
        Assert.Equal("Synology", synology.Manufacturer);
        Assert.Equal("RS1221+", synology.Sku);
        Assert.Equal("rack", synology.Kind);
        Assert.Equal(2, synology.RackUnits);
        Assert.Equal(482m, synology.WidthMm);
        Assert.Equal(88m, synology.HeightMm);
        Assert.Equal(306.6m, synology.DepthMm);
        Assert.Equal(5, synology.Groups.Sum(g => g.Count));
        Assert.Equal(4, synology.Groups.Single(g => g.Key == "rear-lan").Count);
        var synologyInlet = synology.Groups.Single(g => g.Key == "rear-power");
        Assert.Equal("power", synologyInlet.Type);
        Assert.Equal("inlet", synologyInlet.PowerRole);
        Assert.Equal(1, synologyInlet.Count);
        Assert.All(synology.Groups, g => Assert.Equal("rear", g.Face));
        Assert.Empty(synology.Slots);
        Assert.Null(synology.Passthrough);
        Assert.Null(InventoryHardwareProfiles.Find(synology.Key, "hw-reference-v1"));
        Assert.Null(InventoryHardwareProfiles.Find("synology-rs1221rpplus", synology.Revision));
        var diskStation = InventoryHardwareProfiles.Find("synology-ds423plus", "synology-ds423plus-20261030-v1")!;
        Assert.Equal("Synology", diskStation.Manufacturer);
        Assert.Equal("DiskStation", diskStation.Family);
        Assert.Equal("DS423+", diskStation.Model);
        Assert.Equal("DS423+", diskStation.Sku);
        Assert.Equal("desktop", diskStation.Kind);
        Assert.Equal(0, diskStation.RackUnits);
        Assert.Equal(199m, diskStation.WidthMm);
        Assert.Equal(166m, diskStation.HeightMm);
        Assert.Equal(223m, diskStation.DepthMm);
        var diskStationLan = Assert.Single(diskStation.Groups);
        Assert.Equal("rear-lan", diskStationLan.Key);
        Assert.Equal("rj45", diskStationLan.Type);
        Assert.Equal("rear", diskStationLan.Face);
        Assert.Equal(2, diskStationLan.Count);
        Assert.Equal("unspecified", diskStationLan.PowerRole);
        Assert.Null(diskStation.Passthrough);
        Assert.Empty(diskStation.Slots);
        Assert.Null(InventoryHardwareProfiles.Find(diskStation.Key, "hw-reference-v1"));
        Assert.Null(InventoryHardwareProfiles.Find("synology-ds423", diskStation.Revision));
        var tallSupport = InventoryHardwareProfiles.Find("shelf-5u", "mount-support-20261030-v1")!;
        Assert.Equal("shelf", tallSupport.Kind);
        Assert.Equal(5, tallSupport.RackUnits);
        Assert.Equal(482.6m, tallSupport.WidthMm);
        Assert.Equal(222m, tallSupport.HeightMm);
        Assert.Equal(300m, tallSupport.DepthMm);
        var tallSlot = Assert.Single(tallSupport.Slots);
        Assert.Equal("main", tallSlot.Key);
        Assert.Equal(440m, tallSlot.WidthMm);
        Assert.Equal(190m, tallSlot.HeightMm);
        Assert.Equal(300m, tallSlot.DepthMm);
        Assert.Empty(tallSupport.Groups);
        Assert.Null(tallSupport.Manufacturer);
        Assert.Null(tallSupport.Sku);
        var oldSupport = InventoryHardwareProfiles.Find("shelf-2u", "hw-reference-v1")!;
        Assert.Equal(60m, Assert.Single(oldSupport.Slots).HeightMm);
        Assert.True(diskStation.HeightMm > oldSupport.Slots[0].HeightMm);
        Assert.True(diskStation.HeightMm <= tallSlot.HeightMm);
        Assert.Null(InventoryHardwareProfiles.Find(tallSupport.Key, "hw-reference-v1"));
        var qnap = InventoryHardwareProfiles.Find("qnap-ts464-8g", "qnap-20261030-v1")!;
        Assert.Equal("QNAP", qnap.Manufacturer);
        Assert.Equal("TS-x64", qnap.Family);
        Assert.Equal("TS-464", qnap.Model);
        Assert.Equal("TS-464-8G", qnap.Sku);
        Assert.Equal("desktop", qnap.Kind);
        Assert.Equal(0, qnap.RackUnits);
        Assert.Equal(170m, qnap.WidthMm);
        Assert.Equal(165m, qnap.HeightMm);
        Assert.Equal(226.5m, qnap.DepthMm);
        var qnapLan = Assert.Single(qnap.Groups);
        Assert.Equal("rear-lan", qnapLan.Key);
        Assert.Equal("rj45", qnapLan.Type);
        Assert.Equal("rear", qnapLan.Face);
        Assert.Equal("unspecified", qnapLan.PowerRole);
        Assert.Equal(2, qnapLan.Count);
        Assert.Null(qnap.Passthrough);
        Assert.Empty(qnap.Slots);
        Assert.Null(InventoryHardwareProfiles.Find(qnap.Key, "hw-reference-v1"));
        Assert.Null(InventoryHardwareProfiles.Find("qnap-ts464-4g", qnap.Revision));
        Assert.True(qnap.HeightMm > oldSupport.Slots[0].HeightMm);
        Assert.True(qnap.HeightMm <= tallSlot.HeightMm);
        Assert.True(qnap.WidthMm <= tallSlot.WidthMm);
        Assert.True(qnap.DepthMm <= tallSlot.DepthMm);
    }
    [Fact]
    public void Batch50KeepsDistinctExactModelsAndTypedPowerRoles()
    {
        var models = PreGermanCatalogue.Where(p => p.Revision == "batch50-20261030-v1").ToArray();
        Assert.Equal(50, models.Length);
        Assert.Equal(50, models.Select(p => (p.Manufacturer, p.Model, p.Sku)).Distinct().Count());
        Assert.All(models, p => {
            Assert.NotNull(p.Manufacturer); Assert.NotNull(p.Sku);
            Assert.InRange(p.RackUnits, p.Kind == "desktop" ? 0 : 1, p.Kind == "desktop" ? 0 : 60);
            Assert.NotEmpty(p.Groups);
            Assert.All(p.Groups, g => Assert.Equal(g.Type == "power" ? "inlet" : "unspecified", g.PowerRole));
            Assert.Null(InventoryHardwareProfiles.Find(p.Key, "latest"));
            Assert.Null(InventoryHardwareProfiles.Find(p.Key, "hw-reference-v1"));
        });
    }

    [Fact]
    public void SecondBatch50AddsModelsWithoutReplacingAnyPriorIdentity()
    {
        var added = PreGermanCatalogue.Where(p => p.Revision == "batch50b-20261031-v1").ToArray();
        var previous = PreGermanCatalogue.Where(p => p.Revision != "batch50b-20261031-v1" && p.Revision != "batch100-20261031-v1" && p.Revision != "batch100b-20261031-v1" && p.Revision != "batch100c-20261031-v1" && p.Revision != "selected506a-20261101-v1" && p.Revision != "selected506b-20261101-v1" && p.Revision != "selected506c-20261101-v1" && p.Revision != "selected506d-20261101-v1" && p.Revision != "selected506e-20261101-v1" && p.Revision != "selected506f-20261101-v1" && p.Revision != "selected506g-20261101-v1" && p.Revision != "selected506h-20261101-v1" && p.Revision != "selected506i-20261101-v1" && p.Revision != "selected506j-20261101-v1" && p.Revision != "selected506k-20261101-v1" && p.Revision != "selected506l-20261101-v1" && p.Revision != "selected506l-support-20261101-v1" && p.Revision != "mount-support7u-20261101-v1").ToArray();
        Assert.Equal(50, added.Length);
        Assert.Equal(61, previous.Length);
        Assert.Equal(50, added.Select(p => (p.Manufacturer, p.Model)).Distinct().Count());
        Assert.All(added, p => {
            Assert.DoesNotContain(previous, old => old.Key == p.Key || (old.Manufacturer == p.Manufacturer && old.Model == p.Model));
            Assert.All(p.Groups, g => Assert.Equal(g.Type == "power" ? "inlet" : "unspecified", g.PowerRole));
            Assert.Null(InventoryHardwareProfiles.Find(p.Key, "batch50-20261030-v1"));
        });
    }

    [Fact]
    public void Batch100PreservesThePrevious111AndHasNoDuplicateModel()
    {
        var added = PreGermanCatalogue.Where(p => p.Revision == "batch100-20261031-v1").ToArray();
        var previous = PreGermanCatalogue.Where(p => p.Revision != "batch100-20261031-v1" && p.Revision != "batch100b-20261031-v1" && p.Revision != "batch100c-20261031-v1" && p.Revision != "selected506a-20261101-v1" && p.Revision != "selected506b-20261101-v1" && p.Revision != "selected506c-20261101-v1" && p.Revision != "selected506d-20261101-v1" && p.Revision != "selected506e-20261101-v1" && p.Revision != "selected506f-20261101-v1" && p.Revision != "selected506g-20261101-v1" && p.Revision != "selected506h-20261101-v1" && p.Revision != "selected506i-20261101-v1" && p.Revision != "selected506j-20261101-v1" && p.Revision != "selected506k-20261101-v1" && p.Revision != "selected506l-20261101-v1" && p.Revision != "selected506l-support-20261101-v1" && p.Revision != "mount-support7u-20261101-v1").ToArray();
        Assert.Equal(100, added.Length);
        Assert.Equal(111, previous.Length);
        Assert.Equal(100, added.Select(p => (p.Manufacturer, p.Model)).Distinct().Count());
        Assert.All(added, p => {
            Assert.DoesNotContain(previous, old => old.Key == p.Key || (old.Manufacturer == p.Manufacturer && old.Model == p.Model));
            Assert.All(p.Groups, g => Assert.Equal(g.Type == "power" ? "inlet" : "unspecified", g.PowerRole));
            Assert.Null(InventoryHardwareProfiles.Find(p.Key, "batch50-20261030-v1"));
            Assert.Null(InventoryHardwareProfiles.Find(p.Key, "batch50b-20261031-v1"));
        });
    }

    [Fact]
    public void FourthBatchPreservesThePrevious211AndAdds100NewModels()
    {
        var added = PreGermanCatalogue.Where(p => p.Revision == "batch100b-20261031-v1").ToArray();
        var previous = PreGermanCatalogue.Where(p => p.Revision != "batch100b-20261031-v1" && p.Revision != "batch100c-20261031-v1" && p.Revision != "selected506a-20261101-v1" && p.Revision != "selected506b-20261101-v1" && p.Revision != "selected506c-20261101-v1" && p.Revision != "selected506d-20261101-v1" && p.Revision != "selected506e-20261101-v1" && p.Revision != "selected506f-20261101-v1" && p.Revision != "selected506g-20261101-v1" && p.Revision != "selected506h-20261101-v1" && p.Revision != "selected506i-20261101-v1" && p.Revision != "selected506j-20261101-v1" && p.Revision != "selected506k-20261101-v1" && p.Revision != "selected506l-20261101-v1" && p.Revision != "selected506l-support-20261101-v1" && p.Revision != "mount-support7u-20261101-v1").ToArray();
        Assert.Equal(100, added.Length);
        Assert.Equal(211, previous.Length);
        Assert.Equal(100, added.Select(p => (p.Manufacturer, p.Model)).Distinct().Count());
        Assert.All(added, p => {
            Assert.DoesNotContain(previous, old => old.Key == p.Key || (old.Manufacturer == p.Manufacturer && old.Model == p.Model));
            Assert.All(p.Groups, g => Assert.Equal(g.Type == "power" ? "inlet" : "unspecified", g.PowerRole));
            Assert.Null(InventoryHardwareProfiles.Find(p.Key, "batch100-20261031-v1"));
        });
    }

    [Fact]
    public void FifthBatchPreservesThePrevious311AndAdds100NewModels()
    {
        var added = PreGermanCatalogue.Where(p => p.Revision == "batch100c-20261031-v1").ToArray();
        var previous = PreGermanCatalogue.Where(p => p.Revision != "batch100c-20261031-v1" && p.Revision != "selected506a-20261101-v1" && p.Revision != "selected506b-20261101-v1" && p.Revision != "selected506c-20261101-v1" && p.Revision != "selected506d-20261101-v1" && p.Revision != "selected506e-20261101-v1" && p.Revision != "selected506f-20261101-v1" && p.Revision != "selected506g-20261101-v1" && p.Revision != "selected506h-20261101-v1" && p.Revision != "selected506i-20261101-v1" && p.Revision != "selected506j-20261101-v1" && p.Revision != "selected506k-20261101-v1" && p.Revision != "selected506l-20261101-v1" && p.Revision != "selected506l-support-20261101-v1" && p.Revision != "mount-support7u-20261101-v1").ToArray();
        Assert.Equal(100, added.Length);
        Assert.Equal(311, previous.Length);
        Assert.Equal(100, added.Select(p => (p.Manufacturer, p.Model)).Distinct().Count());
        Assert.All(added, p => {
            Assert.DoesNotContain(previous, old => old.Key == p.Key || (old.Manufacturer == p.Manufacturer && old.Model == p.Model));
            Assert.All(p.Groups, g => Assert.Equal(g.Type == "power" ? "inlet" : "unspecified", g.PowerRole));
            Assert.Null(InventoryHardwareProfiles.Find(p.Key, "batch100b-20261031-v1"));
        });
    }

    [Fact]
    public void Selected506AddsSeventeenRequestedIdentitiesAndKeepsAll411PreviousProfiles()
    {
        var added = PreGermanCatalogue.Where(p => p.Revision == "selected506a-20261101-v1").ToArray();
        var previous = PreGermanCatalogue.Where(p => p.Revision != "selected506a-20261101-v1" && p.Revision != "selected506b-20261101-v1" && p.Revision != "selected506c-20261101-v1" && p.Revision != "selected506d-20261101-v1" && p.Revision != "selected506e-20261101-v1" && p.Revision != "selected506f-20261101-v1" && p.Revision != "selected506g-20261101-v1" && p.Revision != "selected506h-20261101-v1" && p.Revision != "selected506i-20261101-v1" && p.Revision != "selected506j-20261101-v1" && p.Revision != "selected506k-20261101-v1" && p.Revision != "selected506l-20261101-v1" && p.Revision != "selected506l-support-20261101-v1" && p.Revision != "mount-support7u-20261101-v1").ToArray();
        Assert.Equal(17, added.Length);
        Assert.Equal(411, previous.Length);
        Assert.Equal(17, added.Select(p => (p.Manufacturer, p.Model)).Distinct().Count());
        Assert.All(added, p => {
            Assert.StartsWith("selected-", p.Key);
            Assert.DoesNotContain(previous, old => old.Key == p.Key || (old.Manufacturer == p.Manufacturer && old.Model == p.Model));
            Assert.Contains(p.Kind, new[] { "rack", "desktop" });
            Assert.Equal(p.Kind == "desktop" ? 0 : 1, p.RackUnits);
            Assert.All(p.Groups, g => Assert.Equal(g.Type == "power" ? "inlet" : "unspecified", g.PowerRole));
            Assert.Null(InventoryHardwareProfiles.Find(p.Key, "batch100c-20261031-v1"));
            Assert.Null(InventoryHardwareProfiles.Find(p.Key, "latest"));
        });
    }

}
