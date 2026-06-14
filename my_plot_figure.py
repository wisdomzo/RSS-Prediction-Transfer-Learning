import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.cm as cm
from matplotlib.colors import Normalize
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from scipy.spatial import ConvexHull


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

    if 'Best_Model_Error' in df.columns:
        error_data_oracle = df['Best_Model_Error'].values
    else:
        model_cols = [col for col in df.columns if col.startswith('Model_')]
        absolute_errors = df[model_cols].sub(df['RSSI'], axis=0).abs()
        error_data_oracle = absolute_errors.min(axis=1).values
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
    if referenceFileAddress is not None:
        ax.set_xlim(0, max(max(sorted_errors), max(sorted_errors_ref), max(sorted_errors_oracle)) + 0.5)
    else:
        ax.set_xlim(0, max(max(sorted_errors), max(sorted_errors_oracle)) + 0.5)
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


def plot_dynamic_clustering_high_error_heatmap(outputFileAddress, file_path, fix_longitude, fix_latitude, mae_threshold=5.0, n_clusters=6, needPNG=True, needSVG=False):
    """
    仅针对 MAE 大于指定阈值的恶性样本点进行自适应空间环境聚类并绘制热力图
    """
    # 1. 锁死出版级图表通用 RC 参数（Helvetica + 严谨字号阶梯）
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['font.sans-serif'] = ['Helvetica', 'Arial', 'DejaVu Sans']
    plt.rcParams['font.size'] = 7
    plt.rcParams['axes.labelsize'] = 7
    plt.rcParams['axes.titlesize'] = 7
    plt.rcParams['xtick.labelsize'] = 5
    plt.rcParams['ytick.labelsize'] = 5
    plt.rcParams['svg.fonttype'] = 'none'

    # 读取输入文件
    df = pd.read_csv(file_path)
    
    # 发射机固定端经纬度
    tx_lon = fix_longitude
    tx_lat = fix_latitude

    # 大圆球面距离重算函数 (Haversine Formula)
    def haversine_dist(lon1, lat1, lon2, lat2):
        R = 6371.0088
        lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = np.sin(dlat / 2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2)**2
        return 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a)) * R * 1000

    # 重新计算距离
    df['calc_dist'] = haversine_dist(df['Longitude'], df['Latitude'], tx_lon, tx_lat)

    # ==================== 核心改动：仅保留绝对误差大于阈值的顽固样本 ====================
    if 'Median_Abs_Error' not in df.columns:
        df['Median_Abs_Error'] = np.abs(df['Predicted_Value'] - df['RSSI'])
    df_filtered = df[df['Median_Abs_Error'] > mae_threshold].copy()

    total_bad_points = len(df_filtered)
    print(f"📊 过滤完成：全图绝对误差 > {mae_threshold}dB 的高风险样本共计 {total_bad_points} 个。")
    
    if total_bad_points < n_clusters:
        print(f"⚠️ 恶性样本点数 ({total_bad_points}) 少于设定的聚类数 ({n_clusters})，请调低阈值或减少簇数！")
        return
    # ==================================================================================

    # 提取过滤后的核心特征并标准化
    X = df_filtered[['calc_dist', 'DN']].values
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # 对大误差样本点执行 K-Means 动态聚类
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    df_filtered['cluster'] = kmeans.fit_predict(X_scaled)

    # 计算大误差簇内部的 MAE 统计值
    cluster_max_mae = df_filtered.groupby('cluster')['Median_Abs_Error'].max().to_dict()

    # 2. 精准映射画布物理尺寸 (80mm x 56.56mm)
    width_inch = 80 / 25.4
    height_inch = 56.56 / 25.4
    
    # 建立独立双通道，彻底隔离主图文本与右侧指标条
    fig, (ax, cbar_ax) = plt.subplots(1, 2, figsize=(width_inch, height_inch), 
                                       gridspec_kw={'width_ratios': [20, 1]})

    # 强制限定核心内部框比例为 80:56.56
    ax.set_box_aspect(56.56 / 80.0)

    # 动态设定色彩映射范围（根据过滤后的真实 MAE 上下界自适应）
    vmin = df_filtered['Median_Abs_Error'].min()
    vmax = df_filtered['Median_Abs_Error'].max()
    cmap = plt.get_cmap('YlOrRd')

    # 3. 动态绘制每个恶性环境簇的边界凸包
    for cluster_id in range(n_clusters):
        cluster_pts = X[df_filtered['cluster'] == cluster_id]
        max_mae_val = cluster_max_mae[cluster_id]
        
        # 归一化色彩计算
        color = cmap((max_mae_val - vmin) / (max(vmax - vmin, 0.1)))
        
        # 防御性重构：过滤完全重合的重复坐标点
        unique_pts = np.unique(cluster_pts, axis=0)
        
        if len(unique_pts) >= 3:
            try:
                # 引入 QJ 参数彻底化解一维退化共线报错
                hull = ConvexHull(cluster_pts, qhull_options='QJ')
                polygon_pts = cluster_pts[hull.vertices]
                
                # 填充恶性盲点分布多边形
                ax.fill(polygon_pts[:, 0], polygon_pts[:, 1], 
                        facecolor=color, edgecolor='white', linewidth=0.3, alpha=0.85)
            except Exception:
                ax.scatter(cluster_pts[:, 0], cluster_pts[:, 1], color=color, s=8, edgecolor='white', linewidth=0.2)
        else:
            # 样本点过于稀疏或共线时降级为清晰的大散点高亮
            ax.scatter(cluster_pts[:, 0], cluster_pts[:, 1], color=color, s=8, edgecolor='white', linewidth=0.2)
            
        # 在群落中心喷涂 MAE 中位数及包含的恶性点数量
        cx = np.mean(cluster_pts[:, 0])
        cy = np.mean(cluster_pts[:, 1])
        text_ratio = (max_mae_val - vmin) / (max(vmax - vmin, 0.1))
        text_color = 'white' if text_ratio > 0.6 else 'black'
        ax.text(cx, cy, f"{max_mae_val:.1f}\n({len(cluster_pts)})", 
                ha='center', va='center', fontsize=4.2, color=text_color, fontweight='bold')

    # 4. 全量背景点微弱打底（将所有通过和未通过的原始采样点作为背景灰色铺设，凸显对比）
    ax.scatter(df['calc_dist'], df['DN'], c='gray', s=1, alpha=0.10, zorder=0)

    # 5. 图表坐标轴与网格规范化
    ax.set_title(f'Dynamic Clusters of Severe Errors (MAE > {mae_threshold} dB)', fontsize=7, fontweight='bold')
    ax.set_xlabel('Geographical Distance Between Transceivers in m', fontsize=7)
    ax.set_ylabel('Mobile Altitude + Building Height in m', fontsize=7)
    ax.grid(True, linestyle=':', alpha=0.4, color='gray', zorder=0)
    
    # 限制轴边界与全量数据集对齐，确保空间视野不缩水
    ax.set_xlim(0, df['calc_dist'].max() * 1.05)
    ax.set_ylim(0, df['DN'].max() * 1.05)

    # 6. 独立通道内的纯颜色指标条渲染
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(vmin=vmin, vmax=vmax))
    sm.set_array([])
    cbar = fig.colorbar(sm, cax=cbar_ax)
    cbar_ax.tick_params(labelsize=4, pad=1)
    cbar_ax.set_ylabel('Cluster Worst MAE in dB', fontsize=5, labelpad=3)

    # 调整子图间的物理宽度
    plt.subplots_adjust(wspace=0.18)
    
    # 7. 同时输出 PNG 和矢量 SVG
    out_name = f'report_heatmap_bad_clusters_gt{int(mae_threshold)}'
    if needPNG:
        plt.savefig(outputFileAddress + f'{out_name}.png', dpi=300, bbox_inches='tight')
    if needSVG:
        plt.savefig(outputFileAddress + f'{out_name}.svg', dpi=300, bbox_inches='tight')
    print(f"🎉 恶性长尾分析热力图成功导出为 {out_name}.png/.svg")


