At 3 a.m. on the last working day, approval traffic is near zero. The risks are that one person is on call, possibly one of the new engineers, and the busiest day of the month starts in about five hours. Any changes to production need the incident commander to approve them.

Ranked by how likely each failure is multiplied by how much damage it does:

## 1. The worker stops and nothing alerts

- **How it happens:** with no HTTP traffic overnight, App Service unloads the app unless Always On is enabled, and the background worker stops with it. A config change or an exception that is caught and logged inside the loop gives the same result.
- **What on-call sees:** nothing. The health check stays green, as in INC-2047 ("Health check ok. Messages processed in last 12h: 0"). Approvals keep working, so nobody notices until suppliers call.
- **Build now:**
  - Enable Always On, and add a check to the pipeline that fails if it's off.
  - Alert on the age of the oldest `Pending` row, not on whether the worker is alive.
  - Have the worker record a heartbeat in SQL even when there's no work, and alert if the heartbeat is stale.

## 2. A problem across all of PayEx is recorded as thousands of rejected invoices

- **How it happens:** an expired or rotated API key (the key was last rotated on 23 January), a certificate problem or a PayEx outage makes every call return 401, 403 or 5xx. A worker that treats any 4xx as "this invoice is bad" marks the whole backlog `Rejected` within minutes.
- **What on-call sees:** finance arrives at 8 a.m. to a large queue of rejected invoices with nothing actually wrong with them, and cleaning it up means editing payment records by hand.
- **Build now:**
  - Treat only 400 and 422 as a problem with that one invoice.
  - Treat 401, 403, 429 and 5xx as a problem with PayEx. Open a circuit breaker, stop claiming rows and raise one alert. Don't touch the invoices.

## 3. Two instances submit the same invoice at the same time

- **How it happens:** the lease on a claimed row is shorter than a slow PayEx call (up to 35 to 40 seconds with our timeout). The lease expires, another instance claims the row and sends the same idempotency key while the first call is still running. A platform recycle in the middle of a call (INC-2041 had one at 10:03) creates the same overlap.
- **What happens next:** depends on how PayEx handles two requests with the same key at once. It might return the original result, return a 409 meaning "already in progress", or, in the worst case, process both.
- **Build now:**
  - Make the lease at least the client timeout plus a margin, about 2 minutes.
  - Write the result only if the worker still holds the lease, so a call that finishes late can't overwrite a newer one.
  - Increase the attempt count when a row is claimed, not when the call finishes, so a row that crashes the worker can't loop forever.
  - Ask PayEx how it handles concurrent requests with the same key.

## 4. Retries continue after PayEx forgets the key

- **How it happens:** PayEx is down overnight, the worker keeps retrying with backoff, and the outage lasts longer than PayEx remembers keys. The next retry looks like a new payment.
- **What on-call sees:** it looks like a clean recovery. The duplicate payments surface days later.
- **Build now:**
  - Keep the retry window well inside PayEx's key retention period, then move the row to `Unknown` for someone to resolve.
  - Until PayEx states its retention period in writing, assume it's short.

## 5. The reconciliation job causes duplicates

- **How it happens:** the daily job runs overnight while the worker is still clearing a backlog. It sees rows still being worked on, or rows PayEx hasn't put in its report yet, flags them as missing, and resubmits them.
- **Build now:**
  - The reconciliation job only reads and reports. It never submits.
  - It ignores rows newer than a settling period and allows for any delay in PayEx's report.
  - It uses the same definition of "day" as finance (UTC or local time), so invoices approved just before midnight aren't flagged as mismatches every month.

## 6. A tired person makes it worse

- **How it happens:** on-call follows the instinct to "just resubmit the stuck ones", using a direct SQL update or a resubmit action that generates a new key.
- **Build now:**
  - Give Admins a resubmit action that always reuses the stored key and writes an audit row (SOC 2).
  - Make the runbook say plainly: never edit the outbox table directly, and `Unknown` means look it up in PayEx, not resend.
  - Under the out-of-hours rules in INC-2047, anything beyond pausing the worker needs the incident commander's approval anyway.

## 7. The payload changes between attempts

- **How it happens:** the worker rebuilds the PayEx request from the current invoice on each attempt. The supplier fields added in 2.15.0 are edited between attempts, PayEx sees the same key with a different payload, and rejects it, or worse.
- **Build now:** store the exact payload in the outbox row when the invoice is approved, and send those same bytes on every attempt.

## 8. The morning backlog

- **How it happens:** the second-to-last day (the INC-2041 day) left a backlog, or PayEx was slow overnight.
- **Clearing time:** at about 1 second per call with 40 calls in flight, the queue clears at roughly 2,400 a minute, so it's gone in minutes. At 30-second timeouts it clears at about 80 a minute, the same rate as peak arrivals, so the queue never shrinks during business hours.
- **When PayEx recovers:** firing the whole backlog at once can trigger 429s.
- **Build now:** cap concurrency per instance, honour `Retry-After`, and find out PayEx's rate limits.

## Two smaller ones

- **Azure SQL failover:** if PayEx succeeds but saving the reference fails, don't retry straight away. Let the lease expire and resend with the same key.
- **Deployments overnight:** during a slot swap, old and new code both run the worker, so database migrations must work with both versions.

## Paging at 3 a.m.

Only page when someone can act. A backlog that is growing while PayEx is healthy is our fault: page. A backlog caused by PayEx being down can't be fixed at 3 a.m.: open the circuit breaker, notify, and escalate at the start of business, unless the payment cut-off is at risk. Ask finance what that cut-off time is.

## Before January

Run a rehearsal on staging with a PayEx stub that:

- times out after accepting the payment
- returns 401 for everything
- recycles an instance in the middle of a call
- returns 429 when the backlog is released

Run the rehearsal with one of the new engineers following the runbook and the rest of the team watching. If they can resolve all four without help, the design is ready to operate.

There are now four more PayEx questions for the list from my first answer: how long keys are kept, how concurrent requests with the same key behave, rate limits, and how far behind the report runs. I can add this failure analysis to the ADR if you'd like.