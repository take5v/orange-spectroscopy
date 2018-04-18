"""
Modified HistogramLUTItem from pyqtgraph
"""

from pyqtgraph.Qt import QtGui, QtCore
from pyqtgraph import functions as fn
from pyqtgraph.graphicsItems.GraphicsWidget import GraphicsWidget
from pyqtgraph.graphicsItems.ViewBox import *
from pyqtgraph.graphicsItems.GradientEditorItem import *
from pyqtgraph.graphicsItems.LinearRegionItem import *
from pyqtgraph.graphicsItems.PlotDataItem import *
from pyqtgraph.graphicsItems.AxisItem import *
from pyqtgraph.graphicsItems.GridItem import *
from pyqtgraph.Point import Point
import numpy as np

import weakref


__all__ = ['HistogramLUTItem']

class HistogramLUTItem(GraphicsWidget):

    sigLookupTableChanged = QtCore.Signal(object)
    sigLevelsChanged = QtCore.Signal(object)
    sigLevelChangeFinished = QtCore.Signal(object)

    def __init__(self, image=None, fillHistogram=True, rgbHistogram=False):
        GraphicsWidget.__init__(self)
        self.lut = None
        self.imageItem = lambda: None  # fake a dead weakref
        self.rgbHistogram = rgbHistogram

        self.layout = QtGui.QGraphicsGridLayout()
        self.setLayout(self.layout)
        self.layout.setContentsMargins(1, 1, 1, 1)
        self.layout.setSpacing(0)
        self.vb = ViewBox(parent=self)
        self.vb.setMaximumWidth(152)
        self.vb.setMinimumWidth(45)
        self.vb.setMouseEnabled(x=False, y=True)
        self.gradient = GradientEditorItem()
        #self.gradient = TickSliderItem()
        self.gradient.setOrientation('right')
        self.gradient.loadPreset('grey')
        self.regions = [
            LinearRegionItem([0, 1], 'horizontal', swapMode='block')
        ]
        for region in self.regions:
            region.setZValue(1000)
            self.vb.addItem(region)
            region.lines[0].addMarker('<|', 0.5)
            region.lines[1].addMarker('|>', 0.5)
            region.sigRegionChanged.connect(self.regionChanging)
            region.sigRegionChangeFinished.connect(self.regionChanged)

        self.region = self.regions[0]  # for backward compatibility.

        self.axis = AxisItem('right', linkView=self.vb, maxTickLength=-10, parent=self)
        self.layout.addItem(self.axis, 0, 2)
        self.layout.addItem(self.vb, 0, 0)
        self.layout.addItem(self.gradient, 0, 1)
        self.range = None
        self.gradient.setFlag(self.gradient.ItemStacksBehindParent)
        self.vb.setFlag(self.gradient.ItemStacksBehindParent)

        self.gradient.sigGradientChanged.connect(self.gradientChanged)
        self.vb.sigRangeChanged.connect(self.viewRangeChanged)
        plot = self.plot = PlotCurveItem(pen=(200, 200, 200, 100))

        plot.rotate(90)
        self.vb.addItem(plot)

        self.fillHistogram(fillHistogram)
        self._showRegions()

        self.vb.addItem(self.plot)
        self.autoHistogramRange()

        if image is not None:
            self.setImageItem(image)

    def fillHistogram(self, fill=True, level=0.0, color=(100, 100, 200)):
        plot = self.plot
        if fill:
            plot.setFillLevel(level)
            plot.setBrush(color)
        else:
            plot.setFillLevel(None)

    def paint(self, p, *args):
        pass
        #rgn = self.getLevels()
        #p1 = self.vb.mapFromViewToItem(self, Point(self.vb.viewRect().center().x(), rgn[0]))
        #gradRect = self.gradient.mapRectToParent(self.gradient.gradRect.rect())
        #p.drawLine(p1 + Point(0, 5), gradRect.bottomLeft())

    def setHistogramRange(self, mn, mx, padding=0.1):
        """Set the Y range on the histogram plot. This disables auto-scaling."""
        self.vb.enableAutoRange(self.vb.YAxis, False)
        self.vb.setYRange(mn, mx, padding)

    def autoHistogramRange(self):
        """Enable auto-scaling on the histogram plot."""
        self.vb.enableAutoRange(self.vb.XYAxes)

    def setImageItem(self, img):
        """Set an ImageItem to have its levels and LUT automatically controlled
        by this HistogramLUTItem.
        """
        self.imageItem = weakref.ref(img)
        img.sigImageChanged.connect(self.imageChanged)
        img.setLookupTable(self.getLookupTable)  ## send function pointer, not the result
        self.regionChanged()
        self.imageChanged(autoLevel=True)

    def viewRangeChanged(self):
        self.update()

    def gradientChanged(self):
        if self.imageItem() is not None:
            if self.gradient.isLookupTrivial():
                self.imageItem().setLookupTable(None)  # lambda x: x.astype(np.uint8))
            else:
                self.imageItem().setLookupTable(self.getLookupTable)  ## send function pointer, not the result

        self.lut = None
        self.sigLookupTableChanged.emit(self)

    def getLookupTable(self, img=None, n=None, alpha=None):
        """Return a lookup table from the color gradient defined by this
        HistogramLUTItem.
        """
        if n is None:
            if img.dtype == np.uint8:
                n = 256
            else:
                n = 512
        if self.lut is None:
            self.lut = self.gradient.getLookupTable(n, alpha=alpha)
        return self.lut

    def regionChanged(self):
        if self.imageItem() is not None:
            self.imageItem().setLevels(self.getLevels())
        self.sigLevelChangeFinished.emit(self)

    def regionChanging(self):
        if self.imageItem() is not None:
            self.imageItem().setLevels(self.getLevels())
        self.sigLevelsChanged.emit(self)
        self.update()

    def imageChanged(self, autoLevel=False, autoRange=False):
        if self.imageItem() is None:
            return

        self.plot.setVisible(True)
        # plot one histogram for all image data
        h = self.imageItem().getHistogram()
        if h[0] is None:
            return
        self.plot.setData(*h)
        if autoLevel:
            mn = h[0][0]
            mx = h[0][-1]
            self.region.setRegion([mn, mx])
        else:
            mn, mx = self.imageItem().levels
            self.region.setRegion([mn, mx])

    def getLevels(self):
        """Return the min and max levels.

        For rgba mode, this returns a list of the levels for each channel.
        """
        return self.region.getRegion()

    def setLevels(self, min=None, max=None, rgba=None):
        """Set the min/max (bright and dark) levels.

        Arguments may be *min* and *max* for single-channel data, or
        *rgba* = [(rmin, rmax), ...] for multi-channel data.
        """
        if min is None:
            min, max = rgba[0]
        assert None not in (min, max)
        self.region.setRegion((min, max))

    def _showRegions(self):
        for i in range(len(self.regions)):
            self.regions[i].setVisible(False)

        self.regions[0].setVisible(True)
        self.gradient.show()
