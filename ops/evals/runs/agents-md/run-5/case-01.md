# case-01 / agents-md / run 5

- model: claude-opus-5-5
- attempt: 1
- duration_ms: 29083
- cost_usd: 0.0796404
- tool calls denied: 0

---

I couldn't check this against the source. The working directory has only `AGENTS.md`/`CLAUDE.md` and no `backend/` folder, so I can't see `ApiControllerBase.Handle`, `ApprovalService.Approve` or the rest of `ApprovalsController`. The findings below come from the diff plus the project conventions in `AGENTS.md`. Line numbers are in the new file, `backend/src/InvoiceApp.Api/Controllers/ApprovalsController.cs`.

## Defects

**1. Null `Ids` crashes the request with a 500 (line 49, `foreach (var id in request.Ids)`)**
`Ids` is declared `List<string>?`, but it's looped over with no null check. A body of `{}` or `{"ids": null}` passes model binding and then throws `NullReferenceException`, which returns a 500 instead of a 400. The compiler should also warn about this (CS8602).
Confidence: **high**.

**2. Service errors skip `Handle(...)`, so bad IDs return 500 instead of 404/409/400 (line 51)**
`AGENTS.md` says controllers must use `Handle(...)` so service errors map to 404, 409 and 400. This action calls `_approvals.Approve` directly. An unknown ID or an invoice that isn't in `PendingApproval` throws an exception that nothing maps to a status code, so the client gets a 500.
Confidence: **high** that the convention is broken. **Medium-high** that this produces a 500, since I couldn't read `Handle` or check for a global exception filter.

**3. Partial failure leaves invoices approved and the client can't tell which (lines 49–52)**
Each approval is saved as the loop runs. If the third of five IDs fails, the first two are already Approved, but the response is an error with no list of what succeeded. Retrying the same request then fails on the first ID, because it's no longer pending. So a bulk request can neither be retried safely nor rolled back. The fix is either to check every ID before approving any, or to return a result for each ID.
Confidence: **high**.

**4. Duplicate IDs fail partway through (lines 49–51)**
`["INV-1","INV-1"]` approves INV-1 and then fails on the second copy because it's already Approved. That triggers defect 3. Removing duplicates first (`Distinct()`) avoids it.
Confidence: **medium-high**. It depends on `Approve` rejecting invoices that aren't pending, which is what the lifecycle in `AGENTS.md` implies.

**5. The bulk rule lives in the controller (lines 47–54)**
How a batch behaves (all-or-nothing vs. per item, duplicates, size limits) is a business rule. `AGENTS.md` says business rules go in Domain and must never be in controllers. This should be something like `ApprovalService.ApproveMany(ids, approver)`, with the controller just wrapping it in `Handle(...)`. Doing that also gives one place to fix defects 3 and 4.
Confidence: **high** (convention violation).

**6. No tests (whole diff)**
`AGENTS.md` says every new rule or endpoint needs tests using `FakeInvoiceRepository`. The diff has none. At minimum it should cover null or empty `Ids`, an unknown ID, an invoice that isn't pending, duplicates, and the role check.
Confidence: **high**, based on the diff as shown.

## Lower-severity
- **No limit on batch size (line 41):** one request can approve any number of invoices with nothing capping it. Confidence: **low-medium** (hardening, not a functional bug).
- **An empty list returns `200 []` (line 54):** this is harmless, but think about whether it should be a 400. Confidence: **low**.

## Checked, no problem found
- `[RequireRole("Approver")]` matches the existing `Reject` action. Whether Admin also gets through depends on how `RequireRole` is implemented, and it's the same pattern as the existing actions.
- The `bulk-approve` route doesn't clash with `{id}/approve` or `{id}/reject`, because the number of path segments differs.
- Declaring the request `record` inside the controller follows the convention.
