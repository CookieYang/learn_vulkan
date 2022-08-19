import sys
import maya.cmds as cmds
import maya.OpenMaya as OpenMaya
import maya.OpenMayaMPx as OpenMayaMPx
import math

kPluginCmdName = "optimize"


# Command
class scriptedCommand(OpenMayaMPx.MPxCommand):
    def __init__(self):
        OpenMayaMPx.MPxCommand.__init__(self)

    def getVertices(self, mesh):
        vertices = []
        vertexCount = cmds.polyEvaluate(mesh, v = True)
        for i in range(0, vertexCount):
            cmd1 = mesh + ".vt[" + str(i) + "]"
            cmd2 = mesh + ".pt[" + str(i) + "]"
            vert = cmds.getAttr(cmd1)
            offset = cmds.getAttr(cmd2)
            vertices.append(vert[0][0] + offset[0][0] ) #x
            vertices.append(vert[0][1] + offset[0][1] ) #y
            vertices.append(vert[0][2] + offset[0][2] ) #z
        return vertexCount, vertices

    def doMove(self, x, y, z, cmd):
        cmds.move(x , y , z , cmd, a = True, ls = True)

    def length(self, x0, y0, z0, x1, y1, z1):
        return math.sqrt((x0 - x1) * (x0 - x1) + (y0 - y1) * (y0 - y1) + (z0 - z1) * (z0 - z1))

    #remove deformation
    '''
    def doIt(self, argList):
        for name in nameList:
            print(name)
            for k in range(0, 47):
                print(k)
                c1, src = self.getVertices("|" + name + "_bs_0_" + str(k) + "|" + name + "_bs_0_" + str(k))
                for i in range(0, c1):
                    cmd = "|" + name + "_bs_5_" + str(k) + "|" + name + "_bs_5_" + str(k) + ".vtx[" + str(i) + "]"
                    self.doMove(src[i*3],src[i*3+1],src[i*3+2], cmd)
                    cmd = "|" + name + "_bs_6_" + str(k) + "|" + name + "_bs_6_" + str(k) + ".vtx[" + str(i) + "]"
                    self.doMove(src[i*3],src[i*3+1],src[i*3+2], cmd)
    '''

    # find data distribution
    def dataDistribution(self, prefix, bsCount, threshold):
        print(prefix)
        vertexCount, src0 = self.getVertices(prefix + "_0_0Shape")
        print(vertexCount)
        for k in range(1, bsCount + 1):
            print("col: ", k)
            c1, trg0 = self.getVertices("|" + prefix +"_0_" + str(k) + "|" + prefix + "_0_" + str(k))
            deltaList = [0] * 10
            t = threshold / 10.0
            for i in range(0, vertexCount):
                delta = self.length(src0[i*3], src0[i*3+1], src0[i*3+2], trg0[i*3],trg0[i*3+1],trg0[i*3+2])
                if delta < t:
                    deltaList[0] += 1
                elif delta < 2 * t:
                    deltaList[1] += 1
                elif delta < 3 * t:
                    deltaList[2] += 1
                elif delta < 4 * t:
                    deltaList[3] += 1
                elif delta < 5 * t:
                    deltaList[4] += 1
                elif delta < 6 * t:
                    deltaList[5] += 1
                elif delta < 7 * t:
                    deltaList[6] += 1
                elif delta < 8 * t:
                    deltaList[7] += 1
                elif delta < 9 * t:
                    deltaList[8] += 1
                else:
                    deltaList[9] += 1
            print(deltaList)

    # col optimize
    def colOptimize(self, prefix, bsCount, threshold):
        print(prefix)
        vertexCount, src0 = self.getVertices(prefix + "_0_0Shape")
        for k in range(1, bsCount + 1):
            print("col: ", k)
            c1, trg0 = self.getVertices("|" + prefix + "_0_" + str(k) + "|" + prefix + "_0_" + str(k))
            opCount = 0
            for i in range(0, vertexCount):
                if self.length(src0[i*3], src0[i*3+1], src0[i*3+2], trg0[i*3],trg0[i*3+1],trg0[i*3+2]) < threshold: #0.000001 or 0.02
                    cmd = "|" + prefix + "_0_" + str(k) + "|" + prefix + "_0_" + str(k) + ".vtx[" + str(i) + "]"
                    opCount += 1
                    self.doMove(src0[i*3],src0[i*3+1],src0[i*3+2], cmd)
            print(opCount)

    #row optimize
    def rowOptimize(self, prefix, endIndex, threshold):
        print(prefix)
        vertexCount, src0 = self.getVertices(prefix + "_0_0Shape")
        for k in range(1, endIndex + 1):
            print("row: ", k)
            c1, trg0 = self.getVertices("|" + prefix + "_" + str(k) + "_0" + "|" + prefix + "_" + str(k) + "_0")
            opCount = 0
            for i in range(0, vertexCount):
                if self.length(src0[i*3], src0[i*3+1], src0[i*3+2], trg0[i*3],trg0[i*3+1],trg0[i*3+2]) < threshold:         
                    cmd = "|" + prefix + "_"+ str(k) + "_0" + "|" + prefix + "_" + str(k) + "_0" + ".vtx[" + str(i) + "]"
                    opCount += 1
                    self.doMove(src0[i*3],src0[i*3+1],src0[i*3+2], cmd)
            print(opCount)

    # data optimize
    def contentOptimize(self, prefix, bsCount, startIndex, endIndex, threshold):
        print(prefix)
        vertexCount, src0 = self.getVertices(prefix + "_0_0Shape")
        for k in range(startIndex, endIndex + 1):
            print("row: ",k)
            c1, trg0 = self.getVertices("|" + prefix + "_" + str(k) + "_0|" + prefix + "_" + str(k) +"_0")
            for i in range(1, bsCount + 1):
                print(i)
                c0, src1 = self.getVertices("|" + prefix + "_0_" + str(i) + "|" + prefix + "_0_" + str(i))
                opCount = 0
                for j in range(0, vertexCount):
                    if self.length(src0[j*3], src0[j*3+1], src0[j*3+2], src1[j*3],src1[j*3+1],src1[j*3+2]) < threshold:
                        cmd = "|" + prefix + "_" + str(k) + "_" + str(i) + "|" + prefix + "_" + str(k) + "_" + str(i) + ".vtx[" + str(j) + "]"
                        opCount += 1
                        self.doMove(trg0[j*3],trg0[j*3+1],trg0[j*3+2], cmd)
                print(opCount)

    def doIt(self, argList):
        functionIndex, bsCount, startIndex, endIndex, prefix, threshold = self.parseArguments(argList)
        print("do operation")
        if functionIndex == 0:
            self.dataDistribution(prefix, bsCount, threshold)
        elif functionIndex == 1:
            self.colOptimize(prefix, bsCount, threshold)
        elif functionIndex == 2:
            self.rowOptimize(prefix, endIndex, threshold)
        elif functionIndex == 3:
            self.contentOptimize(prefix, bsCount, startIndex, endIndex, threshold)
        else:
            print("invaild function index")


    def parseArguments(self, args):
        ''' 
        The presence of this function is not enforced,
        but helps separate argument parsing code from other
        command code. 
        '''
        print("parseArguments")
        # The following MArgParser object allows you to check if specific flags are set.
        argData = OpenMaya.MArgParser( self.syntax(), args )
        threshold = 0.02
        startIndex = 0
        endIndex = 0
        pattern = ""
        functionIndex = 0
        bsCount = 0
        if argData.isFlagSet( "-f" ):
            functionIndex = argData.flagArgumentInt( "-f", 0 )

        if argData.isFlagSet( "-bc" ):
            bsCount = argData.flagArgumentInt( "-bc", 0 )

        if argData.isFlagSet( "-s" ):
            startIndex = argData.flagArgumentInt( "-s", 0 )

        if argData.isFlagSet( "-e" ):
            endIndex = argData.flagArgumentInt( "-e", 0 )

        if argData.isFlagSet( "-t" ):
            threshold = argData.flagArgumentDouble( "-t", 0 )
            
        if argData.isFlagSet( "-p" ):
            pattern = argData.flagArgumentString( "-p", 0 )
        print(functionIndex, bsCount, startIndex, endIndex, pattern, threshold)
        return functionIndex, bsCount, startIndex, endIndex, pattern, threshold


