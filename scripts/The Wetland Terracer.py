from qgis.core import (QgsProcessing,
                       QgsProcessingAlgorithm,
                       QgsProcessingParameterRasterLayer,
                       QgsProcessingParameterNumber,
                       QgsProcessingParameterEnum,
                       QgsProcessingParameterRasterDestination)
from osgeo import gdal, osr
import numpy as np
import sys

class WetlandTerracer(QgsProcessingAlgorithm):
    INPUT_RASTER = 'INPUT_RASTER'
    HEIGHT_WINDOW = 'HEIGHT_WINDOW'
    PRECISION = 'PRECISION'
    VERTICAL_MULT = 'VERTICAL_MULT'
    OUTPUT_DEM = 'OUTPUT_DEM'

    def name(self): return 'wetland_terracer'
    def displayName(self): return 'Wetland Terracer'
    def group(self): return 'Site Assessment Tools'
    def groupId(self): return 'site_assessment_tools'
    def createInstance(self): return WetlandTerracer()

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterRasterLayer(self.INPUT_RASTER, 'Input Raw Raster'))
        self.addParameter(QgsProcessingParameterNumber(self.HEIGHT_WINDOW, 'Elevation Window Height (Feet)', defaultValue=20))
        self.addParameter(QgsProcessingParameterEnum(self.PRECISION, 'Rounding Precision', options=['0.25 ft', '0.10 ft', 'No Rounding'], defaultValue=0))
        self.addParameter(QgsProcessingParameterNumber(self.VERTICAL_MULT, 'Vertical Multiplier (e.g. 3.28084 for Meters -> Feet)', defaultValue=1.0))
        self.addParameter(QgsProcessingParameterRasterDestination(self.OUTPUT_DEM, 'Output Terraced DEM'))

    def processAlgorithm(self, parameters, context, feedback):
        
        try:
            raw_val = parameters[self.PRECISION]
            feedback.pushInfo(f"DEBUG: RAW MODEL INPUT: '{raw_val}'")
        except:
            feedback.pushInfo("DEBUG: Could not read raw value.")
        
        source_layer = self.parameterAsRasterLayer(parameters, self.INPUT_RASTER, context)
        win_height = self.parameterAsDouble(parameters, self.HEIGHT_WINDOW, context)
        precision_idx = self.parameterAsInt(parameters, self.PRECISION, context)
        v_mult = self.parameterAsDouble(parameters, self.VERTICAL_MULT, context)
        out_path = self.parameterAsOutputLayer(parameters, self.OUTPUT_DEM, context)

        # 1. READ DATA DIRECTLY VIA GDAL (Bypass QGIS)
        ds = gdal.Open(source_layer.source())
        band = ds.GetRasterBand(1)
        arr = band.ReadAsArray()
        
        # Get Geotransform and Projection to save later
        geotransform = ds.GetGeoTransform()
        projection = ds.GetProjection()
        no_data_val = band.GetNoDataValue()
        
        # 2. THE CLEANUP (Numpy Magic)
        # Create a boolean mask of "Bad Data"
        # Bad = (Matches NoData Value) OR (Is astronomical) OR (Is effectively infinite)
        if no_data_val is not None:
            is_nodata = (arr == no_data_val)
        else:
            is_nodata = np.zeros(arr.shape, dtype=bool)

        # Also kill anything non-terrestrial (> 30,000 or < -1,500)
        is_crazy = (arr > 30000) | (arr < -1500)
        
        # Combine masks
        bad_pixels = is_nodata | is_crazy

        # 3. CALCULATE STATS (Only on valid pixels)
        # We use a masked array to get the REAL min
        valid_data = np.ma.masked_array(arr, mask=bad_pixels)
        
        if valid_data.count() == 0:
            feedback.reportError("No valid elevation data found in raster!", fatalError=True)
            return {}

        z_min_raw = valid_data.min()
        z_min_adj = z_min_raw * v_mult
        z_max_adj = z_min_adj + win_height
        
        feedback.pushInfo(f"Valid Min: {z_min_raw:.2f}. Basin Floor: {z_min_adj:.2f} ft. Ceiling: {z_max_adj:.2f} ft.")

        # 4. APPLY MATH
        # Convert entire array to target units
        arr_ft = arr * v_mult
        
        # Determine Rounding
        if precision_idx == 0: # 0.25 ft
            arr_processed = np.round(arr_ft * 4.0) / 4.0
        elif precision_idx == 1: # 0.10 ft
            arr_processed = np.round(arr_ft * 10.0) / 10.0
        else:
            arr_processed = arr_ft
            
        # 5. APPLY CLIPPING (The Ceiling)
        # Any valid pixel ABOVE the ceiling becomes NoData
        # Any "Bad Pixel" (from step 2) becomes NoData
        
        final_nodata_value = -9999.0
        
        # Logic: Set output to -9999 where:
        # (Original was bad) OR (Value > Ceiling)
        mask_final = bad_pixels | (arr_ft > z_max_adj)
        
        arr_processed[mask_final] = final_nodata_value

        # 6. WRITE OUTPUT
        driver = gdal.GetDriverByName("GTiff")
        out_ds = driver.Create(out_path, ds.RasterXSize, ds.RasterYSize, 1, gdal.GDT_Float32)
        out_ds.SetGeoTransform(geotransform)
        out_ds.SetProjection(projection)
        
        out_band = out_ds.GetRasterBand(1)
        out_band.WriteArray(arr_processed)
        out_band.SetNoDataValue(final_nodata_value)
        
        # Clean up memory
        ds = None
        out_ds = None

        return {self.OUTPUT_DEM: out_path}