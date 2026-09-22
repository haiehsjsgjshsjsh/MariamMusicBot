import os
import re
import json
import time
import random
import asyncio
import subprocess
from pathlib import Path
from collections import defaultdict, deque

import static_ffmpeg
static_ffmpeg.add_paths()

import yt_dlp

from pyrogram import Client, filters, enums
from pyrogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ChatPermissions,
    ChatPrivileges,
)

from pytgcalls import PyTgCalls
from pytgcalls.types import MediaStream


# =========================================================
# إعدادات Railway
# =========================================================

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]
SESSION_STRING = os.environ["SESSION_STRING"]

# اسم الصورة الموجودة في GitHub
PHOTO_PATH = "IMG_20260922_130735_050.jpg"


# =========================================================
# الملفات
# =========================================================

DATA_DIR = Path("data")
MUSIC_DIR = Path("music_cache")

DATA_DIR.mkdir(exist_ok=True)
MUSIC_DIR.mkdir(exist_ok=True)

CUSTOM_FILE = DATA_DIR / "custom_replies.json"
SETTINGS_FILE = DATA_DIR / "group_settings.json"
WARN_FILE = DATA_DIR / "warnings.json"


# =========================================================
# قراءة وحفظ JSON
# =========================================================

def load_json(path, default):
    try:
        if path.exists():
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass

    return default


