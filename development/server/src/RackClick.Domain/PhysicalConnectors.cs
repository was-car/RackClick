namespace RackClick.Domain;

/// <summary>Physical form classification only; cord ends, pinout and electrical suitability are unspecified.</summary>
public static class PhysicalConnectors
{
    public static string? Validate(string type, string? value)
    {
        if (value is null) return null;
        bool valid = type switch
        {
            "power" => value is "iec-c13" or "iec-c14" or "iec-c19" or "iec-c20" or "nema-5-15p" or "nema-5-15r" or "nema-5-20p" or "nema-5-20r" or "nema-l5-30p" or "nema-l5-30r" or "nema-l6-20p" or "nema-l6-20r" or "nema-l6-30p" or "nema-l6-30r" or "iec60309-16a-2p-e-plug" or "iec60309-16a-2p-e-connector" or "iec60309-32a-2p-e-plug",
            "console" => value is "serial-8p8c" or "serial-10p10c" or "serial-de9" or "serial-rj12",
            "idc" => value is "idc-110" or "idc-dual-110-krone",
            _ => false
        };
        return valid ? value : throw new DomainError(422, "physical_connector_invalid");
    }
}
