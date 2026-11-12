using System.Net;
using System.Net.Http.Json;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using System.Security.Cryptography;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.Extensions.Logging;
using Npgsql;
using RackClick.Server;
using Xunit;
using AccountLab = RackClick.Quality.Tests.MfaAccountManagementTests.Laboratory;

namespace RackClick.Quality.Tests;

[Collection("MfaHttp")]
public sealed class InventoryDataAdministrationTests
{
    [Fact]
    public async Task EmptyInventoryAdministrationIsAuthorizedAndDoesNotChangeSecurity()
    {
        await using var h = await Harness.Create();
        var sentinel=await h.Lab.AddUser("inventory.security.sentinel",factor:true);await h.Lab.Challenge(sentinel.Id);await h.Lab.RecoveryCode(sentinel.Id);
        var before = await h.Lab.SnapshotAll();
        using var response = await h.Send("GET", "");
        Assert.True(response.IsSuccessStatusCode,await response.Content.ReadAsStringAsync(TestContext.Current.CancellationToken));
        var status = await h.Json(response);
        Assert.True(status["empty"]!.GetValue<bool>());
        Assert.Equal(0, status["counts"]!["customers"]!.GetValue<int>());
        Assert.Equal(50, status["demo"]!["counts"]!["customers"]!.GetValue<int>());
        Assert.Equal(20665, status["demo"]!["counts"]!["ports"]!.GetValue<int>());
        Assert.Equal(before, await h.Lab.SnapshotAll());
    }

    [Fact]
    public async Task Demo50BackupRestorePreservesEveryIdentityAndSecurityAndReplaysBeforeEmptyAndRevision()
    {
        await using var h = await Harness.Create();
        var sentinel=await h.Lab.AddUser("demo.security.sentinel",factor:true);await h.Lab.Challenge(sentinel.Id);await h.Lab.RecoveryCode(sentinel.Id);
        var before = await h.Security(); var revision = await h.Revision(); var key = Guid.NewGuid();
        using var loaded = await h.Send("POST","/demo50",new { confirmation="LOAD DEMO50" },revision,key);
        Assert.Equal(HttpStatusCode.OK,loaded.StatusCode);
        var result = await h.Json(loaded);
        Assert.Equal(50,result["counts"]!["customers"]!.GetValue<int>());
        Assert.Equal(1563,result["counts"]!["devices"]!.GetValue<int>());
        Assert.Equal(2207,result["counts"]!["connections"]!.GetValue<int>());
        foreach(var (table,count) in new (string,int)[] { ("customer",50),("inventory_site",66),("inventory_building",88),("inventory_room",226),("inventory_rack",180),("inventory_device",1563),("inventory_port_group",2869),("inventory_port",20665),("inventory_connection",2207) })
            Assert.Equal(count,await h.Lab.Count($"SELECT count(*) FROM {table}"));
        Assert.Equal(revision+1,result["systemhausRevision"]!.GetValue<long>());
        Assert.Equal(before,await h.Security());
        using var replay = await h.Send("POST","/demo50",new { confirmation="LOAD DEMO50" },revision,key);
        Assert.Equal(HttpStatusCode.OK,replay.StatusCode); Assert.Equal(result.ToJsonString(),(await h.Json(replay)).ToJsonString());
        using var populated = await h.Send("POST","/demo50",new { confirmation="LOAD DEMO50" },revision+1);
        Assert.Equal(HttpStatusCode.Conflict,populated.StatusCode);
        var backupKey = Guid.NewGuid();
        using var backup = await h.Send("POST","/backup",new {},revision+1,backupKey);
        Assert.Equal(HttpStatusCode.OK,backup.StatusCode);
        var exported = await h.Json(backup); var archive = exported["archive"]!;
        var bytes=Convert.FromBase64String(archive["contentBase64"]!.GetValue<string>());
        Assert.Equal(bytes.Length,archive["byteLength"]!.GetValue<int>());
        Assert.Equal(Convert.ToHexStringLower(SHA256.HashData(bytes)),archive["sha256"]!.GetValue<string>());
        using(var stream=typeof(InventoryStore).Assembly.GetManifestResourceStream("RackClick.Demo50.manifest.json")!)
        {
            var manifest=JsonNode.Parse(stream)!;var expectedCustomers=new JsonArray();
            foreach(var pin in manifest["customers"]!.AsArray().OrderBy(n=>n!["customerId"]!.GetValue<string>(),StringComparer.Ordinal))
            {
                using var customerStream=typeof(InventoryStore).Assembly.GetManifestResourceStream("RackClick.Demo50."+pin!["file"]!.GetValue<string>())!;var original=JsonNode.Parse(customerStream)!;
                expectedCustomers.Add(new JsonObject { ["id"]=pin["customerId"]!.DeepClone(),["name"]=pin["name"]!.DeepClone(),["revision"]=original["revision"]!.DeepClone(),["inventory"]=original["inventory"]!.DeepClone() });
            }
            Assert.True(JsonNode.DeepEquals(expectedCustomers,JsonNode.Parse(bytes)!["customers"]),"Export equals all 50 pinned source inventories, including identities, mounts, metadata and cables");
        }
        Assert.Equal($"rackclick-inventory-backup-{exported["operationId"]!.GetValue<string>()}.json",archive["filename"]!.GetValue<string>());
        Assert.Equal(revision+1,await h.Revision());
        using var generic = await h.Send("GET","/api/v1/customers/"+JsonNode.Parse(bytes)!["customers"]![0]!["id"]+"/operations/"+backupKey);
        Assert.Equal(HttpStatusCode.NotFound,generic.StatusCode);
        using var status=await h.Send("GET","/operations/"+backupKey);
        Assert.Equal(HttpStatusCode.OK,status.StatusCode); Assert.Equal("committed",(await h.Json(status))["state"]!.GetValue<string>());
        await using var target=await Harness.Create();var targetSentinel=await target.Lab.AddUser("restore.security.sentinel",factor:true);await target.Lab.Challenge(targetSentinel.Id);await target.Lab.RecoveryCode(targetSentinel.Id);
        var targetSecurity=await target.Security();var targetRevision=await target.Revision();
        var contentBase64=archive["contentBase64"]!.GetValue<string>();var archiveSha256=archive["sha256"]!.GetValue<string>();
        using var preview=await target.Send("POST","/preview",new { contentBase64 }); Assert.Equal(HttpStatusCode.OK,preview.StatusCode);
        var restoreKey=Guid.NewGuid();
        using var restore=await target.Send("POST","/restore",new { contentBase64,archiveSha256,confirmation="RESTORE INVENTORY" },targetRevision,restoreKey);
        Assert.Equal(HttpStatusCode.OK,restore.StatusCode); Assert.Equal(targetSecurity,await target.Security());
        using var roundtrip=await target.Send("POST","/backup",new {},targetRevision+1);
        Assert.Equal(HttpStatusCode.OK,roundtrip.StatusCode);
        var targetBytes=Convert.FromBase64String((await target.Json(roundtrip))["archive"]!["contentBase64"]!.GetValue<string>());
        Assert.True(JsonNode.DeepEquals(JsonNode.Parse(bytes)!["customers"],JsonNode.Parse(targetBytes)!["customers"]));
        using var restoreReplay=await target.Send("POST","/restore",new { contentBase64,archiveSha256,confirmation="RESTORE INVENTORY" },targetRevision,restoreKey);
        Assert.Equal(HttpStatusCode.OK,restoreReplay.StatusCode);
    }

