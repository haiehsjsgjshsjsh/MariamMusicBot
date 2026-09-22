import os
import re
import json
import asyncio
import inspect
from pathlib import Path
from collections import defaultdict, deque

import static_ffmpeg
static_ffmpeg.add_paths()

import yt_dlp

from pyrogram import Client, filters
from pyrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ChatPermissions,
    ChatPrivileges,
)

from pytgcalls import PyTgCalls
from pytgcalls.types import MediaStream, GroupCallConfig


# =========================================================
# إعدادات الحسابات
# =========================================================

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]
SESSION_STRING = os.environ["SESSION_STRING"]

# اسم الصورة التي رفعتها في GitHub
PHOTO_PATH = "IMG_20260922_130735_050.jpg"


# =========================================================
# تشغيل البوت والمساعد
# =========================================================

bot = Client(
    "MariamMusicBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

assistant = Client(
    "MariamMusicAssistant",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)

calls = PyTgCalls(assistant)


# =========================================================
# ملفات البيانات
# =========================================================

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

REPLIES_FILE = DATA_DIR / "custom_replies.json"
SETTINGS_FILE = DATA_DIR / "group_settings.json"
WARNINGS_FILE = DATA_DIR / "warnings.json"


def load_json(path, default):
    try:
        if not path.exists():
            return default

        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    except Exception:
        return default


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )


replies_data = load_json(REPLIES_FILE, {})
settings_data = load_json(SETTINGS_FILE, {})
warnings_data = load_json(WARNINGS_FILE, {})


# =========================================================
# الميوزك
# =========================================================

queues = defaultdict(deque)
current_song = {}
waiting_for_song = set()


# =========================================================
# أدوات عامة
# =========================================================

async def maybe_await(value):
    if inspect.isawaitable(value):
        return await value
    return value


async def is_admin(message):
    try:
        member = await bot.get_chat_member(
            message.chat.id,
            message.from_user.id
        )

        return member.status in (
            "administrator",
            "owner"
        )

    except Exception:
        return False


async def is_owner(message):
    try:
        member = await bot.get_chat_member(
            message.chat.id,
            message.from_user.id
        )

        return member.status == "owner"

    except Exception:
        return False


async def need_admin(message):
    if await is_admin(message):
        return True

    await message.reply_text(
        "❌ الأمر ده للمشرفين بس."
    )

    return False


async def need_owner(message):
    if await is_owner(message):
        return True

    await message.reply_text(
        "❌ الأمر ده لمالك المجموعة بس."
    )

    return False


def get_settings(chat_id):
    key = str(chat_id)

    if key not in settings_data:
        settings_data[key] = {
            "enabled": True,
            "links": False,
            "images": False,
            "videos": False,
            "stickers": False,
            "voice": False,
            "bad_words": False,
        }
        save_json(SETTINGS_FILE, settings_data)

    return settings_data[key]


def group_enabled(chat_id):
    return get_settings(chat_id).get("enabled", True)


# =========================================================
# الردود التلقائية
# =========================================================

@bot.on_message(
    filters.group &
    filters.text &
    filters.regex(r"^اضف رد\s+(.+?)\s*=\s*(.+)$")
)
async def add_reply(_, message):

    if not await need_admin(message):
        return

    match = re.match(
        r"^اضف رد\s+(.+?)\s*=\s*(.+)$",
        message.text,
        re.S
    )

    if not match:
        return

    word = match.group(1).strip().lower()
    reply = match.group(2).strip()

    if not word or not reply:
        await message.reply_text(
            "❌ الاستخدام:\n\n"
            "اضف رد الكلمة = الرد"
        )
        return

    chat_id = str(message.chat.id)

    if chat_id not in replies_data:
        replies_data[chat_id] = {}

    if len(replies_data[chat_id]) >= 500 and word not in replies_data[chat_id]:
        await message.reply_text(
            "❌ وصلت للحد الأقصى وهو 500 رد."
        )
        return

    replies_data[chat_id][word] = reply

    save_json(
        REPLIES_FILE,
        replies_data
    )

    await message.reply_text(
        f"✅ تم إضافة الرد.\n\n"
        f"🔤 الكلمة: {word}\n"
        f"💬 الرد: {reply}"
    )


