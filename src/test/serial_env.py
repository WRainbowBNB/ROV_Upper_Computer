import serial
import struct
import time
import threading

# 🌟🌟🌟 把这里的串口号改成你刚才 socat 生成的第二个号码！
PORT = '/dev/pts/13'  
BAUDRATE = 115200

def XOR_check(byte_data):
    checksum = 0
    for b in byte_data:
        checksum ^= b
    return checksum

def receive_from_pc(ser):
    """精确解析上位机发来的控制帧和请求帧"""
    rx_buf = bytearray()
    while True:
        if ser.in_waiting > 0:
            rx_buf.extend(ser.read(ser.in_waiting))
            
            # 只要缓冲区够最小帧长度(5字节)，就尝试解析
            while len(rx_buf) >= 5:  
                if rx_buf[0] == 0xFA and rx_buf[1] == 0xAF:
                    frame_type = rx_buf[2]
                    
                    # ─── 1. 心跳请求帧 (0x52) ───
                    if frame_type == 0x52:
                        if rx_buf[3] == 0xFB and rx_buf[4] == 0xBF:
                            # 这个一秒钟发5次，打印出来太刷屏了，我们静默吃掉就行
                            del rx_buf[:5]
                        else:
                            rx_buf.pop(0)
                            
                    # ─── 2. 摇杆控制帧 (0x49) ───
                    elif frame_type == 0x49:
                        if len(rx_buf) >= 23: # 控制帧总长 23 字节
                            if rx_buf[21] == 0xFB and rx_buf[22] == 0xBF:
                                # 🌟 X光解包时刻！
                                # rx_buf[3:19] 是 16 个字节，刚好是 Y, X, Z, Yaw 四个 float
                                y, x, z, yaw = struct.unpack('<4f', rx_buf[3:19])
                                arm_angle = rx_buf[19] # 机械臂角度 1 个字节
                                
                                # 打印出极其舒适的数据日志
                                print(f"🕹️ [控制] 前后(Y):{y:5.2f} | 左右(X):{x:5.2f} | 上下(Z):{z:5.2f} | 偏航(Yaw):{yaw:5.2f} | 夹爪:{arm_angle}")
                                
                                del rx_buf[:23] # 吃掉这一包
                            else:
                                rx_buf.pop(0) # 帧尾不对，抛弃假帧头
                        else:
                            break # 长度还不够 23，等下一波数据进来再解
                            
                    else:
                        # 未知帧类型
                        rx_buf.pop(0)
                else:
                    # 不是帧头，往后挪一位继续找
                    rx_buf.pop(0)
                    
        time.sleep(0.01)

def send_to_pc(ser):
    """模拟单片机周期性回传温度和电流数据"""
    current_sim = 5.0 # 初始电流 5A
    temp_sim = 20.0   # 初始温度 20度

    while True:
        # 模拟电流逐渐增大，直到过流
        current_sim += 0.5 
        if current_sim > 15.0: current_sim = 5.0 # 循环

        temp_sim += 0.2

        # 严格按照附录打包上行数据帧 (帧头2 + 帧类型1 + 温度4 + 进水1 + 电流4)
        # 帧类型 0x53 = 'S' (Sensor)
        data_bytes = struct.pack('<3BfBf', 0xFA, 0xAF, 0x53, temp_sim, 0, current_sim)
        
        # 算校验和 (算帧类型、温度、进水、电流的异或)
        checksum = XOR_check(data_bytes[2:])
        
        # 拼上帧尾
        final_frame = data_bytes + struct.pack('<3B', checksum, 0xFB, 0xBF)
        
        ser.write(final_frame)
        print(f"📡 单片机发送数据 -> 温度: {temp_sim:.1f}°C, 电流: {current_sim:.1f}A")
        
        # 每秒回传两次
        time.sleep(0.5) 

if __name__ == "__main__":
    try:
        ser = serial.Serial(PORT, BAUDRATE)
        print(f"🤖 模拟单片机已启动，连接在 {PORT}")
        
        # 开一个线程专门接收上位机数据
        threading.Thread(target=receive_from_pc, args=(ser,), daemon=True).start()
        
        # 主线程狂发数据
        send_to_pc(ser)
        
    except Exception as e:
        print(f"模拟单片机启动失败: {e}")