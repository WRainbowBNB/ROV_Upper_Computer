import configparser
import os
from PyQt6.QtCore import Qt, QObject, pyqtSignal, QEvent, QTimer
from PyQt6.QtGui import QKeyEvent
import pygame

#为了键盘映射
class KeyMapper:
    #是在根目录下找这个文件，所以理论上能找到
    def __init__(self, config_path = 'config/config.ini'):
        self.config_path = config_path
        self.key_find_list = {}
        #字符串 -> Qt.Key
        self.str_to_key = {
            'W':Qt.Key.Key_W, 'S':Qt.Key.Key_S,
            'A':Qt.Key.Key_A, 'D':Qt.Key.Key_D,
            'LEFT':Qt.Key.Key_Left, 'RIGHT':Qt.Key.Key_Right,
            'UP':Qt.Key.Key_Up, 'DOWN':Qt.Key.Key_Down,
            'X':Qt.Key.Key_X, 'Q':Qt.Key.Key_Q,
            'E':Qt.Key.Key_E, 'O':Qt.Key.Key_O,
            'P':Qt.Key.Key_P

        }

        self.load_config()
    
    def load_config(self):
        if not os.path.exists(self.config_path):
            print(f'没找到配置文件0v0{self.config_path}')
            return
        #这个是专门读取配置文件的函数
        config = configparser.ConfigParser()
        config.read(self.config_path, encoding = 'utf-8')
        if 'keyboard' in config:
            kb = config['keyboard']
            self.key_find_list['forward'] = self.str_to_key.get(kb.get('key_forward', 'W').upper())
            self.key_find_list['backward'] = self.str_to_key.get(kb.get('key_backward', 'S').upper())
            self.key_find_list['yaw_left'] = self.str_to_key.get(kb.get('key_yaw_left', 'A').upper())
            self.key_find_list['yaw_right'] = self.str_to_key.get(kb.get('key_yaw_right', 'D').upper())
            self.key_find_list['left'] = self.str_to_key.get(kb.get('key_left', 'LEFT').upper())
            self.key_find_list['right'] = self.str_to_key.get(kb.get('key_right', 'RIGHT').upper())
            self.key_find_list['up'] = self.str_to_key.get(kb.get('key_up', 'UP').upper())
            self.key_find_list['down'] = self.str_to_key.get(kb.get('key_down', 'DOWN').upper())
            self.key_find_list['mode_toggle'] = self.str_to_key.get(kb.get('key_mode_toggle', 'X').upper())
            self.key_find_list['claw_open'] = self.str_to_key.get(kb.get('key_claw_open', 'Q').upper())
            self.key_find_list['claw_close'] = self.str_to_key.get(kb.get('key_claw_close', 'E').upper())
            self.key_find_list['over_current'] = self.str_to_key.get(kb.get('key_over_current', 'O').upper())
            self.key_find_list['temperature'] = self.str_to_key.get(kb.get('key_temperature', 'P').upper())

    def Handle_kb(self, qt_key):
        for action, bound_key in self.key_find_list.items():
            if qt_key == bound_key:
                return action
        return None

class KeyboardController(QObject):
    #定义信号
    action_pressed = pyqtSignal(str)
    action_released = pyqtSignal(str)
    
    def __init__(self, parent = None):
        super().__init__(parent)
        #为了用Handle_kb
        self.mapper = KeyMapper('config/config.ini')

    #事件过滤
    #obj是监测对象吧算是
    def eventFilter(self, obj, event:QKeyEvent):
        #如果是按键按下就发对应动作信号
        if event.type() == QEvent.Type.KeyPress:
            if not event.isAutoRepeat():
                action = self.mapper.Handle_kb(event.key())
                if action:
                    self.action_pressed.emit(action) #发信号
                    return True
                
        #如果按键释放同样发对应动作信号
        elif event.type() == QEvent.Type.KeyRelease:
            if not event.isAutoRepeat():
                action = self.mapper.Handle_kb(event.key())
                if action:
                    self.action_released.emit(action)
                    return True
        #其他事件不管        
        return super().eventFilter(obj, event)


