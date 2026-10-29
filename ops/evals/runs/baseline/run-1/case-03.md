# case-03 / baseline / run 1

- model: claude-opus-5-5
- attempt: 1
- duration_ms: 25009
- cost_usd: 0.0791772
- tool calls denied: 0

---

I found two defects and one compatibility risk. There are no other files in the working directory, so I couldn't check callers, tests or the target framework. Everything below is based on the diff alone.

### 1. `backend/src/InvoiceApp.Domain/DiscountCalculator.cs:16`: `MidpointRounding.ToZero` truncates; it doesn't just settle ties
**Confidence: high** that this changes results. **Medium** that the change is unintended.

The name suggests it only decides what happens to values ending in exactly 5. In fact, `ToZero` (along with `ToNegativeInfinity` and `ToPositiveInfinity`, added in .NET Core 3.0) always rounds toward zero. So `Math.Round(discount, 2, MidpointRounding.ToZero)` throws away everything after the second decimal place.

The result is a smaller discount and a higher price, off by one cent in many ordinary cases:

| amount | % | exact discount | old result | new result |
|---|---|---|---|---|
| 9.99 | 15 | 1.4985 | 8.4915 → **8.49** | 9.99 − 1.49 = **8.50** |
| 19.99 | 33 | 6.5967 | 13.3933 → **13.39** | 19.99 − 6.59 = **13.40** |

Any invoice where the discount has a third decimal place of 5 or more now costs a cent more. Totals stored or printed before this change won't match recalculated ones, and existing tests that assert the old values should fail. If the goal was half-up rounding of the discount line, use `MidpointRounding.AwayFromZero` for the inner `Round`.

### 2. `backend/src/InvoiceApp.Domain/DiscountCalculator.cs:17`: the outer `ToZero` truncates the final amount in the other direction
**Confidence: high** about the behaviour. **Medium** about its impact, which depends on whether `amount` can have more than 2 decimal places.

If `amount` always has 2 decimal places, the outer `Round` does nothing. If `amount` can have more (for example, unit price × fractional quantity, or FX-converted values), the final result is now truncated rather than rounded. For example, `Apply(10.005m, 0)` used to return 10.01 and now returns 10.00.

The two roundings also pull in opposite directions. Truncating the discount favours the seller, while truncating the result favours the customer. That points to a misunderstanding of the enum rather than a deliberate policy.

### 3. `backend/src/InvoiceApp.Domain/DiscountCalculator.cs:16–17`: needs .NET Core 3.0 or later
**Confidence: low** (I couldn't see the `.csproj`).

`MidpointRounding.ToZero` doesn't exist in .NET Framework or `netstandard2.0`. If the Domain project targets either of those, this won't compile.

**Minor:** the blank line that used to follow `var discounted` now sits between `var discount` and `return` (line 15). It's harmless.

If the rounding change was intended (truncating the discount as a business rule), it should come with a comment and updated tests. As written, it reads like `ToZero` was mistaken for a tie-breaking rule.
