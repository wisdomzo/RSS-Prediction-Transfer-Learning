import lzma
import numpy as np
import pickle
import concurrent.futures
import tensorflow as tf
import matplotlib.pyplot as plt
from tensorflow.keras import layers, models
from tensorflow.keras.layers import Lambda
from keras.saving import register_keras_serializable
from tensorflow.keras.utils import plot_model
from tensorflow.python.ops.distributions.util import same_dynamic_shape
from tensorflow.keras.callbacks import ReduceLROnPlateau
import multiprocessing
import threading
import json
import sys
import my_plot_figure
import os
from tqdm import tqdm
import subFun
import socket
from sklearn.ensemble import RandomForestRegressor
import joblib
import numpy as np
from tensorflow.keras import layers, models, callbacks, regularizers, optimizers
from sklearn.model_selection import KFold
from dask.distributed import get_client, as_completed
import dill
import training_judge_model
import gc
import pandas as pd

class ProgressBarWithPID(tf.keras.callbacks.Callback):
    def on_train_begin(self, logs=None):
        # 获取进程ID
        self.process_id = os.getpid()
        # 初始化进度条
        self.progress_bar = tqdm(total=self.params['epochs'], desc=f"Process {self.process_id} Progress", unit="epoch")

    def on_epoch_end(self, epoch, logs=None):
        # 更新进度条
        self.progress_bar.update(1)

    def on_train_end(self, logs=None):
        # 训练结束，关闭进度条
        self.progress_bar.close()



def readDataForDL(dataPath, K):
    with lzma.open(dataPath, 'rb') as saveFile:
        dataStrick = pickle.load(saveFile)
    data_FV = dataStrick['FV']
    data_TV = dataStrick['TV']
    data_rxData_Altitude = dataStrick['rxData_Altitude']
    data_cityType = dataStrick['cityType']
    exM = dataStrick['exM']
    M = dataStrick['M']
    N = dataStrick['N']
    frequency_MHz = dataStrick['frequency_MHz']
    lambda_value = 3e8 / (dataStrick['frequency_MHz'] * 10 ** 6)
    Pt = 10 ** (0.1 * dataStrick['Pt_dBm'])
    numSample = data_FV.shape[1]
    SF = dataStrick['SF']

    origFV = np.zeros((N, exM, K, numSample), dtype=float)
    for count in range(numSample):
        origFV[:,:,0,count] = np.reshape(data_FV[:,count], (N, exM)) #海拔+建筑物高度
        origFV[:,:,1,count] = get_gradient(count, data_rxData_Altitude, M, origFV[:,:,0,count]) #梯度
        origFV[:,:,2,count] = np.reshape(data_cityType[:, count], (N, exM)) #城市类型
        origFV[:,:,3,count] = frequency_MHz * np.ones((N, exM), dtype=float) #frequency
        origFV[:,:,4,count] = data_rxData_Altitude['disBtwTxRx'][count]/(M - 1) * np.ones((N, exM), dtype=float) #步长
    origTV = data_TV
    origRxData_Altitude = data_rxData_Altitude
    return origFV, origTV, origRxData_Altitude, lambda_value, Pt, exM, N



def get_gradient(count, data_rxData_Altitude, M, h_surface):
    # 1. 获取当前样本的总距离和采样点数
    total_dist = data_rxData_Altitude['disBtwTxRx'][count]
    
    # 2. 计算真实的物理步长 (单位：米/点)
    # 这样计算出的梯度单位是 (高度差/距离差)，即真实的坡度 tan(θ)
    current_spacing = total_dist / (M - 1)

    # 3. 计算原始梯度 (h_diff / d_diff)
    grad_raw = np.gradient(h_surface, current_spacing, axis=1)

    # 4. 限制极值：使用 arctan 转换为坡度角 (弧度)
    # 范围被限制在 [-pi/2, pi/2] 之间，约 [-1.57, 1.57]
    grad_arctan = np.arctan(grad_raw)

    # 可选：如果希望模型更容易处理，可以归一化到 [-1, 1]
    grad_norm = grad_arctan / (np.pi / 2)

    return grad_norm


def selectProperty(markVector, FV):
    markVector = np.array(markVector)
    numProperty = sum(markVector)
    sizeVector = FV.shape
    N = sizeVector[0]
    M = sizeVector[1]
    D = sizeVector[2]
    numSample = sizeVector[3]

    selectedFV = np.zeros((N, M, numProperty, numSample), dtype=float)
    for indSample in range(numSample):
        tempFV = FV[:,:,:, indSample]
        indices_to_remove = np.where(markVector == 0)[0]
        tempFV = np.delete(tempFV, indices_to_remove, axis = 2)
        selectedFV[:,:,:, indSample] = tempFV

    return selectedFV, numProperty


def evaLinearPredict(rxData_Altitude, trainIndex, trainFre, testDistance, testFre):
    trainData = rxData_Altitude.iloc[trainIndex,:]
    x = np.log10(trainData['disBtwTxRx'].values)
    y = trainData['RSSI'].values
    z = np.log10(trainFre)
    xz = np.column_stack([x, z, np.ones_like(x)])
    coefficients, _, _, _ = np.linalg.lstsq(xz, y, rcond=None)
    predictRSSI = coefficients[0] * np.log10(testDistance) + coefficients[1] * np.log10(testFre) + coefficients[2]
    #单个变量拟合
    degree = 1  # 设置拟合的多项式阶数，这里为1表示线性拟合
    #coefficients = np.polyfit(x, y, degree)
    #predictRSSI = np.polyval(coefficients, np.log10(testDistance))
    return predictRSSI, coefficients


