# ============================================================
# MariamMusicBot - FULL VERSION
# Pyrogram + PyTgCalls + yt-dlp
# ============================================================

import os
import re
import json
import asyncio
import inspect
from collections import defaultdict, deque

import yt_dlp

from pyrogram import Client, filters, idle, enums
from pyrogram.types import (
    ChatPrivileges,
    ChatPermissions,
    BotCommand,
)

from pytgcalls import PyTgCalls
from pytgcalls import filters as call_filters
from pytgcalls.types import MediaStream
from pytgcalls.types import AudioQuality


# ============================================================
# ENVIRONMENT VARIABLES
# ============================================================

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
SESSION_STRING = os.getenv("SESSION_STRING", "")

# اختياري:
# لو عندك ملف Cookies من YouTube ارفع مساره هنا
# مثال:
# YOUTUBE_COOKIES=/app/cookies.txt
YOUTUBE_COOKIES = os.getenv("YOUTUBE_COOKIES", "").strip()


# ============================================================
# CHECK CONFIG
# ============================================================

if not API_ID:
    raise RuntimeError("❌ API_ID is missing")

if not API_HASH:
    raise RuntimeError("❌ API_HASH is missing")

if not BOT_TOKEN:
    raise RuntimeError("❌ BOT_TOKEN is missing")

if not SESSION_STRING:
    raise RuntimeError("❌ SESSION_STRING is missing")


# ============================================================
# CLIENTS
# ============================================================

bot = Client(
    "MariamMusicBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
)

music_user = Client(
    "MariamMusicUser",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING,
)

call = PyTgCalls(music_user)


# ============================================================
# DATA
# ============================================================

DATA_FILE = "mariam_data.json"

data = {
    "enabled_chats": {},
    "custom_replies": {},
    "bad_words_enabled": {},
}

queues = defaultdict(deque)
current_song = {}
playing = set()


# ============================================================
# LOAD / SAVE DATA
# ============================================================

def load_data():
    global data

    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)

            if isinstance(loaded, dict):
                data.update(loaded)

        print("✅ Data loaded")

    except Exception as e:
        print(f"⚠️ Data load error: {e}")


def save_data():
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    except Exception as e:
        print(f"⚠️ Data save error: {e}")


# ============================================================
# HELPERS
# ============================================================

async def maybe_await(value):
    if inspect.isawaitable(value):
        return await value
    return value


def chat_enabled(chat_id):
    return bool(data["enabled_chats"].get(str(chat_id), False))


def set_chat_enabled(chat_id, value):
    data["enabled_chats"][str(chat_id)] = value
    save_data()


def normalize_text(text):
    if not text:
        return ""

    text = text.lower().strip()

    replacements = {
        "أ": "ا",
        "إ": "ا",
        "آ": "ا",
        "ة": "ه",
        "ى": "ي",
    }

    for a, b in replacements.items():
        text = text.replace(a, b)

    return text


# ============================================================
# TARGET USER
# ============================================================

async def get_target_user(message):
    """
    يدعم:
    - Reply على رسالة الشخص
    - @username
    - رقم ID
    """

    if message.reply_to_message:
        if message.reply_to_message.from_user:
            return message.reply_to_message.from_user

    text = (message.text or "").strip()
    parts = text.split(maxsplit=1)

    if len(parts) < 2:
        return None

    target = parts[1].strip()

    if target.startswith("@"):
        try:
            return await bot.get_users(target)
        except Exception:
            return None

    if target.lstrip("-").isdigit():
        try:
            return await bot.get_users(int(target))
        except Exception:
            return None

    return None


# ============================================================
# ADMIN CHECK
# ============================================================

async def get_member(chat_id, user_id):
    try:
        return await bot.get_chat_member(chat_id, user_id)
    except Exception:
        return None


async def is_admin(chat_id, user_id):
    member = await get_member(chat_id, user_id)

    if not member:
        return False

    return member.status in (
        enums.ChatMemberStatus.OWNER,
        enums.ChatMemberStatus.ADMINISTRATOR,
    )


async def is_owner(chat_id, user_id):
    member = await get_member(chat_id, user_id)

    if not member:
        return False

    return member.status == enums.ChatMemberStatus.OWNER


