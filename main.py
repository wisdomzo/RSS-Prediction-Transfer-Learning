import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'  # 0为显示所有，1为屏蔽INFO，2为屏蔽INFO和WARNING
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
import predict_area
import training_history_database
import transfer_learning_main
import base64
import io
import json
import multiprocessing
from dask.distributed import Client, get_client, Queue


def connect_to_existing_cluster(coords):
    """
    稳健版 Dask 连接函数：
    1. 校验输入地址
    2. 自动补全 tcp:// 协议
    3. 连接失败或地址为空时安全返回，触发单机模式
    """
    # 1. 获取并清洗地址输入
    raw_addr = coords.get('scheduler', "").strip()
    
    # 如果用户没填，直接返回 None，下游 get_client() 报错会触发单机逻辑
    if not raw_addr:
        print(">>> 未指定 Scheduler 地址，将使用单机模式运行。")
        return None

    # 自动处理协议头：防止用户填了 "192.168.1.1" 或重复填了 "tcp://192.168.1.1"
    if "://" in raw_addr:
        scheduler_addr = raw_addr
    else:
        scheduler_addr = f"tcp://{raw_addr}"

    try:
        # 尝试获取已存在的客户端 (防止在一个 Session 里重复初始化)
        from dask.distributed import Client, get_client
        try:
            client = get_client()
            # 检查当前连接的地址是否和用户输入的一致，如果不一致则关闭旧的开新的
            if client.scheduler.address == scheduler_addr:
                print(f">>> 已连接到目标集群: {scheduler_addr}")
                return client
            else:
                client.close()
        except:
            pass

        # 2. 准备代码提取路径 (BRIDGE_PATH)
        important_files = [
            'subFun_TL.py', 'subFun.py', 'main_collect_data.py', 'main_multiple_processes.py',
            'predict_area.py', 'training_history_database.py', 'transfer_learning_main.py',
            'main.py', 'my_plot_figure.py', 'paper_functions.py', 'qgis_functions.py'
        ]

        RAW_ROOT = get_app_root_directory()
        # 兼容 macOS 打包后的路径
        if "Contents/Frameworks" in RAW_ROOT:
            APP_ROOT = RAW_ROOT.replace("Contents/Frameworks", "Contents/Resources")
            BRIDGE_PATH = os.path.join(os.path.expanduser("~"), "Library", "Application Support", "RSS_PredictApp", "tempPythonBridge")
            if not os.path.exists(BRIDGE_PATH): os.makedirs(BRIDGE_PATH)
            # 物理拷贝文件到桥接路径
            for f in important_files:
                src_f = os.path.join(APP_ROOT, f)
                if os.path.exists(src_f): shutil.copy2(src_f, BRIDGE_PATH)
        else:
            BRIDGE_PATH = RAW_ROOT 

        # 3. 建立连接 (设置 5 秒超时，地址填错时能迅速返回)
        print(f">>> 正在尝试连接集群: {scheduler_addr} ...")
        client = Client(scheduler_addr, timeout="5s")
        
        # 4. 同步代码至远程节点
        for f in important_files:
            target_f = os.path.join(BRIDGE_PATH, f)
            if os.path.exists(target_f):
                try:
                    # upload_file 是分发脚本到远程 Worker 的核心
                    client.upload_file(target_f)
                except Exception:
                    # 本地 Worker 可能会因为文件占用报错，通常可以直接忽略
                    continue
        
        print(f">>> Dask 集群接入成功并已同步代码！")
        return client

    except Exception as e:
        # 无论是因为超时、IP 填错、还是网络不通，都统一拦截并打印
        print(f">>> 无法接入集群 ({scheduler_addr})，错误: {e}")
        print(">>> 降级为单机模式运行。")
        return None
    
class QueueLogger:
    def __init__(self, queue):
        self.queue = queue
    def write(self, message):
        # 只要不是纯空行，就把消息丢进队列
        if message.strip():
            self.queue.put(message)
    def flush(self):
        pass