def run_in_parallel_linear(predictRSSI_linear, numNetworks, rxData_Altitude_forTraining, machineLearningData, testDistance, testFre):
    with concurrent.futures.ProcessPoolExecutor() as executor:
        # 创建任务
        futures = {
            executor.submit(evaLinearPredict,
                            rxData_Altitude_forTraining, machineLearningData[nw]['trainIndex'], machineLearningData[nw]['trainData'][0,0,3,:], testDistance, testFre): nw
            for nw in range(numNetworks)
        }
        # 获取结果并存储到 predictRSSI
        for future in concurrent.futures.as_completed(futures):
            nw = futures[future]
            try:
                result = future.result()
                predictRSSI_linear[nw]['value'] = result[0]  # 将结果保存到对应的索引
                predictRSSI_linear[nw]['weight'] = result[1]
            except Exception as e:
                print(f"Network {nw} generated an exception: {e}")
    return predictRSSI_linear


def run_in_parallel_TL(predictRSSI_TL, numNetworks, machineLearningData, historyModels, numCore1, numCore2, numCore3, learning_type=None, api_instance=None, freeze_layer=None, learning_rate=None):
    # 创建共享队列
    with concurrent.futures.ProcessPoolExecutor() as executor:
        if historyModels is not None:
            # 200: 2个batch_size
            repNum = int(np.ceil( 200 / (machineLearningData[0]['trainRulData'].shape[0] + machineLearningData[0]['valRulData'].shape[0]) ))
            futures = {
                executor.submit(evaDeepLearningPredict,
                                np.transpose(np.tile(machineLearningData[nw]['trainData'], (1,1,1,repNum)), (3, 0, 1, 2)),
                                np.tile(machineLearningData[nw]['trainRulData'], (repNum, 1)),
                                np.transpose(np.tile(machineLearningData[nw]['valData'], (1,1,1,repNum)), (3, 0, 1, 2)),
                                np.tile(machineLearningData[nw]['valRulData'], (repNum, 1)),
                                historyModels[nw]['model'],
                                numCore1,
                                numCore2,
                                numCore3,
                                learning_type,
                                None,
                                None,
                                freeze_layer, 
                                learning_rate
                                ): nw for nw in range(numNetworks)
            }
        else:
            # 创建任务
            futures = {
                executor.submit(evaDeepLearningPredict,
                                np.transpose(machineLearningData[nw]['trainData'], (3, 0, 1, 2)),
                                machineLearningData[nw]['trainRulData'],
                                np.transpose(machineLearningData[nw]['valData'], (3, 0, 1, 2)),
                                machineLearningData[nw]['valRulData'],
                                None,
                                numCore1,
                                numCore2,
                                numCore3,
                                None,
                                None,
                                None,
                                None,
                                None
                                ): nw for nw in range(numNetworks)
            }

        # 获取结果并存储到 predictRSSI
        for future in concurrent.futures.as_completed(futures):
            nw = futures[future]
            try:
                result = future.result()
                predictRSSI_TL[nw]['model'] = result  # 将结果保存到对应的索引
            except Exception as e:
                import traceback
                print(f"Network {nw} failed with error:\n{traceback.format_exc()}")
                #print(f"Network {nw} generated an exception: {e}")
    
    # 4. 训练结束，停止监听线程
    return predictRSSI_TL




@register_keras_serializable(package="CustomLayers")
class InputPreprocessor(tf.keras.layers.Layer):
    def __init__(self, num_classes=27, embedding_dim=8, **kwargs):
        super().__init__(**kwargs)
        self.num_classes = num_classes
        self.embedding_dim = embedding_dim

    def build(self, input_shape):
        # 显式初始化Embedding层（可训练权重）
        self.embedding = tf.keras.layers.Embedding(
            input_dim=self.num_classes,
            output_dim=self.embedding_dim
        )
        super().build(input_shape)  # 标记层为"已构建"

    def call(self, inputs):
        # 其他逻辑不变...
        numerical_1 = inputs[..., 0:1] # 标高+建筑物高度
        numerical_2 = inputs[..., 1:2] # 梯度
        categorical = inputs[..., 2:3] # landuse
        numerical_3 = inputs[..., 3:4] # frequency
        numerical_4 = inputs[..., 4:5] # 步长

        categorical = tf.squeeze(categorical, axis=-1)
        categorical = tf.cast(categorical, tf.int32)
        categorical = self.embedding(categorical)  # 使用在build()中初始化的Embedding层

        numerical_1 = (numerical_1 - (-500)) / (500 - (-500))
        numerical_2 = numerical_2 / (np.pi / 2)
        numerical_3 = numerical_3 / 1000.0
        numerical_4 = numerical_4 / 1000.0


        return tf.concat([numerical_1, numerical_2, categorical, numerical_3, numerical_4], axis=-1)

    def get_config(self):
        return {"num_classes": self.num_classes, "embedding_dim": self.embedding_dim}



def create_cnn_model(input_shape, numCore1, numCore2, numCore3):
    model = models.Sequential()

    # 1. 输入层（需用Lambda处理复杂操作）
    model.add(layers.InputLayer(shape=input_shape))

    # 在模型中使用Lambda层调用
    model.add(InputPreprocessor(num_classes=27, embedding_dim=8))  # 自包含的层，可序列化

    # --- 优化后的CNN结构 ---
    # 第一组卷积层（横向特征提取）
    model.add(layers.Conv2D(numCore1, (3, 5), padding='same'))  # 非对称核
    model.add(layers.BatchNormalization())
    model.add(layers.LeakyReLU(negative_slope=0.1))
    model.add(layers.MaxPooling2D((2, 2), strides=(2, 1)))  # 保留宽度信息

    # 第二组卷积层（纵向特征提取）
    model.add(layers.Conv2D(numCore2, (5, 3), padding='same'))  # 非对称核
    model.add(layers.BatchNormalization())
    model.add(layers.LeakyReLU(negative_slope=0.1))
    model.add(layers.AveragePooling2D((2, 2), strides=2))

    # 调解网络参数
    # 第三组卷积层（深度特征提取）
    for _ in range(4):  # 从3层增加到4层
        model.add(layers.Conv2D(numCore3, (3, 3), padding='same'))
        model.add(layers.BatchNormalization())
        model.add(layers.LeakyReLU(negative_slope=0.1))

    # 新增第四组（特征精炼）
    model.add(layers.Conv2D(numCore3*2, (3, 5), padding='same'))  # 最终宽核
    model.add(layers.BatchNormalization())
    model.add(layers.LeakyReLU(negative_slope=0.1))
    # 调解网络参数

    # 输出层
    model.add(layers.Dropout(0.6))  # 提高正则化
    model.add(layers.GlobalAveragePooling2D())  # 替代Flatten
    model.add(layers.Dense(1, kernel_regularizer='l2'))  # L2正则

    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=5e-4), 
        loss='mse', 
        metrics=['mae']
    )

    return model


