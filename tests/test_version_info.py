from pathlib import Path
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]


class VersionInfoTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
