using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Npgsql;
using NpgsqlTypes;

// Explicit local data loader, NOT a web restore endpoint. The only accepted
// payload is the reviewed ORIGINAL synthetic RC9 plan, pinned by full digest.
internal static class Program
{
    private const string PlanSha = "cbfe4b43a0148299f6f4c24a21dfcb5e21a8efd5ca2d08d552119ac0cd292bd7";
    private const string SourceSha = "cb52d27990a82d3f2dc12bf731bcbe6c1586575643f301e4b040b250f31374d0";
    // Closed profiles: preserve the historical15 loader contract and explicitly
    // admit the reviewed45 source demo. Never accept an arbitrary later schema.
    private static readonly IReadOnlyDictionary<string, string> SchemaProfiles = new Dictionary<string, string>
    {
        [string.Join(',', Enumerable.Range(1, 15))] = "a09be30a6b72512a6fc0cc7a1d9419aec6a08f5c6b9ff8a603161c6285d022be",
        [string.Join(',', Enumerable.Range(1, 45))] = "50649cc57003f7c7f797e980072a4c52e425875a114d59bee63b7eeddf85b4d5"
    };
    private static int CommitPhase;
    private sealed record Table(string Name, string Columns);
    private static readonly Table[] Tables = [
        new("customer", "id,name"),
        new("inventory_site", "id,name,customer_id,properties"),
        new("inventory_building", "id,name,customer_id,properties,site_id"),
        new("inventory_room", "id,name,customer_id,properties,building_id"),
        new("inventory_rack", "id,customer_id,room_id,name,location,size_u,properties"),
        new("inventory_device", "id,customer_id,rack_id,room_id,kind,name,size_u,sort_order,poe_budget,properties"),
        new("inventory_port_group", "id,customer_id,device_id,type,name,prefix,sort_order"),
        new("inventory_port", "id,customer_id,device_id,group_id,type,gn,sort_order,label,status,poe,watts,color,face,power_role,properties"),
        new("inventory_connection", "id,customer_id,note,color,patch,properties"),
        new("inventory_connection_endpoint", "customer_id,connection_id,ordinal,port_id")
    ];
    // Never write any of these; lock them while checking preservation. No
    // password hashes, seeds or ciphertext leave PostgreSQL in this check.
    private static readonly string[] SecurityTables = ["app_user", "user_group", "user_group_member", "customer_group",
        "customer_group_member", "permission_grant", "app_session", "app_mfa_user", "app_mfa_factor",
        "app_mfa_challenge", "app_mfa_recovery_code", "app_mfa_policy"];

    private sealed class Rejected(string code) : Exception(code);
    private sealed record Input(string Mode, string ConnectionString, string ActorName, Guid ExpectedHouseId, long ExpectedRevision, Guid RequestId);

    public static async Task<int> Main(string[] args)
    {
        try
        {
            Require(args.Length == 2 && args[0] == "--plan", "arguments_invalid");
            using var planStream = new FileStream(args[1], FileMode.Open, FileAccess.Read, FileShare.Read);
            Require(planStream.Length is > 0 and <= 8_388_608, "plan_invalid");
            using var bytes = new MemoryStream();
            await planStream.CopyToAsync(bytes);
            var planBytes = bytes.ToArray();
            Require(Convert.ToHexStringLower(SHA256.HashData(planBytes)) == PlanSha, "plan_hash_mismatch");
            using var document = JsonDocument.Parse(planBytes);
            var plan = document.RootElement;
            Require(plan.GetProperty("format").GetString() == "RackClickOriginalRc9Demo-v1" &&
                plan.GetProperty("sourceSha256").GetString() == SourceSha, "plan_invalid");
            var text = new StringBuilder();
            char[] buffer = new char[4096];
            int read;
            while ((read = await Console.In.ReadAsync(buffer)) != 0)
            {
                Require(text.Length + read <= 16_384, "input_too_large");
                text.Append(buffer, 0, read);
            }
            var input = JsonSerializer.Deserialize<Input>(text.ToString(), new JsonSerializerOptions { PropertyNameCaseInsensitive = true });
            Require(input is not null && input.Mode is "check" or "apply" && !string.IsNullOrWhiteSpace(input.ActorName) &&
                input.RequestId != Guid.Empty, "input_invalid");
            var answer = await Run(input!, plan);
            Console.WriteLine(answer);
            return 0;
        }
        catch (Exception e) when (e is Rejected or JsonException or IOException or ArgumentException or NpgsqlException or InvalidOperationException)
        {
            // No raw messages/paths/SQL/credentials in the operator report.
            var code = CommitPhase == 1 ? "commit_status_unknown" : CommitPhase == 2 ? "committed_report_failed"
                : e is Rejected r ? r.Message : e is PostgresException ? "database_rejected" : "import_failed";
            bool? committed = CommitPhase == 1 ? null : CommitPhase == 2;
            Console.WriteLine(JsonSerializer.Serialize(new { success = false, committed, code }));
            return 1;
        }
    }

