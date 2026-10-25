# ClipFlow

Download videos in any quality (up to 8K when available), grab just the audio (MP3 / M4A / FLAC / WAV),
or cut **only the part you want** with a visual trim timeline. Built on yt-dlp + ffmpeg.

## Get the installer (GitHub)

1. Create a GitHub repository and upload this folder's contents (make sure `.github/workflows/build.yml` is at the repo root).
2. Every upload/commit starts the **Build Windows installer** workflow in the **Actions** tab automatically.
3. When it turns green, open **Releases** (right side of the repo page) and download `ClipFlow-Setup-<version>.exe`. Double-click to install.

> YouTube changes often. If downloads start failing, just push any small change — every build pulls the latest yt-dlp.

## Run from source

```
pip install -r requirements.txt
# put ffmpeg.exe and deno.exe in ./bin (or on PATH)
python main.py
```

## Notes
- Only download content you own or have permission to save; downloading from YouTube may violate its Terms of Service.
- Regenerate the icon with `python scripts/make_icon.py`.
