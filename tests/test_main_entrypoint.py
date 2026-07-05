from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "main.py"
SUBFUN = ROOT / "subFun.py"
SUBFUN_TL = ROOT / "subFun_TL.py"
TRANSFER_LEARNING_MAIN = ROOT / "transfer_learning_main.py"
NON_ENGLISH_LOG_RE = re.compile(r"[\u3040-\u30ff\u3400-\u9fff]")
LOG_OUTPUT_RE = re.compile(r"(print\(|evaluate_js\(|updateProgress\(|alert\(|desc\s*=)")
APP_LOG_OUTPUT_FILES = [
    "main.py",
    "subFun.py",
    "subFun_TL.py",
    "transfer_learning_main.py",
    "training_history_database.py",
    "training_judge_model.py",
    "predict_area.py",
    "qgis_processor.py",
    "main_collect_data.py",
]


class MainEntrypointTests(unittest.TestCase):
    def test_main_defaults_to_app_suite_with_env_override(self):
        source = MAIN.read_text(encoding="utf-8")
        self.assertIn("ASSET_UI_ENTRY", source)
        self.assertIn('"web/app-suite.html"', source)
        self.assertIn("get_resource_path(ui_entry)", source)

    def test_main_starts_resizable_without_auto_maximize(self):
        source = MAIN.read_text(encoding="utf-8")
        window_call = source[source.index("webview.create_window("):source.index("window.expose(executeRssPrediction)")]
        self.assertNotIn("window.maximize()", source)
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

    def test_model_training_reset_terminates_active_training_process(self):
        source = MAIN.read_text(encoding="utf-8")
        self.assertIn("current_model_training_process", source)
        self.assertIn("def terminate_current_model_training", source)
        self.assertIn("_model_training_process_entry", source)
        self.assertIn("_monitor_model_training_process", source)
        self.assertIn("terminate_current_model_training()", source)
        self.assertIn("current_model_training_process = multiprocessing.Process", source)
        self.assertIn('coords["custom_model_path"] = custom_model_path', source)
        model_training_process_block = source[
            source.index("current_model_training_process = multiprocessing.Process"):
            source.index("current_model_training_process.start()")
        ]
        self.assertNotIn("daemon=True", model_training_process_block)

    def test_model_training_process_connects_dask_inside_child_process(self):
        source = MAIN.read_text(encoding="utf-8")
        process_entry = source[
            source.index("def _model_training_process_entry"):
            source.index("def _monitor_prediction_process")
        ]
        self.assertIn("client = connect_to_existing_cluster(coords)", process_entry)
        self.assertIn("start_dask_log_proxy()", process_entry)
        self.assertLess(
            process_entry.index("connect_to_existing_cluster(coords)"),
            process_entry.index("worker_thread_modelGen")
        )

    def test_process_log_payloads_are_forwarded_directly_to_app_terminal(self):
        source = MAIN.read_text(encoding="utf-8")
        self.assertIn("def forward_process_log_to_app", source)
        self.assertIn("updateTerminal", source)
        self.assertIn("json.dumps(str(payload))", source)
        model_monitor = source[
            source.index("def _monitor_model_training_process"):
            source.index("def terminate_current_prediction")
        ]
        self.assertIn("forward_process_log_to_app(payload)", model_monitor)
        self.assertNotIn("print(payload)", model_monitor)

    def test_single_machine_training_workers_forward_stdout_to_app_queue(self):
        source = SUBFUN_TL.read_text(encoding="utf-8")
        self.assertIn("def init_local_training_worker_logging", source)
        self.assertIn("class QueueStream", source)
        self.assertIn("sys.stdout = QueueStream(log_queue)", source)
        self.assertIn("sys.stderr = QueueStream(log_queue)", source)
        self.assertIn("log_queue = getattr(api_instance, \"queue\", None)", source)
        self.assertIn("initializer=init_local_training_worker_logging", source)
        self.assertIn("initargs=(log_queue,)", source)

    def test_dataset_output_download_is_exposed(self):
        source = MAIN.read_text(encoding="utf-8")
        self.assertIn("def download_dataset_output", source)
        self.assertIn('download_model("ML_")', source)
        self.assertIn("window.expose(download_dataset_output)", source)

    def test_picklable_filter_skips_multiprocessing_queue_runtime_error(self):
        source = SUBFUN.read_text(encoding="utf-8")
        self.assertIn("def is_picklable", source)
        self.assertIn("except Exception:", source)

    def test_transfer_learning_judge_training_is_optional(self):
        main_source = MAIN.read_text(encoding="utf-8")
        transfer_source = TRANSFER_LEARNING_MAIN.read_text(encoding="utf-8")
        self.assertIn("train_judge_model = bool(coords.get('trainJudgeModel', False))", main_source)
        self.assertIn("train_judge_model = train_judge_model", main_source)
        self.assertIn("train_judge_model=False", transfer_source)
        self.assertIn('should_train_judge = learning_type == "type_TL" and train_judge_model', transfer_source)
        self.assertIn("if should_train_judge:", transfer_source)
        self.assertIn("subFun.barrier_and_cleanup(futures_to_wait=predictRSSI_TL)", transfer_source)
        self.assertIn("subFun_TL.trainJudgeModel_cnn", transfer_source)
        self.assertIn('print("Judge model training...Skipped.")', transfer_source)

    def test_application_log_output_is_english(self):
        offenders = []
        for file_name in APP_LOG_OUTPUT_FILES:
            path = ROOT / file_name
            for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                if LOG_OUTPUT_RE.search(line) and NON_ENGLISH_LOG_RE.search(line):
                    offenders.append(f"{path.name}:{line_no}:{line.strip()}")

        self.assertEqual([], offenders)


if __name__ == "__main__":
    unittest.main()
