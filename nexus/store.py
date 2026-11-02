import json, sqlite3
from datetime import datetime, timezone
from .config import DATA, DB, OWNER_ID
ACCESS = DATA / "access.json"
def _db():
    c=sqlite3.connect(DB, timeout=20); c.execute("PRAGMA journal_mode=WAL"); return c
def init_db():
    with _db() as c:
        c.execute("CREATE TABLE IF NOT EXISTS users(user_id INTEGER PRIMARY KEY, username TEXT, full_name TEXT, first_seen TEXT, last_seen TEXT, requests INTEGER DEFAULT 0)")
        c.execute("CREATE TABLE IF NOT EXISTS downloads(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,host TEXT,title TEXT,mode TEXT,status TEXT,created_at TEXT)")
def touch(user):
    now=datetime.now(timezone.utc).isoformat()
    with _db() as c:
        c.execute("INSERT INTO users VALUES(?,?,?,?,?,1) ON CONFLICT(user_id) DO UPDATE SET username=excluded.username,full_name=excluded.full_name,last_seen=excluded.last_seen,requests=users.requests+1",(user.id,user.username,user.full_name,now,now))
def log_job(uid,host,title,mode,status):
    with _db() as c: c.execute("INSERT INTO downloads(user_id,host,title,mode,status,created_at) VALUES(?,?,?,?,?,?)",(uid,host,(title or "")[:240],mode,status,datetime.now(timezone.utc).isoformat()))
def stats():
    with _db() as c:
        return (c.execute("SELECT COUNT(*) FROM users").fetchone()[0],c.execute("SELECT COUNT(*) FROM downloads").fetchone()[0])
def access():
    try:
        d=json.loads(ACCESS.read_text(encoding="utf-8")); mode=d.get("mode","public"); users=d.get("allowed_users",[])
        return {"mode":mode if mode in ("public","private") else "public","allowed_users":[int(x) for x in users if str(x).isdigit()]}
    except Exception: return {"mode":"public","allowed_users":[]}
def save_access(d):
    safe={"mode":d.get("mode","public"),"allowed_users":sorted(set(int(x) for x in d.get("allowed_users",[]) if str(x).isdigit()))}
    tmp=ACCESS.with_suffix(".tmp"); tmp.write_text(json.dumps(safe,ensure_ascii=False,indent=2),encoding="utf-8"); tmp.replace(ACCESS)
def owner(user): return bool(user and user.id==OWNER_ID)
def allowed(user):
    if not user: return False
    d=access(); return owner(user) or d["mode"]=="public" or user.id in d["allowed_users"]
