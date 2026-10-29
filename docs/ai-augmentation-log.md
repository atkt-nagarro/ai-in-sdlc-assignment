# AI augmentation log

The assignment asks for agent output, and evidence of how it was used. This page records where I used AI, what it produced, what I kept, and how I checked it. The raw sessions are kept verbatim next to it, so every quote here can be found.

## Tools

| Tool | Version | Used for |
| --- | --- | --- |
| Claude Code CLI | 2.1.306 | All agent sessions below, and as my working assistant for the whole assignment |
| `claude-opus-5-5` | through the corporate gateway | Diagram draft, ADR sparring, the review eval |
| `claude-haiku-4-5-20251001` | through the corporate gateway | Eval sensitivity probe only |
| Mermaid MCP (`mcp-mermaid`) | 0.4.1, local `svg`/`base64` output only | Drawing and rendering the diagrams |

I also used Claude Code as a working assistant throughout: reading the codebase and the incident packs, drafting these documents from my decisions, writing the scripts, and checking numbers. Two rules held for everything published here. Every number comes from a script in this repository or a cited file. Every agent claim I relied on was checked against the evidence, and the checks are described per task below.

## Per task

| Task | What the agent did | Raw output | Kept | Changed or rejected | How it was checked |
| --- | --- | --- | --- | --- | --- |
| 1. As-built diagrams | Drew the container view and the approval sequence with the Mermaid MCP, working from a clean checkout of the baseline commit, and listed 11 inferences | [01-mermaid/](agent-sessions/01-mermaid/) | Browser `sessionStorage`; the UI never showing who approved; unused `DiscountCalculator` and `GetByIds`; the refresh-failure and hidden "Session expired." behaviours | Removed the launch-profile URL it presented as the process address; split the controllers it merged, which hid different role rules; added the build boundary | All 107 of its citations resolve. Its inferences were tested against the running app ([walkthrough](architecture/approval-path-walkthrough.txt)). My corrected diagrams: 65/65 citations verified by [check_citations.py](architecture/check_citations.py). |
| 1. Target diagrams | Rendered and validated through the Mermaid MCP ([render_diagrams.py](architecture/render_diagrams.py)) | `docs/architecture/diagrams/*.svg` | All four render | Content follows ADR-001; nothing taken from the agent's own design | Visual check of each render |
| 1. Architecture test | Drafted the reflection test from the AGENTS.md rule | n/a | The rule and the BCL-only approach | Chose the Domain rule over the later "no controller calls PayEx" rule, because a type that does not exist yet would pass for the wrong reason | Red/green run captured in [architecture-test-run.txt](architecture/architecture-test-run.txt) |
| 2. ADR | Four-turn sparring session: trade-offs, a stated preference for option 3, the 3 a.m. failure, cost | [02-adr/](agent-sessions/02-adr/) (prompts, responses, JSON) | Payload snapshot per attempt; 4xx versus PayEx-wide classification; lease longer than the timeout; Always On; the in-memory `SessionStore` problem | Its option-3 concession; its use of an eval fixture as evidence; its "users retried" inference; its SOC 2 claim; two numbers. See *Where the agent was wrong* in [ADR-001](adr/ADR-001-exactly-once-payex-submission.md). | Log analysis of repeat IDs; arithmetic re-done; each quote checked against the JSON |
| 3. Autonomy policy | Helped draft the wording | n/a | Structure | Levels, ceilings and the day-one call are mine; the INC-2041 confounders are from my reading of the pack | Each cited time checked in `app-logs.txt` and `metrics.csv` |
| 4. Review eval | 72 isolated reviewer sessions (3 runs × 12 cases × 2 conditions), plus 36 probe sessions | [ops/evals/runs/](../ops/evals/runs/) | All outputs scored | Scored strictly against a key committed before the first run (`9e8defb`) | A blind second scorer (a separate agent, same key) re-scored all 108 reviews: 107/108 agree, Cohen's kappa 0.98. I adopted its call on the one disagreement ([second-scorer.json](../ops/evals/second-scorer.json)). |
| 5. Trifecta audit | Checked the Claude Code settings keys against the current docs | n/a | `permissions`, `sandbox.network.allowedDomains`, `disabledMcpjsonServers`, `blockReadsOutsideWorkingDirectories` | Nothing taken on trust: every key confirmed at code.claude.com | Profile JSON validated; evidence lines in the audit checked one by one |
| 5. Measurement plan | Wrote and ran the baseline script; checked the `az` and `gh` commands | [baseline-captured.txt](metrics/baseline-captured.txt) | Numbers as computed | Added 2.13.4 to the release list after rereading INC-2041 (CFR 2/5, not 2/4) | `compute_baseline.py` output matches the plan; `az` commands checked with `--help` |

## Cost of the agent sessions

| Sessions | Count | Cost |
| --- | --- | --- |
| Review eval, Opus, no context file | 36 | $2.01 |
| Review eval, Opus, AGENTS.md | 36 | $2.60 |
| Review eval, Haiku probe | 36 | $0.99 |
| ADR sparring (four turns) | 1 | $1.00 |
| Mermaid MCP diagram draft | 1 | $0.65, plus $0.78 for a discarded first run |

## Where the agent was wrong, across tasks

- **ADR:** it moved its recommendation when I stated a preference. It also cited my own eval fixture as production history, read random ID collisions in a log as user retries, overstated SOC 2, and got two numbers wrong ([details](adr/ADR-001-exactly-once-payex-submission.md#where-the-agent-was-wrong-or-useless)).
- **Diagrams:** nothing structurally wrong. It presented the launch-profile URL as the process address and merged controllers with different role rules. Its first run could see my draft diagrams, so I discarded it and re-ran on a clean checkout ([as-built.md](architecture/as-built.md#what-i-changed-in-its-draft-and-why)).
- **Eval:** with AGENTS.md as context, the reviewer became surer of an unverifiable claim (case-02 `_queries`) and raised one false alarm (run 6, case-06). The smaller model missed the duplicate-payment retry three times out of three.
- **Lesson:** an agent with repository access reads everything, fixtures included. Keep eval cases where agents doing other work cannot see them.
