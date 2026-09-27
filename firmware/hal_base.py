# =============================================================================
# hal_base.py — Base Classes for the EZ-BOTIX HAL Driver Framework
# =============================================================================
#
# This module defines the three-level inheritance hierarchy that ALL
# hardware drivers in the EZ-BOTIX firmware build upon:
#
#   HalDriver          — Abstract base for every driver
#   HalTimedDriver     — For output drivers with duration-based commands
#   HalPollingDriver   — For input drivers with periodic scanning
#
# No driver should ever be written from scratch. Always inherit from
# one of these base classes.
#
# DESIGN PRINCIPLES:
#   1. Command Queue — Commands are buffered (FIFO), never overwritten.
#   2. Dual-Mode API — Every timed command supports blocking + non-blocking.
#   3. Cyclic Cooperation — Every driver's cyclic() is called by the
#      scheduler at a driver-specific interval.
#
# DEPENDENCIES:
#   - time (MicroPython built-in)
#   - No imports from any other HAL module (avoids circular dependencies)
#
# USAGE:
#   from hal_base import HalTimedDriver, HalPollingDriver
#
#   class BuzzerDriver(HalTimedDriver):
#       CYCLIC_INTERVAL_MS = 1
#       def _on_command_start(self, cmd): ...
#       def _on_command_end(self): ...
#
#   class KeypadDriver(HalPollingDriver):
#       CYCLIC_INTERVAL_MS = 10
#       def _scan(self): ...
#       def _on_input(self, value): ...
# =============================================================================

import time


# #############################################################################
#
#   ██  HalDriver — Abstract Base Class for ALL Drivers
#
# #############################################################################
#
# This is the root of the driver hierarchy. Every HAL driver — whether
# it's an output device (buzzer, motor, LED) or an input device (keypad,
# button) — inherits from this class.
#
# What you get for free by inheriting:
#   • A FIFO command queue (commands are buffered, not overwritten)
#   • A state machine (IDLE → ACTIVE → IDLE)
#   • Blocking spin loop that advances ALL drivers (via scheduler)
#   • Public API: stop(), is_busy(), clear_queue()
#   • Safety timeout on blocking calls (prevents infinite hangs)
#
# What you MUST implement in your subclass:
#   • _on_command_start(cmd)  — Start the hardware for a given command
#   • _on_tick()              — Called every cyclic() while ACTIVE
#   • _on_command_end()       — Stop/cleanup hardware when command ends
#
# #############################################################################