@bot.on_message(
    filters.group &
    filters.text &
    filters.regex(r"^مسح رد\s+(.+)$")
)
async def delete_reply(_, message):

    if not await need_admin(message):
        return

    match = re.match(
        r"^مسح رد\s+(.+)$",
        message.text,
        re.S
    )

    if not match:
        return

    word = match.group(1).strip().lower()
    chat_id = str(message.chat.id)

    if chat_id not in replies_data:
        await message.reply_text(
            "❌ الرد مش موجود."
        )
        return

    if word not in replies_data[chat_id]:
        await message.reply_text(
            "❌ الرد مش موجود."
        )
        return

    del replies_data[chat_id][word]

    save_json(
        REPLIES_FILE,
        replies_data
    )

    await message.reply_text(
        f"✅ تم مسح الرد الخاص بـ: {word}"
    )


# =========================================================
# تفعيل وتعطيل البوت
# =========================================================

@bot.on_message(
    filters.group &
    filters.text &
    filters.regex(r"^تفعيل البوت$")
)
async def activate_bot(_, message):

    if not await need_admin(message):
        return

    settings = get_settings(message.chat.id)

    settings["enabled"] = True

    save_json(
        SETTINGS_FILE,
        settings_data
    )

    await message.reply_text(
        "🟢 تم تفعيل البوت.\n\n"
        "🎵 الميوزك تعمل\n"
        "💬 الردود تعمل\n"
        "🛡️ الإدارة تعمل\n"
        "🔒 الحماية تعمل"
    )


@bot.on_message(
    filters.group &
    filters.text &
    filters.regex(r"^تعطيل البوت$")
)
async def deactivate_bot(_, message):

    if not await need_admin(message):
        return

    settings = get_settings(message.chat.id)

    settings["enabled"] = False

    save_json(
        SETTINGS_FILE,
        settings_data
    )

    await message.reply_text(
        "🔴 تم تعطيل البوت في المجموعة."
    )


# =========================================================
# الرتب
# =========================================================

@bot.on_message(
    filters.group &
    filters.text &
    filters.regex(r"^رتبتي$")
)
async def my_rank(_, message):

    try:
        member = await bot.get_chat_member(
            message.chat.id,
            message.from_user.id
        )

        if member.status == "owner":
            rank = "👑 المالك"

        elif member.status == "administrator":
            rank = "🛡️ مشرف"

        else:
            rank = "👤 عضو"

        await message.reply_text(
            f"🎖️ رتبتك: {rank}"
        )

    except Exception:
        await message.reply_text(
            "❌ حصل خطأ."
        )


@bot.on_message(
    filters.group &
    filters.text &
    filters.regex(r"^المشرفين$")
)
async def admins_list(_, message):

    try:
        admins = []

        async for member in bot.get_chat_members(
            message.chat.id,
            filter="administrators"
        ):
            user = member.user

            if user.username:
                name = f"@{user.username}"
            else:
                name = user.first_name or "بدون اسم"

            admins.append(
                f"• {name}"
            )

        if not admins:
            await message.reply_text(
                "❌ مفيش مشرفين."
            )
            return

        await message.reply_text(
            "🛡️ مشرفين المجموعة:\n\n" +
            "\n".join(admins)
        )

    except Exception:
        await message.reply_text(
            "❌ حصل خطأ أثناء جلب المشرفين."
        )


@bot.on_message(
    filters.group &
    filters.text &
    filters.regex(r"^المالك$")
)
async def group_owner(_, message):

    try:
        async for member in bot.get_chat_members(
            message.chat.id,
            filter="administrators"
        ):

            if member.status == "owner":

                user = member.user

                if user.username:
                    name = f"@{user.username}"
                else:
                    name = user.first_name or "بدون اسم"

                await message.reply_text(
                    f"👑 مالك المجموعة:\n{name}"
                )

                return

        await message.reply_text(
            "❌ لم أستطع معرفة المالك."
        )

    except Exception:
        await message.reply_text(
            "❌ حصل خطأ."
        )


