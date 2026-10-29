# case-06 / agents-md / run 4

- model: claude-opus-5-5
- attempt: 1
- duration_ms: 29126
- cost_usd: 0.08510519999999999
- tool calls denied: 0

---

I found no definite defects in this diff. That comes with a big caveat: the workspace has no source code. It holds only `AGENTS.md`, `CLAUDE.md` and a few harness files, with no `backend/` folder. So I couldn't check the new tests against `ApprovalService`, `Invoice`, `FakeInvoiceRepository`, the `Pending(...)` helper or the rest of `ApprovalServiceTests.cs`. Judged on the diff alone, the three tests are well-formed and follow the project conventions: `FakeInvoiceRepository` is used, names are clear, and there's one class per class under test.

These are the assumptions that would make a test fail. Each needs checking against the real code:

1. **`ApprovalServiceTests.cs`, line 17 (`Assert.Throws<ArgumentException>`).** `Assert.Throws` needs the exact type, not a subclass. The test fails if `Reject` throws `ArgumentNullException`, `ArgumentOutOfRangeException`, `InvalidOperationException` or a custom validation exception for a whitespace reason. It also fails if `Reject` doesn't trim before checking (an `IsNullOrEmpty` check rather than `IsNullOrWhiteSpace`). Confidence it's a real defect: **low**. `ArgumentException.ThrowIfNullOrWhiteSpace` throws exactly `ArgumentException` for whitespace, and AGENTS.md's "400" mapping suggests `ArgumentException` is the convention.

2. **Line 32 (`Assert.InRange(..., before, DateTime.UtcNow)`).** This assumes `Approve` stamps `DecidedAt` with `DateTime.UtcNow` at full precision. The test fails if the service uses `DateTime.Now`, an injected `TimeProvider` or clock, or rounds the time (for example to whole seconds, which can land before `before`). Confidence: **low to medium**. It depends on the implementation, and this is the most fragile assertion in the diff. If the service takes a clock, the better test injects a fixed time and asserts equality.

3. **Line 40 (`Assert.Throws<KeyNotFoundException>`).** Same exact-type issue as line 17. It fails if the repository or service signals a missing invoice another way, such as a custom `InvoiceNotFoundException` or returning null. Confidence: **low**. The 404 mapping in `ApiControllerBase.Handle` suggests `KeyNotFoundException`.

4. **Lines 11, 21 and 36 (method names).** I can't see lines 1–58. If a test with any of these names already exists, the file won't compile. `Reject_WithWhitespaceReason_Throws` is the most likely clash if an empty-reason test is already there. Confidence: **low**.

5. **Lines 28 and 40 (approver `"nitin"`).** If `ApprovalService` stops someone approving their own invoice and `Pending(...)` sets the submitter to `"nitin"`, line 28 would throw. Confidence: **low**.

If you point me at the repo with `backend/src/InvoiceApp.Domain` and the full test file, I can check each of these and give you a firm answer.
