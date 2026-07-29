# hal_oled.py
from machine import Pin, I2C
import time

try:
    import ssd1306
except ImportError:
    pass

class RobotOLED:
    def __init__(self, scl_pin=22, sda_pin=21, width=128, height=64):
        self.width = width
        self.height = height
        try:
            self.i2c = I2C(0, scl=Pin(scl_pin), sda=Pin(sda_pin), freq=400000)
            self.display = ssd1306.SSD1306_I2C(self.width, self.height, self.i2c)
            self.clear()
        except Exception as e:
            print("OLED Init Error:", e)
            self.display = None

    def clear(self):
        if self.display:
            self.display.fill(0)
            self.display.show()

    def show_text(self, text, x=0, y=28):
        if not self.display:
            return
        self.clear()
        self.display.text(str(text), x, y, 1)
        self.display.show()

    def show_emoji(self, emoji_name):
        if not self.display:
            return
        self.clear()
        if emoji_name == "heart":
            # Simple heart shape using rectangles and lines
            self.display.fill_rect(44, 20, 16, 16, 1)
            self.display.fill_rect(68, 20, 16, 16, 1)
            self.display.fill_rect(40, 24, 48, 16, 1)
            self.display.fill_rect(44, 40, 40, 8, 1)
            self.display.fill_rect(52, 48, 24, 8, 1)
            self.display.fill_rect(60, 56, 8, 8, 1)
        elif emoji_name == "cute_eyes":
            # Two rounded rectangles for eyes, with a pixel offset for pupils
            self.display.fill_rect(32, 20, 20, 24, 1)
            self.display.fill_rect(76, 20, 20, 24, 1)
            # Pupils (black to cut out)
            self.display.fill_rect(44, 24, 8, 8, 0)
            self.display.fill_rect(88, 24, 8, 8, 0)
        elif emoji_name == "angry_eyes":
            # Angry slanted eyebrows and eyes
            self.display.line(24, 20, 52, 32, 1)
            self.display.line(25, 20, 53, 32, 1)
            self.display.fill_rect(32, 32, 20, 12, 1)
            
            self.display.line(104, 20, 76, 32, 1)
            self.display.line(103, 20, 75, 32, 1)
            self.display.fill_rect(76, 32, 20, 12, 1)
        else:
            self.display.text("?", 60, 28, 1)
        
        self.display.show()

# Instantiate instance to expose to the server execution context
oled = RobotOLED()
