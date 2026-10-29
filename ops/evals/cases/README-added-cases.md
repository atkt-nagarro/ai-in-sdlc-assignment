# Added cases

The assignment asks for two cases beyond the ten fixed ones, drawn from real
defects, with at least one of them clean. Four of the original ten were shown
in the session, so these two are the only ones no participant has seen before.

## case-11: retry after a payment timeout (defect)

`PayExClient.SubmitAsync` gains a retry loop. When the HTTP call times out,
it waits and posts the same payment again, up to three attempts.

This is the classic way payment integrations double-charge. A client-side
timeout tells you that you stopped waiting, not that the provider rejected
the request. PayEx's own documentation for this service says the same thing:
a timeout does not reliably mean the submission failed. Retrying a POST that
carries no idempotency key turns every slow-but-successful call into a
duplicate payment. The change looks responsible, and that is why it gets
through review: it adds resilience, logs a warning and backs off.

The class matches the client that appears in `ops/incidents/INC-2041`
(typed `HttpClient`, `PayExOptions`, `Map(invoice)`), so a reviewer gets
realistic context. The diff contains exactly one defect.

## case-12: extracting the shared decision step (clean)

`ApprovalService.Approve` and `Reject` repeated the same five lines. The
change moves them into a private `Decide(...)` method. It keeps the two
details that would make it a behaviour change if missed:

- `Reject` still validates the reason before it looks the invoice up, so a
  blank reason on an unknown invoice still raises `ArgumentException`, not
  `KeyNotFoundException`.
- `DecisionNote` is only assigned when a note is passed, so `Approve` leaves
  it untouched, as before.

The diff was produced with `diff -u` against the real
`backend/src/InvoiceApp.Domain/ApprovalService.cs`, and the existing seven
tests pass against the changed file. Refactors like this are where reviewers
raise false alarms ("approve now clears the note", "the validation order
changed"). Neither is true here, and that is what the case tests.
