import os
import re
import json
import uuid
import shutil
import asyncio
import logging
from pathlib import Path
from urllib.parse import urlparse

import yt_dlp

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# ==================================================
#  MEDIA DOWNLOADER PRO V3
# ==================================================

# ------------------ SETTINGS ----------------------

TOKEN = os.getenv("BOT_TOKEN", "")
OWNER_ID = 5249057606

DOWNLOAD_DIR = Path("downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True)

ACCESS_FILE = Path("access.json")

MAX_TELEGRAM_SIZE = 49 * 1024 * 1024

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# ------------------ ACCESS SYSTEM -----------------

def load_access():
    default = {
        "mode": "public",
        "allowed_users": []
    }

    if not ACCESS_FILE.exists():
        return default

    try:
        data = json.loads(ACCESS_FILE.read_text(encoding="utf-8"))

        if data.get("mode") not in ("public", "private"):
            data["mode"] = "public"

        if not isinstance(data.get("allowed_users"), list):
            data["allowed_users"] = []

        return data

    except Exception:
        logger.exception("Could not read access.json")
        return default


def save_access(data):
    ACCESS_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def is_owner(update):
    user = update.effective_user
    return bool(user and user.id == OWNER_ID)


def is_allowed(update):
    user = update.effective_user

    if not user:
        return False

    if user.id == OWNER_ID:
        return True

    access = load_access()

    if access["mode"] == "public":
        return True

    return user.id in access["allowed_users"]


async def access_denied(update):
    if update.callback_query:
        await update.callback_query.answer(
            "🔒 هذا البوت خاص حالياً.",
            show_alert=True
        )
    elif update.effective_message:
        await update.effective_message.reply_text(
            "🔒 عذراً، البوت خاص حالياً.\n"
            "ليس لديك صلاحية استخدامه."
        )


# ------------------ MAIN MENU ---------------------

MAIN_MENU = ReplyKeyboardMarkup(
    [
        ["🎬 تحميل فيديو", "🎵 تحميل MP3"],
        ["⚙️ الإعدادات", "📊 معلومات البوت"],
        ["❓ المساعدة"],
    ],
    resize_keyboard=True,
    is_persistent=True,
)


def quality_menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💎 1080p", callback_data="q_1080"),
            InlineKeyboardButton("🔥 720p", callback_data="q_720"),
        ],
        [
            InlineKeyboardButton("📱 480p", callback_data="q_480"),
            InlineKeyboardButton("⚡ 360p", callback_data="q_360"),
        ],
        [
            InlineKeyboardButton("🌟 أفضل جودة", callback_data="q_best"),
        ],
        [
            InlineKeyboardButton("❌ إلغاء", callback_data="cancel"),
        ],
    ])


def admin_menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🌍 الوضع العام", callback_data="admin_public"),
            InlineKeyboardButton("🔒 الوضع الخاص", callback_data="admin_private"),
        ],
    ])


# ------------------ DOWNLOAD ENGINE ---------------

def download_media(url, mode, quality):
    folder = DOWNLOAD_DIR / uuid.uuid4().hex
    folder.mkdir(parents=True, exist_ok=True)

    output = str(folder / "%(title).70s.%(ext)s")

    common_options = {
        "outtmpl": output,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "socket_timeout": 30,
        "retries": 5,
        "fragment_retries": 5,
        "windowsfilenames": True,
    }

    if mode == "mp3":
        options = {
            **common_options,
            "format": "bestaudio/best",
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
            **common_options,
            "format": fmt,
            "merge_output_format": "mp4",
        }

    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=True)
            filepath = Path(ydl.prepare_filename(info))

        if mode == "mp3":
            filepath = filepath.with_suffix(".mp3")

        if not filepath.exists():
            candidates = [
                f for f in folder.iterdir()
                if f.is_file()
            ]

            if not candidates:
                raise Exception("لم يتم العثور على الملف بعد التحميل.")

            filepath = max(candidates, key=lambda f: f.stat().st_size)

        return filepath, folder, info

    except Exception:
        shutil.rmtree(folder, ignore_errors=True)
        raise


