# =============================================================================
# hal_buzzer.py — Buzzer Driver (Dual-Mode, Queued)
# =============================================================================
#
# HAL driver for the EZ-BOTIX passive buzzer.
#
# HARDWARE:
#   - Passive piezo buzzer on GPIO 19 (configurable via pin_config.py)
#   - Driven by ESP32 PWM at 50% duty cycle for maximum volume
#   - PULL_DOWN on the pin to avoid faint hum (PULL_UP leaks current)
#
# CAPABILITIES:
#   - Single tones: play_tone(freq, duration_ms)
#   - Pre-programmed melodies: play_melody("Mario")
#   - Both blocking (default) and non-blocking modes
#   - Command queue: multiple tones/melodies are buffered and played
#     in sequence, never overwritten
#
# INHERITANCE:
#   BuzzerDriver(HalTimedDriver) → inherits:
#     • Command queue (FIFO, max 32 commands)
#     • Automatic duration checking (auto-stop when time expires)
#     • Blocking spin loop (advances all drivers via scheduler)
#     • stop() / is_busy() / clear_queue()
#
# FREQUENCY LIMITS:
#   - Minimum: ~20 Hz (below this → individual clicks, not a tone)
#   - Maximum: ~20,000 Hz (upper limit of human hearing)
#   - ESP32 PWM supports 1 Hz to 40 MHz, but the passive buzzer
#     only responds well in the audible range.
#
# DEPENDENCIES:
#   - machine (Pin, PWM) — MicroPython hardware abstraction
#   - pin_config — centralized GPIO pin assignments
#   - hal_base (HalTimedDriver) — base class with queue + timing
# =============================================================================

from machine import Pin, PWM
from pin_config import PINS
from hal_base import HalTimedDriver


