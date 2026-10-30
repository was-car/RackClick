namespace RackClick.Server;

public static partial class OpenApiDocument
{
    private static void AddMfaAccounts(Dictionary<string, object?> paths, Dictionary<string, object?> schemas)
    {
        schemas["MfaAccountStatus"] = Shape(
            ["userId", "userName", "available", "required", "enrollmentPending", "factorState", "globalPolicyEnabled",
             "graceDays", "deadlineUtc", "daysRemaining", "deadlineReached", "globalAdministratorExempt", "sessionMfaVerified",
             "canEnable", "canDisable", "canReset", "revision", "serverNowUtc"],
            ("userId", Text("uuid")), ("userName", Text()), ("available", Obj(("type", "boolean"))),
            ("required", Obj(("type", "boolean"))), ("enrollmentPending", Obj(("type", "boolean"))),
            ("factorState", Obj(("type", "string"), ("enum", new[] { "none", "pending", "active", "disabled" }))),
            ("globalPolicyEnabled", Obj(("type", "boolean"))),
            ("graceDays", Obj(("type", new[] { "integer", "null" }))),
            ("deadlineUtc", Obj(("type", new[] { "string", "null" }), ("format", "date-time"))),
            ("daysRemaining", Obj(("type", new[] { "integer", "null" }), ("minimum", 0))),
            ("deadlineReached", Obj(("type", "boolean"))), ("globalAdministratorExempt", Obj(("type", "boolean"))),
            ("sessionMfaVerified", Obj(("type", "boolean"))), ("canEnable", Obj(("type", "boolean"))),
            ("canDisable", Obj(("type", "boolean"))), ("canReset", Obj(("type", "boolean"))),
            ("revision", Obj(("type", "integer"), ("minimum", 1))), ("serverNowUtc", Text("date-time")));
        schemas["MfaAccountChangeRequest"] = Shape([], ("password", Text()));
        schemas["MfaAccountReceipt"] = Shape(["userId", "action", "requestId", "systemhausRevision", "signInRequired", "resource"],
            ("userId", Text("uuid")), ("action", Text()), ("requestId", Text("uuid")),
            ("systemhausRevision", Obj(("type", "integer"))), ("signInRequired", Obj(("type", "boolean"))), ("resource", Ref("MfaAccountStatus")));
        schemas["MfaAccountOperationStatus"] = Shape(["state", "requestId", "operation"],
            ("state", Obj(("type", "string"), ("enum", new[] { "committed", "notRecorded" }))),
            ("requestId", Text("uuid")), ("operation", Obj(("anyOf", new[] { Ref("MfaAccountReceipt"), Obj(("type", "null")) }))));

        foreach (var prefix in new[] { "/api/v1/me/mfa", "/api/v1/admin/users/{userId}/mfa" })
        {
            bool admin = prefix.Contains("/admin/", StringComparison.Ordinal);
            string scope = admin ? "AdminUser" : "Own";
            paths[prefix] = Obj(("get", MfaOperation(scope + "MfaStatus",
                admin ? "Requires global security.manage; no seeds are returned." : "Own security state and remaining grace, computed with the PostgreSQL clock.",
                Ref("MfaAccountStatus"), admin: admin, etag: true)));
            foreach (string action in new[] { "enable", "disable", "reset" })
                paths[prefix + "/" + action] = Obj(("post", MfaOperation(scope + "Mfa" + action,
                    "Commit and audit MFA change atomically. " + (admin ? "Requires security.manage and completed MFA; own account uses the self route."
                        : "Requires current password and completed MFA when an active factor exists. Ends the account's sessions; sign in again.")
                    + " Disable cannot extend the 45-day grace. Only global Systemhaus administrators can disable their own MFA after the deadline.",
                    Ref("MfaAccountReceipt"), admin: admin, mutation: true)));
            paths[prefix + "/operations/{requestId}"] = Obj(("get", MfaOperation(scope + "MfaOperation",
                "Read the original actor's committed result after reauthentication. notRecorded does not prove cancellation.",
                Ref("MfaAccountOperationStatus"), admin: admin, receipt: true)));
        }
    }

    private static object MfaOperation(string id, string description, object response, bool admin, bool mutation = false,
        bool etag = false, bool receipt = false)
    {
        var value = (Dictionary<string, object?>)Operation(id, description, "200", response,
            mutation ? "MfaAccountChangeRequest" : null, mutation: mutation, revision: mutation, etag: etag);
        var parameters = value.TryGetValue("parameters", out var existing) ? (List<object>)existing! : [];
        value["parameters"] = parameters;
        foreach (var parameter in parameters.OfType<Dictionary<string, object?>>())
            if (parameter.TryGetValue("name", out var name) && name as string == "X-RackClick-Actor") parameter["required"] = true;
        if (admin) parameters.Add(Obj(("in", "path"), ("name", "userId"), ("required", true), ("schema", Text("uuid"))));
        if (receipt) parameters.Add(Obj(("in", "path"), ("name", "requestId"), ("required", true), ("schema", Text("uuid"))));
        if (mutation) ((Dictionary<string, object?>)value["responses"]!)["429"] = Response("Authentication operation rate limit reached.", Ref("Error"));
        return value;
    }
}
