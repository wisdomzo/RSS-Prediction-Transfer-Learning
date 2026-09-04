import os
import sys
import subFun
import pickle
import lzma
import pandas as pd
import numpy as np
from datetime import datetime

def get_app_root_directory():
    if hasattr(sys, '_MEIPASS'):
        return sys._MEIPASS
    else:
        return os.path.abspath(".")

APP_ROOT = get_app_root_directory()
if APP_ROOT not in sys.path:
    sys.path.insert(0, APP_ROOT)


def start_collect_logic(expDataPath, map_path, fun_path, frequency_MHz, SF, Pt_dBm, Tx_longitude, Tx_latitude, Tx_altitude, Tx_antennaHeight, Rx_antennaHeight):
    # Global variables.
    # region
    N = 31# NxN sample points on the Fresnel plane.
    M = 30# Number of samples along the Tx-Rx line.
    kapa = 0.1# Expansion factor for the environment beyond the Tx-Rx segment.
    exM = M + 2 * int(np.floor(kapa * M))
    visualAngle = {
        'H': np.deg2rad(30),# Horizontal half-angle of the field of view, in degrees.
        'V': np.deg2rad(15)# Vertical half-angle of the field of view, in degrees.
    }

    expName = "myTempExp"
    dataPath = expDataPath + "/data.pkl.xz"
    altitudeDataPath = expDataPath + "/rxData_" + expName + "_SF" + str(SF) + "_altitude.csv"

    # Integrate experimental data.
    if os.path.isfile(dataPath):
        with lzma.open(dataPath, 'rb') as f:
            dataStrick = pickle.load(f)
            if 'rxData' in dataStrick: rxData = dataStrick['rxData']
            if 'rxData_Altitude' in dataStrick: rxData_Altitude = dataStrick['rxData_Altitude']
    else:
        rxData = subFun.integrateExpData(expDataPath)
        #####
        all_vars = {key: value for key, value in globals().items()
                    if not key.startswith('__') and subFun.is_picklable(value)}
        with lzma.open(dataPath, 'wb') as saveFile:
            pickle.dump(all_vars, saveFile)
        #####
        rxData.to_csv(expDataPath + "/rxData_" + expName + "_SF" + str(SF) + ".csv", index=False)

    # Add elevation data.
    if 'rxData_Altitude' not in globals():
        while True:
            if os.path.isfile(altitudeDataPath):
                rxData_Altitude = pd.read_csv(altitudeDataPath)
                rxData_Altitude.ffill(inplace=True)
                #####
                if 'all_vars' in globals(): del all_vars
                all_vars = {key: value for key, value in globals().items()
                            if not key.startswith('__') and subFun.is_picklable(value)}
                with lzma.open(dataPath, 'wb') as saveFile:
                    pickle.dump(all_vars, saveFile)
                #####
                break
            else:
                # Add building height to terrain elevation to obtain the effective elevation.
                csv_path = expDataPath + "/rxData_" + expName + "_SF" + str(SF) + ".csv"
                print("\nGenerating Tx-Rx spatial distance with the building map.")
                gpkg_path_building = subFun.get_gpkg_files(map_path, "*_building.gpkg")
                if not gpkg_path_building:
                    print("Building map ignored.")
                    print("\nGenerating Tx-Rx spatial distance with the altitude map.")
                    gpkg_path_altitude = subFun.get_gpkg_files(map_path, "*_altitude.tif")
                    output_path_altitude = expDataPath + "/rxData_" + expName + "_SF" + str(SF) + "_altitude.csv"
                    subFun.load_map_data(csv_path, gpkg_path_altitude, output_path_altitude, "altitude")
                else:
                    output_path_building = expDataPath + "/rxData_" + expName + "_SF" + str(SF) + "_building.csv"
                    subFun.load_map_data(csv_path, gpkg_path_building, output_path_building, "building")
                    print("\nGenerating Tx-Rx spatial distance with the altitude map.")
                    gpkg_path_altitude = subFun.get_gpkg_files(map_path, "*_altitude.tif")
                    output_path_altitude = expDataPath + "/rxData_" + expName + "_SF" + str(SF) + "_altitude_no_building.csv"
                    subFun.load_map_data(csv_path, gpkg_path_altitude, output_path_altitude, "altitude")
                    subFun.merge_csv_files(output_path_building, output_path_altitude, altitudeDataPath)

    # Analyze experimental data.
    # region
    #if expIndex in (1, 2):
    #    Tx_longitude = 133.0474619
    #    Tx_latitude = 33.1848442
    #    Tx_altitude = 228
    #    Tx_antennaHeight = 2.16
    #    Rx_antennaHeight = 1.8
    #elif expIndex in (3, 4):
    #    Tx_longitude = 133.0564234
    #    Tx_latitude = 33.1983187
    #    Tx_altitude = 200
    #    Tx_antennaHeight = 1.79
    #    Rx_antennaHeight = 1.8
    #elif expIndex in (5, 6):
    #    Tx_longitude = 127.7658981
    #    Tx_latitude = 26.2532089
    #    Tx_altitude = 157 # 125 m terrain elevation plus a 32 m building.
    #    Tx_antennaHeight = 2.09
    #    Rx_antennaHeight = 1.83
    #elif expIndex in (7, 8):
    #    Tx_longitude = 127.7739396
    #    Tx_latitude = 26.2477756
    #    Tx_altitude = 150 # 137 m terrain elevation plus a 13 m building.
    #    Tx_antennaHeight = 0
    #    Rx_antennaHeight = 1.83
    #elif expIndex in (9, 10):
    #    Tx_longitude = 127.984681
    #    Tx_latitude = 26.61895
    #    Tx_altitude = 50 # 45 m terrain elevation plus a 5 m building.
    #    Tx_antennaHeight = 0.58
    #    Rx_antennaHeight = 1.83
    #elif expIndex in [11]:
    #    Tx_longitude = 137.7153306
    #   Tx_latitude = 35.27004166
    #    Tx_altitude = 837 # 837 m terrain elevation with no building height.
    #    Tx_antennaHeight = 1.2
    #    Rx_antennaHeight = 0.5 # On the front passenger seat inside the vehicle.
    #elif expIndex in (12, 13):
    #    Tx_longitude = 133.718148
    #    Tx_latitude = 33.62094
    #    Tx_altitude = 121 # 61 m terrain elevation plus a 60 m building.
    #    Tx_antennaHeight = 0.58
    #    Rx_antennaHeight = 1.5
    #else:
    #    sys.exit()
    # endregion

    # Map-based machine-learning inference.
    # Read or generate sample-point data.
    # region
    outputQGISFilesPath = expDataPath + "/outputQGISforML_" + expName + "_SF" + str(SF) + ".csv"
    cityType_outputQGISFilesPath = expDataPath + "/cityType_outputQGISforML_" + expName + "_SF" + str(SF) + ".csv"
    while True:
        if os.path.isfile(outputQGISFilesPath) and os.path.isfile(cityType_outputQGISFilesPath):
            QGIS_output = (pd.read_csv(outputQGISFilesPath).sort_values(by='searchIndex'))
            QGIS_output[['DN']] = QGIS_output[['DN']].ffill()# Forward-fill NaN values.
            QGIS_output_cityType = (pd.read_csv(cityType_outputQGISFilesPath).sort_values(by='searchIndex'))
            QGIS_output_cityType[['Type']] = QGIS_output_cityType[['Type']].fillna(0)  # Fill NaN values.
            break
        else:
            if 'FresnelR_H' not in rxData_Altitude.columns:
                rxData_Altitude['FresnelR_H'] = float(0)
            if 'FresnelR_V' not in rxData_Altitude.columns:
                rxData_Altitude['FresnelR_V'] = float(0)
            if 'disBtwTxRx' not in rxData_Altitude.columns:
                rxData_Altitude['disBtwTxRx'] = float(0)
            altitudeGridMatrix = np.zeros((exM * N, rxData_Altitude.shape[0]),dtype=complex)
            dist_expanded = np.zeros((exM * N, rxData_Altitude.shape[0]))
            for count in range(rxData_Altitude.shape[0]):
                gpsGrid, FresnelR_H, FresnelR_V, disBtwTxRx = subFun.formatMap(
                    frequency_MHz, visualAngle, Tx_longitude, Tx_latitude, Tx_altitude, Tx_antennaHeight,
                    rxData_Altitude['Longitude'].iloc[count], rxData_Altitude['Latitude'].iloc[count],
                    rxData_Altitude['DN'].iloc[count], Rx_antennaHeight, N, M, exM, kapa
                )
                altitudeGridMatrix[:,count] = gpsGrid
                rxData_Altitude.at[count, 'FresnelR_H'] = FresnelR_H
                rxData_Altitude.at[count, 'FresnelR_V'] = FresnelR_V
                rxData_Altitude.at[count, 'disBtwTxRx'] = disBtwTxRx
                # Fill the corresponding column with the current distance to match the gpsGrid point count.
                dist_expanded[:, count] = disBtwTxRx
            QGIS_input = pd.DataFrame(
                np.concatenate((np.real(altitudeGridMatrix.reshape(-1,1)), np.imag(altitudeGridMatrix.reshape(-1,1)), dist_expanded.reshape(-1, 1)), axis=1),
                columns=['longitude', 'latitude', 'disBtwTxRx']
            )
            QGIS_input = QGIS_input.reset_index()
            QGIS_input.rename(columns={'index': 'searchIndex'}, inplace=True)
            QGIS_input.to_csv(expDataPath + "/inputQGISforML_" + expName + "_SF" + str(SF) + ".csv", index=False)
            #####
            if 'all_vars' in globals(): del all_vars
            all_vars = {key: value for key, value in globals().items()
                        if not key.startswith('__') and subFun.is_picklable(value)}
            with lzma.open(dataPath, 'wb') as saveFile:
                pickle.dump(all_vars, saveFile)
            #####
            csv_path = expDataPath + "/inputQGISforML_" + expName + "_SF" + str(SF) + ".csv"
            print("\nGenerating meshgrid with the building map.")
            gpkg_path_bd = subFun.get_gpkg_files(map_path, "*_building.gpkg")
            print("\nGenerating meshgrid with the altitude map.")
            gpkg_path_al = subFun.get_gpkg_files(map_path, "*_altitude.tif")
            print("\nGenerating meshgrid with the city-type map.")
            gpkg_path_cityType = subFun.get_gpkg_files(map_path, "*_cityType.gpkg")
            if not gpkg_path_bd:
                print("Building map ignored.")
                subFun.load_area_max_data(csv_path, gpkg_path_al, outputQGISFilesPath, "altitude", M, visualAngle['H'])
            else:
                outputQGISFilesPath_building = expDataPath + "/outputQGISforML_" + expName + "_SF" + str(SF) + "_building.csv"
                subFun.load_area_max_data(csv_path, gpkg_path_bd, outputQGISFilesPath_building, "building", M, visualAngle['H'])
                outputQGISFilesPath_altitude = expDataPath + "/outputQGISforML_" + expName + "_SF" + str(SF) + "_altitude.csv"
                subFun.load_area_max_data(csv_path, gpkg_path_al, outputQGISFilesPath_altitude, "altitude", M, visualAngle['H'])
                subFun.merge_csv_files(outputQGISFilesPath_building, outputQGISFilesPath_altitude, outputQGISFilesPath)
            # Read the city type (land use).
            subFun.load_area_max_data(csv_path, gpkg_path_cityType, cityType_outputQGISFilesPath, "cityType", M, visualAngle['H'])
    # endregion




    # Generate feature vectors.
    # region
    FV, cityType, rotatedXYZMatrix = subFun.genFeatureVector(
        QGIS_output, QGIS_output_cityType, exM, N, rxData_Altitude.shape[0], Tx_longitude, Tx_latitude, Tx_altitude,
        Tx_antennaHeight, rxData_Altitude, Rx_antennaHeight
    )
    TV = subFun.genTargetValue(
        Pt_dBm, frequency_MHz, rxData_Altitude, Tx_longitude, Tx_latitude, Tx_altitude,
        Tx_antennaHeight, Rx_antennaHeight
    )

    print("Saving data...")
    time_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_file_path = os.path.join(expDataPath, f'ML_{expName}_SF{SF}_{time_str}.pkl.xz')
    ######
    to_save = {}
    allowed_prefixes = (
        'FV',
        'TV',
        'rxData_Altitude',
        'cityType',
        'exM',
        'N',
        'M',
        'frequency_MHz',
        'Pt_dBm',
        'SF'
    )
    to_save.update({
        k: v for k, v in locals().items()
        if not k.startswith('__') and
        k.startswith(allowed_prefixes) and  # Accept a match against any prefix in the tuple.
        subFun.is_picklable(v)
    })
    with lzma.open(save_file_path, 'wb') as saveFile:
        pickle.dump(to_save, saveFile)
    del to_save
    import gc
    gc.collect()
    ######
    print("Done.")
    # endregion

    return True


if __name__ == "__main__":
    # Retain command-line invocation support for standalone debugging.
    start_collect_logic(*sys.argv[1:])