# =========================================================
# ترقية
# =========================================================

@bot.on_message(
    filters.group &
    filters.text &
    filters.regex(r"^ترقية$")
)
async def promote_user(_, message):

    if not await need_admin(message):
        return

    if not message.reply_to_message:
        await message.reply_text(
            "❌ اعمل رد على رسالة الشخص واكتب:\n"
            "ترقية"
        )
        return

    user = message.reply_to_message.from_user

    try:
        privileges = ChatPrivileges(
            can_manage_chat=True,
            can_delete_messages=True,
            can_manage_video_chats=True,
            can_restrict_members=True,
            can_promote_members=False,
            can_change_info=True,
            can_invite_users=True,
            can_pin_messages=True
        )

        await bot.promote_chat_member(
            message.chat.id,
            user.id,
            privileges=privileges
        )

        await message.reply_text(
            f"🛡️ تم ترقية {user.mention}."
        )

    except Exception as e:
        await message.reply_text(
            f"❌ لم أستطع ترقية العضو.\n{e}"
        )


# =========================================================
# تنزيل مشرف
# =========================================================

@bot.on_message(
    filters.group &
    filters.text &
    filters.regex(r"^تنزيل$")
)
async def demote_user(_, message):

    if not await need_owner(message):
        return

    if not message.reply_to_message:
        await message.reply_text(
            "❌ اعمل رد على رسالة المشرف واكتب:\n"
            "تنزيل"
        )
        return

    user = message.reply_to_message.from_user

    try:

        await bot.promote_chat_member(
            message.chat.id,
            user.id,
            privileges=ChatPrivileges()
        )

        await message.reply_text(
            f"✅ تم تنزيل {user.mention} من الإشراف."
        )

    except Exception as e:
        await message.reply_text(
            f"❌ حصل خطأ.\n{e}"
        )


# =========================================================
# طرد
# =========================================================

@bot.on_message(
    filters.group &
    filters.text &
    filters.regex(r"^طرد$")
)
async def kick_user(_, message):

    if not await need_admin(message):
        return

    if not message.reply_to_message:
        await message.reply_text(
            "❌ اعمل رد على رسالة الشخص واكتب: طرد"
        )
        return

    user = message.reply_to_message.from_user

    try:
        await bot.ban_chat_member(
            message.chat.id,
            user.id
        )

        await bot.unban_chat_member(
            message.chat.id,
            user.id
        )

        await message.reply_text(
            f"🚪 تم طرد {user.mention}."
        )

    except Exception:
        await message.reply_text(
            "❌ لم أستطع طرد العضو."
        )


# =========================================================
# حظر
# =========================================================

@bot.on_message(
    filters.group &
    filters.text &
    filters.regex(r"^حظر$")
)
async def ban_user(_, message):

    if not await need_admin(message):
        return

    if not message.reply_to_message:
        await message.reply_text(
            "❌ اعمل رد على رسالة الشخص واكتب: حظر"
        )
        return

    user = message.reply_to_message.from_user

    try:
        await bot.ban_chat_member(
            message.chat.id,
            user.id
        )

        await message.reply_text(
            f"🚫 تم حظر {user.mention}."
        )

    except Exception:
        await message.reply_text(
            "❌ لم أستطع حظر العضو."
        )


# =========================================================
# فك الحظر
# =========================================================

@bot.on_message(
    filters.group &
    filters.text &
    filters.regex(r"^فك حظر$")
)
async def unban_user(_, message):

    if not await need_admin(message):
        return

    if not message.reply_to_message:
        await message.reply_text(
            "❌ اعمل رد على رسالة الشخص واكتب: فك حظر"
        )
        return

    user = message.reply_to_message.from_user

    try:
        await bot.unban_chat_member(
            message.chat.id,
            user.id
        )

        await message.reply_text(
            f"✅ تم فك الحظر عن {user.mention}."
        )

    except Exception:
        await message.reply_text(
            "❌ حصل خطأ."
        )


# =========================================================
# كتم
# =========================================================

