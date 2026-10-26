using System.Text.Json.Nodes;
using Npgsql;
using RackClick.Domain;
using static RackClick.Server.InventoryJson;

namespace RackClick.Server;

public sealed partial class InventoryStore
{
    private static async Task<Change> CreateFromSharedTemplate(NpgsqlConnection db, NpgsqlTransaction tx, Actor actor,
        Guid customer, JsonObject payload, CancellationToken ct)
    {
        CatalogKeys(payload, ["templateId", "definitionVersion", "definitionSha256", "kind", "rackId", "roomId", "name", "color", "poeBudget", "notes"]);
        Guid template = Id(payload, "templateId"); int version = Integer(payload, "definitionVersion", 1, 1);
        string hash = String(payload, "definitionSha256");
        if (hash.Length != 64 || hash.Any(c => c is not (>= '0' and <= '9' or >= 'a' and <= 'f')))
            throw new DomainError(422, "request_invalid");
        var definition = await SharedDeviceTemplates.ForCreation(db, tx, actor, customer, template, version, hash, ct);
        return await CreateFromTemplateDefinition(db, tx, actor, customer, payload, template, version, hash, definition, ct);
    }
}
