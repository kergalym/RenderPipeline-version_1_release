
from panda3d.core import NodePath, Shader, LVecBase2i, Texture, GeomEnums

from Code.Globals import Globals
from Code.RenderPass import RenderPass
from Code.RenderTarget import RenderTarget


class AmbientOcclusionPass(RenderPass):

    """ This pass computes the screen space ambient occlusion if enabled in the
     settings. As many samples are required for a good looking result, the pass
     is done at half resolution and then upscaled by the edge preserving blur
     pass """

    def __init__(self):
        RenderPass.__init__(self)

    def getID(self):
        return "AmbientOcclusionPass"

    def getRequiredInputs(self):
        return {
            "frameIndex": "Variables.frameIndex",
            "mainRender": "Variables.mainRender",
            "mainCam": "Variables.mainCam",
            "depthTex": "DeferredScenePass.depth",
            "cameraPosition": "Variables.cameraPosition",
            "currentViewMat": "Variables.currentViewMat",
            "currentProjMatInv": "Variables.currentProjMatInv",
            "noiseTex": "Variables.noise4x4"
        }

    def create(self):
        self.target = RenderTarget("AmbientOcclusion")
        self.target.setHalfResolution()
        self.target.addColorTexture()
        self.target.prepareOffscreenBuffer()
 
    def setShaders(self):
        shader = Shader.load(Shader.SLGLSL, 
            "Shader/DefaultPostProcess.vertex",
            "Shader/ComputeOcclusion.fragment")
        self.target.setShader(shader)
        return [shader]

    def getOutputs(self):
        return {
            "AmbientOcclusionPass.computeResult": lambda: self.target.getColorTexture(),
        }
