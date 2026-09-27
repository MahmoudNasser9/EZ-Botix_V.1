# EZ-BOTIX Firmware — HAL Driver Architecture (V2)

> **Version:** 2.0  
> **Date:** 2026-09-02  
> **Target:** ESP32 + MicroPython  

---

## 1. Design Philosophy

Three core principles govern every driver in the EZ-BOTIX firmware:

### Principle 1 — Dual-Mode API (Blocking + Non-Blocking)

Every timed command offers both **blocking** and **non-blocking** modes.
The caller chooses. Blocking mode reuses the non-blocking path internally —
there is never any code duplication.

### Principle 2 — Command Queue (FIFO Buffer)

Every driver maintains a **command queue**. When user code issues multiple
commands, they are **buffered** and executed **one by one in order** — never
overwritten.

```
  buzzer.play_tone(440, 500, blocking=False)   ──► Queue: [ tone(440) ]
  buzzer.play_tone(880, 300, blocking=False)   ──► Queue: [ tone(440), tone(880) ]

  Scheduler ticks...
    ├── cyclic: starts tone(440), plays for 500ms
    ├── cyclic: tone(440) done, starts tone(880), plays for 300ms
    └── cyclic: tone(880) done, queue empty, driver IDLE
```

### Principle 3 — Interval-Based Cyclic Scheduling

Every driver's `cyclic()` is called by the scheduler at a **driver-specific
interval** — exactly like a user task. There is no special "driver list" — 
drivers ARE tasks.

```
  ┌─────────────────────────────────────────────────────────┐
  │                    TaskScheduler                         │
  │                                                         │
  │   Task List (ordered by next_run_ms):                   │
  │                                                         │
  │   ┌──────────────────┬──────────┬─────────────────────┐ │
  │   │ Name             │ Interval │ Callback            │ │
  │   ├──────────────────┼──────────┼─────────────────────┤ │
  │   │ BuzzerDriver     │   1 ms   │ buzzer.cyclic()     │ │
  │   │ RobotDrive       │   5 ms   │ car.cyclic()        │ │
  │   │ LEDController    │  10 ms   │ led.cyclic()        │ │
  │   │ KeypadDriver     │  10 ms   │ keypad.cyclic()     │ │
  │   │ RGBStripDriver   │  20 ms   │ rgb_front.cyclic()  │ │
  │   │ RGBStripDriver   │  20 ms   │ rgb_back.cyclic()   │ │
  │   │ (user task)      │ 200 ms   │ check_obstacle()    │ │
  │   └──────────────────┴──────────┴─────────────────────┘ │
  │                                                         │
  │   tick()  ──► check each task's interval, call if due   │
  └─────────────────────────────────────────────────────────┘
```

This means:
- **Blockly beginners** can write simple sequential code that "just works" (blocking mode).
- **Advanced programs** can run multiple things concurrently (non-blocking + scheduler).
- **No code duplication** — blocking simply enqueues the command, then spins on `cyclic()` until the queue drains.
- **No command loss** — commands are buffered, not overwritten.

---

## 2. Class Hierarchy

Every driver fits into a clear, three-level inheritance tree.
Concrete drivers only need to implement 3 small methods.

```
                          ┌──────────────────────┐
                          │     HalDriver        │  ◄── Abstract base
                          │     (hal_base.py)     │      for ALL drivers
                          │                       │
                          │  • Command queue      │
                          │  • State machine      │
                          │  • Blocking spin loop │
                          │  • is_busy() / stop() │
                          └──────────┬────────────┘
                                     │
                  ┌──────────────────┼──────────────────┐
                  │                                     │
         ┌────────▼─────────┐              ┌────────────▼────────────┐
         │  HalTimedDriver  │              │   HalPollingDriver     │
         │  (hal_base.py)   │              │   (hal_base.py)        │
         │                  │              │                         │
         │  + Elapsed time  │              │  + Periodic scanning   │
         │  + Auto-stop     │              │  + Debounce state      │
         │  + Duration mgmt │              │  + Callback dispatch   │
         └────────┬─────────┘              └────────────┬────────────┘
                  │                                     │
      ┌───────────┼───────────┬─────────────┐     ┌─────┼──────┬──────────┐
      │           │           │             │     │            │          │
 BuzzerDriver  RobotDrive  LEDController  RGBStrip│  KeypadDriver  ButtonDriver  IRSensorDriver
 (hal_buzzer)  (hal_motor) (hal_LED)      (hal_RGB)  (hal_keypad)  (hal_button)  (hal_ir)


  PURE-READ DRIVER (no inheritance — instant hardware read):

    Ultrasonic
    (hal_ultrasonic)
```

### Why This Hierarchy?

| Layer | Responsibility | What it saves you |
|-------|---------------|-------------------|
| `HalDriver` | Queue, state machine, blocking, stop | Every driver gets these for free |
| `HalTimedDriver` | Elapsed time check, auto-stop on duration | Output drivers never re-implement timing |
| `HalPollingDriver` | Scan cycle, debounce tracking | Input drivers never re-implement debounce |
| Concrete driver | Only: start hardware, tick logic, stop hardware | 3 small methods to write |

---

## 3. State Machine

Every driver follows this universal state model:

```
                                     enqueue(cmd)
    ┌──────────┐    (queue not empty)     ┌──────────┐
    │          │ ────────────────────────► │          │
    │   IDLE   │                          │  ACTIVE  │
    │          │ ◄──────────────────────── │          │
    └──────────┘   duration expired        └──────────┘
                   OR stop() called              │
                                                 │  (for multi-step commands
                                                 │   like melodies or effects)
                                                 ▼
                                           ┌──────────┐
                                           │  STEP N  │──► N+1 ──► ... ──► IDLE
                                           └──────────┘
```

### State Transitions

| From | To | Trigger | Action |
|------|----|---------|--------|
| IDLE | ACTIVE | `cyclic()` dequeues a command | `_on_command_start()` → hardware ON |
| ACTIVE | IDLE | Duration expired in `cyclic()` | `_on_command_end()` → hardware OFF |
| ACTIVE | IDLE | `stop()` called by user | Hardware OFF + queue cleared |
| ACTIVE | STEP N | Multi-step command (e.g. melody) | Driver-specific step logic |
| IDLE (with queue) | ACTIVE | `cyclic()` finds next command | Immediate transition, no gap |

### Core State Variables (inherited from HalDriver)

| Variable | Type | Purpose |
|----------|------|---------|
| `_state` | int | Current state (`STATE_IDLE`, `STATE_ACTIVE`, etc.) |
| `_command_queue` | list | FIFO buffer of pending commands (dicts) |
| `_current_cmd` | dict | The command currently being executed |
| `_scheduler` | ref | Back-reference to the scheduler (set on registration) |

### Additional Variables (added by HalTimedDriver)