def save_json(path, data):
    temp = path.with_suffix(".tmp")

    with temp.open("w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )

    temp.replace(path)


custom_replies = load_json(CUSTOM_FILE, {})
group_settings = load_json(SETTINGS_FILE, {})
warnings = load_json(WARN_FILE, {})


# =========================================================
# Telegram Clients
# =========================================================

bot = Client(
    "MariamMusicBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
)

assistant = Client(
    "MariamMusicAssistant",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING,
)

# مهم جداً:
# لا ننشئ PyTgCalls هنا
# لأنه كان سبب مشكلة different loop
calls = None


# =========================================================
# الذاكرة
# =========================================================

queues = defaultdict(deque)
current_song = {}

waiting_song = set()

download_locks = defaultdict(asyncio.Lock)

last_now_playing = {}


# =========================================================
# إعدادات الحماية
# =========================================================

DEFAULT_SETTINGS = {
    "enabled": True,

    "links": False,
    "photos": False,
    "videos": False,
    "stickers": False,
    "voice": False,

    "bad_words": True,
}


# ضع الكلمات التي تريد منعها هنا
BAD_WORDS = {
    "كلمة_ممنوعة_1",
    "كلمة_ممنوعة_2",
}


# =========================================================
# إعدادات المجموعة
# =========================================================

def settings_for(chat_id):

    key = str(chat_id)

    if key not in group_settings:

        group_settings[key] = DEFAULT_SETTINGS.copy()

        save_json(
            SETTINGS_FILE,
            group_settings
        )

    else:

        changed = False

        for k, v in DEFAULT_SETTINGS.items():

            if k not in group_settings[key]:

                group_settings[key][k] = v
                changed = True

        if changed:
            save_json(
                SETTINGS_FILE,
                group_settings
            )

    return group_settings[key]


# =========================================================
# هل مجموعة؟
# =========================================================

def is_group(message):

    if not message.chat:
        return False

    return message.chat.type in (
        enums.ChatType.GROUP,
        enums.ChatType.SUPERGROUP,
    )


# =========================================================
# الرتب
# =========================================================

async def get_status(chat_id, user_id):

    try:

        member = await bot.get_chat_member(
            chat_id,
            user_id
        )

        status = str(member.status).lower()

        return status, member

    except Exception:

        return "", None


async def is_admin(chat_id, user_id):

    status, _ = await get_status(
        chat_id,
        user_id
    )

    return status in (
        "owner",
        "creator",
        "administrator",
        "admin",
    )


async def is_owner(chat_id, user_id):

    status, _ = await get_status(
        chat_id,
        user_id
    )

    return status in (
        "owner",
        "creator",
    )


# =========================================================
# التأكد أن الأمر للمشرف
# =========================================================

async def require_admin(message):

    if not is_group(message):
        return False

    if not message.from_user:

        await message.reply_text(
            "❌ مش قادر أحدد المستخدم."
        )

        return False

    if not await is_admin(
        message.chat.id,
        message.from_user.id
    ):

        await message.reply_text(
            "❌ الأمر ده للمشرفين فقط."
        )

        return False

    return True


# =========================================================
# البوت متفعل؟
# =========================================================

async def ensure_enabled(message):

    if not is_group(message):
        return True

    return settings_for(
        message.chat.id
    )["enabled"]


# =========================================================
# حذف آمن
# =========================================================

async def safe_delete(message):

    try:
        await message.delete()
    except Exception:
        pass


# =========================================================
# تحديد الشخص بالـ Reply
# =========================================================

async def target_user(message):

    if (
        message.reply_to_message
        and message.reply_to_message.from_user
    ):

        return message.reply_to_message.from_user


    text = (
        message.text or ""
    ).strip()

    parts = text.split(
        maxsplit=1
    )

    if len(parts) < 2:
        return None


    raw = parts[1].strip()

    raw = raw.split()[0]


    # ID
    if raw.isdigit():

        try:

            return await bot.get_users(
                int(raw)
            )

        except Exception:

            return None


    # username
    if raw.startswith("@"):

        try:

            return await bot.get_users(
                raw
            )

        except Exception:

            return None


    return None


# =========================================================
# إنشاء Voice Chat
# =========================================================

async def make_voice_chat(chat_id):

    try:

        from pyrogram.raw.functions.phone import CreateGroupCall

        peer = await assistant.resolve_peer(
            chat_id
        )

        result = await assistant.invoke(

            CreateGroupCall(

                peer=peer,

                random_id=random.randint(
                    1,
                    2_000_000_000
                ),

                title="Mariam Music",
            )
        )

        return result

    except Exception:

        # ممكن يكون Voice Chat موجود بالفعل
        return None


# =========================================================
# تنظيف اسم الملف
# =========================================================

def clean_filename(text):

    text = re.sub(
        r"[^\w\u0600-\u06FF -]+",
        "",
        text
    )

    text = text.strip()

    if not text:
        text = "song"

    return text[:70]


# =========================================================
# تحميل الأغنية
# =========================================================

async def search_and_download(query):

    safe = clean_filename(
        query
    )

    stamp = str(
        abs(hash(query))
    )[:12]

    output_base = (
        MUSIC_DIR
        / f"{stamp}_{safe}"
    )


    # موجودة قبل كده؟
    existing = list(
        MUSIC_DIR.glob(
            f"{stamp}_{safe}.*"
        )
    )

    if existing:
        return str(
            existing[0]
        )


    sources = [

        # SoundCloud أولاً
        {
            "source": f"scsearch1:{query}",
            "extractor_args": {},
        },

        # YouTube
        {
            "source": f"ytsearch1:{query}",
            "extractor_args": {
                "youtube": {
                    "player_client": [
                        "android"
                    ]
                }
            },
        },

    ]


    async with download_locks[query]:

        existing = list(
            MUSIC_DIR.glob(
                f"{stamp}_{safe}.*"
            )
        )

        if existing:
            return str(
                existing[0]
            )


        last_error = None


        for item in sources:

            options = {

                "format":
                    "bestaudio/best",

                "outtmpl":
                    str(output_base)
                    + ".%(ext)s",

                "noplaylist":
                    True,

                "quiet":
                    True,

                "no_warnings":
                    True,

                "overwrites":
                    False,

                "socket_timeout":
                    30,

                "retries":
                    2,

                "fragment_retries":
                    2,

                "extractor_args":
                    item["extractor_args"],
            }


            try:

                def download():

                    with yt_dlp.YoutubeDL(
                        options
                    ) as ydl:

                        return ydl.extract_info(
                            item["source"],
                            download=True
                        )


                info = await asyncio.to_thread(
                    download
                )


                if info:

                    path = (
                        Path(
                            options["outtmpl"]
                            .replace(
                                "%(ext)s",
                                info.get(
                                    "ext",
                                    "mp3"
                                )
                            )
                        )
                    )

                    if path.exists():

                        return str(path)


                found = list(
                    MUSIC_DIR.glob(
                        f"{stamp}_{safe}.*"
                    )
                )

                if found:

                    return str(
                        found[0]
                    )


            except Exception as e:

                last_error = e


    raise RuntimeError(
        "مش قادر أحمل الأغنية حالياً."
    )


# =========================================================
# مدة الأغنية
# =========================================================

def song_duration(path):

    try:

        result = subprocess.run(

            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                path,
            ],

            capture_output=True,

            text=True,

            timeout=15,
        )


        value = float(
            result.stdout.strip()
        )

        return int(value)


    except Exception:

        return 0


