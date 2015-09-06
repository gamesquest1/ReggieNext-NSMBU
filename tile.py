#!/usr/bin/python
# -*- coding: latin-1 -*-

# Reggie! - New Super Mario Bros. U Level Editor
# data here
# Copyright (C) 2009-2015 Treeki, Tempus, angelsl, JasonP27, Kamek64, 
# MalStar1000, RoadrunnerWMC, MrRean

# This file is part of Reggie!.

# Reggie! is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Reggie! is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Reggie!.  If not, see <http://www.gnu.org/licenses/>.


# tile.py
# settings for tilesets and tileset objects


################################################################
################################################################

import reggie
import level
import threading
from PyQt5 import QtCore, QtGui, QtWidgets # if reggie.py has it, this should have it
import SARC as SarcLib
import spritelib as SLib

Qt = QtCore.Qt

TileWidth = 60

Tiles = None # 0x200 tiles per tileset, plus 64 for each type of override
TilesetFilesLoaded = [None, None, None, None]
TilesetAnimTimer = None
TilesetCache = {} # Tileset cache, to avoid reloading when possible
TilesetCompletelyCached = {}
TileThreads = [None, None, None, None] # holds tileset-rendering threads
TileBehaviours = None
ObjectDefinitions = None # 4 tilesets
TilesetsAnimating = False

class StoppableThread(threading.Thread):
    """
    Thread class with a stop() method. The thread itself has to check
    regularly for the stopped() condition.
    http://stackoverflow.com/a/325528
    """

    def __init__(self):
        super(StoppableThread, self).__init__()
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.isSet()


class ProgressiveTilesetRenderingThread(StoppableThread):
    """
    Thread that renders tilesets progressively.
    It's a StoppableThread which allows the operation
    to be killed (say, when the user opens a new level
    before the current level's tilesets are finished
    rendering).
    """
    @staticmethod
    def getTileFromImage(tilemap, xtilenum, ytilenum):
        return tilemap.copy((xtilenum * 64) + 2, (ytilenum * 64) + 2, 60, 60)

    def setStuff(self, comptiledata, tilesetIdx, tileoffset, name):
        """
        Sets settings that the thread will use
        """
        self.comptiledata = comptiledata
        self.tilesetIdx = tilesetIdx
        self.tileoffset = tileoffset
        self.tilesetname = name
        self.name = name # thread name

    def run(self):
        """
        Renders tilesets progressively.
        """
        TilesetCompletelyCached[self.tilesetname] = False

        for image in gtx.renderGTX(gtx.loadGTX(self.comptiledata)):

            if self.stopped(): return

            pix = QtGui.QPixmap.fromImage(image)
            sourcex = 0
            sourcey = 0
            for i in range(self.tileoffset, self.tileoffset + 256):
                if Tiles[i] is not None:
                    Tiles[i].setMain(self.getTileFromImage(pix, sourcex, sourcey))
                sourcex += 1
                if sourcex >= 32:
                    sourcex = 0
                    sourcey += 1

            mainWindow.scene.update()
            mainWindow.objPicker.LoadFromTilesets()

            if self.stopped(): return

        ProcessOverrides(self.tilesetIdx, self.tilesetname)

        TilesetCompletelyCached[self.tilesetname] = True

