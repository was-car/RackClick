using System.Diagnostics;
using System.Net;
using System.Net.Http.Json;
using System.Runtime.Versioning;
using System.Security.AccessControl;
using System.Security.Cryptography;
using System.Security.Principal;
using System.Text;
using System.Text.Json;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.AspNetCore.TestHost;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;
using Npgsql;
using RackClick.Domain;
using RackClick.Server;
using Xunit;

namespace RackClick.Quality.Tests;

[CollectionDefinition("MfaPortableDatabaseRestore", DisableParallelization = true)]
public sealed class MfaPortableDatabaseRestoreCollection;

// Real PG17 custom dump/restore, Windows DPAPI/file recovery and normal Program middleware/endpoints.
// HTTP is TestServer in memory. The only Windows seam is the explicit LAB identity, not a provider stub.
// The coordinator supplies a NEW isolated cluster. Databases/roles/artifacts remain for review; no global cleanup.
[Collection("MfaPortableDatabaseRestore")]
[SupportedOSPlatform("windows")]
public sealed class MfaPortableDatabaseRestoreTests(MfaPortableDatabaseRestoreTests.PortableFixture fixture)
    : IClassFixture<MfaPortableDatabaseRestoreTests.PortableFixture>
{
    [Fact]
    public async Task CustomDumpRestoresTheCompleteSchemaInventoryAndRestrictedRuntimeIdentity()
    {
        Assert.Equal(45L, await fixture.Count(fixture.Target.OwnerConnection, "SELECT count(*) FROM schema_migration"));
        Assert.Equal(1L, await fixture.Count(fixture.Target.OwnerConnection, "SELECT count(*) FROM customer"));
        Assert.Equal(1L, await fixture.Count(fixture.Target.OwnerConnection, "SELECT count(*) FROM inventory_rack"));
        Assert.Equal(2L, await fixture.Count(fixture.Target.OwnerConnection, "SELECT count(*) FROM app_mfa_factor WHERE state='active'"));
        Assert.True(await fixture.Boolean(fixture.Target.RuntimeConnection, """
            SELECT NOT rolsuper AND NOT rolcreatedb AND NOT rolcreaterole AND NOT rolbypassrls
                AND current_user<>pg_get_userbyid(d.datdba)
                AND NOT has_schema_privilege(current_user,'public','CREATE')
                AND NOT has_database_privilege(current_user,current_database(),'CREATE,TEMP')
            FROM pg_roles r CROSS JOIN pg_database d WHERE r.rolname=current_user AND d.datname=current_database()
            """));
        var denied = await Assert.ThrowsAsync<PostgresException>(() => fixture.Execute(fixture.Target.RuntimeConnection,
            "CREATE TABLE public.f0505_must_be_denied(id integer)"));
        Assert.Equal(PostgresErrorCodes.InsufficientPrivilege, denied.SqlState);
        foreach (var table in PortableFixture.CatalogueTables)
        {
            Assert.True(await fixture.Boolean(fixture.Target.RuntimeConnection,
                "SELECT has_table_privilege(current_user,@table,'SELECT') AND NOT has_table_privilege(current_user,@table,'INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')",
                ("table", "public." + table)), "global catalogue is not read-only");
        }
        await fixture.AssertFactorCiphertextsPreserved();
        await fixture.AssertSourceUnchanged();
        fixture.Record("custom_restore_schema45_inventory_runtime_restricted");
    }

    [Fact]
    public async Task RestoredBackupSessionsAndChallengesCannotAuthorizeRequests()
    {
        foreach (var user in fixture.Users)
        {
            Assert.Equal(0L, await fixture.Count(fixture.Target.OwnerConnection,
                "SELECT count(*) FROM app_session WHERE token_hash=@token", ("token", Secrets.Digest(user.OldSession))));
            Assert.Equal(1L, await fixture.Count(fixture.Target.OwnerConnection,
                "SELECT count(*) FROM app_mfa_challenge WHERE token_hash=@token AND consumed_at IS NOT NULL",
                ("token", Secrets.Digest(user.OldChallenge))));
            Assert.Equal(HttpStatusCode.Unauthorized, (await fixture.Get("/api/v1/me", "RackClick.Session=" + user.OldSession)).StatusCode);
        }
        var before = await fixture.Count(fixture.Target.OwnerConnection, "SELECT count(*) FROM app_session");
        var prior = fixture.Users[0];
        var rejected = await fixture.Post("/api/v1/auth/mfa/verify", new { code = MfaTotp.Compute(prior.Secret, DateTimeOffset.UtcNow) },
            "RackClick.MfaChallenge=" + prior.OldChallenge, Secrets.Csrf(prior.OldChallenge));
        Assert.Equal(HttpStatusCode.Unauthorized, rejected.StatusCode);
        Assert.False(HasSession(rejected));
        Assert.Equal(before, await fixture.Count(fixture.Target.OwnerConnection, "SELECT count(*) FROM app_session"));
        Assert.Equal("2", await fixture.Text(fixture.Target.OwnerConnection,
            "SELECT after_json->>'revokedChallenges' FROM audit_event WHERE action='deployment.recover'"));
        await fixture.AssertSourceUnchanged();
        fixture.Record("backup_authorities_revoked_by_recovery_administrator");
    }

    [Theory]
    [InlineData(1)]
    [InlineData(7)]
    public async Task EachPreservedFactorCompletesPasswordChallengeTotpSessionAndCsrf(int version)
    {
        var user = fixture.Users.Single(u => u.Version == version);
        var caseNumber = version == 1 ? 11 : 17;
        var before = await fixture.Count(fixture.Target.OwnerConnection, "SELECT count(*) FROM app_session");
        var login = await fixture.Post("/api/v1/auth/login", new { username = user.Name, password = fixture.AppPassword }, caseNumber: caseNumber);
        Assert.Equal(HttpStatusCode.Accepted, login.StatusCode);
        Assert.False(HasSession(login));
        Assert.Equal(before, await fixture.Count(fixture.Target.OwnerConnection, "SELECT count(*) FROM app_session"));
        var body = await login.Content.ReadFromJsonAsync<JsonElement>(TestContext.Current.CancellationToken);
        var challenge = Cookie(login, "RackClick.MfaChallenge");
        Assert.Equal(HttpStatusCode.Unauthorized, (await fixture.Get("/api/v1/me", challenge)).StatusCode);
        var acceptedCode = MfaTotp.Compute(user.Secret, DateTimeOffset.UtcNow);
        var verify = await fixture.Post("/api/v1/auth/mfa/verify", new { code = acceptedCode },
            challenge, body.GetProperty("csrf").GetString(), caseNumber);
        Assert.Equal(HttpStatusCode.OK, verify.StatusCode);
        var session = Cookie(verify, "RackClick.Session");
        var csrf = (await verify.Content.ReadFromJsonAsync<JsonElement>(TestContext.Current.CancellationToken)).GetProperty("csrf").GetString();
        var me = await fixture.Get("/api/v1/me", session);
        Assert.Equal(HttpStatusCode.OK, me.StatusCode);
        var meBody = await me.Content.ReadFromJsonAsync<JsonElement>(TestContext.Current.CancellationToken);
        Assert.True(meBody.GetProperty("user").GetProperty("id").GetGuid() == user.Id, "restored user identity changed");
        Assert.Equal(HttpStatusCode.OK, (await fixture.Get("/api/v1/customers", session)).StatusCode);
        Assert.Equal(HttpStatusCode.Forbidden, (await fixture.Post("/api/v1/auth/logout", null, session, "not-the-session-csrf")).StatusCode);
        Assert.Equal(HttpStatusCode.NoContent, (await fixture.Post("/api/v1/auth/logout", null, session, csrf)).StatusCode);
        Assert.Equal(HttpStatusCode.Unauthorized, (await fixture.Get("/api/v1/me", session)).StatusCode);
        var sessionsBeforeReplay = await fixture.Count(fixture.Target.OwnerConnection, "SELECT count(*) FROM app_session");
        var nextLogin = await fixture.Post("/api/v1/auth/login", new { username = user.Name, password = fixture.AppPassword }, caseNumber: caseNumber);
        Assert.Equal(HttpStatusCode.Accepted, nextLogin.StatusCode);
        var nextBody = await nextLogin.Content.ReadFromJsonAsync<JsonElement>(TestContext.Current.CancellationToken);
        var repeated = await fixture.Post("/api/v1/auth/mfa/verify", new { code = acceptedCode }, Cookie(nextLogin, "RackClick.MfaChallenge"), nextBody.GetProperty("csrf").GetString(), caseNumber);
        Assert.Equal(HttpStatusCode.Unauthorized, repeated.StatusCode);
        Assert.False(HasSession(repeated));
        Assert.Equal(sessionsBeforeReplay, await fixture.Count(fixture.Target.OwnerConnection, "SELECT count(*) FROM app_session"));
        await fixture.AssertFactorCiphertextsPreserved();
        await fixture.AssertSourceUnchanged();
        fixture.Record("restored_factor_http_version_" + version);
    }

    [Fact]
    public async Task WrongTotpNeverEmitsASession()
    {
        var user = fixture.Users[1];
        var before = await fixture.Count(fixture.Target.OwnerConnection, "SELECT count(*) FROM app_session");
        var login = await fixture.Post("/api/v1/auth/login", new { username = user.Name, password = fixture.AppPassword });
        Assert.Equal(HttpStatusCode.Accepted, login.StatusCode);
        var body = await login.Content.ReadFromJsonAsync<JsonElement>(TestContext.Current.CancellationToken);
        var valid = Enumerable.Range(-1, 3).Select(offset => MfaTotp.Compute(user.Secret, DateTimeOffset.UtcNow.AddSeconds(offset * 30))).ToHashSet();
        var wrong = Enumerable.Range(0, 100).Select(n => n.ToString("D6")).First(code => !valid.Contains(code));
        var response = await fixture.Post("/api/v1/auth/mfa/verify", new { code = wrong }, Cookie(login, "RackClick.MfaChallenge"), body.GetProperty("csrf").GetString());
        Assert.Equal(HttpStatusCode.Unauthorized, response.StatusCode);
        Assert.False(HasSession(response));
        Assert.Equal(before, await fixture.Count(fixture.Target.OwnerConnection, "SELECT count(*) FROM app_session"));
        await fixture.AssertSourceUnchanged();
        fixture.Record("wrong_totp_no_session");
    }

    [Fact]
    public async Task WrongEnvelopePasswordRejectsBeforePublishingAStoreOrBuildingAHost()
    {
        var candidate = fixture.NewCandidate();
        await Assert.ThrowsAsync<MfaRecoveryEnvelopeException>(() => fixture.PrepareCandidate(fixture.Target,
            fixture.Envelope, fixture.EnvelopePassword + "-wrong", candidate.Root, candidate.Id));
        Assert.False(Directory.Exists(candidate.Root));
        await fixture.AssertSourceUnchanged();
        fixture.Record("wrong_envelope_password_before_store_and_host");
    }

    [Fact]
    public async Task EnvelopeWithoutTheRetiredVersionCannotEnableAHostForItsDatabase()
    {
        var candidate = fixture.NewCandidate();
        var rejected = await Assert.ThrowsAsync<InvalidOperationException>(() => fixture.PrepareCandidate(fixture.Target,
            fixture.IncompleteEnvelope, fixture.EnvelopePassword, candidate.Root, candidate.Id));
        Assert.Equal("required_factor_version_missing", rejected.Message);
        Assert.False(Directory.Exists(candidate.Root));
        await fixture.AssertSourceUnchanged();
        fixture.Record("missing_retired_material_before_store_and_host");
    }

    [Fact]
    public async Task AFactorWithInvalidUserAadRejectsBeforePublishingAStoreOrBuildingAHost()
    {
        var destination = await fixture.RestoreNewDatabase();
        // Corrupt only our additional restored database: copy the second user's valid ciphertext under the first user's ID.
        await fixture.Execute(destination.OwnerConnection,
            "UPDATE app_mfa_factor SET secret_ciphertext=@cipher,key_version=7 WHERE user_id=@user",
            ("cipher", fixture.Users[1].Ciphertext), ("user", fixture.Users[0].Id));
        var candidate = fixture.NewCandidate();
        await Assert.ThrowsAnyAsync<CryptographicException>(() => fixture.PrepareCandidate(destination,
            fixture.Envelope, fixture.EnvelopePassword, candidate.Root, candidate.Id));
        Assert.False(Directory.Exists(candidate.Root));
        await fixture.AssertSourceUnchanged();
        fixture.Record("invalid_factor_aad_before_store_and_host");
    }

    private static bool HasSession(HttpResponseMessage response) => response.Headers.TryGetValues("Set-Cookie", out var values)
        && values.Any(value => value.StartsWith("RackClick.Session=", StringComparison.Ordinal));

    private static string Cookie(HttpResponseMessage response, string name) => response.Headers.GetValues("Set-Cookie")
        .Single(value => value.StartsWith(name + "=", StringComparison.Ordinal)).Split(';')[0];

    [SupportedOSPlatform("windows")]
    public sealed class PortableFixture : IAsyncLifetime
    {
        private const string Origin = "https://rackclick.test";
        private const string ContentRootVariable = "ASPNETCORE_TEST_CONTENTROOT_RACKCLICK_SERVER";
        public static readonly string[] CatalogueTables = ["hardware_definition", "hardware_mount_slot", "hardware_group_template", "hardware_passthrough", "hardware_connector_template", "hardware_profile_extension", "hardware_group_extension"];
        private static readonly SecurityIdentifier Reader = new(WellKnownSidType.BuiltinUsersSid, null);
        private static readonly SecurityIdentifier System = new(WellKnownSidType.LocalSystemSid, null);
        private static readonly SecurityIdentifier Admin = new(WellKnownSidType.BuiltinAdministratorsSid, null);
        private readonly SecurityIdentifier me = WindowsIdentity.GetCurrent().User ?? throw new InvalidOperationException("lab_identity_missing");
        private readonly Guid sourceInstallation = Guid.NewGuid();
        private readonly Guid systemhaus = Guid.NewGuid();
        private readonly Dictionary<int, byte[]> materials = new();
        private readonly List<string> passed = [];
        private readonly List<Database> databases = [];
        private string adminConnection = "", pgBin = "", root = "", sourceRoot = "", sourceFingerprint = "";
        private string[] sourceFiles = [];
        private Database source = null!;
        private WebApplicationFactory<Program>? factory;
        private HttpClient? client;
        private string? previousConnection, previousOrigin, previousContentRoot;
        private bool environmentCaptured;
        private string recoveredRoot = "";
        private Guid recoveredInstallation;
        private string stage = "entry";
        private string failureType = "none", failureSqlState = "none";
        private object[] failureChain = [];
        private SecurityIdentifier[] Trust => [me, System, Admin];
        public User[] Users { get; private set; } = [];
        public Database Target { get; private set; } = null!;
        public string AppPassword { get; } = RandomText();
        public string EnvelopePassword { get; } = RandomText();
        public string Envelope => Path.Combine(root, "envelopes", "complete.rckey");
        public string IncompleteEnvelope => Path.Combine(root, "envelopes", "missing-retired.rckey");
        private string Dump => Path.Combine(root, "database", "data.dump");

        public async ValueTask InitializeAsync()
        {
            Assert.SkipUnless(OperatingSystem.IsWindows(), "Windows DPAPI required");
            var rawAdmin = Environment.GetEnvironmentVariable("RACKCLICK_TEST_PG_ADMIN");
            var rawBin = Environment.GetEnvironmentVariable("RACKCLICK_TEST_PG_BIN");
            var rawRoot = Environment.GetEnvironmentVariable("RACKCLICK_TEST_F0505_ROOT");
            Assert.SkipWhen(string.IsNullOrEmpty(rawAdmin) || string.IsNullOrEmpty(rawBin) || string.IsNullOrEmpty(rawRoot), "isolated F0505 PG environment required");
            try
            {
                stage = "private_fixture";
                adminConnection = new NpgsqlConnectionStringBuilder(rawAdmin) { IncludeErrorDetail = false, Pooling = false }.ConnectionString;
                var settings = new NpgsqlConnectionStringBuilder(adminConnection);
                Assert.True(settings.Host is "127.0.0.1" or "localhost", "only an isolated loopback cluster is allowed");
                pgBin = Path.GetFullPath(rawBin!);
                Assert.True(File.Exists(Path.Combine(pgBin, "pg_dump.exe")) && File.Exists(Path.Combine(pgBin, "pg_restore.exe")), "PG binaries missing");
                var baseRoot = Path.GetFullPath(rawRoot!);
                Assert.True(baseRoot.StartsWith(@"C:\RackClick_SVR\.local\f0505-integration-", StringComparison.OrdinalIgnoreCase) && Directory.Exists(baseRoot), "private root invalid");
                root = Path.Combine(baseRoot, "fixture-" + Guid.NewGuid().ToString("N"));
                // Operational test-path limit observed on this Windows host, not a new product path policy.
                var projectedStagingKey = Path.Combine(root, "c-" + new string('0', 32), Guid.Empty.ToString("D"), "mfa-keys.preparando-" + new string('0', 32), "key-v7.dpapi.json");
                Assert.True(projectedStagingKey.Length < 260, "fixture_path_too_long");
                NewFolder(root); NewFolder(Path.Combine(root, "database")); NewFolder(Path.Combine(root, "envelopes"), Reader);
                Assert.Equal(17L, (await Count(adminConnection, "SHOW server_version_num")) / 10000);
                stage = "source_schema45";
                source = await NewDatabase();
                await using (var db = new NpgsqlConnection(source.OwnerConnection))
                {
                    await db.OpenAsync(); await using var tx = await db.BeginTransactionAsync();
                    await SchemaMigrations.Apply(db, tx, CancellationToken.None); await tx.CommitAsync();
                }
                stage = "source_synthetic_data";
                await SeedSource();
                sourceRoot = Path.Combine(root, "source-keys");
                CreateSourceStore(sourceRoot, includeRetired: true);
                WindowsMfaKeyRecoveryFiles.ExportToFile(sourceRoot, sourceInstallation, Reader, Reader, Trust,
                    EnvelopePassword, Path.GetDirectoryName(Envelope)!, Path.GetFileName(Envelope));
                var incomplete = Path.Combine(root, "incomplete-source-keys");
                CreateSourceStore(incomplete, includeRetired: false);
                WindowsMfaKeyRecoveryFiles.ExportToFile(incomplete, sourceInstallation, Reader, Reader, Trust,
                    EnvelopePassword, Path.GetDirectoryName(IncompleteEnvelope)!, Path.GetFileName(IncompleteEnvelope));
                sourceFingerprint = await DatabaseFingerprint(source.OwnerConnection);
                sourceFiles = FileSnapshot(sourceRoot).Concat(FileSnapshot(incomplete)).Concat(FileSnapshot(Path.Combine(root, "envelopes"))).ToArray();
                stage = "pg_dump_custom";
                await RunPg("pg_dump.exe", source.OwnerConnection, "--format=custom", "--no-owner", "--no-acl", "--file", Dump);
                Assert.True(File.ReadAllBytes(Dump).AsSpan(0, 5).SequenceEqual("PGDMP"u8), "custom dump signature missing");
                stage = "pg_restore_new_database";
                Target = await RestoreNewDatabase();
                Assert.Equal(sourceFingerprint, await DatabaseFingerprint(Target.OwnerConnection));
                stage = "recovery_administrator";
                var dumpHash = Hash(File.ReadAllBytes(Dump));
                await Execute(Target.OwnerConnection, $"COMMENT ON DATABASE {Target.Name} IS 'RackClickRecoveryPending:{Target.Id:D}:{dumpHash}'");
                var config = new ConfigurationBuilder().AddInMemoryCollection(new Dictionary<string, string?>
                {
                    ["ConnectionStrings:RackClick"] = Target.OwnerConnection, ["Recovery:ExpectedDatabase"] = Target.Name,
                    ["Recovery:BackupSha256"] = dumpHash, ["Recovery:User"] = "portable-recovery-admin",
                }).Build();
                var output = new StringWriter();
                Assert.Equal(0, await RecoveryAdministrator.Run(config, new StringReader(RandomText() + "\n"), output, CancellationToken.None));
                Assert.Equal(0L, await Count(Target.OwnerConnection, "SELECT count(*) FROM app_session"));
                Assert.Equal(0L, await Count(Target.OwnerConnection, "SELECT count(*) FROM app_mfa_challenge WHERE consumed_at IS NULL"));
                stage = "portable_recovery";
                (recoveredRoot, recoveredInstallation) = NewCandidate();
                await PrepareCandidate(Target, Envelope, EnvelopePassword, recoveredRoot, recoveredInstallation);
                stage = "ready_for_tests";
                await AssertSourceUnchanged();
                WriteReport();
            }
            catch (Exception error)
            {
                failureType = error.GetType().Name;
                failureSqlState = error is PostgresException pg ? pg.SqlState : "none";
                var chain = new List<object>();
                for (Exception? node = error; node is not null; node = node.InnerException)
                    chain.Add(new { type = node.GetType().Name, hresult = node.HResult,
                        win32 = node is System.ComponentModel.Win32Exception native ? native.NativeErrorCode : 0,
                        kind = node switch { WindowsMfaKeyRecoveryFileException e => e.Kind.ToString(), WindowsMfaKeyRecoveryException e => e.Kind.ToString(), MfaKeyStoreCreationException e => e.Kind.ToString(), MfaKeyRingException e => e.Kind.ToString(), _ => "none" } });
                failureChain = chain.ToArray();
                WriteReport();
                throw new InvalidOperationException("f0505_fixture_failed_" + stage);
            }
        }

        private async Task SeedSource()
        {
            await Execute(source.OwnerConnection, "INSERT INTO systemhaus(id,name) VALUES(@id,'Portable integration laboratory')", ("id", systemhaus));
            var customer = Guid.NewGuid(); var site = Guid.NewGuid(); var building = Guid.NewGuid(); var room = Guid.NewGuid();
            await Execute(source.OwnerConnection, "INSERT INTO customer(id,systemhaus_id,name) VALUES(@id,@sh,'Portable synthetic customer')", ("id", customer), ("sh", systemhaus));
            await Execute(source.OwnerConnection, "INSERT INTO inventory_site(id,systemhaus_id,customer_id,name) VALUES(@id,@sh,@customer,'Site')", ("id", site), ("sh", systemhaus), ("customer", customer));
            await Execute(source.OwnerConnection, "INSERT INTO inventory_building(id,systemhaus_id,customer_id,site_id,name) VALUES(@id,@sh,@customer,@parent,'Building')", ("id", building), ("sh", systemhaus), ("customer", customer), ("parent", site));
            await Execute(source.OwnerConnection, "INSERT INTO inventory_room(id,systemhaus_id,customer_id,building_id,name) VALUES(@id,@sh,@customer,@parent,'Room')", ("id", room), ("sh", systemhaus), ("customer", customer), ("parent", building));
            await Execute(source.OwnerConnection, "INSERT INTO inventory_rack(id,systemhaus_id,customer_id,room_id,name,size_u) VALUES(@id,@sh,@customer,@parent,'Rack',12)", ("id", Guid.NewGuid()), ("sh", systemhaus), ("customer", customer), ("parent", room));
            var group = Guid.NewGuid();
            await Execute(source.OwnerConnection, "INSERT INTO user_group(id,systemhaus_id,name) VALUES(@id,@sh,'Portable readers')", ("id", group), ("sh", systemhaus));
            foreach (var capability in new[] { Capabilities.HouseRead, Capabilities.InventoryRead })
                await Execute(source.OwnerConnection, "INSERT INTO permission_grant(id,systemhaus_id,user_group_id,capability) VALUES(@id,@sh,@group,@cap)", ("id", Guid.NewGuid()), ("sh", systemhaus), ("group", group), ("cap", capability));
            var users = new List<User>();
            foreach (var version in new[] { 1, 7 })
            {
                var key = RandomNumberGenerator.GetBytes(32); materials.Add(version, key);
                var id = Guid.NewGuid(); var secret = RandomNumberGenerator.GetBytes(20); var name = "portable-user-" + version;
                var cipher = MfaSecretCipher.Seal(key, version, secret, systemhaus, id);
                var user = new User(id, name, version, secret, cipher, Secrets.Token(), Secrets.Token()); users.Add(user);
                await Execute(source.OwnerConnection, "INSERT INTO app_user(id,systemhaus_id,username,password_hash) VALUES(@id,@sh,@name,@hash)", ("id", id), ("sh", systemhaus), ("name", name), ("hash", Secrets.PasswordHash(name, AppPassword)));
                await Execute(source.OwnerConnection, "INSERT INTO user_group_member(systemhaus_id,user_id,group_id) VALUES(@sh,@user,@group)", ("sh", systemhaus), ("user", id), ("group", group));
                await Execute(source.OwnerConnection, "INSERT INTO app_mfa_user(systemhaus_id,user_id,mfa_required) VALUES(@sh,@user,true)", ("sh", systemhaus), ("user", id));
                await Execute(source.OwnerConnection, "INSERT INTO app_mfa_factor(systemhaus_id,user_id,state,secret_ciphertext,key_version,confirmed_at) VALUES(@sh,@user,'active',@cipher,@version,now())", ("sh", systemhaus), ("user", id), ("cipher", cipher), ("version", version));
                await Execute(source.OwnerConnection, "INSERT INTO app_session(token_hash,user_id,csrf_hash,expires_at,mfa_verified_at) VALUES(@token,@user,@csrf,now()+interval '8 hours',now())", ("token", Secrets.Digest(user.OldSession)), ("user", id), ("csrf", Secrets.Digest(Secrets.Csrf(user.OldSession))));
                await Execute(source.OwnerConnection, "INSERT INTO app_mfa_challenge(token_hash,systemhaus_id,user_id,purpose,csrf_hash,expires_at) VALUES(@token,@sh,@user,'verify',@csrf,now()+interval '4 minutes')", ("token", Secrets.Digest(user.OldChallenge)), ("sh", systemhaus), ("user", id), ("csrf", Secrets.Digest(Secrets.Csrf(user.OldChallenge))));
            }
            Users = users.ToArray();
        }

        private void CreateSourceStore(string storeRoot, bool includeRetired)
        {
            var versions = includeRetired ? new[] { 1, 7 } : [7];
            var ring = JsonSerializer.SerializeToUtf8Bytes(new { format = MfaKeyRing.RingFormat, formatVersion = 1, installationId = sourceInstallation,
                versions = versions.Select(version => new { version, state = version == 7 ? "active" : "retired", createdAtUtc = "2026-11-01T00:00:00Z" }) });
            WindowsMfaKeyStoreWriter.CreateStoreFromMaterial(storeRoot, sourceInstallation, Reader, Trust, ring,
                versions.Select(version => (Version: version, Key: materials[version])).ToArray());
        }

        public (string Root, Guid Id) NewCandidate() => (Path.Combine(root, "c-" + Guid.NewGuid().ToString("N")), Guid.NewGuid());

        // Test-only supervision. This is not a new product fence/operator: it checks DB factors before creating its in-memory host.
        public async Task PrepareCandidate(Database database, string envelope, string password, string targetRoot, Guid installation)
        {
            var reader = new WindowsMfaKeyFileReader(Reader, Trust.Select(sid => sid.Value).ToHashSet(StringComparer.Ordinal));
            var sealedBytes = reader.ReadValidated(envelope, MfaKeyRecoveryEnvelope.MaxEnvelopeBytes);
            var plain = MfaKeyRecoveryEnvelope.Open(password, sealedBytes);
            try
            {
                using var content = MfaKeyRecoveryPayload.Deserialize(plain, sourceInstallation);
                foreach (var factor in await Factors(database.OwnerConnection))
                {
                    if (!content.Ring.Entries.Any(entry => entry.Version == factor.Version)) throw new InvalidOperationException("required_factor_version_missing");
                    byte[]? opened = null;
                    var key = content.KeyFor(factor.Version).ToArray();
                    try
                    {
                        opened = MfaSecretCipher.Open(key, factor.Version, factor.Ciphertext, factor.Systemhaus, factor.User);
                        Assert.True(CryptographicOperations.FixedTimeEquals(opened, Users.Single(user => user.Id == factor.User).Secret), "factor material mismatch");
                    }
                    finally { CryptographicOperations.ZeroMemory(key); if (opened is not null) CryptographicOperations.ZeroMemory(opened); }
                }
            }
            finally { CryptographicOperations.ZeroMemory(plain); }
            WindowsMfaKeyRecoveryFiles.RecoverFromFile(envelope, password, sourceInstallation, targetRoot, installation, Reader, Reader, Trust, adaptDestinationInstallation: true);
            var provider = new WindowsMfaKeyProvider(targetRoot, installation, Reader, Trust);
            foreach (var factor in await Factors(database.OwnerConnection))
            {
                var key = provider.GetKey(factor.Version); byte[]? opened = null;
                try
                {
                    opened = MfaSecretCipher.Open(key, factor.Version, factor.Ciphertext, factor.Systemhaus, factor.User);
                    Assert.True(CryptographicOperations.FixedTimeEquals(opened, Users.Single(user => user.Id == factor.User).Secret), "recovered factor material mismatch");
                }
                finally { CryptographicOperations.ZeroMemory(key); if (opened is not null) CryptographicOperations.ZeroMemory(opened); }
            }
        }

        private HttpClient Client()
        {
            if (client is not null) return client;
            previousConnection = Environment.GetEnvironmentVariable("ConnectionStrings__RackClick"); previousOrigin = Environment.GetEnvironmentVariable("PublicOrigin"); environmentCaptured = true;
            previousContentRoot = Environment.GetEnvironmentVariable(ContentRootVariable);
            Assert.True(Directory.Exists(AppContext.BaseDirectory) && File.Exists(Path.Combine(AppContext.BaseDirectory, "RackClick.Server.deps.json")), "test content root/deps missing");
            // Official WebApplicationFactory setting is read before SetContentRoot's manifest/solution fallback.
            // The SDK generates an empty manifest for a reference-only private project; no solution or working-directory inference.
            Environment.SetEnvironmentVariable(ContentRootVariable, AppContext.BaseDirectory);
            Environment.SetEnvironmentVariable("ConnectionStrings__RackClick", Target.RuntimeConnection);
            Environment.SetEnvironmentVariable("PublicOrigin", Origin);
            factory = new WebApplicationFactory<Program>().WithWebHostBuilder(builder =>
            {
                builder.UseSetting("MfaKeyStore:Enabled", "true"); builder.UseSetting("MfaKeyStore:InstancesRoot", recoveredRoot);
                builder.UseSetting("MfaKeyStore:InstallationId", recoveredInstallation.ToString("D"));
                builder.ConfigureLogging(logging => logging.ClearProviders());
                builder.ConfigureTestServices(services =>
                {
                    services.AddSingleton<IMfaHostIdentity>(new LabIdentity(Reader, Trust));
                    services.AddSingleton<IStartupFilter, LabRequestAddress>();
                });
            });
            client = factory.CreateClient(new WebApplicationFactoryClientOptions { BaseAddress = new Uri(Origin), HandleCookies = false });
            Assert.IsType<WindowsMfaKeyProvider>(factory.Services.GetRequiredService<IMfaKeyProvider>());
            return client;
        }

        public async Task<HttpResponseMessage> Post(string path, object? body, string? cookie = null, string? csrf = null, int caseNumber = 1)
        {
            using var request = new HttpRequestMessage(HttpMethod.Post, path) { Content = body is null ? new StringContent("{}", Encoding.UTF8, "application/json") : JsonContent.Create(body) };
            request.Headers.TryAddWithoutValidation("Origin", Origin);
            request.Headers.TryAddWithoutValidation("X-F0505-Lab-Case", caseNumber.ToString());
            if (cookie is not null) request.Headers.TryAddWithoutValidation("Cookie", cookie);
            if (csrf is not null) request.Headers.TryAddWithoutValidation("X-RackClick-CSRF", csrf);
            return await Client().SendAsync(request);
        }
        public async Task<HttpResponseMessage> Get(string path, string cookie)
        {
            using var request = new HttpRequestMessage(HttpMethod.Get, path); request.Headers.TryAddWithoutValidation("Cookie", cookie);
            return await Client().SendAsync(request);
        }

        private async Task<Database> NewDatabase()
        {
            var id = Guid.NewGuid(); var name = "rc_db_" + id.ToString("N"); var owner = "rc_owner_" + id.ToString("N"); var runtime = "rc_run_" + id.ToString("N");
            var ownerPassword = RandomText(); var runtimePassword = RandomText();
            await CreateRole(owner, ownerPassword); await CreateRole(runtime, runtimePassword);
            await Execute(adminConnection, $"CREATE DATABASE {name} OWNER {owner} ENCODING 'UTF8' TEMPLATE template0");
            await Execute(adminConnection, $"REVOKE ALL ON DATABASE {name} FROM PUBLIC; GRANT CONNECT ON DATABASE {name} TO {runtime}");
            var database = new Database(id, name,
                new NpgsqlConnectionStringBuilder(adminConnection) { Database = name, Username = owner, Password = ownerPassword }.ConnectionString,
                new NpgsqlConnectionStringBuilder(adminConnection) { Database = name, Username = runtime, Password = runtimePassword }.ConnectionString, runtime);
            databases.Add(database);
            await Execute(database.OwnerConnection, "REVOKE ALL ON SCHEMA public FROM PUBLIC");
            return database;
        }
        private async Task CreateRole(string role, string password)
        {
            // Both identifiers are internal UUID-based labels; SQL quote construction is delegated to PostgreSQL format().
            var sql = await Text(adminConnection, "SELECT format('CREATE ROLE %I LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS PASSWORD %L',@role,@password)", ("role", role), ("password", password));
            await Execute(adminConnection, sql);
        }
        public async Task<Database> RestoreNewDatabase()
        {
            var database = await NewDatabase();
            await RunPg("pg_restore.exe", database.OwnerConnection, "--single-transaction", "--exit-on-error", "--no-owner", "--no-acl", "--dbname", database.Name, Dump);
            await Execute(database.OwnerConnection, "REVOKE ALL ON SCHEMA public FROM PUBLIC");
            await Execute(database.OwnerConnection, $"GRANT USAGE ON SCHEMA public TO {database.RuntimeRole}; GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public TO {database.RuntimeRole}; GRANT USAGE,SELECT ON ALL SEQUENCES IN SCHEMA public TO {database.RuntimeRole}");
            foreach (var table in CatalogueTables)
                await Execute(database.OwnerConnection, $"REVOKE ALL ON public.{table} FROM {database.RuntimeRole}; GRANT SELECT ON public.{table} TO {database.RuntimeRole}");
            return database;
        }
        private async Task RunPg(string executable, string connectionString, params string[] options)
        {
            var cs = new NpgsqlConnectionStringBuilder(connectionString); var passFile = Path.Combine(root, "pgpass-" + Guid.NewGuid().ToString("N"));
            var security = new FileSecurity(); security.SetOwner(me); security.SetAccessRuleProtection(true, false);
            foreach (var sid in Trust) security.AddAccessRule(new FileSystemAccessRule(sid, FileSystemRights.FullControl, AccessControlType.Allow));
            using (var file = new FileInfo(passFile).Create(FileMode.CreateNew, FileSystemRights.Write, FileShare.Read, 4096, FileOptions.None, security))
            {
                var escaped = string.Join(':', new[] { cs.Host!, cs.Port.ToString(), cs.Database!, cs.Username!, cs.Password! }.Select(value => value.Replace("\\", "\\\\", StringComparison.Ordinal).Replace(":", "\\:", StringComparison.Ordinal))) + "\n";
                file.Write(Encoding.UTF8.GetBytes(escaped)); file.Flush(true);
            }
            try
            {
                var start = new ProcessStartInfo(Path.Combine(pgBin, executable)) { UseShellExecute = false, RedirectStandardOutput = true, RedirectStandardError = true, CreateNoWindow = true };
                foreach (var key in start.Environment.Keys.Where(key => key.StartsWith("PG", StringComparison.OrdinalIgnoreCase) || key.Contains("CONNECTION", StringComparison.OrdinalIgnoreCase) || key.StartsWith("RACKCLICK_", StringComparison.OrdinalIgnoreCase)).ToArray()) start.Environment.Remove(key);
                start.Environment["PGPASSFILE"] = passFile;
                foreach (var arg in new[] { "--host", cs.Host!, "--port", cs.Port.ToString(), "--username", cs.Username!, "--no-password" }) start.ArgumentList.Add(arg);
                if (executable == "pg_dump.exe") { start.ArgumentList.Add("--dbname"); start.ArgumentList.Add(cs.Database!); }
                foreach (var option in options) start.ArgumentList.Add(option);
                using var process = Process.Start(start) ?? throw new InvalidOperationException("pg_process_missing");
                var output = process.StandardOutput.ReadToEndAsync(); var error = process.StandardError.ReadToEndAsync();
                await process.WaitForExitAsync(new CancellationTokenSource(TimeSpan.FromMinutes(2)).Token);
                await output; var stderr = await error;
                Assert.True(process.ExitCode == 0 && stderr.Length == 0, "postgres utility failed or warned");
            }
            finally { File.Delete(passFile); }
        }

        public async Task AssertFactorCiphertextsPreserved()
        {
            foreach (var factor in await Factors(Target.OwnerConnection))
            {
                var user = Users.Single(user => user.Id == factor.User);
                Assert.True(factor.Systemhaus == systemhaus && factor.Version == user.Version && factor.Ciphertext.SequenceEqual(user.Ciphertext), "factor identity/version/ciphertext changed");
            }
        }
        public async Task AssertSourceUnchanged()
        {
            Assert.Equal(sourceFingerprint, await DatabaseFingerprint(source.OwnerConnection));
            var incomplete = Path.Combine(root, "incomplete-source-keys");
            Assert.True(sourceFiles.SequenceEqual(FileSnapshot(sourceRoot).Concat(FileSnapshot(incomplete)).Concat(FileSnapshot(Path.Combine(root, "envelopes")))), "source key/envelope bytes or ACL changed");
        }
        private async Task<string> DatabaseFingerprint(string connection)
        {
            await using var db = new NpgsqlConnection(connection); await db.OpenAsync();
            var names = new List<string>();
            await using (var command = new NpgsqlCommand("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename", db))
            await using (var rows = await command.ExecuteReaderAsync()) while (await rows.ReadAsync()) names.Add(rows.GetString(0));
            using var hash = IncrementalHash.CreateHash(HashAlgorithmName.SHA256);
            foreach (var name in names)
            {
                var quoted = '"' + name.Replace("\"", "\"\"", StringComparison.Ordinal) + '"';
                await using var command = new NpgsqlCommand($"SELECT to_jsonb(t)::text FROM public.{quoted} t ORDER BY to_jsonb(t)::text", db);
                await using var rows = await command.ExecuteReaderAsync(); hash.AppendData(Encoding.UTF8.GetBytes(name + "\n"));
                while (await rows.ReadAsync()) hash.AppendData(Encoding.UTF8.GetBytes(rows.GetString(0) + "\n"));
            }
            return Convert.ToHexString(hash.GetHashAndReset());
        }
        private static string[] FileSnapshot(string path) => Directory.EnumerateFileSystemEntries(path, "*", SearchOption.AllDirectories).Prepend(path).Order(StringComparer.Ordinal).Select(item =>
        {
            FileSystemSecurity security = Directory.Exists(item) ? new DirectoryInfo(item).GetAccessControl() : new FileInfo(item).GetAccessControl();
            return item + "|" + security.GetSecurityDescriptorSddlForm(AccessControlSections.Owner | AccessControlSections.Access) + "|" + (File.Exists(item) ? Hash(File.ReadAllBytes(item)) : "directory");
        }).ToArray();
        private async Task<List<Factor>> Factors(string connection)
        {
            var factors = new List<Factor>(); await using var db = new NpgsqlConnection(connection); await db.OpenAsync();
            await using var cmd = new NpgsqlCommand("SELECT systemhaus_id,user_id,key_version,secret_ciphertext FROM app_mfa_factor ORDER BY key_version", db);
            await using var rows = await cmd.ExecuteReaderAsync();
            while (await rows.ReadAsync()) factors.Add(new Factor(rows.GetGuid(0), rows.GetGuid(1), rows.GetInt32(2), rows.GetFieldValue<byte[]>(3)));
            Assert.Equal(2, factors.Count); return factors;
        }
        public async Task Execute(string connection, string sql, params (string Name, object Value)[] parameters) => await Scalar(connection, sql, parameters);
        public async Task<long> Count(string connection, string sql, params (string Name, object Value)[] parameters) => Convert.ToInt64(await Scalar(connection, sql, parameters));
        public async Task<bool> Boolean(string connection, string sql, params (string Name, object Value)[] parameters) => Convert.ToBoolean(await Scalar(connection, sql, parameters));
        public async Task<string> Text(string connection, string sql, params (string Name, object Value)[] parameters) => Convert.ToString(await Scalar(connection, sql, parameters)) ?? "";
        private static async Task<object?> Scalar(string connection, string sql, params (string Name, object Value)[] parameters)
        {
            await using var db = new NpgsqlConnection(connection); await db.OpenAsync(); await using var command = new NpgsqlCommand(sql, db);
            foreach (var (name, value) in parameters) command.Parameters.AddWithValue(name, value);
            return await command.ExecuteScalarAsync();
        }
        private void NewFolder(string path, SecurityIdentifier? reader = null)
        {
            Assert.False(Directory.Exists(path) || File.Exists(path), "fixture folder already exists");
            var security = new DirectorySecurity(); security.SetOwner(me); security.SetAccessRuleProtection(true, false);
            foreach (var sid in Trust) security.AddAccessRule(new FileSystemAccessRule(sid, FileSystemRights.FullControl, InheritanceFlags.ContainerInherit | InheritanceFlags.ObjectInherit, PropagationFlags.None, AccessControlType.Allow));
            if (reader is not null) security.AddAccessRule(new FileSystemAccessRule(reader, FileSystemRights.ReadAndExecute, InheritanceFlags.ContainerInherit | InheritanceFlags.ObjectInherit, PropagationFlags.None, AccessControlType.Allow));
            new DirectoryInfo(path).Create(security);
        }
        private static string Hash(byte[] bytes) => Convert.ToHexString(SHA256.HashData(bytes)).ToLowerInvariant();
        private static string RandomText() => Convert.ToHexString(RandomNumberGenerator.GetBytes(24)) + "aA1";
        public void Record(string name) { passed.Add(name); WriteReport(); }
        private void WriteReport()
        {
            if (root.Length == 0 || !Directory.Exists(root)) return;
            File.WriteAllText(Path.Combine(root, "summary-sanitized.json"), JsonSerializer.Serialize(new { schemaVersion = 1, stage,
                passed = passed.Order().ToArray(), failureType, failureSqlState, failureChain, testServerInMemory = true, postgresReal = true, windowsDpapiReal = true,
                identitySeam = "explicit_laboratory_only", providerStub = false, databasesPreserved = databases.Count,
                installerTested = false, vmOperated = false, adopted = false }));
        }
        public async ValueTask DisposeAsync()
        {
            try
            {
                if (sourceFingerprint.Length != 0) await AssertSourceUnchanged();
                client?.Dispose(); if (factory is not null) await factory.DisposeAsync();
            }
            finally
            {
                foreach (var key in materials.Values) CryptographicOperations.ZeroMemory(key);
                foreach (var user in Users) CryptographicOperations.ZeroMemory(user.Secret);
                if (environmentCaptured)
                {
                    try { Environment.SetEnvironmentVariable("ConnectionStrings__RackClick", previousConnection); }
                    finally
                    {
                        try { Environment.SetEnvironmentVariable("PublicOrigin", previousOrigin); }
                        finally { Environment.SetEnvironmentVariable(ContentRootVariable, previousContentRoot); }
                    }
                }
                WriteReport();
            }
        }
        private sealed record LabIdentity(SecurityIdentifier Reader, SecurityIdentifier[] Trusted) : IMfaHostIdentity
        {
            public SecurityIdentifier? ReaderSid => Reader;
            public IReadOnlyCollection<SecurityIdentifier> TrustedPrincipals => Trusted;
            public string Description => "F0505-identity-LAB-explicit";
        }
        // TestServer has no real clients. Keep the product rate limiter active while giving each positive/replay case a fixed LAB address.
        private sealed class LabRequestAddress : IStartupFilter
        {
            public Action<IApplicationBuilder> Configure(Action<IApplicationBuilder> next) => app =>
            {
                app.Use(async (context, continuation) =>
                {
                    var last = context.Request.Headers["X-F0505-Lab-Case"].ToString() switch { "11" => 11, "17" => 17, _ => 1 };
                    context.Connection.RemoteIpAddress = IPAddress.Parse("127.0.0." + last);
                    await continuation();
                });
                next(app);
            };
        }
        public sealed record User(Guid Id, string Name, int Version, byte[] Secret, byte[] Ciphertext, string OldSession, string OldChallenge);
        public sealed record Database(Guid Id, string Name, string OwnerConnection, string RuntimeConnection, string RuntimeRole);
        private sealed record Factor(Guid Systemhaus, Guid User, int Version, byte[] Ciphertext);
    }
}
