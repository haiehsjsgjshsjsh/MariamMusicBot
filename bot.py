import os
import asyncio
import inspect
import json
from collections import defaultdict, deque

import yt_dlp

# ============================================================
# إصلاح توافق PyTgCalls مع Pyrogram قبل استيراد PyTgCalls
# ============================================================

import pyrogram.errors as pyrogram_errors

if not hasattr(pyrogram_errors, "GroupcallForbidden"):

    if hasattr(pyrogram_errors, "GroupCallForbidden"):
        pyrogram_errors.GroupcallForbidden = (
            pyrogram_errors.GroupCallForbidden
        )

    else:
        class GroupcallForbidden(Exception):
            pass

        pyrogram_errors.GroupcallForbidden = GroupcallForbidden


# ============================================================
# Telegram
# ============================================================

from pyrogram import Client, filters, idle, enums
from pyrogram.types import ChatPrivileges, BotCommand

# ============================================================
# PyTgCalls
# ============================================================

from pytgcalls import PyTgCalls
from pytgcalls import filters as call_filters
from pytgcalls.types import MediaStream, AudioQuality, StreamEnded


# ============================================================
# ENV
# ============================================================

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
SESSION_STRING = os.getenv("SESSION_STRING", "")

YOUTUBE_COOKIES = os.getenv(
    "YOUTUBE_COOKIES",
    ""
).strip()


if not API_ID:
    raise RuntimeError("API_ID غير موجود")

if not API_HASH:
    raise RuntimeError("API_HASH غير موجود")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN غير موجود")

if not SESSION_STRING:
    raise RuntimeError("SESSION_STRING غير موجود")


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
    "enabled": {},
    "bad_words": {},
    "replies": {},
}

queues = defaultdict(deque)
current_song = {}
playing = set()


# ============================================================
# DATA
# ============================================================

def load_data():

    global data

    try:

        if os.path.exists(DATA_FILE):

            with open(
                DATA_FILE,
                "r",
                encoding="utf-8"
            ) as f:

                saved = json.load(f)

            if isinstance(saved, dict):
                data.update(saved)

    except Exception as e:

        print(
            "DATA LOAD ERROR:",
            repr(e)
        )


def save_data():

    try:

        with open(
            DATA_FILE,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                data,
                f,
                ensure_ascii=False,
                indent=2
            )

    except Exception as e:

        print(
            "DATA SAVE ERROR:",
            repr(e)
        )


# ============================================================
# HELPERS
# ============================================================

def norm(text):

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


async def maybe_await(value):

    if inspect.isawaitable(value):
        return await value

    return value


async def get_member(chat_id, user_id):

    try:

        return await bot.get_chat_member(
            chat_id,
            user_id
        )

    except Exception:

        return None


async def is_admin(chat_id, user_id):

    member = await get_member(
        chat_id,
        user_id
    )

    if not member:
        return False

    return member.status in (
        enums.ChatMemberStatus.OWNER,
        enums.ChatMemberStatus.ADMINISTRATOR,
    )


async def bot_can(chat_id, permission):

    try:

        me = await bot.get_me()

        member = await bot.get_chat_member(
            chat_id,
            me.id
        )

        if member.status == enums.ChatMemberStatus.OWNER:
            return True

        if member.status != enums.ChatMemberStatus.ADMINISTRATOR:
            return False

        privileges = member.privileges

        if not privileges:
            return False

        return bool(
            getattr(
                privileges,
                permission,
                False
            )
        )

    except Exception:

        return False


async def target_user(message):

    # Reply
    if message.reply_to_message:

        if message.reply_to_message.from_user:

            return message.reply_to_message.from_user

    # Username / ID
    parts = (
        message.text or ""
    ).split(
        maxsplit=1
    )

    if len(parts) < 2:
        return None

    target = parts[1].strip()

    try:

        if target.startswith("@"):
            return await bot.get_users(target)

        if target.lstrip("-").isdigit():
            return await bot.get_users(
                int(target)
            )

    except Exception:

        return None

    return None


# ============================================================
# START
# ============================================================

