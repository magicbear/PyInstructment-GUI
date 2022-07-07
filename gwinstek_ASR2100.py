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
from libs.SocketInterfaces import SocketInterfaces
from libs.QEditableLCD import QEditableLCD
from libs.QMeassureLCD import QMeassureLCD
import pyvisa as visa
import numpy as np
import struct
import math

def generateSINData(start_phase = 0, end_phase = 360, num=4096, positiveOnly=False):
    baseWaveform = (np.sin(np.linspace(math.pi,-math.pi, num=num)) * 32767).astype(np.int16)
    if positiveOnly:
        baseWaveform = np.abs(baseWaveform)
    start_point = int(start_phase / 360. * (num/2))
    end_point = int(end_phase / 360. * (num/2))
    baseWaveform[0:start_point] = 0
    baseWaveform[end_point:int(num/2)] = 0
    baseWaveform[int(num/2):int(num/2)+start_point] = 0
    baseWaveform[int(num/2)+end_point:num] = 0
    return baseWaveform

class GwinstekASR2100(QWidget):
    modelChanged = pyqtSignal(str)

    def __init__(self,parent=None):
        QWidget.__init__(self)

        self.rm = visa.ResourceManager(visa_library="@ivi")
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
        self.current_range = None
        self.set_commands = {"voltage": None, "current": None}

        self.setWindowTitle('GWINSTEK ASR-2100')

        self.dev_selector = QLineEdit("192.168.11.247:2268", self)

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
        voltage_group = QGroupBox("Voltage", self)
        voltage_group.setLayout(voltage_group_layout)
  
        # Voltage LCD
        voltage_group_ctrl_layout = QHBoxLayout()
        ac_label = QLabel("AC RMS", self)
        voltage_group_ctrl_layout.addWidget(ac_label)
        self.voltage_lcd = QEditableLCD(5, self, QColor(99, 193, 149), "background-color: #222; border: 0px; border-radius: 5px;", textStyle="selection-background-color: #333; font-size: 36px; ", size=(100, 50))
        self.voltage_lcd.valueChanged.connect(self.on_voltage_lcd_valueChanged)
        voltage_group_ctrl_layout.addWidget(self.voltage_lcd)

        self.voltage_slider = QSlider(Qt.Horizontal,self)
        self.voltage_slider.setMinimum(0)
        self.voltage_slider.setMaximum(3500)
        self.voltage_slider.valueChanged.connect(self.on_voltage_slider_valueChanged)
        voltage_group_ctrl_layout.addWidget(self.voltage_slider)

        # Voltage DC LCD
        voltage_group_dc_ctrl_layout = QHBoxLayout()
        dc_label = QLabel("DC-OFF", self)
        voltage_group_dc_ctrl_layout.addWidget(dc_label)
        self.voltage_dc_lcd = QEditableLCD(5, self, QColor(99, 193, 149), "background-color: #222; border: 0px; border-radius: 5px;", textStyle="selection-background-color: #333; font-size: 36px; ", size=(100, 50))
        self.voltage_dc_lcd.valueChanged[float].connect(lambda x: self.voltage_dc_slider.setValue(x*10))
        voltage_group_dc_ctrl_layout.addWidget(self.voltage_dc_lcd)

        self.voltage_dc_slider = QSlider(Qt.Horizontal,self)
        self.voltage_dc_slider.setMinimum(-5000)
        self.voltage_dc_slider.setMaximum(5000)
        self.voltage_dc_slider.valueChanged.connect(self.on_voltage_dc_slider_valueChanged)
        voltage_group_dc_ctrl_layout.addWidget(self.voltage_dc_slider)

        # OVP
        voltage_group_protect_layout = QHBoxLayout()
        ovp_label = QLabel("V-Limit:", self)
        voltage_group_protect_layout.addWidget(ovp_label)
        self.volt_neg_slider = QSlider(Qt.Horizontal,self)
        self.volt_neg_slider.setInvertedControls(True)
        self.volt_neg_slider.setMinimum(-5000)
        self.volt_neg_slider.setMaximum(-200)

        self.volt_neg_lcd = QEditableLCD(6, self, QColor(237, 64, 60), "background-color: #222; border: 0px; border-radius: 2px;", textStyle="selection-background-color: #333; ")
        self.volt_pos_lcd = QEditableLCD(6, self, QColor(237, 64, 60), "background-color: #222; border: 0px; border-radius: 2px;", textStyle="selection-background-color: #333; ")

        self.volt_pos_slider = QSlider(Qt.Horizontal,self)
        self.volt_pos_slider.setMinimum(200)
        self.volt_pos_slider.setMaximum(5000)
        
        self.volt_neg_slider.valueChanged.connect(self.on_volt_neg_slider_valueChanged)
        self.volt_neg_lcd.valueChanged[float].connect(lambda x: self.volt_neg_slider.setValue(x*10) if not self.initalizing else 0)
        self.volt_pos_slider.valueChanged.connect(self.on_volt_pos_slider_valueChanged)
        self.volt_pos_lcd.valueChanged[float].connect(lambda x: self.volt_pos_slider.setValue(x*10) if not self.initalizing else 0)
        voltage_group_protect_layout.addWidget(self.volt_neg_slider)
        voltage_group_protect_layout.addWidget(self.volt_neg_lcd)
        voltage_group_protect_layout.addWidget(self.volt_pos_lcd)
        voltage_group_protect_layout.addWidget(self.volt_pos_slider)

        # Add Voltage Group To Main Layout
        voltage_group_layout.addLayout(voltage_group_ctrl_layout)
        voltage_group_layout.addLayout(voltage_group_dc_ctrl_layout)
        voltage_group_layout.addLayout(voltage_group_protect_layout)
        main_control_layout.addWidget(voltage_group)

        # Current Group
        current_group_layout = QVBoxLayout()
        current_group_ctrl_layout = QHBoxLayout()
        current_group = QGroupBox("Current", self)
        current_group.setLayout(current_group_layout)

        # Current LCD
        self.current_lcd = QEditableLCD(5, self, QColor(0, 237, 0), "background-color: #222; border: 0px; border-radius: 5px;", textStyle="selection-background-color: #333; font-size: 36px; ", size=(100, 50))
        self.current_lcd.valueChanged.connect(self.on_current_lcd_valueChanged)
        current_group_ctrl_layout.addWidget(self.current_lcd)

        self.current_slider = QSlider(Qt.Horizontal,self)
        self.current_slider.valueChanged.connect(self.on_current_slider_valueChanged)
        current_group_ctrl_layout.addWidget(self.current_slider)

        self.current_ocp = QCheckBox("O&CP", self)
        self.current_ocp.stateChanged.connect(self.on_current_ocp_stateChanged)
        current_group_ctrl_layout.addWidget(self.current_ocp)

        # Peak
        current_group_protect_layout = QHBoxLayout()
        ocp_label = QLabel("IPeak:", self)
        current_group_protect_layout.addWidget(ocp_label)
        self.ipk_neg_slider = QSlider(Qt.Horizontal,self)
        self.ipk_neg_slider.setInvertedControls(True)
        # self.ipk_neg_slider.setInvertedAppearance(True)

        self.ipk_neg_lcd = QEditableLCD(6, self, QColor(0, 237, 60), "background-color: #222; border: 0px; border-radius: 2px;", textStyle="selection-background-color: #333; ")
        self.ipk_protect = QCheckBox("PROTECT", self)
        self.ipk_pos_lcd = QEditableLCD(6, self, QColor(0, 237, 60), "background-color: #222; border: 0px; border-radius: 2px;", textStyle="selection-background-color: #333; ")

        self.ipk_pos_slider = QSlider(Qt.Horizontal,self)

        self.ipk_neg_slider.valueChanged.connect(self.on_ipk_neg_slider_valueChanged)
        self.ipk_neg_lcd.valueChanged[float].connect(lambda x: self.ipk_neg_slider.setValue(x*100) if not self.initalizing else 0)
        self.ipk_protect.stateChanged.connect(self.on_ipk_protect_stateChanged)
        self.ipk_pos_slider.valueChanged.connect(self.on_ipk_pos_slider_valueChanged)
        self.ipk_pos_lcd.valueChanged[float].connect(lambda x: self.ipk_pos_slider.setValue(x*100) if not self.initalizing else 0)
        current_group_protect_layout.addWidget(self.ipk_neg_slider)
        current_group_protect_layout.addWidget(self.ipk_neg_lcd)
        current_group_protect_layout.addWidget(self.ipk_protect)
        current_group_protect_layout.addWidget(self.ipk_pos_lcd)
        current_group_protect_layout.addWidget(self.ipk_pos_slider)

        # Add Current Group To Main Layout
        current_group_layout.addLayout(current_group_ctrl_layout)
        current_group_layout.addLayout(current_group_protect_layout)
        main_control_layout.addWidget(current_group)

        # Frequence Group
        frequence_group_layout = QVBoxLayout()
        frequence_group_ctrl_layout = QHBoxLayout()
        self.frequence_group = QGroupBox("Frequence & Phase", self)
        self.frequence_group.setLayout(frequence_group_layout)

        # Frequence LCD
        self.frequence_lcd = QEditableLCD(5, self, QColor(255, 128, 0), "background-color: #222; border: 0px; border-radius: 5px;", textStyle="selection-background-color: #333; font-size: 36px; ", size=(100, 30))
        self.frequence_lcd.valueChanged[float].connect(lambda x: self.frequence_slider.setValue(x*100 if x < 100 else 10000 + (x-100) * 10))
        frequence_group_ctrl_layout.addWidget(self.frequence_lcd)

        self.frequence_slider = QSlider(Qt.Horizontal,self)
        self.frequence_slider.valueChanged.connect(self.on_freq_slider_valueChanged)
        self.frequence_slider.setMinimum(100)
        self.frequence_slider.setMaximum(10000+8999)
        frequence_group_ctrl_layout.addWidget(self.frequence_slider)

        # OFP
        ofp_label = QLabel("F-Limit:", self)
        frequence_group_ctrl_layout.addWidget(ofp_label)
        self.freq_neg_slider = QSlider(Qt.Horizontal,self)
        self.freq_neg_slider.setInvertedControls(True)
        self.freq_neg_slider.setMinimum(100)
        self.freq_neg_slider.setMaximum(10000+8999)

        self.freq_neg_lcd = QEditableLCD(5, self, QColor(237, 64, 60), "background-color: #222; border: 0px; border-radius: 2px;", textStyle="selection-background-color: #333; ")
        self.freq_pos_lcd = QEditableLCD(5, self, QColor(237, 64, 60), "background-color: #222; border: 0px; border-radius: 2px;", textStyle="selection-background-color: #333; ")

        self.freq_pos_slider = QSlider(Qt.Horizontal,self)
        self.freq_pos_slider.setMinimum(100)
        self.freq_pos_slider.setMaximum(10000+8999)
        
        self.freq_neg_slider.valueChanged.connect(self.on_freq_neg_slider_valueChanged)
        self.freq_neg_lcd.valueChanged[float].connect(lambda x: self.freq_neg_slider.setValue(x*100 if x < 100 else 10000 + (x-100) * 10))
        self.freq_pos_slider.valueChanged.connect(self.on_freq_pos_slider_valueChanged)
        self.freq_pos_lcd.valueChanged[float].connect(lambda x: self.freq_pos_slider.setValue(x*100 if x < 100 else 10000 + (x-100) * 10))
        frequence_group_ctrl_layout.addWidget(self.freq_neg_slider)
        frequence_group_ctrl_layout.addWidget(self.freq_neg_lcd)
        frequence_group_ctrl_layout.addWidget(self.freq_pos_lcd)
        frequence_group_ctrl_layout.addWidget(self.freq_pos_slider)


        # Phase
        phase_group_layout = QHBoxLayout()
        phase_label = QLabel("Phase:", self)
        self.phase_start_lcd = QEditableLCD(5, self, QColor(237, 64, 60), "background-color: #222; border: 0px; border-radius: 2px;", textStyle="selection-background-color: #333; ")
        self.phase_start_slider = QSlider(Qt.Horizontal,self)
        self.phase_start_slider.setMinimum(0)
        self.phase_start_slider.setMaximum(3599)

        self.phase_end_lcd = QEditableLCD(5, self, QColor(237, 64, 60), "background-color: #222; border: 0px; border-radius: 2px;", textStyle="selection-background-color: #333; ")
        self.phase_end_slider = QSlider(Qt.Horizontal,self)
        self.phase_end_slider.setMinimum(0)
        self.phase_end_slider.setMaximum(3599)
        
        self.phase_start_slider.valueChanged.connect(self.on_phase_start_slider_valueChanged)
        self.phase_start_lcd.valueChanged[float].connect(lambda x: self.phase_start_slider.setValue(x*10))
        self.phase_end_slider.valueChanged.connect(self.on_phase_end_slider_valueChanged)
        self.phase_end_lcd.valueChanged[float].connect(lambda x: self.phase_end_slider.setValue(x*100 if x < 100 else 10000 + (x-100) * 10))

        phase_group_layout.addWidget(phase_label)
        phase_group_layout.addWidget(self.phase_start_lcd)
        phase_group_layout.addWidget(self.phase_start_slider)
        phase_group_layout.addWidget(self.phase_end_lcd)
        phase_group_layout.addWidget(self.phase_end_slider)


        # SCR
        scr_group_layout = QHBoxLayout()
        scr_label = QLabel("SCR SIM:", self)
        self.scr_lcd = QEditableLCD(5, self, QColor(237, 64, 60), "background-color: #222; border: 0px; border-radius: 2px;", textStyle="selection-background-color: #333; ")
        self.scr_slider = QSlider(Qt.Horizontal,self)
        self.scr_slider.setMinimum(0)
        self.scr_slider.setMaximum(3599)

        self.scr_slider.valueChanged.connect(self.on_scr_slider_valueChanged)
        self.scr_lcd.valueChanged[float].connect(lambda x: self.scr_slider.setValue(x*10))

        scr_group_layout.addWidget(scr_label)
        scr_group_layout.addWidget(self.scr_lcd)
        scr_group_layout.addWidget(self.scr_slider)

        self.br_sim = QComboBox(self)
        self.br_sim.addItem("None", "None")
        self.br_sim.addItem("Full Bridge Rectifier", "FBR")
        self.br_sim.addItem("Half Bridge Rectifier", "HBR")
        self.br_sim.addItem("MOSFET RPC", "RPC")
        self.br_sim.currentIndexChanged.connect(self.on_scr_slider_valueChanged)
        scr_group_layout.addWidget(self.br_sim)


        freq_sync_group_layout = QHBoxLayout()
        freq_sync_label = QLabel("Freq Sync:", self)
        
        freq_sync_group_layout.addWidget(freq_sync_label)

        self.freq_sync = QComboBox(self)
        self.freq_sync.addItem("None", "None")
        self.freq_sync.addItem("Sync With Power Line", "LINE")
        self.freq_sync.addItem("Sync With Ext", "EXT")
        self.freq_sync.currentIndexChanged.connect(self.on_freq_sync_valueChanged)
        freq_sync_group_layout.addWidget(self.freq_sync)

        # Add Frequence Group To Main Layout
        frequence_group_layout.addLayout(frequence_group_ctrl_layout)
        frequence_group_layout.addLayout(phase_group_layout)
        frequence_group_layout.addLayout(scr_group_layout)
        frequence_group_layout.addLayout(freq_sync_group_layout)
        main_control_layout.addWidget(self.frequence_group)

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
        self.meas_q_lcd = QMeassureLCD("Q (var)", 8, self, QColor(192, 128, 0), size=(120, 30))
        self.meas_pf_lcd = QMeassureLCD("PowerFactor (PF)", 5, self, QColor(0, 192, 128), size=(90, 30))
        self.meas_cf_lcd = QMeassureLCD("CF", 5, self, QColor(0, 192, 128), size=(90, 30))
        self.meas_s_lcd = QMeassureLCD("Power(VA)", 8, self, QColor(0, 128, 255), size=(120, 30))

        meas_layout = QVBoxLayout()
        meas_layout1 = QHBoxLayout()
        meas_layout1.addWidget(self.meas_vol_lcd)
        meas_layout1.addWidget(self.meas_cur_lcd)
        meas_layout1.addWidget(self.meas_pow_lcd)
        meas_layout.addLayout(meas_layout1)
        meas_layout2 = QHBoxLayout()
        meas_layout2.addWidget(self.meas_q_lcd)
        meas_layout2.addWidget(self.meas_pf_lcd)
        meas_layout2.addWidget(self.meas_cf_lcd)
        meas_layout2.addWidget(self.meas_s_lcd)
        meas_layout.addLayout(meas_layout2)
        # Meassure Zone End

        vbox = QVBoxLayout()
        vbox.addLayout(box_selector)
        vbox.addLayout(main_layout)

        vbox.addLayout(meas_layout)

        self.setLayout(vbox)
         
        # self.slider.valueChanged.connect(self.on_main_slider_valueChanged)
        self.resize(350,250)

        # self.volt_neg_lcd.installEventFilter(self)
        # self.volt_neg_lcd_edit.installEventFilter(self)
        # self.volt_pos_lcd.installEventFilter(self)
        # self.volt_pos_lcd_edit.installEventFilter(self)
        # self.ovp_value.installEventFilter(self)

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
                self.querying = True
                load_settings = False
                for k, v in self.set_commands.items():
                    if v is not None:
                        if type(v) is list:
                            for vl in v:
                                self.dev.write(vl)
                        else:
                            self.dev.write(v)
                        self.set_commands[k] = None
                        if k == "mode":
                            load_settings = True
                # <Vrms>,<Vavg>,<Vmax>,<Vmin>,<Irms>,<Iavg>,<Imax>,<Imin>,<IpkH>,<P>,<S>,<Q>,<PF>,<CF>,<THDv>,<THDi>,<Freq>
                error_list = []
                while True:
                    self.dev.write(":SYSTem:ERRor?")
                    err = self.dev.read().strip()
                    if err != '+0,"No error"':
                        error_list.append(err)
                    else:
                        break

                if len(error_list) > 0:
                    QMessageBox.critical(None,"Error", "A error has occured: <b>%s</b>" % ("\n<br />".join(error_list)))
                    self.load_current_settings()

                if load_settings:
                    self.load_current_settings()

                self.dev.write(":STATus:WARNing:CONDition?")
                reg_warning_status = int(self.dev.read().strip())

                self.dev.write(":STATus:OPERation?")
                reg_operation_status = int(self.dev.read().strip())

                self.dev.write(":STATus:QUEStionable?")
                reg_questionable_status = int(self.dev.read().strip())
                # :STATus:WARNing:CONDition?
                # :STATus:OPERation
                # :STATus:QUEStionable
                # *SRE?

                # print("REG: WARNING %04x  OPT %04x  QUESTION %04x" % (reg_warning_status, reg_operation_status, reg_questionable_status))

                if (reg_warning_status & 0x1) != 0:
                    self.protection = "OVP"
                elif (reg_warning_status & 0x2) != 0:
                    self.protection = "Over Irms"
                elif (reg_warning_status & 0x8) != 0:
                    self.protection = "Over Ipeak"
                elif (reg_warning_status & 0x40) != 0:
                    self.protection = "Overheat"
                elif (reg_warning_status & 0x80) != 0:
                    self.protection = "Ext Sync Error"
                elif (reg_warning_status & 0x200) != 0:
                    self.protection = "Sense Error"
                elif (reg_warning_status & 0x1000) != 0:
                    self.protection = "Power Limit"
                elif (reg_warning_status & 0x2000) != 0:
                    self.protection = "IRMS\nSoft Limit"
                    # pass
                elif (reg_warning_status & 0x4000) != 0:
                    self.protection = "IPK\nSoft Limit"
                else:
                    self.protection = None
                    self.update_output_button()

                if self.protection is not None:
                    self.update_output_button()
                self.dev.write(":SOURce:READ?")
                self.querying = False
                meas_value = self.dev.read().strip().split(",")
                self.meas_volt = float(meas_value[0])
                self.meas_vol_lcd.display("%.04f" % (self.meas_volt))

                self.meas_curr = float(meas_value[4])
                self.meas_cur_lcd.display("%.04f" % (self.meas_curr))

                self.meas_pwr = float(meas_value[9])
                self.meas_pow_lcd.display("%.04f" % (self.meas_pwr))

                self.meas_s = float(meas_value[10])
                self.meas_s_lcd.display("%.04f" % (self.meas_s))

                self.meas_q = float(meas_value[11])
                self.meas_q_lcd.display("%.04f" % (self.meas_q))

                self.meas_pf = float(meas_value[12])
                self.meas_pf_lcd.display("%.03f" % (self.meas_pf))

                self.meas_cf = float(meas_value[13])
                self.meas_cf_lcd.display("%.03f" % (self.meas_cf))

                # if self.protection is not None:
                #     self.protection = None
                #     self.update_output_button()
                # else:
                #     self.protection = protect_state
                pass
            except Exception as e:
                print("Read data failed", e)
                traceback.print_exc()
                self.failed_read+=1
                if self.failed_read >= 10:
                    self.on_open_click()
                #     self.on_open_click()

    def load_current_settings(self):
            self.initalizing = True

            self.dev.write(":MODE?")
            self.set_mode = self.dev.read().strip()

            self.dev.write(":OUTPut?")
            self.output_enabled = self.dev.read().strip() == "+1"
            self.update_output_button()

            self.dev.write(":FUNCtion?")
            self.output_waveform = self.dev.read().strip()

            self.dev.write(":SOUR:VOLT:RANG?")
            self.set_voltage_range = self.dev.read().strip()
            
            self.dev.write(":VOLTage?")
            self.set_voltage = float(self.dev.read().strip()) * (1 if self.output_waveform == "SIN" else 1/(2*math.sqrt(2)))
            self.voltage_slider.setValue(self.set_voltage * 10)

            if self.set_mode == "ACDC-INT" or self.set_mode == "ACDC-Sync":
                self.dev.write(":VOLT:OFFSet?")
                self.set_dc_voltage = float(self.dev.read().strip())
                self.voltage_dc_slider.setValue(self.set_dc_voltage * 10)
                self.voltage_dc_lcd.setEnabled(True)
                self.voltage_dc_slider.setEnabled(True)
            else:
                self.voltage_dc_lcd.setEnabled(False)
                self.voltage_dc_slider.setEnabled(False)

            # if self.output_waveform == "SIN" and self.set_voltage_range != "AUTO":
            #     self.dev.write(":SOUR:VOLT:RANG AUTO")
            # elif self.output_waveform == "ARB16" and self.set_voltage_range == "AUTO":
                
            if self.set_mode in ["ACDC-INT", "AC-INT"]:
                self.dev.write(":FREQuency?")
                self.set_freq = float(self.dev.read().strip())
                self.dev.write(":FREQuency:LIMit:LOW?")
                self.set_freq_neg = float(self.dev.read().strip())
                self.dev.write(":FREQuency:LIMit:HIGH?")
                self.set_freq_pos = float(self.dev.read().strip())
                self.frequence_slider.setValue(self.set_freq *100 if self.set_freq < 100 else 10000 + (self.set_freq-100) * 10)
                self.freq_neg_slider.setValue(self.set_freq_neg *100 if self.set_freq_neg < 100 else 10000 + (self.set_freq_neg-100) * 10)
                self.freq_pos_slider.setValue(self.set_freq_pos *100 if self.set_freq_pos < 100 else 10000 + (self.set_freq_pos-100) * 10)

                self.frequence_slider.setEnabled(True)
                self.freq_neg_slider.setEnabled(True)
                self.freq_pos_slider.setEnabled(True)
            else:
                self.frequence_slider.setEnabled(False)
                self.freq_neg_slider.setEnabled(False)
                self.freq_pos_slider.setEnabled(False)

            if self.set_mode in ["ACDC-INT", "ACDC-Sync", "AC-Sync"]:
                self.dev.write(":PHASe:STARt?")
                self.set_phase_start = float(self.dev.read().strip())
                self.dev.write(":PHASe:STOP?")
                self.set_phase_end = float(self.dev.read().strip())

                self.phase_start_slider.setEnabled(True)
                self.phase_end_slider.setEnabled(True)
                self.phase_start_slider.setValue(self.set_phase_start * 10)
                
                self.phase_end_slider.setValue(self.set_phase_end * 10)
            else:
                self.phase_start_slider.setEnabled(False)
                self.phase_end_slider.setEnabled(False)

            if self.set_mode in ["ACDC-Sync", "AC-Sync"]:
                self.dev.write(":INPut:SYNC:SOURce?")
                if self.dev.read().strip() == "LINE":
                    self.freq_sync.setCurrentIndex(1)
                else:
                    self.freq_sync.setCurrentIndex(2)

            self.current_range = None
            self.initalizing = False

    @pyqtSlot()
    def on_open_click(self):
        if self.dev is None:
            self.initalizing = True
            
            self.dev = SocketInterfaces(self.dev_selector.text())
            # for i in range(0,5):
            #     try:
            #         self.dev = self.rm.open_resource("TCPIP0::%s::SOCKET" % (self.dev_selector.text().replace(":","::")), read_termination = '\n')
            #         break
            #     except Exception as e:
            #         print("Open Resource Failed")
            #         time.sleep(1)

            self.btn_connect.setText("Close")
            self.dev.write("*IDN?")
            self.model = self.dev.read().strip()
            self.modelChanged.emit(self.model)
            self.model = self.model.split(",")
            self.setWindowTitle(" ".join(self.model[0:2])+" VER: "+self.model[3])

            self.load_current_settings()
            self.initalizing = False

        else:
            self.dev.write(":SYSTem:COMMunicate:RLSTate LOCal")
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
    def on_voltage_dc_slider_valueChanged(self):
        self.set_dc_voltage = self.voltage_dc_slider.value() / 10
        self.voltage_dc_lcd.display("%.01f" % (self.set_dc_voltage))
        if self.initalizing:
            return
        self.set_commands["voltage"] = ":VOLT:OFFSet %.01f" % (self.set_dc_voltage)

    @pyqtSlot()
    def on_voltage_slider_valueChanged(self):
        self.set_voltage = self.voltage_slider.value() / 10
        self.voltage_lcd.display("%.01f" % (self.set_voltage))
        rangeChanged = False
        manual_init = self.initalizing

        if not self.initalizing:
            self.initalizing = True

        if self.set_voltage < 176.80:
            if self.set_voltage_range != "100":
                self.set_voltage_range = "100"
                self.dev.write(":SOUR:VOLT:RANG 100")
                time.sleep(0.1)
                if self.output_enabled:
                    self.dev.write(":OUTPut 1")
                self.current_slider.setMinimum(50)
                self.current_slider.setMaximum(1050)
                self.ipk_neg_slider.setMinimum(-4200)
                self.ipk_neg_slider.setMaximum(-420)
                self.ipk_pos_slider.setMinimum(420)
                self.ipk_pos_slider.setMaximum(4200)
                if self.current_range != "LOW":
                    rangeChanged = True
                self.current_range = "LOW"
        else:
            if self.set_voltage_range != "200":
                self.set_voltage_range = "200"
                self.dev.write(":SOUR:VOLT:RANG 200")
                time.sleep(0.1)
                if self.output_enabled:
                    self.dev.write(":OUTPut 1")
                self.current_slider.setMinimum(25)
                self.current_slider.setMaximum(525)
                self.ipk_neg_slider.setMinimum(-2100)
                self.ipk_neg_slider.setMaximum(-210)
                self.ipk_pos_slider.setMinimum(210)
                self.ipk_pos_slider.setMaximum(2100)
                if self.current_range != "HIGH":
                    rangeChanged = True
                self.current_range = "HIGH"

        if rangeChanged:
            self.dev.write(":CURRent:LIMit:RMS?")
            self.set_current = float(self.dev.read().strip())
            self.current_slider.setValue(self.set_current * 100)

            self.dev.write(":CURRent:LIMit:RMS:MODE?")
            self.current_ocp.setChecked(self.dev.read().strip() != "+1")

            self.dev.write(":CURRent:LIMit:PEAK:MODE?")
            self.ipk_protect.setChecked(self.dev.read().strip() != "+1")

            self.dev.write(":CURRent:LIMit:PEAK:LOW?")
            self.set_ipk_neg = float(self.dev.read().strip())
            self.ipk_neg_slider.setValue(self.set_ipk_neg * 100)

            self.dev.write(":CURRent:LIMit:PEAK:HIGH?")
            self.set_ipk_pos = float(self.dev.read().strip())
            self.ipk_pos_slider.setValue(self.set_ipk_pos * 100)

            self.dev.write(":VOLTage:LIMit:LOW?")
            self.set_volt_neg = float(self.dev.read().strip())
            self.volt_neg_slider.setValue(self.set_volt_neg * 10)

            self.dev.write(":VOLTage:LIMit:HIGH?")
            self.set_volt_pos = float(self.dev.read().strip())
            self.volt_pos_slider.setValue(self.set_volt_pos * 10)

        self.initalizing = manual_init

        if self.initalizing:
            return

        if self.output_waveform == "SIN":
            self.set_commands["voltage"] = ":VOLT %.01f" % (self.set_voltage)
        else:
            self.set_commands["voltage"] = ":VOLT %.01f" % (self.set_voltage * math.sqrt(2)*2)

    @pyqtSlot()
    def on_volt_neg_slider_valueChanged(self):
        self.set_volt_neg = self.volt_neg_slider.value() / 10
        self.volt_neg_lcd.display("%.01f" % (self.set_volt_neg))
        if self.initalizing:
            return
        print("Set Voltage Limit Low Range ", (self.set_volt_neg))
        self.set_commands["current"] = ":VOLTage:LIMit:LOW %.02f" % (self.set_volt_neg)

    @pyqtSlot()
    def on_volt_pos_slider_valueChanged(self):
        self.set_volt_pos = self.volt_pos_slider.value() / 10
        self.volt_pos_lcd.display("%.01f" % (self.set_volt_pos))
        if self.initalizing:
            return
        print("Set Voltage Limit High Range ", (self.set_volt_pos))
        self.set_commands["current"] = ":VOLTage:LIMit:HIGH %.02f" % (self.set_volt_pos)

    def on_voltage_lcd_valueChanged(self, value):
        if self.initalizing:
            return
        try:
            self.voltage_slider.setValue(float(value) * 10)
        except Exception as e:
            QMessageBox.warning(None, "Warning", "Input invalid")

    @pyqtSlot()
    def on_current_slider_valueChanged(self):
        self.set_current = self.current_slider.value() / 100
        self.current_lcd.display("%.02f" % (self.set_current))
        if self.initalizing:
            return
        self.set_commands["current"] = ":CURRent:LIMit:RMS %.02f" % (self.set_current)

    @pyqtSlot()
    def on_ipk_neg_slider_valueChanged(self):
        self.set_ipk_neg = self.ipk_neg_slider.value() / 100
        self.ipk_neg_lcd.display("%.02f" % (self.set_ipk_neg))
        if self.initalizing:
            return
        print("Set IPeak Low Range ", (self.set_ipk_neg))
        self.set_commands["current"] = ":CURRent:LIMit:PEAK:LOW %.02f" % (self.set_ipk_neg)

    @pyqtSlot()
    def on_ipk_pos_slider_valueChanged(self):
        self.set_ipk_pos = self.ipk_pos_slider.value() / 100
        self.ipk_pos_lcd.display("%.02f" % (self.set_ipk_pos))
        if self.initalizing:
            return
        print("Set High Range ", (self.set_ipk_pos))
        self.set_commands["current"] = ":CURRent:LIMit:PEAK:HIGH %.02f" % (self.set_ipk_pos)

    def on_current_lcd_valueChanged(self, value):
        try:
            self.current_slider.setValue(float(value) * 100)
        except Exception as e:
            QMessageBox.warning(None, "Warning", "Input invalid")

    @pyqtSlot()
    def on_current_ocp_stateChanged(self):
        self.set_ocp = self.current_ocp.isChecked()
        if self.initalizing:
            return
        self.set_commands["current_ocp"] = ":CURRent:LIMit:RMS:MODE %s" % ("OFF" if self.set_ocp else "ON")

    @pyqtSlot()
    def on_ipk_protect_stateChanged(self):
        self.set_ipk_protect = self.ipk_protect.isChecked()
        if self.initalizing:
            return
        self.set_commands["current_ocp"] = ":CURRent:LIMit:PEAK:MODE %s" % ("OFF" if self.set_ipk_protect else "ON")

    @pyqtSlot()
    def on_freq_slider_valueChanged(self):
        self.set_freq = self.frequence_slider.value() / 100 if self.frequence_slider.value() < 10000 else 100+(self.frequence_slider.value() - 10000) / 10
        print(self.frequence_slider.value(), self.set_freq )
        if self.set_freq >= 100:
            self.frequence_lcd.display("%.01f" % (self.set_freq))
        else:
            self.frequence_lcd.display("%.02f" % (self.set_freq))
        if self.initalizing:
            return
        self.set_commands["frequence"] = ":FREQuency %.02f" % (self.set_freq)

    @pyqtSlot()
    def on_freq_neg_slider_valueChanged(self):
        self.set_freq_neg = self.freq_neg_slider.value() / 100 if self.freq_neg_slider.value() < 10000 else 100+(self.freq_neg_slider.value() - 10000) / 10
        if self.set_freq_neg >= 100:
            self.freq_neg_lcd.display("%.01f" % (self.set_freq_neg))
        else:
            self.freq_neg_lcd.display("%.02f" % (self.set_freq_neg))
        if self.initalizing:
            return
        print("Set Frequence Limit Low Range ", (self.set_freq_neg))
        self.set_commands["frequence"] = ":FREQuency:LIMit:LOW %.02f" % (self.set_freq_neg)

    @pyqtSlot()
    def on_freq_pos_slider_valueChanged(self):
        self.set_freq_pos = self.freq_pos_slider.value() / 100 if self.freq_pos_slider.value() < 10000 else 100+(self.freq_pos_slider.value() - 10000) / 10
        if self.set_freq_pos >= 100:
            self.freq_pos_lcd.display("%.01f" % (self.set_freq_pos))
        else:
            self.freq_pos_lcd.display("%.02f" % (self.set_freq_pos))
        if self.initalizing:
            return
        print("Set Frequence Limit High Range ", (self.set_freq_pos))
        self.set_commands["frequence"] = ":FREQuency:LIMit:HIGH %.02f" % (self.set_freq_pos)

    @pyqtSlot()
    def on_phase_start_slider_valueChanged(self):
        self.set_phase_start = self.phase_start_slider.value() / 10
        self.phase_start_lcd.display("%.01f" % (self.set_phase_start))
        if self.initalizing:
            return
        print("Set Phase Start ", (self.set_phase_start))
        self.set_commands["frequence"] = ":PHASe:STARt %.02f" % (self.set_phase_start)

    @pyqtSlot()
    def on_phase_end_slider_valueChanged(self):
        self.set_phase_end = self.phase_end_slider.value() / 10
        self.phase_end_lcd.display("%.01f" % (self.set_phase_end))
        if self.initalizing:
            return
        print("Set Phase End ", (self.set_phase_end))
        self.set_commands["frequence"] = ":PHASe:STOP %.02f" % (self.set_phase_end)

    @pyqtSlot()
    def on_scr_slider_valueChanged(self):
        self.set_scr = self.scr_slider.value()/10
        self.scr_lcd.display("%.01f" % (self.set_scr))
        # print("TRAC:WAV 16,#216" + ''.join(['%04x' % b for b in bytearray(struct.pack(">32h",*generateSINData(self.set_scr, num=32)))]))
        if self.initalizing:
            return
        print("Set SCR Simulate ", (self.set_scr))
        if self.set_scr == 0 and self.br_sim.currentData() == "None":
            self.set_commands["mode"] = [":FUNCtion SIN", ":OUTPut %d" % (1 if self.output_enabled else 0)]
        else:
            # self.set_commands["scr"] = "TRACe:WAVe:CLEar 16"# % (self.set_phase_start)
            # self.set_commands["scr_data"] = ":DATA:WAVE 16,#232" + ''.join(['%04X' % b for b in bytearray(struct.pack(">32h",*generateSINData(self.set_scr, num=32)))])
            if self.br_sim.currentData() == "FBR":
                sinData = generateSINData(self.set_scr, positiveOnly=True)
            elif self.br_sim.currentData() == "HBR":
                sinData = generateSINData(self.set_scr, positiveOnly=False)
                sinData = np.where(sinData > 0, sinData, 0)
            elif self.br_sim.currentData() == "RPC":
                sinData = generateSINData(start_phase = 0, end_phase = self.set_scr, positiveOnly=False)
            else:
                sinData = generateSINData(self.set_scr, positiveOnly=False)

            self.set_commands["scr_data"] = b":DATA:WAVE 16,#48192" + struct.pack(">4096h",*sinData) + b"\n"
            self.set_commands["mode"] = [":FUNCtion ARB16", ":OUTPut %d" % (1 if self.output_enabled else 0)]

    @pyqtSlot()
    def on_freq_sync_valueChanged(self):
        if self.initalizing:
            return

        if self.freq_sync.currentData() == "None":
            self.set_commands["mode"] = ":MODE ACDC-INT"
        else:
            self.set_commands["mode"] = ":MODE ACDC-SYNC"
            self.set_commands["sync"] = ":INPut:SYNC:SOURce %s" % (self.freq_sync.currentData())


    @pyqtSlot()
    def on_btn_output_clicked(self):
        if self.initalizing:
            return
        
        if self.protection:
            print("Clear Protect")
            self.dev.write(":OUTPut:PROTection:CLEar")
            self.protection = None
            time.sleep(0.1)
            self.dev.write(":OUTPut?")
            self.output_enabled = self.dev.read().strip() == "+1"
            self.update_output_button()
        elif self.output_enabled == False:
            print("Change Output State ON")
            self.dev.write(":OUTPut 1")
            self.output_enabled = True
        else:
            print("Change Output State OFF")
            self.dev.write(":OUTPut 0")
            self.output_enabled = False

        self.update_output_button()
    
    def keyPressEvent(self, e):
        if e.key() == Qt.Key_F5:
            self.on_btn_output_clicked()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    qb = GwinstekASR2100()
    qb.show()
    def handle_exception(exc_type, exc_value, exc_traceback):
        if qb is not None and qb.dev is not None:
            qb.on_open_click()
        if not exc_type is KeyboardInterrupt:
            QMessageBox.critical(None,"Error", "<html>A critical error has occured.<br /><br/> %s: <b>%s</b><br /><br />Traceback:<pre>%s</pre><br/><br/></html>" % (exc_type.__name__, exc_value, '<br />'.join(traceback.format_tb(exc_traceback))))
        sys.exit(1)

    sys.excepthook = handle_exception
    sys.exit(app.exec_())
