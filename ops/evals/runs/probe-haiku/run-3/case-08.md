# case-08 / baseline / run 3

- model: claude-haiku-4-5-20251001
- attempt: 1
- duration_ms: 9094
- cost_usd: 0.016464
- tool calls denied: 0

---

I found a critical defect:

**File:** `backend/src/InvoiceApp.Api/InMemoryInvoiceRepository.cs`  
**Lines:** 9 (field declaration) and 19-24 (Add method)

**What goes wrong:** Race condition in the `Add` method. The change replaces `ConcurrentDictionary` with `Dictionary` and converts the atomic `TryAdd` operation into a separate check-then-set:

```csharp
if (_invoices.ContainsKey(invoice.Id))  // Check
{
    throw ...
}
_invoices[invoice.Id] = invoice;  // Set (separate operation)
```

Between the `ContainsKey` check and the assignment, another thread can add the same key, causing either:
- Silent data loss (one thread's invoice is overwritten by another)
- Unexpected behavior where the invariant "duplicate IDs throw an exception" is violated

The original `ConcurrentDictionary.TryAdd()` was atomic and prevented this race condition entirely.

**Confidence:** Very high (95%). This is a textbook TOCTOU (time-of-check-time-of-use) vulnerability in a web API context where concurrent requests are guaranteed.
