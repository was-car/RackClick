using System.Text.Json;
using System.Text.Json.Nodes;
using RackClick.Domain;

namespace RackClick.Server;

internal static class InventoryJson
{
    public static JsonObject Object(JsonElement value)
    {
        if (value.ValueKind != JsonValueKind.Object) throw new DomainError(422, "payload_invalid");
        try
        {
            // JsonNode parses lazily. Force decoding and reject duplicate keys here,
            // including nested extensions, before deferred access can escape validation.
            Validate(value);
            return JsonNode.Parse(value.GetRawText())!.AsObject();
        }
        catch (Exception e) when (e is JsonException or InvalidOperationException or ArgumentException)
        { throw new DomainError(422, "payload_invalid"); }
    }
    private static void Validate(JsonElement value)
    {
        if (value.ValueKind == JsonValueKind.Object)
        {
            var names = new HashSet<string>(StringComparer.Ordinal);
            foreach (var property in value.EnumerateObject())
            {
                if (!names.Add(property.Name)) throw new DomainError(422, "payload_invalid");
                Validate(property.Value);
            }
        }
        else if (value.ValueKind == JsonValueKind.Array)
            foreach (var item in value.EnumerateArray()) Validate(item);
        else if (value.ValueKind == JsonValueKind.String)
            _ = value.GetString();
    }
    public static string Canonical(JsonNode? value)
    {
        JsonNode? Sort(JsonNode? node) => node switch
        {
            JsonObject obj => new JsonObject(obj.OrderBy(p => p.Key, StringComparer.Ordinal)
                .Select(p => KeyValuePair.Create(p.Key, Sort(p.Value)))),
            JsonArray arr => new JsonArray(arr.Select(Sort).ToArray()),
            _ => node?.DeepClone()
        };
        return Sort(value)?.ToJsonString() ?? "null";
    }
    public static Guid Id(JsonObject obj, string key)
        => Guid.TryParse(String(obj, key), out var id) && id != Guid.Empty ? id : throw new DomainError(422, "object_id_invalid");
    public static Guid? OptionalId(JsonObject obj, string key) => obj[key] is null ? null : Id(obj, key);
    public static string String(JsonObject obj, string key, string? fallback = null)
    {
        if (!obj.TryGetPropertyValue(key, out var node) || node is null)
            return fallback ?? throw new DomainError(422, "field_required");
        try { return node.GetValue<string>(); }
        catch (InvalidOperationException) { throw new DomainError(422, "field_invalid"); }
    }
    public static string Text(JsonObject obj, string key, int maximum = 2000, string fallback = "")
    {
        var value = String(obj, key, fallback);
        if (value.Length == 0) return value;
        return Names.Validate(value, maximum);
    }
    public static int Integer(JsonObject obj, string key, int minimum, int maximum, int? fallback = null)
    {
        if (obj[key] is null && fallback.HasValue) return fallback.Value;
        if (obj[key] is not JsonValue value || !value.TryGetValue<int>(out int result) || result < minimum || result > maximum)
            throw new DomainError(422, "number_invalid");
        return result;
    }
    public static decimal? Number(JsonObject obj, string key, decimal maximum)
    {
        if (obj[key] is null) return null;
        if (obj[key] is not JsonValue value || !value.TryGetValue<decimal>(out decimal result) || result < 0 || result > maximum)
            throw new DomainError(422, "number_invalid");
        return result;
    }
    public static bool Boolean(JsonObject obj, string key, bool fallback = false)
    {
        if (obj[key] is null) return fallback;
        if (obj[key] is not JsonValue value || !value.TryGetValue<bool>(out bool result)) throw new DomainError(422, "field_invalid");
        return result;
    }
    public static JsonArray Array(JsonObject obj, string key, int maximum = 256, bool optional = false)
    {
        if (optional && obj[key] is null) return [];
        if (obj[key] is not JsonArray array || array.Count > maximum) throw new DomainError(422, "array_invalid");
        return array;
    }
    public static Guid[] Ids(JsonObject obj, string key, bool optional = false)
    {
        var values = Array(obj, key, optional: optional).Select(n =>
            Guid.TryParse(n?.ToString(), out var id) && id != Guid.Empty ? id : throw new DomainError(422, "object_id_invalid")).ToArray();
        if (values.Distinct().Count() != values.Length) throw new DomainError(422, "duplicate_ids");
        return values;
    }
    public static string Properties(JsonObject input, JsonObject? existing = null)
    {
        if (input["properties"] is not null && input["properties"] is not JsonObject) throw new DomainError(422, "properties_invalid");
        var result = (JsonObject?)existing?.DeepClone() ?? new JsonObject();
        void Merge(JsonObject target, JsonObject patch)
        {
            foreach (var item in patch)
                if (item.Value is JsonObject child && target[item.Key] is JsonObject current) Merge(current, child);
                else target[item.Key] = item.Value?.DeepClone();
        }
        if (input["properties"] is JsonObject patch) Merge(result, patch);
        var json = result.ToJsonString();
        if (System.Text.Encoding.UTF8.GetByteCount(json) > 8192) throw new DomainError(422, "properties_too_large");
        return json;
    }
    public static string? Color(JsonObject obj, string key = "color")
    {
        if (obj[key] is null) return null;
        string color = String(obj, key);
        if (color.Length != 7 || color[0] != '#' || color[1..].Any(c => !Uri.IsHexDigit(c))) throw new DomainError(422, "color_invalid");
        return color;
    }
}

public sealed record InventoryCommandRequest(string? Type, JsonElement Payload);
