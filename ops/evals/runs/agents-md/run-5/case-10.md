# case-10 / agents-md / run 5

- model: claude-opus-5-5
- attempt: 1
- duration_ms: 19771
- cost_usd: 0.06073
- tool calls denied: 0

---

I couldn't check the diff against the code: `backend/` isn't in the working directory, so this review is based only on the diff. The line numbers below are counted from the hunk header (`+20,13`).

## Findings

### 1. Unexpected errors are reported as success
**File:** `backend/src/InvoiceApp.Api/Controllers/ApiControllerBase.cs`, lines 35–38 (new `catch (Exception)` block)
**Confidence:** High

Any exception not already handled now returns `200 OK` with `{ "status": "completed" }`. This includes null references, repository failures and bugs in `ApprovalService`. In this app, that means:
- An approval, rejection or delete that failed partway looks like it worked. The UI and API clients will tell the user the invoice was approved or deleted when it may not have been, or may have been only partly changed.
- Clients have no way to tell a real success from a crash, so they can't retry or show an error.
- An approval workflow that says "approved" when it wasn't is a correctness problem, not just a cosmetic one.

The correct behaviour is a 500, which is what happened before this change.

### 2. The exception is thrown away without being logged
**File:** same file, line 35 (`catch (Exception)` has no variable and nothing is logged)
**Confidence:** High

Because the exception is caught here, ASP.NET Core's exception handling and logging never see it. Nothing is logged and nothing reaches the developer exception page or any error-tracking setup. Failures in production would leave no trace, so bugs that used to be visible become silent.

### 3. The "success" response has a different shape from a real success
**File:** same file, line 37
**Confidence:** High

A real success returns `Ok(action())`, which is the actual result, such as an invoice object. The new branch returns `{ status = "completed" }` instead. Any client that reads the response as the expected type will get missing or default fields. For example, the web UI might show an invoice with no id or status, or crash later in a less obvious place. This makes the bug in finding 1 harder to trace.

### 4. The change has no tests
**Confidence:** Medium. I couldn't see the test project, so this is inferred from the diff only.

AGENTS.md requires tests for every new rule. More importantly, a test that pinned down this behaviour would itself be asserting the wrong thing.

## Recommendation
Remove the `catch (Exception)` block entirely and let unexpected exceptions become 500s through the framework. If the goal was a consistent error body, add a global exception handler or middleware that logs the exception and returns `500` with something like `{ error = "Unexpected error" }`. It must never return a 2xx status.
