# case-08 / baseline / run 1

- model: claude-haiku-4-5-20251001
- attempt: 1
- duration_ms: 11813
- cost_usd: 0.01857775
- tool calls denied: 0

---

I found two significant defects:

**Finding 1: Loss of thread safety**  
File: `InMemoryInvoiceRepository.cs`, Line 9  
The change from `ConcurrentDictionary<string, Invoice>` to `Dictionary<string, Invoice>` removes thread-safe access. A `Dictionary` is not safe for concurrent reads/writes. In a web API where multiple requests handle invoices concurrently, this will cause race conditions (lost updates, torn reads, exceptions during enumeration).  
**Confidence: Very high** — This is a fundamental requirement for shared mutable state in multi-threaded contexts.

**Finding 2: Race condition in Add method**  
File: `InMemoryInvoiceRepository.cs`, Lines 19 and 24  
The original code used `TryAdd()`, which atomically checks and adds in one operation. The new code splits this into two separate operations:
```csharp
if (_invoices.ContainsKey(invoice.Id))  // Check
    throw ...;
_invoices[invoice.Id] = invoice;         // Add
```
Between the check and the assignment, another thread can insert the same key, causing the exception to not fire when it should, or silently overwriting an existing invoice. The original atomic `TryAdd` cannot fail this way.  
**Confidence: Very high** — Classic check-then-act race condition.

Both defects stem from removing `ConcurrentDictionary`, which was the correct choice for this use case.
