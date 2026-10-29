# case-11 / baseline / run 2

- model: claude-opus-5-5
- attempt: 1
- duration_ms: 21914
- cost_usd: 0.0608954
- tool calls denied: 0

---

I found one serious defect and one minor one. Only the diff was available: the working directory has no source, so I couldn't see `Map`, `PayExPayment`, or how the `HttpClient` is registered.

### 1. A retry after a timeout can create a duplicate payment (high severity)
**File:** `backend/src/InvoiceApp.Api/Clients/PayExClient.cs`, the `catch (TaskCanceledException) when (...)` block (around new line 31) and the loop that resends `POST /v2/payments`.

**What goes wrong:** A client-side timeout only means we stopped waiting. It doesn't mean PayEx never got or never processed the request. If PayEx is slow but still finishes the first POST, the retry sends the same payment again, and the invoice can be charged two or three times. Timeouts are most likely exactly when PayEx is under load and slow, which is when it's likely still processing. Before this change, a timeout surfaced as an error and nothing was resent.

**Fix:** Send an idempotency key that stays the same across retries, such as a header or field derived from `invoice.Id`, if PayEx supports one. If it doesn't, check the payment's status by invoice reference before resubmitting. Otherwise, don't retry this call automatically.

**Confidence:** High that the retry is unsafe as written. Medium that it actually causes double charges. That part depends on things I couldn't see: whether `Map(invoice)` already includes a reference PayEx uses to reject duplicates, and whether PayEx enforces it.

### 2. `HttpResponseMessage` is never disposed (low severity)
**File:** same file, the `var response = await _http.PostAsJsonAsync(...)` line inside the `try` (around new line 26).

**What goes wrong:** When `EnsureSuccessStatusCode` throws, the response is never disposed, and the same happens on the success path. This was already true before the change, but now the line can run up to three times per call. The impact is small because the content is buffered, but `using var response = ...` is the correct form.

**Confidence:** High that it's real; the impact is minor.

### Things I couldn't check
- **Retries stacking:** if the `HttpClient` registration already adds Polly or `AddStandardResilienceHandler`, these retries multiply with the handler's own.
- **Worst-case wait:** with the default 100 s `HttpClient.Timeout`, one call can block for about 5 minutes (3 × 100 s plus 6 s of delays). That may exceed the caller's own timeout if this runs inside an HTTP request.

The rest of the retry logic looks correct. The `!ct.IsCancellationRequested` filter tells a timeout apart from the caller cancelling. The final attempt rethrows. `Task.Delay(..., ct)` stops promptly if the caller cancels during the backoff.
