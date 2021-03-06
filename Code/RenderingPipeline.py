from panda3d.core import NodePath, Shader, Vec4, TransparencyAttrib, LVecBase2i, Material, VBase4
from panda3d.core import PTAVecBase3f, PTAFloat, PTALMatrix4f, PTAInt, SamplerState
from panda3d.core import CSYupRight, TransformState, Mat4, CSZupRight, BitMask32
from panda3d.core import Texture, UnalignedLMatrix4f, Vec3, PTAFloat, TextureStage
from panda3d.core import ColorWriteAttrib, Vec2, AlphaTestAttrib, PStatClient
from panda3d.core import RenderState, TransformState

from Code.DebugObject import DebugObject
from Code.SystemAnalyzer import SystemAnalyzer
from Code.BugReporter import BugReporter
from Code.Scattering import Scattering
from Code.Globals import Globals
from Code.GlobalIllumination import GlobalIllumination
from Code.EffectLoader import EffectLoader

from Code.PipelineSettingsManager import PipelineSettingsManager
from Code.LightManager import LightManager
from Code.MountManager import MountManager
from Code.RenderPassManager import RenderPassManager
from Code.AmbientOcclusionManager import AmbientOcclusionManager
from Code.AntialiasingManager import AntialiasingManager
from Code.TransparencyManager import TransparencyManager
from Code.DynamicObjectsManager import DynamicObjectsManager
from Code.GUI.PipelineGuiManager import PipelineGuiManager
from Code.SSLRManager import SSLRManager
from Code.CloudManager import CloudManager
from Code.MemoryMonitor import MemoryMonitor

from Code.GUI.BetterOnscreenImage import BetterOnscreenImage

from Code.RenderPasses.InitialRenderPass import InitialRenderPass
from Code.RenderPasses.DeferredScenePass import DeferredScenePass
from Code.RenderPasses.ViewSpacePass import ViewSpacePass
from Code.RenderPasses.LightingPass import LightingPass
from Code.RenderPasses.DynamicExposurePass import DynamicExposurePass
from Code.RenderPasses.FinalPostprocessPass import FinalPostprocessPass
from Code.RenderPasses.VolumetricLightingPass import VolumetricLightingPass
from Code.RenderPasses.MotionBlurPass import MotionBlurPass
from Code.RenderPasses.SceneFinishPass import SceneFinishPass
from Code.RenderPasses.BloomPass import BloomPass
from Code.RenderPasses.SkyboxMaskPass import SkyboxMaskPass
from Code.RenderPasses.DOFPass import DOFPass

from Code.GUI.BufferViewerGUI import BufferViewerGUI

from direct.gui.DirectFrame import DirectFrame

import time


