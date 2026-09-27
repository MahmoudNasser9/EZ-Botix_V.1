# =============================================================================
# hal_scheduler.py — Cooperative Task Scheduler for EZ-BOTIX
# =============================================================================
#
# The scheduler is the OS heartbeat. It manages ALL periodic work:
#   • Driver cyclic() calls — registered via register_driver()
#   • User periodic tasks  — registered via add_task()
#
# Everything is a "task" — a callback + an interval. There is no special
# "driver mode" or separate driver list. Drivers register themselves as
# tasks with their own CYCLIC_INTERVAL_MS, and their cyclic() is called
# at that interval — exactly the same as any user task.
#
# The scheduler also provides the main event loop (run()), which keeps
# ticking until a termination condition is met.
#
# Dependencies: None (this module has no imports from hal_base or drivers)
# =============================================================================

import time


class TaskScheduler:
    """
    Lightweight cooperative task scheduler for MicroPython.

    All periodic work — HAL driver cyclic calls AND user tasks — runs
    through this single scheduler. No special cases, no separate lists.

    Usage:
        from hal_scheduler import scheduler

        # Register a driver (its cyclic() will be called at its interval)
        scheduler.register_driver(buzzer)

        # Register a user task
        scheduler.add_task(200, check_obstacle, name="ObstacleCheck")

        # Start the event loop
        scheduler.run()           # Run until all drivers are idle
        scheduler.run(duration_ms=5000)  # Run for 5 seconds
        scheduler.run(duration_ms=0)     # Run forever
    """

    def __init__(self):
        # ── Unified task list ─────────────────────────────────────────
        # Every entry is a dict with these fields:
        #   'name'      (str)  — Human-readable label (for debug output)
        #   'interval'  (int)  — Milliseconds between calls
        #   'last_run'  (int)  — ticks_ms() timestamp of the last execution
        #   'callback'  (func) — The function to call (no arguments)
        #   'is_driver' (bool) — True if this task is a HAL driver's cyclic
        #
        # Drivers and user tasks sit side-by-side in this list.
        # The scheduler treats them identically — the only difference is
        # 'is_driver', which is used for bookkeeping (not scheduling).
        self._tasks = []

        # ── Registered drivers ────────────────────────────────────────
        # A separate list of driver *references* (not tasks).
        # Used by is_all_idle() to check whether any driver is still busy.
        # This list does NOT control scheduling — _tasks does.
        self._drivers = []

    # ═════════════════════════════════════════════════════════════════
    #  REGISTRATION — adding drivers and user tasks
    # ═════════════════════════════════════════════════════════════════

    def register_driver(self, driver):
        """
        Register a HAL driver with the scheduler.

        This does two things:
          1. Adds the driver's cyclic() as a periodic task, called
             at the driver's CYCLIC_INTERVAL_MS interval.
          2. Gives the driver a back-reference to this scheduler,
             so that _block_until_idle() can call scheduler.tick()
             to advance ALL drivers during a blocking wait.

        Args:
            driver: An instance of HalDriver (or any subclass).
                    Must have: .cyclic() method,
                               .CYCLIC_INTERVAL_MS attribute,
                               .is_busy() method,
                               ._scheduler attribute (will be set).

        Example:
            from hal_buzzer import buzzer
            scheduler.register_driver(buzzer)   # buzzer.cyclic() called every 1ms
        """
        # ── Give the driver a back-reference to this scheduler ────────
        # The driver uses this in _block_until_idle() to advance
        # all other drivers while waiting. Without this, blocking
        # calls would freeze every other driver.
        driver._scheduler = self

        # ── Track the driver for is_all_idle() checks ─────────────────
        # We keep a separate list of driver objects so we can call
        # driver.is_busy() without scanning the entire task list.
        self._drivers.append(driver)

        # ── Add the driver's cyclic() as a regular scheduled task ─────
        # The driver's CYCLIC_INTERVAL_MS determines how often it's called.
        # From the scheduler's perspective, this is just another task.
        self._tasks.append({
            'name':      driver.__class__.__name__,  # e.g. "BuzzerDriver"
            'interval':  driver.CYCLIC_INTERVAL_MS,
            'last_run':  time.ticks_ms(),
            'callback':  driver.cyclic,
            'is_driver': True,
        })

    def add_task(self, interval_ms, callback, name="UserTask"):
        """
        Register a user periodic task.

        The callback will be called every interval_ms milliseconds.
        If the callback raises an exception, it is caught and printed
        — it will NOT crash the scheduler or affect other tasks.

        Args:
            interval_ms (int):  How often to call the callback (in ms).
            callback (func):    The function to call (no arguments).
            name (str):         Human-readable name (shown in error messages).

        Example:
            def check_obstacle():
                if ultrasonic.distance_cm() < 15:
                    car.stop()

            scheduler.add_task(200, check_obstacle, name="ObstacleCheck")
        """
        self._tasks.append({
            'name':      name,
            'interval':  int(interval_ms),
            'last_run':  time.ticks_ms(),
            'callback':  callback,
            'is_driver': False,
        })

    # ═════════════════════════════════════════════════════════════════
    #  EXECUTION — the heartbeat
    # ═════════════════════════════════════════════════════════════════

    def tick(self):
        """
        Execute one scheduler tick.

        Checks every registered task (drivers AND user tasks) and calls
        those whose interval has elapsed since their last execution.

        This method is designed to be called rapidly (every ~1ms) from
        the main event loop (run()) or from a driver's _block_until_idle().

        Error handling:
          If a task's callback throws an exception, we catch it, print
          a diagnostic message with the task name, and continue. One
          bad task must NEVER crash the entire system.

        Performance:
          This method iterates the full task list on every call. With
          ~10 tasks at typical intervals, this takes <50µs on ESP32.
        """
        now = time.ticks_ms()

        for task in self._tasks:
            # Use ticks_diff for safe rollover handling.
            # ticks_ms() wraps at 2^30 ms (~12.4 days).
            # Raw subtraction (now - last_run) would break on wrap.
            if time.ticks_diff(now, task['last_run']) >= task['interval']:
                task['last_run'] = now
                try:
                    task['callback']()
                except Exception as e:
                    print("Task '{}' error: {}".format(task['name'], e))

    def run(self, duration_ms=None):
        """
        Main event loop — starts the scheduler and ticks continuously.

        Three termination modes:

          1. run()               → Run until ALL registered drivers are idle.
                                    (No active commands, no queued commands.)
                                    If no drivers are registered, returns
                                    immediately.

          2. run(duration_ms=N)  → Run for exactly N milliseconds, then stop.
                                    Useful for "run everything for 5 seconds".

          3. run(duration_ms=0)  → Run forever until a KeyboardInterrupt
                                    (Ctrl+C) is received. Useful for
                                    event-driven programs (e.g. keypad
                                    callback loops).

        Args:
            duration_ms (int or None):
                None  = run until all drivers idle (default).
                0     = run forever.
                N > 0 = run for N milliseconds.

        Examples:
            scheduler.run()                # Until all drivers finish
            scheduler.run(duration_ms=5000)  # For 5 seconds
            scheduler.run(duration_ms=0)     # Forever (Ctrl+C to stop)
        """
        start = time.ticks_ms()

        while True:
            # ── Execute one scheduler tick ────────────────────────────
            # This calls every task whose interval has elapsed.
            self.tick()

            # ── Small sleep to prevent CPU starvation ─────────────────
            # Without this, the tight loop would consume 100% CPU and
            # starve other MicroPython internals (GC, WiFi, etc.).
            time.sleep_ms(1)

            # ── Check termination condition ───────────────────────────
            if duration_ms is None:
                # Mode 1: Run until all drivers are idle.
                # If no drivers are registered, exit immediately to
                # avoid an infinite loop with nothing to do.
                if self.is_all_idle():
                    break

            elif duration_ms > 0:
                # Mode 2: Run for a fixed duration.
                if time.ticks_diff(time.ticks_ms(), start) >= duration_ms:
                    break

            # Mode 3: duration_ms == 0 → run forever (no break condition).
            # The loop continues until the user sends Ctrl+C
            # (KeyboardInterrupt), which MicroPython handles naturally.

    # ═════════════════════════════════════════════════════════════════
    #  QUERIES — checking scheduler state
    # ═════════════════════════════════════════════════════════════════

    def is_all_idle(self):
        """
        Returns True if ALL registered drivers are idle.

        A driver is considered idle when:
          • Its state is STATE_IDLE (no active command), AND
          • Its command queue is empty (no pending commands).

        This is the termination condition for run() in default mode.
        If no drivers are registered, returns True immediately.
        """
        # all() on an empty iterable returns True — which is correct:
        # if there are no drivers, there's nothing to wait for.
        return all(not drv.is_busy() for drv in self._drivers)

    def clear(self):
        """
        Remove ALL registered tasks AND drivers.

        After calling clear(), the scheduler is empty — no tasks will
        run on the next tick(). Drivers are also unlinked (their
        _scheduler back-reference is set to None).

        Use this to completely reset the system, e.g. before loading
        a new user program.
        """
        # Unlink all drivers from this scheduler
        for drv in self._drivers:
            drv._scheduler = None

        # Clear both lists
        self._tasks.clear()
        self._drivers.clear()


# ═════════════════════════════════════════════════════════════════════
# Module-level instance
# ═════════════════════════════════════════════════════════════════════
# This is the single global scheduler that all drivers and user code
# share. It is created once when this module is first imported.
#
# Usage:
#   from hal_scheduler import scheduler
#   scheduler.register_driver(buzzer)
#   scheduler.add_task(200, my_callback)
#   scheduler.run()
# ═════════════════════════════════════════════════════════════════════

scheduler = TaskScheduler()