| Variable | Type | Purpose |
|----------|------|---------|
| `_start_ms` | int | `time.ticks_ms()` when the current command started |
| `_duration_ms` | int | How long the current command runs (0 = until `stop()`) |

---

## 4. Command Queue System

### 4.1 What Is a Command?

A command is a **dictionary** describing one unit of work for the driver.
Each driver defines its own command format — the base class just stores
and dequeues them.

```python
# ── Buzzer commands ──────────────────────────────────────────────────
{'action': 'tone',    'freq': 440, 'duration_ms': 500}
{'action': 'silence', 'duration_ms': 100}          # Pause between notes
{'action': 'melody',  'name': 'Mario'}              # Expands to many cmds

# ── Motor commands ───────────────────────────────────────────────────
{'action': 'drive',   'left': 80, 'right': 80, 'duration_ms': 2000}
{'action': 'stop'}

# ── LED commands ─────────────────────────────────────────────────────
{'action': 'on',      'duration_ms': 5000}
{'action': 'blink',   'interval_ms': 500, 'duration_ms': 3000}

# ── RGB commands ─────────────────────────────────────────────────────
{'action': 'color',   'r': 255, 'g': 0, 'b': 0, 'duration_ms': 1000}
{'action': 'effect',  'name': 'rainbow', 'duration_ms': 5000}
```

### 4.2 Queue Rules

```
  MAX_QUEUE_SIZE = 16 (configurable per driver class)

  ┌─────────────────────────────────────────────────────────────────┐
  │                        COMMAND QUEUE                            │
  │                                                                 │
  │  enqueue(cmd)                                                   │
  │  ┌───────┐                                                      │
  │  │       │    ┌─────┐  ┌─────┐  ┌─────┐  ┌─────┐              │
  │  │  NEW  │───►│ cmd │  │ cmd │  │ cmd │  │ cmd │──► dequeue    │
  │  │  CMD  │    │  4  │  │  3  │  │  2  │  │  1  │    (FIFO)    │
  │  │       │    └─────┘  └─────┘  └─────┘  └─────┘              │
  │  └───────┘                                                      │
  │                                                                 │
  │  Rules:                                                         │
  │  1. Commands added at the BACK (append)                         │
  │  2. Commands removed from the FRONT (pop(0))                    │
  │  3. If queue is full, the NEW command is DROPPED (not oldest)   │
  │  4. stop() clears the ENTIRE queue + stops current command      │
  │  5. clear_queue() clears pending commands only (current runs)   │
  └─────────────────────────────────────────────────────────────────┘
```

### 4.3 Queue + Blocking Interaction

```
  ┌──────────────────────────────────────────────────────────────────┐
  │                    enqueue(cmd, blocking)                        │
  │                                                                  │
  │  blocking=False                  │  blocking=True (default)      │
  │  ──────────────                  │  ────────────────────────      │
  │  1. Add cmd to queue             │  1. Add cmd to queue          │
  │  2. Return immediately           │  2. Spin on _block_until_idle │
  │                                  │     ├── calls self.cyclic()   │
  │  cyclic() processes              │     ├── calls scheduler.tick()│
  │  commands automatically          │     │   (advances ALL drivers)│
  │  via the scheduler.              │     └── exits when queue      │
  │                                  │         is empty + state IDLE │
  └──────────────────────────────────────────────────────────────────┘
```

> **Key insight:** The blocking spin loop calls `scheduler.tick()`, which
> advances **every** registered driver — not just `self`. This means
> background operations (like a melody) continue to play even while
> another driver is in a blocking call.

---

## 5. Base Class — `HalDriver` (hal_base.py)

This is the foundation for ALL drivers. Every line is commented.