    [Fact]
    public async Task PermissionsCsrfOriginActorAndSelectiveBodyLimitsAreEnforced()
    {
        await using var h=await Harness.Create();var rev=await h.Revision();var before=await h.Lab.SnapshotAll();
        foreach(var response in new[] {
            await h.Send("POST","/backup",new {},rev,origin:"https://foreign.invalid"),
            await h.Send("POST","/backup",new {},rev,csrf:"wrong") })
        { using(response) Assert.Equal(HttpStatusCode.Forbidden,response.StatusCode); }
        using var actor=await h.Send("POST","/backup",new {},rev,actor:Guid.NewGuid()); Assert.Equal(HttpStatusCode.Conflict,actor.StatusCode);
        using var stale=await h.Send("POST","/backup",new {},rev+1);Assert.Equal(HttpStatusCode.PreconditionFailed,stale.StatusCode);
        using var smallLimit=await h.Send("POST","/backup",new { unexpected=new string('x',17000) },rev);Assert.Equal(HttpStatusCode.RequestEntityTooLarge,smallLimit.StatusCode);
        using var previewLimit=await h.Send("POST","/preview",new { contentBase64=new string('x',17000) });Assert.Equal(HttpStatusCode.UnprocessableEntity,previewLimit.StatusCode);
        using var largeLimit=await h.Send("POST","/restore",new { contentBase64=new string('x',45*1024*1024) },rev);Assert.Equal(HttpStatusCode.RequestEntityTooLarge,largeLimit.StatusCode);
        Assert.Equal(before,await h.Lab.SnapshotAll());
        await h.Lab.Execute("DELETE FROM permission_grant WHERE capability='security.manage'");
        using var forbidden=await h.Send("GET","");Assert.Equal(HttpStatusCode.Forbidden,forbidden.StatusCode);
        using var previewDenied=await h.Send("POST","/preview",new { contentBase64="" });Assert.Equal(HttpStatusCode.Forbidden,previewDenied.StatusCode);
    }

    [Fact]
    public async Task AuditFailureRollsBackTheEntireGlobalImportAndReceipt()
    {
        await using var h=await Harness.Create();var rev=await h.Revision();
        await h.Lab.Execute("CREATE FUNCTION reject_data_audit_fixture() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF NEW.action LIKE 'inventory.data.%' THEN RAISE EXCEPTION 'fixture_audit_failure'; END IF; RETURN NEW; END $$; CREATE TRIGGER reject_data_audit_fixture BEFORE INSERT ON audit_event FOR EACH ROW EXECUTE FUNCTION reject_data_audit_fixture()");
        var before=await h.Lab.SnapshotAll();var request=Guid.NewGuid();
        using var failed=await h.Send("POST","/restore",RestoreBody(Archive()),rev,request);Assert.Equal(HttpStatusCode.ServiceUnavailable,failed.StatusCode);
        Assert.Equal(0,await h.Lab.Count("SELECT count(*) FROM customer"));Assert.Equal(before,await h.Lab.SnapshotAll());
        using var status=await h.Send("GET","/operations/"+request);Assert.Equal("notRecorded",(await h.Json(status))["state"]!.GetValue<string>());
    }

