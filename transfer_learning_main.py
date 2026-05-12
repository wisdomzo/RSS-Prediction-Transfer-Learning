import sys
import os
import numpy as np
import multiprocessing
import subFun_TL
import subFun
import pandas as pd
import pickle
import lzma
import ast

def get_app_root_directory():
    if hasattr(sys, '_MEIPASS'):
        return sys._MEIPASS
    else:
        return os.path.abspath(".")

APP_ROOT = get_app_root_directory()
if APP_ROOT not in sys.path:
    sys.path.insert(0, APP_ROOT)







def run_transfer_learning(selected_folder_csv, num_test_per, user_input, model_path, data_index, content_data_index, learning_type=None, api_instance=None, freeze_layer=9, learning_rate=1e-4):
    #读取数据
    # region
    numTestPer_TL = float(num_test_per)
    history_model_index = user_input
    history_model_name = model_path
    data_index_for_TL = data_index
    data_name_for_TL = content_data_index
    readDataIndex_TL = data_index_for_TL
    dataPath = history_model_name

    #读取历史模型
    with lzma.open(dataPath, 'rb') as saveFile:
        dataStrick = pickle.load(saveFile)
    numNetworks = dataStrick['numNetworks']
    markVector = dataStrick['markVector']
    K = dataStrick['K']
    historyModels = dataStrick['predictRSSI_TL']
    judge_model = dataStrick.get('judge_model')
    numCore1 = dataStrick['numCore1']
    numCore2 = dataStrick['numCore2']
    numCore3 = dataStrick['numCore3']
    del dataStrick

    #读取数据
    readDataIndex = data_index_for_TL
    for i, arg in enumerate(readDataIndex):
        globals()[f'origFV_{arg}'], globals()[f'origTV_{arg}'], globals()[
            f'origRxData_Alt_{arg}'], lambda_value, Pt, exM, N = subFun_TL.readDataForDL(data_name_for_TL[i], K)
    # endregion

    init_origFV_TL = np.concatenate([globals()[f'origFV_{i}'] for i in readDataIndex_TL], axis=3)
    init_origTV_TL = np.concatenate([globals()[f'origTV_{i}'] for i in readDataIndex_TL], axis=1)
    init_origRxData_Altitude_TL = pd.concat([globals()[f'origRxData_Alt_{i}'] for i in readDataIndex_TL], axis=0)
    if numTestPer_TL == 1:
        # 预测模式不需要增强，直接使用原始数据进行预测
        origFV_TL, origTV_TL, origRxData_Altitude_TL = init_origFV_TL, init_origTV_TL, init_origRxData_Altitude_TL
    else:
        # 信道可逆性补强：中心对称翻转增强
        origFV_TL, origTV_TL, origRxData_Altitude_TL = subFun.augment_centrosymmetric(init_origFV_TL, init_origTV_TL, init_origRxData_Altitude_TL)

    # 打乱元素顺序
    numSample_TL = origFV_TL.shape[3]
    randIndex_TL = np.random.permutation(numSample_TL)
    FV_TL = origFV_TL[:, :, :, randIndex_TL]
    TV_TL = origTV_TL[:, randIndex_TL].T
    rxData_Altitude_TL = origRxData_Altitude_TL.iloc[randIndex_TL, :]

    # 指定训练特征
    FV_TL, Q_TL = subFun_TL.selectProperty(markVector, FV_TL)

    ##########
    #设定训练，验证，测试等数据数据 for Model Generation
    ##########
    # region
    #numTestPer_TL = 0.9
    numTest_TL = int(np.floor(numSample_TL * numTestPer_TL))
    testData_TL = FV_TL[:, :, :, range(numTest_TL)]
    testRulData_TL = TV_TL[range(numTest_TL), :]
    testDistance_TL = rxData_Altitude_TL['disBtwTxRx'].iloc[range(numTest_TL)].values
    testFre_TL = testData_TL[0,0,3,:]

    numVal_TL = int(np.floor(0.2 * (numSample_TL - numTest_TL)))
    FV_forTraining_TL = FV_TL[:, :, :, numTest_TL:]
    TV_forTraining_TL = TV_TL[numTest_TL:, :]
    rxData_Altitude_forTraining_TL = rxData_Altitude_TL.iloc[numTest_TL:,:]


    machineLearningData_TL = [{} for _ in range(numNetworks)]
    for nw in range(numNetworks):
        tempSqr = np.arange(numSample_TL - numTest_TL)
        valIndex_TL = np.random.choice(tempSqr, numVal_TL, replace=False)
        trainIndex_TL = np.setdiff1d(tempSqr, valIndex_TL)
        machineLearningData_TL[nw]['valIndex'] = valIndex_TL
        machineLearningData_TL[nw]['valData'] = FV_forTraining_TL[:,:,:, valIndex_TL]
        machineLearningData_TL[nw]['valRulData'] = TV_forTraining_TL[valIndex_TL, :]
        machineLearningData_TL[nw]['trainIndex'] = trainIndex_TL
        machineLearningData_TL[nw]['trainData'] = FV_forTraining_TL[:,:,:, trainIndex_TL]
        machineLearningData_TL[nw]['trainRulData'] = TV_forTraining_TL[trainIndex_TL, :]
    # endregion

    # region
    if numTestPer_TL < 1:
        print("\n线性预测...Start.")
        predictRSSI_linear_TL = [{} for _ in range(numNetworks)]
        predictRSSI_linear_TL = subFun_TL.run_in_parallel_linear(
            predictRSSI_linear_TL, numNetworks, rxData_Altitude_forTraining_TL, machineLearningData_TL, testDistance_TL, testFre_TL
        )
        print("线性预测...Done.")

        print("\n深度网络预测...Start.")
        # predictRSSI_TL is model
        predictRSSI_TL = [{} for _ in range(numNetworks)]
        predictRSSI_TL = subFun_TL.run_in_parallel_TL_adaptive(predictRSSI_TL, numNetworks, machineLearningData_TL, historyModels, numCore1, numCore2, numCore3, learning_type=learning_type, api_instance=api_instance, freeze_layer=freeze_layer, learning_rate=learning_rate)        
        print("深度网络预测...Done.")

        print("训练裁判...Start.")
        judge_model = subFun_TL.trainJudgeModel(numNetworks, predictRSSI_TL, FV_forTraining_TL, TV_forTraining_TL)
        print("训练裁判...Done.")

        print("\n保存模型...Start.")
        save_file_path = os.path.join(selected_folder_csv, f'TL_model_for_{data_index_for_TL}.pkl.xz')
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
        print("\n保存模型...Done.")
    elif numTestPer_TL == 1:
        #TBD追缴n系列空间渐衰预测
        predictRSSI_TL = historyModels
        judge_model = judge_model
        print("\n保存模型...Start.")
        save_file_path = os.path.join(selected_folder_csv, f'Predict_model_for_{data_index_for_TL}.pkl.xz')
        #########
        to_save = {}
        allowed_prefixes = (
            'numNetworks', 
            'Pt', 
            'testDistance_TL', 
            'predictRSSI_TL', 
            'testData_TL', 
            'rxData_Altitude_TL', 
            'testRulData_TL',
            'judge_model'
        )
        to_save.update({
            k: v for k, v in locals().items() 
            if not k.startswith('__') and 
            k.startswith(allowed_prefixes) and  # 只要匹配元组中任意一个即可
            subFun.is_picklable(v)
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
        print("\n保存模型...Done.")
    # endregion

    return True


if __name__ == "__main__":
    # 保留命令行调用能力
    import sys
    # 解析命令行参数的逻辑...
    # run_transfer_learning(...)