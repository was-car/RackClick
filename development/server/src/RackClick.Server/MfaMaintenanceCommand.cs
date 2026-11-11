using System.ComponentModel;
using System.Runtime.InteropServices;
using System.Runtime.Versioning;
using System.Security.Cryptography;
using System.Security.Principal;
using System.Text;
using System.Text.Json;
using Npgsql;

namespace RackClick.Server;

internal static class MfaMaintenanceCommand
{
    public static async Task<int> RunAsync(TextReader input,TextWriter output,CancellationToken ct)
    {
        if(!OperatingSystem.IsWindows())return await Reject(output,"mfa_maintenance_not_windows");
        using var impersonated=WindowsIdentity.GetCurrent(ifImpersonating:true);
        var elevated=impersonated is null && IsElevatedAdministrator();
        SecurityIdentifier[] trusted=[new(WellKnownSidType.LocalSystemSid,null),new(WellKnownSidType.BuiltinAdministratorsSid,null)];
        return await RunAsync(input,output,elevated,trusted,ct);
    }

    [SupportedOSPlatform("windows")]
    internal static async Task<int> RunAsync(TextReader input,TextWriter output,bool elevated,
        IReadOnlyCollection<SecurityIdentifier> trusted,CancellationToken ct)
    {
        if(!elevated)return await Reject(output,"mfa_maintenance_not_elevated");
        using var timeout=CancellationTokenSource.CreateLinkedTokenSource(ct);timeout.CancelAfter(TimeSpan.FromMinutes(3));
        try
        {
            var request=Parse(await Read(input,timeout.Token),trusted);
            var result=await MfaMaintenanceCoordinator.RunAsync(request,trusted,null,timeout.Token);
            await output.WriteLineAsync(JsonSerializer.Serialize(new{status="verified",code=result.Code,operationId=result.OperationId,
                catalogSha256=result.CatalogSha256,retiredVersion=result.RetiredVersion,encryptedMaterialPreserved=result.EncryptedMaterialPreserved}));
            return 0;
        }
        catch(MfaMaintenanceException error){return await Reject(output,error.Code);}
        catch(MfaBackupCatalogException){return await Reject(output,"mfa_backup_catalog_rejected");}
        catch(MfaKeyRingException){return await Reject(output,"mfa_maintenance_store_rejected");}
        catch(MfaKeyRetentionException){return await Reject(output,"mfa_maintenance_dependencies_invalid");}
        catch(NpgsqlException){return await Reject(output,"mfa_maintenance_database_unavailable");}
        catch(Exception error)when(error is IOException or UnauthorizedAccessException or Win32Exception)
        {return await Reject(output,"mfa_maintenance_store_unavailable");}
        catch(CryptographicException){return await Reject(output,"mfa_maintenance_factor_authentication_failed");}
        catch(OperationCanceledException){return await Reject(output,"mfa_maintenance_cancelled");}
    }

