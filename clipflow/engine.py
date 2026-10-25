"""Download engine: a thin, GUI-independent layer on top of yt-dlp."""
from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass, field
from typing import Callable, Optional

import yt_dlp
from yt_dlp.utils import DownloadCancelled, download_range_func

QUALITY_NAMES = {4320: "8K", 2160: "4K", 1440: "2K"}
VIDEO_CONTAINERS = ["MP4", "MKV", "WEBM"]
AUDIO_FORMATS = ["MP3", "M4A", "FLAC", "WAV"]
AUDIO_BITRATES = ["320", "256", "192", "128"]
BEST = "Best available"
BROWSERS = ["Firefox", "Chrome", "Edge", "Brave", "Opera", "Vivaldi"]
# user-chosen sign-in source (fixes "Sign in to confirm you're not a bot")
SETTINGS = {"browser": "", "cookiefile": ""}


# ----------------------------------------------------------------- helpers
def app_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def find_tool(name: str) -> Optional[str]:
    """Looks for a bundled tool (ffmpeg.exe, deno.exe) next to the app, then in ./bin."""
    for base in (app_dir(), os.path.join(app_dir(), "bin")):
        p = os.path.join(base, name)
        if os.path.isfile(p):
            return p
    return None


def fmt_time(sec: float) -> str:
    sec = max(0.0, float(sec))
    whole = int(sec)
    frac = sec - whole
    h, rem = divmod(whole, 3600)
    m, s = divmod(rem, 60)
    base = f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"
    if frac >= 0.05:
        base += f"{frac:.1f}"[1:]  # ".5"
    return base


def parse_time(text: str) -> float:
    """Accepts '90', '1:30', '1:02:03', '1:02:03.5'. Raises ValueError on bad input."""
    text = text.strip()
    if not text:
        raise ValueError("empty")
    parts = text.split(":")
    if len(parts) > 3:
        raise ValueError("too many parts")
    total = 0.0
    for p in parts:
        total = total * 60 + float(p)
    if total < 0:
        raise ValueError("negative")
    return total


def file_tag(start: float, end: float) -> str:
    def one(v: float) -> str:
        v = int(round(v))
        h, rem = divmod(v, 3600)
        m, s = divmod(rem, 60)
        return f"{h}h{m:02d}m{s:02d}s" if h else f"{m}m{s:02d}s"

    return f"{one(start)}-{one(end)}"


def quality_label(height: int) -> str:
    name = QUALITY_NAMES.get(height)
    return f"{height}p ({name})" if name else f"{height}p"


def parse_quality(label: str) -> Optional[int]:
    m = re.match(r"(\d+)p", label)
    return int(m.group(1)) if m else None


# ------------------------------------------------------------------- types
@dataclass
class VideoInfo:
    url: str
    title: str
    uploader: str
    duration: int
    thumbnail: Optional[str]
    heights: list = field(default_factory=list)
    is_live: bool = False

    @property
    def quality_labels(self) -> list:
        return [BEST] + [quality_label(h) for h in self.heights]


@dataclass
class Request:
    url: str
    folder: str
    mode: str = "video"            # "video" | "audio"
    height: Optional[int] = None   # None = best available
    container: str = "mp4"
    audio_format: str = "mp3"
    bitrate: str = "192"
    start: Optional[float] = None  # set both start and end to trim
    end: Optional[float] = None

    @property
    def trimmed(self) -> bool:
        return self.start is not None and self.end is not None


ProgressCb = Callable[[Optional[float], str], None]


# ------------------------------------------------------------------ engine
def base_opts() -> dict:
    opts = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "windowsfilenames": True,
        "retries": 10,
        "fragment_retries": 10,
        "concurrent_fragment_downloads": 4,
    }
    cookiefile = SETTINGS.get("cookiefile")
    if cookiefile and os.path.isfile(cookiefile):
        opts["cookiefile"] = cookiefile
    elif SETTINGS.get("browser"):
        opts["cookiesfrombrowser"] = (SETTINGS["browser"].lower(),)
    ffmpeg = find_tool("ffmpeg.exe")
    if ffmpeg:
        opts["ffmpeg_location"] = os.path.dirname(ffmpeg)
    deno = find_tool("deno.exe")
    if deno:  # YouTube needs a JS runtime for its challenges
        opts["js_runtimes"] = {"deno": {"path": deno}}
    return opts


