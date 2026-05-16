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


def save_oof_to_csv(oof_predict_matrix, y_all, filename="oof_analysis.csv"):
    """
    oof_predict_matrix: (N, 30) 的 NumPy 数组
    y_all: (N,) 或 (N, 1) 的真实 RSSI 数组
    """
    # 1. 构造列名
    num_models = oof_predict_matrix.shape[1]
    model_cols = [f'expert_{i}' for i in range(num_models)]
    
    # 2. 转为 DataFrame
    df_oof = pd.DataFrame(oof_predict_matrix, columns=model_cols)
    
    # 3. 加入真实值和中位数作为参考
    df_oof['True_RSSI'] = y_all.flatten()
    df_oof['Median_Prediction'] = np.median(oof_predict_matrix, axis=1)
    
    # 4. 计算中位数的绝对误差 (MAE)
    df_oof['Median_Abs_Error'] = np.abs(df_oof['Median_Prediction'] - df_oof['True_RSSI'])
    
    # 5. 找到每个样本点上表现最好的专家编号和对应的最小误差
    errors_matrix = np.abs(oof_predict_matrix - y_all.reshape(-1, 1))
    df_oof['Best_Expert_Idx'] = np.argmin(errors_matrix, axis=1)
    df_oof['Best_Expert_Error'] = np.min(errors_matrix, axis=1)
    
    # 保存
    df_oof.to_csv(filename, index=False)
    print(f">>> OOF 分析文件已保存至: {filename}")
    
    return df_oof


def find_most_balanced_groups(expert_errors, Amin=4, Amax=10):
    results = []
    
    for k in range(Amin, Amax + 1):
        km = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels = km.fit_predict(expert_errors)
        counts = np.bincount(labels)
        
        # 指标1：计算人数的标准差（越小越平衡）
        std_val = np.std(counts)
        # 指标2：最小组的人数
        min_size = np.min(counts)
        
        results.append({
            'k': k,
            'std': std_val,
            'min_size': min_size,
            'labels': labels,
            'counts': counts
        })

    # 决策逻辑：
    # 1. 优先筛选出最小组人数 > 1 的方案（拒绝孤儿专家）
    valid_options = [r for r in results if r['min_size'] > 1]
    
    # 2. 如果都有孤儿组，就用全部方案；否则只从有效方案里选
    pool = valid_options if valid_options else results
    
    # 3. 从候选池中选择标准差最小（最平均）的方案
    best_res = min(pool, key=lambda x: x['std'])
    
    return best_res['labels'], best_res['k']