@bot.on_message(
    filters.group &
    filters.text &
    filters.regex(r"^كتم$")
)
async def mute_user(_, message):

    if not await need_admin(message):
        return

    if not message.reply_to_message:
        await message.reply_text(
            "❌ اعمل رد على رسالة الشخص واكتب: كتم"
        )
        return

    user = message.reply_to_message.from_user

    try:

        await bot.restrict_chat_member(
            message.chat.id,
            user.id,
            permissions=ChatPermissions()
        )

        await message.reply_text(
            f"🔇 تم كتم {user.mention}."
        )

    except Exception:
        await message.reply_text(
            "❌ لم أستطع كتم العضو."
        )


# =========================================================
# فك الكتم
# =========================================================

@bot.on_message(
    filters.group &
    filters.text &
    filters.regex(r"^فك كتم$")
)
async def unmute_user(_, message):

    if not await need_admin(message):
        return

    if not message.reply_to_message:
        await message.reply_text(
            "❌ اعمل رد على رسالة الشخص واكتب: فك كتم"
        )
        return

    user = message.reply_to_message.from_user

    try:

        await bot.restrict_chat_member(
            message.chat.id,
            user.id,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True
            )
        )

        await message.reply_text(
            f"🔊 تم فك الكتم عن {user.mention}."
        )

    except Exception:
        await message.reply_text(
            "❌ حصل خطأ."
        )


# =========================================================
# التحذيرات
# =========================================================

@bot.on_message(
    filters.group &
    filters.text &
    filters.regex(r"^تحذير$")
)
async def warn_user(_, message):

    if not await need_admin(message):
        return

    if not message.reply_to_message:
        await message.reply_text(
            "❌ اعمل رد على رسالة الشخص واكتب: تحذير"
        )
        return

    user = message.reply_to_message.from_user

    chat_id = str(message.chat.id)
    user_id = str(user.id)

    if chat_id not in warnings_data:
        warnings_data[chat_id] = {}

    warnings_data[chat_id][user_id] = (
        warnings_data[chat_id].get(user_id, 0) + 1
    )

    count = warnings_data[chat_id][user_id]

    save_json(
        WARNINGS_FILE,
        warnings_data
    )

    await message.reply_text(
        f"⚠️ تم تحذير {user.mention}.\n"
        f"عدد التحذيرات: {count}"
    )


@bot.on_message(
    filters.group &
    filters.text &
    filters.regex(r"^تحذيرات$")
)
async def warnings_list(_, message):

    if not message.reply_to_message:
        await message.reply_text(
            "❌ اعمل رد على رسالة الشخص واكتب: تحذيرات"
        )
        return

    user = message.reply_to_message.from_user

    chat_id = str(message.chat.id)
    user_id = str(user.id)

    count = warnings_data.get(
        chat_id,
        {}
    ).get(
        user_id,
        0
    )

    await message.reply_text(
        f"⚠️ تحذيرات {user.mention}: {count}"
    )


@bot.on_message(
    filters.group &
    filters.text &
    filters.regex(r"^مسح تحذيرات$")
)
async def clear_warnings(_, message):

    if not await need_admin(message):
        return

    if not message.reply_to_message:
        await message.reply_text(
            "❌ اعمل رد على رسالة الشخص واكتب: مسح تحذيرات"
        )
        return

    user = message.reply_to_message.from_user

    chat_id = str(message.chat.id)
    user_id = str(user.id)

    if chat_id in warnings_data:
        warnings_data[chat_id].pop(
            user_id,
            None
        )

    save_json(
        WARNINGS_FILE,
        warnings_data
    )

    await message.reply_text(
        f"✅ تم مسح تحذيرات {user.mention}."
    )


# =========================================================
# التثبيت
# =========================================================

@bot.on_message(
    filters.group &
    filters.text &
    filters.regex(r"^تثبيت$")
)
async def pin_message(_, message):

    if not await need_admin(message):
        return

    if not message.reply_to_message:
        await message.reply_text(
            "❌ اعمل رد على الرسالة واكتب: تثبيت"
        )
        return

    try:
        await bot.pin_chat_message(
            message.chat.id,
            message.reply_to_message.id
        )

        await message.reply_text(
            "📌 تم تثبيت الرسالة."
        )

    except Exception:
        await message.reply_text(
            "❌ لم أستطع تثبيت الرسالة."
        )


