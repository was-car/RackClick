using RackClick.Domain;

int passed = 0;
void Check(string name, Action body)
{
    try { body(); passed++; Console.WriteLine($"PASS {name}"); }
    catch (Exception e) { Console.Error.WriteLine($"FAIL {name}: {e.Message}"); Environment.ExitCode = 1; }
}
void Assert(bool ok) { if (!ok) throw new Exception("Assertion failed"); }
void Error(int status, string code, Action body)
{
    try { body(); } catch (DomainError e) when (e.Status == status && e.Code == code) { return; }
    throw new Exception($"Expected {status}/{code}");
}
Check("custom multilingual names remain unchanged", () => Assert(Names.Validate("  Wascar · München <A> \"B\"  ") == "Wascar · München <A> \"B\""));
Check("empty name is rejected", () => Error(422, "name_required", () => Names.Validate(" \t ")));
Check("missing name is rejected", () => Error(422, "name_required", () => Names.Validate(null)));
Check("control characters are rejected", () => Error(422, "name_invalid", () => Names.Validate("Rack\u0000A")));
Check("name limit counts Unicode scalar values", () => Assert(Names.Validate(string.Concat(Enumerable.Repeat("🔌", 100))).Length == 200));
Check("overlong name is rejected", () => Error(422, "name_invalid", () => Names.Validate(new string('a', 101))));
Check("malformed Unicode name is rejected", () => Error(422, "name_invalid", () => Names.Validate("Rack\ud800")));
Check("username trims and uses invariant lowercase", () => Assert(UserNames.Normalize("  WASCAR.MÜNCHEN  ") == "wascar.münchen"));
Check("username admits one scalar value", () => Assert(UserNames.Normalize("A") == "a"));
Check("username admits 100 BMP scalar values", () => Assert(UserNames.Normalize(new string('A', 100)) == new string('a', 100)));
Check("D007 username admits 51 supplementary scalar values", () => Assert(UserNames.Normalize(string.Concat(Enumerable.Repeat("🔌", 51))).Length == 102));
Check("D007 username admits 100 supplementary scalar values", () => Assert(UserNames.Normalize(string.Concat(Enumerable.Repeat("🔌", 100))).Length == 200));
Check("username trims before counting the boundary", () => Assert(UserNames.Normalize("  " + new string('A', 100) + "  ").Length == 100));
Check("username counts combining marks as scalar values", () => Assert(UserNames.Normalize(string.Concat(Enumerable.Repeat("e\u0301", 50))).Length == 100));
Check("username does not silently normalize Unicode composition", () => Assert(UserNames.Normalize("É") != UserNames.Normalize("E\u0301")));
Check("username invariant folding does not depend on Turkish culture", () => {
    var previous = System.Globalization.CultureInfo.CurrentCulture;
    try { System.Globalization.CultureInfo.CurrentCulture = new("tr-TR"); Assert(UserNames.Normalize("I") == "i"); }
    finally { System.Globalization.CultureInfo.CurrentCulture = previous; }
});
foreach (var invalid in new string?[] { null, "", "  ", new string('a', 101), string.Concat(Enumerable.Repeat("🔌", 101)),
    "a\u0000b", "a\nb", "a\ud800", "\udc00a" })
    Check("invalid username is rejected by the shared policy", () => Error(422, "username_invalid", () => UserNames.Normalize(invalid)));
Check("revision survives invariant formatting", () => Assert(Revisions.Parse(Revisions.ETag(9223372036854775807)) == long.MaxValue));
Check("missing revision prevents blind writes", () => Error(428, "revision_required", () => Revisions.Parse(null)));
foreach (var invalid in new[] { "1", "*", "W/\"1\"", "\"0\"", "\"-1\"", "\"1\",\"2\"", "\"9223372036854775808\"" })
    Check($"invalid revision {invalid}", () => Error(422, "revision_invalid", () => Revisions.Parse(invalid)));