@bot.on_message(
    filters.private & filters.command("start")
)
async def start_handler(_, message):

    await message.reply_text(
        "👋 أهلاً بيك في MariamMusicBot\n\n"
        "ضيف البوت للجروب وخليه مشرف.\n\n"
        "اكتب:\n"
        "الأوامر\n\n"
        "لعرض كل أوامر البوت."
    )


# ============================================================
# الأوامر
# ============================================================

HELP = """
╔════════════════════╗
     🎀 MariamMusicBot
╚════════════════════╝

🎵 الموسيقى:

• تشغيل اسم الأغنية
• تخطي
• إيقاف
• الأغنية
• الطابور


👑 الإدارة:

• ترقية
• تنزيل رتبة
• طرد


⚙️ البوت:

• تفعيل البوت
• تعطيل البوت
• حالة البوت


🛡 الحماية:

• منع السب
• السماح بالسب


💬 الردود:

• اضف رد الكلمة الرد
• مسح الرد الكلمة


🎮 الألعاب:

• العاب
• نرد
• عملة
• حظك اليوم


📋 عرض الأوامر:

• الأوامر
"""


@bot.on_message(
    filters.group & filters.text,
    group=1
)
async def commands_handler(_, message):

    text = norm(message.text)

    if text in (
        "الاوامر",
        "/الاوامر",
        "اوامر",
        "اوامر البوت"
    ):

        await message.reply_text(
            HELP
        )


# ============================================================
# تفعيل
# ============================================================

@bot.on_message(
    filters.group & filters.text,
    group=2
)
async def enable_handler(_, message):

    if norm(message.text) not in (
        "تفعيل",
        "تفعيل البوت"
    ):
        return

    if not await is_admin(
        message.chat.id,
        message.from_user.id
    ):

        await message.reply_text(
            "❌ الأمر للمشرفين فقط."
        )

        return

    data["enabled"][
        str(message.chat.id)
    ] = True

    save_data()

    await message.reply_text(
        "✅ تم تفعيل البوت.\n\n"
        "🎵 استخدم:\n"
        "تشغيل + اسم الأغنية"
    )


# ============================================================
# تعطيل
# ============================================================

@bot.on_message(
    filters.group & filters.text,
    group=3
)
async def disable_handler(_, message):

    if norm(message.text) not in (
        "تعطيل",
        "تعطيل البوت"
    ):
        return

    if not await is_admin(
        message.chat.id,
        message.from_user.id
    ):

        await message.reply_text(
            "❌ الأمر للمشرفين فقط."
        )

        return

    data["enabled"][
        str(message.chat.id)
    ] = False

    save_data()

    queues[
        message.chat.id
    ].clear()

    playing.discard(
        message.chat.id
    )

    current_song.pop(
        message.chat.id,
        None
    )

    try:
        await call.leave_call(
            message.chat.id
        )
    except Exception:
        pass

    await message.reply_text(
        "🛑 تم تعطيل البوت."
    )


# ============================================================
# حالة البوت
# ============================================================

@bot.on_message(
    filters.group & filters.text,
    group=4
)
async def status_handler(_, message):

    if norm(message.text) != "حالة البوت":
        return

    enabled = data["enabled"].get(
        str(message.chat.id),
        False
    )

    await message.reply_text(
        "🤖 حالة البوت:\n\n"
        f"⚙️ التفعيل: "
        f"{'✅' if enabled else '❌'}\n"
        f"🎵 التشغيل: "
        f"{'✅' if message.chat.id in playing else '❌'}"
    )


# ============================================================
# ترقية
# ============================================================

