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

    def test_prediction_reset_terminates_active_prediction_process(self):
        source = MAIN.read_text(encoding="utf-8")
        self.assertIn("current_prediction_process", source)
        self.assertIn("def terminate_current_prediction", source)
        self.assertIn("multiprocessing.Process", source)
        self.assertIn(".terminate()", source)
        self.assertIn(".kill()", source)
        self.assertIn("terminate_current_prediction()", source)

    def test_dataset_output_download_is_exposed(self):
        source = MAIN.read_text(encoding="utf-8")
        self.assertIn("def download_dataset_output", source)
        self.assertIn('download_model("ML_")', source)
        self.assertIn("window.expose(download_dataset_output)", source)


if __name__ == "__main__":
    unittest.main()
