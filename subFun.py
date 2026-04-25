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


def integrateExpData(exp_data_path):
    csv_files = sorted(glob(os.path.join(exp_data_path, '*.csv')))
    fin_data = pd.DataFrame()

    for file_name in csv_files:
        try:
            # 1. 探测列名
            full_df = pd.read_csv(file_name, nrows=0) # nrows=0 比 nrows=1 更快，只读表头
            columns_lower = [col.lower() for col in full_df.columns]
            
            # 2. 检查列是否存在
            if not all(k in columns_lower for k in ['latitude', 'longitude', 'rssi']):
                print(f"文件 {file_name} 缺少必要的列，已跳过")
                continue

            # 3. 获取原始列名映射
            # 这样可以确保无论 CSV 里这三列在什么位置，都能准确提取
            name_map = {
                full_df.columns[columns_lower.index('latitude')]: 'Latitude',
                full_df.columns[columns_lower.index('longitude')]: 'Longitude',
                full_df.columns[columns_lower.index('rssi')]: 'RSSI'
            }

            # 4. 只读取需要的列
            temp_df = pd.read_csv(
                file_name,
                usecols=list(name_map.keys()),
                dtype='float64'
            ).dropna(how='any') # 只要经纬度或RSSI有一个为空，这一行就没意义

            # 5. 【关键修复】使用 rename 而不是直接覆盖 columns
            # rename 会根据“键值对”匹配列名，不会受原始顺序影响
            temp_df = temp_df.rename(columns=name_map)

            # 6. 统一列顺序，确保 concat 时不会出错
            temp_df = temp_df[['Latitude', 'Longitude', 'RSSI']]

            # 7. 合并与去重
            if fin_data.empty:
                fin_data = temp_df
            else:
                # 使用 drop_duplicates 可能比 isin 更高效（视数据量而定）
                fin_data = pd.concat([fin_data, temp_df], ignore_index=True)
                fin_data = fin_data.drop_duplicates().reset_index(drop=True)

        except Exception as e:
            print(f"处理文件 {file_name} 时出错: {str(e)}")
            continue

    if not fin_data.empty:
        print(f"成功整合 {len(fin_data)} 条数据")
    return fin_data


def backup_integrateExpData(exp_data_path):
    # 获取指定路径下的所有 CSV 文件
    csv_files = sorted(glob(os.path.join(exp_data_path, '*.csv')))

    fin_data = pd.DataFrame()  # 初始化空的 DataFrame

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
    #N是NxN个方阵，M是TxRx之间连线的抽样数
    numEx = int(np.floor(M * kapa))
    tempMatrix = np.zeros((N, M), dtype=complex)
    exTxRxMatrix_Tx = np.zeros((N, numEx), dtype=complex)
    exTxRxMatrix_Rx = np.zeros((N, numEx), dtype=complex)
    for count1 in range(N):
        #计算主体
        for count2 in range(M):
            x = (2 * count2 - 1) / (2 * M) * D
            y = (1 + 1 / N - (2 * count1) / N) * FresnelR_H
            tempMatrix[count1, count2] = x + 1j * y
        #计算前后背景
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
    #求旋转后坐标
    FresnelR_H, FresnelR_V, disBtwTxRx = calMaxFresnelZoneRadius(
        frequency_MHz, visualAngle, Tx_longitude, Tx_latitude, Tx_altitude, Tx_antennaHeight,
        Rx_longitude, Rx_latitude, Rx_altitude, Rx_antennaHeight
    )
    position = oneGrid(disBtwTxRx, FresnelR_H, N, M, exM, kapa)
    px, py, pz = position['x'], position['y'], position['z']
    rotatedXYZ = np.concatenate((px.reshape(1,-1), py.reshape(1,-1), pz.reshape(1,-1)), axis=0)

    #求反向旋转矩阵invH
    H = calRotateH(Tx_longitude, Tx_latitude, Tx_altitude, Tx_antennaHeight, Rx_longitude, Rx_latitude, Rx_altitude, Rx_antennaHeight)
    invH = np.linalg.pinv(H)

    #求旋转前坐标
    XYZ = invH @ rotatedXYZ

    #转换为地球坐标系
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
    except (pickle.PicklingError, TypeError):
        return False

