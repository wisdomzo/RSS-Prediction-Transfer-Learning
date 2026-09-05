import sys
import os
import subprocess
import subFun
from subFun import generate_grid_points
import main_collect_data
import shutil
import pandas as pd

def get_app_root_directory():
    if hasattr(sys, '_MEIPASS'):
        return sys._MEIPASS
    else:
        return os.path.abspath(".")

APP_ROOT = get_app_root_directory()
if APP_ROOT not in sys.path:
    sys.path.insert(0, APP_ROOT)


def copy_prediction_data(source_path, target_folder='selected_folder_csv'):
    """
    Copy a source file to the target folder when the source path is nonempty
    and points to an existing file.

    Args:
        source_path (str): Source file path, which may be '' or None.
        target_folder (str): Target folder. Defaults to 'selected_folder_csv'.
    """

    # 1. Skip empty, None, or whitespace-only paths.
    if not source_path or not str(source_path).strip():
        print("Source path is empty. Copy task skipped.")
        return False

    # 2. Verify that the source is an existing file.
    if os.path.exists(source_path) and os.path.isfile(source_path):
        try:
            # 3. Ensure the target directory exists.
            if not os.path.exists(target_folder):
                os.makedirs(target_folder)

            df = pd.read_csv(source_path)
            column_map = {str(column).lower(): column for column in df.columns}
            lon_name = next((column_map[key] for key in ['longitude', 'lon', 'lng', 'x'] if key in column_map), None)
            lat_name = next((column_map[key] for key in ['latitude', 'lat', 'y'] if key in column_map), None)
            rssi_name = next((column_map[key] for key in ['rssi'] if key in column_map), None)
            if not lon_name or not lat_name:
                print("Prediction CSV rejected: missing longitude and latitude columns.")
                return False

            normalized_df = pd.DataFrame({
                'Longitude': pd.to_numeric(df[lon_name], errors='coerce'),
                'Latitude': pd.to_numeric(df[lat_name], errors='coerce')
            })
            if rssi_name:
                normalized_df['RSSI'] = pd.to_numeric(df[rssi_name], errors='coerce')
            else:
                normalized_df['RSSI'] = -999
            normalized_df = normalized_df.dropna(subset=['Longitude', 'Latitude'])
            if normalized_df.empty:
                print("Prediction CSV rejected: no valid longitude and latitude rows.")
                return False

            # 4. Save the normalized prediction-point CSV for downstream processing.
            file_name = os.path.basename(source_path)
            dest_path = os.path.join(target_folder, file_name)
            normalized_df.to_csv(dest_path, index=False)
            print(f"Copied file successfully: {file_name} -> {target_folder}")
            return True

        except Exception as e:
            print(f"Error during copy: {e}")
            return False
    else:
        print(f"File does not exist or path is invalid: {source_path}")
        return False


def run_prediction_process(args_list):
    selected_folder_csv = args_list[0]
    selected_folder_map = args_list[1]
    selected_folder_fun = args_list[2]

    lon_min = float(args_list[3]) if args_list[3] else None
    lat_min = float(args_list[4]) if args_list[4] else None
    lon_max = float(args_list[5]) if args_list[5] else None
    lat_max = float(args_list[6]) if args_list[6] else None

    frequency = float(args_list[9])
    SF = int(args_list[10])
    EIRP = float(args_list[11])
    fixAntenna_lng = float(args_list[12])
    fixAntenna_lat = float(args_list[13])
    fixAntenna_alt = float(args_list[14])
    fixAntenna_height = float(args_list[15])
    moveAntenna_height = float(args_list[16])
    predictDataSelectValue = args_list[17]

    if not predictDataSelectValue or not str(predictDataSelectValue).strip():
        # Configure grid sampling.
        if lon_min == lon_max and lat_min == lat_max:
            N, M = 1, 1
        else:
            N, M = int(args_list[7]), int(args_list[8])
        # Generate grid points.
        generate_grid_points(lon_min, lon_max, lat_min, lat_max, N, M, selected_folder_csv)
    else:
        copy_prediction_data(predictDataSelectValue, selected_folder_csv)

    try:
        main_collect_data.start_collect_logic(
            selected_folder_csv,
            selected_folder_map,
            selected_folder_fun,
            frequency,
            SF,
            EIRP,
            fixAntenna_lng,
            fixAntenna_lat,
            fixAntenna_alt,
            fixAntenna_height,
            moveAntenna_height
        )
    except Exception as e:
        print(f"Data collection failed: {e}")
        sys.exit(1)



if __name__ == "__main__":
    run_prediction_process(sys.argv[1:])
