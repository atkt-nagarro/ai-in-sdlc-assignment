# case-02 / baseline / run 2

- model: claude-opus-5-5
- attempt: 1
- duration_ms: 20415
- cost_usd: 0.054874599999999996
- tool calls denied: 0

---

I could only review the diff text. The repo contains just the diff (`.message`), so I couldn't check `_queries`, `ApiControllerBase`, or how the project is configured. Line numbers below refer to the new file, counting from the hunk header `@@ +22`.

## Findings

**1. SQL injection through `customer`: `InvoicesController.cs:28`**
`customer` comes from the query string and is pasted straight into the SQL text. A request like `?customer=x' OR 1=1; DROP TABLE Invoices; --` runs whatever SQL the attacker writes. Because the parameter is required, every caller of this endpoint can reach it. Depending on what `_queries.Run` does and what the database account is allowed to do, this means an attacker can read, change or delete any table.
**Confidence: high.**

**2. SQL injection through `status`: `InvoicesController.cs:32`**
Same problem: `status` is put into the SQL without escaping. The `IsNullOrEmpty` check only skips the clause when the value is missing. It does nothing to clean the value.
**Confidence: high.**

**Fix for both:** use parameters, for example `WHERE CustomerName LIKE @customer AND (@status IS NULL OR Status = @status)` with `@customer = "%" + customer + "%"`. Or use the existing `_repository`/EF and LINQ: `.Where(i => i.CustomerName.Contains(customer))`. If `_queries.Run` only accepts a raw string, it needs an overload that takes parameters.

**3. LIKE wildcards in `customer` aren't escaped: `InvoicesController.cs:28`**
Even after fixing #1, a `customer` value containing `%`, `_` or `[` (SQL Server) still works as a wildcard. For example, `?customer=%` matches every invoice. Escape these characters or use an `ESCAPE` clause. EF's `Contains` handles this for you.
**Confidence: medium.** It's a real bug. How much it matters depends on whether wide matches are a problem here.

**4. A missing `customer` may return every invoice: `InvoicesController.cs:26`**
`customer` is declared as a non-nullable `string`. If nullable reference types are *not* enabled, a request with no `customer` binds it as `null`. The query then becomes `LIKE '%%'` and returns the whole table. If they *are* enabled, `[ApiController]` returns a 400 for you, which is fine. I couldn't check which setting the project uses.
**Confidence: low to medium.**

**5. The search skips `_repository`: `InvoicesController.cs:35`**
Every other action shown uses `_repository`. This one runs raw SQL through `_queries`. If `_repository` filters by tenant or user, or hides soft-deleted rows, this endpoint skips all of that and returns everyone's invoices. Separately, `SELECT *` has no limit or paging.
**Confidence: low.** This is a guess, because I can't see the repository code.

**6. `_queries` might not exist: `InvoicesController.cs:35`**
The diff doesn't add a `_queries` field or a constructor parameter for it. If neither exists already, the code won't compile.
**Confidence: low.** It may already be declared somewhere outside the hunk.

The `"search"` route doesn't clash with `"{id}"`. ASP.NET Core routing picks the literal segment over the parameter.

#1 and #2 alone are reason enough not to merge this.
