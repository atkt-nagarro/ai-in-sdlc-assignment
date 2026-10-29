"""Baseline numbers we can capture today from the repo and its CI history (stdlib only)."""

import csv
import math
from collections import OrderedDict
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RUN_TIMINGS = REPO / "ops" / "pipeline" / "run-timings.csv"

# Production releases on record; "failed" = followed by an incident that needed remediation.
RELEASES = [
    ("2.13.4", "about 2026-01-05", False, "INC-2041/README.md: running nine days without incident"),
    ("2.14.0", "2026-01-14", True, "INC-2041: 5xx alert 14 minutes after the 09:58Z deploy"),
    ("2.14.3", "2026-01-16", False, "INC-2047/recent-changes.md: no incident recorded"),
    ("2.15.0", "2026-01-21", False, "INC-2047/recent-changes.md: no incident recorded"),
    ("2.15.1", "2026-01-28", True, "INC-2047: notifications stopped after the 08:41Z deploy"),
]
# Implied by the version numbers but absent from every record.
UNSEEN_RELEASES = ["2.14.1", "2.14.2"]


def parse_time(text):
    return datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def percentile(sorted_values, fraction):
    """Linear interpolation between closest ranks, same as numpy's default."""
    position = (len(sorted_values) - 1) * fraction
    lower, upper = math.floor(position), math.ceil(position)
    if lower == upper:
        return sorted_values[lower]
    return sorted_values[lower] + (sorted_values[upper] - sorted_values[lower]) * (position - lower)


def median(values):
    return percentile(sorted(values), 0.5)


def wilson_interval(successes, trials, z=1.96):
    rate = successes / trials
    denominator = 1 + z * z / trials
    centre = (rate + z * z / (2 * trials)) / denominator
    half_width = z * math.sqrt(rate * (1 - rate) / trials + z * z / (4 * trials * trials)) / denominator
    return max(0.0, centre - half_width), min(1.0, centre + half_width)


def load_rows():
    with RUN_TIMINGS.open() as handle:
        return list(csv.DictReader(handle))


def load_runs(rows):
    runs = OrderedDict()
    for row in rows:
        run = runs.setdefault(int(row["run_number"]), {
            "number": int(row["run_number"]),
            "started": parse_time(row["started_at"]),
            "branch": row["branch"],
            "event": row["event"],
            "conclusion": row["conclusion"],
            "seconds": 0,
            "steps": [],
        })
        run["seconds"] += int(row["duration_seconds"])
        run["steps"].append(row["step"])
    for run in runs.values():
        # Single job with sequential steps, so the run ends when its last step does.
        run["finished"] = run["started"] + timedelta(seconds=run["seconds"])
    return runs


def failed_step(run, all_steps):
    """Last step that ran; only 'Upload test results' runs after a failure (if: always())."""
    ran = [step for step in all_steps if step in run["steps"] and step != "Upload test results"]
    return ran[-1] if ran else "unknown"


def changes(runs, split_on_gap):
    """Group PR runs into changes, each merged by the first main push after its last PR run."""
    main_pushes = [run for run in runs.values() if run["event"] == "push"]
    by_branch = OrderedDict()
    for run in runs.values():
        if run["event"] == "pull_request":
            by_branch.setdefault(run["branch"], []).append(run)

    found = []
    for branch, branch_runs in by_branch.items():
        groups = [[branch_runs[0]]]
        for run in branch_runs[1:]:
            previous = groups[-1][-1]
            pushed_between = any(previous["number"] < push["number"] < run["number"] for push in main_pushes)
            # Runs more than three days apart with a main push in between are a new change.
            if split_on_gap and pushed_between and run["started"] - previous["started"] > timedelta(days=3):
                groups.append([run])
            else:
                groups[-1].append(run)
        for group in groups:
            merge = next((push for push in main_pushes if push["number"] > group[-1]["number"]), None)
            if merge:
                hours = (merge["finished"] - group[0]["started"]).total_seconds() / 3600
                found.append((branch, [run["number"] for run in group], merge["number"], hours))
    return found


def summary(hours):
    ordered = sorted(hours)
    return f"median {median(ordered):.1f} h, range {ordered[0]:.1f}-{ordered[-1]:.1f} h, n={len(ordered)}"


def main():
    rows = load_rows()
    runs = load_runs(rows)
    all_steps = max((run["steps"] for run in runs.values()), key=len)
    pull_requests = [run for run in runs.values() if run["event"] == "pull_request"]
    main_pushes = [run for run in runs.values() if run["event"] == "push"]
    first, last = min(r["started"] for r in runs.values()), max(r["started"] for r in runs.values())

    print("BASELINE CAPTURED FROM THE REPOSITORY AND ITS CI HISTORY")
    print(f"source: {RUN_TIMINGS.relative_to(REPO)} ({len(runs)} runs, {first:%Y-%m-%d} to {last:%Y-%m-%d})")
    print()

    print("1. LEAD TIME FOR CHANGES (proxy: first PR CI run -> merged-to-main CI run finished)")
    split = changes(runs, split_on_gap=True)
    for branch, pr_runs, merge_run, hours in split:
        print(f"   {branch:27} PR runs {str(pr_runs):17} -> main run {merge_run:2} {hours:6.1f} h")
    print(f"   primary (split branches reused after a merge): {summary([c[3] for c in split])}")
    print(f"   sensitivity (one change per branch):           {summary([c[3] for c in changes(runs, False)])}")
    merged = {c[2] for c in split}
    print(f"   main pushes with no PR run in the window: {[p['number'] for p in main_pushes if p['number'] not in merged]}")
    minutes = sorted(run["seconds"] / 60 for run in runs.values())
    print(f"   CI time per run: median {median(minutes):.1f} min, p90 {percentile(minutes, 0.9):.1f} min, "
          f"range {minutes[0]:.1f}-{minutes[-1]:.1f} min")
    step_medians = sorted(
        ((median([int(r["duration_seconds"]) for r in rows if r["step"] == step]), step) for step in all_steps),
        reverse=True)
    print("   slowest steps (median): " + ", ".join(f"{step} {secs / 60:.1f} min" for secs, step in step_medians[:3]))
    print()

    print("2. CHANGE FAILURE RATE (production releases followed by an incident)")
    for version, date, failed, evidence in RELEASES:
        print(f"   {version:7} {date:17} {'FAILED' if failed else 'ok':7} {evidence}")
    failures = sum(1 for release in RELEASES if release[2])
    low, high = wilson_interval(failures, len(RELEASES))
    print(f"   known releases: {failures}/{len(RELEASES)} = {failures / len(RELEASES):.0%} (Wilson 95% {low:.0%}-{high:.0%})")
    total = len(RELEASES) + len(UNSEEN_RELEASES)
    print(f"   if {' and '.join(UNSEEN_RELEASES)} also shipped cleanly: {failures}/{total} = {failures / total:.0%}")
    pr_failed = [run for run in pull_requests if run["conclusion"] != "success"]
    main_failed = [run for run in main_pushes if run["conclusion"] != "success"]
    print(f"   not CFR (caught before production): CI failed on {len(pr_failed)}/{len(pull_requests)} PR runs, "
          f"{len(main_failed)}/{len(main_pushes)} main pushes")
    for run in pr_failed:
        print(f"     run {run['number']} {run['branch']}: failed at '{failed_step(run, all_steps)}'")
    print()

    print("3. REVIEW TURNAROUND: not capturable today")
    print("   the CI export has PR runs but no review or approval timestamps; query in measurement-plan.md")


if __name__ == "__main__":
    main()