class ROV_Controller(QObject):
    #给ui传信号，一参是指令名，二参是动作
    ui_speed_signal = pyqtSignal(str, str)
    serial_send_signal = pyqtSignal(str)
    ui_claw_signal = pyqtSignal(str)
    ui_joystick_state_signal = pyqtSignal(str)

    #TODO：串口别忘加了
    def __init__(self, serial_instance, parent = None):
        super().__init__(parent)
        self.ser = serial_instance
        #过流标志
        self.cur_over_flag = False
        #速度状态，默认慢速
        self.speed_mode = 'SLOW'
        #最大推力默认0.3
        self.F = 0.3
        #长按标志（给X用的）
        self.X_long_pressed = False 
        self.out_time = 800
        self.check_pressed_timer = QTimer()
        self.check_pressed_timer.timeout.connect(self.handle_X_pressed_timeout)
        self.modes = []
        self.cur_mode_idx = 0
        self.joy_map = {'y': 1, 'x': 2, 'z': 3, 'yaw': 0}
        self.joy_dz = {'y': 0.05, 'x': 0.05, 'z': 0.05, 'yaw': 0.05} 
        self.joy_max = {'y': 1.0, 'x': 1.0, 'z': 1.0, 'yaw': 1.0}
        self.btn_map = {'x': 3, 'lb': 6, 'rb': 7}
        self.load_config()
        self.cur_couple = self.modes[self.cur_mode_idx]
        self.cur_current = 0.0
        self.cur_temprature = 25.0
        self.claw_state = 'CLAW OPEN'
        #手柄相关
        pygame.init()
        pygame.joystick.init()
        self.has_joy = False
        self.joy = None
        self.control_timer = QTimer(self)
        self.control_timer.timeout.connect(self.main_control_loop)
        self.control_timer.start(50)

    def load_config(self):
        config = configparser.ConfigParser()
        config.read('config/config.ini', encoding='utf-8')
        
        #读速度
        if 'speed_modes' in config:
            speed_table = config['speed_modes']
            i = 0
            while f'mode{i}_name' in speed_table:
                self.modes.append({
                    'name': speed_table.get(f'mode{i}_name'),
                    'rate': speed_table.getfloat(f'mode{i}_rate'),
                    'color': speed_table.get(f'mode{i}_color')
                })
                i += 1
        #读电流
        if 'overcurrent' in config:
            oc = config['overcurrent']
            self.threshold = oc.getfloat('threshold', fallback = 10.0)
            self.refresh_interval = oc.getint('refresh_interval', fallback = 500)
  
        #读手柄按键
        if 'button' in config:
            # getint 会自动把文本转成整数
            self.btn_map['x'] = config['button'].getint('X', fallback=3)
            self.btn_map['lb'] = config['button'].getint('LB', fallback=6)
            self.btn_map['rb'] = config['button'].getint('RB', fallback=7)
            
        #读手柄摇杆轴
        if 'axis' in config:
            self.joy_map['y'] = config['axis'].getint('y', fallback=1)
            self.joy_map['yaw'] = config['axis'].getint('yaw', fallback=0)
            self.joy_map['x'] = config['axis'].getint('x', fallback=2)
            self.joy_map['z'] = config['axis'].getint('z', fallback=3)
            
        #读死区
        for axis_name in ['x', 'y', 'z', 'yaw']:
            if axis_name in config:
                self.joy_dz[axis_name] = config[axis_name].getfloat('deadzone', fallback=0.05)
                raw_max = config[axis_name].getfloat('max', fallback=1.0)
                self.joy_max[axis_name] = abs(raw_max) if abs(raw_max) > 0 else 1.0

    def main_control_loop(self):
        pygame.event.pump()
        for event in pygame.event.get():
            if event.type == pygame.JOYBUTTONDOWN:
                #em，不同手柄按键可能对应的序号不同，记得测试并调整
                #这里是我试是X是3， LB是6, RB是7, 恩或许可以写在config里面
                if event.button == 3: 
                    self.handle_mode_toggle_pressed()
                elif event.button == 6: 
                    self.handle_claw_open()        
                elif event.button == 7: 
                    self.handle_claw_close()       
            
            elif event.type == pygame.JOYBUTTONUP:
                if event.button == 3:
                    self.handle_mode_toggle_released()

        #检测是否有手柄
        if pygame.joystick.get_count() > 0:
            #有手柄
            if not self.has_joy:
                #如果是刚插上的，进行初始化绑定
                self.joy = pygame.joystick.Joystick(0)
                self.joy.init()
                self.has_joy = True
                self.ui_joystick_state_signal.emit("手柄已连接")
        
            #Y：1 Yaw：0 Z：3 X：2
            joy_y = -self.joy.get_axis(1) #上推负，下推正
            joy_yaw = self.joy.get_axis(0) # 左推负，右推正
            joy_x = -self.joy.get_axis(2)
            joy_z = self.joy.get_axis(3) 

            #死区
            if abs(joy_y) < self.joy_dz['y']:
                joy_y = 0.0
            if abs(joy_x) < self.joy_dz['x']:
                joy_x = 0.0
            if abs(joy_z) < self.joy_dz['z']:
                joy_z = 0.0
            if abs(joy_yaw) < self.joy_dz['yaw']:
                joy_yaw = 0.0

            #结合当前界面的推力限幅系数
            rate = self.F
            self.ser.Y_F = joy_y /  self.joy_max['y'] * rate
            self.ser.X_F = joy_x /  self.joy_max['x'] * rate
            self.ser.Z_F = joy_z /  self.joy_max['z'] * rate
            self.ser.Yaw_F = joy_yaw /  self.joy_max['yaw'] * rate
            
            #发命令
            self.ser.send_command()
            
        else:
            #没有手柄，走键盘映射
            if self.has_joy:
                self.has_joy = False
                self.joy = None
                self.ui_joystick_state_signal.emit("手柄未连接")
            
            #定时下发命令
            self.ser.send_command()
    
    #以下是按键映射对应代码,ber，堆这一堆正常吗
    def handle_forward(self):
        self.ser.Y_F = self.F
    def handle_backward(self):
        self.ser.Y_F = -self.F
    def handle_yaw_left(self):
        self.ser.Yaw_F = self.F
    def handle_yaw_right(self):
        self.ser.Yaw_F = -self.F
    def handle_right(self):
        self.ser.X_F = self.F
    def handle_left(self):
        self.ser.X_F = -self.F
    def handle_up(self):
        self.ser.Z_F = self.F
    def handle_down(self):
        self.ser.Z_F = -self.F
    def handle_forward_released(self): 
        self.ser.Y_F = 0.0
    def handle_backward_released(self): 
        self.ser.Y_F = 0.0
    def handle_left_released(self): 
        self.ser.X_F = 0.0
    def handle_right_released(self): 
        self.ser.X_F = 0.0
    def handle_up_released(self): 
        self.ser.Z_F = 0.0
    def handle_down_released(self): 
        self.ser.Z_F = 0.0
    def handle_yaw_left_released(self): 
        self.ser.Yaw_F = 0.0
    def handle_yaw_right_released(self): 
        self.ser.Yaw_F = 0.0

    #按键按下开始倒计时
    def handle_mode_toggle_pressed(self):
        #标志位先清零
        self.X_long_pressed = False
        #800ms倒计时
        self.check_pressed_timer.start(self.out_time)   

    #按下超时说明长按
    def handle_X_pressed_timeout(self):
        self.X_long_pressed = True
        #长按，慢 -> 快 -> 中
        self.cur_mode_idx = (self.cur_mode_idx - 1) % len(self.modes)
        self._signal_emit()

    #按下松开且定时器没有停止工作说明是短按
    def handle_mode_toggle_released(self):
        if self.check_pressed_timer.isActive():
            self.check_pressed_timer.stop()
            #长按，慢 -> 快 -> 中
            if not self.X_long_pressed:
                self.cur_mode_idx = (self.cur_mode_idx + 1) % len(self.modes)
                self._signal_emit()

    #处理并发送信号的函数
    def _signal_emit(self):
        self.cur_couple = self.modes[self.cur_mode_idx]
        self.speed_mode = self.cur_couple['name']
        self.F = self.cur_couple['rate']
        self.ui_speed_signal.emit(self.speed_mode, self.cur_couple['color'])
        self.serial_send_signal.emit(self.speed_mode)

    def handle_claw_open(self):
        #TODO：改串口数据，额通信协议里面没看到机械爪o-o
        self.ser.arm_angle = 255 #这是机械臂
        self.claw_state = 'CLAW OPEN'
        self.ui_claw_signal.emit(self.claw_state)

    def handle_claw_close(self):
        #TODO：改串口数据，额通信协议里面没看到机械爪o-o
        self.ser.arm_angle = 0 #这是机械臂
        self.claw_state = 'CLAW CLOSE'
        self.ui_claw_signal.emit(self.claw_state)
        


    