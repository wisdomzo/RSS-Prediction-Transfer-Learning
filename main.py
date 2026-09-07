import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'  # 0 shows all messages, 1 suppresses INFO, and 2 suppresses INFO and WARNING.
import sys
import webview
import main_collect_data
import subFun
import subFun_TL
import subprocess
from datetime import datetime
import shutil
import glob
import pandas as pd
import threading
import glob
import pandas as pd
import re
import predict_area
import training_history_database
import transfer_learning_main
import my_plot_figure
import base64
import io
import json
import multiprocessing
from pathlib import Path
from dask.distributed import Client, get_client, Queue
from version_info import resolve_runtime_version


current_prediction_process = None
current_prediction_queue = None
prediction_monitor_thread = None
current_model_training_process = None
current_model_training_queue = None
model_training_monitor_thread = None
PREDICTION_RESULT_MODE_FILE = "predict_RSS_result_mode.json"
UI_PREFERENCES_FILE = "ui_preferences.json"


def connect_to_existing_cluster(coords):
    """
    Establish a resilient Dask connection.

    1. Validate the supplied address.
    2. Add the tcp:// scheme when omitted.
    3. Return safely on an empty address or connection failure so local mode can be used.
    """
    # 1. Retrieve and normalize the address.
    raw_addr = coords.get('scheduler', "").strip()

    # Return None for an empty address; the downstream get_client() failure activates local mode.
    if not raw_addr:
        print(">>> No scheduler address was provided. Running in single-machine mode.")
        return None

    # Normalize the scheme so both "192.168.1.1" and "tcp://192.168.1.1" are accepted.
    if "://" in raw_addr:
        scheduler_addr = raw_addr
    else:
        scheduler_addr = f"tcp://{raw_addr}"

    try:
        # Reuse an existing client to avoid repeated initialization within one session.
        from dask.distributed import Client, get_client
        try:
            client = get_client()
            # Replace the existing client when it is connected to a different address.
            if client.scheduler.address == scheduler_addr:
                print(f">>> Connected to target cluster: {scheduler_addr}")
                return client
            else:
                client.close()
        except:
            pass

        # 2. Prepare the code extraction path (BRIDGE_PATH).
        important_files = [
            'subFun_TL.py', 'subFun.py', 'main_collect_data.py', 'main_multiple_processes.py',
            'predict_area.py', 'training_history_database.py', 'transfer_learning_main.py',
            'main.py', 'my_plot_figure.py', 'paper_functions.py', 'qgis_functions.py'
        ]

        RAW_ROOT = get_app_root_directory()
        # Support the path layout of a packaged macOS application.
        if "Contents/Frameworks" in RAW_ROOT:
            APP_ROOT = RAW_ROOT.replace("Contents/Frameworks", "Contents/Resources")
            BRIDGE_PATH = os.path.join(os.path.expanduser("~"), "Library", "Application Support", "RSS_PredictApp", "tempPythonBridge")
            if not os.path.exists(BRIDGE_PATH): os.makedirs(BRIDGE_PATH)
            # Copy the file into the bridge path.
            for f in important_files:
                src_f = os.path.join(APP_ROOT, f)
                if os.path.exists(src_f): shutil.copy2(src_f, BRIDGE_PATH)
        else:
            BRIDGE_PATH = RAW_ROOT

        # 3. Connect with a five-second timeout so invalid addresses fail quickly.
        print(f">>> Attempting to connect to cluster: {scheduler_addr} ...")
        client = Client(scheduler_addr, timeout="5s")

        # 4. Synchronize code with the remote workers.
        for f in important_files:
            target_f = os.path.join(BRIDGE_PATH, f)
            if os.path.exists(target_f):
                try:
                    # upload_file distributes the script to remote workers.
                    client.upload_file(target_f)
                except Exception:
                    # A local worker may report a harmless file-in-use error.
                    continue

        print(">>> Dask cluster connected and code synchronized successfully.")
        return client

    except Exception as e:
        # Report timeouts, invalid IP addresses, and unreachable networks consistently.
        print(f">>> Unable to connect to cluster ({scheduler_addr}). Error: {e}")
        print(">>> Falling back to single-machine mode.")
        return None

class QueueLogger:
    def __init__(self, queue):
        self.queue = queue
    def write(self, message):
        # Enqueue every nonblank message.
        if message.strip():
            self.queue.put(message)
    def flush(self):
        pass


class ProcessWindowProxy:
    def __init__(self, queue):
        self.queue = queue

    def evaluate_js(self, script):
        self.queue.put({"type": "js", "payload": script})

    def create_file_dialog(self, *args, **kwargs):
        return None


def start_dask_log_proxy():
    remote_q = Queue("app_terminal_logs")

    def _listen():
        while True:
            try:
                msg = remote_q.get()
                print(msg)
            except Exception:
                break

    threading.Thread(target=_listen, daemon=True).start()
    return remote_q


def forward_process_log_to_app(payload):
    message = str(payload).replace("\r", "").strip()
    if not message:
        return
    terminal = getattr(sys, "__stdout__", None)
    if terminal:
        terminal.write(f"{message}\n")
        terminal.flush()
    if window:
        window.evaluate_js(f"updateTerminal({json.dumps(str(payload))})")


def _prediction_process_entry(coords, progress_queue):
    global window
    window = ProcessWindowProxy(progress_queue)
    sys.stdout = QueueLogger(progress_queue)
    sys.stderr = QueueLogger(progress_queue)
    worker_thread(coords)
    progress_queue.put({"type": "done", "payload": True})


def _model_training_process_entry(coords, progress_queue):
    global window
    window = ProcessWindowProxy(progress_queue)
    sys.stdout = QueueLogger(progress_queue)
    sys.stderr = QueueLogger(progress_queue)
    client = connect_to_existing_cluster(coords)
    if client:
        start_dask_log_proxy()
        print(">>> Remote log forwarding is active...")
    model_prefix = worker_thread_modelGen(window, coords, auto_download=False)
    if model_prefix:
        progress_queue.put({"type": "download_model", "payload": model_prefix})
    progress_queue.put({"type": "done", "payload": True})


