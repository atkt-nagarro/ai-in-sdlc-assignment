# case-09 / baseline / run 1

- model: claude-opus-5-5
- attempt: 1
- duration_ms: 17675
- cost_usd: 0.04679200000000001
- tool calls denied: 0

---

I found one likely defect. I couldn't confirm it because the source isn't in the working directory. The only file there is an empty `result.json`, so I reviewed the diff on its own and couldn't check the README's claims against the backend.

**1. `README.md:25`: the reset instruction is probably wrong. Confidence: medium.**

> To reset the sample data without restarting, sign out and sign in again.

This conflicts with the lines just before it (22–23). Those say the store is in-memory, rebuilt on every start, and that data is lost "when the process stops." That means data lasts for the life of the process. Signing out usually only clears the session or cookie. It doesn't reseed an app-wide in-memory store, so a user who follows this step will still see their old data.

If sign-in really does reseed the store, the wording is still a problem. Data would then be lost on every sign-out, and it might be wiped for everyone sharing the instance. Lines 22–23 only warn about losing data when the process stops, so they would understate the risk.

To fix it, either delete the sentence, or check the sign-in/sign-out handler and seeding code. If reseeding on sign-in is real, say clearly that signing out throws away your changes.

**Minor, low confidence:** line 21 still sends readers to `AGENTS.md` for the demo accounts. That's unchanged, but `AGENTS.md` is normally a file of instructions for AI agents, so it's an odd place to document login details. Not a defect if the file actually lists them.

**`appsettings.json`: no defects.** The JSON is valid. Setting `"Microsoft.AspNetCore": "Warning"` is the standard ASP.NET Core template value. It cuts the framework's request/response logging, and the app's own logs stay at Information. One thing to know: an `appsettings.Development.json` can override this when running locally. That's expected behaviour, not a bug.
