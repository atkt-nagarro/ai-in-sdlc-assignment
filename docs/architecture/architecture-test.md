# Architecture test: what the Domain assembly may reference

## The rule

AGENTS.md says `InvoiceApp.Domain` holds "business rules, no web or storage
code". Nothing enforced that. `DomainDependencyTests` now checks it through
the Domain assembly's references: each must be named `System`, `System.*`,
`netstandard` or `mscorlib`, and none may be `System.Net`, `System.Data` or
anything under them. Anything else is a failure: ASP.NET Core, EF Core,
SqlClient, Azure SDKs, or `InvoiceApp.Api` itself.

Test: [`backend/tests/InvoiceApp.Tests/DomainDependencyTests.cs`](../../backend/tests/InvoiceApp.Tests/DomainDependencyTests.cs)

## The command

```
dotnet test backend/InvoiceApp.sln --filter "Category=Architecture"
```

CI already runs it, because `.github/workflows/ci.yml` runs every test in the
solution. The test project sets `RollForward=Major`, so the same command also
runs on a machine that only has a newer .NET, as mine does (.NET 10).

## Why this rule and not another

The next two changes to this service are a database and a PayEx client. Both
pull in exactly the dependencies this rule forbids. INC-2041 shows what
happens when the payment call is wired in wherever it is convenient: release
2.14.0 put the PayEx call inside the approval request and created a new
`HttpClient` per call (`ops/incidents/INC-2041/deploy-diff.patch`). Keeping
Domain free of HTTP and storage assemblies means the code that uses them sits
outside it, in `InvoiceApp.Api`, which is where the outbox dispatcher in
ADR-001 has to live anyway. The test reads only Domain's references, so it
would not have caught 2.14.0 itself.

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
reference does not show up, which is acceptable: it does no harm until code
uses it, and then it shows up. The bigger gap is that the test judges each
reference by name. Any name starting `System.` passes unless it falls under
`System.Net` or `System.Data`, and storage written with base-library types
such as `System.IO` passes too.

The next rule I would add, once a PayEx client exists, is that no controller
depends on it: only the outbox dispatcher may call PayEx. It is not written
yet, because a test for a type that does not exist would pass for the wrong
reason.
