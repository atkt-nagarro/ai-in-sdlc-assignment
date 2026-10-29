# case-08 / agents-md / run 4

- model: claude-opus-5-5
- attempt: 1
- duration_ms: 23916
- cost_usd: 0.0728408
- tool calls denied: 0

---

I could only review the diff itself. The workspace has `AGENTS.md`/`CLAUDE.md` but no `backend/` source, so I couldn't open the full file or `Program.cs` to confirm how the repository is registered. Line numbers below are for the new version of the file, worked out from the hunk headers.

## Findings

### 1. `Dictionary` is not thread-safe, and this repository is shared across requests
**File:** `backend/src/InvoiceApp.Api/InMemoryInvoiceRepository.cs`, line 9
**What goes wrong:** ASP.NET Core handles requests at the same time on different threads. An in-memory repository only keeps its data between requests if it is registered as a singleton, so one `Dictionary` instance gets read and written by several threads at once. `Dictionary<TKey,TValue>` doesn't support even one writer running alongside readers. Two `Add`/`Update` calls at the same moment, or a write during a `GetById`, can damage its internal buckets. You could see lost invoices, wrong lookups, `InvalidOperationException` ("Operations that change non-concurrent collections must have exclusive access"), or in older runtimes a thread stuck in an infinite loop. `ConcurrentDictionary` was protecting against all of this.
**Confidence:** High that this is a real defect. Medium-high that it's registered as a singleton, since I couldn't check `Program.cs`. A scoped or transient in-memory repository would lose all its data after every request, so singleton is almost certain.

### 2. The duplicate-ID check in `Add` can be beaten by a race, so the second invoice silently overwrites the first
**File:** same file, lines 19–24 (`ContainsKey` then `_invoices[invoice.Id] = invoice`)
**What goes wrong:** `TryAdd` checked and inserted in one atomic step. The new code checks and inserts in two separate steps. If two requests add an invoice with the same ID at the same time, both can pass `ContainsKey`, and the second indexer assignment replaces the first invoice with no exception. The rule "Invoice {id} already exists" stops being enforced exactly when it matters, and the first caller still gets a success response for an invoice that no longer exists. Making the dictionary safe wouldn't fix this alone, because the check and the write must happen as one operation.
**Confidence:** High.

### 3. Listing invoices can throw while another request is writing
**File:** same file, the unchanged member around lines 12–15 that the diff hides (probably a `GetAll()` that enumerates `_invoices.Values`)
**What goes wrong:** If a list request is enumerating a `Dictionary` while another request calls `Add` or `Update`, the enumerator throws `InvalidOperationException: Collection was modified`, and the list endpoint returns a 500 error from time to time. `ConcurrentDictionary`'s enumerator handles concurrent changes safely.
**Confidence:** Medium. It depends on that hidden member enumerating the dictionary, which I couldn't see.

## Suggested fix
Revert to `ConcurrentDictionary` and `TryAdd`. The original code was correct and this change doesn't gain anything. If there's a reason to keep `Dictionary`, put a single `lock` around every access (`GetById`, the listing method, `Add`, `Update`), and copy the values to a list inside the lock before returning them.

The existing unit tests won't catch any of this, because they use `FakeInvoiceRepository` and run on a single thread. Only a concurrency test against `InMemoryInvoiceRepository` itself would show it.