# ------------------ START -------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        await access_denied(update)
        return

    user = update.effective_user
    first_name = user.first_name or "صديقي"

    welcome = (
        f"✨ أهلاً بك {first_name}!\n\n"
        "🚀 *MEDIA DOWNLOADER PRO*\n"
        "منصتك الذكية لتنزيل الفيديوهات والصوتيات.\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "🎬 تنزيل الفيديو بجودات متعددة\n"
        "🎵 استخراج الصوت بصيغة MP3\n"
        "⚡ واجهة سهلة وسريعة\n"
        "🛡️ تجربة استخدام منظمة\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "👇 اختر الخدمة التي تريدها من القائمة."
    )

    await update.message.reply_text(
        welcome,
        reply_markup=MAIN_MENU,
        parse_mode="Markdown"
    )


# ------------------ HELP --------------------------

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        await access_denied(update)
        return

    await update.message.reply_text(
        "📚 *دليل استخدام البوت*\n\n"
        "1️⃣ اختر تحميل فيديو أو MP3.\n"
        "2️⃣ أرسل رابط المحتوى.\n"
        "3️⃣ إذا اخترت الفيديو، حدد الجودة.\n"
        "4️⃣ انتظر اكتمال التحميل والإرسال.\n\n"
        "💡 استخدم الروابط المباشرة من المنصات المدعومة.\n"
        "⚠️ قد لا تعمل بعض الروابط بسبب قيود المنصة.",
        parse_mode="Markdown",
        reply_markup=MAIN_MENU
    )


# ------------------ USER ID -----------------------

async def my_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    await update.message.reply_text(
        f"🆔 رقم حسابك في تيليجرام:\n`{user.id}`",
        parse_mode="Markdown"
    )


# ------------------ ADMIN COMMANDS ----------------

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        await update.message.reply_text("⛔ هذا الأمر خاص بمالك البوت.")
        return

    access = load_access()

    mode_text = (
        "🌍 عام للجميع"
        if access["mode"] == "public"
        else "🔒 خاص بالمسموح لهم"
    )

    await update.message.reply_text(
        "👑 *لوحة تحكم المالك*\n\n"
        f"وضع البوت الحالي: {mode_text}\n"
        f"عدد المستخدمين المضافين: {len(access['allowed_users'])}\n\n"
        "اختر وضع التشغيل:",
        reply_markup=admin_menu(),
        parse_mode="Markdown"
    )


async def set_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        await update.message.reply_text("⛔ هذا الأمر للمالك فقط.")
        return

    if not context.args or context.args[0].lower() not in ("public", "private"):
        await update.message.reply_text(
            "الاستخدام:\n"
            "/mode public\n"
            "/mode private"
        )
        return

    access = load_access()
    access["mode"] = context.args[0].lower()
    save_access(access)

    if access["mode"] == "public":
        msg = "🌍 تم تفعيل الوضع العام. أصبح البوت متاحاً للجميع."
    else:
        msg = "🔒 تم تفعيل الوضع الخاص. الاستخدام للمسموح لهم فقط."

    await update.message.reply_text(msg)


async def allow_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        await update.message.reply_text("⛔ هذا الأمر للمالك فقط.")
        return

    try:
        user_id = int(context.args[0])
    except (IndexError, ValueError):
        await update.message.reply_text(
            "الاستخدام:\n/allow USER_ID\n\n"
            "مثال:\n/allow 123456789"
        )
        return

    access = load_access()

    if user_id not in access["allowed_users"]:
        access["allowed_users"].append(user_id)
        save_access(access)

    await update.message.reply_text(
        f"✅ تمت إضافة المستخدم بنجاح.\n🆔 `{user_id}`",
        parse_mode="Markdown"
    )


async def remove_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        await update.message.reply_text("⛔ هذا الأمر للمالك فقط.")
        return

    try:
        user_id = int(context.args[0])
    except (IndexError, ValueError):
        await update.message.reply_text(
            "الاستخدام:\n/remove USER_ID"
        )
        return

    if user_id == OWNER_ID:
        await update.message.reply_text("لا يمكنك حذف صلاحية المالك.")
        return

    access = load_access()
    access["allowed_users"] = [
        uid for uid in access["allowed_users"]
        if uid != user_id
    ]
    save_access(access)

    await update.message.reply_text(
        f"🗑️ تم حذف المستخدم من القائمة.\n🆔 `{user_id}`",
        parse_mode="Markdown"
    )