@bot.on_message(
    filters.group & filters.text,
    group=5
)
async def promote_handler(_, message):

    text = norm(message.text)

    if not (
        text == "ترقية"
        or text.startswith("ترقيه ")
        or text.startswith("ترقية ")
    ):
        return

    if not await is_admin(
        message.chat.id,
        message.from_user.id
    ):

        await message.reply_text(
            "❌ الأمر للمشرفين فقط."
        )

        return

    if not await bot_can(
        message.chat.id,
        "can_promote_members"
    ):

        await message.reply_text(
            "❌ البوت مش معاه صلاحية "
            "إضافة مشرفين.\n\n"
            "خلي البوت مشرف وفعل له "
            "صلاحية إضافة مشرفين."
        )

        return

    target = await target_user(
        message
    )

    if not target:

        await message.reply_text(
            "❌ اعمل Reply على الشخص "
            "واكتب:\n\n"
            "ترقية"
        )

        return

    try:

        member = await bot.get_chat_member(
            message.chat.id,
            target.id
        )

        if member.status == enums.ChatMemberStatus.OWNER:

            await message.reply_text(
                "❌ ده مالك الجروب."
            )

            return

        privileges = ChatPrivileges(
            can_manage_chat=True,
            can_delete_messages=True,
            can_manage_video_chats=True,
            can_restrict_members=True,
            can_invite_users=True,
            can_pin_messages=True,
            can_change_info=True,
            can_promote_members=False,
            is_anonymous=False,
        )

        await bot.promote_chat_member(
            message.chat.id,
            target.id,
            privileges=privileges
        )

        await message.reply_text(
            f"👑 تم ترقية "
            f"{target.mention} "
            f"إلى مشرف بنجاح."
        )

    except Exception as e:

        print(
            "PROMOTE ERROR:",
            repr(e)
        )

        await message.reply_text(
            "❌ فشلت الترقية.\n\n"
            "تأكد أن البوت مشرف ومعاه "
            "صلاحية إضافة مشرفين."
        )


# ============================================================
# تنزيل رتبة
# ============================================================

@bot.on_message(
    filters.group & filters.text,
    group=6
)
async def demote_handler(_, message):

    text = norm(message.text)

    if text not in (
        "تنزيل",
        "تنزيل رتبه",
        "تنزيل رتبة"
    ):
        return

    if not await is_admin(
        message.chat.id,
        message.from_user.id
    ):

        await message.reply_text(
            "❌ الأمر للمشرفين فقط."
        )

        return

    if not await bot_can(
        message.chat.id,
        "can_promote_members"
    ):

        await message.reply_text(
            "❌ البوت محتاج صلاحية "
            "تعديل المشرفين."
        )

        return

    target = await target_user(
        message
    )

    if not target:

        await message.reply_text(
            "❌ اعمل Reply على المشرف "
            "واكتب:\n\n"
            "تنزيل رتبة"
        )

        return

    try:

        member = await bot.get_chat_member(
            message.chat.id,
            target.id
        )

        if member.status == enums.ChatMemberStatus.OWNER:

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
            privileges=privileges
        )

        await message.reply_text(
            f"✅ تم تنزيل رتبة "
            f"{target.mention}."
        )

    except Exception as e:

        print(
            "DEMOTE ERROR:",
            repr(e)
        )

        await message.reply_text(
            "❌ فشل تنزيل الرتبة."
        )


# ============================================================
# طرد
# ============================================================

@bot.on_message(
    filters.group & filters.text,
    group=7
)
async def kick_handler(_, message):

    if norm(message.text) not in (
        "طرد",
        "اطرد"
    ):
        return

    if not await is_admin(
        message.chat.id,
        message.from_user.id
    ):

        await message.reply_text(
            "❌ الأمر للمشرفين فقط."
        )

        return

    if not await bot_can(
        message.chat.id,
        "can_restrict_members"
    ):

        await message.reply_text(
            "❌ البوت محتاج صلاحية "
            "حظر الأعضاء."
        )

        return

    target = await target_user(
        message
    )

    if not target:

        await message.reply_text(
            "❌ اعمل Reply على الشخص "
            "واكتب طرد."
        )

        return

    try:

        member = await bot.get_chat_member(
            message.chat.id,
            target.id
        )

        if member.status in (
            enums.ChatMemberStatus.OWNER,
            enums.ChatMemberStatus.ADMINISTRATOR
        ):

            await message.reply_text(
                "❌ مينفعش أطرد مشرف "
                "أو مالك."
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
            f"🚫 تم طرد "
            f"{target.mention}."
        )

    except Exception as e:

        print(
            "KICK ERROR:",
            repr(e)
        )

        await message.reply_text(
            "❌ فشل الطرد."
        )


# ============================================================
# منع السب
# ============================================================

BAD_WORDS = {
    "كس",
    "شرموط",
    "شرموطه",
    "خول",
    "متناك",
    "نيك",
    "زب",
    "وسخ"
}