def genFeatureVector(QGIS_output, QGIS_output_cityType, M, N, numRxData, Tx_longitude, Tx_latitude, Tx_altitude, Tx_antennaHeight, rxData_Altitude, Rx_antennaHeight):
    #海拔
    lon = np.reshape(QGIS_output['longitude'].values, (M * N, numRxData))
    lat = np.reshape(QGIS_output['latitude'].values, (M * N, numRxData))
    alt = np.reshape(QGIS_output['DN'].values, (M * N, numRxData))

    FV = np.zeros((M * N, numRxData))
    rotatedXYZMatrix = np.zeros((3, M * N, numRxData))
    for indSample in range(numRxData):
        lonLatAlt = np.array([lon[:, indSample], lat[:, indSample], alt[:, indSample]])
        #转换米坐标
        XYZ = lonLatAlt * 0
        for count in range(M * N):
            x, y = ll_to_meter(lonLatAlt[0, count].item(), lonLatAlt[1, count].item(), Tx_longitude, Tx_latitude)
            z = lonLatAlt[2, count].item() - (Tx_altitude + Tx_antennaHeight)
            XYZ[:, count] = [x, y, z]
        #求变换矩阵
        H = calRotateH(
            Tx_longitude, Tx_latitude, Tx_altitude, Tx_antennaHeight, rxData_Altitude['Longitude'].iloc[indSample],
            rxData_Altitude['Latitude'].iloc[indSample], rxData_Altitude['DN'].iloc[indSample], Rx_antennaHeight
        )
        #矩阵变换
        rotatedXYZ = H @ XYZ
        rotatedXYZMatrix[:,:, indSample] = rotatedXYZ
        #绝对高度矩阵
        FV[:, indSample] = rotatedXYZ[2,:]

    #城市类型
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
    """ 列出当前目录下所有以'ML_'开头的文件 """
    ml_files = [f for f in os.listdir('.') if f.startswith('ML_')]
    return ml_files

def list_history_files():
    """ 列出当前目录下所有以'history_'开头的文件 """
    history_files = [f for f in os.listdir('.') if f.startswith('history_model_from_')]
    return history_files

def list_history_TL_files():
    """ 列出当前目录下所有以'history_'和'TL_'开头的文件 """
    history_TL_files = [
        f for f in os.listdir('.')
        if f.startswith('history_model_from_') or f.startswith('TL_model_')
    ]
    return history_TL_files

def list_history_TL_Predict_files():
    """ 列出当前目录下所有以'history_'和'TL_'开头的文件 """
    history_TL_files = [
        f for f in os.listdir('.')
        if f.startswith('history_model_from_') or f.startswith('TL_model_') or f.startswith('Predict_model_')
    ]
    return history_TL_files


def list_TL_files():
    """ 列出当前目录下所有以'TL_' """
    TL_files = [f for f in os.listdir('.') if f.startswith('TL_')]
    return TL_files

def list_Predict_files():
    """ 列出当前目录下所有以'Predict_' """
    Predict_files = [f for f in os.listdir('.') if f.startswith('Predict_')]
    return Predict_files

def get_user_selection(ml_files):
    """ 让用户选择多个编号 """
    for idx, file in enumerate(ml_files, 1):
        print(f"{idx}: {file}")

    user_input = input("请选择一个或多个文件编号进行操作（用逗号分隔）：")
    selections = list(map(int, user_input.split(',')))
    # 验证用户选择的有效性
    for selection in selections:
        if selection < 1 or selection > len(ml_files):
            print(f"无效的选择: {selection}")
            return None
    return selections