async def bot_has_admin_right(chat_id, right):
    try:
        me = await bot.get_me()
        member = await bot.get_chat_member(chat_id, me.id)

        if member.status == enums.ChatMemberStatus.OWNER:
            return True

        if member.status != enums.ChatMemberStatus.ADMINISTRATOR:
            return False

        privileges = member.privileges

        if not privileges:
            return False

        return bool(getattr(privileges, right, False))

    except Exception:
        return False


# ============================================================
# COMMANDS TEXT
# ============================================================

HELP_TEXT = """
╔════════════════════╗
      🎀 أوامر MariamMusicBot
╚════════════════════╝

🎵 قسم الموسيقى

• تشغيل اسم الأغنية
مثال:
تشغيل عمرو دياب تملي معاك

• تخطي
لتخطي الأغنية الحالية

• إيقاف
لإيقاف التشغيل والخروج من المكالمة

• الأغنية
لمعرفة الأغنية الحالية

• الطابور
لعرض الأغاني الموجودة في الانتظار


👑 قسم الإدارة

• ترقية
↳ اعمل Reply على الشخص ثم اكتب ترقية

• تنزيل رتبة
↳ اعمل Reply على المشرف ثم اكتب تنزيل رتبة

• طرد
↳ اعمل Reply على الشخص ثم اكتب طرد


⚙️ تشغيل البوت

• تفعيل البوت

• تعطيل البوت


🛡 الحماية

• منع السب
• السماح بالسب


💬 الردود

• اضف رد الكلمة الرد

مثال:
اضف رد صباح الخير صباح النور ❤️

• مسح الرد الكلمة


🎮 الألعاب

• العاب
• نرد
• عملة
• حظك اليوم


ℹ️ معلومات

• الأوامر
• حالة البوت
"""


# ============================================================
# START
# ============================================================

@bot.on_message(filters.private & filters.command("start"))
async def start_private(client, message):

    await message.reply_text(
        "👋 أهلاً بيك في MariamMusicBot\n\n"
        "ضيفني لجروبك وخليني مشرف عشان أقدر أشغل الموسيقى "
        "وأستخدم أوامر الإدارة.\n\n"
        "اكتب:\n"
        "الأوامر\n"
        "علشان تشوف كل الأوامر."
    )


# ============================================================
# HELP
# ============================================================

@bot.on_message(filters.group & filters.text, group=1)
async def help_handler(client, message):

    text = normalize_text(message.text)

    if text in (
        "الاوامر",
        "اوامر",
        "اوامر البوت",
        "/الاوامر",
    ):
        await message.reply_text(HELP_TEXT)


# ============================================================
# ENABLE
# ============================================================

@bot.on_message(filters.group & filters.text, group=2)
async def enable_handler(client, message):

    text = normalize_text(message.text)

    if text not in ("تفعيل البوت", "تفعيل"):
        return

    if not await is_admin(message.chat.id, message.from_user.id):
        await message.reply_text("❌ الأمر ده للمشرفين فقط.")
        return

    set_chat_enabled(message.chat.id, True)

    await message.reply_text(
        "✅ تم تفعيل البوت في الجروب.\n\n"
        "🎵 تقدر تستخدم:\n"
        "تشغيل + اسم الأغنية"
    )


# ============================================================
# DISABLE
# ============================================================

@bot.on_message(filters.group & filters.text, group=3)
async def disable_handler(client, message):

    text = normalize_text(message.text)

    if text not in ("تعطيل البوت", "تعطيل"):
        return

    if not await is_admin(message.chat.id, message.from_user.id):
        await message.reply_text("❌ الأمر ده للمشرفين فقط.")
        return

    set_chat_enabled(message.chat.id, False)

    try:
        await call.leave_call(message.chat.id)
    except Exception:
        pass

    queues[message.chat.id].clear()
    current_song.pop(message.chat.id, None)
    playing.discard(message.chat.id)

    await message.reply_text("🛑 تم تعطيل البوت.")


# ============================================================
# PROMOTE
# ============================================================

