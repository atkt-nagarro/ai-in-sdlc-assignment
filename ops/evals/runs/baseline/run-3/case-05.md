# case-05 / baseline / run 3

- model: claude-opus-5-5
- attempt: 1
- duration_ms: 16096
- cost_usd: 0.0445762
- tool calls denied: 0

---

I couldn't check any of this against the code. The working directory has no `.cs` files, so I reviewed only the diff. Things the diff doesn't show, like `Handle`, `RequireRole`, `CurrentUser` and `_repository.Delete`, are inferred from how they're used.

### 1. Missing authorization on Delete (high confidence)
**File:** `InvoicesController.cs`, the new `Delete` action (around line 44)

The `Update` action right below it has `[RequireRole("Admin")]`, but `Delete` doesn't. So any caller who gets past the controller-level auth can permanently delete any invoice by ID. If the controller has no class-level `[Authorize]`, that includes anonymous callers. Deleting is at least as risky as updating, so this looks like an accidental omission rather than a choice. There's also no check that the caller owns the invoice or belongs to the right tenant, but that may be equally missing on `Update`.

**Fix:** Add `[RequireRole("Admin")]`, or whatever role policy applies to destructive operations.

### 2. Skips the `Handle(...)` wrapper the other actions use (medium-high confidence)
**File:** `InvoicesController.cs`, line ~47 (`_repository.Delete(id);`)

The action just above returns `Handle(() => _repository.Add(invoice))`. That wrapper is probably how the base controller turns repository failures (not found, validation, conflicts) into proper HTTP responses. `Delete` calls the repository directly, so one of two things happens:
- If `Delete` throws for a missing ID, the client gets an unhandled 500 instead of a 404.
- If `Delete` silently does nothing for a missing ID, the action still returns `204 NoContent` and logs "Invoice X deleted" for an invoice that never existed. That puts a false entry in what looks like an audit log.

**Fix:** Use `return Handle(() => _repository.Delete(id));`, or an equivalent that maps "not found" to 404, and only log after the delete actually succeeds.

### 3. `CurrentUser.Name` can throw after the delete has already happened (low-medium confidence)
**File:** `InvoicesController.cs`, line ~48 (the `_logger.LogInformation` line)

Because of finding 1, this endpoint may be reachable by callers with no resolved identity. If `CurrentUser` or `.Name` is null, the logging line throws a `NullReferenceException`. The invoice is already gone by then, so the client gets a 500 for an operation that succeeded and no log entry is written. How likely this is depends on how `CurrentUser` is implemented, which I couldn't see. Fixing finding 1 mostly removes the risk.

Nothing else stood out. The log call uses structured placeholders, so the user-supplied `id` doesn't create a log-injection problem.
