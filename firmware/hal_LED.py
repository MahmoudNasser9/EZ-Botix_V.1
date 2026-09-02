from machine import Pin
from pin_config import PINS

# Standard ESP32 dev board onboard LED (Active HIGH)
onboard_led = Pin(PINS["LED_ONBOARD"], Pin.OUT)

class InvertedLED:
    """Wrapper for pull-up LEDs where writing 0 turns it ON and 1 turns it OFF."""
    def __init__(self, pin_num):
        self._pin = Pin(pin_num, Pin.OUT, Pin.PULL_UP, value=1)
        
    def value(self, val):
        # Invert the logic: requested ON (1) -> write LOW (0)
        self._pin.value(0 if val else 1)

    def toggle(self):
        # Toggle the underlying pin state
        self._pin.toggle()

# External LED at TX2 (Active LOW due to 3.3V pull-up)
external_led = InvertedLED(PINS["LED_EXTERNAL"])

# Ensure they start turned off (0)
onboard_led.value(0)
external_led.value(0)