@bot.on_message(
    filters.group & filters.text,
    group=8
)
async def bad_words_handler(_, message):

    if not data["bad_words"].get(
        str(message.chat.id),
        False
    ):
        return

    if await is_admin(
        message.chat.id,
        message.from_user.id
    ):
        return

    text = norm(message.text)

    for word in BAD_WORDS:

        if word in text:

            try:

                await message.delete()

                await message.reply_text(
                    f"⚠️ ممنوع السب يا "
                    f"{message.from_user.mention}"
                )

            except Exception:
                pass

            return


@bot.on_message(
    filters.group & filters.text,
    group=9
)
async def bad_on(_, message):

    if norm(message.text) != "منع السب":
        return

    if not await is_admin(
        message.chat.id,
        message.from_user.id
    ):
        return

    data["bad_words"][
        str(message.chat.id)
    ] = True

    save_data()

    await message.reply_text(
        "🛡️ تم تفعيل منع السب."
    )


@bot.on_message(
    filters.group & filters.text,
    group=10
)
async def bad_off(_, message):

    if norm(message.text) != "السماح بالسب":
        return

    if not await is_admin(
        message.chat.id,
        message.from_user.id
    ):
        return

    data["bad_words"][
        str(message.chat.id)
    ] = False

    save_data()

    await message.reply_text(
        "✅ تم إيقاف منع السب."
    )


# ============================================================
# الردود
# ============================================================

@bot.on_message(
    filters.group & filters.text,
    group=11
)
async def add_reply(_, message):

    text = message.text or ""

    if not norm(text).startswith(
        "اضف رد "
    ):
        return

    parts = text.split(
        maxsplit=2
    )

    if len(parts) < 3:

        await message.reply_text(
            "❌ الصيغة:\n"
            "اضف رد الكلمة الرد"
        )

        return

    keyword = norm(
        parts[1]
    )

    reply = parts[2]

    chat = str(
        message.chat.id
    )

    if chat not in data["replies"]:
        data["replies"][chat] = {}

    data["replies"][chat][keyword] = reply

    save_data()

    await message.reply_text(
        "✅ تم إضافة الرد."
    )


@bot.on_message(
    filters.group & filters.text,
    group=12
)
async def delete_reply(_, message):

    text = message.text or ""

    if not norm(text).startswith(
        "مسح الرد "
    ):
        return

    parts = text.split(
        maxsplit=2
    )

    if len(parts) < 3:
        return

    keyword = norm(
        parts[2]
    )

    chat = str(
        message.chat.id
    )

    replies = data["replies"].get(
        chat,
        {}
    )

    if keyword not in replies:

        await message.reply_text(
            "❌ الرد غير موجود."
        )

        return

    del replies[keyword]

    save_data()

    await message.reply_text(
        "✅ تم حذف الرد."
    )


@bot.on_message(
    filters.group & filters.text,
    group=13
)
async def custom_reply(_, message):

    text = norm(
        message.text
    )

    chat = str(
        message.chat.id
    )

    replies = data["replies"].get(
        chat,
        {}
    )

    if text in replies:

        await message.reply_text(
            replies[text]
        )


# ============================================================
# YOUTUBE
# ============================================================

def youtube_search(query):

    options = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "extract_flat": True,
        "noplaylist": True,
    }

    if YOUTUBE_COOKIES:

        options["cookiefile"] = (
            YOUTUBE_COOKIES
        )

    with yt_dlp.YoutubeDL(
        options
    ) as ydl:

        result = ydl.extract_info(
            "ytsearch1:" + query,
            download=False
        )

    entries = result.get(
        "entries"
    ) or []

    if not entries:
        return None

    return entries[0]


# ============================================================
# AUDIO
# ============================================================

def get_audio(video_url):

    options = {
        "quiet": True,
        "no_warnings": True,
        "format": "bestaudio/best",
        "noplaylist": True,
    }

    if YOUTUBE_COOKIES:

        options["cookiefile"] = (
            YOUTUBE_COOKIES
        )

    with yt_dlp.YoutubeDL(
        options
    ) as ydl:

        info = ydl.extract_info(
            video_url,
            download=False
        )

    return info