async def list_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        await update.message.reply_text("⛔ هذا الأمر للمالك فقط.")
        return

    access = load_access()
    users = access["allowed_users"]

    mode = "عام 🌍" if access["mode"] == "public" else "خاص 🔒"

    if users:
        user_list = "\n".join(f"• `{uid}`" for uid in users)
    else:
        user_list = "لا يوجد مستخدمون مضافون."

    await update.message.reply_text(
        f"👥 *قائمة المستخدمين المسموح لهم*\n\n"
        f"وضع البوت: {mode}\n\n"
        f"{user_list}",
        parse_mode="Markdown"
    )


# ------------------ BOT INFO ----------------------

async def bot_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    access = load_access()
    mode = "🌍 عام للجميع" if access["mode"] == "public" else "🔒 خاص"

    await update.message.reply_text(
        "📊 *معلومات البوت*\n\n"
        "🚀 MEDIA DOWNLOADER PRO\n"
        "🎬 تنزيل الفيديو: متاح\n"
        "🎵 استخراج MP3: متاح\n"
        f"🌐 نظام الوصول: {mode}\n"
        "⚙️ الحالة: يعمل عند اتصال الخادم\n\n"
        "شكراً لاستخدامك بوتنا ❤️",
        parse_mode="Markdown"
    )


# ------------------ TEXT HANDLER ------------------

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        await access_denied(update)
        return

    text = update.message.text.strip()

    if text == "🎬 تحميل فيديو":
        context.user_data["mode"] = "video"
        await update.message.reply_text(
            "🎬 *تحميل فيديو*\n\n"
            "أرسل رابط الفيديو الذي تريد تنزيله.\n"
            "بعدها ستختار الجودة المناسبة.",
            parse_mode="Markdown"
        )
        return

    if text == "🎵 تحميل MP3":
        context.user_data["mode"] = "mp3"
        await update.message.reply_text(
            "🎵 *استخراج الصوت MP3*\n\n"
            "أرسل رابط المحتوى الذي تريد استخراج الصوت منه.",
            parse_mode="Markdown"
        )
        return

    if text == "⚙️ الإعدادات":
        await update.message.reply_text(
            "⚙️ *الإعدادات*\n\n"
            "🎬 جودة الفيديو: تختارها بعد إرسال الرابط.\n"
            "🎵 جودة الصوت: MP3 بمعدل 192 kbps.\n\n"
            "👑 إعدادات الخصوصية والإدارة للمالك عبر /admin.",
            parse_mode="Markdown"
        )
        return

    if text == "📊 معلومات البوت":
        await bot_info(update, context)
        return

    if text == "❓ المساعدة":
        await help_command(update, context)
        return

    if not re.match(r"^https?://", text, re.IGNORECASE):
        await update.message.reply_text(
            "⚠️ أرسل رابطاً يبدأ بـ http:// أو https://"
        )
        return

    parsed = urlparse(text)

    if not parsed.netloc:
        await update.message.reply_text("⚠️ الرابط غير صحيح.")
        return

    mode = context.user_data.get("mode")

    if not mode:
        await update.message.reply_text(
            "👇 اختر أولاً تحميل فيديو أو تحميل MP3 من القائمة."
        )
        return

    context.user_data["url"] = text

    if mode == "mp3":
        await download_and_send(update, context, "mp3", "best")
    else:
        await update.message.reply_text(
            "🎯 *اختر جودة الفيديو المطلوبة:*",
            reply_markup=quality_menu(),
            parse_mode="Markdown"
        )


# ------------------ BUTTON HANDLER ----------------

