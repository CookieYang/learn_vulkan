import sys
from ctypes import *
import os
import maya.cmds as cmds
import maya.OpenMaya as OpenMaya
import maya.OpenMayaMPx as OpenMayaMPx
import maya.utils as utils
import time
import re

##############################################################
#DAGTABLE
#head_0_0 head_0_1 head_0_2 head_0_3 ...
#head_1_0 
#head_2_0
#head_3_0
#.
#.
#.
###############################################################

digitPattern = r"[0-9]+"

VISION = "2.0.0"

sys.stdout = sys.__stdout__
dir(sys.stdout)

class StructAnchorInfo(Structure):
    _fields_ = [('indices', POINTER(c_uint)),
               ('length', c_int),
               ('row', c_int),
               ('col', c_int)]

class StructMeshInfo(Structure):
    _fields_ = [('vertexes', POINTER(c_float)),
               ('vertexCount', c_int),
               ('indices', POINTER(c_uint)),
               ('faceCount', c_int)]

class StructPairInfo(Structure):
    _fields_ = [('indices', POINTER(c_uint)),
               ('size', POINTER(c_uint)),
               ('sizeLength', c_int)]

CALCULATEFUNC = CFUNCTYPE(None, POINTER(c_float), c_int, c_int, c_int, c_int)
PREPROCESSFUNC = CFUNCTYPE(None, POINTER(c_uint), c_int, POINTER(c_uint), c_int, c_int)

