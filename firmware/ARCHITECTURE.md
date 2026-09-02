# EZ-BOTIX Firmware — HAL Driver Architecture

> **Version:** 1.0  
> **Date:** 2026-09-02  
> **Target:** ESP32 + MicroPython  

---

## 1. Design Philosophy

Every HAL driver in the EZ-BOTIX firmware follows one unified pattern.  
The two core principles are:

1. **Dual-Mode API** — Every timed command offers both **blocking** and **non-blocking** modes. The caller chooses.
2. **Cyclic Cooperation** — Every driver exposes a `cyclic()` method. The OS scheduler calls it on every tick to advance non-blocking operations.

This means:
- **Blockly beginners** can write simple sequential code that "just works" (blocking mode).
- **Advanced programs** can run multiple things concurrently (non-blocking mode + scheduler).
- **No code duplication** — the blocking path simply starts the non-blocking operation, then spins on `cyclic()` until it finishes.

---

## 2. Dual-Mode API Pattern

Every timed command accepts a `blocking` parameter (default `True` for backward compatibility):

```
                 ┌──────────────────────────────────────────────────┐
                 │           buzzer.play_tone(440, 500)             │
                 │                                                  │
                 │  blocking=True (default)  │  blocking=False      │
                 │  ─────────────────────    │  ──────────────────  │
                 │  Starts hardware          │  Starts hardware     │
                 │  Spins on cyclic()        │  Returns immediately │
                 │  Returns when done        │  cyclic() auto-stops │
                 └──────────────────────────────────────────────────┘
```

### Implementation Rule

The blocking path **never** uses `time.sleep_ms()` directly. Instead, it reuses the non-blocking path:

```python
def play_tone(self, freq, duration_ms=0, blocking=True):
    # 1. Start the hardware (always non-blocking internally)
    self._start_tone(freq, duration_ms)

    # 2. If blocking requested, spin until done
    if blocking and duration_ms > 0:
        while self._state != STATE_IDLE:
            self.cyclic()
            time.sleep_ms(1)
```

This guarantees:
- ✅ Blocking and non-blocking paths use **identical timing logic**
- ✅ No risk of the two modes drifting out of sync
- ✅ `cyclic()` is always the single source of truth for "when to stop"

---

## 3. Driver State Machine

Every driver that has time-dependent behavior uses this state model:

```
    ┌──────────┐   start_command()   ┌──────────┐   elapsed >= duration   ┌──────────┐
    │          │ ──────────────────►  │          │ ──────────────────────► │          │
    │   IDLE   │                     │  ACTIVE  │                         │   IDLE   │
    │          │ ◄──────────────────  │          │                         │          │
    └──────────┘      stop()         └──────────┘                         └──────────┘
                                          │
                                          │ (for multi-step commands
                                          │  like melodies / effects)
                                          ▼
                                     ┌──────────┐
                                     │ STEP N   │──► STEP N+1 ──► ... ──► IDLE
                                     └──────────┘
```

### Core State Variables

Every timed driver maintains:

| Variable        | Type  | Purpose                                         |
|-----------------|-------|-------------------------------------------------|
| `_state`        | int   | Current state (`IDLE`, `ACTIVE`, `MELODY`, etc.) |
| `_start_ms`     | int   | `time.ticks_ms()` when command started           |
| `_duration_ms`  | int   | How long to run (0 = indefinitely until `stop()`) |

### The `cyclic()` Contract

```python
def cyclic(self):
    """
    Called by the OS scheduler on every tick (~1-5ms).
    
    Rules:
    - MUST return quickly (no sleep, no loops, no blocking I/O)
    - MUST be safe to call when IDLE (just returns)
    - MUST handle auto-stop when duration expires
    - MUST advance multi-step sequences (melodies, effects)
    """
    if self._state == self.STATE_IDLE:
        return  # Fast exit — costs almost nothing

    now = time.ticks_ms()
    elapsed = time.ticks_diff(now, self._start_ms)
    
    # Check if timed command has expired
    if self._duration_ms > 0 and elapsed >= self._duration_ms:
        self.stop()
        return
    
    # Handle multi-step logic (driver-specific)
    ...
```

---

## 4. System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER CODE (Blockly)                        │
│                                                                     │
│   buzzer.play_tone(440, 500)          # blocking by default        │
│   car.forward(80, duration_ms=2000, blocking=False)  # non-block   │
│   rgb_front.show_effect("rainbow", blocking=False)   # non-block   │
│   scheduler.run()                     # start the OS loop          │
└─────────┬───────────────────────────────────────────────────────────┘
          │ calls
          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     TaskScheduler (OS Layer)                        │
│                                                                     │
│   tick() ──► for drv in _drivers:  drv.cyclic()   ◄── every tick   │
│          ──► for task in tasks:    task.callback() ◄── by interval  │
│                                                                     │
│   register_driver(driver)   ◄── called once at boot                │
│   add_task(interval, cb)    ◄── user periodic tasks                │
└─────────┬───────────────────────────────────────────────────────────┘
          │ calls cyclic() on each
          ▼
