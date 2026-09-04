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

class QueueStream:
    def __init__(self, log_queue):
        self.log_queue = log_queue

    def write(self, message):
        if self.log_queue and message.strip():
            self.log_queue.put(message)

    def flush(self):
        pass


def init_local_training_worker_logging(log_queue):
    if not log_queue:
        return
    sys.stdout = QueueStream(log_queue)
    sys.stderr = QueueStream(log_queue)


class ProgressBarWithPID(tf.keras.callbacks.Callback):
    def on_train_begin(self, logs=None):

        self.process_id = os.getpid()

        self.progress_bar = tqdm(total=self.params['epochs'], desc=f"Process {self.process_id} Progress", unit="epoch")

    def on_epoch_end(self, epoch, logs=None):

        self.progress_bar.update(1)

    def on_train_end(self, logs=None):

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
        origFV[:,:,0,count] = np.reshape(data_FV[:,count], (N, exM))
        origFV[:,:,1,count] = get_gradient(count, data_rxData_Altitude, M, origFV[:,:,0,count])
        origFV[:,:,2,count] = np.reshape(data_cityType[:, count], (N, exM))
        origFV[:,:,3,count] = frequency_MHz * np.ones((N, exM), dtype=float) #frequency
        origFV[:,:,4,count] = data_rxData_Altitude['disBtwTxRx'][count]/(M - 1) * np.ones((N, exM), dtype=float)
    origTV = data_TV
    origRxData_Altitude = data_rxData_Altitude
    return origFV, origTV, origRxData_Altitude, lambda_value, Pt, exM, N



def get_gradient(count, data_rxData_Altitude, M, h_surface):

    total_dist = data_rxData_Altitude['disBtwTxRx'][count]



    current_spacing = total_dist / (M - 1)


    grad_raw = np.gradient(h_surface, current_spacing, axis=1)



    grad_arctan = np.arctan(grad_raw)


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

    degree = 1
    #coefficients = np.polyfit(x, y, degree)
    #predictRSSI = np.polyval(coefficients, np.log10(testDistance))
    return predictRSSI, coefficients


def run_in_parallel_linear(predictRSSI_linear, numNetworks, rxData_Altitude_forTraining, machineLearningData, testDistance, testFre):
    with concurrent.futures.ProcessPoolExecutor() as executor:

        futures = {
            executor.submit(evaLinearPredict,
                            rxData_Altitude_forTraining, machineLearningData[nw]['trainIndex'], machineLearningData[nw]['trainData'][0,0,3,:], testDistance, testFre): nw
            for nw in range(numNetworks)
        }

        for future in concurrent.futures.as_completed(futures):
            nw = futures[future]
            try:
                result = future.result()
                predictRSSI_linear[nw]['value'] = result[0]
                predictRSSI_linear[nw]['weight'] = result[1]
            except Exception as e:
                print(f"Network {nw} generated an exception: {e}")
    return predictRSSI_linear


def run_in_parallel_TL(predictRSSI_TL, numNetworks, machineLearningData, historyModels, numCore1, numCore2, numCore3, learning_type=None, api_instance=None, freeze_layer=None, learning_rate=None):

    log_queue = getattr(api_instance, "queue", None)
    with concurrent.futures.ProcessPoolExecutor(initializer=init_local_training_worker_logging, initargs=(log_queue,)) as executor:
        if historyModels is not None:

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


        for future in concurrent.futures.as_completed(futures):
            nw = futures[future]
            try:
                result = future.result()
                predictRSSI_TL[nw]['model'] = result
            except Exception as e:
                import traceback
                print(f"Network {nw} failed with error:\n{traceback.format_exc()}")
                #print(f"Network {nw} generated an exception: {e}")


    return predictRSSI_TL