# =========================================================
# تنسيق المدة
# =========================================================

def fmt_duration(seconds):

    if not seconds:
        return "غير معروف"


    seconds = int(seconds)

    minutes, sec = divmod(
        seconds,
        60
    )

    hours, minutes = divmod(
        minutes,
        60
    )


    if hours:

        return (
            f"{hours}:"
            f"{minutes:02d}:"
            f"{sec:02d}"
        )


    return (
        f"{minutes}:"
        f"{sec:02d}"
    )


# =========================================================
# رسالة الأغنية
# =========================================================

async def send_now_playing(
    message,
    song
):

    chat_id = message.chat.id


    text = (

        "🎶 **مريومه الدلوعه**\n\n"

        f"🎵 **الأغنية:** "
        f"{song['title']}\n"

        f"⏱ **المدة:** "
        f"{fmt_duration(song.get('duration', 0))}\n"

        f"👤 **الطلب:** "
        f"{song.get('requester', 'غير معروف')}"
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
                ),

            ],

        ]
    )


    try:

        if os.path.exists(
            PHOTO_PATH
        ):

            sent = await bot.send_photo(

                chat_id,

                PHOTO_PATH,

                caption=text,

                reply_markup=keyboard,
            )

        else:

            sent = await bot.send_message(

                chat_id,

                text,

                reply_markup=keyboard,
            )


        last_now_playing[
            chat_id
        ] = sent.id


    except Exception:

        pass


# =========================================================
# تشغيل الأغنية التالية
# =========================================================

async def play_next(chat_id):

    if not queues[chat_id]:

        current_song.pop(
            chat_id,
            None
        )

        return


    song = queues[
        chat_id
    ].popleft()


    current_song[
        chat_id
    ] = song


    try:

        # لو مفيش Voice Chat نحاول نعمل واحد
        await make_voice_chat(
            chat_id
        )

        await asyncio.sleep(
            1
        )


        # تشغيل الصوت
        await calls.play(

            chat_id,

            MediaStream(

                song["path"],

                video_flags=
                MediaStream.Flags.IGNORE,
            ),
        )


        await send_now_playing(
            song["message"],
            song
        )


    except Exception as e:

        current_song.pop(
            chat_id,
            None
        )


        try:

            await song[
                "message"
            ].reply_text(

                "❌ حصل خطأ في تشغيل الأغنية:\n\n"
                f"`{str(e)[:700]}`"

            )

        except Exception:

            pass


        # جرب الأغنية التالية
        if queues[chat_id]:

            await play_next(
                chat_id
            )


# =========================================================
# إضافة أغنية للقائمة
# =========================================================

