# case-03 / agents-md / run 5

- model: claude-opus-5-5
- attempt: 1
- duration_ms: 30295
- cost_usd: 0.08090639999999999
- tool calls denied: 0

---

I couldn't check this against the code: the working directory has only `AGENTS.md`, `CLAUDE.md` and a few run artifacts. There's no `backend/` folder, so I couldn't see the rest of `DiscountCalculator.cs`, its callers, or tests. Everything below comes from the diff alone.

## Findings

### 1. Prices now round up for the merchant instead of to the nearest cent
**File:** `backend/src/InvoiceApp.Domain/DiscountCalculator.cs`, new lines 16–17
**Confidence:** High that the behaviour changed (it follows from the arithmetic). Medium that it's a defect, because I can't see a stated reason for it.

Before, the code took the exact discounted amount and rounded it to the nearest cent. Now it cuts the discount down to 2 decimal places first (`ToZero`), then subtracts. So the customer loses any fraction of a cent in the discount, and the final price is effectively rounded up rather than to the nearest cent. The overcharge is up to 0.0099 per invoice.

Examples:

| amount | discount % | exact result | old | new |
|---|---|---|---|---|
| 19.99 | 7.5 | 18.49075 | 18.49 | **18.50** |
| 0.99 | 15 | 0.8415 | 0.84 | **0.85** |

If this was meant to be a refactor or a precision fix, it's a regression. If the business really wants the discount truncated, that's a pricing-policy change and needs a test that pins it. If any existing tests assert `AwayFromZero` results, those cases will now fail.

### 2. The outer `ToZero` rounding is either pointless or truncates
**File:** same, line 17 (`2, MidpointRounding.ToZero`)
**Confidence:** Medium

- If `amount` always has 2 decimal places, `amount - <2-dp discount>` already has 2 decimal places, so the outer `Math.Round` does nothing.
- If `amount` can have more decimal places, this rounding cuts the result down instead of rounding to the nearest cent. For example, `10.005` at 0% now gives 10.00, where the old code gave 10.01.

Either way, it's a second silent change from `AwayFromZero` to `ToZero`.

### 3. Negative amounts or negative percentages round in the opposite direction
**File:** same, line 16
**Confidence:** Low to medium. It only matters if callers pass credit notes or surcharges, and I couldn't check that.

`ToZero` moves negative values up towards zero, so the effect is mirrored for negative inputs:
- With a negative percentage (a surcharge), the surcharge gets truncated, which favours the customer.
- With a negative amount (a credit), the credit gets slightly bigger.

The rounding direction therefore depends on the sign of the input, which is unlikely to be intended.

### 4. A blank line is left behind (cosmetic)
**File:** same, after line 14
**Confidence:** High

Removing `var discounted = ...` leaves a blank line between `var discount` and `return`.

## Recommendation
If the goal is for discount and net amount to add up exactly to the original amount, round the discount on its own with the original mode, then subtract without a second rounding:

```csharp
var discount = Math.Round(amount * (discountPercent / 100m), 2, MidpointRounding.AwayFromZero);
return amount - discount;
```

Whatever rounding you choose, add tests in `DiscountCalculatorTests` for cases like 19.99 @ 7.5% and 0.99 @ 15% so the rule is written down.
