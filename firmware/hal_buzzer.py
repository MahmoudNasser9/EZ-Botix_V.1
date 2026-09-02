# hal_buzzer.py
from machine import Pin, PWM
import time
from pin_config import PINS

class RobotBuzzer:
    def __init__(self, pin=None):
        if pin is None:
            pin = PINS["BUZZER"]
        # Configure the passive buzzer on the specified pin (GPIO 19 by default)
        # Avoid PULL_UP, as it leaks current and causes a faint hum!
        # Initialize PWM with duty=0 to prevent startup glitches.
        self.pwm = PWM(Pin(pin, Pin.OUT, Pin.PULL_DOWN), freq=1000, duty=0)
        
    def play_tone(self, freq, duration_ms=None):
        """
        Plays a tone at the specified frequency (Hz).
        
        Frequency (freq) Limits:
        - Minimum: ~20 Hz (below this it becomes individual clicks rather than a tone)
        - Maximum: ~20,000 Hz (upper limit of human hearing)
        - Note: ESP32 PWM supports 1 Hz up to 40,000,000 Hz, but buzzers only operate well in the audible range.
        
        Duty Cycle:
        - The code uses a fixed duty cycle of 512 (50% on a 0-1023 scale) to generate the loudest sound.
        
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

    def play_melody(self, name):
        """Plays a pre-programmed melody."""
        MELODIES = {
            "Mario": [
                (660, 100), (0, 150), (660, 100), (0, 300), (660, 100), (0, 300),
                (510, 100), (0, 100), (660, 100), (0, 300), (770, 100), (0, 550), (380, 100)
            ],
            "StarWars": [
                (392, 350), (392, 350), (392, 350), (311, 250), (466, 100),
                (392, 350), (311, 250), (466, 100), (392, 700)
            ],
            "Siren": [
                (800, 300), (1000, 300), (800, 300), (1000, 300), (800, 300), (1000, 300)
            ],
            "Happy": [
                (523, 200), (0, 50), (523, 200), (0, 50), (587, 400), (523, 400), 
                (698, 400), (659, 800)
            ],
            "CarHorn": [
                (450, 300), (0, 100), (450, 400)
            ],
            "TruckHorn": [
                (250, 800)
            ],
            "PowerUp": [
                (440, 100), (554, 100), (659, 100), (880, 200)
            ],
            "PowerDown": [
                (880, 100), (659, 100), (554, 100), (440, 200)
            ],
            "Error": [
                (150, 200), (0, 50), (150, 200)
            ],
            "Success": [
                (1046, 150), (1568, 300)
            ],
            "MissionImpossible": [
                (784, 150), (0, 150), (784, 150), (0, 150),
                (932, 150), (0, 150), (1046, 150), (0, 150),
                (784, 150), (0, 150), (784, 150), (0, 150),
                (698, 150), (0, 150), (740, 150), (0, 150)
            ]
        }
        if name in MELODIES:
            for freq, duration in MELODIES[name]:
                self.play_tone(freq, duration)
                # Small 20ms pause between notes so they don't blend together
                time.sleep_ms(20)
            self.stop()

# Instantiate instance to expose to the server execution context
buzzer = RobotBuzzer()
buzzer.stop()