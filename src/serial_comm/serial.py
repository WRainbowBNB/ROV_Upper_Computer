import serial
import sys
from PyQt6.QtCore import QTimer, QThread, pyqtSignal
import struct


class SerialControl(QThread):
    #回传信号
    data_deliver_current_signal = pyqtSignal(float)
    data_deliver_temperature_signal = pyqtSignal(float)
    def __init__(self):
        super().__init__()
        self.is_running = True
        self.ser = None
        #为了发送请求搞的定时器
        self.request_timer = QTimer()
        self.request_timer.start(200)
        self.request_timer.timeout.connect(self.send_request)
        self.X_F = 0.0
        self.Y_F = 0.0
        self.Z_F = 0.0
        self.Yaw_F = 0.0
        self.arm_angle = 0
        self.rx_buf = bytearray()
		#开串口
        try:
            #'/dev/ttyUSB0'
            self.ser = serial.Serial('/dev/pts/5' , 115200, timeout = 0.1)
            print("串口已连接")
        except Exception as e:
            print(f"串口连接错误{e}")
            self.ser = None
    
    #发送请求帧
    def send_request(self):
        bytes = struct.pack('<5B',0xFA, 0xAF, 0x52, 0xFB, 0xBF)
        self.ser.write(bytes)

    #写异或校验的
    def XOR_check(self, bytes):
        checksum = 0
        for param in bytes:
            checksum ^= param
        return checksum
    
    def send_command(self):
        tx_buf = struct.pack('<3B4fB', 0xFA, 0xAF, 0x49, self.Y_F, self.X_F, self.Z_F, self.Yaw_F, self.arm_angle)
        checksum = self.XOR_check(tx_buf[2:])
        tx_buf += struct.pack('<3B', checksum, 0xFB, 0xBF)
        self.ser.write(tx_buf)

    #让接收作为子线程，避免gui卡死
    def run(self):
        if self.ser is None:
            return 
        while self.is_running:
            if self.ser.in_waiting > 0:
                #读数据
                data = self.ser.read(self.ser.in_waiting)
                self.rx_buf.extend(data)
                #处理数据
                while len(self.rx_buf) >= 15:
                    if self.rx_buf[0] == 0xFA and self.rx_buf[1] == 0xAF:
                        frame = self.rx_buf[2:12]
                        #计算校验位
                        check_sum = self.XOR_check(frame) & 0xFF
                        if check_sum == self.rx_buf[12]:
                            if self.rx_buf[13] == 0xFB and self.rx_buf[14] == 0xBF:
                                #校验通过，提取温度和电流
                                #注意，还有个进水，这个根据后续需要再加
                                temperature = struct.unpack('<f', self.rx_buf[3:7])[0]
                                current = struct.unpack('<f', self.rx_buf[8:12])[0]
                                #传递数据
                                self.data_deliver_current_signal.emit(current)
                                self.data_deliver_temperature_signal.emit(temperature)
                                #删掉这一包
                                del self.rx_buf[:15]
                        else:
                            #避免假帧头
                            self.rx_buf.pop(0)
                    else:
                        #窗口后移一位
                        self.rx_buf.pop(0)	

    def stop_thread(self):
        self.is_running = False
        self.quit()
        self.wait()
        if self.ser and self.ser.is_open:
            self.ser.close()
            print("串口关了")