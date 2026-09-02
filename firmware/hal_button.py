from machine import Pin
from pin_config import PINS

class Button:
    def __init__(self, pin_num):
        # The schematic shows an external 10K pull-up resistor to 3.3V,
        # and the button connects the pin to GND when pressed.
        # So we configure the pin as an input. We don't need internal pulls.
        self._pin = Pin(pin_num, Pin.IN)
        
    def is_pressed(self):
        # Because of the pull-up, it reads 1 when idle and 0 when pressed.
        return self._pin.value() == 0

# Pin is defined centrally in pin_config.py
button = Button(PINS["BUTTON"])