def _monitor_prediction_process(process, progress_queue):
    global current_prediction_process, current_prediction_queue
    while True:
        try:
            event = progress_queue.get(timeout=0.2)
        except Exception:
            if not process.is_alive():
                break
            continue

        event_type = event.get("type") if isinstance(event, dict) else "log"
        payload = event.get("payload") if isinstance(event, dict) else event

        if event_type == "js" and window:
            window.evaluate_js(payload)
        elif event_type == "done":
            break
        else:
            forward_process_log_to_app(payload)

    process.join(timeout=0.2)
    if current_prediction_process is process:
        current_prediction_process = None
        current_prediction_queue = None


def _monitor_model_training_process(process, progress_queue):
    global current_model_training_process, current_model_training_queue
    while True:
        try:
            event = progress_queue.get(timeout=0.2)
        except Exception:
            if not process.is_alive():
                break
            continue

        event_type = event.get("type") if isinstance(event, dict) else "log"
        payload = event.get("payload") if isinstance(event, dict) else event

        if event_type == "js" and window:
            window.evaluate_js(payload)
        elif event_type == "download_model":
            download_model(payload)
        elif event_type == "done":
            break
        else:
            forward_process_log_to_app(payload)

    process.join(timeout=0.2)
    if current_model_training_process is process:
        current_model_training_process = None
        current_model_training_queue = None


def terminate_current_prediction():
    global current_prediction_process, current_prediction_queue
    process = current_prediction_process
    if not process:
        return False
    if process.is_alive():
        print("Stopping active RSS prediction process...")
        process.terminate()
        process.join(timeout=2)
        if process.is_alive():
            process.kill()
            process.join(timeout=1)
    current_prediction_process = None
    current_prediction_queue = None
    return True


def terminate_current_model_training():
    global current_model_training_process, current_model_training_queue
    process = current_model_training_process
    if not process:
        return False
    if process.is_alive():
        print("Stopping active model training process...")
        process.terminate()
        process.join(timeout=2)
        if process.is_alive():
            process.kill()
            process.join(timeout=1)
    current_model_training_process = None
    current_model_training_queue = None
    return True

class Api:
    def __init__(self):
        # The window may not exist during initialization.
        pass

    def get_app_version(self):
        return resolve_runtime_version(
            Path(APP_ROOT),
            Path(get_resource_path("asset_version.txt")),
        )

    def select_files_native(self, type):
        # Use the current constant and a compatible filter format.
        if type == "csv":
            file_types = (
                'CSV files (*.csv)', 'All files (*.*)'
            )
            multipleFiles = True
        elif type == "altitude":
            file_types = (
                'TIFF files (*.tif;*.tiff)', 'All files (*.*)'
            )
            multipleFiles = False
        elif type == "building" or type == "landuse":
            file_types = (
                'GPKG files (*.gpkg)', 'All files (*.*)'
            )
            multipleFiles = False
        elif type == "fv":
            file_types = (
                'ML files (*.xz)', 'All files (*.*)'
            )
            multipleFiles = True
        try:
            result = window.create_file_dialog(
                webview.FileDialog.OPEN, # Use the current constant.
                allow_multiple=multipleFiles,
                file_types=file_types
            )
            return result
        except Exception as e:
            print(f"Dialog Error: {e}")
            return None

    def select_folder_native(self):
        try:
            folder_dialog = getattr(webview.FileDialog, "FOLDER", None)
            if folder_dialog is None:
                folder_dialog = getattr(webview, "FOLDER_DIALOG", None)
            if folder_dialog is None:
                print("Folder dialog is not available in this pywebview version.")
                return None
            result = window.create_file_dialog(
                folder_dialog,
                allow_multiple=False
            )
            if not result:
                return None
            return result[0] if isinstance(result, (list, tuple)) else result
        except Exception as e:
            print(f"Folder dialog error: {e}")
            return None

    def start_log_proxy(self):
        from dask.distributed import Queue
        # Keep this name identical to the name used by the worker.
        self.remote_q = Queue("app_terminal_logs")

        def _listen():
            while True:
                try:
                    msg = self.remote_q.get() # Block until a message is available.
                    print(msg) # Trigger the local WebviewLogger on machine A and forward to the GUI.
                except: break

        threading.Thread(target=_listen, daemon=True).start()

    def executeModelGeneration(self, coords):
        global current_model_training_process, current_model_training_queue, model_training_monitor_thread
        terminate_current_model_training()
        coords = dict(coords)
        if coords.get("model") == "customized_model":
            custom_model_path = select_custom_model_file(window)
            if not custom_model_path:
                return False
            coords["custom_model_path"] = custom_model_path

        current_model_training_queue = multiprocessing.Queue()
        current_model_training_process = multiprocessing.Process(
            target=_model_training_process_entry,
            args=(coords, current_model_training_queue)
        )
        current_model_training_process.start()
        model_training_monitor_thread = threading.Thread(
            target=_monitor_model_training_process,
            args=(current_model_training_process, current_model_training_queue),
            daemon=True
        )
        model_training_monitor_thread.start()
        return True


class WebviewLogger:
    def __init__(self, window):
        self.window = window
        self.terminal = sys.stdout

    def write(self, message):
        self.terminal.write(message)

        # 1. Remove carriage returns emitted by Keras progress bars; they can split strings unexpectedly.
        msg = message.replace('\r', '').replace('\n', '')

        if msg.strip():
            try:
                # 2. Use json.dumps to encode the Python string safely as a JavaScript string.
                # It escapes quotes, slashes, and nonprinting characters automatically.
                safe_msg_json = json.dumps(msg)

                # 3. Inject the JavaScript. safe_msg_json already includes its surrounding quotes.
                self.window.evaluate_js(f"updateTerminal({safe_msg_json})")
            except Exception as e:
                # Prevent recursive errors caused by log redirection.
                self.terminal.write(f"\nLogger Error: {str(e)}\n")

    def flush(self):
        self.terminal.flush()




