import csv
import os
import pandas as pd
from glob import glob
import numpy as np
import math
import pickle
import my_plot_figure
import subprocess
from pathlib import Path
import platform
import tensorflow as tf
import rasterio
from rasterio.mask import mask
import geopandas as gpd
from shapely.geometry import Point
from shapely.geometry import box
import main_collect_data
import transfer_learning_main
import shapely
from rasterio import features
import gc
import time
import tensorflow as tf
from dask.distributed import get_client, wait


def integrateExpData(exp_data_path):
    csv_files = sorted(glob(os.path.join(exp_data_path, '*.csv')))
    fin_data = pd.DataFrame()

    for file_name in csv_files:
        try:
            # 1. Detect column names.
            full_df = pd.read_csv(file_name, nrows=0) # nrows=0 reads only the header and is faster than nrows=1.
            columns_lower = [col.lower() for col in full_df.columns]

            # 2. Verify that the required columns exist.
            if not all(k in columns_lower for k in ['latitude', 'longitude', 'rssi']):
                print(f"File {file_name} is missing required columns and was skipped.")
                continue

            # 3. Build a mapping from the original column names.
            # This extracts all three columns correctly regardless of their positions in the CSV file.
            name_map = {
                full_df.columns[columns_lower.index('latitude')]: 'Latitude',
                full_df.columns[columns_lower.index('longitude')]: 'Longitude',
                full_df.columns[columns_lower.index('rssi')]: 'RSSI'
            }

            # 4. Read only the required columns.
            temp_df = pd.read_csv(
                file_name,
                usecols=list(name_map.keys()),
                dtype='float64'
            ).dropna(how='any') # Discard rows missing longitude, latitude, or RSSI.

            # 5. Rename columns by mapping instead of overwriting columns positionally.
            # rename matches source and destination names without depending on the original order.
            temp_df = temp_df.rename(columns=name_map)

            # 6. Standardize column order before concatenation.
            temp_df = temp_df[['Latitude', 'Longitude', 'RSSI']]

            # 7. Merge and remove duplicates.
            if fin_data.empty:
                fin_data = temp_df
            else:
                # drop_duplicates can be more efficient than isin, depending on the dataset size.
                fin_data = pd.concat([fin_data, temp_df], ignore_index=True)
                fin_data = fin_data.drop_duplicates().reset_index(drop=True)

        except Exception as e:
            print(f"Error while processing file {file_name}: {str(e)}")
            continue

    if not fin_data.empty:
        print(f"Successfully integrated {len(fin_data)} record(s).")
    return fin_data


def backup_integrateExpData(exp_data_path):
    # Find all CSV files under the specified path.
    csv_files = sorted(glob(os.path.join(exp_data_path, '*.csv')))

    fin_data = pd.DataFrame()  # Initialize an empty DataFrame.

    for i in range(len(csv_files)):
        fileName = csv_files[i]
        try:
            opts = pd.read_csv(fileName)
        except Exception as e:
            continue
        if opts.shape[1] == 11:
            dtype_dict = {
                'column1': 'str',
                'column2': 'float64',
                'column3': 'str',
                'column4': 'str',
                'column5': 'datetime64[ns]',
                'column6': 'float64',
                'column7': 'datetime64[ns]',
                'column8': 'float64',
                'column9': 'float64',
                'column10': 'str',
                'column11': 'float64'
            }
            tempT = pd.read_csv(fileName,dtype = dtype_dict).dropna(how='all')
        else:
            continue
        if fin_data.empty:
            fin_data = pd.concat([fin_data, tempT])
        else:
            is_duplicated = tempT.isin(fin_data).all(axis=1)
            non_duplicated_data = tempT[~is_duplicated]
            fin_data = pd.concat([fin_data, non_duplicated_data])
            fin_data = fin_data.reset_index(drop=True)

    return fin_data


def oneGrid(D, FresnelR_H, N, M, exM, kapa):
    # N defines an N-by-N matrix; M is the number of samples along the Tx-Rx path.
    numEx = int(np.floor(M * kapa))
    tempMatrix = np.zeros((N, M), dtype=complex)
    exTxRxMatrix_Tx = np.zeros((N, numEx), dtype=complex)
    exTxRxMatrix_Rx = np.zeros((N, numEx), dtype=complex)
    for count1 in range(N):
        # Compute the central region.
        for count2 in range(M):
            x = (2 * count2 - 1) / (2 * M) * D
            y = (1 + 1 / N - (2 * count1) / N) * FresnelR_H
            tempMatrix[count1, count2] = x + 1j * y
        # Compute the surrounding context before and after the central region.
        for k in range(numEx):
            xEx_Tx = (1 / (2 * M) - (numEx + 1 - k) / M) * D
            xEx_Rx = (1 - 1 / (2 * M) + k / M) * D
            yEx = np.imag(tempMatrix[count1, 1])
            exTxRxMatrix_Tx[count1, k] = xEx_Tx + 1j * yEx
            exTxRxMatrix_Rx[count1, k] = xEx_Rx + 1j * yEx
    xx = np.real(np.concatenate((exTxRxMatrix_Tx, tempMatrix, exTxRxMatrix_Rx), axis=1))
    yy = np.imag(np.concatenate((exTxRxMatrix_Tx, tempMatrix, exTxRxMatrix_Rx), axis=1))
    zz = np.zeros((N, exM))
    result = {
        'x': xx,
        'y': yy,
        'z': zz
    }
    return result

