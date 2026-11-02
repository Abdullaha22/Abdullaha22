import logging, os
from pathlib import Path
import imageio_ffmpeg
ROOT = Path(__file__).resolve().parent.parent
DATA = Path(os.getenv("NEXUS_DATA_DIR", ROOT / "data"))
DOWNLOADS = Path(os.getenv("NEXUS_DOWNLOAD_DIR", DATA / "downloads"))
DB = Path(os.getenv("NEXUS_DB_PATH", DATA / "nexus.sqlite3"))
TOKEN = os.getenv("BOT_TOKEN", "").strip()
OWNER_ID = int(os.getenv("OWNER_ID", "5249057606"))
MAX_FILE = int(os.getenv("MAX_UPLOAD_BYTES", str(49 * 1024 * 1024)))
MAX_ITEMS = int(os.getenv("MAX_PLAYLIST_ITEMS", "10"))
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
DATA.mkdir(parents=True, exist_ok=True); DOWNLOADS.mkdir(parents=True, exist_ok=True)
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(name)s: %(message)s")
LOG = logging.getLogger("nexus")