    [Fact]
    public async Task ClosedArchiveRejectsDuplicatesUnknownFieldsForeignReferencesAndInvalidHardwareWithoutMutation()
    {
        await using var h=await Harness.Create();var before=await h.Lab.SnapshotAll();
        var valid=Archive();
        using var preview=await h.Send("POST","/preview",new { contentBase64=Convert.ToBase64String(Encoding.UTF8.GetBytes(valid.ToJsonString())) });Assert.Equal(HttpStatusCode.OK,preview.StatusCode);
        var variants=new List<string> { valid.ToJsonString().Replace("\"schemaVersion\":48","\"schemaVersion\":48,\"schemaVersion\":48",StringComparison.Ordinal),
            valid.ToJsonString().Replace("Synthetic roundtrip","\\uD800",StringComparison.Ordinal),
            valid.ToJsonString().Replace("Synthetic roundtrip","\\uDC00",StringComparison.Ordinal),
            valid.ToJsonString().Replace("\"name\":","\"\\uD800\":0,\"name\":",StringComparison.Ordinal) };
        var unknown=(JsonObject)valid.DeepClone();unknown["accounts"]=new JsonArray();variants.Add(unknown.ToJsonString());
        var relation=(JsonObject)valid.DeepClone();relation["customers"]![0]!["inventory"]!["buildings"]!.AsArray().Add(new JsonObject { ["id"]=Guid.NewGuid().ToString(),["siteId"]=Guid.NewGuid().ToString(),["name"]="Foreign",["properties"]=new JsonObject() });variants.Add(relation.ToJsonString());
        var model=(JsonObject)valid.DeepClone();model["customers"]![0]!["inventory"]!["racks"]!.AsArray().Add(new JsonObject { ["id"]=Guid.NewGuid().ToString(),["roomId"]=null,["name"]="Invalid model",["sizeU"]=42,["location"]="",["hardwareProfileKey"]="invented",["properties"]=new JsonObject { ["hardwareProfileVersion"]="invented" } });variants.Add(model.ToJsonString());
        foreach(var text in variants) { using var rejected=await h.Send("POST","/preview",new { contentBase64=Convert.ToBase64String(Encoding.UTF8.GetBytes(text)) });Assert.Equal(HttpStatusCode.UnprocessableEntity,rejected.StatusCode); }
        using var badHash=await h.Send("POST","/restore",new { contentBase64=Convert.ToBase64String(Encoding.UTF8.GetBytes(valid.ToJsonString())),archiveSha256=new string('0',64),confirmation="RESTORE INVENTORY" },await h.Revision());Assert.Equal(HttpStatusCode.UnprocessableEntity,badHash.StatusCode);
        Assert.Equal(before,await h.Lab.SnapshotAll());
    }

    private static JsonObject Archive()
    {
        var inventory=new JsonObject();foreach(var name in new[] {"sites","buildings","rooms","racks","devices","portGroups","ports","connections"}) inventory[name]=new JsonArray();
        return new JsonObject { ["formatVersion"]=1,["kind"]="RackClickInventoryBackup",["schemaVersion"]=48,["createdAt"]="2026-11-12T00:00:00Z",["customers"]=new JsonArray(new JsonObject { ["id"]=Guid.NewGuid().ToString(),["name"]="Synthetic roundtrip",["revision"]=3,["inventory"]=inventory }) };
    }

    [Fact]
    public async Task ExplicitCancellationFencesUnrecordedIntentButCannotUndoACommit()
    {
        await using var h=await Harness.Create();var rev=await h.Revision();var key=Guid.NewGuid();
        using var cancelled=await h.Send("POST","/operations/"+key+"/cancel",new { action="backup",archiveSha256=(string?)null },rev,key);
        Assert.Equal(HttpStatusCode.OK,cancelled.StatusCode);Assert.Equal("cancelled",(await h.Json(cancelled))["state"]!.GetValue<string>());
        using var fenced=await h.Send("POST","/backup",new {},rev,key);Assert.Equal(HttpStatusCode.Conflict,fenced.StatusCode);Assert.Equal("operation_cancelled",(await h.Json(fenced))["error"]!.GetValue<string>());
        using var status=await h.Send("GET","/operations/"+key);Assert.Equal("cancelled",(await h.Json(status))["state"]!.GetValue<string>());
        using var reused=await h.Send("POST","/operations/"+key+"/cancel",new { action="demo50",archiveSha256=(string?)null },rev,key);Assert.Equal(HttpStatusCode.Conflict,reused.StatusCode);
        var committedKey=Guid.NewGuid();using var committed=await h.Send("POST","/backup",new {},rev,committedKey);Assert.Equal(HttpStatusCode.OK,committed.StatusCode);
        using var afterCommit=await h.Send("POST","/operations/"+committedKey+"/cancel",new { action="backup",archiveSha256=(string?)null },rev,committedKey);Assert.Equal(HttpStatusCode.OK,afterCommit.StatusCode);Assert.Equal("committed",(await h.Json(afterCommit))["state"]!.GetValue<string>());
        await h.Lab.Execute("DELETE FROM permission_grant WHERE capability='reports.export'");
        using var revoked=await h.Send("GET","/operations/"+committedKey);Assert.Equal(HttpStatusCode.Forbidden,revoked.StatusCode);
        using var revokedCancel=await h.Send("POST","/operations/"+committedKey+"/cancel",new { action="backup",archiveSha256=(string?)null },rev,committedKey);Assert.Equal(HttpStatusCode.Forbidden,revokedCancel.StatusCode);
    }

