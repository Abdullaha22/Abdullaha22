import asyncio
import shutil
import uuid
from pathlib import Path
from urllib.parse import urlparse

import yt_dlp

from .config import DOWNLOADS, FFMPEG, MAX_ITEMS

SEM = asyncio.Semaphore(2)
IMAGE = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
VIDEO = {".mp4", ".m4v", ".mov", ".webm", ".mkv"}


def valid_url(value):
    parsed = urlparse((value or "").strip())
    return parsed.scheme in ("http", "https") and bool(parsed.hostname)


def host(value):
    return (urlparse(value).hostname or "unknown").lower().removeprefix("www.")


def _inspect(value):
    options = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": False,
        "socket_timeout": 25,
        "playlistend": MAX_ITEMS,
    }
    with yt_dlp.YoutubeDL(options) as downloader:
        return downloader.extract_info(value, download=False)


async def inspect(value):
    if not valid_url(value):
        raise ValueError("الرابط غير صحيح")
    return await asyncio.to_thread(_inspect, value)


def _download(value, folder, mode, quality, selected):
    options = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": False,
        "socket_timeout": 35,
        "retries": 4,
        "fragment_retries": 4,
        "cachedir": False,
        "continuedl": True,
        "windowsfilenames": True,
        "ffmpeg_location": FFMPEG,
        "playlistend": MAX_ITEMS,
        "outtmpl": str(folder / "%(playlist_index)03d_%(title).65s.%(ext)s"),
    }

    if selected:
        clean = sorted({int(item) for item in selected if 1 <= int(item) <= MAX_ITEMS})
        if not clean:
            raise ValueError("لم يتم تحديد عناصر صالحة")
        options["playlist_items"] = ",".join(map(str, clean))

    if mode == "audio":
        options.update(
            format="bestaudio/best",
            postprocessors=[{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
        )
    else:
        if quality == "best":
            fmt = "bestvideo*+bestaudio/best"
        else:
            if str(quality) not in {"360", "480", "720", "1080"}:
                raise ValueError("جودة الفيديو غير صالحة")
            fmt = (
                f"bestvideo[height<={int(quality)}]+bestaudio/"
                f"best[height<={int(quality)}]/best"
            )
        options.update(format=fmt, merge_output_format="mp4")

    with yt_dlp.YoutubeDL(options) as downloader:
        info = downloader.extract_info(value, download=True)

    paths = sorted(
        [path for path in folder.iterdir() if path.is_file() and path.stat().st_size],
        key=lambda path: path.name.lower(),
    )
    if mode == "audio":
        paths = [path for path in paths if path.suffix.lower() == ".mp3"]
    if not paths:
        raise RuntimeError("لم ينتج التنزيل ملفاً قابلاً للإرسال")
    return paths, info


async def download(value, mode, quality="best", selected=None):
    folder = DOWNLOADS / uuid.uuid4().hex
    folder.mkdir(parents=True, exist_ok=True)
    try:
        async with SEM:
            paths, info = await asyncio.to_thread(
                _download, value, folder, mode, quality, selected
            )
        return folder, paths, info
    except Exception:
        shutil.rmtree(folder, ignore_errors=True)
        raise


def cleanup(folder):
    shutil.rmtree(folder, ignore_errors=True)


def is_image(path):
    return Path(path).suffix.lower() in IMAGE


def is_video(path):
    return Path(path).suffix.lower() in VIDEO
