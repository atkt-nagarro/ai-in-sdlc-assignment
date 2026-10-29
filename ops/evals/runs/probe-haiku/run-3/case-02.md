# case-02 / baseline / run 3

- model: claude-haiku-4-5-20251001
- attempt: 1
- duration_ms: 9125
- cost_usd: 0.01639525
- tool calls denied: 0

---

I found critical defects in this diff:

**1. SQL Injection vulnerability - Lines 26-28 (HIGH CONFIDENCE)**
- File: `backend/src/InvoiceApp.Api/Controllers/InvoicesController.cs`
- The code directly interpolates user input (`customer` and `status`) into SQL strings using string templates: `$"SELECT * FROM Invoices WHERE CustomerName LIKE '%{customer}%'"` and `sql += $" AND Status = '{status}'"`
- An attacker can input `' OR '1'='1` or similar to break the query logic, or `'; DROP TABLE Invoices; --` to execute arbitrary SQL commands
- This violates OWASP Top 10 (A03:2021 Injection) and is a textbook SQL injection vulnerability
- Fix: Use parameterized queries instead (e.g., `_repository.GetInvoicesByCustomer(customer, status)` using LINQ/EF, or parameterized SQL with `@customer` and `@status` placeholders)

**2. No input validation on required parameter - Line 26 (MEDIUM CONFIDENCE)**
- The `customer` parameter is required (not nullable) but has no length check
- An empty string passes through without error, though it's less critical than the injection issue

**3. Unhandled exception from query execution - Line 35 (LOW-MEDIUM CONFIDENCE)**
- `_queries.Run(sql)` can throw but isn't wrapped in error handling
- Other endpoints in the controller presumably have error handling patterns; this one doesn't follow them

The SQL injection is the critical issue and should block this code from merging.
