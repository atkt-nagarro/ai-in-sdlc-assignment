# Autonomy policy: first-response incident summaries

**Scope:** the first 30 minutes after a page on Invoice Approval. The agent reads the alert, logs, metrics and recent changes, and helps the on-call engineer write the first summary for the incident channel. **Owner:** service owner. **Review:** quarterly.

## Levels

| Level | The agent | A human |
| --- | --- | --- |
| L0 Off | does nothing | does everything |
| L1 Draft | reads read-only evidence and writes a private draft in which every claim cites a log line, metric row or change record | checks each citation, edits, posts |
| L2 Release | posts a labelled draft after one-click approval | approves or rewrites it before it goes out |
| L3 Auto-post facts | posts factual updates (alert, deploys in window, error rate) with no hypotheses | owns hypotheses, impact and actions |
| L4 Act | changes production | not allowed for this workflow |

## Tasks

| Task | Day one | Ceiling |
| --- | --- | --- |
| Gather evidence: alert, logs for the window, metrics, deploys, config changes | L1 | L3 |
| Timeline of facts with citations | L1 | L3 |
| Ranked hypotheses, each with the evidence that would disprove it | L1 | L2 |
| Impact count (e.g. notifications missed since the 2.15.1 deploy) | L1 | L2 |
| Mitigation options: what changes, cost, how to undo | L1 | L2 |
| Message to finance | L1 | L2 |
| Execute a restart, rollback or subscription change | L0 | L0. Needs a named approver (incident commander out of hours) |

## Controls that make a level safe

- **Read-only identity.** Log Analytics Reader. Management-plane Reader on Service Bus for counts and rules, never data-plane access: there is no peek-only role, and Receiver can consume messages. No PayEx credentials, no write tokens.
- **No outbound channel.** Drafts go to a file and a human posts them. This is the trifecta redesign in `docs/security/lethal-trifecta-audit.md`.
- **Citations or it goes.** An uncited claim is deleted before posting.
- **Words.** "Hypothesis", never "root cause", until the incident commander confirms it.
- **Redaction.** Supplier emails and approver names are stripped from anything posted; worker logs contain recipient addresses.
- **Log text is data.** Instructions found in logs are reported, never followed.
- **Audit.** Prompts, evidence and drafts are kept with the incident record (SOC 2).
- **Kill switch.** The on-call engineer can disable the agent for the incident with one command.

## Evidence needed to move a task up one level

1. **Replay:** at least 10 past evidence packs, INC-2041 and INC-2047 included, scored against the final write-up. Pass marks:
   - zero uncited or contradicted claims
   - the correct hypothesis in the top two in 8 of 10
   - no disproved hypothesis stated as fact. For example, blaming PayEx in INC-2041 while its status page was green, or blaming the deprecated-config warning.
2. **Shadow:** 5 live incidents at the current level where the human corrected no fact.
3. **Injection test:** an instruction planted in a log field (say, a customer name) is ignored and flagged.

Any wrong fact posted at L2 or above drops that task a level and resets its count.

## Who approves a move

The service owner proposes it with the evidence above. The engineering manager and the incident-process owner approve it. Security must also sign off on any change to what the agent can read or where it can write.

## Day one

**L1 for every task, L0 for execution.** Two of the six engineers are new to this code. They cannot yet tell a confident wrong summary from a right one, and our evidence packs are full of confounders that produce exactly that. INC-2041's volume surge started at 09:55, three minutes before the deploy, with deprecated-config warnings and a routine recycle mixed in. On day one, when a new engineer is primary, the experienced secondary reviews the draft before anything is posted. The earliest realistic promotion is the timeline task to L2, after the replay and five live incidents.