def ll_to_meter(longitude, latitude, x0, y0):
    """
    Convert longitude and latitude to meter coordinates.

    Parameters:
        longitude (float): Longitude in decimal degrees.
        latitude (float): Latitude in decimal degrees.
        x0 (float): Reference point longitude in decimal degrees.
        y0 (float): Reference point latitude in decimal degrees.

    Returns:
        tuple: (x, y) coordinates in meters.
    """
    R = 6371000  # Earth radius in meters

    # Convert degrees to radians
    lon_rad = np.deg2rad(longitude)
    lat_rad = np.deg2rad(latitude)
    lon0_rad = np.deg2rad(x0)
    lat0_rad = np.deg2rad(y0)

    # Calculate the differences
    d_lon = lon_rad - lon0_rad
    d_lat = lat_rad - lat0_rad

    # Calculate x and y in meters
    x = R * d_lon * np.cos(lat0_rad)
    y = R * d_lat

    return x, y

def meter_to_ll(x, y, x0, y0):
    R = 6371000 #Earth radius in meters

    # Convert degrees to radians
    lon0Rad = np.deg2rad(x0)
    lat0Rad = np.deg2rad(y0)

    # Calculate longitude and latitude in radians
    lonRad = lon0Rad + (x / (R * np.cos(lat0Rad)))
    latRad = lat0Rad + (y / R)

    # Convert radians to degrees
    longitude = np.rad2deg(lonRad)
    latitude = np.rad2deg(latRad)
    return longitude, latitude

def calMaxFresnelZoneRadius(frequency_MHz, visualAngle, Tx_longitude, Tx_latitude, Tx_altitude, Tx_antennaHeight, Rx_longitude, Rx_latitude, Rx_altitude, Rx_antennaHeight):
    #lambda = 3e8 / (frequency_MHz*10^6);
    x, y = ll_to_meter(Rx_longitude, Rx_latitude, Tx_longitude, Tx_latitude)
    disBtwTxRx = math.sqrt(x ** 2 + y ** 2 + ((Tx_altitude + Tx_antennaHeight) - (Rx_altitude + Rx_antennaHeight)) ** 2)
    FresnelR_H = 0.5 * disBtwTxRx * math.tan(visualAngle['H'])
    FresnelR_V = 0.5 * disBtwTxRx * math.tan(visualAngle['V'])
    return FresnelR_H, FresnelR_V, disBtwTxRx

def formatMap(frequency_MHz, visualAngle, Tx_longitude, Tx_latitude, Tx_altitude, Tx_antennaHeight, Rx_longitude, Rx_latitude, Rx_altitude, Rx_antennaHeight, N, M, exM, kapa):
    #longitude is x; latitude is y
    # Compute the rotated coordinates.
    FresnelR_H, FresnelR_V, disBtwTxRx = calMaxFresnelZoneRadius(
        frequency_MHz, visualAngle, Tx_longitude, Tx_latitude, Tx_altitude, Tx_antennaHeight,
        Rx_longitude, Rx_latitude, Rx_altitude, Rx_antennaHeight
    )
    position = oneGrid(disBtwTxRx, FresnelR_H, N, M, exM, kapa)
    px, py, pz = position['x'], position['y'], position['z']
    rotatedXYZ = np.concatenate((px.reshape(1,-1), py.reshape(1,-1), pz.reshape(1,-1)), axis=0)

    # Compute the inverse rotation matrix invH.
    H = calRotateH(Tx_longitude, Tx_latitude, Tx_altitude, Tx_antennaHeight, Rx_longitude, Rx_latitude, Rx_altitude, Rx_antennaHeight)
    invH = np.linalg.pinv(H)

    # Recover the coordinates before rotation.
    XYZ = invH @ rotatedXYZ

    # Convert to the geographic coordinate system.
    XYZ_degree = 0 * XYZ
    for count in range(XYZ.shape[1]):
        temp_x = XYZ[0, count]
        temp_y = XYZ[1, count]
        temp_z = XYZ[2, count]
        alpha, beta = meter_to_ll(temp_x, temp_y, Tx_longitude, Tx_latitude)
        gamma = temp_z + (Tx_altitude + Tx_antennaHeight)
        XYZ_degree[:, count] = [alpha, beta, gamma]
    gpsGrid = XYZ_degree[0,:].T + 1j * XYZ_degree[1,:].T
    return gpsGrid, FresnelR_H, FresnelR_V, disBtwTxRx

def calRotateH(Tx_longitude, Tx_latitude, Tx_altitude, Tx_antennaHeight, Rx_longitude, Rx_latitude, Rx_altitude, Rx_antennaHeight):
    x, y = ll_to_meter(Rx_longitude, Rx_latitude, Tx_longitude, Tx_latitude)
    z = (Rx_altitude + Rx_antennaHeight) - (Tx_altitude + Tx_antennaHeight)
    r1 = math.sqrt(x ** 2 + y ** 2)
    r2 = math.sqrt(r1 ** 2 + z ** 2)
    cosTheta = x / r1
    sinTheta = y / r1
    cosPhi = r1 / r2
    sinPhi = z / r2
    H = np.array([
        [cosPhi * cosTheta, cosPhi * sinTheta, sinPhi],
        [-sinTheta, cosTheta, 0],
        [-sinPhi * cosTheta, -sinPhi * sinTheta, cosPhi]
    ])
    return H