@bot.on_message(filters.group & filters.text, group=4)
async def promote_handler(client, message):

    text = normalize_text(message.text)

    if not text.startswith("ترقيه") and not text.startswith("ترقية"):
        return

    if not await is_admin(message.chat.id, message.from_user.id):
        await message.reply_text("❌ لازم تكون مشرف.")
        return

    if not await bot_has_admin_right(
        message.chat.id,
        "can_promote_members"
    ):
        await message.reply_text(
            "❌ البوت مش معاه صلاحية **إضافة مشرفين**.\n\n"
            "افتح إعدادات المشرفين وخلي البوت عنده:\n"
            "👑 إضافة مشرفين"
        )
        return

    target = await get_target_user(message)

    if not target:
        await message.reply_text(
            "❌ اعمل Reply على الشخص واكتب:\n"
            "ترقية"
        )
        return

    if target.is_self:
        await message.reply_text("❌ مينفعش أرقي نفسي.")
        return

    try:
        target_member = await bot.get_chat_member(
            message.chat.id,
            target.id
        )

        if target_member.status == enums.ChatMemberStatus.OWNER:
            await message.reply_text("❌ ده مالك الجروب.")
            return

        privileges = ChatPrivileges(
            can_manage_chat=True,
            can_delete_messages=True,
            can_manage_video_chats=True,
            can_restrict_members=True,
            can_invite_users=True,
            can_pin_messages=True,
            can_change_info=False,
            can_promote_members=False,
            is_anonymous=False,
        )

        await bot.promote_chat_member(
            message.chat.id,
            target.id,
            privileges=privileges,
        )

        await message.reply_text(
            f"👑 تم ترقية {target.mention} إلى مشرف بنجاح."
        )

    except Exception as e:

        error = str(e)

        if "CHAT_ADMIN_REQUIRED" in error:
            msg = "❌ البوت لازم يكون مشرف ومعاه صلاحيات الإدارة."

        elif "RIGHT_FORBIDDEN" in error:
            msg = "❌ البوت مش معاه صلاحية ترقية الأعضاء."

        elif "USER_NOT_PARTICIPANT" in error:
            msg = "❌ الشخص مش موجود في الجروب."

        else:
            msg = f"❌ فشلت الترقية:\n`{error[:500]}`"

        await message.reply_text(msg)


# ============================================================
# DEMOTE
# ============================================================

@bot.on_message(filters.group & filters.text, group=5)
async def demote_handler(client, message):

    text = normalize_text(message.text)

    if not (
        text.startswith("تنزيل رتب")
        or text.startswith("تنزيل رتبه")
        or text.startswith("تنزيل")
    ):
        return

    if not await is_admin(message.chat.id, message.from_user.id):
        await message.reply_text("❌ لازم تكون مشرف.")
        return

    if not await bot_has_admin_right(
        message.chat.id,
        "can_promote_members"
    ):
        await message.reply_text(
            "❌ البوت محتاج صلاحية إضافة مشرفين/تعديل المشرفين."
        )
        return

    target = await get_target_user(message)

    if not target:
        await message.reply_text(
            "❌ اعمل Reply على المشرف واكتب:\n"
            "تنزيل رتبة"
        )
        return

    try:

        target_member = await bot.get_chat_member(
            message.chat.id,
            target.id
        )

        if target_member.status == enums.ChatMemberStatus.OWNER:
            await message.reply_text(
                "❌ مينفعش تنزيل مالك الجروب."
            )
            return

        privileges = ChatPrivileges(
            can_manage_chat=False,
            can_delete_messages=False,
            can_manage_video_chats=False,
            can_restrict_members=False,
            can_invite_users=False,
            can_pin_messages=False,
            can_change_info=False,
            can_promote_members=False,
            is_anonymous=False,
        )

        await bot.promote_chat_member(
            message.chat.id,
            target.id,
            privileges=privileges,
        )

        await message.reply_text(
            f"✅ تم تنزيل رتبة {target.mention}."
        )

    except Exception as e:
        await message.reply_text(
            f"❌ فشل تنزيل الرتبة:\n`{str(e)[:500]}`"
        )


# ============================================================
# KICK
# ============================================================

