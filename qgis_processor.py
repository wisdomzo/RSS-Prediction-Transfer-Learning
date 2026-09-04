import sys
import os
from qgis.core import *
from qgis.core import QgsProcessingFeatureSourceDefinition, QgsVectorFileWriter
import platform


if platform.system() == "Darwin":
    print("macOS system detected.")
    # 1. Configure the QGIS environment.
    qgis_path = "/Applications/QGIS-LTR.app/Contents"
    os.environ['QGIS_PREFIX_PATH'] = f"{qgis_path}/MacOS"
    sys.path.extend([
        f"{qgis_path}/Resources/python",
        f"{qgis_path}/Resources/python/plugins",
        f"{qgis_path}/Resources/python/qgis"
    ])

    # 2. Initialize QGIS Processing.
    from qgis.analysis import QgsNativeAlgorithms
    QgsApplication.setPrefixPath(f"{qgis_path}/MacOS", True)
    qgs = QgsApplication([], False)
    qgs.initQgis()

    # 3. Import and initialize Processing.
    import processing
    from processing.core.Processing import Processing
    Processing.initialize()
    print("QGIS Processing initialized successfully.")




if platform.system() == "Linux":
    print("Linux Raspberry Pi system detected.")
    # 1. Configure the QGIS environment for Raspberry Pi paths.
    qgis_path = "/usr"  # Default Raspberry Pi installation path.
    os.environ['QGIS_PREFIX_PATH'] = qgis_path
    sys.path.extend([
        "/usr/share/qgis/python",
        "/usr/lib/python3/dist-packages",  # Required PyQGIS module path.
        "/usr/share/qgis/python/plugins",  # Required Processing plugin path.
    ])

    # 2. Initialize the QGIS application.
    QgsApplication.setPrefixPath(qgis_path, True)
    qgs = QgsApplication([], False)
    qgs.initQgis()

    # 3. Initialize QGIS Processing.
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
    print("Windows system detected.")

    # 1. Configure the QGIS environment.
    # Default installation path; adjust it for the installed QGIS version.
    qgis_path = r"C:\Program Files\QGIS 3.40.5"  # Replace 3.xx with the installed QGIS version.

    os.environ['QGIS_PREFIX_PATH'] = os.path.join(qgis_path, "apps", "qgis-ltr")
    sys.path.extend([
        os.path.join(qgis_path, "apps", "qgis-ltr", "python"),
        os.path.join(qgis_path, "apps", "qgis-ltr", "python", "plugins"),
        os.path.join(qgis_path, "apps", "Python312", "Lib", "site-packages")  # Replace XX with the installed Python version.
    ])

    # 2. Initialize the QGIS application.
    from qgis.core import QgsApplication
    QgsApplication.setPrefixPath(os.path.join(qgis_path, "apps", "qgis-ltr"), True)
    qgs = QgsApplication([], False)
    qgs.initQgis()

    # 3. Import and initialize Processing.
    from qgis.analysis import QgsNativeAlgorithms
    import processing
    from processing.core.Processing import Processing
    Processing.initialize()
    print("QGIS Processing initialized successfully.")



def process_data(csv_path, gpkg_path, output_path):
    # Load the CSV and require X/Y coordinate columns.
    csv_uri = (
        f"file://{csv_path}?"
        "delimiter=,&"  # Comma delimiter.
        "xField=Longitude&"  # Longitude field; replace with the actual column name if needed.
        "yField=Latitude&"  # Latitude field.
        "crs=EPSG:6668&"  # Coordinate reference system (WGS84).
        "encoding=UTF-8"  # File encoding.
    )
    csv_layer = QgsVectorLayer(csv_uri, "orig_CSV", "delimitedtext")
    if not csv_layer.isValid():
        print("Error: CSV loading failed.")
        return

    # Load the GPKG file; the first layer is selected automatically.
    gpkg_layer = QgsVectorLayer(gpkg_path, "open_map", "ogr")  # No explicit layer name.
    if not gpkg_layer.isValid():
        print("Error: GPKG loading failed.")
        return
    else:
        print(f"GPKG layer loaded successfully: {gpkg_layer.name()}")


    # Repair geometries when this optional processing step is enabled.
    #fixed_result = processing.run("native:fixgeometries", {
    #    'INPUT': gpkg_layer,
    #    'METHOD': 0,
    #    'OUTPUT': "memory:"
    #})
    #fixed_layer = fixed_result['OUTPUT']


    # Create spatial indexes with error handling.
    try:
        processing.run("native:createspatialindex", {'INPUT': csv_layer})
        processing.run("native:createspatialindex", {'INPUT': gpkg_layer})
    except Exception as e:
        print(f"Spatial index creation failed: {str(e)}")


    # Join attributes by location.
    join_params = {
        'INPUT': csv_layer,  # A layer object can be passed directly.
        'JOIN': gpkg_layer,
        'PREDICATE': [5],  # 5 = intersects.
        'JOIN_FIELDS': [],  # Include all fields.
        'METHOD': 2,  # 0=create separate features (one-to-many), 1=first match only (one-to-one), 2=largest overlap only (one-to-one).
        'DISCARD_NONMATCHING': False,
        'OUTPUT': 'memory:joined_layer'
    }

    try:
        join_result = processing.run("qgis:joinattributesbylocation", join_params)
        joined_layer = join_result['OUTPUT']

        # Export the CSV with QgsVectorFileWriter.
        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = "CSV"
        options.fileEncoding = "UTF-8"
        #options.layerOptions = ["GEOMETRY=AS_XYZ"]  # Enable this option to retain coordinates.

        # Perform the export.
        transform_context = QgsProject.instance().transformContext()
        result = QgsVectorFileWriter.writeAsVectorFormatV3(
            joined_layer,
            output_path,
            transform_context,
            options
        )

        if result[0] == QgsVectorFileWriter.NoError:
            print(f"Processing succeeded. Results saved to: {output_path}")
            return output_path
        else:
            print(f"CSV export failed: {result[1]}")
            return None

    except Exception as e:
        print(f"Processing failed: {str(e)}")
        return None



if __name__ == "__main__":
    process_data(sys.argv[1], sys.argv[2], sys.argv[3])
    qgs.exitQgis()
