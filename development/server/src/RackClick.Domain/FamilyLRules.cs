using System.Text.Json.Nodes;

namespace RackClick.Domain;

public static class FamilyLRules
{
    public static readonly string[] ExtraTypes = ["ipc", "fiber", "sfpdd", "cfp2", "sas", "dsl", "telephony", "isdn", "expansion", "power_dc"];
    public static bool IsPower(string type) => type is "power" or "power_dc";
    public static bool IsRoom(string kind) => kind is "wall" or "pole" or "din" or "floor" or "tabletop";
    public static string? Descriptor(string type, string? value)
    {
        if (value is null) return null;
        bool extra = type switch
        {
            "ipc" => value is "belden-revconnect-core",
            "fiber" => value is "lc-duplex-upc" or "lc-simplex-upc" or "sc-duplex-upc" or "sc-simplex-upc" or "sc-simplex-apc",
            "sfpdd" => value is "sfp-dd",
            "cfp2" => value is "cfp2",
            "sas" => value is "sff-8644" or "sff-8088",
            "dsl" => value is "dsl-8p8c" or "dsl-rj11",
            "telephony" => value is "voice-8p8c" or "voice-rj11" or "voice-tae",
            "isdn" => value is "isdn-8p8c",
            "expansion" => value is "avaya-ipoffice-expansion-8p8c",
            "power_dc" => value is "dc-barrel" or "unifi-smartpower" or "usb-c-pd" or "dc-terminal-2p" or "dc-terminal-3p" or "dc-terminal-6p",
            "console" => value is "serial-mini-din8" or "serial-usb-c" or "serial-mini-usb" or "serial-micro-usb",
            "power" => value is "schuko-f" or "eu-2pin-plug",
            _ => false
        };
        return extra ? value : PhysicalConnectors.Validate(type, value);
    }
    public static string? Feature(string name, string? value)
    {
        if (value is null) return null;
        bool valid = name switch
        {
            "physicalFace" => value is "front" or "rear" or "top" or "bottom",
            "interfaceRole" => value is "ethernet" or "storage" or "cluster" or "ha" or "management" or "optical-line" or "optical-client" or "serial" or "proprietary" or "voice" or "dsl",
            "signalRole" => value is "tx" or "rx" or "bidi" or "passive",
            "powerSystem" => value is "dc" or "usb-pd" or "unifi-smartpower",
            _ => false
        };
        return valid ? value : throw new DomainError(422, "hardware_metadata_invalid");
    }
    public static void PowerPair(string a, string ar, string? systemA, string b, string br, string? systemB)
    {
        if (a != "power_dc" && b != "power_dc") { InventoryRules.RequirePowerPair(a, ar, b, br); return; }
        if (a != "power_dc" || b != "power_dc" || ar is not ("inlet" or "outlet") || br is not ("inlet" or "outlet") || ar == br ||
            Feature("powerSystem", systemA) is null || Feature("powerSystem", systemB) is null || systemA != systemB)
            throw new DomainError(409, "connection_incompatible");
    }
}
