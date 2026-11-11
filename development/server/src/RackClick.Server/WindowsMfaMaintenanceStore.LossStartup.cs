using System.Runtime.InteropServices;
using System.Text.Json;

namespace RackClick.Server;

internal sealed record MfaLossStartupReceipt(Guid InstallationId,Guid OperationId,Guid SystemhausId,int NewVersion,
    int[] AllowedVersions,string WitnessHash,string RingHash,string ActiveKeyHash);

internal sealed partial class WindowsMfaMaintenanceStore
{
    internal const string LossStartupFileName="mfa-loss-state.json";
    private sealed record LossCompletion(Guid OperationId,string JournalHash,string ReceiptHash,Identity ReceiptObject,Identity FenceObject);
    private string LossStartupPath=>Path.Combine(_folder,LossStartupFileName);

    internal bool LossReleased(Guid operation)=>!Exists(_fence)&&Exists(LossPath(operation,"complete"));
    private void RequireLossCompletion(Guid operation,string journalHash,Identity fence)
    {
        var done=Decode<LossCompletion>(ReadPrivate(LossPath(operation,"complete"),4096));
        if(done.OperationId!=operation||done.JournalHash!=journalHash||done.FenceObject!=fence)throw Corrupt("loss completion binding");
        RequireIdentity(IdentityAt(LossStartupPath),done.ReceiptObject);
        RequireHash(_reader.ReadValidated(LossStartupPath,4096),done.ReceiptHash);
    }
    internal void PublishLossStartupReceipt(MfaLossResetWitness witness)
    {
        var journal=ReadLossJournal(witness.OperationId);RequireLossMaterial(witness.OperationId);
        var bytesRing=ReadRing();var ring=MfaKeyRing.Parse(bytesRing,_installation);
        if(ring.Entries.Single(e=>e.State==MfaKeyState.Active).Version!=witness.NewVersion)throw Corrupt("loss receipt before final ring");
        var key=_reader.ReadValidated(Path.Combine(Path.GetDirectoryName(_ring)!,MfaKeyRing.KeyFileName(witness.NewVersion)),MfaKeyRing.MaxKeyFileBytes);
        var receipt=new MfaLossStartupReceipt(_installation,witness.OperationId,witness.SystemhausId,witness.NewVersion,
            ring.Entries.Select(e=>e.Version).Order().ToArray(),Hash(JsonSerializer.SerializeToUtf8Bytes(witness)),Hash(bytesRing),Hash(key));
        var bytes=JsonSerializer.SerializeToUtf8Bytes(receipt);var identityPath=LossPath(witness.OperationId,"startup-identity");
        if(Exists(LossStartupPath))
        {
            RequireHash(_reader.ReadValidated(LossStartupPath,4096),Hash(bytes));
            RequireIdentity(IdentityAt(LossStartupPath),Decode<Identity>(ReadPrivate(identityPath,4096)));return;
        }
        var stage=LossPath(witness.OperationId,"startup-stage");Identity identity;
        if(!Exists(stage)){using var handle=Create(stage,true,Read|Write,1);identity=Information(handle);WriteFlush(handle,bytes);}
        else {using var handle=Open(stage,Read,1);RequireServiceFile(Security(handle));RequireHash(ReadHandle(handle,4096),Hash(bytes));identity=Information(handle);}
        if(!Exists(identityPath))CreateContent(identityPath,JsonSerializer.SerializeToUtf8Bytes(identity));
        RequireIdentity(identity,Decode<Identity>(ReadPrivate(identityPath,4096)));Checkpoint?.Invoke("before_loss_startup_receipt");
        if(Exists(LossStartupPath))throw Corrupt("loss receipt collision");
        File.Move(stage,LossStartupPath,false);RequireIdentity(IdentityAt(LossStartupPath),identity);RequireHash(_reader.ReadValidated(LossStartupPath,4096),Hash(bytes));
        Checkpoint?.Invoke("after_loss_startup_receipt");
    }
    // Called only by the coordinator after its read transaction and admission have been verified.
    internal void CompleteLoss(Guid operation)
    {
        var journal=ReadLossJournal(operation);
        if(LossReleased(operation))return;
        var bytesJournal=ReadPrivate(LossPath(operation,"plan"),MaxRotationJournalBytes);
        var receiptBytes=_reader.ReadValidated(LossStartupPath,4096);var receipt=Decode<MfaLossStartupReceipt>(receiptBytes);
        if(receipt.OperationId!=operation||receipt.InstallationId!=_installation||receipt.NewVersion!=journal.Plan.NewVersion)throw Corrupt("loss release receipt");
        var expectedIdentity=Decode<Identity>(ReadPrivate(LossPath(operation,"startup-identity"),4096));RequireIdentity(IdentityAt(LossStartupPath),expectedIdentity);
        var done=JsonSerializer.SerializeToUtf8Bytes(new LossCompletion(operation,Hash(bytesJournal),Hash(receiptBytes),expectedIdentity,journal.FenceObject));
        var complete=LossPath(operation,"complete");if(!Exists(complete))CreateContent(complete,done);RequireHash(ReadPrivate(complete,4096),Hash(done));
        Checkpoint?.Invoke("before_loss_release");
        using(var handle=Open(_fence,Read|Delete,1))
        {
            RequireServiceFile(Security(handle));RequireIdentity(Information(handle),journal.FenceObject);
            var fence=Decode<LossFence>(ReadHandle(handle,4096));if(fence.OperationId!=operation||fence.JournalHash!=Hash(bytesJournal))throw Corrupt("loss fence changed before release");
            var disposition=new FileDisposition{DeleteFile=true};
            if(!SetFileInformationByHandle(handle,4,ref disposition,(uint)Marshal.SizeOf<FileDisposition>()))throw NativeFailure("delete loss fence");
        }
        Checkpoint?.Invoke("after_loss_release");
    }
}
