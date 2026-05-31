import sys
from src.gui import rov_gui as ui
from PyQt6.QtWidgets import QApplication, QDialog
from PyQt6.QtCore import QTimer, pyqtSignal, pyqtSlot, Qt, QTime
from PyQt6.QtGui import QImage, QPixmap,  QCloseEvent
import cv2
import numpy as np
import os
from src.vision.cv_tools import CameraThread
from src.joystick.controller import KeyboardController, ROV_Controller
from src.serial_comm.serial import SerialControl
from src.sensor.sensor_handle import SensorHandle
import pygame

class MainWindow(QDialog, ui.Ui_Dialog):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.setupUi(self)
        self.video.setScaledContents(True)
        self.video.clear()
        self.camera_thread = CameraThread()
        self.serial_comm = SerialControl()
        self.sensor_handler = SensorHandle(self.serial_comm)
        #连接信号
        self.camera_thread.frame_captured.connect(self.show_video)
        self.camera_thread.start()
        #杆件限幅
        self.current_slider.setMinimum(0)
        self.current_slider.setMaximum(200)
        self.temperature_slider.setMinimum(0)
        self.temperature_slider.setMaximum(800)
        #实例化
        self.kb_controller = KeyboardController(self)
        self.rov_controller = ROV_Controller(self.serial_comm)
        #nb,python这么方便，直接用事件过滤器
        app = QApplication.instance()
        if app:
            app.installEventFilter(self.kb_controller)
        self.kb_controller.action_pressed.connect(self.on_action_pressed)
        self.kb_controller.action_released.connect(self.on_action_released)
        self.rov_controller.ui_speed_signal.connect(self.update_gui_speed)
        self.sensor_handler.ui_current_signal.connect(self.update_gui_current)
        self.sensor_handler.ui_temperature_signal.connect(self.update_gui_temperature)
        self.rov_controller.ui_claw_signal.connect(self.update_gui_claw_state)
        self.refresh_button.clicked.connect(self.refresh_over_time)
        self.rov_controller.ui_joystick_state_signal.connect(self.update_joystick_state)
        self.current_slider.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.temperature_slider.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        #过流时间定时器相关
        self.over_flag = False
        self.over_s = 0
        self.over_timer = QTimer(self)
        self.over_timer.timeout.connect(self.handle_over_current_time)
        self.serial_comm.start()
        self.rov_controller._signal_emit() 
        #你别说，让ai生成的这个样式还听好看
        self.speed_state.setStyleSheet("""
            color: #00FF88;  
            font-size: 26px; 
            font-weight: bold;
            font-family: 'Consolas', 'Monaco', monospace;
            background-color: #1A1A1A; 
            border: 1px solid #00FFFF;  
            border-radius: 4px;        
            padding: 4px 10px;         
        """)
        self.sensor_handler.ui_current_signal.emit(0.0, '#00B050')
        self.sensor_handler.ui_temperature_signal.emit(25.0)
        self.rov_controller.ui_claw_signal.emit('CLAW OPEN')
        self.current_slider.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.temperature_slider.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setStyleSheet("""
            QDialog {
                background-color: #121212;
                color: #E0E0E0;
                font-family: 'Consolas', 'Monaco', 'DejaVu Sans Mono', 'Ubuntu Mono', monospace;
            }
            QLabel {
                color: #00FFFF;
                font-size: 14px;
                font-weight: bold;
                font-family: 'Consolas', 'Monaco', monospace;
            }
        """)
        self.connect_state.setStyleSheet("""
            color: #FF6666;  
            font-size: 16px;
            font-weight: bold;
            font-family: 'Consolas', 'Monaco', monospace;
            background-color: #1A1A1A; 
            border: 1px solid #00FFFF;  
            border-radius: 4px;       
            padding: 4px 10px;         
        """)
        self.video.setStyleSheet("""
            QLabel {
                border: 2px solid #00FFFF;
                border-radius: 4px;
                background-color: #0A0A0A;
                
            }
        """)
       

    @pyqtSlot(np.ndarray)
    def show_video(self, frame):
        #OpenCV->RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        #转成Qt图片
        h, w, ch = rgb_frame.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)

        #显示
        self.video.setPixmap(QPixmap.fromImage(qt_image))
    
    #注意奥，要加类型，不然人以为你可能就传了个普通参数
    def closeEvent(self, event:QCloseEvent):
        self.camera_thread.stop()
        self.serial_comm.stop_thread()
        event.accept()

    #table
    def on_action_pressed(self, action_name):
        pressed_table = {
            'mode_toggle':  self.rov_controller.handle_mode_toggle_pressed,
            'forward':      self.rov_controller.handle_forward,
            'backward':     self.rov_controller.handle_backward,
            'yaw_left':     self.rov_controller.handle_yaw_left,
            'yaw_right':    self.rov_controller.handle_yaw_right,
            'right':        self.rov_controller.handle_right,
            'left':         self.rov_controller.handle_left,
            'up':           self.rov_controller.handle_up,
            'down':         self.rov_controller.handle_down,
            'claw_open':    self.rov_controller.handle_claw_open,
            'claw_close':   self.rov_controller.handle_claw_close,
        }

        #查表执行
        func = pressed_table.get(action_name)
        if func:
            func()

    def on_action_released(self, action_name):
        released_table = {
            'mode_toggle':  self.rov_controller.handle_mode_toggle_released,
            'forward':      self.rov_controller.handle_forward_released,
            'backward':     self.rov_controller.handle_backward_released,
            'yaw_left':     self.rov_controller.handle_yaw_left_released,
            'yaw_right':    self.rov_controller.handle_yaw_right_released,
            'right':        self.rov_controller.handle_right_released,
            'left':         self.rov_controller.handle_left_released,
            'up':           self.rov_controller.handle_up_released,
            'down':         self.rov_controller.handle_down_released,
        }

        func = released_table.get(action_name)
        if func:
            func()

    #速度模式
    def update_gui_speed(self, speed_mode, color):
        self.speed_state.setText(speed_mode)
        self.speed_state.setStyleSheet(f"""
            color: {color}; 
            font-size: 26px; 
            font-weight: bold;
            font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
            background-color: #1A1A1A; 
            border: 1px solid #00FFFF;  
            border-radius: 4px;       
            padding: 4px 10px;      
        """)

    #电流显示
    def update_gui_current(self, cur, color):
        self.current.setStyleSheet("""
            color: #00FFFF;
            font-size: 14px;
            font-weight: bold;
            font-family: 'Consolas', 'Monaco', monospace;
        """)
        self.current.setText(f"电流：{cur:.1f}A")
        self.current_slider.setValue(int(cur * 10))
        #改色儿
        self.current_slider.setStyleSheet(f"""
            QSlider::groove:vertical {{
                background: #2A2A2A;
                width: 8px;
                border-radius: 4px;
            }}
            QSlider::add-page:vertical {{
                background: {color};   
                border-radius: 4px;
            }}
            QSlider::handle:vertical {{
                background: {color};    
                border: 1px solid #FFFFFF;
                height: 12px;
                margin: 0 -4px;         
                border-radius: 4px;
            }}
        """)

        self.current_state.setStyleSheet("""
            color: #00FFFF;
            font-size: 14px;
            font-weight: bold;
            font-family: 'Consolas', 'Monaco', monospace;
        """)
        if cur > 10.0:
            self.current_state.setText("警告！已过流！")
            self.current_state.setStyleSheet(f"""
                color: {color}
            """)
            #获取已过时间
            if not self.over_flag :
                self.over_flag = True
                self.over_timer.start(1000)
        else:
            self.current_state.setText("未过流")
            self.current_state.setStyleSheet(f"""
                color: #00FFFF;
            """)
            if self.over_flag:
                self.over_flag = False
                self.over_timer.stop()

    def handle_over_current_time(self):
        self.over_s += 1
        over_min = self.over_s // 60
        over_sec = self.over_s % 60
        self.over_time.setText(f"过流时间:{over_min} min {over_sec} s")
        self.over_time.setStyleSheet("""
            color: #00FFFF;
            font-size: 14px;
            font-weight: bold;
            font-family: 'Consolas', 'Monaco', monospace;
        """)

    def refresh_over_time(self):
        self.over_s = 0
        self.over_time.setText("过流时间: 0 min 0 s")

    #温度显示
    def update_gui_temperature(self, cur_temprature):
        self.temperature.setStyleSheet("""
            color: #00FFFF;
            font-size: 14px;
            font-weight: bold;
            font-family: 'Consolas', 'Monaco', monospace;
        """)
        self.temperature.setText(f"温度：{cur_temprature:.1f}°C")
        self.temperature_slider.setValue(int(cur_temprature * 10))
        self.temperature_slider.setStyleSheet(f"""
            QSlider::groove:vertical {{
                background: #2A2A2A;   
                width: 8px;
                border-radius: 4px;
            }}
            QSlider::add-page:vertical {{
                background: #00FFFF;   
                border-radius: 4px;
            }}
            QSlider::handle:vertical {{
                background: #00FFFF;    
                border: 1px solid #FFFFFF;
                height: 12px;
                margin: 0 -4px;         
                border-radius: 4px;
            }}
        """)

    #机械爪状态
    def update_gui_claw_state(self, claw_state):
        self.claw_label.setText(claw_state.upper())
        self.claw_label.setStyleSheet("""
            color: #00FFFF;         
            font-size: 22px;        
            font-weight: bold;      
            font-family: 'Consolas', 'Monaco', 'DejaVu Sans Mono', 'Ubuntu Mono', monospace;
            background-color: #1A1A1A; 
            border: 1px solid #00FFFF;  
            border-radius: 4px;        
            padding: 4px 10px;         
        """)

    #手柄连接状态
    def update_joystick_state(self, joystick_state):
        self.connect_state.setText(joystick_state)
        self.connect_state.setStyleSheet("""
            color: #FF6666;  
            font-size: 16px;
            font-weight: bold;
            font-family: 'Consolas', 'Monaco', monospace;
            background-color: #1A1A1A; 
            border: 1px solid #00FFFF;  
            border-radius: 4px;       
            padding: 4px 10px;         
        """)


