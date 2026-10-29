# case-09 / agents-md / run 5

- model: claude-opus-5-5
- attempt: 1
- duration_ms: 18980
- cost_usd: 0.059549
- tool calls denied: 0

---

I could only review the diff itself. The working directory has no source code, just `AGENTS.md`, `CLAUDE.md` and some harness files, so I couldn't check the README's new claims against the repository or sign-in code. My confidence levels reflect that.

## Findings

**1. `README.md`, line 25 (new): the reset instructions are probably wrong**

> To reset the sample data without restarting, sign out and sign in again.

- **What goes wrong:** Signing out normally just clears the auth cookie or session. An in-memory repository in ASP.NET Core is almost always registered as a singleton in `Program.cs`, so its data lasts until the process stops, not until the user signs out. A user who follows this step will still see their changed data. The README also contradicts itself: line 23 says data is lost "when the process stops", which implies it survives signing out. If signing out really did reset the data, that would be business logic in the sign-in path, which `AGENTS.md` forbids, and a shared store would then reset for every user whenever anyone signed out.
- **Fix:** Delete the sentence, or replace it with "restart the app to reset the sample data". Keep it only if a reset-on-sign-in feature actually exists and has tests.
- **Confidence:** Medium. The contradiction is in the text itself. The claim that sign-out doesn't reset the store is inferred from the usual pattern because I couldn't read `Program.cs` or `Auth/`.

**2. `README.md`, lines 21–22 (new): "These accounts exist only in the in-memory store"**

- **What goes wrong:** `AGENTS.md` describes sign-in (`Auth/`) separately from the in-memory invoice repository. The demo accounts may be hard-coded or set in configuration under `Auth/` rather than kept in "the in-memory store", and "recreated on every start" could be wrong if they're static. That's a small inaccuracy, not a functional problem.
- **Fix:** Check where the accounts are defined and reword to match, e.g. "The demo accounts are built into the app; invoice data is held in memory and lost when the process stops."
- **Confidence:** Low. This depends on code I couldn't see.

## No defects

- **`backend/src/InvoiceApp.Api/appsettings.json`, line 5:** Adding `"Microsoft.AspNetCore": "Warning"` is the standard ASP.NET Core template setting, and the JSON is valid (comma added correctly). Startup messages such as "Now listening on…" come from `Microsoft.Hosting.Lifetime`, which this doesn't cover, so they still appear. Per-request framework logs at Information level will no longer show, which is the intended effect.

To confirm finding 1, check how the repository is registered in `Program.cs` and what the sign-out endpoint does.
