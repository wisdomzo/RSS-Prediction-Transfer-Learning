import my_plot_figure
import subFun_TL
import subFun
import subprocess
import sys
import os
import pickle
import lzma
from matplotlib import rcParams
import numpy as np
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from tensorflow.keras.utils import plot_model

def show_diff_model_performance():
    ml_history_files = subFun.list_history_TL_Predict_files()
    if not ml_history_files:
        print("没有找到以'history_model_from_'开头的文件。")
        sys.exit()
    else:
        user_input = subFun.get_user_selection(ml_history_files)
        selected_name = [ml_history_files[i - 1] for i in user_input]
        print("---> 评价各种模型")
        # 初始化四个空字典
        sorted_data_linear_dict = {}
        cdf_linear_dict = {}
        sorted_data_DL_dict = {}
        cdf_DL_dict = {}
        for count, name in enumerate(selected_name):
            if "TL_model" in name:
                sorted_data_linear_dict[name], cdf_linear_dict[name], sorted_data_DL_dict[name], cdf_DL_dict[name] = subFun_TL.show_TL_model(name)
            if "history_model" in name:
                sorted_data_linear_dict[name], cdf_linear_dict[name], sorted_data_DL_dict[name], cdf_DL_dict[name] = subFun_TL.show_history_model(name)
            if "Predict_model" in name:
                _, sorted_data_DL_dict[name], cdf_DL_dict[name] = subFun_TL.show_Predict_model(name)
        print("---> 绘制对比图")
        # 全局设置
        fontsize = 7
        linewidth = 0.5
        figsize_mm = (80, 56.56)
        default_path = 'diff_CDF_plot_429.svg'
        default_path_CCDF = 'diff_CCDF_plot.svg'
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
        # 创建画布 CDF
        fig, ax = plt.subplots(figsize=(figsize_mm[0] / 25.4, figsize_mm[1] / 25.4))
        # 绘制曲线'-'（实线）, '--'（虚线）, ':'（点线）, '-.'（点划线）
        for count, name in enumerate(selected_name):
            try:
                sorted_data_linear_dict[name]
            except Exception as e:
                print(f"跳过错误: {e}")
            else:
                ax.plot(sorted_data_linear_dict[name], cdf_linear_dict[name],
                        label=str(count + 1) + ' (linear)',
                        linestyle='--',
                        # color = 'C0',
                        )
            try:
                sorted_data_DL_dict[name]
            except Exception as e:
                print(f"跳过错误: {e}")
            else:
                ax.plot(sorted_data_DL_dict[name], cdf_DL_dict[name],
                        label=str(count + 1) + ' (DL)',
                        linestyle='-',
                        # color = 'C1',
                        )
        # 设置 x 轴的范围（例如：0 到 100）
        max_x = input("请输入x的最大值: ")
        ax.set_xlim([0, float(max_x)])  # 替换 xmin 和 xmax 为你想要的范围
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
        # 关闭画布
        plt.close()

    return


# region
def analyze_diff_model_performance():
    ml_history_TL_files = subFun.list_history_TL_files()
    if not ml_history_TL_files:
        print("没有找到文件。")
        sys.exit()
    else:
        user_input = subFun.get_user_selection(ml_history_TL_files)
        selected_name = [ml_history_TL_files[i - 1] for i in user_input]
        print("---> 分析各种模型")
        for count, name in enumerate(selected_name):
            with lzma.open(name, 'rb') as saveFile:
                dataStrick = pickle.load(saveFile)
            if "TL_model" in name:
                predictRSSI_TL = dataStrick['predictRSSI_TL']
                # 使用你的模型列表进行分析
                analyze_models(predictRSSI_TL, model_name_prefix="RSSI_TL")
            else:
                print("<UNK>")
            print("模型 " + name + " 处理完毕。")

    return
# endregion




def display_readme(file_path="README.md"):
    """
    读取并显示 README 文件的内容

    参数:
        file_path (str): README 文件的路径，默认为 "README.md"

    返回:
        str: README 文件的内容（如果文件存在）
    """
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()
            print(content)  # 打印文件内容
            return content  # 也可以返回内容以便进一步处理
    except FileNotFoundError:
        print(f"错误：文件 '{file_path}' 未找到！")
        return None
    except Exception as e:
        print(f"读取文件时出错: {e}")
        return None



