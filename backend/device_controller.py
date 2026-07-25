"""
device_controller.py

Owns the MicroPython REPL protocol: entering/exiting raw REPL, running code
live, flashing code to main.py, and stopping the robot. It talks to the
board only through a SerialManager - it never touches pyserial directly.

Centralizing the protocol constants (Ctrl+C/A/B/D) here means there is
exactly one place that knows how the wire protocol works. Previously this
logic was duplicated (and had drifted out of sync) across run_code,
flash_code, and stop_device.
"""

import json
import time

import serial


class DeviceController:
    # Every block-generated program needs these names available on the device.
    EXECUTION_HEADER = (
        "from hal_car import car, onboard_led\n"
        "from hal_keypad import keypad\n"
        "import time\n\n"
    )

    CTRL_C = b"\x03"  # Interrupt running program
    CTRL_A = b"\x01"  # Enter raw REPL
    CTRL_B = b"\x02"  # Exit raw REPL (back to friendly REPL)
    CTRL_D = b"\x04"  # Execute (raw REPL) / soft reboot (friendly REPL)

    def __init__(self, serial_manager):
        self.serial = serial_manager

    # --- Low-level REPL transitions, used by every public method below ---

    def _enter_raw_repl(self):
        self.serial.write(self.CTRL_C + self.CTRL_A)
        time.sleep(0.05)

    def _exit_raw_repl(self):
        self.serial.write(self.CTRL_B)
        time.sleep(0.05)

    def _execute_raw(self, payload: str):
        """Sends payload text then triggers execution inside raw REPL."""
        self.serial.write(payload.encode("utf-8"))
        time.sleep(0.05)
        self.serial.write(self.CTRL_D)

    def _soft_reboot(self):
        """Must be called from friendly REPL - clears RAM and runs main.py."""
        self.serial.write(self.CTRL_D)
        time.sleep(0.05)

    # --- Public API (method names match what the frontend calls) ---

    def run_code(self, block_code: str):
        """Injects block-generated code straight into RAM and runs it once."""
        if not self.serial.is_open():
            return {"status": "error", "message": "No robot connected!"}

        try:
            full_code = self.EXECUTION_HEADER + block_code
            self._enter_raw_repl()
            self._execute_raw(full_code)
            return {"status": "success"}
        except (serial.SerialException, OSError):
            self.serial.disconnect()  # auto-cleanup ghost link on wire pull
            return {"status": "disconnect_detected", "message": "Hardware disconnected unexpectedly!"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def flash_code(self, block_code: str):
        """Writes code to main.py on the device, then soft-reboots to auto-run it."""
        if not self.serial.is_open():
            return {"status": "error", "message": "No robot connected!"}

        try:
            full_code = self.EXECUTION_HEADER + block_code
            escaped_payload = json.dumps(full_code)
            storage_script = (
                f"with open('main.py', 'w') as f:\n"
                f"    f.write({escaped_payload})\n"
            )

            self._enter_raw_repl()
            self._execute_raw(storage_script)
            time.sleep(0.5)  # let the flash memory cells finish writing

            self._exit_raw_repl()
            self._soft_reboot()
            return {"status": "success"}
        except (serial.SerialException, OSError):
            self.serial.disconnect()
            return {"status": "disconnect_detected", "message": "Hardware disconnected unexpectedly!"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def stop_device(self):
        """Forces the hardware execution pipeline to halt safely, instantly."""
        if not self.serial.is_open():
            return {"status": "error", "message": "Device port not open"}

        try:
            # Uses the same raw-REPL path as run_code/flash_code (the original
            # version used a different, inconsistent entry sequence here).
            # Also imports onboard_led explicitly - the previous version
            # referenced onboard_led.value(0) without importing it, which
            # raised a NameError on every Stop press.
            stop_script = (
                "from hal_car import car, onboard_led\n"
                "car.stop()\n"
                "onboard_led.value(0)\n"
            )
            self._enter_raw_repl()
            self._execute_raw(stop_script)
            self._exit_raw_repl()
            return {"status": "success"}
        except (serial.SerialException, OSError):
            self.serial.disconnect()
            return {"status": "disconnect_detected"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
