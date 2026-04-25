・做过的实验
A. 四万十町（高知県）：920
B. 琉球大学（那覇市）、農研機構（名護市）：920
C. 売木村（長野県）：920
D. 高知工科大学（高知県）：920
E. 信州大学（長野県）：920, 429

・用语介绍
地形|920|429
山岳（Mountain）|AC|E
农场（Farm）|AB|None
海面（Ocean surface）|B|None
郊区（Suburb）|ABCD|E
城市（City）|None|E
大都市（Metropolis）|None|None



# 1. 确保 tempData 不是空的
touch tempData/.keep

rm -rf build dist

# 2. 清理并打包
pyinstaller --noconfirm --onedir --windowed \
  --icon="wave.icns" \
  --add-data "web:web" \
  --add-data "tempData:tempData" \
  --add-data "database:database" \
  --add-data "models:models" \
  --add-data "assets:assets" \
  --exclude-module "ray.thirdparty_files.psutil" \
  --add-data "predict_area.py:." \
  --add-data "main_collect_data.py:." \
  --add-data "transfer_learning_main.py:." \
  --add-data "subFun.py:." \
  --add-data "subFun_TL.py:." \
  --add-data "my_plot_figure.py:." \
  --add-data "main_multiple_processes.py:." \
  --add-data "paper_functions.py:." \
  --add-data "training_history_database.py:." \
  --hidden-import "rasterio.sample" \
  --hidden-import "matplotlib.pyplot" \
  --hidden-import "psutil" \
  --collect-all ray \
  --collect-all psutil \
  --collect-all rasterio \
  --collect-all pywebview \
  --collect-all matplotlib \
  --hidden-import "pyogrio._geometry" \
  --hidden-import "fiona._shim" \
  --hidden-import "fiona.schema" \
  --collect-all "pyogrio" \
  --collect-all "fiona" \
  --hidden-import "numpy.core._multiarray_umath" \
  --hidden-import "numpy.core.multiarray" \
  --collect-all "numpy" \
  --name "D2D_Map_App" \
  "main.py"