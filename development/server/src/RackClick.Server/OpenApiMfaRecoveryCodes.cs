namespace RackClick.Server;
public static partial class OpenApiDocument
{
    private static void AddMfaRecoveryCodes(Dictionary<string, object?> paths, Dictionary<string, object?> schemas)
    {
        schemas["MfaRecoveryCodesStatus"] = Shape(["userId","remaining","revision","canGenerate","sessionMfaVerified"],
            ("userId",Text("uuid")),("remaining",Obj(("type","integer"),("minimum",0),("maximum",10))),
            ("revision",Obj(("type","integer"),("minimum",1))),("canGenerate",Obj(("type","boolean"))),
            ("sessionMfaVerified",Obj(("type","boolean"))));
        schemas["MfaRecoveryCodesRequest"] = Shape(["password"],("password",Obj(("type","string"),("format","password"),("minLength",1),("maxLength",1024))));
        schemas["MfaRecoveryCodeRequest"] = Shape(["code"],("code",Obj(("type","string"),("minLength",32),("maxLength",39))));
        schemas["MfaRecoveryCodesGeneration"] = Shape(["userId","requestId","remaining","systemhausRevision","codesAvailable","codes"],
            ("userId",Text("uuid")),("requestId",Text("uuid")),("remaining",Obj(("type","integer"),("minimum",0),("maximum",10))),
            ("systemhausRevision",Obj(("type","integer"))),("codesAvailable",Obj(("type","boolean"))),
            ("codes",Obj(("anyOf",new[]{Obj(("type","array"),("items",Text()),("minItems",10),("maxItems",10)),Obj(("type","null"))}))));
        var generate=(Dictionary<string,object?>)Operation("GenerateOwnRecoveryCodes","Own password and MFA-verified session required. Replaces previous codes. Only the first committed response includes values; every receipt/replay omits them.","200",Ref("MfaRecoveryCodesGeneration"),"MfaRecoveryCodesRequest",mutation:true,revision:true);
        foreach(var item in ((List<object>)generate["parameters"]!).OfType<Dictionary<string,object?>>())
            if(item.GetValueOrDefault("name") as string=="X-RackClick-Actor")item["required"]=true;
        ((Dictionary<string,object?>)generate["responses"]!)["429"]=Response("Rate limit reached.",Ref("Error"));
        paths["/api/v1/me/mfa/recovery-codes"]=Obj(("get",Operation("ReadOwnRecoveryCodeStatus","Remaining count only; never returns code values.","200",Ref("MfaRecoveryCodesStatus"),etag:true)),("post",generate));
        var receipt=(Dictionary<string,object?>)Operation("ReadOwnRecoveryCodesReceipt","Original actor only; returns recorded=false or a code-free receipt.","200",Obj(("type","object")));
        receipt["parameters"]=new List<object>{Obj(("in","path"),("name","requestId"),("required",true),("schema",Text("uuid")))};
        paths["/api/v1/me/mfa/recovery-codes/operations/{requestId}"]=Obj(("get",receipt));
        var recover=(Dictionary<string,object?>)Operation("RecoverMfa","After password login, redeem one recovery code using the challenge cookie and challenge CSRF. Revokes old sessions/codes/factor and returns ONLY a new enrollment challenge; confirm a new authenticator before API access.","202",Obj(("type","object")),"MfaRecoveryCodeRequest",authenticated:false,mutation:true,login:true);
        paths["/api/v1/auth/mfa/recover"]=Obj(("post",recover));
    }
}
