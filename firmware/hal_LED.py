from machine import Pin

# Standard ESP32 dev board onboard LED is GPIO 2 (Active HIGH)
onboard_led = Pin(2, Pin.OUT)

class InvertedLED:
    """Wrapper for pull-up LEDs where writing 0 turns it ON and 1 turns it OFF."""
    def __init__(self, pin_num):
        self._pin = Pin(pin_num, Pin.OUT, Pin.PULL_UP)
        
    def value(self, val):
        # Invert the logic: requested ON (1) -> write LOW (0)
        self._pin.value(0 if val else 1)

# Custom external LED at GPIO 5 (Active LOW due to 3.3V pull-up)
external_led = InvertedLED(5)

# Ensure they start turned off (0)
onboard_led.value(0)
external_led.value(0)
