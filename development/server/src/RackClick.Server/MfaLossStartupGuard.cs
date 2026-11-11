using System.Data;
using System.Runtime.Versioning;
using System.Security.Cryptography;
using System.Security.Principal;
using System.Text.Json;
using Npgsql;

namespace RackClick.Server;

[SupportedOSPlatform("windows")]
internal static class MfaLossStartupGuard
{
    // Validates loss history on every boot. True means its material supersedes the rotation material guard.
    internal static async Task<bool> ValidateIfLatestAsync(NpgsqlConnection db,string root,Guid installation,SecurityIdentifier reader,
        IReadOnlyCollection<SecurityIdentifier> trusted,IMfaKeyProvider provider,CancellationToken ct)
    {
        MfaMaintenanceAdmission.ThrowIfFenced(root,installation);
        var safe=new WindowsMfaKeyFileReader(reader,trusted.Select(s=>s.Value).ToHashSet(StringComparer.Ordinal));
        string marker=Path.Combine(root,installation.ToString("D"),WindowsMfaMaintenanceStore.LossStartupFileName);
        MfaLossStartupReceipt? receipt=null;
        if(File.Exists(marker))
        {
            var bytes=safe.ReadValidated(marker,4096);
            try{receipt=JsonSerializer.Deserialize<MfaLossStartupReceipt>(bytes);}catch(JsonException){throw Fail("mfa_loss_startup_receipt_invalid");}
            if(receipt is null||!JsonSerializer.SerializeToUtf8Bytes(receipt).AsSpan().SequenceEqual(bytes)||receipt.InstallationId!=installation||receipt.OperationId==Guid.Empty||receipt.SystemhausId==Guid.Empty
                ||receipt.NewVersion is <1 or >1000000||receipt.AllowedVersions is null||receipt.AllowedVersions.Length is <1 or >64
                ||receipt.AllowedVersions.Any(v=>v is <1 or >1000000)||!receipt.AllowedVersions.SequenceEqual(receipt.AllowedVersions.Distinct().Order())||!receipt.AllowedVersions.Contains(receipt.NewVersion)
                ||!HashValid(receipt.WitnessHash)||!HashValid(receipt.RingHash)||!HashValid(receipt.ActiveKeyHash))
                throw Fail("mfa_loss_startup_receipt_invalid");
        }
        await using var tx=await db.BeginTransactionAsync(IsolationLevel.RepeatableRead,ct);
        await using(var readOnly=new NpgsqlCommand("SET TRANSACTION READ ONLY",db,tx))await readOnly.ExecuteNonQueryAsync(ct);
        await using(var exists=new NpgsqlCommand("SELECT to_regclass('public.app_mfa_loss_startup_witness') IS NOT NULL,(SELECT max(version) FROM public.schema_migration)",db,tx))
        await using(var row=await exists.ExecuteReaderAsync(ct))
        {
            await row.ReadAsync(ct);
            if(row.IsDBNull(1))throw Fail("mfa_loss_startup_projection_missing");
            if(!row.GetBoolean(0))
            {
                if(row.GetInt32(1)>=48||receipt is not null)throw Fail("mfa_loss_startup_projection_missing");
                // Older schemas cannot contain a committed loss-reset when used by this guard.
                await row.DisposeAsync();await tx.CommitAsync(ct);return false;
            }
        }
        Guid? operation=null;int version=0;
        await using(var latest=new NpgsqlCommand("SELECT operation_id,new_version FROM public.app_mfa_loss_startup_witness ORDER BY new_version DESC LIMIT 1",db,tx))
        await using(var rows=await latest.ExecuteReaderAsync(ct))if(await rows.ReadAsync(ct)){operation=rows.GetGuid(0);version=rows.GetInt32(1);}
        if(operation is null)
        {
            if(receipt is not null)throw Fail("mfa_loss_startup_witness_missing");await tx.CommitAsync(ct);return false;
        }
        if(receipt is null||receipt.OperationId!=operation||receipt.NewVersion!=version)throw Fail("mfa_loss_startup_receipt_missing");
        var witness=await MfaLossResetDatabase.ReadStartupWitnessAsync(db,tx,operation.Value,ct)??throw Fail("mfa_loss_startup_witness_missing");
        if(witness.InstallationId!=installation||witness.DatabaseName!=db.Database||witness.SystemhausId!=receipt.SystemhausId||witness.Mode!="loss-reset"||witness.Authority!="windows-local"
            ||witness.NewVersion is <1 or >1000000||witness.LostVersions.Any(v=>v<1||v>=witness.NewVersion)
            ||Convert.ToHexStringLower(SHA256.HashData(JsonSerializer.SerializeToUtf8Bytes(witness)))!=receipt.WitnessHash)
            throw Fail("mfa_loss_startup_binding_invalid");
        int rotation=0;await using(var max=new NpgsqlCommand("SELECT COALESCE(max(new_version),0) FROM public.app_mfa_rotation_witness",db,tx))rotation=Convert.ToInt32(await max.ExecuteScalarAsync(ct));
        if(rotation>version){await tx.CommitAsync(ct);return false;}
        if(rotation==version)throw Fail("mfa_loss_startup_version_collision");
        // Loss does not erase the previous rotation receipt/history. Validate that binding, without asserting old material is current.
        var rotationMarker=Path.Combine(root,installation.ToString("D"),WindowsMfaMaintenanceStore.RotationStartupFileName);
        if(rotation>0)
        {
            var oldBytes=safe.ReadValidated(rotationMarker,4096);MfaRotationStartupReceipt? old;
            try{old=JsonSerializer.Deserialize<MfaRotationStartupReceipt>(oldBytes);}catch(JsonException){throw Fail("mfa_loss_rotation_history_invalid");}
            if(old is null||old.InstallationId!=installation||old.NewVersion!=rotation)throw Fail("mfa_loss_rotation_history_invalid");
            var oldWitness=await MfaRotationDatabase.ReadWitnessAsync(db,tx,old.OperationId,ct);
            if(oldWitness is null||oldWitness.Binding.NewVersion!=rotation||Convert.ToHexStringLower(SHA256.HashData(JsonSerializer.SerializeToUtf8Bytes(oldWitness.Binding)))!=old.BindingHash)
                throw Fail("mfa_loss_rotation_history_invalid");
        }
        else if(File.Exists(rotationMarker))throw Fail("mfa_loss_rotation_history_invalid");
        var folder=Path.Combine(root,installation.ToString("D"),"mfa-keys");var ringBytes=safe.ReadValidated(Path.Combine(folder,MfaKeyRing.RingFileName),MfaKeyRing.MaxRingFileBytes);
        var ring=MfaKeyRing.Parse(ringBytes,installation);
        if(ring.Entries.Single(e=>e.State==MfaKeyState.Active).Version!=version||!ring.Entries.Select(e=>e.Version).Order().SequenceEqual(receipt.AllowedVersions)
            ||ring.Entries.Any(e=>witness.LostVersions.Contains(e.Version))||Convert.ToHexStringLower(SHA256.HashData(ringBytes))!=receipt.RingHash
            ||Convert.ToHexStringLower(SHA256.HashData(safe.ReadValidated(Path.Combine(folder,MfaKeyRing.KeyFileName(version)),MfaKeyRing.MaxKeyFileBytes)))!=receipt.ActiveKeyHash)
            throw Fail("mfa_loss_startup_material_invalid");
        foreach(var entry in ring.Entries){var key=provider.GetKey(entry.Version);try{if(key.Length!=32)throw Fail("mfa_loss_startup_material_invalid");}finally{CryptographicOperations.ZeroMemory(key);}}
        await MfaMaintenanceCoordinator.AuthenticateFactors(db,tx,provider,ct);
        await tx.CommitAsync(ct);MfaMaintenanceAdmission.ThrowIfFenced(root,installation);return true;
    }
    private static bool HashValid(string? value)=>value is {Length:64}&&value.All(char.IsAsciiHexDigitLower);
    private static MfaMaintenanceException Fail(string code)=>new(code);
}