class HalDriver:
    """
    Abstract base class for all EZ-BOTIX hardware drivers.

    Provides command queue management, state machine, and blocking
    support. Concrete drivers inherit from this (usually via
    HalTimedDriver or HalPollingDriver) and implement three methods.
    """

    # ─────────────────────────────────────────────────────────────────
    # Constants — override in subclasses as needed
    # ─────────────────────────────────────────────────────────────────

    # State machine states
    STATE_IDLE   = 0    # Driver is idle — no active command
    STATE_ACTIVE = 1    # Driver is executing a command

    # Command queue limits
    MAX_QUEUE_SIZE = 16     # Maximum number of buffered commands
                            # Override per driver (e.g., buzzer uses 32
                            # because melodies expand to many notes)

    # Scheduling
    CYCLIC_INTERVAL_MS = 10     # How often the scheduler calls cyclic()
                                # Override per driver:
                                #   Buzzer: 1ms   (precise note timing)
                                #   Motor:  5ms   (coarse timing OK)
                                #   LED:    10ms  (blink toggle)
                                #   RGB:    20ms  (~50fps animation)

    # Safety
    BLOCK_TIMEOUT_MS = 30000    # Max time (ms) a blocking call can wait
                                # before force-stopping. Prevents infinite
                                # hangs if a driver bug leaves state stuck.

    # ─────────────────────────────────────────────────────────────────
    # Constructor
    # ─────────────────────────────────────────────────────────────────

    def __init__(self):
        """
        Initialize the base driver state.

        Sets up the state machine, command queue, and scheduler
        back-reference. Called by subclass __init__ via super().__init__().
        """
        # ── State machine ─────────────────────────────────────────────
        # Tracks what the driver is currently doing.
        # IDLE = nothing happening, ACTIVE = executing a command.
        self._state = self.STATE_IDLE

        # The command currently being executed (a dict), or None if idle.
        self._current_cmd = None

        # ── Command queue (FIFO) ──────────────────────────────────────
        # A list of command dicts waiting to be executed.
        # Commands are added at the back (append) and removed from
        # the front (pop(0)), guaranteeing first-in-first-out order.
        #
        # Each command is a dict with at least an 'action' key:
        #   {'action': 'tone', 'freq': 440, 'duration_ms': 500}
        #
        # The format is driver-specific — the base class just stores
        # and dequeues them. The subclass interprets them.
        self._command_queue = []

        # ── Scheduler back-reference ──────────────────────────────────
        # Set by the scheduler when this driver is registered via
        # scheduler.register_driver(self).
        #
        # Used by _block_until_idle() to call scheduler.tick(), which
        # advances ALL registered drivers — not just this one. This is
        # what makes "background music keeps playing during a blocking
        # motor command" work.
        #
        # If None (driver not registered), blocking still works but
        # only advances this driver's own cyclic().
        self._scheduler = None

    # ═════════════════════════════════════════════════════════════════
    #  PUBLIC API — what user code and Blockly-generated code calls
    # ═════════════════════════════════════════════════════════════════

    def stop(self):
        """
        EMERGENCY STOP — immediately halt the hardware and discard
        all pending commands.

        After calling stop():
          • The hardware is turned off (via _on_command_end)
          • The command queue is emptied
          • The driver state is set to IDLE

        This is the "panic button". Use it to immediately kill
        everything the driver is doing.

        Safe to call when already idle (does nothing).
        """
        # Only shut down hardware if we were actually doing something.
        # This avoids unnecessary hardware calls when already idle.
        if self._state != self.STATE_IDLE:
            self._on_command_end()

        # Reset everything to a clean idle state
        self._state = self.STATE_IDLE
        self._current_cmd = None
        self._command_queue.clear()

    def is_busy(self):
        """
        Returns True if the driver has work to do.

        A driver is "busy" when EITHER:
          • It is actively executing a command (state != IDLE), OR
          • It has commands waiting in the queue

        This is used by:
          • scheduler.is_all_idle() — to decide when to stop run()
          • User code — to poll without blocking:
                while buzzer.is_busy():
                    # do something else in the meantime
        """
        return self._state != self.STATE_IDLE or len(self._command_queue) > 0

    def clear_queue(self):
        """
        Clear all PENDING commands, but let the current one finish.

        Use this when you want to cancel future queued work without
        interrupting what's currently playing/driving/animating.

        Example:
            buzzer.play_melody("Mario", blocking=False)
            time.sleep(1)
            buzzer.clear_queue()  # Stop after the current note finishes
        """
        self._command_queue.clear()

    # ═════════════════════════════════════════════════════════════════
    #  CYCLIC — called by the scheduler at CYCLIC_INTERVAL_MS
    # ═════════════════════════════════════════════════════════════════

    def cyclic(self):
        """
        Called by the scheduler at regular intervals (CYCLIC_INTERVAL_MS).

        This method is the heart of the driver. It drives the entire
        state machine:

          1. If IDLE and queue has commands → dequeue the next one and
             start it (transitions to ACTIVE).
          2. If ACTIVE → delegate to _on_tick() for driver-specific work.
             The subclass's _on_tick() checks if the command is done and
             calls _finish_current() when appropriate.

        CONTRACT (rules that MUST be followed):
          • MUST return quickly — no sleep, no loops, no blocking I/O.
          • MUST be safe to call when IDLE — just checks the queue.
          • MUST be safe to call multiple times per tick — idempotent.
          • MUST NOT raise exceptions (catch internally if needed).
        """
        # ── Step 1: If idle, try to start the next queued command ─────
        # When the driver is idle and commands are waiting, we dequeue
        # the oldest command and start executing it. This is the
        # IDLE → ACTIVE transition.
        if self._state == self.STATE_IDLE:
            if self._command_queue:
                self._dequeue_and_start()
            return  # Fast exit — nothing more to do this tick

        # ── Step 2: We are ACTIVE — let the subclass do its work ──────
        # The subclass's _on_tick() method handles:
        #   • Checking if the command is done (e.g., duration expired)
        #   • Advancing multi-step logic (e.g., animation frames)
        #   • Calling _finish_current() when the command completes
        self._on_tick()

    # ═════════════════════════════════════════════════════════════════
    #  INTERNAL HELPERS — used by this class and subclasses
    # ═════════════════════════════════════════════════════════════════

    def _enqueue(self, cmd, blocking=True):
        """
        Add a command to the queue. If blocking, wait until it completes.

        This is the GATEWAY for all public API methods. Every driver
        method that starts a hardware action calls _enqueue() internally.

        Example (in a buzzer driver):
            def play_tone(self, freq, duration_ms=0, blocking=True):
                cmd = {'action': 'tone', 'freq': freq, 'duration_ms': duration_ms}
                self._enqueue(cmd, blocking)

        Args:
            cmd (dict):      Command descriptor. Format is driver-specific.
                             Must contain at least an 'action' key.
            blocking (bool): If True (default), spin until this command
                             AND all commands before it in the queue
                             have completed. If False, return immediately.

        Queue-full behavior:
            If the queue has reached MAX_QUEUE_SIZE, the NEW command is
            DROPPED (not the oldest). A warning is printed. This protects
            existing queued work from being disrupted.
        """
        # ── Guard: don't exceed the queue limit ───────────────────────
        # On ESP32 with limited RAM, unbounded queues are dangerous.
        # We cap at MAX_QUEUE_SIZE and drop the new command if full.
        if len(self._command_queue) >= self.MAX_QUEUE_SIZE:
            print("WARNING: {} queue full, command dropped".format(
                self.__class__.__name__))
            return

        # ── Add the command to the back of the queue (FIFO) ───────────
        self._command_queue.append(cmd)

        # ── If blocking requested, spin until everything is done ──────
        # "Blocking" means: wait here until the queue is empty AND the
        # driver is idle. This includes all commands that were already
        # in the queue plus the one we just added.
        if blocking:
            self._block_until_idle()

    def _dequeue_and_start(self):
        """
        Remove the next command from the front of the queue and start it.

        This is the IDLE → ACTIVE transition. Called by cyclic() when
        the driver is idle and the queue has commands waiting.

        Flow:
          1. Pop the oldest command from the queue (FIFO order)
          2. Set state to ACTIVE
          3. Call _on_command_start(cmd) — subclass configures hardware
        """
        # Pop the oldest command (first in, first out)
        self._current_cmd = self._command_queue.pop(0)

        # Transition to ACTIVE state
        self._state = self.STATE_ACTIVE

        # Let the subclass start the hardware for this command.
        # For example, a buzzer would set PWM frequency and duty cycle.
        self._on_command_start(self._current_cmd)

    def _finish_current(self):
        """
        End the current command and immediately start the next one.

        Called by subclasses (from _on_tick or _on_active_tick) when
        the current command has completed its work.

        If the queue has more commands, the next one starts IMMEDIATELY
        — there is no one-tick gap between commands. This ensures
        seamless transitions (e.g., melody notes don't have audible gaps).

        If the queue is empty, the driver goes idle.
        """
        # Let the subclass clean up the hardware.
        # For example, a buzzer would set PWM duty to 0.
        self._on_command_end()

        # Clear the finished command reference
        self._current_cmd = None

        # ── Try to start the next command immediately (no gap) ────────
        # This is critical for smooth operation: if a melody has 20
        # notes queued, we don't want a 1-tick silence between each
        # note. The next note starts in the SAME cyclic() call.
        if self._command_queue:
            self._dequeue_and_start()
        else:
            # Queue is empty — return to idle
            self._state = self.STATE_IDLE

    def _block_until_idle(self):
        """
        Spin loop that waits until the queue is empty AND state is IDLE.

        This is how blocking mode works under the hood. The loop:

          1. Calls self.cyclic() every iteration — to advance THIS driver
             immediately, bypassing the scheduler's interval check.

          2. Calls scheduler.tick() every iteration — to advance ALL
             OTHER registered drivers at their configured intervals.
             This is what makes "background music keeps playing during
             a blocking motor command" work.

          3. Sleeps 1ms per iteration — to prevent CPU starvation and
             give MicroPython internals (GC, WiFi stack) time to run.

          4. Has a safety timeout — if the driver is stuck for more
             than BLOCK_TIMEOUT_MS (default 30 seconds), we force-stop
             to prevent an infinite hang. This catches driver bugs
             (e.g., state stuck in ACTIVE due to a logic error).

        WHY scheduler.tick() IS CALLED HERE:
            Without this, a blocking call on one driver would freeze
            every other driver. Consider:

                buzzer.play_melody("Mario", blocking=False)  # background
                car.forward(80, duration_ms=2000)            # blocking

            The car's blocking call spins here for 2 seconds. If we
            only called car.cyclic(), the buzzer melody would freeze.
            By calling scheduler.tick(), the buzzer's cyclic() continues
            to be called at its 1ms interval — the melody plays on.
        """
        # Calculate the absolute deadline for the safety timeout.
        # ticks_add handles rollover correctly.
        deadline = time.ticks_add(time.ticks_ms(), self.BLOCK_TIMEOUT_MS)

        # Spin until both conditions are met:
        #   1. _state is IDLE (no command currently executing)
        #   2. _command_queue is empty (no commands waiting)
        while self._state != self.STATE_IDLE or self._command_queue:

            # ── Advance THIS driver immediately ───────────────────────
            # We call our own cyclic() directly, bypassing the
            # scheduler's interval check. This ensures the blocking
            # driver responds with ~1ms latency, regardless of its
            # configured CYCLIC_INTERVAL_MS.
            self.cyclic()

            # ── Advance ALL other drivers via the scheduler ───────────
            # The scheduler's tick() checks each task's interval and
            # calls those that are due. This keeps every other driver
            # alive during our blocking wait.
            #
            # Note: The scheduler will also call OUR cyclic() again
            # if our interval has elapsed — that's fine. cyclic() is
            # designed to be safe to call multiple times (idempotent).
            if self._scheduler is not None:
                self._scheduler.tick()

            # ── Small sleep to prevent CPU starvation ─────────────────
            # Without this, the tight loop would consume 100% CPU
            # and starve MicroPython internals (GC, WiFi, etc.).
            time.sleep_ms(1)

            # ── Safety timeout check ──────────────────────────────────
            # If we've been spinning for too long, something is wrong.
            # Force-stop to prevent an infinite hang and print a warning
            # so the developer knows what happened.
            if time.ticks_diff(time.ticks_ms(), deadline) >= 0:
                print("WARNING: {} blocking timeout, forcing stop".format(
                    self.__class__.__name__))
                self.stop()
                break

    # ═════════════════════════════════════════════════════════════════
    #  ABSTRACT METHODS — subclasses MUST implement these
    # ═════════════════════════════════════════════════════════════════
    #
    # These three methods define what makes each driver unique.
    # The base class handles ALL the queue management, state machine,
    # and blocking logic. The subclass only needs to say:
    #   - HOW to start the hardware for a command
    #   - WHAT to do on each tick while active
    #   - HOW to stop the hardware when done
    #
    # ═════════════════════════════════════════════════════════════════

    def _on_command_start(self, cmd):
        """
        Called when a new command is dequeued and the driver becomes ACTIVE.

        The subclass MUST override this to:
          • Read the command dict and configure the hardware accordingly
          • Set any driver-specific state needed for the command

        Args:
            cmd (dict): The command to execute. Format is driver-specific.
                        Always has an 'action' key.

        Example (buzzer):
            def _on_command_start(self, cmd):
                if cmd['action'] == 'tone':
                    self.pwm.freq(cmd['freq'])
                    self.pwm.duty(512)
                    self._duration_ms = cmd['duration_ms']
                elif cmd['action'] == 'silence':
                    self.pwm.duty(0)
                    self._duration_ms = cmd['duration_ms']
        """
        raise NotImplementedError(
            "{} must implement _on_command_start()".format(
                self.__class__.__name__))

    def _on_tick(self):
        """
        Called every cyclic() while the driver is ACTIVE.

        The subclass MUST override this to:
          • Check if the current command is done
          • Call self._finish_current() when the command completes
          • Advance any multi-step logic (animation frames, etc.)

        CONTRACT:
          • MUST be fast (no sleep, no loops, no blocking I/O)
          • MUST call self._finish_current() when the command is done
          • MUST NOT modify _state directly — use _finish_current()

        Note: HalTimedDriver overrides this with automatic duration
        checking, so timed drivers override _on_active_tick() instead.
        """
        raise NotImplementedError(
            "{} must implement _on_tick()".format(
                self.__class__.__name__))

    def _on_command_end(self):
        """
        Called when a command finishes (by duration, or by stop()).

        The subclass MUST override this to:
          • Turn off the hardware (silence buzzer, stop motors, etc.)
          • Clean up any driver-specific state

        CONTRACT:
          • MUST be idempotent — safe to call even if hardware is
            already off. This can happen if stop() is called when
            the driver is already idle.
          • MUST NOT modify _state or _command_queue — the caller
            (stop() or _finish_current()) handles that.

        Example (buzzer):
            def _on_command_end(self):
                self.pwm.duty(0)  # Silence — safe even if already silent
        """
        raise NotImplementedError(
            "{} must implement _on_command_end()".format(
                self.__class__.__name__))


