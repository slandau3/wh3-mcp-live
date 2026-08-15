"""Shared database loading utilities for WH3-Dump TSV files."""
from pathlib import Path
from config import WH3_DUMP_DIR


def load_tsv(path: Path) -> list[dict]:
    """Load a TSV file into a list of dicts, skipping comment lines."""
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    if len(lines) < 2:
        return []
    headers = lines[0].split("\t")
    rows = []
    for line in lines[1:]:
        if line.startswith("#"):
            continue
        vals = line.split("\t")
        row = {}
        for i, h in enumerate(headers):
            row[h] = vals[i] if i < len(vals) else ""
        rows.append(row)
    return rows
