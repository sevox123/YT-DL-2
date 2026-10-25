"""ClipFlow GUI (customtkinter)."""
import io
import json
import os
import queue
import re
import subprocess
import sys
import threading
import tkinter as tk
import urllib.request
from tkinter import filedialog, messagebox

import customtkinter as ctk
from PIL import Image

from . import APP_NAME, engine
from ._version import __version__
from .widgets import RangeSlider

BG, CARD, CARD2 = "#12121a", "#1b1b27", "#242436"
HOVER = "#2e2e45"
ACCENT, ACCENT_H, PINK = "#7c5cff", "#6a49f0", "#ff5c93"
TEXT, MUTED, OK, ERR = "#f2f2f8", "#8b8ba3", "#3ddc97", "#ff6b6b"
THUMB_W, THUMB_H = 176, 99


COOKIE_OFF = "Off"
COOKIE_FILE = "cookies.txt file…"


def settings_path():
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    return os.path.join(base, APP_NAME, "settings.json")


def load_settings():
    try:
        with open(settings_path(), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_settings(data):
    try:
        os.makedirs(os.path.dirname(settings_path()), exist_ok=True)
        with open(settings_path(), "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception:
        pass


def resource(*parts):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base, *parts)


class App(ctk.CTk):
    def __init__(self):
        ctk.set_appearance_mode("dark")
        super().__init__(fg_color=BG)
        self.title(APP_NAME)
        self.geometry("900x800")
        self.minsize(840, 640)
        ico = resource("assets", "icon.ico")
        self.after(250, lambda: self._try(lambda: self.iconbitmap(ico)))

        self.q = queue.Queue()
        self.info = None
        self.cancel = threading.Event()
        self.busy = False
        self.indeterminate = False
        self.last_file = None

        self.url_var = tk.StringVar()
        self.mode_var = tk.StringVar(value="Video")
        self.quality_var = tk.StringVar(value=engine.BEST)
        self.container_var = tk.StringVar(value="MP4")
        self.afmt_var = tk.StringVar(value="MP3")
        self.bitrate_var = tk.StringVar(value="192")
        self.trim_var = tk.BooleanVar(value=False)
        self.start_var = tk.StringVar(value="0:00")
        self.end_var = tk.StringVar(value="0:00")
        self.settings = load_settings()
        default_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        self.folder_var = tk.StringVar(value=self.settings.get("folder") or default_dir)
        engine.SETTINGS["browser"] = self.settings.get("browser", "")
        engine.SETTINGS["cookiefile"] = self.settings.get("cookiefile", "")
        if engine.SETTINGS["cookiefile"]:
            choice = COOKIE_FILE
        else:
            choice = engine.SETTINGS["browser"] or COOKIE_OFF
        self.cookie_var = tk.StringVar(value=choice)

        self.f_title = ctk.CTkFont(family="Segoe UI", size=26, weight="bold")
        self.f_h = ctk.CTkFont(family="Segoe UI", size=14, weight="bold")
        self.f_n = ctk.CTkFont(family="Segoe UI", size=13)
        self.f_s = ctk.CTkFont(family="Segoe UI", size=12)

        self._build()
        self.after(60, self._pump)

    # ------------------------------------------------------------ plumbing
    @staticmethod
    def _try(fn):
        try:
            fn()
        except Exception:
            pass

    def post(self, fn, *args):
        self.q.put((fn, args))

    def _pump(self):
        try:
            while True:
                fn, args = self.q.get_nowait()
                fn(*args)
        except queue.Empty:
            pass
        self.after(60, self._pump)

    def card(self):
        f = ctk.CTkFrame(self.body, fg_color=CARD, corner_radius=16)
        f.pack(fill="x", padx=18, pady=7)
        return f

    def menu(self, parent, label, var, values, width=170, command=None):
        col = ctk.CTkFrame(parent, fg_color="transparent")
        ctk.CTkLabel(col, text=label, font=self.f_s, text_color=MUTED).pack(anchor="w")
        m = ctk.CTkOptionMenu(
            col, values=values, variable=var, width=width, height=36, corner_radius=10,
            fg_color=CARD2, button_color=HOVER, button_hover_color="#3a3a55",
            dropdown_fg_color=CARD2, dropdown_hover_color=ACCENT, font=self.f_n,
            dropdown_font=self.f_n, command=command)
        m.pack(pady=(3, 0))
        return col, m

    # ---------------------------------------------------------------- build
    def _build(self):
        self.body = ctk.CTkScrollableFrame(self, fg_color=BG, corner_radius=0)
        self.body.pack(fill="both", expand=True)
        self._build_header()
        self._build_url()
        self._build_cookies()
        self._build_preview()
        self._build_options()
        self._build_trim()
        self._build_output()
        self._build_action()
        ctk.CTkLabel(
            self.body, font=self.f_s, text_color=MUTED,
            text=f"{APP_NAME} v{__version__}  •  powered by yt-dlp & ffmpeg  •  download only content you have the right to save",
        ).pack(pady=(6, 14))

    def _build_header(self):
        hdr = ctk.CTkFrame(self.body, fg_color="transparent")
        hdr.pack(fill="x", padx=22, pady=(14, 4))
        try:
            logo = ctk.CTkImage(Image.open(resource("assets", "icon.png")), size=(52, 52))
            ctk.CTkLabel(hdr, image=logo, text="").pack(side="left")
        except Exception:
            pass
        t = ctk.CTkFrame(hdr, fg_color="transparent")
        t.pack(side="left", padx=14)
        ctk.CTkLabel(t, text=APP_NAME, font=self.f_title, text_color=TEXT).pack(anchor="w")
        ctk.CTkLabel(t, text="Any quality. Any part of the video. Or just the audio.",
                     font=self.f_n, text_color=MUTED).pack(anchor="w")

    def _build_url(self):
        c = self.card()
        ctk.CTkLabel(c, text="Video link", font=self.f_h, text_color=TEXT).pack(anchor="w", padx=18, pady=(14, 6))
        row = ctk.CTkFrame(c, fg_color="transparent")
        row.pack(fill="x", padx=18, pady=(0, 16))
        self.url_entry = ctk.CTkEntry(
            row, textvariable=self.url_var, height=42, corner_radius=12, border_width=0,
            fg_color=CARD2, font=self.f_n, placeholder_text="Paste a YouTube link here…")
        self.url_entry.pack(side="left", fill="x", expand=True)
        self.url_entry.bind("<Return>", lambda e: self.analyze())
        ctk.CTkButton(row, text="Paste", width=72, height=42, corner_radius=12, fg_color=CARD2,
                      hover_color=HOVER, font=self.f_n, command=self.paste).pack(side="left", padx=(8, 0))
        self.analyze_btn = ctk.CTkButton(row, text="Analyze", width=104, height=42, corner_radius=12,
                                         fg_color=ACCENT, hover_color=ACCENT_H, font=self.f_h, command=self.analyze)
        self.analyze_btn.pack(side="left", padx=(8, 0))

    def _build_cookies(self):
        c = self.card()
        row = ctk.CTkFrame(c, fg_color="transparent")
        row.pack(fill="x", padx=18, pady=14)
        t = ctk.CTkFrame(row, fg_color="transparent")
        t.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(t, text="YouTube sign-in", font=self.f_h, text_color=TEXT).pack(anchor="w")
        self.cookie_hint = ctk.CTkLabel(
            t, font=self.f_s, text_color=MUTED, justify="left", anchor="w", wraplength=520,
            text='Fixes "Sign in to confirm you\'re not a bot". Pick the browser where you are logged in to YouTube '
                 '(Firefox is the most reliable; for Chrome/Edge close the browser first).')
        self.cookie_hint.pack(anchor="w", pady=(2, 0))
        ctk.CTkOptionMenu(
            row, values=[COOKIE_OFF] + engine.BROWSERS + [COOKIE_FILE], variable=self.cookie_var, width=170,
            height=36, corner_radius=10, fg_color=CARD2, button_color=HOVER, button_hover_color="#3a3a55",
            dropdown_fg_color=CARD2, dropdown_hover_color=ACCENT, font=self.f_n, dropdown_font=self.f_n,
            command=self._on_cookie_choice).pack(side="right", padx=(12, 0))

    def _on_cookie_choice(self, value):
        if value == COOKIE_FILE:
            path = filedialog.askopenfilename(title="Select cookies.txt (Netscape format)",
                                              filetypes=[("Cookies", "*.txt"), ("All files", "*.*")])
            if not path:
                prev = engine.SETTINGS["browser"] or (COOKIE_FILE if engine.SETTINGS["cookiefile"] else COOKIE_OFF)
                self.cookie_var.set(prev)
                return
            engine.SETTINGS["cookiefile"], engine.SETTINGS["browser"] = path, ""
        elif value == COOKIE_OFF:
            engine.SETTINGS["cookiefile"] = engine.SETTINGS["browser"] = ""
        else:
            engine.SETTINGS["browser"], engine.SETTINGS["cookiefile"] = value, ""
        self._save()
        self.set_status("Sign-in source saved. Press Analyze again.")

    def _save(self):
        self.settings.update(browser=engine.SETTINGS["browser"], cookiefile=engine.SETTINGS["cookiefile"],
                             folder=self.folder_var.get().strip())
        save_settings(self.settings)

    def _build_preview(self):
        c = self.card()
        row = ctk.CTkFrame(c, fg_color="transparent")
        row.pack(fill="x", padx=18, pady=16)
        ph = Image.new("RGB", (THUMB_W, THUMB_H), CARD2)
        self.thumb_img = ctk.CTkImage(ph, size=(THUMB_W, THUMB_H))
        self.thumb_lbl = ctk.CTkLabel(row, image=self.thumb_img, text="", corner_radius=10)
        self.thumb_lbl.pack(side="left")
        txt = ctk.CTkFrame(row, fg_color="transparent")
        txt.pack(side="left", fill="x", expand=True, padx=16)
        self.title_lbl = ctk.CTkLabel(txt, text="No video yet", font=self.f_h, text_color=TEXT,
                                      wraplength=560, justify="left", anchor="w")
        self.title_lbl.pack(anchor="w")
        self.meta_lbl = ctk.CTkLabel(txt, text="Paste a link and press Analyze to see the available qualities.",
                                     font=self.f_n, text_color=MUTED, wraplength=560, justify="left", anchor="w")
        self.meta_lbl.pack(anchor="w", pady=(4, 0))

    def _build_options(self):
        c = self.card()
        top = ctk.CTkFrame(c, fg_color="transparent")
        top.pack(fill="x", padx=18, pady=(14, 8))
        ctk.CTkLabel(top, text="What do you want?", font=self.f_h, text_color=TEXT).pack(side="left")
        ctk.CTkSegmentedButton(
            top, values=["Video", "Audio only"], variable=self.mode_var, command=self._on_mode,
            selected_color=ACCENT, selected_hover_color=ACCENT_H, unselected_color=CARD2,
            unselected_hover_color=HOVER, fg_color=CARD2, height=34, font=self.f_n,
        ).pack(side="right")

        holder = ctk.CTkFrame(c, fg_color="transparent")
        holder.pack(fill="x", padx=18, pady=(4, 16))

        self.video_opts = ctk.CTkFrame(holder, fg_color="transparent")
        col, self.quality_menu = self.menu(self.video_opts, "Quality", self.quality_var, [engine.BEST], 230)
        col.pack(side="left")
        col, _ = self.menu(self.video_opts, "Format", self.container_var, engine.VIDEO_CONTAINERS, 120)
        col.pack(side="left", padx=(16, 0))
        self.video_opts.pack(fill="x")

        self.audio_opts = ctk.CTkFrame(holder, fg_color="transparent")
        col, _ = self.menu(self.audio_opts, "Audio format", self.afmt_var, engine.AUDIO_FORMATS, 140,
                           command=self._on_audio_fmt)
        col.pack(side="left")
        self.bitrate_col, _ = self.menu(self.audio_opts, "Bitrate (kbps)", self.bitrate_var,
                                        engine.AUDIO_BITRATES, 140)
        self.bitrate_col.pack(side="left", padx=(16, 0))

    def _build_trim(self):
        c = self.card()
        head = ctk.CTkFrame(c, fg_color="transparent")
        head.pack(fill="x", padx=18, pady=(14, 4))
        t = ctk.CTkFrame(head, fg_color="transparent")
        t.pack(side="left")
        ctk.CTkLabel(t, text="Download only a section", font=self.f_h, text_color=TEXT).pack(anchor="w")
        ctk.CTkLabel(t, text="Trim on the timeline, or type exact start / end times.",
                     font=self.f_s, text_color=MUTED).pack(anchor="w")
        self.trim_switch = ctk.CTkSwitch(head, text="", variable=self.trim_var, command=self._toggle_trim,
                                         progress_color=ACCENT, width=46, state="disabled")
        self.trim_switch.pack(side="right")

        self.trim_body = ctk.CTkFrame(c, fg_color="transparent")
        self.slider = RangeSlider(self.trim_body, command=self._on_slider, bg=CARD, track="#33334d",
                                  accent=ACCENT, accent2=PINK)
        self.slider.pack(fill="x", padx=14, pady=(6, 0))
        row = ctk.CTkFrame(self.trim_body, fg_color="transparent")
        row.pack(fill="x", padx=18, pady=(2, 16))
        for side, label, var in (("left", "Start", self.start_var), ("right", "End", self.end_var)):
            col = ctk.CTkFrame(row, fg_color="transparent")
            col.pack(side=side)
            ctk.CTkLabel(col, text=label, font=self.f_s, text_color=MUTED).pack(anchor="w")
            e = ctk.CTkEntry(col, textvariable=var, width=110, height=36, corner_radius=10, border_width=0,
                             fg_color=CARD2, justify="center", font=self.f_n)
            e.pack()
            e.bind("<Return>", lambda ev: self._on_entry())
            e.bind("<FocusOut>", lambda ev: self._on_entry())
        self.len_lbl = ctk.CTkLabel(row, text="Selected: 0:00", font=self.f_n, text_color=PINK)
        self.len_lbl.pack(expand=True, pady=(18, 0))

    def _build_output(self):
        c = self.card()
        ctk.CTkLabel(c, text="Save to", font=self.f_h, text_color=TEXT).pack(anchor="w", padx=18, pady=(14, 6))
        row = ctk.CTkFrame(c, fg_color="transparent")
        row.pack(fill="x", padx=18, pady=(0, 16))
        ctk.CTkEntry(row, textvariable=self.folder_var, height=38, corner_radius=10, border_width=0,
                     fg_color=CARD2, font=self.f_n).pack(side="left", fill="x", expand=True)
        ctk.CTkButton(row, text="Browse…", width=92, height=38, corner_radius=10, fg_color=CARD2,
                      hover_color=HOVER, font=self.f_n, command=self.browse).pack(side="left", padx=(8, 0))

    def _build_action(self):
        c = self.card()
        row = ctk.CTkFrame(c, fg_color="transparent")
        row.pack(fill="x", padx=18, pady=(16, 8))
        self.dl_btn = ctk.CTkButton(row, text="Download", height=50, corner_radius=14, fg_color=ACCENT,
                                    hover_color=ACCENT_H, font=ctk.CTkFont(family="Segoe UI", size=17, weight="bold"),
                                    state="disabled", command=self.start_download)
        self.dl_btn.pack(side="left", fill="x", expand=True)
        self.cancel_btn = ctk.CTkButton(row, text="Cancel", width=100, height=50, corner_radius=14,
                                        fg_color=CARD2, hover_color=HOVER, font=self.f_n, state="disabled",
                                        command=self.cancel_download)
        self.cancel_btn.pack(side="left", padx=(8, 0))
        self.progress = ctk.CTkProgressBar(c, height=10, corner_radius=5, fg_color=CARD2, progress_color=ACCENT)
        self.progress.set(0)
        self.progress.pack(fill="x", padx=18, pady=(6, 6))
        self.status_lbl = ctk.CTkLabel(c, text="Paste a link to begin.", font=self.f_n, text_color=MUTED,
                                       wraplength=780, justify="left", anchor="w")
        self.status_lbl.pack(fill="x", padx=18, pady=(0, 6))
        self.open_btn = ctk.CTkButton(c, text="Show in folder", width=140, height=34, corner_radius=10,
                                      fg_color=CARD2, hover_color=HOVER, font=self.f_n, command=self.open_folder)
        self.open_btn.pack_forget()
        self.action_card = c
        ctk.CTkFrame(c, fg_color="transparent", height=8).pack()

    # --------------------------------------------------------------- events
    def set_status(self, text, color=MUTED):
        self.status_lbl.configure(text=text, text_color=color)

    def paste(self):
        try:
            self.url_var.set(self.clipboard_get().strip())
        except tk.TclError:
            return
        self.analyze()

    def browse(self):
        d = filedialog.askdirectory(initialdir=self.folder_var.get() or None)
        if d:
            self.folder_var.set(os.path.normpath(d))

    def _on_mode(self, value):
        if value == "Video":
            self.audio_opts.pack_forget()
            self.video_opts.pack(fill="x")
        else:
            self.video_opts.pack_forget()
            self.audio_opts.pack(fill="x")
            self._on_audio_fmt(self.afmt_var.get())

    def _on_audio_fmt(self, value):
        if value in ("MP3", "M4A"):
            self.bitrate_col.pack(side="left", padx=(16, 0))
        else:
            self.bitrate_col.pack_forget()

    def _toggle_trim(self):
        if self.trim_var.get():
            self.trim_body.pack(fill="x")
        else:
            self.trim_body.pack_forget()

    def _sync_entries(self, lo, hi):
        self.start_var.set(engine.fmt_time(lo))
        self.end_var.set(engine.fmt_time(hi))
        self.len_lbl.configure(text=f"Selected: {engine.fmt_time(hi - lo)}")

    def _on_slider(self, lo, hi):
        self._sync_entries(lo, hi)

    def _on_entry(self):
        if not self.info or not self.info.duration:
            return
        cur_lo, cur_hi = self.slider.values()
        try:
            lo = engine.parse_time(self.start_var.get())
            hi = engine.parse_time(self.end_var.get())
            lo = max(0.0, min(lo, self.info.duration))
            hi = max(0.0, min(hi, self.info.duration))
            if hi <= lo:
                raise ValueError("end before start")
        except ValueError:
            lo, hi = cur_lo, cur_hi
        self.slider.set_values(lo, hi)
        lo, hi = self.slider.values()
        self._sync_entries(lo, hi)

    # ------------------------------------------------------------- analyze
    def analyze(self):
        url = self.url_var.get().strip()
        if not url or self.busy:
            return
        self.analyze_btn.configure(state="disabled", text="Analyzing…")
        self.dl_btn.configure(state="disabled")
        self.open_btn.pack_forget()
        self.set_status("Reading video info…")
        threading.Thread(target=self._analyze_worker, args=(url,), daemon=True).start()

    def _analyze_worker(self, url):
        try:
            self.post(self._on_info, engine.fetch_info(url))
        except Exception as e:
            self.post(self._on_info_error, e)

    def _on_info(self, info):
        self.info = info
        self.analyze_btn.configure(state="normal", text="Analyze")
        self.title_lbl.configure(text=info.title)
        length = engine.fmt_time(info.duration) if info.duration else "unknown length"
        qs = f"up to {engine.quality_label(info.heights[0])}" if info.heights else "audio only"
        meta = "  •  ".join(x for x in (info.uploader, length, qs) if x)
        self.meta_lbl.configure(text=meta)

        labels = info.quality_labels
        self.quality_menu.configure(values=labels)
        self.quality_var.set(labels[0])

        can_trim = info.duration > 2 and not info.is_live
        self.trim_switch.deselect()
        self.trim_switch.configure(state="normal" if can_trim else "disabled")
        self._toggle_trim()
        if can_trim:
            self.slider.set_range(info.duration)
            self._sync_entries(0, info.duration)

        if info.is_live:
            self.set_status("Live streams can't be downloaded until they finish.", ERR)
            return
        self.dl_btn.configure(state="normal")
        self.set_status("Ready. Pick a quality and press Download.")
        if info.thumbnail:
            threading.Thread(target=self._thumb_worker, args=(info.thumbnail,), daemon=True).start()

    def _on_info_error(self, e):
        self.analyze_btn.configure(state="normal", text="Analyze")
        self.set_status(self._clean_error(e), ERR)

    def _thumb_worker(self, url):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            img = Image.open(io.BytesIO(urllib.request.urlopen(req, timeout=10).read())).convert("RGB")
            w, h = img.size
            target = THUMB_W / THUMB_H
            if w / h > target:
                nw = int(h * target)
                img = img.crop(((w - nw) // 2, 0, (w - nw) // 2 + nw, h))
            else:
                nh = int(w / target)
                img = img.crop((0, (h - nh) // 2, w, (h - nh) // 2 + nh))
            self.post(self._set_thumb, img.resize((THUMB_W * 2, THUMB_H * 2), Image.LANCZOS))
        except Exception:
            pass

    def _set_thumb(self, img):
        self.thumb_img = ctk.CTkImage(img, size=(THUMB_W, THUMB_H))
        self.thumb_lbl.configure(image=self.thumb_img)

    # ------------------------------------------------------------ download
    def _make_request(self):
        folder = self.folder_var.get().strip()
        if not folder:
            messagebox.showwarning(APP_NAME, "Please choose a folder to save into.")
            return None
        if self.url_var.get().strip() != self.info.url:
            self.set_status("The link changed — press Analyze first.", ERR)
            return None
        req = engine.Request(
            url=self.info.url, folder=folder,
            mode="audio" if self.mode_var.get() == "Audio only" else "video",
            height=engine.parse_quality(self.quality_var.get()),
            container=self.container_var.get().lower(),
            audio_format=self.afmt_var.get().lower(),
            bitrate=self.bitrate_var.get(),
        )
        if self.trim_var.get() and self.info.duration:
            lo, hi = self.slider.values()
            if not (lo <= 0.5 and hi >= self.info.duration - 0.5):
                req.start, req.end = lo, hi
        return req

    def start_download(self):
        if not self.info or self.busy:
            return
        req = self._make_request()
        if req is None:
            return
        try:
            os.makedirs(req.folder, exist_ok=True)
        except OSError as e:
            self.set_status(f"Can't use that folder: {e}", ERR)
            return
        self._save()
        self.busy = True
        self.cancel.clear()
        self.last_file = None
        self.open_btn.pack_forget()
        self.dl_btn.configure(state="disabled", text="Downloading…")
        self.cancel_btn.configure(state="normal")
        self.analyze_btn.configure(state="disabled")
        self._set_indeterminate(False)
        self.progress.set(0)
        self.set_status("Starting…")
        threading.Thread(target=self._dl_worker, args=(req,), daemon=True).start()

    def _dl_worker(self, req):
        try:
            path = engine.download(req, lambda f, t: self.post(self._on_progress, f, t), self.cancel)
            self.post(self._on_done, path, req.folder)
        except engine.Cancelled:
            self.post(self._on_cancelled)
        except Exception as e:
            self.post(self._on_error, e)

    def cancel_download(self):
        self.cancel.set()
        self.cancel_btn.configure(state="disabled")
        self.set_status("Cancelling…")

    def _set_indeterminate(self, on):
        if on == self.indeterminate:
            return
        self.indeterminate = on
        if on:
            self.progress.configure(mode="indeterminate")
            self.progress.start()
        else:
            self.progress.stop()
            self.progress.configure(mode="determinate")

    def _on_progress(self, frac, text):
        if self.cancel.is_set():
            return
        if frac is None:
            self._set_indeterminate(True)
        else:
            self._set_indeterminate(False)
            self.progress.set(frac)
        self.set_status(text)

    def _finish_ui(self):
        self.busy = False
        self._set_indeterminate(False)
        self.dl_btn.configure(state="normal", text="Download")
        self.cancel_btn.configure(state="disabled")
        self.analyze_btn.configure(state="normal")

    def _on_done(self, path, folder):
        self._finish_ui()
        self.progress.set(1)
        self.last_file = path
        name = os.path.basename(path) if path else folder
        self.set_status(f"Done — saved: {name}", OK)
        self.open_btn.pack(anchor="w", padx=18, pady=(0, 6))

    def _on_cancelled(self):
        self._finish_ui()
        self.progress.set(0)
        self.set_status("Cancelled. Partial files may remain in the folder.")

    def _on_error(self, e):
        self._finish_ui()
        self.progress.set(0)
        self.set_status(self._clean_error(e), ERR)

    @staticmethod
    def _clean_error(e):
        msg = re.sub(r"\x1b\[[0-9;]*m", "", str(e)).replace("ERROR:", "").strip()
        low = msg.lower()
        if "sign in to confirm" in low or "not a bot" in low:
            return ("YouTube wants proof you're not a bot. Use the 'YouTube sign-in' box above: pick the browser "
                    "where you're logged in to YouTube (Firefox is the most reliable), then press Analyze again.")
        if "cookie" in low and any(k in low for k in ("decrypt", "copy", "dpapi", "locked", "could not find")):
            return ("Couldn't read cookies from that browser. Close it completely and try again, "
                    "or choose Firefox, or export a cookies.txt file and select it.")
        msg = msg.splitlines()[0] if msg else "Unknown error"
        return f"{msg}\nIf this keeps happening, install the latest ClipFlow release — YouTube changes often."

    def open_folder(self):
        try:
            if self.last_file and os.path.exists(self.last_file):
                subprocess.Popen(["explorer", "/select,", os.path.normpath(self.last_file)])
            else:
                os.startfile(self.folder_var.get())  # type: ignore[attr-defined]
        except Exception:
            pass


def main():
    App().mainloop()
