# Autonomy policy: first-response incident summaries

**Scope:** the first 30 minutes after a page: the agent reads alerts, logs, metrics and recent changes and helps on-call write the first summary. **Owner:** service owner, reviewed quarterly.

**L0 Off:** a human does everything. **L1 Draft:** the agent drafts from read-only evidence and cites a log line, metric row or change for every claim; a human checks each citation, edits and posts. **L2 Release:** the draft is posted after one human click. **L3 Auto-post facts:** templated updates (alert, deploys, error rate) are posted with no hypotheses. **L4 Act:** not allowed; a named approver acts.

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

- **All levels:** read-only identity (Log Analytics Reader; management-plane Reader on Service Bus, as no data-plane role is peek-only); no PayEx or write credentials; instructions found in logs are reported, never followed; prompts, evidence and drafts kept with the incident record (SOC 2); kill switch: one `az role assignment delete` cuts every read.
- **L1:** no outbound channel or write tools ([trifecta audit](../security/lethal-trifecta-audit.md)); uncited claims deleted; "hypothesis", never "root cause", until the incident commander confirms; personal data redacted.
- **L2:** only a separate step holds the write-only channel webhook, and it posts after the click.
- **L3:** only templated fields from structured sources are posted, never free text from logs.

## Evidence to move a task up one level

1. **Replay** 10 past packs, INC-2041 and INC-2047 included, against the final write-up: zero uncited or contradicted claims, the right hypothesis in the top two in 8 of 10, no disproved hypothesis stated as fact (e.g. blaming PayEx in INC-2041 while its status page was green).
2. **Shadow** 5 live incidents at the current level with no fact corrected.
3. **Injection test:** an instruction planted in a log field is ignored and flagged.

A wrong fact posted at L2 or above drops the task a level and resets its count. **Who approves:** the service owner proposes; the engineering manager and incident-process owner approve. A move to L2 or above adds a posting channel, so it reopens the trifecta audit and needs Security sign-off.

## Day one

**L1 for every drafting task, L0 for any action.** Two of the six engineers are new to this code and cannot yet tell a confident wrong summary from a right one, which is what our packs invite: INC-2041's surge began at 09:55, three minutes before the deploy, amid deprecated-config warnings and a routine recycle. A new primary has every draft reviewed by the experienced secondary.
