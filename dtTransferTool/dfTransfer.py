import sys
import maya.OpenMaya as OpenMaya
import maya.OpenMayaMPx as OpenMayaMPx
import TransferFunc.MeshDeformerUI as meshUI

kPluginCmdName = "MeshDeformer"

# Command
class scriptedCommand(OpenMayaMPx.MPxCommand):
    def __init__(self):
        OpenMayaMPx.MPxCommand.__init__(self)
        
    def doIt(self,argList):
        meshUI.mayaRun()

# Creator
def cmdCreator():
    return OpenMayaMPx.asMPxPtr( scriptedCommand() )
    
# Initialize the script plug-in
def initializePlugin(mobject):
    mplugin = OpenMayaMPx.MFnPlugin(mobject)
    try:
        mplugin.registerCommand( kPluginCmdName, cmdCreator )
    except:
        sys.stderr.write( "Failed to register command: %s\n" % kPluginCmdName )
        raise

# Uninitialize the script plug-in
def uninitializePlugin(mobject):
    mplugin = OpenMayaMPx.MFnPlugin(mobject)
    try:
        mplugin.deregisterCommand( kPluginCmdName )
    except:
        sys.stderr.write( "Failed to unregister command: %s\n" % kPluginCmdName )