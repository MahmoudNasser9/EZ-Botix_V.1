# hal_ultrasonic.py
from machine import Pin, time_pulse_us
import time

class Ultrasonic:
    """
    Hardware abstraction for an HC-SR04 ultrasonic sensor.
    """
    def __init__(self, trigger_pin=14, echo_pin=27):
        self.trigger = Pin(trigger_pin, Pin.OUT)
        self.echo = Pin(echo_pin, Pin.IN)
        self.trigger.value(0)
        
    def distance_cm(self):
        """
        Measure the distance in centimeters.
        Returns -1 if out of range or no echo received.
        """
        # Ensure trigger is low
        self.trigger.value(0)
        time.sleep_us(2)
        
        # Send a 10us pulse
        self.trigger.value(1)
        time.sleep_us(10)
        self.trigger.value(0)
        
        try:
            # Measure echo pulse length (high state), timeout 30ms (~5 meters)
            pulse_time = time_pulse_us(self.echo, 1, 30000)
            if pulse_time < 0:
                return -1
            
            # Sound speed is 343 m/s = 0.0343 cm/us
            # Distance = (pulse_time * 0.0343) / 2
            distance = (pulse_time * 0.0343) / 2
            return round(distance, 1)
        except OSError:
            # Timeout or other error
            return -1

# Expose a global instance for easy use in user code
ultrasonic = Ultrasonic(trigger_pin=14, echo_pin=27)