┌────────────────┐ ┌────────────────┐ ┌────────────────┐
│ buzzer.cyclic() │ │  car.cyclic()  │ │rgb_front.cyclic│
│                │ │                │ │                │
│ Check elapsed  │ │ Check elapsed  │ │ Advance frame  │
│ Stop if done   │ │ Stop if done   │ │ Stop if done   │
└────────────────┘ └────────────────┘ └────────────────┘

┌────────────────┐ ┌────────────────┐ ┌────────────────┐
│  led.cyclic()  │ │keypad.cyclic() │ │rgb_back.cyclic │
│                │ │                │ │                │
│ Toggle blink   │ │ Debounce scan  │ │ Advance frame  │
│ Stop if done   │ │ Fire callback  │ │ Stop if done   │
└────────────────┘ └────────────────┘ └────────────────┘

  PURE-READ DRIVERS (no cyclic needed):
  ┌──────────┐  ┌──────────┐  ┌──────────────┐
  │  button  │  │ ir_sensor│  │  ultrasonic   │
  │ .is_pressed()│ .is_obstacle_detected() │ .distance_cm() │
  └──────────┘  └──────────┘  └──────────────┘
```

---

## 5. Driver Template

Every new driver MUST follow this template:

```python
# hal_example.py
import time
from pin_config import PINS


class ExampleDriver:
    """HAL driver for <hardware component>."""

    # --- States ---
    STATE_IDLE   = 0
    STATE_ACTIVE = 1

    def __init__(self):
        # Hardware setup
        ...
        # State machine
        self._state = self.STATE_IDLE
        self._start_ms = 0
        self._duration_ms = 0

    # ─────────────────────────────────────────────
    # Public API (what user code calls)
    # ─────────────────────────────────────────────

    def start(self, duration_ms=0, blocking=True):
        """
        Start the hardware action.

        Args:
            duration_ms: How long to run. 0 = run until stop() is called.
            blocking:    True  = wait here until done (default).
                         False = return immediately, cyclic() handles the rest.
        """
        self._apply_hardware()  # Turn on the hardware NOW
        self._state = self.STATE_ACTIVE
        self._start_ms = time.ticks_ms()
        self._duration_ms = int(duration_ms)

        if blocking and duration_ms > 0:
            self._block_until_idle()

    def stop(self):
        """Stop the hardware immediately."""
        self._shutdown_hardware()
        self._state = self.STATE_IDLE

    def is_busy(self):
        """Returns True if the driver is currently doing something."""
        return self._state != self.STATE_IDLE

    # ─────────────────────────────────────────────
    # Cyclic (called by OS scheduler every tick)
    # ─────────────────────────────────────────────

    def cyclic(self):
        """Called every OS tick. Manages timing and state transitions."""
        if self._state == self.STATE_IDLE:
            return

        if self._duration_ms > 0:
            elapsed = time.ticks_diff(time.ticks_ms(), self._start_ms)
            if elapsed >= self._duration_ms:
                self.stop()

    # ─────────────────────────────────────────────
    # Private helpers
    # ─────────────────────────────────────────────

    def _block_until_idle(self):
        """Spin on cyclic() until the operation completes."""
        while self._state != self.STATE_IDLE:
            self.cyclic()
            time.sleep_ms(1)

    def _apply_hardware(self):
        """Turn on / configure the physical hardware."""
        ...

    def _shutdown_hardware(self):
        """Turn off the physical hardware."""
        ...


# Module-level instance
example = ExampleDriver()
```

---

## 6. Driver Classification

| Driver | Type | Has `cyclic()`? | Modes |
|--------|------|:---------------:|-------|
| **hal_buzzer** | Output + Timed | ✅ | Blocking / Non-blocking tone & melody |
| **hal_motor** | Output + Timed | ✅ | Blocking / Non-blocking timed drive |
| **hal_LED** | Output + Timed | ✅ | Blocking / Non-blocking on, blink |
| **hal_RGB_LED** | Output + Timed | ✅ | Blocking / Non-blocking effects |
| **hal_keypad** | Input + Debounce | ✅ | Non-blocking scan + callbacks |
| **hal_button** | Input (instant) | ❌ | Read-only, always non-blocking |
| **hal_ir** | Input (instant) | ❌ | Read-only, always non-blocking |
| **hal_ultrasonic** | Input (µs-level) | ❌ | Read-only, ~30µs acceptable |
| **hal_oled** | Output + Animation | 🔜 Phase 2 | Too large for Phase 1 |
| **hal_scheduler** | OS Infrastructure | N/A | Drives all `cyclic()` calls |

---

## 7. Scheduler Enhancement

The scheduler gains a `register_driver()` method. Drivers registered this way have their `cyclic()` called on **every single tick**, before user tasks:

```python
class TaskScheduler:
    def __init__(self):
        self.tasks = []       # User periodic tasks (interval-based)
        self._drivers = []    # HAL drivers (called every tick)

    def register_driver(self, driver):
        """Register a driver. Its cyclic() is called every tick."""
        self._drivers.append(driver)

    def tick(self):
        """One OS tick. Drivers first, then user tasks."""
        # 1. Always call every driver's cyclic — fast, no interval check
        for drv in self._drivers:
            drv.cyclic()

        # 2. Check and run interval-based user tasks
        now = time.ticks_ms()
        for task in self.tasks:
            if time.ticks_diff(now, task['last_run']) >= task['interval']:
                task['last_run'] = now
                try:
                    task['callback']()
                except Exception as e:
                    print("Task error:", e)