def is_picklable(obj):
    try:
        pickle.dumps(obj)
        return True
    except Exception:
        return False

def genFeatureVector(QGIS_output, QGIS_output_cityType, M, N, numRxData, Tx_longitude, Tx_latitude, Tx_altitude, Tx_antennaHeight, rxData_Altitude, Rx_antennaHeight):
    # Altitude.
    lon = np.reshape(QGIS_output['longitude'].values, (M * N, numRxData))
    lat = np.reshape(QGIS_output['latitude'].values, (M * N, numRxData))
    alt = np.reshape(QGIS_output['DN'].values, (M * N, numRxData))

    FV = np.zeros((M * N, numRxData))
    rotatedXYZMatrix = np.zeros((3, M * N, numRxData))
    for indSample in range(numRxData):
        lonLatAlt = np.array([lon[:, indSample], lat[:, indSample], alt[:, indSample]])
        # Convert to meter-based coordinates.
        XYZ = lonLatAlt * 0
        for count in range(M * N):
            x, y = ll_to_meter(lonLatAlt[0, count].item(), lonLatAlt[1, count].item(), Tx_longitude, Tx_latitude)
            z = lonLatAlt[2, count].item() - (Tx_altitude + Tx_antennaHeight)
            XYZ[:, count] = [x, y, z]
        # Compute the transformation matrix.
        H = calRotateH(
            Tx_longitude, Tx_latitude, Tx_altitude, Tx_antennaHeight, rxData_Altitude['Longitude'].iloc[indSample],
            rxData_Altitude['Latitude'].iloc[indSample], rxData_Altitude['DN'].iloc[indSample], Rx_antennaHeight
        )
        # Apply the matrix transformation.
        rotatedXYZ = H @ XYZ
        rotatedXYZMatrix[:,:, indSample] = rotatedXYZ
        # Absolute-elevation matrix.
        FV[:, indSample] = rotatedXYZ[2,:]

    # Urban-area type.
    cityType = np.reshape(QGIS_output_cityType['Type'].values, (M * N, numRxData))
    return FV, cityType, rotatedXYZMatrix

def genTargetValue(Pt_dBm, frequency_MHz, rxData_Altitude, Tx_longitude, Tx_latitude, Tx_altitude, Tx_antennaHeight, Rx_antennaHeight):
    lambda_value = 3e8 / (frequency_MHz * 10 ** 6)
    Pt = 10 ** (0.1 * Pt_dBm)
    TV = np.zeros((1, rxData_Altitude.shape[0]),dtype=float)
    for count in range(rxData_Altitude.shape[0]):
        x, y = ll_to_meter(rxData_Altitude['Longitude'].iloc[count], rxData_Altitude['Latitude'].iloc[count],
                           Tx_longitude, Tx_latitude)
        d = math.sqrt(x ** 2 + y ** 2 + ((Tx_altitude + Tx_antennaHeight) - (rxData_Altitude['DN'].iloc[count] + Rx_antennaHeight)) ** 2)
        Pr_free = cal_Pr_free(Pt, lambda_value, d, 2)
        TV[0, count] = rxData_Altitude['RSSI'].iloc[count] - Pr_free
    return TV

def list_ml_files():
    """List all files in the current directory whose names start with 'ML_'."""
    ml_files = [f for f in os.listdir('.') if f.startswith('ML_')]
    return ml_files

def list_history_files():
    """List all files in the current directory whose names start with 'history_'."""
    history_files = [f for f in os.listdir('.') if f.startswith('history_model_from_')]
    return history_files

def list_history_TL_files():
    """List files in the current directory whose names start with 'history_' or 'TL_'."""
    history_TL_files = [
        f for f in os.listdir('.')
        if f.startswith('history_model_from_') or f.startswith('TL_model_')
    ]
    return history_TL_files

def list_history_TL_Predict_files():
    """List files in the current directory whose names start with 'history_' or 'TL_'."""
    history_TL_files = [
        f for f in os.listdir('.')
        if f.startswith('history_model_from_') or f.startswith('TL_model_') or f.startswith('Predict_model_')
    ]
    return history_TL_files


def list_TL_files():
    """List all files in the current directory whose names start with 'TL_'."""
    TL_files = [f for f in os.listdir('.') if f.startswith('TL_')]
    return TL_files

def list_Predict_files():
    """List all files in the current directory whose names start with 'Predict_'."""
    Predict_files = [f for f in os.listdir('.') if f.startswith('Predict_')]
    return Predict_files

def get_user_selection(ml_files):
    """Prompt the user to select multiple numbered entries."""
    for idx, file in enumerate(ml_files, 1):
        print(f"{idx}: {file}")

    user_input = input("Select one or more file numbers, separated by commas: ")
    selections = list(map(int, user_input.split(',')))
    # Validate the selected entries.
    for selection in selections:
        if selection < 1 or selection > len(ml_files):
            print(f"Invalid selection: {selection}")
            return None
    return selections