    [Fact]
    public async Task ConcurrentImportsSerializeAndAuthorityRevokedDuringHouseWaitIsRechecked()
    {
        await using var h=await Harness.Create();var rev=await h.Revision();var body=RestoreBody(Archive());
        var results=await Task.WhenAll(h.Send("POST","/restore",body,rev),h.Send("POST","/restore",body,rev));
        Assert.Equal(1,results.Count(r=>r.StatusCode==HttpStatusCode.OK));Assert.Equal(1,results.Count(r=>r.StatusCode==HttpStatusCode.PreconditionFailed));foreach(var result in results) result.Dispose();
        Assert.Equal(1,await h.Lab.Count("SELECT count(*) FROM customer"));
        await using var db=await h.Lab.RuntimeSource.OpenConnectionAsync(TestContext.Current.CancellationToken);await using var tx=await db.BeginTransactionAsync(TestContext.Current.CancellationToken);
        await using(var hold=new NpgsqlCommand("SELECT id FROM systemhaus FOR UPDATE",db,tx)) await hold.ExecuteNonQueryAsync(TestContext.Current.CancellationToken);
        var pending=h.Send("POST","/backup",new {},rev+1);bool waiting=false;
        for(int i=0;i<200;i++) { if(await h.Lab.Count("SELECT count(*) FROM pg_stat_activity WHERE datname=current_database() AND cardinality(pg_blocking_pids(pid))>0")>0) {waiting=true;break;}await Task.Delay(20,TestContext.Current.CancellationToken); }
        Assert.True(waiting,"Request reached the database lock before privilege revocation");
        await using(var revoke=new NpgsqlCommand("DELETE FROM permission_grant WHERE capability='reports.export'",db,tx)) await revoke.ExecuteNonQueryAsync(TestContext.Current.CancellationToken);
        await tx.CommitAsync(TestContext.Current.CancellationToken);
        using var denied=await pending;Assert.Equal(HttpStatusCode.Forbidden,denied.StatusCode);
    }

    [Fact]
    public async Task PhysicalValidationRejectsAlteredHardwareCapacityMountsAndCablesBeforeAnyWrite()
    {
        await using var h=await Harness.Create();var fixture=DemoArchive();var variants=new List<JsonObject>();
        JsonObject Variant() {var copy=(JsonObject)fixture.DeepClone();variants.Add(copy);return copy["customers"]![0]!["inventory"]!.AsObject();}
        var capacity=Variant();foreach(var rack in capacity["racks"]!.AsArray()) rack!["sizeU"]=1;
        var profile=Variant();var bound=profile["devices"]!.AsArray().First(d=>d!["hardwareProfileKey"] is not null)!;bound["properties"]!["hardwareProfileVersion"]="unknown";
        var ports=Variant();var hardwareIds=ports["devices"]!.AsArray().Where(d=>d!["hardwareProfileKey"] is not null).Select(d=>d!["id"]!.GetValue<string>()).ToHashSet();ports["ports"]!.AsArray().First(p=>hardwareIds.Contains(p!["deviceId"]!.GetValue<string>()))!["face"]="auto";
        var missing=Variant();missing["ports"]!.AsArray().RemoveAt(0);
        var cycle=Variant();var child=cycle["devices"]!.AsArray().First(d=>d!["mountParentId"] is not null)!;child["mountParentId"]=child["id"]!.DeepClone();
        var slot=Variant();var mounted=slot["devices"]!.AsArray().First(d=>d!["mountParentId"] is not null)!;var duplicate=(JsonObject)mounted.DeepClone();duplicate["id"]=Guid.NewGuid().ToString();duplicate["sortOrder"]=999999;slot["devices"]!.AsArray().Add(duplicate);
        var cable=Variant();cable["connections"]![0]!["toPortId"]=cable["connections"]![0]!["fromPortId"]!.DeepClone();
        var pair=Variant();var power=pair["ports"]!.AsArray().Where(p=>p!["type"]!.GetValue<string>()=="power").Take(2).ToArray();foreach(var p in power) p!["powerRole"]="inlet";
        pair["connections"]!.AsArray().Clear();pair["connections"]!.AsArray().Add(new JsonObject { ["id"]=Guid.NewGuid().ToString(),["fromPortId"]=power[0]!["id"]!.DeepClone(),["toPortId"]=power[1]!["id"]!.DeepClone(),["note"]="",["color"]=null,["patch"]="none",["createdAt"]="2026-11-12T00:00:00Z",["properties"]=new JsonObject() });
        foreach(var variant in variants)
        { using var response=await h.Send("POST","/preview",new { contentBase64=Convert.ToBase64String(Encoding.UTF8.GetBytes(variant.ToJsonString())) });Assert.Equal(HttpStatusCode.UnprocessableEntity,response.StatusCode); }
        var cross=(JsonObject)fixture.DeepClone();var foreign=Archive()["customers"]![0]!.DeepClone();var site=Guid.NewGuid().ToString();foreign["inventory"]!["sites"]!.AsArray().Add(new JsonObject { ["id"]=site,["name"]="Other customer's site",["properties"]=new JsonObject() });cross["customers"]!.AsArray().Add(foreign);cross["customers"]![0]!["inventory"]!["buildings"]![0]!["siteId"]=site;
        using var crossRejected=await h.Send("POST","/preview",new { contentBase64=Convert.ToBase64String(Encoding.UTF8.GetBytes(cross.ToJsonString())) });Assert.Equal(HttpStatusCode.UnprocessableEntity,crossRejected.StatusCode);
        Assert.Equal(0,await h.Lab.Count("SELECT count(*) FROM customer"));
    }

