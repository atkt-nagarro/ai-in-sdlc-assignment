# Demo video script (target 9 minutes)

Record with Teams (Meeting, Share screen, Record) or QuickTime (File, New Screen Recording), then export MP4. Upload to OneDrive or SharePoint with "anyone in the organisation can view", and paste the link into the README index.

**Before you start:**
- Terminal at the repository root, font size 16.
- VS Code with the Markdown preview open, so the Mermaid diagrams render.
- Run the test once to warm the build. If your machine only has the .NET 10 SDK, `export DOTNET_ROLL_FORWARD=Major`.

| Time | Show | Say (in your own words) |
| --- | --- | --- |
| 0:00–0:40 | README index | "Invoice Approval goes tier-2 in January, with PayEx and a 24x7 rotation. Here are the four things I own before go-live, and the evidence behind each." |
| 0:40–2:00 | `docs/architecture/as-built.md`: the container view, then the sequence diagram | "Every box and arrow cites a file and line. A script checks all 65." Run `python3 docs/architecture/check_citations.py`. Open `docs/agent-sessions/01-mermaid/`: "This is what the agent drew with the Mermaid MCP. Here is what it inferred, and here is what I corrected." Point at one correction. |
| 2:00–2:30 | `approval-path-walkthrough.txt` | "I ran the app to confirm the status codes: 200, 409 on a second approve, 404, 401. The route in the incident logs is a 404 in the real code, so `ops/` describes a system that doesn't exist yet." |
| 2:30–3:00 | `target-state.md` | "Green exists, dashed amber is planned: SQL, outbox, dispatcher, reconciliation, a shared session store." |
| 3:00–4:00 | Terminal | Run `dotnet test backend/InvoiceApp.sln --filter "Category=Architecture"` (green). Add `private static readonly HttpClient PayEx = new();` to `ApprovalService`, run it again (red, names `System.Net.Http`), then `git checkout backend/src/InvoiceApp.Domain/ApprovalService.cs`. "It compiles; only the test catches it." |
| 4:00–5:30 | `docs/adr/ADR-001-exactly-once-payex-submission.md` | "Exactly-once is at-least-once plus dedupe at PayEx, so I chose a transactional outbox, a stable key, and reconciliation as a check." Show the strongest objection and the 3 a.m. table. Then *Where the agent was wrong*: "It caved when I said I preferred option 3. It cited my own eval fixture as production history. It read random ID collisions as users retrying." |
| 5:30–6:15 | `docs/policy/autonomy-policy-incident-summaries.md` | "Day one is L1 for everything: private drafts, every claim cited, a human posts. Two engineers are new, and our incident packs are full of confounders." Show the promotion evidence. |
| 6:15–7:45 | `ops/evals/RESULTS.md` and one raw review in `runs/` | "Three runs of twelve cases. Opus caught 27 of 27 either way. With AGENTS.md it raised one false alarm and cost 31% more, so the change was no improvement. A blind second scorer agreed with my scoring on 107 of 108." Show the Haiku probe: "Even a 30-point gap gives p = 0.125 on twelve cases. The eval is too small and too easy to judge a prompt change." Mention the pre-registered answer key (commit before the first run). |
| 7:45–8:30 | `docs/security/lethal-trifecta-audit.md` | "All three legs are present. I removed external communication: no browser, no web, sandbox egress allowlist, read-only identity. A human posts." Show `oncall-agent-settings.json`. |
| 8:30–9:15 | `docs/metrics/measurement-plan.md` | Run `python3 docs/metrics/compute_baseline.py`. "Lead time proxy median 58 hours; change failure rate 2 of 5 releases. Review turnaround can't be measured yet: there are no PRs. Here's the query for day one." |
| 9:15–9:40 | `docs/ai-augmentation-log.md` | "This is where I used the agent, what I kept, and what I threw away." |

Keep each section to its slot. If you run long, shorten the ADR walkthrough, not the evidence.
