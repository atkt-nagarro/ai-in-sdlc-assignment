# case-02 / agents-md / run 6

- model: claude-opus-5-5
- attempt: 1
- duration_ms: 24562
- cost_usd: 0.073447
- tool calls denied: 0

---

I couldn't check this against the rest of the code. The workspace only has `AGENTS.md`, `CLAUDE.md` and the diff, with no `backend/` source. The findings below come from the diff plus the project conventions in `AGENTS.md`. Line numbers are new-file lines worked out from the hunk header (`+22`).

## Findings

### 1. SQL injection through `customer`: `InvoicesController.cs:28`
**What goes wrong:** `customer` comes straight from the query string and is pasted into the SQL. A request like `?customer=' OR 1=1 --` returns every invoice. Stacked queries such as `'; DELETE FROM Invoices; --` could also run if the driver allows them. Any signed-in user can do this, and no role check is needed.
**Fix:** Use parameters (`LIKE @pattern` with `pattern = "%" + customer + "%"`). Better still, go through the repository, as in finding 3.
**Confidence:** High.

### 2. SQL injection through `status`: `InvoicesController.cs:32`
**What goes wrong:** This is the same flaw as finding 1, using the optional `status` parameter (`?customer=x&status=' OR '1'='1`).
**Fix:** Parse `status` into the domain status enum (Draft / PendingApproval / Approved / Rejected) and return 400 if parsing fails. Pass the result as a parameter or a typed filter, never as SQL text.
**Confidence:** High.

### 3. `_queries` and raw SQL don't fit this system: `InvoicesController.cs:35` (and 28)
**What goes wrong:** `AGENTS.md` says storage is an in-memory repository and that no database exists. Only `ops/`, which describes a *planned* deployment, mentions one. So either:
- `_queries` isn't declared or injected, and the build fails, or
- it was added outside this hunk, which brings a database dependency into a system that has none.

In both cases, the controller would be holding query logic. That breaks the rules "business rules go in the Domain project, never in controllers" and "repositories are interfaces in Domain with an in-memory implementation in Api."
**Fix:** Add a `Search(customer, status)` method to the Domain repository interface (or a Domain service). Implement it in the in-memory repository and call it from the controller. Finding 2's enum change fits naturally here.
**Confidence:** High that this breaks the conventions. Medium-high that it fails to compile, since I can't see the rest of the class.

### 4. No tests for the new endpoint
**What goes wrong:** `AGENTS.md` says every new endpoint needs tests using `FakeInvoiceRepository`, and this diff adds none.
**Confidence:** High, for the diff as shown.

### 5. An empty `customer` returns every invoice; LIKE wildcards aren't escaped: `InvoicesController.cs:28`
**What goes wrong:** `?customer=` produces `LIKE '%%'`, which matches every row. A `%` or `_` in the input also acts as a wildcard. Fixing the injection with parameters doesn't change either behaviour. Both may or may not be intended.
**Confidence:** Low to medium. This depends on the intended behaviour.

## Not a defect
Having `search` next to `{id}` is fine. ASP.NET Core attribute routing matches the literal segment `search` before the `{id}` parameter.

**Bottom line:** I'd block this. Findings 1–3 each justify sending it back on their own.
