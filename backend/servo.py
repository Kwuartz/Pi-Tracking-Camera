import pigpio
import time

pi = pigpio.pi()
if not pi.connected:
    exit()

servo1_gpio = 2
servo2_gpio = 3

def angle_to_pulse(angle):
    return 1000 + (angle / 180.0) * 1000

pi.set_servo_pulsewidth(servo1_gpio, angle_to_pulse(90))
pi.set_servo_pulsewidth(servo2_gpio, angle_to_pulse(90))

# while True:
#     for angle in range(0, 181, 5):
#         pi.set_servo_pulsewidth(servo1_gpio, angle_to_pulse(angle))
#         pi.set_servo_pulsewidth(servo2_gpio, angle_to_pulse(angle))
#         time.sleep(0.5)
#     for angle in range(180, -1, -5):
#         pi.set_servo_pulsewidth(servo1_gpio, angle_to_pulse(angle))
#         pi.set_servo_pulsewidth(servo2_gpio, angle_to_pulse(angle))
#         time.sleep(0.5)

pi.stop()