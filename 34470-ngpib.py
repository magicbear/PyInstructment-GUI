from socket import *

import visa
import struct
import io
import numpy as np
import traceback
import random

tcpS = socket(AF_INET, SOCK_STREAM) # 创建socket对象
tcpS.setsockopt(SOL_SOCKET,SO_REUSEADDR,1) #加入socket配置，重用ip和端口
tcpS.bind(("0.0.0.0",5025)) # 绑定ip端口号
tcpS.listen(100)  # 设置最大链接数
BUFSIZ = 1024
buf = np.zeros((65536,),np.uint8)
bufsize = 0

rm = visa.ResourceManager("@py")
dev = rm.open_resource("TCPIP0::192.168.9.190::inst0::INSTR")
dev.write("*IDN?")
print(dev.read())

dev.write(":TRIGger:COUNt INFinity")

dev.write(":INITiate:IMMediate")

get_temp = 1
temp = b"+0.00E0\n"
while True:
    print("服务器启动，监听客户端链接")
    conn, addr = tcpS.accept() 
    print("链接的客户端", addr)
    while True:
        try:
            data = conn.recv(BUFSIZ) # 读取已链接客户的发送的消息
        except Exception:
            print("断开的客户端", addr)
            break

        buf[bufsize:bufsize+len(data)] = np.frombuffer(data, np.uint8)[:]
        bufsize += len(data)
        if bufsize < 3:
            print("Buffer Not enough  left data: %d" % (bufsize))
            continue

        if bufsize >= buf[2] + 3:
            payload = buf[:buf[2]+3]

            if payload[0] == 0x08:
                if payload[3] == 0xA0:
                    # Device Param Query
                    print("Care CMD: Device Param Query   Len: %d " % (payload[2]))
                    conn.send(struct.pack("@BBBBBB", 0x09, payload[1], 2, payload[3], payload[4], 0x00))
                elif payload[3] == 0xB0:
                    # Device Param Settings
                    print("Care CMD: Device Param Settings   Len: %d " % (payload[2]))
                    conn.send(struct.pack("@BBBBBB", 0x09, payload[1], 2, payload[3], payload[4], 0x01))
                elif payload[3] == 0xAA:
                    # GPIB Command
                    str_cmd = payload[5:].tobytes().decode("UTF-8")
                    print("GPIB Addr: \033[31m%d\033[0m  SubCMD: %d Len: %d   %s" % (payload[1], payload[4], payload[2], str_cmd))
                    if payload[1] == 23 and len(payload[5:]) > 0:
                        try:
                            if payload[3] == 0xAA:
                                # conn.send(struct.pack("@BBBBB", 0x09, payload[1], 2 + len(temp), 0xAA, payload[4]) + temp)
                                # temp = ("÷+2.610%dE+01\n" % (int(100))).encode("utf-8")
                                # get_temp = 0
                                # else:
                                dev.write(":DATA:LAST?")
                                data = dev.read()
                                print("  Read DATA: ", data)
                                bdata = data.encode("utf-8")
                                conn.send(struct.pack("@BBBBB", 0x09, payload[1], 2 + len(temp), 0xAE, payload[4]) + temp)
                                conn.send(struct.pack("@BBBBB", 0x09, payload[1], len(bdata) + 2, 0xAA, payload[4]) + bdata)
                        except Exception as e:
                            print("FATAL in read file thread PIP process: %s" % (str(e) + "\n" + ''.join(traceback.format_tb(e.__traceback__))))
                            conn.send(struct.pack("@BBBBB", 0x09, payload[1], 2, 0xAA, 0x00))

                elif payload[3] == 0xAB:
                    print("GPIB Addr: %d Data Back: %s Len: %d " % (payload[1], "Y" if payload[3] == 0xAA else "N", payload[2]))
                    conn.send(struct.pack("@BBBBBB", 0x09, payload[1], 2, 0xAB, 0x00, 0x01))
                elif payload[3] == 0xAE:
                    print("Care CMD: \033[32mGet Temperature\033[0m   Len: %d " % (payload[2]))
                    get_temp = 1
                    dev.write(":SYSTem:TEMPerature?")
                    temp = dev.read().encode("utf-8")
                    conn.send(struct.pack("@BBBBB", 0x09, payload[1], 2 + len(temp), 0xAA, payload[4]) + temp)
                    # temp = "+2.61E+01\n".encode("utf-8")
                    # conn.send(struct.pack("@BBBBB", 0x09, payload[1], 2 + len(temp), 0xAA, payload[4]) + temp)
                else:
                    print("Care CMD: %d   Len: %d " % (payload[3], payload[2]))
                    conn.send(struct.pack("@BBBBBB", 0x09, payload[1], 2, payload[3], payload[4], 0x01))
            else:
                print("Invalid Care CMD: %d  Len: %d " % (payload[0], payload[2]))

            payload_size = buf[2] + 3
            buf[:bufsize-payload_size] = buf[payload_size:bufsize]
            bufsize -= payload_size
        else:
            print("Buffer Not enough  current: %d" % (bufsize))
    conn.close() #关闭客户端链接
tcpS.closel()