def get_folder_path():
    while True:
        folder_csv_path = input("Enter the CSV directory path: ").strip()
        folder_map_path = input("Enter the database directory path: ").strip()
        folder_fun_path = input("Enter the functions directory path: ").strip()

        # Verify that the paths exist.
        if not os.path.exists(folder_csv_path):
            print(f"Error: path '{folder_csv_path}' does not exist. Please enter it again.")
            continue
        if not os.path.exists(folder_map_path):
            print(f"Error: path '{folder_map_path}' does not exist. Please enter it again.")
            continue
        if not os.path.exists(folder_fun_path):
            print(f"Error: path '{folder_fun_path}' does not exist. Please enter it again.")
            continue

        # Verify that each path is a directory.
        if not os.path.isdir(folder_csv_path):
            print(f"Error: '{folder_csv_path}' is not a folder. Please enter it again.")
            continue
        if not os.path.isdir(folder_map_path):
            print(f"Error: '{folder_map_path}' is not a folder. Please enter it again.")
            continue
        if not os.path.isdir(folder_fun_path):
            print(f"Error: '{folder_fun_path}' is not a folder. Please enter it again.")
            continue

        return folder_csv_path, folder_map_path, folder_fun_path



def run_qgis_processing(csv_path, gpkg_path, output_path, fun_path):
    if platform.system() == "Darwin":
        qgis_python = "/Applications/QGIS-LTR.app/Contents/MacOS/bin/python3"
    elif platform.system() == "Linux":
        qgis_python = "/usr/bin/python3"
    elif platform.system() == "Windows":
        qgis_python = r"C:\Program Files\QGIS 3.40.5\apps\Python312\python.exe"
    else:
        raise OSError("Unsupported OS")
    script_path = fun_path + "/qgis_processor.py"

    subprocess.run([
        qgis_python,
        script_path,
        csv_path,
        gpkg_path,
        output_path
    ])

def select_gpkg_file(folder_path):
    # Verify that the directory exists.
    if not os.path.isdir(folder_path):
        print(f"Error: folder '{folder_path}' does not exist.")
        return None

    # Find all .gpkg files.
    gpkg_files = list(Path(folder_path).glob("*.gpkg"))
    if not gpkg_files:
        print(f"No .gpkg files were found in '{folder_path}'.")
        return None

    # Display the available choices.
    print("\nFound the following .gpkg files:")
    for i, file in enumerate(gpkg_files, 1):
        print(f"{i}. {file.name}")

    # Prompt the user to select a file.
    while True:
        try:
            choice = input("\nSelect a file number (q to quit, i to ignore): ").strip()
            if choice.lower() == 'q':
                return None
            if choice.lower() == 'i':
                return set()

            choice_idx = int(choice) - 1
            if 0 <= choice_idx < len(gpkg_files):
                return str(gpkg_files[choice_idx])
            else:
                print(f"Error: please enter a number between 1 and {len(gpkg_files)}.")
        except ValueError:
            print("Error: please enter a valid number.")

