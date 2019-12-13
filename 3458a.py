#coding:utf-8

import visa
import sys
from PyQt5.QtCore import (Qt, QEvent, QTimer, QPointF, QRectF)
from PyQt5.QtWidgets import (QWidget, QLCDNumber, QSlider, QVBoxLayout, QApplication, QSizePolicy)
from PyQt5.QtWidgets import *
from PyQt5.QtCore import pyqtSlot
from PyQt5.QtGui import (QColor, QBrush)
import time
import threading
from PyQt5.QtChart import *
from collections import deque
import numpy as np

class CollectThread(threading.Thread):
    def __init__(self, win):
        threading.Thread.__init__(self)
        self.dev = None
        self.dev_port = None
        self.res = None
        self.win = win
        self.pid_resistor = 0
        self.pid_voltage = 0
        self.pid_last_voltage = 0
        self.pid_current = 0
        self.PID_VALUE = None
        self.pid = None
        self.terminated = False
        self.cmd_queue = deque([])

    def run(self):
        self.rm = visa.ResourceManager("@ni")
        self.res = self.rm.list_resources()
        while not self.terminated:
            if self.dev is None and self.dev_port is None:
                time.sleep(0.01)
                continue
            if self.dev is None:
                print("Opening Resource")
                self.dev = self.rm.open_resource(self.dev_port)
                print("Open success")

            if self.dev is not None and not self.win.initalizing:
                try:
                    while len(self.cmd_queue) > 0:
                        rcmd = self.cmd_queue.popleft()
                        print(rcmd)
                        self.dev.write(rcmd)

                    if self.win.state['TRIG'] != '4':
                        # self.dev.write(" ")
                        self.win.meas = float(self.dev.read().strip())
                        self.win.meas_data.append(self.win.meas)
                    
                    # time.sleep(0.5)
                except Exception as e:
                    print("Read data failed: %s" % (str(e)))
            else:
                time.sleep(0.1)

class InstChart(QChartView):
    def __init__(self, parent):
        QChartView.__init__(self, parent)
        self.meas_data = None
        self.m_coordX = QGraphicsSimpleTextItem(self.chart())
        self.lineItem = QGraphicsLineItem(self.chart())
        self.m_coordX.setZValue(100)
        self.installEventFilter(self)
        self.acceptUpdate = True

    @pyqtSlot()
    def mouseMoveEvent(self, event):
        xyVal = self.chart().mapToValue(event.pos())

        if xyVal.x() > 0 and int(xyVal.x()) < self.chart().series()[0].count():
            dataPos = self.chart().mapToPosition(QPointF(int(xyVal.x()), self.meas_data[int(xyVal.x())]))

            self.m_coordX.setPos(dataPos.x() + 5, dataPos.y() + 5)
            self.m_coordX.setText("%g, %f" % (int(xyVal.x()), self.meas_data[int(xyVal.x())]))

            # #get axis min, max value to calculate position
            # self.min_x, self.min_y = self.chart().AxisX().min(), self.chart().yAxis().min()
            # self.max_x, self.max_y = self.chart().AxisX().max(), self.chart().yAxis().max()

            # self.point_bottom = self.chart().mapToPosition(QPointF(self.min_x, self.min_y))
            # self.point_top = self.chart().mapToPosition(QPointF(self.min_x, self.max_y))

            line = self.lineItem.line()
            line.setLine(dataPos.x(), self.chart().plotArea().top(), dataPos.x(), self.chart().plotArea().bottom() )
            self.lineItem.setLine(line)
            # print(event, self.m_coordX)

    @pyqtSlot()
    def wheelEvent(self, event):
        if event.angleDelta().y() > 0:
            factor = 2.0
        else:
            factor = 0.5

        r = QRectF(self.chart().plotArea().left(),self.chart().plotArea().top(),
                                    self.chart().plotArea().width()/factor,self.chart().plotArea().height())
        mousePos = event.pos()
        r.moveCenter(self.chart().mapToPosition(self.chart().mapToValue(mousePos)))
        self.chart().zoomIn(r)
        delta = self.chart().plotArea().center() -mousePos
        self.chart().scroll(delta.x(),0)
        # print("Wheel Event")
        # self.chart().zoom(0.5 if event.angleDelta().y() > 0 else 2.0)
        event.accept()
        return super(QChartView, self).wheelEvent(event)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Enter:
            self.acceptUpdate = False
            rc = super(self.__class__, self).eventFilter(obj, event)
            return rc
        elif event.type() == QEvent.Leave:
            self.acceptUpdate = True
            rc = super(self.__class__, self).eventFilter(obj, event)
            return rc
        return super(self.__class__, self).eventFilter(obj, event)


