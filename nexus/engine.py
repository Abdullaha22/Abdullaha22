import asyncio, shutil, uuid
from pathlib import Path
from urllib.parse import urlparse
import yt_dlp
from .config import DOWNLOADS, FFMPEG
SEM=asyncio.Semaphore(2)
IMAGE={".jpg",".jpeg",".png",".webp",".gif"}
def valid_url(s):
    p=urlparse((s or "").strip()); return p.scheme in ("http","https") and bool(p.netloc)
def host(s): return (urlparse(s).hostname or "unknown").lower().removeprefix("www.")
def _inspect(s):
    with yt_dlp.YoutubeDL({"quiet":True,"no_warnings":True,"noplaylist":False,"socket_timeout":25}) as y: return y.extract_info(s,download=False)
async def inspect(s):
    if not valid_url(s): raise ValueError("الرابط غير صحيح")
    return await asyncio.to_thread(_inspect,s)
def _download(s,folder,mode,quality,selected):
    o={"quiet":True,"no_warnings":True,"noplaylist":False,"socket_timeout":35,"retries":4,"fragment_retries":4,"cachedir":False,"continuedl":True,"windowsfilenames":True,"ffmpeg_location":FFMPEG,"outtmpl":str(folder/"%(playlist_index)03d_%(title).65s.%(ext)s")}
    if selected: o["playlist_items"]=",".join(map(str,selected))
    if mode=="audio": o.update(format="bestaudio/best",postprocessors=[{"key":"FFmpegExtractAudio","preferredcodec":"mp3","preferredquality":"192"}])
    else:
        fmt="bestvideo*+bestaudio/best" if quality=="best" else f"bestvideo[height<={int(quality)}]+bestaudio[height<={int(quality)}]/best[height<={int(quality)}]/best"
        o.update(format=fmt,merge_output_format="mp4")
    with yt_dlp.YoutubeDL(o) as y: info=y.extract_info(s,download=True)
    paths=sorted([p for p in folder.iterdir() if p.is_file() and p.stat().st_size],key=lambda p:p.name.lower())
    if mode=="audio": paths=[p for p in paths if p.suffix.lower()==".mp3"]
    if not paths: raise RuntimeError("لم ينتج التنزيل ملفاً قابلاً للإرسال")
    return paths,info
async def download(s,mode,quality="best",selected=None):
    folder=DOWNLOADS/uuid.uuid4().hex; folder.mkdir(parents=True)
    try:
        async with SEM: paths,info=await asyncio.to_thread(_download,s,folder,mode,quality,selected)
        return folder,paths,info
    except Exception: shutil.rmtree(folder,ignore_errors=True); raise
def cleanup(folder): shutil.rmtree(folder,ignore_errors=True)
def is_image(p:Path): return p.suffix.lower() in IMAGE
