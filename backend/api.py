"""
api.py

AlphaBotAPI is the ONLY class bound to pywebview's js_api. Every method name
here matches what web/js/api-bridge.js calls, so the frontend doesn't need
to change if you rearrange the backend further.

This class does no real work itself - it just wires together
SerialManager + DeviceController + ProjectManager and forwards calls.
Adding a new capability (e.g. a firmware-upload feature) means adding a
method here plus wherever the real logic belongs - never growing this
class into a god-object again.
"""

from backend.serial_manager import SerialManager
from backend.device_controller import DeviceController
from backend.project_manager import ProjectManager


class AlphaBotAPI:
    def __init__(self):
        self._serial = SerialManager()
        self._device = DeviceController(self._serial)
        self._project = ProjectManager()

    def set_window(self, window):
        self._project.set_window(window)

    # --- Connectivity ---

    def get_ports(self):
        try:
            return self._serial.list_ports()
        except Exception:
            return []

    def connect_device(self, port_name):
        try:
            self._serial.connect(port_name)
            return {"status": "success", "message": f"Connected to {port_name}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def disconnect_device(self):
        self._serial.disconnect()
        return {"status": "success"}

    # --- Code execution ---

    def run_code(self, code_string):
        return self._device.run_code(code_string)

    def flash_code(self, code_string):
        return self._device.flash_code(code_string)

    def stop_device(self):
        return self._device.stop_device()

    # --- Project files ---

    def save_project(self, project_data):
        return self._project.save_project(project_data)

    def load_project(self):
        return self._project.load_project()
