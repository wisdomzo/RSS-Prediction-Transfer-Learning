import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.cm as cm
from matplotlib.colors import Normalize


def compute_cdf(data):
    # 对数据进行排序
    sorted_data = np.sort(data, axis=0)

    # 生成CDF的y值
    cdf = np.arange(1, len(sorted_data) + 1) / len(sorted_data)

    return sorted_data, cdf


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


def plot_MAE_CDF(output_file_path,targetFileAddress, referenceFileAddress=None, needPNG=True, needSVG=False):
    # 1. 全局配置高保真纸张字体（Helvetica）
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['font.sans-serif'] = ['Helvetica', 'Arial', 'DejaVu Sans']

    # 严格执行 7pt / 5pt 的紧凑科研字号，避免文字过大挤压图表空间
    plt.rcParams['font.size'] = 7
    plt.rcParams['axes.labelsize'] = 7
    plt.rcParams['axes.titlesize'] = 7
    plt.rcParams['xtick.labelsize'] = 7
    plt.rcParams['ytick.labelsize'] = 7
    plt.rcParams['legend.fontsize'] = 5 

    # 核心设定：保证导出的 SVG 格式中文字是可编辑的、不会被转为线条（Path）
    plt.rcParams['svg.fonttype'] = 'none'

    # 2. 读取测试集数据并自动计算绝对误差（兼容训练集格式）
    df = pd.read_csv(targetFileAddress)

    if 'Median_Abs_Error' in df.columns:
        error_data = df['Median_Abs_Error'].values
    elif 'Abs_Error' in df.columns:
        error_data = df['Abs_Error'].values
    else:
        # 动态构建绝对误差
        error_data = np.abs(df['Predicted_Value'] - df['RSSI']).values

    sorted_errors = np.sort(error_data)
    y_vals = np.arange(1, len(sorted_errors) + 1) / len(sorted_errors)

    # 3. 计算画布的英寸尺寸 (1 inch = 25.4 mm)
    width_inch = 80 / 25.4
    height_inch = 56.56 / 25.4

    # 创建图形界面
    fig, ax = plt.subplots(figsize=(width_inch, height_inch))

    # 4. 绘制 CDF 曲线
    # darkorange, royalblue, firebrick, seagreen, slateblue, crimson, teal
    ax.plot(sorted_errors, y_vals, color='darkorange', linewidth=1, label='Cross-Validation w/ Fine-Tuned Models')

    # ==================== 核心修正代码 ====================
    # 强制限制画面内“核心图表框”的宽高比例严格等于 80 : 56.56
    # 参数为 (高度 / 宽度)
    ax.set_box_aspect(56.56 / 80.0)
    # ======================================================

    # 5. 标定 50% 与 80% 的关键水位线
    p50_idx = np.searchsorted(y_vals, 0.5)
    p80_idx = np.searchsorted(y_vals, 0.8)
    p50_val = sorted_errors[p50_idx]
    p80_val = sorted_errors[p80_idx]

    # 添加水平/垂直辅助切线
    ax.axhline(0.5, color='gray', linestyle='--', alpha=0.5, linewidth=0.5)
    #ax.axvline(p50_val, color='gray', linestyle=':', alpha=0.5, linewidth=0.5)
    ax.text(p50_val + 0.3, 0.43, f'Median: {p50_val:.2f} dB', color='darkorange', fontsize=5)

    ax.axhline(0.8, color='gray', linestyle='--', alpha=0.5, linewidth=0.5)
    #ax.axvline(p80_val, color='gray', linestyle=':', alpha=0.5, linewidth=0.5)
    ax.text(p80_val + 0.3, 0.73, f'80% CDF: {p80_val:.2f} dB', color='darkorange', fontsize=5)

    if referenceFileAddress is not None:
        # 读取参考数据并计算绝对误差
        df_ref = pd.read_csv(referenceFileAddress)
        error_data_ref = np.abs(df_ref['Predicted_Value'] - df_ref['RSSI']).values
        sorted_errors_ref = np.sort(error_data_ref)
        y_vals_ref = np.arange(1, len(sorted_errors_ref) + 1) / len(sorted_errors_ref)
        ax.plot(sorted_errors_ref, y_vals_ref, color='royalblue', linewidth=1, label='Predictions w/ Basic Models')

        p50_idx_ref = np.searchsorted(y_vals_ref, 0.5)
        p80_idx_ref = np.searchsorted(y_vals_ref, 0.8)
        p50_val_ref = sorted_errors_ref[p50_idx_ref]
        p80_val_ref = sorted_errors_ref[p80_idx_ref]

        ax.text(p50_val_ref + 1.3, 0.52, f'Median: {p50_val_ref:.2f} dB', color='royalblue', fontsize=5)
        ax.text(p80_val_ref + 2.3, 0.82, f'80% CDF: {p80_val_ref:.2f} dB', color='royalblue', fontsize=5)

    error_data_oracle = df['Best_Model_Error'].values
    sorted_errors_oracle = np.sort(error_data_oracle)
    y_vals_oracle = np.arange(1, len(sorted_errors_oracle) + 1) / len(sorted_errors_oracle)
    ax.plot(sorted_errors_oracle, y_vals_oracle, color='firebrick', linewidth=1, label='Oracle Selection w/ Fine-Tuned Models')

    p50_idx_oracle = np.searchsorted(y_vals_oracle, 0.5)
    p80_idx_oracle = np.searchsorted(y_vals_oracle, 0.8)
    p50_val_oracle = sorted_errors_oracle[p50_idx_oracle]
    p80_val_oracle = sorted_errors_oracle[p80_idx_oracle]
    ax.text(p50_val_oracle + 1, 0.6, f'Median: {p50_val_oracle:.2f} dB', color='firebrick', fontsize=5)
    ax.text(p80_val_oracle + 1.3, 0.82, f'80% CDF: {p80_val_oracle:.2f} dB', color='firebrick', fontsize=5)

    # 6. 设置轴标签与美化
    ax.set_title('CDF of Median Absolute Error', fontsize=7, fontweight='bold')
    ax.set_xlabel('Median Absolute Error in dB', fontsize=7)
    ax.set_ylabel('Probability', fontsize=7)
    ax.set_xlim(0, max(max(sorted_errors), max(sorted_errors_ref), max(sorted_errors_oracle)) + 0.5)
    ax.set_ylim(0, 1.02)
    ax.grid(True, alpha=0.2, linestyle=':')
    ax.legend(loc='lower right', fontsize=5)

    # 7. 以 300 DPI 分别导出高保真印刷 PNG 和矢量可编辑格式 SVG
    # 使用 bbox_inches='tight' 确保周围文本不被切掉，同时内部 Box 锁定 80:56.56 比例
    if needPNG:
        plt.savefig(output_file_path + 'MAE_cdf.png', dpi=300, bbox_inches='tight')
    if needSVG:
        plt.savefig(output_file_path + 'MAE_cdf.svg', dpi=300, bbox_inches='tight')

    return




