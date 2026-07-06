import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.cm as cm
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.colors import Normalize
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from scipy.spatial import ConvexHull
from scipy.stats import norm
import scipy.stats as stats
from scipy.spatial.distance import cdist
from sklearn.cluster import DBSCAN
from math import radians, sin, cos, sqrt, atan2
import os
import re


def compute_cdf(data):
    # 对数据进行排序
    sorted_data = np.sort(data, axis=0)

    # 生成CDF的y值
    cdf = np.arange(1, len(sorted_data) + 1) / len(sorted_data)

    return sorted_data, cdf


def normalize_matplotlib_color(color_value):
    color = str(color_value or "").strip()
    if re.fullmatch(r"#[0-9a-fA-F]{6}", color):
        return color
    rgb_match = re.fullmatch(r"rgb\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*\)", color)
    if rgb_match:
        channels = [max(0, min(255, int(value))) / 255 for value in rgb_match.groups()]
        return tuple(channels)
    return None


def plot(*args):
    if len(args) == 2:
        plt.plot(args[0], args[1], color='b', marker='.', linestyle='')
        plt.show()

    if len(args) == 3:
        # 启用交互式绘图（在 Jupyter Notebook 中使用）
        plt.ion()  # 仅在 Jupyter Notebook 中使用
        # plt.show()  # 在非交互模式下，可以使用这行

        # 创建 3D 图形
        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')

        # 绘制三维散点图
        sc = ax.scatter(args[0], args[1], args[2], c='b', marker='.', linestyle='')

        # 添加坐标轴标签
        ax.set_xlabel('X Label')
        ax.set_ylabel('Y Label')
        ax.set_zlabel('Z Label')

        # 显示图形
        plt.show()

        # 之后可以进行手动编辑，比如使用图形界面的工具进行缩放、平移等
    return


