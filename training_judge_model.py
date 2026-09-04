import numpy as np
import tensorflow as tf
import matplotlib.pyplot as plt
from tensorflow.keras import layers, models
from tensorflow.keras.layers import Lambda
from keras.saving import register_keras_serializable
from tensorflow.keras.utils import plot_model
from tensorflow.python.ops.distributions.util import same_dynamic_shape
from tensorflow.keras.callbacks import ReduceLROnPlateau
from tqdm import tqdm
from sklearn.ensemble import RandomForestRegressor
from tensorflow.keras import layers, models, callbacks, regularizers, optimizers, regularizers
from sklearn.model_selection import KFold
from dask.distributed import get_client, as_completed
import dill
import pandas as pd
from sklearn.cluster import KMeans
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from sklearn.model_selection import train_test_split
from scipy.spatial import KDTree
from collections import Counter
from sklearn.ensemble import RandomForestClassifier


def run_main_judge_cnn():

    return


def save_oof_to_csv(df_oof, filename="oof_analysis.csv"):
    # Save the analysis results.
    df_oof.to_csv(filename, index=False)
    print(f">>> OOF analysis file saved to: {filename}")
    return




# Example of invoking the judge model from the main function and integrating it into the prediction pipeline.
def train_and_predict_by_judge_model(judgeModelInfo, testData_TL, rxData_Altitude_TL):
    """
    ``judgeModelInfo`` contains predictions from all 30 models trained on the
    fine-tuning dataset, together with each sample's features and ground truth.
    This information can be used to train a judge model.
        judgeModelInfo = {
            "df_oof": df_oof,#dataframe
            "debug_data": debug_data, # Dictionary.
        }
        debug_data = {
            "FV": FV,
            "TV": TV,
            "optionalParams": optionalParams,
            "OOF": oof_predict_matrix,
        }
        judgeModelInfo['debug_data']['OOF'].shape[1]: Number of expert models.
        df_oof['Model_n']: Model predictions on the fine-tuning dataset, where n=0,1,...,29.
        df_oof['RSSI_TV']: Ground truth for the model, namely the TV value corresponding to FV.
        df_oof['Median_Prediction']: Median prediction across N models, used as the baseline.
        df_oof['Median_Abs_Error']: Absolute error between the median prediction and ground truth.
        df_oof['Best_Model_Idx']: Index of the best-performing model.
        df_oof['Best_Model_Error']: Prediction error of the best-performing model.
        df_oof['Latitude']: Latitude coordinate.
        df_oof['Longitude']: Longitude coordinate.
        df_oof['RSSI']: Measured ground-truth value.
        df_oof['DN']: Elevation.
        df_oof['FresnelR_H']: Fresnel diffraction parameter at the first half-wavelength point.
        df_oof['FresnelR_V']: Fresnel diffraction parameter in the vertical direction.
        df_oof['disBtwTxRx']: Distance between the transmitter and receiver.
    ``testData_TL`` is the test input feature vector FV with shape 31*36*5*N.
    ``rxData_Altitude_TL`` contains test features and ground truth, including
    Latitude, Longitude, RSSI, DN, FresnelR_H, FresnelR_V, and disBtwTxRx.
        rxData_Altitude_TL[model_n]: Model predictions on the test dataset, where n=0,1,...,29.
    """

    # save_oof_to_csv(judgeModelInfo['df_oof'], "/Users/zhaoou/Downloads/oof_analysis.csv")
    correctedPredictionValue = algo_FV_randomForestRegressor_residuals(judgeModelInfo, testData_TL, rxData_Altitude_TL)
    # correctedPredictionValue = algo_disDN_mapping_sign(judgeModelInfo, testData_TL, rxData_Altitude_TL)



    return correctedPredictionValue


