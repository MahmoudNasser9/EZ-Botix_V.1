# =============================================================================
# pin_config.py — EZ-BOTIX Central Pin Configuration
# =============================================================================
#
# This is the SINGLE source of truth for ALL GPIO pin assignments on the
# EZ-BOTIX board (ESP32).
#
# HOW TO USE:
#   Every HAL driver imports from this file instead of hardcoding pin numbers.
#
#       from pin_config import PINS
#       my_pin = PINS["MOTOR_L_IN1"]
#
# HOW TO RECONFIGURE:
#   If you rewire a component to a different GPIO, change ONLY the value here.
#   You do NOT need to touch any HAL driver file.
#
# PIN MAP REFERENCE (ESP32 Dev Board):
#
#   GPIO  2  - Onboard LED (Active HIGH)
#   GPIO 12  - Keypad ROW 1
#   GPIO 13  - RGB LED Back  strip data (LED_DATA_B)  / Keypad ROW 0
#   GPIO 14  - Ultrasonic TRIGGER                      / Keypad ROW 2
#   GPIO 15  - RGB LED Front strip data (LED_DATA_F)
#   GPIO 17  - External status LED      (TX2, Active LOW pull-up)
#   GPIO 19  - Buzzer PWM               (passive, PULL_DOWN)
#   GPIO 21  - OLED SDA                 (I2C0)
#   GPIO 22  - OLED SCL                 (I2C0)
#   GPIO 23  - Button                   (external 10K pull-up to 3V3)
#   GPIO 25  - Motor Right IN3          / Keypad COL 1
#   GPIO 26  - Motor Right IN4          / Keypad COL 0
#   GPIO 27  - Ultrasonic ECHO          / Keypad ROW 3
#   GPIO 32  - Motor Left  IN1          / Keypad COL 3
#   GPIO 33  - Motor Left  IN2          / Keypad COL 2
#   GPIO 34  - IR Sensor   (input-only)
#
# NOTE: GPIOs 13, 14, 25, 26, 27, 32, 33 are SHARED between the
#       motor/ultrasonic drivers and the keypad. Ensure only one of
#       those two subsystems is active at a time.
# =============================================================================

PINS = {
    # ------------------------------------------------------------------
    # Onboard & Status LEDs
    # ------------------------------------------------------------------
    "LED_ONBOARD":      2,   # Active HIGH - standard ESP32 dev board LED
    "LED_EXTERNAL":     17,  # TX2 pin; Active LOW (InvertedLED, pull-up)

    # ------------------------------------------------------------------
    # Buzzer
    # ------------------------------------------------------------------
    "BUZZER":           19,  # Passive buzzer - PWM, PULL_DOWN to avoid hum

    # ------------------------------------------------------------------
    # Button
    # ------------------------------------------------------------------
    "BUTTON":           23,  # External 10K pull-up; reads 0 when pressed

    # ------------------------------------------------------------------
    # IR Obstacle Sensor
    # ------------------------------------------------------------------
    "IR_SENSOR":        34,  # GPIO34 is input-only on ESP32

    # ------------------------------------------------------------------
    # Ultrasonic Sensor (HC-SR04)
    # ------------------------------------------------------------------
    "ULTRASONIC_TRIG":  14,
    "ULTRASONIC_ECHO":  27,

    # ------------------------------------------------------------------
    # Motor Driver (DRV8833)
    # Left  motors  <- OUT3/OUT4 <- M_IN1 / M_IN2
    # Right motors  <- OUT1/OUT2 <- M_IN3 / M_IN4
    # ------------------------------------------------------------------
    "MOTOR_L_IN1":      32,
    "MOTOR_L_IN2":      33,
    "MOTOR_R_IN1":      25,
    "MOTOR_R_IN2":      26,

    # ------------------------------------------------------------------
    # RGB LED Strips (WS2812 / NeoPixel)
    # ------------------------------------------------------------------
    "RGB_FRONT":        15,  # LED_DATA_F - Front strip data line
    "RGB_BACK":         13,  # LED_DATA_B - Back  strip data line
    "RGB_NUM_LEDS":     8,   # Number of LEDs per strip

    # ------------------------------------------------------------------
    # OLED Display (SSD1306, 128x64, I2C0)
    # ------------------------------------------------------------------
    "OLED_SCL":         22,  # I2C0 clock
    "OLED_SDA":         21,  # I2C0 data

    # ------------------------------------------------------------------
    # Matrix Keypad (4x4)
    # Rows are outputs (driven HIGH one at a time)
    # Columns are inputs (PULL_DOWN; read HIGH when key pressed)
    # ------------------------------------------------------------------
    "KEYPAD_ROW0":      13,
    "KEYPAD_ROW1":      12,
    "KEYPAD_ROW2":      14,
    "KEYPAD_ROW3":      27,
    "KEYPAD_COL0":      26,
    "KEYPAD_COL1":      25,
    "KEYPAD_COL2":      33,
    "KEYPAD_COL3":      32,
}
