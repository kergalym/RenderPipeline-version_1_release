
from panda3d.core import Vec3, Vec2, TexturePool, RenderState, TransformState
from direct.interval.IntervalGlobal import Parallel, Sequence, Wait

from Code.Globals import Globals
from Code.DebugObject import DebugObject
from Code.MemoryMonitor import MemoryMonitor
from Code.GUI.BufferViewerGUI import BufferViewerGUI
from Code.GUI.BetterOnscreenImage import BetterOnscreenImage
from Code.GUI.BetterSlider import BetterSlider
from Code.GUI.BetterOnscreenText import BetterOnscreenText
from Code.GUI.CheckboxWithLabel import CheckboxWithLabel
from Code.GUI.CheckboxCollection import CheckboxCollection
from Code.GUI.UIWindow import UIWindow
from Code.GUI.FastText import FastText
from Code.GUI.PerformanceOverlay import PerformanceOverlay


class PipelineGuiManager(DebugObject):

    """ This class manages the onscreen debug gui for
    the pipeline """

    def __init__(self, pipeline):
        DebugObject.__init__(self, "GUIManager")
        self.pipeline = pipeline
        self.body = Globals.base.pixel2d
        self.showbase = pipeline.showbase
        self.guiActive = False
        self.enableGISliders = False
        self.window = UIWindow(
            "Pipeline Debugger", 280, Globals.base.win.getYSize())
        self.defines = {}
        self.bufferViewerParent = Globals.base.pixel2d.attachNewNode(
            "Buffer Viewer GUI")
        self.bufferViewer = BufferViewerGUI(self.bufferViewerParent)
        self.setup()



    def update(self):
        if self.memUsageText:

            memstr = str(round(MemoryMonitor.getEstimatedMemUsage() / 1024.0 / 1024.0, 2))

            numTextureBytes = 0
            renderTextures = Globals.render.findAllTextures()
            for tex in renderTextures:
                numTextureBytes += MemoryMonitor._calculateTexSize(tex)

            texstr = str(round(numTextureBytes / 1024.0 / 1024.0, 2))

            otherTextures = TexturePool.findAllTextures()
            numOtherBytes = 0
            for tex in otherTextures:
                if tex not in renderTextures:
                    numOtherBytes += MemoryMonitor._calculateTexSize(tex)
            
            otherstr = str(round(numOtherBytes / 1024.0 / 1024.0, 2))

            self.memUsageText.setText("VRAM Usage: " + memstr + " MB / Textures: " + texstr + " MB / Other: " + otherstr + " MB")

        if self.fpsText:
            clock = Globals.clock
            self.fpsText.setText("Frame time over {:3.1f}s     Avg: {:3.2f}     Max: {:3.2f}     Deviation: {:3.2f}".format(
                clock.getAverageFrameRateInterval(), 
                1000.0 / clock.getAverageFrameRate(),
                clock.getMaxFrameDuration() * 1000.0,
                clock.calcFrameRateDeviation() * 1000.0
                ))

        if self.stateText:
            self.stateText.setText("{:6d} Render States, {:6d} Transform States".format(RenderState.getNumStates(), TransformState.getNumStates()))

        if self.perfOverlay:
            self.perfOverlay.update()



    def setup(self):
        """ Setups this manager """
        self.debug("Creating GUI ..")
        self.initialized = False
        self.rootNode = self.body.attachNewNode("GUIManager")
        self.rootNode.setPos(0, 1, 0)
        self.watermark = BetterOnscreenImage(
            image="Data/GUI/Watermark.png", parent=self.rootNode,
            x=20, y=20, w=230, h=55)
        self.showDebugger = BetterOnscreenImage(
            image="Data/GUI/ShowDebugger.png", parent=self.rootNode,
            x=20, y=80, w=230, h=36)
        self.debuggerParent = self.window.getNode()
        self.debuggerParent.setPos(-350, 0, 0)
        self.debuggerContent = self.window.getContentNode()
        self._initSettings()
        self.showbase.accept("g", self._toggleGUI)
        self.currentGUIEffect = None
        self.memUsageText = None
        self.fpsText = None
        self.perfOverlay = None
        self.stateText = None

        self.regenerateShaderHint = BetterOnscreenImage(
            image="Data/GUI/RegeneratingShaders.png", parent=self.rootNode,
            x=(Globals.base.win.getXSize() - 280)/2, y=Globals.base.win.getYSize() - 90, w=280, h=56)
        self.hintFadeEffect = None
        self.regenerateShaderHint.hide()

        if self.pipeline.settings.displayDebugStats:
            self.memUsageText = FastText(pos=Vec2(
                Globals.base.getAspectRatio() - 0.1, 0.76), rightAligned=True, color=Vec3(1, 1, 0), size=0.03)
            self.fpsText = FastText(pos=Vec2(
                Globals.base.getAspectRatio() - 0.1, 0.72), rightAligned=True, color=Vec3(1, 1, 0), size=0.03)
            self.stateText = FastText(pos=Vec2(
                Globals.base.getAspectRatio() - 0.1, 0.68), rightAligned=True, color=Vec3(1, 1, 0), size=0.03)


        if self.pipeline.settings.displayPerformanceOverlay:
            self.perfOverlay = PerformanceOverlay(self.pipeline)
            self.showbase.accept("tab", self.perfOverlay.toggle)

        # Globals.clock.setAverageFrameRateInterval(3.0)

    def _initSettings(self):
        """ Inits all debugging settings """

        currentY = 10

        # Render Modes
        self.renderModes = CheckboxCollection()

        # Handle to the settings
        s = self.pipeline.settings

        modes = []
        features = []

        register_mode = lambda name, mid: modes.append((name, mid))
        register_feature = lambda name, fid: features.append((name, fid))

        register_mode("Default", "rm_Default")
        register_mode("Metallic", "rm_Metallic")
        register_mode("BaseColor", "rm_BaseColor")
        register_mode("Roughness", "rm_Roughness")
        register_mode("Specular", "rm_Specular")
        register_mode("Normal", "rm_Normal")
        register_mode("Velocity", "rm_Velocity")

        if s.occlusionTechnique != "None":
            register_mode("Occlusion", "rm_Occlusion")
            register_feature("Occlusion", "ft_OCCLUSION")


        register_feature("Upscale Blur", "ft_UPSCALE_BLUR")

        register_mode("Lighting", "rm_Lighting")
        register_mode("Raw-Lighting", "rm_Diffuse_Lighting")

        if s.enableScattering:
            register_mode("Scattering", "rm_Scattering")
            register_feature("Scattering", "ft_SCATTERING")

        if s.enableGlobalIllumination:
            register_mode("GI-Diffuse", "rm_GI_DIFFUSE")
            register_mode("GI-Specular", "rm_GI_REFLECTIONS")
            register_feature("G-Illum", "ft_GI")

        register_mode("Ambient", "rm_Ambient")
        register_feature("Ambient", "ft_AMBIENT")

        if s.enableMotionBlur:
            register_feature("Motion Blur", "ft_MOTIONBLUR")

        if s.antialiasingTechnique != "None":
            register_feature("Anti-Aliasing", "ft_ANTIALIASING")

        register_feature("Shadows", "ft_SHADOWS")
        register_feature("Correct color", "ft_COLOR_CORRECTION")
        
        if s.renderShadows:
            register_mode("PSSM Splits", "rm_PSSM_SPLITS")
            register_mode("Shadowing", "rm_SHADOWS")
            
            if s.usePCSS:
                register_feature("PCSS", "ft_PCSS")

            register_feature("PCF", "ft_PCF")

        register_feature("Env. Filtering", "ft_FILTER_ENVIRONMENT")
        register_feature("PBS", "ft_COMPLEX_LIGHTING")

        if s.enableSSLR:
            register_mode("SSLR", "rm_SSLR")
            register_feature("SSLR", "ft_SSLR")

        if s.enableBloom:
            register_mode("Bloom", "rm_BLOOM")
            register_feature("Bloom", "ft_BLOOM")


        if s.useTransparency:
            register_feature("Transparency", "ft_TRANSPARENCY")

        if s.useDiffuseAntialiasing:
            register_feature("Diffuse AA", "ft_DIFFUSE_AA")

        # register_mode("Shadow Load", "rm_SHADOW_COMPUTATIONS")
        # register_mode("Lights Load", "rm_LIGHT_COMPUTATIONS")

        self.renderModesTitle = BetterOnscreenText(text="Render Mode",
                                                   x=20, y=currentY,
                                                   parent=self.debuggerContent,
                                                   color=Vec3(1), size=15)

        currentY += 80
        isLeft = True
        for modeName, modeID in modes:

            box = CheckboxWithLabel(
                parent=self.debuggerParent, x=20 if isLeft else 158, y=currentY,
                chbCallback=self._updateSetting, chbArgs=[modeID, False],
                radio=True, textSize=14, text=modeName, textColor=Vec3(0.6),
                chbChecked=modeID == "rm_Default")
            self.renderModes.add(box.getCheckbox())

            isLeft = not isLeft

            if isLeft:
                currentY += 25

        self.featuresTitle = BetterOnscreenText(text="Toggle Features",
                                                x=20, y=currentY, parent=self.debuggerContent, color=Vec3(1), size=15)

        currentY += 80
        isLeft = True
        for featureName, featureID in features:

            box = CheckboxWithLabel(
                parent=self.debuggerParent, x=20 if isLeft else 158, y=currentY,
                chbCallback=self._updateSetting, chbArgs=[featureID, True],
                textSize=14, text=featureName, textColor=Vec3(0.6),
                chbChecked=True)

            isLeft = not isLeft

            if isLeft:
                currentY += 25

        self.demoSlider = BetterSlider(
            x=20, y=currentY+20, size=230, parent=self.debuggerContent)

        self.demoText = BetterOnscreenText(x=20, y=currentY,
                                       text="Sun Position", align="left", parent=self.debuggerContent,
                                       size=15, color=Vec3(1.0))

        currentY += 70


        if s.enableGlobalIllumination and self.enableGISliders:

            self.slider_opts = {
                "mip_multiplier": {
                    "name": "Mip Multiplier",
                    "min": 1.0,
                    "max": 3.0,
                    "default": 1.0,
                },
                "step_multiplier": {
                    "name": "Step Multiplier",
                    "min": 1.0,
                    "max": 3.0,
                    "default": 1.0,
                },
            }

           

            for name, opts in self.slider_opts.iteritems():
                opts["slider"] = BetterSlider(
                    x=20, y=currentY+20, size=230, minValue=opts["min"],maxValue=opts["max"], value=opts["default"], parent=self.debuggerContent, callback=self._optsChanged)

                opts["label"] = BetterOnscreenText(x=20, y=currentY,
                                               text=opts["name"], align="left", parent=self.debuggerContent,
                                               size=15, color=Vec3(1.0))

                opts["value_label"] = BetterOnscreenText(x=250, y=currentY,
                                               text=str(opts["default"]), align="right", parent=self.debuggerContent,
                                               size=15, color=Vec3(0.6),mayChange=True)
                currentY += 50


        self.initialized = True
            
    def onPipelineLoaded(self):

        if self.pipeline.settings.enableGlobalIllumination and self.enableGISliders:
            self._optsChanged()


    def onRegenerateShaders(self):

        if self.hintFadeEffect:
            self.hintFadeEffect.finish()

        self.regenerateShaderHint.show()
        Globals.base.graphicsEngine.renderFrame()
        Globals.base.graphicsEngine.renderFrame()
        Globals.base.graphicsEngine.renderFrame()

        self.regenerateShaderHint.hide()



    def _optsChanged(self):

        if not self.enableGISliders:
            return

        container = self.pipeline.globalIllum.finalPass

        for name, opt in self.slider_opts.iteritems():
            container.setShaderInput("opt_" + name, opt["slider"].getValue())
            opt["value_label"].setText("{:0.4f}".format(opt["slider"].getValue()))
        

    def _updateSetting(self, status, name, updateWhenFalse=False):
        # Render Modes

        if hasattr(self.pipeline, "renderPassManager"):

            define = lambda key, val: self.pipeline.getRenderPassManager().registerDefine(key, val)
            undefine = lambda key: self.pipeline.getRenderPassManager().unregisterDefine(key)

            if name.startswith("rm_"):
                modeId = "DEBUG_RM_" + name[3:].upper()

                if status:
                    define(modeId, 1)
                else:
                    undefine(modeId)

                if name == "rm_Default":
                    undefine("DEBUG_VISUALIZATION_ACTIVE")
                else:
                    define("DEBUG_VISUALIZATION_ACTIVE", 1)

            elif name.startswith("ft_"):
                # instead of enabling per feature, we disable per feature
                modeId = "DEBUG_DISABLE_" + name[3:].upper()

                if status:
                    undefine(modeId)
                else:
                    define(modeId, 1)

            if self.initialized and (status is True or updateWhenFalse):
                self.pipeline.reloadShaders()
                # pass

    def _toggleGUI(self):
        self.debug("Toggle overlay")

        if self.currentGUIEffect is not None:
            self.currentGUIEffect.finish()

        if not self.guiActive:
            # show debugger
            self.currentGUIEffect = Parallel(
                self.watermark.posInterval(
                    0.4, self.watermark.getInitialPos() + Vec3(0, 0, 200),
                    blendType="easeIn"),
                self.showDebugger.posInterval(
                    0.4, self.showDebugger.getInitialPos() + Vec3(0, 0, 400),
                    blendType="easeIn"),
                self.debuggerParent.posInterval(
                    0.3, Vec3(0, 0, 0), blendType="easeOut"),
                Sequence(
                    Wait(0.2),
                    self.bufferViewerParent.posInterval(
                        0.11, Vec3(30, 0, 0), blendType="easeOut")
                )
            )
            self.currentGUIEffect.start()

            # self.watermark.hide()
            # self.showDebugger.hide()

        else:
            # hide debugger
            self.currentGUIEffect = Parallel(
                self.watermark.posInterval(
                    0.4, self.watermark.getInitialPos(), blendType="easeOut"),
                self.showDebugger.posInterval(
                    0.4, self.showDebugger.getInitialPos(),
                    blendType="easeOut"),
                self.debuggerParent.posInterval(
                    0.3, Vec3(-350, 0, 0), blendType="easeInOut"),
                self.bufferViewerParent.posInterval(
                    0.15, Vec3(0, 0, 0), blendType="easeOut")
            )
            self.currentGUIEffect.start()

        self.guiActive = not self.guiActive
