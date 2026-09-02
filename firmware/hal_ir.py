from machine import Pin, ADC
from pin_config import PINS

class IRSensor:
    def __init__(self, pin_num):
        # The pin is configured as an input.
        # D34 on ESP32 is input-only.
        self._pin = Pin(pin_num, Pin.IN)

    def is_obstacle_detected(self):
        """
        Returns True if an obstacle is detected.
        The sensor gives a low-level (0) output signal when an obstacle is detected.
        """
        return self._pin.value() == 0

    def get_digital_value(self):
        """
        Returns the raw digital value (0 or 1).
        """
        return self._pin.value()

# Pin is defined centrally in pin_config.py
ir_sensor = IRSensor(PINS["IR_SENSOR"])
