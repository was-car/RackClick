using System.Text.Json;
using Npgsql;
using NpgsqlTypes;
using RackClick.Domain;

namespace RackClick.Server;

public sealed partial class PostgresStore(NpgsqlDataSource source)
{
    private static readonly JsonSerializerOptions Json = new(JsonSerializerDefaults.Web);

    private static NpgsqlCommand Command(NpgsqlConnection db, NpgsqlTransaction? tx, string sql,
        params (string Name, object? Value)[] values)
    {
        var cmd = new NpgsqlCommand(sql, db, tx);
        foreach (var (name, value) in values)
        {
            if (value is null) cmd.Parameters.AddWithValue(name, NpgsqlDbType.Uuid, DBNull.Value);
            else cmd.Parameters.AddWithValue(name, value);
        }
        return cmd;
    }

    internal static async Task<bool> Can(NpgsqlConnection db, NpgsqlTransaction? tx, Actor actor,
        Guid? customer, string capability, CancellationToken ct)
    {
        await using var cmd = Command(db, tx, """
            SELECT EXISTS(
              SELECT 1 FROM app_user u
              JOIN user_group_member m ON m.systemhaus_id=u.systemhaus_id AND m.user_id=u.id
              JOIN permission_grant g ON g.systemhaus_id=m.systemhaus_id AND g.user_group_id=m.group_id
              WHERE u.id=@uid AND u.systemhaus_id=@house AND u.active AND g.capability=@cap
                AND ((g.customer_id IS NULL AND g.customer_group_id IS NULL)
                  OR (@customer IS NOT NULL AND g.customer_id=@customer)
                  OR (@customer IS NOT NULL AND EXISTS(
                    SELECT 1 FROM customer_group_member cm WHERE cm.systemhaus_id=@house
                      AND cm.group_id=g.customer_group_id AND cm.customer_id=@customer)))
            )
            """, ("uid", actor.Id), ("house", actor.HouseId), ("cap", capability), ("customer", customer));
        return (bool)(await cmd.ExecuteScalarAsync(ct))!;
    }

    internal static async Task LockOperation(NpgsqlConnection db, NpgsqlTransaction tx, Actor actor, Guid requestId, CancellationToken ct, bool allowReport = false)
    {
        await using var cmd = Command(db, tx, "SELECT pg_advisory_xact_lock(hashtextextended(@key,0))",
            ("key", $"RackClick/operation/{actor.HouseId:D}/{actor.Id:D}/{requestId:D}"));
        await cmd.ExecuteNonQueryAsync(ct);
        if (!allowReport) await RejectReportOperation(db, tx, actor, requestId, ct);
    }

    internal static async Task RejectReportOperation(NpgsqlConnection db, NpgsqlTransaction tx, Actor actor, Guid requestId, CancellationToken ct)
    {
        // Generic recovery/replay must never expose a report artifact using inventory/security authority alone.
        await using var command = Command(db, tx, "SELECT EXISTS(SELECT 1 FROM operation WHERE systemhaus_id=@house AND actor_id=@actor AND request_id=@request AND result_json->>'kind' IN ('report','spreadsheetReport','rc9ExcelReport','inventoryExport'))",
            ("house", actor.HouseId), ("actor", actor.Id), ("request", requestId));
        if (await command.ExecuteScalarAsync(ct) is true) throw new DomainError(404, "not_found");
    }

