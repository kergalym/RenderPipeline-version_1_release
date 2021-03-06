import time
from os.path import join
from panda3d.core import Shader
from direct.stdpy.file import open

from Code.DebugObject import DebugObject


class Effect(DebugObject):
    
    effectCount = 0

    def __init__(self):
        DebugObject.__init__(self, "Effect")

        Effect.effectCount += 1

        self.effectID = Effect.effectCount
        self.name = "Effect"
        self.properties = {
            "transparent": False,
            "alphaTest": False,
            "normalMapping": True,
            "dynamic": False,
            "castShadows": True,
            "castGI": True,
            "mainPass": True
        }
        self.assignments = {"Default": [], "Shadows": [], "Voxelize": [], "EarlyZ": []}

    def load(self, filename):
        """ Loads the effect from a given filename """
        self.debug("Load effect from", filename)

        self.defines = {}
        self.source = filename
        self.shaderParts = {"Default": {}, "Shadows": {}, "Voxelize": {}, "EarlyZ": {}}
        self.shaderObjs = {"Default": None, "Shadows": None, "Voxelize": None, "EarlyZ": None}
        self._handleProperties()
        self.name = filename.replace("\\", "/").split("/")[-1].split(".")[0]
        self._rename("Effect-" + self.name)

        with open(filename, "r") as handle:
            content = handle.readlines()

        self._parse(content)
        self._createShaderObjects()

    def assignNode(self, node, mode, sort=0):
        """ Adds the node to the assigned nodes of the mode. This is used when
        reloading shaders """
        if node not in self.assignments[mode]:
            self.assignments[mode].append((node, sort))
        node.setShader(self.getShader(mode), sort)

    def reload(self):
        """ Reloads the effect from disk """

        self.load(self.source)

        for node, sort in self.assignments["Default"]:
            node.setShader(self.getShader("Default"), sort)

    def getSerializedSettings(self, properties=None):
        """ Serializes the effects properties to a string """
        serialized = ""
        for key in sorted(self.properties):
            val = self.properties[key]
            if properties and key in properties:
                val = properties[key]
            serialized += "1" if val else "0"
        return serialized

    def getEffectID(self):
        """ Returns the effects uid """
        return self.effectID

    def getSetting(self, name):
        """ Returns the settings value """
        return self.properties[name]

    def setSettings(self, settings):
        """ Overrides the settings with the given settings """
        for key, val in settings.items():
            if key in self.properties:
                self.properties[key] = val
            else:
                self.warn("Unkown setting:", key)

    def hasShader(self, stage):
        """ Returns Whether there exists a shader for the given stage """
        return stage in self.shaderObjs and self.shaderObjs[stage] is not None

    def getShader(self, stage):
        """ Returns the created shader for a given stage, or None if no shader
        for that stage exists """
        return self.shaderObjs[stage]

    def _createShaderObjects(self):
        """ Creates the shaders from the parsed shader code """
        for stage, parts in self.shaderParts.items():
            if len(parts) < 1:
                # No program defined
                continue

            programs = {"vertex": "", "fragment": "", "geometry": "", 
                "tesscontrol": "", "tesseval": ""}
            for progName, progCode in parts.items():
                fname = self._createShaderFile(stage, progName, progCode)
                programs[progName] = fname

            if programs["vertex"] == "":

                # Default stage always needs a vertex shader
                # if stage == "Default":
                self.error("No vertex program stage "+ stage + " defined! Using default shader!")
                # else:
                #     if "Default" in self.shaderParts and "vertex" in self.shaderParts["Default"]:
                #         vertex_prog = self.shaderParts["Default"]["vertex"]
                #         programs["vertex"] = vertex_prog
                #         self.warn("Using vertex shader from default stage for stage " + stage)
                #     else:
                #         self.error("Stage " + stage + " has no vertex program, and no default stage is available!")

                continue

            params = [programs["vertex"], programs["fragment"], programs["geometry"], 
                programs["tesscontrol"], programs["tesseval"]]
            shaderObj = Shader.load(Shader.SLGLSL, *params)
            self.shaderObjs[stage] = shaderObj

    def _createShaderFile(self, stage, part, code):
        """ Writes the shader code to a temporary file and returns the path to that
        file """

        filename = "PipelineTemp/$$-Effect" + str(self.getEffectID()) + "_" + self.name + "_" + stage + "_" + part + "_" + self.getSerializedSettings() + ".tmp.glsl"

        with open(filename, "w") as handle:
            handle.write(code)

        return filename

    def _getIdentationLevel(self, line):
        """ Counts the amount of spaces at the beginning of a line and returns
        the level of identation """
        spaces = line.lstrip()
        diff = len(line) - len(spaces)
        return int(diff / 4)

    def _handleProperties(self):
        """ Internal method to convert the properties to defines """

        if self.properties["transparent"]:
            self.defines["IS_TRANSPARENT"] = 1
        if self.properties["alphaTest"]:
            self.defines["USE_ALPHA_TEST"] = 1
        if self.properties["normalMapping"]:
            self.defines["USE_NORMAL_MAPPING"] = 1
        if self.properties["dynamic"]:
            self.defines["IS_DYNAMIC"] = 1

    def _handleBlocks(self, lines, block_lvl=0):
        """ Scans the given set of lines for block definitions of the given
        block level and returns a list of all blocks found """

        inBlock = False
        blockLines = []
        blocks = []

        # Iterate over all lines
        for line in lines:

            # Check if the line has the required identation level
            lvl = self._getIdentationLevel(line)
            if lvl == block_lvl:

                # Some lines might have the correct identation level, but are
                # no block definition, so we have to check if its actually a block
                if ":" in line:
                    if inBlock:
                        blocks.append(blockLines)
                    inBlock = True
                    blockLines = [line]

            # In case the line is no block definition, and we are currently in a 
            # block, append it to the current block lines
            elif inBlock:
                blockLines.append(line)

        # If we are still in a block, close it
        if inBlock:
            blocks.append(blockLines)

        return blocks

    def _parseTemplate(self, filename):
        """ Parses a shader template file and returns its content """

        with open(filename, "r") as handle:
            content = handle.readlines()

        parsedLines = []

        for line in content:
            line = line.rstrip()
            parsedLines.append(line)

        return parsedLines

    def _createShaderCode(self, parameters, inserts, stage, program):
        """ Creates the shader code from a given set of parameters and inserts """

        if "template" not in parameters:
            self.error("No template specified")
            return False

        if len(parameters["template"]) != 1:
            self.error("None or multiple templates specified")
            return False

        # Convert parameters to get inserted at the INOUT entrypoint
        if "SHADER_IN_OUT" not in inserts:
            inserts["SHADER_IN_OUT"] = []

        for param, lines in parameters.items():
            if param == "in":
                for line in lines:
                    inserts["SHADER_IN_OUT"].append("in " + line.rstrip(";") + ";");
            elif param == "out":
                for line in lines:
                    inserts["SHADER_IN_OUT"].append("out " + line.rstrip(";") + ";");
            elif param == "uniform":
                for line in lines:
                    inserts["SHADER_IN_OUT"].append("uniform " + line.rstrip(";") + ";"); 
            elif param == "include":
                for line in lines:
                    includePath = line.strip('"')
                    inserts["SHADER_IN_OUT"].append("#pragma include \"" +includePath + "\""); 
            elif param == "template":
                pass
            else:
                self.warn("Unkown parameter", param)

        if "SHADER_IN_OUT" not in inserts:
            self.warn("Warning, shader template has no in/out section!")

        # Convert defines to get inserted after the shader version directive
        defineContent  = []

        for key, val in self.defines.items():
            defineContent.append("#define " + key + " " + str(val))

        templateFile = parameters["template"][0]

        if templateFile.lower() == "default":
            # When there is no template specified, assume the default template
            templateFile = join("ShaderMount/", "DefaultShaders/" + stage + "/" + program + ".glsl")
        else:
            templateFile = join("ShaderMount/", templateFile.strip('"'))

        templateContent = self._parseTemplate(templateFile)

        builtShader = ["// Autogenerated, do not edit"]

        for line in templateContent:
            if not line.strip().startswith("#pragma ENTRY_POINT"):
                builtShader.append(line)
                if line.strip().startswith("#version"):
                    builtShader += defineContent
            else:
                entryPointName = line.strip().split()[-1]

                if entryPointName in inserts:
                    for insert in inserts[entryPointName]:
                        builtShader.append(insert.lstrip())

        return "\n".join(builtShader)

    def _parse(self, lines):
        """ Reads the effect file, extracts all shader parts, parses them and stores
        them in the internal shader parts array """
            
        strippedLines = []

        # Strip lines
        for line in lines:
            line = line.rstrip()
            if len(line.strip()) < 1:
                continue
            if line.strip().startswith("//"):
                continue
            strippedLines.append(line)
        
        # Check for defines
        for line in strippedLines:
            if line.startswith("define"):
                parts = line.split()
                if len(parts) < 3:
                    self.warn("Invalid define:", line)
                    continue
                defineName = parts[1]
                defineVal = " ".join(parts[2:])

                self.defines[defineName] = defineVal

        # Extract blocks
        stageBlocks = self._handleBlocks(strippedLines)

        defaultArgs = {}

        for stageBlock in stageBlocks:
            blockName = stageBlock[0].rstrip(":").split()[-1]

            if blockName not in ["Default", "Shadows", "Voxelize", "EarlyZ"]:
                self.error("Unkown block name:", blockName)
                continue

            # Extract block shaders
            parts = self._handleBlocks(stageBlock[1:], block_lvl = 1)

            for part in parts:
                partName = part[0].rstrip(":").strip()

                parameters = {}
                inserts = {}

                # Iterate over shader lines and find parameters
                for line in part[1:]:
                    if not line.startswith(" "*8):
                        self.error("Wrong identation:", line)
                        continue
                    line = line[8:]
                    lvl = self._getIdentationLevel(line)

                    if lvl == 0:
                        paramName = line.split()[0]

                        # Check if the param is supported
                        if paramName not in ["in", "out", "template", "insert", "uniform", "include"]:
                            self.error("Unkown keyword", paramName)
                            continue

                        # Ignore insert params as they are parsed later on
                        if paramName in ["insert"]:
                            continue

                        paramValue = " ".join(line.split()[1:])

                        if paramName in parameters:
                            parameters[paramName].append(paramValue)
                        else:
                            parameters[paramName] = [paramValue]

                # Find shader insertions
                shaderBlocks = self._handleBlocks(part, block_lvl=2)

                for shaderBlock in shaderBlocks:
                    shaderBlockTitle = shaderBlock[0].rstrip(":").strip().split()
                    shaderBlockName = shaderBlockTitle[-1]
                    shaderBlockType = shaderBlockTitle[0]

                    if shaderBlockType not in ["insert"]:
                        self.error("Invalid block type:", shaderBlockType)

                    blockContent = shaderBlock[1:]  

                    # Detect inserts, and add them to the insert list
                    if shaderBlockType == "insert":
                        entryPoint = shaderBlockName.lstrip("@")
                        if entryPoint in inserts:
                            inserts[entryPoint] += blockContent
                        else:
                            inserts[entryPoint] = blockContent

                code = self._createShaderCode(parameters, inserts, blockName, partName)
                self.shaderParts[blockName][partName] = code

                if blockName == "Default":
                    defaultArgs[partName] = (parameters, inserts)

        # Fill all stages with values from the default stage, e.g. if there is 
        # no vertex code for EarlyZ defined, use the one from the default stage
        for blockName, parts in self.shaderParts.items():

            if len(parts) < 1:
                # if no parts are defined at all, skip this stage
                continue

            if blockName != "Default":
                # Fill stages with the values from the default shader
                for defaultPart in self.shaderParts["Default"]:
                    if defaultPart not in parts:
                        self.debug("Filling stage " + blockName + "." + defaultPart + " with values from default stage")
                        parameters, inserts = defaultArgs[defaultPart]
                        code = self._createShaderCode(parameters, inserts, blockName, defaultPart)
                        self.shaderParts[blockName][defaultPart] = code