def plot_vertical_stacked_environment_boxplots(outputFileAddress, file_path, fix_longitude, fix_latitude, needPNG=True, needSVG=False):
    # 1. 锁死出版级图表通用 RC 参数（Helvetica + 严谨字号阶梯）
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['font.sans-serif'] = ['Helvetica', 'Arial', 'DejaVu Sans']
    plt.rcParams['font.size'] = 6.5
    plt.rcParams['axes.labelsize'] = 7
    plt.rcParams['axes.titlesize'] = 7
    plt.rcParams['xtick.labelsize'] = 5.5
    plt.rcParams['ytick.labelsize'] = 5.5
    plt.rcParams['svg.fonttype'] = 'none'

    # 读取输入文件
    df = pd.read_csv(file_path)
    
    # 发射机固定端经纬度
    tx_lon = fix_longitude
    tx_lat = fix_latitude

    # 大圆球面距离重算函数 (Haversine Formula)
    def haversine_dist(lon1, lat1, lon2, lat2):
        R = 6371.0088
        lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = dlon1 = lon2 - lon1
        a = np.sin(dlat / 2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2)**2
        return 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a)) * R * 1000

    # 准备物理坐标
    df['calc_dist'] = haversine_dist(df['Longitude'], df['Latitude'], tx_lon, tx_lat)
    
    # 提取获胜模型的数字 ID
    if 'Best_Model_Idx' not in df.columns:
        model_cols = [col for col in df.columns if col.startswith('Model_')]
        df['Best_Model_Idx'] = df[model_cols].sub(df['RSSI'], axis=0).abs().idxmin(axis=1).str.extract('Model_(\d+)').astype(int)
    df['expert_id'] = df['Best_Model_Idx'].astype(int)

    # 严格准备 0 到 29 的连续横轴
    all_model_ids = list(range(30))
    x_labels = [f"{i}" for i in all_model_ids]
    
    dist_data_per_model = []
    dn_data_per_model = []

    # 无论模型赢没赢过，都在横轴为其保留位置，未赢过的填充空数组以防错位
    for m_id in all_model_ids:
        winner_subset = df[df['expert_id'] == m_id]
        if len(winner_subset) > 0:
            dist_data_per_model.append(winner_subset['calc_dist'].values)
            dn_data_per_model.append(winner_subset['DN'].values)
        else:
            dist_data_per_model.append(np.array([]))
            dn_data_per_model.append(np.array([]))

    # 2. 精准设定画布物理尺寸 (2行1列纵向堆叠，拉宽至 160mm 宽 x 120mm 高)
    width_inch = 160 / 25.4
    height_inch = 120 / 25.4
    
    # sharex=True 让上下两张图完全共享横轴的模型 ID 标签
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(width_inch, height_inch), sharex=True)

    # 配备经典的 tab20 颜色，超过 20 个循环使用，保证 30 个模型颜色分明
    cmap = plt.get_cmap('tab20')
    box_colors = [cmap(i % 20) for i in range(30)]

    # ==================== 上半部分：距离分布箱线图 ====================
    # vert=True 切换为纵向箱线，positions 绑定 0~29 确保与横轴对齐
    bplot1 = ax1.boxplot(dist_data_per_model, vert=True, patch_artist=True, 
                          positions=all_model_ids, widths=0.5,
                          flierprops=dict(marker='o', markersize=1.0, markeredgecolor='gray', alpha=0.3))
    
    # 渲染上色
    for patch, color in zip(bplot1['boxes'], box_colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.75)
        patch.set_edgecolor('black')
        patch.set_linewidth(0.4)
    for median in bplot1['medians']:
        median.set_color('darkred')
        median.set_linewidth(0.8)
        
    ax1.set_title("(a) Geographical Distance Bounds Between Transceivers per Fine-Tuned Model", fontsize=7, fontweight='bold')
    ax1.set_ylabel("Geographical Distance in m", fontsize=7)
    ax1.grid(True, linestyle=':', alpha=0.3, color='gray')

    # ==================== 下半部分：DN 遮挡深度箱线图 ====================
    bplot2 = ax2.boxplot(dn_data_per_model, vert=True, patch_artist=True, 
                          positions=all_model_ids, widths=0.5,
                          flierprops=dict(marker='o', markersize=1.0, markeredgecolor='gray', alpha=0.3))
    
    for patch, color in zip(bplot2['boxes'], box_colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.75)
        patch.set_edgecolor('black')
        patch.set_linewidth(0.4)
    for median in bplot2['medians']:
        median.set_color('darkred')
        median.set_linewidth(0.8)
        
    ax2.set_title("(b) Altitude + Building Height Bounds per Fine-Tuned Model", fontsize=7, fontweight='bold')
    ax2.set_ylabel("Altitude + Building Height in m", fontsize=7)
    ax2.set_xlabel("Fine-Tuned Model ID", fontsize=7)
    ax2.grid(True, linestyle=':', alpha=0.3, color='gray')

    # 设置完美的 X 轴刻度和标签显示
    ax2.set_xticks(all_model_ids)
    ax2.set_xticklabels(x_labels, rotation=45, ha='right')

    # 3. 紧凑排版，压缩上下子图之间的空白，避免跨度过大
    plt.subplots_adjust(hspace=0.18)
    
    # 4. 双格式印刷级输出
    out_name = 'report_stacked_boxplot_models_comparison'
    if needPNG:
        plt.savefig(outputFileAddress + f'{out_name}.png', dpi=300, bbox_inches='tight')
    if needSVG:
        plt.savefig(outputFileAddress + f'{out_name}.svg', dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"🎉 纵向堆叠多维箱线图绘制成功！已导出为 {out_name}.png/.svg")


