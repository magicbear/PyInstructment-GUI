import sys
from PyQt5.QtCore import (Qt, QEvent, QTimer)
from PyQt5.QtWidgets import (QWidget, QLCDNumber, QSlider, QVBoxLayout, QApplication, QSizePolicy)
from PyQt5.QtWidgets import *
from PyQt5.QtCore import pyqtSlot, pyqtSignal
from PyQt5.QtGui import QColor
from PyQt5 import *
import time
import traceback

class QEditableLCD(QFrame):
    valueChanged = pyqtSignal([str],[float])
    debugEvent = False

    def __init__(self, number, parent, color = None, baseStyle = None, textStyle = None, size = None):
        # obj = super(self.__class__, self).__init__(number, parent)
        obj = super(self.__class__, self).__init__(parent)
        self.obj_number = QLCDNumber(number, self)
        if color is not None:
            self.obj_number.setSegmentStyle(QLCDNumber.Flat)
            palette = self.obj_number.palette()
            palette.setColor(palette.WindowText, color)
            self.obj_number.setPalette(palette)

        if baseStyle is not None:
            self.baseStyle = baseStyle
            self.obj_number.setStyleSheet(baseStyle)
        color = self.obj_number.palette().color(self.obj_number.palette().WindowText)

        style = ""
        if self.baseStyle is not None:
            style = self.baseStyle
        if textStyle is not None:
            style += textStyle
        style += "color: rgb(%d, %d, %d); selection-color: rgb(%d, %d, %d);" % (color.red(), color.green(), color.blue(), color.red(), color.green(), color.blue())
        self.edit = QLineEdit(self)
        self.size = size
        if size is not None:
            self.obj_number.setFixedSize(size[0], size[1])
            self.setFixedSize(size[0], size[1])
            self.edit.setFixedSize(size[0], size[1])
        else:
            self.setFixedSize(self.obj_number.sizeHint().width(), self.obj_number.sizeHint().height())
            self.edit.setFixedSize(self.obj_number.sizeHint().width(), self.obj_number.sizeHint().height())
        self.edit.setAlignment(Qt.AlignRight)
        self.edit.setStyleSheet(style)
        self.edit.hide()
        self.obj_number.installEventFilter(self)
        self.edit.installEventFilter(self)

    def eventFilter(self, obj, event):
        if self.debugEvent:
            evtType = str(event.type())
            if event.type() == 18: evtType = "Hide"
            elif event.type() == 27: evtType = "HideToParent"
            elif event.type() == 12: evtType = "Paint"
            elif event.type() == 25: evtType = "WindowDeactivate"
            elif event.type() == 5: evtType = "MouseMove"
            elif event.type() == 10: evtType = "Enter"
            elif event.type() == QEvent.Leave: evtType = "Leave"
            elif event.type() == QEvent.Show: evtType = "Show"
            elif event.type() == QEvent.ShowToParent: evtType = "ShowToParent"
            elif event.type() == QEvent.InputMethodQuery: evtType = "InputMethodQuery"
            elif event.type() == QEvent.FocusIn: evtType = "FocusIn"
            elif event.type() == QEvent.UpdateLater: evtType = "UpdateLater"
            elif event.type() == QEvent.UpdateRequest: evtType = "UpdateRequest"
            elif event.type() == QEvent.WindowActivate: evtType = "WindowActivate"
            elif event.type() == QEvent.WindowDeactivate: evtType = "WindowDeactivate"
            elif event.type() == QEvent.FocusOut: evtType = "FocusOut"
            if event.type() in [5]:
                return  super(self.__class__, self).eventFilter(obj, event)
            print("%s -> %s" % ( "QLCDNumber" if obj is self.obj_number  else "QLineEdit", evtType))
        # if event.type()
        if event.type() == QEvent.Enter and obj in [self.obj_number] and self.isEnabled() == True:
            # 
            rc = super(self.__class__, self).eventFilter(obj, event)
            if self.receivers(self.valueChanged[str]) == 0 and self.receivers(self.valueChanged[float]) == 0:
                return rc
            self.obj_number.hide()
            self.edit.show()
            self.edit.setText(str(self.obj_number.value()))
            self.edit.setFocus()
            self.edit.selectAll()
            return rc
        elif obj in [self.edit]:
            if event.type() == QEvent.Leave or event.type() == QEvent.FocusOut:
                rc = super(self.__class__, self).eventFilter(obj, event)
                self.edit.hide()
                self.obj_number.show()
                return rc
            elif event.type() == QEvent.KeyPress and (event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter):
                try:
                    #  self.edit.text()
                    if self.receivers(self.valueChanged[str]) > 0:
                        self.valueChanged[str].emit(self.edit.text())
                    if self.receivers(self.valueChanged[float]) > 0:
                        try:
                            self.valueChanged[float].emit(float(self.edit.text()))
                        except ValueError as e:
                            QMessageBox.warning(None, "Warning", "Input invalid")
                    obj.selectAll()
                except Exception as e:
                    QMessageBox.critical(None,"Error", "<html>A critical error has occured.<br /><br/> %s: <b>%s</b><br /><br />Traceback:<pre>%s</pre><br/><br/></html>" % (e.__class__.__name__, e, '<br />'.join(traceback.format_tb(e.__traceback__))))
        return super(self.__class__, self).eventFilter(obj, event)

    def display(self, str):
        self.edit.setText(str)
        if not self.edit.hasFocus():
            self.edit.hide()
            self.obj_number.show()
        self.obj_number.display(str)
        # self.repaint()
