import csv
import tempfile
import unittest
from pathlib import Path

import predict_area


class PredictionCsvTests(unittest.TestCase):
    def test_prediction_csv_accepts_coordinate_columns_without_rssi(self):
        with tempfile.TemporaryDirectory() as source_dir, tempfile.TemporaryDirectory() as target_dir:
            source_path = Path(source_dir) / "points.csv"
            source_path.write_text(
                "lon,lat,label\n"
                "137.95,35.83,A\n"
                "137.96,35.84,B\n",
                encoding="utf-8",
            )

            copied = predict_area.copy_prediction_data(str(source_path), target_dir)

            self.assertTrue(copied)
            output_path = Path(target_dir) / "points.csv"
            with output_path.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))

            self.assertEqual(["Longitude", "Latitude", "RSSI"], list(rows[0].keys()))
            self.assertEqual("137.95", rows[0]["Longitude"])
            self.assertEqual("35.83", rows[0]["Latitude"])
            self.assertEqual("-999", rows[0]["RSSI"])

    def test_prediction_csv_rejects_files_without_coordinate_columns(self):
        with tempfile.TemporaryDirectory() as source_dir, tempfile.TemporaryDirectory() as target_dir:
            source_path = Path(source_dir) / "bad.csv"
            source_path.write_text("RSSI,Prediction\n-90,-88\n", encoding="utf-8")

            copied = predict_area.copy_prediction_data(str(source_path), target_dir)

            self.assertFalse(copied)
            self.assertFalse((Path(target_dir) / "bad.csv").exists())


if __name__ == "__main__":
    unittest.main()