def plot_Uncertainty_Prediction_Error(folderAddress, needPNG, needSVG):
    # ========================================================
    # 1. 全局配置高保真纸张字体与科研规格（严格匹配你的标准）
    # ========================================================
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['font.sans-serif'] = ['Helvetica', 'Arial', 'DejaVu Sans']

    # 严格执行 7pt / 5pt 的紧凑科研字号，避免文字过大挤压图表空间
    plt.rcParams['font.size'] = 7
    plt.rcParams['axes.labelsize'] = 7
    plt.rcParams['axes.titlesize'] = 7
    plt.rcParams['xtick.labelsize'] = 7
    plt.rcParams['ytick.labelsize'] = 7
    plt.rcParams['legend.fontsize'] = 7 

    # 设定精确的物理画布尺寸 (mm 转换为 inch)
    width_inch = 80 / 24
    height_inch = 56.56 / 24

    # 核心设定：保证导出的 SVG 格式中文字是可编辑的、不会被转为线条（Path）
    plt.rcParams['svg.fonttype'] = 'none'

    # ========================================================
    # 2. 数据读取与并行处理逻辑（220MHz 与 920MHz）
    # ========================================================
    file_path_220 = os.path.join(folderAddress, "predict_RSS_M0_220.csv")
    file_path_920 = os.path.join(folderAddress, "predict_RSS_M0_920.csv")
    
    if not os.path.exists(file_path_220) or not os.path.exists(file_path_920):
        print(f"Error: Make sure both M0_220.csv and M0_920.csv exist in {folderAddress}")
        return

    # 读取并处理 220MHz 数据
    df_220 = pd.read_csv(file_path_220)
    df_220['Absolute_Error'] = (df_220['RSSI'] - df_220['Predicted_Value']).abs()

    # 读取并处理 920MHz 数据
    df_920 = pd.read_csv(file_path_920)
    df_920['Absolute_Error'] = (df_920['RSSI'] - df_920['Predicted_Value']).abs()

    # 初始预设的区间划分边界与标签
    custom_bins = [0, 3, 5, float('inf')]
    custom_labels = ['0-3 dB', '3-5 dB', '> 5 dB']

    # 硬切分区间
    df_220['Uncertainty_Group'] = pd.cut(df_220['Uncertainty'], bins=custom_bins, labels=custom_labels, include_lowest=True)
    df_920['Uncertainty_Group'] = pd.cut(df_920['Uncertainty'], bins=custom_bins, labels=custom_labels, include_lowest=True)

    # 按初始区间粗提取数据
    raw_data_220 = [df_220[df_220['Uncertainty_Group'] == label]['Absolute_Error'].dropna().values for label in custom_labels]
    raw_data_920 = [df_920[df_920['Uncertainty_Group'] == label]['Absolute_Error'].dropna().values for label in custom_labels]

    # ========================================================
    # 3. 动态筛选有数据的区间（0样本数据不留白占位）
    # ========================================================
    active_labels = []
    filtered_data_220 = []
    filtered_data_920 = []

    for i, label in enumerate(custom_labels):
        has_220 = len(raw_data_220[i]) > 0
        has_920 = len(raw_data_920[i]) > 0
        
        if has_220 or has_920:
            active_labels.append(label)
            filtered_data_220.append(raw_data_220[i])
            filtered_data_920.append(raw_data_920[i])

    if not active_labels:
        print("Error: No valid data found in any uncertainty intervals.")
        return

    # 根据筛选后实际剩下的有效区间数量，动态生成 X 轴主刻度
    x_indices = np.arange(1, len(active_labels) + 1)
    
    box_width = 0.25   # 每个单箱体的宽度
    gap = 0.04         # 220和920箱体之间的微小间隙

    # 错开后的精确绘制中心位置坐标
    pos_220 = x_indices - (box_width / 2 + gap / 2)
    pos_920 = x_indices + (box_width / 2 + gap / 2)

    # ========================================================
    # 4. 开始绘制纯 matplotlib 交错并列箱线图
    # ========================================================
    fig, ax = plt.subplots(figsize=(width_inch, height_inch), dpi=300)

    # 共享线条参数，适配 80mm 物理微型图表宽度
    line_props = {
        'medianprops': {'color': '#333333', 'linewidth': 0.7},
        'boxprops': {'linewidth': 0.5},
        'whiskerprops': {'linewidth': 0.5, 'linestyle': '-'},
        'capprops': {'linewidth': 0.5},
        'flierprops': {
            'marker': 'o', 'markersize': 1.2, 'alpha': 0.18, 'markeredgecolor': 'none'
        }
    }

    # 绘制箱线图组
    box_220 = ax.boxplot(filtered_data_220, positions=pos_220, widths=box_width, patch_artist=True, **line_props)
    box_920 = ax.boxplot(filtered_data_920, positions=pos_920, widths=box_width, patch_artist=True, **line_props)

    # ========================================================
    # 5. 配色与高级渐变色控制
    # ========================================================
    color_220 = '#9ecae1'  
    color_920 = '#2171b5'  
    
    for patch in box_220['boxes']:
        patch.set_facecolor(color_220)
        patch.set_edgecolor('#1c4563')

    for patch in box_920['boxes']:
        patch.set_facecolor(color_920)
        patch.set_edgecolor('#082a4d')

    for flier in box_220['fliers']: flier.set_markerfacecolor(color_220)
    for flier in box_920['fliers']: flier.set_markerfacecolor(color_920)

    # ========================================================
    # 6. 图表细节修饰（移除 Title 并压缩余白）
    # ========================================================
    # 移除原有的 ax.set_title()，上方不再预留任何文字空间
    ax.set_xlabel('Uncertainty Intervals', labelpad=2)   # 压紧横轴标签间距
    ax.set_ylabel('Absolute Error in dB', labelpad=2)     # 压紧纵轴标签间距

    # 将 X 轴刻度牢牢固定在两条并列箱体的正中间
    ax.set_xticks(x_indices)
    ax.set_xticklabels(active_labels)
    
    # 优化 X 轴两端留白，既不贴墙也绝不过宽
    ax.set_xlim(0.4, len(active_labels) + 0.6)

    # 细化网格线
    ax.grid(axis='y', linestyle='--', linewidth=0.5, alpha=0.5)

    # 创建紧凑的学术图例
    ax.legend(
        [box_220['boxes'][0], box_920['boxes'][0]], 
        ['220 MHz', '920 MHz'], 
        loc='upper left', 
        frameon=True, 
        edgecolor='#e0e0e0',
        fancybox=False,
        borderpad=0.3,       # 缩减图例内边距
        labelspacing=0.3     # 缩减图例行间距
    )

    # ========================================================
    # 7. 极致余白压缩与精确画布保存
    # ========================================================
    # 使用 subplots_adjust 强制控制绘图边界。
    # top=0.96 彻底吃掉原本留给 Title 的巨大空白，让箱体区域向上延伸
    plt.subplots_adjust(left=0.12, right=0.96, top=0.96, bottom=0.14)

    svg_output = os.path.join(folderAddress, 'Uncertainty_Prediction_Error.svg')
    png_output = os.path.join(folderAddress, 'Uncertainty_Prediction_Error.png')
    
    # 在 savefig 时显式指定 pad_inches=0.012 (约 0.3mm)，实现无宽边裁剪
    save_props = {'dpi': 300, 'bbox_inches': 'tight', 'pad_inches': 0.012}
    
    if needSVG:
        plt.savefig(svg_output, format='svg', **save_props)
    if needPNG:
        plt.savefig(png_output, **save_props)
    
    plt.show()

    # ========================================================
    # 8. 打印每个频段在实际有效区间下的样本量
    # ========================================================
    print("\n--- [220 MHz] 实际样本数量统计 ---")
    print(df_220['Uncertainty_Group'].value_counts().sort_index())
    print("\n--- [920 MHz] 实际样本数量统计 ---")
    print(df_920['Uncertainty_Group'].value_counts().sort_index())


