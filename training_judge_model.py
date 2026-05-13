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
from tensorflow.keras import layers, models, callbacks, regularizers, optimizers
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

    judge_cnn = train_judge_cnn(X_all, oof_predict_matrix, y_all, input_shape)
    # predict_with_judge(X_test, m1_experts, judge_cnn)

    return judge_cnn


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



def train_judge_cnn(X_all, oof_predict_matrix, y_all, input_shape):
    """
    X_all: (N, 31, 36, 5) 地图特征
    oof_predict_matrix: (N, 30) 专家在生题考试中的预测值
    y_all: (N,) 真实RSSI值
    """
    
    # 1. 【专家聚类】将30个专家划分为7个特长小组
    # 特征：专家在1000个点上的误差分布
    num_groups = 7
    expert_errors = oof_predict_matrix.T - y_all.reshape(1, -1)
    
    kmeans = KMeans(n_clusters=num_groups, random_state=42, n_init=10)
    expert_group_map = kmeans.fit_predict(expert_errors) 
    print(f">>> 专家聚类完成，各组分布: {np.bincount(expert_group_map)}")

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

    # 附加属性：保存映射表，方便预测时还原专家
    model.expert_group_map = expert_group_map
    
    return model


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


if __name__ == "__main__":
    # 保留命令行调用能力
    import sys
    # 解析命令行参数的逻辑...
    run_main_judge_cnn()