    internal static async Task RequireCurrentSession(NpgsqlConnection db, NpgsqlTransaction tx, Actor actor, CancellationToken ct)
    {
        if (actor.SessionTokenHash is null) throw new DomainError(401, "authentication_required");
        await using var cmd = Command(db, tx, $"""
            SELECT s.token_hash FROM app_session s JOIN app_user u ON u.id=s.user_id
              WHERE s.token_hash=@token AND s.user_id=@actor AND u.systemhaus_id=@house AND u.active AND s.expires_at>clock_timestamp()
              AND {MfaSessionAllowedSql}
              FOR SHARE OF s,u
            """, ("token", actor.SessionTokenHash), ("actor", actor.Id), ("house", actor.HouseId));
        if (await cmd.ExecuteScalarAsync(ct) is not string) throw new DomainError(401, "authentication_required");
        // The predicate above may run before FOR SHARE waits for an actor/session lock.
        // Keep those locks and evaluate PostgreSQL's wall clock again after acquisition,
        // including in RepeatableRead transactions (whose snapshot time stays unchanged).
        await using var current = Command(db, tx, $"""
            SELECT s.token_hash FROM app_session s JOIN app_user u ON u.id=s.user_id
              WHERE s.token_hash=@token AND s.user_id=@actor AND u.systemhaus_id=@house AND u.active AND s.expires_at>clock_timestamp()
              AND {MfaSessionAllowedSql}
            """, ("token", actor.SessionTokenHash), ("actor", actor.Id), ("house", actor.HouseId));
        if (await current.ExecuteScalarAsync(ct) is not string) throw new DomainError(401, "authentication_required");
    }

    public async Task<SessionIdentity?> Session(string token, CancellationToken ct)
    {
        if (token.Length != 64) return null;
        await using var db = await source.OpenConnectionAsync(ct);
        await using var cmd = Command(db, null, $"""
            SELECT u.id,u.systemhaus_id,u.username,s.csrf_hash FROM app_session s
            JOIN app_user u ON u.id=s.user_id
            WHERE s.token_hash=@token AND s.expires_at>now() AND u.active
              AND {MfaSessionAllowedSql}
            """, ("token", Secrets.Digest(token)));
        await using var row = await cmd.ExecuteReaderAsync(ct);
        return await row.ReadAsync(ct) ? new(new Actor(row.GetGuid(0), row.GetGuid(1), row.GetString(2))
            { SessionTokenHash = Secrets.Digest(token) }, row.GetString(3)) : null;
    }

    internal NpgsqlDataSource DataSource => source;

    // Login sin segundo factor: un usuario con MFA exigido no puede entrar por esta vía (sesión solo tras desafío).
    public async Task<(string Token, string Csrf)> Login(string username, string password, CancellationToken ct)
    {
        var outcome = await Authenticate(username, password, ct);
        return outcome.Session ?? throw new DomainError(401, "mfa_required");
    }

    public async Task Logout(string token, CancellationToken ct)
    {
        await using var db = await source.OpenConnectionAsync(ct);
        await using var cmd = Command(db, null, "DELETE FROM app_session WHERE token_hash=@token", ("token", Secrets.Digest(token)));
        await cmd.ExecuteNonQueryAsync(ct);
    }

    public async Task<EffectivePermissions> ReadPermissions(Actor actor, CancellationToken ct)
    {
        await using var db = await source.OpenConnectionAsync(ct);
        await using var tx = await db.BeginTransactionAsync(System.Data.IsolationLevel.RepeatableRead, ct);
        await using (var active = Command(db, tx,
            "SELECT active FROM app_user WHERE id=@uid AND systemhaus_id=@house",
            ("uid", actor.Id), ("house", actor.HouseId)))
            if (await active.ExecuteScalarAsync(ct) is not true)
                throw new DomainError(401, "authentication_required");

        var permissions = await QueryPermissions(db, tx, actor.HouseId, actor.Id, ct);
        await tx.CommitAsync(ct);
        return permissions;
    }

