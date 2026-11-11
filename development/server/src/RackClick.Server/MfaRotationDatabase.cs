using System.Buffers.Binary;
using System.Data;
using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;
using Npgsql;

namespace RackClick.Server;

internal sealed record MfaRotationBinding(Guid OperationId, Guid InstallationId, Guid SystemhausId, string OperatorSid,
    int OldVersion, int NewVersion, string OriginalRingHash, string AdditiveRingHash, string FinalRingHash,
    string NewKeyHash, string CatalogHash, string EnvelopeHash);

internal sealed record MfaRotationWitness(MfaRotationBinding Binding, long FactorCount, long RevokedSessions, long ConsumedChallenges);

// Transaction-only adapter. The coordinator owns local authority, DB admission, fence,
// material verification, stable-plan comparison and COMMIT/uncertain-COMMIT reconciliation.
internal static class MfaRotationDatabase
{
    private const int PageSize = 128;
    private const int MaxCipherBytes = 16 * 1024;
    private const int MaxSnapshotRowBytes = 64 * 1024;
    private const int MaxVersion = 1_000_000;
    // Closed internal identifiers only. Keep this order common to all rotation paths.
    private static readonly string[] Tables = ["public.app_mfa_factor", "public.app_session", "public.app_mfa_challenge",
        "public.app_mfa_recovery_code", "public.app_user", "public.app_mfa_user", "public.systemhaus", "public.app_mfa_rotation_witness"];
    private static readonly Regex SidPattern = new(@"\AS-1-[0-9]+(-[0-9]+){1,15}\z", RegexOptions.CultureInvariant | RegexOptions.NonBacktracking);

    internal static void ValidateBinding(MfaRotationBinding binding)
    {
        if (binding is null || binding.OperationId == Guid.Empty || binding.InstallationId == Guid.Empty || binding.SystemhausId == Guid.Empty
            || binding.OperatorSid is null || binding.OperatorSid.Length is < 7 or > 184 || !SidPattern.IsMatch(binding.OperatorSid)
            || binding.OldVersion is < 1 or > MaxVersion || binding.NewVersion is < 1 or > MaxVersion || binding.NewVersion <= binding.OldVersion
            || !HashValid(binding.OriginalRingHash) || !HashValid(binding.AdditiveRingHash) || !HashValid(binding.FinalRingHash)
            || !HashValid(binding.NewKeyHash) || !HashValid(binding.CatalogHash) || !HashValid(binding.EnvelopeHash)
            || binding.OriginalRingHash == binding.AdditiveRingHash || binding.OriginalRingHash == binding.FinalRingHash
            || binding.AdditiveRingHash == binding.FinalRingHash)
            throw Fail("mfa_rotation_binding_invalid");
    }

    internal static async Task LockAsync(NpgsqlConnection connection, NpgsqlTransaction transaction, CancellationToken ct)
    {
        RequireTransaction(connection, transaction, true);
        await using (var settings = new NpgsqlCommand("SET LOCAL lock_timeout='10s'; SET LOCAL synchronous_commit=on", connection, transaction))
            await settings.ExecuteNonQueryAsync(ct);
        foreach (var table in Tables)
        {
            await using var command = new NpgsqlCommand("LOCK TABLE " + table + " IN ACCESS EXCLUSIVE MODE", connection, transaction);
            await command.ExecuteNonQueryAsync(ct);
        }
        await RequireLocks(connection, transaction, ct);
    }

