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
    #全局变量
    # region
    N = 31#fresi面上的NxN个采样点
    M = 30#TxRx直线上的采样数
    kapa = 0.1#TxRx后面环境的扩展系数
    exM = M + 2 * int(np.floor(kapa * M))
    visualAngle = {
        'H': np.deg2rad(30),#半水平视野XX度
        'V': np.deg2rad(15)#半垂直视野XX度
    }

    expName = "myTempExp"
    dataPath = expDataPath + "/data.pkl.xz"
    altitudeDataPath = expDataPath + "/rxData_" + expName + "_SF" + str(SF) + "_altitude.csv"

    #整合实验数据
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

    #添加海拔数据
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
                # 把building高度算进海拔，看作新的海拔
                csv_path = expDataPath + "/rxData_" + expName + "_SF" + str(SF) + ".csv"
                print("\n使用<building>地图生成TxRx空间距离。")
                gpkg_path_building = subFun.get_gpkg_files(map_path, "*_building.gpkg")
                if not gpkg_path_building:
                    print("忽略building地图！")
                    print("\n使用<海拔>地图生成TxRx空间距离。")
                    gpkg_path_altitude = subFun.get_gpkg_files(map_path, "*_altitude.tif")
                    output_path_altitude = expDataPath + "/rxData_" + expName + "_SF" + str(SF) + "_altitude.csv"
                    subFun.load_map_data(csv_path, gpkg_path_altitude, output_path_altitude, "altitude")
                else:
                    output_path_building = expDataPath + "/rxData_" + expName + "_SF" + str(SF) + "_building.csv"
                    subFun.load_map_data(csv_path, gpkg_path_building, output_path_building, "building")
                    print("\n使用<海拔>地图生成TxRx空间距离。")
                    gpkg_path_altitude = subFun.get_gpkg_files(map_path, "*_altitude.tif")
                    output_path_altitude = expDataPath + "/rxData_" + expName + "_SF" + str(SF) + "_altitude_no_building.csv"
                    subFun.load_map_data(csv_path, gpkg_path_altitude, output_path_altitude, "altitude")
                    subFun.merge_csv_files(output_path_building, output_path_altitude, altitudeDataPath)

    #分析实验数据
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
    #    Tx_altitude = 157 #海拔125米，楼32米
    #    Tx_antennaHeight = 2.09
    #    Rx_antennaHeight = 1.83
    #elif expIndex in (7, 8):
    #    Tx_longitude = 127.7739396
    #    Tx_latitude = 26.2477756
    #    Tx_altitude = 150 #海拔137米，楼13米
    #    Tx_antennaHeight = 0
    #    Rx_antennaHeight = 1.83
    #elif expIndex in (9, 10):
    #    Tx_longitude = 127.984681
    #    Tx_latitude = 26.61895
    #    Tx_altitude = 50 #海拔45米，楼5米
    #    Tx_antennaHeight = 0.58
    #    Rx_antennaHeight = 1.83
    #elif expIndex in [11]:
    #    Tx_longitude = 137.7153306
    #   Tx_latitude = 35.27004166
    #    Tx_altitude = 837 #海拔837米，楼0米
    #    Tx_antennaHeight = 1.2
    #    Rx_antennaHeight = 0.5 #车内助手席上
    #elif expIndex in (12, 13):
    #    Tx_longitude = 133.718148
    #    Tx_latitude = 33.62094
    #    Tx_altitude = 121 #海拔61米，楼60米
    #    Tx_antennaHeight = 0.58
    #    Rx_antennaHeight = 1.5
    #else:
    #    sys.exit()
    # endregion

    #基于地图的机器学习推测
    #读取或生成抽样点数据
    # region
    outputQGISFilesPath = expDataPath + "/outputQGISforML_" + expName + "_SF" + str(SF) + ".csv"
    cityType_outputQGISFilesPath = expDataPath + "/cityType_outputQGISforML_" + expName + "_SF" + str(SF) + ".csv"
    while True:
        if os.path.isfile(outputQGISFilesPath) and os.path.isfile(cityType_outputQGISFilesPath):
            QGIS_output = (pd.read_csv(outputQGISFilesPath).sort_values(by='searchIndex'))
            QGIS_output[['DN']] = QGIS_output[['DN']].ffill()#填充NaN
            QGIS_output_cityType = (pd.read_csv(cityType_outputQGISFilesPath).sort_values(by='searchIndex'))
            QGIS_output_cityType[['Type']] = QGIS_output_cityType[['Type']].fillna(0)  # 填充NaN
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
                # 将当前的距离值填充到对应的列，使其与 gpsGrid 的点数一致
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
            print("\n使用<building>地图生成meshgrid。")
            gpkg_path_bd = subFun.get_gpkg_files(map_path, "*_building.gpkg")
            print("\n使用<标高>地图生成meshgrid。")
            gpkg_path_al = subFun.get_gpkg_files(map_path, "*_altitude.tif")
            print("\n使用<城市类型>地图生成meshgrid。")
            gpkg_path_cityType = subFun.get_gpkg_files(map_path, "*_cityType.gpkg")
            if not gpkg_path_bd:
                print("忽略building地图！")
                subFun.load_area_max_data(csv_path, gpkg_path_al, outputQGISFilesPath, "altitude", M, visualAngle['H'])
            else:
                outputQGISFilesPath_building = expDataPath + "/outputQGISforML_" + expName + "_SF" + str(SF) + "_building.csv"
                subFun.load_area_max_data(csv_path, gpkg_path_bd, outputQGISFilesPath_building, "building", M, visualAngle['H'])
                outputQGISFilesPath_altitude = expDataPath + "/outputQGISforML_" + expName + "_SF" + str(SF) + "_altitude.csv"
                subFun.load_area_max_data(csv_path, gpkg_path_al, outputQGISFilesPath_altitude, "altitude", M, visualAngle['H'])
                subFun.merge_csv_files(outputQGISFilesPath_building, outputQGISFilesPath_altitude, outputQGISFilesPath)
            # 读取城市类型（landuse）
            subFun.load_area_max_data(csv_path, gpkg_path_cityType, cityType_outputQGISFilesPath, "cityType", M, visualAngle['H'])
    # endregion




    #生成特征向量
    # region
    FV, cityType, rotatedXYZMatrix = subFun.genFeatureVector(
        QGIS_output, QGIS_output_cityType, exM, N, rxData_Altitude.shape[0], Tx_longitude, Tx_latitude, Tx_altitude,
        Tx_antennaHeight, rxData_Altitude, Rx_antennaHeight
    )
    TV = subFun.genTargetValue(
        Pt_dBm, frequency_MHz, rxData_Altitude, Tx_longitude, Tx_latitude, Tx_altitude,
        Tx_antennaHeight, Rx_antennaHeight
    )

    print("正在保存数据...")
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
        k.startswith(allowed_prefixes) and  # 只要匹配元组中任意一个即可
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
    # 保留命令行调用能力，方便你单独调试这个脚本
    start_collect_logic(*sys.argv[1:])