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
    # 保存
    df_oof.to_csv(filename, index=False)
    print(f">>> OOF 分析文件已保存至: {filename}")
    return




# 下面是主函数中调用裁判模型的示例，展示了如何将裁判模型集成到整体预测流程中
def train_and_predict_by_judge_model(judgeModelInfo, testData_TL, rxData_Altitude_TL):
    """
    judgeModelInfo记录了所有在微调数据集上训练的30个模型的预测结果，以及每个样本点的相关特征和真实值。这些信息可以用来训练一个裁判模型
        judgeModelInfo = {
            "df_oof": df_oof,#dataframe
            "debug_data": debug_data, #字典
        }
        debug_data = {
            "FV": FV,
            "TV": TV,
            "optionalParams": optionalParams,
            "OOF": oof_predict_matrix,
        }
        judgeModelInfo['debug_data']['OOF'].shape[1]：专家数量。
        df_oof['Model_n']：模型在微调数据集上的预测值，n=0,1,...,29。
        df_oof['RSSI_TV']：模型对应的真实值，即与FV对应的TV值。
        df_oof['Median_Prediction']：N个模型的中位数预测值，作为基准参考。
        df_oof['Median_Abs_Error']：中位数预测值与真实值之间的绝对误差。
        df_oof['Best_Model_Idx']：表现最好的模型的索引。
        df_oof['Best_Model_Error']：最佳模型的预测误差。
        df_oof['Latitude']：纬度坐标。
        df_oof['Longitude']：经度坐标。
        df_oof['RSSI']：采集到的真实值。
        df_oof['DN']：海拔高度。
        df_oof['FresnelR_H']：第一半波长处的菲涅尔绕射参数。
        df_oof['FresnelR_V']：垂直方向的菲涅尔绕射参数。
        df_oof['disBtwTxRx']：发射机与接收机之间的距离。
    testData_TL是用来测试的数据的输入特征向量，FV，31*36*5*N。
    rxData_Altitude_TL是用来测试的数据的相关特征和真实值，包含了Latitude, Longitude, RSSI, DN, FresnelR_H, FresnelR_V, disBtwTxRx等列。
        rxData_Altitude_TL[model_n]：模型在测试数据上的预测值，n=0,1,...,29。
    """

    save_oof_to_csv(judgeModelInfo['df_oof'], "/Users/zhaoou/Downloads/oof_analysis.csv")
    correctedPredictionValue = algo_FV_randomForestRegressor_residuals(judgeModelInfo, testData_TL, rxData_Altitude_TL)
    # correctedPredictionValue = algo_disDN_mapping_sign(judgeModelInfo, testData_TL, rxData_Altitude_TL)



    return correctedPredictionValue


def algo_disDN_mapping_sign(judgeModelInfo, testData, rxData_Altitude_TL):
    """
    非对称剔除策略：基于环境指纹(DN, Distance)进行中位数偏移补偿
    """
    # 1. 获取训练数据 (微调数据集 B 的 OOF 结果)
    numNetworks = judgeModelInfo['debug_data']['OOF'].shape[1]  # 专家数量
    df_oof = judgeModelInfo["df_oof"].copy()
    model_cols = ['Model_' + str(i) for i in range(numNetworks)]

    # 计算训练集的统计量
    df_oof['mean_30'] = df_oof[model_cols].mean(axis=1)
    df_oof['std_30'] = df_oof[model_cols].std(axis=1)
    # K 实际值：误差绝对值 / 标准差
    df_oof['K_actual'] = df_oof['Median_Abs_Error'] / (df_oof['std_30'] + 1e-9)
    # Sign 实际值：(中位数 - 真实值) 的符号。
    # 注意：如果 Median > TV，符号为 +1 (高估)；如果 Median < TV，符号为 -1 (低估)
    df_oof['Bias_Sign'] = np.sign(df_oof['Median_Prediction'] - df_oof['RSSI_TV'])

    # 2. 构建 MxM 环境指纹表 (Lookup Tables)
    # 使用等频或等宽分箱，这里建议使用 judge 数据的范围来定义边界
    M_dis = 100
    M_alt = 20
    dist_bins = pd.cut(df_oof['disBtwTxRx'], bins=M_dis, retbins=True)[1]
    dn_bins = pd.cut(df_oof['DN'], bins=M_alt, retbins=True)[1]

    # 将 bin 标签打回 df
    df_oof['dist_grid'] = pd.cut(df_oof['disBtwTxRx'], bins=dist_bins, labels=False, include_lowest=True)
    df_oof['dn_grid'] = pd.cut(df_oof['DN'], bins=dn_bins, labels=False, include_lowest=True)

    # 计算每个格子的平均 K 值和平均 Sign 值
    # K_table: 记录该环境下平均错了几倍 sigma
    # Sign_table: 记录该环境下高估/低估的一致性（-1 到 1 之间）
    k_table = df_oof.groupby(['dn_grid', 'dist_grid'])['K_actual'].mean()
    sign_table = df_oof.groupby(['dn_grid', 'dist_grid'])['Bias_Sign'].mean()

    # 3. 对测试数据进行处理
    # 计算测试集 30 个模型的统计量
    test_model_cols = ['Model_' + str(i) for i in range(numNetworks)]
    test_preds_matrix = rxData_Altitude_TL[test_model_cols].values
    
    test_median = np.median(test_preds_matrix, axis=1)
    test_std = np.std(test_preds_matrix, axis=1)

    # 匹配测试点所属的格子
    test_dist_grid = pd.cut(rxData_Altitude_TL['disBtwTxRx'], bins=dist_bins, labels=False, include_lowest=True).values
    test_dn_grid = pd.cut(rxData_Altitude_TL['DN'], bins=dn_bins, labels=False, include_lowest=True).values

    correctedPredictionValue = test_median.copy()

    # 4. 执行非对称补偿逻辑
    for i in range(len(rxData_Altitude_TL)):
        g_dn = test_dn_grid[i]
        g_dist = test_dist_grid[i]
        
        # 检查格子索引是否存在（防止测试集超出训练集边界）
        if (g_dn, g_dist) in sign_table.index:
            k_val = k_table[(g_dn, g_dist)]
            s_val = sign_table[(g_dn, g_dist)]
            
            # 核心策略：只有符号一致性绝对值超过 0.25
            if np.abs(s_val) > 0.75:
                # 如果 s_val > 0.5，说明该区域普遍高估(Median > TV)，我们需要减去偏差
                # 如果 s_val < -0.5，说明该区域普遍低估(Median < TV)，我们需要加上偏差
                # 修正公式：Corrected = Median - (Sign_Direction * K * Sigma)
                # 因为 Bias_Sign 定义为 Median - TV，所以补偿应该是 减去 这个偏差
                correction = s_val * k_val * test_std[i]
                correctedPredictionValue[i] = test_median[i] - correction
    
    return correctedPredictionValue