def get_folder_path():
    while True:
        folder_csv_path = input("请输入csv文件夹路径: ").strip()
        folder_map_path = input("请输入database文件夹路径: ").strip()
        folder_fun_path = input("请输入functions文件夹路径: ").strip()

        # 检查路径是否存在
        if not os.path.exists(folder_csv_path):
            print(f"错误: 路径 '{folder_csv_path}' 不存在，请重新输入。")
            continue
        if not os.path.exists(folder_map_path):
            print(f"错误: 路径 '{folder_map_path}' 不存在，请重新输入。")
            continue
        if not os.path.exists(folder_fun_path):
            print(f"错误: 路径 '{folder_fun_path}' 不存在，请重新输入。")
            continue

        # 检查是否是文件夹
        if not os.path.isdir(folder_csv_path):
            print(f"错误: '{folder_csv_path}' 不是文件夹，请重新输入。")
            continue
        if not os.path.isdir(folder_map_path):
            print(f"错误: '{folder_map_path}' 不是文件夹，请重新输入。")
            continue
        if not os.path.isdir(folder_fun_path):
            print(f"错误: '{folder_fun_path}' 不是文件夹，请重新输入。")
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
    # 检查文件夹是否存在
    if not os.path.isdir(folder_path):
        print(f"错误: 文件夹 '{folder_path}' 不存在！")
        return None

    # 查找所有 .gpkg 文件
    gpkg_files = list(Path(folder_path).glob("*.gpkg"))
    if not gpkg_files:
        print(f"在 '{folder_path}' 中未找到 .gpkg 文件！")
        return None

    # 显示可选项
    print("\n找到以下 .gpkg 文件:")
    for i, file in enumerate(gpkg_files, 1):
        print(f"{i}. {file.name}")

    # 让用户选择
    while True:
        try:
            choice = input("\n请选择文件编号 (输入 q 退出，输入 i 忽略): ").strip()
            if choice.lower() == 'q':
                return None
            if choice.lower() == 'i':
                return set()

            choice_idx = int(choice) - 1
            if 0 <= choice_idx < len(gpkg_files):
                return str(gpkg_files[choice_idx])
            else:
                print(f"错误: 请输入 1-{len(gpkg_files)} 之间的数字！")
        except ValueError:
            print("错误: 请输入有效的数字！")

