# hal_car.py
from machine import Pin

# Onboard Components
# Pin 2 is the standard onboard LED for most ESP32 dev boards
onboard_led = Pin(2, Pin.OUT)

class RobotCar:
    def __init__(self):
        # Motor Pin Configurations (Custom PCB targets)
        self.m1a = Pin(12, Pin.OUT)
        self.m1b = Pin(13, Pin.OUT)
        self.m2a = Pin(14, Pin.OUT)
        self.m2b = Pin(15, Pin.OUT)
        self.stop()

    def move(self, direction):
        if direction == "FORWARD":
            self.m1a.value(1); self.m1b.value(0); self.m2a.value(1); self.m2b.value(0)
        elif direction == "BACKWARD":
            self.m1a.value(0); self.m1b.value(1); self.m2a.value(0); self.m2b.value(1)
        elif direction == "LEFT":
            self.m1a.value(0); self.m1b.value(1); self.m2a.value(1); self.m2b.value(0)
        elif direction == "RIGHT":
            self.m1a.value(1); self.m1b.value(0); self.m2a.value(0); self.m2b.value(1)
        elif direction == "STOP":
            self.stop()

    def stop(self):
        self.m1a.value(0); self.m1b.value(0); self.m2a.value(0); self.m2b.value(0)

# Instantiate instances to expose to the server execution context
car = RobotCar()