def finalize_finetune_config(model, freeze_layer, learning_rate):
    """
    0: input_preprocessor
    1: conv2d
    2: batch_normalization
    3: leaky_re_lu
    4: max_pooling2d
    5: conv2d_1
    6: batch_normalization_1
    7: leaky_re_lu_1
    8: average_pooling2d
    9: conv2d_2
    10: batch_normalization_2
    11: leaky_re_lu_2
    12: conv2d_3
    13: batch_normalization_3
    14: leaky_re_lu_3
    15: conv2d_4
    16: batch_normalization_4
    17: leaky_re_lu_4
    18: conv2d_5
    19: batch_normalization_5
    20: leaky_re_lu_5
    21: conv2d_6
    22: batch_normalization_6
    23: leaky_re_lu_6
    24: dropout
    25: global_average_pooling2d
    26: dense
    """
    
    # 1. 基础防护：锁定前 14 层（包含 InputPreprocessor 和前两组卷积）
    for i in range(freeze_layer):
        model.layers[i].trainable = False
    
    # 2. 深度微调：开启 15 层及以后
    # 包含卷积、BN 和最后的 Dense 层
    for i in range(freeze_layer, len(model.layers)):
        model.layers[i].trainable = True
    
    # 强制锁定所有 BN 层（包括 15 层以后的）
    for layer in model.layers:
        if isinstance(layer, tf.keras.layers.BatchNormalization):
            layer.trainable = False

    # 3. 检查 InputPreprocessor (第 1 层)
    # 特别注意：为了应对新 Landuse，即便它在前 14 层，也要单独开启
    """
    for layer in model.layers:
        if "InputPreprocessor" in layer.name:
            layer.trainable = True
            print("已特赦开启：InputPreprocessor (用于学习新 Landuse Embedding)")
    """

    # 4. 重新编译：必须使用微小的学习率
    # 针对 35km 这种长距离、大尺度模型，高学习率会瞬间毁掉模型
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=learning_rate), 
        loss='mse', 
        metrics=['mae']
    )
    
    return model


def incremental_training_config(model):
    for layer in model.layers:
        layer.trainable = True
    
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=1e-4), 
        loss='mse', 
        metrics=['mae']
    )

    return model


def evaDeepLearningPredict(trainData, trainRulData, valData, valRulData, input_model, numCore1, numCore2, numCore3, learning_type=None, log_queue=None, api_instance=None, freeze_layer=None, learning_rate=None):

    N, M, K = trainData.shape[1:]
    input_shape = (N, M, K)

    if input_model is None:
        epochsValue = 1000
        mini_batch_size = 64
        early_stopping = tf.keras.callbacks.EarlyStopping(
            monitor = 'val_loss',
            patience = 10,
            min_delta = 0.0, #默认值：设置为 0.0，表示任何降低验证损失的行为都会被视为改善。
            restore_best_weights = True
        )
        # 它的作用是：当 val_loss 停滞时，尝试减小学习率来寻找更优解
        reduce_lr = tf.keras.callbacks.ReduceLROnPlateau(
            monitor = 'val_loss', 
            factor = 0.2,          # 学习率缩小为原来的 1/5 (例如 1e-6 -> 2e-7)
            patience = 5,         # 5个epoch不改善就降息。注意：这个值要小于 EarlyStopping 的 patience
            min_lr = 1e-7,         # 学习率的底线
            verbose = 1
        )
        # 创建CNN模型
        model = create_cnn_model(input_shape, numCore1, numCore2, numCore3)
    else:
        if learning_type == "type_TL":
            epochsValue = 5000
            mini_batch_size = 8
            early_stopping = tf.keras.callbacks.EarlyStopping(
                monitor = 'val_loss',
                patience = 100,
                min_delta = 0.0, #默认值：设置为 0.0，表示任何降低验证损失的行为都会被视为改善。
                restore_best_weights = True
            )
            # 它的作用是：当 val_loss 停滞时，尝试减小学习率来寻找更优解
            reduce_lr = tf.keras.callbacks.ReduceLROnPlateau(
                monitor = 'val_loss', 
                factor = 0.2,          # 学习率缩小为原来的 1/5 (例如 1e-6 -> 2e-7)
                patience = 50,         # 15个epoch不改善就降息。注意：这个值要小于 EarlyStopping 的 patience
                min_lr = 1e-8,         # 学习率的底线
                verbose = 1
            )
            model = finalize_finetune_config(input_model, freeze_layer, learning_rate)
        elif learning_type == "type_IT":
            epochsValue = 5000
            mini_batch_size = 32
            early_stopping = tf.keras.callbacks.EarlyStopping(
                monitor = 'val_loss',
                patience = 100,
                min_delta = 0.0, #默认值：设置为 0.0，表示任何降低验证损失的行为都会被视为改善。
                restore_best_weights = True
            )
            reduce_lr = tf.keras.callbacks.ReduceLROnPlateau(
                monitor = 'val_loss', 
                factor = 0.2,          # 学习率缩小为原来的 1/5 (例如 1e-6 -> 2e-7)
                patience = 50,         # 15个epoch不改善就降息。注意：这个值要小于 EarlyStopping 的 patience
                min_lr = 1e-8,         # 学习率的底线
                verbose = 1
            )
            model = incremental_training_config(input_model)
        # 检查 preModel 的输入形状是否与新数据匹配
        if input_model.input_shape[1:] != input_shape:
            raise ValueError(f"Input shape mismatch! Expected: {input_model.input_shape[1:]}, got: {input_shape}")

    # 设置训练参数
    # validation_freq (default = 1): Only relevant if validation data is provided. Specifies how many training epochs to run before a new validation run is performed, e.g. validation_freq=2 runs validation every 2 epochs.
    validation_frequency = 1

    # 使用自定义的进度条回调
    progress_bar = ProgressBarWithPID()

    model.summary()

    # 训练模型
    model.fit(
        trainData,
        trainRulData,
        batch_size = mini_batch_size,
        epochs = epochsValue,
        validation_data = (valData, valRulData),
        validation_freq = validation_frequency, #default = 1
        shuffle = True,
        callbacks = [early_stopping, reduce_lr, progress_bar],
        verbose = 2   # 设置 verbose = 0，不显示训练信息。= 1 显示进度条。= 2 显示每个 epoch 的日志。
    )

    return model