# #############################################################################
#
#   ██  HalTimedDriver — Base for Output Drivers with Duration
#
# #############################################################################
#
# Extends HalDriver with automatic elapsed-time checking.
#
# HOW IT WORKS:
#   The subclass sets self._duration_ms in _on_command_start().
#   This class's _on_tick() automatically checks if the elapsed time
#   has reached the duration. If so, it calls _finish_current() — the
#   subclass doesn't need to implement any timing logic.
#
# WHAT SUBCLASSES IMPLEMENT:
#   • _on_command_start(cmd) — Configure hardware + set self._duration_ms
#   • _on_command_end()      — Turn off hardware (idempotent)
#   • _on_active_tick()      — (OPTIONAL) Per-tick work while active
#                               Default: do nothing (fine for simple tones)
#
# WHAT SUBCLASSES DO NOT IMPLEMENT:
#   • _on_tick() — handled here (checks duration, delegates to _on_active_tick)
#
# EXAMPLES OF TIMED DRIVERS:
#   • BuzzerDriver  — plays a tone for N ms
#   • RobotDrive    — drives forward for N ms
#   • LEDController — blinks for N ms
#   • RGBStripDriver — runs an effect for N ms
#
# #############################################################################

class HalTimedDriver(HalDriver):
    """
    Base class for output drivers with duration-based commands.

    Adds automatic elapsed-time tracking. The subclass sets _duration_ms
    in _on_command_start(), and this class auto-stops the command when
    the duration expires. No manual timing code needed in subclasses.
    """

    def __init__(self):
        # Initialize the parent class (queue, state machine, etc.)
        super().__init__()

        # ── Timing state ──────────────────────────────────────────────
        # These are managed by this class. The subclass sets _duration_ms
        # in _on_command_start(); everything else is automatic.

        # When the current command started (ticks_ms timestamp).
        # Set automatically in _dequeue_and_start().
        self._start_ms = 0

        # How long the current command should run, in milliseconds.
        # Set by the subclass in _on_command_start().
        #   0  = run indefinitely until stop() is called
        #   >0 = auto-stop after this many milliseconds
        self._duration_ms = 0

    def _dequeue_and_start(self):
        """
        Start a command and record when it began.

        Overrides the parent to add timestamp recording. The start
        time is captured BEFORE _on_command_start() is called, so
        the subclass can rely on _start_ms being set when it runs.
        """
        # Record the start time BEFORE calling the parent.
        # The parent's _dequeue_and_start() calls _on_command_start(),
        # where the subclass may need to reference _start_ms.
        self._start_ms = time.ticks_ms()

        # Reset duration — the subclass sets it in _on_command_start()
        self._duration_ms = 0

        # Call the parent: dequeue command, set ACTIVE, call _on_command_start
        super()._dequeue_and_start()

    def _on_tick(self):
        """
        Automatic timing check for timed commands.

        This method is called by the base class's cyclic() every tick
        while the driver is ACTIVE. It does two things:

          1. If _duration_ms > 0 and enough time has elapsed → finish
             the command (calls _finish_current, which may start the
             next queued command immediately).

          2. Otherwise, delegate to _on_active_tick() for any
             driver-specific per-tick work (e.g., advancing an
             animation frame or toggling a blink state).

        Subclasses should override _on_active_tick(), NOT this method.
        """
        # ── Check if the timed command has expired ────────────────────
        # Only check if _duration_ms > 0. A duration of 0 means
        # "run indefinitely until stop() is called".
        if self._duration_ms > 0:
            # Use ticks_diff for safe rollover handling.
            # Raw subtraction (now - start) breaks when ticks_ms wraps
            # at 2^30 ms (~12.4 days).
            elapsed = time.ticks_diff(time.ticks_ms(), self._start_ms)

            if elapsed >= self._duration_ms:
                # Time's up! Finish this command.
                # _finish_current() calls _on_command_end() to stop the
                # hardware, then immediately starts the next queued
                # command (if any) — no gap.
                self._finish_current()
                return

        # ── Driver-specific per-tick work ─────────────────────────────
        # If we reach here, the command is still running (either the
        # duration hasn't expired, or it runs indefinitely).
        # Delegate to the subclass for any per-tick updates.
        self._on_active_tick()

    def _on_active_tick(self):
        """
        Called every cyclic() while the driver is ACTIVE and the
        duration has not yet expired.

        Override this in your subclass for per-tick hardware updates:
          • Advancing animation frames (RGB effects)
          • Toggling blink state (LED)
          • Any periodic hardware update while a command runs

        Default implementation: do nothing. This is sufficient for
        simple timed commands that just need to "wait until done"
        (e.g., a single tone or a timed motor drive).

        CONTRACT:
          • MUST be fast (no sleep, no loops, no blocking I/O)
          • Called at CYCLIC_INTERVAL_MS rate while active
        """
        # Default: no per-tick work needed.
        # Simple timed commands (tone, timed drive) just start the
        # hardware and let the automatic duration check stop it.
        pass