def train_judge_cnn(X_all, oof_predict_matrix, y_all, input_shape):
    """
    X_all: (N, 31, 36, 5) 地图特征
    oof_predict_matrix: (N, 30) 专家在生题考试中的预测值
    y_all: (N,) 真实RSSI值
    """
    
    # 1. 【专家聚类】将30个专家划分为7个特长小组
    # 特征：专家在1000个点上的误差分布
    expert_errors = oof_predict_matrix.T - y_all.reshape(1, -1)

    # 自动在 4-10 组之间找最平衡的方案
    expert_group_map, num_groups = find_most_balanced_groups(expert_errors, Amin=4, Amax=10)

    print(f">>> 动态确定的最佳分组数: {num_groups}")
    print(f">>> 最终专家分布: {np.bincount(expert_group_map)}")

    # 2. 【标签转换】为每个样本点找到“最佳专家组”
    # 计算每个小组在每个样本点上的平均绝对误差
    group_errors = np.zeros((X_all.shape[0], num_groups))
    for g in range(num_groups):
        members = np.where(expert_group_map == g)[0]
        # 计算该组所有专家的平均误差
        group_errors[:, g] = np.mean(np.abs(oof_predict_matrix[:, members] - y_all.reshape(-1, 1)), axis=1)
    
    # 裁判的新目标：预测这 7 个组里哪个最准
    best_group_labels = np.argmin(group_errors, axis=1)

    # 3. 【构建架构】针对 1000 样本优化的轻量级 CNN
    model = models.Sequential([
        # 第一层卷积：使用 5x5 核捕捉更大范围的地形特征
        layers.Conv2D(32, (5, 5), padding='same', input_shape=input_shape),
        layers.BatchNormalization(),
        layers.Activation('relu'),
        layers.MaxPooling2D((2, 2)),

        # 第二层卷积
        layers.Conv2D(64, (3, 3), padding='same'),
        layers.BatchNormalization(),
        layers.Activation('relu'),
        layers.MaxPooling2D((2, 2)),

        # 第三层：深层提取
        layers.Conv2D(64, (3, 3), padding='same'),
        layers.BatchNormalization(),
        layers.Activation('relu'),

        # 全局平均池化：这是防止过拟合的神器，它让模型关注整体地形而非局部像素
        layers.GlobalAveragePooling2D(),
        
        # 极小的全连接层
        layers.Dense(64, activation='relu', kernel_regularizer=regularizers.l2(0.05)),
        layers.Dropout(0.7), 
        
        # 输出层：7分类（对应7个小组）
        layers.Dense(num_groups, activation='softmax')
    ])

    # 4. 【编译】使用低学习率
    model.compile(
        optimizer=optimizers.Adam(learning_rate=0.0001),
        loss='sparse_categorical_crossentropy',
        metrics=['accuracy']
    )

    # 5. 【训练配置】
    early_stop = callbacks.EarlyStopping(
        monitor='val_loss', 
        patience=40, 
        restore_best_weights=True
    )
    reduce_lr = callbacks.ReduceLROnPlateau(
        monitor='val_loss', 
        factor=0.5, 
        patience=20, 
        min_lr=1e-6
    )

    # --- 新增：数据增强与数据集拆分 ---
    # 1. 拆分数据集 (1000个样本，80%训练，20%验证)
    X_train, X_val, y_train, y_val = train_test_split(
        X_all, best_group_labels, test_size=0.2, random_state=42
    )

    # 2. 定义增强器
    datagen = ImageDataGenerator(
        width_shift_range=0.05,  # 左右随机平移10%
        height_shift_range=0.05, # 上下随机平移10%
        horizontal_flip=False,   # 水平翻转地图
        fill_mode='nearest'     # 填充边缘
    )

    print(">>> 启动带实时数据增强的专家组分类器训练...")

    print(">>> 启动专家组分类器训练...")
    model.fit(
        datagen.flow(X_train, y_train, batch_size=16),
        validation_data=(X_val, y_val), # 验证集保持原样，不进行增强
        epochs=1200, 
        callbacks=[early_stop, reduce_lr], 
        verbose=1
    )
    
    return model, expert_group_map


def predict_with_judge(X_test, m1_experts, judge_cnn):
    """
    m1_experts: 30个微调后的正式模型列表
    """
    # 1. 裁判先给出 7 个小组的胜率
    group_probs = judge_cnn.predict(X_test) # (N, 7)
    
    # 2. 获取聚类映射
    group_map = judge_cnn.expert_group_map
    
    final_predictions = []
    
    # 3. 遍历每个样本点进行软投票（Soft Voting）
    for i in range(len(X_test)):
        sample_res = 0
        for g in range(5):
            # 找到属于该组的所有专家索引
            members = np.where(group_map == g)[0]
            # 计算该组专家的预测中位数
            group_median = np.median([m1_experts[m].predict(X_test[i:i+1]) for m in members])
            # 根据裁判给出的概率加权
            sample_res += group_probs[i, g] * group_median
        final_predictions.append(sample_res)
        
    return np.array(final_predictions)



