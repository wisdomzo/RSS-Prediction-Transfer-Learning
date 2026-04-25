import sys
import os
from qgis.core import *
from qgis.core import QgsProcessingFeatureSourceDefinition, QgsVectorFileWriter
import platform


if platform.system() == "Darwin":
    print("检测到macOS系统")
    # 1. 设置 QGIS 环境
    qgis_path = "/Applications/QGIS-LTR.app/Contents"
    os.environ['QGIS_PREFIX_PATH'] = f"{qgis_path}/MacOS"
    sys.path.extend([
        f"{qgis_path}/Resources/python",
        f"{qgis_path}/Resources/python/plugins",
        f"{qgis_path}/Resources/python/qgis"
    ])

    # 2. 初始化 Processing
    from qgis.analysis import QgsNativeAlgorithms
    QgsApplication.setPrefixPath(f"{qgis_path}/MacOS", True)
    qgs = QgsApplication([], False)
    qgs.initQgis()

    # 3. 导入 Processing
    import processing
    from processing.core.Processing import Processing
    Processing.initialize()
    print("QGIS Processing initialized successfully.")




if platform.system() == "Linux":
    print("检测到Linux树莓派系统")
    # 1. 设置 QGIS 环境（树莓派路径）
    qgis_path = "/usr"  # 树莓派默认安装路径
    os.environ['QGIS_PREFIX_PATH'] = qgis_path
    sys.path.extend([
        "/usr/share/qgis/python",
        "/usr/lib/python3/dist-packages",  # 关键：PyQGIS 模块路径
        "/usr/share/qgis/python/plugins",  # 关键：Processing 插件路径
    ])

    # 2. 初始化 QGIS 应用
    QgsApplication.setPrefixPath(qgis_path, True)
    qgs = QgsApplication([], False)
    qgs.initQgis()

    # 3. 初始化 Processing
    from qgis.analysis import QgsNativeAlgorithms

    try:
        from processing.core.Processing import Processing

        Processing.initialize()
        import processing

        print("QGIS Processing initialized successfully.")
    except Exception as e:
        print(f"QGIS Processing loss: {e}")
        qgs.exitQgis()
        sys.exit(1)




if platform.system() == "Windows":
    print("检测到Windows系统")

    # 1. 设置 QGIS 环境
    # 默认安装路径（根据你的QGIS版本调整）
    qgis_path = r"C:\Program Files\QGIS 3.40.5"  # 替换3.xx为你的QGIS版本号

    os.environ['QGIS_PREFIX_PATH'] = os.path.join(qgis_path, "apps", "qgis-ltr")
    sys.path.extend([
        os.path.join(qgis_path, "apps", "qgis-ltr", "python"),
        os.path.join(qgis_path, "apps", "qgis-ltr", "python", "plugins"),
        os.path.join(qgis_path, "apps", "Python312", "Lib", "site-packages")  # 替换XX为Python版本号
    ])

    # 2. 初始化 QGIS 应用
    from qgis.core import QgsApplication
    QgsApplication.setPrefixPath(os.path.join(qgis_path, "apps", "qgis-ltr"), True)
    qgs = QgsApplication([], False)
    qgs.initQgis()

    # 3. 导入并初始化 Processing
    from qgis.analysis import QgsNativeAlgorithms
    import processing
    from processing.core.Processing import Processing
    Processing.initialize()
    print("QGIS Processing initialized successfully.")



def process_data(csv_path, gpkg_path, output_path):
    # 加载 CSV（确保有 X/Y 列）
    csv_uri = (
        f"file://{csv_path}?"
        "delimiter=,&"  # 分隔符（逗号）
        "xField=Longitude&"  # 经度字段名（可替换为你的实际列名）
        "yField=Latitude&"  # 纬度字段名
        "crs=EPSG:6668&"  # 坐标系（WGS84）
        "encoding=UTF-8"  # 文件编码
    )
    csv_layer = QgsVectorLayer(csv_uri, "orig_CSV", "delimitedtext")
    if not csv_layer.isValid():
        print("错误：CSV加载失败！")
        return

    # 加载GPKG文件（自动加载第一个图层）
    gpkg_layer = QgsVectorLayer(gpkg_path, "open_map", "ogr")  # 不指定图层名
    if not gpkg_layer.isValid():
        print("错误：GPKG加载失败！")
        return
    else:
        print(f"成功加载GPKG图层：{gpkg_layer.name()}")


    # 修复几何（关键步骤）
    #fixed_result = processing.run("native:fixgeometries", {
    #    'INPUT': gpkg_layer,
    #    'METHOD': 0,
    #    'OUTPUT': "memory:"
    #})
    #fixed_layer = fixed_result['OUTPUT']


    # 创建空间索引（添加错误处理）
    try:
        processing.run("native:createspatialindex", {'INPUT': csv_layer})
        processing.run("native:createspatialindex", {'INPUT': gpkg_layer})
    except Exception as e:
        print(f"空间索引创建失败：{str(e)}")


    # 执行按位置连接
    join_params = {
        'INPUT': csv_layer,  # 可以直接使用图层对象
        'JOIN': gpkg_layer,
        'PREDICATE': [5],  # 5=相交
        'JOIN_FIELDS': [],  # 所有字段
        'METHOD': 2,  # 创建匹配要素0=创建匹配要素（多对一），1=仅保留匹配要素（一对一）2=仅采用重叠最大的要素属性（一对一）
        'DISCARD_NONMATCHING': False,
        'OUTPUT': 'memory:joined_layer'
    }

    try:
        join_result = processing.run("qgis:joinattributesbylocation", join_params)
        joined_layer = join_result['OUTPUT']

        # 使用 QgsVectorFileWriter 导出 CSV
        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = "CSV"
        options.fileEncoding = "UTF-8"
        #options.layerOptions = ["GEOMETRY=AS_XYZ"]  # 如果需要保留坐标

        # 执行导出
        transform_context = QgsProject.instance().transformContext()
        result = QgsVectorFileWriter.writeAsVectorFormatV3(
            joined_layer,
            output_path,
            transform_context,
            options
        )

        if result[0] == QgsVectorFileWriter.NoError:
            print(f"处理成功，结果保存到：{output_path}")
            return output_path
        else:
            print(f"导出CSV失败：{result[1]}")
            return None

    except Exception as e:
        print(f"处理失败：{str(e)}")
        return None



if __name__ == "__main__":
    process_data(sys.argv[1], sys.argv[2], sys.argv[3])
    qgs.exitQgis()