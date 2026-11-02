import os, re, json, uuid, shutil, asyncio, logging
from pathlib import Path
from urllib.parse import urlparse
import yt_dlp
import imageio_ffmpeg
from telegram import (Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, InputMediaPhoto, InputMediaVideo)
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

TOKEN = os.getenv('BOT_TOKEN', '').strip()
OWNER_ID = 5249057606
ROOT = Path(__file__).resolve().parent
DOWNLOADS = ROOT / 'downloads'
ACCESS = ROOT / 'access.json'
MAX_SIZE = 49 * 1024 * 1024
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
log = logging.getLogger('nexus')
DOWNLOADS.mkdir(exist_ok=True)
MENU = ReplyKeyboardMarkup([['📩 الدعم الفني'], ['⚙️ الإعدادات', '📊 معلومات البوت'], ['❓ المساعدة', '❌ إلغاء']], resize_keyboard=True)
URL_RE = re.compile(r'^https?://', re.I)

def access_data():
    default = {'mode':'public', 'allowed_users':[]}
    try:
        d = json.loads(ACCESS.read_text(encoding='utf-8'))
        return {'mode': d.get('mode') if d.get('mode') in ('public','private') else 'public', 'allowed_users': d.get('allowed_users', []) if isinstance(d.get('allowed_users', []), list) else []}
    except FileNotFoundError: return default
    except Exception:
        log.exception('access.json read error'); return default

def save_access(d): ACCESS.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')
def owner(update): return bool(update.effective_user and update.effective_user.id == OWNER_ID)
def allowed(update):
    u=update.effective_user
    if not u: return False
    d=access_data()
    return owner(update) or d['mode']=='public' or u.id in d['allowed_users']
async def deny(update):
    if update.callback_query: await update.callback_query.answer('البوت خاص حالياً.', show_alert=True)
    elif update.effective_message: await update.effective_message.reply_text('🔒 البوت خاص حالياً.')

def kb(*rows): return InlineKeyboardMarkup([[InlineKeyboardButton(t, callback_data=c) for t,c in row] for row in rows])
def ydl_opts(folder, mode='video', quality='best', inspect=False):
    o={'quiet':True,'no_warnings':True,'noplaylist':False,'socket_timeout':30,'retries':5,'fragment_retries':5,'file_access_retries':3,'windowsfilenames':True,'continuedl':True,'cachedir':False,'ffmpeg_location':FFMPEG,'outtmpl':str(folder/'%(playlist_index|)03d_%(title).60s.%(ext)s')}
    if inspect: o['skip_download']=True
    elif mode=='mp3':
        o.update(format='bestaudio/best',postprocessors=[{'key':'FFmpegExtractAudio','preferredcodec':'mp3','preferredquality':'192'}])
    else:
        fmt='bestvideo*+bestaudio/best' if quality=='best' else f'bestvideo[height<={quality}]+bestaudio/best[height<={quality}]/best'
        o.update(format=fmt,merge_output_format='mp4')
    return o

def inspect_url(url):
    with yt_dlp.YoutubeDL({'quiet':True,'no_warnings':True,'noplaylist':False}) as y: return y.extract_info(url, download=False)

def do_download(url, folder, mode, quality='best', selected=None):
    opts=ydl_opts(folder, mode, quality)
    if selected is not None: opts['playlist_items']=','.join(str(i+1) for i in selected)
    with yt_dlp.YoutubeDL(opts) as y: info=y.extract_info(url, download=True)
    files=[p for p in folder.iterdir() if p.is_file() and p.stat().st_size]
    if mode=='mp3': files=[p for p in files if p.suffix.lower()=='.mp3'] or files
    files.sort(key=lambda p:p.name.lower())
    if not files: raise RuntimeError('لم يتم إنشاء ملفات قابلة للإرسال.')
    return files, info

async def start(update:Update, context:ContextTypes.DEFAULT_TYPE):
    if not allowed(update): return await deny(update)
    name=update.effective_user.first_name or 'صديقي'
    await update.message.reply_text(
        '╭━━━━━━━━━━━━━━━━━━━━╮\n       ◈ N E X U S ◈\n╰━━━━━━━━━━━━━━━━━━━━╯\n\n'
        f'أهلاً بك، {name} ✨\nMEDIA DOWNLOADER PRO\nNEXUS EDITION V4\n\n'
        'مركزك الذكي لتنزيل الوسائط من مكان واحد.\n\n'
        '🎬 فيديوهات وReels ومقاطع قصيرة\n🖼️ صور وألبومات\n🎵 استخراج الصوت MP3\n⚡ اختيار الجودة والعناصر\n📩 دعم فني مباشر\n\n'
        'أرسل الرابط مباشرة حتى أفحص المحتوى وأعرض خيارات التنزيل.\n\nᴘᴏᴡᴇʀᴇᴅ ʙʏ NEXUS', reply_markup=MENU)