@bot.on_message(
    filters.group &
    filters.text &
    filters.regex(r"^إلغاء تثبيت$")
)
async def unpin_message(_, message):

    if not await need_admin(message):
        return

    try:
        await bot.unpin_chat_message(
            message.chat.id
        )

        await message.reply_text(
            "📌 تم إلغاء التثبيت."
        )

    except Exception:
        await message.reply_text(
            "❌ حصل خطأ."
        )


# =========================================================
# إعدادات الحماية
# =========================================================

@bot.on_message(
    filters.group &
    filters.text &
    filters.regex(
        r"^(قفل|فتح)\s+(الروابط|الصور|الفيديو|الملصقات|الصوت|السب)$"
    )
)
async def protection_settings(_, message):

    if not await need_admin(message):
        return

    match = re.match(
        r"^(قفل|فتح)\s+(الروابط|الصور|الفيديو|الملصقات|الصوت|السب)$",
        message.text
    )

    if not match:
        return

    action = match.group(1)
    item = match.group(2)

    mapping = {
        "الروابط": "links",
        "الصور": "images",
        "الفيديو": "videos",
        "الملصقات": "stickers",
        "الصوت": "voice",
        "السب": "bad_words",
    }

    key = mapping[item]

    settings = get_settings(
        message.chat.id
    )

    settings[key] = action == "قفل"

    save_json(
        SETTINGS_FILE,
        settings_data
    )

    if action == "قفل":
        await message.reply_text(
            f"🔒 تم قفل {item}."
        )
    else:
        await message.reply_text(
            f"🔓 تم فتح {item}."
        )


# =========================================================
# كلمات ممنوعة
# =========================================================

BAD_WORDS = {
    "كلمة_ممنوعة_1",
    "كلمة_ممنوعة_2",
}


@bot.on_message(filters.group)
async def protection_handler(_, message):

    if not group_enabled(message.chat.id):
        return

    if not message.from_user:
        return

    if await is_admin(message):
        return

    settings = get_settings(
        message.chat.id
    )

    # الروابط
    if settings.get("links") and message.text:

        if re.search(
            r"(https?://|www\.|t\.me/|telegram\.me/)",
            message.text,
            re.I
        ):
            try:
                await message.delete()
            except Exception:
                pass

            return

    # الصور
    if settings.get("images") and message.photo:

        try:
            await message.delete()
        except Exception:
            pass

        return

    # الفيديو
    if settings.get("videos") and message.video:

        try:
            await message.delete()
        except Exception:
            pass

        return

    # الملصقات
    if settings.get("stickers") and message.sticker:

        try:
            await message.delete()
        except Exception:
            pass

        return

    # الصوت
    if settings.get("voice") and (
        message.voice or message.audio
    ):

        try:
            await message.delete()
        except Exception:
            pass

        return

    # السب
    if settings.get("bad_words") and message.text:

        text = message.text.lower()

        for word in BAD_WORDS:
            if word.lower() in text:

                try:
                    await message.delete()
                except Exception:
                    pass

                return


# =========================================================
# تشغيل الميوزك
# =========================================================

def format_duration(seconds):

    if not seconds:
        return "غير معروف"

    try:
        seconds = int(seconds)
    except Exception:
        return "غير معروف"

    minutes = seconds // 60
    secs = seconds % 60

    return f"{minutes:02d}:{secs:02d}"


