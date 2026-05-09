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
    testData_TL = dataStrick['testData_TL']
    rxData_Altitude_TL = dataStrick['rxData_Altitude_TL']
    testRulData_TL = dataStrick['testRulData_TL']
    print(dataPath + " read done ")

    Pr_free = subFun.cal_Pr_free_show(Pt, testData_TL[0,0,3,:], testDistance_TL, 2)
    realRSSI = Pr_free + testRulData_TL[:, 0]
    yPredTestMatrix_DL = np.zeros((testData_TL.shape[-1], numNetworks), dtype=float)
    for nw in range(numNetworks):
        yPredTestMatrix_DL[:, nw] = Pr_free + predictRSSI_TL[nw]['model'].predict(np.transpose(testData_TL, (3, 0, 1, 2)), verbose=2)[:, 0]

    sorted_data_DL, cdf_DL = my_plot_figure.compute_cdf(
        np.abs(realRSSI - np.median(yPredTestMatrix_DL, axis=1)))

    rxData_Altitude_TL['Predicted_Value'] = np.median(yPredTestMatrix_DL, axis=1)
    rxData_Altitude_TL['Uncertainty'] = np.std(yPredTestMatrix_DL, axis=1)
    rxData_Altitude_TL['pathLoss_eta_2'] = Pr_free
    Pr_free_eta_3 = subFun.cal_Pr_free_show(Pt, testData_TL[0,0,3,:], testDistance_TL, 3)
    rxData_Altitude_TL['pathLoss_eta_3'] = Pr_free_eta_3

    return rxData_Altitude_TL, sorted_data_DL, cdf_DL


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