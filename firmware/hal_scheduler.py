"""
hal_scheduler.py

Lightweight non-blocking cooperative task scheduler for MicroPython.
Allows registering tasks to execute periodically at a given interval (in ms).
"""

import time


class TaskScheduler:
    def __init__(self):
        self.tasks = []

    def add_task(self, interval_ms, callback):
        """Registers a callback function to run periodically every interval_ms."""
        self.tasks.append({
            'interval': int(interval_ms),
            'last_run': time.ticks_ms(),
            'callback': callback
        })

    def tick(self):
        """Executes any tasks whose interval has elapsed."""
        now = time.ticks_ms()
        for task in self.tasks:
            if time.ticks_diff(now, task['last_run']) >= task['interval']:
                task['last_run'] = now
                try:
                    task['callback']()
                except Exception as e:
                    print("Task error:", e)

    def run(self, duration_ms=None):
        """Loops continuously (or for a given duration) executing tasks."""
        start = time.ticks_ms()
        while True:
            self.tick()
            time.sleep_ms(1)
            if duration_ms is not None:
                if time.ticks_diff(time.ticks_ms(), start) >= duration_ms:
                    break

    def clear(self):
        """Removes all registered tasks."""
        self.tasks.clear()


scheduler = TaskScheduler()
