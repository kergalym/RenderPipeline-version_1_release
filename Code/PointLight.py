
import math

from panda3d.core import NodePath, Vec4, Vec3, BoundingSphere, Point3
from panda3d.core import OmniBoundingVolume, CardMaker, TransparencyAttrib

from Code.Light import Light
from Code.DebugObject import DebugObject
from Code.LightType import LightType
from Code.ShadowSource import ShadowSource
from Code.Globals import Globals


class PointLight(Light, DebugObject):

    """ This light type simulates a PointLight. It has a position
    and a radius. The attenuation is computed based on a quadratic
    function.

    Shadows are simulated using a cubemap, which means that this light has
    6 Shadow maps, and when calling setShadowMapResolution() you are
    actually setting the resolution for all maps. 
    """

    def __init__(self):
        """ Creates a new point light. Remember to set a position
        and a radius """
        Light.__init__(self)
        DebugObject.__init__(self, "PointLight")
        self.bounds = BoundingSphere()
        self.spacing = 0.5
        self.bufferRadius = 0.0
        self.typeName = "PointLight"

    def getLightType(self):
        """ Internal method to fetch the type of this light, used by Light """
        return LightType.Point

    def _computeLightBounds(self):
        """ Recomputes the bounds of this light. For a PointLight, this
        is simple, as it's only a BoundingSphere """
        self.bounds.setCenter(self.position)
        self.bounds.setRadius(self.radius)

    def _updateDebugNode(self):
        """ Internal method to generate new debug geometry. """
        debugNode = NodePath("PointLightDebugNode")
        debugNode.setPos(self.position)

        # Create the inner image 
        cm = CardMaker("PointLightDebug")
        cm.setFrameFullscreenQuad()
        innerNode = NodePath(cm.generate())
        innerNode.setTexture(Globals.loader.loadTexture("Data/GUI/Visualization/PointLight.png"))
        innerNode.setBillboardPointEye()
        innerNode.reparentTo(debugNode)

        # Create the outer lines
        lineNode = debugNode.attachNewNode("lines")

        # Generate outer circles
        points1 = []
        points2 = []
        points3 = []
        for i in range(self.visualizationNumSteps + 1):
            angle = float(
                i) / float(self.visualizationNumSteps) * math.pi * 2.0
            points1.append(Vec3(0, math.sin(angle), math.cos(angle)))
            points2.append(Vec3(math.sin(angle), math.cos(angle), 0))
            points3.append(Vec3(math.sin(angle), 0, math.cos(angle)))

        self._createDebugLine(points1, False).reparentTo(lineNode)
        self._createDebugLine(points2, False).reparentTo(lineNode)
        self._createDebugLine(points3, False).reparentTo(lineNode)
        lineNode.setScale(self.radius)

        # Remove the old debug node
        self.debugNode.node().removeAllChildren()

        # Attach the new debug node
        debugNode.reparentTo(self.debugNode)
        # self.debugNode.flattenStrong()

    def _initShadowSources(self):
        """ Internal method to init the shadow sources """
        for i in range(6):
            source = ShadowSource()
            source.setupPerspectiveLens(1.0, self.radius, (100, 100))
            source.setResolution(self.shadowResolution)
            self._addShadowSource(source)

    def _updateShadowSources(self):
        """ Recomputes the position of the shadow sources. """

        # Position each 1 shadow source in 1 direction
        cubemapDirections = [
            Vec3(-1, 0, 0),
            Vec3(1, 0, 0),
            Vec3(0, -1, 0),
            Vec3(0, 1, 0),
            Vec3(0, 0, -1),
            Vec3(0, 0, 1),
        ]

        for index, direction in enumerate(cubemapDirections):
            self.shadowSources[index].setPos(self.position)
            self.shadowSources[index].lookAt(self.position + direction)

    def __repr__(self):
        """ Generates a string representation of this instance """
        return "PointLight[]"
