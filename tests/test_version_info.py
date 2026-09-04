from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]


class VersionInfoTests(unittest.TestCase):
    def test_git_output_is_decoded_as_utf8_on_windows_locales(self):
        from version_info import _run_git

        completed = subprocess.CompletedProcess(
            args=["git"],
            returncode=0,
            stdout="v2.6.4, English interface update",
            stderr="",
        )
        with mock.patch("version_info.subprocess.run", return_value=completed) as run:
            self.assertEqual(_run_git(ROOT, "log", "-1", "--pretty=%s"), "v2.6.4, English interface update")
        self.assertEqual(run.call_args.kwargs["encoding"], "utf-8")
        self.assertEqual(run.call_args.kwargs["errors"], "replace")

    def test_git_output_none_is_treated_as_missing_version_data(self):
        from version_info import _run_git

        completed = subprocess.CompletedProcess(
            args=["git"],
            returncode=0,
            stdout=None,
            stderr="",
        )
        with mock.patch("version_info.subprocess.run", return_value=completed):
            self.assertIsNone(_run_git(ROOT, "log", "-1", "--pretty=%s"))

    def test_explicit_version_has_priority_and_is_normalized(self):
        from version_info import resolve_version

        with mock.patch("version_info._run_git") as run_git:
            self.assertEqual(resolve_version(ROOT, "2.7.0"), "v2.7.0")
        run_git.assert_not_called()

    def test_exact_git_tag_is_used_when_no_version_is_supplied(self):
        from version_info import resolve_version

        with mock.patch("version_info._run_git", side_effect=["v2.6.5"]):
            self.assertEqual(resolve_version(ROOT), "v2.6.5")

    def test_latest_commit_subject_is_used_when_head_has_no_tag(self):
        from version_info import resolve_version

        with mock.patch(
            "version_info._run_git",
            side_effect=[None, "v2.6.4, English interface update"],
        ):
            self.assertEqual(resolve_version(ROOT), "v2.6.4")

    def test_missing_git_version_raises_a_clear_error(self):
        from version_info import VersionResolutionError, resolve_version

        with mock.patch("version_info._run_git", side_effect=[None, "UI cleanup"]):
            with self.assertRaisesRegex(VersionResolutionError, "version"):
                resolve_version(ROOT)

    def test_invalid_explicit_version_is_rejected(self):
        from version_info import VersionResolutionError, resolve_version

        with self.assertRaisesRegex(VersionResolutionError, "semantic version"):
            resolve_version(ROOT, "release-latest")

    def test_runtime_version_prefers_packaged_resource(self):
        from version_info import resolve_runtime_version

        with tempfile.TemporaryDirectory() as directory:
            version_file = Path(directory) / "asset_version.txt"
            version_file.write_text("v2.6.4\n", encoding="utf-8")
            with mock.patch("version_info.resolve_version") as resolve_git_version:
                self.assertEqual(
                    resolve_runtime_version(ROOT, version_file),
                    "v2.6.4",
                )
            resolve_git_version.assert_not_called()

    def test_runtime_version_falls_back_to_development_build(self):
        from version_info import VersionResolutionError, resolve_runtime_version

        with tempfile.TemporaryDirectory() as directory:
            missing_file = Path(directory) / "asset_version.txt"
            with mock.patch(
                "version_info.resolve_version",
                side_effect=VersionResolutionError("missing"),
            ):
                self.assertEqual(
                    resolve_runtime_version(ROOT, missing_file),
                    "Development Build",
                )


class BuildScriptVersionTests(unittest.TestCase):
    def test_build_script_uses_git_version_and_updates_macos_metadata(self):
        script = (ROOT / "build_mac.sh").read_text(encoding="utf-8")
        self.assertIn('version_info.py', script)
        self.assertIn('APP_NAME="${BASE_NAME}_${VERSION}"', script)
        self.assertIn("CFBundleShortVersionString", script)
        self.assertIn("CFBundleVersion", script)
        self.assertIn('dist/$APP_NAME.app/Contents/Info.plist', script)
        self.assertIn('build/asset_version.txt', script)
        self.assertIn('--add-data "build/asset_version.txt:."', script)

    def test_windows_build_script_matches_mac_packaging_contract(self):
        script = (ROOT / "build_windows.ps1").read_text(encoding="utf-8")
        self.assertIn("version_info.py", script)
        self.assertIn('RSS_Predictor_Windows_$Version', script)
        self.assertIn("build\\asset_version.txt", script)
        self.assertIn('Set-Content -Path $AssetVersionPath -Value $Version', script)
        self.assertIn('"--add-data", "web;web"', script)
        self.assertIn('"--add-data", "tempData;tempData"', script)
        self.assertIn('"--add-data", "database;database"', script)
        self.assertIn('"--add-data", "models;models"', script)
        self.assertIn('"--add-data", "assets;assets"', script)
        self.assertIn('"--add-data", "build\\asset_version.txt;."', script)
        self.assertIn('"--exclude-module", "ray.thirdparty_files.psutil"', script)
        self.assertIn('"--hidden-import", "numpy.core.multiarray"', script)
        self.assertIn('"--hidden-import", "numpy.core._multiarray_umath"', script)
        self.assertIn('"--hidden-import", "fiona._shim"', script)
        self.assertIn('"--collect-all", "pywebview"', script)
        self.assertIn("Remove-Item -Recurse -Force build, dist", script)
        self.assertIn("Get-ChildItem -Filter *.spec", script)


if __name__ == "__main__":
    unittest.main()