def plot_Four_Scenarios_Error_CDF(folderAddress, needPNG, needSVG):
    """
    读取四个指定切分场景的 CSV 文件，计算其绝对误差并绘制学术级对比 CDF 图。
    
    包含的文件：
    1. predict_RSS_beforeFT.csv (微调前基准)
    2. predict_RSS_height.csv   (高不确定性微调后)
    3. predict_RSS_low.csv      (低不确定性微调后)
    4. predict_RSS_random_42.csv   (随机不确定性微调后)
    5. predict_RSS_proposal.csv   (高不确定性+多样性微调后)
    """
    # ========================================================
    # 1. 全局配置高保真纸张字体与科研规格（严格匹配你的标准）
    # ========================================================
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['font.sans-serif'] = ['Helvetica', 'Arial', 'DejaVu Sans']

    # 严格执行 7pt / 5pt 的紧凑科研字号
    plt.rcParams['font.size'] = 7
    plt.rcParams['axes.labelsize'] = 7
    plt.rcParams['axes.titlesize'] = 7
    plt.rcParams['xtick.labelsize'] = 7
    plt.rcParams['ytick.labelsize'] = 7
    plt.rcParams['legend.fontsize'] = 7

    # 设定精确的物理画布尺寸 (mm 转换为 inch) -> 标准单栏微型图
    width_inch = 80 / 25.4
    height_inch = 56.56 / 25.4
    plt.rcParams['svg.fonttype'] = 'none'

    # ========================================================
    # 2. 定义文件配置映射（物理文件名、图例标签、颜色、线型）
    # ========================================================
    file_configs = [
        {
            'filename': 'predict_RSS_beforeFT.csv',
            'label': 'Baseline',
            'color': "#000000",       # 黑基准线
            'linestyle': '--'         # 虚线代表未微调
        },
        {
            'filename': 'predict_RSS_low.csv',
            'label': 'Bottom-U',
            'color': '#002FA7',       # 浅绿
            'linestyle': '-'
        },
        {
            'filename': 'predict_RSS_random_42.csv',
            'label': 'Random',
            'color': '#6ECC54',       # 橙色
            'linestyle': '-'
        },
        {
            'filename': 'predict_RSS_hight.csv',
            'label': 'Top-U',
            'color': '#EB5C20',       # 沉稳学术蓝（期望中最优的曲线）
            'linestyle': '-'
        },
        {
            'filename': 'predict_RSS_proposal.csv',
            'label': 'URAS (proposed)',
            'color': '#C8161D',
            'linestyle': '-'
        }
    ]

    # ========================================================
    # 3. 开始创建 matplotlib 画布
    # ========================================================
    fig, ax = plt.subplots(figsize=(width_inch, height_inch), dpi=300)
    
    print("--- CDF 统计分析审查中 ---")
    valid_plots = 0

    # ========================================================
    # 4. 循环读取、计算绝对误差并绘制 CDF 曲线
    # ========================================================
    for cfg in file_configs:
        file_path = os.path.join(folderAddress, cfg['filename'])
        
        if not os.path.exists(file_path):
            print(f"Warning: File not found: {cfg['filename']}, skipped.")
            continue
            
        # 读取数据
        df = pd.read_csv(file_path)
        if len(df) == 0:
            print(f"Warning: File is empty: {cfg['filename']}, skipped.")
            continue
            
        # 计算绝对误差 (Absolute Error)
        abs_error = (df['RSSI'] - df['Predicted_Value']).abs().dropna().values
        
        # 核心数学逻辑：计算 CDF
        sorted_error = np.sort(abs_error)
        cdf_y = np.arange(1, len(sorted_error) + 1) / len(sorted_error)
        
        # 绘制该场景的 CDF 趋势线
        ax.plot(
            sorted_error, 
            cdf_y, 
            label=cfg['label'], 
            color=cfg['color'], 
            linestyle=cfg['linestyle'],
            linewidth=1.0
        )
        
        # 顺便计算并打印中位数误差(50% CDF)，方便你在论文文字里描述
        median_err = np.median(abs_error)
        print(f"✓ 成功加载 {cfg['filename']}: 样本数 = {len(abs_error)}, 中位数误差 = {median_err:.2f} dB")
        valid_plots += 1

    if valid_plots == 0:
        print("Error: No valid data files were found to plot. Check folder path.")
        return

    # ========================================================
    # 5. 图表细节修饰（无 Title 且极限压紧空间）
    # ========================================================
    ax.set_xlabel('Absolute Error in dB', labelpad=2)
    ax.set_ylabel('CDF', labelpad=2)

    # 严谨的 CDF 坐标范围控制（从0到1）
    ax.set_ylim(0, 1.02)
    ax.set_xlim(0, None)  # 误差从0开始，右边界自适应
    #ax.set_xlim(0, 30) 
    
    # 细化网格参考线
    ax.grid(axis='both', linestyle='--', linewidth=0.5, alpha=0.4)

    # 严谨的论文右下角（或左上角）小图例，这里设在右下角防止挡住 CDF 曲线抬头
    ax.legend(
        loc='lower right', 
        frameon=True, 
        edgecolor='#e0e0e0',
        fancybox=False,
        borderpad=0.3,       
        labelspacing=0.3     
    )

    # ========================================================
    # 6. 极致余白压缩与精确画布保存
    # ========================================================
    # top=0.96 完全释放 Title 占用的空间，实现紧凑度最大化
    plt.subplots_adjust(left=0.12, right=0.97, top=0.96, bottom=0.14)

    filename = 'Four_Scenarios_Error_CDF'
    svg_output = os.path.join(folderAddress, f'{filename}.svg')
    png_output = os.path.join(folderAddress, f'{filename}.png')
    
    save_props = {'dpi': 300, 'bbox_inches': 'tight', 'pad_inches': 0.012}
    
    if needSVG:
        plt.savefig(svg_output, format='svg', **save_props)
    if needPNG:
        plt.savefig(png_output, **save_props)
    
    plt.show()
    print("================ CDF 绘图任务圆满完成 ================")