def generate_grid_points(lon_min, lon_max, lat_min, lat_max, N, M, output_file):
    """
    生成经纬度网格点并保存到CSV文件

    参数:
        lon_min: 经度最小值
        lon_max: 经度最大值
        lat_min: 纬度最小值
        lat_max: 纬度最大值
        N: 经度方向采样点数
        M: 纬度方向采样点数
        output_file: 输出CSV文件名
    """

    # 如果output_path是目录，自动生成文件名
    if os.path.isdir(output_file):
        output_file = os.path.join(output_file, "grid_points.csv")
    else:
        output_file = output_file

    # 计算经度和纬度的步长
    lon_step = (lon_max - lon_min) / (N - 1) if N > 1 else 0
    lat_step = (lat_max - lat_min) / (M - 1) if M > 1 else 0

    # 生成网格点
    points = []
    point_id = 0
    for i in range(M):
        lat = lat_min + i * lat_step
        for j in range(N):
            lon = lon_min + j * lon_step
            point = [
                0,  # id (默认0)
                0,  # NodeID (默认0)
                0,  # RouteInfo (默认0)
                0,  # DestID (默认0)
                0,  # SendTime (默认0)
                0,  # SeqID (默认0)
                0,  # RecvTime (默认0)
                lat,  # Latitude
                lon,  # Longitude
                0,  # EncData (默认0)
                -999  # RSSI (默认-999)
            ]
            points.append(point)
            point_id += 1

    # 确保输出目录存在
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    # 写入CSV文件
    with open(output_file, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        # 写入表头
        writer.writerow([
            'id', 'NodeID', 'RouteInfo', 'DestID', 'SendTime',
            'SeqID', 'RecvTime', 'Latitude', 'Longitude',
            'EncData', 'RSSI'
        ])
        # 写入数据
        writer.writerows(points)

    print(f"成功生成 {len(points)} 个点并保存到 {output_file}")
    return

def cal_Pr_free(Pt, lambda_value, d, eta):
    Pr_free = 10 * np.log10(   (Pt * lambda_value ** 2) / ( (4*np.pi)**2 * d ** eta)    )
    return Pr_free

def cal_Pr_free_show(Pt, fre, d, eta):
    lambda_value = 3e8/(fre*10**6)
    Pr_free = 10 * np.log10(   (Pt * lambda_value ** 2) / ( (4*np.pi)**2 * d ** eta)    )
    return Pr_free


def merge_csv_files(file_a, file_b, output_file):
    # 1. 读取 CSV 文件 A 和 B
    df_a = pd.read_csv(file_a)
    df_b = pd.read_csv(file_b)

    # 2. 将 A 文件的 measuredHeight 列中的 null 替换为 0
    df_a["measuredHeight"] = df_a["measuredHeight"].fillna(0)
    # 将 B 文件的 DN 列中的 null 替换为相邻非空值的平均值（线性插值）
    df_b["DN"] = df_b["DN"].interpolate(method='linear')  # 线性插值

    # 3. 检查两文件行数是否一致（确保可以逐行相加）
    if len(df_a) != len(df_b):
        print("警告：两个 CSV 文件的行数不一致，可能导致计算错误！")
    else:
        # 4. 将 A 的 measuredHeight 与 B 的 DN 相加，并覆盖 B 的 DN 列
        df_b["DN"] = df_b["DN"] + df_a["measuredHeight"]

        # 5. 保存修改后的 B 文件（覆盖原文件或另存为新文件）
        #df_b.to_csv(file_b, index=False)  # 覆盖原文件
        df_b.to_csv(output_file, index=False)  # 或另存为新文件

        try:
            os.remove(file_a)
            os.remove(file_b)
            #print(f"已删除原文件：{file_a} 和 {file_b}")
        except FileNotFoundError:
            print("文件不存在，无法删除！")
        except PermissionError:
            print("权限不足，无法删除文件！")

    return


def input_with_default(prompt, default):
    user_input = input(f"{prompt}（直接回车使用默认值 {default}）: ").strip()
    return default if not user_input else type(default)(user_input)  # 自动转换类型



def get_gpkg_files(folder_path, pattern):
    # 检查文件夹是否存在
    if not os.path.isdir(folder_path):
        print(f"错误: 文件夹 '{folder_path}' 不存在！")
        return []

    # 查找所有 .gpkg 文件
    # 使用 glob 搜索包含 "_building.gpkg" 的文件
    # rglob 会搜索子目录，glob 只搜索当前层级
    gpkg_files = list(Path(folder_path).glob(pattern))
    # 将结果赋值给 gpkg_path_building
    # 如果没有找到，glob 会返回空列表 []
    gpkg_path = [str(p) for p in gpkg_files]

    return gpkg_path[0] if gpkg_path else None  # 返回找到的文件路径，如果没有找到则返回 None

def get_ML_files(folder_path, pattern):
    # 检查文件夹是否存在
    if not os.path.isdir(folder_path):
        print(f"错误: 文件夹 '{folder_path}' 不存在！")
        return []

    # 查找所有 .gpkg 文件
    # 使用 glob 搜索包含 "_building.gpkg" 的文件
    # rglob 会搜索子目录，glob 只搜索当前层级
    gpkg_files = list(Path(folder_path).glob(pattern))
    # 将结果赋值给 gpkg_path_building
    # 如果没有找到，glob 会返回空列表 []
    gpkg_path = [str(p) for p in gpkg_files]

    return gpkg_path if gpkg_path else None  # 返回找到的文件路径，如果没有找到则返回 None


class GeoQueryEngine:
    def __init__(self):
        self.raster_data = None

    def load_raster(self, path):
        self.raster_data = rasterio.open(path)

    def sample_raster_fast(self, gdf, lon_name, lat_name):
        """
        极速栅格采样：一次性提取所有点的高程值
        """
        # 生成坐标对列表 [(lon1, lat1), (lon2, lat2), ...]
        coords = zip(gdf[lon_name], gdf[lat_name])
        # 使用 sample 批量采样，它直接返回一个生成器，速度极快
        return [float(val[0]) for val in self.raster_data.sample(coords)]

def load_map_data(csv_path, map_path, output_path, pattern):
    # 1. 读取 CSV 数据
    df = pd.read_csv(csv_path)
    
    # --- 自动识别列名 ---
    col_map = {c.lower(): c for c in df.columns}
    lon_keywords = ['longitude', 'Longitude', 'lon', 'lng', 'x']
    lat_keywords = ['latitude', 'Latitude', 'lat', 'y']
    lon_name = next((col_map[k] for k in lon_keywords if k in col_map), None)
    lat_name = next((col_map[k] for k in lat_keywords if k in col_map), None)

    if not lon_name or not lat_name:
        raise KeyError("无法识别 CSV 中的经纬度列。")

    # --- 转换为 GeoDataFrame ---
    gdf_points = gpd.GeoDataFrame(
        df, 
        geometry=gpd.points_from_xy(df[lon_name], df[lat_name]),
        crs="EPSG:6668" 
    )

    pattern_lower = pattern.lower()

    # 2. 核心逻辑
    if "building" in pattern_lower or "citytype" in pattern_lower:
        is_building = "building" in pattern_lower
        layer = "building" if is_building else "cityType"
        target_field = "measuredHeight" if is_building else "Type"
        # 为 cityType 设定默认值 20，为建筑高度设定 0.0
        default_val = 0.0 if is_building else 20

        import os
        use_default = False
        if not map_path or not os.path.exists(map_path):
            print(f"警告：地图路径无效或不存在 ({map_path})，将使用默认值 {default_val}")
            use_default = True

        if not use_default:
            # 正常加载矢量地图逻辑
            try:
                map_gdf = gpd.read_file(map_path, layer=layer)
                if map_gdf.crs != "EPSG:6668":
                    map_gdf = map_gdf.to_crs("EPSG:6668")

                # 新逻辑
                # 1. 执行空间连接
                # sjoin 会保持 gdf_points 的原始索引
                result_gdf = gpd.sjoin(gdf_points, map_gdf[[target_field, 'geometry']], how="left", predicate="within")

                # 2. 【核心修改】按原始索引去重，而不是按经纬度去重
                # 这样：
                # - 原始数据中 23 个相同经纬度的点（因为索引不同）会全部保留
                # - 如果其中某一个点匹配到了 2 个多边形，则只保留第一个匹配结果，确保 1 对 1
                result_gdf = result_gdf[~result_gdf.index.duplicated(keep='first')]

                # 3. 如果需要解决 measuredHeight 只有第一行有值的问题，增加补全逻辑
                # 这一步会根据经纬度分组，把 20.7 广播给同组所有行
                if 'measuredHeight' in result_gdf.columns:
                    result_gdf['measuredHeight'] = result_gdf.groupby([lat_name, lon_name])['measuredHeight'].transform('max')

                # 4. 填充连接失败的缺失值
                result_gdf[target_field] = result_gdf[target_field].fillna(default_val)

                # 5. 转换为普通 DataFrame 并清理
                df = pd.DataFrame(result_gdf.drop(columns=['geometry', 'index_right'], errors='ignore'))
                # 新逻辑结束
            except Exception as e:
                print(f"读取地图出错: {e}，切换至默认值模式")
                use_default = True

        if use_default:
            # 直接给原始 df 分配默认值列
            df[target_field] = default_val
            # 这里的 df 已经是普通的 pandas DataFrame，不需要 drop geometry

        # --- 统一后期处理 ---
        if not is_building:
            df[target_field] = df[target_field].astype(int)
            # 如果列名不是 "Type"，重命名它
            if target_field != "Type":
                df = df.rename(columns={target_field: "Type"})

    elif "altitude" in pattern_lower or "dem" in pattern_lower:
        print(f"模式：{pattern} | 极速高程采样...")
        engine = GeoQueryEngine()
        engine.load_raster(map_path)
        sampled_data = engine.sample_raster_fast(df, lon_name, lat_name)
        df["DN"] = sampled_data

        # --- 补救逻辑：使用区域平均海拔 ---
        # 首先，将常见的栅格无效值（NoData）转换为 NaN，方便统一处理
        # 常见的无效值包括 -9999, -32767, -32768 等
        invalid_values = [-9999, -32767, -32768]
        df["DN"] = df["DN"].replace(invalid_values, np.nan)

        # 检查是否有读取失败的点 (NaN)
        nan_count = df["DN"].isna().sum()
        if nan_count > 0:
            # 计算当前 CSV 中所有有效采样点的平均海拔
            area_avg_alt = df["DN"].mean()
            
            # 如果整个区域都采样失败（均值为 NaN），则保底填充 0
            if pd.isna(area_avg_alt):
                area_avg_alt = 0.0
                print(f"警告：该区域无有效海拔数据，已全量填充 0.0")
            else:
                print(f"检测到 {nan_count} 个采样失败点，已使用区域均值 {area_avg_alt:.2f}m 自动填充")
            
            # 执行填充
            df["DN"] = df["DN"].fillna(area_avg_alt)

    # 保存
    df.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"任务完成！保存至: {output_path}")
    return df