Check("matching revision accepted", () => Revisions.Require(3, 3));
Check("stale revision rejected", () => Error(412, "revision_conflict", () => Revisions.Require(2, 3)));
Guid house = Guid.NewGuid(), otherHouse = Guid.NewGuid(), a = Guid.NewGuid(), b = Guid.NewGuid(), group = Guid.NewGuid();
Check("no grants denies access", () => Assert(!Permissions.Allows([], house, a, Capabilities.InventoryRead)));
Check("grant from another Systemhaus denies access", () => Assert(!Permissions.Allows([new(otherHouse, Capabilities.InventoryRead)], house, a, Capabilities.InventoryRead)));
Check("read grant does not permit editing", () => Assert(!Permissions.Allows([new(house, Capabilities.InventoryRead)], house, a, Capabilities.InventoryEdit)));
Check("client grant permits assigned client", () => Assert(Permissions.Allows([new(house, Capabilities.InventoryRead, a)], house, a, Capabilities.InventoryRead)));
Check("client grant denies another client", () => Assert(!Permissions.Allows([new(house, Capabilities.InventoryRead, a)], house, b, Capabilities.InventoryRead)));
Check("client grant is not global", () => Assert(!Permissions.Allows([new(house, Capabilities.HouseManage, a)], house, null, Capabilities.HouseManage)));
Check("client-group grant follows membership", () => Assert(Permissions.Allows([new(house, Capabilities.InventoryEdit, CustomerGroupId: group)], house, a, Capabilities.InventoryEdit, new HashSet<Guid> { group })));
Check("client-group removal revokes permission", () => Assert(!Permissions.Allows([new(house, Capabilities.InventoryEdit, CustomerGroupId: group)], house, a, Capabilities.InventoryEdit, new HashSet<Guid>())));
Check("client-group grant without client denies access", () => Assert(!Permissions.Allows([new(house, Capabilities.HouseManage, CustomerGroupId: group)], house, null, Capabilities.HouseManage, new HashSet<Guid> { group })));
Check("invalid double scope is denied", () => Assert(!Permissions.Allows([new(house, Capabilities.InventoryRead, a, group)], house, a, Capabilities.InventoryRead, new HashSet<Guid> { group })));
Check("global grant applies only within its Systemhaus", () => Assert(Permissions.Allows([new(house, Capabilities.InventoryRead)], house, b, Capabilities.InventoryRead)));
Check("removing all group grants revokes effective access", () => {
    var grants = new List<Grant> { new(house, Capabilities.InventoryEdit, a) };
    Assert(Permissions.Allows(grants, house, a, Capabilities.InventoryEdit));
    grants.Clear(); Assert(!Permissions.Allows(grants, house, a, Capabilities.InventoryEdit));
});
Check("RJ45 PoE remains in its connector family", () => Assert(InventoryRules.Family("rj45_poe") == "rj45"));
Check("SFP group is not RJ45", () => Assert(InventoryRules.Family("sfp") == "sfp"));
Check("unknown connector type is rejected", () => Error(422, "port_type_invalid", () => InventoryRules.PortType("invented")));
Check("front and rear are presentation values", () => Assert(InventoryRules.Face("front") == "front" && InventoryRules.Face("rear") == "rear"));
Check("unknown port face is rejected", () => Error(422, "port_face_invalid", () => InventoryRules.Face("backside-terminal")));
Check("occupied is derived and not a stored port state", () => Error(422, "port_status_invalid", () => InventoryRules.Status("occupied")));
Check("PoE watts unknown differs from zero", () => Assert(InventoryRules.Watts(null) is null && InventoryRules.Watts(0) == 0));
Check("RC9 documented watts upper boundary accepted", () => Assert(InventoryRules.Watts(90) == 90));
Check("negative watts rejected", () => Error(422, "watts_invalid", () => InventoryRules.Watts(-1)));
Check("watts above RC9 boundary rejected", () => Error(422, "watts_invalid", () => InventoryRules.Watts(90.01m)));
Check("power inlet to outlet accepted", () => InventoryRules.RequirePowerPair("power", "inlet", "power", "outlet"));
Check("unspecified power roles preserve documented uncertainty", () => InventoryRules.RequirePowerPair("power", "unspecified", "power", "unspecified"));
Check("two power inlets rejected", () => Error(409, "connection_incompatible", () => InventoryRules.RequirePowerPair("power", "inlet", "power", "inlet")));
Check("two power outlets rejected", () => Error(409, "connection_incompatible", () => InventoryRules.RequirePowerPair("power", "outlet", "power", "outlet")));
Check("AC and data connectors cannot be joined", () => Error(409, "connection_incompatible", () => InventoryRules.RequirePowerPair("power", "outlet", "rj45", "unspecified")));
Check("rack exactly at capacity accepted", () => InventoryRules.RequireCapacity(42, 40, 2));
Check("rack over capacity rejected", () => Error(409, "rack_capacity_exceeded", () => InventoryRules.RequireCapacity(42, 41, 2)));
Check("capacity arithmetic does not overflow", () => Error(409, "rack_capacity_exceeded", () => InventoryRules.RequireCapacity(42, int.MaxValue, int.MaxValue)));
foreach (var patch in new[] { "none", "planned", "progress", "done", "tested" })
    Check($"RC9 textual patch state {patch} preserved", () => Assert(InventoryRules.Patch(patch) == patch));
Check("patch is not reduced to a boolean", () => Error(422, "patch_status_invalid", () => InventoryRules.Patch("true")));
Check("session digest is never serialized in actor DTO", () => Assert(!System.Text.Json.JsonSerializer.Serialize(
    new Actor(Guid.NewGuid(), Guid.NewGuid(), "synthetic") { SessionTokenHash = "private-marker" }).Contains("private-marker")));
Check("foundation admin receives explicit deletion capability", () => Assert(Capabilities.FoundationAdmin.Contains(Capabilities.InventoryDelete)));
Check("user notes preserve whitespace and multiline content", () => Assert(FreeText.Validate("  Línea 1\r\n\tZeile 2  ", 2000) == "  Línea 1\r\n\tZeile 2  "));
Check("free text rejects NUL without losing Unicode support", () => Error(422, "text_invalid", () => FreeText.Validate("Texto\u0000", 2000)));
Console.WriteLine($"RESULT: {passed} domain tests passed; PostgreSQL/HTTP integration NOT RUN by this suite.");
