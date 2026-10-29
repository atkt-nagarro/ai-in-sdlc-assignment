# case-01 / agents-md / run 4

- model: claude-opus-5-5
- attempt: 1
- duration_ms: 28450
- cost_usd: 0.0763816
- tool calls denied: 0

---

I couldn't check any of this against the actual code. The workspace only has `AGENTS.md` and `CLAUDE.md`, with no `backend/` folder. So this review is based on the diff plus the project conventions. Line numbers count from the hunk header (`+38`) in the new file.

## Findings

**1. `ApprovalsController.cs:49`: a missing or null `Ids` crashes the request with a 500**
`Ids` is declared as `List<string>?`, but `foreach (var id in request.Ids)` never checks it for null. A body like `{}` or `{"ids": null}` throws a `NullReferenceException`, and the client gets a 500 instead of a 400. The compiler would also warn about this (CS8602) if nullable checking is on.
*Confidence: high.*

**2. `ApprovalsController.cs:51`: errors from the service aren't mapped to 404/409/400**
Every other endpoint wraps its service call in `Handle(...)` so service errors become 404, 409 or 400. This one calls `_approvals.Approve` directly. An unknown id, or an invoice that isn't in `PendingApproval`, will escape as an unhandled exception and return 500.
*Confidence: high that it breaks the convention. Medium-high on the 500, which assumes the service reports errors by throwing, as `Handle` suggests.*

**3. `ApprovalsController.cs:49–52`: one failure leaves earlier approvals applied, and the client isn't told**
Each `Approve` call is saved as it goes. If the third of five ids fails, the first two stay approved, the rest are skipped, and the client gets a single error with no list of what succeeded. Retrying the same request then fails on the first id, because it's already approved. The same happens with a duplicate id in the list: the second `Approve` on that invoice fails after the first one went through. The endpoint should either check everything before approving anything, or return a result for each id.
*Confidence: high.*

**4. `ApprovalsController.cs:45–55`: the bulk-approval rules sit in the controller**
How a bulk approval behaves (all-or-nothing vs. partial, duplicate handling, limits) is a business rule. `AGENTS.md` says those belong in `ApprovalService` in the Domain project, not in controllers. Moving the loop into something like `ApprovalService.ApproveMany(ids, approver)` would also make finding 3 testable.
*Confidence: medium. A bare loop is arguably just orchestration, but the failure behaviour above makes it a rule.*

**5. No tests in the diff**
`AGENTS.md` says every new endpoint needs tests using `FakeInvoiceRepository`. Nothing is added for the happy path, null or empty `Ids`, unknown ids, already-approved invoices, or the role restriction.
*Confidence: high, based on what the diff contains.*

**6. `ApprovalsController.cs:41`: no limit on how many ids one request can approve**
The list can be any size, so a single request can approve as many invoices as it lists. That's also a large blast radius for a mistaken or malicious call.
*Confidence: low-medium. It's a hardening gap rather than a functional bug.*

## Checked and not a problem
- **`[RequireRole("Approver")]` vs. "Approver or Admin":** this matches the existing `Reject` action. Whether Admin is let through depends on how `RequireRole` works, which I couldn't see. If the other approval actions list both roles, this one should too.
- **Route clash:** `bulk-approve` doesn't conflict with `{id}/approve` or `{id}/reject`.
- **`results.Select(DecisionResponse.From)`:** `results` is already a fully built list, so there's no problem with deferred evaluation.
- **Self-approval and other approval rules:** these still apply, because each id goes through `_approvals.Approve`.
