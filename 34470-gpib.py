from socket import *

import visa
import struct
import io
import numpy as np
import traceback
import time
# import matplotlib.pyplot as stimulusResponsePlot
import datetime


rm = visa.ResourceManager("@py")
dev = rm.open_resource("TCPIP0::192.168.9.194::inst0::INSTR")
dev.write("*IDN?")
print(dev.read())

dev.write(":TRIGger:COUNt INFinity")

# dev.write(":INITiate:IMMediate")

# stimulusResponsePlot.title ("Keysight FieldFox Spectrum Trace Data via Python - PyVisa - SCPI")
# stimulusResponsePlot.xlabel("Frequency")
# stimulusResponsePlot.ylabel("Amplitude (dBm)")
timeScale = np.zeros((65536,), np.int32)
data = np.zeros((65536,), np.float32)
dataOffset = 0
# print(timeScale.shape, data.shape)
# stimulusResponsePlot.show(False)

# dev.write(":TRIG:SOUR BUS")

while True:
    dev.write(":SYSTem:TEMPerature?")
    temp = dev.read()[:-1]
    # time.sleep(0.5)
    temp = 30.0
    # dev.write("*TRG")
    # dev.write(":DATA:LAST?")
    dev.write(":R? 1")
    dmeas = dev.read()
    time.sleep(0.5)

    timeScale[dataOffset % 65536] = time.time()
    print("%s,%s,%s" % (datetime.datetime.now(), temp, dmeas[:dmeas.find(" ")]))
    # data[dataOffset % 65536] = dmeas[:dmeas.find(" ")]
    # dataOffset+=1

    # print(data[:dataOffset])
    # stimulusResponsePlot.plot(timeScale[:dataOffset],data[:dataOffset])
    # stimulusResponsePlot.pause(0.5)

