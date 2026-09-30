import ast
import math
from pathlib import Path
import tempfile
import unittest

import pandas as pd


# Isolate the grid helper from GUI and machine-learning import side effects.
source = Path(__file__).resolve().parents[1] / "predict_area.py"
tree = ast.parse(source.read_text())
helper = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "filter_circle_grid")
namespace = {"pd": pd, "math": math}
exec(compile(ast.Module(body=[helper], type_ignores=[]), str(source), "exec"), namespace)
filter_circle_grid = namespace["filter_circle_grid"]


class CirclePredictionTests(unittest.TestCase):
    def test_center_boundary_and_outside(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "grid.csv"
            boundary = math.degrees(1000 / 6371000)
            pd.DataFrame({"Latitude": [0, boundary, .02], "Longitude": [0, 0, 0], "RSSI": [-999] * 3}).to_csv(path, index=False)
            filter_circle_grid(path, {"lat": 0, "lng": 0, "radius": 1000})
            result = pd.read_csv(path)
            self.assertEqual(len(result), 2)
            self.assertEqual(result.RSSI.tolist(), [-999, -999])

    def test_empty_circle_preserves_original_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "grid.csv"
            pd.DataFrame({"Latitude": [1], "Longitude": [1], "RSSI": [-999]}).to_csv(path, index=False)
            original = path.read_bytes()
            with self.assertRaisesRegex(ValueError, "No grid points"):
                filter_circle_grid(path, {"lat": 0, "lng": 0, "radius": 1})
            self.assertEqual(path.read_bytes(), original)

    def test_invalid_radius(self):
        for radius in [0, -1, float("nan"), float("inf")]:
            with self.subTest(radius=radius), self.assertRaisesRegex(ValueError, "Invalid"):
                filter_circle_grid("unused.csv", {"lat": 0, "lng": 0, "radius": radius})
