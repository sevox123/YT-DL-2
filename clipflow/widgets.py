"""Custom widgets: a two-handle range slider used as the trim timeline."""
import tkinter as tk


class RangeSlider(tk.Canvas):
    PAD = 18          # horizontal padding (room for the handles)
    HANDLE_R = 10
    HIT_R = 15

    def __init__(self, master, command=None, bg="#1b1b27", track="#2f2f45",
                 accent="#7c5cff", accent2="#ff5c93", height=50):
        super().__init__(master, height=height, bg=bg, highlightthickness=0, bd=0)
        self.command = command
        self.track, self.accent, self.accent2 = track, accent, accent2
        self.minv, self.maxv = 0.0, 100.0
        self.lo, self.hi = 0.0, 100.0
        self.enabled = True
        self._drag = None
        self._off = 0.0
        self.bind("<Configure>", lambda e: self.redraw())
        self.bind("<Button-1>", self._press)
        self.bind("<B1-Motion>", self._move)
        self.bind("<ButtonRelease-1>", self._release)
        self.bind("<Motion>", self._hover)

    # ---- public API
    @property
    def gap(self):
        return min(1.0, self.maxv / 10)

    def set_range(self, maxv):
        self.maxv = max(1.0, float(maxv))
        self.lo, self.hi = 0.0, self.maxv
        self.redraw()

    def set_values(self, lo, hi, notify=False):
        lo = max(self.minv, min(float(lo), self.maxv))
        hi = max(self.minv, min(float(hi), self.maxv))
        if hi - lo < self.gap:
            hi = min(self.maxv, lo + self.gap)
            lo = max(self.minv, hi - self.gap)
        self.lo, self.hi = lo, hi
        self.redraw()
        if notify:
            self._notify()

    def values(self):
        return self.lo, self.hi

    def set_enabled(self, on):
        self.enabled = bool(on)
        self.redraw()

    # ---- geometry
    def _span_px(self):
        return max(1, self.winfo_width() - 2 * self.PAD)

    def _x(self, v):
        return self.PAD + (v - self.minv) / (self.maxv - self.minv) * self._span_px()

    def _v(self, x):
        r = (x - self.PAD) / self._span_px()
        return self.minv + max(0.0, min(1.0, r)) * (self.maxv - self.minv)

    def _snap(self, v):
        if abs(v - self.maxv) < 0.5:
            return self.maxv
        if abs(v - self.minv) < 0.5:
            return self.minv
        return float(round(v))

    # ---- drawing
    def redraw(self):
        self.delete("all")
        w, h = self.winfo_width(), int(self.cget("height"))
        if w < 2 * self.PAD + 10:
            return
        cy = h // 2
        x0, x1 = self.PAD, w - self.PAD
        for i in range(11):                               # ticks
            x = x0 + (x1 - x0) * i / 10
            self.create_line(x, cy + 14, x, cy + (20 if i % 5 == 0 else 17), fill=self.track, width=2)
        self.create_line(x0, cy, x1, cy, width=8, fill=self.track, capstyle="round")
        xl, xh = self._x(self.lo), self._x(self.hi)
        a, b = (self.accent, self.accent2) if self.enabled else ("#4a4a5e", "#4a4a5e")
        self.create_line(xl, cy, xh, cy, width=8, fill=a, capstyle="round")
        for x, col in ((xl, a), (xh, b)):
            r = self.HANDLE_R
            self.create_oval(x - r, cy - r, x + r, cy + r, fill="#ffffff", outline=col, width=3)

    # ---- interaction
    def _hover(self, e):
        if not self.enabled:
            return self.configure(cursor="arrow")
        near = min(abs(e.x - self._x(self.lo)), abs(e.x - self._x(self.hi))) <= self.HIT_R
        inside = self._x(self.lo) < e.x < self._x(self.hi)
        self.configure(cursor="hand2" if near else ("fleur" if inside else "arrow"))

    def _press(self, e):
        if not self.enabled:
            return
        xl, xh = self._x(self.lo), self._x(self.hi)
        dl, dh = abs(e.x - xl), abs(e.x - xh)
        if dl <= self.HIT_R or dh <= self.HIT_R:
            if dl == dh:
                self._drag = "lo" if e.x < xl else "hi"
            else:
                self._drag = "lo" if dl < dh else "hi"
        elif xl < e.x < xh:
            self._drag, self._off = "mid", self._v(e.x) - self.lo
        else:
            self._drag = "lo" if dl < dh else "hi"
            self._move(e)

    def _move(self, e):
        if not self._drag:
            return
        v = self._snap(self._v(e.x))
        if self._drag == "lo":
            self.lo = max(self.minv, min(v, self.hi - self.gap))
        elif self._drag == "hi":
            self.hi = min(self.maxv, max(v, self.lo + self.gap))
        else:
            span = self.hi - self.lo
            lo = max(self.minv, min(self._snap(self._v(e.x) - self._off), self.maxv - span))
            self.lo, self.hi = lo, lo + span
        self.redraw()
        self._notify()

    def _release(self, _):
        self._drag = None

    def _notify(self):
        if self.command:
            self.command(self.lo, self.hi)