class TilesetTile():
    """
    Class that represents a single tile in a tileset
    """
    def __init__(self, main):
        """
        Initializes the TilesetTile
        """
        self.main = main
        self.isAnimated = False
        self.animFrame = 0
        self.animTiles = []
        self.collData = ()
        self.collOverlay = None
        self.depthMap = None

    def setMain(self, main):
        """
        Sets self.main
        """
        self.main = main

    def addAnimationData(self, data):
        """
        Applies Newer-style animation data to the tile
        """
        animTiles = []
        numberOfFrames = len(data) // 2048
        for frame in range(numberOfFrames):
            framedata = data[frame*2048: (frame*2048)+2048]
            decoder = TPLLib.decoder(TPLLib.RGB4A3)
            decoder = decoder(framedata, 32, 32)
            newdata = decoder.run()
            img = QtGui.QImage(newdata, 32, 32, 128, QtGui.QImage.Format_ARGB32)
            pix = QtGui.QPixmap.fromImage(img.copy(0, 0, 31, 31).scaledToHeight(TileWidth, Qt.SmoothTransformation))
            animTiles.append(pix)
        self.animTiles = animTiles
        self.isAnimated = True

    def nextFrame(self):
        """
        Increments to the next frame
        """
        if not self.isAnimated: return
        self.animFrame += 1
        if self.animFrame == len(self.animTiles):
            self.animFrame = 0

    def resetAnimation(self):
        """
        Resets the animation frame
        """
        self.animFrame = 0

    def getCurrentTile(self):
        """
        Returns the current tile based on the current animation frame
        """
        result = None
        if (not TilesetsAnimating) or (not self.isAnimated): result = self.main
        else: result = self.animTiles[self.animFrame]
        result = QtGui.QPixmap(result)

        p = QtGui.QPainter(result)
        if CollisionsShown and (self.collOverlay is not None):
            p.drawPixmap(0, 0, self.collOverlay)
        if DepthShown and (self.depthMap is not None):
            p.drawPixmap(0, 0, self.depthMap)
        del p

        return result

    def setCollisions(self, colldata):
        """
        Sets the collision data for this tile
        """
        self.collData = tuple(colldata)
        self.updateCollisionOverlay()

    def setQuestionCollisions(self):
        """
        Sets the collision data to that of a question block
        """
        self.setCollisions((0,0,0,5,0,0,0,0))

    def setBrickCollisions(self):
        """
        Sets the collision data to that of a brick block
        """
        self.setCollisions((0,0,0,0x10,0,0,0,0))

    def updateCollisionOverlay(self):
        """
        Updates the collisions overlay for this pixmap
        """
        # This is completely stolen from Puzzle. Only minor
        # changes have been made. Thanks, Treeki!
        CD = self.collData
        if CD[2] & 16:      # Red
            color = QtGui.QColor(255, 0, 0, 120)
        elif CD[5] == 1:    # Ice
            color = QtGui.QColor(0, 0, 255, 120)
        elif CD[5] == 2:    # Snow
            color = QtGui.QColor(0, 0, 255, 120)
        elif CD[5] == 3:    # Quicksand
            color = QtGui.QColor(128,64,0, 120)
        elif CD[5] == 4:    # Conveyor
            color = QtGui.QColor(128,128,128, 120)
        elif CD[5] == 5:    # Conveyor
            color = QtGui.QColor(128,128,128, 120)
        elif CD[5] == 6:    # Rope
            color = QtGui.QColor(128,0,255, 120)
        elif CD[5] == 7:    # Half Spike
            color = QtGui.QColor(128,0,255, 120)
        elif CD[5] == 8:    # Ledge
            color = QtGui.QColor(128,0,255, 120)
        elif CD[5] == 9:    # Ladder
            color = QtGui.QColor(128,0,255, 120)
        elif CD[5] == 10:   # Staircase
            color = QtGui.QColor(255, 0, 0, 120)
        elif CD[5] == 11:   # Carpet
            color = QtGui.QColor(255, 0, 0, 120)
        elif CD[5] == 12:   # Dust
            color = QtGui.QColor(128,64,0, 120)
        elif CD[5] == 13:   # Grass
            color = QtGui.QColor(0, 255, 0, 120)
        elif CD[5] == 14:   # Unknown
            color = QtGui.QColor(255, 0, 0, 120)
        elif CD[5] == 15:   # Beach Sand
            color = QtGui.QColor(128, 64, 0, 120)
        else:               # Brown?
            color = QtGui.QColor(64, 30, 0, 120)


        # Sets Brush style for fills
        if CD[2] & 4:        # Climbing Grid
            style = Qt.DiagCrossPattern
        elif (CD[3] & 16) or (CD[3] & 4) or (CD[3] & 8): # Breakable
            style = Qt.Dense5Pattern
        else:
            style = Qt.SolidPattern

        brush = QtGui.QBrush(color, style)
        pen = QtGui.QPen(QtGui.QColor(0,0,0,128))
        collPix = QtGui.QPixmap(TileWidth, TileWidth)
        collPix.fill(QtGui.QColor(0,0,0,0))
        painter = QtGui.QPainter(collPix)
        painter.setBrush(brush)
        painter.setPen(pen)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        # Paints shape based on other stuff
        if CD[3] & 32: # Slope
            if CD[7] == 0:
                painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(0, TileWidth),
                                                    QtCore.QPoint(TileWidth, TileWidth),
                                                    QtCore.QPoint(TileWidth, 0)]))
            elif CD[7] == 1:
                painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(0, 0),
                                                    QtCore.QPoint(TileWidth, TileWidth),
                                                    QtCore.QPoint(0, TileWidth)]))
            elif CD[7] == 2:
                painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(0, TileWidth),
                                                    QtCore.QPoint(TileWidth, TileWidth),
                                                    QtCore.QPoint(TileWidth, TileWidth // 2)]))
            elif CD[7] == 3:
                painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(0, TileWidth),
                                                    QtCore.QPoint(0, TileWidth // 2),
                                                    QtCore.QPoint(TileWidth, 0),
                                                    QtCore.QPoint(TileWidth, TileWidth)]))
            elif CD[7] == 4:
                painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(0, TileWidth),
                                                    QtCore.QPoint(0, 0),
                                                    QtCore.QPoint(TileWidth, TileWidth // 2),
                                                    QtCore.QPoint(TileWidth, TileWidth)]))
            elif CD[7] == 5:
                painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(0, TileWidth // 2),
                                                    QtCore.QPoint(TileWidth, TileWidth),
                                                    QtCore.QPoint(0, TileWidth)]))
            elif CD[7] == 10:
                painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(0, 0),
                                                    QtCore.QPoint(0, TileWidth),
                                                    QtCore.QPoint(TileWidth, TileWidth),
                                                    QtCore.QPoint(TileWidth, 0)]))
            elif CD[7] == 11:
                painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(0, TileWidth),
                                                    QtCore.QPoint(TileWidth, TileWidth * 3 // 4),
                                                    QtCore.QPoint(TileWidth, TileWidth)]))
            elif CD[7] == 12:
                painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(TileWidth, TileWidth),
                                                    QtCore.QPoint(TileWidth, TileWidth // 2),
                                                    QtCore.QPoint(0, TileWidth * 3 // 4),
                                                    QtCore.QPoint(0, TileWidth)]))
            elif CD[7] == 13:
                painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(TileWidth, TileWidth),
                                                    QtCore.QPoint(TileWidth, TileWidth // 4),
                                                    QtCore.QPoint(0, TileWidth // 2),
                                                    QtCore.QPoint(0, TileWidth)]))
            elif CD[7] == 14:
                painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(TileWidth, TileWidth),
                                                    QtCore.QPoint(TileWidth, 0),
                                                    QtCore.QPoint(0, TileWidth // 4),
                                                    QtCore.QPoint(0, TileWidth)]))
            elif CD[7] == 15:
                painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(TileWidth, TileWidth),
                                                    QtCore.QPoint(TileWidth, TileWidth // 4),
                                                    QtCore.QPoint(0, 0),
                                                    QtCore.QPoint(0, TileWidth)]))
            elif CD[7] == 16:
                painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(TileWidth, TileWidth),
                                                    QtCore.QPoint(TileWidth, TileWidth // 2),
                                                    QtCore.QPoint(0, TileWidth // 4),
                                                    QtCore.QPoint(0, TileWidth)]))
            elif CD[7] == 17:
                painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(TileWidth, TileWidth),
                                                    QtCore.QPoint(TileWidth, TileWidth * 3 // 4),
                                                    QtCore.QPoint(0, TileWidth // 2),
                                                    QtCore.QPoint(0, TileWidth)]))
            elif CD[7] == 18:
                painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(TileWidth, TileWidth),
                                                    QtCore.QPoint(0, TileWidth * 3 // 4),
                                                    QtCore.QPoint(0, TileWidth)]))

        elif CD[3] & 64: # Reverse Slope
            if CD[7] == 0:
                painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(0, 0),
                                                    QtCore.QPoint(TileWidth, TileWidth),
                                                    QtCore.QPoint(TileWidth, 0)]))
            elif CD[7] == 1:
                painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(0, TileWidth),
                                                    QtCore.QPoint(0, 0),
                                                    QtCore.QPoint(TileWidth, 0)]))
            elif CD[7] == 2:
                painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(TileWidth, 0),
                                                    QtCore.QPoint(0, 0),
                                                    QtCore.QPoint(TileWidth, TileWidth // 2)]))
            elif CD[7] == 3:
                painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(0, 0),
                                                    QtCore.QPoint(0, TileWidth // 2),
                                                    QtCore.QPoint(TileWidth, TileWidth),
                                                    QtCore.QPoint(TileWidth, 0)]))
            elif CD[7] == 4:
                painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(0, TileWidth),
                                                    QtCore.QPoint(0, 0),
                                                    QtCore.QPoint(TileWidth, 0),
                                                    QtCore.QPoint(TileWidth, TileWidth // 2)]))
            elif CD[7] == 5:
                painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(0, TileWidth // 2),
                                                    QtCore.QPoint(0, 0),
                                                    QtCore.QPoint(TileWidth, 0)]))
            elif CD[7] == 10:
                painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(0, 0),
                                                    QtCore.QPoint(0, TileWidth),
                                                    QtCore.QPoint(TileWidth, TileWidth),
                                                    QtCore.QPoint(TileWidth, 0)]))
            elif CD[7] == 11:
                painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(0, 0),
                                                    QtCore.QPoint(TileWidth, 0),
                                                    QtCore.QPoint(TileWidth, TileWidth // 4)]))
            elif CD[7] == 12:
                painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(0, 0),
                                                    QtCore.QPoint(TileWidth, 0),
                                                    QtCore.QPoint(TileWidth, TileWidth // 2),
                                                    QtCore.QPoint(0, TileWidth // 4)]))
            elif CD[7] == 13:
                painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(0, 0),
                                                    QtCore.QPoint(TileWidth, 0),
                                                    QtCore.QPoint(TileWidth, TileWidth * 3 // 4),
                                                    QtCore.QPoint(0, TileWidth // 2)]))
            elif CD[7] == 14:
                painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(0, 0),
                                                    QtCore.QPoint(TileWidth, 0),
                                                    QtCore.QPoint(TileWidth, TileWidth),
                                                    QtCore.QPoint(0, TileWidth * 3 // 4)]))
            elif CD[7] == 15:
                painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(0, 0),
                                                    QtCore.QPoint(TileWidth, 0),
                                                    QtCore.QPoint(TileWidth, TileWidth * 3 // 4),
                                                    QtCore.QPoint(0, TileWidth)]))
            elif CD[7] == 16:
                painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(0, 0),
                                                    QtCore.QPoint(TileWidth, 0),
                                                    QtCore.QPoint(TileWidth, TileWidth // 2),
                                                    QtCore.QPoint(0, TileWidth * 3 // 4)]))
            elif CD[7] == 17:
                painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(0, 0),
                                                    QtCore.QPoint(TileWidth, 0),
                                                    QtCore.QPoint(TileWidth, TileWidth // 4),
                                                    QtCore.QPoint(0, TileWidth // 2)]))
            elif CD[7] == TileWidth * 3 // 4:
                painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(0, 0),
                                                    QtCore.QPoint(TileWidth, 0),
                                                    QtCore.QPoint(0, TileWidth // 4)]))

        elif CD[2] & 8: # Partial
            if CD[7] == 1:
                painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(0, 0),
                                                    QtCore.QPoint(TileWidth // 2, 0),
                                                    QtCore.QPoint(TileWidth // 2, TileWidth // 2),
                                                    QtCore.QPoint(0, TileWidth // 2)]))
            elif CD[7] == 2:
                painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(TileWidth // 2, 0),
                                                    QtCore.QPoint(TileWidth, 0),
                                                    QtCore.QPoint(TileWidth, TileWidth // 2),
                                                    QtCore.QPoint(TileWidth // 2, TileWidth // 2)]))
            elif CD[7] == 3:
                painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(0, 0),
                                                    QtCore.QPoint(TileWidth, 0),
                                                    QtCore.QPoint(TileWidth, TileWidth // 2),
                                                    QtCore.QPoint(0, TileWidth // 2)]))
            elif CD[7] == 4:
                painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(0, TileWidth // 2),
                                                    QtCore.QPoint(TileWidth // 2, TileWidth // 2),
                                                    QtCore.QPoint(TileWidth // 2, TileWidth),
                                                    QtCore.QPoint(0, TileWidth)]))
            elif CD[7] == 5:
                painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(0, 0),
                                                    QtCore.QPoint(TileWidth // 2, 0),
                                                    QtCore.QPoint(TileWidth // 2, TileWidth),
                                                    QtCore.QPoint(0, TileWidth)]))
            elif CD[7] == 6:
                painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(0, TileWidth),
                                                    QtCore.QPoint(TileWidth // 2, TileWidth),
                                                    QtCore.QPoint(TileWidth // 2, 0),
                                                    QtCore.QPoint(TileWidth, 0),
                                                    QtCore.QPoint(TileWidth, TileWidth // 2),
                                                    QtCore.QPoint(0, TileWidth // 2)]))
            elif CD[7] == 7:
                painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(0, 0),
                                                    QtCore.QPoint(TileWidth, 0),
                                                    QtCore.QPoint(TileWidth, TileWidth // 2),
                                                    QtCore.QPoint(TileWidth // 2, TileWidth // 2),
                                                    QtCore.QPoint(TileWidth // 2, TileWidth),
                                                    QtCore.QPoint(0, TileWidth)]))
            elif CD[7] == 8:
                painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(TileWidth // 2, TileWidth // 2),
                                                    QtCore.QPoint(TileWidth, TileWidth // 2),
                                                    QtCore.QPoint(TileWidth, TileWidth),
                                                    QtCore.QPoint(TileWidth // 2, TileWidth)]))
            elif CD[7] == 9:
                painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(TileWidth, 0),
                                                    QtCore.QPoint(TileWidth, TileWidth // 2),
                                                    QtCore.QPoint(0, TileWidth // 2),
                                                    QtCore.QPoint(0, TileWidth),
                                                    QtCore.QPoint(TileWidth // 2, TileWidth),
                                                    QtCore.QPoint(TileWidth // 2, 0)]))
            elif CD[7] == 10:
                painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(TileWidth // 2, 0),
                                                    QtCore.QPoint(TileWidth, 0),
                                                    QtCore.QPoint(TileWidth, TileWidth),
                                                    QtCore.QPoint(TileWidth // 2, TileWidth)]))
            elif CD[7] == 11:
                painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(0, 0),
                                                    QtCore.QPoint(TileWidth, 0),
                                                    QtCore.QPoint(TileWidth, TileWidth),
                                                    QtCore.QPoint(TileWidth // 2, TileWidth),
                                                    QtCore.QPoint(TileWidth // 2, TileWidth // 2),
                                                    QtCore.QPoint(0, TileWidth // 2)]))
            elif CD[7] == 12:
                painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(0, TileWidth // 2),
                                                    QtCore.QPoint(TileWidth, TileWidth // 2),
                                                    QtCore.QPoint(TileWidth, TileWidth),
                                                    QtCore.QPoint(0, TileWidth)]))
            elif CD[7] == 13:
                painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(0, 0),
                                                    QtCore.QPoint(TileWidth // 2, 0),
                                                    QtCore.QPoint(TileWidth // 2, TileWidth // 2),
                                                    QtCore.QPoint(TileWidth, TileWidth // 2),
                                                    QtCore.QPoint(TileWidth, TileWidth),
                                                    QtCore.QPoint(0, TileWidth)]))
            elif CD[7] == 14:
                painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(TileWidth, TileWidth),
                                                    QtCore.QPoint(TileWidth, 0),
                                                    QtCore.QPoint(TileWidth // 2, 0),
                                                    QtCore.QPoint(TileWidth // 2, TileWidth // 2),
                                                    QtCore.QPoint(0, TileWidth // 2),
                                                    QtCore.QPoint(0, TileWidth)]))
            elif CD[7] == 15:
                painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(0, 0),
                                                    QtCore.QPoint(TileWidth, 0),
                                                    QtCore.QPoint(TileWidth, TileWidth),
                                                    QtCore.QPoint(0, TileWidth)]))

        elif CD[2] & 0x20: # Solid-on-bottom
            painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(0, TileWidth),
                                                QtCore.QPoint(TileWidth, TileWidth),
                                                QtCore.QPoint(TileWidth, TileWidth * 3 // 4),
                                                QtCore.QPoint(0, TileWidth * 3 // 4)]))

            painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(TileWidth * 0.625, 0),
                                                QtCore.QPoint(TileWidth * 0.625, TileWidth // 2),
                                                QtCore.QPoint(TileWidth * 3 // 4, TileWidth // 2),
                                                QtCore.QPoint(TileWidth // 2, 17),
                                                QtCore.QPoint(TileWidth // 4, TileWidth // 2),
                                                QtCore.QPoint(TileWidth * 0.125, TileWidth // 2),
                                                QtCore.QPoint(TileWidth * 0.125, 0)]))

        elif CD[2] & 0x80: # Solid-on-top
            painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(0, 0),
                                                QtCore.QPoint(TileWidth, 0),
                                                QtCore.QPoint(TileWidth, TileWidth // 4),
                                                QtCore.QPoint(0, TileWidth // 4)]))

            painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(TileWidth * 0.875, TileWidth),
                                                QtCore.QPoint(TileWidth * 0.875, TileWidth // 2),
                                                QtCore.QPoint(TileWidth * 3 // 4, TileWidth // 2),
                                                QtCore.QPoint(TileWidth // 2, 7),
                                                QtCore.QPoint(TileWidth // 4, TileWidth // 2),
                                                QtCore.QPoint(TileWidth * 0.375, TileWidth // 2),
                                                QtCore.QPoint(TileWidth * 0.375, TileWidth)]))

        elif CD[2] & 16: # Spikes
            if CD[7] == 0:
                painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(TileWidth, 0),
                                                    QtCore.QPoint(TileWidth, TileWidth // 2),
                                                    QtCore.QPoint(0, TileWidth // 4)]))
                painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(TileWidth, TileWidth // 2),
                                                    QtCore.QPoint(TileWidth, TileWidth),
                                                    QtCore.QPoint(0, TileWidth * 3 // 4)]))
            if CD[7] == 1:
                painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(0, 0),
                                                    QtCore.QPoint(0, TileWidth // 2),
                                                    QtCore.QPoint(TileWidth, TileWidth // 4)]))
                painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(0, TileWidth // 2),
                                                    QtCore.QPoint(0, TileWidth),
                                                    QtCore.QPoint(TileWidth, TileWidth * 3 // 4)]))
            if CD[7] == 2:
                painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(0, TileWidth),
                                                    QtCore.QPoint(TileWidth // 2, TileWidth),
                                                    QtCore.QPoint(TileWidth // 4, 0)]))
                painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(TileWidth // 2, TileWidth),
                                                    QtCore.QPoint(TileWidth, TileWidth),
                                                    QtCore.QPoint(TileWidth * 3 // 4, 0)]))
            if CD[7] == 3:
                painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(0, 0),
                                                    QtCore.QPoint(TileWidth // 2, 0),
                                                    QtCore.QPoint(TileWidth // 4, TileWidth)]))
                painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(TileWidth // 2, 0),
                                                    QtCore.QPoint(TileWidth, 0),
                                                    QtCore.QPoint(TileWidth * 3 // 4, TileWidth)]))
            if CD[7] == 4:
                painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(0, 0),
                                                    QtCore.QPoint(TileWidth, 0),
                                                    QtCore.QPoint(TileWidth * 3 // 4, TileWidth),
                                                    QtCore.QPoint(TileWidth // 4, TileWidth)]))
            if CD[7] == 5:
                painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(TileWidth // 4, 0),
                                                    QtCore.QPoint(TileWidth * 3 // 4, 0),
                                                    QtCore.QPoint(TileWidth // 2, TileWidth)]))
            if CD[7] == 6:
                painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(0, 0),
                                                    QtCore.QPoint(TileWidth, 0),
                                                    QtCore.QPoint(TileWidth // 2, TileWidth)]))
                
        elif (CD[3] & 1) or (CD[3] in (5, 0x10)) or (CD[3] & 4) or (CD[3] & 8): # Solid, question or brick
            painter.drawRect(0, 0, TileWidth, TileWidth)

        else: # No fill
            pass

        self.collOverlay = collPix


    def addOverlay(self, overlayTile):
        """
        Adds a 3D overlay tile
        """
        if overlayTile is not None:
            overlayPix = overlayTile.main

            # Create a depth map
            self.depthMap = QtGui.QPixmap(TileWidth, TileWidth)
            self.depthMap.fill(theme.color('depth_highlight'))
            p2 = QtGui.QPainter(self.depthMap)
            p2.setCompositionMode(p2.CompositionMode_DestinationIn)
            p2.drawPixmap(0, 0, overlayPix)
            p2.end; del p2

            # Known bug: if the depth_highlight color is
            # fully opaque, things can get messed up.

            # Overlay the overlay tile onto self.main
            p1 = QtGui.QPainter(self.main)
            p1.drawPixmap(0, 0, overlayPix)
            p1.end; del p1


def RenderObject(tileset, objnum, width, height, fullslope=False):
    """
    Render a tileset object into an array
    """
    # allocate an array
    dest = []
    for i in range(height): dest.append([0]*width)

    # ignore non-existent objects
    try:
        tileset_defs = ObjectDefinitions[tileset]
    except IndexError:
        tileset_defs = None
    if tileset_defs is None: return dest
    try:
        obj = tileset_defs[objnum]
    except IndexError:
        obj = None
    if obj is None: return dest
    if len(obj.rows) == 0: return dest

    # diagonal objects are rendered differently
    if (obj.rows[0][0][0] & 0x80) != 0:
        RenderDiagonalObject(dest, obj, width, height, fullslope)
    else:
        # standard object
        repeatFound = False
        beforeRepeat = []
        inRepeat = []
        afterRepeat = []

        for row in obj.rows:
            if len(row) == 0: continue
            # row[0][0] is 0, 1, 2, 4
            if (row[0][0] & 2) != 0 or (row[0][0] & 4) != 0:
                repeatFound = True
                inRepeat.append(row)
            else:
                if repeatFound:
                    afterRepeat.append(row)
                else:
                    beforeRepeat.append(row)

        bc = len(beforeRepeat); ic = len(inRepeat); ac = len(afterRepeat)
        if ic == 0:
            for y in range(height):
                RenderStandardRow(dest[y], beforeRepeat[y % bc], y, width)
        else:
            afterthreshold = height - ac - 1
            for y in range(height):
                if y < bc:
                    RenderStandardRow(dest[y], beforeRepeat[y], y, width)
                elif y > afterthreshold:
                    RenderStandardRow(dest[y], afterRepeat[y - height + ac], y, width)
                else:
                    RenderStandardRow(dest[y], inRepeat[(y - bc) % ic], y, width)

    return dest

class ObjectDef():
    """
    Class for the object definitions
    """

    def __init__(self):
        """
        Constructor
        """
        self.width = 0
        self.height = 0
        self.rows = []

    def load(self, source, offset, tileoffset):
        """
        Load an object definition
        """
        i = offset
        row = []

        while True:
            cbyte = source[i]

            if cbyte == 0xFE:
                self.rows.append(row)
                i += 1
                row = []
            elif cbyte == 0xFF:
                return
            elif (cbyte & 0x80) != 0:
                row.append((cbyte,))
                i += 1
            else:
                # extra = source[i+2]
                # tilesetoffset = ((extra & 7) >> 1) * 256
                # tile = (cbyte, source[i+1] + tilesetoffset, extra >> 2)
                # row.append(tile)
                # i += 3
                extra = source[i+2]
                tile = [cbyte, source[i+1] | ((extra & 3) << 8), extra >> 2]
                row.append(tile)
                i += 3
                
def RenderStandardRow(dest, row, y, width):
    """
    Render a row from an object
    """
    repeatFound = False
    beforeRepeat = []
    inRepeat = []
    afterRepeat = []

    for tile in row:
        # NSMBU introduces two (?) new ways to define horizontal tiling, IN ADDITION TO the original one
        tiling = False
        tiling = tiling or ((tile[2] & 1) != 0 and (tile[0] & 1) != 0) # NSMBW-style (still applies to NSMBU)
        tiling = tiling or ((row[0][0] & 4) != 0 and (tile[0] & 4) == 0) # NSMBU-style (J_Kihon BG rocks)
        tiling = tiling or ((tile[0] & 1) != 0) # NSMBU-style (horizontal pipes)

        if tiling:
            repeatFound = True
            inRepeat.append(tile)
        else:
            if repeatFound:
                afterRepeat.append(tile)
            else:
                beforeRepeat.append(tile)

    bc = len(beforeRepeat); ic = len(inRepeat); ac = len(afterRepeat)
    if ic == 0:
        for x in range(width):
            dest[x] = beforeRepeat[x % bc][1]
    else:
        afterthreshold = width - ac - 1
        for x in range(width):
            if x < bc:
                dest[x] = beforeRepeat[x][1]
            elif x > afterthreshold:
                dest[x] = afterRepeat[x - width + ac][1]
            else:
                dest[x] = inRepeat[(x - bc) % ic][1]


def RenderDiagonalObject(dest, obj, width, height, fullslope):
    """
    Render a diagonal object
    """
    # set all to empty tiles
    for row in dest:
        for x in range(width):
            row[x] = -1

    # get sections
    mainBlock,subBlock = GetSlopeSections(obj)
    cbyte = obj.rows[0][0][0]

    # get direction
    goLeft = ((cbyte & 1) != 0)
    goDown = ((cbyte & 2) != 0)

    # base the amount to draw by seeing how much we can fit in each direction
    if fullslope:
        drawAmount = max(height // len(mainBlock), width // len(mainBlock[0]))
    else:
        drawAmount = min(height // len(mainBlock), width // len(mainBlock[0]))

    # if it's not goingLeft and not goingDown:
    if not goLeft and not goDown:
        # slope going from SW => NE
        # start off at the bottom left
        x = 0
        y = height - len(mainBlock) - (0 if subBlock is None else len(subBlock))
        xi = len(mainBlock[0])
        yi = -len(mainBlock)

    # ... and if it's goingLeft and not goingDown:
    elif goLeft and not goDown:
        # slope going from SE => NW
        # start off at the top left
        x = 0
        y = 0
        xi = len(mainBlock[0])
        yi = len(mainBlock)

    # ... and if it's not goingLeft but it's goingDown:
    elif not goLeft and goDown:
        # slope going from NW => SE
        # start off at the top left
        x = 0
        y = (0 if subBlock is None else len(subBlock))
        xi = len(mainBlock[0])
        yi = len(mainBlock)

    # ... and finally, if it's goingLeft and goingDown:
    else:
        # slope going from SW => NE
        # start off at the bottom left
        x = 0
        y = height - len(mainBlock)
        xi = len(mainBlock[0])
        yi = -len(mainBlock)


    # finally draw it
    for i in range(drawAmount):
        PutObjectArray(dest, x, y, mainBlock, width, height)
        if subBlock is not None:
            xb = x
            if goLeft: xb = x + len(mainBlock[0]) - len(subBlock[0])
            if goDown:
                PutObjectArray(dest, xb, y - len(subBlock), subBlock, width, height)
            else:
                PutObjectArray(dest, xb, y + len(mainBlock), subBlock, width, height)
        x += xi
        y += yi


def PutObjectArray(dest, xo, yo, block, width, height):
    """
    Places a tile array into an object
    """
    #for y in range(yo,min(yo+len(block),height)):
    for y in range(yo,yo+len(block)):
        if y < 0: continue
        if y >= height: continue
        drow = dest[y]
        srow = block[y-yo]
        #for x in range(xo,min(xo+len(srow),width)):
        for x in range(xo,xo+len(srow)):
            if x < 0: continue
            if x >= width: continue
            drow[x] = srow[x-xo][1]


def GetSlopeSections(obj):
    """
    Sorts the slope data into sections
    """
    sections = []
    currentSection = None

    for row in obj.rows:
        if len(row) > 0 and (row[0][0] & 0x80) != 0: # begin new section
            if currentSection is not None:
                sections.append(CreateSection(currentSection))
            currentSection = []
        currentSection.append(row)

    if currentSection is not None: # end last section
        sections.append(CreateSection(currentSection))

    if len(sections) == 1:
        return (sections[0],None)
    else:
        return (sections[0],sections[1])


def CreateSection(rows):
    """
    Create a slope section
    """
    # calculate width
    width = 0
    for row in rows:
        thiswidth = CountTiles(row)
        if width < thiswidth: width = thiswidth

    # create the section
    section = []
    for row in rows:
        drow = [0] * width
        x = 0
        for tile in row:
            if (tile[0] & 0x80) == 0:
                drow[x] = tile
                x += 1
        section.append(drow)

    return section


def CountTiles(row):
    """
    Counts the amount of real tiles in an object row
    """
    res = 0
    for tile in row:
        if (tile[0] & 0x80) == 0:
            res += 1
    return res


def CreateTilesets():
    """
    Blank out the tileset arrays
    """
    global Tiles, TilesetFilesLoaded, TilesetAnimTimer, TileBehaviours, ObjectDefinitions

    Tiles = [None]*0x200*4
    Tiles += Overrides
    TilesetFilesLoaded = [None, None, None, None]
    #TileBehaviours = [0]*1024
    TilesetAnimTimer = QtCore.QTimer()
    TilesetAnimTimer.timeout.connect(IncrementTilesetFrame)
    TilesetAnimTimer.start(180)
    ObjectDefinitions = [None]*4
    SLib.Tiles = Tiles


def LoadTileset(idx, name, reload=False):
    try:
        return _LoadTileset(idx, name, reload)
    except Exception:
        raise
        QtWidgets.QMessageBox.warning(None, trans.string('Err_CorruptedTileset', 0), trans.string('Err_CorruptedTileset', 1, '[file]', name))
        return False

def _LoadTileset(idx, name, reload=False):
    """
    Load in a tileset into a specific slot
    """

    # # find the tileset path
    # global arcname
    # TilesetPaths = reversed(gamedef.GetGamePaths())

    # found = False
    # for path in TilesetPaths:
    #     if path is None: break

    #     arcname = path + '/Unit/' + name + '.sarc'
    #     compressed = False
    #     if os.path.isfile(arcname):
    #         found = True
    #         break
    #     arcname += '.lh'
    #     compressed = True
    #     if os.path.isfile(arcname):
    #         found = True
    #         break

    # # warning if not found
    # if not found:
    #     QtWidgets.QMessageBox.warning(None, trans.string('Err_MissingTileset', 0), trans.string('Err_MissingTileset', 1, '[file]', name))
    #     return False

    # if this file's already loaded, return
    if TilesetFilesLoaded[idx] == name and not reload: return

    # get the data
    # with open(arcname, 'rb') as fileobj:
    #     arcdata = fileobj.read()
    # if compressed:
    #     arcdata = LHTool.decompressLH(arcdata)
    if name not in szsData: return
    arcdata = szsData[name]
    arc = SarcLib.SARC_Archive()
    arc.load(arcdata)

    tileoffset = idx * 256

    global Tiles, TilesetCache, TileThreads
    if name not in TilesetCache or not TilesetCompletelyCached[name]:
        # Load the tiles because they're not cached.

        # Decompress the textures
        try:
            comptiledata = arc['BG_tex/%s.gtx' % name].data
            colldata = arc['BG_chk/d_bgchk_%s.bin' % name].data
        except KeyError:
            QtWidgets.QMessageBox.warning(None, trans.string('Err_CorruptedTilesetData', 0), trans.string('Err_CorruptedTilesetData', 1, '[file]', name))
            return False

        # Prepare the TilesetTiles
        for i in range(tileoffset, tileoffset + 256):
            Tiles[i] = TilesetTile(QtGui.QPixmap())

        # Run the progressive tileset rendering thread for this tileset
        if TileThreads[idx] is not None:
            TileThreads[idx].stop()
        TileThreads[idx] = ProgressiveTilesetRenderingThread()
        TileThreads[idx].setStuff(comptiledata, idx, tileoffset, name)
        TileThreads[idx].start()

        # # Add overlays
        # overlayfile = arc['BG_unt/%s_add.bin' % name].data
        # overlayArray = struct.unpack('>441H', overlayfile[:882])
        # i = idx * 0x200
        # arrayi = 0
        # for y in range(21):
        #     for x in range(21):
        #         if Tiles[i] is not None:
        #             Tiles[i].addOverlay(Tiles[overlayArray[arrayi]])
        #         i += 1; arrayi += 1

        # Load the tileset animations, if there are any
        #isAnimated, prefix = CheckTilesetAnimated(arc)
        isAnimated = False
        if isAnimated:
            row = 0
            col = 0
            for i in range(tileoffset,tileoffset+441):
                filenames = []
                filenames.append('%s_%d%s%s.bin' % (prefix, idx, hex(row)[2].lower(), hex(col)[2].lower()))
                filenames.append('%s_%d%s%s.bin' % (prefix, idx, hex(row)[2].upper(), hex(col)[2].upper()))
                if filenames[0] == filenames[1]:
                    item = filenames[0]
                    filenames = []
                    filenames.append(item)
                for fn in filenames:
                    fn = 'BG_tex/' + fn
                    found = False
                    try:
                        arc[fn]
                        found = True
                    except KeyError:
                        pass
                    if found:
                        Tiles[i].addAnimationData(arc[fn])
                col += 1
                if col == 16:
                    col = 0
                    row += 1

    else:
        # We already have tiles in the tileset cache; copy them over to Tiles
        for i in range(256):
            Tiles[i + tileoffset] = TilesetCache[name][i]


    # Load the object definitions
    defs = [None] * 256

    indexfile = arc['BG_unt/%s_hd.bin' % name].data
    deffile = arc['BG_unt/%s.bin' % name].data
    objcount = len(indexfile) // 6
    indexstruct = struct.Struct('>HBBH')

    for i in range(objcount):
        data = indexstruct.unpack_from(indexfile, i * 6)
        obj = ObjectDef()
        obj.width = data[1]
        obj.height = data[2]
        obj.load(deffile, data[0], tileoffset)
        defs[i] = obj

    ObjectDefinitions[idx] = defs

    # Keep track of this filepath
    TilesetFilesLoaded[idx] = name

    # Add Tiles to spritelib
    SLib.Tiles = Tiles

    # Add Tiles to the cache, but not for NSMBU Pa1/2/3 since that doesn't make any sense
    if mainWindow.CurrentGame != NewSuperMarioBrosU:
        TilesetCache[name] = []
        for i in range(256):
            TilesetCache[name].append(Tiles[i + tileoffset])


def LoadTexture(tiledata):
    with open('texturipper/texture.ctpk', 'wb') as binfile:
        binfile.write(tiledata)

    if AutoOpenScriptEnabled: return QtGui.QImage(512, 512, QtGui.QImage.Format_ARGB32)

    with subprocess.Popen('texturipper/texturipper_1.2.exe texture.ctpk', cwd='texturipper') as proc:
        pass

    pngname = None
    for filename in os.listdir('texturipper'):
        if filename.endswith('.png'):
            pngname = filename
    if not pngname: raise Exception

    with open(os.path.join('texturipper', pngname), 'rb') as pngfile:
        img = QtGui.QImage(os.path.join('texturipper', pngname))

    for filename in os.listdir('texturipper'):
        if filename == 'texturipper_1.2.exe': continue
        os.remove(os.path.join('texturipper', filename))

    return img


def IncrementTilesetFrame():
    """
    Moves each tileset to the next frame
    """
    if not TilesetsAnimating: return
    for tile in Tiles:
        if tile is not None: tile.nextFrame()
    mainWindow.scene.update()
    mainWindow.objPicker.update()


def CheckTilesetAnimated(tileset):
    """Checks if a tileset contains Newer-style animations, and if so, returns
    (True, prefix) where prefix is the animation prefix. If not, (False, None).
    tileset should be a Wii.py U8 object."""
    # Find the animation files, if any
    excludes = (
        'block_anime.bin',
        'hatena_anime.bin',
        'tuka_coin_anime.bin',
        )
    texFiles = tileset['BG_tex']
    animFiles = []
    for f in texFiles:
        # Determine if it's likely an animation file
        if f.lower() in excludes: continue
        if f[-4:].lower() != '.bin': continue
        namelen = len(f)
        if namelen == 9:
            if f[1] != '_': continue
            if f[2] not in '0123': continue
            if f[3].lower() not in '0123456789abcdef': continue
            if f[4].lower() not in '0123456789abcdef': continue
        elif namelen == 10:
            if f[2] != '_': continue
            if f[3] not in '0123': continue
            if f[4].lower() not in '0123456789abcdef': continue
            if f[5].lower() not in '0123456789abcdef': continue
        animFiles.append(f)

    # Quit if there's no animation
    if len(animFiles) == 0: return False, None
    else:
        # This makes so many assumptions
        fn = animFiles[0]
        prefix = fn[0] if len(fn) == 9 else fn[:2]
        return True, prefix



def UnloadTileset(idx):
    """
    Unload the tileset from a specific slot
    """
    for i in range(idx * 0x200, idx * 0x200 + 0x200):
        Tiles[i] = None

    ObjectDefinitions[idx] = None
    TilesetFilesLoaded[idx] = None


def ProcessOverrides(idx, name):
    """
    Load overridden tiles if there are any
    """

    try:
        tsindexes = ['J_Kihon', 'J_Chika', 'J_Setsugen', 'J_Yougan', 'J_Gold', 'J_Suichu']
        if name in tsindexes:
            offset = (0x200 * 4) + (tsindexes.index(name) * 64)
            # Setsugen/Snow is unused for some reason? but we still override it

            defs = ObjectDefinitions[idx]
            t = Tiles

            # Invisible blocks
            # these are all the same so let's just load them from the first row
            replace = 0x200 * 4
            for i in [3, 4, 5, 6, 7, 8, 9, 10]:
                t[i].main = t[replace].main
                replace += 1

            # Question and brick blocks
            # these don't have their own tiles so we have to do them by objects
            replace = offset + 9
            for i in range(30, 41):
                defs[i].rows[0][0] = (0, replace, 0)
                replace += 1
            for i in range(16, 30):
                defs[i].rows[0][0] = (0, replace, 0)
                replace += 1

            # now the extra stuff (invisible collisions etc)
            replace = 0x200 * 4 + 64 * 4
            for i in [0, 1, 11, 14, 2, 13, 12]:
                t[i].main = t[replace].main
                replace += 1
            replace = 0x200 * 4 + 64 * 5
            for i in [190, 191, 192]:
                t[i].main = t[replace].main
                replace += 1
            # t[1].main = t[1280].main # solid
            # t[2].main = t[1311].main # vine stopper
            # t[11].main = t[1310].main # jumpthrough platform
            # t[12].main = t[1309].main # 16x8 roof platform

            # t[16].main = t[1291].main # 1x1 slope going up
            # t[17].main = t[1292].main # 1x1 slope going down
            # t[18].main = t[1281].main # 2x1 slope going up (part 1)
            # t[19].main = t[1282].main # 2x1 slope going up (part 2)
            # t[20].main = t[1283].main # 2x1 slope going down (part 1)
            # t[21].main = t[1284].main # 2x1 slope going down (part 2)
            # t[22].main = t[1301].main # 4x1 slope going up (part 1)
            # t[23].main = t[1302].main # 4x1 slope going up (part 2)
            # t[24].main = t[1303].main # 4x1 slope going up (part 3)
            # t[25].main = t[1304].main # 4x1 slope going up (part 4)
            # t[26].main = t[1305].main # 4x1 slope going down (part 1)
            # t[27].main = t[1306].main # 4x1 slope going down (part 2)
            # t[28].main = t[1307].main # 4x1 slope going down (part 3)
            # t[29].main = t[1308].main # 4x1 slope going down (part 4)
            # t[30].main = t[1062].main # coin

            # t[32].main = t[1289].main # 1x1 roof going down
            # t[33].main = t[1290].main # 1x1 roof going up
            # t[34].main = t[1285].main # 2x1 roof going down (part 1)
            # t[35].main = t[1286].main # 2x1 roof going down (part 2)
            # t[36].main = t[1287].main # 2x1 roof going up (part 1)
            # t[37].main = t[1288].main # 2x1 roof going up (part 2)
            # t[38].main = t[1293].main # 4x1 roof going down (part 1)
            # t[39].main = t[1294].main # 4x1 roof going down (part 2)
            # t[40].main = t[1295].main # 4x1 roof going down (part 3)
            # t[41].main = t[1296].main # 4x1 roof going down (part 4)
            # t[42].main = t[1297].main # 4x1 roof going up (part 1)
            # t[43].main = t[1298].main # 4x1 roof going up (part 2)
            # t[44].main = t[1299].main # 4x1 roof going up (part 3)
            # t[45].main = t[1300].main # 4x1 roof going up (part 4)
            # t[46].main = t[1312].main # P-switch coins

            # t[53].main = t[1314].main # donut lift
            # t[61].main = t[1063].main # multiplayer coin
            # t[63].main = t[1313].main # instant death tile

        elif name == 'Pa1_nohara' or name == 'Pa1_nohara2' or name == 'Pa1_daishizen':
            # flowers
            t = Tiles
            t[416].main = t[1092].main # grass
            t[417].main = t[1093].main
            t[418].main = t[1094].main
            t[419].main = t[1095].main
            t[420].main = t[1096].main

            if name == 'Pa1_nohara' or name == 'Pa1_nohara2':
                t[432].main = t[1068].main # flowers
                t[433].main = t[1069].main # flowers
                t[434].main = t[1070].main # flowers

                t[448].main = t[1158].main # flowers on grass
                t[449].main = t[1159].main
                t[450].main = t[1160].main
            elif name == 'Pa1_daishizen':
                # forest flowers
                t[432].main = t[1071].main # flowers
                t[433].main = t[1072].main # flowers
                t[434].main = t[1073].main # flowers

                t[448].main = t[1222].main # flowers on grass
                t[449].main = t[1223].main
                t[450].main = t[1224].main

        elif name == 'Pa3_rail' or name == 'Pa3_rail_white' or name == 'Pa3_daishizen':
            # These are the line guides
            # Pa3_daishizen has less though

            t = Tiles

            t[768].main = t[1088].main # horizontal line
            t[769].main = t[1089].main # vertical line
            t[770].main = t[1090].main # bottomright corner
            t[771].main = t[1091].main # topleft corner

            t[784].main = t[1152].main # left red blob (part 1)
            t[785].main = t[1153].main # top red blob (part 1)
            t[786].main = t[1154].main # top red blob (part 2)
            t[787].main = t[1155].main # right red blob (part 1)
            t[788].main = t[1156].main # topleft red blob
            t[789].main = t[1157].main # topright red blob

            t[800].main = t[1216].main # left red blob (part 2)
            t[801].main = t[1217].main # bottom red blob (part 1)
            t[802].main = t[1218].main # bottom red blob (part 2)
            t[803].main = t[1219].main # right red blob (part 2)
            t[804].main = t[1220].main # bottomleft red blob
            t[805].main = t[1221].main # bottomright red blob

            # Those are all for Pa3_daishizen
            if name == 'Pa3_daishizen': return

            t[816].main = t[1056].main # 1x2 diagonal going up (top edge)
            t[817].main = t[1057].main # 1x2 diagonal going down (top edge)

            t[832].main = t[1120].main # 1x2 diagonal going up (part 1)
            t[833].main = t[1121].main # 1x2 diagonal going down (part 1)
            t[834].main = t[1186].main # 1x1 diagonal going up
            t[835].main = t[1187].main # 1x1 diagonal going down
            t[836].main = t[1058].main # 2x1 diagonal going up (part 1)
            t[837].main = t[1059].main # 2x1 diagonal going up (part 2)
            t[838].main = t[1060].main # 2x1 diagonal going down (part 1)
            t[839].main = t[1061].main # 2x1 diagonal going down (part 2)

            t[848].main = t[1184].main # 1x2 diagonal going up (part 2)
            t[849].main = t[1185].main # 1x2 diagonal going down (part 2)
            t[850].main = t[1250].main # 1x1 diagonal going up
            t[851].main = t[1251].main # 1x1 diagonal going down
            t[852].main = t[1122].main # 2x1 diagonal going up (part 1)
            t[853].main = t[1123].main # 2x1 diagonal going up (part 2)
            t[854].main = t[1124].main # 2x1 diagonal going down (part 1)
            t[855].main = t[1125].main # 2x1 diagonal going down (part 2)

            t[866].main = t[1065].main # big circle piece 1st row
            t[867].main = t[1066].main # big circle piece 1st row
            t[870].main = t[1189].main # medium circle piece 1st row
            t[871].main = t[1190].main # medium circle piece 1st row

            t[881].main = t[1128].main # big circle piece 2nd row
            t[882].main = t[1129].main # big circle piece 2nd row
            t[883].main = t[1130].main # big circle piece 2nd row
            t[884].main = t[1131].main # big circle piece 2nd row
            t[885].main = t[1252].main # medium circle piece 2nd row
            t[886].main = t[1253].main # medium circle piece 2nd row
            t[887].main = t[1254].main # medium circle piece 2nd row
            t[888].main = t[1188].main # small circle

            t[896].main = t[1191].main # big circle piece 3rd row
            t[897].main = t[1192].main # big circle piece 3rd row
            t[900].main = t[1195].main # big circle piece 3rd row
            t[901].main = t[1316].main # medium circle piece 3rd row
            t[902].main = t[1317].main # medium circle piece 3rd row
            t[903].main = t[1318].main # medium circle piece 3rd row

            t[912].main = t[1255].main # big circle piece 4th row
            t[913].main = t[1256].main # big circle piece 4th row
            t[916].main = t[1259].main # big circle piece 4th row

            t[929].main = t[1320].main # big circle piece 5th row
            t[930].main = t[1321].main # big circle piece 5th row
            t[931].main = t[1322].main # big circle piece 5th row
            t[932].main = t[1323].main # big circle piece 5th row

        elif name == 'Pa3_MG_house_ami_rail':
            t = Tiles

            t[832].main = t[1088].main # horizontal line
            t[833].main = t[1090].main # bottomright corner
            t[834].main = t[1088].main # horizontal line

            t[848].main = t[1089].main # vertical line
            t[849].main = t[1089].main # vertical line
            t[850].main = t[1091].main # topleft corner

            t[835].main = t[1152].main # left red blob (part 1)
            t[836].main = t[1153].main # top red blob (part 1)
            t[837].main = t[1154].main # top red blob (part 2)
            t[838].main = t[1155].main # right red blob (part 1)

            t[851].main = t[1216].main # left red blob (part 2)
            t[852].main = t[1217].main # bottom red blob (part 1)
            t[853].main = t[1218].main # bottom red blob (part 2)
            t[854].main = t[1219].main # right red blob (part 2)

            t[866].main = t[1065].main # big circle piece 1st row
            t[867].main = t[1066].main # big circle piece 1st row
            t[870].main = t[1189].main # medium circle piece 1st row
            t[871].main = t[1190].main # medium circle piece 1st row

            t[881].main = t[1128].main # big circle piece 2nd row
            t[882].main = t[1129].main # big circle piece 2nd row
            t[883].main = t[1130].main # big circle piece 2nd row
            t[884].main = t[1131].main # big circle piece 2nd row
            t[885].main = t[1252].main # medium circle piece 2nd row
            t[886].main = t[1253].main # medium circle piece 2nd row
            t[887].main = t[1254].main # medium circle piece 2nd row

            t[896].main = t[1191].main # big circle piece 3rd row
            t[897].main = t[1192].main # big circle piece 3rd row
            t[900].main = t[1195].main # big circle piece 3rd row
            t[901].main = t[1316].main # medium circle piece 3rd row
            t[902].main = t[1317].main # medium circle piece 3rd row
            t[903].main = t[1318].main # medium circle piece 3rd row

            t[912].main = t[1255].main # big circle piece 4th row
            t[913].main = t[1256].main # big circle piece 4th row
            t[916].main = t[1259].main # big circle piece 4th row

            t[929].main = t[1320].main # big circle piece 5th row
            t[930].main = t[1321].main # big circle piece 5th row
            t[931].main = t[1322].main # big circle piece 5th row
            t[932].main = t[1323].main # big circle piece 5th row
    except Exception:
        # Fail silently
        pass


def LoadOverrides():
    """
    Load overrides
    """
    global Overrides

    OverrideBitmap = QtGui.QPixmap('reggiedata/overrides.png')
    Overrides = [None]*384
    idx = 0
    xcount = OverrideBitmap.width() // TileWidth
    ycount = OverrideBitmap.height() // TileWidth
    sourcex = 0
    sourcey = 0

    for y in range(ycount):
        for x in range(xcount):
            bmp = OverrideBitmap.copy(sourcex, sourcey, TileWidth, TileWidth)
            Overrides[idx] = TilesetTile(bmp)

            # Set collisions if it's a brick or question
            if y <= 4:
                if 8 < x < 20: Overrides[idx].setQuestionCollisions()
                elif 20 <= x < 32: Overrides[idx].setBrickCollisions()

            idx += 1
            sourcex += TileWidth
        sourcex = 0
        sourcey += TileWidth
        if idx % 64 != 0:
            idx -= (idx % 64)
            idx += 64

