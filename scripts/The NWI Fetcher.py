from qgis.core import (QgsProcessing,
                       QgsProcessingAlgorithm,
                       QgsProcessingParameterFeatureSource,
                       QgsProcessingParameterVectorDestination,
                       QgsProject,
                       QgsCoordinateReferenceSystem,
                       QgsCoordinateTransform,
                       QgsGeometry)
from qgis import processing
import urllib.request
import urllib.parse
import json
import os

class NWIFetcher(QgsProcessingAlgorithm):
    INPUT_AOI = 'INPUT_AOI'
    OUTPUT_NWI = 'OUTPUT_NWI'

    def name(self): return 'nwi_fetcher'
    def displayName(self): return 'NWI Fetcher'
    def group(self): return 'Site Assessment Tools'
    def groupId(self): return 'site_assessment_tools'
    def createInstance(self): return NWIFetcher()

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterFeatureSource(self.INPUT_AOI, 'Area of Interest (AOI) Polygon'))
        self.addParameter(QgsProcessingParameterVectorDestination(self.OUTPUT_NWI, 'Output NWI Vectors'))

    def processAlgorithm(self, parameters, context, feedback):
        aoi_source = self.parameterAsSource(parameters, self.INPUT_AOI, context)
        output_path = self.parameterAsOutputLayer(parameters, self.OUTPUT_NWI, context)

        # --- MINOR EDIT 1: Safely Transform BBox to WGS84 for the Server ---
        crs_aoi = aoi_source.sourceCrs()
        crs_wgs84 = QgsCoordinateReferenceSystem("EPSG:4326")
        tr_to_wgs = QgsCoordinateTransform(crs_aoi, crs_wgs84, context.project())

        features = aoi_source.getFeatures()
        feature = next(features)
        
        geom_wgs = QgsGeometry(feature.geometry())
        geom_wgs.transform(tr_to_wgs)
        rect = geom_wgs.boundingBox()
        
        # Format: xmin,ymin,xmax,ymax (Now in universally accepted Lat/Lon)
        bbox_string = f"{rect.xMinimum()},{rect.yMinimum()},{rect.xMaximum()},{rect.yMaximum()}"
        feedback.pushInfo(f"Requesting NWI for WGS84 area: {bbox_string}")

        base_url = "https://fwspublicservices.wim.usgs.gov/wetlandsmapservice/rest/services/Wetlands/MapServer/0/query"
        
        # --- MINOR EDIT 2: Tell server to expect and return WGS84 ---
        params = {
            'geometry': bbox_string,
            'geometryType': 'esriGeometryEnvelope',
            'spatialRel': 'esriSpatialRelIntersects',
            'inSR': '4326',       
            'outSR': '4326',      
            'outFields': '*',
            'f': 'geojson'
        }
        
        query_string = urllib.parse.urlencode(params)
        full_url = f"{base_url}?{query_string}"

        feedback.pushInfo("Contacting US Fish & Wildlife Service (WIM Server)...")
        
        try:
            req = urllib.request.Request(
                full_url, 
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) QGIS/3.0'}
            )
            
            with urllib.request.urlopen(req) as response:
                data = response.read()
                
                try:
                    json_check = json.loads(data)
                    if 'error' in json_check:
                         feedback.reportError(f"API Error: {json_check['error']}", fatalError=True)
                         return {}
                except: pass

                # --- MINOR EDIT 3: Save as GeoJSON, then let QGIS build the GPKG ---
                temp_geojson = os.path.join(os.path.dirname(output_path), "temp_nwi.geojson")
                with open(temp_geojson, 'wb') as out_file:
                    out_file.write(data)
                    
            feedback.pushInfo("NWI Data Downloaded Successfully. Converting to Final Output...")
            
            # This safely converts the text to a GPKG and projects it back to your local CRS (EPSG:3089)
            processing.run("native:reprojectlayer", {
                'INPUT': temp_geojson,
                'TARGET_CRS': crs_aoi,
                'OUTPUT': output_path
            }, context=context, feedback=feedback)
            
            try: os.remove(temp_geojson) 
            except: pass
            
        except Exception as e:
            feedback.reportError(f"Download Failed: {e}", fatalError=True)
            return {}

        return {self.OUTPUT_NWI: output_path}