    // Shared projection only: callers perform their own active-user/authorization checks.
    // Declared sources are preserved; this DTO never authorizes later operations.
    private static async Task<EffectivePermissions> QueryPermissions(NpgsqlConnection db, NpgsqlTransaction tx,
        Guid houseId, Guid userId, CancellationToken ct)
    {
        var sources = new List<PermissionSource>();
        await using (var cmd = Command(db, tx, """
            SELECT ug.id,ug.name,g.capability,
              CASE WHEN g.customer_id IS NOT NULL THEN 'customer'
                   WHEN g.customer_group_id IS NOT NULL THEN 'customerGroup' ELSE 'systemhaus' END,
              COALESCE(g.customer_id,g.customer_group_id)
            FROM user_group_member m
            JOIN user_group ug ON ug.systemhaus_id=m.systemhaus_id AND ug.id=m.group_id
            JOIN permission_grant g ON g.systemhaus_id=m.systemhaus_id AND g.user_group_id=m.group_id
            WHERE m.user_id=@uid AND m.systemhaus_id=@house
            ORDER BY ug.id,g.capability,g.customer_id,g.customer_group_id
            """, ("uid", userId), ("house", houseId)))
        await using (var row = await cmd.ExecuteReaderAsync(ct))
            while (await row.ReadAsync(ct))
                sources.Add(new(row.GetGuid(0), row.GetString(1), row.GetString(2), row.GetString(3),
                    row.IsDBNull(4) ? null : row.GetGuid(4)));

        var customers = new Dictionary<Guid, List<string>>();
        await using (var cmd = Command(db, tx, """
            WITH effective AS (
              SELECT DISTINCT c.id,g.capability
              FROM customer c
              JOIN user_group_member m ON m.systemhaus_id=c.systemhaus_id AND m.user_id=@uid
              JOIN permission_grant g ON g.systemhaus_id=m.systemhaus_id AND g.user_group_id=m.group_id
              WHERE c.systemhaus_id=@house AND (
                (g.customer_id IS NULL AND g.customer_group_id IS NULL) OR g.customer_id=c.id
                OR EXISTS (SELECT 1 FROM customer_group_member cm
                  WHERE cm.systemhaus_id=c.systemhaus_id AND cm.customer_id=c.id AND cm.group_id=g.customer_group_id))
            )
            SELECT e.id,e.capability FROM effective e WHERE EXISTS (
              SELECT 1 FROM effective visible WHERE visible.id=e.id AND visible.capability='inventory.read')
            ORDER BY e.id,e.capability
            """, ("uid", userId), ("house", houseId)))
        await using (var row = await cmd.ExecuteReaderAsync(ct))
            while (await row.ReadAsync(ct))
            {
                Guid id = row.GetGuid(0);
                if (!customers.TryGetValue(id, out var capabilities)) customers[id] = capabilities = [];
                capabilities.Add(row.GetString(1));
            }
        return new(sources.Where(s => s.ScopeType == "systemhaus").Select(s => s.Capability)
            .Distinct(StringComparer.Ordinal).Order(StringComparer.Ordinal).ToArray(),
            customers.Select(c => new CustomerPermissions(c.Key, c.Value)).ToArray(), sources);
    }

    public async Task<House> ReadHouse(Actor actor, CancellationToken ct)
    {
        await using var db = await source.OpenConnectionAsync(ct);
        if (!await Can(db, null, actor, null, Capabilities.HouseRead, ct)) throw new DomainError(403, "forbidden");
        await using var cmd = Command(db, null, "SELECT id,name,revision FROM systemhaus WHERE id=@id", ("id", actor.HouseId));
        await using var row = await cmd.ExecuteReaderAsync(ct);
        if (!await row.ReadAsync(ct)) throw new DomainError(404, "not_found");
        return new(row.GetGuid(0), row.GetString(1), row.GetInt64(2));
    }