```

---

## 8. Boot Sequence & Driver Registration

When the ESP32 runs user code, the execution header (injected by `device_controller.py`) sets up the system:

```
┌─────────────────────────────────────────────────┐
│                  BOOT SEQUENCE                   │
│                                                  │
│  1. Import all HAL drivers                       │
│  2. Register drivers with scheduler              │
│  3. Execute user's Blockly-generated code        │
│  4. If user calls scheduler.run(), the OS loop   │
│     drives all cyclic() functions automatically  │
└─────────────────────────────────────────────────┘
```

---

## 9. Usage Examples

### Simple Blocking (Beginner / Blockly)

```python
# This works exactly like before — one thing at a time
buzzer.play_tone(440, 500)             # Blocks for 500ms
car.forward(80, duration_ms=2000)      # Blocks for 2000ms
buzzer.play_melody("Mario")            # Blocks until melody ends
```

### Non-Blocking Concurrent (Advanced)

```python
# Start multiple things at once — none block
buzzer.play_tone(440, 500, blocking=False)
car.forward(80, duration_ms=2000, blocking=False)
rgb_front.show_effect("rainbow", blocking=False)

# Let the scheduler drive everything
scheduler.run()  # Runs until all drivers are idle

# Or run for a specific time
scheduler.run(duration_ms=5000)  # Run everything for 5 seconds
```

### Mixed Mode

```python
# Start background music
buzzer.play_melody("Mario", blocking=False)

# While music plays, drive around (blocking calls in sequence)
car.forward(80, duration_ms=1000)   # Blocks 1s, but music keeps playing
                                     # because blocking uses cyclic() internally
car.turn_left(60, duration_ms=500)  # Blocks 0.5s
car.forward(80, duration_ms=1000)   # Blocks 1s
car.stop()
```

> **Key insight:** Even the blocking path calls `cyclic()` in its spin loop. This means background non-blocking operations (like a melody) continue to advance while a blocking call is waiting. Everything stays alive.

---

## 10. Implementation Roadmap

Step-by-step. Each step is fully tested before moving to the next.

| Step | Driver | Estimated Lines | Depends On |
|------|--------|:---------:|------------|
| **1** | `hal_scheduler.py` — Add `register_driver()` | ~10 new | Nothing |
| **2** | `hal_buzzer.py` — Full rewrite with dual-mode | ~120 | Step 1 |
| **3** | `hal_motor.py` — Add timed drive + `cyclic()` | ~30 new | Step 1 |
| **4** | `hal_LED.py` — Add `LEDController` wrapper | ~60 new | Step 1 |
| **5** | `hal_RGB_LED.py` — Generator-based effects | ~80 changed | Step 1 |
| **6** | `hal_keypad.py` — Non-blocking debounce | ~30 changed | Step 1 |
| **7** | `device_controller.py` — Update header | ~10 changed | Steps 1-6 |
| **8** | `hal_oled.py` — Phase 2 (future) | ~200+ | Steps 1-7 |

---

## 11. File Map

```
firmware/
├── pin_config.py          # Central pin assignments (already done ✅)
├── hal_scheduler.py       # OS tick engine + driver registration
├── hal_buzzer.py          # Buzzer   — blocking + non-blocking tone/melody
├── hal_motor.py           # Motors   — blocking + non-blocking timed drive
├── hal_LED.py             # LEDs    — blocking + non-blocking on/blink
├── hal_RGB_LED.py         # NeoPixel — blocking + non-blocking effects
├── hal_keypad.py          # Keypad   — non-blocking scan + callbacks
├── hal_button.py          # Button   — pure read (no changes needed)
├── hal_ir.py              # IR       — pure read (no changes needed)
├── hal_ultrasonic.py      # Sonar    — pure read (no changes needed)
├── hal_oled.py            # OLED     — Phase 2 (deferred)
└── ssd1306.py             # SSD1306 low-level I2C driver (no changes)
```

---

## 12. Design Rules (for all future drivers)

1. **Never call `time.sleep_ms()` in a public API.** Use the state machine + `cyclic()` pattern.
2. **Blocking mode reuses non-blocking.** The blocking path is just `_block_until_idle()` — a spin loop on `cyclic()`.
3. **`cyclic()` must be fast.** No allocations, no loops, no I/O waits. Just check timestamps, update state.
4. **`stop()` is always instant.** It kills the hardware and resets to `STATE_IDLE`.
5. **`is_busy()` returns `True` when a timed command is in progress.** Useful for user code to check without blocking.
6. **Default to `blocking=True`** for backward compatibility with existing Blockly programs.
7. **All pins come from `pin_config.py`.** No hardcoded GPIO numbers in any driver.