async def queue_song(
    message,
    query
):

    if not await ensure_enabled(
        message
    ):

        await message.reply_text(
            "⛔ البوت متعطل في المجموعة."
        )

        return


    searching = await message.reply_text(

        f"🔎 بدور على:\n"
        f"**{query}**"
    )


    try:

        path = await search_and_download(
            query
        )


        duration = song_duration(
            path
        )


        if message.from_user:

            requester = (
                message.from_user.mention
            )

        else:

            requester = "غير معروف"


        song = {

            "title":
                query,

            "path":
                path,

            "duration":
                duration,

            "requester":
                requester,

            "message":
                message,
        }


        chat_id = message.chat.id


        was_empty = (

            not queues[chat_id]

            and chat_id
            not in current_song
        )


        queues[
            chat_id
        ].append(song)


        try:
            await searching.delete()
        except Exception:
            pass


        if was_empty:

            await play_next(
                chat_id
            )

        else:

            await message.reply_text(

                "✅ اتضافت للقائمة.\n\n"

                f"🎵 **{query}**\n"

                f"📌 الترتيب: "
                f"{len(queues[chat_id])}"

            )


    except Exception as e:

        try:
            await searching.delete()
        except Exception:
            pass


        await message.reply_text(

            "❌ مش قادر أشغل الأغنية.\n\n"

            f"{str(e)[:600]}"

        )


# =========================================================
# إيقاف الميوزك
# =========================================================

async def stop_music(chat_id):

    try:

        await calls.leave_call(
            chat_id
        )

    except Exception:

        pass


    queues[
        chat_id
    ].clear()


    current_song.pop(
        chat_id,
        None
    )


# =========================================================
# تشغيل الميوزك
# =========================================================

@bot.on_message(
    filters.group & filters.text,
    group=1
)
async def music_commands(
    _,
    message
):

    if not message.text:
        return


    if not await ensure_enabled(
        message
    ):
        return


    text = message.text.strip()


    # ---------------------------------
    # تشغيل
    # ---------------------------------

    if text == "تشغيل":

        waiting_song.add(
            message.chat.id
        )

        await message.reply_text(
            "🎵 قول اسم الأغنية"
        )

        return


    # ---------------------------------
    # تشغيل اسم الأغنية
    # ---------------------------------

    if text.startswith(
        "تشغيل "
    ):

        query = text[
            7:
        ].strip()


        if query:

            await queue_song(
                message,
                query
            )

        return


    # ---------------------------------
    # تخطي
    # ---------------------------------

    if text in (
        "تخطي",
        "التالي"
    ):

        if not await is_admin(
            message.chat.id,
            message.from_user.id
        ):

            await message.reply_text(
                "❌ تخطي الأغاني للمشرفين."
            )

            return


        try:

            await calls.leave_call(
                message.chat.id
            )

        except Exception:

            pass


        current_song.pop(
            message.chat.id,
            None
        )


        if queues[
            message.chat.id
        ]:

            await play_next(
                message.chat.id
            )

        else:

            await message.reply_text(
                "📭 مفيش أغاني تانية."
            )

        return


    # ---------------------------------
    # وقف
    # ---------------------------------

    if text in (
        "وقف",
        "إيقاف"
    ):

        if not await is_admin(
            message.chat.id,
            message.from_user.id
        ):

            await message.reply_text(
                "❌ وقف الأغاني للمشرفين."
            )

            return


        await stop_music(
            message.chat.id
        )


        await message.reply_text(
            "⏹ تم إيقاف التشغيل."
        )

        return


    # ---------------------------------
    # القائمة
    # ---------------------------------

    if text == "القائمة":

        q = queues[
            message.chat.id
        ]

        now = current_song.get(
            message.chat.id
        )


        lines = [
            "🎵 **قائمة التشغيل**"
        ]


        if now:

            lines.append(
                f"▶️ الآن: **{now['title']}**"
            )


        if q:

            for i, song in enumerate(
                q,
                1
            ):

                lines.append(
                    f"{i}. {song['title']}"
                )

        elif not now:

            lines.append(
                "📭 القائمة فاضية."
            )


        await message.reply_text(
            "\n".join(lines)
        )


