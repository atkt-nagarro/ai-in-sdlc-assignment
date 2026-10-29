# case-11 / agents-md / run 6

- model: claude-opus-5-5
- attempt: 1
- duration_ms: 34461
- cost_usd: 0.09545540000000001
- tool calls denied: 0

---

I couldn't check this against real code. The workspace has only `AGENTS.md`, `CLAUDE.md` and the diff, with no `backend/` source. `AGENTS.md` also says a payment provider exists only in the *planned* deployment under `ops/`, so `PayExClient` isn't part of the system as documented. These findings come from the diff alone. Line numbers refer to the new file.

## Findings

**1. Retrying a payment POST after a timeout can charge the same invoice twice.** `PayExClient.cs:26` and `:31`. **Confidence: high**
- **What goes wrong:** a timeout tells you nothing about what happened on PayEx's side. The request may have arrived and been processed, with only the response lost or late. The `catch` on line 31 then re-sends the same `POST /v2/payments`.
- **Why nothing prevents it:** I see no idempotency key in the diff, either as a header on the request or as a value that stays the same across attempts. Up to 3 payments could be created for one invoice.
- **What would change my mind:** I can't see `Map` or how the `HttpClient` is set up. This drops to low only if `Map(invoice)` sends a key PayEx dedupes on (for example the invoice ID as the payment reference), or if a handler adds an `Idempotency-Key` header.
- **Fix:** send a stable idempotency key per invoice, derived from `invoice.Id`, on every attempt. If PayEx doesn't support one, don't retry on timeout. Instead, look up the payment status before re-submitting.

**2. It retries the riskiest failure and skips the safe ones.** `PayExClient.cs:31`. **Confidence: medium-high**
- Only `TaskCanceledException` (a timeout) is retried, which is the case where the request may already have gone through.
- An `HttpRequestException` from a refused or reset connection, where the request usually never reached PayEx, is not retried. Neither is a 503, which `EnsureSuccessStatusCode` throws as `HttpRequestException`.
- That's the opposite of a safe retry policy for a non-idempotent call. If this was meant to make the client more resilient, it covers the wrong cases.

**3. The caller can now wait about three times longer than before.** `PayExClient.cs:22–37`. **Confidence: medium**
- Each attempt can use up the full `HttpClient.Timeout` (100 s by default), plus 2 s and 4 s of delay between attempts.
- With default settings, `SubmitAsync` can block for about 306 s before failing. Anything upstream with its own timeout, such as a request pipeline or a proxy, will likely give up first. The caller then sees a failure while payments may have been created behind it, which makes finding 1 worse.
- I can't confirm the configured timeout without the registration code.

**4. Retries may stack on top of retries that already exist.** **Confidence: low, unverifiable**
- If the `HttpClient` is registered with `AddStandardResilienceHandler`, Polly or another retry handler, this loop multiplies those retries: 3 × N attempts.
- There's no `Program.cs` here to check.

**5. There are no tests for the retry behaviour.** **Confidence: high that tests are missing from the diff**
- `AGENTS.md` requires tests for every new rule. Nothing covers the retry count, rethrowing on the last attempt, or not retrying when the caller cancels.

## Minor issues

- **Line 33:** the warning doesn't pass the caught exception to `LogWarning`, so the inner `TimeoutException` and stack trace are lost.
- **Line 26:** `HttpResponseMessage` is never disposed. This was already true before the change.

## Checked and correct

- The `!ct.IsCancellationRequested` filter correctly avoids retrying when the caller cancels.
- `Task.Delay(..., ct)` stops waiting when the caller cancels.
- On the last attempt the original exception propagates, because the `when` filter stops matching.
- The `for (;;)` loop compiles without a fall-through return.
