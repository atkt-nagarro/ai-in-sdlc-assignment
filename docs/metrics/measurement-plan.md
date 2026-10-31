# Measurement plan: the delivery baseline before the rotation starts

Three numbers show whether delivery gets better or worse once the rotation and its agents start: lead time for changes, change failure rate and review turnaround. Without a "before", any "after" is a story.

## Captured today

From [`compute_baseline.py`](compute_baseline.py), output saved in [`baseline-captured.txt`](baseline-captured.txt):

```
python3 docs/metrics/compute_baseline.py
```

| Metric | Value | Source | Caveat |
| --- | --- | --- | --- |
| **Lead time for changes** (proxy) | **Median 57.9 h** (n=6, range 5.5–99.9 h). 67.5 h if each branch counts as one change. | `ops/pipeline/run-timings.csv` | Measures first PR CI run → merged-to-main CI finished, not commit → production. CI records no deploys, and the PR-to-merge mapping is inferred from timing. |
| CI time inside that | Median 31.3 min, p90 34.5 min | same | Static analysis alone is 8.0 min |
| **Change failure rate** | **2/5 = 40%** (Wilson 95% 12–77%). 29% if 2.14.1 and 2.14.2 also shipped cleanly, 57% if both failed. | Releases in `INC-2041/README.md` and `INC-2047/recent-changes.md`; failures INC-2041 (2.14.0) and INC-2047 (2.15.1) | Tiny sample. The release list is rebuilt from incident packs. |
| Not change failure rate | CI failed on 2/12 PR runs and 0/8 pushes to main | `run-timings.csv` | These failures were caught before production, so they don't count |
| Review turnaround | **Not capturable** | n/a | The CI export has PR-triggered runs but no review, approval or ready-for-review timestamps, and the upstream repository has no pull requests |

The upstream repository gives one more figure, though not a lead time. Commit `0616158` was authored at 2026-10-12T10:20:35Z, and CI went green on main at 2026-10-14T09:41:35Z: **47.4 h**, n=1. The repository itself was created only minutes before that CI run, so nearly all of the 47.4 h passed before it existed. The commands and their output are saved in [`upstream-lead-time.txt`](upstream-lead-time.txt):

```
gh api repos/NITIN1670/ai-in-sdlc-assignment/commits/0616158 --jq '[.sha, .commit.author.date] | @tsv'
gh api 'repos/NITIN1670/ai-in-sdlc-assignment/actions/runs?branch=main&head_sha=0616158bdd735dfdf87c88ae381a26902dacfdfe' \
  --jq '.workflow_runs[] | [.id, .event, .conclusion, .run_started_at, .updated_at] | @tsv'
```

## The live baseline: definition, source and query

Names in angle brackets are identifiers this repository does not contain yet: `<org>` is the team's GitHub organisation, and `<app>`, `<rg>` and `<app-resource-id>` are the production App Service, its resource group and its resource ID.

### 1. Lead time for changes

**Definition:** first commit authored on a PR → that change running in production. Report median and p90 per week.

**PR side:**
```
gh pr list --repo <org>/invoice-approval --state merged --base main --search 'merged:>=<week-start>' --limit 49 \
  --json number,mergedAt,mergeCommit,commits \
  --jq '.[] | [.number, .commits[0].authoredDate, .mergedAt, .mergeCommit.oid] | @tsv'
```
Asking for `commits` caps one call at 49 pull requests (GitHub's GraphQL node limit), so run it one week at a time, with `<week-start>` as that Monday.

**Deploy side.** The pipeline has no deploy job, so GitHub records no deployments. First add one with `environment: production`, then:
```
gh api 'repos/<org>/invoice-approval/deployments?environment=production&per_page=100' \
  --jq '.[] | [.sha, .created_at] | @tsv'
```
Until that exists, use App Service's own record:
```
az webapp log deployment list --name <app> --resource-group <rg>
az monitor activity-log list --resource-id <app-resource-id> --offset 30d --max-events 5000 \
  --query "[?contains(operationName.value, 'slotsswap')].{time:eventTimestamp, status:status.value}"
```
`--max-events` defaults to 50 and applies before `--query`; without it, older swaps vanish without a warning. Swap events carry no SHA, so take it from the app's `[Deploy] ... commit=` log line (`publisher-logs.txt`).

A change's lead time is the first deploy whose SHA contains its merge commit (`git merge-base --is-ancestor`), minus the PR's first authored commit.

### 2. Change failure rate

**Definition (DORA):** production deployments that needed remediation (a rollback, a hotfix, or a Sev 1–2 incident linked to the release), divided by all production deployments in the period.

**Source:** the deployment list above, joined to incidents on a new mandatory **"caused by release"** field in the incident template. Today nothing records that link; it has to be rebuilt from timing and the incident evidence.

If incidents are GitHub issues labelled `incident`, with the release in the body:
```
gh issue list --repo <org>/invoice-approval --label incident --state all --limit 200 \
  --json number,createdAt,title,body --jq '.[] | [.number, .createdAt, .title, .body] | @tsv'
```
A deployment counts as **failed** when any of these hold:
- an incident names its release
- the next production deployment of a different SHA rolls it back, i.e. deploys an ancestor of it (`git merge-base --is-ancestor <new> <old>`, with `<new>` not equal to `<old>`)
- a PR from a `hotfix/*` branch reaches production within 7 days

CFR = failed deployments ÷ all production deployments, weekly and rolling 90 days.

### 3. Review turnaround

**Definition:** PR ready for review → first review by someone other than the author, and → approval. Median and p90 per week; bots and drafts excluded.

```
gh api graphql -f q='repo:<org>/invoice-approval is:pr is:merged merged:>=2026-12-01' -f query='
query($q: String!) {
  search(query: $q, type: ISSUE, first: 100) {
    nodes { ... on PullRequest {
      number createdAt author { login }
      timelineItems(itemTypes: [READY_FOR_REVIEW_EVENT], first: 1) { nodes { ... on ReadyForReviewEvent { createdAt } } }
      reviews(first: 20) { nodes { author { __typename login } submittedAt state } }
    } }
  }
}'
```
Turnaround = the first `submittedAt` from a reviewer who is not the author and whose `author.__typename` is not `Bot`, minus the ready-for-review time (or `createdAt` if the PR never was a draft).

## Cadence and ownership

- Weekly, starting two weeks before the first rotation. The same scripts each time, with the output committed under `docs/metrics/`.
- The service owner owns it, and it gets reviewed at each rotation retro.
- Report median and p90 with n, never a mean: one slow change drags a mean a long way.

## Fix before trusting the numbers

- **Deploys do not appear to wait for CI.** Release 2.15.1 was deployed at 08:41:33Z (`publisher-logs.txt`), 23 minutes before the next push-to-main CI run started at 09:05Z (run 12). The CI export has no SHAs, so which run built it is inferred. Gate deploys on green main CI and record the SHA.
- **Releases and merges don't line up.** 2.15.0 (supplier contacts) is dated 21 January, but the next push-to-main run after that PR was on 22 January.
- **Pushes without PRs.** Main runs 9, 13 and 20 have no PR run in the window. Require PRs, or review turnaround undercounts.
- **An empty step.** The pipeline spends a median 2.4 minutes on `--filter Category=Integration`, and the repository has no integration tests.
