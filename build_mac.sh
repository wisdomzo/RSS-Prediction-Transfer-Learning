#!/bin/bash

# --- 配置区 ---
# 获取命令行传入的第一个参数作为版本号
VERSION=$1

OS=$(uname)
ARCH=$(uname -m)

if [[ "$OS" == "Darwin" ]]; then
    if [[ "$ARCH" == "x86_64" ]]; then
        BASE_NAME="D2D_Map_App_Intel"
    elif [[ "$ARCH" == "arm64" ]]; then
        BASE_NAME="D2D_Map_App_ARM"
    fi
elif [[ "$OS" == "Linux" ]]; then
    BASE_NAME="D2D_Map_App_Linux"
elif [[ "$OS" == MINGW* || "$OS" == CYGWIN* || "$OS" == MSYS* ]]; then
    BASE_NAME="D2D_Map_App_Windows"
else
    BASE_NAME="D2D_Map_App_Unknown"
fi

# --- 核心修改：处理版本号后缀 ---
if [ -n "$VERSION" ]; then
    APP_NAME="${BASE_NAME}_${VERSION}"
else
    APP_NAME="$BASE_NAME"
fi

MAIN_SCRIPT="main.py"
ICON_FILE="wave.icns"
echo "APP_NAME=${APP_NAME}"

echo "🚀 开始打包流程: $APP_NAME"

# 1. 清理旧的构建文件
echo "🧹 正在清理旧的 build 和 dist 文件夹..."
rm -rf build dist *.spec

# 2. 执行 PyInstaller 打包命令 (保持不变)
echo "📦 正在调用 PyInstaller 进行打包 (这可能需要几分钟)..."

pyinstaller --noconfirm --onedir --windowed \
  --icon="$ICON_FILE" \
  --name "$APP_NAME" \
  --add-data "web:web" \
  --add-data "tempData:tempData" \
  --add-data "database:database" \
  --add-data "models:models" \
  --add-data "assets:assets" \
  --add-data "predict_area.py:." \
  --add-data "main_collect_data.py:." \
  --add-data "transfer_learning_main.py:." \
  --add-data "subFun.py:." \
  --add-data "subFun_TL.py:." \
  --add-data "my_plot_figure.py:." \
  --add-data "main_multiple_processes.py:." \
  --add-data "paper_functions.py:." \
  --add-data "training_history_database.py:." \
  --exclude-module "ray.thirdparty_files.psutil" \
  --hidden-import "psutil" \
  --hidden-import "numpy" \
  --hidden-import "numpy.core.multiarray" \
  --hidden-import "numpy.core._multiarray_umath" \
  --hidden-import "rasterio.sample" \
  --hidden-import "matplotlib.pyplot" \
  --hidden-import "pyogrio._geometry" \
  --hidden-import "fiona._shim" \
  --hidden-import "fiona.schema" \
  --collect-all "psutil" \
  --collect-all "numpy" \
  --collect-all "ray" \
  --collect-all "rasterio" \
  --collect-all "pywebview" \
  --collect-all "matplotlib" \
  --collect-all "pyogrio" \
  --collect-all "fiona" \
  "$MAIN_SCRIPT"

# 3. 检查打包结果
if [ $? -eq 0 ]; then
    echo "✅ 打包成功！"
    echo "📂 应用位置: $(pwd)/dist/$APP_NAME"
else
    echo "❌ 打包失败，请检查上方报错信息。"
    exit 1
fi