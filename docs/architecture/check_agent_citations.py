"""Resolves every file:line the diagram agent cited in its answer and prints the cited line."""

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
ANSWER = REPO / "docs" / "agent-sessions" / "01-mermaid" / "final-answer.md"
CITATION = re.compile(r"`([\w./-]+\.(?:cs|js|html|json|ts|csproj))(?::([\d,\- ]+))?`")
SHORTHAND = {"Api/": "InvoiceApp.Api/", "Domain/": "InvoiceApp.Domain/"}


def resolve(path):
    for short, full in SHORTHAND.items():
        if path.startswith(short):
            path = full + path[len(short):]
    for base in (REPO, REPO / "backend" / "src", REPO / "backend" / "src" / "InvoiceApp.Api"):
        if (base / path).exists():
            return base / path
    # The agent often cites a bare file name; accept it only when it is unique in the repo.
    matches = [m for m in REPO.glob(f"**/{Path(path).name}") if not {"bin", "obj", "node_modules"} & set(m.parts)]
    return matches[0] if len(matches) == 1 else None


def main():
    total = failed = 0
    for row in ANSWER.read_text().splitlines():
        if not row.startswith("|") or "---" in row:
            continue
        cells = [cell.strip() for cell in row.strip("|").split("|")]
        if len(cells) < 2:
            continue
        for path, spec in CITATION.findall(cells[1]):
            total += 1
            file = resolve(path)
            lines = file.read_text().splitlines() if file else []
            numbers = [int(n) for n in re.findall(r"\d+", spec or "")]
            if not file or any(n > len(lines) for n in numbers):
                failed += 1
                print(f"FAIL {cells[0]} {path}:{spec}")
            elif numbers:
                print(f"ok   {cells[0]:5} {path}:{numbers[0]}  {lines[numbers[0] - 1].strip()[:80]}")
    print(f"{total - failed}/{total} agent citations resolve")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
