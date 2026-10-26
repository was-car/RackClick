using Npgsql;
using RackClick.Domain;

namespace RackClick.Server;

public sealed record AdminUserSession(Guid Id, DateTime ExpiresAt, bool Current);
public sealed record AdminUserSessionsSnapshot(long Revision, AdminUser User, IReadOnlyList<AdminUserSession> Sessions);

public sealed partial class PostgresStore
{
    public async Task<AdminUserSessionsSnapshot> ReadUserSessions(Actor actor, Guid userId, CancellationToken ct)
    {
        if (userId == Guid.Empty) throw new DomainError(422, "request_invalid");
        await using var db = await source.OpenConnectionAsync(ct);
        await using var tx = await db.BeginTransactionAsync(System.Data.IsolationLevel.RepeatableRead, ct);
        await RequireSecurity(db, tx, actor, ct);
        AdminUser user;
        await using (var cmd = Command(db, tx, "SELECT id,username,active FROM app_user WHERE id=@user AND systemhaus_id=@house", ("user", userId), ("house", actor.HouseId)))
        await using (var rows = await cmd.ExecuteReaderAsync(ct))
        {
            if (!await rows.ReadAsync(ct)) throw new DomainError(404, "not_found");
            user = new(rows.GetGuid(0), rows.GetString(1), rows.GetBoolean(2));
        }
        await using var revision = Command(db, tx, "SELECT revision FROM systemhaus WHERE id=@house", ("house", actor.HouseId));
        long current = (long)(await revision.ExecuteScalarAsync(ct))!;
        var sessions = new List<AdminUserSession>();
        if (user.Active)
        {
            await using var cmd = Command(db, tx, "SELECT id,expires_at,token_hash=@token FROM app_session WHERE user_id=@user AND expires_at>clock_timestamp() ORDER BY expires_at,id", ("user", userId), ("token", actor.SessionTokenHash!));
            await using var rows = await cmd.ExecuteReaderAsync(ct);
            while (await rows.ReadAsync(ct)) sessions.Add(new(rows.GetGuid(0), rows.GetDateTime(1), rows.GetBoolean(2)));
        }
        await tx.CommitAsync(ct);
        return new(current, user, sessions);
    }
}