# =========================================================
# اسم الأغنية بعد تشغيل
# =========================================================

@bot.on_message(
    filters.group & filters.text,
    group=2
)
async def waiting_handler(
    _,
    message
):

    chat_id = message.chat.id


    if chat_id not in waiting_song:
        return


    text = message.text.strip()


    if text in (
        "تشغيل",
        "وقف",
        "إيقاف",
        "تخطي",
        "التالي",
        "القائمة",
    ):

        return


    waiting_song.discard(
        chat_id
    )


    await queue_song(
        message,
        text
    )


# =========================================================
# أزرار الميوزك
# =========================================================

@bot.on_callback_query()
async def music_buttons(
    _,
    query
):

    try:

        await query.answer()

    except Exception:

        pass


    chat_id = (
        query.message.chat.id
    )


    # تخطي
    if query.data == "music_skip":

        try:

            await calls.leave_call(
                chat_id
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

            await query.message.reply_text(
                "📭 مفيش أغاني تانية."
            )


    # وقف
    elif query.data == "music_stop":

        await stop_music(
            chat_id
        )


        await query.message.reply_text(
            "⏹ تم إيقاف التشغيل."
        )


    # القائمة
    elif query.data == "music_queue":

        q = queues[
            chat_id
        ]

        now = current_song.get(
            chat_id
        )


        lines = [
            "🎵 **القائمة**"
        ]


        if now:

            lines.append(
                f"▶️ الآن: {now['title']}"
            )


        for i, song in enumerate(
            q,
            1
        ):

            lines.append(
                f"{i}. {song['title']}"
            )


        if not now and not q:

            lines.append(
                "📭 القائمة فاضية."
            )


        await query.message.reply_text(
            "\n".join(lines)
        )


# =========================================================
# تفعيل / تعطيل
# =========================================================

@bot.on_message(
    filters.group & filters.text,
    group=3
)
async def activation(
    _,
    message
):

    text = message.text.strip()


    if text not in (
        "تفعيل البوت",
        "تعطيل البوت",
    ):

        return


    if not await require_admin(
        message
    ):

        return


    enabled = (
        text == "تفعيل البوت"
    )


    settings = settings_for(
        message.chat.id
    )


    settings["enabled"] = enabled


    save_json(
        SETTINGS_FILE,
        group_settings
    )


    if enabled:

        await message.reply_text(
            "✅ تم تفعيل البوت."
        )

    else:

        await message.reply_text(
            "⛔ تم تعطيل البوت."
        )


# =========================================================
# إضافة الردود
# =========================================================

@bot.on_message(
    filters.group & filters.text,
    group=4
)
async def custom_reply_commands(
    _,
    message
):

    text = message.text.strip()


    # ---------------------------------
    # إضافة رد
    # ---------------------------------

    if text.startswith(
        "اضف رد "
    ):

        if not await require_admin(
            message
        ):

            return


        body = text[
            7:
        ].strip()


        if "=" not in body:

            await message.reply_text(

                "❌ استخدم:\n\n"

                "`اضف رد الكلمة = الرد`"

            )

            return


        trigger, reply = body.split(
            "=",
            1
        )


        trigger = trigger.strip()
        reply = reply.strip()


        if not trigger or not reply:

            await message.reply_text(
                "❌ الكلمة والرد لازم يكونوا موجودين."
            )

            return


        chat_key = str(
            message.chat.id
        )


        custom_replies.setdefault(
            chat_key,
            {}
        )


        # الحد الأقصى 500
        if (
            trigger
            not in custom_replies[chat_key]
            and len(
                custom_replies[chat_key]
            ) >= 500
        ):

            await message.reply_text(
                "❌ وصلت للحد الأقصى: 500 رد."
            )

            return


        custom_replies[
            chat_key
        ][trigger] = reply


        save_json(
            CUSTOM_FILE,
            custom_replies
        )


        await message.reply_text(

            "✅ تم حفظ الرد.\n\n"

            f"📌 الكلمة: "
            f"{trigger}\n"

            f"💬 الرد: "
            f"{reply}"

        )

        return


    # ---------------------------------
    # مسح رد
    # ---------------------------------

    if text.startswith(
        "مسح رد "
    ):

        if not await require_admin(
            message
        ):

            return


        trigger = text[
            7:
        ].strip()


        data = custom_replies.get(
            str(message.chat.id),
            {}
        )


        if trigger in data:

            del data[
                trigger
            ]


            save_json(
                CUSTOM_FILE,
                custom_replies
            )


            await message.reply_text(
                "✅ تم حذف الرد."
            )

        else:

            await message.reply_text(
                "❌ الرد مش موجود."
            )


# =========================================================
# الردود التلقائية
# =========================================================

@bot.on_message(
    filters.group & filters.text,
    group=5
)
async def custom_auto_reply(
    _,
    message
):

    if not await ensure_enabled(
        message
    ):

        return


    text = message.text.strip()


    if text.startswith(
        (
            "اضف رد ",
            "مسح رد ",
        )
    ):

        return


    data = custom_replies.get(
        str(message.chat.id),
        {}
    )


    for trigger, reply in data.items():

        if trigger.lower() in text.lower():

            await message.reply_text(
                reply
            )

            break


# =========================================================
# الحماية
# =========================================================

@bot.on_message(
    filters.group,
    group=6
)
async def protection(
    _,
    message
):

    if not await ensure_enabled(
        message
    ):

        return


    if not message.from_user:

        return


    # المشرفين مستثنين
    if await is_admin(
        message.chat.id,
        message.from_user.id
    ):

        return


    settings = settings_for(
        message.chat.id
    )


    text = (
        message.text
        or message.caption
        or ""
    ).lower()


    # ---------------------------------
    # الروابط
    # ---------------------------------

    if settings["links"]:

        if (
            "http://" in text
            or "https://" in text
            or "t.me/" in text
            or "www." in text
        ):

            await safe_delete(
                message
            )

            return


    # ---------------------------------
    # الكلمات الممنوعة
    # ---------------------------------

    if (
        settings["bad_words"]
        and text
    ):

        for word in BAD_WORDS:

            if (
                word
                and word.lower() in text
            ):

                await safe_delete(
                    message
                )

                return


    # ---------------------------------
    # الصور
    # ---------------------------------

    if (
        settings["photos"]
        and message.photo
    ):

        await safe_delete(
            message
        )

        return


    # ---------------------------------
    # الفيديو
    # ---------------------------------

    if (
        settings["videos"]
        and message.video
    ):

        await safe_delete(
            message
        )

        return


    # ---------------------------------
    # الملصقات
    # ---------------------------------

    if (
        settings["stickers"]
        and message.sticker
    ):

        await safe_delete(
            message
        )

        return


    # ---------------------------------
    # الصوت
    # ---------------------------------

    if (
        settings["voice"]
        and (
            message.voice
            or message.audio
        )
    ):

        await safe_delete(
            message
        )

        return


# =========================================================
# أوامر الحماية
# =========================================================

@bot.on_message(
    filters.group & filters.text,
    group=7
)
async def protection_commands(
    _,
    message
):

    text = message.text.strip()


    commands = {

        "قفل الروابط":
            ("links", True),

        "فتح الروابط":
            ("links", False),

        "قفل الصور":
            ("photos", True),

        "فتح الصور":
            ("photos", False),

        "قفل الفيديو":
            ("videos", True),

        "فتح الفيديو":
            ("videos", False),

        "قفل الملصقات":
            ("stickers", True),

        "فتح الملصقات":
            ("stickers", False),

        "قفل الصوت":
            ("voice", True),

        "فتح الصوت":
            ("voice", False),

        "قفل السب":
            ("bad_words", True),

        "فتح السب":
            ("bad_words", False),

    }


    if text not in commands:

        return


    if not await require_admin(
        message
    ):

        return


    key, value = commands[
        text
    ]


    settings = settings_for(
        message.chat.id
    )


    settings[key] = value


    save_json(
        SETTINGS_FILE,
        group_settings
    )


    await message.reply_text(
        f"✅ {text}."
    )


# =========================================================
# الرتب والإدارة
# =========================================================

@bot.on_message(
    filters.group & filters.text,
    group=8
)
async def moderation(
    _,
    message
):

    text = message.text.strip()


    # ---------------------------------
    # رتبتي
    # ---------------------------------

    if text == "رتبتي":

        if not message.from_user:

            return


        status, member = await get_status(

            message.chat.id,

            message.from_user.id
        )


        names = {

            "owner":
                "👑 المالك",

            "creator":
                "👑 المالك",

            "administrator":
                "🛡️ مشرف",

            "admin":
                "🛡️ مشرف",

            "member":
                "👤 عضو",

            "restricted":
                "🔇 مقيد",

            "left":
                "🚪 خارج المجموعة",

            "banned":
                "🚫 محظور",

        }


        await message.reply_text(

            "📌 رتبتك: "
            + names.get(
                status,
                "غير معروف"
            )

        )

        return


    # ---------------------------------
    # المالك
    # ---------------------------------

    if text == "المالك":

        try:

            async for member in bot.get_chat_members(

                message.chat.id,

                filter=
                enums.ChatMembersFilter.ADMINISTRATORS

            ):

                status = str(
                    member.status
                ).lower()


                if status in (
                    "owner",
                    "creator",
                ):

                    await message.reply_text(

                        "👑 مالك المجموعة:\n"
                        f"{member.user.mention}"

                    )

                    return


            await message.reply_text(
                "❌ مش قادر أحدد المالك."
            )


        except Exception as e:

            await message.reply_text(
                f"❌ {str(e)[:300]}"
            )


        return


    # ---------------------------------
    # المشرفين
    # ---------------------------------

    if text == "المشرفين":

        lines = [
            "🛡️ **مشرفين المجموعة:**"
        ]


        try:

            async for member in bot.get_chat_members(

                message.chat.id,

                filter=
                enums.ChatMembersFilter.ADMINISTRATORS

            ):

                lines.append(
                    f"• {member.user.mention}"
                )


            await message.reply_text(
                "\n".join(lines)
            )


        except Exception as e:

            await message.reply_text(
                f"❌ {str(e)[:300]}"
            )


        return


    # ---------------------------------
    # أوامر الإدارة
    # ---------------------------------

    if text not in (

        "ترقية",
        "تنزيل",
        "طرد",
        "حظر",
        "فك حظر",
        "كتم",
        "فك كتم",

    ):

        return


    if not await require_admin(
        message
    ):

        return


    user = await target_user(
        message
    )


    if not user:

        await message.reply_text(
            "❌ اعمل Reply على الشخص الأول."
        )

        return


    if user.is_bot:

        await message.reply_text(
            "❌ مينفعش أطبق الأمر على بوت."
        )

        return


    try:

        # ---------------------------------
        # ترقية
        # ---------------------------------

        if text == "ترقية":

            privileges = ChatPrivileges(

                can_manage_chat=True,

                can_delete_messages=True,

                can_manage_video_chats=True,

                can_restrict_members=True,

                can_promote_members=False,

                can_change_info=True,

                can_invite_users=True,

                can_pin_messages=True,

            )


            await bot.promote_chat_member(

                message.chat.id,

                user.id,

                privileges=privileges,

            )


            await message.reply_text(

                "✅ تمت ترقية "
                f"{user.mention}"

            )


        # ---------------------------------
        # تنزيل
        # ---------------------------------

        elif text == "تنزيل":

            privileges = ChatPrivileges(

                can_manage_chat=False,

                can_delete_messages=False,

                can_manage
