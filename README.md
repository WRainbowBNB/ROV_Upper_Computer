手柄和键盘的映射与miniROV文档中定义的相同，用户若想改映射的话，直接去config.ini里面改就行，

注意，在手柄接入时，键盘按键命令中与移动相关的映射失效，只看手柄（即：前进后退转弯上下等等），但是速度模式的改变和机械爪则可通过键盘或手柄肩键进行改变

关于手柄相关映射，不同手柄对应按键的序号可能不同，需要通过test里面的手柄测试得知该手柄按键的实际序号，并去config.ini里面进行相应修改

在进行下位机连通测试时，应打开socat虚拟串口，记录当前串口号，并在src/serial_comm/serial.py 和test/serial_env.py中进行相应修改

<img width="1250" height="1003" alt="image" src="https://github.com/user-attachments/assets/72b9bd37-f687-47ec-888b-758b8d021f53" />

<img width="1250" height="1003" alt="image" src="https://github.com/user-attachments/assets/8610f707-375b-40e8-b41f-3ea95a6b7540" />