def plot_High_Error_Probability(folderAddress, needPNG, needSVG):
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
    plt.rcParams['legend.fontsize'] = 5 

    # 设定精确的物理画布尺寸 (mm 转换为 inch)
    width_inch = 80 / 25.4
    height_inch = 56.56 / 25.4
    plt.rcParams['svg.fonttype'] = 'none'

    # ========================================================
    # 2. 数据读取与并行处理逻辑（220MHz 与 920MHz）
    # ========================================================
    file_path_220 = os.path.join(folderAddress, "predict_RSS_M0_220.csv")
    file_path_920 = os.path.join(folderAddress, "predict_RSS_M0_920.csv")
    
    if not os.path.exists(file_path_220) or not os.path.exists(file_path_920):
        print(f"Error: Make sure both M0_220.csv and M0_920.csv exist in {folderAddress}")
        return

    # 读取并计算绝对误差
    df_220 = pd.read_csv(file_path_220)
    df_220['Absolute_Error'] = (df_220['RSSI'] - df_220['Predicted_Value']).abs()

    df_920 = pd.read_csv(file_path_920)
    df_920['Absolute_Error'] = (df_920['RSSI'] - df_920['Predicted_Value']).abs()

    # 指定新的区间：0-3, 3-5, >5
    custom_bins = [0, 3, 5, float('inf')]
    custom_labels = ['0-3 dB', '3-5 dB', '> 5 dB']

    # 硬切分区间
    df_220['Uncertainty_Group'] = pd.cut(df_220['Uncertainty'], bins=custom_bins, labels=custom_labels, include_lowest=True)
    df_920['Uncertainty_Group'] = pd.cut(df_920['Uncertainty'], bins=custom_bins, labels=custom_labels, include_lowest=True)

    # ========================================================
    # 3. 核心统计逻辑：计算每个区间内 Error > 10dB 的概率
    # ========================================================
    prob_220 = []
    prob_920 = []
    active_labels = []

    for label in custom_labels:
        sub_220 = df_220[df_220['Uncertainty_Group'] == label]
        sub_920 = df_920[df_920['Uncertainty_Group'] == label]
        
        total_220 = len(sub_220)
        total_920 = len(sub_920)
        
        # 只要有一方有样本，就保留该区间，防止空置错位
        if total_220 > 0 or total_920 > 0:
            active_labels.append(label)
            
            # 计算 220 MHz 的概率
            if total_220 > 0:
                high_err_220 = len(sub_220[sub_220['Absolute_Error'] > 10])
                prob_220.append((high_err_220 / total_220) * 100) # 转换为百分比
            else:
                prob_220.append(0.0)
                
            # 计算 920 MHz 的概率
            if total_920 > 0:
                high_err_920 = len(sub_920[sub_920['Absolute_Error'] > 10])
                prob_920.append((high_err_920 / total_920) * 100)
            else:
                prob_920.append(0.0)

    if not active_labels:
        print("Error: No data found in any of the specified intervals.")
        return

    # ========================================================
    # 4. 绘图坐标计算（并列柱状图）
    # ========================================================
    x_indices = np.arange(1, len(active_labels) + 1)
    bar_width = 0.25   # 柱子宽度
    gap = 0.02         # 柱子间微小间隙

    pos_220 = x_indices - (bar_width / 2 + gap / 2)
    pos_920 = x_indices + (bar_width / 2 + gap / 2)

    # ========================================================
    # 5. 开始绘制纯 matplotlib 柱状图
    # ========================================================
    fig, ax = plt.subplots(figsize=(width_inch, height_inch), dpi=300)

    # 学术蓝双色系
    color_220 = '#9ecae1'  
    color_920 = '#2171b5'  

    # 绘制两组柱状图
    bars_220 = ax.bar(pos_220, prob_220, width=bar_width, color=color_220, edgecolor='#1c4563', linewidth=0.5, label='220 MHz')
    bars_920 = ax.bar(pos_920, prob_920, width=bar_width, color=color_920, edgecolor='#082a4d', linewidth=0.5, label='920 MHz')

    # ========================================================
    # 6. 图表细节修饰（无 Title、极限压紧余白）
    # ========================================================
    ax.set_xlabel('Uncertainty Intervals', labelpad=2)
    ax.set_ylabel('Probability of Error > 10 dB (%)', labelpad=2)

    # 刻度及边缘紧凑对齐
    ax.set_xticks(x_indices)
    ax.set_xticklabels(active_labels)
    ax.set_xlim(0.4, len(active_labels) + 0.6)
    
    # 纵轴从 0 到 100%
    ax.set_ylim(0, 105) 
    ax.grid(axis='y', linestyle='--', linewidth=0.5, alpha=0.5)

    # 紧凑图例
    ax.legend(
        loc='upper left', 
        frameon=True, 
        edgecolor='#e0e0e0',
        fancybox=False,
        borderpad=0.3,       
        labelspacing=0.3     
    )

    # ========================================================
    # 7. 极致余白压缩与保存
    # ========================================================
    plt.subplots_adjust(left=0.12, right=0.97, top=0.96, bottom=0.14)

    svg_output = os.path.join(folderAddress, 'High_Error_Probability.svg')
    png_output = os.path.join(folderAddress, 'High_Error_Probability.png')
    
    save_props = {'dpi': 300, 'bbox_inches': 'tight', 'pad_inches': 0.012}
    
    if needSVG:
        plt.savefig(svg_output, format='svg', **save_props)
    if needPNG:
        plt.savefig(png_output, **save_props)
    
    plt.show()

    # ========================================================
    # 8. 在控制台打印具体的概率数值，便于论文撰写和检查
    # ========================================================
    print("\n--- 统计分析结果报告 ---")
    for i, label in enumerate(active_labels):
        print(f"区间 [{label}]:")
        print(f"  - 220 MHz 样本高误差概率: {prob_220[i]:.2f}%")
        print(f"  - 920 MHz 样本高误差概率: {prob_920[i]:.2f}%")


