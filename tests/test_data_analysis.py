from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

ROOT = Path(__file__).resolve().parents[1]
PLOT_FILE = ROOT / "my_plot_figure.py"

try:
    import my_plot_figure
except ModuleNotFoundError as exc:
    if exc.name in {"pandas", "matplotlib", "sklearn", "scipy", "numpy"}:
        my_plot_figure = None
        PLOTTING_DEPENDENCY_SKIP_REASON = f"Data analysis plotting dependencies are not installed: {exc.name}"
    else:
        raise
else:
    PLOTTING_DEPENDENCY_SKIP_REASON = ""


class DataAnalysisTests(unittest.TestCase):
    def require_plotting_dependencies(self):
        if my_plot_figure is None:
            self.skipTest(PLOTTING_DEPENDENCY_SKIP_REASON)

    def test_model_aggregation_error_cdf_skips_invalid_csv_files(self):
        self.require_plotting_dependencies()
        with TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "missing_columns.csv"
            csv_path.write_text("RSSI,Prediction\n-90,-88\n", encoding="utf-8")

            result = my_plot_figure.plot_Model_Aggregation_Error_CDF(
                [str(csv_path)],
                str(Path(tmp) / "out"),
                needPNG=False,
                needSVG=False,
            )

            self.assertEqual(result["status"], "error")
            self.assertIn("No valid CSV", result["message"])
            self.assertIn("Model_*", result["skipped_files"][0]["reason"])

    def test_model_aggregation_error_cdf_generates_combined_svg_png_and_metrics(self):
        self.require_plotting_dependencies()
        with TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "prediction.csv"
            csv_path.write_text(
                "\n".join(
                    [
                        "rssi,Model_0,Model_1,Model_2",
                        "-90,-89,-91,-88",
                        "-80,-81,-79,-78",
                        "-70,-75,-65,-73",
                    ]
                ),
                encoding="utf-8",
            )

            result = my_plot_figure.plot_Model_Aggregation_Error_CDF(
                [str(csv_path)],
                str(Path(tmp) / "analysis"),
                needPNG=True,
                needSVG=True,
            )

            self.assertEqual(result["status"], "success")
            self.assertEqual(result["valid_file_count"], 1)
            self.assertEqual(result["files"][0]["sample_count"], 3)
            self.assertEqual(result["files"][0]["model_columns"], ["Model_0", "Model_1", "Model_2"])
            self.assertAlmostEqual(result["files"][0]["median_absolute_error_mean"], 1.6666666667)
            self.assertAlmostEqual(result["files"][0]["mean_absolute_error_mean"], 0.7777777778)
            self.assertTrue(Path(result["svg_path"]).exists())
            self.assertTrue(Path(result["png_path"]).exists())

    def test_model_aggregation_plot_uses_non_interactive_agg_canvas(self):
        source = PLOT_FILE.read_text(encoding="utf-8")
        function_source = source[
            source.index("def plot_Model_Aggregation_Error_CDF"):
            source.index("\ndef main():")
        ]
        self.assertIn("FigureCanvasAgg(fig)", function_source)
        self.assertIn("Figure(figsize=", function_source)
        self.assertNotIn("plt.subplots(", function_source)

    def test_model_aggregation_plot_supports_display_mode_and_line_styles(self):
        source = PLOT_FILE.read_text(encoding="utf-8")
        function_source = source[
            source.index("def plot_Model_Aggregation_Error_CDF"):
            source.index("\ndef main():")
        ]
        self.assertIn('display_mode="both"', function_source)
        self.assertIn("file_colors=None", function_source)
        self.assertIn('display_mode in {"both", "mean"}', function_source)
        self.assertIn('display_mode in {"both", "median"}', function_source)
        self.assertIn('linestyle=":"', function_source)
        self.assertIn('linestyle="-"', function_source)
        self.assertIn("normalize_matplotlib_color(result.get(\"color\"))", function_source)

    def test_rgb_color_strings_are_converted_for_matplotlib(self):
        source = PLOT_FILE.read_text(encoding="utf-8")
        self.assertIn("def normalize_matplotlib_color", source)
        self.assertIn('rgb\\(', source)
        self.assertIn("return tuple(channels)", source)


if __name__ == "__main__":
    unittest.main()