async def search_song(query):

    # يوتيوب
    try:

        options = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "extract_flat": True,
            "noplaylist": True,
        }

        def search():
            with yt_dlp.YoutubeDL(options) as ydl:
                return ydl.extract_info(
                    f"ytsearch1:{query}",
                    download=False
                )

        info = await asyncio.to_thread(
            search
        )

        entries = info.get(
            "entries",
            []
        )

        if entries:
            result = entries[0]

            return {
                "title": result.get(
                    "title",
                    query
                ),
                "url": result.get(
                    "webpage_url"
                ) or result.get(
                    "url"
                ),
                "duration": result.get(
                    "duration"
                ),
            }

    except Exception:
        pass

    # SoundCloud
    try:

        options = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "extract_flat": True,
            "noplaylist": True,
        }

        def search_sc():
            with yt_dlp.YoutubeDL(options) as ydl:
                return ydl.extract_info(
                    f"scsearch1:{query}",
                    download=False
                )

        info = await asyncio.to_thread(
            search_sc
        )

        entries = info.get(
            "entries",
            []
        )

        if entries:
            result = entries[0]

            return {
                "title": result.get(
                    "title",
                    query
                ),
                "url": result.get(
                    "webpage_url"
                ) or result.get(
                    "url"
                ),
                "duration": result.get(
                    "duration"
                ),
            }

    except Exception:
        pass

    return None


async def get_audio_url(url):

    options = {
        "quiet": True,
        "no_warnings": True,
        "format": "bestaudio/best",
        "noplaylist": True,
    }

    def extract():
        with yt_dlp.YoutubeDL(options) as ydl:
            return ydl.extract_info(
                url,
                download=False
            )

    info = await asyncio.to_thread(
        extract
    )

    return {
        "url": info.get("url"),
        "title": info.get(
            "title",
            "أغنية"
        ),
        "duration": info.get(
            "duration"
        ),
    }


async def send_now_playing(
    chat_id,
    song,
    requester
):

    title = song.get(
        "title",
        "أغنية"
    )

    duration = format_duration(
        song.get("duration")
    )

    requester_name = (
        requester.mention
        if requester
        else "غير معروف"
    )

    caption = (
        "🎶 **مريومه الدلوعه**\n\n"
        f"🎵 **الأغنية:** {title}\n"
        f"⏱️ **المدة:** {duration}\n"
        f"👤 **الطلب بواسطة:** {requester_name}\n\n"
        "▶️ جاري التشغيل..."
    )

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "⏭ تخطي",
                    callback_data="music_skip"
                ),
                InlineKeyboardButton(
                    "⏹ وقف",
                    callback_data="music_stop"
                ),
            ],
            [
                InlineKeyboardButton(
                    "📋 القائمة",
                    callback_data="music_queue"
                )
            ]
        ]
    )

    try:

        if os.path.exists(
            PHOTO_PATH
        ):

            await bot.send_photo(
                chat_id,
                PHOTO_PATH,
                caption=caption,
                reply_markup=keyboard
            )

        else:

            await bot.send_message(
                chat_id,
                caption,
                reply_markup=keyboard
            )

    except Exception:

        await bot.send_message(
            chat_id,
            caption,
            reply_markup=keyboard
        )


async def play_song(
    chat_id,
    song
):

    try:

        audio = await get_audio_url(
            song["url"]
        )

        stream_url = audio.get(
            "url"
        )

        if not stream_url:
            raise Exception(
                "لم يتم العثور على رابط الصوت."
            )

        song["title"] = audio.get(
            "title",
            song.get("title", "أغنية")
        )

        song["duration"] = audio.get(
            "duration",
            song.get("duration")
        )

        current_song[chat_id] = song

        stream = MediaStream(
            stream_url
        )

        result = calls.play(
            chat_id,
            stream,
            GroupCallConfig(
                auto_start=True
            )
        )

        await maybe_await(result)

        await send_now_playing(
            chat_id,
            song,
            song.get("requester")
        )

        return True

    except Exception as e:

        print(
            "PLAY ERROR:",
            repr(e)
        )

        return False


async def play_next(chat_id):

    if not queues[chat_id]:
        current_song.pop(
            chat_id,
            None
        )
        return

    song = queues[chat_id].popleft()

    success = await play_song(
        chat_id,
        song
    )

    if not success:
        await play_next(
            chat_id
        )


# =========================================================
# أمر تشغيل
# =========================================================

