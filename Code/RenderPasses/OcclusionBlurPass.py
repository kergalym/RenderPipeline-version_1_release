
from panda3d.core import NodePath, Shader, LVecBase2i, Texture, GeomEnums

from Code.Globals import Globals
from Code.RenderPass import RenderPass
from Code.RenderTarget import RenderTarget


class OcclusionBlurPass(RenderPass):

    """ This pass performs a edge preserving blur by comparing the scene normals
    during the blur pass, aswell as as bilateral upscaling the occlusion input. """

    def __init__(self):
        RenderPass.__init__(self)

    def getID(self):
        return "OcclusionBlurPass"

    def getRequiredInputs(self):
        return {
            "sourceTex":  "AmbientOcclusionPass.computeResult", 
            "normalTex": "DeferredScenePass.wsNormal",
            "depthTex": "DeferredScenePass.depth",

        }

    def create(self):
        self.targetV = RenderTarget("OcclusionBlurV")
        self.targetV.setHalfResolution()
        self.targetV.addColorTexture()
        self.targetV.prepareOffscreenBuffer()
 
        self.targetH = RenderTarget("OcclusionBlurH")
        self.targetH.setHalfResolution()
        self.targetH.addColorTexture()
        self.targetH.prepareOffscreenBuffer()

        self.targetH.setShaderInput("processedSourceTex", self.targetV.getColorTexture())

    def setShaders(self):
        shaderV = Shader.load(Shader.SLGLSL, 
            "Shader/DefaultPostProcess.vertex",
            "Shader/OcclusionBlurV.fragment")
        self.targetV.setShader(shaderV)

        shaderH = Shader.load(Shader.SLGLSL, 
            "Shader/DefaultPostProcess.vertex",
            "Shader/OcclusionBlurH.fragment")
        self.targetH.setShader(shaderH)

        return [shaderV, shaderH]

    def getOutputs(self):
        return {
            "OcclusionBlurPass.blurResult": lambda: self.targetH.getColorTexture(),
        }

    def setShaderInput(self, name, value):
        self.targetH.setShaderInput(name, value)
        self.targetV.setShaderInput(name, value)
