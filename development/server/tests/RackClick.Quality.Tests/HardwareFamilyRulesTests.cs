using System.IO.Compression;
using System.Reflection;
using System.Text;
using System.Text.Json;
using RackClick.Domain;
using RackClick.Server;
using Xunit;

namespace RackClick.Quality.Tests;

public sealed class HardwareFamilyRulesTests
{
    [Fact]
    public void IdcStaysExactAndSerialDoesNotBecomeEthernet()
    {
        Assert.Equal("idc", InventoryRules.Family("idc"));
        InventoryRules.RequireConnectorPair("idc", "idc");
        foreach (string other in InventoryRules.PortTypes.Where(type => type != "idc"))
        {
            Assert.Throws<DomainError>(() => InventoryRules.RequireConnectorPair("idc", other));
            Assert.Throws<DomainError>(() => InventoryRules.RequireConnectorPair(other, "idc"));
        }
        Assert.Equal("console", InventoryRules.Family("console"));
        Assert.Throws<DomainError>(() => InventoryRules.RequireConnectorPair("console", "rj45", true));
        InventoryRules.RequireConnectorPair("rj45", "sfp");
        Assert.Throws<DomainError>(() => InventoryRules.PortType("idc110"));
        Assert.Throws<DomainError>(() => InventoryRules.PortType("IDC"));
    }

    [Fact]
    public void DescriptorClassificationIsClosedByRawType()
    {
        foreach (var pair in new[] { ("power", "iec-c13"), ("power", "iec60309-32a-2p-e-plug"),
            ("console", "serial-10p10c"), ("console", "serial-de9"), ("idc", "idc-110"), ("idc", "idc-dual-110-krone") })
            Assert.Equal(pair.Item2, PhysicalConnectors.Validate(pair.Item1, pair.Item2));
        foreach (string type in InventoryRules.PortTypes) Assert.Null(PhysicalConnectors.Validate(type, null));
        foreach (var pair in new[] { ("rj45", "serial-8p8c"), ("idc", "iec-c13"), ("console", "idc-110"),
            ("power", "IEC-C13"), ("power", "iec-c13 "), ("power", "unknown") })
            Assert.Equal("physical_connector_invalid", Assert.Throws<DomainError>(() => PhysicalConnectors.Validate(pair.Item1, pair.Item2)).Code);
    }

    [Fact]
    public void ClassificationDoesNotRestrictGenericPowerCordEnds()
    {
        Assert.Equal("iec-c19", PhysicalConnectors.Validate("power", "iec-c19"));
        Assert.Equal("iec-c14", PhysicalConnectors.Validate("power", "iec-c14"));
        InventoryRules.RequirePowerPair("power", "outlet", "power", "inlet");
        InventoryRules.RequirePowerPair("power", "unspecified", "power", "unspecified");
        Assert.Throws<DomainError>(() => InventoryRules.RequirePowerPair("power", "inlet", "power", "inlet"));
    }

