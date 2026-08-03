# hal_oled.py  –  EZ-BOTIX OLED HAL  (Extended Animation Edition)
#
# Animations inspired by:
#   • RoboEyes (FluxGarage / mchobby MicroPython port)
#   • Intellar, SpiderMaf, AbdulsalamAbbod, Vinny, Picaio community styles
#
# animate_eyes(style, animation) — full list of animations:
#   LOOK ANIMATIONS   : blink, double_blink, wink_left, wink_right
#   MOVEMENT          : look_left, look_right, look_up, look_down
#                       look_topleft, look_topright, look_botleft, look_botright
#   MOOD / EXPRESSION : happy, angry, sad, surprised, confused
#   SPECIAL FX        : spin, dizzy, sleepy, excited, flicker, glitch

from machine import Pin, I2C
import time
import framebuf

try:
    import ssd1306
except ImportError:
    pass

HEART_32 = bytearray([
    0x00,0x00,0x00,0x00, 0x00,0x00,0x00,0x00, 0x00,0x00,0x00,0x00, 0x01,0xf0,0x0f,0x80,
    0x06,0x0c,0x30,0x60, 0x08,0x02,0x40,0x10, 0x10,0x01,0x80,0x08, 0x20,0x00,0x00,0x04,
    0x20,0x00,0x00,0x04, 0x40,0x00,0x00,0x02, 0x40,0x00,0x00,0x02, 0x40,0x00,0x00,0x02,
    0x40,0x00,0x00,0x02, 0x20,0x00,0x00,0x04, 0x20,0x00,0x00,0x04, 0x10,0x00,0x00,0x08,
    0x08,0x00,0x00,0x10, 0x04,0x00,0x00,0x20, 0x02,0x00,0x00,0x40, 0x01,0x00,0x00,0x80,
    0x00,0x80,0x01,0x00, 0x00,0x40,0x02,0x00, 0x00,0x20,0x04,0x00, 0x00,0x10,0x08,0x00,
    0x00,0x08,0x10,0x00, 0x00,0x04,0x20,0x00, 0x00,0x02,0x40,0x00, 0x00,0x01,0x80,0x00,
    0x00,0x00,0x00,0x00, 0x00,0x00,0x00,0x00, 0x00,0x00,0x00,0x00, 0x00,0x00,0x00,0x00
])
HEART_24 = bytearray([
    0x00,0x00,0x00, 0x00,0x00,0x00, 0x00,0x00,0x00, 0x0f,0x01,0xe0,
    0x10,0x83,0x10, 0x20,0x44,0x08, 0x40,0x28,0x04, 0x40,0x00,0x04,
    0x40,0x00,0x04, 0x20,0x00,0x08, 0x20,0x00,0x08, 0x10,0x00,0x10,
    0x08,0x00,0x20, 0x04,0x00,0x40, 0x02,0x00,0x80, 0x01,0x01,0x00,
    0x00,0x82,0x00, 0x00,0x44,0x00, 0x00,0x28,0x00, 0x00,0x10,0x00,
    0x00,0x00,0x00, 0x00,0x00,0x00, 0x00,0x00,0x00, 0x00,0x00,0x00
])
HEART_16 = bytearray([
    0x00,0x00, 0x00,0x00, 0x38,0x1c, 0x44,0x22, 0x82,0x41, 0x81,0x81, 0x80,0x01, 0x40,0x02,
    0x20,0x04, 0x10,0x08, 0x08,0x10, 0x04,0x20, 0x02,0x40, 0x01,0x80, 0x00,0x00, 0x00,0x00
])
HEART_8 = bytearray([0x00, 0x66, 0x99, 0x81, 0x42, 0x24, 0x18, 0x00])

