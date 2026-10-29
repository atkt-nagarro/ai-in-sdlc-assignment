# case-01 / baseline / run 2

- model: claude-opus-5-5
- attempt: 1
- duration_ms: 25377
- cost_usd: 0.067048
- tool calls denied: 0

---

I couldn't check this against the real code. The workspace contains only the diff, not `ApprovalsController.cs` or the `_approvals` service, so findings 2–5 depend on how `Approve` behaves. They're marked as assumptions where that matters. Line numbers come from the new side of the hunk.

### 1. Missing or null `Ids` causes a crash (500 error)
**`ApprovalsController.cs:49`**: `foreach (var id in request.Ids)`

`Ids` is declared as `List<string>?`, so the type itself says it can be null. A body of `{}` or `{"ids": null}` binds without errors, and the `foreach` then throws a `NullReferenceException`. The client gets a 500 error instead of a 400. The compiler should also be warning about this (CS8602) if nullable reference types are on.

Fix: either make it `List<string> Ids` with `[Required]`, or add `if (request.Ids is null || request.Ids.Count == 0) return BadRequest(...)`.

**Confidence: high.**

### 2. One failure partway through leaves the batch half-done
**`ApprovalsController.cs:49–52`**

Each `Approve` call runs on its own, with no transaction and no error handling around the loop. If invoice #3 of 10 throws (not found, already approved, wrong state, concurrency conflict), invoices #1–2 stay approved if `Approve` saves as it goes. The request then fails as a whole, so the client gets an error and can't tell which invoices were approved.

Fix: either wrap the batch in a transaction so it's all-or-nothing, or catch errors per item and return a per-ID success/failure result.

**Confidence: medium-high.** This assumes `Approve` saves to the database and/or throws on bad input, which is typical but I couldn't confirm it.

### 3. A null result from `Approve` crashes the response
**`ApprovalsController.cs:54`**: `results.Select(DecisionResponse.From)`

If `Approve` returns `null` for an unknown ID instead of throwing, the null goes into `results`, and `DecisionResponse.From(null)` probably throws. Because `Select` runs lazily, the crash happens during JSON serialization, after all the approvals have already been saved.

**Confidence: low-medium.** It depends on what `Approve` returns, which I couldn't see. Check how the single-invoice endpoint above line 38 handles a missing invoice.

### 4. Duplicate IDs in one request aren't handled
**`ApprovalsController.cs:49`**

`["A","A"]` calls `Approve("A")` twice. Depending on the service, the second call either throws "already approved" after the first one saved (which triggers finding #2), or records a second approval and duplicates the audit trail. Removing duplicates with `.Distinct()` before the loop fixes it.

**Confidence: medium.**

### 5. No limit on how many IDs a request can contain
**`ApprovalsController.cs:41, 49`**

Nothing caps the list size, so a single request can trigger thousands of approvals one after another. That means long-running requests, timeouts partway through (which makes finding #2 worse), and a cheap way to load the server. Add a maximum, e.g. `[MaxLength(100)]` or an explicit check.

**Confidence: medium.** This is a hardening gap rather than a correctness bug.

### Worth checking (not confirmed)
If the existing single `Approve` action (above line 38) does any checks in the controller before calling `_approvals.Approve`, such as "can't approve your own invoice", approval-amount limits, or tenant/ownership checks, the bulk endpoint skips them. If those rules live inside the service, there's no problem. I couldn't see the earlier part of the file, so I can't confirm either way.