class Api:
    def __init__(self):
        # 初始时 window 可能还没创建
        pass

    def select_files_native(self, type):
        # 使用最新的常量和兼容的过滤器格式
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
                webview.FileDialog.OPEN, # 使用最新常量
                allow_multiple=multipleFiles, 
                file_types=file_types
            )
            return result
        except Exception as e:
            print(f"Dialog Error: {e}")
            return None
    
    def start_log_proxy(self):
        from dask.distributed import Queue
        # 确保这里的名字和 Worker 那边完全一致
        self.remote_q = Queue("app_terminal_logs") 
        
        def _listen():
            while True:
                try:
                    msg = self.remote_q.get() # 阻塞接收
                    print(msg) # 触发 A 机本地的 WebviewLogger -> 发送到 GUI
                except: break
                
        threading.Thread(target=_listen, daemon=True).start()

    def executeModelGeneration(self, coords):
        # 1. 确保连接到 Dask 集群
        # 这个函数是我们之前改写的，它会返回 client 或 None
        client = connect_to_existing_cluster(coords)  # 确保连接到集群

        if client:
        # 2. 启动日志代理（必须在 client 产生后）
            self.start_log_proxy() 
            print(">>> 远程日志链路已激活...")

        # 2. 启动后台线程执行耗时任务，防止前端 UI 卡死
        # 建议将 client 也传进去，这样 worker 内部就不需要重新查找 client
        threading.Thread(
            target=worker_thread_modelGen, 
            args=(self, coords), 
            daemon=True
            ).start()
        return True


class WebviewLogger:
    def __init__(self, window):
        self.window = window
        self.terminal = sys.stdout

    def write(self, message):
        self.terminal.write(message)
        
        # 1. 过滤掉 Keras 进度条中常见的 \r (回车符)，它会导致字符串异常断开
        msg = message.replace('\r', '').replace('\n', '')
        
        if msg.strip():
            try:
                # 2. 【核心修复】使用 json.dumps 将 Python 字符串安全地转为 JS 字符串
                # 它会自动处理引号、斜杠和特殊不可见字符
                safe_msg_json = json.dumps(msg) 
                
                # 3. 注入 JS。注意这里不需要在 {safe_msg_json} 外面加引号了，因为 dumps 已经带了
                self.window.evaluate_js(f"updateTerminal({safe_msg_json})")
            except Exception as e:
                # 防止由于日志重定向导致的循环报错
                self.terminal.write(f"\nLogger Error: {str(e)}\n")

    def flush(self):
        self.terminal.flush()




if hasattr(sys, '_MEIPASS'):
    # 设置 GDAL 数据路径
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
    """使用 Downloads 避开 macOS 权限封锁"""
    if getattr(sys, 'frozen', False):
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


# 定义供前端调用的Python接口
def worker_thread(coords):
    """在后台线程中运行机器学习任务，防止卡死 UI"""
    try:
        selected_folder_csv = get_writable_temp_path()
        DATABASE_MAP = {
            "DB_matumotoCity": "database/nagano_matumoto_shinndai",
            "DB_kouchi_kamishi": "database/kouchi_kami",
            "DB_kouchi_shimanntoucyou": "database/kouchi_shimanntoucyou",
            "DB_kanagawa_yokosukashi": "database/kanagawa_yokosuka"
        }
        db_key = coords.get('database')
        relative_path = DATABASE_MAP.get(db_key)
        if relative_path:
            selected_folder_map = os.path.join(APP_ROOT, relative_path)
        else:
            print(f"未知数据库: {db_key}")
            return False
        subFun.clean_folder_except(selected_folder_csv, "keep_nothing")  # 清理临时文件夹，保留特定前缀的文件
        
        # 准备参数列表
        if coords['predictDataSelectValue'] == "predictData_file":
            select_prediction_file_path = select_prediction_file(window)
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
            baseModel = select_custom_model_file(window)
        selected_predict_model = baseModel

        window.evaluate_js("updateProgress(30, '予測エリアを生成中...')")
        predict_area.run_prediction_process(args)
        # 获取匹配的文件列表
        contentReadDataIndex = subFun.get_ML_files(selected_folder_csv, "ML_myTempExp_*")
        window.evaluate_js("updateProgress(40, '推測モデルのパラメータを調整している...')")
        try:
            # 直接传入参数，不再需要 python_exe 和命令行字符串化
            transfer_learning_main.run_transfer_learning(
                selected_folder_csv,
                num_test_per = str(1),
                user_input = 1,
                model_path = selected_predict_model,
                data_index = list(range(1,len(contentReadDataIndex)+1)),
                content_data_index = contentReadDataIndex
            )
            print("迁移学习任务已完成")
        except Exception as e:
            print(f"迁移学习执行失败: {e}")
            raise e
        
        selected_name = subFun.get_gpkg_files(selected_folder_csv, "Predict_model_for_*")
        window.evaluate_js("updateProgress(70, '受信電力を推測している...')")
        rxData_Altitude_TL, _, _ = subFun_TL.show_Predict_model(selected_name)
        time_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        rxData_Altitude_TL.to_csv(os.path.join(selected_folder_csv, f'predict_RSS_{time_str}.csv'), index=False)
        print("已生成预测结果。")
        subFun.clean_folder_except(selected_folder_csv, "predict_RSS_")
        #"""
        window.evaluate_js("updateProgress(100, '完了')")
        return True
    except Exception as e:
        print(f"执行失败: {e}")
        window.evaluate_js(f"updateProgress(-1, 'エラー: {str(e)}')")






