# case-03 / baseline / run 2

- model: claude-opus-5-5
- attempt: 1
- duration_ms: 31805
- cost_usd: 0.079818
- tool calls denied: 0

---

I found two defects, both in how the new code rounds. There was no source in the working directory, so I reviewed the diff on its own, without callers, tests or the project's target framework.

---

### 1. The discount is now cut down to whole cents, so customers are often overcharged by 1¢
**File:** `backend/src/InvoiceApp.Domain/DiscountCalculator.cs`, line 16 (inner `Math.Round(discount, 2, MidpointRounding.ToZero)`)

**What goes wrong:** Before, the code worked out the exact discounted total and then rounded it to the nearest cent, rounding halves up. Now the discount itself is cut down to whole cents before it's subtracted. That makes the discount smaller and the total larger whenever the discount has a third decimal place. The bias always goes against the customer, by up to 0.0099:

| amount | % | old result | new result |
|---|---|---|---|
| 9.99 | 15 | 8.49 (9.99 − 1.4985 = 8.4915) | **8.50** (9.99 − 1.49) |
| 19.99 | 7 | 18.59 (18.5907) | **18.60** (19.99 − 1.39) |
| 0.09 | 10 | 0.08 (0.081) | **0.09** (no discount at all; 0.009 → 0.00) |

The last row shows that on small amounts the discount can disappear completely. Totals that used to be correct will now be off by a cent, and any existing tests or stored invoice totals will stop matching. If something else shows the discount line with the old rounding, the printed discount and the printed total won't add up.

**Confidence:** High that this changes results as shown. Medium that it's unintended: nothing in the diff (no comment, no test) suggests you meant to switch to truncation, and you wouldn't normally choose a rounding direction that only ever favours the seller without saying so.

---

### 2. The outer rounding now cuts off extra decimals instead of rounding them
**File:** `backend/src/InvoiceApp.Domain/DiscountCalculator.cs`, line 17 (outer `..., 2, MidpointRounding.ToZero)`)

**What goes wrong:** If `amount` already has only 2 decimal places, `amount − (2-decimal discount)` also has 2, so this outer round does nothing. But if `amount` can have more decimals (4-decimal unit prices, fractional quantities, or an amount that includes tax), the final value is now cut off rather than rounded. For example, `Apply(10.005m, 0m)` used to return 10.01 and now returns 10.00, and `Apply(10.019m, 0m)` returns 10.01 instead of 10.02.

**Confidence:** Medium. It only matters if callers pass amounts with more than 2 decimals, which I couldn't check.

---

### Lower-confidence note
- **Line 16–17, `MidpointRounding.ToZero`:** this option only exists on .NET Core 3.0 and later (and .NET 5+). If `InvoiceApp.Domain` targets `netstandard2.0` or .NET Framework, the code won't compile. **Confidence:** Low, since I couldn't see the `.csproj`. The build would catch it straight away anyway.

**Suggested fix:** If the goal wasn't to change rounding behaviour, go back to rounding the final total once (`Math.Round(amount - discount, 2, MidpointRounding.AwayFromZero)`). If you do want to round the discount on its own (for example, so the discount line and total always add up on the invoice), round it with `AwayFromZero` instead of `ToZero`. Then add a test with the 9.99 @ 15% case.
