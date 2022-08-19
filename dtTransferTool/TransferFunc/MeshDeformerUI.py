from PySide import QtGui, QtCore			# PySide
import shiboken								# PySide

import pysideuic							#Pyside
import xml.etree.ElementTree as xml			#Pyside
from cStringIO import StringIO				#Pyside

from PySide.QtCore import Slot, QMetaObject, Qt
from PySide.QtUiTools import QUiLoader
from PySide.QtGui import QApplication, QMainWindow, QMessageBox
import cPickle

import TransferFunc.TransferFun as tf


import maya.cmds as cmds
import maya.OpenMayaUI as mui
import os, sys

sys.stdout = sys.__stdout__
dir(sys.stdout)

windowObject = "TimeManip"

################################################################
#how to record components?
#[componentName, Type, []]
#Type: 0-face, only face 1-lash like 2-brow like  []:component indices


def wrapinstance(ptr, base=None):
    """
    Utility to convert a pointer to a Qt class instance (PySide/PyQt compatible)

    :param ptr: Pointer to QObject in memory
    :type ptr: long or Swig instance
    :param base: (Optional) Base class to wrap with (Defaults to QObject, which should handle anything)
    :type base: QtGui.QWidget
    :return: QWidget or subclass instance
    :rtype: QtGui.QWidget
    """
    if ptr is None:
        return None
    ptr = long(ptr) #Ensure type
    if globals().has_key('shiboken'):
        if base is None:
            qObj = shiboken.wrapInstance(long(ptr), QtCore.QObject)
            metaObj = qObj.metaObject()
            cls = metaObj.className()
            superCls = metaObj.superClass().className()
            if hasattr(QtGui, cls):
                base = getattr(QtGui, cls)
            elif hasattr(QtGui, superCls):
                base = getattr(QtGui, superCls)
            else:
                base = QtGui.QWidget
        return shiboken.wrapInstance(long(ptr), base)
    elif globals().has_key('sip'):
        base = QtCore.QObject
        return sip.wrapinstance(long(ptr), base)
    else:
        return None


def getMainWindow():

    pointer = mui.MQtUtil.mainWindow()
    
    return wrapinstance(long( pointer ), QtGui.QWidget )   # Works with both PyQt and PySide