@register_keras_serializable(package="CustomLayers")
class InputPreprocessor(tf.keras.layers.Layer):
    def __init__(self, num_classes=27, embedding_dim=8, **kwargs):
        super().__init__(**kwargs)
        self.num_classes = num_classes
        self.embedding_dim = embedding_dim

    def build(self, input_shape):

        self.embedding = tf.keras.layers.Embedding(
            input_dim=self.num_classes,
            output_dim=self.embedding_dim
        )
        super().build(input_shape)

    def call(self, inputs):

        numerical_1 = inputs[..., 0:1]
        numerical_2 = inputs[..., 1:2]
        categorical = inputs[..., 2:3] # landuse
        numerical_3 = inputs[..., 3:4] # frequency
        numerical_4 = inputs[..., 4:5]

        categorical = tf.squeeze(categorical, axis=-1)
        categorical = tf.cast(categorical, tf.int32)
        categorical = self.embedding(categorical)

        numerical_1 = (numerical_1 - (-500)) / (500 - (-500))
        numerical_2 = numerical_2 / (np.pi / 2)
        numerical_3 = numerical_3 / 1000.0
        numerical_4 = numerical_4 / 1000.0


        return tf.concat([numerical_1, numerical_2, categorical, numerical_3, numerical_4], axis=-1)

    def get_config(self):
        return {"num_classes": self.num_classes, "embedding_dim": self.embedding_dim}



