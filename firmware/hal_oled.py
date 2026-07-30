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


class RobotOLED:
    W = 128
    H = 64

    def __init__(self, scl_pin=22, sda_pin=21):
        try:
            self.i2c = I2C(0, scl=Pin(scl_pin), sda=Pin(sda_pin), freq=400000)
            self.display = ssd1306.SSD1306_I2C(self.W, self.H, self.i2c)
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

    # --------------------------------------------------------------- text modes

    def show_text(self, text, size=2):
        """Manual size: 1=tiny, 2=medium, 3=large, 4=huge"""
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
        """Smart-fit: picks the largest scale that makes everything fit on screen."""
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
            if cols == 0:
                continue
            
            if scale > 1 and any(len(w) > cols for w in raw_words):
                continue

            words = []
            for w in raw_words:
                while len(w) > cols and cols > 0:
                    words.append(w[:cols])
                    w = w[cols:]
                if w:
                    words.append(w)

            lines, current = [], ""
            for word in words:
                test = (current + " " + word).strip()
                if len(test) <= cols:
                    current = test
                else:
                    if current:
                        lines.append(current)
                    current = word
            if current:
                lines.append(current)
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

    # ----------------------------------------------------------- static emojis

    def show_emoji(self, emoji_name):
        if not self.display:
            return
        d = self.display
        d.fill(0)
        if emoji_name == "heart":
            d.fill_rect(24,  8, 32, 32, 1); d.fill_rect(72,  8, 32, 32, 1)
            d.fill_rect(16, 16, 96, 24, 1); d.fill_rect(24, 40, 80,  8, 1)
            d.fill_rect(40, 48, 48,  8, 1); d.fill_rect(56, 56, 16,  8, 1)
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

    # ===================================================== ANIMATION ENGINE ===

    def animate_eyes(self, style="big_eyes", animation="blink"):
        """
        Play a smooth eye animation once then leave eyes open.

        STYLES      : big_eyes | hollow_eyes | wide_eyes | tall_eyes |
                      cute_eyes | small_eyes
        ANIMATIONS:
          Blink / wink  : blink, double_blink, wink_left, wink_right
          Look around   : look_left, look_right, look_up, look_down,
                          look_topleft, look_topright, look_botleft, look_botright
          Mood          : happy, angry, sad, surprised, confused
          Special FX    : spin, dizzy, sleepy, excited, flicker, glitch
        """
        if not self.display:
            return

        # --- eye geometry per style (lx,ly,lw,lh, rx,ry,rw,rh, pupil_size) ---
        STYLES = {
            "big_eyes":    (16, 12, 40, 40, 72, 12, 40, 40, 12),
            "hollow_eyes": (16, 12, 40, 40, 72, 12, 40, 40, 12),
            "wide_eyes":   (12, 20, 48, 28, 68, 20, 48, 28, 10),
            "tall_eyes":   (24,  8, 32, 48, 72,  8, 32, 48,  8),
            "cute_eyes":   (16,  8, 40, 48, 72,  8, 40, 48, 14),
            "small_eyes":  (32, 20, 24, 28, 72, 20, 24, 28,  8),
        }
        geo = STYLES.get(style, STYLES["big_eyes"])
        lx, ly, lw, lh, rx, ry, rw, rh, ps = geo
        d = self.display

        # Default pupil centres
        lpc_x = lx + (lw - ps) // 2
        lpc_y = ly + (lh - ps) // 2
        rpc_x = rx + (rw - ps) // 2
        rpc_y = ry + (rh - ps) // 2

        # --- drawing helpers ---
        def draw_open(lpx=None, lpy=None, rpx=None, rpy=None):
            if lpx is None: lpx, lpy, rpx, rpy = lpc_x, lpc_y, rpc_x, rpc_y
            d.fill(0)
            d.fill_rect(lx, ly, lw, lh, 1); d.fill_rect(rx, ry, rw, rh, 1)
            d.fill_rect(lpx, lpy, ps, ps, 0); d.fill_rect(rpx, rpy, ps, ps, 0)
            d.show()

        def draw_squash(h_l, h_r=None, lpx=None, lpy=None, rpx=None, rpy=None):
            """Draw eyes squashed to height h_l (left) / h_r (right)."""
            if h_r is None: h_r = h_l
            if lpx is None: lpx, lpy, rpx, rpy = lpc_x, lpc_y, rpc_x, rpc_y
            h_l, h_r = max(1, h_l), max(1, h_r)
            d.fill(0)
            ml = ly + (lh - h_l) // 2; mr = ry + (rh - h_r) // 2
            d.fill_rect(lx, ml, lw, h_l, 1); d.fill_rect(rx, mr, rw, h_r, 1)
            d.show()

        def _blink_eye(squash_fn, steps=6):
            """Generic close/open sequence."""
            for i in range(steps, 0, -1):
                squash_fn(lh * i // steps)
                time.sleep_ms(25)
            time.sleep_ms(60)
            for i in range(1, steps + 1):
                squash_fn(lh * i // steps)
                time.sleep_ms(20)

        def _move_pupils(dx, dy, steps=5, hold_ms=400):
            """Slide pupils from centre to offset (dx, dy) then back."""
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

        # ------------------------------------------------------------- resting
        draw_open()
        time.sleep_ms(200)

        # ======================================================= BLINK GROUP ==
        if animation == "blink":
            _blink_eye(lambda h: draw_squash(h))
            draw_open()

        elif animation == "double_blink":
            _blink_eye(lambda h: draw_squash(h))
            draw_open(); time.sleep_ms(180)
            _blink_eye(lambda h: draw_squash(h))
            draw_open()

        elif animation == "wink_left":
            # Left eye blinks, right stays open
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

        # =================================================== LOOK-AROUND GROUP
        elif animation == "look_left":
            _move_pupils(-(lw // 2 - ps), 0)

        elif animation == "look_right":
            _move_pupils( (lw // 2 - ps), 0)

        elif animation == "look_up":
            _move_pupils(0, -(lh // 2 - ps))

        elif animation == "look_down":
            _move_pupils(0,  (lh // 2 - ps))

        elif animation == "look_topleft":
            _move_pupils(-(lw // 3), -(lh // 3))

        elif animation == "look_topright":
            _move_pupils( (lw // 3), -(lh // 3))

        elif animation == "look_botleft":
            _move_pupils(-(lw // 3),  (lh // 3))

        elif animation == "look_botright":
            _move_pupils( (lw // 3),  (lh // 3))

        # ======================================================= MOOD GROUP ===
        elif animation == "happy":
            # Eyes squash down to half, arch up (eyebrow-like lines above)
            for i in range(6, 2, -1):
                draw_squash(lh * i // 6)
                time.sleep_ms(30)
            # Draw happy arched lines + smile
            d.fill(0)
            # Left & Right happy arc (bottom half of eyes)
            d.fill_rect(lx, ly + lh // 2, lw, lh // 2, 1)
            d.fill_rect(rx, ry + rh // 2, rw, rh // 2, 1)
            # Add a smile in the middle bottom
            # Center of OLED is x=64, U-shape smile
            d.fill_rect(48, 52, 32, 4, 1) # bottom of mouth
            d.fill_rect(44, 48, 4, 8, 1)  # left corner
            d.fill_rect(80, 48, 4, 8, 1)  # right corner
            d.show(); time.sleep_ms(700)
            # Bounce back
            for i in range(3, 7):
                draw_squash(lh * i // 6)
                time.sleep_ms(30)
            draw_open()

        elif animation == "angry":
            # Pupils push inward + eyes squash slightly + angry V-lines on brows
            steps = 5
            for s in range(1, steps + 1):
                ox = (lw // 4) * s // steps   # pupils move toward nose
                draw_open(lpc_x + ox, lpc_y, rpc_x - ox, rpc_y)
                time.sleep_ms(30)
            # Draw angry brow lines over current frame
            d.line(lx, ly - 4, lx + lw, ly + 4, 1)
            d.line(rx + rw, ry - 4, rx, ry + 4, 1)
            d.show(); time.sleep_ms(700)
            # Revert
            for s in range(steps - 1, -1, -1):
                ox = (lw // 4) * s // steps
                draw_open(lpc_x + ox, lpc_y, rpc_x - ox, rpc_y)
                time.sleep_ms(30)
            draw_open()

        elif animation == "sad":
            # Pupils drift downward + eyes tilt (inner corners drop)
            steps = 6
            for s in range(1, steps + 1):
                oy = (lh // 4) * s // steps
                draw_open(lpc_x, lpc_y + oy, rpc_x, rpc_y + oy)
                time.sleep_ms(35)
            # Droopy inner corners via darkened top inner triangles
            d.fill_rect(lx + lw - 8, ly, 8, 8, 0)
            d.fill_rect(rx, ry, 8, 8, 0)
            d.show(); time.sleep_ms(600)
            for s in range(steps - 1, -1, -1):
                oy = (lh // 4) * s // steps
                draw_open(lpc_x, lpc_y + oy, rpc_x, rpc_y + oy)
                time.sleep_ms(35)
            draw_open()

        elif animation == "surprised":
            # Eyes grow wide (height expands), pupils shrink to dots
            # Simulate by clearing, drawing taller eyes
            d.fill(0)
            extra = 8
            d.fill_rect(lx - 2, ly - extra, lw + 4, lh + extra * 2, 1)
            d.fill_rect(rx - 2, ry - extra, rw + 4, rh + extra * 2, 1)
            # Tiny pupils (half size)
            half = ps // 2
            d.fill_rect(lpc_x + half // 2, lpc_y + half // 2, half, half, 0)
            d.fill_rect(rpc_x + half // 2, rpc_y + half // 2, half, half, 0)
            d.show(); time.sleep_ms(700)
            # Blink back to normal
            _blink_eye(lambda h: draw_squash(h))
            draw_open()

        elif animation == "confused":
            # Horizontal shake left–right (head-shake feel)
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

        # ====================================================== SPECIAL FX ===
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
            # Pupils spiral inward from edge to center, repeat twice
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
            # Eyes very slowly droop shut, pause, then snap open
            for h in range(lh, 0, -lh // 10 or -1):
                d.fill(0)
                h = max(1, h)
                d.fill_rect(lx, ly + lh - h, lw, h, 1)
                d.fill_rect(rx, ry + rh - h, rw, h, 1)
                d.show(); time.sleep_ms(70)
            time.sleep_ms(800)
            for h in range(1, lh + 1, lh // 6 or 1):
                d.fill(0)
                d.fill_rect(lx, ly + lh - h, lw, h, 1)
                d.fill_rect(rx, ry + rh - h, rw, h, 1)
                d.show(); time.sleep_ms(40)
            draw_open()

        elif animation == "excited":
            # Eyes rapidly bounce up and down 4 times
            for _ in range(4):
                for oy in [-6, -10, -6, 0, 4, 0]:
                    d.fill(0)
                    d.fill_rect(lx, ly + oy, lw, lh, 1)
                    d.fill_rect(rx, ry + oy, rw, rh, 1)
                    d.fill_rect(lpc_x, lpc_y + oy, ps, ps, 0)
                    d.fill_rect(rpc_x, rpc_y + oy, ps, ps, 0)
                    d.show(); time.sleep_ms(40)

        elif animation == "flicker":
            # Rapid random flicker on/off (like a glitching robot)
            import urandom
            for _ in range(15):
                if urandom.getrandbits(1):
                    draw_open()
                else:
                    d.fill(0); d.show()
                time.sleep_ms(urandom.randint(30, 90))
            draw_open()

        elif animation == "glitch":
            # Draw eyes with random horizontal pixel shifts
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

        elif animation == "heartbeat":
            # Draw a beating heart animation
            def draw_heart(scale):
                d.fill(0)
                if scale == "big":
                    d.fill_rect(24,  8, 32, 32, 1); d.fill_rect(72,  8, 32, 32, 1)
                    d.fill_rect(16, 16, 96, 24, 1); d.fill_rect(24, 40, 80,  8, 1)
                    d.fill_rect(40, 48, 48,  8, 1); d.fill_rect(56, 56, 16,  8, 1)
                elif scale == "small":
                    d.fill_rect(32, 16, 24, 24, 1); d.fill_rect(72, 16, 24, 24, 1)
                    d.fill_rect(24, 24, 80, 16, 1); d.fill_rect(32, 40, 64,  8, 1)
                    d.fill_rect(48, 48, 32,  8, 1); d.fill_rect(60, 56,  8,  8, 1)
                d.show()

            for _ in range(4):
                draw_heart("small")
                time.sleep_ms(150)
                draw_heart("big")
                time.sleep_ms(150)
                draw_heart("small")
                time.sleep_ms(150)
                draw_heart("big")
                time.sleep_ms(400)
            draw_open()

        else:
            # Unknown animation — just show open eyes
            draw_open()


# Global instance exposed to the MicroPython REPL execution context
oled = RobotOLED()
