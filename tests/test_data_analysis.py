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

    def test_prediction_csv_analysis_generates_absolute_error_cdf(self):
        self.require_plotting_dependencies()
        with TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "predict_RSS_sample.csv"
            csv_path.write_text(
                "\n".join(
                    [
                        "Latitude,Longitude,RSSI,DN,FresnelR_H,FresnelR_V,disBtwTxRx,Model_0,Model_1,Predicted_Value,Uncertainty,pathLoss_eta_2,pathLoss_eta_3",
                        "35.1,137.1,-90,10,1,2,100,-89,-92,-91,0.2,-88,-87",
                        "35.2,137.2,-80,11,1,2,110,-82,-79,-81,0.4,-78,-77",
                        "35.3,137.3,-999,12,1,2,120,-70,-72,-71,0.6,-69,-68",
                    ]
                ),
                encoding="utf-8",
            )

            result = my_plot_figure.plot_Prediction_CSV_Analysis(
                [str(csv_path)],
                str(Path(tmp) / "analysis"),
                analysis_type="absolute_error_cdf",
                needPNG=True,
                needSVG=True,
            )

            self.assertEqual(result["status"], "success")
            self.assertEqual(result["valid_file_count"], 1)
            self.assertEqual(result["files"][0]["sample_count"], 2)
            self.assertAlmostEqual(result["files"][0]["median"], 1.0)
            self.assertTrue(Path(result["svg_path"]).exists())
            self.assertTrue(Path(result["png_path"]).exists())

    def test_prediction_csv_analysis_rssi_cdf_keeps_placeholder_values(self):
        self.require_plotting_dependencies()
        with TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "predict_RSS_map_bound.csv"
            csv_path.write_text(
                "\n".join(
                    [
                        "Latitude,Longitude,RSSI,Predicted_Value,Uncertainty",
                        "35.1,137.1,-999,-91,0.2",
                        "35.2,137.2,-999,-81,0.4",
                    ]
                ),
                encoding="utf-8",
            )

            result = my_plot_figure.plot_Prediction_CSV_Analysis(
                [str(csv_path)],
                str(Path(tmp) / "analysis"),
                analysis_type="rssi_cdf",
                needPNG=True,
                needSVG=True,
            )

            self.assertEqual(result["status"], "success")
            self.assertEqual(result["files"][0]["sample_count"], 2)
            self.assertAlmostEqual(result["files"][0]["median"], -999.0)

    def test_prediction_csv_analysis_uses_publication_figure_size(self):
        source = PLOT_FILE.read_text(encoding="utf-8")
        function_source = source[
            source.index("def plot_Prediction_CSV_Analysis"):
            source.index("\ndef split_dataset_by_region_stratified_sampling")
        ]
        self.assertIn("width_inch = 80 / 25.4", function_source)
        self.assertIn("height_inch = 56.56 / 25.4", function_source)
        self.assertIn("Figure(figsize=(width_inch, height_inch), dpi=300)", function_source)
        self.assertIn("plt.rcParams['legend.fontsize'] = 7", function_source)
        self.assertIn('analysis_type in {"uncertainty_cdf", "absolute_error_cdf"}', function_source)
        self.assertIn('"rssi_cdf": ("RSSI CDF", "RSSI in dBm")', function_source)
        self.assertIn('"predicted_value_cdf": ("Predicted Value CDF", "Predicted RSS in dBm")', function_source)
        self.assertIn('"uncertainty_cdf": ("Uncertainty CDF", "Uncertainty in dB")', function_source)
        self.assertIn('"absolute_error_cdf": ("Prediction Absolute Error CDF", "Absolute Error in dB")', function_source)

    def test_prediction_csv_analysis_generates_model_error_boxplot(self):
        self.require_plotting_dependencies()
        with TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "predict_RSS_sample.csv"
            csv_path.write_text(
                "\n".join(
                    [
                        "Latitude,Longitude,RSSI,Model_0,Model_1,Predicted_Value,Uncertainty",
                        "35.1,137.1,-90,-89,-94,-91,0.2",
                        "35.2,137.2,-80,-83,-79,-81,0.4",
                        "35.3,137.3,-999,0,0,-70,0.6",
                    ]
                ),
                encoding="utf-8",
            )

            result = my_plot_figure.plot_Prediction_CSV_Analysis(
                [str(csv_path)],
                str(Path(tmp) / "analysis"),
                analysis_type="model_error_boxplot",
                needPNG=True,
                needSVG=True,
            )

            self.assertEqual(result["status"], "success")
            self.assertEqual(result["files"][0]["model_count"], 2)
            self.assertEqual(result["files"][0]["sample_count"], 4)
            self.assertAlmostEqual(result["files"][0]["mean"], 2.25)
            self.assertAlmostEqual(result["files"][0]["median"], 2.0)

    def test_prediction_csv_analysis_boxplot_uses_colored_boxes(self):
        source = PLOT_FILE.read_text(encoding="utf-8")
        function_source = source[
            source.index("if analysis_type == \"model_error_boxplot\":"):
            source.index("        ax.tick_params(axis=\"x\"", source.index("if analysis_type == \"model_error_boxplot\":"))
        ]
        self.assertIn("box_artists = ax.boxplot(", function_source)
        self.assertIn("for index, patch in enumerate(box_artists[\"boxes\"]):", function_source)
        self.assertIn("patch.set_facecolor", function_source)

    def test_prediction_csv_analysis_boxplot_requires_rssi_column(self):
        self.require_plotting_dependencies()
        with TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "missing_rssi.csv"
            csv_path.write_text(
                "\n".join(
                    [
                        "Latitude,Longitude,Model_0,Predicted_Value,Uncertainty",
                        "35.1,137.1,-89,-91,0.2",
                    ]
                ),
                encoding="utf-8",
            )

            result = my_plot_figure.plot_Prediction_CSV_Analysis(
                [str(csv_path)],
                str(Path(tmp) / "analysis"),
                analysis_type="model_error_boxplot",
                needPNG=False,
                needSVG=False,
            )

            self.assertEqual(result["status"], "error")
            self.assertIn("RSSI", result["skipped_files"][0]["reason"])

    def test_prediction_csv_analysis_generates_summary_statistics_table(self):
        self.require_plotting_dependencies()
        with TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "predict_RSS_summary.csv"
            csv_path.write_text(
                "\n".join(
                    [
                        "RSSI,Predicted_Value,Uncertainty",
                        "-90,-91,0.2",
                        "-80,-78,0.4",
                        "-999,-70,0.6",
                        "-70,-73,0.8",
                    ]
                ),
                encoding="utf-8",
            )

            result = my_plot_figure.plot_Prediction_CSV_Analysis(
                [str(csv_path)],
                str(Path(tmp) / "analysis"),
                analysis_type="summary_statistics_table",
                needPNG=True,
                needSVG=True,
            )

            self.assertEqual(result["status"], "success")
            self.assertEqual(result["files"][0]["sample_count"], 3)
            self.assertEqual(result["files"][0]["metric_count"], 4)
            self.assertAlmostEqual(result["files"][0]["statistics"]["RSSI"]["mean"], -80.0)
            self.assertAlmostEqual(result["files"][0]["statistics"]["Predicted_Value"]["median"], -78.0)
            self.assertAlmostEqual(result["files"][0]["statistics"]["Uncertainty"]["p80"], 0.64)
            self.assertAlmostEqual(result["files"][0]["statistics"]["Absolute Error"]["p95"], 2.9)
            self.assertTrue(Path(result["svg_path"]).exists())
            self.assertTrue(Path(result["png_path"]).exists())

    def test_prediction_csv_analysis_generates_baseline_comparison_cdf(self):
        self.require_plotting_dependencies()
        with TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "predict_RSS_baseline.csv"
            csv_path.write_text(
                "\n".join(
                    [
                        "RSSI,Predicted_Value,pathLoss_eta_2,pathLoss_eta_3",
                        "-90,-91,-95,-85",
                        "-80,-79,-88,-82",
                        "-999,-70,-60,-61",
                    ]
                ),
                encoding="utf-8",
            )

            result = my_plot_figure.plot_Prediction_CSV_Analysis(
                [str(csv_path)],
                str(Path(tmp) / "analysis"),
                analysis_type="path_loss_baseline_cdf",
                needPNG=False,
                needSVG=False,
            )

            self.assertEqual(result["status"], "success")
            self.assertEqual(result["files"][0]["series_count"], 3)
            self.assertEqual(result["files"][0]["sample_count"], 6)
            self.assertAlmostEqual(result["files"][0]["series"]["ML Prediction"]["median"], 1.0)
            self.assertAlmostEqual(result["files"][0]["series"]["Path Loss eta 2"]["median"], 6.5)

    def test_prediction_csv_analysis_generates_uncertainty_calibration_bins(self):
        self.require_plotting_dependencies()
        with TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "predict_RSS_calibration.csv"
            csv_path.write_text(
                "\n".join(
                    [
                        "RSSI,Predicted_Value,Uncertainty",
                        "-90,-90,0.1",
                        "-80,-82,0.2",
                        "-70,-75,0.9",
                        "-999,-60,1.0",
                    ]
                ),
                encoding="utf-8",
            )

            result = my_plot_figure.plot_Prediction_CSV_Analysis(
                [str(csv_path)],
                str(Path(tmp) / "analysis"),
                analysis_type="uncertainty_calibration",
                needPNG=False,
                needSVG=False,
            )

            self.assertEqual(result["status"], "success")
            self.assertEqual(result["files"][0]["sample_count"], 3)
            self.assertEqual(result["files"][0]["bin_count"], 3)
            self.assertGreater(result["files"][0]["mean"], 0)

    def test_prediction_csv_analysis_spatial_error_map_requires_coordinates(self):
        self.require_plotting_dependencies()
        with TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "predict_RSS_no_coordinates.csv"
            csv_path.write_text(
                "\n".join(
                    [
                        "RSSI,Predicted_Value",
                        "-90,-91",
                        "-80,-78",
                    ]
                ),
                encoding="utf-8",
            )

            result = my_plot_figure.plot_Prediction_CSV_Analysis(
                [str(csv_path)],
                str(Path(tmp) / "analysis"),
                analysis_type="spatial_error_map",
                needPNG=False,
                needSVG=False,
            )

            self.assertEqual(result["status"], "error")
            self.assertIn("Latitude", result["skipped_files"][0]["reason"])
            self.assertIn("Longitude", result["skipped_files"][0]["reason"])

    def test_prediction_csv_analysis_skips_missing_required_columns(self):
        self.require_plotting_dependencies()
        with TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "bad.csv"
            csv_path.write_text("Latitude,Longitude,RSSI\n35.1,137.1,-80\n", encoding="utf-8")

            result = my_plot_figure.plot_Prediction_CSV_Analysis(
                [str(csv_path)],
                str(Path(tmp) / "analysis"),
                analysis_type="predicted_value_cdf",
                needPNG=False,
                needSVG=False,
            )

            self.assertEqual(result["status"], "error")
            self.assertIn("Predicted_Value", result["skipped_files"][0]["reason"])


if __name__ == "__main__":
    unittest.main()
