# case-06 / agents-md / run 5

- model: claude-opus-5-5
- attempt: 1
- duration_ms: 29506
- cost_usd: 0.0887222
- tool calls denied: 0

---

I couldn't check this diff against the code. The working directory has only `CLAUDE.md`, `AGENTS.md` and some harness files. `ApprovalService`, `Invoice`, `FakeInvoiceRepository` and the rest of `ApprovalServiceTests.cs` (including the `Pending(...)` helper) aren't there. So I can't confirm the exception types, the property names, or that the code compiles.

**I found no definite defects in the diff on its own.** The points below are risks that depend on code I couldn't see, plus two gaps in what the tests check.

## Risks that depend on the unseen code

1. **`ApprovalServiceTests.cs:40` (diff line), `Assert.Throws<KeyNotFoundException>`.** `Assert.Throws<T>` only passes if the exception is exactly that type, not a subclass. `AGENTS.md` says `ApiControllerBase.Handle(...)` maps service errors to 404/409/400. That often means the service throws its own exception, such as `InvoiceNotFoundException`. If the service throws anything other than exactly `KeyNotFoundException`, even a subclass of it, this test fails. If it should accept subclasses, use `Assert.ThrowsAny<KeyNotFoundException>`. **Confidence: low to medium.**

2. **`ApprovalServiceTests.cs:17`, `Assert.Throws<ArgumentException>`.** The same exact-type rule applies. A whitespace reason checked with `ArgumentException.ThrowIfNullOrWhiteSpace` throws exactly `ArgumentException`, so that passes. But if the service throws a subclass, a custom validation exception, or `InvalidOperationException` (which `Handle` might map to 400 or 409), the test fails. **Confidence: low.**

3. **`ApprovalServiceTests.cs:27–32`, the time check.** This is only correct if the service stamps `DecidedAt` with `DateTime.UtcNow`:
   - If it uses `DateTime.Now`, the test fails on any machine outside UTC. That would be a real bug in the service, not the test.
   - If `DecidedAt` is a `DateTimeOffset?`, the code still compiles because `DateTime` converts implicitly, and it behaves correctly.
   - If the service takes a clock or `TimeProvider`, `new ApprovalService(repository)` doesn't compile. The existing tests apparently use the same constructor, so this is unlikely.

   **Confidence: low.**

## Gaps in what the tests check (not bugs)

4. **`ApprovalServiceTests.cs:30–32`.** The test only checks the returned `result`, never what the repository stored. If `Approve` returns an updated copy (for example a record built with `with`) and never saves it, this test still passes. Re-reading `repository.Get("INV-901")` and asserting on that would catch it. **Confidence that the gap exists: high. Whether it hides a real bug: unknown.**

5. **`ApprovalServiceTests.cs:17`.** The test doesn't check that the invoice is still `PendingApproval` after the rejected call. A service that changes the status before validating the reason would pass. **Same confidence as #4.**

If you can share `ApprovalService.cs`, the invoice model and `FakeInvoiceRepository.cs`, I can confirm or rule out #1–#3.