def plot_global_share_pure_matplotlib(output_file_path, file_path, fix_lon=139.674057, fix_lat=35.223331, threshold=10, needPNG=True, needSVG=False):
    # 1. 锁死出版级图表通用 RC 参数（Helvetica + 7pt/5pt 字号阶梯）
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['font.sans-serif'] = ['Helvetica', 'Arial', 'DejaVu Sans']
    plt.rcParams['font.size'] = 7
    plt.rcParams['axes.labelsize'] = 7
    plt.rcParams['axes.titlesize'] = 7
    plt.rcParams['xtick.labelsize'] = 5
    plt.rcParams['ytick.labelsize'] = 5
    plt.rcParams['svg.fonttype'] = 'none' # 极其关键：维持 Inkscape 内文字完全为可编辑的独立文本图层

    # 读取输入文件
    df = pd.read_csv(file_path)

    # 大圆球面距离重算函数 (Haversine Formula)
    def haversine_dist(lon1, lat1, lon2, lat2):
        R = 6371.0088
        lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = np.sin(dlat / 2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2)**2
        return 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a)) * R * 1000

    # 重新计算距离
    df['calc_dist'] = haversine_dist(df['Longitude'], df['Latitude'], fix_lon, fix_lat)

    # 定义距离与 DN 分箱边界
    dist_bins = [0, 500, 1000, 1500, 2000, 2500, 3500]
    dist_labels = ['0-500 m', '500-1k m', '1k-1.5k m', '1.5k-2k m', '2k-2.5k m', '>2.5k m']
    dn_bins = [0, 30, 60, 80, 100]
    dn_labels = ['0-30 m', '30-60 m', '60-80 m', '80-100 m']

    df['dist_band'] = pd.cut(df['calc_dist'], bins=dist_bins, labels=dist_labels, include_lowest=True)
    df['dn_band'] = pd.cut(df['DN'], bins=dn_bins, labels=dn_labels, include_lowest=True)

    # 全局分母：计算全地图范围内大误差（>threshold dB）的总点数
    grand_total_gt10 = (df['Median_Abs_Error'] > threshold).sum()

    # 计算大误差份额矩阵
    df_val = pd.DataFrame(index=dn_labels, columns=dist_labels, dtype=float)
    df_text = pd.DataFrame(index=dn_labels, columns=dist_labels, dtype=object)

    for dn in dn_labels:
        for d in dist_labels:
            sub = df[(df['dn_band'] == dn) & (df['dist_band'] == d)]
            cell_gt10 = (sub['Median_Abs_Error'] > threshold).sum()
            
            # 计算全局贡献份额
            pct_global = (cell_gt10 / grand_total_gt10) * 100
            df_val.loc[dn, d] = pct_global
            df_text.loc[dn, d] = f"{pct_global:.1f}%"

    # 倒序处理：让浅层遮挡（0-30m）在底部，深层在顶部
    df_val_final = df_val.iloc[::-1]
    df_text_final = df_text.iloc[::-1]
    matrix_data = df_val_final.values

    # 2. 精准映射画布物理尺寸 (80mm x 56.56mm)
    width_inch = 80 / 25.4
    height_inch = 56.56 / 25.4
    
    # 建立独立双通道，彻底切断主图文字与右侧指标条的交叠空间
    fig, (ax, cbar_ax) = plt.subplots(1, 2, figsize=(width_inch, height_inch), 
                                       gridspec_kw={'width_ratios': [20, 1]})

    # 3. 使用纯 matplotlib 渲染矩阵底色
    cmap = cm.get_cmap('YlOrRd')
    norm = Normalize(vmin=0, vmax=20)
    im = ax.imshow(matrix_data, cmap=cmap, norm=norm, aspect='auto')

    # ==================== 强制限定内部框比例为 80:56.56 ====================
    ax.set_box_aspect(56.56 / 80.0)
    # ==========================================================================

    # 4. 手工添加网格内的数值标签（智能判定文字前背景对比色，防止黑字看不清）
    nrows, ncols = matrix_data.shape
    for i in range(nrows):
        for j in range(ncols):
            val_str = df_text_final.iloc[i, j]
            # 如果背景色太深（份额 > 12%），文字自动转为白色，其余为黑色，保证极致的清晰度
            text_color = 'white' if matrix_data[i, j] > 12 else 'black'
            ax.text(j, i, val_str, ha='center', va='center', fontsize=5, color=text_color)

    # 5. 图表轴细节美化与刻度对齐
    ax.set_xticks(np.arange(ncols))
    ax.set_yticks(np.arange(nrows))
    ax.set_title(f'Spatial Share of MAE > {threshold} dB', fontsize=7, fontweight='bold')
    ax.set_xlabel('Geographical Distance Between Transceivers in m', fontsize=7)
    ax.set_ylabel('Mobile Altitude in m', fontsize=7)

    # 轴标签防拥挤优化
    ax.set_xticklabels(dist_labels, rotation=30, ha='right', fontsize=5)
    ax.set_yticklabels(df_val_final.index, rotation=0, fontsize=5)

    # 6. 独立通道内的纯 Matplotlib 指标条渲染
    cbar = fig.colorbar(im, cax=cbar_ax)
    cbar_ax.tick_params(labelsize=4, pad=1)
    cbar_ax.set_ylabel('Percentage in %', fontsize=5, labelpad=3)

    # 调整两子图间的物理宽度，留出呼吸空间
    plt.subplots_adjust(wspace=0.15)
    
    # 7. 同时输出高保真印刷级 PNG 和 Inkscape 二次编辑专用矢量 SVG
    if needPNG:
        plt.savefig(output_file_path + 'MAE_heatmap_' + str(threshold) + 'dB.png', dpi=300, bbox_inches='tight')
    if needSVG:
        plt.savefig(output_file_path + 'MAE_heatmap_' + str(threshold) + 'dB.svg', dpi=300, bbox_inches='tight')
        pass
    print("Pure matplotlib version generated successfully.")



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
    targetFileAddress = "/Users/zhaoou/Desktop/課題1_TL拡張/TL検証/220MHz/oof_analysis_FT30.csv"
    referenceFileAddress = "/Users/zhaoou/Desktop/課題1_TL拡張/TL検証/220MHz/predict_RSS_M0.csv"
    outputFileAddress = "/Users/zhaoou/Downloads/"

    plot_MAE_CDF(outputFileAddress, targetFileAddress, referenceFileAddress, needPNG=True, needSVG=False)
    plot_global_share_pure_matplotlib(outputFileAddress, targetFileAddress, fix_longitude, fix_latitude, threshold=10, needPNG=True, needSVG=False)

    return


if __name__ == "__main__":
    import sys
    main() 