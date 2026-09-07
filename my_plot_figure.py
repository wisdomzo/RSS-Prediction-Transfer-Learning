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

    sorted_data = np.sort(data, axis=0)


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

        plt.ion()



        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')


        sc = ax.scatter(args[0], args[1], args[2], c='b', marker='.', linestyle='')


        ax.set_xlabel('X Label')
        ax.set_ylabel('Y Label')
        ax.set_zlabel('Z Label')


        plt.show()


    return


def plot_Four_Scenarios_Error_CDF(folderAddress, needPNG, needSVG):
    """Read the configured scenario CSV files, calculate absolute errors, and plot a publication-quality comparison CDF."""
    # ========================================================

    # ========================================================
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['font.sans-serif'] = ['Helvetica', 'Arial', 'DejaVu Sans']


    plt.rcParams['font.size'] = 7
    plt.rcParams['axes.labelsize'] = 7
    plt.rcParams['axes.titlesize'] = 7
    plt.rcParams['xtick.labelsize'] = 7
    plt.rcParams['ytick.labelsize'] = 7
    plt.rcParams['legend.fontsize'] = 7


    width_inch = 80 / 25.4
    height_inch = 56.56 / 25.4
    plt.rcParams['svg.fonttype'] = 'none'

    # ========================================================

    # ========================================================
    file_configs = [
        {
            'filename': 'predict_RSS_beforeFT.csv',
            'label': 'Baseline',
            'color': "#000000",
            'linestyle': '--'
        },
        {
            'filename': 'predict_RSS_low.csv',
            'label': 'Bottom-U',
            'color': '#002FA7',
            'linestyle': '-'
        },
        {
            'filename': 'predict_RSS_random_42.csv',
            'label': 'Random',
            'color': '#6ECC54',
            'linestyle': '-'
        },
        {
            'filename': 'predict_RSS_hight.csv',
            'label': 'Top-U',
            'color': '#EB5C20',
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

    # ========================================================
    fig, ax = plt.subplots(figsize=(width_inch, height_inch), dpi=300)

    print("--- Reviewing CDF statistics ---")
    valid_plots = 0

    # ========================================================

    # ========================================================
    for cfg in file_configs:
        file_path = os.path.join(folderAddress, cfg['filename'])

        if not os.path.exists(file_path):
            print(f"Warning: File not found: {cfg['filename']}, skipped.")
            continue


        df = pd.read_csv(file_path)
        if len(df) == 0:
            print(f"Warning: File is empty: {cfg['filename']}, skipped.")
            continue


        abs_error = (df['RSSI'] - df['Predicted_Value']).abs().dropna().values


        sorted_error = np.sort(abs_error)
        cdf_y = np.arange(1, len(sorted_error) + 1) / len(sorted_error)


        ax.plot(
            sorted_error,
            cdf_y,
            label=cfg['label'],
            color=cfg['color'],
            linestyle=cfg['linestyle'],
            linewidth=1.0
        )


        median_err = np.median(abs_error)
        print(
            f"Loaded {cfg['filename']}: samples = {len(abs_error)}, "
            f"median error = {median_err:.2f} dB"
        )
        valid_plots += 1

    if valid_plots == 0:
        print("Error: No valid data files were found to plot. Check folder path.")
        return

    # ========================================================

    # ========================================================
    ax.set_xlabel('Absolute Error in dB', labelpad=2)
    ax.set_ylabel('CDF', labelpad=2)


    ax.set_ylim(0, 1.02)
    ax.set_xlim(0, None)
    #ax.set_xlim(0, 30)


    ax.grid(axis='both', linestyle='--', linewidth=0.5, alpha=0.4)


    ax.legend(
        loc='lower right',
        frameon=True,
        edgecolor='#e0e0e0',
        fancybox=False,
        borderpad=0.3,
        labelspacing=0.3
    )

    # ========================================================

    # ========================================================

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
    print("================ CDF plotting completed ================")


def plot_Travel_Distance(folderAddress,
                         start_lat,
                         start_lon,
                         needPNG=True,
                         needSVG=False):
    """Calculate nearest-neighbor travel distances for four sampling methods and plot the comparison as a bar chart."""

    # ==========================================================

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


def plot_Prediction_CSV_Analysis(csv_paths, output_folder, analysis_type, needPNG=True, needSVG=True, file_colors=None):
    """
    Plot core analysis figures for generated prediction CSV files.
    """
    if isinstance(csv_paths, (str, os.PathLike)):
        csv_paths = [csv_paths]

    analysis_labels = {
        "rssi_cdf": ("RSSI CDF", "RSSI in dBm"),
        "predicted_value_cdf": ("Predicted Value CDF", "Predicted RSS in dBm"),
        "uncertainty_cdf": ("Uncertainty CDF", "Uncertainty in dB"),
        "absolute_error_cdf": ("Prediction Absolute Error CDF", "Absolute Error in dB"),
        "model_error_boxplot": ("Model Absolute Error Box Plot", "Absolute Error in dB"),
        "summary_statistics_table": ("Summary Statistics Table", "Value"),
        "predicted_vs_rssi_scatter": ("Predicted vs RSSI Scatter Plot", "RSSI in dBm"),
        "error_vs_distance": ("Error vs Distance Plot", "Tx-Rx Distance in m"),
        "error_vs_altitude_fresnel": ("Error vs Altitude / Fresnel Features", "Feature Value"),
        "path_loss_baseline_cdf": ("Path Loss Baseline Comparison", "Absolute Error in dB"),
        "uncertainty_calibration": ("Uncertainty Calibration Plot", "Uncertainty in dB"),
        "model_error_violin": ("Model Ensemble Violin Plot", "Absolute Error in dB"),
        "spatial_error_map": ("Spatial Error Map", "Longitude"),
    }
    if analysis_type not in analysis_labels:
        return {
            "status": "error",
            "message": "Select a supported prediction CSV analysis type.",
            "files": [],
            "skipped_files": [],
        }

    color_lookup = {}
    if isinstance(file_colors, dict):
        color_lookup = {str(key): value for key, value in file_colors.items() if value}

    os.makedirs(output_folder, exist_ok=True)
    model_column_pattern = re.compile(r"^Model_(\d+)$")
    valid_results = []
    skipped_files = []

    def get_column(columns_by_lower, candidates):
        for candidate in candidates:
            column = columns_by_lower.get(candidate.lower())
            if column is not None:
                return column
        return None

    def require_columns(named_columns):
        missing = [name for name, column in named_columns if column is None]
        if missing:
            return f"Missing required column(s): {', '.join(missing)}."
        return ""

    def valid_error_frame(df, rssi_column, predicted_column, extra_columns=None):
        selected_columns = [rssi_column, predicted_column] + list(extra_columns or [])
        values = df[selected_columns].apply(pd.to_numeric, errors="coerce")
        values = values[values[rssi_column] > -900].dropna()
        if values.empty:
            return None
        values["Absolute Error"] = (values[rssi_column] - values[predicted_column]).abs()
        return values

    def describe_values(values):
        values = np.asarray(values, dtype=float)
        return {
            "mean": float(np.mean(values)),
            "median": float(np.median(values)),
            "std": float(np.std(values, ddof=1)) if values.size > 1 else 0.0,
            "p50": float(np.percentile(values, 50)),
            "p80": float(np.percentile(values, 80)),
            "p90": float(np.percentile(values, 90)),
            "p95": float(np.percentile(values, 95)),
        }

    for csv_path in csv_paths or []:
        file_name = os.path.basename(str(csv_path))
        try:
            df = pd.read_csv(csv_path)
        except Exception as exc:
            skipped_files.append({"file": file_name, "reason": f"Could not read CSV: {exc}"})
            continue

        columns_by_lower = {str(col).lower(): col for col in df.columns}
        rssi_column = columns_by_lower.get("rssi")
        predicted_column = columns_by_lower.get("predicted_value")
        uncertainty_column = columns_by_lower.get("uncertainty")
        distance_column = columns_by_lower.get("disbtwtxrx")
        altitude_column = columns_by_lower.get("dn")
        fresnel_h_column = columns_by_lower.get("fresnelr_h")
        fresnel_v_column = columns_by_lower.get("fresnelr_v")
        latitude_column = get_column(columns_by_lower, ["latitude", "lat", "y"])
        longitude_column = get_column(columns_by_lower, ["longitude", "lon", "lng", "x"])
        path_loss_eta_2_column = columns_by_lower.get("pathloss_eta_2")
        path_loss_eta_3_column = columns_by_lower.get("pathloss_eta_3")
        model_columns = [col for col in df.columns if model_column_pattern.match(str(col))]
        model_columns = sorted(
            model_columns,
            key=lambda col: int(model_column_pattern.match(str(col)).group(1))
        )

        selected_color = color_lookup.get(str(csv_path)) or color_lookup.get(file_name)
        if analysis_type == "rssi_cdf":
            if not rssi_column:
                skipped_files.append({"file": file_name, "reason": "Missing RSSI or rssi column."})
                continue
            values = pd.to_numeric(df[rssi_column], errors="coerce").dropna().to_numpy()
            if values.size == 0:
                skipped_files.append({"file": file_name, "reason": "No valid RSSI samples."})
                continue
            valid_results.append({"file": file_name, "color": selected_color, "values": values})
        elif analysis_type == "predicted_value_cdf":
            if not predicted_column:
                skipped_files.append({"file": file_name, "reason": "Missing Predicted_Value column."})
                continue
            values = pd.to_numeric(df[predicted_column], errors="coerce").dropna().to_numpy()
            if values.size == 0:
                skipped_files.append({"file": file_name, "reason": "No valid Predicted_Value samples."})
                continue
            valid_results.append({"file": file_name, "color": selected_color, "values": values})
        elif analysis_type == "uncertainty_cdf":
            if not uncertainty_column:
                skipped_files.append({"file": file_name, "reason": "Missing Uncertainty column."})
                continue
            values = pd.to_numeric(df[uncertainty_column], errors="coerce").dropna().to_numpy()
            if values.size == 0:
                skipped_files.append({"file": file_name, "reason": "No valid Uncertainty samples."})
                continue
            valid_results.append({"file": file_name, "color": selected_color, "values": values})
        elif analysis_type == "absolute_error_cdf":
            missing = []
            if not rssi_column:
                missing.append("RSSI or rssi")
            if not predicted_column:
                missing.append("Predicted_Value")
            if missing:
                skipped_files.append({"file": file_name, "reason": f"Missing required column(s): {', '.join(missing)}."})
                continue
            values = pd.DataFrame({
                "RSSI": pd.to_numeric(df[rssi_column], errors="coerce"),
                "Predicted_Value": pd.to_numeric(df[predicted_column], errors="coerce"),
            })
            values = values[(values["RSSI"] > -900)].dropna()
            if values.empty:
                skipped_files.append({"file": file_name, "reason": "No valid RSSI and Predicted_Value rows after filtering placeholder RSSI values."})
                continue
            errors = (values["RSSI"] - values["Predicted_Value"]).abs().to_numpy()
            valid_results.append({"file": file_name, "color": selected_color, "values": errors})
        elif analysis_type == "model_error_boxplot":
            if not rssi_column:
                skipped_files.append({"file": file_name, "reason": "Missing RSSI or rssi column."})
                continue
            if not model_columns:
                skipped_files.append({"file": file_name, "reason": "Missing Model_* columns such as Model_0, Model_1, ..."})
                continue
            numeric = df[[rssi_column] + model_columns].apply(pd.to_numeric, errors="coerce")
            numeric = numeric[numeric[rssi_column] > -900]
            model_errors = []
            used_model_columns = []
            for col in model_columns:
                errors = (numeric[col] - numeric[rssi_column]).abs().dropna().to_numpy()
                if errors.size:
                    model_errors.append(errors)
                    used_model_columns.append(col)
            if not model_errors:
                skipped_files.append({"file": file_name, "reason": "No valid Model_* and RSSI rows after filtering placeholder RSSI values."})
                continue
            valid_results.append({
                "file": file_name,
                "color": selected_color,
                "model_errors": model_errors,
                "model_columns": used_model_columns,
                "values": np.concatenate(model_errors),
            })
        elif analysis_type == "summary_statistics_table":
            missing_reason = require_columns([
                ("RSSI or rssi", rssi_column),
                ("Predicted_Value", predicted_column),
                ("Uncertainty", uncertainty_column),
            ])
            if missing_reason:
                skipped_files.append({"file": file_name, "reason": missing_reason})
                continue
            values = valid_error_frame(df, rssi_column, predicted_column, [uncertainty_column])
            if values is None:
                skipped_files.append({"file": file_name, "reason": "No valid rows after filtering placeholder RSSI values."})
                continue
            statistics = {
                "RSSI": describe_values(values[rssi_column].to_numpy()),
                "Predicted_Value": describe_values(values[predicted_column].to_numpy()),
                "Uncertainty": describe_values(values[uncertainty_column].to_numpy()),
                "Absolute Error": describe_values(values["Absolute Error"].to_numpy()),
            }
            valid_results.append({
                "file": file_name,
                "color": selected_color,
                "values": values["Absolute Error"].to_numpy(),
                "statistics": statistics,
                "metric_count": len(statistics),
            })
        elif analysis_type == "predicted_vs_rssi_scatter":
            missing_reason = require_columns([
                ("RSSI or rssi", rssi_column),
                ("Predicted_Value", predicted_column),
            ])
            if missing_reason:
                skipped_files.append({"file": file_name, "reason": missing_reason})
                continue
            values = valid_error_frame(df, rssi_column, predicted_column)
            if values is None:
                skipped_files.append({"file": file_name, "reason": "No valid RSSI and Predicted_Value rows after filtering placeholder RSSI values."})
                continue
            valid_results.append({
                "file": file_name,
                "color": selected_color,
                "x": values[rssi_column].to_numpy(),
                "y": values[predicted_column].to_numpy(),
                "values": values["Absolute Error"].to_numpy(),
            })
        elif analysis_type == "error_vs_distance":
            missing_reason = require_columns([
                ("RSSI or rssi", rssi_column),
                ("Predicted_Value", predicted_column),
                ("disBtwTxRx", distance_column),
            ])
            if missing_reason:
                skipped_files.append({"file": file_name, "reason": missing_reason})
                continue
            values = valid_error_frame(df, rssi_column, predicted_column, [distance_column])
            if values is None:
                skipped_files.append({"file": file_name, "reason": "No valid distance and error rows after filtering placeholder RSSI values."})
                continue
            valid_results.append({
                "file": file_name,
                "color": selected_color,
                "x": values[distance_column].to_numpy(),
                "values": values["Absolute Error"].to_numpy(),
            })
        elif analysis_type == "error_vs_altitude_fresnel":
            feature_columns = [
                ("DN", altitude_column),
                ("FresnelR_H", fresnel_h_column),
                ("FresnelR_V", fresnel_v_column),
            ]
            missing_reason = require_columns([
                ("RSSI or rssi", rssi_column),
                ("Predicted_Value", predicted_column),
                *feature_columns,
            ])
            if missing_reason:
                skipped_files.append({"file": file_name, "reason": missing_reason})
                continue
            values = valid_error_frame(df, rssi_column, predicted_column, [column for _, column in feature_columns])
            if values is None:
                skipped_files.append({"file": file_name, "reason": "No valid feature and error rows after filtering placeholder RSSI values."})
                continue
            valid_results.append({
                "file": file_name,
                "color": selected_color,
                "features": {name: values[column].to_numpy() for name, column in feature_columns},
                "values": values["Absolute Error"].to_numpy(),
            })
        elif analysis_type == "path_loss_baseline_cdf":
            series_columns = [
                ("ML Prediction", predicted_column),
                ("Path Loss eta 2", path_loss_eta_2_column),
                ("Path Loss eta 3", path_loss_eta_3_column),
            ]
            missing_reason = require_columns([("RSSI or rssi", rssi_column), *series_columns])
            if missing_reason:
                skipped_files.append({"file": file_name, "reason": missing_reason})
                continue
            numeric = df[[rssi_column] + [column for _, column in series_columns]].apply(pd.to_numeric, errors="coerce")
            numeric = numeric[numeric[rssi_column] > -900].dropna()
            if numeric.empty:
                skipped_files.append({"file": file_name, "reason": "No valid baseline comparison rows after filtering placeholder RSSI values."})
                continue
            series = {
                name: (numeric[column] - numeric[rssi_column]).abs().to_numpy()
                for name, column in series_columns
            }
            valid_results.append({
                "file": file_name,
                "color": selected_color,
                "series": series,
                "values": np.concatenate(list(series.values())),
            })
        elif analysis_type == "uncertainty_calibration":
            missing_reason = require_columns([
                ("RSSI or rssi", rssi_column),
                ("Predicted_Value", predicted_column),
                ("Uncertainty", uncertainty_column),
            ])
            if missing_reason:
                skipped_files.append({"file": file_name, "reason": missing_reason})
                continue
            values = valid_error_frame(df, rssi_column, predicted_column, [uncertainty_column])
            if values is None:
                skipped_files.append({"file": file_name, "reason": "No valid uncertainty and error rows after filtering placeholder RSSI values."})
                continue
            valid_results.append({
                "file": file_name,
                "color": selected_color,
                "x": values[uncertainty_column].to_numpy(),
                "values": values["Absolute Error"].to_numpy(),
            })
        elif analysis_type == "model_error_violin":
            if not rssi_column:
                skipped_files.append({"file": file_name, "reason": "Missing RSSI or rssi column."})
                continue
            if not model_columns:
                skipped_files.append({"file": file_name, "reason": "Missing Model_* columns such as Model_0, Model_1, ..."})
                continue
            numeric = df[[rssi_column] + model_columns].apply(pd.to_numeric, errors="coerce")
            numeric = numeric[numeric[rssi_column] > -900]
            model_errors = []
            used_model_columns = []
            for col in model_columns:
                errors = (numeric[col] - numeric[rssi_column]).abs().dropna().to_numpy()
                if errors.size:
                    model_errors.append(errors)
                    used_model_columns.append(col)
            if not model_errors:
                skipped_files.append({"file": file_name, "reason": "No valid Model_* and RSSI rows after filtering placeholder RSSI values."})
                continue
            valid_results.append({
                "file": file_name,
                "color": selected_color,
                "model_errors": model_errors,
                "model_columns": used_model_columns,
                "values": np.concatenate(model_errors),
            })
        elif analysis_type == "spatial_error_map":
            missing_reason = require_columns([
                ("RSSI or rssi", rssi_column),
                ("Predicted_Value", predicted_column),
                ("Latitude", latitude_column),
                ("Longitude", longitude_column),
            ])
            if missing_reason:
                skipped_files.append({"file": file_name, "reason": missing_reason})
                continue
            values = valid_error_frame(df, rssi_column, predicted_column, [latitude_column, longitude_column])
            if values is None:
                skipped_files.append({"file": file_name, "reason": "No valid coordinate and error rows after filtering placeholder RSSI values."})
                continue
            valid_results.append({
                "file": file_name,
                "color": selected_color,
                "longitude": values[longitude_column].to_numpy(),
                "latitude": values[latitude_column].to_numpy(),
                "values": values["Absolute Error"].to_numpy(),
            })

    if not valid_results:
        return {
            "status": "error",
            "message": "No valid prediction CSV files were available for this analysis.",
            "analysis_type": analysis_type,
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
    plt.rcParams['legend.fontsize'] = 7
    plt.rcParams['svg.fonttype'] = 'none'

    title, x_label = analysis_labels[analysis_type]
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

    if analysis_type == "summary_statistics_table":
        ax.axis("off")
        metric_rows = []
        row_colors = []
        statistic_names = ["mean", "median", "std", "p50", "p80", "p90", "p95"]
        for index, result in enumerate(valid_results):
            color = normalize_matplotlib_color(result.get("color")) or default_colors[index % len(default_colors)]
            for metric_name, stats in result["statistics"].items():
                metric_rows.append([
                    os.path.splitext(result["file"])[0],
                    metric_name,
                    *[f"{stats[name]:.2f}" for name in statistic_names],
                ])
                row_colors.append(color)
        table = ax.table(
            cellText=metric_rows,
            colLabels=["CSV", "Metric", "Mean", "Median", "Std", "P50", "P80", "P90", "P95"],
            loc="center",
            cellLoc="center",
        )
        table.auto_set_font_size(False)
        table.set_fontsize(5.2)
        table.scale(1.0, 1.3)
        for (row, col), cell in table.get_celld().items():
            cell.set_edgecolor("#cbd5e1")
            cell.set_linewidth(0.35)
            if row == 0:
                cell.set_facecolor("#e2e8f0")
                cell.set_text_props(weight="bold", color="#111827")
            elif col == 0:
                cell.set_facecolor(row_colors[(row - 1) % len(row_colors)])
                cell.set_text_props(color="#ffffff")
        ax.set_title(title, pad=4)
    elif analysis_type in {"model_error_boxplot", "model_error_violin"}:
        all_errors_by_model = {}
        for result in valid_results:
            for model_col, errors in zip(result["model_columns"], result["model_errors"]):
                all_errors_by_model.setdefault(model_col, []).append(errors)
        ordered_models = sorted(all_errors_by_model, key=lambda col: int(model_column_pattern.match(str(col)).group(1)))
        plot_data = [np.concatenate(all_errors_by_model[col]) for col in ordered_models]
        if analysis_type == "model_error_boxplot":
            box_artists = ax.boxplot(
                plot_data,
                tick_labels=ordered_models,
                patch_artist=True,
                boxprops={"alpha": 0.62, "edgecolor": "#1f2937", "linewidth": 0.7},
                medianprops={"color": "#ef4444", "linewidth": 1.0},
                whiskerprops={"color": "#1f2937", "linewidth": 0.7},
                capprops={"color": "#1f2937", "linewidth": 0.7},
                flierprops={"marker": ".", "markersize": 1.6, "markerfacecolor": "#64748b", "markeredgecolor": "#64748b", "alpha": 0.35},
            )
            for index, patch in enumerate(box_artists["boxes"]):
                patch.set_facecolor(default_colors[index % len(default_colors)])
        else:
            violin_artists = ax.violinplot(plot_data, showmeans=True, showmedians=True, showextrema=True)
            for index, body in enumerate(violin_artists["bodies"]):
                body.set_facecolor(default_colors[index % len(default_colors)])
                body.set_edgecolor("#1f2937")
                body.set_alpha(0.58)
            ax.set_xticks(range(1, len(ordered_models) + 1), ordered_models)
        ax.tick_params(axis="x", labelrotation=60)
        ax.set_ylabel(x_label, labelpad=2)
    elif analysis_type == "predicted_vs_rssi_scatter":
        all_x = []
        all_y = []
        for index, result in enumerate(valid_results):
            color = normalize_matplotlib_color(result.get("color")) or default_colors[index % len(default_colors)]
            ax.scatter(result["x"], result["y"], label=os.path.splitext(result["file"])[0], color=color, s=9, alpha=0.62, edgecolors="none")
            all_x.extend(result["x"])
            all_y.extend(result["y"])
        ref_min = min(min(all_x), min(all_y))
        ref_max = max(max(all_x), max(all_y))
        ax.plot([ref_min, ref_max], [ref_min, ref_max], color="#111827", linestyle="--", linewidth=0.8, label="y = x")
        ax.set_xlabel(x_label, labelpad=2)
        ax.set_ylabel("Predicted RSS in dBm", labelpad=2)
        ax.legend(loc="best", frameon=True, edgecolor="#e0e0e0", fancybox=False, borderpad=0.3, labelspacing=0.25)
    elif analysis_type == "error_vs_distance":
        for index, result in enumerate(valid_results):
            color = normalize_matplotlib_color(result.get("color")) or default_colors[index % len(default_colors)]
            ax.scatter(result["x"], result["values"], label=os.path.splitext(result["file"])[0], color=color, s=9, alpha=0.62, edgecolors="none")
        ax.set_xlabel(x_label, labelpad=2)
        ax.set_ylabel("Absolute Error in dB", labelpad=2)
        ax.set_ylim(0, None)
        ax.legend(loc="best", frameon=True, edgecolor="#e0e0e0", fancybox=False, borderpad=0.3, labelspacing=0.25)
    elif analysis_type == "error_vs_altitude_fresnel":
        feature_names = ["DN", "FresnelR_H", "FresnelR_V"]
        feature_axes = fig.subplots(1, 3, sharey=True)
        for axis, feature_name in zip(feature_axes, feature_names):
            for index, result in enumerate(valid_results):
                color = normalize_matplotlib_color(result.get("color")) or default_colors[index % len(default_colors)]
                axis.scatter(result["features"][feature_name], result["values"], label=os.path.splitext(result["file"])[0], color=color, s=7, alpha=0.58, edgecolors="none")
            label = "DN in m" if feature_name == "DN" else f"{feature_name} in m"
            axis.set_xlabel(label, labelpad=2)
            axis.grid(axis="both", linestyle="--", linewidth=0.5, alpha=0.4)
        feature_axes[0].set_ylabel("Absolute Error in dB", labelpad=2)
        feature_axes[-1].legend(loc="best", frameon=True, edgecolor="#e0e0e0", fancybox=False, borderpad=0.3, labelspacing=0.25)
        fig.suptitle(title, y=0.98)
        ax.remove()
        ax = feature_axes[0]
    elif analysis_type == "path_loss_baseline_cdf":
        line_styles = {"ML Prediction": "-", "Path Loss eta 2": "--", "Path Loss eta 3": ":"}
        for index, result in enumerate(valid_results):
            base_color = normalize_matplotlib_color(result.get("color")) or default_colors[index % len(default_colors)]
            for series_name, values in result["series"].items():
                sorted_values, cdf = compute_cdf(values)
                label = f"{os.path.splitext(result['file'])[0]} - {series_name}"
                ax.plot(sorted_values, cdf, label=label, color=base_color, linestyle=line_styles[series_name], linewidth=1.0)
        ax.set_xlabel(x_label, labelpad=2)
        ax.set_ylabel("CDF", labelpad=2)
        ax.set_xlim(0, None)
        ax.set_ylim(0, 1.02)
        ax.legend(loc="lower right", frameon=True, edgecolor="#e0e0e0", fancybox=False, borderpad=0.3, labelspacing=0.25)
    elif analysis_type == "uncertainty_calibration":
        for index, result in enumerate(valid_results):
            color = normalize_matplotlib_color(result.get("color")) or default_colors[index % len(default_colors)]
            order = np.argsort(result["x"])
            x_sorted = np.asarray(result["x"])[order]
            y_sorted = np.asarray(result["values"])[order]
            bin_count = min(10, max(1, y_sorted.size))
            splits = np.array_split(np.arange(y_sorted.size), bin_count)
            bin_x = [float(np.mean(x_sorted[split])) for split in splits if split.size]
            bin_y = [float(np.mean(y_sorted[split])) for split in splits if split.size]
            result["bin_count"] = len(bin_x)
            ax.plot(bin_x, bin_y, marker="o", markersize=2.6, label=os.path.splitext(result["file"])[0], color=color, linewidth=1.0)
        ax.set_xlabel(x_label, labelpad=2)
        ax.set_ylabel("Mean Absolute Error in dB", labelpad=2)
        ax.set_ylim(0, None)
        ax.legend(loc="best", frameon=True, edgecolor="#e0e0e0", fancybox=False, borderpad=0.3, labelspacing=0.25)
    elif analysis_type == "spatial_error_map":
        for index, result in enumerate(valid_results):
            scatter = ax.scatter(
                result["longitude"],
                result["latitude"],
                c=result["values"],
                cmap="turbo",
                s=12,
                alpha=0.78,
                edgecolors="none",
                label=os.path.splitext(result["file"])[0],
            )
        fig.colorbar(scatter, ax=ax, label="Absolute Error in dB", fraction=0.046, pad=0.04)
        ax.set_xlabel("Longitude", labelpad=2)
        ax.set_ylabel("Latitude", labelpad=2)
        ax.legend(loc="best", frameon=True, edgecolor="#e0e0e0", fancybox=False, borderpad=0.3, labelspacing=0.25)
    else:
        for index, result in enumerate(valid_results):
            color = normalize_matplotlib_color(result.get("color")) or default_colors[index % len(default_colors)]
            sorted_values, cdf = compute_cdf(result["values"])
            label = os.path.splitext(result["file"])[0]
            ax.plot(sorted_values, cdf, label=label, color=color, linestyle="-", linewidth=1.0)
        ax.set_xlabel(x_label, labelpad=2)
        ax.set_ylabel('CDF', labelpad=2)
        ax.set_ylim(0, 1.02)
        if analysis_type in {"uncertainty_cdf", "absolute_error_cdf"}:
            ax.set_xlim(0, None)
        ax.legend(loc='lower right', frameon=True, edgecolor='#e0e0e0', fancybox=False, borderpad=0.3, labelspacing=0.25)

    if analysis_type not in {"summary_statistics_table", "error_vs_altitude_fresnel"}:
        ax.set_title(title, pad=4)
        ax.grid(axis='both', linestyle='--', linewidth=0.5, alpha=0.4)
    if analysis_type == "summary_statistics_table":
        fig.subplots_adjust(left=0.02, right=0.98, top=0.88, bottom=0.05)
    elif analysis_type == "error_vs_altitude_fresnel":
        fig.subplots_adjust(left=0.1, right=0.98, top=0.86, bottom=0.22, wspace=0.26)
    else:
        fig.subplots_adjust(left=0.12, right=0.97, top=0.92, bottom=0.18)

    filename = f'Prediction_CSV_{analysis_type}'
    svg_output = os.path.join(output_folder, f'{filename}.svg')
    png_output = os.path.join(output_folder, f'{filename}.png')
    save_props = {'dpi': 300, 'bbox_inches': 'tight', 'pad_inches': 0.012}
    if needSVG:
        fig.savefig(svg_output, format='svg', **save_props)
    if needPNG:
        fig.savefig(png_output, **save_props)
    fig.clear()

    files = []
    for result in valid_results:
        values = result["values"]
        files.append({
            "file": result["file"],
            "sample_count": int(values.size),
            "model_count": len(result.get("model_columns", [])),
            "metric_count": result.get("metric_count", 0),
            "series_count": len(result.get("series", {})),
            "bin_count": result.get("bin_count", 0),
            "mean": float(np.mean(values)),
            "median": float(np.median(values)),
            "std": float(np.std(values, ddof=1)) if values.size > 1 else 0.0,
            "p50": float(np.percentile(values, 50)),
            "p80": float(np.percentile(values, 80)),
            "p90": float(np.percentile(values, 90)),
            "p95": float(np.percentile(values, 95)),
            "statistics": result.get("statistics", {}),
            "series": {name: describe_values(series_values) for name, series_values in result.get("series", {}).items()},
        })

    return {
        "status": "success",
        "message": f"Generated {title} for {len(valid_results)} valid CSV file(s).",
        "analysis_type": analysis_type,
        "analysis_title": title,
        "valid_file_count": len(valid_results),
        "files": files,
        "skipped_files": skipped_files,
        "svg_path": svg_output if needSVG else "",
        "png_path": png_output if needPNG else "",
    }


def split_dataset_by_region_stratified_sampling(folderAddress,fileName="predict_RSS.csv",lat_col="Latitude",lon_col="Longitude"):
    # URAS: Uncertainty + Region Stratified Sampling
    import os
    import numpy as np
    import pandas as pd
    from sklearn.cluster import DBSCAN

    # =====================================================
    # Helper Function
    # =====================================================

    def find_best_region(
            df_part,
            lat_col,
            lon_col,
            uncertainty_col,
            eps,
            min_samples):

        if len(df_part) == 0:
            return pd.DataFrame()

        coords = df_part[
            [lat_col, lon_col]
        ].values

        clustering = DBSCAN(
            eps=eps,
            min_samples=min_samples
        )

        labels = clustering.fit_predict(coords)

        df_part = df_part.copy()

        df_part["Cluster"] = labels

        valid_cluster = df_part[
            df_part["Cluster"] != -1
        ]

        # No cluster found
        if len(valid_cluster) == 0:
            return df_part

        cluster_stat = []

        for cid in sorted(
                valid_cluster["Cluster"].unique()):

            tmp = valid_cluster[
                valid_cluster["Cluster"] == cid
            ]

            cluster_stat.append([
                cid,
                tmp["Uncertainty"].mean(),
                len(tmp)
            ])

        cluster_stat = pd.DataFrame(
            cluster_stat,
            columns=[
                "Cluster",
                "MeanU",
                "Size"
            ]
        )

        # Region Score
        cluster_stat["Score"] = (
            cluster_stat["MeanU"]
            *
            np.log1p(
                cluster_stat["Size"]
            )
        )

        best_cluster = (
            cluster_stat
            .sort_values(
                by="Score",
                ascending=False
            )
            .iloc[0]["Cluster"]
        )

        best_region = valid_cluster[
            valid_cluster["Cluster"]
            == best_cluster
        ].copy()

        return best_region

    # =====================================================
    # Region Stratified Sampling
    # =====================================================

    def region_stratified_sampling(
            df,
            lat_col='Latitude',
            lon_col='Longitude',
            uncertainty_col='Uncertainty',
            sample_ratio=0.1,
            top_ratio=0.7,
            middle_ratio=0.2,
            bottom_ratio=0.1,
            eps=0.0008,
            min_samples=20):

        df = df.copy().reset_index(drop=True)

        total_samples = len(df)

        select_num = max(
            int(total_samples * sample_ratio),
            1
        )

        # =====================================
        # Split U Distribution
        # =====================================

        df_sorted = df.sort_values(
            by=uncertainty_col,
            ascending=False
        ).reset_index(drop=True)

        top_num = int(total_samples * 0.2)
        bottom_num = int(total_samples * 0.2)

        top_df = df_sorted.iloc[:top_num].copy()

        middle_df = df_sorted.iloc[
            top_num:-bottom_num
        ].copy()

        bottom_df = df_sorted.iloc[
            -bottom_num:
        ].copy()

        # =====================================
        # Find Regions
        # =====================================

        top_region = find_best_region(
            top_df,
            lat_col,
            lon_col,
            uncertainty_col,
            eps,
            min_samples
        )

        middle_region = find_best_region(
            middle_df,
            lat_col,
            lon_col,
            uncertainty_col,
            eps,
            min_samples
        )

        bottom_region = find_best_region(
            bottom_df,
            lat_col,
            lon_col,
            uncertainty_col,
            eps,
            min_samples
        )

        # =====================================
        # Allocation
        # =====================================

        n_top = int(
            select_num * top_ratio
        )

        n_middle = int(
            select_num * middle_ratio
        )

        n_bottom = (
            select_num
            - n_top
            - n_middle
        )

        top_ft = (
            top_region
            .sort_values(
                by=uncertainty_col,
                ascending=False
            )
            .head(
                min(
                    n_top,
                    len(top_region)
                )
            )
        )

        if len(middle_region) > 0:

            middle_ft = (
                middle_region
                .sample(
                    n=min(
                        n_middle,
                        len(middle_region)
                    ),
                    random_state=42
                )
            )

        else:

            middle_ft = pd.DataFrame()

        if len(bottom_region) > 0:

            bottom_ft = (
                bottom_region
                .sample(
                    n=min(
                        n_bottom,
                        len(bottom_region)
                    ),
                    random_state=42
                )
            )

        else:

            bottom_ft = pd.DataFrame()

        selected_df = pd.concat(
            [
                top_ft,
                middle_ft,
                bottom_ft
            ]
        )

        # =====================================
        # Fill Missing
        # =====================================

        if len(selected_df) < select_num:

            remain_num = (
                select_num
                - len(selected_df)
            )

            remain_pool = df[
                ~df["SampleID"].isin(
                    selected_df["SampleID"]
                )
            ]

            additional = (
                remain_pool
                .sort_values(
                    by=uncertainty_col,
                    ascending=False
                )
                .head(remain_num)
            )

            selected_df = pd.concat(
                [
                    selected_df,
                    additional
                ]
            )

        print(str(min(top_ft['Uncertainty'])) + " < top_ft < " + str(max(top_ft['Uncertainty'])))
        print(str(min(middle_ft['Uncertainty'])) + " < middle_ft < " + str(max(middle_ft['Uncertainty'])))
        print(str(min(bottom_ft['Uncertainty'])) + " < bottom_ft < " + str(max(bottom_ft['Uncertainty'])))
        return selected_df

    # =====================================================
    # Load Dataset
    # =====================================================

    file_path = os.path.join(
        folderAddress,
        fileName
    )

    df = pd.read_csv(file_path)

    if "SampleID" not in df.columns:

        df["SampleID"] = np.arange(
            len(df)
        )

    total_samples = len(df)

    p10_idx = max(
        int(total_samples * 0.1),
        1
    )

    # =====================================================
    # Top10%
    # =====================================================

    df_sorted = df.sort_values(
        by="Uncertainty",
        ascending=False
    )

    high_ft = df_sorted.iloc[:p10_idx]

    # =====================================================
    # Bottom10%
    # =====================================================

    low_ft = df_sorted.iloc[-p10_idx:]

    # =====================================================
    # Random
    # =====================================================

    random_42_ft = df.sample(
        n=p10_idx,
        random_state=42
    )

    # =====================================================
    # Region Stratified Sampling
    # =====================================================

    region_ft = region_stratified_sampling(
        df,
        lat_col=lat_col,
        lon_col=lon_col,
        uncertainty_col="Uncertainty",

        sample_ratio=0.1,

        top_ratio=0.7,
        middle_ratio=0.2,
        bottom_ratio=0.1,

        eps=0.0008,
        min_samples=20
    )

    # =====================================================
    # Save FT Dataset
    # =====================================================

    high_ft.to_csv(
        os.path.join(
            folderAddress,
            "highUncertainty_ft_10p.csv"
        ),
        index=False
    )

    low_ft.to_csv(
        os.path.join(
            folderAddress,
            "lowUncertainty_ft_10p.csv"
        ),
        index=False
    )

    random_42_ft.to_csv(
        os.path.join(
            folderAddress,
            "random_42_ft_10p.csv"
        ),
        index=False
    )

    region_ft.to_csv(
        os.path.join(
            folderAddress,
            "proposal_ft_10p.csv"
        ),
        index=False
    )

    # =====================================================
    # Common Test
    # =====================================================

    train_ids = (
        set(high_ft["SampleID"])
        |
        set(low_ft["SampleID"])
        |
        set(random_42_ft["SampleID"])
        |
        set(region_ft["SampleID"])
    )

    common_test = df[
        ~df["SampleID"].isin(
            train_ids
        )
    ]

    common_test.to_csv(
        os.path.join(
            folderAddress,
            "common_test.csv"
        ),
        index=False
    )

    # =====================================================
    # Report
    # =====================================================

    print("================================")
    print("Finished")
    print("================================")
    print(f"Total Samples : {total_samples}")
    print(f"FT Samples    : {p10_idx}")
    print(f"Common Test   : {len(common_test)}")
    print()

    print(
        f"High Mean U   : "
        f"{high_ft['Uncertainty'].mean():.3f}"
    )

    print(
        f"Low Mean U    : "
        f"{low_ft['Uncertainty'].mean():.3f}"
    )

    print(
        f"Random Mean U : "
        f"{random_42_ft['Uncertainty'].mean():.3f}"
    )

    print(
        f"Region Mean U : "
        f"{region_ft['Uncertainty'].mean():.3f}"
    )








def main():
    """Run the module's publication-quality plotting workflow."""


    # EIRP = 37  # dBm
    fix_longitude = 139.674057
    fix_latitude = 35.223331

    # fix_antennaHeight = 1.8
    # move_antennaHeight = 1.37
    targetFileAddress = "/Users/zhaoou/Desktop/課題1_TL拡張/TL検証/920MHz/predict_RSS_FT30.csv"
    referenceFileAddress = "/Users/zhaoou/Desktop/課題1_TL拡張/TL検証/920MHz/predict_RSS_M0_test_30.csv"
    outputFileAddress = "/Users/zhaoou/Downloads/"



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


    #plot_Four_Scenarios_Error_CDF(folderAddress, needPNG=False, needSVG=True)
    split_dataset_by_region_stratified_sampling(folderAddress,fileName="predict_RSS.csv",lat_col="Latitude",lon_col="Longitude")
    #plot_Travel_Distance(folderAddress, start_lat = start_lat_unseen1, start_lon = start_lon_unseen1, needPNG=True, needSVG=False)

    return





if __name__ == "__main__":
    import sys,os
    main()
