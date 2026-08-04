# hal_buzzer.py
from machine import Pin, PWM
import time

class RobotBuzzer:
    def __init__(self, pin=2):
        # Configure the passive buzzer on the specified pin (GPIO 2 by default)
        self.pwm = PWM(Pin(pin))
        self.pwm.duty(0)
        
    def play_tone(self, freq, duration_ms=None):
        """
        Plays a tone at the specified frequency (Hz).
        If duration_ms is provided, blocks and plays for that duration, then stops.
        """
        if freq > 0:
            self.pwm.freq(int(freq))
            self.pwm.duty(512) # 50% duty cycle for maximum volume
        else:
            self.pwm.duty(0)
            
        if duration_ms is not None:
            time.sleep_ms(int(duration_ms))
            self.stop()
            
    def stop(self):
        """Stops the buzzer immediately."""
        self.pwm.duty(0)

# Instantiate instance to expose to the server execution context
buzzer = RobotBuzzer()