@bot.on_message(filters.group & filters.text, group=6)
async def kick_handler(client, message):

    text = normalize_text(message.text)

    if text not in ("طرد", "اطرد"):
        return

    if not await is_admin(message.chat.id, message.from_user.id):
        await message.reply_text("❌ الأمر للمشرفين فقط.")
        return

    if not await bot_has_admin_right(
        message.chat.id,
        "can_restrict_members"
    ):
        await message.reply_text(
            "❌ البوت محتاج صلاحية حظر/تقييد الأعضاء."
        )
        return

    target = await get_target_user(message)

    if not target:
        await message.reply_text(
            "❌ اعمل Reply على الشخص واكتب:\n"
            "طرد"
        )
        return

    try:

        target_member = await bot.get_chat_member(
            message.chat.id,
            target.id
        )

        if target_member.status == enums.ChatMemberStatus.OWNER:
            await message.reply_text("❌ مينفعش طرد مالك الجروب.")
            return

        if target_member.status == enums.ChatMemberStatus.ADMINISTRATOR:
            await message.reply_text(
                "❌ لازم تنزيل رتبة المشرف الأول."
            )
            return

        await bot.ban_chat_member(
            message.chat.id,
            target.id
        )

        await bot.unban_chat_member(
            message.chat.id,
            target.id
        )

        await message.reply_text(
            f"🚫 تم طرد {target.mention}."
        )

    except Exception as e:
        await message.reply_text(
            f"❌ فشل الطرد:\n`{str(e)[:500]}`"
        )


# ============================================================
# BAD WORDS
# ============================================================

BAD_WORDS = {
    "كس",
    "شرموط",
    "شرموطة",
    "خول",
    "متناك",
    "نيك",
    "وسخ",
    "زب",
}


@bot.on_message(filters.group & filters.text, group=7)
async def protection_handler(client, message):

    if not data["bad_words_enabled"].get(
        str(message.chat.id),
        False
    ):
        return

    if await is_admin(message.chat.id, message.from_user.id):
        return

    text = normalize_text(message.text)

    for word in BAD_WORDS:

        if word in text.split() or word in text:

            try:
                await message.delete()

                await message.reply_text(
                    f"⚠️ ممنوع السب هنا يا {message.from_user.mention}"
                )

            except Exception:
                pass

            break


# ============================================================
# ENABLE BAD WORD PROTECTION
# ============================================================

@bot.on_message(filters.group & filters.text, group=8)
async def bad_words_on_handler(client, message):

    text = normalize_text(message.text)

    if text != "منع السب":
        return

    if not await is_admin(message.chat.id, message.from_user.id):
        await message.reply_text("❌ للمشرفين فقط.")
        return

    data["bad_words_enabled"][str(message.chat.id)] = True
    save_data()

    await message.reply_text(
        "🛡️ تم تفعيل منع السب."
    )


# ============================================================
# DISABLE BAD WORD PROTECTION
# ============================================================

@bot.on_message(filters.group & filters.text, group=9)
async def bad_words_off_handler(client, message):

    text = normalize_text(message.text)

    if text != "السماح بالسب":
        return

    if not await is_admin(message.chat.id, message.from_user.id):
        await message.reply_text("❌ للمشرفين فقط.")
        return

    data["bad_words_enabled"][str(message.chat.id)] = False
    save_data()

    await message.reply_text(
        "✅ تم إيقاف منع السب."
    )


# ============================================================
# ADD CUSTOM REPLY
# ============================================================

@bot.on_message(filters.group & filters.text, group=10)
async def add_reply_handler(client, message):

    text = message.text or ""

    normalized = normalize_text(text)

    if not normalized.startswith("اضف رد "):
        return

    parts = text.split(maxsplit=2)

    if len(parts) < 3:
        await message.reply_text(
            "❌ الصيغة:\n"
            "اضف رد الكلمة الرد"
        )
        return

    keyword = parts[1].strip()
    reply = parts[2].strip()

    chat_key = str(message.chat.id)

    if chat_key not in data["custom_replies"]:
        data["custom_replies"][chat_key] = {}

    data["custom_replies"][chat_key][
        normalize_text(keyword)
    ] = reply

    save_data()

    await message.reply_text(
        f"✅ تمت إضافة الرد على: {keyword}"
    )


# ============================================================
# DELETE CUSTOM REPLY
# ============================================================