def plot_Travel_Distance(folderAddress,
                         start_lat,
                         start_lon,
                         needPNG=True,
                         needSVG=False):
    """
    计算四种采样方法的总移动距离（Nearest Neighbor）
    并绘制柱状图。

    Parameters
    ----------
    folderAddress : str
        CSV所在文件夹

    start_lat : float
        起点纬度

    start_lon : float
        起点经度
    """

    # ==========================================================
    # 字体配置（与你CDF保持一致）
    # ==========================================================
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['font.sans-serif'] = ['Helvetica', 'Arial', 'DejaVu Sans']

    plt.rcParams['font.size'] = 7
    plt.rcParams['axes.labelsize'] = 7
    plt.rcParams['xtick.labelsize'] = 7
    plt.rcParams['ytick.labelsize'] = 7

    width_inch = 80 / 25.4
    height_inch = 56.56 / 25.4

    plt.rcParams['svg.fonttype'] = 'none'

    # ==========================================================
    # 文件配置
    # ==========================================================
    file_configs = [
        {
            'filename': 'random_42_ft_10p.csv',
            'label': 'Random',
            'color': '#6ECC54'
        },
        {
            'filename': 'highUncertainty_ft_10p.csv',
            'label': 'Top-U',
            'color': '#EB5C20'
        },
        {
            'filename': 'lowUncertainty_ft_10p.csv',
            'label': 'Bottom-U',
            'color': '#002FA7'
        },
        {
            'filename': 'proposal_ft_10p.csv',
            'label': 'URAS',
            'color': '#C8161D'
        }
    ]

    # ==========================================================
    # Haversine距离（单位 km）
    # ==========================================================
    def haversine(lat1, lon1, lat2, lon2):

        R = 6371.0

        lat1 = radians(lat1)
        lon1 = radians(lon1)
        lat2 = radians(lat2)
        lon2 = radians(lon2)

        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = sin(dlat/2)**2 + cos(lat1)*cos(lat2)*sin(dlon/2)**2
        c = 2*atan2(sqrt(a), sqrt(1-a))

        return R*c

    # ==========================================================
    # Nearest Neighbor路径长度
    # ==========================================================
    def nearest_neighbor_distance(points,
                                  start_lat,
                                  start_lon):

        unvisited = points.copy()

        current_lat = start_lat
        current_lon = start_lon

        total_distance = 0

        while len(unvisited) > 0:

            distances = [
                haversine(current_lat,
                          current_lon,
                          p[0],
                          p[1])
                for p in unvisited
            ]

            idx = np.argmin(distances)

            total_distance += distances[idx]

            current_lat, current_lon = unvisited.pop(idx)

        return total_distance


    labels = []
    distances = []
    colors = []

    print("======== Travel Distance Analysis ========")

    for cfg in file_configs:

        file_path = os.path.join(folderAddress,
                                 cfg['filename'])

        if not os.path.exists(file_path):
            print(f"Missing: {cfg['filename']}")
            continue

        df = pd.read_csv(file_path)

        # 经纬度列名
        lat_col = 'Latitude'
        lon_col = 'Longitude'

        points = list(zip(df[lat_col], df[lon_col]))

        total_dist = nearest_neighbor_distance(points,
                                               start_lat,
                                               start_lon)

        print(f"{cfg['label']:10s}: {total_dist:.2f} km")

        labels.append(cfg['label'])
        distances.append(total_dist)
        colors.append(cfg['color'])

    # ==========================================================
    # 绘图
    # ==========================================================
    fig, ax = plt.subplots(figsize=(width_inch, height_inch),
                           dpi=300)

    bars = ax.bar(labels,
                  distances,
                  color=colors,
                  width=0.7)

    ax.set_ylabel('Travel Distance (km)')
    ax.grid(axis='y',
            linestyle='--',
            linewidth=0.5,
            alpha=0.4)

    # 数值标注
    for bar, d in zip(bars, distances):
        ax.text(bar.get_x() + bar.get_width()/2,
                bar.get_height(),
                f"{d:.1f}",
                ha='center',
                va='bottom',
                fontsize=6)

    plt.subplots_adjust(left=0.16,
                        right=0.98,
                        top=0.96,
                        bottom=0.16)

    filename = "Travel_Distance"

    if needPNG:
        plt.savefig(os.path.join(folderAddress,
                                 filename + ".png"),
                    dpi=300,
                    bbox_inches='tight',
                    pad_inches=0.012)

    if needSVG:
        plt.savefig(os.path.join(folderAddress,
                                 filename + ".svg"),
                    format='svg',
                    dpi=300,
                    bbox_inches='tight',
                    pad_inches=0.012)

    plt.show()

    print("======== Finished ========")


