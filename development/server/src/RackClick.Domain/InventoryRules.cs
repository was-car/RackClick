namespace RackClick.Domain;

public static class InventoryRules
{
    public static readonly string[] PortTypes = ["rj45", "rj45_poe", "sfp", "sfp28", "qsfp", "mgmt", "console", "power", "usb_a", "usb_c"];
    public static string PortType(string? value) => value is not null && PortTypes.Contains(value, StringComparer.Ordinal)
        ? value : throw new DomainError(422, "port_type_invalid");
    public static string Family(string value) => PortType(value) == "rj45_poe" ? "rj45" : value;
    public static string Status(string? value) => value is "free" or "reserved" or "disabled" or "faulty"
        ? value : throw new DomainError(422, "port_status_invalid");
    public static string Face(string? value) => value is "auto" or "front" or "rear"
        ? value : throw new DomainError(422, "port_face_invalid");
    public static string PowerRole(string? value) => value is "unspecified" or "inlet" or "outlet"
        ? value : throw new DomainError(422, "power_role_invalid");
    public static string Patch(string? value) => value is "none" or "planned" or "progress" or "done" or "tested"
        ? value : throw new DomainError(422, "patch_status_invalid");
    public static void RequirePowerPair(string firstType, string firstRole, string secondType, string secondRole)
    {
        if ((firstType == "power") != (secondType == "power") ||
            (firstType == "power" && firstRole != "unspecified" && firstRole == secondRole))
            throw new DomainError(409, "connection_incompatible");
    }
    public static void RequireCapacity(int rackSize, int used, int added)
    {
        if (rackSize < 1 || rackSize > 1000 || added < 0 || used < 0 || (long)used + added > rackSize)
            throw new DomainError(409, "rack_capacity_exceeded");
    }
    public static decimal? Watts(decimal? value) => value is null or >= 0 and <= 90
        ? value : throw new DomainError(422, "watts_invalid");
}
