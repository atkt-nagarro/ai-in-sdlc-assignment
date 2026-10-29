# case-09 / agents-md / run 6

- model: claude-opus-5-5
- attempt: 1
- duration_ms: 20279
- cost_usd: 0.0608582
- tool calls denied: 0

---

I found one likely defect, in the README. The appsettings change looks fine. I couldn't check either finding against the code, because the working directory only has `AGENTS.md`, `CLAUDE.md` and some harness files. There's no `backend/`, so I couldn't read the auth setup, the in-memory repository or `Program.cs`. The confidence levels below reflect that.

## Findings

**1. `README.md`, added line 25: "To reset the sample data without restarting, sign out and sign in again."**
- **What goes wrong:** This almost certainly doesn't work, and it contradicts the paragraph just above it. That paragraph says the data is recreated on every start and lost when the process stops, which means the data lasts as long as the process does. Signing out and back in normally only clears and reissues the sign-in cookie. An in-memory repository registered in `Program.cs` is normally a singleton, so it isn't reseeded per session. A user who follows this instruction will still see the old data and think the reset failed or the app is broken. If someone has since added a reset-on-sign-in hook, that would be a bigger problem: one user signing in would wipe every other user's data, and the Admin-only rule for destructive actions would be bypassed.
- **Fix:** Delete the sentence, or replace it with "restart the app to reset the sample data." If reset without restarting is really wanted, it should be an Admin-only endpoint backed by Domain logic, with tests.
- **Confidence:** Medium-high (about 80%). The contradiction is plain from the diff itself. Whether it's actually wrong depends on code I couldn't see.

**2. `README.md`, added lines 21–23: "These accounts exist only in the in-memory store and are recreated on every start…"**
- **What goes wrong:** This may describe the wrong place. `AGENTS.md` puts sign-in under `Auth/` and separate from the in-memory repository, and the repository is described as holding invoices. If the demo accounts are hardcoded or come from config, they aren't "in the in-memory store" and aren't "recreated." The sentence would mislead anyone trying to add or change accounts. The second half, that entered data is lost when the process stops, is probably correct.
- **Fix:** Check how `Auth/` defines the accounts. If they're static, reword to something like "The demo accounts are built into the app. Invoice data is kept in memory and lost when the process stops."
- **Confidence:** Low (about 35%). This is a precision issue I can't confirm.

## No defect

**`appsettings.json`:** Adding `"Microsoft.AspNetCore": "Warning"` is valid JSON, and the comma is in the right place. It's the standard ASP.NET Core template default. The only effect is that the framework's own Information logs, such as per-request routing lines, disappear from the console. That looks intentional.
