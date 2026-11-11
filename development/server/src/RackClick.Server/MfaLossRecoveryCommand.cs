using System.ComponentModel;
using System.Runtime.Versioning;
using System.Security.Cryptography;
using System.Security.Principal;
using System.Text;
using System.Text.Json;
using Npgsql;

namespace RackClick.Server;

// Explicit local authority only; never configured from DI, web claims, environment or input JSON.
internal static class MfaLossRecoveryCommand
{
    private const int Limit=65536;
    internal sealed record Request(string Action,MfaMaintenanceRequest Maintenance,string Service,int[] Lost,
        SecurityIdentifier? Custodian,string? Password,string? Folder,string? Name,string? Envelope,string? EnvelopeHash);

    internal static async Task<int> RunAsync(TextReader input,TextWriter output,CancellationToken ct)
    {
        var denied=MfaEmergencyRecoveryCommand.AuthorizationFailure();
        if(denied is not null)return await Reject(output,denied,"authorization",false);
        if(!OperatingSystem.IsWindows())return await Reject(output,"mfa_emergency_not_windows","authorization",false);
        return await RunAuthorized(input,output,ct);
    }
    [SupportedOSPlatform("windows")]
    private static async Task<int> RunAuthorized(TextReader input,TextWriter output,CancellationToken ct)
    {
        string stage="input";bool attempted=false;
        using var timeout=CancellationTokenSource.CreateLinkedTokenSource(ct);timeout.CancelAfter(TimeSpan.FromMinutes(5));ct=timeout.Token;
        try
        {
            var text=new StringBuilder();var buffer=new char[4096];
            while(true)
            {int count=await input.ReadAsync(buffer.AsMemory(),ct).AsTask().WaitAsync(ct);if(count==0)break;if(text.Length>Limit-count)throw Invalid();text.Append(buffer,0,count);}
            var r=Parse(text.ToString());stage=r.Action;
            // Every coordinator entry recaptures authority and the stopped, bound SCM service.
            attempted=true;
            if(r.Action=="export")
            {
                var file=await MfaLossResetCoordinator.ExportToFileAsync(r.Maintenance,r.Service,r.Custodian!,r.Password!,r.Folder!,r.Name!,ct);
                await output.WriteLineAsync(JsonSerializer.Serialize(new{status="verified",code="mfa_loss_external_envelope_published",stage,
                    operationId=r.Maintenance.OperationId,envelopeSha256=file.Sha256,envelopeBytes=file.Length,sessionGranted=false,serviceVerified=false}));
                return 0;
            }
            MfaLossResetResult result;
            if(r.Action=="apply")
            {
                result=await MfaLossResetCoordinator.ApplyFromFileAsync(r.Maintenance,r.Service,r.Custodian!,r.Envelope!,r.Password!,r.EnvelopeHash!,ct);
            }
            else result=r.Action switch
            {
                "prepare"=>await MfaLossResetCoordinator.PrepareAsync(r.Maintenance,r.Service,r.Lost,ct),
                "publish"=>await MfaLossResetCoordinator.PublishAsync(r.Maintenance,r.Service,ct),
                "complete"=>await MfaLossResetCoordinator.CompleteAsync(r.Maintenance,r.Service,ct),
                _=>throw Invalid()
            };
            await output.WriteLineAsync(JsonSerializer.Serialize(new{status="verified",code="mfa_loss_"+result.Phase,stage,result.OperationId,result.NewVersion,result.Factors,
                sessionGranted=false,serviceVerified=false}));return 0;
        }
        catch(MfaMaintenanceException e){return await Reject(output,e.Code,stage,attempted);}
        catch(MfaBackupCatalogException){return await Reject(output,"mfa_backup_catalog_rejected",stage,attempted);}
        catch(MfaKeyRingException){return await Reject(output,"mfa_loss_store_rejected",stage,attempted);}
        catch(MfaKeyRetentionException){return await Reject(output,"mfa_loss_dependencies_invalid",stage,attempted);}
        catch(WindowsMfaKeyRecoveryException){return await Reject(output,"mfa_loss_envelope_rejected",stage,attempted);}
        catch(WindowsMfaKeyRecoveryFileException){return await Reject(output,"mfa_loss_envelope_file_rejected",stage,attempted);}
        catch(MfaRecoveryEnvelopeException){return await Reject(output,"mfa_loss_envelope_rejected",stage,attempted);}
        catch(NpgsqlException){return await Reject(output,"mfa_loss_database_unavailable",stage,attempted);}
        catch(CryptographicException){return await Reject(output,"mfa_loss_authentication_failed",stage,attempted);}
        catch(OperationCanceledException){return await Reject(output,"mfa_loss_cancelled",stage,attempted);}
        catch(Exception e)when(e is IOException or UnauthorizedAccessException or Win32Exception)
        {return await Reject(output,"mfa_loss_local_io_failed",stage,attempted);}
        catch(InvalidOperationException e)when(e.Message.StartsWith("mfa_maintenance_",StringComparison.Ordinal))
        {return await Reject(output,"mfa_loss_service_rejected",stage,attempted);}
    }
    [SupportedOSPlatform("windows")]
    internal static Request Parse(string text)
    {
        if(text.Length>Limit)throw Invalid();
        try
        {
            _=new UTF8Encoding(false,true).GetByteCount(text);
            using var doc=JsonDocument.Parse(text,new JsonDocumentOptions{MaxDepth=4});if(doc.RootElement.ValueKind!=JsonValueKind.Object)throw Invalid();
            var fields=new Dictionary<string,JsonElement>(StringComparer.Ordinal);
            foreach(var p in doc.RootElement.EnumerateObject())
            {string fieldName;try{fieldName=p.Name;}catch(InvalidOperationException){throw Invalid();}if(!fields.TryAdd(fieldName,p.Value))throw Invalid();}
            string Text(string name,int max=4096)
            {
                if(!fields.TryGetValue(name,out var v)||v.ValueKind!=JsonValueKind.String)throw Invalid();string value;
                try{value=v.GetString()!;}catch(InvalidOperationException){throw Invalid();}
                if(value.Length==0||value.Length>max||value.Any(c=>c<32))throw Invalid();return value;
            }
            Guid Id(string name){var v=Text(name);return Guid.TryParseExact(v,"D",out var id)&&id!=Guid.Empty&&id.ToString("D")==v?id:throw Invalid();}
            string Hash(string name){var v=Text(name);return v.Length==64&&v.All(char.IsAsciiHexDigitLower)?v:throw Invalid();}
            string PathValue(string name)
            {
                var v=Text(name);if(!Path.IsPathFullyQualified(v)||!char.IsAsciiLetter(v[0])||v[1]!=':'||v[2]!='\\'||v.AsSpan(2).Contains(':')||v.Contains('"'))throw Invalid();
                return Path.GetFullPath(v);
            }
            SecurityIdentifier Sid(string name)
            {try{var sid=new SecurityIdentifier(Text(name));return sid.IsAccountSid()?sid:throw Invalid();}catch(ArgumentException){throw Invalid();}}
            var action=Text("action");
            string[] common=["action","ownerConnection","instancesRoot","installationId","readerSid","serviceName","expectedCatalogSha256","operationId","confirmation"];
            string[] extra=action switch{"prepare"=>["lostVersions"],"export"=>["envelopeFolder","envelopeName","envelopeReaderSid","password"],
                "apply"=>["envelopePath","envelopeReaderSid","password","expectedEnvelopeSha256"],"publish" or "complete"=>[],_=>throw Invalid()};
            if(fields.Count!=common.Length+extra.Length||common.Concat(extra).Any(k=>!fields.ContainsKey(k)))throw Invalid();
            var installation=Id("installationId");var operation=Id("operationId");var root=PathValue("instancesRoot");
            try{_=MfaLossResetCoordinator.NativeServiceRoot(root,installation);}catch(MfaMaintenanceException){throw Invalid();}
            var reader=Sid("readerSid");var service=Text("serviceName",128);
            if(service.Any(c=>!char.IsAsciiLetterOrDigit(c)&&c is not '-' and not '_' and not '.'))throw Invalid();
            if(Text("confirmation")!=$"CONFIRMO PERDIDA {installation:D} {operation:D} {action}")throw Invalid();
            int[] lost=[];
            if(action=="prepare")
            {
                var list=fields["lostVersions"];if(list.ValueKind!=JsonValueKind.Array||list.GetArrayLength() is <1 or >64)throw Invalid();
                lost=list.EnumerateArray().Select(v=>v.ValueKind==JsonValueKind.Number&&v.TryGetInt32(out var n)&&n is >=1 and <=1000000?n:throw Invalid()).ToArray();
                if(lost.Distinct().Count()!=lost.Length)throw Invalid();
            }
            SecurityIdentifier? custodian=null;string? password=null,folder=null,name=null,envelope=null,eh=null;
            if(action is "export" or "apply")
            {
                custodian=Sid("envelopeReaderSid");if(custodian==reader)throw Invalid();password=Text("password",512);
                if(password.Length<12)throw Invalid();
            }
            if(action=="export")
            {
                folder=PathValue("envelopeFolder");name=Text("envelopeName",126);
                if(!System.Text.RegularExpressions.Regex.IsMatch(name,@"\A[A-Za-z0-9][A-Za-z0-9._-]{0,119}\.rckey\z",System.Text.RegularExpressions.RegexOptions.CultureInvariant))throw Invalid();
            }
            if(action=="apply"){envelope=PathValue("envelopePath");eh=Hash("expectedEnvelopeSha256");}
            return new(action,new("loss-reset",Text("ownerConnection"),root,installation,reader,Hash("expectedCatalogSha256"),0,operation,null),service,lost,custodian,password,folder,name,envelope,eh);
        }
        catch(Exception e)when(e is JsonException or EncoderFallbackException or ArgumentException or NotSupportedException or PathTooLongException){throw Invalid();}
    }
    private static async Task<int> Reject(TextWriter output,string code,string stage,bool attempted)
    {
        await output.WriteLineAsync(JsonSerializer.Serialize(new{status="rejected",code,stage,operationsApplied=attempted?(int?)null:0,
            maintenanceState=attempted?"inspect_before_retry":"not_started",sessionGranted=false,serviceVerified=false}));return 1;
    }
    private static MfaMaintenanceException Invalid()=>new("mfa_emergency_input_invalid");
}