# Creator
def cmdCreator():
    return OpenMayaMPx.asMPxPtr( scriptedCommand() )

def syntaxCreator():
    ''' Defines the argument and flag syntax for this command. '''
    syntax = OpenMaya.MSyntax()
    
    # In this example, our flag will be expecting a numeric value, denoted by OpenMaya.MSyntax.kDouble. 
    syntax.addFlag( "-t", "-threshold", OpenMaya.MSyntax.kDouble )
    syntax.addFlag( "-bc", "-bsCount", OpenMaya.MSyntax.kUnsigned)
    syntax.addFlag( "-s", "-startIndex", OpenMaya.MSyntax.kUnsigned)
    syntax.addFlag( "-e", "-endIndex", OpenMaya.MSyntax.kUnsigned)
    syntax.addFlag( "-f", "-functionIndex", OpenMaya.MSyntax.kUnsigned)
    syntax.addFlag( "-p", "-pattern", OpenMaya.MSyntax.kString )
    # ... Add more flags here ...
        
    return syntax
    
# Initialize the script plug-in
def initializePlugin(mobject):
    mplugin = OpenMayaMPx.MFnPlugin(mobject)
    try:
        mplugin.registerCommand( kPluginCmdName, cmdCreator, syntaxCreator)
    except:
        print("Failed to register command")
        sys.stderr.write( "Failed to register command: %s\n" % kPluginCmdName )
        raise

# Uninitialize the script plug-in
def uninitializePlugin(mobject):
    mplugin = OpenMayaMPx.MFnPlugin(mobject)
    try:
        mplugin.deregisterCommand( kPluginCmdName )
    except:
        sys.stderr.write( "Failed to unregister command: %s\n" % kPluginCmdName )