def plot_Quantile_Uncertainty_Error(folderAddress, needPNG, needSVG):
    # ========================================================
    # 1. 全局配置高保真纸张字体与科研规格（严格匹配你的标准）
    # ========================================================
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['font.sans-serif'] = ['Helvetica', 'Arial', 'DejaVu Sans']

    # 严格执行 7pt / 5pt 的紧凑科研字号，避免文字过大挤压图表空间
    plt.rcParams['font.size'] = 7
    plt.rcParams['axes.labelsize'] = 7
    plt.rcParams['axes.titlesize'] = 7
    plt.rcParams['xtick.labelsize'] = 7
    plt.rcParams['ytick.labelsize'] = 7
    plt.rcParams['legend.fontsize'] = 5 

    # 设定精确的物理画布尺寸 (mm 转换为 inch)
    width_inch = 80 / 25.4
    height_inch = 56.56 / 25.4

    # 核心设定：保证导出的 SVG 格式中文字是可编辑的、不会被转为线条（Path）
    plt.rcParams['svg.fonttype'] = 'none'

    # ========================================================
    # 2. 数据读取与并行处理逻辑（220MHz 与 920MHz）
    # ========================================================
    file_path_220 = os.path.join(folderAddress, "predict_RSS_M0_220.csv")
    file_path_920 = os.path.join(folderAddress, "predict_RSS_M0_920.csv")
    
    if not os.path.exists(file_path_220) or not os.path.exists(file_path_920):
        print(f"Error: Make sure both M0_220.csv and M0_920.csv exist in {folderAddress}")
        return

    # 读取并处理 220MHz 数据
    df_220 = pd.read_csv(file_path_220)
    df_220['Absolute_Error'] = (df_220['RSSI'] - df_220['Predicted_Value']).abs()

    # 读取并处理 920MHz 数据
    df_920 = pd.read_csv(file_path_920)
    df_920['Absolute_Error'] = (df_920['RSSI'] - df_920['Predicted_Value']).abs()

    # 定义统一的分位数区间标签
    # 后 20% (Low), 中间 60% (Mid), 前 20% (High)
    custom_labels = ['Bottom 20% (Low)', 'Middle 60% (Med)', 'Top 20% (High)']

    # ========================================================
    # 3. 动态分位数切分函数（核心修改）
    # ========================================================
    def segment_by_quantile(df):
        # 自动计算 20% 和 80% 的分位数边界值
        q20 = df['Uncertainty'].quantile(0.2)
        q80 = df['Uncertainty'].quantile(0.8)
        
        # 建立边界数组，包含极值保护
        bins = [-float('inf'), q20, q80, float('inf')]
        
        # 使用 pd.cut 进行动态硬切分
        df['Uncertainty_Group'] = pd.cut(
            df['Uncertainty'], 
            bins=bins, 
            labels=custom_labels, 
            include_lowest=True
        )
        return df

    df_220 = segment_by_quantile(df_220)
    df_920 = segment_by_quantile(df_920)

    # 提取各区间对应的数据列表
    raw_data_220 = [df_220[df_220['Uncertainty_Group'] == label]['Absolute_Error'].dropna().values for label in custom_labels]
    raw_data_920 = [df_920[df_920['Uncertainty_Group'] == label]['Absolute_Error'].dropna().values for label in custom_labels]

    # ========================================================
    # 4. 动态筛选有数据的区间（防止空样本占位，保持代码健壮性）
    # ========================================================
    active_labels = []
    filtered_data_220 = []
    filtered_data_920 = []

    for i, label in enumerate(custom_labels):
        has_220 = len(raw_data_220[i]) > 0
        has_920 = len(raw_data_920[i]) > 0
        
        if has_220 or has_920:
            active_labels.append(label)
            filtered_data_220.append(raw_data_220[i])
            filtered_data_920.append(raw_data_920[i])

    if not active_labels:
        print("Error: No valid data found after quantile split.")
        return

    # 动态生成并列坐标系
    x_indices = np.arange(1, len(active_labels) + 1)
    box_width = 0.25   
    gap = 0.04         

    pos_220 = x_indices - (box_width / 2 + gap / 2)
    pos_920 = x_indices + (box_width / 2 + gap / 2)

    # ========================================================
    # 5. 开始绘制纯 matplotlib 交错并列箱线图
    # ========================================================
    fig, ax = plt.subplots(figsize=(width_inch, height_inch), dpi=300)

    line_props = {
        'medianprops': {'color': '#333333', 'linewidth': 0.7},
        'boxprops': {'linewidth': 0.5},
        'whiskerprops': {'linewidth': 0.5, 'linestyle': '-'},
        'capprops': {'linewidth': 0.5},
        'flierprops': {
            'marker': 'o', 'markersize': 1.2, 'alpha': 0.18, 'markeredgecolor': 'none'
        }
    }

    box_220 = ax.boxplot(filtered_data_220, positions=pos_220, widths=box_width, patch_artist=True, **line_props)
    box_920 = ax.boxplot(filtered_data_920, positions=pos_920, widths=box_width, patch_artist=True, **line_props)

    # ========================================================
    # 6. 配色控制（220MHz: 浅蓝，920MHz: 深蓝）
    # ========================================================
    color_220 = '#9ecae1'  
    color_920 = '#2171b5'  
    
    for patch in box_220['boxes']:
        patch.set_facecolor(color_220)
        patch.set_edgecolor('#1c4563')

    for patch in box_920['boxes']:
        patch.set_facecolor(color_920)
        patch.set_edgecolor('#082a4d')

    for flier in box_220['fliers']: flier.set_markerfacecolor(color_220)
    for flier in box_920['fliers']: flier.set_markerfacecolor(color_920)

    # ========================================================
    # 7. 图表细节修饰与紧凑对齐（不要 Title 且极限压紧空间）
    # ========================================================
    ax.set_xlabel('Uncertainty Quantile Intervals', labelpad=2)   
    ax.set_ylabel('Absolute Error in dB', labelpad=2)     

    ax.set_xticks(x_indices)
    ax.set_xticklabels(active_labels)
    ax.set_xlim(0.4, len(active_labels) + 0.6)

    ax.grid(axis='y', linestyle='--', linewidth=0.5, alpha=0.5)

    # 严谨的论文级小图例
    ax.legend(
        [box_220['boxes'][0], box_920['boxes'][0]], 
        ['220 MHz', '920 MHz'], 
        loc='upper left', 
        frameon=True, 
        edgecolor='#e0e0e0',
        fancybox=False,
        borderpad=0.3,       
        labelspacing=0.3     
    )

    # ========================================================
    # 8. 极致余白压缩与精确画布保存
    # ========================================================
    # top=0.96 顶满上方，配合去除了 title，空间利用率达到最高
    plt.subplots_adjust(left=0.12, right=0.97, top=0.96, bottom=0.14)

    svg_output = os.path.join(folderAddress, 'Quantile_Uncertainty_Prediction_Error.svg')
    png_output = os.path.join(folderAddress, 'Quantile_Uncertainty_Prediction_Error.png')
    
    save_props = {'dpi': 300, 'bbox_inches': 'tight', 'pad_inches': 0.012}
    
    if needSVG:
        plt.savefig(svg_output, format='svg', **save_props)
    if needPNG:
        plt.savefig(png_output, **save_props)
    
    plt.show()

    # ========================================================
    # 9. 打印每个频段在分位数区间下的实际样本量（控制台审查）
    # ========================================================
    print("\n--- [220 MHz] 分位数区间样本数量统计 ---")
    print(df_220['Uncertainty_Group'].value_counts().sort_index())
    print("\n--- [920 MHz] 分位数区间样本数量统计 ---")
    print(df_920['Uncertainty_Group'].value_counts().sort_index())