    internal static async Task<MfaRotationWitness?> ReadWitnessAsync(NpgsqlConnection connection, NpgsqlTransaction transaction,
        Guid operation, CancellationToken ct)
    {
        RequireTransaction(connection, transaction, false);
        if (operation == Guid.Empty) throw Fail("mfa_rotation_binding_invalid");
        await using var command = new NpgsqlCommand("""
            SELECT installation_id,systemhaus_id,operator_sid,old_version,new_version,
                original_ring_sha256,additive_ring_sha256,final_ring_sha256,new_key_sha256,catalog_sha256,envelope_sha256,
                factor_count,revoked_sessions,consumed_challenges,mode,authority,database_name,
                current_database(),isfinite(committed_at)
            FROM public.app_mfa_rotation_witness WHERE operation_id=@operation
            """, connection, transaction);
        command.Parameters.AddWithValue("operation", operation);
        await using var rows = await command.ExecuteReaderAsync(ct);
        if (!await rows.ReadAsync(ct)) return null;
        var binding = new MfaRotationBinding(operation, rows.GetGuid(0), rows.GetGuid(1), rows.GetString(2), rows.GetInt32(3), rows.GetInt32(4),
            rows.GetString(5), rows.GetString(6), rows.GetString(7), rows.GetString(8), rows.GetString(9), rows.GetString(10));
        ValidateBinding(binding);
        var result = new MfaRotationWitness(binding, rows.GetInt64(11), rows.GetInt64(12), rows.GetInt64(13));
        if (result.FactorCount < 0 || result.RevokedSessions < 0 || result.ConsumedChallenges < 0
            || rows.GetString(14) != "rotate" || rows.GetString(15) != "windows-local" || !rows.GetBoolean(18)
            || rows.GetString(16) != rows.GetString(17) || rows.GetString(16) != DatabaseName(binding.InstallationId))
            throw Fail("mfa_rotation_witness_invalid");
        if (await rows.ReadAsync(ct)) throw Fail("mfa_rotation_witness_invalid");
        return result;
    }

    // Hashes every complete factor row and complete affected session/challenge rows,
    // with type/length framing. No aggregate, plaintext or ciphertext is logged/stored.
    // The caller must retain and compare this hash across planned/rewrap/absent-witness recovery.
    internal static async Task<string> ReadSnapshotHashAsync(NpgsqlConnection connection, NpgsqlTransaction transaction, CancellationToken ct)
    {
        await RequireLocks(connection, transaction, ct);
        using var hash = IncrementalHash.CreateHash(HashAlgorithmName.SHA256);
        var queries = new[]
        {
            "SELECT CASE WHEN octet_length(to_jsonb(f)::text)<=@limit THEN to_jsonb(f)::text ELSE NULL END FROM public.app_mfa_factor f ORDER BY f.systemhaus_id,f.user_id",
            "SELECT CASE WHEN octet_length(to_jsonb(s)::text)<=@limit THEN to_jsonb(s)::text ELSE NULL END FROM public.app_session s WHERE EXISTS(SELECT 1 FROM public.app_mfa_factor f WHERE f.user_id=s.user_id) ORDER BY s.token_hash",
            "SELECT CASE WHEN octet_length(to_jsonb(c)::text)<=@limit THEN to_jsonb(c)::text ELSE NULL END FROM public.app_mfa_challenge c WHERE EXISTS(SELECT 1 FROM public.app_mfa_factor f WHERE f.systemhaus_id=c.systemhaus_id AND f.user_id=c.user_id) ORDER BY c.token_hash"
        };
        // Stable JSON timestamps independently of session timezone/date formatting.
        await using (var format = new NpgsqlCommand("SET LOCAL TimeZone='UTC'; SET LOCAL DateStyle='ISO, YMD'; SET LOCAL bytea_output='hex'", connection, transaction))
            await format.ExecuteNonQueryAsync(ct);
        for (var index = 0; index < queries.Length; index++)
        {
            AppendHash(hash, [(byte)index]);
            await using var command = new NpgsqlCommand(queries[index], connection, transaction);
            command.Parameters.AddWithValue("limit", MaxSnapshotRowBytes);
            await using var rows = await command.ExecuteReaderAsync(ct);
            while (await rows.ReadAsync(ct))
            {
                if (rows.IsDBNull(0)) throw Fail("mfa_rotation_snapshot_row_too_large");
                var bytes = Encoding.UTF8.GetBytes(rows.GetString(0));
                try { AppendHash(hash, bytes); } finally { CryptographicOperations.ZeroMemory(bytes); }
            }
        }
        return Convert.ToHexStringLower(hash.GetHashAndReset());
    }