@bot.on_message(
    filters.group &
    filters.text &
    filters.regex(r"^تشغيل(?:\s+(.+))?$")
)
async def music_command(_, message):

    if not group_enabled(
        message.chat.id
    ):
        return

    match = re.match(
        r"^تشغيل(?:\s+(.+))?$",
        message.text,
        re.S
    )

    query = (
        match.group(1).strip()
        if match and match.group(1)
        else None
    )

    if not query:

        waiting_for_song.add(
            message.chat.id
        )

        await message.reply_text(
            "🎵 قول اسم الأغنية."
        )

        return

    await add_song_to_queue(
        message,
        query
    )


async def add_song_to_queue(
    message,
    query
):

    await message.reply_text(
        f"🔎 بدور على: {query}"
    )

    song = await search_song(
        query
    )

    if not song:

        await message.reply_text(
            "❌ مش لاقي الأغنية."
        )

        return

    song["requester"] = (
        message.from_user
    )

    chat_id = message.chat.id

    if chat_id in current_song:

        queues[chat_id].append(
            song
        )

        await message.reply_text(
            f"➕ اتضافت للقائمة:\n"
            f"🎵 {song['title']}"
        )

    else:

        success = await play_song(
            chat_id,
            song
        )

        if not success:

            await message.reply_text(
                "❌ مقدرتش أشغل الأغنية."
            )


# =========================================================
# استقبال اسم الأغنية بعد تشغيل
# =========================================================

@bot.on_message(
    filters.group &
    filters.text
)
async def waiting_song_handler(
    _,
    message
):

    chat_id = message.chat.id

    if chat_id not in waiting_for_song:
        return

    if message.text.startswith(
        (
            "تشغيل",
            "وقف",
            "تخطي",
            "القائمة"
        )
    ):
        return

    waiting_for_song.discard(
        chat_id
    )

    await add_song_to_queue(
        message,
        message.text.strip()
    )


# =========================================================
# تخطي
# =========================================================

@bot.on_message(
    filters.group &
    filters.text &
    filters.regex(r"^تخطي$")
)
async def skip_song(_, message):

    if not group_enabled(
        message.chat.id
    ):
        return

    chat_id = message.chat.id

    try:

        await maybe_await(
            calls.leave_call(
                chat_id
            )
        )

    except Exception:
        pass

    current_song.pop(
        chat_id,
        None
    )

    if queues[chat_id]:

        await play_next(
            chat_id
        )

    else:

        await message.reply_text(
            "⏭️ مفيش أغاني تانية في القائمة."
        )


# =========================================================
# وقف
# =========================================================

@bot.on_message(
    filters.group &
    filters.text &
    filters.regex(r"^(وقف|إيقاف)$")
)
async def stop_music(_, message):

    if not group_enabled(
        message.chat.id
    ):
        return

    chat_id = message.chat.id

    queues[chat_id].clear()

    current_song.pop(
        chat_id,
        None
    )

    try:

        await maybe_await(
            calls.leave_call(
                chat_id
            )
        )

    except Exception:
        pass

    await message.reply_text(
        "⏹️ تم إيقاف الميوزك ومسح القائمة."
    )


# =========================================================
# القائمة
# =========================================================

@bot.on_message(
    filters.group &
    filters.text &
    filters.regex(r"^القائمة$")
)
async def show_queue(_, message):

    chat_id = message.chat.id

    lines = []

    if chat_id in current_song:

        lines.append(
            "▶️ الآن:\n"
            f"🎵 {current_song[chat_id].get('title', 'أغنية')}"
        )

    if queues[chat_id]:

        lines.append(
            "\n📋 القائمة:"
        )

        for index, song in enumerate(
            queues[chat_id],
            1
        ):
            lines.append(
                f"{index}. {song.get('title', 'أغنية')}"
            )

    if not lines:

        await message.reply_text(
            "📋 القائمة فاضية."
        )

        return

    await message.reply_text(
        "\n".join(lines)
    )


# =========================================================
# أزرار الميوزك
# =========================================================

