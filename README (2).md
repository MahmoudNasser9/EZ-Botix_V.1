# EZ-BOTIX

Blockly-based visual programming desktop app for the EZ-BOTIX ESP32 robot kit.

## Structure

```
ez-botix/
├── main.py                       # entry point only
├── requirements.txt
├── backend/
│   ├── api.py                    # AlphaBotAPI - the ONLY class bound to pywebview
│   ├── serial_manager.py         # SerialManager - raw serial port ownership
│   ├── device_controller.py      # DeviceController - MicroPython REPL protocol
│   └── project_manager.py        # ProjectManager - save/load .ezb file dialogs
├── firmware/                     # runs ON the ESP32, not on the desktop
│   ├── hal_car.py
│   └── hal_keypad.py
└── web/
    ├── index.html                # markup shell only
    ├── css/style.css
    ├── lib/blockly/              # vendored blockly.min.js + python_compressed.js
    └── js/
        ├── registry.js           # EZBOTIX.registerCategory() mechanism
        ├── toolbox.js            # builds the toolbox from the registry
        ├── api-bridge.js         # the only file that calls pywebview.api
        ├── ui.js                 # DOM wiring, button handlers
        └── blocks/
            ├── lights.js         # 💡 Lights category
            ├── motion.js         # 🛞 Motion category
            ├── inputs.js         # ⌨️ Inputs category
            └── utility.js        # delay_ms (lives in the standard Loops category)
```

## Running

```bash
pip install -r requirements.txt
python main.py
```

## Firmware setup (currently manual)

`firmware/hal_car.py` and `firmware/hal_keypad.py` must exist on the ESP32's
own filesystem (they're imported by the code the app sends over serial).
Right now that's done by hand with Thonny: open each file and use
"Save as... > MicroPython device" to copy it to the board.

This is the natural next automation target - an "Upload Firmware" button in
`AlphaBotAPI` that pushes both files over the same serial connection
`SerialManager` already owns, so a fresh board can be set up without
opening Thonny at all.

## Adding a new hardware block (e.g. a servo)

1. Create `web/js/blocks/servo.js`:
   ```js
   Blockly.Blocks['servo_set_angle'] = { /* ... */ };
   python.pythonGenerator.forBlock['servo_set_angle'] = function (block) { /* ... */ };

   EZBOTIX.registerCategory({
       name: "🦾 Servo",
       colour: 45,
       blocks: ["servo_set_angle"]
   });
   ```
2. Add its driver code to a new `firmware/hal_servo.py`, and add the import
   to `DeviceController.EXECUTION_HEADER` in `backend/device_controller.py`.
3. Add one `<script src="js/blocks/servo.js"></script>` line in `index.html`.

Nothing else changes - `toolbox.js` and `ui.js` pick it up automatically.

## Bugs fixed during this refactor

- **`stop_device` NameError**: the stop script called `onboard_led.value(0)`
  without importing `onboard_led` - every Stop press would fail on-device.
  Fixed in `DeviceController.stop_device`.
- **Inconsistent REPL entry**: `stop_device` used a different (fragile)
  method of talking to the REPL than `run_code`/`flash_code`. All three now
  share the same `_enter_raw_repl`/`_exit_raw_repl` helpers.
- **Save success notification showed red, not teal**: the original passed
  the string `"success"` as the `isError` flag (truthy), so a successful
  save flashed the error color. Fixed in `ui.js`.
- **DTR/RTS reset timing**: `dsrdtr`/`rtscts` are now passed to `serial.Serial()`
  at construction time instead of being set after the port is already open.
- **Keypad debounce**: `firmware/hal_keypad.py`'s `read_key()` is now
  edge-triggered - a held key is reported once (on the scan where the press
  is first detected), not on every scan, and a 20ms re-scan confirms the
  press is stable before it's accepted, filtering out mechanical contact
  bounce. `wait_for_key()` is unaffected functionally.
- **Offline editor**: Blockly no longer loads from `unpkg.com` at runtime.
  `blockly.min.js` and `python_compressed.js` (v13.1.1, pulled from the
  official `blockly` npm package) are now vendored under `web/lib/blockly/`
  and `index.html` references them locally, so the editor opens with no
  internet connection required.

## Known remaining issues (not yet addressed)

- `run_code`/`flash_code` don't read back any response from the board, so a
  traceback from bad block-generated code is currently invisible to the user.