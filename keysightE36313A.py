#coding:utf-8

import sys
from PyQt5.QtCore import (Qt, QEvent, QTimer)
from PyQt5.QtWidgets import (QWidget, QLCDNumber, QSlider, QVBoxLayout, QApplication, QSizePolicy)
from PyQt5.QtWidgets import *
from PyQt5.QtCore import pyqtSlot, pyqtSignal
from PyQt5.QtGui import QColor
from PyQt5 import *
import time
import traceback
from libs.QEditableLCD import QEditableLCD
from libs.QMeassureLCD import QMeassureLCD
import pyvisa as visa
import threading

from objbrowser import browse

class KeysightE36313A(QWidget):
    modelChanged = pyqtSignal(str)

    def __init__(self,parent=None):
        QWidget.__init__(self)

        self.rm = visa.ResourceManager(visa_library="@ivi")
        time.sleep(0.2)
        for i in range(0,10):
            try:
                # res = self.rm.list_resources()
                res = ['TCPIP::192.168.9.153::inst0::INSTR']
                break
            except Exception as e:
                self.rm = visa.ResourceManager(visa_library=R'C:\Program Files (x86)\IVI Foundation\VISA\Win64\Bin\kivisa32.dll')
                print("List Resource Failed")
                time.sleep(0.1)

        self.dev = None
        self.model = None
        self.mode = None
        self.initalizing = True
        self.err = None
        self.pause_query = False
        self.querying = False
        self.failed_read = 0
        self.current_range = None
        self.set_commands = {}

        self.setWindowTitle('Keysight E36313A')

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

        ChannelColors = [(51,37,4),(10,51,15),(22,32,51)]
        ChannelTitleColors = [(250,217,74),(89,164,30),(29,103,171)]
        ChannelVoltageLimit = [6,25,25]
        ChannelOverVoltageLimit = [6.6,27.5,27.5]
        ChannelCurrentLimit = [10.6,2.06,2.06]
        self.channelObjects = {}
        for channel in range(1,4):
            self.channelObjects[channel] = {
                "voltage_slider":None,
                "protection": None,
                "output_enabled": False,
                "questionable_register": None,
                "meas_volt": 0,
                "meas_curr": 0
            }

            ch = self.channelObjects[channel]
            ch_grid_layout = QGridLayout()
            ch_grid_layout.setSpacing(0)
            ch_grid_layout.setContentsMargins(0,0,0,0)
            voltage_group = QGroupBox("2wire", self)
            voltage_group.setAccessibleName("ChannelGroup")
            voltage_group.setLayout(ch_grid_layout)
            voltage_group.setContentsMargins(0,0,0,0)

            voltage_group.setStyleSheet("QGroupBox {background-color: rgb(%d,%d,%d); color: #fff; border-radius: 3px; margin: 0;}" % (ChannelColors[channel-1][0],ChannelColors[channel-1][1],ChannelColors[channel-1][2])+
                " QGroupBox::title { margin-top: 0em; subcontrol-origin: padding; subcontrol-position: left top; } "+
                " QGroupBox[accessibleName=ChannelGroup] { padding: 0px; margin: 0px; border: 3px solid rgb(%d,%d,%d);} " % (ChannelTitleColors[channel-1][0], ChannelTitleColors[channel-1][1],ChannelTitleColors[channel-1][2])+
                " QGroupBox[accessibleName=ChannelGroup]::title { subcontrol-position: top center; subcontrol-origin: margin; background-color: rgb(%d,%d,%d); }"  % (ChannelTitleColors[channel-1][0], ChannelTitleColors[channel-1][1],ChannelTitleColors[channel-1][2]) +
                " QDial { background-color: #444; }"+
                " QLabel { color: #fff; } QVBoxLayout {margin: 0; padding: 0; }")
                #  width: 100%%; margin: 2px; padding: 5px;)
            # 89, 164, 30
            # 29, 103, 171

            ch_background = QLabel("2 WIRE", self)
            ch_background.setStyleSheet("background-color: rgb(%d,%d,%d); color: #000; margin: 0; padding: 3px;" % (ChannelTitleColors[channel-1][0], ChannelTitleColors[channel-1][1],ChannelTitleColors[channel-1][2]))
            ch_background.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.MinimumExpanding)
            ch_background.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
            ch_grid_layout.addWidget(ch_background, 0, 0)

            ch_label = QLabel("%d" % (channel), self)
            ch_label.setStyleSheet("background-color: rgb(%d,%d,%d); margin: 0; padding: 3px;" % (ChannelColors[channel-1][0],ChannelColors[channel-1][1],ChannelColors[channel-1][2]))
            ch_label.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
            ch_grid_layout.addWidget(ch_label, 0, 0)

            ch_mode = QLabel("CV", voltage_group)
            ch_mode.setStyleSheet("*[state=protect]{ color: #ff0000; } * {background-color: rgb(%d,%d,%d); color: #000; margin: 0; padding: 3px}" % (ChannelTitleColors[channel-1][0], ChannelTitleColors[channel-1][1],ChannelTitleColors[channel-1][2]))
            # ch_mode.move(voltage_group.sizeHint().width() - ch_mode.sizeHint().width(),0)
            ch_mode.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.MinimumExpanding)
            ch_mode.setAlignment(Qt.AlignTop | Qt.AlignRight)
            ch["mode"] = ch_mode
            ch_grid_layout.addWidget(ch_mode, 0, 0, alignment=Qt.AlignTop | Qt.AlignRight)
            # browse(ch_mode)

            # Control Zone START
            ch_group_ctrl_layout = QHBoxLayout()

            ch_voltage_group_ctrl_layout = QVBoxLayout()
            volt_label = QLabel("Voltage", self)
            volt_label.setAlignment(Qt.AlignHCenter)
            ch_voltage_group_ctrl_layout.addWidget(volt_label)
            ch["voltage_slider"] = QDial(self)
            ch["voltage_slider"].setMinimum(0)
            ch["voltage_slider"].setMaximum(ChannelVoltageLimit[channel-1] * 1000)
            ch["voltage_slider"].channel = channel
            ch["voltage_slider"].valueChanged.connect(self.on_voltage_slider_valueChanged)
            ch_voltage_group_ctrl_layout.addWidget(ch["voltage_slider"])

            ch_current_group_ctrl_layout = QVBoxLayout()
            curr_label = QLabel("Current", self)
            curr_label.setAlignment(Qt.AlignHCenter)
            ch_current_group_ctrl_layout.addWidget(curr_label)
            ch["current_slider"] = QDial(self)
            ch["current_slider"].setMinimum(1)
            ch["current_slider"].setMaximum(ChannelCurrentLimit[channel-1] * 1000)
            ch["current_slider"].channel = channel
            ch["current_slider"].valueChanged.connect(self.on_current_slider_valueChanged)
            ch_current_group_ctrl_layout.addWidget(ch["current_slider"])

            ch_ovp_group_ctrl_layout = QVBoxLayout()
            ovp_label = QLabel("OVP", self)
            ovp_label.setAlignment(Qt.AlignHCenter)
            ch_ovp_group_ctrl_layout.addWidget(ovp_label)
            ch["ovp_slider"] = QDial(self)
            ch["ovp_slider"].channel = channel
            ch["ovp_slider"].setMinimum(0)
            ch["ovp_slider"].setMaximum((ChannelOverVoltageLimit[channel-1]) * 1000)
            ch["ovp_slider"].valueChanged.connect(self.on_ovp_slider_valueChanged)
            ch_ovp_group_ctrl_layout.addWidget(ch["ovp_slider"])

            ch_group_ctrl_layout.addLayout(ch_voltage_group_ctrl_layout)
            ch_group_ctrl_layout.addLayout(ch_current_group_ctrl_layout)
            ch_group_ctrl_layout.addLayout(ch_ovp_group_ctrl_layout)

            ch_grid_layout.addLayout(ch_group_ctrl_layout, 1, 0)
            # Control Zone END

            # Meassure Zone Start
            ch["meas_vol_lcd"] = QMeassureLCD("Voltage", 8, self, QColor(255, 0, 0), size=(160, 40), unit="V")
            ch["meas_vol_lcd"].channel = channel
            ch["meas_cur_lcd"] = QMeassureLCD("Current", 8, self, QColor(0, 255, 0), size=(160, 40), unit="A")
            ch["meas_cur_lcd"].channel = channel
            ch["meas_pow_lcd"] = QMeassureLCD("Power(W)", 8, self, QColor(0, 128, 255), size=(160, 40), unit="W")
            ch["meas_pow_lcd"].channel = channel
            ch["meas_vol_lcd"].setContentsMargins(0,0,0,0)
            ch["meas_cur_lcd"].setContentsMargins(0,0,0,0)
            ch["meas_pow_lcd"].setContentsMargins(0,0,0,0)

            meas_layout = QVBoxLayout()
            # meas_layout.setSpacing(0)
            meas_layout.setContentsMargins(5,5,5,5)
            meas_layout.addWidget(ch["meas_vol_lcd"])
            meas_layout.addWidget(ch["meas_cur_lcd"])
            meas_layout.addWidget(ch["meas_pow_lcd"])
            # meassure_group.setLayout(meas_layout)
            # Meassure Zone End

            ch_grid_layout.addLayout(meas_layout, 2, 0)

            set_layout = QGridLayout()

            set_label = QLabel("Set", voltage_group)
            set_layout.addWidget(set_label,0,0,4,1, Qt.AlignVCenter | Qt.AlignHCenter)

            volt_lcd_label = QLabel("VOLT", self)
            ch["voltage_lcd"] = QEditableLCD(6, self, QColor(99, 193, 149), "background-color: #222; border: 0px; border-radius: 5px;", textStyle="selection-background-color: #333; font-size: 36px; ", size=(100, 50))
            ch["voltage_lcd"].channel = channel
            ch["voltage_lcd"].valueChanged[float].connect(lambda x: self.channelObjects[self.sender().channel]["voltage_slider"].setValue(x*1000))
            set_layout.addWidget(volt_lcd_label, 0, 1)
            set_layout.addWidget(ch["voltage_lcd"], 0, 2)

            curr_label = QLabel("CURR", self)
            # Current LCD
            ch["current_lcd"] = QEditableLCD(6, self, QColor(0, 237, 0), "background-color: #222; border: 0px; border-radius: 5px;", textStyle="selection-background-color: #333; font-size: 36px; ", size=(100, 50))
            ch["current_lcd"].channel = channel
            ch["current_lcd"].valueChanged[float].connect(lambda x: self.channelObjects[self.sender().channel]["current_slider"].setValue(x*1000))
            set_layout.addWidget(curr_label, 1, 1)
            set_layout.addWidget(ch["current_lcd"], 1, 2)

            # OVP
            ovp_label = QLabel("OVP", self)
            ch["ovp_lcd"] = QEditableLCD(6, self, QColor(237, 64, 60), "background-color: #222; border: 0px; border-radius: 2px;", textStyle="selection-background-color: #333; ", size=(100, 50))
            ch["ovp_lcd"].channel = channel
            ch["ovp_lcd"].valueChanged[float].connect(lambda x: self.channelObjects[self.sender().channel]["ovp_slider"].setValue(x*1000))
            set_layout.addWidget(ovp_label, 2, 1)
            set_layout.addWidget(ch["ovp_lcd"], 2, 2)

            ch["current_ocp"] = QCheckBox("OCP", self)
            ch["current_ocp"].setStyleSheet("color: #fff")
            ch["current_ocp"].stateChanged.connect(self.on_current_ocp_stateChanged)
            ch["current_ocp"].channel = channel
            set_layout.addWidget(ch["current_ocp"], 3, 1, 1, 2)

            # Load Control
            ch["btn_output"] = QPushButton("ON", self)
            ch["btn_output"].clicked.connect(self.on_btn_output_clicked)
            ch["btn_output"].setFixedSize(40,30)
            ch["btn_output"].setProperty("state", "on")
            ch["btn_output"].setStyleSheet("QPushButton { border-radius: 15px; background-color: #666; } QPushButton[state=protect] { background-color: #ff0000; } QPushButton[state=on] { background-color: rgb(%d,%d,%d); }" % (ChannelTitleColors[channel-1][0], ChannelTitleColors[channel-1][1],ChannelTitleColors[channel-1][2]))
            ch["btn_output"].channel = channel

            ch_grid_layout.addLayout(set_layout, 3, 0)
            ch_grid_layout.addWidget(ch["btn_output"], 4, 0, alignment=Qt.AlignHCenter)
            ch_grid_layout.setRowMinimumHeight(4, 45)

            main_layout.addWidget(voltage_group)

        # self.btn_output.setFixedSize(self.btn_output.sizeHint().width(), main_control_layout.sizeHint().height())
        # main_layout.addWidget(self.btn_output)
        
        vbox = QVBoxLayout()
        vbox.addLayout(box_selector)
        vbox.addLayout(main_layout)

        self.setLayout(vbox)
         
        # self.resize(350,250)
        self.setFixedSize(753,664)

        timer = QTimer(self)
        timer.setSingleShot(False)
        timer.timeout.connect(self.get_meas_value)
        timer.start(300)

    def query_thread(self):
        emptyCycle = 0
        while self.dev is not None:
            try:
                if self.pause_query or self.initalizing:
                    time.sleep(0.05)
                    continue

                for k, v in self.set_commands.items():
                    if v is not None:
                        if type(v) is list:
                            for vl in v:
                                self.dev.write(vl)
                        else:
                            self.dev.write(v)
                        self.set_commands[k] = None

                self.querying = True

                self.dev.write(":SYSTem:ERRor?")
                err = self.dev.read().strip()

                if err != '+0,"No error"':
                    self.err = err

                for channel,ch in self.channelObjects.items():
                    self.dev.write(":STAT:QUES:INST:ISUM%d:COND?" % (channel))
                    questionable_register = int(self.dev.read().strip())
                    if ch["questionable_register"] != questionable_register:
                        ch["questionable_register"] = questionable_register
                        if (ch["questionable_register"] & 0x1) == 0x1:
                            ch["mode"].setText("CC")
                            ch["mode"].setProperty("state", "")
                            ch["mode"].setStyle(ch["mode"].style())
                        elif (ch["questionable_register"] & 0x2) == 0x2:
                            ch["mode"].setText("CV")
                            ch["mode"].setProperty("state", "")
                            ch["mode"].setStyle(ch["mode"].style())
                        elif (ch["questionable_register"] & 0x4) == 0x4:
                            ch["mode"].setText("OVP")
                            ch["protection"] = "OVP"
                            ch["mode"].setProperty("state", "protect")
                            ch["mode"].setStyle(ch["mode"].style())
                            self.update_output_button()
                        elif (ch["questionable_register"] & 0x8) == 0x8:
                            ch["mode"].setText("OCP")
                            ch["protection"] = "OCP"
                            ch["mode"].setProperty("state", "protect")
                            ch["mode"].setStyle(ch["mode"].style())
                            self.update_output_button()

                self.dev.write("FETCH:DLOG? 1,(@%s)" % (','.join(["%d"%(channel) for channel,ch in self.channelObjects.items()])))
                dlog = self.dev.read().strip()
                if dlog == "":
                    time.sleep(0.2)
                    emptyCycle+=1
                    if (emptyCycle > 2):
                        print("Restart DLOG")
                        self.dev.write("INITiate:DLOG \"External:/log_1.csv\"")
                        while True:
                            self.dev.write("*OPC?")
                            if self.dev.read().strip() == "1":
                                break
                            else:
                                time.sleep(0.1)
                        emptyCycle = 0
                else:
                    emptyCycle = 0
                    dlogs = dlog.split(",")
                    offsets = 0
                    for channel,ch in self.channelObjects.items():
                    # self.dev.write("MEAS:VOLT? (@%d)" % (channel))
                        ch["meas_volt"] = float(dlogs[offsets])
                        offsets+=1
                        ch["meas_curr"] = float(dlogs[offsets])
                        offsets+=1
                        # ch["meas_curr"] = 0
                    # float(self.dev.read())

                    # print("mas volt %.06f" % (time.time()-t1))
                    # self.dev.write("MEAS:CURR? (@%d)" % (channel))
                    # ch["meas_curr"] =  float(self.dev.read())
                    # print("mas curr %.06f" % (time.time()-t1))

                self.querying = False
            except Exception as e:
                print("Read data thread failed", e)
                traceback.print_exc()
                self.failed_read+=1

    @pyqtSlot()
    def get_meas_value(self):
        if self.dev is not None and not self.initalizing:
            try:
                if self.pause_query:
                    return
                # self.dev.write(":OUTPut:PROTection:TRIPped?")
                # protect_state = self.dev.read().strip()
                #     if self.output_enabled:

                if self.err != None:
                    QMessageBox.critical(None,"Error", "A error has occured: <b>%s</b>" % (self.err))
                    self.err = None

                for channel,ch in self.channelObjects.items():
                    ch["meas_vol_lcd"].display("%.03f" % (ch["meas_volt"]))
                    if ch["meas_curr"] < 0.02:
                        ch["meas_cur_lcd"].display("%.03f" % (ch["meas_curr"] * 1000))
                        ch["meas_cur_lcd"].unit.setText("mA")
                    else:
                        ch["meas_cur_lcd"].display("%.03f" % (ch["meas_curr"]))
                        ch["meas_cur_lcd"].unit.setText("A")

                    ch["meas_pow_lcd"].display("%.03f" % (ch["meas_volt"] * ch["meas_curr"]))

                # :STATus:WARNing:CONDition?
                # :STATus:OPERation
                # :STATus:QUEStionable
                # *SRE?

                # print("REG: WARNING %04x  OPT %04x  QUESTION %04x" % (reg_warning_status, reg_operation_status, reg_questionable_status))

                # self.dev.write(":SOURce:READ?")
                # self.querying = False
                # meas_value = self.dev.read().strip().split(",")
                # self.meas_volt = float(meas_value[0])
                # self.meas_vol_lcd.display("%.04f" % (self.meas_volt))

                # self.meas_curr = float(meas_value[4])
                # self.meas_cur_lcd.display("%.04f" % (self.meas_curr))

                # self.meas_pwr = float(meas_value[9])
                # self.meas_pow_lcd.display("%.04f" % (self.meas_pwr))

                # if self.protection is not None:
                #     self.protection = None
                #     self.update_output_button()
                # else:
                #     self.protection = protect_state
                pass
            except Exception as e:
                print("Read data failed", e)
                traceback.print_exc()
                # self.failed_read+=1
                if self.failed_read >= 10:
                    self.on_open_click()
                #     self.on_open_click()

    def load_current_settings(self):
            self.initalizing = True
            for channel,ch in self.channelObjects.items():
                self.dev.write(":OUTP? (@%d)" % (channel))
                ch["output_enabled"] = self.dev.read().strip() == "1"
                
                self.dev.write(":VOLTage? (@%d)" % (channel))
                ch["set_voltage"] = float(self.dev.read().strip())
                ch["voltage_slider"].setValue(ch["set_voltage"] * 1000)

                self.dev.write(":CURRent? (@%d)" % (channel))
                ch["set_current"] = float(self.dev.read().strip())
                ch["current_slider"].setValue(ch["set_current"] * 1000)

                self.dev.write(":VOLT:PROT? (@%d)" % (channel))
                ch["set_ovp"] = float(self.dev.read().strip())
                ch["ovp_slider"].setValue(ch["set_ovp"] * 1000)

                self.dev.write(":CURR:PROT:STAT? (@%d)" % (channel))
                ch["set_ocp"] = self.dev.read().strip() != "1"
                ch["current_ocp"].setChecked(ch["set_ocp"])

            self.update_output_button()

            self.current_range = None
            self.initalizing = False

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

            self.thread = threading.Thread(target=self.query_thread)
            self.thread.start()

            self.btn_connect.setText("Close")
            self.dev.write("*IDN?")
            self.model = self.dev.read().strip()
            self.modelChanged.emit(self.model)
            self.model = self.model.split(",")
            self.setWindowTitle(" ".join(self.model[0:2])+" VER: "+self.model[3])
            # Init DLOG
            # for channel,ch in self.channelObjects.items():
            self.dev.write("ABORt:DLOG")
            time.sleep(0.5)
            self.dev.write("SENSe:DLOG:FUNCtion:VOLTage 1,(@%s)" % (','.join(["%d"%(channel) for channel,ch in self.channelObjects.items()])))
            self.dev.write("SENSe:DLOG:FUNCtion:CURRent 1,(@%s)" % (','.join(["%d"%(channel) for channel,ch in self.channelObjects.items()])))
            # self.dev.write("SENSe:DLOG:FUNCtion:VOLTage ON, (@%s)" % (channel))

            # Sample Interval
            self.dev.write("SENSe:DLOG:PER 0.2")
            self.dev.write("TRIGger:DLOG:SOURce IMM")
            self.dev.write("SENSe:DLOG:TIME 3600")
            self.dev.write("INITiate:DLOG \"External:/log_1.csv\"")

            self.load_current_settings()
            self.failed_read = 0
            self.initalizing = False

        else:
            # self.dev.write(":SYSTem:COMMunicate:RLSTate LOCal")
            self.pause_query = True
            while self.querying:
                time.sleep(0.01)
            self.dev.write("ABORt:DLOG")
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
        return super(self.__class__, self).eventFilter(obj, event)

    def update_output_button(self):
        for channel,ch in self.channelObjects.items():
            if  ch["protection"] is not None:
                ch["btn_output"].setText(ch["protection"])
                ch["btn_output"].setProperty("state", "protect")
            elif ch["output_enabled"] == False:
                ch["btn_output"].setText("On")
                ch["btn_output"].setProperty("state", "off")
            else:
                ch["btn_output"].setText("On")
                ch["btn_output"].setProperty("state", "on")

            ch["btn_output"].setStyle(ch["btn_output"].style())


    @pyqtSlot()
    def on_voltage_slider_valueChanged(self):
        ch = self.channelObjects[self.sender().channel]
        ch["set_voltage"] = self.sender().value() / 1000
        ch["voltage_lcd"].display("%.03f" % (ch["set_voltage"]))
        if self.initalizing:
            return
        self.set_commands["voltage_ch%d" % (self.sender().channel)] = ":VOLTage %.03f,(@%d)" % (ch["set_voltage"], self.sender().channel)

    @pyqtSlot()
    def on_current_slider_valueChanged(self):
        ch = self.channelObjects[self.sender().channel]
        ch["set_current"] = self.sender().value() / 1000
        ch["current_lcd"].display("%.03f" % (ch["set_current"]))
        if self.initalizing:
            return
        self.set_commands["current_ch%d" % (self.sender().channel)] = ":CURRent %.03f,(@%d)" % (ch["set_current"], self.sender().channel)

    @pyqtSlot()
    def on_ovp_slider_valueChanged(self):
        ch = self.channelObjects[self.sender().channel]
        ch["set_ovp"] = self.sender().value() / 1000
        ch["ovp_lcd"].display("%.03f" % (ch["set_ovp"]))
        if self.initalizing:
            return
        self.set_commands["ovp_ch%d" % (self.sender().channel)] = ":VOLT:PROT %.03f,(@%d)" % (ch["set_ovp"], self.sender().channel)

    @pyqtSlot()
    def on_current_ocp_stateChanged(self):
        ch = self.channelObjects[self.sender().channel]
        ch["set_ocp"] = self.sender().isChecked()
        if self.initalizing:
            return
        self.set_commands["oc_ch%d" % (self.sender().channel)] = ":CURR:PROT:STAT %s,(@%d)" % ("OFF" if ch["set_ocp"] else "ON", self.sender().channel)

    def add_cmd_queue(self, ch, cmd):
        if "queue_%d" % (ch) not in self.set_commands or self.set_commands["queue_%d" % (ch)] is None:
            self.set_commands["queue_%d" % (ch)] = []
        self.set_commands["queue_%d" % (ch)].append(cmd)

    @pyqtSlot()
    def on_btn_output_clicked(self):
        if self.initalizing:
            return
        
        ch = self.channelObjects[self.sender().channel]

        if ch["protection"]:
            print("Clear Protect")
            self.add_cmd_queue(self.sender().channel, ":OUTPut:PROTection:CLEar (@%d)" % (self.sender().channel))
            ch["protection"] = None
            time.sleep(0.1)
            self.add_cmd_queue(self.sender().channel, ":OUTPut? (@%d)" % (self.sender().channel))
            ch["output_enabled"] = self.dev.read().strip() == "1"
            self.update_output_button()
        elif ch["output_enabled"] == False:
            print("Change Output State ON")
            self.add_cmd_queue(self.sender().channel, ":OUTPut ON,(@%d)" % (self.sender().channel))
            ch["output_enabled"] = True
        else:
            print("Change Output State OFF")
            self.add_cmd_queue(self.sender().channel, ":OUTPut OFF,(@%d)" % (self.sender().channel))
            ch["output_enabled"] = False

        self.update_output_button()
    
    def keyPressEvent(self, e):
        if e.key() == Qt.Key_F5:
            self.on_btn_output_clicked()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    qb = KeysightE36313A()
    qb.show()
    def handle_exception(exc_type, exc_value, exc_traceback):
        if qb is not None and qb.dev is not None:
            qb.on_open_click()
        if not exc_type is KeyboardInterrupt:
            QMessageBox.critical(None,"Error", "<html>A critical error has occured.<br /><br/> %s: <b>%s</b><br /><br />Traceback:<pre>%s</pre><br/><br/></html>" % (exc_type.__name__, exc_value, '<br />'.join(traceback.format_tb(exc_traceback))))
        sys.exit(1)

    sys.excepthook = handle_exception
    sys.exit(app.exec_())