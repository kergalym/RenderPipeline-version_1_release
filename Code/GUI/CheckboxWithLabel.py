
from panda3d.core import Vec3

from Code.GUI.BetterCheckbox import BetterCheckbox
from Code.GUI.BetterOnscreenText import BetterOnscreenText


class CheckboxWithLabel:

    """ This is a checkbox, combined with a label """

    def __init__(self, parent=None, x=0, y=0, chbCallback=None,
                 chbArgs=None, chbChecked=True, text="", textSize=15,
                 radio=False, textColor=None):

        if chbArgs is None:
            chbArgs = []

        if textColor is None:
            textColor = Vec3(1)

        self.checkbox = BetterCheckbox(
            parent=parent, x=x, y=y,
            callback=chbCallback, extraArgs=chbArgs,
            checked=chbChecked, radio=radio)
        self.text = BetterOnscreenText(x=x + 20, y=y + 7 + textSize / 3,
                                       text=text, align="left", parent=parent,
                                       size=textSize, color=textColor)

    def getCheckbox(self):
        """ Returns a handle to the checkbox """
        return self.checkbox

    def getLabel(self):
        """ Returns a handle to the label """
        return self.text
