# case-10 / baseline / run 1

- model: claude-opus-5-5
- attempt: 1
- duration_ms: 16755
- cost_usd: 0.046171000000000004
- tool calls denied: 0

---

I found one defect, and it's serious. I couldn't find `ApiControllerBase.cs` in the working directory, so this review is based on the diff alone.

## Finding: the new catch-all reports every unexpected failure as success

**File:** `backend/src/InvoiceApp.Api/Controllers/ApiControllerBase.cs`, the added `catch (Exception)` block (around lines 35–38 in the new file)

**Confidence:** High. Nothing outside the diff could make this correct.

**What goes wrong:**

1. **Failures look like successes.** Any exception the earlier blocks don't catch now returns `200 OK` with `{ status: "completed" }`. That includes database errors, timeouts, `NullReferenceException`s, failed outbound calls and serialization errors. A client that creates, updates or pays an invoice is told it worked when nothing was saved, or only part of it was. In an invoicing app, that means silent data loss and money records that don't match.

2. **The exception disappears without a trace.** It isn't logged or rethrown, and it isn't kept. Any global exception middleware, `UseExceptionHandler`/ProblemDetails, the developer exception page, and APM/error tracking all stop seeing these errors. Production failures become invisible.

3. **The response shape breaks the API contract.** The success path returns `Ok(action())`, which is the action's actual result. This path returns a different anonymous object with the same 200 status. Typed clients will either fail to deserialize it or quietly fill in default values, such as a null or zero invoice ID, and carry on with bad data.

4. **Retries and resilience stop working.** Clients, gateways and retry policies like Polly only retry on 5xx or transient errors. A 200 is never retried, so temporary faults that would have recovered become permanent losses.

5. **It also catches cancellations.** If the client aborts the request (`RequestAborted`), the resulting `OperationCanceledException` is caught too and recorded as a completed 200 in logs and metrics.

**Fix:** Delete the block and let unexpected exceptions reach the global exception handler. If a local catch is really needed, log the exception and return a 500, for example with `Problem(...)` or `StatusCode(500, ...)`, or rethrow with `throw;`. Unknown errors should never return a 2xx.

There are no other changes in the diff.