@bot.on_callback_query()
async def music_buttons(_, query):

    data = query.data
    chat_id = query.message.chat.id

    if data == "music_skip":

        try:
            await maybe_await(
                calls.leave_call(
                    chat_id
                )
            )
        except Exception:
            pass

        current_song.pop(
            chat_id,
            None
        )

        await play_next(
            chat_id
        )

        await query.answer(
            "⏭ تم التخطي"
        )

    elif data == "music_stop":

        queues[chat_id].clear()

        current_song.pop(
            chat_id,
            None
        )

        try:
            await maybe_await(
                calls.leave_call(
                    chat_id
                )
            )
        except Exception:
            pass

        await query.answer(
            "⏹ تم الإيقاف"
        )

    elif data == "music_queue":

        lines = []

        if chat_id in current_song:
            lines.append(
                "▶️ الآن:\n"
                + current_song[chat_id].get(
                    "title",
                    "أغنية"
                )
            )

        if queues[chat_id]:

            lines.append(
                "\n📋 القائمة:"
            )

            for i, song in enumerate(
                queues[chat_id],
                1
            ):
                lines.append(
                    f"{i}. {song.get('title', 'أغنية')}"
                )

        if not lines:
            text = "📋 القائمة فاضية."
        else:
            text = "\n".join(lines)

        await query.answer()

        await query.message.reply_text(
            text
        )


# =========================================================
# الردود التلقائية
# =========================================================

@bot.on_message(
    filters.group &
    filters.text
)
async def auto_replies(
    _,
    message
):

    if not group_enabled(
        message.chat.id
    ):
        return

    if not message.text:
        return

    # الأوامر لا تدخل في الردود
    if message.text.startswith(
        (
            "اضف رد",
            "مسح رد",
            "تشغيل",
            "تخطي",
            "وقف",
            "إيقاف",
            "القائمة",
            "تفعيل البوت",
            "تعطيل البوت"
        )
    ):
        return

    chat_id = str(
        message.chat.id
    )

    group_replies = replies_data.get(
        chat_id,
        {}
    )

    text = message.text.strip().lower()

    if text in group_replies:

        try:
            await message.reply_text(
                group_replies[text]
            )
        except Exception:
            pass


# =========================================================
# الترحيب بالأعضاء الجدد
# =========================================================

@bot.on_message(
    filters.group &
    filters.new_chat_members
)
async def welcome_new_member(
    _,
    message
):

    for user in message.new_chat_members:

        name = user.mention

        await message.reply_text(
            f"🎉 أهلاً وسهلاً {name}\n\n"
            "💗 نورت المجموعة يا جميل."
        )


# =========================================================
# المساعدة
# =========================================================

@bot.on_message(
    filters.group &
    filters.text &
    filters.regex(r"^مساعدة$")
)
async def help_command(_, message):

    text = """
🤖 أوامر مريومه الدلوعه

🎵 الميوزك:
• تشغيل
• تشغيل اسم الأغنية
• تخطي
• وقف
• إيقاف
• القائمة

💬 الردود:
• اضف رد الكلمة = الرد
• مسح رد الكلمة

🛡️ الإدارة:
• ترقية
• تنزيل
• طرد
• حظر
• فك حظر
• كتم
• فك كتم
• تحذير
• تحذيرات
• مسح تحذيرات
• تثبيت
• إلغاء تثبيت
• المشرفين
• المالك
• رتبتي

🔒 الحماية:
• قفل الروابط
• فتح الروابط
• قفل الصور
• فتح الصور
• قفل الفيديو
• فتح الفيديو
• قفل الملصقات
• فتح الملصقات
• قفل الصوت
• فتح الصوت
• قفل السب
• فتح السب

⚙️ التحكم:
• تفعيل البوت
• تعطيل البوت
"""

    await message.reply_text(
        text
    )


# =========================================================
# تشغيل البوت
# =========================================================

async def main():

    print("Starting bot...")

    await bot.start()

    print("Starting assistant...")

    await assistant.start()

    print("Starting voice calls...")

    await maybe_await(
        calls.start()
    )

    print(
        "MariamMusicBot is running."
    )

    await asyncio.Event().wait()


if __name__ == "__main__":

    asyncio.run(
        main()
    )