    [Fact]
    public async Task ArchiveLimitsAndJsonbUnicodeAreCheckedBeforeImportAndRuntimeCannotUseDdl()
    {
        await using var h=await Harness.Create();
        await using(var db=await h.Lab.RuntimeSource.OpenConnectionAsync(TestContext.Current.CancellationToken))
        await using(var command=new NpgsqlCommand("SELECT NOT rolsuper AND NOT rolcreatedb AND NOT rolcreaterole AND NOT has_schema_privilege(current_user,'public','CREATE') AND NOT has_database_privilege(current_user,current_database(),'CREATE,TEMPORARY') AND NOT has_table_privilege(current_user,'hardware_definition','INSERT,UPDATE,DELETE') FROM pg_roles WHERE rolname=current_user",db))
            Assert.True((bool)(await command.ExecuteScalarAsync(TestContext.Current.CancellationToken))!);
        using var encoded=await h.Send("POST","/preview",new { contentBase64=new string('A',44739248) });Assert.Equal(HttpStatusCode.UnprocessableEntity,encoded.StatusCode);Assert.Equal("inventory_archive_too_large",(await h.Json(encoded))["error"]!.GetValue<string>());
        var rows=Archive();rows["customers"]![0]!["inventory"]!["sites"]=new JsonArray(Enumerable.Range(0,100000).Select(_=>(JsonNode)new JsonObject()).ToArray());
        using var rowLimit=await h.Send("POST","/preview",new { contentBase64=Convert.ToBase64String(Encoding.UTF8.GetBytes(rows.ToJsonString())) });Assert.Equal(HttpStatusCode.UnprocessableEntity,rowLimit.StatusCode);Assert.Equal("inventory_archive_too_large",(await h.Json(rowLimit))["error"]!.GetValue<string>());
        var unicode=Archive();unicode["customers"]![0]!["inventory"]!["sites"]!.AsArray().Add(new JsonObject { ["id"]=Guid.NewGuid().ToString(),["name"]="Valid site",["properties"]=new JsonObject { ["untrusted"]="\0" } });
        using var jsonb=await h.Send("POST","/preview",new { contentBase64=Convert.ToBase64String(Encoding.UTF8.GetBytes(unicode.ToJsonString())) });Assert.Equal(HttpStatusCode.UnprocessableEntity,jsonb.StatusCode);
        Assert.Equal(0,await h.Lab.Count("SELECT count(*) FROM customer"));
    }

    private static JsonObject DemoArchive()
    {
        using var data=typeof(InventoryStore).Assembly.GetManifestResourceStream("RackClick.Demo50.c01.inventory.json")!;
        var source=JsonNode.Parse(data)!;var result=Archive();result["customers"]![0]!["id"]=source["customerId"]!.DeepClone();result["customers"]![0]!["revision"]=source["revision"]!.DeepClone();result["customers"]![0]!["inventory"]=source["inventory"]!.DeepClone();return result;
    }

    [Fact]
    public async Task ConcurrentSameKeyHasOneCommitAndReceiptsNeverCrossActorsOrGrantScopes()
    {
        await using var h=await Harness.Create();var rev=await h.Revision();var key=Guid.NewGuid();var archive=Archive();
        var results=await Task.WhenAll(h.Send("POST","/restore",RestoreBody(archive),rev,key),h.Send("POST","/restore",RestoreBody(archive),rev,key));
        foreach(var response in results) Assert.Equal(HttpStatusCode.OK,response.StatusCode);
        Assert.Equal((await h.Json(results[0])).ToJsonString(),(await h.Json(results[1])).ToJsonString());foreach(var response in results) response.Dispose();
        Assert.Equal(1,await h.Lab.Count("SELECT count(*) FROM audit_event WHERE request_id=@key",("key",key)));
        var other=await h.Lab.AddUser("another.global.administrator");
        await h.Lab.Execute("INSERT INTO user_group_member(systemhaus_id,user_id,group_id) SELECT systemhaus_id,@other,group_id FROM user_group_member WHERE user_id=@admin",("other",other.Id),("admin",h.Lab.Admin.Id));
        var store=new InventoryStore(h.Lab.RuntimeSource);
        var status=JsonSerializer.SerializeToNode(await store.InventoryDataOperation(other,key,TestContext.Current.CancellationToken),new JsonSerializerOptions(JsonSerializerDefaults.Web))!;
        Assert.Equal("notRecorded",status["state"]!.GetValue<string>());Assert.Null(status["operation"]);
        var scoped=await h.Lab.AddUser("client.scoped.administrator");var group=Guid.NewGuid();var customer=Guid.Parse(archive["customers"]![0]!["id"]!.GetValue<string>());
        await h.Lab.Execute("INSERT INTO user_group(id,systemhaus_id,name) VALUES(@group,@house,'Client-scoped administrative fixture'); INSERT INTO user_group_member(systemhaus_id,user_id,group_id) VALUES(@house,@user,@group); INSERT INTO permission_grant(id,systemhaus_id,user_group_id,capability,customer_id) SELECT gen_random_uuid(),systemhaus_id,@group,capability,@customer FROM permission_grant WHERE customer_id IS NULL AND customer_group_id IS NULL",("group",group),("house",h.Lab.House),("user",scoped.Id),("customer",customer));
        var denied=await Assert.ThrowsAsync<RackClick.Domain.DomainError>(()=>store.ReadInventoryDataAdministration(scoped,TestContext.Current.CancellationToken));Assert.Equal(403,denied.Status);
        using var anonymous=await h.Client.GetAsync("/api/v1/admin/inventory-data",TestContext.Current.CancellationToken);Assert.Equal(HttpStatusCode.Unauthorized,anonymous.StatusCode);
    }

