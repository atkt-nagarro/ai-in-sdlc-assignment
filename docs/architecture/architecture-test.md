# Architecture test: the Domain project stays free of web, HTTP and storage code

## The rule

AGENTS.md says `InvoiceApp.Domain` holds "business rules, no web or storage
code". Nothing enforced that. `DomainDependencyTests` now does: the Domain
assembly may reference the base class library only, and not the parts of it
that reach networks or databases (`System.Net*`, `System.Data*`). Anything
else is a failure: ASP.NET Core, EF Core, SqlClient, Azure SDKs, or
`InvoiceApp.Api` itself.

Test: [`backend/tests/InvoiceApp.Tests/DomainDependencyTests.cs`](../../backend/tests/InvoiceApp.Tests/DomainDependencyTests.cs)

## The command

```
dotnet test backend/InvoiceApp.sln --filter "Category=Architecture"
```

CI already runs it, because `.github/workflows/ci.yml` runs every test in the
solution. On a machine that has only the .NET 10 SDK, as mine does, the net8.0
test host needs `DOTNET_ROLL_FORWARD=Major` in front of the command.

## Why this rule and not another

The next two changes to this service are a database and a PayEx client. Both
pull in exactly the dependencies this rule forbids. INC-2041 shows what
happens when the payment call is wired in wherever it is convenient: release
2.14.0 put the PayEx call inside the approval request and created a new
`HttpClient` per call (`ops/incidents/INC-2041/deploy-diff.patch`). Keeping
Domain free of HTTP and storage forces both behind interfaces in the API
layer, which is where the outbox dispatcher in ADR-001 has to live anyway.

The rule also catches the violation the compiler does not. Domain's project
file references no packages, so nobody can use EF Core or ASP.NET Core
types there without editing the `.csproj`. But `HttpClient` is part of the
shared framework, and `ImplicitUsings` already imports `System.Net.Http`. A
one-line change compiles cleanly and only this test notices.

## Evidence that it runs and bites

Captured in [`architecture-test-run.txt`](architecture-test-run.txt):

1. As committed: 1 passed. The only reference Domain has today is
   `System.Runtime, Version=8.0.0.0` (section 4 of the capture).
2. With `private static readonly HttpClient PayEx = new();` added to
   `ApprovalService`, the build still succeeds and the test fails with
   `InvoiceApp.Domain must not depend on web, HTTP, storage or application
   code, but it references: System.Net.Http`.
3. Reverted: 1 passed, and the full suite is 8 passed.

## How it works, and its limits

It reads `typeof(ApprovalService).Assembly.GetReferencedAssemblies()`, the
assembly references the compiler actually emitted. That makes it cheap and
needs no new package. The other side of that is that an unused project
reference does not show up. That is acceptable, because an unused reference
does no harm until something uses it, and then the test fails.

The next rule I would add, once a PayEx client exists, is that no controller
depends on it: only the outbox dispatcher may call PayEx. It is not written
yet, because a test for a type that does not exist would pass for the wrong
reason.