    public async Task<IReadOnlyList<Customer>> ReadCustomers(Actor actor, CancellationToken ct)
    {
        await using var db = await source.OpenConnectionAsync(ct);
        await using var cmd = Command(db, null, """
            SELECT c.id,c.systemhaus_id,c.name,c.revision FROM customer c
            WHERE c.systemhaus_id=@house AND EXISTS (
              SELECT 1 FROM app_user u
              JOIN user_group_member m ON m.systemhaus_id=u.systemhaus_id AND m.user_id=u.id
              JOIN permission_grant g ON g.systemhaus_id=m.systemhaus_id AND g.user_group_id=m.group_id
              WHERE u.id=@uid AND u.systemhaus_id=c.systemhaus_id AND u.active AND g.capability='inventory.read'
                AND ((g.customer_id IS NULL AND g.customer_group_id IS NULL) OR g.customer_id=c.id
                  OR EXISTS(SELECT 1 FROM customer_group_member cm WHERE cm.systemhaus_id=c.systemhaus_id
                    AND cm.customer_id=c.id AND cm.group_id=g.customer_group_id)))
            ORDER BY c.name,c.id
            """, ("house", actor.HouseId), ("uid", actor.Id));
        var result = new List<Customer>();
        await using var row = await cmd.ExecuteReaderAsync(ct);
        while (await row.ReadAsync(ct)) result.Add(new(row.GetGuid(0), row.GetGuid(1), row.GetString(2), row.GetInt64(3)));
        return result;
    }

    public Task<string> RenameHouse(Actor actor, string? name, long expected, Guid requestId, CancellationToken ct)
        => Mutate(actor, null, "systemhaus.rename", Capabilities.HouseManage, name, expected, requestId, ct);
    public Task<string> CreateCustomer(Actor actor, string? name, long expected, Guid requestId, CancellationToken ct)
        => Mutate(actor, null, "customer.create", Capabilities.CustomerCreate, name, expected, requestId, ct);
    public Task<string> RenameCustomer(Actor actor, Guid customerId, string? name, long expected, Guid requestId, CancellationToken ct)
        => Mutate(actor, customerId, "customer.rename", Capabilities.CustomerManage, name, expected, requestId, ct);

