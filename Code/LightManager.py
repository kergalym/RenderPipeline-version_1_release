
import math
import struct

from panda3d.core import Texture, Camera, Vec3, Vec2, NodePath, RenderState
from panda3d.core import Shader, GeomEnums, MatrixLens
from panda3d.core import CullFaceAttrib, ColorWriteAttrib, DepthWriteAttrib
from panda3d.core import OmniBoundingVolume, PTAInt, Vec4, PTAVecBase4f
from panda3d.core import LVecBase2i, ShaderAttrib, UnalignedLVecBase4f
from panda3d.core import ComputeNode, LVecBase4i, GraphicsOutput, SamplerState
from panda3d.core import PStatCollector
from panda3d.core import Shader, Filename

from Code.Light import Light
from Code.LightType import LightType
from Code.DebugObject import DebugObject
from Code.RenderTarget import RenderTarget
from Code.ShadowSource import ShadowSource
from Code.ShadowAtlas import ShadowAtlas
from Code.ShaderStructArray import ShaderStructArray
from Code.Globals import Globals
from Code.MemoryMonitor import MemoryMonitor
from Code.LightLimits import LightLimits
from Code.IESLoader import IESLoader

from Code.RenderPasses.ShadowScenePass import ShadowScenePass
from Code.RenderPasses.LightCullingPass import LightCullingPass
from Code.RenderPasses.ScatteringPass import ScatteringPass
from Code.RenderPasses.ScatteringCubemapPass import ScatteringCubemapPass
from Code.RenderPasses.UnshadowedLightsPass import UnshadowedLightsPass
from Code.RenderPasses.ShadowedLightsPass import ShadowedLightsPass
from Code.RenderPasses.ExposurePass import ExposurePass
from Code.RenderPasses.ApplyLightsPass import ApplyLightsPass

from Code.GUI.FastText import FastText

pstats_ProcessLights = PStatCollector("App:LightManager:ProcessLights")
pstats_CullLights = PStatCollector("App:LightManager:CullLights")
pstats_PerLightUpdates = PStatCollector("App:LightManager:PerLightUpdates")
pstats_FetchShadowUpdates = PStatCollector(
    "App:LightManager:FetchShadowUpdates")
pstats_WriteBuffers = PStatCollector("App:LightManager:WriteBuffers")
pstats_QueueShadowUpdate = PStatCollector("App:LightManager:QueueShadowUpdate")
pstats_AppendRenderedLight = PStatCollector("App:LightManager:AppendRenderedLight")