    [Fact]
    public async Task BackupAndRestorePreserveAnExistingCableWhosePortWasMarkedFaultyByTheEditor()
    {
        await using var h=await Harness.Create();long revision=await h.Revision();var archive=DemoArchive();
        using var imported=await h.Send("POST","/restore",RestoreBody(archive),revision);Assert.Equal(HttpStatusCode.OK,imported.StatusCode);
        var customer=archive["customers"]![0]!;var inventory=customer["inventory"]!;
        var endpoints=inventory["connections"]!.AsArray().SelectMany(c=>new[]{c!["fromPortId"]!.GetValue<string>(),c["toPortId"]!.GetValue<string>()}).ToHashSet();
        var port=inventory["ports"]!.AsArray().First(p=>p!["type"]!.GetValue<string>()=="rj45" && endpoints.Contains(p["id"]!.GetValue<string>()))!;
        var group=inventory["portGroups"]!.AsArray().Single(g=>g!["id"]!.GetValue<string>()==port["groupId"]!.GetValue<string>())!;
        var command=JsonSerializer.SerializeToElement(new { deviceId=port["deviceId"]!.GetValue<string>(),groupId=port["groupId"]!.GetValue<string>(),groupType=group["type"]!.GetValue<string>(),portIds=new[]{port["id"]!.GetValue<string>()},changes=new {status="faulty",label="User <label>",color="#ABCDEF",properties=new {notes="Changed after connection"}} });
        await new InventoryStore(h.Lab.RuntimeSource).Execute(h.Lab.Admin,Guid.Parse(customer["id"]!.GetValue<string>()),new InventoryCommandRequest("ports.update",command),customer["revision"]!.GetValue<long>(),Guid.NewGuid(),TestContext.Current.CancellationToken);
        using var backup=await h.Send("POST","/backup",new {},revision+1);Assert.Equal(HttpStatusCode.OK,backup.StatusCode);
        var artifact=(await h.Json(backup))["archive"]!;var text=Convert.FromBase64String(artifact["contentBase64"]!.GetValue<string>());
        var saved=JsonNode.Parse(text)!["customers"]![0]!["inventory"]!["ports"]!.AsArray().Single(p=>p!["id"]!.GetValue<string>()==port["id"]!.GetValue<string>())!;
        Assert.Equal("faulty",saved["status"]!.GetValue<string>());Assert.Equal("User <label>",saved["label"]!.GetValue<string>());Assert.Equal("Changed after connection",saved["properties"]!["notes"]!.GetValue<string>());
        await using var target=await Harness.Create();using var restore=await target.Send("POST","/restore",new { contentBase64=artifact["contentBase64"]!.GetValue<string>(),archiveSha256=artifact["sha256"]!.GetValue<string>(),confirmation="RESTORE INVENTORY" },await target.Revision());Assert.Equal(HttpStatusCode.OK,restore.StatusCode);
        Assert.Equal(inventory["connections"]!.AsArray().Count,await target.Lab.Count("SELECT count(*) FROM inventory_connection"));
    }
    [Fact]
    public async Task NullRequiredArchiveValuesAreRejectedEquallyByPreviewAndRestore()
    {
        await using var h=await Harness.Create();var fixture=DemoArchive();var revision=await h.Revision();var failures=new List<string>();
        var required=new Dictionary<string,string[]> {
            ["sites"]=["id","name","properties"], ["buildings"]=["id","siteId","name","properties"],
            ["rooms"]=["id","buildingId","name","properties"], ["racks"]=["id","name","location","sizeU","properties"],
            ["devices"]=["id","kind","name","sortOrder","properties"], ["portGroups"]=["id","deviceId","type","name","prefix","sortOrder"],
            ["ports"]=["id","deviceId","groupId","type","gn","sortOrder","label","status","poe","face","powerRole","properties"],
            ["connections"]=["id","fromPortId","toPortId","note","patch","createdAt","properties"] };
        foreach(var collection in required)
        foreach(string field in collection.Value)
        {
            var archive=(JsonObject)fixture.DeepClone();archive["customers"]![0]!["inventory"]![collection.Key]![0]![field]=null;
            var bytes=Encoding.UTF8.GetBytes(archive.ToJsonString());
            using var preview=await h.Send("POST","/preview",new { contentBase64=Convert.ToBase64String(bytes) });
            using var restore=await h.Send("POST","/restore",RestoreBody(archive),revision);
            if(preview.StatusCode!=HttpStatusCode.UnprocessableEntity || restore.StatusCode!=HttpStatusCode.UnprocessableEntity)
                failures.Add($"{collection.Key}.{field}=null: preview{(int)preview.StatusCode}/restore{(int)restore.StatusCode}");
        }
        Assert.Equal(0,await h.Lab.Count("SELECT count(*) FROM customer"));
        Assert.Equal(0,await h.Lab.Count("SELECT count(*) FROM operation"));
        Assert.Equal(revision,await h.Revision());Assert.True(failures.Count==0,string.Join("; ",failures));
    }

    [Fact]
    public async Task CustomerRevisionsOutsideTheJavaScriptSafeRangeCannotEnterTheInventory()
    {
        await using var h=await Harness.Create();var revision=await h.Revision();var failures=new List<string>();
        foreach(long value in new[]{0L,-1L,9007199254740992L,long.MaxValue})
        {
            var archive=Archive();archive["customers"]![0]!["revision"]=value;var bytes=Encoding.UTF8.GetBytes(archive.ToJsonString());
            using var preview=await h.Send("POST","/preview",new { contentBase64=Convert.ToBase64String(bytes) });
            // The pre-fix import is intentionally isolated per accepted value, so both review responses are observable.
            if(preview.StatusCode!=HttpStatusCode.UnprocessableEntity) failures.Add($"revision{value}: preview{(int)preview.StatusCode}");
        }
        var unsafeArchive=Archive();unsafeArchive["customers"]![0]!["revision"]=9007199254740992L;
        using var restore=await h.Send("POST","/restore",RestoreBody(unsafeArchive),revision);
        if(restore.StatusCode!=HttpStatusCode.UnprocessableEntity) failures.Add($"unsafe restore{(int)restore.StatusCode}");
        Assert.True(failures.Count==0,string.Join("; ",failures));
        Assert.Equal(0,await h.Lab.Count("SELECT count(*) FROM customer"));Assert.Equal(0,await h.Lab.Count("SELECT count(*) FROM operation"));
    }