    private async Task<string> Mutate(Actor actor, Guid? customerId, string action, string capability,
        string? input, long expected, Guid requestId, CancellationToken ct)
    {
        string name = Names.Validate(input);
        if (requestId == Guid.Empty) throw new DomainError(422, "request_id_invalid");
        string requestHash = Secrets.Digest(JsonSerializer.Serialize(new { action, customerId, name, expected }, Json));
        await using var db = await source.OpenConnectionAsync(ct);
        await using var tx = await db.BeginTransactionAsync(ct);
        House house;
        await LockOperation(db, tx, actor, requestId, ct);
        // Foundation changes to hierarchy serialize on their Systemhaus row. Inventory will use customer revisions.
        await using (var cmd = Command(db, tx,
            "SELECT id,name,revision FROM systemhaus WHERE id=@id FOR UPDATE", ("id", actor.HouseId)))
        await using (var row = await cmd.ExecuteReaderAsync(ct))
        {
            if (!await row.ReadAsync(ct)) throw new DomainError(404, "not_found");
            house = new(row.GetGuid(0), row.GetString(1), row.GetInt64(2));
        }
        await RequireCurrentSession(db, tx, actor, ct);
        if (customerId.HasValue && !await Can(db, tx, actor, customerId, Capabilities.InventoryRead, ct))
            throw new DomainError(404, "not_found");
        if (!await Can(db, tx, actor, customerId, capability, ct)) throw new DomainError(403, "forbidden");
        await OperationCancellation.EnsureNotCanceled(db, tx, actor, requestId, requestHash, ct);
        await using (var cmd = Command(db, tx, """
            SELECT request_hash,result_json::text FROM operation
            WHERE systemhaus_id=@house AND actor_id=@actor AND request_id=@request
            """, ("house", actor.HouseId), ("actor", actor.Id), ("request", requestId)))
        await using (var row = await cmd.ExecuteReaderAsync(ct))
            if (await row.ReadAsync(ct))
            {
                if (row.GetString(0) != requestHash) throw new DomainError(409, "request_id_reused");
                // Read-only replay: disposing the transaction releases the lock without changing state.
                return row.GetString(1);
            }
        object? before = house;
        object resource;
        Guid resourceId;
        Guid? contextCustomerId = null;
        long? contextCustomerBefore = null, contextCustomerAfter = null;
        if (action == "customer.rename")
        {
            Customer customer;
            await using (var cmd = Command(db, tx,
                "SELECT id,systemhaus_id,name,revision FROM customer WHERE id=@id AND systemhaus_id=@house FOR UPDATE",
                ("id", customerId!.Value), ("house", actor.HouseId)))
            await using (var row = await cmd.ExecuteReaderAsync(ct))
            {
                if (!await row.ReadAsync(ct)) throw new DomainError(404, "not_found");
                customer = new(row.GetGuid(0), row.GetGuid(1), row.GetString(2), row.GetInt64(3));
            }
            // Inventory may hold the customer row after the earlier house check.
            // Recheck time-dependent session and grants after that final wait.
            await RequireCurrentSession(db, tx, actor, ct);
            if (!await Can(db, tx, actor, customerId, Capabilities.InventoryRead, ct)) throw new DomainError(404, "not_found");
            if (!await Can(db, tx, actor, customerId, capability, ct)) throw new DomainError(403, "forbidden");
            Revisions.Require(expected, customer.Revision);
            before = customer;
            resourceId = customer.Id;
            resource = customer with { Name = name, Revision = checked(customer.Revision + 1) };
            contextCustomerId = customer.Id;
            contextCustomerBefore = customer.Revision;
            contextCustomerAfter = ((Customer)resource).Revision;
            await using var cmdUpdate = Command(db, tx, "UPDATE customer SET name=@name,revision=revision+1 WHERE id=@id AND systemhaus_id=@house",
                ("name", name), ("id", resourceId), ("house", actor.HouseId));
            await cmdUpdate.ExecuteNonQueryAsync(ct);
        }
        else
        {
            Revisions.Require(expected, house.Revision);
            if (action == "systemhaus.rename")
            {
                resourceId = house.Id;
                resource = house with { Name = name, Revision = checked(house.Revision + 1) };
                await using var cmd = Command(db, tx, "UPDATE systemhaus SET name=@name WHERE id=@id", ("name", name), ("id", house.Id));
                await cmd.ExecuteNonQueryAsync(ct);
            }
            else
            {
                before = null;
                resourceId = Guid.NewGuid();
                resource = new Customer(resourceId, house.Id, name, 1);
                contextCustomerId = resourceId;
                contextCustomerAfter = 1;
                await using var cmd = Command(db, tx, "INSERT INTO customer(id,systemhaus_id,name) VALUES(@id,@house,@name)",
                    ("id", resourceId), ("house", house.Id), ("name", name));
                await cmd.ExecuteNonQueryAsync(ct);
            }
        }
        long nextRevision = checked(house.Revision + 1);
        await using (var cmd = Command(db, tx, "UPDATE systemhaus SET revision=@revision WHERE id=@id",
            ("revision", nextRevision), ("id", house.Id))) await cmd.ExecuteNonQueryAsync(ct);
        string after = JsonSerializer.Serialize(resource, Json);
        string result = JsonSerializer.Serialize(new { resource, systemhausRevision = nextRevision, requestId }, Json);
        Guid eventId = Guid.NewGuid();
        await using (var cmd = Command(db, tx, """
            INSERT INTO audit_event(id,systemhaus_id,actor_id,request_id,action,resource_id,before_json,after_json)
            VALUES(@id,@house,@actor,@request,@action,@resource,CAST(@before AS jsonb),CAST(@after AS jsonb))
            """, ("id", eventId), ("house", house.Id), ("actor", actor.Id), ("request", requestId),
            ("action", action), ("resource", resourceId), ("before", JsonSerializer.Serialize(before, Json)), ("after", after)))
            await cmd.ExecuteNonQueryAsync(ct);
        await using (var cmd = Command(db, tx, """
            INSERT INTO operation(systemhaus_id,actor_id,request_id,request_hash,result_json)
            VALUES(@house,@actor,@request,@hash,CAST(@result AS jsonb))
            """, ("house", house.Id), ("actor", actor.Id), ("request", requestId), ("hash", requestHash), ("result", result)))
            await cmd.ExecuteNonQueryAsync(ct);
        await CaptureAuditContext(db, tx, actor, eventId, requestId, resourceId, action, house.Revision, nextRevision,
            [new(action == "systemhaus.rename" ? "systemhaus" : "customer", resourceId, "target")], ct,
            contextCustomerId, contextCustomerBefore, contextCustomerAfter);
        await tx.CommitAsync(ct);
        return result;
    }