def train_residual_regressor_cnn(X_all, oof_predict_matrix, y_all, input_shape):
    """
    X_all: (N, 31, 36, 5) 地图特征
    oof_predict_matrix: (N, 30) 专家预测值
    y_all: (N,) 真实RSSI值
    """
    
    # 1. 【目标重塑】计算残差 (Residual)
    # 中位数是目前最稳的基准，我们让 CNN 学习中位数漏掉的“局部特征损耗”
    median_predictions = np.median(oof_predict_matrix, axis=1)
    residuals = y_all - median_predictions  # 目标：真实值 - 中值
    
    print(f">>> 残差分析: 均值={np.mean(residuals):.4f}, 标准差={np.std(residuals):.4f}")
    
    # 2. 【构建回归架构】
    # 与分类器不同，回归器需要更敏感的激活函数和线性输出
    model = models.Sequential([
        # 第一层：大卷积核捕捉地形轮廓
        layers.Conv2D(32, (5, 5), padding='same', input_shape=input_shape),
        layers.BatchNormalization(),
        layers.Activation('elu'), # 使用 ELU 替代 ReLU，对负值残差更友好
        layers.MaxPooling2D((2, 2)),

        # 第二层
        layers.Conv2D(64, (3, 3), padding='same'),
        layers.BatchNormalization(),
        layers.Activation('elu'),
        layers.MaxPooling2D((2, 2)),

        # 第三层：提取深层环境特征
        layers.Conv2D(64, (3, 3), padding='same'),
        layers.BatchNormalization(),
        layers.Activation('elu'),

        # 全局平均池化
        layers.GlobalAveragePooling2D(),
        
        # 全连接层：增加神经元数量，用于拟合复杂的残差波动
        layers.Dense(128, activation='elu', kernel_regularizer=regularizers.l2(0.01)),
        layers.Dropout(0.4), 
        
        # 输出层：单个神经元，线性激活 (Linear)，直接输出残差 dB 值
        layers.Dense(1, activation='linear') 
    ])

    # 3. 【编译】使用 MSE 损失函数
    # 回归任务对学习率较敏感，初始值设为 0.0005
    model.compile(
        optimizer=optimizers.Adam(learning_rate=0.0005),
        loss='mse',      # 均方误差
        metrics=['mae']  # 监控平均绝对误差
    )

    # 4. 【训练配置】
    # 增加 patience，因为残差学习需要更精细的收敛过程
    early_stop = callbacks.EarlyStopping(
        monitor='val_loss', 
        patience=60, 
        restore_best_weights=True
    )
    reduce_lr = callbacks.ReduceLROnPlateau(
        monitor='val_loss', 
        factor=0.5, 
        patience=25, 
        min_lr=1e-7
    )

    # 5. 【拆分与训练】
    X_train, X_val, y_train, y_val = train_test_split(
        X_all, residuals, test_size=0.2, random_state=42
    )

    print(">>> 启动 CNN 残差回归器训练 (正在拟合环境偏差)...")
    
    # 注意：回归任务通常不需要过强的位移增强，防止破坏地形与残差的对应关系
    model.fit(
        X_train, y_train,
        validation_data=(X_val, y_val),
        epochs=1500, 
        batch_size=32,
        callbacks=[early_stop, reduce_lr], 
        verbose=1
    )
    
    return model



