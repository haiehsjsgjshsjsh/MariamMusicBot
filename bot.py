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
# الإعدادات
# =========================================================

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]
SESSION_STRING = os.environ["SESSION_STRING"]

# اسم الصورة الموجودة في GitHub بجانب bot.py
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
        json.dump(data, f, ensure_ascii=False, indent=2)


REPLIES = load_json(REPLIES_FILE, {})
SETTINGS = load_json(SETTINGS_FILE, {})
WARNINGS = load_json(WARNINGS_FILE, {})


# =========================================================
# بيانات الميوزك
# =========================================================

queues = defaultdict(deque)
current_song = {}
waiting_for_song = set()


# =========================================================
# أدوات
# =========================================================

async def maybe_await(value):
    if inspect.isawaitable(value):
        return await value
    return value


async def get_member(message):
    try:
        return await bot.get_chat_member(
            message.chat.id,
            message.from_user.id
        )
    except Exception:
        return None


def get_status(member):
    if not member:
        return ""

    return str(member.status).lower()


async def is_owner(message):
    member = await get_member(message)
    status = get_status(member)

    return (
        "owner" in status
        or "creator" in status
    )


async def is_admin(message):
    member = await get_member(message)
    status = get_status(member)

    return (
        "owner" in status
        or "creator" in status
        or "administrator" in status
        or "admin" in status
    )


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
    chat_id = str(chat_id)

    if chat_id not in SETTINGS:
        SETTINGS[chat_id] = {
            "enabled": True,
            "links": False,
            "images": False,
            "videos": False,
            "stickers": False,
            "voice": False,
            "bad_words": False
        }

        save_json(
            SETTINGS_FILE,
            SETTINGS
        )

    return SETTINGS[chat_id]


def enabled(chat_id):
    return get_settings(chat_id).get(
        "enabled",
        True
    )


# =========================================================
# تفعيل البوت
# =========================================================

@bot.on_message(
    filters.group &
    filters.text &
    filters.regex(r"^تفعيل البوت$")
)
async def activate(_, message):

    if not await need_admin(message):
        return

    settings = get_settings(message.chat.id)
    settings["enabled"] = True

    save_json(
        SETTINGS_FILE,
        SETTINGS
    )

    await message.reply_text(
        "🟢 تم تفعيل البوت.\n\n"
        "🎵 الميوزك تعمل\n"
        "💬 الردود تعمل\n"
        "🛡️ الإدارة تعمل\n"
        "🔒 الحماية تعمل"
    )


# =========================================================
# تعطيل البوت
# =========================================================

@bot.on_message(
    filters.group &
    filters.text &
    filters.regex(r"^تعطيل البوت$")
)
async def deactivate(_, message):

    if not await need_admin(message):
        return

    settings = get_settings(message.chat.id)
    settings["enabled"] = False

    save_json(
        SETTINGS_FILE,
        SETTINGS
    )

    await message.reply_text(
        "🔴 تم تعطيل البوت في المجموعة."
    )


# =========================================================
# إضافة رد
# =========================================================

@bot.on_message(
    filters.group &
    filters.text &
    filters.regex(r"^اضف رد\s+(.+?)\s*=\s*(.+)$")
)
async def add_reply(_, message):

    if not enabled(message.chat.id):
        return

    if not await need_admin(message):
        return

    match = re.match(
        r"^اضف رد\s+(.+?)\s*=\s*(.+)$",
        message.text,
        re.S
    )

    word = match.group(1).strip().lower()
    reply = match.group(2).strip()

    chat_id = str(message.chat.id)

    if chat_id not in REPLIES:
        REPLIES[chat_id] = {}

    if (
        len(REPLIES[chat_id]) >= 500
        and word not in REPLIES[chat_id]
    ):
        await message.reply_text(
            "❌ وصلت للحد الأقصى: 500 رد."
        )
        return

    REPLIES[chat_id][word] = reply

    save_json(
        REPLIES_FILE,
        REPLIES
    )

    await message.reply_text(
        "✅ تم إضافة الرد.\n\n"
        f"🔤 الكلمة: {word}\n"
        f"💬 الرد: {reply}"
    )