    [Theory]
    [InlineData(1L)]
    [InlineData(9007199254740991L)]
    public async Task SafeRevisionBoundaryAndLegitimateNullableValuesRoundTrip(long customerRevision)
    {
        await using var h=await Harness.Create();var archive=DemoArchive();archive["customers"]![0]!["revision"]=customerRevision;
        var port=archive["customers"]![0]!["inventory"]!["ports"]!.AsArray().First(p=>p!["type"]!.GetValue<string>()=="rj45")!;
        port["poe"]=false;port["watts"]=null;port["color"]=null;port["properties"]!["userNullableValue"]=null;
        var bytes=Encoding.UTF8.GetBytes(archive.ToJsonString());
        using var preview=await h.Send("POST","/preview",new { contentBase64=Convert.ToBase64String(bytes) });Assert.Equal(HttpStatusCode.OK,preview.StatusCode);
        var revision=await h.Revision();using var restore=await h.Send("POST","/restore",RestoreBody(archive),revision);Assert.Equal(HttpStatusCode.OK,restore.StatusCode);
        using var list=await h.Send("GET","/api/v1/customers");Assert.Equal(HttpStatusCode.OK,list.StatusCode);
        var customers=JsonNode.Parse(await list.Content.ReadAsStringAsync(TestContext.Current.CancellationToken))!.AsArray();Assert.Equal(customerRevision,customers[0]!["revision"]!.GetValue<long>());
        using var backup=await h.Send("POST","/backup",new {},revision+1);Assert.Equal(HttpStatusCode.OK,backup.StatusCode);
        var exported=JsonNode.Parse(Convert.FromBase64String((await h.Json(backup))["archive"]!["contentBase64"]!.GetValue<string>()))!;
        Assert.True(JsonNode.DeepEquals(archive["customers"],exported["customers"]));
    }

    [Fact]
    public async Task BackupRejectsAnUnsafePersistedCustomerRevisionWithoutRecordingAnArtifact()
    {
        await using var h=await Harness.Create();var id=Guid.NewGuid();var revision=await h.Revision();
        await h.Lab.Execute("INSERT INTO customer(id,systemhaus_id,name,revision) VALUES(@id,@house,'Unsafe revision fixture',9007199254740992)",("id",id),("house",h.Lab.House));
        using var backup=await h.Send("POST","/backup",new {},revision);Assert.Equal(HttpStatusCode.UnprocessableEntity,backup.StatusCode);
        Assert.Equal(0,await h.Lab.Count("SELECT count(*) FROM operation"));
    }

    [Fact]
    public async Task ExhaustedSafeHouseRevisionRejectsNewImportsAndKeepsBackupAvailable()
    {
        var failures=new List<string>();
        foreach(string action in new[]{"restore","demo50"})
        {
            await using var h=await Harness.Create();
            await h.Lab.Execute("UPDATE systemhaus SET revision=9007199254740991");
            object body=action=="restore"?RestoreBody(Archive()):new { confirmation="LOAD DEMO50" };
            using var response=await h.Send("POST","/"+action,body,9007199254740991L);
            if(response.StatusCode!=HttpStatusCode.Conflict) failures.Add($"{action}: {(int)response.StatusCode}");
            if(await h.Lab.Count("SELECT count(*) FROM customer")!=0 || await h.Lab.Count("SELECT count(*) FROM operation")!=0 || await h.Lab.Count("SELECT revision FROM systemhaus")!=9007199254740991L) failures.Add($"{action}: changed inventory/receipt/revision");
            if(response.StatusCode==HttpStatusCode.Conflict)
            {
                Assert.Equal("inventory_revision_exhausted",(await h.Json(response))["error"]!.GetValue<string>());
                using var backup=await h.Send("POST","/backup",new {},9007199254740991L);Assert.Equal(HttpStatusCode.OK,backup.StatusCode);
                Assert.Equal(9007199254740991L,(await h.Json(backup))["systemhausRevision"]!.GetValue<long>());
            }
        }
        Assert.True(failures.Count==0,string.Join("; ",failures));
    }

    [Fact]
    public async Task LastSafeHouseRevisionCanBeCommittedAndItsReplayPrecedesTheExhaustionGuard()
    {
        await using var h=await Harness.Create();await h.Lab.Execute("UPDATE systemhaus SET revision=9007199254740990");
        var archive=Archive();var key=Guid.NewGuid();using var response=await h.Send("POST","/restore",RestoreBody(archive),9007199254740990L,key);
        Assert.Equal(HttpStatusCode.OK,response.StatusCode);var result=await h.Json(response);Assert.Equal(9007199254740991L,result["systemhausRevision"]!.GetValue<long>());
        using var replay=await h.Send("POST","/restore",RestoreBody(archive),9007199254740990L,key);Assert.Equal(HttpStatusCode.OK,replay.StatusCode);Assert.Equal(result.ToJsonString(),(await h.Json(replay)).ToJsonString());
        Assert.Equal(1,await h.Lab.Count("SELECT count(*) FROM customer"));Assert.Equal(1,await h.Lab.Count("SELECT count(*) FROM operation"));
    }

