# case-07 / agents-md / run 4

- model: claude-opus-5-5
- attempt: 1
- duration_ms: 24892
- cost_usd: 0.068533
- tool calls denied: 0

---

I couldn't check this against the code. The workspace has only `AGENTS.md`, `CLAUDE.md` and some harness files. `ApprovalsController.cs`, the `Invoice` type and the `CurrentUser` type aren't there. So this review covers only the diff, and I've rated confidence with that in mind.

## Findings

**1. Logging the user's sign-in session object risks leaking secrets**
- **Where:** `ApprovalsController.cs`, the new `_logger.LogInformation` call (around line 35), `{@Session}` / `CurrentUser`.
- **What goes wrong:** The `@` tells a structured logger like Serilog to copy every public property of `CurrentUser` into the log. Sign-in objects often hold session IDs, tokens, claims, or a reference to the full `ClaimsPrincipal`. Anything in there ends up in plain text in every log sink, and anyone who can read the logs could take over that session. The approval only needs the user's name, which the code already passes to `Approve`.
- **Fix:** Log only an identifier, e.g. `"Invoice {InvoiceId} approved by {Approver}", invoice.Id, CurrentUser.Name`.
- **Confidence:** High that this is a defect. Medium on how bad it is, since I can't see which properties `CurrentUser` has.

**2. Logging the whole invoice puts customer and financial data in logs**
- **Where:** Same call, `{@Invoice}` / `invoice`.
- **What goes wrong:** This writes the entire invoice to the logs: supplier or customer details, amounts, line items and any payment fields. `AGENTS.md` treats customer data as sensitive ("Never commit … customer data"), and logs are usually kept longer and read by more people than the data store. The log line says "Invoice payload", so the full dump is clearly intended.
- **Fix:** Log the invoice ID and the new status, nothing else.
- **Confidence:** High.

**3. `_logger` may not exist in this controller (compile error)**
- **Where:** Same line.
- **What goes wrong:** The diff adds no `ILogger<ApprovalsController>` field or constructor parameter. If the controller doesn't already have one, the build fails.
- **Confidence:** Low to medium. The constructor is outside the hunk, so I can't tell.

**4. `@` does nothing with the default .NET logger**
- **Where:** Same line.
- **What goes wrong:** If the app uses the built-in .NET logging (no Serilog or similar), the `@` is ignored and each object is printed with its default `ToString()`. For a class with no override, that's just the type name. The log line then carries nothing useful. With Serilog, the problem is the reverse: findings 1 and 2.
- **Confidence:** Medium. It depends on the logging setup in `Program.cs`, which I couldn't see.

## Not part of this diff
The unchanged lines call `_approvals.Approve(...)` directly instead of going through `Handle(...)`, which `AGENTS.md` requires so service errors map to 404/409/400. If that's how the file really looks, it's an existing bug, not one this diff adds.

**Summary:** Replace the log call with something like `_logger.LogInformation("Invoice {InvoiceId} approved by {Approver}", invoice.Id, CurrentUser.Name);`. That fixes findings 1, 2 and 4, as long as `_logger` is injected (finding 3).