def algo_FV_randomForestRegressor_residuals(judgeModelInfo, testData, rxData_Altitude_TL):
    """
    随机森林裁判训练函数：
    FV: 特征向量 (W, L, C, N_samples)
    TV: 真实RSSI (1, N_samples) 或 (N_samples,)
    """
    def get_adaptive_params(n_samples):
        # 基础配置
        params = {
            'n_jobs': -1,
            'random_state': 42
        }
        
        if n_samples < 200:
            # 极小样本：非常保守
            params['n_estimators'] = 200
            params['max_depth'] = 4
            params['min_samples_leaf'] = 5
        elif n_samples < 1000:
            # 中等样本：平衡
            params['n_estimators'] = 100
            params['max_depth'] = 10
            params['min_samples_leaf'] = 2
        else:
            # 较多样本：允许复杂
            params['n_estimators'] = 100
            params['max_depth'] = None # 允许自由生长
            params['min_samples_leaf'] = 1
            
        return params

    # 1. 准备数据：将 FV 转置为 (N_samples, W, L, C) 并展平为 (N_samples, Features)
    # 裁判需要看环境特征来做决定
    FV = judgeModelInfo['debug_data']['FV']  # 假设这里存了特征向量
    TV = judgeModelInfo['debug_data']['TV']  # 真实RSSI值
    numNetworks = judgeModelInfo['debug_data']['OOF'].shape[1]  # 专家数量
    model_cols = ['Model_' + str(i) for i in range(numNetworks)]
    predictValues = rxData_Altitude_TL[model_cols].values
    
    X_input = np.transpose(FV, (3, 0, 1, 2)) 
    N_samples = X_input.shape[0]
    X_flat = X_input.reshape(N_samples, -1) # 展平特征，供随机森林使用

    # 确保 TV 是一维的
    y_true = np.squeeze(TV)

    # 2. 获取 30 个专家在这些微调数据上的预测结果
    predictedMatrix = judgeModelInfo['debug_data']['OOF']
    median_predictions = np.median(predictedMatrix, axis=1)

    # 3. 【核心修改】构造残差标签
    # 残差 = 真实值 - 中位数预测值
    # 如果残差是 +5，说明中位数估低了；如果是 -5，说明中位数估高了
    residuals = y_true - median_predictions

    # 4. 训练随机森林回归器 (Regressor)
    print("正在训练残差修正模型 (Random Forest Regressor)...")

    # 这里的参数可以沿用之前的 get_adaptive_params 逻辑，但模型换成 Regressor
    # 对于回归，max_depth 可以稍微设深一点点，或者不设
    adaptive_params = get_adaptive_params(N_samples)
    judge_model = RandomForestRegressor(**adaptive_params)

    # 学习：环境特征 -> 应该修正多少分贝
    judge_model.fit(X_flat, residuals)

    # 5. 评估微调集上的效果
    # 最终预测 = 中位数 + 修正值
    train_corrections = judge_model.predict(X_flat)
    final_train_preds = median_predictions + train_corrections
    
    new_mae = np.mean(np.abs(final_train_preds - y_true))
    old_mae = np.mean(np.abs(median_predictions - y_true))
    
    print(f"修正模型训练完成。")
    print(f"微调集原始中位数 MAE: {old_mae:.4f}")
    print(f"微调集修正后 MAE: {new_mae:.4f}")


    print("正在使用 judge_model 进行预测修正...")
    test_input = np.transpose(testData, (3, 0, 1, 2)) 
    test_N_samples = test_input.shape[0]
    test_input_flat = test_input.reshape(test_N_samples, -1) # 展平特征，供随机森林使用
    correction = judge_model.predict(test_input_flat)
    current_median = np.median(predictValues, axis=1)
    final_rssi = current_median + correction
    print("预测修正完成。")

    return np.array(final_rssi)




if __name__ == "__main__":
    # 保留命令行调用能力
    import sys
    # 解析命令行参数的逻辑...
    run_main_judge_cnn()