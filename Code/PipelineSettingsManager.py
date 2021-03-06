from Code.SettingsManager import SettingsManager


class PipelineSettingsManager(SettingsManager):

    """ This class is a subclass of the SettingsManager and
    stores the settings (and their defaults) used by RenderPipeline. """

    def __init__(self):
        """ Constructs a new PipelineSettingsManager. Remember to call
        loadFromFile to load actual settings instead of the defaults. """
        SettingsManager.__init__(self, "PipelineSettings")

    def _addDefaultSettings(self):
        """ Internal method which populates the settings array with defaults
        and the internal type of settings (like int, bool, ...) """

        # [General]
        self._addSetting("preventMultipleInstances", bool, False)
        self._addSetting("resolution3D", float, 1.0)
        self._addSetting("stateCacheClearInterval", float, 0.2)

        # [Rendering]
        self._addSetting("enableEarlyZ", bool, True)

        # [Antialiasing]
        self._addSetting("antialiasingTechnique", str, "SMAA")
        self._addSetting("smaaQuality", str, "Low")
        self._addSetting("jitterAmount", float, 1.0)

        # [Lighting]
        self._addSetting("computePatchSizeX", int, 32)
        self._addSetting("computePatchSizeY", int, 32)
        self._addSetting("defaultReflectionCubemap", str, "Default-0/#.png")
        self._addSetting("colorLookupTable", str, "Default.png")
        self._addSetting("cubemapAntialiasingFactor", float, 5.0)
        self._addSetting("useAdaptiveBrightness", bool, True)
        self._addSetting("targetExposure", float, 0.8)
        self._addSetting("brightnessAdaptionSpeed", float, 1.0)
        self._addSetting("globalAmbientFactor", float, 1.0)
        self._addSetting("useColorCorrection", bool, True)
        self._addSetting("enableAlphaTestedShadows", bool, True)
        self._addSetting("useDiffuseAntialiasing", bool, True)

        # [Scattering]
        self._addSetting("enableScattering", bool, False)
        self._addSetting("scatteringCubemapSize", int, 256)

        # [SSLR]
        self._addSetting("enableSSLR", bool, True)
        self._addSetting("sslrUseHalfRes", bool, False)
        self._addSetting("sslrNumSteps", int, 32)
        self._addSetting("sslrScreenRadius", float, 0.3)

        # [Occlusion]
        self._addSetting("occlusionTechnique", str, "None")
        self._addSetting("occlusionRadius", float, 1.0)
        self._addSetting("occlusionStrength", float, 1.0)
        self._addSetting("occlusionSampleCount", int, 16)
        self._addSetting("useTemporalOcclusion", bool, True)
        self._addSetting("useLowQualityBlur", bool, False)
        self._addSetting("useOcclusionNoise", bool, True)
        
        # [Shadows]
        self._addSetting("renderShadows", bool, True)
        self._addSetting("shadowAtlasSize", int, 8192)
        self._addSetting("shadowCascadeBorderPercentage", float, 0.1)       
        self._addSetting("maxShadowUpdatesPerFrame", int, 2)
        self._addSetting("numPCFSamples", int, 64)
        self._addSetting("usePCSS", bool, True)
        self._addSetting("numPCSSSearchSamples", int, 32)
        self._addSetting("numPCSSFilterSamples", int, 64)
        self._addSetting("useHardwarePCF", bool, False)
        self._addSetting("alwaysUpdateAllShadows", bool, False)
        self._addSetting("pcssSampleRadius", float, 0.01)

        # [Transparency]
        self._addSetting("useTransparency", bool, True)
        self._addSetting("maxTransparencyLayers", int, 10)
        self._addSetting("maxTransparencyRange", float, 100.0)
        self._addSetting("transparencyBatchSize", int, 200)

        # [Motion blur]
        self._addSetting("enableMotionBlur", bool, False)
        self._addSetting("motionBlurSamples", int, 8)
        self._addSetting("motionBlurFactor", float, 1.0)
        self._addSetting("motionBlurDilatePixels", float, 10.0)

        # [Global Illumination]
        self._addSetting("enableGlobalIllumination", bool, False)
        self._addSetting("giVoxelGridSize", float, 100.0)
        self._addSetting("giQualityLevel", str, "High")

        # [Clouds]
        self._addSetting("enableClouds", bool, False)

        # [Bloom]
        self._addSetting("enableBloom", bool, False)

        # [Depth of Field]
        self._addSetting("enableDOF", bool, True)

        # [Debugging]
        self._addSetting("displayOnscreenDebugger", bool, False)
        self._addSetting("displayDebugStats", bool, True)
        self._addSetting("displayPerformanceOverlay", bool, True)
        self._addSetting("pipelineOutputLevel", str, "debug")
        self._addSetting("useDebugAttachments", bool, False)
