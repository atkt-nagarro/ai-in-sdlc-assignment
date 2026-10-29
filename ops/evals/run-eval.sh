#!/usr/bin/env bash
# Runs the review eval: every case in its own fresh, isolated Claude Code session.
#
#   ops/evals/run-eval.sh <condition> <run-number> [<run-number> ...]
#
# Conditions
#   baseline   the agent gets the review prompt and the diff, nothing else
#   agents-md  identical, except the repository's CLAUDE.md (which imports AGENTS.md)
#              is present as the project context file
#
# Each case runs in a new empty temporary directory with no MCP servers and no session
# persistence, so nothing carries over between cases or runs. The agent keeps its read-only
# file tools, but they only reach that empty directory: any read outside it needs a
# permission prompt, and --permission-prompts none denies those (denials are recorded in
# the result). Without tools the model writes imaginary tool calls into its answer. Results go to
# ops/evals/runs/<condition>/run-<n>/<case>.json (raw) and .md (the review text).
# Existing results are kept, so an interrupted run can simply be started again.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"

export MODEL="${MODEL:-claude-opus-5-5}"
export EFFORT="${EFFORT:-high}"
PARALLEL="${PARALLEL:-4}"

# Verbatim from ops/evals/README.md.
export REVIEW_PROMPT='Review this diff for defects. For each finding give the file, the line, what goes wrong, and how confident you are. If you find nothing, say so explicitly rather than listing general observations.'

condition="${1:?condition: baseline or agents-md}"
shift
[[ "$condition" == "baseline" || "$condition" == "agents-md" ]] || { echo "unknown condition: $condition" >&2; exit 2; }
[[ $# -gt 0 ]] || { echo "give at least one run number" >&2; exit 2; }
export condition HERE REPO

review_case() {
  local run="$1" case_file="$2"
  local case_id out_dir workdir attempt
  case_id="$(basename "$case_file" .diff)"
  out_dir="$HERE/runs/$condition/run-$run"
  mkdir -p "$out_dir"

  if python3 -I -c 'import json,sys; d=json.load(open(sys.argv[1])); sys.exit(0 if not d.get("is_error") and d.get("result") else 1)' "$out_dir/$case_id.json" 2>/dev/null; then
    echo "skip   $condition run-$run $case_id (already done)"
    return 0
  fi

  for attempt in 1 2 3; do
    workdir="$(mktemp -d)"
    if [[ "$condition" == "agents-md" ]]; then
      cp "$REPO/CLAUDE.md" "$REPO/AGENTS.md" "$workdir/"
    fi

    printf '%s\n\n%s\n' "$REVIEW_PROMPT" "$(cat "$case_file")" > "$workdir/.message"
    (
      cd "$workdir"
      env -u CLAUDECODE -u CLAUDE_CODE_ENTRYPOINT claude -p \
        --model "$MODEL" --effort "$EFFORT" \
        --tools "Read,Grep,Glob" --permission-prompts none \
        --strict-mcp-config --mcp-config '{"mcpServers":{}}' \
        --setting-sources user,project --no-session-persistence \
        --output-format json < .message > result.json 2> stderr.txt
    ) || true

    if python3 -I -c 'import json,sys; d=json.load(open(sys.argv[1])); sys.exit(0 if not d.get("is_error") and d.get("result") else 1)' "$workdir/result.json" 2>/dev/null; then
      cp "$workdir/result.json" "$out_dir/$case_id.json"
      python3 -I - "$out_dir/$case_id.json" "$out_dir/$case_id.md" "$case_id" "$condition" "$run" "$attempt" <<'PY'
import json, sys
src, dst, case_id, condition, run, attempt = sys.argv[1:]
d = json.load(open(src))
models = ", ".join(d.get("modelUsage", {}).keys())
with open(dst, "w") as f:
    f.write(f"# {case_id} / {condition} / run {run}\n\n")
    f.write(f"- model: {models}\n- attempt: {attempt}\n")
    f.write(f"- duration_ms: {d.get('duration_ms')}\n- cost_usd: {d.get('total_cost_usd')}\n")
    f.write(f"- tool calls denied: {len(d.get('permission_denials') or [])}\n\n---\n\n")
    f.write(d["result"].rstrip() + "\n")
PY
      echo "done   $condition run-$run $case_id (attempt $attempt)"
      echo "$(date -u +%FT%TZ) $condition run-$run $case_id ok attempt=$attempt" >> "$HERE/runs/attempts.log"
      rm -rf "$workdir"
      return 0
    fi

    echo "$(date -u +%FT%TZ) $condition run-$run $case_id failed attempt=$attempt: $(head -c 300 "$workdir/stderr.txt" | tr '\n' ' ')" >> "$HERE/runs/attempts.log"
    rm -rf "$workdir"
    sleep $((attempt * 20))
  done

  echo "FAILED $condition run-$run $case_id after 3 attempts" >&2
  return 1
}
export -f review_case

mkdir -p "$HERE/runs"
{
  echo "started: $(date -u +%FT%TZ)"
  echo "condition: $condition  runs: $*  model: $MODEL  effort: $EFFORT"
  echo "claude: $(claude --version 2>/dev/null)"
} >> "$HERE/runs/manifest.txt"

for run in "$@"; do
  for case_file in "$HERE"/cases/case-*.diff; do
    printf '%s %s\n' "$run" "$case_file"
  done
done | xargs -P "$PARALLEL" -n 2 bash -c 'review_case "$0" "$1"'

echo "finished: $(date -u +%FT%TZ) condition=$condition runs=$*" >> "$HERE/runs/manifest.txt"
