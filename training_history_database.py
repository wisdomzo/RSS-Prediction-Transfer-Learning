import os
import numpy as np
import multiprocessing
import subFun_TL
import subFun
import pandas as pd
import pickle
import lzma
import ast
import sys
import platform

def get_app_root_directory():
    if hasattr(sys, '_MEIPASS'):
        return sys._MEIPASS
    else:
        return os.path.abspath(".")

APP_ROOT = get_app_root_directory()
if APP_ROOT not in sys.path:
    sys.path.insert(0, APP_ROOT)


def get_optimized_num_networks():
    total_logical_cores = multiprocessing.cpu_count()
    sys_platform = platform.system()

    # Default value for unexpected platforms or configurations.
    target_count = total_logical_cores

    if sys_platform == 'Linux':
        # Linux usually runs on a server, so use more resources while retaining the global cap.
        target_count = total_logical_cores * 1.0

    elif sys_platform == 'Darwin':  # macOS
        # Detect Apple Silicon (M1/M2/M3/M4).
        # platform.processor() == 'arm' is an alternative check.
        is_apple_silicon = os.uname().machine.startswith('arm')

        if is_apple_silicon:
            # Reserve two Apple Silicon cores for the system and use 80% of the remainder.
            # This limits system contention while making effective use of performance cores.
            target_count = (total_logical_cores - 2) * 0.8
        else:
            # Intel Macs use Hyper-Threading; target approximately 1.2 times the physical core count.
            target_count = (total_logical_cores / 2) * 1.2

    elif sys_platform == 'Windows':
        # On Windows, estimate capacity from the physical-core equivalent.
        target_count = total_logical_cores * 0.6  # Conservative utilization compromise.

    # Round down and clamp the result to the range 1 through 30.
    res = int(np.floor(target_count))
    return max(1, min(30, res))






def run_training_history_database(selected_folder_csv, numCore1, numCore2, numCore3, numTestPer, data_index, content_data_index, learning_type=None, api_instance=None):
    ##########
    # Read data.
    ##########
    # region
    # City types: 0=surface, 1=urban, 2=suburban, 3=town, 4=rural.
    seed_value = 6666
    np.random.seed(seed_value)
    K = 5 # Image channels: 0=elevation + building height, 1=gradient, 2=city type, 3=SF (or frequency), 4=step length.
    numNetworks = get_optimized_num_networks()
    readDataIndex = data_index
    for i, arg in enumerate(readDataIndex):
        globals()[f'origFV_{arg}'], globals()[f'origTV_{arg}'], globals()[
            f'origRxData_Alt_{arg}'], lambda_value, Pt, exM, N = subFun_TL.readDataForDL(content_data_index[i], K)

    init_origFV = np.concatenate([globals()[f'origFV_{i}'] for i in readDataIndex], axis=3)
    init_origTV = np.concatenate([globals()[f'origTV_{i}'] for i in readDataIndex], axis=1)
    init_origRxData_Altitude = pd.concat([globals()[f'origRxData_Alt_{i}'] for i in readDataIndex], axis=0)
    # Reinforce channel reciprocity through centrosymmetric-flip augmentation.
    origFV, origTV, origRxData_Altitude = subFun.augment_centrosymmetric(init_origFV, init_origTV, init_origRxData_Altitude)

    # Shuffle sample order.
    numSample = origFV.shape[3]
    randIndex = np.random.permutation(numSample)
    FV = origFV[:, :, :, randIndex]
    TV = origTV[:, randIndex].T
    rxData_Altitude = origRxData_Altitude.iloc[randIndex, :]

    # Select training features.
    markAltitude = 1
    mark3DBuilding = 1
    markCityType = 1
    markFre = 1
    markStep = 1
    markVector = [markAltitude, mark3DBuilding, markCityType, markFre, markStep]
    FV, Q = subFun_TL.selectProperty(markVector, FV)
    # endregion

    ##########
    # Prepare training, validation, and test datasets for model generation.
    ##########
    # region
    numTest = int(np.floor(numSample * numTestPer))
    testData = FV[:, :, :, range(numTest)]
    testRulData = TV[range(numTest), :]
    testDistance = rxData_Altitude['disBtwTxRx'].iloc[range(numTest)].values
    testFre = testData[0,0,3,:]

    numVal = int(np.floor(0.2 * (numSample - numTest)))
    FV_forTraining = FV[:, :, :, numTest:]
    TV_forTraining = TV[numTest:, :]
    rxData_Altitude_forTraining = rxData_Altitude.iloc[numTest:,:]

    machineLearningData = [{} for _ in range(numNetworks)]
    for nw in range(numNetworks):
        tempSqr = np.arange(numSample - numTest)
        valIndex = np.random.choice(tempSqr, numVal, replace=False)
        trainIndex = np.setdiff1d(tempSqr, valIndex)
        machineLearningData[nw]['valIndex'] = valIndex
        machineLearningData[nw]['valData'] = FV_forTraining[:,:,:, valIndex]
        machineLearningData[nw]['valRulData'] = TV_forTraining[valIndex, :]
        machineLearningData[nw]['trainIndex'] = trainIndex
        machineLearningData[nw]['trainData'] = FV_forTraining[:,:,:, trainIndex]
        machineLearningData[nw]['trainRulData'] = TV_forTraining[trainIndex, :]
    # endregion

    print("\nLinear prediction...Start.")
    predictRSSI_linear = [{} for _ in range(numNetworks)]
    predictRSSI_linear = subFun_TL.run_in_parallel_linear(predictRSSI_linear, numNetworks, rxData_Altitude_forTraining, machineLearningData, testDistance, testFre)
    print("Linear prediction...Done.")

    print("\nDeep neural network prediction...Start.")
    predictRSSI_TL = [{} for _ in range(numNetworks)]
    predictRSSI_TL = subFun_TL.run_in_parallel_TL_adaptive(predictRSSI_TL, numNetworks, machineLearningData, None, numCore1, numCore2, numCore3, learning_type=learning_type, api_instance=api_instance)
    print("Deep neural network prediction...Done.")

    print("\nSaving model...Start.")
    save_file_path = os.path.join(selected_folder_csv, f'history_model_from_{data_index}.pkl.xz')
    #########
    to_save = {}
    exclude_prefixes = (
        '__', 'FV', 'TV', 'init_', 'orig', 'rxData_', 'test', 'valIndex',
        'trainIndex', 'tempSqr', 'readDataIndex', 'content_data_index',
        'randIndex', 'data_index', 'arg', 'i', 'numSample', 'Q', 'numVal',
        'numTest', 'machineLearningData', 'to_save'
    )
    to_save.update({
        k: v for k, v in locals().items()
        if not k.startswith(exclude_prefixes) and subFun.is_picklable(v)
    })
    with lzma.open(save_file_path, 'wb') as saveFile:
        pickle.dump(to_save, saveFile)
    for key in list(globals().keys()):
        if key.startswith('orig') and not key.startswith('__'):
            del globals()[key]
    del to_save
    import gc
    gc.collect()
    #########
    print("Saving model...Done.")

    return True



##########
# Train the model and predict data.
##########
# region
if __name__ == '__main__':
    import sys
