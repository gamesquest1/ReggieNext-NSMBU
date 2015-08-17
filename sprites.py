#!/usr/bin/python
# -*- coding: latin-1 -*-

# Reggie! - New Super Mario Bros. Wii Level Editor
# Version Next Milestone 2 Alpha 4
# Copyright (C) 2009-2014 Treeki, Tempus, angelsl, JasonP27, Kamek64,
# MalStar1000, RoadrunnerWMC

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



# sprites.py
# Contains code to render NSMBU sprite images
# not even close to done...need to do quite a few


################################################################
################################################################

# Imports

from PyQt5 import QtCore, QtGui
Qt = QtCore.Qt


import spritelib as SLib
ImageCache = SLib.ImageCache


################################################################
################################################################


# ...holy shit this game is complex

class SpriteImage_Block(SLib.SpriteImage): # 59, 60
    def __init__(self, parent, scale=1.5):
        super().__init__(parent, scale)
        self.spritebox.shown = False

        self.tilenum = 1315
        self.contentsOverride = None

    def dataChanged(self):
        super().dataChanged()

        # SET CONTENTS
        # In the blocks.png file:
        # 0 = Empty, 1 = Coin, 2 = Mushroom, 3 = Fire Flower, 4 = Propeller, 5 = Penguin Suit,
        # 6 = Mini Shroom, 7 = Star, 8 = Continuous Star, 9 = Yoshi Egg, 10 = 10 Coins,
        # 11 = 1-up, 12 = Vine, 13 = Spring, 14 = Shroom/Coin, 15 = Ice Flower, 16 = Toad

        if self.contentsOverride is not None:
            contents = self.contentsOverride
        else:
            contents = self.parent.spritedata[5] & 0xF

        self.image = ImageCache['Blocks'][contents]


    def paint(self, painter):
        super().paint(painter)

        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        if self.tilenum < len(SLib.Tiles):
            painter.drawPixmap(0, 0, SLib.Tiles[self.tilenum].main)
        painter.drawPixmap(0, 0, self.image)

class SpriteImage_Goomba(SLib.SpriteImage_Static): # 0
    def __init__(self, parent):
        super().__init__(
            parent,
            4.75,
            ImageCache['Goomba'],
            (-.5, -4),
            )

    @staticmethod
    def loadImages():
        SLib.loadIfNotInImageCache('Goomba', 'goomba.png')

class SpriteImage_PipePiranhaUp(SLib.SpriteImage_Static): # 2
    def __init__(self, parent):
        super().__init__(
            parent,
            4.75,
            ImageCache['PipePiranhaUp'],
            (-0, -0),
            )

    @staticmethod
    def loadImages():
        SLib.loadIfNotInImageCache('PipePiranhaUp', 'piranha_pipe_up.png')        

class SpriteImage_KoopaTroopa(SLib.SpriteImage_StaticMultiple): # 19
    def __init__(self, parent, scale=6):
        super().__init__(parent, scale)
        self.offset = (-12, -12)

    @staticmethod
    def loadImages():
        SLib.loadIfNotInImageCache('KoopaG', 'koopa_green.png')
        SLib.loadIfNotInImageCache('KoopaR', 'koopa_red.png')

    def dataChanged(self):

        # shiz
        shellcolor = self.parent.spritedata[5] & 1 # just 2 values, so throw this

        if shellcolor == 0:
            self.image = ImageCache['KoopaG']
        else:
            self.image = ImageCache['KoopaR']
            
        super().dataChanged()  
     

class SpriteImage_StarCoin(SLib.SpriteImage_Static): # 45
    def __init__(self, parent):
        super().__init__(
            parent,
            10,
            ImageCache['StarCoin'],
            )

    @staticmethod
    def loadImages():
        SLib.loadIfNotInImageCache('StarCoin', 'starcoin.png')

class SpriteImage_MovementControlledStarCoin(SLib.SpriteImage_Static): # 48
    def __init__(self, parent):
        super().__init__(
            parent,
            10,
            ImageCache['MCStarCoin'],
            )

    @staticmethod
    def loadImages():
        SLib.loadIfNotInImageCache('MCStarCoin', 'starcoin.png')               

class SpriteImage_QBlock(SpriteImage_Block): # 59
    def __init__(self, parent):
        super().__init__(parent, 3.75)
        self.tilenum = 49

class SpriteImage_BrickBlock(SLib.SpriteImage_Static): # 60
    def __init__(self, parent):
        super().__init__(
            parent,
            3.75,
            ImageCache['BrickBlock'],
            )

    @staticmethod
    def loadImages():
        SLib.loadIfNotInImageCache('BrickBlock', 'brick_block.png')          