def plot_Quantile_High_Error_Rate(folderAddress, rho, needPNG, needSVG):
    """
    统计不同频段在 Uncertainty 分位数区间内，Absolute_Error 超过 rho 的样本比例。
    
    参数:
    - folderAddress: 数据文件夹路径
    - rho: 绝对误差阈值 (dB)，例如 10 或 6
    - needPNG: 是否保存 PNG
    - needSVG: 是否保存 SVG
    """
    # ========================================================
    # 1. 全局配置高保真纸张字体与科研规格（严格匹配标准）
    # ========================================================
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['font.sans-serif'] = ['Helvetica', 'Arial', 'DejaVu Sans']

    # 严格执行 7pt / 5pt 的紧凑科研字号，避免文字过大挤压空间
    plt.rcParams['font.size'] = 7
    plt.rcParams['axes.labelsize'] = 7
    plt.rcParams['axes.titlesize'] = 7
    plt.rcParams['xtick.labelsize'] = 7
    plt.rcParams['ytick.labelsize'] = 7
    plt.rcParams['legend.fontsize'] = 5 

    # 设定精确的物理画布尺寸 (mm 转换为 inch)
    width_inch = 80 / 25.4
    height_inch = 56.56 / 25.4
    plt.rcParams['svg.fonttype'] = 'none'

    # ========================================================
    # 2. 数据读取与并行处理逻辑（220MHz 与 920MHz）
    # ========================================================
    file_path_220 = os.path.join(folderAddress, "predict_RSS_M0_220_10.csv")
    file_path_920 = os.path.join(folderAddress, "predict_RSS_M0_920_10.csv")
    
    if not os.path.exists(file_path_220) or not os.path.exists(file_path_920):
        print(f"Error: Make sure both M0_220.csv and M0_920.csv exist in {folderAddress}")
        return

    # 读取并处理 220MHz 数据
    df_220 = pd.read_csv(file_path_220)
    df_220['Absolute_Error'] = (df_220['RSSI'] - df_220['Predicted_Value']).abs()

    # 读取并处理 920MHz 数据
    df_920 = pd.read_csv(file_path_920)
    df_920['Absolute_Error'] = (df_920['RSSI'] - df_920['Predicted_Value']).abs()

    # 统一定义分位数区间标签
    custom_labels = ['Bottom 20% (Low)', 'Middle 60% (Med)', 'Top 20% (High)']

    # ========================================================
    # 3. 动态分位数硬切分与高误率统计
    # ========================================================
    def compute_high_error_rates(df):
        # 自动获取当前频段数据的 20% 和 80% 分位数边界值
        q20 = df['Uncertainty'].quantile(0.2)
        q80 = df['Uncertainty'].quantile(0.8)
        bins = [-float('inf'), q20, q80, float('inf')]
        
        df['Uncertainty_Group'] = pd.cut(df['Uncertainty'], bins=bins, labels=custom_labels, include_lowest=True)
        
        rates = []
        counts = []
        for label in custom_labels:
            sub_df = df[df['Uncertainty_Group'] == label]
            total_samples = len(sub_df)
            counts.append(total_samples)
            
            if total_samples > 0:
                # 统计 Absolute_Error 严格大于 rho 的样本比例
                high_error_count = len(sub_df[sub_df['Absolute_Error'] > rho])
                rates.append((high_error_count / total_samples) * 100)  # 转换为百分比
            else:
                rates.append(0.0)
        return rates, counts

    rates_220, counts_220 = compute_high_error_rates(df_220)
    rates_920, counts_920 = compute_high_error_rates(df_920)

    # ========================================================
    # 4. 动态过滤无效空置区间
    # ========================================================
    active_labels = []
    filtered_rates_220 = []
    filtered_rates_920 = []

    for i, label in enumerate(custom_labels):
        # 只要该分位数区间内含有有效样本，即保留该列坐标
        if counts_220[i] > 0 or counts_920[i] > 0:
            active_labels.append(label)
            filtered_rates_220.append(rates_220[i])
            filtered_rates_920.append(rates_920[i])

    if not active_labels:
        print("Error: No data available to plot.")
        return

    # 计算并列柱状图横坐标位置
    x_indices = np.arange(1, len(active_labels) + 1)
    bar_width = 0.25   # 单根柱子物理宽度
    gap = 0.02         # 两根柱子间微小间隙

    pos_220 = x_indices - (bar_width / 2 + gap / 2)
    pos_920 = x_indices + (bar_width / 2 + gap / 2)

    # ========================================================
    # 5. 开始绘制纯 matplotlib 柱状图
    # ========================================================
    fig, ax = plt.subplots(figsize=(width_inch, height_inch), dpi=300)

    # 双色高保真学术蓝
    color_220 = '#9ecae1'  
    color_920 = '#2171b5'  

    # 渲染并列柱体
    bars_220 = ax.bar(pos_220, filtered_rates_220, width=bar_width, color=color_220, edgecolor='#1c4563', linewidth=0.5, label='220 MHz')
    bars_920 = ax.bar(pos_920, filtered_rates_920, width=bar_width, color=color_920, edgecolor='#082a4d', linewidth=0.5, label='920 MHz')

    # ========================================================
    # 6. 图表细节修饰（无 Title 且极限压紧空间）
    # ========================================================
    ax.set_xlabel('Uncertainty Quantile Intervals', labelpad=2)
    # 动态将 rho 写入纵轴标签，增强论文字符规范性
    ax.set_ylabel(f'Ratio of Error > {rho} dB (%)', labelpad=2)

    # 精确对齐横轴刻度标签
    ax.set_xticks(x_indices)
    ax.set_xticklabels(active_labels)
    ax.set_xlim(0.4, len(active_labels) + 0.6)
    
    # 纵轴留出合适冗余防遮挡图例
    max_rate = max(max(filtered_rates_220), max(filtered_rates_920))
    ax.set_ylim(0, min(105, max_rate + 20) if max_rate > 0 else 105)
    
    # 细化横向网格参考线
    ax.grid(axis='y', linestyle='--', linewidth=0.5, alpha=0.5)

    # 紧凑图例设计
    ax.legend(
        loc='upper left', 
        frameon=True, 
        edgecolor='#e0e0e0',
        fancybox=False,
        borderpad=0.3,       
        labelspacing=0.3     
    )

    # ========================================================
    # 7. 极致余白压缩与精确保存
    # ========================================================
    # top=0.96 完全吃掉 Title 释放的全部顶部空间，紧凑度最大化
    plt.subplots_adjust(left=0.12, right=0.97, top=0.96, bottom=0.14)

    filename = f'Quantile_High_Error_Rate_rho_{rho}'
    svg_output = os.path.join(folderAddress, f'{filename}.svg')
    png_output = os.path.join(folderAddress, f'{filename}.png')
    
    save_props = {'dpi': 300, 'bbox_inches': 'tight', 'pad_inches': 0.012}
    
    if needSVG:
        plt.savefig(svg_output, format='svg', **save_props)
    if needPNG:
        plt.savefig(png_output, **save_props)
    
    plt.show()

    # ========================================================
    # 8. 控制台打印数值报告（便于写论文直接复制数据）
    # ========================================================
    print(f"\n--- 统计报告：误差超过 {rho} dB 的样本比例 ---")
    for i, label in enumerate(active_labels):
        print(f"区间 [{label}]:")
        print(f"  - 220 MHz 占比: {filtered_rates_220[i]:.2f}% (区间总数: {counts_220[i]})")
        print(f"  - 920 MHz 占比: {filtered_rates_920[i]:.2f}% (区间总数: {counts_920[i]})")


