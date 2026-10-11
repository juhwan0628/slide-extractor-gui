"""Publish repository-hosted badges and JSON for public installer downloads."""
from html import escape
import runpy
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
                     **({"Authorization": f"Bearer {token}"} if token else {}),
                     "X-GitHub-Api-Version": "2022-11-28"},
        )
        with urlopen(request, timeout=30) as response:
            batch = json.load(response)
        releases.extend(batch)
        if len(batch) < 100:
            return releases
    raise RuntimeError("Release pagination limit exceeded; preserving existing counters")


def badge_svg(label, message, color="6556d9"):
    """Render a self-contained badge without an external image service."""
    left = max(40, len(label) * 7 + 12)
    right = max(30, len(message) * 7 + 12)
    width = left + right
    title = escape(f"{label}: {message}")
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="20" '
        f'role="img" aria-label="{title}"><title>{title}</title>'
        f'<rect width="{width}" height="20" rx="3" fill="#555"/>'
        f'<path d="M{left} 0h{right-3}q3 0 3 3v14q0 3-3 3h-{right-3}z" fill="#{color}"/>'
        '<g fill="#fff" text-anchor="middle" font-family="Verdana,DejaVu Sans,sans-serif" font-size="11">'
        f'<text x="{left/2}" y="14">{escape(label)}</text>'
        f'<text x="{left+right/2}" y="14">{escape(message)}</text></g></svg>\n'
    )

def write_static_badges(output):
    output.mkdir(parents=True, exist_ok=True)
    version = runpy.run_path(str(Path(__file__).resolve().parents[1] / "slide_core/version.py"))["VERSION"]
    for name, label, message, color in (
        ("beta", "beta", version, "6556d9"),
        ("platform-macos", "macOS", "Apple Silicon", "20242a"),
        ("platform-windows", "Windows", "x64", "20242a"),
    ):
        (output / f"{name}.svg").write_text(badge_svg(label, message, color), encoding="utf-8")

def write_badges(counts, output):
    output.mkdir(parents=True, exist_ok=True)
    for key, label in (("total", "Installer downloads"), ("macos", "Mac downloads"),
                       ("windows", "Windows downloads")):
        badge = {"schemaVersion": 1, "label": label, "message": str(counts[key]),
                 "color": "6556d9", "cacheSeconds": 300}
        (output / f"{key}.svg").write_text(badge_svg(label, str(counts[key])), encoding="utf-8")
        (output / f"{key}.json").write_text(json.dumps(badge, indent=2) + "\n", encoding="utf-8")

if __name__ == "__main__":
    counts = installer_counts(fetch_releases(os.environ["GITHUB_REPOSITORY"], os.environ["GH_TOKEN"]))
    write_badges(counts, Path("docs/downloads"))
    write_static_badges(Path("docs/downloads"))
    print(json.dumps(counts))
