using System.Security.Cryptography;
using System.Text.Json;
using System.Text.RegularExpressions;

namespace RackClick.Server;

internal sealed record MfaLossSource(byte[] Ring,int[] FileVersions,string FilesHash);
internal sealed record MfaLossMaterial(string RingHash,string FilesHash);

internal sealed partial class WindowsMfaMaintenanceStore
{
    private sealed record LossFile(string Name,int Version,string Hash,Identity Object);
    private sealed record LossJournal(MfaLossResetPlan Plan,LossFile[] Files,Identity FenceObject);
    private sealed record LossFence(int FormatVersion,Guid InstallationId,Guid OperationId,string JournalHash,string Mode);
    private sealed record LossPublication(Identity Key,Identity Ring);
    private sealed record LossEnvelope(string PlanHash,string MaterialHash,string EnvelopeHash);
    private string LossPath(Guid operation,string kind)=>OperationPath(operation,"loss-"+kind);
    internal string LossCandidateRoot(Guid operation)=>Metadata(operation.ToString("N")+".lc");
    private byte[] ReadLossOpaque(string path,int maximum)
    {
        using var handle=Open(path,Read,1);RequireServiceFile(Security(handle));var identity=Information(handle);
        var length=RandomAccess.GetLength(handle);if(length<0||length>maximum)throw Corrupt("loss source size");
        var bytes=length==0?Array.Empty<byte>():ReadHandle(handle,maximum);
        RequireIdentity(Information(handle),identity);RequireServiceFile(Security(handle));return bytes;
    }