class SpriteImage_Coin(SLib.SpriteImage_Static): # 65
    def __init__(self, parent):
        super().__init__(
            parent,
            3.75, # native res (3.75*16=60)
            ImageCache['Coin'],
            )

class SpriteImage_MovementController(SLib.SpriteImage): # 70
    def __init__(self, parent):
        super().__init__(parent, 3.75)

        self.width = ((self.parent.spritedata[7] & 0xF) + 1) << 4
        self.aux.append(SLib.AuxiliaryTrackObject(parent, 60, SLib.AuxiliaryTrackObject.Vertical))


    def dataChanged(self):
        super().dataChanged()

        distance = self.parent.spritedata[5] >> 4
        self.aux[0].setSize(distance + 60)
        self.aux[0].setPos(0, 0)
        self.aux[0].update()        

class SpriteImage_MovingCoin(SLib.SpriteImage_Static): # 87
    def __init__(self, parent):
        super().__init__(
            parent,
            3.75,
            ImageCache['Coin'],
            ) 

class SpriteImage_PipeUp(SLib.SpriteImage): # 139
    def __init__(self, parent, scale=3.75):
        super().__init__(parent, scale)
        self.spritebox.shown = False
        self.parent.setZValue(24999)
        self.width = 32
        self.pipeHeight = 60
        self.hasTop = True

    @staticmethod
    def loadImages():
        if 'PipeTopGreen' not in ImageCache:
            for color in ('Green',):
                ImageCache['PipeTop%s' % color] = SLib.GetImg('pipe_%s_top.png' % color.lower())
                ImageCache['PipeMiddleV%s' % color] = SLib.GetImg('pipe_%s_middle.png' % color.lower())

    def dataChanged(self):
        super().dataChanged()

        rawheight = (self.parent.spritedata[5] & 0x0F) + 1
        rawtop = self.parent.spritedata[2] >> 4

        if rawtop == 0:
            self.hasTop = True
            self.pipeHeight = rawheight
        elif rawtop == 1:
            self.hasTop = True
            self.pipeHeight = rawheight + 1
        elif rawtop == 3:
            self.hasTop = False
            self.pipeHeight = rawheight
        else:
            self.hasTop = True
            self.pipeHeight = rawheight

        self.height = self.pipeHeight * 16
        self.yOffset = 16 - self.height


    def paint(self, painter):
        super().paint(painter)

        color = 'Green'
        if self.hasTop:
            painter.drawPixmap(0, 0, ImageCache['PipeTop%s' % color])
            painter.drawTiledPixmap(0, 60, 120, self.pipeHeight * 60 - 60, ImageCache['PipeMiddleV%s' % color])
        else:
            painter.drawTiledPixmap(0, 0, 120, self.pipeHeight * 60, ImageCache['PipeMiddleV%s' % color])

class SpriteImage_BubbleYoshi(SLib.SpriteImage_Static): # 143
    def __init__(self, parent):
        super().__init__(
            parent,
            3.75,
            ImageCache['BubbleYoshi'],
            )

    @staticmethod
    def loadImages():
        SLib.loadIfNotInImageCache('BubbleYoshi', 'babyyoshibubble.png')                 


class SpriteImage_CoinOutline(SLib.SpriteImage_StaticMultiple): # 158
    def __init__(self, parent):
        super().__init__(
            parent,
            3.75, # native res (3.75*16=60)
            ImageCache['CoinOutlineMultiplayer'],
            )

    @staticmethod
    def loadImages():
        SLib.loadIfNotInImageCache('CoinOutline', 'coin_outline.png')
        SLib.loadIfNotInImageCache('CoinOutlineMultiplayer', 'coin_outline_multiplayer.png')

    def dataChanged(self):
        multi = (self.parent.spritedata[2] >> 4) & 1
        self.image = ImageCache['CoinOutline' + ('Multiplayer' if multi else '')]
        super().dataChanged()

class SpriteImage_BalloonYoshi(SLib.SpriteImage_Static): # 224
    def __init__(self, parent):
        super().__init__(
            parent,
            3.75,
            ImageCache['BalloonYoshi'],
            )

    @staticmethod
    def loadImages():
        SLib.loadIfNotInImageCache('BalloonYoshi', 'balloonbabyyoshi.png')          

class SpriteImage_TileGod(SLib.SpriteImage): # 237
    def __init__(self, parent):
        super().__init__(parent, 3.75)
        self.aux.append(SLib.AuxiliaryRectOutline(parent, 0, 0))

    def dataChanged(self):
        super().dataChanged()

        width = self.parent.spritedata[8] & 0xF
        height = self.parent.spritedata[5] >> 4
        if width == 0: width = 1
        if height == 0: height = 1
        if width == 1 and height == 1:
            self.aux[0].setSize(0,0)
            return
        self.aux[0].setSize(width * 60, height * 60)