HEART_32_FILLED = bytearray([
    0x00,0x00,0x00,0x00, 0x00,0x00,0x00,0x00, 0x01,0xf0,0x0f,0x80, 0x03,0xf8,0x1f,0xc0,
    0x07,0xfc,0x3f,0xe0, 0x0f,0xfe,0x7f,0xf0, 0x1f,0xff,0xff,0xf8, 0x3f,0xff,0xff,0xfc,
    0x3f,0xff,0xff,0xfc, 0x7f,0xff,0xff,0xfe, 0x7f,0xff,0xff,0xfe, 0x7f,0xff,0xff,0xfe,
    0x7f,0xff,0xff,0xfe, 0x3f,0xff,0xff,0xfc, 0x3f,0xff,0xff,0xfc, 0x1f,0xff,0xff,0xf8,
    0x0f,0xff,0xff,0xf0, 0x07,0xff,0xff,0xe0, 0x03,0xff,0xff,0xc0, 0x01,0xff,0xff,0x80,
    0x00,0xff,0xff,0x00, 0x00,0x7f,0xfe,0x00, 0x00,0x3f,0xfc,0x00, 0x00,0x1f,0xf8,0x00,
    0x00,0x0f,0xf0,0x00, 0x00,0x07,0xe0,0x00, 0x00,0x03,0xc0,0x00, 0x00,0x01,0x80,0x00,
    0x00,0x00,0x00,0x00, 0x00,0x00,0x00,0x00, 0x00,0x00,0x00,0x00, 0x00,0x00,0x00,0x00
])
HEART_24_FILLED = bytearray([
    0x00,0x00,0x00, 0x00,0x00,0x00, 0x0f,0x01,0xe0, 0x1f,0x83,0xf0,
    0x3f,0xc7,0xf8, 0x7f,0xef,0xfc, 0x7f,0xff,0xfc, 0x7f,0xff,0xfc,
    0x3f,0xff,0xf8, 0x3f,0xff,0xf8, 0x1f,0xff,0xf0, 0x0f,0xff,0xe0,
    0x07,0xff,0xc0, 0x03,0xff,0x80, 0x01,0xff,0x00, 0x00,0xfe,0x00,
    0x00,0x7c,0x00, 0x00,0x38,0x00, 0x00,0x10,0x00, 0x00,0x00,0x00,
    0x00,0x00,0x00, 0x00,0x00,0x00, 0x00,0x00,0x00, 0x00,0x00,0x00
])
HEART_16_FILLED = bytearray([
    0x00,0x00, 0x38,0x1c, 0x7c,0x3e, 0xfe,0x7f, 0xff,0xff, 0xff,0xff, 0x7f,0xfe, 0x3f,0xfc,
    0x1f,0xf8, 0x0f,0xf0, 0x07,0xe0, 0x03,0xc0, 0x01,0x80, 0x00,0x00, 0x00,0x00, 0x00,0x00
])