```python
# =============================================================================
# hal_base.py — Base classes for the EZ-BOTIX HAL driver framework
# =============================================================================
#
# This module defines the inheritance hierarchy that all hardware drivers
# build upon. Three classes are provided:
#
#   HalDriver        — Abstract base for ALL drivers
#   HalTimedDriver   — For output drivers with duration-based commands
#   HalPollingDriver — For input drivers with periodic scanning
#
# No driver should ever be written from scratch. Always inherit from one
# of these base classes.
# =============================================================================

import time


# =============================================================================
# ██  HalDriver — Abstract Base Class
# =============================================================================
#
# Provides:
#   • Command queue (FIFO buffer)
#   • State machine (IDLE / ACTIVE)
#   • Blocking spin loop (_block_until_idle)
#   • Public API: stop(), is_busy(), clear_queue()
#
# Subclasses MUST implement:
#   • _on_command_start(cmd)  — Start the hardware for this command
#   • _on_tick()              — Called every cyclic while ACTIVE
#   • _on_command_end()       — Stop/cleanup hardware when command ends
# =============================================================================

class HalDriver:
    """Abstract base class for all EZ-BOTIX hardware drivers."""

    # ── Constants ─────────────────────────────────────────────────────
    STATE_IDLE   = 0   # Driver is idle, no active command
    STATE_ACTIVE = 1   # Driver is executing a command

    MAX_QUEUE_SIZE   = 16      # Max buffered commands (override per driver)
    CYCLIC_INTERVAL_MS = 10    # How often cyclic() is called (override per driver)
    BLOCK_TIMEOUT_MS = 30000   # Safety timeout for blocking calls (30 seconds)

    # ── Constructor ───────────────────────────────────────────────────
    def __init__(self):
        # --- State machine ---
        self._state = self.STATE_IDLE       # Current driver state
        self._current_cmd = None            # The command being executed right now

        # --- Command queue (FIFO) ---
        # Commands are added at the back (append) and removed from
        # the front (pop(0)). This guarantees first-in-first-out order.
        self._command_queue = []

        # --- Scheduler back-reference ---
        # Set by the scheduler when this driver is registered.
        # Used by _block_until_idle() to advance ALL drivers during
        # a blocking wait — not just this one.
        self._scheduler = None

    # ═════════════════════════════════════════════════════════════════
    #  PUBLIC API — what user code and subclasses call
    # ═════════════════════════════════════════════════════════════════

    def stop(self):
        """
        EMERGENCY STOP — immediately halt the hardware and discard
        all pending commands.

        This is the "panic button". After calling stop():
          • The hardware is turned off (_on_command_end)
          • The command queue is emptied
          • The driver state is IDLE
        """
        # Only call hardware shutdown if we were actually doing something
        if self._state != self.STATE_IDLE:
            self._on_command_end()

        # Reset everything
        self._state = self.STATE_IDLE
        self._current_cmd = None
        self._command_queue.clear()

    def is_busy(self):
        """
        Returns True if the driver is currently executing a command
        OR has commands waiting in the queue.

        Useful for user code to check without blocking:
            while buzzer.is_busy():
                # do something else
        """
        return self._state != self.STATE_IDLE or len(self._command_queue) > 0

    def clear_queue(self):
        """
        Clear all PENDING commands, but let the current command finish.

        Use this when you want to cancel future work without
        interrupting what's currently playing/running.
        """
        self._command_queue.clear()

    # ═════════════════════════════════════════════════════════════════
    #  CYCLIC — called by the scheduler at CYCLIC_INTERVAL_MS
    # ═════════════════════════════════════════════════════════════════

    def cyclic(self):
        """
        Called by the scheduler at regular intervals (CYCLIC_INTERVAL_MS).

        This method drives the entire state machine:
          1. If IDLE and queue has commands → dequeue and start
          2. If ACTIVE → delegate to _on_tick() for driver-specific work
          3. _on_tick() decides when to finish (calls _finish_current())

        Rules for this method:
          • MUST return quickly (no sleep, no loops, no blocking I/O)
          • MUST be safe to call when IDLE (just checks queue)
          • MUST be safe to call multiple times per tick (idempotent)
        """
        # ── Step 1: If idle, try to start the next queued command ─────
        if self._state == self.STATE_IDLE:
            if self._command_queue:
                self._dequeue_and_start()
            return  # Fast exit — nothing more to do

        # ── Step 2: We are ACTIVE — let the subclass do its work ──────
        self._on_tick()

    # ═════════════════════════════════════════════════════════════════
    #  INTERNAL HELPERS — used by the base class and subclasses
    # ═════════════════════════════════════════════════════════════════

    def _enqueue(self, cmd, blocking=True):
        """
        Add a command to the queue. If blocking, wait until done.

        This is the gateway for ALL public API methods. Every driver
        method that starts a hardware action calls _enqueue() internally:

            def play_tone(self, freq, duration_ms=0, blocking=True):
                cmd = {'action': 'tone', 'freq': freq, 'duration_ms': duration_ms}
                self._enqueue(cmd, blocking)

        Args:
            cmd (dict):   Command descriptor (driver-specific format).
            blocking (bool): If True, spin until this command AND all
                             commands before it in the queue are done.
        """
        # Guard: don't exceed the queue limit
        if len(self._command_queue) >= self.MAX_QUEUE_SIZE:
            # Queue full — drop the NEW command (don't disrupt existing work)
            print("WARNING: {} queue full, command dropped".format(
                self.__class__.__name__))
            return

        # Add the command to the back of the queue
        self._command_queue.append(cmd)

        # If blocking, spin until the entire queue drains to IDLE
        if blocking:
            self._block_until_idle()

    def _dequeue_and_start(self):
        """
        Remove the next command from the front of the queue and start it.

        Called by cyclic() when the driver is IDLE and the queue is
        not empty. This is the transition from IDLE → ACTIVE.
        """
        # Pop the oldest command (FIFO — first in, first out)
        self._current_cmd = self._command_queue.pop(0)

        # Transition to ACTIVE state
        self._state = self.STATE_ACTIVE

        # Let the subclass start the hardware for this command
        self._on_command_start(self._current_cmd)

    def _finish_current(self):
        """
        End the current command and check for the next one.

        Called by subclasses (via _on_tick) when a command is done.
        If the queue has more commands, the next one starts immediately
        — there is no one-tick gap between commands.
        """
        # Let the subclass clean up the hardware
        self._on_command_end()

        # Clear the finished command
        self._current_cmd = None

        # Try to start the next command immediately (no gap)
        if self._command_queue:
            self._dequeue_and_start()
        else:
            # Queue is empty — go idle
            self._state = self.STATE_IDLE

    def _block_until_idle(self):
        """
        Spin loop that waits until the queue is empty AND state is IDLE.

        This is how blocking mode works. It:
          1. Calls self.cyclic() every iteration (for this driver)
          2. Calls scheduler.tick() every iteration (for ALL other drivers)
          3. Has a safety timeout to prevent infinite hangs

        IMPORTANT: Because we call scheduler.tick(), ALL registered
        drivers continue to advance during a blocking wait. This means
        background music keeps playing while a blocking motor command
        is running — everything stays alive.
        """
        # Calculate the absolute deadline for the safety timeout
        deadline = time.ticks_add(time.ticks_ms(), self.BLOCK_TIMEOUT_MS)

        while self._state != self.STATE_IDLE or self._command_queue:
            # ── Advance this driver immediately (bypass interval check) ──
            self.cyclic()

            # ── Advance ALL other drivers via the scheduler ──────────────
            if self._scheduler is not None:
                self._scheduler.tick()

            # ── Small sleep to prevent CPU starvation ────────────────────
            time.sleep_ms(1)

            # ── Safety timeout: force-stop if stuck too long ─────────────
            if time.ticks_diff(time.ticks_ms(), deadline) >= 0:
                print("WARNING: {} blocking timeout, forcing stop".format(
                    self.__class__.__name__))
                self.stop()
                break

    # ═════════════════════════════════════════════════════════════════
    #  ABSTRACT METHODS — subclasses MUST implement these
    # ═════════════════════════════════════════════════════════════════

    def _on_command_start(self, cmd):
        """
        Called when a new command is dequeued and the driver becomes ACTIVE.

        Subclass MUST override this to:
          • Read the command dict and configure the hardware
          • Set any driver-specific state (e.g., _duration_ms)

        Args:
            cmd (dict): The command to execute.

        Example (buzzer):
            def _on_command_start(self, cmd):
                if cmd['action'] == 'tone':
                    self.pwm.freq(cmd['freq'])
                    self.pwm.duty(512)
                    self._duration_ms = cmd['duration_ms']
        """
        raise NotImplementedError

    def _on_tick(self):
        """
        Called every cyclic() while the driver is ACTIVE.

        Subclass MUST override this to:
          • Check if the current command is done → call _finish_current()
          • Advance multi-step logic (e.g., next frame of animation)
          • Do any per-tick hardware updates

        Rules:
          • MUST be fast (no sleep, no loops)
          • MUST call self._finish_current() when the command is done
        """
        raise NotImplementedError

    def _on_command_end(self):
        """
        Called when a command finishes (either by duration or by stop()).

        Subclass MUST override this to:
          • Turn off the hardware (silence buzzer, stop motors, etc.)
          • Clean up any driver-specific state

        This method MUST be safe to call even if the hardware is
        already off (idempotent).
        """
        raise NotImplementedError


# =============================================================================
# ██  HalTimedDriver — Base for Output Drivers with Duration
# =============================================================================
#
# Extends HalDriver with automatic elapsed-time checking.
# The subclass sets _duration_ms in _on_command_start(), and this class
# handles the "is it done yet?" check automatically in _on_tick().
#
# Subclasses MUST implement:
#   • _on_command_start(cmd)  — Configure hardware + set _duration_ms
#   • _on_command_end()       — Turn off hardware
#   • _on_active_tick()       — (OPTIONAL) Per-tick work while active
#
# Subclasses do NOT need to implement _on_tick() — it's handled here.
# =============================================================================

class HalTimedDriver(HalDriver):
    """Base class for output drivers with duration-based commands."""

    def __init__(self):
        # Initialize the parent (queue, state machine, etc.)
        super().__init__()

        # ── Timing state (managed by this class) ─────────────────────
        self._start_ms = 0       # ticks_ms() when the current command started
        self._duration_ms = 0    # How long to run (0 = indefinitely until stop())

    # ── Override _dequeue_and_start to record the start timestamp ─────
    def _dequeue_and_start(self):
        """Start a command and record when it began."""
        # Record the start time BEFORE calling the parent (which calls
        # _on_command_start, where the subclass reads this timestamp).
        self._start_ms = time.ticks_ms()
        self._duration_ms = 0  # Reset — subclass sets this in _on_command_start

        # Call the parent to dequeue, set ACTIVE state, and call _on_command_start
        super()._dequeue_and_start()

    # ── Override _on_tick to add automatic duration checking ──────────
    def _on_tick(self):
        """
        Automatic timing check for timed commands.

        1. If _duration_ms > 0 and elapsed time >= duration → finish
        2. Otherwise, delegate to _on_active_tick() for driver-specific work

        Subclasses should override _on_active_tick() instead of _on_tick().
        """
        # ── Check if the timed command has expired ────────────────────
        if self._duration_ms > 0:
            elapsed = time.ticks_diff(time.ticks_ms(), self._start_ms)
            if elapsed >= self._duration_ms:
                # Time's up — finish this command (may start next in queue)
                self._finish_current()
                return

        # ── Driver-specific per-tick work (optional override) ─────────
        self._on_active_tick()

    def _on_active_tick(self):
        """
        Called every cyclic() while the driver is ACTIVE and the
        duration has not yet expired.

        Override this for per-tick hardware updates:
          • Advancing animation frames (RGB effects)
          • Toggling blink state (LED)
          • Stepping through melody notes (buzzer)

        Default implementation: do nothing (sufficient for simple
        timed commands like a single tone or a timed motor drive).
        """
        pass  # Simple timed commands need no per-tick work


# =============================================================================
# ██  HalPollingDriver — Base for Input Drivers with Periodic Scanning
# =============================================================================
#
# Extends HalDriver for input devices that need periodic scanning
# (e.g., keypad matrix scan). Uses timestamp-based debouncing instead
# of blocking time.sleep_ms().
#
# This driver is ALWAYS active — it doesn't use the command queue.
# Its cyclic() continuously scans the hardware and fires callbacks
# when input is detected.
#
# Subclasses MUST implement:
#   • _scan()                — Read the hardware, return raw value or None
#   • _on_input(value)       — Called when a debounced input is confirmed
# =============================================================================

class HalPollingDriver(HalDriver):
    """Base class for input drivers with periodic scanning and debouncing."""

    # ── Polling-specific states ───────────────────────────────────────
    STATE_SCANNING   = 10   # Normal scanning (no pending input)
    STATE_DEBOUNCING = 11   # A raw input was detected, waiting to confirm

    DEBOUNCE_MS = 20        # How long to wait before confirming input

    def __init__(self):
        super().__init__()

        # ── Polling state ─────────────────────────────────────────────
        self._state = self.STATE_SCANNING   # Start in scanning mode
        self._pending_value = None          # The value being debounced
        self._debounce_start_ms = 0         # When debounce period started
        self._last_confirmed = None         # Last confirmed input (for edge detection)
        self._callback = None               # Optional user callback for input events

    def on_input(self, callback):
        """
        Register a callback that fires when a debounced input is detected.

        Args:
            callback: A function that takes one argument (the input value).
                      Example: keypad.on_input(lambda key: print("Pressed:", key))
        """
        self._callback = callback

    def cyclic(self):
        """
        Polling state machine — scans hardware and debounces input.

        This replaces the base HalDriver cyclic() entirely.
        The command queue is NOT used for polling drivers.

        State flow:
            SCANNING ──(raw input detected)──► DEBOUNCING
            DEBOUNCING ──(20ms elapsed, re-scan confirms)──► fire callback
            DEBOUNCING ──(20ms elapsed, re-scan differs)──► back to SCANNING
        """
        if self._state == self.STATE_SCANNING:
            # ── SCANNING: read the hardware ───────────────────────────
            raw = self._scan()

            if raw is not None and raw != self._last_confirmed:
                # New input detected — start debounce timer
                self._pending_value = raw
                self._debounce_start_ms = time.ticks_ms()
                self._state = self.STATE_DEBOUNCING

            elif raw is None:
                # Input released — reset edge detection
                self._last_confirmed = None

        elif self._state == self.STATE_DEBOUNCING:
            # ── DEBOUNCING: wait for confirmation ─────────────────────
            elapsed = time.ticks_diff(time.ticks_ms(), self._debounce_start_ms)

            if elapsed >= self.DEBOUNCE_MS:
                # Debounce period elapsed — re-scan to confirm
                confirmed = self._scan()

                if confirmed == self._pending_value:
                    # Confirmed! This is a real input.
                    self._last_confirmed = confirmed
                    self._on_input(confirmed)

                    # Fire user callback if registered
                    if self._callback is not None:
                        try:
                            self._callback(confirmed)
                        except Exception as e:
                            print("Input callback error:", e)

                # Either way, go back to scanning
                self._pending_value = None
                self._state = self.STATE_SCANNING

    # ── Abstract methods for subclasses ───────────────────────────────

    def _scan(self):
        """
        Perform one hardware scan. Return the detected value, or None.

        Example (keypad): scan the matrix, return the key character or None.
        """
        raise NotImplementedError

    def _on_input(self, value):
        """
        Called when a debounced input is confirmed.

        Override this for driver-specific handling (e.g., storing
        the last key for read_key() to return).
        """
        pass

    # ── Unused base class methods (polling drivers don't use queue) ───

    def _on_command_start(self, cmd):
        pass  # Not used — polling drivers don't have commands

    def _on_tick(self):
        pass  # Not used — cyclic() is fully overridden

    def _on_command_end(self):
        pass  # Not used — polling drivers are always scanning
```

