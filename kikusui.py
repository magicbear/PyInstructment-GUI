#coding:utf-8

import visa
import sys
from PyQt5.QtCore import (Qt, QEvent, QTimer)
from PyQt5.QtWidgets import (QWidget, QLCDNumber, QSlider, QVBoxLayout, QApplication, QSizePolicy)
from PyQt5.QtWidgets import *
from PyQt5.QtCore import pyqtSlot
from PyQt5.QtGui import QColor
import time

def get_mode_4(self):
    self.dev.write("FUNCtion:MODE?")
    return self.dev.read().strip()

def get_mode_3(self):
    self.dev.write("CCCR?")
    cc_cr = self.dev.read().strip()
    if cc_cr == "1":
        return "CC"
    elif cc_cr == "2":
        return "CR"

    self.dev.write("CV?")
    cv = self.dev.read().strip()
    if cv == "1":
        return "CV"

    return "CP"

def get_mode_itech(self):
    self.dev.write("MODE?")
    cur_mode = self.dev.read().strip()
    if cur_mode == "CURRent":
        return "CC"
    elif cur_mode == "VOLTage":
        return "CV"
    elif cur_mode == "POWer":
        return "CP"
    elif cur_mode == "RESistance":
        return "CR"

def set_mode_4(self, new_mode):
    self.dev.write("FUNCtion:MODE %s" % (new_mode))

def set_mode_3(self, new_mode):
    if new_mode == "CC":
        self.dev.write("CCCR 1")
    elif new_mode == "CR":
        self.dev.write("CCCR 2")
    elif new_mode == "CV":
        self.dev.write("CV 1")
    elif new_mode == "CP":
        self.dev.write("CV 0")

def get_range_4(self):
    self.dev.write("CONDuctance:RANGe?")
    return self.dev.read().strip()

def get_range_3(self):
    self.dev.write("CCRANGE?")
    range_v = self.dev.read().strip()
    if range_v == "0":
        return "LOW"
    elif range_v == "1":
        return "HIGH"

def set_range_4(self, new_range):
    self.dev.write("CONDuctance:RANGe %s" % new_range)

def set_range_3(self, new_range):
    self.dev.write("CCRANGE %s" % ("1" if new_range == "HIGH" else "0"))

COMMAND_SET = [
    {
        "models": ["PLZ164W","PLZ164WA","PLZ334","PLZ664WA"],
        "LOAD": "INP",
        "MEAS:CURR": "MEAS:CURR?",
        "MEAS:VOLT": "MEAS:VOLT?",
        "MEAS:POW": "MEAS:POW?",
        "SLEW_RATE": "CURRent:SLEW",
        "CURRENT": "CURRent",
        "VOLTAGE": "VOLTage",
        "RESISTANCE": "COND",
        "POWER": "POWer",
        "GET_MODE_FN": get_mode_4,
        "SET_MODE_FN": set_mode_4,
        "GET_RANGE_FN": get_range_4,
        "SET_RANGE_FN": set_range_4
    },
    {
        "models": ["PLZ153WH","PLZ303WH","PLZ603WH","PLZ1003WH"],
        "LOAD": "INP",
        "MEAS:CURR": "CURR?",
        "MEAS:VOLT": "VOLT?",
        "MEAS:POW": "POW?",
        "CURRENT": "ISET",
        "VOLTAGE": "VSET",
        "RESISTANCE": "RSET",
        "POWER": "PSET",
        "GET_MODE_FN": get_mode_3,
        "SET_MODE_FN": set_mode_3,
        "GET_RANGE_FN": get_range_3,
        "SET_RANGE_FN": set_range_3
    }
]

slew_table = {
    "PLZ164W":[[0.0025,2.5,0.001],[0.00025,0.25,0.00001],[0.000025,0.025,0.000001]],
    "PLZ164WA":[[0.0025,2.5,0.001],[0.00025,0.25,0.00001],[0.000025,0.025,0.000001]],
    "PLZ334":[[0.005,5,0.002],[0.0005,0.5,0.00002],[0.00005,0.05,0.000002]],
    "PLZ664WA":[[0.01,10,0.0004],[0.001,1,0.00004],[0.0001,0.1,0.000004]],
}

