import ast
from pathlib import Path
import re
import tokenize
import unittest


ROOT = Path(__file__).resolve().parents[1]
CJK_RE = re.compile(r"[\u3040-\u30ff\u3400-\u9fff\uac00-\ud7af]")
EXCLUDED_DIRS = {".git", ".venv", "build", "dist", "report", "tmp", "__pycache__"}


def source_files(suffixes):
    for path in ROOT.rglob("*"):
        if path.suffix.lower() not in suffixes:
            continue
        if any(part in EXCLUDED_DIRS for part in path.relative_to(ROOT).parts):
            continue
        yield path


def python_docstrings(tree):
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if not isinstance(body, list) or not body:
            continue
        first_statement = body[0]
        if (
            isinstance(first_statement, ast.Expr)
            and isinstance(first_statement.value, ast.Constant)
            and isinstance(first_statement.value.value, str)
        ):
            yield first_statement.lineno, first_statement.value.value


def called_function_name(call):
    if isinstance(call.func, ast.Name):
        return call.func.id
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    return ""


class EnglishSourceTests(unittest.TestCase):
    def test_python_comments_and_docstrings_are_english_only(self):
        offenders = []
        for path in source_files({".py"}):
            relative = path.relative_to(ROOT)
            with path.open("rb") as source:
                for token in tokenize.tokenize(source.readline):
                    if token.type == tokenize.COMMENT and CJK_RE.search(token.string):
                        offenders.append(f"{relative}:{token.start[0]}:{token.string.strip()}")

            source_text = path.read_text(encoding="utf-8")
            for line_no, docstring in python_docstrings(ast.parse(source_text, filename=str(relative))):
                if CJK_RE.search(docstring):
                    offenders.append(f"{relative}:{line_no}:docstring")

        self.assertEqual([], offenders)

    def test_python_user_facing_messages_are_english_only(self):
        user_facing_calls = {
            "alert",
            "create_confirmation_dialog",
            "input",
            "input_with_default",
            "print",
            "updateProgress",
            "updateTerminal",
        }
        offenders = []
        for path in source_files({".py"}):
            relative = path.relative_to(ROOT)
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(relative))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call) or called_function_name(node) not in user_facing_calls:
                    continue
                for argument in node.args:
                    for child in ast.walk(argument):
                        if (
                            isinstance(child, ast.Constant)
                            and isinstance(child.value, str)
                            and CJK_RE.search(child.value)
                        ):
                            offenders.append(
                                f"{relative}:{node.lineno}:{called_function_name(node)}:{child.value}"
                            )

        self.assertEqual([], offenders)

    def test_frontend_and_scripts_are_english_only(self):
        offenders = []
        checked_roots = (ROOT / "web", ROOT / "design-preview")
        suffixes = {".html", ".css", ".js"}
        paths = [
            path
            for checked_root in checked_roots
            if checked_root.exists()
            for path in checked_root.rglob("*")
            if path.suffix.lower() in suffixes
        ]
        paths.extend(source_files({".sh", ".bat"}))

        for path in paths:
            relative = path.relative_to(ROOT)
            for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                if CJK_RE.search(line):
                    offenders.append(f"{relative}:{line_no}:{line.strip()}")

        self.assertEqual([], offenders)


if __name__ == "__main__":
    unittest.main()
