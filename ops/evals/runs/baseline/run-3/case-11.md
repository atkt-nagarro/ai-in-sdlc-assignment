# case-11 / baseline / run 3

- model: claude-opus-5-5
- attempt: 1
- duration_ms: 26549
- cost_usd: 0.0695286
- tool calls denied: 0

---

I found one serious defect. I only had the diff to work from; the rest of the repo isn't in the working directory. So I couldn't check `Map`, `PayExPayment`, or how the `HttpClient` is registered, and I've noted below where that limits my confidence.

### 1. Retrying a payment POST after a timeout can charge the same invoice twice
**File:** `backend/src/InvoiceApp.Api/Clients/PayExClient.cs`, lines 26 and 31–37 (new file numbering)
**Confidence:** High that this is a real risk. Medium that it will actually cause double charges, because that depends on whether PayEx removes duplicates (see below).

A timeout leaves the outcome unknown. It doesn't mean the request failed. When `HttpClient.Timeout` fires, PayEx may already have received the request, created the payment, and just been slow to reply, or the reply may have been lost on the way back. The new loop sends `POST /v2/payments` again with nothing that ties the attempts together. Unless PayEx removes duplicates, one invoice can produce up to three payments, and the receipt you return belongs only to the last one. A slow PayEx is also the most likely moment for this to happen, so it would show up as duplicate charges under load rather than as a rare edge case.

This is safe only if each attempt carries something PayEx uses to recognise a repeat: an `Idempotency-Key` header, or a field in `PayExPayment` that PayEx enforces as unique, such as the invoice ID used as a merchant reference. Nothing in the diff adds one, and I couldn't check `Map`. **Fix:** create one idempotency key per `SubmitAsync` call, outside the loop, and send it on every attempt. Or, before retrying, ask PayEx whether a payment already exists for this invoice and only re-send if it doesn't.

### 2. Worst-case wait is about 3× the HttpClient timeout plus 6 seconds
**Same file**, lines 22 and 37
**Confidence:** Medium. It depends on settings I couldn't see.

Each attempt can run for the full `HttpClient.Timeout`, which defaults to 100 seconds. Add the 2s and 4s delays, and a caller can wait over 5 minutes before getting an error. If the code calling `SubmitAsync` has its own timeout, it may give up first. It then reports a failure while a retry is still running in the background and may succeed, which makes the duplicate problem in #1 worse. Also, if this `HttpClient` already has a retry layer (Polly or `AddStandardResilienceHandler`), the two retry layers multiply each other. I couldn't check that because the DI registration isn't in this diff.

### 3. Minor: the `HttpResponseMessage` is never disposed
**Same file**, line 26
**Confidence:** High that it's missing. The impact is low.

`response` isn't wrapped in `using`. The code already did this before the change, but now it can happen up to three times per call. A non-success response that throws from `EnsureSuccessStatusCode` leaves its content undisposed until garbage collection. Use `using var response = ...`.

Everything else looks right to me. The `when` filter correctly skips retrying when the caller cancels, `Task.Delay` honours `ct`, and the last attempt throws its exception normally.
