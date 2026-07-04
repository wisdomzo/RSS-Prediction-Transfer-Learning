from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "web" / "app-suite.html"
LOGO_DIR = ROOT / "logos"
WEB_LOGO_DIR = ROOT / "web" / "logos"


class AppSuiteStaticTests(unittest.TestCase):
    def read_app(self):
        return APP.read_text(encoding="utf-8")

    def test_app_suite_file_exists(self):
        self.assertTrue(APP.exists())

    def test_app_suite_wires_existing_pywebview_api_contract(self):
        html = self.read_app()
        required_calls = [
            "executeRssPrediction",
            "executeModelGeneration",
            "upload_csv_files",
            "executeDataProcessing",
            "get_prediction_data",
            "download_csv",
            "reset_temp_data",
            "get_help_pdf",
            "select_files_native",
        ]
        for call in required_calls:
            self.assertTrue(
                f"window.pywebview.api.{call}" in html or f"pywebview.api.{call}" in html,
                msg=f"Missing pywebview API call: {call}",
            )

    def test_app_suite_exposes_backend_progress_callbacks(self):
        html = self.read_app()
        self.assertIn("function updateProgress", html)
        self.assertIn("function updateTerminal", html)

    def test_app_suite_contains_product_suite_views(self):
        html = self.read_app()
        for label in [
            "Prediction Workspace",
            "Model Training",
            "Dataset Prep",
            "Results Explorer",
            "Log Console",
            "Dask Cluster",
            "Model Registry",
            "Export Center",
            "Acknowledgements",
        ]:
            self.assertIn(label, html)

    def test_app_suite_log_console_is_primary_workspace_not_only_rightbar(self):
        html = self.read_app()
        self.assertIn('data-view="logs"', html)
        self.assertIn('id="view-logs"', html)
        self.assertIn('id="terminal-content"', html)
        self.assertIn('id="terminal-content-main"', html)
        self.assertIn("appendTerminalLine", html)

    def test_prediction_parameters_are_above_prediction_area(self):
        html = self.read_app()
        start = html.index('id="view-prediction"')
        end = html.index('id="view-training"')
        prediction = html[start:end]
        self.assertLess(
            prediction.index("<h3>Parameters</h3>"),
            prediction.index("<h3>Prediction Area</h3>"),
        )

    def test_prediction_area_is_conditional_on_map_bounds_mode(self):
        html = self.read_app()
        self.assertIn('id="prediction-area-panel"', html)
        self.assertIn('onchange="togglePredictionArea()"', html)
        self.assertIn("function togglePredictionArea", html)
        self.assertIn('predictMode === "predictData_map"', html)

    def test_app_suite_has_professional_welcome_and_acknowledgement(self):
        html = self.read_app()
        self.assertIn("Welcome to ASSET Framework.", html)
        self.assertIn(
            "Special thanks to Dr. Ou Zhao for the foundational research and paper that made this project possible.",
            html,
        )

    def test_visible_page_descriptions_do_not_expose_internal_api_notes(self):
        html = self.read_app()
        for phrase in [
            "This screen calls",
            "This view calls",
            "backend callback",
            "backend contract",
            "The backend still",
            "CSV export uses",
            "WebviewLogger",
        ]:
            self.assertNotIn(phrase, html)

    def test_app_suite_has_institutional_logo_acknowledgements_page(self):
        html = self.read_app()
        self.assertTrue((LOGO_DIR / "NICT_logo.png").exists())
        self.assertTrue((LOGO_DIR / "ShinshuUniv_logo.png").exists())
        self.assertTrue((WEB_LOGO_DIR / "NICT_logo.png").exists())
        self.assertTrue((WEB_LOGO_DIR / "ShinshuUniv_logo.png").exists())
        self.assertIn('data-view="acknowledgements"', html)
        self.assertIn('id="view-acknowledgements"', html)
        self.assertIn('src="logos/NICT_logo.png"', html)
        self.assertIn('src="logos/ShinshuUniv_logo.png"', html)
        self.assertNotIn("../logos/", html)
        self.assertIn("National Institute of Information and Communications Technology", html)
        self.assertIn("Shinshu University", html)

    def test_prediction_run_locks_inputs_and_nonessential_navigation(self):
        html = self.read_app()
        self.assertIn("let predictionRunning = false", html)
        self.assertIn("function setPredictionRunning", html)
        self.assertIn('new Set(["prediction", "logs"])', html)
        self.assertIn("prediction-running", html)
        self.assertIn("data-keep-unlocked", html)
        self.assertIn("setPredictionRunning(true)", html)
        self.assertIn("setPredictionRunning(false)", html)
        self.assertIn("button.disabled = predictionRunning && !allowedViewsDuringPrediction.has(button.dataset.view)", html)
        self.assertIn("if (predictionRunning && !allowedViewsDuringPrediction.has(name))", html)

    def test_reset_clears_prediction_results(self):
        html = self.read_app()
        self.assertIn("function clearPredictionResults", html)
        self.assertIn("clearPredictionResults()", html)
        self.assertIn('document.getElementById("result-status").textContent = "No result loaded"', html)
        self.assertIn("if (!layer._url) resultMap.removeLayer(layer)", html)


if __name__ == "__main__":
    unittest.main()
