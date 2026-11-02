import logging, re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, InputMediaPhoto, InputMediaVideo
from telegram.ext import ContextTypes
from . import BRAND, VERSION
from .config import LOG, OWNER_ID, MAX_FILE, MAX_ITEMS, FFMPEG
from .store import allowed, owner, access, save_access, touch, log_job, stats
from .engine import inspect, download, cleanup, valid_url, host, is_image
MENU=ReplyKeyboardMarkup([["📩 الدعم الفني"],["📊 معلومات البوت","⚙️ الإعدادات"],["❓ المساعدة","❌ إلغاء"]],resize_keyboard=True)
def ik(*rows): return InlineKeyboardMarkup([[InlineKeyboardButton(a,callback_data=b) for a,b in r] for r in rows])
def playlist_kb(n,selected):
    rows=[[(('☑️ ' if i in selected else '⬜ ')+f'العنصر {i}',f'pick:{i}')] for i in range(1,n+1)]
    rows += [[("📥 تنزيل الكل","all")],[ ("✅ تنزيل المحدد","selected") ],[("❌ إلغاء","cancel")]]
    return ik(*rows)
async def deny(u):
    if u.callback_query: await u.callback_query.answer("البوت خاص حالياً",show_alert=True)
    elif u.effective_message: await u.effective_message.reply_text("🔒 البوت خاص حالياً")
async def start(u,c):
    if not allowed(u.effective_user): return await deny(u)
    touch(u.effective_user); name=u.effective_user.first_name or "صديقي"
    await u.effective_message.reply_text(f"◈ N E X U S ◈\nأهلاً بك {name} ✨\nMEDIA DOWNLOADER PRO — V{VERSION}\n\nأرسل الرابط مباشرة حتى أفحصه وأعرض الخيارات.\n🎬 فيديو مدعوم\n🖼️ صور وألبومات عامة مدعومة\n🎵 استخراج MP3\n📩 دعم فني مباشر\n\n{BRAND}",reply_markup=MENU)
async def help_cmd(u,c):
    if not allowed(u.effective_user): return await deny(u)
    await u.effective_message.reply_text("أرسل رابطاً عاماً. الروابط الخاصة أو المحمية أو التي تتطلب تسجيل دخول قد لا تعمل. استخدم فقط محتوى تملك حق تنزيله.")
async def myid(u,c): await u.effective_message.reply_text(f"ID: {u.effective_user.id}")
async def info(u,c):
    if not allowed(u.effective_user): return await deny(u)
    users,jobs=stats(); await u.effective_message.reply_text(f"NEXUS V{VERSION}\nFFmpeg: {'جاهز' if FFMPEG else 'غير متوفر'}\nالمستخدمون: {users}\nالطلبات: {jobs}\n{BRAND}")
async def admin(u,c):
    if not owner(u.effective_user): return await u.effective_message.reply_text("للمالك فقط")
    d=access(); users,jobs=stats()
    await u.effective_message.reply_text(f"لوحة الإدارة V5\nالوضع: {d['mode']}\nالمستخدمون: {users}\nالطلبات: {jobs}\n/mode public|private\n/allow ID\n/remove ID\n/users",reply_markup=ik([("🌍 عام","admin:public"),("🔒 خاص","admin:private")]))
async def mode_cmd(u,c):
    if not owner(u.effective_user): return await u.effective_message.reply_text("للمالك فقط")
    if not c.args or c.args[0] not in ("public","private"): return await u.effective_message.reply_text("/mode public أو /mode private")
    d=access(); d["mode"]=c.args[0]; save_access(d); await u.effective_message.reply_text("تم تحديث الوضع")
async def allow_cmd(u,c):
    if not owner(u.effective_user): return await u.effective_message.reply_text("للمالك فقط")
    try: uid=int(c.args[0])
    except (IndexError,ValueError): return await u.effective_message.reply_text("/allow USER_ID")
    d=access(); d["allowed_users"].append(uid); save_access(d); await u.effective_message.reply_text("تمت الإضافة")
