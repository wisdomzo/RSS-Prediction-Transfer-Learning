# Real App Suite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the ASSET product-suite redesign into a real pywebview app that preserves the current prediction, training, dataset, result, file-picker, PDF, reset, and export functionality.

**Architecture:** Add a new `web/app-suite.html` as the next-generation UI shell, wired directly to existing `window.pywebview.api.*` calls and compatible global callbacks such as `updateProgress()` and `updateTerminal()`. Keep `web/index.html` untouched until the new shell is contract-tested, then switch `main.py` to load the new shell in a small final step.

**Tech Stack:** Python `unittest` for static contract tests, pywebview bridge APIs from `main.py`, vanilla HTML/CSS/JavaScript, Leaflet and Leaflet Draw loaded from the existing CDN pattern.

---

### Task 1: Static Contract Test For Real UI Wiring

**Files:**
- Create: `tests/test_app_suite_static.py`
- Create: `web/app-suite.html`

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "web" / "app-suite.html"


def read_app():
    return APP.read_text(encoding="utf-8")


def test_app_suite_file_exists():
    assert APP.exists()


def test_app_suite_wires_existing_pywebview_api_contract():
    html = read_app()
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
        assert f"window.pywebview.api.{call}" in html or f"pywebview.api.{call}" in html


def test_app_suite_exposes_backend_progress_callbacks():
    html = read_app()
    assert "function updateProgress" in html
    assert "function updateTerminal" in html


def test_app_suite_contains_product_suite_views():
    html = read_app()
    for label in [
        "Prediction Workspace",
        "Model Training",
        "Dataset Prep",
        "Results Explorer",
        "Dask Cluster",
        "Model Registry",
        "Export Center",
    ]:
        assert label in html
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_app_suite_static -v`

Expected: FAIL because `web/app-suite.html` does not exist yet.

- [ ] **Step 3: Create minimal real UI shell**

Create `web/app-suite.html` with:
- navigation for the product-suite modules
- real Prediction form fields matching the current backend `coords`
- real Model Training fields matching `executeModelGeneration(coords)`
- real Dataset Prep path selection and upload/data-processing calls
- real Result view calling `get_prediction_data()` and `download_csv()`
- global `updateProgress(percent, status)` and `updateTerminal(message)` callbacks

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_app_suite_static -v`

Expected: PASS with all contract tests green.

### Task 2: Entrypoint Switch

**Files:**
- Modify: `main.py`

- [ ] **Step 1: Keep old UI recoverable**

Change `html_path = get_resource_path("web/index.html")` to prefer `web/app-suite.html` only after Task 1 passes.

- [ ] **Step 2: Smoke-check app entry source**

Run: `python3 -m unittest tests.test_app_suite_static -v`

Expected: PASS.

### Task 3: Manual Runtime QA

**Files:**
- No code changes unless QA exposes a bug.

- [ ] **Step 1: Start the app**

Run: `python3 main.py`

Expected: pywebview opens `ASSET Framework` with the new suite shell.

- [ ] **Step 2: Exercise core paths**

Verify:
- Prediction can call `executeRssPrediction(coords)`
- `updateProgress()` visibly updates Runtime Monitor
- `updateTerminal()` appends log lines
- Dataset Prep can call native file selection and `upload_csv_files(...)`
- Model Training can call `executeModelGeneration(coords)`
- Results Explorer can load `get_prediction_data()` and call `download_csv()`