    internal static async Task<MfaRotationWitness> RewrapAsync(NpgsqlConnection connection, NpgsqlTransaction transaction,
        MfaRotationBinding binding, IMfaKeyProvider provider, byte[] newKey, CancellationToken ct)
    {
        // Even .NET authentication/provider/cancellation errors must prevent a caller from
        // accidentally committing an already processed page. This method NEVER commits.
        var retainedKeys = new Dictionary<int, byte[]>();
        byte[]? keyCopy = null;
        try
        {
            ValidateBinding(binding);
            await RequireLocks(connection, transaction, ct);
            await RequireIdentity(connection, transaction, binding, ct);
            if (await ReadWitnessAsync(connection, transaction, binding.OperationId, ct) is not null)
                throw Fail("mfa_rotation_witness_exists");
            await using (var versions = new NpgsqlCommand("SELECT COALESCE(max(new_version),0) FROM public.app_mfa_rotation_witness", connection, transaction))
                if (binding.NewVersion <= (int)(await versions.ExecuteScalarAsync(ct))!) throw Fail("mfa_rotation_version_reused");
            ArgumentNullException.ThrowIfNull(provider);
            if (newKey is null || newKey.Length != MfaSecretCipher.KeyBytes) throw Fail("mfa_rotation_key_invalid");
            keyCopy = newKey.ToArray();
            // Confirm the already published additive provider exposes exactly the new key.
            var published = provider.GetKey(binding.NewVersion);
            try
            {
                if (published.Length != MfaSecretCipher.KeyBytes || !CryptographicOperations.FixedTimeEquals(published, keyCopy))
                    throw Fail("mfa_rotation_key_invalid");
            }
            finally { CryptographicOperations.ZeroMemory(published); }

            long count = 0;
            Guid? afterHouse = null; Guid? afterUser = null;
            while (true)
            {
                var page = await ReadPage(connection, transaction, afterHouse, afterUser, ct);
                try
                {
                    if (page.Count == 0) break;
                    foreach (var factor in page)
                    {
                        ct.ThrowIfCancellationRequested();
                        if (factor.House != binding.SystemhausId || factor.User == Guid.Empty || factor.Version is < 1 or > MaxVersion
                            || factor.Version >= binding.NewVersion || factor.State is not ("pending" or "active" or "disabled"))
                            throw Fail("mfa_rotation_factor_invalid");
                        if (!retainedKeys.TryGetValue(factor.Version, out var oldKey))
                        {
                            if (retainedKeys.Count >= MfaKeyRing.MaxVersions) throw Fail("mfa_rotation_factor_invalid");
                            oldKey = provider.GetKey(factor.Version);
                            retainedKeys.Add(factor.Version, oldKey);
                            if (oldKey.Length != MfaSecretCipher.KeyBytes) throw Fail("mfa_rotation_key_invalid");
                        }
                        byte[]? plain = null; byte[]? cipher = null; byte[]? roundtrip = null;
                        try
                        {
                            plain = MfaSecretCipher.Open(oldKey, factor.Version, factor.Cipher, factor.House, factor.User);
                            if (plain.Length == 0) throw Fail("mfa_rotation_factor_invalid");
                            cipher = MfaSecretCipher.Seal(keyCopy, binding.NewVersion, plain, factor.House, factor.User);
                            roundtrip = MfaSecretCipher.Open(keyCopy, binding.NewVersion, cipher, factor.House, factor.User);
                            if (!CryptographicOperations.FixedTimeEquals(plain, roundtrip)) throw Fail("mfa_rotation_roundtrip_failed");
                            await using var update = new NpgsqlCommand("""
                                UPDATE public.app_mfa_factor SET secret_ciphertext=@cipher,key_version=@new
                                WHERE systemhaus_id=@house AND user_id=@user AND key_version=@old AND secret_ciphertext=@previous
                                """, connection, transaction);
                            update.Parameters.AddWithValue("cipher", cipher); update.Parameters.AddWithValue("new", binding.NewVersion);
                            update.Parameters.AddWithValue("house", factor.House); update.Parameters.AddWithValue("user", factor.User);
                            update.Parameters.AddWithValue("old", factor.Version); update.Parameters.AddWithValue("previous", factor.Cipher);
                            if (await update.ExecuteNonQueryAsync(ct) != 1) throw Fail("mfa_rotation_factor_changed");
                            count = checked(count + 1);
                        }
                        finally { Zero(plain); Zero(cipher); Zero(roundtrip); }
                    }
                    afterHouse = page[^1].House; afterUser = page[^1].User;
                }
                finally { foreach (var row in page) Zero(row.Cipher); }
            }
            await using (var recount = new NpgsqlCommand("SELECT count(*)=count(*) FILTER(WHERE key_version=@new) AND count(*)=@count FROM public.app_mfa_factor", connection, transaction))
            {
                recount.Parameters.AddWithValue("new", binding.NewVersion); recount.Parameters.AddWithValue("count", count);
                if (await recount.ExecuteScalarAsync(ct) is not true) throw Fail("mfa_rotation_count_mismatch");
            }
            long sessions;
            await using (var revoke = new NpgsqlCommand("""
                WITH revoked AS (DELETE FROM public.app_session s WHERE EXISTS(
                    SELECT 1 FROM public.app_mfa_factor f WHERE f.user_id=s.user_id) RETURNING 1)
                SELECT count(*) FROM revoked
                """, connection, transaction)) sessions = (long)(await revoke.ExecuteScalarAsync(ct))!;
            long challenges;
            await using (var consume = new NpgsqlCommand("""
                WITH consumed AS (UPDATE public.app_mfa_challenge c SET consumed_at=clock_timestamp()
                    WHERE consumed_at IS NULL AND EXISTS(SELECT 1 FROM public.app_mfa_factor f
                        WHERE f.systemhaus_id=c.systemhaus_id AND f.user_id=c.user_id) RETURNING 1)
                SELECT count(*) FROM consumed
                """, connection, transaction)) challenges = (long)(await consume.ExecuteScalarAsync(ct))!;
            var witness = new MfaRotationWitness(binding, count, sessions, challenges);
            await InsertWitness(connection, transaction, witness, ct);
            if (await ReadWitnessAsync(connection, transaction, binding.OperationId, ct) != witness)
                throw Fail("mfa_rotation_witness_invalid");
            return witness;
        }
        catch
        {
            if (transaction?.Connection is not null)
            {
                try { await transaction.RollbackAsync(CancellationToken.None); }
                catch (Exception) { /* Coordinator reconciles if connection/rollback outcome is uncertain. */ }
            }
            throw;
        }
        finally
        {
            Zero(keyCopy);
            foreach (var key in retainedKeys.Values) Zero(key);
        }
    }

