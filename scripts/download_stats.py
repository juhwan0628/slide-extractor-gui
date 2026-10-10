"""Publish Shields endpoint data for public installer downloads."""
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen

def installer_counts(releases):
    counts = {"macos": 0, "windows": 0}
    for release in releases:
        if release.get("draft"):
            continue
        for asset in release.get("assets", []):
            name = asset["name"].lower()
            if name.endswith(".dmg"):
                counts["macos"] += asset["download_count"]
            elif name.endswith(".exe"):
                counts["windows"] += asset["download_count"]
    counts["total"] = counts["macos"] + counts["windows"]
    return counts

def fetch_releases(repository, token):
    releases = []
    for page in range(1, 1001):
        request = Request(
            f"https://api.github.com/repos/{repository}/releases?per_page=100&page={page}",
            headers={"Accept": "application/vnd.github+json",
                     "Authorization": f"Bearer {token}",
                     "X-GitHub-Api-Version": "2022-11-28"},
        )
        with urlopen(request, timeout=30) as response:
            batch = json.load(response)
        releases.extend(batch)
        if len(batch) < 100:
            return releases
    raise RuntimeError("Release pagination limit exceeded; preserving existing counters")

def write_badges(counts, output):
    output.mkdir(parents=True, exist_ok=True)
    for key, label in (("total", "Installer downloads"), ("macos", "Mac downloads"),
                       ("windows", "Windows downloads")):
        badge = {"schemaVersion": 1, "label": label, "message": str(counts[key]),
                 "color": "6556d9", "cacheSeconds": 300}
        (output / f"{key}.json").write_text(json.dumps(badge, indent=2) + "\n", encoding="utf-8")

if __name__ == "__main__":
    counts = installer_counts(fetch_releases(os.environ["GITHUB_REPOSITORY"], os.environ["GH_TOKEN"]))
    write_badges(counts, Path("docs/downloads"))
    print(json.dumps(counts))