    private static object RestoreBody(JsonObject archive)
    {
        var bytes=Encoding.UTF8.GetBytes(archive.ToJsonString());return new { contentBase64=Convert.ToBase64String(bytes),archiveSha256=Convert.ToHexStringLower(SHA256.HashData(bytes)),confirmation="RESTORE INVENTORY" };
    }

    internal sealed class Harness : IAsyncDisposable
    {
        public AccountLab Lab { get; private set; } = null!;
        public HttpClient Client { get; private set; } = null!;
        private WebApplicationFactory<Program> _factory = null!;
        private readonly Dictionary<string, string?> _previous = [];
        public const string Origin = "https://rackclick.test";
        private string _cookie = "", _csrf = "";
        public static async Task<Harness> Create()
        {
            var h = new Harness { Lab = await AccountLab.Create() };
            try
            {
                // Production hardware catalogue must be read-only to the runtime identity.
                string runtime = new NpgsqlConnectionStringBuilder(h.Lab.RuntimeConnection).Username!;
                string database = new NpgsqlConnectionStringBuilder(h.Lab.RuntimeConnection).Database!;
                await h.Lab.Execute($"REVOKE INSERT,UPDATE,DELETE ON hardware_definition,hardware_mount_slot,hardware_group_template,hardware_passthrough,hardware_connector_template,hardware_profile_extension,hardware_group_extension FROM {runtime}");
                await h.Lab.Execute($"REVOKE TEMPORARY ON DATABASE {database} FROM PUBLIC");
                foreach (var pair in new Dictionary<string,string?> { ["ConnectionStrings__RackClick"] = h.Lab.RuntimeConnection,
                    ["MfaKeyStore__Enabled"] = "false", ["PublicOrigin"] = Origin, ["RackClick__FrontendPath"] = null })
                { h._previous[pair.Key] = Environment.GetEnvironmentVariable(pair.Key); Environment.SetEnvironmentVariable(pair.Key,pair.Value); }
                h._factory = new WebApplicationFactory<Program>().WithWebHostBuilder(builder =>
                    builder.UseEnvironment("Production").ConfigureLogging(logging => logging.ClearProviders()));
                h.Client = h._factory.CreateClient(new WebApplicationFactoryClientOptions { BaseAddress = new Uri(Origin), HandleCookies = false });
                using var login = await h.Send("POST", "/api/v1/auth/login", new { username = h.Lab.Admin.UserName, password = AccountLab.Password });
                Assert.Equal(HttpStatusCode.OK, login.StatusCode);
                h._cookie = login.Headers.GetValues("Set-Cookie").Single(v=>v.StartsWith("RackClick.Session=",StringComparison.Ordinal)).Split(';')[0];
                h._csrf = (await h.Json(login))["csrf"]!.GetValue<string>();
                return h;
            }
            catch { await h.DisposeAsync(); throw; }
        }
        public Task<HttpResponseMessage> Send(string method, string path, object? body = null, long? revision = null,
            Guid? requestId = null, string? origin = null, string? csrf = null, Guid? actor = null)
        {
            var request = new HttpRequestMessage(new HttpMethod(method),path.StartsWith("/api/",StringComparison.Ordinal) ? path : "/api/v1/admin/inventory-data"+path);
            if(body is not null) request.Content = new StringContent(JsonSerializer.Serialize(body),Encoding.UTF8,"application/json");
            if(_cookie.Length>0) request.Headers.Add("Cookie",_cookie); request.Headers.Add("Origin",origin ?? Origin);
            request.Headers.Add("X-RackClick-CSRF",csrf ?? _csrf); request.Headers.Add("X-RackClick-Actor",(actor ?? Lab.Admin.Id).ToString());
            if(revision.HasValue) request.Headers.TryAddWithoutValidation("If-Match","\""+revision+"\"");
            request.Headers.Add("Idempotency-Key",(requestId ?? Guid.NewGuid()).ToString());
            return Client.SendAsync(request,TestContext.Current.CancellationToken);
        }
        public async Task<JsonObject> Json(HttpResponseMessage response) => JsonNode.Parse(await response.Content.ReadAsStringAsync(TestContext.Current.CancellationToken))!.AsObject();
        public async Task<long> Revision() { using var r = await Send("GET",""); Assert.True(r.IsSuccessStatusCode,await r.Content.ReadAsStringAsync(TestContext.Current.CancellationToken)); return (await Json(r))["systemhausRevision"]!.GetValue<long>(); }
        public async Task<string> Security()
        {
            var values=new List<string>();await using var db=await Lab.RuntimeSource.OpenConnectionAsync(TestContext.Current.CancellationToken);
            foreach(var table in new[] {"app_user","app_mfa_user","app_mfa_factor","app_mfa_recovery_code","app_mfa_challenge","app_session","app_mfa_policy","user_group","user_group_member","permission_grant","customer_group","customer_group_member"})
            { await using var command=new NpgsqlCommand($"SELECT COALESCE(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text),'[]'::jsonb)::text FROM {table} t",db);values.Add(table+":"+await command.ExecuteScalarAsync(TestContext.Current.CancellationToken)); }
            return string.Join("\n",values);
        }
        public async ValueTask DisposeAsync()
        {
            Client?.Dispose(); if(_factory is not null) await _factory.DisposeAsync();
            if(Lab is not null) await Lab.DisposeAsync();
            foreach(var pair in _previous) Environment.SetEnvironmentVariable(pair.Key,pair.Value);
        }
    }
}
