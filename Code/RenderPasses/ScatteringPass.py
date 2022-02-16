
from panda3d.core import NodePath, Shader, LVecBase2i, Texture, GeomEnums

from Code.Globals import Globals
from Code.RenderPass import RenderPass
from Code.RenderTarget import RenderTarget


class ScatteringPass(RenderPass):

    """ This pass computes the scattering if specified in the settings """

    def __init__(self):
        RenderPass.__init__(self)

    def getID(self):
        return "ScatteringPass"

    def getRequiredInputs(self):
        return {

            # Scattering
            "transmittanceSampler": ["Variables.transmittanceSampler", "Variables.emptyTextureWhite"],
            "inscatterSampler": ["Variables.inscatterSampler", "Variables.emptyTextureWhite"],
            "irradianceSampler": ["Variables.irradianceSampler", "Variables.emptyTextureWhite"],
            "scatteringOptions": ["Variables.scatteringOptions", "Variables.null"],

            "mainRender": "Variables.mainRender",
            "cameraPosition": "Variables.cameraPosition",
            "mainCam": "Variables.mainCam",

            "skyboxMask": "SkyboxMaskPass.resultTex",

            "depthTex": "DeferredScenePass.depth",
            "basecolorTex": "DeferredScenePass.data2",

            "cloudsTex": ["CloudRenderPass.resultTex", "Variables.emptyTextureWhite"]
        }

    def create(self):
        self.target = RenderTarget("Scattering")
        self.target.addColorTexture()
        self.target.addAuxTexture()
        self.target.setAuxBits(16)
        self.target.setColorBits(16)
        self.target.prepareOffscreenBuffer()
 
    def setShaders(self):
        shader = Shader.load(Shader.SLGLSL, 
            "Shader/DefaultPostProcess.vertex",
            "Shader/ScatteringPass.fragment")
        self.target.setShader(shader)
        return [shader]

    def getOutputs(self):
        return {
            "ScatteringPass.resultTex": lambda: self.target.getColorTexture(),
            "ScatteringPass.attenuationTex": lambda: self.target.getAuxTexture(0),
        }