class SigSlot(QWidget):
    def __init__(self,parent=None):
        QWidget.__init__(self)
        self.comm_th = CollectThread(self)
        self.comm_th.start()
        
        self.meas = None
        self.dev = None
        self.model = None
        self.meas_count = 0
        self.state = {}
        self.initalizing = True
        # self.meas_data = []

        self.setWindowTitle('Keysight 3458A')

        self.dev_selector = QComboBox(self)
        while self.comm_th.res is None:
            time.sleep(0.01)
        self.dev_selector.addItems(self.comm_th.res)

        self.btn_connect = QPushButton('Open', self)
        self.btn_connect.clicked.connect(self.on_open_click)

        # Device Selector
        box_selector = QHBoxLayout()
        box_selector.addWidget(self.dev_selector)
        box_selector.addWidget(self.btn_connect)

        self.dev_id = QLineEdit(self)

        # Options Zone
        opt_selector = QVBoxLayout()
        opt_group = QGroupBox("Options", self)
        opt_group.setLayout(opt_selector)

        if True:     # Options Zone
            opt_fn = QHBoxLayout()
            opt_fn.addWidget(QLabel("FUNC:", self))
            self.opt_fn = QComboBox(self)
            self.opt_fn.addItems(["DCV","ACV","ACDCV","OHM","OHMF","DCI","ACI","ACDCI","FREQ","PER","DSAC","DSDC","SSAC","SSDC"])
            self.opt_fn.currentTextChanged.connect(lambda:self.on_opt_changed("FUNC", self.opt_fn))
            opt_fn.addWidget(self.opt_fn)
            opt_selector.addLayout(opt_fn)

            opt_emask = QHBoxLayout()
            opt_emask.addWidget(QLabel("NDIG:", self))
            self.opt_ndig = QComboBox(self)
            self.opt_ndig.addItems(["4","5","6","7","8"])
            self.opt_ndig.currentTextChanged.connect(lambda:self.on_opt_changed("NDIG", self.opt_ndig))
            opt_emask.addWidget(self.opt_ndig)
            opt_selector.addLayout(opt_emask)

            opt_nplc = QHBoxLayout()
            opt_nplc.addWidget(QLabel("NPLC:", self))
            self.opt_nplc = QComboBox(self)
            self.opt_nplc.addItems(["0.01", "0.1", "1", "2", "10", "20", "50", "100"])
            self.opt_nplc.currentTextChanged.connect(lambda:self.on_opt_changed("NPLC", self.opt_nplc))
            opt_nplc.addWidget(self.opt_nplc)
            opt_selector.addLayout(opt_nplc)

            opt_nrdgs = QHBoxLayout()
            opt_nrdgs.addWidget(QLabel("NRDGS:", self))
            self.opt_nrdgs = QComboBox(self)
            self.opt_nrdgs.addItems(["1", "5", "10"])
            self.opt_nrdgs.currentTextChanged.connect(lambda:self.on_opt_changed("NRDGS", self.opt_nrdgs))
            opt_nrdgs.addWidget(self.opt_nrdgs)
            opt_selector.addLayout(opt_nrdgs)

            opt_math = QHBoxLayout()
            opt_math.addWidget(QLabel("MATH:", self))
            self.opt_math = QComboBox(self)
            self.opt_math.addItems(["OFF", "CONT", "CTHRM", "DB", "DBM", "FILTER", "NULL", "PERC", "PFAIL", "RMS", "SCALE", "STAT", "CTHRM2K", "CTHRM10K", "FTHRM2K", "FTHRM10K", "CRTD85", "CRTD92", "FRTD85", "FRTD92"])
            self.opt_math.currentTextChanged.connect(lambda:self.on_opt_changed("MATH", self.opt_math))
            opt_math.addWidget(self.opt_math)
            opt_selector.addLayout(opt_math)
        

        # CHART
        self.series_1 = QLineSeries() #定义LineSerise，将类QLineSeries实例化
        # self._1_point_0 = QPointF(0.00,0.00) #定义折线坐标点
        # self._1_point_1 = QPointF(0.80,6.00)
        # self._1_point_2 = QPointF(2.00,2.00)
        # self._1_point_3 = QPointF(4.00,3.00)
        # self._1_point_4 = QPointF(1.00,3.00)
        # self._1_point_5 = QPointF(5.00,3.00)
        # self._1_point_list = [self._1_point_0,self._1_point_1,self._1_point_4,self._1_point_2,self._1_point_3,self._1_point_5] #定义折线点清单
        # self.series_1.append(self._1_point_list) #折线添加坐标点清单
        self.series_data_cnt = 500
        # self.meas_data = deque([0] * self.series_data_cnt, maxlen=self.series_data_cnt)
        self.meas_data = []
        self.series_1.append([QPointF(x, y) for x, y in enumerate(self.meas_data)])
        self.series_1.setName("折线一")#折线命名


        self.x_Aix = QValueAxis()#定义x轴，实例化
        self.x_Aix.setRange(0.00, self.series_data_cnt) #设置量程
        # self.x_Aix.setLabelsVisible(False)
        # self.x_Aix.setFormatCondition("align", 60)
        # self.x_Aix.setLabelFormat("{value|hh:nn}")
        # self.x_Aix.setFormatCondition("else", 60)
        self.x_Aix.setLabelFormat("{value|hh:nn:ss}")
        self.x_Aix.setLabelFormat("%0.2f") #设置坐标轴坐标显示方式，精确到小数点后两位
        self.x_Aix.setTickCount(6)#设置x轴有几个量程
        self.x_Aix.setMinorTickCount(0)#设置每个单元格有几个小的分级

        self.y_Aix = QValueAxis()#定义y轴
        # self.y_Aix.setRange(0.00,6.00)
        self.y_Aix.setLabelFormat("%0.7f")
        self.y_Aix.setTickCount(7)
        self.y_Aix.setMinorTickCount(0)

        self.charView = InstChart(self)  #定义charView，父窗体类型为 Window
        self.charView.setGeometry(0,0,self.width(),self.height())  #设置charView位置、大小
        self.charView.meas_data = self.meas_data
        # self.charView.mouseMoveEvent.connect(self.onMouseMovePlotArea)

        self.chart = self.charView.chart()
        self.chart.addSeries(self.series_1)
        self.chart.setAxisX(self.x_Aix, self.series_1) #设置x轴属性
        self.chart.setAxisY(self.y_Aix, self.series_1) #设置y轴属性
        self.chart.setAcceptHoverEvents(True)
        self.chart.legend().hide()
        # self.charView.hovered.connect(self.charView.onHovered)

        # self.charView.chart().addSeries(self.series_1)  #添加折线
        # self.charView.chart().setAxisX(self.x_Aix) #设置x轴属性
        # self.charView.chart().setAxisY(self.y_Aix) #设置y轴属性
        # self.charView.legend().hide()