class transfer():
    
    def __init__(self, anchors, faceIndices, lashIndices, browIndices, componentsInfo):
        self.bFirstUse = True
        self.running = False
        self.dagTable = None
        self.src0 = None
        self.pairInfo = None
        self.browInfo = None
        self.anchors = anchors
        self.faceIndices = faceIndices
        self.lashIndices = lashIndices
        self.browIndices = browIndices
        #print(componentsInfo)
        self.componentsInfo = componentsInfo
        self.componentVsize = componentsInfo.values()
        for key in self.componentsInfo.keys():
            self.componentsInfo[key] = []
        self.pairs = []
        self.browTri = []
        self.callback = CALCULATEFUNC(self.calculateCallback)
        self.pCallback = PREPROCESSFUNC(self.preprocessCallback)
        #self.targetsCount = 0
        if len(self.anchors) == 0:
            self.anchors.append(0)   
        self.transferMesh = None
        self.boundX = 0.0
        self.boundY = 0.0
        self.anchorInfo = None
        self.indexCount = 0
        self.width = 0
        self.targetRow = []
        self.widthSpace = 200
        self.heightSpace = 200
        CUR_PATH = os.getcwd()
        configPath = os.path.join(CUR_PATH,"config.cig")
        with open(configPath, 'r') as f:
            line = f.readline()
            parts = line.split()
            self.widthSpace = int(parts[0])
            self.heightSpace = int(parts[1])

    def setTargetRow(self, num):
        self.targetRow = num
    
    def getBlendshapeNames(self):
        selection = OpenMaya.MSelectionList()
        OpenMaya.MGlobal.getActiveSelectionList(selection)
        iterSel = OpenMaya.MItSelectionList(selection, OpenMaya.MFn.kShape)

        dagPath = OpenMaya.MDagPath()
        try:
            iterSel.getDagPath(dagPath)
        except:
            return None
        else:
            currentInMeshMFnMesh = OpenMaya.MFnMesh(dagPath)
            if currentInMeshMFnMesh:
               nodeList = cmds.listConnections(currentInMeshMFnMesh.name(), t = 'blendShape')
               # if t = 'transform', meshTransformNodeNames = None , I don't know why.
               meshTransformNodeNames = cmds.listConnections(nodeList[0], t = 'mesh')
               return meshTransformNodeNames
            else:
                return None

    def getVertices(self, mesh):
        vertices = []
        totalCount = 0
        for key in self.componentsInfo.keys():
            cmd = self.replaceName(mesh, key)
            #print(cmd)
            #print(mesh)
            transform = cmds.xform(self.getShortName(mesh), q = True, t = True)
            vertexCount = cmds.polyEvaluate(cmd, v = True)
            #if bori:
                #self.componentVsize.append(vertexCount)
            totalCount += vertexCount
            for i in range(0, vertexCount):
                cmd1 = cmd + ".vt[" + str(i) + "]"
                cmd2 = cmd + ".pt[" + str(i) + "]"
                vert = cmds.getAttr(cmd1)
                offset = cmds.getAttr(cmd2)
                vertices.append(vert[0][0] + offset[0][0] ) #x
                vertices.append(vert[0][1] + offset[0][1] ) #y
                vertices.append(vert[0][2] + offset[0][2] ) #z
            #print(cmd, "vertexCount: " + str(vertexCount))
        return totalCount, vertices

    def getIndices(self, mesh):
        indices = []
        offset = 0
        for j in range(0, len(self.componentsInfo.keys())):
            key = self.componentsInfo.keys()[j]
            cmd = self.replaceName(mesh, key)
            faceCount = cmds.polyEvaluate(cmd, f = True)
            for i in range(0, faceCount):
                selectcmd = cmd + ".f[" + str(i) + "]"
                cmds.select(selectcmd, r = True)
                vinds = cmds.polyInfo(fv = True)
                line = vinds[0]
                parts = line.split()
                faceIndex = parts[2:]
                indices.append(int(faceIndex[0]) + offset)
                indices.append(int(faceIndex[1]) + offset)
                indices.append(int(faceIndex[2]) + offset)
                if len(faceIndex) == 4: # deal with quadrilateral face(need test)
                    indices.append(int(faceIndex[0]) + offset)
                    indices.append(int(faceIndex[2]) + offset)
                    indices.append(int(faceIndex[3]) + offset)
            offset += self.componentVsize[j]
            #print(cmd, "faceCount: " + str(faceCount))
            '''
        for i in range(0, len(indices) / 3):
            index1 = indices[3 * i]
            index2 = indices[3 * i + 1]
            index3 = indices[3 * i + 2]
            print(index1, index2, index3)
            if(index1 == index2 or index1 == index3 or index2 == index3):
                print("error!!!", i)
                break
                '''
        return len(indices) / 3, indices

    def cloneOneMesh(self, source, target):
        for i in range(0, len(target)):
            t = target[i]
            s = self.replaceName(source, self.componentsInfo.keys()[i])
            newNames = cmds.duplicate(s, n = t)
            print(newNames)
            for name in newNames:
                if name != t:
                    cmds.rename(name, t)

    def parseIndex(self, name):
        parts = name.split("_")
        pattern = re.compile(digitPattern)
        col = re.match(pattern, parts[-1])
        return int(parts[-2]), int(col.group())

    def generateDAGTable(self):
        transformNodes = self.getBlendshapeNames()
        DAGPath = []
        if not transformNodes:
            meassge ="Error: please select blendshape mesh!!!"
            print(meassge)
        else:
            # parse row0 first
            rowLength = 0
            colLength = 0
            for node in transformNodes:
                nodename, nodeIndexGroup = self.splitName(node)
                indexParts = nodeIndexGroup.split("_")
                if int(indexParts[0]) == 0:
                    rowLength += 1
                elif int(indexParts[1]) == 0:
                    colLength += 1
            for i in range(0, len(transformNodes)):
                DAGPath.append(transformNodes[i] + '|' + cmds.listRelatives(transformNodes[i])[0])
            #print(DAGPath)
            if len(DAGPath) != (rowLength + colLength):
                self.bFirstUse = False
            self.indexCount += rowLength + colLength
            self.width = rowLength
            print(rowLength, colLength)
            # generate empty table
            self.dagTable = [[0] * (rowLength) for i in range(colLength + 1)]
            #print(colLength, rowLength)
            #self.targetsCount = (colLength * (rowLength + 1)) - len(DAGPath)
            for i in range(0, len(DAGPath)):
                print(DAGPath[i])
                row, col = self.parseIndex(DAGPath[i])
                #print(row, col)
                self.dagTable[row][col] = DAGPath[i] 
            
    def prepareCommonData(self):
        #print("Message: " + str(self.targetsCount) + " targets will be generated...")
        print("Message: prepare Data...")
        self.src0 = StructMeshInfo()
        print(self.dagTable[0][0])
        src0Vc, src0V =  self.getVertices(self.dagTable[0][0])
        src0Fc, src0I = self.getIndices(self.dagTable[0][0])
        self.src0.vertexes = (c_float * len(src0V))(*src0V)
        self.src0.vertexCount = src0Vc
        self.src0.indices = (c_uint * len(src0I))(*src0I)
        self.src0.faceCount = src0Fc
        #print(len(src0V), src0Vc, len(src0I), src0Fc)

        self.anchorInfo = StructAnchorInfo()
        self.anchorInfo.indices = (c_uint * len(self.anchors))(*self.anchors)
        self.anchorInfo.length = len(self.anchors)

        print("Message: current tool vision is " + VISION)
        CUR_PATH = os.getcwd()
        dllPath = os.path.join(CUR_PATH,"dtransfer.dll")
        pDll = cdll.LoadLibrary(dllPath)
        if not pDll:
            print("Error: dll not found, please check install doc!!!")
            return False

        vision = pDll.getVisionNumber
        vision.restype = c_voidp
        vision.argtypes = [POINTER(c_int),]
        v = [0] * 3
        v_c = (c_int * len(v))(*v)
        vision(v_c)
        v_str = ""
        for i in range(0, 3):
            v_str += str(v_c[i])
            v_str += str(".")
        print("Message: current dll vision is " + v_str[:-1])
        

        self.transferMesh = pDll.transferMesh
        self.transferMesh.argtypes = [POINTER(StructMeshInfo),POINTER(StructMeshInfo),POINTER(StructMeshInfo), CALCULATEFUNC, POINTER(StructAnchorInfo), POINTER(StructPairInfo),POINTER(StructPairInfo)]
        self.transferMesh.restype = c_voidp

        preprocess = pDll.preprocess
        preprocess.argtypes = [POINTER(StructMeshInfo),POINTER(StructPairInfo),POINTER(StructPairInfo),PREPROCESSFUNC]
        preprocess.restype = c_void_p

        lashInfo = StructPairInfo()
        pIndices = []
        pIndicesSize = []
        pIndicesLength = 1 + len(self.lashIndices)
        pIndices.extend(self.faceIndices)
        pIndicesSize.append(len(self.faceIndices))
        for part in self.lashIndices:
            pIndices.extend(part)
            pIndicesSize.append(len(part))
        lashInfo.indices = (c_uint * len(pIndices))(*pIndices)
        lashInfo.size = (c_uint * len(pIndicesSize))(*pIndicesSize)
        lashInfo.sizeLength = pIndicesLength
        print(len(pIndices), pIndicesSize, pIndicesLength)

        browInfo = StructPairInfo()
        bIndices = []
        bIndicesSize = []
        bIndicesSizeLength = len(self.browIndices)
        for brow in self.browIndices:
            bIndices.extend(brow)
            bIndicesSize.append(len(brow))
        browInfo.indices = (c_uint * len(bIndices))(*bIndices)
        browInfo.size = (c_uint * len(bIndicesSize))(*bIndicesSize)
        browInfo.sizeLength = bIndicesSizeLength
        print(len(bIndices), bIndicesSize, bIndicesSizeLength)

        preprocess(byref(self.src0), byref(lashInfo), byref(browInfo), self.pCallback)

        self.pairInfo = StructPairInfo()
        pairInfoIndices = []
        pairInfoSize = []
        pairInfoSizeLength = 1
        pairInfoIndices.extend(self.pairs)
        pairInfoSize.append(len(self.pairs) / 2)
        self.pairInfo.indices = (c_uint * len(pairInfoIndices))(*pairInfoIndices)
        self.pairInfo.size = (c_uint * len(pairInfoSize))(*pairInfoSize)
        self.pairInfo.sizeLength = pairInfoSizeLength

        self.browInfo = StructPairInfo()
        browInfoIndices = []
        browInfoSize = []
        browInfoSizeLength = 1
        browInfoIndices.extend(self.browTri)
        browInfoSize.append(len(self.browTri))
        self.browInfo.indices = (c_uint * len(browInfoIndices))(*browInfoIndices)
        self.browInfo.size = (c_uint * len(browInfoSize))(*browInfoSize)
        self.browInfo.sizeLength = browInfoSizeLength
        #self.browInfo.sizeLength = 0
        
        bounds = cmds.exactWorldBoundingBox(self.dagTable[0][0])
        self.boundX = abs(bounds[3] - bounds[0]) + 50
        self.boundY = abs(bounds[4] - bounds[1]) + 50


        for key in self.componentsInfo.keys():
            if len(self.componentsInfo[key]) == 0:
                cmd = self.replaceName(self.dagTable[0][0], key)
                bounds = cmds.exactWorldBoundingBox(cmd)
                self.componentsInfo[key].append(self.widthSpace)
                self.componentsInfo[key].append(self.heightSpace)
                self.componentsInfo[key].append(0.0)
        print("Message: prepare Data Success!!!")
        return True
        
    def getShortName(self, fullName):
        parts = fullName.split("|")
        if parts[0] == "":
            return "|" + parts[1]
        else:
            return "|" + parts[0]

    def moveObject(self, shortName):
        for key in self.componentsInfo.keys():
            name = self.replaceName(shortName, key, True)
            row, col = self.parseIndex(name)
            cmds.xform(name, t = (row * self.widthSpace, col * self.heightSpace, 0.0), r = True)


    def moveToOrign(self, shortName):
        for key, value in self.componentsInfo:
            name = self.replaceName(shortName, key, True)
            bounds = cmds.exactWorldBoundingBox(name + name)
            x = ((bounds[3] + bounds[0]) / 2)
            y = ((bounds[4] + bounds[1]) / 2)
            z = ((bounds[5] + bounds[2]) / 2)
            cmds.xform(name, t = (value[0] - x, value[1] - y, value[2] - z), r = True)

    def show(self, shortName):
        for key in self.componentsInfo.keys():
            name = self.replaceName(shortName, key, True)
            cmd = name + ".visibility"
            cmds.setAttr(cmd, 1)

    def createTargetNamebyIndex(self, row, col):
        shortName = []
        for key in self.componentsInfo:
            name, index = self.splitName(key)
            shortName.append(name + "_" + str(row) + "_" + str(col))
        return shortName 

    def splitName(self, name):
        parts = name.split("_")
        newname = ""
        newIndex = ""
        for i in range(0, len(parts) - 2):
            newname += parts[i]
            newname += "_"
        pattern = re.compile(digitPattern)
        col = re.match(pattern, parts[-1])
        newIndex = parts[-2] + "_" + col.group()
        return newname[:-1], newIndex

    def replaceName(self, oldName, newName, bshort = False):
        pureOldName = ""
        pureIndex = ""
        if not bshort:
            pureOldName, pureIndex = self.splitName(self.getShortName(oldName)[1:])
        else:
            pureOldName, pureIndex = self.splitName(oldName[1:])
        pureNewName, pureNewIndex = self.splitName(newName)
        s = oldName
        return s.replace(pureOldName, pureNewName)

    def generateOneRow(self, i):
        row = self.dagTable[i]
        print(row)
        for j in range(1, len(row)):
            if type(self.dagTable[i][j]) == int:
                self.generateOneBlendshape(i, j)
                
    def generateBlendshapes(self):
        if not self.running: # do once
            self.generateDAGTable() 
            if not self.prepareCommonData():
                return 

            if len(self.pairs) == 0:
                print("Warnning: no component connect finded")
                
            if self.bFirstUse:
                for i in range(0, len(self.dagTable)):
                    row = self.dagTable[i]
                    for j in range(0, len(row)):
                        if type(self.dagTable[i][j]) != int:
                            shortName = self.getShortName(self.dagTable[i][j])
                            self.moveObject(shortName)
                            if i != 0 or j != 0:
                                self.show(shortName)
            self.running = True
        print(self.targetRow)
        if len(self.targetRow) == 0:
            for i in range(1, len(self.dagTable)):
                self.generateOneRow(i) 
        else:
            for target in self.targetRow:
                if target >= len(self.dagTable) - 1:
                    target = len(self.dagTable) - 1
                self.generateOneRow(target)
                
    def generateOneBlendshape(self, i, j):
        row = self.dagTable[i][0]
        col = self.dagTable[0][j]
        shortName = self.createTargetNamebyIndex(i, j)
        print("Message: begin generate row: " + str(i) + ",col: " + str(j) + "...")
        src1 = StructMeshInfo()
        #print("Message: get " + row)
        src1Vc, src1V =  self.getVertices(row)
        src1Fc, src1I = self.getIndices(row)
        src1.vertexes = (c_float * len(src1V))(*src1V)
        src1.vertexCount = src1Vc
        src1.indices = (c_uint * len(src1I))(*src1I)
        src1.faceCount = src1Fc

        trg0 = StructMeshInfo()
        #print("Message: get " + col)
        trg0Vc, trg0V =  self.getVertices(col)
        trg0Fc, trg0I = self.getIndices(col)
        trg0.vertexes = (c_float * len(trg0V))(*trg0V)
        trg0.vertexCount = trg0Vc
        trg0.indices = (c_uint * len(trg0I))(*trg0I)
        trg0.faceCount = trg0Fc
        self.anchorInfo.row = i
        self.anchorInfo.col = j
        self.cloneOneMesh(row, shortName)
        self.transferMesh(byref(self.src0), byref(src1), byref(trg0), self.callback, byref(self.anchorInfo), byref(self.pairInfo), byref(self.browInfo))

    def preprocessCallback(self, lashPairs, lashPairsSize, browTris, browTrisSize, errorCode):
        if errorCode == 1:
            for i in range(0, lashPairsSize):
                self.pairs.append(lashPairs[2 * i])
                self.pairs.append(lashPairs[2 * i + 1])
            for i in range(0, browTrisSize):
                self.browTri.append(browTris[3 * i])
                self.browTri.append(browTris[3 * i + 1])
                self.browTri.append(browTris[3 * i + 2])
                print(browTris[3 * i], browTris[3 * i + 1], browTris[3 * i + 2])
            print("Message: preprocess success", len(self.pairs))
        else:
            print("Error: Preprocess failed, error code: " + str(errorCode))
            
    def calculateCallback(self, vertex, size, errorCode, row, col):
        shortName = self.createTargetNamebyIndex(row, col)
        if errorCode == 1: #no error occurred
            # replace vertex positions
            offset = 0
            for i in range(0, len(shortName)):
                shortName[i] = "|" + shortName[i]
                doShow(shortName[i])
                fullName =  shortName[i] + shortName[i]
                for j in range(0, self.componentVsize[i]):
                    cmd = fullName + ".vtx[" + str(j) + "]"
                    utils.executeInMainThreadWithResult(doMove, vertex[3 * (j + offset)] , vertex[3 * (j + offset) + 1] , vertex[3 * (j + offset) + 2 ]  , cmd)
                offset += self.componentVsize[i]
                print(self.dagTable[0][0], shortName[i][1:])
                bsShortName = self.replaceName(self.dagTable[0][0], shortName[i])
                doBlendshape(bsShortName, self.indexCount + row * self.width + col + 50, shortName[i])
                #moveOriDeferred(shortName[i], self.componentsInfo.values()[i][0], self.componentsInfo.values()[i][1], self.componentsInfo.values()[i][2])
                #print("Move Y: " + str(self.heightSpace))
                moveObjDeferred(shortName[i], row, col, self.widthSpace, self.heightSpace)
            #self.targetsCount -= 1
            print(shortName[0] + " has been finished.")
            self.dagTable[row][col] = "finished"
        elif errorCode == -1:
            print("Error: " + shortName[0] + " failed," + "nan or inf in input")
        elif errorCode == -2:
            print("Error: " + shortName[0] + " failed," + "illegal or trivial triangles")
        elif errorCode == -3:
            print("Error: " + shortName[0] + " failed," + "nan or inf in E1Mat")
        elif errorCode == -4:
            print("Error: " + shortName[0] + " failed," + "not initialized when transfer")
        elif errorCode == -5:
            print("Error: " + shortName[0] + " failed," + "vertex size not matched")
        elif errorCode == -6:
            print("Error: " + shortName[0] + " failed," + "nan or inf in srcVertsDeformed")
        elif errorCode == -7:
            print("Error: " + shortName[0] + " failed," + "nan or inf in result")
        elif errorCode == -8:
            print("Error: load auth bundle failed!!!")
        elif errorCode == -9:
            print("Error: auth failed!!!")
        else:
            print("Error: " + shortName[0] + " failed, code " + str(errorCode))
            
def moveOriDeferred(shortName, orignX, orignY, orignZ):
    bounds = cmds.exactWorldBoundingBox(shortName + shortName)
    x = ((bounds[3] + bounds[0]) / 2)
    y = ((bounds[4] + bounds[1]) / 2)
    z = ((bounds[5] + bounds[2]) / 2)
    cmds.xform(shortName, t = (orignX - x, orignY - y, orignZ - z), r = True)

def moveObjDeferred(shortName, row, col, boundX, boundY):
    cmds.xform(shortName, t = (row * boundX, col * boundY, 0.0), r = True)

def doShow(name):
    cmd = name + ".visibility"
    cmds.setAttr(cmd, 1)

def doMove(x, y, z, cmd):
    cmds.move(x , y , z , cmd, a = True, ls = True)

def doBlendshape(bsName, index, shortName):
    print("add " + shortName + " to Blendshape")
    cmds.blendShape(bsName, edit=True, t=(bsName, index, shortName, 1.0))