@bot.on_message(filters.group & filters.text, group=11)
async def delete_reply_handler(client, message):

    text = message.text or ""
    normalized = normalize_text(text)

    if not normalized.startswith("مسح الرد "):
        return

    parts = text.split(maxsplit=2)

    if len(parts) < 3:
        await message.reply_text(
            "❌ الصيغة:\n"
            "مسح الرد الكلمة"
        )
        return

    keyword = normalize_text(parts[2])
    chat_key = str(message.chat.id)

    replies = data["custom_replies"].get(chat_key, {})

    if keyword not in replies:
        await message.reply_text(
            "❌ الرد ده مش موجود."
        )
        return

    del replies[keyword]
    save_data()

    await message.reply_text(
        "✅ تم حذف الرد."
    )


# ============================================================
# CUSTOM REPLIES
# ============================================================

@bot.on_message(filters.group & filters.text, group=12)
async def custom_reply_handler(client, message):

    text = normalize_text(message.text)

    if not text:
        return

    chat_key = str(message.chat.id)

    replies = data["custom_replies"].get(
        chat_key,
        {}
    )

    if text in replies:

        await message.reply_text(
            replies[text]
        )


# ============================================================
# YOUTUBE SEARCH
# ============================================================

def youtube_search(query):

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "extract_flat": True,
        "noplaylist": True,
        "default_search": "ytsearch5",
    }

    if YOUTUBE_COOKIES:
        ydl_opts["cookiefile"] = YOUTUBE_COOKIES

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:

        result = ydl.extract_info(
            f"ytsearch5:{query}",
            download=False,
        )

    entries = result.get("entries") or []

    if not entries:
        return None

    return entries[0]


# ============================================================
# GET PLAY URL
# ============================================================

def get_audio_url(video_url):

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "format": "bestaudio/best",
        "noplaylist": True,
    }

    if YOUTUBE_COOKIES:
        ydl_opts["cookiefile"] = YOUTUBE_COOKIES

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:

        info = ydl.extract_info(
            video_url,
            download=False,
        )

        return {
            "url": info.get("url"),
            "title": info.get("title", "Unknown"),
            "webpage_url": info.get("webpage_url", video_url),
            "duration": info.get("duration", 0),
        }


# ============================================================
# PLAY CURRENT
# ============================================================

async def play_current(chat_id):

    if not queues[chat_id]:

        try:
            await call.leave_call(chat_id)
        except Exception:
            pass

        playing.discard(chat_id)
        current_song.pop(chat_id, None)

        return False

    song = queues[chat_id].popleft()

    try:

        audio = await asyncio.to_thread(
            get_audio_url,
            song["webpage_url"]
        )

        if not audio or not audio.get("url"):
            raise RuntimeError(
                "لم يتم الحصول على رابط الصوت."
            )

        current_song[chat_id] = {
            **song,
            **audio,
        }

        stream = MediaStream(
            audio["url"],
            AudioQuality.HIGH,
        )

        await call.play(
            chat_id,
            stream,
        )

        playing.add(chat_id)

        return True

    except Exception as e:

        current_song.pop(chat_id, None)

        print(
            f"PLAY ERROR: {repr(e)}"
        )

        return False


# ============================================================
# PLAY COMMAND
# ============================================================

