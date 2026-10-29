# case-01 / baseline / run 3

- model: claude-opus-5-5
- attempt: 1
- duration_ms: 23810
- cost_usd: 0.0616066
- tool calls denied: 0

---

I couldn't check this against the source. The working directory has no `backend/` tree, only harness files, so this review is based on the diff alone. Where a finding depends on code I couldn't see, I say so.

## Findings

**1. Missing or null `Ids` crashes with a 500 error.** `ApprovalsController.cs`, `foreach (var id in request.Ids)` (about line 49). **Confidence: high.**
`Ids` is declared `List<string>?`, so it is meant to be allowed to be null. A body like `{}` or `{"ids": null}` passes model binding, and then the `foreach` throws `NullReferenceException`. The client gets a 500 instead of a 400. Fix this by checking `request.Ids is null or { Count: 0 }` and returning `BadRequest`, or by making the property non-nullable and required so validation rejects the request.

**2. One failure leaves a batch half-approved, and the client isn't told which ones went through.** Same `foreach`, around `_approvals.Approve(...)` (about line 51). **Confidence: medium-high.** This depends on `Approve` throwing for bad input, which is how most services behave, but I couldn't confirm it.
Each `Approve` call presumably saves its change on its own. If ID #3 of 10 is unknown, already approved/rejected, or fails a business rule, the exception escapes. IDs #1–2 stay approved, #4–10 never run, and the response is an error. The client can't tell what happened, and retrying the same list will likely hit "already approved" on #1. Fix it in one of two ways:
- Wrap the loop in a transaction so it's all-or-nothing.
- Catch errors per item and return a result for each ID (`{id, success, error}`).

**3. Duplicate IDs in the request aren't handled.** Same loop. **Confidence: medium.**
`["A","A"]` calls `Approve("A")` twice. Depending on the service, the second call either throws (which triggers finding #2 on a request that's really valid) or records a second approval or audit entry. Removing duplicates first (`request.Ids.Distinct()`) fixes this.

**4. There's no limit on how many IDs one request can send.** `BulkApprove` (about line 45). **Confidence: medium.**
The request can carry any number of IDs, and each one is approved synchronously in a single request. A very large list ties up a request thread and the database for a long time. Add a maximum count, for example with `[MaxLength(N)]` on `Ids` or an explicit check.

**5. The bulk path may skip checks that the single-approve endpoint does.** Lines 45–55 compared with the existing approve action that ends at line 38. **Confidence: low.** This is unverified because I couldn't see the single endpoint's body.
If the existing approve action does anything in the controller beyond calling `_approvals.Approve(id, CurrentUser.Name)`, the bulk endpoint gets around it. Examples would be returning `NotFound` for unknown IDs, a rule against approving your own invoice, approval amount limits, or audit logging. Check that the two endpoints apply the same rules, ideally by having both go through one shared service method.

## Things I checked that aren't problems
- **Route conflict:** `bulk-approve` is a fixed path with one segment, and `{id}/reject` has two segments, so they don't collide.
- **Lazy `Select`:** `results` is already a fully built list, so serialising `results.Select(...)` is safe. (If `DecisionResponse.From` has overloads, the method group could fail to compile, but that would show up at build time.)
