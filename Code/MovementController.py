
from panda3d.core import ModifierButtons, Vec3, PStatClient

from Code.MemoryMonitor import MemoryMonitor


class MovementController:

    """ This is a helper class, used to controll the camera and enable various
    debugging features. It is not really part of the pipeline, but included to
    view the demo scenes. """

    def __init__(self, showbase):
        self.showbase = showbase
        self.movement = [0, 0, 0]
        self.velocity = Vec3(0.0)
        self.hprMovement = [0,0]
        self.speed = 1.0
        self.initialPosition = Vec3(0)
        self.initialDestination = Vec3(0)
        self.initialHpr = Vec3(0)
        self.mouseEnabled = False
        self.lastMousePos = [0,0]
        self.mouseSensivity = 0.7
        self.keyboardHprSpeed = 0.8
        self.useHpr = False
        self.smoothness = 0.8
        self.smoothness = 0.0
        # self.smoothness = 0.0

    def setInitialPosition(self, pos, target):
        """ Sets the initial camera position """
        self.initialPosition = pos
        self.initialDestination = target
        self.useHpr = False
        self._resetToInitial()

    def setInitialPositionHpr(self, pos, hpr):
        """ Sets the initial camera position """
        self.initialPosition = pos
        self.initialHpr = hpr
        self.useHpr = True
        self._resetToInitial()

    def _resetToInitial(self):
        """ Resets the camera to the initial position """
        self.showbase.camera.setPos(self.initialPosition)

        if self.useHpr:
            self.showbase.camera.setHpr(self.initialHpr)
        else:
            self.showbase.camera.lookAt(
                self.initialDestination.x, self.initialDestination.y, self.initialDestination.z)

    def _setMovement(self, direction, amount):
        self.movement[direction] = amount

    def _setHprMovement(self, direction, amount):
        self.hprMovement[direction] = amount

    def _setMouseEnabled(self, enabled):
        self.mouseEnabled = enabled

    def _increaseSpeed(self):
        self.speed *= 1.4

    def _decreaseSpeed(self):
        self.speed *= 0.6

    def unbind(self):
        """ Unbinds the movement controler and restores the previous state """
        raise NotImplementedError()


    def setup(self):
        """ Attaches the movement controller and inits the keybindings """

        # x
        self.showbase.accept("w",       self._setMovement, [0, 1])
        self.showbase.accept("w-up",    self._setMovement, [0, 0])
        self.showbase.accept("s",       self._setMovement, [0, -1])
        self.showbase.accept("s-up",    self._setMovement, [0, 0])

        # y
        self.showbase.accept("a",       self._setMovement, [1, -1])
        self.showbase.accept("a-up",    self._setMovement, [1, 0])
        self.showbase.accept("d",       self._setMovement, [1, 1])
        self.showbase.accept("d-up",    self._setMovement, [1, 0])

        # z
        self.showbase.accept("space",   self._setMovement, [2, 1])
        self.showbase.accept("space-up", self._setMovement, [2, 0])
        self.showbase.accept("shift",   self._setMovement, [2, -1])
        self.showbase.accept("shift-up", self._setMovement, [2, 0])

        # wireframe + debug + buffer viewer
        # self.showbase.accept("f3", self.showbase.toggleWireframe)
        self.showbase.accept("p",  self._showDebugOutput)

        # mouse
        self.showbase.accept("mouse1",    self._setMouseEnabled, [True])
        self.showbase.accept("mouse1-up", self._setMouseEnabled, [False])

        # arrow mouse navigation
        self.showbase.accept("arrow_up",        self._setHprMovement, [1, 1])
        self.showbase.accept("arrow_up-up",     self._setHprMovement, [1, 0])
        self.showbase.accept("arrow_down",      self._setHprMovement, [1, -1])
        self.showbase.accept("arrow_down-up",   self._setHprMovement, [1, 0])
        self.showbase.accept("arrow_left",      self._setHprMovement, [0, 1])
        self.showbase.accept("arrow_left-up",   self._setHprMovement, [0, 0])
        self.showbase.accept("arrow_right",     self._setHprMovement, [0, -1])
        self.showbase.accept("arrow_right-up",  self._setHprMovement, [0, 0])

        # increase / decrease speed
        self.showbase.accept("+", self._increaseSpeed)
        self.showbase.accept("-", self._decreaseSpeed)

        # disable modifier buttons to be able to move while pressing shift for
        # example
        self.showbase.mouseWatcherNode.setModifierButtons(ModifierButtons())
        self.showbase.buttonThrowers[
            0].node().setModifierButtons(ModifierButtons())

        # disable pandas builtin mouse control
        self.showbase.disableMouse()

        # add ourself as an update task
        self.showbase.addTask(
            self._update, "updateMovementController", priority=-19000)


        self.showbase.accept("1", PStatClient.connect)
        self.showbase.accept("3", self._resetToInitial)

    def _update(self, task):
        """ Internal update method """

        # Update mouse first
        if self.showbase.mouseWatcherNode.hasMouse():
            x = self.showbase.mouseWatcherNode.getMouseX()
            y = self.showbase.mouseWatcherNode.getMouseY()
            self.currentMousePos = [x * 90 * self.mouseSensivity, y * 70 * self.mouseSensivity]

            if self.mouseEnabled:
                diffx = self.lastMousePos[0] - self.currentMousePos[0]
                diffy = self.lastMousePos[1] - self.currentMousePos[1]

                # no move on the beginning
                if self.lastMousePos[0] == 0 and self.lastMousePos[1] == 0:
                    diffx = 0
                    diffy = 0

                self.showbase.camera.setH(self.showbase.camera.getH() + diffx)
                self.showbase.camera.setP(self.showbase.camera.getP() - diffy)

            self.lastMousePos = self.currentMousePos[:]

        # Compute movement in render space
        movementDirection = (Vec3(self.movement[1], self.movement[0], 0)
                             * self.speed
                             * self.showbase.taskMgr.globalClock.getDt() * 100.0)

        # Transform by camera direction
        cameraQuaternion = self.showbase.camera.getQuat(self.showbase.render)
        translatedDirection = cameraQuaternion.xform(movementDirection)
      

        # zforce is independent of camera direction
        translatedDirection.addZ(
            self.movement[2] * self.showbase.taskMgr.globalClock.getDt() * 40.0 * self.speed)

        self.velocity += translatedDirection*0.15

        # apply new position
        self.showbase.camera.setPos(
            self.showbase.camera.getPos() + self.velocity)
        
        self.velocity *= self.smoothness

        # transform rotation (keyboard keys)
        rotationSpeed = self.keyboardHprSpeed * 100.0 * self.showbase.taskMgr.globalClock.getDt()
        self.showbase.camera.setHpr(self.showbase.camera.getHpr() + Vec3(self.hprMovement[0],self.hprMovement[1],0) * rotationSpeed )

        return task.cont



    def _showDebugOutput(self):
        """ Lists the available debug options """
        print("\n" * 5)
        print("DEBUG MENU")
        print("-" * 50)
        print("Select an option:")
        print("\t(1) Connect to pstats")
        print("\t(2) Toggle frame rate meter")
        print("\t(3) Reset to initial position")
        print("\t(4) Display camera position")
        print("\t(5) Show scene graph")
        print("\t(6) Open placement window")
        print("\t(7) Analyze VRAM")

        selectedOption = input("Which do you want to choose?: ")

        try:
            selectedOption = int(selectedOption.strip())
        except:
            print("Option has to be a valid number!")
            return False

        if selectedOption < 1 or selectedOption > 7:
            print("Invalid option!")
            return False

        # pstats
        if selectedOption == 1:
            print("Connecting to pstats ..")
            print("If you have no pstats running, this will take 5 seconds to timeout ..")
            PStatClient.connect()

        # frame rate meter
        elif selectedOption == 2:
            print("Toggling frame rate meter ..")
            self.showbase.setFrameRateMeter(not self.showbase.frameRateMeter)

        # initial position
        elif selectedOption == 3:
            print("Reseting camera position / hpr ..")
            self._resetToInitial()

        # display camera pos
        elif selectedOption == 4:
            print("Debug information:")
            campos = self.showbase.cam.getPos(self.showbase.render)
            camrot = self.showbase.cam.getHpr(self.showbase.render)
            print("camPos = Vec3(" + str(round(campos.x, 2)) + "," + str(round(campos.y, 2)) + "," + str(
                round(campos.z, 2)) + ")")
            print("camHpr = Vec3(" + str(round(camrot.x, 2)) + "," + str(round(camrot.y, 2)) + "," + str(
                round(camrot.z, 2)) + ")")


        # show scene graph
        elif selectedOption == 5:
            print("SCENE GRAPH:")
            print("-" * 50)
            self.showbase.render.ls()
            print("-" * 50)
            print("ANALYZED:")
            print("-" * 50)
            self.showbase.render.analyze()
            print("-" * 50)

        # placement window
        elif selectedOption == 6:
            print("Opening placement window. You need tkinter installed to be able to use it")
            self.showbase.render.place()
            # print "It seems .place() is currently not working. Sorry!!"
    
        # vram analyszs
        elif selectedOption == 7:
            print("Analyzing VRAM ...")
            MemoryMonitor.analyzeMemory()