---

## 6. Scheduler Design

The scheduler is a **unified task runner**. Drivers and user tasks live
in the same list — there is no special "driver mode". Each task has its
own interval.

```python
# =============================================================================
# hal_scheduler.py — Cooperative Task Scheduler for EZ-BOTIX
# =============================================================================
#
# The scheduler manages ALL periodic work in the system:
#   • Driver cyclic() calls (registered via register_driver)
#   • User periodic tasks (registered via add_task)
#
# Everything is a "task" — a callback + an interval. The scheduler calls
# each task's callback when its interval elapses.
# =============================================================================

import time


class TaskScheduler:
    """
    Lightweight cooperative task scheduler.

    All periodic work — driver cyclic calls AND user tasks — runs
    through this single scheduler. No special cases, no separate lists.
    """

    def __init__(self):
        # ── Single unified task list ──────────────────────────────────
        # Each entry is a dict:
        #   {
        #       'name':     str   — Human-readable name (for debugging)
        #       'interval': int   — Milliseconds between calls
        #       'last_run': int   — ticks_ms() of last execution
        #       'callback': func  — The function to call
        #       'is_driver': bool — True if this is a HAL driver task
        #   }
        self._tasks = []

        # ── Registered drivers (for is_all_idle check) ────────────────
        self._drivers = []

    # ═════════════════════════════════════════════════════════════════
    #  REGISTRATION
    # ═════════════════════════════════════════════════════════════════

    def register_driver(self, driver):
        """
        Register a HAL driver. Its cyclic() method will be called
        at the driver's CYCLIC_INTERVAL_MS interval.

        Also gives the driver a back-reference to this scheduler,
        so that blocking calls can advance all drivers.

        Args:
            driver: An instance of HalDriver (or subclass).
        """
        # Give the driver a back-reference to us
        driver._scheduler = self

        # Track the driver for is_all_idle() checks
        self._drivers.append(driver)

        # Add the driver's cyclic as a regular task
        self._tasks.append({
            'name':      driver.__class__.__name__,
            'interval':  driver.CYCLIC_INTERVAL_MS,
            'last_run':  time.ticks_ms(),
            'callback':  driver.cyclic,
            'is_driver': True,
        })

    def add_task(self, interval_ms, callback, name="UserTask"):
        """
        Register a user periodic task.

        Args:
            interval_ms (int):  How often to call the callback (in ms).
            callback (func):    The function to call (no arguments).
            name (str):         Human-readable name (for debug output).
        """
        self._tasks.append({
            'name':      name,
            'interval':  int(interval_ms),
            'last_run':  time.ticks_ms(),
            'callback':  callback,
            'is_driver': False,
        })

    # ═════════════════════════════════════════════════════════════════
    #  EXECUTION
    # ═════════════════════════════════════════════════════════════════

    def tick(self):
        """
        One scheduler tick. Checks every task and calls those whose
        interval has elapsed.

        This method is designed to be called rapidly (every ~1ms).
        Each task is only invoked when its own interval has passed.

        Error handling: if a task's callback throws an exception,
        we catch it, print it, and continue — one bad task cannot
        kill the entire system.
        """
        now = time.ticks_ms()

        for task in self._tasks:
            if time.ticks_diff(now, task['last_run']) >= task['interval']:
                task['last_run'] = now
                try:
                    task['callback']()
                except Exception as e:
                    print("Task '{}' error: {}".format(task['name'], e))

    def run(self, duration_ms=None):
        """
        Main event loop. Call this to start the system.

        Modes:
          • run()              → Run until ALL drivers are idle
                                  (no active commands, no queued commands)
          • run(duration_ms=N) → Run for exactly N milliseconds
          • run(duration_ms=0) → Run forever (until KeyboardInterrupt)

        Args:
            duration_ms (int|None):
                None = run until all drivers are idle (default).
                0    = run forever.
                N>0  = run for N milliseconds.
        """
        start = time.ticks_ms()

        while True:
            # ── Execute one tick ──────────────────────────────────────
            self.tick()
            time.sleep_ms(1)

            # ── Check termination conditions ──────────────────────────
            if duration_ms is None:
                # Mode: run until all drivers are idle
                if self.is_all_idle():
                    break
            elif duration_ms > 0:
                # Mode: run for a fixed duration
                if time.ticks_diff(time.ticks_ms(), start) >= duration_ms:
                    break
            # else: duration_ms == 0 → run forever (no break)

    # ═════════════════════════════════════════════════════════════════
    #  QUERIES
    # ═════════════════════════════════════════════════════════════════

    def is_all_idle(self):
        """
        Returns True if ALL registered drivers are idle
        (no active command and no queued commands).
        """
        return all(not drv.is_busy() for drv in self._drivers)

    def clear(self):
        """Remove all tasks and drivers."""
        self._tasks.clear()
        self._drivers.clear()


# ── Module-level instance ─────────────────────────────────────────────
scheduler = TaskScheduler()
```

