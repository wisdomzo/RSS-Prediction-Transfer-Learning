param(
    [string]$PackageVersion = ""
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

$Python = "python"
$VersionArgs = @("--repo", $ScriptDir)
if ($PackageVersion.Trim()) {
    $VersionArgs += $PackageVersion.Trim()
}

try {
    $Version = (& $Python "$ScriptDir\version_info.py" @VersionArgs).Trim()
} catch {
    Write-Error "Unable to determine the package version. $_"
    exit 1
}

if (-not $Version) {
    Write-Error "Unable to determine the package version."
    exit 1
}

$AppName = "RSS_Predictor_Windows_$Version"
$MainScript = "main.py"
$AppIcon = Join-Path $ScriptDir "wave.icns"
$AssetVersionPath = Join-Path $ScriptDir "build\asset_version.txt"

Write-Host "APP_NAME=$AppName"
Write-Host "Starting Windows packaging process: $AppName"

Write-Host "Cleaning old build and dist directories..."
Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue
Get-ChildItem -Filter *.spec -ErrorAction SilentlyContinue | Remove-Item -Force
New-Item -ItemType Directory -Force -Path build | Out-Null
Set-Content -Path $AssetVersionPath -Value $Version -Encoding UTF8

$PyInstallerArgs = @(
    "--noconfirm",
    "--onefile",
    "--windowed",
    "--name", $AppName,
    "--add-data", "web;web",
    "--add-data", "tempData;tempData",
    "--add-data", "database;database",
    "--add-data", "models;models",
    "--add-data", "assets;assets",
    "--add-data", "build\asset_version.txt;.",
    "--add-data", "predict_area.py;.",
    "--add-data", "main_collect_data.py;.",
    "--add-data", "transfer_learning_main.py;.",
    "--add-data", "subFun.py;.",
    "--add-data", "subFun_TL.py;.",
    "--add-data", "my_plot_figure.py;.",
    "--add-data", "main_multiple_processes.py;.",
    "--add-data", "paper_functions.py;.",
    "--add-data", "training_history_database.py;.",
    "--exclude-module", "ray.thirdparty_files.psutil",
    "--hidden-import", "psutil",
    "--hidden-import", "numpy",
    "--hidden-import", "numpy.core.multiarray",
    "--hidden-import", "numpy.core._multiarray_umath",
    "--hidden-import", "scipy._external.array_api_compat.numpy.fft",
    "--hidden-import", "scipy._lib.array_api_compat.numpy.fft",
    "--hidden-import", "rasterio.sample",
    "--hidden-import", "matplotlib.pyplot",
    "--hidden-import", "pyogrio._geometry",
    "--hidden-import", "fiona._shim",
    "--hidden-import", "fiona.schema",
    "--collect-all", "psutil",
    "--collect-all", "numpy",
    "--collect-all", "scipy",
    "--collect-all", "rasterio",
    "--collect-all", "pywebview",
    "--collect-all", "matplotlib",
    "--collect-all", "pyogrio",
    "--collect-all", "fiona"
)

if (Test-Path $AppIcon) {
    $PyInstallerArgs += @("--icon", $AppIcon)
} else {
    Write-Host "No wave.icns file was found. Packaging will continue without a custom icon."
}

$RayAvailable = $false
try {
    & $Python -c "import ray" *> $null
    if ($LASTEXITCODE -eq 0) {
        $RayAvailable = $true
    }
} catch {
    $RayAvailable = $false
}

if ($RayAvailable) {
    $PyInstallerArgs += @("--collect-all", "ray")
}

$PyInstallerArgs += $MainScript

Write-Host "Running PyInstaller packaging. This may take a few minutes..."
& pyinstaller @PyInstallerArgs

if ($LASTEXITCODE -eq 0) {
    Write-Host "Packaging completed successfully."
    Write-Host "Application location: $ScriptDir\dist\$AppName.exe"
} else {
    Write-Error "Packaging failed. Review the error messages above."
    exit 1
}
