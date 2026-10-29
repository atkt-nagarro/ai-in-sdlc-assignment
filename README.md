# NAGP AI in SDLC: Home Assignment 2

The Invoice Approval service goes tier-2 in January, with a 24x7 rotation, a published SLO and PayEx payments. This repository holds what I would want to own before that happens. Every measured number comes from a script or a cited file in this repository; estimates are labelled as such.

| # | Hand-in item | Where |
| --- | --- | --- |
| 1 | Mermaid source for the as-built and target diagrams, with the citation list and the inferred-items list | [as-built.md](docs/architecture/as-built.md), [target-state.md](docs/architecture/target-state.md), [diagrams/](docs/architecture/diagrams/) |
| 2 | One architecture test, with the command that runs it | [DomainDependencyTests.cs](backend/tests/InvoiceApp.Tests/DomainDependencyTests.cs), [architecture-test.md](docs/architecture/architecture-test.md) |
| 3 | The exactly-once decision record, including *Where the agent was wrong or useless* | [ADR-001](docs/adr/ADR-001-exactly-once-payex-submission.md) |
| 4 | One-page autonomy policy, with the day-one level stated | [autonomy-policy-incident-summaries.md](docs/policy/autonomy-policy-incident-summaries.md) |
| 5 | The two added evaluation cases, and results for three runs plus the changed-variable run | [case-11](ops/evals/cases/case-11.diff), [case-12](ops/evals/cases/case-12.diff), [RESULTS.md](ops/evals/RESULTS.md), [results.csv](ops/evals/results.csv) |
| 6 | The risk audit, with a decision recorded | [lethal-trifecta-audit.md](docs/security/lethal-trifecta-audit.md) |
| 7 | The measurement plan, with the two numbers captured | [measurement-plan.md](docs/metrics/measurement-plan.md) |
| 8 | The 8 to 10 minute demo video | [demo.mp4](docs/demo/demo.mp4), 8 min 41 s (narration: [narration-script.md](docs/demo/narration-script.md); plan: [demo-script.md](docs/demo/demo-script.md)) |
| 9 | AI augmentation logs | [ai-augmentation-log.md](docs/ai-augmentation-log.md), raw sessions in [docs/agent-sessions/](docs/agent-sessions/) and [ops/evals/runs/](ops/evals/runs/) |

## Check it yourself

```
dotnet test backend/InvoiceApp.sln                                   # 8 tests, including the architecture rule
dotnet test backend/InvoiceApp.sln --filter "Category=Architecture"  # the architecture rule on its own
python3 docs/architecture/check_citations.py                         # every as-built citation resolves
python3 docs/architecture/check_agent_citations.py                   # every citation in the agent's draft resolves
python3 docs/metrics/compute_baseline.py                             # baseline numbers
python3 ops/evals/summarize.py                                       # eval rates and intervals
```

The test project sets `RollForward=Major`, so the `dotnet test` commands also run on a machine that only has a newer .NET, such as .NET 10. Running the app itself on such a machine needs `DOTNET_ROLL_FORWARD=Major dotnet run --project backend/src/InvoiceApp.Api`.

---

## Invoice Approval demo app

A small invoice approval app used for live AI-in-SDLC demos. It is deliberately simple: a .NET 8 API, a plain web UI, and an in-memory store, so it runs with one command and no database.

## Run it

```
dotnet run --project backend/src/InvoiceApp.Api
```

Open http://localhost:5000 and sign in:

| User | Password | Role |
| --- | --- | --- |
| `demo.approver` | `ChangeMe123!` | Approver |
| `demo.admin` | `ChangeMe123!` | Admin |

These are demo accounts for a local, in-memory app. They are not real credentials.

## What it does

1. Create an invoice (it starts as a draft).
2. Submit it for approval.
3. An approver approves it, or rejects it with a reason.

Invoices move through Draft, Pending Approval, then Approved or Rejected.

## Tests

```
dotnet test backend/InvoiceApp.sln
```

## Project layout

```
backend/
  src/InvoiceApp.Domain   business rules
  src/InvoiceApp.Api      controllers, sign-in, web UI (wwwroot)
  tests/InvoiceApp.Tests  xUnit tests
docs/use-cases            short feature briefs
AGENTS.md                 conventions for AI coding agents
```

## Use cases

- [UC-1 Bulk invoice approval](docs/use-cases/UC-1-bulk-approval.md)
- [UC-2 Partial approval](docs/use-cases/UC-2-partial-approval.md)
