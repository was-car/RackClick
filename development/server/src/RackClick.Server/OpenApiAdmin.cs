namespace RackClick.Server;

public static partial class OpenApiDocument
{
    private static void AddAdmin(Dictionary<string, object?> paths, Dictionary<string, object?> schemas)
    {
        AddAudit(paths, schemas);
        var integer = Obj(("type", "integer"));
        schemas["AdminUser"] = Shape(["id", "userName", "active"], ("id", Text("uuid")), ("userName", Text()), ("active", Obj(("type", "boolean"))));
        schemas["AdminEffectivePermissionsSnapshot"] = Shape(["revision", "user", "permissions"], ("revision", integer), ("user", Ref("AdminUser")), ("permissions", Ref("EffectivePermissions")));
        var effectiveGet = (Dictionary<string, object?>)Operation("readUserEffectivePermissions", "Current GLOBAL security.manage required before target lookup. Own Systemhaus only. One read-only snapshot, same projection as me for active users; inactive users have three empty permission lists. Sources are declared group grants; customer rows require inventory.read. Not authorization for future operations.", "200", Ref("AdminEffectivePermissionsSnapshot"), etag: true);
        effectiveGet["parameters"] = new object[] { Obj(("in", "path"), ("name", "userId"), ("required", true), ("schema", Text("uuid"))) };
        var effectiveResponses = (Dictionary<string, object?>)effectiveGet["responses"]!;
        effectiveResponses["404"] = Response("User absent or outside the administrator's Systemhaus.", Ref("Error"));
        effectiveResponses["422"] = Response("Empty user UUID.", Ref("Error"));
        paths["/api/v1/admin/users/{userId}/effective-permissions"] = Obj(("get", effectiveGet));
        schemas["AdminUserSession"] = Shape(["id", "expiresAt", "current"], ("id", Text("uuid")), ("expiresAt", Text("date-time")), ("current", Obj(("type", "boolean"))));
        schemas["AdminUserSessions"] = Shape(["revision", "user", "sessions"], ("revision", integer), ("user", Ref("AdminUser")), ("sessions", ArrayOf(Ref("AdminUserSession"))));
        var sessionsGet = (Dictionary<string, object?>)Operation("listUserSessions", "Current global security.manage required. Own Systemhaus, active target and unexpired sessions only. Public opaque IDs never authenticate; no token, cookie, CSRF, IP or browser fields. Read-only snapshot, not a promise of future session validity.", "200", Ref("AdminUserSessions"), etag: true);
        sessionsGet["parameters"] = new object[] { Obj(("in", "path"), ("name", "userId"), ("required", true), ("schema", Text("uuid"))) };
        paths["/api/v1/admin/users/{userId}/sessions"] = Obj(("get", sessionsGet));
        schemas["RevokeUserSession"] = Obj(("type", "object"), ("required", Array.Empty<string>()), ("properties", Obj()), ("additionalProperties", false));
        schemas["UserSessionRevokedResource"] = Shape(["userId", "sessionId", "revoked", "wasCurrent"], ("userId", Text("uuid")), ("sessionId", Text("uuid")), ("revoked", Obj(("type", "boolean"))), ("wasCurrent", Obj(("type", "boolean"))));
        schemas["UserSessionRevoked"] = Shape(["resource", "systemhausRevision", "requestId"], ("resource", Ref("UserSessionRevokedResource")), ("systemhausRevision", integer), ("requestId", Text("uuid")));
        schemas["UserSessionRevocationStatus"] = Shape(["requestId", "state", "operation"], ("requestId", Text("uuid")), ("state", Obj(("type", "string"), ("enum", new[] { "committed", "notRecorded", "cancelled" }))), ("operation", Obj(("nullable", true), ("allOf", new[] { Ref("UserSessionRevoked") }))));
        const string revokePath = "/api/v1/admin/users/{userId}/sessions/{sessionId}/revoke";
        foreach (bool fence in new[] { false, true })
        {
            var post = (Dictionary<string, object?>)Operation(fence ? "cancelUserSessionRevocation" : "revokeUserSession", "Current GLOBAL security.manage required. Strict empty body. Exact public session/user IDs in own Systemhaus. Revokes only selected row, including current or expired session; preserves other/new logins and account. wasCurrent is historical from original execution. Replay never deletes again. Cancellation accepts stale revision/absent targets and does not revoke. Recover own revocation using NEW login of SAME actor and GET original intent. notRecorded is not cancellation.", "200", Ref(fence ? "UserSessionRevocationStatus" : "UserSessionRevoked"), "RevokeUserSession", mutation: true, revision: true);
            var revokeParameters = (List<object>)post["parameters"]!;
            foreach (var parameter in revokeParameters)
                if (parameter is Dictionary<string, object?> header)
                {
                    if (header["name"] as string == "If-Match") header["description"] = "Original Systemhaus revision, including replay and cancellation; cancellation accepts stale revision.";
                    if (header["name"] as string == "X-RackClick-Actor") header["required"] = true;
                }
            revokeParameters.Add(Obj(("in", "path"), ("name", "userId"), ("required", true), ("schema", Text("uuid"))));
            revokeParameters.Add(Obj(("in", "path"), ("name", "sessionId"), ("required", true), ("schema", Text("uuid"))));
            if (fence) revokeParameters.Add(Obj(("in", "path"), ("name", "requestId"), ("required", true), ("schema", Text("uuid"))));
            paths[revokePath + (fence ? "/operations/{requestId}/cancel" : "")] = Obj(("post", post));
        }
        var revokeStatus = (Dictionary<string, object?>)Operation("userSessionRevocationStatus", "Current GLOBAL security.manage required. Own original actor/Systemhaus/action/userId/sessionId only. Retrieves original public result without target lookup. wasCurrent remains historical. notRecorded never proves cancellation.", "200", Ref("UserSessionRevocationStatus"));
        revokeStatus["parameters"] = new object[] { Obj(("in", "path"), ("name", "userId"), ("required", true), ("schema", Text("uuid"))), Obj(("in", "path"), ("name", "sessionId"), ("required", true), ("schema", Text("uuid"))), Obj(("in", "path"), ("name", "requestId"), ("required", true), ("schema", Text("uuid"))) };
        paths[revokePath + "/operations/{requestId}"] = Obj(("get", revokeStatus));
        schemas["AdminUsers"] = Shape(["revision", "users"], ("revision", integer), ("users", ArrayOf(Ref("AdminUser"))));
        schemas["AdminGroupTarget"] = Shape(["id", "name"], ("id", Text("uuid")), ("name", Text()));
        schemas["AdminGroupGrant"] = Shape(["id", "capability", "scope", "target"], ("id", Text("uuid")), ("capability", Text()),
            ("scope", Obj(("type", "string"), ("enum", new[] { "systemhaus", "customer", "customerGroup" }))),
            ("target", Obj(("nullable", true), ("allOf", new[] { Ref("AdminGroupTarget") }))));
        schemas["AdminUserGroup"] = Shape(["id", "name", "members", "grants"], ("id", Text("uuid")), ("name", Text()),
            ("members", ArrayOf(Ref("AdminUser"))), ("grants", ArrayOf(Ref("AdminGroupGrant"))));
        schemas["AdminCustomerGroup"] = Shape(["id", "name", "customers"], ("id", Text("uuid")), ("name", Text()), ("customers", ArrayOf(Ref("AdminGroupTarget"))));
        schemas["AdminUserGroups"] = Shape(["revision", "groups"], ("revision", integer), ("groups", ArrayOf(Ref("AdminUserGroup"))));
        schemas["AdminCustomerGroups"] = Shape(["revision", "groups"], ("revision", integer), ("groups", ArrayOf(Ref("AdminCustomerGroup"))));
        paths["/api/v1/admin/user-groups"] = Obj(("get", Operation("listUserGroups", "Current global security.manage required. Group memberships and declared grants; not effective permissions of each account.", "200", Ref("AdminUserGroups"))));
        paths["/api/v1/admin/customer-groups"] = Obj(("get", Operation("listCustomerGroups", "Current global security.manage required. Customer group memberships scoped to this Systemhaus.", "200", Ref("AdminCustomerGroups"))));
        schemas["CreateAdminGroup"] = Shape(["name"], ("name", Text()));
        schemas["AdminGroupCreatedResource"] = Shape(["id", "name", "kind"], ("id", Text("uuid")), ("name", Text()),
            ("kind", Obj(("type", "string"), ("enum", new[] { "userGroup", "customerGroup" }))));
        schemas["AdminGroupCreated"] = Shape(["resource", "systemhausRevision", "requestId"], ("resource", Ref("AdminGroupCreatedResource")), ("systemhausRevision", integer), ("requestId", Text("uuid")));
        schemas["AdminGroupCreationStatus"] = Shape(["requestId", "state", "operation"], ("requestId", Text("uuid")),
            ("state", Obj(("type", "string"), ("enum", new[] { "committed", "notRecorded", "cancelled" }))),
            ("operation", Obj(("nullable", true), ("allOf", new[] { Ref("AdminGroupCreated") }))));
        schemas["SetGroupMember"] = Shape(["userId", "assigned"], ("userId", Text("uuid")), ("assigned", Obj(("type", "boolean"))));
        schemas["GroupMemberResource"] = Shape(["groupId", "userId", "assigned"], ("groupId", Text("uuid")), ("userId", Text("uuid")), ("assigned", Obj(("type", "boolean"))));
        schemas["GroupMemberChanged"] = Shape(["resource", "systemhausRevision", "requestId"], ("resource", Ref("GroupMemberResource")), ("systemhausRevision", integer), ("requestId", Text("uuid")));
        schemas["GroupMemberStatus"] = Shape(["requestId", "state", "operation"], ("requestId", Text("uuid")), ("state", Obj(("type", "string"), ("enum", new[] { "committed", "notRecorded", "cancelled" }))), ("operation", Obj(("nullable", true), ("allOf", new[] { Ref("GroupMemberChanged") }))));
        const string memberPath = "/api/v1/admin/user-groups/{groupId}/members";
        foreach (bool cancelling in new[] { false, true })
        {
            var memberPost = (Dictionary<string, object?>)Operation(cancelling ? "cancelGroupMemberChange" : "setGroupMember",
                cancelling ? "Original actor/key/group/user/assigned/revision. Stale revision and absent targets accepted; returns existing commit or durable cancellation. Never undoes membership."
                : "Current global security.manage required. Targets in own Systemhaus. Auditable revision increment even for no-op; active last global administrator protected. Permissions apply immediately to existing sessions.",
                "200", Ref(cancelling ? "GroupMemberStatus" : "GroupMemberChanged"), "SetGroupMember", mutation: true, revision: true);
            var memberHeaders = (List<object>)memberPost["parameters"]!;
            foreach (var p in memberHeaders)
                if (p is Dictionary<string, object?> h && h["name"] as string == "X-RackClick-Actor") h["required"] = true;
            memberHeaders.Add(Obj(("in", "path"), ("name", "groupId"), ("required", true), ("schema", Text("uuid"))));
            if (cancelling) memberHeaders.Add(Obj(("in", "path"), ("name", "requestId"), ("required", true), ("schema", Text("uuid"))));
            paths[memberPath + (cancelling ? "/operations/{requestId}/cancel" : "")] = Obj(("post", memberPost));
        }
        var memberGet = (Dictionary<string, object?>)Operation("groupMemberChangeStatus", "Own actor and route group only, current global security.manage required; notRecorded is not a cancellation fence.", "200", Ref("GroupMemberStatus"));
        memberGet["parameters"] = new object[] { Obj(("in", "path"), ("name", "groupId"), ("required", true), ("schema", Text("uuid"))), Obj(("in", "path"), ("name", "requestId"), ("required", true), ("schema", Text("uuid"))) };
        paths[memberPath + "/operations/{requestId}"] = Obj(("get", memberGet));
        schemas["AdminCapabilities"] = Shape(["revision", "capabilities"], ("revision", integer), ("capabilities", ArrayOf(Text())));
        paths["/api/v1/admin/capabilities"] = Obj(("get", Operation("listAdminCapabilities", "Current global security.manage required. Foundation capability catalog; scoped capabilities never grant global access.", "200", Ref("AdminCapabilities"))));
        var grantScope = Obj(("type", "string"), ("enum", new[] { "systemhaus", "customer", "customerGroup" }));
        var grantCapability = Obj(("type", "string"), ("enum", RackClick.Domain.Capabilities.FoundationAdmin));
        var grantTarget = Obj(("type", "string"), ("format", "uuid"), ("nullable", true));
        schemas["SetGrant"] = Shape(["grantId", "capability", "scope", "assigned"], ("grantId", Text("uuid")), ("capability", grantCapability), ("scope", grantScope), ("targetId", grantTarget), ("assigned", Obj(("type", "boolean"))));
        schemas["GrantResource"] = Shape(["groupId", "grantId", "capability", "scope", "targetId", "assigned"], ("groupId", Text("uuid")), ("grantId", Text("uuid")), ("capability", grantCapability), ("scope", grantScope), ("targetId", grantTarget), ("assigned", Obj(("type", "boolean"))));
        schemas["GrantChanged"] = Shape(["resource", "systemhausRevision", "requestId"], ("resource", Ref("GrantResource")), ("systemhausRevision", integer), ("requestId", Text("uuid")));
        schemas["GrantStatus"] = Shape(["requestId", "state", "operation"], ("requestId", Text("uuid")), ("state", Obj(("type", "string"), ("enum", new[] { "committed", "notRecorded", "cancelled" }))), ("operation", Obj(("nullable", true), ("allOf", new[] { Ref("GrantChanged") }))));
        const string grantPath = "/api/v1/admin/user-groups/{groupId}/grants";
        foreach (bool cancelling in new[] { false, true })
        {
            var grantPost = (Dictionary<string, object?>)Operation(cancelling ? "cancelGrantChange" : "setGrant",
                cancelling ? "Original actor/key/group/grant/capability/scope/target/assigned/revision; stale revision and absent targets allowed. Durable fence never changes a grant."
                : "Current global security.manage required, reevaluated after lock. Immutable grant ID/intent. Duplicate tuple conflicts. Systemhaus targetId must be null; other scopes require own nonempty UUID. No-op auditable revision increment; active last global administrator protected. Confirms only after commit.",
                "200", Ref(cancelling ? "GrantStatus" : "GrantChanged"), "SetGrant", mutation: true, revision: true);
            var grantHeaders = (List<object>)grantPost["parameters"]!;
            foreach (var p in grantHeaders)
                if (p is Dictionary<string, object?> h && h["name"] as string == "X-RackClick-Actor") h["required"] = true;
            grantHeaders.Add(Obj(("in", "path"), ("name", "groupId"), ("required", true), ("schema", Text("uuid"))));
            if (cancelling) grantHeaders.Add(Obj(("in", "path"), ("name", "requestId"), ("required", true), ("schema", Text("uuid"))));
            paths[grantPath + (cancelling ? "/operations/{requestId}/cancel" : "")] = Obj(("post", grantPost));
        }
        var grantGet = (Dictionary<string, object?>)Operation("grantChangeStatus", "Own actor and group only, current global security.manage required. notRecorded is not a fence.", "200", Ref("GrantStatus"));
        grantGet["parameters"] = new object[] { Obj(("in", "path"), ("name", "groupId"), ("required", true), ("schema", Text("uuid"))), Obj(("in", "path"), ("name", "requestId"), ("required", true), ("schema", Text("uuid"))) };
        paths[grantPath + "/operations/{requestId}"] = Obj(("get", grantGet));
        schemas["AdminCustomers"] = Shape(["revision", "customers"], ("revision", integer), ("customers", ArrayOf(Ref("AdminGroupTarget"))));
        paths["/api/v1/admin/customers"] = Obj(("get", Operation("listAdminCustomers", "Current global security.manage required. Own Systemhaus customer IDs and names only, without granting inventory access.", "200", Ref("AdminCustomers"))));
        schemas["SetCustomerGroupMember"] = Shape(["customerId", "assigned"], ("customerId", Text("uuid")), ("assigned", Obj(("type", "boolean"))));
        schemas["CustomerGroupMemberResource"] = Shape(["groupId", "customerId", "assigned"], ("groupId", Text("uuid")), ("customerId", Text("uuid")), ("assigned", Obj(("type", "boolean"))));
        schemas["CustomerGroupMemberChanged"] = Shape(["resource", "systemhausRevision", "requestId"], ("resource", Ref("CustomerGroupMemberResource")), ("systemhausRevision", integer), ("requestId", Text("uuid")));
        schemas["CustomerGroupMemberStatus"] = Shape(["requestId", "state", "operation"], ("requestId", Text("uuid")), ("state", Obj(("type", "string"), ("enum", new[] { "committed", "notRecorded", "cancelled" }))), ("operation", Obj(("nullable", true), ("allOf", new[] { Ref("CustomerGroupMemberChanged") }))));
        const string customerMemberPath = "/api/v1/admin/customer-groups/{groupId}/members";
        foreach (bool cancelling in new[] { false, true })
        {
            var customerMemberPost = (Dictionary<string, object?>)Operation(cancelling ? "cancelCustomerGroupMemberChange" : "setCustomerGroupMember",
                cancelling ? "Original actor/key/group/customer/assigned/revision. Stale revision and absent targets accepted; returns existing commit or durable cancellation. Never undoes membership."
                : "Current global security.manage required. Targets in own Systemhaus. Auditable revision increment even for no-op; Does not change users, grants, inventory or customer revisions. Permissions apply immediately to existing sessions.",
                "200", Ref(cancelling ? "CustomerGroupMemberStatus" : "CustomerGroupMemberChanged"), "SetCustomerGroupMember", mutation: true, revision: true);
            var customerMemberHeaders = (List<object>)customerMemberPost["parameters"]!;
            foreach (var p in customerMemberHeaders)
                if (p is Dictionary<string, object?> h && h["name"] as string == "X-RackClick-Actor") h["required"] = true;
            customerMemberHeaders.Add(Obj(("in", "path"), ("name", "groupId"), ("required", true), ("schema", Text("uuid"))));
            if (cancelling) customerMemberHeaders.Add(Obj(("in", "path"), ("name", "requestId"), ("required", true), ("schema", Text("uuid"))));
            paths[customerMemberPath + (cancelling ? "/operations/{requestId}/cancel" : "")] = Obj(("post", customerMemberPost));
        }
        var customerMemberGet = (Dictionary<string, object?>)Operation("customerGroupMemberChangeStatus", "Own actor and route group only, current global security.manage required; notRecorded is not a cancellation fence.", "200", Ref("CustomerGroupMemberStatus"));
        customerMemberGet["parameters"] = new object[] { Obj(("in", "path"), ("name", "groupId"), ("required", true), ("schema", Text("uuid"))), Obj(("in", "path"), ("name", "requestId"), ("required", true), ("schema", Text("uuid"))) };
        paths[customerMemberPath + "/operations/{requestId}"] = Obj(("get", customerMemberGet));
        foreach (string kind in new[] { "user", "customer" })
        {
            string groupPath = "/api/v1/admin/" + kind + "-groups";
            var post = (Dictionary<string, object?>)Operation("create" + kind + "Group", "Global security.manage, original actor/key and Systemhaus revision required. Creates an empty group without implicit members or grants; confirms only after commit.", "201", Ref("AdminGroupCreated"), "CreateAdminGroup", mutation: true, revision: true);
            foreach (var p in (List<object>)post["parameters"]!)
                if (p is Dictionary<string, object?> h && h["name"] as string == "X-RackClick-Actor") h["required"] = true;
            ((Dictionary<string, object?>)paths[groupPath]!)["post"] = post;
            var get = (Dictionary<string, object?>)Operation(kind + "GroupCreationStatus", "Own actor and group kind only. Current global security.manage required. notRecorded never proves cancellation.", "200", Ref("AdminGroupCreationStatus"));
            get["parameters"] = new object[] { Obj(("in", "path"), ("name", "requestId"), ("required", true), ("schema", Text("uuid"))) };
            paths[groupPath + "/operations/{requestId}"] = Obj(("get", get));
            var groupCancel = (Dictionary<string, object?>)Operation("cancel" + kind + "GroupCreation", "Original actor/key/name/revision; stale revision accepted. Returns prior commit or durably reserves cancellation. Never deletes a group.", "200", Ref("AdminGroupCreationStatus"), "CreateAdminGroup", mutation: true, revision: true);
            var headers = (List<object>)groupCancel["parameters"]!;
            foreach (var p in headers)
                if (p is Dictionary<string, object?> h && h["name"] as string == "X-RackClick-Actor") h["required"] = true;
            headers.Add(Obj(("in", "path"), ("name", "requestId"), ("required", true), ("schema", Text("uuid"))));
            paths[groupPath + "/operations/{requestId}/cancel"] = Obj(("post", groupCancel));
        }
        schemas["SetUserState"] = Shape(["active"], ("active", Obj(("type", "boolean"))));
        schemas["UserStateChanged"] = Shape(["resource", "systemhausRevision", "requestId"], ("resource", Ref("AdminUser")), ("systemhausRevision", integer), ("requestId", Text("uuid")));
        schemas["UserStateStatus"] = Shape(["requestId", "state", "operation"], ("requestId", Text("uuid")), ("state", Obj(("type", "string"), ("enum", new[] { "committed", "notRecorded", "cancelled" }))), ("operation", Obj(("nullable", true), ("allOf", new[] { Ref("UserStateChanged") }))));
        foreach (bool fence in new[] { false, true })
        {
            var statePost = (Dictionary<string, object?>)Operation(fence ? "cancelUserState" : "setUserState", "Current global security.manage required. Original actor/key/active/revision. Disabling atomically revokes sessions and protects last active global administrator. Activation never restores old sessions. Cancellation accepts stale revision and absent target; notRecorded is not cancellation.", "200", Ref(fence ? "UserStateStatus" : "UserStateChanged"), "SetUserState", mutation: true, revision: true);
            var stateParameters = (List<object>)statePost["parameters"]!;
            foreach (var parameter in stateParameters)
                if (parameter is Dictionary<string, object?> h && h["name"] as string == "X-RackClick-Actor") h["required"] = true;
            stateParameters.Add(Obj(("in", "path"), ("name", "userId"), ("required", true), ("schema", Text("uuid"))));
            if (fence) stateParameters.Add(Obj(("in", "path"), ("name", "requestId"), ("required", true), ("schema", Text("uuid"))));
            paths["/api/v1/admin/users/{userId}/state" + (fence ? "/operations/{requestId}/cancel" : "")] = Obj(("post", statePost));
        }
        var stateStatus = (Dictionary<string, object?>)Operation("userStateStatus", "Own actor/target/Systemhaus/action only; current global security.manage required. notRecorded never proves cancellation.", "200", Ref("UserStateStatus"));
        stateStatus["parameters"] = new object[] { Obj(("in", "path"), ("name", "userId"), ("required", true), ("schema", Text("uuid"))), Obj(("in", "path"), ("name", "requestId"), ("required", true), ("schema", Text("uuid"))) };
        paths["/api/v1/admin/users/{userId}/state/operations/{requestId}"] = Obj(("get", stateStatus));
        schemas["ResetUserPassword"] = Shape(["password"], ("password", Obj(("type", "string"), ("x-rackclick-min-utf16-length", 16), ("x-rackclick-max-utf16-length", 1024), ("writeOnly", true), ("description", "16-1024 UTF-16 code units; no trimming or normalization."))));
        schemas["CancelUserPasswordReset"] = Shape([]);
        schemas["UserPasswordResource"] = Shape(["id", "userName", "active", "passwordReset"], ("id", Text("uuid")), ("userName", Text()), ("active", Obj(("type", "boolean"))), ("passwordReset", Obj(("type", "boolean"))));
        schemas["UserPasswordChanged"] = Shape(["resource", "systemhausRevision", "requestId"], ("resource", Ref("UserPasswordResource")), ("systemhausRevision", integer), ("requestId", Text("uuid")));
        schemas["UserPasswordStatus"] = Shape(["requestId", "state", "operation"], ("requestId", Text("uuid")), ("state", Obj(("type", "string"), ("enum", new[] { "committed", "notRecorded", "cancelled" }))), ("operation", Obj(("nullable", true), ("allOf", new[] { Ref("UserPasswordChanged") }))));
        foreach (bool fence in new[] { false, true })
        {
            var passwordPost = (Dictionary<string, object?>)Operation(fence ? "cancelUserPasswordReset" : "resetUserPassword", "Current global security.manage required. Reset atomically changes salted hash, clears login lockout and revokes ALL target sessions, including own session. Active/group/permissions unchanged. Replay verifies CURRENT password; a later different reset makes old-password replay conflict. GET recovers old commit without password. Cancellation uses public intent only, accepts stale revision/absent target and never resets; notRecorded is not cancellation. No password or verifier is audited or returned.", "200", Ref(fence ? "UserPasswordStatus" : "UserPasswordChanged"), fence ? "CancelUserPasswordReset" : "ResetUserPassword", mutation: true, revision: true);
            var passwordParameters = (List<object>)passwordPost["parameters"]!;
            foreach (var parameter in passwordParameters)
                if (parameter is Dictionary<string, object?> h && h["name"] as string == "X-RackClick-Actor") h["required"] = true;
            passwordParameters.Add(Obj(("in", "path"), ("name", "userId"), ("required", true), ("schema", Text("uuid"))));
            if (fence) passwordParameters.Add(Obj(("in", "path"), ("name", "requestId"), ("required", true), ("schema", Text("uuid"))));
            paths["/api/v1/admin/users/{userId}/password" + (fence ? "/operations/{requestId}/cancel" : "")] = Obj(("post", passwordPost));
        }
        var passwordStatus = (Dictionary<string, object?>)Operation("userPasswordStatus", "Own actor/target/Systemhaus/action only; current global security.manage required. Retrieves old commit even after another reset. No password. notRecorded never proves cancellation.", "200", Ref("UserPasswordStatus"));
        passwordStatus["parameters"] = new object[] { Obj(("in", "path"), ("name", "userId"), ("required", true), ("schema", Text("uuid"))), Obj(("in", "path"), ("name", "requestId"), ("required", true), ("schema", Text("uuid"))) };
        paths["/api/v1/admin/users/{userId}/password/operations/{requestId}"] = Obj(("get", passwordStatus));
        schemas["CreateUser"] = Shape(["username", "password"], ("username", Text()), ("password", Obj(("type", "string"), ("x-rackclick-min-utf16-length", 16), ("x-rackclick-max-utf16-length", 1024), ("writeOnly", true), ("description", "16-1024 UTF-16 code units; no trimming or normalization."))));
        schemas["CancelUserCreation"] = Shape(["username"], ("username", Text()));
        schemas["UserCreated"] = Shape(["resource", "systemhausRevision", "requestId"], ("resource", Ref("AdminUser")), ("systemhausRevision", integer), ("requestId", Text("uuid")));
        schemas["UserCreationStatus"] = Shape(["requestId", "state", "operation"], ("requestId", Text("uuid")), ("state", Obj(("type", "string"), ("enum", new[] { "committed", "notRecorded", "cancelled" }))), ("operation", Obj(("nullable", true), ("allOf", new[] { Ref("UserCreated") }))));
        var create = (Dictionary<string, object?>)Operation("createUser", "Systemhaus security.manage required. Creates active account without group memberships. Password never returned or audited. Same request/revision/name/password replays; changed password conflicts. No cancellation inferred from notRecorded.", "201", Ref("UserCreated"), "CreateUser", mutation: true, revision: true);
        // Unlike the historical foundation routes, administration requires the original actor header.
        foreach (var p in (List<object>)create["parameters"]!)
            if (p is Dictionary<string, object?> header && header.TryGetValue("name", out var name) && name as string == "X-RackClick-Actor") header["required"] = true;
        paths["/api/v1/admin/users"] = Obj(("get", Operation("listUsers", "Systemhaus security.manage required. Safe public fields only; ETag is the Systemhaus revision.", "200", Ref("AdminUsers"), etag: true)), ("post", create));
        var status = (Dictionary<string, object?>)Operation("userCreationStatus", "Own actor and Systemhaus only, current security.manage required. notRecorded is not a cancellation fence.", "200", Ref("UserCreationStatus"));
        status["parameters"] = new object[] { Obj(("in", "path"), ("name", "requestId"), ("required", true), ("schema", Text("uuid"))) };
        paths["/api/v1/admin/users/operations/{requestId}"] = Obj(("get", status));
        var cancel = (Dictionary<string, object?>)Operation("cancelUserCreation", "Current global security.manage required. Original actor/key/username/revision; no password. Stale original revision accepted. Returns committed if creation won, otherwise durably cancelled. No account is deleted.", "200", Ref("UserCreationStatus"), "CancelUserCreation", mutation: true, revision: true);
        var parameters = (List<object>)cancel["parameters"]!;
        foreach (var p in parameters)
            if (p is Dictionary<string, object?> header && header.TryGetValue("name", out var name) && name as string == "X-RackClick-Actor") header["required"] = true;
        parameters.Add(Obj(("in", "path"), ("name", "requestId"), ("required", true), ("schema", Text("uuid"))));
        paths["/api/v1/admin/users/operations/{requestId}/cancel"] = Obj(("post", cancel));
    }
}
