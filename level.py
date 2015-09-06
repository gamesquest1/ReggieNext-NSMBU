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


# level.py
# does stuff with parsing levels / areas, loads metadata, loads blocks, and saves them


################################################################
################################################################

import reggie
import tile
from PyQt5 import QtCore, QtGui, QtWidgets # if reggie.py has it, this should have it
import SARC as SarcLib
import spritelib as SLib
import struct

class AbstractLevel():
    """
    Class for an abstract level from any game. Defines the API.
    """
    def __init__(self):
        """
        Initializes the level with default settings
        """
        self.filepath = None
        self.name = 'untitled'

        self.areas = []

    def load(self, data, areaNum, progress=None):
        """
        Loads a level from bytes data. You MUST reimplement this in subclasses!
        """
        pass

    def save(self):
        """
        Returns the level as a bytes object. You MUST reimplement this in subclasses!
        """
        return b''

    def addArea(self):
        """
        Adds an area to the level, and returns it.
        """
        new = AbstractArea()
        self.areas.append(new)

        return new

    def deleteArea(self, number):
        """
        Removes the area specified. Number is a 1-based value, not 0-based;
        so you would pass a 1 if you wanted to delete the first area.
        """
        del self.areas[number - 1]
        return True


class Level_NSMBU(AbstractLevel):
    """
    Class for a level from New Super Mario Bros. U
    """
    def __init__(self):
        """
        Initializes the level with default settings
        """
        super().__init__()
        self.areas.append(Area_NSMBU())

    def load(self, data, areaNum, progress=None):
        """
        Loads a NSMBU level from bytes data.
        """
        super().load(data, areaNum, progress)

        global Area

        arc = SarcLib.SARC_Archive()
        arc.load(data)

        try:
            courseFolder = arc['course']
        except:
            return False

        # Sort the area data
        areaData = {}
        for file in courseFolder.contents:
            name, val = file.name, file.data

            if val is None: continue

            if not name.startswith('course'): continue
            if not name.endswith('.bin'): continue
            if '_bgdatL' in name:
                # It's a layer file
                if len(name) != 19: continue
                try:
                    thisArea = int(name[6])
                    laynum = int(name[14])
                except ValueError: continue
                if not (0 < thisArea < 5): continue

                if thisArea not in areaData: areaData[thisArea] = [None] * 4
                areaData[thisArea][laynum + 1] = val
            else:
                # It's the course file
                if len(name) != 11: continue
                try:
                    thisArea = int(name[6])
                except ValueError: continue
                if not (0 < thisArea < 5): continue

                if thisArea not in areaData: areaData[thisArea] = [None] * 4
                areaData[thisArea][0] = val

        # Create area objects
        self.areas = []
        thisArea = 1
        while thisArea in areaData:
            course = areaData[thisArea][0]
            L0 = areaData[thisArea][1]
            L1 = areaData[thisArea][2]
            L2 = areaData[thisArea][3]

            if thisArea == areaNum:
                newarea = Area_NSMBU()
                Area = newarea
                SLib.Area = Area
            else:
                newarea = AbstractArea()

            newarea.areanum = thisArea
            newarea.load(course, L0, L1, L2, progress)
            self.areas.append(newarea)

            thisArea += 1


        return True

    def save(self, innerfilename):
        """
        Save the level back to a file
        """

        # Make a new archive
        newArchive = SarcLib.SARC_Archive()

        # Create a folder within the archive
        courseFolder = SarcLib.Folder('course')
        newArchive.addFolder(courseFolder)

        # Go through the areas, save them and add them back to the archive
        for areanum, area in enumerate(self.areas):
            course, L0, L1, L2 = area.save()

            if course is not None:
                courseFolder.addFile(SarcLib.File('course%d.bin' % (areanum + 1), course))
            if L0 is not None:
                courseFolder.addFile(SarcLib.File('course%d_bgdatL0.bin' % (areanum + 1), L0))
            if L1 is not None:
                courseFolder.addFile(SarcLib.File('course%d_bgdatL1.bin' % (areanum + 1), L1))
            if L2 is not None:
                courseFolder.addFile(SarcLib.File('course%d_bgdatL2.bin' % (areanum + 1), L2))

        # Here we have the new inner-SARC savedata
        innersarc = newArchive.save(0x04, 0x170)

        # Now make an outer SARC
        outerArchive = SarcLib.SARC_Archive()
        fn = innerfilename
        outerArchive.addFile(SarcLib.File(fn, innersarc))
        for szsThingName in szsData:
            try:
                spl = szsThingName.split('-')
                int(spl[0])
                int(spl[1])
                continue
            except: pass
            outerArchive.addFile(SarcLib.File(szsThingName, szsData[szsThingName]))

        # Make it easy for future Reggies to pick out the level name
        outerArchive.addFile(SarcLib.File('levelname', fn.encode('utf-8')))


        return outerArchive.save(0x2000)


    def addArea(self):
        """
        Adds an area to the level, and returns it.
        """
        new = Area_NSMBU()
        self.areas.append(new)

        return new


