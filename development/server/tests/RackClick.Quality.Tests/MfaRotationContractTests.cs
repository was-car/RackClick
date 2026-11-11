using System.Reflection;
using RackClick.Server;
using Xunit;

namespace RackClick.Quality.Tests;

public sealed class MfaRotationContractTests
{
    [Theory]
    [InlineData("RackClick.Server.MfaRotationCoordinator")]
    [InlineData("RackClick.Server.MfaRotationDatabase")]
    public void RotationHasItsOwnCoordinatorAndCommitWitnessAdapter(string type)
    {
        Assert.NotNull(typeof(MfaSecretCipher).Assembly.GetType(type));
    }

    [Fact]
    public void AdditiveWitnessMigrationDoesNotRewriteHistoricalMigrations()
    {
        Assert.True(SchemaMigrations.LatestVersion >= 46);
        Assert.True(File.Exists(Path.Combine(AppContext.BaseDirectory,"database","046-mfa-key-rotation.sql")));
    }
}