    [SupportedOSPlatform("windows")]
    private static MfaMaintenanceRequest Parse(string input,IReadOnlyCollection<SecurityIdentifier> trusted)
    {
        try
        {
            _=new UTF8Encoding(false,true).GetByteCount(input);
            using var document=JsonDocument.Parse(input,new JsonDocumentOptions{MaxDepth=3});
            var root=document.RootElement;if(root.ValueKind!=JsonValueKind.Object)throw Invalid();
            var values=new Dictionary<string,JsonElement>(StringComparer.Ordinal);
            foreach(var field in root.EnumerateObject())
            {
                string name;
                try{name=field.Name;}catch(InvalidOperationException){throw Invalid();}
                if(!values.TryAdd(name,field.Value))throw Invalid();
            }
            string Text(string key)
            {
                if(!values.TryGetValue(key,out var value) || value.ValueKind!=JsonValueKind.String)throw Invalid();
                try{return value.GetString()!;}catch(InvalidOperationException){throw Invalid();}
            }
            Guid Id(string key){var text=Text(key);return Guid.TryParseExact(text,"D",out var id)&&id!=Guid.Empty&&id.ToString("D")==text?id:throw Invalid();}
            string Digest(string key){var value=Text(key);return value.Length==64&&value.All(c=>c is >= '0' and <= '9' or >= 'a' and <= 'f')?value:throw Invalid();}
            var action=Text("action");
            string[] common=["action","ownerConnection","instancesRoot","installationId","readerSid","serviceName"];
            string[] extra=action switch
            {
                "catalog-initialize"=>["catalogBase64","confirmation"],
                "catalog-refresh"=>["catalogBase64","confirmation","expectedCatalogSha256"],
                "check"=>["expectedCatalogSha256"],
                "retire"=>["expectedCatalogSha256","candidate","operationId","confirmation"],
                "resume"=>["expectedCatalogSha256","operationId","confirmation"],
                _=>throw Invalid()
            };
            if(values.Count!=common.Length+extra.Length || common.Concat(extra).Any(k=>!values.ContainsKey(k)))throw Invalid();
            var installation=Id("installationId");var instances=Text("instancesRoot");
            string path;
            try{if(!Path.IsPathFullyQualified(instances))throw Invalid();path=Path.GetFullPath(instances);}
            catch(Exception error)when(error is ArgumentException or NotSupportedException or PathTooLongException){throw Invalid();}
            SecurityIdentifier reader;
            try{reader=new SecurityIdentifier(Text("readerSid"));}catch(ArgumentException){throw Invalid();}
            if(!reader.IsAccountSid() || trusted.Contains(reader))throw Invalid();
            var hash=action=="catalog-initialize"?"":Digest("expectedCatalogSha256");
            byte[]? catalog=null;
            if(action is "catalog-initialize" or "catalog-refresh")
            {
                if(Text("confirmation")!="CONFIRMO CATALOGO "+installation.ToString("D"))throw Invalid();
                var encoded=Text("catalogBase64");if(encoded.Length>1400000)throw Invalid();
                try{catalog=Convert.FromBase64String(encoded);}catch(FormatException){throw Invalid();}
                if(catalog.Length>1024*1024)throw Invalid();
            }
            var operation=action is "retire" or "resume"?Id("operationId"):Guid.Empty;
            var candidate=0;
            if(action=="retire")
            {
                if(values["candidate"].ValueKind!=JsonValueKind.Number || !values["candidate"].TryGetInt32(out candidate) || candidate is <1 or >1000000
                    || Text("confirmation")!="CONFIRMO RETIRADA "+installation.ToString("D")+" v"+candidate.ToString(System.Globalization.CultureInfo.InvariantCulture))throw Invalid();
            }
            if(action=="resume" && Text("confirmation")!="CONFIRMO REANUDAR "+installation.ToString("D")+" "+operation.ToString("D"))throw Invalid();
            var installationFolder=Directory.GetParent(path);
            if(!string.Equals(Path.GetFileName(path),"security",StringComparison.OrdinalIgnoreCase)
                || installationFolder is null || installationFolder.Name!=installation.ToString("D") || installationFolder.Parent is null)throw Invalid();
            try { WindowsMfaMaintenanceService.RequireStopped(Text("serviceName"),reader,installation,installationFolder.Parent.FullName); }
            catch(InvalidOperationException){throw new MfaMaintenanceException("mfa_maintenance_service_rejected");}
            catch(IdentityNotMappedException){throw new MfaMaintenanceException("mfa_maintenance_service_rejected");}
            return new(action,Text("ownerConnection"),path,installation,reader,hash,candidate,operation,catalog);
        }
        catch(JsonException){throw Invalid();}
        catch(EncoderFallbackException){throw Invalid();}
    }

    private static async Task<string> Read(TextReader input,CancellationToken ct)
    {
        var buffer=new char[4096];var text=new StringBuilder();
        while(true)
        {
            var count=await input.ReadAsync(buffer.AsMemory(),ct).AsTask().WaitAsync(ct);
            if(count==0)return text.ToString();
            if(text.Length>2*1024*1024-count)throw Invalid();text.Append(buffer,0,count);
        }
    }
    private static async Task<int> Reject(TextWriter output,string code)
    {await output.WriteLineAsync(JsonSerializer.Serialize(new{status="rejected",code,maintenanceState="inspect_before_retry"}));return 1;}
    private static MfaMaintenanceException Invalid()=>new("mfa_maintenance_input_invalid");

    [SupportedOSPlatform("windows")]
    private static bool IsElevatedAdministrator()
    {
        using var identity=WindowsIdentity.GetCurrent();
        if(!new WindowsPrincipal(identity).IsInRole(WindowsBuiltInRole.Administrator))return false;
        var memory=Marshal.AllocHGlobal(sizeof(int));
        try{return GetTokenInformation(identity.AccessToken.DangerousGetHandle(),20,memory,sizeof(int),out var length)&&length>=sizeof(int)&&Marshal.ReadInt32(memory)!=0;}
        finally{Marshal.FreeHGlobal(memory);}
    }
    [DllImport("advapi32.dll",SetLastError=true)]
    [return:MarshalAs(UnmanagedType.Bool)]
    private static extern bool GetTokenInformation(IntPtr token,int informationClass,IntPtr information,int length,out int returned);
}