class LightManager(DebugObject):

    """ This class is internally used by the RenderingPipeline to handle
    Lights and their Shadows. It stores a list of lights, and updates the
    required ShadowSources per frame. There are two main update methods:

    updateLights processes each light and does a basic frustum check.
    If the light is in the frustum, its ID is passed to the light precompute
    container (set with setLightingCuller). Also, each shadowSource of
    the light is checked, and if it reports to be invalid, it's queued to
    the list of queued shadow updates.

    updateShadows processes the queued shadow updates and setups everything
    to render the shadow depth textures to the shadow atlas.

    Lights can be added with addLight. Notice you cannot change the shadow
    resolution or wether the light casts shadows after you called addLight.
    This is because it might already have a position in the atlas, and so
    the atlas would have to delete it's map, which is not supported (yet).
    This shouldn't be an issue, as you usually always know before if a
    light will cast shadows or not.

    """

    def __init__(self, pipeline):
        """ Creates a new LightManager. It expects a RenderPipeline as parameter. """
        DebugObject.__init__(self, "LightManager")

        self.lightSlots = [None] * LightLimits.maxTotalLights
        self.shadowSourceSlots = [None] * LightLimits.maxShadowMaps

        self.queuedShadowUpdates = []
        self.renderedLights = {}

        self.pipeline = pipeline

        # Create arrays to store lights & shadow sources
        self.allLightsArray = ShaderStructArray(Light, LightLimits.maxTotalLights)
        self.updateCallbacks = []

        self.cullBounds = None
        self.numTiles = None
        self.lightingComputator = None
        self.shadowScene = Globals.render

        # Create atlas
        self.shadowAtlas = ShadowAtlas()
        self.shadowAtlas.setSize(self.pipeline.settings.shadowAtlasSize)
        self.shadowAtlas.create()

        self.maxShadowUpdatesPerFrame = self.pipeline.settings.maxShadowUpdatesPerFrame
        self.numShadowUpdatesPTA = PTAInt.emptyArray(1)

        self.updateShadowsArray = ShaderStructArray(
            ShadowSource, self.maxShadowUpdatesPerFrame)
        self.allShadowsArray = ShaderStructArray(
            ShadowSource, LightLimits.maxShadowMaps)

        self._initLightCulling()


        # Create shadow compute buffer
        self._createShadowPass()
        self._createUnshadowedLightsPass()
        self._createShadowedLightsPass()
        self._createApplyLightsPass()
        self._createExposurePass()

        if self.pipeline.settings.enableScattering:
            self._createScatteringPass()

        # Create the initial shadow state
        self.shadowScene.setTag("ShadowPassShader", "Default")

        # Register variables & arrays
        self.pipeline.getRenderPassManager().registerDynamicVariable("shadowUpdateSources", 
            self._bindUpdateSources)
        self.pipeline.getRenderPassManager().registerDynamicVariable("allLights", 
            self._bindAllLights)
        self.pipeline.getRenderPassManager().registerDynamicVariable("allShadowSources", 
            self._bindAllSources)

        self.pipeline.getRenderPassManager().registerStaticVariable("numShadowUpdates", 
            self.numShadowUpdatesPTA)

        self._loadIESProfiles()
        self._addShaderDefines()
        self._createDebugTexts()

    def _bindUpdateSources(self, renderPass, name):
        """ Internal method to bind the shadow update source to a target """
        self.updateShadowsArray.bindTo(renderPass, name)

    def _bindAllLights(self, renderPass, name):
        """ Internal method to bind the global lights array to a target """
        self.allLightsArray.bindTo(renderPass, name)

    def _bindAllSources(self, renderPass, name):
        """ Internal method to bind the global shadow sources to a target """
        self.allShadowsArray.bindTo(renderPass, name)

    def _createShadowPass(self):
        """ Creates the shadow pass, where the shadow atlas is generated into """
        self.shadowPass = ShadowScenePass()
        self.shadowPass.setMaxRegions(self.maxShadowUpdatesPerFrame)
        self.shadowPass.setSize(self.shadowAtlas.getSize())
        self.pipeline.getRenderPassManager().registerPass(self.shadowPass)

    def _createUnshadowedLightsPass(self):
        """ Creates the pass which renders all unshadowed lights """
        self.unshadowedLightsPass = UnshadowedLightsPass()
        self.pipeline.getRenderPassManager().registerPass(self.unshadowedLightsPass)

    def _createApplyLightsPass(self):
        """ Creates the pass which applies all lights """
        self.applyLightsPass = ApplyLightsPass(self.pipeline)
        self.applyLightsPass.setTileCount(self.numTiles)
        self.pipeline.getRenderPassManager().registerPass(self.applyLightsPass)


    def _createShadowedLightsPass(self):
        """ Creates the pass which renders all unshadowed lights """
        self.shadowedLightsPass = ShadowedLightsPass()
        self.pipeline.getRenderPassManager().registerPass(self.shadowedLightsPass)

    def _createExposurePass(self):
        """ Creates the pass which applies the exposure and color correction """
        self.exposurePass = ExposurePass()
        self.pipeline.getRenderPassManager().registerPass(self.exposurePass)

    def _createScatteringPass(self):
        """ Creates the scattering pass """
        self.scatteringPass = ScatteringPass()
        self.pipeline.getRenderPassManager().registerPass(self.scatteringPass)

        self.scatteringCubemapPass = ScatteringCubemapPass(self.pipeline)
        self.pipeline.getRenderPassManager().registerPass(self.scatteringCubemapPass)

    def _loadIESProfiles(self):
        """ Loads the ies profiles from Data/IESProfiles. """
        self.iesLoader = IESLoader()
        self.iesLoader.loadIESProfiles("Data/IESProfiles/")

        self.pipeline.getRenderPassManager().registerStaticVariable("IESProfilesTex",
            self.iesLoader.getIESProfileStorageTex())

    def _initLightCulling(self):
        """ Creates the pass which gets a list of lights and computes which
        light affects which tile """

        # Fetch patch size
        self.patchSize = LVecBase2i(
            self.pipeline.settings.computePatchSizeX,
            self.pipeline.settings.computePatchSizeY)

        # size has to be a multiple of the compute unit size
        # but still has to cover the whole screen
        sizeX = int(math.ceil(float(Globals.resolution.x) / self.patchSize.x))
        sizeY = int(math.ceil(float(Globals.resolution.y) / self.patchSize.y))

        self.lightCullingPass = LightCullingPass(self.pipeline)
        self.lightCullingPass.setSize(sizeX, sizeY)
        self.lightCullingPass.setPatchSize(self.patchSize.x, self.patchSize.y)

        self.pipeline.getRenderPassManager().registerPass(self.lightCullingPass)
        self.pipeline.getRenderPassManager().registerStaticVariable("lightingTileCount", LVecBase2i(sizeX, sizeY))

        self.debug("Batch size =", sizeX, "x", sizeY,
                   "Actual Buffer size=", int(sizeX * self.patchSize.x),
                   "x", int(sizeY * self.patchSize.y))

        self.numTiles = LVecBase2i(sizeX, sizeY)

        # Create the buffer which stores the rendered lights
        self._makeRenderedLightsBuffer()

    def _makeRenderedLightsBuffer(self):
        """ Creates the buffer which stores the indices of all rendered lights """

        bufferSize = 16
        bufferSize += LightLimits.maxLights["PointLight"]
        bufferSize += LightLimits.maxLights["PointLightShadow"]
        bufferSize += LightLimits.maxLights["DirectionalLight"]
        bufferSize += LightLimits.maxLights["DirectionalLightShadow"]
        bufferSize += LightLimits.maxLights["SpotLight"]
        bufferSize += LightLimits.maxLights["SpotLightShadow"]

        self.renderedLightsBuffer = Texture("RenderedLightsBuffer")
        self.renderedLightsBuffer.setupBufferTexture(bufferSize, Texture.TInt, Texture.FR32i, GeomEnums.UHDynamic)

        self.pipeline.getRenderPassManager().registerStaticVariable(
            "renderedLightsBuffer", self.renderedLightsBuffer)

        MemoryMonitor.addTexture("Rendered Lights Buffer", self.renderedLightsBuffer)

    def _addShaderDefines(self):
        """ Adds settings like the maximum light count to the list of defines
        which are available in the shader later """
        define = lambda name, val: self.pipeline.getRenderPassManager().registerDefine(name, val)
        settings = self.pipeline.settings


        define("MAX_VISIBLE_LIGHTS", LightLimits.maxTotalLights)

        define("MAX_POINT_LIGHTS", LightLimits.maxLights["PointLight"])
        define("MAX_SHADOWED_POINT_LIGHTS", LightLimits.maxLights["PointLightShadow"])

        define("MAX_DIRECTIONAL_LIGHTS", LightLimits.maxLights["DirectionalLight"])
        define("MAX_SHADOWED_DIRECTIONAL_LIGHTS", LightLimits.maxLights["DirectionalLightShadow"])

        define("MAX_SPOT_LIGHTS", LightLimits.maxLights["SpotLight"])
        define("MAX_SHADOWED_SPOT_LIGHTS", LightLimits.maxLights["SpotLightShadow"])

        define("MAX_TILE_POINT_LIGHTS", LightLimits.maxPerTileLights["PointLight"])
        define("MAX_TILE_SHADOWED_POINT_LIGHTS", LightLimits.maxPerTileLights["PointLightShadow"])

        define("MAX_TILE_DIRECTIONAL_LIGHTS", LightLimits.maxPerTileLights["DirectionalLight"])
        define("MAX_TILE_SHADOWED_DIRECTIONAL_LIGHTS", LightLimits.maxPerTileLights["DirectionalLightShadow"])

        define("MAX_TILE_SPOT_LIGHTS", LightLimits.maxPerTileLights["SpotLight"])
        define("MAX_TILE_SHADOWED_SPOT_LIGHTS", LightLimits.maxPerTileLights["SpotLightShadow"])

        define("SHADOW_MAX_TOTAL_MAPS", LightLimits.maxShadowMaps)

        define("LIGHTING_COMPUTE_PATCH_SIZE_X", settings.computePatchSizeX)
        define("LIGHTING_COMPUTE_PATCH_SIZE_Y", settings.computePatchSizeY)

        if settings.renderShadows:
            define("USE_SHADOWS", 1)
            
        define("SHADOW_MAP_ATLAS_SIZE", settings.shadowAtlasSize)
        define("SHADOW_MAX_UPDATES_PER_FRAME", settings.maxShadowUpdatesPerFrame)
        define("SHADOW_GEOMETRY_MAX_VERTICES", settings.maxShadowUpdatesPerFrame * 3)
        define("CUBEMAP_ANTIALIASING_FACTOR", settings.cubemapAntialiasingFactor)
        define("SHADOW_NUM_PCF_SAMPLES", settings.numPCFSamples)
        define("PCSS_SAMPLE_RADIUS", settings.pcssSampleRadius)

        if settings.usePCSS:
            define("USE_PCSS", 1)

        if settings.useDiffuseAntialiasing:
            define("USE_DIFFUSE_ANTIALIASING", 1)

        define("SHADOW_NUM_PCSS_SEARCH_SAMPLES", settings.numPCSSSearchSamples)
        define("SHADOW_NUM_PCSS_FILTER_SAMPLES", settings.numPCSSFilterSamples)
        define("SHADOW_PSSM_BORDER_PERCENTAGE", settings.shadowCascadeBorderPercentage)

        if settings.useHardwarePCF:
            define("USE_HARDWARE_PCF", 1)

        if settings.enableAlphaTestedShadows:
            define("USE_ALPHA_TESTED_SHADOWS", 1)

    def processCallbacks(self):
        """ Processes all updates from the previous frame """
        for update in self.updateCallbacks:
            update.onUpdated()
        self.updateCallbacks = []

    def _createDebugTexts(self):
        """ Creates a debug overlay if specified in the pipeline settings """
        self.lightsVisibleDebugText = None
        self.lightsUpdatedDebugText = None

        if self.pipeline.settings.displayDebugStats:
            self.lightsVisibleDebugText = FastText(pos=Vec2(
                Globals.base.getAspectRatio() - 0.1, 0.84), rightAligned=True, color=Vec3(1, 1, 0), size=0.03)
            self.lightsUpdatedDebugText = FastText(pos=Vec2(
                Globals.base.getAspectRatio() - 0.1, 0.8), rightAligned=True, color=Vec3(1, 1, 0), size=0.03)

    def _queueShadowUpdate(self, sourceIndex):
        """ Internal method to add a shadowSource to the list of queued updates. Returns
        the position of the source in queue """
        if sourceIndex not in self.queuedShadowUpdates:
            self.queuedShadowUpdates.append(sourceIndex)
            return len(self.queuedShadowUpdates) - 1
        return self.queuedShadowUpdates.index(sourceIndex)

    def _allocateLightSlot(self, light):
        """ Tries to find a free light slot. Returns False if no slot is free, if 
        a slot is free it gets allocated and linked to the light """
        for index, val in enumerate(self.lightSlots):
            if val == None:
                light.setIndex(index)
                self.lightSlots[index] = light
                return True
        return False

    def _findShadowSourceSlot(self):
        """ Tries to find a free shadow source. Returns False if no slot is free """
        for index, val in enumerate(self.shadowSourceSlots):
            if val == None:
                return index
        return -1

    def addLight(self, light):
        """ Adds a light to the list of rendered lights.

        NOTICE: You have to set relevant properties like Whether the light
        casts shadows or the shadowmap resolution before calling this! 
        Otherwise it won't work (and maybe crash? I didn't test, 
        just DON'T DO IT!) """
        
        if light.attached:
            self.warn("Light is already attached!")
            return

        light.attached = True
        # self.lights.append(light)

        if not self._allocateLightSlot(light):
            self.error("Cannot allocate light slot, out of slots.")
            return False

        if light.hasShadows() and not self.pipeline.settings.renderShadows:
            self.warn("Attached shadow light but shadowing is disabled in pipeline.ini")
            light.setCastsShadows(False)

        sources = light.getShadowSources()

        # Check each shadow source
        for index, source in enumerate(sources):

            # Check for correct resolution
            tileSize = self.shadowAtlas.getTileSize()
            if source.resolution < tileSize or source.resolution % tileSize != 0:
                self.warn(
                    "The ShadowSource resolution has to be a multiple of the tile size (" + str(tileSize) + ")!")
                self.warn("Adjusting resolution to", tileSize)
                source.resolution = tileSize

            if source.resolution > self.shadowAtlas.getSize():
                self.warn(
                    "The ShadowSource resolution cannot be bigger than the atlas size (" + str(self.shadowAtlas.getSize()) + ")")
                self.warn("Adjusting resolution to", tileSize)
                source.resolution = tileSize

            # Frind slot for source
            sourceSlotIndex = self._findShadowSourceSlot()
            if sourceSlotIndex < 0:
                self.error("Cannot store more shadow sources!")
                return False

            self.shadowSourceSlots[sourceSlotIndex] = source
            source.setSourceIndex(sourceSlotIndex)
            light.setSourceIndex(index, sourceSlotIndex)

        # Store light in the shader struct array
        self.allLightsArray[light.getIndex()] = light

        light.queueUpdate()
        light.queueShadowUpdate()

    def removeLight(self, light):
        """ Removes a light from the rendered lights """

        index = light.getIndex()
        if light.hasShadows():
            sources = light.getShadowSources()

            for source in sources:
                self.shadowSourceSlots[source.getSourceIndex()] = None
                self.shadowAtlas.deallocateTiles(source.getUID())

                # remove the source from the current updates
                if source.getSourceIndex() in self.queuedShadowUpdates:
                    self.queuedShadowUpdates.remove(source.getSourceIndex())
                source.cleanup()

        light.cleanup()
        del light

        self.lightSlots[index] = None

    def setCullBounds(self, bounds):
        """ Sets the current camera bounds used for light culling """
        self.cullBounds = bounds

    def _writeRenderedLightsToBuffer(self):
        """ Stores the list of rendered lights in the buffer to access it in
        the shader later """

        pstats_WriteBuffers.start()
        image = memoryview(self.renderedLightsBuffer.modifyRamImage())

        bufferEntrySize = 4

        # Write counters
        offset = 0
        image[offset:offset + bufferEntrySize * 6] = struct.pack('i' * 6, 
            len(self.renderedLights["PointLight"]),
            len(self.renderedLights["PointLightShadow"]),
            len(self.renderedLights["DirectionalLight"]),
            len(self.renderedLights["DirectionalLightShadow"]),
            len(self.renderedLights["SpotLight"]),
            len(self.renderedLights["SpotLightShadow"]))

        offset = 16 * bufferEntrySize

        # Write light lists
        for lightType in ["PointLight", "PointLightShadow", "DirectionalLight", 
            "DirectionalLightShadow", "SpotLight", "SpotLightShadow"]:
        
            entryCount = len(self.renderedLights[lightType])

            if entryCount > LightLimits.maxLights[lightType]:
                self.error("Out of lights bounds for", lightType)

            if entryCount > 0:
                # We can write all lights at once, thats pretty cool!
                image[offset:offset + entryCount * bufferEntrySize] = struct.pack('i' * entryCount, *self.renderedLights[lightType])
            offset += LightLimits.maxLights[lightType] * bufferEntrySize

        pstats_WriteBuffers.stop()

    def update(self):
        """ Main update function """
        self.updateLights()
        self.updateShadows()
        self.processCallbacks()

    def updateLights(self):
        """ This is one of the two per-frame-tasks. See class description
        to see what it does """

        # Clear dictionary to store the lights rendered this frame
        self.renderedLights = {}
        # self.queuedShadowUpdates = []

        for lightType in LightLimits.maxLights:
            self.renderedLights[lightType] = []        
        pstats_ProcessLights.start()

        # Fetch gi grid bounds
        giGridBounds = None
        if self.pipeline.settings.enableGlobalIllumination:
            giGridBounds = self.pipeline.globalIllum.getBounds()

        # Process each light
        for index, light in enumerate(self.lightSlots):

            if light == None:
                continue

            # When shadow maps should be always updated
            if self.pipeline.settings.alwaysUpdateAllShadows:
                light.queueShadowUpdate()

            # Update light if required
            pstats_PerLightUpdates.start()
            if light.needsUpdate():
                light.performUpdate()
            pstats_PerLightUpdates.stop()

            # Perform culling
            pstats_CullLights.start()
            lightBounds = light.getBounds()
            if not self.cullBounds.contains(lightBounds):
                
                # In case the light is not in the camera frustum, check if the light is
                # in the gi frustum
                if giGridBounds:
                    if not giGridBounds.contains(lightBounds):
                        continue
                else:
                    continue

            pstats_CullLights.stop()

            delaySpawn = False

            # Queue shadow updates if necessary
            pstats_QueueShadowUpdate.start()
            if light.hasShadows() and light.needsShadowUpdate():
                neededUpdates = light.performShadowUpdate()
                for update in neededUpdates:
                    updatePosition = self._queueShadowUpdate(update.getSourceIndex())
                    willUpdateNextFrame = updatePosition < self.maxShadowUpdatesPerFrame

                    # If the source did not get rendered so far, and wont get rendered
                    # in the next frame, delay the rendering of this light
                    if not willUpdateNextFrame and not update.hasAtlasPos():
                        delaySpawn = True

            pstats_QueueShadowUpdate.stop()
            
            # When the light is not ready yet, wait for the next frame
            if delaySpawn:
                # self.debug("Delaying light spawn")
                continue

            # Check if the ies profile has been assigned yet
            if light.getLightType() == LightType.Spot:
                if light.getIESProfileIndex() < 0 and light.getIESProfileName() is not None:
                    name = light.getIESProfileName()
                    index = self.iesLoader.getIESProfileIndexByName(name)
                    if index < 0:
                        self.error("Unkown ies profile:",name)
                        light.setIESProfileIndex(0)
                    else:
                        light.setIESProfileIndex(index)

            # Add light to the correct list now
            pstats_AppendRenderedLight.start()
            lightTypeName = light.getTypeName()
            if light.hasShadows():
                lightTypeName += "Shadow"
            self.renderedLights[lightTypeName].append(index)
            pstats_AppendRenderedLight.stop()

        pstats_ProcessLights.stop()

        self._writeRenderedLightsToBuffer()

        # Generate debug text
        if self.lightsVisibleDebugText is not None:
            renderedPL = str(len(self.renderedLights["PointLight"]))
            renderedPL_S = str(len(self.renderedLights["PointLightShadow"]))

            renderedDL = str(len(self.renderedLights["DirectionalLight"]))
            renderedDL_S = str(len(self.renderedLights["DirectionalLightShadow"]))

            renderedSL = str(len(self.renderedLights["SpotLight"]))
            renderedSL_S = str(len(self.renderedLights["SpotLight"]))

            self.lightsVisibleDebugText.setText(
                "Point: " + renderedPL + "/" + renderedPL_S + ", Directional: " + renderedDL + "/"+  renderedDL_S + ", Spot: " + renderedSL+ "/" + renderedSL_S)

    def updateShadows(self):
        """ This is one of the two per-frame-tasks. See class description
        to see what it does """

        # Process shadows
        queuedUpdateLen = len(self.queuedShadowUpdates)

        # Compute shadow updates
        numUpdates = 0
        lastRenderedSourcesStr = "[ "

        # When there are no updates, disable the buffer
        if len(self.queuedShadowUpdates) < 1:
            self.shadowPass.setActiveRegionCount(0)
            self.numShadowUpdatesPTA[0] = 0
            
        else:

            # Check each update in the queue
            for index, updateID in enumerate(self.queuedShadowUpdates):

                # We only process a limited number of shadow maps
                if numUpdates >= self.maxShadowUpdatesPerFrame:
                    break

                update = self.shadowSourceSlots[updateID]
                updateSize = update.getResolution()

                # assign position in atlas if not done yet
                if not update.hasAtlasPos():
                    storePos = self.shadowAtlas.reserveTiles(
                        updateSize, updateSize, update.getUID())

                    if not storePos:
                        # No space found, try to reduce resolution
                        self.warn(
                            "Could not find space for the shadow map of size", updateSize)
                        self.warn(
                            "The size will be reduced to", self.shadowAtlas.getTileSize())

                        updateSize = self.shadowAtlas.getTileSize()
                        update.setResolution(updateSize)
                        storePos = self.shadowAtlas.reserveTiles(
                            updateSize, updateSize, update.getUID())

                        if not storePos:
                            self.fatal(
                                "Still could not find a shadow atlas position, "
                                "the shadow atlas is completely full. "
                                "Either we reduce the resolution of existing shadow maps, "
                                "increase the shadow atlas resolution, "
                                "or crash the app. Guess what I decided to do :-P")

                    update.assignAtlasPos(*storePos)

                update.update()

                # Store update in array
                self.allShadowsArray[updateID] = update
                self.updateShadowsArray[index] = update
                
                # Compute viewport & set depth clearer
                texScale = float(update.getResolution()) / float(self.shadowAtlas.getSize())

                atlasPos = update.getAtlasPos()
                left, right = atlasPos.x, (atlasPos.x + texScale)
                bottom, top = atlasPos.y, (atlasPos.y + texScale)

                self.shadowPass.setRegionDimensions(numUpdates, left, right, bottom, top)
                regionCam = self.shadowPass.getRegionCamera(numUpdates)
                regionCam.setPos(update.cameraNode.getPos())
                regionCam.setHpr(update.cameraNode.getHpr())
                regionCam.node().setLens(update.getLens())

                numUpdates += 1

                # Finally, we can tell the update it's valid now.
                update.setValid()

                # In the next frame the update is processed, so call it later
                self.updateCallbacks.append(update)

                # Only add the uid to the output if the max updates
                # aren't too much. Otherwise we spam the screen
                if self.maxShadowUpdatesPerFrame <= 8:
                    lastRenderedSourcesStr += str(update.getUID()) + " "

            # Remove all updates which got processed from the list
            self.queuedShadowUpdates = self.queuedShadowUpdates[numUpdates:]
            self.numShadowUpdatesPTA[0] = numUpdates

            self.shadowPass.setActiveRegionCount(numUpdates)

        lastRenderedSourcesStr += "]"

        # Generate debug text
        if self.lightsUpdatedDebugText is not None:
            self.lightsUpdatedDebugText.setText(
                'Updates: ' + str(numUpdates) + "/" + str(queuedUpdateLen) + ", Last: " + lastRenderedSourcesStr + ", Free Tiles: " + str(self.shadowAtlas.getFreeTileCount()) + "/" + str(self.shadowAtlas.getTotalTileCount()))
