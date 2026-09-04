import paper_functions
import subFun_TL
import subFun
import subprocess
import sys
import os

# region
# 1. Farm at Shimanto Town, SF8
# 2. Farm at Shimanto Town, SF10
# 3. Shrine at Shimanto Town, SF8
# 4. Shrine at Shimanto Town, SF10
# 5. University of the Ryukyus in Okinawa, SF8
# 6. University of the Ryukyus in Okinawa, SF10
# 7. Elementary school in Okinawa, SF8
# 8. Elementary school in Okinawa, SF10
# 9. Agricultural research site in Nago, SF8
# 10. Agricultural research site in Nago, SF10
# 11. Southern site in Nagano, SF8
# 12. Kochi University of Technology, SF8
# 13. Kochi University of Technology, SF10
# endregion


def main():
    #ml_files = subFun.list_ml_files()
    #history_files = subFun.list_history_files()

    while True:
        print("\n-----------------------------------------------")
        print("Welcome to RSS Prediction System v2.1.10, by Ou Zhao, 20250525")
        print("-----------------------------------------------")
        print("Select an option:")
        print("1: Train a general model")
        print("2: Train a localized model through transfer learning")
        print("3: Evaluate a general model")
        print("4: Evaluate a transfer-learning model")
        print("5: Process experimental data")
        print("6: Predict RSS")
        print("7: Display the training-network topology")
        print("8: Compare model performance")
        print("9: Analyze a specific model (test)")
        print("99: Display terminology and help")
        print("0: Exit")
        choice = input("Enter an option number (1, 2, ..., 0): ")

        if choice == '1':
            print("Selected: train a general model.")
            # Train a model from scratch.
            ml_files = subFun.list_ml_files()
            if not ml_files:
                print("No files beginning with 'ML_' were found.")
                return
            print("---> Select training data")
            readDataIndex = subFun.get_user_selection(ml_files)
            contentReadDataIndex = [ml_files[i-1] for i in readDataIndex]
            numCore1 = subFun.input_with_default("Enter the number of convolution blocks in layer 1", 8)
            numCore2 = subFun.input_with_default("Enter the number of convolution blocks in layer 2", 16)
            numCore3 = subFun.input_with_default("Enter the number of convolution blocks in layer 3", 32)
            numTestPer = subFun.input_with_default("Enter the test-data proportion", 0.15)
            subprocess.run([sys.executable, 'training_history_database.py', str(numCore1), str(numCore2), str(numCore3), str(numTestPer), str(readDataIndex)] + contentReadDataIndex, check=True)
            break
        elif choice == '2':
            print("Selected: train a localized model through transfer learning.")
            # Train a transfer-learning model.
            ml_files = subFun.list_ml_files()
            history_TL_files = subFun.list_history_TL_files()
            if not history_TL_files:
                print("No files beginning with 'history_model_from_' or 'TL_model_' were found.")
                return
            if not ml_files:
                print("No files beginning with 'ML_' were found.")
                return
            print("---> Select a historical model and prediction data")
            user_input = subFun.get_user_selection(history_TL_files)
            selected_predict_model = history_TL_files[user_input[0] - 1]
            readDataIndex = subFun.get_user_selection(ml_files)
            contentReadDataIndex = [ml_files[i - 1] for i in readDataIndex]
            numTestPer_TL = subFun.input_with_default("Enter the proportion of new data to predict with the transfer model [0,1]", 0.9)
            subprocess.run([sys.executable, 'transfer_learning_main.py', str(numTestPer_TL), str(user_input), selected_predict_model, str(readDataIndex)] + contentReadDataIndex, check=True)
            break
        elif choice == '3':
            print("Selected: evaluate a general model.")
            # Evaluate a general model.
            #ml_files = subFun.list_ml_files()
            history_files = subFun.list_history_files()
            if not history_files:
                print("No files beginning with 'history_model_from_' were found.")
                return
            user_input = subFun.get_user_selection(history_files)
            selected_name = history_files[user_input[0] - 1]
            print("---> Evaluate historical model")
            subFun_TL.show_history_model(selected_name)
            break
        elif choice == '4':
            print("Selected: evaluate a transfer-learning model.")
            # Evaluate a transfer-learning model.
            TL_files = subFun.list_TL_files()
            if not TL_files:
                print("No files beginning with 'TL_' were found.")
                return
            user_input = subFun.get_user_selection(TL_files)
            selected_name = TL_files[user_input[0] - 1]
            print("---> Evaluate transfer-learning model")
            subFun_TL.show_TL_model(selected_name)
            break
        elif choice == '5':
            print("Selected: process experimental data.")
            # Process experimental data.
            selected_folder_csv, selected_folder_map, selected_folder_fun = subFun.get_folder_path()
            subprocess.run([sys.executable, "main_collect_data.py", selected_folder_csv, selected_folder_map, selected_folder_fun], check=True)
            break
        elif choice == '6':
            print("Selected: predict RSS.")
            # Predict RSS.
            selected_folder_csv, selected_folder_map, selected_folder_fun = subFun.get_folder_path()
            subprocess.run([sys.executable, "predict_area.py", selected_folder_csv, selected_folder_map, selected_folder_fun], check=True)
            print("ML file generation completed.")
            # Select a historical model and prediction data.
            ml_files = subFun.list_ml_files()
            history_TL_files = subFun.list_history_TL_files()
            if not history_TL_files:
                print("No files beginning with 'history_model_from_' or 'TL_' were found.")
                return
            if not ml_files:
                print("No files beginning with 'ML_' were found.")
                return
            print("---> Select a model and prediction data")
            user_input = subFun.get_user_selection(history_TL_files)
            selected_predict_model = history_TL_files[user_input[0] - 1]
            readDataIndex = subFun.get_user_selection(ml_files)
            contentReadDataIndex = [ml_files[i - 1] for i in readDataIndex]
            numTestPer_TL = str(1)
            subprocess.run(
                [sys.executable, 'transfer_learning_main.py', numTestPer_TL, str(user_input), selected_predict_model,
                 str(readDataIndex)] + contentReadDataIndex, check=True)
            print("Prediction results generated.")
            print("\n---> Select prediction results (files beginning with 'Predict')")
            Predict_files = subFun.list_Predict_files()
            if not Predict_files:
                print("No files beginning with 'Predict_' were found.")
                return
            user_input = subFun.get_user_selection(Predict_files)
            selected_name = Predict_files[user_input[0] - 1]
            rxData_Altitude_TL, _, _ = subFun_TL.show_Predict_model(selected_name)
            print("---> Generate CSV file")
            rxData_Altitude_TL.to_csv(selected_folder_csv + '/predict_RSS.csv', index=False)
            break
        elif choice == '7':
            print("Selected: display the training-network topology.")
            # Display the training-network topology.
            history_TL_files = subFun.list_history_TL_files()
            if not history_TL_files:
                print("No files beginning with 'history_model_from_' were found.")
                return
            user_input = subFun.get_user_selection(history_TL_files)
            selected_name = history_TL_files[user_input[0] - 1]
            subFun_TL.show_training_network_topology(selected_name)
            break
        elif choice == '8':
            print("Selected: compare model performance.")
            # Compare model performance.
            paper_functions.show_diff_model_performance()
            break
        elif choice == '9':
            print("Selected: analyze a specific model (test).")
            print("This feature is currently under development (test).")
            #paper_functions.analyze_diff_model_performance()
            break
        elif choice == '99':
            print("Selected: display help information.\n")
            paper_functions.display_readme("Readme.txt")
            break
        elif choice == '0':
            print("Exiting the program.")
            break
        else:
            print("Invalid selection. Enter another option.")


if __name__ == "__main__":
    main()