class AbstractArea():
    """
    An extremely basic abstract area. Implements the basic function API.
    """
    def __init__(self):
        self.areanum = 1
        self.course = None
        self.L0 = None
        self.L1 = None
        self.L2 = None

    def load(self, course, L0, L1, L2, progress=None):
        self.course = course
        self.L0 = L0
        self.L1 = L1
        self.L2 = L2

    def save(self):
        return (self.course, self.L0, self.L1, self.L2)


class AbstractParsedArea(AbstractArea):
    """
    An area that is parsed to load sprites, entrances, etc. Still abstracted among games.
    Don't instantiate this! It could blow up becuase many of the functions are only defined
    within subclasses. If you want an area object, use a game-specific subclass.
    """
    def __init__(self):
        """
        Creates a completely new area
        """

        # Default area number
        self.areanum = 1

        # Settings
        self.defEvents = 0
        self.wrapFlag = 0
        self.timeLimit = 300
        self.unk1 = 0
        self.startEntrance = 0
        self.unk2 = 0
        self.unk3 = 0

        # Lists of things
        self.entrances = []
        self.sprites = []
        self.zones = []
        self.locations = []
        self.pathdata = []
        self.paths = []
        self.progpathdata = []
        self.progpaths = []
        self.comments = []
        self.layers = [[], [], []]

        # Metadata
        self.LoadReggieInfo(None)

        # Load tilesets
        tile.CreateTilesets()
        #LoadTileset(0, self.tileset0)
        #LoadTileset(1, self.tileset1)


    def load(self, course, L0, L1, L2, progress=None):
        """
        Loads an area from the archive files
        """

        # with open('course3.bin', 'rb') as f:
        #     course = f.read()

        # Load in the course file and blocks
        self.LoadBlocks(course)

        # with open('L0_.bin', 'rb') as f:
        #     L0 = f.read()
        # with open('L1_.bin', 'rb') as f:
        #     L1 = f.read()
        # with open('L2_.bin', 'rb') as f:
        #     L2 = f.read()
        # with open('block6.bin', 'wb') as f:
        #     f.write(self.blocks[6])
        # with open('block9.bin', 'wb') as f:
        #     f.write(self.blocks[9])
        # for blocknum in range(20):
        #     try:
        #         with open('block%d_.bin' % blocknum, 'rb') as f:
        #             self.blocks[blocknum] = f.read()
        #     except: pass

        # with open('course3_bgdatL0.bin', 'rb') as f:
        #     L0 = f.read()
        # with open('course3_bgdatL1.bin', 'rb') as f:
        #     L1 = f.read()
        # with open('course3_bgdatL2.bin', 'rb') as f:
        #     L2 = f.read()

        # Load stuff from individual blocks
        self.LoadTilesetNames() # block 1
        self.LoadOptions() # block 2
        self.LoadEntrances() # block 7
        self.LoadSprites() # block 8
        self.LoadZones() # block 10 (also blocks 3, 5, and 6)
        self.LoadLocations() # block 11
        self.LoadPaths() # block 12 and 13
        self.LoadProgPaths() # block 16 and 17

        # Load the editor metadata
        if self.block1pos[0] != 0x70:
            rdsize = self.block1pos[0] - 0x70
            rddata = course[0x70:self.block1pos[0]]
            self.LoadReggieInfo(rddata)
        else:
            self.LoadReggieInfo(None)
        del self.block1pos

        # Now, load the comments
        self.LoadComments()

        # Load the tilesets
        if progress is not None: progress.setLabelText(trans.string('Splash', 3))
        if app.splashscrn is not None: updateSplash(trans.string('Splash', 3), 0)

        CreateTilesets()
        if progress is not None: progress.setValue(1)
        if app.splashscrn is not None: updateSplash(trans.string('Splash', 3), 1)
        if self.tileset0 != '': LoadTileset(0, self.tileset0)
        if progress is not None: progress.setValue(2)
        if app.splashscrn is not None: updateSplash(trans.string('Splash', 3), 2)
        if self.tileset1 != '': LoadTileset(1, self.tileset1)
        if progress is not None: progress.setValue(3)
        if app.splashscrn is not None: updateSplash(trans.string('Splash', 3), 3)
        if self.tileset2 != '': LoadTileset(2, self.tileset2)
        if progress is not None: progress.setValue(4)
        if app.splashscrn is not None: updateSplash(trans.string('Splash', 3), 4)
        if self.tileset3 != '': LoadTileset(3, self.tileset3)

        # Load the object layers
        if progress is not None:
            progress.setLabelText(trans.string('Splash', 1))
            progress.setValue(5)
        if app.splashscrn is not None:
            updateSplash(trans.string('Splash', 1), 5)

        self.layers = [[], [], []]

        if L0 is not None:
            self.LoadLayer(0, L0)
        if L1 is not None:
            self.LoadLayer(1, L1)
        if L2 is not None:
            self.LoadLayer(2, L2)

        # Delete self.blocks
        #del self.blocks

        return True

    def save(self):
        """
        Save the area back to a file
        """
        # Prepare this first because otherwise the game refuses to load some sprites
        self.SortSpritesByZone()

        # We don't parse blocks 4, 11, 12, 13, 14.
        # We can create the rest manually.
        #self.blocks = [None] * 17
        #self.blocks[3] = b'\0\0\0\0\0\0\0\0'
        # Other known values for block 4 in NSMBW: 0000 0002 0042 0000,
        #                     0000 0002 0002 0000, 0000 0003 0003 0000
        #self.blocks[5] = b'\0\0\xFF\xFF\xFF\xFF\0\0\0\0\0\0\0\0\0\0\0\0\0\0' # always this
        #self.blocks[11] = b'' # never used
        #self.blocks[12] = b'' # never used
        #self.blocks[13] = b'' # paths
        #self.blocks[14] = b'' # path nodes
        #self.blocks[15] = b'' # progress paths
        #self.blocks[16] = b'' # progress path nodes

        # Save each block
        self.SaveTilesetNames() # block 1
        #self.SaveOptions() # block 2
        self.SaveEntrances() # block 7
        self.SaveSprites() # block 8
        self.SaveLoadedSprites() # block 9
        #self.SaveZones() # block 10 (and 3, 5 and 6)
        self.SaveLocations() # block 11
        #self.SavePaths() # blocks 14 and 15
        #self.SaveProgPaths() # blocks 16 and 17

        # Save the metadata
        rdata = bytearray(self.Metadata.save())
        if len(rdata) % 4 != 0:
           for i in range(4 - (len(rdata) % 4)):
               rdata.append(0)
        rdata = b''#bytes(rdata)

        # Save the main course file
        # We'll be passing over the blocks array two times.
        # Using bytearray here because it offers mutable bytes
        # and works directly with struct.pack_into(), so it's a
        # win-win situation
        FileLength = (len(self.blocks) * 8) + len(rdata)
        for block in self.blocks:
            FileLength += len(block)

        course = bytearray()
        for i in range(FileLength): course.append(0)
        saveblock = struct.Struct('>II')

        HeaderOffset = 0
        FileOffset = (len(self.blocks) * 8) + len(rdata)
        for block in self.blocks:
            blocksize = len(block)
            saveblock.pack_into(course, HeaderOffset, FileOffset, blocksize)
            if blocksize > 0:
                course[FileOffset:FileOffset + blocksize] = block
            HeaderOffset += 8
            FileOffset += blocksize

        # Return stuff
        return (
            bytes(course),
            self.SaveLayer(0),
            self.SaveLayer(1),
            self.SaveLayer(2),
            )


    def RemoveFromLayer(self, obj):
        """
        Removes a specific object from the level and updates Z-indices accordingly
        """
        layer = self.layers[obj.layer]
        idx = layer.index(obj)
        del layer[idx]
        for i in range(idx,len(layer)):
            upd = layer[i]
            upd.setZValue(upd.zValue() - 1)

    def SortSpritesByZone(self):
        """
        Sorts the sprite list by zone ID so it will work in-game
        """

        split = {}
        zones = []

        f_MapPositionToZoneID = MapPositionToZoneID
        zonelist = self.zones

        for sprite in self.sprites:
            zone = f_MapPositionToZoneID(zonelist, sprite.objx, sprite.objy)
            sprite.zoneID = zone
            if not zone in split:
                split[zone] = []
                zones.append(zone)
            split[zone].append(sprite)

        newlist = []
        zones.sort()
        for z in zones:
            newlist += split[z]

        self.sprites = newlist


    def LoadReggieInfo(self, data):
        if (data is None) or (len(data) == 0):
            self.Metadata = Metadata()
            return

        try: self.Metadata = Metadata(data)
        except Exception: self.Metadata = Metadata() # fallback


