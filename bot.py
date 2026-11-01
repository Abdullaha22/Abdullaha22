import os
import re
import uuid
import asyncio
import shutil
from pathlib import Path

import yt_dlp
from telegram import (
    Update, InlineKeyboardButton,
    InlineKeyboardMarkup, ReplyKeyboardMarkup
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

# ==========================================
# NEXUS EDITION | MEDIA DOWNLOADER PRO
# ==========================================

TOKEN = os.getenv("BOT_TOKEN", "")
OWNER_ID = 5249057606

DOWNLOAD_DIR = Path("downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True)

MAX_TELEGRAM_SIZE = 49 * 1024 * 1024

BRAND = "MEDIA DOWNLOADER PRO"
EDITION = "NEXUS EDITION"

# ==========================================
# MAIN MENU
# ==========================================

MAIN_MENU = ReplyKeyboardMarkup(
    [
        ["🎬 تحميل فيديو", "🎵 تحميل MP3"],
        ["⚙️ الإعدادات", "📊 معلومات البوت"],
        ["❓ المساعدة"]
    ],
    resize_keyboard=True
)


def quality_menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("1080p • FHD", callback_data="q_1080"),
            InlineKeyboardButton("720p • HD", callback_data="q_720")
        ],
        [
            InlineKeyboardButton("480p • SD", callback_data="q_480"),
            InlineKeyboardButton("360p • LOW", callback_data="q_360")
        ],
        [
            InlineKeyboardButton("⚡ أفضل جودة", callback_data="q_best")
        ],
        [
            InlineKeyboardButton("✖ إلغاء العملية", callback_data="cancel")
        ]
    ])


def is_owner(update):
    return (
        update.effective_user is not None
        and update.effective_user.id == OWNER_ID
    )


# ==========================================
# DOWNLOAD ENGINE
# ==========================================

def download_media(url, mode, quality):
    folder = DOWNLOAD_DIR / uuid.uuid4().hex
    folder.mkdir(parents=True, exist_ok=True)

    output = str(folder / "%(title).70s.%(ext)s")

    if mode == "mp3":
        options = {
            "format": "bestaudio/best",
            "outtmpl": output,
            "noplaylist": True,
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
        }

    else:
        if quality == "best":
            fmt = "bestvideo+bestaudio/best"
        else:
            fmt = (
                f"bestvideo[height<={quality}]+bestaudio/"
                f"best[height<={quality}]/best"
            )

        options = {
            "format": fmt,
            "outtmpl": output,
            "noplaylist": True,
            "merge_output_format": "mp4",
        }

    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=True)
            filepath = Path(ydl.prepare_filename(info))

        if mode == "mp3":
            filepath = filepath.with_suffix(".mp3")
        elif not filepath.exists():
            mp4_files = list(folder.glob("*.mp4"))
            if mp4_files:
                filepath = mp4_files[0]

        if not filepath.exists():
            files = list(folder.glob("*"))
            if not files:
                raise Exception("لم يتم العثور على الملف بعد التحميل")
            filepath = files[0]

        return filepath, folder, info

    except Exception:
        shutil.rmtree(folder, ignore_errors=True)
        raise


# ==========================================
# WELCOME
# ==========================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        await update.message.reply_text(
            "🔒 هذا البوت مخصص لصاحبه حالياً."
        )
        return

    first_name = update.effective_user.first_name or "صديقي"

    welcome = (
        "╭━━━━━━━━━━━━━━━━━━╮\n"
        "      ◈ N E X U S ◈\n"
        "╰━━━━━━━━━━━━━━━━━━╯\n\n"
        f"أهلاً بك، {first_name} ✨\n\n"
        "مرحباً بك في مركز الوسائط الذكي.\n"
        "تجربة تنزيل متكاملة، صُممت لتكون\n"
        "بسيطة وسريعة وأنيقة.\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "🎬  VIDEO  | تنزيل الفيديو\n"
        "🎵  AUDIO  | استخراج الصوت MP3\n"
        "⚡  QUALITY | جودات متعددة\n"
        "🛡️  SYSTEM | واجهة منظمة\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "اختر الخدمة التي تريدها من القائمة أدناه.\n\n"
        "ᴘᴏᴡᴇʀᴇᴅ ʙʏ ᴍᴇᴅɪᴀ ᴅᴏᴡɴʟᴏᴀᴅᴇʀ ᴘʀᴏ"
    )

    await update.message.reply_text(
        welcome,
        reply_markup=MAIN_MENU
    )


