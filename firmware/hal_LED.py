# =============================================================================
# hal_LED.py — LED Driver (Instant On/Off/Toggle)
# =============================================================================
#
# HAL driver for the EZ-BOTIX LEDs.
#
# HARDWARE:
#   - Onboard LED (Active HIGH) on GPIO 2
#   - External LED (Active LOW) on GPIO 17 (TX2 pin)
#
# DESIGN:
#   LEDs are INSTANT actuators — they don't need a command queue,
#   cyclic processing, or duration tracking. They simply turn on or off.
#
#   If you want blinking, use the scheduler's Tasks system:
#       scheduler.add_task(200, onboard_led.toggle)
#       scheduler.run(duration_ms=0)
#
#   Or in Blockly:
#       ⏱️ Every [200] ms do
#           💡 Onboard LED [TOGGLE]
#       ⏱️ Start Task Scheduler Loop
#
# DEPENDENCIES:
#   - machine (Pin) — MicroPython hardware abstraction
#   - pin_config — centralized GPIO pin assignments
# =============================================================================

from machine import Pin
from pin_config import PINS


# ─────────────────────────────────────────────────────────────────────
# Low-level hardware wrapper (Active LOW)
# ─────────────────────────────────────────────────────────────────────

class InvertedLED:
    """
    Hardware wrapper for pull-up LEDs where logic is inverted.
    Writing 0 turns it ON and 1 turns it OFF.
    Provides the same .value(val) API as a normal machine.Pin.
    """
    def __init__(self, pin_num):
        self._pin = Pin(pin_num, Pin.OUT, Pin.PULL_UP, value=1)

    def value(self, val):
        # Invert the logic: requested ON (1) -> write LOW (0)
        self._pin.value(0 if val else 1)


# ─────────────────────────────────────────────────────────────────────
# High-level LED Controller (Instant)
# ─────────────────────────────────────────────────────────────────────

class LEDController:
    """
    Simple LED controller with instant on/off/toggle.

    No command queue, no cyclic, no scheduler registration needed.
    Every method call takes effect IMMEDIATELY on the hardware.

    Usage:
        onboard_led.on()       # Turns on instantly
        onboard_led.off()      # Turns off instantly
        onboard_led.toggle()   # Flips current state
        onboard_led.value(1)   # V1 backward compatibility
    """

    def __init__(self, hardware_pin):
        """
        Initialize the LED controller.

        Args:
            hardware_pin: A machine.Pin or InvertedLED instance that
                          has a .value(val) method.
        """
        self._led = hardware_pin
        self._state = False  # Track current state for toggle

        # Ensure LED starts off
        self._led.value(0)

    # ═════════════════════════════════════════════════════════════════
    #  PUBLIC API
    # ═════════════════════════════════════════════════════════════════

    def on(self):
        """Turn the LED on immediately."""
        self._state = True
        self._led.value(1)

    def off(self):
        """Turn the LED off immediately."""
        self._state = False
        self._led.value(0)

    def toggle(self):
        """
        Toggle the LED: if on → off, if off → on.

        Uses internal state tracking (not hardware readback) so it
        works reliably with both normal and inverted LEDs.
        """
        self._state = not self._state
        self._led.value(1 if self._state else 0)

    def value(self, val):
        """
        Set LED state by value (0 or 1).

        Backward compatibility with the old V1 API where
        Blockly generated `onboard_led.value(1)`.
        """
        self._state = bool(val)
        self._led.value(val)


# =============================================================================
# Module-level instances
# =============================================================================
# These are the global LED instances used by all user code and
# Blockly-generated programs. Created once when this module is imported.
#
# Usage:
#   from hal_LED import onboard_led, external_led
#   onboard_led.on()
#   external_led.toggle()
# =============================================================================

# Standard ESP32 dev board onboard LED (Active HIGH)
_onboard_pin = Pin(PINS["LED_ONBOARD"], Pin.OUT)
onboard_led = LEDController(_onboard_pin)

# External LED at TX2 (Active LOW due to 3.3V pull-up)
_external_pin = InvertedLED(PINS["LED_EXTERNAL"])
external_led = LEDController(_external_pin)