def fetch_info(url: str) -> VideoInfo:
    opts = base_opts() | {"skip_download": True}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
    if info.get("entries"):  # playlist url -> first entry
        info = next(iter(info["entries"]))
    heights = sorted(
        {f["height"] for f in info.get("formats", []) if f.get("height") and f.get("vcodec") not in (None, "none")},
        reverse=True,
    )
    return VideoInfo(
        url=url,
        title=info.get("title") or "Untitled",
        uploader=info.get("uploader") or info.get("channel") or "",
        duration=int(info.get("duration") or 0),
        thumbnail=info.get("thumbnail"),
        heights=heights,
        is_live=bool(info.get("is_live")),
    )


def build_opts(req: Request, hook=None, pp_hook=None) -> dict:
    opts = base_opts()
    tag = f" [{file_tag(req.start, req.end)}]" if req.trimmed else ""
    opts["outtmpl"] = os.path.join(req.folder, f"%(title).150s{tag}.%(ext)s")
    opts["addmetadata"] = True

    if req.mode == "audio":
        codec = req.audio_format.lower()
        opts["format"] = "ba/b"
        pp = {"key": "FFmpegExtractAudio", "preferredcodec": codec}
        if codec in ("mp3", "m4a"):
            pp["preferredquality"] = req.bitrate
        opts["postprocessors"] = [pp]
    else:
        h = req.height
        opts["format"] = f"bv*[height<={h}]+ba/b[height<={h}]" if h else "bv*+ba/b"
        container = req.container.lower()
        opts["merge_output_format"] = container
        if container == "mp4":      # prefer the most compatible codecs at each resolution
            opts["format_sort"] = ["res", "fps", "vcodec:h264", "acodec:aac"]
        elif container == "webm":
            opts["format_sort"] = ["res", "fps", "vcodec:vp9", "acodec:opus"]

    if req.trimmed:
        opts["download_ranges"] = download_range_func(None, [(req.start, req.end)])
        opts["force_keyframes_at_cuts"] = True  # frame-accurate cuts

    if hook:
        opts["progress_hooks"] = [hook]
    if pp_hook:
        opts["postprocessor_hooks"] = [pp_hook]
    return opts


class Cancelled(Exception):
    pass


def download(req: Request, on_progress: ProgressCb, cancel_flag) -> Optional[str]:
    """Runs the download. `cancel_flag` is a threading.Event. Returns the output file path."""
    parts = 1 if req.mode == "audio" else 2
    state = {"done": 0}

    def hook(d):
        if cancel_flag.is_set():
            raise DownloadCancelled()
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            what = "audio" if req.mode == "audio" else ("video" if state["done"] == 0 else "audio")
            if total:
                frac = (state["done"] + d["downloaded_bytes"] / total) / parts
                speed = (d.get("_speed_str") or "").strip()
                eta = (d.get("_eta_str") or "").strip()
                on_progress(min(frac, 0.99), f"Downloading {what}…  {(d.get('_percent_str') or '').strip()}   {speed}   ETA {eta}")
            else:
                on_progress(None, "Downloading selected section…")
        elif d["status"] == "finished":
            state["done"] += 1

    def pp_hook(d):
        if d["status"] == "started":
            on_progress(None, f"Processing ({d.get('postprocessor', 'ffmpeg')})…")

    try:
        with yt_dlp.YoutubeDL(build_opts(req, hook, pp_hook)) as ydl:
            info = ydl.extract_info(req.url, download=True)
        downloads = info.get("requested_downloads") or []
        return downloads[0].get("filepath") if downloads else None
    except DownloadCancelled as e:
        raise Cancelled() from e
    except yt_dlp.utils.DownloadError as e:
        if cancel_flag.is_set():
            raise Cancelled() from e
        raise