def generate_grid_points(lon_min, lon_max, lat_min, lat_max, N, M, output_file):
    """
    Generate a longitude-latitude grid and save it to a CSV file.

    Args:
        lon_min: Minimum longitude.
        lon_max: Maximum longitude.
        lat_min: Minimum latitude.
        lat_max: Maximum latitude.
        N: Number of samples along the longitude axis.
        M: Number of samples along the latitude axis.
        output_file: Output CSV file name.
    """

    # Generate a file name automatically when output_path is a directory.
    if os.path.isdir(output_file):
        output_file = os.path.join(output_file, "grid_points.csv")
    else:
        output_file = output_file

    # Compute longitude and latitude increments.
    lon_step = (lon_max - lon_min) / (N - 1) if N > 1 else 0
    lat_step = (lat_max - lat_min) / (M - 1) if M > 1 else 0

    # Generate the grid points.
    points = []
    point_id = 0
    for i in range(M):
        lat = lat_min + i * lat_step
        for j in range(N):
            lon = lon_min + j * lon_step
            point = [
                0,  # id (default: 0)
                0,  # NodeID (default: 0)
                0,  # RouteInfo (default: 0)
                0,  # DestID (default: 0)
                0,  # SendTime (default: 0)
                0,  # SeqID (default: 0)
                0,  # RecvTime (default: 0)
                lat,  # Latitude
                lon,  # Longitude
                0,  # EncData (default: 0)
                -999  # RSSI (default: -999)
            ]
            points.append(point)
            point_id += 1

    # Ensure that the output directory exists.
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    # Write the CSV file.
    with open(output_file, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        # Write the header.
        writer.writerow([
            'id', 'NodeID', 'RouteInfo', 'DestID', 'SendTime',
            'SeqID', 'RecvTime', 'Latitude', 'Longitude',
            'EncData', 'RSSI'
        ])
        # Write the data rows.
        writer.writerows(points)

    print(f"Generated {len(points)} point(s) and saved them to {output_file}.")
    return

def cal_Pr_free(Pt, lambda_value, d, eta):
    Pr_free = 10 * np.log10(   (Pt * lambda_value ** 2) / ( (4*np.pi)**2 * d ** eta)    )
    return Pr_free

def cal_Pr_free_show(Pt, fre, d, eta):
    lambda_value = 3e8/(fre*10**6)
    Pr_free = 10 * np.log10(   (Pt * lambda_value ** 2) / ( (4*np.pi)**2 * d ** eta)    )
    return Pr_free


def merge_csv_files(file_a, file_b, output_file):
    # 1. Read CSV files A and B.
    df_a = pd.read_csv(file_a)
    df_b = pd.read_csv(file_b)

    # 2. Replace null values in file A's measuredHeight column with zero.
    df_a["measuredHeight"] = df_a["measuredHeight"].fillna(0)
    # Linearly interpolate null values in file B's DN column from adjacent valid values.
    df_b["DN"] = df_b["DN"].interpolate(method='linear')  # Linear interpolation.

    # 3. Verify that both files have the same row count before row-wise addition.
    if len(df_a) != len(df_b):
        print("Warning: the two CSV files have different row counts, which may cause calculation errors.")
    else:
        # 4. Add file A's measuredHeight to file B's DN and replace file B's DN column.
        df_b["DN"] = df_b["DN"] + df_a["measuredHeight"]

        # 5. Save the modified file B, either in place or to a separate output file.
        #df_b.to_csv(file_b, index=False)  # Overwrite the original file.
        df_b.to_csv(output_file, index=False)  # Save to a separate file.

        try:
            os.remove(file_a)
            os.remove(file_b)
            #print(f"Deleted original files: {file_a} and {file_b}")
        except FileNotFoundError:
            print("File does not exist and cannot be deleted.")
        except PermissionError:
            print("Insufficient permissions to delete the file.")

    return


def input_with_default(prompt, default):
    user_input = input(f"{prompt} (press Enter to use the default {default}): ").strip()
    return default if not user_input else type(default)(user_input)  # Convert to the default value's type.



def get_gpkg_files(folder_path, pattern):
    # Verify that the directory exists.
    if not os.path.isdir(folder_path):
        print(f"Error: folder '{folder_path}' does not exist.")
        return []

    # Find matching .gpkg files.
    # Use glob to find files containing "_building.gpkg".
    # rglob searches recursively; glob searches only the current level.
    gpkg_files = list(Path(folder_path).glob(pattern))
    # Assign the results to gpkg_path_building.
    # glob returns an empty list when no file matches.
    gpkg_path = [str(p) for p in gpkg_files]

    return gpkg_path[0] if gpkg_path else None  # Return the matching path, or None if no file was found.

def get_ML_files(folder_path, pattern):
    # Verify that the directory exists.
    if not os.path.isdir(folder_path):
        print(f"Error: folder '{folder_path}' does not exist.")
        return []

    # Find matching .gpkg files.
    # Use glob to find files containing "_building.gpkg".
    # rglob searches recursively; glob searches only the current level.
    gpkg_files = list(Path(folder_path).glob(pattern))
    # Assign the results to gpkg_path_building.
    # glob returns an empty list when no file matches.
    gpkg_path = [str(p) for p in gpkg_files]

    return gpkg_path if gpkg_path else None  # Return the matching paths, or None if no file was found.


class GeoQueryEngine:
    def __init__(self):
        self.raster_data = None

    def load_raster(self, path):
        self.raster_data = rasterio.open(path)

    def sample_raster_fast(self, gdf, lon_name, lat_name):
        """
        Sample the raster efficiently by extracting elevations for all points in one operation.
        """
        # Generate coordinate pairs: [(lon1, lat1), (lon2, lat2), ...].
        coords = zip(gdf[lon_name], gdf[lat_name])
        # Use sample for batch sampling; it returns a generator directly.
        return [float(val[0]) for val in self.raster_data.sample(coords)]

def load_map_data(csv_path, map_path, output_path, pattern):
    # 1. Read the CSV data.
    df = pd.read_csv(csv_path)

    # --- Detect column names automatically. ---
    col_map = {c.lower(): c for c in df.columns}
    lon_keywords = ['longitude', 'Longitude', 'lon', 'lng', 'x']
    lat_keywords = ['latitude', 'Latitude', 'lat', 'y']
    lon_name = next((col_map[k] for k in lon_keywords if k in col_map), None)
    lat_name = next((col_map[k] for k in lat_keywords if k in col_map), None)

    if not lon_name or not lat_name:
        raise KeyError("Could not identify longitude and latitude columns in the CSV file.")

    # --- Convert to a GeoDataFrame. ---
    gdf_points = gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(df[lon_name], df[lat_name]),
        crs="EPSG:6668"
    )

    pattern_lower = pattern.lower()

    # 2. Core processing.
    if "building" in pattern_lower or "citytype" in pattern_lower:
        is_building = "building" in pattern_lower
        layer = "building" if is_building else "cityType"
        target_field = "measuredHeight" if is_building else "Type"
        # Use 20 as the default cityType and 0.0 as the default building height.
        default_val = 0.0 if is_building else 20

        import os
        use_default = False
        if not map_path or not os.path.exists(map_path):
            print(f"Warning: map path is invalid or missing ({map_path}); using default value {default_val}.")
            use_default = True

        if not use_default:
            # Load the vector map.
            try:
                map_gdf = gpd.read_file(map_path, layer=layer)
                if map_gdf.crs != "EPSG:6668":
                    map_gdf = map_gdf.to_crs("EPSG:6668")

                # Updated workflow.
                # 1. Perform the spatial join.
                # sjoin preserves the original gdf_points index.
                result_gdf = gpd.sjoin(gdf_points, map_gdf[[target_field, 'geometry']], how="left", predicate="within")

                # 2. Deduplicate by original index rather than by longitude and latitude.
                # This has two effects:
                # - All 23 source points at identical coordinates remain because their indices differ.
                # - If one point matches two polygons, only the first match remains, preserving a one-to-one result.
                result_gdf = result_gdf[~result_gdf.index.duplicated(keep='first')]

                # 3. Fill groups where measuredHeight is present only in the first row.
                # Grouping by coordinates broadcasts a value such as 20.7 to every row in that group.
                if 'measuredHeight' in result_gdf.columns:
                    result_gdf['measuredHeight'] = result_gdf.groupby([lat_name, lon_name])['measuredHeight'].transform('max')

                # 4. Fill values missing because the spatial join failed.
                result_gdf[target_field] = result_gdf[target_field].fillna(default_val)

                # 5. Convert to a regular DataFrame and clean it.
                df = pd.DataFrame(result_gdf.drop(columns=['geometry', 'index_right'], errors='ignore'))
                # End of the updated workflow.
            except Exception as e:
                print(f"Error while reading map: {e}. Switching to default-value mode.")
                use_default = True

        if use_default:
            # Assign default-value columns directly to the original DataFrame.
            df[target_field] = default_val
            # df is already a pandas DataFrame, so no geometry column needs to be dropped.

        # --- Common post-processing. ---
        if not is_building:
            df[target_field] = df[target_field].astype(int)
            # Rename the column when its name is not "Type".
            if target_field != "Type":
                df = df.rename(columns={target_field: "Type"})

    elif "altitude" in pattern_lower or "dem" in pattern_lower:
        print(f"Mode: {pattern} | Fast altitude sampling...")
        engine = GeoQueryEngine()
        engine.load_raster(map_path)
        sampled_data = engine.sample_raster_fast(df, lon_name, lat_name)
        df["DN"] = sampled_data

        # --- Fallback: use the area's mean elevation. ---
        # Convert common raster NoData sentinels to NaN for uniform handling.
        # Common invalid values include -9999, -32767, and -32768.
        invalid_values = [-9999, -32767, -32768]
        df["DN"] = df["DN"].replace(invalid_values, np.nan)

        # Identify points whose raster sampling failed (NaN).
        nan_count = df["DN"].isna().sum()
        if nan_count > 0:
            # Compute the mean elevation of all valid samples in the current CSV file.
            area_avg_alt = df["DN"].mean()

            # Fall back to zero if sampling failed for the entire area and the mean is NaN.
            if pd.isna(area_avg_alt):
                area_avg_alt = 0.0
                print("Warning: no valid altitude data found in this area; filled all values with 0.0.")
            else:
                print(f"Detected {nan_count} failed sample point(s); filled them with area mean altitude {area_avg_alt:.2f} m.")

            # Fill the missing values.
            df["DN"] = df["DN"].fillna(area_avg_alt)

    # Save the result.
    df.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"Task completed. Saved to: {output_path}")
    return df


