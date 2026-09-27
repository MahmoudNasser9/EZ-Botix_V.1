# =============================================================================
# test_v2.py - Firmware V2 Architecture Test
# =============================================================================
# Run this file on your ESP32 to test the new non-blocking architecture.

from hal_scheduler import scheduler
from hal_buzzer import buzzer
from hal_LED import onboard_led, external_led
import time

print("--- Starting EZ-BOTIX V2 Test ---")

# 1. Register our new drivers with the scheduler
scheduler.register_driver(buzzer)
scheduler.register_driver(onboard_led)
scheduler.register_driver(external_led)

# 2. Enqueue commands (non-blocking)
print("Queueing commands...")

# The external LED will blink every 100ms for 3 seconds
external_led.blink(interval_ms=100, duration_ms=3000, blocking=False)
# Then it will stay solid for 2 seconds
external_led.on(duration_ms=2000, blocking=False)

# While that happens, the onboard LED will just stay on for 1 second
onboard_led.on(duration_ms=1000, blocking=False)

# While BOTH LEDs are doing their thing, play a melody!
buzzer.play_melody("PowerUp", blocking=False)
# Then queue a long tone
buzzer.play_tone(880, 500, blocking=False)


# 3. Start the event loop!
print("Starting scheduler...")
# scheduler.run() will spin until all drivers have emptied their queues
# and gone back to IDLE.
start_time = time.ticks_ms()

scheduler.run()

elapsed = time.ticks_diff(time.ticks_ms(), start_time)
print(f"--- Test Finished in {elapsed}ms! ---")
print("All queues are empty, all drivers are idle.")