def get_correlation_distance_approach(judgeReport, testData, multiModelPredictRSSI, dcor=50, k_neighbors=1):
    """
    升级版：基于局部共识投票的空间相关性策略
    
    k_neighbors: 最多考虑周围多少个邻居进行投票
    """
    # 1. 坐标投影
    lat_ref = judgeReport['Latitude'].mean()
    def project_to_meters(df):
        x = df['Longitude'].values * 111320 * np.cos(np.radians(lat_ref))
        y = df['Latitude'].values * 111000
        return np.column_stack((x, y))

    train_coords_m = project_to_meters(judgeReport)
    test_coords_m = project_to_meters(testData)
    
    # 2. 获取参考点的最佳专家 ID
    b_best_experts = judgeReport['Best_Model_Idx'].values.astype(int)
    tree = KDTree(train_coords_m)
    
    # 3. 初始预测值（中位数）
    final_predictions = testData['Predicted_Value'].values.copy()
    
    # 4. 执行多邻居查询
    # k=k_neighbors 查找最近的多个点
    distances, indices = tree.query(test_coords_m, k=k_neighbors, distance_upper_bound=dcor)
    
    # 5. 投票逻辑
    for i in range(len(testData)):
        # 提取当前点的有效邻居索引（排除距离超出 dcor 的点，tree.query 会返回 inf 或 len(train)）
        valid_mask = ~np.isinf(distances[i])
        valid_indices = indices[i][valid_mask]
        
        if len(valid_indices) > 0:
            # 拿到这些邻居推荐的专家 ID
            neighbor_expert_choices = b_best_experts[valid_indices]
            
            # --- 方案 A: 简单多数投票 ---
            # vote_result = Counter(neighbor_expert_choices).most_common(1)[0][0]
            
            # --- 方案 B: 距离加权投票 (更推荐) ---
            # 距离越近权重越大，权重 = 1 / (距离 + 1e-5)
            valid_dists = distances[i][valid_mask]
            weights = 1.0 / (valid_dists + 1e-5)
            
            # 计算每个专家的加权得分
            unique_experts = np.unique(neighbor_expert_choices)
            expert_scores = {exp: 0.0 for exp in unique_experts}
            for exp, w in zip(neighbor_expert_choices, weights):
                expert_scores[exp] += w
            
            # 选出得分最高的专家
            best_voted_expert = max(expert_scores, key=expert_scores.get)
            
            # 检查置信度：如果最高分占比太低，可以选择 fallback
            # total_weight = sum(expert_scores.values())
            # if expert_scores[best_voted_expert] / total_weight > 0.4: ...
            
            final_predictions[i] = multiModelPredictRSSI[i, best_voted_expert]
            print(f"样本 {i}: 使用邻居投票选择专家 {best_voted_expert}，距离 {valid_dists}, 权重 {weights}")
            
    return final_predictions



def train_judge_model_DN_Dis(judge_model, rxData_Altitude_TL, yPredTestMatrix_DL, threshold=0.25):
    """
    置信度门控专家系统
    threshold: 触发专家的信心阈值（因为有30个模型，平均概率是0.033，设置0.2-0.3通常就很强了）
    """
    # 1. 训练模型
    train_features = ['DN', 'disBtwTxRx']
    X_train = judge_model[train_features].values
    y_train = judge_model['Best_Model_Idx'].values.astype(int)
    
    clf = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42, verbose=2)
    clf.fit(X_train, y_train)
    
    # 2. 获取测试集的概率分布 (N_test, 30)
    X_test = rxData_Altitude_TL[train_features].values
    probs = clf.predict_proba(X_test)
    
    # 3. 准备基础预测（先全部填充为中位数预测值）
    # 假设 rxData_Altitude_TL 里已经算好了中位数列 'Median_Prediction'
    final_predictions = np.median(yPredTestMatrix_DL, axis=1)
    
    # 4. 门控决策
    num_test = len(rxData_Altitude_TL)
    expert_triggered_count = 0
    
    for i in range(num_test):
        # 找到概率最高的专家及其概率值
        best_expert_id = np.argmax(probs[i])
        max_prob = probs[i][best_expert_id]
        
        # 门控检查：只有信心超过阈值，才切换专家
        if max_prob >= threshold:
            final_predictions[i] = yPredTestMatrix_DL[i, best_expert_id]
            expert_triggered_count += 1
            
    print(f">>> 门控开启！在 {num_test} 个样本中，有 {expert_triggered_count} 个样本切换到了专家方案。")
    print(f">>> 其余 {num_test - expert_triggered_count} 个样本保持中位数平稳预测。")

    return final_predictions




# 下面是主函数中调用裁判模型的示例，展示了如何将裁判模型集成到整体预测流程中
def train_and_predict_by_judge_model(judgeModelInfo, testData_TL, rxData_Altitude_TL):

    correctedPredictionValue = algo_FV_randomForestRegressor_residuals(judgeModelInfo, testData_TL, rxData_Altitude_TL)



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