---

## 7. Driver-Scheduler Integration

### 7.1 How Drivers Register

At boot, each driver instance registers with the scheduler.
This creates a task entry with the driver's specific interval:

```
  ┌────────────────────┐    register_driver(buzzer)    ┌──────────────────┐
  │   BuzzerDriver     │ ────────────────────────────► │  TaskScheduler   │
  │                    │                                │                  │
  │  CYCLIC_INTERVAL:  │   Creates task:                │  _tasks: [       │
  │    1 ms            │   { name: 'BuzzerDriver',     │    { ... },      │
  │                    │     interval: 1,               │    { ... },      │
  │  _scheduler: ──────┼──► callback: buzzer.cyclic }  │  ]               │
  │    (back-ref)      │                                │                  │
  └────────────────────┘                                └──────────────────┘
```

### 7.2 How Blocking Mode Advances All Drivers

```
  User calls: car.forward(80, duration_ms=2000)  ← blocking=True (default)

  ┌──────────────────────────────────────────────────────────────────────┐
  │  car._enqueue({'action': 'drive', ...}, blocking=True)               │
  │     │                                                                │
  │     ▼                                                                │
  │  car._block_until_idle()                                             │
  │     │                                                                │
  │     │   while car.is_busy():                                         │
  │     │     ├── car.cyclic()       ← advance this driver immediately   │
  │     │     ├── scheduler.tick()   ← advance ALL other drivers too     │
  │     │     │     ├── buzzer.cyclic()   ← background melody continues  │
  │     │     │     ├── rgb.cyclic()      ← LED effects continue         │
  │     │     │     ├── keypad.cyclic()   ← keypad keeps scanning        │
  │     │     │     └── car.cyclic()      ← (safe: just rechecks timer)  │
  │     │     └── sleep_ms(1)                                            │
  │     │                                                                │
  │     └── exits when car._state == IDLE and car._command_queue == []   │
  └──────────────────────────────────────────────────────────────────────┘
```

---

## 8. Concrete Driver — Cyclic Intervals

Each driver class defines its own `CYCLIC_INTERVAL_MS` based on how
fast it needs to react:

| Driver | `CYCLIC_INTERVAL_MS` | Rationale |
|--------|:--------------------:|-----------|
| `BuzzerDriver` | **1 ms** | Melody note transitions need ≤1ms precision |
| `RobotDrive` | **5 ms** | Motor timing is coarse; 5ms resolution is plenty |
| `LEDController` | **10 ms** | Blink toggle at 100Hz max — more than enough |
| `RGBStripDriver` | **20 ms** | ~50fps for smooth LED animations |
| `KeypadDriver` | **10 ms** | Scan at 100Hz for responsive key detection |
| `ButtonDriver` | **10 ms** | Debounce + edge detection at 100Hz |
| `IRSensorDriver` | **10 ms** | Obstacle edge detection at 100Hz |