def load_area_max_data(csv_path, map_path, output_path, pattern, M, visualAngle):
    # 1. Read the CSV data.
    df = pd.read_csv(csv_path)

    col_map = {c.lower(): c for c in df.columns}
    lon_name = next((col_map[k] for k in ['longitude', 'lon', 'x'] if k in col_map), None)
    lat_name = next((col_map[k] for k in ['latitude', 'lat', 'y'] if k in col_map), None)
    dist_name = next((col_map[k] for k in ['disbtwtxrx', 'distance'] if k in col_map), "disBtwTxRx")

    if not lon_name or not lat_name:
        raise KeyError("Could not identify longitude and latitude columns in the CSV file.")

    # --- 2. Generate geometries with Shapely 2.x vectorization. ---
    points = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df[lon_name], df[lat_name]), crs="EPSG:6668")
    points_m = points.to_crs(epsg=3857)
    coords = points_m.geometry.get_coordinates()

    L = df[dist_name].values / (M - 1)
    # visualAngle must be in radians; use np.deg2rad for values expressed in degrees.
    D = L * np.tan(visualAngle)

    x, y = coords['x'].values, coords['y'].values
    # Create rectangles using vectorized operations.
    rects = shapely.box(x - L/2, y - D/2, x + L/2, y + D/2)
    gdf_area = gpd.GeoDataFrame(df, geometry=rects, crs="EPSG:3857").to_crs(epsg=6668)

    pattern_lower = pattern.lower()

    # --- 3. Optimize vector-map processing by retaining only the Building sjoin. ---
    if "building" in pattern_lower:
        target_field = "measuredHeight"
        default_val = 0.0
        if os.path.exists(map_path):
            map_gdf = gpd.read_file(map_path, layer="building")[[target_field, 'geometry']]
            if map_gdf.crs != "EPSG:6668":
                map_gdf = map_gdf.to_crs("EPSG:6668")
            joined = gpd.sjoin(gdf_area, map_gdf, how="left", predicate="intersects")
            res = joined.groupby(joined.index)[target_field].max()
            df[target_field] = res.reindex(df.index, fill_value=default_val).values
        else:
            df[target_field] = default_val



    # --- 4. Optimize raster processing shared by CityType and Altitude. ---
    elif any(k in pattern_lower for k in ["citytype", "altitude", "dem"]):
        is_citytype = "citytype" in pattern_lower
        target_col = "Type" if is_citytype else "DN"
        if map_path is None or not os.path.exists(map_path):
            # Fill CityType with 20; altitude typically uses 0 or 10.
            default_fill = 20 if is_citytype else 0
            df[target_col] = default_fill
            if is_citytype:
                df[target_col] = df[target_col].astype(int)
            # Skip the subsequent rasterio processing block.
        else:
            with rasterio.Env(): # Use an isolated rasterio environment.
                if is_citytype:
                    print("Converting CityType vector map to a temporary raster for faster extraction...")
                    # Read the vector layer.
                    map_gdf = gpd.read_file(map_path, layer="cityType")
                    if map_gdf.crs != "EPSG:6668":
                        map_gdf = map_gdf.to_crs("EPSG:6668")

                    # Define rasterization resolution; 0.0001 degrees is approximately 10 meters and can be adjusted to map precision.
                    res_deg = 0.0001
                    b = map_gdf.total_bounds
                    # Compute the output shape and transformation matrix.
                    out_shape = (int((b[3]-b[1])/res_deg) + 1, int((b[2]-b[0])/res_deg) + 1)
                    full_transform = rasterio.transform.from_bounds(*b, out_shape[1], out_shape[0])

                    # Convert vectors to an in-memory array for the main performance improvement.
                    full_data = features.rasterize(
                        [(shape, val) for shape, val in zip(map_gdf.geometry, map_gdf['Type'])],
                        out_shape=out_shape, transform=full_transform, fill=20 # Default fill value: 20.
                    )
                    nodata = -9999
                    gdf_raster_crs = gdf_area # Already in EPSG:6668.
                else:
                    # Keep the altitude/DEM processing unchanged.
                    print("Processing altitude raster...")
                    src = rasterio.open(map_path)
                    nodata = src.nodata if src.nodata is not None else -9999
                    gdf_raster_crs = gdf_area.to_crs(src.crs)
                    total_bounds = gdf_raster_crs.total_bounds
                    full_window = src.window(*total_bounds).round()
                    full_data = src.read(1, window=full_window)
                    full_transform = src.window_transform(full_window)
                    src.close()

                # --- Shared, optimized window-extraction logic. ---
                inv_trans = ~full_transform
                bounds = gdf_raster_crs.geometry.bounds
                c1, r1 = inv_trans * (bounds['minx'].values, bounds['maxy'].values)
                c2, r2 = inv_trans * (bounds['maxx'].values, bounds['miny'].values)

                r_starts = np.clip(np.floor(r1).astype(int), 0, full_data.shape[0])
                r_ends = np.clip(np.ceil(r2 + 1).astype(int), 0, full_data.shape[0])
                c_starts = np.clip(np.floor(c1).astype(int), 0, full_data.shape[1])
                c_ends = np.clip(np.ceil(c2 + 1).astype(int), 0, full_data.shape[1])

                results = []
                for rs, re, cs, ce in zip(r_starts, r_ends, c_starts, c_ends):
                    chunk = full_data[rs:re, cs:ce]
                    if chunk.size > 0:
                        valid = chunk[chunk != nodata]
                        if valid.size > 0:
                            if is_citytype:
                                # Extract the mode (the most frequent Type).
                                counts = np.bincount(valid.astype(int))
                                results.append(np.argmax(counts))
                            else:
                                # Extract the maximum Altitude.
                                results.append(valid.max())
                        else: results.append(np.nan)
                    else: results.append(np.nan)

                df[target_col] = results
                # Fill missing values and format the result.
                fill_val = 20 if is_citytype else df[target_col].mean()
                df[target_col] = df[target_col].fillna(fill_val)
                if is_citytype: df[target_col] = df[target_col].astype(int)

    # 5. Save the result.
    df.to_csv(output_path, index=False, encoding='utf-8-sig')
    print("Processing completed.")
    return df


