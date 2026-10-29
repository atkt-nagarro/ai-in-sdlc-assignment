# case-08 / baseline / run 2

- model: claude-opus-5-5
- attempt: 1
- duration_ms: 18853
- cost_usd: 0.0534604
- tool calls denied: 0

---

I found two defects, and a likely third in code the diff doesn't show. The workspace contains only the diff, so I couldn't check how the repository is registered or read the lines the diff hides. All of these depend on one assumption: the repository is a singleton shared across requests. An in-memory repository has to be registered that way to keep data between requests, so the assumption is very likely true.

### 1. `Dictionary` is not thread-safe, but this instance is shared across requests
**File:** `backend/src/InvoiceApp.Api/InMemoryInvoiceRepository.cs`, line 9 (`private readonly Dictionary<string, Invoice> _invoices`)

**What goes wrong:** ASP.NET Core handles requests in parallel. `Add` and `Update` (line ~28) change the dictionary with no lock. If two writes overlap, or a write overlaps a `GetById` read, the dictionary's internal state can be corrupted. The results include lost entries, a read that returns the wrong result or throws, and the well-known failure where `Dictionary` gets stuck in an infinite loop and pins a CPU core. `ConcurrentDictionary` was there to prevent exactly this.

**Confidence:** High if the repository is a singleton; I couldn't see the registration to confirm.

### 2. `Add` checks then writes in two steps, so a duplicate can silently overwrite an invoice
**File:** same file, lines ~19–24 (`if (_invoices.ContainsKey(...))` … `_invoices[invoice.Id] = invoice;`)

**What goes wrong:** `TryAdd` checked and inserted in one atomic step. The new code checks first and writes later. Two concurrent `Add` calls with the same Id can both pass the `ContainsKey` check, and the second write then replaces the first invoice. The duplicate check that should throw `InvalidOperationException` never fires, and the first invoice is lost without any error. The indexer write also makes this worse: `_invoices.Add(invoice.Id, invoice)` would at least throw on a duplicate key, while `[...] =` overwrites.

**Confidence:** High under concurrent requests. This is a behaviour regression even apart from finding 1.

### 3. (Likely) Listing invoices can throw while another request writes
**File:** same file, lines ~16–18 (hidden from the diff, between `GetById` and `Add`)

**What goes wrong:** Those hidden lines probably hold a get-all method that iterates over `_invoices.Values`. Iterating a `ConcurrentDictionary` while it changes is safe. Iterating a `Dictionary` while another request calls `Add` or `Update` throws `InvalidOperationException: Collection was modified`, which would surface as intermittent 500 errors.

**Confidence:** Medium. It depends on code I can't see.

**Fix:** Revert to `ConcurrentDictionary` with `TryAdd`. If there's a reason to use a plain `Dictionary`, guard every access with a `lock`, including reads and any iteration, which should return a snapshot copy such as `.ToList()` taken inside the lock.