---

## 9. System Architecture — Full Picture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          USER CODE (Blockly)                             │
│                                                                          │
│   buzzer.play_tone(440, 500)             # blocking (default)            │
│   car.forward(80, duration_ms=2000, blocking=False)  # non-blocking      │
│   rgb_front.show_effect("rainbow", blocking=False)   # non-blocking      │
│   scheduler.run()                        # drive everything              │
└───────────┬──────────────────────────────────────────────────────────────┘
            │ calls
            ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                       TaskScheduler (OS Layer)                           │
│                                                                          │
│   tick() ──► for each task:                                              │
│                if interval elapsed → task.callback()                     │
│                                                                          │
│   run()  ──► while not all_idle: tick() + sleep(1ms)                     │
│                                                                          │
│   Unified task list:                                                     │
│     ┌────────────────┬────────┬───────────────────────┐                   │
│     │ BuzzerDriver   │  1 ms  │ buzzer.cyclic()       │ ← driver task     │
│     │ RobotDrive     │  5 ms  │ car.cyclic()          │ ← driver task     │
│     │ LEDController  │ 10 ms  │ led.cyclic()          │ ← driver task     │
│     │ KeypadDriver   │ 10 ms  │ keypad.cyclic()       │ ← driver task     │
│     │ ButtonDriver   │ 10 ms  │ button.cyclic()       │ ← driver task     │
│     │ IRSensorDriver │ 10 ms  │ ir_sensor.cyclic()    │ ← driver task     │
│     │ RGBStripDriver │ 20 ms  │ rgb_front.cyclic()    │ ← driver task     │
│     │ RGBStripDriver │ 20 ms  │ rgb_back.cyclic()     │ ← driver task     │
│     │ UserTask       │200 ms  │ check_obstacle()      │ ← user task       │
│     └────────────────┴────────┴───────────────────────┘                   │
└───────────┬──────────────────────────────────────────────────────────────┘
            │ calls cyclic() on each at its interval
            ▼
┌────────────────┐  ┌────────────────┐  ┌────────────────┐
│ buzzer.cyclic()│  │  car.cyclic()  │  │rgb_front.cyclic│
│                │  │                │  │                │
│ Dequeue cmd    │  │ Dequeue cmd    │  │ Dequeue cmd    │
│ Check elapsed  │  │ Check elapsed  │  │ Advance frame  │
│ Start next cmd │  │ Start next cmd │  │ Start next cmd │
└────────────────┘  └────────────────┘  └────────────────┘

┌────────────────┐  ┌────────────────┐  ┌────────────────┐
│  led.cyclic()  │  │keypad.cyclic() │  │button.cyclic() │
│                │  │                │  │                │
│ Dequeue cmd    │  │ Scan matrix    │  │ Read pin       │
│ Toggle blink   │  │ Debounce check │  │ Debounce check │
│ Start next cmd │  │ Fire callback  │  │ Fire on_press  │
└────────────────┘  └────────────────┘  └────────────────┘

┌──────────────────┐
│ir_sensor.cyclic()│
│                  │
│ Read pin         │
│ Debounce check   │
│ Fire on_obstacle │
└──────────────────┘

PURE-READ DRIVER (no cyclic, no scheduler registration):
┌──────────────┐
│  ultrasonic  │
│              │
│ .distance_cm()  — instant hardware pulse (~30µs)
└──────────────┘
```

---

## 10. Boot Sequence & Driver Registration

```
┌──────────────────────────────────────────────────────────────────┐
│                      BOOT SEQUENCE                               │
│                                                                  │
│  1. Import hal_base (loads base classes)                         │
│  2. Import hal_scheduler (creates global scheduler)              │
│  3. Import all HAL drivers (each creates its global instance)    │
│  4. Register drivers with scheduler:                             │
│     ┌──────────────────────────────────────────────────────────┐ │
│     │ from hal_scheduler import scheduler                      │ │
│     │                                                          │ │
│     │ scheduler.register_driver(buzzer)      # 1ms interval    │ │
│     │ scheduler.register_driver(car)         # 5ms interval    │ │
│     │ scheduler.register_driver(onboard_led) # 10ms interval   │ │
│     │ scheduler.register_driver(external_led)# 10ms interval   │ │
│     │ scheduler.register_driver(rgb_front)   # 20ms interval   │ │
│     │ scheduler.register_driver(rgb_back)    # 20ms interval   │ │
│     │ scheduler.register_driver(keypad)      # 10ms interval   │ │
│     │ scheduler.register_driver(button)      # 10ms interval   │ │
│     │ scheduler.register_driver(ir_sensor)   # 10ms interval   │ │
│     └──────────────────────────────────────────────────────────┘ │
│  5. Execute user's Blockly-generated code                        │
│  6. If user calls scheduler.run(), the event loop drives all     │
│     cyclic() functions automatically at their intervals          │
└──────────────────────────────────────────────────────────────────┘
```

---

## 11. Driver Classification

| Driver | Base Class | Has `cyclic()`? | `CYCLIC_INTERVAL_MS` | Modes |
|--------|-----------|:---------------:|:--------------------:|-------|
| **hal_buzzer** | `HalTimedDriver` | ✅ | 1 ms | Blocking/Non-blocking tone & melody |
| **hal_motor** | `HalTimedDriver` | ✅ | 5 ms | Blocking/Non-blocking timed drive |
| **hal_LED** | `HalTimedDriver` | ✅ | 10 ms | Blocking/Non-blocking on, blink |
| **hal_RGB_LED** | `HalTimedDriver` | ✅ | 20 ms | Blocking/Non-blocking effects |
| **hal_keypad** | `HalPollingDriver` | ✅ | 10 ms | Non-blocking scan + callbacks |
| **hal_button** | `HalPollingDriver` | ✅ | 10 ms | Debounced edge detection + `on_press` / `on_release` callbacks |
| **hal_ir** | `HalPollingDriver` | ✅ | 10 ms | Debounced edge detection + `on_obstacle` / `on_clear` callbacks |
| **hal_ultrasonic** | None (pure read) | ❌ | N/A | `.distance_cm()` — ~30µs hardware pulse |
| **hal_oled** | `HalTimedDriver` | 🔜 Phase 2 | TBD | Scrolling text, animations |
| **hal_scheduler** | N/A (OS infra) | N/A | N/A | Drives all cyclic() calls |

---

## 12. Concrete Driver Example — BuzzerDriver

This shows how a complete driver looks when built on the hierarchy.
Notice how little code the concrete driver needs — the base classes
handle all the queue, timing, and blocking logic.

```python
# =============================================================================
# hal_buzzer.py — Buzzer Driver (Dual-Mode, Queued)
# =============================================================================
from machine import Pin, PWM
import time
from pin_config import PINS
from hal_base import HalTimedDriver