def load_area_max_data(csv_path, map_path, output_path, pattern, M, visualAngle):
    # 1. 读取 CSV 数据
    df = pd.read_csv(csv_path)
    
    col_map = {c.lower(): c for c in df.columns}
    lon_name = next((col_map[k] for k in ['longitude', 'lon', 'x'] if k in col_map), None)
    lat_name = next((col_map[k] for k in ['latitude', 'lat', 'y'] if k in col_map), None)
    dist_name = next((col_map[k] for k in ['disbtwtxrx', 'distance'] if k in col_map), "disBtwTxRx")

    if not lon_name or not lat_name:
        raise KeyError("无法识别 CSV 中的经纬度列。")

    # --- 2. 几何生成 (利用 Shapely 2.x 矢量化加速) ---
    points = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df[lon_name], df[lat_name]), crs="EPSG:6668")
    points_m = points.to_crs(epsg=3857)
    coords = points_m.geometry.get_coordinates()
    
    L = df[dist_name].values / (M - 1)
    # 确保 visualAngle 是弧度，如果是角度请用 np.deg2rad
    D = L * np.tan(visualAngle)
    
    x, y = coords['x'].values, coords['y'].values
    # 矢量化创建矩形
    rects = shapely.box(x - L/2, y - D/2, x + L/2, y + D/2)
    gdf_area = gpd.GeoDataFrame(df, geometry=rects, crs="EPSG:3857").to_crs(epsg=6668)

    pattern_lower = pattern.lower()
    
    # --- 3. 矢量地图优化 (仅保留 Building 的 sjoin) ---
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



    # --- 4. 栅格逻辑优化 (CityType 和 Altitude 共用) ---
    elif any(k in pattern_lower for k in ["citytype", "altitude", "dem"]):
        is_citytype = "citytype" in pattern_lower
        target_col = "Type" if is_citytype else "DN"
        if map_path is None or not os.path.exists(map_path):
            # 如果是 CityType 填充 20，如果是海拔通常填充 0 或 10
            default_fill = 20 if is_citytype else 0 
            df[target_col] = default_fill
            if is_citytype: 
                df[target_col] = df[target_col].astype(int)
            # 直接跳过后面的 rasterio 处理块
        else:
            with rasterio.Env(): # 确保环境清洁
                if is_citytype:
                    print("正在将 CityType 矢量地图转换为临时栅格以加速提取...")
                    # 读取矢量图层
                    map_gdf = gpd.read_file(map_path, layer="cityType")
                    if map_gdf.crs != "EPSG:6668":
                        map_gdf = map_gdf.to_crs("EPSG:6668")
                    
                    # 定义栅格化分辨率（例如 0.0001度 约10米，可根据地图精度调整）
                    res_deg = 0.0001 
                    b = map_gdf.total_bounds
                    # 计算输出形状和变换矩阵
                    out_shape = (int((b[3]-b[1])/res_deg) + 1, int((b[2]-b[0])/res_deg) + 1)
                    full_transform = rasterio.transform.from_bounds(*b, out_shape[1], out_shape[0])
                    
                    # 核心加速：将矢量转为内存数组
                    full_data = features.rasterize(
                        [(shape, val) for shape, val in zip(map_gdf.geometry, map_gdf['Type'])],
                        out_shape=out_shape, transform=full_transform, fill=20 # 默认填充20
                    )
                    nodata = -9999
                    gdf_raster_crs = gdf_area # 已经在 6668
                else:
                    # 海拔/DEM 处理逻辑保持不变
                    print("正在处理海拔栅格...")
                    src = rasterio.open(map_path)
                    nodata = src.nodata if src.nodata is not None else -9999
                    gdf_raster_crs = gdf_area.to_crs(src.crs)
                    total_bounds = gdf_raster_crs.total_bounds
                    full_window = src.window(*total_bounds).round()
                    full_data = src.read(1, window=full_window)
                    full_transform = src.window_transform(full_window)
                    src.close()

                # --- 统一的切片提取逻辑 (极致加速版) ---
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
                                # 提取众数 (出现次数最多的 Type)
                                counts = np.bincount(valid.astype(int))
                                results.append(np.argmax(counts))
                            else:
                                # 提取最大值 (Altitude)
                                results.append(valid.max())
                        else: results.append(np.nan)
                    else: results.append(np.nan)
                
                df[target_col] = results
                # 填充缺失值并格式化
                fill_val = 20 if is_citytype else df[target_col].mean()
                df[target_col] = df[target_col].fillna(fill_val)
                if is_citytype: df[target_col] = df[target_col].astype(int)

    # 5. 保存
    df.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"处理完成！")
    return df