# ============================================================
# PLAY
# ============================================================

async def play_next(chat_id):

    if not queues[chat_id]:

        playing.discard(
            chat_id
        )

        current_song.pop(
            chat_id,
            None
        )

        return False

    song = queues[chat_id].popleft()

    try:

        info = await asyncio.to_thread(
            get_audio,
            song["url"]
        )

        audio_url = info.get(
            "url"
        )

        if not audio_url:

            raise RuntimeError(
                "Audio URL not found"
            )

        current_song[chat_id] = {
            "title": info.get(
                "title",
                song["title"]
            ),
            "url": song["url"]
        }

        stream = MediaStream(
            audio_url,
            AudioQuality.HIGH
        )

        await call.play(
            chat_id,
            stream
        )

        playing.add(
            chat_id
        )

        return True

    except Exception as e:

        print(
            "PLAY ERROR:",
            repr(e)
        )

        current_song.pop(
            chat_id,
            None
        )

        playing.discard(
            chat_id
        )

        return False


# ============================================================
# تشغيل
# ============================================================

@bot.on_message(
    filters.group & filters.text,
    group=20
)
async def play_handler(_, message):

    text = message.text or ""

    if not norm(text).startswith(
        "تشغيل"
    ):
        return

    if not data["enabled"].get(
        str(message.chat.id),
        False
    ):

        await message.reply_text(
            "⚠️ البوت غير مفعل.\n\n"
            "اكتب:\n"
            "تفعيل البوت"
        )

        return

    parts = text.split(
        maxsplit=1
    )

    if len(parts) < 2:

        await message.reply_text(
            "🎵 اكتب اسم الأغنية بعد تشغيل."
        )

        return

    query = parts[1].strip()

    wait = await message.reply_text(
        "🔎 جاري البحث..."
    )

    try:

        result = await asyncio.to_thread(
            youtube_search,
            query
        )

        if not result:

            await wait.edit_text(
                "❌ لم أجد الأغنية."
            )

            return

        url = result.get(
            "webpage_url"
        )

        if not url and result.get("id"):

            url = (
                "https://www.youtube.com/watch?v="
                + result["id"]
            )

        song = {
            "title": result.get(
                "title",
                query
            ),
            "url": url
        }

        queues[
            message.chat.id
        ].append(song)

        if message.chat.id in playing:

            await wait.edit_text(
                "➕ تمت إضافة الأغنية للطابور:\n\n"
                + song["title"]
            )

            return

        await wait.edit_text(
            "⏳ جاري التشغيل..."
        )

        success = await play_next(
            message.chat.id
        )

        if success:

            await wait.edit_text(
                "🎵 يتم التشغيل الآن:\n\n"
                + current_song[
                    message.chat.id
                ]["title"]
            )

        else:

            await wait.edit_text(
                "❌ فشل تشغيل الأغنية.\n\n"
                "لو ظهر في اللوج:\n"
                "Sign in to confirm you're not a bot\n"
                "فالمشكلة من حماية YouTube."
            )

    except Exception as e:

        print(
            "SEARCH ERROR:",
            repr(e)
        )

        await wait.edit_text(
            "❌ حصل خطأ أثناء البحث."
        )


# ============================================================
# تخطي
# ============================================================

@bot.on_message(
    filters.group & filters.text,
    group=21
)
async def skip_handler(_, message):

    if norm(message.text) != "تخطي":
        return

    if not await is_admin(
        message.chat.id,
        message.from_user.id
    ):
        return

    try:

        await call.leave_call(
            message.chat.id
        )

    except Exception:
        pass

    playing.discard(
        message.chat.id
    )

    current_song.pop(
        message.chat.id,
        None
    )

    success = await play_next(
        message.chat.id
    )

    if success:

        await message.reply_text(
            "⏭️ تم التخطي.\n\n"
            "🎵 "
            + current_song[
                message.chat.id
            ]["title"]
        )

    else:

        await message.reply_text(
            "⏭️ تم التخطي.\n"
            "📭 الطابور فاضي."
        )


# ============================================================
# إيقاف
# ============================================================

