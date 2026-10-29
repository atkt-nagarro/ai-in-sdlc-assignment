# case-11 / agents-md / run 4

- model: claude-opus-5-5
- attempt: 1
- duration_ms: 30360
- cost_usd: 0.0869072
- tool calls denied: 0

---

I found one serious defect and one secondary concern.

I couldn't check this against the actual code. The workspace has no `backend/` directory, only `AGENTS.md`, which says no payment provider exists in the code yet. So I reviewed the diff on its own. I can't see how `HttpClient` is registered, what `Map(invoice)` sends, or what PayEx's API guarantees.

### 1. Retrying after a timeout can pay the same invoice twice
**File:** `backend/src/InvoiceApp.Api/Clients/PayExClient.cs`, line 31 (the `catch`), which re-runs the POST on line 26
**Confidence:** High that the duplicate can happen. Medium on how bad it is in practice, because I can't tell whether PayEx removes duplicates on its side.

**What goes wrong:** A timeout only means the client stopped waiting. It doesn't mean PayEx never got the request. PayEx may have received `POST /v2/payments` and created the payment, but the response was slow or lost. The loop then sends the same payment again, up to 3 times, with nothing that lets PayEx spot it as a repeat. One invoice can be paid two or three times. These cases are the hardest to spot, because each "retrying" warning looks harmless in the logs.

**Fix:** Only retry if repeating the request is safe. Choose one of these:
- Send an idempotency key that stays the same across attempts, such as one derived from `invoice.Id`, if PayEx supports one.
- After a timeout, ask PayEx whether a payment already exists for this invoice before sending it again.
- Don't retry here. Report the result as unknown and let a reconciliation step settle it.

### 2. Worst-case wait goes from about 100 seconds to about 5 minutes
**File:** same file, lines 22 and 37
**Confidence:** Medium. It depends on the `HttpClient` setup, which isn't in the diff.

**What goes wrong:** `HttpClient.Timeout` applies to each attempt separately (100 seconds by default). Three timed-out attempts plus the 2-second and 4-second delays add up to about 306 seconds before the caller gets an error. If the caller is handling an API request, that request hangs for minutes. Also, if the client is registered with a resilience or Polly handler (for example `AddStandardResilienceHandler`), those retries multiply with this loop's. That makes the wait longer and the duplicate-payment risk in finding 1 worse.

**Fix:** Set an overall time limit that covers all attempts, and make sure the client doesn't already retry somewhere else.

The rest of the change works as intended. The `!ct.IsCancellationRequested` filter correctly separates a timeout from the caller cancelling. The final timeout and HTTP error responses are still passed to the caller instead of being swallowed. The delay respects `ct`.