class BuzzerDriver(HalTimedDriver):
    """
    HAL driver for the passive buzzer.

    Supports single tones and pre-programmed melodies, with both
    blocking and non-blocking modes. Commands are queued — issuing
    multiple tones plays them in sequence, not one overwriting another.

    Usage:
        buzzer.play_tone(440, 500)                  # Blocking: A4 for 500ms
        buzzer.play_tone(880, 300, blocking=False)   # Non-blocking: queued
        buzzer.play_melody("Mario")                  # Blocking: full melody
        buzzer.play_melody("Mario", blocking=False)  # Non-blocking: queued
        buzzer.stop()                                # Emergency stop + clear queue
    """

    # ─────────────────────────────────────────────────────────────────
    # Driver-specific constants (override base class defaults)
    # ─────────────────────────────────────────────────────────────────

    # Buzzer needs fast polling for precise note transitions.
    # At 1ms, a 100ms note has at most 1ms timing error (1%).
    CYCLIC_INTERVAL_MS = 1

    # Melodies expand to many individual tone + silence commands.
    # "MissionImpossible" has 16 notes × 2 (note + gap) = 32 commands.
    # Set the queue large enough for the longest melody.
    MAX_QUEUE_SIZE = 32

    # ─────────────────────────────────────────────────────────────────
    # Pre-programmed melodies
    # ─────────────────────────────────────────────────────────────────
    # Each melody is a list of (frequency_hz, duration_ms) tuples.
    # A frequency of 0 represents a silent pause.
    #
    # These are defined at the CLASS level (not instance level) to
    # avoid re-creating the dict on every play_melody() call.
    # ─────────────────────────────────────────────────────────────────

    MELODIES = {
        "Mario": [
            (660, 100), (0, 150), (660, 100), (0, 300), (660, 100), (0, 300),
            (510, 100), (0, 100), (660, 100), (0, 300), (770, 100), (0, 550),
            (380, 100),
        ],
        "StarWars": [
            (392, 350), (392, 350), (392, 350), (311, 250), (466, 100),
            (392, 350), (311, 250), (466, 100), (392, 700),
        ],
        "Siren": [
            (800, 300), (1000, 300), (800, 300), (1000, 300),
            (800, 300), (1000, 300),
        ],
        "Happy": [
            (523, 200), (0, 50), (523, 200), (0, 50), (587, 400),
            (523, 400), (698, 400), (659, 800),
        ],
        "CarHorn": [
            (450, 300), (0, 100), (450, 400),
        ],
        "TruckHorn": [
            (250, 800),
        ],
        "PowerUp": [
            (440, 100), (554, 100), (659, 100), (880, 200),
        ],
        "PowerDown": [
            (880, 100), (659, 100), (554, 100), (440, 200),
        ],
        "Error": [
            (150, 200), (0, 50), (150, 200),
        ],
        "Success": [
            (1046, 150), (1568, 300),
        ],
        "MissionImpossible": [
            (784, 150), (0, 150), (784, 150), (0, 150),
            (932, 150), (0, 150), (1046, 150), (0, 150),
            (784, 150), (0, 150), (784, 150), (0, 150),
            (698, 150), (0, 150), (740, 150), (0, 150),
        ],
    }

    # ─────────────────────────────────────────────────────────────────
    # Constructor
    # ─────────────────────────────────────────────────────────────────

    def __init__(self, pin=None):
        """
        Initialize the buzzer driver.

        Sets up the PWM hardware and initializes the base class
        (command queue, state machine, timing).

        Args:
            pin (int or None): GPIO pin number. If None, uses the
                               BUZZER pin from pin_config.py.
        """
        # Initialize base class (queue, state machine, timing)
        super().__init__()

        # ── Hardware setup ────────────────────────────────────────────
        if pin is None:
            pin = PINS["BUZZER"]

        # Configure PWM on the buzzer pin.
        #   - Pin.PULL_DOWN: prevents current leakage through the
        #     buzzer's internal pull-up, which causes a faint hum.
        #   - freq=1000: initial frequency (will be overwritten on play)
        #   - duty=0: start silent (no startup glitch)
        self._pwm = PWM(Pin(pin, Pin.OUT, Pin.PULL_DOWN), freq=1000, duty=0)

    # ═════════════════════════════════════════════════════════════════
    #  PUBLIC API — what user code and Blockly-generated code calls
    # ═════════════════════════════════════════════════════════════════

    def play_tone(self, freq, duration_ms=0, blocking=True):
        """
        Play a tone at the given frequency.

        The tone is added to the command queue. If other tones are
        already queued, this tone plays AFTER them (not overwriting).

        Args:
            freq (int):        Frequency in Hz (20 - 20000).
                               Values ≤ 0 are treated as silence.
            duration_ms (int): How long to play, in milliseconds.
                               0 = play indefinitely until stop() is called.
            blocking (bool):   True (default) = wait here until the tone
                                 (and any previously queued commands) finish.
                               False = return immediately, tone plays in
                                 background via the scheduler.

        Examples:
            # Blocking (beginner / Blockly):
            buzzer.play_tone(440, 500)              # A4 for 500ms, waits

            # Non-blocking (advanced):
            buzzer.play_tone(440, 500, blocking=False)   # Queued, returns
            buzzer.play_tone(880, 300, blocking=False)   # Queued after 440Hz

            # Indefinite (until stop):
            buzzer.play_tone(440)                   # Plays until buzzer.stop()
        """
        # Build the command dict for the queue.
        # 'action' tells _on_command_start what kind of command this is.
        cmd = {
            'action': 'tone',
            'freq': int(freq),
            'duration_ms': int(duration_ms),
        }

        # _enqueue adds to queue and optionally blocks until done.
        # This is inherited from HalDriver.
        self._enqueue(cmd, blocking)

    def play_melody(self, name, blocking=True):
        """
        Play a pre-programmed melody.

        The melody is EXPANDED into individual tone and silence commands
        in the queue. Each note becomes a separate command, so the
        melody plays note-by-note via the normal cyclic mechanism.

        A small 20ms silence gap is added between notes to prevent
        them from blending together (matches the original behavior).

        Args:
            name (str):      Melody name. Available melodies:
                             "Mario", "StarWars", "Siren", "Happy",
                             "CarHorn", "TruckHorn", "PowerUp",
                             "PowerDown", "Error", "Success",
                             "MissionImpossible"
            blocking (bool): True (default) = wait until the entire
                               melody finishes.
                             False = return immediately, melody plays
                               in background via the scheduler.

        Examples:
            buzzer.play_melody("Mario")                  # Blocking
            buzzer.play_melody("StarWars", blocking=False) # Background

        Unknown melody names are silently ignored (no error).
        """
        # Look up the melody. If not found, do nothing.
        if name not in self.MELODIES:
            return

        notes = self.MELODIES[name]

        # ── Expand the melody into individual commands ────────────────
        # Each (freq, duration) pair becomes either a 'tone' command
        # (if freq > 0) or a 'silence' command (if freq == 0).
        # A 20ms silence gap is added between notes so they don't
        # blend together — this matches the original behavior.
        for freq, dur in notes:
            if freq > 0:
                # Audible note
                self._command_queue.append({
                    'action': 'tone',
                    'freq': freq,
                    'duration_ms': dur,
                })
            else:
                # Silent pause (freq == 0 in the melody data)
                self._command_queue.append({
                    'action': 'silence',
                    'duration_ms': dur,
                })

            # Add a tiny 20ms gap between notes so they don't blend.
            # Without this, consecutive notes at the same frequency
            # sound like one continuous tone instead of two separate notes.
            self._command_queue.append({
                'action': 'silence',
                'duration_ms': 20,
            })

        # ── If blocking, wait for the entire melody to finish ─────────
        if blocking:
            self._block_until_idle()

    # ═════════════════════════════════════════════════════════════════
    #  BASE CLASS IMPLEMENTATIONS (required by HalTimedDriver)
    # ═════════════════════════════════════════════════════════════════

    def _on_command_start(self, cmd):
        """
        Start the hardware for a tone or silence command.

        Called by the base class when a command is dequeued from the
        queue and the driver transitions from IDLE to ACTIVE.

        For 'tone' commands: set PWM frequency and 50% duty cycle.
        For 'silence' commands: set PWM duty to 0 (no sound).
        Both set _duration_ms for the base class auto-stop timer.

        Args:
            cmd (dict): The command to execute. Has 'action' key
                        ('tone' or 'silence') and 'duration_ms'.
        """
        action = cmd['action']

        if action == 'tone':
            # ── Start playing the tone ────────────────────────────────
            # Set PWM frequency to the desired Hz value.
            # Set duty cycle to 512 (50% of 0-1023 range) for max volume.
            self._pwm.freq(cmd['freq'])
            self._pwm.duty(512)

            # Tell the base class how long to run before auto-stopping.
            # If duration_ms is 0, the tone plays until stop() is called.
            self._duration_ms = cmd['duration_ms']

        elif action == 'silence':
            # ── Silent pause (between melody notes) ───────────────────
            # Turn off sound but keep the timing running.
            # The base class auto-stop will end this silence after
            # the specified duration, then dequeue the next command.
            self._pwm.duty(0)
            self._duration_ms = cmd['duration_ms']

    def _on_command_end(self):
        """
        Turn off the buzzer.

        Called when:
          • A timed command expires (auto-stop by base class)
          • stop() is called by user code (emergency stop)

        Idempotent: safe to call even if the buzzer is already silent.
        Setting duty to 0 on an already-silent PWM is a no-op.
        """
        self._pwm.duty(0)


# =============================================================================
# Module-level instance
# =============================================================================
# This is the global buzzer instance used by all user code and
# Blockly-generated programs. It is created once when this module
# is first imported.
#
# Usage:
#   from hal_buzzer import buzzer
#   buzzer.play_tone(440, 500)
# =============================================================================

buzzer = BuzzerDriver()