class Area_NSMBU(AbstractParsedArea):
    """
    Class for a parsed NSMBU level area
    """
    def __init__(self):
        """
        Creates a completely new NSMBU area
        """
        # Default tileset names for NSMBU
        self.tileset0 = 'J_Kihon'
        self.tileset1 = 'M_Nohara_Onpu'
        self.tileset2 = ''
        self.tileset3 = ''

        super().__init__()

    def LoadBlocks(self, course):
        """
        Loads self.blocks from the course file
        """
        self.blocks = [None] * 15
        getblock = struct.Struct('>II')
        for i in range(15):
            data = getblock.unpack_from(course, i * 8)
            if data[1] == 0:
                self.blocks[i] = b''
            else:
                self.blocks[i] = course[data[0]:data[0] + data[1]]

        self.block1pos = getblock.unpack_from(course, 0)


    def LoadTilesetNames(self):
        """
        Loads block 1, the tileset names
        """
        data = struct.unpack_from('32s32s32s32s', self.blocks[0])
        self.tileset0 = data[0].strip(b'\0').decode('latin-1')
        self.tileset1 = data[1].strip(b'\0').decode('latin-1')
        self.tileset2 = data[2].strip(b'\0').decode('latin-1')
        self.tileset3 = data[3].strip(b'\0').decode('latin-1')


    def LoadOptions(self):
        """
        Loads block 2, the general options
        """
        optdata = self.blocks[1]
        optstruct = struct.Struct('>IxxxxHhLBBBx')
        offset = 0
        data = optstruct.unpack_from(optdata,offset)
        self.defEvents, self.wrapFlag, self.timeLimit, self.unk1, self.startEntrance, self.unk2, self.unk3 = data


    def LoadEntrances(self):
        """
        Loads block 7, the entrances
        """
        entdata = self.blocks[6]
        entcount = len(entdata) // 24
        entstruct = struct.Struct('>HHxBxxBBBBBBxBxBBBBBBx')
        offset = 0
        entrances = []
        for i in range(entcount):
            data = entstruct.unpack_from(entdata,offset)
            entrances.append(EntranceItem(*data))
            offset += 24
        self.entrances = entrances


    def LoadSprites(self):
        """
        Loads block 8, the sprites
        """
        spritedata = self.blocks[7]
        sprcount = len(spritedata) // 24
        sprstruct = struct.Struct('>HHH10sxx2sxxxx')
        offset = 0
        sprites = []

        unpack = sprstruct.unpack_from
        append = sprites.append
        obj = SpriteItem
        for i in range(sprcount):
            data = unpack(spritedata, offset)
            append(obj(data[0], data[1], data[2], data[3] + data[4]))
            offset += 24
        self.sprites = sprites


    def LoadZones(self):
        """
        Loads blocks 3, 5, 6 and 10 - the bounding, background and zone data
        """

        # Block 3 - bounding data
        bdngdata = self.blocks[2]
        count = len(bdngdata) // 28
        bdngstruct = struct.Struct('>llllHHxxxxxxxx')
        offset = 0
        bounding = []
        for i in range(count):
            datab = bdngstruct.unpack_from(bdngdata,offset)
            bounding.append([datab[0], datab[1], datab[2], datab[3], datab[4], datab[5]])
            offset += 28
        self.bounding = bounding

        # Block 5 - Bg data
        bgData = self.blocks[4]
        bgCount = len(bgData) // 28
        offset = 0
        bg = {}
        for i in range(bgCount):
            newBg = Background_NSMBU()
            bgId = newBg.loadFrom(bgData[offset:offset + 28])
            bg[bgId] = newBg
            offset += 28
        self.bg = bg

        # Block 10 - zone data
        zonedata = self.blocks[9]
        zonestruct = struct.Struct('>hhhhHxxBBxxxxxxBBBxBxxx')
        count = len(zonedata) // 28
        offset = 0
        zones = []
        for i in range(count):
            dataz = zonestruct.unpack_from(zonedata, offset)

            # Find the proper bounding
            boundObj = None
            id = dataz[6]
            for checkb in self.bounding:
                if checkb[4] == id: boundObj = checkb

            # Find the proper bg
            bgObj = None
            if dataz[10] in bg:
                bgObj = bg[dataz[10]]

            zones.append(ZoneItem(dataz[0], dataz[1], dataz[2], dataz[3], dataz[4], dataz[5], dataz[6], dataz[7], dataz[8], dataz[9], dataz[10], boundObj, bgObj, i))
            offset += 28
        self.zones = zones


    def LoadLocations(self):
        """
        Loads block 11, the locations
        """
        locdata = self.blocks[10]
        locstruct = struct.Struct('>HHHHBxxx')
        count = len(locdata) // 12
        offset = 0
        locations = []
        for i in range(count):
            data = locstruct.unpack_from(locdata, offset)
            locations.append(LocationItem(data[0], data[1], data[2], data[3], data[4]))
            offset += 12
        self.locations = locations


    def LoadLayer(self, idx, layerdata):
        """
        Loads a specific object layer from a bytes object
        """
        objcount = len(layerdata) // 16
        objstruct = struct.Struct('>HhhHHB')
        offset = 0
        z = (2 - idx) * 8192

        layer = self.layers[idx]
        append = layer.append
        unpack = objstruct.unpack_from
        for i in range(objcount):
            data = unpack(layerdata, offset)
            x, y = data[1], data[2]
            append(ObjectItem(data[0] >> 12, data[0] & 4095, idx, x, y, data[3], data[4], z, data[5]))
            z += 1
            offset += 16


    def LoadPaths(self):
        """
        Loads block 12, the paths
        """
        # Path struct: <BxHHH
        pathdata = self.blocks[13]
        pathcount = len(pathdata) // 12
        pathstruct = struct.Struct('>BxHHH')
        offset = 0
        unpack = pathstruct.unpack_from
        pathinfo = []
        paths = []
        for i in range(pathcount):
            data = unpack(pathdata, offset)
            nodes = self.LoadPathNodes(data[1], data[2])
            add2p = {'id': int(data[0]),
                     'nodes': [],
                     'loops': data[3] == 2,
                     }
            for node in nodes:
                add2p['nodes'].append(node)
            pathinfo.append(add2p)


            offset += 12

        for i in range(pathcount):
            xpi = pathinfo[i]
            for j, xpj in enumerate(xpi['nodes']):
                paths.append(PathItem(xpj['x'], xpj['y'], xpi, xpj))


        self.pathdata = pathinfo
        self.paths = paths


    def LoadPathNodes(self, startindex, count):
        """
        Loads block 13, the path nodes
        """
        # PathNode struct: <HHffhxx
        ret = []
        nodedata = self.blocks[14]
        nodestruct = struct.Struct('>HHffhxx')
        offset = startindex * 20
        unpack = nodestruct.unpack_from
        for i in range(count):
            data = unpack(nodedata, offset)
            ret.append({'x': int(data[0]),
                        'y': int(data[1]),
                        'speed': float(data[2]),
                        'accel': float(data[3]),
                        'delay': int(data[4]),
                        #'id' : i
            })
            offset += 20
        return ret

    def LoadProgPaths(self):
        """
        Loads block 16, the progress paths
        """
        return
        # Progress path struct: <HHHxxx?xx
        progpathdata = self.blocks[15]
        progpathcount = len(progpathdata) // 12
        progpathstruct = struct.Struct('>HHHxxx?xx')
        offset = 0
        unpack = progpathstruct.unpack_from
        progpathinfo = []
        progpaths = []
        for i in range(progpathcount):
            data = unpack(progpathdata, offset)
            nodes = self.LoadProgPathNodes(data[1], data[2])
            add2p = {'id': data[0],
                     'nodes': [],
                     'altpath': data[3],
                     }
            for node in nodes:
                add2p['nodes'].append(node)
            progpathinfo.append(add2p)

            offset += 12

        for i in range(progpathcount):
            xpi = progpathinfo[i]
            for j, xpj in enumerate(xpi['nodes']):
                progpaths.append(ProgressPathItem(xpj['x'], xpj['y'], xpi, xpj))


        self.progpathdata = progpathinfo
        self.progpaths = progpaths


    def LoadProgPathNodes(self, startindex, count):
        """
        Loads block 17, the progress path nodes
        """
        return
        ret = []
        nodedata = self.blocks[16]
        nodestruct = struct.Struct('>hh16x')
        offset = startindex * 20
        unpack = nodestruct.unpack_from
        for i in range(count):
            data = unpack(nodedata, offset)
            ret.append({'x': int(data[0]),
                        'y': int(data[1]),
            })
            offset += 20
        return ret


    def LoadComments(self):
        """
        Loads the comments from self.Metadata
        """
        self.comments = []
        b = self.Metadata.binData('InLevelComments_A%d' % self.areanum)
        if b is None: return
        idx = 0
        while idx < len(b):
            xpos  = b[idx]   << 24
            xpos |= b[idx+1] << 16
            xpos |= b[idx+2] << 8
            xpos |= b[idx+3]
            idx += 4
            ypos  = b[idx]   << 24
            ypos |= b[idx+1] << 16
            ypos |= b[idx+2] << 8
            ypos |= b[idx+3]
            idx += 4
            tlen  = b[idx]   << 24
            tlen |= b[idx+1] << 16
            tlen |= b[idx+2] << 8
            tlen |= b[idx+3]
            idx += 4
            s = ''
            for char in range(tlen):
                s += chr(b[idx])
                idx += 1

            com = CommentItem(xpos, ypos, s)
            com.listitem = QtWidgets.QListWidgetItem()

            self.comments.append(com)

            com.UpdateListItem()


    def SaveTilesetNames(self):
        """
        Saves the tileset names back to block 1
        """
        self.blocks[0] = ''.join([self.tileset0.ljust(32, '\0'), self.tileset1.ljust(32, '\0'), self.tileset2.ljust(32, '\0'), self.tileset3.ljust(32, '\0')]).encode('latin-1')


    def SaveOptions(self):
        """
        Saves block 2, the general options
        """
        optstruct = struct.Struct('>IxxxxHhLBBBx')
        buffer = bytearray(20)
        optstruct.pack_into(buffer, 0, self.defEvents, self.wrapFlag, self.timeLimit, self.unk1, self.startEntrance, self.unk2, self.unk3)
        self.blocks[1] = bytes(buffer)


    def SaveLayer(self, idx):
        """
        Saves an object layer to a bytes object
        """
        layer = self.layers[idx]
        if not layer: return None

        offset = 0
        objstruct = struct.Struct('>HhhHHB')
        buffer = bytearray((len(layer) * 16) + 2)
        f_int = int
        for obj in layer:
            objstruct.pack_into(buffer, offset, f_int((obj.tileset << 12) | obj.type), f_int(obj.objx), f_int(obj.objy), f_int(obj.width), f_int(obj.height), f_int(obj.contents))
            offset += 16
        buffer[offset] = 0xFF
        buffer[offset + 1] = 0xFF
        return bytes(buffer)


    def SaveEntrances(self):
        """
        Saves the entrances back to block 7
        """
        offset = 0
        entstruct = struct.Struct('>HHxBxxBBBBBBxBxBBBBBBx')
        buffer = bytearray(len(self.entrances) * 24)
        zonelist = self.zones
        for entrance in self.entrances:
            zoneID = MapPositionToZoneID(zonelist, entrance.objx, entrance.objy)
            entstruct.pack_into(buffer, offset, int(entrance.objx), int(entrance.objy), int(entrance.unk05), int(entrance.entid), int(entrance.destarea), int(entrance.destentrance), int(entrance.enttype), int(entrance.unk0C), zoneID, int(entrance.unk0F), int(entrance.entsettings), int(entrance.unk12), int(entrance.unk13), int(entrance.unk14), int(entrance.unk15), int(entrance.unk16))
            offset += 24
        self.blocks[6] = bytes(buffer)


    def SavePaths(self):
        """
        Saves the paths back to block 13
        """
        pathstruct = struct.Struct('>BxHHH')
        nodecount = 0
        for path in self.pathdata:
            nodecount += len(path['nodes'])
        nodebuffer = bytearray(nodecount * 20)
        nodeoffset = 0
        nodeindex = 0
        offset = 0
        buffer = bytearray(len(self.pathdata) * 12)

        for path in self.pathdata:
            if(len(path['nodes']) < 1): continue
            self.WritePathNodes(nodebuffer, nodeoffset, path['nodes'])

            pathstruct.pack_into(buffer, offset, int(path['id']), int(nodeindex), int(len(path['nodes'])), 2 if path['loops'] else 0)
            offset += 12
            nodeoffset += len(path['nodes']) * 20
            nodeindex += len(path['nodes'])

        self.blocks[13] = bytes(buffer)
        self.blocks[14] = bytes(nodebuffer)


    def WritePathNodes(self, buffer, offst, nodes):
        """
        Writes the pathnode data to the block 14 bytearray
        """
        offset = int(offst)

        nodestruct = struct.Struct('>HHffhxxxxxx')
        for node in nodes:
            nodestruct.pack_into(buffer, offset, int(node['x']), int(node['y']), float(node['speed']), float(node['accel']), int(node['delay']))
            offset += 20


    def SaveProgPaths(self):
        """
        Saves the progress paths back to block 16
        """
        pathstruct = struct.Struct('>HHHxxx?xx')
        nodecount = 0
        for path in self.progpathdata:
            nodecount += len(path['nodes'])
        nodebuffer = bytearray(nodecount * 20)
        nodeoffset = 0
        nodeindex = 0
        offset = 0
        buffer = bytearray(len(self.progpathdata) * 12)

        for path in self.progpathdata:
            if(len(path['nodes']) < 1): continue
            self.WriteProgPathNodes(nodebuffer, nodeoffset, path['nodes'])

            pathstruct.pack_into(buffer, offset, int(path['id']), int(nodeindex), int(len(path['nodes'])), path['altpath'])
            offset += 12
            nodeoffset += len(path['nodes']) * 20
            nodeindex += len(path['nodes'])

        self.blocks[15] = bytes(buffer)
        self.blocks[16] = bytes(nodebuffer)


    def WriteProgPathNodes(self, buffer, offst, nodes):
        """
        Writes the progpathnode data to the block 17 bytearray
        """
        offset = int(offst)

        nodestruct = struct.Struct('>hh16x')
        for node in nodes:
            nodestruct.pack_into(buffer, offset, int(node['x']), int(node['y']))
            offset += 20


    def SaveSprites(self):
        """
        Saves the sprites back to block 8
        """
        offset = 0
        sprstruct = struct.Struct('>HHH10sH2sxxxx')
        buffer = bytearray((len(self.sprites) * 24) + 4)
        f_int = int
        for sprite in self.sprites:
            try:
                sprstruct.pack_into(buffer, offset, f_int(sprite.type), f_int(sprite.objx), f_int(sprite.objy), sprite.spritedata[:10], sprite.zoneID, sprite.spritedata[10:])
            except struct.error:
                # Hopefully this will solve the mysterious bug, and will
                # soon no longer be necessary.
                raise ValueError('SaveSprites struct.error. Current sprite data dump:\n' + \
                    str(offset) + '\n' + \
                    str(sprite.type) + '\n' + \
                    str(sprite.objx) + '\n' + \
                    str(sprite.objy) + '\n' + \
                    str(sprite.spritedata[:6]) + '\n' + \
                    str(sprite.zoneID) + '\n' + \
                    str(bytes([sprite.spritedata[7],])) + '\n',
                    )
            offset += 24
        buffer[offset] = 0xFF
        buffer[offset + 1] = 0xFF
        buffer[offset + 2] = 0xFF
        buffer[offset + 3] = 0xFF
        self.blocks[7] = bytes(buffer)


    def SaveLoadedSprites(self):
        """
        Saves the list of loaded sprites back to block 9
        """
        ls = []
        for sprite in self.sprites:
            if sprite.type not in ls: ls.append(sprite.type)
        ls.sort()

        offset = 0
        sprstruct = struct.Struct('>Hxx')
        buffer = bytearray(len(ls) * 4)
        for s in ls:
            sprstruct.pack_into(buffer, offset, int(s))
            offset += 4
        self.blocks[8] = bytes(buffer)


    def SaveZones(self):
        """
        Saves blocks 10, 3, 5 and 6, the zone data, boundings, bgA and bgB data respectively
        """
        bdngstruct = struct.Struct('>llllxBxBxxxx')
        bgAstruct = struct.Struct('>xBhhhhHHHxxxBxxxx')
        bgBstruct = struct.Struct('>xBhhhhHHHxxxBxxxx')
        zonestruct = struct.Struct('>HHHHHHBBBBxBBBBxBB')
        offset = 0
        i = 0
        zcount = len(Area.zones)
        buffer2 = bytearray(24 * zcount)
        buffer4 = bytearray(24 * zcount)
        buffer5 = bytearray(24 * zcount)
        buffer9 = bytearray(24 * zcount)
        for z in Area.zones:
            bdngstruct.pack_into(buffer2, offset, z.yupperbound, z.ylowerbound, z.yupperbound2, z.ylowerbound2, i, 0xF)
            bgAstruct.pack_into(buffer4, offset, i, z.XscrollA, z.YscrollA, z.YpositionA, z.XpositionA, z.bg1A, z.bg2A, z.bg3A, z.ZoomA)
            bgBstruct.pack_into(buffer5, offset, i, z.XscrollB, z.YscrollB, z.YpositionB, z.XpositionB, z.bg1B, z.bg2B, z.bg3B, z.ZoomB)
            zonestruct.pack_into(buffer9, offset, z.objx, z.objy, z.width, z.height, z.modeldark, z.terraindark, i, i, z.cammode, z.camzoom, z.visibility, i, i, z.camtrack, z.music, z.sfxmod)
            offset += 24
            i += 1

        self.blocks[2] = bytes(buffer2)
        self.blocks[4] = bytes(buffer4)
        self.blocks[5] = bytes(buffer5)
        self.blocks[9] = bytes(buffer9)


    def SaveLocations(self):
        """
        Saves block 11, the location data
        """
        locstruct = struct.Struct('>HHHHBxxx')
        offset = 0
        zcount = len(Area.locations)
        buffer = bytearray(12 * zcount)

        for z in Area.locations:
            locstruct.pack_into(buffer, offset, int(z.objx), int(z.objy), int(z.width), int(z.height), int(z.id))
            offset += 12

        self.blocks[10] = bytes(buffer)


