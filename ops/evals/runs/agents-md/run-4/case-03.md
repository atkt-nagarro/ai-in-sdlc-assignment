# case-03 / agents-md / run 4

- model: claude-opus-5-5
- attempt: 1
- duration_ms: 33372
- cost_usd: 0.0914772
- tool calls denied: 0

---

I found two defects and one related risk. The repo doesn't contain `DiscountCalculator.cs` or any other `.cs` files, so I reviewed the diff alone. I couldn't check callers, existing tests, or whether amounts can have more than two decimal places.

### 1. `MidpointRounding.ToZero` cuts off digits; it doesn't round halves down
**File:** `backend/src/InvoiceApp.Domain/DiscountCalculator.cs`, line 16 (inner `Math.Round`)

In .NET, `MidpointRounding.ToZero` rounds every value toward zero, not just values ending in exactly 5. So `Math.Round(discount, 2, MidpointRounding.ToZero)` simply drops everything after the second decimal place. The discount is now always rounded down. Because it's subtracted, the customer pays up to 0.0099 more on every non-exact discount, and that adds up across invoices.

Examples:
- 9.99 at 15%: the exact discount is 1.4985. Old result: 8.4915 → **8.49**. New result: 9.99 − 1.49 = **8.50**.
- 19.99 at 33%: the exact discount is 6.5967. Old result: **13.39**. New result: 19.99 − 6.59 = **13.40**.

Only exact halves (like 0.025) come out the same both ways.

**Confidence:** High that the behaviour changes as described. Medium that it's a mistake rather than a deliberate "always round discounts down" policy. The name `ToZero` suggests the author may have thought it only affects halves, and the diff has no comment, test, or rationale.

### 2. The outer `Math.Round(..., ToZero)` changes results even with no discount
**File:** same file, lines 16–17 (outer `Math.Round`)

If `amount` already has two decimal places, the outer round does nothing. If it has more (for example, unit price × quantity), the total is now cut off instead of rounded half away from zero. So `Apply(10.005m, 0m)` used to return **10.01** and now returns **10.00**. A 0% discount should leave the amount unchanged except for normal rounding, and before this change it did.

**Confidence:** High that the behaviour changes. Medium that it matters, depending on whether amounts with more than two decimal places ever reach this method.

### 3. Tests probably weren't updated
**File:** `backend/tests/InvoiceApp.Tests/DiscountCalculatorTests.cs` (expected per `AGENTS.md`; not present in this workspace)

This changes a money calculation rule, but the diff includes no test changes. Any existing tests for cases like 9.99 at 15% should now fail. If they don't, nothing covers this code path. `AGENTS.md` requires tests for every new rule.

**Confidence:** Medium. I couldn't see the test project.

**Suggested fix:** If rounding discounts down is intended, write it as `Math.Truncate(discount * 100m) / 100m`, add a comment and tests, and keep the original `AwayFromZero` rounding for the final amount. If it isn't intended, revert to the original code.
