Nothing in the repo gives costs: there are no Azure prices, no PayEx fee schedule and no team rates. So build cost below is in engineer-weeks, and running cost is in Azure resources and people's time, not dollars. The short answer: **about 9 to 13 engineer-weeks to build, of which about 4 to 6 are specific to the worker design. Running it costs almost nothing extra in Azure. The real running cost is people's time.**

## Build cost

**Needed for production under any option:**

| Work | Engineer-weeks |
|---|---|
| SQL repository, migrations, a way to save several changes in one transaction, approval that only applies while still pending, append-only audit table | 2–3 |
| PayEx client: shared HttpClient, idempotency header, timeout above 30 s, API key from Key Vault so it can be rotated without a deploy | 0.5 |
| Sessions in a shared store. `SessionStore.cs:9` keeps them in memory, so with three instances behind a load balancer, users get signed out unless requests stick to one instance | 0.5–1 |
| Daily reconciliation: read-only, PayEx report API, matching, report output | 1.5–2.5 |
| **Subtotal** | **4.5–7** |

The reconciliation estimate depends most on what PayEx's report API looks like. If there isn't one, it means parsing files by hand, and the estimate goes toward the top of the range or beyond.

**Specific to the outbox and worker:**

| Work | Engineer-weeks |
|---|---|
| `PaymentSubmission` table with a stored copy of the payload and a stable key; `ApprovalService` creates the row; tests using `FakeInvoiceRepository` | 0.5–1 |
| Worker: claiming rows with a lease, writing results only while holding the lease, counting attempts at claim time, backoff, telling one bad invoice apart from a PayEx-wide failure, circuit breaker, graceful shutdown, heartbeat | 1.5–2 |
| Admin resubmit that reuses the stored key and writes an audit row | 0.5 |
| Alerts: age of oldest `Pending` row, `Unknown` count, stale heartbeat; dashboard; check that Always On is enabled | 0.5–1 |
| PayEx stub with fault injection, tests against a real SQL Server, load test at 80 a minute | 1–1.5 |
| Runbook and one rehearsal (a day for the team) | 0.5 |
| **Subtotal** | **4.5–6.5** |

The minimum version of option 3 would have needed about 1 to 1.5 of those weeks anyway: the submission row, the stored payload and the resubmit action. So **choosing the worker added about 3.5 to 5 engineer-weeks.**

**Calendar.** Today is 29 October. If go-live is mid-January, and allowing for the December holidays, there are roughly 7 working weeks. Three engineers on this path is enough with a little room to spare. Two is tight. If time runs short:

1. Protect the worker, the alerts and the idempotency key first.
2. Next, cut the reconciliation back to a script someone runs by hand and checks each day, and automate it in February. Finance's monthly reconciliation covers the gap.
3. Don't cut the fault-injection tests. They're what makes the 3 a.m. failures from my last answer survivable.

The critical path runs through PayEx, not the team. Without answers on idempotency, key retention and the report API, about a third of this can't be finished.

## Running cost: Azure

Very little extra, because the design adds no new resources:

- **Compute:** the worker runs inside the existing three App Service instances and needs little CPU. Always On has no extra charge on Basic tier and above.
- **Azure SQL:**
  - Polling every couple of seconds from three instances is roughly 100,000 small indexed queries a day, which Azure SQL handles easily.
  - Data volume: about 40,000 submission rows a month plus attempts and audit rows. Seven years of audit data is a few million rows, probably low single-digit GB.
  - Ledger tables and long-term backup retention, if you use them for SOC 2, add some storage cost.
- **Monitoring:** a few log lines per invoice and a handful of alert rules. Small.
- **Service Bus:** unused by this design. It costs whatever it costs now. Decide whether to keep it for notifications or remove it.
- **PayEx:** fees per payment don't change. Find out whether they charge per API call, since retries and status lookups would add calls.

## Running cost: people

This is where the money goes:

| Activity | Rough effort | What drives it |
|---|---|---|
| Resolving `Unknown` submissions | Near zero most months; a cluster after any PayEx incident | Whether PayEx honours the key. If it doesn't, every timeout needs a person. |
| Reading the daily reconciliation report | About 10–15 min a day, more at month end | How noisy the report is. Tune the settling period early. |
| PayEx key rotation, API version changes, dependency upgrades | A few days a quarter | PayEx's change schedule |
| Rehearsal | Half a day for the team each quarter | Keeps the runbook honest as people rotate |
| Onboarding | 2–3 days per engineer to understand leases and keys well enough to be on call | Matters now with two new engineers |
| SOC 2 evidence | Hours a quarter: reconciliation reports, access reviews for Admin resubmit, change records | The outbox makes this cheaper, because evidence is a query rather than reconstruction |

There's also a risk: badly tuned alerts will page people at night. The paging rule from my last answer (page only when the cause is ours, not when PayEx is down) is what keeps this cheap.

## What you get back

The extra 3.5 to 5 engineer-weeks buy two things: approvals stay fast when PayEx is slow (INC-2041), and lost or duplicate payments are prevented rather than discovered afterwards. One duplicate payment on a large invoice, and the finance time spent recovering it, probably costs more than the extra build.

## What would change these numbers

- **PayEx has no idempotency key:** build cost stays the same. Running cost rises a lot, because every timeout becomes manual work.
- **PayEx has no report API:** reconciliation could double in size.
- **The shared session store, or the SQL work generally, is already planned and staffed elsewhere:** take it out of the subtotal for work needed under any option.

I can fold these estimates into the ADR with the failure analysis, with assumptions and open questions listed separately so they can be updated as PayEx answers.