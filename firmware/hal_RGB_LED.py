# hal_RGB_LED.py
#
# Driver for two WS2812 5050 RGB LED modules (8 LEDs each).
#   - Front strip (RGB_LED_F): LED_DATA_F = GPIO 15, 8 LEDs
#   - Back  strip (RGB_LED_B): LED_DATA_B = GPIO 13, 8 LEDs
#
# Hardware notes:
#   - WS2812 modules are powered from the +5V rail on J7 / J12.
#   - Data lines pass through 330 Ohm series resistors (R2, R3) to GPIO 15/13.
#   - MicroPython's built-in `neopixel` module handles the WS2812 timing.
#
# Usage examples:
#   rgb_front.set_led(0, 255, 0, 0)   # LED 0 -> red
#   rgb_back.set_all(0, 0, 255)        # all 8 LEDs -> blue
#   rgb_front.clear()                  # turn off all LEDs on front strip
#   rgb_back.show_effect("rainbow")    # run a built-in effect

import neopixel
from machine import Pin
import time


class RGBStrip:
    """
    Controls a single WS2812 LED strip.

    Parameters
    ----------
    pin : int
        GPIO number connected to the strip's data line.
    num_leds : int
        Number of LEDs on the strip (default 8).
    """

    def __init__(self, pin: int, num_leds: int = 8):
        self._pin = pin
        self._num_leds = num_leds
        self._np = neopixel.NeoPixel(Pin(pin, Pin.OUT), num_leds)
        self.clear()  # start with all LEDs off

    # ------------------------------------------------------------------
    # Core LED control
    # ------------------------------------------------------------------

    def set_led(self, index: int, r: int, g: int, b: int):
        """
        Set a single LED by index and immediately update the strip.

        Parameters
        ----------
        index : int   LED index, 0-based (0 to num_leds-1).
        r, g, b : int Colour components, each 0-255.
        """
        if 0 <= index < self._num_leds:
            self._np[index] = (
                max(0, min(255, r)),
                max(0, min(255, g)),
                max(0, min(255, b)),
            )
            self._np.write()

    def set_all(self, r: int, g: int, b: int):
        """Turn every LED on the strip to the same colour and update."""
        colour = (max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)))
        for i in range(self._num_leds):
            self._np[i] = colour
        self._np.write()

    def clear(self):
        """Turn off all LEDs on this strip."""
        self.set_all(0, 0, 0)

    def turn_on(self, r: int = 255, g: int = 255, b: int = 255):
        """Turn on all LEDs to white (or a specified colour) and update."""
        self.set_all(r, g, b)

    # ------------------------------------------------------------------
    # Built-in effects  (blocking - designed for simple block programs)
    # ------------------------------------------------------------------

    def show_effect(self, name: str, delay_ms: int = 50):
        """
        Play a named lighting effect.

        Supported effects
        -----------------
        "rainbow"     - Cycles through the colour wheel across all LEDs.
        "chase_red"   - Red dot travels along the strip.
        "chase_green" - Green dot travels along the strip.
        "chase_blue"  - Blue dot travels along the strip.
        "blink_white" - Blinks all LEDs white three times.
        "pulse_red"   - Fades red in and out once.
        "police"      - Red/blue alternating flash (6 cycles).
        "fire"        - Orange/red flicker effect.
        """
        name = name.lower().strip()

        if name == "rainbow":
            self._effect_rainbow(delay_ms)
        elif name == "chase_red":
            self._effect_chase(255, 0, 0, delay_ms)
        elif name == "chase_green":
            self._effect_chase(0, 255, 0, delay_ms)
        elif name == "chase_blue":
            self._effect_chase(0, 0, 255, delay_ms)
        elif name == "blink_white":
            self._effect_blink(255, 255, 255, times=3, delay_ms=200)
        elif name == "pulse_red":
            self._effect_pulse(255, 0, 0, delay_ms=10)
        elif name == "police":
            self._effect_police(cycles=6, delay_ms=150)
        elif name == "fire":
            self._effect_fire(delay_ms)
        # Unknown effect names are silently ignored

    # ------------------------------------------------------------------
    # Internal effect helpers
    # ------------------------------------------------------------------

    def _wheel(self, pos: int):
        """Map 0-255 to a colour on the RGB wheel (no white)."""
        pos = pos & 0xFF
        if pos < 85:
            return (255 - pos * 3, pos * 3, 0)
        if pos < 170:
            pos -= 85
            return (0, 255 - pos * 3, pos * 3)
        pos -= 170
        return (pos * 3, 0, 255 - pos * 3)

    def _effect_rainbow(self, delay_ms: int):
        for j in range(256):
            for i in range(self._num_leds):
                self._np[i] = self._wheel((i * 256 // self._num_leds + j) & 255)
            self._np.write()
            time.sleep_ms(delay_ms)

    def _effect_chase(self, r: int, g: int, b: int, delay_ms: int):
        for i in range(self._num_leds):
            self._np[i] = (r, g, b)
            self._np.write()
            time.sleep_ms(delay_ms)
            self._np[i] = (0, 0, 0)
        self._np.write()

    def _effect_blink(self, r: int, g: int, b: int, times: int, delay_ms: int):
        for _ in range(times):
            self.set_all(r, g, b)
            time.sleep_ms(delay_ms)
            self.clear()
            time.sleep_ms(delay_ms)

    def _effect_pulse(self, r: int, g: int, b: int, delay_ms: int):
        for v in range(0, 256, 5):
            self.set_all(r * v // 255, g * v // 255, b * v // 255)
            time.sleep_ms(delay_ms)
        for v in range(255, -1, -5):
            self.set_all(r * v // 255, g * v // 255, b * v // 255)
            time.sleep_ms(delay_ms)
        self.clear()

    def _effect_police(self, cycles: int, delay_ms: int):
        for _ in range(cycles):
            self.set_all(255, 0, 0)
            time.sleep_ms(delay_ms)
            self.set_all(0, 0, 255)
            time.sleep_ms(delay_ms)
        self.clear()

    def _effect_fire(self, delay_ms: int):
        import os  # os.urandom works on ALL MicroPython versions and ESP32 builds
        for _ in range(30):
            for i in range(self._num_leds):
                flicker = os.urandom(1)[0] & 0x1F  # 0-31
                self._np[i] = (200 + flicker, 40 + flicker // 2, 0)
            self._np.write()
            time.sleep_ms(delay_ms)
        self.clear()

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def num_leds(self) -> int:
        """Number of LEDs in this strip."""
        return self._num_leds


# ---------------------------------------------------------------------------
# Module-level instances - these names are injected into every block program
# via the EXECUTION_HEADER in device_controller.py.
#
#   rgb_front  -> GPIO 15 (LED_DATA_F)  -> J7  RGB_LED_F  (8 LEDs)
#   rgb_back   -> GPIO 13 (LED_DATA_B)  -> J12 RGB_LED_B  (8 LEDs)
# ---------------------------------------------------------------------------

rgb_front = RGBStrip(pin=15, num_leds=8)
rgb_back  = RGBStrip(pin=13, num_leds=8)
