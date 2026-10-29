# case-10 / baseline / run 2

- model: claude-opus-5-5
- attempt: 1
- duration_ms: 16321
- cost_usd: 0.043006
- tool calls denied: 0

---

I couldn't find the file in the working directory, so this review is based only on the diff.

## Finding 1: the new catch-all reports every unexpected failure as success (critical)

**File:** `backend/src/InvoiceApp.Api/Controllers/ApiControllerBase.cs`, the added `catch (Exception)` block (about lines 36–39 in the new file)

**What goes wrong:** Any exception not caught by the three blocks above it now becomes `200 OK` with `{ status = "completed" }`. That includes `NullReferenceException`, database errors, timeouts, `DbUpdateConcurrencyException` and serialization errors. Before this change, these became a 500 through the framework's normal error handling.

The effects:
- **Clients are told failed operations worked.** In an invoicing app, a create, update, payment or void that failed partway returns "completed". The client won't retry, and the user believes an invoice was saved or a payment recorded when it wasn't. Worse, a partial write may have happened, and nothing reports it.
- **The response shape changes silently.** On success the endpoint returns `Ok(action())`, which is the serialized `T`. On this path it returns `{ status: "completed" }` with the same 200 status. Clients reading the expected fields get `undefined`/null or a deserialization error far from the real cause, which is hard to diagnose.
- **The error disappears.** The exception isn't bound or logged, and because it never reaches the exception middleware, app-level logging, APM and error tracking never see it. Production failures become invisible.
- **Monitoring is blinded.** 5xx-rate alerts, health checks and load balancer or retry policies all depend on failures returning a 5xx status. These now look healthy.

**Confidence:** Very high. This is a defect whatever the intent was. If the goal was to stop raw exception details leaking to clients, ASP.NET Core already returns a generic 500 outside Development. The right fix is to remove this block. Failing that, log the exception and return `StatusCode(500, new { error = "An unexpected error occurred." })` or `Problem()`.

## Finding 2: the catch-all also catches cancellation (medium, same block)

**What goes wrong:** `catch (Exception)` also catches `OperationCanceledException`/`TaskCanceledException`, for example when a client disconnects or a cancellation token fires inside `action()`. A cancelled operation then returns "completed" too. This is part of Finding 1 but worth noting separately: if someone keeps a catch-all, it needs to exclude cancellation, e.g. `catch (Exception ex) when (ex is not OperationCanceledException)`.

**Confidence:** High that it happens if `action()` can throw cancellation. Medium on how much it matters, because I can't see the rest of the file or its callers.

Nothing else in the diff is a defect. The three existing catch blocks haven't changed, and the new block comes after them, so it doesn't shadow them.
