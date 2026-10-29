# case-07 / baseline / run 1

- model: claude-opus-5-5
- attempt: 1
- duration_ms: 20389
- cost_usd: 0.0649358
- tool calls denied: 0

---

I only had the diff to work from. The working directory has no source files (just `.message`, `result.json`, `stderr.txt`), so I couldn't check what `CurrentUser` or the invoice type contain, or whether `_logger` exists. My confidence levels reflect that.

## Findings

**1. The whole user/session object is written to the logs**
- **File/line:** `ApprovalsController.cs`, the new `_logger.LogInformation(...)` call (lines ~34–36), the `{@Session}` / `CurrentUser` argument.
- **What goes wrong:** The `@` tells Serilog-style structured logging to serialize the object's public properties one by one, instead of calling `ToString()`. `CurrentUser` on an authenticated controller usually holds identity data: user ID, email, roles, claims, and sometimes the raw bearer token, session ID or refresh token. All of that would land in plain text in every log sink (files, Seq, ELK, App Insights). That's a credential/PII leak. People with log access could hijack sessions, and it may break GDPR/SOC2 rules on what logs can hold. The label "Session" suggests the author knows it's session data.
- **Fix:** Log only what you need, e.g. `CurrentUser.Name` or a user ID: `"Invoice {InvoiceId} approved by {Approver}", invoice.Id, CurrentUser.Name`.
- **Confidence:** High that this is a defect. Medium on exactly what leaks, since I couldn't see the `CurrentUser` type.

**2. The whole invoice is written to the logs**
- **File/line:** Same call, the `{@Invoice}` / `invoice` argument.
- **What goes wrong:** This serializes the entire invoice entity. Invoices usually carry sensitive financial data and PII: supplier bank details/IBAN, tax IDs, addresses, line items, amounts. Once it's in the logs it gets copied to log stores with weaker access control and longer retention than the database. If the invoice is an EF entity with navigation properties, serializing it can also walk related objects (supplier, line items, approval history), which makes the leak bigger and adds per-request cost. Serilog's depth limit stops infinite recursion, but each log entry can still get large.
- **Fix:** Log the identifier and maybe the new status: `{InvoiceId}`, `{Status}`.
- **Confidence:** High that logging the full payload is wrong. Medium on how sensitive it actually is, since I couldn't see the invoice model.

**3. `_logger` may not exist in this controller**
- **File/line:** Same call, `_logger`.
- **What goes wrong:** The diff adds no field or constructor injection for `ILogger<ApprovalsController>`. If neither this class nor `ApiControllerBase` already has `_logger`, the build fails.
- **Confidence:** Low. It's probably already there, but I couldn't confirm it.

## Not a finding
A null `invoice` (not found) isn't a new problem here. Structured logging renders null without throwing, and the existing `DecisionResponse.From(invoice)` call was already exposed to it.

**Bottom line:** Findings 1 and 2 should block the merge. Change the log line to record IDs (invoice ID, approver name/ID) instead of serializing the invoice and session objects.
