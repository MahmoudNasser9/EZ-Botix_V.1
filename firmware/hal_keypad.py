# hal_keypad.py
from machine import Pin
import time

class MatrixKeypad:
    def __init__(self):
        # Explicit ESP32 pin maps for row outputs and column inputs
        self.row_pins = [Pin(13, Pin.OUT), Pin(12, Pin.OUT), Pin(14, Pin.OUT), Pin(27, Pin.OUT)]
        self.col_pins = [Pin(26, Pin.IN, Pin.PULL_DOWN), Pin(25, Pin.IN, Pin.PULL_DOWN), Pin(33, Pin.IN, Pin.PULL_DOWN), Pin(32, Pin.IN, Pin.PULL_DOWN)]
        
        self.layout = [
            ['1','2','3','A'],
            ['4','5','6','B'],
            ['7','8','9','C'],
            ['*','0','#','D']
        ]

        # Tracks the key currently held down, so a held key is reported
        # once instead of on every scan (see read_key below).
        self._last_key = None

    def _scan(self):
        """One raw scan of the matrix. Returns the key currently held, or None."""
        for r_idx, row in enumerate(self.row_pins):
            row.value(1) # Drive current row HIGH
            for c_idx, col in enumerate(self.col_pins):
                if col.value() == 1: # Check which column reads HIGH
                    row.value(0)
                    return self.layout[r_idx][c_idx]
            row.value(0) # Pull row back LOW
        return None

    def read_key(self):
        """Scans the matrix and returns a newly-pressed key, or None.

        This is edge-triggered and debounced:
          - A key held down across multiple calls is only returned once,
            on the call where the press was first detected.
          - A short delay + re-scan confirms the press is stable before
            it's accepted, so mechanical switch bounce doesn't get
            reported as multiple separate key presses.
        """
        current = self._scan()

        if current is None:
            self._last_key = None
            return None

        if current == self._last_key:
            # Still the same key from a previous read - already reported.
            return None

        time.sleep_ms(20)  # debounce delay
        if self._scan() != current:
            # Reading changed during the debounce window - contact bounce,
            # not a real press. Ignore it; the next scan will pick up
            # whatever the settled state actually is.
            return None

        self._last_key = current
        return current

    def wait_for_key(self, target_key):
        """Blocks the user execution thread until the specified key is hit"""
        while True:
            if self.read_key() == target_key:
                break
            time.sleep_ms(50) # Prevents core CPU starvation

# Instantiate a global instance for the system context
keypad = MatrixKeypad()