def worker_thread_modelGen(api_instance, coords):
    selected_folder_csv = get_writable_temp_path()
    copy_selected_files(coords, selected_folder_csv)
    if coords['model'] != "noModel":
        # 转移学习方法
        if coords['model'] == "NICT_latest_model":
            selected_predict_model = subFun.get_gpkg_files(os.path.join(APP_ROOT, "models"), "*NICT*")
        contentReadDataIndex = subFun.get_ML_files(selected_folder_csv, "ML_myTempExp_*")
        window.evaluate_js("updateProgress(10, '時間かかりますが、転移学習によるモデル生成を実行中...')")
        try:
            transfer_learning_main.run_transfer_learning(
                selected_folder_csv,
                num_test_per = str(0.01), #对于新数据的预测比例，如果是0.01，则表示用1%的数据进行预测，剩余99%用于生成模型
                user_input = 1,
                model_path = selected_predict_model,
                data_index = list(range(1,len(contentReadDataIndex)+1)),
                content_data_index = contentReadDataIndex,
                learning_type = coords['learningType'],
                api_instance = api_instance,
                freeze_layer = int(coords['freezeLayer']),
                learning_rate = float(coords['learningRate'])
            )
            print("迁移学习任务已完成")
            subFun.clean_folder_except(selected_folder_csv, "TL_model_")
            window.evaluate_js("updateProgress(100, 'モデル生成が完了しました。')")
            download_model("TL_model_")
        except Exception as e:
            print(f"迁移学习执行失败: {e}")
            raise e
    else:
        # 不使用迁移学习方法，直接生成模型
        contentReadDataIndex = subFun.get_ML_files(selected_folder_csv, "ML_myTempExp_*")
        window.evaluate_js("updateProgress(10, '時間かかりますが、機械学習によるモデル生成を実行中...')")
        try:
            print("\n开始训练历史模型...")
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
            print("機械学習任务已完成")
            subFun.clean_folder_except(selected_folder_csv, "history_model_from_")
            window.evaluate_js("updateProgress(100, 'モデル生成が完了しました。')")
            download_model("history_model_from_")
        except Exception as e:
            print(f"機械学習実行失败: {e}")
            raise e



def copy_selected_files(coords, target_folder='selected_folder_csv'):
    """
    将 coords['selectedPaths'] 中的文件拷贝到指定文件夹下。
    
    参数:
    coords (dict): 包含 'selectedPaths' 键的字典，其值为路径列表。
    target_folder (str): 目标文件夹名称，默认为 'selected_folder_csv'。
    """
    
    # 1. 确保目标文件夹存在，如果不存在则创建
    if not os.path.exists(target_folder):
        os.makedirs(target_folder)
        print(f"创建目标文件夹: {target_folder}")

    # 2. 获取路径列表
    selected_paths = coords.get('selectedPaths', [])
    
    copy_count = 0
    
    # 3. 遍历并拷贝
    for source_path in selected_paths:
        if os.path.exists(source_path):
            # 获取文件名（不带路径部分）
            file_name = os.path.basename(source_path)
            # 拼接目标完整路径
            dest_path = os.path.join(target_folder, file_name)
            
            try:
                # 执行拷贝 (shutil.copy 会保留权限，shutil.copy2 会尽量保留元数据如修改时间)
                shutil.copy2(source_path, dest_path)
                print(f"成功拷贝: {file_name}")
                copy_count += 1
            except Exception as e:
                print(f"拷贝文件 {file_name} 时出错: {e}")
        else:
            print(f"警告: 文件不存在，跳过: {source_path}")

    print(f"\n任务完成！共成功拷贝 {copy_count} 个文件到 {target_folder}。")



