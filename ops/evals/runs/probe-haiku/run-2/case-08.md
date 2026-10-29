# case-08 / baseline / run 2

- model: claude-haiku-4-5-20251001
- attempt: 1
- duration_ms: 13243
- cost_usd: 0.018897749999999998
- tool calls denied: 0

---

I found two defects in this diff:

**1. Line 9: Thread-safety regression**
- **File**: `backend/src/InvoiceApp.Api/InMemoryInvoiceRepository.cs`
- **What goes wrong**: Changing from `ConcurrentDictionary<string, Invoice>` to `Dictionary<string, Invoice>` removes thread-safety from the entire repository. The original `Dictionary` is not safe for concurrent access, which is critical in a web API where multiple threads access the repository simultaneously. Methods like `GetById`, `Add`, and `Update` can now have race conditions, visibility issues, or throw `InvalidOperationException` unexpectedly.
- **Confidence**: Very high — this is a fundamental thread-safety violation for a repository in a multi-threaded context.

**2. Lines 19–25: Race condition in `Add` method**
- **File**: `backend/src/InvoiceApp.Api/InMemoryInvoiceRepository.cs`
- **What goes wrong**: The new implementation replaces `TryAdd()` (which is atomic) with a separate `ContainsKey()` check followed by assignment. This is a check-then-act pattern that is not atomic: two threads can both see that the key doesn't exist, both proceed past the check, and both add entries. The duplicate key exception will not be thrown, and the second add will silently overwrite the first. This breaks the contract of the `Add` method even on a concurrent-safe dictionary.
- **Confidence**: Very high — this is a classic race condition bug that violates the method's intended semantics.
