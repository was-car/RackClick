namespace RackClick.Server;

/// <summary>Own, immutable synthetic hardware profiles. No vendor model or electrical specification is implied.</summary>
public static partial class InventoryHardwareProfiles
{
    public const string Version = "hw-reference-v1";
    public sealed record Group(string Key, string Type, int Count, string Face, string Name, string Prefix)
    {
        public string PowerRole { get; init; } = "unspecified";
        /// <summary>Classification only; power links have unspecified cord ends.</summary>
        public string? PhysicalConnector { get; init; }
        public string? PhysicalFace { get; init; }
        public string? InterfaceRole { get; init; }
        public string? SignalRole { get; init; }
        public string? PowerSystem { get; init; }
    }
    public sealed record Slot(string Key, decimal WidthMm, decimal HeightMm, decimal DepthMm);
    public sealed record Continuity(string FrontGroupKey, string RearGroupKey, int Count);
    public sealed record Profile(string Key, int RackUnits, decimal? WidthMm, decimal? HeightMm, decimal? DepthMm, string Color,
        IReadOnlyList<Group> Groups, string Revision = Version)
    {
        public string Kind { get; init; } = "rack";
        public string? MountingJson { get; init; }
        public string? ConfigurationJson { get; init; }
        public string? ContinuitiesJson { get; init; }
        public string DefinitionSha256 { get; init; } = "";
        public IReadOnlyList<Slot> Slots { get; init; } = [];
        public Continuity? Passthrough { get; init; }
        public string? Manufacturer { get; init; }
        public string? Family { get; init; }
        public string? Model { get; init; }
        public string? Sku { get; init; }
    }

    /// <summary>Exact, immutable model revisions. No implicit latest-version lookup.</summary>
    public sealed class Registry
    {
        private readonly Dictionary<(string Key, string Revision), Profile> entries = [];
        public IReadOnlyList<Profile> All { get; }
        public Registry(IEnumerable<Profile> profiles)
        {
            var snapshots = new List<Profile>();
            foreach (var profile in profiles)
            {
                if (string.IsNullOrWhiteSpace(profile.Key) || profile.Key.Length > 128 ||
                    string.IsNullOrWhiteSpace(profile.Revision) || profile.Revision.Length > 128 || profile.Groups is null || profile.Slots is null)
                    throw new ArgumentException("hardware_catalog_invalid", nameof(profiles));
                var snapshot = profile with { Groups = Array.AsReadOnly(profile.Groups.ToArray()), Slots = Array.AsReadOnly(profile.Slots.ToArray()) };
                if (!entries.TryAdd((snapshot.Key, snapshot.Revision), snapshot))
                    throw new ArgumentException("hardware_catalog_duplicate_revision", nameof(profiles));
                snapshots.Add(snapshot);
            }
            All = snapshots.AsReadOnly();
        }
        public Profile? Find(string? key, string? revision) => key is not null && revision is not null
            && entries.TryGetValue((key, revision), out var profile) ? profile : null;
    }
    private static readonly Lazy<Registry> Published = new(() => new Registry(ReferenceCatalog.All.Concat(CommercialHardwareProfiles.Catalog.All).Concat(ArubaHardwareProfiles.Catalog.All).Concat(FortinetHardwareProfiles.Catalog.All).Concat(SynologyHardwareProfiles.Catalog.All).Concat(DiskStationHardwareProfiles.Catalog.All).Concat(QnapHardwareProfiles.Catalog.All).Concat(Batch50HardwareProfiles.Catalog.All).Concat(Batch50BHardwareProfiles.Catalog.All).Concat(Batch100HardwareProfiles.Catalog.All).Concat(Batch100BHardwareProfiles.Catalog.All).Concat(Batch100CHardwareProfiles.Catalog.All).Concat(Selected506AHardwareProfiles.Catalog.All).Concat(Selected506BHardwareProfiles.Catalog.All).Concat(Selected506CHardwareProfiles.Catalog.All).Concat(Selected506DHardwareProfiles.Catalog.All).Concat(Selected506EHardwareProfiles.Catalog.All).Concat(Selected506FHardwareProfiles.Catalog.All).Concat(Selected506GHardwareProfiles.Catalog.All).Concat(Selected506HHardwareProfiles.Catalog.All).Concat(Selected506IHardwareProfiles.Catalog.All).Concat(Selected506JHardwareProfiles.Catalog.All).Concat(Selected506KHardwareProfiles.Catalog.All).Concat(Selected506LHardwareProfiles.Catalog.All).Concat(GermanCpeHardwareProfiles.Catalog.All).Concat(GermanRepeatersHardwareProfiles.Catalog.All)));
    // Authenticate classification against the exact published revision and group.
    // Arbitrary unbound/historical properties never become trusted classifications.
    public static string? TrustedPhysicalConnector(string? key, string? revision, string? groupKey, string? portType, string? face, string? stored)
    {
        var group = Find(key, revision)?.Groups.SingleOrDefault(group => group.Key == groupKey);
        return group?.PhysicalConnector is { } declared && declared == stored && group.Face == face &&
            (group.Type == portType || (group.Type == "rj45" && portType == "rj45_poe")) ? declared : null;
    }
    public static IReadOnlyList<Profile> All => Published.Value.All;
    public static Profile? Find(string? key, string? revision) => Published.Value.Find(key, revision);
}
