# case-11 / agents-md / run 5

- model: claude-opus-5-5
- attempt: 1
- duration_ms: 27482
- cost_usd: 0.08197700000000001
- tool calls denied: 0

---

I found one serious defect and a few smaller ones. A caveat first: the working directory holds only `AGENTS.md`, `CLAUDE.md` and the diff. There is no `backend/` folder, so I couldn't check `IPayExClient`, `Map`, `PayExOptions`, how the `HttpClient` is registered in `Program.cs`, or who calls `SubmitAsync`. Also, `AGENTS.md` says the payment provider is only *planned* and "none of which exist in the code". This diff edits a PayEx client that, by that description, shouldn't exist yet. Check that it's going into the branch you expect.

## Findings

**1. Retrying a payment POST after a timeout can charge twice**
`PayExClient.cs`, the `catch (TaskCanceledException) when (...)` block (new lines ~31–39), which loops back to `PostAsJsonAsync("/v2/payments", ...)`.
**Confidence: high**

When `HttpClient.Timeout` fires, it only means we stopped waiting. It doesn't mean PayEx rejected the payment. The request may have reached PayEx and been processed, with only the response lost or slow. Retrying the same POST then submits a second payment for the same invoice, and up to 3 in total.

It gets worse because the `try` also wraps `ReadFromJsonAsync`. If the timeout fires while the body is being read, `EnsureSuccessStatusCode()` has already passed. PayEx has definitely accepted the payment, and the code still sends it again.

Nothing in the diff sends an idempotency key (header or request field), and `Map(invoice)` isn't visible, so I can't tell whether PayEx deduplicates on an invoice reference.

Fix: send a stable idempotency key for each invoice, e.g. derived from `invoice.Id`, and confirm PayEx honours it. Without that, don't retry blindly after a timeout. Query PayEx for the payment's status first, or fail and leave it to a reconciliation step.

**2. A response that was already received counts as a "timeout"**
Same `try` block.
**Confidence: medium-high**

This follows from #1 but is worth fixing on its own. Even if retries stay, only the send should be retryable. Move the read out of the retry scope, e.g. use `HttpCompletionOption.ResponseHeadersRead` and keep the read outside the `try`. Once a 2xx status is seen, a failure while reading should not trigger a resubmit.

**3. Worst-case latency grows about 3×**
The `for` loop together with `Task.Delay(TimeSpan.FromSeconds(attempt * 2), ct)`.
**Confidence: medium**

Each attempt can take the full `HttpClient.Timeout`, which defaults to 100 s unless `PayExOptions` or the client registration sets something lower. That makes the worst case roughly 3 × timeout + 6 s. If `SubmitAsync` runs inside an HTTP request, such as an approval endpoint, the caller or a proxy will probably give up before this finishes. The payment then completes with no one waiting for the result, which makes #1 more likely. Also, if the client already has a resilience handler (`AddStandardResilienceHandler` / Polly) in `Program.cs`, the two retry layers multiply. I couldn't check that.

**4. `HttpResponseMessage` is never disposed**
`var response = await _http.PostAsJsonAsync(...)`.
**Confidence: medium (minor)**

This was already true before the change, but now it can happen up to three times per call. Use `using var response = ...`.

**5. The new behaviour has no tests**
**Confidence: high (process, not runtime)**

`AGENTS.md` requires tests for every new rule. The diff has none. At minimum it needs tests for: retry on timeout, no retry when `ct` is cancelled, giving up after `MaxAttempts`, and no resubmit once a success status has been received.

## Checked and fine
- `when (!ct.IsCancellationRequested ...)` correctly tells an `HttpClient` timeout apart from the caller cancelling.
- On the last attempt the filter is false, so the original `TaskCanceledException` reaches the caller unchanged.
- If the caller cancels during `Task.Delay(..., ct)`, the exception is thrown outside the `try` and propagates correctly.