    internal static async Task ValidateCommittedAsync(NpgsqlConnection connection, NpgsqlTransaction transaction,
        MfaRotationWitness witness, IMfaKeyProvider provider, CancellationToken ct)
    {
        ValidateBinding(witness.Binding);
        await RequireLocks(connection, transaction, ct);
        await RequireIdentity(connection, transaction, witness.Binding, ct);
        if (await ReadWitnessAsync(connection, transaction, witness.Binding.OperationId, ct) != witness)
            throw Fail("mfa_rotation_witness_invalid");
        var key = provider.GetKey(witness.Binding.NewVersion);
        try
        {
            if (key.Length != MfaSecretCipher.KeyBytes) throw Fail("mfa_rotation_key_invalid");
            long count = 0; Guid? afterHouse = null; Guid? afterUser = null;
            while (true)
            {
                var page = await ReadPage(connection, transaction, afterHouse, afterUser, ct);
                try
                {
                    if (page.Count == 0) break;
                    foreach (var factor in page)
                    {
                        if (factor.House != witness.Binding.SystemhausId || factor.User == Guid.Empty || factor.Version != witness.Binding.NewVersion
                            || factor.State is not ("pending" or "active" or "disabled")) throw Fail("mfa_rotation_factor_invalid");
                        byte[]? plain = null;
                        try
                        {
                            plain = MfaSecretCipher.Open(key, factor.Version, factor.Cipher, factor.House, factor.User);
                            if (plain.Length == 0) throw Fail("mfa_rotation_factor_invalid");
                            count = checked(count + 1);
                        }
                        finally { Zero(plain); }
                    }
                    afterHouse = page[^1].House; afterUser = page[^1].User;
                }
                finally { foreach (var row in page) Zero(row.Cipher); }
            }
            if (count != witness.FactorCount) throw Fail("mfa_rotation_count_mismatch");
        }
        finally { Zero(key); }
    }