# ==========================================
# TEXT HANDLER
# ==========================================

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        return

    text = update.message.text.strip()

    if text == "🎬 تحميل فيديو":
        context.user_data["mode"] = "video"
        await update.message.reply_text(
            "╭━━ ◈ VIDEO CENTER ◈ ━━╮\n\n"
            "أرسل رابط الفيديو الذي تريد تنزيله.\n\n"
            "سيكون بإمكانك اختيار الجودة المناسبة\n"
            "قبل بدء عملية التنزيل.\n\n"
            "⚡ NEXUS DOWNLOAD ENGINE"
        )
        return

    if text == "🎵 تحميل MP3":
        context.user_data["mode"] = "mp3"
        await update.message.reply_text(
            "╭━━ ◈ AUDIO CENTER ◈ ━━╮\n\n"
            "أرسل رابط المحتوى لاستخراج الصوت.\n\n"
            "🎵 صيغة الإخراج: MP3\n"
            "🎚️ جودة الصوت: 192 kbps\n\n"
            "⚡ NEXUS AUDIO ENGINE"
        )
        return

    if text == "⚙️ الإعدادات":
        await update.message.reply_text(
            "╭━━ ◈ SETTINGS ◈ ━━╮\n\n"
            "🎬 جودة الفيديو:\n"
            "1080p | 720p | 480p | 360p\n\n"
            "🎵 جودة الصوت: MP3 192 kbps\n\n"
            "يتم اختيار جودة الفيديو بعد إرسال الرابط.\n\n"
            "NEXUS CONFIGURATION"
        )
        return

    if text == "📊 معلومات البوت":
        await update.message.reply_text(
            "╭━━ ◈ SYSTEM STATUS ◈ ━━╮\n\n"
            f"🚀 الاسم: {BRAND}\n"
            f"💠 الإصدار: {EDITION}\n"
            "🟢 الحالة: يعمل\n"
            "🔒 الوصول: المالك فقط\n"
            "🎬 الخدمة: تنزيل الفيديو\n"
            "🎵 الخدمة: استخراج MP3\n\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "SYSTEM OPERATIONAL"
        )
        return

    if text == "❓ المساعدة":
        await update.message.reply_text(
            "╭━━ ◈ QUICK GUIDE ◈ ━━╮\n\n"
            "1️⃣ اختر تنزيل فيديو أو MP3.\n"
            "2️⃣ أرسل رابط المحتوى.\n"
            "3️⃣ اختر جودة الفيديو إذا طلب منك ذلك.\n"
            "4️⃣ انتظر اكتمال المعالجة.\n"
            "5️⃣ سيصلك الملف داخل المحادثة.\n\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "⚠️ يجب أن يكون الرابط من منصة مدعومة.\n"
            "⚡ NEXUS USER GUIDE"
        )
        return

    if not re.match(r"^https?://", text):
        await update.message.reply_text(
            "⚠️ الرابط غير صالح.\n\n"
            "أرسل رابطاً يبدأ بـ http:// أو https://"
        )
        return

    mode = context.user_data.get("mode")

    if not mode:
        await update.message.reply_text(
            "◈ يرجى اختيار الخدمة أولاً من القائمة."
        )
        return

    context.user_data["url"] = text

    if mode == "mp3":
        await download_and_send(update, context, "mp3", "best")
    else:
        await update.message.reply_text(
            "╭━━ ◈ QUALITY SELECTOR ◈ ━━╮\n\n"
            "اختر دقة الفيديو المناسبة:",
            reply_markup=quality_menu()
        )


# ==========================================
# BUTTON HANDLER
# ==========================================