async def help_cmd(update, context):
    if not allowed(update): return await deny(update)
    await update.effective_message.reply_text('أرسل رابط المحتوى مباشرة، ثم اختر فيديو أو MP3 والجودة. قد لا تعمل الروابط الخاصة أو المحمية أو التي تتطلب تسجيل دخول. استخدم فقط محتوى تملك حق تنزيله.')
async def myid(update, context): await update.effective_message.reply_text(f'🆔 ID: {update.effective_user.id}')
async def admin(update, context):
    if not owner(update): return await update.effective_message.reply_text('⛔ للمالك فقط.')
    d=access_data()
    await update.effective_message.reply_text(f"👑 لوحة المالك\nالوضع: {d['mode']}\nالمستخدمون: {len(d['allowed_users'])}\n/mode public أو /mode private\n/allow USER_ID\n/remove USER_ID\n/users", reply_markup=kb([('🌍 عام','adm:public'),('🔒 خاص','adm:private')]))
async def mode_cmd(update, context):
    if not owner(update): return await update.effective_message.reply_text('⛔ للمالك فقط.')
    if not context.args or context.args[0] not in ('public','private'): return await update.effective_message.reply_text('الاستخدام: /mode public أو /mode private')
    d=access_data(); d['mode']=context.args[0]; save_access(d); await update.effective_message.reply_text('✅ تم تحديث وضع الوصول.')
async def allow_cmd(update, context):
    if not owner(update): return await update.effective_message.reply_text('⛔ للمالك فقط.')
    try: uid=int(context.args[0])
    except (IndexError,ValueError): return await update.effective_message.reply_text('الاستخدام: /allow USER_ID')
    d=access_data()
    if uid not in d['allowed_users']: d['allowed_users'].append(uid)
    save_access(d); await update.effective_message.reply_text(f'✅ تمت إضافة {uid}.')
async def remove_cmd(update, context):
    if not owner(update): return await update.effective_message.reply_text('⛔ للمالك فقط.')
    try: uid=int(context.args[0])
    except (IndexError,ValueError): return await update.effective_message.reply_text('الاستخدام: /remove USER_ID')
    if uid==OWNER_ID: return await update.effective_message.reply_text('لا يمكن حذف المالك.')
    d=access_data(); d['allowed_users']=[x for x in d['allowed_users'] if x!=uid]; save_access(d); await update.effective_message.reply_text('🗑️ تمت الإزالة.')
async def users_cmd(update, context):
    if not owner(update): return await update.effective_message.reply_text('⛔ للمالك فقط.')
    d=access_data(); await update.effective_message.reply_text('الوضع: '+d['mode']+'\n'+('\n'.join(map(str,d['allowed_users'])) or 'لا يوجد مستخدمون.'))
async def info_cmd(update, context):
    if not allowed(update): return await deny(update)
    await update.effective_message.reply_text(f"MEDIA DOWNLOADER PRO | NEXUS EDITION V4\nFFmpeg: {'جاهز' if FFMPEG else 'غير متوفر'}\nحد الملف المرسل بهذا الإصدار: 49 MB")

async def support_start(update, context):
    context.user_data['support']=True
    await update.effective_message.reply_text('📩 اكتب رسالتك أو أرسل صورة/ملف يوضح المشكلة. سأوصلها للمالك. للإلغاء اضغط ❌ إلغاء.')
async def support_send(update, context):
    m=update.effective_message; u=update.effective_user
    try:
        copied=await context.bot.copy_message(OWNER_ID, m.chat_id, m.message_id)
        await context.bot.send_message(OWNER_ID, f'📩 طلب دعم جديد\nالاسم: {u.full_name}\nالمعرف: @{u.username or "غير متوفر"}\nID: {u.id}', reply_to_message_id=copied.message_id)
        await m.reply_text('✅ وصلت رسالتك للدعم الفني.')
    except Exception:
        log.exception('support forwarding failed'); await m.reply_text('⚠️ تعذر إرسال الرسالة حالياً.')
    context.user_data.pop('support',None)