def plot_Top_Quantile_High_Error_Trend(folderAddress, rho, needPNG, needSVG):
    """
    统计 920MHz 频段在不同 Top 不确定性累积区间内（Top 10% - 100%），
    Absolute_Error 超过 rho 的样本比例趋势。
    
    参数:
    - folderAddress: 数据文件夹路径
    - rho: 绝对误差阈值 (dB)
    - needPNG: 是否保存 PNG
    - needSVG: 是否保存 SVG
    """
    # ========================================================
    # 1. 全局配置高保真纸张字体与科研规格（严格匹配你的标准）
    # ========================================================
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['font.sans-serif'] = ['Helvetica', 'Arial', 'DejaVu Sans']

    # 严格执行 7pt / 5pt 的紧凑科研字号，避免文字过大挤压空间
    plt.rcParams['font.size'] = 7
    plt.rcParams['axes.labelsize'] = 7
    plt.rcParams['axes.titlesize'] = 7
    plt.rcParams['xtick.labelsize'] = 7
    plt.rcParams['ytick.labelsize'] = 7
    plt.rcParams['legend.fontsize'] = 5 

    # 设定精确的物理画布尺寸 (mm 转换为 inch)
    width_inch = 80 / 25.4
    height_inch = 56.56 / 25.4
    plt.rcParams['svg.fonttype'] = 'none'

    # ========================================================
    # 2. 数据读取与处理逻辑（仅读取 920MHz 数据）
    # ========================================================
    file_path_920 = os.path.join(folderAddress, "predict_RSS_exp23.csv")
    
    if not os.path.exists(file_path_920):
        print(f"Error: File not found at {file_path_920}")
        return

    # 读取并计算绝对误差
    df = pd.read_csv(file_path_920)
    df['Absolute_Error'] = (df['RSSI'] - df['Predicted_Value']).abs()

    # ========================================================
    # 3. 核心统计逻辑：计算 Top 10% 到 Top 100% 的累积高误率
    # ========================================================
    # 定义 Top 梯队百分比：10%, 20%, 30%, ..., 100%
    top_percentages = np.arange(10, 110, 10)
    rates_920 = []
    counts_920 = []
    x_labels = [f'Top {p}%' for p in top_percentages]

    for p in top_percentages:
        # 计算当前分位数阈值。注意：Uncertainty 越大代表不确定性越高
        # Top 10% 意味着不确定性处于前 10% 的高风险样本（即大于 90% 分位数的样本）
        quantile_threshold = df['Uncertainty'].quantile(1.0 - (p / 100.0))
        
        # 筛选出 Uncertainty 大于等于该阈值的子集
        sub_df = df[df['Uncertainty'] >= quantile_threshold]
        total_samples = len(sub_df)
        counts_920.append(total_samples)
        
        if total_samples > 0:
            high_error_count = len(sub_df[sub_df['Absolute_Error'] > rho])
            rates_920.append((high_error_count / total_samples) * 100)
        else:
            rates_920.append(0.0)

    # ========================================================
    # 4. 开始绘制纯 matplotlib 趋势折线图
    # ========================================================
    fig, ax = plt.subplots(figsize=(width_inch, height_inch), dpi=300)

    # 精选学术沉稳深蓝系，配置精致微型标记
    color_line = '#2171b5'  # Royal Blue
    
    ax.plot(
        x_labels, 
        rates_920, 
        color=color_line, 
        linestyle='-', 
        linewidth=1.0, 
        marker='o', 
        markersize=2.5, 
        markerfacecolor=color_line, 
        markeredgecolor='white', 
        markeredgewidth=0.4,
        label='920 MHz'
    )

    # ========================================================
    # 5. 图表细节修饰（无 Title 且极限压紧空间）
    # ========================================================
    ax.set_xlabel('Uncertainty Thresholds (Cumulative)', labelpad=2)
    ax.set_ylabel(f'Ratio of Error > {rho} dB (%)', labelpad=2)

    # 旋转横轴长文本标签以防挤压，紧凑对齐
    ax.set_xticklabels(x_labels, rotation=30, ha='right')
    
    # 优化 X 轴两端留白，防止首尾数据点贴墙
    ax.set_xlim(-0.4, len(x_labels) - 0.6)
    
    # 纵轴留出合适冗余防遮挡图例
    max_rate = max(rates_920) if rates_920 else 0
    ax.set_ylim(0, min(105, max_rate + 20) if max_rate > 0 else 105)
    
    # 细化横向网格参考线
    ax.grid(axis='both', linestyle='--', linewidth=0.5, alpha=0.4)

    # 紧凑图例设计
    ax.legend(
        loc='upper right', 
        frameon=True, 
        edgecolor='#e0e0e0',
        fancybox=False,
        borderpad=0.3,       
        labelspacing=0.3     
    )

    # ========================================================
    # 6. 极致余白压缩与精确保存
    # ========================================================
    # bottom=0.18 稍微为旋转后的 X 轴标签留出呼吸空间，top=0.96 顶满上方
    plt.subplots_adjust(left=0.12, right=0.97, top=0.96, bottom=0.18)

    filename = f'Top_Quantile_High_Error_Trend_rho_{rho}'
    svg_output = os.path.join(folderAddress, f'{filename}.svg')
    png_output = os.path.join(folderAddress, f'{filename}.png')
    
    save_props = {'dpi': 300, 'bbox_inches': 'tight', 'pad_inches': 0.012}
    
    if needSVG:
        plt.savefig(svg_output, format='svg', **save_props)
    if needPNG:
        plt.savefig(png_output, **save_props)
    
    plt.show()

    # ========================================================
    # 7. 控制台打印数值报告（便于直接复制进正文或表格）
    # ========================================================
    print(f"\n--- 统计报告：920MHz 累积不确定性梯队 (Error > {rho} dB) ---")
    for i, label in enumerate(x_labels):
        print(f"区间 [{label}]: 占比 = {rates_920[i]:.2f}% (该累积集总样本数: {counts_920[i]})")


def plot_Uncertainty_High_Error_Distribution(folderAddress, needPNG, needSVG):
    """
    针对 920MHz 频段，统计 Top 10% 最大误差样本在不同不确定性梯队（按从大到小每10%切分）中的分布比例。
    """
    # ========================================================
    # 1. 全局配置高保真纸张字体与科研规格（严格匹配你的标准）
    # ========================================================
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['font.sans-serif'] = ['Helvetica', 'Arial', 'DejaVu Sans']

    # 严格执行 7pt / 5pt 的紧凑科研字号，避免文字过大挤压空间
    plt.rcParams['font.size'] = 7
    plt.rcParams['axes.labelsize'] = 7
    plt.rcParams['axes.titlesize'] = 7
    plt.rcParams['xtick.labelsize'] = 7
    plt.rcParams['ytick.labelsize'] = 7
    plt.rcParams['legend.fontsize'] = 5 

    # 设定精确的物理画布尺寸 (mm 转换为 inch)
    width_inch = 80 / 25.4
    height_inch = 56.56 / 25.4
    plt.rcParams['svg.fonttype'] = 'none'

    # ========================================================
    # 2. 数据读取与处理逻辑（读取 920MHz 数据）
    # ========================================================
    file_path_920 = os.path.join(folderAddress, "predict_RSS_exp23.csv")
    
    if not os.path.exists(file_path_920):
        print(f"Error: File not found at {file_path_920}")
        return

    # 读取并计算绝对误差
    df = pd.read_csv(file_path_920)
    df['Absolute_Error'] = (df['RSSI'] - df['Predicted_Value']).abs()

    # ========================================================
    # 3. 核心数学统计（完全对应你的3个功能需求）
    # ========================================================
    # 功能 (1)：找到全体数据中 Top 10% 的最大误差阈值 (即 90% 分位数边界)
    error_threshold = df['Absolute_Error'].quantile(0.90)

    # 功能 (2)：统计大于 10% Top 误差的总样本数
    high_error_df = df[df['Absolute_Error'] > error_threshold]
    total_high_error_count = len(high_error_df)
    
    if total_high_error_count == 0:
        print("Error: Total high error count is 0. Check your dataset variance.")
        return

    # 功能 (3)：将【Uncertainty】从大到小降序排列
    df_sorted = df.sort_values(by='Uncertainty', ascending=False).reset_index(drop=True)
    total_samples = len(df_sorted)

    # 准备进行每 10% 样本量的分桶统计
    ratios = []
    x_labels = [f'{i*10}-{(i+1)*10}%' for i in range(10)]
    
    # 动态计算每 10% 区间对应的行索引边界（精确到单条数据，防止四舍五入丢样本）
    for i in range(10):
        start_idx = int(np.floor(i * 0.1 * total_samples))
        end_idx = int(np.floor((i + 1) * 0.1 * total_samples)) if i < 9 else total_samples
        
        # 截取当前不确定性梯队的子集
        sub_chunk = df_sorted.iloc[start_idx:end_idx]
        
        # 统计当前梯队中绝对误差大于 Top 10% 阈值的样本数
        sub_high_error_count = len(sub_chunk[sub_chunk['Absolute_Error'] > error_threshold])
        
        # 计算该数占“大于10%top误差总数”的比例
        chunk_ratio = (sub_high_error_count / total_high_error_count) * 100
        ratios.append(chunk_ratio)

    # ========================================================
    # 4. 开始绘制纯 matplotlib 紧凑型分布柱状图
    # ========================================================
    fig, ax = plt.subplots(figsize=(width_inch, height_inch), dpi=300)

    # 选用 920MHz 专属的沉稳学术深蓝
    color_bar = '#2171b5'  
    
    x_indices = np.arange(len(x_labels))
    bar_width = 0.6  # 单单根柱子，稍微放宽增强视觉可读性

    bars = ax.bar(
        x_indices, 
        ratios, 
        width=bar_width, 
        color=color_bar, 
        edgecolor='#082a4d', 
        linewidth=0.5, 
        label='920 MHz'
    )

    # ========================================================
    # 5. 图表细节修饰（无 Title 且极限压紧空间）
    # ========================================================
    ax.set_xlabel('Uncertainty Strata (From High to Low)', labelpad=2)
    ax.set_ylabel('Percentage of Top 10% Errors (%)', labelpad=2)

    # 旋转 X 轴标签以防微型图表重叠， ha='right' 精确右对齐
    ax.set_xticks(x_indices)
    ax.set_xticklabels(x_labels, rotation=30, ha='right')
    
    # 紧凑优化边缘留白
    ax.set_xlim(-0.5, len(x_labels) - 0.5)
    
    # 动态增高 Y 轴上限，防止柱子触顶压迫左上角图例
    max_ratio = max(ratios) if ratios else 0
    ax.set_ylim(0, min(105, max_ratio + 12) if max_ratio > 0 else 105)
    
    # 细化网格参考线
    ax.grid(axis='y', linestyle='--', linewidth=0.5, alpha=0.5)

    # 极其小巧的科研图例
    ax.legend(
        loc='upper right', 
        frameon=True, 
        edgecolor='#e0e0e0',
        fancybox=False,
        borderpad=0.3,       
        labelspacing=0.3     
    )

    # ========================================================
    # 6. 极致余白压缩与精确画布保存
    # ========================================================
    # bottom=0.18 完美预留给旋转后的不确定性阶梯文本，top=0.96 顶满上方
    plt.subplots_adjust(left=0.12, right=0.97, top=0.96, bottom=0.18)

    filename = 'Uncertainty_Top10_Error_Distribution'
    svg_output = os.path.join(folderAddress, f'{filename}.svg')
    png_output = os.path.join(folderAddress, f'{filename}.png')
    
    save_props = {'dpi': 300, 'bbox_inches': 'tight', 'pad_inches': 0.012}
    
    if needSVG:
        plt.savefig(svg_output, format='svg', **save_props)
    if needPNG:
        plt.savefig(png_output, **save_props)
    
    plt.show()

    # ========================================================
    # 7. 控制台输出审查报告（撰写论文时可直接引用这些核心结论）
    # ========================================================
    print(f"\n================ 统计分析审查报告 ================")
    print(f"1. 整体样本总量: {total_samples} 条")
    print(f"2. 全局 Top 10% 最大绝对误差阈值 (E_top10): {error_threshold:.4f} dB")
    print(f"3. 绝对误差严格大于该阈值的总样本数 (N_total_high): {total_high_error_count} 条")
    print(f"4. 大误差样本在【不确定性降序阶梯】中的分布比例:")
    for i, label in enumerate(x_labels):
        actual_count = int(round((ratios[i] / 100) * total_high_error_count))
        print(f"   梯队 [{label}]: 占比 = {ratios[i]:.2f}% (含高误差样本数: {actual_count} 条)")
    print(f"==================================================")


