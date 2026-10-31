# AI augmentation log

The assignment asks for agent output, and evidence of how it was used. This page records where I used AI, what it produced, what I kept, and how I checked it. The raw agent output is kept next to it, so every agent quote here can be found: the full stream of the diagram run, and the final JSON of each ADR turn and each eval review. Two sessions are not exported: my working-assistant session, noted below, and the second scorer's, whose prompt and a scan of what it opened are kept instead.

## Tools

| Tool | Version | Used for |
| --- | --- | --- |
| Claude Code CLI | 2.1.306 | All agent sessions below, and as my working assistant for the whole assignment |
| `claude-opus-5-5` | through the corporate gateway | Diagram draft, ADR sparring, the review eval, blind second scoring |
| `claude-haiku-4-5-20251001` | through the corporate gateway | Eval sensitivity probe only |
| Mermaid MCP (`mcp-mermaid`) | 0.4.1, local `svg` output (local PNG previews only for my visual checks) | Drawing, validating and rendering the diagrams |
| Playwright | 1.64.1, headless Chromium | Recording the demo video |
| ffmpeg | 8.1.2 | Cleaning up my recorded narration and fitting it to the video's captions |

I also used Claude Code as a working assistant throughout: reading the codebase and the incident packs, drafting these documents, writing the scripts, and checking numbers. That session is not exported; it stayed in my local Claude Code history. Measured numbers come from scripts in this repository or cited files, and estimates are labelled as such. The checks on agent output are described per task below.

## Per task

| Task | What the agent did | Raw output | Kept | Changed or rejected | How it was checked |
| --- | --- | --- | --- | --- | --- |
| 1. As-built diagrams | Drew the container view and the approval sequence with the Mermaid MCP, working from a clean checkout of the baseline commit, and listed 11 inferences | [01-mermaid/](agent-sessions/01-mermaid/) | Browser `sessionStorage`; the UI never showing who approved; unused `DiscountCalculator` and `GetByIds`; the refresh-failure and hidden "Session expired." behaviours | Its inference 11 was wrong (Kestrel also defaults to port 5000). Removed the listening address it drew as part of the process; split the controllers it merged, which hid different role rules; added the build boundary | [check_agent_citations.py](architecture/check_agent_citations.py): 107/107 of its citations resolve. After its run, inferences 1 to 5 and 11 were tested against the running app ([walkthrough](architecture/approval-path-walkthrough.txt)), 1 and 5 only in part; the rest were judged from the code. The corrected diagrams: 69/69 citations verified by [check_citations.py](architecture/check_citations.py). |
| 1. Target diagrams | Rendered and validated through the Mermaid MCP ([render_diagrams.py](architecture/render_diagrams.py)); the MCP caught a syntax error (a `;` inside a note) | `docs/architecture/diagrams/*.svg` | All four render | Content follows ADR-001, including the Key Vault idea adopted from the ADR agent | Visual check of each render; the final review also caught a `#` that truncated a note, now fixed |
| 1. Architecture test | Drafted the reflection test from the AGENTS.md rule | working-assistant session, not exported | The rule and the BCL-only approach | Chose the Domain rule over the later "no controller calls PayEx" rule, because a type that does not exist yet would pass for the wrong reason | Red/green run captured in [architecture-test-run.txt](architecture/architecture-test-run.txt) |
| 2. ADR | Four-turn sparring session: trade-offs, a stated preference for option 3, the 3 a.m. failure, cost | [02-adr/](agent-sessions/02-adr/) (prompts, responses, JSON) | One payload snapshot at approval, resent on every attempt; 4xx versus PayEx-wide classification; lease longer than the timeout; Always On; Key Vault for the key; the in-memory `SessionStore` problem; the starting shape of the options table, the 3 a.m. failure list and the build estimate | Its option-3 concession; its use of an eval fixture as evidence; its "clicking approve again" inference; its overclaimed INC-2047 alert; its misreading of today's concurrency; its SOC 2 claim; two numbers. See *Where the agent was wrong* in [ADR-001](adr/ADR-001-exactly-once-payex-submission.md). | Log analysis of repeat IDs; arithmetic re-done; each quote checked against the JSON |
| 3. Autonomy policy | Drafted the policy for the workflow I picked: levels, ceilings, controls, promotion evidence and the day-one call | working-assistant session, not exported | The levels, ceilings and day-one call | Trimmed to fit one A4 page | Each cited time checked in `app-logs.txt` and `metrics.csv`; page count measured on an A4 render |
| 4. Review eval | 72 isolated reviewer sessions (3 runs × 12 cases × 2 conditions), plus 36 probe sessions | [ops/evals/runs/](../ops/evals/runs/) | All outputs scored | Scored strictly against a key committed before the first run (`9e8defb`) | A blind second scorer (a separate Claude Code agent, same key plus notes on three cases, told not to open my scores) re-scored all 108 reviews: 107/108 agree, Cohen's kappa 0.98. Its case-03 note spelled out the mechanism the scoring used, so its agreement on the two Haiku case-03 misses is not independent. Its call on the one disagreement was adopted. Its prompt and a summary of what it opened are in [03-second-scorer](agent-sessions/03-second-scorer/), and its verdicts in [second-scorer.json](../ops/evals/second-scorer.json). |
| 5. Trifecta audit | Checked the Claude Code settings keys against the current docs | working-assistant session, not exported | `permissions`, `defaultMode: dontAsk`, `sandbox.network.allowedDomains` with `strictAllowlist`, `disabledMcpjsonServers`, `blockReadsOutsideWorkingDirectories` | The final review found that `allowedDomains` alone only pre-approves hosts. `strictAllowlist` and `dontAsk` were added after the sandboxing docs confirmed the behaviour | Profile JSON validated; evidence lines in the audit checked one by one |
| 5. Measurement plan | Wrote and ran the baseline script; checked the `az` and `gh` commands | [baseline-captured.txt](metrics/baseline-captured.txt) | Numbers as computed | Added 2.13.4 to the release list after rereading INC-2041 (CFR 2/5, not 2/4) | `compute_baseline.py` output matches the plan; `az` commands checked with `--help` |
| 8. Demo video | Produced the screen recording: a scripted Playwright run of the rendered deliverables and the running app, with the tests run live and captions on screen. Then cleaned up my recorded narration (noise reduction, levels) and fitted each line to its caption | [narration-script.md](demo/narration-script.md) | The video, 8 min 41 s, narrated in my own voice | Replaced the first, synthesised narration with my recording. Nothing in the picture was faked: the app is the real app, the git change is the real one-line change, and the test results match the captured runs. The terminal is a scripted panel that trims the dotnet output | Each line placed on its caption, a few slightly sped up to fit; frames checked against the narration; the end card says how the video was made |

