# case-02 / baseline / run 2

- model: claude-haiku-4-5-20251001
- attempt: 1
- duration_ms: 10298
- cost_usd: 0.016882750000000002
- tool calls denied: 0

---

**File:** `backend/src/InvoiceApp.Api/Controllers/InvoicesController.cs`

**Line 26-27 and 30-31:** SQL Injection vulnerability

**What goes wrong:** User input from `customer` and `status` query parameters is directly interpolated into SQL strings without parameterization. An attacker can inject SQL code by passing values like `%' OR '1'='1` or `'; DROP TABLE Invoices; --`.

**Example attack:**
```
GET /api/invoices/search?customer=%'+OR+'1'='1&status='; DROP TABLE Invoices; --
```

This would execute destructive commands or bypass the WHERE clause entirely.

**Fix:** Use parameterized queries instead of string interpolation. The `_queries.Run()` call should accept parameters separately, or use an ORM that handles escaping automatically.

**Confidence:** Very high (99%) — this is a textbook SQL injection vulnerability. Directly interpolating unsanitized user input into SQL strings is categorically unsafe.
