# case-10 / baseline / run 3

- model: claude-opus-5-5
- attempt: 1
- duration_ms: 13346
- cost_usd: 0.038320999999999994
- tool calls denied: 0

---

The source file isn't in the working directory, so this review is based only on the diff.

## Finding 1: Every unexpected exception is reported as success
**File:** `backend/src/InvoiceApp.Api/Controllers/ApiControllerBase.cs`, lines 36–39 (the new `catch (Exception)` block)
**Confidence:** High

**What goes wrong:** Any exception that isn't one of the three already handled now returns `200 OK` with `{ status = "completed" }`. That covers `NullReferenceException`, database exceptions like `DbUpdateException` and `SqlException`, timeouts, and `OperationCanceledException`.

- **Clients are told failed operations succeeded.** In an invoice app, a create, update, or payment call that crashed partway through tells the caller "completed". The client won't retry or show an error, and the user thinks the invoice was saved or paid when it wasn't. A crash partway through can also leave data partly written, and nobody hears about it.
- **The response shape is wrong.** On success the method returns `Ok(action())`, so callers expect the action's return type, such as an invoice DTO. The fallback returns `{ status: "completed" }` instead. Clients will fail to deserialize it, or silently get null or default fields, with no sign of where the problem started.
- **Errors disappear from monitoring.** The exception is caught without a variable and never logged or rethrown. It doesn't reach the ASP.NET Core exception-handling middleware, logging, APM, or the developer exception page. 5xx error-rate alerts stop firing because the failures now count as 2xx.
- **Cancellation is masked.** When a client disconnects, `OperationCanceledException` / `TaskCanceledException` is turned into a 200 too.

**Fix:** Remove the block and let the exception reach the global exception handler, which returns 500 and logs it. If the base class has to handle it, log it and return a 500 problem response:
```csharp
catch (Exception ex)
{
    _logger.LogError(ex, "Unhandled error");
    return Problem(statusCode: StatusCodes.Status500InternalServerError);
}
```

## Finding 2 (minor, existing behavior made worse): Some argument errors become 404s
**File:** same file, lines 24 / 32 (catch ordering)
**Confidence:** Low. It depends on what the actions throw, and it isn't introduced by this diff.

`ArgumentException` is caught last, which is fine because it doesn't derive from the earlier two types. But some framework methods throw `KeyNotFoundException` for things that are really bad input, and those get mapped to 404. I'm noting it only for context. It isn't a defect in this change.

**Bottom line:** Finding 1 is serious enough that this diff shouldn't be merged as written.
