using System.Globalization;
using System.Text;

namespace RackClick.Domain;

public sealed class DomainError(int status, string code) : Exception(code)
{
    public int Status { get; } = status;
    public string Code { get; } = code;
}

public static class Names
{
    public static string Validate(string? value, int maximum = 100)
    {
        if (value is null) throw new DomainError(422, "name_required");
        var name = value.Trim();
        if (name.Length == 0) throw new DomainError(422, "name_required");
        if (!IsValidUnicode(name) || name.EnumerateRunes().Count() > maximum || name.Any(char.IsControl))
            throw new DomainError(422, "name_invalid");
        // User-supplied display names are never translated, case-folded, or used as resource IDs.
        return name;
    }

    internal static bool IsValidUnicode(string value)
    {
        ReadOnlySpan<char> remaining = value.AsSpan();
        while (!remaining.IsEmpty)
        {
            if (Rune.DecodeFromUtf16(remaining, out _, out int consumed) != System.Buffers.OperationStatus.Done)
                return false;
            remaining = remaining[consumed..];
        }
        return true;
    }
}

public static class FreeText
{
    public static string Validate(string value, int maximum)
    {
        if (!Names.IsValidUnicode(value) || value.EnumerateRunes().Count() > maximum ||
            value.Any(c => char.IsControl(c) && c is not ('\r' or '\n' or '\t')))
            throw new DomainError(422, "text_invalid");
        return value;
    }
}

public static class UserNames
{
    public const int MaximumRunes = 100;

    // Identity policy shared by account creation and login. Preserve the existing
    // invariant lowercase identity; do not translate or silently NFC-normalize it.
    // The limit is Unicode scalar values after trimming, never UTF-16 code units.
    public static string Normalize(string? value)
    {
        try { return Names.Validate(value, MaximumRunes).ToLowerInvariant(); }
        catch (DomainError e) when (e.Code is "name_required" or "name_invalid")
        {
            throw new DomainError(422, "username_invalid");
        }
    }
}

public static class Revisions
{
    public static string ETag(long revision) => $"\"{revision.ToString(CultureInfo.InvariantCulture)}\"";
    public static long Parse(string? etag)
    {
        if (string.IsNullOrWhiteSpace(etag)) throw new DomainError(428, "revision_required");
        if (etag.Length < 3 || etag[0] != '"' || etag[^1] != '"' ||
            !long.TryParse(etag[1..^1], NumberStyles.None, CultureInfo.InvariantCulture, out var n) || n <= 0)
            throw new DomainError(422, "revision_invalid");
        return n;
    }
    public static void Require(long expected, long actual)
    {
        if (expected != actual) throw new DomainError(412, "revision_conflict");
    }
}

public static class Capabilities
{
    public const string HouseRead = "systemhaus.read";
    public const string HouseManage = "systemhaus.manage";
    public const string CustomerCreate = "customer.create";
    public const string CustomerManage = "customer.manage";
    public const string InventoryRead = "inventory.read";
    public const string InventoryEdit = "inventory.edit";
    public const string InventoryDelete = "inventory.delete";
    public const string ReportsExport = "reports.export";
    public const string TemplatesPublish = "templates.publish";
    public const string SecurityManage = "security.manage";
    public static readonly string[] FoundationAdmin =
        [HouseRead, HouseManage, CustomerCreate, CustomerManage, InventoryRead, InventoryEdit, InventoryDelete, SecurityManage, ReportsExport, TemplatesPublish];
}

public sealed record Grant(Guid HouseId, string Capability, Guid? CustomerId = null, Guid? CustomerGroupId = null);
public static class Permissions
{
    public static bool Allows(IEnumerable<Grant> grants, Guid houseId, Guid? customerId,
        string capability, IReadOnlySet<Guid>? customerGroups = null) => grants.Any(g =>
            g.HouseId == houseId && g.Capability == capability &&
            !(g.CustomerId.HasValue && g.CustomerGroupId.HasValue) &&
            ((!g.CustomerId.HasValue && !g.CustomerGroupId.HasValue) ||
             (customerId.HasValue && (g.CustomerId == customerId ||
              (g.CustomerGroupId.HasValue && customerGroups?.Contains(g.CustomerGroupId.Value) == true)))));
}

public sealed record House(Guid Id, string Name, long Revision);
public sealed record Customer(Guid Id, Guid HouseId, string Name, long Revision);
public sealed record Actor(Guid Id, Guid HouseId, string UserName)
{
    [System.Text.Json.Serialization.JsonIgnore]
    public string? SessionTokenHash { get; init; }
}
public sealed record SessionIdentity(Actor Actor, string CsrfHash);
public sealed record PermissionSource(Guid UserGroupId, string UserGroupName, string Capability, string ScopeType, Guid? ScopeId);
public sealed record CustomerPermissions(Guid CustomerId, IReadOnlyList<string> Capabilities);
public sealed record EffectivePermissions(IReadOnlyList<string> SystemhausCapabilities,
    IReadOnlyList<CustomerPermissions> Customers, IReadOnlyList<PermissionSource> Sources);
