# case-07 / baseline / run 3

- model: claude-haiku-4-5-20251001
- attempt: 1
- duration_ms: 9848
- cost_usd: 0.0161765
- tool calls denied: 0

---

**FINDING: Information Disclosure / Sensitive Data Leakage**

- **File:** `backend/src/InvoiceApp.Api/Controllers/ApprovalsController.cs`
- **Lines:** 31–33
- **What goes wrong:** The log statement destructures and outputs the entire `invoice` and `CurrentUser` objects using Serilog's `{@...}` format specifiers. Invoice objects typically contain sensitive financial data (amounts, account numbers, customer details, payment methods), and `CurrentUser` likely contains user identifiers and session information. Logging these full objects could expose PII and violate compliance requirements (GDPR, PCI-DSS) if logs are persisted, aggregated to external systems, or accessed by unauthorized personnel.
- **Confidence:** High (90%)

**Recommendation:** Log only non-sensitive identifiers (e.g., invoice ID, user ID) rather than the full objects. Example:
```csharp
_logger.LogInformation(
    "Approval completed. Invoice: {InvoiceId}. User: {UserId}",
    invoice.Id, CurrentUser.Id);
```
