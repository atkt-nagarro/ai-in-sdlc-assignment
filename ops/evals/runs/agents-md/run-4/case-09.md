# case-09 / agents-md / run 4

- model: claude-opus-5-5
- attempt: 1
- duration_ms: 20399
- cost_usd: 0.0617694
- tool calls denied: 0

---

I couldn't check this diff against the code. The working directory only has `CLAUDE.md`, `AGENTS.md` and a few harness files (`.message`, `result.json`, `stderr.txt`). `backend/` isn't there, so the findings below come from the diff and the project conventions in `AGENTS.md` only.

### Finding 1: README tells users they can reset data by signing out, which almost certainly doesn't work
- **File / line:** `README.md`, the added line "To reset the sample data without restarting, sign out and sign in again." (about line 25 in the new file)
- **What goes wrong:** According to `AGENTS.md`, invoices are stored in an in-memory repository in the Api project and registered in `Program.cs`. A store like that is normally a singleton that lives as long as the process. Signing out only clears the auth cookie or session; it doesn't rebuild the repository. Following this instruction leaves the data unchanged.
- **It also contradicts the sentence just before it.** That sentence says data "is lost when the process stops", which only makes sense if data survives everything except a restart, including sign-out and sign-in.
- **Confidence:** Medium-high (about 75%). I couldn't open the repository registration or the `Auth/` code to rule out a sign-in hook that reseeds data. But such a hook would mean business logic in the sign-in path, which `AGENTS.md` forbids. **Fix:** delete the line, or say that restarting the app is the only way to reset.

### Finding 2: "These accounts exist only in the in-memory store" may not match how sign-in works
- **File / line:** `README.md`, the added lines starting "These accounts exist only in the in-memory store and are recreated on every start…" (about lines 21–23)
- **What goes wrong:** `AGENTS.md` lists demo users with fixed passwords. Sign-in lives in `Auth/`, separate from the in-memory invoice repository. Accounts like these are often hard-coded or loaded from config rather than kept in "the in-memory store" and "recreated". If so, the wording misdescribes how sign-in works. The practical point, that entered data is lost when the process stops, is probably still correct.
- **Confidence:** Low (about 35%). This depends on `Auth/` code I couldn't see.

### `appsettings.json`: no defects
Adding `"Microsoft.AspNetCore": "Warning"` is the standard ASP.NET Core template setting and the JSON is valid. It doesn't hide the "Now listening on…" startup message, because that comes from `Microsoft.Hosting.Lifetime`, which still logs at `Information` under `Default`.

If you can make `backend/src/InvoiceApp.Api` available, I can check `Program.cs` and `Auth/` to confirm or rule out both README findings.