async def owner_reply(update, context):
    m=update.effective_message
    if not owner(update) or not m.reply_to_message: return False
    # Reply to the metadata message sent after the copied support content.
    s=m.reply_to_message.text or m.reply_to_message.caption or ''
    match=re.search(r'\bID:\s*(\d+)',s)
    if not match: return False
    body=m.text or m.caption or ''
    try:
        if m.photo: await context.bot.send_photo(int(match.group(1)),m.photo[-1].file_id,caption=body or '📩 رد الدعم الفني')
        elif m.document: await context.bot.send_document(int(match.group(1)),m.document.file_id,caption=body or '📩 رد الدعم الفني')
        else: await context.bot.send_message(int(match.group(1)),'📩 رد الدعم الفني:\n\n'+(body or 'تم استلام رد من الدعم.'))
        await m.reply_text('✅ تم إرسال الرد.')
    except Exception: log.exception('owner support reply failed'); await m.reply_text('⚠️ تعذر إرسال الرد.')
    return True

async def text_handler(update, context):
    if not allowed(update): return await deny(update)
    m=update.effective_message; text=(m.text or '').strip()
    if owner(update) and await owner_reply(update,context): return
    if text=='❌ إلغاء':
        context.user_data.clear(); return await m.reply_text('تم إلغاء العملية.',reply_markup=MENU)
    if text=='📩 الدعم الفني': return await support_start(update,context)
    if context.user_data.get('support'): return await support_send(update,context)
    if text=='❓ المساعدة': return await help_cmd(update,context)
    if text=='📊 معلومات البوت': return await info_cmd(update,context)
    if text=='⚙️ الإعدادات': return await m.reply_text('اختر الجودة بعد إرسال الرابط. ويمكنك اختيار استخراج الصوت MP3.')
    if not URL_RE.match(text) or not urlparse(text).netloc: return await m.reply_text('أرسل رابطاً صحيحاً يبدأ بـ https:// أو http://.')
    context.user_data['url']=text
    status=await m.reply_text('🔎 أفحص الرابط وأتعرف على الوسائط...')
    try:
        info=await asyncio.to_thread(inspect_url,text)
        if not info: raise RuntimeError('لم أتمكن من قراءة الرابط.')
        entries=info.get('entries')
        if entries:
            entries=[e for e in entries if e]
            context.user_data['pending']={'url':text,'count':min(len(entries),10),'selected':[]}
            buttons=[]
            for i in range(min(len(entries),10)):
                buttons.append([(f'⬜ العنصر {i+1}',f'pick:{i}')])
            buttons += [[('📥 تنزيل الكل','all')],[('✅ تنزيل المحدد','chosen')],[('❌ إلغاء','cancel')]]
            await status.edit_text(f'🖼️ وجدت {len(entries)} عناصر. اختر العناصر المطلوبة أو نزّل الكل.',reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(t,callback_data=c) for t,c in row] for row in buttons]))
        else:
            context.user_data['pending']={'url':text}
            await status.edit_text(f"تم التعرف على المحتوى:\n{(info.get('title') or 'Media')[:160]}\nاختر المطلوب:",reply_markup=kb([('🎬 فيديو','video'),('🎵 MP3','mp3')],[('❌ إلغاء','cancel')]))
    except Exception as e:
        log.exception('inspect failed'); await status.edit_text('❌ تعذر قراءة الرابط. قد يكون خاصاً أو يتطلب تسجيل دخول أو غير مدعوم.\n'+str(e)[:220])

