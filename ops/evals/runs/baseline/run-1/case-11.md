# case-11 / baseline / run 1

- model: claude-opus-5-5
- attempt: 1
- duration_ms: 24449
- cost_usd: 0.0701468
- tool calls denied: 0

---

I found one serious defect and two minor ones. Only the diff was available: the workspace contains no other source, so I couldn't check `Map`, `PayExPayment`, or how the `HttpClient` is registered.

### 1. Retrying a timed-out payment POST can charge the customer twice
**File:** `PayExClient.cs`, new lines 26 and 31 (the `PostAsJsonAsync` call and the `catch (TaskCanceledException) when …` filter)

A client-side timeout doesn't mean PayEx failed to process the payment. It only means no response arrived in time. PayEx may have received the request and created the payment, with only the response being slow or lost. The retry sends the same `POST /v2/payments` again, and nothing in the diff makes that safe: no idempotency key header and no stable request ID. So each retry can create a new payment. With `MaxAttempts = 3`, one invoice could be charged up to three times.

The timeout is actually the riskiest failure to retry. Failures where the request clearly never arrived (connection refused, DNS errors) aren't retried, because they surface as `HttpRequestException`.

**Fix:** Send an idempotency key that stays the same across attempts, e.g. derived from `invoice.Id`, if PayEx supports one. Otherwise, don't retry blindly: after a timeout, look up the payment status by invoice reference before resubmitting. If PayEx already dedupes on a field that `Map` sends, such as a merchant reference, this risk goes away, but I couldn't confirm that.

**Confidence:** High that this retry is unsafe as written. Medium that it actually causes duplicates in production, since that depends on PayEx's dedup behaviour, which I can't see.

### 2. Worst-case latency roughly triples
**File:** `PayExClient.cs`, new lines 22 and 37

Each attempt can run until `HttpClient.Timeout` (100 s by default unless configured), plus 2 s and 4 s of delay between attempts. That's about 306 s in the worst case, where it used to be about 100 s. If the caller is an HTTP request or a job with a shorter timeout, the caller gives up first, but `SubmitAsync` keeps retrying in the background unless `ct` is tied to the caller's lifetime. That makes problem #1 worse, because the caller may also resubmit.

**Confidence:** Medium. It depends on the configured timeout and how `ct` is passed in.

### 3. `HttpResponseMessage` is never disposed
**File:** `PayExClient.cs`, new line 26

`var response = …` has no `using`. This was already true before the change, but now it can happen up to three times per call. Because the default `ResponseContentRead` mode buffers the body, the practical impact is small.

**Fix:** `using var response = await _http.PostAsJsonAsync(...)`.

**Confidence:** High that it's missing, low severity.

Everything else looks correct. The `!ct.IsCancellationRequested` filter correctly tells a caller cancellation apart from an `HttpClient` timeout. On the last attempt the exception propagates as expected. `Task.Delay(..., ct)` correctly stops the backoff when the caller cancels.
