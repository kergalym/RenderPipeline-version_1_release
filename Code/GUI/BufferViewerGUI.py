
import direct.gui.DirectGuiGlobals as DGG

from Code.Globals import Globals
from Code.DebugObject import DebugObject
from Code.RenderTargetType import RenderTargetType
from Code.GUI.BetterOnscreenImage import BetterOnscreenImage
from Code.GUI.BetterOnscreenText import BetterOnscreenText
from Code.GUI.BetterButton import BetterButton
from Code.GUI.CheckboxWithLabel import CheckboxWithLabel
from Code.GUI.UIWindow import UIWindow
from functools import partial

from Code.MemoryMonitor import MemoryMonitor

from panda3d.core import Vec3, Vec4
from direct.gui.DirectFrame import DirectFrame
from direct.interval.IntervalGlobal import Parallel, Func, Sequence


class FakeBuffer:

    """ Small wrapper to allow textures to be viewed in the texture viewer,
    which expects a RenderTarget. This class emulates the functions required
    by the BufferViewerGUI. """

    def __init__(self, tex):
        self.tex = tex

    def hasTarget(self, target):
        return target == RenderTargetType.Color

    def getTexture(self, target):
        return self.tex


class BufferViewerGUI(DebugObject):

    """ Simple gui to view texture buffers for debugging """

    buffers = {}
    bufferOrder = []

    @classmethod
    def registerBuffer(self, name, buff):
        self.buffers[name] = buff
        self.bufferOrder.append(name)

    @classmethod
    def unregisterBuffer(self, name):
        if name in self.buffers:
            del self.buffers[name]
            self.bufferOrder.remove(name)
        else:
            print("BufferViewer: Warning: buffer not in dictionary")

    @classmethod
    def registerTexture(self, name, tex):
        fb = FakeBuffer(tex)
        self.registerBuffer(name, fb)

    @classmethod
    def unregisterTexture(self, name):
        self.unregisterBuffer(name)

    def __init__(self, parent):
        DebugObject.__init__(self, "BufferViewer")
        self.parent = parent
        self.parent.setColorScale(0, 0, 0, 0)

        self.visible = False
        self.currentGUIEffect = None
        self.parent.hide()
        Globals.base.accept("v", self.toggle)

        self.window = UIWindow(
            "Buffer Viewer", 1480, 1040, parent)

        self.window.getNode().setPos(255, 1, -20)

        self.texWidth = 160
        self.texHeight = 90
        self.texPadding = 22
        self.pageSize = 7
        self.innerPadding = 8
        self.paddingTop = 40

        self.renderPassesOnly = True

        self.createComponents()

    def createComponents(self):
        self.buffersParent = self.window.getContentNode().attachNewNode(
            "buffers")
        self.togglePassOnly = CheckboxWithLabel(
            parent=self.window.getContentNode(), x=10, y=10,
            textSize=15, text="Display render passes only", chbChecked=True,
            chbCallback=self.setShowRenderPasses)

    def setShowRenderPasses(self, toggle):
        self.renderPassesOnly = toggle
        self.renderBuffers()

    def calculateTexSize(self, tex):
        dataSize = MemoryMonitor._calculateTexSize(tex)
        dataSizeMB = dataSize / (1024.0 * 1024.0)
        return round(dataSizeMB, 1)

    def renderBuffers(self):
        self.buffersParent.node().removeAllChildren()

        posX = 0
        posY = 0

        for name in self.bufferOrder:
            target = self.buffers[name]

            if isinstance(target, FakeBuffer) and self.renderPassesOnly:
                continue

            for targetType in RenderTargetType.All:
                if not target.hasTarget(targetType):
                    continue
                tex = target.getTexture(targetType)
                sizeStr = str(tex.getXSize()) + " x " + str(tex.getYSize())

                if tex.getZSize() != 1:
                    sizeStr += " x " + str(tex.getZSize())

                sizeStr += " - " + str(self.calculateTexSize(tex)) + " MB"

                col = (1,1,1,0.2)

                if not MemoryMonitor.isRegistered(tex):
                    col = (1,0.2,0,1)
                    print("Not found:", tex)

                node = DirectFrame(parent=self.buffersParent, frameColor=col, frameSize=(-self.innerPadding, self.texWidth + self.innerPadding, -self.texHeight - 30 - self.innerPadding, self.innerPadding + 15),
                    state=DGG.NORMAL)
                node.setPos(
                    20 + posX * (self.texWidth + self.texPadding), 0, -self.paddingTop - 22 - posY * (self.texHeight + self.texPadding + 44))
                node.bind(DGG.ENTER, partial(self.onMouseOver, node))
                node.bind(DGG.EXIT, partial(self.onMouseOut, node))
                node.bind(DGG.B1RELEASE, partial(self.showDetail, tex))

                aspect = tex.getYSize() / float(tex.getXSize())
                computedWidth = self.texWidth
                computedHeight = self.texWidth * aspect

                if computedHeight > self.texHeight:
                    # have to scale tex width instead
                    computedHeight = self.texHeight
                    computedWidth = tex.getXSize() / float(tex.getYSize()) * \
                        self.texHeight

                img = BetterOnscreenImage(
                    image=tex, parent=node, x=0, y=30, w=computedWidth,
                    h=computedHeight, transparent=False, nearFilter=False,
                    anyFilter=False)
                txtName = BetterOnscreenText(
                    text=name, x=0, y=0, size=13, parent=node)
                txtSizeFormat = BetterOnscreenText(
                    text=sizeStr, x=0, y=20, size=13, parent=node,
                    color=Vec3(0.2))
                txtTarget = BetterOnscreenText(
                    text=str(targetType), align="right", x=self.texWidth,
                    y=20, size=13, parent=node, color=Vec3(0.2))

                posX += 1
                if posX > self.pageSize:
                    posY += 1
                    posX = 0

    def showDetail(self, tex, coord):
        availableW = 1280
        availableH = 750

        texW, texH = tex.getXSize(), tex.getYSize()
        aspect = float(texH) / texW

        displayW = availableW
        displayH = displayW * aspect

        if displayH > availableH:
            displayH = availableH
            displayW = displayH / aspect

        self.buffersParent.node().removeAllChildren()

        img = BetterOnscreenImage(
            image=tex, parent=self.buffersParent, x=10, y=40, w=displayW, h=displayH,
            transparent=False, nearFilter=False, anyFilter=False)

        backBtn = BetterButton(
            self.buffersParent, 230, 2, "Back", callback=self.renderBuffers)
        writeBtn = BetterButton(
            self.buffersParent, 350, 2, "Write to Disk", callback=partial(self.writeTexToDisk, tex))

    def writeTexToDisk(self, tex):
        print("Writing", tex, "to disk ..")
        Globals.base.graphicsEngine.extractTextureData(tex, Globals.base.win.getGsg())
        tex.write(tex.getName() + ".png")
        print("Done!")

    def onMouseOver(self, node, a):
        node['frameColor'] = (1, 1, 1, 0.4)

    def onMouseOut(self, node, a):
        node['frameColor'] = (1, 1, 1, 0.2)

    def toggle(self):
        self.visible = not self.visible

        self.debug("Toggle buffer viewer")

        if self.currentGUIEffect is not None:
            self.currentGUIEffect.finish()

        if not self.visible:

            self.currentGUIEffect = Sequence(
                self.parent.colorScaleInterval(
                    0.12, Vec4(1, 1, 1, 0),
                    blendType="easeIn"),
                Func(self.parent.hide)

            )
            self.currentGUIEffect.start()

        else:
            self.renderBuffers()
            self.parent.show()
            self.currentGUIEffect = Parallel(
                self.parent.colorScaleInterval(
                    0.12, Vec4(1, 1, 1, 1),
                    blendType="easeIn"),
            )
            self.currentGUIEffect.start()