def plot_Model_Aggregation_Error_CDF(csv_paths, output_folder, needPNG=True, needSVG=True, display_mode="both", file_colors=None):
    """
    Validate one or more prediction CSV files, compute ensemble median/mean RSSI
    estimates from Model_* columns, and plot their absolute-error CDF curves.
    """
    if isinstance(csv_paths, (str, os.PathLike)):
        csv_paths = [csv_paths]

    if display_mode not in {"both", "mean", "median"}:
        display_mode = "both"

    color_lookup = {}
    if isinstance(file_colors, dict):
        color_lookup = {str(key): value for key, value in file_colors.items() if value}

    os.makedirs(output_folder, exist_ok=True)
    model_column_pattern = re.compile(r"^Model_(\d+)$")
    valid_results = []
    skipped_files = []

    for csv_path in csv_paths or []:
        file_name = os.path.basename(str(csv_path))
        try:
            df = pd.read_csv(csv_path)
        except Exception as exc:
            skipped_files.append({"file": file_name, "reason": f"Could not read CSV: {exc}"})
            continue

        rssi_column = next((col for col in df.columns if col.lower() == "rssi"), None)
        model_columns = [col for col in df.columns if model_column_pattern.match(str(col))]
        model_columns = sorted(
            model_columns,
            key=lambda col: int(model_column_pattern.match(str(col)).group(1))
        )

        if not rssi_column:
            skipped_files.append({"file": file_name, "reason": "Missing RSSI or rssi column."})
            continue
        if not model_columns:
            skipped_files.append({"file": file_name, "reason": "Missing Model_* columns such as Model_0, Model_1, ..."})
            continue

        numeric = df[[rssi_column] + model_columns].apply(pd.to_numeric, errors="coerce")
        rssi = numeric[rssi_column]
        model_values = numeric[model_columns]
        ensemble_median = model_values.median(axis=1, skipna=True)
        ensemble_mean = model_values.mean(axis=1, skipna=True)
        valid_rows = pd.DataFrame({
            "RSSI": rssi,
            "Median": ensemble_median,
            "Mean": ensemble_mean
        }).dropna()

        if valid_rows.empty:
            skipped_files.append({"file": file_name, "reason": "No valid numeric rows after cleaning RSSI and Model_* values."})
            continue

        median_abs_error = (valid_rows["Median"] - valid_rows["RSSI"]).abs().to_numpy()
        mean_abs_error = (valid_rows["Mean"] - valid_rows["RSSI"]).abs().to_numpy()
        selected_color = color_lookup.get(str(csv_path)) or color_lookup.get(file_name)
        valid_results.append({
            "file": file_name,
            "color": selected_color,
            "sample_count": int(len(valid_rows)),
            "model_columns": model_columns,
            "median_abs_error": median_abs_error,
            "mean_abs_error": mean_abs_error,
            "median_absolute_error_mean": float(np.mean(median_abs_error)),
            "mean_absolute_error_mean": float(np.mean(mean_abs_error)),
            "median_absolute_error_median": float(np.median(median_abs_error)),
            "mean_absolute_error_median": float(np.median(mean_abs_error)),
        })

    if not valid_results:
        return {
            "status": "error",
            "message": "No valid CSV files were available for data analysis.",
            "files": [],
            "skipped_files": skipped_files,
        }

    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['font.sans-serif'] = ['Helvetica', 'Arial', 'DejaVu Sans']
    plt.rcParams['font.size'] = 7
    plt.rcParams['axes.labelsize'] = 7
    plt.rcParams['axes.titlesize'] = 7
    plt.rcParams['xtick.labelsize'] = 7
    plt.rcParams['ytick.labelsize'] = 7
    plt.rcParams['legend.fontsize'] = 6
    plt.rcParams['svg.fonttype'] = 'none'

    width_inch = 80 / 25.4
    height_inch = 56.56 / 25.4
    fig = Figure(figsize=(width_inch, height_inch), dpi=300)
    FigureCanvasAgg(fig)
    ax = fig.subplots()
    default_colors = [
        "#1f77b4", "#d62728", "#2ca02c", "#9467bd", "#ff7f0e",
        "#17becf", "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22",
        "#003f5c", "#bc5090", "#ffa600", "#58508d", "#00876c",
    ]

    for index, result in enumerate(valid_results):
        color = normalize_matplotlib_color(result.get("color")) or default_colors[index % len(default_colors)]
        sorted_mean, mean_cdf = compute_cdf(result["mean_abs_error"])
        sorted_median, median_cdf = compute_cdf(result["median_abs_error"])
        label_prefix = os.path.splitext(result["file"])[0]
        if display_mode in {"both", "median"}:
            ax.plot(
                sorted_median,
                median_cdf,
                label=f"{label_prefix} median",
                color=color,
                linestyle="-",
                linewidth=1.0,
            )
        if display_mode in {"both", "mean"}:
            ax.plot(
                sorted_mean,
                mean_cdf,
                label=f"{label_prefix} mean",
                color=color,
                linestyle=":",
                linewidth=1.0,
            )

    ax.set_xlabel('Absolute Error in dB', labelpad=2)
    ax.set_ylabel('CDF', labelpad=2)
    ax.set_ylim(0, 1.02)
    ax.set_xlim(0, None)
    ax.grid(axis='both', linestyle='--', linewidth=0.5, alpha=0.4)
    ax.legend(
        loc='lower right',
        frameon=True,
        edgecolor='#e0e0e0',
        fancybox=False,
        borderpad=0.3,
        labelspacing=0.25
    )
    fig.subplots_adjust(left=0.12, right=0.97, top=0.96, bottom=0.14)

    filename = 'Model_Aggregation_Error_CDF'
    svg_output = os.path.join(output_folder, f'{filename}.svg')
    png_output = os.path.join(output_folder, f'{filename}.png')
    save_props = {'dpi': 300, 'bbox_inches': 'tight', 'pad_inches': 0.012}

    if needSVG:
        fig.savefig(svg_output, format='svg', **save_props)
    if needPNG:
        fig.savefig(png_output, **save_props)
    fig.clear()

    return {
        "status": "success",
        "message": f"Generated CDF analysis for {len(valid_results)} valid CSV file(s).",
        "display_mode": display_mode,
        "valid_file_count": len(valid_results),
        "files": [
            {
                key: value
                for key, value in result.items()
                if key not in {"median_abs_error", "mean_abs_error"}
            }
            for result in valid_results
        ],
        "skipped_files": skipped_files,
        "svg_path": svg_output if needSVG else "",
        "png_path": png_output if needPNG else "",
    }