async def button_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query

    if not is_allowed(update):
        await access_denied(update)
        return

    if query.data.startswith("admin_") and not is_owner(update):
        await query.answer("هذا الخيار للمالك فقط.", show_alert=True)
        return

    await query.answer()

    if query.data == "admin_public":
        access = load_access()
        access["mode"] = "public"
        save_access(access)
        await query.edit_message_text(
            "🌍 تم تفعيل الوضع العام.\nالبوت متاح للجميع الآن."
        )
        return

    if query.data == "admin_private":
        access = load_access()
        access["mode"] = "private"
        save_access(access)
        await query.edit_message_text(
            "🔒 تم تفعيل الوضع الخاص.\nفقط المستخدمون المسموح لهم يستطيعون الدخول."
        )
        return

    if query.data == "cancel":
        context.user_data.pop("url", None)
        context.user_data.pop("mode", None)
        await query.edit_message_text("❌ تم إلغاء العملية.")
        return

    if query.data.startswith("q_"):
        quality = query.data.replace("q_", "")

        if quality not in ("1080", "720", "480", "360", "best"):
            await query.edit_message_text("⚠️ جودة غير صالحة.")
            return

        await query.edit_message_text(
            f"⏳ جاري تجهيز الفيديو بجودة {quality}..."
        )

        await download_and_send(
            update,
            context,
            "video",
            quality,
            callback=True
        )


# ------------------ SEND MEDIA --------------------

async def download_and_send(
    update,
    context,
    mode,
    quality,
    callback=False
):
    if callback:
        message = update.callback_query.message
    else:
        message = update.message

    url = context.user_data.get("url")

    if not url:
        await message.reply_text("⚠️ لم أجد الرابط. أرسله من جديد.")
        return

    status = await message.reply_text(
        "⏳ *بدأ التحميل الآن...*\n\n"
        "قد تستغرق العملية بعض الوقت حسب حجم الملف وسرعة الخادم.",
        parse_mode="Markdown"
    )

    folder = None

    try:
        filepath, folder, info = await asyncio.to_thread(
            download_media,
            url,
            mode,
            quality
        )

        size = filepath.stat().st_size
        title = info.get("title", "Media")

        if size > MAX_TELEGRAM_SIZE:
            await status.edit_text(
                "⚠️ اكتمل التحميل، لكن الملف أكبر من حد الإرسال المباشر.\n\n"
                f"📁 الحجم: {size / 1024 / 1024:.1f} MB\n"
                "يحتاج هذا الملف إلى خدمة استضافة خارجية لإرساله كرابط."
            )
            return

        await status.edit_text(
            "✅ اكتمل التحميل!\n📤 جاري إرسال الملف إليك..."
        )

        with open(filepath, "rb") as media:
            if mode == "mp3":
                await message.reply_audio(
                    audio=media,
                    title=title[:64],
                    caption="🎵 تم استخراج الصوت بنجاح\n"
                            "🚀 MEDIA DOWNLOADER PRO"
                )
            else:
                await message.reply_video(
                    video=media,
                    caption=f"🎬 {title[:150]}\n"
                            "🚀 MEDIA DOWNLOADER PRO",
                    supports_streaming=True
                )

        await status.delete()

    except Exception as error:
        logger.exception("Download failed")

        try:
            await status.edit_text(
                "❌ تعذر إكمال عملية التنزيل.\n\n"
                "قد يكون الرابط غير مدعوم، أو أن المنصة تمنع الوصول، "
                "أو حدث خطأ مؤقت.\n\n"
                f"التفاصيل: {str(error)[:350]}"
            )
        except Exception:
            pass

    finally:
        if folder and folder.exists():
            shutil.rmtree(folder, ignore_errors=True)

        context.user_data.pop("url", None)
        context.user_data.pop("mode", None)


# ------------------ MAIN --------------------------

def main():
    if not TOKEN:
        raise RuntimeError(
            "BOT_TOKEN is missing. Set it in the environment variables."
        )

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("id", my_id))

    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CommandHandler("mode", set_mode))
    app.add_handler(CommandHandler("allow", allow_user))
    app.add_handler(CommandHandler("remove", remove_user))
    app.add_handler(CommandHandler("users", list_users))

    app.add_handler(CallbackQueryHandler(button_handler))

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_text
        )
    )

    print("MEDIA DOWNLOADER PRO V3 is running...")

    app.run_polling()


if __name__ == "__main__":
    main()