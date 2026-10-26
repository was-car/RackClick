using System.Text.Json.Nodes;
using Npgsql;
using RackClick.Domain;

namespace RackClick.Server;

public sealed partial class InventoryStore
{
    // Evidence for a future structural inverse. It never supplies an inverse from a client snapshot.
    private static JsonObject UnavailableGroupEditEvidence() => new()
    {
        ["formatVersion"] = 1, ["complete"] = false, ["reason"] = "size_limit"
    };

    private static async Task<JsonObject> CaptureGroupEditEvidence(NpgsqlConnection db, NpgsqlTransaction tx,
        Actor actor, Guid customer, Guid device, CancellationToken ct)
    {
        await using var command = Cmd(db, tx, """
            WITH groups AS MATERIALIZED (
                SELECT g.* FROM inventory_port_group g
                WHERE g.systemhaus_id=@house AND g.customer_id=@customer AND g.device_id=@device
            ), ports AS MATERIALIZED (
                SELECT p.* FROM inventory_port p
                WHERE p.systemhaus_id=@house AND p.customer_id=@customer AND p.device_id=@device
            ), connections AS MATERIALIZED (
                SELECT c.* FROM inventory_connection c
                WHERE c.systemhaus_id=@house AND c.customer_id=@customer
                  AND EXISTS (SELECT 1 FROM inventory_connection_endpoint e JOIN ports p ON p.id=e.port_id
                    WHERE e.systemhaus_id=@house AND e.customer_id=@customer AND e.connection_id=c.id)
            ), evidence AS (
                SELECT jsonb_build_object(
                    'formatVersion',1,'complete',true,'systemhausId',@house,'customerId',@customer,'deviceId',@device,
                    'groups',(SELECT coalesce(jsonb_agg(to_jsonb(g) ORDER BY g.id),'[]'::jsonb) FROM groups g),
                    'ports',(SELECT coalesce(jsonb_agg(to_jsonb(p) ORDER BY p.id),'[]'::jsonb) FROM ports p),
                    'connections',(SELECT coalesce(jsonb_agg(to_jsonb(c) ORDER BY c.id),'[]'::jsonb) FROM connections c),
                    'connectionEndpoints',(SELECT coalesce(jsonb_agg(to_jsonb(e) ORDER BY e.connection_id,e.ordinal),'[]'::jsonb)
                        FROM inventory_connection_endpoint e WHERE e.systemhaus_id=@house AND e.customer_id=@customer
                          AND EXISTS (SELECT 1 FROM connections c WHERE c.id=e.connection_id))
                ) AS body
            )
            SELECT CASE WHEN octet_length(body::text)<=8388608 THEN body::text ELSE NULL END FROM evidence
            """, ("house", actor.HouseId), ("customer", customer), ("device", device));
        var value = await command.ExecuteScalarAsync(ct);
        return value is string json ? JsonNode.Parse(json)!.AsObject() : UnavailableGroupEditEvidence();
    }
}
