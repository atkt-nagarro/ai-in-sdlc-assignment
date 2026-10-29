# case-06 / agents-md / run 6

- model: claude-opus-5-5
- attempt: 1
- duration_ms: 35930
- cost_usd: 0.0981146
- tool calls denied: 0

---

I couldn't check this diff against the real code. The working directory only contains `CLAUDE.md`, `AGENTS.md` and a few harness files. `ApprovalService`, `FakeInvoiceRepository`, the `Pending(...)` helper and the existing test file aren't there, so the findings below come from the diff alone.

## Findings

**1. The hunk header doesn't match the body, so the patch probably won't apply**
- **Where:** the `@@ -58,4 +58,34 @@` line.
- **What goes wrong:** The header says 4 old lines and 34 new lines, which means 30 added lines. The body actually has 3 unchanged lines and 33 added lines, so it should be about `-58,3 +58,36`. `git apply` and `patch` will likely reject it as a corrupt patch. If the diff was edited by hand or cut short when pasted, regenerate it before merging.
- **Confidence:** High that the counts don't match. Medium that it matters, since the mismatch may have come from copying the diff rather than from the real change.

**2. The time check in `Approve_RecordsTheApproverAndTime` assumes things about the service** (about line 80)
- **What goes wrong:** `Assert.InRange(result.DecidedAt!.Value, before, DateTime.UtcNow)` only works if:
  - `DecidedAt` is a `DateTime?`. If it's a `DateTimeOffset?` or a non-nullable `DateTime`, the test won't compile.
  - The service sets it from `DateTime.UtcNow`. If it uses `DateTime.Now`, the test fails on any machine not set to UTC, which can include CI. If it gets the time from an injected clock (`TimeProvider`), then `new ApprovalService(repository)` won't compile, and the test should use a fake clock and check for an exact value.
- **Confidence:** Low to medium. This is a real risk, but I can't confirm it without the source.

**3. `Assert.Throws<T>` only passes on the exact exception type** (about lines 69 and 88)
- **What goes wrong:** xUnit's `Assert.Throws<T>` fails if the code throws a subclass of `T`. Two cases:
  - If `Approve` throws something like `InvoiceNotFoundException : KeyNotFoundException`, the unknown-invoice test fails. The same applies if `ApiControllerBase.Handle` maps a custom not-found exception to 404.
  - If `Reject` only checks for an empty reason and not a whitespace-only one, the whitespace test fails. That would be correct, because it would expose a real gap in the service.
- If subclasses are intended, use `Assert.ThrowsAny<T>`.
- **Confidence:** Low. Whether this is a defect depends on code I couldn't see.

## No problems found in
- Naming and structure: each test is in `ApprovalServiceTests`, uses `FakeInvoiceRepository`, and has a clear name, as `AGENTS.md` asks.
- Logic of each test, if the service behaves as the tests expect.
- Credentials or customer data: none. "nitin" is only a test username.

If you can add the `backend/` tree to the workspace, I can settle findings 2 and 3 for certain.
