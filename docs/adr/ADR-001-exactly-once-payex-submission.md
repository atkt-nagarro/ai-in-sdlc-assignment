# ADR-001: Getting each approved invoice to PayEx exactly once

- **Status:** Accepted, 29 October 2026
- **Owner:** senior engineer, Invoice Approval
- **Agent session:** [docs/agent-sessions/02-adr](../agent-sessions/02-adr/). Four turns, verbatim.

## Context

In January this service starts paying approved invoices through PayEx.

- **Volume:** about 40,000 invoices a month. 60% (24,000) land in the last three working days, which is about 8,000 a day. The peak is around 80 approvals a minute.
- **PayEx:** returns a reference on success. It times out at 30 s, and a timeout does not tell us whether the payment went through.
- **Platform:** three App Service instances, Azure SQL (not built yet; today's store is in memory), and an Azure Service Bus that, according to the brief, nothing uses. The INC-2047 pack disagrees: it shows the planned deployment publishing invoice events to three subscriptions. Either way, Service Bus stays out of the payment path.
- **Compliance:** SOC 2 Type II in six months. Approval actions are auditable for seven years.
- **Team:** six engineers, two new to this code, on a one-week rotation.

INC-2041 is the warning. Release 2.14.0 called PayEx inside the approve request (`deploy-diff.patch:85-86`) with a fresh `HttpClient` per call. Under month-end load the sockets ran out, calls hung for up to the default 100 s, and approvals failed, while PayEx itself reported no incident.

## The constraint that decides it

We cannot get exactly-once on our own. A timed-out call may have been paid. What we can build is:

1. never lose an approval's payment intent,
2. deliver it at least once,
3. make every repeat carry the same identity, so PayEx can discard duplicates.

That third part needs PayEx to honour an idempotency key, or at least let us look a payment up by our reference. Nothing in hand says it does. So the design must be safe in both worlds.

## Options

| | Idempotency key + dedupe table | Transactional outbox + worker | Optimistic submit + nightly reconciliation |
| --- | --- | --- | --- |
| Lost payment (approved, never sent) | Possible: crash between commit and call, nothing retries | Prevented: intent committed with the approval, worker retries | Found up to a day later |
| Duplicate payment | Prevented only if PayEx honours the key | Same, and retries reuse one stored key and payload | Found after the money has left |
| Approval depends on PayEx | Yes, if called inline (INC-2041) | No | Yes |
| Build | Low | Medium | Low at first, grows with matching rules |
| On-call | Quiet, but losses are silent | Medium, alertable | Month-end manual fixes for whoever is on call |

Option 1 done properly becomes option 2: store the key with the approval and add something that picks up unsent rows. Option 3 is a good safety net and a poor primary mechanism.

## Decision

**Transactional outbox in Azure SQL with a dispatcher worker.** Every submission carries a stable idempotency key, and a daily reconciliation runs as a detective control. Service Bus stays out of the payment path.

1. **One transaction on approval:**
   - the invoice moves to Approved only if it is still `PendingApproval` (a conditional update, otherwise 409)
   - an append-only `ApprovalAudit` row is written
   - a `PaymentSubmission` row is written, unique on `InvoiceId`, holding a GUID idempotency key and a snapshot of the exact payload
   - all three go through `IInvoiceRepository`, implemented by a SQL repository in the API layer, so Domain stays free of storage code (the architecture test)
2. **Only final approvals create a submission.** Under UC-1, an invoice over $1,000 is final after its second approver. Under UC-2, the payload carries the approved amount, not the invoiced one.
3. **The dispatcher** is a `BackgroundService` on each instance (Always On enabled).
   - It claims rows atomically (`UPDATE TOP (n) … OUTPUT` with `READPAST, UPDLOCK, ROWLOCK`), with a 2-minute lease.
   - The attempt count goes up at claim time.
   - It writes a result only if it still holds the lease.
4. **The PayEx client** is a typed `IHttpClientFactory` client with a 40 s timeout, longer than PayEx's 30 s so we see PayEx's own answer. It resends the stored payload bytes and key on every attempt. It reads the API key from Key Vault, so a rotation like the one on 23 January needs no deploy.
5. **Outcomes:**

   | PayEx response | Status | What happens |
   | --- | --- | --- |
   | Success | `Submitted` | Reference stored |
   | 400/422 | `Rejected` | Goes to finance with an owner |
   | Timeout | `Unknown` | See the next item |
   | 401/403/429/5xx | Unchanged | PayEx-wide failure: the circuit opens and the rows are left alone |
6. **`Unknown`:**
   - If PayEx dedupes on the key, retry with the same key inside its retention window.
   - If PayEx doesn't dedupe but supports a lookup by our reference, look it up first.
   - If neither exists, send it to a manual queue. Never resend blind.
7. **Reconciliation** runs daily, read-only, and reports only. It allows a settling period so in-flight rows are not flagged.
8. **Alerts on outcomes, not liveness,** in Application Insights:
   - oldest `Pending`/`Unknown` older than 15 minutes in business hours
   - any `Unknown`
   - a stale worker heartbeat
   - circuit open

At the worst case, where every call hits the 30 s timeout, keeping up with 80 a minute needs 80 × 0.5 = 40 calls in flight, about 14 per instance. That sets the dispatcher's concurrency cap.

## The strongest objection

"With two engineers new to the code, a background worker that can stop silently is harder to run than a synchronous call that fails loudly. INC-2047's worker logged `Health check ok … processed in last 12h: 0` for more than a day."

I take that seriously. It is why the alerts watch the age of the oldest unpaid approval, not whether the process is up. But the loud synchronous call already failed us once: INC-2041 turned a fault in the PayEx call into an approvals outage at month end. A synchronous design also cannot resolve a timeout without the same machinery: it still needs a stored key, a status lookup and a retry path. So it ends up with the outbox's complexity and none of its isolation. I will also make the worker boring to operate:

- a runbook whose first rule is "`Unknown` means look it up, never resend"
- an Admin resubmit that always reuses the stored key
- one staging rehearsal before the rotation, run by a new engineer against a fault-injecting PayEx stub

## How it fails at 3 a.m. on the last working day

Traffic is near zero, one person is on call, and the busiest day starts at 9.

| Failure | How we notice | Mitigation |
| --- | --- | --- |
| App unloaded overnight (no Always On) or the worker loop dies quietly | Heartbeat older than 5 min; oldest-pending age | Always On checked in the pipeline; heartbeat row |
| PayEx key rotated or expired (last rotation 23 Jan), so every call returns 401 | Circuit-open alert | 401/403/429/5xx never mark invoices rejected; the rows wait |
| Lease shorter than a slow call, so two instances send the same row | Duplicate-attempt count | Lease 2 min > 40 s timeout; result written only by the lease holder |
| PayEx outage outlasts its key retention, so a retry becomes a new payment | `Unknown` count | Retry window kept inside retention, then `Unknown` → manual |
| Payload changed between attempts (for example `CustomerName`, or the 2.15.0 supplier contact fields if they reach the payload, edited after approval) | PayEx rejects the key/payload mismatch | Send the stored snapshot, never rebuild |
| Tired engineer "just resends" with a new key | Audit row on every resubmit | Resubmit reuses the key; no direct table edits |
| Backlog at 09:00 after a slow night | Oldest-pending age | Drains at about 2,400 a minute when PayEx answers in 1 s; capped and honours `Retry-After` |

## Cost

**Build.** 9 to 13.5 engineer-weeks in total. These are the agent's estimates (turn 4); I checked each line and kept them. Of that, 4.5 to 6.5 weeks are specific to the outbox and worker: table, worker with leases and backoff, admin resubmit, alerts, the PayEx stub and load test at 80 a minute, and the runbook and rehearsal. The other 4.5 to 7 weeks are needed under any option: the SQL repository and transactions, the PayEx client, a shared session store, and reconciliation. The leanest safe version of option 3 would need 1 to 1.5 of those weeks anyway, so the worker adds about 3.5 to 5 weeks. These are estimates, not measurements. The brief says only "January", so I plan for the worse case, a go-live in the first week of January. From 29 October, with the holidays out, that leaves about 7 working weeks. At about 60% focus, once on-call weeks and reviews are taken out, 13.5 engineer-weeks needs three engineers. Two are enough for a mid-January go-live (about 9 weeks), or if reconciliation is automated in February.

**Run.** Computed from the volumes:

- **Rows:** 40,000 submission rows a month, which is 3.36 million over seven years. At about 1 KB each with the payload snapshot (assumed), that is roughly 3.4 GB, plus a similar order for audit rows.
- **Polling:** one claim query every 2 s per instance is 3 × 43,200 = 129,600 small indexed queries a day.
- **Azure:** one Key Vault secret and no other new resource. The worker runs on the existing plan, which must be Basic or higher for Always On, and Service Bus is unchanged.
- **People:** 10 to 15 minutes a day on the reconciliation report, more at month end. Near-zero `Unknown` work if PayEx dedupes; one manual case per timeout if it does not.

## Consequences

- Approvals no longer wait on PayEx. Users see "Awaiting PayEx" until a reference arrives.
- The seven-year audit question becomes a query over `ApprovalAudit` and `PaymentSubmission`, not a reconstruction from logs.
- `SessionStore` is in memory (`SessionStore.cs:9`), so three instances need a shared session store or sticky sessions. This is in the build estimate above.
- The in-memory repository's lock does not make approval atomic today: `Approve` reads, changes and saves in separate calls. The conditional update in step 1 is what closes that gap.

## What would make me revisit this

- PayEx confirms neither idempotency keys nor lookup by reference. Every timeout then becomes manual work, and finance must agree that process before go-live.
- The oldest-pending age goes over 15 minutes on more than one month-end, or the backlog is not empty by 18:00 on the last working day.
- Reconciliation finds any duplicate or missing payment.
- Peak volume passes 10× (800 a minute). Then a queue between the outbox and the dispatcher earns its keep.
- A second consumer needs approval events. Publish them through Service Bus from the same outbox.
- The service moves off App Service, which changes where the worker can live.

## Questions PayEx must answer before build

1. Do you accept an idempotency key, in which header, and for how long?
2. How do you treat two concurrent requests with the same key?
3. Can we look up a payment by our invoice reference?
4. What are your rate limits?
5. How far behind is your reporting API?

## Where the agent was wrong or useless

I used Claude Code (`claude-opus-5-5`) as a sparring partner in four turns:

1. trade-offs
2. a stated preference for option 3
3. the 3 a.m. failure
4. cost

It was useful on detail. I adopted:

- the payload snapshot
- its 4xx-versus-PayEx-wide classification
- a lease longer than the timeout
- Always On
- Key Vault for the key
- its catch that `SessionStore` breaks with three instances

The options table, the 3 a.m. failure list and the build estimate started from its answers. I checked and reworked each of them. It was wrong in ways that matter:

1. **It moved its recommendation under social pressure, with no new evidence.** In turn 1 it recommended the outbox. When I said I preferred option 3 because the team is new, it answered "**Yes, partly.** I can support option 3 for January", conceding "I won't argue with your read of the team". Its "minimum safe version of option 3" was the outbox table plus a nightly job. That is still a background process, just with 24-hour detection instead of minutes. The concession was about tone, not engineering.
2. **It cited my own eval fixture as production history.** Turn 1 names "the retry pattern in `ops/evals/cases/case-11.diff`" as evidence of how release 2.14.3 retries. case-11 is a review case I wrote for task 4. `recent-changes.md` says only "Retry policy for the PayEx client, pooled handler" and nothing about idempotency. An agent with repository access reads everything, fixtures included.
3. **It read a coincidence as user behaviour.** It said users were "clicking approve again" in INC-2041, citing INV-41988 (500 at 10:21:29, then 200 at 10:24:11). The two lines exist. But across the window, 57 of 279 invoice IDs appear more than once. For 52 of those 57, the repeat follows a successful 200, which `EnsurePending` would refuse. Random IDs drawn from INV-41000 to INV-41998 would produce about 48 such IDs. That is not people retrying. The real risk of repeat approvals stands. This evidence does not show it.
4. **It overclaimed its own alert.** It said alerting on the oldest unpaid approval "would have caught INC-2047 within minutes". INC-2047 was the notification subscription filter (`InvoiceApproved` versus `invoice.approved`). A PayEx backlog alert never sees that path.
5. **It got the concurrency of today's code wrong.** It said "the in-memory lock hides this today". It does not. `InMemoryInvoiceRepository` locks each call, while `ApprovalService.Approve` does `GetById`, then the status change, then `Update` as separate steps on a shared object. Two concurrent approvals can both pass `EnsurePending` now.
6. **It misstated SOC 2.** It said "auditors expect controls that prevent wrong payments, not just ones that find them". SOC 2 does not rank preventive above detective controls; reconciliation is a normal control. The real case against option 3 is the cost of recovering money from a supplier.
7. **Two numbers were off:**
   - "The queue never shrinks during business hours" assumes the 80-a-minute peak lasts all day. The month-end average is about 8,000 a day, roughly 13 to 17 a minute over a working day, so a backlog drains outside the peak.
   - It assumed a mid-January go-live but counted "roughly 7 working weeks". That is the figure for early January; mid-January gives about 9. It never asked which date is real, and its staffing advice depends on it.
