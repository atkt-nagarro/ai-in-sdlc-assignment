# case-07 / baseline / run 2

- model: claude-haiku-4-5-20251001
- attempt: 1
- duration_ms: 11242
- cost_usd: 0.0164865
- tool calls denied: 0

---

**Finding: Information Disclosure via Sensitive Data Logging**

**File:** `backend/src/InvoiceApp.Api/Controllers/ApprovalsController.cs`  
**Lines:** 31–33  
**Issue:** The logging statement uses structured logging syntax (`@Invoice` and `@Session`) to serialize complete objects into logs. This will capture:
- Full invoice data (amounts, payee details, account information — likely sensitive financial data)
- Complete user/session object (`CurrentUser`) which could include authentication credentials, tokens, or other PII

Logs are typically stored with less restrictive access controls than the application itself and may be forwarded to external services. Logging full financial and user objects violates data minimization principles and creates a security exposure.

**Confidence:** High. This is a common anti-pattern — the `@` structured logging syntax specifically serializes entire objects, and both invoices and session/user data are inherently sensitive in a financial application.

**Recommendation:** Log only necessary, non-sensitive fields (e.g., invoice ID, user ID) rather than full objects, or exclude sensitive properties before logging.
