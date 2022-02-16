
from panda3d.core import NodePath, Shader, LVecBase2i, Texture, PTAFloat, Vec4

from Code.Globals import Globals
from Code.RenderPass import RenderPass
from Code.RenderTarget import RenderTarget


class FinalPostprocessPass(RenderPass):

    """ This pass does the final postprocessing, including color correction and
    adding a vignette. """

    def __init__(self):
        RenderPass.__init__(self)

    def getID(self):
        return "FinalPostprocessPass"

    def getRequiredInputs(self):
        return {
            "colorTex": ["MotionBlurPass.resultTex",
                         "AntialiasingPass.resultTex",
                         "BloomPass.resultTex",
                         "ExposurePass.resultTex"],

            "colorLUT": "Variables.colorLUT",
            "velocityTex": "DeferredScenePass.velocity",
        }

    def create(self):
        self.target = RenderTarget("Final Pass")
        # The final pass is at full res
        self.target.setSize(Globals.base.win.getXSize(), Globals.base.win.getYSize())

        self.target.addColorTexture()
        self.target.prepareOffscreenBuffer()

        # Make this pass show on the screen
        Globals.base.win.getDisplayRegion(1).setCamera(self.target._camera)

    def setShaders(self):
        shader = Shader.load(Shader.SLGLSL, 
            "Shader/DefaultPostProcess.vertex",
            "Shader/FinalPostprocessPass.fragment")
        self.target.setShader(shader)

        return [shader]
