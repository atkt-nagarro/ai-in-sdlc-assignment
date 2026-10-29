# Target state: once persistence and PayEx are in

This is the service after the January work, following [ADR-001](../adr/ADR-001-exactly-once-payex-submission.md). **Green boxes exist in the code today. Dashed amber boxes do not exist yet.** Grey is external.

## Container view

```mermaid
flowchart LR
    user(["Approver or Admin"])
    finance(["Finance"])

    subgraph appsvc["Azure App Service, 3 instances (planned hosting)"]
        ui["Static web UI (exists)"]
        api["InvoiceApp.Api controllers (exists)"]
        domain["ApprovalService (exists)<br/>plus second approver over $1,000 (planned, UC-1)"]
        dispatcher["PayEx dispatcher<br/>BackgroundService (planned)"]
        recon["Daily reconciliation<br/>read-only (planned)"]
    end

    sql[("Azure SQL (planned)<br/>Invoices, ApprovalAudit append-only 7 years,<br/>PaymentSubmission outbox")]
    sessions[("Shared session store (planned)<br/>SessionStore is in memory today")]
    kv["Key Vault: PayEx key (planned)"]
    insights["Application Insights alerts (planned)<br/>oldest unpaid approval, Unknown, heartbeat"]
    sb["Service Bus topic (provisioned, unused)<br/>notifications only, later"]
    payex["PayEx API (external)"]

    user --> ui
    user --> api
    api --> domain
    api --> sessions
    domain -->|"one transaction: invoice, audit, outbox row"| sql
    dispatcher -->|"claim due rows with a lease"| sql
    dispatcher -->|"POST payment, idempotency key"| payex
    dispatcher -->|"API key"| kv
    dispatcher --> insights
    recon -->|"daily report"| payex
    recon -->|"compare"| sql
    recon -->|"mismatch report"| finance
    sql -.->|"approval events from the same outbox, later"| sb

    classDef planned stroke-dasharray: 6 4,fill:#fff7e6,stroke:#b7791f,color:#16202a
    classDef exists fill:#e6f4f1,stroke:#0f766e,color:#16202a
    classDef external fill:#eef1f5,stroke:#4f5b67,color:#16202a
    class dispatcher,recon,sql,sessions,kv,insights,sb planned
    class ui,api,domain exists
    class payex external
```

| Element | Status | Source |
| --- | --- | --- |
| Static web UI | Exists | `backend/src/InvoiceApp.Api/wwwroot/` |
| API controllers and sign-in | Exists. Demo users come from `appsettings.json`, which is not fit for production. | `backend/src/InvoiceApp.Api/Controllers/`, `Auth/` |
| ApprovalService | Exists. It gains the second-approver rule for invoices over $1,000 (UC-1), and writes the outbox row on final approval. | `backend/src/InvoiceApp.Domain/ApprovalService.cs` |
| App Service, 3 instances | **Planned** | Scenario facts, `ops/incidents/INC-2041/README.md` |
| Azure SQL: Invoices, ApprovalAudit, PaymentSubmission | **Planned**. Today the store is an in-memory list. | ADR-001, decision step 1 |
| PayEx dispatcher | **Planned** | ADR-001, steps 3 to 6 |
| Daily reconciliation | **Planned** | ADR-001, step 7 |
| Shared session store | **Planned**. `SessionStore` keeps tokens in process memory, which breaks with three instances. | ADR-001, consequences |
| Key Vault for the PayEx key | **Planned**. The key was rotated on 23 January, so it must change without a deploy. | ADR-001, cost |
| Application Insights alerts | **Planned** | ADR-001, step 8 |
| Service Bus topic | Provisioned, unused. Later it carries notifications from the same outbox. Never in the payment path. | ADR-001, decision |
| PayEx | External | Scenario facts |

## Sequence: approving an invoice

```mermaid
sequenceDiagram
    autonumber
    actor Approver
    box rgb(230,244,241) Exists today
        participant API as ApprovalsController
        participant Svc as ApprovalService
    end
    box rgb(255,247,230) Planned, not built yet
        participant DB as Azure SQL
        participant W as PayEx dispatcher
        participant R as Daily reconciliation
    end
    participant P as PayEx (external)

    Approver->>API: POST /api/approvals/{id}/approve
    API->>Svc: Approve(id, approver)
    Svc->>DB: one transaction: invoice to Approved only if still pending,<br/>ApprovalAudit row, PaymentSubmission row with key and payload
    alt invoice no longer pending
        DB-->>API: 0 rows updated
        API-->>Approver: 409
    else committed
        API-->>Approver: 200, Approved, awaiting PayEx
    end
    loop every 2 s on each instance
        W->>DB: claim due rows, READPAST and UPDLOCK, 2 min lease, attempts + 1
    end
    W->>P: POST stored payload with the idempotency key, 40 s timeout
    alt success
        P-->>W: reference
        W->>DB: Submitted with reference, only while holding the lease
    else 400 or 422
        W->>DB: Rejected, routed to finance
    else timeout
        W->>DB: Unknown
        W->>P: look up by key or reference before any retry
    else 401, 403, 429 or 5xx
        W->>W: open circuit, leave rows untouched, alert
    end
    R->>P: daily report, read-only
    R->>DB: compare Submitted and Unknown, report mismatches
```

## What changes compared with today

- The approve request no longer does anything external. It commits one transaction and returns, so a slow or broken PayEx cannot slow approvals (INC-2041).
- "Only pending invoices can be decided" moves from an in-memory check (`EnsurePending`) to a conditional update in SQL. That makes it hold across three instances and concurrent clicks.
- Every payment attempt reuses one stored key and one stored payload. The dispatcher claims rows with a lease, so two instances never send the same row at once.
- Alerts watch outcomes (the oldest unpaid approval), not just whether the process is running. That is the lesson of INC-2047.

Not shown here: the notification worker from INC-2047 and UC-2 partial approval. Neither changes this path, except that the payload carries the approved amount.
