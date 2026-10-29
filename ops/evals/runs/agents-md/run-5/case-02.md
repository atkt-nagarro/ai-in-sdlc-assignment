# case-02 / agents-md / run 5

- model: claude-opus-5-5
- attempt: 1
- duration_ms: 29275
- cost_usd: 0.0816698
- tool calls denied: 0

---

I reviewed the diff on its own. The working directory contains only `CLAUDE.md` and `AGENTS.md`, with no `backend/` source, so I couldn't check the rest of the controller or the project. Line numbers below are from the new version of the diff.

### 1. SQL injection through `customer`: `InvoicesController.cs:28`
**What goes wrong:** `customer` comes straight from the query string and is pasted into the SQL text. A request like `?customer=x' OR '1'='1` returns every invoice. Depending on what `_queries.Run` uses underneath, an attacker could also chain extra statements (for example `'; DELETE FROM Invoices; --`) or use UNION to read other tables. Any signed-in user can do this, because the endpoint has no role restriction.
**Fix:** Pass values as parameters (`@customer` with the value `"%" + customer + "%"`) instead of building the string. Better still, don't build SQL in the controller at all (see finding 4).
**Confidence:** High.

### 2. SQL injection through `status`: `InvoicesController.cs:32`
**What goes wrong:** Same problem with the optional `status` parameter. It is never checked against the four real statuses (Draft, PendingApproval, Approved, Rejected), so any text is accepted and runs as SQL.
**Fix:** Parse it into the status enum with `Enum.TryParse` and return 400 if it isn't valid, then filter on the typed value.
**Confidence:** High.

### 3. `_queries` probably doesn't exist, and there is no database: `InvoicesController.cs:35`
**What goes wrong:** The diff doesn't add a `_queries` field or inject it in the constructor. According to `AGENTS.md`, storage is an in-memory repository and nothing in the code talks to a database (the database under `ops/` is only planned). So either:
- this doesn't compile because `_queries` is undefined, or
- `_queries` is some raw-SQL runner with no `Invoices` table behind it, so the call fails at runtime or silently searches different data from what `GetAll` returns.

**Fix:** Add a `Search(customer, status)` method to the repository interface in Domain, implement it in the in-memory repository, and call `_repository` like the other actions do.
**Confidence:** Medium. I couldn't see the file, but the project docs strongly suggest this.

### 4. Breaks project conventions: `InvoicesController.cs:25–36`
**What goes wrong:** `AGENTS.md` says controllers must not contain business or storage logic and must go through repository interfaces and `Handle(...)`. This action builds queries inline, skips `Handle`, and `SELECT *` returns raw rows instead of the domain `Invoice` model. That could expose extra columns and produce a different JSON shape from the other endpoints.
**Fix:** Same change as finding 3.
**Confidence:** High that the conventions are broken. Medium on the impact of the response shape.

### 5. No tests
**What goes wrong:** `AGENTS.md` requires tests for every new endpoint (using `FakeInvoiceRepository`), and the diff adds none. Tests would need to cover filtering by customer, filtering by status, an invalid status, and a missing `customer`.
**Confidence:** High, based on what's in the diff.

### 6. Behaviour when `customer` is missing: `InvoicesController.cs:26`
**What goes wrong:** `customer` is declared as a required (non-nullable) string. If nullable checking is on and `ApiControllerBase` carries `[ApiController]`, leaving it out returns an automatic 400. If not, it arrives as null and the query becomes `LIKE '%%'`, which returns every invoice. Either way, the intent should be stated explicitly. Separately, `%` and `_` typed into `customer` act as wildcards; that is a small issue once parameters are used.
**Confidence:** Low to medium, because it depends on project settings I couldn't see.

**Not a problem:** Placing `[HttpGet("search")]` before `[HttpGet("{id}")]` is fine. ASP.NET Core prefers the fixed `search` path over the `{id}` placeholder, so the two don't collide.
