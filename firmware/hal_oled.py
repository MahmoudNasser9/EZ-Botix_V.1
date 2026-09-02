# hal_oled.py – EZ-BOTIX OLED HAL (Extended Animation Edition)
#
# Hardware Abstraction Layer for 128x64 I2C SSD1306 OLED Displays.
#
# Features:
#   • Scaled text rendering & automatic smart-fit text wrapping
#   • Pre-allocated bitmap framebuffers for 0-RAM-leak heartbeat graphics
#   • Modular eye animation engine inspired by RoboEyes & community styles:
#       - Look:      blink, double_blink, wink_left, wink_right
#       - Movement:  look_left, look_right, look_up, look_down,
#                    look_topleft, look_topright, look_botleft, look_botright
#       - Expression: happy, angry, angry_flash, sad, sad cry, sad Trembling, surprised, confused
#       - Special FX: spin, dizzy, sleepy, excited, So excited, flicker, glitch

import time
import framebuf
import math
import gc
from machine import Pin, I2C
from pin_config import PINS

try:
    import urandom as random
except ImportError:
    import random

try:
    import ssd1306
except ImportError:
    ssd1306 = None


# ==============================================================================
# BITMAP ASSETS
# ==============================================================================

HEART_BITMAPS = {
    "outline_32": bytearray([
        0x00, 0x00, 0x00, 0x00,  0x00, 0x00, 0x00, 0x00,  0x00, 0x00, 0x00, 0x00,  0x01, 0xf0, 0x0f, 0x80,
        0x06, 0x0c, 0x30, 0x60,  0x08, 0x02, 0x40, 0x10,  0x10, 0x01, 0x80, 0x08,  0x20, 0x00, 0x00, 0x04,
        0x20, 0x00, 0x00, 0x04,  0x40, 0x00, 0x00, 0x02,  0x40, 0x00, 0x00, 0x02,  0x40, 0x00, 0x00, 0x02,
        0x40, 0x00, 0x00, 0x02,  0x20, 0x00, 0x00, 0x04,  0x20, 0x00, 0x00, 0x04,  0x10, 0x00, 0x00, 0x08,
        0x08, 0x00, 0x00, 0x10,  0x04, 0x00, 0x00, 0x20,  0x02, 0x00, 0x00, 0x40,  0x01, 0x00, 0x00, 0x80,
        0x00, 0x80, 0x01, 0x00,  0x00, 0x40, 0x02, 0x00,  0x00, 0x20, 0x04, 0x00,  0x00, 0x10, 0x08, 0x00,
        0x00, 0x08, 0x10, 0x00,  0x00, 0x04, 0x20, 0x00,  0x00, 0x02, 0x40, 0x00,  0x00, 0x01, 0x80, 0x00,
        0x00, 0x00, 0x00, 0x00,  0x00, 0x00, 0x00, 0x00,  0x00, 0x00, 0x00, 0x00,  0x00, 0x00, 0x00, 0x00,
    ]),
    "filled_32": bytearray([
        0x00, 0x00, 0x00, 0x00,  0x00, 0x00, 0x00, 0x00,  0x01, 0xf0, 0x0f, 0x80,  0x03, 0xf8, 0x1f, 0xc0,
        0x07, 0xfc, 0x3f, 0xe0,  0x0f, 0xfe, 0x7f, 0xf0,  0x1f, 0xff, 0xff, 0xf8,  0x3f, 0xff, 0xff, 0xfc,
        0x3f, 0xff, 0xff, 0xfc,  0x7f, 0xff, 0xff, 0xfe,  0x7f, 0xff, 0xff, 0xfe,  0x7f, 0xff, 0xff, 0xfe,
        0x7f, 0xff, 0xff, 0xfe,  0x3f, 0xff, 0xff, 0xfc,  0x3f, 0xff, 0xff, 0xfc,  0x1f, 0xff, 0xff, 0xf8,
        0x0f, 0xff, 0xff, 0xf0,  0x07, 0xff, 0xff, 0xe0,  0x03, 0xff, 0xff, 0xc0,  0x01, 0xff, 0xff, 0x80,
        0x00, 0xff, 0xff, 0x00,  0x00, 0x7f, 0xfe, 0x00,  0x00, 0x3f, 0xfc, 0x00,  0x00, 0x1f, 0xf8, 0x00,
        0x00, 0x0f, 0xf0, 0x00,  0x00, 0x07, 0xe0, 0x00,  0x00, 0x03, 0xc0, 0x00,  0x00, 0x01, 0x80, 0x00,
        0x00, 0x00, 0x00, 0x00,  0x00, 0x00, 0x00, 0x00,  0x00, 0x00, 0x00, 0x00,  0x00, 0x00, 0x00, 0x00,
    ]),
    "outline_24": bytearray([
        0x00, 0x00, 0x00,  0x00, 0x00, 0x00,  0x00, 0x00, 0x00,  0x0f, 0x01, 0xe0,
        0x10, 0x83, 0x10,  0x20, 0x44, 0x08,  0x40, 0x28, 0x04,  0x40, 0x00, 0x04,
        0x40, 0x00, 0x04,  0x20, 0x00, 0x08,  0x20, 0x00, 0x08,  0x10, 0x00, 0x10,
        0x08, 0x00, 0x20,  0x04, 0x00, 0x40,  0x02, 0x00, 0x80,  0x01, 0x01, 0x00,
        0x00, 0x82, 0x00,  0x00, 0x44, 0x00,  0x00, 0x28, 0x00,  0x00, 0x10, 0x00,
        0x00, 0x00, 0x00,  0x00, 0x00, 0x00,  0x00, 0x00, 0x00,  0x00, 0x00, 0x00,
    ]),
    "filled_24": bytearray([
        0x00, 0x00, 0x00,  0x00, 0x00, 0x00,  0x0f, 0x01, 0xe0,  0x1f, 0x83, 0xf0,
        0x3f, 0xc7, 0xf8,  0x7f, 0xef, 0xfc,  0x7f, 0xff, 0xfc,  0x7f, 0xff, 0xfc,
        0x3f, 0xff, 0xf8,  0x3f, 0xff, 0xf8,  0x1f, 0xff, 0xf0,  0x0f, 0xff, 0xe0,
        0x07, 0xff, 0xc0,  0x03, 0xff, 0x80,  0x01, 0xff, 0x00,  0x00, 0xfe, 0x00,
        0x00, 0x7c, 0x00,  0x00, 0x38, 0x00,  0x00, 0x10, 0x00,  0x00, 0x00, 0x00,
        0x00, 0x00, 0x00,  0x00, 0x00, 0x00,  0x00, 0x00, 0x00,  0x00, 0x00, 0x00,
    ]),
    "outline_16": bytearray([
        0x00, 0x00,  0x00, 0x00,  0x38, 0x1c,  0x44, 0x22,  0x82, 0x41,  0x81, 0x81,  0x80, 0x01,  0x40, 0x02,
        0x20, 0x04,  0x10, 0x08,  0x08, 0x10,  0x04, 0x20,  0x02, 0x40,  0x01, 0x80,  0x00, 0x00,  0x00, 0x00,
    ]),
    "filled_16": bytearray([
        0x00, 0x00,  0x38, 0x1c,  0x7c, 0x3e,  0xfe, 0x7f,  0xff, 0xff,  0xff, 0xff,  0x7f, 0xfe,  0x3f, 0xfc,
        0x1f, 0xf8,  0x0f, 0xf0,  0x07, 0xe0,  0x03, 0xc0,  0x01, 0x80,  0x00, 0x00,  0x00, 0x00,  0x00, 0x00,
    ]),
    "outline_8": bytearray([
        0x00, 0x66, 0x99, 0x81, 0x42, 0x24, 0x18, 0x00
    ]),
}


