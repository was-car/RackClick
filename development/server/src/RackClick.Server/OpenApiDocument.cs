namespace RackClick.Server;

// Foundation contract is deliberately explicit: no undocumented inventory or
// administration endpoints are advertised before they exist.
public static partial class OpenApiDocument
{
    private static Dictionary<string, object?> Obj(params (string Key, object? Value)[] values)
        => values.ToDictionary(v => v.Key, v => v.Value);
    private static object Ref(string name) => Obj(("$ref", $"#/components/schemas/{name}"));
    private static object Text(string? format = null) => format is null
        ? Obj(("type", "string")) : Obj(("type", "string"), ("format", format));
    private static object ArrayOf(object items) => Obj(("type", "array"), ("items", items));
    private static object Shape(string[] required, params (string Key, object? Value)[] properties)
        => Obj(("type", "object"), ("required", required), ("properties", Obj(properties)));
    private static object Body(string schema) => Obj(("required", true),
        ("description", "JSON request body, maximum 16384 bytes (16 KiB); enforced by Kestrel and the request boundary."),
        ("content", Obj(("application/json", Obj(("schema", Ref(schema)))))));
    private static object Header(string name, string description, object? schema = null)
        => Obj(("in", "header"), ("name", name), ("required", true),
            ("description", description), ("schema", schema ?? Text()));
    private static object Response(string description, object? schema = null, bool etag = false)
    {
        var value = Obj(("description", description));
        if (schema is not null) value["content"] = Obj(("application/json", Obj(("schema", schema))));
        if (etag) value["headers"] = Obj(("ETag", Obj(("schema", Text()), ("description", "Quoted positive revision, e.g. \"1\"."))));
        return value;
    }

    private static object Operation(string id, string description, string status, object? response,
        string? request = null, bool authenticated = true, bool mutation = false,
        bool revision = false, bool customer = false, bool etag = false, bool login = false)
    {
        var parameters = new List<object>();
        if (mutation || login) parameters.Add(Header("Origin", "Must equal the configured same-origin public URL."));
        if (mutation) parameters.Add(Header("X-RackClick-CSRF", "Token supplied by login or me, bound to the current session."));
        if (revision)
        {
            parameters.Add(Header("If-Match", "Systemhaus revision for Systemhaus rename/customer create; customer revision for customer rename. Required even for replay."));
            parameters.Add(Header("Idempotency-Key", "Nonempty UUID retained for retries with the same action, normalized body and original revision.", Text("uuid")));
            parameters.Add(Obj(("in", "header"), ("name", "X-RackClick-Actor"), ("required", false),
                ("description", "Original actor UUID; the GUI always sends it to keep retries bound to their initial user. A changed session actor returns 409 actor_changed."),
                ("schema", Text("uuid"))));
        }
        if (customer) parameters.Add(Obj(("in", "path"), ("name", "id"), ("required", true), ("schema", Text("uuid"))));
        var responses = Obj((status, Response(status == "204" ? "Session revoked." : "Confirmed result; mutation returns only after commit.", response, etag)),
            ("400", Response("Malformed request, host or HTTPS requirements.", Ref("Error"))),
            ("403", Response("Origin/CSRF invalid, or capability absent on a visible resource.", Ref("Error"))),
            ("503", Response("Service unavailable; no success is claimed.", Ref("Error"))));
        if (authenticated || login) responses["401"] = Response("Authentication required or login failed.", Ref("Error"));
        if (login) responses["429"] = Response("Login IP rate limit reached.", Ref("Error"));
        if (request is not null)
        {
            responses["413"] = Response("Request body exceeds 16384 bytes (16 KiB).", Ref("Error"));
            responses["415"] = Response("Request Content-Type is not supported JSON.", Ref("Error"));
        }
        if (revision)
        {
            responses["404"] = Response("Resource absent or outside visible scope.", Ref("Error"));
            responses["409"] = Response("Idempotency key reused for a different request, or X-RackClick-Actor no longer matches the session.", Ref("Error"));
            responses["412"] = Response("Revision conflict; keep the draft.", Ref("Error"));
            responses["422"] = Response("Invalid name, revision, request UUID or actor UUID.", Ref("Error"));
            responses["428"] = Response("If-Match revision required.", Ref("Error"));
        }
        var operation = Obj(("operationId", id), ("description", description), ("responses", responses),
            ("security", authenticated ? new object[] { Obj(("sessionCookie", System.Array.Empty<string>())) } : System.Array.Empty<object>()));
        if (parameters.Count != 0) operation["parameters"] = parameters;
        if (request is not null) operation["requestBody"] = Body(request);
        return operation;
    }