    private sealed record Factor(Guid House, Guid User, int Version, string State, byte[] Cipher);
    private static async Task<List<Factor>> ReadPage(NpgsqlConnection connection, NpgsqlTransaction transaction,
        Guid? afterHouse, Guid? afterUser, CancellationToken ct)
    {
        var result = new List<Factor>(PageSize);
        try
        {
            await using var command = new NpgsqlCommand("""
                SELECT systemhaus_id,user_id,key_version,state,
                    CASE WHEN octet_length(secret_ciphertext) BETWEEN 29 AND @maxbytes THEN secret_ciphertext ELSE NULL END
                FROM public.app_mfa_factor
                WHERE (@first OR (systemhaus_id,user_id)>(@house,@user))
                ORDER BY systemhaus_id,user_id LIMIT 128
                """, connection, transaction);
            command.Parameters.AddWithValue("maxbytes", MaxCipherBytes); command.Parameters.AddWithValue("first", afterHouse is null);
            command.Parameters.AddWithValue("house", afterHouse ?? Guid.Empty); command.Parameters.AddWithValue("user", afterUser ?? Guid.Empty);
            await using var rows = await command.ExecuteReaderAsync(ct);
            while (await rows.ReadAsync(ct))
            {
                if (rows.IsDBNull(4)) throw Fail("mfa_rotation_factor_invalid");
                result.Add(new(rows.GetGuid(0), rows.GetGuid(1), rows.GetInt32(2), rows.GetString(3), rows.GetFieldValue<byte[]>(4)));
            }
            return result;
        }
        catch { foreach (var row in result) Zero(row.Cipher); throw; }
    }

    private static async Task RequireIdentity(NpgsqlConnection connection, NpgsqlTransaction transaction, MfaRotationBinding binding, CancellationToken ct)
    {
        await using (var db = new NpgsqlCommand("SELECT current_database()", connection, transaction))
            if ((string)(await db.ExecuteScalarAsync(ct))! != DatabaseName(binding.InstallationId)) throw Fail("mfa_rotation_database_mismatch");
        await using (var houses = new NpgsqlCommand("SELECT count(*)=1 AND count(*) FILTER(WHERE id=@house)=1 FROM public.systemhaus", connection, transaction))
        {
            houses.Parameters.AddWithValue("house", binding.SystemhausId);
            if (await houses.ExecuteScalarAsync(ct) is not true) throw Fail("mfa_rotation_systemhaus_mismatch");
        }
        await using (var users = new NpgsqlCommand("""
            SELECT NOT EXISTS(SELECT 1 FROM public.app_user WHERE systemhaus_id<>@house OR id='00000000-0000-0000-0000-000000000000'::uuid)
                AND NOT EXISTS(SELECT 1 FROM public.app_mfa_factor f LEFT JOIN public.app_user u
                    ON u.id=f.user_id AND u.systemhaus_id=f.systemhaus_id WHERE u.id IS NULL OR f.systemhaus_id<>@house)
            """, connection, transaction))
        {
            users.Parameters.AddWithValue("house", binding.SystemhausId);
            if (await users.ExecuteScalarAsync(ct) is not true) throw Fail("mfa_rotation_user_mismatch");
        }
    }

