using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;
using Npgsql;
using RackClick.Domain;

namespace RackClick.Server;

public sealed record InventoryCatalogCategory(string Key, string Label, IReadOnlyList<string> PresetKeys);
public sealed record InventoryCatalogPort(int Gn, int SortOrder, string Type, string Label, string Status,
    bool Poe, decimal? Watts, string? Color, string Face, string PowerRole, JsonElement Properties);
public sealed record InventoryCatalogGroup(string Key, string Type, string Name, string Prefix, int SortOrder,
    IReadOnlyList<InventoryCatalogPort> Ports);
public sealed record InventoryCatalogPreset(string Key, string CategoryKey, string Label, string Icon, string Color,
    int SizeU, decimal? PoeBudget, IReadOnlyList<InventoryCatalogGroup> PortGroups);
public sealed record InventoryCatalogSnapshot(Guid CustomerId, long Revision, string Language, string CatalogVersion,
    string CatalogSha256, IReadOnlyList<InventoryCatalogCategory> Categories, IReadOnlyList<InventoryCatalogPreset> Presets);

// Immutable product reference, generated from the hash-checked adopted RC9 source. Not user templates or inventory.
internal static class InventoryRc9Catalog
{
    internal const string Version = "rc9-base-v1";
    private sealed record Source(string Path, string Sha256);
    private sealed record Language(IReadOnlyList<InventoryCatalogCategory> Categories, IReadOnlyList<InventoryCatalogPreset> Presets);
    private sealed record Catalog(string CatalogVersion, Source Source, Dictionary<string, Language> Languages);
    private static readonly Lazy<Catalog> Data = new(Load);
    internal static string Sha256 => InventoryRc9CatalogData.Sha256;
    internal static string ValidateLanguage(string value) => value is "en" or "de" or "es"
        ? value : throw new DomainError(422, "request_invalid");

    private static Catalog Load()
    {
        void Require(bool condition) { if (!condition) throw new InvalidOperationException("RC9 catalog reference invalid"); }
        string digest = Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes(InventoryRc9CatalogData.Json)));
        Require(digest == Sha256 && digest.Length == 64);
        var data = JsonSerializer.Deserialize<Catalog>(InventoryRc9CatalogData.Json, new JsonSerializerOptions(JsonSerializerDefaults.Web)
            { UnmappedMemberHandling = JsonUnmappedMemberHandling.Disallow })
            ?? throw new InvalidOperationException("RC9 catalog reference missing");
        Require(data.CatalogVersion == Version && data.Source is not null && data.Source.Sha256.Length == 64
            && data.Languages is not null && data.Languages.Keys.Order(StringComparer.Ordinal).SequenceEqual(new[] { "de", "en", "es" }));
        foreach (var language in data.Languages!.Values)
        {
            Require(language.Categories.Count == 7 && language.Presets.Count == 33);
            Require(language.Categories.Select(c => c.Key).Distinct(StringComparer.Ordinal).Count() == 7
                && language.Presets.Select(p => p.Key).Distinct(StringComparer.Ordinal).Count() == 33);
            var categorized = language.Categories.SelectMany(c => c.PresetKeys).ToArray();
            Require(categorized.Length == 33 && categorized.Distinct(StringComparer.Ordinal).Count() == 33
                && categorized.ToHashSet(StringComparer.Ordinal).SetEquals(language.Presets.Select(p => p.Key)));
            foreach (var preset in language.Presets)
            {
                Require(language.Categories.Any(c => c.Key == preset.CategoryKey && c.PresetKeys.Contains(preset.Key))
                    && preset.SizeU is >= 1 and <= 1000 && preset.PortGroups.Count <= 32
                    && preset.PoeBudget is null or >= 0 and < 1000000);
                _ = Names.Validate(preset.Label); _ = FreeText.Validate(preset.Icon, 100);
                Require(ValidColor(preset.Color));
                for (int g = 0; g < preset.PortGroups.Count; g++)
                {
                    var group = preset.PortGroups[g];
                    Require(group.Key == "g" + (g + 1) && group.SortOrder == g && group.Ports.Count is >= 1 and <= 96
                        && InventoryRules.Family(group.Type) == group.Type);
                    _ = FreeText.Validate(group.Name, 100); _ = FreeText.Validate(group.Prefix, 100);
                    for (int i = 0; i < group.Ports.Count; i++)
                    {
                        var port = group.Ports[i];
                        Require(port.Gn > 0 && port.SortOrder == i && InventoryRules.Family(port.Type) == group.Type
                            && (!port.Poe || group.Type == "rj45") && (port.Type == "rj45_poe") == port.Poe
                            && (port.Type == "power" || port.PowerRole == "unspecified")
                            && (port.Color is null || ValidColor(port.Color))
                            && port.Properties.ValueKind == JsonValueKind.Object && !port.Properties.EnumerateObject().Any());
                        _ = InventoryRules.Status(port.Status); _ = InventoryRules.Face(port.Face);
                        _ = InventoryRules.PowerRole(port.PowerRole); _ = InventoryRules.Watts(port.Watts);
                        _ = FreeText.Validate(port.Label, 500);
                    }
                }
            }
        }
        return data;
    }

    internal static bool ValidColor(string value) => value.Length == 7 && value[0] == '#' && value[1..].All(Uri.IsHexDigit);
    internal static InventoryCatalogSnapshot Snapshot(Guid customer, long revision, string language)
    {
        var data = Data.Value.Languages[ValidateLanguage(language)];
        return new(customer, revision, language, Version, Sha256, data.Categories, data.Presets);
    }
    internal static InventoryCatalogPreset Preset(string key, string version, string sha256, string language)
    {
        if (version != Version || sha256 != Sha256) throw new DomainError(409, "catalog_changed");
        return Data.Value.Languages[ValidateLanguage(language)].Presets.FirstOrDefault(p => p.Key == key)
            ?? throw new DomainError(422, "preset_invalid");
    }
}

public sealed partial class InventoryStore
{
    public async Task<InventoryCatalogSnapshot> ReadCatalog(Actor actor, Guid customer, long expected, IQueryCollection query, CancellationToken ct)
    {
        await using var db = await source.OpenConnectionAsync(ct);
        await using var tx = await db.BeginTransactionAsync(System.Data.IsolationLevel.ReadCommitted, ct);
        await RequireRead(db, tx, actor, customer, ct);
        long revision;
        await using (var command = Cmd(db, tx, "SELECT revision FROM customer WHERE systemhaus_id=@house AND id=@customer FOR SHARE",
            ("house", actor.HouseId), ("customer", customer)))
            revision = await command.ExecuteScalarAsync(ct) is long value ? value : throw new DomainError(404, "not_found");
        await PostgresStore.RequireCurrentSession(db, tx, actor, ct);
        await RequireRead(db, tx, actor, customer, ct);
        Revisions.Require(expected, revision);
        if (query.Count != 1 || query.Any(p => p.Key != "language") || !query.TryGetValue("language", out var language) || language.Count != 1)
            throw new DomainError(422, "request_invalid");
        var result = InventoryRc9Catalog.Snapshot(customer, revision, InventoryRc9Catalog.ValidateLanguage(language.ToString()));
        await PostgresStore.RequireCurrentSession(db, tx, actor, ct);
        await RequireRead(db, tx, actor, customer, ct);
        await tx.CommitAsync(ct);
        return result;
    }
}