class BuzzerDriver(HalTimedDriver):
    """
    HAL driver for the passive buzzer.

    Supports:
      • Single tones (play_tone)         — queued, blocking or non-blocking
      • Melodies    (play_melody)         — expand to queued note sequence
      • Silence gaps (used between notes) — queued silence periods

    Inherits from HalTimedDriver:
      • Command queue (FIFO, max 16 commands)
      • Automatic duration checking (auto-stop when time expires)
      • Blocking spin loop (advances all drivers)
      • stop() / is_busy() / clear_queue()
    """

    # ── Timing: buzzer needs fast polling for precise note transitions ─
    CYCLIC_INTERVAL_MS = 1     # Called every 1ms by the scheduler
    MAX_QUEUE_SIZE     = 32    # Melodies can have many notes

    # ── Melody definitions (freq, duration_ms) ────────────────────────
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
        # ... more melodies ...
    }

    def __init__(self, pin=None):
        # Initialize base class (queue, state machine, timing)
        super().__init__()

        # ── Hardware setup ────────────────────────────────────────────
        if pin is None:
            pin = PINS["BUZZER"]
        # Configure PWM with duty=0 to prevent startup glitches.
        # PULL_DOWN avoids the faint hum that PULL_UP causes.
        self.pwm = PWM(Pin(pin, Pin.OUT, Pin.PULL_DOWN), freq=1000, duty=0)

    # ═════════════════════════════════════════════════════════════════
    #  PUBLIC API — what user code calls
    # ═════════════════════════════════════════════════════════════════

    def play_tone(self, freq, duration_ms=0, blocking=True):
        """
        Play a tone at the given frequency.

        Args:
            freq (int):        Frequency in Hz (20-20000).
            duration_ms (int): How long to play. 0 = play until stop().
            blocking (bool):   True = wait until done (default).
                               False = return immediately, plays in background.

        Examples:
            buzzer.play_tone(440, 500)                # Blocking: waits 500ms
            buzzer.play_tone(880, 300, blocking=False) # Non-blocking: queued
        """
        cmd = {'action': 'tone', 'freq': int(freq), 'duration_ms': int(duration_ms)}
        self._enqueue(cmd, blocking)

    def play_melody(self, name, blocking=True):
        """
        Play a named melody by expanding it into queued tone commands.

        Each note becomes a separate command in the queue, so the
        melody plays note by note via the normal cyclic mechanism.

        Args:
            name (str):      Melody name (e.g., "Mario", "StarWars").
            blocking (bool): True = wait until entire melody finishes.
                             False = return immediately, plays in background.
        """
        if name not in self.MELODIES:
            return  # Unknown melody — silently ignore

        notes = self.MELODIES[name]

        # Expand the melody into individual tone + silence commands
        for freq, dur in notes:
            if freq > 0:
                # Audible note
                self._command_queue.append(
                    {'action': 'tone', 'freq': freq, 'duration_ms': dur})
            else:
                # Silent gap (freq == 0)
                self._command_queue.append(
                    {'action': 'silence', 'duration_ms': dur})

            # Add a tiny gap between notes so they don't blend
            self._command_queue.append(
                {'action': 'silence', 'duration_ms': 20})

        # If blocking, wait for the entire melody to finish
        if blocking:
            self._block_until_idle()

    # ═════════════════════════════════════════════════════════════════
    #  ABSTRACT METHOD IMPLEMENTATIONS (required by HalTimedDriver)
    # ═════════════════════════════════════════════════════════════════

    def _on_command_start(self, cmd):
        """
        Start the hardware for a tone or silence command.

        Called by the base class when a command is dequeued.
        We read the command dict, configure the PWM, and set
        the duration for automatic timing.
        """
        action = cmd['action']

        if action == 'tone':
            # Set PWM frequency and 50% duty cycle for maximum volume
            self.pwm.freq(cmd['freq'])
            self.pwm.duty(512)
            self._duration_ms = cmd['duration_ms']

        elif action == 'silence':
            # Turn off sound but keep timing running
            self.pwm.duty(0)
            self._duration_ms = cmd['duration_ms']

    def _on_command_end(self):
        """
        Turn off the buzzer. Called when a command finishes or stop() is used.
        Safe to call multiple times (idempotent).
        """
        self.pwm.duty(0)


# ── Module-level instance ─────────────────────────────────────────────
buzzer = BuzzerDriver()
```

---

## 13. Usage Examples

### 13.1 Simple Blocking (Beginner / Blockly)

```python
# ── Sequential execution — each command waits until done ──────────
# Default blocking=True, so each line blocks until complete.
buzzer.play_tone(440, 500)             # Plays 440Hz for 500ms, then returns
buzzer.play_tone(880, 300)             # Plays 880Hz for 300ms, then returns
car.forward(80, duration_ms=2000)      # Drives forward for 2s, then returns
buzzer.play_melody("Mario")            # Plays entire melody, then returns
```

### 13.2 Queued Commands (Intermediate)

```python
# ── Queue multiple commands — they run one by one ─────────────────
# Non-blocking: commands are buffered and play in order.
buzzer.play_tone(440, 500, blocking=False)   # Queued (plays first)
buzzer.play_tone(880, 300, blocking=False)   # Queued (plays after 440)
buzzer.play_tone(660, 400, blocking=False)   # Queued (plays after 880)

# All three tones are in the queue.
# The scheduler processes them one by one:
#   1. 440Hz for 500ms
#   2. 880Hz for 300ms
#   3. 660Hz for 400ms
# Total time: 1200ms

scheduler.run()  # Drives everything until all drivers are idle
```

### 13.3 Non-Blocking Concurrent (Advanced)

```python
# ── Multiple drivers run at the same time ─────────────────────────
buzzer.play_melody("Mario", blocking=False)                # Background music
car.forward(80, duration_ms=2000, blocking=False)          # Drive forward
rgb_front.show_effect("rainbow", blocking=False)           # LED animation

# All three start immediately (non-blocking).
# The scheduler runs them concurrently:
scheduler.run()  # Exits when ALL drivers finish
```

### 13.4 Mixed Mode (Blocking + Non-Blocking Together)

```python
# ── Background music + sequential driving ─────────────────────────
# Start background music (non-blocking — returns immediately)
buzzer.play_melody("Mario", blocking=False)

# Sequential blocking drive commands.
# IMPORTANT: Because blocking mode calls scheduler.tick() internally,
# the background melody CONTINUES to play during these blocking calls.
car.forward(80, duration_ms=1000)      # Blocks 1s — melody plays on
car.turn_left(60, duration_ms=500)     # Blocks 0.5s — melody plays on
car.forward(80, duration_ms=1000)      # Blocks 1s — melody plays on
car.stop()