def clean_folder_except(folder_path, prefix_to_keep):
    """
    删除指定文件夹下所有文件，但保留以指定前缀开头的文件。
    
    参数:
    folder_path (str or Path): 目标文件夹的路径
    prefix_to_keep (str): 需要保留的文件名前缀
    """
    # 1. 将输入转换为 Path 对象
    folder = Path(folder_path)
    
    # 2. 安全检查：确保路径存在且是一个文件夹
    if not folder.exists():
        print(f"跳过清理：路径不存在 -> {folder_path}")
        return
    if not folder.is_dir():
        print(f"跳过清理：指定路径不是文件夹 -> {folder_path}")
        return

    print(f"正在清理文件夹: {folder.absolute()}")
    print(f"保留前缀为 '{prefix_to_keep}' 的文件...")

    count = 0
    # 3. 遍历文件夹
    for file_path in folder.iterdir():
        # 只处理文件，不处理子文件夹
        if file_path.is_file():
            # 判断文件名是否不以指定前缀开头
            if not file_path.name.startswith(prefix_to_keep):
                try:
                    file_path.unlink()  # 执行删除
                    # print(f"  [已删除]: {file_path.name}")
                    count += 1
                except Exception as e:
                    print(f"  [错误] 无法删除 {file_path.name}: {e}")
    
    print(f"清理完成，共删除 {count} 个文件。")



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
            num_test_per = str(0.01), #对于新数据的预测比例，如果是0.01，则表示用1%的数据进行预测，剩余99%用于生成模型
            user_input = 1,
            model_path = modelToBeFineTuned,
            data_index = list(range(1,len(contentReadDataIndex)+1)),
            content_data_index = contentReadDataIndex
        )
        print("微調整完成！")
        clean_folder_except(selected_folder_csv, "TL_model_")
    except Exception as e:
        print(f"微調整失敗: {e}")
        raise e
    
    return True



