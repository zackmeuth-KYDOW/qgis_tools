from qgis.core import (QgsProcessing,
                       QgsProcessingAlgorithm,
                       QgsProcessingParameterFeatureSource,
                       QgsProcessingParameterVectorDestination,
                       QgsVectorLayer,
                       QgsCoordinateReferenceSystem,
                       QgsCoordinateTransform,
                       QgsGeometry)
import processing

class GeologyFetcher(QgsProcessingAlgorithm):
    INPUT = 'INPUT'
    OUTPUT = 'OUTPUT'

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.INPUT,
                'Area of Interest (AOI)',
                [QgsProcessing.TypeVectorPolygon]
            )
        )
        self.addParameter(
            QgsProcessingParameterVectorDestination(
                self.OUTPUT,
                'Output Geology Layer'
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        source = self.parameterAsSource(parameters, self.INPUT, context)
        
        # 1. Get the bounding box of the AOI and transform it to EPSG:3089
        crs_aoi = source.sourceCrs()
        crs_3089 = QgsCoordinateReferenceSystem("EPSG:3089")
        transform = QgsCoordinateTransform(crs_aoi, crs_3089, context.project())
        
        bbox_geom = QgsGeometry.fromRect(source.sourceExtent())
        bbox_geom.transform(transform)
        bbox = bbox_geom.boundingBox()
        
        xmin, ymin, xmax, ymax = bbox.xMinimum(), bbox.yMinimum(), bbox.xMaximum(), bbox.yMaximum()
        
        # 2. Tell QGIS's native ArcGIS engine exactly what to fetch
        base_url = "https://kgs.uky.edu/arcgis/rest/services/KY_Geo/MapServer/9"
        
        # The exact string format required by the QGIS arcgisfeatureserver provider
        uri = f"crs='EPSG:3089' bbox='{xmin},{ymin},{xmax},{ymax}' url='{base_url}'"
        
        feedback.pushInfo(f"Connecting to KGS Server native engine for bounding box: {xmin}, {ymin}, {xmax}, {ymax}")
        
        # 3. Spin up the virtual layer (letting QGIS handle the internet connection natively)
        temp_layer = QgsVectorLayer(uri, "temp_geology", "arcgisfeatureserver")
        
        if not temp_layer.isValid():
            feedback.reportError("QGIS native engine failed to connect to the KGS server.")
            return {}
            
        feedback.pushInfo("Successfully connected. Reprojecting AOI for accurate clipping...")
        
        # 4. Save the data to the hard drive as your final output
        output_file = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)
        
        try:
            # First reproject the original AOI to match the 3089 Geology layer
            reprojected_aoi = processing.run("native:reprojectlayer", {
                'INPUT': parameters[self.INPUT],
                'TARGET_CRS': crs_3089,
                'OUTPUT': 'TEMPORARY_OUTPUT'
            }, context=context, feedback=feedback)['OUTPUT']

            feedback.pushInfo("Clipping features to the exact AOI and saving...")
            
            processing.run("native:clip", {
                'INPUT': temp_layer,
                'OVERLAY': reprojected_aoi,
                'OUTPUT': output_file
            }, context=context, feedback=feedback)
            
            feedback.pushInfo("Geology layer successfully fetched, clipped, and saved in EPSG:3089!")
        except Exception as e:
            feedback.reportError(f"Failed to process output geology layer: {str(e)}")
            return {}

        return {self.OUTPUT: output_file}

    def name(self):
        return 'geologyfetcher'

    def displayName(self):
        return 'KGS Geology Fetcher'

    def group(self):
        return 'Site Assessment Tools'

    def groupId(self):
        return 'site_assessment_tools'

    def createInstance(self):
        return GeologyFetcher()