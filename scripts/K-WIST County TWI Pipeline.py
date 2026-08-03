import os
import shutil
import tempfile
import time
import traceback
import processing
from qgis.PyQt.QtCore import QCoreApplication, QSettings
from qgis.core import (QgsProcessing,
                       QgsProcessingAlgorithm,
                       QgsProcessingException,
                       QgsProcessingMultiStepFeedback,
                       QgsProcessingContext,
                       QgsCoordinateTransform,
                       QgsProcessingParameterRasterLayer,
                       QgsProcessingParameterVectorLayer,
                       QgsProcessingParameterField,
                       QgsProcessingParameterDistance,
                       QgsProcessingParameterFolderDestination,
                       QgsProcessingParameterBoolean,
                       QgsProcessingParameterFile,
                       QgsVectorLayer,
                       QgsFeature,
                       QgsVectorFileWriter,
                       QgsCoordinateTransformContext,
                       QgsApplication,
                       QgsProject)


TWI_MODEL_DISPLAY = "Topographic Wetness Index (TWI)"
TWI_MODEL_FILE = "Topographic Wetness Index (TWI).model3"
SAGA_ALG_IDS = [
    "sagang:fillsinkswangliu",
    "sagang:flowaccumulationtopdown",
    "sagang:slopeaspectcurvature",
    "sagang:topographicwetnessindextwi",
]