    private LossFile[] LossSourceFiles()
    {
        RequireLocked();var folder=Path.GetDirectoryName(_ring)!;var result=new List<LossFile>();
        foreach(var path in Directory.EnumerateFileSystemEntries(folder).Order(StringComparer.Ordinal))
        {
            if(result.Count>=129)throw Corrupt("loss source census too large");
            var name=Path.GetFileName(path);int version=0;
            if(name!=MfaKeyRing.RingFileName)
            {
                var match=Regex.Match(name,@"\Akey-v([1-9][0-9]{0,6})\.dpapi\.json\z",RegexOptions.CultureInvariant|RegexOptions.NonBacktracking);
                if(!match.Success||!int.TryParse(match.Groups[1].Value,out version)||version>1000000)throw Corrupt("unknown loss source object");
            }
            var identity=IdentityAt(path);var bytes=ReadLossOpaque(path,version==0?MfaKeyRing.MaxRingFileBytes:MfaKeyRing.MaxKeyFileBytes);
            RequireIdentity(IdentityAt(path),identity);result.Add(new(name,version,Hash(bytes),identity));
        }
        if(!result.Any(f=>f.Version==0))throw Corrupt("loss ring history unknown");
        return result.ToArray();
    }
    internal MfaLossSource InspectLossSource()
    {
        var files=LossSourceFiles();var ring=ReadRing();
        if(files.Single(f=>f.Version==0).Hash!=Hash(ring))throw Corrupt("loss source changed");
        return new(ring,files.Where(f=>f.Version>0).Select(f=>f.Version).ToArray(),Hash(JsonSerializer.SerializeToUtf8Bytes(files)));
    }
    internal void PrepareLoss(MfaLossResetPlan plan)
    {
        RequireLocked();RequireNoPending();
        if(Directory.EnumerateFileSystemEntries(_management,"*.loss-*").Any())throw Corrupt("previous loss operation requires reconciliation");
        var files=LossSourceFiles();if(plan.InstallationId!=_installation||plan.OperationId==Guid.Empty
            ||Hash(JsonSerializer.SerializeToUtf8Bytes(files))!=plan.SourceFilesHash||Hash(ReadRing())!=plan.SourceRingHash)throw Corrupt("loss source binding");
        foreach(var file in files)
        {
            var bytes=ReadLossOpaque(Path.Combine(Path.GetDirectoryName(_ring)!,file.Name),file.Version==0?MfaKeyRing.MaxRingFileBytes:MfaKeyRing.MaxKeyFileBytes);
            RequireHash(bytes,file.Hash);RequireIdentity(IdentityAt(Path.Combine(Path.GetDirectoryName(_ring)!,file.Name)),file.Object);
            CreateContent(LossPath(plan.OperationId,"archive-"+file.Name),JsonSerializer.SerializeToUtf8Bytes(bytes));
        }
        using var fence=Create(_fence,true,Read|Write,1);
        var journal=new LossJournal(plan,files,Information(fence));var bytesJournal=JsonSerializer.SerializeToUtf8Bytes(journal);
        CreateContent(LossPath(plan.OperationId,"plan"),bytesJournal);
        WriteFlush(fence,JsonSerializer.SerializeToUtf8Bytes(new LossFence(1,_installation,plan.OperationId,Hash(bytesJournal),"loss-reset")));
        Checkpoint?.Invoke("loss_planned_fenced");
    }
    private LossJournal ReadLossJournal(Guid operation)
    {
        RequireLocked();var bytes=ReadPrivate(LossPath(operation,"plan"),MaxRotationJournalBytes);var journal=Decode<LossJournal>(bytes);
        if(journal.Plan.InstallationId!=_installation||journal.Plan.OperationId!=operation)throw Corrupt("loss journal identity");
        if(Exists(_fence))
        {
            using var handle=Open(_fence,Read,1);RequireServiceFile(Security(handle));RequireIdentity(Information(handle),journal.FenceObject);
            var fence=Decode<LossFence>(ReadHandle(handle,4096));
            if(fence.Mode!="loss-reset"||fence.FormatVersion!=1||fence.InstallationId!=_installation||fence.OperationId!=operation||fence.JournalHash!=Hash(bytes))throw Corrupt("loss journal binding");
        }
        else RequireLossCompletion(operation,Hash(bytes),journal.FenceObject);
        foreach(var file in journal.Files)RequireHash(Decode<byte[]>(ReadPrivate(LossPath(operation,"archive-"+file.Name),2*Math.Max(MfaKeyRing.MaxRingFileBytes,MfaKeyRing.MaxKeyFileBytes))),file.Hash);
        return journal;
    }
    internal MfaLossResetPlan ReadLossPlan(Guid operation)=>ReadLossJournal(operation).Plan;
    internal void VerifyLossOriginal(Guid operation)
    {
        var journal=ReadLossJournal(operation);var current=LossSourceFiles();
        if(!current.SequenceEqual(journal.Files))throw Corrupt("loss source changed after planning");
    }
    internal MfaLossMaterial RecordLossMaterial(Guid operation)
    {
        var material=InspectLossCandidate(operation);CreateContent(LossPath(operation,"ready"),JsonSerializer.SerializeToUtf8Bytes(material));return material;
    }
    internal MfaLossMaterial InspectLossCandidate(Guid operation)
    {
        ReadLossJournal(operation);var root=LossCandidateRoot(operation);
        var folder=Path.Combine(root,_installation.ToString("D"),"mfa-keys");
        _reader.RequireSafeFolder(root);_reader.RequireSafeFolder(Path.GetDirectoryName(folder)!);_reader.RequireSafeFolder(folder);
        var ringBytes=_reader.ReadValidated(Path.Combine(folder,MfaKeyRing.RingFileName),MfaKeyRing.MaxRingFileBytes);
        var ring=MfaKeyRing.Parse(ringBytes,_installation);var files=new SortedDictionary<string,object>(StringComparer.Ordinal);
        foreach(var path in Directory.EnumerateFileSystemEntries(folder))
        {
            var name=Path.GetFileName(path);
            if(name!=MfaKeyRing.RingFileName&&!ring.Entries.Any(e=>MfaKeyRing.KeyFileName(e.Version)==name))throw Corrupt("unknown candidate file");
            var identity=IdentityAt(path);var bytes=_reader.ReadValidated(path,name==MfaKeyRing.RingFileName?MfaKeyRing.MaxRingFileBytes:MfaKeyRing.MaxKeyFileBytes);
            RequireIdentity(IdentityAt(path),identity);files.Add(name,new{Hash=Hash(bytes),Object=identity});
        }
        if(files.Count!=ring.Entries.Count+1)throw Corrupt("incomplete loss candidate");
        return new(Hash(ringBytes),Hash(JsonSerializer.SerializeToUtf8Bytes(files)));
    }
    internal byte[] ReadLossCandidateRing(Guid operation)=>_reader.ReadValidated(Path.Combine(LossCandidateRoot(operation),_installation.ToString("D"),"mfa-keys",MfaKeyRing.RingFileName),MfaKeyRing.MaxRingFileBytes);
    internal MfaLossMaterial RequireLossMaterial(Guid operation)
    {
        var expected=Decode<MfaLossMaterial>(ReadPrivate(LossPath(operation,"ready"),4096));
        if(InspectLossCandidate(operation)!=expected)throw Corrupt("loss candidate changed");return expected;
    }
    internal string PinLossEnvelope(Guid operation,string hash)
    {
        var plan=ReadLossPlan(operation);var material=RequireLossMaterial(operation);
        if(hash.Length!=64||hash.Any(c=>!char.IsAsciiHexDigitLower(c)))throw Corrupt("invalid envelope digest");
        var bytes=JsonSerializer.SerializeToUtf8Bytes(new LossEnvelope(Hash(JsonSerializer.SerializeToUtf8Bytes(plan)),material.FilesHash,hash));
        var path=LossPath(operation,"envelope-pin");
        if(!Exists(path))CreateContent(path,bytes);
        RequireHash(ReadPrivate(path,4096),Hash(bytes));return hash;
    }
    internal string RequireLossEnvelope(Guid operation)
    {
        var pin=Decode<LossEnvelope>(ReadPrivate(LossPath(operation,"envelope-pin"),4096));
        // Existing immutable pin, never infer it from a DB witness during reconciliation.
        return PinLossEnvelope(operation,pin.EnvelopeHash);
    }
    internal void PublishLoss(Guid operation)
    {
        var journal=ReadLossJournal(operation);var plan=journal.Plan;var material=RequireLossMaterial(operation);
        var sourceFolder=Path.GetDirectoryName(_ring)!;var keyName=MfaKeyRing.KeyFileName(plan.NewVersion);
        var keyPath=Path.Combine(sourceFolder,keyName);var keyStage=LossPath(operation,"stage-key");var ringStage=LossPath(operation,"stage-ring");
        var publicationPath=LossPath(operation,"publication");
        var candidate=Path.Combine(LossCandidateRoot(operation),_installation.ToString("D"),"mfa-keys");
        var keyBytes=_reader.ReadValidated(Path.Combine(candidate,keyName),MfaKeyRing.MaxKeyFileBytes);
        var ringBytes=_reader.ReadValidated(Path.Combine(candidate,MfaKeyRing.RingFileName),MfaKeyRing.MaxRingFileBytes);
        LossPublication publication;
        if(!Exists(publicationPath))
        {
            VerifyLossOriginal(operation);
            using var key=Create(keyStage,true,Read|Write,1);WriteFlush(key,keyBytes);var keyIdentity=Information(key);
            using var ring=Create(ringStage,true,Read|Write,1);WriteFlush(ring,ringBytes);
            publication=new(keyIdentity,Information(ring));CreateContent(publicationPath,JsonSerializer.SerializeToUtf8Bytes(publication));
        }
        else publication=Decode<LossPublication>(ReadPrivate(publicationPath,4096));
        // Preserve every original blob, including corrupt/opaque material. Only the ring and the planned new key are published.
        foreach(var file in journal.Files.Where(f=>f.Version!=0))
        {var path=Path.Combine(sourceFolder,file.Name);RequireIdentity(IdentityAt(path),file.Object);RequireHash(ReadLossOpaque(path,MfaKeyRing.MaxKeyFileBytes),file.Hash);}
        var allowed=journal.Files.Select(f=>f.Name).Append(keyName).ToHashSet(StringComparer.Ordinal);
        if(Directory.EnumerateFileSystemEntries(sourceFolder).Any(p=>!allowed.Contains(Path.GetFileName(p))))throw Corrupt("unknown live loss object");
        Checkpoint?.Invoke("before_loss_key_publish");
        if(!Exists(keyPath))
        {RequireIdentity(IdentityAt(keyStage),publication.Key);RequireHash(_reader.ReadValidated(keyStage,MfaKeyRing.MaxKeyFileBytes),Hash(keyBytes));File.Move(keyStage,keyPath,false);}
        RequireIdentity(IdentityAt(keyPath),publication.Key);RequireHash(_reader.ReadValidated(keyPath,MfaKeyRing.MaxKeyFileBytes),Hash(keyBytes));
        Checkpoint?.Invoke("after_loss_key_publish");
        var live=_reader.ReadValidated(_ring,MfaKeyRing.MaxRingFileBytes);
        if(Hash(live)==plan.SourceRingHash)
        {
            RequireIdentity(IdentityAt(_ring),journal.Files.Single(f=>f.Version==0).Object);RequireIdentity(IdentityAt(ringStage),publication.Ring);
            RequireHash(_reader.ReadValidated(ringStage,MfaKeyRing.MaxRingFileBytes),material.RingHash);File.Replace(ringStage,_ring,null,false);
        }
        RequireIdentity(IdentityAt(_ring),publication.Ring);RequireHash(_reader.ReadValidated(_ring,MfaKeyRing.MaxRingFileBytes),material.RingHash);
        Checkpoint?.Invoke("after_loss_ring_publish");
        // No fence removal or rotate receipt: startup/service verification is a later, explicit loss-reset step.
    }
}
