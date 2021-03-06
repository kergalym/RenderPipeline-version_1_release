
from panda3d.core import Texture, TransparencyAttrib
from direct.gui.DirectCheckBox import DirectCheckBox
import direct.gui.DirectGuiGlobals as DGG

from Code.DebugObject import DebugObject
from Code.Globals import Globals


class BetterCheckbox(DebugObject):

    """ This is a wrapper around DirectCheckBox, providing a simpler interface
    and better visuals """

    def __init__(self, parent=None, x=0, y=0, callback=None, extraArgs=None,
                 radio=False, expandW=100, checked=False):
        DebugObject.__init__(self, "BetterCheckbox")

        prefix = "Checkbox" if not radio else "Radiobox"

        checkedImg = Globals.loader.loadTexture(
            "Data/GUI/" + prefix + "Active.png")
        uncheckedImg = Globals.loader.loadTexture(
            "Data/GUI/" + prefix + "Empty.png")

        # Set near filter, otherwise textures look like crap
        for tex in [checkedImg, uncheckedImg]:
            tex.setMinfilter(Texture.FTNearest)
            tex.setMagfilter(Texture.FTNearest)
            tex.setAnisotropicDegree(0)
            tex.setWrapU(Texture.WMClamp)
            tex.setWrapV(Texture.WMClamp)

        self._node = DirectCheckBox(parent=parent, pos=(
            x + 7.5, 1, -y - 7.5), scale=(15 / 2.0, 1, 15 / 2.0),
            checkedImage=checkedImg, uncheckedImage=uncheckedImg,
            image=uncheckedImg, extraArgs = extraArgs, state=DGG.NORMAL,
            relief=DGG.FLAT, command=self._updateStatus)

        self._node["frameColor"] = (0, 0, 0, 0.0)
        self._node["frameSize"] = (-2, 2 + expandW / 7.5, -1.6, 1.6)

        self._node.setTransparency(TransparencyAttrib.MAlpha)

        self.callback = callback
        self.extraArgs = extraArgs
        self.collection = None

        if checked:
            self._setChecked(True)

    def _setCollection(self, coll):
        """ Internal method to add a checkbox to a checkbox collection, this
        is used for radio-buttons """

        self.collection = coll

    def _updateStatus(self, status, *args):
        """ Internal method when another checkbox in the same radio group
        changed it's value """
        if self.collection:
            if status:
                self.collection._changed(self)
                # A radio box can't be unchecked
                self._node["state"] = DGG.DISABLED

        if self.callback is not None:
            self.callback(*([status] + self.extraArgs))

    def _setChecked(self, val):
        """ Internal method to check/uncheck the checkbox """
        self._node["isChecked"] = val

        if val:
            self._node['image'] = self._node['checkedImage']
        else:
            self._node['image'] = self._node['uncheckedImage']

        if self.callback is not None:
            self.callback(*([val] + self.extraArgs))
