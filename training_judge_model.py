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



def run_main_judge_cnn():
    # 读档
    with open("debug.pkl", "rb") as f:
        debug_data = dill.load(f)
    globals().update(debug_data)
    FV = debug_data['FV']
    TV = debug_data['TV']
    X_all = debug_data['X_all']
    y_all = debug_data['y_all']
    oof_predict_matrix = debug_data['OOF']
    input_shape = X_all.shape[1:]

    # save_oof_to_csv(oof_predict_matrix, y_all, filename="oof_analysis.csv")

    # judge_cnn, expert_group_map = train_judge_cnn(X_all, oof_predict_matrix, y_all, input_shape)
    judge_cnn = train_residual_regressor_cnn(X_all, oof_predict_matrix, y_all, input_shape)
    # predict_with_judge(X_test, m1_experts, judge_cnn)

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




if __name__ == "__main__":
    # 保留命令行调用能力
    import sys
    # 解析命令行参数的逻辑...
    run_main_judge_cnn()