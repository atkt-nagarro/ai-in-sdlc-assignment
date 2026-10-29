# case-10 / agents-md / run 4

- model: claude-opus-5-5
- attempt: 1
- duration_ms: 23727
- cost_usd: 0.069325
- tool calls denied: 0

---

I couldn't open the source: `backend/` isn't in the working directory. So this review is based on the diff alone, and the line numbers come from the hunk header (new file starting at line 20).

## Findings

**1. Failed operations report success: `ApiControllerBase.cs:35–38` (the new `catch (Exception)`)**
Any exception the three typed handlers don't catch now returns **HTTP 200 `{ status: "completed" }`**. That includes `NullReferenceException`, `InvalidCastException`, a broken repository and so on. If an approve, reject or delete call crashes partway through, the client and the web UI are told it worked. An exception thrown after a partial change in the in-memory repository also leaves the data inconsistent with nothing to flag it. In an invoice-approval system, a false "approved" or "deleted" is a correctness problem and an audit problem.
*Confidence: high.*

**2. The exception is thrown away without logging: same lines**
`catch (Exception)` doesn't bind or log the exception. Combined with the 200 status, the failure leaves no trace: nothing in the logs, no 5xx in metrics, nothing for the ASP.NET exception handler or ProblemDetails middleware to pick up. Real bugs become invisible in production and in integration or e2e tests, which will now pass where they should fail.
*Confidence: high.*

**3. The response shape doesn't match the success path: line 37 vs. line 21**
On success, `Handle` returns `Ok(action())`, which is the actual result (for example the invoice DTO). The new branch returns `{ status = "completed" }`. Any caller that reads the body on a 200 will get a missing or undefined invoice and fail later in a less obvious place.
*Confidence: high. I couldn't confirm how `wwwroot/` handles the response, but any client that reads the returned object is affected.*

**4. Cancelled requests are also reported as success: same lines**
`OperationCanceledException` (for example when the client aborts) gets caught and answered with 200. This is minor next to #1, but it's the same root cause.
*Confidence: medium. It only matters if any action respects cancellation tokens.*

**5. No tests (AGENTS.md: "Every new rule or endpoint needs tests")**
This changes error-mapping behaviour for every endpoint, and the diff includes no test changes.
*Confidence: high that tests are missing. Low impact, because the right fix is to drop the change, not to test it.*

**Minor: the hunk header doesn't match the body**
`@@ -20,9 +20,13 @@` claims 9 old and 13 new lines, but the hunk shows 16 and 20. Either the diff was edited by hand or it's truncated, and it won't apply cleanly with `git apply`.
*Confidence: high on the mismatch. Low impact on the code itself.*

## Recommendation
Remove the `catch (Exception)` block. Let unexpected exceptions propagate so they become 500 responses through `app.UseExceptionHandler(...)` / ProblemDetails in `Program.cs`, where they also get logged. If a broad catch is really wanted here, it should log the exception and return a 500 (`Problem(...)`), never `Ok`.
