#!/bin/bash

# --- Configuration ---
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

VERSION_ARGS=(--repo "$SCRIPT_DIR")
if [ -n "$1" ]; then
    VERSION_ARGS+=("$1")
fi

if ! VERSION=$(python3 "$SCRIPT_DIR/version_info.py" "${VERSION_ARGS[@]}"); then
    echo "Unable to determine the package version."
    exit 1
fi

OS=$(uname)
ARCH=$(uname -m)

if [[ "$OS" == "Darwin" ]]; then
    if [[ "$ARCH" == "x86_64" ]]; then
        BASE_NAME="RSS_Predictor_Intel"
    elif [[ "$ARCH" == "arm64" ]]; then
        BASE_NAME="RSS_Predictor_ARM"
    fi
elif [[ "$OS" == "Linux" ]]; then
    BASE_NAME="RSS_Predictor_Linux"
elif [[ "$OS" == MINGW* || "$OS" == CYGWIN* || "$OS" == MSYS* ]]; then
    BASE_NAME="RSS_Predictor_Windows"
else
    BASE_NAME="RSS_Predictor_Unknown"
fi

APP_NAME="${BASE_NAME}_${VERSION}"
BUNDLE_VERSION="${VERSION#v}"

MAIN_SCRIPT="main.py"
ICON_FILE="wave.icns"
echo "APP_NAME=${APP_NAME}"

echo "🚀 Starting packaging process: $APP_NAME"

# 1. Clean old build files
echo "🧹 Cleaning old build and dist directories..."
rm -rf build dist *.spec
mkdir -p build
printf '%s\n' "$VERSION" > build/asset_version.txt

# 2. Run the PyInstaller packaging command (unchanged)
echo "📦 Running PyInstaller packaging (this may take a few minutes)..."

pyinstaller --noconfirm --onedir --windowed \
  --icon="$ICON_FILE" \
  --name "$APP_NAME" \
  --add-data "web:web" \
  --add-data "tempData:tempData" \
  --add-data "database:database" \
  --add-data "models:models" \
  --add-data "assets:assets" \
  --add-data "build/asset_version.txt:." \
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

# 3. Check the packaging result
if [ $? -eq 0 ]; then
    PLIST_PATH="dist/$APP_NAME.app/Contents/Info.plist"
    if [[ "$OS" == "Darwin" && -f "$PLIST_PATH" ]]; then
        /usr/libexec/PlistBuddy -c "Set :CFBundleShortVersionString $BUNDLE_VERSION" "$PLIST_PATH" \
          || /usr/libexec/PlistBuddy -c "Add :CFBundleShortVersionString string $BUNDLE_VERSION" "$PLIST_PATH"
        /usr/libexec/PlistBuddy -c "Set :CFBundleVersion $BUNDLE_VERSION" "$PLIST_PATH" \
          || /usr/libexec/PlistBuddy -c "Add :CFBundleVersion string $BUNDLE_VERSION" "$PLIST_PATH"
        echo "Application metadata version: $BUNDLE_VERSION"
    fi
    echo "✅ Packaging completed successfully."
    echo "📂 Application location: $(pwd)/dist/$APP_NAME"
else
    echo "❌ Packaging failed. Review the error messages above."
    exit 1
fi
