# case-03 / baseline / run 3

- model: claude-opus-5-5
- attempt: 1
- duration_ms: 26170
- cost_usd: 0.070788
- tool calls denied: 0

---

I found three problems, all coming from the rounding change. Only the diff was available: the working directory contains just the diff and none of the project's source, tests or `.csproj`. So I couldn't check the target framework, the callers, or whether this change was meant to happen.

### 1. Customers are now charged up to 1¢ more — `DiscountCalculator.cs:16` (the new `return` line)
**What goes wrong:** In .NET Core 3.0 and later, `MidpointRounding.ToZero` doesn't just decide how to round halves. It always rounds toward zero, which for positive numbers means chopping off the extra digits. So the inner `Math.Round(discount, 2, MidpointRounding.ToZero)` always rounds the discount **down**, and the customer gets a smaller discount than before.

- `Apply(9.99m, 15m)`: the discount is 1.4985. Old code: 9.99 − 1.4985 = 8.4915 → **8.49**. New code: discount cut to 1.49 → 9.99 − 1.49 = **8.50**
- `Apply(19.99m, 10m)`: the discount is 1.999. Old code: 17.991 → **17.99**. New code: discount cut to 1.99 → **18.00**

The old code rounded the final price to the nearest cent. The new code rounds the discount down, which always favours the seller and can overcharge by up to 0.01 per call. If `Apply` is called once per line item, the error adds up across an invoice. Any other code that works out "discount = amount − Apply(...)", or rounds the discount line with `AwayFromZero`, will now be a cent off from this result.

**Confidence:** High that the results change and that the new results are wrong under the old "round the final price to the nearest cent" rule. Medium that it's a bug and not a deliberate policy change: nothing in the diff says the change is intended, and no tests were updated.

### 2. The outer round now cuts off digits instead of rounding — same line
**What goes wrong:** The outer `Math.Round(..., 2, MidpointRounding.ToZero)` also chops instead of rounding to the nearest cent. When `amount` is already a whole number of cents, it does nothing. But if `amount` has more than two decimal places (for example, unit price × a fractional quantity, or tax-inclusive amounts), the result is now cut short. For example, `Apply(10.005m, 0m)` used to return 10.01 and now returns 10.00. Combined with finding 1, the code now rounds twice, which differs from the old single round to the nearest cent.

**Confidence:** High that the behaviour differs. Medium that it matters, because that depends on whether callers ever pass amounts with more than two decimal places.

### 3. Possible build failure on older frameworks — same line
**What goes wrong:** `MidpointRounding.ToZero` only exists in .NET Core 3.0+ / .NET 5+. If `InvoiceApp.Domain` targets `netstandard2.0` or .NET Framework, this won't compile.

**Confidence:** Low. I couldn't see the project file.

### Minor
- Line 15: removing `var discounted` leaves a stray blank line. This is cosmetic only.

**Suggested fix:** If the aim is to round the discount to a whole cent so it can be shown as its own line, round it the same way the old code did (`AwayFromZero`) and drop the outer round. Then the discount line and the discounted price always add up to the original amount:
```csharp
var discount = Math.Round(amount * (discountPercent / 100m), 2, MidpointRounding.AwayFromZero);
return amount - discount;
```
If the aim wasn't to change rounding at all, revert this change. Either way, add tests for cases like `9.99 @ 15%` and `19.99 @ 10%` so the expected rounding is pinned down.
