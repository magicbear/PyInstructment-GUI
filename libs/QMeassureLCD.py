import sys
from PyQt5.QtCore import (Qt, QEvent, QTimer)
from PyQt5.QtWidgets import (QWidget, QLCDNumber, QSlider, QVBoxLayout, QApplication, QSizePolicy)
from PyQt5.QtWidgets import *
from PyQt5.QtCore import pyqtSlot, pyqtSignal
from PyQt5.QtGui import QColor
from PyQt5 import *
import time
import traceback

class QMeassureLCD(QGroupBox):
    def __init__(self, name, number, parent, color = None, groupStyle = "QGroupBox {padding: 5px; background-color: #222; color: #fff; border-radius: 3px; margin: 0} QGroupBox::title { margin-top: 0em; subcontrol-origin: padding; subcontrol-position: left top; }", lcdStyle = "background-color: #222; border: 0px ;", size = None, unit = None):
        # obj = super(self.__class__, self).__init__(number, parent)
        obj = super(self.__class__, self).__init__(name, parent)
        meas_layout = QHBoxLayout()
        meas_layout.setSpacing(0)
        self.setContentsMargins(0,0,0,0)
        self.obj_number = QLCDNumber(number, self)
        if color is not None:
            self.obj_number.setSegmentStyle(QLCDNumber.Flat)
            palette = self.obj_number.palette()
            palette.setColor(palette.WindowText, color)
            self.obj_number.setPalette(palette)

        if groupStyle is not None:
            self.setStyleSheet(groupStyle)

        if lcdStyle is not None:
            self.obj_number.setStyleSheet(lcdStyle)

        if size is not None:
            self.obj_number.setFixedSize(size[0], size[1])
            # self.setFixedSize(size[0], size[1])
        # else:
        #     self.setFixedSize(self.obj_number.sizeHint().width(), self.obj_number.sizeHint().height())

        meas_layout.addWidget(self.obj_number)
        if unit is not None:
            self.unit = QLabel(" %s" % (unit), self)
            self.unit.setAlignment(Qt.AlignCenter | Qt.AlignBottom)
            meas_layout.addWidget(self.unit)
        self.setLayout(meas_layout)

    def display(self, str):
        self.obj_number.display(str)
