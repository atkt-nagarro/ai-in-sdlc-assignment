# case-02 / baseline / run 1

- model: claude-opus-5-5
- attempt: 1
- duration_ms: 18687
- cost_usd: 0.0627692
- tool calls denied: 0

---

I could only review the diff itself. The working directory has just the diff, no source files, so I couldn't check `_queries`, `ApiControllerBase` or how the app is set up.

### 1. SQL injection through `customer`: high confidence
**File:** `InvoicesController.cs`, line 28 (`var sql = $"SELECT * FROM Invoices WHERE CustomerName LIKE '%{customer}%'";`)

The `customer` value comes straight from the query string and is pasted into the SQL text. Anyone who can call this endpoint can run their own SQL. For example, `?customer=' OR 1=1 --` returns every invoice. Depending on the database's permissions and whether it allows several statements at once, an attacker could also read other tables, change data or delete it (e.g. `'; DROP TABLE Invoices; --`).

**Fix:** pass the value as a parameter, e.g. `WHERE CustomerName LIKE @customer` with `@customer = "%" + customer + "%"`, or use the repository/ORM.

### 2. SQL injection through `status`: high confidence
**File:** same, line 32 (`sql += $" AND Status = '{status}'";`)

This is the same problem with the optional `status` value. Checking that it isn't empty doesn't stop injection.

**Fix:** use a parameter. Better still, read it into the `InvoiceStatus` enum (or check it against a list of allowed values) and return 400 if it doesn't match.

### 3. `%` and `_` in `customer` act as wildcards: medium confidence
**File:** same, line 28

In SQL `LIKE`, `%` matches anything and `_` matches any single character. User input isn't escaped, so `?customer=%` or `?customer=_` matches every customer. This stays true after you switch to parameters, because the value still goes into a `LIKE`. It matters most if search results are meant to be limited, or if large result sets are a cost problem.

**Fix:** escape `%`, `_` and `[` before wrapping the value in `%...%`, using an `ESCAPE` clause or your database's escaping rules.

### 4. Missing `customer` may return every invoice: low–medium confidence
**File:** same, line 26 (`[FromQuery] string customer`)

What happens depends on settings I can't see. If nullable reference types are on and the controller is an `[ApiController]`, ASP.NET Core returns 400 when `customer` is missing. If not, `customer` is `null`, the string becomes `LIKE '%%'`, and the endpoint quietly returns the whole table. Nothing limits the number of rows either, so the response could be very large.

**Fix:** check for an empty value explicitly (return 400), and consider adding paging.

### 5. `_queries` may not exist: low confidence (couldn't check)
**File:** same, line 35

The diff uses `_queries` but doesn't add a field, constructor parameter or DI registration for it. The rest of the controller uses `_repository`. If `_queries` isn't already defined on this class or `ApiControllerBase`, the code won't compile. If it is defined and `Run` executes any SQL string it's given, it's what makes findings 1–2 dangerous.

### Checked and not a problem
- **Route clash between `search` and `{id}`:** attribute routing gives the fixed `search` path priority over `{id}`, so `GET /invoices/search` won't be sent to `GetById`.

Findings 1 and 2 should block merging this.
