import logging
import re

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    InputMediaPhoto,
    InputMediaVideo,
)

from . import BRAND, VERSION
from .config import LOG, OWNER_ID, MAX_FILE, MAX_ITEMS, FFMPEG
from .store import allowed, owner, access, save_access, touch, log_job, stats
from .engine import inspect, download, cleanup, valid_url, host, is_image, is_video

MENU = ReplyKeyboardMarkup(
    [["📩 الدعم الفني"], ["📊 معلومات البوت", "⚙️ الإعدادات"], ["❓ المساعدة", "❌ إلغاء"]],
    resize_keyboard=True,
)


def ik(*rows):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(label, callback_data=data) for label, data in row]
        for row in rows
    ])


def playlist_kb(count, selected):
    rows = [
        [(('☑️ ' if index in selected else '⬜ ') + f'العنصر {index}', f'pick:{index}')]
        for index in range(1, count + 1)
    ]
    rows += [[('📥 تنزيل الكل', 'all')], [('✅ تنزيل المحدد', 'selected')], [('❌ إلغاء', 'cancel')]]
    return ik(*rows)


async def deny(update):
    if update.callback_query:
        await update.callback_query.answer("البوت خاص حالياً", show_alert=True)
    elif update.effective_message:
        await update.effective_message.reply_text("🔒 البوت خاص حالياً")


async def start(update, context):
    if not allowed(update.effective_user):
        return await deny(update)
    touch(update.effective_user)
    name = update.effective_user.first_name or "صديقي"
    await update.effective_message.reply_text(
        f"◈ N E X U S ◈\nأهلاً بك {name} ✨\n"
        f"MEDIA DOWNLOADER PRO — V{VERSION}\n\n"
        "أرسل الرابط مباشرة حتى أفحصه وأعرض الخيارات.\n"
        "🎬 فيديو مدعوم\n🖼️ صور وألبومات عامة مدعومة\n"
        "🎵 استخراج MP3\n📩 دعم فني مباشر\n\n" + BRAND,
        reply_markup=MENU,
    )


async def help_cmd(update, context):
    if not allowed(update.effective_user):
        return await deny(update)
    await update.effective_message.reply_text(
        "أرسل رابطاً عاماً. الروابط الخاصة أو المحمية أو التي تتطلب تسجيل دخول قد لا تعمل. "
        "استخدم فقط محتوى تملك حق تنزيله."
    )


async def myid(update, context):
    await update.effective_message.reply_text(f"ID: {update.effective_user.id}")


async def info(update, context):
    if not allowed(update.effective_user):
        return await deny(update)
    users, jobs = stats()
    await update.effective_message.reply_text(
        f"NEXUS V{VERSION}\nFFmpeg: {'جاهز' if FFMPEG else 'غير متوفر'}\n"
        f"المستخدمون: {users}\nالطلبات: {jobs}\n{BRAND}"
    )


async def admin(update, context):
    if not owner(update.effective_user):
        return await update.effective_message.reply_text("للمالك فقط")
    data = access()
    users, jobs = stats()
    await update.effective_message.reply_text(
        f"لوحة الإدارة V5\nالوضع: {data['mode']}\nالمستخدمون: {users}\nالطلبات: {jobs}\n"
        "/mode public|private\n/allow ID\n/remove ID\n/users",
        reply_markup=ik([("🌍 عام", "admin:public"), ("🔒 خاص", "admin:private")]),
    )


async def mode_cmd(update, context):
    if not owner(update.effective_user):
        return await update.effective_message.reply_text("للمالك فقط")
    if not context.args or context.args[0] not in ("public", "private"):
        return await update.effective_message.reply_text("/mode public أو /mode private")
    data = access()
    data["mode"] = context.args[0]
    save_access(data)
    await update.effective_message.reply_text("تم تحديث الوضع")


async def allow_cmd(update, context):
    if not owner(update.effective_user):
        return await update.effective_message.reply_text("للمالك فقط")
    try:
        user_id = int(context.args[0])
    except (IndexError, ValueError):
        return await update.effective_message.reply_text("/allow USER_ID")
    data = access()
    data["allowed_users"] = sorted(set(data["allowed_users"] + [user_id]))
    save_access(data)
    await update.effective_message.reply_text("تمت الإضافة")


async def remove_cmd(update, context):
    if not owner(update.effective_user):
        return await update.effective_message.reply_text("للمالك فقط")
    try:
        user_id = int(context.args[0])
    except (IndexError, ValueError):
        return await update.effective_message.reply_text("/remove USER_ID")
    if user_id == OWNER_ID:
        return await update.effective_message.reply_text("لا يمكن حذف المالك")
    data = access()
    data["allowed_users"] = [item for item in data["allowed_users"] if item != user_id]
    save_access(data)
    await update.effective_message.reply_text("تمت الإزالة")


