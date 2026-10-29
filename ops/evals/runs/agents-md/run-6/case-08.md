# case-08 / agents-md / run 6

- model: claude-opus-5-5
- attempt: 1
- duration_ms: 22536
- cost_usd: 0.0672658
- tool calls denied: 0

---

I found two defects and one likely third. The repository source isn't in this workspace (only `AGENTS.md`/`CLAUDE.md`), so I reviewed the diff alone and couldn't check `Program.cs` to see how the repository is registered.

**1. `InMemoryInvoiceRepository.cs:9`: `Dictionary` isn't safe when shared between requests**
- **What goes wrong:** The repository only keeps data between requests if it's registered as a singleton. If it is, one `Dictionary` instance is shared by every request, and ASP.NET Core runs requests at the same time. `Dictionary` isn't safe for concurrent writes, or for reads that happen during a write. Two `Add`/`Update` calls at once, especially while the table is resizing, can corrupt it. The results include lost invoices, `IndexOutOfRangeException` or `InvalidOperationException` from inside the dictionary, and in some .NET versions a `GetById` that loops forever and hangs a request thread. `ConcurrentDictionary` didn't have this problem.
- **Fix:** Go back to `ConcurrentDictionary`, or put a `lock` around every access.
- **Confidence:** High that this is a real defect, assuming the usual singleton registration. A scoped or transient registration would lose all data after each request, so the app wouldn't work at all.

**2. `InMemoryInvoiceRepository.cs:19–24` (`Add`): the duplicate check and the insert are separate steps**
- **What goes wrong:** `ContainsKey` and the indexer assignment are two separate operations. Two requests adding the same `invoice.Id` can both pass the check, and the second one silently overwrites the first. The "already exists" exception never fires. `TryAdd` did the check and the insert in one atomic step. Using the indexer `_invoices[id] = invoice` also means a race turns into a silent overwrite rather than an exception. Even with a plain `Dictionary`, `_invoices.Add(id, invoice)` would at least have thrown.
- **Fix:** Go back to `if (!_invoices.TryAdd(invoice.Id, invoice)) throw ...`.
- **Confidence:** High, given the shared instance from finding 1.

**3. Lines ~13–15 (hidden by the diff, probably a `GetAll`/list method): listing invoices can crash**
- **What goes wrong:** If the hidden method loops over `_invoices.Values` (directly or through LINQ), a write from another request during the loop will throw `InvalidOperationException: Collection was modified`. That shows up as a 500 on the list endpoint. `ConcurrentDictionary` allows looping while other requests write, so this is a new failure.
- **Confidence:** Medium. I can't see those lines, but the hunk header shows code there, and a repository like this usually has a list method.

The cleanest fix for all three is to revert the diff. I couldn't find any benefit from switching to `Dictionary` that would justify these problems.