def clean_folder_except(folder_path, prefix_to_keep):
    """
    Delete all files in a directory except those whose names start with a specified prefix.

    Args:
        folder_path (str or Path): Path to the target directory.
        prefix_to_keep (str): File-name prefix to retain.
    """
    # 1. Convert the input to a Path object.
    folder = Path(folder_path)

    # 2. Verify that the path exists and is a directory.
    if not folder.exists():
        print(f"Skipping cleanup: path does not exist. -> {folder_path}")
        return
    if not folder.is_dir():
        print(f"Skipping cleanup: specified path is not a directory -> {folder_path}")
        return

    print(f"Cleaning folder: {folder.absolute()}")
    print(f"Retaining prefix as: '{prefix_to_keep}' file(s)...")

    count = 0
    # 3. Iterate over the directory.
    for file_path in folder.iterdir():
        # Process files only, not subdirectories.
        if file_path.is_file():
            # Check whether the file name lacks the retained prefix.
            if not file_path.name.startswith(prefix_to_keep):
                try:
                    file_path.unlink()  # Delete the file.
                    # print(f"  [Deleted]: {file_path.name}")
                    count += 1
                except Exception as e:
                    print(f"  [Error] Failed to delete {file_path.name}: {e}")

    print(f"Cleanup complete. Deleted {count} file(s).")



