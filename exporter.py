from __future__ import annotations
import csv
from pathlib import Path
from models import TrackCandidate

EXPORT_DIR = Path("data/exports")

def export_csv(candidates: list[TrackCandidate], filename: str) -> Path:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = EXPORT_DIR / filename
    fields = list(TrackCandidate("", "", "", "", "").to_dict().keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for item in candidates:
            writer.writerow(item.to_dict())
    return path
