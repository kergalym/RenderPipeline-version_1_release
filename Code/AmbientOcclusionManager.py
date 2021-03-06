
from panda3d.core import Texture

from Code.Globals import Globals
from Code.DebugObject import DebugObject

from Code.RenderPasses.AmbientOcclusionPass import AmbientOcclusionPass
from Code.RenderPasses.OcclusionBlurPass import OcclusionBlurPass
from Code.RenderPasses.OcclusionCombinePass import OcclusionCombinePass
from Code.MemoryMonitor import MemoryMonitor

from Code.GUI.BufferViewerGUI import BufferViewerGUI


class AmbientOcclusionManager(DebugObject):

    """ The ambient occlusion manager handles the setup of the passes required
    to compute ambient occlusion. He also registers the configuration defines
    specified in the pipeline configuration """

    availableTechniques = ["SAO", "HBAO", "None"]

    def __init__(self, pipeline):
        """ Creates the manager and directly creates the passes """
        DebugObject.__init__(self, "AmbientOcclusion")
        self.pipeline = pipeline
        self.create()

    def create(self):
        """ Creates the passes required to compute the occlusion, selecting
        the appropriate pass for the selected technique """

        technique = self.pipeline.settings.occlusionTechnique

        if technique not in self.availableTechniques:
            self.error("Unrecognized technique: " + technique)
            return

        if technique == "None":
            return

        # Create the ambient occlusion pass. The technique is selected in the 
        # shader later, based on the defines
        self.aoPass = AmbientOcclusionPass()
        self.pipeline.getRenderPassManager().registerPass(self.aoPass)

        # Create the ambient occlusion blur pass
        self.blurPass = OcclusionBlurPass()
        self.pipeline.getRenderPassManager().registerPass(self.blurPass)

        # Register the configuration defines
        self.pipeline.getRenderPassManager().registerDefine("OCCLUSION_TECHNIQUE_" + technique, 1)
        self.pipeline.getRenderPassManager().registerDefine("USE_OCCLUSION", 1)
        self.pipeline.getRenderPassManager().registerDefine("OCCLUSION_RADIUS", 
            self.pipeline.settings.occlusionRadius)
        self.pipeline.getRenderPassManager().registerDefine("OCCLUSION_STRENGTH", 
            self.pipeline.settings.occlusionStrength)
        self.pipeline.getRenderPassManager().registerDefine("OCCLUSION_SAMPLES", 
            self.pipeline.settings.occlusionSampleCount)
        if self.pipeline.settings.useLowQualityBlur:
            self.pipeline.getRenderPassManager().registerDefine("USE_LOW_QUALITY_BLUR", 1)
        if self.pipeline.settings.useOcclusionNoise:
            self.pipeline.getRenderPassManager().registerDefine("USE_OCCLUSION_NOISE", 1)

        if self.pipeline.settings.useTemporalOcclusion:
            
            # Create a texture to store the last frame occlusion
            self.lastFrameOcclusionTex = Texture("LastFrameOcclusion")
            self.lastFrameOcclusionTex.setup2dTexture(Globals.resolution.x,
                Globals.resolution.y, Texture.TFloat, Texture.FR16)
            self.pipeline.getRenderPassManager().registerStaticVariable("lastFrameOcclusion", self.lastFrameOcclusionTex)

            BufferViewerGUI.registerTexture("LastFrameOcclusion", self.lastFrameOcclusionTex)
            MemoryMonitor.addTexture("LastFrameOcclusion", self.lastFrameOcclusionTex)
            self.pipeline.getRenderPassManager().registerDefine("USE_TEMPORAL_OCCLUSION", 1)
            self.combinePass = OcclusionCombinePass()
            self.pipeline.getRenderPassManager().registerPass(self.combinePass)