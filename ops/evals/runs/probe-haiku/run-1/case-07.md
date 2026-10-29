# case-07 / baseline / run 1

- model: claude-haiku-4-5-20251001
- attempt: 1
- duration_ms: 17068
- cost_usd: 0.0212315
- tool calls denied: 0

---

**File**: `backend/src/InvoiceApp.Api/Controllers/ApprovalsController.cs`

**Lines**: 34–36 (the new logging statement)

**What goes wrong**: The code logs the complete `invoice` and `CurrentUser` objects at `LogInformation` level, which is typically enabled in production. Invoices contain sensitive financial data (amounts, customer details, pricing), and `CurrentUser` objects contain user identity information. This exposes PII and financial data in logs, violating data protection principles and likely regulatory requirements (GDPR, PCI-DSS). 

At minimum, you should log only the invoice ID and approval status, redacting sensitive fields. Consider whether `CurrentUser` needs to be logged at all, or whether just the user ID would suffice.

**Confidence**: Very high (95%+). This is a well-known security issue in logging.