def algo_disDN_mapping_sign(judgeModelInfo, testData, rxData_Altitude_TL):
    """
    Asymmetric filtering strategy that compensates median bias using the
    environmental fingerprint (DN and distance).
    """
    # 1. Obtain training data from the OOF results for fine-tuning dataset B.
    numNetworks = judgeModelInfo['debug_data']['OOF'].shape[1]  # Number of expert models.
    df_oof = judgeModelInfo["df_oof"].copy()
    model_cols = ['Model_' + str(i) for i in range(numNetworks)]

    # Compute training-set statistics.
    df_oof['mean_30'] = df_oof[model_cols].mean(axis=1)
    df_oof['std_30'] = df_oof[model_cols].std(axis=1)
    # Actual K value: absolute error divided by standard deviation.
    df_oof['K_actual'] = df_oof['Median_Abs_Error'] / (df_oof['std_30'] + 1e-9)
    # Actual sign: sign of (median - ground truth).
    # If Median > TV, the sign is +1 (overestimate); if Median < TV, it is -1 (underestimate).
    df_oof['Bias_Sign'] = np.sign(df_oof['Median_Prediction'] - df_oof['RSSI_TV'])

    # 2. Build MxM environmental-fingerprint lookup tables.
    # Use quantile or equal-width bins; define boundaries from the judge dataset range.
    M_dis = 100
    M_alt = 20
    dist_bins = pd.cut(df_oof['disBtwTxRx'], bins=M_dis, retbins=True)[1]
    dn_bins = pd.cut(df_oof['DN'], bins=M_alt, retbins=True)[1]

    # Assign bin labels back to the DataFrame.
    df_oof['dist_grid'] = pd.cut(df_oof['disBtwTxRx'], bins=dist_bins, labels=False, include_lowest=True)
    df_oof['dn_grid'] = pd.cut(df_oof['DN'], bins=dn_bins, labels=False, include_lowest=True)

    # Compute the mean K and sign values for each grid cell.
    # K_table records the average error in multiples of sigma for the environment.
    # Sign_table records overestimate/underestimate consistency from -1 to 1.
    k_table = df_oof.groupby(['dn_grid', 'dist_grid'])['K_actual'].mean()
    sign_table = df_oof.groupby(['dn_grid', 'dist_grid'])['Bias_Sign'].mean()

    # 3. Process the test data.
    # Compute statistics across the 30 models for the test set.
    test_model_cols = ['Model_' + str(i) for i in range(numNetworks)]
    test_preds_matrix = rxData_Altitude_TL[test_model_cols].values

    test_median = np.median(test_preds_matrix, axis=1)
    test_std = np.std(test_preds_matrix, axis=1)

    # Identify the grid cell containing each test point.
    test_dist_grid = pd.cut(rxData_Altitude_TL['disBtwTxRx'], bins=dist_bins, labels=False, include_lowest=True).values
    test_dn_grid = pd.cut(rxData_Altitude_TL['DN'], bins=dn_bins, labels=False, include_lowest=True).values

    correctedPredictionValue = test_median.copy()

    # 4. Apply asymmetric compensation.
    for i in range(len(rxData_Altitude_TL)):
        g_dn = test_dn_grid[i]
        g_dist = test_dist_grid[i]

        # Ensure the cell index exists in case a test point lies outside the training bounds.
        if (g_dn, g_dist) in sign_table.index:
            k_val = k_table[(g_dn, g_dist)]
            s_val = sign_table[(g_dn, g_dist)]

            # Core strategy: compensate only when the absolute sign consistency exceeds the threshold.
            if np.abs(s_val) > 0.75:
                # If s_val > 0.5, the region is generally overestimated (Median > TV), so subtract the bias.
                # If s_val < -0.5, the region is generally underestimated (Median < TV), so add the bias.
                # Correction formula: Corrected = Median - (Sign_Direction * K * Sigma).
                # Bias_Sign is defined as Median - TV, so compensation subtracts this bias.
                correction = s_val * k_val * test_std[i]
                correctedPredictionValue[i] = test_median[i] - correction

    return correctedPredictionValue



