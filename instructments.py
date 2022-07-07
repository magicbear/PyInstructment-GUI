#coding:utf-8

import sys
from libs.itech import DCLoad
from PyQt5.QtCore import (Qt, QEvent, QTimer)
from PyQt5.QtWidgets import (QWidget, QLCDNumber, QSlider, QVBoxLayout, QApplication, QSizePolicy)
from PyQt5.QtWidgets import *
from PyQt5.QtCore import pyqtSlot
from PyQt5.QtGui import QColor, QIcon
import time

from itech import ITechLoad
from keithley2280S import Keithley2280S
from gwinstek_ASR2100 import GwinstekASR2100
from keysightE36313A import KeysightE36313A
import traceback


app = QApplication(sys.argv)
app.setWindowIcon(QIcon('logo.png'))
app.setApplicationDisplayName("Instructment")

tab_widget = QTabWidget()
tab_widget.setWindowTitle('Instructment Control Panel')
# tab_widget.addTab(keithley, "Keithley 2280S-32-6")
# tab_widget.show()

tab_dcsupply = QWidget()
vbox = QGridLayout()

tab_group_keithley = QGroupBox("KEITHLEY 2280S-32-6", tab_widget)
layout = QHBoxLayout()
tab_group_keithley.setLayout(layout)
keithley = Keithley2280S()
layout.addWidget(keithley)
keithley.modelChanged.connect(lambda x: tab_group_keithley.setTitle(x))
tab_group_keithley.setMinimumSize(keithley.minimumSize().width(),keithley.minimumSize().height())
vbox.addWidget(tab_group_keithley, 0, 0, 3, 1, Qt.AlignTop)

tab_group_itech = QGroupBox("ITECH IT8512C", tab_widget)
layout = QHBoxLayout()
tab_group_itech.setLayout(layout)
itech = ITechLoad()
layout.addWidget(itech)
itech.modelChanged.connect(lambda x: tab_group_itech.setTitle("ITECH "+x))
vbox.addWidget(tab_group_itech, 0, 1, 3, 1, Qt.AlignTop)

keysight_36313 = KeysightE36313A()
tab_group_keysight_36313 = QGroupBox("Keysight E36313A", tab_widget)
layout = QHBoxLayout()
tab_group_keysight_36313.setLayout(layout)
layout.addWidget(keysight_36313)
keysight_36313.modelChanged.connect(lambda x: tab_group_keysight_36313.setTitle(x))
tab_group_keysight_36313.setMinimumSize(keysight_36313.minimumSize().width(),keysight_36313.minimumSize().height())
vbox.addWidget(tab_group_keysight_36313, 0, 2, 2, 1, Qt.AlignTop)

# vbox.setColumnMinimumWidth(0,654)
# vbox.setColumnMinimumWidth(1,753)

tab_dcsupply.setLayout(vbox)

tab_widget.addTab(tab_dcsupply, "DC Supply")


tab_group_gwinstek = QGroupBox("Gwinstek ASR-2100", tab_widget)
gwinstek = GwinstekASR2100()
layout = QHBoxLayout()
tab_group_gwinstek.setLayout(layout)
layout.addWidget(gwinstek)
gwinstek.modelChanged.connect(lambda x: tab_group_gwinstek.setTitle(" ".join(x.split(",")[0:2])+" VER: "+x.split(",")[3]))
# vbox.addWidget(tab_group_gwinstek)
tab_widget.addTab(tab_group_gwinstek, "AC Supply")

# tab_widget.setLayout(vbox)
tab_widget.showMaximized()

def handle_exception(exc_type, exc_value, exc_traceback):
    if keithley is not None and keithley.dev is not None:
        keithley.on_open_click()
    if not exc_type is KeyboardInterrupt:
        QMessageBox.critical(None,"Error", "<html>A critical error has occured.<br /><br/> %s: <b>%s</b><br /><br />Traceback:<pre>%s</pre><br/><br/></html>" % (exc_type.__name__, exc_value, '<br />'.join(traceback.format_tb(exc_traceback))))
    sys.exit(1)

sys.excepthook = handle_exception

sys.exit(app.exec_())