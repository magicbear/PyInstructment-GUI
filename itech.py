#coding:utf-8

import sys
from libs.itech import DCLoad
from PyQt5.QtCore import (Qt, QEvent, QTimer)
from PyQt5.QtWidgets import (QWidget, QLCDNumber, QSlider, QVBoxLayout, QApplication, QSizePolicy)
from PyQt5.QtWidgets import *
from PyQt5.QtCore import pyqtSlot, pyqtSignal
from PyQt5.QtGui import QColor
import time

class ITechLoad(QWidget):
    modelChanged = pyqtSignal(str)

    def __init__(self,parent=None):
        QWidget.__init__(self)

        self.dev = None
        self.model = None
        self.mode = None
        self.initalizing = True
        self.load_enabled = True
        self.cur_pulse_enabled = False
        self.remote_enabled = False
        self.failed_read = 0

        self.setWindowTitle('ITech Electric Load')

        self.dev_selector = QLineEdit("192.168.9.15:23", self)
        # QComboBox(self)
        # self.dev_selector.addItems(res)

        self.btn_connect = QPushButton('Open', self)
        self.btn_connect.clicked.connect(self.on_open_click)
        self.btn_connect.setToolTip('This is an example button')

        # Device Selector
        box_selector = QHBoxLayout()
        box_selector.addWidget(self.dev_selector)
        box_selector.addWidget(self.btn_connect)

        # Mode Zone
        mode_selector = QVBoxLayout()
        mode_group = QGroupBox("Mode", self)
        self.mode_cc = QRadioButton("CC")
        self.mode_cc.toggled.connect(lambda:self.on_mode_select(self.mode_cc))
        self.mode_cv = QRadioButton("CV")
        self.mode_cv.toggled.connect(lambda:self.on_mode_select(self.mode_cv))
        self.mode_cr = QRadioButton("CR")
        self.mode_cr.toggled.connect(lambda:self.on_mode_select(self.mode_cr))
        self.mode_cp = QRadioButton("CW")
        self.mode_cp.toggled.connect(lambda:self.on_mode_select(self.mode_cp))
        mode_selector.addWidget(self.mode_cc)
        mode_selector.addWidget(self.mode_cv)
        mode_selector.addWidget(self.mode_cr)
        mode_selector.addWidget(self.mode_cp)


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
        self.slider.setMinimum(0)
        self.slider.setMaximum(1000)
        self.main_slider_value = QLineEdit("0.00A", self)
        self.main_slider_value.installEventFilter(self)
        # sp_slider_value = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        # sp_slider_value.setHorizontalStretch(0.1)
        # self.main_slider_value.setSizePolicy(sp_slider_value)
        self.main_slider_value.setFixedSize(80, 20)

        # Meassure Zone Start
        mode_meas_vol = QGroupBox("Voltage", self)
        mode_meas_cur = QGroupBox("Current", self)
        mode_meas_pow = QGroupBox("Power", self)

        meas_vol_layout = QHBoxLayout()
        self.meas_vol_lcd = QLCDNumber(6, self)
        # get the palette
        palette = self.meas_vol_lcd.palette()
        palette.setColor(palette.WindowText, QColor(255, 0, 0))
        self.meas_vol_lcd.setPalette(palette)
        meas_vol_layout.addWidget(self.meas_vol_lcd)
        mode_meas_vol.setLayout(meas_vol_layout)

        meas_cur_layout = QHBoxLayout()
        self.meas_cur_lcd = QLCDNumber(6, self)
        palette = self.meas_cur_lcd.palette()
        palette.setColor(palette.WindowText, QColor(0, 255, 0))
        self.meas_cur_lcd.setPalette(palette)
        meas_cur_layout.addWidget(self.meas_cur_lcd)
        mode_meas_cur.setLayout(meas_cur_layout)

        meas_pow_layout = QHBoxLayout()
        self.meas_pow_lcd = QLCDNumber(6, self)
        palette = self.meas_pow_lcd.palette()
        palette.setColor(palette.WindowText, QColor(0, 128, 255))
        self.meas_pow_lcd.setPalette(palette)
        meas_pow_layout.addWidget(self.meas_pow_lcd)
        mode_meas_pow.setLayout(meas_pow_layout)

        self.meas_vol_lcd.setSegmentStyle(QLCDNumber.Flat)
        self.meas_cur_lcd.setSegmentStyle(QLCDNumber.Flat)
        self.meas_pow_lcd.setSegmentStyle(QLCDNumber.Flat)

        mode_meas_vol.setStyleSheet("QGroupBox {padding: 5px; background-color: #222; color: #fff; border-radius: 3px; margin-top: 1em} QGroupBox::title { margin-top: 0em; subcontrol-origin: padding; subcontrol-position: left top; }");
        mode_meas_cur.setStyleSheet("QGroupBox {padding: 5px; background-color: #222; color: #fff; border-radius: 3px; margin-top: 1em} QGroupBox::title { margin-top: 0em; subcontrol-origin: padding; subcontrol-position: left top; }");
        mode_meas_pow.setStyleSheet("QGroupBox {padding: 5px; background-color: #222; color: #fff; border-radius: 3px; margin-top: 1em} QGroupBox::title { margin-top: 0em; subcontrol-origin: padding; subcontrol-position: left top; }");
        self.meas_vol_lcd.setStyleSheet("background-color: #222; border: 0px ;")
        self.meas_cur_lcd.setStyleSheet("background-color: #222; border: 0px ;")
        self.meas_pow_lcd.setStyleSheet("background-color: #222; border: 0px ;")


        self.lcd.setSegmentStyle(QLCDNumber.Flat)
        palette = self.lcd.palette()
        palette.setColor(palette.WindowText, QColor(255, 128, 0))
        self.lcd.setPalette(palette)
        self.lcd.setStyleSheet("background-color: #222; border: 0px; border-radius: 5px;")

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
        self.pulse_freq.setSingleStep(100)

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
        main_layout.addWidget(self.lcd)
        self.btn_load.setFixedSize(self.btn_load.sizeHint().width(), mode_group.sizeHint().height())
        main_layout.addWidget(self.btn_load)

        vbox = QVBoxLayout()
        vbox.addLayout(box_selector)
        vbox.addLayout(main_layout)

        layer_main_slider = QHBoxLayout()
        layer_main_slider.addWidget(main_slider_label)
        layer_main_slider.addWidget(self.slider)
        layer_main_slider.addWidget(self.main_slider_value)        
        vbox.addLayout(layer_main_slider)

        vbox.addLayout(meas_layout)

        # Slew Rate Zone
        layer_slew = QVBoxLayout()

        layer_slew_up = QHBoxLayout()
        self.slew_group = QGroupBox("Slew", self)
        self.slew_slider = QSlider(Qt.Horizontal,self)
        self.slew_slider.valueChanged.connect(self.on_slew_value_changed)
        slew_label = QLabel("UP Slew Rate:",self)
        self.slew_slider_value = QLabel("0.00A/μs", self)

        self.slew_slider.setMinimum(0.01 * 1000)
        self.slew_slider.setMaximum(6     * 1000)
        self.slew_slider.setSingleStep(1)

        layer_slew_up.addWidget(slew_label)
        layer_slew_up.addWidget(self.slew_slider)
        layer_slew_up.addWidget(self.slew_slider_value)


        layer_slew_down = QHBoxLayout()
        self.slew_slider_down = QSlider(Qt.Horizontal,self)
        self.slew_slider_down.valueChanged.connect(self.on_slew_down_value_changed)
        slew_label = QLabel("DL Slew Rate:",self)
        self.slew_slider_down_value = QLabel("0.00A/μs", self)

        self.slew_slider_down.setMinimum(0.001 * 1000)
        self.slew_slider_down.setMaximum(6     * 1000)
        self.slew_slider_down.setSingleStep(1)

        layer_slew_down.addWidget(slew_label)
        layer_slew_down.addWidget(self.slew_slider_down)
        layer_slew_down.addWidget(self.slew_slider_down_value)


        layer_slew.addLayout(layer_slew_up)
        layer_slew.addLayout(layer_slew_down)

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
        if self.mode == "CC" or self.mode == "CR":
            return 1000
        else:
            return 100

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
                load_info = self.dev.GetInputValues()
                self.meas_curr = load_info["current"]
                self.meas_volt = load_info["voltage"]
                self.meas_pow =  load_info["power"]
                self.remote_enabled = load_info["op_state"] & 0x4 == 0x4
                if (load_info["op_state"] & 0x8 == 0x8) != self.load_enabled:
                    self.load_enabled = load_info["op_state"] & 0x8 == 0x8
                    self.update_load_button()

                self.cur_pulse_enabled = load_info["work_mode"] == 2

                if not self.remote_enabled:
                    # self.dev.SetRemoteControl()
                    self.mode = self.dev.GetMode()
                    self.update_mode()

                self.failed_read = 0

                self.meas_cur_lcd.display(self.meas_curr)
                self.meas_vol_lcd.display(self.meas_volt)
                self.meas_pow_lcd.display(self.meas_pow)
            except Exception as e:
                print("Read data failed", e)
                self.failed_read+=1
                if self.failed_read >= 10:
                    self.on_open_click()
                    self.on_open_click()

    def update_mode(self):
        div_val = self.get_main_scale_div()

        self.initalizing = True

        transient = self.dev.GetTransient(self.mode)
        dur_time = (transient[1] + transient[3])/10
        self.cur_pulse_freq = 1/dur_time
        self.cur_pulse_duty = 100 * transient[1] / (transient[1] + transient[3])

        if self.mode == "CC":
            self.mode_cc.setChecked(True)
            self.cur_current = self.dev.GetCCCurrent()
            self.slider.setValue(float(self.cur_current) * div_val)
            self.slider.setMaximum(self.dev.GetMaxCurrent() * div_val) # Max 60A
            self.cur_pulse_level = 100 * transient[2] / self.cur_current if self.cur_current != 0 else 0
            self.pulse_enabled.setEnabled(True)
        elif self.mode == "CV":
            self.mode_cv.setChecked(True)
            self.cur_voltage = self.dev.GetCVVoltage()
            self.slider.setValue(float(self.cur_voltage) * div_val)
            self.slider.setMinimum(0.1 * div_val) # Min 0.1V
            self.slider.setMaximum(self.dev.GetMaxVoltage() * div_val) # Max 120V
            self.cur_pulse_level = 100 * transient[2] / self.cur_voltage if self.cur_voltage != 0 else 0
            self.pulse_enabled.setEnabled(False)
        elif self.mode == "CW":
            self.mode_cp.setChecked(True)
            self.cur_power = self.dev.GetCWPower()
            self.slider.setValue(float(self.cur_power) * div_val)
            self.slider.setMaximum(self.dev.GetMaxPower() * div_val) # Max 300W
            self.cur_pulse_level = 100 * transient[2] / self.cur_power if self.cur_power != 0 else 0
            self.pulse_enabled.setEnabled(False)
        elif self.mode == "CR":
            self.mode_cr.setChecked(True)
            self.cur_resister = self.dev.GetCRResistance()
            self.slider.setValue(float(self.cur_resister) * div_val)
            self.slider.setMinimum(0.05 * div_val) # Min 0.05Ohm
            self.slider.setMaximum(7500 * div_val) # Max 7500Ohm
            self.cur_pulse_level = 100 * transient[2] / self.cur_resister if self.cur_resister != 0 else 0
            self.pulse_enabled.setEnabled(False)

        self.update_pulse_info()
        self.cur_up_slew_rate = self.dev.GetUpSlewRate()
        self.cur_down_slew_rate = self.dev.GetDownSlewRate()
        self.update_slew_value()
        self.update_slew_down_value()
        self.update_slider_value()
        self.initalizing = False

    @pyqtSlot()
    def on_open_click(self):
        if self.dev is None:
            self.initalizing = True

            self.dev = DCLoad()
            host = self.dev_selector.text().split(":")
            self.dev.Initialize(host[0], int(host[1]))

            self.btn_connect.setText("Close")
            product_info = self.dev.GetProductInformation()
            self.model = product_info["model"]+" "+product_info["serial_number"]+"  FW: "+product_info["fw"]
            self.modelChanged.emit(self.model)
            self.setWindowTitle(self.model)

            self.mode = self.dev.GetMode()
            self.update_mode()

            # self.dev.write("PULSe:FREQuency?")
            # self.cur_pulse_freq = self.dev.read().strip()
            # self.dev.write("PULSe:DCYCle?")
            # self.cur_pulse_duty = self.dev.read().strip()
            # self.dev.write("PULSe:LEVel:PERCentage:CURRent?")
            # self.cur_pulse_level = self.dev.read().strip()
            # self.dev.write("PULSe?")
            # self.cur_pulse_enabled = self.dev.read().strip()
            # print("Pluse Freq : %s  DUTY: %s%%" % (self.cur_pulse_freq, self.cur_pulse_duty))
            # self.update_pulse_info()

            self.initalizing = False
            self.load_enabled = None
            self.get_meas_value()

        else:
            self.dev.SetLocalControl()
            self.dev.close()
            self.btn_connect.setText("Open")
            self.dev = None
            self.initalizing = True
        
        self.repaint()

    def update_pulse_info(self):
        self.pulse_freq.setValue(float(self.cur_pulse_freq))
        self.pulse_duty.setValue(float(self.cur_pulse_duty) * 10)
        self.pulse_level_slider.setValue(float(self.cur_pulse_level) * 10)
        self.pulse_freq_text.setText("%.0fHz" % (float(self.cur_pulse_freq)))
        self.pulse_duty_text.setText("%.01f%%" % (float(self.cur_pulse_duty)))
        self.pulse_level_text.setText("%.01f%%" % (float(self.cur_pulse_level)))
        if self.cur_pulse_enabled == True:
            self.pulse_enabled.setChecked(True)
            self.mode_cv.setEnabled(False)
            self.mode_cr.setEnabled(False)
            self.mode_cp.setEnabled(False)
        else:
            self.pulse_enabled.setChecked(False)
            self.mode_cv.setEnabled(True)
            self.mode_cr.setEnabled(True)
            self.mode_cp.setEnabled(True)

    def update_pulse_params(self):
        if not self.initalizing:
            if not self.remote_enabled:
                self.dev.SetRemoteControl()
            t_freq_ms = 1/self.cur_pulse_freq  * 10000
            if self.mode == "CC":
                # print(t_freq_ms * self.cur_pulse_duty / 100.0)
                print(self.mode, self.cur_current, t_freq_ms * (1-self.cur_pulse_duty / 100.0) / 1000.0, self.cur_pulse_level / 100.0 * self.cur_current, t_freq_ms * (self.cur_pulse_duty / 100.0) / 1000.0)
                self.dev.SetTransient(self.mode, self.cur_current, t_freq_ms * (1-self.cur_pulse_duty / 100.0) / 1000.0, self.cur_pulse_level / 100.0 * self.cur_current, t_freq_ms * (self.cur_pulse_duty / 100.0) / 1000.0)
                print(self.dev.GetTransient(self.mode))

    @pyqtSlot()
    def on_pulse_enabled_toggle(self):
        if not self.initalizing:
            self.cur_pulse_enabled = True if self.pulse_enabled.isChecked() else False
            self.update_pulse_params()
            self.dev.SetFunction("fixed" if self.cur_pulse_enabled == False else "transient")
            self.dev.ForceTrigger()
            print("Set Pluse To %s" % (self.cur_pulse_enabled))
            self.update_pulse_params()
            self.update_pulse_info()

    @pyqtSlot()
    def on_pulse_freq_slider_valueChanged(self):
        if self.initalizing:
            return

        self.cur_pulse_freq = self.pulse_freq.value()
        print("Set Pluse Frequence to %d" % (self.pulse_freq.value()))
        self.update_pulse_params()
        self.update_pulse_info()

    @pyqtSlot()
    def on_pulse_duty_slider_valueChanged(self):
        if self.initalizing:
            return
        print("Set Pluse Duty to %.01f%%" % (self.pulse_duty.value()/10))
        self.cur_pulse_duty = self.pulse_duty.value()/10
        self.update_pulse_params()
        self.update_pulse_info()

    @pyqtSlot()
    def on_pulse_level_slider_valueChanged(self):
        if self.initalizing:
            return
        print("Set Pluse Level to %.01f%%" % (self.pulse_level_slider.value()/10))
        self.cur_pulse_level = (self.pulse_level_slider.value()/10)
        self.update_pulse_params()
        self.update_pulse_info()

    @pyqtSlot()
    def on_mode_select(self,b):
        if b.isChecked() and not self.initalizing:
            print("Set MODE = %s  %d" % (b.text(), b.isChecked()))
            if not self.remote_enabled:
                self.dev.SetRemoteControl()
            self.dev.SetMode(b.text())
            self.mode = b.text()
            self.update_mode()

    def update_slider_value(self):
        div_val = self.get_main_scale_div()


        if self.mode == "CC":
            self.lcd.display("%.03f" % (self.slider.value()/div_val))
            self.main_slider_value.setText("%.03f A" % (self.slider.value()/div_val))
        elif self.mode == "CV":
            self.lcd.display("%.02f" % (self.slider.value()/div_val))
            self.main_slider_value.setText("%.02f V" % (self.slider.value()/div_val))
        elif self.mode == "CW":
            self.lcd.display("%.02f" % (self.slider.value()/div_val))
            self.main_slider_value.setText("%.02f W" % (self.slider.value()/div_val))
        elif self.mode == "CR":
            if self.slider.value() /div_val < 100:
                self.lcd.display("%.03f" % (self.slider.value()/div_val))
            elif self.slider.value() /div_val < 1000:
                self.lcd.display("%.02f" % (self.slider.value()/div_val))
            else:
                self.lcd.display("%.01f" % (self.slider.value()/div_val))
            self.main_slider_value.setText("%.03f Ω" % (self.slider.value()/div_val))

    @pyqtSlot()
    def on_main_slider_valueChanged(self):
        div_val = self.get_main_scale_div()
        
        if self.initalizing:
            return

        if not self.remote_enabled:
            self.dev.SetRemoteControl()
        self.update_slider_value()
        if self.mode == "CC":
            self.cur_current = self.slider.value()/div_val
            self.dev.SetCCCurrent(self.slider.value()/div_val)
        elif self.mode == "CV":
            self.cur_voltage = self.slider.value()/div_val
            self.dev.SetCVVoltage(self.slider.value()/div_val)
        elif self.mode == "CW":
            self.cur_power = self.slider.value()/div_val
            self.dev.SetCWPower(self.slider.value()/div_val)
        elif self.mode == "CR":
            self.cur_resister = self.slider.value()/div_val
            self.dev.SetCRResistance(self.slider.value()/div_val)

        if self.cur_pulse_enabled:
            self.update_pulse_params()

    def update_slew_value(self):
        self.slew_slider.setValue(float(self.cur_up_slew_rate) * 1000)
        if self.slew_slider.value() >= 1000:
            self.slew_slider_value.setText("%.03fA/μs" % (self.slew_slider.value()/ 1000))
        else:
            self.slew_slider_value.setText("%.01fmA/μs" % (self.slew_slider.value()))

    @pyqtSlot()
    def on_slew_value_changed(self):
        if self.initalizing:
            return
        if not self.remote_enabled:
            self.dev.SetRemoteControl()
        print("Set Slew Rate to %.06f A/us" % (self.slew_slider.value()/1000))
        self.cur_up_slew_rate = self.slew_slider.value() / 1000
        self.dev.SetUpSlewRate(self.slew_slider.value() / 1000)

        self.update_slew_value()

    def update_slew_down_value(self):
        self.slew_slider_down.setValue(float(self.cur_down_slew_rate) * 1000)
        if self.slew_slider_down.value() >= 1000:
            self.slew_slider_down_value.setText("%.03fA/μs" % (self.slew_slider_down.value()/ 1000))
        else:
            self.slew_slider_down_value.setText("%.01fmA/μs" % (self.slew_slider_down.value()))

    @pyqtSlot()
    def on_slew_down_value_changed(self):
        if self.initalizing:
            return
        if not self.remote_enabled:
            self.dev.SetRemoteControl()
        print("Set Slew Rate to %.06f A/us" % (self.slew_slider_down.value()/1000))
        self.cur_down_slew_rate = self.slew_slider_down.value() / 1000
        self.dev.SetDownSlewRate(self.slew_slider_down.value() / 1000)

        self.update_slew_down_value()

    def eventFilter(self, obj, event):
        if obj == self.main_slider_value and event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
                try:
                    div_val = self.get_main_scale_div()
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
            rc = super(self.__class__, self).eventFilter(obj, event)
            if self.dev is not None and not self.remote_enabled:
                self.dev.SetRemoteControl()
            obj.setFocus()
            obj.selectAll()
            return rc
        return super(self.__class__, self).eventFilter(obj, event)

    def update_load_button(self):
        if self.load_enabled == False:
            self.btn_load.setStyleSheet("background-color: #b1e46e; color: black;")
            self.mode_cc.setEnabled(True)
            self.mode_cv.setEnabled(True)
            self.mode_cr.setEnabled(True)
            self.mode_cp.setEnabled(True)
        else:
            self.btn_load.setStyleSheet("background-color: #b92919;")
            self.mode_cc.setEnabled(False)
            self.mode_cv.setEnabled(False)
            self.mode_cr.setEnabled(False)
            self.mode_cp.setEnabled(False)

    @pyqtSlot()
    def on_btn_load_clicked(self):
        if self.initalizing:
            return
        print("Change Load State")
        if not self.remote_enabled:
            self.dev.SetRemoteControl()
        if self.load_enabled == False:
            self.dev.TurnLoadOn()
            self.load_enabled = True
        else:
            self.dev.TurnLoadOff()
            self.load_enabled = False

        self.update_load_button()
    
    def keyPressEvent(self, e):
        if e.key() == Qt.Key_F5:
            self.on_btn_load_clicked()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    qb = ITechLoad()
    qb.show()
    sys.exit(app.exec_())