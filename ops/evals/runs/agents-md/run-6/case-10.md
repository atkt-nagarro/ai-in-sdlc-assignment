# case-10 / agents-md / run 6

- model: claude-opus-5-5
- attempt: 1
- duration_ms: 19581
- cost_usd: 0.0618686
- tool calls denied: 0

---

I reviewed this from the diff alone. `backend/` isn't in the working directory, so I couldn't see the callers of `Handle(...)` or check for an exception middleware or logger. The line numbers below come from the hunk and may be off by a line or two, because the hunk header says 13 lines but the hunk has 18.

## Findings

**1. Failures are reported as success. `ApiControllerBase.cs` ~line 35–38. Confidence: high**

`catch (Exception)` catches every exception the three specific handlers miss, such as `NullReferenceException`, repository errors and `OperationCanceledException`. It then returns **200 OK**. Every controller goes through `Handle(...)`, so a crashed approve, reject or delete now tells the client it worked. The web UI and any API callers will show an invoice as approved or deleted when nothing happened.

The in-memory repository can also be left half-updated if the exception happens partway through a change. Because the response says "completed", nobody will find out.

**2. Successful responses come back in two different shapes. Same lines. Confidence: high**

A normal success returns `Ok(action())`, which is the actual result, such as an invoice. The new branch returns `Ok(new { status = "completed" })` with the same 200 status. A client reading the body as an invoice gets missing or null fields and can't tell the two cases apart by status code.

**3. The exception is thrown away with no record. Same lines. Confidence: high**

The exception isn't captured (`catch (Exception)` with no variable) and nothing is logged. It also never reaches ASP.NET Core's exception handling, so the developer exception page, the 500 response and any error monitoring all stop seeing it. Real bugs will become silent and very hard to diagnose.

**4. No tests. Confidence: medium**

AGENTS.md says every new rule needs tests, and this adds a new error-mapping rule with none. That's a smaller point, since findings 1–3 mean the change shouldn't go in as written anyway.

## Recommendation

Remove the catch-all block. Unexpected exceptions should reach the framework and come back as a 500. If you want a controlled response, log the exception and return `Problem(statusCode: 500)`. Never return `Ok`.

The order of the catch blocks is fine. `Exception` comes last, so the specific handlers still run first.
