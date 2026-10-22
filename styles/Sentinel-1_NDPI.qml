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
    <rasterrenderer nodataColor="" classificationMax="0.9" alphaBand="-1" band="1" type="singlebandpseudocolor" opacity="1" classificationMin="0.5">
      <rasterTransparency/>
      <minMaxOrigin>
        <limits>None</limits>
        <extent>WholeRaster</extent>
        <statAccuracy>Estimated</statAccuracy>
        <cumulativeCutLower>0.02</cumulativeCutLower>
        <cumulativeCutUpper>0.98</cumulativeCutUpper>
        <stdDevFactor>2</stdDevFactor>
      </minMaxOrigin>
      <rastershader>
        <colorrampshader labelPrecision="4" minimumValue="0.5" colorRampType="INTERPOLATED" clip="0" maximumValue="0.90000000000000002" classificationMode="1">
          <colorramp name="[source]" type="gradient">
            <Option type="Map">
              <Option name="color1" type="QString" value="44,123,182,255,rgb:0.172549,0.4823529,0.7137255,1"/>
              <Option name="color2" type="QString" value="215,25,28,255,rgb:0.8431373,0.0980392,0.1098039,1"/>
              <Option name="direction" type="QString" value="cw"/>
              <Option name="discrete" type="QString" value="0"/>
              <Option name="rampType" type="QString" value="gradient"/>
              <Option name="spec" type="QString" value="rgb"/>
              <Option name="stops" type="QString" value="0.25;171,217,233,255,rgb:0.6705882,0.8509804,0.9137255,1;rgb;cw:0.5;255,255,191,255,rgb:1,1,0.7490196,1;rgb;cw:0.75;253,174,97,255,rgb:0.9921569,0.6823529,0.3803922,1;rgb;cw"/>
            </Option>
          </colorramp>
          <item color="#2c7bb6" alpha="255" value="0.5" label="0.5000"/>
          <item color="#abd9e9" alpha="255" value="0.6" label="0.6000"/>
          <item color="#ffffbf" alpha="255" value="0.7" label="0.7000"/>
          <item color="#fdae61" alpha="255" value="0.8" label="0.8000"/>
          <item color="#d7191c" alpha="255" value="0.9" label="0.9000"/>
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
        </colorrampshader>
      </rastershader>
    </rasterrenderer>
    <brightnesscontrast brightness="0" contrast="0" gamma="1"/>
    <huesaturation colorizeStrength="100" colorizeOn="0" colorizeRed="255" colorizeBlue="128" invertColors="0" grayscaleMode="0" colorizeGreen="128" saturation="0"/>
    <rasterresampler maxOversampling="2"/>
    <resamplingStage>resamplingFilter</resamplingStage>
  </pipe>
  <blendMode>0</blendMode>
</qgis>
