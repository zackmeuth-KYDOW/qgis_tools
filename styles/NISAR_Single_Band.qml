<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis version="3.44.13-Solothurn" styleCategories="Symbology">
  <pipe-data-defined-properties>
    <Option type="Map">
      <Option name="name" type="QString" value=""/>
      <Option name="properties"/>
      <Option name="type" type="QString" value="collection"/>
    </Option>
  </pipe-data-defined-properties>
  <pipe>
    <provider>
      <resampling zoomedOutResamplingMethod="nearestNeighbour" enabled="false" zoomedInResamplingMethod="nearestNeighbour" maxOversampling="2"/>
    </provider>
    <rasterrenderer nodataColor="" alphaBand="-1" grayBand="1" type="singlebandgray" opacity="1" gradient="BlackToWhite">
      <rasterTransparency/>
      <minMaxOrigin>
        <limits>CumulativeCut</limits>
        <extent>WholeRaster</extent>
        <statAccuracy>Estimated</statAccuracy>
        <cumulativeCutLower>0.02</cumulativeCutLower>
        <cumulativeCutUpper>0.98</cumulativeCutUpper>
        <stdDevFactor>2</stdDevFactor>
      </minMaxOrigin>
      <contrastEnhancement>
        <minValue>0.0327563</minValue>
        <maxValue>0.753167</maxValue>
        <algorithm>StretchToMinimumMaximum</algorithm>
      </contrastEnhancement>
      <rampLegendSettings useContinuousLegend="1" minimumLabel="" direction="0" maximumLabel="" suffix="" prefix="" orientation="2">
        <numericFormat id="basic">
          <Option type="Map">
            <Option name="decimal_separator" type="invalid"/>
            <Option name="decimals" type="int" value="6"/>
            <Option name="rounding_type" type="int" value="0"/>
            <Option name="show_plus" type="bool" value="false"/>
            <Option name="show_thousand_separator" type="bool" value="true"/>
            <Option name="show_trailing_zeros" type="bool" value="false"/>
            <Option name="thousand_separator" type="invalid"/>
          </Option>
        </numericFormat>
      </rampLegendSettings>
    </rasterrenderer>
    <brightnesscontrast brightness="0" contrast="0" gamma="1"/>
    <huesaturation colorizeStrength="100" colorizeOn="0" colorizeRed="255" colorizeBlue="128" invertColors="0" grayscaleMode="0" colorizeGreen="128" saturation="0"/>
    <rasterresampler maxOversampling="2"/>
    <resamplingStage>resamplingFilter</resamplingStage>
  </pipe>
  <blendMode>0</blendMode>
</qgis>
