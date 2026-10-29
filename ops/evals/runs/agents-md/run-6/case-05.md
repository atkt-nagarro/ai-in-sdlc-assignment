# case-05 / agents-md / run 6

- model: claude-opus-5-5
- attempt: 1
- duration_ms: 21193
- cost_usd: 0.069543
- tool calls denied: 0

---

I couldn't check this against the source. The working directory only has `AGENTS.md`, `CLAUDE.md` and a few harness files, and `backend/` doesn't exist. So these findings come from the diff and the project rules in `AGENTS.md`. Anything that depends on how the repository or base class behaves is marked as such.

## Findings

**1. Any signed-in user can delete invoices**
- **Where:** `InvoicesController.cs`, the new `Delete` action (~line 44)
- **What goes wrong:** The action has no `[RequireRole("Admin")]`. Sign-in is still required, but any role can call it, so a `demo.approver` account can delete invoices. `AGENTS.md` says destructive actions are Admin only, and the `Update` action just below has the attribute.
- **Fix:** Add `[RequireRole("Admin")]`.
- **Confidence:** High. This is visible in the diff.

**2. Errors skip `Handle(...)`, so a missing invoice can return 500 or a false 204**
- **Where:** Same action, `_repository.Delete(id);` (~line 46)
- **What goes wrong:** The other actions are wrapped in `Handle(...)`, which turns service errors into 404, 409 or 400. This one isn't, so the result depends on what `Delete` does with an unknown id:
  - If it throws, the client gets a 500 instead of a 404.
  - If it silently does nothing or returns `false`, the client gets a 204 for an invoice that never existed. The log line also records a deletion that didn't happen, which makes the audit trail wrong.
- **Fix:** Wrap the call in `Handle(...)`, and only log after a delete actually succeeds.
- **Confidence:** High that this breaks the project convention. Medium on which of the two failures happens, because I can't see the repository's contract.

**3. Deletion bypasses the invoice lifecycle rules**
- **Where:** Same line
- **What goes wrong:** The controller calls the repository directly. `ApprovalService` owns the Draft, PendingApproval, Approved and Rejected lifecycle, so this path enforces none of it. As written, an Approved or PendingApproval invoice can be deleted with no check. Whether that should be allowed is a business rule, and `AGENTS.md` says business rules belong in Domain, not in controllers.
- **Fix:** Add a delete operation to `ApprovalService` that decides which states can be deleted, and have the controller call it through `Handle(...)`.
- **Confidence:** Medium. It clearly breaks the convention, but I can't see whether a lifecycle rule for deletion was intended.

**4. No tests**
- **Where:** The diff as a whole
- **What goes wrong:** `AGENTS.md` requires tests for every new endpoint. The diff only touches the controller, so there are no tests for the role restriction, the not-found case or state rules.
- **Confidence:** High, assuming this is the full diff.

**5. Possible compile errors**
- **Where:** Lines 46–47
- **What goes wrong:** The new code uses `_repository.Delete`, `_logger` and `CurrentUser`, and none of them appear elsewhere in the diff. If the repository interface has no `Delete` method, or the controller has no injected logger or `CurrentUser` member, this won't build.
- **Confidence:** Low. I couldn't check the files.

To confirm findings 2, 3 and 5, I'd need the repository interface, `ApiControllerBase` and `ApprovalService`.
