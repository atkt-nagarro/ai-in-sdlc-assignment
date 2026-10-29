**Yes, partly.** I can support option 3 for January, but only with four additions. Option 3 as written means calling PayEx inside the approval request and checking each night. That would still leave three risks:

- duplicate payments when users retry
- submissions lost without anyone noticing
- PayEx slowness slowing down approvals, as in INC-2041

None of the four additions is a background worker.

## Your points

- **Least to build:** true, but the gap is smaller than it looks. Option 3 still needs the SQL repository, the PayEx client, a scheduled reconciliation job, PayEx's reporting API, matching logic and a process for fixing mismatches. The nightly job is itself a scheduled process running in production. It has to be monitored, and when it fails you find out the next morning.
- **Finance already reconciles monthly:** this helps, and it counts for SOC 2. But a monthly check finds a duplicate payment up to 30 days after the money left, and a lost submission after the supplier has already chased you. The nightly job needs to be the real control, with finance's monthly check behind it.
- **No background worker with two new engineers:** this is a fair reason, and it's the one that changes my answer for January. A worker that runs every minute fails loudly and early, which some would argue is easier to operate. But I won't argue with your read of the team.

## The minimum safe version of option 3

1. **Approvals must not repeat.** Update the invoice only while it is still `PendingApproval`; otherwise return 409. In INC-2041 the same invoice was approved more than once (INV-41988, INV-41360). Without this, every retry after an error is another call to PayEx.
2. **Save the submission with the approval.** Add a `PaymentSubmission` row in the same transaction as the approval, with a unique constraint on the invoice ID. Its status starts as `Pending`, then becomes `Submitted` (with PayEx's reference), `Rejected` or `Unknown`.
   - Without this row, the nightly job has nothing reliable to compare against. A crash after the approval but before the call to PayEx leaves no trace.
   - This is the outbox table, just without a worker reading it.
3. **Send an idempotency key to PayEx, and never retry automatically after a timeout.** Mark the submission `Unknown` and leave it to the nightly job. Set the client timeout to about 35 to 40 seconds, longer than PayEx's 30. Use a shared HttpClient, not a new one per call (INC-2041's socket exhaustion).
4. **Stop calling PayEx while it's failing.** Use a circuit breaker: the approval still saves, and the response says the payment is pending. The submission stays `Pending` for the nightly job. This keeps a PayEx outage at month end from becoming an approval outage.

The nightly job then works through the `Pending` and `Unknown` rows against PayEx's records. It should alert if it doesn't run, and alert on anything it can't match.

## Risks you'd be accepting

Put these in the decision record:

- **Late payments:** a `Pending` or `Unknown` invoice can wait up to a day for its payment. At month end, about 8,000 invoices a day, even a 0.1% rate means about 8 manual cases a day, in the busiest window.
- **Slow approvals:** an approval can still take up to 40 seconds while PayEx is slow but not slow enough to trip the circuit breaker.
- **People must resolve the hard cases:** someone has to decide each `Unknown`, so the runbook has to be good enough for a new engineer to follow.

## What doesn't change

- **PayEx's answers still decide this.** If PayEx doesn't dedupe on a key or let us look up a payment by our reference, then retrying after a timeout risks paying twice under any option. `Unknown` cases then need a person to resolve them, and finance needs to sign off on that.
- **I still think a worker is the right long-term design.** With item 2 in place, moving there in February or March means running the same resolution logic every minute instead of every night. There's no schema change and no redesign. If you build to this shape now, choosing option 3 for January costs you very little later.

If you go ahead, I can write this up as an ADR: option 3 for January, the four additions, the accepted risks, and what would trigger the move to a worker.