async def button_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query

    if query.from_user.id != OWNER_ID:
        await query.answer("غير مصرح لك", show_alert=True)
        return

    await query.answer()

    if query.data == "cancel":
        context.user_data.pop("url", None)
        context.user_data.pop("mode", None)

        await query.edit_message_text(
            "╭━━ ◈ OPERATION CANCELLED ◈ ━━╮\n\n"
            "تم إلغاء العملية بنجاح.\n"
            "يمكنك اختيار خدمة أخرى من القائمة."
        )
        return

    if query.data.startswith("q_"):
        quality = query.data.replace("q_", "")

        quality_label = "أفضل جودة" if quality == "best" else quality + "p"

        await query.edit_message_text(
            "╭━━ ◈ NEXUS ENGINE ◈ ━━╮\n\n"
            f"🎯 الجودة المختارة: {quality_label}\n"
            "⏳ جارٍ تجهيز عملية التنزيل..."
        )

        await download_and_send(
            update, context, "video", quality,
            callback=True
        )


# ==========================================
# DOWNLOAD & SEND
# ==========================================

async def download_and_send(
    update, context, mode, quality, callback=False
):
    if callback:
        message = update.callback_query.message
    else:
        message = update.message

    url = context.user_data.get("url")

    if not url:
        await message.reply_text(
            "⚠️ لم أجد الرابط.\nأرسل الرابط من جديد."
        )
        return

    status = await message.reply_text(
        "╭━━ ◈ NEXUS PROCESSING ◈ ━━╮\n\n"
        "⏳ جارٍ تحميل ومعالجة المحتوى...\n"
        "يرجى الانتظار حتى اكتمال العملية.\n\n"
        "⚡ NEXUS DOWNLOAD ENGINE"
    )

    folder = None

    try:
        filepath, folder, info = await asyncio.to_thread(
            download_media, url, mode, quality
        )

        size = filepath.stat().st_size
        title = info.get("title", "Media")

        if size > MAX_TELEGRAM_SIZE:
            await status.edit_text(
                "╭━━ ◈ FILE SIZE NOTICE ◈ ━━╮\n\n"
                "⚠️ اكتمل التحميل، لكن حجم الملف\n"
                "يتجاوز حد الإرسال المباشر المعتمد هنا.\n\n"
                f"📁 الحجم: {size / 1024 / 1024:.1f} MB\n\n"
                "إرسال الملفات الكبيرة يحتاج ربط\n"
                "خدمة استضافة خارجية.\n\n"
                "NEXUS SYSTEM"
            )
            return

        await status.edit_text(
            "📤 اكتملت المعالجة بنجاح.\n"
            "جارٍ إرسال الملف إليك..."
        )

        with open(filepath, "rb") as media:
            if mode == "mp3":
                await message.reply_audio(
                    audio=media,
                    title=title[:64],
                    caption=(
                        "╭━━ ◈ NEXUS AUDIO ◈ ━━╮\n\n"
                        "🎵 تم استخراج الصوت بنجاح.\n"
                        "ᴍᴇᴅɪᴀ ᴅᴏᴡɴʟᴏᴀᴅᴇʀ ᴘʀᴏ"
                    )
                )
            else:
                await message.reply_video(
                    video=media,
                    caption=(
                        "╭━━ ◈ NEXUS VIDEO ◈ ━━╮\n\n"
                        f"🎬 {title[:150]}\n\n"
                        "✅ تم التنزيل بنجاح."
                    ),
                    supports_streaming=True
                )

        await status.delete()

    except Exception as error:
        await status.edit_text(
            "╭━━ ◈ DOWNLOAD FAILED ◈ ━━╮\n\n"
            "❌ تعذر إكمال عملية التنزيل.\n\n"
            f"التفاصيل: {str(error)[:400]}\n\n"
            "تحقق من الرابط وحاول مرة أخرى."
        )

    finally:
        if folder and folder.exists():
            shutil.rmtree(folder, ignore_errors=True)

        context.user_data.pop("url", None)
        context.user_data.pop("mode", None)


# ==========================================
# RUN APPLICATION
# ==========================================

def main():
    if not TOKEN:
        raise RuntimeError(
            "BOT_TOKEN is missing. Set it in environment variables."
        )

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    app.add_handler(
        CallbackQueryHandler(button_handler)
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_text
        )
    )

    print("NEXUS EDITION is running...")

    app.run_polling()


if __name__ == "__main__":
    main()