def runFineTuning(args, modelToBeFineTuned):
    selected_folder_csv = args[0]
    selected_folder_map = args[1]
    frequency = float(args[9])
    SF = int(args[10])
    EIRP = float(args[11])
    fixAntenna_lng = float(args[12])
    fixAntenna_lat = float(args[13])
    fixAntenna_alt = float(args[14])
    fixAntenna_height = float(args[15])
    moveAntenna_height = fixAntenna_height
    fine_tuning = args[17]
    fine_tuning = [float(x) for x in fine_tuning]
    fine_tuning_lng = float(args[18])
    fine_tuning_lat = float(args[19])

    genFineTuningCSV(selected_folder_csv, fine_tuning, fine_tuning_lng, fine_tuning_lat)
    main_collect_data.start_collect_logic(
        selected_folder_csv,
        selected_folder_map,
        [],
        frequency,
        SF,
        EIRP,
        fixAntenna_lng,
        fixAntenna_lat,
        fixAntenna_alt,
        fixAntenna_height,
        moveAntenna_height
    )

    contentReadDataIndex = get_ML_files(selected_folder_csv, "ML_myTempExp_*")
    try:
        transfer_learning_main.run_transfer_learning(
            selected_folder_csv,
            num_test_per = str(0.01), # Fraction of new data used for prediction; 0.01 uses 1% and reserves 99% for model generation.
            user_input = 1,
            model_path = modelToBeFineTuned,
            data_index = list(range(1,len(contentReadDataIndex)+1)),
            content_data_index = contentReadDataIndex
        )
        print("Fine-tuning complete!")
        clean_folder_except(selected_folder_csv, "TL_model_")
    except Exception as e:
        print(f"Fine-tuning process failed: {e}")
        raise e

    return True



def genFineTuningCSV(selected_folder_csv, fine_tuning, fine_tuning_lng, fine_tuning_lat):
    """
    Generate the fine_tuning_nearfield.csv file.
    """

    # Construct the file path.
    os.makedirs(selected_folder_csv, exist_ok=True)
    file_path = os.path.join(selected_folder_csv, 'fine_tuning_nearfield.csv')

    # Write the CSV file.
    try:
        with open(file_path, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            # Uncomment the following line if a header is required.
            writer.writerow(['longitude', 'latitude', 'rssi'])

            for rssi in fine_tuning:
                # Assume every point is offset by one meter, for example one meter east.
                # The points can instead be distributed around the antenna if required.
                new_lng = fine_tuning_lng
                new_lat = fine_tuning_lat

                writer.writerow([new_lng, new_lat, rssi])

        print(f"File generated successfully: {file_path}")
    except Exception as e:
        print(f"File generation failed: {e}")



def augment_centrosymmetric(origFV, origTV, origAlt):
    """
    Apply a point-reflection transform while preserving physical channel semantics.

    origFV shape: (31, 36, 5, 1498), with five channels indexed from 0 through 4.
    """
    # 1. Reverse the spatial dimensions (axes 0 and 1).
    # This reverses the matrix structure of every channel.
    flippedFV = np.flip(origFV, axis=(0, 1)).copy()

    # 2. Correct the physical semantics of channel 1, the gradient channel.
    # Point reflection reverses the axis-1 gradient direction when viewed from Rx toward Tx.
    # Negate it so the model does not interpret the terrain-slope direction as unchanged.
    flippedFV[:, :, 1, :] = -flippedFV[:, :, 1, :]

    # 3. Concatenate feature matrices along the sample dimension (axis=-1).
    augFV = np.concatenate([origFV, flippedFV], axis=-1)

    # 4. Concatenate the target values.
    # Assume the RSS prediction target is invariant under reflection by reciprocity.
    augTV = np.concatenate([origTV, origTV], axis=-1)

    # 5. Duplicate the corresponding DataFrame rows.
    augAlt = pd.concat([origAlt, origAlt], axis=0).reset_index(drop=True)

    return augFV, augTV, augAlt



def barrier_and_cleanup(futures_to_wait=None, timeout=120):
    """
    Isolate and reset distributed-computing resources.

    Attempt to obtain an active client automatically when none is supplied.
    """
    # --- Obtain the active Dask client automatically. ---
    try:
        client = get_client()
    except ValueError:
        print(">>> Error: no active Dask Client detected. Cleanup cannot be performed.")
        return

    print("\n" + "="*50)
    print(">>> [Intermission] Starting resource isolation procedure...")

    # --- Step 1: Force synchronization. ---
    if futures_to_wait is not None:
        print(">>> Waiting for all asynchronous tasks to finish physically...")
        # Normalize dictionaries and lists into a form accepted by wait.
        if isinstance(futures_to_wait, dict):
            futures_to_wait = list(futures_to_wait.values())
        elif not isinstance(futures_to_wait, list):
            futures_to_wait = [futures_to_wait]

        # This prevents a forced restart while tasks are still running.
        wait(futures_to_wait)

    # --- Step 2: Clean up host-side resources. ---
    print(">>> Cleaning main-process memory and session state...")
    tf.keras.backend.clear_session()
    gc.collect()

    # --- Step 3: Attempt a worker restart (hard reset). ---
    try:
        print(f">>> Attempting physical worker restart (timeout {timeout}s)...")
        client.restart(timeout=timeout)
        print(">>> Physical restart succeeded. Worker resources have been reset.")
    except Exception as e:
        print(f">>> Physical restart failed or timed out: {e}")
        print(">>> Falling back to soft cleanup...")

        def worker_soft_cleanup():
            import tensorflow as tf
            import gc
            import os
            tf.keras.backend.clear_session()
            gc.collect()
            return f"Worker PID {os.getpid()} cleaned."

        try:
            results = client.run(worker_soft_cleanup)
            print(f">>> Soft cleanup completed. Responding worker count: {len(results)}")
        except Exception as soft_e:
            print(f">>> Soft cleanup also encountered an exception: {soft_e}")

    # --- Step 4: Allow a quiet cooldown period. ---
    print(">>> Running a 5-second quiet cooldown to release TCP ports...")
    time.sleep(5)
    print(">>> Resource isolation completed. Ready for the next stage.")
    print("="*50 + "\n")