class Metadata():
    """
    Class for the new level metadata system
    """
    # This new system is much more useful and flexible than the old
    # system, but is incompatible with older versions of Reggie.
    # They will fail to understand the data, and skip it like it
    # doesn't exist. The new system is written with forward-compatibility
    # in mind. Thus, when newer versions of Reggie are created
    # with new metadata values, they will be easily able to add to
    # the existing ones. In addition, the metadata system is lossless,
    # so unrecognized values will be preserved when you open and save.

    # Type values:
    # 0 = binary
    # 1 = string
    # 2+ = undefined as of now - future Reggies can use them
    # Theoretical limit to type values is 4,294,967,296

    def __init__(self, data=None):
        """
        Creates a metadata object with the data given
        """
        self.DataDict = {}
        if data is None: return

        if data[0:4] != b'MD2_':
            # This is old-style metadata - convert it
            try:
                strdata = ''
                for d in data: strdata += chr(d)
                level_info = pickle.loads(strdata)
                for k, v in level_info.iteritems():
                    self.setStrData(k, v)
            except Exception: pass
            if ('Website' not in self.DataDict) and ('Webpage' in self.DataDict):
                self.DataDict['Website'] = self.DataDict['Webpage']
            return

        # Iterate through the data
        idx = 4
        while idx < len(data) - 4:

            # Read the next (first) four bytes - the key length
            rawKeyLen = data[idx:idx+4]
            idx += 4

            keyLen = (rawKeyLen[0] << 24) | (rawKeyLen[1] << 16) | (rawKeyLen[2] << 8) | rawKeyLen[3]

            # Read the next (key length) bytes - the key (as a str)
            rawKey = data[idx:idx+keyLen]
            idx += keyLen

            key = ''
            for b in rawKey: key += chr(b)

            # Read the next four bytes - the number of type entries
            rawTypeEntries = data[idx:idx+4]
            idx += 4

            typeEntries = (rawTypeEntries[0] << 24) | (rawTypeEntries[1] << 16) | (rawTypeEntries[2] << 8) | rawTypeEntries[3]

            # Iterate through each type entry
            typeData = {}
            for entry in range(typeEntries):

                # Read the next four bytes - the type
                rawType = data[idx:idx+4]
                idx += 4

                type = (rawType[0] << 24) | (rawType[1] << 16) | (rawType[2] << 8) | rawType[3]

                # Read the next four bytes - the data length
                rawDataLen = data[idx:idx+4]
                idx += 4

                dataLen = (rawDataLen[0] << 24) | (rawDataLen[1] << 16) | (rawDataLen[2] << 8) | rawDataLen[3]

                # Read the next (data length) bytes - the data (as bytes)
                entryData = data[idx:idx+dataLen]
                idx += dataLen

                # Add it to typeData
                self.setOtherData(key, type, entryData)


    def binData(self, key):
        """
        Returns the binary data associated with key
        """
        return self.otherData(key, 0)

    def strData(self, key):
        """
        Returns the string data associated with key
        """
        data = self.otherData(key, 1)
        if data is None: return
        s = ''
        for d in data: s += chr(d)
        return s

    def otherData(self, key, type):
        """
        Returns unknown data, with the given type value, associated with key (as binary data)
        """
        if key not in self.DataDict: return
        if type not in self.DataDict[key]: return
        return self.DataDict[key][type]

    def setBinData(self, key, value):
        """
        Sets binary data, overwriting any existing binary data with that key
        """
        self.setOtherData(key, 0, value)

    def setStrData(self, key, value):
        """
        Sets string data, overwriting any existing string data with that key
        """
        data = []
        for char in value: data.append(ord(char))
        self.setOtherData(key, 1, data)

    def setOtherData(self, key, type, value):
        """
        Sets other (binary) data, overwriting any existing data with that key and type
        """
        if key not in self.DataDict: self.DataDict[key] = {}
        self.DataDict[key][type] = value

    def save(self):
        """
        Returns a bytes object that can later be loaded from
        """

        # Sort self.DataDict
        dataDictSorted = []
        for dataKey in self.DataDict: dataDictSorted.append((dataKey, self.DataDict[dataKey]))
        dataDictSorted.sort(key=lambda entry: entry[0])

        data = []

        # Add 'MD2_'
        data.append(ord('M'))
        data.append(ord('D'))
        data.append(ord('2'))
        data.append(ord('_'))

        # Iterate through self.DataDict
        for dataKey, types in dataDictSorted:

            # Add the key length (4 bytes)
            keyLen = len(dataKey)
            data.append(keyLen >> 24)
            data.append((keyLen >> 16) & 0xFF)
            data.append((keyLen >> 8) & 0xFF)
            data.append(keyLen & 0xFF)

            # Add the key (key length bytes)
            for char in dataKey: data.append(ord(char))

            # Sort the types
            typesSorted = []
            for type in types: typesSorted.append((type, types[type]))
            typesSorted.sort(key=lambda entry: entry[0])

            # Add the number of types (4 bytes)
            typeNum = len(typesSorted)
            data.append(typeNum >> 24)
            data.append((typeNum >> 16) & 0xFF)
            data.append((typeNum >> 8) & 0xFF)
            data.append(typeNum & 0xFF)

            # Iterate through typesSorted
            for type, typeData in typesSorted:

                # Add the type (4 bytes)
                data.append(type >> 24)
                data.append((type >> 16) & 0xFF)
                data.append((type >> 8) & 0xFF)
                data.append(type & 0xFF)

                # Add the data length (4 bytes)
                dataLen = len(typeData)
                data.append(dataLen >> 24)
                data.append((dataLen >> 16) & 0xFF)
                data.append((dataLen >> 8) & 0xFF)
                data.append(dataLen & 0xFF)

                # Add the data (data length bytes)
                for d in typeData: data.append(d)

        return data        