def show_history_model(dataPath):
    with lzma.open(dataPath, 'rb') as saveFile:
        dataStrick = pickle.load(saveFile)

    numNetworks = dataStrick['numNetworks']
    Pt = dataStrick['Pt']
    lambda_value = dataStrick['lambda_value']
    testDistance = dataStrick['testDistance']
    predictRSSI_linear = dataStrick['predictRSSI_linear']
    predictRSSI_TL = dataStrick['predictRSSI_TL']
    testData = dataStrick['testData']
    testRulData = dataStrick['testRulData']
    print(dataPath + " read done ")

    Pr_free = subFun.cal_Pr_free_show(Pt, testData[0,0,3,:], testDistance, 2)
    realRSSI = Pr_free + testRulData[:, 0]
    yPredTestMatrix_linear = np.zeros((len(realRSSI), numNetworks), dtype=float)
    yPredTestMatrix_DL = np.zeros((len(realRSSI), numNetworks), dtype=float)
    for nw in range(numNetworks):
        yPredTestMatrix_linear[:, nw] = predictRSSI_linear[nw]['value']
        yPredTestMatrix_DL[:, nw] = Pr_free + predictRSSI_TL[nw]['model'].predict(np.transpose(testData, (3, 0, 1, 2)), verbose=2)[:, 0]

    # 计算CDF数据
    sorted_data_linear, cdf_linear = my_plot_figure.compute_cdf(np.abs(realRSSI - np.median(yPredTestMatrix_linear, axis=1)))
    sorted_data_DL, cdf_DL = my_plot_figure.compute_cdf(np.abs(realRSSI - np.median(yPredTestMatrix_DL, axis=1)))

    # 绘制CDF图
    my_plot_figure.plot_and_confirm_cdf(
        sorted_data_linear = sorted_data_linear,
        cdf_linear = cdf_linear,
        sorted_data_DL = sorted_data_DL,
        cdf_DL = cdf_DL,
        default_path='cdf_plot.svg',
        figsize_mm=(80, 56.56),
        fontsize=7,
        linewidth=0.5
    )
    return sorted_data_linear, cdf_linear, sorted_data_DL, cdf_DL


def show_TL_model(dataPath):
    with lzma.open(dataPath, 'rb') as saveFile:
        dataStrick = pickle.load(saveFile)

    numNetworks = dataStrick['numNetworks']
    Pt = dataStrick['Pt']
    testDistance_TL = dataStrick['testDistance_TL']
    try:
        predictRSSI_linear_TL = dataStrick['predictRSSI_linear_TL']
    except NameError:
        pass
    predictRSSI_TL = dataStrick['predictRSSI_TL']
    testData_TL = dataStrick['testData_TL']
    testRulData_TL = dataStrick['testRulData_TL']
    print(dataPath + " read done ")

    Pr_free = subFun.cal_Pr_free_show(Pt, testData_TL[0,0,3,:], testDistance_TL, 2)
    realRSSI = Pr_free + testRulData_TL[:, 0]
    yPredTestMatrix_linear = np.zeros((len(realRSSI), numNetworks), dtype=float)
    yPredTestMatrix_DL = np.zeros((len(realRSSI), numNetworks), dtype=float)
    for nw in range(numNetworks):
        try:
            predictRSSI_linear_TL
            yPredTestMatrix_linear[:, nw] = predictRSSI_linear_TL[nw]['value']
        except NameError:
            pass
        yPredTestMatrix_DL[:, nw] = Pr_free + predictRSSI_TL[nw]['model'].predict(np.transpose(testData_TL, (3, 0, 1, 2)), verbose=2)[:, 0]

    # 计算CDF数据
    sorted_data_linear, cdf_linear = my_plot_figure.compute_cdf(
        np.abs(realRSSI - np.median(yPredTestMatrix_linear, axis=1)))
    sorted_data_DL, cdf_DL = my_plot_figure.compute_cdf(
        np.abs(realRSSI - np.median(yPredTestMatrix_DL, axis=1)))

    # 绘制CDF图
    my_plot_figure.plot_and_confirm_cdf(
        sorted_data_linear=sorted_data_linear,
        cdf_linear=cdf_linear,
        sorted_data_DL=sorted_data_DL,
        cdf_DL=cdf_DL,
        default_path='cdf_plot.svg',
        figsize_mm=(80, 56.56),
        fontsize=7,
        linewidth=0.5
    )
    return sorted_data_linear, cdf_linear, sorted_data_DL, cdf_DL



