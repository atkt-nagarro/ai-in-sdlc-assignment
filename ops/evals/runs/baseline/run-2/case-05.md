# case-05 / baseline / run 2

- model: claude-opus-5-5
- attempt: 1
- duration_ms: 17250
- cost_usd: 0.042856200000000004
- tool calls denied: 0

---

The working directory has no source files, so I reviewed the diff by itself. I couldn't check `ApiControllerBase`, the repository, or the rest of the controller, and the confidence levels below reflect that.

## Findings

**1. The delete endpoint has no role check, while the edit endpoint below it requires Admin**
- **File/line:** `InvoicesController.cs`, new `Delete` action (around line 44–45, the `[HttpDelete("{id}")]` attribute)
- **What goes wrong:** `Update` right below it has `[RequireRole("Admin")]`, but `Delete` doesn't. So it's protected only by whatever applies to the whole controller, if anything. Most likely any logged-in user can delete any invoice, which is more access than editing needs. Deleting is the more destructive action, so it should be at least as locked down.
- **Fix:** Add `[RequireRole("Admin")]`, or whatever role delete should need.
- **Confidence:** High. The difference sits right next to it in the same diff. The only way this is fine is if delete is meant to be open to non-admins, and that seems unlikely.

**2. Errors skip the controller's usual `Handle(...)` wrapper**
- **File/line:** `InvoicesController.cs` ~line 47, `_repository.Delete(id);`
- **What goes wrong:** The action just above (`return Handle(() => _repository.Add(invoice));`) shows the controller's normal pattern: repository calls go through `Handle`, which most likely turns exceptions (not found, validation errors) into proper HTTP responses. `Delete` calls the repository directly. If the id doesn't exist, the caller probably gets a 500, or a 204 for an invoice that was never there, instead of a 404.
- **Fix:** Something like `return Handle(() => _repository.Delete(id), NoContent)`, or whatever `Handle` overload fits, and keep the log line inside the success path.
- **Confidence:** Medium. It clearly breaks the local pattern. What actually happens depends on what `Handle` and `_repository.Delete` do with a missing id, and I couldn't see either.

**3. The audit log can say "deleted" when nothing was deleted**
- **File/line:** `InvoicesController.cs` ~line 48, `_logger.LogInformation(...)`
- **What goes wrong:** If `_repository.Delete` does nothing for an unknown id instead of throwing, the log still records "Invoice X deleted by Y" and the caller gets 204. That makes the audit trail wrong, and since there's no ownership check, it can't be trusted for incident review either.
- **Confidence:** Low to medium. This only happens if `Delete` doesn't throw on a missing id.

**4. Possible null reference on `CurrentUser.Name`**
- **File/line:** `InvoicesController.cs` ~line 48
- **What goes wrong:** If `CurrentUser` can be null, for example on an anonymous request because of finding 1, this throws after the delete has already happened. The client gets a 500 even though the invoice is gone.
- **Confidence:** Low. It depends on how `ApiControllerBase.CurrentUser` is implemented and whether authentication is required for the whole controller.

The main thing to fix is finding 1. To confirm 2–4 I'd need `ApiControllerBase` (for `Handle` and `CurrentUser`) and the repository's `Delete` method.