    private static async Task RequireLocks(NpgsqlConnection connection, NpgsqlTransaction transaction, CancellationToken ct)
    {
        RequireTransaction(connection, transaction, true);
        await using var command = new NpgsqlCommand("""
            SELECT current_setting('synchronous_commit')='on' AND NOT EXISTS(
                SELECT 1 FROM unnest(@tables::text[]) AS required(name) WHERE NOT EXISTS(
                    SELECT 1 FROM pg_catalog.pg_locks l WHERE l.pid=pg_catalog.pg_backend_pid()
                    AND l.database=(SELECT oid FROM pg_catalog.pg_database WHERE datname=current_database())
                    AND l.granted AND l.mode='AccessExclusiveLock' AND l.relation=pg_catalog.to_regclass(required.name)))
            """, connection, transaction);
        command.Parameters.AddWithValue("tables", Tables);
        if (await command.ExecuteScalarAsync(ct) is not true) throw Fail("mfa_rotation_locks_required");
    }

    private static async Task InsertWitness(NpgsqlConnection connection, NpgsqlTransaction transaction, MfaRotationWitness witness, CancellationToken ct)
    {
        var b = witness.Binding;
        await using var command = new NpgsqlCommand("""
            INSERT INTO public.app_mfa_rotation_witness(operation_id,mode,authority,installation_id,database_name,
                systemhaus_id,operator_sid,old_version,new_version,original_ring_sha256,additive_ring_sha256,
                final_ring_sha256,new_key_sha256,catalog_sha256,envelope_sha256,factor_count,revoked_sessions,consumed_challenges)
            VALUES(@operation,'rotate','windows-local',@installation,current_database(),@house,@sid,@old,@new,
                @original,@additive,@final,@key,@catalog,@envelope,@factors,@sessions,@challenges)
            """, connection, transaction);
        command.Parameters.AddWithValue("operation", b.OperationId); command.Parameters.AddWithValue("installation", b.InstallationId);
        command.Parameters.AddWithValue("house", b.SystemhausId); command.Parameters.AddWithValue("sid", b.OperatorSid);
        command.Parameters.AddWithValue("old", b.OldVersion); command.Parameters.AddWithValue("new", b.NewVersion);
        command.Parameters.AddWithValue("original", b.OriginalRingHash); command.Parameters.AddWithValue("additive", b.AdditiveRingHash);
        command.Parameters.AddWithValue("final", b.FinalRingHash); command.Parameters.AddWithValue("key", b.NewKeyHash);
        command.Parameters.AddWithValue("catalog", b.CatalogHash); command.Parameters.AddWithValue("envelope", b.EnvelopeHash);
        command.Parameters.AddWithValue("factors", witness.FactorCount); command.Parameters.AddWithValue("sessions", witness.RevokedSessions);
        command.Parameters.AddWithValue("challenges", witness.ConsumedChallenges);
        if (await command.ExecuteNonQueryAsync(ct) != 1) throw Fail("mfa_rotation_witness_invalid");
    }

    private static void RequireTransaction(NpgsqlConnection connection, NpgsqlTransaction transaction, bool maintenance)
    {
        if (connection is null || transaction is null || connection.State != ConnectionState.Open || !ReferenceEquals(transaction.Connection, connection)
            || (maintenance && transaction.IsolationLevel != IsolationLevel.ReadCommitted)) throw Fail("mfa_rotation_transaction_required");
    }
    private static string DatabaseName(Guid installation) => "rc_db_" + installation.ToString("N");
    private static bool HashValid(string? value) => value is { Length: 64 } && value.All(c => c is >= '0' and <= '9' or >= 'a' and <= 'f');
    private static void Zero(byte[]? bytes) { if (bytes is not null) CryptographicOperations.ZeroMemory(bytes); }
    private static void AppendHash(IncrementalHash hash, byte[] bytes)
    {
        Span<byte> length = stackalloc byte[4]; BinaryPrimitives.WriteInt32BigEndian(length, bytes.Length);
        hash.AppendData(length); hash.AppendData(bytes);
    }
    private static MfaMaintenanceException Fail(string code) => new(code);
}
