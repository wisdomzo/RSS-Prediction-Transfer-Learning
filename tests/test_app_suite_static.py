from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "web" / "app-suite.html"
LOGO_DIR = ROOT / "logos"
WEB_LOGO_DIR = ROOT / "web" / "logos"
HELP_ASSET_DIR = ROOT / "web" / "assets" / "help"


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
            "download_dataset_output",
            "reset_temp_data",
            "get_help_pdf",
            "select_files_native",
            "select_folder_native",
            "list_analysis_csv_files",
            "executeDataAnalysis",
            "reset_data_analysis_outputs",
            "download_data_analysis_svg",
            "download_data_analysis_png",
            "get_ui_preferences",
            "save_ui_preferences",
            "download_application_log",
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
            "Feature Generation",
            "Results Explorer",
            "Log Console",
            "Data Analysis",
            "Reference",
            "Acknowledgements",
        ]:
            self.assertIn(label, html)
        for removed_label in [
            "Dask Cluster",
            "Model Registry",
            "Export Center",
            'data-view="cluster"',
            'data-view="registry"',
            'data-view="exports"',
            'id="view-cluster"',
            'id="view-registry"',
            'id="view-exports"',
        ]:
            self.assertNotIn(removed_label, html)
        self.assertIn('id="runtime-pill"', html)
        self.assertIn('id="runtime-title"', html)
        self.assertNotIn('id="progress-percent"', html)
        self.assertNotIn('id="progress-status"', html)

    def test_sidebar_brand_displays_runtime_app_version(self):
        html = self.read_app()
        self.assertIn('id="app-version"', html)
        self.assertIn('class="version-badge"', html)
        self.assertIn("async function loadAppVersion", html)
        self.assertIn("window.pywebview.api.get_app_version()", html)
        self.assertIn('window.addEventListener("pywebviewready", loadAppVersion)', html)

    def test_system_data_analysis_view_supports_cdf_plot_and_downloads(self):
        html = self.read_app()
        self.assertIn('data-view="analysis"', html)
        self.assertIn('id="view-analysis"', html)
        self.assertIn('id="analysis-cdf-preview"', html)
        self.assertIn('id="analysis-csv-table"', html)
        self.assertIn('id="analysis-display-mode"', html)
        self.assertIn('id="analysis-empty-preview"', html)
        self.assertIn('data-analysis-tab="ensemble-cdf"', html)
        self.assertIn('id="analysis-panel-ensemble-cdf"', html)
        self.assertIn("resetDataAnalysis()", html)
        self.assertIn('id="download-analysis-svg-btn"', html)
        self.assertIn('id="download-analysis-png-btn"', html)
        self.assertIn("function selectAnalysisFolder", html)
        self.assertIn("function renderAnalysisCsvFiles", html)
        self.assertIn("function resetDataAnalysis", html)
        self.assertIn("function showAnalysisPanel", html)
        self.assertIn("function runDataAnalysis", html)
        self.assertIn('class="analysis-csv-checkbox" data-index="${index}" />', html)
        self.assertIn('class="analysis-color-input"', html)
        self.assertIn('class="analysis-color-text"', html)
        self.assertIn('displayMode: document.getElementById("analysis-display-mode").value', html)
        self.assertIn("getSelectedAnalysisFileOptions", html)
        self.assertIn("renderAnalysisSummary(result, result.display_mode", html)
        self.assertIn('mode === "both" || mode === "mean"', html)
        self.assertIn('mode === "both" || mode === "median"', html)
        self.assertIn("window.pywebview.api.select_folder_native()", html)
        self.assertIn("window.pywebview.api.list_analysis_csv_files", html)
        self.assertIn("window.pywebview.api.executeDataAnalysis", html)
        self.assertIn("window.pywebview.api.reset_data_analysis_outputs()", html)
        self.assertIn("window.pywebview.api.download_data_analysis_svg()", html)
        self.assertIn("window.pywebview.api.download_data_analysis_png()", html)
        self.assertIn("Additional analysis functions will be added here in future releases.", html)

    def test_system_reference_view_contains_scientific_citations(self):
        html = self.read_app()
        system_start = html.index('<div class="nav-title">System</div>')
        system_end = html.index("</aside>", system_start)
        system_nav = html[system_start:system_end]
        self.assertIn('data-view="reference"', system_nav)
        self.assertIn("Reference", system_nav)
        self.assertIn('id="view-reference"', html)
        self.assertIn("Scientific References", html)
        self.assertIn("This application was developed with reference to the following research works.", html)
        self.assertIn("Geographic Knowledge-Driven Transfer Learning for Enhanced Received Signal Strength Prediction", html)
        self.assertIn("IEEE Trans. Cogn. Commun. Netw.", html)
        self.assertIn("https://doi.org/10.1109/TCCN.2025.3633744", html)
        self.assertIn('<span class="pill">Journal Article</span>\n                    <span class="pill">IEEE</span>\n                    <a class="pill reference-link"', html)
        self.assertIn('class="pill reference-link"', html)
        self.assertNotIn('class="ghost-btn reference-link"', html)
        self.assertIn(".reference-link", html)
        self.assertIn("display: inline-flex;", html)
        self.assertIn("align-items: center;", html)
        self.assertIn("line-height: 1;", html)
        self.assertIn("Open DOI", html)
        self.assertIn("ASSET: An Ensemble-Learning-Based Framework for Adaptive Signal Strength Estimation and Tracking", html)
        self.assertIn("Technical Report", html)

    def test_prediction_data_tooltip_documents_csv_coordinate_format(self):
        html = self.read_app()
        self.assertIn('data-help-for="p-predictDataSelect"', html)
        self.assertIn("CSV prediction files must include longitude and latitude columns.", html)
        self.assertIn("Accepted longitude names: longitude, lon, lng, or x.", html)
        self.assertIn("Accepted latitude names: latitude, lat, or y.", html)
        self.assertIn("RSSI is optional for prediction CSV files; missing values are filled internally.", html)

    def test_height_parameter_tooltips_include_reference_image(self):
        html = self.read_app()
        self.assertTrue((HELP_ASSET_DIR / "antenna-height-reference.png").exists())
        self.assertIn(".help-tooltip.visual-help", html)
        self.assertIn(".help-tooltip img", html)
        self.assertEqual(6, html.count('src="assets/help/antenna-height-reference.png"'))
        for help_id in [
            "p-fixAntenna_alt",
            "p-fixAntenna_height",
            "p-moveAntenna_height",
            "d-fixAntenna_alt",
            "d-fixAntenna_height",
            "d-moveAntenna_height",
        ]:
            self.assertIn(f'data-help-for="{help_id}"', html)

    def test_app_suite_log_console_is_primary_workspace_not_only_rightbar(self):
        html = self.read_app()
        self.assertIn('data-view="logs"', html)
        self.assertIn('id="view-logs"', html)
        self.assertIn('id="terminal-content"', html)
        self.assertIn('id="terminal-content-main"', html)
        self.assertIn("appendTerminalLine", html)

    def test_app_starts_two_column_and_expands_to_three_columns_on_wide_viewports(self):
        html = self.read_app()
        self.assertIn("grid-template-columns: 264px minmax(0, 1fr);", html)
        self.assertIn("display: none;", html)
        self.assertIn("@media (min-width: 1360px)", html)
        self.assertIn("grid-template-columns: 264px minmax(720px, 1fr) 340px;", html)
        self.assertIn(".rightbar { display: block; }", html)
        self.assertNotIn("Watch Runtime Monitor for progress.", html)

    def test_prediction_parameters_are_above_prediction_area(self):
        html = self.read_app()
        start = html.index('id="view-prediction"')
        end = html.index('id="view-training"')
        prediction = html[start:end]
        self.assertLess(
            prediction.index("<h3>Parameters</h3>"),
            prediction.index("<h3>Prediction Area</h3>"),
        )

    def test_model_settings_uses_same_workspace_width_as_welcome(self):
        html = self.read_app()
        start = html.index('id="view-training"')
        end = html.index('id="view-dataset"')
        training = html[start:end]
        self.assertIn('class="panel welcome-panel workspace-width"', html)
        self.assertIn('class="model-training-stack workspace-width"', training)
        self.assertNotIn('class="wide-grid"', training)
        self.assertLess(
            training.index("<h3>Model Settings</h3>"),
            training.index("<h3>Feature Vector Files</h3>"),
        )
        self.assertIn(".model-training-stack", html)
        self.assertIn(".workspace-width", html)

    def test_prediction_welcome_and_parameters_share_workspace_width(self):
        html = self.read_app()
        start = html.index('id="view-prediction"')
        end = html.index('id="view-training"')
        prediction = html[start:end]
        self.assertIn('class="panel welcome-panel workspace-width"', prediction)
        self.assertIn('class="stack workspace-width"', prediction)

    def test_compact_log_width_is_not_driven_by_log_content(self):
        html = self.read_app()
        self.assertIn("width: 340px;", html)
        self.assertIn("max-width: 340px;", html)
        self.assertIn(".rightbar .stack {", html)
        self.assertIn("grid-template-columns: minmax(0, 1fr);", html)
        self.assertIn(".rightbar .panel,", html)
        self.assertIn(".rightbar .log {", html)
        self.assertIn("overflow-wrap: anywhere;", html)
        self.assertIn("white-space: pre-wrap;", html)

    def test_application_log_height_can_be_locked(self):
        html = self.read_app()
        self.assertIn(".application-log.fixed-height", html)
        self.assertIn(".application-log.expanded-height", html)
        self.assertIn('id="log-height-toggle"', html)
        self.assertIn('onclick="toggleApplicationLogHeight()"', html)
        self.assertIn('id="terminal-content-main" class="log application-log fixed-height"', html)
        self.assertIn("function toggleApplicationLogHeight", html)
        self.assertIn('terminal.classList.toggle("fixed-height", !isExpanded)', html)
        self.assertIn('terminal.classList.toggle("expanded-height", isExpanded)', html)
        self.assertIn('button.textContent = isExpanded ? "Lock Height" : "Expand Height"', html)

    def test_application_log_can_be_exported(self):
        html = self.read_app()
        self.assertIn('id="export-log-btn"', html)
        self.assertIn('onclick="exportApplicationLog()"', html)
        self.assertIn("async function exportApplicationLog", html)
        self.assertIn('document.getElementById("terminal-content-main").textContent', html)
        self.assertIn('Array.from(terminal.children).map((line) => line.textContent).join("\\n")', html)
        self.assertIn("window.pywebview.api.download_application_log", html)
        self.assertIn("Application log exported.", html)

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
        self.assertIn('class="nav-item hidden" data-view="acknowledgements"', html)
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

    def test_completed_prediction_guides_user_to_latest_results(self):
        html = self.read_app()
        self.assertIn('id="results-nav-item"', html)
        self.assertIn('id="results-new-badge"', html)
        self.assertIn('id="prediction-result-guide"', html)
        self.assertIn("Prediction complete", html)
        self.assertIn("Your latest RSS prediction is ready.", html)
        self.assertIn('onclick="openLatestPredictionResults()"', html)
        self.assertIn("function showPredictionResultGuide", html)
        self.assertIn("function dismissPredictionResultGuide", html)
        self.assertIn("function clearPredictionResultGuide", html)
        self.assertIn("async function openLatestPredictionResults", html)
        self.assertIn('showView("results")', html)
        self.assertIn("await loadResults()", html)
        self.assertIn("if (predictionRunning && Number(percent) >= 100) showPredictionResultGuide()", html)
        results_view_branch = html[
            html.index('if (name === "results") {'):
            html.index('if (name === "results") {') + 180
        ]
        self.assertIn("clearPredictionResultGuide()", results_view_branch)
        self.assertIn("clearPredictionResultGuide()", html)
        self.assertIn("setTimeout(dismissPredictionResultGuide, 12000)", html)

    def test_app_has_first_run_sidebar_overview_tour(self):
        html = self.read_app()
        self.assertIn('id="tour-overlay"', html)
        self.assertIn('id="tour-spotlight"', html)
        self.assertIn('id="tour-card"', html)
        self.assertIn("const tourDefinitions", html)
        self.assertIn("appOverview", html)
        self.assertIn("Prediction Workspace", html)
        self.assertIn("Feature Generation", html)
        self.assertIn("Results Explorer", html)
        self.assertIn("Data Analysis", html)
        self.assertIn("Log Console", html)
        self.assertIn("asset.skipAppOverviewTour", html)
        self.assertIn("Do not show this guide again", html)
        self.assertIn('startTour("appOverview")', html)
        self.assertIn("async function loadTourPreferences", html)
        self.assertIn("async function persistTourPreference", html)
        self.assertIn("window.pywebview.api.get_ui_preferences()", html)
        self.assertIn("window.pywebview.api.save_ui_preferences", html)
        self.assertIn("async function waitForPywebviewApi", html)
        self.assertIn("await loadTourPreferences()", html)

    def test_prediction_workspace_has_contextual_tour(self):
        html = self.read_app()
        self.assertIn("predictionWorkspace", html)
        self.assertIn("asset.skipPredictionWorkspaceTour", html)
        self.assertIn('data-tour-target="prediction-parameters"', html)
        self.assertIn('data-tour-target="prediction-area"', html)
        self.assertIn('data-tour-target="prediction-run"', html)
        self.assertIn('data-tour-target="prediction-reset"', html)
        self.assertIn('data-tour-target="prediction-draw-area"', html)
        self.assertIn("Enter the radio, antenna, model, and database settings required for prediction.", html)
        self.assertIn("Use the map tool to define the prediction boundary when map-bound mode is selected.", html)
        self.assertIn('if (name === "prediction") maybeStartPredictionWorkspaceTour()', html)

    def test_model_training_has_contextual_tour(self):
        html = self.read_app()
        self.assertIn("modelTraining", html)
        self.assertIn("asset.skipModelTrainingTour", html)
        self.assertIn('data-tour-target="training-model-settings"', html)
        self.assertIn('data-tour-target="training-feature-vector-files"', html)
        self.assertIn('data-tour-target="training-generate-mode"', html)
        self.assertIn('data-tour-target="training-open-guide"', html)
        self.assertIn('data-tour-target="training-generate-model"', html)
        self.assertIn('data-tour-target="training-reset"', html)
        self.assertIn("Confirm the model source, learning strategy, freeze layer, learning rate, and judge-model option before training.", html)
        self.assertIn("Select one or more .xz feature vector files, or open Feature Generation when vectors still need to be prepared.", html)
        self.assertIn("Choose local single-machine training or provide a Dask scheduler for distributed execution.", html)
        self.assertIn("Open the distributed learning guide before using Dask workers on other computers.", html)
        self.assertIn("Start model generation after the settings and feature vectors are ready.", html)
        self.assertIn("Stop the current training task if needed and clear model-training state after completion.", html)
        self.assertIn('if (name === "training") maybeStartModelTrainingTour()', html)

    def test_prediction_workspace_tour_locks_page_scroll(self):
        html = self.read_app()
        self.assertIn(".tour-scroll-locked", html)
        self.assertIn("let tourScrollY = 0", html)
        self.assertIn("function setTourScrollLock(isLocked)", html)
        self.assertIn('document.body.classList.toggle("tour-scroll-locked", isLocked)', html)
        self.assertIn("setTourScrollLock(true)", html)
        self.assertIn("function preventTourScroll(event)", html)
        self.assertIn("if (!activeTourName) return", html)
        self.assertIn('window.addEventListener("wheel", preventTourScroll, { passive: false })', html)
        self.assertIn('window.addEventListener("touchmove", preventTourScroll, { passive: false })', html)
        self.assertIn('window.addEventListener("keydown", preventTourKeyboardScroll)', html)
        self.assertIn("setTourScrollLock(false)", html)

    def test_tour_layer_stays_above_app_components(self):
        html = self.read_app()
        self.assertIn("z-index: 10000", html)
        self.assertIn("z-index: 10001", html)
        self.assertIn("z-index: 10002", html)

    def test_reset_stops_backend_and_clears_inputs_and_logs(self):
        html = self.read_app()
        self.assertIn("async function resetPrediction", html)
        self.assertIn("await window.pywebview.api.reset_temp_data()", html)
        self.assertIn("resetPredictionInputs()", html)
        self.assertIn("clearTerminal()", html)
        self.assertIn('document.getElementById("p-predictDataSelect").value = "predictData_map"', html)
        self.assertIn('document.getElementById("terminal-content-main").textContent = "> ASSET suite initialized"', html)

    def test_csv_prediction_mode_locks_mesh_dimensions(self):
        html = self.read_app()
        self.assertIn("function setMeshControlsLocked", html)
        self.assertIn('document.getElementById("p-mesh-lng").disabled = locked', html)
        self.assertIn('document.getElementById("p-mesh-lat").disabled = locked', html)
        self.assertIn('predictMode === "predictData_file"', html)

    def test_app_suite_has_professional_splash_animation(self):
        html = self.read_app()
        self.assertIn('id="splash-screen"', html)
        self.assertIn("ASSET Framework", html)
        self.assertIn("splashExitMs = 3800", html)
        self.assertIn("function dismissSplash", html)
        self.assertIn("setTimeout(dismissSplash, splashExitMs)", html)
        self.assertIn("@keyframes signalSweep", html)

    def test_results_map_hidden_until_results_are_loaded(self):
        html = self.read_app()
        self.assertIn('id="result-empty-state"', html)
        self.assertIn('class="panel hidden" id="result-map-panel"', html)
        self.assertIn('document.getElementById("result-map-panel").classList.remove("hidden")', html)
        self.assertIn('document.getElementById("result-empty-state").classList.add("hidden")', html)
        self.assertIn('document.getElementById("result-map-panel").classList.add("hidden")', html)

    def test_results_explorer_uses_mesh_area_map_with_prediction_value_legend(self):
        html = self.read_app()
        self.assertNotIn("leaflet-heat", html)
        self.assertIn('id="result-legend"', html)
        self.assertIn("Median RSS", html)
        self.assertIn("result-legend-gradient", html)
        self.assertIn("result-legend-labels", html)
        self.assertIn("function renderResultMeshMap", html)
        self.assertIn("function createInterpolatedMeshCanvasLayer", html)
        self.assertIn("function drawInterpolatedMeshCanvas", html)
        self.assertIn("function interpolateMeshValue", html)
        self.assertIn("function renderResultLegend", html)
        self.assertIn("const meshCanvasOpacity = 0.58", html)
        self.assertIn("canvasContext.globalAlpha = meshCanvasOpacity", html)
        self.assertIn("bilinear", html)
        self.assertNotIn("L.rectangle", html)
        self.assertIn("continuous mesh loaded", html)

    def test_results_explorer_uses_point_map_for_csv_prediction_results(self):
        html = self.read_app()
        self.assertIn("function getPredictionResultMode", html)
        self.assertIn('getPredictionResultMode(rawData) === "predictData_map"', html)
        self.assertIn("function renderResultPointMap", html)
        self.assertIn("L.circleMarker", html)
        self.assertIn("points loaded", html)
        self.assertIn("Prediction_Result_Mode", html)

    def test_results_explorer_has_uncertainty_mesh_subview(self):
        html = self.read_app()
        self.assertIn('data-result-layer="prediction"', html)
        self.assertIn('data-result-layer="uncertainty"', html)
        self.assertIn('id="uncertainty-eta"', html)
        self.assertIn('id="uncertainty-status"', html)
        self.assertIn("function showResultLayer", html)
        self.assertIn("function renderUncertaintyLayer", html)
        self.assertIn("function classifyUncertaintyValue", html)
        self.assertIn("function getUncertaintyColor", html)
        self.assertIn("Uncertainty", html)
        self.assertIn("Top-η", html)
        self.assertIn("Bottom-η", html)
        self.assertIn("uncertaintyMeshOpacity", html)
        self.assertIn("rgba(231, 76, 60", html)
        self.assertIn("rgba(39, 174, 96", html)
        self.assertIn("rgba(52, 152, 219", html)
        self.assertIn("Math.min(0.5, Math.max(0, eta))", html)

    def test_prediction_parameters_can_be_temporarily_saved_and_reloaded_after_reset(self):
        html = self.read_app()
        self.assertIn("Save Params", html)
        self.assertIn("Reload Params", html)
        self.assertIn("let savedPredictionParams = null", html)
        self.assertIn("const predictionParamIds", html)
        self.assertIn("function savePredictionParams", html)
        self.assertIn("function reloadPredictionParams", html)
        self.assertIn("savedPredictionParams = capturePredictionParams()", html)
        self.assertIn("applyPredictionParams(savedPredictionParams)", html)
        self.assertIn('"min-lng"', html)
        self.assertIn('"max-lat"', html)

    def test_dataset_prep_has_own_parameters_and_temporary_save_reload(self):
        html = self.read_app()
        self.assertIn("<h3>Dataset Parameters</h3>", html)
        self.assertIn('id="dataset-param-cache-status"', html)
        self.assertIn('onclick="saveDatasetParams()"', html)
        self.assertIn('onclick="reloadDatasetParams()"', html)
        self.assertIn("let savedDatasetParams = null", html)
        self.assertIn("const datasetParamIds", html)
        for field_id in [
            "d-frequency",
            "d-SF",
            "d-EIRP",
            "d-fixAntenna_lng",
            "d-fixAntenna_lat",
            "d-fixAntenna_alt",
            "d-fixAntenna_height",
            "d-moveAntenna_height",
        ]:
            self.assertIn(f'id="{field_id}"', html)
            self.assertIn(f'"{field_id}"', html)
        self.assertIn("function saveDatasetParams", html)
        self.assertIn("function reloadDatasetParams", html)
        self.assertIn("savedDatasetParams = captureDatasetParams()", html)
        self.assertIn("applyDatasetParams(savedDatasetParams)", html)
        self.assertIn('frequency: document.getElementById("d-frequency").value', html)
        self.assertIn('moveAntenna_height: document.getElementById("d-moveAntenna_height").value', html)

    def test_model_training_and_dataset_prep_have_reset_defaults(self):
        html = self.read_app()
        self.assertIn('onclick="resetModelTraining()"', html)
        self.assertIn('onclick="resetDatasetPrep()"', html)
        self.assertIn("async function resetModelTraining", html)
        self.assertIn("async function resetDatasetPrep", html)
        self.assertIn('document.getElementById("m-isGenFV").value = "yes"', html)
        self.assertIn('document.getElementById("m-model").value = "noModel"', html)
        self.assertIn("selectedPaths.fv = []", html)
        self.assertIn("selectedPaths.csv = []", html)
        self.assertIn("selectedPaths.altitude = []", html)
        self.assertIn("selectedPaths.building = []", html)
        self.assertIn("selectedPaths.landuse = []", html)
        self.assertIn('document.getElementById("dataset-status").textContent = "Waiting for files"', html)
        self.assertIn('document.getElementById("d-frequency").value = "920"', html)
        self.assertIn('document.getElementById("d-SF").value = "0"', html)
        self.assertIn('document.getElementById("dataset-param-cache-status").textContent = "Not saved"', html)
        self.assertIn('document.getElementById("fv-status").textContent = "None selected"', html)
        self.assertGreaterEqual(html.count('updateProgress(0, "Ready")'), 4)
        self.assertGreaterEqual(html.count("await window.pywebview.api.reset_temp_data()"), 3)

    def test_generate_feature_vectors_locks_feature_vector_files_and_guides_to_dataset_prep(self):
        html = self.read_app()
        self.assertIn('onchange="toggleFeatureVectorFiles()"', html)
        self.assertIn('id="feature-vector-panel"', html)
        self.assertIn('id="feature-vector-file-assets"', html)
        self.assertIn('id="feature-vector-guidance"', html)
        self.assertIn("function toggleFeatureVectorFiles", html)
        self.assertIn('const shouldLock = mode === "yes"', html)
        self.assertIn('document.getElementById("feature-vector-file-assets").classList.toggle("locked-panel", shouldLock)', html)
        self.assertNotIn('document.getElementById("feature-vector-panel").classList.toggle("locked-panel", shouldLock)', html)
        self.assertIn('document.getElementById("feature-vector-select-btn").disabled = shouldLock', html)
        self.assertIn("showView('dataset')", html)
        self.assertIn("Generate feature vectors in Feature Generation first.", html)

    def test_generate_feature_vectors_locks_generate_model_and_controls_dataset_prep_access(self):
        html = self.read_app()
        self.assertIn('id="generate-model-btn"', html)
        self.assertIn('document.getElementById("generate-model-btn").disabled = shouldLock', html)
        self.assertIn('<button class="ghost-btn" id="open-dataset-prep-btn" onclick="showView(\'dataset\')">Open Feature Generation</button>', html)
        self.assertIn('document.getElementById("open-dataset-prep-btn").disabled = !shouldLock', html)

    def test_model_training_has_animated_training_visual(self):
        html = self.read_app()
        self.assertIn('id="training-visual"', html)
        self.assertIn('class="training-visual idle"', html)
        self.assertIn("Neural Training Flow", html)
        self.assertIn("training-flow-line", html)
        self.assertNotIn("Loss trend", html)
        self.assertNotIn("training-loss-line", html)
        self.assertIn("@keyframes trainingPulse", html)
        self.assertIn("@keyframes signalPacket", html)
        self.assertIn("setTrainingVisualState", html)
        self.assertIn('document.getElementById("training-visual").className = `training-visual ${state}`', html)
        self.assertIn('setTrainingVisualState(isLocked ? "active" : "idle")', html)
        self.assertIn('setTrainingVisualState("complete")', html)

    def test_visible_parameters_have_hover_help_documentation(self):
        html = self.read_app()
        self.assertIn("parameter-help", html)
        self.assertIn("help-tooltip", html)
        self.assertIn('[role="tooltip"]', html)
        self.assertIn(".parameter-help:hover .help-tooltip", html)
        self.assertIn(".parameter-help:focus .help-tooltip", html)
        for field_id in [
            "p-model",
            "p-database",
            "p-predictDataSelect",
            "p-mesh-lng",
            "p-mesh-lat",
            "p-frequency",
            "p-SF",
            "p-EIRP",
            "p-fixAntenna_alt",
            "p-fixAntenna_lng",
            "p-fixAntenna_lat",
            "p-fixAntenna_height",
            "p-moveAntenna_height",
            "m-isGenFV",
            "m-scheduler",
            "m-model",
            "m-numCore1",
            "m-learningType",
            "m-trainJudgeModel",
            "m-freezeLayer",
            "m-learningRate",
            "d-frequency",
            "d-SF",
            "d-EIRP",
            "d-fixAntenna_lng",
            "d-fixAntenna_lat",
            "d-fixAntenna_alt",
            "d-fixAntenna_height",
            "d-moveAntenna_height",
            "d-training-csv",
            "d-altitude-map",
            "d-building-map",
            "d-city-type-map",
        ]:
            self.assertIn(f'data-help-for="{field_id}"', html)
        self.assertIn("Training CSV files must include longitude and latitude columns.", html)
        self.assertIn("Example longitude columns: longitude, lon, lng, or x.", html)
        self.assertIn("Example latitude columns: latitude, lat, or y.", html)
        self.assertIn("Example RSSI columns: RSSI or rssi.", html)

    def test_open_guide_shows_distributed_learning_guide(self):
        html = self.read_app()
        self.assertIn('onclick="openDistributedGuide()"', html)
        self.assertIn('id="distributed-guide-modal"', html)
        self.assertIn("Distributed Learning Guide", html)
        self.assertIn("Prerequisites", html)
        self.assertIn("Install Dask Distributed on every worker computer", html)
        self.assertIn('python -m pip install "dask[distributed]" --upgrade', html)
        self.assertIn('python -c "import dask, distributed; print(dask.__version__, distributed.__version__)"', html)
        self.assertIn("ulimit -n 10000", html)
        self.assertIn("dask scheduler --host 192.168.1.200", html)
        self.assertIn("dask worker tcp://192.168.199.1:8786 --nworkers 12 --nthreads 1 --name MacPro_alpha --memory-limit 14GB", html)
        self.assertIn("dask worker tcp://192.168.199.1:8786 --nworkers 12 --nthreads 1 --name MacPro_beta --memory-limit 14GB", html)
        self.assertIn("dask worker tcp://192.168.199.1:8786 --nworkers 6 --nthreads 1 --name MacPro_shan --memory-limit 14GB", html)
        self.assertIn("tcp://192.168.199.1:8786", html)
        self.assertIn("Paste the scheduler address into Model Training / Scheduler", html)
        for explanation in [
            "--host",
            "--nworkers",
            "--nthreads",
            "--name",
            "--memory-limit",
            "worker count",
            "scheduler address",
        ]:
            self.assertIn(explanation, html)
        self.assertIn("If ASSET cannot connect to the scheduler, training continues in single-machine mode.", html)
        self.assertIn("copyGuideCommand", html)
        self.assertGreaterEqual(html.count('data-guide-copy='), 5)
        self.assertIn("function openDistributedGuide", html)
        self.assertIn("function closeDistributedGuide", html)
        self.assertIn("function loadAndShowPdf", html)
        self.assertNotIn("Open PDF Guide", html)
        self.assertNotIn('onclick="loadAndShowPdf()"', html)

    def test_base_model_choice_locks_training_controls_by_mode(self):
        html = self.read_app()
        self.assertIn('id="m-model" onchange="toggleModelTrainingControls()"', html)
        self.assertIn('id="m-learningType" onchange="toggleModelTrainingControls()"', html)
        self.assertIn("function toggleModelTrainingControls", html)
        self.assertIn('const isNewModel = document.getElementById("m-model").value === "noModel"', html)
        self.assertIn('const isTransferLearning = document.getElementById("m-learningType").value === "type_TL"', html)
        self.assertIn('document.getElementById("m-learningType").disabled = modelTrainingLocked || isNewModel', html)
        self.assertIn('document.getElementById("m-freezeLayer").disabled = modelTrainingLocked || isNewModel', html)
        self.assertIn('document.getElementById("m-numCore1").disabled = modelTrainingLocked || !isNewModel', html)
        self.assertIn('document.getElementById("m-learningRate").disabled = modelTrainingLocked || !isNewModel', html)
        self.assertIn('id="m-trainJudgeModel"', html)
        self.assertIn('type="checkbox"', html)
        self.assertIn('document.getElementById("m-trainJudgeModel").checked = false', html)
        self.assertIn('document.getElementById("m-trainJudgeModel").disabled = !canTrainJudge', html)
        self.assertIn('const canTrainJudge = !modelTrainingLocked && !isNewModel && isTransferLearning', html)
        self.assertIn('trainJudgeModel: document.getElementById("m-trainJudgeModel").checked', html)
        self.assertIn(".switch-input", html)
        self.assertIn("width: 1px;", html)
        self.assertIn("height: 1px;", html)
        self.assertIn("margin: 0;", html)
        self.assertIn("toggleModelTrainingControls();", html)

    def test_model_training_stays_locked_after_generation_until_reset(self):
        html = self.read_app()
        self.assertIn("let modelTrainingLocked = false", html)
        self.assertIn('const allowedViewsDuringTraining = new Set(["training", "logs"])', html)
        self.assertIn("function setModelTrainingLocked", html)
        self.assertIn("setModelTrainingLocked(true)", html)
        self.assertIn("setModelTrainingLocked(false)", html)
        self.assertIn("button.disabled = modelTrainingLocked && !allowedViewsDuringTraining.has(button.dataset.view)", html)
        self.assertIn("Model training is running. Only Model Training and Log Console remain available.", html)
        self.assertIn('document.querySelectorAll("#view-training input, #view-training select, #view-training button")', html)
        self.assertNotIn('button:not([data-training-reset])', html)
        self.assertIn("control.disabled = modelTrainingLocked", html)
        self.assertIn('if (modelTrainingLocked && Number(percent) >= 100) setModelTrainingLocked(false)', html)
        self.assertIn("if (selectedPaths.fv.length === 0)", html)
        self.assertIn("Select feature vector files before generating a model.", html)
        self.assertIn("if (modelTrainingLocked) return", html)
        self.assertIn("modelTrainingLocked || isNewModel", html)
        self.assertIn("modelTrainingLocked || !isNewModel", html)

    def test_dataset_prep_locks_workspace_while_processing_and_exposes_download(self):
        html = self.read_app()
        self.assertIn("let datasetProcessing = false", html)
        self.assertIn("let datasetOutputReady = false", html)
        self.assertIn('new Set(["dataset", "logs"])', html)
        self.assertIn("function setDatasetProcessing", html)
        self.assertIn("setDatasetProcessing(true)", html)
        self.assertIn("setDatasetProcessing(false)", html)
        self.assertIn('document.getElementById("download-dataset-output-btn").classList.remove("hidden")', html)
        self.assertIn('id="download-dataset-output-btn"', html)
        self.assertIn("function downloadDatasetOutput", html)
        self.assertIn("window.pywebview.api.download_dataset_output()", html)
        self.assertIn("if (datasetProcessing && !allowedViewsDuringDataset.has(name))", html)
        self.assertIn('id="upload-dataset-process-btn"', html)
        self.assertIn("datasetOutputReady = true", html)
        self.assertIn("datasetOutputReady = false", html)
        self.assertIn('document.getElementById("upload-dataset-process-btn").disabled = datasetProcessing || datasetOutputReady', html)
        self.assertIn("Feature generation completed. Download the output or reset to process another dataset.", html)
        self.assertIn('id="dataset-output-guide"', html)
        self.assertIn("function showDatasetOutputGuide", html)
        self.assertIn("function clearDatasetOutputGuide", html)
        self.assertIn('document.getElementById("download-dataset-output-btn").scrollIntoView', html)
        self.assertIn('document.getElementById("download-dataset-output-btn").classList.add("next-action-highlight")', html)
        self.assertIn("showDatasetOutputGuide()", html)
        self.assertIn("clearDatasetOutputGuide()", html)
        self.assertIn("@keyframes nextActionPulse", html)
        self.assertIn("Output is ready. Download the generated dataset, or reset to process another one.", html)

    def test_dataset_processing_completion_does_not_ask_to_process_another_dataset(self):
        html = self.read_app()
        main_source = (ROOT / "main.py").read_text(encoding="utf-8")
        self.assertNotIn("Process another dataset?", html)
        self.assertNotIn("Process another dataset?", main_source)
        self.assertNotIn("create_confirmation_dialog('Confirmation'", main_source)
        self.assertNotIn("user_choice", main_source)


if __name__ == "__main__":
    unittest.main()
