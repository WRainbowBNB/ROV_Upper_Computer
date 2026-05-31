from PyQt6.QtCore import Qt, QObject, pyqtSignal, QEvent, QTimer
from src.serial_comm.serial import SerialControl
import configparser

class SensorHandle(QObject):
    ui_current_signal = pyqtSignal(float, str)
    ui_temperature_signal = pyqtSignal(float)
    def __init__(self, serial_instance, parent = None):
        super().__init__(parent)
        self.cur_current = 0.0
        self.cur_temperature = 0.0
        self.serial = serial_instance
        self.threshold = 0.0
        #后面如果还有别的传感器再加
        self.serial.data_deliver_current_signal.connect(self.handle_over_current)
        self.serial.data_deliver_temperature_signal.connect(self.handle_temperature)
        self.load_config()

    def load_config(self):
        config = configparser.ConfigParser()
        config.read('config/config.ini', encoding = 'utf-8')
        if 'overcurrent' in config:
            oc = config['overcurrent']
            self.threshold = oc.getfloat('threshold', fallback = 10.0)
        
    def handle_over_current(self, ser_cur):
        self.cur_current = ser_cur
        if self.cur_current > self.threshold:
            self.cur_over_flag = True
            color = '#FF0000'
        else:
            self.cur_over_flag = False
            color = '#00B050'

        self.ui_current_signal.emit(self.cur_current, color)

    def handle_temperature(self, ser_temperature):
        self.cur_temperature = ser_temperature
        self.ui_temperature_signal.emit(self.cur_temperature)