def create_cnn_model(input_shape, numCore1, numCore2, numCore3):
    model = models.Sequential()


    model.add(layers.InputLayer(shape=input_shape))


    model.add(InputPreprocessor(num_classes=27, embedding_dim=8))



    model.add(layers.Conv2D(numCore1, (3, 5), padding='same'))
    model.add(layers.BatchNormalization())
    model.add(layers.LeakyReLU(negative_slope=0.1))
    model.add(layers.MaxPooling2D((2, 2), strides=(2, 1)))


    model.add(layers.Conv2D(numCore2, (5, 3), padding='same'))
    model.add(layers.BatchNormalization())
    model.add(layers.LeakyReLU(negative_slope=0.1))
    model.add(layers.AveragePooling2D((2, 2), strides=2))



    for _ in range(4):
        model.add(layers.Conv2D(numCore3, (3, 3), padding='same'))
        model.add(layers.BatchNormalization())
        model.add(layers.LeakyReLU(negative_slope=0.1))


    model.add(layers.Conv2D(numCore3*2, (3, 5), padding='same'))
    model.add(layers.BatchNormalization())
    model.add(layers.LeakyReLU(negative_slope=0.1))



    model.add(layers.Dropout(0.6))
    model.add(layers.GlobalAveragePooling2D())
    model.add(layers.Dense(1, kernel_regularizer='l2'))

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


    for i in range(freeze_layer):
        model.layers[i].trainable = False



    for i in range(freeze_layer, len(model.layers)):
        model.layers[i].trainable = True


    for layer in model.layers:
        if isinstance(layer, tf.keras.layers.BatchNormalization):
            layer.trainable = False



    """
    for layer in model.layers:
        if "InputPreprocessor" in layer.name:
            layer.trainable = True
            print("InputPreprocessor has been unfrozen to learn the new Landuse Embedding.")
    """



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
            min_delta = 0.0,
            restore_best_weights = True
        )

        reduce_lr = tf.keras.callbacks.ReduceLROnPlateau(
            monitor = 'val_loss',
            factor = 0.2,
            patience = 5,
            min_lr = 1e-7,
            verbose = 1
        )

        model = create_cnn_model(input_shape, numCore1, numCore2, numCore3)
    else:
        if learning_type == "type_TL":
            epochsValue = 5000
            mini_batch_size = 8
            early_stopping = tf.keras.callbacks.EarlyStopping(
                monitor = 'val_loss',
                patience = 100,
                min_delta = 0.0,
                restore_best_weights = True
            )

            reduce_lr = tf.keras.callbacks.ReduceLROnPlateau(
                monitor = 'val_loss',
                factor = 0.2,
                patience = 50,
                min_lr = 1e-8,
                verbose = 1
            )
            model = finalize_finetune_config(input_model, freeze_layer, learning_rate)
        elif learning_type == "type_IT":
            epochsValue = 5000
            mini_batch_size = 32
            early_stopping = tf.keras.callbacks.EarlyStopping(
                monitor = 'val_loss',
                patience = 100,
                min_delta = 0.0,
                restore_best_weights = True
            )
            reduce_lr = tf.keras.callbacks.ReduceLROnPlateau(
                monitor = 'val_loss',
                factor = 0.2,
                patience = 50,
                min_lr = 1e-8,
                verbose = 1
            )
            model = incremental_training_config(input_model)

        if input_model.input_shape[1:] != input_shape:
            raise ValueError(f"Input shape mismatch! Expected: {input_model.input_shape[1:]}, got: {input_shape}")


    # validation_freq (default = 1): Only relevant if validation data is provided. Specifies how many training epochs to run before a new validation run is performed, e.g. validation_freq=2 runs validation every 2 epochs.
    validation_frequency = 1


    progress_bar = ProgressBarWithPID()

    model.summary()


    model.fit(
        trainData,
        trainRulData,
        batch_size = mini_batch_size,
        epochs = epochsValue,
        validation_data = (valData, valRulData),
        validation_freq = validation_frequency, #default = 1
        shuffle = True,
        callbacks = [early_stopping, reduce_lr, progress_bar],
        verbose = 2
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


    sorted_data_linear, cdf_linear = my_plot_figure.compute_cdf(np.abs(realRSSI - np.median(yPredTestMatrix_linear, axis=1)))
    sorted_data_DL, cdf_DL = my_plot_figure.compute_cdf(np.abs(realRSSI - np.median(yPredTestMatrix_DL, axis=1)))


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


    sorted_data_linear, cdf_linear = my_plot_figure.compute_cdf(
        np.abs(realRSSI - np.median(yPredTestMatrix_linear, axis=1)))
    sorted_data_DL, cdf_DL = my_plot_figure.compute_cdf(
        np.abs(realRSSI - np.median(yPredTestMatrix_DL, axis=1)))


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
    judge_model = dataStrick.get('judge_model', None)
    testData_TL = dataStrick['testData_TL']
    rxData_Altitude_TL = dataStrick['rxData_Altitude_TL']
    testRulData_TL = dataStrick['testRulData_TL']
    print(dataPath + " read done ")

    Pr_free = subFun.cal_Pr_free_show(Pt, testData_TL[0,0,3,:], testDistance_TL, 2)
    realRSSI = Pr_free + testRulData_TL[:, 0]
    yPredTestMatrix_DL = np.zeros((testData_TL.shape[-1], numNetworks), dtype=float)
    for nw in range(numNetworks):
        yPredTestMatrix_DL[:, nw] = Pr_free + predictRSSI_TL[nw]['model'].predict(np.transpose(testData_TL, (3, 0, 1, 2)), verbose=2)[:, 0]
        rxData_Altitude_TL['Model_'+str(nw)] = np.array(yPredTestMatrix_DL[:, nw])

    sorted_data_DL, cdf_DL = my_plot_figure.compute_cdf(
        np.abs(realRSSI - np.median(yPredTestMatrix_DL, axis=1)))

    rxData_Altitude_TL['Predicted_Value'] = np.median(yPredTestMatrix_DL, axis=1)
    if judge_model is not None:
        rxData_Altitude_TL['Predicted_Value_Judge'] = training_judge_model.train_and_predict_by_judge_model(judge_model, testData_TL, rxData_Altitude_TL)
    else:
        print("No judge model provided, skipping judge-based prediction.")
    rxData_Altitude_TL['Uncertainty'] = np.std(yPredTestMatrix_DL, axis=1)
    rxData_Altitude_TL['pathLoss_eta_2'] = Pr_free
    Pr_free_eta_3 = subFun.cal_Pr_free_show(Pt, testData_TL[0,0,3,:], testDistance_TL, 3)
    rxData_Altitude_TL['pathLoss_eta_3'] = Pr_free_eta_3

    return rxData_Altitude_TL, sorted_data_DL, cdf_DL


def get_top_k_prediction_judge_model(judge_model, FV, yPredTestMatrix_DL):

    print("Applying prediction correction with judge_model...")
    X_input = np.transpose(FV, (3, 0, 1, 2))
    N_samples = X_input.shape[0]
    X_flat = X_input.reshape(N_samples, -1)

    correction = judge_model.predict(X_flat)
    current_median = np.median(yPredTestMatrix_DL, axis=1)
    final_rssi = current_median + correction

    print("Prediction correction completed.")
    return np.array(final_rssi)


def get_final_rssi_prediction(Pr_free, judge_model, expert_group_map, experts_list, test_data_tl):
    """Combine judge-model group probabilities and expert predictions into final RSSI values."""
    print(">>> Starting judge-guided mixture-of-experts inference (MoE Inference)...")



    test_input = np.transpose(test_data_tl, (3, 0, 1, 2))
    group_probs = judge_model.predict(test_input, verbose=1)

    num_samples = test_input.shape[0]
    num_groups = group_probs.shape[1]



    print(">>> Aggregating raw predictions from 30 experts...")
    all_expert_preds = []
    for nw in range(len(experts_list)):

        pred = experts_list[nw]['model'].predict(test_input, verbose=0)[:, 0]
        all_expert_preds.append(pred)
    all_expert_preds = np.array(all_expert_preds)


    G = 1
    final_rssi = np.zeros(num_samples)

    print(f">>> Executing Top-{G} probability fusion...")
    for i in range(num_samples):

        current_probs = group_probs[i]



        top_g_indices = np.argsort(current_probs)[-G:][::-1]



        top_g_probs = current_probs[top_g_indices]
        top_g_probs_norm = top_g_probs / np.sum(top_g_probs)

        weighted_sample_res = 0
        for idx, g_idx in enumerate(top_g_indices):

            members = np.where(expert_group_map == g_idx)[0]


            group_experts_opinions = all_expert_preds[members, i]
            group_median = np.median(group_experts_opinions)


            weighted_sample_res += top_g_probs_norm[idx] * group_median

        final_rssi[i] = weighted_sample_res

    print(">>> Prediction completed.")
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
        rankdir='TB',
        expand_nested=False,
        dpi=300,
    )

    return


