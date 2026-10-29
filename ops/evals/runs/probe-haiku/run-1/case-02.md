# case-02 / baseline / run 1

- model: claude-haiku-4-5-20251001
- attempt: 1
- duration_ms: 8244
- cost_usd: 0.016089000000000003
- tool calls denied: 0

---

I found a critical defect:

**File:** `backend/src/InvoiceApp.Api/Controllers/InvoicesController.cs`

**Lines:** 27 and 31

**Defect:** SQL injection vulnerability. Both the `customer` and `status` parameters are interpolated directly into the SQL query string using string formatting. An attacker can inject arbitrary SQL by crafting malicious input (e.g., `customer` = `%' OR '1'='1` or `status` = `'; DROP TABLE Invoices; --`).

**Confidence:** 100%

**Fix:** Use parameterized queries instead of string concatenation:

```csharp
var sql = "SELECT * FROM Invoices WHERE CustomerName LIKE @customer";
var parameters = new[] { new SqlParameter("@customer", $"%{customer}%") };

if (!string.IsNullOrEmpty(status))
{
    sql += " AND Status = @status";
    parameters = parameters.Append(new SqlParameter("@status", status)).ToArray();
}

return Ok(_queries.Run(sql, parameters));
```

(Exact syntax depends on your query execution method, but the principle is: separate the query structure from the data values.)
