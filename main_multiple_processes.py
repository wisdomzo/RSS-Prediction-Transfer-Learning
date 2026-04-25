import paper_functions
import subFun_TL
import subFun
import subprocess
import sys
import os

# region
# 1. 農場＠四万十町SF8
# 2. 農場＠四万十町SF10
# 3. 神社＠四万十町SF8
# 4. 神社＠四万十町SF10
# 5. 琉大＠沖縄SF8
# 6. 琉大＠沖縄SF10
# 7. 小学＠沖縄SF8
# 8. 小学＠沖縄SF10
# 9. 農研＠名護SF8
# 10. 農研＠名護SF10
# 11. 南＠長野SF8
# 12. 高工大＠高知SF8
# 13. 高工大＠高知SF10
# endregion


def main():
    #ml_files = subFun.list_ml_files()
    #history_files = subFun.list_history_files()

    while True:
        print("\n-----------------------------------------------")
        print("欢迎使用<<RSS预测系统v2.1.10>>, by 趙欧, 20250525")
        print("-----------------------------------------------")
        print("请选择一个选项：")
        print("1: 训练一般模型")
        print("2: 转移学习训练本地化模型")
        print("3: 评价《一般》模型")
        print("4: 评价《迁移》模型")
        print("5: 实验数据处理")
        print("6: 预测RSS")
        print("7: 展示训练网络拓扑图")
        print("8: 比较多个模型性能")
        print("9: 分析具体模型性能（test）")
        print("99: 用语说明等")
        print("0: 退出")
        choice = input("请输入选项的数字 (1, 2, ..., 0): ")

        if choice == '1':
            print("用户选择了训练一般模型。")
            # 添加从头训练模型的代码
            ml_files = subFun.list_ml_files()
            if not ml_files:
                print("没有找到以'ML_'开头的文件。")
                return
            print("---> 选择训练数据")
            readDataIndex = subFun.get_user_selection(ml_files)
            contentReadDataIndex = [ml_files[i-1] for i in readDataIndex]
            numCore1 = subFun.input_with_default("请输入第一层卷积块数量", 8)
            numCore2 = subFun.input_with_default("请输入第二层卷积块数量", 16)
            numCore3 = subFun.input_with_default("请输入第三层卷积块数量", 32)
            numTestPer = subFun.input_with_default("请输入测试数据百分比", 0.15)
            subprocess.run([sys.executable, 'training_history_database.py', str(numCore1), str(numCore2), str(numCore3), str(numTestPer), str(readDataIndex)] + contentReadDataIndex, check=True)
            break
        elif choice == '2':
            print("用户选择了转移学习训练本地化模型。")
            # 添加转移学习模型的代码
            ml_files = subFun.list_ml_files()
            history_TL_files = subFun.list_history_TL_files()
            if not history_TL_files:
                print("没有找到以'history_model_from_'或者'TL_model_'开头的文件。")
                return
            if not ml_files:
                print("没有找到以'ML_'开头的文件。")
                return
            print("---> 选择历史模型和待预测数据")
            user_input = subFun.get_user_selection(history_TL_files)
            selected_predict_model = history_TL_files[user_input[0] - 1]
            readDataIndex = subFun.get_user_selection(ml_files)
            contentReadDataIndex = [ml_files[i - 1] for i in readDataIndex]
            numTestPer_TL = subFun.input_with_default("基于迁移模型，请输入对于新数据的预测比例[0,1]", 0.9)
            subprocess.run([sys.executable, 'transfer_learning_main.py', str(numTestPer_TL), str(user_input), selected_predict_model, str(readDataIndex)] + contentReadDataIndex, check=True)
            break
        elif choice == '3':
            print("用户选择了评价一般模型。")
            # 添加评价一般模型的代码
            #ml_files = subFun.list_ml_files()
            history_files = subFun.list_history_files()
            if not history_files:
                print("没有找到以'history_model_from_'开头的文件。")
                return
            user_input = subFun.get_user_selection(history_files)
            selected_name = history_files[user_input[0] - 1]
            print("---> 评价历史模型")
            subFun_TL.show_history_model(selected_name)
            break
        elif choice == '4':
            print("用户选择了评价迁移模型。")
            # 添加评价转移模型的代码
            TL_files = subFun.list_TL_files()
            if not TL_files:
                print("没有找到以'TL_'开头的文件。")
                return
            user_input = subFun.get_user_selection(TL_files)
            selected_name = TL_files[user_input[0] - 1]
            print("---> 评价迁移模型")
            subFun_TL.show_TL_model(selected_name)
            break
        elif choice == '5':
            print("用户选择了实验数据处理。")
            # 添加实验数据处理的代码
            selected_folder_csv, selected_folder_map, selected_folder_fun = subFun.get_folder_path()
            subprocess.run([sys.executable, "main_collect_data.py", selected_folder_csv, selected_folder_map, selected_folder_fun], check=True)
            break
        elif choice == '6':
            print("用户选择了预测RSS。")
            # 添加预测RSS的代码
            selected_folder_csv, selected_folder_map, selected_folder_fun = subFun.get_folder_path()
            subprocess.run([sys.executable, "predict_area.py", selected_folder_csv, selected_folder_map, selected_folder_fun], check=True)
            print("ML文件 Done。")
            # 选择历史模型和待预测数据
            ml_files = subFun.list_ml_files()
            history_TL_files = subFun.list_history_TL_files()
            if not history_TL_files:
                print("没有找到以'history_model_from_'或者'TL_'开头的文件。")
                return
            if not ml_files:
                print("没有找到以'ML_'开头的文件。")
                return
            print("---> 选择模型和待预测数据")
            user_input = subFun.get_user_selection(history_TL_files)
            selected_predict_model = history_TL_files[user_input[0] - 1]
            readDataIndex = subFun.get_user_selection(ml_files)
            contentReadDataIndex = [ml_files[i - 1] for i in readDataIndex]
            numTestPer_TL = str(1)
            subprocess.run(
                [sys.executable, 'transfer_learning_main.py', numTestPer_TL, str(user_input), selected_predict_model,
                 str(readDataIndex)] + contentReadDataIndex, check=True)
            print("已生成预测结果。")
            print("\n---> 选择预测结果（Predict开头文件）")
            Predict_files = subFun.list_Predict_files()
            if not Predict_files:
                print("没有找到以'Predict_'开头的文件。")
                return
            user_input = subFun.get_user_selection(Predict_files)
            selected_name = Predict_files[user_input[0] - 1]
            rxData_Altitude_TL, _, _ = subFun_TL.show_Predict_model(selected_name)
            print("---> 生成csv文件")
            rxData_Altitude_TL.to_csv(selected_folder_csv + '/predict_RSS.csv', index=False)
            break
        elif choice == '7':
            print("用户选择了展示训练网络拓扑图。")
            # 添加展示训练网络拓扑图的代码
            history_TL_files = subFun.list_history_TL_files()
            if not history_TL_files:
                print("没有找到以'history_model_from_'开头的文件。")
                return
            user_input = subFun.get_user_selection(history_TL_files)
            selected_name = history_TL_files[user_input[0] - 1]
            subFun_TL.show_training_network_topology(selected_name)
            break
        elif choice == '8':
            print("用户选择了比较个模型性能。")
            # 添加比较个模型性能的代码
            paper_functions.show_diff_model_performance()
            break
        elif choice == '9':
            print("用户选择了分析具体模型性能（test）。")
            print("目前正在开发中（test）。")
            #paper_functions.analyze_diff_model_performance()
            break
        elif choice == '99':
            print("用户选择了获取帮助信息。信息如下：\n")
            paper_functions.display_readme("Readme.txt")
            break
        elif choice == '0':
            print("退出程序。")
            break
        else:
            print("无效的选择，请重新输入。")


if __name__ == "__main__":
    main()