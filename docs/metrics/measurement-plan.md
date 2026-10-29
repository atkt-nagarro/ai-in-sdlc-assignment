# Measurement plan: the delivery baseline before the rotation starts

Three numbers tell us whether the rotation, and the agents we add to it, make delivery better or worse: lead time for changes, change failure rate and review turnaround. Without a "before", any "after" is a story.

## Captured today

From [`compute_baseline.py`](compute_baseline.py), output saved in [`baseline-captured.txt`](baseline-captured.txt):

```
python3 docs/metrics/compute_baseline.py
```

| Metric | Value | Source | Caveat |
| --- | --- | --- | --- |
| **Lead time for changes** (proxy) | **Median 57.9 h** (n=6, range 5.5–99.9 h). 67.5 h if each branch counts as one change. | `ops/pipeline/run-timings.csv` | Measures first PR CI run → merged-to-main CI finished, not commit → production. CI records no deploys, and the PR-to-merge mapping is inferred from timing. |
| CI time inside that | Median 31.3 min, p90 34.5 min | same | Static analysis alone is 8.0 min |
| **Change failure rate** | **2/5 = 40%** (Wilson 95% 12–77%). 29% if 2.14.1 and 2.14.2 also shipped cleanly. | Releases in `INC-2041/README.md` and `INC-2047/recent-changes.md`; failures INC-2041 (2.14.0) and INC-2047 (2.15.1) | Tiny sample. The release list is rebuilt from incident packs. |
| Not change failure rate | CI failed on 2/12 PR runs and 0/8 pushes to main | `run-timings.csv` | These failures were caught before production, so they don't count |
| Review turnaround | **Not capturable** | n/a | There are no pull request or review events in the repository or the CI export |

The upstream repository adds one data point. Commit `0616158` was authored at 2026-10-12T10:20:35Z, and CI went green on main at 2026-10-14T09:41:35Z: **47.4 h**, n=1. It came from:

```
gh api repos/NITIN1670/ai-in-sdlc-assignment/commits --jq '.[0].commit.author.date'
gh api repos/NITIN1670/ai-in-sdlc-assignment/actions/runs --jq '.workflow_runs[0].updated_at'
```

## The live baseline: definition, source and query

### 1. Lead time for changes

**Definition:** first commit authored on a PR → that change running in production. Report median and p90 per week.

**PR side:**
```
gh pr list --repo <org>/invoice-approval --state merged --base main --limit 200 \
  --json number,mergedAt,mergeCommit,commits \
  --jq '.[] | [.number, .commits[0].authoredDate, .mergedAt, .mergeCommit.oid] | @tsv'
```

**Deploy side.** The pipeline has no deploy job, so GitHub records no deployments. First add one with `environment: production`, then:
```
gh api 'repos/<org>/invoice-approval/deployments?environment=production&per_page=100' \
  --jq '.[] | [.sha, .created_at] | @tsv'
```
Until that exists, use App Service's own record:
```
az webapp log deployment list --name <app> --resource-group <rg>
az monitor activity-log list --resource-id <app-resource-id> --offset 30d \
  --query "[?contains(operationName.value, 'slotsswap')].{time:eventTimestamp, status:status.value}"
```
A change's lead time is the first deploy whose SHA contains its merge commit (`git merge-base --is-ancestor`), minus the PR's first authored commit.

### 2. Change failure rate

**Definition (DORA):** production deployments that needed remediation (a rollback, a hotfix, or a Sev 1–2 incident linked to the release), divided by all production deployments in the period.

**Source:** the deployment list above, joined to incidents on a new mandatory **"caused by release"** field in the incident template. Today that link can only be inferred from timing.

### 3. Review turnaround

**Definition:** PR ready for review → first review by someone other than the author, and → approval. Median and p90 per week; bots and drafts excluded.

```
gh api graphql -f q='repo:<org>/invoice-approval is:pr is:merged merged:>=2026-12-01' -f query='
query($q: String!) {
  search(query: $q, type: ISSUE, first: 100) {
    nodes { ... on PullRequest {
      number createdAt author { login }
      timelineItems(itemTypes: [READY_FOR_REVIEW_EVENT], first: 1) { nodes { ... on ReadyForReviewEvent { createdAt } } }
      reviews(first: 20) { nodes { author { login } submittedAt state } }
    } }
  }
}'
```
Turnaround = the first `submittedAt` from a non-author, non-bot reviewer, minus the ready-for-review time (or `createdAt` if the PR never was a draft).

## Cadence and ownership

- Weekly, starting two weeks before the first rotation. The same scripts each time, with the output committed under `docs/metrics/`.
- The service owner owns it, and it gets reviewed at each rotation retro.
- Report median and p90 with n, never a mean. These distributions are skewed (5.5 h to 99.9 h above).

## Fix before trusting the numbers

- **Deploys are not tied to CI.** Release 2.15.1 was deployed at 08:41:33Z (`publisher-logs.txt`), before the push-to-main CI run started at 09:05Z (run 12). Gate deploys on green main CI and record the SHA.
- **Releases and merges don't line up.** 2.15.0 (supplier contacts) is dated 21 January, but the next push-to-main run after that PR was on 22 January.
- **Pushes without PRs.** Main runs 9, 13 and 20 have no PR run in the window. Require PRs, or review turnaround undercounts.
- **An empty step.** The pipeline spends a median 2.4 minutes on `--filter Category=Integration`, and the repository has no integration tests.
