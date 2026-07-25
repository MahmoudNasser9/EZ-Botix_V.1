"""
serial_manager.py

Owns the physical serial connection and nothing else: scanning ports,
opening/closing the link, and writing raw bytes. It has no idea what a
"robot" or a "REPL" is - that logic belongs in DeviceController.

Keeping this layer dumb-on-purpose means it can be reused for any future
project that needs a serial link, and it's trivial to unit test in
isolation (mock serial.Serial and you're done).
"""

import serial
import serial.tools.list_ports

# Common USB-to-Serial hardware fingerprints used by ESP32 dev boards.
ROBOT_VENDOR_IDS = [0x1A86, 0x10C4, 0x303A, 0x0403]


class SerialManager:
    def __init__(self, baudrate=115200, timeout=1):
        self.baudrate = baudrate
        self.timeout = timeout
        self._ser = None

    def is_open(self):
        return self._ser is not None and self._ser.is_open

    def list_ports(self):
        """Scans hardware channels and generates clean, kid-friendly labels."""
        ports = serial.tools.list_ports.comports()
        labeled = []
        for p in ports:
            is_robot = p.vid in ROBOT_VENDOR_IDS
            label = f"🤖 EZ-BOTIX ({p.device})" if is_robot else f"🔌 Unknown Device ({p.device})"
            labeled.append({"device": p.device, "label": label, "is_robot": is_robot})

        labeled.sort(key=lambda x: x["is_robot"], reverse=True)
        return labeled

    def connect(self, port_name):
        """Opens the port while protecting the hardware reset lines."""
        self.disconnect()  # clear out any stale link first

        # NOTE: dsrdtr/rtscts are passed at construction time, not set
        # afterward. pyserial asserts DTR/RTS by default the moment the
        # port is opened - setting them False only *after* open() is too
        # late to prevent that first reset pulse. Passing them here
        # suppresses it at the source.
        self._ser = serial.Serial(
            port_name,
            self.baudrate,
            timeout=self.timeout,
            dsrdtr=False,
            rtscts=False,
        )
        self._ser.setDTR(False)
        self._ser.setRTS(False)

    def disconnect(self):
        """Gracefully releases the COM port resource back to the OS."""
        try:
            if self._ser and self._ser.is_open:
                self._ser.close()
        except Exception:
            pass
        finally:
            self._ser = None

    def write(self, data: bytes):
        if not self.is_open():
            raise serial.SerialException("Port is not open")
        self._ser.write(data)
