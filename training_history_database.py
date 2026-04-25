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
    
    # 默认值（防止意外情况）
    target_count = total_logical_cores

    if sys_platform == 'Linux':
        # Linux 通常是服务器，倾向于多用资源，但设置上限
        target_count = total_logical_cores * 1.0
        
    elif sys_platform == 'Darwin':  # macOS
        # 检查是否为 Apple Silicon (M1/M2/M3/M4)
        # 也可以通过 platform.processor() == 'arm' 判断
        is_apple_silicon = os.uname().machine.startswith('arm')
        
        if is_apple_silicon:
            # M2 Pro 核心都是实打实的，建议保留 2 个核心给系统，其余 80% 用于计算
            # 这样既不会让系统卡顿，也能充分利用 P-Core
            target_count = (total_logical_cores - 2) * 0.8
        else:
            # Intel Mac 带有超线程，使用总线程数的 75% 左右，或者物理核的 1.2 倍
            target_count = (total_logical_cores / 2) * 1.2
            
    elif sys_platform == 'Windows':
        # Windows 同样建议参考物理核心数
        target_count = total_logical_cores * 0.6  # 比较稳妥的折中方案
    
    # 统一计算：向下取整，限制在 1 到 30 之间
    res = int(np.floor(target_count))
    return max(1, min(30, res))






def run_training_history_database(selected_folder_csv, numCore1, numCore2, numCore3, numTestPer, data_index, content_data_index, learning_type=None, api_instance=None):
    ##########
    #读取数据
    ##########
    # region
    #城市类型：0是【地表】，1是【城市】，2是【郊区】，3是【小镇】，4是【农村】
    seed_value = 6666
    np.random.seed(seed_value)
    K = 5 #图片维度。0代表海拔+建筑物高层。1代表梯度。2代表城市类型。3代表SF(or 频率)。4代表步长。
    numNetworks = get_optimized_num_networks()
    readDataIndex = data_index
    for i, arg in enumerate(readDataIndex):
        globals()[f'origFV_{arg}'], globals()[f'origTV_{arg}'], globals()[
            f'origRxData_Alt_{arg}'], lambda_value, Pt, exM, N = subFun_TL.readDataForDL(content_data_index[i], K)

    init_origFV = np.concatenate([globals()[f'origFV_{i}'] for i in readDataIndex], axis=3)
    init_origTV = np.concatenate([globals()[f'origTV_{i}'] for i in readDataIndex], axis=1)
    init_origRxData_Altitude = pd.concat([globals()[f'origRxData_Alt_{i}'] for i in readDataIndex], axis=0)
    # 信道可逆性补强：中心对称翻转增强
    origFV, origTV, origRxData_Altitude = subFun.augment_centrosymmetric(init_origFV, init_origTV, init_origRxData_Altitude)

    # 打乱元素顺序
    numSample = origFV.shape[3]
    randIndex = np.random.permutation(numSample)
    FV = origFV[:, :, :, randIndex]
    TV = origTV[:, randIndex].T
    rxData_Altitude = origRxData_Altitude.iloc[randIndex, :]

    # 指定训练特征
    markAltitude = 1
    mark3DBuilding = 1
    markCityType = 1
    markFre = 1
    markStep = 1
    markVector = [markAltitude, mark3DBuilding, markCityType, markFre, markStep]
    FV, Q = subFun_TL.selectProperty(markVector, FV)
    # endregion

    ##########
    #设定训练，验证，测试等数据数据 for Model Generation
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

    print("\n线性预测...Start.")
    predictRSSI_linear = [{} for _ in range(numNetworks)]
    predictRSSI_linear = subFun_TL.run_in_parallel_linear(predictRSSI_linear, numNetworks, rxData_Altitude_forTraining, machineLearningData, testDistance, testFre)
    print("线性预测...Done.")

    print("\n深度网络预测...Start.")
    predictRSSI_TL = [{} for _ in range(numNetworks)]
    predictRSSI_TL = subFun_TL.run_in_parallel_TL_adaptive(predictRSSI_TL, numNetworks, machineLearningData, None, numCore1, numCore2, numCore3, learning_type=learning_type, api_instance=api_instance)
    print("深度网络预测...Done.")

    print("\n保存模型...Start.")
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
    print("保存模型...Done.")

    return True



##########
#训练模型和预测数据
##########
# region
if __name__ == '__main__':
    import sys