def main():
    '''
    请严格按照以下【科研出版级制图规范】为我编写 Python 绘图代码，并读取指定的数据文件运行生成图表：

    1. 画布与几何比例规范：
    - 目标物理尺寸：画布总宽 80 mm，总高 56.56 mm。代码中需精准转换为英寸 (figsize=(80/25.4, 56.56/25.4))。
    - 核心图表框比例：必须使用 `ax.set_box_aspect(56.56 / 80.0)` 强制锁定内部坐标轴框的宽高几何比例完美满足 80:56.56。
    - 边缘排版：保存时使用 `bbox_inches='tight'` 以确保小尺寸下的轴标签和标题绝对不会被切掉。

    2. 字体与字号阶梯规范：
    - 字体家族：全局指定为无衬线字体，优先采用 'Helvetica'（依次无缝回退 'Arial', 'DejaVu Sans'）。
    - 字号主阶梯：主标题、X/Y 轴标签、Y 轴刻度字号严格锁定为 7 pt。
    - 局部微调字号：图例 (Legend)、柱头/线旁的数据标签、以及空间较窄时的 X 轴刻度，允许使用 4 pt 到 5 pt，以确保整体视觉紧凑且不拥挤。

    3. 矢量编辑与文本保护规范（针对 Inkscape 后期）：
    - 必须在代码最前端声明：`plt.rcParams['svg.fonttype'] = 'none'`。
    - 作用：确保导出的 SVG 文件中，所有文本（标题、刻度、数据标注）都保持为“独立可编辑的文本对象”，禁止被强制退化转换为矢量路径(Path)，以便于在 Inkscape 中双击修改或换色。

    4. 视觉防重叠与美化技术：
    - 如果是折线图/CDF图的多曲线标注，不同曲线的分位数文字严禁使用固定坐标堆叠。需使用非对称纵向交错法（一组 va='top' 挂在线下，一组 va='bottom' 飘在线上）或直接集成进 Legend 中。
    - 如果是多维组合柱状图，柱头数据标签（如 XX%）字号缩至 4 pt 且必须设置 `rotation=90`（垂直向上延伸），确保横向绝对不打架。
    - 辅助线（如 axhline, axvline）的线宽 (linewidth) 必须压低至 0.5 ~ 0.6，颜色采用 'gray' 且设置半透明 `alpha=0.5`，确保主次分明，整体风格精致细腻。
    - X 轴长文本标签需设置 `rotation=30, ha='right'` 斜向对齐，防止横向挤压。

    5. 文件输出要求：
    - 运行后必须同时输出 300 DPI 印刷级 PNG 图像和完全矢量可编辑的 SVG 文件。

    =========================================
    【当前任务信息】
    - 数据源文件：[请在此处输入你的文件名，例如：predict_RSS_TL_30.csv]
    - 期望图表类型：[请在此处输入图表类型，例如：CDF图 / 多阈值分组柱状图 / 散点图]
    - 具体的X/Y轴与绘图逻辑要求：[请在此处简述你的绘图想法，例如：横轴是disBtwTxRx，以500米为间隔，纵轴为大于6.15的数量占该距离段总数的百分比...]
    =========================================
    '''

    # 参数配置
    # EIRP = 37  # dBm
    fix_longitude = 139.674057
    fix_latitude = 35.223331
    # fix_altitude = 115 #海拔79.74米，楼35.2米
    # fix_antennaHeight = 1.8
    # move_antennaHeight = 1.37
    targetFileAddress = "/Users/zhaoou/Desktop/課題1_TL拡張/TL検証/920MHz/predict_RSS_FT30.csv"
    referenceFileAddress = "/Users/zhaoou/Desktop/課題1_TL拡張/TL検証/920MHz/predict_RSS_M0_test_30.csv"
    outputFileAddress = "/Users/zhaoou/Downloads/"
    #folderAddress = "/Users/zhaoou/Desktop/課題1_TL拡張/不確実性検証/unseen1011"


    folderAddress = "/Users/zhaoou/Desktop/課題1_TL拡張/不確実性検証/unseen1"
    folderAddress1 = "/Users/zhaoou/Desktop/課題1_TL拡張/不確実性検証/unseen1011"
    folderAddress2 = "/Users/zhaoou/Desktop/課題1_TL拡張/不確実性検証/unseen1213"
    folderAddress3 = "/Users/zhaoou/Desktop/課題1_TL拡張/不確実性検証/unseen1"
    start_lat_unseen1011 = 26.61895
    start_lon_unseen1011 = 127.984681
    start_lat_unseen1 = 35.27004166
    start_lon_unseen1 = 137.7153306
    start_lat_unseen1213 = 33.62094
    start_lon_unseen1213 = 133.718148
    start_lat_unseen45 = 33.1848442
    start_lon_unseen45 = 133.0474619
    start_lat_unseen14 = 36.2509355
    start_lon_unseen14 = 137.9773808
    start_lat_unseen67 = 26.2477756
    start_lon_unseen67 = 127.7739396

    # RCC函数
    #plot_Four_Scenarios_Error_CDF(folderAddress, needPNG=False, needSVG=True)
    #split_dataset_by_region_stratified_sampling(folderAddress,fileName="predict_RSS.csv",lat_col="Latitude",lon_col="Longitude")
    plot_Travel_Distance(folderAddress, start_lat = start_lat_unseen1, start_lon = start_lon_unseen1, needPNG=True, needSVG=False)
    
    return





if __name__ == "__main__":
    import sys,os
    main() 
