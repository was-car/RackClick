using System.Data;
using System.Runtime.Versioning;
using System.Security.Cryptography;
using System.Security.Principal;
using System.Text.Json;
using Npgsql;

namespace RackClick.Server;

[SupportedOSPlatform("windows")]
internal static class MfaRotationStartupGuard
{
    // Read-only guard under host shared admission + ring lifetime handle; no recovery or writes at startup.
    internal static async Task ValidateAsync(NpgsqlConnection db,string root,Guid installation,SecurityIdentifier reader,
        IReadOnlyCollection<SecurityIdentifier> trusted,IMfaKeyProvider provider,CancellationToken ct)
    {
        if(await MfaLossStartupGuard.ValidateIfLatestAsync(db,root,installation,reader,trusted,provider,ct))return;
        MfaMaintenanceAdmission.ThrowIfFenced(root,installation);
        var safe=new WindowsMfaKeyFileReader(reader,trusted.Select(s=>s.Value).ToHashSet(StringComparer.Ordinal));
        var marker=Path.Combine(root,installation.ToString("D"),WindowsMfaMaintenanceStore.RotationStartupFileName);
        MfaRotationStartupReceipt? receipt=null;
        if(File.Exists(marker))
        {
            var bytes=safe.ReadValidated(marker,4096);
            receipt=JsonSerializer.Deserialize<MfaRotationStartupReceipt>(bytes);
            if(receipt is null || !JsonSerializer.SerializeToUtf8Bytes(receipt).AsSpan().SequenceEqual(bytes)
                || receipt.InstallationId!=installation || receipt.OperationId==Guid.Empty)
                throw new MfaMaintenanceException("mfa_rotation_startup_receipt_invalid");
        }
        await using var tx=await db.BeginTransactionAsync(IsolationLevel.RepeatableRead,ct);
        await using(var mode=new NpgsqlCommand("SET TRANSACTION READ ONLY",db,tx))await mode.ExecuteNonQueryAsync(ct);
        await using(var exists=new NpgsqlCommand("SELECT to_regclass('public.app_mfa_rotation_witness') IS NOT NULL",db,tx))
            if(await exists.ExecuteScalarAsync(ct) is not true)
            {
                if(receipt is not null)throw new MfaMaintenanceException("mfa_rotation_startup_witness_missing");
                await tx.CommitAsync(ct);return;
            }
        int? version=null;string? expectedHash=null;
        await using(var query=new NpgsqlCommand("SELECT installation_id,database_name,new_version,new_key_sha256 FROM public.app_mfa_rotation_witness ORDER BY new_version DESC LIMIT 1",db,tx))
        await using(var rows=await query.ExecuteReaderAsync(ct))
        {
            if(await rows.ReadAsync(ct))
            {
                if(rows.GetGuid(0)!=installation || rows.GetString(1)!=db.Database)throw new MfaMaintenanceException("mfa_rotation_startup_binding_invalid");
                version=rows.GetInt32(2);expectedHash=rows.GetString(3);
            }
        }
        if(version is not null)
        {
            if(receipt is null || receipt.NewVersion!=version)throw new MfaMaintenanceException("mfa_rotation_startup_receipt_missing");
            var witness=await MfaRotationDatabase.ReadWitnessAsync(db,tx,receipt.OperationId,ct);
            if(witness is null || witness.Binding.NewVersion!=version
                || Convert.ToHexStringLower(SHA256.HashData(JsonSerializer.SerializeToUtf8Bytes(witness.Binding)))!=receipt.BindingHash)
                throw new MfaMaintenanceException("mfa_rotation_startup_witness_mismatch");
            var keys=Path.Combine(root,installation.ToString("D"),"mfa-keys");
            var ring=MfaKeyRing.Parse(safe.ReadValidated(Path.Combine(keys,MfaKeyRing.RingFileName),MfaKeyRing.MaxRingFileBytes),installation);
            if(ring.Entries.Single(e=>e.State==MfaKeyState.Active).Version!=version
                || Convert.ToHexStringLower(SHA256.HashData(safe.ReadValidated(Path.Combine(keys,MfaKeyRing.KeyFileName(version.Value)),MfaKeyRing.MaxKeyFileBytes)))!=expectedHash)
                throw new MfaMaintenanceException("mfa_rotation_startup_material_invalid");
            await using(var old=new NpgsqlCommand("SELECT EXISTS(SELECT 1 FROM public.app_mfa_factor WHERE key_version<>@version)",db,tx))
            {
                old.Parameters.AddWithValue("version",version.Value);
                if(await old.ExecuteScalarAsync(ct) is true)throw new MfaMaintenanceException("mfa_rotation_startup_factor_version_invalid");
            }
            await MfaMaintenanceCoordinator.AuthenticateFactors(db,tx,provider,ct);
        }
        else if(receipt is not null)throw new MfaMaintenanceException("mfa_rotation_startup_witness_missing");
        await tx.CommitAsync(ct);
        MfaMaintenanceAdmission.ThrowIfFenced(root,installation);
    }
}