class RenderingPipeline(DebugObject):

    """ This is the main rendering pipeline module. It setups the whole pipeline
    process, as well as creating the managers for the different effects/passes.
    It also handles some functions to prepare the scene, e.g. for tessellation.
    """

    def __init__(self, showbase):
        """ Creates a new pipeline """
        DebugObject.__init__(self, "RenderingPipeline")
        self.showbase = showbase
        self.settings = None
        self.ready = False
        self.mountManager = MountManager()

    def getMountManager(self):
        """ Returns the mount manager. You can use this to set the
        write directory and base path """
        return self.mountManager

    def loadSettings(self, filename):
        """ Loads the pipeline settings from an ini file """
        self.settings = PipelineSettingsManager()
        self.settings.loadFromFile(filename)

        # This has to be here, before anything is printed
        DebugObject.setOutputLevel(self.settings.pipelineOutputLevel)

    def getSettings(self):
        """ Returns the current pipeline settings """
        return self.settings

    def addLight(self, light):
        """ Attaches a new light to the pipeline, this just forwards the call to
        the light manager. """
        self.lightManager.addLight(light)

    def removeLight(self, light):
        """ Removes a light from the pipeline, this just forwards the call to
        the light manager. """
        self.lightManager.removeLight(light)

    def onSceneInitialized(self):
        """ Tells the pipeline that the scene is ready to be rendered. This starts
        shadow updates """
        self.ready = True

    def setScatteringSource(self, lightSource):
        """ Sets the light source used for the scattering, can be a point or 
        directional light """
        if self.settings.enableScattering:
            self.scattering.setSunLight(lightSource)

    def getMainPassBitmask(self):
        """ Returns the camera bit used to render the main scene """
        return BitMask32.bit(2)

    def getShadowPassBitmask(self):
        """ Returns the camera bit used to render the shadow scene """
        return BitMask32.bit(3)

    def getVoxelizePassBitmask(self):
        """ Returns the camera bit used to voxelize the scene for GI """
        return BitMask32.bit(4)

    def createMaterial(self, baseColor, roughness=0.5, specular=0.5, metallic=0.0, bumpFactor=0.0):
        """ Creates and returns a new material with the given physically based
        parameters """
        material = Material()
        material.set_diffuse(VBase4(baseColor.x, baseColor.y, baseColor.z, bumpFactor))
        material.set_ambient(VBase4(0.0))
        material.set_emission(VBase4(0.0))
        material.set_shininess(0.0)
        material.set_specular(VBase4(specular, metallic, roughness, 0.0))
        return material

    def setEffect(self, obj, effect, properties = None, sort=0):
        """ Applies the effect to an object with the given properties """
        if isinstance(obj, list) or isinstance(obj, tuple):
            for part in obj:
                self.setEffect(part, effect, properties, sort)
            return

        effect = self.effectLoader.loadEffect(effect, properties)

        if effect.getSetting("transparent"):
            if not self.settings.useTransparency:
                self.error("Cannot assign transparent material when transparency is disabled")
                return False

        if effect.getSetting("dynamic"):
            self.registerDynamicObject(obj)

        if not effect.getSetting("castShadows"):
            obj.hide(self.getShadowPassBitmask())

        if not effect.getSetting("castGI"):
            obj.hide(self.getVoxelizePassBitmask())

        if not effect.getSetting("mainPass"):
            obj.hide(self.getMainPassBitmask())

        effect.assignNode(obj, "Default", sort)

        # Create EarlyZ state
        if effect.getSetting("mainPass") and effect.hasShader("EarlyZ"):
            initialState = NodePath("EffectInitialEarlyZState"+str(effect.getEffectID()))
            initialState.setShader(effect.getShader("EarlyZ"), sort + 22)
            stateName = "NodeEffect" + str(effect.getEffectID())
            self.deferredScenePass.registerEarlyZTagState(stateName, initialState)
            obj.setTag("EarlyZShader", stateName)

        # Create shadow caster state
        if effect.getSetting("castShadows") and effect.hasShader("Shadows"):
            initialState = NodePath("EffectInitialShadowState"+str(effect.getEffectID()))
            initialState.setShader(effect.getShader("Shadows"), sort + 20)
            stateName = "NodeEffect" + str(effect.getEffectID())
            self.lightManager.shadowPass.registerTagState(stateName, initialState)
            obj.setTag("ShadowPassShader", stateName)

        # Create GI state
        if effect.getSetting("castGI") and self.settings.enableGlobalIllumination and effect.hasShader("Voxelize"):
            initialState = NodePath("EffectInitialGIState"+str(effect.getEffectID()))
            initialState.setShader(effect.getShader("Voxelize"), sort + 21)
            stateName = "NodeGIEffect" + str(effect.getEffectID())
            self.globalIllum.voxelizePass.registerTagState(stateName, initialState)
            obj.setTag("VoxelizePassShader", stateName)

    def fillTextureStages(self, nodePath):
        """ Prepares all materials of a given nodepath to have at least the 4 
        default textures in the correct order: [diffuse, normal, specular, roughness] """
        
        emptyDiffuseTex = loader.loadTexture("Data/Textures/EmptyDiffuseTexture.png")
        emptyNormalTex = loader.loadTexture("Data/Textures/EmptyNormalTexture.png")
        emptySpecularTex = loader.loadTexture("Data/Textures/EmptySpecularTexture.png")
        emptyRoughnessTex = loader.loadTexture("Data/Textures/EmptyRoughnessTexture.png")

        textureOrder = [emptyDiffuseTex, emptyNormalTex, emptySpecularTex, emptyRoughnessTex]
        textureSorts = [0, 10, 20, 30]

        # Prepare the textures
        for tex in textureOrder:
            tex.setMinfilter(SamplerState.FTLinear)
            tex.setMagfilter(SamplerState.FTLinear)
            tex.setFormat(Texture.FRgba)

        # Iterate over all geom nodes
        for np in nodePath.findAllMatches("**/+GeomNode"):

            # Check how many texture stages the nodepath already has
            stages = np.findAllTextureStages()
            numStages = len(stages)

            # Fill the texture stages up
            for i in range(numStages, 4):
                stage = TextureStage("DefaultTexStage" + str(i))
                stage.setSort(textureSorts[i])
                stage.setMode(TextureStage.CMModulate)
                stage.setColor(Vec4(0, 0, 0, 1))
                np.setTexture(stage, textureOrder[i])

    def registerDynamicObject(self, np):
        """ Registers a new dynamic object to the pipeline. Every object which moves
        or transforms its vertices (like actors) has to be registered to make sure
        the velocity buffers are correct. When the object is deleted, 
        unregisterDynamicObject should be called. """
        self.dynamicObjectsManager.registerObject(np)

    def unregisterDynamicObject(self, np):
        """ Unregisters a dynamic object which was previously registered with
        registerDynamicObject """
        self.dynamicObjectsManager.unregisterObject(np)

    def getDefaultSkybox(self, scale=60000):
        """ Loads the default skybox, scaling it by the given scale factor. Note
        that there should always be a noticeable difference between the skybox
        scale and the camera far plane, to avoid z-fighting issues. The default
        skybox also comes with a default skybox shader aswell as a default skybox
        texture. The shaders and textures can be overridden by the user if required. """
        skybox = loader.loadModel("Data/InternalModels/Skybox.bam")
        skybox.setScale(scale)

        skytex = loader.loadTexture("Data/Skybox/sky.jpg")
        skytex.setWrapU(SamplerState.WMRepeat)
        skytex.setWrapV(SamplerState.WMRepeat)
        skytex.setMinfilter(SamplerState.FTLinear)
        skytex.setMagfilter(SamplerState.FTLinear)
        skytex.setFormat(Texture.FRed)
        skybox.setShaderInput("skytex", skytex)
        self.setEffect(skybox, "Effects/Skybox/Skybox.effect", {
            "castShadows": False, 
            "normalMapping": False, 
            "castGI": False}, 100)
        skybox.setName("Skybox")
        return skybox

    def reloadShaders(self):
        """ Reloads all shaders and regenerates all intitial states. This function
        also updates the shader autoconfig """
        self.debug("Reloading shaders")
        if self.guiManager:
            self.guiManager.onRegenerateShaders()

        self.renderPassManager.writeAutoconfig()
        self.renderPassManager.setShaders()
        if self.settings.enableGlobalIllumination:
            self.globalIllum.reloadShader()

    def reloadEffects(self):
        """ Reloads all effects """
        self.effectLoader.reloadEffects()

    def getRenderPassManager(self):
        """ Returns a handle to the render pass manager attribute """
        return self.renderPassManager

    def _createTasks(self):
        """ Spanws the pipeline update tasks, this are mainly the pre-render
        and post-render tasks, whereas the pre-render task has a lower priority
        than the draw task, and the post-render task has a higher priority. """
        self.showbase.addTask(self._preRenderUpdate, "RP_BeforeRender", sort=10)
        self.showbase.addTask(self._postRenderUpdate, "RP_AfterRender", sort=100)

        # for task in self.showbase.taskMgr.getAllTasks():
            # print task, task.getSort()

    def _createLastFrameBuffers(self):
        """ Creates the buffers which store the last frame depth, as the render
        target matcher cannot handle this """

        self.lastFrameDepth = Texture("LastFrameDepth")
        self.lastFrameDepth.setup2dTexture(Globals.resolution.x, Globals.resolution.y,
            Texture.TFloat, Texture.FR32)
        BufferViewerGUI.registerTexture("LastFrameDepth", self.lastFrameDepth)
        MemoryMonitor.addTexture("LastFrameDepth", self.lastFrameDepth)
        self.renderPassManager.registerStaticVariable("lastFrameDepth", self.lastFrameDepth)

    def _createInputHandles(self):
        """ Defines various inputs to be used in the shader passes. Most inputs
        use pta-arrays, so updating them is faster than using setShaderInput all the
        time. """
        self.cameraPosition = PTAVecBase3f.emptyArray(1)
        self.currentViewMat = PTALMatrix4f.emptyArray(1)
        self.currentProjMatInv = PTALMatrix4f.emptyArray(1)
        self.lastMVP = PTALMatrix4f.emptyArray(1)
        self.currentMVP = PTALMatrix4f.emptyArray(1)
        self.frameIndex = PTAInt.emptyArray(1)
        self.frameDelta = PTAFloat.emptyArray(1)

        self.renderPassManager.registerStaticVariable("lastMVP", self.lastMVP)
        self.renderPassManager.registerStaticVariable("currentMVP", self.currentMVP)
        self.renderPassManager.registerStaticVariable("frameIndex", self.frameIndex)
        self.renderPassManager.registerStaticVariable("cameraPosition", self.cameraPosition)
        self.renderPassManager.registerStaticVariable("mainCam", self.showbase.cam)
        self.renderPassManager.registerStaticVariable("mainRender", self.showbase.render)
        self.renderPassManager.registerStaticVariable("frameDelta", self.frameDelta)
        self.renderPassManager.registerStaticVariable("currentViewMat", self.currentViewMat)
        self.renderPassManager.registerStaticVariable("currentProjMatInv", self.currentProjMatInv)
        self.renderPassManager.registerStaticVariable("zeroVec2", Vec2(0))
        self.renderPassManager.registerStaticVariable("zeroVec3", Vec3(0))
        self.renderPassManager.registerStaticVariable("zeroVec4", Vec4(0))

        self.transformMat = TransformState.makeMat(Mat4.convertMat(CSYupRight, CSZupRight))

    def _preRenderUpdate(self, task):
        """ This is the pre render task which handles updating of all the managers
        as well as calling the pipeline update task """
        if not self.ready:
            return task.cont
        self._updateInputHandles()
        self.lightManager.update()
        if self.guiManager:
            self.guiManager.update()
        if self.settings.useTransparency:
            self.transparencyManager.update()
        self.antialiasingManager.update()
        self.renderPassManager.preRenderUpdate()
        self.sslrManager.update()
        if self.settings.enableClouds:
            self.cloudManager.update()
        if self.globalIllum:
            self.globalIllum.update()
        if self.scattering:
            self.scattering.update()
        self.dynamicObjectsManager.update()
        self._checkForStateClear()
        return task.cont

    def _checkForStateClear(self):
        """ This method regulary clears the state cache """
        if not hasattr(self, "lastStateClear"):
            self.lastStateClear = 0
        if Globals.clock.getFrameTime() - self.lastStateClear > self.settings.stateCacheClearInterval:
            RenderState.clearCache()
            TransformState.clearCache()
            self.lastStateClear = Globals.clock.getFrameTime()

    def _updateInputHandles(self):
        """ Updates the input-handles on a per frame basis defined in 
        _createInputHandles """
        # Compute camera bounds
        cameraBounds = self.showbase.camNode.getLens().makeBounds()
        cameraBounds.xform(self.showbase.camera.getMat(self.showbase.render))
        self.lightManager.setCullBounds(cameraBounds)

        self.lastMVP[0] = UnalignedLMatrix4f(self.currentMVP[0])
        self.currentMVP[0] = self._computeMVP()
        self.currentViewMat[0] = UnalignedLMatrix4f(self.transformMat.invertCompose(self.showbase.render.getTransform(self.showbase.cam)).getMat())
        self.currentProjMatInv[0] = UnalignedLMatrix4f(self.showbase.camLens.getProjectionMatInv())
        self.frameDelta[0] = Globals.clock.getDt()
        self.cameraPosition[0] = self.showbase.cam.getPos(self.showbase.render)
        self.frameIndex[0] = self.frameIndex[0] + 1

    def _computeMVP(self, flattenProjection = False):
        """ Computes the current scene mvp. Actually, this is the
        worldViewProjectionMatrix, but for convience it's called mvp. 
        When flattenProjection is True, the film offset will be removed from the
        matrix. """
        camLens = self.showbase.camLens
        projMat = Mat4(camLens.getProjectionMat())

        if flattenProjection:
            projMat.setCell(1, 0, 0.0)
            projMat.setCell(1, 1, 0.0)

        modelViewMat = self.showbase.render.getTransform(self.showbase.cam).getMat()
        return UnalignedLMatrix4f(modelViewMat * projMat)

    def _postRenderUpdate(self, task):
        """ This is the post render update, being called after the draw task. """
        if not self.ready:
            return task.cont
        return task.cont

    def _createViewSpacePass(self):
        """ Creates a pass which computes the view space normals and position.
        This pass is only created if any render pass requires the provided
        inputs """
        if self.renderPassManager.anyPassRequires("ViewSpacePass.normals") or \
            self.renderPassManager.anyPassRequires("ViewSpacePass.position"):
            self.viewSpacePass = ViewSpacePass()
            self.renderPassManager.registerPass(self.viewSpacePass)

    def _createSkyboxMaskPass(self):
        """ Creates a pass which computes the skybox mask.
        This pass is only created if any render pass requires the provided
        inputs """

        if self.renderPassManager.anyPassRequires("SkyboxMaskPass.resultTex"):
            self.skyboxMaskPass = SkyboxMaskPass()
            self.renderPassManager.registerPass(self.skyboxMaskPass)

    def _createDefaultTextureInputs(self):
        """ This method loads various textures used in the different render passes
        and provides them as inputs to the render pass manager """
        for color in ["White", "Black"]:
            emptyTex = loader.loadTexture("Data/Textures/" + color + ".png")
            emptyTex.setMinfilter(SamplerState.FTLinear)
            emptyTex.setMagfilter(SamplerState.FTLinear)
            emptyTex.setWrapU(SamplerState.WMClamp)
            emptyTex.setWrapV(SamplerState.WMClamp)
            self.renderPassManager.registerStaticVariable("emptyTexture" + color, emptyTex)

        texNoise = loader.loadTexture("Data/Textures/noise4x4.png")
        texNoise.setMinfilter(SamplerState.FTNearest)
        texNoise.setMagfilter(SamplerState.FTNearest)
        self.renderPassManager.registerStaticVariable("noise4x4", texNoise)

        # Load the cubemap which is used for point light shadow rendering
        cubemapLookup = self.showbase.loader.loadCubeMap(
            "Data/Cubemaps/DirectionLookup/#.png")
        cubemapLookup.setMinfilter(SamplerState.FTNearest)
        cubemapLookup.setMagfilter(SamplerState.FTNearest)
        cubemapLookup.setFormat(Texture.FRgb8)
        self.renderPassManager.registerStaticVariable("directionToFaceLookup", 
            cubemapLookup)

        # Load the default environment cubemap
        cubemapEnv = self.showbase.loader.loadCubeMap(
            self.settings.defaultReflectionCubemap, readMipmaps=True)
        cubemapEnv.setMinfilter(SamplerState.FTLinearMipmapLinear)
        cubemapEnv.setMagfilter(SamplerState.FTLinearMipmapLinear)
        cubemapEnv.setFormat(Texture.FRgba)
        self.renderPassManager.registerStaticVariable("defaultEnvironmentCubemap", 
            cubemapEnv)
        self.renderPassManager.registerStaticVariable("defaultEnvironmentCubemapMipmaps", 
            cubemapEnv.getExpectedNumMipmapLevels())

        # Load the color LUT
        colorLUT = loader.loadTexture("Data/ColorLUT/" + self.settings.colorLookupTable)
        colorLUT.setWrapU(SamplerState.WMClamp)
        colorLUT.setWrapV(SamplerState.WMClamp)
        colorLUT.setFormat(Texture.F_rgb16)
        colorLUT.setMinfilter(SamplerState.FTLinear)
        colorLUT.setMagfilter(SamplerState.FTLinear)
        self.renderPassManager.registerStaticVariable("colorLUT", colorLUT)

        # Load the normal quantization tex
        normalQuantTex = loader.loadTexture("Data/NormalQuantization/NormalQuantizationTex.png")
        normalQuantTex.setMinfilter(Texture.FTLinearMipmapLinear)
        normalQuantTex.setMagfilter(Texture.FTLinear)
        normalQuantTex.setWrapU(Texture.WMRepeat)
        normalQuantTex.setWrapV(Texture.WMRepeat)
        normalQuantTex.setFormat(Texture.FRgba16)
        self.showbase.render.setShaderInput("normalQuantizationTex", normalQuantTex)

    def _createGenericDefines(self):
        """ Registers some of the configuration defines, mainly specified in the
        pipeline config, at the render pass manager """
        define = lambda name, val: self.renderPassManager.registerDefine(name, val)
        define("WINDOW_WIDTH", Globals.resolution.x)
        define("WINDOW_HEIGHT", Globals.resolution.y)

        if self.settings.displayOnscreenDebugger:
            define("DEBUGGER_ACTIVE", 1)

        # TODO: Move to scattering module
        if self.settings.enableScattering:
            define("USE_SCATTERING", 1)

        if self.settings.useDebugAttachments:
            define("USE_DEBUG_ATTACHMENTS", 1)

        define("GLOBAL_AMBIENT_FACTOR", self.settings.globalAmbientFactor)

        if self.settings.useColorCorrection:
            define("USE_COLOR_CORRECTION", 1)

        # Pass camera near and far plane
        define("CAMERA_NEAR", Globals.base.camLens.getNear())
        define("CAMERA_FAR", Globals.base.camLens.getFar())

        # Motion blur settings
        define("MOTION_BLUR_SAMPLES", self.settings.motionBlurSamples)
        define("MOTION_BLUR_FACTOR", self.settings.motionBlurFactor)
        define("MOTION_BLUR_DILATE_PIXELS", self.settings.motionBlurDilatePixels)

    def _createGlobalIllum(self):
        """ Creates the global illumination manager if enabled in the settings """
        if self.settings.enableGlobalIllumination:
            self.globalIllum = GlobalIllumination(self)
            self.globalIllum.setup()
        else:
            self.globalIllum = None

    def _precomputeScattering(self):
        """ Precomputes the scattering model for the default atmosphere if
        specified in the settings """
        if self.settings.enableScattering:
            earthScattering = Scattering(self)
            scale = 150
            earthScattering.setSettings({
                "atmosphereOffset": Vec3(0, 0, - (6360.0 + 0.7) * scale),
                "atmosphereScale": Vec3(scale)
            })
            earthScattering.precompute()
            earthScattering.provideInputs()
            self.scattering = earthScattering
        else:
            self.scattering = None

    def getScattering(self):
        """ Returns the scattering instance if scattering is enabled, otherwise
        throws an exception """
        if not self.settings.enableScattering:
            raise Exception("Scattering is not enabled, you can not fetch the scattering instance.")
        return self.scattering

    def recreate(self):
        """ Destroys and recreates the pipeline, preserving all lights """
        raise NotImplementedError()

    def destroy(self):
        """ Destroys the pipeline, cleaning up all buffers and textures """
        raise NotImplementedError()

    def convertToPatches(self, model):
        """ Converts a model to patches. This is required before being able
        to use it with tessellation shaders """
        self.debug("Converting model to patches ..")
        for node in model.findAllMatches("**/+GeomNode"):
            geomNode = node.node()
            numGeoms = geomNode.getNumGeoms()
            for i in range(numGeoms):
                geomNode.modifyGeom(i).makePatchesInPlace()

    def toggleGui(self):
        """ Toggles the gui, useful for creating screenshots """
        if self.guiVisible:
            # Globals.base.pixel2d.hide()
            Globals.base.render2d.hide()
            Globals.base.setFrameRateMeter(False)

        else:
            # Globals.base.pixel2d.show()
            Globals.base.render2d.show()
            Globals.base.setFrameRateMeter(True)
        self.guiVisible = not self.guiVisible

    def _createBugReport(self):
        """ Creates a bug report """

        w, h = self.showbase.win.getXSize(), self.showbase.win.getYSize()

        overlayBg = DirectFrame(parent=self.showbase.pixel2dp,
                                   frameColor=(0.05, 0.05, 0.05, 0.8),
                                   frameSize=(0, w, -h, 0))  # state=DGG.NORMAL
        overlay = BetterOnscreenImage(image="Data/GUI/BugReport.png", parent=self.showbase.pixel2dp, w=757, h=398, x=(w-757)/2, y=(h-398)/2)

        for i in range(2):
            self.showbase.graphicsEngine.renderFrame()
        reporter = BugReporter(self)
        overlay.remove()
        overlayBg.remove()

    def _setGuiShaders(self):
        """ Sets the default shaders to the gui, this is required when disabling
        the fixed function pipeline """
        shader = Shader.load(Shader.SLGLSL, "Shader/GUI/vertex.glsl", "Shader/GUI/fragment.glsl")
        for target in [self.showbase.aspect2d, self.showbase.render2d, self.showbase.pixel2d,
            self.showbase.aspect2dp, self.showbase.render2dp, self.showbase.pixel2dp]:
            # target.setShader(shader, 50)
            pass

    def create(self):
        """ Creates the pipeline """

        self.debug("Setting up render pipeline")

        self.guiVisible = True

        # Handy shortcuts
        self.showbase.accept("1", PStatClient.connect)
        self.showbase.accept("r", self.reloadShaders)
        self.showbase.accept("t", self.reloadEffects)
        self.showbase.accept("f7", self._createBugReport)
        self.showbase.accept("f8", self.toggleGui)

        if self.settings is None:
            self.error("You have to call loadSettings first!")
            return

        self.debug("Checking required Panda3D version ..")
        # SystemAnalyzer.checkPandaVersionOutOfDate(12,8,2015)
        # SystemAnalyzer.analyze()

        # Mount everything first
        self.mountManager.mount()

        # Check if there is already another instance running, but only if specified
        # in the settings
        if self.settings.preventMultipleInstances and not self.mountManager.getLock():
            self.fatal("Another instance of the rendering pipeline is already running")
            return

        # Store globals, as cython can't handle them
        self.debug("Setting up globals")
        Globals.load(self.showbase)
            
        Globals.resolution = LVecBase2i( \
            int(self.showbase.win.getXSize() * self.settings.resolution3D),
            int(self.showbase.win.getYSize() * self.settings.resolution3D))

        Globals.font = loader.loadFont("Data/Font/SourceSansPro-Semibold.otf")
        Globals.font.setPixelsPerUnit(25)

        # Check size
        if Globals.resolution.x % 2 == 1:
            self.fatal(
                "The window width has to be a multiple of 2 "
                "(Current: ", Globals.resolution.x, ")")
            return

        if self.settings.displayOnscreenDebugger:
            self.guiManager = PipelineGuiManager(self)
        else:
            self.guiManager = None

        # Some basic scene settings
        self.showbase.camLens.setNearFar(0.1, 70000)
        self.showbase.camLens.setFov(110)
        self.showbase.win.setClearColor(Vec4(1.0, 0.0, 1.0, 1.0))
        self.showbase.camNode.setCameraMask(self.getMainPassBitmask())
        self.showbase.render.setAttrib(TransparencyAttrib.make(TransparencyAttrib.MNone), 100)

        # Create render pass matcher
        self.renderPassManager = RenderPassManager()

        # Create last frame buffers
        self._createLastFrameBuffers()

        self._precomputeScattering()

        # Add initial pass
        self.initialRenderPass = InitialRenderPass()
        self.renderPassManager.registerPass(self.initialRenderPass)

        # Add deferred pass
        self.deferredScenePass = DeferredScenePass(self)
        self.renderPassManager.registerPass(self.deferredScenePass)

        # Add lighting pass
        self.lightingPass = LightingPass()
        self.renderPassManager.registerPass(self.lightingPass)

        # Add dynamic exposure pass
        if self.settings.useAdaptiveBrightness:
            self.dynamicExposurePass = DynamicExposurePass(self)
            self.renderPassManager.registerPass(self.dynamicExposurePass)

        # Add motion blur pass
        if self.settings.enableMotionBlur:
            self.motionBlurPass = MotionBlurPass()
            self.renderPassManager.registerPass(self.motionBlurPass)

        # Add volumetric lighting
        # self.volumetricLightingPass = VolumetricLightingPass()
        # self.renderPassManager.registerPass(self.volumetricLightingPass)

        # Add bloom pass
        if self.settings.enableBloom:
            self.bloomPass = BloomPass()
            self.renderPassManager.registerPass(self.bloomPass)

        # Add dof pass
        if self.settings.enableDOF:
            self.dofPass = DOFPass()
            self.renderPassManager.registerPass(self.dofPass)

        # Add final pass
        self.finalPostprocessPass = FinalPostprocessPass()
        self.renderPassManager.registerPass(self.finalPostprocessPass)

        # Add scene finish pass
        self.sceneFinishPass = SceneFinishPass(self)
        self.renderPassManager.registerPass(self.sceneFinishPass)

        # Create managers
        self.occlusionManager = AmbientOcclusionManager(self)
        self.lightManager = LightManager(self)
        self.antialiasingManager = AntialiasingManager(self)
        self.dynamicObjectsManager = DynamicObjectsManager(self)
        self.sslrManager = SSLRManager(self)
        
        if self.settings.useTransparency:
            self.transparencyManager = TransparencyManager(self)

        if self.settings.enableClouds:
            self.cloudManager = CloudManager(self)

        self._createGlobalIllum()

        # Make variables available
        self._createGenericDefines()
        self._createInputHandles()
        self._createDefaultTextureInputs()
        self._createViewSpacePass()
        self._createSkyboxMaskPass()

        # Create an empty node at render space to store all dummmy cameras on
        camDummyNode = render.attachNewNode("RPCameraDummys")
        camDummyNode.hide()

        # Create an empty node at render space to store the light debug nodes
        lightDebugNode = render.attachNewNode("RPLightDebugNodes")

        # Finally matchup all the render passes and set the shaders
        self.renderPassManager.createPasses()
        self.renderPassManager.writeAutoconfig()
        self.renderPassManager.setShaders()

        # Create the update tasks
        self._createTasks()

        # Create the effect loader
        self.effectLoader = EffectLoader(self)

        # Apply the default effect to the scene
        self.setEffect(Globals.render, "Effects/Default/Default.effect", {
            "transparent": False,
            "normalMapping": True,
            "alphaTest": True,

            }, -10)

        render.setAttrib(AlphaTestAttrib.make(AlphaTestAttrib.MNone, 1), 999999)

        # Apply the debug effect to the light debug nodes
        self.setEffect(lightDebugNode, "Effects/LightDebug.effect", {
            "transparent": False,
            "normalMapping": False,
            "alphaTest": True,
            "castShadows": False,
            "castGI": False
        }, 100)

        self._setGuiShaders()

        if self.settings.enableGlobalIllumination:
            self.globalIllum.reloadShader()

        # Give the gui a hint when the pipeline is done loading
        if self.guiManager:
            self.guiManager.onPipelineLoaded()
