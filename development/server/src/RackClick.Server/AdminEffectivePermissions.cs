using Npgsql;
using RackClick.Domain;

namespace RackClick.Server;

public sealed record AdminEffectivePermissionsSnapshot(long Revision, AdminUser User, EffectivePermissions Permissions);

public sealed partial class PostgresStore
{
    public async Task<AdminEffectivePermissionsSnapshot> ReadUserEffectivePermissions(Actor actor, Guid userId, CancellationToken ct)
    {
        await using var db = await source.OpenConnectionAsync(ct);
        await using var tx = await db.BeginTransactionAsync(System.Data.IsolationLevel.RepeatableRead, ct);
        // Check current GLOBAL authority before target lookup, including foreign/absent IDs.
        await RequireSecurity(db, tx, actor, ct);
        if (userId == Guid.Empty) throw new DomainError(422, "request_invalid");
        AdminUser user;
        await using (var cmd = Command(db, tx, "SELECT id,username,active FROM app_user WHERE id=@user AND systemhaus_id=@house", ("user", userId), ("house", actor.HouseId)))
        await using (var rows = await cmd.ExecuteReaderAsync(ct))
        {
            if (!await rows.ReadAsync(ct)) throw new DomainError(404, "not_found");
            user = new(rows.GetGuid(0), rows.GetString(1), rows.GetBoolean(2));
        }
        await using var revision = Command(db, tx, "SELECT revision FROM systemhaus WHERE id=@house", ("house", actor.HouseId));
        long current = (long)(await revision.ExecuteScalarAsync(ct))!;
        EffectivePermissions permissions = user.Active
            ? await QueryPermissions(db, tx, actor.HouseId, userId, ct)
            : new([], [], []);
        await tx.CommitAsync(ct);
        return new(current, user, permissions);
    }
}