if hasattr(sys, '_MEIPASS'):
    # Configure the GDAL data path.
    os.environ['GDAL_DATA'] = os.path.join(sys._MEIPASS, 'rasterio', 'gdal_data')
    os.environ['PROJ_LIB'] = os.path.join(sys._MEIPASS, 'rasterio', 'proj_data')

def get_app_root_directory():
    if hasattr(sys, '_MEIPASS'):
        return sys._MEIPASS
    else:
        return os.path.abspath(".")

APP_ROOT = get_app_root_directory()
if APP_ROOT not in sys.path:
    sys.path.insert(0, APP_ROOT)

def get_resource_path(relative_path):
    base_path = sys._MEIPASS if hasattr(sys, '_MEIPASS') else os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def get_writable_temp_path():
    """Return a writable runtime directory for generated ASSET files."""
    if getattr(sys, 'frozen', False):
        if os.name == "nt":
            app_data_root = os.environ.get("APPDATA") or os.path.expanduser("~")
            base_path = os.path.join(app_data_root, "RSS_PredictApp", "tempData")
        else:
            base_path = os.path.join(
                os.path.expanduser("~"),
                "Library",
                "Application Support",
                "RSS_PredictApp",
                "tempData"
            )
    else:
        base_path = os.path.join(APP_ROOT, "tempData")

    os.makedirs(base_path, exist_ok=True)
    return base_path


def get_writable_settings_path():
    """Return a writable settings directory that reset_temp_data does not clear."""
    if getattr(sys, 'frozen', False):
        if os.name == "nt":
            app_data_root = os.environ.get("APPDATA") or os.path.expanduser("~")
            base_path = os.path.join(app_data_root, "RSS_PredictApp", "settings")
        else:
            base_path = os.path.join(
                os.path.expanduser("~"),
                "Library",
                "Application Support",
                "RSS_PredictApp",
                "settings"
            )
    else:
        base_path = os.path.join(APP_ROOT, "settings")

    os.makedirs(base_path, exist_ok=True)
    return base_path


