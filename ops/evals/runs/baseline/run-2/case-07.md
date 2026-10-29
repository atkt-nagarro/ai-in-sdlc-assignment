# case-07 / baseline / run 2

- model: claude-opus-5-5
- attempt: 1
- duration_ms: 20156
- cost_usd: 0.0547912
- tool calls denied: 0

---

I couldn't check any of this against the code: the working directory only has the diff, with no `.cs` files. So this review is based on the diff alone, and I've noted where that limits my confidence.

## Findings

**1. The whole user/session object gets written to the logs**
`ApprovalsController.cs:36–38` (the `{@Session}` / `CurrentUser` argument)
- **What goes wrong:** The `@` operator tells the logger to serialize every public property of `CurrentUser`. A current-user object usually holds things like the user ID, email, roles and claims. It often also holds the session ID, the bearer/JWT token or other credentials. All of that would go to every log sink (files, Seq, ELK, App Insights) on every approval. Anyone who can read the logs could then pretend to be that user. That's a security problem and likely a compliance problem too (GDPR, SOC 2).
- **Fix:** Log only what you need, e.g. `CurrentUser.Name` or a user ID, as a plain value.
- **Confidence:** High that this logs too much. Medium on how bad it is, because I can't see what `CurrentUser` actually contains.

**2. The whole invoice gets written to the logs**
`ApprovalsController.cs:36–38` (the `{@Invoice}` / `invoice` argument)
- **What goes wrong:** Serializing the full invoice sends financial details and personal data to the logs: vendor bank details, addresses, tax IDs, amounts, line items. That's normally restricted data.
- **Fix:** Log `invoice.Id` (and maybe the new status) as plain values instead.
- **Confidence:** High that this logs too much. Medium on how sensitive the fields are.

**3. Logging the invoice may hit the database or throw**
Same line, `{@Invoice}`
- **What goes wrong:** If `invoice` is an EF entity with lazy-loaded links to other records, serializing it reads every link. That can fire extra database queries during logging. It can also throw `ObjectDisposedException` if the DbContext has already closed, and the approve request would then return a 500 even though the approval was saved. If the entity links back to itself, the logger walks the loop until its depth limit and produces huge log entries.
- **Confidence:** Low to medium. It depends on whether `_approvals.Approve` returns an entity or a DTO, which I couldn't see.

**4. `_logger` may not exist**
`ApprovalsController.cs:36`
- **What goes wrong:** The diff uses `_logger` but doesn't add it or inject an `ILogger<ApprovalsController>`. If neither this controller nor `ApiControllerBase` already has it, the code won't compile.
- **Confidence:** Low. It's probably already there, but you should check.

**5. The `@` may do nothing**
`ApprovalsController.cs:37`
- **What goes wrong:** `{@...}` is Serilog syntax. If the app uses the plain Microsoft logging providers without Serilog, `@` isn't understood. The log would just show each object's `ToString()`, which is usually only the type name. That would make the new log line useless rather than harmful.
- **Confidence:** Low. It depends on how logging is set up.

## Suggested replacement
```csharp
_logger.LogInformation(
    "Invoice {InvoiceId} approved by {Approver}",
    invoice.Id, CurrentUser.Name);
```
This removes findings 1, 2, 3 and 5. It also makes the log easier to search, because `InvoiceId` becomes its own field.