# =========================================================
# مسح رد
# =========================================================

@bot.on_message(
    filters.group &
    filters.text &
    filters.regex(r"^مسح رد\s+(.+)$")
)
async def delete_reply(_, message):

    if not enabled(message.chat.id):
        return

    if not await need_admin(message):
        return

    word = message.text[
        len("مسح رد "):
    ].strip().lower()

    chat_id = str(message.chat.id)

    if (
        chat_id not in REPLIES
        or word not in REPLIES[chat_id]
    ):
        await message.reply_text(
            "❌ الرد ده مش موجود."
        )
        return

    del REPLIES[chat_id][word]

    save_json(
        REPLIES_FILE,
        REPLIES
    )

    await message.reply_text(
        f"✅ تم مسح الرد: {word}"
    )


# =========================================================
# الرتبة - إصلاح المالك والمشرف
# =========================================================

@bot.on_message(
    filters.group &
    filters.text &
    filters.regex(r"^رتبتي$")
)
async def my_rank(_, message):

    if not enabled(message.chat.id):
        return

    try:

        member = await bot.get_chat_member(
            message.chat.id,
            message.from_user.id
        )

        status = str(member.status).lower()

        if (
            "owner" in status
            or "creator" in status
        ):
            rank = "👑 مالك المجموعة"

        elif (
            "administrator" in status
            or "admin" in status
        ):
            rank = "🛡️ مشرف"

        else:
            rank = "👤 عضو"

        await message.reply_text(
            f"🎖️ رتبتك: {rank}"
        )

    except Exception as e:

        print("RANK ERROR:", repr(e))

        await message.reply_text(
            "❌ حصل خطأ وأنا بجيب رتبتك."
        )


# =========================================================
# المالك
# =========================================================

@bot.on_message(
    filters.group &
    filters.text &
    filters.regex(r"^المالك$")
)
async def owner_command(_, message):

    if not enabled(message.chat.id):
        return

    try:

        async for member in bot.get_chat_members(
            message.chat.id,
            filter="administrators"
        ):

            status = str(member.status).lower()

            if (
                "owner" in status
                or "creator" in status
            ):

                await message.reply_text(
                    "👑 مالك المجموعة:\n\n"
                    + member.user.mention
                )
                return

        await message.reply_text(
            "❌ مش قادر أحدد المالك."
        )

    except Exception as e:

        print("OWNER ERROR:", repr(e))

        await message.reply_text(
            "❌ حصل خطأ."
        )


# =========================================================
# المشرفين
# =========================================================

