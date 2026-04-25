import matplotlib.pyplot as plt
import numpy as np
from matplotlib import rcParams


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


def compute_cdf(data):
    # 对数据进行排序
    sorted_data = np.sort(data, axis=0)

    # 生成CDF的y值
    cdf = np.arange(1, len(sorted_data) + 1) / len(sorted_data)

    return sorted_data, cdf


def plot_and_confirm_cdf(sorted_data_linear, cdf_linear, sorted_data_DL, cdf_DL,
                         default_path='cdf_plot.svg', figsize_mm=(80, 56.56),
                         fontsize=7, linewidth=0.5):
    """
    绘制CDF对比图并交互式询问是否保存

    参数:
        sorted_data_linear (array): 线性预测误差排序数据
        cdf_linear (array): 线性预测的CDF值
        sorted_data_DL (array): DL预测误差排序数据
        cdf_DL (array): DL预测的CDF值
        default_path (str): 默认保存路径
        figsize_mm (tuple): 图片尺寸（毫米）
        fontsize (int): 字体大小（pt）
        linewidth (float): 所有线条宽度（pt）
    """
    # 全局设置
    rcParams.update({
        'font.family': 'sans-serif',
        'font.sans-serif': ['Helvetica', 'Arial', 'DejaVu Sans'],
        'font.size': fontsize,
        'lines.linewidth': linewidth,
        'axes.linewidth': linewidth,
        'xtick.major.width': linewidth,
        'ytick.major.width': linewidth,
        'grid.linewidth': linewidth,
        'patch.linewidth': linewidth,
    })
    # 创建画布
    fig, ax = plt.subplots(figsize=(figsize_mm[0] / 25.4, figsize_mm[1] / 25.4))
    # 绘制曲线'-'（实线）, '--'（虚线）, ':'（点线）, '-.'（点划线）
    ax.plot(sorted_data_linear, cdf_linear,
            label='Linear Prediction (median)',
            linestyle = '--',
            #color = 'C0',
            )
    ax.plot(sorted_data_DL, cdf_DL,
            label='DL-based Prediction (median)',
            linestyle = '-',
            #color = 'C1',
            )
    # 设置 x 轴的范围（例如：0 到 100）
    #ax.set_xlim([xmin, xmax])  # 替换 xmin 和 xmax 为你想要的范围
    # 设置图表元素
    ax.set_xlabel('Error Between Predicted vs Actual RSS in dB')
    ax.set_ylabel('CDF')
    ax.grid(True)
    ax.tick_params(axis='both', width=linewidth)

    # 设置图例
    legend = ax.legend(loc='lower right')
    legend.get_frame().set_linewidth(linewidth)

    plt.tight_layout()

    # 用户交互保存确认
    while True:
        save = input(f"是否保存为SVG文件？ [y/n] (默认路径: {default_path}): ").strip().lower()

        if save == 'y':
            plt.savefig(default_path,
                        format='svg',
                        dpi=300,
                        bbox_inches='tight',
                        )
            print(f"已保存至: {default_path}")
            break
        elif save == 'n':
            print("未保存文件")
            break
        else:
            print("请输入 y 或 n")

    # 显示图表
    plt.show()

    plt.close()