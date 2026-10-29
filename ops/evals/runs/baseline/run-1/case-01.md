# case-01 / baseline / run 1

- model: claude-opus-5-5
- attempt: 1
- duration_ms: 23599
- cost_usd: 0.07765739999999999
- tool calls denied: 0

---

I couldn't open the code. The working directory has only `.message`, `result.json` and `stderr.txt`, and no `backend/` tree. So this review is based on the diff alone. I couldn't see `_approvals.Approve`, the single-invoice `Approve` action above line 38, or `DecisionResponse.From`. Findings that depend on those say so.

## Findings

**1. Crash when `Ids` is missing or null**
- **File/line:** `ApprovalsController.cs`, `foreach (var id in request.Ids)` (about line 49)
- **What goes wrong:** `Ids` is declared as nullable (`List<string>?`). A body of `{}` or `{"ids": null}` passes model binding and then crashes the loop with a `NullReferenceException`. The client gets a 500 instead of a 400. The `?` suggests null was expected but never checked.
- **Confidence:** High.

**2. A failure partway through leaves some invoices approved and the client can't tell which**
- **File/line:** the loop body, `results.Add(_approvals.Approve(id, CurrentUser.Name));` (about line 51)
- **What goes wrong:** Each `Approve` call presumably saves on its own. If the call for item *k* throws (not found, already approved/rejected, invalid state), items 0..k-1 stay approved. The request then fails as a whole, and the response says nothing about which ones succeeded. Retrying the same list will probably fail on the first item, which is now already approved. You need either a transaction around the whole batch or a per-item result (`{id, success, error}`).
- **Confidence:** Medium-high. It depends on `Approve` throwing on bad input, which is the usual pattern, and I couldn't verify it.

**3. Checks done in the single-invoice action may be skipped**
- **File/line:** the whole `BulkApprove` method compared with the existing `Approve` action (lines about 30–39, not shown)
- **What goes wrong:** The new method calls the service directly. Any checks the existing single-invoice endpoint does in the controller are skipped here: existence/404 handling, "can't approve your own invoice", approval amount limits, state checks. If the single endpoint handles a null return from `Approve` for not-found, then `DecisionResponse.From(null)` would also throw here.
- **Confidence:** Low-medium. Worth checking the single-invoice action against this one.

**4. No limit on how many IDs one request can send**
- **File/line:** `BulkApproveRequest(List<string>? Ids)` and the loop
- **What goes wrong:** A caller can send thousands of IDs in one request. That means one long synchronous request holding a thread and possibly DB locks, plus a very large response. Add a maximum count and reject anything over it with a 400.
- **Confidence:** Medium that it's a real problem (it depends on how much you trust Approver-role users). High that no limit exists.

**5. Duplicate IDs aren't handled**
- **File/line:** the loop (about line 49)
- **What goes wrong:** `["A","A"]` approves A twice. Depending on `Approve`, that either throws on the second call (triggering the partial failure in #2) or records two approval events. `Ids.Distinct()` would avoid both.
- **Confidence:** Medium.

## Suggested shape
```csharp
if (request?.Ids is not { Count: > 0 } ids) return BadRequest("Ids is required.");
if (ids.Count > MaxBulk) return BadRequest($"At most {MaxBulk} ids per request.");
foreach (var id in ids.Distinct()) { /* per-item try/catch, or one transaction */ }
```

If you can share `ApprovalService.Approve` and the rest of `ApprovalsController.cs`, I can confirm or rule out #2, #3 and #5.
