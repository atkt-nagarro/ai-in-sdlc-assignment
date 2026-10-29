# case-08 / baseline / run 3

- model: claude-opus-5-5
- attempt: 1
- duration_ms: 20311
- cost_usd: 0.058834
- tool calls denied: 0

---

I couldn't check this against the code. The workspace has only the diff, not the C# source, so I couldn't see the DI registration, the hidden lines 13–15 (probably a `GetAll`), or the callers. All findings come from the diff alone.

## Findings

**1. The repository is no longer thread-safe**
`InMemoryInvoiceRepository.cs:9`
- **What goes wrong:** An in-memory repository in ASP.NET Core almost always has to be a singleton, or its data would vanish after each request. That means requests share one `Dictionary` across threads. `Dictionary<TKey,TValue>` doesn't support a write happening at the same time as any other read or write. Concurrent `Add`/`Update` calls, or a write while `GetById` is reading, can corrupt its internal buckets. Typical symptoms are lost entries, `IndexOutOfRangeException`, `NullReferenceException`, or a reader stuck in an endless loop at 100% CPU. The bug only appears under load and is hard to reproduce, so tests will probably pass.
- **Confidence:** High, assuming the singleton registration (very likely, but I couldn't confirm it). If it's scoped or transient, the repository is broken in a different way: data doesn't persist between requests.

**2. Check-then-act race in `Add` lets a duplicate overwrite silently**
`InMemoryInvoiceRepository.cs:19–24`
- **What goes wrong:** `TryAdd` checked and inserted in one atomic step. The new code is `ContainsKey(...)` followed by `_invoices[id] = invoice`. If two requests add the same `Id` at once, both can pass the check, and the second write overwrites the first without the "already exists" exception. Duplicate detection is the point of this method, and it now fails in exactly the concurrent case it exists for. The indexer assignment (instead of `.Add`) also removes the last safety net, since `.Add` would at least throw on a duplicate key.
- **Confidence:** High, given concurrent access (see #1).

**3. Code that enumerates the dictionary can throw (hidden lines)**
`InMemoryInvoiceRepository.cs:~13–15`
- **What goes wrong:** If the hidden lines contain something like `GetAll() => _invoices.Values` (or a LINQ query over it), enumerating while another thread calls `Add`/`Update` will throw `InvalidOperationException: Collection was modified`, or worse, read corrupted state. `ConcurrentDictionary` allowed enumeration during writes.
- **Confidence:** Medium. It's the usual shape for this class, but I can't see those lines.

**4. Leftover `using System.Collections.Concurrent;`**
Top of file, not in the diff.
- **What goes wrong:** This using is now unused. Normally that's just a warning. It only breaks the build if the project enforces IDE0005 with `TreatWarningsAsErrors` / `EnforceCodeStyleInBuild`.
- **Confidence:** Low that it matters.

## Recommendation
Revert to `ConcurrentDictionary` with `TryAdd`. The diff gives no reason for the change, and the original was correct. If there's a reason to keep a plain `Dictionary`, every member, including `GetById`, `Update` and any enumeration, needs a `lock`. Any enumeration should also return a snapshot (`.ToList()` taken inside the lock), not the live `Values` view.