def select_custom_model_file(window):
    """
    弹出文件选择对话框，返回用户选择的 .xz 文件路径
    """
    window.evaluate_js("alert('モデルファイルを選択してください (.xz 形式)')")
    file_types = ('Model files (*.xz)', 'All files (*.*)')
    
    # 弹出对话框
    result = window.create_file_dialog(
        webview.FileDialog.OPEN,
        allow_multiple=False, 
        file_types=file_types
    )
    
    # 如果用户点击了取消，result 会是 None
    if result and len(result) > 0:
        return result[0]
    return None


def select_prediction_file(window):
    """
    弹出文件选择对话框，返回用户选择的 .csv 文件路径
    """
    window.evaluate_js("alert('予測CSVファイルを選択してください (.csv 形式)')")
    file_types = ('CSV files (*.csv)', 'All files (*.*)')
    
    # 弹出对话框
    result = window.create_file_dialog(
        webview.FileDialog.OPEN,
        allow_multiple=False, 
        file_types=file_types
    )
    
    # 如果用户点击了取消，result 会是 None
    if result and len(result) > 0:
        return result[0]
    return None




def executeRssPrediction(coords):
    """JS 接口：启动后台线程"""
    threading.Thread(target=worker_thread, args=(coords,), daemon=True).start()
    return True



def executeDataProcessing(coords):
    """
    JS 接口：直接执行逻辑。
    由于 pywebview 调用此函数时已在独立线程中，
    所以这里直接写逻辑，JS 端的 await 就会等待到执行结束。
    """
    try:
        selected_folder_csv = get_writable_temp_path()
        
        # 直接调用逻辑，不使用 threading.Thread
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

        user_confirmed = window.create_confirmation_dialog('提示', '他のデータを処理しますか？\n\nYes: はい\nCancel: キャンセル')
        
        # 返回给 JS 的结果，可以是布尔值或处理后的数据
        return {
            "status": "success", 
            "message": "Processing completed",
            "user_choice": user_confirmed
        }
        
    except Exception as e:
        print(f"执行失败: {e}")
        # 返回错误信息，让 JS 的 try-catch 能捕获到逻辑错误
        return {"status": "error", "message": str(e)}


def get_prediction_data():
    """读取最新的预测结果 CSV 并返回给前端绘图"""
    try:
        folder = get_writable_temp_path()
        # 匹配最新的预测文件
        files = glob.glob(os.path.join(folder, "predict_RSS_*.csv"))
        if not files:
            return None
        
        latest_file = max(files, key=os.path.getctime)
        df = pd.read_csv(latest_file)
        
        # 确保列名与 JS 匹配：lng, lat, Predicted_Value
        return df.to_dict(orient='records')
    except Exception as e:
        print(f"读取数据失败: {e}")
        return None


def download_csv():
    """使用 pywebview 原生对话框保存文件"""
    try:
        folder = get_writable_temp_path()
        files = glob.glob(os.path.join(folder, "predict_RSS_*.csv"))
        if not files:
            return False
            
        latest_file = max(files, key=os.path.getctime)
        
        # 调用 pywebview 的原生保存对话框
        file_path = window.create_file_dialog(
            webview.FileDialog.SAVE, 
            directory=os.path.expanduser("~"), 
            save_filename=os.path.basename(latest_file),
            file_types=('CSV Files (*.csv)', 'All files (*.*)')
        )

        if file_path:
            # 兼容不同操作系统的返回格式
            actual_path = file_path[0] if isinstance(file_path, (list, tuple)) else file_path
            shutil.copy(latest_file, actual_path)
            return True
        return False
    except Exception as e:
        print(f"保存失败: {e}")
        return False
    

