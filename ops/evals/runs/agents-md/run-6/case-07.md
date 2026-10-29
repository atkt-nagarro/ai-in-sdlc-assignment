# case-07 / agents-md / run 6

- model: claude-opus-5-5
- attempt: 1
- duration_ms: 26085
- cost_usd: 0.0732034
- tool calls denied: 0

---

I could only review the diff itself. The working directory holds just `AGENTS.md` and `CLAUDE.md`, with none of the backend source. So I couldn't check what `Invoice`, `CurrentUser` or `_logger` actually contain. Each confidence rating below reflects that.

## Findings

**1. Logging the whole invoice exposes invoice and customer data**
- **File/line:** `backend/src/InvoiceApp.Api/Controllers/ApprovalsController.cs`, new lines 34–36 (`{@Invoice}`, `invoice`)
- **What goes wrong:** The `@` operator unpacks the whole object into the log, so every field of the invoice gets logged: amounts, vendor or customer names, and any bank or payment details on the model. The logs then hold a copy of business and customer data. That breaks the "never customer data" rule, and log storage usually has looser access controls and longer retention than the data store. Nothing in the message needs the full object. The invoice ID and the approver are enough for an audit line.
- **Fix:** Log only named fields, e.g. `_logger.LogInformation("Invoice {InvoiceId} approved by {Approver}", invoice.Id, CurrentUser.Name);`.
- **Confidence:** High that this is a defect. Medium on exactly which sensitive fields leak, because I couldn't see the `Invoice` type.

**2. Logging the signed-in user's session could leak login tokens**
- **File/line:** Same file, lines 35–36 (`Session: {@Session}`, `CurrentUser`)
- **What goes wrong:** `CurrentUser` is unpacked in full, and the code labels it "Session". It probably carries more than a name: roles and claims, a session or cookie ID, and possibly a token. Anyone who can read the logs could then take over a signed-in session. Even in the best case, it writes the user's personal details on every approval.
- **Fix:** Drop it. `CurrentUser.Name` is already the right thing to log, as in the fix for finding 1.
- **Confidence:** High that logging this object is wrong. Medium that it actually contains a session or token value, because I couldn't see the `Auth/` types.

**3. `@` may not do anything, depending on the logging library**
- **File/line:** Same file, line 35
- **What goes wrong:** With the built-in `Microsoft.Extensions.Logging` console and debug outputs, `@` is ignored and the object is printed with `ToString()`. For a class, that's usually just its type name, so the "payload" in the log is useless. With Serilog or a similar library, the full object is written out, which is findings 1 and 2. Either way the line doesn't do what it's meant to do safely.
- **Confidence:** Medium. It depends on which logging library `Program.cs` sets up.

**4. `_logger` might not exist, so the code might not compile**
- **File/line:** Same file, line 34
- **What goes wrong:** The diff adds no `ILogger<ApprovalsController>` field or constructor parameter. If the controller doesn't already have one, the build fails.
- **Confidence:** Low. It's probably already there, but this hunk doesn't show it.

## Problems already there, not caused by this diff
- `Approve` calls `_approvals.Approve(...)` directly instead of going through `Handle(...)`. Service errors therefore won't map to 404/409/400 as `AGENTS.md` requires.
- `[RequireRole("Approver")]` appears to leave out Admin, but the rules say approvals are "Approver or Admin". Whether this is a bug depends on how `RequireRole` handles Admin. I couldn't check that.

Fixing findings 1 and 2 with the structured log line above also fixes finding 3.