async def users_cmd(update, context):
    if not owner(update.effective_user):
        return await update.effective_message.reply_text("للمالك فقط")
    data = access()
    await update.effective_message.reply_text(
        data["mode"] + "\n" + ("\n".join(map(str, data["allowed_users"])) or "لا يوجد")
    )


async def support_send(update, context):
    message = update.effective_message
    user = update.effective_user
    try:
        anchor = await context.bot.send_message(
            OWNER_ID,
            f"📩 طلب دعم\nالاسم: {user.full_name}\n@{user.username or 'غير متوفر'}\nID: {user.id}",
        )
        await context.bot.copy_message(
            OWNER_ID, message.chat_id, message.message_id,
            reply_to_message_id=anchor.message_id,
        )
        await message.reply_text("وصلت رسالتك للدعم الفني.")
    except Exception:
        LOG.exception("support forwarding failed")
        await message.reply_text("تعذر إرسال الرسالة حالياً")
    finally:
        context.user_data.pop("support", None)


async def owner_reply(update, context):
    message = update.effective_message
    if not owner(update.effective_user) or not message.reply_to_message:
        return False
    match = re.search(r"ID:\s*(\d+)", message.reply_to_message.text or "")
    if not match:
        return False
    try:
        await context.bot.copy_message(int(match.group(1)), message.chat_id, message.message_id)
        await message.reply_text("تم إرسال الرد")
    except Exception:
        LOG.exception("support reply failed")
        await message.reply_text("تعذر إرسال الرد")
    return True


async def send_files(message, files, mode, status):
    if mode == "audio":
        good = [path for path in files if path.stat().st_size <= MAX_FILE]
        if len(good) < len(files):
            await message.reply_text("بعض الملفات أكبر من حد الإرسال المحدد ولم تُرسل")
        if not good:
            return await status.edit_text("لا توجد ملفات ضمن حد الإرسال")
        for path in good:
            with path.open("rb") as stream:
                await message.reply_audio(stream, title=path.stem[:64], caption=BRAND)
    else:
        sendable = []
        for path in files:
            if path.stat().st_size > MAX_FILE:
                await message.reply_text(f"تم تجاوز حد الإرسال لهذا الملف: {path.name[:80]}")
            else:
                sendable.append(path)
        visual = [path for path in sendable if is_image(path) or is_video(path)]
        documents = [path for path in sendable if not is_image(path) and not is_video(path)]
        for index in range(0, len(visual), 10):
            group = visual[index:index + 10]
            if len(group) == 1:
                path = group[0]
                with path.open("rb") as stream:
                    if is_image(path):
                        await message.reply_photo(stream, caption=BRAND)
                    else:
                        await message.reply_video(stream, supports_streaming=True, caption=BRAND)
            else:
                streams, media = [], []
                try:
                    for path in group:
                        stream = path.open("rb")
                        streams.append(stream)
                        media.append(InputMediaPhoto(stream) if is_image(path) else InputMediaVideo(stream, supports_streaming=True))
                    await message.reply_media_group(media)
                finally:
                    for stream in streams:
                        stream.close()
        for path in documents:
            with path.open("rb") as stream:
                await message.reply_document(stream, caption=BRAND, filename=path.name)
    try:
        await status.edit_text("✅ اكتمل الإرسال\n" + BRAND)
    except Exception:
        pass


async def run_job(query, context, mode, quality="best", selected=None):
    pending = context.user_data.get("pending", {})
    url = pending.get("url")
    if not url:
        return await query.message.reply_text("انتهى الطلب، أرسل الرابط مجدداً")
    status = await query.message.reply_text("⏳ جارٍ التنزيل...")
    folder = None
    title = pending.get("title", "Media")
    try:
        folder, files, info_data = await download(url, mode, quality, selected)
        title = (info_data or {}).get("title") or title
        await send_files(query.message, files, mode, status)
        log_job(query.from_user.id, host(url), title, mode, "success")
    except Exception as exc:
        LOG.exception("download failed")
        log_job(query.from_user.id, host(url), title, mode, "failed")
        try:
            await status.edit_text(
                "❌ تعذر التنزيل. قد يكون المصدر غير مدعوم أو خاصاً أو محمياً.\n" + str(exc)[:160]
            )
        except Exception:
            pass
    finally:
        if folder:
            cleanup(folder)
        context.user_data.pop("pending", None)


