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
        print("No files beginning with 'history_model_from_' were found.")
        sys.exit()
    else:
        user_input = subFun.get_user_selection(ml_history_files)
        selected_name = [ml_history_files[i - 1] for i in user_input]
        print("---> Evaluating models")
        # Initialize four empty dictionaries.
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
        print("---> Plotting comparison")
        # Global plot settings.
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
        # Create the CDF figure.
        fig, ax = plt.subplots(figsize=(figsize_mm[0] / 25.4, figsize_mm[1] / 25.4))
        # Plot curves using '-', '--', ':', and '-.' line styles.
        for count, name in enumerate(selected_name):
            try:
                sorted_data_linear_dict[name]
            except Exception as e:
                print(f"Skipping due to error: {e}")
            else:
                ax.plot(sorted_data_linear_dict[name], cdf_linear_dict[name],
                        label=str(count + 1) + ' (linear)',
                        linestyle='--',
                        # color = 'C0',
                        )
            try:
                sorted_data_DL_dict[name]
            except Exception as e:
                print(f"Skipping due to error: {e}")
            else:
                ax.plot(sorted_data_DL_dict[name], cdf_DL_dict[name],
                        label=str(count + 1) + ' (DL)',
                        linestyle='-',
                        # color = 'C1',
                        )
        # Set the x-axis range, for example from 0 to 100.
        max_x = input("Enter the maximum x-axis value: ")
        ax.set_xlim([0, float(max_x)])  # Replace xmin and xmax with the desired range.
        # Configure chart elements.
        ax.set_xlabel('Error Between Predicted vs Actual RSS in dB')
        ax.set_ylabel('CDF')
        ax.grid(True)
        ax.tick_params(axis='both', width=linewidth)
        # Configure the legend.
        legend = ax.legend(loc='lower right')
        legend.get_frame().set_linewidth(linewidth)
        plt.tight_layout()
        # Ask the user whether to save the figure.
        while True:
            save = input(f"Save as an SVG file? [y/n] (default path: {default_path}): ").strip().lower()
            if save == 'y':
                plt.savefig(default_path,
                            format='svg',
                            dpi=300,
                            bbox_inches='tight',
                            )
                print(f"Saved to: {default_path}")
                break
            elif save == 'n':
                print("File was not saved.")
                break
            else:
                print("Enter y or n.")
        # Display the chart.
        plt.show()
        # Close the figure.
        plt.close()

    return


# region
def analyze_diff_model_performance():
    ml_history_TL_files = subFun.list_history_TL_files()
    if not ml_history_TL_files:
        print("No files were found.")
        sys.exit()
    else:
        user_input = subFun.get_user_selection(ml_history_TL_files)
        selected_name = [ml_history_TL_files[i - 1] for i in user_input]
        print("---> Analyzing models")
        for count, name in enumerate(selected_name):
            with lzma.open(name, 'rb') as saveFile:
                dataStrick = pickle.load(saveFile)
            if "TL_model" in name:
                predictRSSI_TL = dataStrick['predictRSSI_TL']
                # Analyze the selected model list.
                analyze_models(predictRSSI_TL, model_name_prefix="RSSI_TL")
            else:
                print("<UNK>")
            print("Model " + name + " processed successfully.")

    return
# endregion




def display_readme(file_path="README.md"):
    """
    Read and display the contents of a README file.

    Args:
        file_path (str): Path to the README file. Defaults to "README.md".

    Returns:
        str: README contents if the file exists; otherwise, None.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()
            print(content)  # Display the file contents.
            return content  # Return the contents for further processing.
    except FileNotFoundError:
        print(f"Error: File '{file_path}' was not found.")
        return None
    except Exception as e:
        print(f"Error reading file: {e}")
        return None


