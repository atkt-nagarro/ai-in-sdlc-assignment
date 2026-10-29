# Added cases

The assignment asks for two cases beyond the ten fixed ones, drawn from real defects, with at least one of them clean. Four of the original ten were walked through in the session, and all ten ship with the repository, so these two are the only ones nobody has seen before.

## case-11: retry after a payment timeout (defect)

`PayExClient.SubmitAsync` gains a retry loop. When the HTTP call times out, it waits and posts the same payment again, up to three attempts.

**Where it comes from:** this is the textbook double-payment defect, the reason payment APIs offer idempotency keys at all. A client-side timeout only tells you that you stopped waiting, not that the provider rejected the request. The scenario says the same of PayEx: a timeout does not reliably mean the submission failed. Retrying a POST that carries no idempotency key turns every slow-but-successful call into a duplicate payment.

**Why I chose it:** I wanted one case where the reviewer has to understand the payment provider, not just the code. After INC-2041, a retry on timeout is the fix I would most expect a well-meaning engineer to make to `PayExClient`, and it is the one that costs real money if review misses it.

The change looks responsible, and that is why it gets through review: it adds resilience, logs a warning and backs off. The class matches the client that appears in `ops/incidents/INC-2041` (typed `HttpClient`, `PayExOptions`, `Map(invoice)`), so a reviewer gets realistic context. The diff contains exactly one defect.

## case-12: extracting the shared decision step (clean)

`ApprovalService.Approve` and `Reject` repeated the same five lines. The change moves them into a private `Decide(...)` method.

**Where it comes from:** a behaviour-preserving extract-method refactor of a state transition, the kind of change that draws confident but false "this changes behaviour" review comments. It keeps the two details that would make it a behaviour change if missed:

- `Reject` still validates the reason before it looks the invoice up, so a blank reason on an unknown invoice still raises `ArgumentException`, not `KeyNotFoundException`.
- `DecisionNote` is only assigned when a note is passed, so `Approve` leaves it untouched, as before.

**Why I chose it:** I wanted a clean case that looks risky. The reviewer has to trace both code paths to see that nothing changed, and a noisy reviewer raises its false alarms exactly there.

The diff was produced with `diff -u` against the real `backend/src/InvoiceApp.Domain/ApprovalService.cs`. With it applied, the full test suite passes ([case-12-test-run.txt](case-12-test-run.txt)). The false alarms this case invites are "approve now clears the note" and "the validation order changed". Neither is true here, and that is what the case tests.
