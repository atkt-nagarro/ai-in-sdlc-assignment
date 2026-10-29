# Answer key and scoring rules

Written and committed before the first eval run, so the scoring cannot drift
towards whatever the reviewer happened to say. The facilitator's key lives in
the session runbook, which I do not have, so every label below is my own call
and the reasoning is written out so it can be challenged.

I judged each diff on its own content. Several diffs are written against a
slightly different version of the code (`DecisionResponse`, `CurrentUser` and
`_logger` exist in the diffs but not in this repository). That is fine: the
reviewer sees only the diff, and so did I when labelling.

## Labels

| Case | Label | The defect a finding must name to count as caught |
| --- | --- | --- |
| case-01 | defect | Either of: (a) the loop is not atomic. A missing or already-decided id throws part-way, the invoices before it stay approved, and the exception escapes as a 500 (the action does not use `Handle`), so the caller cannot tell which invoices were approved. (b) `Ids` is declared nullable and iterated unchecked, so a body without `ids` is a `NullReferenceException` and a 500. |
| case-02 | defect | SQL injection: `customer` and `status` are interpolated into the SQL string. |
| case-03 | defect | The rounding behaviour changes. The discount is now truncated (`ToZero`) before it is subtracted, instead of the total being rounded half away from zero, so totals move by a cent against the customer. Example: 19.99 at 15% gives 17.00 after the change and 16.99 before. A finding must say that results change. "Mixed rounding modes are confusing" is not enough. |
| case-04 | clean | Pure rename of `_repository` to `_invoices`. |
| case-05 | defect | The new `Delete` action has no `[RequireRole("Admin")]`, so any signed-in user can delete invoices. `Update` directly below it is Admin-only. |
| case-06 | clean | Tests only. They exercise existing behaviour correctly. |
| case-07 | defect | The whole invoice payload and the session/current-user object are written to the log with structured destructuring (`{@Invoice}`, `{@Session}`). That puts customer data and session details in the logs. |
| case-08 | defect | `ConcurrentDictionary` is swapped for `Dictionary` in a repository that serves concurrent requests. Concurrent writes can corrupt it, and `Add` becomes a check-then-insert race. |
| case-09 | defect (documentation) | The README now says that signing out and back in resets the sample data. It does not. `AuthController.Logout` only removes the session token (`SessionStore.Remove`), and invoices live in `InMemoryInvoiceRepository`, which is registered as a singleton (`Program.cs:14`) and is only reset by a restart. A finding must say the claim is wrong, or explain why it is unlikely to be true. "Check that this is accurate" on its own is not enough. |
| case-10 | defect | The new catch-all turns every unexpected exception into `200 OK {"status":"completed"}`, so failures are reported to the caller as successes. |
| case-11 | defect | The payment POST is retried after a timeout without an idempotency key. A timeout does not mean PayEx rejected the first request, so a retry can submit the same invoice twice. A finding about latency alone does not count. |
| case-12 | clean | Extracting `Decide(...)` preserves behaviour. `Reject` still validates the reason before looking the invoice up, and `DecisionNote` is only written when a note is passed, so `Approve` leaves it untouched exactly as before. The existing seven tests pass against the changed code. |

Nine defect cases and three clean ones. Cases 11 and 12 are mine (see
`cases/README-added-cases.md`); nobody saw them in the session.

### Why case-09 is labelled a defect

This is the one I am least sure the facilitator would agree with. A
docs-and-config diff looks like a natural "clean" case. But the sentence "to
reset the sample data without restarting, sign out and sign in again" is
specific, checkable and false against this codebase, and a reader who follows
it will believe their data has been reset when it has not. A false instruction
in a README is a defect. Because the label is contestable, `RESULTS.md` also
reports every headline rate with case-09 left out.

## Scoring rules

One verdict per case per run.

- **caught**: the review names the keyed defect. File and line can be
  approximate, but the mechanism must be right. A correct finding reached for
  the wrong reason does not count.
- **missed**: a defect case where no finding names the keyed defect. Other
  real issues the review raises in the same diff do not rescue a miss.
- **false alarm**: a clean case where the review asserts at least one defect.
  A defect means something goes wrong: wrong behaviour, a crash, a security
  exposure, data loss or a compile error.
- **clean**: a clean case where the review reports no defect.

How I treat borderline output:

- Style, naming, duplication, test-coverage and "consider" suggestions are
  not defects, per `README.md`.
- A defect listed as a finding counts as asserted even if it is hedged with
  low confidence. The prompt asks for findings with file, line and what goes
  wrong, so anything in that list is a claim.
- If the review says it found no defects and then adds observations, the
  observations are not counted.
- On defect cases, extra findings that are wrong do not change the verdict.
  I note them in `notes` and count them separately as spurious findings.
  They are what makes a reviewer noisy even when it catches the real problem.

## Rates

- Caught rate = caught / defect-case runs. Missed rate = 1 - caught rate.
- False alarm rate = false alarms / clean-case runs.
- Rates are pooled across the three runs of each condition, with Wilson 95%
  intervals. Per-case consistency (caught in 0, 1, 2 or 3 of 3 runs) is shown
  alongside, because three runs of the same case are not independent samples.