class RobotOLED:
    W = 128
    H = 64

    def __init__(self, scl_pin=22, sda_pin=21):
        try:
            import gc
            gc.collect() # Clean memory to prevent fragmentation
            self.i2c = I2C(0, scl=Pin(scl_pin), sda=Pin(sda_pin), freq=400000)
            self.display = ssd1306.SSD1306_I2C(self.W, self.H, self.i2c)
            
            # PRE-ALLOCATING MEMORY SO IT NEVER LEAKS OR CRASHES
            self.fb32 = framebuf.FrameBuffer(HEART_32, 32, 32, framebuf.MONO_HLSB)
            self.fb32f = framebuf.FrameBuffer(HEART_32_FILLED, 32, 32, framebuf.MONO_HLSB)
            self.fb24 = framebuf.FrameBuffer(HEART_24, 24, 24, framebuf.MONO_HLSB)
            self.fb24f = framebuf.FrameBuffer(HEART_24_FILLED, 24, 24, framebuf.MONO_HLSB)
            self.fb16 = framebuf.FrameBuffer(HEART_16, 16, 16, framebuf.MONO_HLSB)
            self.fb16f = framebuf.FrameBuffer(HEART_16_FILLED, 16, 16, framebuf.MONO_HLSB)
            self.fb8 = framebuf.FrameBuffer(HEART_8, 8, 8, framebuf.MONO_HLSB) 
            
            self.clear()
        except Exception as e:
            print("OLED Init Error:", e)
            self.display = None

    # ------------------------------------------------------------------ helpers

    def clear(self):
        if self.display:
            self.display.fill(0)
            self.display.show()

    def _draw_scaled_text(self, text, x, y, scale):
        d = self.display
        char_w = 8 * scale
        for ci, ch in enumerate(text):
            cx = x + ci * char_w
            if cx + char_w > self.W:
                break
            buf = bytearray(8)
            fb = framebuf.FrameBuffer(buf, 8, 8, framebuf.MONO_VLSB)
            fb.fill(0)
            fb.text(ch, 0, 0, 1)
            for py in range(8):
                for px in range(8):
                    if fb.pixel(px, py):
                        d.fill_rect(cx + px * scale, y + py * scale, scale, scale, 1)

    def show_text(self, text, size=2):
        if not self.display:
            return
        scale = max(1, min(int(size), 4))
        char_w = 8 * scale
        char_h = 8 * scale
        cols = self.W // char_w
        rows = self.H // char_h
        
        words = []
        for w in str(text).split():
            while len(w) > cols and cols > 0:
                words.append(w[:cols])
                w = w[cols:]
            if w:
                words.append(w)

        lines, current = [], ""
        for word in words:
            if not current:
                current = word
            elif len(current) + 1 + len(word) <= cols:
                current += " " + word
            else:
                lines.append(current)
                current = word
        if current:
            lines.append(current)
        lines = lines[:rows]
        total_h = len(lines) * char_h
        y_start = max(0, (self.H - total_h) // 2)
        self.display.fill(0)
        for i, line in enumerate(lines):
            x = max(0, (self.W - len(line) * char_w) // 2)
            self._draw_scaled_text(line, x, y_start + i * char_h, scale)
        self.display.show()

    def show_text_fit(self, text):
        if not self.display:
            return
        text = str(text)
        raw_words = text.split()
        best_scale, best_lines = 1, [text]
        for scale in range(4, 0, -1):
            char_w = 8 * scale
            char_h = 8 * scale
            cols = self.W // char_w
            rows = self.H // char_h
            if cols == 0: continue
            if scale > 1 and any(len(w) > cols for w in raw_words): continue

            words = []
            for w in raw_words:
                while len(w) > cols and cols > 0:
                    words.append(w[:cols])
                    w = w[cols:]
                if w: words.append(w)

            lines, current = [], ""
            for word in words:
                test = (current + " " + word).strip()
                if len(test) <= cols:
                    current = test
                else:
                    if current: lines.append(current)
                    current = word
            if current: lines.append(current)
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

    def show_emoji(self, emoji_name):
        if not self.display: return
        d = self.display
        d.fill(0)
        
        if emoji_name == "heart":
            # Safely using the pre-allocated buffers
            d.blit(self.fb24, 66, 28, 0)
            d.blit(self.fb24, 67, 28, 0)
            d.blit(self.fb24, 66, 29, 0)
            
            d.blit(self.fb32, 42, 16, 0)
            d.blit(self.fb32, 43, 16, 0)
            d.blit(self.fb32, 42, 17, 0)
        elif emoji_name == "cute_eyes":
            d.fill_rect(16, 8, 40, 48, 1); d.fill_rect(72, 8, 40, 48, 1)
            d.fill_rect(40, 16, 16, 16, 0); d.fill_rect(96, 16, 16, 16, 0)
        elif emoji_name == "angry_eyes":
            for i in range(5):
                d.line(16, 16+i, 56, 40+i, 1); d.line(112, 16+i, 72, 40+i, 1)
            d.fill_rect(24, 40, 32, 16, 1); d.fill_rect(72, 40, 32, 16, 1)
        elif emoji_name == "big_eyes":
            d.fill_rect(16, 16, 40, 32, 1); d.fill_rect(72, 16, 40, 32, 1)
        elif emoji_name == "hollow_eyes":
            d.fill_rect(16, 12, 40, 40, 1); d.fill_rect(24, 20, 24, 24, 0)
            d.fill_rect(32, 28,  8,  8, 1); d.fill_rect(72, 12, 40, 40, 1)
            d.fill_rect(80, 20, 24, 24, 0); d.fill_rect(88, 28,  8,  8, 1)
        elif emoji_name == "wide_eyes":
            d.fill_rect(12, 24, 48, 24, 1); d.fill_rect(68, 24, 48, 24, 1)
        elif emoji_name == "tall_eyes":
            d.fill_rect(24,  8, 32, 48, 1); d.fill_rect(36, 16,  8, 32, 0)
            d.fill_rect(72,  8, 32, 48, 1); d.fill_rect(84, 16,  8, 32, 0)
        elif emoji_name == "small_eyes":
            d.fill_rect(32, 24, 24, 24, 1); d.fill_rect(72, 24, 24, 24, 1)
        else:
            d.text("?", 60, 28, 1)
        d.show()

    def animate_eyes(self, style="big_eyes", animation="blink"):
        if not self.display: return

        STYLES = {
            "big_eyes":    (16, 12, 40, 40, 72, 12, 40, 40, 12),
            "wide_eyes":   (12, 20, 48, 28, 68, 20, 48, 28, 10),
            "tall_eyes":   (24,  8, 32, 48, 72,  8, 32, 48,  8),
            "cute_eyes":   (16,  8, 40, 48, 72,  8, 40, 48, 14),
            "small_eyes":  (32, 20, 24, 28, 72, 20, 24, 28,  8),
        }
        geo = STYLES.get(style, STYLES["big_eyes"])
        lx, ly, lw, lh, rx, ry, rw, rh, ps = geo
        d = self.display

        lpc_x = lx + (lw - ps) // 2
        lpc_y = ly + (lh - ps) // 2
        rpc_x = rx + (rw - ps) // 2
        rpc_y = ry + (rh - ps) // 2

        def draw_open(lpx=None, lpy=None, rpx=None, rpy=None):
            if lpx is None: lpx, lpy, rpx, rpy = lpc_x, lpc_y, rpc_x, rpc_y
            d.fill(0)
            d.fill_rect(lx, ly, lw, lh, 1); d.fill_rect(rx, ry, rw, rh, 1)
            d.fill_rect(lpx, lpy, ps, ps, 0); d.fill_rect(rpx, rpy, ps, ps, 0)
            d.show()

        def draw_squash(h_l, h_r=None, lpx=None, lpy=None, rpx=None, rpy=None):
            if h_r is None: h_r = h_l
            if lpx is None: lpx, lpy, rpx, rpy = lpc_x, lpc_y, rpc_x, rpc_y
            h_l, h_r = max(1, h_l), max(1, h_r)
            d.fill(0)
            ml = ly + (lh - h_l) // 2; mr = ry + (rh - h_r) // 2
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

        draw_open()
        time.sleep_ms(200)

        if animation == "blink":
            _blink_eye(lambda h: draw_squash(h))
            draw_open()
        elif animation == "double_blink":
            _blink_eye(lambda h: draw_squash(h))
            draw_open(); time.sleep_ms(180)
            _blink_eye(lambda h: draw_squash(h))
            draw_open()
        elif animation == "wink_left":
            for i in range(6, 0, -1):
                draw_squash(lh * i // 6, lh)
                time.sleep_ms(25)
            time.sleep_ms(80)
            for i in range(1, 7):
                draw_squash(lh * i // 6, lh)
                time.sleep_ms(20)
            draw_open()
        elif animation == "wink_right":
            for i in range(6, 0, -1):
                draw_squash(lh, lh * i // 6)
                time.sleep_ms(25)
            time.sleep_ms(80)
            for i in range(1, 7):
                draw_squash(lh, lh * i // 6)
                time.sleep_ms(20)
            draw_open()

        elif animation == "look_left": _move_pupils(-(lw // 2 - ps), 0)
        elif animation == "look_right": _move_pupils( (lw // 2 - ps), 0)
        elif animation == "look_up": _move_pupils(0, -(lh // 2 - ps))
        elif animation == "look_down": _move_pupils(0,  (lh // 2 - ps))
        elif animation == "look_topleft": _move_pupils(-(lw // 3), -(lh // 3))
        elif animation == "look_topright": _move_pupils( (lw // 3), -(lh // 3))
        elif animation == "look_botleft": _move_pupils(-(lw // 3),  (lh // 3))
        elif animation == "look_botright": _move_pupils( (lw // 3),  (lh // 3))

        elif animation == "angry":
            # 1. Eyes narrow into flat rectangles (suspicion)
            d.fill(0)
            d.fill_rect(24, 40, 32, 16, 1)
            d.fill_rect(72, 40, 32, 16, 1)
            d.show()
            time.sleep_ms(350)
            
            # 2. Heavy brows slam down!
            for i in range(5):
                d.line(16, 16+i, 56, 40+i, 1)
                d.line(112, 16+i, 72, 40+i, 1)
            d.show()
            time.sleep_ms(250)
            
            # 3. Shake violently with rage!
            for shake in range(6):
                offset = 6 if shake % 2 == 0 else -6
                d.fill(0)
                # Draw shifted eyes
                d.fill_rect(24 + offset, 40, 32, 16, 1)
                d.fill_rect(72 + offset, 40, 32, 16, 1)
                # Draw shifted brows
                for i in range(5):
                    d.line(16 + offset, 16+i, 56 + offset, 40+i, 1)
                    d.line(112 + offset, 16+i, 72 + offset, 40+i, 1)
                d.show()
                time.sleep_ms(45)
            
            # 4. Hold the angry glare
            d.fill(0)
            d.fill_rect(24, 40, 32, 16, 1)
            d.fill_rect(72, 40, 32, 16, 1)
            for i in range(5):
                d.line(16, 16+i, 56, 40+i, 1)
                d.line(112, 16+i, 72, 40+i, 1)
            d.show()
            time.sleep_ms(800)
            
            # 5. Snap back to normal eyes
            draw_open()

        elif animation == "angry_flash":
            # 1. Slam brows down
            d.fill(0)
            d.fill_rect(24, 40, 32, 16, 1)
            d.fill_rect(72, 40, 32, 16, 1)
            for i in range(6):
                d.line(16, 16+i, 56, 40+i, 1)
                d.line(112, 16+i, 72, 40+i, 1)
            d.show()
            time.sleep_ms(300)
            
            # 2. Flash inverted colors (System Warning!)
            for _ in range(4):
                # White screen, black eyes
                d.fill(1)
                d.fill_rect(24, 40, 32, 16, 0)
                d.fill_rect(72, 40, 32, 16, 0)
                for i in range(6):
                    d.line(16, 16+i, 56, 40+i, 0)
                    d.line(112, 16+i, 72, 40+i, 0)
                d.show()
                time.sleep_ms(60)
                
                # Normal screen, white eyes
                d.fill(0)
                d.fill_rect(24, 40, 32, 16, 1)
                d.fill_rect(72, 40, 32, 16, 1)
                for i in range(6):
                    d.line(16, 16+i, 56, 40+i, 1)
                    d.line(112, 16+i, 72, 40+i, 1)
                d.show()
                time.sleep_ms(60)
            
            time.sleep_ms(700)
            draw_open()
        elif animation == "sad":
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

        elif animation == "sad cry":
            slice_sz = 16
            steps = 6
            
            # 1. Look down and slant brows into sad shape
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
                d.show()
                time.sleep_ms(40)
                
            time.sleep_ms(300)
            
            # # 2. Tremble (shake left/right rapidly)
            # for shake in range(8):
            #     offset = 3 if shake % 2 == 0 else -3
            #     d.fill(0)
            #     d.fill_rect(lx + offset, ly, lw, lh, 1); d.fill_rect(rx + offset, ry, rw, rh, 1)
            #     d.fill_rect(lpc_x + offset, lpc_y + (lh // 4), ps, ps, 0)
            #     d.fill_rect(rpc_x + offset, rpc_y + (lh // 4), ps, ps, 0)
            #     for i in range(slice_sz):
            #         d.line(lx + offset, ly + i, lx + offset + slice_sz - i, ly, 0)
            #         d.line(rx + offset + rw - 1, ly + i, rx + offset + rw - 1 - (slice_sz - i), ly, 0)
            #     d.show()
            #     time.sleep_ms(40)
            
            # 3. Release three tears sequentially
            tear_paths = [(lx + lw//4, ly + lh), (rx + rw//4, ry + rh), (lx + lw//2, ly + lh)]
            for tx, ty in tear_paths:
                for drop in range(0, 16, 4):
                    d.fill_rect(tx, ty + drop, 2, 2, 1)
                    d.show()
                    time.sleep_ms(50)
                    d.fill_rect(tx, ty + drop, 2, 2, 0)
            
            time.sleep_ms(300)
            
            # 4. Recover smoothly back to normal
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
                d.show()
                time.sleep_ms(40)
            draw_open()

        elif animation == "sad Trembling":
            slice_sz = 16
            steps = 6
            
            # 1. Look down and slant brows into sad shape
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
                d.show()
                time.sleep_ms(40)
                
            time.sleep_ms(300)
            
            # 2. Tremble (shake left/right rapidly but slightly)
            for shake in range(12):
                offset = 2 if shake % 2 == 0 else -2
                d.fill(0)
                d.fill_rect(lx + offset, ly, lw, lh, 1); d.fill_rect(rx + offset, ry, rw, rh, 1)
                d.fill_rect(lpc_x + offset, lpc_y + (lh // 4), ps, ps, 0)
                d.fill_rect(rpc_x + offset, rpc_y + (lh // 4), ps, ps, 0)
                
                for i in range(slice_sz):
                    d.line(lx + offset, ly + i, lx + offset + slice_sz - i, ly, 0)
                    d.line(rx + offset + rw - 1, ly + i, rx + offset + rw - 1 - (slice_sz - i), ly, 0)
                d.show()
                time.sleep_ms(40)
            
            time.sleep_ms(500)
            
            # 3. Recover smoothly back to normal
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
                d.show()
                time.sleep_ms(40)
            draw_open()

        elif animation == "surprised":
            d.fill(0)
            extra = 8
            d.fill_rect(lx - 2, ly - extra, lw + 4, lh + extra * 2, 1)
            d.fill_rect(rx - 2, ry - extra, rw + 4, rh + extra * 2, 1)
            half = ps // 2
            d.fill_rect(lpc_x + half // 2, lpc_y + half // 2, half, half, 0)
            d.fill_rect(rpc_x + half // 2, rpc_y + half // 2, half, half, 0)
            d.show(); time.sleep_ms(700)
            _blink_eye(lambda h: draw_squash(h))
            draw_open()
        elif animation == "confused":
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
        elif animation == "spin":
            import math
            r = min(lw, lh) // 2 - ps - 2; r = max(2, r)
            cx_l = lpc_x + ps // 2; cy_l = lpc_y + ps // 2
            cx_r = rpc_x + ps // 2; cy_r = rpc_y + ps // 2
            for i in range(25):
                angle = (2 * math.pi * i) / 20
                ox = int(r * math.cos(angle)); oy = int(r * math.sin(angle))
                draw_open(cx_l - ps // 2 + ox, cy_l - ps // 2 + oy,
                          cx_r - ps // 2 + ox, cy_r - ps // 2 + oy)
                time.sleep_ms(35)
            draw_open()
        elif animation == "dizzy":
            import math
            for rep in range(2):
                for i in range(20):
                    angle = (2 * math.pi * i) / 20
                    r = int((1 - i / 20) * (min(lw, lh) // 2 - ps - 2))
                    ox = int(r * math.cos(angle)); oy = int(r * math.sin(angle))
                    draw_open(lpc_x + ox, lpc_y + oy, rpc_x + ox, rpc_y + oy)
                    time.sleep_ms(30)
            draw_open()

        elif animation == "sleepy":
            # 1. Close eyes (droop shut)
            for h in range(lh, 0, -lh // 10 or -1):
                d.fill(0)
                h = max(1, h)
                d.fill_rect(lx, ly + lh - h, lw, h, 1)
                d.fill_rect(rx, ry + rh - h, rw, h, 1)
                d.show(); time.sleep_ms(70)
            
            # 2. Sleep pause with floating Zs
            for i in range(3):
                # Draw Zs at different positions/sizes
                # 1st Z small, 2nd medium, 3rd large
                self._draw_scaled_text("z", 70 + (i*10), 30 - (i*10), i + 1)
                d.show()
                time.sleep_ms(500)
            
            # 3. Open eyes
            for h in range(1, lh + 1, lh // 6 or 1):
                d.fill(0)
                d.fill_rect(lx, ly + lh - h, lw, h, 1)
                d.fill_rect(rx, ry + rh - h, rw, h, 1)
                d.show(); time.sleep_ms(40)
            draw_open()

        elif animation == "excited":
            for _ in range(4):
                for oy in [-6, -10, -6, 0, 4, 0]:
                    d.fill(0)
                    d.fill_rect(lx, ly + oy, lw, lh, 1)
                    d.fill_rect(rx, ry + oy, rw, rh, 1)
                    d.fill_rect(lpc_x, lpc_y + oy, ps, ps, 0)
                    d.fill_rect(rpc_x, rpc_y + oy, ps, ps, 0)
                    d.show(); time.sleep_ms(40)

        elif animation == "So excited":
            for _ in range(4):
                for oy in [-6, -10, -6, 0, 4, 0]:
                    d.fill(0)
                    # 1. Draw Eye Sockets
                    d.fill_rect(lx, ly + oy, lw, lh, 1)
                    d.fill_rect(rx, ry + oy, rw, rh, 1)
                    
                    # 2. Draw Large Sparkle Star (9x9 core)
                    for cx, cy in [(lpc_x + ps//2, lpc_y + ps//2 + oy), 
                                   (rpc_x + ps//2, rpc_y + ps//2 + oy)]:
                        
                        # Central Rectangle (The 9x9 Core)
                        # Replaced 5x5 with 9x9
                        d.fill_rect(cx-4, cy-4, 9, 9, 0)
                        
                        # Lines extending out (Proportionally longer)
                        # Vertical cross
                        d.line(cx, cy-9, cx, cy+9, 0)
                        d.line(cx-9, cy, cx+9, cy, 0)
                        
                        # Diagonal lines
                        d.line(cx-7, cy-7, cx+7, cy+7, 0)
                        d.line(cx-7, cy+7, cx+7, cy-7, 0)
                    
                    d.show(); time.sleep_ms(40)
            draw_open()

        elif animation == "flicker":
            import urandom
            for _ in range(15):
                if urandom.getrandbits(1): draw_open()
                else: d.fill(0); d.show()
                time.sleep_ms(urandom.randint(30, 90))
            draw_open()
            
        elif animation == "glitch":
            import urandom
            for _ in range(12):
                d.fill(0)
                shift_l = urandom.randint(-12, 12)
                shift_r = urandom.randint(-12, 12)
                d.fill_rect(max(0, lx + shift_l), ly, lw, lh, 1)
                d.fill_rect(max(0, rx + shift_r), ry, rw, rh, 1)
                d.fill_rect(max(0, lpc_x + shift_l), lpc_y, ps, ps, 0)
                d.fill_rect(max(0, rpc_x + shift_r), rpc_y, ps, ps, 0)
                d.show(); time.sleep_ms(50)
            draw_open()
        else:
            draw_open()

    def animate_heartbeat(self, size="medium", style="double_hollow"):
        """Plays a beating heart animation with 0 memory leakage."""
        if not self.display: return
        d = self.display
        
        # We safely dropped the massive 48x48 size. Max is now 32x32.
        dim_map = {
            "large":  (32, 24, 16),
            "medium": (24, 16, 8),
            "small":  (16, 8, 8) 
        }
        M, S, SS = dim_map.get(size, (24, 16, 8))
        
        is_filled = (style == "single_filled")
        is_double = (style == "double_hollow")
        
        # PULL FROM PRE-ALLOCATED MEMORY (Prevents RAM crashes!)
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

        fb_main = get_fb(M, is_filled)
        fb_sub = get_fb(S, is_filled)
        fb_subsub = get_fb(SS, False)
        
        cx_main = 56 if is_double else 64
        cy_main = 30 if is_double else 32
        cx_sub  = 76
        cy_sub  = 40

        def draw_pulse(is_peak, thicken):
            d.fill(0)
            if is_double:
                if is_peak: # Maximum Expansion
                    # Sub offset behind
                    d.blit(fb_sub, cx_sub - S//2, cy_sub - S//2, 0)
                    if thicken:
                        d.blit(fb_sub, cx_sub - S//2 + 1, cy_sub - S//2, 0)
                        d.blit(fb_sub, cx_sub - S//2, cy_sub - S//2 + 1, 0)
                    # Main in front
                    d.blit(fb_main, cx_main - M//2, cy_main - M//2, 0)
                    if thicken:
                        d.blit(fb_main, cx_main - M//2 + 1, cy_main - M//2, 0)
                        d.blit(fb_main, cx_main - M//2, cy_main - M//2 + 1, 0)
                else: # Contracted State
                    d.blit(fb_subsub, cx_sub - SS//2, cy_sub - SS//2, 0)
                    if thicken:
                        d.blit(fb_subsub, cx_sub - SS//2 + 1, cy_sub - SS//2, 0)
                        d.blit(fb_subsub, cx_sub - SS//2, cy_sub - SS//2 + 1, 0)
                        
                    d.blit(fb_sub, cx_main - S//2, cy_main - S//2, 0)
                    if thicken:
                        d.blit(fb_sub, cx_main - S//2 + 1, cy_main - S//2, 0)
                        d.blit(fb_sub, cx_main - S//2, cy_main - S//2 + 1, 0)
            else: # Single Hollow or Single Filled
                if is_peak:
                    d.blit(fb_main, cx_main - M//2, cy_main - M//2, 0)
                    if thicken and not is_filled:
                        d.blit(fb_main, cx_main - M//2 + 1, cy_main - M//2, 0)
                        d.blit(fb_main, cx_main - M//2, cy_main - M//2 + 1, 0)
                else:
                    d.blit(fb_sub, cx_main - S//2, cy_main - S//2, 0)
                    if thicken and not is_filled:
                        d.blit(fb_sub, cx_main - S//2 + 1, cy_main - S//2, 0)
                        d.blit(fb_sub, cx_main - S//2, cy_main - S//2 + 1, 0)
            d.show()

        # Execute "Lub-dub" rhythm
        for _ in range(4):
            draw_pulse(False, False) 
            time.sleep_ms(150)
            draw_pulse(True, True)   
            time.sleep_ms(150)
            draw_pulse(False, False) 
            time.sleep_ms(150)
            draw_pulse(True, True)   
            time.sleep_ms(400)
            
        d.fill(0); d.show()

# Global instance exposed to the MicroPython REPL execution context
oled = RobotOLED()