def get_real_ip():
    """Return the host's LAN address instead of the loopback address."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:

        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip


def remote_train_wrapper(trainData, trainRulData, valData, valRulData,
                        history_weights, c1, c2, c3, l_type, input_shape, freeze_layer, learning_rate):
    """Train a model on a remote worker and return its weights."""
    import os, sys
    import subFun_TL
    import tensorflow as tf
    from dask.distributed import Queue
    import numpy as np


    try:
        q = Queue("app_terminal_logs")
        worker_ip = get_real_ip()


        class RemoteToGuiLogger:
            def write(self, msg):
                if msg.strip():

                    q.put(f"[{worker_ip}] {msg.strip()}")
            def flush(self): pass


        sys.stdout = RemoteToGuiLogger()
    except:
        pass



    current_dir = os.getcwd()
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)

    print(f">>> [Worker] Starting training task. Type: {l_type}")



    base_model = subFun_TL.create_cnn_model(input_shape, c1, c2, c3)


    if history_weights is not None:
        base_model.set_weights(history_weights)
    else:
        base_model = None


    trained_model = subFun_TL.evaDeepLearningPredict(
        np.transpose(trainData, (3, 0, 1, 2)),
        trainRulData,
        np.transpose(valData, (3, 0, 1, 2)),
        valRulData,
        input_model=base_model,
        numCore1=c1,
        numCore2=c2,
        numCore3=c3,
        learning_type=l_type,
        log_queue=None,
        api_instance=None,
        freeze_layer=freeze_layer,
        learning_rate=learning_rate
    )


    return trained_model.get_weights()



def run_in_parallel_TL_adaptive(predictRSSI_TL, numNetworks, machineLearningData,
                               historyModels, numCore1, numCore2, numCore3,
                               learning_type, api_instance, freeze_layer=None, learning_rate=None):
    import subFun_TL
    import numpy as np
    from dask.distributed import get_client, as_completed


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
        print(f">>> [Distributed mode] Starting adaptive task manager. Total tasks: {numNetworks}")


        future_to_nw = {}

        def submit_task(nw):
            """Submit or resubmit the training task for one network index."""
            weights = None
            if historyModels and historyModels[nw] and historyModels[nw].get('model'):
                repNum = int(np.ceil( 200 / (machineLearningData[0]['trainRulData'].shape[0] + machineLearningData[0]['valRulData'].shape[0]) ))
                trainD = np.tile(machineLearningData[nw]['trainData'], (1,1,1,repNum))
                trainRulD = np.tile(machineLearningData[nw]['trainRulData'], (repNum, 1))
                valD = np.tile(machineLearningData[nw]['valData'], (1,1,1,repNum))
                valRulD = np.tile(machineLearningData[nw]['valRulData'], (repNum, 1))
                weights = historyModels[nw]['model'].get_weights()
            else:
                trainD = machineLearningData[nw]['trainData']
                trainRulD = machineLearningData[nw]['trainRulData']
                valD = machineLearningData[nw]['valData']
                valRulD = machineLearningData[nw]['valRulData']

            f = client.submit(
                subFun_TL.remote_train_wrapper,
                trainD, trainRulD,
                valD, valRulD,
                weights, numCore1, numCore2, numCore3,
                learning_type, trainD.shape[:-1], freeze_layer, learning_rate,
                pure=False,
                retries=3
            )
            return f


        futures_list = []
        for nw in range(numNetworks):
            f = submit_task(nw)
            future_to_nw[f] = nw
            futures_list.append(f)


        seq = as_completed(futures_list)
        completed_count = 0

        print(">>> Monitor is ready and collecting computation results in real time...")

        for future in seq:
            nw_index = future_to_nw.pop(future)
            try:

                weights_result = future.result()


                input_shape = machineLearningData[nw_index]['trainData'].shape[:-1]
                model = subFun_TL.create_cnn_model(input_shape, numCore1, numCore2, numCore3)
                model.set_weights(weights_result)
                predictRSSI_TL[nw_index]['model'] = model

                completed_count += 1
                print(f"--- [Progress] Task {nw_index} completed ({completed_count}/{numNetworks}) ---")

            except Exception as e:

                print(f"!!! [Critical error] Task {nw_index} failed completely: {str(e)}")
                print(f"!!! Regenerating a new task for index {nw_index} and returning it to the queue...")


                new_f = submit_task(nw_index)
                future_to_nw[new_f] = nw_index
                seq.add(new_f)

    else:

        print(">>> [Single-machine mode] Remote workers are not ready. Using local ProcessPoolExecutor...")
        predictRSSI_TL = subFun_TL.run_in_parallel_TL(
            predictRSSI_TL, numNetworks, machineLearningData,
            historyModels, numCore1, numCore2, numCore3,
            learning_type, api_instance if api_instance else None,
            freeze_layer, learning_rate
        )

    return predictRSSI_TL


def trainJudgeModel(numNetworks, AIcommittee, FV, TV):
    """Train a random-forest judge model from feature vectors and observed RSSI targets."""

    def get_adaptive_params(n_samples):

        params = {
            'n_jobs': -1,
            'random_state': 42
        }

        if n_samples < 200:

            params['n_estimators'] = 200
            params['max_depth'] = 4
            params['min_samples_leaf'] = 5
        elif n_samples < 1000:

            params['n_estimators'] = 100
            params['max_depth'] = 10
            params['min_samples_leaf'] = 2
        else:

            params['n_estimators'] = 100
            params['max_depth'] = None
            params['min_samples_leaf'] = 1

        return params




    X_input = np.transpose(FV, (3, 0, 1, 2))
    N_samples = X_input.shape[0]
    X_flat = X_input.reshape(N_samples, -1)


    y_true = np.squeeze(TV)


    predictedMatrix = np.zeros((N_samples, numNetworks), dtype=float)
    print("Collecting expert prediction results...")
    for nw in range(numNetworks):

        preds = AIcommittee[nw]['model'].predict(X_input, verbose=0)
        predictedMatrix[:, nw] = preds.flatten()

    median_predictions = np.median(predictedMatrix, axis=1)




    residuals = y_true - median_predictions


    print("Training residual correction model (Random Forest Regressor)...")



    adaptive_params = get_adaptive_params(N_samples)
    judge_model = RandomForestRegressor(**adaptive_params)


    judge_model.fit(X_flat, residuals)



    train_corrections = judge_model.predict(X_flat)
    final_train_preds = median_predictions + train_corrections

    new_mae = np.mean(np.abs(final_train_preds - y_true))
    old_mae = np.mean(np.abs(median_predictions - y_true))

    print("Correction model training completed.")
    print(f"Fine-tuning set original median MAE: {old_mae:.4f}")
    print(f"Fine-tuning set corrected MAE: {new_mae:.4f}")


    '''
    # Temporary output used to inspect the generated CSV data.
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
    """Train a CNN judge with sequential cross-validation folds and distributed expert models."""
    client = None
    is_distributed = False
    try:
        from dask.distributed import get_client, as_completed
        client = get_client()
        is_distributed = True
        print(">>> [Distributed mode] Connected to Dask cluster. Dispatching parallel tasks...")
    except (ImportError, ValueError, Exception):
        print(">>> [Single-machine mode] No Dask cluster detected. Running fine-tuning sequentially...")


    # X_all: (N, 31, 36, 5), y_all: (N,)
    X_all = np.transpose(FV, (3, 0, 1, 2))
    y_all = np.squeeze(TV)
    n_samples = X_all.shape[0]
    input_shape = X_all.shape[1:]


    kf = KFold(n_splits=5, shuffle=True, random_state=42)


    oof_predict_matrix = np.zeros((n_samples, numNetworks))


    for fold_idx, (train_idx, val_idx) in enumerate(kf.split(X_all)):
        print(f"\n>>> Processing cross-validation fold {fold_idx+1}/5...")

        X_train_fold = X_all[train_idx]
        y_train_fold = y_all[train_idx]
        X_exam_fold = X_all[val_idx]


        if is_distributed:

            future_to_nw = {}
            for nw in range(numNetworks):

                weights = None
                if historyModels and historyModels[nw] and historyModels[nw].get('model'):
                    weights = historyModels[nw]['model'].get_weights()


                f = client.submit(
                    remote_fold_train_predict,
                    X_train_fold, y_train_fold, X_exam_fold,
                    weights, numCore1, numCore2, numCore3,
                    learning_type, input_shape, freeze_layer, learning_rate,
                    pure=False
                )
                future_to_nw[f] = nw


            completed_fold_count = 0
            for future in as_completed(future_to_nw.keys()):
                nw_index = future_to_nw[future]
                try:
                    preds = future.result()
                    oof_predict_matrix[val_idx, nw_index] = preds.flatten()
                    completed_fold_count += 1
                    if completed_fold_count % 10 == 0:
                        print(f"    Fold {fold_idx+1}: expert {completed_fold_count}/{numNetworks} completed")
                except Exception as e:
                    print(f"    !!! Fold {fold_idx+1} expert {nw_index} task failed: {e}")
        else:

            for nw in range(numNetworks):
                weights = historyModels[nw]['model'].get_weights() if historyModels and historyModels[nw] else None

                preds = remote_fold_train_predict(
                    X_train_fold, y_train_fold, X_exam_fold,
                    weights, numCore1, numCore2, numCore3,
                    learning_type, input_shape, freeze_layer, learning_rate
                )
                oof_predict_matrix[val_idx, nw] = preds.flatten()
                if (nw + 1) % 5 == 0:
                    print(f"    Single-machine progress: Fold {fold_idx+1}, expert {nw+1}/{numNetworks} completed")


    print("\n>>> [Training dataset prepared] Training CNN judge model...")

    debug_data = {
        "FV": FV,
        "TV": TV,
        "optionalParams": optionalParams,
        "OOF": oof_predict_matrix,
    }
    """
    with open("debug.pkl", "wb") as f:
        dill.dump(debug_data, f)
    """

    # judge_cnn, expert_group_map = training_judge_model.train_judge_cnn(X_all, oof_predict_matrix, y_all, input_shape)


    model_cols = [f'Model_{i}' for i in range(numNetworks)]
    df_oof = pd.DataFrame(oof_predict_matrix, columns=model_cols)
    df_oof['RSSI_TV'] = y_all.flatten()
    df_oof['Median_Prediction'] = np.median(oof_predict_matrix, axis=1)
    df_oof['Median_Abs_Error'] = np.abs(df_oof['Median_Prediction'] - df_oof['RSSI_TV'])
    errors_matrix = np.abs(oof_predict_matrix - y_all.reshape(-1, 1))
    df_oof['Best_Model_Idx'] = np.argmin(errors_matrix, axis=1)
    df_oof['Best_Model_Error'] = np.min(errors_matrix, axis=1)
    param_cols = optionalParams.columns.tolist()
    df_oof[param_cols] = optionalParams.values

    judgeModelInfo = {
        "df_oof": df_oof,#dataframe
        "debug_data": debug_data,
    }
    return judgeModelInfo


def remote_fold_train_predict(X_train, y_train, X_exam, weights, numCore1, numCore2, numCore3, l_type, shape, freeze_layer, learning_rate):
    """Train a temporary expert remotely with the production fine-tuning configuration."""



    model = create_cnn_model(shape, numCore1, numCore2, numCore3)
    if weights is not None:
        model.set_weights(weights)


    if l_type == "type_TL":


        model = finalize_finetune_config(model, freeze_layer, learning_rate)



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




        model.fit(
            X_train, y_train,
            validation_split=0.15,
            epochs=5000,
            batch_size=8,
            callbacks=[early_stopping, reduce_lr],
            verbose=1
        )

    else:

        model.compile(optimizer='adam', loss='mse')
        model.fit(X_train, y_train, epochs=20, batch_size=32, verbose=0)




    preds = model.predict(X_exam, verbose=0)



    del model



    tf.keras.backend.clear_session()


    gc.collect()

    return preds
