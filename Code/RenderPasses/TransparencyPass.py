
from panda3d.core import Shader

from Code.Globals import Globals
from Code.RenderPass import RenderPass
from Code.RenderTarget import RenderTarget


class TransparencyPass(RenderPass):

    """ This pass reads the per pixel linked lists generated during the deferred
    scene pass and applies them to the rendered image. To sort the lists a bubble
    sort algorithm is used """

    def __init__(self):
        RenderPass.__init__(self)

    def getID(self):
        return "TransparencyPass"

    def getRequiredInputs(self):
        return {
            "sceneTex": "LightingPass.resultTex",
            "cameraPosition": "Variables.cameraPosition",
            "depthTex": "DeferredScenePass.depth",

            "pixelCountBuffer": "Variables.transpPixelCountBuffer",
            "spinLockBuffer": "Variables.transpSpinLockBuffer",
            "listHeadBuffer": "Variables.transpListHeadBuffer",
            "materialDataBuffer": "Variables.transpMaterialDataBuffer",

            "transparencyShadeResult": "TransparencyShadePass.resultState",
            "velocityTex": "DeferredScenePass.velocity",
        }

    def setShaders(self):
        shader = Shader.load(Shader.SLGLSL, 
            "Shader/DefaultPostProcess.vertex",
            "Shader/TransparencyPass.fragment")
        self.target.setShader(shader)

        return [shader]

    def create(self):
        self.target = RenderTarget("TransparencyPass")
        self.target.addColorTexture()
        self.target.setColorBits(16)
        self.target.prepareOffscreenBuffer()

    def getOutputs(self):
        return {
            "TransparencyPass.resultTex": lambda: self.target.getColorTexture(),
        }

