# Added cases

The assignment asks for two cases beyond the ten fixed ones, drawn from real defects, with at least one of them clean. Four of the original ten were walked through in the session, and all ten ship with the repository, so these two are the only ones that were neither shown in the session nor part of the original repository.

## case-11: retry after a payment timeout (defect)

`PayExClient.SubmitAsync` gains a retry loop. When the HTTP call times out, it waits and posts the same payment again, up to three attempts.

**Where it comes from:** retrying a payment POST after a timeout, with no idempotency key, is a documented way to pay twice. Users of Mollie's PHP client traced duplicate payments to the client retrying requests that had in fact gone through, first after 500 responses ([mollie-api-php #642](https://github.com/mollie/mollie-api-php/issues/642), 2022) and then during an API slowdown that ran past its 10-second timeout ([#663](https://github.com/mollie/mollie-api-php/issues/663), 2023). GoCardless shipped a subtler version: its client created a new idempotency key inside the retry loop, so every retry looked like a new payment ([commit 9ca3785](https://github.com/gocardless/gocardless-pro-python/commit/9ca3785836504233abe7cf1151369913eb507174), 2017). As Stripe puts it, a call can succeed while the connection breaks before the client hears back ([Stripe, 2017](https://stripe.com/blog/idempotency)), and the scenario says the same of PayEx: a timeout does not reliably mean the submission failed.

**Why I chose it:** I wanted one case where the reviewer has to understand the payment provider, not just the code. After INC-2041, a retry on timeout is the fix I would most expect a well-meaning engineer to make to `PayExClient`, and it is the one that costs real money if review misses it.

The change looks responsible, which is how it can get through review: it adds resilience, logs a warning and backs off. In the eval, Opus caught it in all six runs and the smaller model missed it in all three. The class matches the pre-2.14.0 client on the old side of `ops/incidents/INC-2041/deploy-diff.patch` (typed `HttpClient`, `PayExOptions`, `Map(invoice)`), so a reviewer gets realistic context. The answer key scores one defect, the duplicate payment; reviewers also raised other points in this diff, which I did not classify.

## case-12: extracting the shared decision step (clean)

`ApprovalService.Approve` and `Reject` repeated the same six lines, plus a status assignment that differed only in its value. The change moves them into a private `Decide(...)` method.

**Where it comes from:** a behaviour-preserving extract-method refactor of a state transition. Reviewers find these hard to judge: review tools show a refactoring like any other change, so reviewers have to work out for themselves that behaviour is unchanged ([Ge et al., VL/HCC 2017](https://doi.org/10.1109/VLHCC.2017.8103453)), and refactoring reviews take significantly longer to resolve ([AlOmar et al., MSR 2022](https://arxiv.org/abs/2203.14404)). The doubt is fair, because Extract Method can change behaviour; Visual Studio's automated version has done so ([dotnet/roslyn #81557](https://github.com/dotnet/roslyn/issues/81557)). This change keeps the two details that would make it a behaviour change if missed:

- `Reject` still validates the reason before it looks the invoice up, so a blank reason on an unknown invoice still raises `ArgumentException`, not `KeyNotFoundException`.
- `DecisionNote` is only assigned when a note is passed, so `Approve` leaves it untouched, as before.

**Why I chose it:** I wanted a clean case that looks risky. The reviewer has to trace both code paths to see that nothing changed, and that is where I expected a noisy reviewer to raise false alarms. None did: all nine reviews of case-12 reported no defect.

The diff was produced with `diff -u` against the real `backend/src/InvoiceApp.Domain/ApprovalService.cs`. With it applied, the full test suite passes ([case-12-test-run.txt](case-12-test-run.txt)): eight tests, the seven the answer key mentions plus the architecture test added after it. The false alarms this case invites are "approve now clears the note" and "the validation order changed". Neither is true here, and that is what the case tests.
