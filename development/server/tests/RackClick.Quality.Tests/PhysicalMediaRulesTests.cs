using System.Text.Json;
using RackClick.Domain;
using RackClick.Server;
using Xunit;

namespace RackClick.Quality.Tests;

public sealed class PhysicalMediaRulesTests
{
    [Theory]
    [InlineData("sfp56")]
    [InlineData("qsfpdd")]
    public void NewMediaKeepTheirExactFamily(string type)
    {
        Assert.Equal(type, InventoryRules.PortType(type));
        Assert.Equal(type, InventoryRules.Family(type));
        InventoryRules.RequireConnectorPair(type, type);
        InventoryRules.RequireConnectorPair(type, type, true);
        foreach (string other in InventoryRules.PortTypes.Where(other => other != type))
        {
            var error = Assert.Throws<DomainError>(() => InventoryRules.RequireConnectorPair(type, other));
            Assert.Equal(409, error.Status);
            Assert.Equal("connection_incompatible", error.Code);
            Assert.Throws<DomainError>(() => InventoryRules.RequireConnectorPair(other, type));
        }
    }

    [Theory]
    [InlineData("qsfp-dd")]
    [InlineData("qsfp_dd")]
    [InlineData("qsfp56")]
    [InlineData("sfp56-dd")]
    [InlineData("osfp")]
    public void UndeclaredAliasesStayInvalid(string type)
    {
        var error = Assert.Throws<DomainError>(() => InventoryRules.PortType(type));
        Assert.Equal(422, error.Status);
        Assert.Equal("port_type_invalid", error.Code);
    }

    [Fact]
    public void LegacyManualPolicyAndHardwareExactnessArePreserved()
    {
        InventoryRules.RequireConnectorPair("rj45", "sfp");
        InventoryRules.RequireConnectorPair("sfp", "sfp28");
        InventoryRules.RequireConnectorPair("rj45", "rj45_poe", true);
        Assert.Throws<DomainError>(() => InventoryRules.RequireConnectorPair("sfp", "sfp28", true));
        InventoryRules.RequirePowerPair("power", "inlet", "power", "outlet");
        Assert.Throws<DomainError>(() => InventoryRules.RequirePowerPair("power", "inlet", "power", "inlet"));
    }

    [Fact]
    public void OpenApiSupportsBothFamiliesAndTwentyThreePaletteKeys()
    {
        var document = JsonSerializer.SerializeToElement(OpenApiDocument.Create());
        var schemas = document.GetProperty("components").GetProperty("schemas");
        var palette = schemas.GetProperty("UserPortColorsMap");
        Assert.Equal(23, palette.GetProperty("maxProperties").GetInt32());
        Assert.Equal(23, palette.GetProperty("properties").EnumerateObject().Count());
        foreach (string type in new[] { "sfp56", "qsfpdd" })
        {
            Assert.True(palette.GetProperty("properties").TryGetProperty(type, out _));
            foreach (string schema in new[] { "InventoryCsvRequest", "InventorySpreadsheetRequest" })
                Assert.Contains(type, schemas.GetProperty(schema).GetProperty("properties").GetProperty("family")
                    .GetProperty("enum").EnumerateArray().Select(value => value.GetString()));
        }
    }

    [Fact]
    public void CurrentCatalogueStillHasTheReviewedPhysicalMediaContract()
    {
        var historical = InventoryHardwareProfiles.All.Where(profile => profile.Revision is not
            ("german-cpe-20261103-v1" or "german-repeaters-20261103-v1")).ToArray();
        Assert.Equal(868, historical.Length);
        Assert.Equal(862, historical.Count(profile => profile.Manufacturer is not null));
        Assert.Equal(884, InventoryHardwareProfiles.All.Count);
        Assert.Equal(878, InventoryHardwareProfiles.All.Count(profile => profile.Manufacturer is not null));
        Assert.Equal(6, InventoryHardwareProfiles.All.Count(profile => profile.Revision == "german-cpe-20261103-v1"));
        Assert.Equal(10, InventoryHardwareProfiles.All.Count(profile => profile.Revision == "german-repeaters-20261103-v1"));
        Assert.Equal(48, SchemaMigrations.LatestVersion);
    }
}