async def deliver(message, files, mode, status):
    too_big=[p for p in files if p.stat().st_size>MAX_SIZE]
    files=[p for p in files if p.stat().st_size<=MAX_SIZE]
    if too_big: await status.edit_text('⚠️ بعض الملفات تجاوزت حد الإرسال (49 MB) ولم تُرسل: '+', '.join(p.name for p in too_big[:4]))
    if not files: return
    if mode=='mp3':
        for p in files:
            with p.open('rb') as f: await message.reply_audio(f,title=p.stem[:64],caption='MEDIA DOWNLOADER PRO | NEXUS')
        await status.delete(); return
    for start in range(0,len(files),10):
        group=files[start:start+10]
        if len(group)==1:
            p=group[0]
            with p.open('rb') as f:
                if p.suffix.lower() in ('.jpg','.jpeg','.png','.webp'): await message.reply_photo(f)
                else: await message.reply_video(f,supports_streaming=True)
        else:
            opened=[]; media=[]
            try:
                for p in group:
                    f=p.open('rb'); opened.append(f)
                    if p.suffix.lower() in ('.jpg','.jpeg','.png','.webp'): media.append(InputMediaPhoto(f))
                    else: media.append(InputMediaVideo(f,supports_streaming=True))
                await message.reply_media_group(media)
            finally:
                for f in opened: f.close()
    await status.delete()

async def do_job(q, context, mode='video', quality='best', selected=None):
    p=context.user_data.get('pending') or {}; url=p.get('url') or context.user_data.get('url')
    if not url: return await q.message.reply_text('انتهت صلاحية الطلب. أرسل الرابط مجدداً.')
    status=await q.message.reply_text('⏳ جارٍ التنزيل والمعالجة...')
    folder=DOWNLOADS/uuid.uuid4().hex; folder.mkdir(parents=True,exist_ok=True)
    try:
        files,info=await asyncio.to_thread(do_download,url,folder,mode,quality,selected)
        await deliver(q.message,files,mode,status)
    except Exception as e:
        log.exception('download failed'); await status.edit_text('❌ فشل التنزيل. قد يكون المحتوى محمياً أو غير مدعوم أو أكبر من حدود المنصة.\n'+str(e)[:250])
    finally:
        shutil.rmtree(folder,ignore_errors=True); context.user_data.pop('pending',None); context.user_data.pop('url',None)

async def callbacks(update, context):
    q=update.callback_query
    if not allowed(update): return await deny(update)
    data=q.data or ''; await q.answer()
    if data.startswith('adm:'):
        if not owner(update): return await q.answer('للمالك فقط',show_alert=True)
        d=access_data(); d['mode']=data.split(':')[1]; save_access(d); return await q.edit_message_text('✅ تم تغيير الوضع إلى '+d['mode'])
    if data=='cancel': context.user_data.pop('pending',None); context.user_data.pop('url',None); return await q.edit_message_text('❌ تم الإلغاء.')
    if data=='video': return await q.edit_message_text('اختر جودة الفيديو:',reply_markup=kb([('💎 1080p','q:1080'),('🔥 720p','q:720')],[('📱 480p','q:480'),('⚡ 360p','q:360')],[('🌟 أفضل جودة','q:best')],[('❌ إلغاء','cancel')]))
    if data=='mp3': return await do_job(q,context,'mp3')
    if data.startswith('q:'): return await do_job(q,context,'video',data.split(':')[1])
    if data.startswith('pick:'):
        p=context.user_data.get('pending')
        if not p: return await q.edit_message_text('انتهى الطلب. أرسل الرابط مجدداً.')
        i=int(data.split(':')[1]); s=set(p.get('selected',[])); s.symmetric_difference_update({i}); p['selected']=sorted(s)
        return await q.answer(f'المحدد: {len(s)}')
    if data=='chosen':
        p=context.user_data.get('pending') or {}; s=p.get('selected',[])
        if not s: return await q.answer('حدد عنصراً أولاً.',show_alert=True)
        return await do_job(q,context,'video','best',s)
    if data=='all': return await do_job(q,context,'video','best')

async def errors(update,context): log.error('Telegram handler error: %s',context.error)
def main():
    if not TOKEN: raise RuntimeError('BOT_TOKEN is missing from environment variables.')
    app=Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler('start',start)); app.add_handler(CommandHandler('help',help_cmd)); app.add_handler(CommandHandler('id',myid))
    app.add_handler(CommandHandler('admin',admin)); app.add_handler(CommandHandler('mode',mode_cmd)); app.add_handler(CommandHandler('allow',allow_cmd)); app.add_handler(CommandHandler('remove',remove_cmd)); app.add_handler(CommandHandler('users',users_cmd))
    app.add_handler(CallbackQueryHandler(callbacks)); app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,text_handler))
    app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO | filters.Document.ALL,text_handler)); app.add_error_handler(errors)
    log.info('NEXUS V4 started; ffmpeg=%s',FFMPEG); app.run_polling()
if __name__=='__main__': main()
