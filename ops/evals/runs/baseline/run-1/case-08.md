# case-08 / baseline / run 1

- model: claude-opus-5-5
- attempt: 1
- duration_ms: 21961
- cost_usd: 0.0589822
- tool calls denied: 0

---

I couldn't find the source file in the working directory, so this review is based only on the diff. If the class were only ever used by one thread, the old and new code would behave the same. The defects below only appear when it's accessed concurrently. In an ASP.NET Core API, an in-memory repository is almost always registered as a singleton, because otherwise its data would vanish after each request or scope. That means concurrent access is the normal case.

### 1. `Dictionary` is not thread-safe
**File:** `backend/src/InvoiceApp.Api/InMemoryInvoiceRepository.cs`, line 9
**Confidence:** High, assuming the repository is a singleton or otherwise shared between requests (I couldn't check the DI registration).

Before this change, `ConcurrentDictionary` made concurrent reads and writes safe. `Dictionary<TKey,TValue>` only supports multiple readers at once. Once a write is involved, it needs outside locking. Concurrent `Add`/`Update` calls, or a write while `GetById` is reading, can corrupt the dictionary's internal buckets. You might see:
- entries that silently disappear
- `InvalidOperationException` or `IndexOutOfRangeException` thrown from inside `Dictionary`
- `TryGetValue` stuck in an infinite loop on a corrupted bucket chain, pinning a CPU core and hanging the request. This is a documented failure mode of `Dictionary` used without a lock.

These failures are intermittent and depend on load, so tests are unlikely to catch them.

### 2. Check-then-act race in `Add` breaks the duplicate-ID guarantee
**File:** same file, lines 19–24
**Confidence:** High, under the same assumption as #1.

`TryAdd` checked for the key and inserted in one atomic step. The new code does it in two steps: `ContainsKey` (line 19), then `_invoices[invoice.Id] = invoice` (line 24). If two requests add the same ID at the same time, both can pass the check. The second write then silently overwrites the first, and neither caller gets the "already exists" exception. One invoice is lost with no error. Even if #1 were fixed by locking only individual dictionary operations, this race would remain. The check and the insert have to be atomic together.

### 3. Any enumeration in the hidden lines is now unsafe (possible)
**File:** same file, roughly lines 13–15, which the diff doesn't show
**Confidence:** Low to medium. It depends on code I can't see.

Repositories like this usually have a `GetAll()` that returns or iterates `_invoices.Values`. `ConcurrentDictionary` enumeration is safe while other threads write. `Dictionary` enumeration throws `InvalidOperationException: Collection was modified` if another thread calls `Add` or `Update` during it. Returning `.Values` lazily, without `.ToList()`, makes this worse because the enumeration happens later, in the caller's code.

### Recommendation
Revert to `ConcurrentDictionary` with `TryAdd`. If there was a reason to switch, such as wanting deterministic ordering, keep the `Dictionary` but wrap every member in `lock`, including reads and any snapshot used for enumeration.