def genFineTuningCSV(selected_folder_csv, fine_tuning, fine_tuning_lng, fine_tuning_lat):
    """
    生成 fine_tuning_nearfield.csv 文件
    """

    # 构造文件路径
    os.makedirs(selected_folder_csv, exist_ok=True)
    file_path = os.path.join(selected_folder_csv, 'fine_tuning_nearfield.csv')

    # 写入 CSV
    try:
        with open(file_path, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            # 如果需要表头，可以取消下面注释
            writer.writerow(['longitude', 'latitude', 'rssi'])
            
            for rssi in fine_tuning:
                # 这里假设所有点都偏离 1 米（例如向东偏移 1 米）
                # 你也可以根据需要让它们环绕天线分布
                new_lng = fine_tuning_lng
                new_lat = fine_tuning_lat
                
                writer.writerow([new_lng, new_lat, rssi])
                
        print(f"成功生成文件: {file_path}")
    except Exception as e:
        print(f"生成文件失败: {e}")



def augment_centrosymmetric(origFV, origTV, origAlt):
    """
    执行中心对称翻转并处理物理通道一致性
    origFV 形状: (31, 36, 5, 1498)  <- 注意：你提到有5个通道(0-4)
    """
    # 1. 空间维度的翻转 (Axis 0 和 Axis 1)
    # 这步会翻转所有通道的矩阵结构
    flippedFV = np.flip(origFV, axis=(0, 1)).copy()
    
    # 2. 物理意义修正：针对 Channel 1 (梯度通道)
    # 因为中心对称意味着从 Rx 向 Tx 看，原本沿 axis 1 计算的梯度方向相反了
    # 必须取反，否则模型会误以为地形起伏方向没变
    flippedFV[:, :, 1, :] = -flippedFV[:, :, 1, :]
    
    # 3. 拼接特征矩阵 (在样本量维度 axis=-1 拼接)
    augFV = np.concatenate([origFV, flippedFV], axis=-1)
    
    # 4. 拼接标签 (Target Values)
    # 假设翻转后 RSS 预测目标不变（互易性原理）
    augTV = np.concatenate([origTV, origTV], axis=-1)
    
    # 5. DataFrame 对应倍增
    augAlt = pd.concat([origAlt, origAlt], axis=0).reset_index(drop=True)
    
    return augFV, augTV, augAlt