#               self.charView.chart().createDefaultAxes() #使用默认坐标系
        # self.charView.chart().setTitleBrush(QBrush(Qt.cyan))  #设置标题笔刷
        # self.charView.chart().setTitle("双折线") #设置标题             
        # self.charView.show()#显示charView

        # Load Control        
        self.lcd = QLCDNumber(12, self)
        spRight = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        spRight.setHorizontalStretch(2)
        self.lcd.setSizePolicy(spRight)


        self.btn_load = QPushButton('RUN', self)
        self.btn_load.clicked.connect(self.on_btn_load_clicked)
        self.btn_load.setFixedSize(self.btn_load.sizeHint().width(), opt_group.sizeHint().height())

        main_layout = QHBoxLayout()
        # mode_size = mode_group.sizeHint()
        # mode_size.setWidth(80)
        # mode_group.resize(mode_size)
        main_layout.addWidget(opt_group)
        main_layout.addWidget(self.lcd)
        main_layout.addWidget(self.btn_load)

        # Statistics Zone
        stat_selector = QVBoxLayout()
        stat_group = QGroupBox("Statistics", self)
        stat_group.setLayout(stat_selector)
        if True:
            st_layout = QHBoxLayout()
            st_layout.addWidget(QLabel("Pk to Pk:", self))
            self.state_pk = QLabel("0.00000000", self)
            st_layout.addWidget(self.state_pk)
            stat_selector.addLayout(st_layout)

            st_layout = QHBoxLayout()
            st_layout.addWidget(QLabel("Spans:", self))
            self.state_span = QLabel("0 rdgs", self)
            st_layout.addWidget(self.state_span)
            stat_selector.addLayout(st_layout)

            st_layout = QHBoxLayout()
            st_layout.addWidget(QLabel("Average:", self))
            self.state_average = QLabel("0.00000000", self)
            st_layout.addWidget(self.state_average)
            stat_selector.addLayout(st_layout)

            st_layout = QHBoxLayout()
            st_layout.addWidget(QLabel("Std Dev:", self))
            self.state_sdev = QLabel("0.00000000", self)
            st_layout.addWidget(self.state_sdev)
            stat_selector.addLayout(st_layout)

            st_layout = QHBoxLayout()
            st_layout.addWidget(QLabel("Maximum:", self))
            self.state_max = QLabel("0.00000000", self)
            st_layout.addWidget(self.state_max)
            stat_selector.addLayout(st_layout)

            st_layout = QHBoxLayout()
            st_layout.addWidget(QLabel("Minimum:", self))
            self.state_min = QLabel("0.00000000", self)
            st_layout.addWidget(self.state_min)
            stat_selector.addLayout(st_layout)

            self.btn_clear = QPushButton('Clear', self)
            self.btn_clear.clicked.connect(self.on_btn_clear_clicked)
            stat_selector.addWidget(self.btn_clear)


        vbox = QVBoxLayout()
        vbox.addLayout(box_selector)
        vbox.addWidget(self.dev_id)
        vbox.addLayout(main_layout)

        stat_layout = QHBoxLayout()
        stat_layout.addWidget(stat_group)
        stat_layout.addWidget(self.charView)
        vbox.addLayout(stat_layout)
        # vbox.addWidget(stat_group)
        # vbox.addWidget(self.charView)

        self.setLayout(vbox)
         
        self.resize(750,650)

        timer = QTimer(self)
        timer.setSingleShot(False)
        timer.timeout.connect(self.get_meas_value)
        timer.start(50)

    @pyqtSlot()
    def get_meas_value(self):
        if self.dev is not None and not self.initalizing and self.meas is not None:
            try:
                self.failed_read = 0

                self.lcd.display("%.08f" % (self.meas))
                if self.charView.acceptUpdate:
                    self.charView.setUpdatesEnabled(False)
                    self.series_1.replace([QPointF(x, y) for x, y in enumerate(self.meas_data)])
                    self.x_Aix.setRange(0,len(self.meas_data))
                    self.y_Aix.setRange(min(self.meas_data),max(self.meas_data))
                    self.charView.update()
                    self.charView.setUpdatesEnabled(True)
                    self.meas_count+=1

                self.state_pk.setText("%.08f" % (max(self.meas_data) - min(self.meas_data)))
                self.state_span.setText("%d rdgs" % (len(self.meas_data)))
                self.state_average.setText("%.08f" % (np.average(self.meas_data)))
                self.state_sdev.setText("%.08f" % (np.std(self.meas_data)))
                self.state_max.setText("%.08f" % (np.max(self.meas_data)))
                self.state_min.setText("%.08f" % (np.min(self.meas_data)))
                self.meas = None
            except Exception as e:
                print("Display data failed: %s" % (str(e)))
                self.failed_read+=1
                if self.failed_read >= 10:
                    self.on_open_click()

    @pyqtSlot()
    def on_open_click(self):
        if self.dev is None:
            self.initalizing = True
            # self.comm_th.dev_port = "GPIB::22::INSTR"
            self.comm_th.dev_port = self.dev_selector.currentText()

            while self.comm_th.dev is None:
                print("Waiting...")
                time.sleep(0.1)
            time.sleep(1)

            self.dev = self.comm_th.dev
            self.btn_connect.setText("Close")
            self.dev.write("END ALWAYS")
            time.sleep(0.1)
            self.dev.write("ID?")
            self.model = self.dev.read().strip()
            self.dev_id.setText(self.model)

            self.dev.write("NDIG?")
            self.state["NDIG"] = str(round(float(self.dev.read().strip())))
            self.opt_ndig.setCurrentText(self.state["NDIG"])

            self.dev.write("NPLC?")
            self.state["NPLC"] = "%g" % (round(float(self.dev.read().strip()),2))
            self.opt_nplc.setCurrentText(self.state["NPLC"])

            self.dev.write("NRDGS?")
            self.state["NRDGS"] = str(self.dev.read().strip())
            self.opt_nrdgs.setCurrentText(self.state["NRDGS"])

            self.dev.write("TRIG?")
            """
            1   AUTO
            2   EXT    Triggers on low-going TTL signal on the Ext Trig connector
            3   SGL    Triggers once (upon receipt of TRIG SGL) then reverts to TRIG HOLD)
            4   HOLD
            5   SYN    Triggers when the multimeter's output buffer is empty, memory is off or empty, and the controller requests data
            7   LEVEL  Triggers when the input signal reaches the voltage specified by the LEVEL command on the slope specified by the SLOPE command.
            8   LINE   Triggers on a zero crossing of the AC line voltage
            """
            self.state["TRIG"] = str(self.dev.read().strip())

            self.dev.write("FUNC?")
            self.state["FUNC"] = str(self.dev.read().strip())
            self.opt_fn.setCurrentIndex(int(self.state["FUNC"].split(",")[0]) - 1)

            self.dev.write("MATH?")
            self.state["MATH"] = str(self.dev.read().strip())
            math_index = int(self.state["MATH"].split(",")[0])
            if math_index >= 2:
                math_index -= 1
            self.opt_math.setCurrentIndex(math_index)

            self.update_load_button()
            print(self.state)

            self.initalizing = False
        else:
            self.dev.close()
            self.btn_connect.setText("Open")
            self.initalizing = True
            self.comm_th.dev.close()
            self.comm_th.dev_port = None
            self.comm_th.dev = None
            self.dev = None

    def update_load_button(self):
        if self.state['TRIG'] == "1":
            self.btn_load.setStyleSheet("background-color: #b1e46e; color: black;")
        else:
            self.btn_load.setStyleSheet("background-color: #b92919;")

    @pyqtSlot()
    def on_btn_load_clicked(self):
        if self.initalizing:
            return
        if self.state['TRIG'] == "4":
            self.comm_th.cmd_queue.append("TRIG AUTO")
            self.state['TRIG'] = "1"
        else:
            self.comm_th.cmd_queue.append("TRIG HOLD")
            self.state['TRIG'] = "4"

        self.update_load_button()

    @pyqtSlot()
    def on_btn_clear_clicked(self):
        self.meas_data.clear()

    @pyqtSlot()
    def on_opt_changed(self, opt, obj):        
        if not self.initalizing:
            if opt == "NDIG" or opt == "NPLC":
                self.dev.write("%s %s" % (opt, obj.currentText()))
                self.state[opt] = obj.currentText()
            elif opt == "NRDGS":
                self.dev.write("%s %s, AUTO" % (opt, obj.currentText()))
                self.state[opt] = "%s, AUTO" % (obj.currentText())
            elif opt == "FUNC":
                self.dev.write("%s %s, AUTO" % (opt, obj.currentText()))
                self.state[opt] = "%d, 0" % (obj.currentIndex() + 1)
            elif opt == "MATH":
                self.dev.write("%s %s" % (opt, obj.currentText()))
                self.state[opt] = "%d, 0" % (obj.currentIndex() + 1)

            print("Set %s => %s" % (opt, obj.currentText()))

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Enter and obj in []:
            rc = super(SigSlot, self).eventFilter(obj, event)
            obj.setFocus()
            obj.selectAll()
            return rc
        #     print(obj)
        return super(SigSlot, self).eventFilter(obj, event)

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_F5:
            self.on_btn_load_clicked()

app = QApplication(sys.argv)
qb = SigSlot()
qb.show()
sys.exit(app.exec_())