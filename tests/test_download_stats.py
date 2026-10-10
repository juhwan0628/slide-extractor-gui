"""Download totals count public installers rather than source packages or users."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
import json

spec = importlib.util.spec_from_file_location("download_stats", Path(__file__).parents[1] / "scripts/download_stats.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class DownloadStatsTests(unittest.TestCase):
    def test_public_betas_and_stable_installers_count_but_sources_and_drafts_do_not(self):
        releases = [
            {"draft": False, "prerelease": True, "assets": [
                {"name": "app.dmg", "download_count": 2},
                {"name": "app.exe", "download_count": 3},
                {"name": "Sources-Licenses.zip", "download_count": 100},
                {"name": "SHA256SUMS.txt", "download_count": 50}]},
            {"draft": False, "prerelease": False, "assets": [
                {"name": "old.DMG", "download_count": 4}]},
            {"draft": True, "assets": [{"name": "draft.exe", "download_count": 900}]},
        ]
        self.assertEqual(module.installer_counts(releases), {"macos": 6, "windows": 3, "total": 9})

    def test_empty_release_list_has_zero_downloads(self):
        self.assertEqual(module.installer_counts([]), {"macos": 0, "windows": 0, "total": 0})

    def test_badges_have_numeric_counts_and_supported_endpoint_schema(self):
        with tempfile.TemporaryDirectory() as temp:
            module.write_badges({"macos": 2, "windows": 5, "total": 7}, Path(temp))
            for key, count in (("total", 7), ("macos", 2), ("windows", 5)):
                data = json.loads((Path(temp) / f"{key}.json").read_text())
                self.assertEqual(data["schemaVersion"], 1)
                self.assertEqual(data["message"], str(count))

if __name__ == "__main__":
    unittest.main()
