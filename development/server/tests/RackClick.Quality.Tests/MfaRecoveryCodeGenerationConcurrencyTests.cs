using Npgsql;
using RackClick.Server;
using Xunit;
using Lab=RackClick.Quality.Tests.MfaAccountManagementTests.Laboratory;

namespace RackClick.Quality.Tests;

// Delivery once means one secret-bearing response even when the same generation request overlaps itself.
// No provider/key read is used by generation; the existing fixture supplies an MFA-verified account/session.
[Collection("MfaHttp")]
public sealed class MfaRecoveryCodeGenerationConcurrencyTests
{
    [Fact]
    public async Task TheSameConcurrentGenerationDisclosesTenCodesInOnlyOneResponse()
    {
        var ct=TestContext.Current.CancellationToken;
        await using var lab=await Lab.Create();await lab.Factor(lab.Admin.Id);
        await lab.Execute("UPDATE app_mfa_factor SET confirmed_at=clock_timestamp() WHERE user_id=@u",("u",lab.Admin.Id));
        var revision=await lab.Count("SELECT revision FROM systemhaus WHERE id=@h",("h",lab.House));
        var request=Guid.NewGuid();
        await using var blocker=await lab.RuntimeSource.OpenConnectionAsync(ct);
        await using var transaction=await blocker.BeginTransactionAsync(ct);
        await using(var hold=new NpgsqlCommand("SELECT revision FROM systemhaus WHERE id=@h FOR UPDATE",blocker,transaction))
        {hold.Parameters.AddWithValue("h",lab.House);await hold.ExecuteScalarAsync(ct);}
        var first=lab.Store.GenerateOwnRecoveryCodes(lab.Admin,Lab.Password,revision,request,true,ct);
        var second=lab.Store.GenerateOwnRecoveryCodes(lab.Admin,Lab.Password,revision,request,true,ct);
        var waiting=0L;
        try
        {
            // Both calls must really overlap: one waits on house, the other on the operation lock.
            for(var attempt=0;attempt<250;attempt++)
            {
                waiting=await lab.Count("""
                    SELECT count(DISTINCT l.pid) FROM pg_catalog.pg_locks l
                    JOIN pg_catalog.pg_stat_activity a ON a.pid=l.pid
                    WHERE NOT l.granted AND a.datname=current_database()
                    """);
                if(waiting>=2 || first.IsCompleted || second.IsCompleted)break;
                await Task.Delay(20,ct);
            }
        }
        finally{await transaction.CommitAsync(ct);}
        var results=await Task.WhenAll(first,second);
        Assert.True(waiting>=2,"Two generation requests were not observed waiting concurrently");
        Assert.Equal(1,results.Count(r=>r.CodesAvailable));Assert.Equal(1,results.Count(r=>!r.CodesAvailable));
        var delivered=results.Single(r=>r.CodesAvailable);var codes=delivered.Codes;
        Assert.NotNull(codes);Assert.Equal(10,codes.Length);Assert.Equal(10,codes.Distinct(StringComparer.Ordinal).Count());
        Assert.Null(results.Single(r=>!r.CodesAvailable).Codes);
        Assert.All(results,r=>{Assert.Equal(request,r.RequestId);Assert.Equal(lab.Admin.Id,r.UserId);Assert.Equal(revision+1,r.SystemhausRevision);});
        Assert.Equal(10,await lab.Count("SELECT count(*) FROM app_mfa_recovery_code WHERE code_hash LIKE 'rck1$%' AND consumed_at IS NULL"));
        Assert.Equal(1,await lab.Count("SELECT count(*) FROM operation WHERE request_id=@r",("r",request)));
        Assert.Equal(1,await lab.Count("SELECT count(*) FROM audit_event WHERE request_id=@r AND action='auth.mfa.recovery_codes.generated'",("r",request)));
        var state=await lab.SnapshotAll();
        foreach(var code in codes)
        {
            Assert.False(state.Contains(code,StringComparison.Ordinal),"Stored state contains a plaintext recovery value");
            Assert.False(state.Contains(code.Replace("-","",StringComparison.Ordinal),StringComparison.Ordinal),"Stored state contains a normalized recovery value");
        }
        var replay=await lab.Store.GenerateOwnRecoveryCodes(lab.Admin,Lab.Password,revision,request,true,ct);
        var receipt=await lab.Store.ReadOwnRecoveryCodesReceipt(lab.Admin,request,ct);
        Assert.False(replay.CodesAvailable);Assert.Null(replay.Codes);Assert.NotNull(receipt);Assert.False(receipt.CodesAvailable);Assert.Null(receipt.Codes);
        Assert.Equal(state,await lab.SnapshotAll());
    }
}
