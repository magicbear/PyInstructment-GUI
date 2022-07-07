import socket

class SocketInterfaces():
    def __init__(self, host_str):
        host = host_str.split(":")
        self.buffer = bytearray(1024)
        self.dev = socket.socket()
        self.dev.connect((host[0], int(host[1])))

    def write(self, str):
        # print(">>",str)
        if type(str) is bytes:
            return self.dev.send(str + b"\n")
        else:
            return self.dev.send((str.strip() + "\n").encode("utf-8"))

    def read(self):
        r = self.dev.recv_into(self.buffer)
        # print("<< "+self.buffer[0:r].decode("utf-8").strip())
        return self.buffer[0:r].decode("utf-8")

    def close(self):
       self.dev.close()
       self.dev = None

# :SYSTem:ERRor?
# s = SocketInterfaces("192.168.9.159:2268")
# s.write("*IDN?")
# print(s.read())