class KWISTCountyTWIPipeline(QgsProcessingAlgorithm):
    INPUT_RASTER = 'INPUT_RASTER'
    INPUT_VECTOR = 'INPUT_VECTOR'
    ID_COLUMN = 'ID_COLUMN'
    BUFFER_DIST = 'BUFFER_DIST'
    TWI_MODEL_PATH = 'TWI_MODEL_PATH'
    KEEP_INTERMEDIATES = 'KEEP_INTERMEDIATES'
    OUTPUT_DIR = 'OUTPUT_DIR'
    LOG_DIR = 'LOG_DIR'

    def tr(self, string):
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return KWISTCountyTWIPipeline()

    def name(self):
        return 'kwist_county_twi_pipeline'

    def displayName(self):
        return self.tr('K-WIST County TWI Pipeline')

    def group(self):
        return self.tr('K-WIST Scripts')

    def groupId(self):
        return 'kwist_scripts'

    def shortHelpString(self):
        return self.tr(
            "Full pipeline: clips a DEM to buffered HUC12 chips, computes TWI via the "
            "Topographic Wetness Index model, trims chips back to original boundaries, "
            "and compiles a VRT mosaic.\n\n"
            "Prerequisites:\n"
            "- SAGA Next Gen provider must be active in Processing\n"
            "- The 'Topographic Wetness Index (TWI)' model must be registered in Processing\n"
            "  (Settings \u2192 Processing \u2192 Models \u2192 Add Model\u2026)"
        )

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterRasterLayer(
            self.INPUT_RASTER, 'Source DEM'))

        self.addParameter(QgsProcessingParameterVectorLayer(
            self.INPUT_VECTOR, 'Mask Vector (e.g., HUC12 boundaries)'))

        self.addParameter(QgsProcessingParameterField(
            self.ID_COLUMN, 'Unique ID Column (Used for naming chips)',
            parentLayerParameterName=self.INPUT_VECTOR))

        self.addParameter(QgsProcessingParameterDistance(
            self.BUFFER_DIST, 'Buffer Distance (Meters)',
            defaultValue=200, parentParameterName=self.INPUT_VECTOR))

        self.addParameter(QgsProcessingParameterFile(
            self.TWI_MODEL_PATH, 'TWI Model (.model3)',
            behavior=QgsProcessingParameterFile.File,
            extension='model3',
            optional=True))

        self.addParameter(QgsProcessingParameterBoolean(
            self.KEEP_INTERMEDIATES, 'Keep intermediate files (_Buffered, _TWI, _FILLED, _FLOW, _SLOPE)',
            defaultValue=True))

        self.addParameter(QgsProcessingParameterFolderDestination(
            self.OUTPUT_DIR, 'Target Output Directory'))

        self.addParameter(QgsProcessingParameterFile(
            self.LOG_DIR, 'Log directory (optional; defaults to output dir)',
            behavior=QgsProcessingParameterFile.Folder,
            optional=True))

    def _check_prerequisites(self, model_file, feedback):
        """Verify SAGA algorithms and TWI model are available. Return model ID."""
        feedback.pushInfo("Checking prerequisites\u2026")

        registry = QgsApplication.processingRegistry()

        missing = [aid for aid in SAGA_ALG_IDS if not registry.algorithmById(aid)]
        if missing:
            lines = ["The following SAGA algorithms are missing from Processing:"]
            for aid in missing:
                lines.append(f"  \u2022 {aid}")
            lines.append("")

            saga_bin = shutil.which("saga_cmd")
            qgis_saga = QSettings().value("SAGAS_PATH", "")

            if saga_bin:
                lines.append(
                    f"SAGA was found on your system at: {saga_bin}\n"
                    "but the Processing provider is not active.\n"
                    "Go to Processing \u2192 Options \u2192 Providers \u2192 SAGA Next Gen\n"
                    "and verify the SAGA path is set correctly."
                )
            elif qgis_saga and os.path.isfile(qgis_saga):
                lines.append(
                    f"SAGA is configured in QGIS at:\n  {qgis_saga}\n"
                    "but the SAGA Next Gen provider is not active.\n"
                    "Go to Processing \u2192 Options \u2192 Providers \u2192 SAGA Next Gen\n"
                    "and ensure it is enabled."
                )
            else:
                lines.append(
                    "SAGA GIS does not appear to be installed or configured.\n"
                    "1. Install SAGA (https://saga-gis.org)\n"
                    "2. In QGIS go to Processing \u2192 Options \u2192 Providers \u2192 SAGA Next Gen\n"
                    "3. Set the SAGA path to the installation directory"
                )

            raise QgsProcessingException("\n".join(lines))

        feedback.pushInfo("All SAGA algorithms are available.")

        twi_id = None
        for alg in registry.algorithms():
            if alg.displayName() == TWI_MODEL_DISPLAY:
                twi_id = alg.id()
                feedback.pushInfo(f"Found registered TWI model: {twi_id}")
                break

        if not twi_id and model_file and os.path.isfile(model_file):
            feedback.pushInfo("TWI model not registered. Attempting to load from file\u2026")
            from qgis.core import QgsProcessingModelAlgorithm
            temp = QgsProcessingModelAlgorithm()
            if temp.fromFile(model_file):
                if not registry.addAlgorithm(temp):
                    existing = registry.algorithmById(temp.id())
                    if existing:
                        twi_id = existing.id()
                else:
                    twi_id = temp.id()
                if twi_id:
                    feedback.pushInfo(f"Loaded TWI model: {twi_id}")

        if not twi_id:
            raise QgsProcessingException(
                f"The '{TWI_MODEL_DISPLAY}' model could not be found.\n"
                f"Please register it in Processing (Settings \u2192 Processing \u2192 Models \u2192 Add Model\u2026) "
                f"or provide a valid path to '{TWI_MODEL_FILE}' in the TWI Model parameter.")

        return twi_id

    def _append_log(self, log_path, level, message):
        with open(log_path, 'a') as f:
            f.write(f"{time.strftime('%Y-%m-%dT%H:%M:%S')}   {level:7s}   {message}\n")

    def processAlgorithm(self, parameters, context, feedback):
        raster_layer = self.parameterAsRasterLayer(parameters, self.INPUT_RASTER, context)
        vector_layer = self.parameterAsVectorLayer(parameters, self.INPUT_VECTOR, context)
        id_col = self.parameterAsString(parameters, self.ID_COLUMN, context)
        buffer_dist = self.parameterAsDouble(parameters, self.BUFFER_DIST, context)
        model_file = self.parameterAsString(parameters, self.TWI_MODEL_PATH, context)
        keep_intermediates = self.parameterAsBool(parameters, self.KEEP_INTERMEDIATES, context)
        out_dir = self.parameterAsString(parameters, self.OUTPUT_DIR, context)

        if raster_layer is None:
            raise QgsProcessingException("A Source DEM must be selected.")
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)

        twi_model_id = self._check_prerequisites(model_file, feedback)

        target_crs = raster_layer.crs()
        transform = QgsCoordinateTransform(vector_layer.crs(), target_crs, context.transformContext())

        total_features = vector_layer.featureCount()
        if total_features == 0:
            raise QgsProcessingException("Input vector layer is empty.")

        feedback.pushInfo(f"Targeting Raster CRS: {target_crs.authid()}")
        feedback.pushInfo(f"Processing {total_features} feature(s) through the full pipeline\u2026")

        multi_feedback = QgsProcessingMultiStepFeedback(total_features * 3 + 1, feedback)
        final_chip_paths = []
        intermediate_chip_paths = {'FILLED': [], 'FLOW': [], 'SLOPE': []}

        log_dir = self.parameterAsString(parameters, self.LOG_DIR, context) or out_dir
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        log_path = os.path.join(log_dir, f"twi_pipeline_{timestamp}.log")
        self._append_log(log_path, "INFO", f"Pipeline started — {total_features} feature(s), buffer={buffer_dist}m, keep_intermediates={keep_intermediates}")

        for i, feat in enumerate(vector_layer.getFeatures()):
            if feedback.isCanceled():
                break

            step_base = i * 3
            uid = str(feat[id_col]).replace(" ", "_")

            try:
                geom = feat.geometry()
                geom.transform(transform)
                buf_geom = geom.buffer(buffer_dist, 5) if buffer_dist > 0 else geom

                # ---------- Step 1: Clip buffered DEM chip ----------
                multi_feedback.setCurrentStep(step_base)
                feedback.pushInfo(f"[{i+1}/{total_features}] Clipping buffered DEM: {uid}\u2026")

                buffered_path = os.path.join(out_dir, f"{uid}_Buffered.tif")
                self._clip_raster(
                    raster_layer, buf_geom, target_crs, buffered_path,
                    context, multi_feedback
                )

                # ---------- Step 2: Run TWI model on the chip ----------
                multi_feedback.setCurrentStep(step_base + 1)
                feedback.pushInfo(f"[{i+1}/{total_features}] Computing TWI: {uid}\u2026")

                twi_path = os.path.join(out_dir, f"{uid}_TWI.tif")
                twi_temp_dir = tempfile.mkdtemp(dir='/mnt/Z/temp/', prefix=f"twi_{uid}_")
                twi_ctx = QgsProcessingContext()
                twi_ctx.setProject(QgsProject.instance())
                twi_ctx.setTemporaryFolder(twi_temp_dir)
                try:
                    model_results = processing.run(twi_model_id, {
                        'input_dem': buffered_path,
                        'site_twi': twi_path,
                    }, context=twi_ctx, feedback=multi_feedback)

                    if keep_intermediates:
                        child_ids = {
                            'FILLED': ('sagang:fillsinkswangliu_1', 'FILLED'),
                            'FLOW': ('sagang:flowaccumulationtopdown_1', 'FLOW'),
                            'SLOPE': ('sagang:slopeaspectcurvature_1', 'SLOPE'),
                        }
                        child_results = model_results.get('CHILD_RESULTS', {})
                        for name, (child_id, output_name) in child_ids.items():
                            src = child_results.get(child_id, {}).get(output_name)
                            if src and os.path.isfile(src):
                                dst = os.path.join(out_dir, f"{uid}_{name}.tif")
                                processing.run("gdal:translate", {
                                    'INPUT': src,
                                    'OUTPUT': dst,
                                }, context=context, feedback=multi_feedback, is_child_algorithm=True)
                                intermediate_chip_paths[name].append(dst)
                finally:
                    try:
                        shutil.rmtree(twi_temp_dir)
                    except OSError as e:
                        self._append_log(log_path, "WARN",
                            f"Failed to remove temp dir {twi_temp_dir}: {e}")

                if not os.path.isfile(twi_path):
                    raise QgsProcessingException(
                        f"TWI model completed but output file was not created: {twi_path}")

                # ---------- Step 3: Trim to original boundary ----------
                multi_feedback.setCurrentStep(step_base + 2)
                feedback.pushInfo(f"[{i+1}/{total_features}] Trimming to original boundary: {uid}\u2026")

                final_path = os.path.join(out_dir, f"{uid}_Final.tif")
                self._clip_raster(
                    twi_path, geom, target_crs, final_path,
                    context, multi_feedback
                )
                final_chip_paths.append(final_path)

                # ---------- Clean up intermediates ----------
                if not keep_intermediates:
                    for path in (buffered_path, twi_path):
                        try:
                            if os.path.isfile(path):
                                os.remove(path)
                        except OSError:
                            pass

                self._append_log(log_path, "INFO", f"[{i+1}/{total_features}] {uid} — OK")

            except Exception as e:
                msg = f"[{i+1}/{total_features}] {uid} — FAILED: {e}"
                feedback.pushInfo(msg)
                self._append_log(log_path, "FAIL", f"{msg}\n{traceback.format_exc()}")
                continue

        # ---------- Step 4: Build VRT mosaics ----------
        if final_chip_paths:
            multi_feedback.setCurrentStep(total_features * 3)
            feedback.pushInfo("Compiling Virtual Raster (VRT) Mosaic\u2026")

            vrt_temp_dir = tempfile.mkdtemp(dir='/mnt/Z/temp/', prefix='vrt_')
            context.setTemporaryFolder(vrt_temp_dir)

            vrt_output = os.path.join(out_dir, "KWIST_Master_Mosaic.vrt")
            processing.run("gdal:buildvirtualraster", {
                'INPUT': final_chip_paths,
                'RESOLUTION': 1,
                'SEPARATE': False,
                'PROJ_DIFFERENCE': False,
                'OUTPUT': vrt_output,
            }, context=context, feedback=multi_feedback, is_child_algorithm=True)

            feedback.pushInfo(f"TWI VRT: {vrt_output}")

            for name in ('FILLED', 'FLOW', 'SLOPE'):
                chips = intermediate_chip_paths.get(name, [])
                if chips:
                    vrt_path = os.path.join(out_dir, f"KWIST_{name}_Mosaic.vrt")
                    processing.run("gdal:buildvirtualraster", {
                        'INPUT': chips,
                        'RESOLUTION': 1,
                        'SEPARATE': False,
                        'PROJ_DIFFERENCE': False,
                        'OUTPUT': vrt_path,
                    }, context=context, feedback=multi_feedback, is_child_algorithm=True)
                    feedback.pushInfo(f"{name} VRT: {vrt_path}")

            try:
                shutil.rmtree(vrt_temp_dir)
            except OSError:
                pass

        return {self.OUTPUT_DIR: out_dir}

    def _clip_raster(self, input_raster, clip_geom, crs, output_path, context, feedback):
        """Clip a raster to a polygon geometry."""
        clip_geom = clip_geom.buffer(0, 5)
        fd, mask_path = tempfile.mkstemp(suffix='.gpkg')
        os.close(fd)

        mask_layer = QgsVectorLayer(
            f"MultiPolygon?crs={crs.authid()}", "mask", "memory")
        feat = QgsFeature()
        feat.setGeometry(clip_geom)
        mask_layer.dataProvider().addFeatures([feat])
        mask_layer.updateExtents()

        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = "GPKG"
        QgsVectorFileWriter.writeAsVectorFormatV2(
            mask_layer, mask_path, QgsCoordinateTransformContext(), options)

        processing.run("gdal:cliprasterbymasklayer", {
            'INPUT': input_raster,
            'MASK': mask_path,
            'SOURCE_CRS': crs,
            'TARGET_CRS': crs,
            'CROP_TO_CUTLINE': True,
            'KEEP_RESOLUTION': True,
            'OPTIONS': 'COMPRESS=LZW',
            'OUTPUT': output_path,
        }, context=context, feedback=feedback, is_child_algorithm=True)

        if not os.path.isfile(output_path):
            raise QgsProcessingException(
                f"Clipping completed but output not created: {output_path}")

        try:
            os.remove(mask_path)
        except OSError:
            pass