def split_dataset_by_uncertainty(folderAddress, fileName="predict_RSS.csv"):
    """
    针对指定的 CSV 数据集，按照 Uncertainty 的三种模式（高、低、随机）
    切分出前 10% 作为 fine-tuning (ft) 集，剩余 90% 作为 test 集。
    
    参数:
    - folderAddress: 数据集所在的文件夹路径
    - fileName: 数据集文件名，默认为 'predict_RSS.csv'
    """
    # ========================================================
    # 1. 读取原始数据并进行基础校验
    # ========================================================
    file_path = os.path.join(folderAddress, fileName)
    if not os.path.exists(file_path):
        print(f"Error: File not found at {file_path}")
        return

    df = pd.read_csv(file_path)
    total_samples = len(df)
    
    if total_samples == 0:
        print("Error: The input CSV file is empty.")
        return

    # 精确计算 10% 样本量的截断行索引位置（使用 floor 确保索引安全）
    split_idx = int(np.floor(0.1 * total_samples))
    if split_idx == 0:
        split_idx = 1 # 确保数据量极小时至少分出 1 行
        
    print(f"--- 数据集基础信息 ---")
    print(f"总样本数: {total_samples} 行")
    print(f"切分规格: 前 10% = {split_idx} 行, 剩余 90% = {total_samples - split_idx} 行\n")

    # ========================================================
    # 功能 (1)：高不确定性切分（Uncertainty 从大到小降序排列）
    # ========================================================
    df_high_sorted = df.sort_values(by='Uncertainty', ascending=False).reset_index(drop=True)
    
    high_ft_10p = df_high_sorted.iloc[:split_idx]
    high_test_10p = df_high_sorted.iloc[split_idx:]
    
    high_ft_10p.to_csv(os.path.join(folderAddress, "hightUncertainty_ft_10p.csv"), index=False)
    high_test_10p.to_csv(os.path.join(folderAddress, "hightUncertainty_test_10p.csv"), index=False)
    print("✓ 成功导出: hightUncertainty_ft_10p.csv & hightUncertainty_test_10p.csv")

    # ========================================================
    # 功能 (2)：低不确定性切分（Uncertainty 从小到大升序排列）
    # ========================================================
    df_low_sorted = df.sort_values(by='Uncertainty', ascending=True).reset_index(drop=True)
    
    low_ft_10p = df_low_sorted.iloc[:split_idx]
    low_test_10p = df_low_sorted.iloc[split_idx:]
    
    low_ft_10p.to_csv(os.path.join(folderAddress, "lowUncertainty_ft_10p.csv"), index=False)
    low_test_10p.to_csv(os.path.join(folderAddress, "lowUncertainty_test_10p.csv"), index=False)
    print("✓ 成功导出: lowUncertainty_ft_10p.csv & lowUncertainty_test_10p.csv")

    # ========================================================
    # 功能 (3)：随机切分（不进行任何物理排列，完全随机抽样）
    # ========================================================
    # 设定 random_state 确保实验的可重复性（若需要每次运行都完全随机，可将其删去或设为 None）
    df_random_shuffled = df.sample(frac=1.0, random_state=42).reset_index(drop=True)
    
    random_ft_10p = df_random_shuffled.iloc[:split_idx]
    random_test_10p = df_random_shuffled.iloc[split_idx:]
    
    random_ft_10p.to_csv(os.path.join(folderAddress, "randomUncertainty_ft_10p.csv"), index=False)
    random_test_10p.to_csv(os.path.join(folderAddress, "randomUncertainty_test_10p.csv"), index=False)
    print("✓ 成功导出: randomUncertainty_ft_10p.csv & randomUncertainty_test_10p.csv")
    
    print("\n================ 数据切分任务全部圆满完成 ================")



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
    folderAddress = "/Users/zhaoou/Desktop/課題1_TL拡張/TL検証/1_Uncertainty_vs_Error/unseen1"

    #plot_MAE_CDF(outputFileAddress, targetFileAddress, referenceFileAddress, needPNG=True, needSVG=False)
    #plot_dynamic_clustering_high_error_heatmap(outputFileAddress, targetFileAddress, fix_longitude, fix_latitude, mae_threshold=4.79, n_clusters=3, needPNG=True, needSVG=False)
    #plot_vertical_stacked_environment_boxplots(outputFileAddress, targetFileAddress, fix_longitude, fix_latitude, needPNG=True, needSVG=False)
    #plot_Uncertainty_Prediction_Error(folderAddress, needPNG=True, needSVG=True)
    #plot_High_Error_Probability(folderAddress, needPNG=True, needSVG=True)
    #plot_Quantile_Uncertainty_Error(folderAddress, needPNG=True, needSVG=True)
    #plot_Quantile_High_Error_Rate(folderAddress, 10, needPNG=False, needSVG=False)
    #plot_Top_Quantile_High_Error_Trend(folderAddress, 10, needPNG=False, needSVG=False)
    #plot_Uncertainty_High_Error_Distribution(folderAddress, needPNG=False, needSVG=False)
    split_dataset_by_uncertainty(folderAddress, fileName="predict_RSS.csv")
    return





if __name__ == "__main__":
    import sys,os
    main() 