    private static void Require(bool condition, string code) { if (!condition) throw new Rejected(code); }
    private static NpgsqlCommand Command(NpgsqlConnection db, NpgsqlTransaction tx, string sql, params (string, object)[] args)
    {
        var command = new NpgsqlCommand(sql, db, tx) { CommandTimeout = 60 };
        foreach (var (name, value) in args) command.Parameters.AddWithValue(name, value);
        return command;
    }

    private static async Task<string> Run(Input input, JsonElement plan)
    {
        var config = new NpgsqlConnectionStringBuilder(input.ConnectionString);
        Require(config.Host == "127.0.0.1" && config.Port is >= 1 and <= 65535, "loopback_required");
        config.Pooling = false;
        config.IncludeErrorDetail = false;
        await using var db = new NpgsqlConnection(config.ConnectionString);
        await db.OpenAsync();
        await using var tx = await db.BeginTransactionAsync();
        await using (var limits = Command(db, tx, "SET LOCAL lock_timeout='5s'; SET LOCAL statement_timeout='60s'"))
            await limits.ExecuteNonQueryAsync();
        await using (var restricted = Command(db, tx, """
            SELECT NOT (r.rolsuper OR r.rolcreatedb OR r.rolcreaterole OR r.rolreplication OR r.rolbypassrls)
                AND NOT pg_has_role(r.oid,d.datdba,'MEMBER')
                AND NOT has_database_privilege(current_user,current_database(),'CREATE')
                AND NOT has_schema_privilege(current_user,'public','CREATE')
            FROM pg_roles r CROSS JOIN pg_database d WHERE r.rolname=current_user AND d.datname=current_database()
            """))
            Require((bool)(await restricted.ExecuteScalarAsync())!, "restricted_runtime_required");
        await using (var schema = Command(db, tx, """
            SELECT string_agg(version::text,',' ORDER BY version),
                string_agg(version::text||':'||lower(digest),E'\n' ORDER BY version)||E'\n' FROM schema_migration
            """))
        await using (var history = await schema.ExecuteReaderAsync())
        {
            Require(await history.ReadAsync() && !history.IsDBNull(0), "schema_profile_unsupported");
            Require(SchemaProfiles.TryGetValue(history.GetString(0), out string? expectedSchemaSha), "schema_profile_unsupported");
            Require(!history.IsDBNull(1) && Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes(history.GetString(1)))) == expectedSchemaSha,
                "migration_digest_mismatch");
        }
        Guid house;
        long revision;
        await using (var row = Command(db, tx, "SELECT id,revision FROM systemhaus FOR UPDATE"))
        await using (var reader = await row.ExecuteReaderAsync())
        {
            Require(await reader.ReadAsync(), "house_missing");
            house = reader.GetGuid(0); revision = reader.GetInt64(1);
            Require(!await reader.ReadAsync(), "house_invalid");
        }
        Require(input.Mode == "check" && input.ExpectedHouseId == Guid.Empty || input.ExpectedHouseId == house, "house_mismatch");
        // Serialize with security changes, without reading their material into
        // the client. Identifiers below come ONLY from the internal list.
        await using (var locks = Command(db, tx, "LOCK TABLE " + string.Join(',', SecurityTables) + " IN SHARE MODE; LOCK TABLE " +
            string.Join(',', Tables.Select(t => t.Name)) + " IN EXCLUSIVE MODE"))
            await locks.ExecuteNonQueryAsync();
        Guid actor;
        await using (var user = Command(db, tx, "SELECT id FROM app_user WHERE systemhaus_id=@house AND username=@name AND active",
            ("house", house), ("name", input.ActorName)))
        {
            var id = await user.ExecuteScalarAsync();
            Require(id is Guid, "actor_invalid"); actor = (Guid)id!;
        }
        await using (var auth = Command(db, tx, """
            SELECT count(DISTINCT g.capability)=4 FROM user_group_member m
            JOIN permission_grant g ON g.systemhaus_id=m.systemhaus_id AND g.user_group_id=m.group_id
            WHERE m.systemhaus_id=@house AND m.user_id=@actor AND g.customer_id IS NULL AND g.customer_group_id IS NULL
              AND g.capability IN ('systemhaus.manage','security.manage','customer.create','inventory.edit')
            """, ("house", house), ("actor", actor)))
            Require((bool)(await auth.ExecuteScalarAsync())!, "global_admin_required");
        var requestHash = Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes(
            "original-rc9-demo-v1|" + PlanSha + "|" + house.ToString("D") + "|" + input.ExpectedRevision)));
        await using (var previous = Command(db, tx, "SELECT request_hash,result_json::text FROM operation WHERE systemhaus_id=@house AND actor_id=@actor AND request_id=@request",
            ("house", house), ("actor", actor), ("request", input.RequestId)))
        await using (var reader = await previous.ExecuteReaderAsync())
            if (await reader.ReadAsync())
            {
                Require(reader.GetString(0) == requestHash, "request_id_reused");
                string saved = reader.GetString(1);
                CommitPhase = 2; // This receipt already records a committed operation.
                return saved;
            }
        foreach (var table in Tables)
        {
            await using var count = Command(db, tx, "SELECT count(*) FROM " + table.Name);
            Require((long)(await count.ExecuteScalarAsync())! == 0, "inventory_not_empty");
        }
        if (input.Mode == "check")
            return JsonSerializer.Serialize(new { success = true, committed = false, code = "demo_import_ready", systemhausId = house,
                expectedRevision = revision, sourceSha256 = SourceSha, planSha256 = PlanSha, counts = plan.GetProperty("counts") });
        Require(input.ExpectedRevision == revision, "revision_conflict");
        var before = await SecurityFingerprint(db, tx);
        foreach (var table in Tables)
        {
            var columns = table.Columns.Split(',');
            string sql = "INSERT INTO " + table.Name + "(" + table.Columns + ",systemhaus_id) VALUES (" +
                string.Join(',', columns.Select((_, i) => "@p" + i)) + ",@house)";
            await using var batch = new NpgsqlBatch(db, tx) { Timeout = 60 };
            foreach (var row in plan.GetProperty("rows").GetProperty(table.Name).EnumerateArray())
            {
                var command = new NpgsqlBatchCommand(sql);
                for (int i = 0; i < columns.Length; i++) command.Parameters.Add(Parameter("p" + i, columns[i], row.GetProperty(columns[i])));
                command.Parameters.AddWithValue("house", house);
                batch.BatchCommands.Add(command);
            }
            await batch.ExecuteNonQueryAsync();
            await using var count = Command(db, tx, "SELECT count(*) FROM " + table.Name);
            Require((long)(await count.ExecuteScalarAsync())! == plan.GetProperty("rows").GetProperty(table.Name).GetArrayLength(), "row_count_mismatch");
        }
        await using (var constraints = Command(db, tx, "SET CONSTRAINTS ALL IMMEDIATE")) await constraints.ExecuteNonQueryAsync();
        Require(before == await SecurityFingerprint(db, tx), "security_preservation_failed");
        await using (var update = Command(db, tx, "UPDATE systemhaus SET revision=revision+1 WHERE id=@house", ("house", house)))
            Require(await update.ExecuteNonQueryAsync() == 1, "house_invalid");
        string result = JsonSerializer.Serialize(new { success = true, committed = true, code = "demo_import_committed", sourceSha256 = SourceSha,
            planSha256 = PlanSha, systemhausId = house, revision = checked(revision + 1), securityPreserved = true, counts = plan.GetProperty("counts") });
        await using (var audit = Command(db, tx, """
            INSERT INTO audit_event(id,systemhaus_id,actor_id,request_id,action,resource_id,before_json,after_json)
            VALUES (@id,@house,@actor,@request,'inventory.demo.import',@house,'{"inventoryEmpty":true}'::jsonb,@after::jsonb);
            INSERT INTO operation(systemhaus_id,actor_id,request_id,request_hash,result_json)
            VALUES (@house,@actor,@request,@hash,@after::jsonb)
            """, ("id", Guid.NewGuid()), ("house", house), ("actor", actor), ("request", input.RequestId), ("hash", requestHash), ("after", result)))
            await audit.ExecuteNonQueryAsync();
        CommitPhase = 1;
        await tx.CommitAsync();
        CommitPhase = 2;
        return result;
    }

    private static NpgsqlParameter Parameter(string name, string column, JsonElement value)
    {
        NpgsqlDbType type = column == "id" || column.EndsWith("_id", StringComparison.Ordinal) ? NpgsqlDbType.Uuid
            : column == "properties" ? NpgsqlDbType.Jsonb
            : column is "size_u" or "sort_order" or "gn" or "ordinal" ? NpgsqlDbType.Integer
            : column is "poe_budget" or "watts" ? NpgsqlDbType.Numeric
            : column == "poe" ? NpgsqlDbType.Boolean : NpgsqlDbType.Text;
        object typed = value.ValueKind == JsonValueKind.Null ? DBNull.Value : type switch
        {
            NpgsqlDbType.Uuid => value.GetGuid(),
            NpgsqlDbType.Integer => value.GetInt32(),
            NpgsqlDbType.Numeric => value.GetDecimal(),
            NpgsqlDbType.Boolean => value.GetBoolean(),
            NpgsqlDbType.Jsonb => value.GetRawText(),
            _ => value.GetString()!
        };
        return new NpgsqlParameter(name, type) { Value = typed };
    }

    private static async Task<string> SecurityFingerprint(NpgsqlConnection db, NpgsqlTransaction tx)
    {
        var summary = new StringBuilder();
        foreach (var table in SecurityTables)
        {
            await using var fingerprint = Command(db, tx, "SELECT md5(COALESCE(string_agg(to_jsonb(t)::text,E'\\n' ORDER BY to_jsonb(t)::text),'')) FROM " + table + " t");
            summary.Append((string)(await fingerprint.ExecuteScalarAsync())!);
        }
        return summary.ToString();
    }
}