@bot.on_message(
    filters.group &
    filters.text &
    filters.regex(r"^المشرفين$")
)
async def admins_command(_, message):

    if not enabled(message.chat.id):
        return

    try:

        admins = []

        async for member in bot.get_chat_members(
            message.chat.id,
            filter="administrators"
        ):

            status = str(member.status).lower()

            if (
                "administrator" in status
                or "admin" in status
                or "owner" in status
                or "creator" in status
            ):
                admins.append(
                    f"• {member.user.mention}"
                )

        if not admins:
            await message.reply_text(
                "❌ مش قادر أجيب المشرفين."
            )
            return

        await message.reply_text(
            "🛡️ مشرفين المجموعة:\n\n"
            + "\n".join(admins)
        )

    except Exception as e:

        print("ADMINS ERROR:", repr(e))

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
async def promote(_, message):

    if not enabled(message.chat.id):
        return

    if not await need_admin(message):
        return

    if not message.reply_to_message:
        await message.reply_text(
            "❌ اعمل رد على رسالة الشخص واكتب: ترقية"
        )
        return

    user = message.reply_to_message.from_user

    try:

        privileges = ChatPrivileges(
            can_manage_chat=True,
            can_delete_messages=True,
            can_manage_video_chats=True,
            can_restrict_members=True,
            can_change_info=True,
            can_invite_users=True,
            can_pin_messages=True,
            can_promote_members=False
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
# تنزيل
# =========================================================

@bot.on_message(
    filters.group &
    filters.text &
    filters.regex(r"^تنزيل$")
)
async def demote(_, message):

    if not enabled(message.chat.id):
        return

    if not await need_owner(message):
        return

    if not message.reply_to_message:
        await message.reply_text(
            "❌ اعمل رد على رسالة المشرف واكتب: تنزيل"
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
            f"✅ تم تنزيل {user.mention}."
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
async def kick(_, message):

    if not enabled(message.chat.id):
        return

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
async def ban(_, message):

    if not enabled(message.chat.id):
        return

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
# فك حظر
# =========================================================

@bot.on_message(
    filters.group &
    filters.text &
    filters.regex(r"^فك حظر$")
)
async def unban(_, message):

    if not enabled(message.chat.id):
        return

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
async def mute(_, message):

    if not enabled(message.chat.id):
        return

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
# فك كتم
# =========================================================

@bot.on_message(
    filters.group &
    filters.text &
    filters.regex(r"^فك كتم$")
)
async def unmute(_, message):

    if not enabled(message.chat.id):
        return

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
# التحذير
# =========================================================

@bot.on_message(
    filters.group &
    filters.text &
    filters.regex(r"^تحذير$")
)
async def warn(_, message):

    if not enabled(message.chat.id):
        return

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

    WARNINGS.setdefault(chat_id, {})

    WARNINGS[chat_id][user_id] = (
        WARNINGS[chat_id].get(user_id, 0) + 1
    )

    save_json(
        WARNINGS_FILE,
        WARNINGS
    )

    await message.reply_text(
        f"⚠️ تم تحذير {user.mention}.\n"
        f"عدد التحذيرات: {WARNINGS[chat_id][user_id]}"
    )


# =========================================================
# التحذيرات
# =========================================================

@bot.on_message(
    filters.group &
    filters.text &
    filters.regex(r"^تحذيرات$")
)
async def warnings(_, message):

    if not enabled(message.chat.id):
        return

    if not message.reply_to_message:
        await message.reply_text(
            "❌ اعمل رد على رسالة الشخص واكتب: تحذيرات"
        )
        return

    user = message.reply_to_message.from_user

    count = WARNINGS.get(
        str(message.chat.id),
        {}
    ).get(
        str(user.id),
        0
    )

    await message.reply_text(
        f"⚠️ تحذيرات {user.mention}: {count}"
    )


# =========================================================
# مسح التحذيرات
# =========================================================

@bot.on_message(
    filters.group &
    filters.text &
    filters.regex(r"^مسح تحذيرات$")
)
async def clear_warnings(_, message):

    if not enabled(message.chat.id):
        return

    if not await need_admin(message):
        return

    if not message.reply_to_message:
        await message.reply_text(
            "❌ اعمل رد على الشخص واكتب: مسح تحذيرات"
        )
        return

    user = message.reply_to_message.from_user

    chat_id = str(message.chat.id)
    user_id = str(user.id)

    if chat_id in WARNINGS:
        WARNINGS[chat_id].pop(
            user_id,
            None
        )

    save_json(
        WARNINGS_FILE,
        WARNINGS
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
async def pin(_, message):

    if not enabled(message.chat.id):
        return

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


# =========================================================
# إلغاء التثبيت
# =========================================================

@bot.on_message(
    filters.group &
    filters.text &
    filters.regex(r"^إلغاء تثبيت$")
)
async def unpin(_, message):

    if not enabled(message.chat.id):
        return

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
# الحماية
# =========================================================

@bot.on_message(
    filters.group &
    filters.text &
    filters.regex(
        r"^(قفل|فتح)\s+(الروابط|الصور|الفيديو|الملصقات|الصوت|السب)$"
    )
)
async def protection_settings(_, message):

    if not enabled(message.chat.id):
        return

    if not await need_admin(message):
        return

    match = re.match(
        r"^(قفل|فتح)\s+(الروابط|الصور|الفيديو|الملصقات|الصوت|السب)$",
        message.text
    )

    action = match.group(1)
    item = match.group(2)

    mapping = {
        "الروابط": "links",
        "الصور": "images",
        "الفيديو": "videos",
        "الملصقات": "stickers",
        "الصوت": "voice",
        "السب": "bad_words"
    }

    settings = get_settings(
        message.chat.id
    )

    settings[mapping[item]] = (
        action == "قفل"
    )

    save_json(
        SETTINGS_FILE,
        SETTINGS
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
# الكلمات الممنوعة
# =========================================================

BAD_WORDS = {
    "كلمة_ممنوعة_1",
    "كلمة_ممنوعة_2"
}


@bot.on_message(filters.group)
async def protection_handler(_, message):

    if not enabled(message.chat.id):
        return

    if not message.from_user:
        return

    if await is_admin(message):
        return

    settings = get_settings(
        message.chat.id
    )

    # الروابط
    if (
        settings.get("links")
        and message.text
        and re.search(
            r"(https?://|www\.|t\.me/|telegram\.me/)",
            message.text,
            re.I
        )
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
    if (
        settings.get("voice")
        and (message.voice or message.audio)
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
# البحث عن الأغنية
# =========================================================

async def search_song(query):

    options = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "extract_flat": True,
        "noplaylist": True
    }

    # YouTube
    try:

        def search_youtube():

            with yt_dlp.YoutubeDL(options) as ydl:

                return ydl.extract_info(
                    f"ytsearch1:{query}",
                    download=False
                )

        info = await asyncio.to_thread(
            search_youtube
        )

        entries = info.get(
            "entries",
            []
        )

        if entries:

            item = entries[0]

            return {
                "title": item.get(
                    "title",
                    query
                ),
                "url": item.get(
                    "webpage_url"
                ) or item.get(
                    "url"
                ),
                "duration": item.get(
                    "duration"
                )
            }

    except Exception as e:

        print(
            "YOUTUBE SEARCH ERROR:",
            repr(e)
        )


    # SoundCloud
    try:

        def search_soundcloud():

            with yt_dlp.YoutubeDL(options) as ydl:

                return ydl.extract_info(
                    f"scsearch1:{query}",
                    download=False
                )

        info = await asyncio.to_thread(
            search_soundcloud
        )

        entries = info.get(
            "entries",
            []
        )

        if entries:

            item = entries[0]

            return {
                "title": item.get(
                    "title",
                    query
                ),
                "url": item.get(
                    "webpage_url"
                ) or item.get(
                    "url"
                ),
                "duration": item.get(
                    "duration"
                )
            }

    except Exception as e:

        print(
            "SOUNDCLOUD SEARCH ERROR:",
            repr(e)
        )

    return None


# =========================================================
# استخراج الصوت
# =========================================================

async def get_audio(url):

    options = {
        "quiet": True,
        "no_warnings": True,
        "format": "bestaudio/best",
        "noplaylist": True
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
        )
    }


# =========================================================
# مدة الأغنية
# =========================================================

def duration_text(seconds):

    if not seconds:
        return "غير معروف"

    try:
        seconds = int(seconds)
    except Exception:
        return "غير معروف"

    minutes = seconds // 60
    seconds = seconds % 60

    return f"{minutes:02d}:{seconds:02d}"


# =========================================================
# رسالة التشغيل
# =========================================================

async def now_playing(chat_id, song):

    title = song.get(
        "title",
        "أغنية"
    )

    duration = duration_text(
        song.get("duration")
    )

    requester = song.get(
        "requester"
    )

    if requester:
        requester_text = requester.mention
    else:
        requester_text = "غير معروف"

    caption = (
        "🎶 **مريومه الدلوعه**\n\n"
        f"🎵 **الأغنية:** {title}\n"
        f"⏱️ **المدة:** {duration}\n"
        f"👤 **الطلب بواسطة:** {requester_text}\n\n"
        "▶️ **جاري التشغيل...**"
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
                )
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


# =========================================================
# تشغيل أغنية
# =========================================================

async def play_song(chat_id, song):

    try:

        audio = await get_audio(
            song["url"]
        )

        stream_url = audio.get(
            "url"
        )

        if not stream_url:
            return False

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

        await maybe_await(
            result
        )

        await now_playing(
            chat_id,
            song
        )

        return True

    except Exception as e:

        print(
            "PLAY ERROR:",
            repr(e)
        )

        return False


# =========================================================
# تشغيل التالي
# =========================================================

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
# تشغيل
# تشغيل
# تشغيل اسم الأغنية
# =========================================================

@bot.on_message(
    filters.group &
    filters.text &
    filters.regex(r"^تشغيل(?:\s+(.+))?$")
)
async def music_command(_, message):

    if not enabled(message.chat.id):
        return

    match = re.match(
        r"^تشغيل(?:\s+(.+))?$",
        message.text,
        re.S
    )

    query = None

    if match and match.group(1):

        query = match.group(
            1
        ).strip()

    # لو كتب تشغيل فقط
    if not query:

        waiting_for_song.add(
            message.chat.id
        )

        await message.reply_text(
            "🎵 قول اسم الأغنية."
        )

        return

    await add_song(
        message,
        query
    )


# =========================================================
# إضافة أغنية للقائمة
# =========================================================

async def add_song(message, query):

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
            "➕ اتضافت للقائمة:\n"
            f"🎵 {song['title']}"
        )

        return

    success = await play_song(
        chat_id,
        song
    )

    if not success:

        await message.reply_text(
            "❌ مقدرتش أشغل الأغنية."
        )


# =========================================================
# بعد تشغيل: قول اسم الأغنية
# =========================================================

@bot.on_message(
    filters.group &
    filters.text
)
async def waiting_song(_, message):

    chat_id = message.chat.id

    if chat_id not in waiting_for_song:
        return

    if message.text in (
        "تشغيل",
        "تخطي",
        "وقف",
        "إيقاف",
        "القائمة"
    ):
        return

    waiting_for_song.discard(
        chat_id
    )

    await add_song(
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
async def skip(_, message):

    if not enabled(message.chat.id):
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
            "⏭️ مفيش أغاني تانية."
        )


# =========================================================
# وقف
# =========================================================

@bot.on_message(
    filters.group &
    filters.text &
    filters.regex(r"^(وقف|إيقاف)$")
)
async def stop(_, message):

    if not enabled(message.chat.id):
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

async def queue_text(chat_id):

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

        return "📋 القائمة فاضية."

    return "\n".join(lines)


@bot.on_message(
    filters.group &
    filters.text &
    filters.regex(r"^القائمة$")
)
async def show_queue(_, message):

    if not enabled(message.chat.id):
        return

    await message.reply_text(
        await queue_text(
            message.chat.id
        )
    )


# =========================================================
# أزرار الميوزك
# =========================================================

@bot.on_callback_query()
async def music_buttons(_, query):

    if query.data not in (
        "music_skip",
        "music_stop",
        "music_queue"
    ):
        return

    chat_id = query.message.chat.id

    if query.data == "music_skip":

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

    elif query.data == "music_stop":

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

    elif query.data == "music_queue":

        await query.answer()

        await query.message.reply_text(
            await queue_text(chat_id)
        )


# =========================================================
# الردود التلقائية
# =========================================================

@bot.on_message(
    filters.group &
    filters.text
)
async def auto_reply(_, message):

    if not enabled(message.chat.id):
        return

    text = message.text.strip().lower()

    if text.startswith(
        (
            "اضف رد",
            "مسح رد",
            "تشغيل",
            "تخطي",
            "وقف",
            "إيقاف",
            "القائمة",
            "تفعيل البوت",
            "تعطيل البوت",
            "مساعدة"
        )
    ):
        return

    chat_id = str(
        message.chat.id
    )

    replies = REPLIES.get(
        chat_id,
        {}
    )

    if text in replies:

        await message.reply_text(
            replies[text]
        )


# =========================================================
# الترحيب
# =========================================================

@bot.on_message(
    filters.group &
    filters.new_chat_members
)
async def welcome(_, message):

    if not enabled(message.chat.id):
        return

    for user in message.new_chat_members:

        await message.reply_text(
            f"🎉 أهلاً وسهلاً {user.mention}\n\n"
            "💗 نورت المجموعة."
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

    if not enabled(message.chat.id):
        return

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

⚙️ التحكم:
• تفعيل البوت
• تعطيل البوت

👑 الرتب:
• رتبتي
• المالك
• المشرفين

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
    asyncio.run(main())
