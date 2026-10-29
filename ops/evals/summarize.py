"""Turns a scored results CSV into the rates, intervals and per-case grid used in RESULTS.md."""

import csv
import json
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFECT_VERDICTS = {"caught", "missed"}
CLEAN_VERDICTS = {"clean", "false_alarm"}
ADDED_CASES = {"case-11", "case-12"}
CONTESTED_CASE = "case-09"


def wilson(successes, trials, z=1.96):
    if trials == 0:
        return float("nan"), float("nan")
    rate = successes / trials
    denominator = 1 + z * z / trials
    centre = (rate + z * z / (2 * trials)) / denominator
    half_width = z * math.sqrt(rate * (1 - rate) / trials + z * z / (4 * trials * trials)) / denominator
    return max(0.0, centre - half_width), min(1.0, centre + half_width)


def rate_line(label, hits, trials):
    low, high = wilson(hits, trials)
    return f"  {label:26} {hits:2}/{trials:<2} = {hits / trials:6.1%}   95% CI {low:5.1%} - {high:5.1%}"


def exact_sign_test(better, worse):
    """Two-sided exact sign test on discordant cases; ties are dropped."""
    discordant = better + worse
    if discordant == 0:
        return 1.0
    tail = sum(math.comb(discordant, k) for k in range(0, min(better, worse) + 1)) / 2 ** discordant
    return min(1.0, 2 * tail)


def condition_of(row):
    return f"{row['model']} / context={row['context_file']}"


def raw_stats(rows):
    """Median words, cost and duration per review, read from the saved raw outputs."""
    words, costs, millis = [], [], []
    for row in rows:
        label = "agents-md" if row["context_file"] == "AGENTS.md" else "baseline"
        folder = HERE / "runs" / row.get("run_label", label) / f"run-{row['run']}"
        raw = json.loads((folder / f"{row['case']}.json").read_text())
        words.append(len(raw["result"].split()))
        costs.append(raw.get("total_cost_usd") or 0)
        millis.append(raw.get("duration_ms") or 0)
    return statistics.median(words), statistics.median(costs), statistics.median(millis) / 1000, sum(costs)


def summarise(rows, title):
    defect_rows = [r for r in rows if r["verdict"] in DEFECT_VERDICTS]
    clean_rows = [r for r in rows if r["verdict"] in CLEAN_VERDICTS]
    caught = sum(r["verdict"] == "caught" for r in defect_rows)
    false_alarms = sum(r["verdict"] == "false_alarm" for r in clean_rows)
    runs = sorted({int(r["run"]) for r in rows})
    print(f"{title}  (runs {runs})")
    print(rate_line("caught", caught, len(defect_rows)))
    print(rate_line("missed", len(defect_rows) - caught, len(defect_rows)))
    print(rate_line("false alarm", false_alarms, len(clean_rows)))
    for run in runs:
        run_defects = [r for r in defect_rows if int(r["run"]) == run]
        run_clean = [r for r in clean_rows if int(r["run"]) == run]
        print(f"    run {run}: caught {sum(r['verdict'] == 'caught' for r in run_defects)}/{len(run_defects)}, "
              f"false alarms {sum(r['verdict'] == 'false_alarm' for r in run_clean)}/{len(run_clean)}")
    without = [r for r in defect_rows if r["case"] != CONTESTED_CASE]
    print(rate_line(f"caught without {CONTESTED_CASE}", sum(r["verdict"] == "caught" for r in without), len(without)))
    added = [r for r in rows if r["case"] in ADDED_CASES]
    print(f"  added cases 11-12: {sum(r['verdict'] in ('caught', 'clean') for r in added)}/{len(added)} scored correctly")
    defect_cases = sorted({r["case"] for r in defect_rows})
    always = sum(all(r["verdict"] == "caught" for r in defect_rows if r["case"] == case) for case in defect_cases)
    print(rate_line("defect cases caught 3/3", always, len(defect_cases)))
    try:
        words, cost, seconds, total = raw_stats(rows)
        print(f"  per review: median {words:.0f} words, {seconds:.0f} s, ${cost:.3f}; total ${total:.2f}")
    except FileNotFoundError:
        pass
    print()


def grid(rows):
    by_case = defaultdict(dict)
    for row in rows:
        by_case[row["case"]][int(row["run"])] = row["verdict"]
    runs = sorted({int(r["run"]) for r in rows})
    short = {"caught": "C", "missed": "M", "clean": "ok", "false_alarm": "FA"}
    print("per-case grid (C caught, M missed, ok clean, FA false alarm)")
    print("  case     " + " ".join(f"r{run:<3}" for run in runs))
    for case in sorted(by_case):
        print(f"  {case}  " + " ".join(f"{short[by_case[case].get(run, '')]:4}" for run in runs))
    print()


def paired(rows):
    """Compares conditions case by case: how many runs out of three each got right."""
    conditions = sorted({condition_of(r) for r in rows})
    if len(conditions) != 2:
        return
    score = defaultdict(lambda: defaultdict(int))
    for row in rows:
        score[row["case"]][condition_of(row)] += row["verdict"] in ("caught", "clean")
    first, second = conditions
    better = sum(score[c][second] > score[c][first] for c in score)
    worse = sum(score[c][second] < score[c][first] for c in score)
    print(f"paired by case: '{second}' better on {better} cases, worse on {worse}, "
          f"tied on {len(score) - better - worse}; exact sign test p = {exact_sign_test(better, worse):.2f}")


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "results.csv"
    with path.open() as handle:
        rows = list(csv.DictReader(handle))
    if len(sys.argv) > 2:
        for row in rows:
            row["run_label"] = sys.argv[2]
    for condition in sorted({condition_of(r) for r in rows}):
        summarise([r for r in rows if condition_of(r) == condition], condition)
    grid(rows)
    paired(rows)


if __name__ == "__main__":
    main()
