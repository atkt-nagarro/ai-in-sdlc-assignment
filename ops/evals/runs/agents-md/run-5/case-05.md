# case-05 / agents-md / run 5

- model: claude-opus-5-5
- attempt: 1
- duration_ms: 20856
- cost_usd: 0.0676274
- tool calls denied: 0

---

I couldn't check this against the source. The working directory only has `AGENTS.md`, `CLAUDE.md` and a few harness files, with no `backend/` folder. So these findings come from the diff and the project rules in `AGENTS.md`. I couldn't confirm what `IInvoiceRepository.Delete`, `ApiControllerBase.Handle` or `_logger` actually look like.

### 1. Any signed-in user can delete invoices (missing Admin check)
- **File/line:** `backend/src/InvoiceApp.Api/Controllers/InvoicesController.cs`, new lines 44–45 (`[HttpDelete("{id}")]` / `public IActionResult Delete(string id)`)
- **What goes wrong:** The method has no `[RequireRole("Admin")]`. Every endpoint requires sign-in, but that's the only check here, so a `demo.approver` user can delete any invoice. `AGENTS.md` says destructive actions are Admin only, and the `Update` method right below has `[RequireRole("Admin")]`.
- **Fix:** Add `[RequireRole("Admin")]`.
- **Confidence:** High.

### 2. Errors skip `Handle(...)`, so an unknown id gives 500 or a false 204
- **File/line:** same file, new line 47 (`_repository.Delete(id);`) and line 49 (`return NoContent();`)
- **What goes wrong:** The call isn't wrapped in `Handle(...)`, which maps service errors to 404, 409 and 400. If the repository throws for a missing id, the client gets a 500 instead of a 404. If it quietly does nothing, the client gets a 204 and the log says "deleted" for an invoice that never existed.
- **Fix:** Use `return Handle(() => ...)` like `Create` does above it, and only log after the delete succeeds.
- **Confidence:** High that this breaks the project convention. Medium on which of the two outcomes happens, because I can't see the repository code.

### 3. Deleting skips the approval rules
- **File/line:** same file, new line 47
- **What goes wrong:** The controller calls the repository directly, so `ApprovalService` never gets a say. As written, an Approved invoice, or one waiting for approval, can be deleted with no check. `AGENTS.md` says `ApprovalService` owns the invoice lifecycle and business rules belong in the Domain project, not controllers. Even if the rule is "any status can be deleted", that decision belongs in Domain, where a status check can return 409.
- **Fix:** Add a delete method to `ApprovalService` (in Domain) that enforces the allowed statuses, and call it through `Handle(...)`.
- **Confidence:** Medium-high. It clearly breaks the stated architecture. Whether deleting an Approved invoice is a real bug depends on business rules I can't see, but it's very likely unintended.

### 4. No tests for the new endpoint
- **File/line:** missing from the diff (there are no changes under `backend/tests/InvoiceApp.Tests`)
- **What goes wrong:** `AGENTS.md` requires tests for every new rule or endpoint, using `FakeInvoiceRepository`. There are none for the success path, unknown id, wrong role, or deleting a non-deletable status.
- **Confidence:** High, based on the diff as given.

### Could not verify
- Whether `IInvoiceRepository` actually has a `Delete(string)` method, and whether `FakeInvoiceRepository` and the in-memory repository implement it. If not, the build fails.
- Whether `_logger` and `CurrentUser` exist on the controller or `ApiControllerBase`.

If you can share the controller, `ApiControllerBase`, the repository interface and `ApprovalService`, I can confirm findings 2 and 3 and check these last two points.
