import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "docs/app-manuals/asset-framework-user-manual-ja.md"
BUILDER = ROOT / "docs/app-manuals/build_asset_manual_pdf.py"


class ManualContentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.markdown = SOURCE.read_text(encoding="utf-8")
        cls.builder = BUILDER.read_text(encoding="utf-8")

    def test_required_product_explanations_are_present(self):
        required = [
            "対象アプリ版: v2.8.4",
            "文書版: v1.3",
            "更新日: 2026年9月17日",
            "General Model M0 (Shinshu Univ. & NICT 202605)",
            "Incremental Training",
            "First-Person View",
            "Train Window View",
            "Aircraft Window View",
            "Boat View",
            "モデルの出力や学習内容には影響しません",
            "不確実さ",
            "FresnelR_H",
            "FresnelR_V",
            "disBtwTxRx",
            "Predicted_Value",
            "pathLoss_eta_2",
            "pathLoss_eta_3",
            "本ソフトウェアで生成したモデルのみ",
            "アプリ開発会社へお問い合わせ",
            "学習の進行に合わせて値を自動的に小さく",
        ]
        for phrase in required:
            self.assertIn(phrase, self.markdown)

    def test_latest_training_features_are_not_marked_as_future(self):
        self.assertNotIn("Incremental Learning` は今後のアップデートで追加予定", self.markdown)
        self.assertNotIn("General Model M0 (NICT 202605)", self.markdown)

    def test_removed_reader_label_is_absent(self):
        self.assertNotIn("対象読者", self.markdown)

    def test_hiragino_fonts_are_configured(self):
        self.assertIn('local("HiraKakuProN-W3")', self.builder)
        self.assertIn('local("HiraKakuProN-W6")', self.builder)
        self.assertIn("font-weight: 300", self.builder)
        self.assertIn("font-weight: 600", self.builder)
        self.assertIn("--print-to-pdf", self.builder)

    def test_cover_uses_full_page_template(self):
        self.assertIn("@page cover", self.builder)
        self.assertIn("margin: 0", self.builder)
        self.assertIn("page: cover", self.builder)


if __name__ == "__main__":
    unittest.main()
