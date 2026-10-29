# Review eval: results

## Setup

| | |
| --- | --- |
| Cases | The 10 fixed cases, plus [case-11](cases/case-11.diff) (defect) and [case-12](cases/case-12.diff) (clean) added by me ([why these two](cases/README-added-cases.md)). 9 defect cases, 3 clean. |
| Prompt | v1, verbatim from `README.md` |
| Model | `claude-opus-5-5`, effort `high`, Claude Code 2.1.306 |
| Isolation | One fresh session per case, in an empty temp directory. No MCP servers, no session persistence. File tools can't reach outside the directory, and no tool call was denied in any run. Harness: [run-eval.sh](run-eval.sh). |
| Runs | 1–3 baseline (no context file). 4–6 with the single change. |
| The one change | The context file: the repository's `CLAUDE.md` (which imports `AGENTS.md`) placed in the working directory. Nothing else differs. |
| Scoring | Strict, against [answer-key.md](answer-key.md). The key was committed in `9e8defb` at 17:23:16Z, and the first run started at 17:23:26Z. Raw outputs are in `runs/`; scores in [results.csv](results.csv). |

## Results

| Runs | Context file | Caught | Missed | False alarms |
| --- | --- | --- | --- | --- |
| 1 | none | 9/9 | 0/9 | 0/3 |
| 2 | none | 9/9 | 0/9 | 0/3 |
| 3 | none | 9/9 | 0/9 | 0/3 |
| **1–3** | **none** | **27/27 = 100%** (95% CI 87.5–100%) | **0%** | **0/9 = 0%** (95% CI 0–29.9%) |
| 4 | AGENTS.md | 9/9 | 0/9 | 0/3 |
| 5 | AGENTS.md | 9/9 | 0/9 | 0/3 |
| 6 | AGENTS.md | 9/9 | 0/9 | 1/3 |
| **4–6** | **AGENTS.md** | **27/27 = 100%** (95% CI 87.5–100%) | **0%** | **1/9 = 11.1%** (95% CI 2.0–43.5%) |

Every defect was caught in all six runs. The only miss of any kind is a false alarm in run 6, on case-06 (see [scoring reliability](#scoring-reliability)). Leaving out case-09, the contested label, changes nothing: 24/24 caught in both conditions.

## Was the change an improvement?

**No.** Caught rates are identical. The context file added one false alarm, 1/9 against 0/9. A paired comparison by case gives the baseline better on one case, worse on none, with 11 tied (sign test p = 1.0).

What the context file did change:

- **Cost and time:** median per review $0.072 against $0.055 (+31%), and 24 s against 20 s.
- **Repository-specific findings.** With AGENTS.md the reviewer added convention breaches the baseline could not know about: no tests for a new rule, `Handle(...)` bypassed, business logic in a controller.
  - On case-09 it caught a second true inaccuracy in all three runs: the demo accounts live in `appsettings.json`, not "the in-memory store".
- **More confidence in an unverifiable claim.** On case-02 it rated "`_queries` probably does not exist, so this won't build" at medium-high, because AGENTS.md says there is no database. The baseline runs rated the same claim low. The diff cannot show whether `_queries` exists.

My verdict: keep AGENTS.md for the repository-specific findings it adds, and accept that this eval cannot show it improves detection. If anything it made the reviewer slightly noisier.

## How confident am I at this sample size

Not very, and the data says why.

- **Ceiling.** At 27/27 the lower 95% bound is 87.5%. Treating the three runs of a case as independent overstates the evidence, because the same case gives the same answer every time. Counted by case, 9/9 only bounds the catch rate above 70%.
- **False alarms rest on 3 clean cases.** 0/9 is compatible with a true false-alarm rate of up to 30%, and 1/9 with up to 44%. One review flipping on one case moved the rate by 11 points.
- **A large real difference barely registers.** As a sensitivity check, outside the one-change comparison, I ran the same set with a smaller model:

| Model | Caught | False alarms | Median cost per review |
| --- | --- | --- | --- |
| `claude-opus-5-5` (runs 1–3) | 27/27 = 100% | 0/9 | $0.055 |
| `claude-haiku-4-5-20251001` ([probe](results-probe-haiku.csv)) | 19/27 = 70% (CI 52–84%) | 1/9 (CI 2–44%) | $0.017 |

The smaller model missed case-11 (the duplicate-payment retry) and case-09 in all three runs. It missed case-03 twice by describing `ToZero` as tie-breaking. It also raised one false alarm, a "race condition" in a correct timing assertion. That is a gap of 30 points, yet paired by case it is 4 better, 0 worse and 8 tied, which gives p = 0.125. With 12 cases this eval can just about separate a weak reviewer from a strong one. It cannot detect the kind of change a prompt tweak or a context file makes.

## Scoring reliability

A second scorer re-scored all 108 reviews (72 main plus 36 probe). It was a separate agent working blind from the same answer key, told not to open my scores. Its verdicts are in [second-scorer.json](second-scorer.json).

- **Agreement:** 107 of 108 (99.1%), Cohen's kappa 0.98.
- **The one disagreement:** run 6, case-06. I had scored it clean. The second scorer called it a false alarm, and under the key's own rule it is right. Unlike runs 1–5, that review never says it found no defects, and its findings list asserts two test failures that would not happen (an `InRange` type error, an exact-exception mismatch). Its first finding, that the hunk header does not match the body, is true. I changed my score to false alarm.

## What I would change before trusting it for comparisons

- **Harder cases**, so strong models do not all score 100%: defects that need two files, or knowledge of the conventions, to see.
- **As many clean cases as defect cases.** False alarms are what make people stop reading reviews, and 3 clean cases cannot measure them.
- **Score noise as well as verdicts.** Count wrong findings per review on defect cases too.
- **Fix the fixtures.** 7 of the 10 original diffs (02, 03, 04, 06, 07, 08, 10) have hunk headers that do not match their bodies. The reviewer noticed this on case-06 in 3 of 6 runs. I verified it, and scored it as true, not a false alarm.
- **Keep the eval cases away from agents that have repository access.** The ADR sparring agent read `case-11.diff` and cited it as production history (see ADR-001).

## Files

- `runs/baseline/run-{1,2,3}`, `runs/agents-md/run-{4,5,6}`, `runs/probe-haiku/run-{1,2,3}`: raw JSON and the review text for every case
- [results.csv](results.csv), [results-probe-haiku.csv](results-probe-haiku.csv): one scored row per case per run
- [summary.txt](summary.txt), [summary-probe-haiku.txt](summary-probe-haiku.txt): output of `python3 ops/evals/summarize.py`
