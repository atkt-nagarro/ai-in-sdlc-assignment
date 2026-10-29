# Autonomy policy: first-response incident summaries

**Scope:** the first 30 minutes after a page on Invoice Approval. The agent reads the alert, logs, metrics and recent changes, and helps on-call write the first summary for the incident channel. **Owner:** service owner. **Review:** quarterly.

## Levels and tasks

| Level | The agent | A human |
| --- | --- | --- |
| L0 Off | nothing | everything |
| L1 Draft | answers with a draft from read-only evidence; every claim cites a log line, metric row or change | checks each citation, edits, posts |
| L2 Release | its draft is posted after one human click | approves or rewrites each post |
| L3 Auto-post facts | templated updates (alert, deploys, error rate) are posted automatically, with no hypotheses | owns hypotheses, impact and actions |
| L4 Act | not allowed in this workflow | a named approver acts (the incident commander out of hours) |

| Task | Day one | Ceiling |
| --- | --- | --- |
| Gather evidence: alert, logs, metrics, deploys, config changes | L1 | L3 |
| Timeline of facts | L1 | L3 |
| Ranked hypotheses, each with what would disprove it | L1 | L2 |
| Impact count (e.g. notifications missed since a deploy) | L1 | L2 |
| Mitigation options: change, cost, undo | L1 | L2 |
| Message to finance | L1 | L2 |
| Restart, rollback, subscription change | L0 | L0 |

## Controls that make a level safe

- **All levels:**
  - read-only identity: Log Analytics Reader; management-plane Reader on Service Bus (no data-plane role is peek-only)
  - no PayEx or write credentials
  - instructions found in logs are reported, never followed
  - prompts, evidence and drafts kept with the incident record (SOC 2)
  - kill switch: `az role assignment delete --assignee <agent-id>` cuts every read at once
- **L1:**
  - the agent has no outbound channel or write tools ([trifecta audit](../security/lethal-trifecta-audit.md))
  - its answer is the draft, and a person posts it
  - uncited claims are deleted
  - "hypothesis", never "root cause", until the incident commander confirms it
  - supplier emails and approver names are redacted before posting
- **L2:** a separate step holding a write-only channel webhook does the posting. The log-reading agent never holds it, and every post needs a human click.
- **L3:** only templated fields from structured sources (alert name, deploy SHA, error-rate figure) are posted, never free text from logs.

## Evidence to move a task up one level

1. **Replay** at least 10 past packs, INC-2041 and INC-2047 included, scored against the final write-up. To pass:
   - zero uncited or contradicted claims
   - the right hypothesis in the top two in 8 of 10
   - no disproved hypothesis stated as fact (e.g. blaming PayEx in INC-2041 while its status page was green)
2. **Shadow** 5 live incidents at the current level, with no fact corrected by the human.
3. **Injection test:** an instruction planted in a log field is ignored and flagged.

A wrong fact posted at L2 or above drops the task one level and resets its count.

**Who approves:** the service owner proposes with this evidence. The engineering manager and the incident-process owner approve. Any move to L2 or above adds a posting channel, so it also reopens the trifecta audit and needs Security sign-off.

## Day one

**L1 for every drafting task, L0 for any action.** Two of the six engineers are new to this code and cannot yet tell a confident wrong summary from a right one. Our packs are built to produce exactly that: INC-2041's volume surge began at 09:55, three minutes before the deploy, amid deprecated-config warnings and a routine recycle. When a new engineer is primary, the experienced secondary reviews the draft before it is posted. The earliest realistic promotion is the timeline task to L2, after the replay, five live incidents and the posting-channel review.