    [Fact]
    public void OnlyPublishedBoundGroupMetadataIsAuthenticated()
    {
        var profile = InventoryHardwareProfiles.All.First(profile => profile.Groups.Any(group => group.PhysicalConnector is not null));
        var group = profile.Groups.First(group => group.PhysicalConnector is not null);
        string? Trusted(string? key, string? revision, string? groupKey, string? type, string? face, string? stored) =>
            InventoryHardwareProfiles.TrustedPhysicalConnector(key, revision, groupKey, type, face, stored);
        Assert.Equal(group.PhysicalConnector, Trusted(profile.Key, profile.Revision, group.Key, group.Type, group.Face, group.PhysicalConnector));
        Assert.Null(Trusted(null, profile.Revision, group.Key, group.Type, group.Face, group.PhysicalConnector));
        Assert.Null(Trusted(profile.Key, "latest", group.Key, group.Type, group.Face, group.PhysicalConnector));
        Assert.Null(Trusted(profile.Key, profile.Revision, "other", group.Type, group.Face, group.PhysicalConnector));
        Assert.Null(Trusted(profile.Key, profile.Revision, group.Key, "usb_a", group.Face, group.PhysicalConnector));
        Assert.Null(Trusted(profile.Key, profile.Revision, group.Key, group.Type, "auto", group.PhysicalConnector));
        Assert.Null(Trusted(profile.Key, profile.Revision, group.Key, group.Type, group.Face, "forged"));
        Assert.Null(Trusted(profile.Key, profile.Revision, group.Key, group.Type, group.Face, null));
        string[] classifiedRevisions = ["selected506k-20261101-v1", "selected506l-20261101-v1", "selected506l-support-20261101-v1",
            "german-cpe-20261103-v1", "german-repeaters-20261103-v1"];
        Assert.All(InventoryHardwareProfiles.All.Where(profile => !classifiedRevisions.Contains(profile.Revision)),
            profile => Assert.All(profile.Groups, group => Assert.Null(group.PhysicalConnector)));
        Assert.All(InventoryHardwareProfiles.All.Where(profile => classifiedRevisions.Contains(profile.Revision)),
            profile => Assert.All(profile.Groups.Where(group => group.PhysicalConnector is not null), group =>
            {
                Assert.Equal(group.PhysicalConnector, Trusted(profile.Key, profile.Revision, group.Key, group.Type, group.Face, group.PhysicalConnector));
                Assert.Null(Trusted(profile.Key, profile.Revision, group.Key, "unknown", group.Face, group.PhysicalConnector));
            }));
    }

    private static InventoryPortView Port() => new(Guid.Empty, Guid.Empty, Guid.Empty, "Device", "rackEquipment",
        null, null, [], Guid.Empty, "Power", "power", "power", 1, "Label", "free", "rear", false, null, null, "outlet", false, [], []);

    [Fact]
    public void OptionalDtoPropertyIsOmittedForLegacyRows()
    {
        var options = new JsonSerializerOptions(JsonSerializerDefaults.Web);
        Assert.False(JsonSerializer.SerializeToElement(Port(), options).TryGetProperty("physicalConnector", out _));
        Assert.Equal("iec-c19", JsonSerializer.SerializeToElement(Port() with { PhysicalConnector = "iec-c19" }, options)
            .GetProperty("physicalConnector").GetString());
        var schemas = JsonSerializer.SerializeToElement(OpenApiDocument.Create()).GetProperty("components").GetProperty("schemas");
        Assert.DoesNotContain("physicalConnector", schemas.GetProperty("InventoryPortView").GetProperty("required")
            .EnumerateArray().Select(value => value.GetString()));
    }

    [Fact]
    public void CsvAndSpreadsheetOnlyAppendClassificationWhenPresent()
    {
        byte[] Build(string method, InventoryPortView port) => (byte[])typeof(InventoryStore)
            .GetMethod(method, BindingFlags.NonPublic | BindingFlags.Static)!.Invoke(null, [Guid.Empty, 1L, "ports", new object[] { port }])!;
        string legacy = Encoding.UTF8.GetString(Build("BuildReportCsv", Port()));
        string expanded = Encoding.UTF8.GetString(Build("BuildReportCsv", Port() with { PhysicalConnector = "iec-c19" }));
        Assert.DoesNotContain("physical_connector", legacy);
        Assert.EndsWith("\"physical_connector\"", expanded.Split("\r\n")[0]);
        Assert.EndsWith("\"iec-c19\"", expanded.Split("\r\n")[1]);
        foreach (bool classified in new[] { false, true })
        {
            using var stream = new MemoryStream(Build("BuildSpreadsheet", Port() with { PhysicalConnector = classified ? "iec-c19" : null }));
            using var zip = new ZipArchive(stream, ZipArchiveMode.Read);
            using var reader = new StreamReader(zip.GetEntry("xl/worksheets/sheet1.xml")!.Open());
            Assert.Equal(classified, reader.ReadToEnd().Contains("physical_connector", StringComparison.Ordinal));
        }
    }
}
