# case-07 / agents-md / run 5

- model: claude-opus-5-5
- attempt: 1
- duration_ms: 24087
- cost_usd: 0.07402239999999999
- tool calls denied: 0

---

I couldn't check this against the source. The workspace only has `AGENTS.md`, `CLAUDE.md` and some harness files, and `backend/` isn't there. So I reviewed the diff alone, and anything that depends on what `CurrentUser`, `Invoice` or `_logger` actually are is marked as an inference.

Line numbers refer to the new file (the hunk starts at line 28).

## Findings

**1. The whole sign-in session goes into the log**
- **File:** `backend/src/InvoiceApp.Api/Controllers/ApprovalsController.cs`, lines 35–36 (`Session: {@Session}` … `CurrentUser`)
- **What goes wrong:** `@` tells structured loggers like Serilog to log every property of the object, not just a summary. `CurrentUser` comes from the `Auth/` sign-in code, so it probably holds more than a name: claims, roles, maybe a session ID or token. If so, every approval writes data that can be used to sign in into the logs. Anyone who can read the logs could then replay the session as an Approver or Admin. Even if it turns out to hold only a name and role, the label "Session" shows the intent was to log the session object. The audit trail only needs `CurrentUser.Name`, which is already passed to `Approve`.
- **Fix:** Log scalar values only, for example `"Invoice {InvoiceId} approved by {Approver}", invoice.Id, CurrentUser.Name`.
- **Confidence:** High that it's a defect. Medium on how bad it is, since I couldn't see what `CurrentUser` contains.

**2. The full invoice, with customer data, goes into the log**
- **File:** same file, lines 35–36 (`Invoice payload: {@Invoice}` … `invoice`)
- **What goes wrong:** Same issue: every field of the approved invoice is written to the log. In an invoice system that typically means supplier or customer names, amounts and possibly bank or payment details. That copies customer data into logs, which usually have wider access and longer retention than the data store. `AGENTS.md` treats customer data as sensitive ("Never commit … customer data"). Logging it on every approval goes against that intent.
- **Fix:** Log the invoice ID and the new status, not the whole object.
- **Confidence:** Medium-high. I'm assuming `Invoice` has the usual invoice fields; I couldn't see its definition.

**3. `_logger` might not exist in this controller**
- **File:** same file, line 34
- **What goes wrong:** The diff doesn't add an `ILogger<ApprovalsController>` field or constructor parameter. If the controller doesn't already have one, this won't compile.
- **Confidence:** Low. It may already be declared outside the hunk; check before merging.

## Not caused by this diff, but worth noting
- `Approve` calls `_approvals.Approve(...)` directly rather than going through `Handle(...)`, which `AGENTS.md` requires. That's in the unchanged lines, so this diff doesn't cause it. It does mean a missing or wrongly-stated invoice probably returns a 500 instead of a 404 or 409.

Findings 1 and 2 are the ones that matter. Both go away if you log `invoice.Id` and `CurrentUser.Name` as plain values instead of using `{@...}` on the whole objects.
