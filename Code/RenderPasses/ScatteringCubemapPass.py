
from panda3d.core import NodePath, Shader, LVecBase2i, Texture, GeomEnums

from Code.Globals import Globals
from Code.RenderPass import RenderPass
from Code.RenderTarget import RenderTarget


class ScatteringCubemapPass(RenderPass):

    """ This pass computes the scattering to a cubemap """

    def __init__(self, pipeline):
        RenderPass.__init__(self)
        self.cubemapSize = pipeline.settings.scatteringCubemapSize
        self.pipeline = pipeline

    def getID(self):
        return "ScatteringCubemapPass"

    def getRequiredInputs(self):
        return {
            "transmittanceSampler": ["Variables.transmittanceSampler", "Variables.emptyTextureWhite"],
            "inscatterSampler": ["Variables.inscatterSampler", "Variables.emptyTextureWhite"],
            "scatteringOptions": ["Variables.scatteringOptions", "Variables.null"],
        }

    def create(self):
        self.cubemap = Texture("Scattering Cubemap")
        self.cubemap.setupCubeMap(self.cubemapSize, Texture.TFloat, Texture.FRgba16)
        self.cubemap.setMinfilter(Texture.FTLinearMipmapLinear)
        self.cubemap.setMagfilter(Texture.FTLinear)

        self.target = RenderTarget("ScatteringCubemap")
        self.target.setSize(self.cubemapSize * 6, self.cubemapSize)

        if self.pipeline.settings.useDebugAttachments:
            self.target.addColorTexture()
        
        self.target.prepareOffscreenBuffer()
        self.target.setShaderInput("cubemapSize", self.cubemapSize)
        self.target.setShaderInput("cubemapDest", self.cubemap)

    def setShaders(self):
        shader = Shader.load(Shader.SLGLSL, 
            "Shader/DefaultPostProcess.vertex",
            "Shader/ScatteringCubemapPass.fragment")
        self.target.setShader(shader)
        return [shader]

    def getOutputs(self):
        return {
            "ScatteringCubemapPass.resultCubemap": lambda: self.cubemap,
        }
