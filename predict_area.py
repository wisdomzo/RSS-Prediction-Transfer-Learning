import sys
import os
import subprocess
import subFun
from subFun import generate_grid_points
import main_collect_data
import shutil

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
    如果 source_path 存在且不为空，则拷贝文件到目标文件夹。
    
    参数:
    source_path (str): 源文件路径（可能是 '' 或 None）
    target_folder (str): 目标文件夹，默认为 'selected_folder_csv'
    """
    
    # 1. 预检查：如果路径为空字符串、None 或者全是空格，直接跳过
    if not source_path or not str(source_path).strip():
        print("源路径为空，跳过拷贝任务。")
        return False

    # 2. 检查物理文件是否存在
    if os.path.exists(source_path) and os.path.isfile(source_path):
        try:
            # 3. 确保目标目录存在
            if not os.path.exists(target_folder):
                os.makedirs(target_folder)
            
            # 4. 执行拷贝（保留元数据）
            file_name = os.path.basename(source_path)
            dest_path = os.path.join(target_folder, file_name)
            
            shutil.copy2(source_path, dest_path)
            print(f"成功拷贝文件: {file_name} -> {target_folder}")
            return True
            
        except Exception as e:
            print(f"拷贝过程中发生错误: {e}")
            return False
    else:
        print(f"文件不存在或路径无效: {source_path}")
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
        # 网格采样逻辑
        if lon_min == lon_max and lat_min == lat_max:
            N, M = 1, 1
        else:
            N, M = int(args_list[7]), int(args_list[8])
        # 生成网格点
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
        print(f"数据采集失败: {e}")
        sys.exit(1)



if __name__ == "__main__":
    run_prediction_process(sys.argv[1:])