async def text_handler(update, context):
    if not allowed(update.effective_user):
        return await deny(update)
    message = update.effective_message
    text = (message.text or "").strip()
    if owner(update.effective_user) and await owner_reply(update, context):
        return
    if text == "❌ إلغاء":
        context.user_data.clear()
        return await message.reply_text("تم الإلغاء", reply_markup=MENU)
    if text == "📩 الدعم الفني":
        context.user_data["support"] = True
        return await message.reply_text("اكتب رسالتك أو أرسل ملفاً للدعم. للإلغاء اضغط ❌ إلغاء")
    if context.user_data.get("support"):
        return await support_send(update, context)
    if text == "❓ المساعدة":
        return await help_cmd(update, context)
    if text == "📊 معلومات البوت":
        return await info(update, context)
    if text == "⚙️ الإعدادات":
        return await message.reply_text("اختر الفيديو أو MP3 بعد إرسال الرابط")
    if not valid_url(text):
        return await message.reply_text("أرسل الرابط مباشرة بصيغة https:// أو http://")
    status = await message.reply_text("🔎 أفحص الرابط...")
    try:
        details = await inspect(text)
        entries = [item for item in (details or {}).get("entries", []) if item]
        if entries:
            count = min(len(entries), MAX_ITEMS)
            context.user_data["pending"] = {
                "url": text, "title": (details or {}).get("title", "Media"),
                "count": count, "selected": [],
            }
            await status.edit_text(
                f"وجدت {len(entries)} عناصر. اختر من أول {count} أو نزّل الكل.",
                reply_markup=playlist_kb(count, set()),
            )
        else:
            context.user_data["pending"] = {
                "url": text, "title": (details or {}).get("title", "Media")
            }
            await status.edit_text(
                f"تم التعرف على المحتوى:\n{context.user_data['pending']['title']}\nاختر:",
                reply_markup=ik(
                    [("🎬 فيديو", "mode:video"), ("🎵 MP3", "mode:audio")],
                    [("❌ إلغاء", "cancel")],
                ),
            )
    except Exception as exc:
        LOG.exception("inspect failed")
        await status.edit_text("تعذر قراءة الرابط. تأكد أنه عام ومدعوم.\n" + str(exc)[:150])


async def media_handler(update, context):
    if not allowed(update.effective_user):
        return await deny(update)
    if context.user_data.get("support"):
        return await support_send(update, context)
    await update.effective_message.reply_text(
        "استلام الملفات المباشرة غير مفعّل بعد؛ يمكنك إرسالها عبر الدعم الفني أو إرسال رابط عام."
    )


async def callbacks(update, context):
    query = update.callback_query
    if not allowed(update.effective_user):
        return await deny(update)
    data = query.data or ""
    if data.startswith("admin:"):
        if not owner(update.effective_user):
            return await query.answer("للمالك فقط", show_alert=True)
        await query.answer()
        data_access = access()
        data_access["mode"] = data.split(":", 1)[1]
        save_access(data_access)
        return await query.edit_message_text("تم تغيير الوضع إلى " + data_access["mode"])
    if data == "cancel":
        await query.answer()
        context.user_data.pop("pending", None)
        return await query.edit_message_text("تم الإلغاء")
    if data == "mode:audio":
        await query.answer()
        return await run_job(query, context, "audio")
    if data == "mode:video":
        await query.answer()
        return await query.edit_message_text(
            "اختر الجودة:",
            reply_markup=ik(
                [("1080p", "quality:1080"), ("720p", "quality:720")],
                [("480p", "quality:480"), ("360p", "quality:360")],
                [("أفضل جودة", "quality:best")], [("إلغاء", "cancel")],
            ),
        )
    if data.startswith("quality:"):
        await query.answer()
        return await run_job(query, context, "video", data.split(":", 1)[1])
    if data.startswith("pick:"):
        pending = context.user_data.get("pending")
        if not pending:
            return await query.answer("انتهى الطلب", show_alert=True)
        try:
            index = int(data.split(":", 1)[1])
        except ValueError:
            return await query.answer("اختيار غير صالح", show_alert=True)
        if not 1 <= index <= pending.get("count", 0):
            return await query.answer("اختيار غير صالح", show_alert=True)
        selected = set(pending.get("selected", []))
        selected.symmetric_difference_update({index})
        pending["selected"] = sorted(selected)
        await query.answer()
        return await query.edit_message_reply_markup(
            reply_markup=playlist_kb(pending["count"], selected)
        )
    if data == "selected":
        selected = context.user_data.get("pending", {}).get("selected", [])
        if not selected:
            return await query.answer("حدد عنصراً أولاً", show_alert=True)
        await query.answer()
        return await run_job(query, context, "video", "best", selected)
    if data == "all":
        await query.answer()
        return await run_job(query, context, "video")
    await query.answer("خيار غير معروف", show_alert=True)


async def error_handler(update, context):
    LOG.exception("Unhandled bot error", exc_info=context.error)
