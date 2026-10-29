# case-01 / agents-md / run 6

- model: claude-opus-5-5
- attempt: 1
- duration_ms: 28387
- cost_usd: 0.074862
- tool calls denied: 0

---

I couldn't check this against the code. The working directory only has `AGENTS.md`, `CLAUDE.md` and a few harness files, and `backend/` isn't there. So this review is based on the diff and the conventions in `AGENTS.md` alone. Where a finding depends on code I couldn't see, I say so.

## Findings

**1. A missing or null `Ids` crashes the request with a 500**
`ApprovalsController.cs`, `foreach (var id in request.Ids)` (around new line 49)
- **What goes wrong:** `Ids` is declared as nullable (`List<string>?`), but it's used without a null check. A body of `{}` or `{"ids": null}` throws a `NullReferenceException`, which becomes a 500 instead of a 400. The compiler will also warn about this (CS8602) if nullable checks are on.
- **Confidence:** High.

**2. Service errors bypass `Handle(...)`, so they return 500 instead of 404/409/400**
`ApprovalsController.cs`, `results.Add(_approvals.Approve(id, CurrentUser.Name));`
- **What goes wrong:** `AGENTS.md` says controllers must use `Handle(...)` so service errors map to 404, 409 and 400. This endpoint calls `_approvals.Approve` directly. An unknown ID, or an invoice that isn't in `PendingApproval` (already approved, rejected, still a draft), will throw out of the action and come back as a 500.
- **Confidence:** High that the convention is broken. Medium-high on the exact status code, since I couldn't read `ApiControllerBase` or the existing single-invoice `Approve` action.

**3. A failure partway through leaves some invoices approved, and the client isn't told which**
Same loop.
- **What goes wrong:** Each `Approve` call saves on its own. If the 3rd of 5 IDs fails, invoices 1–2 stay approved, 3–5 aren't, and the client only gets an error, with no list of what succeeded. A retry with the same list then fails on ID 1 because it's already approved. Repeated IDs in one request cause the same problem: the second approval of the same invoice fails after the first succeeded.
- **Fix:** Decide the behaviour and put it in `ApprovalService`. Either check every invoice first and approve all or none, or return a result for each ID.
- **Confidence:** High.

**4. Bulk-approval logic is in the controller instead of the Domain project**
- **What goes wrong:** How a batch is processed (all-or-nothing vs. partial, handling repeated IDs, empty lists, a maximum batch size) is a business rule. `AGENTS.md` says those belong in Domain, never in controllers. This should be something like `ApprovalService.ApproveMany(ids, approver)`, with the controller as a thin wrapper.
- **Confidence:** Medium-high. It's a convention violation, and fixing it is also the natural fix for #3.

**5. No tests**
- **What goes wrong:** `AGENTS.md` says every new endpoint needs tests using `FakeInvoiceRepository`. The diff adds none. Cases worth covering: null or empty `Ids`, an unknown ID, an invoice that isn't pending, repeated IDs, and a mixed batch.
- **Confidence:** High, for what's in this diff.

**6. No limit on batch size**
- **What goes wrong:** Any approver can send any number of IDs in one request. That's a minor abuse risk, and with the partial-failure problem in #3 it makes a large accidental approval harder to undo.
- **Confidence:** Low-medium. This depends on what the product wants.

## Checked and not a problem (as far as the diff shows)
- **Role:** `[RequireRole("Approver")]` matches the existing `Reject` action. Whether Admin is also allowed depends on how `RequireRole` works, which I couldn't see. If it doesn't treat Admin as covering Approver, the existing actions have the same gap.
- **Routes:** `bulk-approve` doesn't clash with `{id}/approve` or `{id}/reject`.
- **Response:** Calling `results.Select(DecisionResponse.From)` on the already-built list is fine.

If you can make `backend/` available, I can confirm #2 and the role question against `ApiControllerBase`, `RequireRole` and `ApprovalService`.