def algo_FV_randomForestRegressor_residuals(judgeModelInfo, testData, rxData_Altitude_TL):
    """
    Train a random-forest judge model.

    FV: Feature vector with shape (W, L, C, N_samples).
    TV: Ground-truth RSSI with shape (1, N_samples) or (N_samples,).
    """
    def get_adaptive_params(n_samples):
        # Base configuration.
        params = {
            'n_jobs': -1,
            'random_state': 42
        }

        if n_samples < 200:
            # Very small dataset: use a highly conservative configuration.
            params['n_estimators'] = 200
            params['max_depth'] = 4
            params['min_samples_leaf'] = 5
        elif n_samples < 1000:
            # Medium-sized dataset: balance bias and model complexity.
            params['n_estimators'] = 100
            params['max_depth'] = 10
            params['min_samples_leaf'] = 2
        else:
            # Larger dataset: allow greater model complexity.
            params['n_estimators'] = 100
            params['max_depth'] = None # Allow unrestricted tree depth.
            params['min_samples_leaf'] = 1

        return params

    # 1. Transpose FV to (N_samples, W, L, C), then flatten it to (N_samples, Features).
    # The judge uses environmental features to determine the correction.
    FV = judgeModelInfo['debug_data']['FV']  # Stored feature vector.
    TV = judgeModelInfo['debug_data']['TV']  # Ground-truth RSSI values.
    numNetworks = judgeModelInfo['debug_data']['OOF'].shape[1]  # Number of expert models.
    model_cols = ['Model_' + str(i) for i in range(numNetworks)]
    predictValues = rxData_Altitude_TL[model_cols].values

    X_input = np.transpose(FV, (3, 0, 1, 2))
    N_samples = X_input.shape[0]
    X_flat = X_input.reshape(N_samples, -1) # Flatten features for the random forest.

    # Ensure TV is one-dimensional.
    y_true = np.squeeze(TV)

    # 2. Obtain predictions from the 30 experts on the fine-tuning data.
    predictedMatrix = judgeModelInfo['debug_data']['OOF']
    median_predictions = np.median(predictedMatrix, axis=1)

    # 3. Construct the residual targets.
    # Residual = ground truth - median prediction.
    # A +5 residual means the median is 5 dB too low; -5 means it is 5 dB too high.
    residuals = y_true - median_predictions

    # 4. Train the random-forest regressor.
    print("Training residual correction model (Random Forest Regressor)...")

    # Reuse the adaptive-parameter logic with a regressor.
    # For regression, max_depth may be slightly deeper or unrestricted.
    adaptive_params = get_adaptive_params(N_samples)
    judge_model = RandomForestRegressor(**adaptive_params)

    # Learn the mapping from environmental features to the required dB correction.
    judge_model.fit(X_flat, residuals)

    # 5. Evaluate performance on the fine-tuning set.
    # Final prediction = median prediction + correction.
    train_corrections = judge_model.predict(X_flat)
    final_train_preds = median_predictions + train_corrections

    new_mae = np.mean(np.abs(final_train_preds - y_true))
    old_mae = np.mean(np.abs(median_predictions - y_true))

    print("Correction model training completed.")
    print(f"Fine-tuning set original median MAE: {old_mae:.4f}")
    print(f"Fine-tuning set corrected MAE: {new_mae:.4f}")


    print("Applying prediction correction with judge_model...")
    test_input = np.transpose(testData, (3, 0, 1, 2))
    test_N_samples = test_input.shape[0]
    test_input_flat = test_input.reshape(test_N_samples, -1) # Flatten features for the random forest.
    correction = judge_model.predict(test_input_flat)
    current_median = np.median(predictValues, axis=1)
    final_rssi = current_median + correction
    print("Prediction correction completed.")

    return np.array(final_rssi)




if __name__ == "__main__":
    # Retain command-line invocation support.
    import sys
    # Command-line argument parsing logic.
    run_main_judge_cnn()
