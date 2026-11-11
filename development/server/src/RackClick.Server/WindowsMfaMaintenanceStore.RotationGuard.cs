using System.Text.Json;

namespace RackClick.Server;

internal sealed record MfaRotationStartupReceipt(Guid InstallationId,Guid OperationId,int NewVersion,string BindingHash);

internal sealed partial class WindowsMfaMaintenanceStore
{
    internal const string RotationStartupFileName="mfa-rotation-state.json";
    private sealed record StartupPrior(Guid OperationId,Identity? Object,string? Hash);

    internal MfaRotationStartupReceipt? RecordRotationStartupPrior(Guid operation)
    {
        RequireLocked();
        var target=Path.Combine(_folder,RotationStartupFileName);
        Identity? identity=null;string? hash=null;MfaRotationStartupReceipt? receipt=null;
        if(Exists(target))
        {
            var bytes=_reader.ReadValidated(target,4096);identity=IdentityAt(target);hash=Hash(bytes);
            receipt=Decode<MfaRotationStartupReceipt>(bytes);
            if(receipt.InstallationId!=_installation || receipt.OperationId==Guid.Empty)throw Corrupt("unknown startup receipt");
            RequireHash(_reader.ReadValidated(target,4096),hash);RequireIdentity(IdentityAt(target),identity);
        }
        CreateContent(OperationPath(operation,"startup-prior"),JsonSerializer.SerializeToUtf8Bytes(new StartupPrior(operation,identity,hash)));
        return receipt;
    }

    internal void PublishRotationStartupReceipt(MfaRotationWitness witness)
    {
        RequireLocked();
        var journal=ReadRotation(witness.Binding.OperationId);
        if(journal.State is not ("ring_published" or "verified") || journal.NewVersion!=witness.Binding.NewVersion)
            throw Corrupt("rotation receipt before final ring");
        var bytes=JsonSerializer.SerializeToUtf8Bytes(new MfaRotationStartupReceipt(_installation,witness.Binding.OperationId,
            witness.Binding.NewVersion,Hash(JsonSerializer.SerializeToUtf8Bytes(witness.Binding))));
        var target=Path.Combine(_folder,RotationStartupFileName);
        var identityRecord=OperationPath(witness.Binding.OperationId,"startup-stage-identity");
        if(Exists(target) && _reader.ReadValidated(target,4096).AsSpan().SequenceEqual(bytes))
        {
            RequireIdentity(IdentityAt(target),Decode<Identity>(ReadPrivate(identityRecord,4096)));
            return;
        }
        var prior=Decode<StartupPrior>(ReadPrivate(OperationPath(witness.Binding.OperationId,"startup-prior"),4096));
        if(prior.OperationId!=witness.Binding.OperationId)throw Corrupt("startup prior operation");
        void RequirePrior()
        {
            if(prior.Object is null){if(Exists(target))throw Corrupt("unknown startup receipt collision");}
            else
            {
                RequireIdentity(IdentityAt(target),prior.Object);
                RequireHash(_reader.ReadValidated(target,4096),prior.Hash??throw Corrupt("missing prior hash"));
            }
        }
        RequirePrior();
        var stage=Metadata(witness.Binding.OperationId.ToString("N")+".startup-receipt.json");
        Identity identity;
        if(!Exists(stage))
        {
            using var handle=Create(stage,true,Read|Write,1);identity=Information(handle);WriteFlush(handle,bytes);
        }
        else
        {
            using var handle=Open(stage,Read,1);RequireServiceFile(Security(handle));
            RequireHash(ReadHandle(handle,4096),Hash(bytes));identity=Information(handle);
        }
        if(!Exists(identityRecord))CreateContent(identityRecord,JsonSerializer.SerializeToUtf8Bytes(identity));
        RequireIdentity(identity,Decode<Identity>(ReadPrivate(identityRecord,4096)));
        Checkpoint?.Invoke("before_startup_receipt");
        RequirePrior();
        RequireIdentity(IdentityAt(stage),identity);
        if(prior.Object is null)File.Move(stage,target,false);
        else
        {
            File.Replace(stage,target,null,false);
        }
        RequireIdentity(IdentityAt(target),identity);
        RequireHash(_reader.ReadValidated(target,4096),Hash(bytes));
        Checkpoint?.Invoke("after_startup_receipt");
    }
}