# #############################################################################
#
#   ██  HalPollingDriver — Base for Input Drivers with Periodic Scanning
#
# #############################################################################
#
# Extends HalDriver for input devices that need periodic scanning.
#
# HOW IT WORKS:
#   This class completely overrides cyclic() with a polling state machine.
#   It does NOT use the command queue — polling drivers are "always on",
#   continuously scanning for input.
#
#   The state machine has two states:
#     SCANNING   — Actively reading the hardware. If new input detected,
#                   transition to DEBOUNCING.
#     DEBOUNCING — A raw input was detected. Wait 20ms (via timestamps,
#                   NOT sleep), then re-scan to confirm. If confirmed,
#                   fire the callback. Either way, back to SCANNING.
#
# WHY TIMESTAMP-BASED DEBOUNCE?
#   Physical switches "bounce" — they make and break contact several times
#   in ~10-20ms before settling. If we read every 10ms without debouncing,
#   one press might register as 2-3 presses.
#
#   The old code used time.sleep_ms(20) for debounce, which blocks the
#   entire scheduler for 20ms — freezing every other driver. Our approach
#   uses timestamps: start a 20ms timer, return immediately, and check
#   on the next cyclic() call whether 20ms has passed. Zero blocking.
#
# WHAT SUBCLASSES IMPLEMENT:
#   • _scan()            — Read the hardware, return a value or None
#   • _on_input(value)   — Called when input is confirmed (optional)
#
# EXAMPLES:
#   • KeypadDriver    — scans 4x4 matrix, returns key character
#   • ButtonDriver    — reads GPIO, returns True when pressed
#   • IRSensorDriver  — reads GPIO, returns True when obstacle detected
#
# #############################################################################