def get_ui_preferences():
    """Load persistent UI preferences used by the frontend."""
    preferences_path = os.path.join(get_writable_settings_path(), UI_PREFERENCES_FILE)
    try:
        if not os.path.exists(preferences_path):
            return {}
        with open(preferences_path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        return payload if isinstance(payload, dict) else {}
    except Exception as e:
        print(f"Failed to load UI preferences: {e}")
        return {}


def save_ui_preferences(preferences):
    """Merge and persist UI preferences outside the resettable temp directory."""
    preferences_path = os.path.join(get_writable_settings_path(), UI_PREFERENCES_FILE)
    try:
        existing = get_ui_preferences()
        if not isinstance(preferences, dict):
            return False
        existing.update(preferences)
        with open(preferences_path, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2, sort_keys=True)
        return True
    except Exception as e:
        print(f"Failed to save UI preferences: {e}")
        return False


def save_prediction_result_mode(prediction_mode):
    """Persist the latest prediction input mode for result rendering."""
    try:
        mode = prediction_mode if prediction_mode in {"predictData_map", "predictData_file"} else "predictData_map"
        mode_path = os.path.join(get_writable_temp_path(), PREDICTION_RESULT_MODE_FILE)
        with open(mode_path, "w", encoding="utf-8") as f:
            json.dump({"prediction_result_mode": mode}, f)
    except Exception as e:
        print(f"Failed to save prediction result mode: {e}")


def load_prediction_result_mode():
    """Load the latest prediction input mode for result rendering."""
    try:
        mode_path = os.path.join(get_writable_temp_path(), PREDICTION_RESULT_MODE_FILE)
        if not os.path.exists(mode_path):
            return "predictData_map"
        with open(mode_path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        mode = payload.get("prediction_result_mode")
        return mode if mode in {"predictData_map", "predictData_file"} else "predictData_map"
    except Exception as e:
        print(f"Failed to load prediction result mode: {e}")
        return "predictData_map"


# Define the Python API exposed to the frontend.
def worker_thread(coords):
    """Run the machine-learning task in a background thread to keep the UI responsive."""
    try:
        selected_folder_csv = get_writable_temp_path()
        DATABASE_MAP = {
            "DB_matumotoCity": "database/nagano_matumoto_shinndai",
            "DB_kouchi_kamishi": "database/kouchi_kami",
            "DB_kouchi_shimanntoucyou": "database/kouchi_shimanntoucyou",
            "DB_kanagawa_yokosukashi": "database/kanagawa_yokosuka",
            "DB_nagano_urugimura": "database/nagano_urugimura",
            "DB_okinawa_naha": "database/okinawa_naha",
            "DB_okinawa_nago": "database/okinawa_nago",
            "DB_nagano_ina": "database/nagano_ina"
        }
        db_key = coords.get('database')
        relative_path = DATABASE_MAP.get(db_key)
        if relative_path:
            selected_folder_map = os.path.join(APP_ROOT, relative_path)
        else:
            print(f"Unknown database: {db_key}")
            return False
        subFun.clean_folder_except(selected_folder_csv, "keep_nothing")  # Clear temporary files except those with the specified prefix.
        save_prediction_result_mode(coords.get("predictDataSelectValue", "predictData_map"))

        # Prepare the argument list.
        if coords['predictDataSelectValue'] == "predictData_file":
            select_prediction_file_path = coords.get("prediction_file_path") or select_prediction_file(window)
        else:
            select_prediction_file_path = ""
        args = [
            selected_folder_csv, selected_folder_map, APP_ROOT,
            coords['min_lng'], coords['min_lat'], coords['max_lng'], coords['max_lat'],
            coords['mesh_lng'], coords['mesh_lat'],
            coords['frequency'], coords['SF'], coords['EIRP'],
            coords['fixAntenna_lng'], coords['fixAntenna_lat'], coords['fixAntenna_alt'],
            coords['fixAntenna_height'], coords['moveAntenna_height'], select_prediction_file_path
        ]

        if coords['model'] == "NICT_latest_model":
            baseModel = subFun.get_gpkg_files(os.path.join(APP_ROOT, "models"), "*NICT*")
        elif coords['model'] == "customized_model":
            baseModel = coords.get("custom_model_path") or select_custom_model_file(window)
        selected_predict_model = baseModel

        window.evaluate_js("updateProgress(30, 'Generating prediction area...')")
        predict_area.run_prediction_process(args)
        # Collect matching files.
        contentReadDataIndex = subFun.get_ML_files(selected_folder_csv, "ML_myTempExp_*")
        window.evaluate_js("updateProgress(40, 'Preparing prediction model parameters...')")
        try:
            # Pass arguments directly; python_exe and command-line serialization are no longer required.
            transfer_learning_main.run_transfer_learning(
                selected_folder_csv,
                num_test_per = str(1),
                user_input = 1,
                model_path = selected_predict_model,
                data_index = list(range(1,len(contentReadDataIndex)+1)),
                content_data_index = contentReadDataIndex
            )
            print("Transfer learning task completed.")
        except Exception as e:
            print(f"Transfer learning execution failed: {e}")
            raise e

        selected_name = subFun.get_gpkg_files(selected_folder_csv, "Predict_model_for_*")
        window.evaluate_js("updateProgress(70, 'Predicting received signal strength...')")
        rxData_Altitude_TL, _, _ = subFun_TL.show_Predict_model(selected_name)
        time_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        rxData_Altitude_TL.to_csv(os.path.join(selected_folder_csv, f'predict_RSS_{time_str}.csv'), index=False)
        print("Prediction results generated.")
        subFun.clean_folder_except(selected_folder_csv, "predict_RSS_")
        save_prediction_result_mode(coords.get("predictDataSelectValue", "predictData_map"))
        #"""
        window.evaluate_js("updateProgress(100, 'Completed')")
        return True
    except Exception as e:
        print(f"Execution failed: {e}")
        window.evaluate_js(f"updateProgress(-1, 'Error: {str(e)}')")






def worker_thread_modelGen(api_instance, coords, auto_download=True):
    selected_folder_csv = get_writable_temp_path()
    copy_selected_files(coords, selected_folder_csv)
    if coords['model'] != "noModel":
        # Transfer-learning workflow.
        if coords['model'] == "NICT_latest_model":
            selected_predict_model = subFun.get_gpkg_files(os.path.join(APP_ROOT, "models"), "*NICT*")
        if coords['model'] == "customized_model":
            selected_predict_model = coords.get("custom_model_path")
        contentReadDataIndex = subFun.get_ML_files(selected_folder_csv, "ML_myTempExp_*")
        train_judge_model = bool(coords.get('trainJudgeModel', False))
        window.evaluate_js("updateProgress(10, 'Generating model with transfer learning. This may take some time...')")
        try:
            transfer_learning_main.run_transfer_learning(
                selected_folder_csv,
                num_test_per = str(0.01), # Fraction of new data used for prediction; 0.01 uses 1% and reserves 99% for model generation.
                user_input = 1,
                model_path = selected_predict_model,
                data_index = list(range(1,len(contentReadDataIndex)+1)),
                content_data_index = contentReadDataIndex,
                learning_type = coords['learningType'],
                api_instance = api_instance,
                freeze_layer = int(coords['freezeLayer']),
                learning_rate = float(coords['learningRate']),
                train_judge_model = train_judge_model
            )
            print("Transfer learning task completed.")
            subFun.clean_folder_except(selected_folder_csv, "TL_model_")
            window.evaluate_js("updateProgress(100, 'Model generation completed.')")
            if auto_download:
                download_model("TL_model_")
            return "TL_model_"
        except Exception as e:
            print(f"Transfer learning execution failed: {e}")
            raise e
    else:
        # Generate the model directly without transfer learning.
        contentReadDataIndex = subFun.get_ML_files(selected_folder_csv, "ML_myTempExp_*")
        window.evaluate_js("updateProgress(10, 'Generating model with machine learning. This may take some time...')")
        try:
            print("\nStarting historical model training...")
            training_history_database.run_training_history_database(
                selected_folder_csv,
                numCore1 = int(coords['numCore1']),
                numCore2 = 2 * int(coords['numCore1']),
                numCore3 = 4 * int(coords['numCore1']),
                numTestPer = 0.15,
                data_index = list(range(1,len(contentReadDataIndex)+1)),
                content_data_index = contentReadDataIndex,
                learning_type = coords['learningType'],
                api_instance = api_instance
            )
            print("Machine learning task completed.")
            subFun.clean_folder_except(selected_folder_csv, "history_model_from_")
            window.evaluate_js("updateProgress(100, 'Model generation completed.')")
            if auto_download:
                download_model("history_model_from_")
            return "history_model_from_"
        except Exception as e:
            print(f"Machine learning execution failed: {e}")
            raise e



def copy_selected_files(coords, target_folder='selected_folder_csv'):
    """
    Copy files from coords['selectedPaths'] into the specified directory.

    Args:
        coords (dict): Dictionary whose 'selectedPaths' value is a list of paths.
        target_folder (str): Destination directory name. Defaults to 'selected_folder_csv'.
    """

    # 1. Create the destination directory if it does not exist.
    if not os.path.exists(target_folder):
        os.makedirs(target_folder)
        print(f"Created target folder: {target_folder}")

    # 2. Retrieve the path list.
    selected_paths = coords.get('selectedPaths', [])

    copy_count = 0

    # 3. Iterate over the paths and copy each file.
    for source_path in selected_paths:
        if os.path.exists(source_path):
            # Extract the file name without its parent path.
            file_name = os.path.basename(source_path)
            # Construct the complete destination path.
            dest_path = os.path.join(target_folder, file_name)

            try:
                # Copy the file. shutil.copy preserves permissions; shutil.copy2 also attempts to preserve metadata such as modification time.
                shutil.copy2(source_path, dest_path)
                print(f"Copied successfully: {file_name}")
                copy_count += 1
            except Exception as e:
                print(f"Error while copying file {file_name}: {e}")
        else:
            print(f"Warning: file does not exist, skipped: {source_path}")

    print(f"\nTask completed. Copied {copy_count} file(s) to {target_folder}.")



def select_custom_model_file(window):
    """
    Display a file-selection dialog and return the selected .xz file path.
    """
    window.evaluate_js("alert('Please select a model file (.xz format).')")
    file_types = ('Model files (*.xz)', 'All files (*.*)')

    # Display the dialog.
    result = window.create_file_dialog(
        webview.FileDialog.OPEN,
        allow_multiple=False,
        file_types=file_types
    )

    # result is None when the user cancels.
    if result and len(result) > 0:
        return result[0]
    return None


def select_prediction_file(window):
    """
    Display a file-selection dialog and return the selected .csv file path.
    """
    window.evaluate_js("alert('Please select a prediction CSV file (.csv format).')")
    file_types = ('CSV files (*.csv)', 'All files (*.*)')

    # Display the dialog.
    result = window.create_file_dialog(
        webview.FileDialog.OPEN,
        allow_multiple=False,
        file_types=file_types
    )

    # result is None when the user cancels.
    if result and len(result) > 0:
        return result[0]
    return None




def executeRssPrediction(coords):
    """JavaScript API: start a background prediction process that Reset can terminate."""
    global current_prediction_process, current_prediction_queue, prediction_monitor_thread
    terminate_current_prediction()
    coords = dict(coords)
    if coords.get("predictDataSelectValue") == "predictData_file":
        prediction_file_path = select_prediction_file(window)
        if not prediction_file_path:
            return False
        coords["prediction_file_path"] = prediction_file_path
    if coords.get("model") == "customized_model":
        custom_model_path = select_custom_model_file(window)
        if not custom_model_path:
            return False
        coords["custom_model_path"] = custom_model_path
    save_prediction_result_mode(coords.get("predictDataSelectValue", "predictData_map"))
    current_prediction_queue = multiprocessing.Queue()
    current_prediction_process = multiprocessing.Process(
        target=_prediction_process_entry,
        args=(coords, current_prediction_queue),
        daemon=True
    )
    current_prediction_process.start()
    prediction_monitor_thread = threading.Thread(
        target=_monitor_prediction_process,
        args=(current_prediction_process, current_prediction_queue),
        daemon=True
    )
    prediction_monitor_thread.start()
    return True



def executeDataProcessing(coords):
    """
    JavaScript API: execute the operation directly.

    pywebview invokes this function on a separate thread, so the operation can run
    synchronously here while the JavaScript await waits for completion.
    """
    try:
        selected_folder_csv = get_writable_temp_path()

        # Invoke the operation directly without threading.Thread.
        main_collect_data.start_collect_logic(
            selected_folder_csv,
            selected_folder_csv,
            selected_folder_csv,
            float(coords['frequency']),
            int(coords['SF']),
            float(coords['EIRP']),
            float(coords['fixAntenna_lng']),
            float(coords['fixAntenna_lat']),
            float(coords['fixAntenna_alt']),
            float(coords['fixAntenna_height']),
            float(coords['moveAntenna_height'])
        )

        reset_temp_data("ML_")

        return {
            "status": "success",
            "message": "Feature generation completed. Download the output or reset to process another dataset."
        }

    except Exception as e:
        print(f"Execution failed: {e}")
        # Return the error so the JavaScript try-catch can handle the operation failure.
        return {"status": "error", "message": str(e)}


def get_prediction_data():
    """Read the latest prediction CSV and return map-ready records."""
    try:
        folder = get_writable_temp_path()
        files = glob.glob(os.path.join(folder, "predict_RSS_*.csv"))
        if not files:
            return None

        latest_file = max(files, key=os.path.getctime)
        df = pd.read_csv(latest_file)

        latitude_column = next((col for col in df.columns if str(col).lower() in {"latitude", "lat"}), None)
        longitude_column = next((col for col in df.columns if str(col).lower() in {"longitude", "lng", "lon"}), None)
        if not latitude_column or not longitude_column:
            print("Failed to read prediction data: missing Latitude/Longitude columns.")
            return None

        model_column_pattern = re.compile(r"^Model_(\d+)$")
        model_columns = [col for col in df.columns if model_column_pattern.match(str(col))]
        model_columns = sorted(
            model_columns,
            key=lambda col: int(model_column_pattern.match(str(col)).group(1))
        )

        if model_columns:
            numeric_models = df[model_columns].apply(pd.to_numeric, errors="coerce")
            df["Predicted_Value"] = numeric_models.median(axis=1, skipna=True)
        elif "Predicted_Value" in df.columns:
            df["Predicted_Value"] = pd.to_numeric(df["Predicted_Value"], errors="coerce")
        else:
            print("Failed to read prediction data: missing Model_* prediction columns.")
            return None

        df["Latitude"] = pd.to_numeric(df[latitude_column], errors="coerce")
        df["Longitude"] = pd.to_numeric(df[longitude_column], errors="coerce")
        df = df.dropna(subset=["Latitude", "Longitude", "Predicted_Value"])
        if df.empty:
            print("Failed to read prediction data: no valid numeric prediction rows.")
            return None

        prediction_result_mode = load_prediction_result_mode()
        df["Prediction_Result_Mode"] = prediction_result_mode

        return df.to_dict(orient='records')
    except Exception as e:
        print(f"Failed to read data: {e}")
        return None


def download_csv():
    """Save a file with the native pywebview dialog."""
    try:
        folder = get_writable_temp_path()
        files = glob.glob(os.path.join(folder, "predict_RSS_*.csv"))
        if not files:
            return False

        latest_file = max(files, key=os.path.getctime)

        # Open the native pywebview save dialog.
        file_path = window.create_file_dialog(
            webview.FileDialog.SAVE,
            directory=os.path.expanduser("~"),
            save_filename=os.path.basename(latest_file),
            file_types=('CSV Files (*.csv)', 'All files (*.*)')
        )

        if file_path:
            # Support the return formats used by different operating systems.
            actual_path = file_path[0] if isinstance(file_path, (list, tuple)) else file_path
            shutil.copy(latest_file, actual_path)
            return True
        return False
    except Exception as e:
        print(f"Save failed: {e}")
        return False


def download_dataset_output():
    """Save the latest generated feature-vector output from Dataset Prep."""
    return download_model("ML_")


def download_model(file_head):
    """
    Display a dialog to save the model file matching the specified prefix (file_head).

    :param file_head: Prefix string such as "TL_model_" or "ML_model_".
    """
    try:
        # 1. Locate the temporary directory.
        folder = get_writable_temp_path()

        # 2. Find files with the prefix, accepting any suffix such as .gpkg, .pth, or .onnx.
        search_pattern = os.path.join(folder, f"{file_head}*")
        files = glob.glob(search_pattern)

        if not files:
            print(f"No model file found with prefix {file_head}")
            # Optionally notify the frontend.
            window.evaluate_js(f"alert('Save failed: no file starting with {file_head} was found.')")
            return False

        # 3. Select the most recently generated matching file.
        latest_file = max(files, key=os.path.getctime)
        original_filename = os.path.basename(latest_file)

        # 4. Open the native pywebview save dialog.
        # Some versions use webview.SAVE_DIALOG, while others use webview.FileDialog.SAVE.
        file_path = window.create_file_dialog(
            webview.FileDialog.SAVE,
            directory=os.path.expanduser("~"),
            save_filename=original_filename,
            file_types=('Model Files (*.pkl.xz)', 'All files (*.*)')
        )

        # 5. Copy the file after the user confirms the destination.
        if file_path:
            # Support platform-specific return formats (str or list).
            actual_destination = file_path[0] if isinstance(file_path, (list, tuple)) else file_path

            shutil.copy(latest_file, actual_destination)
            print(f"Saved {original_filename} to: {actual_destination}")
            return True

        return False

    except Exception as e:
        print(f"Error during save: {e}")
        return False


def upload_csv_files(file_data_list, altitude_file_data_list, building_file_data_list, landuse_file_data_list):
    """
    Process lists of file paths.

    1. Copy the file referenced by the Altitude path and rename it to fine_tuning_database_altitude.tif.
    2. Process the GPKG files.
    3. Read and merge the CSV files.
    """
    try:
        # Obtain the temporary output directory.
        selected_folder_csv = get_writable_temp_path()
        if not os.path.exists(selected_folder_csv):
            os.makedirs(selected_folder_csv)

        # --- 1. Process the Altitude TIF file (altitude_file_data_list is a path list). ---
        if altitude_file_data_list and len(altitude_file_data_list) > 0:
            src_path = altitude_file_data_list[0] # Use the first file path.
            try:
                save_path_altitude = os.path.join(selected_folder_csv, "fine_tuning_database_altitude.tif")
                # Copy directly from the source path; Base64 decoding is no longer required.
                shutil.copy(src_path, save_path_altitude)
                print(f"Altitude file copied to: fine_tuning_database_altitude.tif")
            except Exception as e:
                print(f"Altitude saving error: {e}")

        # --- 2. Process the building GPKG file. ---
        if building_file_data_list and len(building_file_data_list) > 0:
            src_path = building_file_data_list[0]
            try:
                save_path_building = os.path.join(selected_folder_csv, "fine_tuning_database_building.gpkg")
                shutil.copy(src_path, save_path_building)
                print(f"Building file copied to: fine_tuning_database_building.gpkg")
            except Exception as e:
                print(f"Building saving error: {e}")

        # --- 3. Process the land-use GPKG file. ---
        if landuse_file_data_list and len(landuse_file_data_list) > 0:
            src_path = landuse_file_data_list[0]
            try:
                save_path_landuse = os.path.join(selected_folder_csv, "fine_tuning_database_cityType.gpkg")
                shutil.copy(src_path, save_path_landuse)
                print(f"Landuse file copied to: fine_tuning_database_cityType.gpkg")
            except Exception as e:
                print(f"Landuse saving error: {e}")

        # --- 4. Process the list of CSV files. ---
        all_dataframes = []
        skipped_files = []
        total_dropped_rows = 0

        # Define keywords used to recognize alternate uploaded column names.
        lon_k = ['longitude', 'lon', 'lng', 'x']
        lat_k = ['latitude', 'lat', 'y']
        rssi_k = ['rssi', 'dn', 'predicted_value']

        for csv_path in file_data_list:
            # csv_path is now a path string.
            file_name = os.path.basename(csv_path)
            if not file_name.lower().endswith('.csv'):
                continue

            try:
                # Read the local path directly with pandas.
                df = pd.read_csv(csv_path)

                cols = df.columns.tolist()
                cols_lower = [c.lower() for c in cols]

                # Find matching columns.
                target_lon = next((cols[i] for i, c in enumerate(cols_lower) if c in lon_k), None)
                target_lat = next((cols[i] for i, c in enumerate(cols_lower) if c in lat_k), None)
                target_rssi = next((cols[i] for i, c in enumerate(cols_lower) if c in rssi_k), None)

                if not (target_lon and target_lat and target_rssi):
                    skipped_files.append(f"{file_name} (column names do not match)")
                    continue

                # Extract and clean the data.
                df_filtered = df[[target_lon, target_lat, target_rssi]].copy()
                df_filtered.columns = ['Longitude', 'Latitude', 'RSSI']

                initial_len = len(df_filtered)
                df_filtered = df_filtered.dropna(subset=['Longitude', 'Latitude', 'RSSI'])
                total_dropped_rows += (initial_len - len(df_filtered))

                if not df_filtered.empty:
                    all_dataframes.append(df_filtered)
                else:
                    skipped_files.append(f"{file_name} (no valid data after cleaning)")

            except Exception as e:
                skipped_files.append(f"{file_name} (read error: {str(e)})")

        # --- 5. Merge and save the combined CSV file. ---
        if all_dataframes:
            combined_df = pd.concat(all_dataframes, ignore_index=True)
            save_path_total = os.path.join(selected_folder_csv, "fine_tuning_total.csv")
            combined_df.to_csv(save_path_total, index=False, encoding='utf-8')

            msg = f"Combined {len(all_dataframes)} files into 'fine_tuning_total.csv'."
            if total_dropped_rows > 0:
                msg += f"\n(Removed {total_dropped_rows} records containing null values.)"
            if skipped_files:
                msg += "\nSkipped files: " + ", ".join(skipped_files)

            return {"status": "success", "message": msg}
        else:
            return {"status": "error", "message": "No valid CSV data was found."}

    except Exception as e:
        print(f"Fatal Upload Error: {e}")
        return {"status": "error", "message": str(e)}


def reset_temp_data(prefix_to_keep=None):
    """
    Clear the temporary directory during reset.

    :param prefix_to_keep: Prefix of files to retain. If omitted, remove all files.
    """
    try:
        terminate_current_prediction()
        terminate_current_model_training()
        # prefix_to_keep is None when the JavaScript caller omits the argument.
        target_prefix = prefix_to_keep if prefix_to_keep is not None else "KEEP_NOTHING"

        selected_folder_csv = get_writable_temp_path()

        # Delegate the operation to subFun.
        subFun.clean_folder_except(selected_folder_csv, target_prefix)

        print(f"Cleanup complete. Prefix retained: {target_prefix}, path: {selected_folder_csv}")
        return True
    except Exception as e:
        print(f"Failed to clean the temporary folder: {e}")
        return False


def get_help_pdf():
    """Read guide.pdf from the project root and encode it as Base64."""
    # Keep this file name synchronized with the file stored in the project root.
    pdf_path = os.path.join(APP_ROOT, 'assets/fine_tuning_guide.pdf')

    if not os.path.exists(pdf_path):
        return {"status": "error", "message": f"File not found: {pdf_path}"}

    try:
        with open(pdf_path, "rb") as f:
            encoded_pdf = base64.b64encode(f.read()).decode('utf-8')
            return {"status": "success", "data": encoded_pdf}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def get_data_analysis_output_folder():
    output_folder = os.path.join(get_writable_temp_path(), "data_analysis")
    os.makedirs(output_folder, exist_ok=True)
    return output_folder


def list_analysis_csv_files(folder_path):
    try:
        if not folder_path or not os.path.isdir(folder_path):
            return {"status": "error", "message": "Select a valid folder before listing CSV files.", "files": []}
        csv_files = sorted(glob.glob(os.path.join(folder_path, "*.csv")))
        return {
            "status": "success",
            "message": f"Found {len(csv_files)} CSV file(s).",
            "files": [
                {
                    "path": path,
                    "name": os.path.basename(path),
                    "size": os.path.getsize(path),
                }
                for path in csv_files
            ],
        }
    except Exception as e:
        print(f"Failed to list analysis CSV files: {e}")
        return {"status": "error", "message": str(e), "files": []}


def executeDataAnalysis(analysis_request):
    try:
        display_mode = "both"
        file_colors = {}
        if isinstance(analysis_request, dict):
            display_mode = analysis_request.get("displayMode", "both")
            file_entries = analysis_request.get("files", [])
            csv_paths = []
            for entry in file_entries:
                if isinstance(entry, dict):
                    path = entry.get("path")
                    if path:
                        csv_paths.append(path)
                        if entry.get("color"):
                            file_colors[path] = entry.get("color")
                elif entry:
                    csv_paths.append(entry)
        else:
            csv_paths = analysis_request

        if not csv_paths:
            return {"status": "error", "message": "Select one or more CSV files before running data analysis."}

        output_folder = get_data_analysis_output_folder()
        result = my_plot_figure.plot_Model_Aggregation_Error_CDF(
            csv_paths,
            output_folder,
            needPNG=True,
            needSVG=True,
            display_mode=display_mode,
            file_colors=file_colors,
        )

        if result.get("status") != "success":
            print(result.get("message", "Data analysis failed."))
            return result

        png_path = result.get("png_path")
        if png_path and os.path.exists(png_path):
            with open(png_path, "rb") as f:
                result["png_data_uri"] = "data:image/png;base64," + base64.b64encode(f.read()).decode("utf-8")

        print(result.get("message", "Data analysis completed."))
        for skipped in result.get("skipped_files", []):
            print(f"Skipped {skipped.get('file')}: {skipped.get('reason')}")
        return result
    except Exception as e:
        print(f"Data analysis failed: {e}")
        return {"status": "error", "message": str(e)}


def executePredictionCsvAnalysis(analysis_request):
    try:
        analysis_type = "rssi_cdf"
        file_colors = {}
        csv_paths = []
        if isinstance(analysis_request, dict):
            analysis_type = analysis_request.get("analysisType", "rssi_cdf")
            file_entries = analysis_request.get("files", [])
            for entry in file_entries:
                if isinstance(entry, dict):
                    path = entry.get("path")
                    if path:
                        csv_paths.append(path)
                        if entry.get("color"):
                            file_colors[path] = entry.get("color")
                elif entry:
                    csv_paths.append(entry)
        else:
            csv_paths = analysis_request

        if not csv_paths:
            return {"status": "error", "message": "Select one or more prediction CSV files before running analysis."}

        output_folder = get_data_analysis_output_folder()
        result = my_plot_figure.plot_Prediction_CSV_Analysis(
            csv_paths,
            output_folder,
            analysis_type=analysis_type,
            needPNG=True,
            needSVG=True,
            file_colors=file_colors,
        )

        if result.get("status") != "success":
            print(result.get("message", "Prediction CSV analysis failed."))
            return result

        png_path = result.get("png_path")
        if png_path and os.path.exists(png_path):
            with open(png_path, "rb") as f:
                result["png_data_uri"] = "data:image/png;base64," + base64.b64encode(f.read()).decode("utf-8")

        print(result.get("message", "Prediction CSV analysis completed."))
        for skipped in result.get("skipped_files", []):
            print(f"Skipped {skipped.get('file')}: {skipped.get('reason')}")
        return result
    except Exception as e:
        print(f"Prediction CSV analysis failed: {e}")
        return {"status": "error", "message": str(e)}


def reset_data_analysis_outputs():
    try:
        output_folder = get_data_analysis_output_folder()
        for path in glob.glob(os.path.join(output_folder, "*")):
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
        print("Data analysis outputs reset.")
        return True
    except Exception as e:
        print(f"Failed to reset data analysis outputs: {e}")
        return False


def download_analysis_output(extension, file_path=None):
    try:
        output_folder = get_data_analysis_output_folder()
        if file_path:
            requested_path = os.path.abspath(file_path)
            output_root = os.path.abspath(output_folder)
            if not requested_path.startswith(output_root + os.sep):
                window.evaluate_js("alert('Save failed: invalid analysis output path.')")
                return False
            file_path = requested_path
        else:
            candidates = glob.glob(os.path.join(output_folder, f"*.{extension}"))
            file_path = max(candidates, key=os.path.getmtime) if candidates else ""
        if not file_path or not os.path.exists(file_path):
            window.evaluate_js(f"alert('Save failed: no {extension.upper()} analysis output was found.')")
            return False

        file_types = (
            'SVG files (*.svg)' if extension == "svg" else 'PNG files (*.png)',
            'All files (*.*)'
        )
        save_path = window.create_file_dialog(
            webview.FileDialog.SAVE,
            directory=os.path.expanduser("~"),
            save_filename=os.path.basename(file_path),
            file_types=file_types
        )
        if not save_path:
            return False

        actual_destination = save_path[0] if isinstance(save_path, (list, tuple)) else save_path
        shutil.copy(file_path, actual_destination)
        print(f"Saved data analysis {extension.upper()} to: {actual_destination}")
        return True
    except Exception as e:
        print(f"Data analysis save failed: {e}")
        return False


def download_data_analysis_svg(file_path=None):
    return download_analysis_output("svg", file_path)


def download_data_analysis_png(file_path=None):
    return download_analysis_output("png", file_path)


def download_application_log(log_text):
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"ASSET_application_log_{timestamp}.txt"
        save_path = window.create_file_dialog(
            webview.FileDialog.SAVE,
            directory=os.path.expanduser("~"),
            save_filename=file_name,
            file_types=('Text files (*.txt)', 'All files (*.*)')
        )
        if not save_path:
            return False

        actual_destination = save_path[0] if isinstance(save_path, (list, tuple)) else save_path
        normalized_text = str(log_text or "")
        with open(actual_destination, "w", encoding="utf-8") as log_file:
            log_file.write(normalized_text)
            if normalized_text and not normalized_text.endswith("\n"):
                log_file.write("\n")

        print(f"Application log saved to: {actual_destination}")
        return True
    except Exception as e:
        print(f"Application log export failed: {e}")
        return False


def start_logic():
    # Start in a resizable normal window; the UI expands to a three-column layout when the user maximizes it.
    # Redirect standard output.
    sys.stdout = WebviewLogger(window)
    # Perform initialization.
    # Define ANSI color escape sequences.
    print("Initializing Application...")
    reset_temp_data()
    print("System environment check complete...")
    print("Waiting for user operation...")


window = None
def main():
    global window
    api = Api()

    # Resolve the absolute HTML entry-point path for source and packaged execution.
    # Use the product suite by default; set ASSET_UI_ENTRY=web/index.html to restore the legacy UI.
    ui_entry = os.environ.get("ASSET_UI_ENTRY", "web/app-suite.html")
    html_path = get_resource_path(ui_entry)

    # Configure the PyWebView window, including its size, title, and resizability.
    window = webview.create_window(
        title="ASSET Framework",  # Window title.
        url=html_path,               # HTML file to load.
        js_api=api,
        resizable=True               # Allow window resizing.
    )

    # Expose Python functions to the frontend JavaScript.
    window.expose(executeRssPrediction)
    window.expose(get_prediction_data)
    window.expose(download_csv)
    window.expose(download_dataset_output)
    window.expose(upload_csv_files)
    window.expose(reset_temp_data)
    window.expose(executeDataProcessing)
    window.expose(get_help_pdf)
    window.expose(list_analysis_csv_files)
    window.expose(executeDataAnalysis)
    window.expose(executePredictionCsvAnalysis)
    window.expose(reset_data_analysis_outputs)
    window.expose(download_data_analysis_svg)
    window.expose(download_data_analysis_png)
    window.expose(download_application_log)
    window.expose(get_ui_preferences)
    window.expose(save_ui_preferences)

    # Start the window with the WebKit engine on macOS.
    webview.start(start_logic, debug=False, gui='webkit2')

if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
