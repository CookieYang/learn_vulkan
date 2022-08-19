import sys

import maya.api.OpenMaya as OpenMaya
import maya.cmds as cmds
# ... additional imports here ...

kPluginCmdName = 'Rename'

def maya_useNewAPI():
	"""
	The presence of this function tells Maya that the plugin produces, and
	expects to be passed, objects created using the Maya Python API 2.0.
	"""
	pass
	
##########################################################
# Plug-in 
##########################################################
class MyCommandWithFlagClass( OpenMaya.MPxCommand ):
    
    def __init__(self):
        ''' Constructor. '''
        OpenMaya.MPxCommand.__init__(self)
    
    def doIt(self, args):
        ''' Command execution. '''
        
        # We recommend parsing your arguments first.
        direction, startIndex, pattern = self.parseArguments(args)
        selected_items = cmds.ls(selection=True)
        if selected_items:
            for i in range(0, len(selected_items)):
                item = selected_items[i]
                if direction:
                    newName = pattern + "_" + str(i + startIndex) + "_0"
                    cmds.rename(item, newName)
                    shape = cmds.listRelatives("|" + newName, shapes=True)
                    cmds.rename("|" + newName + "|" + shape[0],  newName)
                else:
                    newName = pattern + "_" + "0_" + str(i + startIndex)
                    cmds.rename(item, newName)
                    shape = cmds.listRelatives("|" + newName, shapes=True)
                    cmds.rename("|" + newName + "|" + shape[0],  newName)
            
        

        
    
    def parseArguments(self, args):
        ''' 
        The presence of this function is not enforced,
        but helps separate argument parsing code from other
        command code. 
        '''
        
        # The following MArgParser object allows you to check if specific flags are set.
        argData = OpenMaya.MArgParser( self.syntax(), args )
        direction = False
        startIndex = 0
        pattern = ""
        if argData.isFlagSet( "-d" ):
            direction = argData.flagArgumentBool( "-d", 0 )
            
        if argData.isFlagSet( "-s" ):
            startIndex = argData.flagArgumentInt( "-s", 0 )

        if argData.isFlagSet( "-p" ):
            pattern = argData.flagArgumentString( "-p", 0 )

        return direction, startIndex, pattern
            
        
        # ... If there are more flags, process them here ...

##########################################################
# Plug-in initialization.
##########################################################
def cmdCreator():
    ''' Create an instance of our command. '''
    return MyCommandWithFlagClass() 

def syntaxCreator():
    ''' Defines the argument and flag syntax for this command. '''
    syntax = OpenMaya.MSyntax()
    
    # In this example, our flag will be expecting a numeric value, denoted by OpenMaya.MSyntax.kDouble. 
    syntax.addFlag( "-d", "-direction", OpenMaya.MSyntax.kBoolean )
    syntax.addFlag( "-s", "-startIndex", OpenMaya.MSyntax.kUnsigned)
    syntax.addFlag( "-p", "-pattern", OpenMaya.MSyntax.kString )
    # ... Add more flags here ...
        
    return syntax
    
def initializePlugin( mobject ):
    ''' Initialize the plug-in when Maya loads it. '''
    mplugin = OpenMaya.MFnPlugin( mobject )
    try:
        mplugin.registerCommand( kPluginCmdName, cmdCreator, syntaxCreator )
    except:
        sys.stderr.write( 'Failed to register command: ' + kPluginCmdName )

def uninitializePlugin( mobject ):
    ''' Uninitialize the plug-in when Maya un-loads it. '''
    mplugin = OpenMaya.MFnPlugin( mobject )
    try:
        mplugin.deregisterCommand( kPluginCmdName )
    except:
        sys.stderr.write( 'Failed to unregister command: ' + kPluginCmdName )

##########################################################
# Sample usage.
##########################################################
''' 
# Copy the following lines and run them in Maya's Python Script Editor:

import maya.cmds as cmds
cmds.Rename( d = 0, s = 10, p = "Head_bs")

'''