@bot.on_message(filters.group & filters.text, group=20)
async def play_handler(client, message):

    text = message.text or ""

    normalized = normalize_text(text)

    if not normalized.startswith("تشغيل"):
        return

    if not chat_enabled(message.chat.id):

        await message.reply_text(
            "⚠️ البوت مش متفعل هنا.\n"
            "اكتب: تفعيل البوت"
        )

        return

    parts = text.split(maxsplit=1)

    if len(parts) < 2:

        await message.reply_text(
            "🎵 قول اسم الأغنية بعد تشغيل.\n\n"
            "مثال:\n"
            "تشغيل تملي معاك"
        )

        return

    query = parts[1].strip()

    wait = await message.reply_text(
        "🔎 بدور على الأغنية..."
    )

    try:

        result = await asyncio.to_thread(
            youtube_search,
            query
        )

        if not result:

            await wait.edit_text(
                "❌ ملقيتش الأغنية."
            )

            return

        webpage_url = result.get("webpage_url")

        if not webpage_url and result.get("id"):

            webpage_url = (
                "https://www.youtube.com/watch?v="
                + result["id"]
            )

        song = {
            "title": result.get(
                "title",
                query
            ),
            "webpage_url": webpage_url,
            "requested_by": (
                message.from_user.mention
                if message.from_user
                else "Unknown"
            ),
        }

        queues[message.chat.id].append(song)

        if message.chat.id in playing:

            await wait.edit_text(
                f"➕ تمت إضافة الأغنية للطابور:\n"
                f"🎵 {song['title']}"
            )

            return

        await wait.edit_text(
            "⏳ جاري تشغيل الأغنية..."
        )

        success = await play_current(
            message.chat.id
        )

        if success:

            await wait.edit_text(
                f"🎵 يتم التشغيل الآن:\n"
                f"**{current_song[message.chat.id]['title']}**"
            )

        else:

            await wait.edit_text(
                "❌ مقدرتش أشغل الأغنية.\n\n"
                "لو ظهر في اللوج:\n"
                "Sign in to confirm you're not a bot\n"
                "فالمشكلة من حماية YouTube وهنحتاج Cookies."
            )

    except Exception as e:

        print(
            f"SEARCH/PLAY ERROR: {repr(e)}"
        )

        await wait.edit_text(
            "❌ حصل خطأ أثناء البحث/التشغيل.\n\n"
            f"`{str(e)[:500]}`"
        )


# ============================================================
# SKIP
# ============================================================

@bot.on_message(filters.group & filters.text, group=21)
async def skip_handler(client, message):

    text = normalize_text(message.text)

    if text not in ("تخطي", "تخطي الاغنيه"):
        return

    if not chat_enabled(message.chat.id):
        return

    if not await is_admin(
        message.chat.id,
        message.from_user.id
    ):
        await message.reply_text(
            "❌ تخطي الأغنية للمشرفين فقط."
        )
        return

    if not queues[message.chat.id] and message.chat.id not in playing:

        await message.reply_text(
            "❌ مفيش أغنية شغالة."
        )
        return

    try:

        await call.leave_call(
            message.chat.id
        )

    except Exception:
        pass

    playing.discard(message.chat.id)
    current_song.pop(message.chat.id, None)

    success = await play_current(
        message.chat.id
    )

    if success:

        await message.reply_text(
            f"⏭️ تم التخطي.\n"
            f"🎵 الآن: {current_song[message.chat.id]['title']}"
        )

    else:

        await message.reply_text(
            "⏭️ تم التخطي.\n"
            "📭 مفيش أغاني تانية في الطابور."
        )


# ============================================================
# STOP
# ============================================================

@bot.on_message(filters.group & filters.text, group=22)
async def stop_handler(client, message):

    text = normalize_text(message.text)

    if text not in (
        "ايقاف",
        "وقف",
        "وقف التشغيل",
    ):
        return

    if not await is_admin(
        message.chat.id,
        message.from_user.id
    ):
        await message.reply_text(
            "❌ إيقاف الموسيقى للمشرفين فقط."
        )
        return

    try:
        await call.leave_call(
            message.chat.id
        )
    except Exception:
        pass

    queues[message.chat.id].clear()

    current_song.pop(
        message.chat.id,
        None
    )

    playing.discard(
        message.chat.id
    )

    await message.reply_text(
        "⏹️ تم إيقاف التشغيل وإفراغ الطابور."
    )


# ============================================================
# NOW PLAYING
# ============================================================

@bot.on_message(filters.group & filters.text, group=23)
async def now_playing_handler(client, message):

    text = normalize_text(message.text)

    if text not in (
        "الاغنيه",
        "الاغنية",
        "الان",
    ):
        return

    song = current_song.get(
        message.chat.id
    )

    if not song:

        await message.reply_text(
            "🎵 مفيش أغنية شغالة دلوقتي."
        )

        return

    await message.reply_text(
        "🎵 الأغنية الحالية:\n\n"
        f"**{song['title']}**"
    )


# ============================================================
# QUEUE
# ============================================================

@bot.on_message(filters.group & filters.text, group=24)
async def queue_handler(client, message):

    text = normalize_text(message.text)

    if text not in (
        "الطابور",
        "قائمه التشغيل",
    ):
        return

    q = queues[message.chat.id]

    if not q:

        await message.reply_text(
            "📭 الطابور فاضي."
        )

        return

    lines = ["📋 **الطابور:**\n"]

    for i, song in enumerate(q, 1):

        lines.append(
            f"{i}. {song['title']}"
        )

        if i >= 20:
            break

    await message.reply_text(
        "\n".join(lines)
    )