class SpriteImage_BubbleYoshi2(SLib.SpriteImage_Static): # 243
    def __init__(self, parent):
        super().__init__(
            parent,
            3.75,
            ImageCache['BubbleYoshi'],
            )

    @staticmethod
    def loadImages():
        SLib.loadIfNotInImageCache('BubbleYoshi', 'babyyoshibubble.png')          

class SpriteImage_Parabeetle(SLib.SpriteImage_Static): # 261
    def __init__(self, parent):
        super().__init__(
            parent,
            3.75,
            ImageCache['Parabeetle'],
            )

    @staticmethod
    def loadImages():
        SLib.loadIfNotInImageCache('Parabeetle', 'parabeetle.png')

class SpriteImage_SuperGuide(SLib.SpriteImage_Static): # 348
    def __init__(self, parent):
        super().__init__(
            parent,
            3.75,
            ImageCache['SuperGuide'],
            )

    @staticmethod
    def loadImages():
        SLib.loadIfNotInImageCache('SuperGuide', 'guide_block.png')          

class SpriteImage_GoldenYoshi(SLib.SpriteImage_Static): # 365
    def __init__(self, parent):
        super().__init__(
            parent,
            3.75,
            ImageCache['GoldenYoshi'],
            )

    @staticmethod
    def loadImages():
        SLib.loadIfNotInImageCache('GoldenYoshi', 'babyyoshiglowing.png')        

class SpriteImage_BonyBeetle(SLib.SpriteImage_Static): # 443
    def __init__(self, parent):
        super().__init__(
            parent,
            3.75,
            ImageCache['BonyBeetle'],
            )

    @staticmethod
    def loadImages():
        SLib.loadIfNotInImageCache('BonyBeetle', 'bony_beetle.png')

class SpriteImage_RotationControlledCoin(SLib.SpriteImage_Static): # 236
    def __init__(self, parent):
        super().__init__(
            parent,
            3.75,
            ImageCache['Coin'],
            )         

class SpriteImage_BoltControlledCoin(SLib.SpriteImage_Static): # 328
    def __init__(self, parent):
        super().__init__(
            parent,
            3.75,
            ImageCache['Coin'],
            )         


class SpriteImage_WaddleWing(SLib.SpriteImage_Static): # 481
    def __init__(self, parent):
        super().__init__(
            parent,
            4,
            ImageCache['Waddlewing'],
            (-1, -4),
            )

    @staticmethod
    def loadImages():
        SLib.loadIfNotInImageCache('Waddlewing', 'waddlewing.png')

class SpriteImage_BoltControlledMovingCoin(SLib.SpriteImage_Static): # 496
    def __init__(self, parent):
        super().__init__(
            parent,
            3.75,
            ImageCache['Coin'],
            )

class SpriteImage_MovingGrassPlatform(SLib.SpriteImage): # 499
    def __init__(self, parent):
        super().__init__(parent, 3.75)
        self.aux.append(SLib.AuxiliaryRectOutline(parent, 0, 0))

    def dataChanged(self):
        super().dataChanged()

        width = self.parent.spritedata[8] & 0xF
        height = self.parent.spritedata[9] & 0xF
        if width == 0: width = 1
        if height == 0: height = 1
        if width == 1 and height == 1:
            self.aux[0].setSize(0,0)
            return
        self.aux[0].setSize(width * 60, height * 60)        

################################################################
################################################################


ImageClasses = {
    0: SpriteImage_Goomba,
    59: SpriteImage_QBlock,
    #60: SpriteImage_BrickBlock,
    65: SpriteImage_Coin,
    87: SpriteImage_MovingCoin,
    139: SpriteImage_PipeUp,
    143: SpriteImage_BubbleYoshi,
    158: SpriteImage_CoinOutline,
    #224: SpriteImage_BalloonYoshi,
    237: SpriteImage_TileGod,
    243: SpriteImage_BubbleYoshi2,
    261: SpriteImage_Parabeetle,
    326: SpriteImage_RotationControlledCoin,
    328: SpriteImage_BoltControlledCoin,
    348: SpriteImage_SuperGuide,
    365: SpriteImage_GoldenYoshi,
    443: SpriteImage_BonyBeetle,
    481: SpriteImage_WaddleWing,
    496: SpriteImage_BoltControlledMovingCoin,
    499: SpriteImage_MovingGrassPlatform,
    }