def show_Predict_model(dataPath):
    with lzma.open(dataPath, 'rb') as saveFile:
        dataStrick = pickle.load(saveFile)

    numNetworks = dataStrick['numNetworks']
    Pt = dataStrick['Pt']
    testDistance_TL = dataStrick['testDistance_TL']
    predictRSSI_TL = dataStrick['predictRSSI_TL']
    judge_model = dataStrick['judge_model']
    expert_group_map = dataStrick['expert_group_map']
    testData_TL = dataStrick['testData_TL']
    rxData_Altitude_TL = dataStrick['rxData_Altitude_TL']
    testRulData_TL = dataStrick['testRulData_TL']
    print(dataPath + " read done ")

    Pr_free = subFun.cal_Pr_free_show(Pt, testData_TL[0,0,3,:], testDistance_TL, 2)
    realRSSI = Pr_free + testRulData_TL[:, 0]
    yPredTestMatrix_DL = np.zeros((testData_TL.shape[-1], numNetworks), dtype=float)
    for nw in range(numNetworks):
        yPredTestMatrix_DL[:, nw] = Pr_free + predictRSSI_TL[nw]['model'].predict(np.transpose(testData_TL, (3, 0, 1, 2)), verbose=2)[:, 0]
        rxData_Altitude_TL['model_'+str(nw)] = np.array(yPredTestMatrix_DL[:, nw])

    sorted_data_DL, cdf_DL = my_plot_figure.compute_cdf(
        np.abs(realRSSI - np.median(yPredTestMatrix_DL, axis=1)))

    rxData_Altitude_TL['Predicted_Value'] = np.median(yPredTestMatrix_DL, axis=1)
    # rxData_Altitude_TL['Predicted_Value_Judge'] = get_top_k_prediction_judge_model(judge_model, testData_TL, yPredTestMatrix_DL)
    rxData_Altitude_TL['Predicted_Value_Judge'] = get_final_rssi_prediction(Pr_free, judge_model, expert_group_map, predictRSSI_TL, testData_TL)
    rxData_Altitude_TL['Uncertainty'] = np.std(yPredTestMatrix_DL, axis=1)
    rxData_Altitude_TL['pathLoss_eta_2'] = Pr_free
    Pr_free_eta_3 = subFun.cal_Pr_free_show(Pt, testData_TL[0,0,3,:], testDistance_TL, 3)
    rxData_Altitude_TL['pathLoss_eta_3'] = Pr_free_eta_3

    return rxData_Altitude_TL, sorted_data_DL, cdf_DL


def get_top_k_prediction_judge_model(judge_model, FV, yPredTestMatrix_DL):

    print("正在使用 judge_model 进行预测修正...")
    X_input = np.transpose(FV, (3, 0, 1, 2)) 
    N_samples = X_input.shape[0]
    X_flat = X_input.reshape(N_samples, -1) # 展平特征，供随机森林使用

    correction = judge_model.predict(X_flat)
    current_median = np.median(yPredTestMatrix_DL, axis=1)
    final_rssi = current_median + correction

    print("预测修正完成。")
    return np.array(final_rssi)


def get_final_rssi_prediction(Pr_free, judge_model, expert_group_map, experts_list, test_data_tl):
    """
    judge_model: 训练好的裁判模型 (CNN)
    expert_group_map: 专家分组映射表
    experts_list: 包含30个微调后的专家模型 predictRSSI_TL
    test_data_tl: 测试集地图特征 (N, 31, 36, 5)
    """
    print(">>> 启动裁判引导的混合专家推理 (MoE Inference)...")
    
    # 1. 裁判给出每个样本点属于各个专家组的概率 P(g)
    # 输入形状调整为 (N, 31, 36, 5)
    test_input = np.transpose(test_data_tl, (3, 0, 1, 2))
    group_probs = judge_model.predict(test_input, verbose=1) # 返回 (N, num_groups)
    
    num_samples = test_input.shape[0]
    num_groups = group_probs.shape[1]

    # 2. 预先获取所有 30 个专家的原始预测值
    # 形状为 (30, N)
    print(">>> 正在汇总 30 位专家的原始意见...")
    all_expert_preds = []
    for nw in range(len(experts_list)):
        # 执行你给出的预测循环
        pred = experts_list[nw]['model'].predict(test_input, verbose=0)[:, 0]
        all_expert_preds.append(pred)
    all_expert_preds = np.array(all_expert_preds)

    # 3. 计算最终加权 RSSI
    G = 1  # 设定你想取的前 G 个组，比如取前 2 名或前 3 名
    final_rssi = np.zeros(num_samples)
    
    print(f">>> 正在执行 Top-{G} 概率融合...")
    for i in range(num_samples):
        # 1. 获取当前样本各组的概率
        current_probs = group_probs[i]

        # 2. 找到概率最大的前 G 个组的索引
        # np.argsort 会从小到大排，用 [-G:] 截取最大的 G 个，再用 [::-1] 倒序
        top_g_indices = np.argsort(current_probs)[-G:][::-1]

        # 3. 提取这 G 个组的概率并进行归一化（使 Top-G 的概率之和重新变为 1）
        # 这一步很关键，否则如果删掉了部分组，总概率不足 1，预测值会整体偏低
        top_g_probs = current_probs[top_g_indices]
        top_g_probs_norm = top_g_probs / np.sum(top_g_probs)

        weighted_sample_res = 0
        for idx, g_idx in enumerate(top_g_indices):
            # 找到属于该组 g_idx 的所有专家索引
            members = np.where(expert_group_map == g_idx)[0]
            
            # 获取该组专家的意见
            group_experts_opinions = all_expert_preds[members, i]
            group_median = np.median(group_experts_opinions)
            
            # 使用重新归一化后的概率进行加权
            weighted_sample_res += top_g_probs_norm[idx] * group_median
            
        final_rssi[i] = weighted_sample_res

    print(">>> 预测完成。")
    return final_rssi + Pr_free