class HalPollingDriver(HalDriver):
    """
    Base class for input drivers with periodic scanning and debouncing.

    Continuously scans the hardware at CYCLIC_INTERVAL_MS intervals.
    Uses timestamp-based debouncing to filter out switch bounce.
    Fires a user callback when a debounced input is confirmed.
    """

    # ── Polling-specific states ───────────────────────────────────────
    # These extend (not replace) the base STATE_IDLE / STATE_ACTIVE.
    # Polling drivers use their own state values to avoid confusion.
    STATE_SCANNING   = 10   # Actively scanning for input
    STATE_DEBOUNCING = 11   # Raw input detected, waiting to confirm

    # ── Debounce timing ───────────────────────────────────────────────
    # How long to wait (ms) after detecting a raw input before
    # re-scanning to confirm. 20ms is sufficient for most mechanical
    # switches and membrane keypads.
    DEBOUNCE_MS = 20

    def __init__(self):
        """
        Initialize the polling driver.

        Sets up the scanning state machine and callback storage.
        The driver starts in SCANNING state (not IDLE) because
        polling drivers are always active.
        """
        # Initialize the parent (we still need _scheduler, etc.)
        super().__init__()

        # ── Override the initial state ────────────────────────────────
        # Polling drivers are always scanning — they don't start idle.
        # This is different from timed drivers which start idle and
        # wait for commands.
        self._state = self.STATE_SCANNING

        # ── Debounce state ────────────────────────────────────────────
        # The value that was detected and is being debounced.
        # Set when transitioning from SCANNING → DEBOUNCING.
        self._pending_value = None

        # When the debounce period started (ticks_ms timestamp).
        self._debounce_start_ms = 0

        # ── Edge detection ────────────────────────────────────────────
        # The last value that was confirmed (passed debounce).
        # Used for edge detection: we only fire the callback when
        # a NEW input is detected, not when the same input is held.
        #
        # This prevents a held button from firing the callback
        # on every scan cycle — it fires once on the press edge.
        self._last_confirmed = None

        # ── User callback ─────────────────────────────────────────────
        # Optional function called when a debounced input is confirmed.
        # Set via on_input(callback). Takes one argument: the value.
        self._callback = None

    # ═════════════════════════════════════════════════════════════════
    #  PUBLIC API
    # ═════════════════════════════════════════════════════════════════

    def on_input(self, callback):
        """
        Register a callback that fires when a debounced input is detected.

        The callback receives one argument: the confirmed input value.
        For a keypad, this is a character ('A', '1', '#', etc.).
        For a button, this is True (pressed).
        For an IR sensor, this is True (obstacle detected).

        Only one callback can be registered at a time. Calling this
        again replaces the previous callback.

        The callback is wrapped in try/except — if it throws an
        exception, the error is printed but the driver keeps running.

        Args:
            callback (function): A function that takes one argument.

        Example:
            keypad.on_input(lambda key: print("Pressed:", key))
            button.on_input(lambda pressed: buzzer.play_tone(440, 100))
        """
        self._callback = callback

    def is_busy(self):
        """
        Polling drivers are always "not busy" for scheduler purposes.

        Unlike timed drivers, polling drivers don't have a concept of
        "work to finish". They scan continuously. Returning False here
        ensures that scheduler.run() doesn't wait for polling drivers
        to "finish" — it only waits for timed drivers (buzzer, motor, etc.).
        """
        return False

    # ═════════════════════════════════════════════════════════════════
    #  CYCLIC — completely overrides the base class cyclic()
    # ═════════════════════════════════════════════════════════════════

    def cyclic(self):
        """
        Polling state machine — scans hardware and debounces input.

        This REPLACES the base HalDriver's cyclic() entirely.
        The command queue is NOT used by polling drivers.

        State flow:
          SCANNING ──(new raw input detected)──► DEBOUNCING
          DEBOUNCING ──(20ms elapsed + re-scan confirms)──► fire callback
          DEBOUNCING ──(20ms elapsed + re-scan differs)──► back to SCANNING

        Called by the scheduler at CYCLIC_INTERVAL_MS intervals (e.g., 10ms).
        Returns quickly — no blocking, no sleep.
        """
        if self._state == self.STATE_SCANNING:
            # ══════════════════════════════════════════════════════════
            #  SCANNING STATE — read the hardware
            # ══════════════════════════════════════════════════════════
            # Call the subclass's _scan() to read the hardware.
            # Returns a value (key character, True, etc.) or None.
            raw = self._scan()

            if raw is not None and raw != self._last_confirmed:
                # ── New input detected! ───────────────────────────────
                # This is a DIFFERENT value from what was last confirmed.
                # Start the debounce timer to verify it's a real press
                # and not switch bounce.
                self._pending_value = raw
                self._debounce_start_ms = time.ticks_ms()
                self._state = self.STATE_DEBOUNCING

            elif raw is None:
                # ── Input released ────────────────────────────────────
                # The hardware is no longer reporting any input.
                # Reset edge detection so the SAME input can be
                # detected again on the next press.
                #
                # Without this, pressing 'A', releasing, then pressing
                # 'A' again would NOT fire the callback the second time
                # (because _last_confirmed would still be 'A').
                self._last_confirmed = None

        elif self._state == self.STATE_DEBOUNCING:
            # ══════════════════════════════════════════════════════════
            #  DEBOUNCING STATE — wait for confirmation
            # ══════════════════════════════════════════════════════════
            # We detected a raw input in the previous scan. Now we
            # wait for DEBOUNCE_MS (20ms) to let the switch settle,
            # then re-scan to see if it's still the same value.
            elapsed = time.ticks_diff(
                time.ticks_ms(), self._debounce_start_ms)

            if elapsed >= self.DEBOUNCE_MS:
                # ── Debounce period elapsed — re-scan to confirm ──────
                confirmed = self._scan()

                if confirmed == self._pending_value:
                    # ── CONFIRMED! This is a real input. ──────────────
                    # The same value was read before AND after the
                    # debounce window. This is a genuine press.

                    # Record for edge detection (prevents re-fire while held)
                    self._last_confirmed = confirmed

                    # Notify the subclass (for driver-specific handling)
                    self._on_input(confirmed)

                    # Fire the user's callback (if registered)
                    if self._callback is not None:
                        try:
                            self._callback(confirmed)
                        except Exception as e:
                            print("Input callback error:", e)

                # else: Value changed during debounce window — it was
                # just switch bounce, not a real press. Ignore it.

                # ── Back to scanning (either way) ─────────────────────
                self._pending_value = None
                self._state = self.STATE_SCANNING

    # ═════════════════════════════════════════════════════════════════
    #  ABSTRACT METHODS — subclasses MUST implement these
    # ═════════════════════════════════════════════════════════════════

    def _scan(self):
        """
        Perform one hardware scan. Return the detected value, or None.

        This is called by cyclic() on every tick while in SCANNING state,
        and once more during DEBOUNCING to confirm.

        Returns:
            A value representing the detected input (key character,
            True for pressed, etc.), or None if no input is detected.

        CONTRACT:
          • MUST be fast (just read a pin or scan a matrix)
          • MUST return None when no input is present
          • Return value is compared with == for debounce confirmation

        Example (button):
            def _scan(self):
                return True if self._pin.value() == 0 else None

        Example (keypad):
            def _scan(self):
                # Scan 4x4 matrix, return key character or None
                for r in range(4):
                    self.rows[r].value(1)
                    for c in range(4):
                        if self.cols[c].value():
                            self.rows[r].value(0)
                            return self.layout[r][c]
                    self.rows[r].value(0)
                return None
        """
        raise NotImplementedError(
            "{} must implement _scan()".format(
                self.__class__.__name__))

    def _on_input(self, value):
        """
        Called when a debounced input is confirmed.

        Override this for driver-specific handling. For example, a
        keypad driver might store the key for read_key() to return.

        The default implementation does nothing — the user callback
        (registered via on_input()) is already fired by cyclic().
        Override this only if the driver itself needs to react.

        Args:
            value: The confirmed input value (same as _scan() returned).
        """
        # Default: no driver-specific handling needed.
        # The user callback is handled by cyclic() above.
        pass

    # ═════════════════════════════════════════════════════════════════
    #  UNUSED BASE CLASS METHODS
    # ═════════════════════════════════════════════════════════════════
    # Polling drivers don't use the command queue, so these base class
    # abstract methods are stubbed out. They're never called because
    # cyclic() is completely overridden.
    # ═════════════════════════════════════════════════════════════════

    def _on_command_start(self, cmd):
        """Not used by polling drivers — command queue is not used."""
        pass

    def _on_tick(self):
        """Not used by polling drivers — cyclic() is fully overridden."""
        pass

    def _on_command_end(self):
        """Not used by polling drivers — always scanning, never stops."""
        pass
