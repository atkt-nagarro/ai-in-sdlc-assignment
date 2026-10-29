# case-05 / agents-md / run 4

- model: claude-opus-5-5
- attempt: 1
- duration_ms: 25754
- cost_usd: 0.0737476
- tool calls denied: 0

---

I reviewed this from the diff alone. The working directory only has `AGENTS.md`, `CLAUDE.md` and some harness files, not the `backend/` source. So I couldn't check `ApiControllerBase`, the repository interface or the existing tests. Where a finding depends on code I couldn't see, I say so.

## Findings

**1. The delete endpoint isn't restricted to Admins**
- **Where:** `InvoicesController.cs:44–45`, the `Delete` action.
- **What goes wrong:** There is no `[RequireRole("Admin")]`, so any signed-in user can delete any invoice, including someone who is only an Approver. The project rules say destructive actions are Admin only. The `Update` action right below it has the attribute, which suggests it was simply left off here.
- **Fix:** Add `[RequireRole("Admin")]` under `[HttpDelete("{id}")]`.
- **Confidence:** High.

**2. Not using `Handle(...)`, so bad IDs give the wrong response**
- **Where:** `InvoicesController.cs:47–49`.
- **What goes wrong:** The other actions wrap their work in `Handle(...)` so that service errors become 404, 409 or 400. Here the call is made directly, and one of two things happens, depending on how `Delete` behaves in the repository (which I couldn't see):
  - If it throws for an unknown ID, the client gets a 500 instead of a 404.
  - If it quietly does nothing for an unknown ID, the client gets a 204 "success" and the log says "Invoice X deleted" when nothing was deleted. That makes the audit log wrong.
- **Fix:** Use `return Handle(() => { _repository.Delete(id); ... });`, or the equivalent, and make sure a missing invoice produces the not-found error that `Handle` turns into a 404. Log only after the delete has actually succeeded.
- **Confidence:** High that this breaks the `Handle` convention. Medium on which of the two failures happens.

**3. Any invoice can be deleted, whatever its status, and the controller skips the business rules**
- **Where:** `InvoicesController.cs:47`.
- **What goes wrong:** The controller calls the repository directly. Nothing checks the invoice's status, so Approved or PendingApproval invoices can be removed, which wipes out the record of the approval. `ApprovalService` is supposed to own the invoice lifecycle, and the rules say business logic belongs in the Domain project, not in controllers. If deletion should be limited by status (for example Draft only, or never once Approved), that check is missing and has no home.
- **Fix:** Add a domain method, for example `ApprovalService.Delete(id)`, that enforces the allowed statuses and raises a conflict error that `Handle` maps to 409. Call that from the controller.
- **Confidence:** Medium. That it bypasses the rules is clear, but whether deleting Approved invoices should be blocked is a product decision.

**4. No tests**
- **Where:** The diff as a whole.
- **What goes wrong:** The rules say every new endpoint needs tests using `FakeInvoiceRepository`. The diff has none: no check that non-Admins are refused, that a missing ID returns 404, or that status rules (if added) are enforced.
- **Fix:** Add cases to `InvoicesControllerTests`, and to `ApprovalServiceTests` if the rule moves into the domain.
- **Confidence:** High that the diff has no tests.

**5. It may not compile**
- **Where:** `InvoicesController.cs:47–48`.
- **What goes wrong:** The diff doesn't add `Delete` to the repository interface or its in-memory implementation, and doesn't add a `_logger` field or `CurrentUser` property. If they don't already exist, this won't build. I couldn't check.
- **Confidence:** Low, because it depends on code I couldn't see.

Findings 1 and 2 are the ones I'd block the merge on.
