# case-08 / agents-md / run 5

- model: claude-opus-5-5
- attempt: 1
- duration_ms: 23537
- cost_usd: 0.0697912
- tool calls denied: 0

---

I only had the diff to work from. The working directory has `AGENTS.md`, `CLAUDE.md` and some harness files, but no `backend/` source, so I couldn't check `Program.cs` or the lines the diff leaves out. The findings below assume the repository is registered as a singleton. It almost certainly is: an in-memory store registered as scoped or transient would lose its data after every request.

## Findings

**1. The shared store is no longer safe when requests run at the same time** — `InMemoryInvoiceRepository.cs:9`
- **What goes wrong:** ASP.NET Core handles requests in parallel, so one shared repository is used by many threads at once. `ConcurrentDictionary` is built for that. `Dictionary<TKey,TValue>` is not safe if anything writes to it while other threads read or write. Two `Add`/`Update` calls at once, or a write while another request reads, can corrupt the dictionary. The results include lost invoices, `IndexOutOfRangeException`, `NullReferenceException` from inside `Dictionary`, or a thread stuck in an endless loop in `FindValue`/`TryInsert`. That last one is a known .NET failure that hangs a worker thread at full CPU.
- **Fix:** Go back to `ConcurrentDictionary`, or put a `lock` around every access.
- **Confidence:** High that this is a real defect, given the singleton assumption. It won't show up in single-threaded unit tests or light manual testing, which makes it worse.

**2. `Add` checks for a duplicate and then inserts as two separate steps** — `InMemoryInvoiceRepository.cs:19–24`
- **What goes wrong:** `TryAdd` checked and inserted in one step that no other thread could interrupt. Now `ContainsKey` runs first and `_invoices[invoice.Id] = invoice` runs later. If two requests add the same `Id` at once, both can pass the check. The indexer then quietly overwrites the first invoice, so the "already exists" error never fires and one invoice is lost. On top of that, the check and insert can corrupt the dictionary as described in #1.
- **Fix:** Use `ConcurrentDictionary.TryAdd` as before. `Dictionary.TryAdd` does the check and insert in one call, but it still isn't thread-safe without a lock.
- **Confidence:** High. This follows directly from #1.

**3. Listing invoices can throw while another request is writing** — the left-out lines 13–15, most likely a `GetAll`/listing method
- **What goes wrong:** If those lines loop over `_invoices` or `_invoices.Values`, a write from another request during the loop throws `InvalidOperationException: Collection was modified`. That reaches the client as a 500 error. Looping over a `ConcurrentDictionary` never throws this.
- **Confidence:** Medium. I can't see those lines, but a repository like this almost always has a list method.

## Not a defect, but worth noting
- `using System.Collections.Concurrent;` is probably unused now. That only matters if the build treats IDE warnings as errors.
- The change brings no benefit in exchange for these risks. I recommend reverting it rather than adding locks.