# Eye geometry style configurations: (lx, ly, lw, lh, rx, ry, rw, rh, pupil_size)
EYE_STYLES = {
    "big_eyes":   (16, 12, 40, 40,  72, 12, 40, 40, 12),
    "wide_eyes":  (12, 20, 48, 28,  68, 20, 48, 28, 10),
    "tall_eyes":  (24,  8, 32, 48,  72,  8, 32, 48,  8),
    "cute_eyes":  (16,  8, 40, 48,  72,  8, 40, 48, 14),
    "small_eyes": (32, 20, 24, 28,  72, 20, 24, 28,  8),
}


# ==============================================================================
# ROBOT OLED HAL CLASS
# ==============================================================================

class RobotOLED:
    """MicroPython HAL driver for SSD1306 OLED screens (128x64 I2C)."""

    W = 128
    H = 64

    def __init__(self, scl_pin=None, sda_pin=None):
        if scl_pin is None:
            scl_pin = PINS["OLED_SCL"]
        if sda_pin is None:
            sda_pin = PINS["OLED_SDA"]
        self.display = None

        try:
            gc.collect()  # Garbage collect to maximize contiguous RAM

            self.i2c = I2C(0, scl=Pin(scl_pin), sda=Pin(sda_pin), freq=400000)
            if ssd1306 is not None:
                self.display = ssd1306.SSD1306_I2C(self.W, self.H, self.i2c)

            # Pre-allocate FrameBuffers for 0-leak bitmap drawing
            self.fb32  = framebuf.FrameBuffer(HEART_BITMAPS["outline_32"], 32, 32, framebuf.MONO_HLSB)
            self.fb32f = framebuf.FrameBuffer(HEART_BITMAPS["filled_32"],  32, 32, framebuf.MONO_HLSB)
            self.fb24  = framebuf.FrameBuffer(HEART_BITMAPS["outline_24"], 24, 24, framebuf.MONO_HLSB)
            self.fb24f = framebuf.FrameBuffer(HEART_BITMAPS["filled_24"],  24, 24, framebuf.MONO_HLSB)
            self.fb16  = framebuf.FrameBuffer(HEART_BITMAPS["outline_16"], 16, 16, framebuf.MONO_HLSB)
            self.fb16f = framebuf.FrameBuffer(HEART_BITMAPS["filled_16"],  16, 16, framebuf.MONO_HLSB)
            self.fb8   = framebuf.FrameBuffer(HEART_BITMAPS["outline_8"],   8,  8, framebuf.MONO_HLSB)

            self.clear()
        except Exception as err:
            print("OLED Init Error:", err)
            self.display = None

    # --------------------------------------------------------------------------
    # Core Display Primitives
    # --------------------------------------------------------------------------

    def clear(self):
        """Clears screen buffer and updates display."""
        if self.display:
            self.display.fill(0)
            self.display.show()

    # --------------------------------------------------------------------------
    # Text Rendering Engine
    # --------------------------------------------------------------------------

    def _draw_scaled_text(self, text, x, y, scale):
        """Renders string with scaled pixel characters."""
        d = self.display
        char_w = 8 * scale
        buf = bytearray(8)
        fb = framebuf.FrameBuffer(buf, 8, 8, framebuf.MONO_VLSB)

        for ci, ch in enumerate(text):
            cx = x + ci * char_w
            if cx + char_w > self.W:
                break
            fb.fill(0)
            fb.text(ch, 0, 0, 1)
            for py in range(8):
                for px in range(8):
                    if fb.pixel(px, py):
                        d.fill_rect(cx + px * scale, y + py * scale, scale, scale, 1)

    def _wrap_text(self, text, cols):
        """Splits input text into lines fitting within maximum column width."""
        raw_words = str(text).split()
        words = []
        for w in raw_words:
            while len(w) > cols and cols > 0:
                words.append(w[:cols])
                w = w[cols:]
            if w:
                words.append(w)

        lines, current = [], ""
        for word in words:
            test = (current + " " + word).strip() if current else word
            if len(test) <= cols:
                current = test
            else:
                lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines

    def show_text(self, text, size=2):
        """Displays text with explicit scale factor (1-4). Wraps lines automatically."""
        if not self.display:
            return
        scale = max(1, min(int(size), 4))
        char_w = 8 * scale
        char_h = 8 * scale
        cols = self.W // char_w
        rows = self.H // char_h

        lines = self._wrap_text(text, cols)[:rows]
        total_h = len(lines) * char_h
        y_start = max(0, (self.H - total_h) // 2)

        self.display.fill(0)
        for i, line in enumerate(lines):
            x = max(0, (self.W - len(line) * char_w) // 2)
            self._draw_scaled_text(line, x, y_start + i * char_h, scale)
        self.display.show()

    def show_text_fit(self, text):
        """Automatically calculates the largest font scale that fits full text on screen."""
        if not self.display:
            return
        text_str = str(text)
        raw_words = text_str.split()
        best_scale, best_lines = 1, [text_str]

        for scale in range(4, 0, -1):
            char_w = 8 * scale
            char_h = 8 * scale  # Define here so it is available for rows calculation
            cols = self.W // char_w
            rows = self.H // char_h
            if cols == 0:
                continue
            if scale > 1 and any(len(w) > cols for w in raw_words):
                continue

            lines = self._wrap_text(text_str, cols)
            if len(lines) <= rows:
                best_scale, best_lines = scale, lines
                break

        char_w = 8 * best_scale
        char_h = 8 * best_scale
        total_h = len(best_lines) * char_h
        y_start = max(0, (self.H - total_h) // 2)

        self.display.fill(0)
        for i, line in enumerate(best_lines):
            x = max(0, (self.W - len(line) * char_w) // 2)
            self._draw_scaled_text(line, x, y_start + i * char_h, best_scale)
        self.display.show()

    # --------------------------------------------------------------------------
    # Static Emoji Renderer
    # --------------------------------------------------------------------------

    def show_emoji(self, emoji_name):
        """Displays static predefined emoji shapes on display."""
        if not self.display:
            return
        self.display.fill(0)
        self._draw_emoji_internal(emoji_name)
        self.display.show()

    def show_text_and_emoji(self, text, emoji_name):
        """Displays text at the top of the screen and an emoji below it."""
        if not self.display:
            return
        self.display.fill(0)
        
        # Draw emoji
        self._draw_emoji_internal(emoji_name)
        
        # Draw text at the top
        text_str = str(text)
        scale = 2 if len(text_str) <= 8 else 1
        char_w = 8 * scale
        x = max(0, (self.W - len(text_str) * char_w) // 2)
        y = 0 if scale == 2 else 4
        
        # Clear a small background behind text just in case of overlap
        self.display.fill_rect(0, 0, self.W, 8 * scale, 0)
        self._draw_scaled_text(text_str, x, y, scale)
        
        self.display.show()

    def _draw_emoji_internal(self, emoji_name):
        d = self.display
        # Normalize: strip whitespace and lowercase. Keep underscores as-is since
        # emoji names use underscores (e.g. "angry_eyes", "hollow_eyes").
        name = str(emoji_name).strip().lower()

        if name == "heart":
            # Display a 48x48 heart to fit entirely in the white/blue section (y=16 to 63)
            # The top 16 pixels of the OLED are often a different color (yellow)
            for y in range(48):
                src_y = (y * 2) // 3
                start_x = -1
                for x in range(48):
                    src_x = (x * 2) // 3
                    if self.fb32f.pixel(src_x, src_y):
                        if start_x == -1: 
                            start_x = x
                    else:
                        if start_x != -1:
                            d.hline(40 + start_x, 16 + y, x - start_x, 1)
                            start_x = -1
                if start_x != -1:
                    d.hline(40 + start_x, 16 + y, 48 - start_x, 1)
        elif name == "angry_eyes":

            # Slanted heavy brows connected smoothly to narrowed eyes
            d.fill_rect(24, 40, 32, 16, 1); d.fill_rect(72, 40, 32, 16, 1)
            for i in range(8):
                d.line(16, 24 + i, 56, 40 + i, 1)
                d.line(112, 24 + i, 72, 40 + i, 1)
            # Add small angry pupils
            d.fill_rect(36, 48, 8, 8, 0); d.fill_rect(84, 48, 8, 8, 0)
        elif name == "hollow_eyes":
            # Give a robotic target / hollow pupil look
            d.fill_rect(16, 12, 40, 40, 1); d.fill_rect(72, 12, 40, 40, 1)
            d.fill_rect(24, 20, 24, 24, 0); d.fill_rect(80, 20, 24, 24, 0)
            d.fill_rect(32, 28,  8,  8, 1); d.fill_rect(88, 28,  8,  8, 1)
        elif name in EYE_STYLES:
            # Dynamically draw properly proportioned eyes with pupils based on config
            lx, ly, lw, lh, rx, ry, rw, rh, ps = EYE_STYLES[name]
            lpc_x = lx + (lw - ps) // 2
            lpc_y = ly + (lh - ps) // 2
            rpc_x = rx + (rw - ps) // 2
            rpc_y = ry + (rh - ps) // 2
            
            d.fill_rect(lx, ly, lw, lh, 1)
            d.fill_rect(rx, ry, rw, rh, 1)
            d.fill_rect(lpc_x, lpc_y, ps, ps, 0)
            d.fill_rect(rpc_x, rpc_y, ps, ps, 0)
            
            if name == "cute_eyes":
                # Add tiny white anime shine dots in the pupils
                d.fill_rect(lpc_x + 2, lpc_y + 2, 4, 4, 1)
                d.fill_rect(rpc_x + 2, rpc_y + 2, 4, 4, 1)
        else:
            d.text("?", 60, 28, 1)

    # --------------------------------------------------------------------------
    # Modular Eye Animation Engine
    # --------------------------------------------------------------------------

    def animate_eyes(self, style="big_eyes", animation="blink"):
        """Plays dynamic eye animations according to selected style and animation preset."""
        if not self.display:
            return

        geo = EYE_STYLES.get(style, EYE_STYLES["big_eyes"])
        lx, ly, lw, lh, rx, ry, rw, rh, ps = geo
        d = self.display

        lpc_x = lx + (lw - ps) // 2
        lpc_y = ly + (lh - ps) // 2
        rpc_x = rx + (rw - ps) // 2
        rpc_y = ry + (rh - ps) // 2

        # Drawing helpers for animation steps
        def draw_open(lpx=None, lpy=None, rpx=None, rpy=None):
            if lpx is None:
                lpx, lpy, rpx, rpy = lpc_x, lpc_y, rpc_x, rpc_y
            d.fill(0)
            d.fill_rect(lx, ly, lw, lh, 1); d.fill_rect(rx, ry, rw, rh, 1)
            d.fill_rect(lpx, lpy, ps, ps, 0); d.fill_rect(rpx, rpy, ps, ps, 0)
            d.show()

        def draw_squash(h_l, h_r=None):
            if h_r is None:
                h_r = h_l
            h_l, h_r = max(1, h_l), max(1, h_r)
            d.fill(0)
            ml = ly + (lh - h_l) // 2
            mr = ry + (rh - h_r) // 2
            d.fill_rect(lx, ml, lw, h_l, 1); d.fill_rect(rx, mr, rw, h_r, 1)
            d.show()

        def _blink_eye(squash_fn, steps=6):
            for i in range(steps, 0, -1):
                squash_fn(lh * i // steps)
                time.sleep_ms(25)
            time.sleep_ms(60)
            for i in range(1, steps + 1):
                squash_fn(lh * i // steps)
                time.sleep_ms(20)

        def _move_pupils(dx, dy, steps=5, hold_ms=400):
            for s in range(1, steps + 1):
                ox = dx * s // steps; oy = dy * s // steps
                draw_open(lpc_x + ox, lpc_y + oy, rpc_x + ox, rpc_y + oy)
                time.sleep_ms(35)
            time.sleep_ms(hold_ms)
            for s in range(steps - 1, -1, -1):
                ox = dx * s // steps; oy = dy * s // steps
                draw_open(lpc_x + ox, lpc_y + oy, rpc_x + ox, rpc_y + oy)
                time.sleep_ms(35)
            draw_open()

        # Initial resting state
        draw_open()
        time.sleep_ms(200)

        anim_key = str(animation).strip().lower().replace("_", " ")

        # --- BLINK & WINK ---
        if anim_key == "blink":
            _blink_eye(lambda h: draw_squash(h))
            draw_open()
        elif anim_key == "double blink":
            _blink_eye(lambda h: draw_squash(h))
            draw_open()
            time.sleep_ms(180)
            _blink_eye(lambda h: draw_squash(h))
            draw_open()
        elif anim_key == "wink left":
            for i in range(6, 0, -1):
                draw_squash(lh * i // 6, lh)
                time.sleep_ms(25)
            time.sleep_ms(80)
            for i in range(1, 7):
                draw_squash(lh * i // 6, lh)
                time.sleep_ms(20)
            draw_open()
        elif anim_key == "wink right":
            for i in range(6, 0, -1):
                draw_squash(lh, lh * i // 6)
                time.sleep_ms(25)
            time.sleep_ms(80)
            for i in range(1, 7):
                draw_squash(lh, lh * i // 6)
                time.sleep_ms(20)
            draw_open()

        # --- MOVEMENT / LOOK ---
        elif anim_key == "look left":     _move_pupils(-(lw // 2 - ps), 0)
        elif anim_key == "look right":    _move_pupils((lw // 2 - ps), 0)
        elif anim_key == "look up":       _move_pupils(0, -(lh // 2 - ps))
        elif anim_key == "look down":     _move_pupils(0, (lh // 2 - ps))
        elif anim_key == "look topleft":  _move_pupils(-(lw // 3), -(lh // 3))
        elif anim_key == "look topright": _move_pupils((lw // 3), -(lh // 3))
        elif anim_key == "look botleft":  _move_pupils(-(lw // 3), (lh // 3))
        elif anim_key == "look botright": _move_pupils((lw // 3), (lh // 3))

        # --- EXPRESSION / MOOD ---
        elif anim_key == "angry":
            self._anim_angry(d, draw_open)
        elif anim_key == "angry flash":
            self._anim_angry_flash(d, draw_open)
        elif anim_key == "sad":
            self._anim_sad(d, draw_open, lx, ly, lw, lh, rx, ry, rw, rh, ps, lpc_x, lpc_y, rpc_x, rpc_y)
        elif anim_key == "sad cry":
            self._anim_sad_cry(d, draw_open, lx, ly, lw, lh, rx, ry, rw, rh, ps, lpc_x, lpc_y, rpc_x, rpc_y)
        elif anim_key == "sad trembling":
            self._anim_sad_trembling(d, draw_open, lx, ly, lw, lh, rx, ry, rw, rh, ps, lpc_x, lpc_y, rpc_x, rpc_y)
        elif anim_key == "surprised":
            self._anim_surprised(d, draw_open, _blink_eye, draw_squash, lx, ly, lw, lh, rx, ry, rw, rh, ps, lpc_x, lpc_y, rpc_x, rpc_y)
        elif anim_key == "confused":
            self._anim_confused(d, draw_open, lx, ly, lw, lh, rx, ry, rw, rh, ps, lpc_x, lpc_y, rpc_x, rpc_y)

        # --- SPECIAL FX ---
        elif anim_key == "spin":
            self._anim_spin(draw_open, lw, lh, ps, lpc_x, lpc_y, rpc_x, rpc_y)
        elif anim_key == "dizzy":
            self._anim_dizzy(draw_open, lw, lh, ps, lpc_x, lpc_y, rpc_x, rpc_y)
        elif anim_key == "sleepy":
            self._anim_sleepy(d, draw_open, lx, ly, lw, lh, rx, ry, rw, rh)
        elif anim_key == "excited":
            self._anim_excited(d, draw_open, lx, ly, lw, lh, rx, ry, rw, rh, ps, lpc_x, lpc_y, rpc_x, rpc_y)
        elif anim_key == "so excited":
            self._anim_so_excited(d, draw_open, lx, ly, lw, lh, rx, ry, rw, rh, ps, lpc_x, lpc_y, rpc_x, rpc_y)
        elif anim_key == "flicker":
            self._anim_flicker(d, draw_open)
        elif anim_key == "glitch":
            self._anim_glitch(d, draw_open, lx, ly, lw, lh, rx, ry, rw, rh, ps, lpc_x, lpc_y, rpc_x, rpc_y)
        else:
            draw_open()

    # --------------------------------------------------------------------------
    # Private Animation Helper Routines
    # --------------------------------------------------------------------------

    def _anim_angry(self, d, draw_open):
        """Displays an angry expression by narrowing the eyes, dropping eyebrows, and shaking."""
        d.fill(0)
        d.fill_rect(24, 40, 32, 16, 1); d.fill_rect(72, 40, 32, 16, 1)
        d.show(); time.sleep_ms(350)

        for i in range(8):
            d.line(16, 24 + i, 56, 40 + i, 1)
            d.line(112, 24 + i, 72, 40 + i, 1)
        # Draw pupils AFTER brows so they are not overwritten
        d.fill_rect(36, 48, 8, 8, 0); d.fill_rect(84, 48, 8, 8, 0)
        d.show(); time.sleep_ms(250)

        for shake in range(6):
            offset = 6 if shake % 2 == 0 else -6
            d.fill(0)
            d.fill_rect(24 + offset, 40, 32, 16, 1)
            d.fill_rect(72 + offset, 40, 32, 16, 1)
            d.fill_rect(36 + offset, 48, 8, 8, 0)
            d.fill_rect(84 + offset, 48, 8, 8, 0)
            for i in range(8):
                d.line(16 + offset, 24 + i, 56 + offset, 40 + i, 1)
                d.line(112 + offset, 24 + i, 72 + offset, 40 + i, 1)
            d.show(); time.sleep_ms(45)

        d.fill(0)
        d.fill_rect(24, 40, 32, 16, 1); d.fill_rect(72, 40, 32, 16, 1)
        d.fill_rect(36, 48, 8, 8, 0); d.fill_rect(84, 48, 8, 8, 0)
        for i in range(8):
            d.line(16, 24 + i, 56, 40 + i, 1)
            d.line(112, 24 + i, 72, 40 + i, 1)
        d.show(); time.sleep_ms(800)
        draw_open()

    def _anim_angry_flash(self, d, draw_open):
        """Displays an angry expression and rapidly flashes the screen colors."""
        d.fill(0)
        d.fill_rect(24, 40, 32, 16, 1); d.fill_rect(72, 40, 32, 16, 1)
        d.fill_rect(36, 48, 8, 8, 0); d.fill_rect(84, 48, 8, 8, 0)
        for i in range(8):
            d.line(16, 24 + i, 56, 40 + i, 1)
            d.line(112, 24 + i, 72, 40 + i, 1)
        d.show(); time.sleep_ms(300)

        for _ in range(4):
            d.fill(1)
            d.fill_rect(24, 40, 32, 16, 0); d.fill_rect(72, 40, 32, 16, 0)
            d.fill_rect(36, 48, 8, 8, 1); d.fill_rect(84, 48, 8, 8, 1)
            for i in range(8):
                d.line(16, 24 + i, 56, 40 + i, 0)
                d.line(112, 24 + i, 72, 40 + i, 0)
            d.show(); time.sleep_ms(60)

            d.fill(0)
            d.fill_rect(24, 40, 32, 16, 1); d.fill_rect(72, 40, 32, 16, 1)
            d.fill_rect(36, 48, 8, 8, 0); d.fill_rect(84, 48, 8, 8, 0)
            for i in range(8):
                d.line(16, 24 + i, 56, 40 + i, 1)
                d.line(112, 24 + i, 72, 40 + i, 1)
            d.show(); time.sleep_ms(60)

        time.sleep_ms(700)
        draw_open()

    def _anim_sad(self, d, draw_open, lx, ly, lw, lh, rx, ry, rw, rh, ps, lpc_x, lpc_y, rpc_x, rpc_y):
        """Displays a sad expression by looking down and narrowing the eyes slightly."""
        steps = 6
        for s in range(1, steps + 1):
            oy = (lh // 4) * s // steps
            draw_open(lpc_x, lpc_y + oy, rpc_x, rpc_y + oy)
            time.sleep_ms(35)
        d.fill_rect(lx + lw - 8, ly, 8, 8, 0)
        d.fill_rect(rx, ry, 8, 8, 0)
        d.show(); time.sleep_ms(1000)
        for s in range(steps - 1, -1, -1):
            oy = (lh // 4) * s // steps
            draw_open(lpc_x, lpc_y + oy, rpc_x, rpc_y + oy)
            time.sleep_ms(35)
        draw_open()

    def _anim_sad_cry(self, d, draw_open, lx, ly, lw, lh, rx, ry, rw, rh, ps, lpc_x, lpc_y, rpc_x, rpc_y):
        """Displays a crying sad face with downward slanted eyebrows and tears."""
        slice_sz = 16
        steps = 6

        for s in range(1, steps + 1):
            d.fill(0)
            d.fill_rect(lx, ly, lw, lh, 1); d.fill_rect(rx, ry, rw, rh, 1)
            oy = (lh // 4) * s // steps
            d.fill_rect(lpc_x, lpc_y + oy, ps, ps, 0)
            d.fill_rect(rpc_x, rpc_y + oy, ps, ps, 0)
            curr_slice = slice_sz * s // steps
            for i in range(curr_slice):
                d.line(lx, ly + i, lx + curr_slice - i, ly, 0)
                d.line(rx + rw - 1, ly + i, rx + rw - 1 - (curr_slice - i), ly, 0)
            d.show(); time.sleep_ms(40)

        time.sleep_ms(300)

        tear_paths = [(lx + lw // 4, ly + lh), (rx + rw // 4, ry + rh), (lx + lw // 2, ly + lh)]
        for tx, ty in tear_paths:
            for drop in range(0, 16, 4):
                d.fill_rect(tx, ty + drop, 2, 2, 1)
                d.show(); time.sleep_ms(50)
                d.fill_rect(tx, ty + drop, 2, 2, 0)

        time.sleep_ms(300)

        for s in range(steps - 1, -1, -1):
            d.fill(0)
            d.fill_rect(lx, ly, lw, lh, 1); d.fill_rect(rx, ry, rw, rh, 1)
            oy = (lh // 4) * s // steps
            d.fill_rect(lpc_x, lpc_y + oy, ps, ps, 0)
            d.fill_rect(rpc_x, rpc_y + oy, ps, ps, 0)
            curr_slice = slice_sz * s // steps
            for i in range(curr_slice):
                d.line(lx, ly + i, lx + curr_slice - i, ly, 0)
                d.line(rx + rw - 1, ly + i, rx + rw - 1 - (curr_slice - i), ly, 0)
            d.show(); time.sleep_ms(40)

        draw_open()

    def _anim_sad_trembling(self, d, draw_open, lx, ly, lw, lh, rx, ry, rw, rh, ps, lpc_x, lpc_y, rpc_x, rpc_y):
        """Displays a trembling sad face to convey deep sadness."""
        slice_sz = 16
        steps = 6

        for s in range(1, steps + 1):
            d.fill(0)
            d.fill_rect(lx, ly, lw, lh, 1); d.fill_rect(rx, ry, rw, rh, 1)
            oy = (lh // 4) * s // steps
            d.fill_rect(lpc_x, lpc_y + oy, ps, ps, 0)
            d.fill_rect(rpc_x, rpc_y + oy, ps, ps, 0)
            curr_slice = slice_sz * s // steps
            for i in range(curr_slice):
                d.line(lx, ly + i, lx + curr_slice - i, ly, 0)
                d.line(rx + rw - 1, ly + i, rx + rw - 1 - (curr_slice - i), ly, 0)
            d.show(); time.sleep_ms(40)

        time.sleep_ms(300)

        for shake in range(12):
            offset = 2 if shake % 2 == 0 else -2
            d.fill(0)
            d.fill_rect(lx + offset, ly, lw, lh, 1); d.fill_rect(rx + offset, ry, rw, rh, 1)
            d.fill_rect(lpc_x + offset, lpc_y + (lh // 4), ps, ps, 0)
            d.fill_rect(rpc_x + offset, rpc_y + (lh // 4), ps, ps, 0)
            for i in range(slice_sz):
                d.line(lx + offset, ly + i, lx + offset + slice_sz - i, ly, 0)
                d.line(rx + offset + rw - 1, ly + i, rx + offset + rw - 1 - (slice_sz - i), ly, 0)
            d.show(); time.sleep_ms(40)

        time.sleep_ms(500)

        for s in range(steps - 1, -1, -1):
            d.fill(0)
            d.fill_rect(lx, ly, lw, lh, 1); d.fill_rect(rx, ry, rw, rh, 1)
            oy = (lh // 4) * s // steps
            d.fill_rect(lpc_x, lpc_y + oy, ps, ps, 0)
            d.fill_rect(rpc_x, rpc_y + oy, ps, ps, 0)
            curr_slice = slice_sz * s // steps
            for i in range(curr_slice):
                d.line(lx, ly + i, lx + curr_slice - i, ly, 0)
                d.line(rx + rw - 1, ly + i, rx + rw - 1 - (curr_slice - i), ly, 0)
            d.show(); time.sleep_ms(40)

        draw_open()

    def _anim_so_excited(self, d, draw_open, lx, ly, lw, lh, rx, ry, rw, rh, ps, lpc_x, lpc_y, rpc_x, rpc_y):
        """Displays bouncing eyes with beautiful starry pupils."""
        star_size = int(ps * 1.4)  # Make the star slightly larger than the normal pupil
        for _ in range(6):
            for oy in [-6, -10, -6, 0, 4, 0]:
                d.fill(0)
                d.fill_rect(lx, ly + oy, lw, lh, 1)
                d.fill_rect(rx, ry + oy, rw, rh, 1)

                for cx, cy in [(lpc_x + ps // 2, lpc_y + ps // 2 + oy),
                               (rpc_x + ps // 2, rpc_y + ps // 2 + oy)]:
                    
                    # Draw a perfect 4-point diamond star pupil
                    for i in range(star_size):
                        # Calculate tapering width for the star's arms
                        width = max(1, (star_size - i) // 2)
                        
                        # Vertical arms (Top and Bottom)
                        d.fill_rect(cx - width, cy - i, width * 2, 1, 0)
                        d.fill_rect(cx - width, cy + i, width * 2, 1, 0)
                        
                        # Horizontal arms (Left and Right)
                        d.fill_rect(cx - i, cy - width, 1, width * 2, 0)
                        d.fill_rect(cx + i, cy - width, 1, width * 2, 0)
                        
                    # Add a tiny white sparkle in the exact center of the dark star
                    d.fill_rect(cx - 1, cy - 1, 2, 2, 1)

                d.show(); time.sleep_ms(40)
        draw_open()

    def _anim_surprised(self, d, draw_open, blink_eye, draw_squash, lx, ly, lw, lh, rx, ry, rw, rh, ps, lpc_x, lpc_y, rpc_x, rpc_y):
        """Displays a surprised expression with expanded eyes and tiny pupils."""
        d.fill(0)
        extra = 8
        d.fill_rect(lx - 2, ly - extra, lw + 4, lh + extra * 2, 1)
        d.fill_rect(rx - 2, ry - extra, rw + 4, rh + extra * 2, 1)
        half = ps // 2
        d.fill_rect(lpc_x + half // 2, lpc_y + half // 2, half, half, 0)
        d.fill_rect(rpc_x + half // 2, rpc_y + half // 2, half, half, 0)
        d.show(); time.sleep_ms(700)
        blink_eye(lambda h: draw_squash(h))
        draw_open()

    def _anim_confused(self, d, draw_open, lx, ly, lw, lh, rx, ry, rw, rh, ps, lpc_x, lpc_y, rpc_x, rpc_y):
        """Shakes the eyes back and forth quickly to convey confusion."""
        for _ in range(3):
            for ox in [-8, 8, -6, 6, -3, 3, 0]:
                d.fill(0)
                d.fill_rect(lx + ox, ly, lw, lh, 1)
                d.fill_rect(rx + ox, ry, rw, rh, 1)
                d.fill_rect(lpc_x + ox, lpc_y, ps, ps, 0)
                d.fill_rect(rpc_x + ox, rpc_y, ps, ps, 0)
                d.show()
                time.sleep_ms(40)
        draw_open()

    def _anim_spin(self, draw_open, lw, lh, ps, lpc_x, lpc_y, rpc_x, rpc_y):
        """Spins the pupils in a circular motion."""
        r = max(2, min(lw, lh) // 2 - ps - 2)
        cx_l, cy_l = lpc_x + ps // 2, lpc_y + ps // 2
        cx_r, cy_r = rpc_x + ps // 2, rpc_y + ps // 2  # Centre of each eye's pupil zone
        for i in range(25):
            angle = (2 * math.pi * i) / 20
            ox = int(r * math.cos(angle))
            oy = int(r * math.sin(angle))
            draw_open(cx_l - ps // 2 + ox, cy_l - ps // 2 + oy,
                      cx_r - ps // 2 + ox, cy_r - ps // 2 + oy)
            time.sleep_ms(35)
        draw_open()

    def _anim_dizzy(self, draw_open, lw, lh, ps, lpc_x, lpc_y, rpc_x, rpc_y):
        """Spins the pupils in a decreasing spiral to simulate dizziness."""
        for _ in range(2):  # Two full spiral repetitions
            for i in range(20):
                angle = (2 * math.pi * i) / 20
                r = int((1 - i / 20) * (min(lw, lh) // 2 - ps - 2))
                ox = int(r * math.cos(angle))
                oy = int(r * math.sin(angle))
                draw_open(lpc_x + ox, lpc_y + oy, rpc_x + ox, rpc_y + oy)
                time.sleep_ms(30)
        draw_open()

    def _anim_sleepy(self, d, draw_open, lx, ly, lw, lh, rx, ry, rw, rh):
        """Slowly closes the eyes and draws 'Z's to simulate sleeping."""
        for h in range(lh, 0, -max(1, lh // 10)):
            d.fill(0)
            d.fill_rect(lx, ly + lh - h, lw, h, 1)
            d.fill_rect(rx, ry + rh - h, rw, h, 1)
            d.show(); time.sleep_ms(70)
        for i in range(3):
            self._draw_scaled_text("z", 70 + (i * 10), 30 - (i * 10), i + 1)
            d.show()
            time.sleep_ms(700)
        for h in range(1, lh + 1, max(1, lh // 6)):
            d.fill(0)
            d.fill_rect(lx, ly + lh - h, lw, h, 1)
            d.fill_rect(rx, ry + rh - h, rw, h, 1)
            d.show(); time.sleep_ms(40)
        draw_open()

    def _anim_excited(self, d, draw_open, lx, ly, lw, lh, rx, ry, rw, rh, ps, lpc_x, lpc_y, rpc_x, rpc_y):
        """Bounces the eyes up and down rapidly."""
        for _ in range(4):
            for oy in [-6, -10, -6, 0, 4, 0]:
                d.fill(0)
                d.fill_rect(lx, ly + oy, lw, lh, 1)
                d.fill_rect(rx, ry + oy, rw, rh, 1)
                d.fill_rect(lpc_x, lpc_y + oy, ps, ps, 0)
                d.fill_rect(rpc_x, rpc_y + oy, ps, ps, 0)
                d.show(); time.sleep_ms(40)
        draw_open()
        
    def _anim_flicker(self, d, draw_open):
        """Flickers the eyes on and off randomly."""
        for _ in range(15):
            if random.getrandbits(1):
                draw_open()
            else:
                d.fill(0); d.show()
            time.sleep_ms(random.randint(30, 90))
        draw_open()

    def _anim_glitch(self, d, draw_open, lx, ly, lw, lh, rx, ry, rw, rh, ps, lpc_x, lpc_y, rpc_x, rpc_y):
        """Displaces the eyes randomly to simulate a digital glitch."""
        for _ in range(12):
            d.fill(0)
            shift_l = random.randint(-12, 12)
            shift_r = random.randint(-12, 12)
            d.fill_rect(max(0, lx + shift_l), ly, lw, lh, 1)
            d.fill_rect(max(0, rx + shift_r), ry, rw, rh, 1)
            d.fill_rect(max(0, lpc_x + shift_l), lpc_y, ps, ps, 0)
            d.fill_rect(max(0, rpc_x + shift_r), rpc_y, ps, ps, 0)
            d.show(); time.sleep_ms(50)
        draw_open()

    # --------------------------------------------------------------------------
    # Heartbeat Animation Engine
    # --------------------------------------------------------------------------

    def animate_heartbeat(self, size="medium", style="double_hollow"):
        """Plays a heartbeat pulse animation using pre-allocated memory framebuffers."""
        if not self.display:
            return
        d = self.display

        dim_map = {
            "large":  (32, 24, 16),
            "medium": (24, 16, 8),
            "small":  (16, 8, 8)
        }
        M, S, SS = dim_map.get(size, (24, 16, 8))

        is_filled = (style == "single_filled")
        is_double = (style == "double_hollow")

        def get_fb(dim, filled):
            if filled:
                if dim == 32: return self.fb32f
                if dim == 24: return self.fb24f
                return self.fb16f
            else:
                if dim == 32: return self.fb32
                if dim == 24: return self.fb24
                if dim == 8:  return self.fb8
                return self.fb16

        fb_main   = get_fb(M, is_filled)
        fb_sub    = get_fb(S, is_filled)
        fb_subsub = get_fb(SS, False)

        cx_main = 56 if is_double else 64
        cy_main = 30 if is_double else 32
        cx_sub  = 76
        cy_sub  = 40

        def draw_pulse(is_peak, thicken):
            d.fill(0)
            if is_double:
                if is_peak:
                    d.blit(fb_sub, cx_sub - S // 2, cy_sub - S // 2, 0)
                    if thicken:
                        d.blit(fb_sub, cx_sub - S // 2 + 1, cy_sub - S // 2, 0)
                        d.blit(fb_sub, cx_sub - S // 2, cy_sub - S // 2 + 1, 0)
                    d.blit(fb_main, cx_main - M // 2, cy_main - M // 2, 0)
                    if thicken:
                        d.blit(fb_main, cx_main - M // 2 + 1, cy_main - M // 2, 0)
                        d.blit(fb_main, cx_main - M // 2, cy_main - M // 2 + 1, 0)
                else:
                    d.blit(fb_subsub, cx_sub - SS // 2, cy_sub - SS // 2, 0)
                    if thicken:
                        d.blit(fb_subsub, cx_sub - SS // 2 + 1, cy_sub - SS // 2, 0)
                        d.blit(fb_subsub, cx_sub - SS // 2, cy_sub - SS // 2 + 1, 0)
                    d.blit(fb_sub, cx_main - S // 2, cy_main - S // 2, 0)
                    if thicken:
                        d.blit(fb_sub, cx_main - S // 2 + 1, cy_main - S // 2, 0)
                        d.blit(fb_sub, cx_main - S // 2, cy_main - S // 2 + 1, 0)
            else:
                if is_peak:
                    d.blit(fb_main, cx_main - M // 2, cy_main - M // 2, 0)
                    if thicken and not is_filled:
                        d.blit(fb_main, cx_main - M // 2 + 1, cy_main - M // 2, 0)
                        d.blit(fb_main, cx_main - M // 2, cy_main - M // 2 + 1, 0)
                else:
                    d.blit(fb_sub, cx_main - S // 2, cy_main - S // 2, 0)
                    if thicken and not is_filled:
                        d.blit(fb_sub, cx_main - S // 2 + 1, cy_main - S // 2, 0)
                        d.blit(fb_sub, cx_main - S // 2, cy_main - S // 2 + 1, 0)
            d.show()

        # Execute "Lub-dub" double pulse rhythm
        for _ in range(4):
            draw_pulse(False, False)
            time.sleep_ms(150)
            draw_pulse(True, True)
            time.sleep_ms(150)
            draw_pulse(False, False)
            time.sleep_ms(150)
            draw_pulse(True, True)
            time.sleep_ms(400)

        d.fill(0)
        d.show()


# ==============================================================================
# GLOBAL INSTANCE (REPL / MICROPYTHON EXECUTION CONTEXT)
# ==============================================================================

oled = RobotOLED()