    public static object Create()
    {
        object uuid = Text("uuid"), text = Text();
        object revision = Obj(("type", "integer"), ("format", "int64"), ("minimum", 1));
        var schemas = Obj(
            ("Error", Shape(["error"], ("error", text), ("traceId", text))),
            ("LoginRequest", Shape(["username", "password"],
                ("username", Obj(("type", "string"), ("description", "Trimmed, valid Unicode, 1–100 scalar values, no control characters; invariant lowercase identity. No NFC normalization."))),
                ("password", Obj(("type", "string"), ("writeOnly", true), ("description", "Unmodified; at most 1024 UTF-16 code units."))))),
            ("LoginResponse", Shape(["csrf"], ("csrf", text))),
            ("NameRequest", Shape(["name"], ("name", Obj(("type", "string"),
                ("description", "Trimmed, valid Unicode, 1–100 scalar values, no control characters; user text is not translated."))))),
            ("User", Shape(["id", "houseId", "userName"], ("id", uuid), ("houseId", uuid), ("userName", text))),
            ("House", Shape(["id", "name", "revision"], ("id", uuid), ("name", text), ("revision", revision))),
            ("Customer", Shape(["id", "houseId", "name", "revision"], ("id", uuid), ("houseId", uuid), ("name", text), ("revision", revision))),
            ("PermissionSource", Shape(["userGroupId", "userGroupName", "capability", "scopeType", "scopeId"],
                ("userGroupId", uuid), ("userGroupName", text), ("capability", text),
                ("scopeType", Obj(("type", "string"), ("enum", new[] { "systemhaus", "customer", "customerGroup" }))),
                ("scopeId", Obj(("type", "string"), ("format", "uuid"), ("nullable", true))))),
            ("CustomerPermissions", Shape(["customerId", "capabilities"], ("customerId", uuid), ("capabilities", ArrayOf(text)))),
            ("EffectivePermissions", Shape(["systemhausCapabilities", "customers", "sources"],
                ("systemhausCapabilities", ArrayOf(text)), ("customers", ArrayOf(Ref("CustomerPermissions"))),
                ("sources", ArrayOf(Ref("PermissionSource"))))),
            ("MeResponse", Shape(["user", "csrf", "permissions"], ("user", Ref("User")), ("csrf", text), ("permissions", Ref("EffectivePermissions")))),
            ("HouseMutation", Shape(["resource", "systemhausRevision", "requestId"],
                ("resource", Ref("House")), ("systemhausRevision", revision), ("requestId", uuid))),
            ("CustomerMutation", Shape(["resource", "systemhausRevision", "requestId"],
                ("resource", Ref("Customer")), ("systemhausRevision", revision), ("requestId", uuid))),
            ("OpenApi", Obj(("type", "object"), ("description", "This OpenAPI 3.0.3 foundation document."))));
        var paths = Obj(
            ("/api/v1/auth/login", Obj(("post", Operation("login", "Create an eight-hour session. Secure HttpOnly SameSite=Strict cookie; insecure loopback only under explicit development opt-in.",
                "200", Ref("LoginResponse"), "LoginRequest", authenticated: false, login: true)))),
            ("/api/v1/auth/logout", Obj(("post", Operation("logout", "Revoke the current session.", "204", null, mutation: true)))),
            ("/api/v1/me", Obj(("get", Operation("me", "Current identity and fresh effective grants. Customer capabilities include global/direct/customer-group union, restricted to readable customers. Sources describe the caller's own group grants. Server rechecks authorization on every operation.",
                "200", Ref("MeResponse"))))),
            ("/api/v1/openapi.json", Obj(("get", Operation("openapi", "Authenticated foundation API contract.", "200", Ref("OpenApi"))))),
            ("/api/v1/systemhaus", Obj(
                ("get", Operation("readSystemhaus", "Requires global systemhaus.read.", "200", Ref("House"), etag: true)),
                ("put", Operation("renameSystemhaus", "Requires global systemhaus.manage and current Systemhaus revision.", "200", Ref("HouseMutation"), "NameRequest", mutation: true, revision: true)))),
            ("/api/v1/customers", Obj(
                ("get", Operation("readCustomers", "Only customers with inventory.read in the current effective scope.", "200", ArrayOf(Ref("Customer")))),
                ("post", Operation("createCustomer", "Requires global customer.create and current Systemhaus revision. Duplicate names keep separate IDs.", "201", Ref("CustomerMutation"), "NameRequest", mutation: true, revision: true)))),
            ("/api/v1/customers/{id}", Obj(("put", Operation("renameCustomer", "Requires inventory.read and customer.manage for this customer, and its current revision. Foundation writes currently serialize on Systemhaus.",
                "200", Ref("CustomerMutation"), "NameRequest", mutation: true, revision: true, customer: true)))));
        AddInventory(paths, schemas);
        AddInventorySpreadsheetReports(paths, schemas);
        AddRc9ExcelReports(paths, schemas);
        AddInventoryRackSvgReports(paths, schemas);
        AddChanges(paths, schemas);
        AddAdmin(paths, schemas);
        AddUserCatalogFavorites(paths, schemas);
        AddUserPreferences(paths, schemas);
        AddUserPortColors(paths, schemas);
        AddUserCategoryColors(paths, schemas);
        AddPrivateDeviceTemplates(paths, schemas);
        AddSharedDeviceTemplates(paths, schemas);
        return Obj(("openapi", "3.0.3"),
            ("info", Obj(("title", "RackClick Server Foundation"), ("version", "0.1.0-s1"),
                ("description", "Internal S1 contract; incomplete inventory and administration are not advertised. Legacy /login and /logout aliases are not provided."))),
            ("servers", new[] { Obj(("url", "/")) }), ("paths", paths),
            ("components", Obj(("schemas", schemas), ("securitySchemes", Obj(("sessionCookie", Obj(
                ("type", "apiKey"), ("in", "cookie"), ("name", "RackClick.Session"))))))));
    }
}