def prediction_area_RSSI(selected_predict_model, contentReadDataIndex):
    with lzma.open(selected_predict_model, 'rb') as saveFile:
        dataStrick_model = pickle.load(saveFile)
    with lzma.open(contentReadDataIndex, 'rb') as f:
        dataStrick_content = pickle.load(f)

    numNetworks = dataStrick_model['numNetworks']
    Pt = 10**(0.1*dataStrick_content['Pt_dBm'])
    lambda_value = 3e8 / (dataStrick_content['frequency_MHz'] * 10 ** 6)

    print("read data done")

    return


def show_training_network_topology(dataPath):
    with lzma.open(dataPath, 'rb') as saveFile:
        dataStrick = pickle.load(saveFile)

    model = dataStrick['predictRSSI_TL'][0]['model']
    print(model.summary())
    plot_model(
        model,
        to_file='model.pdf',
        show_shapes=True,
        show_dtype=False,
        show_layer_names=True,
        rankdir='TB',  # 图形方向：'TB'垂直 / 'LR'水平
        expand_nested=False,
        dpi=300,
    )

    return


def get_real_ip():
    """获取本机在局域网中的真实 IP，而不是 127.0.0.1"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # 这里并不需要真的拨通，只是为了让系统选择合适的网络接口
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip


def remote_train_wrapper(trainData, trainRulData, valData, valRulData, 
                        history_weights, c1, c2, c3, l_type, input_shape, freeze_layer, learning_rate):
    """
    此函数仅在远程机器运行。它接收数据，调用你原来的训练函数，并返回权重。
    """
    import os, sys
    import subFun_TL
    import tensorflow as tf
    from dask.distributed import Queue
    import numpy as np

    # 1. 接入 A 机定义的队列
    try:
        q = Queue("app_terminal_logs")
        worker_ip = get_real_ip()  # 获取当前 Worker 的 IP 地址

        # 2. 定义重定向类
        class RemoteToGuiLogger:
            def write(self, msg):
                if msg.strip():
                    # 通过队列发送：[IP] 内容
                    q.put(f"[{worker_ip}] {msg.strip()}")
            def flush(self): pass

        # 3. 重定向本进程的 stdout
        sys.stdout = RemoteToGuiLogger()
    except:
        pass # 如果连不上队列，则保持默认输出

    # 1. 确保 Worker 能找到被 upload_file 上传上来的脚本
    # Dask upload_file 通常把文件放在 Worker 的当前工作目录
    current_dir = os.getcwd()
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)

    print(f">>> [Worker] 开始处理训练任务，类型: {l_type}")

    # 2. 预备模型对象
    # 无论是否是迁移学习，我们先在远程节点构建基础结构
    base_model = subFun_TL.create_cnn_model(input_shape, c1, c2, c3)

    # 如果有权重，加载它
    if history_weights is not None:
        base_model.set_weights(history_weights)
    else:
        base_model = None # 如果是全新训练，传 None 让函数内部去新建
    
    # 3. 调用修复后的函数
    trained_model = subFun_TL.evaDeepLearningPredict(
        np.transpose(trainData, (3, 0, 1, 2)),
        trainRulData, 
        np.transpose(valData, (3, 0, 1, 2)),
        valRulData, 
        input_model=base_model, # 这里对应新的参数名
        numCore1=c1, 
        numCore2=c2, 
        numCore3=c3, 
        learning_type=l_type, 
        log_queue=None,
        api_instance=None,
        freeze_layer=freeze_layer,
        learning_rate=learning_rate
    )
    
    # 5. 只返回权重数组（跨机器传输模型对象的唯一安全方式）
    return trained_model.get_weights()



def run_in_parallel_TL_adaptive(predictRSSI_TL, numNetworks, machineLearningData, 
                               historyModels, numCore1, numCore2, numCore3, 
                               learning_type, api_instance, freeze_layer=None, learning_rate=None):
    import subFun_TL
    import numpy as np
    from dask.distributed import get_client, as_completed

    # 1. 探测 Dask 集群状态
    is_distributed = False
    client = None
    try:
        client = get_client()
        workers = client.scheduler_info()['workers']
        if len(workers) > 0:
            is_distributed = True
    except (ValueError, Exception):
        is_distributed = False

    if is_distributed:
        print(f">>> [分布式模式] 正在启动自适应任务管理器，总数: {numNetworks}")
        
        # 建立 任务句柄(Future) 到 索引(nw) 的映射表，方便失败时知道是谁坏了
        future_to_nw = {}

        def submit_task(nw):
            """内部辅助函数：用于提交或重新提交单个索引的任务"""
            weights = None
            if historyModels and historyModels[nw] and historyModels[nw].get('model'):
                repNum = int(np.ceil( 200 / (machineLearningData[0]['trainRulData'].shape[0] + machineLearningData[0]['valRulData'].shape[0]) ))
                trainD = np.tile(machineLearningData[nw]['trainData'], (1,1,1,repNum))
                valD = np.tile(machineLearningData[nw]['valData'], (1,1,1,repNum))
                weights = historyModels[nw]['model'].get_weights()
            else:
                trainD = machineLearningData[nw]['trainData']
                valD = machineLearningData[nw]['valData']
            
            f = client.submit(
                subFun_TL.remote_train_wrapper,
                trainD, machineLearningData[nw]['trainRulData'],
                valD, machineLearningData[nw]['valRulData'],
                weights, numCore1, numCore2, numCore3, 
                learning_type, trainD.shape[:-1], freeze_layer, learning_rate,
                pure=False,
                retries=3  # 基础重试
            )
            return f

        # 2. 初始提交所有任务
        futures_list = []
        for nw in range(numNetworks):
            f = submit_task(nw)
            future_to_nw[f] = nw
            futures_list.append(f)
        
        # 3. 使用 as_completed 动态迭代
        seq = as_completed(futures_list)
        completed_count = 0

        print(">>> 监控器已就绪，正在实时回收计算结果...")

        for future in seq:
            nw_index = future_to_nw.pop(future) # 取出该任务对应的索引
            try:
                # 获取结果
                weights_result = future.result()
                
                # 在 M3 主机上重建模型
                input_shape = machineLearningData[nw_index]['trainData'].shape[:-1]
                model = subFun_TL.create_cnn_model(input_shape, numCore1, numCore2, numCore3)
                model.set_weights(weights_result)
                predictRSSI_TL[nw_index]['model'] = model
                
                completed_count += 1
                print(f"--- [进度] 任务 {nw_index} 完成 ({completed_count}/{numNetworks}) ---")

            except Exception as e:
                # 如果 retries=10 都没救回来，走到了这里
                print(f"!!! [严重错误] 任务 {nw_index} 彻底失败: {str(e)}")
                print(f"!!! 正在为索引 {nw_index} 重新生成新任务并放回队列...")
                
                # 重新提交任务
                new_f = submit_task(nw_index)
                future_to_nw[new_f] = nw_index
                seq.add(new_f) # 将新任务塞进正在运行的迭代器中

    else:
        # --- 保险丝：如果没连上，走你最稳的原生并行逻辑 ---
        print(">>> [单机模式] 远程机未就绪，使用本机 ProcessPoolExecutor...")
        predictRSSI_TL = subFun_TL.run_in_parallel_TL(
            predictRSSI_TL, numNetworks, machineLearningData, 
            historyModels, numCore1, numCore2, numCore3, 
            learning_type, api_instance if api_instance else None,
            freeze_layer, learning_rate
        )
    
    return predictRSSI_TL


def trainJudgeModel(numNetworks, AIcommittee, FV, TV):
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
    X_input = np.transpose(FV, (3, 0, 1, 2)) 
    N_samples = X_input.shape[0]
    X_flat = X_input.reshape(N_samples, -1) # 展平特征，供随机森林使用

    # 确保 TV 是一维的
    y_true = np.squeeze(TV)

    # 2. 获取 30 个专家在这些微调数据上的预测结果
    predictedMatrix = np.zeros((N_samples, numNetworks), dtype=float)
    print("正在收集专家预测结果...")
    for nw in range(numNetworks):
        # 预测并填入矩阵
        preds = AIcommittee[nw]['model'].predict(X_input, verbose=0)
        predictedMatrix[:, nw] = preds.flatten()

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


    '''
    # 临时文件，查看输出csv
    import pandas as pd
    actual_predict_matrix = np.stack(predictedMatrix)
    model_cols = [f'Model_{i}' for i in range(actual_predict_matrix.shape[1])]
    df_models = pd.DataFrame(actual_predict_matrix, columns=model_cols)
    df_models.to_csv('predict_results.csv', index=False)

    actual_RSSI = np.stack(TV).squeeze()
    df_rssi = pd.DataFrame(actual_RSSI, columns=['RSSI']) 
    df_rssi.to_csv('actual_RSSI.csv', index=False)
    '''
    return judge_model


def trainJudgeModel_cnn(numNetworks, historyModels, FV, TV, optionalParams,
                    numCore1, numCore2, numCore3, learning_type, 
                    freeze_layer, learning_rate):
    """
    裁判训练主函数：
    - 外层：5折交叉验证（顺序执行）
    - 内层：30个专家模型（Dask分布式并行）
    - 目标：训练一个 CNN 选人裁判，逼近 0.85dB 的上帝模式
    """
    client = None
    is_distributed = False
    try:
        from dask.distributed import get_client, as_completed
        client = get_client()
        is_distributed = True
        print(">>> [分布式模式] 已连接到 Dask 集群，开始分发并行任务...")
    except (ImportError, ValueError, Exception):
        print(">>> [单机模式] 未检测到 Dask 集群，将按顺序执行微调...")

    # 1. 数据准备
    # X_all: (N, 31, 36, 5), y_all: (N,)
    X_all = np.transpose(FV, (3, 0, 1, 2))
    y_all = np.squeeze(TV)
    n_samples = X_all.shape[0]
    input_shape = X_all.shape[1:]
    
    # 建立 5 折交叉验证
    kf = KFold(n_splits=5, shuffle=True, random_state=42)
    
    # 全样本 OOF (Out-of-Fold) 预测矩阵，用来存专家在生题上的表现
    oof_predict_matrix = np.zeros((n_samples, numNetworks))

    # 2. 外层循环：顺序处理每一折 (Fold)
    for fold_idx, (train_idx, val_idx) in enumerate(kf.split(X_all)):
        print(f"\n>>> 正在处理第 {fold_idx+1}/5 折交叉验证...")
        
        X_train_fold = X_all[train_idx]
        y_train_fold = y_all[train_idx]
        X_exam_fold = X_all[val_idx] # 本折的专家“生题”考试卷
        
        # 内层：分布式并行训练 30 个临时专家
        if is_distributed:
            # --- 路径 A：分布式并行 ---
            future_to_nw = {}
            for nw in range(numNetworks):
                # 获取专家初始权重
                weights = None
                if historyModels and historyModels[nw] and historyModels[nw].get('model'):
                    weights = historyModels[nw]['model'].get_weights()
                
                # 提交 Dask 任务
                f = client.submit(
                    remote_fold_train_predict,
                    X_train_fold, y_train_fold, X_exam_fold,
                    weights, numCore1, numCore2, numCore3,
                    learning_type, input_shape, freeze_layer, learning_rate,
                    pure=False
                )
                future_to_nw[f] = nw
            
            # 回收本折的 30 个专家预测结果
            completed_fold_count = 0
            for future in as_completed(future_to_nw.keys()):
                nw_index = future_to_nw[future]
                try:
                    preds = future.result()
                    oof_predict_matrix[val_idx, nw_index] = preds.flatten()
                    completed_fold_count += 1
                    if completed_fold_count % 10 == 0:
                        print(f"    Fold {fold_idx+1}: 专家 {completed_fold_count}/{numNetworks} 已交卷")
                except Exception as e:
                    print(f"    !!! Fold {fold_idx+1} 专家 {nw_index} 任务失败: {e}")
        else:
            # --- 路径 B：单机顺序执行 ---
            for nw in range(numNetworks):
                weights = historyModels[nw]['model'].get_weights() if historyModels and historyModels[nw] else None
                # 直接调用本地函数
                preds = remote_fold_train_predict(
                    X_train_fold, y_train_fold, X_exam_fold,
                    weights, numCore1, numCore2, numCore3,
                    learning_type, input_shape, freeze_layer, learning_rate
                )
                oof_predict_matrix[val_idx, nw] = preds.flatten()
                if (nw + 1) % 5 == 0:
                    print(f"    单机进度: Fold {fold_idx+1}, 专家 {nw+1}/{numNetworks} 已完成")

    # 4. 训练 CNN 裁判 (识别地形 -> 选出最强专家)
    print("\n>>> [教材整理完毕] 正在训练 CNN 裁判模型...")

    #"""
    debug_data = {
        "FV": FV,
        "TV": TV,
        "optionalParams": optionalParams,
        "X_all": X_all,
        "y_all": y_all,
        "OOF": oof_predict_matrix,
    }
    with open("debug.pkl", "wb") as f:
        dill.dump(debug_data, f)
    #"""

    # judge_cnn, expert_group_map = training_judge_model.train_judge_cnn(X_all, oof_predict_matrix, y_all, input_shape)

    # 构成一个裁判报告单
    model_cols = [f'Model_{i}' for i in range(numNetworks)]
    df_oof = pd.DataFrame(oof_predict_matrix, columns=model_cols)
    df_oof['RSSI'] = y_all.flatten()
    df_oof['Median_Prediction'] = np.median(oof_predict_matrix, axis=1)
    df_oof['Median_Abs_Error'] = np.abs(df_oof['Median_Prediction'] - df_oof['RSSI'])
    errors_matrix = np.abs(oof_predict_matrix - y_all.reshape(-1, 1))
    df_oof['Best_Model_Idx'] = np.argmin(errors_matrix, axis=1)
    df_oof['Best_Model_Error'] = np.min(errors_matrix, axis=1)
    param_cols = optionalParams.columns.tolist()
    df_oof[param_cols] = optionalParams.values

    return df_oof


