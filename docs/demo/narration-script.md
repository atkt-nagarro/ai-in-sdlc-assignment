# Demo narration

The narration of [demo.mp4](demo.mp4), scene by scene. The same words appear as captions in the video.

## Introduction

This is my submission for the AI in SDLC home assignment.

The Invoice Approval service goes tier-2 in January, with a 24x7 rotation, a published SLO, and payments through an external provider, PayEx.

Before that happens, a senior engineer should own four things: a decision record, an autonomy policy, a working evaluation and an honest measurement plan.

This index maps all nine hand-in items to their files.

Every measured number comes from a script or a cited file, and where I used an AI agent, I show what it produced and where it was wrong.

## Task 1 · As-built diagrams

Task one is the as-built picture of the code as it stands today.

There is a browser page, one ASP.NET Core 8 process, and an in-memory repository and session store. Nothing else.

No database, no PayEx and no Service Bus: those exist only in the ops folder, which describes the planned deployment.

Every box and arrow cites a file and a line, and a script checks all 69 citations.

Here is that check, run live.

The sequence diagram follows one approval from the click to the stored decision, with the 401, 403, 404 and 409 branches.

The first draft came from Claude Code using the Mermaid MCP, on a clean checkout of the baseline commit.

All 107 of its citations resolve, and it listed eleven things it had inferred rather than read.

I checked each inference against the running app. One was wrong: it said port 5000 only comes from the launch profile, but Kestrel listens there by default.

I also split the controllers it had merged, because they carry different role rules.

## Task 1 · The running app

To test those claims, I ran the app and drove the approval path.

Signed in as the approver, the Approvals tab lists the pending invoices.

I approve invoice 1001, and it leaves the pending list.

The full walkthrough is captured with curl: a second approval returns 409, an unknown invoice 404, and a call without a token 401.

The route the incident logs use returns 404 here, which confirms that the ops folder describes a system that does not exist yet.

## Task 1 · Target state

The target state shows what persistence and PayEx add.

Green exists in the code today. Dashed amber is not built yet.

Approvals go through the repository interface to a planned SQL repository in the API layer, so the domain stays free of storage code.

A dispatcher sends payments from an outbox, Key Vault holds the PayEx key, and Service Bus, provisioned but unused by this code, carries notifications only.

## Task 1 · Architecture test

That boundary is the rule my architecture test enforces: the domain project may use the base class library, and nothing web, HTTP or storage.

Here it is, passing.

Now I add one line to ApprovalService: a static HttpClient. It still compiles, because implicit usings already import System.Net.Http.

The test fails, and names the assembly that broke the rule.

I revert the change, and it passes again. CI runs this rule on every build.

## Task 2 · Exactly-once decision record

Task two is the decision record on getting each approved invoice to PayEx exactly once.

Exactly-once to an external system is really at-least-once delivery, plus duplicate suppression at the receiver.

So I chose a transactional outbox in Azure SQL: the approval, an audit row and a payment submission row commit in one transaction.

A dispatcher sends each submission with a stable idempotency key, and a timeout becomes Unknown. It is never resent blind.

Daily reconciliation is the safety net, not the mechanism.

The strongest objection is that a background worker can stall silently, and with two new engineers on the rotation, that is a real risk.

My answer is to alert on the age of the oldest unpaid approval, not on whether the process is alive.

This table shows how the design fails at 3 a.m. on the last working day, with detection and mitigation for each case.

I stressed the agent three ways: a stated preference, the 3 a.m. failure, and the cost to build and run.

Its most revealing answer was a failure: when I said I preferred nightly reconciliation, it moved its recommendation without any new evidence.

It also cited my own eval fixture as production history, and read random ID collisions in a log as users retrying.

## Task 3 · Autonomy policy

Task three is a one-page autonomy policy, for first-response incident summaries.

It defines five levels, from off to acting, and gives every task a level for day one and a ceiling.

Each level has its own controls. Moving a task up needs replayed incidents, live shadowing and an injection test, and any move above level one reopens the security review.

On day one, the team runs level one for every drafting task and level zero for any action, because two of the six engineers cannot yet tell a confident wrong summary from a right one.

## Task 4 · Review evaluation

Task four is the review evaluation.

Each of the twelve cases, the ten fixed ones plus my two, ran three times in a fresh, isolated session, against the one review prompt.

I committed the answer key before the first run, so the scoring could not drift towards the results.

Opus caught 27 out of 27 defects, with no false alarms.

Then I changed exactly one thing: the context file, by adding AGENTS.md.

It still caught every defect, but it raised one false alarm and cost about 30% more, so the change was not an improvement.

How confident am I? Not very: this set is too small, and too easy for a strong model.

As a check, a smaller model caught only 70%, yet even that 30-point gap gives p = 0.125 over twelve cases.

A second, blind AI scorer agreed with 107 of my 108 verdicts.

## Task 5 · Lethal trifecta audit

Task five starts with a lethal trifecta audit of the agent setup.

All three legs are present: production logs hold private data, user text in those logs is untrusted content, and a browser and a shell can talk to the outside world.

I removed external communication for the on-call profile: no browser or web tools, a strict sandbox allowlist that refuses rather than prompts, and a read-only identity.

The agent writes a draft, and a person posts it.

## Task 5 · Measurement plan

The measurement plan names the exact source and query for lead time, change failure rate and review turnaround.

Two of them can be captured today, from the repository and its CI history.

The lead time proxy has a median of about 58 hours, and two of five releases failed: a change failure rate of 40%, with a very wide interval.

Review turnaround cannot be measured yet, because nothing records reviews, so the plan gives the query to run once pull requests flow.

## AI augmentation log

Finally, the AI augmentation log records every agent session: what it produced, what I kept, what I rejected, and how I checked it.

The raw transcripts sit next to it, so every quote can be checked.

Thank you for watching.