current_range_table = {
    "PLZ164W":[33,3.3,0.33],
    "PLZ164WA":[33,3.3,0.33],
    "PLZ334":[66,6.6,0.66],
    "PLZ664WA":[132,13.2,1.32],
    "PLZ1004W":[200,20,2]
}

voltage_range_table = {
    "PLZ164W": [157.5,157.5,157.5],
    "PLZ164WA":[157.5,157.5,157.5],
    "PLZ334":  [157.5,157.5,157.5],
    "PLZ664WA":[157.5,157.5,157.5],
    "PLZ1004W":[157.5,157.5,157.5]
}

power_range_table = {
    "PLZ164W":[173.25,17.325,1.7325],
    "PLZ164WA":[173.25,17.325,1.7325],
    "PLZ334":[346.5,34.65,3.465],
    "PLZ664WA":[693,69.3,6.93],
    "PLZ1004W":[1050,105,10.5]
}

conductance_range_table = {
    "PLZ164W":[23.1,2.31,0.231],
    "PLZ164WA":[23.1,2.31,0.231],
    "PLZ334":[46.2,4.62,0.462],
    "PLZ664WA":[92.4,9.24,0.924],
    "PLZ1004W":[139.9968,13.99968,1.399968]
}
class Kikusui(QWidget):
    def __init__(self,parent=None):
        QWidget.__init__(self)
        self.rm = visa.ResourceManager(visa_library="@ni")
        # self.rm = visa.ResourceManager(visa_library=R'C:\Program Files (x86)\IVI Foundation\VISA\Win64\Bin\kivisa32.dll')
        time.sleep(0.5)
        for i in range(0,10):
            try:
                res = self.rm.list_resources()
                break
            except Exception as e:
                self.rm = visa.ResourceManager(visa_library=R'C:\Program Files (x86)\IVI Foundation\VISA\Win64\Bin\kivisa32.dll')
                print("List Resource Failed")
                time.sleep(0.1)

        self.dev = None
        self.model = None
        self.cur_range = None
        self.mode = None
        self.initalizing = True
        self.load_enabled = "1"
        self.failed_read = 0

        self.setWindowTitle('Kikusui Electric Load')

        self.dev_selector = QComboBox(self)
        self.dev_selector.addItems(res)

        self.btn_connect = QPushButton('Open', self)
        self.btn_connect.clicked.connect(self.on_open_click)
        self.btn_connect.setToolTip('This is an example button')

        # Device Selector
        box_selector = QHBoxLayout()
        box_selector.addWidget(self.dev_selector)
        box_selector.addWidget(self.btn_connect)

        self.dev_id = QLineEdit(self)

        # Mode Zone
        mode_selector = QVBoxLayout()
        mode_group = QGroupBox("Mode", self)
        self.mode_cc = QRadioButton("CC")
        self.mode_cc.toggled.connect(lambda:self.on_mode_select(self.mode_cc))
        self.mode_cv = QRadioButton("CV")
        self.mode_cv.toggled.connect(lambda:self.on_mode_select(self.mode_cv))
        self.mode_cr = QRadioButton("CR")
        self.mode_cr.toggled.connect(lambda:self.on_mode_select(self.mode_cr))
        self.mode_cp = QRadioButton("CP")
        self.mode_cp.toggled.connect(lambda:self.on_mode_select(self.mode_cp))
        mode_selector.addWidget(self.mode_cc)
        mode_selector.addWidget(self.mode_cv)
        mode_selector.addWidget(self.mode_cr)
        mode_selector.addWidget(self.mode_cp)

        # Range Zone
        range_selector = QVBoxLayout()
        range_group = QGroupBox("Range", self)
        self.range_l = QRadioButton("LOW")
        self.range_l.toggled.connect(lambda:self.on_range_select(self.range_l))
        self.range_m = QRadioButton("MED")
        self.range_m.toggled.connect(lambda:self.on_range_select(self.range_m))
        self.range_h = QRadioButton("HIGH")
        self.range_h.toggled.connect(lambda:self.on_range_select(self.range_h))
        range_selector.addWidget(self.range_l)
        range_selector.addWidget(self.range_m)
        range_selector.addWidget(self.range_h)

        # Load Control        
        self.lcd = QLCDNumber(6, self)
        spRight = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        spRight.setHorizontalStretch(2)
        self.lcd.setSizePolicy(spRight)

        self.btn_load = QPushButton('LOAD', self)
        self.btn_load.clicked.connect(self.on_btn_load_clicked)


        # Power
        main_slider_label = QLabel("Power:", self)
        self.slider = QSlider(Qt.Horizontal,self)
        self.main_slider_value = QLineEdit("0.00A", self)
        self.main_slider_value.installEventFilter(self)
        # sp_slider_value = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        # sp_slider_value.setHorizontalStretch(0.1)
        # self.main_slider_value.setSizePolicy(sp_slider_value)
        self.main_slider_value.setFixedSize(80, 20)

        # Slew Rate Zone
        self.slew_group = QGroupBox("Slew", self)
        self.slew_slider = QSlider(Qt.Horizontal,self)
        self.slew_slider.valueChanged.connect(self.on_slew_value_changed)
        slew_label = QLabel("Slew Rate:",self)
        self.slew_slider_value = QLabel("0.00A/μs", self)


        # Meassure Zone Start
        mode_meas_vol = QGroupBox("Voltage", self)
        mode_meas_cur = QGroupBox("Current", self)
        mode_meas_pow = QGroupBox("Power", self)

        meas_vol_layout = QHBoxLayout()
        self.meas_vol_lcd = QLCDNumber(6, self)
        # get the palette
        palette = self.meas_vol_lcd.palette()
        palette.setColor(palette.Light, QColor(255, 0, 0))
        self.meas_vol_lcd.setPalette(palette)
        meas_vol_layout.addWidget(self.meas_vol_lcd)
        mode_meas_vol.setLayout(meas_vol_layout)

        meas_cur_layout = QHBoxLayout()
        self.meas_cur_lcd = QLCDNumber(6, self)
        palette = self.meas_cur_lcd.palette()
        palette.setColor(palette.Light, QColor(0, 255, 0))
        self.meas_cur_lcd.setPalette(palette)
        meas_cur_layout.addWidget(self.meas_cur_lcd)
        mode_meas_cur.setLayout(meas_cur_layout)

        meas_pow_layout = QHBoxLayout()
        self.meas_pow_lcd = QLCDNumber(6, self)
        palette = self.meas_pow_lcd.palette()
        palette.setColor(palette.Light, QColor(0, 0, 255))
        self.meas_pow_lcd.setPalette(palette)
        meas_pow_layout.addWidget(self.meas_pow_lcd)
        mode_meas_pow.setLayout(meas_pow_layout)

        meas_layout = QHBoxLayout()
        meas_layout.addWidget(mode_meas_vol)
        meas_layout.addWidget(mode_meas_cur)
        meas_layout.addWidget(mode_meas_pow)
        # Meassure Zone End

        # Pluse Zone
        pulse_mainLayout = QVBoxLayout()
        pulse_group = QGroupBox("Pluse", self)
        pulse_layout = QHBoxLayout()
        self.pulse_enabled = QCheckBox("ENABLE", self)
        self.pulse_freq = QSlider(Qt.Horizontal, self)
        self.pulse_freq.setMinimum(1)
        self.pulse_freq.setMaximum(20000)
        self.pulse_freq.setSingleStep(10)

        self.pulse_freq_text = QLineEdit("0.00Hz", self)
        self.pulse_freq_text.installEventFilter(self)
        self.pulse_freq_text.setFixedSize(60, 20)

        self.pulse_duty = QSlider(Qt.Horizontal, self)
        self.pulse_duty.setMinimum(50)
        self.pulse_duty.setMaximum(950)

        self.pulse_duty_text = QLineEdit("50.0%", self)
        self.pulse_duty_text.installEventFilter(self)
        self.pulse_duty_text.setFixedSize(40, 20)

        pulse_level_label = QLabel("Level:", self)
        self.pulse_level_slider = QSlider(Qt.Horizontal,self)
        self.pulse_level_text = QLineEdit("0.00A", self)
        self.pulse_level_text.installEventFilter(self)
        self.pulse_level_text.setFixedSize(40, 20)
        self.pulse_level_slider.setMinimum(0)
        self.pulse_level_slider.setMaximum(1000)

        pulse_layout.addWidget(self.pulse_enabled)
        pulse_layout.addWidget(self.pulse_freq)
        pulse_layout.addWidget(self.pulse_freq_text)
        pulse_layout.addWidget(self.pulse_duty)
        pulse_layout.addWidget(self.pulse_duty_text)

        pulse_level_layout = QHBoxLayout()
        pulse_level_layout.addWidget(pulse_level_label)
        pulse_level_layout.addWidget(self.pulse_level_slider)
        pulse_level_layout.addWidget(self.pulse_level_text)

        pulse_mainLayout.addLayout(pulse_layout)
        pulse_mainLayout.addLayout(pulse_level_layout)
        pulse_group.setLayout(pulse_mainLayout)

        self.pulse_enabled.toggled.connect(self.on_pulse_enabled_toggle)
        self.pulse_freq.valueChanged.connect(self.on_pulse_freq_slider_valueChanged)
        self.pulse_duty.valueChanged.connect(self.on_pulse_duty_slider_valueChanged)
        self.pulse_level_slider.valueChanged.connect(self.on_pulse_level_slider_valueChanged)
        # Pluse Zone End


        main_layout = QHBoxLayout()
        mode_group.setLayout(mode_selector)
        # mode_size = mode_group.sizeHint()
        # mode_size.setWidth(80)
        # mode_group.resize(mode_size)
        main_layout.addWidget(mode_group)
        range_group.setLayout(range_selector)
        main_layout.addWidget(range_group)
        main_layout.addWidget(self.lcd)
        self.btn_load.setFixedSize(self.btn_load.sizeHint().width(), mode_group.sizeHint().height())
        main_layout.addWidget(self.btn_load)

        vbox = QVBoxLayout()
        vbox.addLayout(box_selector)
        vbox.addWidget(self.dev_id)
        vbox.addLayout(main_layout)

        layer_main_slider = QHBoxLayout()
        layer_main_slider.addWidget(main_slider_label)
        layer_main_slider.addWidget(self.slider)
        layer_main_slider.addWidget(self.main_slider_value)        
        vbox.addLayout(layer_main_slider)

        vbox.addLayout(meas_layout)

        layer_slew = QHBoxLayout()
        layer_slew.addWidget(slew_label)
        layer_slew.addWidget(self.slew_slider)
        layer_slew.addWidget(self.slew_slider_value)
        self.slew_group.setLayout(layer_slew)
        vbox.addWidget(self.slew_group)

        vbox.addWidget(pulse_group)

        self.setLayout(vbox)
         
        self.slider.valueChanged.connect(self.on_main_slider_valueChanged)
        self.resize(350,250)

        timer = QTimer(self)
        timer.setSingleShot(False)
        timer.timeout.connect(self.get_meas_value)
        timer.start(300)

    def get_main_scale_div(self):
        if self.cur_range == "HIGH":
            div_val = 1000
        elif self.cur_range == "MED":
            div_val = 10000
        else:
            div_val = 100000

        return div_val

    def get_cmd(self, cmd):
        try:
            model = self.model.split(",")
            for i in range(0,len(COMMAND_SET)):
                if model[1] in COMMAND_SET[i]["models"]:
                    return COMMAND_SET[i][cmd]

            return COMMAND_SET[0][cmd]
        except Exception as e:
            return None

    @pyqtSlot()
    def get_meas_value(self):
        if self.dev is not None and not self.initalizing:
            try:
                self.dev.write(self.get_cmd("MEAS:CURR"))
                self.meas_curr = self.dev.read().strip()
                self.dev.write(self.get_cmd("MEAS:VOLT"))
                self.meas_volt = self.dev.read().strip()
                self.dev.write(self.get_cmd("MEAS:POW"))
                self.meas_pow = self.dev.read().strip()

                self.failed_read = 0

                self.meas_cur_lcd.display(self.meas_curr)
                self.meas_vol_lcd.display(self.meas_volt)
                self.meas_pow_lcd.display(self.meas_pow)
            except Exception as e:
                print("Read data failed")
                self.failed_read+=1
                if self.failed_read >= 10:
                    self.on_open_click()
                    self.on_open_click()


    def update_range(self):
        div_val = self.get_main_scale_div()
        
        model = self.model.split(",")

        if self.mode == "CC":
            usage_table = current_range_table
        elif self.mode == "CV":
            usage_table = voltage_range_table
        elif self.mode == "CP":
            usage_table = power_range_table
        elif self.mode == "CR":
            usage_table = conductance_range_table

        if model[1] in slew_table:
            if self.cur_range == "HIGH":
                self.slew_slider.setMinimum(slew_table[model[1]][0][0] * 100000)
                self.slew_slider.setMaximum(slew_table[model[1]][0][1] * 100000)
                self.slew_slider.setSingleStep(slew_table[model[1]][0][2] * 100000)

                self.slider.setMinimum(0)
                self.slider.setMaximum(usage_table[model[1]][0] * div_val)
                self.slider.setSingleStep(usage_table[model[1]][0] * div_val / 300)
            elif self.cur_range == "MED":
                self.slew_slider.setMinimum(slew_table[model[1]][1][0] * 100000)
                self.slew_slider.setMaximum(slew_table[model[1]][1][1] * 100000)
                self.slew_slider.setSingleStep(slew_table[model[1]][1][2] * 100000)

                self.slider.setMinimum(0)
                self.slider.setMaximum(usage_table[model[1]][1] * div_val)
                self.slider.setSingleStep(usage_table[model[1]][1] * div_val / 300)
            elif self.cur_range == "LOW":
                self.slew_slider.setMinimum(slew_table[model[1]][2][0] * 100000)
                self.slew_slider.setMaximum(slew_table[model[1]][2][1] * 100000)
                self.slew_slider.setSingleStep(slew_table[model[1]][2][2] * 100000)

                self.slider.setMinimum(0)
                self.slider.setMaximum(usage_table[model[1]][2] * div_val)
                self.slider.setSingleStep(usage_table[model[1]][2] * div_val / 300)

        # Table : https://manual.kikusui.co.jp/P/PLZ4W/i_f_manual/english/Command/curr_slew.html
        if self.get_cmd("SLEW_RATE") is not None:
            self.dev.write("%s?" % (self.get_cmd("SLEW_RATE")))
            self.cur_slew_rate = self.dev.read().strip()
            self.update_slew_value()
            self.slew_group.show()
            print("SLEW RATE: %s" % (self.cur_slew_rate))
        else:
            self.slew_group.hide()

    def update_mode(self):
        div_val = self.get_main_scale_div()
        
        if self.mode == "CC":
            self.dev.write("%s?" % (self.get_cmd("CURRENT")))
            self.cur_current = self.dev.read().strip()
            self.slider.setValue(float(self.cur_current) * div_val)
            self.pulse_enabled.setEnabled(True)
        elif self.mode == "CV":
            self.dev.write("%s?" % (self.get_cmd("VOLTAGE")))
            self.cur_voltage = self.dev.read().strip()
            self.slider.setValue(float(self.cur_voltage) * div_val)
            self.pulse_enabled.setEnabled(False)
        elif self.mode == "CP":
            self.dev.write("%s?" % (self.get_cmd("POWER")))
            self.cur_power = self.dev.read().strip()
            self.slider.setValue(float(self.cur_power) * div_val)
            self.pulse_enabled.setEnabled(False)
        elif self.mode == "CR":
            self.dev.write("%s?" % (self.get_cmd("RESISTANCE")))
            self.cur_resister = self.dev.read().strip()
            self.slider.setValue(float(self.cur_resister) * div_val)
            self.pulse_enabled.setEnabled(False)
        self.update_slider_value()

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
            self.dev_id.setText(self.model)

            mode = self.get_cmd("GET_MODE_FN")(self)
            self.mode = mode
            if mode == "CC":
                self.mode_cc.setChecked(True)
            elif mode == "CV":
                self.mode_cv.setChecked(True)
            elif mode == "CR":
                self.mode_cr.setChecked(True)
            elif mode == "CP":
                self.mode_cp.setChecked(True)

            cur_range = self.get_cmd("GET_RANGE_FN")(self)
            self.cur_range = cur_range
            if cur_range == "LOW":
                self.range_l.setChecked(True)
            elif cur_range == "MED":
                self.range_m.setChecked(True)
            elif cur_range == "HIGH":
                self.range_h.setChecked(True)
            print("Range: %s" % (cur_range))
            self.update_range()
            self.update_mode()

            # https://manual.kikusui.co.jp/P/PLZ4W/i_f_manual/english/Command/curr_prot.html
            # self.dev.write("CURRent:PROTection?")
            # ocp = self.dev.read().strip()
            # print("OCP: %s" % (ocp))

            # https://manual.kikusui.co.jp/P/PLZ4W/i_f_manual/english/Command/pow_prot.html
            # self.dev.write("POWer:PROTection?")
            # opp = self.dev.read().strip()
            # print("OPP: %s" % (opp))

            # https://manual.kikusui.co.jp/P/PLZ4W/i_f_manual/english/Command/volt_prot_stat.html
            # self.dev.write("VOLTage:PROTection:STATe?")
            # under_voltage_prot_enabled = self.dev.read().strip()
            # print("Under Voltage Protect: %s" % (under_voltage_prot_enabled))

            # self.dev.write("POWer:PROTection:UNDer?")
            # uvp = self.dev.read().strip()
            # print("UVP: %s" % (uvp))

            # self.dev.write("VOLTage:RANGe?")
            # uvp_range = self.dev.read().strip()
            # print("UVP Range: %s" % (uvp_range))

            self.dev.write("%s?" % (self.get_cmd("LOAD")))
            self.load_enabled = self.dev.read().strip()
            self.update_load_button()
            print("LOAD ENABLED: %s" % (self.load_enabled))

            self.dev.write("PULSe:FREQuency?")
            self.cur_pulse_freq = self.dev.read().strip()
            self.dev.write("PULSe:DCYCle?")
            self.cur_pulse_duty = self.dev.read().strip()
            self.dev.write("PULSe:LEVel:PERCentage:CURRent?")
            self.cur_pulse_level = self.dev.read().strip()
            self.dev.write("PULSe?")
            self.cur_pulse_enabled = self.dev.read().strip()
            print("Pluse Freq : %s  DUTY: %s%%" % (self.cur_pulse_freq, self.cur_pulse_duty))
            self.update_pulse_info()

            self.initalizing = False
        else:
            self.dev.close()
            self.btn_connect.setText("Open")
            self.dev = None
            self.initalizing = True

    def update_pulse_info(self):
        self.pulse_freq.setValue(float(self.cur_pulse_freq))
        self.pulse_duty.setValue(float(self.cur_pulse_duty) * 10)
        self.pulse_level_slider.setValue(float(self.cur_pulse_level) * 10)
        self.pulse_freq_text.setText("%.0fHz" % (float(self.cur_pulse_freq)))
        self.pulse_duty_text.setText("%.01f%%" % (float(self.cur_pulse_duty)))
        self.pulse_level_text.setText("%.01f%%" % (float(self.cur_pulse_level)))
        if self.cur_pulse_enabled == "1":
            self.pulse_enabled.setChecked(True)
            self.mode_cv.setEnabled(False)
            self.mode_cr.setEnabled(False)
            self.mode_cp.setEnabled(False)
        else:
            self.pulse_enabled.setChecked(False)
            self.mode_cv.setEnabled(True)
            self.mode_cr.setEnabled(True)
            self.mode_cp.setEnabled(True)

    @pyqtSlot()
    def on_pulse_enabled_toggle(self):
        if not self.initalizing:
            self.cur_pulse_enabled = "1" if self.pulse_enabled.isChecked() else "0"
            print("Set Pluse To %s" % (self.cur_pulse_enabled))
            self.dev.write("PULSe %s" % (self.cur_pulse_enabled))
            self.update_pulse_info()

    @pyqtSlot()
    def on_pulse_freq_slider_valueChanged(self):
        if self.initalizing:
            return
        print("Set Pluse Frequence to %d" % (self.pulse_freq.value()))
        self.cur_pulse_freq = self.pulse_freq.value()
        self.dev.write("PULSe:FREQuency %s" % (self.cur_pulse_freq))
        self.update_pulse_info()

    @pyqtSlot()
    def on_pulse_duty_slider_valueChanged(self):
        if self.initalizing:
            return
        print("Set Pluse Duty to %.01f%%" % (self.pulse_duty.value()/10))
        self.cur_pulse_duty = self.pulse_duty.value()/10
        self.dev.write("PULSe:DCYCLe %s" % (self.cur_pulse_duty))
        self.update_pulse_info()

    @pyqtSlot()
    def on_pulse_level_slider_valueChanged(self):
        if self.initalizing:
            return
        print("Set Pluse Level to %.01f%%" % (self.pulse_level_slider.value()/10))
        self.cur_pulse_level = (self.pulse_level_slider.value()/10)
        self.dev.write("PULSe:LEVel:PERCentage:CURRent %s" % (self.cur_pulse_level))
        self.update_pulse_info()

    @pyqtSlot()
    def on_mode_select(self,b):
        if b.isChecked() and not self.initalizing:
            print("Set MODE = %s  %d" % (b.text(), b.isChecked()))
            self.get_cmd("SET_MODE_FN")(self,b.text())
            self.mode = b.text()
            self.update_mode()
            self.update_range()

    @pyqtSlot()
    def on_range_select(self,b):
        if b.isChecked() and not self.initalizing:
            print("Set Range = %s  %d" % (b.text(), b.isChecked()))
            self.get_cmd("SET_RANGE_FN")(self, b.text())
            self.cur_range = b.text()
            self.update_range()
            self.update_mode()

    def update_slider_value(self):
        div_val = self.get_main_scale_div()
        
        if self.cur_range == "HIGH":
            self.lcd.display("%.02f" % (self.slider.value()/div_val))
        elif self.cur_range == "MED":
            self.lcd.display("%.03f" % (self.slider.value()/div_val))
        elif self.cur_range == "LOW":
            self.lcd.display("%.04f" % (self.slider.value()/div_val))

        if self.mode == "CC":
            self.main_slider_value.setText("%.04f A" % (self.slider.value()/div_val))
        elif self.mode == "CV":
            self.main_slider_value.setText("%.04f V" % (self.slider.value()/div_val))
        elif self.mode == "CP":
            self.main_slider_value.setText("%.04f W" % (self.slider.value()/div_val))
        elif self.mode == "CR":
            self.main_slider_value.setText("%.04f Ω" % (1/(self.slider.value()/div_val) if (self.slider.value()/div_val) > 0 else 7500))

    @pyqtSlot()
    def on_main_slider_valueChanged(self):
        div_val = self.get_main_scale_div()
        
        if self.initalizing:
            return
        print("Set Power to %d" % (self.slider.value()))
        self.update_slider_value()
        if self.mode == "CC":
            self.dev.write("CURRent %.06f" % (self.slider.value()/div_val))
        elif self.mode == "CV":
            self.dev.write("VOLTage %.06f" % (self.slider.value()/div_val))
        elif self.mode == "CP":
            self.dev.write("POWer %.06f" % (self.slider.value()/div_val))
        elif self.mode == "CR":
            self.dev.write("COND %.06f" % (self.slider.value()/div_val))

    def update_slew_value(self):
        self.slew_slider.setValue(float(self.cur_slew_rate) * 100000)
        if self.slew_slider.value() >= 100000:
            self.slew_slider_value.setText("%.03fA/μs" % (self.slew_slider.value()/ 100000))
        else:
            self.slew_slider_value.setText("%.01fmA/μs" % (self.slew_slider.value()/100))

    @pyqtSlot()
    def on_slew_value_changed(self):
        if self.initalizing:
            return
        print("Set Slew Rate to %.06f A/us" % (self.slew_slider.value()/100000))
        self.cur_slew_rate = self.slew_slider.value() / 100000
        if self.slew_slider.value() >= 100000:
            self.dev.write("%s %.03f" % (self.get_cmd("SLEW_RATE"), self.slew_slider.value()/100000))
        else:
            self.dev.write("%s %.03f" % (self.get_cmd("SLEW_RATE"), self.slew_slider.value()/100000))

        self.update_slew_value()

    def eventFilter(self, obj, event):
        if obj == self.main_slider_value and event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
                try:
                    div_val = self.get_main_scale_div()
                    if self.mode == "CR" and float(self.main_slider_value.text()) * div_val > 0:
                        self.slider.setValue(1/float(self.main_slider_value.text()) * div_val)
                    else:
                        self.slider.setValue(float(self.main_slider_value.text()) * div_val)

                    self.on_main_slider_valueChanged()
                    self.main_slider_value.selectAll()
                except Exception as e:
                    print("INPUT INVALID")
                    self.update_slider_value()
            elif event.key() == Qt.Key_Escape:
                self.update_slider_value()
        elif obj == self.pulse_freq_text and event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
                try:
                    self.pulse_freq.setValue(float(self.pulse_freq_text.text()))
                    self.pulse_freq_text.selectAll()
                except Exception as e:
                    print("INPUT INVALID")
                    self.update_pulse_info()
            elif event.key() == Qt.Key_Escape:
                self.update_pulse_info()
        elif obj == self.pulse_duty_text and event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
                try:
                    self.pulse_duty.setValue(float(self.pulse_duty_text.text()) * 10)
                    self.pulse_duty_text.selectAll()
                except Exception as e:
                    print("INPUT INVALID")
                    self.update_pulse_info()
            elif event.key() == Qt.Key_Escape:
                self.update_pulse_info()
        elif obj == self.pulse_level_text and event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
                try:
                    self.pulse_level_slider.setValue(float(self.pulse_level_text.text()) * 10)
                    self.pulse_level_text.selectAll()
                except Exception as e:
                    print("INPUT INVALID")
                    self.update_pulse_info()
            elif event.key() == Qt.Key_Escape:
                self.update_pulse_info()
        elif event.type() == QEvent.Enter and obj in [self.main_slider_value, self.pulse_freq_text, self.pulse_duty_text, self.pulse_level_text]:
            rc = super(Kikusui, self).eventFilter(obj, event)
            obj.setFocus()
            obj.selectAll()
            return rc
        #     print(obj)
        return super(Kikusui, self).eventFilter(obj, event)

    def update_load_button(self):
        if self.load_enabled == "0":
            self.btn_load.setStyleSheet("background-color: #b1e46e; color: black;")
            self.mode_cc.setEnabled(True)
            self.mode_cv.setEnabled(True)
            self.mode_cr.setEnabled(True)
            self.mode_cp.setEnabled(True)
            self.range_l.setEnabled(True)
            self.range_m.setEnabled(True)
            self.range_h.setEnabled(True)
        else:
            self.btn_load.setStyleSheet("background-color: #b92919;")
            self.mode_cc.setEnabled(False)
            self.mode_cv.setEnabled(False)
            self.mode_cr.setEnabled(False)
            self.mode_cp.setEnabled(False)
            self.range_l.setEnabled(False)
            self.range_m.setEnabled(False)
            self.range_h.setEnabled(False)

    @pyqtSlot()
    def on_btn_load_clicked(self):
        if self.initalizing:
            return
        print("Change Load State")
        if self.load_enabled == "0":
            self.dev.write("%s 1" % (self.get_cmd("LOAD")))
            self.load_enabled = "1"
        else:
            self.dev.write("%s 0" % (self.get_cmd("LOAD")))
            self.load_enabled = "0"

        self.update_load_button()
    
    def keyPressEvent(self, e):
        if e.key() == Qt.Key_F5:
            self.on_btn_load_clicked()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    qb = Kikusui()
    qb.show()
    sys.exit(app.exec_())