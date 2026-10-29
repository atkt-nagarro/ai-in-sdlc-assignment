# case-03 / agents-md / run 6

- model: claude-opus-5-5
- attempt: 1
- duration_ms: 29199
- cost_usd: 0.0856536
- tool calls denied: 0

---

I found two defects in the diff and one missing test. I couldn't check them against real code: the working directory only has `AGENTS.md`, `CLAUDE.md` and the diff, not `DiscountCalculator.cs`, its callers or its tests. So I can't tell whether invoice amounts ever have more than 2 decimal places, or which rounding the business actually wants. Line numbers refer to the new file, based on the hunk header `@@ -12,9 +12,9`.

### 1. Totals come out up to 1 cent higher than before
**File:** `backend/src/InvoiceApp.Domain/DiscountCalculator.cs`, line 16 (the inner `Math.Round(discount, 2, MidpointRounding.ToZero)`)

The old code rounded the final total to the nearest cent. The new code cuts the discount down to whole cents before subtracting it. For a normal 2-decimal amount, the result is now always `amount − truncated discount`. Whenever the discount's leftover fraction of a cent is more than half a cent, the total is 1 cent higher than it used to be:

- `Apply(10.00m, 15.678m)`: discount = 1.5678
  - Old: 10.00 − 1.5678 = 8.4322 → **8.43**
  - New: 10.00 − 1.56 = **8.44**

The error always goes against the customer, and it changes amounts that existing invoices and tests already expect. If the goal is "never give more discount than the stated percentage", that's a deliberate policy change. It should be stated, and the tests that pin the old values should be updated. If it isn't deliberate, it's a regression.

**Confidence:** High that the behaviour changed (the arithmetic above is exact). Medium that it's unintended, because the change has no explanation and no tests.

### 2. Amounts with more than 2 decimals are now cut off, even with no discount
**File:** same file, line 17 (the outer `2, MidpointRounding.ToZero`)

The outer rounding changed from `AwayFromZero` to `ToZero`, so any amount with more than 2 decimal places is now cut off instead of rounded. This happens even when the discount is 0:

- `Apply(10.005m, 0m)`: old **10.01**, new **10.00**
- `Apply(19.999m, 0m)`: old **20.00**, new **19.99**

**Confidence:** High that this happens if such amounts can reach this method. Low to medium that it matters in practice, since I couldn't see whether amounts are limited to 2 decimals upstream.

### 3. No tests for the changed rule
`AGENTS.md` says every new rule needs tests in `DiscountCalculatorTests`. The diff changes the rounding rule without adding or updating any. Tests for a fraction above half a cent, an exact half cent, a negative amount (credit note) and a 3-decimal amount would have shown both issues above.

**Confidence:** High that this breaks the project convention. I couldn't confirm whether existing tests now fail, because the test project isn't in the working directory.

### Checked and fine
- **Negative amounts and negative percentages:** `ToZero` treats positive and negative values the same way, so credit notes and surcharges behave like the positive case, with the same 1-cent drift as issue 1. Nothing extra breaks.
- **The leftover blank line** where `discounted` was removed is cosmetic only.
