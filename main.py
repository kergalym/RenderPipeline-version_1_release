"""


RenderPipeline testing file

If you are looking for Code Examples, look at Samples/. This file is for
testing purposes only, and also not very clean coded!



"""


# Don't generate .pyc files
import sys
import os
sys.dont_write_bytecode = True


import math
import struct
from random import random, seed, randint
import copy

from direct.showbase.ShowBase import ShowBase
from panda3d.core import loadPrcFile, Vec3, SamplerState, ClockObject
from panda3d.core import Texture, TextureStage, RenderModeAttrib, RenderState
from panda3d.core import Shader, CullFaceAttrib, TransparencyAttrib

from Code.MovementController import MovementController
from Code.RenderingPipeline import RenderingPipeline
from Code.PointLight import PointLight
from Code.DirectionalLight import DirectionalLight
from Code.DebugObject import DebugObject
from Code.FirstPersonController import FirstPersonCamera
from Code.GlobalIllumination import GlobalIllumination
from Code.SpotLight import SpotLight
from Code.GUI.PipelineLoadingScreen import PipelineLoadingScreen

from Code.Water.ProjectedWaterGrid import ProjectedWaterGrid

from direct.interval.IntervalGlobal import Sequence


class Main(ShowBase, DebugObject):

    """ This is the render pipeline testing showbase """

    def __init__(self):
        DebugObject.__init__(self, "Main")

        self.debug("Bit System =", 8 * struct.calcsize("P"))

        # Load engine configuration
        self.debug("Loading panda3d configuration from configuration.prc ..")
        loadPrcFile("Config/configuration.prc")

        # Init the showbase
        ShowBase.__init__(self)

        # Show loading screen
        self.loadingScreen = PipelineLoadingScreen(self)
        self.loadingScreen.render()
        self.loadingScreen.setStatus("Creating pipeline", 10)

        # Create the render pipeline
        self.debug("Creating pipeline")
        self.renderPipeline = RenderingPipeline(self)

        # Uncomment to use temp directory
        # writeDirectory = tempfile.mkdtemp(prefix='Shader-tmp')
        writeDirectory = "Temp/"

        # Set the pipeline base path
        self.renderPipeline.getMountManager().setBasePath(".")
        
        # Load pipeline settings
        self.renderPipeline.loadSettings("Config/pipeline.ini")

        self.loadingScreen.setStatus("Compiling shaders", 20)

        # Create the pipeline, and enable scattering
        self.renderPipeline.create()

        ####### END OF RENDER PIPELINE SETUP #######

        # Select demo scene here:

        # This sources are not included in the repo, for size reasons
        # self.sceneSource = "Demoscene.ignore/MasterSword/Scene.egg"
        # self.sceneSource = "Demoscene.ignore/MasterSword/Scene2.egg.bam"
        # self.sceneSource = "Demoscene.ignore/Couch2/Scene.egg"
        # self.sceneSource = "Demoscene.ignore/Couch/couch.egg.bam"
        # self.sceneSource = "Demoscene.ignore/LittleHouse/Scene.bam"
        # self.sceneSource = "Demoscene.ignore/LivingRoom/LivingRoom.egg"
        # self.sceneSource = "Demoscene.ignore/LivingRoom2/LivingRoom.egg"
        # self.sceneSource = "Demoscene.ignore/LostEmpire/Model.egg"
        # self.sceneSource = "Demoscene.ignore/SSLRTest/scene.egg"
        # self.sceneSource = "Demoscene.ignore/BMW/Bmw.egg"
        # self.sceneSource = "Demoscene.ignore/Tuscany/Tuscany.egg"
        # self.sceneSource = "Demoscene.ignore/EiffelTower/Scene.bam"
        # self.sceneSource = "Demoscene.ignore/HarvesterModel/Model.egg"
        # self.sceneSource = "Demoscene.ignore/AudiR8/Scene.bam"
        # self.sceneSource = "Demoscene.ignore/OldHouse/Scene.egg"
        # self.sceneSource = "Samples/02-Roaming-Ralph/models/world"
        # self.sceneSource = "Demoscene.ignore/TransparencyTest/Scene.egg"
        # self.sceneSource = "Demoscene.ignore/SanMiguel/Scene.bam"
        # self.sceneSource = "Demoscene.ignore/lvl_one_rp.egg.bam"
        self.sceneSource = "Demoscene.ignore/DabrovicSponza/Scene.egg"
        # self.sceneSource = "Demoscene.ignore/Avolition/level5.bam"
        # self.sceneSource = "Demoscene.ignore/lamborgini-countach.egg"
        # self.sceneSource = "Demoscene.ignore/Alphatest/Scene.bam"
        # self.sceneSource = "Demoscene.ignore/TestScene/Test.bam"
        # self.sceneSource = "Demoscene.ignore/BokehTest/Scene.egg"

        # This sources are included in the repo
        # self.sceneSource = "Models/CornelBox/Model.egg"
        # self.sceneSource = "Models/HouseSet/Model.egg"
        # self.sceneSource = "Models/PSSMTest/Model.egg.bam"
        # self.sceneSource = "Models/PBSTest/Scene.egg.bam"
        # self.sceneSource = "Models/HDRTest/Scene.egg"
        # self.sceneSource = "Models/GITestScene/Scene.egg"
        # self.sceneSource = "Toolkit/Blender Material Library/MaterialLibrary.bam"
        # self.sceneSource = "panda"

        # Select surrounding scene here
        self.sceneSourceSurround = None
        # self.sceneSourceSurround = "Demoscene.ignore/Couch/Surrounding.egg"
        # self.sceneSourceSurround = "Demoscene.ignore/LivingRoom/LivingRoom.egg"

        # Wheter to create the default ground plane
        self.usePlane = False

        # Store a list of transparent objects
        self.transparentObjects = []

        # Create a sun light
        dPos = Vec3(60, 30, 100)

        if True:
            dirLight = DirectionalLight()
            dirLight.setPos(dPos * 100000.0)
            dirLight.setShadowMapResolution(2048)
            dirLight.setColor(Vec3(1.0, 1.0, 1.0) * 5.0)
            dirLight.setCastsShadows(True)
            dirLight.setPssmDistance(140)
            self.renderPipeline.addLight(dirLight)
            self.dirLight = dirLight

            # Tell the GI which light casts the GI
            self.renderPipeline.setScatteringSource(dirLight)

        # Slider to move the sun
        if self.renderPipeline.settings.displayOnscreenDebugger:
            self.renderPipeline.guiManager.demoSlider.node[
                "command"] = self.setSunPos
            self.renderPipeline.guiManager.demoSlider.node[
                "value"] = 89

            self.lastSliderValue = 0.5

        self.movingLights = []

        self.demoLights = []

        # Create some lights
        for i in range(5):
            continue
            pointLight = PointLight()

            radius = float(i) / 3.0 * 6.28 + 1.52
            xoffs = (i-3) * 10.0
            yoffs = math.cos(radius) * 0.0
            pointLight.setPos(xoffs, 0, 8)
            # pointLight.setColor(Vec3(0.2,0.6,1.0)*6)
            pointLight.setColor(Vec3(random(), random(), random())*3)
            pointLight.setShadowMapResolution(512)
            pointLight.setRadius(18)
            pointLight.setCastsShadows(True)
            self.renderPipeline.addLight(pointLight)
            pointLight.attachDebugNode()
            # self.movingLights.append(pointLight)

        # Create more lights
        for i in range(0):
            pointLight = PointLight()
            radius = float(i) / 12.0 * 6.28 + 5.22
            xoffs = math.sin(radius) * 50.0
            yoffs = math.cos(radius) * 50.0
            pointLight.setPos(Vec3( xoffs, yoffs, 12))
            # pointLight.setColor(Vec3(0.2,0.6,1.0) * 0.05)
            pointLight.setColor(random(), random(), random())
            pointLight.setRadius(90)
            self.renderPipeline.addLight(pointLight)
            # pointLight.attachDebugNode(render)

        for x in range(0):
            spotLight = SpotLight()
            spotLight.setColor(Vec3(0.5, 0.8, 1.0) * 0.3)

            lightPos = Vec3(math.sin(x/10.0 * 6.28) * 16.0, math.cos(x/10.0 * 6.28) * 16.0, 29.0)

            spotLight.setPos(lightPos)
            spotLight.lookAt(lightPos - Vec3(0, 0, 1))
            spotLight.setFov(90)
            spotLight.setShadowMapResolution(1024)
            spotLight.setCastsShadows(True)
            spotLight.setNearFar(2.0, 60.0)
            spotLight.setIESProfile("AreaLight")
            self.renderPipeline.addLight(spotLight)
            # spotLight.attachDebugNode(render)
            # self.movingLights.append(spotLight)

        # Attach update task
        self.addTask(self.update, "update")

        # Update loading screen status
        self.loadingScreen.setStatus("Loading scene", 55)


        # Show loading screen a bit
        if False:
            self.doMethodLater(0.5, self.loadScene, "Load Scene")
        else:
            self.loadScene()


    def addDemoLight(self):
        """ Spawns a new light at a random position with a random color """
        light = PointLight()
        spot = self.cam.getPos(self.render)
        light.setPos(spot)
        light.setRadius(45)
        light.setColor(Vec3(1.3,1.05,0.9) * 2.0)
        light.setShadowMapResolution(512)
        light.setCastsShadows(True)
        self.renderPipeline.addLight(light)
        self.demoLights.append(light)

    def removeDemoLight(self):
        """ Removes the last added demo light if present """
        if len(self.demoLights) > 0:
            self.renderPipeline.removeLight(self.demoLights[-1])
            del self.demoLights[-1]

    def update(self, task):
        """ Main update task """

        for idx, light in enumerate(self.movingLights):
            light.setZ(math.sin(idx +globalClock.getFrameTime())*2.0 + 10)
            # light.setZ(5)

        # import time
        # time.sleep(0.2)
        # globalClock.setMode(ClockObject.MLimited)
        # globalClock.setFrameRate(10)

        # Uncomment for party mode :-)
        # self.removeDemoLight()
        # self.addDemoLight()

        return task.cont

    def loadScene(self, task=None):
        """ Starts loading the scene, this is done async """
        # Load scene from disk

        if not os.path.isfile(self.sceneSource) and self.sceneSource not in ["panda", "environment"]:
            self.error("The scene source could not be found!")
            dlLink = None

            if "DabrovicSponza" in self.sceneSource:
                dlLink = "http://rdb.name/renderpipeline/DabrovicSponza.7z"

            if dlLink is not None:
                self.error("You can download it from here: " + dlLink)
                self.error("After downloading, extract it to '" + self.sceneSource + "'")

            sys.exit(0)

        self.debug("Loading Scene '" + self.sceneSource + "'")
        self.loader.loadModel(self.sceneSource, callback = self.onSceneLoaded)


    def onSceneLoaded(self, scene):
        """ Callback which gets called after the scene got loaded """

        self.debug("Successfully loaded scene")

        self.loadingScreen.setStatus("Loading skybox", 70)

        self.scene = scene
        self.scene.prepareScene(self.win.getGsg())
        # render.hide(self.renderPipeline.getVoxelizePassBitmask())
        # self.scene.hide(self.renderPipeline.getVoxelizePassBitmask())

        # Load surround scene
        if self.sceneSourceSurround is not None:
            self.debug("Loading Surround-Scene '" + self.sceneSourceSurround + "'")
            self.sceneSurround = self.loader.loadModel(self.sceneSourceSurround)
            self.sceneSurround.reparentTo(self.scene)
            # self.sceneSurround.setScale(0.7)
            # self.sceneSurround.setH(180)
            # self.sceneSurround.setPos(0, -4.7, 0.73)

        seed(1)

        # Performance testing
        if False:
            highPolyObj = self.scene.find("**/HighPolyObj")

            if highPolyObj is not None and not highPolyObj.isEmpty():
                # highPolyObj.detachNode()
                self.loadingScreen.setStatus("Preparing Performance Test", 75)

                for x in range(0, 20):
                    for y in range(0, 1):
                    # if True:
                        # y = 5
                        copiedObj = copy.deepcopy(highPolyObj)
                        copiedObj.setColorScale(random(), random(), random(), 1)
                        # if random() < 0.2:
                            # copiedObj.setColorScale(0.4, 1.2, 2.0, 1.0)

                        copiedObj.reparentTo(self.scene)
                        copiedObj.setPos(x*1.5 + random(), y*1.5 + random(), random()*5.0 + 0.4)

        # Find transparent objects and mark them as transparent
        if self.renderPipeline.settings.useTransparency:
            self.transpObjRoot = render.attachNewNode("transparentObjects")
            matches = self.scene.findAllMatches("**/T__*")
            if matches:
                for match in matches:
                    # match.hide()
                    # continue
                    self.transparentObjects.append(match)
                    self.renderPipeline.setEffect(match, "Effects/Default/Default.effect", {
                        "transparent": True
                        })
                    match.setAttrib(CullFaceAttrib.make(CullFaceAttrib.M_none))

        for i in ["53", "54", "55", "56", "57"]:
            matches = self.scene.findAllMatches("**/" + i)
            for match in matches:
                match.remove()

        # Wheter to use a ground plane
        
        self.sceneWireframe = False

        # Flatten scene?
        self.loadingScreen.setStatus("Optimizing Scene", 90)

        # self.scene.clearModelNodes()
        loader.asyncFlattenStrong(self.scene, inPlace=False, callback=self.onScenePrepared)
        # self.onScenePrepared()

    def onScenePrepared(self, cb=None):
        """ Callback which gets called after the scene got prepared """

        self.scene.reparentTo(self.render)

        # Prepare textures with SRGB format
        self.prepareSRGB(self.scene)

        # Load ground plane if configured
        if self.usePlane:
            self.groundPlane = self.loader.loadModel(
                "Models/Plane/Plane.bam")
            # self.groundPlane.setPos(0, 0, -5.0)
            self.groundPlane.setTwoSided(True)
            self.groundPlane.flattenStrong()
            self.groundPlane.setName("GroundPlane")
            self.groundPlane.reparentTo(render)

        # Prepare Materials
        self.renderPipeline.fillTextureStages(render)

        # lerpTop = self.scene.posInterval(0.8, Vec3(0, 0, 7), startPos=Vec3(0,0,2))
        # lerpBot = self.scene.posInterval(0.8, Vec3(0, 0, 2), startPos=Vec3(0,0,7))
        # sequence = Sequence(lerpTop, lerpBot)
        # sequence.loop()


        # self.renderPipeline.setEffect(self.scene, "Effects/Default/Default.effect", {
        #     "dynamic": True,
        #     })

        # Some artists really don't know about backface culling
        # self.scene.setTwoSided(True)

        self.scene.set_transparency(True)
        self.scene.hide()

        # Create some ocean
        self.water = ProjectedWaterGrid(self.renderPipeline)
        self.water.setWaterLevel(-2.0)

        #
        if "sponza" in self.sceneSource:
            b1, b2 = self.scene.getTightBounds()

            c1 = loader.loadModel("Demoscene.ignore/CubeOpen/Scene.bam")
            c1.setPos(b1)
            c1.setScale(b2-b1)
            c1.reparentTo(render)
        
        # Required for tesselation
        self.convertToPatches(self.scene)

        # Hotkey for wireframe
        self.accept("f3", self.toggleSceneWireframe)

        # Hotkey to reload all shaders
        self.accept("r", self.setShaders)

        self.accept("f12", self.screenshot)

        # Hotkeys to spawn / remove lights
        self.accept("u", self.addDemoLight)
        self.accept("i", self.removeDemoLight)

        # Create movement controller (Freecam)
        self.controller = MovementController(self)
                
        camPos = Vec3(-34.68,-2.88,20.01)
        camHpr = Vec3(272.67,-5.55,0.0)
        self.controller.setInitialPositionHpr(
            camPos, camHpr)
        self.controller.setup()

        # self.fpCamera = FirstPersonCamera(self, self.cam, self.render)
        # self.fpCamera.start()

        # Load skybox
        self.skybox = self.renderPipeline.getDefaultSkybox()
        self.skybox.reparentTo(render)

        # Set default object shaders
        self.setShaders(refreshPipeline=False)

        # Hide loading screen
        self.loadingScreen.hide()
        # self.toggleSceneWireframe()
        self.renderPipeline.onSceneInitialized()

    def setSunPos(self):
        """ Sets the sun position based on the debug slider """

        radial = True
        rawValue = self.renderPipeline.guiManager.demoSlider.node["value"]
        diff = self.lastSliderValue - rawValue
        self.lastSliderValue = rawValue

        if radial:
            rawValue = rawValue / 100.0 * 2.0 * math.pi
            dPos = Vec3(
                math.sin(rawValue) * 30.0, math.cos(rawValue) * 30.0, 32.0)
            # dPos = Vec3(100, 100, self.lastSliderValue*2 10)
        else:
            dPos = Vec3(30, (rawValue - 50) * 1.5, 0)

        # dPos = Vec3(-2, 0, 40)

        if abs(diff) > 0.0001:
            if hasattr(self, "dirLight"):
                self.dirLight.setPos(dPos * 100000000.0)

    def toggleSceneWireframe(self):
        """ Toggles the scene rendermode """
        self.sceneWireframe = not self.sceneWireframe

        if self.sceneWireframe:
            render.setAttrib(RenderModeAttrib.make(RenderModeAttrib.MWireframe), 10)
            # render2d.setAttrib(RenderModeAttrib.make(RenderModeAttrib.MWireframe), 10)
        else:
            render.setAttrib(RenderModeAttrib.make(RenderModeAttrib.MFilled), 10)
            # render2d.setAttrib(RenderModeAttrib.make(RenderModeAttrib.MFilled), 10)
            
        self.skybox.setAttrib(RenderModeAttrib.make(RenderModeAttrib.MFilled), 20)

    def prepareSRGB(self, np):
        """ Sets the correct texture format for all textures found in <np> """
        for tex in np.findAllTextures():

            baseFormat = tex.getFormat()

            # Only diffuse textures should be SRGB
            if "diffuse" in tex.getName().lower():
                if baseFormat == Texture.FRgb:
                    tex.setFormat(Texture.FSrgb)
                elif baseFormat == Texture.FRgba:
                    tex.setFormat(Texture.FSrgbAlpha)
                elif baseFormat == Texture.FSrgb or baseFormat == Texture.FSrgbAlpha:
                    # Format is okay already
                    pass
                else:
                    print ("Unkown texture format:", baseFormat)
                    print ("\tTexture:", tex)

            # All textures should have the correct filter modes
            tex.setMinfilter(Texture.FTLinearMipmapLinear)
            tex.setMagfilter(Texture.FTLinear)
            tex.setAnisotropicDegree(16)

    def loadLights(self, scene):
        """ Loads lights from a .egg. Lights should be empty objects (blender) """
        model = self.loader.loadModel(scene)
        lights = model.findAllMatches("**/PointLight*")

        for prefab in lights:
            light = PointLight()
            light.setRadius(prefab.getScale().x)
            light.setColor(Vec3(2))
            light.setPos(prefab.getPos())
            light.setShadowMapResolution(512)
            light.setCastsShadows(False)
            self.renderPipeline.addLight(light)
            print ("Adding Light:", prefab.getPos(), prefab.getScale())
            self.lights.append(light)
            self.initialLightPos.append(prefab.getPos())
            self.test = light

    def setShaders(self, refreshPipeline=True):
        """ Sets all shaders """
        self.debug("Reloading Shaders ..")

        if self.renderPipeline:
            # for obj in self.transparentObjects:
            #     obj.setShader(
            #         self.renderPipeline.getDefaultTransparencyShader(), 30)

            if refreshPipeline:
                self.renderPipeline.reloadShaders()

    def convertToPatches(self, model):
        """ Converts a model to patches. This is required before being able
        to use it with tesselation shaders """
        self.debug("Converting model to patches ..")
        for node in model.find_all_matches("**/+GeomNode"):
            geom_node = node.node()
            num_geoms = geom_node.get_num_geoms()
            for i in range(num_geoms):
                geom_node.modify_geom(i).make_patches_in_place()


app = Main()
app.run()