@bot.on_message(
    filters.group & filters.text,
    group=22
)
async def stop_handler(_, message):

    if norm(message.text) not in (
        "ايقاف",
        "وقف",
        "وقف التشغيل"
    ):
        return

    if not await is_admin(
        message.chat.id,
        message.from_user.id
    ):
        return

    try:

        await call.leave_call(
            message.chat.id
        )

    except Exception:
        pass

    queues[
        message.chat.id
    ].clear()

    playing.discard(
        message.chat.id
    )

    current_song.pop(
        message.chat.id,
        None
    )

    await message.reply_text(
        "⏹️ تم إيقاف التشغيل."
    )


# ============================================================
# الأغنية الحالية
# ============================================================

@bot.on_message(
    filters.group & filters.text,
    group=23
)
async def current_handler(_, message):

    if norm(message.text) not in (
        "الاغنيه",
        "الاغنية"
    ):
        return

    song = current_song.get(
        message.chat.id
    )

    if not song:

        await message.reply_text(
            "🎵 لا توجد أغنية تعمل الآن."
        )

        return

    await message.reply_text(
        "🎵 الأغنية الحالية:\n\n"
        + song["title"]
    )


# ============================================================
# الطابور
# ============================================================

@bot.on_message(
    filters.group & filters.text,
    group=24
)
async def queue_handler(_, message):

    if norm(message.text) != "الطابور":
        return

    q = queues[
        message.chat.id
    ]

    if not q:

        await message.reply_text(
            "📭 الطابور فاضي."
        )

        return

    result = [
        "📋 الطابور:"
    ]

    for i, song in enumerate(
        q,
        1
    ):

        result.append(
            f"{i}. {song['title']}"
        )

        if i >= 20:
            break

    await message.reply_text(
        "\n".join(result)
    )


# ============================================================
# انتهاء الأغنية
# ============================================================

@call.on_update(
    call_filters.stream_end()
)
async def stream_end_handler(
    _,
    update: StreamEnded
):

    chat_id = update.chat_id

    playing.discard(
        chat_id
    )

    current_song.pop(
        chat_id,
        None
    )

    if queues[chat_id]:

        await play_next(
            chat_id
        )

    else:

        try:

            await call.leave_call(
                chat_id
            )

        except Exception:
            pass


# ============================================================
# الألعاب
# ============================================================

@bot.on_message(
    filters.group & filters.text,
    group=30
)
async def games_handler(_, message):

    text = norm(
        message.text
    )

    if text == "العاب":

        await message.reply_text(
            """
🎮 ألعاب البوت

🎲 نرد
🪙 عملة
🍀 حظك اليوم
❤️ نسبة الحب
🎯 هدف
🧠 لغز
"""
        )

        return

    if text == "نرد":

        import random

        await message.reply_text(
            "🎲 النتيجة: "
            + str(
                random.randint(
                    1,
                    6
                )
            )
        )

        return

    if text in (
        "عمله",
        "عمله معدنيه"
    ):

        import random

        await message.reply_text(
            random.choice(
                [
                    "🪙 صورة",
                    "🪙 كتابة"
                ]
            )
        )

        return

    if text == "حظك اليوم":

        import random

        await message.reply_text(
            random.choice(
                [
                    "🍀 حظك ممتاز!",
                    "❤️ يوم جميل!",
                    "🔥 يومك قوي!",
                    "👑 النهاردة يومك!",
                    "😂 جرب بكرة!"
                ]
            )
        )


# ============================================================
# WELCOME
# ============================================================

@bot.on_message(
    filters.group & filters.new_chat_members
)
async def welcome_handler(_, message):

    for user in message.new_chat_members:

        if user.is_bot:
            continue

        await message.reply_text(
            f"👋 أهلاً {user.mention}\n"
            "نورت الجروب ❤️"
        )


# ============================================================
# BOT COMMANDS
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
                    "المساعدة"
                )
            ]
        )

    except Exception as e:

        print(
            "COMMAND ERROR:",
            repr(e)
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

        asyncio.run(
            main()
        )

    except KeyboardInterrupt:

        print(
            "🛑 Stopped."
        )

    except Exception as e:

        print(
            "❌ FATAL ERROR:",
            repr(e)
        )
