"""Checks as-built.md citations: file exists, symbol within one line of the cited range."""

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
LOCATION = re.compile(r"^`([\w./-]+):(\d+)(?:-(\d+))?`$")
SLACK = 1  # lines of tolerance either side of the cited range


def citation_rows(doc):
    for line in doc.read_text().splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) >= 4 and LOCATION.match(cells[2]) and cells[3].startswith("`"):
            yield cells[0], cells[2], cells[3].strip("`")


def check(location, symbol):
    path, start, end = LOCATION.match(location).groups()
    file = REPO / path
    if not file.exists():
        return f"missing file {path}"
    lines = file.read_text().splitlines()
    first, last = int(start), int(end or start)
    if last > len(lines):
        return f"line {last} is past the end of {path} ({len(lines)} lines)"
    window = "\n".join(lines[max(0, first - 1 - SLACK):last + SLACK])
    return None if symbol in window else f"'{symbol}' not found near {path}:{start}"


def main():
    doc = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "as-built.md"
    rows = list(citation_rows(doc))
    failures = [(ref, location, problem) for ref, location, symbol in rows
                if (problem := check(location, symbol))]
    for ref, location, problem in failures:
        print(f"FAIL {ref} {location}: {problem}")
    print(f"{len(rows) - len(failures)}/{len(rows)} citations verified")
    sys.exit(1 if failures or not rows else 0)


if __name__ == "__main__":
    main()
