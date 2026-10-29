# Autonomy policy: first-response incident summaries

**Scope:** the first 30 minutes after a page on Invoice Approval. The agent reads the alert, logs, metrics and recent changes, and helps on-call write the first summary for the incident channel. **Owner:** service owner. **Review:** quarterly.

## Levels and tasks

| Level | The agent | A human |
| --- | --- | --- |
| L0 Off | nothing | everything |
| L1 Draft | writes a private draft from read-only evidence; every claim cites a log line, metric row or change | checks each citation, edits, posts |
| L2 Release | posts a labelled draft after one-click approval | approves or rewrites |
| L3 Auto-post facts | posts factual updates (alert, deploys, error rate) with no hypotheses | owns hypotheses, impact and actions |
| L4 Act | changes production | never, for this workflow |

| Task | Day one | Ceiling |
| --- | --- | --- |
| Gather evidence: alert, logs, metrics, deploys, config changes | L1 | L3 |
| Timeline of facts | L1 | L3 |
| Ranked hypotheses, each with what would disprove it | L1 | L2 |
| Impact count (e.g. notifications missed since a deploy) | L1 | L2 |
| Mitigation options: change, cost, undo | L1 | L2 |
| Message to finance | L1 | L2 |
| Restart, rollback, subscription change | L0 | L0. A named approver acts (the incident commander out of hours). |

## Controls that make a level safe

- **Read-only identity:** Log Analytics Reader, plus management-plane Reader on Service Bus. No data-plane role, because none is peek-only and Receiver consumes messages. No PayEx or write credentials.
- **No outbound channel:** drafts go to a file and a person posts them ([trifecta audit](../security/lethal-trifecta-audit.md)).
- **Uncited claims are deleted.** Say "hypothesis", never "root cause", until the incident commander confirms it.
- **Supplier emails and approver names are redacted** from anything posted.
- **Instructions found in logs are reported, never followed.**
- **Prompts, evidence and drafts are kept** with the incident record (SOC 2). On-call can disable the agent with one command.

## Evidence to move a task up one level

1. **Replay** at least 10 past packs, INC-2041 and INC-2047 included, scored against the final write-up. To pass:
   - zero uncited or contradicted claims
   - the right hypothesis in the top two in 8 of 10
   - no disproved hypothesis stated as fact (e.g. blaming PayEx in INC-2041 while its status page was green)
2. **Shadow** 5 live incidents at the current level, with no fact corrected by the human.
3. **Injection test:** an instruction planted in a log field is ignored and flagged.

A wrong fact posted at L2 or above drops the task one level and resets its count.

**Who approves:** the service owner proposes with this evidence. The engineering manager and the incident-process owner approve. Security also signs off on any change to what the agent reads or where it writes.

## Day one

**L1 for every task, L0 for execution.** Two of the six engineers are new to this code and cannot yet tell a confident wrong summary from a right one. Our packs are built to produce exactly that: INC-2041's volume surge began at 09:55, three minutes before the deploy, amid deprecated-config warnings and a routine recycle. When a new engineer is primary, the experienced secondary reviews the draft before it is posted. The earliest realistic promotion is the timeline task to L2, after the replay and five live incidents.
