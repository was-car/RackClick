using Npgsql;
using RackClick.Domain;

namespace RackClick.Server;

public sealed partial class PostgresStore
{
    public async Task<string> ReadUserGroups(Actor actor, CancellationToken ct)
    {
        await using var db = await source.OpenConnectionAsync(ct);
        await using var tx = await db.BeginTransactionAsync(System.Data.IsolationLevel.RepeatableRead, ct);
        await RequireSecurity(db, tx, actor, ct);
        await using var command = Command(db, tx, """
            SELECT jsonb_build_object('revision',h.revision,'groups',COALESCE((
              SELECT jsonb_agg(jsonb_build_object('id',g.id,'name',g.name,
                'members',COALESCE((SELECT jsonb_agg(jsonb_build_object('id',u.id,'userName',u.username,'active',u.active) ORDER BY u.username,u.id)
                  FROM user_group_member m JOIN app_user u ON u.systemhaus_id=m.systemhaus_id AND u.id=m.user_id
                  WHERE m.systemhaus_id=h.id AND m.group_id=g.id),'[]'::jsonb),
                'grants',COALESCE((SELECT jsonb_agg(jsonb_build_object('id',p.id,'capability',p.capability,
                  'scope',CASE WHEN p.customer_id IS NOT NULL THEN 'customer' WHEN p.customer_group_id IS NOT NULL THEN 'customerGroup' ELSE 'systemhaus' END,
                  'target',CASE WHEN p.customer_id IS NOT NULL THEN jsonb_build_object('id',c.id,'name',c.name)
                    WHEN p.customer_group_id IS NOT NULL THEN jsonb_build_object('id',cg.id,'name',cg.name) ELSE NULL END)
                  ORDER BY p.capability,p.id)
                  FROM permission_grant p LEFT JOIN customer c ON c.systemhaus_id=p.systemhaus_id AND c.id=p.customer_id
                    LEFT JOIN customer_group cg ON cg.systemhaus_id=p.systemhaus_id AND cg.id=p.customer_group_id
                  WHERE p.systemhaus_id=h.id AND p.user_group_id=g.id),'[]'::jsonb)) ORDER BY g.name,g.id)
              FROM user_group g WHERE g.systemhaus_id=h.id),'[]'::jsonb))::text
            FROM systemhaus h WHERE h.id=@house
            """, ("house", actor.HouseId));
        string result = await command.ExecuteScalarAsync(ct) as string ?? throw new DomainError(404, "not_found");
        await tx.CommitAsync(ct);
        return result;
    }

    public async Task<string> ReadCustomerGroups(Actor actor, CancellationToken ct)
    {
        await using var db = await source.OpenConnectionAsync(ct);
        await using var tx = await db.BeginTransactionAsync(System.Data.IsolationLevel.RepeatableRead, ct);
        await RequireSecurity(db, tx, actor, ct);
        await using var command = Command(db, tx, """
            SELECT jsonb_build_object('revision',h.revision,'groups',COALESCE((
              SELECT jsonb_agg(jsonb_build_object('id',g.id,'name',g.name,'customers',COALESCE((
                SELECT jsonb_agg(jsonb_build_object('id',c.id,'name',c.name) ORDER BY c.name,c.id)
                FROM customer_group_member m JOIN customer c ON c.systemhaus_id=m.systemhaus_id AND c.id=m.customer_id
                WHERE m.systemhaus_id=h.id AND m.group_id=g.id),'[]'::jsonb)) ORDER BY g.name,g.id)
              FROM customer_group g WHERE g.systemhaus_id=h.id),'[]'::jsonb))::text
            FROM systemhaus h WHERE h.id=@house
            """, ("house", actor.HouseId));
        string result = await command.ExecuteScalarAsync(ct) as string ?? throw new DomainError(404, "not_found");
        await tx.CommitAsync(ct);
        return result;
    }
}
