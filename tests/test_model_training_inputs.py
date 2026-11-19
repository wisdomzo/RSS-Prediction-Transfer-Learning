import ast
import json
import os
from pathlib import Path
import queue
import shutil
import tempfile
import unittest
from unittest.mock import Mock


ROOT = Path(__file__).resolve().parents[1]


def training_namespace():
    # Exercise the actual entry functions without importing GUI/TensorFlow runtimes.
    tree = ast.parse((ROOT / "main.py").read_text())
    names = {"copy_selected_files", "worker_thread_modelGen", "_model_training_process_entry"}
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
    namespace = {
        "os": os, "shutil": shutil, "json": json, "APP_ROOT": str(ROOT),
        "window": Mock(), "subFun": Mock(), "transfer_learning_main": Mock(),
        "training_history_database": Mock(),
    }
    exec(compile(ast.Module(body=functions, type_ignores=[]), "main.py", "exec"), namespace)
    return namespace


class ModelTrainingInputTests(unittest.TestCase):
    def test_selected_files_reach_both_trainers_without_filename_filter(self):
        for model in ("NICT_latest_model", "noModel"):
            with self.subTest(model=model), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                destination = root / "temp"
                destination.mkdir()
                stale = destination / "ML_myTempExp_stale.pkl.xz"
                stale.write_bytes(b"stale")
                paths = [root / "FV_SF10_920_0427.pkl.xz", root / "renamed.pkl.xz"]
                for path in paths:
                    path.write_bytes(b"selected feature data")
                namespace = training_namespace()
                namespace["get_writable_temp_path"] = lambda: str(destination)
                coords = {
                    "model": model, "selectedPaths": [str(path) for path in paths],
                    "learningType": "DL", "freezeLayer": "9", "learningRate": "0.0001", "numCore1": "1",
                }
                namespace["worker_thread_modelGen"](Mock(), coords, auto_download=False)
                trainer = (namespace["training_history_database"].run_training_history_database
                           if model == "noModel" else namespace["transfer_learning_main"].run_transfer_learning)
                kwargs = trainer.call_args.kwargs
                self.assertEqual(kwargs["data_index"], [1, 2])
                self.assertEqual(kwargs["content_data_index"], [str(destination / path.name) for path in paths])
                for path in kwargs["content_data_index"]:
                    self.assertEqual(Path(path).read_bytes(), b"selected feature data")
                namespace["subFun"].get_ML_files.assert_not_called()

    def test_no_files_or_missing_file_stops_before_training(self):
        with tempfile.TemporaryDirectory() as folder:
            for paths, error in (([], ValueError), ([str(Path(folder) / "missing.xz")], FileNotFoundError)):
                with self.subTest(paths=paths):
                    namespace = training_namespace()
                    namespace["get_writable_temp_path"] = lambda: folder
                    with self.assertRaises(error):
                        namespace["worker_thread_modelGen"](Mock(), {"selectedPaths": paths})
                    namespace["transfer_learning_main"].run_transfer_learning.assert_not_called()
                    namespace["training_history_database"].run_training_history_database.assert_not_called()

    def test_child_reports_error_and_signals_completion(self):
        namespace = training_namespace()
        proxy = Mock()
        namespace.update({
            "sys": Mock(), "ProcessWindowProxy": Mock(return_value=proxy),
            "QueueLogger": Mock(), "connect_to_existing_cluster": Mock(return_value=None),
            "worker_thread_modelGen": Mock(side_effect=ValueError("Invalid 'feature' file")),
        })
        events = queue.Queue()
        namespace["_model_training_process_entry"]({}, events)
        proxy.evaluate_js.assert_called_once_with('updateProgress(-1, "Error: Invalid \'feature\' file")')
        self.assertEqual(events.get_nowait(), {"type": "done", "payload": True})
        self.assertTrue(events.empty())


if __name__ == "__main__":
    unittest.main()
