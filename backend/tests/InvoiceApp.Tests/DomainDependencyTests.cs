using InvoiceApp.Domain;
using Xunit;

namespace InvoiceApp.Tests;

/// <summary>
/// Structural rule from AGENTS.md: the Domain project holds business rules, no web or storage code.
/// It may reference the base class library only, and not the parts of it that reach networks or databases.
/// </summary>
public class DomainDependencyTests
{
    private static readonly string[] ForbiddenBaseLibraryAreas = { "System.Net", "System.Data" };

    [Fact]
    [Trait("Category", "Architecture")]
    public void Domain_HasNoWebHttpOrStorageDependencies()
    {
        var violations = typeof(ApprovalService).Assembly
            .GetReferencedAssemblies()
            .Select(reference => reference.Name ?? string.Empty)
            .Where(name => !IsBaseLibrary(name) || ForbiddenBaseLibraryAreas.Any(area => IsInArea(name, area)))
            .OrderBy(name => name)
            .ToList();

        Assert.True(
            violations.Count == 0,
            "InvoiceApp.Domain must not depend on web, HTTP, storage or application code, but it references: "
            + string.Join(", ", violations));
    }

    private static bool IsBaseLibrary(string assemblyName) =>
        assemblyName is "System" or "netstandard" or "mscorlib"
        || assemblyName.StartsWith("System.", StringComparison.Ordinal);

    private static bool IsInArea(string assemblyName, string area) =>
        assemblyName == area || assemblyName.StartsWith(area + ".", StringComparison.Ordinal);
}