# At this point the car is stopped, but the melody may still be playing.
# If you want to wait for the melody too:
scheduler.run()  # Waits until buzzer finishes the melody
```

### 13.5 Queued Motor Path (Path Planning)

```python
# ── Pre-plan a driving path — commands execute in sequence ────────
car.forward(80, duration_ms=2000, blocking=False)      # Step 1: forward 2s
car.turn_left(60, duration_ms=800, blocking=False)     # Step 2: turn left
car.forward(80, duration_ms=1500, blocking=False)      # Step 3: forward 1.5s
car.turn_right(60, duration_ms=800, blocking=False)    # Step 4: turn right
car.forward(80, duration_ms=1000, blocking=False)      # Step 5: forward 1s

# All 5 commands are queued. The scheduler executes them one by one:
scheduler.run()  # Drives the entire path, then stops

# The car executed a complete path without the user needing to time anything!
```

### 13.6 Keypad with Callback

```python
# ── React to key presses via callback ─────────────────────────────
def on_key(key):
    if key == 'A':
        buzzer.play_tone(440, 200, blocking=False)
    elif key == 'B':
        car.forward(80, duration_ms=1000, blocking=False)

keypad.on_input(on_key)

# The scheduler calls keypad.cyclic() every 10ms.
# When a key is pressed and debounced, on_key() fires.
scheduler.run(duration_ms=0)  # Run forever (0 = infinite)
```

---

## 14. Implementation Roadmap

Step-by-step. Each step is fully tested before moving to the next.

| Step | File | What | Est. Lines | Depends On |
|------|------|------|:----------:|------------|
| **1** | `hal_base.py` | `HalDriver` + `HalTimedDriver` + `HalPollingDriver` | ~200 new | Nothing |
| **2** | `hal_scheduler.py` | Rewrite with `register_driver()` + `run(until_idle)` | ~80 rewrite | Step 1 |
| **3** | `hal_buzzer.py` | `BuzzerDriver(HalTimedDriver)` — full rewrite | ~120 rewrite | Steps 1-2 |
| **4** | `hal_motor.py` | `RobotDrive(HalTimedDriver)` — add queue + timed drive | ~100 rewrite | Steps 1-2 |
| **5** | `hal_LED.py` | `LEDController(HalTimedDriver)` — new wrapper class | ~80 new | Steps 1-2 |
| **6** | `hal_RGB_LED.py` | `RGBStripDriver(HalTimedDriver)` — rewrite effects as state machine | ~180 rewrite | Steps 1-2 |
| **7** | `hal_keypad.py` | `KeypadDriver(HalPollingDriver)` — non-blocking debounce | ~60 rewrite | Steps 1-2 |
| **8** | `hal_button.py` | `ButtonDriver(HalPollingDriver)` — debounce + edge callbacks | ~50 rewrite | Steps 1-2 |
| **9** | `hal_ir.py` | `IRSensorDriver(HalPollingDriver)` — edge detection + callbacks | ~50 rewrite | Steps 1-2 |
| **10** | `device_controller.py` | Update EXECUTION_HEADER + boot registration | ~20 changed | Steps 1-9 |
| **11** | `hal_oled.py` | Phase 2 — refactor existing 38KB driver to use base class | ~200+ changed | Steps 1-10 |

---

## 15. File Map

```
firmware/
├── hal_base.py            # ★ NEW — Base classes (HalDriver, HalTimedDriver, HalPollingDriver)
├── pin_config.py          # Central pin assignments (already done ✅)
├── hal_scheduler.py       # OS tick engine + driver registration (rewrite)
├── hal_buzzer.py          # Buzzer   — queued blocking + non-blocking tone/melody
├── hal_motor.py           # Motors   — queued blocking + non-blocking timed drive
├── hal_LED.py             # LEDs     — queued blocking + non-blocking on/blink
├── hal_RGB_LED.py         # NeoPixel — queued blocking + non-blocking effects
├── hal_keypad.py          # Keypad   — non-blocking debounced scan + callbacks
├── hal_button.py          # Button   — debounced edge detection + on_press/on_release callbacks
├── hal_ir.py              # IR       — debounced edge detection + on_obstacle/on_clear callbacks
├── hal_ultrasonic.py      # Sonar    — pure read (no changes needed)
├── hal_oled.py            # OLED     — Phase 2 (refactor existing driver)
└── ssd1306.py             # SSD1306 low-level I2C driver (no changes)
```

---

## 16. Design Rules (for ALL drivers, present and future)

### Rule 1 — Never Call `time.sleep_ms()` in Any Public API or `cyclic()`

Use the state machine + command queue. The ONLY place `sleep_ms(1)` appears
is inside `_block_until_idle()` and `scheduler.run()`.

### Rule 2 — Blocking Mode Reuses Non-Blocking

The blocking path is just: `_enqueue(cmd, blocking=True)` → which calls
`_block_until_idle()` — a spin loop on `cyclic()`. No separate implementation.

### Rule 3 — `cyclic()` Must Be Fast

No allocations, no loops, no I/O waits, no sleep. Just check timestamps,
update state, dequeue commands. Target: **<100µs per call**.

### Rule 4 — `stop()` Is Always Instant and Total

It kills the hardware, clears the queue, and resets to `STATE_IDLE`.
It is the emergency button.

### Rule 5 — `is_busy()` Checks Both State AND Queue

A driver is "busy" if it has an active command OR pending commands in
the queue. This is important for `scheduler.run()` termination.

### Rule 6 — Default to `blocking=True`

For backward compatibility with existing Blockly programs. Beginners
should never need to think about blocking vs non-blocking.

### Rule 7 — All Pins Come from `pin_config.py`

No hardcoded GPIO numbers in any driver file. Ever.

### Rule 8 — Always Use `time.ticks_diff(a, b)` for Elapsed Time

Never use raw subtraction (`now - start`). MicroPython's `ticks_ms()`
wraps around at 2^30 ms (~12.4 days). `ticks_diff()` handles this correctly.

### Rule 9 — Every `cyclic()` Must Be Safe to Call When Idle

If the driver is IDLE and the queue is empty, `cyclic()` must return
immediately with near-zero cost. This is called potentially hundreds
of times per second.

### Rule 10 — Commands Are Queued, Never Overwritten

Two rapid calls to the same driver produce two sequential actions,
not one overwritten action. This is the command queue guarantee.

### Rule 11 — Error Handling in Callbacks

All user callbacks (keypad input, scheduled tasks) are wrapped in
`try/except`. One bad callback must never crash the scheduler or
any driver.

### Rule 12 — Every Method, Class, and Constant Must Have a Comment

Code readability is a first-class priority. Comments explain **why**,
not just **what**. Every file starts with a module-level docstring
describing its purpose and dependencies.