async def remove_cmd(u,c):
    if not owner(u.effective_user): return await u.effective_message.reply_text("للمالك فقط")
    try: uid=int(c.args[0])
    except (IndexError,ValueError): return await u.effective_message.reply_text("/remove USER_ID")
    if uid==OWNER_ID: return await u.effective_message.reply_text("لا يمكن حذف المالك")
    d=access(); d["allowed_users"]=[x for x in d["allowed_users"] if x!=uid]; save_access(d); await u.effective_message.reply_text("تمت الإزالة")
async def users_cmd(u,c):
    if not owner(u.effective_user): return await u.effective_message.reply_text("للمالك فقط")
    d=access(); await u.effective_message.reply_text(d["mode"]+"\n"+("\n".join(map(str,d["allowed_users"])) or "لا يوجد"))
async def support_send(u,c):
    m=u.effective_message; user=u.effective_user
    try:
        anchor=await c.bot.send_message(OWNER_ID,f"📩 طلب دعم\nالاسم: {user.full_name}\n@{user.username or 'غير متوفر'}\nID: {user.id}")
        await c.bot.copy_message(OWNER_ID,m.chat_id,m.message_id,reply_to_message_id=anchor.message_id)
        await m.reply_text("وصلت رسالتك للدعم الفني.")
    except Exception: LOG.exception("support forwarding failed"); await m.reply_text("تعذر إرسال الرسالة حالياً")
    finally: c.user_data.pop("support",None)
async def owner_reply(u,c):
    m=u.effective_message
    if not owner(u.effective_user) or not m.reply_to_message: return False
    match=re.search(r"ID:\s*(\d+)",m.reply_to_message.text or "")
    if not match: return False
    try: await c.bot.copy_message(int(match.group(1)),m.chat_id,m.message_id); await m.reply_text("تم إرسال الرد")
    except Exception: LOG.exception("support reply failed"); await m.reply_text("تعذر إرسال الرد")
    return True
async def send_files(msg,files,mode,status):
    good=[p for p in files if p.stat().st_size<=MAX_FILE]
    if len(good)<len(files): await msg.reply_text("بعض الملفات أكبر من حد الإرسال المحدد ولم تُرسل")
    if not good: return await status.edit_text("لا توجد ملفات ضمن حد الإرسال")
    if mode=="audio":
        for p in good:
            with p.open("rb") as f: await msg.reply_audio(f,title=p.stem[:64],caption=BRAND)
    else:
        for i in range(0,len(good),10):
            group=good[i:i+10]
            if len(group)==1:
                p=group[0]
                with p.open("rb") as f:
                    if is_image(p): await msg.reply_photo(f,caption=BRAND)
                    else: await msg.reply_video(f,supports_streaming=True,caption=BRAND)
            else:
                streams=[]; media=[]
                try:
                    for p in group:
                        f=p.open("rb"); streams.append(f); media.append(InputMediaPhoto(f) if is_image(p) else InputMediaVideo(f,supports_streaming=True))
                    await msg.reply_media_group(media)
                finally:
                    for f in streams: f.close()
    try: await status.edit_text("✅ اكتمل الإرسال\n"+BRAND)
    except Exception: pass
async def run_job(q,c,mode,quality="best",selected=None):
    p=c.user_data.get("pending",{}); url=p.get("url")
    if not url: return await q.message.reply_text("انتهى الطلب، أرسل الرابط مجدداً")
    status=await q.message.reply_text("⏳ جارٍ التنزيل..."); folder=None; title=p.get("title","Media")
    try:
        folder,files,info_data=await download(url,mode,quality,selected); title=(info_data or {}).get("title") or title
        await send_files(q.message,files,mode,status); log_job(q.from_user.id,host(url),title,mode,"success")
    except Exception as e:
        LOG.exception("download failed"); log_job(q.from_user.id,host(url),title,mode,"failed")
        try: await status.edit_text("❌ تعذر التنزيل. قد يكون المصدر غير مدعوم أو خاصاً أو محمياً.\n"+str(e)[:160])
        except Exception: pass
    finally:
        if folder: cleanup(folder)
        c.user_data.pop("pending",None)