def download_model(file_head):
    """
    根据指定的前缀 (file_head) 弹出对话框保存模型文件
    :param file_head: 字符串，如 "TL_model_" 或 "ML_model_"
    """
    try:
        # 1. 定位临时文件夹
        folder = get_writable_temp_path()
        
        # 2. 搜索匹配前缀的文件（匹配所有后缀，如 .gpkg, .pth, .onnx 等）
        search_pattern = os.path.join(folder, f"{file_head}*")
        files = glob.glob(search_pattern)
        
        if not files:
            print(f"未找到前缀为 {file_head} 的模型文件")
            # 可选：通知前端
            window.evaluate_js(f"alert('保存失败：找不到 {file_head} 开头的文件')")
            return False
            
        # 3. 获取该类文件中最新生成的一个
        latest_file = max(files, key=os.path.getctime)
        original_filename = os.path.basename(latest_file)
        
        # 4. 调用 pywebview 原生保存对话框
        # 注意：部分版本使用 webview.SAVE_DIALOG，部分使用 webview.FileDialog.SAVE
        file_path = window.create_file_dialog(
            webview.FileDialog.SAVE, 
            directory=os.path.expanduser("~"), 
            save_filename=original_filename,
            file_types=('Model Files (*.pkl.xz)', 'All files (*.*)')
        )

        # 5. 用户确认保存路径后执行拷贝
        if file_path:
            # 兼容不同系统的返回格式（str 或 list）
            actual_destination = file_path[0] if isinstance(file_path, (list, tuple)) else file_path
            
            shutil.copy(latest_file, actual_destination)
            print(f"成功将 {original_filename} 保存至: {actual_destination}")
            return True
            
        return False
        
    except Exception as e:
        print(f"保存过程出错: {e}")
        return False


def upload_csv_files(file_data_list, altitude_file_data_list, building_file_data_list, landuse_file_data_list):
    """
    现在接收的是文件路径列表 (List of strings)。
    1. 将 Altitude 路径指向的文件复制并重命名为 fine_tuning_database_altitude.tif
    2. 处理各路 GPKG 文件
    3. 读取 CSV 路径并合并
    """
    try:
        # 获取保存路径（临时文件夹）
        selected_folder_csv = get_writable_temp_path() 
        if not os.path.exists(selected_folder_csv):
            os.makedirs(selected_folder_csv)

        # --- 1. 处理 Altitude TIF 文件 (此时 altitude_file_data_list 是路径列表) ---
        if altitude_file_data_list and len(altitude_file_data_list) > 0:
            src_path = altitude_file_data_list[0] # 取第一个文件的路径字符串
            try:
                save_path_altitude = os.path.join(selected_folder_csv, "fine_tuning_database_altitude.tif")
                # 【核心修改】：直接从原始路径复制文件，不再需要 Base64 解码
                shutil.copy(src_path, save_path_altitude)
                print(f"Altitude file copied to: fine_tuning_database_altitude.tif")
            except Exception as e:
                print(f"Altitude saving error: {e}")
        
        # --- 2. 处理 building gpkg 文件 ---
        if building_file_data_list and len(building_file_data_list) > 0:
            src_path = building_file_data_list[0]
            try:
                save_path_building = os.path.join(selected_folder_csv, "fine_tuning_database_building.gpkg")
                shutil.copy(src_path, save_path_building)
                print(f"Building file copied to: fine_tuning_database_building.gpkg")
            except Exception as e:
                print(f"Building saving error: {e}")

        # --- 3. 处理 landuse gpkg 文件 ---
        if landuse_file_data_list and len(landuse_file_data_list) > 0:
            src_path = landuse_file_data_list[0]
            try:
                save_path_landuse = os.path.join(selected_folder_csv, "fine_tuning_database_cityType.gpkg")
                shutil.copy(src_path, save_path_landuse)
                print(f"Landuse file copied to: fine_tuning_database_cityType.gpkg")
            except Exception as e:
                print(f"Landuse saving error: {e}")

        # --- 4. 处理 CSV 文件列表 ---
        all_dataframes = [] 
        skipped_files = [] 
        total_dropped_rows = 0
        
        # 关键词定义（识别用户上传的不同列名）
        lon_k = ['longitude', 'lon', 'lng', 'x']
        lat_k = ['latitude', 'lat', 'y']
        rssi_k = ['rssi', 'dn', 'predicted_value'] 

        for csv_path in file_data_list:
            # csv_path 现在是字符串路径
            file_name = os.path.basename(csv_path)
            if not file_name.lower().endswith('.csv'):
                continue
            
            try:
                # 【核心修改】：直接使用 pandas 读取本地路径
                df = pd.read_csv(csv_path)
                
                cols = df.columns.tolist()
                cols_lower = [c.lower() for c in cols]
                
                # 寻找匹配的列
                target_lon = next((cols[i] for i, c in enumerate(cols_lower) if c in lon_k), None)
                target_lat = next((cols[i] for i, c in enumerate(cols_lower) if c in lat_k), None)
                target_rssi = next((cols[i] for i, c in enumerate(cols_lower) if c in rssi_k), None)
                
                if not (target_lon and target_lat and target_rssi):
                    skipped_files.append(f"{file_name} (列名不匹配)")
                    continue

                # 提取并清洗
                df_filtered = df[[target_lon, target_lat, target_rssi]].copy()
                df_filtered.columns = ['Longitude', 'Latitude', 'RSSI']
                
                initial_len = len(df_filtered)
                df_filtered = df_filtered.dropna(subset=['Longitude', 'Latitude', 'RSSI'])
                total_dropped_rows += (initial_len - len(df_filtered))

                if not df_filtered.empty:
                    all_dataframes.append(df_filtered)
                else:
                    skipped_files.append(f"{file_name} (清洗后无有效数据)")

            except Exception as e:
                skipped_files.append(f"{file_name} (读取错误: {str(e)})")

        # --- 5. 合并并保存总 CSV ---
        if all_dataframes:
            combined_df = pd.concat(all_dataframes, ignore_index=True)
            save_path_total = os.path.join(selected_folder_csv, "fine_tuning_total.csv")
            combined_df.to_csv(save_path_total, index=False, encoding='utf-8')
            
            msg = f"已将 {len(all_dataframes)} 个文件整合为 'fine_tuning_total.csv'。"
            if total_dropped_rows > 0:
                msg += f"\n(剔除了 {total_dropped_rows} 条含空值的记录)"
            if skipped_files:
                msg += "\n跳过文件: " + ", ".join(skipped_files)
                
            return {"status": "success", "message": msg}
        else:
            return {"status": "error", "message": "未发现有效的 CSV 数据。"}

    except Exception as e:
        print(f"Fatal Upload Error: {e}")
        return {"status": "error", "message": str(e)}
    

