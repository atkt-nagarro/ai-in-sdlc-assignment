# case-02 / agents-md / run 4

- model: claude-opus-5-5
- attempt: 1
- duration_ms: 24801
- cost_usd: 0.0713592
- tool calls denied: 0

---

I only had the diff to work with. The workspace has `AGENTS.md`/`CLAUDE.md` but no `backend/` source, so I couldn't check the rest of the controller, `Program.cs` or the tests. Line numbers below are for the new version of `InvoicesController.cs`.

## Findings

**1. SQL injection: `InvoicesController.cs:28` and `:32`** (high confidence)
`customer` and `status` come straight from the query string and are pasted into the SQL text. A request like `?customer=x' OR '1'='1` returns every invoice. Depending on what `_queries.Run` executes, a value like `?status='; DELETE FROM Invoices; --` could run extra statements. Any signed-in user can reach this, because there's no `[RequireRole]` and every account can sign in. Use parameters (`@customer`, `@status`). Better still, drop raw SQL entirely (see 2 and 3). Unescaped `%` and `_` in `customer` also act as LIKE wildcards, which a fix should handle.

**2. `_queries` probably doesn't exist, so this won't build or won't work: `:35`** (medium-high confidence, unverified)
The diff never declares `_queries` or adds it to the constructor. `AGENTS.md` says the app uses an in-memory repository, and that the database under `ops/` is *planned*, not built. There's no `Invoices` table to query. Either this fails to compile, or `_queries` is wired to something that isn't real. I couldn't confirm because the source isn't in the workspace.

**3. Query logic in the controller breaks project rules: `:26–36`** (high confidence)
`AGENTS.md` says business logic stays out of controllers, and data access goes through a repository interface in Domain with an in-memory implementation in Api. The search should be a method like `IInvoiceRepository.Search(customer, status)` that filters in memory, with the controller just calling it.

**4. No checking of `status`: `:30–33`** (medium confidence)
Status can only be `Draft`, `PendingApproval`, `Approved` or `Rejected`. Any other value quietly returns an empty list. It should return 400, either by binding to the status enum or by going through `Handle(...)` like the other endpoints. The endpoint also skips `Handle(...)` completely, so domain errors won't map to 404, 409 or 400.

**5. No tests** (high confidence)
`AGENTS.md` says every new endpoint needs tests using `FakeInvoiceRepository`. The diff adds none.

**6. `SELECT *` sends every column to the client: `:28`** (low-medium confidence)
If the store ever holds columns that shouldn't go to the client, they'll leak. Return the same invoice model that `GetAll` returns.

## Not a defect
- Route clash between `search` and `{id}`: ASP.NET Core routing prefers the literal segment, so `GET api/invoices/search` won't be read as an id.
