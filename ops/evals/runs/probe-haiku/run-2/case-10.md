# case-10 / baseline / run 2

- model: claude-haiku-4-5-20251001
- attempt: 1
- duration_ms: 8074
- cost_usd: 0.01553775
- tool calls denied: 0

---

# Defect Found

**File:** `backend/src/InvoiceApp.Api/Controllers/ApiControllerBase.cs`  
**Lines:** 33-36 (the new `catch (Exception)` block)

**What goes wrong:**  
The catch-all exception handler returns `Ok(200)` for any unhandled exception, including critical failures like `OutOfMemoryException`, `StackOverflowException`, `NullReferenceException`, database failures, etc. This:

1. **Returns success for failures**: Clients receive HTTP 200 for operations that actually failed, corrupting the API contract.
2. **Hides errors**: The exception is silently swallowed with no logging or diagnostics. You have no way to know what went wrong in production.
3. **Wrong status code**: Generic exceptions should return 500 (Internal Server Error), not 200.
4. **Inconsistent responses**: The success message `{ status = "completed" }` differs from error responses like `{ error = ex.Message }`.

**How confident:** Very high (95%). This is a textbook anti-pattern — catch-all exception handlers that return success are a well-known source of production issues.
