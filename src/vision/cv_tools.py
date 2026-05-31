import cv2
import numpy as np
import pandas as pd
from PyQt6.QtCore import QThread, pyqtSignal

class CameraThread(QThread):
    #定义信号：发送捕获的帧（OpenCV格式）
    frame_captured = pyqtSignal(np.ndarray)
    #定义信号：发送错误信息
    error_occurred = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.running_flag = False  #线程运行标志
        self.camera = None
    
    def run(self):
        self.running_flag = True
        #打开摄像头
        self.camera = cv2.VideoCapture(2)

        if not self.camera.isOpened():
            self.error_occurred.emit('无法打开摄像头捏ovo')
            self.running_flag = 0
            return
        
        self.camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
        #降低延迟OHHHHHHHHHHHH
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        #循环捕获帧，直到手动停止
        while self.running_flag:
            #记记记，第一个是标志，第二个是一帧帧图片
            success, frame = self.camera.read()
            if not success:
                self.error_occurred.emit('无法读取摄像头帧捏ovo')
                break
            #发送捕获的帧到主线程
            self.frame_captured.emit(frame)
            #控制捕获速度，根据实际情况再改吧, 记记记msleep是ms级，sleep是s级
            #self.msleep(100)
        self._release_camera()

    #释放资源
    def _release_camera(self):
        if self.camera is not None and self.camera.isOpened():
            self.camera.release()
            self.camera = None
        else:
            self.error_occurred.emit('摄像头未打开或已释放')
    
    def stop(self):
        if self.running_flag:
            self.running_flag = 0 #通知线程退出循环
            self.wait() #等待线程彻底结束，确保退出之后再释放
            
        #最终释放摄像头
        self._release_camera()