    public async Task Bootstrap(string houseName, string username, string password, CancellationToken ct)
    {
        houseName = Names.Validate(houseName);
        username = UserNames.Normalize(username);
        if (password.Length < 16 || password.Length > 1024) throw new DomainError(422, "password_length");
        await using var db = await source.OpenConnectionAsync(ct);
        await using var tx = await db.BeginTransactionAsync(ct);
        await using (var guard = Command(db, tx, "SELECT pg_advisory_xact_lock(81726201)")) await guard.ExecuteNonQueryAsync(ct);
        await using (var exists = Command(db, tx, "SELECT to_regclass('public.systemhaus') IS NOT NULL"))
            if ((bool)(await exists.ExecuteScalarAsync(ct))!) throw new DomainError(409, "already_initialized");
        await SchemaMigrations.Apply(db, tx, ct);
        Guid house = Guid.NewGuid(), user = Guid.NewGuid(), group = Guid.NewGuid();
        await using (var cmd = Command(db, tx, "INSERT INTO systemhaus(id,name) VALUES(@id,@name)", ("id", house), ("name", houseName))) await cmd.ExecuteNonQueryAsync(ct);
        await using (var cmd = Command(db, tx, "INSERT INTO app_user(id,systemhaus_id,username,password_hash) VALUES(@id,@house,@name,@hash)",
            ("id", user), ("house", house), ("name", username), ("hash", Secrets.PasswordHash(username, password)))) await cmd.ExecuteNonQueryAsync(ct);
        await using (var cmd = Command(db, tx, "INSERT INTO user_group(id,systemhaus_id,name) VALUES(@id,@house,'Systemhaus Administrators')",
            ("id", group), ("house", house))) await cmd.ExecuteNonQueryAsync(ct);
        await using (var cmd = Command(db, tx, "INSERT INTO user_group_member VALUES(@house,@user,@group)",
            ("house", house), ("user", user), ("group", group))) await cmd.ExecuteNonQueryAsync(ct);
        foreach (var capability in Capabilities.FoundationAdmin)
        {
            await using var cmd = Command(db, tx, "INSERT INTO permission_grant(id,systemhaus_id,user_group_id,capability) VALUES(@id,@house,@group,@cap)",
                ("id", Guid.NewGuid()), ("house", house), ("group", group), ("cap", capability));
            await cmd.ExecuteNonQueryAsync(ct);
        }
        await tx.CommitAsync(ct);
    }

    public async Task Migrate(CancellationToken ct)
    {
        await using var db = await source.OpenConnectionAsync(ct);
        await using var tx = await db.BeginTransactionAsync(ct);
        await using (var guard = Command(db, tx, "SELECT pg_advisory_xact_lock(81726201)")) await guard.ExecuteNonQueryAsync(ct);
        await using (var exists = Command(db, tx, "SELECT to_regclass('public.systemhaus') IS NOT NULL"))
            if (await exists.ExecuteScalarAsync(ct) is not true) throw new DomainError(409, "not_initialized");
        await SchemaMigrations.Apply(db, tx, ct);
        await tx.CommitAsync(ct);
    }
}
