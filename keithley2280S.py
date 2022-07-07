#coding:utf-8

import sys
from PyQt5.QtCore import (Qt, QEvent, QTimer)
from PyQt5.QtWidgets import (QWidget, QLCDNumber, QSlider, QVBoxLayout, QApplication, QSizePolicy)
from PyQt5.QtWidgets import *
from PyQt5.QtCore import pyqtSlot, pyqtSignal
from PyQt5.QtGui import QColor
from PyQt5 import *
import pyvisa as visa
import time
import traceback
from datetime import datetime
from libs.QEditableLCD import QEditableLCD
from libs.QMeassureLCD import QMeassureLCD

class Keithley2280S(QWidget):
    modelChanged = pyqtSignal(str)

    def __init__(self,parent=None):
        QWidget.__init__(self)

        self.rm = visa.ResourceManager(visa_library="@ivi")
        time.sleep(0.5)
        for i in range(0,10):
            try:
                # res = self.rm.list_resources()
                res = ['TCPIP::192.168.9.129::INSTR']
                break
            except Exception as e:
                self.rm = visa.ResourceManager(visa_library=R'C:\Program Files (x86)\IVI Foundation\VISA\Win64\Bin\kivisa32.dll')
                print("List Resource Failed")
                time.sleep(0.1)

        self.dev = None
        self.model = None
        self.mode = None
        self.initalizing = True
        self.output_enabled = True
        self.cur_pulse_enabled = False
        self.remote_enabled = False
        self.set_ocp = None
        self.set_ovp = None
        self.protection = None
        self.pause_query = False
        self.querying = False
        self.failed_read = 0
        self.log_file = None
        self.set_commands = {"voltage": None, "current": None}

        self.setWindowTitle('Keithley 2280S')

        self.dev_selector = QComboBox(self)
        self.dev_selector.addItems(res)

        self.btn_connect = QPushButton('Open', self)
        self.btn_connect.clicked.connect(self.on_open_click)
        self.btn_connect.setToolTip('Connect/Disconnect To device')

        # Device Selector
        box_selector = QHBoxLayout()
        box_selector.addWidget(self.dev_selector)
        box_selector.addWidget(self.btn_connect)

        # Main Zone
        main_layout = QHBoxLayout()

        main_control_layout = QVBoxLayout()

        # Voltage Group
        voltage_group_layout = QVBoxLayout()
        voltage_group_ctrl_layout = QHBoxLayout()
        voltage_group = QGroupBox("Voltage", self)
        voltage_group.setLayout(voltage_group_layout)
  
        # Voltage LCD
        self.voltage_lcd = QEditableLCD(8, self, QColor(99, 193, 149), "background-color: #222; border: 0px; border-radius: 5px;", textStyle="selection-background-color: #333; font-size: 36px; ", size=(160, 50))
        self.voltage_lcd.valueChanged[float].connect(lambda x: self.voltage_slider.setValue(x*1000))
        voltage_group_ctrl_layout.addWidget(self.voltage_lcd)

        self.voltage_slider = QDial(self)
        self.voltage_slider.setMinimum(0)
        self.voltage_slider.setMaximum(32000)
        self.voltage_slider.valueChanged.connect(self.on_voltage_slider_valueChanged)
        voltage_group_ctrl_layout.addWidget(self.voltage_slider)

        # OVP
        voltage_group_protect_layout = QHBoxLayout()
        ovp_label = QLabel("OVP:", self)
        voltage_group_protect_layout.addWidget(ovp_label)
        self.ovp_value = QLineEdit(self)
        self.ovp_value.setEnabled(False)
        voltage_group_protect_layout.addWidget(self.ovp_value)

        # Add Voltage Group To Main Layout
        voltage_group_layout.addLayout(voltage_group_ctrl_layout)
        voltage_group_layout.addLayout(voltage_group_protect_layout)
        main_control_layout.addWidget(voltage_group)

        # Current Group
        current_group_layout = QVBoxLayout()
        current_group_ctrl_layout = QHBoxLayout()
        current_group = QGroupBox("Current", self)
        current_group.setLayout(current_group_layout)
  
        # Current LCD
        self.current_lcd = QEditableLCD(8, self, QColor(255, 128, 0), "background-color: #222; border: 0px; border-radius: 5px;", textStyle="selection-background-color: #333; font-size: 36px; ", size=(160, 50))
        self.current_lcd.valueChanged[float].connect(lambda x: self.current_slider.setValue(x*10000))
        current_group_ctrl_layout.addWidget(self.current_lcd)

        self.current_slider = QDial(self)
        self.current_slider.setMinimum(0)
        self.current_slider.setMaximum(61000)
        self.current_slider.valueChanged.connect(self.on_current_slider_valueChanged)
        current_group_ctrl_layout.addWidget(self.current_slider)

        # OVP
        current_group_protect_layout = QHBoxLayout()
        ocp_label = QLabel("OCP:", self)
        current_group_protect_layout.addWidget(ocp_label)
        self.ocp_value = QLineEdit(self)
        self.ocp_value.setEnabled(False)
        current_group_protect_layout.addWidget(self.ocp_value)

        # Add Current Group To Main Layout
        current_group_layout.addLayout(current_group_ctrl_layout)
        current_group_layout.addLayout(current_group_protect_layout)
        main_control_layout.addWidget(current_group)

        main_layout.addLayout(main_control_layout)

        # Load Control
        self.btn_output = QPushButton('OUTPUT', self)
        self.btn_output.clicked.connect(self.on_btn_output_clicked)

        self.btn_output.setFixedSize(self.btn_output.sizeHint().width(), main_control_layout.sizeHint().height())
        main_layout.addWidget(self.btn_output)
        

        # Meassure Zone Start
        self.meas_vol_lcd = QMeassureLCD("Voltage", 8, self, QColor(255, 0, 0), size=(160, 40))
        self.meas_cur_lcd = QMeassureLCD("Current", 8, self, QColor(0, 255, 0), size=(160, 40))
        self.meas_pow_lcd = QMeassureLCD("Power(W)", 8, self, QColor(0, 128, 255), size=(160, 40))
        # self.meas_vol_lcd.setContentsMargins(0,0,0,0)
        # self.meas_cur_lcd.setContentsMargins(0,0,0,0)
        # self.meas_pow_lcd.setContentsMargins(0,0,0,0)

        meas_layout = QGridLayout()
        meas_layout.setContentsMargins(5,5,5,5)
        meas_layout.addWidget(self.meas_vol_lcd, 0, 0)
        meas_layout.addWidget(self.meas_cur_lcd, 0, 1)
        meas_layout.addWidget(self.meas_pow_lcd, 1, 0, 1, 2)
        # Meassure Zone End

        vbox = QVBoxLayout()
        vbox.addLayout(box_selector)
        vbox.addLayout(main_layout)

        vbox.addLayout(meas_layout)

        self.setLayout(vbox)
         
        # self.slider.valueChanged.connect(self.on_main_slider_valueChanged)
        # self.resize(350,250)
        # self.setFixedSize(654,512)
        self.setMinimumSize(450,650)

        self.ocp_value.installEventFilter(self)
        self.ovp_value.installEventFilter(self)

        timer = QTimer(self)
        timer.setSingleShot(False)
        timer.timeout.connect(self.get_meas_value)
        timer.start(300)

    @pyqtSlot()
    def get_meas_value(self):
        if self.dev is not None and not self.initalizing:
            try:
                if self.pause_query:
                    return

                for k, v in self.set_commands.items():
                    if v is not None:
                        self.dev.write(v)
                        self.set_commands[k] = None

                self.querying = True
                self.dev.write(":OUTPut:PROTection:TRIPped?")
                protect_state = self.dev.read().strip()
                self.querying = False
                if protect_state == "NONE":
                    if self.output_enabled:
                        self.dev.write(":MEASure1:CONCurrent?")
                        meas_value = self.dev.read().strip().split(",")
                        self.meas_curr = float(meas_value[0][:-1])
                        self.meas_cur_lcd.display("%.05f" % (self.meas_curr))

                        self.meas_volt = float(meas_value[1][:-1])
                        self.meas_vol_lcd.display("%.04f" % (self.meas_volt))

                        self.meas_pow_lcd.display("%.05f" % (self.meas_curr * self.meas_volt))

                        if self.log_file is not None:
                            self.log_file.write("%s\t%.05f\t%.04f\t%.05f\n" % (datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),self.meas_volt, self.meas_curr,self.meas_curr * self.meas_volt))
                        if self.protection is not None:
                            self.protection = None
                            self.update_output_button()
                else:
                    self.protection = protect_state
                    self.update_output_button()
                pass
            except Exception as e:
                print("Read data failed", e)
                self.failed_read+=1
                if self.failed_read >= 10:
                    self.on_open_click()
                #     self.on_open_click()

    @pyqtSlot()
    def on_open_click(self):
        if self.dev is None:
            self.initalizing = True
            for i in range(0,5):
                try:
                    self.dev = self.rm.open_resource(self.dev_selector.currentText())
                    break
                except Exception as e:
                    print("Open Resource Failed")
                    time.sleep(1)

            self.btn_connect.setText("Close")
            self.dev.write("*IDN?")
            self.model = self.dev.read().strip()
            self.modelChanged.emit(self.model)
            self.model = self.model.split(",")
            self.setWindowTitle(" ".join(self.model[0:2])+" VER: "+self.model[3])

            self.dev.write(":OUTPut:STATe?")
            self.output_enabled = self.dev.read().strip() == "1"
            self.update_output_button()

            self.dev.write(":VOLT?")
            self.set_voltage = float(self.dev.read().strip())
            self.voltage_slider.setValue(self.set_voltage * 1000)

            self.dev.write(":CURR?")
            self.set_current = float(self.dev.read().strip())
            self.current_slider.setValue(self.set_current * 10000)

            self.dev.write(":VOLTage:PROTection?")
            self.set_ovp = self.dev.read().strip()
            self.ovp_value.setText(self.set_ovp)

            self.dev.write(":CURRent:PROTection?")
            self.set_ocp = self.dev.read().strip()
            self.ocp_value.setText(self.set_ocp)

            self.initalizing = False

        else:
            if self.log_file is not None:
                self.log_file.close()
                self.log_file = None
            self.dev.write(":SYSTem:LOCal")
            self.dev.close()
            self.btn_connect.setText("Open")
            self.dev = None
            self.initalizing = True
        self.repaint()

    def closeEvent(self, event):
        if self.dev is not None:
            self.on_open_click()

    def eventFilter(self, obj, event):
        if self.dev is None:
            return super(self.__class__, self).eventFilter(obj, event)
        if obj in [self.ocp_value,self.ovp_value]:
            if event.type() == QEvent.Enter:
                rc = super(self.__class__, self).eventFilter(obj, event)
                obj.setEnabled(True)
                obj.setFocus()
                obj.selectAll()
                return rc
            if event.type() == QEvent.Leave:
                rc = super(self.__class__, self).eventFilter(obj, event)
                obj.setEnabled(False)
                return rc
            elif event.type() == QEvent.KeyPress and (event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter):
                try:
                    if obj is self.ocp_value:
                        self.dev.write(":CURRent:PROTection %f" % (float(obj.text())))
                        self.dev.write(":CURRent:PROTection?")
                        self.set_ocp = self.dev.read().strip()
                    elif obj is self.ovp_value:
                        self.dev.write(":VOLTage:PROTection %f" % (float(obj.text())))
                        self.dev.write(":VOLTage:PROTection?")
                        self.set_ovp = self.dev.read().strip()
                    obj.selectAll()
                except Exception as e:
                    QMessageBox.warning(None, "Warning", "Input invalid")
                if obj is self.ocp_value:
                    obj.setText(self.set_ocp)
                elif obj is self.ovp_value:
                    obj.setText(self.set_ovp)
        return super(self.__class__, self).eventFilter(obj, event)

    def update_output_button(self):
        if self.protection is not None:
            self.btn_output.setText(self.protection)
            self.btn_output.setStyleSheet("background-color: #F00; color: #fff; font-weight:bold; border-radius: 15px; border: 2px dashed #000")
        elif self.output_enabled == False:
            self.btn_output.setText("OUTPUT")
            self.btn_output.setStyleSheet("background-color: #999; color: #efefef; border-radius: 15px; border: 2px dashed #000")
        else:
            self.btn_output.setText("OUTPUT")
            self.btn_output.setStyleSheet("background-color: #172e7b; color: white; font-weight:bold; border-radius: 15px; border: 2px dashed #000")

    @pyqtSlot()
    def on_voltage_slider_valueChanged(self):
        self.set_voltage = self.voltage_slider.value() / 1000
        self.voltage_lcd.display("%.04f" % (self.set_voltage))
        if self.initalizing:
            return
        self.set_commands["voltage"] = ":VOLT %.04f" % (self.set_voltage)

    @pyqtSlot()
    def on_current_slider_valueChanged(self):
        self.set_current = self.current_slider.value() / 10000
        self.current_lcd.display("%.05f" % (self.set_current))
        if self.initalizing:
            return
        self.set_commands["current"] = ":CURR %.05f" % (self.set_current)

    @pyqtSlot()
    def on_btn_output_clicked(self):
        if self.initalizing:
            return
        
        if self.protection:
            print("Clear Protect")
            self.dev.write(":OUTPut:PROTection:CLEar")
            self.protection = None
            self.dev.write(":OUTPut:STATe?")
            self.output_enabled = self.dev.read().strip() == "1"
            self.update_output_button()
        elif self.output_enabled == False:
            print("Change Output State ON")
            self.dev.write(":OUTPut:STATe ON")
            self.log_file = open("logs/2280S-%s.csv" % (datetime.now().strftime("%Y-%m-%d %H%M%S")), "w")
            self.log_file.write("Time\tVolt\tCurrent\tPower\n")

            self.output_enabled = True
        else:
            print("Change Output State OFF")
            self.dev.write(":OUTPut:STATe OFF")
            self.output_enabled = False
            if self.log_file is not None:
                self.log_file.close()
                self.log_file = None

        self.update_output_button()
    
    def keyPressEvent(self, e):
        if e.key() == Qt.Key_F5:
            self.on_btn_output_clicked()
        elif e.key() == Qt.Key_M:
            if self.log_file is not None:
                self.log_file.write("%s\tMARK\tMARK\tMARK\n" % (datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    qb = Keithley2280S()
    qb.show()
    def handle_exception(exc_type, exc_value, exc_traceback):
        if qb is not None and qb.dev is not None:
            qb.on_open_click()
        if not exc_type is KeyboardInterrupt:
            QMessageBox.critical(None,"Error", "<html>A critical error has occured.<br /><br/> %s: <b>%s</b><br /><br />Traceback:<pre>%s</pre><br/><br/></html>" % (exc_type.__name__, exc_value, '<br />'.join(traceback.format_tb(exc_traceback))))
        sys.exit(1)

    sys.excepthook = handle_exception
    sys.exit(app.exec_())