def reset_temp_data(prefix_to_keep=None):
    """
    重置时清理临时文件夹
    :param prefix_to_keep: 需要保留的文件前缀。如果不传，默认清理所有。
    """
    try:
        # 如果 JS 调用时没传参数，prefix_to_keep 会是 None
        target_prefix = prefix_to_keep if prefix_to_keep is not None else "KEEP_NOTHING"
        
        selected_folder_csv = get_writable_temp_path()
        
        # 调用 subFun 执行逻辑
        subFun.clean_folder_except(selected_folder_csv, target_prefix) 
        
        print(f"清理完成。保留前缀: {target_prefix}, 路径: {selected_folder_csv}")
        return True
    except Exception as e:
        print(f"清理临时文件夹失败: {e}")
        return False


def get_help_pdf():
    """读取根目录下的 guide.pdf 并转为 base64"""
    # 确保文件名和你放在根目录下的文件名一致
    pdf_path = os.path.join(APP_ROOT, 'assets/fine_tuning_guide.pdf') 
    
    if not os.path.exists(pdf_path):
        return {"status": "error", "message": f"未找到文件: {pdf_path}"}

    try:
        with open(pdf_path, "rb") as f:
            encoded_pdf = base64.b64encode(f.read()).decode('utf-8')
            return {"status": "success", "data": encoded_pdf}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    

def start_logic():
    # 重定向标准输出
    sys.stdout = WebviewLogger(window)
    # 执行初始化
    reset_temp_data()
    print("系统环境检查完成...") # 这句会自动出现在前端终端框里
    print("等待用户操作...")


window = None
def main():
    global window
    api = Api()

    # 获取你HTML文件的绝对路径（适配打包前后）
    html_path = get_resource_path("web/index.html")
    
    # 配置PyWebView窗口（可自定义大小、标题、是否可缩放等）
    window = webview.create_window(
        title="RSS推測アプリ ver1.0",  # 窗口标题
        url=html_path,               # 加载你的HTML文件
        js_api=api,
        width=1024,                   # 窗口宽度
        height=768,                  # 窗口高度
        resizable=True,              # 是否允许缩放
        fullscreen=False,             # 是否全屏
        min_size=(1024, 768)        # 关键：设置最小尺寸为1024×768
    )

    # 暴露Python函数给前端JS（关键！）
    window.expose(executeRssPrediction)
    window.expose(get_prediction_data)
    window.expose(download_csv)
    window.expose(upload_csv_files)
    window.expose(reset_temp_data)
    window.expose(executeDataProcessing)
    window.expose(get_help_pdf)

    # 启动窗口（Mac下用webkit引擎）
    webview.start(start_logic, debug=False, gui='webkit2')

if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()