async def text_handler(u,c):
    if not allowed(u.effective_user): return await deny(u)
    m=u.effective_message; text=(m.text or "").strip()
    if owner(u.effective_user) and await owner_reply(u,c): return
    if text=="❌ إلغاء": c.user_data.clear(); return await m.reply_text("تم الإلغاء",reply_markup=MENU)
    if text=="📩 الدعم الفني": c.user_data["support"]=True; return await m.reply_text("اكتب رسالتك أو أرسل ملفاً للدعم. للإلغاء اضغط ❌ إلغاء")
    if c.user_data.get("support"): return await support_send(u,c)
    if text=="❓ المساعدة": return await help_cmd(u,c)
    if text=="📊 معلومات البوت": return await info(u,c)
    if text=="⚙️ الإعدادات": return await m.reply_text("اختر الفيديو أو MP3 بعد إرسال الرابط")
    if not valid_url(text): return await m.reply_text("أرسل الرابط مباشرة بصيغة https:// أو http://")
    status=await m.reply_text("🔎 أفحص الرابط...")
    try:
        details=await inspect(text); entries=[x for x in (details or {}).get("entries",[]) if x]
        if entries:
            count=min(len(entries),MAX_ITEMS); c.user_data["pending"]={"url":text,"title":(details or {}).get("title","Media"),"count":count,"selected":[]}
            await status.edit_text(f"وجدت {len(entries)} عناصر. اختر من أول {count} أو نزّل الكل.",reply_markup=playlist_kb(count,set()))
        else:
            c.user_data["pending"]={"url":text,"title":(details or {}).get("title","Media")}
            await status.edit_text(f"تم التعرف على المحتوى:\n{c.user_data['pending']['title']}\nاختر:",reply_markup=ik([("🎬 فيديو","mode:video"),("🎵 MP3","mode:audio")],[("❌ إلغاء","cancel")]))
    except Exception as e: LOG.exception("inspect failed"); await status.edit_text("تعذر قراءة الرابط. تأكد أنه عام ومدعوم.\n"+str(e)[:150])
async def media_handler(u,c):
    if not allowed(u.effective_user): return await deny(u)
    if c.user_data.get("support"): return await support_send(u,c)
    await u.effective_message.reply_text("استلام الملفات المباشرة غير مفعّل بعد؛ يمكنك إرسالها عبر الدعم الفني أو إرسال رابط عام.")
async def callbacks(u,c):
    q=u.callback_query
    if not allowed(u.effective_user): return await deny(u)
    d=q.data or ""; await q.answer()
    if d.startswith("admin:"):
        if not owner(u.effective_user): return await q.answer("للمالك فقط",show_alert=True)
        a=access(); a["mode"]=d.split(":",1)[1]; save_access(a); return await q.edit_message_text("تم تغيير الوضع إلى "+a["mode"])
    if d=="cancel": c.user_data.pop("pending",None); return await q.edit_message_text("تم الإلغاء")
    if d=="mode:audio": return await run_job(q,c,"audio")
    if d=="mode:video": return await q.edit_message_text("اختر الجودة:",reply_markup=ik([("1080p","quality:1080"),("720p","quality:720")],[("480p","quality:480"),("360p","quality:360")],[("أفضل جودة","quality:best")],[("إلغاء","cancel")]))
    if d.startswith("quality:"): return await run_job(q,c,"video",d.split(":",1)[1])
    if d.startswith("pick:"):
        p=c.user_data.get("pending")
        if not p: return await q.edit_message_text("انتهى الطلب")
        i=int(d.split(":",1)[1]); s=set(p.get("selected",[])); s.symmetric_difference_update({i}); p["selected"]=sorted(s)
        return await q.edit_message_reply_markup(reply_markup=playlist_kb(p["count"],s))
    if d=="selected":
        s=c.user_data.get("pending",{}).get("selected",[])
        if not s: return await q.answer("حدد عنصراً أولاً",show_alert=True)
        return await run_job(q,c,"video","best",s)
    if d=="all": return await run_job(q,c,"video")
async def error_handler(u,c): LOG.exception("Unhandled bot error",exc_info=c.error)
