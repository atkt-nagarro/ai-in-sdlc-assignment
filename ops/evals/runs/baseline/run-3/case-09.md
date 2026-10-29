# case-09 / baseline / run 3

- model: claude-opus-5-5
- attempt: 1
- duration_ms: 16458
- cost_usd: 0.048893400000000004
- tool calls denied: 0

---

I could only review the diff itself. The working directory has no repository: no `.cs` files, no `AGENTS.md`, and no store or auth code. So I couldn't check the README's claims against how the app actually behaves.

**Finding 1: `README.md:25`, the reset instruction is probably wrong**

> To reset the sample data without restarting, sign out and sign in again.

- **What goes wrong:** This contradicts the paragraph above it. That paragraph says the demo accounts are "recreated on every start" and data is "lost when the process stops," which means seeding happens once, when the process starts. An in-memory store usually lives for the whole process, often as a singleton. Signing out only clears the auth cookie or token, and signing back in reads the same store. So data entered before signing out would still be there. A user who follows this step to get a clean slate would be misled. If sign-in really does re-seed the data, the docs are accurate, but then any user signing in would wipe everyone's data, which is a bug in its own right.
- **Confidence:** Medium-high that this is wrong. I couldn't confirm it without the seeding code and the sign-in/sign-out handlers. To check, see whether the seeder is called from `Program.cs` or startup (then the line is wrong) or from the login endpoint (then the line is right, but the behaviour is a problem).
- **Fix:** Delete the line, or say "restart the process to reset the sample data."

**`backend/src/InvoiceApp.Api/appsettings.json:5`: no defect**

The JSON is valid: the trailing comma was added correctly to the line before. `"Microsoft.AspNetCore": "Warning"` is the standard ASP.NET Core template setting. The only effect is that framework request logs at Information level disappear. Check `appsettings.Development.json` too, since it overrides this file during local `dotnet run` and might make the change have no effect in development. That's worth knowing, but it isn't a defect.