## Cost of the agent sessions

| Sessions | Count | Cost |
| --- | --- | --- |
| Review eval, Opus, no context file | 36 | $2.01 |
| Review eval, Opus, AGENTS.md | 36 | $2.60 |
| Review eval, Haiku probe | 36 | $0.99 |
| ADR sparring (four turns) | 1 | $1.00 |
| Mermaid MCP diagram draft | 1 | $0.65, plus $0.78 for a discarded first run |
| Blind second scoring | 1 | not reported; the tool showed about 183k tokens, recorded only in the working-assistant session |
| Demo video | 1 | no API cost: the screen recording and the audio edit ran locally; the scripting was part of the working-assistant session |

## Where the agent was wrong, across tasks

- **ADR:** it moved its recommendation when the prompt stated a preference. It also cited my own eval fixture as production history, read ambiguous repeat IDs in a log as user retries, overstated SOC 2, and got two numbers wrong ([details](adr/ADR-001-exactly-once-payex-submission.md#where-the-agent-was-wrong-or-useless)).
- **Diagrams:** it drew nothing that does not exist. Its inference 11 was wrong: Kestrel listens on port 5000 by default, not only through the launch profile. It also drew the listening address as part of the process and merged controllers with different role rules. Its first run could see draft diagrams already in the working tree, so it was discarded and re-run on a clean checkout ([as-built.md](architecture/as-built.md#what-i-changed-in-its-draft-and-why)).
- **Eval:** with AGENTS.md as context, the reviewer became surer of an unverifiable claim (case-02 `_queries`) and raised one false alarm (run 6, case-06). The smaller model missed the duplicate-payment retry three times out of three.
- **Lesson:** an agent with repository access can read anything in it, fixtures included: the ADR agent cited an eval case as production history. Keep eval cases where agents doing other work cannot see them.
