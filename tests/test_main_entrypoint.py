from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "main.py"


class MainEntrypointTests(unittest.TestCase):
    def test_main_defaults_to_app_suite_with_env_override(self):
        source = MAIN.read_text(encoding="utf-8")
        self.assertIn("ASSET_UI_ENTRY", source)
        self.assertIn('"web/app-suite.html"', source)
        self.assertIn("get_resource_path(ui_entry)", source)

    def test_main_maximizes_window_without_fullscreen_or_fixed_size(self):
        source = MAIN.read_text(encoding="utf-8")
        window_call = source[source.index("webview.create_window("):source.index("window.expose(executeRssPrediction)")]
        self.assertIn("window.maximize()", source)
        self.assertNotIn("fullscreen=True", window_call)
        self.assertNotIn("width=1024", window_call)
        self.assertNotIn("height=768", window_call)
        self.assertNotIn("min_size=(1024, 768)", window_call)


if __name__ == "__main__":
    unittest.main()
