from Code.AutoGenerated.DayProperty import DayProperty

from Code.DebugObject import DebugObject
from direct.stdpy.file import open, isfile


class TimeOfDay(DebugObject):
    """ This class manages the time of day settings. It has a list of all
    available properties and can interpolate between them """

    def __init__(self):
        """ Creates a new time of day instance. Remember to call load() before
        using this instance """
        DebugObject.__init__(self, "TimeOfDay")
        self._createProperties()

    def _createProperties(self):
        """ Internal method to populate the property list """
        self.properties = {}
        self.propertiesOrdered = []
        self.categories = {
            'sun': 'Sun',
            'lighting': 'Lighting',
            'fog': 'Fog'
        }

        def addEntry(eid, prop):
            self.properties[eid] = prop
            self.propertiesOrdered.append(eid)

        addEntry('sun.angle', DayProperty("Angle", "float", 0.0, 360.0, 0.0, """
            Sun direction in degrees"""))

        addEntry('sun.height', DayProperty("Height", "float", 0.0, 1.0, 0.5, """
            Sun height relative to the planet"""))

        addEntry('lighting.exposure', DayProperty("Exposure", "float", 0.0, 2.0, 1.0, """
            HDR Factor"""))

        addEntry('fog.start', DayProperty("Start", "float", 0.0, 1000.0, 500.0, """
            Where the fog starts, in world-space units"""))

        addEntry('fog.end', DayProperty("End", "float", 0.0, 20000.0, 9000.0, """
             Where the fog ends, in world-space units"""))

    def getProperties(self):
        """ Returns all properties """
        return self.properties

    def bindTo(self, node, uniformName):
        """ Binds the shader inputs to a node. This only has to be done once """

        for propid, prop in self.properties.items():
            name = propid.replace(".", "_")
            node.setShaderInput(name, prop.getPTA())

    def update(self, timestamp):
        """ Updates all shader inputs. timestamp should be between 0 and 1 and
        represents the time of the day, so 0 means 0:00 and 1.0 means 24:00 """

        if timestamp < 0.0 or timestamp > 1.0:
            self.warn("Invalid timestamp:", timestamp)

        for prop in self.properties.values():
            val = prop.getInterpolatedValue(timestamp)
            prop.getPTA()[0] = val

    def getPropertyKeys(self):
        """ Returns all property keys, ordered """
        return self.propertiesOrdered

    def getProperty(self, prop):
        """ Returns a property by id """
        return self.properties[prop]

    def load(self, filename):
        """ Loads the property values from <filename> """

        self.debug("Loading from", filename)

        if not isfile(filename):
            self.error("Could not load", filename)
            return False

        with open(filename, "r") as handle:
            content = handle.readlines()

        for line in content:
            line = line.strip()
            if len(line) < 1 or line.startswith("#"):
                continue
            parts = line.split()

            if len(parts) != 2:
                self.warn("Invalid line:", line)
                continue

            propId = parts[0]
            propData = parts[1]

            if propId not in self.properties:
                self.warn("Invalid ID:", propId)
                continue

            prop = self.properties[propId]

            if not (propData.startswith("[") and propData.endswith("]")):
                self.warn("Invalid data:", propData)

            propData = propData[1:-1].split(";")
            propData = [prop.propType.convertString(i) for i in propData]

            if len(propData) != 8:
                self.warn("Data count does not match for", propId)
                continue

            prop.values = propData
            prop.recompute()

    def save(self, dest):
        """ Writes the default property file to a given location """
        output = "# Autogenerated by Time of Day Manager\n"
        output += "# Do not edit! Your changes will be lost.\n"

        for propid, prop in self.properties.items():
            output += propid + \
                      " [" + ";".join([str(i) for i in prop.values]) + "]\n"

        with open(dest, "w") as handle:
            handle.write(output)

    def saveGlslInclude(self, dest):
        """ Writes the GLSL structure representation to a given location """
        output = "// Autogenerated by Time of Day Manager\n"
        output += "// Do not edit! Your changes will be lost.\n\n\n"

        output += "struct TimeOfDay {\n\n"

        for propid, prop in self.properties.items():
            name = propid.replace(".", "_")
            output += "    // " + prop.description + "\n"
            output += "    " + \
                      prop.propType.getGlslType() + " " + name + ";\n\n"

        output += "};\n\n\n"

        with open(dest, "w") as handle:
            handle.write(output)
