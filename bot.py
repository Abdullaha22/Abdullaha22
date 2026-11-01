import os
import re
import uuid
import asyncio
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

# ========== SETTINGS ==========

TOKEN = os.getenv("BOT_TOKEN", "")
OWNER_ID = 5249057606

DOWNLOAD_DIR = Path("downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True)

MAX_TELEGRAM_SIZE = 49 * 1024 * 1024

# ========== MENUS ==========

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
            InlineKeyboardButton("📺 1080p", callback_data="q_1080"),
            InlineKeyboardButton("🎥 720p", callback_data="q_720")
        ],
        [
            InlineKeyboardButton("📱 480p", callback_data="q_480"),
            InlineKeyboardButton("⚡ 360p", callback_data="q_360")
        ],
        [
            InlineKeyboardButton("🌟 أفضل جودة", callback_data="q_best")
        ],
        [
            InlineKeyboardButton("❌ إلغاء", callback_data="cancel")
        ]
    ])

def is_owner(update):
    return (
        update.effective_user is not None
        and update.effective_user.id == OWNER_ID
    )

# ========== DOWNLOAD ENGINE ==========

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
        height = quality

        if height == "best":
            fmt = "bestvideo+bestaudio/best"
        else:
            fmt = (
                f"bestvideo[height<={height}]+bestaudio/"
                f"best[height<={height}]/best"
            )

        options = {
            "format": fmt,
            "outtmpl": output,
            "noplaylist": True,
            "merge_output_format": "mp4",
        }

    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=True)
        filepath = Path(ydl.prepare_filename(info))

    if mode == "mp3":
        filepath = filepath.with_suffix(".mp3")

    if not filepath.exists():
        files = list(folder.glob("*"))
        if not files:
            raise Exception("لم يتم العثور على الملف بعد التحميل")
        filepath = files[0]

    return filepath, folder, info

# ========== START ==========

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        return

    await update.message.reply_text(
        "👑 أهلاً بك في MEDIA DOWNLOADER PRO\n\n"
        "🚀 مركزك الشخصي لتنزيل الفيديوهات والصوتيات.\n\n"
        "اختر الخدمة من القائمة بالأسفل:",
        reply_markup=MAIN_MENU
    )

# ========== TEXT HANDLER ==========

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        return

    text = update.message.text.strip()

    if text == "🎬 تحميل فيديو":
        context.user_data["mode"] = "video"
        await update.message.reply_text(
            "🎬 أرسل رابط الفيديو الذي تريد تحميله."
        )
        return

    if text == "🎵 تحميل MP3":
        context.user_data["mode"] = "mp3"
        await update.message.reply_text(
            "🎵 أرسل رابط الفيديو لاستخراج الصوت MP3."
        )
        return

    if text == "⚙️ الإعدادات":
        await update.message.reply_text(
            "⚙️ إعدادات التنزيل\n\n"
            "اختر الجودة عند إرسال رابط الفيديو."
        )
        return

    if text == "📊 معلومات البوت":
        await update.message.reply_text(
            "👑 MEDIA DOWNLOADER PRO\n\n"
            "الحالة: يعمل\n"
            "الحساب: محمي\n"
            "المستخدمون المسموحون: 1"
        )
        return

    if text == "❓ المساعدة":
        await update.message.reply_text(
            "📌 طريقة الاستخدام:\n\n"
            "1️⃣ اختر تحميل فيديو أو MP3.\n"
            "2️⃣ أرسل رابط الميديا.\n"
            "3️⃣ اختر الجودة.\n"
            "4️⃣ انتظر اكتمال التحميل."
        )
        return

    if not re.match(r"^https?://", text):
        await update.message.reply_text(
            "⚠️ أرسل رابطاً صحيحاً يبدأ بـ http أو https."
        )
        return

    mode = context.user_data.get("mode")

    if not mode:
        await update.message.reply_text(
            "اختر أولاً تحميل فيديو أو تحميل MP3 من القائمة."
        )
        return

    context.user_data["url"] = text

    if mode == "mp3":
        await download_and_send(update, context, "mp3", "best")
    else:
        await update.message.reply_text(
            "🎯 اختر جودة الفيديو:",
            reply_markup=quality_menu()
        )

# ========== BUTTON HANDLER ==========

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
        await query.edit_message_text("❌ تم إلغاء العملية.")
        return

    if query.data.startswith("q_"):
        quality = query.data.replace("q_", "")
        await query.edit_message_text(
            f"⏳ جاري تجهيز الفيديو بجودة {quality}..."
        )
        await download_and_send(
            update, context, "video", quality,
            callback=True
        )

# ========== SEND MEDIA ==========

async def download_and_send(
    update, context, mode, quality, callback=False
):
    if callback:
        message = update.callback_query.message
    else:
        message = update.message

    url = context.user_data.get("url")

    if not url:
        await message.reply_text("⚠️ لم أجد الرابط. أرسل الرابط من جديد.")
        return

    status = await message.reply_text(
        "⏳ جاري التحميل...\n"
        "يرجى الانتظار حتى اكتمال العملية."
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
                "⚠️ اكتمل التحميل، لكن حجم الملف أكبر من حد "
                "الإرسال المباشر المعتمد هنا.\n\n"
                f"📁 الحجم: {size / 1024 / 1024:.1f} MB\n"
                "الملف محفوظ في مجلد downloads على اللابتوب.\n\n"
                "رابط التحميل الخارجي يحتاج ربط خدمة استضافة."
            )
            return

        await status.edit_text("📤 اكتمل التحميل، جاري الإرسال...")

        with open(filepath, "rb") as media:
            if mode == "mp3":
                await message.reply_audio(
                    audio=media,
                    title=title[:64],
                    caption="🎵 تم استخراج الصوت بنجاح"
                )
            else:
                await message.reply_video(
                    video=media,
                    caption=f"🎬 {title[:180]}",
                    supports_streaming=True
                )

        await status.delete()

    except Exception as error:
        await status.edit_text(
            "❌ تعذر إكمال التنزيل.\n\n"
            f"التفاصيل: {str(error)[:500]}"
        )

    finally:
        if folder and folder.exists():
            import shutil
            shutil.rmtree(folder, ignore_errors=True)

        context.user_data.pop("url", None)
        context.user_data.pop("mode", None)

# ========== RUN ==========

def main():
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

    print("MEDIA DOWNLOADER PRO is running...")
    app.run_polling()

if __name__ == "__main__":
    main()