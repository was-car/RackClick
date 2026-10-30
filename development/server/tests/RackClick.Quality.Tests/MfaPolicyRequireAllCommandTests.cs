using Microsoft.Extensions.Configuration;
using RackClick.Domain;
using RackClick.Server;
using Xunit;

namespace RackClick.Quality.Tests;

public sealed class MfaPolicyRequireAllCommandTests
{
    private static readonly Guid DatabaseId = Guid.Parse("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee");
    private static readonly Guid StoreId = Guid.Parse("11111111-2222-3333-4444-555555555555");
    private static readonly Guid ActorId = Guid.Parse("22222222-3333-4444-5555-666666666666");
    private static string Confirmation => "REQUIRE MFA " + DatabaseId.ToString("D");

    [Fact]
    public async Task UnelevatedOperatorCannotReadInputOrInvokeEitherDependency()
    {
        var output = new StringWriter();
        var rc = await MfaPolicyRequireAllCommand.Run(Config(), new TrapReader(), output, false,
            (_, _) => throw new InvalidOperationException("preflight reached"),
            (_, _, _, _, _) => throw new InvalidOperationException("database reached"), TestContext.Current.CancellationToken);
        Assert.Equal(1, rc);
        Assert.Contains("mfa_policy_not_elevated", output.ToString(), StringComparison.Ordinal);
    }

    [Theory]
    [InlineData("wrong")]
    [InlineData("REQUIRE MFA aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee\n")]
    [InlineData("REQUIRE MFA aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeeeEXTRA")]
    public async Task ConfirmationIsExactAndRejectsBeforePreflightOrDatabase(string confirmation)
    {
        await Reject(Config(), new StringReader(confirmation), "mfa_policy_confirmation_invalid");
    }

    [Theory]
    [InlineData("MfaPolicy:DatabaseInstanceId", "not-a-guid")]
    [InlineData("MfaPolicy:ActorId", "00000000-0000-0000-0000-000000000000")]
    [InlineData("MfaKeyStore:InstallationId", "")]
    [InlineData("MfaKeyStore:Enabled", "false")]
    [InlineData("MfaPolicy:ReaderSid", "")]
    [InlineData("ConnectionStrings:RackClick", "")]
    public async Task InvalidConfigurationDoesNotReadConfirmation(string field, string value)
    {
        await Reject(Config(field, value), new TrapReader(), "mfa_policy_config_invalid");
    }

    [Fact]
    public async Task SeparateDatabaseAndStoreIdsArePreservedAndPreflightPrecedesDatabase()
    {
        bool validated = false;
        var output = new StringWriter();
        var rc = await MfaPolicyRequireAllCommand.Run(Config(), new StringReader(Confirmation), output, true,
            (configuration, sid) =>
            {
                Assert.Equal(StoreId.ToString("D"), configuration["MfaKeyStore:InstallationId"]);
                Assert.Equal("S-1-5-21-1-2-3-1001", sid); validated = true;
                return Keys;
            },
            (connection, databaseId, actorId, provider, _) =>
            {
                Assert.True(validated);
                Assert.Equal(DatabaseId, databaseId); Assert.Equal(ActorId, actorId);
                Assert.Equal("private-connection-value", connection);
                Assert.Same(Keys, provider);
                return Task.FromResult(new MfaPolicyActivationResult(databaseId, Guid.NewGuid(), 2, 3, 4, Guid.NewGuid(), false, 2));
            }, TestContext.Current.CancellationToken);
        Assert.Equal(0, rc);
        Assert.Contains("mfa_policy_required", output.ToString(), StringComparison.Ordinal);
        Assert.Contains("\"futureUserProvisioningCovered\":false", output.ToString(), StringComparison.Ordinal);
        Assert.DoesNotContain("private-connection-value", output.ToString(), StringComparison.Ordinal);
        Assert.DoesNotContain("S-1-5-21", output.ToString(), StringComparison.Ordinal);
    }

    [Fact]
    public async Task InvalidStoreDoesNotActivatePolicyAndEmitsOnlySanitizedCode()
    {
        var output = new StringWriter(); bool touched = false;
        var rc = await MfaPolicyRequireAllCommand.Run(Config(), new StringReader(Confirmation), output, true,
            (_, _) => throw new MfaHostCompositionException("mfa_keystore_unreadable"),
            (_, _, _, _, _) => { touched = true; throw new InvalidOperationException(); }, TestContext.Current.CancellationToken);
        Assert.Equal(1, rc); Assert.False(touched);
        Assert.Equal("{\"status\":\"rejected\",\"code\":\"mfa_keystore_unreadable\"}" + Environment.NewLine, output.ToString());
    }

    [Fact]
    public async Task DomainRejectionIsReportedWithoutClaimingCommit()
    {
        var output = new StringWriter();
        var rc = await MfaPolicyRequireAllCommand.Run(Config(), new StringReader(Confirmation), output, true,
            (_, _) => Keys, (_, _, _, _, _) => throw new DomainError(403, "mfa_policy_owner_required"), TestContext.Current.CancellationToken);
        Assert.Equal(1, rc);
        Assert.DoesNotContain("committed", output.ToString(), StringComparison.Ordinal);
        Assert.Contains("mfa_policy_owner_required", output.ToString(), StringComparison.Ordinal);
    }

    private static async Task Reject(IConfiguration config, TextReader input, string code)
    {
        var output = new StringWriter();
        var rc = await MfaPolicyRequireAllCommand.Run(config, input, output, true,
            (_, _) => throw new InvalidOperationException("preflight reached"),
            (_, _, _, _, _) => throw new InvalidOperationException("database reached"), TestContext.Current.CancellationToken);
        Assert.Equal(1, rc);
        Assert.Contains(code, output.ToString(), StringComparison.Ordinal);
    }

    private static IConfiguration Config(string? field = null, string? value = null)
    {
        var settings = new Dictionary<string, string?>
        {
            ["MfaPolicy:DatabaseInstanceId"] = DatabaseId.ToString("D"), ["MfaPolicy:ActorId"] = ActorId.ToString("D"),
            ["MfaPolicy:ReaderSid"] = "S-1-5-21-1-2-3-1001", ["MfaKeyStore:InstallationId"] = StoreId.ToString("D"),
            ["MfaKeyStore:InstancesRoot"] = @"C:\ProgramData\RackClick\Instances", ["MfaKeyStore:Enabled"] = "true",
            ["ConnectionStrings:RackClick"] = "private-connection-value",
        };
        if (field is not null) settings[field] = value;
        return new ConfigurationBuilder().AddInMemoryCollection(settings).Build();
    }

    private sealed class TrapReader : TextReader
    {
        public override int Read() => throw new InvalidOperationException("input must not be read");
    }

    private static readonly IMfaKeyProvider Keys = new UnusedKeyProvider();
    private sealed class UnusedKeyProvider : IMfaKeyProvider
    {
        public byte[] GetKey(int version) => throw new InvalidOperationException("CLI seam must not read a key");
        public (int Version, byte[] Key) GetActiveKey() => throw new InvalidOperationException("CLI seam must not read a key");
    }
}