# ============================================================
# STREAM ENDED
# ============================================================

@call.on_update(call_filters.stream_end())
async def stream_end_handler(client, update):

    chat_id = getattr(
        update,
        "chat_id",
        None
    )

    if chat_id is None:
        return

    playing.discard(chat_id)
    current_song.pop(chat_id, None)

    if queues[chat_id]:

        success = await play_current(
            chat_id
        )

        if not success:
            print(
                f"❌ Could not play next song in {chat_id}"
            )

    else:

        try:
            await call.leave_call(
                chat_id
            )
        except Exception:
            pass


# ============================================================
# GAMES
# ============================================================

@bot.on_message(filters.group & filters.text, group=30)
async def games_handler(client, message):

    text = normalize_text(message.text)

    if text == "العاب":

        await message.reply_text(
            """
🎮 **ألعاب البوت**

🎲 نرد
🪙 عملة
🍀 حظك اليوم
🔢 تخمين رقم
⚡ أسرع واحد
❤️ نسبة الحب
😂 سؤال وجواب
🎯 هدف
🧠 لغز

اكتب اسم اللعبة لتشغيلها.
"""
        )

        return

    if text == "نرد":

        import random

        number = random.randint(1, 6)

        await message.reply_text(
            f"🎲 النرد رمى: **{number}**"
        )

        return

    if text in ("عمله", "عمله معدنيه"):

        import random

        result = random.choice(
            ["🪙 صورة", "🪙 كتابة"]
        )

        await message.reply_text(
            result
        )

        return

    if text == "حظك اليوم":

        import random

        results = [
            "🍀 حظك ممتاز النهاردة!",
            "🔥 يومك جامد!",
            "❤️ عندك خبر حلو قريب.",
            "😂 حاول تاني بكرة.",
            "👑 النهاردة يومك!",
        ]

        await message.reply_text(
            random.choice(results)
        )


# ============================================================
# WELCOME
# ============================================================

@bot.on_message(
    filters.group & filters.new_chat_members,
    group=40
)
async def welcome_handler(client, message):

    for user in message.new_chat_members:

        if user.is_bot:
            continue

        await message.reply_text(
            f"👋 أهلاً {user.mention}\n\n"
            "نورت الجروب ❤️\n"
            "اكتب الأوامر علشان تشوف أوامر البوت."
        )


# ============================================================
# SET BOT COMMANDS
# ============================================================

async def set_commands():

    try:

        await bot.set_bot_commands(
            [
                BotCommand(
                    "start",
                    "تشغيل البوت"
                ),
                BotCommand(
                    "help",
                    "مساعدة"
                ),
            ]
        )

    except Exception as e:

        print(
            f"⚠️ set commands error: {e}"
        )


# ============================================================
# MAIN
# ============================================================

async def main():

    print(
        "================================"
    )

    print(
        "MariamMusicBot starting..."
    )

    load_data()

    await bot.start()

    print(
        "✅ Bot connected."
    )

    await music_user.start()

    print(
        "✅ Music account connected."
    )

    # مهم جدًا:
    # في نسختك الحالية start() ترجع coroutine
    await maybe_await(
        call.start()
    )

    print(
        "✅ PyTgCalls started."
    )

    me = await bot.get_me()

    print(
        f"🤖 Bot: @{me.username}"
    )

    print(
        "================================"
    )

    print(
        "MariamMusicBot is ONLINE"
    )

    print(
        "================================"
    )

    await set_commands()

    try:

        await idle()

    finally:

        print(
            "🛑 Stopping..."
        )

        try:
            await maybe_await(
                call.stop()
            )
        except Exception:
            pass

        try:
            await music_user.stop()
        except Exception:
            pass

        try:
            await bot.stop()
        except Exception:
            pass


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    try:
        asyncio.run(main())

    except KeyboardInterrupt:

        print(
            "🛑 Bot stopped."
        )

    except Exception as e:

        print(
            f"❌ FATAL ERROR: {repr(e)}"
        )
