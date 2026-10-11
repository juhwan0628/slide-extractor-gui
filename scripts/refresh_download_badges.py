"""Refresh public badge endpoints and record observation times (not download times)."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile
import time

from download_stats import fetch_releases, installer_counts, write_badges

def refresh(repository, output, history):
    for attempt in range(3):
        try:
            counts = installer_counts(fetch_releases(repository, os.environ.get("GH_TOKEN", "")))
            break
        except Exception:
            if attempt == 2:
                raise
            time.sleep(5)
    observed = {"observed_at": datetime.now(timezone.utc).isoformat(), **counts}
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output) as staging:
        stage = Path(staging)
        write_badges(counts, stage)
        (stage / "status.json").write_text(json.dumps(observed) + "\n")
        for path in stage.iterdir():
            path.chmod(0o644)
            os.replace(path, output / path.name)
    history.parent.mkdir(parents=True, exist_ok=True)
    with history.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(observed) + "\n")
    print(json.dumps(observed))
    return observed

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", default="juhwan0628/slide-extractor-gui")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--history", type=Path, required=True)
    args = parser.parse_args()
    refresh(args.repository, args.output, args.history)
