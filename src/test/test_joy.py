import pygame
import time

pygame.init()
pygame.joystick.init()

count = pygame.joystick.get_count()
print(f"【系统报告】电脑当前识别到了 {count} 个手柄！")

if count > 0:
    joy = pygame.joystick.Joystick(0)
    joy.init()
    print(f"手柄名称: {joy.get_name()}")
    
    print("请随便按几个按键或摇杆，按 Ctrl+C 退出...")
    while True:
        pygame.event.pump()
        for event in pygame.event.get():
            if event.type == pygame.JOYBUTTONDOWN:
                print(f"🔴 按下了按键，编号: {event.button}")
            elif event.type == pygame.JOYAXISMOTION and abs(event.value) > 0.1:
                print(f"🕹️ 摇动了轴 {event.axis}，数值: {event.value:.2f}")
        time.sleep(0.05)