def remote_fold_train_predict(X_train, y_train, X_exam, weights, numCore1, numCore2, numCore3, l_type, shape, freeze_layer, learning_rate):
    """
    Dask 远程执行：使用与正式微调完全一致的参数训练“临时专家”并参加考试
    """
    
    # 1. 建立基础模型
    # 注意：远程节点必须能调用 create_cnn_model
    model = create_cnn_model(shape, numCore1, numCore2, numCore3)
    if weights is not None:
        model.set_weights(weights)
    
    # 2. 按照 type_TL 逻辑配置微调环境
    if l_type == "type_TL":
        # 2.1 应用你的 finalize_finetune_config 逻辑
        # 锁定/开启层，锁定所有 BN 层，并重新编译
        model = finalize_finetune_config(model, freeze_layer, learning_rate)
        
        # 2.2 配置完全一致的 Callback 体系
        # 注意：因为只有 400 样本左右，所以必须靠 EarlyStopping 找到最佳状态点
        early_stopping = tf.keras.callbacks.EarlyStopping(
            monitor='val_loss',
            patience=100,
            min_delta=0.0,
            restore_best_weights=True,
            verbose=0
        )
        
        reduce_lr = tf.keras.callbacks.ReduceLROnPlateau(
            monitor='val_loss', 
            factor=0.2,
            patience=50,
            min_lr=1e-8,
            verbose=0
        )
        
        # 2.3 执行深度微调
        # 这里使用 X_train 自身的一部分作为验证集，以触发 EarlyStopping
        # 这里的 5000 epoch 和 batch_size=8 与你正式微调一致
        model.fit(
            X_train, y_train,
            validation_split=0.15, # 从 Fold 训练集里再切一点做验证
            epochs=5000,
            batch_size=8,
            callbacks=[early_stopping, reduce_lr],
            verbose=1 # 远程执行建议关闭日志，避免阻塞 Dask 通讯
        )
        
    else:
        # 非 type_TL 模式的基础微调 (作为备选逻辑)
        model.compile(optimizer='adam', loss='mse')
        model.fit(X_train, y_train, epochs=20, batch_size=32, verbose=0)
    
    # 3. 考试：预测没见过的数据 (这就是裁判学习的真实依据)
    # 此时的 model 已经达到了与最终 M1 专家同级别的“实战水平”
    # --- 2. 考试：先拿到结果 ---
    preds = model.predict(X_exam, verbose=0)

    # --- 3. 【关键：在这里关门】 ---
    # 第一步：删除模型引用
    del model

    # 第二步：清理 Keras 后端占用的显存和文件句柄
    # 这会释放 TensorFlow 在这一轮训练中打开的所有底层 H5 临时文件和 C++ 句柄
    tf.keras.backend.clear_session()

    # 第三步：强制 Python 立即回收内存
    gc.collect()

    return preds