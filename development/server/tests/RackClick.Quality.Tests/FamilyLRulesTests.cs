using System.Reflection;
using System.Text.Json.Nodes;
using RackClick.Domain;
using RackClick.Server;
using Xunit;

namespace RackClick.Quality.Tests;

public sealed class FamilyLRulesTests
{
    [Fact]
    public void NewMediaAreExactWithoutChangingLegacyManualPolicy()
    {
        foreach (string type in FamilyLRules.ExtraTypes)
        {
            Assert.Equal(type, InventoryRules.Family(type));
            InventoryRules.RequireConnectorPair(type, type);
            foreach (string other in InventoryRules.PortTypes.Where(other => other != type))
                Assert.Throws<DomainError>(() => InventoryRules.RequireConnectorPair(type, other));
        }
        InventoryRules.RequireConnectorPair("rj45", "sfp");
        Assert.Throws<DomainError>(() => InventoryRules.PortType("sfp-dd"));
    }

    [Fact]
    public void ExtensionClassifierPreservesBaseAndRejectsWrongRawType()
    {
        Assert.Equal("schuko-f", FamilyLRules.Descriptor("power", "schuko-f"));
        Assert.Throws<DomainError>(() => PhysicalConnectors.Validate("power", "schuko-f"));
        Assert.Equal("iec-c13", FamilyLRules.Descriptor("power", "iec-c13"));
        Assert.Equal("sff-8644", FamilyLRules.Descriptor("sas", "sff-8644"));
        Assert.Equal("belden-revconnect-core", FamilyLRules.Descriptor("ipc", "belden-revconnect-core"));
        Assert.Throws<DomainError>(() => FamilyLRules.Descriptor("rj45", "belden-revconnect-core"));
        Assert.Throws<DomainError>(() => FamilyLRules.Descriptor("sas", "SFF-8644"));
    }

    [Fact]
    public void DcRequiresSameSystemAndOppositeRolesWhileAcCordPolicyRemains()
    {
        foreach (string system in new[] { "dc", "usb-pd", "unifi-smartpower" })
            FamilyLRules.PowerPair("power_dc", "outlet", system, "power_dc", "inlet", system);
        Assert.Throws<DomainError>(() => FamilyLRules.PowerPair("power_dc", "outlet", "unifi-smartpower", "power_dc", "inlet", "dc"));
        Assert.Throws<DomainError>(() => FamilyLRules.PowerPair("power_dc", "outlet", "dc", "power", "inlet", null));
        Assert.Throws<DomainError>(() => FamilyLRules.PowerPair("power_dc", "inlet", "dc", "power_dc", "inlet", "dc"));
        Assert.Throws<DomainError>(() => FamilyLRules.PowerPair("power_dc", "outlet", null, "power_dc", "inlet", "dc"));
        FamilyLRules.PowerPair("power", "outlet", null, "power", "inlet", null);
    }

    [Fact]
    public void PartialDimensionsDoNotInventAHeightFromRackUnits()
    {
        var profile = new InventoryHardwareProfiles.Profile("partial", 2, 447m, null, null, "#123456", []);
        Assert.Null(profile.HeightMm);
        Assert.Null(profile.DepthMm);
        Assert.Equal(2, profile.RackUnits);
        Assert.Equal("main", new InventoryHardwareProfiles.Slot("main", 440m, 280m, 500m).Key);
    }

    [Fact]
    public void ManualPortGroupLimitRemains96AndFeaturesAreClosed()
    {
        var method = typeof(InventoryStore).GetMethod("AddGroup", BindingFlags.NonPublic | BindingFlags.Static)!;
        Assert.Equal(96, method.GetParameters().Last().DefaultValue);
        Assert.Equal("top", FamilyLRules.Feature("physicalFace", "top"));
        Assert.Equal("storage", FamilyLRules.Feature("interfaceRole", "storage"));
        Assert.Equal("tx", FamilyLRules.Feature("signalRole", "tx"));
        Assert.Throws<DomainError>(() => FamilyLRules.Feature("physicalFace", "TOP"));
    }

    [Fact]
    public void MalformedExternalPowerSystemIsDomainErrorRatherThan500()
    {
        var method = typeof(InventoryStore).GetMethod("PowerSystem", BindingFlags.NonPublic | BindingFlags.Static)!;
        foreach (JsonNode value in new JsonNode[] { JsonValue.Create(7)!, new JsonObject(), new JsonArray(), JsonValue.Create("unknown")! })
        {
            var port = new JsonObject { ["type"] = "power_dc", ["properties"] = new JsonObject { ["hardwarePowerSystem"] = value } };
            var error = Assert.Throws<TargetInvocationException>(() => method.Invoke(null, [port]));
            Assert.Equal(422, Assert.IsType<DomainError>(error.InnerException).Status);
        }
    }
}