class DFWindow(QtGui.QMainWindow):

    def __init__(self, parent=getMainWindow()):
        '''
        Initialize the window.
        '''
        super(DFWindow, self).__init__(parent)

        #self.w = QtGui.QWidget()

        #self.setCentralWidget(self.w)

        self.anchorList = []

        self.componentsInfo = []

        self.componentName = {}

        self.tfo = None
        
        #Window title
        self.setObjectName(windowObject)
        self.setWindowTitle('Deformation Transfer Tool')
        self.resize(300, 200)

        w = QtGui.QWidget()

        self.setCentralWidget(w)

        self.running = False
        
        ########################################################################
        #Create Widgets
        ########################################################################

        #: A button for when the user is ready to create the new shape.
        self.selectButton = QtGui.QPushButton("Select Mode ", parent=self)

        self.addComponentButton = QtGui.QPushButton("Add Component", parent = self)

        self.addAnchorButton = QtGui.QPushButton("Add Anchor", parent = self)

        self.addLashButton = QtGui.QPushButton("Add Connection", parent = self)

        #self.addBrowButton = QtGui.QPushButton("Add Relation", parent = self)

        self.tansferButton = QtGui.QPushButton("Generate blendshape", parent = self)


        #: A descriptive label for letting the user know what his current settings
        #: will do.
        self.textBox = QtGui.QLineEdit(self)
        self.textBox.resize(100, 50)

        
        self.connect(self.selectButton, QtCore.SIGNAL("clicked()"), self.beginSelectVertex)

        self.connect(self.addComponentButton, QtCore.SIGNAL("clicked()"), self.addComponent)

        self.connect(self.addAnchorButton, QtCore.SIGNAL("clicked()"), self.addAnchor)

        self.connect(self.addLashButton, QtCore.SIGNAL("clicked()"), self.addLash)

        #self.connect(self.addBrowButton, QtCore.SIGNAL("clicked()"), self.addBrow)

        self.connect(self.tansferButton, QtCore.SIGNAL("clicked()"), self.generateBlendshape)

        
        ########################################################################
        #Layout the widgets
        ########################################################################
        actionLayout1 = QtGui.QBoxLayout(QtGui.QBoxLayout.LeftToRight)
        actionLayout1.addWidget(self.selectButton)
        actionLayout1.addWidget(self.addComponentButton)
        

        actionLayout2 = QtGui.QBoxLayout(QtGui.QBoxLayout.LeftToRight)
        actionLayout2.addWidget(self.addAnchorButton)
        actionLayout2.addWidget(self.addLashButton)
        #actionLayout2.addWidget(self.addBrowButton)

        actionLayout3 = QtGui.QBoxLayout(QtGui.QBoxLayout.LeftToRight)
        actionLayout3.addWidget(self.textBox)
        actionLayout3.addWidget(self.tansferButton)
        
        layout = QtGui.QBoxLayout(QtGui.QBoxLayout.TopToBottom, self)
        layout.addLayout(actionLayout1)
        layout.addLayout(actionLayout2)
        layout.addLayout(actionLayout3)

        w.setLayout(layout)
        
    def addComponent(self):
        allComponents = cmds.ls( sl=True )
        index = 0
        commandPrefix = ""
        if len(allComponents) > 0 :
            component = allComponents[0]
            commandPrefix = component.split(".")[0]
            parts = component.split('.')
            if len(parts) == 2:
                s = parts[1]
                if 'vtx' in s:
                    vtxParts = s.split('[')
                    index = vtxParts[1][:-1]
                
        #get face indices
        faceIndices, faceHardIndices = self.getComponentsIndex(commandPrefix, index)
        print("Message: Component indices count: " + str(len(faceIndices)))
        componentList = []
        componentList.append(commandPrefix)
        componentList.append(0)
        componentList.append(faceIndices)
        self.componentsInfo.append(componentList)

    def addAnchor(self):
        allComponents = cmds.ls( sl=True )
        commandPrefix = ""
        if len(allComponents) > 0 :
            component = allComponents[0]
            commandPrefix = component.split(".")[0]
            parts = component.split('.')
            if len(parts) == 2:
                s = parts[1]
                if 'vtx' in s:
                    vtxParts = s.split('[')
                    index = vtxParts[1][:-1]
                    anchorInfo = []
                    anchorInfo.append(commandPrefix)
                    anchorInfo.append(int(index))
                    self.anchorList.append(anchorInfo)
                    print("Message: anchor index: " + str(index))

    def addLash(self):
        allComponents = cmds.ls( sl=True )
        commandPrefix = ""
        if len(allComponents) > 0 :
            component = allComponents[0]
            commandPrefix = component.split(".")[0]
            parts = component.split('.')
            if len(parts) == 2:
                s = parts[1]
                if 'vtx' in s:
                    vtxParts = s.split('[')
                    index = vtxParts[1][:-1]
                    indices, hardIndices = self.getComponentsIndex(commandPrefix,int(index))
                    componentList = []
                    componentList.append(commandPrefix)
                    componentList.append(1)
                    componentList.append(indices)
                    self.componentsInfo.append(componentList)
                    print("Message: Lash Indices ", indices)
    
    def addBrow(self):
        allComponents = cmds.ls( sl=True )
        commandPrefix = ""
        if len(allComponents) > 0 :
            component = allComponents[0]
            commandPrefix = component.split(".")[0]
            parts = component.split('.')
            if len(parts) == 2:
                s = parts[1]
                if 'vtx' in s:
                    vtxParts = s.split('[')
                    index = vtxParts[1][:-1]
                    indices, hardIndices = self.getComponentsIndex(commandPrefix,int(index))
                    componentList = []
                    componentList.append(commandPrefix)
                    componentList.append(2)
                    componentList.append(indices)
                    self.componentsInfo.append(componentList)
                    print("Message: Brow Indices ", indices)

    def getComponentsIndex(self, commandPrefiex, initialIndex):
        selectedVertex = []
        stack = []
        hardVertex = []
        stack.append(initialIndex)
        while len(stack) != 0:
            self.foundAdjusetVertex(commandPrefiex, selectedVertex, stack, hardVertex)
        return selectedVertex, hardVertex

    def commmandToIndex(self, command):
        parts = command.split("[")
        return int(parts[1][:-1])
            
    def foundAdjusetVertex(self,  commandPrefix, selectedVertex, stack, hardVertex):
        v = stack.pop()
        command = commandPrefix + ".vtx[" + str(v) + "]"
        edges = cmds.polyInfo(command, ve = True)
        pedges = edges[0].split()[2:]
        for edge in pedges:
            ecmd = commandPrefix + ".e[" + edge + "]"
            vertexes = cmds.polyInfo(ecmd, ev = True)
            pvertex = vertexes[0].split()
            if "Hard" == pvertex[-1]:
                pvertex = pvertex[2:-1]
                for vertex in pvertex:
                    v = int(vertex)
                    if v not in selectedVertex:
                        stack.append(v)
                        selectedVertex.append(v)
                    if v not in hardVertex:
                        hardVertex.append(v)
            else:
                pvertex = pvertex[2:]
                for vertex in pvertex:
                    v = int(vertex)
                    if v not in selectedVertex:
                        stack.append(v)
                        selectedVertex.append(v)


    def CalculateComponentIndex(self):
        for item in self.componentsInfo:
            if item[0] in self.componentName.keys():
                pass
            else:
                self.componentName[item[0]] = cmds.polyEvaluate(item[0], v = True)
        size = 0
        added = []
        for key, value in self.componentName.items():
            added.append(key)
            size = value
            for item in self.componentsInfo:
                if item[0] not in added:
                    for i in range(0, len(item[2])):
                        item[2][i] += size
            for item in self.anchorList:
                if item[0] not in added:
                    item[1] += size
        
    def MergeComponents(self):
        faceIndices = []
        lashIndices = []
        browIndices = []
        for item in self.componentsInfo:
            if item[1] == 0:
                faceIndices.extend(item[2])
            elif item[1] == 1:
                lashIndices.append(item[2])
            else:
                browIndices.append(item[2])
        return faceIndices, lashIndices, browIndices

    def innnerGenerate(self, num):
        if self.running == False:
            cmds.selectMode(object = True)
            cmds.selectType(smp = False, sme = False, smf = False, smu = False, pv = False, pe = False, pf = False, puv = False)
            self.CalculateComponentIndex()
            faceIndices, lashIndices, browIndices = self.MergeComponents()
            anchors = []
            for item in self.anchorList:
                anchors.append(item[1])
            self.tfo = tf.transfer(anchors, faceIndices, lashIndices, browIndices, self.componentName)
            self.running = True
        print("Message: begin generate blendshape...")
        self.tfo.setTargetRow(num)
        self.tfo.generateBlendshapes()
                 
    def generateBlendshape(self):
        textboxValue = self.textBox.text()
        target = []
        if textboxValue == '':
            self.innnerGenerate(target)
        elif ':' in textboxValue:
            parts = textboxValue.split(':')
            for i in range(int(parts[0]), int(parts[1]) + 1):
                target.append(i)
            self.innnerGenerate(target)
        else:
            num = int(textboxValue)
            if num:
                if num <= 1:
                    target.append(1)
                    self.innnerGenerate(target)
                else:
                    target.append(num)
                    self.innnerGenerate(target)
            else:
                print("Error: invaild input")
        
    def beginSelectVertex(self):
        #selectType -smp 1 -sme 0 -smf 0 -smu 0 -pv 1 -pe 0 -pf 0 -puv 0;
        cmds.selectMode(component = True)
        cmds.selectType(smp = True, sme = False, smf = False, smu = False, pv = True, pe = False, pf = False, puv = False)
        print("Message: please select anchor points")
        
def mayaRun():
    if cmds.window(windowObject, q=True, exists=True):
        cmds.deleteUI(windowObject)    
    
    global gui  
    gui = DFWindow()  
    gui.show()

mayaRun()