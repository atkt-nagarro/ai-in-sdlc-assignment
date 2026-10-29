# case-02 / baseline / run 3

- model: claude-opus-5-5
- attempt: 1
- duration_ms: 17805
- cost_usd: 0.0492114
- tool calls denied: 0

---

I couldn't check this against the codebase: the working directory only has the diff, not the source files. Line numbers are in the new file, counted from the hunk header (`+22`).

## Findings

### 1. SQL injection: `InvoicesController.cs:28` and `:32`
**Confidence: High**

Both `customer` and `status` come straight from the query string and are pasted into the SQL with string interpolation:

```csharp
var sql = $"SELECT * FROM Invoices WHERE CustomerName LIKE '%{customer}%'";
...
sql += $" AND Status = '{status}'";
```

A request like `GET /invoices/search?customer=' OR 1=1 --` returns every invoice. Depending on the database account's permissions and whether `_queries.Run` allows multiple statements, a payload like `'; DROP TABLE Invoices; --` could also change or delete data. Anyone who can reach this endpoint can exploit it.

**Fix:** Use parameters. For example, if `_queries` wraps Dapper or ADO.NET:
```csharp
var sql = "SELECT ... FROM Invoices WHERE CustomerName LIKE @customer";
// bind @customer = $"%{customer}%", and @status if supplied
```
If `_queries.Run(string)` can't take parameters, that API is the root problem. Better still, add a method to `_repository` like the other actions use.

### 2. LIKE wildcards in `customer` aren't escaped: `:28`
**Confidence: Medium**

Even after you switch to parameters, `%`, `_` and (on SQL Server) `[` inside `customer` still act as wildcards. So `customer=%` or `customer=_` matches every row. This is a correctness problem, not an injection risk. Escape those characters before wrapping the value in `%...%`, if exact substring matching is what you want.

### 3. Missing `customer` may match everything: `:26`
**Confidence: Low–Medium (depends on project settings)**

`customer` is declared as non-nullable `string`, but nothing makes it required. If nullable reference types are on and the controller has `[ApiController]`, a missing value gets an automatic 400. Otherwise `customer` is `null`, the SQL becomes `LIKE '%%'`, and the endpoint returns all invoices without paging. Add `[Required]` or an explicit check if a customer value should be mandatory.

### 4. `_queries` isn't declared in this diff: `:35`
**Confidence: Low (couldn't verify)**

Every other action uses `_repository`. This diff doesn't add a `_queries` field or constructor parameter. If one doesn't already exist outside the hunk, the code won't compile. Worth confirming.

## Not a defect
- Route clash between `search` and `{id}`: ASP.NET Core attribute routing matches literal segments before parameter segments, so `/search` won't be routed to `GetById`.

The SQL injection (#1) should block the merge on its own.
